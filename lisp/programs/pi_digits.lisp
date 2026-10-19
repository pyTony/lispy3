; Digits of pi with the Rabinowitz-Wagon spigot algorithm.
;
;   python lispy3.py pi_digits.lisp
;
; Change n below for more or fewer decimals. Or, from the REPL:
;   (load "pi_digits")
;   (display (pi-digits 200))
;
; A spigot hands out the digits of pi one at a time, using only whole
; numbers: no decimals and no floating point error. The number is kept in
; a "mixed radix" form in the vector a, every step multiplies it by 10,
; and the carry that falls out of the front is the next digit.
;
; The whole-number work is done by divmod, which gives the quotient and
; the remainder at once: (divmod 17 5) is (3 2). div and mod give one each.
; Everything loops with while, so it needs no recursion depth.
; It runs in time n*n: 100 decimals take a moment, 1000 take minutes.

(define n 100)

(define (pi-digits decimals)
  ; a few spare digits, so a pending run of 9s at the end settles
  (define total (+ decimals 6))
  (define size (+ (div (* 10 total) 3) 1))
  (define a (make-vector size 2))
  (define out "")
  (define emitted 0)
  (define nines 0)
  (define predigit 0)
  (define q 0)
  (define i 0)
  (define j 0)
  ; emit adds one digit to out. The first digit out of the spigot is a
  ; leading 0 and is skipped, the 3 gets its decimal point, and digits
  ; past the decimals we were asked for are dropped.
  (define (emit d)
    (cond ((= emitted 1) (set! out (str d ".")))
          ((< 1 emitted (+ decimals 2)) (set! out (str out d))))
    (set! emitted (+ emitted 1)))
  (while (<= j total)
    ; multiply every place by 10 and carry from the back to the front
    (set! q 0)
    (set! i size)
    (while (> i 0)
      (define qr (divmod (+ (* 10 (vector-ref a (- i 1))) (* q i))
                         (- (* 2 i) 1)))
      (vector-set! a (- i 1) (nth qr 1))
      (set! q (first qr))
      (set! i (- i 1)))
    (vector-set! a 0 (mod q 10))
    (set! q (div q 10))
    ; q is the next digit, but a 9 or a 10 may still change the ones before
    (cond ((= q 9) (set! nines (+ nines 1)))
          ((= q 10)
           (emit (+ predigit 1))
           (dotimes [k nines] (emit 0))
           (set! nines 0)
           (set! predigit 0))
          (else
           (emit predigit)
           (set! predigit q)
           (dotimes [k nines] (emit 9))
           (set! nines 0)))
    (set! j (+ j 1)))
  out)

(display (pi-digits n))
