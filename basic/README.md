# BASIC examples and compatibility checks

BASIC source and reference evidence for lispy3 mini-basic live here. The
separate Python mini_basic repository is not vendored here.

| Directory | Contents |
|---|---|
| [examples/](examples/) | BASIC examples; .out files beside golden-output fixtures |
| [bench/](bench/) | BASIC timing comparison programs |
| [reference/](reference/README.md) | BBCSDL runners, tokenised fixtures, extracted Python tests and recorded results |

From the repository root:

```lisp
(import (only mini-basic bbc-load bbc-run))
(bbc-load "basic/examples/structure.bas")
(bbc-load "basic/examples/mandelbrot-terminal.bas")
(bbc-run "PROCmandelbrot(TRUE,79,25,40)")
```

Choose ANSI terminal output for the coloured example. The Mandelbrot BASIC
file defines procedures; its Lisp launchers remain under lisp/programs/.

The Lisp implementation stays in lisp/mini-basic.lisp, mini-basic-ext.lisp
and mini-basic.sld (the Scheme-style library/export declaration).
Cross-Lisp implementations and Lisp-form comparison programs stay under
[compare/](../compare/README.md). Python tests stay in tests/; run
`python -m pytest tests -q` from the repository root.

These files moved from compare/basic/, compare/bench/, compare/reference/
and lisp/programs/mandelbrot-terminal.bas. Historical JSON manifests and raw
logs retain original paths and timestamps as recorded evidence; use the new
paths when repeating a run. Sources, tokenised fixtures and captured outputs
were moved without changing their contents.
