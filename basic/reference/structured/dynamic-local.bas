v$="global"
PROCouter
PROCshow
END
DEF PROCouter
LOCAL v$
v$="outer"
PROCshow
ENDPROC
DEF PROCshow
PRINT v$
ENDPROC
