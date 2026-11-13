REM dialect: bbc
REM GOTO, GOSUB and ON ... GOTO / GOSUB, to line numbers
10 PRINT "start"
20 i% = 0
30 i% = i% + 1
40 IF i% < 3 THEN GOTO 30
50 PRINT "i% = "; i%
60 GOSUB 200
70 FOR k% = 1 TO 3
80   ON k% GOSUB 300, 310, 320
90 NEXT
100 ON 2 GOTO 110, 130
110 PRINT "not here"
120 END
130 PRINT "on goto"
140 PROCcount(3)
150 FOR q% = 1 TO 10
160   IF q% = 4 THEN GOTO 180
170 NEXT
180 PRINT "left the loop at "; q%
190 GOTO 330
200 PRINT "in sub"
210 RETURN
300 PRINT "one" : RETURN
310 PRINT "two" : RETURN
320 PRINT "three" : RETURN
330 PRINT "done"
340 END
400 DEF PROCcount(n%)
410 LOCAL j%
420 j% = 0
430 j% = j% + 1 : PRINT j%;
440 IF j% < n% THEN GOTO 430
450 PRINT
460 ENDPROC
