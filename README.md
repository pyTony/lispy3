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
- [Complex numbers](#complex-numbers)
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
- **Complex Numbers**: `3+4i`, `-i`, `2.5j` and `#C(3 4)` are complex literals. Arithmetic, transcendental functions, polar/rectangular construction, parts and conjugation are supported. Finite values print as `3.0+4.0i`; non-finite components use `#C(real imag)`.
- **Workspace State Management**: Built-in environment persistence via `(save "filename")` and `(load "filename")`, which serialize/deserialize user functions and variables as valid, human-readable Lisp source code.
- **Turtle Graphics**: Every `turtle.*` name is available as a Lisp procedure; `push-pose` / `pop-pose` / `clear-poses` implement the `[` … `]` branching of L-systems, and `(onscroll f)` calls `(f x y step)` when the mouse wheel turns over the window.

**Editor (`lispy_machine.pyw`)**

- **Multiple editor buffers** with syntax colouring read from `syntax/*.json` (Lisp and Python included).
- **Persistent Listener** with history, coloured prompts/results/errors.
- **Inspector pane** showing the pretty-printed last value.
- **Evaluate form at cursor** or the whole buffer without restarting the interpreter.
- **Stop button**: code runs in the background, so the window stays live during an endless loop, and **■ Stop** (`Ctrl+Break`) ends it.
- **Search & replace** with case / whole-word / regex options, next/previous, replace-all.
- **Paren matching**, auto-indent, and **symbol completion** (`Ctrl+Space`).
- **`display` routed into the Listener** — no more stray terminal output.

---

## Files in this project

| File | Role |
|------|------|
| `lispy_libraries.py` | Explicit libraries and selective imports; see the [library guide](docs/LIBRARIES.md). |
| `lispy3.py` | The interpreter (REPL + `python lispy3.py file.lisp` script runner). |
| `lispy3-numpy.py` | The same interpreter with a faster evaluator and bulk vector built-ins; uses NumPy arrays when NumPy is installed. See [Faster runs](#faster-runs-with-lispy3-numpypy). |
| `lisp/` | The folder for Lisp programs: the examples below live here, `(save "name")` writes here, and `(load "name")` and the editor's Open / Save as look here. |
| `lisp/lsystems.lisp` | The L-system drawing engine used by every example. |
| `lisp/programs/tree.lisp`, `lisp/programs/plant.lisp`, `lisp/programs/snowflake.lisp` | The three example L-systems from *The Algorithmic Beauty of Plants*. |
| `lisp/sieve_lispy3.lisp` | The Byte magazine prime sieve, rewritten for lispy3. |
| `lisp/sieve-optimized.lisp` | The same sieve with bulk vector operations; run it with `lispy3-numpy.py`. |
| `lisp/mini-basic.lisp` | BBC BASIC text via `(bbc-run """...""")` or `(bbc-load "prog.bas")`: structured statements, PROC/FN, GOTO, GOSUB/RETURN, ON branches, DATA/READ/RESTORE, DIM arrays and an assignable centisecond TIME clock. See the [mini-basic guide](docs/MINI_BASIC.md) for usage, ANSI output and limits, and `basic/reference/README.md` for native checks. |
| `lisp/programs/pi_digits.lisp` | Prints the first n decimals of pi with a spigot algorithm. |
| `lisp/programs/mandelbrot.lisp` | The Mandelbrot set; turn the mouse wheel over it to zoom in and out around the pointer. |
| Terminal Mandelbrot in BASIC and Lisp | Plain and ANSI-coloured terminal demos; see [run commands and source](docs/TERMINAL_MANDELBROT.md). |
| `lisp/my_workspace.lisp` | Example of a saved workspace (produced by `(save "my_workspace")`). |
| `lispy_machine.pyw` | The Lisp-Machine style editor. |
| `startup.lisp` | Optional startup buffer/script beside the editor; configure showing and execution independently in View → Startup Settings…, which can also reopen the files open at the last close instead. |
| `syntax_highlight.py`, `syntax/*.json` | Editor syntax colouring: the engine, and one rules-and-colours file per language. |
| `docs/QUICK_START.md`, `docs/LISPY_BY_EXAMPLE.md`, `docs/QUICK_REFERENCE.md` | The user manual. |
| `TODO.md` | Features still to be implemented. |
| `tests/` | Regression tests, starting with Norvig's [lispy.html](https://norvig.com/lispy.html). Run `python -m unittest` in this folder; no window opens. `python -m unittest -v` lists each test with a line saying what it checks. |

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

    lispy3> (define z 3+4i)
    lispy3> (magnitude z)
    5.0

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

A program file is ordinary Lisp code that runs from top to bottom, like a Python script. A `;` starts a comment. `(load "other")` runs another file first; the `.lisp` ending is optional. A file name without a folder is looked for in the current folder first and then in `lisp/` and `lisp/programs/` (in the Lispy Machine also the current buffer's folder and the chosen Lisp programs folder, before `lisp/`), so `python lispy3.py tree.lisp` and `(load "lsystems")` work from anywhere. `(save "name")` writes `lisp/name.lisp` unless you give a path. If the program drew with turtle graphics, the window stays open until you close it (not when you use `-i`, where you get the prompt instead).

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

### Faster runs with lispy3-numpy.py

`python lispy3-numpy.py prog.lisp` takes the same options as `lispy3.py` and runs the same programs, only faster: it adds a quicker evaluator for loops, arithmetic, comparisons and `vector-ref` / `vector-set!`. NumPy is optional. Without it everything below still works on ordinary vectors, except the array built-ins at the end.

| Form | What it does |
|------|--------------|
| `(make-num-vector n fill)` | like `make-vector`, but a NumPy array of whole numbers when NumPy is installed; it prints as `#a(1 1 1)`. `(make-num-vector [1 2 3])` makes one from the items of a vector or list |
| `(vector-fill! v x [start] [stop])` | put `x` into items `start` up to (not including) `stop`; the whole vector if left out |
| `(vector-slice-set! v start stop step x)` | put `x` into items `start`, `start+step`, ... below `stop` |
| `(sum v)` | add up all items |
| `(array 1 2 3)` `(zeros n)` `(ones n)` `(arange n)` `(linspace a b n)` | make NumPy arrays (NumPy only) |
| `(a+ a b)` `(a- a b)` `(a* a b)` `(a/ a b)` | item-by-item arithmetic on arrays or an array and a number (NumPy only) |
| `(a-dot a b)` `(matmul a b)` `(mean a)` `(std a)` `(reshape a 2 3)` `(shape a)` | linear algebra and statistics (NumPy only) |
| `(array? x)` `(array->list a)` `(list->array lst)` | test for an array and convert (NumPy only) |

The speed comes from doing a whole vector in one built-in call instead of a Lisp loop, not from NumPy itself: reading or setting one item of a NumPy array is slower than of an ordinary vector. Ten rounds of the sieve take about 2.7 s with `python lispy3.py sieve_lispy3.lisp`, about 1.2 s with `python lispy3-numpy.py sieve_lispy3.lisp`, and about 0.004 s with `python lispy3-numpy.py sieve-optimized.lisp`, with or without NumPy. All three find 1899 primes.

The Lispy Machine editor uses `lispy3-numpy.py` by itself when NumPy is installed; `python lispy_machine.pyw --version` and Help > About then name the NumPy version.

---

## Complex numbers

Complex literals accept the suffix `i` or `j`, for example `3+4i`, `1-2i`,
`4i`, `-i` and `2.5j`. The Common Lisp notation `#C(3 4)` is also accepted.
Bare `i` and `j` remain ordinary symbols so they can be used as variable names.

Finite complex numbers print in infix notation: `3+4i` prints as
`3.0+4.0i`. The reader also accepts that printed form. When a component is
non-finite (`inf` or `nan`), printing uses `#C(real imag)` instead.

| Form | Meaning |
|------|---------|
| `(complex re im)`, `(make-rectangular re im)` | Create a complex number from its two parts |
| `(make-polar mag ang)` | Create one from a magnitude and angle (radians) |
| `(real-part z)`, `(imag-part z)` | Extract real and imaginary parts |
| `(magnitude z)`, `(angle z)` | Magnitude and phase angle |
| `(conjugate z)` | Complex conjugate |
| `(complex? z)`, `(real? z)` | Numeric type predicates |
| `(sqrt -1)`, `(log -1)` | Return complex results for negative inputs |

Arithmetic (`+`, `-`, `*`, `/`, `expt`) and numerical equality (`=`, `eq?`,
`equal?`) support complex numbers. Ordering comparisons (`<`, `>`, `<=`, `>=`)
do not define an ordering for complex values and raise an error.

Example:

    lispy3> (define z 3+4i)
    lispy3> (magnitude z)
    5.0
    lispy3> (* z (conjugate z))
    25.0+0.0i
    lispy3> (sqrt -4)
    0.0+2.0i

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
| `F5` / `Ctrl+Enter` | Run Lisp form, or BASIC/Python selection/current line |
| `F6` | Run the whole program in a fresh workspace, output to Listener |
| `Ctrl+Shift+Enter` | Eval the buffer in the current workspace |
| `Shift+F6` | Run the whole program in a fresh workspace, output to ANSI terminal |
| `F4` / `Ctrl+click` | Open the quoted filename at the cursor (Command+click on macOS) |
| `F7` | Run selected BASIC text or the current BASIC line through Python mini_basic |
| `F8` | Run the whole BASIC buffer through Python mini_basic |
| `Shift+F7` | Inspect the symbol at the cursor (or the name typed in the Listener) |

| `F9` | Evaluate what you typed in the Listener |
| `Ctrl+Break` | Stop the code that is running (also the Listener's **■ Stop** button, **Eval → Stop**, and `Esc` in the plain REPL) |
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

For `.bas`/`.basic` files, the editor provides case-insensitive BASIC keyword,
string, number and REM-comment colouring. **Edit → Reindent selection or buffer**
indents common BASIC blocks or Lisp forms in two-space steps. Selection reindent
operates on complete lines using the surrounding buffer's nesting.

Open and Save As offer a combined supported-source filter, individual Lisp,
BBC BASIC and Python filters, and All files. Filters follow the installed
`syntax/*.json` definitions and include uppercase extensions such as `.BAS`.

**Edit → Check Lisp syntax** checks brackets, strings and reader syntax without
executing code or expanding macros. Errors report the filename, line and column
and move the cursor to the location. Lisp reindent checks first and leaves an
invalid buffer unchanged. Formatting preserves strings/comments and is grouped
as one undo operation. These are reader checks, not checks for undefined names
or runtime errors. BASIC indentation is a layout helper, not a BASIC validator.

**F5/F6 follow the buffer's highlighting language.** Lisp runs in the workspace;
BASIC uses Lispy mini-basic in that workspace; Python runs in a fresh process.
F5 runs an enclosing Lisp form, or selected BASIC/Python text (the current line
when nothing is selected). F6 runs the whole buffer in a fresh workspace. F5 and Ctrl+Shift+Enter keep the current workspace. Python selections are
unindented for execution; traceback line numbers still refer to the buffer.
Python definitions do not persist between runs. Use the configured Python
executable under **Eval → BASIC Settings…** for both external Python runners.

BASIC Settings opens a window that stays open while you change options.
Check states remain visible; changes save automatically and show
“Saved. Applies to the next run.” Python mini_basic console exit status 10
means normal completion with a console-hold request, rather than an error.

**F7/F8 explicitly run Python mini_basic**, independently of F5/F6. There is
no saved backend selector. **BASIC Settings** retains Python executable/project
locations and the optional SDL window. **F6 → Listener** and **Shift+F6 → ANSI terminal** run the buffer and save the destination for F5/F7/F8 and Listener evaluations. There is no separate output selector in BASIC Settings.

**Eval → Real BBC BASIC for SDL buffer** uses the actual BBCSDL executable in its own window. Configure it and the native text loader in BASIC Settings; see [one-time setup](docs/BBCSDL.md).
For terminal-only programs turn SDL graphics off: enabling it mirrors PRINT
through the SDL window and terminal, which can have very different performance.
New ANSI output windows wait for Enter before closing. Select the directory
containing `mini_basic/__main__.py` and optionally a Python executable with the
package installed. A sibling `mini_basic` checkout is detected automatically.
The adapter uses the same `python -m mini_basic` entry point as
`mini_basic/tools/editor.py`, honouring source dialect hints such as
`REM dialect: mini` or `REM dialect: bbc` instead of forcing a dialect. It runs unsaved source,
streams output to the selected destination, and Stop terminates its process. Enable
**Python SDL graphics (hold window)** for graphical programs; close that window
when finished. Python buffer timing includes subprocess startup and window hold.
Terminal INPUT is not connected to the Listener; use the standalone terminal
runner for programs needing console input.

BASIC errors with a reported line highlight the corresponding source line,
including selection offsets and ordinary numbered/unnumbered Python programs.
Errors without a reliable location still appear in the Listener. Complex Python
source preambles/continuations may lack a reliable mapping. Highlights remain
visible while navigating and clear after editing or a new Lisp check. These
commands do not replace the standalone BASIC editor's tokenized-file support,
interpreter pretty-printer or renumbering commands.

### Buffers and the Listener

**View → Startup Settings…** has independent saved options to show the
`startup.lisp` buffer and to run it once at launch. Defaults preserve the old
behaviour: show it when no files are supplied, without executing it. Disable
showing to start with an empty buffer; files explicitly supplied on the command
line still open normally. Enabling execution runs the saved `startup.lisp`
beside the editor after the GUI is ready, even when hidden or other files are
open. Definitions stay in the workspace, output/errors appear in the Listener,
and Stop is available. Running executes all forms, including graphics in the
sample startup file. Settings stay visible while changing them, save
automatically and apply on the next launch; the current startup file is not
changed. The editor's Restart also respects the hidden-startup option.

**Reopen the files that were open when the Machine was last closed** is a
third option in the same window, off by default. When the Machine quits it
remembers the open files in tab order and the current buffer (in
`~/.lispy3_machine.json`); with the option on, the next launch without file
arguments opens those files again instead of `startup.lisp`, and selects the
buffer that was current. Files that no longer exist are skipped quietly, and
unsaved untitled buffers are not remembered. If none of the files remain,
the show-startup option decides as before. Files named on the command line
still take precedence, and running `startup.lisp` stays independent.

Ctrl+S saves the current editor buffer to its associated path, shown in the
status bar after a successful save. Save As updates that path and the tab's
identity together after writing succeeds. Ctrl+W offers Save/Discard/Cancel for
modified text; cancellation or save failure leaves the buffer open. Dirty
markers track actual edits, including paste/undo, rather than cursor movement.

The Listener is a real REPL backed by the interpreter's `global_env`. Code in the Listener and the Inspector (what you type, echoed forms and results) is coloured with the same Lisp colours as the editor; `display` output stays green and errors red. It supports `↑` / `↓` history, coloured prompts (`USER>`), coloured results, and coloured errors. Typing `exit` closes the editor.

Interactive Lisp input evaluates every top-level form on a line. An extra top-level `)` produces a warning with its line and column, then valid forms still execute. The GUI Lisp REPL highlights extra `)` in red while typing. Parentheses inside strings and comments are ignored. Malformed forms (such as an `if` missing its then-expression) remain errors; file loading and buffer syntax checking retain their stricter reader diagnostics.

**Plain lispy3 REPL.** Choose **View → Listener mode → Lisp REPL** (or start the editor with `python lispy_machine.pyw --repl`) and the Listener becomes a console like `python lispy3.py`, still sharing the editor's `global_env`: the `USER>` entry line goes away and you type at a `lispy3>` prompt in the Listener itself, so your input and the output scroll together. Enter on an unfinished form continues it on the next line under a `... (1)>` prompt, pasted lines are read one by one, `Tab` completes like readline (the shared start, then the list of choices) and `Ctrl+Space` opens the same pick list as elsewhere, `↑` / `↓` bring back earlier lines, `Esc` drops an unfinished form, and results are printed as the REPL prints them (nothing for a `define`, and a result too long for one line, such as a whole function, indented like in the Inspector). The text above the prompt is read-only: `←` stops at the prompt, and a click in older output puts the cursor back at the prompt (drag to select and copy). The choice is remembered in `~/.lispy3_machine.json`; choose **Lisp Listener (USER>)** to get the entry-line Listener back.

In Lisp buffers, F5 finds the *outermost enclosing form* at the cursor — skipping strings, `;` comments, and characters such as `#\(` — and evaluates just that. This lets you re-evaluate a single `define` without rerunning the whole file or restarting the interpreter.

**Running and stopping.** Code runs on its own thread, so the editor stays live while it works: you can scroll, edit, read the guide, and watch `display` output arrive. While it runs the status bar says *Running...* and the **■ Stop** button at the top right of the Listener turns red; press it (or `Ctrl+Break`, or **Eval → Stop**) to end an endless loop or a long `(sleep ...)`. The Listener prints `;; Stopped.` and everything defined so far stays defined. `(try ...)` does not catch a Stop. One evaluation runs at a time: F5, F6 or F9 during a run says *Still running* and does nothing. Turtle commands are still carried out by the window's own thread, as Tk requires, so drawings work as before.

In Lisp buffers, F6 evaluates the buffer forms in order. That is precisely what `python lispy3.py file.lisp` does under the hood, so the results are identical.

Lispy closes brackets you leave open. When it does, you see the brackets it added: in the Listener they are printed at the end of your line, and with F5 or F6 they are written into the buffer at the end of the last line of code (before any `;` comment), with a `;; added ))` note in the Listener. `Ctrl+Z` takes them out again.

### Inspector

After every evaluation the Inspector pane shows the value using the interpreter's own `pretty_print`. Clojure-style maps and vectors expand vertically; procedures print as `(lambda …)` or as their native name. Long lists of atoms are packed into rows instead of one item per line. A `(define name …)` returns nothing, so the Inspector then shows the new value of `name`; press `Shift+F7` on any symbol to look at a variable later. If evaluation raised, the Inspector shows the error.

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

Open **Edit → Find…** (`Ctrl+F`) or **Edit → Replace…** (`Ctrl+H`). The inline bar sits above the editor tabs and is shared by every buffer.

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

The default destination is the Listener. **Eval → Run program → ANSI terminal (Shift+F6)**
and `(with-ansi-terminal body...)` select a real terminal instead. Enable
**Eval → Time buffer runs** for timing with either destination. See
[terminal output and timing](docs/TERMINAL_OUTPUT.md).

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

**File → Open…** starts in `lisp/programs`. Choose **View → Lisp programs directory…** to save another starting directory. If that directory is unavailable, browsing falls back to `lisp/programs`. **Save as…** keeps an existing buffer's source directory.

**Edit → Open file at cursor** and **F4** use the focused editor, Listener input, or REPL line. The Listener context menu also offers this command. The caret may be inside the filename or immediately after its closing quote. File navigation accepts pasted Windows paths with single backslashes; it does not evaluate the input.

Quoted filenames can be opened with **F4**, **Ctrl+click** (Command+click on macOS),
or the editor context menu. Relative paths resolve from the source directory,
then the working/editor/library directories. Already-open buffers retain their edits.

Tokenised **`.bbc` / `.BBC` input** is decoded by Python mini_basic when opened,
including from the command line. It becomes an unsaved BASIC `.bas` buffer;
Ctrl+S uses Save As, preserving the original binary. Configure the Python
mini_basic location in BASIC Settings. See [BBC input details](docs/BBCSDL.md).

### Workspaces and file modules

**F6 / Shift+F6 run fresh; F5, Ctrl+Shift+Enter and Listener Eval retain state.**
Results remain available after a run, and editor buffers survive Workspace →
New / Push / Pop. Use `(workspace-push)` / `(workspace-pop)` to preserve and
restore variables, closures, macros, module instances and memo caches in memory.
`(new-workspace)` starts clean.

Explicit `(import (prefix "file.lisp" file:))` keeps file definitions in a private
module. `(reload "file.lisp")` refreshes its recorded imports; `(unload "file.lisp")`
removes them. Legacy `load` still uses the shared workspace. Registered cleanup
releases managed resources; external side effects are not undone. See the
[workspace and module guide](docs/WORKSPACES.md) for scope, Python import analogies,
cleanup limits, and comparison with Racket, Clojure and Common Lisp.

Help → Update also checks local Python/runtime-library changes since startup,
even if Git reports no new commits or pull fails, and offers a restart. It
refreshes open text-file buffers changed on disk; unsaved edits require confirmation
before replacement. Refreshing a buffer does not execute or reload its definitions.

BASIC examples, timing programs and BBCSDL reference checks are collected in
[basic/](basic/README.md). Lisp implementation files remain in lisp/; cross-Lisp
implementations and Lisp-form fixtures remain in compare/.

**BASIC REPL:** choose **View → Listener mode → BASIC REPL** for direct BASIC
input and numbered program editing. `HELP` lists commands. `LOAD`/`SAVE` filenames
and Lisp loader paths complete with Tab. See [BASIC REPL](docs/BASIC_REPL.md).

Pytest defaults to this repository's `tests/` directory (`python -m pytest -q`).
A local `mini_basic` link points to a separate project and is excluded from
recursive discovery; run that project's tests from its own repository.

Lispy Machine schedules cyclic garbage collection on its Tk main thread. This
keeps closed turtle-window/image cycles from being finalized by the Lisp worker.
Cycles are collected periodically while the GUI runs and at exit; normal reference
counting is unchanged, and the prior automatic-GC setting is restored on exit.
