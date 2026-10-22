# Mandelbrot using Lispy3 SDL graphics (no turtle)

Uses the graphics bindings you already installed (`graphics-rgb-mode`, `graphics-open`, `graphics-pixel`, `graphics-present`). No additional patching or installation is needed.

1. Copy `mandelbrot_graphics.lisp` into `C:\Users\admin\lispy3-main\lisp\programs\`.
2. From `C:\Users\admin\lispy3-main`, run:

   ```powershell
   python lispy3.py lisp/programs/mandelbrot_graphics.lisp
   ```

3. A 640x480 SDL window displays the Mandelbrot set. The actual calculation uses a 160x120 RGB buffer and nearest-neighbour scaling, so the prototype runs with fewer interpreter calculations. The set is black, and the outside is coloured.

To get more detail, increase `mandel-w` and `mandel-h` together, e.g. 240 and 180, or increase `mandel-iter` from 48 to 80 (both increase computation time). The view can be moved by changing `mandel-x`, `mandel-y`, and `mandel-step`.

Close the SDL window with its close button or Escape. Both demos continue
polling events after rendering, sleeping between polls so the finished picture
stays responsive. Closing during rendering prevents subsequent presents from
redrawing the closed window. The calculation may still finish its remaining
rows; use Lispy Machine's Stop action to interrupt it immediately.

**Limitation:** Unlike the original turtle version, this example does not yet
implement mouse-wheel zoom. Events are handled by `graphics-present`, every
eight rows during rendering, so a long group of rows can delay the response.
To draw another view, change the constants and run it again.
