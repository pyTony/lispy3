;; Run the BASIC terminal demo through lispy3 mini-basic, using ANSI colour.
(import (only mini-basic bbc-load bbc-run))
(bbc-load "lisp/programs/mandelbrot-terminal.bas")
(bbc-run "PROCmandelbrot(TRUE,79,25,40)")
