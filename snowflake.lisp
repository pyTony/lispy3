;; Snowflake. Change the numbers under "Settings" and run the file again:
;;   python lispy3.py snowflake.lisp
;; or keep the REPL open and redraw with different values:
;;   python lispy3.py -i snowflake.lisp
;;   (snowflake 3 5)      ; generations, then step (line length in pixels)
(load "lsystems")

;; ---- Settings ----
(define axiom "F-F-F-F-F")
(define rule "F-F++F+F-F-F")
(define angle 72)          ; turn angle in degrees
(define start-x -120)      ; where the drawing starts
(define start-y 160)
(define generations 4)     ; each generation makes about 6 times more lines, so keep it small
(define step 2)            ; length of one line in pixels

(define snowflake
  (lambda (generations step)
    (lsystem axiom rule generations step angle start-x start-y)))

(snowflake generations step)
