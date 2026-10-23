i=90:x=1:y=2
PROCearly(10)
PRINT ;x;",";y;",";i
END
DEF PROCearly(x)
LOCAL y,i
y=x*2
FOR i=1 TO 4
IF i=2 THEN PRINT ;x;",";y;",";i:ENDPROC
NEXT
ENDPROC
