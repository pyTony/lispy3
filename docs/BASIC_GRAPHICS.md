# BASIC and Lisp framebuffer graphics

This initial batch implements drawing independently of terminal output. BBC
VDU commands and ANSI terminal escapes retain their existing decoder/output
paths; drawing statements call a framebuffer backend directly.

## Quick BASIC check

Open `basic/graphics/mandelbrot-preview.bas` in Lispy Machine, select BASIC
colouring and run with the Lispy BASIC command. The preview deliberately draws
only six central scanlines: 80 samples per row, at most 24 iterations each.
A narrow coloured band, with the Mandelbrot interior black, is the expected
picture; it is not a full-screen render. The calculation follows the existing
Python mini_basic `examples/graphics/mandelbrot/mand_arch.bas` example, using
MOVE/DRAW instead of rectangles and omitting refresh and text-window extensions.

From the project root:

```console
python lispy3.py lisp/programs/mandelbrot-basic-graphics-preview.lisp
```

Close the SDL window or press Escape when done. CLI program execution holds the
window open after evaluation; Lispy Machine pumps window events even while idle.
As in BBC BASIC for SDL, closing the window that `MODE` opened ends a running
BASIC program like `END`, so an endless `REPEAT ... UNTIL FALSE` loop such as
the soccer ball stops instead of drawing on without a window. Lisp programs
are not stopped; they test `(graphics-window-open?)` themselves.
The six-row native SDL-dummy run took about 0.52 seconds inside BASIC (about
0.77 seconds including library setup) on the development machine. These are
smoke-run timings, not a cross-backend benchmark.

The underlying framebuffer can also be used without pygame or a display.
Only opening a window requires pygame, for example `python -m pip install pygame-ce`.

## BASIC subset

| Command | Behavior |
| --- | --- |
| MODE 0/1/2/8/9 | Reset framebuffer, origin, pen and colours; open SDL window |
| COLOUR n,r,g,b | Make logical colour n that RGB colour until the next MODE |
| GCOL c / GCOL 0,c | Select foreground logical colour |
| GCOL 128+c | Select background logical colour for CLG |
| MOVE x,y / PLOT 4,x,y | Move the graphics cursor |
| DRAW x,y / PLOT 5,x,y | Draw an inclusive solid line, then move cursor |
| PLOT 69,x,y / PLOT x,y | Draw a point, then move cursor |
| ORIGIN x,y | Set coordinate offset, preserving the existing physical cursor |
| CLG | Clear graphics to the selected background |
| PLOT 85,x,y | Fill the triangle made by the last two points visited and x,y |
| CIRCLE [FILL] x,y,r | Circle outline or disc around x,y, radius r units |
| RECTANGLE [FILL] x,y,w[,h] | Rectangle from corner x,y, w wide and h (default w) high |
| CLS | In a graphics mode also clears the window to the COLOUR 128+n background |
| \*REFRESH OFF / ON / \*REFRESH | Show only finished frames; automatic showing; show this frame now. `OSCLI "REFRESH ..."` is the same |
| WAIT n | Pause n centiseconds |
| OFF / ON | Hide/show the text cursor (accepted, nothing to hide in the Listener) |

Graphics coordinates span 1280 by 1024 units with a bottom-left origin;
framebuffer inspection uses top-left pixel coordinates. Dimensions are
640x256 (MODE 0), 320x256 (MODE 1), 160x256 (MODE 2), 640x512 (MODE 8) and 320x256 (MODE 9).
MODE 0 has black/white; MODE 1 has black/red/yellow/white. MODE 2/9 use
black, red, green, yellow, blue, magenta, cyan, white, repeated at indices 8–15;
MODE 8 has the same 16. `COLOUR n,r,g,b` (Lisp: `(graphics-palette n r g b)`)
changes one entry, as `basic/graphics/random-shapes.bas` does for each shape.
This is a static palette approximation: flashing and a full Archimedes palette
are not implemented. The preview uses indices 1–7 only.

Unsupported MODE numbers, nonzero GCOL drawing actions and unsupported PLOT
codes report errors. Relative BY forms, other plotting operations, ellipses,
graphics text, programmable palettes, graphics VDU controls and native
BBCSDL pixel equivalence remain future work. Closing a window does not reopen
it on subsequent drawing; MODE or graphics-open explicitly opens it again.

[Drawing commands](https://www.bbcbasic.uk/bbcwin/manual/bbcwin4.html) and
[GCOL/plotting descriptions](https://www.bbcbasic.uk/bbcwin/manual/bbcwin3.html)
provide the BBC reference. This subset is tested against its declared pixel
behavior; no full BBCSDL graphics compatibility claim is made.

## Lisp primitives

```lisp
(graphics-mode 9)              ; select headless framebuffer
(graphics-gcol 1)
(graphics-move 0 0)
(graphics-draw 1279 1023)
(graphics-get-pixel 0 255)     ; RGB list, top-left pixel coordinates
(graphics-open)               ; optional SDL window
(graphics-present)
(graphics-close)
```

`graphics-mode-info` returns mode number, pixel width/height, colour count and
virtual width/height. `graphics-rgb-mode` accepts width/height for a custom RGB
surface. `graphics-pixel`, `graphics-line`, `graphics-clear` take explicit RGB
channels. `graphics-virtual-pixel`, `graphics-virtual-line`, `graphics-plot`,
`graphics-origin` and `graphics-clg` expose the corresponding drawing operations.

Filled shapes take pixel coordinates and optional RGB channels (white by
default): `(graphics-fill-rect x0 y0 x1 y1 r g b)`,
`(graphics-triangle x0 y0 x1 y1 x2 y2 r g b)`,
`(graphics-polygon points r g b)` and `(graphics-circle-fill x y radius r g b)`.
`(graphics-lines points r g b)` draws a joined line through all points in one
call. Points are a flat list `(x0 y0 x1 y1 ...)` or pairs `((x0 y0) ...)`.
`(graphics-refresh #f)` stops showing every change, `(graphics-refresh)` then
shows the finished frame and `(graphics-refresh #t)` returns to automatic.
`graphics-window-open?` reports window state. Each standard environment owns
its framebuffer (including an imported mini-basic library environment); pygame has one active display, so opening another closes the
previous window while keeping its framebuffer. Window primitives (mode
changes, open, present, close and `graphics-window-open?`) dispatch to the
Tk/SDL-owning thread; drawing runs on the calling thread. In a terminal REPL, call graphics-present during a long
non-drawing computation to pump events; the blocking input prompt does not
run a GUI event loop.

## Soccer ball FPS test

`basic/graphics/soccerball.bas` is BBC BASIC for SDL's
`examples/graphics/soccerball.bbc` (zlib licence) without its ON ERROR line.
It rotates the ball with whole-array matrix maths and draws each frame with
CIRCLE FILL and PLOT 85 under `*REFRESH OFF`. The BASIC features it needs:

- `b() = 1, 2, 3, ...` fills an array row by row (one value fills it all);
  `c() = b() . c()` is the matrix product; `a() = b()`, `a() = b() * 2`,
  `a() = b() + c()` work element by element. `a()` and `a` are separate
  variables, as in BBC BASIC.
- `SUM(a())` and `SUM(a(i, lo TO hi))`.
- DATA items such as `t, -p, 2*q` are expressions that a numeric READ
  evaluates; a string READ gets their text.
- `SQR5` reads as `SQR 5`: a keyword followed only by digits is not a name.

`lisp/programs/soccer-ball.lisp` is the same ball written in Lispy, using
`mat*`, `graphics-polygon`, `graphics-circle-fill` and `graphics-refresh`. It
prints the frames per second after 300 frames:

```console
python lispy3.py lisp/programs/soccer-ball.lisp
```

Timings on the development container with the SDL dummy driver: the Lispy
version computes about 210 frames per second, also inside Lispy Machine; the
BASIC original about 40 per second without its `WAIT 1` (26 with it). Inside
Lispy Machine the window itself is redrawn up to 50 times a second.

### Why it is faster

- Drawing only writes the framebuffer, so it runs on the Lisp thread. Only
  opening, presenting and closing the window go to the Tk/SDL thread; before,
  every PLOT or line waited for a round trip there.
- Lines write the bytes directly (about 3.7 times faster), and fills draw
  whole rows at once. The window is redrawn only when the picture changed.
- With `*REFRESH OFF` / `(graphics-refresh #f)` the window shows only frames
  handed over by `*REFRESH` / `(graphics-refresh)`, so nothing flickers.
- Lispy keeps each runtime macro expansion with its form, so a loop body is
  expanded once. BASIC array access compiles to the native `aref`.

## Plain GUI output and terminal REPL

Captured stdout strips ANSI incrementally at the GUI Listener boundary,
including escape sequences fragmented across writes. Direct GUI diagnostics
are also filtered. Printable Unicode, tabs and newlines remain. This does not
translate cursor motion into editor operations. Real ANSI-terminal output is
unchanged; ANSI and BBC VDU decoding remain separate.

Use `python lispy3.py` in a real terminal for an ANSI-capable Lisp REPL, or
`python -m lispy_support.basic_repl` for a standalone BASIC REPL. These run separate sessions
from Lispy Machine; attaching a terminal to the GUI's live workspace is not
implemented.

## Temporary startup file

```console
python lispy3.py --startup my-setup.lisp
python lispy3.py --startup my-setup.lisp -i program.lisp
python lispy_machine.pyw --startup my-setup.lisp --repl
```

`--startup FILE` (also `--startup=FILE`) affects that launch only and does not
write a saved startup preference. The CLI evaluates setup before its program
or REPL. Lispy Machine executes the selected startup once even if its saved
Run startup setting was off; showing the startup buffer still follows the
saved visibility setting. Normal launches keep the existing defaults. Missing
arguments are usage errors; a failing CLI startup does not enter the REPL.

## Progress and validation

- [x] Restore saved independent framebuffer/Lisp primitives.
- [x] Failing-first BASIC commands, state reset, isolation and pixel tests.
- [x] Bounded off-screen line clipping.
- [x] Real SDL dummy-display Quit/Escape and GUI idle event-pump test.
- [x] Six-row BASIC Mandelbrot file checked by interior/exterior pixels.
- [x] Separate plain GUI output from raw ANSI output.
- [x] Per-launch startup override for CLI and GUI.
- [x] Soccer ball batch: fills, refresh control, whole arrays, SUM, DATA expressions.

A native BBCSDL cursor probe (`MODE 9:MOVE 0,0:ORIGIN 4,0:DRAW 4,0`,
then reset ORIGIN and query POINT at x=0,4,8, y=0) returned foreground colour
7 at all three positions. This exposed a saved-backend origin bug; the retained
pixel regression first failed and now checks the corrected continuation.

Final clean-worktree validation (2026-10-23): Windows 650 passed, 4 skipped,
364 subtests; WSL Debian 654 passed, 380 subtests. The real SDL dummy-display
integration test ran on both platforms. The optional cross-Lisp backends
account for the platform count difference.
