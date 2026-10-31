;;; mini-basic-more.lisp - statements and functions BBC BASIC and MBASIC share
;;;
;;;   SWAP a, b : SWAP a$(i), a$(j)          ; exchange two variables or elements
;;;   MID$(a$, 2, 3) = "xyz"                 ; overwrite part of a string in place
;;;   a *= 2 : a /= 4                        ; besides += and -=
;;;   PRINT STRING$(3, "ab"), EVAL("2*PI")   ; ababab and 6.28318531
;;;   PRINT STRING$(3, 42)                   ; ***: a number is a character code
;;;   k = GET : k$ = GET$ : k = INKEY(50)    ; keys; INKEY waits up to 50 cs
;;;   k$ = INKEY$(0) : k$ = INKEY$           ; "" when no key is waiting
;;;   PRINT POS, VPOS                        ; text column and row
;;;   CLEAR : QUIT                           ; forget variables; stop like END
;;;
;;; GET and INKEY read keys typed into an open MODE window. Without a window
;;; they read the typed input line by line: GET waits for a line and then gives
;;; its characters one at a time, ending with 13 (Return), and INKEY gives
;;; those waiting characters, else -1 when its time is up. INKEY with a
;;; negative number (scan one key) gives 0, FALSE: keys are not scanned.
;;;
;;; In the MBASIC print style, a BBC keyword that a statement assigns to, such
;;; as COUNT = 0 or FOR PI = ..., is a variable name in the whole program, as in
;;; MBASIC, which has no COUNT or PI. BBC style keeps rejecting such names.
;;;
;;; Loaded after mini-basic-error.lisp; it wraps the reader's hooks.

;;; --- Run-time support ---

(define (bbc-string-repeat n s)
  ;; STRING$(5, "ab"); MBASIC's STRING$(5, 42) repeats the character with code 42
  (let [k (trunc n)
        text (if (number? s) (bbc-chr s) s)]
    (if (< k 0) (error "STRING$: the count must not be negative"))
    (str/join (map (lambda (_) text) (range k)))))

(define (bbc-mid-replace s p new & n)
  ;; MID$(s$, p, n) = new$: overwrite from position p, never changing the length
  (let [l (length s)
        start (max 0 (min l (- (trunc p) 1)))
        k (min (length new) (- l start))]
    (if (not (null? n)) (set! k (max 0 (min k (trunc (car n))))))
    (string-append (substring s 0 start) (substring new 0 k) (substring s (+ start k) l))))

;; Keys typed at the console but not read yet, oldest first
(define bbc-typed-keys (list))

(define (bbc-key-from-window)
  ;; A key code from the MODE window, -1 for none yet, -2 without a window
  (if (bbc-bound? 'graphics-key) (graphics-key) -2))

(define (bbc-take-typed-key)
  (let [code (car bbc-typed-keys)]
    (set! bbc-typed-keys (cdr bbc-typed-keys))
    code))

(define (bbc-read-typed-line!)
  ;; Wait for a typed line; its characters and Return become keys
  (let [line (read-line)]
    (set! bbc-col 0)
    (set! bbc-typed-keys (append bbc-typed-keys
                                 (map bbc-asc (map str (seq (str line))))
                                 (list 13)))))

(define (bbc-get)
  (let [code -1]
    (while (< code 0)
      (if (not (null? bbc-typed-keys))
          (set! code (bbc-take-typed-key))
          (let [key (bbc-key-from-window)]
            (cond ((>= key 0) (set! code key))
                  ((= key -1) (sleep 0.01))
                  (else (bbc-read-typed-line!))))))
    code))

(define (bbc-inkey centiseconds)
  (let [t (trunc centiseconds)]
    (if (< t 0)
        0
        (let [deadline (+ (get-internal-real-time) (* t 10))
              code -1
              waiting #t]
          (while waiting
            (if (not (null? bbc-typed-keys))
                (set! code (bbc-take-typed-key))
                (let [key (bbc-key-from-window)]
                  (if (>= key 0) (set! code key))))
            (if (or (>= code 0) (>= (get-internal-real-time) deadline))
                (set! waiting #f)
                (sleep 0.01)))
          code))))

(define (bbc-inkey$ centiseconds)
  (let [code (bbc-inkey centiseconds)]
    (if (< code 0) "" (bbc-chr code))))

(define (bbc-eval text)
  ;; EVAL("expression"): read the text as an expression now and work it out
  (let [saved-toks bbc-toks saved-pos bbc-pos]
    (try
      (begin
        ;; After =, so that a leading number is not read as a line number
        (set! bbc-toks (bbc-tokenize (str "=" text)))
        (set! bbc-pos 1)
        (let [e (bbc-p-expr)]
          (if (not (bbc-at-line-end?)) (bbc-fail "unexpected text after the EVAL expression"))
          (set! bbc-toks saved-toks)
          (set! bbc-pos saved-pos)
          (eval (bbc-value e))))
      (catch err
        (set! bbc-toks saved-toks)
        (set! bbc-pos saved-pos)
        (error err)))))

;; bbc-program sets this when the program uses CLEAR
(define bbc-clear-variables (lambda () #f))

(define-macro (CLEAR) '(bbc-clear-variables))

;;; --- Reader ---

(set! bbc-keywords (append bbc-keywords '("SWAP" "STRING$" "EVAL" "GET" "INKEY" "INKEY$"
                                          "POS" "VPOS" "CLEAR" "QUIT")))

(set! bbc-functions (append bbc-functions '(("STRING$" bbc-string-repeat 2 2 :str)
                                            ("EVAL" bbc-eval 1 1 :num))))

(define (bbc-store-code target value)
  ;; Code giving the variable or array element target (from bbc-p-target) value
  (let [lhs (car target) var (nth target 2)]
    (cond ((and (pair? lhs) (eq? (car lhs) 'AREF))
           (append (list 'ASET! var value) (cdr (cdr lhs))))
          ((and (pair? lhs) (eq? (car lhs) 'WHOLE))
           (bbc-fail "expected a variable or an array element, not a whole array"))
          (else (list 'LET var value)))))

(define (bbc-p-swap)
  (let [a (bbc-p-target)]
    (bbc-expect! :op "," ", between the two variables of SWAP")
    (let [b (bbc-p-target)
          tmp (gensym "swap")]
      (if (not (eq? (bbc-string-name? (nth a 1)) (bbc-string-name? (nth b 1))))
          (bbc-fail "SWAP needs two strings or two numbers"))
      `(let ((,tmp ,(car a)))
         ,(bbc-store-code a (car b))
         ,(bbc-store-code b tmp)))))

(define (bbc-p-mid-assign)
  (bbc-expect! :op "(" "( after MID$")
  (let [target (bbc-p-target)]
    (if (not (bbc-string-name? (nth target 1))) (bbc-fail "MID$ = needs a string variable"))
    (bbc-expect! :op "," ", after the MID$ variable")
    (let [p (bbc-value (bbc-p-expr))
          n (if (bbc-accept! :op ",") (list (bbc-value (bbc-p-expr))) (list))]
      (bbc-expect! :op ")" ")")
      (bbc-expect! :op "=" "= after MID$(...)")
      (bbc-store-code target (append (list 'bbc-mid-replace (car target) p (bbc-value (bbc-p-expr))) n)))))

(define (bbc-skip-to-stmt-end)
  (while (not (bbc-at-stmt-end?)) (bbc-advance!)))

(define (bbc-more-statement)
  (cond ((bbc-accept! :kw "SWAP") (bbc-p-swap))
        ((and (bbc-at? :kw "MID$") (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :op "("))
         (bbc-advance!) (bbc-p-mid-assign))
        ((bbc-accept! :kw "CLEAR")
         ;; MBASIC's CLEAR ,n sets memory sizes, which Lispy does not need
         (bbc-skip-to-stmt-end) (list 'CLEAR))
        ((bbc-accept! :kw "QUIT") (bbc-skip-to-stmt-end) (list 'END))
        (else #f)))

(define (bbc-p-optional-arg default)
  ;; (n) after INKEY$, or default when MBASIC's INKEY$ has none
  (if (bbc-at? :op "(")
      (car (bbc-p-args))
      default))

(define (bbc-more-primary)
  (cond ((bbc-accept! :kw "GET") (bbc-num '(bbc-get)))
        ((and (bbc-at? :kw "GET$") (not (bbc-io-hash? "GET$")))
         (bbc-advance!) (bbc-e '(bbc-chr (bbc-get)) :str))
        ((bbc-accept! :kw "INKEY") (bbc-num (list 'bbc-inkey (bbc-value (bbc-p-unary)))))
        ((bbc-accept! :kw "INKEY$") (bbc-e (list 'bbc-inkey$ (bbc-p-optional-arg 0)) :str))
        ((bbc-accept! :kw "POS") (bbc-p-optional-arg 0) (bbc-num 'bbc-col))
        ((bbc-accept! :kw "VPOS") (bbc-num 'bbc-row))
        (else #f)))

(define bbc-statement-before-more bbc-ext-statement)
(define (bbc-ext-statement)
  (or (bbc-more-statement) (bbc-statement-before-more)))

(define bbc-primary-before-more bbc-p-primary)
(define (bbc-p-primary)
  (or (bbc-more-primary) (bbc-primary-before-more)))

;; Keys, EVAL and CLEAR give different results for the same arguments
(define bbc-pure-fn-before-more bbc-pure-fn?)
(define (bbc-pure-fn? def vars)
  (and (not (bbc-uses? '(bbc-get bbc-inkey bbc-inkey$ bbc-eval CLEAR) (cdr (cdr def))))
       (bbc-pure-fn-before-more def vars)))

;;; --- MBASIC: assigned keywords are names ---

(define (bbc-assigned-keyword? toks i)
  ;; Is token i a keyword (not TIME) starting an assignment: COUNT = or FOR PI =?
  (let [tok (nth toks i)
        before (if (> i 0) (nth toks (- i 1)) (list :eol #f))]
    (and (eq? (car tok) :kw)
         (not (equal? (nth tok 1) "TIME"))
         (bbc-tok? (nth toks (+ i 1)) :op "=")
         (or (member (car before) '(:eol :colon :line))
             (bbc-any? (lambda (word) (bbc-tok? before :kw word)) '("LET" "FOR" "THEN" "ELSE"))))))

(define (bbc-free-assigned-keywords toks)
  (let [names (list)]
    (dotimes [i (- (length toks) 1)]
      (if (bbc-assigned-keyword? toks i)
          (bbc-push! names (nth (nth toks i) 1))))
    (if (null? names)
        toks
        (map (lambda (tok)
               (if (and (eq? (car tok) :kw) (member (nth tok 1) names))
                   (cons :id (cdr tok))
                   tok))
             toks))))

(define bbc-tokenize-before-more bbc-tokenize)
(define (bbc-tokenize text)
  (let [toks (bbc-tokenize-before-more text)]
    (if (eq? bbc-number-print-style :mbasic) (bbc-free-assigned-keywords toks) toks)))
