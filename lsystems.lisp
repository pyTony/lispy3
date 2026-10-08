(define koch (lambda [d n]
  (if (= n 0)
      (fd d)
      (begin
        (koch (/ d 3) (- n 1))
        (lt 60)
        (koch (/ d 3) (- n 1))
        (rt 120)
        (koch (/ d 3) (- n 1))
        (lt 60)
        (koch (/ d 3) (- n 1))))))

(define lsys_step (lambda [sys rules]
  (if (empty? sys) []
      (let [ch (first sys)]
        (append
           (if (= (get rules ch) "") [ch] (seq (get rules ch)))
           (lsys_step (rest sys) rules))))))

(define lsys_run (lambda [sys rules n]
  (if (= n 0) sys
      (lsys_run (lsys_step sys rules) rules (- n 1)))))

(define draw_step (lambda [sys len ang]
    (if (empty? sys) "Done"
      (let [ch (first sys)]
         (if (= ch "F") (fd len)
         (if (= ch "+") (lt ang)
         (if (= ch "-") (rt ang)
         "Skip")))))))

(define lsys_draw (lambda [sys len ang]
  (if (empty? sys) "Done"
      (begin
         (draw_step sys len ang)
         (lsys_draw (rest sys) len ang)))))

(begin
  (pu)
  (goto -200 100)
  (pd)
  (speed 0)
  (tracer 0)
  (lsys_draw (lsys_run (seq "F") {["F"] "F+F-F-F+F"} 3) 5 90)
  (update)
  (bye))
