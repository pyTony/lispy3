(define rewrite (lambda [state rule]
  (if (empty? state)
      []
      (append (if (= (first state) #\F)
                  (seq rule)
                  (list (first state)))
              (rewrite (rest state) rule)))))

(define generate (lambda [state rule n]
  (if (= n 0)
      state
      (generate (rewrite state rule) rule (- n 1)))))

(define draw (lambda [state d]
  (if (empty? state)
      []
      (begin
        (if (= (first state) #\F) (fd d) [])
        (if (= (first state) #\+) (lt 60) [])
        (if (= (first state) #\-) (rt 120) [])
        (draw (rest state) d)))))

(begin
  (pu)
  (goto -200 0)
  (pd)
  (speed 0)
  (draw (generate (seq "F") "F+F--F+F" 3) (/ 400 27))
  (bye))
