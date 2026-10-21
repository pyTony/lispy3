REM Terminal Mandelbrot procedures for lispy3 mini-basic; no MODE/graphics.
REM Load this file, then call PROCmandelbrot(FALSE,79,25,40) or TRUE for colour.
REM Width/height must be integers >=2; iterations must be a positive integer.
DEF PROCmandelbrot(colour%,width%,height%,limit%)
LOCAL ramp$,last%,row%,col%,cx,cy,n%,ink%,glyph$
ramp$=".,:;ox%#@"
last%=-1
IF colour% THEN
  ANSI 27,"[0m"
  COLOUR 128
ENDIF
FOR row%=0 TO height%-1
  cy=-1.0+2.0*row%/(height%-1)
  FOR col%=0 TO width%-1
    cx=-2.2+3.0*col%/(width%-1)
    n%=FNmandelEscape(cx,cy,limit%)
    IF n%=limit% THEN
      ink%=0
      glyph$=" "
    ELSE
      ink%=9+(n% MOD 6)
      glyph$=MID$(ramp$,(n% MOD 9)+1,1)
    ENDIF
    IF colour% AND ink%<>last% THEN
      COLOUR ink%
      last%=ink%
    ENDIF
    PRINT glyph$;
  NEXT col%
  PRINT ""
NEXT row%
IF colour% THEN ANSI 27,"[0m"
ENDPROC

DEF FNmandelEscape(cx,cy,limit%)
LOCAL x,y,n%,nextX
x=0.0:y=0.0:n%=0
WHILE n%<limit% AND x*x+y*y<=4.0
  nextX=x*x-y*y+cx
  y=2.0*x*y+cy
  x=nextX
  n%+=1
ENDWHILE
=n%
