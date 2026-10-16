"""Prop kits: vehicles, tyres, poles, trunks, rails, ladders, lanterns, girders, stairwells,
boats, docks, mine carts, crates, barrels, ore rocks, pipes and drains.

    import props
    from iso import Iso
    s = Iso(480, 300, origin=(240, 40), slots=PAL)
    props.car(s, 10, 20, kind='sedan', paint='pink', seed=3)       # Iso.box parts + tyre sprites
    props.car(s, 60, 20, kind='bus', paint='white', heading='-x')
    g = s.render(outline=True)                                     # black outline (07)
    pole = props.pole(90)                                          # a Figure: stamp(c, x, y)
    props.rails(c, [(10, 150), (120, 150), (120, 40)], gauge=8)    # top-down track with a fillet (10)
    props.ladder(c, 200, 40, 120); props.lantern(c, 230, 60)        # lantern cores are lamp* slots
    props.girders(c, 300, 0, 380, 120, seed=2)                     # dark structure (06)
    m = props.stairwell(c, 209, 127, 273, 184)                     # stairs into black (03)
    props.boat('dory', view='3q', oars=True).stamp(c, 120, 146)    # Figures with .points (04)
    props.dock(c, 214, 268, 128, bottom=150, missing=(-3,), short={6: 3}, posts=(8,))
    props.cart_on_rails(c, [(10, 150), (120, 150)], 40, load=0.6)   # a cart riding props.rails (10)
    props.crate(kind='slat').stamp(c, 352, 148); props.barrel(lid=False).stamp(c, 380, 148)
    props.ore_node(ore='ore', seed=4).stamp(c, 300, 200)           # rock with ore flecks (10)
    run = props.pipe(c, [(0, 40), (60, 40), (60, 90)], end='open')  # run['drips'] for fx (09)
    props.drain(c, 140, 160, kind='floor')

Learned from: 07 Freitas (cars built from boxes with streaked glass and upright 10 x 17 tyre
ovals, column-banded poles and trunks), 10 Stardew Valley (3-row rails 8 px apart with ties every
8 px and filleted corners, the ladder, the 6 x 9 wall lantern), 06 Into the Breach (near-black
girders a step above the dark, lattice towers), 03 Hyper Light Drifter (treads stepping into a
black void, brighter each step toward the viewer), 04 Sea of Stars (hulls as a sheer line with
1 px plank seams and a lit gunwale, jetties as a piling rhythm), 10 again (the mine cart, ore
rocks, crates and barrels as flat lit planes), 09 Katana ZERO (banded alley pipes, grates).
Every design is original: the craft is learned, no game's boats, carts or items are copied.

Sprites come back as figures.Figure (g plus the anchor, the ground point), Canvas helpers paint
in place and return their masks. Slots are ramp names plus a step: car paint uses the Iso 5-step
ramps (paint0..paint4), the rest name their ramp and steps in the docstring. Seeds only feed an
integer hash, so the same call always gives the same pixels.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from figures import Figure, _P, _outline, _h, _bresenham

__all__ = ['car', 'tyre', 'pole', 'trunk', 'rails', 'ladder', 'lantern', 'girders', 'truss',
           'stairwell', 'glass_streak', 'boat', 'dock', 'mine_cart', 'rail_point', 'cart_on_rails',
           'crate', 'barrel', 'ore_node', 'pipe', 'drain', 'BOATS', 'PALETTE', 'PAINTS']

PAINTS = ('pink', 'teal', 'yellow', 'red', 'green', 'white', 'violet', 'orange')

# ---------------------------------------------------------------- 07 vehicles
def tyre(w=10, h=17, hub=(3, 7), slots=None, spokes=False):
    """an upright tyre oval (07: a 10 x 17 implicit oval, NOT a projected circle): black outline,
    tyre body with a lit right rim, a 3 x 7 hub ringed one step darker. spokes=True draws a bike
    wheel instead (thin rim, 2 crossing spokes). slots: {'tyre', 'tyre_lit', 'hub', 'hub_ring', 'ol'}.
    Returns a Figure anchored at the bottom centre (the contact point)."""
    S = dict(tyre='tyre1', tyre_lit='tyre2', hub='hub2', hub_ring='hub1', ol='ol')
    S.update(slots or {})
    P = _P(w + 2, h + 2)
    yy, xx = np.mgrid[0:h, 0:w] + 0.5
    rx, ry = w / 2.0, h / 2.0
    d = ((xx - rx) / rx) ** 2 + ((yy - ry) / ry) ** 2
    body = d <= 1.0
    sub = P.g[1:h + 1, 1:w + 1]
    if spokes:
        inner = ((xx - rx) / (rx - 1.2)) ** 2 + ((yy - ry) / (ry - 1.2)) ** 2 <= 1.0
        sub[body & ~inner] = S['tyre']
        cxi, cyi = w // 2, h // 2
        for (x0, y0, x1, y1) in ((cxi, 1, cxi, h - 2), (1, cyi, w - 2, cyi)):
            for x, y in _bresenham(x0, y0, x1, y1):
                sub[y, x] = S['hub_ring']
    else:
        sub[body] = S['tyre']
        right = body & ~np.roll(body, -1, 1)          # the rightmost pixel of each row
        right2 = body & ~np.roll(body, -2, 1) & ~right
        sub[right | right2] = S['tyre_lit']
        hw, hh = hub
        hx0 = int(round(rx - hw / 2.0 - 0.5))
        hy0 = int(round(ry - hh / 2.0))
        hd = ((xx - (hx0 + hw / 2.0)) / (hw / 2.0 + 0.6)) ** 2 + ((yy - (hy0 + hh / 2.0)) / (hh / 2.0 + 0.6)) ** 2
        ring = hd <= 1.0
        core = ((xx - (hx0 + hw / 2.0)) / (hw / 2.0)) ** 2 + ((yy - (hy0 + hh / 2.0)) / (hh / 2.0)) ** 2 <= 1.0
        sub[ring] = S['hub_ring']
        sub[core] = S['hub']
    _outline(P.g, 'slot', ol=S['ol'])
    return Figure(P.g, (w + 2) // 2, h + 1)

def glass_streak(frame='ol', a='glass2', b='glass3', pitch=7, border=1, pillars=(), edges='uv'):
    """a face function for Iso.box: glass with 2 px diagonal streaks ((2u + v) mod pitch < 1.5)
    inside a 1 unit black frame (07 windows). pillars: u positions of extra frame bars. edges:
    which face coordinates get the frame ('uv', 'u' or 'v': for sliced, sloped glass)."""
    def f(u, v, t, face_step=2, W=None, H=None):
        if W is not None and (('u' in edges and (u < border or u >= W - border)) or
                              ('v' in edges and (v < 1 or v >= H - 1))):
            return frame
        for p in pillars:
            if p <= u < p + 1:
                return frame
        return b if (int(u * 2) + int(v)) % pitch < 1.5 else a
    return f

def _lights(paint, front, lamp, tail, d):
    """front or rear end face: two light blocks near the corners and a darker bumper strip"""
    def f(u, v, t, face_step=2, W=None, H=None):
        if v < 2:
            return '%s%d' % (paint, max(0, face_step - 1))
        if v >= H - 4 and v < H - 1 and (1 <= u < 4 or W - 4 <= u < W - 1):
            return lamp if front else tail
        return '%s%d' % (paint, face_step)
    return f

def _side(paint, doors=(), sill=2):
    """a long side: paint with black door seams (1 unit wide lines) and a darker sill"""
    def f(u, v, t, face_step=2, W=None, H=None):
        if v < sill:
            return '%s%d' % (paint, max(0, face_step - 1))
        for dx in doors:
            if dx <= u < dx + 0.5:
                return 'ol'
        return '%s%d' % (paint, face_step)
    return f

def _ribs(paint, every=3):
    def f(u, v, t, face_step=3, W=None, H=None):
        return '%s%d' % (paint, face_step - 1 if int(u) % every == 0 else face_step)
    return f

def _hatches(paint, n=3, size=(7, 5)):
    """a bus roof: n hatch outlines as black rhombuses (they are rectangles in world space)"""
    def f(u, v, t, face_step=3, W=None, H=None):
        if H > W:                                       # the bus runs along y: hatches along v
            u, v, W, H = v, u, H, W
        L = W / float(n + 1)
        for k in range(1, n + 1):
            cu = k * L
            du, dv = abs(u - cu), abs(v - H / 2.0)
            if du <= size[0] / 2.0 and dv <= size[1] / 2.0 and (du > size[0] / 2.0 - 1 or dv > size[1] / 2.0 - 1):
                return 'ol'
        return '%s%d' % (paint, face_step)
    return f

def car(s, x, y, kind='sedan', paint='pink', heading='x', seed=0, z=0, glass=('glass2', 'glass3'),
        lamp='lamp_w', tail='lamp_r', tyre_grid=None, steps=(2, 1, 3)):
    """a 07 vehicle built from Iso.box parts in world units (1 unit = (2, 1) px), with upright
    tyre sprites on the visible long side. kind: 'sedan' (40 x 17 x 11 chassis, 20 x 15 x 10 cabin),
    'pickup' (cabin forward, an open ribbed bed), 'convertible' (no roof: windshield, two seats and a
    driver's head), 'bus' (84 x 24 x 46 with a chamfered roof, 3 hatches, a row of windows, an
    ad panel on the end). paint: a 5-step ramp name. heading 'x' / '-x' (long along x) or 'y' /
    '-y'; the visible end shows headlights when the car faces it, tail lights otherwise. steps:
    the face steps (top, y face, x face): 07 lights from the right, so the x face is the light
    one. Returns the scene's object ids. Call s.render(outline=True) once everything is placed."""
    along_x = heading in ('x', '-x')
    front_visible = heading in ('x', 'y')
    tg = tyre_grid or tyre().grid()
    ids = []
    gl = glass_streak(a=glass[0], b=glass[1])
    def box(ax, ay, az, L, D, Hh, top=None, side=None, end=None, cast=False, lines=True):
        """L along the heading, D across; side = the long visible face, end = the visible end"""
        if along_x:
            return s.box(x + ax, y + ay, z + az, L, D, Hh, paint, top=top, left=side, right=end, steps=steps,
                         cast=cast, lines=lines)
        return s.box(x + ay, y + ax, z + az, D, L, Hh, paint, top=top, left=end, right=side, steps=steps,
                     cast=cast, lines=lines)
    (a00, a01, a02), (a10, a11, a12) = [[float(v) for v in row] for row in np.asarray(s.A, float)]
    def wind(k, a0, z0, top):
        """windshield / rear glass on cabin slice k (box corner a0 along the car, height z0): the
        streak is a function of the screen position, so the 2 px streaks run unbroken down the
        sloped pane across the 1 px slices instead of hatching row by row"""
        def f(u, v, t, face_step=2, W=None, H=None):
            if top:
                al, ac, n = ((u, v, H) if along_x else (v, u, W))
                wz = z0 + 1
            else:
                al, ac, n = 0, u, W
                wz = z0 + v
            if n is not None and (ac < 1 or ac >= n - 1):
                return 'ol'
            along = a0 + al if top else a1k[k]          # the visible end is the slice's far corner
            wx, wy = (x + along, y + 1 + ac) if along_x else (x + 1 + ac, y + along)
            sx = a00 * wx + a01 * wy + a02 * (z + wz)
            sy = a10 * wx + a11 * wy + a12 * (z + wz)
            return glass[1] if (int(math.floor(sx)) - int(math.floor(sy))) % 11 < 2 else glass[0]
        return f
    a1k = {}
    def cabin(cx0, cl, ch_, z0, front=4, back=3, pillars=()):
        """a cabin of 1 px slices whose ends recede: sloped windshield and rear glass, a paint roof"""
        side_glass = glass_streak(a=glass[0], b=glass[1], pillars=pillars)
        for k in range(int(ch_)):
            f = k / max(1.0, ch_ - 1)
            a0 = cx0 + back * f if front_visible else cx0 + front * f
            a1 = cx0 + cl - (front * f if front_visible else back * f)
            last = k == ch_ - 1
            sg = (lambda off, kk: lambda u, v, t, face_step=2, W=None, H=None:
                  side_glass(u + off, v + kk, t, face_step, cl, ch_))(a0 - cx0, k)
            a1k[k] = a1
            # the glass slices skip the render's crease and between-object lines (they would hatch
            # the pane every row); their black frames already outline the cabin, the roof keeps its lines
            ids.append(box(a0, 1, z0 + k, a1 - a0, D_ - 2, 1, top=None if last else wind(k, a0, z0 + k, True),
                           side=sg, end=wind(k, a0, z0 + k, False), lines=last))
    def wheel(ax):
        p = (x + ax, y + D_, z) if along_x else (x + D_, y + ax, z)
        ids.append(_front_sprite(s, tg, p, H_ + 4, (tg.w // 2, tg.h - 1)))
    if kind == 'bus':
        L_, D_, H_ = 84, 24, 46
        lift = 5
        ids.append(box(2, 1, 0, L_ - 4, D_ - 2, lift, top='ol', side='ol', end='ol'))
        win = lambda u, v, t, face_step=2, W=None, H=None: (
            'ol' if (6 <= u < W - 4 and 22 <= v < 36 and (int(u - 6) % 12 in (0, 9) or v in (22, 35)))
            else (glass[1] if (6 <= u < W - 4 and 23 <= v < 35 and int(u - 6) % 12 < 9 and (int(2 * u) + int(v)) % 7 < 1.5)
                  else (glass[0] if (6 <= u < W - 4 and 23 <= v < 35 and int(u - 6) % 12 < 9)
                        else ('%s%d' % (paint, max(0, face_step - 1)) if v < 3 else '%s%d' % (paint, face_step)))))
        ad = lambda u, v, t, face_step=2, W=None, H=None: (
            'ol' if (3 <= u < W - 3 and 14 <= v < 36 and (u < 4 or u >= W - 4 or v < 15 or v >= 35))
            else ('ad' if (4 <= u < W - 4 and 15 <= v < 35) else _lights(paint, front_visible, lamp, tail, D_)(u, v, t, face_step, W, H)))
        ids.append(box(0, 0, lift, L_, D_, H_ - 6, side=win, end=ad, cast=True))
        ids.append(box(2, 2, lift + H_ - 6, L_ - 4, D_ - 4, 4, top=_hatches(paint)))     # the chamfer
        for ax in (12, L_ - 22, L_ - 12):
            wheel(ax)
        return ids
    L_, D_, H_ = 40, 17, 25
    lift, ch = 4, 11
    ids.append(box(2, 1, 0, L_ - 4, D_ - 2, lift, top='ol', side='ol', end='ol'))       # the dark underside
    front = _lights(paint, front_visible, lamp, tail, D_)
    if kind == 'pickup':
        ids.append(box(0, 0, lift, L_, D_, ch, side=_side(paint, (24,)), end=front, cast=True))
        cabin(L_ - 20 if front_visible else 6, 14, 10, lift + ch, front=3, back=1, pillars=(7,))
        bx0 = 1 if front_visible else 19
        ids.append(box(bx0, 0, lift + ch, 19, 1, 4))                                   # bed walls
        ids.append(box(bx0, D_ - 1, lift + ch, 19, 1, 4))
        ids.append(box(bx0 if front_visible else bx0 + 18, 1, lift + ch, 1, D_ - 2, 4))
        ids.append(box(bx0 + 1, 1, lift + ch, 18, D_ - 2, 0.0, top=_ribs(paint)))
    elif kind == 'convertible':
        ids.append(box(0, 0, lift, L_, D_, ch, side=_side(paint, (22,)), end=front, cast=True))
        wx = 26 if front_visible else 12
        ids.append(box(wx, 1, lift + ch, 1, D_ - 2, 6, end=gl, side='ol'))             # windshield
        for sy in (2, 9):                                                               # seats
            ids.append(s.box(*(_xy(x, y, along_x, wx - 7 if front_visible else wx + 2, sy)), z + lift + ch,
                             *((5, 6) if along_x else (6, 5)), 5, 'seat', cast=False))
        head = _head_grid(seed)
        hx, hy = _xy(x, y, along_x, wx - 4 if front_visible else wx + 5, 4)
        ids.append(_front_sprite(s, head, (hx, hy, z + lift + ch + 2), 6, (3, 5)))
    else:                                                                               # sedan
        ids.append(box(0, 0, lift, L_, D_, ch, side=_side(paint, (13, 26)), end=front, cast=True))
        cabin(9 if front_visible else 11, 21, 10, lift + ch, front=5, back=3, pillars=(10,))
    for ax in (7, L_ - 9):
        wheel(ax)
    return ids

def _front_sprite(s, grid, p, height, anchor):
    """Iso.sprite moved along the view direction (the screen position stays, the depth rises) so
    it draws in front of a body face up to `height` px tall behind it (tyres over the car side)"""
    v = s.view
    k = height * abs(v[2]) / max(1e-6, float(v @ v)) + 1.0
    return s.sprite(grid, p[0] + v[0] * k, p[1] + v[1] * k, p[2] + v[2] * k, anchor=anchor)

def _xy(x, y, along_x, a, b):
    return (x + a, y + b) if along_x else (x + b, y + a)

def _head_grid(seed):
    """a driver's head for a convertible: 4 x 4 hair over skin (iso_person colours)"""
    import artlib
    hair = ('hblack2', 'hred2', 'hblond2', 'hbrown2')[int(_h(seed, 5) * 4) % 4]
    g = artlib.Grid(6, 6)
    rows = ['.oooo.', 'oHHHHo', 'oHSSSo', 'oSSSSo', '.oooo.']
    key = {'o': 'ol', 'H': hair, 'S': 'skinB2'}
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != '.':
                g.a[j][i] = key[ch]
    return g

# ---------------------------------------------------------------- 07 poles and trunks
def _bands(w, n, lit_end):
    """split w columns into n contiguous groups as evenly as possible, extra px to the lit end"""
    base, extra = divmod(w, n)
    sizes = [base] * n
    order = range(n) if lit_end == 0 else range(n - 1, -1, -1)
    for i in list(order)[:extra]:
        sizes[i] += 1
    return sizes

def _band_rows(P, x0, y0, y1, w, slots, widths=None):
    widths = widths or _bands(w, len(slots), 0)
    x = x0
    for sl, k in zip(slots, widths):
        P.rect(x, y0, x + k, y1, sl)
        x += k

def pole(h=90, w=(11, 7), ramp='pole', arms='x', arm_len=22, outline=True):
    """a 07 lamp pole: a column-banded cylinder (no dither), lit on the left, tapering in stepped
    segments (lower w[0] px wide, upper w[1]) with a 1-row collar of the darkest step at each
    step, under an X of four flat arms (2:1 iso bars) or arms=None. ramp: 5 steps, pole4 the
    lightest. Bands at 7 px: 4 4 3 2 1 1 0 (07's #f1f1f1 x2, #cfcfcf, #adaba7, #737272, #4f4c4c x2).
    Returns a Figure anchored at the foot."""
    r = lambda k: '%s%d' % (ramp, k)
    up_w, lo_w = w[1], w[0]
    pad = arm_len * 2 + 4 if arms else lo_w + 4
    Wd = max(pad, lo_w + 4)
    top_extra = arm_len // 2 + 4 if arms else 2
    P = _P(Wd, h + top_extra + 2)
    cx = Wd // 2
    base = h + top_extra
    lo_h = int(h * 0.38)
    seven = [r(4), r(4), r(3), r(2), r(1), r(0), r(0)]
    def slots_for(width):
        if width == 7:
            return seven, None
        if width == 11:
            return [r(4), r(3), r(2), r(1), r(0)], [2, 2, 3, 2, 2]
        n = min(5, max(2, width // 2))
        return [r(4 - int(round(i * 4.0 / (n - 1)))) for i in range(n)], None
    sl, wd = slots_for(lo_w)
    _band_rows(P, cx - lo_w // 2, base - lo_h, base, lo_w, sl, wd)
    P.rect(cx - lo_w // 2, base - lo_h, cx - lo_w // 2 + lo_w, base - lo_h + 1, r(0))     # collar
    mid_w = (lo_w + up_w) // 2 | 1
    if mid_w not in (lo_w, up_w):
        sl, wd = slots_for(mid_w)
        _band_rows(P, cx - mid_w // 2, base - lo_h - 6, base - lo_h, mid_w, sl, wd)
        P.rect(cx - mid_w // 2, base - lo_h - 6, cx - mid_w // 2 + mid_w, base - lo_h - 5, r(0))
        top_lo = base - lo_h - 6
    else:
        top_lo = base - lo_h
    sl, wd = slots_for(up_w)
    _band_rows(P, cx - up_w // 2, base - h, top_lo, up_w, sl, wd)
    if arms:                                            # an X of 2:1 bars, light top, dark under
        ay = base - h
        for sx in (-1, 1):
            for k in range(arm_len):
                x = cx + sx * (k + 1)
                for dy, st in ((-1, 4), (0, 3), (1, 1)):
                    P.put(x, ay + dy - (k // 2), r(st))     # rising arm
                    P.put(x, ay + dy + (k // 2), r(st))     # falling arm
        P.rect(cx - 2, ay - 2, cx + 3, ay + 2, r(3))
        P.rect(cx - 1, ay - 2, cx + 2, ay - 1, r(4))
    if outline:
        _outline(P.g, 'slot', ol='ol')
    return Figure(P.g, cx, base - 1)

def trunk(h=24, w=6, flare=2, ramp='bark', outline=True):
    """a 07 tree trunk: column bands dark left to light right (#962d00, #af6600 x2, #e09622 x2 at
    w=6), a black outline, the root flare widening `flare` px per side over the last 4 rows.
    ramp: steps 0-3 (bark0 the darkest). Returns a Figure anchored at the foot."""
    r = lambda k: '%s%d' % (ramp, k)
    n = 3 if w <= 7 else 4
    slots = [r(i) for i in range(n)]
    widths = _bands(w, n, 1)
    Wd = w + 2 * flare + 4
    P = _P(Wd, h + 2)
    cx0 = (Wd - w) // 2
    _band_rows(P, cx0, 1, h + 1, w, slots, widths)
    for k in range(4):                                  # flare: +1 px a side every 2 rows
        y = h - k
        ext = min(flare, (4 - k) // 2 + (1 if k == 0 else 0))
        if ext > 0:
            P.rect(cx0 - ext, y, cx0, y + 1, slots[0])
            P.rect(cx0 + w, y, cx0 + w + ext, y + 1, slots[-1])
    if outline:
        _outline(P.g, 'slot', ol='ol')
    return Figure(P.g, cx0 + w // 2, h)

# ---------------------------------------------------------------- 10 rails, ladder, lantern
def _fillet(pts, r):
    """sample a polyline at ~1 px arc length with quarter-ish arcs of radius r at its corners ->
    (N, 4) array of x, y, tx, ty"""
    pts = [np.array(p, float) for p in pts]
    out = []
    def seg(a, b):
        d = b - a
        L = float(np.hypot(*d))
        if L < 1e-9:
            return
        t = d / L
        for k in range(int(L)):
            q = a + t * k
            out.append((q[0], q[1], t[0], t[1]))
    cur = pts[0]
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        if i < len(pts) - 1:
            c = pts[i + 1]
            t0 = (b - a) / max(1e-9, np.hypot(*(b - a)))
            t1 = (c - b) / max(1e-9, np.hypot(*(c - b)))
            cos = float(np.clip(t0 @ t1, -1, 1))
            ang = math.acos(cos)
            if ang > 1e-3 and r > 0:
                cut = r * math.tan(ang / 2)
                p0, p1 = b - t0 * cut, b + t1 * cut
                seg(cur, p0)
                n0 = np.array([-t0[1], t0[0]])
                if n0 @ t1 < 0:
                    n0 = -n0
                cen = p0 + n0 * r
                a0 = math.atan2(*(p0 - cen)[::-1])
                a1 = math.atan2(*(p1 - cen)[::-1])
                da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                n = max(2, int(abs(da) * r * 1.5))
                for k in range(n):
                    aa = a0 + da * k / n
                    q = cen + r * np.array([math.cos(aa), math.sin(aa)])
                    tg = np.array([-math.sin(aa), math.cos(aa)]) * (1 if da > 0 else -1)
                    out.append((q[0], q[1], tg[0], tg[1]))
                cur = p1
                continue
        seg(cur, b)
        cur = b
    t = (pts[-1] - pts[-2]) / max(1e-9, np.hypot(*(pts[-1] - pts[-2])))
    out.append((pts[-1][0], pts[-1][1], t[0], t[1]))
    return np.array(out)

def rails(c, pts, rail='rail', wood='tie', gauge=8, tie_every=8, corner_r=4, joint=16):
    """a top-down mine track (10) along a polyline (axis-aligned or 45 degree runs), corners
    filleted so the inner rail turns on radius corner_r. Ties first: every tie_every px a 3 px plank
    across the track, sticking out 2-3 px beyond the rails (snapped square or to 45 degrees) (wood ramp steps 0-3: an outline in step 0, body 2, a lit top row 3). Then
    two rails at +-gauge/2, each a 3 px cross-section: horizontal runs top to bottom
    [rail2 highlight, rail1, rail0 plum], vertical runs left to right [rail0, rail2, rail1], with
    a darker joint on the middle row every `joint` px. Returns the track mask."""
    path = _fillet(pts, corner_r + gauge / 2.0)          # corner_r is the inner rail's radius
    H, W = c.g.shape
    before = c.g.copy()
    def put(x, y, v):
        xi, yi = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
        if 0 <= xi < W and 0 <= yi < H:
            c.g[yi, xi] = v
    hl = gauge // 2 + 2                                 # tie half length: 2 px beyond the rails' centre
    for i in range(0, len(path), tie_every):            # ties: a 3 px plank across the track, outlined
        x, y, tx, ty = path[i]
        a = math.atan2(ty, tx)
        a = round(a / (math.pi / 4)) * (math.pi / 4)    # planks sit square or at 45 degrees, never ragged
        tx, ty = math.cos(a), math.sin(a)
        nx, ny = -ty, tx
        cx, cy = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
        r = hl + 3
        for py in range(cy - r, cy + r + 1):
            for px in range(cx - r, cx + r + 1):
                u = (px - cx) * nx + (py - cy) * ny     # across the track
                v = (px - cx) * tx + (py - cy) * ty     # along it
                au, av = abs(u), abs(v)
                if au > hl + 1.25 or av > 2.25:
                    continue
                if au > hl + 0.25 or av > 1.25:
                    st = 0                              # plum outline
                elif au > hl - 0.75 and (nx + ny) * u < 0:
                    st = 3                              # the end toward the upper left catches the light
                else:
                    st = 2
                if 0 <= px < W and 0 <= py < H:
                    c.g[py, px] = '%s%d' % (wood, st)
    for k, (x, y, tx, ty) in enumerate(path):           # rails
        nx, ny = -ty, tx
        vert = abs(ty) > abs(tx)
        for sgn in (-1, 1):
            bx, by = x + nx * sgn * gauge / 2.0, y + ny * sgn * gauge / 2.0
            if vert:
                for d, st in ((-1, 0), (0, 2), (1, 1)):
                    put(bx + d, by, '%s%d' % (rail, st))
            else:
                for d, st in ((-1, 2), (0, 1 if k % joint else 0), (1, 0)):
                    put(bx, by + d, '%s%d' % (rail, st))
    return ~np.equal(c.g, before)

def ladder(c, x, y0, y1, ramp='wood', rung=7, width=15, nail='nail'):
    """a 10 ladder: two 2 px stiles (outer column step 1, inner step 2), a 2 px rung every `rung`
    px (step 3 over step 1) and a 1 px nail at each rung end. Returns its mask."""
    r = lambda k: '%s%d' % (ramp, k)
    before = c.g.copy()
    for y in range(int(y0) + 3, int(y1) - 1, rung):
        c.rect(x + 2, y, x + width - 2, y + 1, r(3))
        c.rect(x + 2, y + 1, x + width - 2, y + 2, r(1))
    c.rect(x, y0, x + 1, y1, r(1)); c.rect(x + 1, y0, x + 2, y1, r(2))
    c.rect(x + width - 2, y0, x + width - 1, y1, r(1)); c.rect(x + width - 1, y0, x + width, y1, r(2))
    for y in range(int(y0) + 3, int(y1) - 1, rung):
        c.put(x + 1, y, nail); c.put(x + width - 2, y, nail)
    return ~np.equal(c.g, before)

LANTERNS = {
    'wall': ("""
        ..oo..
        .o..o.
        ooiioo
        oLLLLo
        oIwwIo
        oIwwIo
        oiLLio
        .oooo.
        ..oo..""", (3, 8)),
    'paper': ("""
        ..o..
        .oio.
        oLLLo
        LwwwL
        LwwwL
        oLLLo
        .oio.""", (2, 6)),
    'post': ("""
        .ooooo.
        oiiiiio
        .oLwLo.
        .oLwLo.
        .oLLLo.
        .ooooo.
        ...o...
        ...o...
        ...o...
        ...o...
        ...o...
        ...o...
        ...o...
        ...o...
        ..ooo..""", (3, 14)),
}

def lantern(c, x, y, kind='wall', iron='iron', glow='lamp', lit=True, t=None, flicker=None):
    """stamp a lantern whose core slots are lamp* (so post.py light maps and glow masks find
    them): kind 'wall' (10: 6 x 9, a 2 px bail, a 4 x 2 hot core: lamp3 centre, lamp2 sides), 'paper' (5 x 7, hangs from a
    cord), 'post' (a 7 x 15 lamp post). (x, y) is the hanging point / foot. iron: a ramp (steps 0-2),
    glow: a ramp (lamp1 the paper, lamp2 the core, lamp3 the hottest). lit=False shows the core
    unlit (iron2). flicker: a hold table of core steps [(step, frames), ...] played at frame t.
    Returns the lantern's core mask (where to hang the light)."""
    art, (ax, ay) = LANTERNS[kind]
    core = 3
    if flicker and t is not None:
        total = sum(f for _, f in flicker)
        k = int(t) % total
        for st, f in flicker:
            if k < f:
                core = st
                break
            k -= f
    key = {'o': iron + '0', 'i': iron + '1',
           'L': (glow + '1') if lit else iron + '1', 'I': (glow + '2') if lit else iron + '2',
           'w': (glow + str(core)) if lit else iron + '2'}
    rows = [l.strip() for l in art.strip('\n').split('\n')]
    H, W = c.g.shape
    m = np.zeros((H, W), bool)
    ox, oy = int(x) - ax, int(y) - (0 if kind in ('wall', 'paper') else ay)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            px, py = ox + i, oy + j
            if 0 <= px < W and 0 <= py < H:
                c.g[py, px] = key[ch]
                if ch in 'wI':
                    m[py, px] = True
    return m

# ---------------------------------------------------------------- 06 girders and lattice towers
def girders(c, x0, y0, x1, y1, ramp='metal', widths=(3, 6), gap=(10, 26), brace=(18, 30), seed=0):
    """near-black structure (06): vertical girders 3-6 px wide (hash-chosen) across [x0, x1),
    each with a 1 px lit left edge (step 2), body step 1, a 1 px dark right edge (step 0), joined
    by 2 px cross-braces every 18-30 px between neighbours. Detail sits only a step above the
    dark. Returns the mask."""
    r = lambda k: '%s%d' % (ramp, k)
    before = c.g.copy()
    cols = []
    x, k = int(x0), 0
    while x < x1:
        w = widths[0] + int(_h(k, 1, seed) * (widths[1] - widths[0] + 1))
        w = min(w, int(x1) - x)
        cols.append((x, w))
        x += w + gap[0] + int(_h(k, 2, seed) * (gap[1] - gap[0] + 1))
        k += 1
    for i in range(len(cols) - 1):                      # braces behind the columns
        (xa, wa), (xb, wb) = cols[i], cols[i + 1]
        y = int(y0) + int(_h(i, 3, seed) * brace[0])
        while y < y1 - 2:
            c.rect(xa + wa, y, xb, y + 1, r(1))
            c.rect(xa + wa, y + 1, xb, y + 2, r(0))
            y += brace[0] + int(_h(i, y, seed) * (brace[1] - brace[0] + 1))
    for (x, w) in cols:
        c.rect(x, y0, x + w, y1, r(1))
        c.rect(x, y0, x + 1, y1, r(2))
        c.rect(x + w - 1, y0, x + w, y1, r(0))
    return ~np.equal(c.g, before)

def truss(c, x, y0, y1, w=7, ramp='metal', rung=5, diagonals=True):
    """a lattice tower (06 crane): two 1 px chords w apart, rungs every `rung` px and one diagonal
    per bay; the left chord lit (step 2), the rest step 1. Returns the mask."""
    r = lambda k: '%s%d' % (ramp, k)
    before = c.g.copy()
    c.rect(x, y0, x + 1, y1, r(2))
    c.rect(x + w - 1, y0, x + w, y1, r(1))
    k = 0
    for y in range(int(y0), int(y1), rung):
        c.rect(x + 1, y, x + w - 1, y + 1, r(1))
        if diagonals and y + rung < y1:
            a, b = (x + 1, x + w - 2) if k % 2 == 0 else (x + w - 2, x + 1)
            c.line(a, y + 1, b, y + rung - 1, r(1))
        k += 1
    return ~np.equal(c.g, before)

# ---------------------------------------------------------------- 03 stairwell
def stairwell(c, x0, y0, x1, y1, void_rows=17, tread=3, riser=2, ramp='step', void='void', levels=None,
              gamma=1.3, steps=5, t=None, wave_hold=2, T=None):
    """a doorway of treads descending into black (03): fill [x0, x1) x [y0, y1) with `void`, keep
    the top void_rows rows pure void, then repeat tread rows (lit) and riser rows (void) down to y1.
    Tread k (0 = the farthest, top) takes ramp step round((steps - 1) * ((k + 1) / n) ** gamma),
    so the stairs brighten toward the viewer with no dither (the colour rises ~+4..+10 a tread).
    levels: an explicit list of steps per tread. t: a lighting wave runs down the treads, one
    tread a step brighter per wave_hold frames (period n * wave_hold); with T the wave instead
    makes exactly one pass per loop of T frames (frame T == frame 0). Returns {'void', 'treads',
    'tread0', 'tread1', ...} bool masks."""
    c.rect(x0, y0, x1, y1, void)
    H, W = c.g.shape
    rows = list(range(int(y0) + void_rows, int(y1), tread + riser))
    n = len(rows)
    out = {'void': np.zeros((H, W), bool), 'treads': np.zeros((H, W), bool)}
    out['void'][max(0, y0):y1, max(0, x0):x1] = True
    for k, y in enumerate(rows):
        lv = levels[k] if levels else int(round((steps - 1) * ((k + 1) / float(n)) ** gamma))
        if t is not None and ((int(t) % T) * n // T if T else (int(t) // wave_hold) % n) == k:
            lv = min(steps - 1, lv + 1)
        c.rect(x0, y, x1, min(y + tread, y1), '%s%d' % (ramp, lv))
        m = np.zeros((H, W), bool)
        m[y:min(y + tread, y1), max(0, x0):x1] = True
        out['tread%d' % k] = m
        out['treads'] |= m
        out['void'] &= ~m
    return out

# ---------------------------------------------------------------- shared helpers for sprite props
def _fig(g, ax, ay, points=None, parts=None):
    """crop a padded slot grid to its drawn box (1 px kept for nothing: the outline is already in)
    and return a Figure with .points (named (x, y) spots, figure-local) shifted to match"""
    m = ~np.equal(g, None)
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    f = Figure(g[y0:y1, x0:x1].copy(), ax - x0, ay - y0,
               {k: v[y0:y1, x0:x1].copy() for k, v in (parts or {}).items()})
    f.points = _move_pts(points or {}, -x0, -y0)
    return f

def _move_pts(points, dx, dy, mirror_w=None):
    def mv(p):
        x, y = int(p[0]) + dx, int(p[1]) + dy
        return (int(mirror_w - 1 - x) if mirror_w is not None else int(x), int(y))
    return {k: ([mv(p) for p in v] if isinstance(v, list) else mv(v)) for k, v in points.items()}

def _flip_fig(f):
    """Figure.flip that also mirrors .points"""
    g = f.flip()
    g.points = _move_pts(getattr(f, 'points', {}), 0, 0, mirror_w=f.w)
    return g

def _ol(g, outline, ol, parts=None):
    if outline:
        _outline(g, outline if outline in ('slot', 'part') else 'slot', ol=ol)

# ---------------------------------------------------------------- 04 boats
BOATS = {
    # L: length; rise: sheer rise (stern, bow) above the low point at u = low; free: freeboard at the
    # low point; draft: rows under the waterline; stem / stern: columns the stem rakes and the
    # transom rakes over; transom: share of the stern depth the transom keeps; fore: forefoot curve;
    # beam: 3/4 view interior depth in px; tw: transom width share; plank: plank height in px
    'dory': dict(L=26, rise=(2, 3), free=3, draft=1, low=0.45, stem=6, stern=2, transom=0.5, fore=1.0,
                 beam=3, tw=0.4, plank=2, thwarts=(0.3, 0.6), mast=0, mast_at=0.68, mast_w=1),
    'sail': dict(L=40, rise=(1, 3), free=4, draft=2, low=0.5, stem=9, stern=4, transom=0.45, fore=1.4,
                 beam=5, tw=0.5, plank=2, thwarts=(0.24,), mast=30, mast_at=0.62, mast_w=2),
    'fishing': dict(L=48, rise=(1, 4), free=6, draft=2, low=0.4, stem=7, stern=2, transom=0.8, fore=1.4,
                    beam=7, tw=0.75, plank=3, thwarts=(), mast=16, mast_at=0.74, mast_w=2,
                    house=(0.14, 0.40, 8)),
}

def boat(kind='dory', view='side', length=None, facing='right', mast=None, sail=None, oars=False,
         hull='hull', wood='wood', stripe='trim', bottom='bottom', canvas_='sail', house='house',
         glass=('glass2', 'glass3'), rope='rope', outline='slot', ol='ol'):
    """a moored boat, side or 3/4 view (04 Sea of Stars harbour: hulls drawn as a sheer line,
    1 px plank seams, a lit gunwale and a waterline stripe; every design original). kind: 'dory'
    (26 px, strong sheer, raked stem and narrow transom, two thwarts), 'sail' (40 px, a mast and
    a boom), 'fishing' (48 px, a high bow, a wheelhouse with windows and a short mast with a
    crosstree). view 'side' or '3q' (the far gunwale and the inside show above the near one, with
    the thwarts). length rescales the hull. mast: px tall (None = the kind's default, 0 = none;
    a dory takes e.g. mast=14). sail: 'furled' (on the boom, the sail kind's default), 'up' (a
    triangle) or None. oars=True rests an oar in its thole (dory). Slots: hull0-3 (hull3 the lit
    gunwale, hull1 the seams), trim2 (the waterline stripe), bottom0-1 (below the waterline),
    wood0-3 (inside, thwarts, spars), sail1-3, house0-3, glass, rope. Ropes and the mast are drawn
    after the outline, so they stay 1-2 px. Returns a Figure anchored at the hull's middle on the
    waterline row; parts {'hull', 'below', 'inside', 'house', 'sail'}; .points {'bow', 'stern',
    'mast_top', 'seats', 'thole', 'deck'} for mooring lines, pennants and figures."""
    K = dict(BOATS[kind])
    if length:
        sc = length / float(K['L'])
        K['L'] = int(length)
        K['stem'] = max(2, int(round(K['stem'] * sc)))
        K['stern'] = max(1, int(round(K['stern'] * sc)))
    L = K['L']
    if mast is None:
        mast = K['mast']
    if sail is None and kind == 'sail':
        sail = 'furled'
    q = view in ('3q', '3/4')
    W, PAD, HEAD = L + 24, 12, mast + 30
    P = _P(W, HEAD + 16, oy=HEAD)                       # local y = 0 is the waterline row
    r = lambda b, k: '%s%d' % (b, k)
    xs = np.arange(L)
    u = xs / float(L - 1)
    m = K['low']
    rs, rb = K['rise']
    top = np.where(u < m, -K['free'] - rs * ((m - u) / m) ** 2,
                   -K['free'] - rb * ((u - m) / (1 - m)) ** 2)
    top = np.round(top).astype(int)
    bot = np.full(L, K['draft'])
    st, sn = K['stem'], K['stern']
    for x in range(L - st, L):                          # the stem rakes up to a 1 px head
        t = (x - (L - 1 - st)) / float(st)
        bot[x] = int(round(K['draft'] + (top[x] - K['draft']) * t ** K['fore']))
    b0 = top[0] + int(round(K['transom'] * (K['draft'] - top[0])))
    for x in range(0, sn):                              # the transom rakes aft at the top
        t = 1 - x / float(sn)
        bot[x] = int(round(K['draft'] + (b0 - K['draft']) * t))
    bot = np.maximum(bot, top)
    X = lambda x: x + PAD
    # plan half-beam for the 3/4 view: 0 at the stem, tw * beam at the transom
    bm = np.where(u > m, K['beam'] * (1 - ((u - m) / (1 - m)) ** 2),
                  K['beam'] * (1 - (1 - K['tw']) * ((m - u) / m) ** 2))
    far = top - (np.round(bm).astype(int) if q else 0)
    parts = {k: np.zeros(P.g.shape, bool) for k in ('hull', 'below', 'inside', 'house', 'sail')}
    def mark(name, x, y):
        yy = y + P.oy
        if 0 <= x < W and 0 <= yy < P.H:
            parts[name][yy, x] = True
    pts = {'bow': (X(L - 1), int(top[-1])), 'stern': (X(0), int(top[0])), 'seats': []}
    if q:                                               # the inside: far rail, far inner face, floor
        for x in range(L):
            if far[x] >= top[x]:
                continue
            P.put(X(x), far[x], r(hull, 2))
            mark('hull', X(x), far[x])
            for y in range(far[x] + 1, top[x]):
                P.put(X(x), y, r(wood, 2) if y == far[x] + 1 else r(wood, 1))
                mark('inside', X(x), y)
            if x == 0:                                  # the transom's inner face
                for y in range(far[x] + 1, top[x]):
                    P.put(X(x), y, r(hull, 2))
        for tu in K['thwarts']:
            xt = int(round(tu * (L - 1)))
            for dx in (0, 1):
                for y in range(far[xt + dx] + 2, top[xt + dx]):
                    P.put(X(xt + dx), y, r(wood, 3))
            pts['seats'].append((X(xt), int((far[xt] + top[xt]) // 2)))
    elif K['thwarts']:
        for tu in K['thwarts']:
            xt = int(round(tu * (L - 1)))
            pts['seats'].append((X(xt), int(top[xt]) - 1))
    if K.get('house'):                                  # the wheelhouse, behind the near rail
        h0, h1, hh = K['house']
        x0, x1 = int(round(h0 * L)), int(round(h1 * L))
        base = int(top[x0:x1 + 1].max())
        if q:
            base = int((far[x0:x1 + 1].max() + top[x0:x1 + 1].max()) // 2) + 1
        yr = base - hh
        roof = 2 if q else 1
        if q:                                           # the roof's top face
            P.rect(X(x0), yr - 1, X(x1 + 1), yr, r(house, 3))
        P.rect(X(x0 - 1), yr, X(x1 + 2), yr + 1, r(house, 2 if q else 3))
        P.rect(X(x0), yr + 1, X(x1 + 1), base + 1, r(house, 2))
        P.rect(X(x0), yr + 1, X(x0 + 1), base + 1, r(house, 3))
        P.rect(X(x1), yr + 1, X(x1 + 1), base + 1, r(house, 1))
        P.rect(X(x0), yr + 1, X(x1 + 1), yr + 2, r(house, 0))
        for px in range(x0 + 2, x1 - 1, 4):            # 3 px panes, 1 px mullions
            n = min(3, x1 - 1 - px)
            if n >= 2:
                P.rect(X(px), yr + 3, X(px + n), yr + 5, glass[0])
                P.put(X(px), yr + 3, glass[1])
        for y in range(yr - roof + 1, base + 1):
            for x in range(x0 - 1, x1 + 2):
                if P.get(X(x), y) is not None and str(P.get(X(x), y)).startswith(house):
                    mark('house', X(x), y)
        pts['roof'] = (X(x1), yr - roof + 1)
    for x in range(L):                                  # the hull side: rail, planks, stripe, bottom
        for y in range(top[x], bot[x] + 1):
            d = y - top[x]
            if y >= 1:
                v = r(bottom, 0 if y == bot[x] else 1)
                mark('below', X(x), y)
            elif y == 0:
                v = '%s2' % stripe
            elif d == 0:
                v = r(hull, 3)
            elif (d - 1) % K['plank'] == K['plank'] - 1:
                v = r(hull, 1)
            else:
                v = r(hull, 2)
            P.put(X(x), y, v)
            mark('hull', X(x), y)
    xm = int(round(K['mast_at'] * (L - 1)))
    foot = int(top[xm]) if not q else int((far[xm] + top[xm]) // 2)
    mtop = foot - mast
    if mast and sail in ('furled', 'up'):               # spars and sail join the outlined silhouette
        yb = foot - 4
        xb = int(round(0.1 * (L - 1)))
        P.rect(X(xb), yb, X(xm), yb + 1, r(wood, 2))
        if sail == 'furled':
            P.rect(X(xb + 1), yb - 2, X(xm - 1), yb - 1, '%s3' % canvas_)
            P.rect(X(xb + 1), yb - 1, X(xm - 1), yb, '%s2' % canvas_)
            for x in range(xb + 3, xm - 2, 5):          # sail ties
                P.put(X(x), yb - 2, '%s1' % canvas_); P.put(X(x), yb - 1, '%s1' % canvas_)
        else:
            for y in range(mtop + 2, yb):
                f = (y - (mtop + 2)) / float(max(1, yb - 1 - (mtop + 2)))
                xl = int(round(xm - 1 - f * (xm - 1 - xb)))
                P.rect(X(xl), y, X(xm), y + 1, '%s2' % canvas_)
                P.put(X(xl), y, '%s3' % canvas_)        # the lit leech
            P.rect(X(xb + 1), yb - 1, X(xm), yb, '%s1' % canvas_)
        for y in range(mtop, yb + 1):
            for x in range(xb, xm):
                if P.get(X(x), y) is not None and str(P.get(X(x), y)).startswith(canvas_):
                    mark('sail', X(x), y)
        pts['boom_end'] = (X(xb), yb)
    _ol(P.g, outline, ol)
    if mast:                                            # after the outline: a 1-2 px spar
        if K['mast_w'] >= 2 and mast > 8:
            P.rect(X(xm), mtop, X(xm + 1), foot, r(wood, 3))
            P.rect(X(xm + 1), mtop, X(xm + 2), foot, r(wood, 1))
        else:
            P.rect(X(xm), mtop, X(xm + 1), foot, r(wood, 2))
        pts['mast_top'] = (X(xm), mtop)
        if kind != 'dory':
            P.line(X(xm), mtop + 1, X(L - 1), int(top[-1]) - 1, rope)          # forestay
        if 'boom_end' in pts:
            P.line(X(xm) - 1, mtop + 1, pts['boom_end'][0], pts['boom_end'][1] - 3, rope)  # topping lift
        if kind == 'fishing':
            P.rect(X(xm - 2), mtop + 3, X(xm + 4), mtop + 4, r(wood, 2))     # crosstree
            if 'roof' in pts:
                P.line(X(xm) - 1, mtop + 4, pts['roof'][0] + 1, pts['roof'][1] - 1, rope)
    if oars:
        xo = int(round(0.5 * (L - 1)))
        yo = int(top[xo])
        P.put(X(xo), yo - 1, r(wood, 1))                # the thole pin
        P.line(X(xo - 4), yo - 2, X(xo + 5), 0, r(wood, 3))
        P.rect(X(xo + 5), 0, X(xo + 8), 2, r(wood, 3))  # the blade at the water
        pts['thole'] = (X(xo), yo - 1)
    pts['deck'] = (X(L // 2), int(top[L // 2]) - (1 if not q else int(bm[L // 2]) // 2))
    f = _fig(P.g, X(L // 2), P.oy, {k: (v[0], v[1] + P.oy) if not isinstance(v, list)
                                    else [(a, b + P.oy) for a, b in v] for k, v in pts.items()},
             parts)
    return _flip_fig(f) if facing == 'left' else f

# ---------------------------------------------------------------- 04 dock / jetty
def dock(c, x0, x1, y, bottom, top=2, face=3, plank=4, pile_every=6, pile_w=2, missing=(), broken=(),
         short=None, posts=(), braces=False, wood='wood', nail='nail', seed=0):
    """a wooden jetty seen from the side, slightly from above (04 Sea of Stars quays and jetties:
    plank seams, a lit deck edge, a piling rhythm with one break): `top` rows of deck surface from
    row y (planks across the jetty, `plank` px each with a 1 px wood1 seam, a hashed few a step
    darker; top >= 6 is a top-down deck with nail rows), a `face` px stringer under it (wood2,
    a wood0 shadow row, a nail where each pile is bolted), piles every `pile_every` px from the
    stringer down to `bottom` (pile_w px: wood2 lit left, wood1 between, wood0 right). missing: plank
    indices left out (negative counts from the end; the background shows through), broken:
    plank indices drawn cracked and sagging 1 px, short: {pile index: px shorter}, posts: pile
    indices that stand 3 px above the deck as mooring posts, braces: an X brace in every other
    bay. Returns {'mask', 'deck', 'piles' (masks), 'pile_x', 'gaps' [(x0, x1)], 'posts' [(x, y)]}."""
    r = lambda k: '%s%d' % (wood, k)
    H, W = c.g.shape
    before = c.g.copy()
    nplank = max(1, int(math.ceil((x1 - x0) / float(plank))))
    norm = lambda s: set(i % nplank for i in s)
    miss, brk = norm(missing), norm(broken)
    short = short or {}
    ys0 = y + top                                        # stringer top
    piles = []
    px = int(x0) + 1
    while px + pile_w <= x1 - 1:
        piles.append(px)
        px += pile_every
    if piles and x1 - 1 - pile_w - piles[-1] > pile_every // 2:
        piles.append(int(x1) - 1 - pile_w)
    pile_mask = np.zeros((H, W), bool)
    if braces:
        for k in range(0, len(piles) - 1, 2):
            a, b = piles[k] + pile_w, piles[k + 1] - 1
            yb0, yb1 = ys0 + face + 1, min(bottom, ys0 + face + 1 + (b - a))
            c.line(a, yb0, b, yb1, r(1)); c.line(a, yb1, b, yb0, r(1))
    cols = [2] + [1] * (pile_w - 2) + [0] if pile_w >= 3 else [2, 0][:pile_w]
    out_posts = []
    for k, px in enumerate(piles):
        ye = bottom - int(short.get(k, 0))
        for i in range(pile_w):
            c.rect(px + i, ys0, px + i + 1, ye, r(cols[i]))
        pile_mask[max(0, ys0):max(0, ye), max(0, px):px + pile_w] = True
    deck = np.zeros((H, W), bool)
    gaps = []
    for i in range(nplank):
        a, b = int(x0) + i * plank, min(int(x1), int(x0) + (i + 1) * plank)
        if i in miss:
            gaps.append((a, b))
            continue
        tone = 2 if _h(i, 11, seed) < 0.18 else 3
        sag = 1 if i in brk else 0
        for x in range(a, b):
            seam = x == b - 1
            crack = sag and x == a + (b - a) // 2
            for j in range(top):
                yy = y + j
                if sag and x > a + (b - a) // 2:
                    if j == 0:
                        continue                         # the broken half drops a row
                if crack:
                    v = r(0)
                elif seam:
                    v = r(1)
                elif top >= 6 and (j in (1, top - 2)) and x == a + 1:
                    v = nail
                else:
                    v = r(tone)
                c.put(x, yy, v)
                if 0 <= x < W and 0 <= yy < H:
                    deck[yy, x] = True
    c.rect(x0, ys0, x1, ys0 + face - 1, r(2))           # the stringer
    c.rect(x0, ys0 + face - 1, x1, ys0 + face, r(0))
    if face >= 3:
        c.rect(x0, ys0, x1, ys0 + 1, r(1))              # the seam under the deck edge
    for k, px in enumerate(piles):
        if k in posts:                                  # mooring posts stand in front, 3 px proud
            yt = y - 3
            for i in range(pile_w):
                c.rect(px + i, yt, px + i + 1, ys0 + face, r(cols[i]))
            c.rect(px, yt, px + pile_w, yt + 1, r(3))
            pile_mask[max(0, yt):ys0 + face, max(0, px):px + pile_w] = True
            out_posts.append((px + pile_w // 2, yt))
        else:
            c.put(px + pile_w // 2, ys0 + face // 2, nail)
    deck[max(0, ys0):ys0 + face, max(0, x0):x1] = True
    return {'mask': ~np.equal(c.g, before), 'deck': deck, 'piles': pile_mask, 'pile_x': piles,
            'gaps': gaps, 'posts': out_posts}

# ---------------------------------------------------------------- 10 mine cart, crate, barrel, ore
_WHEEL5 = """
    .ooo.
    oiIio
    oIhIo
    oiIio
    .ooo."""

def _heap(P, x0, x1, ybase, hmax, rock, ore, seed, flecks=3):
    """an ore heap over [x0, x1) whose foot is row ybase: 3 x 2 px lumps in rock1/rock2 with a
    rock3 lit top-left pixel, and 2 px ore clusters (ore2 glint, ore1)"""
    w = x1 - x0
    if hmax <= 0 or w <= 2:
        return []
    cx = (x0 + x1 - 1) / 2.0
    hs = []
    for x in range(x0, x1):
        d = abs(x - cx) / (w / 2.0)
        lump = 1 if _h(x // 3, 21, seed) < 0.35 else 0
        hs.append(max(1, int(round(hmax * math.sqrt(max(0.0, 1 - d * d)))) + lump - (1 if d > 0.8 else 0)))
    hs[0] = min(hs[0], max(1, hmax // 2)); hs[-1] = min(hs[-1], max(1, hmax // 2))
    for i, x in enumerate(range(x0, x1)):
        for k in range(min(hs[i], hmax + 1)):
            yy = ybase - k
            row = (ybase - yy) // 2
            cell = (x + (row % 2) * 1) // 3
            st = 1 if _h(cell, row, seed) < 0.45 else 2
            lit = k == hs[i] - 1 and (x + (row % 2)) % 3 == 0
            P.put(x, yy, '%s%d' % (rock, 3 if lit else st))
    out = []
    for n in range(flecks):
        i = int(_h(n, 23, seed) * max(1, w - 3)) + 1
        k = int(_h(n, 24, seed) * max(1, hs[i] - 1))
        x, yy = x0 + i, ybase - k
        if P.get(x, yy) is not None and P.get(x + 1, yy) is not None:
            P.put(x, yy, '%s2' % ore); P.put(x + 1, yy, '%s1' % ore)
            out.append((x, yy))
    return out

def mine_cart(view='side', w=None, h=None, load=0.5, dent=None, along='x', body='iron', rim='wood',
              rock='rock', ore='ore', nail='nail', seed=0, outline='slot', ol='ol'):
    """a mine cart (10 Stardew Valley mine: a tub on rails, read by its trapezoid and two small
    wheels; the design original). view 'side': a w x h (26 x 18) trapezoid tub, a 2 px timber
    rim (wood3 lit, wood2), an iron body (iron1, lit left edge iron2, dark right edge and floor
    iron0) with two 2 px iron2 straps and rivets, two 5 px wheels in front; anchored at the
    wheels' contact row (stamp it at (x, y + gauge // 2) on a props.rails centreline, or use
    cart_on_rails). view 'top': a top-down w x h (18 x 12) tub (along 'x' or 'y'): timber rim,
    inner walls in shadow on the lit side, a bumper at each end, anchored at its centre. load
    0..1: an ore heap of rock1-3 lumps with ore1-2 flecks (4 rows over the rim at 1). dent:
    'left' / 'right', a 2 px notch in that top corner. Returns a Figure; .points {'flecks',
    'load'} (where glints and dropped lumps go)."""
    r = lambda b, k: '%s%d' % (b, k)
    if view == 'top':
        L, D = (w or 18), (h or 12)
        P = _P(L + 6, D + 6)
        ox, oy = 3, 3
        P.rect(ox, oy, ox + L, oy + D, r(rim, 2))
        P.rect(ox, oy, ox + L, oy + 1, r(rim, 3)); P.rect(ox, oy, ox + 1, oy + D, r(rim, 3))
        P.rect(ox, oy + D - 1, ox + L, oy + D, r(rim, 1)); P.rect(ox + L - 1, oy, ox + L, oy + D, r(rim, 1))
        P.rect(ox + 1, oy + 1, ox + L - 1, oy + D - 1, r(body, 1))
        P.rect(ox + 1, oy + 1, ox + L - 1, oy + 2, r(body, 0)); P.rect(ox + 1, oy + 1, ox + 2, oy + D - 1, r(body, 0))
        fl = []
        if load > 0:
            fl = _heap(P, ox + 2, ox + L - 1, oy + D - 2, int(round(load * (D - 4))), rock, ore, seed)
        cy = oy + D // 2
        P.rect(ox - 1, cy - 1, ox, cy + 1, r(body, 2)); P.rect(ox + L, cy - 1, ox + L + 1, cy + 1, r(body, 2))
        if dent in ('left', 'right'):
            dx = ox if dent == 'left' else ox + L - 2
            P.rect(dx, oy, dx + 2, oy + 1, None); P.put(dx + (1 if dent == 'left' else 0), oy + 1, r(rim, 1))
        _ol(P.g, outline, ol)
        f = _fig(P.g, ox + L // 2, oy + D // 2, {'flecks': fl, 'load': (ox + L // 2, oy + D // 2)})
        if along == 'y':
            g = f.g.T.copy()
            f2 = Figure(g, f.ay, f.ax)
            f2.points = {k: ([(b, a) for a, b in v] if isinstance(v, list) else (v[1], v[0]))
                         for k, v in f.points.items()}
            return f2
        return f
    w, h = (w or 26), (h or 18)
    P = _P(w + 4, h + 8, oy=6)
    ox = 2
    yb0, yb1 = 4, h - 3                                  # body rows (rim first) above the wheel centres
    n = yb1 - yb0
    for j in range(n):
        y = yb0 + j
        ins = 0 if j < 2 else 1 + int(round(2.0 * (j - 2) / max(1, n - 3)))
        a, b = ox + ins, ox + w - ins
        if j == 0:
            P.rect(a, y, b, y + 1, r(rim, 3))
        elif j == 1:
            P.rect(a, y, b, y + 1, r(rim, 2))
        else:
            P.rect(a, y, b, y + 1, r(body, 0 if j == n - 1 else 1))
            if j < n - 1:
                P.put(a, y, r(body, 2)); P.put(b - 1, y, r(body, 0))
    for sx in (int(round(w * 0.3)), int(round(w * 0.7)) - 2):   # straps with rivets
        P.rect(ox + sx, yb0 + 2, ox + sx + 2, yb1 - 1, r(body, 2))
        P.put(ox + sx, yb0 + 3, nail); P.put(ox + sx + 1, yb1 - 3, nail)
    fl = []
    if load > 0:
        fl = _heap(P, ox + 2, ox + w - 2, yb0 - 1, int(round(load * 4)), rock, ore, seed)
    if dent in ('left', 'right'):
        dx = ox if dent == 'left' else ox + w - 2
        P.rect(dx, yb0, dx + 2, yb0 + 2, None)
        P.put(dx + (1 if dent == 'left' else 0), yb0 + 2, r(body, 0))
    key = {'o': r(body, 0), 'i': r(body, 1), 'I': r(body, 2), 'h': nail}
    for wx in (5, w - 6):
        P.stamp(_WHEEL5, key, ox + wx - 2, h - 5)
    _ol(P.g, outline, ol)
    return _fig(P.g, ox + w // 2, h - 1 + P.oy,
                {'flecks': [(x, y + P.oy) for x, y in fl], 'load': (ox + w // 2, yb0 - 1 + P.oy)})

def rail_point(pts, s, gauge=8, corner_r=4):
    """the point at arc length s px along a props.rails centreline (10), with the same fillets:
    -> (x, y, tx, ty), the tangent a unit vector. s is clamped to the track."""
    path = _fillet(pts, corner_r + gauge / 2.0)
    i = int(max(0, min(len(path) - 1, round(s))))
    x, y, tx, ty = path[i]
    return float(x), float(y), float(tx), float(ty)

def cart_on_rails(c, pts, s, gauge=8, corner_r=4, **cart):
    """stamp a mine_cart onto a props.rails track (10) at arc length s: a side-view cart on
    horizontal and 45 degree runs (wheels on the near rail), a top-view cart along y on vertical
    runs. cart: mine_cart keywords. Returns (box, figure)."""
    x, y, tx, ty = rail_point(pts, s, gauge, corner_r)
    if abs(tx) >= abs(ty):
        f = mine_cart(view='side', **cart)
        return f.stamp(c, x, y + gauge // 2), f
    f = mine_cart(view='top', along='y', **cart)
    return f.stamp(c, x, y), f

def crate(w=16, h=12, top=3, kind='closed', crack=None, wood='wood', nail='nail', contents=None,
          seed=0, outline='slot', ol='ol'):
    """a wooden crate, front face plus `top` rows of lid (10 Stardew Valley / 05 Metal Slug props:
    a lit frame board around a darker recessed panel, nails at the corners). kind 'closed' (panel
    planks with 1 px seams and a 2 px diagonal brace), 'slat' (2 px slats over dark gaps), 'open'
    (no lid: the back rim and a dark inside, filled with the `contents` slot if given). top=0
    draws the front only. crack: 'left' / 'right', a 2 px notch in that top corner and a 3 px
    crack. Slots wood0-3 (wood3 the lid), nail. Returns a Figure anchored at the bottom centre;
    .points {'top'} (where a mug or a lantern stands)."""
    r = lambda k: '%s%d' % (wood, k)
    P = _P(w + 2, h + top + 2)
    ox, oy = 1, 1 + top
    if top:
        if kind == 'open':
            P.rect(ox + 1, 1, ox + w - 1, 2, r(3))
            P.rect(ox, 2, ox + w, oy, r(0))
            P.rect(ox, 1, ox + 1, oy, r(3)); P.rect(ox + w - 1, 1, ox + w, oy, r(2))
            if contents and top >= 2:
                P.rect(ox + 2, oy - 1 - min(2, top - 2), ox + w - 2, oy, contents)
        else:
            P.rect(ox + 1, 1, ox + w - 1, oy, r(3))
            P.rect(ox, 2, ox + w, oy, r(3))
            for x in range(ox + 4, ox + w - 1, 5):
                P.rect(x, 1, x + 1, oy, r(2))
    P.rect(ox, oy, ox + w, oy + h, r(2))                 # the frame boards
    P.rect(ox, oy, ox + w, oy + 1, r(3))
    P.rect(ox, oy + h - 1, ox + w, oy + h, r(1))
    ix0, iy0, ix1, iy1 = ox + 2, oy + 2, ox + w - 2, oy + h - 2
    if kind == 'slat':
        for y in range(iy0, iy1):
            P.rect(ix0, y, ix1, y + 1, r(0) if (y - iy0) % 3 == 2 else r(2 if (y - iy0) % 3 == 0 else 1))
    else:
        P.rect(ix0, iy0, ix1, iy1, r(1))
        for y in range(iy0 + 2, iy1, 3):
            P.rect(ix0, y, ix1, y + 1, r(0))
        if kind == 'closed':
            n = ix1 - ix0
            for i in range(n):
                yy = iy1 - 1 - int(round(i * (iy1 - iy0 - 1) / float(max(1, n - 1))))
                P.put(ix0 + i, yy, r(2)); P.put(ix0 + i, yy - 1 if yy - 1 >= iy0 else yy, r(2))
    P.rect(ix0, iy0, ix1, iy0 + 1, r(0))                 # the frame's shadow on the panel
    for (x, y) in ((ox + 1, oy + 1), (ox + w - 2, oy + 1), (ox + 1, oy + h - 2), (ox + w - 2, oy + h - 2)):
        P.put(x, y, nail)
    if crack in ('left', 'right'):
        cx = ox if crack == 'left' else ox + w - 2
        y0 = 1 if top else oy
        P.rect(cx, y0, cx + 2, y0 + 2, None)
        kx = cx + (2 if crack == 'left' else -1)
        for k in range(3):
            P.put(kx + (k // 2 if crack == 'left' else -(k // 2)), oy + k, r(0))
    _ol(P.g, outline, ol)
    return _fig(P.g, ox + w // 2, oy + h - 1, {'top': (ox + w // 2, 1 if top else oy)})

def barrel(w=10, h=14, top=2, lid=True, hoops=(0.15, 0.85), dent_hoop=None, wood='wood', iron='iron',
           inside='water1', outline='slot', ol='ol'):
    """a stave barrel (10 Stardew Valley / 07 Freitas column bands: a cylinder lit from the left
    as flat column bands, never pillow shading): w x h staves bulging 1 px at the middle, bands
    wood2 | wood3 | wood2 | wood1 | wood0 left to right, iron hoops at `hoops` (row shares, the
    same bands in iron0-2), and `top` rows of lid (wood3 under a wood2 back rim; lid=False shows
    the `inside` slot, a rain barrel's water). dent_hoop: index of a hoop dented 1 px down on
    its right. Returns a Figure anchored at the bottom centre; .points {'top'} (the lid or water
    centre, for drizzle rings)."""
    P = _P(w + 2, h + top + 2)
    ox, oy = 1, 1 + top
    cx = ox + w / 2.0
    def span(j):
        e = abs((j + 0.5) - h / 2.0) / (h / 2.0)
        ins = 1 if e > 0.72 else 0
        return ox + ins, ox + w - ins
    def band(f, ramp, darker=0):
        st = 2 if f < 0.18 else 3 if f < 0.45 else 2 if f < 0.72 else 1 if f < 0.9 else 0
        if ramp == iron:
            st = {3: 2, 2: 1, 1: 1, 0: 0}[st]
        return '%s%d' % (ramp, max(0, st - darker))
    hoop_rows = {}
    for k, hf in enumerate(hoops):
        hoop_rows[k] = min(h - 1, max(0, int(round(hf * (h - 1)))))
    for j in range(h):
        a, b = span(j)
        for x in range(a, b):
            f = (x - a + 0.5) / float(b - a)
            ramp = wood
            for k, hr in hoop_rows.items():
                dy = 1 if (k == dent_hoop and x >= a + (b - a) * 0.55 and x < b - 1) else 0
                if j == hr + dy:
                    ramp = iron
            P.put(x, oy + j, band(f, ramp, 1 if (j == 0 and top) else 0))   # the chime under the lid
    if top:
        a, b = span(0)
        P.rect(a + 1, oy - top, b - 1, oy - top + 1, '%s2' % wood)
        for k in range(1, top):
            y = oy - top + k
            if lid:
                P.rect(a, y, b, y + 1, '%s3' % wood)
            else:
                P.rect(a, y, b, y + 1, '%s2' % wood)
                P.rect(a + 1, y, b - 1, y + 1, inside)
    _ol(P.g, outline, ol)
    return _fig(P.g, ox + w // 2, oy + h - 1, {'top': (ox + w // 2, oy - max(1, top) + (1 if top > 1 else 0))})

def ore_node(w=14, h=10, ore='ore', rock='rock', flecks=4, lobes=3, seed=0, outline='slot', ol='ol'):
    """a rock with ore in it (10 Stardew Valley mine: a squat lumpy stone, a lit cap and a dark
    right side as flat planes, small ore clusters set into it; the design original): `lobes`
    hash-placed domes (the middle one tallest) in a w x h box, each lit as planes: rock3 on the
    top-left cap, rock2 the front, rock1 the right side and the base row, rock0 cracks down from
    the valleys between lobes. flecks: 2-3 px ore clusters (ore2 glint, ore1 body, ore0 under
    it) kept off the edges, never touching each other. ore: the ore ramp (copper, iron, gem:
    swap the slot). Returns a Figure anchored at the bottom centre; parts {'ore'}; .points
    {'flecks'} (glint pixels, for anim.hold sparkles)."""
    P = _P(w + 2, h + 2)
    ox, oy = 1, 1
    base = oy + h - 1
    L = []
    for k in range(max(1, lobes)):
        if k == 0:
            L.append((w / 2.0 + (_h(k, 31, seed) - 0.5) * w * 0.15, w * 0.36, h))
        else:
            side = -1 if k % 2 else 1
            cxk = w / 2.0 + side * w * (0.24 + 0.08 * _h(k, 32, seed))
            L.append((cxk, w * (0.22 + 0.06 * _h(k, 33, seed)), h * (0.55 + 0.2 * _h(k, 34, seed))))
    tops, owner = [], []
    for i in range(w):
        x = i + 0.5
        best, bk = 0, 0
        for k, (cxk, rxk, hk) in enumerate(L):
            d = (x - cxk) / rxk
            v = hk * math.sqrt(max(0.0, 1 - d * d)) if abs(d) < 1 else 0
            if v > best:
                best, bk = v, k
        tops.append(max(1 if 0 < i < w - 1 else 0, int(round(best))))
        owner.append(bk)
    for i in range(w):
        if tops[i] == 0:
            continue
        cxk, rxk, hk = L[owner[i]]
        d = (i + 0.5 - cxk) / rxk
        for k in range(tops[i]):
            y = base - k
            depth = tops[i] - 1 - k
            if k == 0:
                st = 1
            elif d > 0.3:
                st = 1
            elif depth < 2 and d < 0.25:
                st = 3
            else:
                st = 2
            P.put(ox + i, y, '%s%d' % (rock, st))
    for i in range(1, w - 1):                            # cracks down from the valleys
        if owner[i] != owner[i - 1] and tops[i] >= 3:
            j = i if tops[i] <= tops[i - 1] else i - 1
            for k in range(2):
                P.put(ox + j, base - tops[j] + 1 + k, '%s0' % rock)
    om = np.zeros(P.g.shape, bool)
    out, taken = [], []
    shapes = (((0, 0), (1, 0)), ((0, 0), (0, 1)), ((0, 0), (1, 0), (0, 1)))
    for n in range(flecks * 6):
        if len(out) >= flecks:
            break
        i = 2 + int(_h(n, 35, seed) * max(1, w - 5))
        if tops[i] < 4:
            continue
        k = 2 + int(_h(n, 36, seed) * max(1, tops[i] - 3))
        x, y = ox + i, base - k
        shp = shapes[int(_h(n, 37, seed) * 3) % 3]
        cells = [(x + a, y + b) for a, b in shp]
        if any(abs(px - qx) < 3 and abs(py - qy) < 3 for px, py in cells for qx, qy in taken):
            continue
        if not all(P.get(px, py) is not None and str(P.get(px, py)) != '%s0' % rock and
                   P.get(px + 1, py) is not None and P.get(px, py + 1) is not None for px, py in cells):
            continue
        for j, (px, py) in enumerate(cells):
            P.put(px, py, '%s%d' % (ore, 2 if j == 0 else 1))
            om[py, px] = True
        lx, ly = cells[-1]
        if P.get(lx, ly + 1) is not None and str(P.get(lx, ly + 1)).startswith(rock) and ly + 1 < base:
            P.put(lx, ly + 1, '%s0' % ore); om[ly + 1, lx] = True
        taken += cells
        out.append(cells[0])
    _ol(P.g, outline, ol)
    return _fig(P.g, ox + w // 2, base, {'flecks': out}, {'ore': om})

# ---------------------------------------------------------------- 09 pipes and drains
def _pipe_bands(w):
    """cross-section steps for a w px pipe lit from the upper left: top (or left) edge step 2, the
    highlight step 3, then 2 ... a step 1 and the dark far edge step 0"""
    if w <= 1:
        return [2]
    if w == 2:
        return [3, 1]
    if w == 3:
        return [3, 2, 0]
    return [2, 3] + [2] * (w - 4) + [1, 0]

def pipe(c, pts, w=4, ramp='pipe', joint_every=16, flanges=True, start=None, end=None, void='void'):
    """a pipe run along an axis-aligned polyline (09 Katana ZERO alleys: banded metal pipes,
    flanged joints, an elbow at each turn): straight runs in cross-section bands (_pipe_bands:
    lit along the top of horizontal runs and the left of vertical ones, ramp steps 0-3), round
    tight elbows whose bands follow the bend, 2 px flange collars 1 px proud every `joint_every`
    px and on both sides of each elbow. start / end: None (cut flat), 'cap' (a flange) or 'open'
    (a flange around a dark `void` mouth). Returns {'mask', 'joints' [(x, y)], 'elbows' [(x, y)],
    'drips' [(x, y)]}: drips are the pixels just under each joint of a horizontal run and under
    an open end that faces down, where fx drips should start."""
    H, W = c.g.shape
    before = c.g.copy()
    B = _pipe_bands(w)
    Bf = _pipe_bands(w + 2)
    lo = -(w // 2)
    def put(x, y, v):
        if 0 <= x < W and 0 <= y < H:
            c.g[y, x] = v
    pts = [(int(a), int(b)) for a, b in pts]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if ax != bx and ay != by:
            raise ValueError('pipe: runs must be horizontal or vertical: %r -> %r' % ((ax, ay), (bx, by)))
    segs = list(zip(pts, pts[1:]))
    joints, elbows, drips = [], [], []
    def flange(x, y, horiz, down_drip):
        """a 2 px collar centred across the run at (x, y): along the run px x, x+1 (or y, y+1)"""
        for k in range(2):
            for i, st in enumerate(Bf):
                st = max(0, st - k)
                if horiz:
                    put(x + k, y + lo - 1 + i, '%s%d' % (ramp, st))
                else:
                    put(x + lo - 1 + i, y + k, '%s%d' % (ramp, st))
        joints.append((x, y))
        if horiz and down_drip:
            drips.append((x + 1, y + lo + w + 1))
    for (ax, ay), (bx, by) in segs:                      # straight runs
        horiz = ay == by
        n = abs(bx - ax) if horiz else abs(by - ay)
        sg = 1 if (bx - ax if horiz else by - ay) > 0 else -1
        for k in range(n + 1):
            x, y = (ax + sg * k, ay) if horiz else (ax, ay + sg * k)
            for i, st in enumerate(B):
                if horiz:
                    put(x, y + lo + i, '%s%d' % (ramp, st))
                else:
                    put(x + lo + i, y, '%s%d' % (ramp, st))
    for j in range(1, len(pts) - 1):                     # elbows
        (ax, ay), (bx, by), (cx_, cy_) = pts[j - 1], pts[j], pts[j + 1]
        d0 = (np.sign(bx - ax), np.sign(by - ay))
        d1 = (np.sign(cx_ - bx), np.sign(cy_ - by))
        if d0 == d1:
            continue
        sx0, sy0 = bx + lo, by + lo                      # the corner square
        gx, gy = sx0 + w / 2.0, sy0 + w / 2.0
        piv = (gx + (w / 2.0) * (-d0[0] + d1[0]), gy + (w / 2.0) * (-d0[1] + d1[1]))
        # clear the square, then paint the quarter disc around the inner corner
        for yy in range(sy0, sy0 + w):
            for xx in range(sx0, sx0 + w):
                if 0 <= xx < W and 0 <= yy < H:
                    c.g[yy, xx] = before[yy, xx]
        for yy in range(sy0, sy0 + w):
            for xx in range(sx0, sx0 + w):
                vx, vy = xx + 0.5 - piv[0], yy + 0.5 - piv[1]
                d = math.hypot(vx, vy)
                if d > w + 0.2:
                    continue
                ux, uy = (vx / d, vy / d) if d > 1e-6 else (0.0, 0.0)
                s = d - w / 2.0
                t = s * (ux + uy) / max(1e-6, abs(ux) + abs(uy))
                i = int(max(0, min(w - 1, math.floor(t + w / 2.0))))
                put(xx, yy, '%s%d' % (ramp, B[i]))
        elbows.append((bx, by))
        if flanges:
            for d, inward in ((d0, True), (d1, False)):
                horiz = d[1] == 0
                if horiz:
                    fx = (sx0 - 2 if d[0] > 0 else sx0 + w) if inward else (sx0 + w if d[0] > 0 else sx0 - 2)
                    flange(fx, by, True, True)
                else:
                    fy = (sy0 - 2 if d[1] > 0 else sy0 + w) if inward else (sy0 + w if d[1] > 0 else sy0 - 2)
                    flange(bx, fy, False, False)
    if flanges and joint_every:                          # joints along the straight runs
        for si, ((ax, ay), (bx, by)) in enumerate(segs):
            horiz = ay == by
            n = abs(bx - ax) if horiz else abs(by - ay)
            sg = 1 if (bx - ax if horiz else by - ay) > 0 else -1
            for k in range(joint_every, n, joint_every):
                if k < w // 2 + 8 or k > n - w // 2 - 8:   # keep clear of elbow flanges and ends
                    continue
                x, y = (ax + sg * k, ay) if horiz else (ax, ay + sg * k)
                flange(x, y, horiz, True)
    for which, kind in (('start', start), ('end', end)):
        if not kind:
            continue
        (px_, py_), (qx, qy) = (pts[0], pts[1]) if which == 'start' else (pts[-1], pts[-2])
        horiz = py_ == qy
        sg = 1 if (px_ - qx if horiz else py_ - qy) > 0 else -1   # outward
        if horiz:
            flange(px_ - 1 if sg > 0 else px_, py_, True, False)
            if kind == 'open':                          # the mouth, seen a little from the side
                for i in range(1, w - 1):
                    put(px_, py_ + lo + i, void)
                drips.append((px_, py_ + lo + w + 1))
        else:
            flange(px_, py_ - 1 if sg > 0 else py_, False, False)
            if kind == 'open':
                for i in range(1, w - 1):
                    put(px_ + lo + i, py_, void)
                if sg > 0:
                    drips.append((px_ + lo + w // 2, py_ + 1))
    return {'mask': ~np.equal(c.g, before), 'joints': joints, 'elbows': elbows, 'drips': drips}

def drain(c, x, y, w=12, h=6, kind='floor', ramp='iron', void='void', pitch=2):
    """a drain grate (09 Katana ZERO alley floors and walls; the design original). kind 'floor': a
    grate seen from above in a w x h frame (iron1, its top row iron2 lit), bars every `pitch` px
    (iron1 with a lit iron2 top pixel) over dark slots (`void`, the far inner lip iron0). kind
    'wall': a w x h dark opening with 2 px bars (iron2 lit left, iron1) and a lit sill (iron2 over
    iron0). Returns {'mask', 'holes' (the void pixels), 'outfall' (x, y)}: the pixel under the
    middle of the grate or sill where a trickle or drip starts."""
    r = lambda k: '%s%d' % (ramp, k)
    H, W = c.g.shape
    before = c.g.copy()
    holes = np.zeros((H, W), bool)
    def hole(px, py):
        c.put(px, py, void)
        if 0 <= px < W and 0 <= py < H:
            holes[py, px] = True
    if kind == 'wall':
        for yy in range(y, y + h - 2):
            for xx in range(x, x + w):
                hole(xx, yy)
        bx = x + 1 + (w - 2 - ((w - 2) // 4) * 4) // 2
        while bx + 2 <= x + w - 1:
            c.rect(bx + 1, y, bx + 2, y + h - 2, r(2))
            c.rect(bx + 2, y, bx + 3, y + h - 2, r(1))
            if 0 <= y < H:
                holes[y:y + h - 2, bx + 1:bx + 3] = False
            bx += 4
        c.rect(x - 1, y + h - 2, x + w + 1, y + h - 1, r(2))
        c.rect(x - 1, y + h - 1, x + w + 1, y + h, r(0))
        out = (x + w // 2, y + h)
    else:
        c.rect(x, y, x + w, y + h, r(1))
        c.rect(x, y, x + w, y + 1, r(2))
        c.rect(x, y + h - 1, x + w, y + h, r(0))
        for xx in range(x + 1, x + w - 1):
            if (xx - x - 1) % pitch == 0 and xx < x + w - 2:
                for yy in range(y + 1, y + h - 1):
                    if yy == y + 1:
                        c.put(xx, yy, r(0))
                        if 0 <= xx < W and 0 <= yy < H:
                            holes[yy, xx] = False
                    else:
                        hole(xx, yy)
            else:
                c.put(xx, y + 1, r(2))
        out = (x + w // 2, y + h)
    return {'mask': ~np.equal(c.g, before), 'holes': holes, 'outfall': out}

# ---------------------------------------------------------------- demo palette
PALETTE = {
    'ol': '#000000', 'void': '#000000',
    'tyre1': '#782120', 'tyre2': '#bf5e5e', 'hub1': '#8b8b8b', 'hub2': '#c1bfc0',
    'glass2': '#0095c8', 'glass3': '#00c1ff', 'lamp_w': '#e8f6f8', 'lamp_r': '#ff3a2a', 'ad': '#ffffff',
    'seat0': '#3a1a10', 'seat1': '#5a2a1a', 'seat2': '#7a3a22', 'seat3': '#9a5030', 'seat4': '#b86a40',
    'pole0': '#4f4c4c', 'pole1': '#737272', 'pole2': '#adaba7', 'pole3': '#cfcfcf', 'pole4': '#f1f1f1',
    'bark0': '#962d00', 'bark1': '#af6600', 'bark2': '#e09622', 'bark3': '#f0b84a',
    'rail0': '#1d0d0a', 'rail1': '#4f3f2e', 'rail2': '#7f6a51',
    'tie0': '#1d0d0a', 'tie1': '#3e2412', 'tie2': '#6a3e1e', 'tie3': '#8e5a2c',
    'wood0': '#1d0d0a', 'wood1': '#4a2a16', 'wood2': '#6e4224', 'wood3': '#9a6236', 'nail': '#8a8a8a',
    'iron0': '#1a1416', 'iron1': '#4a4448', 'iron2': '#7a7276',
    'lamp1': '#c88a3a', 'lamp2': '#e7c259', 'lamp3': '#f8eba9',
    'metal0': '#080808', 'metal1': '#101012', 'metal2': '#202024',
    'step0': '#0d160c', 'step1': '#182917', 'step2': '#1e341a', 'step3': '#22401e', 'step4': '#344c2a',
    'hull0': '#3a1416', 'hull1': '#7a2a26', 'hull2': '#b0443a', 'hull3': '#e07a5a',
    'trim2': '#f1e2c0', 'bottom0': '#1e2a2c', 'bottom1': '#34484a',
    'sail1': '#b8a888', 'sail2': '#e6dcc4', 'sail3': '#fff6e0', 'rope': '#9a8a6a',
    'house0': '#4a4038', 'house1': '#9a8e7a', 'house2': '#d8ccb0', 'house3': '#f4ecd8',
    'rock0': '#1c1820', 'rock1': '#3a3440', 'rock2': '#5a5260', 'rock3': '#7e7484',
    'ore0': '#5a2a14', 'ore1': '#c87a3a', 'ore2': '#f2b874',
    'pipe0': '#14161a', 'pipe1': '#2e3238', 'pipe2': '#4c525a', 'pipe3': '#7a828c',
    'water1': '#2c4a63',
}
for _name, _hexes in {
        'pink': ('#7a0030', '#c4004e', '#ff0a6e', '#ff1a78', '#ff6aa4'),
        'teal': ('#004a4a', '#007a7a', '#00a8a0', '#00b8b0', '#5ae0d8'),
        'yellow': ('#7a6400', '#c8a800', '#ffd400', '#ffe02a', '#fff08a'),
        'red': ('#5a0000', '#a80000', '#e00000', '#ff1a1a', '#ff6a5a'),
        'green': ('#004a10', '#00801e', '#00b02e', '#1ac83e', '#7aff8a'),
        'white': ('#6a6a6a', '#a8a8a8', '#d8d8d8', '#e6e6e6', '#ffffff'),
        'violet': ('#3a1a6a', '#5a2aa8', '#7a3ae0', '#8a4af0', '#b89aff'),
        'orange': ('#6a2a00', '#b85000', '#f07a00', '#ff8a1a', '#ffc07a')}.items():
    for _i, _c in enumerate(_hexes):
        PALETTE['%s%d' % (_name, _i)] = _c
