# Lispy by Example

Short, runnable examples, one idea at a time. Type them at the `lispy3>` prompt or in the Listener of the editor; the line after each prompt is what Lispy answers. Start with the [Quick Start](QUICK_START.md) if you have never used Lispy; look names up in the [Quick Reference](QUICK_REFERENCE.md), or type `(help)`.

Things Lispy cannot do yet are marked **TO BE IMPLEMENTED**, with the way to do it today. The same list is in [TODO.md](../TODO.md).

## Contents

- [Getting help inside Lispy](#getting-help-inside-lispy)
- [Numbers](#numbers)
- [Strings and characters](#strings-and-characters)
- [Variables](#variables)
- [Functions](#functions)
- [True and false](#true-and-false)
- [Choosing: if](#choosing-if)
- [Lists](#lists)
- [Head and tail recursion](#head-and-tail-recursion)
- [Iteration: map, filter and while](#iteration-map-filter-and-while)
- [Vectors you can change](#vectors-you-can-change)
- [Maps and keywords](#maps-and-keywords)
- [Local names: let](#local-names-let)
- [Printing](#printing)
- [Files and workspaces](#files-and-workspaces)
- [Turtle graphics](#turtle-graphics)
- [Gotchas](#gotchas)
- [Coming from Scheme or lis.py](#coming-from-scheme-or-lispy)
- [Further reading](#further-reading)

---

## Getting help inside Lispy

    lispy3> (help)
    Special forms (write them as code, quote the name to ask about one: (help 'if)):
      define set! lambda if begin let while quote save load
    Lists and sequences:
      car first cdr rest cons list length null? empty? append seq map filter get
    ...
    lispy3> (help 'cdr)
    (cdr lst) - everything but the first item; same as rest
    lispy3> (help 'sqrt)
    (sqrt ...) - from Python's math: Return the square root of x.

`(help name)` also works without the quote for functions. For special forms such as `if` and `while`, quote the name: `(help 'while)`. Asking about your own function shows its definition. In the editor, **Help → Built-in functions** prints the same list in the Listener.

## Numbers

    lispy3> (+ 2 3)
    5
    lispy3> (- 10 4)
    6
    lispy3> (* 6 7)
    42
    lispy3> (/ 7 2)
    3.5
    lispy3> (floor (/ 7 2))
    3
    lispy3> (fmod 7 3)
    1.0
    lispy3> (sqrt 16)
    4.0
    lispy3> pi
    3.141592653589793
    lispy3> (max 3 9 2)
    9

Every name in Python's `math` module works: `floor`, `ceil`, `sqrt`, `pow`, `log`, `sin`, `cos`, `fmod`, `pi`, `e` and so on.

`+ - * /` take exactly two numbers, so add three with `(+ (+ 1 2) 3)`. **TO BE IMPLEMENTED:** `(+ 1 2 3)` with any number of arguments.

**TO BE IMPLEMENTED:** `modulo` / `quotient` on whole numbers. Today use `(fmod a b)`, which gives a decimal such as `1.0`.

## Strings and characters

A string is text in double quotes. A character is written `#\a`; `#\space`, `#\newline` and `#\tab` are the special ones.

### Writing strings

| Write | You get |
|-------|---------|
| `"hello"` | `hello` |
| `"say \"hi\""` | `say "hi"` |
| `"back\\slash"` | `back\slash` |
| `"tab\there"` | `tab`, a tab, `here` |
| `"one\ntwo"` | `one` and `two` on two lines |
| `"""He said "hi"; ok"""` | `He said "hi"; ok` |

In `"..."` a backslash starts an escape: `\"` quote, `\\` backslash, `\n` new line, `\t` tab. Any other backslash stays as it is, so `"C:\Users"` is fine.

`"""..."""` is a raw string, as in Python: no escapes, and it may hold `"` freely. It ends at the next `"""`.

Both kinds may run over several lines, and the REPL keeps reading until the string is closed:

    lispy3> (display "first line
    ... (1)> second line")
    first line
    second line

A `;` or `'` inside a string is just text, and so are the characters `#\;`, `#\'` and `#\"`.

    lispy3> (length "don't; stop")
    11

When Lispy prints a string, or `save` writes one, it adds the escapes back, so the file reads in as the same text:

    lispy3> "say \"hi\""
    "say \"hi\""
    lispy3> (display "say \"hi\"")
    say "hi"

**TO BE IMPLEMENTED:** `\r`, hex and Unicode escapes such as `\x41;` or `\u00e4`, more character names (`#\return`, `#\nul`, `#\x41`), and string formatting (`format`, or `str` taking several values).

### Working with strings

    lispy3> (length "hello")
    5
    lispy3> (append "Hello, " "world")
    "Hello, world"
    lispy3> (seq "hi")
    (#\h #\i)
    lispy3> (car (seq "hello"))
    #\h

`seq` turns a string into a list of characters, and then every list tool works on it.

Count the `a`s in a word:

    lispy3> (define char-count (lambda [s ch] (length (filter (lambda [c] (= c ch)) (seq s)))))
    lispy3> (char-count "banana" #\a)
    3

Reverse a string:

    lispy3> (define reverse-string
    ...       (lambda [s]
    ...         (begin
    ...           (define out "")
    ...           (map (lambda [c] (set! out (append (str c) out))) (seq s))
    ...           out)))
    lispy3> (reverse-string "lispy")
    "ypsil"

Turn a number into text with `str`:

    lispy3> (append "n=" (str 12))
    "n=12"
    lispy3> (length (str 12345))
    5

**TO BE IMPLEMENTED:** `substring`, `string-ref`, `upcase`/`downcase`, `split`, `string->number`, `list->string` and a `string?` test. Today, work on the character list from `seq`. Character number `k` of a string, using `nth` from [Head and tail recursion](#head-and-tail-recursion):

    lispy3> (nth (seq "lispy") 1)
    #\i

## Variables

    lispy3> (define x 10)
    lispy3> x
    10
    lispy3> (set! x (+ x 1))
    lispy3> x
    11

`define` makes a new name, `set!` changes one that exists.

## Functions

    lispy3> (define square (lambda [x] (* x x)))
    lispy3> (square 12)
    144
    lispy3> (define hyp (lambda [a b] (sqrt (+ (square a) (square b)))))
    lispy3> (hyp 3 4)
    5.0

Parameters may be written `[x y]` or `(x y)`. Functions are values: you can pass them on and keep them in variables.

    lispy3> (define twice (lambda [f x] (f (f x))))
    lispy3> (twice square 3)
    81

The body is one expression; use `begin` for more:

    lispy3> (define shout (lambda [s] (begin (display s "!") (length s))))
    lispy3> (shout "hey")
    hey!
    3

**TO BE IMPLEMENTED:** the shorthand `(define (square x) (* x x))`, and a lambda body of several expressions without `begin`.

## True and false

Comparisons give `True` or `False`.

    lispy3> (< 1 2)
    True
    lispy3> (= "abc" "abc")
    True
    lispy3> (not (= 1 2))
    True

In a test, `False`, `0`, `0.0` and the empty list `()` count as false; everything else, **even the empty string `""`**, counts as true.

`True` and `False` are printed results, not names you can type: `(if x True False)` gives *Undefined symbol: True*. Write `(= 1 1)` for true and `(= 1 0)` for false if you need them as values.

**TO BE IMPLEMENTED:** `#t` / `#f` (or `true` / `false`) literals, and `and` / `or`. Today, use `if`: `(if a b a)` is "a and b", `(if a a b)` is "a or b".

## Choosing: if

    lispy3> (define grade (lambda [p] (if (>= p 90) "A" (if (>= p 75) "B" "C"))))
    lispy3> (grade 80)
    "B"

`if` needs the else part. For many choices, nest the `if`s as above.

**TO BE IMPLEMENTED:** `cond`, for a chain of tests without nesting.

## Lists

    lispy3> (define nums '(3 1 4 1 5))
    lispy3> (car nums)
    3
    lispy3> (cdr nums)
    (1 4 1 5)
    lispy3> (cons 9 nums)
    (9 3 1 4 1 5)
    lispy3> (length nums)
    5
    lispy3> (null? '())
    True
    lispy3> (append '(1 2) '(3))
    (1 2 3)
    lispy3> (list 1 "two" #\3 'four)
    (1 "two" #\3 four)

`'(...)` is a quoted list: its items are not evaluated. `[...]` is a vector; its items **are** evaluated, and it becomes a list:

    lispy3> [1 (+ 1 1) 3]
    (1 2 3)

`car`/`first` give the **head**, `cdr`/`rest` give the **tail**. The head of an empty list is `()`.

**TO BE IMPLEMENTED:** built-in `reverse`, `nth`, `last`, `range`, `reduce`/`fold`, `apply`, `sort` and `member`. Each is a few lines of recursion; see the next section.

## Head and tail recursion

The classic Lisp pattern: do something with the head, recurse on the tail, stop at the empty list.

Sum of a list:

    lispy3> (define sum-list
    ...       (lambda [lst]
    ...         (if (null? lst)
    ...             0
    ...             (+ (car lst) (sum-list (cdr lst))))))
    lispy3> (sum-list '(1 2 3 4))
    10

Length, written yourself:

    lispy3> (define my-length (lambda [lst] (if (null? lst) 0 (+ 1 (my-length (rest lst))))))
    lispy3> (my-length [10 20 30])
    3

Your own `map`:

    lispy3> (define my-map (lambda [f lst] (if (null? lst) '() (cons (f (car lst)) (my-map f (cdr lst))))))
    lispy3> (my-map (lambda [x] (* x 10)) '(1 2 3))
    (10 20 30)

Reverse with an accumulator (the result is built up in `acc`):

    lispy3> (define my-reverse (lambda [lst acc] (if (null? lst) acc (my-reverse (cdr lst) (cons (car lst) acc)))))
    lispy3> (my-reverse '(1 2 3) '())
    (3 2 1)

Item number `k`, and the last item:

    lispy3> (define nth (lambda [lst k] (if (= k 0) (car lst) (nth (cdr lst) (- k 1)))))
    lispy3> (nth '(a b c d) 2)
    c
    lispy3> (define last (lambda [lst] (if (null? (cdr lst)) (car lst) (last (cdr lst)))))
    lispy3> (last '(1 2 3))
    3

Numbers from `a` up to (not including) `b`:

    lispy3> (define range (lambda [a b] (if (>= a b) '() (cons a (range (+ a 1) b)))))
    lispy3> (range 0 5)
    (0 1 2 3 4)

Fold a list into one value:

    lispy3> (define reduce (lambda [f acc lst] (if (null? lst) acc (reduce f (f acc (car lst)) (cdr lst)))))
    lispy3> (reduce + 0 '(1 2 3 4 5))
    15

Lists inside lists:

    lispy3> (define flatten
    ...       (lambda [x]
    ...         (if (null? x) '()
    ...           (if (number? (car x))
    ...               (cons (car x) (flatten (cdr x)))
    ...               (append (flatten (car x)) (flatten (cdr x)))))))
    lispy3> (flatten '(1 (2 3) (4 (5))))
    (1 2 3 4 5)

Recursion on numbers works the same way:

    lispy3> (define fact (lambda [n] (if (< n 2) 1 (* n (fact (- n 1))))))
    lispy3> (fact 20)
    2432902008176640000

**How deep can it go?** About 200 nested calls. Past that Lispy stops with *"recursion too deep ... Use while, map or filter"*. Even a tail call such as `my-reverse` counts, because Lispy does not reuse the call. **TO BE IMPLEMENTED:** tail-call optimisation, so that tail recursion can run any number of times. Until then, use `map`, `filter` or `while` for long lists and big counts.

## Iteration: map, filter and while

`map` and `filter` walk a list without recursion, so they work on lists of any length:

    lispy3> (map (lambda [x] (* x x)) (range 1 6))
    (1 4 9 16 25)
    lispy3> (filter (lambda [x] (= (fmod x 2) 0)) (range 1 11))
    (2 4 6 8 10)
    lispy3> (map (lambda [c] (= c #\space)) (seq "a b"))
    (False True False)

`while` repeats its body while the test is true:

    lispy3> (define i 1)
    lispy3> (while (<= i 3) (display "i = " i) (set! i (+ i 1)))
    i = 1
    i = 2
    i = 3

Sum 1 to 100:

    lispy3> (define total 0)
    lispy3> (define n 1)
    lispy3> (while (<= n 100) (set! total (+ total n)) (set! n (+ n 1)))
    lispy3> total
    5050

Collect results into a list:

    lispy3> (define k 0)
    lispy3> (define squares '())
    lispy3> (while (< k 5) (set! squares (cons (* k k) squares)) (set! k (+ k 1)))
    lispy3> squares
    (16 9 4 1 0)

Fibonacci, loop style, with local variables:

    lispy3> (define fib-loop
    ...       (lambda [n]
    ...         (let [a 0 b 1 i 0]
    ...           (begin
    ...             (while (< i n)
    ...               (define t b)
    ...               (set! b (+ a b))
    ...               (set! a t)
    ...               (set! i (+ i 1)))
    ...             a))))
    lispy3> (fib-loop 50)
    12586269025

**TO BE IMPLEMENTED:** `for-each`, `dotimes` and a counting `for` loop. Today use `map` (and ignore its result) or `while`.

## Vectors you can change

    lispy3> (define v (make-vector 3 0))
    lispy3> (vector-set! v 0 42)
    lispy3> v
    (42 0 0)
    lispy3> (vector-ref v 0)
    42

Items are numbered from 0. `sieve_lispy3.lisp` uses these for the prime sieve.

## Maps and keywords

    lispy3> (define book {:title "SICP" :year 1985})
    lispy3> (:year book)
    1985
    lispy3> (get book :title)
    "SICP"
    lispy3> (get book :nope)
    ()

A keyword starts with `:` and stands for itself. Calling a keyword like a function looks it up in a map.

**TO BE IMPLEMENTED:** `assoc` / `dissoc` to add or remove keys, `keys`, `vals`, and `contains?`. Today, build a new map literal.

## Local names: let

    lispy3> (let [a 2 b 3] (* a b))
    6

The names live only inside the one body expression; use `begin` inside `let` for more.

## Printing

    lispy3> (display "total: " 5050)
    total: 5050
    lispy3> (display '(1 2 3))
    (1 2 3)
    lispy3> (pretty-print book)
    {:title "SICP" :year 1985}

`display` puts its values next to each other with nothing between them and ends the line.

## Files and workspaces

    lispy3> (save "mine")
    Workspace saved to mine.lisp
    lispy3> (load "mine")
    Workspace loaded from mine.lisp. Defined: ...
    lispy3> (load "lsystems")

`save` writes all your definitions as Lisp code; `load` runs any `.lisp` file. From the command line: `python lispy3.py prog.lisp`, or `python lispy3.py -i prog.lisp` to stay at the prompt afterwards.

## Turtle graphics

Every name in Python's `turtle` module is a Lispy function:

    lispy3> (define square-shape
    ...       (lambda [size]
    ...         (begin (fd size) (rt 90) (fd size) (rt 90) (fd size) (rt 90) (fd size) (rt 90))))
    lispy3> (square-shape 100)

`(help 'fd)` explains any turtle name. For drawing plants and snowflakes see the L-system section of the [README](../README.md#l-systems-with-turtle-graphics). If you close the window, type `(reinit-turtle)`.

## Gotchas

- `+ - * /` take exactly two arguments.
- `if` needs an else part, and a lambda body is one expression (use `begin`).
- `""` counts as true in a test; `0` and `()` count as false.
- `(str 12)` makes text that prints like a string, but `(= (str 12) "12")` is `False`. Compare numbers as numbers instead. **TO BE IMPLEMENTED:** `str` should return a real string.
- Recursion stops after about 200 nested calls; use `map`, `filter` or `while` for big jobs.
- **TO BE IMPLEMENTED:** catching errors inside a program (`try` / `error`).

## Coming from Scheme or lis.py

Lispy grew out of Peter Norvig's [`lis.py`](https://norvig.com/lispy.html), like the interpreters in Luciano Ramalho's [fluentpython/lispy](https://github.com/fluentpython/lispy). Scheme examples from there, from *SICP* or from *The Little Schemer* mostly run after a few changes:

| Scheme / lis.py | Lispy today |
|-----------------|-------------|
| `(define (square x) (* x x))` | `(define square (lambda [x] (* x x)))` |
| `(lambda (x) e1 e2)` | `(lambda [x] (begin e1 e2))` |
| `(cond (a x) (b y) (else z))` | `(if a x (if b y z))` |
| `(and a b)` / `(or a b)` | `(if a b a)` / `(if a a b)` |
| `#t` / `#f` | `(= 1 1)` / `(= 1 0)` (they print as `True` / `False`) |
| `(+ a b c)` | `(+ (+ a b) c)` |
| `(modulo a b)`, `(quotient a b)` | `(fmod a b)`, `(floor (/ a b))` |
| `(equal? a b)` | `(= a b)` |
| `(apply f lst)` | **TO BE IMPLEMENTED** |
| deep tail recursion | `while`, `map`, `filter` (no tail-call optimisation yet) |

For example, `fact-iter.scm` from fluentpython/lispy (`mylis/mylis_2/examples`) becomes:

    lispy3> (define factorial-iter
    ...       (lambda [n product]
    ...         (if (= n 1) product (factorial-iter (- n 1) (* n product)))))
    lispy3> (factorial-iter 10 1)
    3628800

and `member.scm`, which needs `cond`, becomes nested `if`s:

    lispy3> (define member
    ...       (lambda [item lst]
    ...         (if (null? lst) '()
    ...           (if (= item (car lst)) lst
    ...             (member item (cdr lst))))))
    lispy3> (member 7 '(5 7 11))
    (7 11)

Lispy adds what lis.py does not have: strings and characters, `[vectors]`, `{maps}` with `:keywords`, `while`, `let`, `save`/`load`, turtle graphics and the editor.

## Further reading

- Norvig, [(How to Write a (Lisp) Interpreter (in Python))](https://norvig.com/lispy.html) and [the sequel](https://norvig.com/lispy2.html): where Lispy comes from.
- [fluentpython/lispy](https://github.com/fluentpython/lispy): `lis.py` with type hints and pattern matching (`original/py3.10`), `cond`/`and`/`or` and tail calls (`mylis/mylis_2`), example programs, tests, and a reading list (SICP, The Little Schemer, How to Design Programs, ...). Most of Lispy's [TODO list](../TODO.md) points there for a reference implementation.
- Abelson and Sussman, [Structure and Interpretation of Computer Programs](https://mitpress.mit.edu/sites/default/files/sicp/index.html): the classic for head and tail recursion.
