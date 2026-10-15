#!/usr/bin/env python3
"""
lispy_machine.py - a Lisp-Machine style editor for the lispy3 interpreter.

Features
  * Multiple editor buffers (tabs) with Lisp syntax highlighting
  * Persistent Listener (REPL) with history, coloured output
  * Inspector pane showing the last evaluated value (pretty-printed)
  * F5 / Ctrl+Enter : evaluate top-level form at cursor
  * F6 / Ctrl+Shift+Enter : evaluate whole buffer
  * F9 : evaluate the Listener input line
  * Paren matching, auto-indent, symbol completion (Ctrl+Space)
  * Open / Save / Save-As / Close buffers
  * Menu + status bar showing the current "package" (USER) and buffer

Run:  python lispy_machine.py
"""
import io
import contextlib
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# --- import the interpreter (no side effects when imported) -------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
import lispy3 as L


# =============================================================================
# Theme
# =============================================================================
COLORS = {
    "bg":          "#1e1e1e",
    "fg":          "#d4d4d4",
    "cursor":      "#ffffff",
    "selection":   "#264f78",
    "comment":     "#6a9955",
    "string":      "#ce9178",
    "keyword":     "#c586c0",
    "number":      "#b5cea8",
    "builtin":     "#4ec9b0",
    "paren_match": "#ffd700",
    "paren_bad":   "#f44747",
    "listener_bg": "#0c0c0c",
    "prompt":      "#569cd6",
    "result":      "#6a9955",
    "error":       "#f44747",
    "info":        "#dcdcaa",
    "status_bg":   "#007acc",
    "status_fg":   "#ffffff",
    "side_bg":     "#252526",
    "side_fg":     "#cccccc",
    "side_sel":    "#37373d",
    "entry_bg":    "#000000",
    "entry_fg":    "#ffffff",
}

FONT_MONO      = ("Consolas", 11)
FONT_MONO_BOLD = ("Consolas", 11, "bold")
FONT_UI        = ("Segoe UI", 9)
FONT_UI_BOLD   = ("Segoe UI", 9, "bold")


# =============================================================================
# Small helpers
# =============================================================================
def offset_to_pos(text: str, offset: int) -> str:
    """Convert a python string offset into a Tk 'line.col' index."""
    line = text.count("\n", 0, offset) + 1
    col  = offset - (text.rfind("\n", 0, offset) + 1)
    return f"{line}.{col}"


def find_top_level_form(text: str, pos: int):
    """Return (start, end) offsets of the outermost enclosing form at `pos`.

    Correctly skips over string literals, characters and ; comments.
    Returns None if the cursor is not inside any form.
    """
    stack = []
    i = 0
    in_str = False
    while i < len(text) and i <= pos:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == ";":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        elif c in "([{":
            stack.append((i, c))
        elif c in ")]}":
            if stack:
                stack.pop()
        i += 1

    if not stack:
        return None

    start, opener = stack[0]
    closer = {"(": ")", "[": "]", "{": "}"}[opener]
    depth = 0
    j = start
    in_str = False
    while j < len(text):
        c = text[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == ";":
            while j < len(text) and text[j] != "\n":
                j += 1
            continue
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return (start, j + 1)
        j += 1
    return None


def find_matching_bracket(text: str, pos: int):
    """Given `pos` points at a bracket char, return the offset of its mate."""
    c = text[pos]
    if c not in "()[]{}":
        return None
    pairs = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{"}
    target = pairs[c]
    forward = c in "([{"
    depth = 1
    i = pos + (1 if forward else -1)
    step = 1 if forward else -1
    while 0 <= i < len(text):
        if text[i] == c:
            depth += 1
        elif text[i] == target:
            depth -= 1
            if depth == 0:
                return i
        i += step
    return None

class _ListenerWriter(io.TextIOBase):
    """A stdout replacement that streams text straight into the Listener pane."""
    def __init__(self, app):
        self.app = app

    def write(self, s):                       # noqa: D401
        if s:
            self.app.listener_write(s, "result")
        return len(s)

    def writable(self):
        return True

    def flush(self):
        pass
        
# =============================================================================
# Editor tab
# =============================================================================
class EditorTab(tk.Frame):
    """One text buffer with syntax highlighting, paren matching, auto-indent."""

    def __init__(self, master, app, name: str, path=None, content: str = ""):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self.name = name
        self.path = path
        self.dirty = False
        self._highlight_job = None
        self._suppress_modified = False

        self.text = tk.Text(
            self, undo=True, wrap="none",
            bg=COLORS["bg"], fg=COLORS["fg"],
            insertbackground=COLORS["cursor"],
            selectbackground=COLORS["selection"],
            selectforeground=COLORS["fg"],
            font=FONT_MONO, tabs=("2c",),
            padx=8, pady=6, borderwidth=0, highlightthickness=0,
        )
        vsb = ttk.Scrollbar(self, orient="vertical",   command=self.text.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._setup_tags()
        self._setup_bindings()

        if content:
            self._suppress_modified = True
            self.text.insert("1.0", content)
            self._suppress_modified = False
            self.text.edit_reset()
        self.text.edit_modified(False)
        self.text.mark_set("insert", "1.0")
        self._schedule_highlight()

    # ---------- tags ----------
    def _setup_tags(self):
        t = self.text
        t.tag_configure("comment",     foreground=COLORS["comment"])
        t.tag_configure("string",      foreground=COLORS["string"])
        t.tag_configure("keyword",     foreground=COLORS["keyword"])
        t.tag_configure("number",      foreground=COLORS["number"])
        t.tag_configure("builtin",     foreground=COLORS["builtin"])
        t.tag_configure("paren_match", background=COLORS["paren_match"],
                                       foreground="#000000")
        t.tag_configure("paren_bad",   background=COLORS["paren_bad"],
                                       foreground="#ffffff")

    # ---------- bindings ----------
    def _setup_bindings(self):
        t = self.text
        t.bind("<KeyRelease>",   self._on_key)
        t.bind("<ButtonRelease-1>", self._on_key)
        t.bind("<Return>",       self._on_return)
        t.bind("<Tab>",          self._on_tab)
        t.bind("<Control-space>", self._complete)
        t.bind("<Control-slash>", self._toggle_comment)

        # Eval bindings
        t.bind("<F5>",                 lambda e: (self.app.eval_form_at_cursor(), "break")[1])
        t.bind("<Control-Return>",     lambda e: (self.app.eval_form_at_cursor(), "break")[1])
        t.bind("<F6>",                 lambda e: (self.app.eval_buffer(), "break")[1])
        t.bind("<Control-Shift-Return>", lambda e: (self.app.eval_buffer(), "break")[1])

    # ---------- highlighting ----------
    def _on_key(self, event=None):
        self._schedule_highlight()
        self._match_paren()
        if not self._suppress_modified:
            self.text.edit_modified(True)

    def _schedule_highlight(self):
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(30, self._highlight)

    def _highlight(self):
        self._highlight_job = None
        t = self.text
        for tag in ("comment", "string", "keyword", "number", "builtin"):
            t.tag_remove(tag, "1.0", "end")

        content = t.get("1.0", "end-1c")

        # strings (with escaped quotes)
        for m in re.finditer(r'"(?:[^"\\]|\\.)*"', content):
            self._tag("string", content, m.start(), m.end())

        # comments (skip inside strings — do a quick pass after strings)
        for m in re.finditer(r";[^\n]*", content):
            self._tag("comment", content, m.start(), m.end())

        # keywords  :foo
        for m in re.finditer(r"(?<![\w\-]):[a-zA-Z_][\w\-]*", content):
            self._tag("keyword", content, m.start(), m.end())

        # numbers
        for m in re.finditer(r"(?<![\w.\-])-?\d+(?:\.\d+)?(?![\w.])", content):
            self._tag("number", content, m.start(), m.end())

        # builtins (symbols defined in global_env)
        builtin_re = re.compile(r"([\w\-+*/<>=!?]+)")
        for m in builtin_re.finditer(content):
            name = m.group(1)
            if name in L.global_env and not name.startswith(":"):
                self._tag("builtin", content, m.start(), m.end())

    def _tag(self, tag, content, start, end):
        self.text.tag_add(tag,
                          offset_to_pos(content, start),
                          offset_to_pos(content, end))

    # ---------- paren matching ----------
    def _match_paren(self):
        t = self.text
        t.tag_remove("paren_match", "1.0", "end")
        t.tag_remove("paren_bad",   "1.0", "end")

        insert = t.index("insert")
        candidates = [insert]
        try:
            candidates.append(t.index("insert - 1c"))
        except tk.TclError:
            pass

        content = t.get("1.0", "end-1c")

        for cand in candidates:
            try:
                ch = t.get(cand)
            except tk.TclError:
                continue
            if ch not in "()[]{}":
                continue

            line, col = map(int, cand.split("."))
            lines = content.split("\n")
            offset = sum(len(l) + 1 for l in lines[: line - 1]) + col

            mate = find_matching_bracket(content, offset)
            if mate is None:
                t.tag_add("paren_bad", cand, f"{cand}+1c")
                return
            mate_pos = offset_to_pos(content, mate)
            t.tag_add("paren_match", cand, f"{cand}+1c")
            t.tag_add("paren_match", mate_pos, f"{mate_pos}+1c")
            return

    # ---------- smart keys ----------
    def _on_return(self, event=None):
        t = self.text
        line_idx = t.index("insert").split(".")[0]
        line = t.get(f"{line_idx}.0", f"{line_idx}.end")
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        extra = 0
        opens  = line.count("(") + line.count("[") + line.count("{")
        closes = line.count(")") + line.count("]") + line.count("}")
        extra = max(0, opens - closes)
        t.insert("insert", "\n" + " " * (indent + extra * 2))
        return "break"

    def _on_tab(self, event=None):
        # If the selection spans whole lines, indent them; else insert 2 spaces.
        sel = self.text.tag_ranges("sel")
        if sel:
            start_line = int(str(sel[0]).split(".")[0])
            end_line   = int(str(sel[1]).split(".")[0])
            for ln in range(start_line, end_line + 1):
                self.text.insert(f"{ln}.0", "  ")
        else:
            self.text.insert("insert", "  ")
        return "break"

    def _toggle_comment(self, event=None):
        sel = self.text.tag_ranges("sel")
        if not sel:
            line = int(self.text.index("insert").split(".")[0])
            lines = [line]
        else:
            l1 = int(str(sel[0]).split(".")[0])
            l2 = int(str(sel[1]).split(".")[0])
            lines = list(range(l1, l2 + 1))
        for ln in lines:
            line_text = self.text.get(f"{ln}.0", f"{ln}.end")
            if line_text.lstrip().startswith(";"):
                # uncomment
                stripped = line_text.lstrip()
                indent = len(line_text) - len(stripped)
                new = line_text[:indent] + stripped[1:].lstrip()
                self.text.delete(f"{ln}.0", f"{ln}.end")
                self.text.insert(f"{ln}.0", new)
            else:
                self.text.insert(f"{ln}.0", "; ")
        return "break"

    # ---------- symbol completion ----------
    def _complete(self, event=None):
        t = self.text
        insert = t.index("insert")
        line_idx = int(insert.split(".")[0])
        before = t.get(f"{line_idx}.0", insert)
        m = re.search(r"[\w\-+*/<>=!?]+$", before)
        prefix = m.group(0) if m else ""

        # Gather candidates: builtins + user-defined names in this buffer
        candidates = set(L.global_env.keys())
        content = t.get("1.0", "end-1c")
        for m2 in re.finditer(r"\(define\s+([\w\-+*/<>=!?]+)", content):
            candidates.add(m2.group(1))
        matches = sorted(c for c in candidates
                         if c.startswith(prefix) and c != prefix
                         and not c.startswith("_"))
        if not matches:
            return "break"
        if len(matches) == 1:
            t.insert("insert", matches[0][len(prefix):])
            return "break"

        # Popup listbox
        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.configure(bg="#333")
        x = t.winfo_rootx() + t.bbox("insert")[0] if t.bbox("insert") else t.winfo_rootx() + 40
        y = (t.winfo_rooty() + t.bbox("insert")[1] + 20) if t.bbox("insert") else t.winfo_rooty() + 40
        popup.wm_geometry(f"+{x}+{y}")

        lb = tk.Listbox(popup, bg="#1e1e1e", fg="#d4d4d4",
                        selectbackground="#264f78", font=FONT_MONO,
                        borderwidth=0, highlightthickness=0,
                        activestyle="none", height=min(10, len(matches)))
        for s in matches:
            lb.insert("end", s)
        lb.pack()

        def choose(evt=None):
            sel = lb.curselection()
            if sel:
                t.insert("insert", matches[sel[0]][len(prefix):])
            popup.destroy()

        lb.bind("<Return>", choose)
        lb.bind("<Double-Button-1>", choose)
        lb.bind("<Escape>", lambda e: popup.destroy())
        popup.bind("<FocusOut>", lambda e: popup.destroy())
        lb.focus_set()
        lb.selection_set(0)
        return "break"

    # ---------- content ----------
    def get_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_content(self, content: str):
        self._suppress_modified = True
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self._suppress_modified = False
        self._schedule_highlight()


# =============================================================================
# Main application
# =============================================================================
class LispMachine(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lispy3 Machine")
        self.geometry("1280x820")
        self.configure(bg=COLORS["bg"])
        self.minsize(900, 600)

        # state
        self.tabs: dict[str, EditorTab] = {}       # name -> EditorTab
        self.tab_order: list[str] = []
        self.listener_history: list[str] = []
        self.listener_hist_idx = 0
        self._welcome_done = False

        self._setup_style()
        self._build_menu()
        self._build_layout()
        self._build_status()
        self._bind_global()

        # welcome buffer
        self.new_buffer("untitled.lisp", WELCOME)

        self.listener_write(";; Lispy3 Machine ready.\n", "info")
        self.listener_write(";; F5 = eval form at cursor,  F6 = eval buffer,  F9 = eval listener input.\n", "info")
        self.listener_write(";; Ctrl+Space completes a symbol.  Try `(load \"lsystems\")`.\n\n", "info")
        self.listener_input.focus_set()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- ttk style ----------
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0, tabmargins=0)
        style.configure("TNotebook.Tab",
                        background=COLORS["side_bg"],
                        foreground=COLORS["side_fg"],
                        padding=[14, 5], font=FONT_UI)
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["bg"])],
                  foreground=[("selected", "#ffffff")])
        style.configure("TPanedwindow", background=COLORS["bg"])
        style.configure("Sash", sashthickness=4, gripcount=0)

    # ---------- menus ----------
    def _build_menu(self):
        bar = tk.Menu(self, tearoff=0)

        file_m = tk.Menu(bar, tearoff=0)
        file_m.add_command(label="New buffer",       accelerator="Ctrl+N", command=self.new_buffer_dialog)
        file_m.add_command(label="Open…",            accelerator="Ctrl+O", command=self.open_file)
        file_m.add_command(label="Save",             accelerator="Ctrl+S", command=self.save_current)
        file_m.add_command(label="Save as…",         accelerator="Ctrl+Shift+S", command=self.save_current_as)
        file_m.add_separator()
        file_m.add_command(label="Close buffer",     accelerator="Ctrl+W", command=self.close_current)
        file_m.add_command(label="Quit",             accelerator="Ctrl+Q", command=self._on_close)
        bar.add_cascade(label="File", menu=file_m)

        edit_m = tk.Menu(bar, tearoff=0)
        edit_m.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self._call_editor("event_generate", "<<Undo>>"))
        edit_m.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self._call_editor("event_generate", "<<Redo>>"))
        edit_m.add_separator()
        edit_m.add_command(label="Toggle comment",   accelerator="Ctrl+/", command=lambda: self._call_editor("_toggle_comment"))
        edit_m.add_command(label="Complete symbol",  accelerator="Ctrl+Space", command=lambda: self._call_editor("_complete"))
        bar.add_cascade(label="Edit", menu=edit_m)

        eval_m = tk.Menu(bar, tearoff=0)
        eval_m.add_command(label="Eval form at cursor", accelerator="F5",     command=self.eval_form_at_cursor)
        eval_m.add_command(label="Eval whole buffer",   accelerator="F6",     command=self.eval_buffer)
        eval_m.add_separator()
        eval_m.add_command(label="Eval listener input", accelerator="F9",     command=self._listener_submit)
        eval_m.add_separator()
        eval_m.add_command(label="Clear listener",      accelerator="Ctrl+L", command=self.clear_listener)
        bar.add_cascade(label="Eval", menu=eval_m)

        view_m = tk.Menu(bar, tearoff=0)
        view_m.add_command(label="Reload lsystems",     command=lambda: self._run_silent('(load "lsystems")'))
        view_m.add_command(label="Show global env",     command=self._show_env)
        view_m.add_separator()
        view_m.add_command(label="Focus listener",      accelerator="Ctrl+E", command=lambda: self.listener_input.focus_set())
        bar.add_cascade(label="View", menu=view_m)

        help_m = tk.Menu(bar, tearoff=0)
        help_m.add_command(label="About", command=self._about)
        bar.add_cascade(label="Help", menu=help_m)

        self.config(menu=bar)

    # ---------- layout ----------
    def _build_layout(self):
        # --- status bar first (bottom-docked)
        status_frame = tk.Frame(self, bg=COLORS["status_bg"], height=22)
        status_frame.pack(side="bottom", fill="x")
        status_frame.pack_propagate(False)
        self.status_left = tk.Label(status_frame, text="USER", bg=COLORS["status_bg"],
                                    fg=COLORS["status_fg"], font=FONT_UI_BOLD, padx=10)
        self.status_left.pack(side="left")
        self.status_right = tk.Label(status_frame, text="Ready", bg=COLORS["status_bg"],
                                     fg=COLORS["status_fg"], font=FONT_UI, padx=10)
        self.status_right.pack(side="right")

        # --- main container split: top (editor + sidebar) and bottom (listener)
        outer = tk.PanedWindow(self, orient="vertical",
                               bg=COLORS["bg"], sashwidth=4, sashrelief="flat")
        outer.pack(fill="both", expand=True)

        top = tk.Frame(outer, bg=COLORS["bg"])
        outer.add(top, minsize=300)

        # ---- sidebar (buffers + inspector) ----
        sidebar = tk.Frame(top, bg=COLORS["side_bg"], width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="BUFFERS", bg=COLORS["side_bg"], fg="#888",
                 font=FONT_UI_BOLD, anchor="w", padx=8, pady=4).pack(fill="x")

        self.buffer_list = tk.Listbox(
            sidebar, bg=COLORS["side_bg"], fg=COLORS["side_fg"],
            selectbackground=COLORS["side_sel"], selectforeground="#ffffff",
            borderwidth=0, highlightthickness=0, activestyle="none",
            font=FONT_UI, height=8)
        self.buffer_list.pack(fill="x", padx=4)
        self.buffer_list.bind("<<ListboxSelect>>", self._on_buffer_select)

        tk.Label(sidebar, text="INSPECTOR", bg=COLORS["side_bg"], fg="#888",
                 font=FONT_UI_BOLD, anchor="w", padx=8, pady=4).pack(fill="x", pady=(12, 0))

        self.inspector = tk.Text(
            sidebar, bg=COLORS["bg"], fg=COLORS["fg"], font=FONT_MONO,
            wrap="word", borderwidth=0, highlightthickness=0, height=10,
            padx=6, pady=4)
        self.inspector.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.inspector.insert("1.0", "(no value yet)")
        self.inspector.configure(state="disabled")

        # ---- editor notebook ----
        self.notebook = ttk.Notebook(top)
        self.notebook.pack(side="left", fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # ---- listener at the bottom of the outer paned window ----
        listener_frame = tk.Frame(outer, bg=COLORS["listener_bg"])
        outer.add(listener_frame, minsize=140)

        hdr = tk.Frame(listener_frame, bg=COLORS["listener_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="LISTENER", bg=COLORS["listener_bg"], fg="#888",
                 font=FONT_UI_BOLD, anchor="w", padx=8, pady=2).pack(side="left")
        tk.Button(hdr, text="Clear", bg=COLORS["side_bg"], fg="#ddd",
                  font=FONT_UI, borderwidth=0, padx=8,
                  command=self.clear_listener).pack(side="right", padx=4, pady=2)

        self.listener_text = ScrolledText(
            listener_frame, bg=COLORS["listener_bg"], fg=COLORS["fg"],
            font=FONT_MONO, wrap="word", height=8,
            borderwidth=0, highlightthickness=0, padx=8, pady=4)
        self.listener_text.pack(fill="both", expand=True)
        self.listener_text.configure(state="disabled")
        self.listener_text.tag_configure("prompt", foreground=COLORS["prompt"], font=FONT_MONO_BOLD)
        self.listener_text.tag_configure("result", foreground=COLORS["result"])
        self.listener_text.tag_configure("error",  foreground=COLORS["error"])
        self.listener_text.tag_configure("info",   foreground=COLORS["info"])

        input_row = tk.Frame(listener_frame, bg=COLORS["listener_bg"])
        input_row.pack(fill="x", padx=6, pady=(0, 6))
        tk.Label(input_row, text="USER>", bg=COLORS["listener_bg"],
                 fg=COLORS["prompt"], font=FONT_MONO_BOLD).pack(side="left", padx=(2, 6))
        self.listener_input = tk.Entry(
            input_row, bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
            insertbackground="#fff", font=FONT_MONO, borderwidth=0,
            highlightthickness=1, highlightbackground="#333",
            highlightcolor=COLORS["prompt"])
        self.listener_input.pack(side="left", fill="x", expand=True, ipady=4)
        self.listener_input.bind("<Return>",  lambda e: (self._listener_submit(), "break")[1])
        self.listener_input.bind("<Up>",      self._history_up)
        self.listener_input.bind("<Down>",    self._history_down)
        self.listener_input.bind("<Control-l>", lambda e: (self.clear_listener(), "break")[1])

    def _build_status(self):
        pass  # placeholder

    def _bind_global(self):
        self.bind_all("<Control-n>", lambda e: self.new_buffer_dialog())
        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_current())
        self.bind_all("<Control-Shift-S>", lambda e: self.save_current_as())
        self.bind_all("<Control-w>", lambda e: self.close_current())
        self.bind_all("<Control-q>", lambda e: self._on_close())
        self.bind_all("<Control-e>", lambda e: self.listener_input.focus_set())

    # =========================================================================
    # Buffer management
    # =========================================================================
    def new_buffer(self, name: str, content: str = "", path=None) -> EditorTab:
        # de-dup name
        base = name
        n = 1
        while name in self.tabs:
            n += 1
            name = f"{base} <{n}>"

        tab = EditorTab(self.notebook, self, name, path=path, content=content)
        self.tabs[name] = tab
        self.tab_order.append(name)
        self.notebook.add(tab, text=name)
        self.notebook.select(tab)
        self._refresh_buffer_list()
        return tab

    def new_buffer_dialog(self):
        self.new_buffer("untitled.lisp", "")

    def current_tab(self) -> EditorTab | None:
        sel = self.notebook.select()
        if not sel:
            return None
        widget = self.nametowidget(sel)
        for name, tab in self.tabs.items():
            if tab is widget:
                return tab
        return None

    def _refresh_buffer_list(self):
        self.buffer_list.delete(0, "end")
        for name in self.tab_order:
            marker = " ●" if self.tabs[name].dirty else ""
            self.buffer_list.insert("end", f" {name}{marker}")

    def _on_buffer_select(self, event=None):
        sel = self.buffer_list.curselection()
        if not sel:
            return
        name = self.tab_order[sel[0]]
        self.notebook.select(self.tabs[name])
        self.tabs[name].text.focus_set()

    def _on_tab_change(self, event=None):
        tab = self.current_tab()
        if tab:
            self.status_right.configure(text=f"buffer: {tab.name}")

    def close_current(self):
        tab = self.current_tab()
        if not tab:
            return
        if tab.dirty:
            if not messagebox.askyesno("Unsaved changes",
                                       f"Discard unsaved changes in {tab.name}?"):
                return
        self.notebook.forget(tab)
        self.tabs.pop(tab.name, None)
        self.tab_order.remove(tab.name)
        tab.destroy()
        self._refresh_buffer_list()

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open Lisp file",
            filetypes=[("Lisp", "*.lisp"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror("Open failed", str(e))
            return
        self.new_buffer(os.path.basename(path), content, path=path)

    def save_current(self):
        tab = self.current_tab()
        if not tab:
            return
        if not tab.path:
            return self.save_current_as()
        try:
            with open(tab.path, "w", encoding="utf-8") as f:
                f.write(tab.get_content())
            tab.dirty = False
            tab.text.edit_modified(False)
            self._refresh_buffer_list()
            self.status_right.configure(text=f"saved: {tab.path}")
        except OSError as e:
            messagebox.showerror("Save failed", str(e))

    def save_current_as(self):
        tab = self.current_tab()
        if not tab:
            return
        path = filedialog.asksaveasfilename(
            title="Save as",
            defaultextension=".lisp",
            filetypes=[("Lisp", "*.lisp"), ("All files", "*.*")])
        if not path:
            return
        tab.path = path
        tab.name = os.path.basename(path)
        self.tab_order = [tab.name if n == tab.name else n for n in self.tab_order]
        self.notebook.tab(tab, text=tab.name)
        self.save_current()
        self._refresh_buffer_list()

    # =========================================================================
    # Evaluation
    # =========================================================================
    def _run(self, code: str):
        """Evaluate `code`. Returns (value, error). Stdout is streamed to the Listener."""
        writer = _ListenerWriter(self)
        try:
            with contextlib.redirect_stdout(writer):
                ast = L.parse(code)
                val = L.eval_exp(ast, L.global_env)
            return val, None
        except Exception as e:                # noqa: BLE001
            return None, e
            
    def eval_form_at_cursor(self):
        tab = self.current_tab()
        if not tab:
            return
        t = tab.text
        content = t.get("1.0", "end-1c")
        try:
            line, col = map(int, t.index("insert").split("."))
        except tk.TclError:
            return
        lines = content.split("\n")
        offset = sum(len(l) + 1 for l in lines[: line - 1]) + col
        span = find_top_level_form(content, offset)
        if span is None:
            self.listener_write(";; No form at cursor.\n", "error")
            return
        start, end = span
        form = content[start:end]
        self.listener_write(f"USER> {form.strip()}\n", "prompt")
        val, err = self._run(form)
        self._report_eval(val, err)

    def eval_buffer(self):
        tab = self.current_tab()
        if not tab:
            return
        content = tab.get_content()
        self.listener_write(f";; --- evaluating {tab.name} ---\n", "info")
        val, err = self._run(f"(begin {content})")
        self._report_eval(val, err, show_value=False)
        self.listener_write(f";; --- done ---\n", "info")

    def _report_eval(self, val, err, show_value=True):
        if err is not None:
            self.listener_write(f"Error: {err}\n", "error")
            self.set_inspector(f"Error: {err}")
            return
        if val is None:
            if show_value:
                self.listener_write(";; ok\n", "info")
            self.set_inspector("(none)")
            return
        try:
            val_str = L.lisp_str(val)
        except Exception:
            val_str = repr(val)
        if show_value:
            self.listener_write(val_str + "\n", "result")
        try:
            pretty = L.pretty_print(val, width=34)
        except Exception:
            pretty = val_str
        self.set_inspector(pretty)

    def _run_silent(self, code: str):
        val, err = self._run(code)
        if err is not None:
            self.listener_write(f"Error: {err}\n", "error")
        elif val is not None:
            try:
                self.listener_write(L.lisp_str(val) + "\n", "result")
            except Exception:
                pass

    # =========================================================================
    # Listener
    # =========================================================================
    def _listener_submit(self):
        code = self.listener_input.get()
        self.listener_input.delete(0, "end")
        if not code.strip():
            return
        self.listener_history.append(code)
        self.listener_hist_idx = len(self.listener_history)
        self.listener_write(f"USER> {code}\n", "prompt")
        # handle "exit" like the console REPL
        if code.strip().lower() == "exit":
            self._on_close()
            return
        val, err = self._run(code)
        self._report_eval(val, err)

    def _history_up(self, event=None):
        if not self.listener_history:
            return "break"
        self.listener_hist_idx = max(0, self.listener_hist_idx - 1)
        self.listener_input.delete(0, "end")
        self.listener_input.insert(0, self.listener_history[self.listener_hist_idx])
        return "break"

    def _history_down(self, event=None):
        if not self.listener_history:
            return "break"
        self.listener_hist_idx = min(len(self.listener_history), self.listener_hist_idx + 1)
        self.listener_input.delete(0, "end")
        if self.listener_hist_idx < len(self.listener_history):
            self.listener_input.insert(0, self.listener_history[self.listener_hist_idx])
        return "break"

    def listener_write(self, text: str, tag: str | None = None):
        self.listener_text.configure(state="normal")
        if tag:
            self.listener_text.insert("end", text, tag)
        else:
            self.listener_text.insert("end", text)
        self.listener_text.see("end")
        self.listener_text.configure(state="disabled")

    def clear_listener(self):
        self.listener_text.configure(state="normal")
        self.listener_text.delete("1.0", "end")
        self.listener_text.configure(state="disabled")

    # =========================================================================
    # Inspector
    # =========================================================================
    def set_inspector(self, text: str):
        self.inspector.configure(state="normal")
        self.inspector.delete("1.0", "end")
        self.inspector.insert("1.0", text)
        self.inspector.configure(state="disabled")

    # =========================================================================
    # Misc
    # =========================================================================
    def _call_editor(self, method_name: str, *args):
        tab = self.current_tab()
        if tab and hasattr(tab, method_name):
            getattr(tab, method_name)(*args)

    def _show_env(self):
        names = sorted(k for k in L.global_env.keys() if not k.startswith("_"))
        text = "USER package — global bindings:\n\n"
        chunks = []
        for n in names:
            chunks.append(n)
        text += "  " + ", ".join(chunks)
        self.listener_write(text + "\n", "info")

    def _about(self):
        messagebox.showinfo(
            "About Lispy3 Machine",
            "Lispy3 Machine — a Lisp Machine style editor\n"
            "for the lispy3 interpreter.\n\n"
            "F5  eval form at cursor\n"
            "F6  eval whole buffer\n"
            "F9  eval listener input\n"
            "Ctrl+Space  complete symbol\n"
            "Ctrl+/      toggle comment\n"
        )

    def _on_close(self):
        dirty = [t for t in self.tabs.values() if t.dirty]
        if dirty:
            if not messagebox.askyesno(
                "Unsaved buffers",
                f"{len(dirty)} buffer(s) have unsaved changes. Quit anyway?"
            ):
                return
        self.destroy()


# =============================================================================
# Welcome content
# =============================================================================
WELCOME = r''';; Welcome to Lispy3 Machine.
;; F5  - evaluate the top-level form at the cursor
;; F6  - evaluate the whole buffer
;; F9  - evaluate what you typed in the Listener
;; Ctrl+Space - complete a symbol
;; Ctrl+/     - toggle comment

(define square (lambda [x] (* x x)))
(square 12)

(define fact
  (lambda [n]
    (if (< n 2)
        1
        (* n (fact (- n 1))))))
(fact 10)

;; Clojure-style data
(define user {:name "Tony" :status "Trusty"})
(:name user)

;; Turtle graphics — load the engine, then draw:
;; (load "lsystems")
;; (lsystem-from "F" "F[+F]F[-F]F" 4 3 23.5 0 -250 90)
;; (lsystem-from "F" "FF-[-F+F+F]+[+F-F-F]" 3 6 23 -50 -250 90)
'''


# =============================================================================
def main():
    app = LispMachine()
    app.mainloop()


if __name__ == "__main__":
    main()