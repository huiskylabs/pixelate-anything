"""Morphology on bool masks: shifts, dilate and erode, distance fields, facing edges, connected
regions and outward normals. The shared base that materials, light and outlines build on.

    import morph
    m = c.g == 'rock3'                                  # any H x W bool mask
    ol   = morph.boundary(m)                            # the 1px outline just outside m
    top  = morph.edges(m, 'up')                         # pixels of m with open space above
    d    = morph.distance(m)                            # 1 on the rim, 2 one pixel in, ... (3-4 chamfer)
    halo = morph.distance_outside(m, 'euclid')          # the field an outer glow falls off along
    ids, n = morph.label(m, 8)                          # blobs numbered 1..n, 0 = background
    nx, ny = morph.normals(m)                           # unit outward normals for rim light
    rim  = morph.edges(m) & (nx * -0.6 + ny * -0.8 > 0.35)   # the rim that faces an upper-left light
    seam = morph.cell_distance(block_ids)               # per block: distance to the next block
    bnx, bny = morph.cell_normals(block_ids)            # per block: which way its rim faces
    clean = morph.remove_small(morph.fill_holes(morph.close(m, 2, 'disc')), 4)
    nx, ny, nz = morph.relief(block_ids, r=3)           # each block raised as a pillow (10)
    ys, xs = morph.nearest(lamps)                       # the nearest lamp pixel: colour bleed, voronoi
    d = morph.distance(tile, border='wrap')             # seamless tiles: opposite sides meet

Every reference study needed these (a Celeste cloud's glow measured along a chamfer field, the
Owlboy and Stardew block rims at d in [1, 2) on the lit side, Sea of Stars sea bands by distance
from the shore, Hyper Light Drifter and Katana ZERO outer glows), and re-derived them inline
because there is no scipy. This module is numpy only and fast: a 480 x 270 field takes a few
milliseconds (chamfer) to a few tens of milliseconds (exact euclid).

Conventions. y grows downward, so 'up' is (0, -1). shift(m, dx, dy) moves content by (dx, dy).
Distances are measured between pixel centres: a pixel that touches the outside is 1, the next
ring in is 2. Beyond the frame the art continues (border=None, the default everywhere): a ground
that runs off the bottom has no edge, no rim and no distance to the frame there. border=False
makes beyond-the-frame count as outside the mask, border=True as inside, and border='wrap'
joins opposite sides (seamless tiles; 'edge' is another name for None). Slot grids go through
regions(c.g) (or straight into cell_distance), with base=True to merge the steps of one ramp.
"""
import builtins, math
import numpy as np

__all__ = ['shift', 'dilate', 'erode', 'open_', 'close', 'distance', 'distance_outside',
           'cell_distance', 'edges', 'boundary', 'label', 'fill_holes', 'remove_small',
           'normals', 'cell_normals', 'ball', 'DIRS',
           'signed', 'nearest', 'relief', 'regions']

INF = np.inf

DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0),
        'upleft': (-1, -1), 'upright': (1, -1), 'downleft': (-1, 1), 'downright': (1, 1)}
for _k, _v in list(DIRS.items()):                       # compass aliases: n s e w nw ne sw se
    DIRS[{'up': 'n', 'down': 's', 'left': 'w', 'right': 'e', 'upleft': 'nw', 'upright': 'ne',
          'downleft': 'sw', 'downright': 'se'}[_k]] = _v

# structuring elements for dilate/erode, distance metrics for the fields
_BALL = {'square': 'square', 'box': 'square', 'chessboard': 'square', 'cheb': 'square', 8: 'square',
         'cross': 'cross', 'diamond': 'cross', 'manhattan': 'cross', 4: 'cross',
         'disc': 'disc', 'circle': 'disc', 'round': 'disc', 'euclid': 'disc'}
_CHAMFER = {'chamfer34': (3, 4, 3.0), 'chamfer': (3, 4, 3.0),       # (axis step, diagonal step, unit)
            'manhattan': (1, 2, 1.0), 'cross': (1, 2, 1.0), 'taxicab': (1, 2, 1.0), 4: (1, 2, 1.0),
            'chessboard': (1, 1, 1.0), 'cheb': (1, 1, 1.0), 'square': (1, 1, 1.0), 8: (1, 1, 1.0)}
_EUCLID = ('euclid', 'euclidean', 'disc')
_BIG_R = 16                     # beyond this radius dilate thresholds a distance field instead

def _mask(m):
    m = np.asarray(m, dtype=bool)
    if m.ndim != 2:
        raise ValueError('morph works on 2-d masks, got shape %s' % (m.shape,))
    return m

def _bd(border):
    """normalise border: None (the art carries on; 'edge' is an alias), False, True or 'wrap'"""
    if isinstance(border, str):
        b = border.lower()
        if b in ('edge', 'none', 'carry'):
            return None
        if b in ('wrap', 'tile'):
            return 'wrap'
        raise ValueError("unknown border %r (None, False, True, 'wrap')" % (border,))
    return None if border is None else bool(border)

def _neg(border):
    return border if border is None or border == 'wrap' else not border

def _on_torus(f, a, margin=0):
    """f(a) on a seamless tile: run f (with border=None) on a copy padded with the opposite sides,
    half a frame plus margin each way, and cut the middle back out. Exact for every field here:
    the nearest pixel on the torus is never more than half a frame away."""
    H, W = a.shape[:2]
    py, px = H // 2 + margin + 1, W // 2 + margin + 1
    out = f(np.pad(a, ((py, py), (px, px)), mode='wrap'))
    cut = lambda o: np.ascontiguousarray(o[py:py + H, px:px + W])
    return tuple(cut(o) for o in out) if isinstance(out, tuple) else cut(out)

def _pad(m, r, border):
    if border is None or border == 'wrap':
        return np.pad(m, r, mode='edge' if border is None else 'wrap')
    return np.pad(m, r, mode='constant', constant_values=border)

# ---------------------------------------------------------------- shifts
def shift(m, dx, dy, fill=False):
    """m moved by (dx, dy): out[y, x] = m[y - dy, x - dx]. Pixels that move in from beyond the
    frame get `fill`; fill='edge' repeats the border row or column. Works on any array whose
    first two axes are y, x (a bool mask, a slot grid with fill=None, an RGB frame)."""
    a = np.asarray(m)
    dx, dy = int(dx), int(dy)
    H, W = a.shape[:2]
    if isinstance(fill, str) and fill == 'wrap':        # the opposite side comes in (tiles)
        return np.roll(a, (dy, dx), (0, 1))
    if isinstance(fill, str) and fill == 'edge':
        yi = np.clip(np.arange(H) - dy, 0, H - 1)
        xi = np.clip(np.arange(W) - dx, 0, W - 1)
        return a[yi][:, xi]
    out = np.full_like(a, fill)
    if abs(dx) >= W or abs(dy) >= H:
        return out
    out[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] = \
        a[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
    return out

def _nb(m, dx, dy, border):
    """the value of the neighbour at p + (dx, dy), for every p"""
    return shift(m, -dx, -dy, 'edge' if border is None else border if border == 'wrap' else bool(border))

# ---------------------------------------------------------------- dilate / erode
def _metric(metric, conn):
    if conn is not None:
        metric = conn
    try:
        return _BALL[metric]
    except (KeyError, TypeError):
        raise ValueError('unknown metric %r (square, cross, disc)' % (metric,))

def ball(r, metric='square'):
    """the structuring element as a (2R+1) x (2R+1) bool array. 'disc' keeps the offsets within
    r + 0.4 of the centre, the pixel-art circle: r=1 is the plus, r=2 the 5 px round
    (3-5-5-5-3), r=3 the 7 px round (3-5-7-7-7-5-3)."""
    half = _halfwidths(r, _metric(metric, None))
    R = len(half) // 2
    xs = np.abs(np.arange(-R, R + 1))
    return xs[None, :] <= half[:, None]

def _halfwidths(r, metric):
    """half the row width of the ball at each dy in -R..R"""
    if metric == 'disc':
        rr = (r + 0.4) ** 2
        R = int(math.floor(r + 0.4))
        dy = np.arange(-R, R + 1)
        return np.floor(np.sqrt(np.maximum(rr - dy * dy, 0)) + 1e-9).astype(int)
    R = int(r)
    if R != r:
        raise ValueError('%s radius must be a whole number, got %r' % (metric, r))
    dy = np.arange(-R, R + 1)
    return np.full(2 * R + 1, R) if metric == 'square' else R - np.abs(dy)

def dilate(m, r=1, metric='square', border=None, conn=None):
    """grow m by r pixels. metric 'square' (8-neighbour, a box), 'cross' (4-neighbour, a
    diamond) or 'disc' (see ball). conn=4|8 is shorthand for cross|square. r < 0 erodes."""
    border = _bd(border)
    m = _mask(m)
    metric = _metric(metric, conn)
    if r < 0:
        return erode(m, -r, metric, border)
    if r == 0:
        return m.copy()
    half = _halfwidths(r, metric)
    R = len(half) // 2
    if R > _BIG_R:                              # large radius: one distance field is cheaper
        if metric == 'disc':
            return distance_outside(m, 'euclid', border=border) <= r + 0.4 + 1e-9
        return distance_outside(m, 'chessboard' if metric == 'square' else 'manhattan',
                                border=border) <= R
    H, W = m.shape
    P = _pad(m, R, border)
    cur = P.copy()                              # P dilated along rows by w, for w ascending
    out = np.zeros((H, W), bool)
    w = 0
    for want in np.unique(half):
        while w < want:
            w += 1
            cur[:, w:] |= P[:, :-w]
            cur[:, :-w] |= P[:, w:]
        for i in np.nonzero(half == want)[0]:   # i = dy + R
            out |= cur[i:i + H, R:R + W]
    return out

def erode(m, r=1, metric='square', border=None, conn=None):
    """shrink m by r pixels (a pixel survives when the whole ball around it is in m)"""
    border = _bd(border)
    m = _mask(m)
    metric = _metric(metric, conn)
    if r < 0:
        return dilate(m, -r, metric, border)
    return ~dilate(~m, r, metric, _neg(border))

def open_(m, r=1, metric='square', border=None, conn=None):
    """erode then dilate: removes specks and spurs thinner than the ball, keeps the rest"""
    return dilate(erode(m, r, metric, border, conn), r, metric, border, conn)

def close(m, r=1, metric='square', border=None, conn=None):
    """dilate then erode: fills notches and gaps narrower than the ball"""
    return erode(dilate(m, r, metric, border, conn), r, metric, border, conn)

# ---------------------------------------------------------------- distance fields
def _chamfer(d, a, b, ids=None):
    """two-pass chamfer in place on d (0 at sources, inf elsewhere): axis steps cost a, diagonal
    steps b. Rows are swept in a Python loop; the dependency along a row is a running minimum,
    min over x' <= x of d[x'] + a (x - x'), which numpy does in one accumulate. With ids,
    propagation only runs between equal ids and a pixel next to another id is a source."""
    H, W = d.shape
    ramp = a * np.arange(W, dtype=d.dtype)
    if ids is not None:
        st = np.zeros((H, W), bool)
        st[:, 1:] = ids[:, 1:] != ids[:, :-1]           # left neighbour is another cell
        en = np.zeros((H, W), bool)
        en[:, :-1] = st[:, 1:]                          # right neighbour is another cell
        up = ids[1:] == ids[:-1]                        # (y+1, x) ~ (y, x)
        dr = ids[1:, 1:] == ids[:-1, :-1]               # (y+1, x+1) ~ (y, x)
        dl = ids[1:, :-1] == ids[:-1, 1:]               # (y+1, x-1) ~ (y, x)
    for y in range(H):                                  # forward: rows top-down, left to right
        v = d[y]
        if y:
            p = d[y - 1]
            if ids is None:
                v = np.minimum(v, p + a)
                v[1:] = np.minimum(v[1:], p[:-1] + b)
                v[:-1] = np.minimum(v[:-1], p[1:] + b)
            else:
                v = np.minimum(v, np.where(up[y - 1], p, 0) + a)
                v[1:] = np.minimum(v[1:], np.where(dr[y - 1], p[:-1], 0) + b)
                v[:-1] = np.minimum(v[:-1], np.where(dl[y - 1], p[1:], 0) + b)
        if ids is not None:
            v = np.where(st[y], np.minimum(v, a), v)
        d[y] = np.minimum.accumulate(v - ramp) + ramp
    for y in range(H - 1, -1, -1):                      # backward: bottom-up, right to left
        v = d[y]
        if y < H - 1:
            n = d[y + 1]
            if ids is None:
                v = np.minimum(v, n + a)
                v[:-1] = np.minimum(v[:-1], n[1:] + b)
                v[1:] = np.minimum(v[1:], n[:-1] + b)
            else:
                v = np.minimum(v, np.where(up[y], n, 0) + a)
                v[:-1] = np.minimum(v[:-1], np.where(dr[y], n[1:], 0) + b)
                v[1:] = np.minimum(v[1:], np.where(dl[y], n[:-1], 0) + b)
        if ids is not None:
            v = np.where(en[y], np.minimum(v, a), v)
        d[y] = np.minimum.accumulate((v + ramp)[::-1])[::-1] - ramp
    return d

def _edt(src, cap=None):
    """exact euclidean distance from every pixel to the nearest True pixel of src (inf if none).
    Separable: the distance g along each column first (two running extrema), then along rows
    D^2(x) = min_k g(x+k)^2 + k^2, widening k until no pixel can still improve (or k > cap)."""
    H, W = src.shape
    if W > H:                                           # widen k along the shorter axis
        return np.ascontiguousarray(_edt(np.ascontiguousarray(src.T), cap).T)
    yy = np.arange(H)[:, None]
    big = H + W + 1
    last = np.maximum.accumulate(np.where(src, yy, -big), axis=0)
    nxt = np.minimum.accumulate(np.where(src, yy, 2 * big)[::-1], axis=0)[::-1]
    g = np.minimum(yy - last, nxt - yy).astype(float)
    g[g > H] = INF
    g2 = g * g
    D2 = g2.copy()
    k = 1
    while k < W:
        k2 = float(k * k)
        if cap is not None and k > cap:
            break
        if k & 7 == 1 and not (D2 > k2).any():          # nothing left that offset k could beat
            break
        np.minimum(D2[:, k:], g2[:, :-k] + k2, out=D2[:, k:])
        np.minimum(D2[:, :-k], g2[:, k:] + k2, out=D2[:, :-k])
        k += 1
    return np.sqrt(D2)

def _field(src, metric, cap):
    """distance to the nearest True pixel of src, in pixels"""
    if metric in _EUCLID:
        return _edt(src, cap)
    try:
        a, b, unit = _CHAMFER[metric]
    except (KeyError, TypeError):
        raise ValueError('unknown metric %r (chamfer34, manhattan, chessboard, euclid)' % (metric,))
    d = np.where(src, 0.0, INF)
    if d.shape[0] > d.shape[1]:                         # loop over the shorter axis
        d = np.ascontiguousarray(_chamfer(np.ascontiguousarray(d.T), a, b).T)
    else:
        _chamfer(d, a, b)
    return d / unit if unit != 1 else d

def distance(m, metric='chamfer34', max=None, border=None):
    """for each pixel of m, the distance to the nearest pixel outside m (0 outside). metric:
    'chamfer34' (axis 1, diagonal 4/3: round enough for bands and glows), 'manhattan',
    'chessboard', or 'euclid' (exact). max caps the field (and lets euclid stop early); pixels
    with nothing outside in reach get inf (or max). border=False: the frame edge is outside."""
    if _bd(border) == 'wrap':
        return _on_torus(lambda a: distance(a, metric, max, None), _mask(m))
    border = _bd(border)
    m = _mask(m)
    if border is False:
        m = np.pad(m, 1, constant_values=False)
    d = _field(~m, metric, max)
    if border is False:
        d = d[1:-1, 1:-1]
    if max is not None:
        np.minimum(d, max, out=d)
    return d

def distance_outside(m, metric='chamfer34', max=None, border=None):
    """for each pixel outside m, the distance to the nearest pixel of m (0 inside): the field an
    outer glow, a halo or a drop of light falls off along. border=True: beyond the frame is m."""
    return distance(~_mask(m), metric, max, _neg(_bd(border)))

def _codes(ids, bg):
    """ids (ints, strings, slot names, None) -> dense int codes 0..k-1, bg -> -1"""
    a = np.asarray(ids)
    if a.ndim != 2:
        raise ValueError('ids must be 2-d, got shape %s' % (a.shape,))
    flat = a.ravel()
    if a.dtype.kind in 'biuf':
        vals, inv = np.unique(flat, return_inverse=True)
        codes = inv.reshape(a.shape).astype(np.int64)
        if bg is not None:
            codes[a == bg] = -1
        return codes, len(vals)
    seen = {}
    codes = np.fromiter((seen.setdefault(v, len(seen)) for v in flat), np.int64, flat.size)
    codes = codes.reshape(a.shape)
    if bg is not None and bg in seen:
        codes[codes == seen[bg]] = -1
    return codes, len(seen)

def cell_distance(ids, metric='chamfer34', bg=None, max=None, border=None):
    """for each pixel, the distance to the nearest pixel with a different id: an id map of
    blocks, bricks, tiles or labels in, the distance to each block's seam out (1 on the seam
    row, 2 next in). Pixels whose id equals bg count as outside every cell (0). ids may be ints
    or slot names (a Canvas grid). The path stays inside the cell, as in a chamfer per cell."""
    if _bd(border) == 'wrap':
        return _on_torus(lambda a: cell_distance(a, metric, -1, max, None), _codes(ids, bg)[0])
    border = _bd(border)
    codes, k = _codes(ids, bg)
    if border is False:
        codes = np.pad(codes, 1, constant_values=-1)
    H, W = codes.shape
    if metric in _EUCLID:                              # every cell at once, exact
        d = _edt_ids(codes, max)[0]
    else:
        try:
            a, b, unit = _CHAMFER[metric]
        except (KeyError, TypeError):
            raise ValueError('unknown metric %r' % (metric,))
        d = np.where(codes < 0, 0.0, INF)
        if H > W:
            d = np.ascontiguousarray(_chamfer(np.ascontiguousarray(d.T), a, b,
                                              np.ascontiguousarray(codes.T)).T)
        else:
            _chamfer(d, a, b, codes)
        if unit != 1:
            d /= unit
    if border is False:
        d = d[1:-1, 1:-1]
    if max is not None:
        np.minimum(d, max, out=d)
    return d


# ---------------------------------------------------------------- edges
def _facings(facing, conn):
    if facing is None:
        return [(0, -1), (0, 1), (-1, 0), (1, 0)] + ([(-1, -1), (1, -1), (-1, 1), (1, 1)] if conn == 8 else [])
    if isinstance(facing, str):
        try:
            return [DIRS[facing.lower().replace('-', '').replace('_', '')]]
        except KeyError:
            raise ValueError('unknown facing %r (%s)' % (facing, ', '.join(DIRS)))
    if len(facing) == 2 and all(isinstance(v, (int, np.integer)) for v in facing):
        return [(int(facing[0]), int(facing[1]))]
    if len(facing) == 2 and all(isinstance(v, (float, np.floating)) for v in facing):
        vx, vy = float(facing[0]), float(facing[1])
        if vx.is_integer() and vy.is_integer():
            return [(int(vx), int(vy))]
        k = round(math.atan2(vy, vx) / (math.pi / 4))  # a light vector: the nearest of the 8
        return [(int(round(math.cos(k * math.pi / 4))), int(round(math.sin(k * math.pi / 4))))]
    return [f for one in facing for f in _facings(one, conn)]

def edges(m, facing=None, width=1, conn=4, border=None):
    """the pixels of m whose neighbour toward `facing` lies outside m: 'up' gives the top rim
    (open space above), 'left', 'down', 'right', a diagonal ('upleft' or 'nw', ...), an (dx, dy)
    step, or a list of these for their union. facing=None: any 4-neighbour (conn=8: any of the
    8) is outside, the inner boundary. width > 1 widens the band: a pixel counts when any of the
    next `width` pixels that way is outside. A float vector such as a light direction (-0.45,
    -0.89) picks the nearest of the 8 neighbours; for a smooth facing test use normals()."""
    border = _bd(border)
    m = _mask(m)
    if facing is None and width > 1:
        return m & ~erode(m, width, 'cross' if conn == 4 else 'square', border)
    out = np.zeros_like(m)
    for dx, dy in _facings(facing, conn):
        for k in range(1, int(width) + 1):
            out |= ~_nb(m, k * dx, k * dy, border)
    return m & out

def boundary(m, outer=True, conn=4, border=None):
    """outer=True: the pixels just outside m that touch it (conn=4: share a side, the clean
    pixel-art outline; conn=8: also a corner, which fills the diagonal steps). outer=False: the
    pixels of m that touch the outside (edges(m))."""
    border = _bd(border)
    m = _mask(m)
    if outer:
        return dilate(m, 1, 'cross' if conn == 4 else 'square', border) & ~m
    return edges(m, None, 1, conn, border)

# ---------------------------------------------------------------- connected regions
def label(m, connectivity=4, conn=None, border=None):
    """number the connected regions of m: (labels, n), labels an int32 array with 0 outside m
    and 1..n in raster order of each region's first pixel. connectivity 4 (sides) or 8 (also
    corners). Scan-line union-find: the rows are cut into runs, runs that touch across a row
    are joined by vectorised hook-and-compress rounds. border='wrap' also joins across opposite
    sides (a tile)."""
    m = _mask(m)
    c = conn or connectivity
    if c not in (4, 8):
        raise ValueError('connectivity must be 4 or 8')
    H, W = m.shape
    start = m.copy()
    start[:, 1:] &= ~m[:, :-1]
    nr = int(start.sum())
    lab = np.zeros((H, W), np.int32)
    if nr == 0:
        return lab, 0
    run = (np.cumsum(start.ravel()) - 1).reshape(H, W)      # run index of every pixel of m
    pairs = [(m[:-1] & m[1:], run[:-1], run[1:])]
    if c == 8:
        pairs.append((m[:-1, :-1] & m[1:, 1:], run[:-1, :-1], run[1:, 1:]))
        pairs.append((m[:-1, 1:] & m[1:, :-1], run[:-1, 1:], run[1:, :-1]))
    if _bd(border) == 'wrap':                           # every neighbour pair on the torus
        pairs = [(m & np.roll(m, (-dy, -dx), (0, 1)), run, np.roll(run, (-dy, -dx), (0, 1)))
                 for dx, dy in [(1, 0), (0, 1)] + ([(1, 1), (-1, 1)] if c == 8 else [])]
    a = np.concatenate([ra[v] for v, ra, rb in pairs])
    b = np.concatenate([rb[v] for v, ra, rb in pairs])
    parent = np.arange(nr)
    if len(a):
        key = np.unique(a.astype(np.int64) * nr + b)        # each touching run pair once
        a, b = key // nr, key % nr
        while len(a):
            ra, rb = parent[a], parent[b]
            live = ra != rb
            if not live.any():
                break
            a, b, ra, rb = a[live], b[live], ra[live], rb[live]
            np.minimum.at(parent, np.maximum(ra, rb), np.minimum(ra, rb))   # hook root to smaller
            while True:                                     # compress to roots
                pp = parent[parent]
                if np.array_equal(pp, parent):
                    break
                parent = pp
    roots, ranked = np.unique(parent, return_inverse=True)
    lab[m] = (ranked.ravel() + 1).astype(np.int32)[run[m]]
    return lab, len(roots)

def fill_holes(m, conn=8):
    """m with its enclosed holes filled. conn is the connectivity of the shape: with 8 (the
    default, pixel-art lines step diagonally) a diagonal wall still closes a hole. A hole that
    reaches the frame edge is not enclosed (the art continues beyond the frame)."""
    m = _mask(m)
    lab, n = label(~m, 4 if conn == 8 else 8)
    open_ids = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return m | ((lab > 0) & ~np.isin(lab, open_ids))

def remove_small(m, min_px=2, conn=8):
    """m without regions smaller than min_px pixels (min_px=2 drops orphan pixels)"""
    m = _mask(m)
    lab, n = label(m, conn)
    size = np.bincount(lab.ravel(), minlength=n + 1)
    size[0] = 0
    return size[lab] >= min_px

# ---------------------------------------------------------------- normals
def _box(a, r):
    """mean over the (2r+1)^2 box, borders replicated"""
    if r <= 0:
        return a
    p = np.pad(a, r, mode='edge')
    H, W = a.shape
    rows = sum(p[:, i:i + W] for i in range(2 * r + 1))
    return sum(rows[i:i + H] for i in range(2 * r + 1)) / float((2 * r + 1) ** 2)

def _unit(gx, gy):
    n = np.hypot(gx, gy)
    ok = n > 1e-6
    n = np.where(ok, n, 1.0)
    return np.where(ok, gx / n, 0.0), np.where(ok, gy / n, 0.0)

def normals(m, blur=1, border=None):
    """unit outward normals (nx, ny) of m, from the gradient of its signed distance field (exact
    euclid, the zero level half way between the rim and the first pixel outside), averaged
    over a (2 blur + 1)^2 box so a stair-stepped edge gets one smooth direction. Defined on both
    sides of the edge (the outline pixels just outside get the normal too); (0, 0) where the
    field is flat. y down: a top rim has ny = -1. Light from the upper left lights the pixels
    where nx * -0.6 + ny * -0.8 > 0."""
    if _bd(border) == 'wrap':
        return _on_torus(lambda a: normals(a, blur, None), _mask(m), int(blur) + 2)
    border = _bd(border)
    m = _mask(m)
    if border is not None:                              # a real ring of border pixels, cropped after
        nx, ny = normals(np.pad(m, 1, constant_values=bool(border)), blur)
        return nx[1:-1, 1:-1], ny[1:-1, 1:-1]
    s = np.where(m, 0.5 - distance(m, 'euclid'), distance_outside(m, 'euclid') - 0.5)
    s = np.where(np.isfinite(s), s, 0.0)
    gx = (_nb(s, 1, 0, None) - _nb(s, -1, 0, None)) * 0.5
    gy = (_nb(s, 0, 1, None) - _nb(s, 0, -1, None)) * 0.5
    return _unit(_box(gx, blur), _box(gy, blur))

def cell_normals(ids, blur=1, bg=None, border=None, metric='chamfer34'):
    """unit outward normals of every cell of an id map (each block's own rim direction, toward
    its nearest seam), from the gradient of cell_distance; differences and the blur box stay
    inside each cell. (0, 0) on bg pixels and where a cell is flat. The chamfer field gives the
    same rim normals as the exact one (0.1% of lit-rim pixels differ) at a third of the cost."""
    if _bd(border) == 'wrap':
        return _on_torus(lambda a: cell_normals(a, blur, -1, None, metric), _codes(ids, bg)[0], int(blur) + 2)
    border = _bd(border)
    codes, _ = _codes(ids, bg)
    if border is False:                                 # the frame is a seam: a ring of bg, cropped after
        nx, ny = cell_normals(np.pad(codes, 1, constant_values=-1), blur, -1, None, metric)
        return nx[1:-1, 1:-1], ny[1:-1, 1:-1]
    s = -cell_distance(codes, metric, bg=-1)
    s = np.where(np.isfinite(s), s, 0.0)
    def nbv(dx, dy):                                    # another cell's pixel reads as the seam: 0
        return np.where(_nb(codes, dx, dy, None) == codes, _nb(s, dx, dy, None), 0.0)
    gx = (nbv(1, 0) - nbv(-1, 0)) * 0.5
    gy = (nbv(0, 1) - nbv(0, -1)) * 0.5
    if blur > 0:                                        # box mean over same-cell pixels only
        sx, sy, cnt = np.zeros_like(gx), np.zeros_like(gy), np.zeros_like(gx)
        for oy in range(-blur, blur + 1):
            for ox in range(-blur, blur + 1):
                k = _nb(codes, ox, oy, None) == codes
                sx += np.where(k, _nb(gx, ox, oy, None), 0.0)
                sy += np.where(k, _nb(gy, ox, oy, None), 0.0)
                cnt += k
        gx, gy = sx / cnt, sy / cnt
    nx, ny = _unit(gx, gy)
    fg = codes >= 0
    return np.where(fg, nx, 0.0), np.where(fg, ny, 0.0)


# ---------------------------------------------------------------- nearest pixel, signed field, relief, regions
def _edt_ids(ids, cap=None, index=False):
    """exact euclidean distance from each pixel of id >= 0 to the nearest pixel of another id
    (ids < 0 are 0), every cell at once. Down each column, h = the distance from a pixel to the
    ends of its own vertical run; then along each row D^2(x) = min over k of k^2 + (h(x +- k)^2
    when that pixel has x's id, else 0). Exact, because in a column whose pixel shares x's id the
    nearest other id is the end of that pixel's run. index=True also returns the (y, x) of the
    pixel found."""
    H, W = ids.shape
    big = 2 * (H + W) + 4
    INF2 = 4 * big * big
    it = np.int32 if INF2 + 4 * W * W < 2 ** 31 else np.int64
    rows = np.arange(H, dtype=it)[:, None]
    first = np.ones((H, W), bool); first[1:] = ids[1:] != ids[:-1]
    last = np.ones((H, W), bool); last[:-1] = ids[:-1] != ids[1:]
    top = np.maximum.accumulate(np.where(first, rows, 0), axis=0)          # first row of the run
    bot = np.minimum.accumulate(np.where(last, rows, H - 1)[::-1], axis=0)[::-1]   # its last row
    du = np.where(top > 0, rows - top + 1, big)
    dd = np.where(bot < H - 1, bot - rows + 1, big)
    g = np.minimum(du, dd)
    g2 = np.where(g < big, g * g, INF2).astype(it)
    empty = ids < 0
    D2 = np.where(empty, 0, g2).astype(it)
    binary = ids.min() >= -1 and ids.max() <= 0          # a mask: every other-id pixel is empty
    if binary:
        g2 = np.where(empty, 0, g2)
    if index:
        sy0 = np.where(du <= dd, top - 1, bot + 1)
        sy = np.where(empty, rows, sy0)
        sx = np.broadcast_to(np.arange(W)[None, :], (H, W)).copy()
        cols = np.broadcast_to(np.arange(W)[None, :], (H, W))
        rr = np.broadcast_to(rows, (H, W))
    lim = W - 1 if cap is None else builtins.min(W - 1, int(math.floor(cap)))
    for k in range(1, lim + 1):
        kk = k * k
        if kk >= D2.max():
            break
        for dst, src in ((np.s_[:, k:], np.s_[:, :-k]), (np.s_[:, :-k], np.s_[:, k:])):
            same = None if binary else ids[src] == ids[dst]
            cand = (g2[src] if binary else np.where(same, g2[src], 0)) + kk
            t = D2[dst]
            better = cand < t
            np.copyto(t, cand, where=better)
            if index:
                srow = np.where(empty[src], rr[src], sy0[src]) if binary else np.where(same, sy0[src], rr[src])
                np.copyto(sy[dst], srow, where=better)
                np.copyto(sx[dst], cols[src], where=better)
    D = np.sqrt(D2.astype(float))
    D[D2 >= INF2] = INF
    return (D, sy, sx) if index else (D,)

def signed(m, metric='euclid', border=None):
    """the signed distance with tools/sdf.py's sign: negative inside, positive outside, zero on
    the pixel edges between them (-0.5 on the rim pixels, +0.5 on the outline pixels)"""
    m = _mask(m)
    return np.where(m, 0.5 - distance(m, metric, border=border),
                    distance_outside(m, metric, border=border) - 0.5)

def nearest(m, border=None):
    """(ys, xs): for every pixel, the coordinates of the nearest pixel of m (euclid); pixels of m
    point at themselves, all -1 when m is empty. c.g[ys, xs] bleeds each emitter's slot out to
    the pixels it is nearest to; seed pixels give voronoi cells (ids = ys * W + xs).
    border: None (or False) or 'wrap'."""
    m = _mask(m)
    H, W = m.shape
    if not m.any():
        return np.full((H, W), -1), np.full((H, W), -1)
    if _bd(border) == 'wrap':
        py, px = H // 2 + 1, W // 2 + 1
        ys, xs = nearest(np.pad(m, ((py, py), (px, px)), mode='wrap'))
        return (ys[py:py + H, px:px + W] - py) % H, (xs[py:py + H, px:px + W] - px) % W
    _, ys, xs = _edt_ids(np.where(m, -1, 0), index=True)
    return ys, xs

def regions(g, base=False, bg=None):
    """an int id map from a slot grid (Canvas.g) or any array of labels: one id per distinct
    value, -1 for None and for bg. base=True gives all the steps of a ramp one id ('rock2' and
    'rock4' are both 'rock'), so cell_distance(regions(c.g, True)) runs to the next material,
    not to the next shade."""
    a = np.asarray(g)
    if base:
        a = np.array([v.rstrip('0123456789') if isinstance(v, str) else v for v in a.ravel()],
                     object).reshape(a.shape)
        if isinstance(bg, str):
            bg = bg.rstrip('0123456789')
    codes, _ = _codes(a, bg)
    if a.dtype == object:
        codes[np.equal(a, None)] = -1
    return codes

def relief(m, r=3, blur=1, bg=None, border=None):
    """(nx, ny, nz): the normals of m raised as a pillow whose edge rounds over r px (a quarter
    circle up from the rim, flat on top). Shade with nx*Lx + ny*Ly + nz*Lz. An id map (or slot
    grid) raises every cell as its own lump with the seams at height 0: pillow stones (10),
    cobbles, slabs. (0, 0, 1) outside m and on bg."""
    a = np.asarray(m)
    codes = np.where(_mask(a), 0, -1) if a.dtype == bool else _codes(a, bg)[0]
    border = _bd(border)
    if border == 'wrap':
        return _on_torus(lambda c: relief(c, r, blur, -1, None), codes, int(blur) + int(r) + 2)
    d = cell_distance(codes, 'euclid', bg=-1, border=border)
    fg = codes >= 0
    r = float(r) if r > 0 else 1e-6
    t = np.clip(np.where(np.isfinite(d), d - 0.5, r) / r, 0, 1)
    h = np.where(fg, r * np.sqrt(1 - (1 - t) ** 2), 0.0)
    nc = lambda dx, dy: shift(codes, -dx, -dy, -2 if border is False else 'edge')
    hv = lambda dx, dy: np.where(nc(dx, dy) == codes, shift(h, -dx, -dy, 'edge'), 0.0)   # seam floor: 0
    gx, gy = (hv(1, 0) - hv(-1, 0)) * 0.5, (hv(0, 1) - hv(0, -1)) * 0.5
    b = int(blur)
    if b > 0:                                           # box mean over same-cell pixels only
        sx, sy, cnt = np.zeros_like(gx), np.zeros_like(gy), np.zeros_like(gx)
        for oy in range(-b, b + 1):
            for ox in range(-b, b + 1):
                k = shift(codes, -ox, -oy, 'edge') == codes
                sx += np.where(k, shift(gx, -ox, -oy, 'edge'), 0.0)
                sy += np.where(k, shift(gy, -ox, -oy, 'edge'), 0.0)
                cnt += k
        gx, gy = sx / cnt, sy / cnt
    n = np.sqrt(gx * gx + gy * gy + 1)
    return np.where(fg, -gx / n, 0.0), np.where(fg, -gy / n, 0.0), np.where(fg, 1 / n, 1.0)
