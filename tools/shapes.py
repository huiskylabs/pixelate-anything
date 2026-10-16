"""Shape makers for painted scenes: flat cloud masses, translucent cumulus sprites, lobe chains and
edge shaping (fray, ledges, noisy edges, void crowns). Every shape is a pure function of its
arguments and a seed; nothing is hand-placed pixel by pixel.

    import shapes
    m = shapes.cloud_mass(c, 260, 48, 52, 30, 'cl', back='rock1', seed=3)   # Celeste flat cloud (02)
    slots, alpha = shapes.cloud(seed=4, size=(150, 100))                    # Sea of Stars cumulus (04)
    shapes.paste_cloud(c, slots, alpha, 40, 20)                             # onto a slot canvas
    shapes.lobes_along(c, [(60, 10), (64, 120)], (6, 12), 'far', base=2)    # Owlboy far cliff (08)
    rock = shapes.fray(rock, seed=2)                                        # teeth, notches, islands (02)
    xe = shapes.ledges(0, 180, 170, seed=5)                                 # a stepped cliff face (02)
    pts = shapes.noisy_edge([(52, 0), (52, 270)], amp=8, wavelength=28)     # displaced polyline (08)
    shapes.void_edge(c, room, 'rock', side='top')                           # checker wall crown (10)
    c.fill(shapes.ray((180, 320), 200, 0, angle=110, length=170, width=(6, 22)), 'sky4')   # a stepped ray in a slot

Conventions: native art pixels, y down, slots are BASE + step (rock0 darkest). Masks are H x W
bool arrays. Pixels are filled on their centres: a disc holds (x + .5 - cx)^2 + (y + .5 - cy)^2
<= (r + .15)^2 (the same test as Canvas.disc). Randomness only from the integer hash below.

The small helpers at the top (hash, value noise, ramp stepping) are shared by sky.py, veg.py
and water.py.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph

# ---------------------------------------------------------------- shared helpers
def _h(a, b=0, s=0):
    """integer hash of (a, b, seed) -> floats in [0, 1) (the hash of iso.hash2, vectorised)"""
    a = np.asarray(a).astype(np.int64)
    b = np.asarray(b).astype(np.int64)
    h = (a * 374761393 + b * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _hs(a, b=0, s=0):
    """scalar _h"""
    return float(_h(int(a), int(b), s))

def vnoise1(x, cell, seed=0, period=None):
    """1D smoothstep value noise in [-1, 1] at positions x; repeats every `period` px when given
    (the cell is nudged so a whole number of cells fits)"""
    x = np.asarray(x, float)
    if period:
        n = max(1, int(round(period / cell)))
        cell = period / n
    u = x / cell
    i = np.floor(u).astype(np.int64)
    f = u - i
    f = f * f * (3 - 2 * f)
    a, b = i, i + 1
    if period:
        a, b = a % n, b % n
    va, vb = _h(a, 0, seed) * 2 - 1, _h(b, 0, seed) * 2 - 1
    return va + (vb - va) * f

def vnoise2(shape, cell, seed=0, wrap=True, x0=0, y0=0):
    """2D smoothstep value noise in [-1, 1] over an H x W block. wrap=True makes it tile with the
    block (the cell is nudged so whole cells fit both ways): a drifting layer then loops."""
    H, W = shape
    cx = W / max(1, round(W / cell)) if wrap else cell
    cy = H / max(1, round(H / cell)) if wrap else cell
    nx, ny = int(round(W / cx)), int(round(H / cy))
    u = (np.arange(W) + x0) / cx
    v = (np.arange(H) + y0) / cy
    iu, iv = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fu, fv = u - iu, v - iv
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    def lat(i, j):
        if wrap:
            i, j = i % nx, j % ny
        return _h(i[None, :], j[:, None], seed) * 2 - 1
    a, b = lat(iu, iv), lat(iu + 1, iv)
    c, d = lat(iu, iv + 1), lat(iu + 1, iv + 1)
    top = a + (b - a) * fu[None, :]
    bot = c + (d - c) * fu[None, :]
    return top + (bot - top) * fv[:, None]

def split(slot):
    """'rock3' -> ('rock', 3); 'eye' -> ('eye', None)"""
    s = str(slot)
    base = s.rstrip('0123456789')
    return (base, int(s[len(base):])) if base != s and not s.startswith('#') else (s, None)

def step(slot, k, n=None):
    """'rock3', -1 -> 'rock2', clamped to 0 .. n-1 (n=None: only clamped at 0)"""
    b, i = split(slot)
    if i is None:
        return slot
    j = max(0, i + int(k))
    if n is not None:
        j = min(n - 1, j)
    return '%s%d' % (b, j)

def _grid(c):
    return c.g if hasattr(c, 'g') else c

def _disc_mask(H, W, cx, cy, r, sy=1.0):
    """bool H x W mask of an (optionally squashed) disc on pixel centres"""
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    rr = r + 0.15
    return (xx - cx) ** 2 + ((yy - cy) / sy) ** 2 <= rr * rr

def _bbox(H, W, cx, cy, rx, ry):
    x0, x1 = max(0, int(math.floor(cx - rx - 1))), min(W, int(math.ceil(cx + rx + 1)) + 1)
    y0, y1 = max(0, int(math.floor(cy - ry - 1))), min(H, int(math.ceil(cy + ry + 1)) + 1)
    return x0, y0, x1, y1

# ---------------------------------------------------------------- flat cloud masses (02)
def cloud_mask(shape, cx, cy, rx, ry, r=(5, 13), spacing=9, belly=3, seed=0, vary=1.0):
    """the silhouette of a flat cloud mass: a filled ellipse core plus a disc on every `spacing`
    px of perimeter per 9 px of lobe radius (about 1.7 r apart: distinct bumps), r from
    r=(lo, hi) by hash and `belly` px bigger on the lower half, so the bottom is the heavier
    scalloped row. Without the core, random discs read as bubbles.
    vary (0..1, default 1): how uneven the lobes are, by seed. At 1 about a quarter of the lobes
    are billows up to 1.6x and a third are small ones down to 0.65x, the lobes on top grow up
    to 1.45x more (a crown), the gaps run from tight clusters to 2x the even step and the lobes
    stand proud by up to 0.7 r, so the edge reads as
    one mass with a few big heads instead of a row of equal bubbles. vary=0 is the older even
    row, pixel for pixel."""
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    m = ((xx - cx) / (0.92 * rx)) ** 2 + ((yy - cy) / (0.92 * ry)) ** 2 <= 1
    per = math.pi * (3 * (rx + ry) - math.sqrt((3 * rx + ry) * (rx + 3 * ry)))
    a, i = 0.0, 0
    a0 = 2 * math.pi * _hs(0, 9, seed)
    while a < 2 * math.pi - 1e-6:
        ang = a0 + a
        px, py = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
        rad = r[0] + (r[1] - r[0]) * _hs(i, 2, seed) ** 0.8 + (belly if math.sin(ang) > 0.15 else 0)
        proud = 0.05 + (0.45 + 0.2 * vary) * _hs(i, 3, seed)     # lobes stand proud of the core, unevenly
        if vary:
            rad0 = rad
            u = _hs(i, 4, seed)
            rad *= 1 + vary * (0.6 * (u - 0.75) / 0.25 if u > 0.75 else -0.35 * (0.33 - u) / 0.33 if u < 0.33 else 0)
            rad *= 1 + 0.45 * vary * max(0.0, -math.sin(ang)) ** 2       # a crown: the heads rise on top
            proud *= min(1.0, rad0 / rad)                                  # a big head sits into the mass
        px += proud * rad * math.cos(ang)
        py += proud * rad * math.sin(ang)
        x0, y0, x1, y1 = _bbox(H, W, px, py, rad, rad)
        if x1 > x0 and y1 > y0:
            sub = (xx[y0:y1, x0:x1] - px) ** 2 + (yy[y0:y1, x0:x1] - py) ** 2 <= (rad + 0.15) ** 2
            m[y0:y1, x0:x1] |= sub
        u = _hs(i, 1, seed)
        step = (0.6 + 0.7 * u) * (1 - vary) + vary * (0.3 + 1.6 * u * u)   # clusters and the odd long gap
        a += 2 * math.pi * (spacing / 9.0) * 1.7 * rad * step / per
        i += 1
    return m

def cloud_mass(c, cx, cy, rx, ry, slot, r=(5, 13), spacing=9, belly=3, fray=0.012, bite=0.06,
               back=None, seed=0, vary=1.0):
    """paint one flat Celeste cloud (02): cloud_mask() in a single slot, no outline, no lobe
    shading (the bloom comes later from this mask). Along its edge, `bite` of the edge pixels
    lose a 1-2 px bite (the back material shows) and, when `back` is a slot, `fray` of them
    (about one per 80 px of edge; at most one per 12 px) drop a chunky 2-5 x 2-3 px crumb of
    `back` 2-4 px inside the cloud (rock torn into it; the reference shows 2-3 per cloud).
    Returns the mask actually painted."""
    g = _grid(c)
    H, W = g.shape
    m = cloud_mask((H, W), cx, cy, rx, ry, r, spacing, belly, seed, vary)   # vary: see cloud_mask
    m = morph.close(m, 1)                              # no 1 px slits where two lobes meet
    m = _fray_edge(m, teeth=0.0, notches=bite, islands=0.0, depth=2, seed=seed + 11)   # the bites
    g[m] = slot
    if back is not None and fray > 0:
        rim = morph.edges(m)
        nx, ny = morph.normals(m)
        ys, xs = np.nonzero(rim)
        pick = _h(xs, ys, seed + 12) < fray
        done = []
        for x, y in zip(xs[pick], ys[pick]):
            if any(abs(x - a) + abs(y - b) < 12 for a, b in done):
                continue
            done.append((x, y))
            dd = 2 + int(3 * _hs(x, y, seed + 13))
            ix = int(round(x - nx[y, x] * dd))
            iy = int(round(y - ny[y, x] * dd))
            w = 2 + int(4 * _hs(x, y, seed + 14))       # a chunky crumb 2-5 wide, 2-3 tall,
            hh = 2 + (_hs(x, y, seed + 15) < 0.4)       # slanted one px per row, corners cut
            sl = 1 if _hs(x, y, seed + 16) < 0.5 else -1
            for j in range(hh):
                a0 = ix - w // 2 + sl * j
                for k in range(w):
                    if (j == 0 and k == w - 1) or (j == hh - 1 and k == 0 and w > 2):
                        continue
                    xx_, yy_ = a0 + k, iy + j
                    if 0 <= xx_ < W and 0 <= yy_ < H and m[yy_, xx_]:
                        g[yy_, xx_] = back
    return m

# ---------------------------------------------------------------- cumulus sprites (04)
def cloud(seed=0, size=(120, 80), lobes=9, radius=(6, 18), tail=None, ramp='cloud', steps=5,
          light=(-0.45, -0.9), checker=2, alpha=(0.88, 0.6), shade=0.35):
    """a lobed Sea of Stars cumulus as a sprite: (slots, alpha), an h x w object grid of
    ramp0..ramp(steps-1) (None outside) and a float grid of opacity.
    The body is a dome over a flat base cut along a 1:2 diagonal (tail['slope']). A back row of
    lobes (radius=(6, 18), biggest in the middle) rides the dome's crest and more lobes fill it;
    they are painted top to bottom, so lower lobes cover upper ones. Each lobe takes three tones
    by height (v = (p - c).light / r, plus `shade` times the same over the whole cloud, so the
    lower right is cooler): lit cap, body, underside; each tone boundary is a
    `checker` px band of a pure 50% checker (the ramp's neighbouring steps must be close, 6-10
    RGB apart). A lobe's lower rim that lands on an earlier lobe is one step darker still (the
    crease that separates the puffs). Wedge tails run along the base diagonal: a trailing sheet
    to the lower right that ends in serrated streaks 1-3 px thick (tail=dict(slope=0.5, n=5,
    length=(25, 60), lead=1)) and `lead` flat sheets tapering to the upper left.
    alpha = (body, outer ring): 0.88 and 0.6. No outline.
    Palette: steps from a cool underside to a warm top within ~0.12 L, e.g.
    ['#93a9b4', '#a2b6bf', '#c4cfd0', '#d8ddd7', '#e1e3da']."""
    W, H = size
    tl = dict(slope=0.5, n=5, length=(25, 60), lead=1)
    tl.update(tail or {})
    top = steps - 1
    t_hi, t_mid, t_lo = top, top - 1, max(1, top - 2)
    rnd = lambda k, j=0: _hs(k, j, seed)
    lx, ly = light
    ln = math.hypot(lx, ly) or 1
    lx, ly = lx / ln, ly / ln
    sl = tl['slope']
    dv = np.array([1.0, sl]) / math.hypot(1.0, sl)        # along the base diagonal
    nv = np.array([-dv[1], dv[0]])                        # its normal (b > 0: below the base)
    bx0, bx1 = 0.24 * W, 0.68 * W                        # margins for the lead and trailing wedges
    cx0, half = 0.5 * (bx0 + bx1), 0.5 * (bx1 - bx0)
    # the base line should leave the sprite near its lower right corner, so the trailing tail
    # has room: a sprite about (1.5 h, h) or taller fits slope 0.5 best
    base_y = max(0.55 * H, min(0.80 * H, H - 2 - sl * (0.95 * W - 0.5 * (bx0 + bx1))))
    P0 = np.array([cx0, base_y])
    base_at = lambda x: base_y + sl * (x - cx0)
    dome = min(0.62 * H, base_y - 2)
    crest = lambda x: base_at(x) - dome * np.sqrt(np.clip(1 - ((x - cx0) / half) ** 2, 0, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    X, Y = xx + 0.5, yy + 0.5
    bcoord = (X - P0[0]) * nv[0] + (Y - P0[1]) * nv[1]
    acoord = (X - P0[0]) * dv[0] + (Y - P0[1]) * dv[1]
    par = ((xx + yy) & 1).astype(bool)
    tone = np.full((H, W), -1, int)
    # lobes: a crest row, then fillers inside the dome
    cen = []
    for i in range(lobes):
        u = (i + 0.5) / lobes
        x = bx0 + 2 * half * u + (rnd(i, 1) - 0.5) * 4
        r = radius[0] + (radius[1] - radius[0]) * (1 - abs(2 * u - 1)) ** 0.8 * (0.75 + 0.25 * rnd(i, 2))
        cen.append((x, crest(x) + 0.85 * r, r))
    nf = lobes
    for j in range(nf):
        x = bx0 + 2 * half * (0.1 + 0.8 * rnd(j, 3))
        y = crest(x) + (base_at(x) - crest(x)) * (0.35 + 0.5 * rnd(j, 4))
        r = radius[0] + (radius[1] - radius[0]) * 0.55 * (0.5 + 0.5 * rnd(j, 5))
        cen.append((x, y, r))
    cen.sort(key=lambda p: p[1])
    core = (Y >= crest(X) + radius[0]) & (bcoord <= 0) & (np.abs(X - cx0) < half * 0.9)
    tone[core] = t_lo
    for k, (x, y, r) in enumerate(cen):
        x0, y0, x1, y1 = _bbox(H, W, x, y, r, r)
        Xs, Ys = X[y0:y1, x0:x1], Y[y0:y1, x0:x1]
        inside = ((Xs - x) ** 2 + (Ys - y) ** 2 <= (r + 0.15) ** 2) & (bcoord[y0:y1, x0:x1] <= 0)
        if not inside.any():
            continue
        v = -((Xs - x) * lx + (Ys - y) * ly) / r          # -1 toward the light .. +1 away
        # the whole-cloud term is constant per lobe (lower right lobes cooler), so tone bands stay
        # concentric arcs on each puff instead of long diagonal stripes across the cloud
        v = v + shade * -((x - cx0) * lx + (y - base_y + dome / 2) * ly) / half
        bw = (checker + 0.5) / r
        P = par[y0:y1, x0:x1]
        t = np.where(v < -0.35, t_hi, np.where(v < 0.2, t_mid, t_lo))
        t = np.where(np.abs(v + 0.35) < bw / 2, np.where(P, t_hi, t_mid), t)
        t = np.where(np.abs(v - 0.2) < bw / 2, np.where(P, t_mid, t_lo), t)
        sub = tone[y0:y1, x0:x1]
        under = inside & (sub >= 0)
        m = np.pad(inside, 1)
        rim = inside & ~(m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
        t = np.where(rim & under & ((Ys - y) / r > 0.3), max(0, t_lo - 1), t)
        sub[inside] = t[inside]
    body = tone >= 0
    sheet = np.zeros((H, W), bool)
    # wedge tails along the base: a flat sheet that tapers to a point, split into layers 2-5 px
    # thick; past `split` of its length the 1 px seams between layers open and each layer ends
    # at its own length in a pointed streak (the serrated end)
    def wedge(a0, sgn, L, thick, n_layers, sd, split=0.45, ragged=0.5):
        along = (acoord - a0) * sgn
        depth = -bcoord - 0.5                             # px above the base line
        u = along / max(1.0, L)
        env = thick * np.clip(1 - u, 0, 1) ** 0.8
        free = tone < 0
        pos, j = 0.0, 0
        while pos < thick and j < max(1, n_layers):
            th = 2 + int(rnd(j, sd) * 4)
            Lj = L if j == 0 else L * (1 - ragged * rnd(j, sd + 1)) * (1 - 0.6 * ragged * (j % 2))
            left = np.clip((Lj - along) / (0.35 * Lj), 0, 1) ** 0.7     # the streak's own taper
            dl = depth - pos
            m = (along >= -thick) & (dl >= 0) & (dl < np.maximum(1, th * left)) & (along <= Lj) \
                & (depth < env + 1) & free
            tone[m] = t_hi if (j % 2 or dl.max() < 0) else t_mid
            sheet[m] = True
            seam = (along >= -thick) & (np.abs(dl - th - 0.5) < 0.5) & (u < split) & (depth < env) & free
            tone[seam] = max(1, t_lo)                     # closed seams: a faint streak line
            sheet[seam] = True
            pos += th + 1
            j += 1
        top = sheet & free & (depth >= env - 1.5) & (u < 0.8)
        tone[top] = t_hi                                  # the sheet's lit upper edge
    if body.any():
        ab = acoord[body & (bcoord > -4)]                 # the body's foot along the base
        if not len(ab):
            ab = acoord[body]
        L = tl['length']
        wedge(ab.max() - 6, +1, L[0] + (L[1] - L[0]) * rnd(1, 40), tl.get('thick', 0.28) * H, tl['n'], 50)
        for i in range(tl.get('lead', 0)):
            wedge(acoord[body].min() + 3 + 6 * i, -1, L[0] + (L[1] - L[0]) * rnd(i, 41),
                  tl.get('lead_thick', 0.25) * H, 8, 60 + i, ragged=0.25)
    slots = np.full((H, W), None, object)
    for v in range(steps):
        slots[tone == v] = '%s%d' % (ramp, v)
    on = tone >= 0
    al = np.where(on, alpha[0], 0.0)
    al[sheet] = 0.5 * (alpha[0] + alpha[1])
    m = np.pad(on, 1)
    ring = on & ~(m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
    al[ring] = alpha[1]
    return slots, al

def paste_cloud(c, slots, alpha, x, y, min_alpha=0.5):
    """a cloud sprite onto a slot canvas at (x, y) where alpha >= min_alpha (opaque: for a
    no-light-layer style; translucency belongs to the native light layer, see cloud_rgba)"""
    g = _grid(c)
    H, W = g.shape
    h, w = slots.shape
    x, y = int(x), int(y)
    sx0, sy0, sx1, sy1 = max(0, -x), max(0, -y), min(w, W - x), min(h, H - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    s = slots[sy0:sy1, sx0:sx1]
    a = alpha[sy0:sy1, sx0:sx1]
    dst = g[y + sy0:y + sy1, x + sx0:x + sx1]
    m = (a >= min_alpha) & ~np.equal(s, None)
    dst[m] = s[m]

def cloud_rgba(slots, alpha, pal):
    """the sprite as an h x w x 4 float array (RGB 0..1, alpha) for compositing over a native-res
    frame: out = base * (1 - a) + rgb * a"""
    h, w = slots.shape
    out = np.zeros((h, w, 4))
    for k in set(slots.ravel()) - {None}:
        hx = pal[k].lstrip('#')
        out[slots == k, :3] = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    out[..., 3] = alpha
    return out

# ---------------------------------------------------------------- lobe chains (08)
def lobes_along(c, path, r=(6, 12), ramp='far', base=2, light=(-0.45, -0.89), crease=True,
                squash=0.85, every=0.8, jitter=4, sides=0.5, seed=0, steps=None):
    """cauliflower lobes along a wobbly spine (Owlboy's far cliffs, 08). Centres every
    `every` * r px along the polyline `path`, pushed sideways by +-jitter px; `sides` of them get
    a smaller side lobe. Drawn lowest first, so each lobe overhangs the one below it. Per lobe:
    body `base`, a cap base + 1 where the normal faces the light (n.l > 0.3) with base + 2 on
    its rim where n.l > 0.55, base - 1 on the side away from it (n.l < -0.6), and a 1 px crease
    on the lower right rim: base - 2 where it sits on a lobe drawn earlier, else base - 1.
    Flat tones, no dither. Returns the union mask."""
    g = _grid(c)
    H, W = g.shape
    pts = np.asarray(path, float).reshape(-1, 2)
    if len(pts) == 1:
        pts = np.vstack([pts, pts])                 # a single point: one lobe there
    seg = np.hypot(*(pts[1:] - pts[:-1]).T)
    total = seg.sum()
    cum = np.concatenate([[0], np.cumsum(seg)])
    def at(s):
        i = min(len(seg) - 1, int(np.searchsorted(cum, s, 'right') - 1))
        f = (s - cum[i]) / max(seg[i], 1e-9)
        p = pts[i] + (pts[i + 1] - pts[i]) * f
        tvec = (pts[i + 1] - pts[i]) / max(seg[i], 1e-9)
        return p, tvec
    lx, ly = light
    ln = math.hypot(lx, ly) or 1
    lx, ly = lx / ln, ly / ln
    clip = (lambda k: max(0, min(steps - 1, k))) if steps else (lambda k: max(0, k))
    # lobe list: one per `every` r along the path, some with a smaller side lobe
    lob = []
    s_, k = 0.0, 0
    while s_ <= total:
        rad = r[0] + (r[1] - r[0]) * _hs(k, 1, seed)
        p, tv = at(s_)
        side = (2 * _hs(k, 2, seed) - 1) * jitter
        cx, cy = p[0] - tv[1] * side, p[1] + tv[0] * side
        if _hs(k, 3, seed) < sides:
            sg = 1 if _hs(k, 4, seed) < 0.5 else -1
            lob.append((cx + sg * 0.8 * rad, cy + 0.3 * rad, rad * 0.65))
        lob.append((cx, cy, rad))
        s_ += max(2.0, every * rad)
        k += 1
    lob.sort(key=lambda q: -(q[1] + q[2]))          # lowest first: upper lobes overhang lower
    union = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    for cx, cy, rad in lob:
        ry = rad * squash
        x0, y0, x1, y1 = _bbox(H, W, cx, cy, rad, ry)
        if x1 <= x0 or y1 <= y0:
            continue
        X, Y = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
        nx, ny = (X - cx) / rad, (Y - cy) / ry
        inside = nx * nx + ny * ny <= ((rad + 0.15) / rad) ** 2
        sub = g[y0:y1, x0:x1]
        ndl = nx * lx + ny * ly
        t = np.full(inside.shape, base)
        t = np.where(ndl > 0.3, base + 1, t)                # the lit cap (upper left)
        t = np.where(ndl < -0.6, base - 1, t)               # the shaded lower right
        m = np.pad(inside, 1)
        t = np.where(inside & ~m[:-2, 1:-1] & (ndl > 0.55), base + 2, t)  # the cap's rim catches the light
        if crease:
            # the underside rim: base - 2 where it sits on a lobe drawn earlier, else base - 1
            low = inside & (~m[2:, 1:-1] | ~m[1:-1, 2:]) & (ny > 0.15) & (nx > -0.5)
            over = union[y0:y1, x0:x1]
            t = np.where(low, np.where(over, base - 2, base - 1), t)
        for v in np.unique(t[inside]):
            sub[inside & (t == v)] = '%s%d' % (ramp, clip(int(v)))
        union[y0:y1, x0:x1] |= inside
    return union

# ---------------------------------------------------------------- edge shaping (D3)
def fray(mask, teeth=0.18, notches=0.12, islands=0.06, depth=2, seed=0, facing=None):
    """roughen a silhouette's micro edge (Celeste terrain, 02). For each pixel just outside the
    edge, by hash, teeth / 2 start a tooth 1-3 px wide that grows 1..depth px outward (so one
    tooth per ~5 px of edge at 0.18); along the rim, notches / 2 start a notch cut inward; `islands` drop a 1-2 px island 2-4 px outside. facing=(dx, dy)
    limits the fraying to the side whose outward normal points that way (n.f > 0.3).
    Returns a new mask."""
    m = np.asarray(mask, bool)
    H, W = m.shape
    out = m.copy()
    nx, ny = morph.normals(m)
    ok = np.ones((H, W), bool)
    if facing is not None:
        fx, fy = facing
        fl = math.hypot(fx, fy) or 1
        ok = (nx * fx + ny * fy) / fl > 0.3
    ring = morph.boundary(m) & ok
    rim = morph.edges(m) & ok
    def feature(band, p, sd, sgn, val):
        """seeds on `band` with probability p / 2, each widened to 1-3 px along the edge and
        pushed 1..depth px along the normal (the whole feature shares its seed's depth)"""
        ys, xs = np.nonzero(band)
        if not len(ys):
            return
        hit = _h(xs, ys, sd) < p / 2.0
        if not hit.any():
            return
        S = np.zeros((H, W), bool)
        S[ys[hit], xs[hit]] = True
        wide = np.zeros((H, W), bool)
        wsel = _h(xs, ys, sd + 1) < 0.6
        wide[ys[hit & wsel], xs[hit & wsel]] = True
        full = S | (morph.dilate(wide, 1) & band)
        sy, sx = morph.nearest(S)
        fy, fx = np.nonzero(full)
        oy, ox = sy[fy, fx], sx[fy, fx]
        n_of = 1 + (_h(ox, oy, sd + 2) * depth).astype(int)
        seed_px = S[fy, fx]
        for k in range(1, depth + 1):
            go = (n_of >= k) & ((k == 1) | seed_px)       # teeth taper: only the seed column goes deeper
            px = np.floor(fx + 0.5 + sgn * nx[fy, fx] * (k - 1)).astype(int)
            py = np.floor(fy + 0.5 + sgn * ny[fy, fx] * (k - 1)).astype(int)
            inb = go & (px >= 0) & (px < W) & (py >= 0) & (py < H)
            out[py[inb], px[inb]] = val
    if teeth > 0:
        feature(ring, teeth, seed + 1, +1, True)
    if notches > 0:
        feature(rim, notches, seed + 3, -1, False)
    if islands > 0:
        ys, xs = np.nonzero(ring)
        pick = _h(xs, ys, seed + 5) < islands
        ys, xs = ys[pick], xs[pick]
        dd = 1 + (_h(xs, ys, seed + 6) * 3).astype(int)        # 2..4 px out from the edge
        px = np.floor(xs + 0.5 + nx[ys, xs] * dd).astype(int)
        py = np.floor(ys + 0.5 + ny[ys, xs] * dd).astype(int)
        two = _h(xs, ys, seed + 7) < 0.5
        for X, Y, t2 in zip(px, py, two):
            for Xi in ((X, X + 1) if t2 else (X,)):
                if 0 <= Xi < W and 0 <= Y < H and not m[Y, Xi]:
                    out[Y, Xi] = True
    return out

def ledges(y0, y1, x_start, step=(6, 20), jog=(2, 8), drift=0.0, lo=None, hi=None, noise=1,
           seed=0):
    """the macro edge of a cliff face as x_e(y) for y in [y0, y1): piecewise constant, with a jog
    of +-jog=(2, 8) px every step=(6, 20) rows (02 cliff, 10 mine walls). drift biases the jogs
    (px per row on average, + = right), lo/hi clamp x, noise adds a +-noise px value-noise wobble (runs of rows).
    Use it as: rock = xx >= xe[:, None] (or <=)."""
    n = int(y1) - int(y0)
    xe = np.zeros(n, float)
    x, i, k = float(x_start), 0, 0
    while i < n:
        run = step[0] + int((step[1] - step[0] + 1) * _hs(k, 1, seed))
        xe[i:i + run] = x
        i += run
        j = jog[0] + int((jog[1] - jog[0] + 1) * _hs(k, 2, seed))
        sgn = 1 if _hs(k, 3, seed) < 0.5 + 0.5 * math.tanh(drift * run / max(1, j)) else -1
        x += sgn * j
        if lo is not None:
            x = max(lo, x)
        if hi is not None:
            x = min(hi, x)
        k += 1
    if noise:                                       # a 1 px value-noise wobble: runs, not per-row jitter
        ys = np.arange(n) + int(y0)
        xe += np.round(noise * 1.4 * vnoise1(ys, 5, seed + 4))
    return np.floor(xe + 0.5).astype(int)

def noisy_edge(pts, amp=8, wavelength=28, seed=0, closed=False, spacing=1.0, period=None):
    """a polyline displaced along its normal by amp * (0.6 vn(s / wavelength) + 0.4 vn(s / 10)),
    s the arc length (Owlboy's frame edge: amp 8, wavelength 28, 08). Resampled every
    `spacing` px; returns an (N, 2) float array (feed it to Canvas.mask_poly or Canvas.poly).
    closed=True treats pts as a polygon (and makes the noise periodic around it)."""
    p = np.asarray(pts, float).reshape(-1, 2)
    if len(p) < 2:
        return p.copy()
    if closed:
        p = np.vstack([p, p[:1]])
    seg = np.hypot(*(p[1:] - p[:-1]).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    n = max(2, int(total / spacing) + 1)
    s = np.linspace(0, total, n, endpoint=not closed)
    i = np.clip(np.searchsorted(cum, s, 'right') - 1, 0, len(seg) - 1)
    f = (s - cum[i]) / np.maximum(seg[i], 1e-9)
    q = p[i] + (p[i + 1] - p[i]) * f[:, None]
    tv = (p[i + 1] - p[i]) / np.maximum(seg[i], 1e-9)[:, None]
    nv = np.stack([tv[:, 1], -tv[:, 0]], 1)
    per = total if closed else period
    w2 = 10 if wavelength > 10 else wavelength / 2.8
    d = amp * (0.6 * vnoise1(s, wavelength, seed, per) + 0.4 * vnoise1(s, w2, seed + 1, per))
    return q + nv * d[:, None]

def _stepped(a, b, span, t):
    """the across position of a straight edge from a (at t = 0) to b (at t = span), its slope snapped
    to a pixel-art ratio (1 px every n rows, or n px every row) so it steps in equal runs"""
    a = float(np.round(a))
    k = (b - a) / max(span, 1e-9)
    if abs(k) < 1e-3:
        return np.full(t.shape, a)
    if abs(k) < 1:
        return a + np.sign(k) * np.floor(np.maximum(t, 0) / max(1, round(1 / abs(k))))
    return a + np.sign(k) * round(abs(k)) * np.floor(np.maximum(t, 0))

def ray(shape, x, y, angle=90, length=100, width=(4, 16)):
    """a hard-edged light ray as an H x W bool mask: a band from (x, y) toward `angle` degrees (90 =
    straight down, as in post.Post.shaft) over `length` px, widening from width[0] to width[1]. Each
    edge is a straight line stepped in equal runs (its slope snapped to 1:n or n:1), so it reads as a
    drawn pixel-art ray, not a jagged polygon. Fill it with a slot one ramp step lighter (Canvas.fill),
    or step what it crosses up a slot (rain, flakes, crests inside the mask): the angled ray for styles
    with no soft shaft. Within 45 degrees of vertical it steps per row, otherwise per column."""
    H, W = shape
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    vertical = abs(uy) >= abs(ux)
    s0, c0, ds, dc, N, M = (y, x, uy, ux, H, W) if vertical else (x, y, ux, uy, W, H)
    span = length * abs(ds)                          # extent along the main axis
    k = dc / abs(ds)                                 # across shift per px along it
    h0, h1 = width[0] / 2 / abs(ds), width[1] / 2 / abs(ds)
    t = (np.arange(N) + 0.5 - s0) * (1 if ds > 0 else -1)
    lo = _stepped(c0 - h0, c0 + k * span - h1, span, t)
    hi = _stepped(c0 + h0, c0 + k * span + h1, span, t)
    cc = np.arange(M) + 0.5
    m = ((t >= 0) & (t <= span))[:, None] & (cc[None, :] >= lo[:, None]) & (cc[None, :] < hi[:, None])
    return m if vertical else m.T

def _orient(a, side):
    """view an array so `side` is the top (the void above the room)"""
    return {'top': a, 'bottom': a[::-1], 'left': a.T, 'right': a.T[::-1]}[side]

def _lumps(w, size, height, seed):
    """per column: (bulge in px, lump id) for a row of rounded lumps size=(lo, hi) px wide"""
    prof = np.zeros(w)
    lid = np.zeros(w, int)
    xpos, k = 0, 0
    while xpos < w:
        lw = size[0] + int((size[1] - size[0] + 1) * _hs(k, 1, seed))
        n = min(w, xpos + lw) - xpos
        u = (np.arange(n) + 0.5) / lw * 2 - 1
        hk = height[0] + (height[1] - height[0]) * _hs(k, 2, seed)
        prof[xpos:xpos + n] = hk * np.sqrt(np.clip(1 - u * u, 0, 1)) ** 0.6
        lid[xpos:xpos + n] = k
        xpos += lw
        k += 1
    return np.floor(prof + 0.5).astype(int), lid

def void_edge(c, room, ramp, side='top', checker=3, lump=(6, 10), fade=7, void=None, base=2,
              crown=(4, 8), steps=None, seed=3):
    """where a lit room meets the black void (Stardew's mine, 10); `side` is the side the void
    is on. 'top' gives a wall crown: a ragged row of crown=(4, 8) px lumps bulging 2-4 px into
    the void, whose first 2..checker px are a pure 50% checker of ramp step 1 (the rest of
    those rows is void), then one row of base - 1. 'bottom', 'left', 'right' give a lip: a row
    of rounded lumps lump=(6, 10) px wide hanging fade-2..fade px into the void: lit on the row
    next to the room (base + 1), one step darker per 2 px outward (below step 0 is void), the
    rounded rim and the far side one step darker, void between the lumps and a 2 px dark seam
    (base - 1) 3 px into the room where two lumps meet; each lump's top shows in the room as a lit cap.
    room: the room's bool mask; the edge is where it meets non-room on that side (a room that
    runs off the frame has no edge there). Paints c and returns the new room mask (lumps
    included, cut pixels removed); cut pixels become `void` (None by default)."""
    g = _grid(c)
    room = np.asarray(room, bool)
    G = _orient(g, side)
    R = _orient(room.copy(), side)
    h, w = R.shape
    BIG = 10 ** 6
    yy, xx = np.mgrid[0:h, 0:w]
    X, Y = {'top': (xx, yy), 'bottom': (xx, h - 1 - yy), 'left': (yy, xx), 'right': (h - 1 - yy, xx)}[side]
    clip = (lambda k: int(np.clip(k, 0, steps - 1))) if steps else (lambda k: max(int(k), 0))
    name = lambda k: '%s%d' % (ramp, clip(k))
    # the edge row per column: the first room row with void right above it
    above = np.vstack([np.ones((1, w), bool), R[:-1]])
    first = R & ~above
    e0 = np.where(first.any(0), np.argmax(first, 0), BIG)
    has = e0 < BIG
    new = R.copy()
    if side == 'top':
        prof, lid = _lumps(w, crown, (2, 4), seed)
        top = np.where(has, e0 - prof, BIG)
        depth = 2 + (_h(lid, 7, seed) * (checker - 1) + 0.5).astype(int)
        d = yy - top[None, :]
        lumpm = has[None, :] & (d >= 0) & (yy < e0[None, :])
        new |= lumpm
        band = has[None, :] & (d >= 0) & (d < depth[None, :]) & new
        keep = ((X + Y) & 1) == 0
        G[band & keep] = name(1)
        G[band & ~keep] = void
        new &= ~(band & ~keep)
        G[has[None, :] & (d == depth[None, :]) & new] = name(base - 1)
        # bites between lumps: the seam column drops one more row
        seam = np.zeros(w, bool)
        seam[1:] = lid[1:] != lid[:-1]
        sm = seam[None, :] & has[None, :] & (d == depth[None, :])
        G[sm] = void
        new &= ~sm
    else:
        # a lip of rounded lumps hanging off the edge into the void: lit on the row next to the
        # room, one step darker per 2 px outward, rounded at the bottom, void between them
        d = (e0[None, :] - 1) - yy                         # 0 on the first void row, + outward
        lum = np.zeros((h, w), bool)
        tone = np.full((h, w), -BIG)
        xpos, k = 0, 0
        while xpos < w:
            lw = lump[0] + int((lump[1] - lump[0] + 1) * _hs(k, 1, seed))
            xa, xb = xpos, min(w, xpos + lw)
            xpos, k = xpos + lw, k + 1
            cols = np.arange(xa, xb)
            if not has[cols].any():
                continue
            out_ = fade - 1 + int(3 * _hs(k, 2, seed)) - 1   # reach into the void: fade-2 .. fade
            u = (cols + 0.5 - 0.5 * (xa + xb) - (_hs(k, 4, seed) - 0.5)) / (0.5 * lw + 0.3)
            hgt = np.floor(out_ * np.clip(1 - u * u, 0, 1) ** 0.45 + 0.5)    # a rounded bottom
            sub_d = d[:, cols]
            ins = has[None, cols] & (sub_d >= 0) & (sub_d < hgt[None, :]) & ~R[:, cols]
            t = base + 1 - (sub_d + 1) // 2                  # falls a step per 2 px
            t = np.where(u[None, :] > 0.55, t - 1, t)        # the lump's far side is in shade
            lum[:, cols] |= ins
            tone[:, cols] = np.where(ins, t, tone[:, cols])
            # its rounded top shows inside the room as a lit cap 2 rows deep
            cap = R[:, cols] & has[None, cols] & (((sub_d == -1) & (np.abs(u)[None, :] < 0.8)) |
                                                  ((sub_d == -2) & (np.abs(u)[None, :] < 0.45)))
            G[:, xa:xb] = np.where(cap, name(base + 1), G[:, xa:xb])
            # a dark seam where this lump meets the next, 2 px into the room
            sx = xa
            if 0 < sx < w and has[sx]:
                sm = (d[:, sx] >= -3) & (d[:, sx] < 0) & R[:, sx]
                G[sm, sx] = name(base - 1)
        new |= lum & (tone >= 0)
        for v in np.unique(tone[lum]):
            m = lum & (tone == v)
            if v >= 0:
                G[m] = name(v)

    return np.ascontiguousarray(_orient_back(new, side))

def _orient_back(a, side):
    return {'top': a, 'bottom': a[::-1], 'left': a.T, 'right': a[::-1].T}[side]

_fray_edge = fray                  # cloud_mass's `fray` argument shadows the function
