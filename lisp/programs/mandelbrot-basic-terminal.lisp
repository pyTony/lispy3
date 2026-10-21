;; Run the BASIC terminal demo through lispy3 mini-basic, without colour.
(import (only mini-basic bbc-load bbc-run))
(bbc-load "lisp/programs/mandelbrot-terminal.bas")
(bbc-run "PROCmandelbrot(FALSE,79,25,40)")
