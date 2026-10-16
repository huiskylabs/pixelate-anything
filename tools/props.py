"""Prop kits: vehicles, tyres, poles, trunks, rails, ladders, lanterns, girders and stairwells.

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

Learned from: 07 Freitas (cars built from boxes with streaked glass and upright 10 x 17 tyre
ovals, column-banded poles and trunks), 10 Stardew Valley (3-row rails 8 px apart with ties every
8 px and filleted corners, the ladder, the 6 x 9 wall lantern), 06 Into the Breach (near-black
girders a step above the dark, lattice towers), 03 Hyper Light Drifter (treads stepping into a
black void, brighter each step toward the viewer).

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
           'stairwell', 'glass_streak', 'PALETTE', 'PAINTS']

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
