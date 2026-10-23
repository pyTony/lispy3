OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/early-fn-loop.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
i=99:limit=999
PRINT ;FNfirst(50);",";i;",";limit
OSCLI "SPOOL":QUIT
DEF FNfirst(limit)
LOCAL i
FOR i=1 TO 100
IF i*i>limit THEN =i
NEXT
=-1
