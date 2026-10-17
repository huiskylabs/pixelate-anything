"""Greyscale block-in of a moment: one flat grey per plane, at native 640x360.

    python3 art/blockin.py a     -> out/blockin-a.png
"""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/04-tide-procession/art')
import math
import pathlib
import numpy as np
from PIL import Image
import geom as G

OUT = pathlib.Path('/home/user/pixelate-anything/examples/moments/04-tide-procession/out')
GREY = {'darkest': 0.12, 'dark': 0.22, 'mid': 0.36, 'brightest': 0.86}


def grey(L):
    # OKLab L of a neutral grey -> sRGB 8-bit
    lin = L ** 3
    s = 1.055 * lin ** (1 / 2.4) - 0.055 if lin > 0.0031308 else 12.92 * lin
    return int(round(255 * s))


def shaft_mask(sh, extra=0):
    yy, xx = np.mgrid[0:G.H, 0:G.W] + 0.5
    a = math.radians(sh['angle'])
    dx, dy = math.cos(a), math.sin(a)
    along = (xx - sh['x']) * dx + (yy - sh['y']) * dy
    across = np.abs(-(xx - sh['x']) * dy + (yy - sh['y']) * dx)
    w0, w1 = sh['width']
    half = (w0 + (w1 - w0) * np.clip(along / sh['length'], 0, 1)) / 2 + extra
    return (along >= 0) & (along <= sh['length']) & (across <= half * 0.8)


def blockin(moment):
    L = np.full((G.H, G.W), GREY['dark'])
    yy, xx = np.mgrid[0:G.H, 0:G.W] + 0.5
    mx, my, mr = G.MOON
    # the moonlit sky: the moon's glow (the halo's size) and the bright band over the horizon
    import scene
    glow = ((xx - mx) ** 2 + (yy - my) ** 2 <= 36 ** 2)
    L[glow] = GREY['mid']
    edge = 176 + np.round(3 * np.sin(xx / 53.0) + 2 * np.sin(xx / 17.0)).astype(int)
    L[(yy >= edge) & (yy < G.HORIZON)] = GREY['mid']
    # the cloud bank with its break, a dark mass
    bank, wisps = scene.cloud_masks(moment)
    L[bank] = GREY['darkest']
    # far headland breaks the horizon on the left (hazed, dark band)
    head = G.mask_poly([(118, 207), (140, 201), (176, 198), (214, 196), (252, 199), (288, 203), (306, 207)])
    L[head] = GREY['dark']
    # the shaft in the sky
    L[shaft_mask(G.SHAFT[moment]) & (yy < G.HORIZON)] = GREY['mid']
    # the moon and its bright aura
    L[G.disc(mx, my, mr)] = GREY['brightest']
    # the shallows beside the causeway (mid); the channel behind them stays dark
    lag, deep = scene.water_masks(moment)
    sh0 = G.SHAFT[moment]
    a0 = math.radians(sh0['angle'])
    fx0, fy0 = sh0['x'] + math.cos(a0) * sh0['length'], sh0['y'] + math.sin(a0) * sh0['length']
    L[lag & ((((xx - fx0) / 74.0) ** 2 + ((yy - fy0 - 8) / 24.0) ** 2) <= 1)] = GREY['mid']
    # island and monastery
    L[G.island_mask()] = GREY['darkest']
    # the causeway: a dark road across the lit flats
    for x in range(G.CAUSEWAY[0][0], G.CAUSEWAY[-1][0] + 1):
        y = G.road_y(x)
        top, face = G.road_th(x)
        L[y:y + top + face, x] = GREY['darkest']
    # pilgrims
    for spec in G.PILGRIMS[moment]:
        fx, h = spec[0], spec[1]
        fy = G.feet_y(fx, moment)
        L[fy - h:fy, fx - 3:fx + 4] = GREY['darkest']
    # the shaft's footprint on the far sea round the leaders (the moon's one repeat): one light
    # mass at block-in stage; the two leaders are detail drawn over it later
    sh = G.SHAFT[moment]
    a = math.radians(sh['angle'])
    ex = sh['x'] + math.cos(a) * sh['length']
    foot = (((xx - ex) / 36.0) ** 2 + ((yy - 230) / 14.0) ** 2 <= 1) & (yy > G.HORIZON) & (yy < 246)
    L[foot] = GREY['brightest']
    # near plane: bank, pine, boat, posts
    bank = G.mask_poly(G.BANK + [(640, 360), (0, 360)])
    L[bank] = GREY['darkest']
    # the bent pine: a leaning trunk and flat swept pads (left side, framing the top-left)
    pine = G.mask_poly([(22, 304), (30, 262), (44, 218), (62, 176), (84, 138), (108, 104), (130, 78),
                        (150, 56), (156, 60), (138, 84), (116, 112), (94, 146), (74, 184), (58, 224),
                        (46, 264), (40, 304)])
    L[pine] = GREY['darkest']
    for cx, cy, rx, ry in ((132, 42, 70, 12), (88, 82, 56, 10), (112, 118, 30, 7), (26, 150, 26, 7)):
        L[((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1] = GREY['darkest']
    x0, y0, x1, y1 = G.BOAT
    L[G.mask_poly([(x0, y0 + 8), (x1, y0), (x1 - 6, y1), (x0 + 10, y1)])] = GREY['darkest']
    for px, top, w in G.POSTS:
        L[top:340, px:px + w] = GREY['darkest']
    img = np.array([[grey(v)] for v in L.ravel()], np.uint8).reshape(G.H, G.W)
    return Image.fromarray(img, 'L').convert('RGB')


if __name__ == '__main__':
    m = sys.argv[1] if len(sys.argv) > 1 else 'a'
    OUT.mkdir(parents=True, exist_ok=True)
    blockin(m).save(OUT / ('blockin-%s.png' % m))
    print('wrote', OUT / ('blockin-%s.png' % m))
