;; Spinning soccer ball with a frames-per-second count: a native Lispy version
;; of BBC BASIC for SDL's examples/graphics/soccerball.bbc.
;;   python lispy3.py lisp/programs/soccer-ball.lisp
;; Close the window or press Escape to stop early.

;; ---- Settings ----
(define frames 300)          ; how many frames to time
(define spin 0.03)           ; turn per frame, in radians

;; Corner coordinates use the golden ratio
(define s (+ (sqrt 5) 1))
(define p (/ s 2))
(define q (+ p 2))
(define r (+ s 1))
(define u (* p 3))

;; The 12 black pentagons, 5 corners (x y z) each, in triangle-strip order
(define corners
  (list 0 1 u (- p) 2 r p 2 r -1 q s 1 q s
        0 1 (- u) (- p) 2 (- r) p 2 (- r) -1 q (- s) 1 q (- s)
        0 -1 u (- p) -2 r p -2 r -1 (- q) s 1 (- q) s
        0 -1 (- u) (- p) -2 (- r) p -2 (- r) -1 (- q) (- s) 1 (- q) (- s)
        1 u 0 2 r (- p) 2 r p q s -1 q s 1
        1 (- u) 0 2 (- r) (- p) 2 (- r) p q (- s) -1 q (- s) 1
        -1 u 0 -2 r (- p) -2 r p (- q) s -1 (- q) s 1
        -1 (- u) 0 -2 (- r) (- p) -2 (- r) p (- q) (- s) -1 (- q) (- s) 1
        u 0 1 r (- p) 2 r p 2 s -1 q s 1 q
        u 0 -1 r (- p) -2 r p -2 s -1 (- q) s 1 (- q)
        (- u) 0 1 (- r) (- p) 2 (- r) p 2 (- s) -1 q (- s) 1 q
        (- u) 0 -1 (- r) (- p) -2 (- r) p -2 (- s) -1 (- q) (- s) 1 (- q)))

;; As a 3 x 60 matrix: a row of x, a row of y (depth) and a row of z
(define xyz [(make-vector 60 0) (make-vector 60 0) (make-vector 60 0)])
(dotimes [k 180]
  (vector-set! (vector-ref xyz (mod k 3)) (div k 3) (nth corners k)))
(define view [(make-vector 60 0) (make-vector 60 0) (make-vector 60 0)])

(define (tilt b) [[(cos b) 0 (- (sin b))] [0 1 0] [(sin b) 0 (cos b)]])
(define (turn c) [[(cos c) (sin c) 0] [(- (sin c)) (cos c) 0] [0 0 1]])

;; Perspective: 640 x 512 window, the ball centred
(define (screen k)
  (let [depth (+ 36 (vector-ref (vector-ref view 1) k))]
    (list (+ 320 (/ (* 1600 (vector-ref (vector-ref view 0) k)) depth))
          (- 256 (/ (* 1600 (vector-ref (vector-ref view 2) k)) depth)))))

(define (pentagon i)
  ;; Draw it only when it faces us; strip order 0 1 2 3 4 goes round as 0 2 4 3 1
  (let [ys (vector-ref view 1)]
    (when (< (+ (vector-ref ys i) (vector-ref ys (+ i 1)) (vector-ref ys (+ i 2))
                (vector-ref ys (+ i 3)) (vector-ref ys (+ i 4)))
             -2.5)
      (graphics-polygon (list (screen i) (screen (+ i 2)) (screen (+ i 4))
                              (screen (+ i 3)) (screen (+ i 1)))
                        0 0 0))))

(define (draw-ball angle)
  (mat* (mat* (tilt 0.5) (turn angle)) xyz view)
  (graphics-clear 0 128 0)
  (graphics-circle-fill 320 256 216 255 255 255)
  (dotimes [j 12] (pentagon (* j 5)))
  (graphics-refresh))

(graphics-rgb-mode 640 512)
(graphics-open 640 512)
(graphics-refresh #f)        ; show only finished frames, like *REFRESH OFF
(define start (clock))
(define frame 0)
(while (and (< frame frames) (graphics-window-open?))
  (draw-ball (* frame spin))
  (set! frame (+ frame 1)))
(define seconds (- (clock) start))
(display (string-append (number->string frame) " frames in "
                        (number->string (/ (round (* seconds 100)) 100.0)) " s: "
                        (number->string (round (/ frame (max seconds 0.001))))
                        " frames per second"))
