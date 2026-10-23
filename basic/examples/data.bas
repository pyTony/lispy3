REM dialect: bbc
REM DATA, READ, RESTORE and arrays
DIM a(3), n$(2)
FOR i = 0 TO 3 : READ a(i) : NEXT
READ n$(0), n$(1)
PRINT a(0) + a(1) + a(2) + a(3)
PRINT n$(0); " "; n$(1)
RESTORE
READ x : PRINT x
DATA 1, 2, 3, 4
DATA "hello", "world"
