"""Greyscale block-in at native size: one flat grey per plane, the hero's light the brightest.
Prints each plane's share so the brief's Planes line is measured, not guessed."""
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[3] / 'tools'))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from PIL import Image
import palette as P
import geo as G

OUT = str(pathlib.Path(__file__).resolve().parents[1] / 'out') + '/'
BANDS = {'dark': 0.24, 'mid': 0.38, 'light': 0.52, 'brightest': 0.88}
PLANE_BAND = {'near walls': 'dark', 'foreground banks': 'dark', 'upper sky and storm': 'mid',
              'low sky glow': 'light', 'mesa': 'mid', 'rock step': 'mid', 'left fall': 'mid',
              'right fall': 'light', 'pool and river': 'mid', 'bridge': 'dark', 'forge frame and landing': 'mid',
              'forge light': 'brightest'}


def grey(L):
    return np.array(Image.new('RGB', (1, 1), P.from_lch(L, 0, 0)).getpixel((0, 0)))


def planes():
    lab = np.full((G.H, G.W), 'low sky glow', object)
    lab[:46] = 'upper sky and storm'
    lab[G.poly(G.MESA) | G.poly(G.BUTTE)] = 'mesa'
    lab[G.step_mask()] = 'rock step'
    lab[G.fall_mask(G.RIGHT_FALL)] = 'right fall'
    lab[G.YY >= G.WALL_FOOT] = 'foreground banks'
    lab[G.poly(G.POOL) | G.poly(G.RIVER)] = 'pool and river'
    lab[G.left_wall() | G.right_wall()] = 'near walls'
    lab[G.fall_mask(G.LEFT_FALL) | G.fall_mask(G.LEFT_FALL2)] = 'left fall'
    x0, y0, x1, y1 = G.FRAME
    lab[y0:y1, x0:x1] = 'forge frame and landing'
    x0, y0, x1, y1 = G.LANDING
    lab[y0:y1, x0:x1] = 'forge frame and landing'
    for x in range(G.BRIDGE_L[0], G.BRIDGE_R[0] + 1):
        y = int(round(G.deck_y(x)))
        lab[y - 1:y + 2, x] = 'bridge'
    x0, y0, x1, y1 = G.DOOR
    lab[y0:y1, x0:x1] = 'forge light'
    lab[G.poly([(219, 106), (238, 106), (246, 111), (206, 111)])] = 'forge light'   # spill on the landing
    x0, y0, x1, y1 = G.LANTERN
    lab[y0:y1, x0:x1] = 'forge light'
    return lab


def build():
    lab = planes()
    img = np.zeros((G.H, G.W, 3), np.uint8)
    for name, band in PLANE_BAND.items():
        img[lab == name] = grey(BANDS[band])
    return img, lab


if __name__ == '__main__':
    img, lab = build()
    Image.fromarray(img).save(OUT + 'blockin-a.png')
    Image.fromarray(img).resize((G.W * 3, G.H * 3), Image.NEAREST).save(OUT + 'blockin-a-x3.png')
    parts = ['%s %d%% (%s)' % (n, round(100 * (lab == n).mean()), b) for n, b in PLANE_BAND.items()
             if round(100 * (lab == n).mean()) >= 1]
    print('- Planes: ' + ', '.join(parts))
