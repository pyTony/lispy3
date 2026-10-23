OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/exit-for.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
FOR i=1 TO 10
IF i=3 THEN EXIT FOR
NEXT
PRINT ;i
FOR j=1 TO 2:PRINT ;j;:NEXT:PRINT
OSCLI "SPOOL":QUIT
