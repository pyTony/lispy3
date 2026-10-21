# Run with real BBC BASIC for SDL

**Eval → Real BBC BASIC for SDL buffer** runs the current, unsaved buffer in
BBCSDL's own window. This is separate from Python mini_basic's SDL graphics.
Output and input belong to BBCSDL, regardless of the Listener/ANSI destination.
The editor waits while that window is open; Stop terminates only that child.
The temporary source remains available until BBCSDL exits. Relative file access
starts in the buffer's directory (or the editor directory for an untitled buffer).

## One-time setup

1. Open `tools/bbcsdl-basrun.bas` in the BBCSDL IDE and save it in **native,
   tokenised format** as `basrun.bbc`. Renaming the extension alone is insufficient.
2. In **Eval → BASIC Settings…**, select the real executable and that helper.
   The known Windows installation is detected automatically:
   `C:\Program Files (x86)\BBC BASIC for SDL 2.0\bbcsdl.exe`.
3. Open BASIC text in Lispy Machine and choose the real BBCSDL buffer action.

The helper is Richard Russell's text loader, licensed CC BY-SA 4.0; its
[original source and explanation](https://www.bbcbasic.net/wiki/doku.php?id=running_a_bas_file_from_the_command_prompt)
are retained in the source header. BBCSDL performs the tokenisation itself.
No source tokenizer is implemented in the editor.

BBCSDL command-line startup expects a native `.bbc` program, not plain `.bas`
text. `*EXEC` reads console input; an isolated startup probe did not enter the
interactive prompt and consume its queued source after the launcher ended.
Consequently this runner uses the documented native loader rather than that
unverified EXEC startup path. The helper must be saved once in BBCSDL. An end-to-end check on 2026-10-21
ran the user-saved native helper against temporary source whose path contained
spaces: BBCSDL printed `NATIVE SDL OK 42` and exited with status 0. Adapter
tests also verify argument handling, unsaved source transfer, cancellation and
actionable configuration errors. Do not append switches after the source path:
the helper treats all remaining command-line text as that filename.

Only real BBCSDL syntax works here. The mini-basic extension `ANSI` is not a
BBCSDL keyword; use BBCSDL's supported terminal/VDU statements for those demos.
