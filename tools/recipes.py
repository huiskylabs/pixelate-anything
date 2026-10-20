"""recipes: composed generators for the parts every scene gets wrong, built from the kit's primitives.

Each recipe draws in the caller's palette slots into a canvas.Canvas (or returns placements), is
deterministic for a seed, and is tested to produce output that `pixelate judge` does not flag for
the failure it exists to avoid. `pixelate library recipes [NAME]` lists catalog pieces that declare a
function in their manifest; it does not inspect imports or prove use:

  Perspective      one- or two-point scaffold on the native grid: receding edges, shrinking repeats, boxes
  rock_face        strata ledges, lit lips, recesses, flakes, frayed edge (not a masonry grid)
  pouring_fall     a waterfall that leaves its lip, curls, widens raggedly and breaks into spray
  cloud_bank       three masses of very different width, flat undersides, lit top tier (no scallop row)
  crowd_vignettes  people as groups with poses and a focus, open ground between (no confetti)

    import canvas, recipes
    c = canvas.Canvas(320, 180)
    rock = recipes.rock_face(c, mask, 'rock', steps=5, light='left', seed=3)
    recipes.pouring_fall(c, 140, 30, 120, w=10, ramp='pool', foam=('foam1', 'foam2'))
    recipes.cloud_bank(c, 20, 300, 60, 'cloud', steps=4)
    p = recipes.Perspective(horizon=96, vps=[(240, 96)])
    for x, y, s in p.repeat((40, 150), 6, gap=0.6): ...      # posts shrinking toward the vanishing point
    groups = recipes.crowd_vignettes((0, 120, 320, 180), [('ring', 7), ('line', 5), ('cluster', 4)])
"""
import math

import numpy as np

import morph
import shapes
import texture
import water

BAYER4 = np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4)

def _h(a, b=0, s=0):
    """a hash in [0, 1)"""
    x = (int(a) * 73856093) ^ (int(b) * 19349663) ^ (int(s) * 83492791) ^ 0x5bd1e995
    x = (x ^ (x >> 13)) * 0x5bd1e995 & 0xffffffff
    return ((x ^ (x >> 15)) & 0xffffff) / float(0x1000000)

def _slot(ramp, k, steps):
    return '%s%d' % (ramp, max(0, min(steps - 1, int(k))))

def _put(c, m, v):
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        c.g[y][x] = v

def _runs1(n, lo, hi, amp, seed):
    """an integer offset per index that holds for runs of lo..hi and steps by up to amp (flat runs
    joined by 1 px steps: how a hand-drawn edge walks)"""
    out = np.zeros(n, int)
    i, k, v = 0, 0, 0
    while i < n:
        run = lo + int((hi - lo + 1) * _h(k, 1, seed))
        out[i:i + run] = v
        i += run
        v = max(-amp, min(amp, v + (1 if _h(k, 2, seed) < 0.5 else -1)))
        k += 1
    return out

# ---------------------------------------------------------------- perspective
class Perspective:
    """a one- or two-point perspective scaffold in screen space on the native grid.

    horizon: the eye-level row. vps: one or two vanishing points (x, y), usually on the horizon.
    Points move toward a vanishing point by a screen fraction t (0 at the point you start from,
    1 at the vanishing point). repeat() spaces equal world steps the way depth spaces them, so
    windows, posts and paving shrink correctly; edge() draws a hand-stepped receding line."""

    def __init__(self, horizon, vps):
        self.horizon = int(horizon)
        self.vps = [(float(x), float(y)) for x, y in vps]
        if not 1 <= len(self.vps) <= 2:
            raise ValueError('one or two vanishing points')

    def toward(self, p, t, vp=0):
        vx, vy = self.vps[vp]
        return (int(round(p[0] + (vx - p[0]) * t)), int(round(p[1] + (vy - p[1]) * t)))

    @staticmethod
    def depth_t(k, gap=1.0, start=1.0):
        """screen fraction toward the vanishing point of the k-th equal world step (start = distance
        of the first one, in the same units as gap)"""
        return 1.0 - start / (start + k * gap)

    def repeat(self, p, n, gap=1.0, start=1.0, vp=0):
        """n points from p toward a vanishing point at equal world spacing: [(x, y, scale)], scale
        1 at p, shrinking with distance (multiply a unit's size by it)"""
        out = []
        for k in range(n):
            t = self.depth_t(k, gap, start)
            x, y = self.toward(p, t, vp)
            out.append((x, y, start / (start + k * gap)))
        return out

    def edge(self, c, p, t1, slot, vp=0, t0=0.0):
        """a receding edge from toward(p, t0) to toward(p, t1), stepped on the native grid"""
        a, b = self.toward(p, t0, vp), self.toward(p, t1, vp)
        c.line(a[0], a[1], b[0], b[1], slot)
        return a, b

    def box(self, c, x0, y0, x1, y1, t, front, side=None, top=None, vp=0):
        """a block whose front face is the screen rectangle x0..x1, y0..y1 and whose sides recede by
        screen fraction t toward a vanishing point; the side and top faces that face the viewer are
        filled (side/top default to the front slot). Returns the polygons drawn."""
        c.rect(x0, y0, x1, y1, front)
        vx, vy = self.vps[vp]
        polys = []
        sx = x1 if vx > x1 else x0 if vx < x0 else None
        if sx is not None:
            a, b = self.toward((sx, y0), t, vp), self.toward((sx, y1), t, vp)
            poly = [(sx, y0), a, b, (sx, y1)]
            c.poly(poly, side or front)
            polys.append(poly)
        sy = y0 if vy < y0 else y1 if vy > y1 else None
        if sy is not None:
            a, b = self.toward((x0, sy), t, vp), self.toward((x1, sy), t, vp)
            poly = [(x0, sy), (x1, sy), b, a]
            c.poly(poly, top or front)
            polys.append(poly)
        c.rect(x0, y0, x1, y1, front)          # the front face stays on top
        return polys

# ---------------------------------------------------------------- rock
def rock_face(c, mask, ramp, steps=5, light='left', band=(6, 15), lip_cover=0.6, recess=0.5, flake=True,
              fray=True, seed=0):
    """paint a rock, cliff or quarry face inside mask as strata, never as a masonry grid.

    Bands of uneven thickness (band px) alternate between the base tone and one step darker by hash.
    Each band has a top lip one step lighter (two on the light side) that runs for only part of the
    width (lip_cover), walking in 1 px steps, and under the lip runs that overhang (recess) a row one
    step darker. The face is a step lighter along the edge facing the light, sparse flakes
    (texture.flakes) add stacked dashes, and the silhouette is frayed (shapes.fray): teeth and
    notches both in the darkest steps, so nothing transparent opens in the face.
    Slots: ramp0..ramp<steps-1>, base = steps // 2. Returns the final mask."""
    m = np.asarray(mask, bool).copy()
    H, W = m.shape
    base = steps // 2
    _put(c, m, _slot(ramp, base, steps))
    ys = np.flatnonzero(m.any(axis=1))
    if not len(ys):
        return m
    y, k = int(ys[0]), 0
    while y < ys[-1]:                              # strata tones
        th = band[0] + int((band[1] - band[0] + 1) * _h(k, 7, seed))
        if _h(k, 8, seed) < 0.35:
            _put(c, m & (np.arange(H)[:, None] >= y) & (np.arange(H)[:, None] < y + th), _slot(ramp, base - 1, steps))
        y += th
        k += 1
    lit_dx = -1 if light == 'left' else 1 if light == 'right' else 0
    if lit_dx:                                    # the edge that faces the light
        edge = m & ~morph.shift(m, -lit_dx, 0)
        _put(c, morph.dilate(edge, 2) & m, _slot(ramp, base + 1, steps))
    y, k = int(ys[0]) + 3, 0
    while y < ys[-1] - 1:                          # lips and recesses
        th = band[0] + int((band[1] - band[0] + 1) * _h(k, 9, seed))
        off = _runs1(W, 6, 18, 1, seed * 31 + k)
        for x in range(W):
            if _h(x // 9, k, seed + 1) > lip_cover:
                continue
            yb = y + off[x]
            if not (0 <= yb < H and m[yb, x]) or (yb > 0 and not m[yb - 1, x]):
                continue
            lit = base + 1 + (1 if (lit_dx < 0 and x < W * 0.4) or (lit_dx > 0 and x > W * 0.6) else 0)
            c.g[yb][x] = _slot(ramp, lit, steps)
            if _h(x // 7, k, seed + 3) < recess and yb + 1 < H and m[yb + 1, x]:
                c.g[yb + 1][x] = _slot(ramp, base - 2, steps)
        y += th
        k += 1
    if flake:
        texture.flakes(c, morph.erode(m, 1), ramp, base=base, cell=(16, 8), cluster=0.6, gate=0.97, steps=steps,
                       seed=seed)
    if fray:
        new = shapes.fray(m, teeth=0.16, notches=0.1, islands=0.03, depth=2, seed=seed)
        _put(c, new & ~m, _slot(ramp, base - 1, steps))
        _put(c, m & ~new, _slot(ramp, 0, steps))
        m = new | m
    return m

# ---------------------------------------------------------------- water
def pouring_fall(c, x0, lip_y, base_y, w=8, ramp='pool', steps=8, foam=('foam1', 'foam2'), widen=1.2,
                 streaks=4, spray=True, curl=True, t=0, T=None, seed=0):
    """a waterfall that pours: water.waterfall for the falling body, then a forward curl over the lip
    (a lit row one px above and wider than the lip), sides that step out unevenly as it drops
    (widen = extra width at the base as a fraction of w, walked in runs, never a straight taper),
    a few detached streak pixels beside it and a dithered spray cloud wider than the fall at its foot.
    Slots: ramp0..ramp<steps-1> and the two foam slots. Returns the bounding box (x0, y0, x1, y1)."""
    lip_y, base_y, x0, w = int(lip_y), int(base_y), int(x0), int(w)
    water.waterfall(c, x0, lip_y, base_y, w=w, ramp=ramp, steps=steps, foam=foam, t=t, T=T, seed=seed)
    H, Wc = c.H, c.W
    top = steps - 1
    put = lambda x, y, v: (0 <= x < Wc and 0 <= y < H) and c.g[y].__setitem__(x, v)
    if curl:
        for x in range(x0 - 1, x0 + w + 1):
            put(x, lip_y - 1, _slot(ramp, top, steps))
        put(x0 - 2, lip_y, _slot(ramp, top - 1, steps))
        put(x0 + w + 1, lip_y, _slot(ramp, top - 1, steps))
    n = max(1, base_y - lip_y)
    jl = _runs1(n, 3, 7, 1, seed + 11)
    jr = _runs1(n, 3, 7, 1, seed + 23)
    xl, xr = x0, x0 + w - 1
    for i in range(n):
        y = lip_y + 1 + i
        f = (i / float(n)) ** 0.75                 # it spreads early, then falls straighter
        el = max(0, int(round(widen * w * 0.5 * f + jl[i] * f)))
        er = max(0, int(round(widen * w * 0.5 * f + jr[i] * f)))
        for d in range(1, el + 1):
            put(xl - d, y, _slot(ramp, top - 2 - (d % 2), steps))
        for d in range(1, er + 1):
            put(xr + d, y, _slot(ramp, top - 3 + (d % 2), steps))
        if i == n - 1:
            xl, xr = xl - el, xr + er
    for s in range(streaks):
        side = -1 if _h(s, 1, seed) < 0.5 else 1
        y = lip_y + 4 + int((n - 8) * _h(s, 2, seed)) if n > 12 else lip_y + 2
        f = ((y - lip_y) / float(n)) ** 0.75
        gap = 2 + int(2 * _h(s, 3, seed))
        x = (x0 - int(widen * w * 0.5 * f) - gap) if side < 0 else (x0 + w - 1 + int(widen * w * 0.5 * f) + gap)
        for d in range(2 + int(3 * _h(s, 4, seed))):
            put(x, y + d, _slot(ramp, top - 2, steps))
    bx0, bx1 = xl, xr
    if spray:
        cx, rx, ry = (xl + xr) / 2.0, (xr - xl + 1) * 0.95 + 3, 5.0
        for yy in range(int(base_y - ry), int(base_y + ry) + 1):
            for xx in range(int(cx - rx), int(cx + rx) + 1):
                d = ((xx - cx) / rx) ** 2 + ((yy - base_y) / ry) ** 2
                if d <= 1 and (1 - d) * 16 > BAYER4[yy % 4, xx % 4] + 3:
                    put(xx, yy, foam[1] if d < 0.35 else foam[0])
        bx0, bx1 = int(cx - rx), int(cx + rx)
    return (bx0, lip_y - 1, bx1, int(base_y + 4))

# ---------------------------------------------------------------- clouds
def cloud_bank(c, x0, x1, base_y, ramp='cloud', steps=4, widths=(0.55, 0.28, 0.16), height=0.42, tiers=2, seed=0):
    """three cloud masses of very different width (widths of x1 - x0) that overlap, each with a flat
    underside a few px apart, a lit top tier (`tiers` rows, the top steps) and a darker belly row.
    Lobes come from shapes.cloud_mask with full variation, so the top is a few big heads and small
    ones, not a row of equal bumps. Smallest and farthest first; the big mass is in front.
    Slots: ramp0..ramp<steps-1>. Returns the union mask."""
    H, W = c.H, c.W
    span = float(x1 - x0)
    yy = np.mgrid[0:H, 0:W][0]
    order = sorted(range(len(widths)), key=lambda i: widths[i])
    centres = [0.38, 0.8, 0.07, 0.6, 0.25]
    union = np.zeros((H, W), bool)
    for rank, i in enumerate(order):
        f = widths[i]
        rx = max(4.0, f * span / 2)
        ry = max(3.0, rx * height * (0.85 + 0.3 * _h(i, 5, seed)))
        cx = x0 + span * centres[i % len(centres)]
        base = int(base_y) - 2 * (len(order) - 1 - rank) - int(2 * _h(i, 6, seed))
        cy = base - ry * 0.45
        lo = max(2.5, rx * 0.16)
        m = shapes.cloud_mask((H, W), cx, cy, rx, ry, r=(lo, max(lo + 2, rx * 0.4)), spacing=9, belly=0,
                              seed=seed * 7 + i, vary=1.0)
        m &= yy <= base
        m = morph.close(m, 1)
        _put(c, m, _slot(ramp, 1, steps))
        edge1 = m & ~morph.shift(m, 0, 1)
        edge2 = m & ~morph.shift(m, 0, 2) & ~edge1
        _put(c, edge2 if tiers > 1 else np.zeros_like(m), _slot(ramp, steps - 2, steps))
        _put(c, edge1, _slot(ramp, steps - 1, steps))
        belly = m & (yy >= base - 1)
        _put(c, belly, _slot(ramp, 0, steps))
        union |= m
    return union

# ---------------------------------------------------------------- crowds
def crowd_vignettes(box, groups, poses=4, min_gap=6, seed=0, tries=400):
    """place people as small scenes rather than confetti.

    box: (x0, y0, x1, y1) of the ground they stand on. groups: a list of (kind, n) with kind
    'ring' (people facing a centre: a juggler, a musician), 'line' (a queue or procession, all facing
    one way) or 'cluster' (a loose chat). Group centres keep min_gap px of open ground between them;
    each group uses at least min(3, poses) poses and no two neighbours share one. Returns
    [{'kind', 'focus': (x, y), 'members': [{'x', 'y', 'pose', 'face'}]}] with face -1 (left) or 1
    (right); draw your own sprites at those feet positions, back to front by y."""
    x0, y0, x1, y1 = box
    rng = np.random.default_rng(seed)
    placed = []
    for gi, (kind, n) in enumerate(groups):
        n = int(n)
        r = {'ring': 2.5 + 0.9 * n, 'line': 1.8 * n, 'cluster': 2.0 + 0.6 * n}.get(kind)
        if r is None:
            raise ValueError("kind must be 'ring', 'line' or 'cluster'")
        for _ in range(tries):
            cx = rng.uniform(x0 + r, max(x0 + r + 1, x1 - r))
            cy = rng.uniform(y0 + r * 0.5, max(y0 + r * 0.5 + 1, y1 - r * 0.5))
            if all(math.hypot(cx - g['focus'][0], (cy - g['focus'][1]) * 1.6) >= r + g['_r'] + min_gap for g in placed):
                break
        else:
            raise ValueError('no room for group %d (%s of %d): enlarge the box or lower min_gap' % (gi, kind, n))
        members = []
        if kind == 'ring':
            a0 = rng.uniform(0, 2 * math.pi)
            for k in range(n):
                a = a0 + 2 * math.pi * k / n + rng.uniform(-0.25, 0.25)
                x, y = cx + r * math.cos(a), cy + 0.55 * r * math.sin(a)
                members.append((x, y, 1 if x < cx else -1))
        elif kind == 'line':
            ang = rng.uniform(-0.35, 0.35)
            face = 1 if rng.uniform() < 0.5 else -1
            for k in range(n):
                d = (k - (n - 1) / 2) * (3.2 + rng.uniform(-0.6, 0.9))
                members.append((cx + d * math.cos(ang), cy + d * math.sin(ang) + rng.uniform(-0.6, 0.6), face))
        else:
            for k in range(n):
                a, d = rng.uniform(0, 2 * math.pi), r * math.sqrt(rng.uniform(0.15, 1))
                x, y = cx + d * math.cos(a), cy + 0.6 * d * math.sin(a)
                members.append((x, y, 1 if x < cx else -1))
        members.sort(key=lambda m: m[0])
        want = min(3, poses)
        order = list(rng.permutation(poses))
        out, last = [], None
        for k, (x, y, face) in enumerate(members):
            pose = int(order[k % poses]) if k < want else int(rng.integers(poses))
            if pose == last:
                pose = (pose + 1) % poses
            last = pose
            out.append({'x': int(round(x)), 'y': int(round(y)), 'pose': pose, 'face': int(face)})
        placed.append({'kind': kind, 'focus': (int(round(cx)), int(round(cy))), 'members': out, '_r': r})
    for g in placed:
        g.pop('_r')
    return placed
