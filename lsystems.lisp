;; 1. Draw a single character. If it's F and depth > 0, expand the rule natively.
;;    F = line forward, + = turn left, - = turn right,
;;    [ = remember position and heading (start a branch), ] = go back to them.
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
          (if (= c #\[)
            (push-pose)
            (if (= c #\])
              (pop-pose)
              [])))))))

;; 2. Map over a sequence. Native `map` handles horizontal iteration without recursion.
(define draw-sys
  (lambda (commands rule depth step angle)
    (map (lambda (c)
           (draw-node c rule depth step angle))
         commands)))

;; 3. Draw a whole L-system with one call:
;;    (lsystem-from axiom rule generations step angle x y heading)
;;    generations = how many times the rule is applied
;;    step        = length of one line, in pixels
;;    x y         = where the drawing starts
;;    heading     = starting direction in degrees (0 = right, 90 = up)
;;    Drawing runs with automatic redrawing off (much faster). It is switched
;;    back on at the end, so commands typed afterwards, like (rt 180), show up.
(define lsystem-from
  (lambda (axiom rule generations step angle x y heading)
    (begin
      (tracer 0 0)
      (clear)
      (clear-poses)
      (pu)
      (goto x y)
      (setheading heading)
      (pd)
      (draw-sys (seq axiom) rule generations step angle)
      (update)
      (tracer 1 10))))

;; Same, starting towards the right: (lsystem axiom rule generations step angle x y)
(define lsystem
  (lambda (axiom rule generations step angle x y)
    (lsystem-from axiom rule generations step angle x y 0)))
