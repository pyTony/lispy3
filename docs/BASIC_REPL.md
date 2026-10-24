# Lispy mini-basic REPL

Choose **View → Listener mode → BASIC REPL** in Lispy Machine. The prompt changes
to `BASIC>`. Switch back to **Lisp REPL** or **Lisp Listener (USER>)** in the same
menu. The choice is saved between launches. Mode changes wait until the current
evaluation has finished; Stop / Ctrl+Break interrupts a running BASIC program.

Type BASIC directly, without a Lisp wrapper:

```basic
PRINT 2+3
n=7
PRINT ;n
10 FOR i=1 TO 3
20 PRINT ;i
30 NEXT
LIST
RUN
```

| Input | Action |
|---|---|
| BASIC statement without a line number | Execute immediately; retain session variables |
| `10 PRINT "Hello"` | Store or replace line 10 without executing it |
| `10` | Delete line 10 |
| `LIST` | Show the stored program in numeric order |
| `RUN` | Reset BASIC runtime state and execute the stored program |
| `NEW` | Clear the program and reset BASIC runtime state |
| `LOAD "file.bas"` | Read the program and open/select its editor buffer; do not run it |
| `SAVE "file.bas"` | Write the numbered stored program as UTF-8 text |
| `HELP` | Show a short command reminder |

The program and runtime are private to this BASIC session. Switching to Lisp or
running an editor buffer does not discard them. Lisp New/push/pop operations do
not change the BASIC session. After RUN its results remain available to direct
BASIC statements; the next RUN starts fresh. NEW leaves Lisp definitions alone.
Closing Lispy Machine discards unsaved BASIC session state, so use SAVE or
**To buffer** to retain it. To buffer opens the stored program as editable BASIC;
it does not convert the immediate-command history into a program.

Program lines may be entered in any order; bare line numbers delete them.
Unnumbered files receive line numbers in steps of ten when loaded. In mixed
files, unnumbered lines are fitted into available gaps while explicit jump
destinations stay unchanged. If no gap is available LOAD reports an error and
keeps the old program. Read failures also preserve the old program.

LOAD supports `.bbc` through the configured Python mini_basic decoder in
**BASIC Settings**. SAVE writes plain text and refuses `.bbc`, which is a
tokenised format. Filenames must be quoted; embedded BASIC quotes use `""`.
Relative BASIC paths resolve from the project's `basic/` directory, also used
by filename completion. For example, `LOAD "examples/structure.bas"` loads the
included example. Absolute paths work as well; Lisp keeps its usual working
directory. A successful LOAD
changes program text; it does not reset already existing immediate variables
until RUN or NEW.

Tab / Ctrl+Space completes BASIC keywords and LOAD/SAVE filenames. Directory
names end in `/` so the next path component can be completed. Spaces are allowed
inside quoted filenames; add the closing quote yourself. Lisp `load`, `save`,
`slurp` and `bbc-load` quoted paths also support completion in the Listener.

The REPL uses the existing BBC-style reader: BASIC keywords require uppercase.
Its implemented language subset and compatibility limits are unchanged; see
[mini-basic](MINI_BASIC.md). Immediate input is submitted one line at a time.
For multiline IF, PROC/FN or loop bodies, store numbered lines or LOAD a file
and RUN it. Errors abort the current submitted batch and return to the prompt;
runtime failures leave partial BASIC state available for inspection.

The Listener captures text without interpreting ANSI controls. F6/Shift+F6 set
the shared output destination as before; BASIC REPL execution respects it. Use
ANSI terminal output for colour/cursor commands. LIST/HELP output stays
in the Listener regardless of the program output destination; the BASIC prompt also remains there.

## Standalone terminal

```sh
python -m lispy_support.basic_repl
```

The same program-editing and runtime commands work; `QUIT` exits. Tab completion
is enabled when Python readline is available. Standalone LOAD handles text;
tokenised LOAD currently requires Lispy Machine's configured decoder.

LOAD opens normal text as a saved editor buffer and tokenised input as an
editable .bas copy. An existing clean buffer is refreshed; dirty edits are kept
and a notice explains that LOAD read the disk version. GUI RUN uses the current
editor buffer (including unsaved edits); standalone RUN uses the stored program.
NEW clears the session program/state and leaves editor buffers intact.

File shortcuts Ctrl+O/S/N/W/Q and Ctrl+Shift+S work with Caps Lock on or off.

Ctrl+L clears the GUI REPL output while preserving the live prompt and pending
input. It works in Lisp/BASIC REPL and the Listener entry, including Caps Lock.

## Number printing compatibility

Use `python -m lispy_support.basic_repl --print-style mbasic` for Microsoft-style
spaces around numeric PRINT values, or `--print-style bbc` for the default.
The choice survives NEW/RUN workspace resets. In Lispy Machine, select
**Eval → BASIC Settings… → Lispy BASIC number printing**; the choice is saved
and applies to the next Listener or ANSI run. See [numeric PRINT spacing](MINI_BASIC.md#optional-mbasic-numeric-print-spacing)
for exact scope and examples.
