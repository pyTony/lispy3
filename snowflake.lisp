(begin
     (tracer 0 0)
     (pu)
     (goto -120 160)
     (pd)
     ;; Direct call to draw-sys (Axiom, Rule, Depth, Step, Angle)
     (draw-sys (seq "F-F-F-F-F") "F-F++F+F-F-F" 4 2 72)
     (update))