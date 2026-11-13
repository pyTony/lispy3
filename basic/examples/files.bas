REM dialect: bbc
REM BBC BASIC file I/O: OPENOUT, PRINT#, BPUT#, OPENIN, INPUT#, BGET#, GET$#,
REM EOF#, PTR#, EXT#, OPENUP and CLOSE#
F% = OPENOUT "files-test.dat"
PRINT #F%, "hello", 42, 2.5, -7
BPUT #F%, "a line"
BPUT #F%, 65
CLOSE #F%
F% = OPENIN "files-test.dat"
PRINT "length "; EXT#F%
INPUT #F%, a$, n%, x, m
PRINT a$, n%, x, m
PRINT "at "; PTR#F%
l$ = GET$#F%
PRINT l$
b% = BGET#F%
PRINT b%, EOF#F%
PTR#F% = 0
INPUT #F%, a$
PRINT a$
CLOSE #F%
F% = OPENUP "files-test.dat"
PTR#F% = EXT#F%
BPUT #F%, "more";
CLOSE #F%
F% = OPENIN "files-test.dat"
PTR#F% = EXT#F% - 4
n% = 0
WHILE NOT EOF#F%
  c$ = CHR$(BGET#F%) : PRINT c$; : n% += 1
ENDWHILE
PRINT : PRINT n%
CLOSE #0
PRINT OPENIN "no-such-file.dat"
