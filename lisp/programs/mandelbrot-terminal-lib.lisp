;; Native Lisp terminal Mandelbrot renderer. No turtle window is used.
;; Entry point: (mandelbrot-terminal coloured? width height iterations).
;; Width/height must be integers >= 2; iterations must be a positive integer.
(import (prefix (only mini-basic COLOUR ANSI-RESET) mandel:))

(define (mandelbrot-terminal-escape cx cy limit)
  (let [x 0.0 y 0.0 n 0]
    (while (and (< n limit) (<= (+ (* x x) (* y y)) 4.0))
      (let [next-x (+ (- (* x x) (* y y)) cx)]
        (set! y (+ (* 2.0 x y) cy))
        (set! x next-x))
      (set! n (+ n 1)))
    n))

(define (mandelbrot-terminal coloured? width height limit)
  (let [ramp ".,:;ox%#@" last-colour -1]
    (if coloured? (begin (mandel:ANSI-RESET) (mandel:COLOUR 128)))
    (dotimes [row height]
      (let [cy (+ -1.0 (/ (* 2.0 row) (- height 1)))]
        (dotimes [col width]
          (let [cx (+ -2.2 (/ (* 3.0 col) (- width 1)))
                n (mandelbrot-terminal-escape cx cy limit)
                ink (if (= n limit) 0 (+ 9 (modulo n 6)))
                glyph (if (= n limit) " "
                          (substring ramp (modulo n 9) (+ (modulo n 9) 1)))]
            (if (and coloured? (not (= ink last-colour)))
                (begin (mandel:COLOUR ink) (set! last-colour ink)))
            (format #t "~a" glyph))))
      (format #t "~%"))
    (if coloured? (mandel:ANSI-RESET))
    #f))
