REM dialect: bbc
REM Operators, functions, strings and PRINT layout
PRINT 7 DIV 2, 7 MOD 2, -7 DIV 2, -7 MOD 2
PRINT 2^10, 10/4, 1/3
PRINT 1 + 2 * 3 - 4, (1 + 2) * 3
PRINT 3 > 2, 3 < 2, 3 = 3, 2 <> 2
PRINT 6 AND 3, 6 OR 3, 6 EOR 3, NOT 0
PRINT TRUE, FALSE
PRINT ABS(-4.5), INT(-4.5), INT(4.5), SGN(-3), SQR(16)
PRINT &FF, &10
a$ = "Hello"
b$ = "World"
c$ = a$ + ", " + b$
PRINT c$; " has "; LEN(c$); " characters"
PRINT LEFT$(c$, 5); "|"; RIGHT$(c$, 5); "|"; MID$(c$, 8, 3); "|"; MID$(c$, 8)
PRINT INSTR(c$, "World"), INSTR(c$, "x")
PRINT ASC("A"), CHR$(66), STR$(42) + "!", VAL("12.5") * 2
PRINT "A";"B";"C"
PRINT "zone","next"
PRINT 1;2;3
PRINT ;1;2;3
PRINT TAB(5);"tab5"
PRINT "x";SPC(3);"y"
PRINT "line1"'"line2"
PRINT "no newline ";
PRINT "here"
list = 5 : t = 2
PRINT list * t
