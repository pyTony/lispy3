# Terminal Mandelbrot: BASIC and Lisp

There are four terminal launchers: plain and ANSI-coloured output, each rendered
by BASIC or native Lisp. They all use the same 79-column by 25-row view and
40-iteration limit. These demos do not open a graphics window.

Run from the repository root:

| Renderer | Plain text | ANSI colour |
|----------|------------|-------------|
| Native Lisp | `python lispy3.py lisp/programs/mandelbrot-terminal.lisp` | `python lispy3.py lisp/programs/mandelbrot-terminal-colour.lisp` |
| BASIC through mini-basic | `python lispy3.py lisp/programs/mandelbrot-basic-terminal.lisp` | `python lispy3.py lisp/programs/mandelbrot-basic-terminal-colour.lisp` |

The same launchers work with `lispy3-numpy.py` in place of `lispy3.py`.
Plain mode emits only characters and newlines, so it can be redirected to a file.
Colour mode selects a black background, uses bright ANSI foreground colours and
restores terminal defaults at completion. It requires an ANSI-capable terminal;
the Tk Listener does not emulate those controls.

## Call the renderers yourself

Load the native Lisp implementation without drawing, then choose a mode and size:

```lisp
(load "programs/mandelbrot-terminal-lib")
(mandelbrot-terminal #f 79 25 40)
(mandelbrot-terminal #t 79 25 40)
```

The arithmetic and loops are Lisp. The renderer imports only COLOUR and
ANSI-RESET from mini-basic for terminal output, using the private `mandel:` prefix.
It does not run its Mandelbrot calculation through the BASIC reader.

The BASIC source lives in `lisp/programs/mandelbrot-terminal.bas`. It defines
procedures/functions without drawing until called:

```lisp
(import (only mini-basic bbc-load bbc-run))
(bbc-load "lisp/programs/mandelbrot-terminal.bas")
(bbc-run "PROCmandelbrot(FALSE,79,25,40)")
(bbc-run "PROCmandelbrot(TRUE,79,25,40)")
```

Arguments are colour flag, width, height and iteration limit. Supply integer
width/height at least 2 and a positive integer limit. A smaller view such as
31 by 13 with 40 iterations is useful for quick checks. Both use x from -2.2 to
0.8 and y from -1 to 1, with z initially zero and iteration z = z*z + c.
A point escapes when its squared magnitude exceeds 4; points still bounded at
the iteration limit are shown as spaces. The exterior uses `.,:;ox%#@` shading.

The BASIC demo targets lispy3 mini-basic and uses its ANSI extension to reset
terminal attributes. It is not a claim of unchanged portability to BBCSDL or to
the separate Python mini_basic interpreter. The earlier external
`examples/graphics/mandelbrot/mandelbrot2.bas` remains a separate plain-text demo.

## Graphical version and checks

The turtle graphical version, with mouse-wheel zoom, remains
`lisp/programs/mandelbrot.lisp`:

```bash
python lispy3.py lisp/programs/mandelbrot.lisp
```

The terminal versions have no interactive zoom. You can time a render in the
REPL by wrapping a call in `(time ...)`; timings include interpreter overhead
and are not directly comparable to BBCSDL native performance.

Regression tests compare BASIC and Lisp against a complex-number reference,
check known inside/outside/boundary points, verify the coloured/plain pictures
match, and exercise all four launchers and their terminal reset sequences:

```bash
python -m pytest tests/test_terminal_mandelbrot.py -q
```
