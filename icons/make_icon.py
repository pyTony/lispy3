"""Draw the starter Lispy Machine icon: a green lambda in yellow parentheses.

    python icons/make_icon.py

Writes lispy_machine.png (256x256) and lispy_machine.ico (16-256 px) next to
this script. Needs Pillow. To use a different picture instead (for example one
drawn by an image generator), just replace those two files; the editor only
looks for the file names.
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BG, EDGE = (30, 30, 30, 255), (0, 122, 204, 255)        # editor bg, status-bar blue
PAREN, LAMBDA = (255, 215, 0, 255), (106, 220, 120, 255)
SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw(px):
    """Draw at 8x and shrink, so edges stay smooth at every size."""
    s = px * 8
    u = s / 32                                             # one unit of a 32-grid
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    border = max(round(1.5 * u), 8)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=round(6 * u), fill=EDGE)
    d.rounded_rectangle([border, border, s - 1 - border, s - 1 - border],
                        radius=round(5 * u), fill=BG)
    # small sizes get fatter strokes so they survive the shrink
    w = round((3.4 if px <= 24 else 2.8) * u)
    # parentheses: arcs of a tall ellipse
    d.arc([5 * u, 6 * u, 15 * u, 26 * u], 120, 240, fill=PAREN, width=w)
    d.arc([17 * u, 6 * u, 27 * u, 26 * u], -60, 60, fill=PAREN, width=w)
    # lambda: long stroke from top-left to bottom-right, short leg to bottom-left
    d.line([(11.5 * u, 9 * u), (20.5 * u, 23 * u)], fill=LAMBDA, width=w)
    d.line([(16 * u, 16 * u), (11.5 * u, 23 * u)], fill=LAMBDA, width=w)
    return img.resize((px, px), Image.LANCZOS)


def main():
    images = [draw(px) for px in SIZES]
    images[-1].save(os.path.join(HERE, "lispy_machine.png"))
    images[-1].save(os.path.join(HERE, "lispy_machine.ico"),
                    sizes=[(px, px) for px in SIZES], append_images=images[:-1])


if __name__ == "__main__":
    main()
