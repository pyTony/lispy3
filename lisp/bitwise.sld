;;; bitwise.sld - bit operations on whole numbers
;;;
;;;   (import bitwise)                  ; or (import (prefix bitwise bits:))
;;;   (bitwise-and #b1100 #b1010)       ; 8
;;;   (arithmetic-shift 1 4)            ; 16, a negative count shifts right
;;;   (signed-field #xFFFFFFFF 32)      ; -1, as a 32-bit integer
;;;
;;; Names follow Scheme: R7RS #b/#o/#x literals (read by lispy3 itself) and
;;; SRFI 151 procedures. The Common Lisp names (logand, ash ...) are aliases,
;;; as rem is for remainder. Numbers are whole and of any size, negative ones
;;; in two's complement with infinitely many sign bits. signed-field and
;;; logical-shift-right give BASIC-style fixed-width integers.

(define-library bitwise
  (export bitwise-and bitwise-ior bitwise-xor bitwise-not arithmetic-shift
          bit-count integer-length bit-set? bit-field signed-field logical-shift-right
          logand logior logxor lognot ash logcount logbitp)
  (begin
    (define (whole n who)
      (if (and (exact? n) (integer? n))
          n
          (error (str who ": needs a whole number, not " n))))

    (define (fold-bits who op start ns)
      (reduce (lambda (acc n) (op acc (whole n who))) start ns))

    (define (bitwise-and & ns) (fold-bits "bitwise-and" (lambda (a b) (a/__and__ b)) -1 ns))
    (define (bitwise-ior & ns) (fold-bits "bitwise-ior" (lambda (a b) (a/__or__ b)) 0 ns))
    (define (bitwise-xor & ns) (fold-bits "bitwise-xor" (lambda (a b) (a/__xor__ b)) 0 ns))
    (define (bitwise-not n) (let [x (whole n "bitwise-not")] (x/__invert__)))

    (define (arithmetic-shift n count)
      ;; Left for a positive count, right (rounding down) for a negative one
      (let [x (whole n "arithmetic-shift")
            k (whole count "arithmetic-shift")]
        (if (>= k 0) (x/__lshift__ k) (x/__rshift__ (- k)))))

    (define (bit-count n)
      ;; 1 bits of a positive number, 0 bits of a negative one
      (let [x (whole n "bit-count")]
        (if (< x 0) (let [y (x/__invert__)] (y/bit_count)) (x/bit_count))))

    (define (integer-length n)
      ;; Bits needed for n, not counting the sign
      (let [x (whole n "integer-length")]
        (if (< x 0) (let [y (x/__invert__)] (y/bit_length)) (x/bit_length))))

    (define (bit-set? index n)
      (not (= 0 (bitwise-and (arithmetic-shift n (- index)) 1))))

    (define (bit-field n start end)
      ;; Bits start .. end-1 of n as an unsigned number
      (bitwise-and (arithmetic-shift n (- start))
                   (- (arithmetic-shift 1 (- end start)) 1)))

    (define (signed-field n width)
      ;; The low width bits of n read as a two's complement number
      (let [u (bit-field n 0 width)]
        (if (bit-set? (- width 1) u) (- u (arithmetic-shift 1 width)) u)))

    (define (logical-shift-right n count width)
      ;; Shift the low width bits of n right, filling with zeros
      (arithmetic-shift (bit-field n 0 width) (- count)))

    (define logand bitwise-and)
    (define logior bitwise-ior)
    (define logxor bitwise-xor)
    (define lognot bitwise-not)
    (define ash arithmetic-shift)
    (define logcount bit-count)
    (define logbitp bit-set?)))
