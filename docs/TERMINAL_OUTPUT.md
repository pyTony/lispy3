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

## Run BASIC source from the editor

Use **F7** (**Run BASIC selection or line**) to execute selected BASIC text,
or the current line when there is no selection. Use **F8** (**Run whole BASIC
buffer**) for a complete program, including unsaved buffers. These commands
automatically import mini-basic's reader with a private editor prefix; no Lisp
wrapper or temporary file is needed. Run a whole loop, procedure or multiline
block together rather than an incomplete opening line.

**Shift+F7** now inspects the symbol at the cursor. **F5/F6** retain their Lisp
evaluation commands. BASIC runs use the current workspace and the normal
Listener output, Stop action and **Time buffer runs** option. Only syntax
implemented by lispy3 mini-basic is supported.

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
