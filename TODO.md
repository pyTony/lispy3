# TODO

Features the manual marks **TO BE IMPLEMENTED** (see [docs/LISPY_BY_EXAMPLE.md](docs/LISPY_BY_EXAMPLE.md) for today's workarounds). When one is done, add it to `HELP_TOPICS` in `lispy3.py` and to [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md), and remove its TO BE IMPLEMENTED notes.

## Language

- [ ] `cond` for a chain of tests
- [ ] `and` / `or` (short-circuit, so they must be special forms)
- [ ] `#t` / `#f` (or `true` / `false`) literals
- [ ] `(define (f x) body)` shorthand
- [ ] Several body expressions in `lambda` and `let` without `begin`
- [ ] Tail-call optimisation, so tail recursion is not limited to about 200 calls
- [ ] `try` / `error` to raise and catch errors inside a program

## Numbers

- [ ] `+ - * /` with any number of arguments, e.g. `(+ 1 2 3)`
- [ ] `mod` / `remainder` on whole numbers (today only `fmod`, which gives a decimal)

## Lists

- [ ] `reverse`, `nth`, `last`, `range`
- [ ] `reduce` / `fold`, `apply`, `sort`, `member`
- [ ] `for-each` and a counting loop (`dotimes` or `for`)

## Strings

- [ ] `substring`, `string-ref`, `upcase`, `downcase`, `split`, `list->string`
- [ ] `string->number` and a `string?` test
- [ ] `str` should return a real string, so `(= (str 12) "12")` is true

## Maps

- [ ] `assoc`, `dissoc`, `keys`, `vals`, `contains?`
