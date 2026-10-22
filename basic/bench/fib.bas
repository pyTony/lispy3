REM dialect: bbc
PRINT FNfib(22)
END
DEF FNfib(n)
IF n<2 THEN =n
=FNfib(n-1)+FNfib(n-2)
