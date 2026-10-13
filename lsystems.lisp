;; 1. Draw a single character. If it's F and depth > 0, expand the rule natively.
(define draw-node
  (lambda (c rule depth step angle)
    (if (= c #\F)
      (if (= depth 0)
        (fd step)
        (draw-sys (seq rule) rule (- depth 1) step angle))
      (if (= c #\+)
        (lt angle)
        (if (= c #\-)
          (rt angle)
          [])))))

;; 2. Map over a sequence. Native `map` handles horizontal iteration without recursion.
(define draw-sys
  (lambda (commands rule depth step angle)
    (map (lambda (c) 
           (draw-node c rule depth step angle)) 
         commands)))

;; 3. Draw a whole L-system with one call:
;;    (lsystem axiom rule generations step angle x y)
;;    generations = how many times the rule is applied
;;    step        = length of one line, in pixels
;;    x y         = where the drawing starts
(define lsystem
  (lambda (axiom rule generations step angle x y)
    (begin
      (tracer 0 0)
      (clear)
      (pu)
      (goto x y)
      (pd)
      (draw-sys (seq axiom) rule generations step angle)
      (update))))
