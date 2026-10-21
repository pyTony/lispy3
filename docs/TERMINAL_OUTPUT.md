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

For a BASIC buffer, **F5/F6** run selected text/current line or the whole
buffer using **Lispy mini-basic**. **F7/F8** explicitly use **Python mini_basic**
for the same two scopes. No backend selection is needed. Run a complete loop,
procedure or multiline block together rather than an incomplete opening line.

**Shift+F7** inspects a symbol. For Lisp buffers F5/F6 retain form/buffer
execution in the workspace. For Python buffers they run selected text/current
line or the buffer in a fresh Python process with output, timing and Stop.
Python traceback lines map back to the buffer; Python definitions do not persist
between runs. The configured Python executable is shared with the external
BASIC runner. Only syntax implemented by the chosen interpreter is supported.

Choose **Eval → BASIC Settings…** and select **Listener** or **ANSI terminal** for either BASIC
interpreter. New ANSI windows wait for Enter after execution. Status, timing
and located error highlights stay in the editor. This redirects output only;
console input is not connected to the terminal viewer. **BASIC Settings** keeps
Python location and SDL graphics options. Disable SDL for terminal-only BASIC
programs to avoid drawing/mirroring through a second output window.

## Time the whole buffer

Enable **Eval → Time buffer runs**, then use either **Run whole buffer (F6)**
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
