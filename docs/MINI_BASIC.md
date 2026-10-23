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

## Current language support

| Area | Implemented |
|------|-------------|
| Values | Numeric and string variables; `%` 32-bit, `%%` 64-bit, `&` byte, `#` float and `$` string suffixes; see [Numbers](#numbers) |
| Output | PRINT, SPC/TAB, CLS, COLOUR/COLOR, VDU text subset, raw ANSI, CHR$ |
| Structure | IF/ELSE, FOR/NEXT, WHILE/ENDWHILE, REPEAT/UNTIL, CASE |
| Calls | PROC/FN, parameters, LOCAL, early returns |
| Jumps | Labels, GOTO, GOSUB/RETURN, ON GOTO/GOSUB and ELSE; implicit `IF condition THEN 100 ELSE 200` |
| Data | DATA/READ/RESTORE; DIM arrays with inclusive upper bounds |
| Timing | Assignable TIME in whole centiseconds |

PROC/FN parameters and LOCAL variables restore their previous values on return.

A numeric destination immediately after single-line `THEN` or `ELSE` is an
implicit `GOTO`, as in [BBC BASIC](https://www.bbcbasic.co.uk/bbcbasic/manual/bbckey4.html#then).
For example, `10 IF n<3 THEN 50` jumps to line 50 when true and otherwise
continues to the next line. Unknown destinations report the normal GOTO error.
Bare numeric statements elsewhere remain invalid.
Use structured exits where possible. Jumps into inactive structured bodies are
outside the supported control-flow model. BBCSDL's shared-stack edge cases do
not imply equivalent behavior here; see the
[reference checks](../basic/reference/README.md) for recorded results and limits.

Graphics, INPUT, file I/O and general BBCSDL compatibility remain outside the
current implemented subset. SBCL/Clojure comparison backends have a smaller
feature set; lispy3 support does not establish backend parity.

## Terminal output: VDU and ANSI

These commands target an ANSI-capable terminal. The Lispy Machine's Tk Listener
captures text but does not emulate a terminal, so control bytes will not produce
the same screen there. Windows console configuration also affects rendering.

VDU and ANSI are separate languages. **VDU interprets BBC control bytes and
translates the supported operations; ANSI sends raw bytes/strings unchanged.**
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
can span VDU statements, including separate runs, until the library is reloaded.
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
Raw `PRINT CHR$(27);"[31m"` still works, but counts escape bytes as text and can
misalign later TAB, comma zones or numeric alignment. There is no automatic
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

`a`, `a%`, `a%%`, `a&`, `a#` and `a$` are six different variables. A `~` in
PRINT applies to the one item after it, as in BBCSDL 1.44a. Arrays (`DIM a%(9)`) do not yet use
these types. These extensions are lispy3 only for now: the SBCL and Clojure
comparison backends do not have them.

## Tests and progress

Acceptance tests are ordinary tests: unfinished behavior should fail before the
implementation is added, rather than being hidden by skip/xfail.

```powershell
python -m pytest tests/test_mini_basic.py tests/test_mini_basic_reader.py tests/test_mini_basic_tdd.py tests/test_mini_basic_time.py tests/test_mini_basic_ansi.py -q
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

## Interactive BASIC

Choose View → Listener mode → BASIC REPL, or run `python basic_repl.py`.
Direct statements, numbered program editing, RUN/LIST/NEW/LOAD/SAVE and
filename completion are described in [BASIC_REPL.md](BASIC_REPL.md).
