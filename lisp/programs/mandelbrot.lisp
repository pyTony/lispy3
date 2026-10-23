;; Mandelbrot set drawn with the turtle.
;; Turn the mouse wheel over the picture: away from you zooms in around the
;; pointer, towards you zooms out. Run:  python lispy3.py lisp/programs/mandelbrot.lisp

(define (escape cx cy max-iter)
  ;; how many steps z -> z*z + c takes to leave the circle of radius 2
  (let ((x 0.0) (y 0.0) (n 0))
    (while (and (< n max-iter) (< (+ (* x x) (* y y)) 4.0))
      (let ((xt (+ (- (* x x) (* y y)) cx)))
        (set! y (+ (* 2.0 x y) cy))
        (set! x xt))
      (set! n (+ n 1)))
    n))

(define (escape-colour n max-iter)
  (if (= n max-iter)
      "black"
      (let ((f (/ n max-iter)))
        (list f (* 0.5 f) (- 1 f)))))

;; The view: the picture is w x h cells of `cell` pixels; the point at the
;; middle of the window is (mandel-x, mandel-y) and one pixel is mandel-step.
(define mandel-w 120)
(define mandel-h 80)
(define cell 3)
(define mandel-x -0.6)
(define mandel-y 0.0)
(define mandel-step (/ 3.2 (* mandel-w cell)))
(define mandel-iter 30)

(define (draw-mandelbrot)
  (tracer 0) (hideturtle) (clear) (pu) (setheading 0) (pensize cell)
  (dotimes [row mandel-h]
    (let ((y (* cell (- (/ mandel-h 2) row))))
      (dotimes [col mandel-w]
        (let ((x (* cell (- col (/ mandel-w 2)))))
          ;; a short stroke; turtle points use (turtle:dot ...), numerical products use dot
          (goto x y)
          (pencolor (escape-colour (escape (+ mandel-x (* x mandel-step))
                                           (+ mandel-y (* y mandel-step))
                                           mandel-iter)
                                   mandel-iter))
          (pd) (fd cell) (pu))))
    (update))
  (update))

(define (zoom x y step)
  ;; keep the point under the pointer where it is, and look twice as close
  (let ((factor (if (> step 0) 0.5 2.0)))
    (set! mandel-x (+ mandel-x (* x mandel-step (- 1 factor))))
    (set! mandel-y (+ mandel-y (* y mandel-step (- 1 factor))))
    (set! mandel-step (* mandel-step factor))
    (set! mandel-iter (max 30 (+ mandel-iter (* 15 step))))
    (draw-mandelbrot)))

(draw-mandelbrot)
(onscroll zoom)
