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

(begin
  (pu)
  (goto -200 -100)
  (pd)
  (speed 0)
  (koch 400 3)
  (bye))
