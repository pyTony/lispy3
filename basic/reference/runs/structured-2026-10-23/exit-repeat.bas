OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/exit-repeat.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
n=0
REPEAT
n+=1
IF n=2 THEN EXIT REPEAT
UNTIL FALSE
PRINT ;n
FOR j=1 TO 2:PRINT ;j;:NEXT:PRINT
OSCLI "SPOOL":QUIT
