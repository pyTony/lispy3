OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/parameters-local.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
x=1:y=2
PROCdouble(10)
PRINT ;x;",";y
OSCLI "SPOOL":QUIT
DEF PROCdouble(x)
LOCAL y
y=x*2
PRINT ;x;",";y
ENDPROC
