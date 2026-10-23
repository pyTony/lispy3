OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/dynamic-local.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
v$="global"
PROCouter
PROCshow
OSCLI "SPOOL":QUIT
DEF PROCouter
LOCAL v$
v$="outer"
PROCshow
ENDPROC
DEF PROCshow
PRINT v$
ENDPROC
