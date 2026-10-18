REM Structured BBC BASIC: loops, IF, CASE, PROC and FN
total% = 0
FOR i% = 1 TO 10 STEP 3
  total% += i%
NEXT i%
PRINT "total% = ";total%
k = 0
REPEAT
  k = k + 1
UNTIL k * k > 50
PRINT "k = ";k
WHILE k > 3
  k -= 2
ENDWHILE
PRINT "k = ";k
FOR n = 1 TO 4
  CASE n OF
    WHEN 1, 2 : PRINT "low ";
    WHEN 3 : PRINT "three ";
    OTHERWISE PRINT "other ";
  ENDCASE
NEXT
PRINT
x = 7
IF x > 5 THEN
  PRINT "big"
ELSE
  PRINT "small"
ENDIF
IF x MOD 2 = 0 THEN PRINT "even" ELSE PRINT "odd"
IF x > 1 AND x < 10 THEN PRINT "between"
IF NOT (x = 3) THEN PRINT "not three"
PROCgreet("Tony", 2)
PRINT FNmax(3, 9); " "; FNmax(12, 4)
PRINT "gcd = "; FNgcd(84, 36)
name$ = "outer"
PROCshow
PRINT name$
END

DEF PROCgreet(who$, times%)
  LOCAL i%
  FOR i% = 1 TO times%
    PRINT "Hello, "; who$; "!"
  NEXT
ENDPROC

DEF FNmax(a, b)
  IF a > b THEN = a
= b

DEF FNgcd(a%, b%)
  WHILE b% <> 0
    t% = b%
    b% = a% MOD b%
    a% = t%
  ENDWHILE
= a%

DEF PROCshow
  LOCAL name$
  name$ = "inner"
  PRINT name$
ENDPROC
