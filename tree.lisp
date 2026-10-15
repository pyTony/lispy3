;; 2D bracketed tree from "The Algorithmic Beauty of Plants" (page 25), shown as
;; Figure 4 at people.ece.cornell.edu/land/OldStudentProjects/cs490-94to95/hwchen/
;; Change the numbers under "Settings" and run the file again:
;;   python lispy3.py tree.lisp
;; or keep the REPL open and redraw with different values:
;;   python lispy3.py -i tree.lisp
;;   (tree 3 8)      ; generations, then step (line length in pixels)
(load "lsystems")

;; ---- Settings ----
(define tree-axiom "F")
(define tree-rule "FF-[-F+F+F]+[+F-F-F]")
(define tree-angle 23)         ; turn angle in degrees
(define tree-x -50)            ; where the trunk starts
(define tree-y -250)
(define tree-generations 4)    ; each generation makes about 8 times more lines
(define tree-step 8)           ; length of one line in pixels

;; green on black, as in the figure (colours are red green blue from 0 to 1)
(bgcolor 0 0 0)
(pencolor 0 0.9 0)

(define tree
  (lambda (generations step)
    (lsystem-from tree-axiom tree-rule generations step tree-angle tree-x tree-y 90)))

(tree tree-generations tree-step)
