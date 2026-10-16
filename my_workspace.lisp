(define ln log)
(define user {:name "Tony" :status "Trusty"})
(define square (lambda [x] (* x x)))
(define fact-iter
  (lambda [n acc]
    (if (< n 2)
        acc
        (fact-iter (- n 1) (* n acc)))))

(define fact
    (lambda [n]
      (fact-iter n 1)))
  
(define bitlength (lambda [n] (if (>= n 1) (+ 1 (bitlength (/ n 2))) 0)))

(define to-binary
  (lambda [n]
    (begin
      (define m (floor (abs n)))     ; work with the magnitude
      (define s "")
      (if (= m 0)
          (set! s "0")
          (while (> m 0)
            (set! s (append (str (floor (fmod m 2))) s))
            (set! m (floor (/ m 2)))))
      (if (< n 0)
          (append "-" s)
          s))))