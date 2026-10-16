"""Block layouts: integer id maps that say which stone, slab or voussoir every pixel belongs to.

A layout is only geometry. texture.shade_cells turns it into carved stone (lit rims, seams,
chips, wear), pillow lumps or rounded slabs. Every layout is a pure function of its arguments
and seed, so a ring can be rotated one block per step and re-rasterised with the light still
on the upper left of every block (something a hand-painted sheet cannot do).

    import layout, texture as tx
    ids = layout.ashlar(60, 96, 140, 140, h=9, w=(10, 16), seed=2, frame=c)     # coursed wall
    ring = layout.polar_blocks(100, 92, [(40, 52), (52, 66)], block_len=12, a0=math.pi, a1=2 * math.pi, frame=c)
    lumps = layout.cells(wall_mask, size=(9, 7), seed=3)                         # cave wall (10)
    slabs = layout.round_corners(layout.ashlar(0, 0, 160, 180, h=(10, 18), w=(14, 30), mask=cliff), 2.5)  # (04)
    ids = layout.combine(ring, ids)                                              # later ones on top
    tx.shade_cells(c, ids, 'stone', profile='rim', struct=True)

Id map convention (int32, H x W): -1 = not part of the layout (left untouched), 0 = seam or
mortar (1 px, always on the upper/left block's side so it is 4-connected), > 0 = a block. A
block id carries its group in the high bits (group(ids)): polar bands and ashlar walls get their
own group, and shade_cells(struct=True) draws the 2 px structural break of Owlboy (08) where
two groups meet. Sizes are native px. frame is a Canvas or (W, H); without it the map spans
(0, 0) .. the layout's far corner.

Learns from: 08 Owlboy (polar rings of voussoirs, ashlar of ~10x9 px blocks, seam hierarchy),
10 Stardew Valley (staggered power-diagram lumps 9x7), 04 Sea of Stars (big slabs 14-30 x
10-20 px with rounded corners: ashlar or cells + round_corners), 09 Katana ZERO (stack bond).
"""
import math
import numpy as np

GROUP = 1 << 20                  # ids = group * GROUP + block

def _hash(a, b, s=0):
    h = (np.asarray(a).astype(np.int64) * 374761393 + np.asarray(b).astype(np.int64) * 668265263
         + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _frame(frame, w, h):
    if frame is None:
        return int(math.ceil(w)), int(math.ceil(h))
    if hasattr(frame, 'W'):
        return frame.W, frame.H
    return int(frame[0]), int(frame[1])

def group(ids):
    """the group number of every pixel (-1 on seams and outside)"""
    ids = np.asarray(ids)
    return np.where(ids > 0, ids // GROUP, -1)

def finish(raw, group=0):
    """raw keys (int64, < 0 outside) -> a layout id map: block = group * GROUP + 1 + key (keys
    of GROUP - 1 or more are renumbered 1..n), and
    a 1 px seam (0) on every pixel whose right or lower neighbour is another block. The seam
    lands on the upper/left block, so it stays 4-connected and each block keeps a clean edge."""
    raw = np.asarray(raw, np.int64)
    inside = raw >= 0
    r = np.roll(raw, -1, 1); r[:, -1] = -1
    d = np.roll(raw, -1, 0); d[-1, :] = -1
    seam = inside & (((r >= 0) & (r != raw)) | ((d >= 0) & (d != raw)))
    out = np.full(raw.shape, -1, np.int32)
    keys = raw[inside & ~seam]
    if keys.size and keys.max() < GROUP - 1:
        # small keys are kept as they are, so a block keeps its id (and its hashed tone, chips
        # and wear) while the layout moves or the mask cuts other blocks away
        out[inside & ~seam] = (group * GROUP + 1 + keys).astype(np.int32)
    elif keys.size:
        u, inv = np.unique(keys, return_inverse=True)
        out[inside & ~seam] = (group * GROUP + 1 + inv).astype(np.int32)
    out[seam] = 0
    return out

def combine(*maps):
    """stack layouts (later ones win where they are >= 0); groups are renumbered so every map
    keeps its own, and a 1 px seam is cut where two maps meet (structural with struct=True). Maps of different sizes are
    aligned at (0, 0) and padded with -1."""
    H = max(m.shape[0] for m in maps)
    W = max(m.shape[1] for m in maps)
    out = np.full((H, W), -1, np.int32)
    gnext = 0
    for m in maps:
        m = np.asarray(m)
        p = np.full((H, W), -1, np.int64)
        p[:m.shape[0], :m.shape[1]] = m
        g = np.where(p > 0, p // GROUP, -1)
        gs = np.unique(g[g >= 0])
        remap = {int(v): gnext + i for i, v in enumerate(gs)}
        gnext += len(gs)
        newp = p.copy()
        for old, new in remap.items():
            sel = g == old
            newp[sel] = new * GROUP + p[sel] % GROUP
        out = np.where(p >= 0, newp, out).astype(np.int32)
    return finish_bands(out)

def _runs(n_lo, n_hi, x0, x1, start, k_seed, seed, prev=None, gap=3):
    """block edges across [x0, x1): widths in [n_lo, n_hi], first edge at x0 - start; an edge
    that lands within `gap` px of an edge of the course above is pushed on (no stacked joints)"""
    xs = [x0 - start]
    k = 0
    while xs[-1] < x1:
        w = n_lo + int(_hash(k, k_seed, seed) * (n_hi - n_lo + 1))
        nx = xs[-1] + w
        if prev is not None and len(prev):
            near = np.abs(np.asarray(prev) - nx)
            j = int(np.argmin(near))
            if near[j] < gap and x0 < nx < x1:
                nx = prev[j] + gap if nx >= prev[j] else prev[j] - gap
                if nx - xs[-1] < max(3, n_lo - gap):
                    nx = prev[j] + gap
        xs.append(nx)
        k += 1
    return xs

def ashlar(x0, y0, x1, y1, h=9, w=(10, 16), seed=0, bond='running', wobble=1, lean=0.35,
           frame=None, mask=None, group=0):
    """coursed blocks in [x0, x1) x [y0, y1): courses h px tall (an int, or a (lo, hi) range per
    course), block widths drawn from w=(lo, hi). bond 'running' keeps joints of neighbouring
    courses at least 3 px apart, 'stack' puts every joint on one grid (Katana slab course, set
    w=(16, 16)), 'random' lets them fall where they fall. wobble moves each bed joint up or down
    by up to that many px in runs of 4-9 px; lean tilts a share of the head joints by 1 px, so
    blocks read as cut by hand (08). mask clips the result."""
    W, H = _frame(frame, x1, y1)
    yy, xx = np.mgrid[0:H, 0:W]
    raw = np.full((H, W), -1, np.int64)
    hs = []                                          # course tops
    y, r = y0, 0
    while y < y1:
        hh = h if np.isscalar(h) else h[0] + int(_hash(r, 3, seed) * (h[1] - h[0] + 1))
        hs.append((y, hh))
        y += hh
        r += 1
    hs.append((y, 0))
    tops = np.array([t for t, _ in hs])
    # wobbled bed joints: boundary k at tops[k] + wob_k(x)
    def wob(k, x):
        if not wobble:
            return np.zeros_like(x)
        run = (x - x0 + (_hash(k, 1, seed + 5) * 9).astype(np.int64)) // 6
        v = _hash(run, k, seed + 6)
        return np.where(v < 0.2, -wobble, np.where(v > 0.8, wobble, 0))
    sub = (yy >= y0) & (yy < y1) & (xx >= x0) & (xx < x1)
    rr = np.clip(np.searchsorted(tops, yy, side='right') - 1, 0, len(tops) - 2)
    if wobble:
        top_w = tops[rr] + wob(rr, xx)
        bot_w = tops[rr + 1] + wob(rr + 1, xx)
        rr = np.where((yy < top_w) & (rr > 0), rr - 1, np.where((yy >= bot_w) & (rr < len(tops) - 2), rr + 1, rr))
    wlo, whi = (w, w) if np.isscalar(w) else w
    prev = None
    for k in range(len(tops) - 1):
        if bond == 'stack':
            start = 0
        elif bond == 'running':
            start = int(_hash(k, 2, seed) * whi) if prev is None else int(_hash(k, 2, seed) * wlo)
        else:
            start = int(_hash(k, 2, seed) * whi)
        xs = _runs(wlo, whi, x0, x1, start, k, seed, prev if bond == 'running' else None)
        if bond == 'stack':
            xs = list(range(x0, x1 + wlo, wlo))
        prev = xs
        e = np.asarray(xs)
        sel = sub & (rr == k)
        if not sel.any():
            continue
        px, py = xx[sel], yy[sel]
        kk = np.clip(np.searchsorted(e, px, side='right') - 1, 0, len(e) - 2)
        if lean:
            # a leaning joint is 1 px further right in the lower half of the course
            t0, hh = tops[k], max(1, tops[k + 1] - tops[k])
            lo_half = (py - t0) >= hh / 2
            for side in (0, 1):
                j = kk + side
                tilt = (_hash(j, k, seed + 9) < lean) & lo_half
                ej = e[np.clip(j, 0, len(e) - 1)] + tilt
                if side == 0:
                    kk = np.where(px < ej, kk - 1, kk)
                else:
                    kk = np.where(px >= ej, kk + 1, kk)
        raw[sel] = k * 4096 + (kk + 8)
    if mask is not None:
        raw[~np.asarray(mask, bool)] = -1
    return finish(raw, group)

def polar_blocks(cx, cy, bands, block_len=12, jitter=0.5, rot=0.0, a0=None, a1=None, seed=0,
                 frame=None, mask=None, group=0, offset=0.5):
    """concentric rings of voussoirs around (cx, cy): bands is a list of (r0, r1) radii (or
    (r0, r1, block_len)). Each band is split into blocks of about block_len px of arc, their
    widths jittered by +-jitter/2 (08: 12 px, +-50%), odd bands offset by `offset` of a block.
    rot (radians) turns the whole pattern: re-rasterising each step keeps the light right.
    a0..a1 (radians, y down, 0 = east, pi/2 = south) keeps an arc only; None keeps the full
    ring. Each band is its own group, so the breaks between rings can be structural."""
    rmax = max(b[1] for b in bands)
    rot = rot % (2 * math.pi)                         # a whole turn is exactly no turn (loops)
    W, H = _frame(frame, cx + rmax + 1, cy + rmax + 1)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    r = np.hypot(xx - cx, yy - cy)
    a = np.arctan2(yy - cy, xx - cx)
    out = np.full((H, W), -1, np.int32)
    for bi, b in enumerate(bands):
        r0, r1 = b[0], b[1]
        bl = b[2] if len(b) > 2 else block_len
        rm = (r0 + r1) / 2.0
        n = max(3, int(round(2 * math.pi * rm / bl)))
        wts = 1 + jitter * (_hash(bi, np.arange(n), seed + 1) - 0.5)
        edges = np.concatenate([[0], np.cumsum(wts)])
        edges = edges / edges[-1] * 2 * math.pi
        off = (offset if bi % 2 else 0) * 2 * math.pi / n + rot
        m = (r >= r0) & (r < r1)
        if a0 is not None and a1 is not None:
            span = (a1 - a0) % (2 * math.pi) or 2 * math.pi
            m &= ((a - a0) % (2 * math.pi)) <= span
        if mask is not None:
            m &= np.asarray(mask, bool)[:H, :W]
        k = np.searchsorted(edges, (a - off) % (2 * math.pi), side='right') - 1
        raw = np.where(m, k % n, -1)
        f = finish(raw, group + bi)
        out = np.where(f >= 0, f, out)
    return finish_bands(out)

def finish_bands(ids):
    """re-seam a map whose parts were finished apart, so a 1 px seam (0) separates them too"""
    g = np.where(ids > 0, ids // GROUP, -1)
    rg = np.roll(g, -1, 1); rg[:, -1] = -1
    dg = np.roll(g, -1, 0); dg[-1, :] = -1
    seam = (ids > 0) & (((rg >= 0) & (rg != g)) | ((dg >= 0) & (dg != g)))
    out = ids.copy()
    out[seam] = 0
    return out

def cells(mask, size=(9, 7), stagger=0.5, jitter=(0.7, 0.6), size_var=0.35, seam=0.55, round=0.0,
          seed=0, origin=(0, 0), group=0):
    """rounded lumps filling a bool mask: sites on a staggered grid of pitch `size`, jittered
    by jitter * size, each with a power-diagram weight +-size_var (big and small stones side by
    side, 10). seam is the half width in px of the gap (0.55 gives a 1 px seam). round > 0 rounds
    every corner with that radius (round_corners). origin shifts the lattice (for a lattice that
    must stay put while the mask changes)."""
    m = np.asarray(mask, bool)
    H0, W0 = m.shape
    rows, cols = np.flatnonzero(m.any(1)), np.flatnonzero(m.any(0))
    if not rows.size:
        return np.full((H0, W0), -1, np.int32)
    by, bx = rows[0], cols[0]                        # only the mask's box is computed
    m = m[by:rows[-1] + 1, bx:cols[-1] + 1]
    H, W = m.shape
    sx, sy = float(size[0]), float(size[1])
    jx, jy = (jitter, jitter) if np.isscalar(jitter) else jitter
    yy, xx = np.mgrid[by:by + H, bx:bx + W] + 0.5
    xx = xx - origin[0]
    yy = yy - origin[1]
    gy = np.floor(yy / sy).astype(np.int64)
    INF = 1e9
    d1 = np.full((H, W), INF); d2 = d1.copy()
    k1 = np.zeros((H, W), np.int64)
    for oy in (-1, 0, 1):
        Y = gy + oy
        st = stagger * (Y % 2)
        gx = np.floor(xx / sx - st).astype(np.int64)
        for ox in (-2, -1, 0, 1, 2):
            X = gx + ox
            px = (X + st + 0.5 + jx * (_hash(X, Y, seed) - 0.5)) * sx
            py = (Y + 0.5 + jy * (_hash(X, Y, seed + 1) - 0.5)) * sy
            wgt = size_var * (2 * _hash(X, Y, seed + 2) - 1)
            d = np.hypot((xx - px) / sx, (yy - py) / sy) - wgt
            key = (X + 100000) * 200003 + (Y + 100000)
            c1 = d < d1
            d2 = np.where(c1, d1, np.minimum(d2, d))
            d1 = np.where(c1, d, d1)
            k1 = np.where(c1, key, k1)
    unit = min(sx, sy) / 2.0
    e = (d2 - d1) * unit                              # px to the nearest bisector
    raw = np.full((H0, W0), -1, np.int64)
    raw[by:by + H, bx:bx + W] = np.where(m, np.where(e < seam, -2, k1), -1)
    out = finish(np.where(raw == -2, -1, raw), group)  # 1 px seams only where blocks still touch
    out[raw == -2] = 0
    return round_corners(out, round) if round > 0 else out

def round_corners(ids, r=2.5):
    """round every block's corners with radius r px: block pixels outside the block's opening
    by a disc of radius r become seam (0), so seams open into small pockets where blocks meet
    (04 slabs, 10 lumps). Thin blocks (under 2r across) keep their pixels."""
    import morph
    ids = np.asarray(ids)
    blk = ids > 0
    d = morph.cell_distance(np.where(blk, ids, 0), 'euclid', bg=0)
    core = blk & (d > r)
    near = morph.distance_outside(core, "euclid", max=r + 2) <= r
    # blocks with no core at all (too thin) stay as they are
    keep = near | ~np.isin(ids, np.unique(ids[core]))
    out = ids.copy()
    out[blk & ~keep] = 0
    return out

def grid(x0, y0, x1, y1, cell=(16, 16), phase=(0, 0), frame=None, mask=None, group=0):
    """a regular grid of cells (paver courses, tile seams every 16 px)"""
    W, H = _frame(frame, x1, y1)
    yy, xx = np.mgrid[0:H, 0:W]
    sub = (yy >= y0) & (yy < y1) & (xx >= x0) & (xx < x1)
    if mask is not None:
        sub &= np.asarray(mask, bool)
    raw = ((xx - x0 + phase[0]) // cell[0]) * 4096 + (yy - y0 + phase[1]) // cell[1] + 8
    return finish(np.where(sub, raw, -1), group)
