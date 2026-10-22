;; Mandelbrot without turtle, using Lispy3's graphics bindings.
;; Run from the Lispy3 root:
;;   python lispy3.py lisp/programs/mandelbrot_graphics.lisp
;; Requires the graphics integration already installed.
;; The computation uses 160x120 RGB pixels; SDL scales to 640x480.

(define mandel-w 160)
(define mandel-h 120)
(define mandel-iter 48)
(define mandel-x -0.6)
(define mandel-y 0.0)
(define mandel-step (/ 3.2 mandel-w))

(define (mandel-escape cx cy max-iter)
  ;; z = z*z + c, starting with z=0; return escape iteration count.
  (let ((x 0.0) (y 0.0) (n 0))
    (while (and (< n max-iter) (< (+ (* x x) (* y y)) 4.0))
      (let ((xt (+ (- (* x x) (* y y)) cx)))
        (set! y (+ (* 2.0 x y) cy))
        (set! x xt))
      (set! n (+ n 1)))
    n))

(define (mandel-paint n max-iter px py)
  ;; Direct RGB colour: deep blue -> cyan -> yellow -> red; set is black.
  (if (= n max-iter)
      (graphics-pixel px py 0 0 0)
      (let ((shade (mod (* n 11) 256)))
        (if (< n (/ max-iter 4))
            (graphics-pixel px py 0 shade 180)
            (if (< n (/ max-iter 2))
                (graphics-pixel px py shade 220 255)
                (if (< n (* max-iter 3/4))
                    (graphics-pixel px py 255 shade 40)
                    (graphics-pixel px py 230 40 shade)))))))

(define (draw-mandelbrot)
  (graphics-rgb-mode mandel-w mandel-h)
  (graphics-open (* 4 mandel-w) (* 4 mandel-h))
  (graphics-clear)
  (dotimes [row mandel-h]
    (dotimes [col mandel-w]
      (let ((cx (+ mandel-x (* (- col (/ mandel-w 2)) mandel-step)))
            (cy (+ mandel-y (* (- (/ mandel-h 2) row) mandel-step))))
        (mandel-paint (mandel-escape cx cy mandel-iter) mandel-iter col row)))
    ;; Present once per 8 rows, keeping the SDL window responsive.
    (if (= (mod row 8) 0)
        (graphics-present)
        #f))
  (graphics-present)
  (display "Mandelbrot rendered: " mandel-w "x" mandel-h " pixels.\n"))

(time (draw-mandelbrot))

;; Keep handling the window close button after rendering, without busy waiting.
(while (graphics-window-open?)
  (graphics-present)
  (sleep 0.02))
