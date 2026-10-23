;;; mini-basic-io.lisp - BBC BASIC file I/O for mini-basic.lisp
;;;
;;;   F% = OPENOUT "data.dat" : PRINT#F%, "text", 42 : CLOSE#F%
;;;   F% = OPENIN "data.dat" : INPUT#F%, a$, n% : CLOSE#F%
;;;   BPUT#F%, 65 : BPUT#F%, "line" : x = BGET#F% : l$ = GET$#F%
;;;   EOF#F%, PTR#F%, PTR#F% = n, EXT#F%, OPENUP, CLOSE#0 (every file)
;;;
;;; Byte layouts follow BBC BASIC for SDL: PRINT# writes a string followed by
;;; CR, a whole number as &40 and 4 bytes (least significant first) and any
;;; other number as &FF and an 8-byte IEEE double; BPUT# writes a string
;;; followed by LF, or without it after a final semicolon. GET$# reads up to
;;; CR, LF or NUL. Strings are bytes 0-255.
;;;
;;; This file wraps the reader's statement and expression hooks rather than
;;; editing them, and is loaded after mini-basic-ext.lisp.

;;; --- Channels ---

(define bbc-channels {})
(define bbc-next-channel 1)

(define (bbc-channel n)
  (let [f (get bbc-channels (trunc n) #f)]
    (if f f (error (str "Invalid channel " n)))))

(define (bbc-open name mode)
  ;; A new channel number, or 0 when the file cannot be opened
  (try (let [f (open-file name mode)
             ch bbc-next-channel]
         (set! bbc-next-channel (+ ch 1))
         (bbc-channels/__setitem__ ch f)
         ch)
       (catch e 0)))

(define (bbc-close n)
  (let [chs (if (= (trunc n) 0) (keys bbc-channels) (list (trunc n)))]
    (for-each (lambda (ch)
                (close (bbc-channel ch))
                (bbc-channels/pop ch))
              chs)))

(define (bbc-eof n)
  (let [f (bbc-channel n)]
    (if (>= (file-position f) (file-length f)) -1 0)))

(define (bbc-ptr n) (file-position (bbc-channel n)))
(define (bbc-set-ptr! n p) (file-position (bbc-channel n) (trunc p)))
(define (bbc-ext n) (file-length (bbc-channel n)))

;;; --- Bytes ---

(define (bbc-string-bytes s)
  (let [b (s/encode "latin-1" "replace")]
    (map (lambda (i) (b/__getitem__ i)) (range (b/__len__)))))

(define (bbc-write-bytes f bytes)
  (for-each (lambda (b) (write-byte b f)) bytes))

(define (bbc-read-byte f)
  (let [b (read-byte f)]
    (if b b (error "End of file"))))

(define (bbc-read-le f count)
  ;; An unsigned whole number from count bytes, least significant first
  (let loop ((i 0) (scale 1) (total 0))
    (if (= i count)
        total
        (loop (+ i 1) (* scale 256) (+ total (* scale (bbc-read-byte f)))))))

(define (bbc-le-bytes n count)
  (let loop ((i 0) (n n) (acc '()))
    (if (= i count)
        (reverse acc)
        (loop (+ i 1) (quotient n 256) (cons (remainder n 256) acc)))))

;;; --- Numbers as PRINT# writes them ---

(define bbc-two-52 4503599627370496)

(define (bbc-double-bits x)
  ;; The 64 IEEE bits of a normal double (or zero) as a whole number
  (if (= x 0)
      0
      (let [parts (frexp (abs x))
            mantissa (nth parts 0)
            exponent (nth parts 1)
            sign (if (< x 0) 9223372036854775808 0)]
        (+ sign
           (* (+ exponent 1022) bbc-two-52)
           (- (trunc (* mantissa 9007199254740992.0)) bbc-two-52)))))

(define (bbc-bits-double bits)
  (let [sign (if (>= bits 9223372036854775808) -1 1)
        rest (remainder bits 9223372036854775808)
        exponent (quotient rest bbc-two-52)
        fraction (remainder rest bbc-two-52)]
    (if (= exponent 0)
        (* sign 0.0)
        (* sign (ldexp (+ bbc-two-52 fraction) (- exponent 1075))))))

(define (bbc-write-number f x)
  (if (and (exact? x) (>= x -2147483648) (<= x 2147483647))
      (begin (write-byte 64 f)
             (bbc-write-bytes f (bbc-le-bytes (if (< x 0) (+ x 4294967296) x) 4)))
      (begin (write-byte 255 f)
             (bbc-write-bytes f (bbc-le-bytes (bbc-double-bits (float x)) 8)))))

(define (bbc-read-number f)
  (let [kind (bbc-read-byte f)]
    (cond ((= kind 64)
           (let [n (bbc-read-le f 4)]
             (if (>= n 2147483648) (- n 4294967296) n)))
          ((= kind 255) (bbc-bits-double (bbc-read-le f 8)))
          (else (error "Type mismatch: INPUT# expected a number")))))

(define (bbc-read-until f stops)
  ;; Bytes up to one in stops (dropped) or the end of the file, as a string
  (let loop ((acc '()))
    (let [b (read-byte f)]
      (if (or (not b) (member b stops))
          (list (apply str (reverse acc)) b)
          (loop (cons (bbc-chr b) acc))))))

;;; --- Statements and functions ---

(define (bbc-print-file n & items)
  (let [f (bbc-channel n)]
    (for-each (lambda (x)
                (if (string? x)
                    (begin (bbc-write-bytes f (bbc-string-bytes x)) (write-byte 13 f))
                    (bbc-write-number f x)))
              items)))

(define (bbc-input-file n kind)
  (let [f (bbc-channel n)]
    (if (eq? kind :str)
        (car (bbc-read-until f '(13)))
        (bbc-read-number f))))

(define (bbc-bput n x newline)
  (let [f (bbc-channel n)]
    (if (string? x)
        (begin (bbc-write-bytes f (bbc-string-bytes x))
               (if newline (write-byte 10 f)))
        (write-byte x f))))

(define (bbc-bget n) (bbc-read-byte (bbc-channel n)))

(define (bbc-get-line n)
  ;; GET$#: up to CR, LF or NUL; a CR LF pair counts as one line end
  (let [f (bbc-channel n)
        got (bbc-read-until f '(13 10 0))]
    (if (equal? (nth got 1) 13)
        (let [here (file-position f)]
          (if (not (equal? (read-byte f) 10)) (file-position f here))))
    (car got)))

;;; --- Reader ---

(set! bbc-keywords (append bbc-keywords '("OPENIN" "OPENOUT" "OPENUP" "CLOSE" "BPUT" "BGET"
                                          "EOF" "PTR" "EXT" "GET$")))

(define bbc-io-calls '(bbc-print-file bbc-input-file bbc-bput bbc-bget bbc-get-line bbc-open
                       bbc-close bbc-eof bbc-ptr bbc-set-ptr! bbc-ext))

(define (bbc-io-hash? word)
  ;; At keyword word followed by #
  (and (bbc-at? :kw word)
       (bbc-tok? (nth bbc-toks (+ bbc-pos 1)) :op "#")))

(define (bbc-p-channel)
  ;; After the keyword: # and the channel number
  (bbc-advance!)
  (bbc-expect! :op "#" "#")
  (bbc-value (bbc-p-unary)))

(define (bbc-p-print-file)
  (let [ch (bbc-p-channel)
        items (list)]
    (while (or (bbc-accept! :op ",") (bbc-accept! :op ";"))
      (bbc-push! items (bbc-value (bbc-p-expr))))
    (append (list 'bbc-print-file ch) items)))

(define (bbc-p-input-file)
  (let [ch (bbc-p-channel)
        g (gensym "channel")
        sets (list)]
    (while (bbc-accept! :op ",")
      (let [info (bbc-p-target)
            target (car info)
            value `(bbc-input-file ,g ,(if (bbc-string-name? (nth info 1)) :str :num))]
        (bbc-push! sets (if (and (pair? target) (eq? (car target) 'AREF))
                            (append (list 'ASET! (nth info 2) value) (cdr (cdr target)))
                            (list 'LET (nth info 2) value)))))
    `(let ((,g ,ch)) ,@sets)))

(define (bbc-p-bput)
  (let [ch (bbc-p-channel)]
    (bbc-expect! :op "," ",")
    (let [x (bbc-value (bbc-p-expr))]
      (list 'bbc-bput ch x (not (bbc-accept! :op ";"))))))

(define (bbc-p-set-ptr)
  (let [ch (bbc-p-channel)]
    (bbc-expect! :op "=" "=")
    (list 'bbc-set-ptr! ch (bbc-value (bbc-p-expr)))))

(define (bbc-io-statement)
  (cond ((bbc-io-hash? "PRINT") (bbc-p-print-file))
        ((bbc-io-hash? "INPUT") (bbc-p-input-file))
        ((bbc-io-hash? "BPUT") (bbc-p-bput))
        ((bbc-io-hash? "CLOSE") (list 'bbc-close (bbc-p-channel)))
        ((bbc-io-hash? "PTR") (bbc-p-set-ptr))
        (else #f)))

(define (bbc-io-primary)
  (let [open-mode (cond ((bbc-at? :kw "OPENIN") "rb")
                        ((bbc-at? :kw "OPENOUT") "w+b")
                        ((bbc-at? :kw "OPENUP") "r+b")
                        (else #f))]
    (cond (open-mode
           (bbc-advance!)
           (bbc-num (list 'bbc-open (bbc-value (bbc-p-unary)) open-mode)))
          ((bbc-io-hash? "BGET") (bbc-num (list 'bbc-bget (bbc-p-channel))))
          ((bbc-io-hash? "EOF") (bbc-num (list 'bbc-eof (bbc-p-channel))))
          ((bbc-io-hash? "PTR") (bbc-num (list 'bbc-ptr (bbc-p-channel))))
          ((bbc-io-hash? "EXT") (bbc-num (list 'bbc-ext (bbc-p-channel))))
          ((bbc-io-hash? "GET$") (bbc-e (list 'bbc-get-line (bbc-p-channel)) :str))
          (else #f))))

(define bbc-statement-before-io bbc-ext-statement)
(define (bbc-ext-statement)
  (or (bbc-io-statement) (bbc-statement-before-io)))

(define bbc-primary-before-io bbc-p-primary)
(define (bbc-p-primary)
  (or (bbc-io-primary) (bbc-primary-before-io)))

;; An FN that reads or writes a file gives different results for the same
;; arguments, so it is not remembered
(define bbc-pure-fn-before-io bbc-pure-fn?)
(define (bbc-pure-fn? def vars)
  (and (not (bbc-uses? bbc-io-calls (cdr (cdr def))))
       (bbc-pure-fn-before-io def vars)))
