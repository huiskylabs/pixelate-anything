"""Market Day kit: palette, slot-map helpers, a planar face painter for steep roofs, and the
signature forms of Strasbourg's old town as seeded functions (steep tiled roofs with stacked
dormer rows, half-timbered fronts, the long arcaded hall with its huge hipped roof, market
stalls with striped awnings) drawn into an iso.Iso scene.

sticker-iso: flat paints at the gamut edge, full #000 silhouettes, no light, no shadow; faces
keep a fixed order (top step 3, left step 2, right step 1)."""
import sys, math
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
import artlib
import palette as P
from iso import Iso, hash2

# ---------------------------------------------------------------- palette
def _flat(base):
    return P.ramp(base, style='flat')          # 5 steps: L -.12 -.05 0 +.04 +.07

def build_palette():
    pal = {'ol': '#000000', 'white': '#ffffff'}
    ramps = {
        # roofs: two paints, a brown and two near-neutral tiles (rationed so the roofs read as
        # one warm field with a few loud ones)
        'terra': P.from_lch(0.60, 0.20, 46),
        'brown': '#9a5a32',
        'tile': P.from_lch(0.50, 0.035, 50),       # weathered grey-brown tile (the hall, old roofs)
        'slate': P.from_lch(0.33, 0.03, 50),       # dark old tile (the hall, a third of the roofs)
        # walls
        'cream': P.from_lch(0.80, 0.06, 88),
        'plaster': P.from_lch(0.78, 0.012, 90),    # off-white plaster (never #fff)
        'pink': P.from_lch(0.78, 0.085, 36),       # apricot (a pink would rival the rose)
        'ochre': '#f2b631',
        'mint': '#5fd3a6',
        'sky': '#4fa8f0',
        'stone': P.from_lch(0.80, 0.06, 80),       # the hall's sandstone
        'red': P.from_lch(0.50, 0.14, 42),         # chimney brick
        # awnings by stall type
        'fruit': P.from_lch(0.72, 0.19, 55),       # orange
        'flower': '#9a5cf0',                       # violet
        'fish': '#2f6fe8',                         # blue
        'bread': '#f5c02a',                        # yellow
        'leaf': '#3fb34a',
        'rose': P.from_lch(0.62, 0.255, 358),      # the wedding: petals, runner, bridesmaids
    }
    for k, base in ramps.items():
        for i, h in enumerate(_flat(base)):
            pal['%s%d' % (k, i)] = h
    # neutral ladder (paving, glass, timber darks)
    for i, L in enumerate((0.22, 0.30, 0.40, 0.52, 0.63, 0.74, 0.82, 0.90)):
        pal['g%d' % i] = P.from_lch(L, 0.008, 250)
    for i, L in enumerate((0.52, 0.60, 0.66)):
        pal['p%d' % i] = P.from_lch(L, 0.012, 80)  # paving: seams, stones, base
    pal['tilek'] = P.from_lch(0.24, 0.03, 45)    # the tile-course line shared by every roof
    pal['timber'] = P.from_lch(0.30, 0.045, 45)
    pal['timber2'] = P.from_lch(0.38, 0.05, 48)
    pal['glass'] = P.from_lch(0.26, 0.03, 250)
    pal['glass2'] = P.from_lch(0.42, 0.05, 240)
    # people
    for k, (L, C, h) in {'skinA': (0.80, 0.07, 55), 'skinB': (0.66, 0.09, 50), 'skinC': (0.48, 0.08, 45)}.items():
        pal[k] = P.from_lch(L, C, h)
        pal[k + 'd'] = P.from_lch(L - 0.08, C, h - 5)
    pal['hk'] = P.from_lch(0.25, 0.02, 40)        # black-brown hair
    pal['hb'] = P.from_lch(0.42, 0.08, 55)        # brown
    pal['hy'] = P.from_lch(0.84, 0.12, 90)        # blond
    pal['hr'] = P.from_lch(0.58, 0.15, 45)        # ginger
    pal['gold'] = P.from_lch(0.80, 0.15, 88)      # brass
    pal['gold2'] = P.from_lch(0.66, 0.13, 80)
    pal['water'] = P.from_lch(0.70, 0.12, 225)
    pal['water2'] = P.from_lch(0.80, 0.09, 215)
    pal['fishc'] = P.from_lch(0.76, 0.03, 230)    # silver fish
    return pal

PAL = build_palette()
SLOTS = list(PAL.keys())

# ---------------------------------------------------------------- slot-map sprites
def grid_from(art, key, outline=True):
    """ASCII art -> artlib.Grid (transparent '.'), with a 1 px #000 silhouette added around it."""
    rows = [r.strip() for r in art.strip('\n').splitlines() if r.strip()]
    w = max(len(r) for r in rows)
    pad = 1 if outline else 0
    g = artlib.Grid(w + 2 * pad, len(rows) + 2 * pad)
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c not in '. ':
                g.set(i + pad, j + pad, key[c])
    if outline:
        add_outline(g)
    return g

def add_outline(g, ol='ol'):
    a = g.a
    H, W = g.h, g.w
    filled = [[a[y][x] is not None for x in range(W)] for y in range(H)]
    for y in range(H):
        for x in range(W):
            if filled[y][x]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                X, Y = x + dx, y + dy
                if 0 <= X < W and 0 <= Y < H and filled[Y][X] and a[Y][X] != ol:
                    a[y][x] = ol
                    break
    return g

def flipx(g):
    h = artlib.Grid(g.w, g.h)
    h.a = [list(reversed(r)) for r in g.a]
    return h

def recolor(g, mapping):
    h = artlib.Grid(g.w, g.h)
    h.a = [[mapping.get(v, v) if v is not None else None for v in r] for r in g.a]
    return h

# ---------------------------------------------------------------- planar faces
_AINV = {}

def plane(s, pts, fill, role=2, lines=True, oid=None, out=None):
    """paint a planar convex polygon (world points, in order around it) into the Iso scene with
    the depth buffer: steep roof slopes, hips and gable ends as true planes (the kit's gable() is
    1-unit steps). out: a rough outward direction; a face turned away from the viewer is skipped.
    fill: a slot or f(X, Y, Z) -> slot on world coordinates. Returns the oid."""
    pts = np.asarray(pts, float)
    N = np.cross(pts[1] - pts[0], pts[2] - pts[0])
    n = np.linalg.norm(N)
    if n < 1e-9:
        return oid
    N = N / n
    v = s.view
    if out is not None:
        if N @ np.asarray(out, float) < 0:
            N = -N
        if N @ v <= 1e-6:
            return oid
    elif N @ v < 0:
        N = -N
    if abs(N @ v) < 1e-6:
        return oid
    scr = np.array([s.to_screen(*p) for p in pts])
    x0 = max(0, int(math.floor(scr[:, 0].min())) - 1); x1 = min(s.W, int(math.ceil(scr[:, 0].max())) + 1)
    y0 = max(0, int(math.floor(scr[:, 1].min())) - 1); y1 = min(s.H, int(math.ceil(scr[:, 1].max())) + 1)
    if x1 <= x0 or y1 <= y0:
        return oid
    py, px = np.mgrid[y0:y1, x0:x1]
    cx, cy = px + 0.5, py + 0.5
    c0 = scr.mean(0)
    order = np.argsort(np.arctan2(scr[:, 1] - c0[1], scr[:, 0] - c0[0]))
    poly = scr[order]
    inside = np.ones(cx.shape, bool)
    for i in range(len(poly)):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % len(poly)]
        e = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        inside &= e >= -1e-6
    if not inside.any():
        return oid
    key = id(s.A)
    if key not in _AINV:
        _AINV[key] = np.linalg.pinv(s.A)
    Ai = _AINV[key]
    sx, sy = cx - s.ox, cy - s.oy
    q = np.einsum('ij,jhw->ihw', Ai, np.stack([sx, sy]))
    t = (N @ pts[0] - np.einsum('i,ihw->hw', N, q)) / (N @ v)
    Pw = q + t[None] * v[:, None, None]
    depth = np.einsum('i,ihw->hw', v, Pw)
    if oid is None:
        s.nobj += 1; oid = s.nobj
        if not lines:
            s.nolines.add(oid)
    if callable(fill):
        f = lambda yy, xx: fill(Pw[0, yy, xx], Pw[1, yy, xx], Pw[2, yy, xx])
    else:
        f = fill
    normal = tuple(int(np.sign(round(c * 1.4))) for c in N)
    s._paint((y0, y1, x0, x1), inside, depth, f, role, oid, [Pw[0], Pw[1], Pw[2]], normal)
    return oid

# ---------------------------------------------------------------- roofs
def roof_x(s, X, Y, Z, w, d, hr, fill_side, fill_end, hip=0.0, lines=True, oid=None):
    """a steep roof over [X, X+w] x [Y, Y+d] from eave height Z, ridge along x at Z+hr.
    Faces turned away from the viewer are skipped (the far slope of a steep roof, the -x end).
    hip > 0 pulls the ridge ends in (a hipped roof)."""
    ym = Y + d / 2.0
    zr = Z + hr
    a = X + hip; b = X + w - hip
    oid = plane(s, [(X, Y + d, Z), (X + w, Y + d, Z), (b, ym, zr), (a, ym, zr)], fill_side, 2, lines, oid, out=(0, 1, 1))
    oid = plane(s, [(X, Y, Z), (X + w, Y, Z), (b, ym, zr), (a, ym, zr)], fill_side, 2, lines, oid, out=(0, -1, 1))
    oid = plane(s, [(X + w, Y, Z), (X + w, Y + d, Z), (b, ym, zr)], fill_end, 3, lines, oid, out=(1, 0, 0.2))
    oid = plane(s, [(X, Y, Z), (X, Y + d, Z), (a, ym, zr)], fill_end, 3, lines, oid, out=(-1, 0, 0.2))
    return oid

def roof_y(s, X, Y, Z, w, d, hr, fill_side, fill_end, hip=0.0, lines=True, oid=None):
    """the same with the ridge along y: the +x slope ('right' role) and the +y end ('left')."""
    xm = X + w / 2.0
    zr = Z + hr
    a = Y + hip; b = Y + d - hip
    oid = plane(s, [(X + w, Y, Z), (X + w, Y + d, Z), (xm, b, zr), (xm, a, zr)], fill_side, 3, lines, oid, out=(1, 0, 1))
    oid = plane(s, [(X, Y, Z), (X, Y + d, Z), (xm, b, zr), (xm, a, zr)], fill_side, 3, lines, oid, out=(-1, 0, 1))
    oid = plane(s, [(X, Y + d, Z), (X + w, Y + d, Z), (xm, b, zr)], fill_end, 2, lines, oid, out=(0, 1, 0.2))
    oid = plane(s, [(X, Y, Z), (X + w, Y, Z), (xm, a, zr)], fill_end, 2, lines, oid, out=(0, -1, 0.2))
    return oid
