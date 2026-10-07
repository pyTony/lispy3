\# LLM Context \& Developer Guide for lispy3



This document provides large language models (LLMs) and AI coding assistants with the essential architecture, syntax rules, and context required to modify, extend, or debug the `lispy3` interpreter efficiently.



\## Core Project Context

\- \*\*Origin\*\*: Evolution of Peter Norvig's `lis.py` Scheme interpreter.

\- \*\*Implementation Language\*\*: Modern Python 3 (using static type hints and Structural Pattern Matching).

\- \*\*Dialect Flavor\*\*: Mostly Scheme semantics but highly infused with \*\*Clojure syntax and data paradigms\*\*.



\---



\## Technical Architecture \& Types



The Abstract Syntax Tree (AST) is composed of native Python data types wrapped around a specific naming mapping:



\- \*\*`Symbol`\*\*: Implemented as a plain Python `str`. Represents variable names or function operators.

\- \*\*`String`\*\*: A frozen Python `@dataclass` holding a single `value: str`. Separates pure textual data literals from symbols.

\- \*\*`List`\*\*: A standard Python `list`. Evaluates as a Lisp function application/code block unless quoted.

\- \*\*`Vector`\*\*: Implemented as a Python `tuple`. Evaluates its items but treats the structure as an immutable ordered data block.

\- \*\*`Map`\*\*: Implemented as a standard Python `dict`. Evaluates its values but keeps symbol keys raw.

\- \*\*`Procedure`\*\*: A custom class wrapper replacing standard Python lambdas. Retains access to the function's parameter names (`parms`), code body (`body`), and closure environment (`env`) to allow clean serialization.



\---



\## Distinct \& Non-Standard Features (Crucial for Code Generation)



When writing or extending code for this interpreter, you must respect the following unique behaviors:



\### 1. Forgiving Parser (Auto-Closing Delimiters)

The `read\_from\_tokens` parser intercepts unmatched trailing delimiters. If the token stream runs out before a closing `)`, `]`, or `}` is encountered, the parser closes the structural block safely instead of throwing an EOF syntax error.



\### 2. Clojure Keyword Lookup Paradigm

\- Symbols beginning with a colon (e.g., `:name`) are \*\*Keywords\*\* and evaluate strictly to themselves.

\- Keywords can act as functions for associative maps. The pattern `(:key map)` is fully implemented to trigger a dictionary lookup, behaving like:

&#x20; ```python

&#x20; case \[str(keyword), target\_exp] if keyword.startswith(':'):

&#x20; ```



\### 3. State Persistence (`save` and `load`)

Environment states can be serialized. The interpreter formats the actively modified `global\_env` symbols back into explicit Lisp declarations via `lisp\_str`.

\- `(save "filename")` stores custom functions and variables as pure Lisp source code (`(define name value)`). It ignores immutable primitives (`math.pi`, standard procedures) and strips `nan`.

\- `(load "filename")` reads the text file line-by-line and evaluates it directly against the active `global\_env`.



\---



\## Evaluation Slices (`eval\_exp` Reference)



The interpreter processes expressions via a robust pattern-matching framework. When extending syntax, follow this structural template:



```python

match x:

&#x20;   case str(symbol) if symbol.startswith(':'):  # Keyword literal

&#x20;       return x

&#x20;   case tuple(elements):                       # Data vector evaluation

&#x20;       return \[eval\_exp(e, env) for e in elements]

&#x20;   case dict(d):                               # Map literal evaluation

&#x20;       return {k if isinstance(k, str) else eval\_exp(k, env): eval\_exp(v, env) for k, v in d.items()}

&#x20;   case \['let', list(bindings) | tuple(bindings), body]: # Scoped block bindings

&#x20;       ...

```



\## Guidelines for AI Modifications

\- \*\*Language Uniformity\*\*: Keep all comments, error messages, and variables strictly in English.

\- \*\*No Python Lambdas for Lisp Lambdas\*\*: Always instantiate a `Procedure` object when encountering a `\['lambda', ...]` case to preserve workspace serialization capabilities.

\- \*\*Types\*\*: Always leverage `TypeAlias` conventions when declaring functions returning or transforming `Exp`.



