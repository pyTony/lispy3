;;; mini-basic.lisp - structured BBC BASIC statements as lispy3 macros
;;;
;;; Run BBC BASIC text with (bbc-run """...""") or (bbc-load "prog.bas"); the
;;; reader at the end of this file turns the text into the statements below.
;;;
;;; Each BBC statement is an UPPERCASE macro that expands into plain lispy3 code,
;;; so a BASIC program written as Lisp forms runs at Lisp speed:
;;;
;;;   (bbc-program
;;;     (DEF-FN (fact n)
;;;       (IF (< n 2) (FN= 1) ELSE (FN= (* n (FN fact (- n 1))))))
;;;     (FOR i 1 5
;;;       (PRINT "fact(" :semi i :semi ") = " :semi (FN fact i))))
;;;
;;; Statements:
;;;   (LET var exp)                    assignment; var% keeps whole numbers, var$ is a string
;;;   (PRINT item ...)                 items, with separators :semi (;) :comma (,) :nl (')
;;;                                    and (TAB n), (TAB x y), (SPC n) items
;;;   (IF test stmt ... ELSE stmt ...) multi-line IF ... ELSE ... ENDIF
;;;   (FOR var from to [STEP s] stmt ...)      FOR ... NEXT, always runs at least once
;;;   (REPEAT stmt ... UNTIL test)     REPEAT ... UNTIL
;;;   (WHILE test stmt ...)            WHILE ... ENDWHILE
;;;   (CASE exp (WHEN (v ...) stmt ...) ... (OTHERWISE stmt ...))
;;;   (DEF-PROC (name parm ...) stmt ...)  and (PROC name arg ...) to call it
;;;   (DEF-FN (name parm ...) stmt ... (FN= exp))  and (FN name arg ...) to call it
;;;   (LOCAL var ...), (ENDPROC), (FN= exp), (EXIT-FOR), (EXIT-REPEAT), (EXIT-WHILE), (END)
;;;
;;; As in BBC BASIC, PROC and FN parameters and LOCAL variables are dynamically
;;; scoped: the old values are saved on entry and put back on exit. bbc-program
;;; defines every variable the program assigns (0, or "" for var$) before it runs,
;;; and lifts DEF-PROC and DEF-FN to the front, so they may come after the main part.
;;; Tests are BBC truth values: 0 and #f are false, anything else (TRUE is -1) is true.

;;; --- Run-time support ---

(define TRUE -1)
(define FALSE 0)

(define (bbc-true? x)
  (not (or (eq? x #f) (eq? x 0) (null? x))))

(define (bbc-int x)
  (trunc x))

;; Values passed out of an FN by (FN= exp) before the early return
(define bbc-fn-value 0)

;; The output column, for :comma zones, TAB and PRINT's right-justified numbers
(define bbc-col 0)
(define bbc-zone-width 10)
(define bbc-blank "")

(define (bbc-write text)
  (format #t "~a" text)
  (let [s (str text)
        nl (s/rfind "\n")]
    (if (< nl 0)
        (set! bbc-col (+ bbc-col (length s)))
        (set! bbc-col (- (length s) nl 1)))))

(define (bbc-newline)
  (format #t "~%")
  (set! bbc-col 0))

(define (bbc-spaces n)
  (if (> n 0) (bbc-write (bbc-blank/ljust n))))

(define (bbc-zone)
  (bbc-spaces (mod (- bbc-zone-width (mod bbc-col bbc-zone-width)) bbc-zone-width)))

(define (bbc-tab n)
  (if (> bbc-col n) (bbc-newline))
  (bbc-spaces (- n bbc-col)))

(define (bbc-tab-xy x y)
  ;; Without a screen, TAB(x,y) can only move along the line
  (bbc-tab x))

(define bbc-g9 "{:.9G}")

(define (bbc-str x)
  ;; A number as BBC BASIC prints it with the default @%: up to 9 significant digits
  (cond ((boolean? x) (if x "-1" "0"))
        ((and (exact? x) (integer? x)) (number->string x))
        (else
         (let [text (bbc-g9/format (float x))]
           (if (member #\E (seq text))
               (let [parts (split text "E")]
                 (str (car parts) "E" (string->number (nth parts 1))))
               text)))))

(define (bbc-print-value v justify)
  (if (string? v)
      (bbc-write v)
      (let [text (bbc-str v)]
        (bbc-write (if justify (text/rjust bbc-zone-width) text)))))

;;; --- Helpers the macros use while they expand ---

(define (bbc-second lst) (car (cdr lst)))

(define (bbc-split forms marker)
  ;; (before after) around the first marker symbol; after is #f without one
  (let loop ((rest forms) (acc '()))
    (cond ((null? rest) (list (reverse acc) #f))
          ((eq? (car rest) marker) (list (reverse acc) (cdr rest)))
          (else (loop (cdr rest) (cons (car rest) acc))))))

(define (bbc-any? f lst)
  (cond ((null? lst) #f)
        ((f (car lst)) #t)
        (else (bbc-any? f (cdr lst)))))

(define (bbc-uses? heads x)
  ;; Does code x contain a form starting with one of the heads?
  (and (pair? x) (list? x)
       (not (eq? (car x) 'quote))
       (or (and (member (car x) heads) #t)
           (bbc-any? (lambda (e) (bbc-uses? heads e)) x))))

(define (bbc-suffix? var ch)
  (let [s (symbol->string var)]
    (and (> (length s) 0) (equal? (string-ref s (- (length s) 1)) ch))))

(define (bbc-default var)
  (if (bbc-suffix? var #\$) "" 0))

(define (bbc-adjoin xs set)
  (cond ((null? xs) set)
        ((member (car xs) set) (bbc-adjoin (cdr xs) set))
        (else (bbc-adjoin (cdr xs) (append set (list (car xs)))))))

(define (bbc-collect heads pick x found)
  ;; Gather (pick form) from every form in x whose head is in heads
  (if (and (pair? x) (list? x) (not (eq? (car x) 'quote)))
      (let [found (if (member (car x) heads) (bbc-adjoin (pick x) found) found)]
        (reduce (lambda (acc e) (bbc-collect heads pick e acc)) found x))
      found))

(define (bbc-assigned-vars stmts)
  ;; Every variable the statements give a value to
  (bbc-collect '(LET FOR LOCAL DEF-PROC DEF-FN)
               (lambda (form)
                 (cond ((member (car form) '(LET FOR)) (list (bbc-second form)))
                       ((eq? (car form) 'LOCAL) (cdr form))
                       (else (cdr (bbc-second form)))))
               stmts '()))

(define (bbc-def? form)
  (and (pair? form) (list? form) (member (car form) '(DEF-PROC DEF-FN)) #t))

(define bbc-boolean-heads '(< > <= >= = not equal? eq? null? bbc-true?
                            even? odd? zero? positive? negative?))

(define (bbc-test test)
  ;; Code for a BBC test; Lisp comparisons already give #t or #f
  (if (and (pair? test) (list? test) (member (car test) bbc-boolean-heads))
      test
      (list 'bbc-true? test)))

(define (bbc-catch tag body handler)
  ;; Run body; a (error tag) inside it runs handler instead, other errors go on
  (let [e (gensym "err")]
    `(try ,body
          (catch ,e (if (equal? ,e ,tag) ,handler (error ,e))))))

(define (bbc-escape stmt tag)
  `(begin ,stmt (error ,tag)))

;;; --- Statements ---

(define-macro (LET var exp)
  (if (bbc-suffix? var #\%)
      `(set! ,var (bbc-int ,exp))
      `(set! ,var ,exp)))

(define (bbc-print-code items justify)
  ;; :semi stops right-justifying numbers, :comma starts it again
  (if (null? items)
      (list '(bbc-newline))
      (let [item (car items)
            more (cdr items)]
        (cond ((eq? item :semi)
               (if (null? more) '() (bbc-print-code more #f)))
              ((eq? item :comma)
               (cons '(bbc-zone) (if (null? more) '() (bbc-print-code more #t))))
              ((eq? item :nl)
               (cons '(bbc-newline) (bbc-print-code more justify)))
              ((and (pair? item) (list? item) (eq? (car item) 'TAB))
               (cons (if (null? (cdr (cdr item)))
                         `(bbc-tab ,(bbc-second item))
                         `(bbc-tab-xy ,@(cdr item)))
                     (bbc-print-code more justify)))
              ((and (pair? item) (list? item) (eq? (car item) 'SPC))
               (cons `(bbc-spaces ,(bbc-second item)) (bbc-print-code more justify)))
              (else
               (cons `(bbc-print-value ,item ,justify) (bbc-print-code more justify)))))))

(define-macro (PRINT & items)
  `(begin ,@(bbc-print-code items #t)))

(define-macro (IF test & body)
  (let [parts (bbc-split body 'ELSE)
        then-part `(begin ,@(car parts))]
    (if (bbc-second parts)
        `(if ,(bbc-test test) ,then-part (begin ,@(bbc-second parts)))
        `(if ,(bbc-test test) ,then-part))))

(define-macro (FOR var from to & more)
  (let [has-step (and (pair? more) (eq? (car more) 'STEP))
        step (if has-step (bbc-second more) 1)
        body (if has-step (cdr (cdr more)) more)
        lim (gensym "lim")
        st (gensym "step")
        next (if (and (bbc-suffix? var #\%) (not (and (number? step) (integer? step))))
                 `(LET ,var (+ ,var ,st))
                 `(set! ,var (+ ,var ,st)))
        more? (cond ((not (number? step)) `(if (< ,st 0) (>= ,var ,lim) (<= ,var ,lim)))
                    ((< step 0) `(>= ,var ,lim))
                    (else `(<= ,var ,lim)))
        loop `(let ((,lim ,to) (,st ,step))
                (while (begin ,@body ,next ,more?)))]
    `(begin
       (LET ,var ,from)
       ,(if (bbc-uses? '(EXIT-FOR) body) (bbc-catch "bbc:exit-for" loop #f) loop))))

(define-macro (REPEAT & body)
  (let [parts (bbc-split body 'UNTIL)
        loop `(while (begin ,@(car parts) (not ,(bbc-test (car (bbc-second parts))))))]
    (if (bbc-uses? '(EXIT-REPEAT) body) (bbc-catch "bbc:exit-repeat" loop #f) loop)))

(define-macro (WHILE test & body)
  (let [loop `(while ,(bbc-test test) ,@body)]
    (if (bbc-uses? '(EXIT-WHILE) body) (bbc-catch "bbc:exit-while" loop #f) loop)))

(define-macro (CASE exp & clauses)
  (let [v (gensym "case")]
    `(let ((,v ,exp))
       (cond ,@(map (lambda (clause)
                      (if (eq? (car clause) 'OTHERWISE)
                          `(else #f ,@(cdr clause))
                          `((or ,@(map (lambda (w) `(= ,v ,w)) (bbc-second clause)))
                            #f ,@(cdr (cdr clause)))))
                    clauses)))))

(define-macro (EXIT-FOR) '(error "bbc:exit-for"))
(define-macro (EXIT-REPEAT) '(error "bbc:exit-repeat"))
(define-macro (EXIT-WHILE) '(error "bbc:exit-while"))
(define-macro (END) '(error "bbc:end"))
(define-macro (ENDPROC) '(error "bbc:endproc"))
(define-macro (FN= exp) (bbc-escape `(set! bbc-fn-value ,exp) "bbc:return"))

(define-macro (LOCAL & vars)
  `(begin ,@(map (lambda (var) `(set! ,var ,(bbc-default var))) vars)))

(define (bbc-def-name kind name)
  (string->symbol (str kind "-" name)))

(define-macro (PROC name & args) `(,(bbc-def-name 'PROC name) ,@args))
(define-macro (FN name & args) `(,(bbc-def-name 'FN name) ,@args))

(define (bbc-tail stmts)
  ;; An FN's last statement gives its value: (FN= x) in tail position is just x,
  ;; also at the end of each branch of an IF or CASE there
  (if (null? stmts)
      stmts
      (let [rev (reverse stmts)]
        (reverse (cons (bbc-tail-stmt (car rev)) (cdr rev))))))

(define (bbc-tail-stmt stmt)
  (cond ((not (and (pair? stmt) (list? stmt))) stmt)
        ((eq? (car stmt) 'FN=) (bbc-second stmt))
        ((eq? (car stmt) 'ENDPROC) #f)
        ((eq? (car stmt) 'IF)
         (let [parts (bbc-split (cdr (cdr stmt)) 'ELSE)]
           (append (list 'IF (bbc-second stmt))
                   (bbc-tail (car parts))
                   (if (bbc-second parts) (cons 'ELSE (bbc-tail (bbc-second parts))) '()))))
        ((eq? (car stmt) 'CASE)
         (append (list 'CASE (bbc-second stmt))
                 (map (lambda (clause)
                        (if (eq? (car clause) 'OTHERWISE)
                            (cons 'OTHERWISE (bbc-tail (cdr clause)))
                            (append (list 'WHEN (bbc-second clause)) (bbc-tail (cdr (cdr clause))))))
                      (cdr (cdr stmt)))))
        (else stmt)))

(define (bbc-def kind head body memo)
  (let [name (car head)
        parms (cdr head)
        args (map (lambda (p) (gensym "arg")) parms)
        locals (bbc-collect '(LOCAL) cdr body '())
        saved (bbc-adjoin locals parms)
        saves (map (lambda (v) (gensym "saved")) saved)
        result (gensym "result")
        tail-body (bbc-tail body)
        tag (if (eq? kind 'FN) "bbc:return" "bbc:endproc")
        run (if (bbc-uses? '(FN= ENDPROC) tail-body)
                (bbc-catch tag `(begin #f ,@tail-body) 'bbc-fn-value)
                `(begin #f ,@tail-body))
        fn `(lambda ,args
              (let ,(map list saves saved)
                ,@(map (lambda (p a) `(set! ,p ,a)) parms args)
                (let ((,result ,run))
                  ,@(map (lambda (v s) `(set! ,v ,s)) saved saves)
                  ,result)))]
    `(define ,(bbc-def-name kind name) ,(if memo `(memoize ,fn) fn))))

(define-macro (DEF-PROC head & body) (bbc-def 'PROC head body #f))
(define-macro (DEF-FN head & body) (bbc-def 'FN head body #f))
;; A pure FN remembers its results, as mini_basic does: FNfib(30) runs once per n
(define-macro (DEF-MEMO-FN head & body) (bbc-def 'FN head body #t))

(define (bbc-symbols x found)
  ;; Every symbol in code x
  (cond ((symbol? x) (bbc-adjoin (list x) found))
        ((and (pair? x) (list? x) (not (eq? (car x) 'quote)))
         (reduce (lambda (acc e) (bbc-symbols e acc)) found x))
        (else found)))

(define (bbc-pure-fn? def vars)
  ;; A DEF-FN that reads no program variable but its own parameters and LOCALs,
  ;; prints nothing and calls no PROC and no other FN: the same arguments
  ;; always give the same result
  (let [head (bbc-second def)
        body (cdr (cdr def))
        own (bbc-adjoin (bbc-collect '(LOCAL) cdr body '()) (cdr head))
        calls (bbc-collect '(FN) (lambda (f) (list (bbc-second f))) body '())]
    (and (eq? (car def) 'DEF-FN)
         (not (bbc-uses? '(PRINT PROC END) body))
         (not (bbc-any? (lambda (v) (and (member v vars) (not (member v own))))
                        (bbc-symbols body '())))
         (not (bbc-any? (lambda (f) (not (eq? f (car head)))) calls)))))

;;; --- A whole program ---

(define-macro (bbc-program & stmts)
  (let [vars (bbc-assigned-vars stmts)
        defs (map (lambda (d) (if (bbc-pure-fn? d vars) (cons 'DEF-MEMO-FN (cdr d)) d))
                  (filter bbc-def? stmts))
        main (filter (lambda (s) (not (bbc-def? s))) stmts)
        run `(begin #f ,@main)]
    `(begin
       ,@(map (lambda (v) `(define ,v ,(bbc-default v))) vars)
       ,@defs
       (set! bbc-col 0)
       ,(if (bbc-uses? '(END) stmts) (bbc-catch "bbc:end" run #f) run)
       #f)))

;;; ===================================================================
;;; --- Reader: BBC BASIC text to the statements above ---
;;;
;;;   (bbc-run """
;;;   DEF FNfact(n) IF n<2 THEN =1 ELSE =n*FNfact(n-1)
;;;   FOR i=1 TO 6 : PRINT "fact(";i;") = ";FNfact(i) : NEXT
;;;   """)
;;;   (bbc-load "fact.bas")              ; the same, from a text file
;;;   (pretty-print (bbc-expand text))   ; the (bbc-program ...) the text becomes
;;;
;;; Keywords are UPPERCASE only, as in BBC BASIC. Line numbers are read and
;;; ignored; GOTO, GOSUB, DATA and arrays come later.

;;; --- Run-time support for expressions ---

(define (bbc-and a b) (let [x (trunc a)] (x/__and__ (trunc b))))
(define (bbc-or a b) (let [x (trunc a)] (x/__or__ (trunc b))))
(define (bbc-eor a b) (let [x (trunc a)] (x/__xor__ (trunc b))))
(define (bbc-not a) (let [x (trunc a)] (x/__invert__)))

(define (bbc-sgn x) (cond ((> x 0) 1) ((< x 0) -1) (else 0)))

(define (bbc-val s)
  (let [n (string->number s)] (if n n 0)))

(define bbc-char-format "{:c}")
(define (bbc-chr n) (bbc-char-format/format (trunc n)))

(define (bbc-asc s)
  (if (= (length s) 0)
      -1
      (let [b (s/encode "utf-8")] (b/__getitem__ 0))))

(define (bbc-left s n) (substring s 0 (max 0 (min (trunc n) (length s)))))

(define (bbc-right s n)
  (let [l (length s)] (substring s (max 0 (- l (trunc n))) l)))

(define (bbc-mid s p & n)
  (let [l (length s)
        start (max 0 (min l (- (trunc p) 1)))
        end (if (null? n) l (max start (min l (+ start (trunc (car n))))))]
    (substring s start end)))

(define (bbc-instr s target & start)
  (+ 1 (s/find target (if (null? start) 0 (max 0 (- (trunc (car start)) 1))))))

;;; --- Tokenizer ---

(define (bbc-push! lst x)
  ;; Add x to the end of a growing list; (lst/append x) would turn a string into a symbol
  (lst/extend (list x)))

;; Tokens are (kind value line): kind is :num :str :id :kw :proc :fn :op :colon :eol or :eof
(define bbc-keywords
  '("PRINT" "LET" "IF" "THEN" "ELSE" "ENDIF" "FOR" "TO" "STEP" "NEXT" "REPEAT" "UNTIL"
    "WHILE" "ENDWHILE" "CASE" "OF" "WHEN" "OTHERWISE" "ENDCASE" "DEF" "ENDPROC" "LOCAL"
    "END" "STOP" "EXIT" "AND" "OR" "EOR" "NOT" "DIV" "MOD" "TRUE" "FALSE" "TAB" "SPC"
    "GOTO" "GOSUB" "RETURN" "ON" "DATA" "READ" "RESTORE" "DIM" "INPUT"
    "ABS" "INT" "SQR" "SIN" "COS" "TAN" "ATN" "LN" "LOG" "EXP" "SGN" "LEN" "PI"
    "LEFT$" "RIGHT$" "MID$" "STR$" "VAL" "CHR$" "ASC" "INSTR"))

(define bbc-hex-digits "0123456789ABCDEFabcdef")
(define bbc-two-char-ops '("<=" ">=" "<>" "+=" "-="))
(define bbc-one-char-ops "+-*/^(),;'=<>~#")

(define (bbc-name-char? c) (or (c/isalnum) (eq? c #\_)))

(define (bbc-tokenize text)
  (let [toks (list)
        n (length text)
        i 0
        line 1
        line-start #t]
    (define (emit kind value) (bbc-push! toks (list kind value line)))
    (define (char-at j) (if (< j n) (string-ref text j) #\nul))
    (define (scan-while j ok?) (while (and (< j n) (ok? (string-ref text j))) (set! j (+ j 1))) j)
    (while (< i n)
      (let [c (string-ref text i)]
        (cond
          ((eq? c #\newline)
           (emit :eol #f)
           (set! line (+ line 1))
           (set! line-start #t)
           (set! i (+ i 1)))
          ((or (eq? c #\space) (eq? c #\tab) (eq? c #\return))
           (set! i (+ i 1)))
          ((and line-start (c/isdigit))
           (let [j (scan-while i (lambda (d) (d/isdigit)))]
             (emit :line (string->number (substring text i j)))
             (set! line-start #f)
             (set! i j)))
          ((eq? c #\")
           (let [parts (list) j (+ i 1) done #f]
             (while (not done)
               (let [close (text/find "\"" j)]
                 (if (< close 0) (error (str "BBC syntax error at line " line ": missing closing quote")))
                 (bbc-push! parts (substring text j close))
                 (if (eq? (char-at (+ close 1)) #\")
                     (begin (bbc-push! parts "\"") (set! j (+ close 2)))
                     (begin (set! done #t) (set! j (+ close 1))))))
             (emit :str (str/join parts))
             (set! line-start #f)
             (set! i j)))
          ((or (c/isdigit) (and (eq? c #\.) ((char-at (+ i 1))/isdigit)))
           (let [j (scan-while i (lambda (d) (or (d/isdigit) (eq? d #\.))))]
             (if (and (eq? (char-at j) #\E)
                      (or ((char-at (+ j 1))/isdigit)
                          (and (member (char-at (+ j 1)) (list #\+ #\-)) ((char-at (+ j 2))/isdigit))))
                 (set! j (scan-while (+ j 2) (lambda (d) (d/isdigit)))))
             (emit :num (string->number (substring text i j)))
             (set! line-start #f)
             (set! i j)))
          ((eq? c #\&)
           (let [j (scan-while (+ i 1) (lambda (d) (>= (bbc-hex-digits/find (str d)) 0)))]
             (emit :num (string->number (substring text (+ i 1) j) 16))
             (set! line-start #f)
             (set! i j)))
          ((or (c/isalpha) (eq? c #\_))
           (let [j (scan-while i bbc-name-char?)]
             (if (member (char-at j) (list #\$ #\%)) (set! j (+ j 1)))
             (let [name (substring text i j)]
               (cond ((equal? name "REM")
                      (set! j (scan-while j (lambda (d) (not (eq? d #\newline))))))
                     ((member name bbc-keywords) (emit :kw name))
                     ((and (> (length name) 4) (equal? (substring name 0 4) "PROC"))
                      (emit :proc (substring name 4)))
                     ((and (> (length name) 2) (equal? (substring name 0 2) "FN"))
                      (emit :fn (substring name 2)))
                     (else (emit :id name))))
             (set! line-start #f)
             (set! i j)))
          ((eq? c #\:)
           (emit :colon #f)
           (set! i (+ i 1)))
          ((member (substring text i (min n (+ i 2))) bbc-two-char-ops)
           (emit :op (substring text i (+ i 2)))
           (set! line-start #f)
           (set! i (+ i 2)))
          ((>= (bbc-one-char-ops/find (str c)) 0)
           (emit :op (str c))
           (set! line-start #f)
           (set! i (+ i 1)))
          (else
           (error (str "BBC syntax error at line " line ": unexpected character " c))))))
    (emit :eol #f)
    (emit :eof #f)
    (emit :eof #f)
    toks))

;;; --- Parser helpers ---

(define bbc-toks (list))
(define bbc-pos 0)

(define (bbc-peek) (nth bbc-toks bbc-pos))

(define (bbc-advance!)
  (let [tok (bbc-peek)]
    (if (not (eq? (car tok) :eof)) (set! bbc-pos (+ bbc-pos 1)))
    tok))

(define (bbc-tok? tok kind value)
  (and (eq? (car tok) kind) (or (not value) (equal? (nth tok 1) value))))

(define (bbc-at? kind value) (bbc-tok? (bbc-peek) kind value))

(define (bbc-accept! kind value)
  (if (bbc-at? kind value) (begin (bbc-advance!) #t) #f))

(define (bbc-fail what)
  (let [tok (bbc-peek)]
    (error (str "BBC syntax error at line " (nth tok 2) ": " what
                (if (nth tok 1) (str " (at " (nth tok 1) ")") "")))))

(define (bbc-expect! kind value what)
  (if (bbc-at? kind value) (bbc-advance!) (bbc-fail (str "expected " what))))

(define (bbc-at-line-end?) (or (bbc-at? :eol #f) (bbc-at? :eof #f)))

(define (bbc-at-stmt-end?)
  (or (bbc-at-line-end?) (bbc-at? :colon #f) (bbc-at? :kw "ELSE")))

(define (bbc-skip-separators)
  (while (or (bbc-at? :eol #f) (bbc-at? :colon #f) (bbc-at? :line #f))
    (bbc-advance!)))

;; BBC variables are lispy3 globals: a name lispy3 already uses gets a v- prefix
(define bbc-special-names
  '("quote" "quasiquote" "if" "cond" "and" "or" "define" "define-macro" "set!" "lambda"
    "begin" "let" "dotimes" "while" "try" "catch" "save" "load" "else" "t" "nil"))
(define bbc-own-vars (list))

(define (bbc-bound? sym)
  (try (begin (eval sym) #t) (catch e #f)))

(define (bbc-var name)
  (let [sym (string->symbol name)]
    (cond ((member sym bbc-own-vars) sym)
          ((or (member name bbc-special-names) (bbc-bound? sym))
           (string->symbol (str "v-" name)))
          (else (bbc-push! bbc-own-vars sym) sym))))

(define (bbc-string-name? name)
  (equal? (string-ref name (- (length name) 1)) #\$))

;;; --- Expressions ---

;; An expression is (form type): type :num, :str or :bool (a Lisp comparison)
(define (bbc-e form type) (list form type))
(define (bbc-type e) (nth e 1))

(define (bbc-value e)
  ;; A BBC value: a comparison becomes -1 or 0
  (if (eq? (bbc-type e) :bool) (list 'if (car e) -1 0) (car e)))

(define (bbc-cond e)
  ;; A test: comparisons stay #t / #f, numbers are checked by the statement macros
  (car e))

(define (bbc-num form) (bbc-e form :num))

(define (bbc-p-expr) (bbc-p-or))

(define (bbc-logic op a b)
  (if (and (eq? (bbc-type a) :bool) (eq? (bbc-type b) :bool))
      (bbc-e (cond ((eq? op 'and) (list 'and (car a) (car b)))
                   ((eq? op 'or) (list 'or (car a) (car b)))
                   (else (list 'not (list 'eq? (car a) (car b)))))
             :bool)
      (bbc-num (list (cond ((eq? op 'and) 'bbc-and) ((eq? op 'or) 'bbc-or) (else 'bbc-eor))
                     (bbc-value a) (bbc-value b)))))

(define (bbc-p-or)
  (let loop ((left (bbc-p-and)))
    (cond ((bbc-accept! :kw "OR") (loop (bbc-logic 'or left (bbc-p-and))))
          ((bbc-accept! :kw "EOR") (loop (bbc-logic 'eor left (bbc-p-and))))
          (else left))))

(define (bbc-p-and)
  (let loop ((left (bbc-p-compare)))
    (if (bbc-accept! :kw "AND")
        (loop (bbc-logic 'and left (bbc-p-compare)))
        left)))

(define bbc-compare-ops '("=" "<>" "<" ">" "<=" ">="))

(define (bbc-compare op a b)
  (let [x (bbc-value a) y (bbc-value b)]
    (bbc-e (cond ((equal? op "=") (list '= x y))
                 ((equal? op "<>") (list 'not (list '= x y)))
                 (else (list (string->symbol op) x y)))
           :bool)))

(define (bbc-p-compare)
  (let loop ((left (bbc-p-add)))
    (let [tok (bbc-peek)]
      (if (and (eq? (car tok) :op) (member (nth tok 1) bbc-compare-ops))
          (begin (bbc-advance!) (loop (bbc-compare (nth tok 1) left (bbc-p-add))))
          left))))

(define (bbc-plus a b)
  (if (or (eq? (bbc-type a) :str) (eq? (bbc-type b) :str))
      (bbc-e (list 'string-append (bbc-value a) (bbc-value b)) :str)
      (bbc-num (list '+ (bbc-value a) (bbc-value b)))))

(define (bbc-p-add)
  (let loop ((left (bbc-p-mul)))
    (cond ((bbc-accept! :op "+") (loop (bbc-plus left (bbc-p-mul))))
          ((bbc-accept! :op "-") (loop (bbc-num (list '- (bbc-value left) (bbc-value (bbc-p-mul))))))
          (else left))))

(define (bbc-p-mul)
  (let loop ((left (bbc-p-power)))
    (cond ((bbc-accept! :op "*")
           (loop (bbc-num (list '* (bbc-value left) (bbc-value (bbc-p-power))))))
          ((bbc-accept! :op "/")
           (loop (bbc-num (list '/ (list 'float (bbc-value left)) (bbc-value (bbc-p-power))))))
          ((bbc-accept! :kw "DIV")
           (loop (bbc-num (list 'quotient (list 'trunc (bbc-value left)) (list 'trunc (bbc-value (bbc-p-power)))))))
          ((bbc-accept! :kw "MOD")
           (loop (bbc-num (list 'remainder (list 'trunc (bbc-value left)) (list 'trunc (bbc-value (bbc-p-power)))))))
          (else left))))

(define (bbc-p-power)
  (let loop ((left (bbc-p-unary)))
    (if (bbc-accept! :op "^")
        (loop (bbc-num (list 'expt (bbc-value left) (bbc-value (bbc-p-unary)))))
        left)))

(define (bbc-p-unary)
  (cond ((bbc-accept! :op "-")
         (let [e (bbc-p-unary)]
           (if (number? (car e)) (bbc-num (- (car e))) (bbc-num (list '- (bbc-value e))))))
        ((bbc-accept! :op "+") (bbc-p-unary))
        ((bbc-accept! :kw "NOT")
         (let [e (bbc-p-unary)]
           (if (eq? (bbc-type e) :bool)
               (bbc-e (list 'not (car e)) :bool)
               (bbc-num (list 'bbc-not (bbc-value e))))))
        (else (bbc-p-primary))))

;; BBC function: (name lisp-function min-args max-args type)
(define bbc-functions
  '(("ABS" abs 1 1 :num) ("INT" floor 1 1 :num) ("SQR" sqrt 1 1 :num)
    ("SIN" sin 1 1 :num) ("COS" cos 1 1 :num) ("TAN" tan 1 1 :num) ("ATN" atan 1 1 :num)
    ("LN" log 1 1 :num) ("LOG" log10 1 1 :num) ("EXP" exp 1 1 :num) ("SGN" bbc-sgn 1 1 :num)
    ("LEN" length 1 1 :num) ("VAL" bbc-val 1 1 :num) ("ASC" bbc-asc 1 1 :num)
    ("STR$" bbc-str 1 1 :str) ("CHR$" bbc-chr 1 1 :str)
    ("LEFT$" bbc-left 2 2 :str) ("RIGHT$" bbc-right 2 2 :str) ("MID$" bbc-mid 2 3 :str)
    ("INSTR" bbc-instr 2 3 :num)))

(define (bbc-lookup name table)
  (cond ((null? table) #f)
        ((equal? (car (car table)) name) (car table))
        (else (bbc-lookup name (cdr table)))))

(define (bbc-p-args)
  ;; (a, b, ...) as BBC values; no brackets, no arguments
  (if (bbc-accept! :op "(")
      (let [args (list (bbc-value (bbc-p-expr)))]
        (while (bbc-accept! :op ",") (bbc-push! args (bbc-value (bbc-p-expr))))
        (bbc-expect! :op ")" ")")
        args)
      (list)))

(define (bbc-p-function entry)
  (let [lisp-name (nth entry 1)
        args (if (= (nth entry 3) 1) (list (bbc-value (bbc-p-unary))) (bbc-p-args))]
    (if (or (< (length args) (nth entry 2)) (> (length args) (nth entry 3)))
        (bbc-fail (str (car entry) " needs " (nth entry 2) " to " (nth entry 3) " arguments")))
    (bbc-e (cons lisp-name args) (nth entry 4))))

(define (bbc-p-primary)
  (let [tok (bbc-peek)
        kind (car tok)
        value (nth tok 1)]
    (cond ((eq? kind :num) (bbc-advance!) (bbc-num value))
          ((eq? kind :str) (bbc-advance!) (bbc-e value :str))
          ((bbc-accept! :op "(")
           (let [e (bbc-p-expr)]
             (bbc-expect! :op ")" ")")
             e))
          ((eq? kind :id)
           (bbc-advance!)
           (if (bbc-at? :op "(") (bbc-fail "arrays are not supported yet"))
           (bbc-e (bbc-var value) (if (bbc-string-name? value) :str :num)))
          ((eq? kind :fn)
           (bbc-advance!)
           (bbc-e (append (list 'FN (string->symbol value)) (bbc-p-args))
                  (if (bbc-string-name? value) :str :num)))
          ((bbc-accept! :kw "TRUE") (bbc-num -1))
          ((bbc-accept! :kw "FALSE") (bbc-num 0))
          ((bbc-accept! :kw "PI") (bbc-num 'pi))
          ((and (eq? kind :kw) (bbc-lookup value bbc-functions))
           (bbc-advance!)
           (bbc-p-function (bbc-lookup value bbc-functions)))
          (else (bbc-fail "expected an expression")))))

;;; --- Statements ---

(define (bbc-p-value-list)
  (let [vals (list (bbc-value (bbc-p-expr)))]
    (while (bbc-accept! :op ",") (bbc-push! vals (bbc-value (bbc-p-expr))))
    vals))

(define (bbc-p-variable)
  (let [tok (bbc-expect! :id #f "a variable")]
    (if (bbc-at? :op "(") (bbc-fail "arrays are not supported yet"))
    (nth tok 1)))

(define (bbc-p-assign)
  (let [name (bbc-p-variable)
        var (bbc-var name)]
    (cond ((bbc-accept! :op "=") (list 'LET var (bbc-value (bbc-p-expr))))
          ((bbc-accept! :op "+=")
           (list 'LET var (list (if (bbc-string-name? name) 'string-append '+) var (bbc-value (bbc-p-expr)))))
          ((bbc-accept! :op "-=") (list 'LET var (list '- var (bbc-value (bbc-p-expr)))))
          (else (bbc-fail "expected = after the variable")))))

(define (bbc-p-print)
  (let [items (list)]
    (while (not (bbc-at-stmt-end?))
      (cond ((bbc-accept! :op ";") (bbc-push! items :semi))
            ((bbc-accept! :op ",") (bbc-push! items :comma))
            ((bbc-accept! :op "'") (bbc-push! items :nl))
            ((bbc-accept! :kw "TAB")
             (bbc-expect! :op "(" "( after TAB")
             (let [x (bbc-value (bbc-p-expr))]
               (if (bbc-accept! :op ",")
                   (let [y (bbc-value (bbc-p-expr))]
                     (bbc-push! items (list 'TAB x y)))
                   (bbc-push! items (list 'TAB x)))
               (bbc-expect! :op ")" ")")))
            ((bbc-accept! :kw "SPC") (bbc-push! items (list 'SPC (bbc-value (bbc-p-unary)))))
            (else (bbc-push! items (bbc-value (bbc-p-expr))))))
    (cons 'PRINT items)))

(define (bbc-returns? stmt)
  ;; Does the statement always leave an FN with a value?
  (and (pair? stmt) (list? stmt)
       (cond ((eq? (car stmt) 'FN=) #t)
             ((eq? (car stmt) 'IF)
              (let [parts (bbc-split (cdr (cdr stmt)) 'ELSE)]
                (and (bbc-second parts)
                     (not (null? (car parts)))
                     (not (null? (bbc-second parts)))
                     (bbc-returns? (last (car parts)))
                     (bbc-returns? (last (bbc-second parts))))))
             (else #f))))

(define (bbc-p-block terminators fn-body)
  ;; Statements up to a keyword in terminators, which is left for the caller.
  ;; An FN body ends after a statement that always returns.
  (let [stmts (list) done #f]
    (while (not done)
      (bbc-skip-separators)
      (let [tok (bbc-peek)]
        (if (or (eq? (car tok) :eof)
                (and (eq? (car tok) :kw) (member (nth tok 1) terminators)))
            (set! done #t)
            (let [stmt (bbc-p-statement)]
              (bbc-push! stmts stmt)
              (if (and fn-body (bbc-returns? stmt)) (set! done #t))
              (if (not (or (bbc-at-stmt-end?) (bbc-at? :kw #f)))
                  (bbc-fail "unexpected text after the statement"))))))
    stmts))

(define (bbc-p-line-stmts)
  ;; The statements of a single-line IF, up to the end of the line or ELSE
  (let [stmts (list)]
    (while (not (or (bbc-at-line-end?) (bbc-at? :kw "ELSE")))
      (if (not (bbc-accept! :colon #f))
          (bbc-push! stmts (bbc-p-statement))))
    stmts))

(define (bbc-p-if)
  (let [test (bbc-cond (bbc-p-expr))]
    (bbc-accept! :kw "THEN")
    (if (bbc-at-line-end?)
        (let [then-part (bbc-p-block '("ELSE" "ENDIF") #f)]
          (if (bbc-accept! :kw "ELSE")
              (let [else-part (bbc-p-block '("ENDIF") #f)]
                (bbc-expect! :kw "ENDIF" "ENDIF")
                (append (list 'IF test) then-part (list 'ELSE) else-part))
              (begin
                (bbc-expect! :kw "ENDIF" "ENDIF")
                (append (list 'IF test) then-part))))
        (let [then-part (bbc-p-line-stmts)]
          (if (bbc-accept! :kw "ELSE")
              (append (list 'IF test) then-part (list 'ELSE) (bbc-p-line-stmts))
              (append (list 'IF test) then-part))))))

(define (bbc-p-for)
  (let [var (bbc-var (bbc-p-variable))]
    (bbc-expect! :op "=" "= after the FOR variable")
    (let [from (bbc-value (bbc-p-expr))]
      (bbc-expect! :kw "TO" "TO")
      (let [to (bbc-value (bbc-p-expr))
            step (if (bbc-accept! :kw "STEP") (list 'STEP (bbc-value (bbc-p-expr))) (list))
            body (bbc-p-block '("NEXT") #f)]
        (bbc-expect! :kw "NEXT" "NEXT")
        (if (bbc-at? :id #f) (bbc-advance!))
        (append (list 'FOR var from to) step body)))))

(define (bbc-p-case)
  (let [subject (bbc-value (bbc-p-expr))
        clauses (list)
        ends '("WHEN" "OTHERWISE" "ENDCASE")]
    (bbc-expect! :kw "OF" "OF")
    (bbc-skip-separators)
    (while (not (bbc-accept! :kw "ENDCASE"))
      (cond ((bbc-accept! :kw "WHEN")
             (let [vals (bbc-p-value-list)]
               (bbc-push! clauses (append (list 'WHEN vals) (bbc-p-block ends #f)))))
            ((bbc-accept! :kw "OTHERWISE")
             (bbc-push! clauses (cons 'OTHERWISE (bbc-p-block ends #f))))
            (else (bbc-fail "expected WHEN, OTHERWISE or ENDCASE")))
      (bbc-skip-separators))
    (append (list 'CASE subject) clauses)))

(define (bbc-p-parms)
  (let [parms (list)]
    (if (bbc-accept! :op "(")
        (begin
          (bbc-push! parms (bbc-var (bbc-p-variable)))
          (while (bbc-accept! :op ",") (bbc-push! parms (bbc-var (bbc-p-variable))))
          (bbc-expect! :op ")" ")")))
    parms))

(define (bbc-p-def)
  (let [tok (bbc-advance!)
        kind (car tok)]
    (if (not (or (eq? kind :proc) (eq? kind :fn)))
        (bbc-fail "expected PROC or FN after DEF"))
    (let [head (cons (string->symbol (nth tok 1)) (bbc-p-parms))]
      (if (eq? kind :proc)
          (let [body (bbc-p-block '("ENDPROC") #f)]
            (bbc-expect! :kw "ENDPROC" "ENDPROC")
            (append (list 'DEF-PROC head) body))
          (append (list 'DEF-FN head) (bbc-p-block '() #t))))))

(define (bbc-p-statement)
  (let [tok (bbc-peek)
        kind (car tok)
        value (nth tok 1)]
    (cond ((eq? kind :id) (bbc-p-assign))
          ((eq? kind :proc)
           (bbc-advance!)
           (append (list 'PROC (string->symbol value)) (bbc-p-args)))
          ((bbc-accept! :op "=") (list 'FN= (bbc-value (bbc-p-expr))))
          ((not (eq? kind :kw)) (bbc-fail "expected a statement"))
          ((equal? value "PRINT") (bbc-advance!) (bbc-p-print))
          ((equal? value "LET") (bbc-advance!) (bbc-p-assign))
          ((equal? value "IF") (bbc-advance!) (bbc-p-if))
          ((equal? value "FOR") (bbc-advance!) (bbc-p-for))
          ((equal? value "REPEAT")
           (bbc-advance!)
           (let [body (bbc-p-block '("UNTIL") #f)]
             (bbc-expect! :kw "UNTIL" "UNTIL")
             (append (list 'REPEAT) body (list 'UNTIL (bbc-cond (bbc-p-expr))))))
          ((equal? value "WHILE")
           (bbc-advance!)
           (let [test (bbc-cond (bbc-p-expr))
                 body (bbc-p-block '("ENDWHILE") #f)]
             (bbc-expect! :kw "ENDWHILE" "ENDWHILE")
             (append (list 'WHILE test) body)))
          ((equal? value "CASE") (bbc-advance!) (bbc-p-case))
          ((equal? value "DEF") (bbc-advance!) (bbc-p-def))
          ((equal? value "LOCAL")
           (bbc-advance!)
           (let [vars (list (bbc-var (bbc-p-variable)))]
             (while (bbc-accept! :op ",") (bbc-push! vars (bbc-var (bbc-p-variable))))
             (cons 'LOCAL vars)))
          ((or (equal? value "END") (equal? value "STOP")) (bbc-advance!) (list 'END))
          ((equal? value "ENDPROC") (bbc-advance!) (list 'ENDPROC))
          ((equal? value "EXIT")
           (bbc-advance!)
           (let [what (bbc-advance!)]
             (cond ((bbc-tok? what :kw "FOR") (if (bbc-at? :id #f) (bbc-advance!)) (list 'EXIT-FOR))
                   ((bbc-tok? what :kw "REPEAT") (list 'EXIT-REPEAT))
                   ((bbc-tok? what :kw "WHILE") (list 'EXIT-WHILE))
                   (else (bbc-fail "expected FOR, REPEAT or WHILE after EXIT")))))
          ((member value '("GOTO" "GOSUB" "RETURN" "ON" "DATA" "READ" "RESTORE" "DIM" "INPUT"))
           (bbc-fail (str value " is not supported yet")))
          (else (bbc-fail "expected a statement")))))

;;; --- Entry points ---

(define (bbc-expand text)
  ;; The (bbc-program ...) form for BBC BASIC source text
  (set! bbc-toks (bbc-tokenize text))
  (set! bbc-pos 0)
  (let [stmts (bbc-p-block '() #f)]
    (if (not (bbc-at? :eof #f)) (bbc-fail "unexpected statement"))
    (cons 'bbc-program stmts)))

(define (bbc-source x)
  ;; A macro argument as text: a string as written, anything else evaluated
  (if (string? x) x (eval x)))

(define-macro (bbc-run source)
  (bbc-expand (bbc-source source)))

(define-macro (bbc-load filename)
  (bbc-expand (slurp (bbc-source filename))))
