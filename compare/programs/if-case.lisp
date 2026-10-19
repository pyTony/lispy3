; IF ... ELSE with BBC truth values, and CASE ... WHEN ... OTHERWISE
(bbc-program
  (LET x 3)
  (IF (> x 2) (PRINT "big") ELSE (PRINT "small"))
  (IF (< x 2) (PRINT "never"))
  (IF 0 (PRINT "zero is true") ELSE (PRINT "zero is false"))
  (IF TRUE (PRINT "TRUE is true"))
  (IF (- x 3) (PRINT "never") ELSE (PRINT "x-3 is false"))
  (FOR n 1 4
    (CASE n
      (WHEN (1 2) (PRINT "low " :semi))
      (WHEN (3) (PRINT "three " :semi))
      (OTHERWISE (PRINT "other " :semi))))
  (PRINT)
  (LET a$ "yes")
  (CASE a$ (WHEN ("no") (PRINT "N")) (WHEN ("yes" "y") (PRINT "Y"))))
