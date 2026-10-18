(define sieve-size 8192)
(define flags (make-num-vector (+ sieve-size 1) 1))
(define cnt 0)

(define run-sieve
  (lambda [iterations]
    (begin
      (define i 1)
      (define j 0)
      (define prime 0)
      (define stop (+ sieve-size 1))
      (while (<= i iterations)
        ;; 1. Vectorized reset: replaces first 8192-iteration while loop
        (vector-fill! flags 1 0 stop)
        (set! j 0)
        ;; 2. Vectorized strike-out: one slice assignment per prime instead of an inner loop.
        ;; Item j is the odd number 2j+3. Unlike the original, item 0 (the number 3) is
        ;; sieved too, so primes up to sqrt(16387) are enough: j <= 62 (prime 127).
        (while (<= j 62)
          (if (= (vector-ref flags j) 1)
              (begin
                (set! prime (+ (+ j j) 3))
                (vector-slice-set! flags (+ j prime) stop prime 0))
              0)
          (set! j (+ j 1)))
        ;; 3. Fast C-level sum of the 1s left: the odd primes 3..16387. The original
        ;; counts 5..16387 plus 9 (it never sieves by 3), which is the same 1899.
        (set! cnt (sum flags))
        (set! i (+ i 1))))))

(display "Starting 10 iterations of the Vectorized NumPy Sieve...")
(define t0 (clock))
(run-sieve 10)
(define elapsed (/ (floor (* (- (clock) t0) 10000)) 10000.0))
(display "Done. Primes found: " cnt " TIME " elapsed)