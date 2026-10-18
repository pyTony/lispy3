# Changelog

All notable changes to Lispy3 and the Lispy Machine editor.

## Unreleased

- Help > About names the git branch the editor runs from (or says it is not
  a git checkout).
- `lispy3-numpy.py`: the interpreter with a faster evaluator, bulk vector
  built-ins (`make-num-vector`, `vector-fill!`, `vector-slice-set!`, `sum`)
  and, when NumPy is installed, NumPy arrays and maths. NumPy stays optional.
  A local variable or definition named `+`, `=`, `vector-ref` and so on is
  respected, and the extra built-ins are left out of `(save ...)`.
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
