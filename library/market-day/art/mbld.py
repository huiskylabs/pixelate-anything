"""Market Day buildings and props: the signature forms as seeded functions.

  roof_fill / end_fill   tile courses (dashed, offset row by row, patched tiles), black eave line
  dormers()              stacked dormer rows on a steep slope, 3 shapes, shrinking toward the ridge
  facade()               half-timbered or plaster fronts, storeys, window rhythm, shop ground floor
  house()                a whole house from a town.row() spec
  hall()                 the long arcaded block, its huge hipped roof, 3 dormer rows, the steps
  stall()                counter, produce, striped awning by type (fruit, flowers, fish, bread)
"""
import sys, math, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[3] / 'tools'))
import numpy as np
from iso import hash2
import mkit
from mkit import plane, roof_x, roof_y

# ---------------------------------------------------------------- roofs
def roof_fill(mat, step, z0, seed, eave=True, period=3):
    """a tile slope: courses every `period` px of height as dashed darker lines offset row by row,
    a few patched (lighter) tiles, a black eave line on the lowest row."""
    base, dark, lite = '%s%d' % (mat, step), 'tilek', '%s%d' % (mat, min(4, step + 1))
    ph = int(hash2(seed, 1, 9) * period)
    def f(X, Y, Z):
        dz = Z - z0
        if eave and dz < 0.8:
            return 'ol'
        row = int((dz + ph) // period)
        along = X + Y                              # runs along the course on either slope
        if (dz + ph) % period < 1.0:
            # a dashed course line: gaps every 5-9 units, offset per row
            L = 6 + int(hash2(row, seed, 3) * 6)
            if (along + row * 3.7) % L > 1.2:
                return dark
        c = int(along // 1.5)
        if hash2(c, row, seed) < 0.035 and (dz + ph) % period > 1.5:
            return lite
        return base
    return f

def gable_fill(wall, step, X0, Z0, w_half, hr, axis, mid, seed, timber=False):
    """a gable triangle in the wall's paint with a black verge along both rakes; half-timbered
    gables get a king post and a collar beam."""
    base = '%s%d' % (wall, step)
    def f(X, Y, Z):
        a = Y if axis == 'y' else X                # position across the gable
        dz = Z - Z0
        top = hr * (1 - abs(a - mid) / w_half)
        if dz > top - 1.0:
            return 'ol'
        if timber:
            if abs(a - mid) < 0.3:
                return 'timber'
            if abs(dz - hr * 0.45) < 0.5:
                return 'timber'
            if abs(dz - hr * 0.45) < 3.5 and 0.8 < abs(a - mid) < 1.6 and dz < hr * 0.45:
                return 'glass'
        elif abs(a - mid) < 0.6 and hr * 0.35 < dz < hr * 0.35 + 3:
            return 'glass'
        return base
    return f

# ---------------------------------------------------------------- dormers
# Dormers are hand-drawn upright icons (at 4-7 px a sheared 3D box turns to mush): a light frame,
# a dark window and a pointed cap; 'tri' is the small triangular eyebrow vent of the photo.
DORMER_ART = {
    'gable': """
..c..
.ccc.
cgggc
cgggc
""",
    'small': """
.c.
ccc
cgc
cgc
""",
    'tri': """
.r.
rgr
""",
    'box': """
ccccc
cgcgc
""",
    'tall': """
.c.
ccc
cgc
cgc
cgc
""",
    'wide': """
...c...
..ccc..
.ccccc.
ccgcgcc
cggcggc
""",
}
_DCACHE = {}

def dormer_sprite(kind, frame='plaster3', roof='tile3'):
    key = (kind, frame, roof)
    if key not in _DCACHE:
        _DCACHE[key] = mkit.grid_from(DORMER_ART[kind], {'c': frame, 'g': 'glass', 'r': roof})
    return _DCACHE[key]

def dormer_rows(s, axis, a0, a1, b_eave, b_ridge, z_eave, z_ridge, mat, wall, seed, rows=3, kinds=('gable',), frame=None, hip=0.0):
    """stacked dormer rows on one slope. axis 'y': a +y slope (ridge along x), a runs along x, b is
    y (eave at b_eave > b_ridge). axis 'x': a +x slope (ridge along y), a runs along y, b is x.
    Rows shrink toward the ridge, spacing is uneven, a dormer goes missing now and then."""
    L = a1 - a0
    placed = []
    frame = frame or ('%s3' % wall)
    for r in range(rows):
        f = 0.14 + r * (0.66 / max(1, rows)) + (0.05 if rows == 1 else 0)
        if f > 0.82:
            break
        b = b_eave + (b_ridge - b_eave) * f
        z = z_eave + (z_ridge - z_eave) * f
        if r == 0:
            kind_pool = [k for k in kinds if k != 'tri'] or ['gable']
        elif r == rows - 1 and rows >= 3:
            kind_pool = ['tri', 'small']
        else:
            kind_pool = ['small', 'gable'] if L > 16 else ['small']
            if 'box' in kinds or 'tall' in kinds:
                kind_pool = [k for k in kinds if k in ('box', 'tall', 'small', 'tri')] or kind_pool
        step = 3.6 + 1.6 * r + hash2(seed, r, 6) * 1.5           # units between dormer centres
        margin = 1.6 + r * 1.0 + hash2(seed, r, 7) * 1.2
        ra0, ra1 = a0 + hip * f, a1 - hip * f
        a = ra0 + margin + (hash2(seed, r, 8) * step * 0.5)
        k = 0
        while a <= ra1 - margin:
            kind = kind_pool[int(hash2(seed, r * 31 + k, 9) * len(kind_pool))]
            if L > 30 and r == 0 and hash2(seed, k, 12) < 0.18:
                kind = 'wide'
            if hash2(seed, r * 17 + k, 10) < 0.10:
                a += step * 0.7
                k += 1
                continue
            g = dormer_sprite(kind, frame, '%s3' % mat)
            if axis == 'y':
                s.sprite(g, a, b, z, upright=True)
            else:
                s.sprite(g, b, a, z, upright=True)
            placed.append((r, a))
            a += step + hash2(seed, r * 13 + k, 11) * 2.0 + (1.5 if kind == 'wide' else 0)
            k += 1
    return placed

# ---------------------------------------------------------------- facades
def facade(b, step):
    """a +y (step 2) or +x (step 1) wall face for house spec b: storeys of 9 px over a 10 px
    ground floor; half-timbered (dark timber grid, braces) or plaster with windows; the far-side
    street fronts get shop windows and a door."""
    wall = b['wall']; seed = b['seed']; timber = b['timber']
    base = '%s%d' % (wall, step)
    every = 2.5 + (hash2(seed, 3, 1) * 1.6)            # window rhythm (units)
    wwin = 1.0 if hash2(seed, 4, 1) < 0.6 else 1.5
    g0 = 10
    storey = 9
    shop = b['side'] == 'far' and step == 2
    shutter = (not timber) and hash2(seed, 5, 1) < 0.4
    sh_col = ['leaf1', 'terra1', 'sky1', 'slate1'][int(hash2(seed, 6, 1) * 4)]
    def f(u, v, t, face_step=2, W=None, H=None):
        W = W or 10; H = H or 30
        if v < g0:                                     # ground floor
            if shop:
                if v < 1:
                    return 'g3'
                door = (W * 0.62 + hash2(seed, 7, 1) * W * 0.2)
                if abs(u - door) < 0.8 and v < 8:
                    return 'timber' if v >= 7 else 'glass'
                if 1 <= v < 7.5 and 0.8 < u < W - 0.8 and abs(u - door) > 1.6 and int(u / 3.2) % 3 != 2:
                    return 'glass2' if v >= 6 else 'glass'
                if v >= 9:
                    return 'timber' if timber else '%s%d' % (wall, max(0, step - 1))
                return base
            if 1 <= v < 6.5 and int((u + seed % 3) / every) % 2 == 1 and (u + seed % 3) % every < wwin + 0.5:
                return 'glass'
            return base
        k = int((v - g0) // storey)
        vv = (v - g0) % storey
        if H - v < 1.0:
            return '%s%d' % (wall, max(0, step - 1))
        if timber:
            if vv < 1:
                return 'timber'                        # the beam at each floor
            if u < 0.5 or u > W - 0.5:
                return 'timber'                        # corner posts
            cu = (u - 0.75) % every
            if cu < 0.5:
                return 'timber'                        # posts between windows
            if 2.5 <= vv < 7 and 0.9 < cu < 0.9 + wwin:
                return 'glass'
            # braces: a diagonal in every other panel below the window
            if 1 <= vv < 2.5 and int((u - 0.75) / every) % 2 == (k % 2) and abs(cu - 0.5 - (vv - 1) * 0.6) < 0.35:
                return 'timber'
            return base
        cu = (u - 1.0) % every
        if 2 <= vv < 7 and 0 <= cu < wwin and 0.6 < u < W - 0.6:
            return 'glass'
        if shutter and 2 <= vv < 7 and (wwin <= cu < wwin + 0.5 or every - 0.5 <= cu) and 0.6 < u < W - 0.6:
            return sh_col
        return base
    return f

def house(s, b, z0=0):
    X, Y, w, d, h = b['X'], b['Y'], b['w'], b['d'], b['h']
    wall, roof, seed = b['wall'], b['roof'], b['seed']
    s.box(X, Y, z0, w, d, h, wall, left=facade(b, 2), right=facade(b, 1), top='%s3' % roof)
    if b['gable']:
        hr = 1.5 * w
        roof_y(s, X - 0.3, Y, z0 + h, w + 0.6, d + 0.4, hr, roof_fill(roof, 1, z0 + h, seed),
               gable_fill(wall, 2, X, z0 + h, (w + 0.6) / 2.0, hr, 'x', X + w / 2.0, seed, b['timber']))
        dormer_rows(s, 'x', Y + 2, Y + d - 2, X + w + 0.3, X + w / 2.0, z0 + h, z0 + h + hr, roof, 'plaster', seed,
                    rows=1 if w < 12 else 2, kinds=('gable', 'tri'))
    else:
        hr = 1.5 * d
        hip = b['hip']
        end = roof_fill(roof, 1, z0 + h, seed + 1) if hip else \
            gable_fill(wall, 1, X, z0 + h, (d + 0.6) / 2.0, hr, 'y', Y + d / 2.0, seed, b['timber'])
        roof_x(s, X, Y - 0.3, z0 + h, w, d + 0.6, hr, roof_fill(roof, 2, z0 + h, seed), end, hip=hip)
        rows = 1 if d < 14 else (2 if w < 11 else 3)
        hv = hash2(seed, 21, 1)
        kinds = ('gable', 'gable', 'tri') if hv < 0.45 else (('tri',) if hv < 0.62 else ('gable',))
        if b['side'] == 'near' and b['Y'] >= 70:
            kinds = [('box', 'gable'), ('tall', 'tri'), ('gable', 'box', 'tri'), ('tall',), ('gable', 'tri')][int(hash2(seed, 26, 1) * 5)]
        if hv > 0.9:
            rows = 0                                   # an old roof with no dormers at all
        elif hv > 0.78:
            rows = min(rows, 1)
        dmat = 'plaster' if hash2(seed, 22, 1) < 0.6 else wall
        if rows:
            dormer_rows(s, 'y', X, X + w, Y + d + 0.3, Y + d / 2.0, z0 + h, z0 + h + hr, roof, dmat, seed, rows=rows, kinds=kinds, hip=hip)
        # chimneys: one or two, never centred
        if hash2(seed, 23, 1) < 0.6:
            cx = X + 1.5 + hash2(seed, 24, 1) * (w - 4)
            cy = Y + d / 2.0 - 1
            s.box(cx, cy, z0 + h + hr - 6, 1.5, 1.5, 9, 'red' if hash2(seed, 25, 1) < 0.5 else 'plaster', top='g1')

# ---------------------------------------------------------------- the hall
def hall(s, A, steps):
    X, Y, w, d, h, hr, hip = A['X'], A['Y'], A['w'], A['d'], A['h'], A['roof'], A['hip']
    bays = 13
    bay = d / bays
    pl = A.get('plinth', 6)
    def front(u, v, t, face_step=1, W=None, H=None):
        # the +x face: a plinth, an arcade of round arches on piers (the portal in bay 7),
        # two storeys of tall windows between pilasters, a cornice
        i = int(u // bay); cu = u - i * bay
        if v < pl:
            return 'stone2' if v >= pl - 1 else 'stone1'
        if v < pl + 14:
            vv = v - pl
            c = bay / 2.0
            portal = i == 7
            rr = bay * (0.40 if portal else 0.34)
            spring = 7.5 if not portal else 8.5
            if abs(cu - c) < rr and (vv < spring or (vv - spring) ** 2 + ((cu - c) * 1.5) ** 2 < (rr * 1.5) ** 2):
                return 'glass'
            if 5 <= i <= 9 and 10.5 <= vv < 12.5 + (0.9 if abs(cu - bay / 2.0) < 1.6 else 0):
                return 'leaf1' if (vv < 11.2 or int(cu * 2) % 5 == 0) else 'rose2'
            if vv >= 12.5:
                return 'stone0'
            return 'stone2'
        vv = v - pl - 14
        if H - v < 1.5:
            return 'stone0'                            # cornice
        if abs(vv - 11) < 0.6:
            return 'stone1'                            # string course
        w0 = vv % 11
        c = bay / 2.0
        if 2 <= w0 < 8.5 and abs(cu - c) < 0.75:
            return 'glass'
        if 1 <= w0 < 2 and abs(cu - c) < 1.2:
            return 'stone2'                            # window heads
        if abs(cu) < 0.35 or abs(cu - bay) < 0.35:
            return 'stone2'                            # pilasters
        return 'stone1'
    def end(u, v, t, face_step=2, W=None, H=None):
        if v < 15:
            if v < 1:
                return 'stone0'
            c = (u % 8) - 4
            if abs(c) < 2.2 and (v < 9 or (v - 9) ** 2 + (c * 1.6) ** 2 < 12):
                return 'glass'
            return 'stone2'
        vv = v - 15
        if abs(vv - 10) < 0.6 or H - v < 1.5:
            return 'stone1'
        if 2 <= vv % 10 < 8 and (u % 6) < 1.5 and 1 < u < W - 1:
            return 'glass'
        return 'stone2'
    s.box(X, Y, 0, w, d, h, 'stone', right=front, left=end, top='slate3')
    side = roof_fill('slate', 1, h, 404, period=3)
    endf = roof_fill('slate', 2, h, 405, period=3)
    roof_y(s, X - 0.5, Y - 0.5, h, w + 1, d + 1, hr, side, endf, hip=hip)
    # three stacked dormer rows on the +x slope, shrinking toward the ridge
    dormer_rows(s, 'x', Y + 1, Y + d - 1, X + w + 0.5, X + w / 2.0, h, h + hr, 'slate', 'stone', 77, rows=3, hip=hip,
                kinds=('gable', 'gable', 'gable', 'tri'))
    # the steps: a white landing and treads, light-grey risers
    x0, y0, y1 = steps['x0'], steps['y0'], steps['y1']
    z = steps['n'] * steps['rise'] + steps['rise']
    ry0, ry1 = steps.get('runner', (-18.5, -13.5))
    def tread(u, v, t, face_step=3, W=None, H=None):
        y = y0 + v
        if ry0 <= y < ry1:
            return 'rose2' if (ry0 + 0.6 <= y < ry1 - 0.6) else 'rose1'
        return 'white'
    s.box(x0, y0, 0, steps['landing'], y1 - y0, z, 'stone', top=tread, left='g7', right='g7')
    oids = [s.nobj]
    x = x0 + steps['landing']
    for i in range(steps['n']):
        z -= steps['rise']
        oids.append(s.box(x, y0, 0, steps['tread'], y1 - y0, z, 'stone', top=tread, left='g7', right='g7'))
        x += steps['tread']
    return oids

# ---------------------------------------------------------------- market stalls
AWN = {'fruit': 'fruit', 'flower': 'flower', 'fish': 'fish', 'bread': 'bread'}
GOODS = {'fruit': ['fruit2', 'leaf2', 'bread2', 'fruit1'], 'flower': ['flower2', 'bread2', 'flower3', 'leaf1'],
         'fish': ['fishc', 'g6', 'fishc', 'fish3'], 'bread': ['bread1', 'ochre1', 'bread0', 'brown3']}

def stall(s, x, y, kind, w=9, d=5, seed=0):
    """a counter (x..x+w along the street, y..y+d) facing +y, produce on top in crates, a striped
    awning above the back half on two poles."""
    paint = AWN[kind]
    goods = GOODS[kind]
    def top(u, v, t, face_step=3, W=None, H=None):
        # crates in a row, each with its produce in 2-px clusters
        cu = int(u // 1.5)
        if (u % 1.5) < 0.25 or v < 0.3:
            return 'brown1'
        c = goods[int(hash2(cu, int(v * 2), seed) * len(goods))] if hash2(cu, seed, 3) < 0.8 else goods[0]
        return c
    def front(u, v, t, face_step=2, W=None, H=None):
        if v > H - 1:
            return 'brown1'
        return 'plaster1' if int(u * 2) % 5 else 'plaster0'
    s.box(x, y, 0, w, d, 5, 'plaster', top=top, left=front, right='plaster1')
    # poles at the front corners
    for px in (x + 0.1, x + w - 0.6):
        s.box(px, y + d - 0.4, 5, 0.5, 0.5, 11, 'g', top='g1', left='g1', right='g0', lines=False)
    # the awning: a sloped striped plane from the back (high) to the front edge, with a valance
    zb, zf = 19, 16
    def awn(X, Y, Z):
        k = int((X - x) // 1.0)
        return '%s2' % paint if k % 2 == 0 else 'g5'
    plane(s, [(x - 0.3, y - 0.5, zb), (x + w + 0.3, y - 0.5, zb), (x + w + 0.3, y + d + 0.3, zf), (x - 0.3, y + d + 0.3, zf)], awn, 1, True,
          out=(0, 0.2, 1))
    # valance: a front strip hanging 2 px
    def val(u, v, t, face_step=2, W=None, H=None):
        k = int(u // 1.0)
        if v < 1 and int(u * 2) % 2 == 0:
            return 'ol'
        return '%s1' % paint if k % 2 == 0 else 'g4'
    s.box(x - 0.3, y + d + 0.1, zf - 2, w + 0.6, 0.2, 2, paint, left=val, right='%s0' % paint, top='%s2' % paint)
