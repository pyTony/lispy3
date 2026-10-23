# Text output and turtle text

`(write object)` writes one object as readable Lisp text, without a newline,
and returns the object. Strings include quotes. Use `(terpri)` or `(newline)`
for a newline. Output follows the current Listener/terminal destination.

```lisp
(write (list 5 7 8))
(terpri)
```

This writes `(5 7 8)` to the Listener or terminal. At a REPL, returning the
object can also cause it to be shown as the expression's result.
`write` currently accepts one object, without Common Lisp stream or formatting
keyword arguments.

`(turtle:write "Hello")` draws text in the turtle graphics window. Earlier
versions exposed turtle's function as plain `write`; update drawing code to
use `turtle:write`. Other existing turtle names such as `forward` are unchanged.
This explicit alias does not introduce a new library import or `with-turtle`
macro.

## Dot product and drawing dots

With NumPy, `(dot a b)` computes a numerical dot product; `a-dot` remains a
compatibility alias. `(turtle:dot size color)` draws a dot. Plain `dot` no
longer names a turtle command, including in the interpreter without NumPy.
Other short turtle names are retained where they do not conflict.
