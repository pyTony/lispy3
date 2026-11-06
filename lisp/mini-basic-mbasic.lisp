;;; mini-basic-mbasic.lisp - MBASIC 5.21 operators and functions for the
;;; MBASIC print style (bbc-set-print-style! :mbasic)
;;;
;;;   PRINT 17 \ 5, 17 MOD 5             ; 3 and 2: integer division and remainder
;;;   PRINT 5 XOR 3, 5 EQV 3, 5 IMP 3    ; 6, -7 and -5: bitwise, as AND and OR
;;;   PRINT FIX(-2.7), CINT(-2.7)        ; -2 (toward zero) and -3 (nearest)
;;;   PRINT HEX$(255), OCT$(8)           ; FF and 10
;;;   A$ = "A" + SPACE$(5) + "B"         ; five spaces
;;;   A$ = STR$(42) : A% = 10.7          ; " 42" with its sign space; A% is 11
;;;   B! = CSNG(A#) : D# = CDBL(C!)      ; single and double precision
;;;   RANDOMIZE 42 : PRINT RND           ; the same RND sequence for the same seed
;;;   DEF FN SQUARE(X) = X * X           ; FN with a space, as MBASIC writes it
;;;   PRINT FN SQUARE(5)
;;;
;;; The operators bind as in MBASIC, tightest first: ^, unary -, * /, \, MOD,
;;; + -, comparisons, NOT, AND, OR, XOR, EQV, IMP. So -2^2 is -4 and
;;; 10 + 7 MOD 3 is 11. \ and MOD round their operands to whole numbers
;;; first, as CINT does. RND on its own is RND(1), a number from 0 to 1, and
;;; RANDOMIZE without a seed takes one from the clock. ' starts a comment and
;;; Ctrl-Z ends the text, as in a CP/M file (the tokenizer in mini-basic.lisp).
;;;
;;; BBC style is unchanged: these words stay names there, and \ is an error.
;;;
;;; Loaded after mini-basic-more.lisp; it wraps the reader's hooks.

;;; --- Run-time support ---

(define (bbc-mbasic?) (eq? bbc-number-print-style :mbasic))

(define (bbc-round-in x low high)
  ;; The nearest whole number, halves away from zero; Overflow outside low..high
  (let [n (if (< x 0) (- (floor (+ (- x) 0.5))) (floor (+ x 0.5)))]
    (if (or (< n low) (> n high)) (error "Overflow"))
    n))

(define (bbc-cint x) (bbc-round-in x -32768 32767))

(define (bbc-fix x) (trunc x))

(define (bbc-mbasic-whole x)
  ;; A whole-number operand: exact numbers as they are, others as CINT rounds
  (if (and (exact? x) (integer? x)) x (bbc-cint x)))

(define (bbc-intdiv a b)
  (let [y (bbc-mbasic-whole b)]
    (if (= y 0) (error "Division by zero"))
    (quotient (bbc-mbasic-whole a) y)))

(define (bbc-mbasic-mod a b)
  (let [y (bbc-mbasic-whole b)]
    (if (= y 0) (error "Division by zero"))
    (remainder (bbc-mbasic-whole a) y)))

(define (bbc-eqv a b) (bbc-not (bbc-eor a b)))
(define (bbc-imp a b) (bbc-or (bbc-not a) b))

(define (bbc-word16 x)
  ;; HEX$ and OCT$ take -32768..65535; a negative number is its 16-bit pattern
  (let [n (bbc-round-in x -32768 65535)]
    (if (< n 0) (+ n 65536) n)))

(define (bbc-hex$ x) (upcase (number->string (bbc-word16 x) 16)))
(define (bbc-oct$ x) (number->string (bbc-word16 x) 8))

(define (bbc-space$ n)
  (let [k (trunc n)]
    (if (or (< k 0) (> k 255)) (error "Illegal function call"))
    (bbc-string-repeat k " ")))

(define (bbc-mbasic-str$ x)
  ;; MBASIC's STR$ keeps the space a positive number prints with
  (let [text (bbc-str x)]
    (if (and (number? x) (>= x 0)) (str " " text) text)))

;; A% = 10.7 gives 11: MBASIC rounds into an integer variable as CINT does
(define bbc-typed-value-before-mbasic bbc-typed-value)
(define (bbc-typed-value var exp)
  (let [name (symbol->string var)]
    (if (and (bbc-mbasic?) (bbc-name-suffix? name "%") (not (bbc-name-suffix? name "%%")))
        `(bbc-cint ,exp)
        (bbc-typed-value-before-mbasic var exp))))

(define (bbc-randomize &optional (seed :clock))
  ;; The same seed gives the same RND sequence again
  (let [n (if (eq? seed :clock) (get-internal-real-time) (trunc seed))]
    (set! bbc-rnd-state (modulo n 4294967296))
    #f))

;;; --- Reader ---

;; Words that are keywords only in the MBASIC print style
(define bbc-mbasic-keywords
  '("XOR" "EQV" "IMP" "FIX" "CINT" "CSNG" "CDBL" "HEX$" "OCT$" "SPACE$" "RANDOMIZE"))

(set! bbc-functions (append bbc-functions '(("FIX" bbc-fix 1 1 :num) ("CINT" bbc-cint 1 1 :num)
                                            ("CSNG" bbc-single 1 1 :num) ("CDBL" float 1 1 :num)
                                            ("HEX$" bbc-hex$ 1 1 :str) ("OCT$" bbc-oct$ 1 1 :str)
                                            ("SPACE$" bbc-space$ 1 1 :str))))

(define (bbc-mbasic-tokens toks)
  ;; MBASIC keywords from names, and FN NAME (with a space) as one FN token
  (let [out (list) rest toks]
    (while (not (null? rest))
      (let [tok (car rest)]
        (cond ((and (eq? (car tok) :id) (equal? (nth tok 1) "FN")
                    (not (null? (cdr rest))) (member (car (car (cdr rest))) (quote (:id :kw))))
               (bbc-push! out (cons :fn (cdr (car (cdr rest)))))
               (set! rest (cdr rest)))
              ((and (eq? (car tok) :id) (member (nth tok 1) bbc-mbasic-keywords))
               (bbc-push! out (cons :kw (cdr tok))))
              (else (bbc-push! out tok))))
      (set! rest (cdr rest)))
    out))

(define bbc-tokenize-before-mbasic bbc-tokenize)
(define (bbc-tokenize text)
  (let [toks (bbc-tokenize-before-mbasic text)]
    (if (eq? bbc-number-print-style :mbasic) (bbc-mbasic-tokens toks) toks)))

;; Logical operators: OR, then XOR, EQV and IMP, each binding more loosely
(define bbc-p-or-before-mbasic bbc-p-or)

(define (bbc-p-xor)
  (let loop ((left (bbc-p-or-before-mbasic)))
    (if (bbc-accept! :kw "XOR")
        (loop (bbc-logic 'eor left (bbc-p-or-before-mbasic)))
        left)))

(define (bbc-p-eqv)
  (let loop ((left (bbc-p-xor)))
    (if (bbc-accept! :kw "EQV")
        (loop (bbc-num (list 'bbc-eqv (bbc-value left) (bbc-value (bbc-p-xor)))))
        left)))

(define (bbc-p-imp)
  (let loop ((left (bbc-p-eqv)))
    (if (bbc-accept! :kw "IMP")
        (loop (bbc-num (list 'bbc-imp (bbc-value left) (bbc-value (bbc-p-eqv)))))
        left)))

(define (bbc-p-or)
  (if (bbc-mbasic?) (bbc-p-imp) (bbc-p-or-before-mbasic)))

;; NOT binds more loosely than comparisons: NOT A = B is NOT (A = B)
(define bbc-p-and-before-mbasic bbc-p-and)

(define (bbc-p-mbasic-not)
  (if (bbc-accept! :kw "NOT")
      (let [e (bbc-p-mbasic-not)]
        (if (eq? (bbc-type e) :bool)
            (bbc-e (list 'not (car e)) :bool)
            (bbc-num (list 'bbc-not (bbc-value e)))))
      (bbc-p-compare)))

(define (bbc-p-and)
  (if (bbc-mbasic?)
      (let loop ((left (bbc-p-mbasic-not)))
        (if (bbc-accept! :kw "AND")
            (loop (bbc-logic 'and left (bbc-p-mbasic-not)))
            left))
      (bbc-p-and-before-mbasic)))

;; Arithmetic: MOD, then \, then * and /, then unary minus, then ^
(define bbc-p-mul-before-mbasic bbc-p-mul)

(define (bbc-p-mbasic-negate)
  (cond ((bbc-accept! :op "-")
         (let [e (bbc-p-mbasic-negate)]
           (if (number? (car e)) (bbc-num (- (car e))) (bbc-num (list '- (bbc-value e))))))
        ((bbc-accept! :op "+") (bbc-p-mbasic-negate))
        (else (bbc-p-power))))

(define (bbc-p-mbasic-times)
  (let loop ((left (bbc-p-mbasic-negate)))
    (cond ((bbc-accept! :op "*")
           (loop (bbc-num (list '* (bbc-value left) (bbc-value (bbc-p-mbasic-negate))))))
          ((bbc-accept! :op "/")
           (loop (bbc-num (list '/ (list 'float (bbc-value left)) (bbc-value (bbc-p-mbasic-negate))))))
          (else left))))

(define (bbc-p-mbasic-intdiv)
  (let loop ((left (bbc-p-mbasic-times)))
    (if (bbc-accept! :op "\\")
        (loop (bbc-num (list 'bbc-intdiv (bbc-value left) (bbc-value (bbc-p-mbasic-times)))))
        left)))

(define (bbc-p-mul)
  (if (bbc-mbasic?)
      (let loop ((left (bbc-p-mbasic-intdiv)))
        (if (bbc-accept! :kw "MOD")
            (loop (bbc-num (list 'bbc-mbasic-mod (bbc-value left) (bbc-value (bbc-p-mbasic-intdiv)))))
            left))
      (bbc-p-mul-before-mbasic)))

(define (bbc-mbasic-primary)
  (let [next (nth bbc-toks (+ bbc-pos 1))]
    (cond ((not (bbc-mbasic?)) #f)
          ;; RND on its own is RND(1) in MBASIC
          ((and (bbc-at? :kw "RND") (not (bbc-tok? next :op "(")))
           (bbc-advance!) (bbc-num '(bbc-rnd 1)))
          ((and (bbc-at? :kw "STR$") (not (bbc-tok? next :op "~")))
           (bbc-advance!) (bbc-e (list 'bbc-mbasic-str$ (bbc-value (bbc-p-unary))) :str))
          (else #f))))

(define bbc-primary-before-mbasic bbc-p-primary)
(define (bbc-p-primary)
  (or (bbc-mbasic-primary) (bbc-primary-before-mbasic)))

(define (bbc-mbasic-statement)
  (if (bbc-accept! :kw "RANDOMIZE")
      (if (bbc-at-stmt-end?)
          (list 'bbc-randomize)
          (list 'bbc-randomize (bbc-value (bbc-p-expr))))
      #f))

(define bbc-statement-before-mbasic bbc-ext-statement)
(define (bbc-ext-statement)
  (or (bbc-mbasic-statement) (bbc-statement-before-mbasic)))

;; RANDOMIZE changes what RND gives
(define bbc-pure-fn-before-mbasic bbc-pure-fn?)
(define (bbc-pure-fn? def vars)
  (and (not (bbc-uses? '(bbc-randomize) (cdr (cdr def))))
       (bbc-pure-fn-before-mbasic def vars)))
