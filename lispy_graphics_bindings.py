"""Register optional Lisp graphics primitives without importing Pygame until open()."""
from __future__ import annotations

from graphics_modes import MODES, GraphicsMode
from lispy_graphics import Graphics

_dispatcher = None

def set_dispatcher(dispatcher):
    """GUI host supplies its owner-thread call function, including library envs."""
    global _dispatcher
    _dispatcher = dispatcher


def install(env, Procedure, String):
    """Install native functions into a single lispy3 environment.

    No global singleton: each environment owns its framebuffer. All GUI calls
    must run on the SDL-owning thread (handled by the Lispy Machine patch).
    """
    current = {"graphics": None, "colour": 1, "pen": (0, 0), "background": 0}

    def gfx():
        if current["graphics"] is None:
            raise RuntimeError("Call (graphics-mode 1) or (graphics-rgb-mode w h) first")
        return current["graphics"]

    def select(mode):
        try:
            mode = MODES[int(mode)]
        except KeyError:
            raise ValueError(f"unsupported graphics MODE {mode}; choose 0, 1, 2 or 9") from None
        old = current["graphics"]
        if old is not None:
            old.close()
        current["graphics"] = Graphics(mode)
        current["colour"] = mode.colours - 1
        current["background"] = 0
        current["pen"] = (0, 0)
        return mode.number

    def rgb_mode(w, h):
        w, h = int(w), int(h)
        mode = GraphicsMode(-1, w, h, 1, ((0, 0, 0),), w, h)  # true RGB drawing, no indexed colour commands
        old = current["graphics"]
        if old is not None:
            old.close()
        current["graphics"] = Graphics(mode)
        current["colour"] = 1
        current["pen"] = (0, 0)
        return [w, h]

    def mode_info(mode=None):
        m = gfx().mode if mode is None else MODES[int(mode)]
        return [m.number, m.width, m.height, m.colours, m.virtual_width, m.virtual_height]

    def rgb(r, g, b):
        return (int(r), int(g), int(b))

    def palette_color(index):
        m = gfx().mode
        i = int(index)
        if not 0 <= i < m.colours or i >= len(m.palette):
            raise ValueError(f"palette index {i} invalid for mode {m.number}")
        return m.palette[i]

    def open_window(w=None, h=None):
        return bool(gfx().open(None if w is None else int(w), None if h is None else int(h)))

    def clear(r=0, g=0, b=0):
        gfx().clear(rgb(r, g, b))
        return []

    def pixel(x, y, r=255, g=255, b=255):
        gfx().pixel(x, y, rgb(r, g, b))
        gfx().maybe_present()
        return []

    def line(x0, y0, x1, y1, r=255, g=255, b=255):
        gfx().line(x0, y0, x1, y1, rgb(r, g, b))
        gfx().maybe_present()
        return []

    def v_pixel(x, y, colour=1):
        gfx().virtual_pixel(x, y, palette_color(colour))
        gfx().maybe_present()
        return []

    def v_line(x0, y0, x1, y1, colour=1):
        gfx().virtual_line(x0, y0, x1, y1, palette_color(colour))
        return []

    def gcol(*args):
        """GCOL colour or GCOL action,colour (only BBC action 0 supported yet)."""
        gfx()
        if len(args) == 1:
            colour = args[0]
        elif len(args) == 2:
            action, colour = args
            if int(action) != 0:
                raise NotImplementedError("GCOL drawing action must be 0 (overwrite) in this implementation")
        else:
            raise TypeError("graphics-gcol expects colour or action, colour")
        colour = int(colour)
        index = colour - 128 if colour >= 128 else colour
        palette_color(index)
        current["background" if colour >= 128 else "colour"] = index
        return []

    def move(x, y):
        gfx()
        current["pen"] = (int(x), int(y))
        return []

    def draw(x, y):
        g = gfx()
        dest = (int(x), int(y))
        start = current["pen"]
        g.virtual_line(*start, *dest, palette_color(current["colour"]))
        current["pen"] = dest
        g.maybe_present()
        return []

    def origin(x, y):
        g = gfx()
        x, y = int(x), int(y)
        old_x, old_y = g.origin
        pen_x, pen_y = current["pen"]
        # The coordinate system changes; the existing physical cursor does not.
        current["pen"] = (pen_x + old_x - x, pen_y + old_y - y)
        g.set_origin(x, y)
        return []

    def present():
        # The surface handles Quit/Escape; host-specific events stay in Python.
        gfx().present()
        return []

    def close():
        if current["graphics"] is not None:
            current["graphics"].close()
        current["graphics"] = None
        current["colour"] = 1
        current["pen"] = (0, 0)
        return []

    def get_pixel(x, y):
        return list(gfx().get_pixel(int(x), int(y)))

    def bbc_mode(number):
        result = select(number)
        open_window()
        return result

    def clg():
        gfx().clear(palette_color(current["background"]))
        gfx().maybe_present()
        return []

    def plot(*args):
        if len(args) == 2:
            code, x, y = 69, *args
        elif len(args) == 3:
            code, x, y = args
        else:
            raise TypeError("PLOT expects x,y or code,x,y")
        code = int(code)
        if code == 4:
            return move(x, y)
        if code == 5:
            return draw(x, y)
        if code == 69:
            v_pixel(x, y, current["colour"])
            current["pen"] = (int(x), int(y))
            return []
        raise ValueError(f"unsupported PLOT {code}; choose 4 (MOVE), 5 (DRAW) or 69 (point)")

    primitives = {
        "graphics-mode": select,
        "bbc-graphics-mode": bbc_mode,
        "graphics-clg": clg,
        "graphics-plot": plot,
        "graphics-rgb-mode": rgb_mode,
        "graphics-mode-info": mode_info,
        "graphics-open": open_window,
        "graphics-clear": clear,
        "graphics-pixel": pixel,
        "graphics-line": line,
        "graphics-virtual-pixel": v_pixel,
        "graphics-virtual-line": v_line,
        "graphics-gcol": gcol,
        "graphics-move": move,
        "graphics-draw": draw,
        "graphics-origin": origin,
        "graphics-present": present,
        "graphics-window-open?": lambda: current["graphics"] is not None and current["graphics"].window_open,
        "graphics-get-pixel": get_pixel,
        "graphics-close": close,
    }
    for name, func in primitives.items():
        def call(*args, function=func):
            if _dispatcher is not None:
                return _dispatcher(function, *args)
            return function(*args)
        env[name] = Procedure(parms=["*args"], body=None, env=env, native_fn=call, name=name)
    return env
