"""Small independent graphics surface: headless RGB first, optional Pygame window.

No dependency on lispy3.py or mini_basic. Pygame is imported only when opening
an actual window. Coordinates accepted by pixel/line are framebuffer pixels;
virtual_pixel/virtual_line use BBC graphics units with bottom-left origin.
"""
from graphics_modes import GraphicsMode, MODE_1, WindowTransform, virtual_to_pixel


def _rgb(value):
    if len(value) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in value):
        raise ValueError('RGB must contain three integer channels in [0,255]')
    return tuple(value)


class Graphics:
    def __init__(self, mode: GraphicsMode = MODE_1, *, background=(0, 0, 0)):
        self.mode = mode
        self.background = _rgb(background)
        self.pixels = bytearray(bytes(self.background) * (mode.width * mode.height))
        self._pygame = None
        self._screen = None
        self._size = None
        self._origin = (0, 0)
        self._closed = False

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

    def pixel(self, x, y, color=(255, 255, 255)):
        x, y = int(x), int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset:offset+3] = bytes(_rgb(color))

    def get_pixel(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError('pixel is outside framebuffer')
        i = (y * self.width + x) * 3
        return tuple(self.pixels[i:i+3])

    def line(self, x0, y0, x1, y1, color=(255, 255, 255)):
        """Integer Bresenham line, with per-pixel clipping by pixel()."""
        x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
        rgb = _rgb(color)
        dx, dy = abs(x1-x0), -abs(y1-y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.pixel(x0, y0, rgb)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def set_origin(self, x, y):
        self._origin = (int(x), int(y))

    def virtual_pixel(self, x, y, color=(255, 255, 255)):
        self.pixel(*virtual_to_pixel(x, y, self.mode, self._origin), color)

    def virtual_line(self, x0, y0, x1, y1, color=(255, 255, 255)):
        p0 = virtual_to_pixel(x0, y0, self.mode, self._origin)
        p1 = virtual_to_pixel(x1, y1, self.mode, self._origin)
        self.line(*p0, *p1, color)

    def open(self, window_width=None, window_height=None, title='Lispy graphics'):
        """Open pygame SDL window; call present() periodically from owning thread."""
        import pygame
        self._pygame = pygame
        pygame.display.init()
        self._size = (window_width or self.width * 2, window_height or self.height * 2)
        if min(self._size) <= 0:
            raise ValueError('window dimensions must be positive')
        self._screen = pygame.display.set_mode(self._size)
        self._closed = False
        pygame.display.set_caption(title)
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
        # RGB byte buffer has x-major scanlines; pygame copies it into a Surface.
        surface = pygame.image.frombuffer(bytes(self.pixels), (self.width, self.height), 'RGB')
        if self._size != (self.width, self.height):
            surface = pygame.transform.scale(surface, self._size)
        self._screen.blit(surface, (0, 0))
        pygame.display.flip()
        return events

    def close(self):
        if self._pygame is not None:
            self._pygame.display.quit()
        self._pygame = self._screen = None
        self._size = None
        self._closed = True
