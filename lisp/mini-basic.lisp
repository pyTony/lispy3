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
;;; Terminal: (CLS), (COLOUR n)/(COLOR n), (VDU byte ...),
;;; (ANSI byte-or-string ...), (ANSI-RESET); see docs/MINI_BASIC.md for limits.
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
;;;   (GOTO target), (GOSUB target), (RETURN), (LABEL name)
;;;   (ON-GOTO index (targets ...) (else-statements ...)) and ON-GOSUB
;;;
;;; As in BBC BASIC, PROC and FN parameters and LOCAL variables are dynamically
;;; scoped: the old values are saved on entry and put back on exit. bbc-program
;;; defines every variable the program assigns (0, or "" for var$) before it runs,
;;; and lifts DEF-PROC and DEF-FN to the front, so they may come after the main part.
;;; Tests are BBC truth values: 0 and #f are false, anything else (TRUE is -1) is true.

;;; Transform graphics commands directly to the framebuffer backend, not ANSI/VDU.

(define-macro (MODE n) `(begin (set! bbc-text-background 0) (bbc-graphics-mode ,n)))
(define-macro (GCOL & values) `(graphics-gcol ,@values))
(define-macro (MOVE x y) `(graphics-move ,x ,y))
(define-macro (DRAW x y) `(graphics-draw ,x ,y))
(define-macro (PLOT & values) `(graphics-plot ,@values))
(define-macro (ORIGIN x y) `(graphics-origin ,x ,y))
(define-macro (CLG) `(graphics-clg))
;; OFF / ON hide and show the text cursor; the Listener has none to hide.
(define-macro (CURSOR on) ''())
(define-macro (CIRCLE fill x y r)
  (if fill `(graphics-virtual-circle-fill ,x ,y ,r) `(graphics-virtual-circle ,x ,y ,r)))
(define-macro (RECTANGLE fill & values)
  `(graphics-virtual-rectangle ,@values
                               ,@(cond ((not fill) '())
                                       ((= (length values) 3) '(() #t))
                                       (else '(#t)))))
(define-macro (WAIT & time) `(bbc-wait ,@time))
(define-macro (OSCLI command) `(bbc-oscli ,command))

;;; --- Run-time support ---

(define TRUE -1)
(define FALSE 0)

(define (bbc-true? x)
  (not (or (eq? x #f) (eq? x 0) (null? x))))

(define (bbc-int x)
  (trunc x))

;; Portable 32-bit random state, owned by this BASIC library/workspace.
;; Ranges/seeding follow BBC BASIC; the sequence is not BBCSDL's bit pattern.
(define bbc-rnd-state 1)
(define bbc-rnd-last 0.0)

(define (bbc-rnd &optional (argument :bare))
  (if (and (not (eq? argument :bare)) (not (number? argument)))
      (error "RND: expected a numeric argument"))
  (let [bare (eq? argument :bare)
        n (if (eq? argument :bare) 1 (bbc-int argument))]
    (cond ((< n 0)
           (set! bbc-rnd-state (modulo n 4294967296))
           n)
          ((and (not bare) (= n 0)) bbc-rnd-last)
          (else
           (set! bbc-rnd-state (modulo (+ (* 1664525 bbc-rnd-state) 1013904223) 4294967296))
           (set! bbc-rnd-last (/ (float bbc-rnd-state) 4294967296))
           (cond (bare (if (>= bbc-rnd-state 2147483648) (- bbc-rnd-state 4294967296) bbc-rnd-state))
                 ((= n 1) bbc-rnd-last)
                 (else (+ 1 (floor (* n bbc-rnd-last)))))))))

;; BASIC TIME is an assignable elapsed-real-time clock, in centiseconds.
;; Keep integer host ticks so reads do not accumulate floating-point drift.
;; It persists between bbc-run/bbc-load calls until assigned or reloaded.
(define bbc-time-base (get-internal-real-time))
(define bbc-time-offset 0)

(define (bbc-time-read)
  (+ bbc-time-offset
     (quotient (* 100 (- (get-internal-real-time) bbc-time-base))
               internal-time-units-per-second)))

(define (bbc-time-set! value)
  (set! bbc-time-offset (bbc-int value))
  (set! bbc-time-base (get-internal-real-time))
  #f)

;; Values passed out of an FN by (FN= exp) before the early return
(define bbc-fn-value 0)

;; The output column, for :comma zones, TAB and PRINT's right-justified numbers
(define bbc-col 0)
(define bbc-zone-width 10)
(define bbc-blank "")

(define (bbc-write-visible text)
  (format #t "~a" text)
  (let [s (str text)
        nl (s/rfind "\n")]
    (if (< nl 0)
        (set! bbc-col (+ bbc-col (length s)))
        (set! bbc-col (- (length s) nl 1)))))

;; Keep Unicode printable text intact; only the VDU byte channel wraps to 8 bits.
(define (bbc-character-code character)
  (let [text (str character)
        bytes (text/encode "utf-32-le")]
    (+ (bytes/__getitem__ 0) (* 256 (bytes/__getitem__ 1))
       (* 65536 (bytes/__getitem__ 2)) (* 16777216 (bytes/__getitem__ 3)))))

(define (bbc-write text)
  (for-each
    (lambda (character)
      (let [code (bbc-character-code character)]
        (if (or (not (null? bbc-vdu-pending)) (< code 32) (= code 127))
            (bbc-vdu (list code))
            (bbc-write-visible (str character)))))
    (seq (str text))))

(define (bbc-newline)
  ;; A normal logical CR/LF is represented by stdout's native newline. If a
  ;; parameter is pending, both bytes must pass through the decoder instead.
  (if (null? bbc-vdu-pending)
      (begin (format #t "~%") (set! bbc-col 0))
      (bbc-vdu (list 13 10))))

(define (bbc-spaces n)
  (if (> n 0) (bbc-write (bbc-blank/ljust n))))

(define (bbc-zone)
  (bbc-spaces (mod (- bbc-zone-width (mod bbc-col bbc-zone-width)) bbc-zone-width)))

(define (bbc-tab n)
  (if (> bbc-col n) (bbc-newline))
  (bbc-spaces (- n bbc-col)))

;; Emit terminal controls without advancing the printable output column.
(define (bbc-ansi control)
  (format #t "~a" (str (bbc-chr 27) "[" control)))

;; COLOUR 128+n sets it; CLS clears a graphics window to it
(define bbc-text-background 0)

(define (bbc-cls)
  (bbc-ansi "2J")
  (bbc-ansi "H")
  (graphics-cls bbc-text-background)
  (set! bbc-col 0))

(define (bbc-wait & time)
  ;; WAIT n pauses n centiseconds
  (sleep (if (null? time) 0 (/ (max 0 (car time)) 100.0))))

(define (bbc-oscli command)
  ;; *REFRESH [OFF|ON] controls when the graphics window shows the picture
  (let [text (string-upcase (str command))
        words (map str (text/split))]
    (cond ((null? words) #f)
          ((and (equal? (car words) "REFRESH") (null? (cdr words))) (graphics-refresh))
          ((equal? (car words) "REFRESH")
           (cond ((equal? (bbc-second words) "OFF") (graphics-refresh #f))
                 ((equal? (bbc-second words) "ON") (graphics-refresh #t))
                 (else (error (str "*REFRESH expects OFF or ON, not " (bbc-second words))))))
          (else (error (str "unsupported * command: " (car words)))))))

(define (bbc-colour value)
  (let [n (bbc-int value)]
    (if (not (or (and (>= n 0) (<= n 15))
                 (and (>= n 128) (<= n 143))))
        (error "COLOUR: expected 0..15 or 128..143"))
    (let [background (>= n 128)
          colour (if (>= n 128) (- n 128) n)]
      (if background (set! bbc-text-background colour))
      (bbc-ansi (str (+ (if background 40 30)
                       (if (>= colour 8) 60 0)
                       (modulo colour 8)) "m")))))

(define (bbc-tab-xy x y)
  (let [column (bbc-int x) row (bbc-int y)]
    (if (or (< column 0) (< row 0))
        (error "TAB: coordinates must be non-negative"))
    (bbc-ansi (str (+ row 1) ";" (+ column 1) "H"))
    (set! bbc-col column)))

(define bbc-vdu-pending '())

;; VDU is a byte stream: parameter bytes can arrive in a later call.
(define (bbc-vdu bytes)
  (for-each
    (lambda (value)
      (let [byte (modulo (bbc-int value) 256)]
        (if (not (null? bbc-vdu-pending))
            (begin
              (set! bbc-vdu-pending (append bbc-vdu-pending (list byte)))
              (let [code (car bbc-vdu-pending)]
                (cond
                  ((and (= code 17) (= (length bbc-vdu-pending) 2))
                   (set! bbc-vdu-pending '())
                   (bbc-colour byte))
                  ((and (= code 31) (= (length bbc-vdu-pending) 3))
                   (let [column (nth bbc-vdu-pending 1)]
                     (set! bbc-vdu-pending '())
                     (bbc-tab-xy column byte))))))
            (cond
              ((or (= byte 17) (= byte 31))
               (set! bbc-vdu-pending (list byte)))
              ((= byte 0) #f)
              ((= byte 7) (format #t "~a" (bbc-chr 7)))
              ((= byte 8)
               (format #t "~a" (bbc-chr 8))
               (set! bbc-col (max 0 (- bbc-col 1))))
              ((= byte 10) (bbc-ansi "1B"))
              ((= byte 12) (bbc-cls))
              ((= byte 13)
               (format #t "~a" (bbc-chr 13)) (set! bbc-col 0))
              ((= byte 30) (bbc-ansi "H") (set! bbc-col 0))
              ((or (< byte 32) (= byte 127))
               (error (str "VDU: unsupported control " byte)))
              (else (bbc-write-visible (bbc-chr byte)))))))
    bytes))

;; Explicit raw ANSI channel; these bytes never enter the BBC VDU decoder.
;; Treat contents as controls, not printable cells. Cursor changes are opaque.
(define (bbc-ansi-bytes items)
  (for-each (lambda (item)
              (format #t "~a" (if (string? item) item
                                  (bbc-chr (modulo (bbc-int item) 256)))))
            items))

(define-macro (ANSI & items) `(bbc-ansi-bytes (list ,@items)))

(define-macro (VDU & bytes) `(bbc-vdu (list ,@bytes)))

(define-macro (CLS) '(bbc-cls))
;; COLOUR n,r,g,b makes graphics logical colour n that RGB colour
(define-macro (COLOUR value & rgb)
  (if (null? rgb) `(bbc-colour ,value) `(graphics-palette ,value ,@rgb)))
(define-macro (COLOR value & rgb)
  (if (null? rgb) `(bbc-colour ,value) `(graphics-palette ,value ,@rgb)))
;; Lisp-only convenience: restore terminal default attributes.
(define-macro (ANSI-RESET) '(bbc-ansi "0m"))

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

(define bbc-number-print-style :bbc)

(define (bbc-set-print-style! style)
  (if (not (member style '(:bbc :mbasic)))
      (error "number print style must be :bbc or :mbasic"))
  (set! bbc-number-print-style style)
  #f)

(define (bbc-print-value v justify)
  (if (string? v)
      (bbc-write v)
      (let [text (bbc-str v)]
        (bbc-write (if (eq? bbc-number-print-style :mbasic)
                       (str (if (eq? (string-ref text 0) #\-) "" " ") text " ")
                       (if justify (text/rjust bbc-zone-width) text))))))

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

(define (bbc-nested-body-code stmts)
  ;; The extension replaces this hook to resolve jumps in active bodies.
  `(begin #f ,@stmts))

;;; --- Statements ---

(define-macro (LET var exp)
  ;; A% 32-bit, A%% 64-bit, A& a byte, A# a float (mini-basic-num.lisp)
  `(set! ,var ,(bbc-typed-value var exp)))

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
              ((and (pair? item) (list? item) (eq? (car item) 'HEX))
               (cons `(bbc-print-hex ,(bbc-second item) ,justify) (bbc-print-code more justify)))
              (else
               (cons `(bbc-print-value ,item ,justify) (bbc-print-code more justify)))))))

(define-macro (PRINT & items)
  `(begin ,@(bbc-print-code items #t)))

(define-macro (IF test & body)
  (let [parts (bbc-split body 'ELSE)
        then-part (bbc-nested-body-code (car parts))]
    (if (bbc-second parts)
        `(if ,(bbc-test test) ,then-part ,(bbc-nested-body-code (bbc-second parts)))
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
                (while (begin ,(bbc-nested-body-code body) ,next ,more?)))]
    `(begin
       (LET ,var ,from)
       ,(if (bbc-uses? '(EXIT-FOR) body) (bbc-catch "bbc:exit-for" loop #f) loop))))

(define-macro (REPEAT & body)
  (let [parts (bbc-split body 'UNTIL)
        loop `(while (begin ,(bbc-nested-body-code (car parts)) (not ,(bbc-test (car (bbc-second parts))))))]
    (if (bbc-uses? '(EXIT-REPEAT) body) (bbc-catch "bbc:exit-repeat" loop #f) loop)))

(define-macro (WHILE test & body)
  (let [loop `(while ,(bbc-test test) ,(bbc-nested-body-code body))]
    (if (bbc-uses? '(EXIT-WHILE) body) (bbc-catch "bbc:exit-while" loop #f) loop)))

(define-macro (CASE exp & clauses)
  (let [v (gensym "case")]
    `(let ((,v ,exp))
       (cond ,@(map (lambda (clause)
                      (if (eq? (car clause) 'OTHERWISE)
                          `(else ,(bbc-nested-body-code (cdr clause)))
                          `((or ,@(map (lambda (w) `(= ,v ,w)) (bbc-second clause)))
                            ,(bbc-nested-body-code (cdr (cdr clause))))))
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
        ;; A bare returned variable must not become a tagbody label.
        ((eq? (car stmt) 'FN=) (list 'begin (bbc-second stmt)))
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
        err (gensym "error")
        tail-body (bbc-tail body)
        tag (if (eq? kind 'FN) "bbc:return" "bbc:endproc")
        run (if (bbc-uses? '(FN= ENDPROC) tail-body)
                (bbc-catch tag `(begin #f ,@tail-body) 'bbc-fn-value)
                `(begin #f ,@tail-body))
        fn `(lambda ,args
              (let ,(map list saves saved)
                ,@(map (lambda (p a) `(set! ,p ,a)) parms args)
                (try
                  (let ((,result ,run))
                    ,@(map (lambda (v s) `(set! ,v ,s)) saved saves)
                    ,result)
                  (catch ,err
                    ,@(map (lambda (v s) `(set! ,v ,s)) saved saves)
                    (error ,err)))))]
    `(define ,(bbc-def-name kind name) ,(if memo `(memoize-exact ,fn) fn))))

(define-macro (DEF-PROC head & body) (bbc-def 'PROC head body #f))
(define-macro (DEF-FN head & body) (bbc-def 'FN head body #f))
;; A pure FN caches calls only when every argument is an exact number.
;; Float/mixed/string calls run directly; explicit Lisp memoize is unchanged.
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
         (not (bbc-uses? '(MODE GCOL MOVE DRAW PLOT ORIGIN CLG CIRCLE RECTANGLE WAIT OSCLI CURSOR graphics-plot graphics-draw graphics-move graphics-gcol graphics-origin graphics-clg bbc-graphics-mode PRINT PROC END GOSUB ON-GOSUB RETURN CLS COLOUR COLOR VDU ANSI ANSI-RESET bbc-cls bbc-colour bbc-vdu bbc-ansi bbc-ansi-bytes bbc-time-read bbc-time-set! bbc-rnd) body))
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
       ;; Closing a MODE window ends the program like END (see graphics bindings)
       ,(if (bbc-uses? '(END MODE) stmts) (bbc-catch "bbc:end" run #f) run)
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
;;; retained as labels; mini-basic-ext.lisp adds jumps, subroutines, DATA and arrays.

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

(define (bbc-ucase s)
  (if (not (string? s)) (error "UCASE$: expected a string"))
  (upcase s))

(define (bbc-lcase s)
  (if (not (string? s)) (error "LCASE$: expected a string"))
  (downcase s))

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
    "GOTO" "GOSUB" "RETURN" "ON" "DATA" "READ" "RESTORE" "DIM" "INPUT" "TIME" "CLS" "COLOUR" "COLOR" "VDU" "ANSI" "MODE" "GCOL" "MOVE" "DRAW" "PLOT" "ORIGIN" "CLG"
    "CIRCLE" "RECTANGLE" "FILL" "WAIT" "OSCLI" "SUM"
    "ABS" "INT" "SQR" "SIN" "COS" "TAN" "ATN" "LN" "LOG" "EXP" "SGN" "LEN" "PI" "RND"
    "LEFT$" "RIGHT$" "MID$" "STR$" "VAL" "CHR$" "ASC" "INSTR" "UCASE$" "LCASE$"))

(define bbc-hex-digits "0123456789ABCDEFabcdef")
(define bbc-two-char-ops '("<=" ">=" "<>" "+=" "-=" "<<" ">>"))
(define bbc-one-char-ops "+-*/^(),;'=<>~#.")

(define (bbc-name-char? c) (or (c/isalnum) (eq? c #\_)))

;; The shared MBASIC option folds syntax names, never string/DATA contents.
(define (bbc-normalize-name name)
  (if (eq? bbc-number-print-style :mbasic) (string-upcase name) name))

;; BBC reads SQR5 as SQR 5: a keyword followed only by digits is not a name
(define (bbc-digit? d) (d/isdigit))

(define (bbc-keyword-digits-end text start j)
  (let [name (substring text start j)
        k (- j start)]
    (while (and (> k 0) (bbc-digit? (string-ref name (- k 1)))) (set! k (- k 1)))
    (if (and (> k 0) (< k (- j start))
             (member (bbc-normalize-name (substring name 0 k)) bbc-keywords))
        (+ start k)
        j)))

(define (bbc-tokenize text)
  (let [toks (list)
        n (length text)
        i 0
        line 1
        line-start #t]
    (define (emit kind value) (bbc-push! toks (list kind value line)))
    (define (emit-name kind value raw)
      (if (eq? bbc-number-print-style :mbasic)
          (bbc-push! toks (list kind value line raw))
          (emit kind value)))
    (define (char-at j) (if (< j n) (string-ref text j) #\nul))
    (define (digit-at? j) (let [d (char-at j)] (d/isdigit)))
    (define (scan-while j ok?) (while (and (< j n) (ok? (string-ref text j))) (set! j (+ j 1))) j)
    (define (statement-start?)
      (or (null? toks)
          (let [last (nth toks (- (length toks) 1))]
            (or (member (car last) '(:eol :colon :line))
                (bbc-tok? last :kw "THEN") (bbc-tok? last :kw "ELSE")))))
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
          ((or (c/isdigit) (and (eq? c #\.) (digit-at? (+ i 1))))
           (let [j (scan-while i (lambda (d) (or (d/isdigit) (eq? d #\.))))]
             (if (and (or (eq? (char-at j) #\E) (and (eq? bbc-number-print-style :mbasic) (eq? (char-at j) #\e)))
                      (or (digit-at? (+ j 1))
                          (and (member (char-at (+ j 1)) (list #\+ #\-)) (digit-at? (+ j 2)))))
                 (set! j (scan-while (+ j 2) (lambda (d) (d/isdigit)))))
             (emit :num (string->number (substring text i j)))
             (set! line-start #f)
             (set! i j)))
          ((and (eq? c #\%) (member (char-at (+ i 1)) (list #\0 #\1)))
           (let [j (scan-while (+ i 1) (lambda (d) (member d (list #\0 #\1))))]
             (emit :num (string->number (substring text (+ i 1) j) 2))
             (set! line-start #f)
             (set! i j)))
          ((eq? c #\&)
           (let [j (scan-while (+ i 1) (lambda (d) (>= (bbc-hex-digits/find (str d)) 0)))]
             (emit :num (bbc-hex-constant (substring text (+ i 1) j)))
             (set! line-start #f)
             (set! i j)))
          ((and (eq? c #\?) (statement-start?))
           ;; ? at the start of a statement is the common shorthand for PRINT
           (emit-name :kw "PRINT" "?")
           (set! line-start #f)
           (set! i (+ i 1)))
          ((and (eq? c #\*) (statement-start?))
           ;; *command: the rest of the line, as OSCLI would get it
           (let [j (scan-while i (lambda (d) (not (eq? d #\newline))))]
             (emit :star (substring text (+ i 1) j))
             (set! line-start #f)
             (set! i j)))
          ((or (c/isalpha) (eq? c #\_))
           (let [j (scan-while i bbc-name-char?)]
             (set! j (bbc-keyword-digits-end text i j))
             (set! j (bbc-name-end text i j (char-at j) (char-at (+ j 1))))
             (let [raw (substring text i j) name (bbc-normalize-name raw)]
               (cond ((and (>= (length name) 3) (equal? (substring name 0 3) "REM"))
                      (set! j (scan-while j (lambda (d) (not (eq? d #\newline))))))
                     ((member name bbc-keywords) (emit-name :kw name raw))
                     ((and (> (length name) 4) (equal? (substring name 0 4) "PROC"))
                      (emit-name :proc (substring name 4) raw))
                     ((and (> (length name) 2) (equal? (substring name 0 2) "FN"))
                      (emit-name :fn (substring name 2) raw))
                     (else (emit-name :id name raw))))
             (set! line-start #f)
             (set! i j)))
          ((eq? c #\:)
           (emit :colon #f)
           (set! i (+ i 1)))
          ((equal? (substring text i (min n (+ i 3))) ">>>")
           (emit :op ">>>")
           (set! line-start #f)
           (set! i (+ i 3)))
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

;; An unknown word used as a statement says so, rather than asking for =
(define (bbc-fail-assign name)
  (bbc-fail (if (bbc-at-stmt-end?)
                (str "unknown statement " name)
                (str "expected = after the variable " name))))

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
  (while (or (bbc-at? :eol #f) (bbc-at? :colon #f))
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
  ;; The shifts << >> >>> bind like comparisons, as in BBC BASIC for SDL
  (let loop ((left (bbc-p-add)))
    (let [tok (bbc-peek)]
      (cond ((and (eq? (car tok) :op) (member (nth tok 1) bbc-compare-ops))
             (bbc-advance!) (loop (bbc-compare (nth tok 1) left (bbc-p-add))))
            ((and (eq? (car tok) :op) (bbc-lookup (nth tok 1) bbc-shift-ops))
             (bbc-advance!)
             (loop (bbc-num (list (bbc-second (bbc-lookup (nth tok 1) bbc-shift-ops))
                                  (bbc-value left) (bbc-value (bbc-p-add))))))
            (else left)))))

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
    ("UCASE$" bbc-ucase 1 1 :str) ("LCASE$" bbc-lcase 1 1 :str)
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

(define (bbc-p-rnd)
  ;; Unlike other unary functions, RND without parentheses is a complete call.
  (if (not (bbc-accept! :op "("))
      (bbc-num '(bbc-rnd))
      (begin
        (if (bbc-at? :op ")") (bbc-fail "RND needs one numeric argument"))
        (let [argument (bbc-p-expr)]
          (if (eq? (bbc-type argument) :str) (bbc-fail "RND needs a numeric argument"))
          (if (bbc-at? :op ",") (bbc-fail "RND needs one numeric argument"))
          (bbc-expect! :op ")" "RND closing )")
          (bbc-num (list 'bbc-rnd (bbc-value argument)))))))

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
          ((bbc-accept! :kw "RND") (bbc-p-rnd))
          ((bbc-accept! :kw "TIME") (bbc-num '(bbc-time-read)))
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
          (else (bbc-fail-assign name)))))

(define (bbc-p-time-assign)
  (bbc-expect! :kw "TIME" "TIME")
  (let [operation (cond ((bbc-accept! :op "=") #f)
                       ((bbc-accept! :op "+=") '+)
                       ((bbc-accept! :op "-=") '-)
                       (else (bbc-fail "expected =, += or -= after TIME")))
        value (bbc-value (bbc-p-expr))]
    (list 'bbc-time-set!
          (if operation (list operation '(bbc-time-read) value) value))))

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
            ((bbc-accept! :op "~") (bbc-push! items (list 'HEX (bbc-value (bbc-p-expr)))))
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

(define (bbc-p-if-branch)
  ;; A number immediately after THEN/ELSE is an implicit GOTO, not a
  ;; general numeric statement. Keep the normal jump/loop continuation code.
  (let [jump (if (bbc-at? :num #f)
                (list (list 'GOTO (nth (bbc-advance!) 1)))
                (list))]
    (append jump (bbc-p-line-stmts))))

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
        (let [then-part (bbc-p-if-branch)]
          (if (bbc-accept! :kw "ELSE")
              (append (list 'IF test) then-part (list 'ELSE) (bbc-p-if-branch))
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
        labels (list)
        ends '("WHEN" "OTHERWISE" "ENDCASE")]
    (bbc-expect! :kw "OF" "OF")
    (bbc-skip-separators)
    (while (not (bbc-accept! :kw "ENDCASE"))
      (cond ((bbc-at? :line #f)
             ;; Unlike later headers (read by bbc-p-block), the first header
             ;; has no preceding clause body to consume its line label.
             (bbc-push! labels (list 'LABEL (nth (bbc-advance!) 1))))
            ((bbc-accept! :kw "WHEN")
             (let [vals (bbc-p-value-list)]
               (bbc-push! clauses (append (list 'WHEN vals) labels (bbc-p-block ends #f)))
               (set! labels (list))))
            ((bbc-accept! :kw "OTHERWISE")
             (bbc-push! clauses (append (list 'OTHERWISE) labels (bbc-p-block ends #f)))
             (set! labels (list)))
            (else (bbc-fail "expected WHEN, OTHERWISE or ENDCASE")))
      (bbc-skip-separators))
    ;; Retain a numbered ENDCASE even for an empty CASE with no clause body.
    (if (not (null? labels))
        (bbc-push! clauses (cons 'OTHERWISE labels)))
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

;; Hook for mini-basic-ext.lisp to handle labels, DATA, DIM, GOTO, etc.
(define (bbc-ext-statement) #f)

(define (bbc-p-statement)
  (let [ext (bbc-ext-statement)]
    (if ext
        ext
        (let [tok (bbc-peek)
              kind (car tok)
              value (nth tok 1)]
          (cond ((eq? kind :star) (bbc-advance!) (list 'OSCLI value))
                ((and (eq? kind :id) (equal? value "OFF")
                      (member (car (nth bbc-toks (+ bbc-pos 1))) '(:colon :eol :eof)))
                 (bbc-advance!) (list 'CURSOR #f))
                ((eq? kind :id) (bbc-p-assign))
                ((eq? kind :proc)
                 (bbc-advance!)
                 (append (list 'PROC (string->symbol value)) (bbc-p-args)))
                ((bbc-accept! :op "=") (list 'FN= (bbc-value (bbc-p-expr))))
                ((not (eq? kind :kw)) (bbc-fail "expected a statement"))
                ((equal? value "PRINT") (bbc-advance!) (bbc-p-print))
                ((equal? value "LET")
                 (bbc-advance!)
                 (if (bbc-at? :kw "TIME") (bbc-p-time-assign) (bbc-p-assign)))
                ((equal? value "TIME") (bbc-p-time-assign))
                ((equal? value "MODE")
                 (bbc-advance!) (list 'MODE (bbc-value (bbc-p-expr))))
                ((equal? value "CLG") (bbc-advance!) (list 'CLG))
                ((member value '("CIRCLE" "RECTANGLE"))
                 (bbc-advance!)
                 (let [fill (bbc-accept! :kw "FILL")]
                   (append (list (string->symbol value) fill) (bbc-p-value-list))))
                ((equal? value "WAIT")
                 (bbc-advance!)
                 (if (bbc-at-stmt-end?) (list 'WAIT) (list 'WAIT (bbc-value (bbc-p-expr)))))
                ((equal? value "OSCLI") (bbc-advance!) (list 'OSCLI (bbc-value (bbc-p-expr))))
                ((member value '("GCOL" "MOVE" "DRAW" "PLOT" "ORIGIN"))
                 (bbc-advance!) (cons (string->symbol value) (bbc-p-value-list)))
                ((equal? value "CLS") (bbc-advance!) (list 'CLS))
                ((or (equal? value "VDU") (equal? value "ANSI"))
                 (bbc-advance!)
                 (cons (if (equal? value "VDU") 'VDU 'ANSI) (bbc-p-value-list)))
                ((or (equal? value "COLOUR") (equal? value "COLOR"))
                 (bbc-advance!)
                 (let [values (bbc-p-value-list)]
                   (if (not (member (length values) '(1 4)))
                       (bbc-fail "COLOUR takes n or n,r,g,b"))
                   (cons 'COLOUR values)))
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
                ((or (equal? value "END") (equal? value "STOP"))
                 (if (and (equal? value "END")
                          (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :kw "DEF"))
                     (bbc-fail "END DEF is not BBC BASIC; return a function value with =expression; procedures use ENDPROC"))
                 (bbc-advance!) (list 'END))
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
                (else (bbc-fail "expected a statement")))))))
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

;;; --- The same program in lispy3, SBCL and Clojure ---
;;;
;;;   (run-lispy (slurp "prog.bas"))
;;;   (run-sbcl "FOR i=1 TO 3 : PRINT i : NEXT")
;;;   (run-clojure (slurp "prog.bas"))
;;;
;;; run-sbcl and run-clojure write the reader's forms out as text for the
;;; macros in compare/sbcl and compare/clojure, with the reader's lispy3 names
;;; (quotient, =, string-append ...) renamed to the bbc- functions there, and
;;; give the text to sbcl or clojure on standard input. They give the exit code.

(define (run-lispy text)
  (eval (bbc-expand text))
  #f)

(define bbc-foreign-names
  '((= bbc=) (< bbc<) (> bbc>) (<= bbc<=) (>= bbc>=) (eq? bbc-eq?) (if bbc-if)
    (quotient bbc-quotient) (remainder bbc-remainder) (trunc bbc-trunc) (float bbc-float)
    (expt bbc-expt) (abs bbc-abs) (floor bbc-floor) (sqrt bbc-sqrt) (sin bbc-sin)
    (cos bbc-cos) (tan bbc-tan) (atan bbc-atan) (log bbc-log) (log10 bbc-log10)
    (exp bbc-exp) (pi bbc-pi) (length bbc-length) (string-append bbc-string-append)))

(define (bbc-rename sym)
  (let loop ((names bbc-foreign-names))
    (cond ((null? names) sym)
          ((eq? (car (car names)) sym) (bbc-second (car names)))
          (else (loop (cdr names))))))

(define (bbc-has? text part)
  (>= (text/find part) 0))

(define (bbc-foreign-symbol sym target)
  ;; SBCL upcases what it reads, so a BBC name with a lower-case letter goes
  ;; in |bars|; the bbc- names and and, or, not are read as written
  (let [name (symbol->string (bbc-rename sym))]
    (if (and (eq? target :sbcl)
             (not (equal? (upcase name) name))
             (not (and (>= (length name) 3) (equal? (substring name 0 3) "bbc")))
             (not (member name '("and" "or" "not"))))
        (str "|" name "|")
        name)))

(define (bbc-foreign-string s)
  (apply str (append (list "\"")
                     (map (lambda (c) (cond ((eq? c #\") "\\\"") ((eq? c #\\) "\\\\") (else c)))
                          (seq s))
                     (list "\""))))

(define (bbc-foreign-number x target)
  ;; SBCL reads 2.5 as a single float, so a float gets a d exponent
  (let [text (str x)]
    (cond ((not (eq? target :sbcl)) text)
          ((bbc-has? text "e") (str (text/replace "e" "d")))
          ((bbc-has? text ".") (str text "d0"))
          (else text))))

(define (bbc-foreign-text x target)
  ;; Code x as SBCL (target :sbcl) or Clojure (:clojure) source text
  (cond ((eq? x #t) (if (eq? target :sbcl) "t" "true"))
        ((eq? x #f) (if (eq? target :sbcl) "nil" "false"))
        ((string? x) (bbc-foreign-string x))
        ((number? x) (bbc-foreign-number x target))
        ((and (symbol? x) (equal? (substring (symbol->string x) 0 1) ":")) (symbol->string x))
        ((symbol? x) (bbc-foreign-symbol x target))
        ((null? x) "()")
        (else (str "(" (reduce (lambda (acc e) (str acc " " (bbc-foreign-text e target)))
                               (bbc-foreign-text (car x) target) (cdr x))
                   ")"))))

(define (bbc-compare-file path)
  (str lispy-home "/compare/" path))

(define (run-sbcl text)
  (run-program "sbcl" (list "--script" (bbc-compare-file "sbcl/run.lisp"))
               (bbc-foreign-text (bbc-expand text) :sbcl)))

(define (run-clojure text)
  (run-program "clojure" (list "-M" (bbc-compare-file "clojure/run.clj"))
               (bbc-foreign-text (bbc-expand text) :clojure)))
(load "mini-basic-ext")
(load "mini-basic-io")
(load "mini-basic-num")
