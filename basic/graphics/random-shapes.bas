10 REM Random truecolour shapes: Python mini_basic, BBC dialect, graphics window.
20 REM Fixed seed/count for timing. Set delay%=2 for a slower screensaver effect.
30 MODE 8:OFF
40 count%=300:delay%=0
50 seed%=RND(-12345)
60 TIME=0
70 FOR n%=1 TO count%
80   x%=80+RND(1100):y%=80+RND(850):r%=10+RND(30)
90   COLOUR 1,RND(256)-1,RND(256)-1,RND(256)-1
100  GCOL 0,1
110  CIRCLE FILL x%,y%,r%
120  x%=RND(1000)-1:y%=RND(800)-1
130  w%=80+RND(160):h%=50+RND(120)
140  COLOUR 1,RND(256)-1,RND(256)-1,RND(256)-1
150  RECTANGLE FILL x%,y%,w%,h%
160  IF delay%>0 THEN WAIT delay%
170 NEXT n%
180 PRINT count%;" circle/rectangle pairs in ";TIME/100;" seconds."
190 END
