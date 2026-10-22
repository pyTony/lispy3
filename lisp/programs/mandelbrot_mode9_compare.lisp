;; Mandelbrot benchmark with the new Lispy3 Pygame graphics backend.
;; This is a MODE-9-inspired *approximation*, NOT a verified port of
;; mini_basic's mandelbrot_archimedes_mode9.bas.
;; Run from the lispy3 project root:
;;   python lispy3.py lisp/programs/mandelbrot_mode9_compare.lisp
;; Adjust the parameters below to match the original BASIC listing.
;; Measure with (time (draw-mandelbrot-mode9)) in an interactive REPL.

;; Archimedes MODE 9-like framebuffer: 320x256, displayed at 640x512.
;; For a quicker first test, change these to 160,128 (window is still 640x512).
(define mb-width 320)
(define mb-height 256)
(define mb-max-iter 24)
(define mb-centre-real -0.6)
(define mb-centre-imag 0.0)
;; Horizontal field of view; same pixel scale on both axes.
(define mb-real-span 3.2)

;; A 8-colour palette inspired by the screenshot, not an exact reproduction.
;; Number 0 is the Mandelbrot interior (black).
(define mb-colours
  '((0 0 0)        ; 0 black
    (255 0 0)      ; 1 red
    (0 255 0)      ; 2 green
    (255 255 0)    ; 3 yellow
    (0 0 255)      ; 4 blue
    (255 0 255)    ; 5 magenta
    (0 255 255)    ; 6 cyan
    (255 255 255)) ; 7 white
 )

(define (mb-escape cr ci limit)
  (let ((zr 0.0) (zi 0.0) (n 0))
    (while (and (< n limit) (< (+ (* zr zr) (* zi zi)) 4.0))
      (let ((new-r (+ (- (* zr zr) (* zi zi)) cr)))
        (set! zi (+ (* 2.0 zr zi) ci))
        (set! zr new-r))
      (set! n (+ n 1)))
    n))

(define (mb-colour-index iterations limit)
  (if (= iterations limit)
      0
      ;; straight modulus colouring
      (+ 1 (mod iterations 7))))

(define (mb-draw-run first-x last-x row colour-index)
  ;; Draw one constant-colour horizontal run: fewer Python graphics calls.
  (let ((rgb (nth colour-index mb-colours)))
    (graphics-line first-x row last-x row
                   (nth 0 rgb) (nth 1 rgb) (nth 2 rgb))))

(define (draw-mandelbrot-mode9)
  (graphics-rgb-mode mb-width mb-height)
  (graphics-open 640 512)
  (graphics-clear 0 0 0)
  (let ((step (/ mb-real-span mb-width)))
    (dotimes [row mb-height]
      (let ((ci (+ mb-centre-imag (* (- (/ mb-height 2) row) step)))
            (run-start 0)
            (previous-colour -1))
        (dotimes [col mb-width]
          (let ((cr (+ mb-centre-real (* (- col (/ mb-width 2)) step))))
            (let ((colour (mb-colour-index (mb-escape cr ci mb-max-iter) mb-max-iter)))
              (if (= previous-colour -1)
                  (set! previous-colour colour)
                  (if (= previous-colour colour)
                      #f
                      (begin
                        (mb-draw-run run-start (- col 1) row previous-colour)
                        (set! run-start col)
                        (set! previous-colour colour)))))))
        (mb-draw-run run-start (- mb-width 1) row previous-colour))
      ;; SDL event polling/update while rendering.
      (if (= (mod row 8) 0) (graphics-present) #f)))
  (graphics-present)
  (display "MODE9-style Mandelbrot: " mb-width "x" mb-height
           ", iterations=" mb-max-iter "\n")
  'ok)

;; Uncomment this line to render immediately in script mode.
(time (draw-mandelbrot-mode9))

;; Keep the finished picture responsive. Close the window or press Escape.
(while (graphics-window-open?)
  (graphics-present)
  (sleep 0.02))
