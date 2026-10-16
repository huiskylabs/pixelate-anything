"""Vegetation grammars: canopies of leaf glyphs on black (Freitas iso, 07), leaf scales (Sea of
Stars, 04), frame leaf masses (Owlboy, 08), fern rosettes and berry vines (Stardew mine, 10).
Each is a set of small drawn shapes placed by hash, never a noise texture or a Bayer dither.

    import veg
    light, mask = veg.lobe_light((H, W), 120, 80, 50, lobes=9, seed=3, with_mask=True)
    veg.leaf_glyphs(c, mask, 'leaf', light, gap='ol', seed=3)          # 07: ~55% black gaps
    veg.leaf_scales(c, crown, 'leaf', pitch=(4, 3), base=3)            # 04: 3x2 crescents
    veg.leafmass(c, sd, ('fol0', 'fol1', 'fol2', 'slate'), t=t, T=T)  # 08: leaves along a frame
    veg.fern(c, 60, 90, 'fern', fronds=7, t=t, T=T)                    # 10: a rosette of fronds
    veg.vine(c, 30, 10, 70, 'vine', berry='berry')                      # 10: trefoil column + berries

Ramps are BASE0 (darkest) .. BASEn; pass steps= the ramp length so tones clamp to it. Animated
helpers take t and T; every period divides T, so frame T is frame 0.
Measured targets (07): canopy pixels 55-57% black gap, leaf clusters median 3 px, p90 6, the
common glyph a 3x2 2:1 'Z' ('.LM/MD.'), tone following the canopy's lobes, no outline, a ragged
3 px fringe that shows the ground.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph
from shapes import _h, _hs, _grid

# ---------------------------------------------------------------- canopy light (07)
def _canopy_lobes(cx, cy, r, lobes, seed, squash):
    out = []
    for i in range(lobes):
        a = 2 * math.pi * _hs(i, 1, seed)
        d = r * 0.55 * math.sqrt(_hs(i, 2, seed))
        rr = r * (0.38 + 0.2 * _hs(i, 3, seed))
        out.append((cx + d * math.cos(a), cy + d * math.sin(a) * squash, rr, rr * squash))
    out.append((cx, cy, r * 0.55, r * 0.55 * squash))         # a core so lobes never leave holes
    out.sort(key=lambda q: q[1])                                # lower lobes overwrite upper
    return out

def lobe_light(shape, cx, cy, r, lobes=9, seed=0, squash=0.72, light=(-0.45, -0.9), q=0.35,
               overall=0.5, with_mask=False):
    """the light over a lobed canopy: 6-12 hashed elliptical lobes (radius 0.38-0.58 r, squash)
    around (cx, cy); per lobe lit = l.(dx/rx, dy/ry) - q * (radius fraction), lower lobes
    overwrite upper ones, plus `overall` times the same over the whole canopy. Values about -1.5
    .. 1.5 (0 outside). with_mask=True returns (light, mask)."""
    H, W = shape
    if r <= 0:
        z = np.zeros((H, W))
        return (z, z > 0) if with_mask else z
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    lx, ly = light
    lit = np.zeros((H, W))
    mask = np.zeros((H, W), bool)
    for x, y, rx, ry in _canopy_lobes(cx, cy, r, lobes, seed, squash):
        dx, dy = (xx - x) / rx, (yy - y) / ry
        rho = dx * dx + dy * dy
        ins = rho <= 1
        lit[ins] = (lx * dx + ly * dy - q * np.sqrt(rho))[ins]
        mask |= ins
    dx, dy = (xx - cx) / r, (yy - cy) / (r * squash)
    lit = np.where(mask, lit + overall * (lx * dx + ly * dy), 0.0)
    return (lit, mask) if with_mask else lit

# ---------------------------------------------------------------- leaf glyphs (07)
# (dx, dy, tone offset)
_GLYPHS = {
    'z':    ((1, 0, 1), (2, 0, 0), (0, 1, 0), (1, 1, -1)),     # .LM/MD.  the 2:1 Z, rising right
    'zl':   ((1, 0, 1), (2, 0, 1), (0, 1, 1), (1, 1, -1)),     # .LL/LD.  its lit variant
    'v':    ((1, 0, 0), (0, 1, 0), (1, 1, -1)),                # .M/MD
    'pair': ((0, 0, 0), (1, 0, -1)),                           # MD
    'dot':  ((0, 0, 0),),                                      # a single leaf, to fill holes
}

def leaf_glyphs(c, mask, ramp, light=None, gap='ol', fill=0.46, fringe=3, touch=0.01, contrast=1.0,
                base=None, steps=5, seed=0):
    """a canopy of 2:1 leaf glyphs on a black field (Freitas, 07). The mask's interior becomes
    `gap`; in its outer `fringe` px, 55% of pixels become gap and the rest keep what was under
    (the ground shows through a ragged edge). Then glyphs are dart-thrown in hash order: tone
    t = base + floor(contrast * light + .5 + .9 (h - .5)) (base defaults to steps - 2, so the
    common glyph is light over mid); a glyph at the top tone is the lit Z, else 12% a pair, 13%
    a V, the rest the Z. A glyph is rejected if it would touch another
    leaf (4-neighbours), except with probability `touch`; throwing stops when the leaves cover
    `fill` of the mask. Random throwing saturates near 35% cover, so a second pass fills the
    holes with pairs and then single leaves that touch nothing (measured on a 200 x 130 demo:
    gap 0.56, clusters median 3, mean 3.0, p90 4; the reference: 0.57, 3, 3.1, 6). Glyphs may poke 1-2 px past the mask (edge leaves over the road).
    light: lobe_light() or None (flat). Returns the leaf mask."""
    g = _grid(c)
    H, W = g.shape
    mask = np.asarray(mask, bool)
    if base is None:
        base = steps - 2                          # the common glyph is light over mid (07)
    L = np.zeros((H, W)) if light is None else np.asarray(light, float)
    d = morph.distance(mask, 'manhattan', border=False)
    band = mask & (d <= fringe)
    g[mask & ~band] = gap
    ys, xs = np.nonzero(band)
    hole = _h(xs, ys, seed + 9) < 0.55
    g[ys[hole], xs[hole]] = gap
    ys, xs = np.nonzero(mask)
    order = np.argsort(_h(xs, ys, seed), kind='stable')
    ys, xs = ys[order], xs[order]
    hk = _h(xs, ys, seed + 3)
    hs4 = _h(xs, ys, seed + 4)
    ht = _h(xs, ys, seed + 5)
    tone = base + np.floor(contrast * L[ys, xs] + 0.5 + 0.9 * (hk - 0.5)).astype(int)
    leaf = np.zeros((H + 6, W + 6), bool)                      # padded occupancy
    target = fill * mask.sum()
    placed = 0
    top = steps - 1
    names = ['%s%d' % (ramp, i) for i in range(steps)]
    def stamp(i, gl, t, allow):
        x0, y0 = int(xs[i]), int(ys[i])
        if not allow:
            for dx, dy, _ in gl:
                X, Y = x0 + dx + 2, y0 + dy + 2
                if leaf[Y, X] or leaf[Y, X - 1] or leaf[Y, X + 1] or leaf[Y - 1, X] or leaf[Y + 1, X]:
                    return 0
        for dx, dy, off in gl:
            X, Y = x0 + dx, y0 + dy
            if 0 <= X < W and 0 <= Y < H:
                g[Y, X] = names[max(0, min(top, t + off))]
                leaf[Y + 2, X + 2] = True
        return len(gl)
    for i in range(len(xs)):
        if placed >= target:
            break
        t = int(tone[i])
        if t >= top:
            kind = 'zl'
        elif hs4[i] < 0.12:
            kind = 'pair'
        elif hs4[i] < 0.25:
            kind = 'v'
        else:
            kind = 'z'
        placed += stamp(i, _GLYPHS[kind], t, ht[i] < touch)
    # random throwing saturates near 35% cover; fill the holes with pairs, then single leaves,
    # never touching (small isolated clusters, as in the reference)
    for kind in ('pair', 'dot'):
        for i in range(len(xs)):
            if placed >= target:
                break
            if mask[ys[i], xs[i]] and g[ys[i], xs[i]] == gap:
                placed += stamp(i, _GLYPHS[kind], int(tone[i]), False)
    return leaf[2:H + 2, 2:W + 2]

# ---------------------------------------------------------------- leaf scales (04)
# scale glyphs, (dx, dy, tone offset) about the grid point
_SCALES = {
    'crescent': ((-1, 0, 1), (0, 0, 1), (1, 0, 1), (-1, 1, -1), (0, 1, -2), (1, 1, -1)),   # 3x2
    'leaf': ((0, -1, 1), (1, -1, 1), (-1, 0, 1), (0, 0, 2), (1, 0, 0), (2, 0, -1),
             (0, 1, -1), (1, 1, -2)),                                                     # 4x3
}

def leaf_scales(c, mask, ramp, pitch=(4, 3), light=(-0.6, -0.8), base=3, steps=7, centre=None,
                radius=None, outline=None, glyph='leaf', seed=0):
    """a round canopy shingled with 3x2 leaf crescents (Sea of Stars, 04). The mask is first
    filled with a sphere-shaded underlayer one step below the scales (darkest at the lower
    right); then on a grid of pitch=(4, 3), odd rows offset by half, each centre jittered +-1,
    a scale takes s = base + round(k * span) from the sphere normal's k = n.light.
    glyph='leaf' (default): a rounded 4x3 leaf, mirrored by hash, lit cap s + 1 with an s + 2
    glint, body s, shaded right end and underside s - 1 / s - 2 ('.LL./LHMD/.DK.'), so the
    scales shingle into rounded tufts; glyph='crescent': the 3x2 crescent of the study (top
    row s + 1, bottom row s - 1 with s - 2 under the centre).
    centre/radius default to the mask's bounding box. outline: a slot for a 1 px outline."""
    g = _grid(c)
    H, W = g.shape
    mask = np.asarray(mask, bool)
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return
    if centre is None:
        centre = (0.5 * (xs.min() + xs.max() + 1), 0.5 * (ys.min() + ys.max() + 1))
    if radius is None:
        radius = max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1) / 2.0
    cx, cy = centre
    lx, ly = light
    ln = math.hypot(lx, ly) or 1
    lx, ly = lx / ln, ly / ln
    top = steps - 1
    span = (steps - 1) / 2.0
    def k_at(x, y):
        nx, ny = (x + 0.5 - cx) / radius, (y + 0.5 - cy) / radius
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
        return (nx * lx + ny * ly) * 0.8 + nz * 0.2
    name = lambda v: '%s%d' % (ramp, int(max(0, min(top, v))))
    under = base - 1 + np.round(k_at(xs, ys) * span * 0.8).astype(int)
    for v in np.unique(under):
        sel = under == v
        g[ys[sel], xs[sel]] = name(v - 1)
    px, py = pitch
    for gy in range(int(ys.min()) - py, int(ys.max()) + py, py):
        row = (gy // py) & 1
        for gx in range(int(xs.min()) - px + (px // 2 if row else 0), int(xs.max()) + px, px):
            x = gx + int(round(2 * _hs(gx, gy, seed) - 1))
            y = gy + int(round(2 * _hs(gx, gy, seed + 1) - 1))
            if not (0 <= x < W and 0 <= y < H and mask[y, x]):
                continue
            s = base + int(round(float(k_at(x, y)) * span))
            s = max(1, min(top - 1, s))
            gl = _SCALES[glyph]
            fl = glyph != 'crescent' and _hs(gx, gy, seed + 2) < 0.5     # mirrored by hash
            for dx, dy, off in gl:
                X, Y = x + (-dx if fl else dx), y + dy
                if 0 <= X < W and 0 <= Y < H and mask[Y, X]:
                    g[Y, X] = name(s + off)
    if outline is not None:
        ring = morph.boundary(mask)
        g[ring] = outline

# ---------------------------------------------------------------- frame leaf mass (08)
# leaf shapes: h = pale, m = sage, d = dark, '.' = none (slanted 3-5 px leaves, pale on top)
LEAVES = (
    ('.hhm', 'hmmd', 'mdd.'),
    ('..hm', '.hmd', 'hmd.', 'dd..'),
    ('hhm..', 'mmmd.', '.ddmd', '...dd'),
    ('hm', 'mm', 'md', 'dd', '.d'),
    ('.hm.', 'hmmd', 'mmdd', '.dd.'),
    ('hhm', 'mdd'),
    ('..hhm', '.hmdd', 'hmd..', 'dd...'),
    ('hm..', '.mmd', '..dd'),
)

def leafmass(c, sd, slots, stamps=LEAVES, band=(-14, 10), sigma=8, pitch=3, cool=-6, body=0.5,
             clump=9, light=(-0.45, -0.9), seed=0, t=None, T=None, k=1, hold=6):
    """the leaf mass that lines a drawn frame (Owlboy, 08). sd: signed distance to the frame's
    inner edge, positive in the void, negative in the playfield (morph.signed(void) or the
    inset_field helper). The density is p(d) = 0.9 exp(-((d + 2) / sigma)^2) inside
    band=(-14, 6), broken into clumps by a value noise of `clump` px.
    1. Body: where p (1 + 0.8 n) > 1 - body the mass is solid slots[0] (the dark leaf tone):
       the void shows through the gaps between clumps and through small holes inside them.
    2. Leaves: candidates on a jittered pitch x pitch grid, kept with probability p (more on
       the clumps and on their 2 px rim, so leaves poke out of the silhouette), each one of `stamps` (rows of h/m/d), mirrored by hash, h/m/d ->
       slots[2]/slots[1]/slots[0]. A leaf on a clump's shadow side (its body normal faces away
       from `light`) is one step darker (h -> m, m -> d); deeper than `cool` px into the
       playfield the 4th slot (a cool slate) replaces the sage. Drawn top to bottom so lower
       leaves overlap.
    Animated (t, T): leaf i sways dx = round(0.6 sin(2 pi (k t' / T) + phase_i)) with t' = t
    held for `hold` frames (2 fps at 12); k is an integer, so frame T is frame 0."""
    from shapes import vnoise2
    g = _grid(c)
    H, W = g.shape
    sd = np.asarray(sd, float)
    lo, hi = band
    inb = (sd >= lo) & (sd <= hi)
    P = np.where(inb, 0.9 * np.exp(-((sd + 2) / sigma) ** 2), 0.0)
    Pb = np.where(inb, np.exp(-((sd - 1) / (1.3 * sigma)) ** 2), 0.0)    # the body reaches into the void
    n = 0.7 * vnoise2((H, W), clump, seed + 21, wrap=False) + \
        0.3 * vnoise2((H, W), max(2, clump / 2.5), seed + 22, wrap=False)
    mass = inb & (Pb * (1 + 0.9 * n) > 1 - body) if body else np.zeros((H, W), bool)
    if mass.any():                                     # small holes where the void shows through
        holes = vnoise2((H, W), 4, seed + 23, wrap=False) < -0.62
        mass &= ~(holes & morph.erode(mass, 2))
    rim = morph.dilate(mass, 2) & ~mass                 # leaves also poke out of the clumps
    g[mass] = slots[0]
    lx, ly = light
    if mass.any():
        nx, ny = morph.normals(mass, blur=3)
        shade = (nx * lx + ny * ly) < -0.25            # the clump side away from the light
    else:
        shade = np.zeros((H, W), bool)
    cand = []
    for gy in range(0, H, pitch):
        for gx in range(0, W, pitch):
            x = gx + int(_hs(gx, gy, seed) * pitch)
            y = gy + int(_hs(gx, gy, seed + 1) * pitch)
            if not (0 <= x < W and 0 <= y < H) or not inb[y, x]:
                continue
            if mass[y, x]:
                p = max(P[y, x], 0.8 * Pb[y, x])
            elif rim[y, x]:
                p = 0.5 * Pb[y, x]
            else:
                p = 0.4 * P[y, x]
            p *= 1 + 0.5 * n[y, x]
            if _hs(gx, gy, seed + 2) < p:
                cand.append((y, x, sd[y, x], gx, gy))
    cand.sort()
    tt = None if t is None else ((int(t) % T if T else int(t)) // hold) * hold
    for y, x, d, gx, gy in cand:
        st = stamps[int(_hs(gx, gy, seed + 3) * len(stamps))]
        flip = _hs(gx, gy, seed + 4) < 0.5
        dx = 0
        if tt is not None and T:
            ph = 2 * math.pi * _hs(gx, gy, seed + 5)
            dx = int(round(0.6 * math.sin(2 * math.pi * ((k * tt) % T) / T + ph)))
        sage = slots[3] if (len(slots) > 3 and d < cool) else slots[1]
        if shade[y, x]:
            lut = {'h': sage, 'm': slots[0], 'd': slots[0]}
        else:
            lut = {'h': slots[2], 'm': sage, 'd': slots[0]}
        w = max(len(r) for r in st)
        for j, row in enumerate(st):
            for i, ch in enumerate(row):
                if ch == '.':
                    continue
                X = x + dx + ((w - 1 - i) if flip else i)
                Y = y + j
                if 0 <= X < W and 0 <= Y < H:
                    g[Y, X] = lut[ch]

def inset_field(W, H, inset=(52, 49, 16, 26), amp=8, wavelength=28, seed=0):
    """(void, sd) for a frame drawn into the art (08): the rectangle inset (left, right, top,
    bottom) px from the edges, each side displaced by amp (0.6 vn(s/wavelength) + 0.4
    vn(s/10)); void is outside it, sd the signed distance (positive in the void)."""
    from shapes import vnoise1
    l, r, t, b = inset
    xs, ys = np.arange(W), np.arange(H)
    left = l + amp * (0.6 * vnoise1(ys, wavelength, seed) + 0.4 * vnoise1(ys, 10, seed + 1))
    right = W - r + amp * (0.6 * vnoise1(ys, wavelength, seed + 2) + 0.4 * vnoise1(ys, 10, seed + 3))
    top = t + amp * 0.6 * (0.6 * vnoise1(xs, wavelength, seed + 4) + 0.4 * vnoise1(xs, 10, seed + 5))
    bot = H - b + amp * 0.6 * (0.6 * vnoise1(xs, wavelength, seed + 6) + 0.4 * vnoise1(xs, 10, seed + 7))
    yy, xx = np.mgrid[0:H, 0:W]
    inside = (xx >= left[:, None]) & (xx < right[:, None]) & (yy >= top[None, :]) & (yy < bot[None, :])
    void = ~inside
    return void, morph.signed(void) * -1.0

# ---------------------------------------------------------------- fern and vine (10)
def fern(c, cx, cy, ramp, fronds=7, length=(12, 17), fan=(195, 345), droop=0.6, lift=0.5, wide=0.7,
         base=1, steps=None, light=(-0.5, -0.85), seed=1, t=None, T=None, hold=6, k=1):
    """a fern rosette (Stardew's mine, 10): `fronds` quadratic Bezier fronds fanned over fan=(195,
    345) degrees (270 is straight up), each L = length px (12-17: the measured 28-32 px span
    once arched) with P1 = P0 + .6L (cos a, sin a - lift) and P2 = P0 + L (cos a, sin a + droop |cos a|): the side fronds arch up and over and their
    tips fall (the reference's palm-like arches; the study's droop 0.45 / lift 0.3 gave stiff
    grass). A frond is 2 px wide (a darker row under the spine) for its first `wide` of its
    length, then 1 px; every 2 px of arc a leaflet tick of max(1, round(3 (1 - u))) px sticks
    out, alternating sides, angled 30 degrees toward the tip, with a 1 px shorter one opposite
    it on the wide part. Tone = base + round(1.2 u), +1 on ticks that face
    the light. Animated: tips sway +-1 px (round(sin(2 pi k t' / T + phase)), t' held `hold`
    frames), weighted toward the tip."""
    g = _grid(c)
    H, W = g.shape
    lx, ly = light
    top = (steps - 1) if steps else 99
    put = lambda X, Y, v: (0 <= X < W and 0 <= Y < H) and g.__setitem__((Y, X), '%s%d' % (ramp, max(0, min(top, v))))
    tt = None if t is None else ((int(t) % T if T else int(t)) // hold) * hold
    for i in range(fronds):
        a = math.radians(fan[0] + (fan[1] - fan[0]) * (i + 0.5) / fronds + 8 * (2 * _hs(i, 1, seed) - 1))
        L = length[0] + (length[1] - length[0]) * _hs(i, 2, seed)
        L *= 0.75 + 0.25 * math.sin(math.pi * (i + 0.5) / fronds)    # outer fronds shorter
        P0 = np.array([cx, cy], float)
        P1 = P0 + 0.6 * L * np.array([math.cos(a), math.sin(a) - lift])
        P2 = P0 + L * np.array([math.cos(a), math.sin(a) + droop * abs(math.cos(a))])
        if tt is not None and T:
            P2[0] += round(math.sin(2 * math.pi * ((k * tt) % T) / T + 2 * math.pi * _hs(i, 3, seed)))
        n = int(2 * L) + 2
        arc, prev, side = 0.0, None, 1
        for j in range(n + 1):
            u = j / n
            p = (1 - u) ** 2 * P0 + 2 * u * (1 - u) * P1 + u * u * P2
            tg = 2 * (1 - u) * (P1 - P0) + 2 * u * (P2 - P1)
            tl = math.hypot(*tg) or 1
            tx, ty = tg / tl
            X, Y = int(math.floor(p[0])), int(math.floor(p[1]))
            tone = base + int(round(1.2 * u))
            put(X, Y, tone - 1 if u < 0.15 else tone)
            if u < wide:
                put(X, Y + 1, tone - 1)
            if prev is not None:
                arc += math.hypot(p[0] - prev[0], p[1] - prev[1])
            prev = p
            if arc >= 2 and u > 0.12:
                arc = 0.0
                ln = max(1, int(round(3 * (1 - u))))
                nx, ny = -ty * side, tx * side
                c30, s30 = math.cos(math.radians(30)), math.sin(math.radians(30))
                dx, dy = nx * c30 + tx * s30, ny * c30 + ty * s30          # angled toward the tip
                lit = 1 if (nx * lx + ny * ly) > 0 else 0
                for s_ in range(1, ln + 1):
                    put(int(math.floor(p[0] + dx * s_)), int(math.floor(p[1] + dy * s_)), tone + lit)
                if u < wide:                                  # pinnate: a shorter leaflet opposite
                    dx2, dy2 = -nx * c30 + tx * s30, -ny * c30 + ty * s30
                    for s_ in range(1, max(1, ln - 1) + 1):
                        put(int(math.floor(p[0] + dx2 * s_)), int(math.floor(p[1] + dy2 * s_)), tone + 1 - lit)
                side = -side

_TREFOIL = ('.hm.', 'hmmm', '.mmd', '..d.')

def vine(c, x, y0, y1, ramp, berry='berry', base=2, steps=None, spread=5, every=2, dense=0.5, seed=2):
    """a hanging vine column (Stardew's mine, 10), 12-16 px wide: a stem x(y) = x + round(2
    sin(y/7 + 2 pi h)) in step base - 2; every `every` px a 4x4 trefoil leaf (lit top-left in
    base + 1, body base, shaded lower right base - 1; a hashed leaf is a step lighter or darker)
    on alternating sides -2..spread px out (over the stem), plus at hash < dense a second leaf
    on the other side, so the column reads as a dense overlapping strip; a 2x2 `berry` (berry0 body, berry1 lit pixel) at hash
    < 0.25, at most one per 8 px. berry=None: no berries."""
    g = _grid(c)
    H, W = g.shape
    top = (steps - 1) if steps else 99
    nm = lambda v: '%s%d' % (ramp, max(0, min(top, v)))
    def put(X, Y, v):
        if 0 <= X < W and 0 <= Y < H:
            g[Y, X] = v
    ph = 2 * math.pi * _hs(0, 1, seed)
    sx = lambda y: x + int(round(2 * math.sin(y / 7.0 + ph)))
    for y in range(int(y0), int(y1)):
        put(sx(y), y, nm(base - 2))
    def leaf(j, side, y, sd):
        off = int((spread + 2) * _hs(j, 2, sd)) - 2       # -2 .. spread: leaves hide the stem
        lx_ = sx(y) + (off if side > 0 else -off - 3)
        tone = base + (1 if _hs(j, 3, sd) < 0.25 else 0) - (1 if _hs(j, 4, sd) < 0.25 else 0)
        flip = side < 0 and _hs(j, 7, sd) < 0.5
        for r, row in enumerate(_TREFOIL):
            for i, ch in enumerate(row):
                if ch != '.':
                    put(lx_ + ((3 - i) if flip else i), y + r, nm(tone + {'h': 1, 'm': 0, 'd': -1}[ch]))
    side, last_b = 1, -99
    for j, y in enumerate(range(int(y0), int(y1) - 2, every)):
        leaf(j, side, y, seed)
        if _hs(j, 8, seed) < dense:                         # a second leaf opposite
            leaf(j, -side, y + 1, seed + 1)
        side = -side
        if berry and _hs(j, 5, seed) < 0.25 and y - last_b >= 8:
            bx = sx(y) + (1 if side > 0 else -2)
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                put(bx + dx, y + 2 + dy, '%s0' % berry)
            put(bx, y + 2, '%s1' % berry)
            last_b = y
