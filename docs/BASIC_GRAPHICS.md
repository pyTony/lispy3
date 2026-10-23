# BASIC graphics implementation

Status: implementation in progress, 2026-10-23.

This batch restores the saved independent RGB framebuffer and Lisp graphics
primitives, then connects MODE, GCOL, MOVE, DRAW, PLOT (absolute move/line/point),
ORIGIN and CLG to the BASIC reader. Window creation is optional for Lisp and
uses pygame only when requested. Tests will exercise pixels without a display
and verify closing/presenting through SDL's dummy display. Unsupported modes
and drawing actions must fail clearly rather than silently approximate.

Reserved scope: graphics_modes.py, lispy_graphics.py,
lispy_graphics_bindings.py, graphics-only standard_env/CLI hooks in lispy3.py,
graphics-only dispatch/polling in lispy_machine.pyw, graphics keyword/macro/
reader clauses in lisp/mini-basic.lisp, new graphics tests/examples and this
document. Terminal ANSI/VDU decoding, PRINT, file I/O and restoration remain
with Claude. Existing PRs retain their other named sections.
