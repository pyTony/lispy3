\# Lispy-Modern: A Modern Clojure-Infused Lisp Interpreter in Python 3



A fully typed, robust, and elegant Lisp/Scheme interpreter written in modern Python 3. This project is a deeply evolutionized version of Peter Norvig's classic `lis.py`, incorporating modern Python features and powerful Clojure-inspired constructs.



The roots of this project date back to a spark of inspiration from a 1981 Finnish computer magazine (\*Prosessori\*), leading to a Python 2 adaptation on the DaniWeb forums in 2011, and finally culminating in this modern, pattern-matching Python 3 masterpiece.



\## Key Features



\- \*\*Structural Pattern Matching\*\*: Powered entirely by Python 3's `match-case` syntax for clean, compiler-like abstract syntax tree (AST) evaluation.

\- \*\*Smart Auto-Closing Brackets\*\*: Forgives unclosed parentheses, brackets, or braces at the end of a line in the REPL (no more counting trailing delimiters!).

\- \*\*Clojure Data Structures\*\*: 

&#x20; - `()` for code and execution blocks.

&#x20; - `\[]` for ordered data Vectors (Python tuples).

&#x20; - `{}` for associative Maps/Dictionaries (Python dicts).

\- \*\*Clojure Keywords \& Property Lists\*\*: Keywords starting with `:` evaluate to themselves. If a keyword is called as a function (e.g., `(:name user)`), it performs a direct dictionary lookup.

\- \*\*Full String Literals Support\*\*: Differentiates between Lisp symbols (variable names) and raw string values using Python `dataclasses`.

\- \*\*Workspace State Management\*\*: Built-in environment persistence via `(save "filename")` and `(load "filename")`, which serialize/deserialize user functions and variables as valid, human-readable Lisp source code.



\## Quick Start



Run the interpreter directly using Python 3:



```bash

python lispy.py

```



\### REPL Example Usage



```lisp

Modern Python 3 Lispy Interpreter Started.

Features: Unclosed brackets are fixed, Clojure map/vector types supported.

Workspace functions: (save "name") and (load "name") are active.



lis.py> (define user {:name "Tony" :status "Trusty"})

lis.py> (:name user)

"Tony"



lis.py> (define square (lambda \[x] (\* x x)))

lis.py> (square 9)

81



lis.py> (save "my\_workspace")

Workspace saved to my\_workspace.lisp

```



