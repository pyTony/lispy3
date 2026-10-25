;;; mini-basic-ext.lisp - Step 3 extensions for mini-basic.lisp
;;;
;;; Step 3a: BBC labels and line numbers, DATA, READ, RESTORE
;;;
;;; A label is defined only as (name) at the start of a statement. GOTO,
;;; GOSUB, RESTORE and ON ... GOTO/GOSUB take a line number, a bare label
;;; name (never evaluated as a variable) or a calculated (expression).
;;; Step 3b: DIM and multi-dimensional arrays
;;; Step 3d: GOSUB / RETURN and ON ... GOSUB with scoped call continuations

;;; --- Run-time state & helpers for DATA / READ / RESTORE ---

(define bbc-data (vector))
(define bbc-data-ptr 0)
(define bbc-data-labels {})

(define (bbc-read!)
  (if (>= bbc-data-ptr (vector-length bbc-data))
      (error "Out of DATA")
      (let [v (vector-ref bbc-data bbc-data-ptr)]
        (set! bbc-data-ptr (+ bbc-data-ptr 1))
        v)))

(define (bbc-restore! & target)
  (if (null? target)
      (set! bbc-data-ptr 0)
      (let [lbl (car target)
            idx (get bbc-data-labels lbl #f)]
        (if idx
            (set! bbc-data-ptr idx)
            (error (str "RESTORE: unknown label " lbl))))))

;;; --- Run-time helpers for DIM and arrays ---

(define (bbc-make-array dims fill)
  ;; Allocate a multi-dimensional vector of (0..d0) x (0..d1) ...
  (let [n (+ (bbc-int (car dims)) 1)
        rest-dims (cdr dims)]
    (if (null? rest-dims)
        (make-vector n fill)
        (let [v (make-vector n #f)]
          (dotimes [i n]
            (vector-set! v i (bbc-make-array rest-dims fill)))
          v))))

(define (bbc-aref arr & indices)
  ;; Read element at (i, j, ...)
  (let loop ((cur arr) (idxs indices))
    (if (null? idxs)
        cur
        (loop (vector-ref cur (bbc-int (car idxs))) (cdr idxs)))))

(define (bbc-aset! arr val & indices)
  ;; Write val to element at (i, j, ...)
  (let loop ((cur arr) (idxs indices))
    (if (null? (cdr idxs))
        (vector-set! cur (bbc-int (car idxs)) val)
        (loop (vector-ref cur (bbc-int (car idxs))) (cdr idxs)))))

;;; --- Whole-array operations: a() = list, a() = b() op c, a() = b() . c(), SUM ---

(define (bbc-array-fill! arr values)
  ;; a() = v1, v2, ...: row by row; a single value fills every element
  (let [all (null? (cdr values)) rest values]
    (define (fill! v)
      (dotimes [i (vector-length v)]
        (cond ((vector? (vector-ref v i)) (fill! (vector-ref v i)))
              ((not (null? rest))
               (vector-set! v i (car rest))
               (if (not all) (set! rest (cdr rest)))))))
    (fill! arr)))

(define (bbc-array-op! dest op a b)
  ;; dest() = a() op b, b an array or a number; no op copies a()
  (if (not (= (vector-length dest) (vector-length a)))
      (error "Type mismatch: arrays differ in size"))
  (dotimes [i (vector-length dest)]
    (let [x (vector-ref a i)
          y (if (vector? b) (vector-ref b i) b)]
      (if (vector? x)
          (bbc-array-op! (vector-ref dest i) op x y)
          (vector-set! dest i (if op (op x y) x))))))

(define (bbc-array-sum arr)
  (let [total 0]
    (dotimes [i (vector-length arr)]
      (let [x (vector-ref arr i)]
        (set! total (+ total (if (vector? x) (bbc-array-sum x) x)))))
    total))

(define (bbc-array-sum-range arr lead lo hi)
  ;; SUM(a(i, lo TO hi)): elements lo..hi of the row a(i, ...)
  (let [row (apply bbc-aref (cons arr lead)) total 0]
    (for-each (lambda (i) (set! total (+ total (vector-ref row i))))
              (range (bbc-int lo) (+ (bbc-int hi) 1)))
    total))

;;; --- DATA items that are expressions: READ evaluates them, as BBC does ---

(define (bbc-data-expr? x) (and (pair? x) (eq? (car x) 'bbc-data-expr)))
(define (bbc-data-string x) (if (bbc-data-expr? x) (bbc-second x) (str x)))
(define (bbc-data-number x)
  (cond ((bbc-data-expr? x) ((nth x 2)))
        ((string? x) (bbc-val x))
        (else x)))

(define (bbc-data-code item vars)
  ;; A word that no statement assigns stays text, as before
  (if (and (pair? item) (eq? (car item) 'DATA-EXPR))
      (let [raw (bbc-second item) form (nth item 2)]
        (if (and (symbol? form) (not (member form vars)))
            raw
            `(list 'bbc-data-expr ,raw (lambda () ,form))))
      (list 'quote item)))

;;; --- Macros for LABEL, DATA, READ, RESTORE, DIM, AREF, ASET! ---

(define-macro (LABEL name) '#f)
(define-macro (DATA & items) '#f)

(define-macro (DIM & specs)
  `(begin
     ,@(map (lambda (spec)
              (let [var (car spec)
                    dims (cdr spec)]
                `(set! ,var (bbc-make-array (list ,@dims) ,(bbc-default var)))))
            specs)))

(define (bbc-butlast lst)
  (if (null? (cdr lst)) '() (cons (car lst) (bbc-butlast (cdr lst)))))

(define (bbc-index-code index)
  ;; Subscripts truncate; whole numbers and integer variables need no trunc
  (if (or (integer? index) (and (symbol? index) (bbc-suffix? index #\%)))
      index
      `(trunc ,index)))

(define-macro (AREF var & indices)
  `(aref ,var ,@(map bbc-index-code indices)))

(define-macro (ASET! var val & indices)
  (let [coerced (if (bbc-suffix? var #\%) `(bbc-int ,val) val)
        codes (map bbc-index-code indices)
        last (nth codes (- (length codes) 1))
        lead (bbc-butlast codes)]
    `(vector-set! (aref ,var ,@lead) ,last ,coerced)))

(define (bbc-lhs-var target)
  ;; Extract the variable symbol from either var or (AREF var i ...)
  (if (and (pair? target) (eq? (car target) 'AREF))
      (bbc-second target)
      target))

(define-macro (READ & targets)
  `(begin
     ,@(map (lambda (t)
              (let [raw (gensym "dat")
                    var (bbc-lhs-var t)
                    coerced (if (bbc-suffix? var #\$)
                                `(bbc-data-string ,raw)
                                `(bbc-data-number ,raw))]
                `(let ((,raw (bbc-read!)))
                   ,(if (and (pair? t) (eq? (car t) 'AREF))
                        `(ASET! ,var ,coerced ,@(cdr (cdr t)))
                        `(LET ,var ,coerced)))))
            targets)))

(define-macro (RESTORE & target)
  (if (null? target)
      '(bbc-restore!)
      `(bbc-restore! ,(car target))))

(define-macro (INPUT prompt question line-mode & targets)
  (let [values (gensym "input")
        kinds (map (lambda (target)
                     (let [var (bbc-lhs-var target)]
                       (cond ((bbc-suffix? var #\$) :str)
                             ((bbc-suffix? var #\%) :int)
                             (else :num)))) targets)]
    `(begin
       (bbc-write ,prompt)
       (let ((,values (basic-input-values ',kinds read-line ,line-mode ,question)))
         (set! bbc-col 0)
         ,@(map (lambda (target index)
                  (let [var (bbc-lhs-var target)
                        value `(nth ,values ,index)]
                    (if (and (pair? target) (eq? (car target) 'AREF))
                        `(ASET! ,var ,value ,@(cdr (cdr target)))
                        `(LET ,var ,value)))) targets (range (length targets)))))))

;;; --- Program-level variable, label, and DATA collection ---

(define (bbc-assigned-vars stmts)
  ;; Every variable the statements give a value to (including READ, DIM, ASET!)
  (bbc-collect '(LET FOR LOCAL READ INPUT DIM ASET! DEF-PROC DEF-FN)
               (lambda (form)
                 (cond ((member (car form) '(LET FOR ASET!)) (list (bbc-second form)))
                       ((eq? (car form) 'LOCAL) (cdr form))
                       ((eq? (car form) 'READ) (map bbc-lhs-var (cdr form)))
                       ((eq? (car form) 'INPUT) (map bbc-lhs-var (cdr (cdr (cdr (cdr form))))))
                       ((eq? (car form) 'DIM) (map car (cdr form)))
                       (else (cdr (bbc-second form)))))
               stmts '()))

(define (bbc-collect-data stmts)
  ;; Walk stmts in order, returning (data-items-list label-map)
  (let [items (list)
        labels {}]
    (define (walk x)
      (if (and (pair? x) (list? x) (not (eq? (car x) 'quote)))
          (cond ((eq? (car x) 'DATA)
                 (for-each (lambda (item) (bbc-push! items item)) (cdr x)))
                ((eq? (car x) 'LABEL)
                 (set! labels (assoc labels (bbc-second x) (length items))))
                (else
                 (for-each walk x)))))
    (for-each walk stmts)
    (list items labels)))

;;; ===================================================================
;;; Step 3c: TAGBODY / GO and GOTO / ON ... GOTO
;;; ===================================================================

(define bbc-goto-target #f)
(define bbc-gosub-handlers (list))
(define bbc-gosub-depth 0)

(define (bbc-subroutine-scope thunk)
  ;; Programs and PROC/FN bodies cannot borrow their caller's return frames.
  (let [saved-handlers bbc-gosub-handlers
        saved-depth bbc-gosub-depth]
    (set! bbc-gosub-handlers (list))
    (set! bbc-gosub-depth 0)
    (try
      (let [result (thunk)]
        (set! bbc-gosub-handlers saved-handlers)
        (set! bbc-gosub-depth saved-depth)
        result)
      (catch err
        (set! bbc-gosub-handlers saved-handlers)
        (set! bbc-gosub-depth saved-depth)
        (error err)))))

(define (bbc-gosub! target)
  (let search ((handlers bbc-gosub-handlers))
    (if (null? handlers)
        (error (str "GOSUB: unknown label " target))
        (let [entry (car handlers)
              pc (get (car entry) target #f)]
          (if pc
              (let [saved-depth bbc-gosub-depth
                    run (bbc-second entry)]
                (set! bbc-gosub-depth (+ saved-depth 1))
                (try
                  (begin
                    (run pc)
                    (error "GOSUB reached end without RETURN"))
                  (catch err
                    (set! bbc-gosub-depth saved-depth)
                    (if (equal? err "bbc:gosub-return") #f (error err)))))
              (search (cdr handlers)))))))

(define-macro (GOSUB target) `(bbc-gosub! ,target))

(define-macro (RETURN)
  '(if (> bbc-gosub-depth 0)
       (error "bbc:gosub-return")
       (error "RETURN without GOSUB")))

(define (bbc-jump! target)
  (set! bbc-goto-target target)
  (error "bbc:goto"))

(define-macro (GOTO target)
  `(bbc-jump! ,target))

(define-macro (GO target)
  `(bbc-jump! ',target))

(define (bbc-on-branch-code transfer idx targets else-stmts)
  (let [k (gensym "idx")
        n (length targets)]
    `(let ((,k (bbc-int ,idx)))
       (cond ,@(map (lambda (i)
                      `((= ,k ,(+ i 1)) (,transfer ,(nth targets i))))
                    (range n))
             ,@(if (null? else-stmts)
                   '((else (error "ON range")))
                   `((else #f ,@else-stmts)))))))

(define-macro (ON-GOTO idx targets else-stmts)
  (bbc-on-branch-code 'GOTO idx targets else-stmts))

(define-macro (ON-GOSUB idx targets else-stmts)
  (bbc-on-branch-code 'GOSUB idx targets else-stmts))

(define (bbc-split-tagbody stmts)
  ;; Split a statement list at (LABEL name) or bare symbols into
  ;; (segments-list label-to-segment-index-map)
  (let [segments (list)
        cur (list)
        labels {}
        idx 0]
    (for-each
      (lambda (s)
        (if (or (symbol? s)
                (and (pair? s) (eq? (car s) 'LABEL)))
            (let [lbl (if (symbol? s) s (bbc-second s))]
              (bbc-push! segments (cons 'begin (cons #f cur)))
              (set! cur (list))
              (set! idx (+ idx 1))
              (set! labels (assoc labels lbl idx)))
            (bbc-push! cur s)))
      stmts)
    (bbc-push! segments (cons 'begin (cons #f cur)))
    (list segments labels)))

(define (bbc-tagbody-code stmts & nested)
  ;; Compile stmts with labels and GOTOs into a TCO-safe segment loop
  (let [info (bbc-split-tagbody stmts)
        segs (car info)
        lbl-map (bbc-second info)
        n (length segs)
        pc (gensym "pc")
        tbl (gensym "lbls")
        err (gensym "err")
        nxt (gensym "nxt")
        runner (gensym "segments")
        saved (gensym "handlers")
        value (gensym "value")
        result (gensym "result")]
    `(let ((,tbl ,lbl-map) (,saved bbc-gosub-handlers))
       ;; A separate invocation keeps the caller's exact statement and loop
       ;; continuation live, including multiple GOSUBs in the same segment.
       (define (,runner ,pc)
         (let ((,value #f))
           (while (< ,pc ,n)
             (try
               (begin
                 (set! ,value
                   (cond ,@(map (lambda (i) `((= ,pc ,i) ,(nth segs i)))
                                (range n))))
                 (set! ,pc (+ ,pc 1)))
               (catch ,err
                 (if (equal? ,err "bbc:goto")
                     (let ((,nxt (get ,tbl bbc-goto-target #f)))
                       (if ,nxt
                           (set! ,pc ,nxt)
                           ,(if (null? nested)
                                '(error (str "GOTO: unknown label " bbc-goto-target))
                                '(error "bbc:goto"))))
                     (error ,err)))))
           ,value))
       (set! bbc-gosub-handlers (cons (list ,tbl ,runner) ,saved))
       (try
         (let ((,result (,runner 0)))
           (set! bbc-gosub-handlers ,saved)
           ,result)
         (catch ,err
           (set! bbc-gosub-handlers ,saved)
           (error ,err))))))

(define (bbc-nested-body-code stmts)
  ;; Each active structured body resolves its own labels. A jump to an outer
  ;; body must unwind without losing its target; only the outermost handler
  ;; reports an unknown label. Jump-free bodies keep their ordinary value.
  (if (bbc-uses? '(GOTO GO ON-GOTO GOSUB ON-GOSUB RETURN) stmts)
      (bbc-tagbody-code stmts #t)
      `(begin #f ,@stmts)))

(define-macro (tagbody & forms)
  (bbc-tagbody-code forms))

(define (bbc-body-code stmts)
  (if (bbc-uses? '(GOTO GO ON-GOTO GOSUB ON-GOSUB RETURN) stmts)
      (bbc-tagbody-code stmts)
      `(begin #f ,@stmts)))

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
        core (if (bbc-uses? '(GOSUB ON-GOSUB RETURN) body)
                 `(bbc-subroutine-scope (lambda () ,(bbc-body-code tail-body)))
                 (bbc-body-code tail-body))
        run (if (bbc-uses? '(FN= ENDPROC) tail-body)
                (bbc-catch tag core 'bbc-fn-value)
                core)
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

(define-macro (bbc-program & stmts)
  (let [vars (bbc-assigned-vars stmts)
        data-info (bbc-collect-data stmts)
        data-items (car data-info)
        data-lbls (bbc-second data-info)
        defs (map (lambda (d) (if (bbc-pure-fn? d vars) (cons 'DEF-MEMO-FN (cdr d)) d))
                  (filter bbc-def? stmts))
        main (filter (lambda (s) (not (bbc-def? s))) stmts)
        run (if (bbc-uses? '(GOSUB ON-GOSUB RETURN) stmts)
                `(bbc-subroutine-scope (lambda () ,(bbc-body-code main)))
                (bbc-body-code main))]
    `(begin
       ,@(map (lambda (v) `(define ,v ,(bbc-default v))) vars)
       (set! bbc-data (list->vector (list ,@(map (lambda (item) (bbc-data-code item vars)) data-items))))
       (set! bbc-data-ptr 0)
       (set! bbc-data-labels ,data-lbls)
       ,@defs
       (set! bbc-col 0)
       ;; Closing a MODE window ends the program like END (see graphics bindings)
       ,(if (bbc-uses? '(END MODE) stmts) (bbc-catch "bbc:end" run #f) run)
       #f)))
       
;;; --- Parser extensions for (label), DATA, READ, RESTORE, DIM, arrays ---

(define (bbc-at-label-name?)
  (member (car (bbc-peek)) '(:id :proc :fn)))

(define (bbc-p-label-name)
  ;; The name in a (label) definition or after a jump keyword
  (if (bbc-at-label-name?)
      (bbc-var (nth (bbc-advance!) 1))
      (bbc-fail "expected a label name")))

(define (bbc-p-jump-target)
  ;; A line number, a bare label name, or a calculated (expression)
  (cond ((bbc-at? :num #f) (nth (bbc-advance!) 1))
        ((bbc-at-label-name?) (list 'quote (bbc-p-label-name)))
        ((bbc-at? :op "(") (bbc-value (bbc-p-expr)))
        (else (bbc-fail "expected a line number, label or (expression)"))))

(define (bbc-data-item-end? offset)
  (let [tok (nth bbc-toks (+ bbc-pos offset))]
    (or (bbc-tok? tok :op ",") (member (car tok) '(:colon :eol :eof)))))

(define (bbc-tokens-text start end)
  ;; Source-like text of tokens start..end-1, for READ into a string
  (str/join (map (lambda (tok)
                   (cond ((> (length tok) 3) (nth tok 3))
                         ((eq? (car tok) :str) (str "\"" (nth tok 1) "\""))
                         (else (str (nth tok 1)))))
                 (map (lambda (i) (nth bbc-toks i)) (range start end)))))

(define (bbc-p-data-item)
  (cond ((and (bbc-at? :num #f) (bbc-data-item-end? 1)) (nth (bbc-advance!) 1))
        ((and (bbc-at? :op "-") (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :num #f) (bbc-data-item-end? 2))
         (bbc-advance!) (- (nth (bbc-advance!) 1)))
        ((and (bbc-at? :op "+") (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :num #f) (bbc-data-item-end? 2))
         (bbc-advance!) (nth (bbc-advance!) 1))
        ((bbc-at? :str #f) (nth (bbc-advance!) 1))
        ((and (bbc-at? :kw #f) (bbc-data-item-end? 1))
         (let [tok (bbc-advance!)]
           (nth tok (if (> (length tok) 3) 3 1))))
        ((bbc-data-item-end? 0) "")
        (else
         ;; t, -p, 2*q ...: READ evaluates it when it reads the item
         (let [start bbc-pos
               e (bbc-value (bbc-p-expr))]
           (list 'DATA-EXPR (bbc-tokens-text start bbc-pos) e)))))

(define (bbc-p-data)
  (let [items (list (bbc-p-data-item))]
    (while (bbc-accept! :op ",")
      (bbc-push! items (bbc-p-data-item)))
    (cons 'DATA items)))

(define (bbc-p-restore)
  (if (bbc-at-stmt-end?)
      (list 'RESTORE)
      (list 'RESTORE (bbc-p-jump-target))))

(define (bbc-p-dim-item)
  (let [tok (bbc-expect! :id #f "an array name")
        var (bbc-array-var (nth tok 1))]
    (if (not (bbc-at? :op "("))
        (bbc-fail "expected ( after array name in DIM"))
    (cons var (bbc-p-args))))

(define (bbc-p-dim)
  (let [specs (list (bbc-p-dim-item))]
    (while (bbc-accept! :op ",")
      (bbc-push! specs (bbc-p-dim-item)))
    (cons 'DIM specs)))

(define (bbc-array-var name)
  ;; a() and a are different variables in BBC BASIC
  (bbc-var (str "array-" name)))

(define (bbc-p-target)
  ;; Parse either a scalar variable or an array element var(i, ...)
  (let [tok (bbc-expect! :id #f "a variable")
        name (nth tok 1)
        var (if (bbc-at? :op "(") (bbc-array-var name) (bbc-var name))]
    (cond ((and (bbc-at? :op "(") (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :op ")"))
           (bbc-advance!) (bbc-advance!)
           (list (list 'WHOLE var) name var))
          ((bbc-at? :op "(")
           (list (append (list 'AREF var) (bbc-p-args)) name var))
          (else (list var name var)))))

(define (bbc-at-whole-array?)
  (and (bbc-at? :id #f)
       (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :op "(")
       (bbc-tok? (nth bbc-toks (+ bbc-pos 2)) :op ")")))

(define (bbc-p-whole-array)
  (let [tok (bbc-advance!)]
    (bbc-advance!) (bbc-advance!)
    (bbc-array-var (nth tok 1))))

(define (bbc-p-array-assign dest)
  ;; dest() = b() . c() | b() [op b()/expr] | value, value, ...
  (if (bbc-at-whole-array?)
      (let [a (bbc-p-whole-array)]
        (cond ((bbc-accept! :op ".")
               (if (not (bbc-at-whole-array?)) (bbc-fail "expected an array() after ."))
               (list 'mat* a (bbc-p-whole-array) dest))
              ((bbc-at-stmt-end?) (list 'bbc-array-op! dest #f a #f))
              (else
               (let [op (cond ((bbc-accept! :op "+") '+)
                              ((bbc-accept! :op "-") '-)
                              ((bbc-accept! :op "*") '*)
                              ((bbc-accept! :op "/") '(lambda (x y) (/ (float x) y)))
                              (else (bbc-fail "expected . + - * or / after the array")))
                     b (if (bbc-at-whole-array?) (bbc-p-whole-array) (bbc-value (bbc-p-expr)))]
                 (list 'bbc-array-op! dest op a b)))))
      (list 'bbc-array-fill! dest (cons 'list (bbc-p-value-list)))))

(define (bbc-p-assign)
  (let [target-info (bbc-p-target)
        lhs (car target-info)
        name (nth target-info 1)
        var (nth target-info 2)
        is-arr (and (pair? lhs) (eq? (car lhs) 'AREF))]
    (cond ((and (pair? lhs) (eq? (car lhs) 'WHOLE))
           (bbc-expect! :op "=" "= after the whole array")
           (bbc-p-array-assign var))
          ((bbc-accept! :op "=")
           (let [rhs (bbc-value (bbc-p-expr))]
             (if is-arr
                 (append (list 'ASET! var rhs) (cdr (cdr lhs)))
                 (list 'LET var rhs))))
          ((bbc-accept! :op "+=")
           (let [op-sym (if (bbc-string-name? name) 'string-append '+)
                 rhs (bbc-value (bbc-p-expr))]
             (if is-arr
                 (let [idxs (map (lambda (_) (gensym "idx")) (cdr (cdr lhs)))]
                   `(let ,(map list idxs (cdr (cdr lhs)))
                      (ASET! ,var (,op-sym (AREF ,var ,@idxs) ,rhs) ,@idxs)))
                 (list 'LET var (list op-sym var rhs)))))
          ((bbc-accept! :op "-=")
           (let [rhs (bbc-value (bbc-p-expr))]
             (if is-arr
                 (let [idxs (map (lambda (_) (gensym "idx")) (cdr (cdr lhs)))]
                   `(let ,(map list idxs (cdr (cdr lhs)))
                      (ASET! ,var (- (AREF ,var ,@idxs) ,rhs) ,@idxs)))
                 (list 'LET var (list '- var rhs)))))
          (else (bbc-fail-assign name)))))

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
           (let [var (if (bbc-at? :op "(") (bbc-array-var value) (bbc-var value))
                 vtype (if (bbc-string-name? value) :str :num)]
             (if (bbc-at? :op "(")
                 (bbc-e (append (list 'AREF var) (bbc-p-args)) vtype)
                 (bbc-e var vtype))))
          ((eq? kind :fn)
           (bbc-advance!)
           (bbc-e (append (list 'FN (string->symbol value)) (bbc-p-args))
                  (if (bbc-string-name? value) :str :num)))
          ((bbc-accept! :kw "TRUE") (bbc-num -1))
          ((bbc-accept! :kw "FALSE") (bbc-num 0))
          ((bbc-accept! :kw "PI") (bbc-num 'pi))
          ((bbc-accept! :kw "RND") (bbc-p-rnd))
          ((bbc-accept! :kw "TIME") (bbc-num '(bbc-time-read)))
          ((bbc-accept! :kw "SUM") (bbc-num (bbc-p-sum)))
          ((and (eq? kind :kw) (bbc-lookup value bbc-functions))
           (bbc-advance!)
           (bbc-p-function (bbc-lookup value bbc-functions)))
          (else (bbc-fail "expected an expression")))))

(define (bbc-p-sum)
  ;; SUM(a()) or SUM(a(i, lo TO hi))
  (bbc-expect! :op "(" "( after SUM")
  (let [var (bbc-array-var (nth (bbc-expect! :id #f "an array name") 1))
        result #f]
    (bbc-expect! :op "(" "( after the array name")
    (if (bbc-accept! :op ")")
        (set! result (list 'bbc-array-sum var))
        (let [lead (list) lo #f hi #f]
          (while (not hi)
            (let [e (bbc-value (bbc-p-expr))]
              (cond ((bbc-accept! :kw "TO") (set! lo e) (set! hi (bbc-value (bbc-p-expr))))
                    ((bbc-accept! :op ",") (bbc-push! lead e))
                    (else (bbc-fail "SUM of part of an array needs a range: a(i, lo TO hi)")))))
          (bbc-expect! :op ")" ")")
          (set! result (list 'bbc-array-sum-range var (cons 'list lead) lo hi))))
    (bbc-expect! :op ")" ")")
    result))

(define (bbc-p-read)
  (let [targets (list (car (bbc-p-target)))]
    (while (bbc-accept! :op ",")
      (bbc-push! targets (car (bbc-p-target))))
    (cons 'READ targets)))

(define (bbc-p-input)
  (let [line-mode (bbc-accept! :id "LINE")
        prompt ""
        question #t
        targets (list)]
    (if (bbc-at? :str #f)
        (begin
          (set! prompt (nth (bbc-advance!) 1))
          (set! question (or (bbc-accept! :op ",") (bbc-accept! :op ";")))))
    (define (target)
      (let [info (bbc-p-target)]
        (if (and line-mode (not (bbc-string-name? (nth info 1))))
            (bbc-fail "INPUT LINE requires a string variable"))
        (car info)))
    (bbc-push! targets (target))
    (while (bbc-accept! :op ",") (bbc-push! targets (target)))
    (append (list 'INPUT prompt question line-mode) targets)))

(define (bbc-p-block terminators fn-body)
  ;; Statements up to a keyword in terminators; a (LABEL ...) may be followed
  ;; directly by any statement on the same line without needing a colon.
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
              (if (not (or (bbc-at-stmt-end?)
                           (bbc-at? :kw #f)
                           (and (pair? stmt) (eq? (car stmt) 'LABEL))))
                  (bbc-fail "unexpected text after the statement"))))))
    stmts))
(define (bbc-p-goto)
  (list 'GOTO (bbc-p-jump-target)))

(define (bbc-p-on)
  (let [idx (bbc-value (bbc-p-expr))
        transfer (cond ((bbc-accept! :kw "GOTO") 'ON-GOTO)
                       ((bbc-accept! :kw "GOSUB") 'ON-GOSUB)
                       (else #f))]
    (if transfer
        (let [targets (list (bbc-p-jump-target))]
          (while (bbc-accept! :op ",")
            (bbc-push! targets (bbc-p-jump-target)))
          (let [else-part (if (bbc-accept! :kw "ELSE") (bbc-p-line-stmts) (list))]
            (list transfer idx targets else-part)))
        (bbc-fail "expected GOTO or GOSUB after ON expression"))))

(define (bbc-ext-statement)
  (let [tok (bbc-peek)
        kind (car tok)
        value (nth tok 1)]
    (cond ((eq? kind :line)
           (bbc-advance!)
           (list 'LABEL value))
          ((bbc-accept! :op "(")
           (let [lbl (bbc-p-label-name)]
             (bbc-expect! :op ")" ") after label")
             (list 'LABEL lbl)))
          ((not (eq? kind :kw)) #f)
          ((equal? value "DATA") (bbc-advance!) (bbc-p-data))
          ((equal? value "READ") (bbc-advance!) (bbc-p-read))
          ((equal? value "INPUT") (bbc-advance!) (bbc-p-input))
          ((equal? value "RESTORE") (bbc-advance!) (bbc-p-restore))
          ((equal? value "DIM") (bbc-advance!) (bbc-p-dim))
          ((equal? value "GOTO") (bbc-advance!) (bbc-p-goto))
          ((equal? value "GOSUB")
           (bbc-advance!) (list 'GOSUB (bbc-p-jump-target)))
          ((equal? value "RETURN") (bbc-advance!) (list 'RETURN))
          ((equal? value "ON")
           (bbc-advance!)
           (if (bbc-at-stmt-end?) (list 'CURSOR #t) (bbc-p-on)))
          (else #f))))
