REM dialect: bbc
REM BBC BASIC for SDL number types: binary, hex, shifts and typed variables
PRINT ;%1010;" ";&FF;" ";&FFFFFFFF
PRINT ;1 << 4;" ";-16 >> 2;" ";-16 >>> 28;" ";1 << 2 + 1
PRINT ~255, 255
PRINT ;~-1;" ";STR$~-2
PRINT ;7 DIV 2;" ";-7 MOD 2;" ";7/2
A% = 3.7 : A%% = 2^40 : b& = 300 : x# = 1/4
PRINT ;A%;" ";A%%;" ";b&;" ";x#
PRINT ;5 AND 3;" ";5 OR 3;" ";5 EOR 3;" ";NOT 0
TIME = 500 : PRINT ;TIME >= 500
