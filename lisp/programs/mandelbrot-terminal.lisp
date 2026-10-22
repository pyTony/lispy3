;; Native Lisp: plain 79-column terminal Mandelbrot.
(load "programs/mandelbrot-terminal-lib")
(time (mandelbrot-terminal #f 79 25 40))
