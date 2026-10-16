# Lispy Quick Reference

Every built-in on one page. Inside Lispy, `(help)` prints this list and `(help 'name)` explains one entry. Examples: [Lispy by Example](LISPY_BY_EXAMPLE.md). First steps: [Quick Start](QUICK_START.md).

## Syntax

| Write | Meaning |
|-------|---------|
| `(f a b)` | call `f` with `a` and `b` |
| `42` `3.14` | numbers |
| `"text"` | string; escapes `\"` `\\` `\n` `\t`; may span lines |
| `"""text"""` | raw string: no escapes, may hold `"` |
| `#\a` `#\space` `#\newline` `#\tab` | characters |
| `name` | variable |
| `:key` | keyword, stands for itself |
| `'(1 2 3)` | quoted list, items not evaluated |
| `[1 (+ 1 1)]` | vector, items evaluated, becomes the list `(1 2)` |
| `{:a 1 :b 2}` | map |
| `; text` | comment to the end of the line |

## Special forms

| Form | What it does |
|------|--------------|
| `(define name value)` | name a value or a function |
| `(set! name value)` | change an existing variable |
| `(lambda [a b] body)` | a function; one body expression |
| `(if test then else)` | choose; else is required |
| `(begin e1 e2 ...)` | run in order, return the last |
| `(let [a 1 b 2] body)` | local names for one body |
| `(while test body...)` | loop while test is true |
| `(quote x)` / `'x` | `x` itself, unevaluated |
| `(:key map)` | look `:key` up in `map` |
| `(save "name")` | write your definitions to `name.lisp` |
| `(load "name")` | run `name.lisp` |

## Lists and strings

| Function | Result |
|----------|--------|
| `(car lst)` / `(first lst)` | head: first item, `()` if empty |
| `(cdr lst)` / `(rest lst)` | tail: all but the first item |
| `(cons x lst)` | `lst` with `x` in front |
| `(list a b ...)` | a new list |
| `(length x)` | items in a list, characters in a string |
| `(null? lst)` / `(empty? lst)` | true for `()` |
| `(append a b)` | join two lists or two strings |
| `(seq "abc")` | `(#\a #\b #\c)` |
| `(map f lst)` | `(f item)` for every item |
| `(filter f lst)` | items where `(f item)` is true |
| `(get map key)` | value for `key`, `()` if missing |
| `(str x)` | `x` as text |

## Numbers and tests

| Function | Result |
|----------|--------|
| `(+ a b)` `(- a b)` `(* a b)` `(/ a b)` | arithmetic, exactly two numbers (`plus` = `+`) |
| `(= a b)` | equal: numbers, strings, symbols, characters |
| `(< a b)` `(> a b)` `(<= a b)` `(>= a b)` | compare |
| `(not x)` | true when `x` is false, `0` or `()` |
| `(abs x)` `(round x)` | absolute value, nearest whole number |
| `(min a b ...)` `(max a b ...)` | smallest, largest |
| `(number? x)` `(symbol? x)` | type tests |
| `sqrt floor ceil fmod pow log exp sin cos tan ...` | everything in Python's `math` |
| `pi` `e` `inf` | constants from `math` |

False in a test: `False`, `0`, `0.0`, `()`. Everything else is true, including `""`. Tests return `True`/`False`; `define`, `set!`, `while` and `display` return nothing; a missing value is `()`. How this compares with Scheme, Common Lisp and Clojure: [True and false](LISPY_BY_EXAMPLE.md#true-and-false).

## Vectors, time and output

| Function | Result |
|----------|--------|
| `(make-vector n fill)` | `n` items of `fill` (default 0) |
| `(vector-ref v i)` | item `i`, counting from 0 |
| `(vector-set! v i x)` | store `x` at `i` |
| `(clock)` | seconds, for timing |
| `(display a b ...)` | print values side by side, then a new line |
| `(pretty-print x)` / `(pprint x)` | print indented |
| `(help)` / `(help 'name)` | list built-ins / explain one |

## Turtle graphics

| Function | Result |
|----------|--------|
| `fd bk lt rt pu pd goto setheading circle color ...` | everything in Python's `turtle` |
| `(push-pose)` / `(pop-pose)` | remember / return to position and heading |
| `(clear-poses)` | forget remembered poses |
| `(reinit-turtle)` / `(reset)` | reopen a closed turtle window |

## Limits to remember

- About 200 nested calls of recursion; use `map`, `filter` or `while` for more.
- `+ - * /` take two arguments; `if` needs else; lambda has one body expression.

## TO BE IMPLEMENTED

Not in Lispy yet (details and workarounds in [Lispy by Example](LISPY_BY_EXAMPLE.md), the list in [TODO.md](../TODO.md)):
`cond`, `and`, `or`, `#t`/`#f`, `(+ 1 2 3)` and `(< 1 2 3)` with many arguments, `modulo`, `quotient`, `apply`, `eq?`, `equal?`, `list?`, `procedure?`, `(define (f x) ...)`, several body expressions in `lambda`, tail-call optimisation, `reverse`, `nth`, `last`, `range`, `reduce`, `sort`, `member`, `for-each`, `dotimes`, `substring`, `string-ref`, `upcase`, `downcase`, `split`, `string->number`, `string?`, `\r`/hex/Unicode string escapes, `format`, `str` returning a real string, `assoc`, `dissoc`, `keys`, `vals`, `contains?`, `try`/`error`, macros (`define-macro`, quasiquote, `eval`).

Most of these have a reference implementation in [fluentpython/lispy](https://github.com/fluentpython/lispy), a set of `lis.py` variants close to Lispy; [Coming from Scheme or lis.py](LISPY_BY_EXAMPLE.md#coming-from-scheme-or-lispy) shows how to translate their examples.
