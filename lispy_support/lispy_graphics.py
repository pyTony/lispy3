"""Small independent graphics surface: headless RGB first, optional Pygame window.

No dependency on lispy3.py or mini_basic. Pygame is imported only when opening
an actual window. Coordinates accepted by pixel/line are framebuffer pixels;
virtual_pixel/virtual_line use BBC graphics units with bottom-left origin.
"""
import math
import time

_active = None

def pump_windows():
    window = _active
    if window is not None and window.window_open:
        window.present()
    return bool(window is not None and window.window_open)

def close_windows():
    if _active is not None:
        _active.close()


def hold_windows():
    while pump_windows():
        time.sleep(0.02)


from lispy_support.graphics_modes import GraphicsMode, MODE_1, virtual_to_pixel


def _rgb(value):
    if len(value) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in value):
        raise ValueError('RGB must contain three integer channels in [0,255]')
    return tuple(value)


class Graphics:
    """RGB framebuffer. Drawing only touches the bytearray, so any thread may draw;
    open/present/close talk to SDL and belong to the window's owning thread."""

    def __init__(self, mode: GraphicsMode = MODE_1, *, background=(0, 0, 0)):
        self.mode = mode
        self.background = _rgb(background)
        self.pixels = bytearray(bytes(self.background) * (mode.width * mode.height))
        self._pygame = None
        self._screen = None
        self._size = None
        self._origin = (0, 0)
        self._closed = False
        self._last_present = 0.0
        # Every drawing call bumps version; present() blits only a changed picture.
        self.version = 0
        self._shown = None
        # With auto_refresh off (BBC *REFRESH OFF) the window shows only frames
        # handed over by refresh(), so a half-drawn frame never flickers.
        self.auto_refresh = True
        self._frame = None
        self._frame_version = 0

    def maybe_present(self):
        if not self.auto_refresh:
            return
        now = time.monotonic()
        if self.window_open and now - self._last_present >= 1/30:
            self._last_present = now
            self.present()

    @property
    def window_open(self):
        return self._screen is not None

    @property
    def width(self):
        return self.mode.width

    @property
    def height(self):
        return self.mode.height

    def clear(self, color=None):
        rgb = self.background if color is None else _rgb(color)
        self.pixels[:] = bytes(rgb) * (self.width * self.height)
        self.version += 1

    def pixel(self, x, y, color=(255, 255, 255)):
        x, y = int(x), int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset:offset+3] = bytes(_rgb(color))
            self.version += 1

    def get_pixel(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError('pixel is outside framebuffer')
        i = (y * self.width + x) * 3
        return tuple(self.pixels[i:i+3])

    def line(self, x0, y0, x1, y1, color=(255, 255, 255)):
        """Clip to the framebuffer, then draw an integer Bresenham line."""
        x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
        rgb = bytes(_rgb(color))
        width, height = self.width, self.height
        # Liang-Barsky clipping bounds work to visible framebuffer dimensions.
        dx, dy = x1-x0, y1-y0
        lower, upper = 0.0, 1.0
        for direction, distance in ((-dx,x0),(dx,width-1-x0),(-dy,y0),(dy,height-1-y0)):
            if direction == 0:
                if distance < 0:
                    return
            else:
                ratio = distance / direction
                if direction < 0:
                    lower = max(lower, ratio)
                else:
                    upper = min(upper, ratio)
                if lower > upper:
                    return
        x0, y0, x1, y1 = (round(x0+lower*dx),round(y0+lower*dy),
                           round(x0+upper*dx),round(y0+upper*dy))
        self.version += 1
        pixels = self.pixels
        if y0 == y1:                         # horizontal: one slice assignment
            if x0 > x1:
                x0, x1 = x1, x0
            start = (y0 * width + x0) * 3
            pixels[start:start + (x1-x0+1)*3] = rgb * (x1-x0+1)
            return
        dx, dy = abs(x1-x0), -abs(y1-y0)
        sx, sy = (3 if x0 < x1 else -3), (width*3 if y0 < y1 else -width*3)
        err = dx + dy
        offset, end = (y0*width + x0) * 3, (y1*width + x1) * 3
        while True:
            pixels[offset:offset+3] = rgb
            if offset == end:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                offset += sx
            if e2 <= dx:
                err += dx
                offset += sy

    def _span(self, y, x0, x1, rgb):
        """Fill pixels x0..x1 inclusive on row y, clipped; rgb is 3 bytes."""
        if 0 <= y < self.height:
            x0, x1 = max(x0, 0), min(x1, self.width - 1)
            if x0 <= x1:
                start = (y * self.width + x0) * 3
                self.pixels[start:start + (x1-x0+1)*3] = rgb * (x1-x0+1)

    def fill_rect(self, x0, y0, x1, y1, color=(255, 255, 255)):
        """Fill the inclusive rectangle between two corners."""
        x0, x1 = sorted((int(x0), int(x1)))
        y0, y1 = sorted((int(y0), int(y1)))
        rgb = bytes(_rgb(color))
        for y in range(max(y0, 0), min(y1, self.height - 1) + 1):
            self._span(y, x0, x1, rgb)
        self.version += 1

    def fill_polygon(self, points, color=(255, 255, 255)):
        """Even-odd scanline fill sampling pixel centres; points are (x, y) pairs."""
        points = [(float(x), float(y)) for x, y in points]
        if len(points) < 3:
            return
        rgb = bytes(_rgb(color))
        edges = [(a, b) if a[1] < b[1] else (b, a)
                 for a, b in zip(points, points[1:] + points[:1]) if a[1] != b[1]]
        if not edges:
            return
        top = max(0, math.ceil(min(e[0][1] for e in edges) - 0.5))
        bottom = min(self.height - 1, math.ceil(max(e[1][1] for e in edges) - 0.5) - 1)
        for y in range(top, bottom + 1):
            yc = y + 0.5
            xs = sorted(ax + (yc - ay) * (bx - ax) / (by - ay)
                        for (ax, ay), (bx, by) in edges if ay <= yc < by)
            for i in range(0, len(xs) - 1, 2):
                self._span(y, math.ceil(xs[i] - 0.5), math.ceil(xs[i+1] - 0.5) - 1, rgb)
        self.version += 1

    def fill_triangle(self, x0, y0, x1, y1, x2, y2, color=(255, 255, 255)):
        self.fill_polygon(((x0, y0), (x1, y1), (x2, y2)), color)

    def fill_circle(self, cx, cy, radius, color=(255, 255, 255)):
        """Fill the pixels whose centres lie within radius of (cx, cy)."""
        cx, cy, radius = float(cx), float(cy), abs(float(radius))
        rgb = bytes(_rgb(color))
        for y in range(max(0, math.ceil(cy - radius - 0.5)),
                       min(self.height - 1, math.floor(cy + radius - 0.5)) + 1):
            half = radius * radius - (y + 0.5 - cy) ** 2
            if half >= 0:
                half = math.sqrt(half)
                self._span(y, math.ceil(cx - half - 0.5), math.floor(cx + half - 0.5), rgb)
        self.version += 1

    def circle(self, cx, cy, radius, color=(255, 255, 255)):
        """Outline: the edge pixels of fill_circle's disc, row by row."""
        cx, cy, radius = float(cx), float(cy), abs(float(radius))
        rgb = bytes(_rgb(color))
        def half(y):
            h = radius * radius - (y + 0.5 - cy) ** 2
            return math.sqrt(h) if h >= 0 else None
        top, bottom = math.ceil(cy - radius - 0.5), math.floor(cy + radius - 0.5)
        for y in range(top, bottom + 1):
            h = half(y)
            if h is None:
                continue
            left, right = math.ceil(cx - h - 0.5), math.floor(cx + h - 0.5)
            # Join to the wider neighbouring row so steep parts have no gaps.
            inner = min((n for n in (half(y - 1), half(y + 1)) if n is not None), default=0.0)
            inner_left = max(left, math.ceil(cx - inner - 0.5) - 1)
            inner_right = min(right, math.floor(cx + inner - 0.5) + 1)
            if y in (top, bottom) or inner_left >= inner_right:
                self._span(y, left, right, rgb)
            else:
                self._span(y, left, inner_left, rgb)
                self._span(y, inner_right, right, rgb)
        self.version += 1

    def refresh(self):
        """Hand the current picture to the window (BBC *REFRESH)."""
        self._frame = bytes(self.pixels)
        self._frame_version += 1

    def set_auto_refresh(self, on):
        self.auto_refresh = bool(on)
        if not self.auto_refresh and self._frame is None:
            self.refresh()

    @property
    def origin(self):
        return self._origin

    def set_origin(self, x, y):
        self._origin = (int(x), int(y))

    def virtual_pixel(self, x, y, color=(255, 255, 255)):
        self.pixel(*virtual_to_pixel(x, y, self.mode, self._origin), color)

    def virtual_to_pixel(self, x, y):
        return virtual_to_pixel(x, y, self.mode, self._origin)

    def virtual_to_pixel_centre(self, x, y):
        """BBC virtual point as unrounded framebuffer coordinates, for fills."""
        mode, (ox, oy) = self.mode, self._origin
        return ((x + ox) * mode.width / mode.virtual_width,
                mode.height - (y + oy) * mode.height / mode.virtual_height)

    def virtual_line(self, x0, y0, x1, y1, color=(255, 255, 255)):
        p0 = virtual_to_pixel(x0, y0, self.mode, self._origin)
        p1 = virtual_to_pixel(x1, y1, self.mode, self._origin)
        self.line(*p0, *p1, color)

    def open(self, window_width=None, window_height=None, title='Lispy graphics'):
        """Open pygame SDL window; call present() periodically from owning thread."""
        global _active
        size = (self.width * 2 if window_width is None else int(window_width),
                self.height * 2 if window_height is None else int(window_height))
        if min(size) <= 0:
            raise ValueError('window dimensions must be positive')
        try:
            import pygame
        except ImportError as error:
            raise RuntimeError('Graphics windows need pygame-ce: python -m pip install pygame-ce') from error
        active = _active
        if active is not None and active is not self:
            active.close()
        self._pygame = pygame
        pygame.display.init()
        self._size = size
        self._screen = pygame.display.set_mode(self._size)
        self._closed = False
        self._shown = None
        pygame.display.set_caption(title)
        _active = self
        self.present()
        return self

    def present(self):
        if self._screen is None:
            if self._closed:
                return []
            raise RuntimeError('call open() before present()')
        pygame = self._pygame
        events = list(pygame.event.get())
        if any(event.type == pygame.QUIT or
               (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)
               for event in events):
            self.close()
            return events
        if any(event.type in (pygame.VIDEOEXPOSE, getattr(pygame, 'WINDOWEXPOSED', -1))
               for event in events):
            self._shown = None               # uncovered window: draw it again
        if self.auto_refresh:
            shown, data = ('auto', self.version), None
        else:
            shown, data = ('frame', self._frame_version), self._frame
        if shown != self._shown:
            self._shown = shown
            if data is None:
                data = bytes(self.pixels)
            # RGB byte buffer has x-major scanlines; pygame copies it into a Surface.
            surface = pygame.image.frombuffer(data, (self.width, self.height), 'RGB')
            if self._size != (self.width, self.height):
                surface = pygame.transform.scale(surface, self._size)
            self._screen.blit(surface, (0, 0))
            pygame.display.flip()
        return events

    def close(self):
        global _active
        if _active is self:
            _active = None
        if self._pygame is not None:
            self._pygame.display.quit()
        self._pygame = self._screen = None
        self._size = None
        self._closed = True
