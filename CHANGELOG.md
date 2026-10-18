# Changelog

All notable changes to Lispy3 and the Lispy Machine editor.

## Lispy Machine 1.0 (lispy3 interpreter 3.0) - unreleased

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
