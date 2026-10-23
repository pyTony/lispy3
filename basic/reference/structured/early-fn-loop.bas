i=99:limit=999
PRINT ;FNfirst(50);",";i;",";limit
END
DEF FNfirst(limit)
LOCAL i
FOR i=1 TO 100
IF i*i>limit THEN =i
NEXT
=-1
