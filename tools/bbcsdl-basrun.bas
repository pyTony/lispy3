REM BBCSDL text-program loader by Richard Russell, April 2019.
REM Source: https://www.bbcbasic.net/wiki/doku.php?id=running_a_bas_file_from_the_command_prompt
REM CC BY-SA 4.0. Save from BBCSDL as native basrun.bbc before use.
IF INKEY(-256)<>&57 IF @platform% AND &40 Accs%% = ]332 ELSE Accs%% = !332
DIM Buff%% 255
IF ASC@cmd$=&22 P% = INSTR(@cmd$,"""",2) ELSE P% = INSTR(@cmd$," ",2)
IF P% = 0 ERROR 0, "No BAS filename specified"
F% = OPENIN MID$(@cmd$,P%+1)
IF F% = 0 ERROR 0, "Couldn't open file " + MID$(@cmd$,P%+1)
DIM Prog%% EXT#F% + 255
Prog%% = (Prog%% + 255) AND -256
PAGE = Prog%%
WHILE NOT EOF#F%
  $Buff%% = GET$#F%
  IF $Buff%%<>"" THEN
    N% = VAL$Buff%%
    WHILE ?Buff%%=&20 OR ?Buff%%>=&30 AND ?Buff%%<=&39 $Buff%% = MID$($Buff%%,2) : ENDWHILE
    REPEAT I%=INSTR($Buff%%,".") : IF I% MID$($Buff%%,I%,1) = CHR$17
    UNTIL I%=0 : REPEAT I%=INSTR($Buff%%,"\") : IF I% MID$($Buff%%,I%,1) = CHR$18
    UNTIL I%=0 : IF EVAL("1RECTANGLERECTANGLE:"+$Buff%%) $Buff%% = $(Accs%%+4)
    REPEAT I%=INSTR($Buff%%,CHR$18) : IF I% MID$($Buff%%,I%,1) = "\"
    UNTIL I%=0 : REPEAT I%=INSTR($Buff%%,CHR$17) : IF I% MID$($Buff%%,I%,1) = "."
    UNTIL I%=0 : L% = LEN$Buff%% + 4 : IF L%>255 ERROR 0, "Line too long"
    $Prog%% = CHR$(L%)+CHR$(N%MOD 256)+CHR$(N%DIV 256)+$Buff%% : Prog%% += L% : ?Prog%% = 0
  ENDIF
ENDWHILE
CLOSE #F% : !Prog%% = &FFFF00
F% = 0 : I% = 0 : L% = 0 : N% = 0 : P% = 0 : RUN
