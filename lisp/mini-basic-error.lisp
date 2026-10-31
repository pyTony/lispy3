;;; mini-basic-error.lisp - BBC BASIC error handling for mini-basic.lisp
;;;
;;;   10 ON ERROR PRINT "Error ";ERR;" at line ";ERL : REPORT : PRINT : END
;;;   ON ERROR LOCAL PRINT REPORT$ : ENDPROC   ; inside a PROC or FN
;;;   ON ERROR OFF                             ; errors stop the program again
;;;   ERROR 100, "Too many"                    ; raise an error of your own
;;;
;;; As in BBC BASIC for SDL, an error goes to the statements after ON ERROR and
;;; the program carries on from there into the following lines. ERR is the BBC
;;; error number, ERL the numbered line where it happened (0 in a program
;;; without line numbers) and REPORT$ its message, which REPORT prints.
;;;
;;; ON ERROR becomes (ON-ERROR label stmts...) (GO end) (LABEL label) stmts...
;;; (LABEL end): an error unwinds to the body holding the label and jumps
;;; there. When that body has already finished, as for an ON ERROR inside a
;;; PROC that has returned, the program body runs the statements on their own
;;; and then ends. ON ERROR LOCAL is put back when its PROC or FN returns.
;;; Stop in Lispy Machine is never trapped.

;;; --- Run-time state ---

(define bbc-error-handler #f)   ; (label thunk) of the active ON ERROR, or #f
(define bbc-err 0)
(define bbc-erl 0)
(define bbc-report "")
(define bbc-line 0)             ; last numbered line reached, kept only when ERL is used
(define bbc-raised #f)          ; (number message) from the last ERROR statement

(define (bbc-error-reset!)
  ;; RUN forgets the previous program's ON ERROR
  (set! bbc-error-handler #f)
  (set! bbc-err 0)
  (set! bbc-erl 0)
  (set! bbc-report "")
  (set! bbc-line 0)
  (set! bbc-raised #f))

(define (bbc-error-number) bbc-err)
(define (bbc-error-line) bbc-erl)
(define (bbc-error-report) bbc-report)

;; BBC BASIC's number and message for a part of a lispy3 error message
(define bbc-error-table
  '(("division by zero" 18 "Division by zero")
    ("modulo by zero" 18 "Division by zero")
    ("index out of range" 15 "Subscript out of range")
    ("not 'complex'" 21 "-ve root")
    ("math domain error" 22 "Log range")
    ("math range error" 20 "Too big")
    ("Numerical result out of range" 20 "Too big")
    ("Number too big" 20 "Too big")
    ("Undefined symbol: PROC-" 29 "No such FN/PROC")
    ("Undefined symbol: FN-" 29 "No such FN/PROC")
    ("Undefined symbol: " 26 "No such variable")
    ("Out of DATA" 42 "Out of DATA")
    ("RETURN without GOSUB" 38 "No GOSUB")
    ("unknown label" 41 "No such line")
    ("ON range" 40 "ON range")
    ("needs strings" 6 "Type mismatch")
    ("unsupported operand" 6 "Type mismatch")
    ("not supported between" 6 "Type mismatch")
    ("has no len()" 6 "Type mismatch")))

(define (bbc-error-info message)
  ;; (number report) for an error message; other errors are number 0
  (if (and bbc-raised (equal? (bbc-second bbc-raised) message))
      bbc-raised
      (let loop ((entries bbc-error-table))
        (cond ((null? entries) (list 0 message))
              ((>= (message/find (car (car entries))) 0) (cdr (car entries)))
              (else (loop (cdr entries)))))))

(define (bbc-raise! number message)
  ;; ERROR n, message$
  (set! bbc-raised (list (bbc-int number) (str message)))
  (error (str message)))

(define (bbc-record-error! message)
  (let [info (bbc-error-info (str message))]
    (set! bbc-raised #f)
    (set! bbc-err (car info))
    (set! bbc-report (bbc-second info))
    (set! bbc-erl bbc-line)))

(define (bbc-trap message labels)
  ;; The segment a tagbody with these labels goes on at after an error, or #f
  ;; to pass the error to the enclosing body. Jumps and exits are not errors.
  (if (and bbc-error-handler (not (let [text (str message)] (text/startswith "bbc:"))))
      (let [at (get labels (car bbc-error-handler) #f)]
        (if (not at) (set! at (get labels 'bbc-error-fallback #f)))
        (if at (bbc-record-error! message))
        at)
      #f))

(define (bbc-error-fallback!)
  ;; The handler's statements, once the body that set it has finished
  ((bbc-second bbc-error-handler)))

(define (bbc-goto-missing labels)
  ;; GOTO to a line no active body has: an error ON ERROR can trap here
  (let [message (str "GOTO: unknown label " bbc-goto-target)
        at (bbc-trap message labels)]
    (if at at (error message))))

;;; --- Statements ---

(define-macro (ON-ERROR label & stmts)
  `(set! bbc-error-handler (list ',label (lambda () ,(bbc-nested-body-code stmts)))))

;; The same; a PROC or FN using it puts the previous handler back (bbc-def)
(define-macro (ON-ERROR-LOCAL label & stmts)
  `(ON-ERROR ,label ,@stmts))

(define-macro (ON-ERROR-OFF) '(set! bbc-error-handler #f))
(define-macro (REPORT) '(bbc-write bbc-report))
(define-macro (LINE n) `(set! bbc-line ,n))

;;; --- Reader ---

(set! bbc-keywords (append bbc-keywords '("ERR" "ERL" "ERROR" "REPORT" "REPORT$")))

(define bbc-track-lines #f)     ; does the program read ERL?
(define bbc-line-number 0)      ; the last line number read

(define bbc-tokenize-before-error bbc-tokenize)
(define (bbc-tokenize text)
  (let [toks (bbc-tokenize-before-error text)]
    (set! bbc-track-lines (bbc-any? (lambda (tok) (bbc-tok? tok :kw "ERL")) toks))
    (set! bbc-line-number 0)
    toks))

(define (bbc-splice stmts)
  ;; Open up (SPLICE stmt ...) and, when ERL is used, note each line number
  (let [out (list)]
    (for-each
      (lambda (s)
        (if (and (pair? s) (eq? (car s) 'SPLICE))
            (for-each (lambda (x) (bbc-push! out x)) (cdr s))
            (begin
              (bbc-push! out s)
              (if (and bbc-track-lines (pair? s) (eq? (car s) 'LABEL) (integer? (bbc-second s)))
                  (bbc-push! out (list 'LINE (bbc-second s)))))))
      stmts)
    out))

(define bbc-p-block-before-error bbc-p-block)
(define (bbc-p-block terminators fn-body)
  (bbc-splice (bbc-p-block-before-error terminators fn-body)))

(define bbc-p-line-stmts-before-error bbc-p-line-stmts)
(define (bbc-p-line-stmts)
  (bbc-splice (bbc-p-line-stmts-before-error)))

(define bbc-p-def-before-error bbc-p-def)
(define (bbc-p-def)
  ;; An error in a PROC or FN is at its own line, not the caller's
  (let [line bbc-line-number
        def (bbc-p-def-before-error)]
    (if bbc-track-lines
        (append (list (car def) (bbc-second def) (list 'LINE line)) (cdr (cdr def)))
        def)))

(define (bbc-p-on-error)
  ;; After ON ERROR: OFF, or [LOCAL] statements to the end of the line
  (if (bbc-accept! :id "OFF")
      (list 'ON-ERROR-OFF)
      (let [head (if (bbc-accept! :kw "LOCAL") 'ON-ERROR-LOCAL 'ON-ERROR)
            label (gensym "on-error")
            end (gensym "on-error-end")
            stmts (bbc-p-line-stmts)]
        (append (list 'SPLICE (append (list head label) stmts) (list 'GO end) (list 'LABEL label))
                stmts
                (list (list 'LABEL end))))))

(define bbc-statement-before-error bbc-ext-statement)
(define (bbc-ext-statement)
  (cond ((bbc-at? :line #f)
         (set! bbc-line-number (nth (bbc-peek) 1))
         (bbc-statement-before-error))
        ((and (bbc-at? :kw "ON") (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :kw "ERROR"))
         (bbc-advance!) (bbc-advance!)
         (bbc-p-on-error))
        ((bbc-accept! :kw "ERROR")
         (let [number (bbc-value (bbc-p-expr))]
           (bbc-expect! :op "," ", after the ERROR number")
           (list 'bbc-raise! number (bbc-value (bbc-p-expr)))))
        ((bbc-accept! :kw "REPORT") (list 'REPORT))
        (else (bbc-statement-before-error))))

(define bbc-primary-before-error bbc-p-primary)
(define (bbc-p-primary)
  (cond ((bbc-accept! :kw "ERR") (bbc-num (list 'bbc-error-number)))
        ((bbc-accept! :kw "ERL") (bbc-num (list 'bbc-error-line)))
        ((bbc-accept! :kw "REPORT$") (bbc-e (list 'bbc-error-report) :str))
        (else (bbc-primary-before-error))))

;; An FN that reads or sets the error state is not remembered
(define bbc-pure-fn-before-error bbc-pure-fn?)
(define (bbc-pure-fn? def vars)
  (and (not (bbc-uses? '(bbc-error-number bbc-error-line bbc-error-report bbc-raise!
                         REPORT ON-ERROR ON-ERROR-LOCAL ON-ERROR-OFF)
                       (cdr (cdr def))))
       (bbc-pure-fn-before-error def vars)))
