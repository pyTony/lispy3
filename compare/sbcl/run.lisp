;;;; Run a mini-basic program with SBCL:  sbcl --script compare/sbcl/run.lisp program.lisp

(setf *read-default-float-format* 'double-float)

(handler-bind ((warning #'muffle-warning))
  (load (merge-pathnames "mini-basic.lisp" *load-truename*))
  (let ((*package* (find-package :bbc-user)))
    (load (second sb-ext:*posix-argv*))))
