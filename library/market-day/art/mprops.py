"""Market Day props: hand-typed slot maps and small iso solids (fountain, flower cart, cafe
parasols and tables, leaf-glyph trees on black, lamp posts, the kite, the bread bicycle, crates)."""
import sys, math, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[3] / 'tools'))
import numpy as np
import artlib, canvas, veg
from iso import hash2
import mkit

def fountain(s, cx, cy):
    """a round stone basin (unit slices), water on top, a column with a jet and a 1 px crest."""
    r = 5
    for yy in range(-r, r):
        half = int(math.sqrt(max(0, r * r - (yy + 0.5) ** 2)) + 0.5)
        if half > 0:
            def top(u, v, t, face_step=3, W=None, H=None, yy=yy, half=half):
                edge = u < 0.9 or u > W - 0.9 or abs(yy + 0.5) > r - 1.4
                if edge:
                    return 'stone3'
                return 'water2' if hash2(int(u * 2), yy, 5) < 0.12 else 'water'
            s.box(cx - half, cy + yy, 0, 2 * half, 1, 4, 'stone', top=top, left='stone2', right='stone1')
    s.box(cx - 0.75, cy - 0.75, 4, 1.5, 1.5, 7, 'stone', top='stone3', left='stone2', right='stone1')
    s.box(cx - 1.25, cy - 1.25, 11, 2.5, 2.5, 1, 'stone', top='water', left='stone2', right='stone1')
    jet = mkit.grid_from("""
.a.
.w.
wsw
.w.
""", {'a': 'water2', 'w': 'water', 's': 'water2'})
    s.sprite(jet, cx, cy, 12, upright=True)

def crate(s, x, y, goods, seed=0, z=0):
    def top(u, v, t, face_step=3, W=None, H=None):
        if u < 0.25 or v < 0.25:
            return 'brown1'
        return goods[int(hash2(int(u * 2), int(v * 2), seed) * len(goods))]
    s.box(x, y, z, 2, 2, 2, 'brown', top=top, left='brown2', right='brown1')

FLOWER_CART = """
..fyf.mf.yf..
.fmfyfmfyfmf.
cccccccccccc.
cnnnnnnnnnnc.
cnnnnnnnnnnc.
.cccccccccc..
..kwk...kwk..
...k.....k...
"""

def flower_cart():
    return mkit.grid_from(FLOWER_CART, {'f': 'flower2', 'y': 'bread2', 'm': 'leaf2', 'c': 'brown1', 'n': 'brown2',
                                         'k': 'ol', 'w': 'g4'})

PARASOL = """
....ccccc....
..ccccccccc..
cccccccccccccc
.dddddddddddd.
.......p......
.......p......
.......p......
.......p......
.......p......
"""

def parasol(paint='plaster'):
    return mkit.grid_from(PARASOL, {'c': '%s3' % paint, 'd': '%s1' % paint, 'p': 'g1'})

CAFE_TABLE = """
aaaa
.pp.
.pp.
"""

def cafe_table():
    return mkit.grid_from(CAFE_TABLE, {'a': 'plaster3', 'p': 'g1'})

LAMP = """
.l.
lll
.p.
.p.
.p.
.p.
.p.
.p.
.p.
.p.
ppp
"""

def lamp():
    return mkit.grid_from(LAMP, {'l': 'g3', 'p': 'g1'})

KITE = """
...y...
..yyb..
.yyybb.
yyyybbb
.kkkkk.
.bbbyy.
..bbyy.
...by..
....k..
"""

def kite():
    return mkit.grid_from(KITE, {'y': 'bread2', 'b': 'fish2', 'k': 'g1'})

BIKE = """
.........yyyy..
........yyyyyy.
.hhh....ccccc..
hhsss....k.....
hssss...k......
.sss...k.......
ttttt.k........
tttttk.........
stttts.........
.ppppp.........
..pp.pp........
.kkk.kkk..kkk..
k...k...kk...k.
k..kk...k.k..k.
k...k...kk...k.
.kkk.....kkk...
"""

def bike(seed=3):
    k = {'y': 'bread1', 'c': 'brown1', 'h': 'hb', 's': 'skinB', 't': 'leaf2', 'p': 'slate2', 'k': 'ol'}
    return mkit.grid_from(BIKE, k)

def tree(seed=0, w=24, h=18):
    """a leaf-glyph canopy on black (veg.leaf_glyphs) over a short trunk, as a sprite."""
    c = canvas.Canvas(w, h + 6)
    yy, xx = np.mgrid[0:h + 6, 0:w]
    m = np.zeros((h + 6, w), bool)
    lobes = [(w * 0.5, h * 0.55, w * 0.42, h * 0.45), (w * 0.3, h * 0.45, w * 0.26, h * 0.32),
             (w * 0.68, h * 0.4, w * 0.25, h * 0.3), (w * 0.52, h * 0.25, w * 0.22, h * 0.24)]
    for (ax, ay, rx, ry) in lobes:
        rx *= 0.85 + 0.3 * hash2(int(ax), seed, 1); ry *= 0.85 + 0.3 * hash2(int(ay), seed, 2)
        m |= ((xx - ax) / rx) ** 2 + ((yy - ay) / ry) ** 2 <= 1.0
    veg.leaf_glyphs(c, m, 'leaf', gap='ol', fill=0.5, fringe=2, seed=seed)
    g = artlib.Grid(w, h + 6)
    for y in range(h + 6):
        for x in range(w):
            v = c.g[y, x]
            g.a[y][x] = v
    tx = w // 2
    for y in range(h - 2, h + 5):
        g.a[y][tx - 1] = 'ol'; g.a[y][tx] = 'brown1'; g.a[y][tx + 1] = 'ol'
    g.a[h + 5][tx] = 'ol'
    return mkit.add_outline(g)

LAUNDRY = """
k.................k
.kppk..wwk..sskk..
..kpk..wk...ssk...
...k...k.....k....
"""

POT = """
rmr
mrm
.n.
"""

def pot():
    return mkit.grid_from(POT, {'r': 'rose2', 'm': 'leaf1', 'n': 'brown1'})
