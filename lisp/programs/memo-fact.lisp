(define-memo (fact n)
  (let loop ((k n) (acc 1))
    (if (< k 2)
        acc
        (loop (- k 1) (* acc k)))))