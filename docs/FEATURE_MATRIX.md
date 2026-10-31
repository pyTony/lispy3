# Feature matrix

What Lispy has today, at a glance: the Lisp language, the mini-basic BASIC
(BBC and MBASIC styles), and the Lispy Machine editor. Each row links to the
page that explains it.

**Last checked: 2026-10-31, `dev` after PR #133.**

✅ works · 🟡 partly, see the note · ❌ not yet

Keep this page current: every pull request that adds, removes or changes a
feature updates its row here in the same PR, and moves the "Last checked" line.
`tests/test_feature_matrix.py` fails when a new built-in topic, a new docs page
or a new MBASIC result is not reflected here. See
[AGENTS.md](../AGENTS.md#keep-the-feature-matrix-current).

## Lisp language

| Feature | Status | Notes |
|---|---|---|
| Numbers: big integers, exact fractions, floats | ✅ | `(/ 1 3)` is `1/3`; `rationalize`, `exact`, `float` |
| Complex numbers | ✅ | `3+4i`, `#C(3 4)`, `make-polar`; `(sqrt -4)` is `0.0+2.0i` ([README](../README.md#complex-numbers)) |
| Clojure data: `[]` vectors, `{}` maps, `:keywords` | ✅ | `assoc`, `dissoc`, `keys`, `contains?`; `(:name m)` looks up |
| Strings and characters | 🟡 | `#\a`, escapes, `"""raw"""`, `format`, `string->list`; no `char->integer`, `string=?`, `string-length` |
| `define`, `lambda`, `let`, named `let` | ✅ | several body forms without `begin` |
| `let*`, `letrec`, `flet`, `labels` | ❌ | nest `let` or use inner `define` |
| `defun`, `&optional`, `&key`, `&rest` | ✅ | CL-style definitions; `t` and `nil` |
| `defvar`, `defparameter`, `defconstant`, `setq`, `progn` | ✅ | |
| `cond`, `if`, `when`, `unless`, `and`, `or` | ✅ | 0 is true, `()` is false |
| `case`, `do`, `dolist` | ❌ | use `cond`, `dotimes`, `for-each` |
| `dotimes`, `while`, CL `loop` with `return` | 🟡 | `loop` keyword forms (`for`/`collect`...); plain `(loop forms)` is not supported |
| Proper tail calls | ✅ | `(count 100000)` runs without stack growth |
| Macros: `define-macro`, `defmacro`, quasiquote, `gensym` | ✅ | |
| `eval`, `read`, `apply`, `funcall`, `#'f` | ✅ | one namespace: `#'f` is `f` |
| Errors: `try` / `catch`, `error` | ✅ | no CL `handler-case`, `unwind-protect`, `catch`/`throw` |
| `call/cc`, multiple `values` | ❌ | |
| Hash tables, `setf` places | 🟡 | `gethash` and user setters ([hash tables](HASH_TABLES.md)); `(setf (car x) ...)` and `(setf (nth ...))` not yet |
| `incf`, `decf`, `1+`, `1-` | ✅ | |
| `push`, `pop` | ❌ | |
| List library | 🟡 | `map`, `mapcar`, `filter`, `reduce`, `sort`, `member`, `nth`, `range`; no `cadr`, `remove`, `find`, `every`/`some`, `subseq`, `list-ref` |
| Memoization: `define-memo` | ✅ | ([hash tables](HASH_TABLES.md)) |
| Promises and SICP lazy streams | ✅ | `delay`, `force`, `delay-force`, `cons-stream`, `stream-map`... (PR #127) |
| Text streams and files | ✅ | `with-open-file`, `read-line`, `write-line`, `with-output-to-string`, string streams |
| Unit tests: `deftest`, `check`, `run-tests` | ✅ | per workspace ([unit tests](UNIT_TESTS.md), PR #131) |
| Time: `clock`, `time`, CL universal time | ✅ | `get-universal-time`, `decode-universal-time` |
| Libraries: `define-library`, `import`, `load :silent` | ✅ | ([libraries](LIBRARIES.md)) |
| Workspaces: `new-workspace`, push/pop, `save`/`load` | ✅ | ([workspaces](WORKSPACES.md)) |
| Turtle graphics and L-systems | ✅ | `push-pose`/`pop-pose`, `onscroll` |
| Framebuffer graphics from Lisp | ✅ | ([BASIC graphics](BASIC_GRAPHICS.md#lisp-primitives)) |
| NumPy arrays (`lispy3-numpy.py`) | ✅ | `make-num-vector`, `dot`, `matmul` ([README](../README.md#faster-runs-with-lispy3-numpypy)) |
| PIL x86 engine | ✅ | `pil`, `pil-run`; needs a built PIL ([PIL](PIL.md), PR #129) |
| `define-record-type`, `defstruct` | ❌ | use maps |

### Built-ins by help topic

The `(help)` topics and how many names each has. When a PR adds a built-in,
the count here changes with it, and the PR updates the feature rows above.

| Help topic | Names |
|---|---|
| Special forms | 47 |
| Lists and sequences | 27 |
| Numbers and comparison | 33 |
| Strings and characters | 13 |
| Maps | 6 |
| Vectors, time and output | 40 |
| Lazy streams | 15 |
| Text streams | 17 |
| Turtle graphics | 6 |
| PIL x86 engine | 5 |

### Compared with real Lisps

Measured 2026-10-31 on `dev` with the comparison scripts kept in the project's
`lisp-comparison/` files (each form typed into Lispy the way the REPL does it,
and into the reference Lisp).

| Reference | Forms | Same | Different | Lispy error | Missing in Lispy | Error in both |
|---|---|---|---|---|---|---|
| Common Lisp (SBCL 2.2.9) | 185 | 100 | 23 | 6 | 56 | 0 |
| Scheme (GNU Guile 3.0.9) | 247 | 166 | 45 | 3 | 26 | 7 |

On 2026-10-18 the Common Lisp run was 50 the same and 118 missing. "Different"
includes deliberate choices, such as Clojure-order `(nth list i)` and `assoc`
working on maps rather than association lists.

## BASIC (mini-basic)

BBC BASIC is the default style; MBASIC style is chosen in **Eval → BASIC
Settings…** or with `(bbc-set-print-style! :mbasic)`. It is a limited
compatibility option, not a complete MBASIC dialect. Details in [mini-basic](MINI_BASIC.md).

| Feature | BBC | MBASIC | Notes |
|---|---|---|---|
| PRINT, `;` `,`, TAB, SPC, COUNT, POS, VPOS | ✅ | ✅ | MBASIC number spacing and singles in MBASIC style |
| PRINT USING / `@%` | ❌ | ❌ | |
| Variables `%` `%%` `&` `#` `$` `!` | ✅ | ✅ | `!` single precision (24 bits) |
| `=` `+=` `-=` `*=` `/=`, SWAP, CLEAR | ✅ | ✅ | PR #125 |
| `MID$(a$,p,n)=` assignment | ✅ | ✅ | PR #125 |
| String functions, `STRING$`, `EVAL`, string `<` `>` | ✅ | ✅ | PR #125 |
| `SPACE$`, `HEX$`, `OCT$`, `FIX`, `CINT`, `MKI$`/`CVI` | ❌ | ❌ | `STR$~` gives hex in BBC style |
| `DIV`, `MOD`, `EOR`, `&hex` | ✅ | 🟡 | MBASIC `\` integer division not yet |
| `XOR`, `EQV`, `IMP` | — | ❌ | |
| IF/THEN/ELSE, block IF, FOR/NEXT, REPEAT, WHILE/ENDWHILE, WHILE/WEND, CASE | ✅ | ✅ | `WEND` in MBASIC style |
| GOTO, GOSUB, ON GOTO/GOSUB, line numbers, `(label)` labels | ✅ | 🟡 | MBASIC: ON out of range should fall through |
| DEF PROC / DEF FN, LOCAL, multi-line FN | ✅ | 🟡 | MBASIC `DEF FN NAME(x)` with a space not yet |
| `RETURN` parameters, `LOCAL a()`, whole-array parameters, `ON x PROC` | ❌ | — | |
| DATA/READ/RESTORE, DIM arrays, whole-array arithmetic, SUM | ✅ | ✅ | |
| OPTION BASE, ERASE, DEFINT, RANDOMIZE, TRON/TROFF | — | ❌ | |
| ON ERROR, ON ERROR LOCAL/OFF, ERR, ERL, REPORT$, ERROR n | ✅ | 🟡 | MBASIC `RESUME` not yet; BBC ERROR EXT not yet |
| INPUT, INPUT LINE / LINE INPUT, GET, GET$, INKEY, INKEY$ | ✅ | ✅ | keys from the MODE window or typed lines |
| TIME, WAIT, END, STOP, QUIT | ✅ | ✅ | |
| RND | ✅ | 🟡 | MBASIC RND sequence differs |
| Text files: OPENIN/OPENOUT/BGET/BPUT, MBASIC OPEN | ✅ | 🟡 | CHAIN, MERGE, KILL, random files not yet |
| Memory: `DIM m n`, `?` `!` `$` indirection, structures | ❌ | — | |
| SOUND, INSTALL | ❌ | — | |
| VDU subset and raw ANSI | ✅ | — | ([terminal output](TERMINAL_OUTPUT.md)) |
| Graphics: MODE, GCOL, MOVE/DRAW/PLOT, CIRCLE, RECTANGLE, `*REFRESH` | ✅ | — | ([BASIC graphics](BASIC_GRAPHICS.md)) |
| Interactive BASIC REPL (`BASIC>`) | ✅ | ✅ | ([BASIC REPL](BASIC_REPL.md)) |

**MBASIC 5.21 golden programs: 10 pass, 2 spacing only, 27 fail (of 39).**
These numbers come from `EXPECTED` in `tests/test_mbasic_compat.py` and are
checked against it. See [MBASIC compatibility](MBASIC_COMPAT.md).

## Lispy Machine (editor)

| Feature | Status | Notes |
|---|---|---|
| Buffers for Lisp, BASIC and Python, syntax colouring | ✅ | colours from `syntax/*.json` |
| Listener: `USER>` entry line, plain Lisp REPL, BASIC REPL | ✅ | View → Listener mode |
| Inspector pane | ✅ | |
| Evaluate form / selection / buffer (F5, Ctrl+Enter) | ✅ | |
| Run program in a fresh workspace (F6, Shift+F6 to ANSI terminal) | ✅ | ([workspaces](WORKSPACES.md)) |
| Stop (Ctrl+Break) | ✅ | code runs in the background |
| Run tests in buffer (Ctrl+F6) | ✅ | Lisp `deftest` or Python `unittest` ([unit tests](UNIT_TESTS.md)) |
| Time buffer runs | ✅ | ([terminal output](TERMINAL_OUTPUT.md#time-the-whole-buffer)) |
| Search and replace, regex | ✅ | |
| Paren matching, auto-indent, completion (Ctrl+Space) | ✅ | |
| Python editor buffers | ✅ | |
| Run BASIC with Python mini_basic (F7/F8) | ✅ | needs a mini_basic clone |
| Run with real BBC BASIC for SDL | ✅ | ([BBCSDL](BBCSDL.md)) |
| PIL x86: run `.asm` buffers | ✅ | needs PIL and NASM ([PIL](PIL.md)) |
| Startup file, reopen last session | ✅ | View → Startup Settings |
| Settings saved in `~/.lispy3_machine.json` | ✅ | a hidden file on Windows now saves too (PRs #130, #132, #133) |
| Help window with this guide (F1) | ✅ | |
| Update from GitHub | ✅ | Help → Update |

## Documentation pages

| Page | About |
|---|---|
| [Quick start](QUICK_START.md) | first five minutes |
| [Lispy by example](LISPY_BY_EXAMPLE.md) | the language, one example at a time |
| [Quick reference](QUICK_REFERENCE.md) | every built-in |
| [Hash tables](HASH_TABLES.md) | hash tables, setters, memoization |
| [Libraries](LIBRARIES.md) | `define-library` and `import` |
| [Workspaces](WORKSPACES.md) | workspaces, Run versus Eval |
| [Unit tests](UNIT_TESTS.md) | Lisp and Python tests |
| [Text output](TEXT_OUTPUT.md) | where `display` goes |
| [Terminal output](TERMINAL_OUTPUT.md) | ANSI terminal, timing |
| [Terminal Mandelbrot](TERMINAL_MANDELBROT.md) | demo programs |
| [mini-basic](MINI_BASIC.md) | the BASIC language |
| [BASIC REPL](BASIC_REPL.md) | typing BASIC in the Listener |
| [BASIC graphics](BASIC_GRAPHICS.md) | MODE window graphics |
| [MBASIC compatibility](MBASIC_COMPAT.md) | golden program tests |
| [BBCSDL](BBCSDL.md) | running real BBC BASIC for SDL |
| [PIL](PIL.md) | the PIL x86 engine |
| [Repository layout](REPOSITORY_LAYOUT.md) | folders, branches, releases |
| [Agent coordination](AGENT_COORDINATION.md) | how assistants share work |
| [LLM guide](LLM.md) | notes for AI assistants |
