# mini-basic in lispy3

mini-basic reads a subset of BBC BASIC text and expands it into lispy3 code.
It is separate from the Python `pyTony/mini_basic` interpreter: features in that
project are not automatically available here.

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
| Output | PRINT, semicolon/comma separators, SPC, TAB, string functions including CHR$ |
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

## Terminal output and ANSI escapes

PRINT can emit escape bytes with `CHR$(27)`. An ANSI-capable terminal interprets
those bytes; mini-basic itself does not provide a terminal emulator.

```basic
PRINT CHR$(27);"[31mRed text";CHR$(27);"[0m"
```

`[31m` selects red foreground and `[0m` restores terminal attributes. Always
restore attributes after an example. Run this in the command-line REPL for a
terminal display: the Lispy Machine's Tk Listener captures text and does not
interpret ANSI control sequences as terminal commands.

Current limits matter for screen-oriented programs:

- CLS, COLOUR and VDU are not implemented as BASIC statements.
- TAB(n) pads to an output column, starting a new line if necessary.
- TAB(x,y) currently uses x only; it does not position a screen cursor at y.
- Escape bytes count toward the formatter's output column, so mixing ANSI escapes
  with TAB, comma zones or numeric alignment can misalign output.

Raw escape output is useful for simple colour text; it does not establish full
ANSI screen support. Terminal capabilities and Windows console configuration
also determine what is displayed.

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
python -m pytest tests/test_mini_basic.py tests/test_mini_basic_reader.py tests/test_mini_basic_tdd.py tests/test_mini_basic_time.py -q
```

[TODO.md](../TODO.md) records completed fixes and remaining compatibility work.
The reference directory records native BBCSDL observations separately from
lispy3 tests. Prioritize demonstrated errors over expanding the language.
