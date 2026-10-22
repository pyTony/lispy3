100 k4nu_c1x7j=0
110 REPEAT
120   k4nu_c1x7j=k4nu_c1x7j+1
130   WHILE k4nu_c1x7j < 3
140     IF k4nu_c1x7j = 1 THEN EXIT REPEAT
150     IF k4nu_c1x7j = 2 THEN EXIT WHILE
160   WEND
170 UNTIL k4nu_c1x7j >=3
180 PRINT k4nu_c1x7j
