"""Register optional Lisp graphics primitives without importing Pygame until open()."""
from __future__ import annotations

import math

from lispy_support.graphics_modes import MODES, GraphicsMode
from lispy_support.lispy_graphics import Graphics

_dispatcher = None

def set_dispatcher(dispatcher):
    """GUI host supplies its owner-thread call function, including library envs."""
    global _dispatcher
    _dispatcher = dispatcher


# Only these talk to SDL; drawing just writes the framebuffer, so it runs on the
# calling thread instead of waiting for a round trip to the window's thread.
WINDOW_PRIMITIVES = frozenset({
    "graphics-mode", "bbc-graphics-mode", "graphics-rgb-mode", "graphics-open",
    "graphics-present", "graphics-close", "graphics-window-open?"})


def _points(values):
    """Flat (x0 y0 x1 y1 ...) or nested ((x0 y0) ...) coordinates as pairs."""
    values = list(values)
    if values and isinstance(values[0], (list, tuple)):
        return [(p[0], p[1]) for p in values]
    if len(values) % 2:
        raise ValueError("points need an even number of coordinates")
    return list(zip(values[0::2], values[1::2]))


def install(env, Procedure, String):
    """Install native functions into a single lispy3 environment.

    No global singleton: each environment owns its framebuffer. Window calls
    run on the SDL-owning thread through the dispatcher (the Lispy Machine
    sets one); drawing runs directly and the host's window poller shows it.
    """
    current = {"graphics": None, "colour": 1, "pen": (0, 0), "background": 0,
               "previous": (0, 0), "basic": False}

    def shown(g):
        """Without a host poller, present now and then while drawing (CLI)."""
        if _dispatcher is None:
            g.maybe_present()

    def gfx():
        if current["graphics"] is None:
            raise RuntimeError("Call (graphics-mode 1) or (graphics-rgb-mode w h) first")
        g = current["graphics"]
        if current["basic"] and g.closed_by_user:
            # BBC BASIC quits when its window is closed; the program catches this as END.
            raise RuntimeError("bbc:end")
        return g

    def select(mode):
        try:
            mode = MODES[int(mode)]
        except KeyError:
            raise ValueError(f"unsupported graphics MODE {mode}; choose 0, 1, 2, 8 or 9") from None
        old = current["graphics"]
        if old is not None:
            old.close()
        current["graphics"] = Graphics(mode)
        current["palette"] = list(mode.palette)
        current["basic"] = False
        current["colour"] = mode.colours - 1
        current["background"] = 0
        current["pen"] = current["previous"] = (0, 0)
        return mode.number

    def rgb_mode(w, h):
        w, h = int(w), int(h)
        mode = GraphicsMode(-1, w, h, 1, ((0, 0, 0),), w, h)  # true RGB drawing, no indexed colour commands
        old = current["graphics"]
        if old is not None:
            old.close()
        current["graphics"] = Graphics(mode)
        current["palette"] = list(mode.palette)
        current["basic"] = False
        current["colour"] = 1
        current["pen"] = current["previous"] = (0, 0)
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
        return current["palette"][i]

    def set_palette(index, r, g, b):
        """BBC COLOUR n,r,g,b: logical colour n becomes that RGB colour."""
        palette_color(index)
        current["palette"][int(index)] = rgb(r, g, b)
        return []

    def open_window(w=None, h=None):
        return bool(gfx().open(None if w is None else int(w), None if h is None else int(h)))

    def clear(r=0, g=0, b=0):
        gfx().clear(rgb(r, g, b))
        return []

    def pixel(x, y, r=255, g=255, b=255):
        gfx().pixel(x, y, rgb(r, g, b))
        shown(gfx())
        return []

    def line(x0, y0, x1, y1, r=255, g=255, b=255):
        gfx().line(x0, y0, x1, y1, rgb(r, g, b))
        shown(gfx())
        return []

    def v_pixel(x, y, colour=1):
        gfx().virtual_pixel(x, y, palette_color(colour))
        shown(gfx())
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

    def visit(x, y):
        current["previous"] = current["pen"]
        current["pen"] = (int(x), int(y))

    def move(x, y):
        gfx()
        visit(x, y)
        return []

    def draw(x, y):
        g = gfx()
        dest = (int(x), int(y))
        start = current["pen"]
        g.virtual_line(*start, *dest, palette_color(current["colour"]))
        visit(*dest)
        shown(g)
        return []

    def origin(x, y):
        g = gfx()
        x, y = int(x), int(y)
        old_x, old_y = g.origin
        pen_x, pen_y = current["pen"]
        # The coordinate system changes; the existing physical cursor does not.
        current["pen"] = (pen_x + old_x - x, pen_y + old_y - y)
        prev_x, prev_y = current["previous"]
        current["previous"] = (prev_x + old_x - x, prev_y + old_y - y)
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
        current["pen"] = current["previous"] = (0, 0)
        return []

    def get_pixel(x, y):
        return list(gfx().get_pixel(int(x), int(y)))

    def bbc_mode(number):
        result = select(number)
        open_window()
        current["basic"] = True
        return result

    def clg():
        gfx().clear(palette_color(current["background"]))
        shown(gfx())
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
            visit(x, y)
            return []
        if code == 85:
            g = gfx()
            corners = (current["previous"], current["pen"], (int(x), int(y)))
            g.fill_polygon([g.virtual_to_pixel_centre(*p) for p in corners],
                           palette_color(current["colour"]))
            visit(x, y)
            shown(g)
            return []
        if 160 <= code <= 167 or 176 <= code <= 183:
            return arc_or_sector(code, x, y)
        raise ValueError(f"unsupported PLOT {code}; choose 4 (MOVE), 5 (DRAW), 69 (point), "
                         "85 (triangle), 160-167 (arc) or 176-183 (sector)")

    def arc_or_sector(code, x, y):
        """PLOT 160-167 arc, 176-183 sector: the point before last is the centre,
        the last point starts the arc (and sets the radius), anticlockwise to the
        direction of x,y. The low 3 bits are BBC's usual relative/colour choice."""
        g = gfx()
        action = code & 7
        if action in (2, 6):
            raise NotImplementedError(f"PLOT {code}: inverting colours is not supported")
        if action < 4:
            x, y = current["pen"][0] + int(x), current["pen"][1] + int(y)
        if action not in (0, 4):
            (cx, cy), (sx, sy) = current["previous"], current["pen"]
            radius = math.hypot(sx - cx, sy - cy)
            start = math.atan2(sy - cy, sx - cx)
            sweep = (math.atan2(y - cy, x - cx) - start) % (2 * math.pi) or 2 * math.pi
            steps = max(4, math.ceil(sweep * radius * g.width / g.mode.virtual_width / 2))
            arc = [g.virtual_to_pixel_centre(cx + radius * math.cos(start + sweep * i / steps),
                                             cy + radius * math.sin(start + sweep * i / steps))
                   for i in range(steps + 1)]
            colour = palette_color(current["background" if action in (3, 7) else "colour"])
            if code >= 176:
                g.fill_polygon([g.virtual_to_pixel_centre(cx, cy)] + arc, colour)
            else:
                for (x0, y0), (x1, y1) in zip(arc, arc[1:]):
                    g.line(math.floor(x0), math.floor(y0), math.floor(x1), math.floor(y1), colour)
            shown(g)
        visit(x, y)
        return []

    def fill_rect(x0, y0, x1, y1, r=255, g=255, b=255):
        gfx().fill_rect(x0, y0, x1, y1, rgb(r, g, b))
        shown(gfx())
        return []

    def triangle(x0, y0, x1, y1, x2, y2, r=255, g=255, b=255):
        gfx().fill_triangle(x0, y0, x1, y1, x2, y2, rgb(r, g, b))
        shown(gfx())
        return []

    def polygon(points, r=255, g=255, b=255):
        gfx().fill_polygon(_points(points), rgb(r, g, b))
        shown(gfx())
        return []

    def lines(points, r=255, g=255, b=255):
        """Polyline through all points with one call."""
        pts, colour = _points(points), rgb(r, g, b)
        surface = gfx()
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            surface.line(x0, y0, x1, y1, colour)
        shown(surface)
        return []

    def circle_fill(x, y, radius, r=255, g=255, b=255):
        gfx().fill_circle(x, y, radius, rgb(r, g, b))
        shown(gfx())
        return []

    def v_circle_fill(x, y, radius, colour=None):
        g = gfx()
        cx, cy = g.virtual_to_pixel_centre(x, y)
        g.fill_circle(cx, cy, float(radius) * g.width / g.mode.virtual_width,
                      palette_color(current["colour"] if colour is None else colour))
        shown(g)
        return []

    def v_circle(x, y, radius, colour=None):
        g = gfx()
        cx, cy = g.virtual_to_pixel_centre(x, y)
        g.circle(cx, cy, float(radius) * g.width / g.mode.virtual_width,
                 palette_color(current["colour"] if colour is None else colour))
        shown(g)
        return []

    def v_rect(x, y, w, h=None, fill=False):
        """BBC RECTANGLE [FILL] x,y,w[,h]: (x,y) is a corner, w and h the size."""
        g = gfx()
        x, y, w = int(x), int(y), int(w)
        h = w if h is None or h == [] else int(h)
        colour = palette_color(current["colour"])
        if fill and fill != []:
            (x0, y0), (x1, y1) = (g.virtual_to_pixel(x, y), g.virtual_to_pixel(x + w, y + h))
            g.fill_rect(x0, y0, x1, y1, colour)
        else:
            corners = ((x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y))
            for (ax, ay), (bx, by) in zip(corners, corners[1:]):
                g.virtual_line(ax, ay, bx, by, colour)
        shown(g)
        return []

    def cls(colour=0):
        """BBC CLS in a graphics mode also clears the window to text background."""
        if current["graphics"] is not None:
            current["graphics"].clear(palette_color(colour))
            shown(current["graphics"])
        return []

    def refresh(*args):
        """(graphics-refresh) shows the frame; #f/#t turn automatic showing off/on."""
        if current["graphics"] is None:
            return []
        g = gfx()
        if args:
            g.set_auto_refresh(args[0] is not False and args[0] != [])
        else:
            g.refresh()
            if _dispatcher is None and g.window_open:
                g.present()
        return []

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
        "graphics-fill-rect": fill_rect,
        "graphics-triangle": triangle,
        "graphics-polygon": polygon,
        "graphics-lines": lines,
        "graphics-circle-fill": circle_fill,
        "graphics-virtual-circle-fill": v_circle_fill,
        "graphics-virtual-circle": v_circle,
        "graphics-virtual-rectangle": v_rect,
        "graphics-cls": cls,
        "graphics-refresh": refresh,
        "graphics-palette": set_palette,
    }
    for name, func in primitives.items():
        if name not in WINDOW_PRIMITIVES:
            env[name] = Procedure(parms=["*args"], body=None, env=env, native_fn=func, name=name)
            continue
        def call(*args, function=func):
            if _dispatcher is not None:
                return _dispatcher(function, *args)
            return function(*args)
        env[name] = Procedure(parms=["*args"], body=None, env=env, native_fn=call, name=name)
    return env
