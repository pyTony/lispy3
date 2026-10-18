# mini-basic in three Lisps

The structured BBC BASIC statements of [`lisp/mini-basic.lisp`](../lisp/mini-basic.lisp),
written as macros in lispy3, SBCL (Common Lisp) and Clojure, side by side. All
three read the same programs in [`programs/`](programs) and print the same
output, which is kept in the `.out` file next to each program.

| | lispy3 | SBCL | Clojure |
|---|---|---|---|
| File | [`lisp/mini-basic.lisp`](../lisp/mini-basic.lisp) | [`sbcl/mini-basic.lisp`](sbcl/mini-basic.lisp) | [`clojure/mini_basic.clj`](clojure/mini_basic.clj) |
| Lines of code (no comments) | 224 | 203 | 234 |
| Macro definition | `define-macro` | `defmacro` | `defmacro` |
| Fresh names | `gensym` | `gensym` | `gensym`, and `x#` in syntax-quote |
| BBC variable | global, `set!` | special variable (`defparameter`), `setf` | `^:dynamic` var, `set!` inside one `binding` for the whole program |
| PROC/FN parameters and `LOCAL` (dynamic scope) | saved on entry, put back on exit by hand | `let` of the special variables | nested `binding` |
| `FOR`, `REPEAT`, `WHILE` | `while` with the body inside the test | `loop` in a `block` | `loop` / `recur` |
| `ENDPROC`, `FN=` part-way, `EXIT-FOR` and so on | `error` / `try`, only where used | `block` / `return-from`, free | `ex-info` / `try`, only where used |
| `FN=` as the last statement | a plain value | `return-from` (costs nothing) | a plain value |
| `END` | `error` / `try` | `catch` / `throw` | `ex-info` / `try` |
| Clashes with the host Lisp | statements are UPPERCASE symbols, lispy3 is case-sensitive | the reader upcases, so `PRINT`, `IF`, `LET`, `CASE` are shadowed in package `mini-basic` | statements are UPPERCASE symbols, Clojure is case-sensitive |
| Program namespace | the global environment (a BBC variable named `list` would hide lispy3's `list`) | package `bbc-user`: only `+ - * / < > <= >= = /= mod not` from CL | namespace `bbc-user`: only `+ - * / < > <= >= = == not= not mod` from clojure.core |

What the comparison shows:

- **Common Lisp has BASIC's control flow built in.** Special variables give BBC's
  dynamic scope, and `block` / `return-from` give every early exit at no cost.
  The SBCL version is the shortest and needs no tail-position tricks.
- **lispy3 and Clojure have no non-local exit except exceptions.** So their macros
  look through the body (`bbc-uses?` / `uses?`) and add a `try` only where an
  early exit appears. They also turn a final `FN=` into a plain value
  (`bbc-tail` / `tail`), even at the end of `IF` and `CASE` branches.
- **Clojure's vars need a binding before `set!` works.** So `bbc-program` binds
  every variable once around the whole run.
- **lispy3 is the only one without packages or namespaces.** So its text reader
  renames a BBC variable that clashes with a lispy3 name: `list` becomes `v-list`.

## BBC BASIC text

[`basic/`](basic) holds BBC BASIC programs as text, read by the reader in
`lisp/mini-basic.lisp` (lispy3 only for now) with `(bbc-load "compare/basic/structure.bas")`.
`(pretty-print (bbc-expand (slurp "compare/basic/fact.bas")))` shows the macro
forms a program becomes. Their `.out` files were checked against
`python -m mini_basic` (each file starts with `REM dialect: bbc`, so mini_basic picks its bbc dialect on its own). `structure.bas` matches exactly, and its output was also checked on real BBC BASIC. Three things
differ in mini_basic and follow BBC BASIC here:

- `DEF FNfact(n) IF n<2 THEN =1 ELSE =n*FNfact(n-1)`: mini_basic reports a DEF FN header error.
- `PRINT INSTR(c$,"World"), INSTR(c$,"x")`: mini_basic does not right-justify the numbers when a string literal appears inside a function's brackets.
- `PRINT ;1;2;3`: mini_basic still pads to the 10-column field; BBC BASIC prints `123`.

## Speed against mini_basic

[`bench/`](bench) holds two programs for a first timing of lispy3's reader
against `python -m mini_basic`. Wall-clock seconds on one machine, startup
(about 0.1 s for both) included:

| Program | mini_basic | lispy3 mini-basic |
|---|---|---|
| [`primes.bas`](bench/primes.bas): primes below 5000 by trial division | 5.1 | 2.7 |
| the same, below 20000 | 32.0 | 15.8 |
| [`fib.bas`](bench/fib.bas): recursive `FNfib(22)` | 0.12 | 0.12 |

Both remember the results of a pure `DEF FN`, so `FNfib` runs once for each
`n`; without the cache lispy3 takes 2.5 s. The classic sieve
(mini_basic's `examples/SIEVE.bbc`) needs `DIM`, `GOTO` and `TIME`, which the
reader does not have yet.

```sh
python3 -c "import lispy3; lispy3.load_workspace('mini-basic'); lispy3.eval_exp(lispy3.parse('(bbc-load \"compare/bench/primes.bas\")'), lispy3.global_env)"
cd ../mini_basic && python -m mini_basic -q ../lispy3/compare/bench/primes.bas
```

## Running

```sh
python3 lispy3.py            # then (load "mini-basic") and (load "compare/programs/fact.lisp")
sbcl --script compare/sbcl/run.lisp compare/programs/fact.lisp
clojure -M compare/clojure/run.clj compare/programs/fact.lisp
# or, with the jars: java -cp "clojure.jar:spec.alpha.jar:core.specs.alpha.jar" clojure.main compare/clojure/run.clj ...
```

`python -m unittest tests.test_compare` checks every program against its `.out`
file in lispy3. It does the same in SBCL when `sbcl` is installed, and in
Clojure when `clojure` is installed or `CLOJURE_CP` holds the jars' class path.
