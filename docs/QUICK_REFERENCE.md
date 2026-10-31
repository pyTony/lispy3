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
| `#t` `#f` | true, false |
| `name` | variable |
| `:key` | keyword, stands for itself |
| `'(1 2 3)` | quoted list, items not evaluated |
| `[1 (+ 1 1)]` | vector, items evaluated: `[1 2]` |
| `7/2` | an exact fraction |
| `#b1010` `#xFF` `#o17` | whole numbers in base 2, 16 and 8, as in Scheme and Common Lisp |
| `'(1 . 2)` | a pair whose tail is not a list |
| `{:a 1 :b 2}` | map |
| `; text` | comment to the end of the line |

## Special forms

| Form | What it does |
|------|--------------|
| `(define name value)` | name a value or a function |
| `(define-memo (f a b) body...)` | like `define`, caching calls only when all arguments are exact numbers (integers/fractions) |
| `(set! name value)` | change an existing variable |
| `(setf x 1 y 2)` `(incf x)` `(incf x 5)` `(decf x)` | Common Lisp: set variables, add to or subtract from one; each gives the new value |
| `(time exp)` | run `exp`, print how long it took in seconds, give its value |
| `(lambda [a b] body)` | a function; one body expression |
| `#'f` `(funcall f a b)` | Common Lisp spellings: `#'f` is just `f` (one namespace), `funcall` calls it |
| `(defun f (a &optional (b 10) &rest more &key x (y 2)) ...)` | Common Lisp parameters: `&optional` may be left out (default, or `()`), `&rest` collects the rest, `&key` is passed as `:y 5`; `(b 10 b-given)` tells whether `b` was passed |
| `(if test then else)` | choose; else is required |
| `(when test body...)` `(unless test body...)` | run body when test is true (`unless`: false), else `()` |
| `(begin e1 e2 ...)` | run in order, return the last |
| `(let [a 1 b 2] body)` | local names for one body; Scheme's `(let ((a 1) (b 2)) body)` and named `(let loop ((i 0)) ...)` work too |
| `(while test body...)` | loop while test is true |
| `(loop for x in lst when (odd? x) collect x)` | Common Lisp `loop`: `for x in`/`on`/`across`, `for i from 1 to 10 by 2` (also `below` `downto` `above`), `for x = a then b`, `with`, `repeat`, `while`, `until`, `do`, `collect` `append` `sum` `count` `maximize` `minimize` (`into v`), `when`/`unless` ... `else` ... `end`, `always` `never` `thereis`, `initially`, `finally`; `(help 'loop)` |
| `(return x)` | leave the running `loop` at once with `x` |
| `(quote x)` / `'x` | `x` itself, unevaluated |
| `(:key map)` | look `:key` up in `map` |
| `(save "name")` | write definitions to `lisp/name.lisp`; imported bindings require keeping original source |
| `(load "name")` | run `name.lisp`; a bare name is looked for in the current folder, then (in the Machine) the current buffer's folder and the chosen programs folder, then `lisp/` and `lisp/programs/` |
| `(import (only library a b))` | select public exports; also prefix/rename; see [Libraries](LIBRARIES.md) |

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
| `(string-append "a" "b" ...)` | strings joined into one, `""` for none |
| `(str x)` | `x` as text (a symbol-like name, see [Atoms, symbols and strings](LISPY_BY_EXAMPLE.md#atoms-symbols-and-strings)) |
| `(string? x)` | true for a string |
| `(string->symbol "car")` / `(symbol->string 'car)` | name from text / text from name |

## Numbers and tests

| Function | Result |
|----------|--------|
| `(+ a b ...)` `(- a b ...)` `(* a b ...)` `(/ a b ...)` | arithmetic, any number of values (`plus` = `+`); `/` gives an exact fraction for whole numbers, `(/ 7 2)` is `7/2` |
| `(div a b)` `(mod a b)` `(divmod a b)` | whole-number division rounding down, what is left over, both as `(div mod)`; like Python's `//`, `%`, `divmod` |
| `(quotient a b)` `(remainder a b)` `(modulo a b)` | Scheme's: round toward zero, left over with the sign of `a`; `modulo` = `mod` |
| `(expt a b)` | power, exact for whole numbers |
| `(even? n)` `(odd? n)` `(zero? x)` `(positive? x)` `(negative? x)` `(integer? x)` | number tests |
| `(exact 3.0)` `(inexact 3)` | `3` and `3.0`; `(exact 0.1)` is `1/10` |
| `(exact x tol)` `(rationalize x tol)` | simplest fraction within `tol` of `x`: `(exact pi 1/100)` is `22/7`, `(rationalize 3/10 1/10)` is `1/3`; `rationalize` gives a decimal for a decimal, as in Scheme |
| `(number->string 255 16)` `(string->number "ff" 16)` | `"ff"` and `255`, any base from 2 to 36 |
| `(import bitwise)` | bit operations from `lisp/bitwise.sld`, Scheme (SRFI 151) names: `bitwise-and` `bitwise-ior` `bitwise-xor` `bitwise-not` `arithmetic-shift` `bit-count` `integer-length` `(bit-set? i n)` `(bit-field n start end)`; Common Lisp aliases `logand` `logior` `logxor` `lognot` `ash` `logcount` `logbitp`; fixed width: `(signed-field n 32)`, `(logical-shift-right n k 32)` |
| `(= a b ...)` | equal: numbers, strings, symbols, characters |
| `(< a b ...)` `(> a b ...)` `(<= a b ...)` `(>= a b ...)` | compare; true when each is in order with the next |
| `(not x)` | true when `x` is `#f` or `()` |
| `(1+ x)` `(1- x)` | `x` plus one, minus one |
| `(abs x)` `(round x)` | absolute value, nearest whole number (a half goes to the even one: `(round 2.5)` is `2`) |
| `(floor x)` `(ceil x)` `(trunc x)` | round down (like BASIC `INT`: `(floor -2.5)` is `-3`), round up, round toward zero (`(trunc -2.7)` is `-2`) |
| `(min a b ...)` `(max a b ...)` | smallest, largest |
| `(number? x)` `(symbol? x)` | type tests |
| `sqrt floor ceil fmod pow log exp sin cos tan gcd lcm isqrt factorial comb ...` | everything in Python's `math` |
| `pi` `e` `inf` | constants from `math` |

True is `#t`, false is `#f`. False in a test: `#f` and `()`. Everything else is true, including `0` and `""`. Tests return `#t`/`#f`; `define`, `set!`, `while` and `display` return nothing; a missing value is `()`. How this compares with Scheme, Common Lisp and Clojure: [True and false](LISPY_BY_EXAMPLE.md#true-and-false).

## Vectors, time and output

| Function | Result |
|----------|--------|
| `(make-vector n fill)` | `n` items of `fill` (default 0) |
| `(vector-ref v i)` | item `i`, counting from 0 |
| `(vector-set! v i x)` | store `x` at `i` |
| `(aref v i j ...)` | item of nested vectors, one index per level: `(aref m 1 0)` is row 1, column 0 |
| `(mat* a b)` | matrix product of nested vectors or lists; a flat `a` is a row, a flat `b` a column. `(mat* a b out)` writes the result into `out`, which may be `a` or `b` |
| `(vector 1 2)` `(vector? v)` `(vector-length v)` | make a vector, test for one, its length |
| `(vector->list v)` `(list->vector lst)` | convert between vectors and lists |
| `(clock)` | seconds since Lispy started, for timing |
| `(clock->string)` / `(clock->string t)` | date and time now, or of a `(clock)` value `t`, like `"2026-10-17 21:53:20"`; add a format such as `"%H:%M"` |
| `(get-universal-time)` | seconds since 1900-01-01 GMT, as in Common Lisp |
| `(universal-time->string [ut] [format])` | a universal time (default now) as local `"2026-10-17 22:03:00"`; format like `"%H:%M"` |
| `(get-decoded-time)` | now as `(second minute hour date month year day-of-week daylight-p zone)` |
| `(decode-universal-time ut [zone])` | `ut` as that list; day 0 is Monday, `zone` is hours west of Greenwich |
| `(encode-universal-time s m h date month year [zone])` | back to a universal time |
| `(get-internal-real-time)` / `(get-internal-run-time)` | timer / processor time in `internal-time-units-per-second` (1000) units |
| `(sleep seconds)` | wait |
| `(display a b ...)` | print values side by side, then a new line |
| `(pretty-print x)` / `(pprint x)` | print indented |
| `(help)` / `(help 'name)` | list built-ins / explain one |
| `(eval code)` | run code held as data: `(eval '(+ 1 2))` is `3` |
| `(read "text")` | turn text into code: `(eval (read "(+ 1 2)"))` is `3` |
| `(slurp "file.txt")` | the whole text file as one string; looks in `lisp/` if not found here |
| `(open-file "data.bin" "rb")` | open a binary file; modes `"rb"`, `"wb"`, `"w+b"`, `"r+b"`, `"ab"` |
| `(read-byte f [eof-value])` / `(write-byte n f)` | read or write one byte; `read-byte` gives `eof-value` (`#f`) at the end |
| `(file-position f [n])` / `(file-length f)` / `(close f)` | byte position (or move to `n`), length, close |
| `(with-open-file (s "notes.txt" :direction :output) body...)` | run `body` with `s` open on a text file, then close it, even after an error |
| `(open "notes.txt" [:direction :input/:output/:io] [:if-exists :supersede/:append/:error/nil] [:if-does-not-exist :error/:create/nil])` | a text file stream, as in Common Lisp; output replaces an existing file unless `:if-exists` says otherwise; `:element-type '(unsigned-byte 8)` opens it binary |
| `(read-line [s [eof-error-p [eof-value]]])` | the next line without its newline; `(read-line s nil :eof)` gives `:eof` at the end instead of an error; no stream reads the console |
| `(read-char [s ...])` / `(peek-char nil [s ...])` | the next character; `peek-char` leaves it to be read |
| `(write-line "text" [s])` / `(write-string "text" [s])` / `(write-char #\a [s])` | write text with a newline, text alone, one character |
| `(princ x [s])` / `(prin1 x [s])` / `(terpri [s])` | write `x` as `display` shows it, or as readable Lisp; end the line |
| `(format s "~a~%" x)` | formatted text to the stream `s`; `t` prints, `nil` gives a string |
| `(with-output-to-string (s) body...)` | everything `body` writes to `s`, as a string |
| `(with-input-from-string (s "one\ntwo") body...)` | run `body` reading from the string through `s` |
| `(make-string-output-stream)` / `(get-output-stream-string s)` | a stream to write to; take the text so far, leaving it empty |
| `(make-string-input-stream "text" [start [end]])` | a stream reading from the string |
| `*standard-output*` / `*standard-input*` | where printing goes and where `read-line` reads from |
| `(streamp x)` `(input-stream-p s)` `(output-stream-p s)` `(open-stream-p s)` | stream tests |
| `(finish-output [s])` / `(force-output [s])` | send buffered output on now |
| `(delay exp)` / `(force p)` | a promise worked out by the first `force` and kept; `force` gives anything else back as it is |
| `(delay-force exp)` / `(make-promise x)` / `(promise? x)` | `(delay (force exp))` that can chain without running out of stack; a promise already holding `x`; test for a promise |
| `(cons-stream a b)` | a lazy stream as in SICP: `b` is worked out only when `stream-cdr` asks for it |
| `(stream-car s)` / `(stream-cdr s)` | first item / the rest of a stream |
| `the-empty-stream` `(stream-null? s)` `(stream-pair? s)` | the empty stream, `()`, and tests |
| `(stream-ref s n)` / `(stream-head s n)` / `(stream-tail s n)` | item `n`; the first `n` items as a list; the stream after them |
| `(stream-map f s ...)` / `(stream-filter pred s)` | lazy streams of results / of the items `pred` is true for |
| `(stream-for-each f s)` / `(stream->list s [n])` | for a finite stream, or its first `n` items |
| `(stream 1 2 3)` / `(list->stream lst)` | a finite stream of the items |
| `(run-program "sbcl" (list "--version") [input])` | run another program, feeding it the input text; prints what it prints, gives its exit code |
| `lispy-home` | the folder `lispy3.py` is in |
| `(memoize f)` | `f` that remembers its results; a call with the same arguments gives the saved value |
| `(memoize-exact f)` | cache only all-exact numeric argument lists; bypass floats, booleans, strings, complex values and containers |

Only in `python lispy3-numpy.py` (NumPy optional):

| Form | Meaning |
|------|---------|
| `(make-num-vector n fill)` | like `make-vector`; a NumPy array when NumPy is installed. `(make-num-vector [1 2 3])` takes the items of a vector or list |
| `(vector-fill! v x [start] [stop])` | set a range of items to `x` |
| `(vector-slice-set! v start stop step x)` | set every `step`th item from `start` below `stop` to `x` |
| `(sum v)` | total of the items |
| `(array ...)` `(zeros n)` `(ones n)` `(arange n)` `(linspace a b n)` `(a+ a b)` `(dot a b)` `(mean a)` ... | NumPy arrays and maths, NumPy only |

## Turtle graphics

| Function | Result |
|----------|--------|
| `fd bk lt rt pu pd goto setheading circle color ...` | everything in Python's `turtle` |
| `(push-pose)` / `(pop-pose)` | remember / return to position and heading |
| `(clear-poses)` | forget remembered poses |
| `(onscroll f)` / `(onscroll #f)` | call `(f x y step)` on each mouse wheel turn, step 1 away from you, -1 towards; stop |
| `(reinit-turtle)` / `(reset)` | reopen a closed turtle window |

## PIL x86 engine

Needs a built [PIL](PIL.md) engine; see Eval > PIL x86 engine > PIL Settings.

| Function | Result |
|----------|--------|
| `(pil "demo hello")` | send one PIL debugger command; guest output is printed, the reply text returned |
| `(pil-run 1000)` | run up to 1000 instructions; the stop status, such as `halt` |
| `(pil-state)` | map of `eax` ... `edi`, `eip`, `flags`, `status`, `demo` |
| `(pil-start)` / `(pil-start "raw.bin")` / `(pil-stop)` | fresh engine, optionally with a raw image; end it |

## Unit tests

| Form | Meaning |
|---|---|
| `(deftest name body...)` | Define a test |
| `(check exp)` | Fail when exp is false or raises an error |
| `(check-equal expected exp)` | Fail unless `(equal? expected exp)` |
| `(check-error exp)` | Fail unless exp raises an error |
| `(run-tests [name...])` | Run tests, print a summary, give `#t` when all passed |

Ctrl+F6 (Eval → Run tests in buffer) runs a Lisp buffer's tests in a fresh
workspace, or a Python buffer with unittest. See [UNIT_TESTS.md](UNIT_TESTS.md).

## Limits to remember

- About 200 nested calls of recursion; use `map`, `filter` or `while` for more.
- `if` needs else; lambda has one body expression.

## TO BE IMPLEMENTED

Not in Lispy yet (details and workarounds in [Lispy by Example](LISPY_BY_EXAMPLE.md)):
`cond`, `and`, `or`, `apply`, `eq?`, `equal?`, `list?`, `procedure?`, `(define (f x) ...)`, several body expressions in `lambda`, tail-call optimisation, `reverse`, `nth`, `last`, `range`, `reduce`, `sort`, `member`, `for-each`, `dotimes`, `substring`, `string-ref`, `upcase`, `downcase`, `split`, `string->number`, `\r`/hex/Unicode string escapes, `format`, `str` returning a real string, `assoc`, `dissoc`, `keys`, `vals`, `contains?`, `try`/`error`, macros (`define-macro`, quasiquote).

Most of these have a reference implementation in [fluentpython/lispy](https://github.com/fluentpython/lispy), a set of `lis.py` variants close to Lispy; [Coming from Scheme or lis.py](LISPY_BY_EXAMPLE.md#coming-from-scheme-or-lispy) shows how to translate their examples.

## Workspace lifecycle

| Form | Effect |
|---|---|
| `(new-workspace [name])` | Fresh state; editor buffers and saved stack remain |
| `(workspace-push [name])` | Preserve exact state; enter fresh state |
| `(workspace-pop)` | Clean temporary resources; restore saved state |
| `(workspace-name)` / `(workspace-depth)` | Current label / saved count |
| `(workspace-on-discard cleanup)` | Register managed workspace cleanup |
| `(module-on-unload cleanup)` | Register cleanup inside module/library |
| `(unload "file.lisp")` / `(reload "file.lisp")` | Detach / replace an explicit imported file module |

F6/Shift+F6 run a fresh program; F5, Ctrl+Shift+Enter and Listener Eval reuse
current state. See [WORKSPACES.md](WORKSPACES.md) for effects and limitations.
