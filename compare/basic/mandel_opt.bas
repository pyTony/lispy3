1 REM dialect: mini
100 REM Optimized Mandelbrot
110 PRINT "Start"
120 TIME = 0
130 Z$ = ".,'~=+:;*%&$OXB#@ "
140 F = 50
150 FOR Y = -12 TO 12
160     FOR X = -49 TO 29
170         C = X * 229 / 100
180         D = Y * 416 / 100
190         A = C: B = D: I = 0
200         REM Unroll the WHILE for speed?
210         WHILE I < 16
220             Q = B / F
230             S = B - (Q * F)
240             T = ((A * A) - (B * B)) / F + C
250             B = 2 * ((A * Q) + (A * S / F)) + D
260             A = T
270             P = A / F
280             Q = B / F
290             IF (P * P) + (Q * Q) >= 5 THEN
300                 COLOUR I
310                 PRINT MID$(Z$, I + 1, 1);
320                 EXIT WHILE
330             ENDIF
340             I = I + 1
350         ENDWHILE
360         IF I >= 16 THEN PRINT" ";
370     NEXT X
380     PRINT
390 NEXT Y
400 Q = TIME
410 COLOUR 7
420 PRINT "Finished"
430 PRINT "Time: "; Q / 100;" secs."
440 REM WAIT -1
