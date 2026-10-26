(define-library mini-basic
  (export bbc-run bbc-load bbc-expand bbc-program bbc-set-print-style!
          CLS COLOUR COLOR ANSI VDU ANSI-RESET
          LET PRINT IF FOR REPEAT WHILE CASE
          EXIT-FOR EXIT-REPEAT EXIT-WHILE END ENDPROC FN=
          LOCAL PROC FN DEF-PROC DEF-FN
          LABEL DATA DIM AREF ASET! READ RESTORE INPUT
          GOSUB RETURN GOTO GO ON-GOTO ON-GOSUB
          ON-ERROR ON-ERROR-LOCAL ON-ERROR-OFF REPORT LINE
          TRUE FALSE run-lispy run-sbcl run-clojure)
  (include "mini-basic.lisp"))
