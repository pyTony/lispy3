# mini-basic in lispy3

Pure BASIC `FN` definitions are automatically wrapped with `memoize-exact`.
Each call is cached only when **every argument value is an exact number**
(an integer or fraction). Floating-point, mixed exact/inexact, boolean, string,
complex and container arguments bypass the cache. The return type does not
affect eligibility. Integer factorial/Fibonacci calls still benefit; ordinary
floating-point Mandelbrot coordinates do not fill the cache.

Lisp `define-memo` uses the same policy. Explicit `(memoize f)` retains its
general cache, including floating-point keys; `(memoize-exact f)` explicitly
selects the restricted policy. Restart or reload/redefine existing functions
after updating: previously created cache wrappers keep their old behaviour.

mini-basic reads a subset of BBC BASIC text and expands it into lispy3 code.
It is separate from the Python `pyTony/mini_basic` interpreter: features in that
project are not automatically available here.

## Optional MBASIC compatibility

Choose **Eval → BASIC Settings… → Lispy BASIC compatibility → MBASIC**.
The saved preference applies to subsequent Lispy BASIC buffer and REPL runs,
including output sent to the ANSI terminal. **BBC** is the default and restores
the existing right-justification/semicolon behavior.

In MBASIC spacing mode, nonnegative decimal numbers have a leading space, negative
numbers have their minus sign, and every number has a trailing space. Thus an old
line such as `PRINT "DESTROY THE";19;"KLINGON WARSHIPS"` prints
`DESTROY THE 19 KLINGON WARSHIPS` without editing the source. Adjacent positive
numbers naturally have two spaces between them. This follows Microsoft's
[numeric PRINT spacing rules](https://www.pcjs.org/documents/books/mspl13/basic/b7lang/).

For Lisp-driven BASIC:

```lisp
(import (only mini-basic bbc-run bbc-set-print-style!))
(bbc-set-print-style! :mbasic)
(bbc-run "PRINT \"DESTROY THE\";19;\"KLINGON WARSHIPS\"")
(bbc-set-print-style! :bbc)
```

The standalone BASIC REPL accepts:

```text
python -m lispy_support.basic_repl --print-style mbasic
```

The same MBASIC option also makes keywords, variable names, array names and
PROC/FN names case-insensitive: `A=1:print a` prints ` 1 `. Quoted strings,
comments and unquoted DATA values retain their spelling. Selecting BBC restores
case-sensitive syntax. Change the option before loading/running definitions;
previously defined names are not renamed retroactively.

MBASIC style also prints an inexact number the way MBASIC prints a single:
rounded to single precision, at most 6 significant digits and no `0` before the
point, so `PRINT 1/3` gives ` .333333 ` and `PRINT 3.14159265*25` gives
` 78.5398 `. `STR$` does the same. `(set! bbc-single-precision #f)` turns this
filter off and shows the full value (useful for `#` doubles). `WEND` ends a
`WHILE` loop like `ENDWHILE`.

MBASIC style also reads MBASIC's own operators, functions and spellings
(`lisp/mini-basic-mbasic.lisp`):

```basic
PRINT 17 \ 5, 17 MOD 5            ' 3 and 2: integer division and remainder
PRINT 5 XOR 3, 5 EQV 3, 5 IMP 3   ' 6, -7 and -5, bit by bit like AND and OR
PRINT FIX(-2.7), CINT(-2.7)       ' -2 (toward zero) and -3 (nearest)
PRINT HEX$(255), OCT$(8)          ' FF and 10
A$ = "A" + SPACE$(5) + STR$(42)   ' "A      42": STR$ keeps the sign space
B! = CSNG(X#) : D# = CDBL(C!)
RANDOMIZE 42 : PRINT RND          ' the same numbers again after RANDOMIZE 42
DEF FN SQUARE(X) = X * X : PRINT FN SQUARE(5)
```

The operators bind as in MBASIC, tightest first: `^`, unary `-`, `*` `/`,
`\`, `MOD`, `+` `-`, comparisons, `NOT`, `AND`, `OR`, `XOR`, `EQV`, `IMP`.
So `-2^2` is -4, `10 + 7 MOD 3` is 11 and `NOT A = B` is `NOT (A = B)`.
`\` and `MOD` round their operands to whole numbers first, as `CINT` does,
and so does assigning to an integer variable: `A% = 10.7` gives 11. `CINT`
rounds halves away from zero and gives Overflow outside -32768 to 32767;
`HEX$` and `OCT$` show a negative number as its 16-bit pattern (`HEX$(-1)` is
`FFFF`). `STRING$(5, 42)` repeats the character with code 42. `RND` on its own
is `RND(1)`, a number from 0 up to 1. `RANDOMIZE n` restarts the generator from
seed n; `RANDOMIZE` alone takes a seed from the clock instead of asking for
one. `'` starts a comment like `REM`, and a Ctrl-Z ends the program text, as
it ends a CP/M file. In the BBC style none of these words are keywords and
`\` is an error.

This is a limited compatibility option, not a complete MBASIC dialect.
Explicit USING formatting and existing comma-zone widths retain
their current behavior. Cursor tracking includes the added spaces, so TAB/SPC
still use the actual output column. Arithmetic is done in double precision,
`#` doubles print as singles, and RND is not MBASIC's generator. It does not
configure the external Python/native BBC backends.

## Random numbers

BBC `RND` is supported in BASIC source:

| Form | Result |
| --- | --- |
| `RND` | Next signed 32-bit integer |
| `RND(1)` | Next floating-point value, at least 0 and below 1 |
| `RND(n)`, `n > 1` | Next integer from 1 through n, inclusive |
| `RND(0)` | Last generated value in 0-to-1 format, without advancing |
| `RND(-n)` | Reseed deterministically and return the negative integer argument |

```basic
seed = RND(-123)
PRINT RND(6)
PRINT RND(1)
PRINT RND(0)
```

Numeric arguments are truncated to integers. Empty parentheses, extra arguments
and string arguments report RND-specific errors. Functions that call RND bypass
automatic memoization because they depend on changing state.

State belongs to the loaded BASIC library/workspace and persists across
`bbc-run` calls. A fresh instance starts at seed 1 with last value 0; use negative
seeding to reproduce a sequence. Workspaces do not share their generator state.
The portable generator is a 32-bit linear congruential generator (multiplier
1664525, increment 1013904223), not BBCSDL's generator: supported forms and ranges
follow BBC behavior, but seeded values are not bit-for-bit BBCSDL results.
See [the BBC BASIC author's RND reference](https://www.bbcbasic.net/wiki/doku.php?id=notes_20on_20the_20use_20of_20rnd).

## String-case compatibility extensions

`UCASE$(s$)` and `LCASE$(s$)` return upper/lower-case strings without modifying
s$. They accept exactly one string, preserve string expression typing, and
report a clear error for numeric arguments. Unicode conversion follows Python
mini_basic's string upper/lower behavior (for example, ß uppercases to SS).
These are mini_basic compatibility extensions used by its museum ELIZA/BETH
examples, not native BBC BASIC keywords. BBCSDL instead supplies FNupper and
FNlower through its [fnusing library](https://bbcbasic.co.uk/bbcsdl/manual/bbcsdlg.html).

## Selective imports

Use `(import (only mini-basic bbc-run))` to get the text reader without installing
its parser helpers globally. For terminal macros, for example:

```lisp
(import (prefix (only mini-basic CLS COLOUR ANSI ANSI-RESET) term:))
(term:CLS)
(term:ANSI 27 "[31m")
(term:ANSI-RESET)
```

The [library guide](LIBRARIES.md) explains exports, prefixes, renaming, helper
isolation and workspace-save limits. Existing `load` examples below remain valid.

## Run BASIC text

Start `python lispy3.py` from this checkout, then load the library:

```lisp
(load "mini-basic")
(bbc-run """
FOR i=1 TO 3
PRINT "Hello ";i
NEXT
""")
```

Use `(bbc-load "path/to/program.bas")` for a plain-text file and
`(bbc-expand "PRINT 42")` to inspect the generated code. Tokenized `.bbc`
loading is not implemented. Keywords must be uppercase; identifiers are
case-sensitive. A BASIC file is passed to `bbc-load`, rather than directly to
lispy3's Lisp loader.

As in BBCSDL, an uppercase variable name must not start with a BBC BASIC
keyword: `COUNT%`, `TOTAL` (`TO`) and `ORDER` (`OR`) are syntax errors. BBCSDL
only treats some keywords, such as `COUNT`, `TIME`, `PI` and `END`, as keywords
when no letter, digit or `_` follows, so `COUNTER`, `TIMER` and `ENDING` are
names. Keywords are uppercase only, so lowercase or mixed-case names
(`count%`, `Count%`) never clash; they are the safer choice.

MBASIC compatibility is tested against MBASIC 5.21 output: see
[MBASIC_COMPAT.md](MBASIC_COMPAT.md).

## Current language support

| Area | Implemented |
|------|-------------|
| Values | Numeric and string variables; `%` 32-bit, `%%` 64-bit, `&` byte, `#` float and `$` string suffixes; see [Numbers](#numbers) |
| Output | PRINT (`?` at the start of a statement is short for PRINT), COUNT, POS, VPOS, SPC/TAB, CLS, COLOUR/COLOR, VDU text subset, raw ANSI, CHR$ |
| Input | INPUT numbers, strings and array elements; INPUT LINE for complete strings; GET, GET$, INKEY, INKEY$ keys; see [Keys and other shared statements](#keys-and-other-shared-statements) |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=`; SWAP; `MID$(a$,p,n)=` overwrites part of a string; CLEAR |
| Strings | LEFT$, RIGHT$ (one or two arguments), MID$, INSTR, LEN, STRING$, STR$, VAL, EVAL, UCASE$, LCASE$; `<` `>` `<=` `>=` compare strings |
| Structure | IF/ELSE, FOR/NEXT, WHILE/ENDWHILE, REPEAT/UNTIL, CASE |
| Calls | PROC/FN, parameters, LOCAL, early returns |
| Jumps | Line numbers and `(label)` labels, GOTO, GOSUB/RETURN, ON GOTO/GOSUB and ELSE, calculated `GOTO (expression)`; implicit `IF condition THEN 100 ELSE 200`; see [Labels and jumps](#labels-and-jumps) |
| Data | DATA/READ/RESTORE; DIM arrays with inclusive upper bounds |
| Errors | ON ERROR, ON ERROR LOCAL, ON ERROR OFF, ERR, ERL, REPORT, REPORT$, ERROR n,message; see [Error handling](#error-handling) |
| Timing | Assignable TIME in whole centiseconds |
| Stop | END, STOP, QUIT |

PROC/FN parameters and LOCAL variables restore their previous values on normal
return, BASIC runtime errors and END, including nested calls. This cleanup is
a Lispy execution guarantee, not a claim to reproduce BBCSDL shared-stack error
semantics. Host interrupts such as KeyboardInterrupt are outside this guarantee.

### Labels and jumps

Labels follow BBC BASIC in every mode, including MBASIC. A label is defined
only by its name in parentheses at the start of a statement, and is jumped to
by its bare name. A target in parentheses is a calculated jump: the expression
is evaluated and must give a line number.

```basic
10 n = 2
20 GOTO (n * 10 + 20)  : REM calculated: jumps to line 40
30 PRINT "skipped"
40 GOSUB greet : GOTO done
(greet) PRINT "hello" : RETURN
(done) RESTORE values : READ a : PRINT a
(values) DATA 42
```

The same three target forms (line number, bare `label`, `(expression)`) work
for `GOTO`, `GOSUB`, `RESTORE` and every target of `ON ... GOTO/GOSUB`.
A bare name is always a label and never reads a variable of the same name, so
`dest = 100 : GOSUB dest` looks for a label `(dest)`; write `GOSUB (dest)`
to jump to line 100. Label names are not variables either.

A numeric destination immediately after single-line `THEN` or `ELSE` is an
implicit `GOTO`, as in [BBC BASIC](https://www.bbcbasic.co.uk/bbcbasic/manual/bbckey4.html#then).
For example, `10 IF n<3 THEN 50` jumps to line 50 when true and otherwise
continues to the next line. Unknown destinations report the normal GOTO error.
Bare numeric statements elsewhere remain invalid.
Use structured exits where possible. Jumps into inactive structured bodies are
outside the supported control-flow model. BBCSDL's shared-stack edge cases do
not imply equivalent behavior here; see the
[reference checks](../basic/reference/README.md) for recorded results and limits.

### Error handling

```basic
10 ON ERROR PRINT "ERROR ";ERR;" AT LINE ";ERL:REPORT:PRINT:END
20 PRINT 1/0
```

prints `ERROR 18 AT LINE 20` and then `Division by zero`. As in BBC BASIC for
SDL, an error goes to the statements after `ON ERROR` on that line, and the
program then carries on into the following lines unless they jump or `END`.
So `ON ERROR GOTO 1000` works, and a handler that neither jumps nor ends runs
the failing line again. Running a program clears the previous handler.

| Form | Meaning |
|------|---------|
| `ON ERROR statements` | Trap later errors with the rest of the line |
| `ON ERROR LOCAL statements` | The same; inside a PROC or FN the previous handler returns when it returns |
| `ON ERROR OFF` | Errors stop the program again |
| `ERR` | BBC error number of the last trapped error |
| `ERL` | Numbered line where it happened; 0 in a program without line numbers |
| `REPORT$`, `REPORT` | Its message; REPORT prints it |
| `ERROR n, message$` | Raise error n with your own message |

Lispy errors get BBC numbers and messages: Division by zero (18), Subscript
out of range (15), Too big (20), Log range (22), No such variable (26),
No such FN/PROC (29), No GOSUB (38), ON range (40), No such line (41),
Out of DATA (42) and Type mismatch (6). Any other error has ERR 0 and Lispy's
own message. Stop in Lispy Machine is never trapped.

An error goes to the handler in the body that set it while that body is
running: the program, or the PROC, FN or loop body holding the `ON ERROR`.
When that body has already finished (an `ON ERROR` in a set-up PROC that has
returned), the handler's statements run on their own and the program ends
after them, instead of continuing at BBCSDL's text position. PROC/FN
parameters and LOCAL variables are restored on the way out, as for any
error (the Lispy guarantee above). `LOCAL ERROR`/`RESTORE ERROR`,
`ERROR EXT` and trapping Escape are not supported. ERL tracking is compiled
only into programs that use ERL.

Graphics, file I/O and general BBCSDL compatibility remain outside the
current implemented subset. SBCL/Clojure comparison backends have a smaller
feature set; lispy3 support does not establish backend parity.

## Keys and other shared statements

These work in both the BBC and the MBASIC style (`lisp/mini-basic-more.lisp`):

```basic
SWAP a, b : SWAP name$(i), name$(j)
a$ = "hello" : MID$(a$, 2, 3) = "ELP"     : REM a$ is now hELPo
total *= 2 : share /= people
PRINT STRING$(3, "ab"), EVAL("2*PI"), LEFT$("abc"), RIGHT$("abc")
IF name$ < "M" THEN PRINT "first half"
k = GET : k$ = GET$ : k = INKEY(50) : k$ = INKEY$(0)
PRINT POS, VPOS
CLEAR : QUIT
```

`MID$(a$, p, n) = b$` never changes the length of `a$`. `EVAL` reads its text
as an expression when it runs; the result counts as a number for `+` and
comparisons, so assign a string result straight to a `$` variable. `CLEAR` sets
every variable of the program back to 0 or `""` and forgets its arrays until
they are given a DIM again. `QUIT` stops the
program like `END`.

`GET` and `INKEY` read keys typed into an open MODE window; the arrows give
136-139 and Home, End, Page Up, Page Down, Insert and Delete 130-135, as in
BBC BASIC for SDL. Escape still closes the window. Without a window the
console has no single keys, so `GET` waits for a typed line and then gives its
characters one at a time, ending with 13 for Return. `INKEY(n)` waits up to n
centiseconds for a key and gives -1 when none came; without a window it only
sees characters left over from a line `GET` read. `INKEY$` is the same as a
string, `""` for none. `INKEY` with a negative number, which scans one key in
BBC BASIC, gives 0 (FALSE): keys are not scanned.

In the MBASIC style, a BBC keyword that the program assigns to, such as
`COUNT = 0` or `PI = 3.14159`, is an ordinary variable everywhere in that
program, as in MBASIC, which has no `COUNT` or `PI`. A program that only reads
`PI` still gets the constant. The BBC style keeps rejecting these names.

## Console input

```basic
INPUT "Name: " name$
INPUT "Age", age%
INPUT x,y
INPUT LINE "Message: " message$
INPUT "PRESS ENTER", pause$
```

In the editor, type replies in the BASIC CLI and press Enter. Replies are
program data, including text such as `RUN`. Stop interrupts an input wait.
The standalone `python -m lispy_support.basic_repl` reads replies from its terminal. In the
editor, ANSI terminal output also reads replies in that terminal; Listener
output reads replies in the BASIC CLI. Stop interrupts either input wait.

As in the [BBC BASIC INPUT manual](https://www.bbcbasic.co.uk/bbcbasic/mancpm/bbckey2.html#input),
a comma or semicolon after a prompt adds `?`; omitting the separator suppresses
it. Bare `INPUT x` displays `?`. Supply multiple values separated by commas,
or continue on another line. Quote strings containing commas. Numeric input
uses a number prefix, not expression evaluation: `12tail` gives 12 and `1+9`
gives 1; nonnumeric or empty input gives zero. `%` variables truncate to integers.
`INPUT LINE` preserves spaces, commas and quotes and requires string targets.

This initial subset supports one optional literal prompt per statement. Prompt
positioning with TAB/SPC and interleaved prompt strings are not implemented.
Files are read with `INPUT#` and `LINE INPUT #`: see [File I/O](#file-io).
`LINE INPUT` is the MBASIC spelling of `INPUT LINE`.

## Terminal output: VDU and ANSI

These commands target an ANSI-capable terminal. The Lispy Machine's Tk Listener
handles `CLS` by clearing previous output; it preserves any active prompt and
typed input. It does not otherwise emulate a terminal, so other control bytes
will not produce the same screen there. Windows console configuration also
affects rendering.

VDU and ANSI are separate languages. **VDU and PRINT share the BBC control-byte
decoder; ANSI sends raw bytes/strings unchanged.**
For example, `VDU 17,1` and `ANSI 27,"[31m"` both select red text, but
`ANSI 17,1` sends two literal control bytes, not a colour command.

```basic
CLS
COLOUR 1
PRINT TAB(4,2);"Red at column 4, row 2"
COLOUR 7
REM Equivalent BBC byte-stream style:
VDU 12,17,1,31,4,2
PRINT "Red at column 4, row 2"
REM Explicit ANSI style, including restoring terminal defaults:
ANSI 27,"[31m"
PRINT "Red text"
ANSI 27,"[0m"
```

Coordinates are zero-based; `TAB(x,y)` emits ANSI row y+1, column x+1 and updates
the tracked column. `TAB(n)` remains padding to column n, with a newline if
already past it. Negative cursor coordinates raise an error.

COLOUR (alias COLOR) accepts foreground 0..15 and background 128..143. Colours
0..7 are black, red, green, yellow, blue, magenta, cyan, white; 8..15 select their
bright ANSI counterparts. This fixed palette does not emulate BBC MODE-dependent
palettes. CLS clears and homes the cursor, retaining selected colours.

### Supported VDU subset

| Bytes | Operation |
|-------|-----------|
| 0 | Ignore |
| 7 | Terminal bell |
| 8 | Backspace; tracked column stops at zero |
| 10 | Move down one row, preserving column |
| 12 | Clear and home (CLS) |
| 13 | Carriage return |
| 17,n | Set colour (COLOUR n) |
| 30 | Home cursor |
| 31,x,y | Position cursor (TAB(x,y)) |
| 32..126, 128..255 | Emit characters using lispy3's character encoding |

VDU truncates numeric expressions and takes the low eight bits. Parameter bytes
can span VDU and PRINT statements, including separate runs, until the library
is reloaded. For example, `VDU 17:PRINT CHR$(1);"Red"` completes the colour
command before printing text. Printable Unicode text remains unchanged; a PRINT
character consumed as a parameter contributes its code point modulo 256.
A normal PRINT newline uses stdout's native newline; if a command is pending,
its logical CR/LF bytes (13,10) instead pass through the decoder. Thus a missing
parameter may consume the newline: complete control sequences explicitly.
A parameter is consumed as data, not interpreted as another control. Unsupported
controls, including 22 (MODE) and 27, raise a clear error. Comma-separated bytes
are supported; BBC's semicolon word form is not yet supported. Graphics controls,
text windows, wrapping/scrolling at BBC viewport boundaries and BBC font mappings
are not emulated. In particular, moving down at the terminal bottom is not a
BBC-compatible scrolling implementation.

The [BBC VDU reference](https://www.bbcbasic.uk/bbcbasic/manual/vdu.html) describes
the wider source language; the table above defines the implemented subset.

### Lisp macros and raw ANSI

```lisp
(bbc-program
  (CLS)
  (COLOUR 1)
  (PRINT (TAB 4 2) "Red text")
  (VDU 17 7 31 0 4)
  (ANSI 27 "[32m")
  (PRINT "Green text")
  (ANSI-RESET))
```

`ANSI` also accepts numeric byte lists such as `ANSI 27,91,51,49,109` in BASIC,
or `(ANSI 27 91 51 49 109)` in Lisp. Numeric items use their low eight bits;
strings pass through unchanged. Output uses stdout text encoding; numeric values
128..255 are characters, not a binary-output API. ANSI is a lispy3 extension,
not a BBC keyword.
`(ANSI-RESET)` is a Lisp convenience for `ANSI 27,"[0m"`.

ANSI output bypasses the VDU decoder and printable-column accounting. Use it for
control sequences and PRINT for visible text. Colour sequences leave the tracked
column correct; raw cursor moves, visible strings or line breaks can make it
stale because ANSI is not parsed. Prefer TAB(x,y), CLS or VDU for tracked moves.
`PRINT CHR$(17);CHR$(1);"Red"` now selects red through the same decoder as
`VDU 17,1`. Supported control bytes do not consume printable columns. Raw
`PRINT CHR$(27);"[31m"` now raises the unsupported-VDU-27 error; use
`ANSI 27,"[31m"` for raw escape sequences. There is no automatic
terminal reset on END or an error: restore attributes explicitly when finished.

## Bundled terminal Mandelbrot demos

The repository now includes matching plain and ANSI-coloured terminal renderers
in BASIC and native Lisp. See [Terminal Mandelbrot](TERMINAL_MANDELBROT.md) for
four one-command launchers, source locations and custom-size calls. The BASIC
source is `basic/examples/mandelbrot-terminal.bas`; it no longer requires the
external Python mini_basic checkout. The external demo below is still available.

## TIME and terminal Mandelbrot

```basic
TIME=0
REM calculation here
PRINT "Time: ";TIME/100;" secs."
```

TIME advances while execution runs and persists across `bbc-run`/`bbc-load` calls.
Assignment resets its offset; LET, += and -= are supported. It starts when the
library loads, rather than at machine boot. TIME$ and BBC's 32-bit wrap are not
implemented. Lispy's `(time expression)` includes parsing/loading around the
expression, so its result may be larger than timing inside BASIC.

If you also have the Python mini_basic repository, its plain-text terminal demo
`examples/graphics/mandelbrot/mandelbrot2.bas` runs unchanged:

```lisp
(time (bbc-load "C:/Users/admin/mini_basic/examples/graphics/mandelbrot/mandelbrot2.bas"))
```

Adjust the external checkout path. This file is not bundled in lispy3. A verified
run printed 25 Mandelbrot rows and reported 1.03 seconds inside BASIC versus
1.205 seconds around loading and execution; timings vary by machine.

## File I/O

`lisp/mini-basic-io.lisp` adds BBC BASIC channel I/O:

```basic
F% = OPENOUT "scores.dat"
PRINT#F%, "Ada", 42
CLOSE#F%
F% = OPENIN "scores.dat"
INPUT#F%, name$, score%
CLOSE#F%
```

| Form | Meaning |
|------|---------|
| `OPENIN f$`, `OPENOUT f$`, `OPENUP f$` | open for reading, create for writing, or open for both; a channel number, or 0 when the file cannot be opened |
| `PRINT#c, a, b$` / `INPUT#c, a, b$` | write and read values in BBC BASIC for SDL's layout |
| `BPUT#c, n` / `BPUT#c, s$` | write a byte, or a string and LF; `BPUT#c, s$;` leaves out the LF |
| `BGET#c`, `GET$#c` | read a byte, or a line ending at CR, LF, CR LF or NUL |
| `EOF#c`, `EXT#c`, `PTR#c`, `PTR#c = n` | at the end (-1 or 0), length, position, move |
| `CLOSE#c`, `CLOSE#0` | close one channel, or every channel |

`PRINT#` writes a string followed by CR, a whole number in the 32-bit range as
&40 and 4 bytes (least significant first), and any other number as &FF and an
8-byte IEEE double. The string and whole-number layouts follow BBC BASIC for SDL;
the real-number layout has not been checked against it. Strings are bytes 0-255.
An FN that uses a channel is never memoized. File I/O is lispy3 only: the
SBCL and Clojure comparison backends do not have it.

### MBASIC text files

MBASIC's sequential files are text files, built on lispy3's text streams:

```basic
OPEN "O", #1, "notes.txt"
PRINT #1, "Total:"; 42
WRITE #1, "Bob, Jr.", 30
CLOSE #1
OPEN "notes.txt" FOR INPUT AS #1
LINE INPUT #1, L$ : PRINT L$
INPUT #1, N$, A : PRINT N$; A
WHILE NOT EOF(1) : LINE INPUT #1, L$ : ENDWHILE
CLOSE
```

| Form | Meaning |
|------|---------|
| `OPEN "O", #n, f$` / `"I"` / `"A"` | open file number n (1-255) for output, input or append; the `#` is optional |
| `OPEN f$ FOR OUTPUT AS #n` / `INPUT` / `APPEND` | the same, GW-BASIC spelling |
| `PRINT #n, ...` | write exactly what `PRINT` would show, separators, zones and the MBASIC number spaces included |
| `WRITE #n, a, b$` | values separated by commas, strings in quotes, then a line end |
| `INPUT #n, a, b$` | fields separated by commas or line ends; a quoted field may hold commas |
| `LINE INPUT #n, a$` | a whole line |
| `EOF(n)` | -1 at the end of an input file, else 0 |
| `CLOSE`, `CLOSE n`, `CLOSE #n, #m` | close every file, or the ones named |

On a channel opened with `OPENIN`, `OPENOUT` or `OPENUP`, `PRINT#` and `INPUT#`
keep the binary layout above. Random files (`OPEN "R"`, `FIELD`, `GET`, `PUT`)
are not supported.

## Numbers

`lisp/mini-basic-num.lisp` adds BBC BASIC for SDL's number types and integer
operators on top of the Lisp [bitwise library](QUICK_REFERENCE.md#numbers-and-tests):

```basic
PRINT %1010, &FF, &FFFFFFFF      : REM 10, 255, -1
PRINT 1 << 4, -16 >> 2, -16 >>> 28
PRINT ~255 : a$ = STR$~255       : REM FF
A% = 3.7 : A%% = 2^40 : b& = 300 : x# = 1/4
```

| Form | Meaning |
|------|---------|
| `%1010`, `&FF`, `1E5`, `.5` | binary, hex and decimal constants; up to 8 hex digits are a 32-bit signed number, so `&FFFFFFFF` is -1 |
| `a << n`, `a >> n`, `a >>> n` | shift left, shift right keeping the sign, shift right filling with zeros (32 bits, or 64 for a bigger number); they bind like comparisons, so `1 << 2 + 1` is 8 |
| `PRINT ~n`, `STR$~n` | upper-case hex; a negative number in 32-bit two's complement |
| `A%` | 32-bit integer: a fraction is cut off, outside -2147483648 to 2147483647 is `Number too big` |
| `A%%` | 64-bit integer |
| `A&` | unsigned byte: the low 8 bits, so 300 is 44 and -1 is 255 |
| `A#` | float |
| `A!` | single-precision float, as in MBASIC: rounded to 24 significant bits, so `A! = 1/3` holds 0.333333343 |

`a`, `a%`, `a%%`, `a&`, `a#`, `a!` and `a$` are seven different variables. A `~` in
PRINT applies to the one item after it, as in BBCSDL 1.44a. Arrays (`DIM a%(9)`) do not yet use
these types. The SBCL and Clojure comparison backends have them too
(see [compare/README.md](../compare/README.md)).

## Tests and progress

Acceptance tests are ordinary tests: unfinished behavior should fail before the
implementation is added, rather than being hidden by skip/xfail.

```powershell
python -m pytest tests/test_mini_basic.py tests/test_mini_basic_reader.py tests/test_mini_basic_tdd.py tests/test_mini_basic_time.py tests/test_mini_basic_ansi.py tests/test_mini_basic_output_cleanup.py -q
```

[TODO.md](../TODO.md) records completed fixes and remaining compatibility work.
The reference directory records native BBCSDL observations separately from
lispy3 tests. Prioritize demonstrated errors over expanding the language.

### Lisp factorial and memoization

A normal Lisp `(define fact (lambda (n) ...))` creates an ordinary procedure.
Unlike automatic pure BASIC `FN` handling, it does not request a cache. Use:

```lisp
(define-memo (fact n)
  (if (< n 2) 1 (* n (fact (- n 1)))))
```

Repeated `(fact 60)` calls then reuse exact-argument results, including the
recursive values for 1 through 59. `60.0` bypasses that automatic cache.
A regression counts 60 body evaluations on the first integer call and zero
on the second call or a later `(fact 59)`.

BBC function definitions return with `=expression`; procedures use `ENDPROC`.
`END DEF` is not BBC BASIC syntax. The reader diagnoses it at the END token's
source line and suggests the correct function/procedure form instead of
misreporting the next line as an incomplete DEF header. See the
[BBC BASIC function tutorial](https://www.bbcbasic.co.uk/bbcwin/tutorial/chapter17.html).

## Structured-control reference checks

BBCSDL 1.44a matches ten shared fixtures for structured EXIT, early FN/PROC
returns and parameter/LOCAL restoration. Abandoning an inner FOR before an
outer ENDWHILE is a separate diagnostic: BBCSDL reports error 46; lispy3 keeps
its clean structured continuation as an intentional extension. See
[reference sources, raw results and reproduction](../basic/reference/README.md#structured-exits-returns-and-local-restoration).
Prefer structured exits or normal loop termination for portable programs.

## Interactive BASIC

Choose View → Listener mode → BASIC REPL, or run `python -m lispy_support.basic_repl`.
Lispy Machine starts in Lisp even if the previous session used BASIC.
File → Load BASIC… selects a program, switches to the BASIC REPL and opens
the loaded source in an editor buffer. Set its starting directory under
Eval → BASIC Settings → BASIC examples directory. With no configured directory,
the browser uses the last successfully loaded BASIC program's directory,
then the Python mini_basic project's examples directory, then this project's
`basic/` directory. Missing directories are skipped. Use last loaded clears
the explicit directory setting. Cancelling the browser leaves the mode unchanged.

Numbered lines entered in the BASIC REPL become its own program: RUN executes
those lines and their errors do not highlight unrelated editor buffers.
F5/F6 explicitly run the editor buffer and select it again for subsequent RUN.
REM starts a comment without requiring a following space (`REMM` is a comment).

Direct statements, numbered program editing, RUN/LIST/NEW/LOAD/SAVE and
filename completion are described in [BASIC_REPL.md](BASIC_REPL.md).
