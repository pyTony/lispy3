# Changelog

All notable changes to Lispy3 and the Lispy Machine editor.

## Unreleased

- Let Python mini_basic honour source dialect hints instead of forcing BBC
  dialect, so mini-only statements can run when the program requests mini.

- Fix editor Ctrl+S/Ctrl+W handling, track real text modifications and preserve
  saved state on navigation/shortcut release. Save As updates tab identities
  only after writing successfully and keeps duplicate basenames distinct.
  Closing edited tabs offers Save/Discard/Cancel and stays open on save failure.

- Keep BASIC settings in a persistent window with visible option state and
  saved feedback. Treat Python mini_basic console-hold exit code 10 as normal
  completion; retain nonzero error reporting for regular Python scripts.

- Replace backend selection with language-aware F5/F6: Lisp form/buffer,
  Lispy BASIC selection/line/buffer, or external Python selection/line/buffer.
  F7/F8 always use Python mini_basic. Retain BASIC Settings for locations/SDL,
  shared BASIC output choice, timing, Stop and source error highlights.

- Add a saved BASIC output selector independent of backend selection. F7/F8
  route either Lispy or Python BASIC output to the Listener or a real ANSI
  terminal while preserving timing, Stop and source error highlighting.

- Restrict automatic BASIC FN caches and Lisp define-memo to calls whose
  argument values are all exact numbers. Bypass floating-point and other
  arguments before cache lookup, including float keys equal to cached integers.
  Explicit memoize remains unrestricted; add memoize-exact for the gated policy.

- Add a saved Lispy/Python BASIC backend selector, configurable Python/project
  paths and optional SDL graphics. Use the existing Python CLI entry point and
  terminate its subprocess on Stop. Highlight located BASIC errors in source,
  accounting for selected text and BASIC line numbers; keep Lisp error marks
  separate from temporary bracket matching.

- Add BASIC syntax highlighting for .bas/.basic files, language-aware Return
  indentation and selection/buffer reindent for Lisp and common BASIC blocks.
  Add non-executing Lisp reader checks with source locations and cursor
  navigation. Reject malformed Lisp before formatting and group edits for undo.

- Add editor mini-basic commands: F7 runs selected BASIC text or the current
  line; F8 runs the whole BASIC buffer. Import the reader automatically and
  retain buffer timing and Stop. Move symbol inspection to Shift+F7.

- Add same-workspace ANSI terminal output through `with-ansi-terminal` and
  Lispy Machine's Eval menu. New output windows wait for Enter before closing.
  Add optional whole-buffer timing for Listener and terminal runs, and silent
  loader status with `(load "file" :silent)` and File → Load library silently.

- Add matching terminal Mandelbrot demos in BASIC and native Lisp, with four
  one-command plain/ANSI-colour launchers. Both use the same view, shading and
  bright-colour palette; coloured runs restore terminal attributes. Tests cover
  mathematical reference output, boundary points and all launchers. The turtle
  version remains available; its source comment now gives the correct run path.


- Add explicit libraries with private environments and macro tables, declared
  exports, composable only/prefix/rename imports and relative includes. Imported
  macros retain private helpers and caller argument scope; imported values are
  live read-only bindings. mini-basic supplies an opt-in library manifest while
  legacy load remains supported. Both evaluators enforce the same rules.
  Workspace save rejects imported bindings until serialization is implemented.


- mini-basic: add ANSI terminal macros and reader commands: CLS, COLOUR/COLOR,
  real TAB(x,y), a bounded BBC VDU text-control decoder, and separate raw ANSI
  bytes/strings. Terminal effects are not memoized in FN. The mini-basic guide
  documents supported controls, fixed colours and terminal/column limitations.


- Terminal REPL: enable GNU readline bracketed paste and evaluate every form in
  one submitted block instead of silently ignoring forms after the first.
  Read the whole block's syntax before execution; expand/evaluate forms in order
  so earlier definitions are available to later macro expansion. Typed
  continuation and libedit/Windows completion behavior are retained.


- mini-basic: make TIME an assignable elapsed clock in centiseconds, including
  LET, += and -=. Clock reads persist across runs and are not memoized in FN.
  The unchanged terminal Mandelbrot demo now reports elapsed time instead of
  zero. Eight clock regressions pass; full suite: 388 passed, 4 skipped,
  319 subtests passed.
- mini-basic: implement GOSUB / RETURN and ON ... GOSUB, including same-line
  continuation, nested calls, calls from loops, and isolated PROC/FN call scopes.
  Call state is restored on normal returns, errors and END. Out-of-range
  ON ... GOTO/GOSUB now raises "ON range" unless an ELSE branch is supplied,
  matching the new BBCSDL range probes. The four previously failing acceptance
  tests are green; full suite: 380 passed, 4 skipped, 319 subtests passed.
- mini-basic: accept numbered CASE clause headers, retaining their labels for
  DATA/RESTORE. Three regressions cover the BBCSDL reference case, nested clauses,
  and source-label preservation.
- mini-basic: capture all 14 jump/subroutine reference cases on BBCSDL 1.44a
  using the supplied tokenised fixture in isolated processes. Raw results and
  documented stack restrictions are in `compare/reference/`; successful
  exit-only cases are not treated as proof of compatible stack cleanup.
- mini-basic: fix GOTO label lookup within active structured bodies, including
  FOR, WHILE, IF / ELSE, REPEAT and CASE. Jumps preserve the surrounding
  continuation, and targets in enclosing active bodies remain reachable.
  Ten jump regression tests pass; the subsequent subroutine tests are now green
  as well. Progress is tracked in `TODO.md`.
- Help > About names the git branch the editor runs from (or says it is not
  a git checkout).
- Tab completion offers `defun`.
- `(make-num-vector [1 2 3])` makes a num vector from a vector or list, and
  `(help 'make-num-vector)` and the other `lispy3-numpy.py` extras have help.
- `lisp/mini-basic.lisp`: structured BBC BASIC statements as macros. `PRINT`,
  `LET`, multi-line `IF ... ELSE`, `FOR ... STEP`, `REPEAT ... UNTIL`, `WHILE`,
  `CASE ... WHEN ... OTHERWISE`, `DEF-PROC` / `DEF-FN` with `LOCAL`,
  `ENDPROC`, `FN=`, the `EXIT-` forms and `END` each expand into plain lispy3
  code inside `(bbc-program ...)`. PROC and FN parameters and LOCAL variables
  are dynamically scoped as in BBC BASIC.
- A BBC BASIC reader in `lisp/mini-basic.lisp`: `(bbc-run """...""")`,
  `(bbc-load "prog.bas")` and `(bbc-expand text)` turn BBC BASIC text, with
  UPPERCASE keywords, BBC operator precedence, string functions and line
  numbers, into the statement macros. GOTO, GOSUB, DATA and arrays come later.
- `(slurp "file")` reads a whole text file into a string.
- `(run-lispy text)`, `(run-sbcl text)`, `(run-clojure text)` in
  `lisp/mini-basic.lisp` run one BBC BASIC program with the mini-basic macros
  of lispy3, SBCL or Clojure: `(run-sbcl (slurp "prog.bas"))`.
- `(time exp)` runs `exp`, prints how long it took and gives its value.
- `(run-program "prog" args [input])` runs another program and prints its
  output; `lispy-home` is the folder `lispy3.py` is in.
- `(define-memo (f x) ...)` and `(memoize f)`: a function that remembers its
  results, like Python's `@functools.cache`. The BBC BASIC reader memoizes a
  pure `DEF FN` (one that reads only its own parameters and `LOCAL`s, prints
  nothing and calls no PROC or other FN), as mini_basic does.
- `compare/`: the same mini-basic macros in SBCL and Clojure, side by side,
  with shared test programs that print the same output in all three Lisps.
- The Lispy Machine runs Lisp code on its own thread, so the window stays
  live during a long run or an endless loop, and the new **■ Stop** button
  (also Eval > Stop and Ctrl+Break) ends it. Turtle commands still run on
  the window's thread.
- `(onscroll f)` calls `(f x y step)` when the mouse wheel turns over the turtle
  window, and `lisp/programs/mandelbrot.lisp` uses it to zoom into the Mandelbrot set
  around the pointer.
- Eval whole buffer (F6) in the Lispy Machine draws again after the turtle
  window was closed, instead of stopping with an empty `Error:`.
- Lispy Machine: right-click opens Cut / Copy / Paste / Select all in the editor,
  Listener, Inspector and Guide. Before, right-click did nothing.
- Fraction results are simplified everywhere: `(mod 3/2 1/2)` is `0`, not `0/1`,
  `remainder` and `quotient` stay exact on fractions, and `(exact 0.1)` is `1/10`.
- Complex numbers: literals such as `3+4i`, `-i` and `#C(3 4)`;
  arithmetic, equality, complex-aware mathematical functions, and
  rectangular/polar constructors, part accessors and predicates. Finite
  values print as infix `3.0+4.0i` while non-finite values use `#C(...)`.
  Bare `i` and `j` remain symbols. Regression checks are in
  `run_complex_checks.py`.
- `lispy3-numpy.py`: the interpreter with a faster evaluator, bulk vector
  built-ins (`make-num-vector`, `vector-fill!`, `vector-slice-set!`, `sum`)
  and, when NumPy is installed, NumPy arrays and maths. NumPy stays optional.
  A local variable or definition named `+`, `=`, `vector-ref` and so on is
  respected, and the extra built-ins are left out of `(save ...)`.
  NumPy's dot product is `(a-dot a b)`, so turtle's `(dot size colour)` still works.
- The Lispy Machine uses `lispy3-numpy.py` when NumPy is installed.
- `lisp/sieve-optimized.lisp`: the sieve with bulk vector operations. It now
  finds the same 1899 primes as `sieve_lispy3.lisp`.
- Fixes for Windows path escapes, universal times before 1970, and Help >
  Update outside a git checkout.
- `(defun f (x) body...)`, the Common Lisp spelling of `(define (f x) body...)`,
  and `t` as true, so `(cond ... (t default))` works.
- `(float x)`, the Common Lisp name for `(inexact x)`: `(float (/ 1 3))` gives
  0.3333333333333333.
- More Common Lisp: `&rest` and `&body` parameters, `(nth i lst)` order,
  `(format nil ...)` and `(format t ...)` with `~d`, `progn`, `setq`, `defvar`,
  `defparameter`, `defconstant`, `defmacro`, and names such as `mapcar`,
  `null`, `evenp`, `zerop`, `rem` and `string-upcase` for the built-ins.
- Each `dotimes` pass gets a fresh loop variable, as in Clojure, so closures
  made in the loop keep their own value.
- Scope tests in `tests/test_scope.py`, and every test has a one-line
  description that `python -m unittest -v` shows.
- Eval whole buffer (F6) in the Lispy Machine expands each form first, so
  `defun`, quasiquote and macros work there as they do in the REPL.

## Lispy Machine 1.0 (lispy3 interpreter 3.0)

Everything merged since the "Lispy3 Machine" release (tag `#editor`,
15 October 2026): pull requests #4 to #36.

### Changes that can affect existing programs

- Truth follows Scheme: only `#f` and `()` are false, so `0` now counts
  as true. (#27)
- `vector`, `make-vector` and `[..]` make real vectors, and `'(1 . 2)` and
  `(cons 1 2)` make real pairs instead of lists. (#27)
- `/` on whole numbers gives exact fractions: `(/ 7 2)` is `7/2`. (#27)
- `(sort strings <)` is an error instead of returning the list unsorted. (#27)
- Calling a Lisp procedure with the wrong number of arguments is an error. (#28)
- The example programs moved into a `lisp/` folder; `startup.lisp` stays in
  the top folder. (#35)

### Language

- The Gemini Argon interpreter: tail calls, `cond`, `and`/`or`, macros, `try`,
  variadic arithmetic and many list, string and map built-ins, with the
  features it dropped restored (script runner, categorised help, `read`, raw
  strings, vectors, `clock`). (#14)
- Strings with escapes and `"""raw"""` strings, `#t`/`#f`, `eval` and `read`. (#5)
- Whole-number functions `div`, `mod`, `divmod`, `remainder` and number tests. (#21)
- Scheme-style `let` and named `let`, `pair?`, `vector-length`,
  `vector->list`, `list->vector`, `numerator`, `denominator`, `exact?`,
  `inexact?`, `rational?`. (#27)
- `min` and `max` accept a single value. (#28)
- `string-append`. (#30)
- Time: `clock->string`, Common Lisp time functions and
  `universal-time->string`. (#24, #26)
- Long results are pretty-printed. (#23)

### Lispy Machine editor

- Syntax colours from `syntax/*.json`, `;` inside strings no longer starts a
  comment, auto-closed brackets are shown. (#7, #8)
- Find/replace, per-form F6 evaluation, Inspector improvements, and the
  Listener shows full function definitions. (direct commits)
- `.lisp` files named on the command line are opened. (#9)
- Its own λ window and taskbar icon, a desktop shortcut script, and a
  launcher and icon on Linux and WSLg too. (#12, #13, #16, #33, #34)
- A plain `lispy3>` REPL in the Listener, with Tab and Ctrl+Space completion
  and a visible cursor. (#17, #18, #19, #31)
- The Listener cursor stays at the prompt, one colour scheme everywhere, and
  "To buffer" copies Listener input into a buffer. (#20, #22)
- Inspector lists your own definitions. (#23)
- Help > Update pulls a new version with git and restarts the editor. (#22, #25)
- Help opens the Lispy guide in its own window; Help > About gives credits. (#32)
- Opens `startup.lisp` from the top folder at startup instead of the built-in
  welcome example. (#29, #35)
- View > Open terminal. (#36)

### Documentation and examples

- User manual: Quick Start, Lispy by Example, Quick Reference, and `(help)`. (#4, #5)
- `pi_digits.lisp` prints the first n decimals of pi. (#11)

### Tests

- Regression tests from Norvig's lispy.html, tests for every ticked TODO
  item and Lispy's own additions, Scheme comparison tests, and one shared
  turtle stub so the whole suite runs green. (#6, #10, #15, #27)

## Lispy3 Machine - 2026-10-15

Tag `#editor`: the first Lispy Machine IDE release.
