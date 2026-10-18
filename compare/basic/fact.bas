REM dialect: bbc
DEF FNfact(n) IF n<2 THEN =1 ELSE =n*FNfact(n-1)
FOR i=1 TO 6
  PRINT "fact(";i;") = ";FNfact(i)
NEXT
