(define-library mini-basic
  (export bbc-run bbc-load bbc-expand bbc-program
          CLS COLOUR COLOR ANSI VDU ANSI-RESET
          LET PRINT IF FOR REPEAT WHILE CASE
          EXIT-FOR EXIT-REPEAT EXIT-WHILE END ENDPROC FN=
          LOCAL PROC FN DEF-PROC DEF-FN
          LABEL DATA DIM AREF ASET! READ RESTORE
          GOSUB RETURN GOTO GO ON-GOTO ON-GOSUB
          TRUE FALSE run-lispy run-sbcl run-clojure)
  (include "mini-basic.lisp"))
