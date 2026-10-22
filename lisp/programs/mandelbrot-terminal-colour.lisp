;; Native Lisp: ANSI-coloured 79-column terminal Mandelbrot.
(load "programs/mandelbrot-terminal-lib")
(time (mandelbrot-terminal #t 79 25 40))
