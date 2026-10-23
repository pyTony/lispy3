OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/nested-exit.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
n=0
WHILE n<2
n+=1
FOR j=1 TO 5
IF j=2 THEN EXIT FOR
NEXT
PRINT ;n;",";j
ENDWHILE
OSCLI "SPOOL":QUIT
