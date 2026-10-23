10 REM Six-scanline Mandelbrot preview: 480 samples, maximum 24 iterations.
20 REM Smaller drawing-only candidate based on mini_basic's mand_arch.bas math.
30 REM No VDU, ANSI, refresh extensions or input required.
40 MODE 9
50 TIME=0
60 FOR PY%=124 TO 129
70   CY=-1.2+PY%*2.4/255
80   FOR PX%=0 TO 319 STEP 4
90     CX=-2.2+PX%*3.0/319
100    ZX=0:ZY=0:I%=0
110    WHILE I%<24 AND ZX*ZX+ZY*ZY<4
120      TEMP=ZX*ZX-ZY*ZY+CX
130      ZY=2*ZX*ZY+CY:ZX=TEMP
140      I%=I%+1
150    ENDWHILE
160    IF I%<24 THEN
170      GCOL 0,(I% MOD 7)+1
180      MOVE PX%*4,PY%*4:DRAW PX%*4+12,PY%*4
190    ENDIF
200  NEXT PX%
210 NEXT PY%
220 PRINT "Six rows complete; ";TIME/100;" seconds."
230 END
