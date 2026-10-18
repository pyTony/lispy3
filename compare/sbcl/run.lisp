;;;; Run a mini-basic program with SBCL:  sbcl --script compare/sbcl/run.lisp program.lisp
;;;; Without a file name the program is read from standard input.

(setf *read-default-float-format* 'double-float)

(handler-bind ((warning #'muffle-warning))
  (load (merge-pathnames "mini-basic.lisp" *load-truename*))
  (let ((*package* (find-package :bbc-user)))
    (load (or (second sb-ext:*posix-argv*) *standard-input*))))
