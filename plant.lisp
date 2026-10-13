;; 2D bracketed plant from "The Algorithmic Beauty of Plants" (page 25), shown as
;; Figure 3 at people.ece.cornell.edu/land/OldStudentProjects/cs490-94to95/hwchen/
;; Change the numbers under "Settings" and run the file again:
;;   python lispy3.py plant.lisp
;; or keep the REPL open and redraw with different values:
;;   python lispy3.py -i plant.lisp
;;   (plant 4 4)     ; generations, then step (line length in pixels)
(load "lsystems")

;; ---- Settings ----
(define plant-axiom "F")
(define plant-rule "F[+F]F[-F]F")
(define plant-angle 23.5)       ; turn angle in degrees
(define plant-x -10)            ; where the stem starts
(define plant-y -250)
(define plant-generations 5)    ; each generation makes 5 times more lines
(define plant-step 2)           ; length of one line in pixels

;; green on black (colours are red green blue from 0 to 1)
(bgcolor 0 0 0)
(pencolor 0 0.9 0)

(define plant
  (lambda (generations step)
    (lsystem-from plant-axiom plant-rule generations step plant-angle plant-x plant-y 90)))

(plant plant-generations plant-step)
