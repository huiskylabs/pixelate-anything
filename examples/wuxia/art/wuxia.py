"""Shared bits for the wuxia RPG scenes: palette building, a slot canvas, ordered dither, the
dialogue overlay of 90s Chinese RPGs (speaker name in jade, cream text with a dark outline straight
over the picture, a blinking triangle) and seamless drifting layers."""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
import colorlib as cl
import cjkfont
from iso import BAYER4

NAME_RGB, TEXT_RGB, EDGE_RGB, ARROW_RGB = (126, 230, 220), (246, 236, 208), (10, 8, 16), (240, 192, 72)

def palette(ramps, extra=None):
    """{'robe': ['#..', ...]} -> {'robe0': '#..', 'robe1': ...}"""
    pal = {}
    for name, hexes in ramps.items():
        for i, h in enumerate(hexes):
            pal['%s%d' % (name, i)] = h
    pal.update(extra or {})
    return pal

def th(x, y):
    """ordered-dither threshold in (0, 1) for pixel (x, y)"""
    return (BAYER4[int(y) & 3, int(x) & 3] + 0.5) / 16

class Canvas:
    def __init__(self, w, h, fill=None):
        self.W, self.H = w, h
        self.g = np.full((h, w), fill, object)
    def put(self, x, y, v):
        x, y = int(math.floor(x)), int(math.floor(y))
        if 0 <= x < self.W and 0 <= y < self.H:
            self.g[y, x] = v
    def get(self, x, y):
        x, y = int(x), int(y)
        return self.g[y, x] if (0 <= x < self.W and 0 <= y < self.H) else None
    def set(self, x, y, v):                     # so cjkfont and pixfont can draw into it
        self.put(x, y, v)
    def paste(self, other, mask=None):
        m = (other != None) if mask is None else mask
        self.g[m] = other[m]
    def ramp(self, x, y, base, v, lo=0, hi=6):
        """put base + a dithered step: v may be fractional"""
        n = int(math.floor(v + th(x, y)))
        self.put(x, y, '%s%d' % (base, max(lo, min(hi, n))))

def to_image(g, pal):
    keys = sorted(set(g.ravel()) - {None})
    idx = np.zeros(g.shape, np.int32)
    lut = {k: i + 1 for i, k in enumerate(keys)}
    for k, i in lut.items():
        idx[g == k] = i
    rgb = np.array([(0, 0, 0)] + [cl.hex_to_rgb(pal[k]) for k in keys], np.uint8)
    return Image.fromarray(rgb[idx], 'RGB')

def dialogue(img, name, lines, t, start, cps=0.6, x=12, y=8, indent=12, blink=8, end=None):
    """type a speech out from frame `start` at cps characters a frame; blink a triangle when done.
    Nothing before start or from `end` on (so a loop can start clean)."""
    if t < start or (end is not None and t >= end):
        return
    n = (t - start) * cps
    cjkfont.draw(img, name + '：', x, y, NAME_RGB, outline=EDGE_RGB)
    total = 0
    for i, line in enumerate(lines):
        k = max(0, min(len(line), int(n - total)))
        if k:
            cjkfont.draw(img, line, x + indent, y + 18 + i * cjkfont.LINE, TEXT_RGB, outline=EDGE_RGB, upto=k)
        total += len(line)
    if n >= total and ((t - start) // blink) % 2 == 0:
        last = lines[-1]
        ax = x + indent + cjkfont.width(last) + 4
        ay = y + 18 + (len(lines) - 1) * cjkfont.LINE + 3
        for j, w in enumerate((7, 5, 3, 1)):                     # a small down triangle with an edge
            for i in range(-1, w + 1):
                for d in (-1, 0, 1):
                    px, py = ax + (7 - w) // 2 + i, ay + j + d
                    if 0 <= px < img.width and 0 <= py < img.height and not (0 <= i < w and d == 0):
                        if img.getpixel((px, py)) != ARROW_RGB:
                            img.putpixel((px, py), EDGE_RGB)
            for i in range(w):
                img.putpixel((ax + (7 - w) // 2 + i, ay + j), ARROW_RGB)

def loop_dissolve(layer, t, T):
    """a layer that drifts (clouds, mist) made seamless: layer(t) and layer(t - T) cross-dissolve over
    the loop with an ordered dither, so frame T matches frame 0. layer(t) -> object grid (None = clear)."""
    a, b = layer(t), layer(t - T)
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    thr = (BAYER4[yy & 3, xx & 3] + 0.5) / 16
    return np.where(thr < t / T, b, a)
