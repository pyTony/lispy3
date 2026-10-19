;;;; mini-basic.lisp for SBCL - the lispy3 mini-basic macros in Common Lisp
;;;;
;;;; The same statements as lisp/mini-basic.lisp, written for a side by side
;;;; comparison. Programs are read in the BBC-USER package, which sees the
;;;; statements and only the arithmetic and comparisons of Common Lisp, so a
;;;; BBC variable may be called LIST or T without touching the CL package.
;;;;
;;;; Where lispy3 has to build things, Common Lisp has them already:
;;;;   - special variables give PROC and FN parameters and LOCAL their
;;;;     dynamic scope, so there is nothing to save and restore by hand;
;;;;   - BLOCK / RETURN-FROM give ENDPROC, FN= and the EXIT- forms, and
;;;;     CATCH / THROW gives END, so no early exit goes through an error.
;;;;
;;;; Run a program with:  sbcl --script compare/sbcl/run.lisp program.lisp

(defpackage :mini-basic
  (:use :cl)
  (:shadow #:print #:if #:let #:case)
  (:export #:bbc-program #:let #:print #:if #:for #:repeat #:while #:case
           #:def-proc #:def-fn #:proc #:fn #:fn= #:local #:endproc #:end
           #:exit-for #:exit-repeat #:exit-while #:true #:false
           ;; What the BBC BASIC text reader writes for operators and functions
           #:bbc= #:bbc< #:bbc> #:bbc<= #:bbc>= #:bbc-eq? #:bbc-if
           #:bbc-quotient #:bbc-remainder #:bbc-trunc #:bbc-float #:bbc-expt
           #:bbc-abs #:bbc-floor #:bbc-sqrt #:bbc-sin #:bbc-cos #:bbc-tan #:bbc-atan
           #:bbc-log #:bbc-log10 #:bbc-exp #:bbc-pi #:bbc-length #:bbc-string-append
           #:bbc-and #:bbc-or #:bbc-eor #:bbc-not #:bbc-sgn #:bbc-val #:bbc-str
           #:bbc-asc #:bbc-chr #:bbc-left #:bbc-right #:bbc-mid #:bbc-instr))

(defpackage :mini-basic.impl
  (:use :cl))

(defpackage :bbc-user
  (:use :mini-basic)
  (:import-from :cl #:+ #:- #:* #:/ #:< #:> #:<= #:>= #:= #:/= #:mod #:not #:and #:or))

(in-package :mini-basic.impl)
(import 'mini-basic:bbc-str)

;;; --- Run-time support ---

(defparameter mini-basic:true -1)
(defparameter mini-basic:false 0)

(defun bbc-true-p (x)
  (not (or (null x) (and (numberp x) (zerop x)))))

(defun bbc-int (x)
  (values (truncate x)))

(defun bbc-equal (a b)
  (cl:if (and (numberp a) (numberp b)) (= a b) (equal a b)))

;; The output column, for :comma zones, TAB and PRINT's right-justified numbers
(defvar *col* 0)
(defparameter *zone-width* 10)

(defun bbc-write (text)
  (write-string text)
  (cl:let ((nl (position #\Newline text :from-end t)))
    (setf *col* (cl:if nl (- (length text) nl 1) (+ *col* (length text))))))

(defun bbc-newline ()
  (terpri)
  (setf *col* 0))

(defun bbc-spaces (n)
  (when (> n 0) (bbc-write (make-string n :initial-element #\Space))))

(defun bbc-zone ()
  (bbc-spaces (mod (- *zone-width* (mod *col* *zone-width*)) *zone-width*)))

(defun bbc-tab (n)
  (when (> *col* n) (bbc-newline))
  (bbc-spaces (- n *col*)))

(defun bbc-tab-xy (x y)
  (declare (ignore y))
  ;; Without a screen, TAB(x,y) can only move along the line
  (bbc-tab x))

(defun strip-zeros (text)
  (cl:let ((dot (position #\. text)))
    (cl:if dot
        (string-right-trim "." (string-right-trim "0" text))
        text)))

(defun mini-basic:bbc-str (x)
  ;; A number as BBC BASIC prints it with the default @%: up to 9 significant digits
  (cond ((eq x t) "-1")
        ((null x) "0")
        ((integerp x) (princ-to-string x))
        (t
         (cl:let* ((d (float x 1d0))
                   (e-text (format nil "~,8,,,,,'EE" d))
                   (e-pos (position #\E e-text))
                   (exponent (parse-integer e-text :start (1+ e-pos))))
           (cl:if (<= -4 exponent 8)
               (strip-zeros (format nil "~,vF" (- 8 exponent) d))
               (format nil "~aE~d" (strip-zeros (subseq e-text 0 e-pos)) exponent))))))

(defun bbc-print-value (v justify)
  (cl:if (stringp v)
      (bbc-write v)
      (cl:let ((text (bbc-str v)))
        (bbc-write (cl:if (and justify (< (length text) *zone-width*))
                          (format nil "~v@a" *zone-width* text)
                          text)))))

;;; --- Operators and functions, as the BBC BASIC text reader writes them ---
;;; The reader in lisp/mini-basic.lisp writes lispy3 code; compare/run_basic.py
;;; renames its lispy3 names (quotient, =, string-append ...) to these.

(defun mini-basic:bbc= (a b) (cl:if (stringp a) (string= a b) (= a b)))
(defun mini-basic:bbc< (a b) (cl:if (stringp a) (and (string< a b) t) (< a b)))
(defun mini-basic:bbc> (a b) (cl:if (stringp a) (and (string> a b) t) (> a b)))
(defun mini-basic:bbc<= (a b) (cl:if (stringp a) (and (string<= a b) t) (<= a b)))
(defun mini-basic:bbc>= (a b) (cl:if (stringp a) (and (string>= a b) t) (>= a b)))
(defun mini-basic:bbc-eq? (a b) (eq a b))
(defmacro mini-basic:bbc-if (test then else) `(cl:if ,test ,then ,else))
(defun mini-basic:bbc-trunc (x) (values (truncate x)))
(defun mini-basic:bbc-quotient (a b) (values (truncate a b)))
(defun mini-basic:bbc-remainder (a b) (rem a b))
(defun mini-basic:bbc-float (x) (float x 1d0))
(defun mini-basic:bbc-expt (a b) (expt a b))
(defun mini-basic:bbc-abs (x) (abs x))
(defun mini-basic:bbc-floor (x) (values (floor x)))
(defun mini-basic:bbc-sqrt (x) (sqrt (float x 1d0)))
(defun mini-basic:bbc-sin (x) (sin (float x 1d0)))
(defun mini-basic:bbc-cos (x) (cos (float x 1d0)))
(defun mini-basic:bbc-tan (x) (tan (float x 1d0)))
(defun mini-basic:bbc-atan (x) (atan (float x 1d0)))
(defun mini-basic:bbc-log (x) (log (float x 1d0)))
(defun mini-basic:bbc-log10 (x) (log (float x 1d0) 10))
(defun mini-basic:bbc-exp (x) (exp (float x 1d0)))
(defparameter mini-basic:bbc-pi pi)
(defun mini-basic:bbc-length (s) (length s))
(defun mini-basic:bbc-string-append (a b) (concatenate 'string a b))
(defun mini-basic:bbc-and (a b) (logand (truncate a) (truncate b)))
(defun mini-basic:bbc-or (a b) (logior (truncate a) (truncate b)))
(defun mini-basic:bbc-eor (a b) (logxor (truncate a) (truncate b)))
(defun mini-basic:bbc-not (a) (lognot (truncate a)))
(defun mini-basic:bbc-sgn (x) (signum (truncate (signum x))))
(defun mini-basic:bbc-val (s)
  (cl:let ((n (ignore-errors (cl:let ((*read-default-float-format* 'double-float)
                                      (*read-eval* nil))
                               (read-from-string s)))))
    (cl:if (realp n) n 0)))
(defun mini-basic:bbc-asc (s) (cl:if (= (length s) 0) -1 (char-code (char s 0))))
(defun mini-basic:bbc-chr (n) (string (code-char (truncate n))))
(defun mini-basic:bbc-left (s n) (subseq s 0 (max 0 (min (truncate n) (length s)))))
(defun mini-basic:bbc-right (s n)
  (cl:let ((l (length s))) (subseq s (max 0 (- l (truncate n))) l)))
(defun mini-basic:bbc-mid (s p &optional n)
  (cl:let* ((l (length s))
            (start (max 0 (min l (- (truncate p) 1))))
            (end (cl:if n (max start (min l (+ start (truncate n)))) l)))
    (subseq s start end)))
(defun mini-basic:bbc-instr (s target &optional start)
  (cl:let ((pos (search target s :start2 (cl:if start (max 0 (min (length s) (- (truncate start) 1))) 0))))
    (cl:if pos (1+ pos) 0)))

;;; --- Helpers the macros use while they expand ---

(defun marker-p (x name)
  ;; Markers such as ELSE and STEP are compared by name, from any package
  (and (symbolp x) (string= (symbol-name x) name)))

(defun form-p (x name)
  (and (consp x) (marker-p (car x) name)))

(defun split-at (forms name)
  ;; (values before after) around the first marker; after is :none without one
  (cl:let ((pos (position-if (lambda (f) (marker-p f name)) forms)))
    (cl:if pos
        (values (subseq forms 0 pos) (subseq forms (1+ pos)))
        (values forms :none))))

(defun suffix-p (var ch)
  (cl:let ((s (symbol-name var)))
    (and (> (length s) 0) (char= (char s (1- (length s))) ch))))

(defun bbc-default (var)
  (cl:if (suffix-p var #\$) "" 0))

(defun collect-forms (names pick x)
  ;; Gather (pick form) from every form in x whose head is one of names
  (cl:let ((found '()))
    (labels ((walk (x)
               (when (and (consp x) (not (eq (car x) 'quote)))
                 (when (some (lambda (n) (form-p x n)) names)
                   (dolist (v (funcall pick x)) (pushnew v found)))
                 (loop for rest on x
                       while (consp rest)
                       do (walk (car rest))))))
      (walk x))
    (nreverse found)))

(defun assigned-vars (stmts)
  ;; Every variable the statements give a value to
  (collect-forms '("LET" "FOR" "LOCAL" "DEF-PROC" "DEF-FN")
                 (lambda (form)
                   (cond ((or (form-p form "LET") (form-p form "FOR")) (list (second form)))
                         ((form-p form "LOCAL") (cdr form))
                         (t (cdr (second form)))))
                 stmts))

(defun def-p (form)
  (or (form-p form "DEF-PROC") (form-p form "DEF-FN")))

(defparameter *boolean-heads* '(< > <= >= = /= not null eq eql equal zerop
                                mini-basic:bbc= mini-basic:bbc< mini-basic:bbc>
                                mini-basic:bbc<= mini-basic:bbc>= mini-basic:bbc-eq?))

(defun bbc-test (test)
  ;; Code for a BBC test; Lisp comparisons already give T or NIL
  (cl:if (and (consp test) (member (car test) *boolean-heads*))
      test
      `(bbc-true-p ,test)))

(defun def-name (kind name)
  (intern (format nil "~a-~a" kind (symbol-name name)) (symbol-package name)))

;;; --- Statements ---

(defmacro mini-basic:let (var exp)
  (cl:if (suffix-p var #\%)
      `(setf ,var (bbc-int ,exp))
      `(setf ,var ,exp)))

(defun print-code (items justify)
  ;; :semi stops right-justifying numbers, :comma starts it again
  (cl:if (null items)
      (list '(bbc-newline))
      (cl:let ((item (car items))
               (more (cdr items)))
        (cond ((eq item :semi)
               (cl:if (null more) '() (print-code more nil)))
              ((eq item :comma)
               (cons '(bbc-zone) (cl:if (null more) '() (print-code more t))))
              ((eq item :nl)
               (cons '(bbc-newline) (print-code more justify)))
              ((form-p item "TAB")
               (cons (cl:if (cddr item)
                            `(bbc-tab-xy ,@(cdr item))
                            `(bbc-tab ,(second item)))
                     (print-code more justify)))
              ((form-p item "SPC")
               (cons `(bbc-spaces ,(second item)) (print-code more justify)))
              (t
               (cons `(bbc-print-value ,item ,justify) (print-code more justify)))))))

(defmacro mini-basic:print (&rest items)
  `(progn ,@(print-code items t)))

(defmacro mini-basic:if (test &rest body)
  (multiple-value-bind (then else) (split-at body "ELSE")
    `(cl:if ,(bbc-test test)
            (progn ,@then)
            ,@(unless (eq else :none) `((progn ,@else))))))

(defmacro mini-basic:for (var from to &rest more)
  (cl:let* ((has-step (marker-p (car more) "STEP"))
            (step (cl:if has-step (second more) 1))
            (body (cl:if has-step (cddr more) more))
            (lim (gensym "LIM"))
            (st (gensym "STEP"))
            (done (cond ((not (numberp step)) `(cl:if (< ,st 0) (< ,var ,lim) (> ,var ,lim)))
                        ((< step 0) `(< ,var ,lim))
                        (t `(> ,var ,lim)))))
    `(progn
       (mini-basic:let ,var ,from)
       (cl:let ((,lim ,to) (,st ,step))
         (block exit-for
           (loop
             ,@body
             (mini-basic:let ,var (+ ,var ,st))
             (when ,done (return-from exit-for))))))))

(defmacro mini-basic:repeat (&rest body)
  (multiple-value-bind (stmts until) (split-at body "UNTIL")
    `(block exit-repeat
       (loop
         ,@stmts
         (when ,(bbc-test (car until)) (return-from exit-repeat))))))

(defmacro mini-basic:while (test &rest body)
  `(block exit-while
     (loop
       (unless ,(bbc-test test) (return-from exit-while))
       ,@body)))

(defmacro mini-basic:case (exp &rest clauses)
  (cl:let ((v (gensym "CASE")))
    `(cl:let ((,v ,exp))
       (cond ,@(mapcar (lambda (clause)
                         (cl:if (form-p clause "OTHERWISE")
                             `(t nil ,@(cdr clause))
                             `((or ,@(mapcar (lambda (w) `(bbc-equal ,v ,w)) (second clause)))
                               nil ,@(cddr clause))))
                       clauses)))))

(defmacro mini-basic:exit-for () '(return-from exit-for))
(defmacro mini-basic:exit-repeat () '(return-from exit-repeat))
(defmacro mini-basic:exit-while () '(return-from exit-while))
(defmacro mini-basic:end () '(throw 'end nil))
(defmacro mini-basic:endproc () '(return-from proc nil))
(defmacro mini-basic:fn= (exp) `(return-from fn ,exp))

(defmacro mini-basic:local (&rest vars)
  `(progn ,@(mapcar (lambda (var) `(setf ,var ,(bbc-default var))) vars)))

(defmacro mini-basic:proc (name &rest args) `(,(def-name "PROC" name) ,@args))
(defmacro mini-basic:fn (name &rest args) `(,(def-name "FN" name) ,@args))

(defun def-code (kind head body)
  ;; The parameters and LOCAL variables are special, so LET binds them dynamically
  (cl:let* ((parms (cdr head))
            (args (mapcar (lambda (p) (gensym (symbol-name p))) parms))
            (locals (set-difference (collect-forms '("LOCAL") #'cdr body) parms)))
    `(defun ,(def-name kind (car head)) ,args
       (cl:let (,@(mapcar #'list parms args)
                ,@(mapcar (lambda (v) (list v v)) locals))
         (declare (special ,@parms ,@locals))
         (block ,(cl:if (string= kind "FN") 'fn 'proc)
           ,@body)))))

(defmacro mini-basic:def-proc (head &rest body) (def-code "PROC" head body))
(defmacro mini-basic:def-fn (head &rest body) (def-code "FN" head body))

;;; --- A whole program ---

(defmacro mini-basic:bbc-program (&rest stmts)
  (cl:let ((vars (assigned-vars stmts)))
    ;; Proclaim before the code below is compiled, so every use is dynamic
    (proclaim `(special ,@vars))
    `(progn
       ,@(mapcar (lambda (v) `(defparameter ,v ,(bbc-default v))) vars)
       ,@(remove-if-not #'def-p stmts)
       (setf *col* 0)
       (catch 'end ,@(remove-if #'def-p stmts))
       nil)))
