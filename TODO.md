# TODO

Most of the language items below came in with the Gemini Argon version (October 2026). The manual (docs/) still describes several of them as TO BE IMPLEMENTED and needs updating.

Features the manual marks **TO BE IMPLEMENTED** (see [docs/LISPY_BY_EXAMPLE.md](docs/LISPY_BY_EXAMPLE.md) for today's workarounds). When one is done, add it to `HELP_TOPICS` in `lispy3.py` and to [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md), and remove its TO BE IMPLEMENTED notes.

Many of these already exist, as small pattern-matching Python 3.10 code close to ours, in Luciano Ramalho's [fluentpython/lispy](https://github.com/fluentpython/lispy) (variations of Norvig's `lis.py`, the same ancestor as Lispy). Items marked *(ref: ...)* point to the file to read:

- `original/py3.10/lis.py`: Norvig's `lis.py` with type hints and `match`/`case`
- `mylis/mylis_2/lis.py`: adds `set!`, `cond`, `and`, `or` and proper tail calls
- `mylis/mylis_3/environ.py`: variadic `+` and comparisons, `modulo`, `quotient`

## Language

- [x] `cond` for a chain of tests *(ref: mylis_2 `cond_form`)*
- [x] `and` / `or`, short-circuit, so they must be special forms *(ref: mylis_2 `and_form`, `or_form`)*
- [x] Macros: `define-macro`, quasiquote `` ` `` with `,` and `,@`, `gensym` (`eval` exists) *(ref: Norvig `original/norvig/lispy.py`, `expand` and `expand_quasiquote`)*
- [x] `(define (f x) body)` shorthand *(ref: py3.10 `lis.py`, `case ['define', [Symbol(name), *parms], *body]`)*
- [x] Several body expressions in `lambda` and `let` without `begin` *(ref: py3.10 `lis.py`, `case ['lambda', [*parms], *body]`)*
- [x] Proper tail calls, so tail recursion is not limited to about 200 calls *(ref: mylis_2 `evaluate`, the `while True` loop with `TCO_ENABLED`)*
- [x] `try` / `error` to raise and catch errors inside a program

## Numbers

- [x] `+ - * /` with any number of arguments, e.g. `(+ 1 2 3)` *(ref: mylis_3 `environ.py`)*
- [x] `<`, `=`, ... comparing more than two values, e.g. `(< 1 2 3)` *(ref: mylis_3 `variadic_comparison`)*
- [x] `modulo` and `quotient` on whole numbers (today only `fmod`, which gives a decimal) *(ref: mylis_3 `environ.py`)*

## Lists

- [x] `reverse`, `nth`, `last`, `range`
- [x] `reduce` / `fold`, `apply`, `sort`, `member` *(ref: `apply` in py3.10 `lis.py`; `member` in `mylis/mylis_2/examples/member.scm`)*
- [x] `append` with any number of lists *(ref: py3.10 `lis.py`)*
- [x] `list?`, `procedure?`, `eq?`, `equal?` tests *(ref: py3.10 `lis.py`)*
- [x] `for-each` and a counting loop (`dotimes` or `for`)

## Strings

- [x] `substring`, `string-ref`, `upcase`, `downcase`, `split`, `list->string`
- [x] `string->number`
- [x] `str` should return a real string, so `(= (str 12) "12")` is true
- [x] More string escapes: `\r`, hex and Unicode (`\x41;`, `\u00e4`)
- [x] More character names: `#\return`, `#\nul`, `#\x41`
- [x] String formatting: `format`, or `str` taking several values

## Maps

- [x] `assoc`, `dissoc`, `keys`, `vals`, `contains?`

## Tests

- [x] Regression tests from Norvig's lispy.html and his `lis_tests` (`tests/test_norvig.py`, run `python -m unittest`)
- [x] `equal?`, `eq?`, `expt`, `apply`, `list?`, `procedure?`, `print` and many-list `map` are in; their Norvig tests are now normal tests (`NorvigStandardEnvTest`)
- [x] Tests for the Gemini Argon additions and the features restored after it (`tests/test_gemini_features.py`)
- [ ] Tests for Lispy's own additions (strings, maps, vectors, `while`, save/load, the example programs). Ref: fluentpython/lispy `original/py3.10/lis_test.py`
