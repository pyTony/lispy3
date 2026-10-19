REM dialect: bbc
REM Count primes below N by trial division
N%=5000
C%=0
FOR I%=2 TO N%
  P%=TRUE
  D%=2
  WHILE D%*D%<=I% AND P%
    IF I% MOD D%=0 THEN P%=FALSE
    D%+=1
  ENDWHILE
  IF P% THEN C%+=1
NEXT I%
PRINT "Primes below ";N%;": ";C%
