;;; mini-basic.lisp - structured BBC BASIC statements as lispy3 macros
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

(define (bbc-def kind head body)
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
                `(begin #f ,@tail-body))]
    `(define (,(bbc-def-name kind name) ,@args)
       (let ,(map list saves saved)
         ,@(map (lambda (p a) `(set! ,p ,a)) parms args)
         (let ((,result ,run))
           ,@(map (lambda (v s) `(set! ,v ,s)) saved saves)
           ,result)))))

(define-macro (DEF-PROC head & body) (bbc-def 'PROC head body))
(define-macro (DEF-FN head & body) (bbc-def 'FN head body))

;;; --- A whole program ---

(define-macro (bbc-program & stmts)
  (let [defs (filter bbc-def? stmts)
        main (filter (lambda (s) (not (bbc-def? s))) stmts)
        run `(begin #f ,@main)]
    `(begin
       ,@(map (lambda (v) `(define ,v ,(bbc-default v))) (bbc-assigned-vars stmts))
       ,@defs
       (set! bbc-col 0)
       ,(if (bbc-uses? '(END) stmts) (bbc-catch "bbc:end" run #f) run)
       #f)))
