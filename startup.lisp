;; Welcome to Lispy3 Machine.
;; F5  - evaluate the top-level form at the cursor
;; F6  - evaluate the whole buffer
;; F9  - evaluate what you typed in the Listener
;; Ctrl+Space - complete a symbol
;; Ctrl+/     - toggle comment

(define square (lambda [x] (* x x)))
; (square 12)

(define fact
  (lambda [n]
    (if (< n 2)
      1
      (* n (fact (- n 1))))))
; (fact 100)

;; Clojure-style data
(define user {:name "Tony" :status "Trusty"})
(:name user)

;; Turtle graphics — load the engine, then draw:
(load "lsystems")
; (lsystem-from "F" "F[+F]F[-F]F" 4 3 23.5 0 -250 90)
; (lsystem-from "F" "FF-[-F+F+F]+[+F-F-F]" 5 16 23 -50 -250 90)
