"""Greyscale block-ins at native size: flat value masses, one grey per plane, no detail."""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/02-endless-ascent/art')
import numpy as np
from common import W, H, YY, XX, OUT, hsh, new_grid, save
import geometry as G

GREYS = {'g0': '#1b1b1b', 'g1': '#333333', 'g2': '#4d4d4d', 'g3': '#666666', 'g4': '#e4e4e4'}
GREYS_B = {'g0': '#141414', 'g1': '#202020', 'g2': '#3f3f3f', 'g3': '#5a5a5a', 'g4': '#e4e4e4'}


def blockin_a():
    g = new_grid('g1')                                  # trunk walls: dark
    xl, xr = G.cleft_edges()
    haze = (XX >= xl[:, None]) & (XX < xr[:, None])
    g[haze] = 'g3'                                      # far haze in the cleft: light
    for (x0, y0, x1, y1) in G.FRONTS_A:                 # carved fronts: mid
        g[y0:y1, x0:x1] = 'g2'
    cx, cy, r = G.CLOCK
    g[(XX - cx) ** 2 + (YY - cy) ** 2 <= r * r] = 'g2'
    g[:, G.CABLE_X:G.CABLE_X + 2] = 'g1'
    g[8:22, xl[15] - 6:xr[15] + 6] = 'g2'                # the carved bridge arch across the top of the cleft
    x0, y0, x1, y1 = G.GONDOLA_BLOCK
    g[y0:y1 + 1, x0:x1 - 6] = 'g1'                      # the gondola's dark wood
    g[214:258, 130:x1 + 1] = 'g4'                       # the passenger, the lantern and its pool: brightest
    return g


def blockin_b():
    """B as planned: night sky (darkest), the aurora ribbon (mid), the cloud sea (light), the gondola"""
    import math
    g = new_grid('g1')
    for x in range(6, 262):                             # the aurora: an S-curved ribbon, tall in three places
        u = (x - 6) / 252
        yh = int(round(78 + 26 * math.sin(math.pi * 1.6 * u + 0.3) + 10 * u))
        Lx = int(12 + 46 * math.exp(-((x - 54) / 26) ** 2) + 38 * math.exp(-((x - 150) / 20) ** 2) + 30 * math.exp(-((x - 226) / 22) ** 2))
        g[max(0, yh - Lx):yh + 1, x] = 'g2'
    for x in range(150, 266):
        u = (x - 150) / 112
        yh = int(round(176 - 14 * math.sin(math.pi * 1.3 * u)))
        g[yh - 14:yh + 1, x] = 'g2'
    g[(YY >= 340) & (XX < 164)] = 'g3'                  # near mass, mid mass, far mass, strata below
    g[(YY >= 322) & (XX >= 172) & (XX < 266)] = 'g3'
    g[(YY >= 304) & (XX >= 206) & (XX < 248)] = 'g3'
    g[YY >= 362] = 'g3'
    g[(YY >= 318) & (YY < 342) & ((XX - 132) ** 2 + ((YY - 326) * 1.3) ** 2 <= 22 * 22)] = 'g3'
    for top in (366, 388, 410, 434, 458):               # the receding ridges: a shadow hollow over each
        for x in range(W):
            yt = top - int(round(4 + 4 * math.sin(x / (17 + top % 7) + top)))
            g[yt - 2:yt, x] = 'g2'
    x0, y0, x1, y1 = G.GONDOLA_BLOCK
    g[y0:y1 + 1, x0:x1 - 6] = 'g2'
    g[214:258, 130:x1 + 1] = 'g4'
    return g


if __name__ == '__main__':
    for name, fn in (('blockin-a', blockin_a), ('blockin-b', blockin_b)):
        g = fn()
        save(g, GREYS if name.endswith('a') else GREYS_B, name, scale=1)
        (OUT / ('%s@1x.png' % name)).unlink()
        (OUT / ('%s-palette.json' % name)).unlink()
        tot = g.size
        print(name, {k: '%.1f%%' % (100 * (g == k).sum() / tot) for k in GREYS})
