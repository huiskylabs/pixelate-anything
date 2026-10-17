"""Shared helpers for the Endless Ascent stills: hashing, palettes from OKLCh stops, masks, export.

Every pixel of a still is a palette slot on the integer grid; images are written at 1x and at a
whole nearest-neighbour scale, with the palette as JSON next to them.
"""
import sys, json, math, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from PIL import Image
import palette as P
from canvas import Canvas, BAYER4

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / 'out'
W, H = 270, 480
YY, XX = np.mgrid[0:H, 0:W]


# ------------------------------------------------------------------ hashing and noise
def hsh(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 15; h = (h * 2246822519) & 0xFFFFFFFF; h ^= h >> 13
    return (h & 0xFFFFFF) / 16777216.0


def hsh_arr(a, b, seed):
    h = (np.asarray(a).astype(np.int64) * 374761393 + np.asarray(b).astype(np.int64) * 668265263
         + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def noise1(u, seed):
    """smooth value noise in [-1, 1]"""
    i = math.floor(u); f = u - i
    s = f * f * (3 - 2 * f)
    return (hsh(i, seed) * (1 - s) + hsh(i + 1, seed) * s) * 2 - 1


def bayer(x, y):
    return BAYER4[int(y) & 3, int(x) & 3]


# ------------------------------------------------------------------ palettes
def build(ramps, singles=None):
    """{'bark': [(L, C, h), ...] darkest first} -> {'bark0': '#hex', ...}"""
    pal = {}
    for name, stops in ramps.items():
        for i, s in enumerate(stops):
            pal['%s%d' % (name, i)] = P.from_lch(*s)
    for k, s in (singles or {}).items():
        pal[k] = P.from_lch(*s)
    return pal


# ------------------------------------------------------------------ grid helpers
def new_grid(fill=None):
    return np.full((H, W), fill, dtype=object)


def put(g, x, y, v):
    x, y = int(x), int(y)
    if 0 <= x < g.shape[1] and 0 <= y < g.shape[0] and v is not None:
        g[y, x] = v


def stamp(g, art, key, ox, oy, only=None):
    """a hand-typed slot map (rows of characters, '.' clear) onto g at (ox, oy)"""
    rows = [r.strip() for r in art.strip('\n').split('\n')]
    rows = [r for r in rows if r]
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.' or ch == ' ':
                continue
            v = key[ch]
            if only is not None and not only(g[oy + j, ox + i] if 0 <= oy + j < g.shape[0] and 0 <= ox + i < g.shape[1] else None):
                continue
            put(g, ox + i, oy + j, v)
    return len(rows[0]) if rows else 0, len(rows)


def art_mask(art):
    rows = [r.strip() for r in art.strip('\n').split('\n')]
    rows = [r for r in rows if r]
    w = max(len(r) for r in rows)
    m = np.zeros((len(rows), w), bool)
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            m[j, i] = ch not in '. '
    return m


def nb4(m):
    """pixels with a 4-neighbour inside m (dilate by 1)"""
    o = m.copy()
    o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o


def shift(m, dx, dy):
    """mask moved by (dx, dy) without wrap"""
    o = np.zeros_like(m)
    h, w = m.shape
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    o[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = m[ys0:ys1, xs0:xs1]
    return o


def line_pts(x0, y0, x1, y1):
    """Bresenham points"""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy
    return pts


def sag_line(x0, y0, x1, y1, sag):
    """a hanging line as clean 1 px points: y = lerp + sag * 4t(1-t), one point per column"""
    pts = []
    n = max(1, abs(x1 - x0))
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        pts.append((int(round(x)), int(round(y))))
    # fill vertical gaps so the line stays connected
    out = []
    for i, (x, y) in enumerate(pts):
        if out:
            px, py = out[-1]
            while abs(y - py) > 1:
                py += 1 if y > py else -1
                out.append((px, py))
        out.append((x, y))
    return out


# ------------------------------------------------------------------ export
def save(g, pal, name, scale=4):
    """write out/NAME@1x.png, out/NAME.png at x scale, out/NAME-palette.json (only used slots)"""
    OUT.mkdir(parents=True, exist_ok=True)
    used = sorted(set(g.ravel()) - {None})
    missing = [k for k in used if k not in pal]
    if missing:
        raise KeyError('no colour for slots: ' + ', '.join(missing[:20]))
    from colorlib import hex_to_rgb
    keys = list(used)
    idx = np.zeros(g.shape, np.int32)
    for i, k in enumerate(keys):
        idx[g == k] = i
    rgb = np.array([hex_to_rgb(pal[k]) for k in keys], np.uint8)
    img = Image.fromarray(rgb[idx], 'RGB')
    img.save(OUT / ('%s@1x.png' % name))
    img.resize((g.shape[1] * scale, g.shape[0] * scale), Image.NEAREST).save(OUT / ('%s.png' % name))
    (OUT / ('%s-palette.json' % name)).write_text(json.dumps({k: pal[k] for k in keys}, indent=1))
    return img


def crop_zoom(name, box, zoom=4, tag='crop'):
    """a zoomed native crop for looking at: out/_look/NAME-TAG.png"""
    img = Image.open(OUT / ('%s@1x.png' % name))
    c = img.crop(box)
    d = OUT / '_look'
    d.mkdir(exist_ok=True)
    c.resize((c.width * zoom, c.height * zoom), Image.NEAREST).save(d / ('%s-%s.png' % (name, tag)))
