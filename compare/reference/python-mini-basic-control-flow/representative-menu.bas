   10 REM Representative Python mini_basic tests; fresh RUN per case
   20 ON ERROR PRINT "ERROR ";ERR;" AT LINE ";ERL:REPORT:PRINT:END
   21 PRINT "1 0001-38d828c013 dialect=bbc"
   22 PRINT "2 0002-e1b142a8f5 dialect=mini"
   23 PRINT "3 0007-82ed7de9b3 dialect=mini"
   24 PRINT "4 0011-05576c3a8c dialect=bbc"
  110 INPUT "Case (1-4): " choice%
  121 IF choice%=1 THEN GOTO 2000
  122 IF choice%=2 THEN GOTO 4000
  123 IF choice%=3 THEN GOTO 6000
  124 IF choice%=4 THEN GOTO 8000
  200 PRINT "Invalid case":END
 2000 REM 0001-38d828c013
 2010 IF TRUE THEN
 2020   FOR I%=0 TO 3
 2030     IF I%=1 THEN
 2040       EXIT FOR
 2050     ENDIF
 2060   NEXT I%
 2070 ENDIF
 2080 PRINT "done"
 3999 END
 4000 REM 0002-e1b142a8f5
 4100 a=0
 4110 REPEAT
 4120   a=a+1
 4130   WHILE a < 3
 4140     IF a = 1 THEN EXIT REPEAT
 4150     IF a = 2 THEN EXIT WHILE
 4160   ENDWHILE
 4170 UNTIL a >=3
 4180 PRINT a
 5999 END
 6000 REM 0007-82ed7de9b3
 6100 FOR i=1 TO 5
 6110   a=0
 6120   REPEAT
 6130     a=a+1
 6140     WHILE a < 3
 6150       i+=1
 6160       IF i=3 THEN EXIT FOR
 6170     ENDWHILE
 6180   UNTIL a >=2
 6190 NEXT
 6200 PRINT i
 7999 END
 8000 REM 0011-05576c3a8c
 8100 FOR uyqtruv0z0dyxpmod9ym_w=1 TO 2
 8110   FOR ap_70ufd=1 TO 2
 8120     PRINT uyqtruv0z0dyxpmod9ym_w; ap_70ufd
 8130   NEXT ap_70ufd
 8140 NEXT uyqtruv0z0dyxpmod9ym_w
 9999 END
