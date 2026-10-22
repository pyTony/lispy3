# ANSI terminal output and buffer timing

In Lispy Machine, choose **Eval → Run program → ANSI terminal (Shift+F6)** to send a
program's printed output to a real terminal. F6/Shift+F6 start a fresh Lisp
workspace; definitions and results remain available afterward for inspection.
Use F5, Ctrl+Shift+Enter or Listener input to evaluate in the current workspace.
Results, errors and Inspector updates still appear in the GUI.

Programs can request the same output destination:

```lisp
(with-ansi-terminal
  (load "programs/mandelbrot-terminal-lib" :silent)
  (mandelbrot-terminal #t 79 25 40))
```

An attached terminal is reused. Otherwise a terminal output window opens and
stays open after execution until you press Enter. Nested requests reuse the
current output destination. BASIC `INPUT` / `INPUT LINE` and Lisp `read-line`
read replies in that terminal. Stop still interrupts evaluation and input waits,
and terminal attributes are reset when evaluation finishes or fails. Closing the
terminal during input reports an error in the editor instead of hanging.
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

Use **F6 → Listener** or **Shift+F6 → ANSI terminal** for the whole buffer.
The last destination is saved and reused by F5/F7/F8 and Listener evaluation;
there is no separate output selection in BASIC Settings. New ANSI windows wait
for Enter after execution. Status, timing and error highlights stay in the editor.
Lispy mini-basic `INPUT` / `INPUT LINE` accepts replies in the selected output
destination, including the ANSI viewer. The Python mini_basic subprocess adapter
still has no interactive input bridge. BASIC Settings keeps Python locations
and SDL graphics options. Disable SDL for terminal-only BASIC programs.
The [real BBCSDL command](BBCSDL.md) uses its own window independently.

## Time the whole buffer

Enable **Eval → Time buffer runs**, then use either **Run program → Listener (F6)**
or **Run program → ANSI terminal (Shift+F6)**. The Listener reports, for example:

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

See [workspaces](WORKSPACES.md) for Run/Eval isolation and explicit push/pop.
