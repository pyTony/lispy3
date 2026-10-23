OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/early-proc-loop.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
i=90:x=1:y=2
PROCearly(10)
PRINT ;x;",";y;",";i
OSCLI "SPOOL":QUIT
DEF PROCearly(x)
LOCAL y,i
y=x*2
FOR i=1 TO 4
IF i=2 THEN PRINT ;x;",";y;",";i:ENDPROC
NEXT
ENDPROC
