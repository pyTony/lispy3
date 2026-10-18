# Lispy Quick Start

Five minutes from nothing to your own functions. For more, read [Lispy by Example](LISPY_BY_EXAMPLE.md); to look something up, use the [Quick Reference](QUICK_REFERENCE.md).

## 1. Start it

    python lispy3.py              the REPL (type, press Enter, see the answer)
    python lispy_machine.pyw      the editor, with a Listener at the bottom
    python lispy3.py prog.lisp    run a program file

Type `(help)` at the prompt to list every built-in, and `(help 'name)` to explain one:

    lispy3> (help 'length)
    (length x) - number of items in a list or characters in a string

## 2. Everything is (function arguments...)

    lispy3> (+ 1 2)
    3
    lispy3> (* (+ 1 2) 4)
    12
    lispy3> (length "hello")
    5

`+ - * /` take exactly **two** numbers: write `(+ (+ 1 2) 3)`, not `(+ 1 2 3)`.

## 3. Name things with define

    lispy3> (define greeting "Hello")
    lispy3> (append greeting ", world")
    "Hello, world"

## 4. Make functions with lambda

    lispy3> (define square (lambda [x] (* x x)))
    lispy3> (square 9)
    81

A function body is **one** expression. Put several in `(begin ...)`.

## 5. Decide with if

    lispy3> (define sign (lambda [n] (if (< n 0) "negative" "not negative")))
    lispy3> (sign -5)
    "negative"

`if` always needs both the *then* and the *else* part.

## 6. Lists: head and tail

    lispy3> (define nums '(3 1 4 1 5))
    lispy3> (car nums)
    3
    lispy3> (cdr nums)
    (1 4 1 5)
    lispy3> (cons 9 nums)
    (9 3 1 4 1 5)

`car` = `first` (the head), `cdr` = `rest` (the tail). Write a list as `'(1 2 3)` or `[1 2 3]`.

## 7. Repeat: recursion, map or while

    lispy3> (define sum (lambda [lst] (if (null? lst) 0 (+ (car lst) (sum (cdr lst))))))
    lispy3> (sum nums)
    14
    lispy3> (map square nums)
    (9 1 16 1 25)
    lispy3> (define i 1)
    lispy3> (while (<= i 3) (display "i = " i) (set! i (+ i 1)))
    i = 1
    i = 2
    i = 3

Recursion is fine for a couple of hundred steps; for longer lists use `map`, `filter` or `while`.

## 8. Keep your work

    lispy3> (save "mine")
    Workspace saved to .../lisp/mine.lisp
    lispy3> (load "mine")

Next: [Lispy by Example](LISPY_BY_EXAMPLE.md).
