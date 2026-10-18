(define sieve-size 8192)
(define flags (make-num-vector (+ sieve-size 1) 1))
(define cnt 0)

(define run-sieve
  (lambda [iterations]
    (begin
      (define i 1)
      (define j 1)
      (define prime 0)
      (define stop (+ sieve-size 1))
      (while (<= i iterations)
        ;; 1. Vectorized reset: replaces first 8192-iteration while loop
        (vector-fill! flags 1 1 stop)
        (set! j 1)
        ;; In sieve-optimized.lisp, since (sum flags) counts the primes at the end,
        ;; you only need to strike out multiples up to j = 63 (where prime = 129, 129^2 > 16387):
        (while (<= j 63)
          (if (= (vector-ref flags j) 1)
              (begin
                (set! prime (+ (+ j j) 3))
                (vector-slice-set! flags (+ j prime) stop prime 0))
              0)
          (set! j (+ j 1)))
        ;; 3. Fast C-level sum of remaining 1s in range [1..sieve-size]
        (set! cnt (- (sum flags) (vector-ref flags 0)))
        (set! i (+ i 1))))))

(display "Starting 10 iterations of the Vectorized NumPy Sieve...")
(define t0 (clock))
(run-sieve 10)
(define elapsed (/ (floor (* (- (clock) t0) 10000)) 10000.0))
(display "Done. Primes found: " cnt " TIME " elapsed)