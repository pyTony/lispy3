; Digits of pi with the Rabinowitz-Wagon spigot algorithm.
;
;   python lispy3.py pi_digits.lisp
;
; Change n below for more or fewer decimals. Or, from the REPL:
;   (load "pi_digits")
;   (display (pi-digits 200))
;
; A spigot hands out the digits of pi one at a time, using only small
; whole numbers: no big decimals and no floating point error. The number
; is kept in a "mixed radix" form in the vector a, every step multiplies
; it by 10, and the carry that falls out of the front is the next digit.
;
; Lispy has no whole-number quotient yet, so (div x d) is (floor (/ x d)).
; That is exact here, because every x stays far below 2^53.
; Everything loops with while, so it needs no recursion depth.
; It runs in time n*n: 100 decimals take a moment, 1000 take minutes.

(define n 100)

(define div (lambda [x d] (floor (/ x d))))
(define mod (lambda [x d] (- x (* d (div x d)))))

(define pi-digits
  (lambda [decimals]
    (begin
      ; a few spare digits, so a pending run of 9s at the end settles
      (define total (+ decimals 6))
      (define size (+ (div (* 10 total) 3) 1))
      (define a (make-vector size 2))
      (define out "")
      (define emitted 0)
      (define nines 0)
      (define predigit 0)
      (define q 0)
      (define x 0)
      (define i 0)
      (define j 0)
      ; emit adds one digit to out. The first digit out of the spigot is a
      ; leading 0 and is skipped, the 3 gets its decimal point, and digits
      ; past the decimals we were asked for are dropped.
      (define emit
        (lambda [d]
          (begin
            (if (= emitted 1)
                (set! out (append (str d) "."))
                (if (> emitted 1)
                    (if (<= emitted (+ decimals 1))
                        (set! out (append out (str d)))
                        0)
                    0))
            (set! emitted (+ emitted 1)))))
      (while (< j (+ total 1))
        ; multiply every place by 10 and carry from the back to the front
        (set! q 0)
        (set! i size)
        (while (> i 0)
          (set! x (+ (* 10 (vector-ref a (- i 1))) (* q i)))
          (vector-set! a (- i 1) (mod x (- (* 2 i) 1)))
          (set! q (div x (- (* 2 i) 1)))
          (set! i (- i 1)))
        (vector-set! a 0 (mod q 10))
        (set! q (div q 10))
        ; q is the next digit, but a 9 or a 10 may still change the ones before
        (if (= q 9)
            (set! nines (+ nines 1))
            (if (= q 10)
                (begin
                  (emit (+ predigit 1))
                  (while (> nines 0) (emit 0) (set! nines (- nines 1)))
                  (set! predigit 0))
                (begin
                  (emit predigit)
                  (set! predigit q)
                  (while (> nines 0) (emit 9) (set! nines (- nines 1))))))
        (set! j (+ j 1)))
      out)))

(display (pi-digits n))
