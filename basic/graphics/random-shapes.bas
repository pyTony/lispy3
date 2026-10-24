10 REM Random truecolour shapes: Python mini_basic, BBC dialect, graphics window.
20 REM Fixed seed/count for timing. Set DELAY%=2 for a slower screensaver effect.
30 MODE 8:OFF
40 COUNT%=300:DELAY%=0
50 SEED%=RND(-12345)
60 TIME=0
70 FOR N%=1 TO COUNT%
80   X%=80+RND(1100):Y%=80+RND(850):R%=10+RND(30)
90   COLOUR 1,RND(256)-1,RND(256)-1,RND(256)-1
100  GCOL 0,1
110  CIRCLE FILL X%,Y%,R%
120  X%=RND(1000)-1:Y%=RND(800)-1
130  W%=80+RND(160):H%=50+RND(120)
140  COLOUR 1,RND(256)-1,RND(256)-1,RND(256)-1
150  RECTANGLE FILL X%,Y%,W%,H%
160  IF DELAY%>0 THEN WAIT DELAY%
170 NEXT N%
180 PRINT COUNT%;" circle/rectangle pairs in ";TIME/100;" seconds."
190 END
