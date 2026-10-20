; Recursive FN, FOR and PRINT with ; separators
(bbc-program
  (DEF-FN (fact n) (IF (< n 2) (FN= 1) ELSE (FN= (* n (FN fact (- n 1))))))
  (FOR i 1 6 (PRINT "fact(" :semi i :semi ") = " :semi (FN fact i))))
