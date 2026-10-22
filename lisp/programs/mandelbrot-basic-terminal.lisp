;; Run the BASIC terminal demo through lispy3 mini-basic, without colour.
(import (only mini-basic bbc-load bbc-run))
(bbc-load "basic/examples/mandelbrot-terminal.bas")
(bbc-run "PROCmandelbrot(FALSE,79,25,40)")
