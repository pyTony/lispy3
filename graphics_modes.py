"""BBC virtual graphics coordinates and physical framebuffer/window mapping."""
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class GraphicsMode:
    number: int
    width: int
    height: int
    colours: int
    palette: tuple[tuple[int, int, int], ...]
    virtual_width: int = 1280
    virtual_height: int = 1024

    def __post_init__(self):
        if min(self.width, self.height, self.virtual_width, self.virtual_height) <= 0:
            raise ValueError('dimensions must be positive')
        if self.colours < 1 or len(self.palette) < self.colours:
            raise ValueError('palette must contain at least colours entries')

BBC_PALETTE = ((0, 0, 0), (255, 0, 0), (0, 255, 0), (255, 255, 0),
               (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255))
MODE_0 = GraphicsMode(0, 640, 256, 2, (BBC_PALETTE[0], BBC_PALETTE[7]))
MODE_1 = GraphicsMode(1, 320, 256, 4, (BBC_PALETTE[0], BBC_PALETTE[1], BBC_PALETTE[3], BBC_PALETTE[7]))
MODE_2 = GraphicsMode(2, 160, 256, 16, BBC_PALETTE * 2)
MODES = {m.number: m for m in (MODE_0, MODE_1, MODE_2)}


def virtual_to_pixel(x: int, y: int, mode: GraphicsMode, origin=(0, 0)) -> Tuple[int, int]:
    """BBC bottom-left virtual -> top-left framebuffer, including ORIGIN offset.

    Return unclipped indices; caller decides whether to clip. Uses floor division,
    including for negative coordinates.
    """
    return ((int(x) + origin[0]) * mode.width // mode.virtual_width,
            mode.height - 1 - ((int(y) + origin[1]) * mode.height // mode.virtual_height))


@dataclass(frozen=True)
class WindowTransform:
    mode: GraphicsMode
    window_width: int
    window_height: int

    def __post_init__(self):
        if self.window_width <= 0 or self.window_height <= 0:
            raise ValueError('window dimensions must be positive')

    def framebuffer_to_window(self, x: int, y: int) -> Tuple[int, int]:
        return (x * self.window_width // self.mode.width,
                y * self.window_height // self.mode.height)
