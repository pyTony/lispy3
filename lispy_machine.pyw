#!/usr/bin/env python3
"""
lispy_machine.pyw - a Lisp-Machine style editor for the lispy3 interpreter.

Features
  * Multiple editor buffers (tabs) with syntax colouring read from syntax/*.json
  * Persistent Listener (REPL) with history, coloured output
  * Inspector pane showing the last evaluated value (pretty-printed)
  * F5 / Ctrl+Enter : run Lisp form or BASIC/Python selection/current line
  * F6 / Shift+F6 : fresh program run in Listener / ANSI terminal
  * Ctrl+Shift+Enter : evaluate buffer in current workspace
  * F7 / F8 : Python mini_basic selection/current line / whole BASIC buffer
  * Shift+F7 : inspect the symbol at the cursor (or typed in the Listener)
  * F9 : evaluate the Listener input line
  * Code runs in the background, so the window stays live; the Stop button
    (or Ctrl+Break) ends a long or endless run
  * View > Listener mode > Lisp REPL: the Listener behaves like `python lispy3.py`
    (lispy3> prompt, multi-line input, Tab completion)
  * Paren matching, auto-indent, symbol completion (Ctrl+Space)
  * Open / Save / Save-As / Close buffers
  * Menu + status bar showing the current "package" (USER) and buffer

Run:  python lispy_machine.pyw [--repl] [file.lisp ...]
      python lispy_machine.pyw --version   shows the editor and lispy3 versions
      --repl starts the Listener as the plain lispy3 REPL (View > Listener mode changes it).
      Each file named on the command line opens in its own buffer; a file that
      does not exist yet opens empty and is created on the first Save. With no
      files, startup.lisp beside the editor opens by default; configure it in Startup Settings.
"""
import io
import hashlib
from pathlib import Path
import contextlib
import ctypes
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import turtle
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from tkinter.scrolledtext import ScrolledText

# --- import the interpreter (no side effects when imported) -------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
import lispy_terminal
from lispy_terminal import terminal_command
import lispy3 as L
from basic_repl import BasicRepl
from repl_completion import filename_completion

def _use_numpy_interpreter() -> bool:
    """With NumPy installed, load lispy3-numpy.py: it speeds up L in place and adds
    the array built-ins. Without NumPy, or if it fails to load, keep plain lispy3."""
    try:
        import numpy  # noqa: F401
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lispy3-numpy.py")
        spec = importlib.util.spec_from_file_location("lispy3_numpy", path)
        spec.loader.exec_module(importlib.util.module_from_spec(spec))
        return True
    except Exception:
        return False

USING_NUMPY = _use_numpy_interpreter()
import guide
import syntax_highlight as SH
import editor_tools as ET
import basic_runner as BR


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


def source_filetypes(languages=LANGUAGES, *, tokenized=True):
    """Use the installed syntax definitions for source-file dialog filters."""
    groups = []
    for language in languages:
        patterns = tuple(dict.fromkeys(pattern for extension in language.extensions
                                      for pattern in ('*'+extension, '*'+extension.upper())))
        if patterns:
            groups.append((language.name, patterns))
    if tokenized:
        groups.append(('Tokenised BBC BASIC', ('*.bbc', '*.BBC')))
    supported = tuple(dict.fromkeys(pattern for _, patterns in groups for pattern in patterns))
    return ([('Supported source files', supported)] if supported else []) + groups + [('All files', '*')]


def execution_language(tab):
    language = getattr(tab, 'language', None)
    if language is None:
        language = SH.language_for(getattr(tab, 'path', None) or tab.name, LANGUAGES)
    return getattr(language, 'name', None)
SYNTAX_TAGS = sorted({tag for lang in LANGUAGES for tag in lang.colors})
BUILTIN_NAMES = frozenset(list(L.standard_env()) + ['load', 'save'])
# The name being typed at the end of a line, for completion (":name" keywords included)
SYMBOL_TAIL = re.compile(r"[\w\-+*/<>=!?:.]+$")

# Remembers the View > Listener mode > Lisp REPL choice between runs
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

def color_code(widget, start: str, text: str, language=None):
    """Colour `text`, which starts at index `start` in `widget`, like the editor does."""
    language = language or LISP_LANGUAGE
    variables = user_defined_names() if language.env_words else ()
    for tag in SYNTAX_TAGS:
        widget.tag_remove(tag, start, f"{start}+{len(text)}c")
    for tag, a, b in language.spans(text, builtins=BUILTIN_NAMES, variables=variables):
        widget.tag_add(tag, f"{start}+{a}c", f"{start}+{b}c")

APP_DIR = os.path.dirname(os.path.abspath(__file__))

def runtime_fingerprint(folder=APP_DIR):
    """Content of runtime sources, independent of Git or modification times."""
    root = Path(folder)
    paths = set(root.glob('*.py')) | set(root.glob('*.pyw'))
    paths |= set((root / 'lisp').glob('*.lisp')) | set((root / 'lisp').glob('*.sld'))
    paths |= set((root / 'syntax').glob('*.json'))
    result = {}
    for path in paths:
        try:
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            result[path.relative_to(root).as_posix()] = None
    return result

RUNTIME_FINGERPRINT = runtime_fingerprint()

__version__ = "1.0"

def version_text() -> str:
    """The line `python lispy_machine.pyw --version` prints, also shown in Help > About."""
    numpy = f", NumPy {sys.modules['numpy'].__version__}" if USING_NUMPY else ""
    return f"Lispy3 Machine {__version__} (lispy3 {L.__version__}, Python {sys.version.split()[0]}{numpy})"

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

def git_branch(folder: str = APP_DIR) -> str:
    """The git branch `folder` is on, for Help > About.

    A detached HEAD gives "detached at <short commit>"; a folder that is not
    a git checkout, or a computer without git, gives "not a git checkout".
    """
    if not os.path.exists(os.path.join(folder, ".git")):
        return "not a git checkout"
    try:
        branch = _git(folder, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if branch == "HEAD":
            commit = _git(folder, "rev-parse", "--short", "HEAD").stdout.strip()
            return f"detached at {commit}" if commit else "not a git checkout"
    except (OSError, subprocess.SubprocessError):
        return "not a git checkout"
    return branch or "not a git checkout"

def about_text(folder: str = APP_DIR) -> str:
    """The text of Help > About."""
    return (
        "Lispy3 Machine — a Lisp Machine style editor\n"
        "for the lispy3 interpreter.\n"
        + version_text() + "\n"
        "Git branch: " + git_branch(folder) + "\n\n"
        + ABOUT_CREDITS + "\n\n"
        "F1  Lispy guide\n"
        "F5  run form / selection / line\n"
        "F6  fresh program in Listener; Shift+F6 in ANSI terminal\n"
        "Ctrl+Shift+Enter  Eval buffer in current workspace\n"
        "F7  Python BASIC selection or line\n"
        "F8  Python BASIC whole buffer\n"
        "Shift+F7  inspect symbol at cursor\n"
        "F9  eval listener input\n"
        "Ctrl+Break  stop the running code\n"
        "Ctrl+Space  complete symbol\n"
        "Ctrl+/      toggle comment"
    )

def git_pull(folder: str = APP_DIR):
    """Run `git pull --ff-only` in `folder`. Return (result, git's output).

    result is "updated", "current" (nothing new) or "failed". --ff-only never
    makes a merge commit, so git cannot stop to open an editor; local changes
    that would be overwritten make git refuse, and its message names them.
    """
    if not os.path.exists(os.path.join(folder, ".git")):
        return "failed", "fatal: not a git repository"
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

def context_menu_items(has_selection: bool, editable: bool) -> list[tuple[str, str, bool]]:
    """The right-click menu: [(label, virtual event, enabled), ...]."""
    return [("Cut",        "<<Cut>>",       has_selection and editable),
            ("Copy",       "<<Copy>>",      has_selection),
            ("Paste",      "<<Paste>>",     editable),
            ("Select all", "<<SelectAll>>", True)]

def add_context_menu(widget, read_only: bool = False, extra_commands=()):
    """Right-click (and Ctrl+click on macOS) on a Text or Entry opens Cut / Copy / Paste.

    A disabled widget, or one marked read_only, offers only Copy and Select all."""
    menu = tk.Menu(widget, tearoff=0)

    def popup(event):
        widget.focus_set()
        if isinstance(widget, tk.Entry):
            has_sel = widget.selection_present()
        else:
            has_sel = bool(widget.tag_ranges("sel"))
        menu.delete(0, "end")
        for label, virtual, enabled in context_menu_items(has_sel, not read_only and str(widget.cget("state")) != "disabled"):
            menu.add_command(label=label, state="normal" if enabled else "disabled",
                             command=lambda v=virtual: widget.event_generate(v))
        if extra_commands:
            widget.mark_set('insert', widget.index(f'@{event.x},{event.y}'))
            menu.add_separator()
            for label, command in extra_commands:
                menu.add_command(label=label, command=command)
        menu.tk_popup(event.x_root, event.y_root)
        return "break"

    widget.bind("<Button-3>", popup, add="+")
    if sys.platform == "darwin":
        widget.bind("<Button-2>", popup, add="+")
        widget.bind("<Control-Button-1>", popup, add="+")

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
        self._pending_control = ''
        self._home_after_cls = False

    def write(self, s):                       # noqa: D401
        data = self._pending_control + s
        self._pending_control = ''
        text = []
        while data:
            if data.startswith('\x1b[2J'):
                if text:
                    self.app._ui_post(self.app.listener_write, ''.join(text), 'result')
                    text.clear()
                self.app._ui_post(self.app._clear_listener_screen)
                self._home_after_cls = True
                data = data[4:]
            elif self._home_after_cls and data.startswith('\x1b[H'):
                self._home_after_cls = False
                data = data[3:]
            elif '\x1b[2J'.startswith(data) or (self._home_after_cls and '\x1b[H'.startswith(data)):
                self._pending_control = data
                break
            else:
                # Keep unrelated ANSI and ordinary output unchanged. Only the
                # clear-screen/home pair emitted by CLS is interpreted here.
                end = data.find('\x1b', 1)
                if end < 0:
                    end = len(data)
                text.append(data[:end])
                self._home_after_cls = False
                data = data[end:]
        if text:
            self.app._ui_post(self.app.listener_write, ''.join(text), 'result')
        return len(s)

    def writable(self):
        return True

    def flush(self):
        if self._pending_control:
            self.app._ui_post(self.app.listener_write, self._pending_control, 'result')
            self._pending_control = ''
        
# =============================================================================
# Running Lisp off the Tk thread
# =============================================================================
# Lisp code runs on its own thread so the window stays live and a Stop button
# can end an endless loop. Tk (and so turtle) may only be used from the main
# thread, so these built-ins are handed over to it and waited for.
GUI_BUILTINS = frozenset(turtle.__all__) | {
    'push-pose', 'pop-pose', 'clear-poses', 'reinit-turtle', 'reset', 'help', 'onscroll'}


class Stopped(BaseException):
    """Raised in the evaluation thread by Stop. Not an Exception, so (try ...) cannot catch it."""


def stop_thread(thread: threading.Thread) -> bool:
    """Raise Stopped inside `thread` at its next Python step."""
    if thread.ident is None or not thread.is_alive():
        return False
    ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread.ident), ctypes.py_object(Stopped))
    return True


class _OnMainThread:
    """A turtle object (Turtle, Screen ...) used from Lisp: its methods run on the Tk thread."""
    def __init__(self, app, obj):
        object.__setattr__(self, "_app", app)
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name):
        value = self._app._ui(getattr, self._obj, name)
        if callable(value):
            return lambda *args: self._app._gui_call(value, *args)
        return value

    def __setattr__(self, name, value):
        self._app._ui(setattr, self._obj, name, value)

    def __repr__(self):
        return repr(self._obj)


def _is_gui_object(value) -> bool:
    return type(value).__module__ in ("turtle", "tkinter")


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
        self.disk_content = content if path else None
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
        t.tag_configure("syntax_error", background=COLORS["paren_bad"],
                        foreground="#ffffff", underline=True)
        t.tag_configure("search_all",  background="#5c4d00",
                                       foreground="#ffffff")
        t.tag_configure("search_current", background="#ffd700",
                                        foreground="#000000")

        # Virtual events fired by menu / programmatic paste and cut
        t.bind("<<Paste>>", self._schedule_highlight)
        t.bind("<<Cut>>",   self._schedule_highlight)

        # X11 middle-click paste; right-click opens Cut / Copy / Paste
        t.bind("<ButtonRelease-2>", self._on_key)
        t.bind("<ButtonRelease-3>", self._on_key)
        add_context_menu(t, extra_commands=[("Open file at cursor", self._open_file_at_cursor)])

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
        t.bind("<<Modified>>", self._on_modified)
        # Widget bindings precede Tk Text's class bindings and global bindings.
        t.bind("<Control-o>", lambda e: (self.app.open_file(), 'break')[1])
        t.bind("<Control-s>", lambda e: (self.app.save_current(), 'break')[1])
        t.bind("<Control-Shift-S>", lambda e: (self.app.save_current_as(), 'break')[1])
        t.bind("<Control-w>", lambda e: (self.app.close_current(), 'break')[1])

        t.bind('<F4>', self._open_file_at_cursor)
        t.bind('<Command-Button-1>' if sys.platform == 'darwin' else '<Control-Button-1>',
               self._open_file_at_cursor)

        # Eval bindings
        t.bind("<F5>",                      lambda e: (self.app.eval_form_at_cursor(), "break")[1])
        t.bind("<Control-Return>",          lambda e: (self.app.eval_form_at_cursor(), "break")[1])
        t.bind("<Shift-F6>", lambda e: (self.app.eval_buffer_in_terminal(), "break")[1])
        t.bind("<F6>",                      lambda e: (self.app.eval_buffer_listener(), "break")[1])
        t.bind("<Control-Shift-Return>",    lambda e: (self.app.eval_buffer(), "break")[1])

    def _open_file_at_cursor(self, event=None):
        text = self.text
        if event is not None and getattr(event, 'num', None) == 1:
            text.mark_set('insert', text.index(f'@{event.x},{event.y}'))
        source = self.get_content()
        offset = len(text.get('1.0', 'insert'))
        reference = ET.file_reference_at_cursor(source, offset, self.language.name)
        if reference is None:
            self.app.listener_write(';; No quoted filename at cursor.\n', 'info')
            return 'break'
        origin = buffer_source_path(self)
        roots = [os.path.dirname(origin)] if origin else []
        roots += [os.getcwd(), APP_DIR, L.LISP_DIR]
        for root in roots:
            path = os.path.abspath(os.path.join(root, reference))
            for candidate in [path] + ([path+'.lisp'] if not os.path.splitext(path)[1] else []):
                if os.path.isfile(candidate):
                    self.app._open_source_path(candidate)
                    return 'break'
        self.app.listener_write(f';; File not found: {reference}\n', 'error')
        return 'break'

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

    def _on_modified(self, event=None):
        if not self._suppress_modified:
            self.dirty = bool(self.text.edit_modified())
            self.app._refresh_buffer_list()
            self._schedule_highlight()

    def _schedule_highlight(self):
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(30, self._highlight)

    def _highlight(self):
        self._highlight_job = None
        if getattr(self, '_syntax_error_source', None) is not None:
            if self.get_content() != self._syntax_error_source:
                self.text.tag_remove('syntax_error', '1.0', 'end')
                self._syntax_error_source = None
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
        prefix = t.get('1.0', 'insert')
        if self.language.name in ('Lisp', 'BBC BASIC'):
            target_indent = ET.next_indent(prefix, basic=self.language.name == 'BBC BASIC')
        else:
            line = prefix.split('\n')[-1]
            target_indent = len(line)-len(line.lstrip())
        
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
def buffer_source_path(tab):
    path = getattr(tab, 'path', None)
    if isinstance(path, str) and path:
        return path
    origin = getattr(tab, 'source_path', None)
    return origin if isinstance(origin, str) else None


def source_arg_path(arg):
    path = os.path.abspath(arg)
    if not os.path.dirname(arg) and not os.path.exists(path):
        path = os.path.join(L.LISP_DIR, 'programs', arg)
    return path


def read_file_arg(arg: str, settings=None):
    """Return (buffer name, content, path) for a file named on the command line.

    A bare file name that is not in the current folder means the file in
    lisp/programs. A file that does not exist yet gives an empty buffer that saves to
    that path. Tokenised .bbc input returns an unsaved .bas buffer; decoder
    failures raise RuntimeError and text read failures raise OSError.
    """
    path = source_arg_path(arg)
    if os.path.splitext(path)[1].lower() == '.bbc':
        settings = settings or {}
        content = BR.detokenize_bbc(path, executable=settings.get('basic_python'),
                                   package_root=settings.get('basic_directory', ''))
        return os.path.splitext(os.path.basename(path))[0]+'.bas', content, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    return os.path.basename(path), content, path


STARTUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "startup.lisp")


def read_startup(path=STARTUP_FILE):
    """Return (buffer name, content, path) for the buffer opened when no file
    is named on the command line: startup.lisp, or an empty untitled buffer if
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
        add_context_menu(self.text, read_only=True)
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
        self.startup_show_buffer = tk.BooleanVar(self, value=bool(self.settings.get('startup_show_buffer', True)))
        self.startup_run = tk.BooleanVar(self, value=bool(self.settings.get('startup_run', False)))
        self.startup_settings_window = None
        self._startup_ran = False
        self.settings.pop('basic_backend', None)  # The run command now chooses it.
        output = self.settings.get('basic_output', 'listener')
        self.basic_output = tk.StringVar(self, value=output if output in ('listener', 'ansi') else 'listener')
        self._output_mode = self.basic_output.get()
        self.basic_pygame = tk.BooleanVar(self, value=bool(self.settings.get('basic_pygame', False)))
        self.basic_settings_window = None
        if plain_repl is None:
            plain_repl = bool(self.settings.get("plain_repl", False))
        self.plain_repl = tk.BooleanVar(self, value=plain_repl)
        self.basic_repl_mode = tk.BooleanVar(self, value=bool(self.settings.get('basic_repl', False)))
        if self.basic_repl_mode.get():
            self.plain_repl.set(True)
        self.basic_repl = BasicRepl(L, self._read_basic_repl_source, get_current_source=self._get_basic_buffer_text)
        self.listener_mode = tk.StringVar(self, value='basic' if self.basic_repl_mode.get() else
                                         'lisp' if self.plain_repl.get() else 'listener')
        self.repl_pending = ""      # lines of an unfinished form in the plain REPL
        self.console_ready = False  # the plain REPL prompt is showing, waiting for input
        self.update_pending = False # Help > Update pulled a new version, not running yet
        self.guide_window = None    # the Help window, made the first time it is opened
        self._job = None            # the thread running Lisp code, while it runs
        self._calls = queue.Queue() # what that thread hands to the Tk thread: (fn, args, box, done)
        L.global_env['help'] = self.lisp_help
        L.global_env['sleep'] = self._sleep
        self._gui_builtins_on_main()
        L.workspaces.add_initializer(self._initialize_workspace_env)

        self._setup_style()
        self._build_menu()
        self._build_layout()
        self._build_status()
        self._bind_global()

        open_errors = self._open_initial_buffers(files)

        self.listener_write(";; Lispy3 Machine ready.\n", "info")
        self.listener_write(";; F5/F6 = run by buffer language; F7/F8 = Python BASIC; F9 = Lisp listener.\n", "info")
        self.listener_write(";; Stop (Ctrl+Break) ends code that runs too long.\n", "info")
        self.listener_write(";; Ctrl+Space completes a symbol.  Try `(load \"lsystems\")`.\n", "info")
        self.listener_write(";; View > Listener mode > Lisp REPL switches the Listener to the lispy3 prompt.\n\n", "info")
        for err in SYNTAX_ERRORS:
            self.listener_write(f";; Syntax colouring file not loaded: {err}\n", "error")
        for err in open_errors:
            self.listener_write(f";; Could not open {err}\n", "error")
        self._apply_repl_mode()
        self._focus_listener()
        self.refresh_definitions()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.startup_run.get():
            self.after_idle(self._run_startup)

    def _open_initial_buffers(self, files):
        errors = []
        for arg in files:
            try:
                name, content, path = read_file_arg(arg, self.settings if isinstance(getattr(self, 'settings', None), dict) else None)
            except (OSError, UnicodeDecodeError, RuntimeError) as error:
                errors.append(f'{arg}: {error}')
                continue
            tab = self.new_buffer(name, content, path=path)
            if os.path.splitext(arg)[1].lower() == '.bbc':
                tab.source_path = source_arg_path(arg)
        if not self.tabs:
            if self.startup_show_buffer.get():
                name, content, path = read_startup()
            else:
                name, content, path = 'untitled.lisp', '', None
            self.new_buffer(name, content, path=path)
        return errors

    def _run_startup(self):
        if self._startup_ran or not self.startup_run.get():
            return
        if self._job is not None:
            self.after(100, self._run_startup)
            return
        self._startup_ran = True
        try:
            with open(STARTUP_FILE, encoding='utf-8') as source:
                content = source.read()
            ET.check_lisp(content, STARTUP_FILE)
            forms = self._parse_top_level_forms(content, source_name=STARTUP_FILE)
        except (OSError, UnicodeError, SyntaxError) as error:
            self.listener_write(f'Error running startup.lisp: {error}\n', 'error')
            return
        self.listener_write(f';; Running {STARTUP_FILE}\n', 'info')
        terminal = getattr(self, '_output_mode', 'listener') == 'ansi'
        self._start(lambda: self._eval_forms_in_terminal(forms) if terminal else self._eval_forms(forms))

    def _open_startup_settings(self):
        if self.startup_settings_window is not None and self.startup_settings_window.winfo_exists():
            self.startup_settings_window.lift()
            return
        window = self.startup_settings_window = tk.Toplevel(self)
        window.title('Startup Settings')
        window.transient(self)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill='both', expand=True)
        status = tk.StringVar(window, value='Changes apply at the next launch.')

        def save():
            self.settings['startup_show_buffer'] = self.startup_show_buffer.get()
            self.settings['startup_run'] = self.startup_run.get()
            save_settings(self.settings)
            status.set('Saved for the next launch.')

        ttk.Checkbutton(frame, text='Show startup.lisp buffer when no files are supplied',
                        variable=self.startup_show_buffer, command=save).pack(anchor='w')
        ttk.Checkbutton(frame, text='Run startup.lisp once at startup (also when hidden)',
                        variable=self.startup_run, command=save).pack(anchor='w', pady=8)
        ttk.Label(frame, text=STARTUP_FILE).pack(anchor='w', pady=8)
        ttk.Label(frame, text='Running executes every form, including printing and graphics.').pack(anchor='w')
        ttk.Label(frame, textvariable=status).pack(anchor='w', pady=8)
        ttk.Button(frame, text='Close', command=window.destroy).pack(anchor='e')

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
        file_m.add_command(label="Load library silently…", command=self.load_library_silently)
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
        edit_m.add_separator()
        edit_m.add_command(label="Open file at cursor", accelerator="F4", command=lambda: self._call_editor("_open_file_at_cursor"))
        edit_m.add_command(label="Check Lisp syntax", command=self.check_buffer_syntax)
        edit_m.add_command(label="Reindent selection or buffer", command=self.reindent_buffer)
        bar.add_cascade(label="Edit", menu=edit_m)

        self.eval_menu = eval_m = tk.Menu(bar, tearoff=0)
        self.time_buffer_runs = tk.BooleanVar(value=False)
        eval_m.add_checkbutton(label="Time buffer runs", variable=self.time_buffer_runs)
        eval_m.add_command(label="Run form / selection / line", accelerator="F5", command=self.eval_form_at_cursor)
        eval_m.add_command(label="Run program → ANSI terminal (fresh workspace)", accelerator="Shift+F6", command=self.eval_buffer_in_terminal)
        eval_m.add_command(label="Run program → Listener (fresh workspace)", accelerator="F6", command=self.eval_buffer_listener)
        eval_m.add_command(label="Eval buffer in current workspace", accelerator="Ctrl+Shift+Enter", command=self.eval_buffer)
        eval_m.add_command(label="Python BASIC selection or line", accelerator="F7", command=self.eval_basic_at_cursor)
        eval_m.add_command(label="Python BASIC whole buffer", accelerator="F8", command=self.eval_basic_buffer)
        eval_m.add_command(label="Real BBC BASIC for SDL buffer", command=self.eval_bbcsdl_buffer)
        eval_m.add_command(label='BASIC Settings…', command=self._open_basic_settings)
        eval_m.add_command(label="Inspect symbol at cursor", accelerator="Shift+F7", command=self.inspect_at_cursor)
        eval_m.add_separator()
        eval_m.add_command(label="Eval listener input", accelerator="F9",     command=self._listener_submit)
        eval_m.add_command(label="Stop", accelerator="Ctrl+Break", command=self.stop, state="disabled")
        eval_m.add_separator()
        eval_m.add_command(label="Listener to buffer",  command=self.listener_to_buffer)
        eval_m.add_command(label="Clear listener",      accelerator="Ctrl+L", command=self.clear_listener)
        bar.add_cascade(label="Eval", menu=eval_m)

        workspace_m = tk.Menu(bar, tearoff=0)
        workspace_m.add_command(label='New workspace', command=lambda: self._workspace_action('new'))
        workspace_m.add_command(label='Push workspace (enter fresh)', command=lambda: self._workspace_action('push'))
        workspace_m.add_command(label='Pop workspace (restore)', command=lambda: self._workspace_action('pop'))
        workspace_m.add_separator()
        workspace_m.add_command(label='Unload module…', command=lambda: self._workspace_module_action('unload'))
        workspace_m.add_command(label='Reload module…', command=lambda: self._workspace_module_action('reload'))
        bar.add_cascade(label='Workspace', menu=workspace_m)

        view_m = tk.Menu(bar, tearoff=0)
        view_m.add_command(label='Startup Settings…', command=self._open_startup_settings)
        view_m.add_command(label="Reload lsystems",     command=lambda: self._run_silent('(load "lsystems")'))
        view_m.add_command(label="Show global env",     command=self._show_env)
        view_m.add_separator()
        view_m.add_command(label="Open terminal",      command=self.open_terminal)
        view_m.add_command(label="Focus listener",      accelerator="Ctrl+E", command=self._focus_listener)
        modes = tk.Menu(view_m, tearoff=0)
        for label, value in [('Lisp Listener (USER>)', 'listener'), ('Lisp REPL', 'lisp'), ('BASIC REPL', 'basic')]:
            modes.add_radiobutton(label=label, value=value, variable=self.listener_mode,
                                  command=self._select_listener_mode)
        view_m.add_cascade(label='Listener mode', menu=modes)
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
        if console and (LispMachine._basic_mode(self) or
                        filename_completion(self.listener_text.get('input', 'insert')) is not None):
            return self._listener_tab(event)
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

        files = filename_completion(before)
        if files is not None:
            start, matches = files
            if matches:
                shared = common_prefix(matches)
                if shared != before[start:]:
                    widget.delete(start, widget.index('insert'))
                    put(shared)
                else:
                    self.listener_write('  '.join(matches)+'\n', 'info')
            return 'break'

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
        add_context_menu(self.inspector)

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
        # Stop is live only while Lisp code runs (see _set_running)
        self.stop_button = tk.Button(hdr, text="■ Stop", bg=COLORS["side_bg"], fg="#ddd",
                                     activebackground=COLORS["error"], disabledforeground="#666",
                                     font=FONT_UI, borderwidth=0, padx=8, state="disabled",
                                     command=self.stop)
        self.stop_button.pack(side="right", padx=4, pady=2)
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
        add_context_menu(self.listener_text)
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
        add_context_menu(self.listener_input)
        self.listener_input.bind("<Return>",  lambda e: (self._listener_submit(), "break")[1])
        self.listener_input.bind("<Tab>", self._listener_complete)
        self.listener_input.bind("<Control-space>", self._listener_complete)
        self.listener_input.bind("<Control-Key-space>", self._listener_complete)
        self.listener_input.bind("<Up>",      self._history_up)
        self.listener_input.bind("<Down>",    self._history_down)
        self.listener_input.bind("<Control-l>", lambda e: (self.clear_listener(), "break")[1])

    def _build_status(self):
        pass  # placeholder

    def _bind_global(self):
        self.bind_all("<F1>", lambda e: (self.open_guide(), "break")[1])
        self.bind_all("<F7>", lambda e: (self.eval_basic_at_cursor(), "break")[1])
        self.bind_all("<F8>", lambda e: (self.eval_basic_buffer(), "break")[1])
        self.bind_all("<Shift-F7>", lambda e: (self.inspect_at_cursor(), "break")[1])
        # Ctrl+Break: Tk calls that key Cancel on Windows and Break on Linux
        self.bind_all("<Control-Cancel>", self.stop)
        self.bind_all("<Control-Break>", self.stop)
        self.bind_all("<Control-n>", lambda e: self.new_buffer_dialog())
        self.bind_all("<Control-o>", lambda e: (self.open_file(), 'break')[1])
        # Tk Text gives Ctrl+O its own editing behavior before bind_all runs.
        # Handle Open at the widget first, including while BASIC waits for INPUT.
        for widget in (self.listener_text, self.listener_input, self.inspector):
            widget.bind("<Control-o>", lambda e: (self.open_file(), 'break')[1])
        self.bind_all("<Control-s>", lambda e: (self.save_current(), 'break')[1])
        self.bind_all("<Control-Shift-S>", lambda e: (self.save_current_as(), 'break')[1])
        self.bind_all("<Control-w>", lambda e: (self.close_current(), 'break')[1])
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
        if tab.dirty or tab.text.edit_modified():
            save = messagebox.askyesnocancel('Unsaved changes', f'Save changes to {tab.name} before closing?')
            if save is None:
                return
            if save and not self.save_current():
                return
        key = next((name for name, value in self.tabs.items() if value is tab), tab.name)
        self.notebook.forget(tab)
        self.tabs.pop(key, None)
        if key in self.tab_order:
            self.tab_order.remove(key)
        tab.destroy()
        self._refresh_buffer_list()

    def _file_dialog_dir(self, tab=None):
        """Where Open and Save as start: the buffer's own folder, else lisp/."""
        if tab is not None and buffer_source_path(tab):
            return os.path.dirname(buffer_source_path(tab))
        os.makedirs(L.LISP_DIR, exist_ok=True)
        return L.LISP_DIR

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open source file",
            initialdir=self._file_dialog_dir(),
            filetypes=source_filetypes())
        if not path:
            return
        self._open_source_path(path)

    def _open_source_path(self, path):
        path = os.path.abspath(path)
        for tab in self.tabs.values():
            origin = buffer_source_path(tab)
            if origin and os.path.normcase(os.path.abspath(origin)) == os.path.normcase(path):
                self.notebook.select(tab)
                return
        try:
            if os.path.splitext(path)[1].lower() == '.bbc':
                name, content, target = read_file_arg(path, self.settings)
            else:
                with open(path, 'r', encoding='utf-8') as source:
                    content = source.read()
                name, target = os.path.basename(path), path
        except (OSError, UnicodeError, RuntimeError) as error:
            messagebox.showerror('Open failed', str(error))
            return
        tab = self.new_buffer(name, content, path=target)
        if target is None:
            tab.source_path = path
            self.listener_write(f';; Detokenised {path}; Save As .bas to keep editable text.\n', 'info')

    def save_current(self):
        tab = self.current_tab()
        if not tab:
            return False
        if not tab.path:
            return self.save_current_as()
        if not LispMachine._save_tab_to_path(self, tab, tab.path):
            return False
        self._refresh_buffer_list()
        return True

    def _save_tab_to_path(self, tab, path):
        if os.path.splitext(path)[1].lower() == '.bbc':
            messagebox.showerror('Save failed', 'BBC files contain tokenised BASIC. Save editable text as .bas; native tokenised output is not supported.')
            return False
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(tab.get_content())
            tab.disk_content = tab.get_content()
            tab.dirty = False
            tab.text.edit_modified(False)
            self.status_right.configure(text=f"saved: {path}")
            return True
        except OSError as e:
            messagebox.showerror("Save failed", str(e))
            return False

    def save_current_as(self):
        tab = self.current_tab()
        if not tab:
            return False
        path = filedialog.asksaveasfilename(
            title="Save as",
            initialdir=self._file_dialog_dir(tab),
            initialfile=os.path.basename(tab.path) if tab.path else re.sub(r' <\d+>$', '', tab.name),
            defaultextension=os.path.splitext(tab.path or re.sub(r' <\d+>$', '', tab.name))[1] or '.lisp',
            filetypes=source_filetypes(tokenized=False))
        if not path:
            return False
        if not LispMachine._save_tab_to_path(self, tab, path):
            return False
        old_key = next((name for name, value in self.tabs.items() if value is tab), tab.name)
        base = os.path.basename(path)
        name, number = base, 1
        while name in self.tabs and self.tabs[name] is not tab:
            number += 1
            name = f'{base} <{number}>'
        tab.path = path
        tab.name = name
        self.tabs.pop(old_key, None)
        self.tabs[name] = tab
        self.tab_order = [name if key == old_key else key for key in self.tab_order]
        self.notebook.tab(tab, text=tab.name)
        tab.set_language()
        self._refresh_buffer_list()
        return True

    # =========================================================================
    # Evaluation
    # =========================================================================
    def _initialize_workspace_env(self, env):
        env['help'] = self.lisp_help
        env['sleep'] = self._sleep
        self._gui_builtins_on_main(env)

    def _workspace_action(self, action):
        if self._busy():
            return
        def work():
            try:
                getattr(L.workspaces, action)()
                self._ui(self.listener_write, f';; Workspace: {L.workspaces.current.name or "Listener"}; saved: {L.workspaces.depth}\n', 'info')
                self._ui(self.set_inspector, '(fresh workspace)' if action == 'new' else '(workspace changed)')
                self._ui(LispMachine._show_workspace_status, self)
                self._ui(self.refresh_definitions)
            except Exception as error:
                self._ui(self._report_form_error, error)
        self._start(work)

    def _workspace_module_action(self, action):
        if self._busy():
            return
        path = filedialog.askopenfilename(title=action.capitalize()+' imported module',
            initialdir=self._file_dialog_dir(), filetypes=[('Lisp module', '*.lisp *.sld'), ('All files', '*')])
        if path:
            self._run_silent('('+action+' '+L.lisp_str(L.String(path))+')')

    def _show_workspace_status(self):
        label = getattr(self, 'status_left', None)
        if label is not None:
            label.configure(text=f'{L.workspaces.current.name or "Listener"} · saved {L.workspaces.depth}')

    def _gui_builtins_on_main(self, env=None):
        """Make the turtle and window built-ins run on the Tk thread, whichever thread calls them."""
        env = L.global_env if env is None else env
        for name in GUI_BUILTINS & set(env):
            value = env[name]
            if isinstance(value, L.Procedure) and value.native_fn is not None:
                if not getattr(value.native_fn, "on_main", False):
                    value.native_fn = self._on_main_fn(value.native_fn)
            elif callable(value) and not getattr(value, "on_main", False):
                env[name] = self._on_main_fn(value)

    def _on_main_fn(self, fn):
        def call(*args):
            return self._gui_call(fn, *args)
        call.on_main = True
        return call

    def _gui_call(self, fn, *args):
        """fn(*args) on the Tk thread; turtle objects it returns are wrapped to do the same."""
        args = [a._obj if isinstance(a, _OnMainThread) else a for a in args]
        result = self._ui(fn, *args)
        return _OnMainThread(self, result) if _is_gui_object(result) else result

    def _ui(self, fn, *args):
        """Call fn(*args) on the Tk thread and return its result. From the Lisp thread this waits."""
        if threading.current_thread() is threading.main_thread():
            return fn(*args)
        box, done = {}, threading.Event()
        self._calls.put((fn, args, box, done))
        while not done.wait(0.05):          # short waits let Stop's exception in
            pass
        if "error" in box:
            raise box["error"]
        return box.get("value")

    def _ui_post(self, fn, *args):
        """Call fn(*args) on the Tk thread without waiting for it (Listener output)."""
        if threading.current_thread() is threading.main_thread():
            fn(*args)
        else:
            self._calls.put((fn, args, None, None))

    def _sleep(self, seconds):
        """(sleep seconds) that Stop can cut short."""
        end = time.monotonic() + float(seconds)
        while (left := end - time.monotonic()) > 0:
            time.sleep(min(left, 0.05))

    def _busy(self) -> bool:
        """True, and say so, while Lisp code is still running."""
        if self._job is None:
            return False
        self.listener_write(";; Still running. Press Stop (Ctrl+Break) to end it.\n", "error")
        return True

    def _start(self, work, on_done=None) -> bool:
        """Run work() on the Lisp thread; then on_done(result, stopped) on the Tk thread.

        Returns False, and runs nothing, while earlier code is still running.
        """
        if self._busy():
            return False

        def body():
            try:
                result, stopped = work(), False
            except Stopped:
                result, stopped = None, True
            while True:                      # a late Stop must not lose the hand-back
                try:
                    self._calls.put((self._finish, (result, stopped, on_done), None, None))
                    return
                except Stopped:
                    stopped = True

        # Deep (non-tail) recursion needs more stack than a thread gets by default.
        old_size = threading.stack_size(64 * 1024 * 1024)
        try:
            self._job = threading.Thread(target=body, name="lispy-eval", daemon=True)
        finally:
            threading.stack_size(old_size)
        self._set_running(True)
        self._job.start()
        self.after(1, self._pump)
        return True

    def _pump(self):
        """Do what the Lisp thread asks of the Tk thread, then give the window a turn."""
        deadline = time.monotonic() + 0.03
        while self._job is not None and time.monotonic() < deadline:
            try:
                fn, args, box, done = self._calls.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:
                break
            try:
                value = fn(*args)
                if box is not None:
                    box["value"] = value
            except BaseException as e:      # noqa: BLE001 - handed back to the Lisp thread
                if box is not None:
                    box["error"] = e
            finally:
                if done is not None:
                    done.set()
        if self._job is not None:
            try:
                self.after(1, self._pump)
            except tk.TclError:              # the window is gone
                pass

    def _finish(self, result, stopped, on_done):
        self._job = None
        self._set_running(False)
        if stopped:
            self.listener_write(";; Stopped.\n", "error")
            self.set_inspector("Stopped")
        if on_done is not None:
            on_done(result, stopped)
        if getattr(self, '_basic_input_used', False):
            self._basic_input_used = False
            if not self.console_ready:
                self._show_prompt()

    def stop(self, event=None):
        """Stop button / Ctrl+Break: end the Lisp code that is running."""
        if self._job is not None and stop_thread(self._job):
            self.status_right.configure(text="Stopping...")
        return "break"

    def _set_running(self, running: bool):
        self.stop_button.configure(state="normal" if running else "disabled",
                                   bg=COLORS["error"] if running else COLORS["side_bg"])
        self.status_right.configure(text="Running..." if running else "Ready")
        LispMachine._show_workspace_status(self)
        try:
            self.eval_menu.entryconfigure("Stop", state="normal" if running else "disabled")
        except tk.TclError:
            pass

    def _run(self, code: str):
        """Evaluate `code`. Returns (value, error). Stdout is streamed to the Listener."""
        return self._eval_with_turtle(lambda: L.eval_exp(L.parse(code), L.global_env))

    def _evaluation_stdout(self):
        if lispy_terminal.terminal_output_active():
            return contextlib.nullcontext()
        if getattr(self, '_output_mode', 'listener') == 'ansi':
            return lispy_terminal.ansi_terminal_output()
        return contextlib.redirect_stdout(_ListenerWriter(self))

    def _eval_with_turtle(self, evaluate):
        """Call `evaluate()` with stdout streamed to the Listener. Returns (value, error)."""
        import turtle as _turtle

        # The turtle Screen is a process-wide singleton whose _RUNNING flag
        # can be flipped to False by transient WM events when a second Tk
        # root (the editor) exists in the same process, and closing the
        # window leaves it False. Force it back on before every evaluation,
        # so the next drawing command opens a fresh window.
        _turtle.TurtleScreen._RUNNING = True

        try:
            output = LispMachine._evaluation_stdout(self)
            with output, L.basic_io.input_from(lambda: LispMachine._basic_read_line(self)):
                return evaluate(), None
        except _turtle.Terminator:
            # Same transient condition; the window is actually alive.
            _turtle.TurtleScreen._RUNNING = True
            try:
                output = LispMachine._evaluation_stdout(self)
                with output, L.basic_io.input_from(lambda: LispMachine._basic_read_line(self)):
                    return evaluate(), None
            except _turtle.Terminator:
                # A genuine close — invite the user to reopen.
                return None, RuntimeError(
                    "Turtle window was closed. Use (reinit-turtle) or reopen it.")
        except Exception as e:                # noqa: BLE001
            return None, e
        
    def eval_form_at_cursor(self):
        tab = self.current_tab()
        if not tab or self._busy():
            return
        language = execution_language(tab)
        if language == 'BBC BASIC':
            self.eval_basic_at_cursor(backend='lispy')
            return
        if language == 'Python':
            text = tab.text
            selection = text.tag_ranges('sel')
            source = (text.get(selection[0], selection[1]) if selection else
                      text.get('insert linestart', 'insert lineend'))
            line = int(str(selection[0]).split('.')[0]) if selection else int(text.index('insert').split('.')[0])
            self.eval_buffer(python_source=True, source=source, source_line=line)
            return
        if language != 'Lisp':
            self.listener_write(';; Select a Lisp, BBC BASIC or Python language for execution.\n', 'info')
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
        self._start(lambda: self._run(form),
                    lambda result, stopped: stopped or self._report_eval(*result, code=form))

    def _editor_syntax_error(self, tab, error):
        self.listener_write(f"Syntax error: {error}\n", 'error')
        LispMachine._highlight_source_error(self, tab, error)

    def _highlight_source_error(self, tab, error):
        if getattr(error, 'lineno', None):
            index = f'{error.lineno}.{max(0, (error.offset or 1)-1)}'
            tab.text.mark_set('insert', index)
            tab.text.see(index)
            tab.text.focus_set()
            tab._syntax_error_source = tab.get_content()
            tab.text.tag_remove('syntax_error', '1.0', 'end')
            end = f'{error.lineno}.end' if getattr(error, 'whole_line', False) else index+'+1c'
            tab.text.tag_add('syntax_error', index, end)
            tab.text.tag_raise('syntax_error')

    def check_buffer_syntax(self):
        tab = self.current_tab()
        if not tab:
            return
        if tab.language.name != 'Lisp':
            self.listener_write(';; Check Lisp syntax requires a Lisp buffer.\n', 'info')
            return
        tab.text.tag_remove('syntax_error', '1.0', 'end')
        tab._syntax_error_source = None
        try:
            ET.check_lisp(tab.get_content(), tab.path or tab.name)
        except SyntaxError as error:
            self._editor_syntax_error(tab, error)
            return
        self.listener_write(f';; {tab.name}: Lisp reader syntax OK (no execution).\n', 'info')

    def reindent_buffer(self):
        tab = self.current_tab()
        if not tab or self._busy():
            return
        source = tab.get_content()
        try:
            if tab.language.name == 'Lisp':
                formatted = ET.indent_lisp(source, tab.path or tab.name)
            elif tab.language.name == 'BBC BASIC':
                formatted = ET.indent_basic(source)
            else:
                self.listener_write(';; Reindent supports Lisp and BASIC buffers.\n', 'info')
                return
        except SyntaxError as error:
            self._editor_syntax_error(tab, error)
            return
        text = tab.text
        selection = text.tag_ranges('sel')
        if selection:
            first = int(str(selection[0]).split('.')[0])-1
            last_line, last_col = map(int, str(selection[1]).split('.'))
            stop = last_line if last_col else last_line-1
            original_lines = source.splitlines(keepends=True)
            new_lines = formatted.splitlines(keepends=True)
            original_lines[first:stop] = new_lines[first:stop]
            formatted = ''.join(original_lines)
        if formatted == source:
            return
        cursor = text.index('insert')
        separators = text.cget('autoseparators')
        text.edit_separator()
        text.configure(autoseparators=False)
        try:
            text.delete('1.0', 'end-1c')
            text.insert('1.0', formatted)
        finally:
            text.edit_separator()
            text.configure(autoseparators=separators)
        text.mark_set('insert', cursor)
        text.see('insert')
        tab._schedule_highlight()

    def _write_closers(self, tab, content: str, closers: str) -> str:
        """Put the missing `closers` at the end of the last code line and say so."""
        pos = L.close_position(content)
        index = offset_to_pos(content, pos)
        tab.text.insert(index, closers)
        tab._schedule_highlight()
        self.listener_write(f";; added {closers} at the end of line {index.split('.')[0]}\n", "info")
        return content[:pos] + closers + content[pos:]

    def _parse_top_level_forms(self, content: str, source_name=None):
        """Split buffer text into a list of top-level forms using the interpreter's own parser."""
        tokens = L.tokenize(content, source_name=source_name)
        forms = []
        while tokens:
            forms.append(L.read_from_tokens(tokens))
        return forms

    def eval_buffer_listener(self):
        self.basic_output.set('listener')
        self._save_basic_settings()
        self.eval_buffer(terminal=False, fresh=True)

    def eval_buffer_in_terminal(self):
        self.basic_output.set('ansi')
        self._save_basic_settings()
        self.eval_buffer(terminal=True, fresh=True)

    def eval_bbcsdl_buffer(self):
        tab = self.current_tab()
        if not tab or self._busy():
            return
        source = tab.get_content()
        settings = dict(self.settings)
        origin = buffer_source_path(tab)
        cwd = os.path.dirname(origin) if origin else APP_DIR
        def run():
            try:
                self.listener_write(';; Running real BBC BASIC for SDL in its own window.\n', 'info')
                status = BR.run_bbcsdl(source, cwd=cwd, executable=settings.get('bbcsdl_executable', ''),
                                      helper=settings.get('bbcsdl_helper', ''))
                self.listener_write(f';; BBCSDL exited with status {status}.\n', 'info' if status == 0 else 'error')
            except Exception as error:
                self.listener_write(f';; BBCSDL: {error}\n', 'error')
        self._start(run)

    def eval_basic_buffer(self, backend='python'):
        self.eval_buffer(basic=True, basic_backend=backend)

    def eval_basic_at_cursor(self, backend='python'):
        tab = self.current_tab()
        if not tab or self._busy():
            return
        text = tab.text
        selection = text.tag_ranges('sel')
        source = (text.get(selection[0], selection[1]) if selection
                  else text.get('insert linestart', 'insert lineend'))
        line = int(str(selection[0]).split('.')[0]) if selection else int(text.index('insert').split('.')[0])
        self.eval_buffer(basic=True, basic_backend=backend, source=source, source_line=line)

    def _save_basic_settings(self):
        self.settings.pop('basic_backend', None)
        self.settings['basic_pygame'] = self.basic_pygame.get()
        self.settings['basic_output'] = self.basic_output.get()
        self._output_mode = self.basic_output.get()
        save_settings(self.settings)

    def _open_basic_settings(self):
        if self.basic_settings_window is not None and self.basic_settings_window.winfo_exists():
            self.basic_settings_window.lift()
            return
        window = self.basic_settings_window = tk.Toplevel(self)
        window.title('BASIC Settings')
        window.transient(self)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='BASIC: F5/F6 use Lispy mini-basic; F7/F8 use Python mini_basic.').pack(anchor='w', pady=(0,12))
        status = tk.StringVar(window, value='Settings are saved automatically.')

        def save():
            self._save_basic_settings()
            status.set('Saved. Applies to the next run.')

        native = ttk.LabelFrame(frame, text='Real BBC BASIC for SDL', padding=8)
        native.pack(fill='x', pady=(0,12))
        for label, key, default in (('Executable', 'bbcsdl_executable', BR.default_bbcsdl()),
                                    ('Native basrun.bbc', 'bbcsdl_helper', '')):
            row = ttk.Frame(native)
            row.pack(fill='x', pady=4)
            ttk.Label(row, text=label, width=18).pack(side='left')
            value = tk.StringVar(window, value=self.settings.get(key) or default)
            ttk.Entry(row, textvariable=value, state='readonly', width=55).pack(side='left', fill='x', expand=True)
            def choose_native(key=key, value=value):
                path = filedialog.askopenfilename(parent=window, title='Select '+key,
                    filetypes=[('All files', '*')])
                if path:
                    self.settings[key] = path
                    value.set(path)
                    save()
            ttk.Button(row, text='Browse…', command=choose_native).pack(side='left')
        ttk.Label(native, text='Runs in BBCSDL’s own window; Listener/ANSI applies to mini-basic.').pack(anchor='w')
        python = ttk.LabelFrame(frame, text='Python mini_basic', padding=8)
        python.pack(fill='x', pady=(0,12))
        ttk.Checkbutton(python, text='SDL graphics window (hold after running)',
                        variable=self.basic_pygame, command=save).pack(anchor='w')
        ttk.Label(python, text='Leave SDL off for terminal-only programs. SDL mirrors text when enabled.').pack(anchor='w', pady=(0,8))
        for label, key, choose, default in (
                ('Project directory', 'basic_directory', self._choose_basic_directory, BR.default_package_root()),
                ('Python executable', 'basic_python', self._choose_basic_python, lispy_terminal.console_python())):
            row = ttk.Frame(python)
            row.pack(fill='x', pady=4)
            ttk.Label(row, text=label, width=18).pack(side='left')
            value = tk.StringVar(window, value=self.settings.get(key) or default)
            ttk.Entry(row, textvariable=value, state='readonly', width=55).pack(side='left', fill='x', expand=True)

            def browse(choose=choose, value=value, key=key, default=default):
                choose()
                value.set(self.settings.get(key) or default)
                status.set('Settings are saved automatically.')

            ttk.Button(row, text='Browse…', command=browse).pack(side='left', padx=(8,0))
        ttk.Label(frame, textvariable=status).pack(anchor='w', pady=(0,8))
        ttk.Button(frame, text='Close', command=window.destroy).pack(anchor='e')

    def _choose_basic_directory(self):
        path = filedialog.askdirectory(title='Python mini_basic project directory',
            initialdir=self.settings.get('basic_directory') or BR.default_package_root() or APP_DIR)
        if path:
            if not os.path.isfile(os.path.join(path, 'mini_basic', '__main__.py')):
                messagebox.showerror('mini_basic directory', 'Choose the project directory containing mini_basic/__main__.py')
                return
            self.settings['basic_directory'] = path
            self._save_basic_settings()

    def _choose_basic_python(self):
        path = filedialog.askopenfilename(title='Python interpreter for mini_basic')
        if path:
            self.settings['basic_python'] = path
            self._save_basic_settings()

    def _basic_error_highlight(self, tab, source, message, first_line, original, numbered=False):
        line = BR.error_source_line(source, message, first_line, numbered)
        if line is None or tab.get_content() != original:
            return
        error = SyntaxError(str(message))
        error.lineno, error.offset, error.whole_line = line, 1, True
        LispMachine._highlight_source_error(self, tab, error)

    def _run_python_basic_buffer(self, tab, source, source_line, terminal=False, python_source=False):
        original = tab.get_content()
        settings = dict(getattr(self, 'settings', {}))
        graphics = getattr(self, 'basic_pygame', None)
        pygame = graphics is not None and graphics.get()
        timing = getattr(self, 'time_buffer_runs', None)
        timed = timing is not None and timing.get()
        origin = buffer_source_path(tab)
        cwd = os.path.dirname(os.path.abspath(origin)) if origin else os.getcwd()
        filename = getattr(tab, 'path', None) or tab.name
        label = 'Python' if python_source else 'Python mini_basic'

        def work():
            started = time.perf_counter() if timed else None
            def write(line):
                if terminal:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                else:
                    self._ui_post(self.listener_write, line, 'result')
                if python_source:
                    location = re.search(r'File "'+re.escape(filename)+r'", line (\d+)', line)
                    if location:
                        error = SyntaxError('Python error')
                        error.lineno, error.offset, error.whole_line = int(location[1]), 1, True
                        def highlight(error=error):
                            if tab.get_content() == original:
                                LispMachine._highlight_source_error(self, tab, error)
                        self._ui(highlight)
                elif re.match(r'^\s*(?:\?|error\b|[A-Za-z_]*(?:Error|Exception)\b)', line, re.IGNORECASE):
                    self._ui(LispMachine._basic_error_highlight, self, tab, source, line, source_line, original, True)
            try:
                output = lispy_terminal.ansi_terminal_output() if terminal else contextlib.nullcontext()
                with output:
                    if python_source:
                        status = BR.run_python_source(source, write, cwd=cwd,
                            executable=settings.get('basic_python'), filename=filename, source_line=source_line)
                    else:
                        status = BR.run_python_basic(source, write, cwd=cwd,
                            executable=settings.get('basic_python'),
                            package_root=settings.get('basic_directory') or BR.default_package_root(), pygame=pygame)
                if not python_source and not pygame and status == 10:
                    self._ui(self.listener_write, ';; Python mini_basic finished (console hold requested).\n', 'info')
                else:
                    self._ui(self.listener_write, f';; {label} exited with status {status}.\n', 'info' if status == 0 else 'error')
            except Exception as error:
                self._ui(self._report_form_error, error)
            finally:
                if started is not None:
                    self._ui(self.listener_write, f';; Buffer elapsed time: {time.perf_counter()-started:.3f} s\n', 'info')
        self._start(work)

    def _eval_forms_in_terminal(self, forms, on_error=None):
        try:
            with lispy_terminal.ansi_terminal_output():
                if on_error is not None:
                    self._eval_forms(forms, on_error=on_error)
                else:
                    self._eval_forms(forms)
        except Exception as error:
            self._ui(self._report_form_error, error)

    def load_library_silently(self):
        if self._busy():
            return
        path = filedialog.askopenfilename(title="Load library silently", initialdir=L.LISP_DIR,
                                          filetypes=[("Lisp source", "*.lisp"), ("All files", "*")])
        if path:
            self._run_silent('(load '+L.lisp_str(L.String(path))+' :silent)')

    def eval_buffer(self, terminal=None, basic=False, source=None, source_line=1,
                    basic_backend='lispy', python_source=False, fresh=False):
        tab = self.current_tab()
        if not tab or self._busy():
            return
        content = tab.get_content() if source is None else source
        if not basic and not python_source:
            language = execution_language(tab)
            basic = language == 'BBC BASIC'
            python_source = language == 'Python'
            if not basic and not python_source and language != 'Lisp':
                self.listener_write(';; Select a Lisp, BBC BASIC or Python language for execution.\n', 'info')
                return
        if terminal is None:
            output = getattr(self, 'basic_output', None)
            terminal = output is not None and output.get() == 'ansi'
        if python_source or (basic and basic_backend == 'python'):
            if content.strip():
                LispMachine._run_python_basic_buffer(self, tab, content, source_line,
                    terminal=terminal, python_source=python_source)
            return
        if basic and not terminal and basic_backend == 'lispy':
            if not self.basic_repl_mode.get():
                self.listener_mode.set('basic')
                self._select_listener_mode()
            self._focus_listener()
            if source is None:
                cmd_lines = ['RUN']
                echo_text = 'RUN'
            else:
                cmd_lines = [ln for ln in source.splitlines() if ln.strip()]
                echo_text = ' : '.join(cmd_lines)
            if self.console_ready:
                self.listener_text.insert('end', echo_text + '\n')
                self.console_ready = False
            else:
                self.listener_write(f'BASIC> {echo_text}\n', 'prompt')
            self._basic_feed(cmd_lines, source=source, source_line=source_line)
            return
        self.listener_write(f";; --- evaluating {tab.name} ---\n", "info")
        closers = '' if basic else L.missing_closers(content)
        if closers:
            content = self._write_closers(tab, content, closers)

        if not content.strip():
            self.listener_write(";; (empty buffer)\n", "info")
            self.listener_write(";; --- done ---\n", "info")
            return

        try:
            if basic:
                # Quote source as a Lisp string; never parse BASIC as Lisp or
                # insert Lisp closing brackets into the user's BASIC buffer.
                forms = self._parse_top_level_forms(
                    '(import (prefix (only mini-basic bbc-run) editor-basic:))\n'
                    '(editor-basic:bbc-run '+L.lisp_str(L.String(content))+')')
            else:
                forms = self._parse_top_level_forms(content, source_name=getattr(tab, 'path', None) or tab.name)
        except Exception as e:                       # noqa: BLE001
            if isinstance(e, SyntaxError) and getattr(e, 'lineno', None) and hasattr(tab, 'text'):
                LispMachine._editor_syntax_error(self, tab, e)
            else:
                self.listener_write(f"Parse error: {e}\n", "error")
            self.listener_write(";; --- done ---\n", "info")
            return

        timing = getattr(self, 'time_buffer_runs', None)
        timed = timing is not None and timing.get()
        original = tab.get_content()

        def basic_error(error):
            self._report_form_error(error)
            LispMachine._basic_error_highlight(self, tab, content, str(error), source_line, original)

        def run_buffer():
            started = time.perf_counter() if timed else None
            try:
                if fresh:
                    try:
                        L.workspaces.new('Run: '+tab.name)
                        self._ui(LispMachine._show_workspace_status, self)
                    except Exception as error:
                        self._ui(self._report_form_error, error)
                        return
                if terminal:
                    if basic:
                        LispMachine._eval_forms_in_terminal(self, forms, on_error=basic_error)
                    else:
                        self._eval_forms_in_terminal(forms)
                else:
                    if basic:
                        self._eval_forms(forms, on_error=basic_error)
                    else:
                        self._eval_forms(forms)
            finally:
                if started is not None:
                    elapsed = time.perf_counter() - started
                    self._ui(self.listener_write, f";; Buffer elapsed time: {elapsed:.3f} s\n", "info")

        self._start(run_buffer)

    def _eval_forms(self, forms, on_error=None):
        """Run the buffer's forms one by one on the Lisp thread, reporting each on the Tk thread."""
        for form in forms:
            self._ui(self._echo_form, form)

            def run_form(form=form):
                # Expand each form just before it runs, as the REPL does, so
                # defun, quasiquote and macros defined earlier in the buffer work.
                form = L.expand(form, toplevel=True)
                return form, L.eval_exp(form, L.global_env)

            result, err = self._eval_with_turtle(run_form)
            if err is not None:
                self._ui(on_error or self._report_form_error, err)
                return
            self._ui(self._report_form, *result)
        self._ui(self.listener_write, ";; --- done ---\n", "info")

    def _echo_form(self, form):
        try:
            form_str = L.lisp_str(form)
        except Exception:
            form_str = repr(form)
        if len(form_str) > 120:
            form_str = form_str[:117] + "..."
        self.listener_write("USER> ", "prompt")
        self.listener_write(f"{form_str}\n", "code")

    def _report_form_error(self, e):
        msg = L.RECURSION_HINT if isinstance(e, RecursionError) else (str(e) or type(e).__name__)
        self.listener_write(f"Error: {msg}\n", "error")
        self.set_inspector(f"Error: {msg}")
        self.listener_write(";; --- aborted ---\n", "info")

    def _report_form(self, form, val):
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
        """Shift+F7: inspect the symbol under the editor cursor or in the Listener."""
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
        self._start(lambda: self._run(code), lambda result, stopped: stopped or self._show_silent(*result))

    def _show_silent(self, val, err):
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
        if not code.strip() or self._busy():
            return
        self.listener_input.delete(0, "end")
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
        self._start(lambda: self._run(code),
                    lambda result, stopped: stopped or self._report_eval(*result, code=code))

    # ---------- plain lispy3 REPL mode ----------
    def _basic_mode(self):
        mode = getattr(self, 'basic_repl_mode', None)
        return bool(mode is not None and mode.get())

    def _read_basic_repl_source(self, path):
        if path.suffix.lower() == '.bbc':
            return BR.detokenize_bbc(str(path), executable=self.settings.get('basic_python') or None,
                                     package_root=self.settings.get('basic_directory', ''))
        return path.read_text(encoding='utf-8-sig')

    def _select_listener_mode(self):
        if self._busy():
            self.listener_mode.set('basic' if self.basic_repl_mode.get() else
                                   'lisp' if self.plain_repl.get() else 'listener')
            return
        mode = self.listener_mode.get()
        self.repl_pending = ''
        self.plain_repl.set(mode != 'listener')
        self.basic_repl_mode.set(mode == 'basic')
        if self.console_ready:
            self.listener_text.delete('prompt_start', 'end-1c')
            self.console_ready = False
        self._apply_repl_mode()
        self.settings['basic_repl'] = self.basic_repl_mode.get()
        self.settings['plain_repl'] = self.plain_repl.get()
        save_settings(self.settings)
        self.listener_write(';; BASIC REPL: HELP lists commands; state is separate from Lisp.\n'
                            if self.basic_repl_mode.get() else ';; Lisp listener mode restored.\n', 'info')
        self._focus_listener()

    def _get_basic_buffer_text(self):
        return getattr(self, '_cached_basic_buffer', '')

    def _begin_basic_input(self, replies):
        self._basic_input_queue = replies
        self._basic_input_used = True
        self.plain_repl.set(True)
        self.basic_repl_mode.set(True)
        self.listener_mode.set('basic')
        self.input_row.pack_forget()
        t = self.listener_text
        t.configure(state='normal')
        t.mark_set('input', 'end-1c')
        t.mark_gravity('input', 'left')
        self.console_ready = True
        self._focus_listener()
        t.see('end')

    def _end_basic_input(self, replies):
        if getattr(self, '_basic_input_queue', None) is replies:
            self._basic_input_queue = None
            self.console_ready = False

    def _basic_read_line(self):
        """Wait on the worker while Tk accepts a raw program reply; Stop stays active."""
        if lispy_terminal.terminal_output_active():
            return lispy_terminal.read_line()
        replies = queue.Queue()
        try:
            self._ui(LispMachine._begin_basic_input, self, replies)
            while True:
                try:
                    return replies.get(timeout=0.05)
                except queue.Empty:
                    pass
        finally:
            self._ui(LispMachine._end_basic_input, self, replies)

    def _cache_current_buffer_for_basic(self):
        tab = self.current_tab()
        self._cached_basic_buffer = tab.get_content() if tab is not None else ''

    def _basic_feed(self, lines, source=None, source_line=1):
        if self._busy():
            self._show_prompt()
            return
        self._cache_current_buffer_for_basic()
        lines = list(lines)
        tab = self.current_tab()
        original = self._get_basic_buffer_text()
        error_source = source
        if source is None and any(line.strip().upper() == 'RUN' for line in lines):
            error_source = original
        timing = getattr(self, 'time_buffer_runs', None)
        timed = error_source is not None and timing is not None and timing.get()
        def work():
            def evaluate():
                if source is not None:
                    # Execute selections as one program, preserving physical
                    # line numbers, labels and multiline control flow.
                    try:
                        if source.strip():
                            self.basic_repl._execute(source)
                    except SystemExit:
                        pass
                    return
                for line in lines:
                    if line.strip():
                        self.listener_history.append(line)
                        self.listener_hist_idx = len(self.listener_history)
                        self.basic_repl.submit(line)
            started = time.perf_counter() if timed else None
            try:
                return self._eval_with_turtle(evaluate)
            finally:
                if started is not None:
                    self._ui(self.listener_write,
                             f';; Buffer elapsed time: {time.perf_counter()-started:.3f} s\n', 'info')
        def done(result, stopped):
            if not stopped:
                _, error = result
                if error is not None:
                    self.listener_write(f'Error: {error}\n', 'error')
                    self.set_inspector(f'Error: {error}')
                    if tab is not None and error_source is not None:
                        LispMachine._basic_error_highlight(
                            self, tab, error_source, str(error), source_line, original)
            self._show_prompt()
        self._start(work, done)

    # The Listener text itself becomes the console: the prompt and what you type
    # sit on the last line, after the "input" mark, and scroll with the output.
    def _prompt_text(self) -> str:
        """lispy3> or, inside an unfinished form, ... (n)> as lispy3.py shows."""
        if LispMachine._basic_mode(self):
            return 'BASIC>'
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
        replies = getattr(self, '_basic_input_queue', None)
        if replies is not None:
            line = self._console_input()
            t.insert('end', '\n')
            self.console_ready = False
            self._basic_input_queue = None
            replies.put(line)
            return 'break'
        self._console_recolor()
        line = self._console_input()
        t.insert("end", "\n")
        self.console_ready = False
        self._plain_feed(line.split("\n"))   # pasted lines are read one by one, as in a terminal
        return "break"

    def _plain_feed(self, lines: list[str]):
        """Give the plain REPL its lines; a complete form runs in the background, then the rest follow."""
        if LispMachine._basic_mode(self):
            self._basic_feed(lines)
            return
        while lines:
            line = lines.pop(0)
            if not self.repl_pending and line.strip().lower() == "exit":
                self._on_close()
                try:
                    if self.plain_repl.get():    # quitting was cancelled
                        self._show_prompt()
                except tk.TclError:              # the window is closed
                    pass
                return
            code = self._plain_submit(line)
            if code is not None:
                def done(result, stopped, code=code):
                    if stopped:
                        lines.clear()
                    else:
                        self._report_eval(*result, code=code, plain=True)
                    self._plain_feed(lines)
                self._start(lambda: self._run(code), done)
                return
        if self.plain_repl.get():
            self._show_prompt()

    def _plain_submit(self, line: str):
        """One line typed at the plain REPL, as lispy3.repl reads it.

        Returns the code to evaluate once the form is complete, else None.
        """
        if not self.repl_pending and not line.strip():
            return None
        self.listener_history.append(line)
        self.listener_hist_idx = len(self.listener_history)
        code = f"{self.repl_pending}\n{line}" if self.repl_pending else line
        if L.count_balance(code) > 0:
            self.repl_pending = code
            return None
        self.repl_pending = ""
        return code

    def _cancel_pending(self, event=None):
        """Esc: drop what is typed and any unfinished form, or stop the code that is running."""
        if self._job is not None:
            return self.stop()
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
        basic = LispMachine._basic_mode(self)
        files = filename_completion(before, basic=basic,
                                    cwd=self.basic_repl.directory if basic else None)
        if files is not None:
            start, matches = files
            if not matches:
                self.bell()
                return 'break'
            shared = common_prefix(matches)
            if shared != before[start:]:
                t.delete(f'input+{start}c', 'insert')
                t.insert('insert', shared)
            else:
                self.listener_write('  '.join(matches)+'\n', 'info')
            return 'break'
        m = SYMBOL_TAIL.search(before)
        prefix = m.group(0) if m else ""
        if not prefix:
            return "break"
        if LispMachine._basic_mode(self):
            language = SH.language_for('listener.bas', LANGUAGES, DEFAULT_LANGUAGE)
            names = {name.upper() for name in language.words} | {'RUN', 'LIST', 'NEW', 'LOAD', 'SAVE', 'HELP'}
            matches = sorted(name for name in names if name.startswith(prefix.upper()))
        else:
            matches = L.complete_names(prefix)
        if not matches:
            self.bell()
            return "break"
        shared = common_prefix(matches)
        if len(matches) == 1:
            shared += " "
        if LispMachine._basic_mode(self):
            if shared != prefix:
                t.delete(f'input+{len(before)-len(prefix)}c', 'insert')
                t.insert('insert', shared)
            else:
                self.listener_write('  '.join(matches)+'\n', 'info')
            return 'break'
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
            language = SH.language_for('listener.bas', LANGUAGES, DEFAULT_LANGUAGE) if LispMachine._basic_mode(self) else LISP_LANGUAGE
            color_code(self.listener_text, "input", self._console_input(), language)
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
        if LispMachine._basic_mode(self):
            if self._busy():
                return
            tab = self.new_buffer('basic-repl.bas', self.basic_repl.source())
            tab.dirty = True
            self._refresh_buffer_list()
            return
        t = self.listener_text
        end = "prompt_start" if self.console_ready else "end-1c"   # leave out the live prompt line
        code = listener_to_code(t.get("1.0", end))
        tab = self.new_buffer("listener.lisp", code)
        tab.dirty = True
        self._refresh_buffer_list()

    def _clear_listener_screen(self):
        """Program CLS clears output without injecting a prompt into a running job."""
        t = self.listener_text
        t.configure(state='normal')
        if getattr(self, '_basic_input_queue', None) is not None:
            end = 'input'
        else:
            end = 'prompt_start' if self.console_ready else 'end'
        t.delete('1.0', end)
        if not self.plain_repl.get():
            t.configure(state='disabled')

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

    def _refresh_changed_buffers(self):
        """Refresh opened text files; never evaluate them or overwrite dirty edits silently."""
        for tab in list(self.tabs.values()):
            if not tab.path or getattr(tab, 'disk_content', None) is None:
                continue
            try:
                with open(tab.path, encoding='utf-8') as source:
                    content = source.read()
            except (OSError, UnicodeError) as error:
                self.listener_write(f';; Cannot check {tab.path}: {error}\n', 'error')
                continue
            if content == tab.disk_content:
                continue
            if tab.dirty and not messagebox.askyesno('File changed on disk',
                    f'{tab.path}\n\nThis buffer also has unsaved edits. Replace them with the disk version?'):
                continue
            cursor = tab.text.index('insert')
            tab.set_content(content)
            tab.text.mark_set('insert', cursor)
            tab.dirty = False
            tab.disk_content = content
            self.listener_write(f';; Reloaded buffer from disk: {tab.path}\n', 'info')
        self._refresh_buffer_list()

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
        LispMachine._refresh_changed_buffers(self)
        if output:
            self.listener_write(output + "\n", "error" if result == "failed" else "info")
        if result == "failed":
            messagebox.showerror("Update failed", output or "git pull failed.")
        current = runtime_fingerprint()
        changed = sorted(name for name in current.keys() | RUNTIME_FINGERPRINT.keys()
                         if current.get(name) != RUNTIME_FINGERPRINT.get(name))
        if changed:
            self.update_pending = True
            self.listener_write(';; Runtime files changed on disk:\n  ' + '\n  '.join(changed) + '\n', 'info')
        if result == "updated":
            self.update_pending = True
        if not self.update_pending:
            if result != "failed":
                messagebox.showinfo("Update", "Lispy3 is already up to date.")
        elif messagebox.askyesno("Update", "Lispy3 runtime files have changed. The new version is used "
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
        if not self.startup_show_buffer.get():
            startup = os.path.normcase(os.path.abspath(STARTUP_FILE))
            files = [path for path in files if os.path.normcase(os.path.abspath(path)) != startup]
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
        messagebox.showinfo("About Lispy3 Machine", about_text() + "\n")

    def _on_close(self):
        if self._job is not None:
            if not messagebox.askyesno("Code is running", "Lisp code is still running. Stop it and quit?"):
                return
            stop_thread(self._job)
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
    if "--version" in sys.argv[1:] or "-V" in sys.argv[1:]:
        print(version_text())
        return
    plain_repl, files = parse_args(sys.argv[1:])
    app = LispMachine(files, plain_repl=True if plain_repl else None)
    app.mainloop()


if __name__ == "__main__":
    main()
