# mini-basic in lispy3

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
| Values | Numeric and string variables; `%` integer and `$` string suffixes |
| Output | PRINT, SPC/TAB, CLS, COLOUR/COLOR, VDU text subset, raw ANSI, CHR$ |
| Structure | IF/ELSE, FOR/NEXT, WHILE/ENDWHILE, REPEAT/UNTIL, CASE |
| Calls | PROC/FN, parameters, LOCAL, early returns |
| Jumps | Labels, GOTO, GOSUB/RETURN, ON GOTO/GOSUB and ELSE |
| Data | DATA/READ/RESTORE; DIM arrays with inclusive upper bounds |
| Timing | Assignable TIME in whole centiseconds |

PROC/FN parameters and LOCAL variables restore their previous values on return.
Use structured exits where possible. Jumps into inactive structured bodies are
outside the supported control-flow model. BBCSDL's shared-stack edge cases do
not imply equivalent behavior here; see the
[reference checks](../compare/reference/README.md) for recorded results and limits.

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

## Tests and progress

Acceptance tests are ordinary tests: unfinished behavior should fail before the
implementation is added, rather than being hidden by skip/xfail.

```powershell
python -m pytest tests/test_mini_basic.py tests/test_mini_basic_reader.py tests/test_mini_basic_tdd.py tests/test_mini_basic_time.py tests/test_mini_basic_ansi.py -q
```

[TODO.md](../TODO.md) records completed fixes and remaining compatibility work.
The reference directory records native BBCSDL observations separately from
lispy3 tests. Prioritize demonstrated errors over expanding the language.
