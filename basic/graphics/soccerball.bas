REM Spinning soccer ball, from BBC BASIC for SDL 2.0 examples/graphics/soccerball.bbc
REM (c) Richard T. Russell, zlib licence. Altered for Lispy: the ON ERROR line is left out.
REM!Keep p, q, r, s, t

MODE 9 : OFF
ORIGIN 640,512 : COLOUR 130
DIM xyz(2,59), tmp(2,59), b(2,2), c(2,2)

s = SQR5 + 1 : p = s/2 : q = p+2 : r = s+1 : t = p*3
FOR I% = 0 TO 59
READ xyz(0,I%), xyz(1,I%), xyz(2,I%)
NEXT

*REFRESH OFF
b = 0.5 : c = 0
b() = COS(b), 0, -SIN(b), 0, 1, 0, SIN(b), 0, COS(b)
REPEAT
c() = COS(c), SIN(c), 0, -SIN(c), COS(c), 0, 0, 0, 1
c() = b() . c() : tmp() = c() . xyz()
CLS
GCOL 3 : CIRCLE FILL 0, 0, 432 : GCOL 0
I% = 0
FOR J% = 0 TO 11
z = SUM(tmp(1, I% TO I%+4))
FOR K% = 0 TO 4
X% = 3200 * tmp(0,I%) / (36 + tmp(1,I%))
Y% = 3200 * tmp(2,I%) / (36 + tmp(1,I%))
IF K%<2 MOVE X%,Y% ELSE IF z<-2.5 PLOT 85,X%,Y%
I% += 1
NEXT
NEXT J%
WAIT 1 : *REFRESH
c += 0.03
UNTIL FALSE
END

DATA 0, 1, t, -p, 2, r, p, 2, r, -1, q, s, 1, q, s
DATA 0, 1, -t, -p, 2, -r, p, 2, -r, -1, q, -s, 1, q, -s
DATA 0, -1, t, -p, -2, r, p, -2, r, -1, -q, s, 1, -q, s
DATA 0, -1, -t, -p, -2, -r, p, -2, -r, -1, -q, -s, 1, -q, -s
DATA 1, t, 0, 2, r, -p, 2, r, p, q, s, -1, q, s, 1
DATA 1, -t, 0, 2, -r, -p, 2, -r, p, q, -s, -1, q, -s, 1
DATA -1, t, 0, -2, r, -p, -2, r, p, -q, s, -1, -q, s, 1
DATA -1, -t, 0, -2, -r, -p, -2, -r, p, -q, -s, -1, -q, -s, 1
DATA t, 0, 1, r, -p, 2, r, p, 2, s, -1, q, s, 1, q
DATA t, 0, -1, r, -p, -2, r, p, -2, s, -1, -q, s, 1, -q
DATA -t, 0, 1, -r, -p, 2, -r, p, 2, -s, -1, q, -s, 1, q
DATA -t, 0, -1, -r, -p, -2, -r, p, -2, -s, -1, -q, -s, 1, -q
