;;;; mini_basic.clj - the lispy3 mini-basic macros in Clojure
;;;;
;;;; The same statements as lisp/mini-basic.lisp, written for a side by side
;;;; comparison. Programs are read in the bbc-user namespace, which sees the
;;;; statements and only the arithmetic and comparisons of clojure.core.
;;;;
;;;; Every BBC variable is a ^:dynamic var. The program runs inside one
;;;; binding of all of them, so set! can change them, and PROC and FN
;;;; parameters and LOCAL are nested bindings: dynamic scope as in BBC BASIC.
;;;; Clojure has no BLOCK / RETURN-FROM, so ENDPROC, FN=, the EXIT- forms and
;;;; END throw, as in lispy3, and only where the code contains one; an FN=
;;;; result in tail position is a plain value.
;;;;
;;;; Run a program with:
;;;;   java -cp "clojure.jar:spec.alpha.jar:core.specs.alpha.jar" clojure.main compare/clojure/run.clj program.lisp

(ns mini-basic
  (:refer-clojure :exclude [print]))

;;; --- Run-time support ---

(def TRUE -1)
(def FALSE 0)

(defn bbc-true? [x]
  (not (or (nil? x) (false? x) (and (number? x) (zero? x)))))

(defn bbc-int [x]
  (if (integer? x) x (long x)))

;; Typed variables: A% 32-bit, A%% 64-bit, A& a byte, A# a float
(defn bbc-in-range [x bits]
  (let [n (bbc-int x)
        top (.shiftLeft BigInteger/ONE (dec bits))]
    (if (and (>= n (- top)) (< n top))
      (long n)
      (throw (ex-info "Number too big" {})))))

(defn bbc-int32 [x] (bbc-in-range x 32))
(defn bbc-int64 [x] (bbc-in-range x 64))
(defn bbc-byte [x] (bit-and (long (bbc-int x)) 255))

(defn bbc-equal [a b]
  (if (and (number? a) (number? b)) (== a b) (= a b)))

(defn bbc-exit [tag value]
  (throw (ex-info "bbc exit" {::exit tag ::value value})))

(defn bbc-exit-value
  "The value an exit carries if it is the one for tag, else rethrow the exception."
  [tag e]
  (if (= tag (::exit (ex-data e)))
    (::value (ex-data e))
    (throw e)))

;; The output column, for :comma zones, TAB and PRINT's right-justified numbers
(def col (atom 0))
(def zone-width 10)

(defn bbc-write [^String text]
  (.write *out* text)
  (let [nl (.lastIndexOf text "\n")]
    (if (neg? nl)
      (swap! col + (count text))
      (reset! col (- (count text) nl 1)))))

(defn bbc-newline []
  (.write *out* "\n")
  (reset! col 0))

(defn bbc-spaces [n]
  (when (pos? n) (bbc-write (apply str (repeat n \space)))))

(defn bbc-zone []
  (bbc-spaces (mod (- zone-width (mod @col zone-width)) zone-width)))

(defn bbc-tab [n]
  (when (> @col n) (bbc-newline))
  (bbc-spaces (- n @col)))

(defn bbc-tab-xy [x _y]
  ;; Without a screen, TAB(x,y) can only move along the line
  (bbc-tab x))

(defn bbc-str
  "A number as BBC BASIC prints it with the default @%: up to 9 significant digits."
  [x]
  (cond (true? x) "-1"
        (false? x) "0"
        (integer? x) (str x)
        (zero? x) "0"
        :else
        (let [bd (.stripTrailingZeros (.round (bigdec (double x)) (java.math.MathContext. 9)))
              exponent (- (.precision bd) (.scale bd) 1)]
          (if (<= -4 exponent 8)
            (.toPlainString bd)
            (str (.toPlainString (.movePointLeft bd exponent)) "E" exponent)))))

(defn bbc-print-value [v justify]
  (if (string? v)
    (bbc-write v)
    (let [text (bbc-str v)]
      (bbc-write (if justify (format (str "%" zone-width "s") text) text)))))

;;; --- Operators and functions, as the BBC BASIC text reader writes them ---
;;; The reader in lisp/mini-basic.lisp writes lispy3 code; compare/run_basic.py
;;; renames its lispy3 names (quotient, =, string-append ...) to these.

(defn- compare-values [a b] (if (string? a) (compare a b) (compare (double a) (double b))))
(defn bbc= [a b] (if (string? a) (= a b) (== a b)))
(defn bbc< [a b] (neg? (compare-values a b)))
(defn bbc> [a b] (pos? (compare-values a b)))
(defn bbc<= [a b] (not (pos? (compare-values a b))))
(defn bbc>= [a b] (not (neg? (compare-values a b))))
(defn bbc-eq? [a b] (= a b))
(defmacro bbc-if [test then else] `(if ~test ~then ~else))
(defn bbc-trunc [x] (if (integer? x) x (long x)))
(defn bbc-quotient [a b] (quot a b))
(defn bbc-remainder [a b] (rem a b))
(defn bbc-float [x] (double x))
(defn bbc-expt [a b]
  (if (and (integer? a) (integer? b) (not (neg? b)))
    (reduce *' 1 (repeat b a))
    (Math/pow a b)))
(defn bbc-abs [x] (if (neg? x) (- x) x))
(defn bbc-floor [x] (if (integer? x) x (long (Math/floor x))))
(defn bbc-sqrt [x] (Math/sqrt x))
(defn bbc-sin [x] (Math/sin x))
(defn bbc-cos [x] (Math/cos x))
(defn bbc-tan [x] (Math/tan x))
(defn bbc-atan [x] (Math/atan x))
(defn bbc-log [x] (Math/log x))
(defn bbc-log10 [x] (Math/log10 x))
(defn bbc-exp [x] (Math/exp x))
(def bbc-pi Math/PI)
(defn bbc-length [^String s] (.length s))
(defn bbc-string-append [a b] (str a b))
(defn bbc-and [a b] (bit-and (bbc-trunc a) (bbc-trunc b)))
(defn bbc-or [a b] (bit-or (bbc-trunc a) (bbc-trunc b)))
(defn bbc-eor [a b] (bit-xor (bbc-trunc a) (bbc-trunc b)))
(defn bbc-not [a] (bit-not (bbc-trunc a)))
(defn bbc-sgn [x] (cond (pos? x) 1 (neg? x) -1 :else 0))
(defn bbc-val [s]
  (cond (re-matches #"[+-]?\d+" s) (Long/parseLong s)
        :else (try (Double/parseDouble s) (catch NumberFormatException _ 0))))
(defn bbc-asc [^String s] (if (empty? s) -1 (int (.charAt s 0))))
(defn bbc-chr [n] (str (char (bbc-trunc n))))
(defn bbc-left [^String s n] (subs s 0 (max 0 (min (bbc-trunc n) (count s)))))
(defn bbc-right [^String s n]
  (let [l (count s)] (subs s (max 0 (- l (bbc-trunc n))) l)))
(defn bbc-mid
  ([^String s p] (bbc-mid s p (count s)))
  ([^String s p n]
   (let [l (count s)
         start (max 0 (min l (dec (bbc-trunc p))))
         end (max start (min l (+ start (bbc-trunc n))))]
     (subs s start end))))
(defn bbc-instr
  ([^String s target] (bbc-instr s target 1))
  ([^String s ^String target start]
   (inc (.indexOf s target (int (max 0 (dec (bbc-trunc start))))))))

;;; --- Shifts and hex, as in BBC BASIC for SDL ---

(defn- bbc-width [n]
  ;; 32 bits for a number that fits them, signed or not, else 64
  (if (and (>= n -2147483648) (<= n 4294967295)) 32 64))

(defn bbc-shl [a b] (bit-shift-left (long (bbc-int a)) (bbc-int b)))
(defn bbc-shr [a b] (bit-shift-right (long (bbc-int a)) (bbc-int b)))
(defn bbc-lsr [a b]
  (let [n (long (bbc-int a))]
    (if (= 32 (bbc-width n))
      (unsigned-bit-shift-right (bit-and n 0xFFFFFFFF) (bbc-int b))
      (unsigned-bit-shift-right n (bbc-int b)))))

(defn bbc-hex
  "Upper-case hex, a negative number in 32 (or 64) bits."
  [x]
  (let [n (long (bbc-int x))]
    (.toUpperCase (if (= 32 (bbc-width n))
                    (Long/toHexString (bit-and n 0xFFFFFFFF))
                    (Long/toHexString n)))))

(defn bbc-print-hex [x justify]
  (let [text (bbc-hex x)]
    (bbc-write (if justify (format (str "%" zone-width "s") text) text))))

;;; --- TIME, in centiseconds since the program started or TIME was set ---

(def time-base (atom (System/nanoTime)))

(defn bbc-time-read []
  (quot (- (System/nanoTime) @time-base) 10000000))

(defn bbc-time-set! [value]
  (reset! time-base (- (System/nanoTime) (* (bbc-int value) 10000000))))

;;; --- DATA, READ, RESTORE and arrays ---

(def data (atom []))
(def data-ptr (atom 0))

(defn bbc-read-datum []
  (when (>= @data-ptr (count @data)) (throw (ex-info "Out of DATA" {})))
  (let [d (nth @data @data-ptr)]
    (swap! data-ptr inc)
    d))

(defn bbc-make-array [dims fill]
  ;; Nested Java arrays of (0..d0) x (0..d1) ...
  (let [n (inc (bbc-int (first dims)))
        a (object-array n)]
    (dotimes [i n]
      (aset a i (if (next dims) (bbc-make-array (next dims) fill) fill)))
    a))

(defn bbc-aref [arr & indices]
  (reduce (fn [a i] (aget ^objects a (int (bbc-int i)))) arr indices))

(defn bbc-aset! [arr val & indices]
  (let [inner (reduce (fn [a i] (aget ^objects a (int (bbc-int i)))) arr (butlast indices))]
    (aset ^objects inner (int (bbc-int (last indices))) val)))

;;; --- Helpers the macros use while they expand ---

(defn marker? [x nm]
  ;; Markers such as ELSE and STEP are compared by name, from any namespace
  (and (symbol? x) (= (name x) nm)))

(defn form? [x nm]
  (and (seq? x) (marker? (first x) nm)))

(defn split-at-marker
  "[before after] around the first marker; after is nil without one."
  [forms nm]
  (let [[before after] (split-with #(not (marker? % nm)) forms)]
    [before (when (seq after) (rest after))]))

(defn suffix? [var ch]
  (let [s (name var)]
    (and (pos? (count s)) (= (last s) ch))))

(defn bbc-default [var]
  (if (suffix? var \$) "" 0))

(defn name-suffix? [var suffix]
  (let [s (name var)]
    (and (> (count s) (count suffix)) (.endsWith s suffix))))

(defn lhs-var
  "The variable of a READ target: var or (AREF var i ...)."
  [target]
  (if (form? target "AREF") (second target) target))

(defn uses?
  "Does code x contain a form starting with one of the names?"
  [names x]
  (and (seq? x)
       (not= 'quote (first x))
       (or (boolean (some #(form? x %) names))
           (boolean (some #(uses? names %) x)))))

(defn collect-forms
  "Every (pick form), in order and once each, for the forms in x headed by one of names."
  [names pick x]
  (->> (tree-seq #(and (seq? %) (not= 'quote (first %))) seq x)
       (filter (fn [f] (some #(form? f %) names)))
       (mapcat pick)
       distinct))

(defn assigned-vars
  "Every variable the statements give a value to."
  [stmts]
  (collect-forms ["LET" "FOR" "LOCAL" "DEF-PROC" "DEF-FN" "READ" "DIM" "ASET!"]
                 (fn [form]
                   (cond (or (form? form "LET") (form? form "FOR") (form? form "ASET!")) [(second form)]
                         (form? form "LOCAL") (rest form)
                         (form? form "READ") (map lhs-var (rest form))
                         (form? form "DIM") (map first (rest form))
                         :else (rest (second form))))
                 (apply list stmts)))

(defn data-items
  "The items of every DATA statement, in program order."
  [stmts]
  (->> (tree-seq #(and (seq? %) (not= 'quote (first %)) (not (form? % "DATA"))) seq (apply list stmts))
       (filter #(form? % "DATA"))
       (mapcat rest)))

(defn def? [form]
  (or (form? form "DEF-PROC") (form? form "DEF-FN")))

(def boolean-heads #{"<" ">" "<=" ">=" "=" "==" "not=" "not" "nil?" "zero?"
                     "bbc=" "bbc<" "bbc>" "bbc<=" "bbc>=" "bbc-eq?"})

(defn bbc-test
  "Code for a BBC test; Clojure comparisons already give true or false."
  [test]
  (if (and (seq? test) (symbol? (first test)) (boolean-heads (name (first test))))
    test
    `(bbc-true? ~test)))

(defn catching
  "Run body; an exit for tag inside it gives its value instead, other exceptions go on."
  [tag body]
  `(try ~body
        (catch clojure.lang.ExceptionInfo e# (bbc-exit-value ~tag e#))))

(defn def-name [kind nm]
  (symbol (str kind "-" (name nm))))

;;; --- Statements ---

(defn typed-value
  "A% 32-bit, A%% 64-bit, A& a byte, A# a float."
  [var exp]
  (cond (name-suffix? var "%%") `(bbc-int64 ~exp)
        (name-suffix? var "%") `(bbc-int32 ~exp)
        (name-suffix? var "&") `(bbc-byte ~exp)
        (name-suffix? var "#") `(double ~exp)
        :else exp))

(defmacro LET [var exp]
  `(set! ~var ~(typed-value var exp)))

(defn print-code
  "The code for PRINT's items; :semi stops right-justifying numbers, :comma starts it again."
  [items justify]
  (if (empty? items)
    ['(mini-basic/bbc-newline)]
    (let [[item & more] items]
      (cond (= item :semi)
            (if more (print-code more false) [])
            (= item :comma)
            (cons '(mini-basic/bbc-zone) (if more (print-code more true) []))
            (= item :nl)
            (cons '(mini-basic/bbc-newline) (print-code more justify))
            (form? item "TAB")
            (cons (if (nnext item)
                    `(bbc-tab-xy ~@(rest item))
                    `(bbc-tab ~(second item)))
                  (print-code more justify))
            (form? item "SPC")
            (cons `(bbc-spaces ~(second item)) (print-code more justify))
            (form? item "HEX")
            (cons `(bbc-print-hex ~(second item) ~justify) (print-code more justify))
            :else
            (cons `(bbc-print-value ~item ~justify) (print-code more justify))))))

(defmacro PRINT [& items]
  `(do ~@(print-code items true)))

(defmacro IF [test & body]
  (let [[then else] (split-at-marker body "ELSE")]
    `(if ~(bbc-test test)
       (do ~@then)
       ~@(when else [`(do ~@else)]))))

(defmacro FOR [var from to & more]
  (let [has-step (marker? (first more) "STEP")
        step (if has-step (second more) 1)
        body (if has-step (nnext more) more)
        lim (gensym "lim")
        st (gensym "step")
        more? (cond (not (number? step)) `(if (neg? ~st) (>= ~var ~lim) (<= ~var ~lim))
                    (neg? step) `(>= ~var ~lim)
                    :else `(<= ~var ~lim))
        run `(let [~lim ~to ~st ~step]
               (loop []
                 ~@body
                 (LET ~var (+ ~var ~st))
                 (when ~more? (recur))))]
    `(do
       (LET ~var ~from)
       ~(if (uses? ["EXIT-FOR"] body) (catching :exit-for run) run))))

(defmacro REPEAT [& body]
  (let [[stmts until] (split-at-marker body "UNTIL")
        run `(loop []
               ~@stmts
               (when-not ~(bbc-test (first until)) (recur)))]
    (if (uses? ["EXIT-REPEAT"] stmts) (catching :exit-repeat run) run)))

(defmacro WHILE [test & body]
  (let [run `(loop []
               (when ~(bbc-test test)
                 ~@body
                 (recur)))]
    (if (uses? ["EXIT-WHILE"] body) (catching :exit-while run) run)))

(defmacro CASE [exp & clauses]
  (let [v (gensym "case")]
    `(let [~v ~exp]
       (cond ~@(mapcat (fn [clause]
                         (if (form? clause "OTHERWISE")
                           [:else `(do ~@(rest clause))]
                           [`(or ~@(map (fn [w] `(bbc-equal ~v ~w)) (second clause)))
                            `(do ~@(nnext clause))]))
                       clauses)))))

(defmacro EXIT-FOR [] `(bbc-exit :exit-for nil))
(defmacro EXIT-REPEAT [] `(bbc-exit :exit-repeat nil))
(defmacro EXIT-WHILE [] `(bbc-exit :exit-while nil))
(defmacro END [] `(bbc-exit :end nil))
(defmacro ENDPROC [] `(bbc-exit :return nil))
(defmacro FN= [exp] `(bbc-exit :return ~exp))

(defmacro LOCAL [& vars]
  `(do ~@(map (fn [var] `(set! ~var ~(bbc-default var))) vars)))

(defmacro PROC [nm & args] `(~(def-name "PROC" nm) ~@args))
(defmacro FN [nm & args] `(~(def-name "FN" nm) ~@args))

(declare tail-stmt)

(defn tail
  "An FN's last statement gives its value: (FN= x) in tail position is just x,
  also at the end of each branch of an IF or CASE there."
  [stmts]
  (if (empty? stmts)
    stmts
    (concat (butlast stmts) [(tail-stmt (last stmts))])))

(defn tail-stmt [stmt]
  (cond (form? stmt "FN=") (second stmt)
        (form? stmt "ENDPROC") nil
        (form? stmt "IF")
        (let [[then else] (split-at-marker (nnext stmt) "ELSE")]
          `(~(first stmt) ~(second stmt) ~@(tail then)
            ~@(when else (cons 'ELSE (tail else)))))
        (form? stmt "CASE")
        `(~(first stmt) ~(second stmt)
          ~@(map (fn [clause]
                   (if (form? clause "OTHERWISE")
                     `(~(first clause) ~@(tail (rest clause)))
                     `(~(first clause) ~(second clause) ~@(tail (nnext clause)))))
                 (nnext stmt)))
        :else stmt))

(defn def-code [kind [nm & parms] body]
  (let [args (map #(gensym (name %)) parms)
        locals (remove (set parms) (collect-forms ["LOCAL"] rest (apply list body)))
        tail-body (tail body)
        run `(do nil ~@tail-body)]
    `(defn ~(def-name kind nm) [~@args]
       (binding [~@(interleave parms args) ~@(interleave locals locals)]
         ~(if (uses? ["FN=" "ENDPROC"] run) (catching :return run) run)))))

(defmacro DEF-PROC [head & body] (def-code "PROC" head body))
(defmacro DEF-FN [head & body] (def-code "FN" head body))

(defmacro DIM [& specs]
  `(do ~@(map (fn [[var & dims]] `(set! ~var (bbc-make-array [~@dims] ~(bbc-default var)))) specs)))

(defmacro AREF [var & indices] `(bbc-aref ~var ~@indices))

(defmacro ASET! [var val & indices] `(bbc-aset! ~var ~(typed-value var val) ~@indices))

(defmacro DATA [& _items] nil)

(defmacro READ [& targets]
  `(do ~@(map (fn [target]
                (let [var (lhs-var target)
                      datum (if (suffix? var \$)
                              `(str (bbc-read-datum))
                              `(let [d# (bbc-read-datum)] (if (string? d#) (bbc-val d#) d#)))]
                  (if (form? target "AREF")
                    `(ASET! ~var ~datum ~@(nnext target))
                    `(LET ~var ~datum))))
              targets)))

(defmacro RESTORE [& target]
  (when (seq target) (throw (ex-info "RESTORE to a label is lispy3 only" {})))
  `(reset! data-ptr 0))

;;; --- A whole program ---

(defmacro bbc-program [& stmts]
  (let [vars (assigned-vars stmts)
        defs (filter def? stmts)
        run `(do (reset! col 0)
                 (reset! data [~@(data-items stmts)])
                 (reset! data-ptr 0)
                 ~@(remove def? stmts))]
    `(do
       ~@(map (fn [v] `(def ~(with-meta v {:dynamic true}) ~(bbc-default v))) vars)
       (declare ~@(map #(def-name (if (form? % "DEF-FN") "FN" "PROC") (first (second %))) defs))
       ~@defs
       (binding [~@(mapcat (fn [v] [v (bbc-default v)]) vars)]
         ~(if (uses? ["END"] (apply list stmts)) (catching :end run) run))
       (flush)
       nil)))
