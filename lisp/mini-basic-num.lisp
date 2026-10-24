;;; mini-basic-num.lisp - BBC BASIC for SDL number types for mini-basic.lisp
;;;
;;;   PRINT %1010, &FFFFFFFF          ; binary 10, and hex as 32-bit signed: -1
;;;   PRINT 1 << 4, -16 >> 2, -16 >>> 28
;;;   PRINT ~255 : a$ = STR$~255      ; FF
;;;   A% = 3.7 : A%% = 2^40 : b& = 300 : x# = 1/4
;;;
;;; A% is a 32-bit integer ("Number too big" outside it), A%% a 64-bit one,
;;; b& an unsigned byte (the low 8 bits) and x# a float. A variable without a
;;; suffix keeps whatever number it is given. The bit work is done by the
;;; bitwise library (lisp/bitwise.sld).

(import (prefix (only bitwise arithmetic-shift bit-field signed-field logical-shift-right) bits:))

(define bbc-int32-min (- (expt 2 31)))
(define bbc-int32-max (- (expt 2 31) 1))
(define bbc-int64-min (- (expt 2 63)))
(define bbc-int64-max (- (expt 2 63) 1))

(define (bbc-whole x)
  (if (and (exact? x) (integer? x)) x (trunc x)))

(define (bbc-in-range x low high)
  (let [n (bbc-whole x)]
    (if (or (< n low) (> n high))
        (error "Number too big")
        n)))

(define (bbc-int32 x) (bbc-in-range x bbc-int32-min bbc-int32-max))
(define (bbc-int64 x) (bbc-in-range x bbc-int64-min bbc-int64-max))
(define (bbc-byte x) (bits:bit-field (bbc-whole x) 0 8))

(define (bbc-typed-value var exp)
  ;; The code that gives exp the type of var's suffix, while LET expands
  (let [name (symbol->string var)]
    (cond ((bbc-name-suffix? name "%%") `(bbc-int64 ,exp))
          ((bbc-name-suffix? name "%") `(bbc-int32 ,exp))
          ((bbc-name-suffix? name "&") `(bbc-byte ,exp))
          ((bbc-name-suffix? name "#") `(float ,exp))
          (else exp))))

(define (bbc-name-suffix? name suffix)
  (let [n (length name) k (length suffix)]
    (and (> n k) (equal? (substring name (- n k) n) suffix))))

;;; --- Reading names and constants ---

(define (bbc-name-end text start j c next)
  ;; Where a name ends: after $, %, %% or, unless it is a keyword (PRINT#,
  ;; EOF#), after a byte & or float # suffix
  (cond ((eq? c #\$) (+ j 1))
        ((and (eq? c #\%) (eq? next #\%)) (+ j 2))
        ((eq? c #\%) (+ j 1))
        ((and (member c (list #\& #\#))
              (not (member (bbc-normalize-name (substring text start j)) bbc-keywords)))
         (+ j 1))
        (else j)))

(define (bbc-hex-constant digits)
  ;; &FFFFFFFF is -1: up to 8 hex digits make a 32-bit signed number
  (let [n (string->number digits 16)]
    (if (<= (length digits) 8) (bits:signed-field n 32) n)))

;;; --- Shifts and hex ---

(define (bbc-shl a b) (bits:arithmetic-shift (bbc-whole a) (bbc-whole b)))
(define (bbc-shr a b) (bits:arithmetic-shift (bbc-whole a) (- (bbc-whole b))))

(define (bbc-width n)
  ;; 32 bits for a number that fits them, signed or not, else 64
  (if (and (>= n bbc-int32-min) (<= n (- (expt 2 32) 1))) 32 64))

(define (bbc-lsr a b)
  (let [n (bbc-whole a)]
    (bits:logical-shift-right n (bbc-whole b) (bbc-width n))))

(define bbc-shift-ops '(("<<" bbc-shl) (">>" bbc-shr) (">>>" bbc-lsr)))

(define (bbc-hex x)
  ;; STR$~ and PRINT ~: upper-case hex, a negative number in 32 (or 64) bits
  (let [n (bbc-whole x)]
    (upcase (number->string (if (< n 0) (bits:bit-field n 0 (bbc-width n)) n) 16))))

(define (bbc-print-hex x justify)
  (let [text (bbc-hex x)]
    (bbc-write (if justify (text/rjust bbc-zone-width) text))))

;; STR$~x is the hex text of x
(define bbc-primary-before-num bbc-p-primary)
(define (bbc-p-primary)
  (if (and (bbc-at? :kw "STR$") (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :op "~"))
      (begin (bbc-advance!) (bbc-advance!)
             (bbc-e (list 'bbc-hex (bbc-value (bbc-p-unary))) :str))
      (bbc-primary-before-num)))
