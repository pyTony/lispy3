# Lispy3: A Modern Clojure-Infused Lisp Interpreter in Python 3 — with a Lisp-Machine Editor

A fully typed, robust, and elegant Lisp/Scheme interpreter written in modern Python 3, plus a companion Tkinter editor (`lispy_machine.pyw`) that turns it into an interactive Lisp-Machine style environment. This project is a deeply evolutionized version of Peter Norvig's classic `lis.py`, incorporating modern Python features and powerful Clojure-inspired constructs.

The roots of this project date back to a spark of inspiration from a 1981 Finnish computer magazine (*Prosessori*), leading to a Python 2 adaptation on the DaniWeb forums in 2011, and finally culminating in this modern, pattern-matching Python 3 masterpiece.

## Documentation

- [Quick Start](docs/QUICK_START.md): five minutes from nothing to your own functions.
- [Lispy by Example](docs/LISPY_BY_EXAMPLE.md): strings, lists, head and tail recursion, loops, maps and more, one runnable example at a time.
- [Quick Reference](docs/QUICK_REFERENCE.md): every built-in on one page.
- Inside Lispy, `(help)` lists the built-ins and `(help 'name)` explains one. In the editor, `(help)` and **Help → Lispy guide** (F1) open the guide in its own window.
- [CHANGELOG.md](CHANGELOG.md): what changed in each release.
- [TODO.md](TODO.md): features not implemented yet, with pointers to reference implementations in [fluentpython/lispy](https://github.com/fluentpython/lispy).

## Contents

- [Documentation](#documentation)
- [Key features](#key-features)
- [Files in this project](#files-in-this-project)
- [Quick start (REPL)](#quick-start-repl)
- [REPL example usage](#repl-example-usage)
- [Running programs](#running-programs)
- [Loops, vectors and timing](#loops-vectors-and-timing)
- [L-systems with turtle graphics](#l-systems-with-turtle-graphics)
  - [How the files fit together](#how-the-files-fit-together)
  - [Your own L-system](#your-own-l-system)
- [**Lispy3 Machine — the editor**](#lispy3-machine--the-editor)
  - [Running the editor](#running-the-editor)
  - [The layout](#the-layout)
  - [Key bindings](#key-bindings)
  - [Buffers and the Listener](#buffers-and-the-listener)
  - [Inspector](#inspector)
  - [Syntax colouring](#syntax-colouring)
  - [Search and replace](#search-and-replace)
  - [How the editor drives the interpreter](#how-the-editor-drives-the-interpreter)
  - [Routing `display` output into the Listener](#routing-display-output-into-the-listener)
  - [A short tour](#a-short-tour)

---

## Key features

**Interpreter (`lispy3.py`)**

- **Structural Pattern Matching**: Powered entirely by Python 3's `match-case` syntax for clean, compiler-like abstract syntax tree (AST) evaluation.
- **Smart Auto-Closing Brackets**: Forgives unclosed parentheses, brackets, or braces at the end of a line in the REPL (no more counting trailing delimiters!).
- **Clojure Data Structures**:
  - `()` for code and execution blocks.
  - `[]` for ordered data Vectors (Python tuples).
  - `{}` for associative Maps/Dictionaries (Python dicts).
- **Clojure Keywords & Property Lists**: Keywords starting with `:` evaluate to themselves. If a keyword is called as a function (e.g. `(:name user)`), it performs a direct dictionary lookup.
- **Full String Literals Support**: Differentiates between Lisp symbols (variable names) and raw string values using Python `dataclasses`.
- **Workspace State Management**: Built-in environment persistence via `(save "filename")` and `(load "filename")`, which serialize/deserialize user functions and variables as valid, human-readable Lisp source code.
- **Turtle Graphics**: Every `turtle.*` name is available as a Lisp procedure; `push-pose` / `pop-pose` / `clear-poses` implement the `[` … `]` branching of L-systems.

**Editor (`lispy_machine.pyw`)**

- **Multiple editor buffers** with syntax colouring read from `syntax/*.json` (Lisp and Python included).
- **Persistent Listener** with history, coloured prompts/results/errors.
- **Inspector pane** showing the pretty-printed last value.
- **Evaluate form at cursor** or the whole buffer without restarting the interpreter.
- **Search & replace** with case / whole-word / regex options, next/previous, replace-all.
- **Paren matching**, auto-indent, and **symbol completion** (`Ctrl+Space`).
- **`display` routed into the Listener** — no more stray terminal output.

---

## Files in this project

| File | Role |
|------|------|
| `lispy3.py` | The interpreter (REPL + `python lispy3.py file.lisp` script runner). |
| `lisp/` | The folder for Lisp programs: the examples below live here, `(save "name")` writes here, and `(load "name")` and the editor's Open / Save as look here. |
| `lisp/lsystems.lisp` | The L-system drawing engine used by every example. |
| `lisp/tree.lisp`, `lisp/plant.lisp`, `lisp/snowflake.lisp` | The three example L-systems from *The Algorithmic Beauty of Plants*. |
| `lisp/sieve_lispy3.lisp` | The Byte magazine prime sieve, rewritten for lispy3. |
| `lisp/pi_digits.lisp` | Prints the first n decimals of pi with a spigot algorithm. |
| `lisp/my_workspace.lisp` | Example of a saved workspace (produced by `(save "my_workspace")`). |
| `lispy_machine.pyw` | The Lisp-Machine style editor. |
| `startup.lisp` | Opens in the editor when it starts without a file (a short tour); change it to start with your own code, or delete it to start with an empty buffer. |
| `syntax_highlight.py`, `syntax/*.json` | Editor syntax colouring: the engine, and one rules-and-colours file per language. |
| `docs/QUICK_START.md`, `docs/LISPY_BY_EXAMPLE.md`, `docs/QUICK_REFERENCE.md` | The user manual. |
| `TODO.md` | Features still to be implemented. |
| `tests/` | Regression tests from Norvig's [lispy.html](https://norvig.com/lispy.html). Run `python -m unittest` in this folder; no window opens. |

`lispy_machine.pyw` **imports `lispy3.py`** and uses it directly — it does not reimplement parsing, evaluation, printing, or turtle support.

---

## Quick start (REPL)

Run the interpreter directly using Python 3:

    python lispy3.py

### REPL example usage

    Modern Python 3 Lispy Interpreter Started.
    Features: Unclosed brackets are fixed, Clojure map/vector types supported.
    Workspace functions: (save "name") and (load "name") are active.

    lispy3> (define user {:name "Tony" :status "Trusty"})
    lispy3> (:name user)
    "Tony"

    lispy3> (define square (lambda [x] (* x x)))
    lispy3> (square 9)
    81

    lispy3> (save "my_workspace")
    Workspace saved to .../lisp/my_workspace.lisp

---

## Running programs

    python lispy3.py                  start the REPL
    python lispy3.py prog.lisp        run prog.lisp from top to bottom, then exit
    python lispy3.py -i prog.lisp     run prog.lisp, then stay in the REPL
    python lispy3.py --version        show the Lispy and Python versions
    python lispy3.py --help           show these options

(`-i` may also come after the file name.)

In the REPL, `Tab` completes the name you are typing: built-ins, special forms such as `define` and `lambda`, your own definitions, and the `:keywords` of maps you have defined. Press it twice to list every choice. `↑` / `↓` bring back earlier lines. This uses Python's `readline`, which Linux and macOS have; on Windows install it once with `pip install pyreadline3` (the REPL says so at start-up when it is missing).

A program file is ordinary Lisp code that runs from top to bottom, like a Python script. A `;` starts a comment. `(load "other")` runs another file first; the `.lisp` ending is optional. A file name without a folder is looked for in the current folder first and then in `lisp/`, so `python lispy3.py tree.lisp` and `(load "lsystems")` work from anywhere. `(save "name")` writes `lisp/name.lisp` unless you give a path. If the program drew with turtle graphics, the window stays open until you close it (not when you use `-i`, where you get the prompt instead).

---

## Loops, vectors and timing

| Form | What it does |
|------|--------------|
| `(while test body...)` | repeat the body while the test is true |
| `(make-vector n fill)` | a vector of `n` items, all `fill` (0 if left out); items are numbered from 0 |
| `(vector-ref v i)` | item `i` of vector `v` |
| `(vector-set! v i x)` | put `x` into item `i` of `v` |
| `(clock)` | seconds since Lispy started, as a decimal number, for timing |
| `(clock->string t)` | the (clock) value `t` as local date and time, like `"2026-10-17 21:53:20"`; leave `t` out for now; `(clock->string t "%H:%M")` takes a format |
| `(get-universal-time)` | seconds since 1900-01-01 GMT, as in Common Lisp |
| `(universal-time->string [ut] [format])` | a universal time (default now) as local `"2026-10-17 22:03:00"`; format like `"%H:%M"` |
| `(get-decoded-time)` | now as `(second minute hour date month year day-of-week daylight-p zone)` |
| `(decode-universal-time ut [zone])` | `ut` as that list; day 0 is Monday, `zone` is hours west of Greenwich |
| `(encode-universal-time s m h date month year [zone])` | back to a universal time |
| `(get-internal-real-time)` / `(get-internal-run-time)` | timer / processor time in `internal-time-units-per-second` (1000) units |
| `(sleep seconds)` | wait |
| `(display a b ...)` | print the values one after another, with nothing between them |

Good to know: `+ - * /` take exactly two arguments, so write `(+ (+ a b) c)`; `(if test then else)` always needs the else part; a `lambda` body is one expression, so wrap several in `(begin ...)`.

`sieve_lispy3.lisp` is the Byte magazine prime sieve written this way: `python lispy3.py sieve_lispy3.lisp`.

---

## L-systems with turtle graphics

![A tree drawn by tree.lisp](docs/tree.png)

*`python lispy3.py tree.lisp`: axiom `F`, rule `FF-[-F+F+F]+[+F-F-F]`, 4 generations, 23 degrees.*

An L-system draws a picture from a short string (the *axiom*) and a rewriting *rule*. Every generation replaces each `F` in the string by the rule. Once the generations are used up, the string is read as turtle commands:

| Symbol | Meaning |
|--------|---------|
| `F` | draw a line forward, `step` pixels long |
| `+` | turn left by `angle` degrees |
| `-` | turn right by `angle` degrees |
| `[` | remember the position and direction (a branch starts here) |
| `]` | go back to the remembered position and direction, without drawing |

Any other character is ignored. Only `F` is rewritten.

A small example, with axiom `F` and rule `F[+F]F`:

    generation 0:  F
    generation 1:  F[+F]F
    generation 2:  F[+F]F[+F[+F]F]F[+F]F

Read generation 1 as: a line, then a side branch turned left, back to where the branch began, then another line on the main stem.

### How the files fit together

    snowflake.lisp ─┐                      lsystems.lisp  (the engine)
    tree.lisp ──────┼─ (load "lsystems") ─▶   draw-node, draw-sys, lsystem-from, lsystem
    plant.lisp ─────┘

    each example file = settings + one call
      settings:  axiom, rule, angle, start position, generations, step
      call:      (tree generations step)  ─▶  (lsystem-from ...)  ─▶  turtle window

`lsystems.lisp` knows how to draw any L-system and is loaded by every example. An example file only holds the settings of one picture and a small function to draw it. Try `python lispy3.py tree.lisp`, `python lispy3.py plant.lisp` and `python lispy3.py snowflake.lisp`.

To change a picture, edit the numbers under `---- Settings ----` and run the file again, or keep the prompt open and redraw with different values:

    python lispy3.py -i tree.lisp
    lispy3> (tree 3 12)

The two numbers are `generations` and `step` (line length in pixels). If you close the turtle window, the next drawing command prints an error once; type `(reinit-turtle)` or just try again.

### Your own L-system

Copy `tree.lisp`, change the settings, and run it. Or draw one straight from the prompt:

    lispy3> (load "lsystems")
    lispy3> (lsystem-from "F" "F[+F]F[-F]F" 4 3 23.5 0 -250 90)

The arguments are `axiom rule generations step angle x y heading`. `x` and `y` are where the drawing starts, and `heading` is the starting direction in degrees (0 is right, 90 is up). `(lsystem axiom rule generations step angle x y)` is the same with heading 0.

The number of lines is (`F`s in the axiom) × (`F`s in the rule) to the power of `generations`. The tree rule has 8 `F`s, so each extra generation makes eight times as many lines and takes about that much longer to draw.

The tree and the plant come from *The Algorithmic Beauty of Plants* (page 25), as shown on <https://people.ece.cornell.edu/land/OldStudentProjects/cs490-94to95/hwchen/>.

---

# Lispy3 Machine — the editor

`lispy_machine.pyw` is a Tkinter editor that turns the interpreter into a small Lisp-Machine style environment: several buffers, one persistent Listener, an Inspector, and one-key evaluation of whatever is at the cursor. It is a *client* of `lispy3.py` — the interpreter itself is untouched.

### Running the editor

    python lispy_machine.pyw
    python lispy_machine.pyw tree.lisp      # open a file instead of startup.lisp
    python lispy_machine.pyw --version      # show the editor and lispy3 versions

Every file named on the command line opens in its own buffer. A bare file name that is not in the current folder means the file in `lisp/`. A name that does not exist yet opens an empty buffer that is created on the first **Save**. **File → Open** and **Save as** start in `lisp/` (or in the buffer's own folder). On Windows this also works with *Open with* or by dragging a `.lisp` file onto `lispy_machine.pyw`.

The window and taskbar icon come from `icons/lispy_machine.ico` (Windows) or `icons/lispy_machine.png`. To use your own picture, replace those files; `python icons/make_icon.py` redraws the starter λ icon. `python make_shortcut.py` puts a *Lispy Machine* launcher with this icon on your desktop. It works on Windows and Linux; on Linux it also adds Lispy Machine to the applications menu, and it starts the editor with the Python that ran the script, so use your venv's `python` if you have one.

The Listener's **To buffer** button (also **Eval → Listener to buffer**) opens what you did in the Listener as a new buffer that runs as a program: the `USER>`, `lispy3>` and `... (n)>` prompts are removed, results, output and errors become `;;` comments, and a form that gave an error is commented out too. Save it with Ctrl+S, or run it with F6.

**Help → Lispy guide** (F1) opens this manual in its own window: Quick Start, Lispy by Example, Quick Reference and a page of every built-in, with a contents list, working links, Back, and a search box that also says which other pages have what you typed. `(help)` in the Listener opens it at the built-ins; `(help 'name)` still prints one line there, and turns an open guide to that name. **Help → About** gives the credits.

**Help → Update** runs `git pull` in the program's folder, so a copy cloned with git updates without the command line. It warns about unsaved buffers first, and git refuses (and says which files) if your own edits to files in that folder would be overwritten. After a successful update it offers to restart the editor, reopening your saved buffers, so the new version is the one running.

`lispy_machine.pyw` and `lispy3.py` must sit in the **same folder** (or `lispy3.py` must be on `PYTHONPATH`). Importing `lispy3` has no side effects because the interpreter guards its entry point with `if __name__ == "__main__":`.

### The layout

```
┌───────── File · Edit · Eval · View · Help ─────────────┐
│ Buffers      │  Editor tabs: [untitled.lisp] [tree.lisp]│
│  ● untitled  │                                          │
│              │  (define fact                            │
│ INSPECTOR    │    (lambda [n] ...))                     │
│  {value}     │                                          │
├──────────────┴──────────────────────────────────────────┤
│ LISTENER                                                 │
│  USER> (fact 10)                                         │
│  3628800                                                 │
│  USER> [input line]                                       │
├──────────────────────────────────────────────────────────┤
│ USER                            buffer: untitled.lisp    │
└──────────────────────────────────────────────────────────┘
```

- **Buffers** — one tab per file. The `●` marker shows unsaved changes.
- **Inspector** — a list of everything you have defined (built-ins left out), each with a short preview of its value; click a name to see its value pretty-printed below the list. The lower part also shows the pretty-printed value of the last evaluation, or of a variable you just defined; the divider between list and value can be dragged. It scrolls both ways, and the dividers between sidebar and editor and between Buffers and Inspector can be dragged; the pretty-printer re-wraps to the Inspector's width.
- **Listener** — a persistent REPL at the bottom, exactly like a Genera Listener.
- **Status bar** — the current "package" (`USER`, matching the interpreter's single `global_env`) and the current buffer name.

### Key bindings

| Key | Action |
|-----|--------|
| `F1` | Open the Lispy guide (in the guide: `Ctrl+F` search, `Enter`/`F3` next match, `Alt+Left` back, `Esc` close) |
| `F5` / `Ctrl+Enter` | Evaluate the outermost form at the cursor |
| `F6` / `Ctrl+Shift+Enter` | Evaluate the whole buffer |
| `F7` | Inspect the symbol at the cursor (or the name typed in the Listener) |
| `F9` | Evaluate what you typed in the Listener |
| `Ctrl+F` | Open Find |
| `Ctrl+H` | Open Find & Replace |
| `F3` / `Shift+F3` | Next / previous match |
| `Ctrl+Space` | Complete a symbol (builtins, special forms, `:keywords` + every `define` in the buffer) |
| `Ctrl+/` | Toggle comment on the selected lines |
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S` | New / Open / Save / Save As |
| `Ctrl+W` | Close buffer |
| `Ctrl+L` | Clear Listener |
| `Ctrl+E` | Focus the Listener input |
| `Ctrl+Q` | Quit |

### Buffers and the Listener

The Listener is a real REPL backed by the interpreter's `global_env`. Code in the Listener and the Inspector (what you type, echoed forms and results) is coloured with the same Lisp colours as the editor; `display` output stays green and errors red. It supports `↑` / `↓` history, coloured prompts (`USER>`), coloured results, and coloured errors. Typing `exit` closes the editor.

**Plain lispy3 REPL.** Tick **View → Plain lispy3 REPL** (or start the editor with `python lispy_machine.pyw --repl`) and the Listener becomes a console like `python lispy3.py`, still sharing the editor's `global_env`: the `USER>` entry line goes away and you type at a `lispy3>` prompt in the Listener itself, so your input and the output scroll together. Enter on an unfinished form continues it on the next line under a `... (1)>` prompt, pasted lines are read one by one, `Tab` completes like readline (the shared start, then the list of choices) and `Ctrl+Space` opens the same pick list as elsewhere, `↑` / `↓` bring back earlier lines, `Esc` drops an unfinished form, and results are printed as the REPL prints them (nothing for a `define`, and a result too long for one line, such as a whole function, indented like in the Inspector). The text above the prompt is read-only: `←` stops at the prompt, and a click in older output puts the cursor back at the prompt (drag to select and copy). The choice is remembered in `~/.lispy3_machine.json`; untick it to get the `USER>` Listener back.

F5 finds the *outermost enclosing form* at the cursor — skipping strings, `;` comments, and characters such as `#\(` — and evaluates just that. This lets you re-evaluate a single `define` without rerunning the whole file or restarting the interpreter.

F6 wraps the whole buffer in `(begin …)` and evaluates it. That is precisely what `python lispy3.py file.lisp` does under the hood, so the results are identical.

Lispy closes brackets you leave open. When it does, you see the brackets it added: in the Listener they are printed at the end of your line, and with F5 or F6 they are written into the buffer at the end of the last line of code (before any `;` comment), with a `;; added ))` note in the Listener. `Ctrl+Z` takes them out again.

### Inspector

After every evaluation the Inspector pane shows the value using the interpreter's own `pretty_print`. Clojure-style maps and vectors expand vertically; procedures print as `(lambda …)` or as their native name. Long lists of atoms are packed into rows instead of one item per line. A `(define name …)` returns nothing, so the Inspector then shows the new value of `name`; press `F7` on any symbol to look at a variable later. If evaluation raised, the Inspector shows the error.

### Syntax colouring

The editor colours a buffer using the rules in `syntax/<language>.json`; the file's extension picks the language (`.lisp` and new buffers use `syntax/lisp.json`, `.py` uses `syntax/python.json`). Each file holds:

| Key | Meaning |
|-----|---------|
| `extensions` | File endings that use this language, e.g. `[".lisp", ".scm"]` |
| `line_comment` | What `Ctrl+/` puts in front of a line (`;` or `#`) |
| `colors` | Colour of each tag, e.g. `"string": "#ce9178"` |
| `rules` | Ordered `{"tag", "pattern"}` regular expressions |
| `word_pattern`, `words` | What a word looks like, and word lists per tag (e.g. `special`: `define`, `if`, ...) |
| `env_words` | `true` for Lisp: words the interpreter knows are `builtin`, names you defined are `variable` |

The buffer is read once from left to right, and at each point the first rule that matches wins, so a `;` inside a string stays part of the string and a `"` inside a comment stays part of the comment. Paren matching ignores brackets inside strings and comments. To add a language, copy a file, change `extensions`, `rules` and `words`, and restart the editor; a file that does not load is reported in the Listener.

### Search and replace

An inline bar that sits above the editor tabs and is shared by every buffer.

| Control | Meaning |
|---------|---------|
| `Aa` | Case sensitive |
| `W` | Whole word |
| `.*` | Regular expression |
| `▲` `▼` | Previous / next match |
| `Replace` | Replace the current match (only) |
| `All` | Replace every match in the buffer |
| `Enter` / `Shift+Enter` | Next / previous (same as `▼` / `▲`) |
| `Esc` / `✕` | Close the bar |

All matches are highlighted dim-yellow; the current match is highlighted gold and selected. The search text and options stay put when you switch buffers, and the highlights follow you to the new buffer. Replace uses a single delete + insert for a whole-buffer replace, so `Ctrl+Z` undoes the entire operation in one step. In regex mode the replacement string supports `\1`-style backreferences.

### How the editor drives the interpreter

Every evaluation goes through the *unmodified* interpreter:

```python
import lispy3 as L

ast = L.parse(code)
val = L.eval_exp(ast, L.global_env)
```

| Editor action | Call into `lispy3` |
|---|---|
| F5 / F6 / F9 / Listener ⏎ | `L.parse` → `L.eval_exp(ast, L.global_env)` |
| Inspector | `L.pretty_print(val, width=<Inspector columns>)` |
| Listener result line | `L.lisp_str(val)` |
| Symbol completion | reads `L.global_env.keys()` |
| `(save "x")` / `(load "x")` | the interpreter's `save_workspace` / `load_workspace` |
| Turtle drawings | `standard_env()` already wraps every `turtle.*` name |

Consequences:

- **One source of truth.** Change `lispy3.py` — add a builtin, alter `pretty_print`, tweak `standard_env` — and the editor picks it up on the next launch.
- **Same files run in both.** A `.lisp` file you run with `python lispy3.py tree.lisp` runs identically when opened in the editor and evaluated with F6.
- **No forking.** The editor never redefines parsing, evaluation, printing, or turtle. It only *drives* them.

If you ever want a frozen interpreter inside the editor, the change is a one-liner: copy `lispy3.py` to `lispy3_frozen.py` and change `import lispy3 as L` to `import lispy3_frozen as L`. Nothing else needs to change.

### Routing `display` output into the Listener

In the plain REPL, `(display …)` and `(pretty-print …)` call Python's `print`, which writes to the process' stdout — the terminal window. Under the editor, the same call would still leak to that terminal, because `display` is a native Python lambda that closes over `print`.

The fix is to redirect `sys.stdout` to the Listener for the duration of each evaluation:

```python
import io, contextlib

class _ListenerWriter(io.TextIOBase):
    def __init__(self, app):
        self.app = app
    def write(self, s):
        if s:
            self.app.listener_write(s, "result")
        return len(s)
    def writable(self):
        return True
    def flush(self):
        pass

def _run(self, code):
    writer = _ListenerWriter(self)
    try:
        with contextlib.redirect_stdout(writer):
            ast = L.parse(code)
            val = L.eval_exp(ast, L.global_env)
        return val, None
    except Exception as e:
        return None, e
```

This is deliberately done at the editor level, **not** by patching `lispy3.display`, because:

- The interpreter's `standard_env` is shared and changeable; wrapping just `display` would leave `pretty-print`, `pprint`, and any future native procedure that prints still leaking to the terminal.
- Redirecting `stdout` is scoped to `_run`, so Tk's own diagnostics and anything the editor prints outside evaluation are unaffected.
- It streams: each `write()` call lands in the Listener immediately, so `(display "Starting…")` followed by a long loop followed by `(display "Done.")` shows `Starting…` right away rather than buffering.

Example, all inside the Listener pane:

    USER> (display "hello" " " "world")
    hello world
    USER> (load "sieve_lispy3")
    USER> (run-sieve 1)
    Starting 10 iterations of the Sieve...Done. Primes found: 1899 TIME 0.03

### A short tour

1. `python lispy_machine.pyw`
2. In the Listener type `(load "lsystems")` ⏎
3. In the editor, put the cursor inside `(lsystem-from "F" "F[+F]F[-F]F" 4 3 23.5 0 -250 90)` and press **F5**.
4. Or open `tree.lisp`, put the cursor anywhere inside the final `(tree tree-generations tree-step)` and press **F5** — the turtle window opens and draws the tree.

Try `Ctrl+H`, search `define`, tick `Aa`, replace with `DEFINE` and press **All** — the whole buffer is redefined (in capitals) in one undoable step. Try `Ctrl+Space` at the end of `(l`, and pick `lambda` or `length` from the popup.

Everything the plain REPL can do, the editor can do — plus a place to keep your `.lisp` files open while you do it.
