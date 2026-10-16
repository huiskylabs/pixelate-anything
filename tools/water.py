"""Water kit: hard-edged depth bands from the shore, dashed foam rings round everything that
stands in the water, tiered pools, banded waterfalls with lip, bulging edges, splash and
droplets, and reflections (Sea of Stars, 04; Owlboy, 08; Hyper Light Drifter, 03).

    import water
    water.depth_bands(c, sea, land, 'sea', cuts=(5, 14, 30), seed=1)       # 04: no dither
    water.foam_rings(c, land, sea, t=t, T=T)                               # 04: front half, dashed
    water.pool(c, basin, 'pool', rim='foam2', t=t, T=T)                     # 04: rim, lip band, sparkle
    water.waterfall(c, 120, 40, 90, w=8, ramp='pool', t=t, T=T)             # 04/08: streaks, splash
    water.reflect(c, 140, 0, 320, 180, shift=-2, t=t, T=T)                  # mirrored, dimmed, rippled

Ramps are BASE0 (darkest) .. BASEn; pass steps= so tones clamp. Animated helpers take (t, T)
and every period they use divides T (pass T; periods that do not divide it are rounded to a
divisor), so frame T is frame 0. All shapes come from integer hashes of (x, y, seed).
Measured (04): bands meet along stepped 1-4 px stairs; foam is 1 px, 3-7 px dashes with 1-2 px
gaps, front half of the contour only, a fainter ring 3-5 px out at 40-50% cover, a 2-4 px
darker AO band; falls 8-9 px wide with constant column tones and a 1 px highlight edge.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph
from shapes import _h, _hs, _grid, vnoise2, split

def _divisor(p, T):
    """the divisor of T nearest to p (p itself when T is None)"""
    if not T:
        return max(1, int(p))
    ds = [d for d in range(1, int(T) + 1) if T % d == 0]
    return min(ds, key=lambda d: (abs(d - p), d))

def _shift_slots(g, m, k, steps=None):
    """move the ramp slots under m by k steps (clamped)"""
    vals = set(g[m].ravel()) - {None}
    for v in vals:
        b, i = split(v)
        if i is None:
            continue
        j = max(0, i + k)
        if steps:
            j = min(steps - 1, j)
        g[m & (g == v)] = '%s%d' % (b, j)

# ---------------------------------------------------------------- depth bands (04)
def depth_bands(c, water, land, ramp='sea', cuts=(5, 14, 30), wobble=3, cell=16, top=None, seed=0, shore=None,
                floating=None):
    """the sea in hard bands by distance from land (no dither): D = d(shore) + wobble * n(x, y),
    n a 2D value noise of `cell` px; the shallowest band is step `top` (default len(cuts)), one
    step darker past each cut. Returns the integer step map (-1 off the water).
    shore: the mask the bands measure from (default `land`). Pass the banks and piers only, or
    floating (a mask of boats, fenders, buoys, ducks: things that float) to take them out of land,
    so floating things do not make shallow blob islands in a canal; they still sit on water
    and foam_rings can still ring them."""
    g = _grid(c)
    H, W = g.shape
    water = np.asarray(water, bool)
    land = np.asarray(land if shore is None else shore, bool)
    if floating is not None:
        land = land & ~np.asarray(floating, bool)
    d = morph.distance_outside(land, 'euclid') if land.any() else np.full((H, W), 1e9)
    D = d + wobble * vnoise2((H, W), cell, seed)
    if top is None:
        top = len(cuts)
    stp = top - np.sum(D[..., None] >= np.asarray(cuts, float)[None, None, :], axis=-1)
    stp = np.where(water, stp, -1)
    for v in np.unique(stp[water]):
        g[water & (stp == v)] = '%s%d' % (ramp, max(0, v))
    return stp

# ---------------------------------------------------------------- foam rings (04)
def foam_rings(c, land, water, rings=((1, 'foam1', 0.85), (4, 'foam0', 0.45)), dash=(3, 7), gap=(1, 2),
               front_only=True, ao=('sea', 3), steps=None, t=0, T=None, pulse=(3, 5, 8), sway=1, seed=0):
    """dashed foam lines where things stand in water (04). rings = ((r, slot, cover), ...): the
    pixels of water exactly r px (chessboard) from land, cut into dashes of dash=(3, 7) px with
    gap=(1, 2) px gaps walked round each object by angle; `cover` of the dashes are kept.
    front_only keeps the half of each ring that faces the viewer (outward normal ny > -0.3).
    ao=(ramp, px): water of that ramp within px of land (and not foam) goes one step darker (two
    within 2 px); with front_only it is measured from the land dropped 2 px, a crescent that is
    deepest at the front and gone at the back (no dark halo over the back of a rock). Animation (t, T): a ring whose r is None pulses outward,
    r = pulse[0] + (t // pulse[2]) % (pulse[1] - pulse[0] + 1) (the cycle snapped to a divisor
    of T); the dashes slide +-sway px on a sine of period T.
    Returns the foam mask."""
    g = _grid(c)
    H, W = g.shape
    land = np.asarray(land, bool)
    water = np.asarray(water, bool)
    nx, ny = morph.normals(land, blur=2) if land.any() else (np.zeros((H, W)), np.zeros((H, W)))
    if ao:
        # front_only: measured from the land dropped 2 px, so the contact shadow is a crescent,
        # ao + 2 px deep at the front, thinner on the sides and gone at the back
        src = morph.shift(land, 0, 2) if front_only else land
        dl = morph.distance_outside(src, 'chessboard', max=ao[1] + 1)
        near = water & ~land & (dl <= ao[1] - (1 if front_only else 0)) & ((dl > 0) | front_only)
        ramp_m = np.zeros((H, W), bool)
        for v in set(g[near].ravel()) - {None}:
            if split(v)[0] == ao[0]:
                ramp_m |= g == v
        _shift_slots(g, near & ramp_m & (dl > 2), -1, steps)
        _shift_slots(g, near & ramp_m & (dl <= 2), -2, steps)
    ids, n = morph.label(land, 8)
    if n == 0:
        return np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W]
    cnt = np.bincount(ids.ravel(), minlength=n + 1).astype(float)
    cx_ = np.bincount(ids.ravel(), xx.ravel(), n + 1) / np.maximum(cnt, 1)
    cy_ = np.bincount(ids.ravel(), yy.ravel(), n + 1) / np.maximum(cnt, 1)
    near_y, near_x = morph.nearest(land)
    owner = ids[near_y, near_x]
    dist = morph.distance_outside(land, 'chessboard', max=16)
    TT = T or 1
    slide = int(round(sway * math.sin(2 * math.pi * (int(t) % TT) / TT))) if T else 0
    foam = np.zeros((H, W), bool)
    for ri, (r, slot, cover) in enumerate(rings):
        if r is None:                    # pulse: per radii, each held pulse[2] frames
            per = pulse[1] - pulse[0] + 1
            if T:
                cyc = _divisor(per * pulse[2], T)
                r = pulse[0] + ((int(t) % T) * per // cyc) % per
            else:
                r = pulse[0] + (int(t) // pulse[2]) % per
        ring = water & (dist == r)
        if front_only:
            ring &= ny > -0.3
        ys, xs = np.nonzero(ring)
        if not len(ys):
            continue
        ob = owner[ys, xs]
        ang = np.arctan2(ys + 0.5 - cy_[ob], xs + 0.5 - cx_[ob])
        order = np.lexsort((ang, ob))
        ys, xs, ob = ys[order], xs[order], ob[order]
        # rank within each object along the angle
        start = np.r_[0, np.nonzero(np.diff(ob))[0] + 1]
        rank = np.arange(len(ob)) - np.repeat(start, np.diff(np.r_[start, len(ob)]))
        keep = np.zeros(len(ob), bool)
        for o in np.unique(ob):
            sel = ob == o
            m = int(sel.sum())
            pat = np.zeros(m + 32, bool)
            pos, k = 0, 0
            while pos < m + 32:
                on = dash[0] + int((dash[1] - dash[0] + 1) * _hs(o, 2 * k, seed + 31 * ri))
                off = gap[0] + int((gap[1] - gap[0] + 1) * _hs(o, 2 * k + 1, seed + 31 * ri))
                if _hs(o, k, seed + 31 * ri + 7) < cover:
                    pat[pos:pos + on] = True
                pos += on + off
                k += 1
            keep[sel] = pat[(rank[sel] + slide + 16) % (m + 32)]
        g[ys[keep], xs[keep]] = slot
        foam[ys[keep], xs[keep]] = True
    return foam

# ---------------------------------------------------------------- pools (04)
def pool(c, mask, ramp='pool', rim='foam2', lip_rows=3, surface=4, steps=8, sparkle=(5, 4), t=0, T=None,
         hold=4, seed=0):
    """a basin of still water (04): filled with ramp step `surface`; the far (top) edge gets a 1 px
    `rim`, the band of lip_rows under it the step surface + 2 (light spills over the lip), a
    jittered sparkle grid of pitch sparkle=(5, 4) (odd rows offset) puts surface + 2 / + 1 dots
    and darker surface - 1 dots between them; each dot toggles on a 3-phase cycle every `hold`
    frames ((t // hold + phase) % 3; with T the 3-phase cycle is snapped to a divisor of T, so
    the loop is exact)."""
    g = _grid(c)
    H, W = g.shape
    mask = np.asarray(mask, bool)
    top = steps - 1
    nm = lambda v: '%s%d' % (ramp, max(0, min(top, v)))
    g[mask] = nm(surface)
    up = morph.edges(mask, 'up')
    lip = np.zeros((H, W), bool)
    for k in range(1, lip_rows + 1):
        lip |= morph.shift(up, 0, k)
    lip &= mask & ~up
    g[lip] = nm(surface + 2)
    if rim:
        g[up] = rim
    if sparkle:
        px, py = sparkle
        if t is None:
            ph = 0
        elif T:                          # 3 phases over a cycle that divides T
            cyc = _divisor(3 * hold, T)
            ph = (int(t) % T) * 3 // cyc
        else:
            ph = int(t) // hold
        ys, xs = np.nonzero(mask & ~up & ~lip)
        gy = ys // py
        off = np.where(gy & 1, px // 2, 0)
        gx = (xs - off) // px
        jx = (_h(gx, gy, seed) * 3).astype(int) - 1
        jy = (_h(gx, gy, seed + 1) * 3).astype(int) - 1
        cx_ = gx * px + off + px // 2 + jx
        cyy = gy * py + py // 2 + jy
        at = (xs == cx_) & (ys == cyy)
        phase = (_h(gx, gy, seed + 2) * 3).astype(int)
        vis = ((ph + phase) % 3) != 0
        hi = _h(gx, gy, seed + 3) < 0.5
        s1 = at & vis
        g[ys[s1 & hi], xs[s1 & hi]] = nm(surface + 2)
        g[ys[s1 & ~hi], xs[s1 & ~hi]] = nm(surface + 1)
        # dark dots on the same grid offset by half a cell, half as many
        at2 = (xs == cx_ + px // 2) & (ys == cyy + py // 2) & (_h(gx, gy, seed + 4) < 0.5)
        g[ys[at2], xs[at2]] = nm(surface - 1)

# ---------------------------------------------------------------- waterfalls (04, 08)
def waterfall(c, x0, y0, y1, w=8, ramp='pool', cols=None, hi_edge='left', foam=('foam1', 'foam2'), steps=8,
              t=0, T=None, speed=1, periods=(6, 8, 12, 16), bulge=True, lip=True, splash=True, drops=8,
              crown=False, seed=0):
    """a fall w px wide from y0 to y1 (04 banded, 08 streaked). Columns keep constant tones
    (cols, default [2, 3, 4, 5, 5, 6, 6, 5] cut to w) with the `hi_edge` column at the top step
    (the 1 px highlight). Streaks fall at `speed` px per frame: each column has a period P_c
    picked by hash from `periods` (snapped to divisors of speed * T) and a pixel is one step
    lighter where q = (y - speed t + phase_c) mod P_c < 2 and, in 60% of columns, one step darker
    for 0.35 P_c px from q = P_c / 2 (inner columns only). bulge: each 8 px
    segment of the moving water bulges an edge 1 px out (hash < 0.35; 8 is snapped to a divisor
    of speed * T). lip: foam rows across w + 2 at the top. splash: a foam crown at y1 that
    changes every 4 frames (w + 4 px wide, 5 rows), plus `drops` 1 px droplets on parabolas that
    leave and land on y1 over a 10-frame cycle (both snapped to divisors of T). crown=True (08, a
    pipe mouth; use lip=False): a splash crown about (w + 7) x 0.8 (w + 7) px over y0, a lit
    foam cap, a checker rim and `drops` droplets thrown around it, in 4 frames held 2 ticks each
    (an 8-frame cycle snapped to a divisor of T). Returns nothing."""
    g = _grid(c)
    H, W = g.shape
    top = steps - 1
    nm = lambda v: '%s%d' % (ramp, max(0, min(top, v)))
    if cols is None:
        cols = [2, 3, 4, 5, 5, 6, 6, 5, 4, 3][:w]
        if len(cols) < w:
            cols = cols + [5] * (w - len(cols))
    vT = speed * T if T else None
    tt = int(t)
    ys = np.arange(int(y0), int(y1))
    yv = ys[(ys >= 0) & (ys < H)]
    seg = _divisor(8, vT) if vT else 8
    for i in range(w):
        X = int(x0) + i
        if not (0 <= X < W):
            continue
        edge = (i == 0 and hi_edge == 'left') or (i == w - 1 and hi_edge == 'right')
        base = top if edge else cols[i]
        col = np.full(len(yv), base)
        if not edge and 0 < i < w - 1:
            P = _divisor(periods[int(_hs(i, 1, seed) * len(periods))], vT) if vT else periods[int(_hs(i, 1, seed) * len(periods))]
            ph = int(_hs(i, 2, seed) * P)
            q = (yv - speed * tt + ph) % P
            col = np.where(q < 2, base + 1, col)                    # a light glint
            if _hs(i, 3, seed) < 0.6:                                # a darker streak (08)
                col = np.where((q >= P // 2) & (q < P // 2 + max(2, int(0.35 * P))), base - 1, col)
        g[yv, X] = np.array([nm(v) for v in col], object)
    if bulge:
        for side, X in ((0, int(x0) - 1), (1, int(x0) + w)):
            if not (0 <= X < W):
                continue
            u = (yv - speed * tt) // seg
            if vT:
                u = u % (vT // seg)                         # the segment pattern loops with T
            on = (_h(u, side, seed + 5) < 0.35) & (((yv - speed * tt) % seg) < 3)
            g[yv[on], X] = nm(cols[0] if side == 0 else cols[w - 1])
    if lip:
        for r in range(3):
            Y = int(y0) + r - 1
            if 0 <= Y < H:
                for X in range(int(x0) - 1, int(x0) + w + 1):
                    if 0 <= X < W and (r < 2 or _hs(X, r, seed + 6) < 0.5):
                        g[Y, X] = foam[1] if r == 0 else foam[0]
    if crown:                      # the splash crown at a pipe mouth (08): 4 frames, 2 ticks each
        if T:
            cyc = _divisor(8, T)
            f = ((tt % T) * 4 // cyc) % 4
        else:
            f = (tt // 2) % 4
        cxr = x0 + w / 2.0
        rx = (w + 7) / 2.0 + (0, 1, 1, 0)[f]
        ry = 0.8 * rx - (0, 0, 1, 1)[f]
        cyr = y0 + 0.25 * ry
        ya, yb = int(math.floor(cyr - ry - 1)), int(math.ceil(cyr + ry + 1))
        xa, xb = int(math.floor(cxr - rx - 1)), int(math.ceil(cxr + rx + 1))
        for Y in range(max(0, ya), min(H, yb + 1)):
            for X in range(max(0, xa), min(W, xb + 1)):
                u, v = (X + 0.5 - cxr) / rx, (Y + 0.5 - cyr) / ry
                q = u * u + v * v
                if q > 1:
                    continue
                if q > 0.62:                                 # the rim: a checker into the water
                    if (X + Y + f) & 1:
                        g[Y, X] = foam[0] if v < 0 else nm(cols[min(w - 1, 2)] + 2)
                elif v < -0.45 - 0.25 * u:                   # the lit cap, upper left
                    g[Y, X] = foam[1]
                elif v < -0.1 - 0.2 * u:
                    g[Y, X] = foam[0]
                else:                                        # the body takes the water's tones
                    g[Y, X] = nm(top - 1 if u < 0.3 else top - 2)
        for i in range(drops):                               # droplets thrown up to 8 px around it
            a = 2 * math.pi * _hs(i, f, seed + 9)
            rr = 1.1 + 0.6 * _hs(i, f + 4, seed + 9)
            X = int(math.floor(cxr + rr * rx * math.cos(a)))
            Y = int(math.floor(cyr + rr * ry * math.sin(a) * 0.9))
            if 0 <= X < W and 0 <= Y < H and _hs(i, f + 8, seed + 9) < 0.6:
                g[Y, X] = foam[0]
    if splash:
        h4 = _divisor(4, T) if T else 4
        k = (tt // h4) % (T // h4) if T else tt // h4
        for r in range(-1, 4):
            Y = int(y1) + r
            if not (0 <= Y < H):
                continue
            for X in range(int(x0) - 2, int(x0) + w + 2):
                if 0 <= X < W:
                    p = 0.7 - 0.13 * (r + 1) - 0.1 * (X < int(x0) or X >= int(x0) + w)
                    if _hs(X * 131 + Y, k, seed + 7) < p:
                        g[Y, X] = foam[1] if r <= 0 else foam[0]
        cyc = _divisor(10, T) if T else 10
        for i in range(drops):
            ph = int(_hs(i, 1, seed + 8) * cyc)
            tau = (tt + ph) % cyc
            vx = (2 * _hs(i, 2, seed + 8) - 1) * (0.5 + 0.5 * w / 8) * 10.0 / cyc
            vy = (1.0 + 1.2 * _hs(i, 3, seed + 8)) * 10.0 / cyc
            X = int(math.floor(x0 + w / 2 + vx * tau))
            Y = int(math.floor(y1 - vy * tau + (vy / cyc) * tau * tau))   # back at y1 after cyc
            if 0 <= X < W and 0 <= Y < H:
                g[Y, X] = foam[1]
                if tau < 3 and Y + 1 < H:
                    g[Y + 1, X] = foam[0]

# ---------------------------------------------------------------- reflections (08, 04)
def reflect(c, y_axis, x0=0, x1=None, y1=None, src=None, shift=-2, steps=None, remap=None, gaps=3,
            ripple=1, base=None, only=None, t=0, T=None, hold=2, seed=0):
    """mirror the scene above the waterline into the water below it: row y_axis + k shows row
    y_axis - 1 - k, shifted along its ramp by `shift` steps (or through remap, a dict or a
    function slot -> slot), each row nudged by up to +-ripple px (a hashed per-row wave that
    moves every `hold` frames and loops over T), and every `gaps`-th row (counted from the axis,
    drifting 1 row per hold) left as the water `base` slot so the reflection reads as streaks.
    only: slot prefixes (a tuple) that reflect; anything else (the sky) shows as `base`.
    Paints [x0, x1) x [y_axis, y1); src (a grid) is read instead of c when given."""
    g = _grid(c)
    H, W = g.shape
    x1 = W if x1 is None else min(W, int(x1))
    y1 = H if y1 is None else min(H, int(y1))
    y_axis, x0 = int(y_axis), max(0, int(x0))
    S = g.copy() if src is None else np.asarray(src, object)
    if remap is None:
        def remap(v):
            b, i = split(v)
            if i is None:
                return v
            j = max(0, i + shift)
            return '%s%d' % (b, min(steps - 1, j) if steps else j)
    elif isinstance(remap, dict):
        dct = remap
        remap = lambda v: dct.get(v, v)
    TT = T or 1
    ph = (int(t) // hold) if T is None else (int(t) // hold) % max(1, TT // hold)
    nph = max(1, TT // hold) if T else 1 << 30
    cache = {}
    xs = np.arange(x0, x1)
    for k in range(0, y1 - y_axis):
        Y, Ys = y_axis + k, y_axis - 1 - k
        if Ys < 0 or Y >= H:
            break
        gap_row = bool(gaps) and base is not None and (k + ph) % gaps == gaps - 1
        dx = 0
        if ripple:
            a = 2 * math.pi * (_hs(k, 1, seed) + ph / nph)
            dx = int(round(ripple * math.sin(a + k * 0.7)))
        row = S[Ys, np.clip(xs - dx, 0, W - 1)]
        out = np.empty(len(row), object)
        for i, v in enumerate(row):
            if v is None or gap_row or (only is not None and not str(v).startswith(tuple(only))):
                out[i] = base
            else:
                if v not in cache:
                    cache[v] = remap(v)
                out[i] = cache[v]
        keep = ~np.equal(out, None)
        g[Y, x0:x1][keep] = out[keep]
