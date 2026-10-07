(define ln log)
(define user {:name "Tony" :status "Trusty"})
(define square (lambda [x] (* x x)))
(define fact (lambda [n] (if (< n 2) 1 (* (fact (- n 1)) n))))
