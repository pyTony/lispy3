# ANSI terminal output and buffer timing

In Lispy Machine, choose **Eval → Eval buffer in ANSI terminal** to send a
buffer's printed output to a real terminal. Evaluation uses the current Lisp
workspace, so definitions and changes to existing variables remain available.
Results, errors and Inspector updates still appear in the GUI.

Programs can request the same output destination:

```lisp
(with-ansi-terminal
  (load "programs/mandelbrot-terminal-lib" :silent)
  (mandelbrot-terminal #t 79 25 40))
```

An attached terminal is reused. Otherwise a terminal output window opens and
stays open after execution until you press Enter. Nested requests reuse the
current output destination. Input is not redirected. Stop still interrupts
evaluation, and terminal attributes are reset when evaluation finishes or fails.
The body of `with-ansi-terminal` has the scope of a lambda body.

The existing **View → Open terminal** command opens an ordinary shell.
Windows uses Windows Terminal when available, or a console window. Linux uses
an installed terminal emulator; `TERMINAL` can name a preferred executable.
macOS uses Terminal. Missing emulators and connection failures report errors.

## Time the whole buffer

Enable **Eval → Time buffer runs**, then use either **Eval whole buffer (F6)**
or **Eval buffer in ANSI terminal**. The Listener reports, for example:

```text
;; Buffer elapsed time: 0.946 s
```

Timing is off by default. It measures elapsed wall time on the evaluation
thread, including evaluation, output and terminal startup when needed. It
excludes initial parsing and time spent keeping the output window open after
execution. A failed or stopped run also reports its elapsed time.

## Load without a status message

```lisp
(load "programs/mandelbrot-terminal-lib" :silent)
```

`:silent` suppresses the loader's returned status message. Explicit output
from the loaded program and errors remain visible. Imports are already quiet.
Use Lisp call syntax for paths; Python's `r"..."` prefix is not supported:

```lisp
(load """C:\Users\admin\lispy3-main\lisp\programs\mandelbrot-basic-terminal-colour.lisp""")
```
