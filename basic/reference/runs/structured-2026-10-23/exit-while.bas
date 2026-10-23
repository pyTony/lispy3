OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/exit-while.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
n=0
WHILE TRUE
n+=1
IF n=3 THEN EXIT WHILE
ENDWHILE
PRINT ;n
FOR j=1 TO 2:PRINT ;j;:NEXT:PRINT
OSCLI "SPOOL":QUIT
