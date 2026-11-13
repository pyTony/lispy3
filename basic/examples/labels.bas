REM dialect: bbc
REM Named labels for GOTO, GOSUB and ON (lispy3 reader; mini_basic has line numbers)
PRINT "start"
GOTO skip
PRINT "not here"
(skip) GOSUB greet
FOR i% = 1 TO 2
  ON i% GOSUB one, two
NEXT
n% = 0
(again) n% = n% + 1
IF n% < 3 THEN GOTO again
PRINT "n% = "; n%
ON 3 GOTO one, two ELSE PRINT "out of range"
PRINT FNcount(4)
END
(greet) PRINT "hello" : RETURN
(one) PRINT "one" : RETURN
(two) PRINT "two" : RETURN
DEF FNcount(m%)
LOCAL c%
(loop) c% = c% + 1
IF c% < m% THEN GOTO loop
=c% * 10
