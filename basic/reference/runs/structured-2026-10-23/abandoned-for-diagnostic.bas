OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/abandoned-for-diagnostic.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
10 n=0
20 WHILE n<2
30 FOR i=1 TO 3
40 n+=1
50 GOTO 80
60 NEXT
80 PRINT ;n
90 ENDWHILE
100 PRINT "done"
110 OSCLI "SPOOL":QUIT
