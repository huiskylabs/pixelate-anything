"""Greyscale block-ins at native size: flat value masses, one grey per plane, no detail."""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/02-endless-ascent/art')
import numpy as np
from common import W, H, YY, XX, OUT, hsh, new_grid, save
import geometry as G

GREYS = {'g0': '#1b1b1b', 'g1': '#333333', 'g2': '#4d4d4d', 'g3': '#666666', 'g4': '#e4e4e4'}


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
    g = new_grid('g0')                                  # night sky: darkest
    for (y, x0, x1, th) in G.AURORA_BLOCK:
        g[y:y + th, x0:x1] = 'g2'                       # aurora: mid
    top = G.cloud_top_line()
    g[YY >= top[None, :].repeat(H, 0)] = 'g3'           # cloud sea: light
    g[:, G.CABLE_X:G.CABLE_X + 2] = np.where(YY[:, :2] < top[G.CABLE_X], 'g1', g[:, G.CABLE_X:G.CABLE_X + 2])
    x0, y0, x1, y1 = G.GONDOLA_BLOCK
    g[y0:y1 + 1, x0:x1 - 6] = 'g1'
    g[214:258, 130:x1 + 1] = 'g4'
    return g


if __name__ == '__main__':
    for name, fn in (('blockin-a', blockin_a), ('blockin-b', blockin_b)):
        g = fn()
        save(g, GREYS, name, scale=1)
        (OUT / ('%s@1x.png' % name)).unlink()
        (OUT / ('%s-palette.json' % name)).unlink()
        tot = g.size
        print(name, {k: '%.1f%%' % (100 * (g == k).sum() / tot) for k in GREYS})
