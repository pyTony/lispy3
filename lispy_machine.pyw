#!/usr/bin/env python3
"""
lispy_machine.pyw - a Lisp-Machine style editor for the lispy3 interpreter.

Features
  * Multiple editor buffers (tabs) with syntax colouring read from syntax/*.json
  * Persistent Listener (REPL) with history, coloured output
  * Inspector pane showing the last evaluated value (pretty-printed)
  * F5 / Ctrl+Enter : evaluate top-level form at cursor
  * F6 / Ctrl+Shift+Enter : evaluate whole buffer
  * F7 : inspect the symbol at the cursor (or typed in the Listener)
  * F9 : evaluate the Listener input line
  * View > Plain lispy3 REPL: the Listener behaves like `python lispy3.py`
    (lispy3> prompt, multi-line input, Tab completion)
  * Paren matching, auto-indent, symbol completion (Ctrl+Space)
  * Open / Save / Save-As / Close buffers
  * Menu + status bar showing the current "package" (USER) and buffer

Run:  python lispy_machine.pyw [--repl] [file.lisp ...]
      --repl starts the Listener as the plain lispy3 REPL (View menu toggles it).
      Each file named on the command line opens in its own buffer; a file that
      does not exist yet opens empty and is created on the first Save. With no
      files, demo.lisp from the Lispy folder opens instead.
"""
import io
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from tkinter.scrolledtext import ScrolledText

# --- import the interpreter (no side effects when imported) -------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
import lispy3 as L
import guide
import syntax_highlight as SH


# =============================================================================
# Theme
# =============================================================================
COLORS = {
    "bg":          "#1e1e1e",
    "fg":          "#d4d4d4",
    "cursor":      "#ffffff",
    "selection":   "#264f78",
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

# Syntax colours and rules come from syntax/*.json (see syntax_highlight.py).
LANGUAGES, SYNTAX_ERRORS = SH.load_languages()
DEFAULT_LANGUAGE = SH.language_for("untitled.lisp", LANGUAGES) or SH.Language({"name": "Plain text"})
SYNTAX_TAGS = sorted({tag for lang in LANGUAGES for tag in lang.colors})
BUILTIN_NAMES = frozenset(list(L.standard_env()) + ['load', 'save'])
# The name being typed at the end of a line, for completion (":name" keywords included)
SYMBOL_TAIL = re.compile(r"[\w\-+*/<>=!?:.]+$")

# Remembers the View > Plain lispy3 REPL choice between runs
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".lispy3_machine.json")

def load_settings(path: str = SETTINGS_PATH) -> dict:
    """The saved editor settings, or {} when there are none or they cannot be read."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except (OSError, ValueError):
        return {}
    return settings if isinstance(settings, dict) else {}

def save_settings(settings: dict, path: str = SETTINGS_PATH) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass

def parse_args(argv):
    """Split the command line into (plain_repl, files). --repl may come anywhere."""
    return "--repl" in argv, [a for a in argv if a != "--repl"]

def common_prefix(names) -> str:
    """The longest start shared by all `names`, as readline completes it."""
    return os.path.commonprefix(list(names))

def user_defined_names():
    """Globals the user made: new names, or their own function under a built-in name."""
    return {k for k, v in L.global_env.items()
            if k not in BUILTIN_NAMES
            or (isinstance(v, L.Procedure) and v.native_fn is None)}

# Code shown in the Listener and Inspector is coloured like a .lisp buffer
LISP_LANGUAGE = SH.language_for("listener.lisp", LANGUAGES, DEFAULT_LANGUAGE)

def setup_code_tags(widget):
    """Give a Text widget the Lisp syntax colours as tags."""
    for tag in SYNTAX_TAGS:
        widget.tag_configure(tag, foreground=LISP_LANGUAGE.colors.get(tag, COLORS["fg"]))

def color_code(widget, start: str, text: str):
    """Colour `text`, which starts at index `start` in `widget`, like the editor does."""
    variables = user_defined_names() if LISP_LANGUAGE.env_words else ()
    for tag in SYNTAX_TAGS:
        widget.tag_remove(tag, start, f"{start}+{len(text)}c")
    for tag, a, b in LISP_LANGUAGE.spans(text, builtins=BUILTIN_NAMES, variables=variables):
        widget.tag_add(tag, f"{start}+{a}c", f"{start}+{b}c")

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Help > About
ABOUT_CREDITS = (
    "Written by Tony Veijalainen (pyTony), github.com/pyTony/lispy3\n"
    "Grown from Peter Norvig's lis.py and lispy.py, norvig.com/lispy.html\n"
    "Roots: a Lisp in the Finnish magazine Prosessori (1981), and a\n"
    "Python 2 version on the DaniWeb forums (2011)\n"
    "Reference: Luciano Ramalho's fluentpython/lispy\n"
    "With code from AI assistants: Google Jules and Gemini, Anthropic Claude"
)

def _git(folder, *args):
    """Run git in `folder` with no console window and no password prompt."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(["git", *args], cwd=folder, env=env, capture_output=True,
                          text=True, timeout=120, creationflags=flags)

def git_pull(folder: str = APP_DIR):
    """Run `git pull --ff-only` in `folder`. Return (result, git's output).

    result is "updated", "current" (nothing new) or "failed". --ff-only never
    makes a merge commit, so git cannot stop to open an editor; local changes
    that would be overwritten make git refuse, and its message names them.
    """
    try:
        before = _git(folder, "rev-parse", "HEAD").stdout.strip()
        done = _git(folder, "pull", "--ff-only")
        after = _git(folder, "rev-parse", "HEAD").stdout.strip()
    except FileNotFoundError:
        return "failed", "git is not installed, or not on PATH."
    except subprocess.TimeoutExpired:
        return "failed", "git pull did not finish in 2 minutes."
    except OSError as e:
        return "failed", f"Could not run git: {e}"
    output = (done.stdout + done.stderr).strip()
    if done.returncode != 0:
        return "failed", output
    return ("updated" if before != after else "current"), output

LISTENER_PROMPT = re.compile(r"(?:USER>|lispy3>|\.\.\. \(\d+\)>) ?")

def listener_to_code(log: str) -> str:
    """Turn a Listener transcript into a program that runs and can be saved.

    The USER>, lispy3> and ... (n)> prompts are removed from what was typed,
    a form that spans lines keeps its lines, and every other line (results,
    printed output, errors) is commented out with ";; ". Lines that are
    already comments and blank lines stay as they are. A form whose result
    was an error, or that the Listener shortened with "...", is commented
    out too, so the program runs to the end.
    """
    out = []
    pending = 0                       # brackets still open in the form being read
    form = None                       # (first, last + 1) index in `out` of the latest form
    for line in log.splitlines():
        if pending:
            m = LISTENER_PROMPT.match(line)
            out.append(line[m.end():] if m and m.group().startswith("...") else line)
            form = (form[0], len(out))
            pending = L.count_balance("\n".join(out[form[0]:]))
            continue
        m = LISTENER_PROMPT.match(line)
        if m:
            code = line[m.end():]
            if not code.strip():
                continue
            balance = L.count_balance(code)
            if balance and code.rstrip().endswith("..."):
                out.append(";; " + code + "   ; shortened in the Listener")
                form = None
                continue
            out.append(code)
            form = (len(out) - 1, len(out))
            pending = balance
        elif not line.strip() or line.lstrip().startswith(";"):
            out.append(line)
        else:
            if line.startswith("Error:") and form is not None:
                first, last = form
                out[first:last] = [";; " + code for code in out[first:last]]
                form = None
            out.append(";; " + line)
    return "\n".join(out) + "\n" if out else ""

def preview(val, limit: int = 40) -> str:
    """A value on one short line for the Inspector's list."""
    try:
        text = L.lisp_str(val)
    except Exception:                                # noqa: BLE001
        text = repr(val)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 3] + "..."

def inspector_items(env=None):
    """The Inspector's list: [(name, preview), ...] of the user's definitions, sorted."""
    env = L.global_env if env is None else env
    return [(name, preview(env[name])) for name in sorted(user_defined_names()) if name in env]

def restart_command(files, plain_repl: bool) -> list[str]:
    """The command that starts Lispy3 Machine again with these files open."""
    script = os.path.join(APP_DIR, "lispy_machine.pyw")
    return [sys.executable, script] + (["--repl"] if plain_repl else []) + list(files)

# View > Open terminal: (program, arguments) tried in order on Linux; the
# working directory is also passed to Popen, so plain terminals start there too.
LINUX_TERMINALS = (
    ("x-terminal-emulator", ()),
    ("gnome-terminal",      ("--working-directory={cwd}",)),
    ("konsole",             ("--workdir", "{cwd}")),
    ("xfce4-terminal",      ("--working-directory={cwd}",)),
    ("mate-terminal",       ("--working-directory={cwd}",)),
    ("lxterminal",          ("--working-directory={cwd}",)),
    ("alacritty",           ("--working-directory", "{cwd}")),
    ("kitty",               ("--directory", "{cwd}")),
    ("xterm",               ()),
)

def terminal_command(cwd: str, platform: str = sys.platform,
                     which=shutil.which, env=os.environ) -> list[str] | None:
    """The command that opens a system terminal in `cwd`, or None if none is found.

    Windows: Windows Terminal, else cmd.exe (started in a new console).
    Linux: $TERMINAL, then the usual terminals; under WSL without a Linux
    terminal, a Windows terminal running wsl.exe in `cwd`.
    """
    if platform == "win32":
        if which("wt.exe"):
            return ["wt.exe", "-d", cwd]
        return [env.get("COMSPEC", "cmd.exe")]
    if platform == "darwin":
        return ["open", "-a", "Terminal", cwd]
    if env.get("TERMINAL") and which(env["TERMINAL"]):
        return [env["TERMINAL"]]
    for program, args in LINUX_TERMINALS:
        if which(program):
            return [program] + [a.format(cwd=cwd) for a in args]
    if env.get("WSL_DISTRO_NAME"):
        if which("wt.exe"):
            return ["wt.exe", "wsl.exe", "--cd", cwd]
        if which("cmd.exe"):
            return ["cmd.exe", "/c", "start", "wsl.exe", "--cd", cwd]
    return None

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
    while i < len(text) and i < pos:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif text.startswith('"""', i):
            end = text.find('"""', i + 3)
            i = len(text) if end < 0 else end + 3
            continue
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
        elif text.startswith('"""', j):
            end = text.find('"""', j + 3)
            j = len(text) if end < 0 else end + 3
            continue
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


def find_matching_bracket(text: str, pos: int, skip=None):
    """Given `pos` points at a bracket char, return the offset of its mate.

    `skip`, if given, is a sequence with a true value at every offset that
    is inside a string or comment; brackets there are not counted.
    """
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
        if skip is not None and skip[i]:
            pass
        elif text[i] == c:
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
        self.language = DEFAULT_LANGUAGE
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
        self.set_language()
        t.tag_configure("paren_match", background=COLORS["paren_match"],
                                       foreground="#000000")
        t.tag_configure("paren_bad",   background=COLORS["paren_bad"],
                                       foreground="#ffffff")
        t.tag_configure("search_all",  background="#5c4d00",
                                       foreground="#ffffff")
        t.tag_configure("search_current", background="#ffd700",
                                        foreground="#000000")

        # Virtual events fired by menu / programmatic paste and cut
        t.bind("<<Paste>>", self._schedule_highlight)
        t.bind("<<Cut>>",   self._schedule_highlight)

        # X11 middle-click paste and Windows right-click paste
        t.bind("<ButtonRelease-2>", self._on_key)
        t.bind("<ButtonRelease-3>", self._on_key)

    # ---------- bindings ----------
    def _setup_bindings(self):
        t = self.text
        t.bind("<KeyRelease>",   self._on_key)
        t.bind("<ButtonRelease-1>", self._on_key)
        t.bind("<Return>",       self._on_return)
        t.bind("<Tab>",          self._on_tab)
        t.bind("<Control-space>", self._complete)
        t.bind("<Control-Key-space>", self._complete)  # Added fallback for Windows/Linux window managers
        t.bind("<Control-slash>", self._toggle_comment)

        # Eval bindings
        t.bind("<F5>",                      lambda e: (self.app.eval_form_at_cursor(), "break")[1])
        t.bind("<Control-Return>",          lambda e: (self.app.eval_form_at_cursor(), "break")[1])
        t.bind("<F6>",                      lambda e: (self.app.eval_buffer(), "break")[1])
        t.bind("<Control-Shift-Return>",    lambda e: (self.app.eval_buffer(), "break")[1])

    # ---------- highlighting ----------
    def set_language(self):
        """Pick the syntax rules from the file name and set the tag colours."""
        self.language = SH.language_for(self.path or self.name, LANGUAGES, DEFAULT_LANGUAGE)
        for tag in SYNTAX_TAGS:
            self.text.tag_configure(tag, foreground=self.language.colors.get(tag, COLORS["fg"]))
        for tag in SYNTAX_TAGS:              # let search / paren tags show on top
            self.text.tag_lower(tag)
        self._schedule_highlight()

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
        for tag in SYNTAX_TAGS:
            t.tag_remove(tag, "1.0", "end")

        content = t.get("1.0", "end-1c")
        variables = user_defined_names() if self.language.env_words else ()
        for tag, start, end in self._spans(content, variables):
            self._tag(tag, content, start, end)

    def _spans(self, content, variables=None):
        if variables is None:
            variables = user_defined_names() if self.language.env_words else ()
        return self.language.spans(content, builtins=BUILTIN_NAMES, variables=variables)

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

            skip = SH.code_mask(self._spans(content), len(content))
            if skip[offset]:                 # a bracket inside a string or comment
                continue
            mate = find_matching_bracket(content, offset, skip)
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
        
        opens  = line.count("(") + line.count("[") + line.count("{")
        closes = line.count(")") + line.count("]") + line.count("}")
        
        # Keep the current line's indent level as the base, adding extra only for unclosed openings.
        # Do not reduce indent when closing brackets are present.
        extra = 2 if opens > closes else 0
        target_indent = indent + extra
        
        t.insert("insert", "\n" + " " * target_indent)
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
        mark = self.language.line_comment
        if not mark:
            return "break"
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
            if line_text.lstrip().startswith(mark):
                # uncomment
                stripped = line_text.lstrip()
                indent = len(line_text) - len(stripped)
                new = line_text[:indent] + stripped[len(mark):].lstrip()
                self.text.delete(f"{ln}.0", f"{ln}.end")
                self.text.insert(f"{ln}.0", new)
            else:
                self.text.insert(f"{ln}.0", mark + " ")
        return "break"

    # ---------- symbol completion ----------
    def _complete(self, event=None):
        t = self.text
        insert = t.index("insert")
        line_idx = int(insert.split(".")[0])
        before = t.get(f"{line_idx}.0", insert)
        m = SYMBOL_TAIL.search(before)
        prefix = m.group(0) if m else ""

        # Gather candidates: builtins, special forms, :keywords + user-defined names in this buffer
        candidates = L.completion_candidates()
        content = t.get("1.0", "end-1c")
        for m2 in re.finditer(r"\(define\s+([\w\-+*/<>=!?]+)", content):
            candidates.add(m2.group(1))
        matches = sorted(c for c in candidates
                         if c.startswith(prefix)
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
# Inline find / replace bar
# =============================================================================
class SearchBar(tk.Frame):
    """An inline find/replace bar, shared by every editor buffer."""

    def __init__(self, master, app):
        super().__init__(master, bg=COLORS["side_bg"])
        self.app = app
        self.matches: list[tuple[int, int]] = []
        self.current_idx = -1

        # ---------- Row 1: Find ----------
        row1 = tk.Frame(self, bg=COLORS["side_bg"])
        row1.pack(fill="x", padx=6, pady=(5, 2))

        tk.Label(row1, text="Find:", bg=COLORS["side_bg"], fg="#ddd",
                 font=FONT_UI).pack(side="left")

        self.find_var = tk.StringVar()
        self.find_entry = tk.Entry(
            row1, textvariable=self.find_var,
            bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
            insertbackground="#fff", font=FONT_MONO,
            borderwidth=0, highlightthickness=1,
            highlightbackground="#333", highlightcolor=COLORS["prompt"])
        self.find_entry.pack(side="left", fill="x", expand=True,
                             padx=(6, 6), ipady=3)

        self.case_var  = tk.BooleanVar(value=False)
        self.word_var  = tk.BooleanVar(value=False)
        self.regex_var = tk.BooleanVar(value=False)
        for label, var in (("Aa", self.case_var),
                           ("W",  self.word_var),
                           (".*", self.regex_var)):
            tk.Checkbutton(
                row1, text=label, variable=var, command=self._refresh,
                bg=COLORS["side_bg"], fg="#ddd",
                selectcolor=COLORS["entry_bg"],
                activebackground=COLORS["side_bg"], activeforeground="#fff",
                font=FONT_UI, borderwidth=0, highlightthickness=0, padx=4,
            ).pack(side="left")

        for text, delta in (("▲", -1), ("▼", 1)):
            tk.Button(row1, text=text, command=lambda d=delta: self._nav(d),
                      bg=COLORS["side_bg"], fg="#ddd", font=FONT_UI,
                      borderwidth=0, padx=6, activebackground=COLORS["side_sel"]
                      ).pack(side="left", padx=(4, 0))

        tk.Button(row1, text="✕", command=self.hide_bar,
                  bg=COLORS["side_bg"], fg="#ddd", font=FONT_UI,
                  borderwidth=0, padx=6, activebackground=COLORS["side_sel"]
                  ).pack(side="left", padx=(4, 0))

        # ---------- Row 2: Replace ----------
        self.row2 = tk.Frame(self, bg=COLORS["side_bg"])

        tk.Label(self.row2, text="Repl:", bg=COLORS["side_bg"], fg="#ddd",
                 font=FONT_UI).pack(side="left")

        self.replace_var = tk.StringVar()
        self.replace_entry = tk.Entry(
            self.row2, textvariable=self.replace_var,
            bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
            insertbackground="#fff", font=FONT_MONO,
            borderwidth=0, highlightthickness=1,
            highlightbackground="#333", highlightcolor=COLORS["prompt"])
        self.replace_entry.pack(side="left", fill="x", expand=True,
                                padx=(6, 6), ipady=3)

        tk.Button(self.row2, text="Replace", command=self._replace_one,
                  bg=COLORS["side_bg"], fg="#ddd", font=FONT_UI,
                  borderwidth=0, padx=6, activebackground=COLORS["side_sel"]
                  ).pack(side="left", padx=(0, 4))
        tk.Button(self.row2, text="All", command=self._replace_all,
                  bg=COLORS["side_bg"], fg="#ddd", font=FONT_UI,
                  borderwidth=0, padx=6, activebackground=COLORS["side_sel"]
                  ).pack(side="left")

        # ---------- Status strip ----------
        self.status = tk.Label(self, text="", bg=COLORS["side_bg"],
                               fg="#888", font=FONT_UI, anchor="w")
        self.status.pack(fill="x", padx=8, pady=(0, 4))

        # ---------- Bindings ----------
        self.find_var.trace_add("write", lambda *a: self._refresh())
        self.find_entry.bind("<Return>",       lambda e: (self._nav(1),  "break")[1])
        self.find_entry.bind("<Shift-Return>", lambda e: (self._nav(-1), "break")[1])
        self.find_entry.bind("<Escape>",       lambda e: (self.hide_bar(), "break")[1])
        self.find_entry.bind("<Down>",         lambda e: (self._nav(1),  "break")[1])
        self.find_entry.bind("<Up>",           lambda e: (self._nav(-1), "break")[1])
        self.replace_entry.bind("<Return>",    lambda e: (self._replace_one(), "break")[1])
        self.replace_entry.bind("<Escape>",    lambda e: (self.hide_bar(), "break")[1])

    # ------------------------------------------------------------------ visibility
    def show_bar(self, with_replace: bool = False):
        if not self.winfo_ismapped():
            self.pack(side="top", fill="x", before=self.app.notebook)
        if with_replace:
            self.row2.pack(fill="x", padx=6, pady=(0, 6))
            self.replace_entry.focus_set()
            self.replace_entry.select_range(0, "end")
        else:
            self.row2.pack_forget()
            self.find_entry.focus_set()
            self.find_entry.select_range(0, "end")
        self._refresh()

    def hide_bar(self):
        self.pack_forget()
        self.app._clear_search_highlights()
        # give focus back to the current buffer
        tab = self.app.current_tab()
        if tab:
            tab.text.focus_set()

    # ------------------------------------------------------------------ finding
    def _pattern(self):
        raw = self.find_var.get()
        if not raw:
            return None
        pat = raw if self.regex_var.get() else re.escape(raw)
        if self.word_var.get():
            pat = r"\b" + pat + r"\b"
        flags = 0 if self.case_var.get() else re.IGNORECASE
        try:
            return re.compile(pat, flags)
        except re.error as e:
            self.status.configure(text=f"Bad pattern: {e}", fg=COLORS["error"])
            return None

    def _refresh(self, follow: bool = True):
        tab = self.app.current_tab()
        if tab is None:
            return
        content = tab.text.get("1.0", "end-1c")
        pat = self._pattern()
        self.matches = ([] if pat is None
                        else [(m.start(), m.end()) for m in pat.finditer(content)])

        # Draw "all matches" highlights
        tab.text.tag_remove("search_all",     "1.0", "end")
        tab.text.tag_remove("search_current", "1.0", "end")
        for s, e in self.matches:
            tab.text.tag_add("search_all",
                             offset_to_pos(content, s),
                             offset_to_pos(content, e))

        if not self.matches:
            self.current_idx = -1
            self.status.configure(
                text=("No matches" if self.find_var.get() else ""), fg="#888")
            return

        if not (0 <= self.current_idx < len(self.matches)):
            self.current_idx = 0
        if follow:
            self._goto_current()
        self.status.configure(text=f"{self.current_idx + 1} / {len(self.matches)}")

    def _goto_current(self):
        tab = self.app.current_tab()
        if tab is None or self.current_idx < 0:
            return
        content = tab.text.get("1.0", "end-1c")
        s, e = self.matches[self.current_idx]
        start = offset_to_pos(content, s)
        end   = offset_to_pos(content, e)

        t = tab.text
        t.tag_remove("search_current", "1.0", "end")
        t.tag_add("search_current", start, end)
        t.see(start)
        t.tag_remove("sel", "1.0", "end")
        t.tag_add("sel", start, end)

    def _nav(self, direction: int):
        if not self.matches:
            self._refresh()
            return
        self.current_idx = (self.current_idx + direction) % len(self.matches)
        self._goto_current()
        self.status.configure(text=f"{self.current_idx + 1} / {len(self.matches)}")

    # ------------------------------------------------------------------ replacing
    @staticmethod
    def _literal_repl(s: str) -> str:
        """Escape a replacement string so re.sub treats it literally."""
        return s.replace("\\", "\\\\")

    def _replace_one(self):
        tab = self.app.current_tab()
        if tab is None or self.current_idx < 0 or not self.matches:
            return
        content = tab.text.get("1.0", "end-1c")
        pat = self._pattern()
        if pat is None:
            return

        s, e = self.matches[self.current_idx]
        repl = self.replace_var.get()
        if self.regex_var.get():
            m = pat.match(content, s)
            new_text = m.expand(repl) if m else repl
        else:
            new_text = repl

        start = offset_to_pos(content, s)
        end   = offset_to_pos(content, e)
        tab.text.delete(start, end)
        tab.text.insert(start, new_text)
        tab.text.edit_modified(True)

        # Re-scan from scratch, then advance one step so we don't re-replace
        # the text we just wrote.
        self.current_idx = min(self.current_idx, max(0, len(self.matches) - 1))
        self._refresh(follow=False)
        self._nav(1)

    def _replace_all(self):
        tab = self.app.current_tab()
        if tab is None:
            return
        pat = self._pattern()
        if pat is None or not self.matches:
            self.status.configure(text="No matches", fg="#888")
            return

        content = tab.text.get("1.0", "end-1c")
        repl = self.replace_var.get()
        if not self.regex_var.get():
            repl = self._literal_repl(repl)
        new_content, count = pat.subn(repl, content)

        # Single delete + insert so it's one undo step.
        tab.text.delete("1.0", "end")
        tab.text.insert("1.0", new_content)
        tab.text.edit_modified(True)

        self.current_idx = -1
        self._refresh(follow=False)
        self.status.configure(text=f"Replaced {count} occurrence(s)")
        
# =============================================================================
# Main application
# =============================================================================
def read_file_arg(arg: str):
    """Return (buffer name, content, path) for a file named on the command line.

    A file that does not exist yet gives an empty buffer that saves to that
    path; any other read error is raised as OSError.
    """
    path = os.path.abspath(arg)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    return os.path.basename(path), content, path


DEMO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.lisp")


def read_demo(path=DEMO_FILE):
    """Return (buffer name, content, path) for the buffer opened when no file
    is named on the command line: demo.lisp, or an empty untitled buffer if
    it is missing or unreadable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return os.path.basename(path), f.read(), path
    except (OSError, UnicodeDecodeError):
        return "untitled.lisp", "", None


# =============================================================================
# Help window: the Lispy guide (docs/*.md and the built-ins), searchable
# =============================================================================
class GuideWindow(tk.Toplevel):
    """The Lispy guide in its own window: pages, their contents, a search box."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Lispy Guide")
        self.geometry("1000x720")
        self.configure(bg=COLORS["bg"])
        self.page = None
        self.rendered = None
        self.history: list[tuple[str, str]] = []   # (page, index) to go Back to
        self.matches: list[int] = []
        self.match_idx = -1
        self._page_cache: dict[str, guide.Rendered] = {}
        self._build()
        self.bind("<Escape>", lambda e: self._escape())
        self.bind("<Control-f>", lambda e: (self.search.focus_set(), self.search.select_range(0, "end"), "break")[2])
        self.bind("<F3>", lambda e: (self._nav(1), "break")[1])
        self.bind("<Shift-F3>", lambda e: (self._nav(-1), "break")[1])
        self.bind("<Alt-Left>", lambda e: (self.back(), "break")[1])

    # ---------- layout ----------
    def _build(self):
        top = tk.Frame(self, bg=COLORS["side_bg"])
        top.pack(side="top", fill="x")
        self.back_btn = tk.Button(top, text="◀ Back", command=self.back, state="disabled",
                                  bg=COLORS["side_bg"], fg=COLORS["side_fg"], relief="flat",
                                  activebackground=COLORS["side_sel"], font=FONT_UI)
        self.back_btn.pack(side="left", padx=6, pady=4)
        tk.Label(top, text="Search:", bg=COLORS["side_bg"], fg=COLORS["side_fg"],
                 font=FONT_UI).pack(side="left", padx=(12, 4))
        self.search_var = tk.StringVar(self)
        self.search = tk.Entry(top, textvariable=self.search_var, width=30, font=FONT_MONO,
                               bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
                               insertbackground=COLORS["cursor"], relief="flat")
        self.search.pack(side="left", pady=4)
        self.search_var.trace_add("write", lambda *a: self._refresh_search())
        self.search.bind("<Return>", lambda e: (self._nav(1), "break")[1])
        self.search.bind("<Shift-Return>", lambda e: (self._nav(-1), "break")[1])
        self.search.bind("<Down>", lambda e: (self._nav(1), "break")[1])
        self.search.bind("<Up>", lambda e: (self._nav(-1), "break")[1])
        self.search_info = tk.Label(top, text="", bg=COLORS["side_bg"], fg="#888",
                                    font=FONT_UI, anchor="w")
        self.search_info.pack(side="left", padx=8, fill="x", expand=True)

        pane = tk.PanedWindow(self, orient="horizontal", bg=COLORS["bg"],
                              sashwidth=5, sashrelief="flat", opaqueresize=True)
        pane.pack(fill="both", expand=True)
        side = tk.Frame(pane, bg=COLORS["side_bg"])
        pane.add(side, minsize=140, width=250, stretch="never")

        tk.Label(side, text="PAGES", bg=COLORS["side_bg"], fg="#888",
                 font=FONT_UI_BOLD, anchor="w", padx=8, pady=4).pack(fill="x")
        self.page_list = tk.Listbox(side, height=len(guide.PAGES), bg=COLORS["side_bg"],
                                    fg=COLORS["side_fg"], selectbackground=COLORS["side_sel"],
                                    selectforeground="#ffffff", font=FONT_UI, relief="flat",
                                    highlightthickness=0, activestyle="none", exportselection=False)
        for title, _ in guide.PAGES:
            self.page_list.insert("end", "  " + title)
        self.page_list.pack(fill="x")
        self.page_list.bind("<<ListboxSelect>>", self._on_page_select)

        tk.Label(side, text="CONTENTS", bg=COLORS["side_bg"], fg="#888",
                 font=FONT_UI_BOLD, anchor="w", padx=8, pady=4).pack(fill="x", pady=(8, 0))
        self.toc = tk.Listbox(side, bg=COLORS["side_bg"], fg=COLORS["side_fg"],
                              selectbackground=COLORS["side_sel"], selectforeground="#ffffff",
                              font=FONT_UI, relief="flat", highlightthickness=0,
                              activestyle="none", exportselection=False)
        self.toc.pack(fill="both", expand=True)
        self.toc.bind("<<ListboxSelect>>", self._on_toc_select)

        self.text = ScrolledText(pane, wrap="word", bg=COLORS["bg"], fg=COLORS["fg"],
                                 font=("Segoe UI", 11), relief="flat", padx=18, pady=12,
                                 insertbackground=COLORS["cursor"], selectbackground=COLORS["selection"],
                                 spacing1=1, spacing3=2, cursor="arrow")
        pane.add(self.text, minsize=300, stretch="always")
        self._setup_tags()
        # Read-only, but text can still be selected and copied
        self.text.bind("<Key>", lambda e: None if (e.state & 0x4 and e.keysym.lower() in ("c", "a"))
                       or e.keysym in ("Up", "Down", "Prior", "Next", "Home", "End") else "break")

    def _setup_tags(self):
        t = self.text
        t.tag_configure("h1", font=("Segoe UI", 20, "bold"), foreground="#ffffff", spacing1=6, spacing3=10)
        t.tag_configure("h2", font=("Segoe UI", 15, "bold"), foreground=COLORS["prompt"], spacing1=14, spacing3=6)
        t.tag_configure("h3", font=("Segoe UI", 12, "bold"), foreground=COLORS["info"], spacing1=10, spacing3=4)
        t.tag_configure("bold", font=("Segoe UI", 11, "bold"), foreground="#ffffff")
        t.tag_configure("code", font=FONT_MONO, foreground="#ce9178")
        t.tag_configure("codeblock", font=FONT_MONO, background="#2a2a2a", foreground=COLORS["fg"],
                        lmargin1=16, lmargin2=16, wrap="none")
        t.tag_configure("table", font=FONT_MONO)
        t.tag_configure("tablehead", font=FONT_MONO_BOLD, foreground="#ffffff")
        t.tag_configure("rule", font=("Segoe UI", 2), background="#444")
        t.tag_configure("item0", lmargin1=8, lmargin2=24)
        t.tag_configure("item1", lmargin1=28, lmargin2=44)
        t.tag_configure("item2", lmargin1=48, lmargin2=64)
        t.tag_configure("link", foreground="#3794ff", underline=True)
        t.tag_bind("link", "<Enter>", lambda e: t.configure(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.configure(cursor="arrow"))
        t.tag_configure("found", background="#613214")
        t.tag_configure("found_current", background="#a8650e", foreground="#ffffff")
        t.tag_raise("found")
        t.tag_raise("found_current")
        setup_code_tags(t)
        self._char_width = tkfont.Font(font=FONT_MONO).measure("0")

    # ---------- showing pages ----------
    def show(self, page: str = guide.PAGES[0][0], anchor: str | None = None, remember: bool = True):
        """Show `page` (a title from guide.PAGES), at the heading `anchor` if given."""
        if remember and self.page is not None:
            self.history.append((self.page, self.text.index("@0,0")))
            self.back_btn.configure(state="normal")
        if page != self.page:
            self._load(page)
        if anchor and anchor in self.rendered.anchors:
            self._goto_offset(self.rendered.anchors[anchor])
        elif not anchor:
            self.text.yview_moveto(0)
        self.deiconify()
        self.lift()

    def _load(self, page: str):
        if page not in self._page_cache:
            self._page_cache[page] = guide.render(guide.load_page(page, L.HELP_TOPICS))
        self.page, self.rendered = page, self._page_cache[page]
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        links = 0
        for text, tags, link in self.rendered.runs:
            tags = list(tags)
            for tag in tags:
                if tag.startswith("hang") and tag not in t.tag_names():
                    t.tag_configure(tag, lmargin2=int(tag[4:]) * self._char_width)
            if link is not None:
                links += 1
                name = f"link{links}"
                tags.append(name)
                t.tag_bind(name, "<Button-1>", lambda e, target=link: self.follow(target))
            start = t.index("end-1c")
            t.insert("end", text, tuple(tags))
            if "codeblock" in tags:
                color_code(t, start, text)
        self.title(f"Lispy Guide: {page}")
        titles = [title for title, _ in guide.PAGES]
        self.page_list.selection_clear(0, "end")
        self.page_list.selection_set(titles.index(page))
        self.toc.delete(0, "end")
        for level, title, _, _ in self.rendered.headings:
            self.toc.insert("end", "    " * max(level - 1, 0) + title)
        self._refresh_search(follow=False)

    def _goto_offset(self, offset: int):
        index = f"1.0+{offset}c"
        self.text.yview(index)
        self.text.mark_set("insert", index)

    def follow(self, target: str):
        """Open a link: another guide page, a heading, or a web page."""
        if target.startswith(("http://", "https://")):
            import webbrowser
            webbrowser.open(target)
            return
        path, _, anchor = target.partition("#")
        page = guide.page_for_file(path) if path else self.page
        if page is None:
            full = os.path.normpath(os.path.join(guide.DOCS_DIR, path))
            if os.path.exists(full):
                import webbrowser
                webbrowser.open("file://" + full)
            return
        self.show(page, anchor or None)

    def back(self):
        if not self.history:
            return
        page, index = self.history.pop()
        if page != self.page:
            self._load(page)
        self.text.yview(index)
        if not self.history:
            self.back_btn.configure(state="disabled")

    def _on_page_select(self, event=None):
        sel = self.page_list.curselection()
        if sel and guide.PAGES[sel[0]][0] != self.page:
            self.show(guide.PAGES[sel[0]][0])

    def _on_toc_select(self, event=None):
        sel = self.toc.curselection()
        if sel:
            self._goto_offset(self.rendered.headings[sel[0]][3])

    def show_name(self, name: str) -> bool:
        """Show the Built-ins page at the line for `name`; False if it is not there."""
        self.show(guide.BUILTINS_PAGE)
        line = guide.find_name(self.rendered.text, name)
        if line is None:
            return False
        self._goto_offset(line)
        self.text.tag_remove("found_current", "1.0", "end")
        self.text.tag_add("found_current", f"1.0+{line}c", f"1.0+{line + len(name)}c")
        return True

    # ---------- search ----------
    def _refresh_search(self, follow: bool = True):
        t = self.text
        t.tag_remove("found", "1.0", "end")
        t.tag_remove("found_current", "1.0", "end")
        needle = self.search_var.get()
        self.matches = guide.find_all(self.rendered.text, needle) if self.rendered else []
        for pos in self.matches:
            t.tag_add("found", f"1.0+{pos}c", f"1.0+{pos + len(needle)}c")
        self.match_idx = -1
        if self.matches and follow:
            self._nav(1)
        else:
            self._show_search_info()

    def _nav(self, direction: int):
        if not self.matches:
            others = self._matches_elsewhere()
            if others and direction > 0:
                self.show(others[0][0])          # jump to the next page that has it
                if self.matches:
                    self._nav(1)
            return
        self.match_idx = (self.match_idx + direction) % len(self.matches)
        pos, n = self.matches[self.match_idx], len(self.search_var.get())
        t = self.text
        t.tag_remove("found_current", "1.0", "end")
        t.tag_add("found_current", f"1.0+{pos}c", f"1.0+{pos + n}c")
        t.see(f"1.0+{pos}c")
        self._show_search_info()

    def _matches_elsewhere(self):
        """(page, count) for the other pages that contain the search text."""
        needle = self.search_var.get()
        if not needle:
            return []
        found = []
        titles = [title for title, _ in guide.PAGES]
        start = titles.index(self.page) if self.page in titles else 0
        for title in titles[start + 1:] + titles[:start]:
            if title not in self._page_cache:
                self._page_cache[title] = guide.render(guide.load_page(title, L.HELP_TOPICS))
            count = len(guide.find_all(self._page_cache[title].text, needle))
            if count:
                found.append((title, count))
        return found

    def _show_search_info(self):
        if not self.search_var.get():
            self.search_info.configure(text="")
            return
        here = (f"{self.match_idx + 1} of {len(self.matches)}" if self.matches and self.match_idx >= 0
                else f"{len(self.matches)} here" if self.matches else "not on this page")
        others = self._matches_elsewhere()
        if others:
            here += "   also in: " + ", ".join(f"{p} ({n})" for p, n in others)
            if not self.matches:
                here += "   (Enter goes there)"
        self.search_info.configure(text=here)

    def _escape(self):
        if self.search_var.get():
            self.search_var.set("")
        else:
            self.withdraw()


WM_CLASS = "LispyMachine"


class LispMachine(tk.Tk):
    def __init__(self, files=(), plain_repl=None):
        # The window class lets Linux docks match the window to the
        # lispy-machine.desktop launcher (StartupWMClass) and show its icon.
        super().__init__(className=WM_CLASS)
        self.title("Lispy3 Machine")
        self._set_icon()
        self.geometry("1280x820")
        self.configure(bg=COLORS["bg"])
        self.minsize(900, 600)

        # state
        self.tabs: dict[str, EditorTab] = {}       # name -> EditorTab
        self.tab_order: list[str] = []
        self.listener_history: list[str] = []
        self.listener_hist_idx = 0
        self._welcome_done = False
        self.settings = load_settings()
        if plain_repl is None:
            plain_repl = bool(self.settings.get("plain_repl", False))
        self.plain_repl = tk.BooleanVar(self, value=plain_repl)
        self.repl_pending = ""      # lines of an unfinished form in the plain REPL
        self.console_ready = False  # the plain REPL prompt is showing, waiting for input
        self.update_pending = False # Help > Update pulled a new version, not running yet
        self.guide_window = None    # the Help window, made the first time it is opened
        L.global_env['help'] = self.lisp_help

        self._setup_style()
        self._build_menu()
        self._build_layout()
        self._build_status()
        self._bind_global()

        # files from the command line, or demo.lisp
        open_errors = []
        for arg in files:
            try:
                name, content, path = read_file_arg(arg)
            except (OSError, UnicodeDecodeError) as e:
                open_errors.append(f"{arg}: {e}")
                continue
            self.new_buffer(name, content, path=path)
        if not self.tabs:
            name, content, path = read_demo()
            self.new_buffer(name, content, path=path)

        self.listener_write(";; Lispy3 Machine ready.\n", "info")
        self.listener_write(";; F5 = eval form at cursor,  F6 = eval buffer,  F9 = eval listener input.\n", "info")
        self.listener_write(";; Ctrl+Space completes a symbol.  Try `(load \"lsystems\")`.\n", "info")
        self.listener_write(";; View > Plain lispy3 REPL switches the Listener to the lispy3 prompt.\n\n", "info")
        for err in SYNTAX_ERRORS:
            self.listener_write(f";; Syntax colouring file not loaded: {err}\n", "error")
        for err in open_errors:
            self.listener_write(f";; Could not open {err}\n", "error")
        self._apply_repl_mode()
        self._focus_listener()
        self.refresh_definitions()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- window icon ----------
    def _set_icon(self):
        """Use icons/lispy_machine.ico (Windows) or .png (Linux, macOS) as the icon.

        On Windows only the icon picture changes: the taskbar button still
        belongs to Python, so its list of recently opened files keeps working. A missing
        or unreadable icon file just leaves the default icon.
        """
        icons = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        try:
            if sys.platform == "win32":
                self.iconbitmap(default=os.path.join(icons, "lispy_machine.ico"))
            else:
                self._icon_image = tk.PhotoImage(file=os.path.join(icons, "lispy_machine.png"))
                self.iconphoto(True, self._icon_image)
                # WSLg (Linux apps on Windows) reads the icon only when it changes
                # after the window is on screen, so set it again on every map.
                self.bind("<Map>", self._reset_icon, add="+")
                self.bind_class("Toplevel", "<Map>", self._reset_icon, add="+")
        except tk.TclError:
            pass

    def _reset_icon(self, event):
        window = event.widget
        if not isinstance(window, (tk.Tk, tk.Toplevel)):
            return      # a widget inside the window was mapped, not the window

        def again():
            try:
                window.iconphoto(False, self._icon_image)
            except tk.TclError:
                pass    # the window closed in the meantime
        self.after(300, again)

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
        style.configure("Inspector.Treeview", background=COLORS["bg"], fieldbackground=COLORS["bg"],
                        foreground=COLORS["side_fg"], font=FONT_MONO, borderwidth=0, rowheight=20)
        style.map("Inspector.Treeview", background=[("selected", COLORS["selection"])],
                  foreground=[("selected", "#ffffff")])

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
        eval_m.add_command(label="Inspect symbol at cursor", accelerator="F7", command=self.inspect_at_cursor)
        eval_m.add_separator()
        eval_m.add_command(label="Eval listener input", accelerator="F9",     command=self._listener_submit)
        eval_m.add_separator()
        eval_m.add_command(label="Listener to buffer",  command=self.listener_to_buffer)
        eval_m.add_command(label="Clear listener",      accelerator="Ctrl+L", command=self.clear_listener)
        bar.add_cascade(label="Eval", menu=eval_m)

        view_m = tk.Menu(bar, tearoff=0)
        view_m.add_command(label="Reload lsystems",     command=lambda: self._run_silent('(load "lsystems")'))
        view_m.add_command(label="Show global env",     command=self._show_env)
        view_m.add_separator()
        view_m.add_command(label="Open terminal",      command=self.open_terminal)
        view_m.add_command(label="Focus listener",      accelerator="Ctrl+E", command=self._focus_listener)
        view_m.add_checkbutton(label="Plain lispy3 REPL", variable=self.plain_repl,
                               command=self._toggle_plain_repl)
        bar.add_cascade(label="View", menu=view_m)

        help_m = tk.Menu(bar, tearoff=0)
        help_m.add_command(label="Lispy guide", accelerator="F1", command=self.open_guide)
        help_m.add_command(label="Built-in functions", command=lambda: self.open_guide(guide.BUILTINS_PAGE))
        help_m.add_separator()
        help_m.add_command(label="Update", command=self._update)
        help_m.add_command(label="About", command=self._about)
        bar.add_cascade(label="Help", menu=help_m)

        self.config(menu=bar)

    def _listener_complete(self, event=None):
        """Ctrl+Space: complete the name being typed, with a list when several fit."""
        console = self.plain_repl.get()
        if console:                                  # the plain REPL types into the Listener text
            t = self.listener_text
            if not self.console_ready:
                return "break"
            if t.compare("insert", "<", "input"):
                t.mark_set("insert", "end-1c")
            widget, before = t, t.get("input", "insert")
        else:
            widget = self.listener_input
            before = widget.get()[:widget.index("insert")]

        def put(text):
            widget.insert("insert", text)
            if console:
                self._console_recolor()
            widget.focus_force()          # back from the popup to where you type

        m = SYMBOL_TAIL.search(before)
        prefix = m.group(0) if m else ""
        
        matches = [c for c in L.complete_names(prefix) if c != prefix]
        if not matches:
            return "break"
        if len(matches) == 1:
            put(matches[0][len(prefix):])
            return "break"
            
        # Popup listbox for listener
        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.configure(bg="#333")
        box = widget.bbox("insert") if console else None
        if box:                                      # just under the cursor in the Listener text
            x = widget.winfo_rootx() + box[0]
            y = widget.winfo_rooty() + box[1] + box[3]
            if y + 200 > self.winfo_screenheight():   # no room below: open above the line
                y = widget.winfo_rooty() + box[1] - 20 * min(10, len(matches)) - 4
        else:
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() - 120
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
            popup.destroy()
            if sel:
                put(matches[sel[0]][len(prefix):])
            else:
                widget.focus_force()

        lb.bind("<Return>", choose)
        lb.bind("<Double-Button-1>", choose)
        lb.bind("<Escape>", lambda e: (popup.destroy(), widget.focus_force()))
        popup.bind("<FocusOut>", lambda e: popup.destroy())
        lb.focus_set()
        lb.selection_set(0)
        return "break"
    
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
        # Both dividers are draggable: sidebar | editor, and buffers / inspector.
        hpane = tk.PanedWindow(top, orient="horizontal", bg=COLORS["bg"],
                               sashwidth=5, sashrelief="flat", opaqueresize=True)
        hpane.pack(fill="both", expand=True)

        sidebar = tk.PanedWindow(hpane, orient="vertical", bg=COLORS["bg"],
                                 sashwidth=5, sashrelief="flat", opaqueresize=True)
        hpane.add(sidebar, minsize=120, width=300, stretch="never")

        buf_frame = tk.Frame(sidebar, bg=COLORS["side_bg"])
        sidebar.add(buf_frame, minsize=50, height=150, stretch="never")
        insp_outer = tk.Frame(sidebar, bg=COLORS["side_bg"])
        sidebar.add(insp_outer, minsize=60, stretch="always")

        tk.Label(buf_frame, text="BUFFERS", bg=COLORS["side_bg"], fg="#888",
                 font=FONT_UI_BOLD, anchor="w", padx=8, pady=4).pack(fill="x")

        self.buffer_list = tk.Listbox(
            buf_frame, bg=COLORS["side_bg"], fg=COLORS["side_fg"],
            selectbackground=COLORS["side_sel"], selectforeground="#ffffff",
            borderwidth=0, highlightthickness=0, activestyle="none",
            font=FONT_UI, height=4)
        self.buffer_list.pack(fill="both", expand=True, padx=4)
        self.buffer_list.bind("<<ListboxSelect>>", self._on_buffer_select)

        tk.Label(insp_outer, text="INSPECTOR", bg=COLORS["side_bg"], fg="#888",
                 font=FONT_UI_BOLD, anchor="w", padx=8, pady=4).pack(fill="x")

        # Your definitions above, the chosen one's value below
        insp_pane = tk.PanedWindow(insp_outer, orient="vertical", bg=COLORS["side_bg"],
                                   sashwidth=5, sashrelief="flat", opaqueresize=True)
        insp_pane.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        tree_frame = tk.Frame(insp_pane, bg=COLORS["side_bg"])
        insp_pane.add(tree_frame, minsize=40, height=140, stretch="never")
        self.def_tree = ttk.Treeview(tree_frame, columns=("value",), show="tree",
                                     style="Inspector.Treeview", selectmode="browse")
        self.def_tree.column("#0", width=110, stretch=False)
        self.def_tree.column("value", width=160, stretch=True)
        tree_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.def_tree.yview)
        self.def_tree.configure(yscrollcommand=tree_y.set)
        tree_y.pack(side="right", fill="y")
        self.def_tree.pack(side="left", fill="both", expand=True)
        self.def_tree.bind("<<TreeviewSelect>>", self._on_definition_select)
        self._tree_job = None

        insp_frame = tk.Frame(insp_pane, bg=COLORS["side_bg"])
        insp_pane.add(insp_frame, minsize=40, stretch="always")
        insp_y = ttk.Scrollbar(insp_frame, orient="vertical")
        insp_x = ttk.Scrollbar(insp_frame, orient="horizontal")
        self.inspector = tk.Text(
            insp_frame, bg=COLORS["bg"], fg=COLORS["fg"], font=FONT_MONO,
            wrap="none", borderwidth=0, highlightthickness=0, height=10,
            padx=6, pady=4, yscrollcommand=insp_y.set, xscrollcommand=insp_x.set)
        insp_y.configure(command=self.inspector.yview)
        insp_x.configure(command=self.inspector.xview)
        insp_x.pack(side="bottom", fill="x")
        insp_y.pack(side="right", fill="y")
        self.inspector.pack(side="left", fill="both", expand=True)
        setup_code_tags(self.inspector)
        self.inspector.insert("1.0", "(no value yet)")
        self.inspector.configure(state="disabled")

        # ---- right-hand area: search bar (hidden) + editor notebook ----
        right_area = tk.Frame(hpane, bg=COLORS["bg"])
        hpane.add(right_area, minsize=200, stretch="always")

        self.search_bar = SearchBar(right_area, self)   # not packed yet

        self.notebook = ttk.Notebook(right_area)
        self.notebook.pack(side="top", fill="both", expand=True)
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
        tk.Button(hdr, text="To buffer", bg=COLORS["side_bg"], fg="#ddd",
                  font=FONT_UI, borderwidth=0, padx=8,
                  command=self.listener_to_buffer).pack(side="right", padx=4, pady=2)

        self.listener_text = ScrolledText(
            listener_frame, bg=COLORS["listener_bg"], fg=COLORS["fg"],
            font=FONT_MONO, wrap="word", height=8,
            insertbackground=COLORS["cursor"], insertwidth=2,   # visible on the dark background
            borderwidth=0, highlightthickness=0, padx=8, pady=4)
        self.listener_text.pack(fill="both", expand=True)
        self.listener_text.configure(state="disabled")
        self.listener_text.tag_configure("prompt", foreground=COLORS["prompt"], font=FONT_MONO_BOLD)
        self.listener_text.tag_configure("result", foreground=COLORS["result"])
        self.listener_text.tag_configure("error",  foreground=COLORS["error"])
        self.listener_text.tag_configure("info",   foreground=COLORS["info"])
        setup_code_tags(self.listener_text)

        # Plain REPL keys; in Listener mode the text is read-only and keeps its usual keys
        for seq, handler in (("<Return>", self._console_return),
                             ("<KP_Enter>", self._console_return),
                             ("<Tab>", self._listener_tab),
                             ("<Control-space>", self._listener_complete),
                             ("<Escape>", self._cancel_pending),
                             ("<Up>", lambda e: self._console_history(-1)),
                             ("<Down>", lambda e: self._console_history(1)),
                             ("<Home>", self._console_home),
                             ("<Left>", self._console_left),
                             ("<ButtonRelease-1>", self._console_click),
                             ("<KeyRelease>", self._console_recolor),
                             ("<Key>", self._console_key),
                             ("<<Paste>>", self._console_paste),
                             ("<<Cut>>", self._console_cut),
                             ("<Control-l>", lambda e: (self.clear_listener(), "break")[1])):
            self.listener_text.bind(seq, lambda e, h=handler: h(e) if self.plain_repl.get() else None)

        self.input_row = input_row = tk.Frame(listener_frame, bg=COLORS["listener_bg"])
        input_row.pack(fill="x", padx=6, pady=(0, 6))
        self.prompt_label = tk.Label(input_row, text="USER>", bg=COLORS["listener_bg"],
                                     fg=COLORS["prompt"], font=FONT_MONO_BOLD)
        self.prompt_label.pack(side="left", padx=(2, 6))
        self.listener_input = tk.Entry(
            input_row, bg=COLORS["entry_bg"], fg=COLORS["entry_fg"],
            insertbackground="#fff", font=FONT_MONO, borderwidth=0,
            highlightthickness=1, highlightbackground="#333",
            highlightcolor=COLORS["prompt"])
        self.listener_input.pack(side="left", fill="x", expand=True, ipady=4)
        self.listener_input.bind("<Return>",  lambda e: (self._listener_submit(), "break")[1])
        self.listener_input.bind("<Control-space>", self._listener_complete)
        self.listener_input.bind("<Control-Key-space>", self._listener_complete)
        self.listener_input.bind("<Up>",      self._history_up)
        self.listener_input.bind("<Down>",    self._history_down)
        self.listener_input.bind("<Control-l>", lambda e: (self.clear_listener(), "break")[1])

    def _build_status(self):
        pass  # placeholder

    def _bind_global(self):
        self.bind_all("<F1>", lambda e: (self.open_guide(), "break")[1])
        self.bind_all("<F7>", lambda e: (self.inspect_at_cursor(), "break")[1])
        self.bind_all("<Control-n>", lambda e: self.new_buffer_dialog())
        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_current())
        self.bind_all("<Control-Shift-S>", lambda e: self.save_current_as())
        self.bind_all("<Control-w>", lambda e: self.close_current())
        self.bind_all("<Control-q>", lambda e: self._on_close())
        self.bind_all("<Control-e>", lambda e: self._focus_listener())
        self.bind_all("<Control-f>",  lambda e: (self.search_bar.show_bar(False), "break")[1])
        self.bind_all("<Control-h>",  lambda e: (self.search_bar.show_bar(True),  "break")[1])
        self.bind_all("<F3>",         lambda e: (self.search_bar._nav(1),  "break")[1])
        self.bind_all("<Shift-F3>",   lambda e: (self.search_bar._nav(-1), "break")[1])

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
        # Refresh search highlights for the new buffer, or clear them.
        if self.search_bar.winfo_ismapped():
            self.search_bar.current_idx = -1
            self.search_bar._refresh(follow=False)
        else:
            self._clear_search_highlights()
            
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
            filetypes=[("Lisp", "*.lisp"), ("Python", "*.py *.pyw"), ("All files", "*.*")])
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
            filetypes=[("Lisp", "*.lisp"), ("Python", "*.py *.pyw"), ("All files", "*.*")])
        if not path:
            return
        tab.path = path
        tab.name = os.path.basename(path)
        self.tab_order = [tab.name if n == tab.name else n for n in self.tab_order]
        self.notebook.tab(tab, text=tab.name)
        tab.set_language()
        self.save_current()
        self._refresh_buffer_list()

    # =========================================================================
    # Evaluation
    # =========================================================================
    def _run(self, code: str):
        """Evaluate `code`. Returns (value, error). Stdout is streamed to the Listener."""
        import turtle as _turtle

        # The turtle Screen is a process-wide singleton whose _RUNNING flag
        # can be flipped to False by transient WM events when a second Tk
        # root (the editor) exists in the same process. Force it back on
        # before every evaluation.
        _turtle.TurtleScreen._RUNNING = True

        writer = _ListenerWriter(self)
        try:
            with contextlib.redirect_stdout(writer):
                ast = L.parse(code)
                val = L.eval_exp(ast, L.global_env)
            return val, None
        except _turtle.Terminator:
            # Same transient condition; the window is actually alive.
            _turtle.TurtleScreen._RUNNING = True
            try:
                writer = _ListenerWriter(self)
                with contextlib.redirect_stdout(writer):
                    ast = L.parse(code)
                    val = L.eval_exp(ast, L.global_env)
                return val, None
            except _turtle.Terminator:
                # A genuine close — invite the user to reopen.
                return None, RuntimeError(
                    "Turtle window was closed. Use (reinit-turtle) or reopen it.")
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
            # An unclosed form: write the brackets the reader would add into the buffer
            closed, closers = L.auto_close(content)
            span = find_top_level_form(closed, offset) if closers else None
            if span is None:
                self.listener_write(";; No form at cursor.\n", "error")
                return
            content = self._write_closers(tab, content, closers)
        start, end = span
        form = content[start:end]
        self.listener_write("USER> ", "prompt")
        self.listener_write(f"{form.strip()}\n", "code")
        val, err = self._run(form)
        self._report_eval(val, err, code=form)

    def _write_closers(self, tab, content: str, closers: str) -> str:
        """Put the missing `closers` at the end of the last code line and say so."""
        pos = L.close_position(content)
        index = offset_to_pos(content, pos)
        tab.text.insert(index, closers)
        tab._schedule_highlight()
        self.listener_write(f";; added {closers} at the end of line {index.split('.')[0]}\n", "info")
        return content[:pos] + closers + content[pos:]

    def _parse_top_level_forms(self, content: str):
        """Split buffer text into a list of top-level forms using the interpreter's own parser."""
        tokens = L.tokenize(content)
        forms = []
        while tokens:
            forms.append(L.read_from_tokens(tokens))
        return forms

    def eval_buffer(self):
        tab = self.current_tab()
        if not tab:
            return
        content = tab.get_content()
        self.listener_write(f";; --- evaluating {tab.name} ---\n", "info")
        closers = L.missing_closers(content)
        if closers:
            content = self._write_closers(tab, content, closers)

        if not content.strip():
            self.listener_write(";; (empty buffer)\n", "info")
            self.listener_write(";; --- done ---\n", "info")
            return

        try:
            forms = self._parse_top_level_forms(content)
        except Exception as e:                       # noqa: BLE001
            self.listener_write(f"Parse error: {e}\n", "error")
            self.listener_write(";; --- done ---\n", "info")
            return

        writer = _ListenerWriter(self)
        for form in forms:
            try:
                form_str = L.lisp_str(form)
            except Exception:
                form_str = repr(form)
            if len(form_str) > 120:
                form_str = form_str[:117] + "..."
            self.listener_write("USER> ", "prompt")
            self.listener_write(f"{form_str}\n", "code")

            try:
                with contextlib.redirect_stdout(writer):
                    val = L.eval_exp(form, L.global_env)
            except Exception as e:                   # noqa: BLE001
                self.listener_write(f"Error: {e}\n", "error")
                self.set_inspector(f"Error: {e}")
                self.listener_write(";; --- aborted ---\n", "info")
                return

            if val is None:
                name = self._defined_name(form)
                if name:
                    self.listener_write(f";; {name} defined\n", "info")
                    self.inspect_symbol(name)
                else:
                    self.listener_write(";; ok\n", "info")
                    self.set_inspector("(none)")
            else:
                try:
                    val_str = L.lisp_str(val)
                except Exception:
                    val_str = repr(val)
                self.listener_write(self._fmt_result(val, val_str) + "\n", "code")
                try:
                    self.set_inspector(L.pretty_print(val, width=self._inspector_cols()))
                except Exception:
                    self.set_inspector(val_str)

        self.listener_write(";; --- done ---\n", "info")

    @staticmethod
    def _defined_name(code):
        """Name from a (define name ...) form (source text or parsed form), else None."""
        try:
            form = L.parse(code) if isinstance(code, str) else code
        except Exception:                            # noqa: BLE001
            return None
        if isinstance(form, list) and len(form) >= 2 and form[0] == 'define' and isinstance(form[1], str):
            return form[1]
        return None

    def _fmt_result(self, val, flat):
        """Listener text for a value: functions and long structures are shown in full."""
        try:
            import tkinter.font as tkfont
            char_w = tkfont.Font(font=self.listener_text.cget("font")).measure("0") or 8
            cols = max(40, (self.listener_text.winfo_width() - 24) // char_w)
            text = L.pretty_print(val, width=cols)
            return text if text.strip() else flat
        except Exception:                            # noqa: BLE001
            return flat

    def _inspector_cols(self):
        """Text columns that fit in the Inspector now (follows the draggable divider)."""
        try:
            import tkinter.font as tkfont
            self.update_idletasks()
            char_w = tkfont.Font(font=self.inspector.cget("font")).measure("0") or 8
            return max(20, (self.inspector.winfo_width() - 16) // char_w)
        except Exception:                            # noqa: BLE001
            return 34

    def inspect_symbol(self, name):
        """Show the global variable `name` in the Inspector, pretty-printed."""
        try:
            val = L.global_env[name]
        except KeyError:
            self.set_inspector(f"{name}: undefined")
            return False
        try:
            text = L.pretty_print(val, width=self._inspector_cols())
        except Exception:                            # noqa: BLE001
            text = repr(val)
        if type(val).__name__ == 'Procedure' and text.startswith('(define'):
            self.set_inspector(text)
        else:
            self.set_inspector(f"{name} =\n{text}")
        return True

    def inspect_at_cursor(self):
        """F7: inspect the symbol under the editor cursor, or the name typed in the Listener."""
        name = ""
        if self.focus_get() is self.listener_input:
            name = self.listener_input.get().strip()
        elif self.focus_get() is self.listener_text and self.console_ready:
            name = self._console_input().strip()
        else:
            tab = self.current_tab()
            if tab:
                t = tab.text
                line = t.get("insert linestart", "insert lineend")
                col = int(t.index("insert").split(".")[1])
                stop = " \t()[]{}'\""
                a = col
                while a > 0 and line[a - 1] not in stop:
                    a -= 1
                b = col
                while b < len(line) and line[b] not in stop:
                    b += 1
                name = line[a:b]
        if name:
            self.inspect_symbol(name)

    def _report_eval(self, val, err, show_value=True, code=None, plain=False):
        """Show a result. `plain` prints it as lispy3.py's REPL does: nothing for None, no notes."""
        if err is not None:
            msg = str(err) or type(err).__name__
            if isinstance(err, RecursionError):
                msg = L.RECURSION_HINT
            self.listener_write(f"Error: {msg}\n", "error")
            self.set_inspector(f"Error: {msg}")
            return
        name = self._defined_name(code) if code is not None else None
        if name and val is None:
            if not plain:
                self.listener_write(f";; {name} defined\n", "info")
            self.inspect_symbol(name)
            return
        try:
            val_str = L.lisp_str(val)
        except Exception:
            val_str = repr(val)
        if plain:
            if val is not None:                  # long values are pretty-printed to the Listener width
                self.listener_write(self._fmt_result(val, val_str) + "\n", "code")
        elif show_value:
            self.listener_write(self._fmt_result(val, val_str) + "\n", "code")
        try:
            pretty = L.pretty_print(val, width=self._inspector_cols())
        except Exception:
            pretty = val_str
        self.set_inspector(pretty)

    def _run_silent(self, code: str):
        val, err = self._run(code)
        if err is not None:
            self.listener_write(f"Error: {err}\n", "error")
        elif val is not None:
            try:
                self.listener_write(self._fmt_result(val, L.lisp_str(val)) + "\n", "code")
            except Exception:
                pass

    # =========================================================================
    # Listener
    # =========================================================================
    def _listener_submit(self):
        if self.plain_repl.get():
            self._console_return()
            return
        code = self.listener_input.get()
        self.listener_input.delete(0, "end")
        if not code.strip():
            return
        pos = L.close_position(code)
        code, closers = L.auto_close(code)   # show the brackets the reader adds
        self.listener_history.append(code)
        self.listener_hist_idx = len(self.listener_history)
        self.listener_write("USER> ", "prompt")
        if closers:
            self.listener_write(code[:pos], "code")
            self.listener_write(closers, "info")
            self.listener_write(f"{code[pos + len(closers):]}\n", "code")
        else:
            self.listener_write(f"{code}\n", "code")
        # handle "exit" like the console REPL
        if code.strip().lower() == "exit":
            self._on_close()
            return
        val, err = self._run(code)
        self._report_eval(val, err, code=code)

    # ---------- plain lispy3 REPL mode ----------
    # The Listener text itself becomes the console: the prompt and what you type
    # sit on the last line, after the "input" mark, and scroll with the output.
    def _prompt_text(self) -> str:
        """lispy3> or, inside an unfinished form, ... (n)> as lispy3.py shows."""
        if self.repl_pending:
            return f"... ({L.count_balance(self.repl_pending)})>"
        return "lispy3>"

    def _apply_repl_mode(self):
        """Show the console prompt (plain REPL) or the USER> entry line (Listener)."""
        t = self.listener_text
        if self.plain_repl.get():
            self.input_row.pack_forget()
            t.configure(state="normal")
            self._show_prompt()
        else:
            if self.console_ready:
                t.configure(state="normal")
                t.delete("prompt_start", "end-1c")
                self.console_ready = False
            t.configure(state="disabled")
            self.input_row.pack(fill="x", padx=6, pady=(0, 6))

    def _focus_listener(self):
        if self.plain_repl.get():
            self.listener_text.mark_set("insert", "end-1c")
            self.listener_text.focus_set()
        else:
            self.listener_input.focus_set()

    def _toggle_plain_repl(self):
        on = self.plain_repl.get()
        if not on:
            self.repl_pending = ""
        self._apply_repl_mode()
        self.listener_write(";; Plain lispy3 REPL on: type at the lispy3> prompt; Enter on an open form "
                            "continues it, Tab completes, Esc drops an unfinished form.\n" if on else
                            ";; Listener mode on: USER> prompt, each line closed and evaluated.\n", "info")
        self.settings["plain_repl"] = on
        save_settings(self.settings)
        self._focus_listener()

    def _show_prompt(self):
        """Write the prompt on a new last line; what is typed after it is the input."""
        t = self.listener_text
        if t.index("end-1c") != "1.0" and t.get("end-2c") != "\n":
            t.insert("end", "\n")
        start = t.index("end-1c")
        t.insert("end", self._prompt_text() + " ", "prompt")
        t.mark_set("prompt_start", start)
        t.mark_gravity("prompt_start", "right")   # output written at it goes before the prompt
        t.mark_set("input", "end-1c")
        t.mark_gravity("input", "left")
        t.mark_set("insert", "end-1c")
        t.see("end")
        self.console_ready = True

    def _console_input(self) -> str:
        return self.listener_text.get("input", "end-1c")

    def _set_console_input(self, text: str):
        t = self.listener_text
        t.delete("input", "end-1c")
        t.insert("end", text)
        t.mark_set("insert", "end-1c")
        t.see("end")

    def _console_return(self, event=None):
        """Enter: the typed line(s) stay on screen and go to the REPL, then a new prompt."""
        t = self.listener_text
        if not self.console_ready:
            return "break"
        self._console_recolor()
        line = self._console_input()
        t.insert("end", "\n")
        self.console_ready = False
        for one_line in line.split("\n"):   # pasted lines are read one by one, as in a terminal
            if not self._plain_submit(one_line):
                break
        try:
            if self.plain_repl.get():
                self._show_prompt()
        except tk.TclError:                  # `exit` closed the window
            pass
        return "break"

    def _plain_submit(self, line: str) -> bool:
        """One line typed at the plain REPL: evaluate once the form is complete, as lispy3.repl does.

        Returns False after `exit`.
        """
        if not self.repl_pending and not line.strip():
            return True
        if not self.repl_pending and line.strip().lower() == "exit":
            self._on_close()
            return False
        self.listener_history.append(line)
        self.listener_hist_idx = len(self.listener_history)
        code = f"{self.repl_pending}\n{line}" if self.repl_pending else line
        if L.count_balance(code) > 0:
            self.repl_pending = code
            return True
        self.repl_pending = ""
        val, err = self._run(code)
        self._report_eval(val, err, code=code, plain=True)
        return True

    def _cancel_pending(self, event=None):
        """Esc: drop what is typed and any unfinished form."""
        if not self.console_ready:
            return "break"
        if self.repl_pending or self._console_input():
            self.listener_text.insert("end", "\n")
            self.console_ready = False
            if self.repl_pending:
                self.listener_write(";; unfinished form dropped\n", "info")
            self.repl_pending = ""
            self._show_prompt()
        return "break"

    def _listener_tab(self, event=None):
        """Tab in the plain REPL completes like readline: the shared start, then the choices."""
        if not self.console_ready:
            return "break"
        t = self.listener_text
        if t.compare("insert", "<", "input"):
            t.mark_set("insert", "end-1c")
        before = t.get("input", "insert")
        m = SYMBOL_TAIL.search(before)
        prefix = m.group(0) if m else ""
        if not prefix:
            return "break"
        matches = L.complete_names(prefix)
        if not matches:
            self.bell()
            return "break"
        shared = common_prefix(matches)
        if len(matches) == 1:
            shared += " "
        if len(shared) > len(prefix):
            t.insert("insert", shared[len(prefix):])
        else:
            self.listener_write("  ".join(matches) + "\n", "info")
        t.see("insert")
        return "break"

    def _console_history(self, step: int):
        if not self.console_ready or not self.listener_history:
            return "break"
        n = len(self.listener_history)
        self.listener_hist_idx = max(0, min(n, self.listener_hist_idx + step))
        self._set_console_input(self.listener_history[self.listener_hist_idx]
                                if self.listener_hist_idx < n else "")
        self._console_recolor()
        return "break"

    def _console_home(self, event=None):
        t = self.listener_text
        if self.console_ready and t.compare("insert", ">=", "input"):
            t.mark_set("insert", "input")
            return "break"
        return None

    def _console_left(self, event=None):
        """Left stops at the prompt instead of walking back into old output."""
        t = self.listener_text
        if self.console_ready and t.compare("insert", "<=", "input") and not (event.state & 0x1):
            t.mark_set("insert", "input")
            return "break"
        return None

    def _console_click(self, event=None):
        """A click in old output (not a drag to select) puts the cursor back at the prompt."""
        t = self.listener_text
        if self.console_ready and not t.tag_ranges("sel") and t.compare("insert", "<", "input"):
            t.mark_set("insert", "end-1c")
        return None

    def _console_recolor(self, event=None):
        """Colour what is typed at the prompt as Lisp code."""
        if self.console_ready:
            color_code(self.listener_text, "input", self._console_input())
        return None

    def _console_key(self, event):
        """Keep the text before the prompt read-only; typing anywhere goes to the input."""
        if not self.console_ready:
            return "break" if event.char else None
        t = self.listener_text
        sel = t.tag_ranges("sel")
        sel_locked = bool(sel) and t.compare("sel.first", "<", "input")
        if event.keysym in ("BackSpace", "Delete"):
            if sel_locked:
                return "break"
            if not sel and (t.compare("insert", "<", "input") or
                            (event.keysym == "BackSpace" and t.compare("insert", "==", "input"))):
                return "break"
            return None
        if event.state & 0x4:                # Ctrl+key: copy, select all ... are fine
            return None
        if event.char and event.char.isprintable():
            if sel_locked:
                t.tag_remove("sel", "1.0", "end")
            if t.compare("insert", "<", "input"):
                t.mark_set("insert", "end-1c")
        return None

    def _console_paste(self, event=None):
        t = self.listener_text
        if not self.console_ready:
            return "break"
        if t.tag_ranges("sel") and t.compare("sel.first", "<", "input"):
            t.tag_remove("sel", "1.0", "end")
        if t.compare("insert", "<", "input"):
            t.mark_set("insert", "end-1c")
        return None

    def _console_cut(self, event=None):
        t = self.listener_text
        if not self.console_ready or (t.tag_ranges("sel") and t.compare("sel.first", "<", "input")):
            return "break"
        return None

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
        t = self.listener_text
        t.configure(state="normal")
        # With the plain REPL's prompt showing, output goes above the prompt line
        where = "prompt_start" if self.console_ready else "end-1c"
        if tag == "code":
            start = t.index(where)
            t.insert(where, text)
            color_code(t, start, text)
        elif tag:
            t.insert(where, text, tag)
        else:
            t.insert(where, text)
        t.see("end")
        if not self.plain_repl.get():
            t.configure(state="disabled")

    def listener_to_buffer(self):
        """Open the Listener log as runnable code in a new buffer: prompts removed, output commented out."""
        t = self.listener_text
        end = "prompt_start" if self.console_ready else "end-1c"   # leave out the live prompt line
        code = listener_to_code(t.get("1.0", end))
        tab = self.new_buffer("listener.lisp", code)
        tab.dirty = True
        self._refresh_buffer_list()

    def clear_listener(self):
        self.listener_text.configure(state="normal")
        self.listener_text.delete("1.0", "end")
        self.console_ready = False
        if self.plain_repl.get():
            self.repl_pending = ""
            self._show_prompt()
        else:
            self.listener_text.configure(state="disabled")

    # =========================================================================
    # Inspector
    # =========================================================================
    def set_inspector(self, text: str):
        self._show_inspected(text)
        # Every evaluation ends here; recolour so newly defined names show up,
        # and list them in the Inspector.
        for tab in self.tabs.values():
            tab._schedule_highlight()
        if self._tree_job is None:
            self._tree_job = self.after_idle(self.refresh_definitions)

    def _show_inspected(self, text: str):
        self.inspector.configure(state="normal")
        self.inspector.delete("1.0", "end")
        self.inspector.insert("1.0", text)
        color_code(self.inspector, "1.0", text)
        self.inspector.configure(state="disabled")

    def refresh_definitions(self):
        """Rebuild the Inspector's list of definitions."""
        self._tree_job = None
        tree = self.def_tree
        tree.delete(*tree.get_children())
        for name, value in inspector_items():
            tree.insert("", "end", iid=name, text=name, values=(value,))

    def _on_definition_select(self, event=None):
        """Clicking a definition shows its value, pretty-printed, below the list."""
        sel = self.def_tree.selection()
        if not sel or sel[0] not in L.global_env:
            return
        name, val = sel[0], L.global_env[sel[0]]
        text = L.pretty_print(val, width=self._inspector_cols())
        if not (type(val).__name__ == 'Procedure' and text.startswith("(define")):
            text = f"{name} =\n{text}"
        self._show_inspected(text)

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

    def _clear_search_highlights(self):
        tab = self.current_tab()
        if tab is None:
            return
        tab.text.tag_remove("search_all",     "1.0", "end")
        tab.text.tag_remove("search_current", "1.0", "end")
        tab.text.tag_remove("sel",            "1.0", "end")

    def _update(self):
        """Help > Update: git pull in the program's folder, without blocking the window."""
        dirty = [t.name for t in self.tabs.values() if t.dirty]
        if dirty and not messagebox.askyesno(
            "Unsaved buffers",
            "These buffers have unsaved changes:\n  " + "\n  ".join(dirty) +
            "\n\nUpdating ends with a restart, so save them first."
            "\nUpdate anyway?"
        ):
            return
        self.listener_write(f";; Updating: git pull in {APP_DIR}\n", "info")

        def work():
            result, output = git_pull()
            self.after(0, self._update_done, result, output)

        threading.Thread(target=work, daemon=True).start()

    def _update_done(self, result: str, output: str):
        if output:
            self.listener_write(output + "\n", "error" if result == "failed" else "info")
        if result == "failed":
            messagebox.showerror("Update failed", output or "git pull failed.")
            return
        if result == "updated":
            self.update_pending = True
        if not self.update_pending:
            messagebox.showinfo("Update", "Lispy3 is already up to date.")
        elif messagebox.askyesno("Update", "Lispy3 was updated. The new version is used "
                                 "after a restart.\n\nRestart Lispy3 Machine now?"):
            self.restart()
        else:
            self.listener_write(";; Restart Lispy3 Machine to use the new version "
                                "(Help > Update offers it again).\n", "info")

    def restart(self):
        """Start a fresh Lispy3 Machine with the saved buffers open, then close this one.

        A new process is the only way the updated lispy3.py and editor code
        are really used: modules already imported stay old in this one.
        """
        dirty = [t.name for t in self.tabs.values() if t.dirty]
        if dirty and not messagebox.askyesno(
            "Unsaved buffers",
            "These buffers have unsaved changes:\n  " + "\n  ".join(dirty) +
            "\n\nThey are lost on restart. Restart anyway?"
        ):
            return
        files = [t.path for t in self.tabs.values() if t.path]
        try:
            subprocess.Popen(restart_command(files, self.plain_repl.get()), cwd=os.getcwd())
        except OSError as e:
            messagebox.showerror("Restart failed", f"Could not start Lispy3 Machine: {e}")
            return
        self.destroy()

    def open_terminal(self):
        """View > Open terminal: a system terminal in Lispy's working directory,
        handy when the Machine was started from a shortcut without a console."""
        cwd = os.getcwd()
        command = terminal_command(cwd)
        if command is None:
            messagebox.showerror("Open terminal", "No terminal program was found.")
            return
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        try:
            subprocess.Popen(command, cwd=cwd, creationflags=flags)
        except OSError as e:
            messagebox.showerror("Open terminal", f"Could not start {command[0]}: {e}")

    # ---------- Help window ----------
    def open_guide(self, page: str | None = None):
        """Help > Lispy guide (F1): open the guide window, or bring it to the front."""
        if self.guide_window is None or not self.guide_window.winfo_exists():
            self.guide_window = GuideWindow(self)
            self.guide_window.protocol("WM_DELETE_WINDOW", self.guide_window.withdraw)
            self.guide_window.show(page or guide.PAGES[0][0], remember=False)
        elif page:
            self.guide_window.show(page)
        else:
            self.guide_window.deiconify()
            self.guide_window.lift()
        self.guide_window.focus_set()
        return self.guide_window

    def lisp_help(self, *args):
        """(help) in the editor opens the guide at the built-ins instead of printing them.

        (help 'name) still prints its one line in the Listener, and an open
        guide window also turns to that name.
        """
        if not args:
            self.open_guide(guide.BUILTINS_PAGE)
            print(";; The Lispy guide is open (F1). (help 'name) explains one name here.")
            return None
        L.lisp_help(*args)
        what = args[0]
        name = what.value if isinstance(what, L.String) else L.lisp_str(what)
        win = self.guide_window
        if win is not None and win.winfo_exists() and win.winfo_viewable():
            win.show_name(name)
        return None

    def _about(self):
        messagebox.showinfo(
            "About Lispy3 Machine",
            "Lispy3 Machine — a Lisp Machine style editor\n"
            "for the lispy3 interpreter.\n\n"
            + ABOUT_CREDITS + "\n\n"
            "F1  Lispy guide\n"
            "F5  eval form at cursor\n"
            "F6  eval whole buffer\n"
            "F7  inspect symbol at cursor\n"
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
def main():
    plain_repl, files = parse_args(sys.argv[1:])
    app = LispMachine(files, plain_repl=True if plain_repl else None)
    app.mainloop()


if __name__ == "__main__":
    main()
