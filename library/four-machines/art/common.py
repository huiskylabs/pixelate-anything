"""Shared bits for the four panels of '05 Four Machines': the composition in fractions of the
screen (each panel maps it onto its own size and redraws every object for its machine), a few
drawing helpers on top of the kit's slot canvas, and the save / check plumbing.

Nothing here draws an object: every panel module draws its own glider, post office, houses, sea
and sky at its own size and under its own hardware rules.
"""
import math, pathlib, sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from PIL import Image
from canvas import Canvas                         # the kit's slot canvas (every pixel a slot name)
import colorlib as cl

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / 'out'
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- the shared composition
# fractions of width (u) and height (v); see brief.md section 4
COMP = dict(
    horizon=0.53,
    sun=(0.86, 0.53, 0.055),                     # centre u, v and radius as a fraction of W
    crag=[(0.30, 0.38), (0.36, 0.33), (0.42, 0.31), (0.47, 0.275), (0.52, 0.26), (0.565, 0.285),
          (0.63, 0.31), (0.68, 0.36), (0.74, 0.42), (0.80, 0.49), (0.83, 0.53)],
    plateau=0.34, cliff_edge=0.33, cliff_foot=0.40,
    office=(0.05, 0.14, 0.26, 0.34), pole=(0.275, 0.08),
    rail=((0.26, 0.31), (0.42, 0.36)),
    wing=(0.41, 0.35, 0.71, 0.41),
    town=(0.40, 0.64, 0.80, 0.86), harbour=0.86, mole=(0.62, 0.88),
    boat=(0.84, 0.89, 0.92),
    gulls=[(0.35, 0.20, 'L'), (0.76, 0.29, 'M'), (0.91, 0.41, 'S')],
)

def px(u, W):
    return int(round(u * W))

# ---------------------------------------------------------------- helpers
def stamp(c, art, key, x, y, flip=False):
    """a hand-typed grid onto a slot canvas: each character maps through key ('.' and ' ' are clear)"""
    rows = [r for r in art.strip('\n').split('\n')]
    for j, r in enumerate(rows):
        if flip:
            r = r[::-1]
        for i, ch in enumerate(r):
            if ch not in '. ' and ch in key and key[ch] is not None:
                c.put(x + i, y + j, key[ch])

def art_size(art):
    rows = art.strip('\n').split('\n')
    return max(len(r) for r in rows), len(rows)

def checker_rows(c, x0, x1, y0, y1, slot, parity=0, mask=None):
    """a 50% checker of `slot` over [x0,x1) x [y0,y1) (pixels where (x + y) % 2 == parity)"""
    for y in range(max(0, y0), min(c.H, y1)):
        for x in range(max(0, x0), min(c.W, x1)):
            if (x + y) % 2 == parity and (mask is None or mask[y, x]):
                c.g[y, x] = slot

def band_sky(c, stops, x0=0, x1=None, mask=None, seam=2):
    """flat bands of solid slots with a `seam`-row 50% checker between neighbours (the era way):
    stops = [(slot, y_start), ...] top to bottom"""
    x1 = c.W if x1 is None else x1
    for i, (slot, y) in enumerate(stops):
        y_end = stops[i + 1][1] if i + 1 < len(stops) else c.H
        for yy in range(max(0, y), min(c.H, y_end)):
            for xx in range(x0, x1):
                if mask is None or mask[yy, xx]:
                    c.g[yy, xx] = slot
        if i + 1 < len(stops) and seam:
            nxt = stops[i + 1][0]
            for yy in range(y_end - seam, y_end):
                for xx in range(x0, x1):
                    if (xx + yy) % 2 == 0 and (mask is None or mask[yy, xx]):
                        c.g[yy, xx] = nxt

def q15(h):
    """a hex colour snapped to the 15-bit (5 bits per channel) grid, as the era check does"""
    r, g, b = cl.hex_to_rgb(h)
    step = 255 / 31
    return '#%02x%02x%02x' % tuple(int(round(round(v / step) * step)) for v in (r, g, b))

def image(c, pal, bg=None):
    """slot canvas -> RGBA image; None pixels are transparent"""
    H, W = c.g.shape
    a = np.zeros((H, W, 4), np.uint8)
    lut = {k: cl.hex_to_rgb(v) for k, v in pal.items()}
    for y in range(H):
        for x in range(W):
            s = c.g[y, x]
            if s is not None:
                a[y, x, :3] = lut[s]; a[y, x, 3] = 255
    im = Image.fromarray(a, 'RGBA')
    if bg is not None:
        base = Image.new('RGBA', im.size, bg); base.alpha_composite(im); im = base
    return im

def over(*layers):
    """composite canvases back to front into a new canvas (None = see-through)"""
    H, W = layers[0].g.shape
    out = Canvas(W, H)
    for L in layers:
        m = L.g != None  # noqa: E711 (object array)
        out.g[m] = L.g[m]
    return out

def save(name, img, scale=4):
    """save the 1x image and its nearest-neighbour @Nx copy into out/"""
    img = img.convert('RGB')
    img.save(OUT / ('%s.png' % name))
    img.resize((img.width * scale, img.height * scale), Image.NEAREST).save(OUT / ('%s@%dx.png' % (name, scale)))
    return img

def crop_zoom(img, box, scale, name):
    """an nearest-neighbour zoom of a box of a 1x image, for looking (into the scratch dir)"""
    z = img.crop(box)
    z = z.resize((z.width * scale, z.height * scale), Image.NEAREST)
    z.save(name)
    return z

def sprite_boxes(spr_canvas, boxes):
    """(x, y, mask) per drawn sprite object, for era.check_sprites: boxes = [(x0, y0, x1, y1), ...]"""
    m = spr_canvas.g != None  # noqa: E711
    out = []
    for x0, y0, x1, y1 in boxes:
        out.append((x0, y0, m[y0:y1, x0:x1]))
    return out

def attr_report(c, pal, subpals, backdrop, block=16):
    """NES attribute check on a background slot canvas: every block's colours (minus the shared
    backdrop) must fit inside one of the declared 3-colour sub-palettes. -> (bad blocks, {block: index})"""
    H, W = c.g.shape
    bad, attr = [], {}
    for by in range(0, H, block):
        for bx in range(0, W, block):
            cols = {pal[s] for s in c.g[by:by + block, bx:bx + block].ravel() if s is not None} - {backdrop}
            fit = [i for i, sp in enumerate(subpals) if cols <= set(sp)]
            if fit:
                attr[(bx // block, by // block)] = fit[0]
            else:
                bad.append((bx, by, sorted(cols)))
    return bad, attr

def shade_facets(c, ids, base_slots, seam, lit, dark, skip=None):
    """irregular rock facets from a layout id map (0 = seam, > 0 = facet): each facet one base tone
    (picked by its id from base_slots), its sun-side (right) edge one lit step, its left edge one
    dark step, seams in `seam`. base_slots: list of (slot, lit_slot, dark_slot) triples."""
    H, W = ids.shape
    for y in range(H):
        for x in range(W):
            i = ids[y, x]
            if i < 0 or (skip is not None and skip[y, x]):
                continue
            if i == 0:
                c.g[y, x] = seam
                continue
            b, l, d = base_slots[((int(i) * 2654435761) >> 7) % len(base_slots)]
            r = ids[y, x + 1] if x + 1 < W else -1
            le = ids[y, x - 1] if x > 0 else -1
            up = ids[y - 1, x] if y > 0 else -1
            if r != i:
                c.g[y, x] = l
            elif up != i and (x + 1 < W and ids[y, min(W - 1, x + 2)] == i) and (y * 7 + x) % 3 != 0:
                c.g[y, x] = l
            elif le != i:
                c.g[y, x] = d
            else:
                c.g[y, x] = b

def torus_cells(w, h, sites, aspect=1.0):
    """a periodic Voronoi id map (w x h, wraps on both axes) with 1 px seams (0); ids from 1.
    aspect > 1 stretches cells vertically. For tile-budget eras: the pattern repeats exactly."""
    yy, xx = np.mgrid[0:h, 0:w]
    best = np.full((h, w), 1e9); sec = np.full((h, w), 1e9); idm = np.zeros((h, w), int)
    for k, (sx, sy) in enumerate(sites, 1):
        dx = np.minimum(abs(xx - sx), w - abs(xx - sx))
        dy = np.minimum(abs(yy - sy), h - abs(yy - sy)) / aspect
        d = np.hypot(dx, dy)
        closer = d < best
        sec = np.where(closer, best, np.minimum(sec, d))
        idm = np.where(closer, k, idm)
        best = np.where(closer, d, best)
    idm[(sec - best) < 0.9] = 0
    return idm

def rock_facets(c, mask, ids, planes, fracture, lip):
    """angular cliff facets from a Voronoi id map: each facet a plane (base, sun-side edge) picked by
    id; seams that run up and down are dark fractures, seams that run across are lit lips (ledge tops)"""
    H, W = ids.shape
    for y in range(H):
        for x in range(W):
            if not mask[y, x]:
                continue
            i = ids[y, x]
            if i == 0:
                l_, r_ = (ids[y, x - 1] if x > 0 else 0), (ids[y, x + 1] if x + 1 < W else 0)
                u_, d_ = (ids[y - 1, x] if y > 0 else 0), (ids[y + 1, x] if y + 1 < H else 0)
                flat = u_ > 0 and d_ > 0 and u_ != d_ and (l_ == 0 or r_ == 0 or l_ == r_)
                c.g[y, x] = lip if flat and (l_ == 0 and r_ == 0) is False else fracture
                continue
            b, l = planes[((int(i) * 2654435761) >> 9) % len(planes)]
            r = ids[y, x + 1] if x + 1 < W else i
            c.g[y, x] = l if r != i else b
