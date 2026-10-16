"""Materials: shaped units placed by hand-tuned rules, never raw noise.

Three engines and a kit, all painting palette slots (BASE + step) into a canvas.Canvas:

  cells    layout.py gives an id map (which block each pixel is in); shade_cells carves it:
           'rim'     Owlboy stone (08): 1 px lit rim on the light-facing edges, a shadow fringe,
                     1 px seams, 2 px structural breaks, chipped corners, checker wear, cracks
           'pillow'  Stardew cave wall (10): rounded lumps, solid 3-4 tone clusters, plum seams
           'slab'    Sea of Stars cliffs (04): big rounded slabs, a lit top arc, dark lower rows
           'twoface' Sword & Sworcery / HLD blocks (01, 03): each block split into two faces
  scatter  deterministic dart throwing of small stamps with a minimum distance, light-aware,
           optionally twinkling in a loop; presets pebbles, pits, pocks, ticks, flecks,
           leaflight, flakes, mottle, jitter_dots, stipple_field
  kit      profile (moulding stacks), panels (ring tables), grille, inset_frame, emitter_grid,
           cap, wet_streaks, tapestry, circuit, segments, slats
  roofs    shingles (scallop / rect / shake courses, slipped and missing tiles, moss), thatch,
           planks (walls, floors, board-and-batten: grain ticks, knots, short and replaced boards)
  iso_face wraps any of them onto a 2:1 iso wall face (courses follow the slope)

    import layout, texture as tx
    ids = layout.ashlar(0, 96, 200, 140, h=9, w=(10, 16), seed=2, frame=c)
    tx.shade_cells(c, ids, 'stone', profile='rim', struct=True, seed=2)       # carved masonry (08)
    tx.shade_cells(c, layout.cells(wall, (9, 7), seed=3), 'rock', profile='pillow')   # cave (10)
    tx.pebbles(c, floor, 'dirt', base=3)                                      # pebble dirt (10)
    tx.ticks(c, lawn, 'grass3', [('grass4', 'grass2'), ('grass2', 'grass1')])   # grass (07)
    tx.pocks(c, chitin)                                                       # pit + lip (05)
    tx.leaflight(c, canopy, [(post.light_field(W, H, 120, 80, 60), ('leaf3', 'warm5'))], t=t, T=T)
    y = tx.profile(c, 0, 320, 40, [dict(h=3, ramp='wood', base=3, pattern='###-.-#-..-#-.--'),
                                    dict(h=7, ramp='stone', base=3, rows=[-1, 0, 0, 1, 1, 2, 3], shadow=6)])
    tx.panels(c, 0, y, 320, y + 48, 'wood', cell=(16, 16), base=3)          # Katana ZERO (09)
    tx.segments(c, belly, [(240, 100), (262, 170)], 14, 'bone', spacing=5)  # Metal Slug (05)

Steps: shade_cells, profile, panels and segments take body/base steps and offsets (+1 = one
step lighter); a scatter stamp tone is a slot name (absolute) or an int (an offset from the
slot already under it). steps= is the ramp length (7 for canvas.ramps). Light is a direction
toward the light, y down: (-0.45, -0.89) is above and a little left. Randomness comes only from
integer hashes of (x, y, seed); animated presets take t and T and every period divides T, so
frame T equals frame 0.
"""
import math
import numpy as np
from canvas import th, thresholds, _ramp_arrays
import morph
import layout as _layout

# ---------------------------------------------------------------- hashes and painting helpers
def _hash(x, y, s=0):
    h = (int(x) * 374761393 + int(y) * 668265263 + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _hash_arr(a, b, s=0):
    h = (np.asarray(a).astype(np.int64) * 374761393 + np.asarray(b).astype(np.int64) * 668265263
         + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _vnoise(xx, yy, cell, s=0):
    """smooth value noise in 0..1 on a lattice of `cell` px (hashed corners, smoothstep blend)"""
    gx, gy = xx / float(cell), yy / float(cell)
    ix, iy = np.floor(gx).astype(np.int64), np.floor(gy).astype(np.int64)
    fx, fy = gx - ix, gy - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    h = lambda i, j: _hash_arr(ix + i, iy + j, s)
    return (h(0, 0) * (1 - fx) + h(1, 0) * fx) * (1 - fy) + (h(0, 1) * (1 - fx) + h(1, 1) * fx) * fy

def _names(ramp, steps):
    return np.array(['%s%d' % (ramp, i) for i in range(steps)], object)

def _grid(c):
    H, W = c.H, c.W
    yy, xx = np.mgrid[0:H, 0:W]
    return xx, yy

def _mask(c, mask):
    if mask is None:
        return np.ones((c.H, c.W), bool)
    m = np.asarray(mask, bool)
    if m.shape != (c.H, c.W):
        out = np.zeros((c.H, c.W), bool)
        out[:min(c.H, m.shape[0]), :min(c.W, m.shape[1])] = m[:c.H, :c.W]
        return out
    return m

def _fit(ids, c):
    """an id map padded or cut to the canvas (-1 where it has nothing)"""
    ids = np.asarray(ids)
    if ids.shape == (c.H, c.W):
        return ids.astype(np.int64)
    out = np.full((c.H, c.W), -1, np.int64)
    h, w = min(c.H, ids.shape[0]), min(c.W, ids.shape[1])
    out[:h, :w] = ids[:h, :w]
    return out

def _unit(v):
    n = math.hypot(v[0], v[1]) or 1.0
    return v[0] / n, v[1] / n

def _loop_check(T, period, what='hold'):
    if T and period and T % period:
        raise ValueError('%s period %d does not divide T=%d: frame T would not equal frame 0'
                         % (what, period, T))

def _put(c, xs, ys, tones, steps=7, under=None):
    """paint stamp pixels: a str tone is a slot, an int an offset from the slot under the pixel
    (read from `under`, the grid before this call, so offsets never compound). Pixels whose
    underlying slot is not on a ramp are skipped for offsets. Later entries win."""
    xs = np.asarray(xs, np.int64); ys = np.asarray(ys, np.int64)
    if not xs.size:
        return
    ok = (xs >= 0) & (xs < c.W) & (ys >= 0) & (ys < c.H)
    xs, ys = xs[ok], ys[ok]
    tones = np.asarray(tones, object)[ok]
    isstr = np.array([isinstance(t, str) for t in tones], bool)
    if isstr.any():
        c.g[ys[isstr], xs[isstr]] = tones[isstr]
    if (~isstr).any():
        if under is None:
            under = _ramp_arrays(c.g)
        bases, st = under
        yi, xi = ys[~isstr], xs[~isstr]
        off = tones[~isstr].astype(np.int64)
        b = bases[yi, xi]; s0 = st[yi, xi]
        good = s0 >= 0
        ns = np.clip(s0 + off, 0, steps - 1)
        vals = np.array(['%s%d' % (bb, k) for bb, k in zip(b[good], ns[good])], object)
        c.g[yi[good], xi[good]] = vals

# ---------------------------------------------------------------- C2: cell stone engine
PROFILES = {
    # body: base step; rim/seam/shadow/struct: offsets from body; chip/wear/cracks: share of blocks
    'rim':     dict(body=4, rim=1, seam=-2, shadow=-1, struct=-3, chip=0.6, wear=0.55, cracks=0.35,
                    vary=0.3, dither='checker', pores=0.0, fringe=0.45),
    'pillow':  dict(body=3, rim=1, seam=-3, shadow=-1, struct=-3, chip=0.0, wear=0.0, cracks=0.0,
                    vary=0.35, dither='none', pores=0.0, fringe=0.0, hilite=0.86),
    'slab':    dict(body=4, rim=2, seam=-2, shadow=-1, struct=-3, chip=0.0, wear=0.0, cracks=0.12,
                    vary=0.45, dither='none', pores=0.015, fringe=0.0, heal=0.3),
    'twoface': dict(body=3, rim=2, seam=-2, shadow=0, struct=-3, chip=0.0, wear=0.0, cracks=0.0,
                    vary=0.0, dither='none', pores=0.0, fringe=0.0),
}

def _per_block(cid, n, xx, yy):
    """centroid, bbox and pixel count of every compact block index 1..n"""
    f = cid.ravel()
    cnt = np.bincount(f, minlength=n + 1).astype(float)
    cnt[0] = 1
    cx = np.bincount(f, (xx + 0.5).ravel(), n + 1) / cnt
    cy = np.bincount(f, (yy + 0.5).ravel(), n + 1) / cnt
    big = 1 << 30
    x0 = np.full(n + 1, big); x1 = np.full(n + 1, -big)
    y0 = np.full(n + 1, big); y1 = np.full(n + 1, -big)
    np.minimum.at(x0, f, xx.ravel()); np.maximum.at(x1, f, xx.ravel())
    np.minimum.at(y0, f, yy.ravel()); np.maximum.at(y1, f, yy.ravel())
    return cnt, cx, cy, x0, x1, y0, y1

def _pick(cid, ok, key, n):
    """per block the pixel (flat index) of `ok` with the smallest key, -1 where none"""
    idx = np.flatnonzero(ok.ravel() & (cid.ravel() > 0))
    out = np.full(n + 1, -1, np.int64)
    if not idx.size:
        return out
    b = cid.ravel()[idx]
    order = np.lexsort((key.ravel()[idx], b))
    b, idx = b[order], idx[order]
    first = np.ones(len(b), bool); first[1:] = b[1:] != b[:-1]
    out[b[first]] = idx[first]
    return out

def shade_cells(c, ids, ramp, light=(-0.45, -0.89), profile='rim', body=None, rim=None, seam=None,
                shadow=None, struct=None, chip=None, wear=None, cracks=None, vary=None, dither=None,
                pores=None, fringe=None, hilite=None, heal=None, ramp2=None, body2=None, split=(0.35, 0.65),
                split_axis='x', faces=None, lz=0.9, steps=7, mask=None, seed=0):
    """carve the blocks of a layout id map (layout.py: -1 untouched, 0 seam, > 0 blocks) in
    `ramp`. profile picks the look and its defaults (PROFILES); any argument overrides them:
      body     the body step (the profile defaults are for steps=7; on another ramp length the
               default body moves to the same place on it); vary is the share of blocks one
               step darker ('rim'), the +- spread of the per-block tone ('pillow'), the share
               a step off ('slab')
      rim      offset of the 1 px rim on edges that face the light (d in [1, 2), facing > 0.35);
               'rim' adds a checker fringe one px further in when dither='checker'
      seam     offset of the 1 px seams; shadow of the fringe on edges facing away
      struct   True (or an offset) draws the 2 px structural break where layout groups meet
               and along the form's outer edge on its shadow side (08 ring/body breaks)
      chip     share of block corners knocked to the seam tone; wear: share of blocks with a
               checker blob 4-9 px across (half polished, rim tone; half pitted, shadow tone);
               cracks: share with a 3-7 px diagonal crack and a lit pixel below. Wear and
               cracks are anchored to the block, so they move with a turning ring
      pores    share of interior pixels one step down (04)
      heal     share of the seam (in runs of a few px) drawn as a 1-step crease instead ('slab')
      hilite   'pillow': shade above this gets one more step, the lump's highlight cluster (10)
      fringe   'rim': share of blocks whose rim and shadow fringes run on through a 1 px
               checker (dither='checker'); the rest get crisp 1-2 px rims
      ramp2, body2, split, split_axis  'twoface': the face right of (or below, 'y'; across the
               diagonal, 'diag') a hashed split at 35-65% of the block uses ramp2 (01 cool sky
               face / warm stage face); faces, a bool mask, splits the whole form instead (08
               prisms: grey lit face and sandstone face either side of the ridge)
    light is the direction toward the light (y down); lz its height for 'pillow'. Returns the
    step grid (-1 where nothing was painted)."""
    if profile not in PROFILES:
        raise ValueError('profile %r: rim, pillow, slab or twoface' % (profile,))
    P = dict(PROFILES[profile])
    if body is None and steps != 7:                  # the defaults are for 7-step ramps: keep the
        P['body'] = int(round(P['body'] * (steps - 1) / 6.0))   # body at the same place on a shorter one
    for k, v in dict(body=body, rim=rim, seam=seam, shadow=shadow, chip=chip, wear=wear,
                     cracks=cracks, vary=vary, dither=dither, pores=pores, fringe=fringe,
                     hilite=hilite, heal=heal).items():
        if v is not None:
            P[k] = v
    if struct is True:
        struct = P['struct']
    ids = _fit(ids, c)
    m = _mask(c, mask)
    full = np.full((c.H, c.W), -1, np.int64)
    rows = np.flatnonzero(((ids >= 0) & m).any(1))
    if not rows.size:
        return full
    cols = np.flatnonzero(((ids >= 0) & m).any(0))
    # work on the layout's box (plus a margin) only: a small wall on a big canvas stays cheap;
    # hashes and the checker phase use canvas coordinates, so the result is the same
    oy, ox = max(0, rows[0] - 3), max(0, cols[0] - 3)
    ey, ex = min(c.H, rows[-1] + 4), min(c.W, cols[-1] + 4)
    ids, m = ids[oy:ey, ox:ex], m[oy:ey, ox:ex]
    G = c.g[oy:ey, ox:ex]                            # a view: painting it paints the canvas
    H, W = ids.shape
    blk = (ids > 0) & m
    sm = (ids == 0) & m
    yy, xx = np.mgrid[0:H, 0:W]
    AX, AY = xx + ox, yy + oy                        # canvas coordinates for hashes
    # compact block index 1..n
    u, inv = np.unique(np.where(blk, ids, 0), return_inverse=True)
    cid = inv.reshape(H, W).astype(np.int64)
    if u[0] != 0:
        cid += 1
        u = np.concatenate([[0], u])
    n = len(u) - 1
    bid = u                                          # original id per compact index
    hb = lambda k: _hash_arr(bid, k, seed + 31)      # per-block hash, indexed by cid
    d = morph.cell_distance(cid, bg=0)
    nx, ny = morph.cell_normals(cid, blur=1, bg=0)
    Lx, Ly = _unit(light)
    facing = nx * Lx + ny * Ly
    chk = ((AX + AY) & 1) == 0
    body_ = P['body']
    cnt, cx, cy, bx0, bx1, by0, by1 = _per_block(cid, n, xx, yy)
    st = np.full((H, W), -1, np.int64)
    face2 = np.zeros((H, W), bool)
    prof = profile
    if prof == 'rim':
        tone = body_ - (hb(1) < P['vary']).astype(np.int64)
        st = np.where(blk, tone[cid], -1)
        sh = body_ + P['shadow']
        away = facing < -0.3
        st = np.where(blk & (d < 3) & away, sh, st)
        lit = facing > 0.35
        soft = blk & (hb(3) < P['fringe'])[cid]       # blocks whose transitions go through a checker
        if P['dither'] == 'checker':
            st = np.where(soft & (d >= 2) & (d < 3) & away & chk, tone[cid], st)
            st = np.where(soft & (d >= 2) & (d < 3) & (facing > 0.6) & chk, body_ + P['rim'], st)
        st = np.where(blk & ~soft & (d >= 2) & (d < 3) & away & (hb(4) < 0.5)[cid], tone[cid], st)
        st = np.where(blk & (d < 2) & lit, body_ + P['rim'], st)
        wide = blk & ~soft & (hb(4) > 0.6)[cid] & (d >= 2) & (d < 3) & (facing > 0.7)
        st = np.where(wide, body_ + P['rim'], st)          # a 2 px rim on the top of some blocks
    elif prof == 'pillow':
        hx = np.maximum(1.0, (bx1 - bx0 + 1) / 2.0); hy = np.maximum(1.0, (by1 - by0 + 1) / 2.0)
        uu = (xx + 0.5 - cx[cid]) / hx[cid]
        vv = (yy + 0.5 - cy[cid]) / hy[cid]
        r = np.clip(np.hypot(uu, vv), 0, 1)
        nz = np.sqrt(1 - r * r)
        ln = math.sqrt(1 + lz * lz)
        shade = (uu * Lx + vv * Ly + nz * lz) / ln
        k = body_ + 1.5 * shade - 0.3 + P['vary'] * (2 * hb(1)[cid] - 1)
        k = np.where((d < 2) & (uu * Lx + vv * Ly < 0), k - 1.2, k)
        if P.get('hilite'):                          # the 2-3 px highlight cluster on the lit top (10)
            k = np.where((shade > P['hilite']) & (d >= 1.5), k + P['rim'], k)
        if P['dither'] == 'checker':
            k = k + (np.where(chk, 0.25, -0.25))
        st = np.where(blk, np.floor(k + 0.5).astype(np.int64), -1)
        st = np.where(blk, np.clip(st, max(1, body_ + P['seam'] + 1), steps - 1), -1)
    elif prof == 'slab':
        hv = hb(1)
        off = np.where(hv < P['vary'] / 2, -1, np.where(hv > 1 - P['vary'] / 2, 1, 0))
        tone = body_ + off
        st = np.where(blk, tone[cid], -1)
        rel_up = (xx + 0.5 - cx[cid]) * -0.5 + (yy + 0.5 - cy[cid]) * -1.0
        hgt = np.maximum(1, by1 - by0 + 1)[cid]
        low = (yy - by0[cid]) >= 0.7 * hgt
        st = np.where(blk & (d < 2.5) & low & (facing < -0.3), body_ + P['shadow'], st)   # 1-2 dark bottom rows
        st = np.where(blk & (d < 2) & (rel_up > 0) & (facing > -0.2), body_ + P['rim'], st)
    elif prof == 'twoface':
        f = split[0] + (split[1] - split[0]) * hb(2)
        if faces is not None:                         # one split for the whole form (08 prism ridge)
            face2 = blk & _mask(c, faces)[oy:ey, ox:ex]
        elif split_axis == 'x':
            face2 = blk & (xx >= (bx0 + f * (bx1 - bx0 + 1))[cid])
        elif split_axis == 'y':
            face2 = blk & (yy >= (by0 + f * (by1 - by0 + 1))[cid])
        else:
            a = (xx - bx0[cid]) / np.maximum(1, bx1 - bx0 + 1)[cid] - (yy - by0[cid]) / np.maximum(1, by1 - by0 + 1)[cid]
            face2 = blk & (a >= (2 * f - 1)[cid])
        b2 = body_ if body2 is None else body2
        st = np.where(blk, np.where(face2, b2, body_), -1)
        if P['dither'] == 'checker':                 # a 2 px checker along the ridge
            nb = morph.shift(face2, 1, 0) | morph.shift(face2, -1, 0) | morph.shift(face2, 0, 1)
            ridge = blk & ~face2 & nb & chk
            face2 = face2 | ridge
            st = np.where(ridge, b2, st)
        st = np.where(blk & (d < 2) & (facing < -0.5), np.where(face2, b2, body_) + P['shadow'], st)
        st = np.where(blk & (d < 2) & (facing > 0.35), np.where(face2, b2, body_) + P['rim'], st)
    else:
        raise ValueError('profile %r: rim, pillow, slab or twoface' % (profile,))
    seam_st = body_ + P['seam']
    # chipped corners: where the rim normal is diagonal, in a hashed share of corners
    if P['chip'] > 0:
        quad = (nx > 0).astype(np.int64) + 2 * (ny > 0)
        diag = blk & (d < 2) & (np.abs(nx) > 0.45) & (np.abs(ny) > 0.45)
        st = np.where(diag & (_hash_arr(bid[cid], quad, seed + 41) < P['chip']), seam_st, st)
    # wear: a checker blob in a share of the blocks
    # wear and cracks start at the interior pixel nearest a hashed point of the block's box, so
    # they ride with the block when the layout moves (a turning ring) instead of jumping
    def anchor(k1, k2):
        tx_ = cx + (hb(k1) - 0.5) * 0.6 * (bx1 - bx0 + 1)
        ty_ = cy + (hb(k2) - 0.5) * 0.6 * (by1 - by0 + 1)
        return np.hypot(xx + 0.5 - tx_[cid], yy + 0.5 - ty_[cid]) + 0.01 * _hash_arr(AX, AY, seed + 43)
    if P['wear'] > 0 and n:
        key = anchor(11, 12)
        pick = _pick(cid, blk & (d >= 2.5), key, n)
        live = (pick >= 0) & (hb(5) < P['wear'])
        live[0] = False
        px = np.where(live, pick % W, -999).astype(float) + 0.5
        py = np.where(live, pick // W, -999).astype(float) + 0.5
        rr = 2.0 + 2.5 * hb(6)                       # 3-12 px patches (08)
        blob = blk & live[cid] & (np.hypot(xx + 0.5 - px[cid], (yy + 0.5 - py[cid]) * 1.4) < rr[cid]) \
            & chk & (d >= 2)
        lift = (hb(10) < 0.5)[cid]                    # half the patches are polished (lit), half pitted
        st = np.where(blob, np.where(lift, body_ + P['rim'], body_ + P['shadow']), st)
    # pores
    if P['pores'] > 0:
        st = np.where(blk & (d >= 2) & (_hash_arr(AX, AY, seed + 47) < P['pores']), st - 1, st)
    # seams and structural breaks; heal > 0 lets that share of the seam fade into a 1-step
    # crease in runs of a few px (04 slabs: seams stop short, slabs half merge)
    st = np.where(sm, seam_st, st)
    if P.get('heal'):
        hv = _vnoise(AX, AY, 6.0, seed + 61)
        st = np.where(sm & (hv < P['heal']), body_ - 1, st)
    if struct is not None and struct is not False:
        g = np.where(ids > 0, ids // _layout.GROUP, -1)
        g = np.where(m, g, -1)
        outside = (ids < 0) | ~m
        gmin = np.full((H, W), 1 << 40, np.int64); gmax = np.full((H, W), -1, np.int64)
        touch_out = np.zeros((H, W), bool)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            gn = morph.shift(g, -dx, -dy, -1)
            on = morph.shift(outside, -dx, -dy, False)
            gmin = np.where(gn >= 0, np.minimum(gmin, gn), gmin)
            gmax = np.where(gn >= 0, np.maximum(gmax, gn), gmax)
            touch_out |= on
        sseam = sm & (((gmax >= 0) & (gmin != gmax)) | touch_out)
        near = morph.dilate(sseam, 1, 'cross') | (touch_out & blk)
        st = np.where(sseam, body_ + struct, st)
        st = np.where(near & blk & (d < 2) & (facing < 0.35), body_ + struct, st)
    # cracks: a short diagonal with a lit pixel under each crack pixel
    if P['cracks'] > 0 and n:
        key = anchor(13, 14)
        pick = _pick(cid, blk & (d >= 2.5), key, n)
        live = np.flatnonzero((pick >= 0) & (hb(7) < P['cracks']))
        live = live[live > 0]
        if live.size:
            x = (pick[live] % W).astype(np.int64); y = (pick[live] // W).astype(np.int64)
            dirx = np.where(hb(8)[live] < 0.5, 1, -1)
            L = 3 + (hb(9)[live] * 5).astype(int)
            alive = np.ones(len(live), bool)
            for s in range(7):
                ok = alive & (s < L) & (x >= 0) & (x < W) & (y >= 0) & (y < H)
                xi, yi = np.clip(x, 0, W - 1), np.clip(y, 0, H - 1)
                ok &= (cid[yi, xi] == live) & (d[yi, xi] >= 1.5)
                alive &= ok
                st[yi[ok], xi[ok]] = seam_st
                y2 = np.clip(yi + 1, 0, H - 1)
                below = ok & (cid[y2, xi] == live) & (yi + 1 < H) & (d[y2, xi] >= 1.5)
                st[y2[below], xi[below]] = body_ + P['rim']
                x = x + np.where(_hash_arr(bid[live], s, seed + 59) < 0.6, dirx, 0)
                y = y + 1
    st = np.where(st >= 0, np.clip(st, 0, steps - 1), -1)
    st = np.where(blk | sm, st, -1)
    paint = st >= 0
    n1 = _names(ramp, steps)
    if ramp2 is not None and face2.any():
        n2 = _names(ramp2, steps)
        G[paint & ~face2] = n1[st[paint & ~face2]]
        G[paint & face2] = n2[st[paint & face2]]
    else:
        G[paint] = n1[st[paint]]
    full[oy:ey, ox:ex] = st
    return full

def stones(c, mask, ramp, size=7, seed=1, base=None, squash=1.0, mortar=None, light=(-1, -1), jitter=0.85,
           profile='pillow', steps=7):
    """rubble or a cave wall in one call: layout.cells lumps about size x size*squash px, carved
    by shade_cells (profile 'pillow' by default; 'rim' for carved stone, 'slab' for big slabs).
    The old angular-Voronoi draft read as crazy paving (study 10) and is gone."""
    ids = _layout.cells(mask, size=(size * 1.25, size * squash), jitter=(min(jitter, 0.7), 0.6), seed=seed)
    st = shade_cells(c, ids, ramp, light=light, profile=profile, body=base, steps=steps, seed=seed)
    if mortar is not None:
        c.g[(np.asarray(ids)[:c.H, :c.W] == 0) & _mask(c, mask)] = mortar
    return st

# ---------------------------------------------------------------- C3: scatter engine
def _stamps(stamps):
    """a stamp [(dx, dy, tone), ...] or a list of them -> a list of stamps"""
    s0 = stamps[0]
    if len(s0) == 3 and isinstance(s0[0], (int, np.integer)):
        return [[tuple(p) for p in stamps]]
    return [[tuple(p) for p in s] for s in stamps]

def _mirror(stamps, light):
    """stamps are authored for light from the upper left; mirror them for another light"""
    if light is None:
        return stamps
    fx = -1 if light[0] > 0 else 1
    fy = -1 if light[1] > 0 else 1
    return [[(dx * fx, dy * fy, t) for dx, dy, t in s] for s in stamps]

def _kernel(fp, union, md, metric):
    """anchor offsets that a stamp with footprint fp blocks for a later stamp of any footprint
    in `union`: fp (+) ball(md) (+) -union, as (oy, ox, bool array)"""
    r = int(math.ceil(md)) - 1 if md > 0 else -1
    ball = [(bx, by) for by in range(-r, r + 1) for bx in range(-r, r + 1)
            if metric == 'cheb' or bx * bx + by * by < md * md] if r >= 0 else [(0, 0)]
    offs = {(px + bx - ux, py + by - uy) for px, py in fp for bx, by in ball for ux, uy in union}
    xs = [o[0] for o in offs]; ys = [o[1] for o in offs]
    ox, oy = min(xs), min(ys)
    k = np.zeros((max(ys) - oy + 1, max(xs) - ox + 1), bool)
    for x, y in offs:
        k[y - oy, x - ox] = True
    return oy, ox, k

def _place(mask, density, stamps, weights=None, min_dist=0, metric='cheb', cover=None, seed=0):
    """deterministic dart throwing: mask pixels pass hash(x, y, seed) < density, then go in the
    order of a second hash; each takes a stamp chosen by a third, and is accepted when no pixel
    of an accepted stamp lies within min_dist (cheb or euclid) of its pixels. Stops once the
    accepted stamps cover cover * |mask| px. Returns (xs, ys, ks) of the accepted stamps."""
    m = np.asarray(mask, bool)
    H, W = m.shape
    ys, xs = np.nonzero(m)
    if not xs.size:
        z = np.zeros(0, np.int64)
        return z, z, z
    dens = density if np.isscalar(density) else np.asarray(density, float)[ys, xs]
    keep = _hash_arr(xs, ys, seed) < dens
    xs, ys = xs[keep], ys[keep]
    pr = _hash_arr(xs, ys, seed + 1)
    order = np.argsort(pr, kind='stable')
    xs, ys = xs[order], ys[order]
    w = np.ones(len(stamps)) if weights is None else np.asarray(weights, float)
    cum = np.cumsum(w) / w.sum()
    ks = np.minimum(np.searchsorted(cum, _hash_arr(xs, ys, seed + 3), side='right'), len(stamps) - 1)
    sizes = np.array([len(s) for s in stamps])
    budget = None if cover is None else cover * m.sum()
    if not min_dist and budget is None:
        return xs, ys, ks
    if not min_dist:
        tot = np.cumsum(sizes[ks])
        n = int(np.searchsorted(tot, budget, side='left')) + 1
        return xs[:n], ys[:n], ks[:n]
    fps = [[(dx, dy) for dx, dy, _ in s] for s in stamps]
    union = sorted({p for f in fps for p in f})
    kers = [_kernel(f, union, min_dist, metric) for f in fps]
    pad = max(max(k[2].shape) for k in kers) + 2
    blocked = np.zeros((H + 2 * pad, W + 2 * pad), bool)
    acc = []
    total = 0
    xl, yl, kl = xs.tolist(), ys.tolist(), ks.tolist()
    for i in range(len(xl)):
        x, y, k = xl[i], yl[i], kl[i]
        if blocked[y + pad, x + pad]:
            continue
        acc.append(i)
        oy, ox, ker = kers[k]
        y0, x0 = y + pad + oy, x + pad + ox
        blocked[y0:y0 + ker.shape[0], x0:x0 + ker.shape[1]] |= ker
        total += sizes[k]
        if budget is not None and total >= budget:
            break
    acc = np.array(acc, np.int64)
    return xs[acc], ys[acc], ks[acc]

def _twinkle(xs, ys, seed, t, T, hold=3, duty=1.0):
    """which stamps show at frame t: visible if frac(h + m * floor(t / hold) * hold / T) < duty
    with an integer m per stamp, so frame T equals frame 0 (hold must divide T)"""
    if t is None or not T:
        return np.ones(len(xs), bool)
    _loop_check(T, hold)
    h = _hash_arr(xs, ys, seed + 2)
    mm = 1 + np.floor(_hash_arr(xs, ys, seed + 4) * 4)
    ph = (h + mm * (int(t) // hold) * hold / float(T)) % 1.0
    return ph < duty

def scatter(c, mask, stamps, density=1.0, min_dist=0, metric='cheb', light=None, cover=None,
            weights=None, seed=0, t=None, T=None, hold=3, duty=1.0, steps=7, min_step=0, clip=True):
    """stamp small shapes over a mask. A stamp is [(dx, dy, tone), ...]; tone is a slot name or
    an int offset from the slot under the pixel. stamps is one stamp or a list (picked by hash,
    weights). density: per-pixel chance a pixel is a candidate (a float or an H x W field, e.g.
    a light field from post.light_field). min_dist: no pixel of a new stamp within this distance
    ('cheb' or 'euclid') of an accepted one. cover stops once the stamps cover that share of the
    mask. light (a direction) mirrors stamps authored for an upper-left light. min_step skips
    stamps whose anchor sits on a step below it. t, T: twinkle, each stamp shown when
    frac(h + m * floor(t / hold) * hold / T) < duty (integer m, so the loop is exact).
    clip drops stamp pixels outside the mask. Returns the (x, y, stamp) rows drawn."""
    m = _mask(c, mask)
    S = _mirror(_stamps(stamps), light)
    xs, ys, ks = _place(m, density, S, weights, min_dist, metric, cover, seed)
    under = _ramp_arrays(c.g)
    if min_step > 0 and xs.size:
        ok = under[1][ys, xs] >= min_step
        xs, ys, ks = xs[ok], ys[ok], ks[ok]
    vis = _twinkle(xs, ys, seed, t, T, hold, duty)
    xs, ys, ks = xs[vis], ys[vis], ks[vis]
    px, py, pt = [], [], []
    for j, s in enumerate(S):
        sel = ks == j
        if not sel.any():
            continue
        for dx, dy, tone in s:
            px.append(xs[sel] + dx); py.append(ys[sel] + dy)
            pt.append(np.full(int(sel.sum()), tone, object))
    if px:
        px, py, pt = np.concatenate(px), np.concatenate(py), np.concatenate(pt)
        inb = (px >= 0) & (px < c.W) & (py >= 0) & (py < c.H)
        px, py, pt = px[inb], py[inb], pt[inb]
        if clip:
            ok = m[py, px]
            px, py, pt = px[ok], py[ok], pt[ok]
        _put(c, px, py, pt, steps, under)
    return np.stack([xs, ys, ks], 1) if xs.size else np.zeros((0, 3), np.int64)

# ------------------------------------------------ scatter presets
def pebbles(c, mask, ramp, base=3, density=0.10, comma=0.15, pair=0.3, patches=(0.3, 0.8), clumps=0.3, tile=16,
            variants=4, steps=7, seed=5):
    """pebble dirt (10): a few seamless tile x tile variants of a base fill with
      patches  one irregular blob (a 2-5 px random walk) per 3x3 lattice cell: a step down
               where its hash < patches[0], a step up above patches[1] (the damp / dry mottle)
      clumps   share of lattice cells with a dark speck clump: a 2-4 px diagonal-ish chain two
               steps down, its first pixel three down (the dark grit of the reference)
      pebbles  a lit cap (base+1, 1 px, 2 px wide with chance `pair`) over a shadow (base-2),
               or with chance `comma` a 1 px cap over a 2 px diagonal shadow; no pebble within
               1 px of another; candidates at `density`
    Measured on the reference dirt: dark flecks 11%, light 12%, the base tone 57%, blob median
    1-2 px, a dark pixel under a light one 2-3x more often than chance. Tiles are picked per
    tile cell by hash and never flipped, so the light stays on top. Returns the step grid."""
    blobs_dirs = ((1, 0), (1, 0), (-1, 0), (0, 1), (1, 1), (-1, 1), (0, -1), (1, -1))
    tiles = []
    for v in range(variants):
        s = seed * 131 + v * 17
        t = np.full((tile, tile), base, np.int64)
        nb = max(1, tile // 3)
        for by in range(nb):
            for bx in range(nb):
                ox = bx * 3 + int(_hash(bx, by, s + 8) * 3)
                oy = by * 3 + int(_hash(bx, by, s + 9) * 3)
                hp = _hash(bx, by, s + 1)
                if hp < patches[0] or hp > patches[1]:
                    k = base - 1 if hp < patches[0] else base + 1
                    x, y = ox, oy
                    for j in range(2 + int(_hash(bx, by, s + 6) * 4)):       # a 2-5 px walk
                        t[y % tile, x % tile] = k
                        dx, dy = blobs_dirs[int(_hash(bx * 8 + j, by, s + 10) * len(blobs_dirs))]
                        x, y = x + dx, y + dy
                if _hash(bx, by, s + 11) < clumps:                           # dark grit
                    x, y = ox + 1, oy + 1
                    for j in range(2 + int(_hash(bx, by, s + 12) * 3)):
                        t[y % tile, x % tile] = base - 3 if j == 0 else min(t[y % tile, x % tile], base - 2)
                        x += 1 if _hash(bx * 8 + j, by, s + 13) < 0.6 else -1
                        y += 1 if _hash(bx * 8 + j, by, s + 14) < 0.6 else 0
        ty, tx_ = np.mgrid[0:tile, 0:tile]
        occ = np.zeros((tile, tile), bool)
        hh = _hash_arr(tx_, ty, s + 2)
        cand = np.argsort(_hash_arr(tx_, ty, s + 3).ravel(), kind='stable')
        for i in cand:
            y, x = divmod(int(i), tile)
            if hh[y, x] >= density:
                continue
            if _hash(x, y, s + 4) < comma:
                pix = [(0, 0, base + 1), (0, 1, base - 2), (1, 2, base - 2)]
            elif _hash(x, y, s + 5) < pair:
                pix = [(0, 0, base + 1), (1, 0, base + 1), (0, 1, base - 2), (1, 1, base - 2)]
            else:
                pix = [(0, 0, base + 1), (0, 1, base - 2)]
            if any(occ[(y + dy + oy) % tile, (x + dx + ox) % tile]
                   for dx, dy, _ in pix for oy in (-1, 0, 1) for ox in (-1, 0, 1)):
                continue
            for dx, dy, k in pix:
                cur = t[(y + dy) % tile, (x + dx) % tile]
                t[(y + dy) % tile, (x + dx) % tile] = max(k, min(cur + 1, base + 2)) if k > base else min(k, cur - 1)
                occ[(y + dy) % tile, (x + dx) % tile] = True
        tiles.append(np.clip(t, 0, steps - 1))
    tiles = np.stack(tiles)
    m = _mask(c, mask)
    xx, yy = _grid(c)
    var = np.minimum((_hash_arr(xx // tile, yy // tile, seed + 7) * variants).astype(np.int64), variants - 1)
    st = tiles[var, yy % tile, xx % tile]
    c.g[m] = _names(ramp, steps)[st[m]]
    return st

def pits(c, mask, dark, light, density=0.044, min_dist=2.2, offset=(-1, 1), fill=None, pair=0.79, seed=0):
    """concrete pits (07): a light pixel with a dark partner at `offset` (79%), the rest a lone
    light or dark pixel; no closer than min_dist (euclid; nearest-neighbour p10 sqrt 5), until
    dark pixels cover `density` of the mask (07: 4.4%, median spacing 3 px). fill paints the mask first."""
    m = _mask(c, mask)
    if fill is not None:
        c.g[m] = fill
    ox, oy = offset
    S = [[(0, 0, light), (ox, oy, dark)], [(0, 0, light)], [(0, 0, dark)]]
    w = [pair, (1 - pair) / 2, (1 - pair) / 2]
    return scatter(c, m, S, density=1.0, min_dist=min_dist, metric='euclid', weights=w,
                   cover=density * (2 * pair + (1 - pair)) / (pair + (1 - pair) / 2), seed=seed)

def pocks(c, mask, cell=4, density=0.55, pit=-2, lip=1, light=(-1, -1), min_step=2, pair=0.3, steps=7, seed=0):
    """pitted chitin, skin, rusted metal (05): on a jittered grid of `cell` px, a pit (pit steps
    down, 1-2 px) with a lit lip on the diagonal away from the light (a concave pit catches the
    light on its far wall). Run it after form shading: offsets follow the shading under it, and
    pits skip slots below min_step (shadowed areas stay clean). density 0.55 for actors, ~0.2
    for props."""
    m = _mask(c, mask)
    H, W = c.H, c.W
    gi, gj = np.mgrid[0:(H + cell - 1) // cell, 0:(W + cell - 1) // cell]
    live = _hash_arr(gj, gi, seed) < density
    x = (gj * cell + (cell * _hash_arr(gj, gi, seed + 1))).astype(np.int64)[live]
    y = (gi * cell + (cell * _hash_arr(gj, gi, seed + 2))).astype(np.int64)[live]
    ok = (x < W) & (y < H)
    x, y = x[ok], y[ok]
    ok = m[y, x]
    x, y = x[ok], y[ok]
    under = _ramp_arrays(c.g)
    ok = under[1][y, x] >= min_step
    x, y = x[ok], y[ok]
    lx = 1 if light[0] < 0 else -1
    ly = 1 if light[1] < 0 else -1
    two = _hash_arr(x, y, seed + 3) < pair
    px = [x, x[two] + 1, x + lx + np.where(two & (lx > 0), 1, 0)]
    py = [y, y[two], y + ly]
    pt = [np.full(len(x), pit, object), np.full(int(two.sum()), pit, object), np.full(len(x), lip, object)]
    px, py, pt = np.concatenate(px), np.concatenate(py), np.concatenate(pt)
    inb = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    px, py, pt = px[inb], py[inb], pt[inb]
    ok = m[py, px]
    _put(c, px[ok], py[ok], pt[ok], steps, under)
    return np.stack([x, y], 1)

def ticks(c, mask, base=None, stamps=(('grass4', 'grass2'), ('grass2', 'grass1')), weights=(0.45, 0.55),
          single=0.3, cover=0.19, min_dist=2, steps=7, seed=0):
    """grass blade ticks (07, 08): vertical 2 px pairs (top tone over bottom tone), or with chance
    `single` only the top pixel, no closer than min_dist (Chebyshev) to another, until they
    cover `cover` of the mask (07: 19%). base fills the mask first. Tones are slots or offsets."""
    m = _mask(c, mask)
    if base is not None:
        c.g[m] = base
    S, w = [], []
    for (top, bot), wt in zip(stamps, weights):
        S += [[(0, 0, top), (0, 1, bot)], [(0, 0, top)]]
        w += [wt * (1 - single), wt * single]
    return scatter(c, m, S, density=1.0, min_dist=min_dist, metric='cheb', weights=w, cover=cover,
                   steps=steps, seed=seed)

def flecks(c, mask, up=1, down=-1, cover=0.19, up_share=0.68, runs=((1, .68), (2, .17), (3, .10), (4, .05)),
           steps=7, seed=0, t=None, T=None, hold=6, phases=4):
    """water shimmer (04): short horizontal runs (68% 1 px, 27% 2-3 px) of a lighter (`up`, 68%)
    or darker (`down`) tone covering `cover` of the mask; runs stop at the mask edge. Tones are
    slots or offsets. Animated: each run hides one frame-hold in `phases` (period hold * phases
    must divide T)."""
    m = _mask(c, mask)
    xx, yy = _grid(c)
    mean = sum(l * p for l, p in runs) / sum(p for _, p in runs)
    start = m & (_hash_arr(xx, yy, seed) < cover / mean)
    ys, xs = np.nonzero(start)
    lens = np.array([l for l, _ in runs]); cum = np.cumsum([p for _, p in runs]); cum = cum / cum[-1]
    L = lens[np.minimum(np.searchsorted(cum, _hash_arr(xs, ys, seed + 1), side='right'), len(lens) - 1)]
    tone = np.where(_hash_arr(xs, ys, seed + 2) < up_share, 0, 1)
    if t is not None and T:
        _loop_check(T, hold * phases, 'hold * phases')
        p = np.floor(_hash_arr(xs, ys, seed + 3) * phases).astype(int)
        vis = ((int(t) // hold + p) % phases) != 0
        xs, ys, L, tone = xs[vis], ys[vis], L[vis], tone[vis]
    under = _ramp_arrays(c.g)
    px, py, pt = [], [], []
    alive = np.ones(len(xs), bool)
    for k in range(int(lens.max())):
        x = xs + k
        alive &= (k < L) & (x < c.W)
        alive &= m[ys, np.minimum(x, c.W - 1)]
        px.append(x[alive]); py.append(ys[alive])
        pt.append(np.where(tone[alive] == 0, np.full(int(alive.sum()), up, object), np.full(int(alive.sum()), down, object)))
    if px:
        _put(c, np.concatenate(px), np.concatenate(py), np.concatenate(pt), steps, under)
    return np.stack([xs, ys, L], 1)

def leaflight(c, mask, lights, d0=0.003, d1=0.035, seed=3, t=None, T=None, hold=3, duty=0.75,
              bright=(0.12, 0.3), clusters=True):
    """isolated leaf-light flecks on a dark flat mass (01): density d0 + d1 * L, where L is the
    strongest light field at the pixel, and the colour of that light. lights is a list of
    (field, (slot_dim, slot_bright)) with H x W fields in 0..1 (post.light_field). A fleck is
    bright with chance bright[0] + bright[1] * L. No fleck touches another (90-95% isolated);
    clusters adds constellations of 10-20 flecks near the lights (L > 0.5). Twinkle as in
    scatter (an integer number of cycles per loop, held for `hold` frames)."""
    m = _mask(c, mask)
    F = np.stack([np.asarray(f, float) for f, _ in lights])
    j = np.argmax(F, 0)
    L = np.max(F, 0)
    xs, ys, _ = _place(m, d0 + d1 * L, [[(0, 0, 0)]], None, 2, 'cheb', None, seed)
    if clusters:
        xx, yy = _grid(c)
        gx, gy = xx // 24, yy // 24
        cxp = gx * 24 + (24 * _hash_arr(gx, gy, seed + 11)).astype(int)
        cyp = gy * 24 + (24 * _hash_arr(gx, gy, seed + 12)).astype(int)
        cxp, cyp = np.clip(cxp, 0, c.W - 1), np.clip(cyp, 0, c.H - 1)
        on = (L[cyp, cxp] > 0.5) & (_hash_arr(gx, gy, seed + 13) < 0.6)
        near = on & (np.hypot(xx - cxp, yy - cyp) < 6) & ((xx + (yy // 2)) % 2 == 0) & (yy % 2 == 0)
        near &= m & (_hash_arr(xx, yy, seed + 14) < 0.5)
        cy2, cx2 = np.nonzero(near)
        xs = np.concatenate([xs, cx2]); ys = np.concatenate([ys, cy2])
        if xs.size:
            key = np.unique(ys * c.W + xs)
            ys, xs = key // c.W, key % c.W
    vis = _twinkle(xs, ys, seed, t, T, hold, duty)
    xs, ys = xs[vis], ys[vis]
    br = _hash_arr(xs, ys, seed + 1) < bright[0] + bright[1] * L[ys, xs]
    for i, (_, (dim, hi)) in enumerate(lights):
        sel = j[ys, xs] == i
        c.g[ys[sel & ~br], xs[sel & ~br]] = dim
        c.g[ys[sel & br], xs[sel & br]] = hi
    return np.stack([xs, ys], 1)

def flakes(c, mask, ramp, base=1, cell=(10, 5), cluster=0.8, gate=0.9, length=(4, 9), stack=(1, 3), lit_end=2,
           shadow=True, steps=7, seed=0):
    """Celeste rock (02): stacks of 1 px dashes, 4-9 px long; each row up is shifted 1-2 px
    right and 2 px shorter, the last lit_end px of the top row are base+2, and a shadow dash
    (base-1, half as long) runs one row below, 1-3 px left, only over base pixels. Clusters of
    stacks on a jittered grid of `cell`. The defaults give the measured background rock: 79%
    base, 12% base+1, 3% base+2, 4-5% base-1. Foreground cliff (~60% non-base in the
    reference): three passes (seeds 0, 1, 2) with cell (7, 4), cluster 0.9, gate 0.95, length
    (2, 5) give about 50%. Returns the number of pixels painted."""
    m = _mask(c, mask)
    H, W = c.H, c.W
    cw, ch = cell
    names = _names(ramp, steps)
    basename = names[min(base, steps - 1)]
    out = []
    for gy in range(-1, H // ch + 1):
        for gx in range(-1, W // cw + 1):
            if _hash(gx // 2, gy // 2, seed) >= cluster or _hash(gx, gy, seed + 1) >= gate:
                continue
            ax = gx * cw + int(_hash(gx, gy, seed + 2) * cw * 0.6) + (gy % 2) * (cw // 2)
            ay = gy * ch + int(_hash(gx, gy, seed + 3) * ch * 0.5)
            L0 = length[0] + int(_hash(gx, gy, seed + 4) * (length[1] - length[0] + 1))
            n = stack[0] + int(_hash(gx, gy, seed + 5) * (stack[1] - stack[0] + 0.6))
            bottom = ay + n - 1
            if shadow:
                sx = ax - 1 - int(_hash(gx, gy, seed + 6) * 3)
                for x in range(sx, sx + max(2, (L0 + 1) // 2)):
                    y = bottom + 1
                    if 0 <= x < W and 0 <= y < H and m[y, x] and c.g[y, x] == basename:
                        out.append((x, y, max(0, base - 1)))
            x0 = ax
            for j in range(n):
                Lj = max(2, L0 - 2 * j)
                y = bottom - j
                for x in range(x0, x0 + Lj):
                    if 0 <= x < W and 0 <= y < H and m[y, x]:
                        k = base + 2 if (j == n - 1 and x >= x0 + Lj - lit_end) else base + 1
                        out.append((x, y, min(steps - 1, k)))
                x0 += 1 + int(_hash(gx * 7 + j, gy, seed + 7) * 2)
    for x, y, k in out:
        c.g[y, x] = names[k]
    return len(out)

def mottle(c, mask, ramp, base=2, block=(2, 2), density=0.1, rim_rows=3, rim_density=0.35, steps=7, seed=0):
    """a backdrop wall's mottle (02): 2x1 / 2x2 blocks one step up at `density` on a block grid
    whose odd rows shift by 1 px, and two steps up at rim_density in the top rim_rows rows under
    the mask's top edge. Paints over whatever is there (fill the mask with base first)."""
    m = _mask(c, mask)
    xx, yy = _grid(c)
    bw, bh = block
    by = yy // bh
    bx = (xx + (by % 2)) // bw
    hb = _hash_arr(bx, by, seed)
    tall = _hash_arr(bx, by, seed + 1) < 0.5
    inblock = tall | ((yy % bh) == 0)
    names = _names(ramp, steps)
    up = m & (hb < density) & inblock
    c.g[up] = names[min(steps - 1, base + 1)]
    if rim_rows:
        depth = np.zeros((c.H, c.W), np.int64)
        run = np.zeros(c.W, np.int64)
        for y in range(c.H):
            run = np.where(m[y], run + 1, 0)
            depth[y] = run
        rim = m & (depth <= rim_rows) & (_hash_arr(bx, by, seed + 2) < rim_density) & inblock
        c.g[rim] = names[min(steps - 1, base + 2)]
    return up

def jitter_dots(c, mask, slots, pitch=(5, 4), jitter=1, density=1.0, dark=None, weights=None, seed=0,
                t=None, T=None, hold=4, phases=3):
    """a loose sparkle lattice (04 tropical pool): dots on a grid of `pitch`, odd rows offset by
    half a pitch, each moved +-jitter px; slot by hash from `slots` (weights). dark adds a dot
    of that slot on the grid offset by half a pitch, at half density. Animated: each dot hides
    one hold in `phases` (hold * phases must divide T)."""
    m = _mask(c, mask)
    px_, py_ = pitch
    out = []
    for s_i, (sl, dens, off) in enumerate([(slots, density, (0, 0))] + ([([dark], density / 2, (px_ // 2, py_ // 2))] if dark else [])):
        gi, gj = np.mgrid[-1:c.H // py_ + 2, -1:c.W // px_ + 2]
        x = gj * px_ + (gi % 2) * (px_ // 2) + off[0] + np.round((2 * _hash_arr(gj, gi, seed + 10 * s_i) - 1) * jitter).astype(int)
        y = gi * py_ + off[1] + np.round((2 * _hash_arr(gj, gi, seed + 10 * s_i + 1) - 1) * jitter).astype(int)
        live = (_hash_arr(gj, gi, seed + 10 * s_i + 2) < dens) & (x >= 0) & (x < c.W) & (y >= 0) & (y < c.H)
        x, y = x[live], y[live]
        ok = m[y, x]
        x, y = x[ok], y[ok]
        if t is not None and T:
            _loop_check(T, hold * phases, 'hold * phases')
            p = np.floor(_hash_arr(x, y, seed + 7) * phases).astype(int)
            vis = ((int(t) // hold + p) % phases) != 0
            x, y = x[vis], y[vis]
        w = np.ones(len(sl)) if (weights is None or s_i) else np.asarray(weights, float)
        cum = np.cumsum(w) / np.sum(w)
        k = np.minimum(np.searchsorted(cum, _hash_arr(x, y, seed + 5), side='right'), len(sl) - 1)
        _put(c, x, y, np.array(sl, object)[k])
        out.append(np.stack([x, y], 1))
    return np.concatenate(out)

def stipple_field(c, mask, slot, density=0.35, seed=0, t=None, T=None, reseed=24, steps=7):
    """white-noise stipple (06 planet limb): each pixel takes `slot` (a slot, or an int offset)
    where hash(x, y) < density; density is a float, an H x W field or a function f(xx, yy).
    Never Bayer. With t and T it reseeds every `reseed` frames (reseed must divide T)."""
    m = _mask(c, mask)
    xx, yy = _grid(c)
    p = density(xx, yy) if callable(density) else density
    s = seed
    if t is not None and T:
        _loop_check(T, reseed, 'reseed')
        s = seed + 7919 * ((int(t) // reseed) % (T // reseed))
    on = m & (_hash_arr(xx, yy, s) < p)
    ys, xs = np.nonzero(on)
    _put(c, xs, ys, np.full(len(xs), slot, object), steps)
    return on

def speckle(c, mask, slots, density=0.06, seed=3, cluster=0.0, min_dist=2):
    """isolated flecks of the given slots (gravel, sparks, leaf-light without a light field).
    The draft paired half the flecks with x+1; references isolate them (01: 90-95%), so the
    flecks keep min_dist (Chebyshev) apart. cluster > 0 lets that share be vertical pairs."""
    S = [[(0, 0, s)] for s in slots] + [[(0, 0, s), (0, 1, s)] for s in slots]
    w = [1 - cluster] * len(slots) + [cluster] * len(slots)
    return scatter(c, mask, S, density=density, min_dist=min_dist, weights=w, seed=seed)

def stipple(c, mask, ramp, base=2, density=0.35, seed=5, light=(-1, -1), depth=None, steps=7):
    """a two-tone white-noise stipple over a base fill, the lighter flecks biased toward the
    light. (Foliage wants veg.leaf_glyphs: this fills every pixel, which study 07 measured as
    wrong for leaves; it suits dust, plaster, a planet's atmosphere.)"""
    m = _mask(c, mask)
    ys, xs = np.nonzero(m)
    if not xs.size:
        return
    c.g[m] = '%s%d' % (ramp, base)
    xx, yy = _grid(c)
    cx, cy = xs.mean(), ys.mean()
    rx, ry = max(1, np.ptp(xs) / 2), max(1, np.ptp(ys) / 2)
    lx, ly = _unit(light)
    k = np.clip(((xx - cx) / rx * lx + (yy - cy) / ry * ly), -1, 1)
    stipple_field(c, m, -1, 0.5 * density * (1 - k), seed + 1, steps=steps)
    stipple_field(c, m, 1, 0.5 * density * (1 + k), seed, steps=steps)
    if depth is not None:
        stipple_field(c, m & np.asarray(depth, bool), -1, 0.5, seed + 2, steps=steps)

def clumps(c, cx, cy, r, ramp, lobes=9, seed=4, steps=7, light=(-1, -1), squash=0.8, holes=None):
    """a canopy of overlapping lobes (references/drawing.md): each lobe has a lit upper rim, a mid body and a
    dark underside; lobes further back are a step darker. Returns the canopy mask."""
    H, W = c.H, c.W
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    total = np.zeros((H, W), bool)
    rnd = lambda i, s: _hash(i, seed, s)
    order = sorted(range(lobes), key=lambda i: rnd(i, 1))           # back to front
    lx, ly = light
    n = math.hypot(lx, ly)
    thr = thresholds(H, W)
    for j, i in enumerate(order):
        a = rnd(i, 2) * 2 * math.pi
        d = r * 0.62 * math.sqrt(rnd(i, 3))
        lr = r * (0.36 + 0.22 * rnd(i, 4))
        ox, oy = cx + math.cos(a) * d, cy + math.sin(a) * d * squash
        dist = np.hypot(xx - ox, (yy - oy) / squash)
        m = dist <= lr
        back = 1.0 - j / max(1, lobes - 1)                         # 1 = furthest back
        rel = ((xx - ox) * lx + (yy - oy) / squash * ly) / (lr * n)
        tone = 2.6 - 0.8 * back + 1.6 * np.clip(rel, -1, 1) + np.where(dist > lr - 1.2, -0.7, 0)
        k = np.clip(np.floor(tone + thr).astype(int), 0, steps - 1)
        c.g[m] = _names(ramp, steps)[k[m]]
        total |= m
    return total

def bricks(c, x0, y0, x1, y1, ramp, size=(8, 4), base=2, seed=7, mortar=None):
    """offset brick courses with a lit top edge per brick and the odd patched brick"""
    bw, bh = size
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    row = (yy - y0) // bh
    off = (bw // 2) * (row % 2)
    u, v = (xx - x0 + off) % bw, (yy - y0) % bh
    bid = (xx - x0 + off) // bw
    hv = _hash_arr(bid, row, seed)
    k = base + (v == 0) + np.where(hv < 0.12, -1, np.where(hv > 0.94, 1, 0))
    vals = np.array(['%s%d' % (ramp, max(0, int(q))) for q in k.ravel()], object).reshape(k.shape)
    if mortar is None:
        mortar = '%s%d' % (ramp, max(0, base - 2))
    vals[(u == 0) | (v == bh - 1)] = mortar
    sub = (yy >= 0) & (yy < c.H) & (xx >= 0) & (xx < c.W)
    c.g[yy[sub], xx[sub]] = vals[sub]

# ---------------------------------------------------------------- C5: architecture kit
_PAT = {'#': 1, '-': 0, '.': -2, ' ': 0, '+': 2, 'o': -1, '=': 0, '_': -1}

def _band(b):
    if isinstance(b, dict):
        return dict(b)
    keys = ('h', 'ramp', 'base', 'rows', 'pattern', 'period')
    return dict(zip(keys, b))

def _default_rows(h):
    if h <= 1:
        return [0]
    if h == 2:
        return [1, -1]
    return [1] + [0] * (h - 2) + [-1]

def profile(c, x0, x1, y0, bands, phase=0, sep=1, steps=7):
    """a moulding stack (09): bands top to bottom, each a dict (or tuple in this order)
      h        rows
      ramp     its ramp; base: its step
      rows     per-row offsets (default: lit top row +1, dark bottom row -1)
      pattern  a string repeated along x: '#' +1, '-' 0, '.' -2, 'o' -1, '+' +2 (dentils,
               slat wainscot '##..##-#--------'); or a list of ints. period defaults to its length
      shadow   rows of cast shadow under an overhang (cornice, rail): the next rows below go
               -3 then -2 (09: 4-8 rows under every overhang)
      sep      False drops the separator above this band
    sep: a 1-row separator at that step of the band's ramp between bands (None: none).
    Returns the y below the stack. Breakers (pilasters, a door) are painted over it after."""
    xs = np.arange(int(x0), int(x1))
    y = int(y0)
    pending = []                                      # (rows left, offset) of a cast shadow
    names_cache = {}
    def row(yr, ramp, k):
        if not (0 <= yr < c.H):
            return
        nm = names_cache.setdefault(ramp, _names(ramp, steps))
        if pending:
            k = k + pending.pop(0)
        sel = (xs >= 0) & (xs < c.W)
        c.g[yr, xs[sel]] = nm[np.clip(k, 0, steps - 1)[sel] if np.ndim(k) else np.full(sel.sum(), int(np.clip(k, 0, steps - 1)))]
    for i, b in enumerate(bands):
        b = _band(b)
        h, ramp, base = int(b['h']), b['ramp'], int(b.get('base', 3))
        if i and sep is not None and b.get('sep', True):
            row(y, ramp, np.full(len(xs), sep))
            y += 1
        rows = b.get('rows') or _default_rows(h)
        pat = b.get('pattern')
        if pat is not None:
            pv = np.array([_PAT[ch] for ch in pat] if isinstance(pat, str) else list(pat), np.int64)
            period = int(b.get('period') or len(pv))
            px = pv[(xs - int(x0) + phase + int(b.get('phase', 0))) % period % len(pv)]
        else:
            px = np.zeros(len(xs), np.int64)
        prow = b.get('pattern_rows')                  # rows the pattern applies to (default all)
        for j in range(h):
            k = base + int(rows[min(j, len(rows) - 1)])
            use = px if (prow is None or j in prow) else 0
            row(y, ramp, k + use)
            y += 1
        if b.get('shadow'):
            n = int(b['shadow'])
            pending[:] = [-3] * ((n + 1) // 2) + [-2] * (n // 2)
    return y

# 09 Katana ZERO 16 x 16 panel, read off the native pixels of one panel (field = base):
#   row 0 stile -2 (bottom row -3), row 1 bevel 0 on top (as bright as the field), -1 on the
#   sides and bottom, rows 2-3 a 2 px recess -3 top and bottom (the bottom pair is the 2-row
#   under-shadow), -2 at the sides, rows 4-5 the hot polished top edge +3 (row 5 only between
#   the corners), then an 8 x 8 field with a 4 x 4 centre square: a ring -1 top/bottom, -2 at
#   the sides, around the field tone. Horizontally: stile 1, bevel 1, recess 2, field 8, so two
#   cells side by side show the measured 2 px stile.
PANEL_RINGS = [(1, 'stile', -2, -2, -3), (1, 'bevel', 0, -1, -1), (2, 'recess', -3, -2, -3),
               (1, 'inner', 3, 0, 0), (1, 'inner2', 3, 0, 0)]

def panels(c, x0, y0, x1, y1, ramp, cell=(16, 16), base=3, rings=None, centre=4, centre_tones=(-1, -2, -1, 0),
           light='top', phase=(0, 0), steps=7):
    """fielded panels tiled over a rect (09): each cell is rings from the outside in, given as
    (width, name, top, side, bottom) step offsets from the field (base); default PANEL_RINGS
    (measured): stile -2, bevel 0/-1/-1, a 2 px recess -3/-2/-3 (its bottom is the 2-row
    under-shadow), a 2-row hot inner top edge +3; inside the rings the field (0) with a centre
    square `centre` px across in centre_tones (top, side, bottom, inside): a darker ring round
    a field-tone core. A tie between top and side goes to the top, so top runs reach the corners.
    light 'top' lights top edges only (09); 'topleft' treats the left side as top and the right
    as bottom. Returns the step grid of the rect."""
    rings = PANEL_RINGS if rings is None else rings
    cw, ch = cell
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    u, v = (xx - x0 + phase[0]) % cw, (yy - y0 + phase[1]) % ch
    dt, db, dl, dr = v, ch - 1 - v, u, cw - 1 - u
    d = np.minimum(np.minimum(dt, db), np.minimum(dl, dr))
    side = np.where(dt == d, 0, np.where(db == d, 2, np.where(dl == d, 3, 4)))   # 0 top 2 bottom 3 left 4 right
    if light == 'topleft':
        side = np.where(side == 3, 0, np.where(side == 4, 2, side))
    else:
        side = np.where(side >= 3, 1, side)
    off = np.zeros(d.shape, np.int64)
    edge = 0
    done = np.zeros(d.shape, bool)
    for w, _, top, sd, bot in rings:
        sel = ~done & (d < edge + w)
        off = np.where(sel, np.choose(np.minimum(side, 2), [top, sd, bot]), off)
        done |= sel
        edge += w
    if centre:
        cu0, cv0 = (cw - centre) // 2, (ch - centre) // 2
        cu, cvv = u - cu0, v - cv0
        inc = (cu >= 0) & (cu < centre) & (cvv >= 0) & (cvv < centre) & ~done
        t, s_, b, ins = centre_tones
        cen = np.where(cvv == 0, t, np.where(cvv == centre - 1, b,
                        np.where((cu == 0) | (cu == centre - 1), s_, ins)))
        if light == 'topleft':
            cen = np.where((cu == 0) & (cvv > 0) & (cvv < centre - 1), t, np.where((cu == centre - 1) & (cvv > 0) & (cvv < centre - 1), b, cen))
        off = np.where(inc, cen, off)
    st = np.clip(base + off, 0, steps - 1)
    sub = (yy >= 0) & (yy < c.H) & (xx >= 0) & (xx < c.W)
    c.g[yy[sub], xx[sub]] = _names(ramp, steps)[st[sub]]
    return st

def grille(c, x0, y0, x1, y1, slot, pitch=2, phase=(0, 0), kind='dots', lit=None, light=(-1, -1)):
    """speaker grilles and grates: kind 'dots' a 1 px dot every `pitch` px both ways (01 amp
    cabinets: 2 px pitch), 'slots' vertical 1 px lines every pitch px, 'hslots' horizontal.
    lit puts that slot on the pixel beside each dot or line on the light side (05 grates)."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    px, py = (pitch, pitch) if np.isscalar(pitch) else pitch
    if kind == 'dots':
        on = ((xx - x0 - phase[0]) % px == 0) & ((yy - y0 - phase[1]) % py == 0)
    elif kind == 'slots':
        on = (xx - x0 - phase[0]) % px == 0
    elif kind == 'hslots':
        on = (yy - y0 - phase[1]) % py == 0
    else:
        raise ValueError("kind: 'dots', 'slots' or 'hslots'")
    sub = (yy >= 0) & (yy < c.H) & (xx >= 0) & (xx < c.W)
    if lit is not None:                               # the pixel beside each mark, toward the light
        dx = 0 if kind == 'hslots' else (-1 if light[0] < 0 else 1)
        dy = (-1 if light[1] < 0 else 1) if kind == 'hslots' else 0
        lx_, ly_ = xx[on] + dx, yy[on] + dy
        ok = (lx_ >= max(0, x0)) & (lx_ < min(c.W, x1)) & (ly_ >= max(0, y0)) & (ly_ < min(c.H, y1))
        c.g[ly_[ok], lx_[ok]] = lit
    c.g[yy[on & sub], xx[on & sub]] = slot
    return on

def inset_frame(c, x0, y0, x1, y1, slot, inset=2, lit=None, light='topleft', notch=0, notch_slot=None):
    """a 1 px trim line `inset` px inside the rect [x0, x1) x [y0, y1) (01 amp cabinets, 06
    pedestal tops). lit paints the top (and, for light='topleft', left) runs in that slot instead.
    notch draws inward-pointing corner triangles of that size at the bottom-left and top-right
    corners, inside the trim (06 brass notches)."""
    a, b = int(x0) + inset, int(y0) + inset
    e, f = int(x1) - 1 - inset, int(y1) - 1 - inset
    if e < a or f < b:
        return
    top = [(x, b) for x in range(a, e + 1)]
    left = [(a, y) for y in range(b, f + 1)]
    bot = [(x, f) for x in range(a, e + 1)]
    right = [(e, y) for y in range(b, f + 1)]
    for pts, is_lit in ((bot, False), (right, False), (left, light == 'topleft'), (top, True)):
        s = lit if (lit is not None and is_lit) else slot
        for x, y in pts:
            c.put(x, y, s)
    if notch:
        ns = notch_slot or slot
        for i in range(notch):
            for j in range(notch - i):
                c.put(a + 1 + i, f - 1 - j, ns)
                c.put(e - 1 - i, b + 1 + j, ns)

def emitter_grid(c, x0, y0, cols, rows, slots=('emit5', 'emit3'), cell=5, pitch=(10, 9.5), jitter=1,
                 shape='square', recess=None, rim=None, seed=0):
    """a lamp panel (01): cols x rows lenses `cell` px across at `pitch` (fractional pitches
    accumulate, so rows land 9 or 10 px apart), each moved +-jitter px by hash (hand placement);
    rows alternate the two lens slots. shape 'square' or 'diamond' (03 wall emitters). recess
    draws a 1 px ring around each lens; rim a lit top-left frame round the whole panel.
    Returns the emitter mask (feed it to post halos)."""
    mask = np.zeros((c.H, c.W), bool)
    px, py = (pitch, pitch) if np.isscalar(pitch) else pitch
    r = cell // 2
    for j in range(rows):
        for i in range(cols):
            x = int(math.floor(x0 + i * px)) + int(round((2 * _hash(i, j, seed) - 1) * jitter))
            y = int(math.floor(y0 + j * py)) + int(round((2 * _hash(i, j, seed + 1) - 1) * jitter))
            s = slots[j % len(slots)]
            for v in range(cell):
                for u in range(cell):
                    if shape == 'diamond' and abs(u - r) + abs(v - r) > r:
                        continue
                    c.put(x + u, y + v, s)
                    if 0 <= x + u < c.W and 0 <= y + v < c.H:
                        mask[y + v, x + u] = True
    if recess is not None:
        ring = morph.boundary(mask, outer=True, conn=4)
        c.g[ring] = recess
    if rim is not None:
        ys, xs = np.nonzero(mask)
        if xs.size:
            a, b, e = xs.min() - 2, ys.min() - 2, xs.max() + 2
            f = ys.max() + 2
            for x in range(a, e + 1):
                c.put(x, b, rim)
            for y in range(b, f + 1):
                c.put(a, y, rim)
    return mask

def cap(c, mask, slot, thick=(1, 2), deep=0.4, notch=(3, 7), seed=0):
    """pale edge caps (05): the top `thick[0]` px of every column of the mask (thick[1] where a
    column hash < deep) take `slot`, except a 1-column notch after every run of notch px."""
    m = _mask(c, mask)
    xs = np.arange(c.W)
    # notch columns: runs of notch[0]..notch[1] columns, then a gap of one
    gap = np.zeros(c.W, bool)
    x, k = 0, 0
    while x < c.W:
        x += notch[0] + int(_hash(k, 1, seed) * (notch[1] - notch[0] + 1))
        if x < c.W:
            gap[x] = True
        x += 1
        k += 1
    th_ = np.where(_hash_arr(xs, 0, seed + 3) < deep, thick[1], thick[0])
    top = m & ~morph.shift(m, 0, 1, False)
    out = np.zeros_like(m)
    for j in range(max(thick)):
        layer = morph.shift(top, 0, j, False) & m & (j < th_)[None, :]
        out |= layer
    out &= ~gap[None, :]
    c.g[out] = slot
    return out

def wet_streaks(c, mask, slot, length=(2, 6), density=0.08, up=(0, -1), seed=0):
    """wet speculars (05): on edge pixels whose outward normal faces `up` (n . up > 0.5), with
    chance `density` start a 2-6 px run that follows the contour (the next edge pixel to the
    side, up or down one row)."""
    m = _mask(c, mask)
    nx, ny = morph.normals(m)
    ux, uy = _unit(up)
    edge = m & ~morph.erode(m, 1, 'cross')
    face = edge & (nx * ux + ny * uy > 0.5)
    ys, xs = np.nonzero(face & (_hash_arr(np.arange(c.W)[None, :] + 0 * np.arange(c.H)[:, None],
                                          np.arange(c.H)[:, None] + 0 * np.arange(c.W)[None, :], seed) < density))
    drawn = np.zeros_like(m)
    for x, y in zip(xs.tolist(), ys.tolist()):
        L = length[0] + int(_hash(x, y, seed + 1) * (length[1] - length[0] + 1))
        dx = 1 if _hash(x, y, seed + 2) < 0.5 else -1
        for _ in range(L):
            drawn[y, x] = True
            nxt = None
            for oy in (0, -1, 1):
                X, Y = x + dx, y + oy
                if 0 <= X < c.W and 0 <= Y < c.H and face[Y, X]:
                    nxt = (X, Y)
                    break
            if nxt is None:
                break
            x, y = nxt
    c.g[drawn] = slot
    return drawn

def slats(c, mask, slot, period=20, width=5, slope=1, phase=0):
    """diagonal slats (03 outer walls): bands `width` px wide every `period` px at 1:slope pixel
    steps, inside the mask"""
    m = _mask(c, mask)
    xx, yy = _grid(c)
    on = m & (((xx - slope * yy + phase) % period) < width)
    c.g[on] = slot
    return on

def segments(c, mask, spine, width, ramp, spacing=5, bow=1.5, groove=(0, 1), crescent=None, base=2,
             light=(-1, -1), contrast=2.2, steps=8, phase=0.0):
    """segmented forms (05: a crab belly, tubes, tails): rings every `spacing` px along a spine
    polyline [(x, y), ...] of half width `width` (a number or a list per vertex). Each ring has
    a 1 px groove (groove[0]; groove[1] for its second px on the half away from the light), a
    1 px crescent highlight just after it on the lit half (|u| < 0.75; crescent defaults to the
    top step; the bow makes it a C), and a bulge between; rings run on past the spine's ends; rings bow
    `bow` px toward the viewer. Cylinder shading base + contrast * facing. phase slides the rings
    along the spine (a crawl: one spacing per loop is seamless). Returns the step grid."""
    m = _mask(c, mask)
    P = np.asarray(spine, float)
    Wv = np.full(len(P), float(width)) if np.isscalar(width) else np.asarray(width, float)
    ys, xs = np.nonzero(m)
    px, py = xs + 0.5, ys + 0.5
    best = np.full(len(xs), np.inf); S = np.zeros(len(xs)); U = np.zeros(len(xs)); NX = np.zeros(len(xs)); NY = np.zeros(len(xs))
    acc = 0.0
    nseg = len(P) - 1
    for i in range(nseg):
        a, b = P[i], P[i + 1]
        dv = b - a
        L = math.hypot(*dv) or 1e-6
        tdir = dv / L
        nrm = np.array([-tdir[1], tdir[0]])
        tr = ((px - a[0]) * tdir[0] + (py - a[1]) * tdir[1]) / L
        tt = np.clip(tr, 0, 1)
        qx, qy = a[0] + tt * dv[0], a[1] + tt * dv[1]
        dist = np.hypot(px - qx, py - qy)
        side = (px - a[0]) * nrm[0] + (py - a[1]) * nrm[1]
        w = Wv[i] + tt * (Wv[i + 1] - Wv[i])
        upd = dist < best
        best = np.where(upd, dist, best)
        # past the spine's ends the rings run on (unclipped arc length), so a cap is ringed too
        te = np.clip(tr, -np.inf if i == 0 else 0, np.inf if i == nseg - 1 else 1)
        S = np.where(upd, acc + te * L, S)
        U = np.where(upd, np.clip(side / np.maximum(w, 1e-6), -1, 1), U)
        NX = np.where(upd, nrm[0], NX); NY = np.where(upd, nrm[1], NY)
        acc += L
    U = np.clip(U, -1, 1)
    Lx, Ly = _unit(light)
    facing = U * (NX * Lx + NY * Ly)
    s2 = S + bow * (1 - U * U) + (phase % spacing)
    mpx = s2 % spacing                                # px past the last groove
    f = mpx / spacing
    k = base + contrast * facing
    k = k + 0.8 * (0.5 - np.abs(f - 0.6)) * 2
    st = np.floor(k + 0.5).astype(np.int64)
    lit = (facing > 0.05) & (np.abs(U) < 0.75)
    cre = steps - 1 if crescent is None else crescent
    # a continuous 1 px groove, then on the lit half the 1 px crescent right after it and on
    # the shadow half a second groove pixel (seams are 2 px on the side away from the light)
    st = np.where(mpx < 1, groove[0], np.where(mpx < 2, np.where(lit, cre, np.where(facing < 0, groove[1], st)), st))
    st = np.clip(st, 0, steps - 1)
    out = np.full((c.H, c.W), -1, np.int64)
    out[ys, xs] = st
    c.g[ys, xs] = _names(ramp, steps)[st]
    return out

def tapestry(c, mask, slots, cell=(4, 24), holes=0.35, channels=30, motifs=('ring', 'diamond', 'chain'),
             motif_every=150, drips=0.15, drip_len=(2, 8), spill=True, clump=28, seed=0):
    """low-contrast ornamental canopy (03): slots = [t0 back/channels, t1, t2 masses, t3 motifs,
    (t4 a second motif tone)] within ~0.07 L of each other; or a list of such families, picked
    by x band (teal on the left, indigo and maroon on the right). The mask's box is split
    recursively into blocks (cell[0] .. cell[1] px); `holes` of the area is left open, chosen by a
    coarse field of `clump` px so masses gather in clumps with open back between; 1 px channels walk
    orthogonally through the masses; ring, diamond and chain motifs are stamped every
    `motif_every` px of area; mass undersides grow 1 px drips 2-8 px long (spill lets them hang
    below the mask). Returns the mass mask."""
    m = _mask(c, mask)
    ys, xs = np.nonzero(m)
    if not xs.size:
        return m
    fam = slots if isinstance(slots[0], (list, tuple)) else [slots]
    bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    lo, hi = cell
    leaves = []
    stack = [(bx0, by0, bx1, by1, 0)]
    while stack:
        a, b, e, f, k = stack.pop()
        w, h = e - a, f - b
        hs = _hash(a * 31 + e, b * 17 + f, seed + k)
        if (max(w, h) > hi or (hs < 0.7 and max(w, h) > 2 * lo)) and max(w, h) >= 2 * lo:
            fr = 0.3 + 0.4 * _hash(a, b * 7 + k, seed + 1)
            if w >= h * 0.5:                              # favour tall strokes (03 masses hang)
                s = int(round(a + fr * w)); s = min(max(s, a + lo), e - lo)
                stack += [(a, b, s, f, k + 1), (s, b, e, f, k + 1)]
            else:
                s = int(round(b + fr * h)); s = min(max(s, b + lo), f - lo)
                stack += [(a, b, e, s, k + 1), (a, s, e, f, k + 1)]
        else:
            leaves.append((a, b, e, f))
    grid = np.zeros((c.H, c.W), np.int64)            # 0 back, 1 / 2 mass tones, 3/4 motif tones
    famg = np.full((c.H, c.W), -1, np.int64)         # the family of each mass pixel
    # holes cluster: a leaf's score mixes a coarse value field (cell `clump` px) with its own
    # hash, and the lowest-scoring leaves by area become holes, so masses gather into clumps
    # with open back between them (03) instead of a quilt
    def vfield(x, y):
        gx, gy = x / float(clump), y / float(clump)
        ix, iy = int(math.floor(gx)), int(math.floor(gy))
        fx, fy = gx - ix, gy - iy
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        v = [_hash(ix + i, iy + j, seed + 13) for j in (0, 1) for i in (0, 1)]
        return (v[0] * (1 - fx) + v[1] * fx) * (1 - fy) + (v[2] * (1 - fx) + v[3] * fx) * fy
    score = [0.7 * vfield((a + e) / 2.0, (b + f) / 2.0) + 0.3 * _hash(a, b, seed + 2) for (a, b, e, f) in leaves]
    area = np.array([(e - a) * (f - b) for (a, b, e, f) in leaves], float)
    order = np.argsort(score, kind='stable')
    hole = np.zeros(len(leaves), bool)
    hole[order[:int(np.searchsorted(np.cumsum(area[order]), holes * area.sum()))]] = True
    nf = len(fam)
    for i, (a, b, e, f) in enumerate(leaves):
        if hole[i]:
            continue
        tone = 1 if _hash(a, b, seed + 3) < 0.5 else 2
        grid[b:f, a:e] = tone
        # family by x with a hashed spread, so masses of two families interleave near the split
        u = ((a + e) / 2.0 - bx0) / max(1, bx1 - bx0) + 0.3 * (_hash(a, b, seed + 14) - 0.5)
        famg[b:f, a:e] = min(nf - 1, max(0, int(u * nf)))
        # a 1 px darker cut on the leaf's right or lower side, often
        if _hash(a, b, seed + 4) < 0.6:
            grid[b:f, max(a, e - 1):e] = 0
        if _hash(a, b, seed + 5) < 0.5:
            grid[max(b, f - 1):f, a:e] = 0
    grid[~m] = 0
    # channels: orthogonal walks
    for i in range(channels):
        k = int(_hash(i, 1, seed + 6) * len(xs))
        x, y = int(xs[k]), int(ys[k])
        dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[int(_hash(i, 2, seed + 6) * 4)]
        L = 8 + int(_hash(i, 3, seed + 6) * 23)
        for s in range(L):
            if 0 <= x < c.W and 0 <= y < c.H and m[y, x]:
                grid[y, x] = 0
            if _hash(i, s, seed + 7) < 0.15:
                dx, dy = (dy, dx) if _hash(i, s, seed + 8) < 0.5 else (-dy, -dx)
            x += dx; y += dy
    masses = (grid > 0) & m
    # motifs
    nmot = max(1, int(m.sum() / motif_every))
    shapes = {
        'ring': [(u, v) for v in range(5) for u in range(5) if (u in (0, 4) or v in (0, 4)) and (u, v) not in ((0, 0), (0, 4), (4, 0), (4, 4))],
        'diamond': [(1, 0), (0, 1), (2, 1), (1, 2)],
        'chain': [(i % 2, i) for i in range(7)],
        'zigzag': [(i % 3 if (i // 3) % 2 == 0 else 2 - i % 3, i) for i in range(7)],
    }
    for i in range(nmot):
        k = int(_hash(i, 4, seed + 9) * len(xs))
        x, y = int(xs[k]), int(ys[k])
        kind = motifs[int(_hash(i, 5, seed + 9) * len(motifs))]
        tone = 3 if (len(fam[0]) < 5 or _hash(i, 6, seed + 9) < 0.6) else 4
        for u, v in shapes[kind]:
            X, Y = x + u, y + v
            if 0 <= X < c.W and 0 <= Y < c.H and m[Y, X]:
                grid[Y, X] = tone
    # drips under masses
    below_open = masses & ~morph.shift(masses, 0, -1, False)
    dys, dxs = np.nonzero(below_open & (_hash_arr(np.arange(c.W)[None, :] + 0 * grid, np.arange(c.H)[:, None] + 0 * grid, seed + 10) < drips))
    dripm = np.zeros_like(m)
    for x, y in zip(dxs.tolist(), dys.tolist()):
        L = drip_len[0] + int(_hash(x, y, seed + 11) * (drip_len[1] - drip_len[0] + 1))
        for j in range(1, L + 1):
            Y = y + j
            if Y >= c.H or (not spill and not m[Y, x]) or masses[Y, x]:
                break
            grid[Y, x] = grid[y, x]
            famg[Y, x] = famg[y, x]
            dripm[Y, x] = True
    # paint: masses (and their drips) in their own family, back, channels and motifs by x band
    xx, yy = _grid(c)
    band = np.clip(((xx - bx0 + (6 * _hash_arr(xx // 3, yy // 6, seed + 12) - 3)) * nf // max(1, bx1 - bx0)).astype(int), 0, nf - 1)
    band = np.where((famg >= 0) & ((grid == 1) | (grid == 2)), famg, band)
    paint = m | dripm
    for fi, f_ in enumerate(fam):
        for tone in range(min(5, len(f_))):
            sel = paint & (band == fi) & (grid == tone)
            c.g[sel] = f_[tone]
    return masses

def circuit(c, mask, slot, inset=2, keep=0.6, hooks=0.4, pipes=6, pipe_len=(6, 20), cut=None, cut_share=0.2,
            mirror_x=None, piece=(6, 16), seed=0):
    """circuit linework inside a ruin mass (03): 1 px lines `inset` px inside the mask's edge,
    split at corners into straight segments and long runs into pieces of `piece` px, a hashed
    `keep` share kept; free ends get a hook
    (1 px in, then 1-2 px back); `pipes` pairs of vertical lines 2 px apart drop from the top
    edge pipe_len px and turn toward the centre. cut draws cut_share of the segments in a darker
    slot. mirror_x: generate the left half and mirror it about that x (03 is mirrored about the
    frame centre). Returns the line mask."""
    m = _mask(c, mask)
    H, W = m.shape
    if mirror_x is not None:
        half = m.copy()
        half[:, int(mirror_x):] = False
        work = half
    else:
        work = m
    inner = morph.erode(work, inset, 'cross', border=False) if inset else work
    edge = inner & ~morph.erode(inner, 1, 'cross', border=False)
    if mirror_x is not None:
        edge &= np.arange(W)[None, :] < int(mirror_x) - inset
    L = morph.shift(edge, 1, 0); R = morph.shift(edge, -1, 0)
    Uu = morph.shift(edge, 0, 1); D = morph.shift(edge, 0, -1)
    hrun = edge & (L | R)
    vrun = edge & (Uu | D) & ~hrun
    lab_h, nh = morph.label(hrun, 4)
    lab_v, nv = morph.label(vrun, 4)
    # long runs break into pieces of piece[0]..piece[1] px, each kept or dropped on its own
    xx, yy = np.mgrid[0:H, 0:W][1], np.mgrid[0:H, 0:W][0]
    plen = piece[0] + (_hash_arr(lab_h + 7 * lab_v, 3, seed) * (piece[1] - piece[0] + 1)).astype(np.int64)
    ph = (xx + (_hash_arr(lab_h, 4, seed) * 16).astype(np.int64)) // plen
    pv = (yy + (_hash_arr(lab_v, 5, seed) * 16).astype(np.int64)) // plen
    key = np.where(hrun, lab_h * 4096 + ph, np.where(vrun, (lab_v + nh) * 4096 + pv, 0))
    u, inv = np.unique(key, return_inverse=True)
    segid = inv.reshape(H, W)
    nh, nv = len(u) - 1, 0
    keep_seg = _hash_arr(np.arange(nh + nv + 1), 1, seed) < keep
    keep_seg[0] = False
    is_cut = _hash_arr(np.arange(nh + nv + 1), 2, seed) < (cut_share if cut else 0)
    line = edge & keep_seg[segid]
    # bridge corner pixels that join two kept segments
    corner = edge & ~line & ((morph.shift(line, 1, 0) | morph.shift(line, -1, 0)) & (morph.shift(line, 0, 1) | morph.shift(line, 0, -1)))
    line |= corner
    cutm = line & is_cut[segid]
    # hooks at free ends
    nbs = sum(morph.shift(line, dx, dy).astype(int) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    ends = line & (nbs == 1)
    ey, ex = np.nonzero(ends)
    add = []
    for x, y in zip(ex.tolist(), ey.tolist()):
        if _hash(x, y, seed + 3) >= hooks:
            continue
        # direction of travel = away from the one neighbour
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            X, Y = x - dx, y - dy
            if 0 <= X < W and 0 <= Y < H and line[Y, X]:
                break
        for px_, py_ in ((-dy, dx), (dy, -dx)):          # the perpendicular that goes deeper
            X, Y = x + px_, y + py_
            if 0 <= X < W and 0 <= Y < H and inner[Y, X] and not edge[Y, X]:
                n = 1 + int(_hash(x, y, seed + 4) * 2)
                add.append((X, Y))
                for j in range(1, n + 1):
                    add.append((X - dx * j, Y - dy * j))
                break
    for X, Y in add:
        if 0 <= X < W and 0 <= Y < H and work[Y, X]:
            line[Y, X] = True
    # pipes from the top edge, turning toward the centre (or the mirror axis)
    cols = np.nonzero(work.any(0))[0]
    if pipes and cols.size:
        axis = mirror_x if mirror_x is not None else (cols.min() + cols.max()) / 2.0
        topy = np.argmax(work, 0)
        for i in range(pipes):
            x = int(cols[int(_hash(i, 7, seed) * len(cols))])
            toward = 1 if x < axis else -1
            Lp = pipe_len[0] + int(_hash(i, 8, seed) * (pipe_len[1] - pipe_len[0] + 1))
            for k, xo in enumerate((0, 2 * -toward)):        # the outer line turns lower and runs further
                X = x + xo
                if not (0 <= X < W):
                    continue
                y0_ = int(topy[X]) + inset
                yend = y0_ + Lp + 2 * k
                for Y in range(y0_, min(H, yend)):
                    if work[Y, X]:
                        line[Y, X] = True
                for j in range(1, 3 + 2 * k + 1):
                    XX = X + toward * j
                    if 0 <= XX < W and 0 <= yend - 1 < H and work[yend - 1, XX]:
                        line[yend - 1, XX] = True
    line &= work
    cutm &= line
    if mirror_x is not None:
        mx = int(mirror_x)
        xsrc = 2 * mx - 1 - np.arange(W)
        okc = (xsrc >= 0) & (xsrc < W)
        mir = np.zeros_like(line); mirc = np.zeros_like(cutm)
        mir[:, okc] = line[:, xsrc[okc]]; mirc[:, okc] = cutm[:, xsrc[okc]]
        right = np.arange(W)[None, :] >= mx
        line = np.where(right, mir, line) & m
        cutm = np.where(right, mirc, cutm) & m
    c.g[line & ~cutm] = slot
    if cut is not None:
        c.g[cutm] = cut
    return line

# ---------------------------------------------------------------- C6: roofs and boards
def _runs(p0, n, lenfn, start=0):
    """1-D runs over positions p0 .. p0 + n - 1: (run index, offset in the run, run length) per
    position; run k is lenfn(k) long and run 0 starts at `start` (walked back to cover p0)."""
    k, s = 0, int(start)
    while s > p0:
        k -= 1
        s -= max(1, int(lenfn(k)))
    idx = np.zeros(n, np.int64); off = np.zeros(n, np.int64); ln = np.ones(n, np.int64)
    p = p0
    while p < p0 + n:
        L = max(1, int(lenfn(k)))
        if s + L > p:
            a, b = max(p, s), min(s + L, p0 + n)
            idx[a - p0:b - p0] = k
            off[a - p0:b - p0] = np.arange(a - s, b - s)
            ln[a - p0:b - p0] = L
            p = b
        s += L
        k += 1
    return idx, off, ln

def _span(m, origin):
    ys, xs = np.nonzero(m)
    X0, X1, Y0, Y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    ox, oy = (X0, Y0) if origin is None else (int(origin[0]), int(origin[1]))
    return X0, X1, Y0, Y1, ox, oy

def _lenfn(size, key, seed):
    """a run-length rule: an int is fixed, (lo, hi) a hashed length per run"""
    if isinstance(size, (tuple, list)):
        lo, hi = int(size[0]), int(size[1])
        return (lambda k: lo + int(_hash(k, key, seed) * (hi - lo + 1))), lo
    return (lambda k: int(size)), int(size)

def _moss(c, m, shade, lit, amount, ramp, cell, seed, steps, base=2):
    """moss patches over a coursed surface: value-noise patches covering `amount` of the mask,
    growing first in `shade` (the rows under a lip, the seams) and over whole units in the patch
    cores; orphan pixels dropped. Moss is base in the shade, base+1 on bodies, base+2 on `lit`."""
    xx, yy = _grid(c)
    nz = _vnoise(xx, yy, cell, seed + 50)
    if not m.any() or amount <= 0:
        return np.zeros_like(m)
    lo = np.quantile(nz[m], 1 - min(1.0, amount))
    core_t = np.quantile(nz[m], 1 - min(1.0, amount * 0.45))
    mm = m & (((nz >= lo) & shade) | (nz >= core_t))
    mm = morph.remove_small(mm, 3, 4)
    k = np.where(shade, base, np.where(lit, base + 2, base + 1))
    names = _names(ramp, steps)
    c.g[mm] = names[np.clip(k, 0, steps - 1)][mm]
    return mm

def _shingle_rows(h, view):
    if h <= 1:
        return [0]
    r = [0] * h
    r[0], r[-1] = -2, 1
    if view != 'side' and h >= 4:
        r[1] = -1
    return r

def shingles(c, mask=None, ramp='roof', size=None, base=3, shape='scallop', view='side', rows=None,
             seam=-2, vary=0.12, slipped=0.03, missing=0.015, under=None, moss=0.0, moss_ramp='moss',
             moss_cell=12, origin=None, seed=0, steps=7):
    """roof shingles and tiles: offset courses of tiles, each with a dark shadow row under the lip
    of the course above, a 1 px seam between tiles and a 1 px lit lower edge (01 HLD roofs, 04
    Sea of Stars 3/4 roofs, 10 Stardew shingles: banded courses, never pillow-shaded tiles).
    shape 'scallop' rounds each tile's lower corners (the seam and the shadow meet in a V),
    'rect' squares them (slate, flat tiles), 'shake' is rect with hashed widths (default (3, 7))
    and a 1 px ragged drop on some tiles. size=(w, h) per tile, w an int or (lo, hi); view
    'side' (default 6x3: shadow, body, lit) or '34' (6x5, adds a half shade row under the lip);
    rows overrides the per-row step offsets, top to bottom. A `vary` share of tiles sits one step
    off; `missing` tiles show `under` (default ramp0) with a lath row, `slipped` tiles hang 1 px
    low with a dark sliver above; moss > 0 grows moss_ramp patches from the laps and seams.
    Courses start at the mask's top-left (or origin). Returns the tile id map (-1 outside)."""
    m = _mask(c, mask)
    ids = np.full((c.H, c.W), -1, np.int64)
    if not m.any():
        return ids
    if size is None:
        size = ((3, 7) if shape == 'shake' else 6, 3 if view == 'side' else 5)
    w, h = size
    h = int(h)
    rows = list(rows) if rows is not None else _shingle_rows(h, view)
    rows = (rows + [rows[-1]] * h)[:h]
    X0, X1, Y0, Y1, ox, oy = _span(m, origin)
    U = np.zeros((c.H, c.W), np.int64); WL = np.ones((c.H, c.W), np.int64)
    V = np.zeros((c.H, c.W), np.int64)
    r0, r1 = (Y0 - oy) // h, (Y1 - 1 - oy) // h
    for r in range(r0, r1 + 1):
        fn, lo = _lenfn(w, r, seed + 1)
        if isinstance(w, (tuple, list)):
            start = -int(_hash(r, 0, seed + 2) * lo)
        else:
            start = -(int(w) // 2) * (r % 2)
        idx, off, ln = _runs(X0 - ox, X1 - X0, fn, start)
        ya, yb = max(Y0, oy + r * h), min(Y1, oy + (r + 1) * h)
        if yb <= ya:
            continue
        ids[ya:yb, X0:X1] = (r + 4096) * 65536 + (idx + 32768)[None, :]
        U[ya:yb, X0:X1] = off[None, :]
        WL[ya:yb, X0:X1] = ln[None, :]
        V[ya:yb, X0:X1] = (np.arange(ya, yb) - oy - r * h)[:, None]
    ids[~m] = -1
    tid = np.where(ids >= 0, ids, 0)
    hv = _hash_arr(tid, tid // 65536, seed + 3)
    rows_a = np.asarray(rows, np.int64)
    k = base + rows_a[np.clip(V, 0, h - 1)]
    k = k + np.where(hv < vary * 0.7, -1, np.where(hv > 1 - vary * 0.3, 1, 0))
    dist = np.minimum(U, WL - U)
    d = np.zeros_like(U)
    if shape == 'scallop' and h >= 3:
        d[dist == 1] = 1 + ((h >= 5) & (WL >= 7))[dist == 1]
        d[(dist == 2) & (WL >= 7) & (h >= 4)] = 1
    elif shape == 'shake':
        d = np.where(_hash_arr(tid, 7, seed + 4) < 0.3, -1, 0) * np.ones_like(U)
    edge = h - 1 - np.maximum(d, 0)
    lit_m = (V == edge) & (U > 0)
    k = np.where(lit_m, base + rows_a[-1] + (k - base - rows_a[np.clip(V, 0, h - 1)]), k)
    dark = (U == 0) | (V > edge)
    k = np.where(dark, base + seam, k)
    names = _names(ramp, steps)
    c.g[m] = names[np.clip(k, 0, steps - 1)][m]
    # shakes that hang 1 px: their lit edge drops over the shadow row of the course below
    if shape == 'shake':
        drop = m & lit_m & (d < 0) & (V == h - 1)
        below = morph.shift(drop, 0, 1, False) & m
        c.g[below] = morph.shift(c.g, 0, 1, None)[below]
        c.g[drop] = names[min(steps - 1, max(0, base))]
    under = under if under is not None else names[0]
    lath = names[min(steps - 1, 1)]
    hs = _hash_arr(tid, 11, seed + 5)
    holes = m & (hs < missing) & (V >= 0)
    c.g[holes] = under
    if h >= 4:
        c.g[holes & (V == h // 2)] = lath
    for t_ in np.unique(ids[m & (hs >= missing) & (hs < missing + slipped)]):
        tm = (ids == t_)
        moved = morph.shift(tm, 0, 1, False) & m
        src = morph.shift(c.g, 0, 1, None)
        c.g[moved] = src[moved]
        c.g[tm & ~moved] = under
    if moss > 0:
        shade = m & ((V <= 0) | (U <= 0) | (V > edge))
        _moss(c, m & ~holes, shade & ~holes, lit_m, moss, moss_ramp, moss_cell, seed, steps)
    return ids

def planks(c, mask=None, ramp='wood', width=5, length=(16, 36), base=3, vertical=False, gap=1,
           lit=1, seam=-2, grain=0.45, knots=0.12, short=0.1, replaced=0.06, replaced_ramp=None,
           replaced_step=1, vary=0.15, nails=False, battens=False, light=(-0.45, -0.89),
           origin=None, seed=0, steps=7):
    """plank walls, floors, decks and doors: boards `width` px across (gap px of them the dark
    seam) cut into hashed lengths with 1 px butt joints staggered board to board, a lit edge
    row on the side facing the light, short 2-4 px grain ticks one step down, the odd knot (a
    dark pair with softer ends) (07 Stardew floors and fences, 10 cabin walls, 09 Katana ZERO
    panelling: flat boards, edge light only). vertical=True stands the boards up (lit column on
    the light's side). A `short` share of boards is cut short; a `replaced` share is newer wood
    (replaced_ramp, else replaced_step steps lighter) with less grain; vary shifts a share one
    step. nails puts a nail head 2 px in from each joint; battens (board-and-batten) lays a
    2 px batten over every seam with a cast shadow on the far side. Returns the board id map."""
    m = _mask(c, mask)
    ids = np.full((c.H, c.W), -1, np.int64)
    if not m.any():
        return ids
    X0, X1, Y0, Y1, ox, oy = _span(m, origin)
    width, gap = int(width), max(0, int(gap))
    A = np.zeros((c.H, c.W), np.int64); L = np.ones((c.H, c.W), np.int64)
    B = np.zeros((c.H, c.W), np.int64)
    lo, hi = (length, length) if not isinstance(length, (tuple, list)) else length
    if vertical:
        a0, a1, b0, b1, oa, ob = Y0, Y1, X0, X1, oy, ox
    else:
        a0, a1, b0, b1, oa, ob = X0, X1, Y0, Y1, ox, oy
    for j in range((b0 - ob) // width, (b1 - 1 - ob) // width + 1):
        def fn(k, j=j):
            n = lo + int(_hash(k, j, seed + 1) * (hi - lo + 1))
            return max(4, n // 2 - 1) if _hash(k, j, seed + 2) < short else n
        start = -int(_hash(j, 0, seed + 3) * lo)
        idx, off, ln = _runs(a0 - oa, a1 - a0, fn, start)
        ba, bb_ = max(b0, ob + j * width), min(b1, ob + (j + 1) * width)
        if bb_ <= ba:
            continue
        bs = (np.arange(ba, bb_) - ob - j * width)
        sid = (j + 4096) * 65536 + (idx + 32768)
        if vertical:
            ids[a0:a1, ba:bb_] = sid[:, None]; A[a0:a1, ba:bb_] = off[:, None]
            L[a0:a1, ba:bb_] = ln[:, None]; B[a0:a1, ba:bb_] = bs[None, :]
        else:
            ids[ba:bb_, a0:a1] = sid[None, :]; A[ba:bb_, a0:a1] = off[None, :]
            L[ba:bb_, a0:a1] = ln[None, :]; B[ba:bb_, a0:a1] = bs[:, None]
    ids[~m] = -1
    sid = np.where(ids >= 0, ids, 0)
    face = width - gap                                    # board face px across
    toward = (light[0] if vertical else light[1]) < 0     # light on the low-b side
    Bf = B if toward else (face - 1 - B)                  # 0 = the lit edge, gap rows stay >= face
    Bf = np.where(B >= face, B, Bf)
    hv = _hash_arr(sid, 1, seed + 4)
    new = _hash_arr(sid, 2, seed + 5) < replaced
    k = base + np.where(new, 0, np.where(hv < vary * 0.6, -1, np.where(hv > 1 - vary * 0.4, 1, 0)))
    k = np.where(new & (replaced_ramp is None), k + replaced_step, k)
    body = (B < face) & (Bf > 0) & (A > 0)
    # knots: a dark pair with a softer pixel each side, mid board, grain cleared around it
    kmid = max(1, face // 2)
    kp = 3 + (_hash_arr(sid, 3, seed + 8) * np.maximum(1, L - 8)).astype(np.int64)
    hasknot = (_hash_arr(sid, 4, seed + 9) < knots) & (L >= 10) & (face >= 3) & (B < face)
    onrow = hasknot & (Bf == kmid)
    near = hasknot & (np.abs(Bf - kmid) <= 1) & (A >= kp - 3) & (A <= kp + 4)
    # grain ticks: 2-4 px, at most one per 7 px cell per row (so ticks never touch end to end),
    # cells staggered 3 px row to row and only every other cell per row
    q = A + 3 * Bf
    cell = q // 7
    ht = _hash_arr(sid * 31 + Bf, cell, seed + 6)
    s0 = 1 + (_hash_arr(sid * 31 + Bf, cell, seed + 7) * 2).astype(np.int64)
    tl = 2 + (_hash_arr(sid * 31 + Bf, cell, seed + 10) * 3).astype(np.int64)
    gdens = np.where(new, grain * 0.3, grain)
    tick = (body & (ht < gdens) & (q % 7 >= s0) & (q % 7 < s0 + tl) & (A < L - 1)
            & ((Bf + cell) % 2 == 0) & ~near)
    k = np.where(tick, k - 1, k)
    kb = k
    k = np.where(onrow & ((A == kp) | (A == kp + 1)), kb - 2, k)
    k = np.where(onrow & ((A == kp - 1) | (A == kp + 2)), kb - 1, k)
    if face >= 6:
        k = np.where(hasknot & (Bf == kmid - 1) & ((A == kp) | (A == kp + 1)), kb - 1, k)
    k = np.where((Bf == 0) & (B < face), k + lit, k)
    k = np.where(B >= face, base + seam, k)                # the seam between boards
    k = np.where((A == 0) & (B < face), base + seam, k)    # butt joints
    if nails and face >= 3:
        nail = (B < face) & (Bf == kmid) & ((A == 2) | (A == L - 2)) & (L >= 8)
        k = np.where(nail, base - 2, k)
    names = _names(ramp, steps)
    kk = np.clip(k, 0, steps - 1)
    c.g[m] = names[kk][m]
    if replaced_ramp is not None:
        rn = _names(replaced_ramp, steps)
        sel = m & new
        c.g[sel] = rn[kk][sel]
    if battens and width >= 4:
        # a 2 px batten over each seam (the seam px and the next board's first px), lit on the
        # light's side, and a 1 px cast shadow on the board beside it on the far side
        lo_c, hi_c = (B == width - 1), (B == 0)
        bat = m & (lo_c | hi_c)
        bk = np.where(lo_c if toward else hi_c, base + lit, base)
        c.g[bat] = names[np.clip(bk, 0, steps - 1)][bat]
        shadow = m & ((B == 1) if toward else (B == width - 2))
        c.g[shadow] = names[max(0, base - 2)]
    return ids

def thatch(c, mask=None, ramp='straw', course=5, base=3, fringe=(0, 2), strokes=0.45, moss=0.0,
           moss_ramp='moss', moss_cell=14, origin=None, seed=0, steps=7):
    """thatch: courses of straw laid bottom first, each hanging over the one below with a ragged
    lit fringe (clumps of 2-3 straws share a drop of fringe px) and a 1 px shadow under it,
    vertical straw strokes one step down every other column (study 07 cottage roofs: coursed,
    edge-lit, no per-straw noise). moss > 0 adds moss_ramp patches in the shadow rows.
    Returns the course index map (-1 outside)."""
    m = _mask(c, mask)
    ids = np.full((c.H, c.W), -1, np.int64)
    if not m.any():
        return ids
    X0, X1, Y0, Y1, ox, oy = _span(m, origin)
    course = int(course)
    names = _names(ramp, steps)
    K = np.full((c.H, c.W), base, np.int64)
    shade = np.zeros((c.H, c.W), bool); litm = np.zeros((c.H, c.W), bool)
    xs = np.arange(X0, X1)
    r0, r1 = (Y0 - oy) // course, (Y1 - 1 - oy) // course
    for r in range(r1, r0 - 1, -1):                       # bottom course first
        cy0 = oy + r * course
        idx, off, ln = _runs(X0 - ox, X1 - X0, lambda k, r=r: 2 + int(_hash(k, r, seed + 1) * 2),
                             -int(_hash(r, 1, seed + 2) * 2))
        f = fringe[0] + (_hash_arr(idx, r, seed + 3) * (fringe[1] - fringe[0] + 1)).astype(np.int64)
        bottom = cy0 + course - 1 + f
        sk = (_hash_arr(xs, r, seed + 4) < strokes) & ((xs + r) % 2 == 0)
        slen = 2 + (_hash_arr(xs, r, seed + 5) * 2).astype(np.int64)
        for i, x in enumerate(xs.tolist()):
            ya, yb = max(0, cy0), min(c.H, int(bottom[i]) + 1)
            if yb <= ya:
                continue
            col = np.full(yb - ya, base, np.int64)
            if sk[i]:
                s0 = max(0, (yb - ya) - 1 - int(slen[i]))
                col[s0:(yb - ya) - 1] = base - 1
            col[-1] = base + 1
            K[ya:yb, x] = col
            ids[ya:yb, x] = r
            shade[ya:yb, x] = False; litm[ya:yb, x] = False
            litm[yb - 1, x] = True
            if yb < c.H:
                K[yb, x] = base - 2
                shade[yb, x] = True
                litm[yb, x] = False
    ids[~m] = -1
    c.g[m] = names[np.clip(K, 0, steps - 1)][m]
    if moss > 0:
        _moss(c, m, m & shade, m & litm, moss, moss_ramp, moss_cell, seed, steps)
    return ids

# ---------------------------------------------------------------- iso faces
def iso_face(c, mask, fn, face='left', *args, **kw):
    """paint any screen-aligned texture (planks, bricks, shingles, ashlar shading) onto a 2:1 iso
    wall face: the face's pixels are un-sheared into a flat strip (each column moves 1 px per
    2 px across), fn paints the strip, and the result is sheared back, so courses and boards run
    along the face's 2:1 slope while vertical joints stay vertical. face 'left': the face that
    falls to the right, 1 px down per 2 across (iso.Iso's y face, its "left" face); 'right': the
    one that rises to the right (the x face). fn is called as fn(strip, *args, mask=strip_mask, **kw) when it takes a
    mask (planks), else as fn(strip, x0, y0, x1, y1, *args, **kw) over the strip's box (bricks);
    only the face's own pixels change. Returns fn's id map sheared back when it returns one.

        tx.iso_face(c, wall_y_face, tx.planks, 'left', ramp='wood', width=4)
        tx.iso_face(c, wall_x_face, tx.bricks, 'right', 'brick', size=(8, 4))"""
    import inspect
    import canvas as _cv
    m = _mask(c, mask)
    if not m.any():
        return None
    if face not in ('left', 'right'):
        raise ValueError("face is 'left' or 'right', got %r" % (face,))
    sgn = 1 if face == 'left' else -1
    xs = np.nonzero(m.any(0))[0]
    xr = int(xs[0])
    cols = np.arange(c.W)
    shift = sgn * ((cols - xr) // 2)                       # screen row = strip row + shift - pad
    pad = int(max(0, shift.max()))
    Hs = c.H + pad + int(max(0, -shift.min()))
    yy = np.arange(Hs)[:, None] - pad + shift[None, :]     # the screen row of every strip pixel
    ok = (yy >= 0) & (yy < c.H)
    yc = np.clip(yy, 0, c.H - 1)
    xx = np.broadcast_to(cols[None, :], yy.shape)
    strip = _cv.Canvas(c.W, Hs)
    strip.g[ok] = c.g[yc[ok], xx[ok]]
    sm = np.zeros((Hs, c.W), bool)
    sm[ok] = m[yc[ok], xx[ok]]
    try:
        takes_mask = 'mask' in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        takes_mask = True
    if takes_mask:
        res = fn(strip, *args, mask=sm, **kw)
    else:
        ys_, xs_ = np.nonzero(sm)
        before = strip.g.copy()
        res = fn(strip, int(xs_.min()), int(ys_.min()), int(xs_.max()) + 1, int(ys_.max()) + 1, *args, **kw)
        strip.g[~sm] = before[~sm]                          # a box painter stays inside the face
    put = ok & sm
    c.g[yc[put], xx[put]] = strip.g[put]
    if isinstance(res, np.ndarray) and res.shape[:2] == (Hs, c.W):
        out = np.full((c.H, c.W), -1, res.dtype)
        out[yc[put], xx[put]] = res[put]
        return out
    return res
