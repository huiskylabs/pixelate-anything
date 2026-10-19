"""Greyscale block-in of image A at native 480x270: one flat grey per value band, built from the
same camera and plan as the art (geom.py). Run: python3 art/blockin.py out/blockin-a.png"""
import sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, str(HERE))
from canvas import Canvas
import geom as G

GREY = {'darkest': '#151515', 'dark': '#3c3c3c', 'mid': '#707070', 'brightest': '#e8e8e8'}


def blockin():
    c = Canvas(G.W, G.H, 'dark')
    # road and pavements (mid) below the far walls
    c.rect(0, int(G.FARWALL_ROW), G.W, G.H, 'mid')
    # far building and sky are 'dark' already; left corner block face (dark)
    c.rect(int(G.X_LC0_S), 0, int(G.X_LC1_S), int(G.LC_BASE), 'dark')
    # left receding wall down to its base line (dark)
    c.poly([(G.X_LC1_S, 0), (G.X_OPEN0, 0), (G.X_OPEN0, G.FAR_ROW), (G.X_LC1_S, G.LC_BASE)], 'dark')
    # right receding wall, hero side and the glass sliver (dark)
    c.poly([(G.X_OPEN1, 0), (G.W, 0), (G.W, G.HERO_BASE + 7), (G.X_HERO_R, G.HERO_BASE),
            (G.X_HERO_C, G.HERO_BASE), (G.X_HERO_SIDE0, G.row(G.Z_HERO_BACK)), (G.X_OPEN1, G.FAR_ROW)], 'dark')
    # the hero shopfront: its lit ground floor (brightest)
    x0, y0, x1, y1 = G.HERO_BOX
    c.rect(x0, y0, x1 + 1, y1 + 1, 'brightest')
    # the near hoarding (darkest)
    c.poly([(0, 70), (56, 76), (56, G.H), (0, G.H)], 'darkest')
    return c


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else str(HERE.parent / 'out' / 'blockin-a.png')
    c = blockin()
    img = c.image(GREY)
    img.save(out)
    g = c.g
    tot = g.size
    for k in GREY:
        print(k, round(100 * (g == k).sum() / tot, 1), '%')
