OSCLI "SPOOL ""C:/Users/admin/.codex/worktrees/basic-structured-reference/lispy3-main/basic/reference/runs/structured-2026-10-23/early-fn.txt"""
ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT
PRINT ;FNsign(-5);",";FNsign(0);",";FNsign(7)
OSCLI "SPOOL":QUIT
DEF FNsign(x)
IF x<0 THEN =-1
IF x=0 THEN =0
=1
