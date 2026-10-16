"""Staging templates and density population: plan the dark and light masses before painting.

    import compose
    p = compose.proscenium(640, 360, seed=4)          # 01: V-opening, canopies, monoliths, unlit band
    c.fill(p['canopy'], 'sil0'); c.fill(p['fg'], 'sil0')
    for x, y in p.meta['emitters']: ...               # paired lamps, one deliberate extra
    st = compose.stage(216, W=384)                    # 09: lit slab in a black void
    r = compose.room(480, 270, seed=2)                # 10: a room blob (40-50%) touching one edge
    void, d = compose.frame_mask(638, 358, seed=1)    # 08: a drawn frame, d > 0 inside the void
    b = compose.bands_plan(224, W=304)                # 05: HUD, void, one action band, ground
    sp = compose.spine_plan(480, 270)                 # 03: a light spine with dark flanks
    lanes = compose.strips([('road', 30), ('curb', 2), ('paving', 18)], start=-40)
    objs = compose.populate(s, lanes=[(10, -60, 200, 1)], walks=[(-40, 40, 160, 60)], seed=3, t=t, T=96)
    compose.vignette(s, 40, 52, 4, seed=7)            # 07: a chatting group facing its centre
    fails = compose.check_density(objs, (0, 0, 600, 600), road=road_mask)

Every template returns a Plan: a dict of named H x W bool masks, plus .meta (rows, points and the
budget rules the style presets check with check.budget, see plan section B6). Templates are pure
functions of their arguments and seed; edges are lumpy by an integer-hash value noise, never by
a random generator with state.

Learned from: 01 Sword & Sworcery (near-symmetric proscenium, 94% of the light in the middle
62%, an unlit hedge band on the bottom 22%), 09 Katana ZERO (a 2.9:1 lit slab between void bands
of 22% and 16%, floor at 70%), 10 Stardew Valley (a hand-shaped room blob over 46% that runs off
one edge, a wall face 48-56 px tall, 52% black), 08 Owlboy (a maroon void frame with insets
52/49/16/26 px and a lumpy inner edge), 05 Metal Slug 3 (void on top, one action band), 03 Hyper
Light Drifter (a light spine, dark flanks), 07 Freitas (full-bleed strips, bumper-to-bumper lanes
2-6 units apart, Poisson clusters of 1 + Poisson(1.6) people, no window more than 85% road).
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph

__all__ = ['Plan', 'proscenium', 'stage', 'room', 'frame_mask', 'bands_plan', 'spine_plan',
           'strips', 'paint_strips', 'populate', 'vignette', 'check_density', 'mirror_points']

# ---------------------------------------------------------------- hashing and noise
def _hash(a, b, s=0):
    h = (np.asarray(a).astype(np.int64) * 374761393 + np.asarray(b).astype(np.int64) * 668265263
         + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _h1(a, b=0, s=0):
    return float(_hash(int(a), int(b), s))

def _vn(x, cell, seed):
    """1D smoothstep value noise in [-1, 1]"""
    u = np.asarray(x, float) / cell
    i = np.floor(u).astype(np.int64)
    f = u - i
    f = f * f * (3 - 2 * f)
    a, b = _hash(i, 0, seed) * 2 - 1, _hash(i + 1, 0, seed) * 2 - 1
    return a + (b - a) * f

def _edge(n, amp, wavelength, seed):
    """the 08 frame edge: amp * (0.6 vn(s / wavelength) + 0.4 vn(s / 10))"""
    s = np.arange(n)
    return amp * (0.6 * _vn(s, wavelength, seed) + 0.4 * _vn(s, 10, seed + 1))

def _poly(H, W, pts):
    """bool mask of pixel centres inside a polygon"""
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    inside = np.zeros((H, W), bool)
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        if ya == yb:
            continue
        inside ^= ((ya > yy) != (yb > yy)) & (xx < (xb - xa) * (yy - ya) / (yb - ya) + xa)
    return inside

class Plan(dict):
    """named bool masks plus .meta (rows, points, budget rules)"""
    def __init__(self, masks, **meta):
        super().__init__(masks)
        self.meta = meta

    def union(self, *names):
        out = None
        for n in names:
            out = self[n].copy() if out is None else out | self[n]
        return out

    def shares(self):
        """{name: fraction of the frame}"""
        return {k: float(v.mean()) for k, v in self.items()}

def mirror_points(points, axis, jitter=(12, 8), seed=0):
    """each (x, y) plus its mirror about x = axis, both nudged by up to +-jitter (01: paired
    emitters at mirrored coordinates, never exactly)"""
    out = []
    for i, (x, y) in enumerate(points):
        for k, xx in enumerate((x, 2 * axis - x)):
            dx = (_h1(i, k, seed) * 2 - 1) * jitter[0]
            dy = (_h1(i, k + 7, seed) * 2 - 1) * jitter[1]
            out.append((int(round(xx + dx)), int(round(y + dy))))
    return out

# ---------------------------------------------------------------- H1 templates
def proscenium(W=640, H=360, axis=None, top_open=None, stage_open=None, stage_y=None, fg_y=None,
               seed=0, monoliths=True, stairs=True):
    """01's near-symmetric stage. Defaults scale the measured 640 x 360 frame: axis at 49% of W,
    a V of sky 260 px wide at the top narrowing to 60 at the stage, the stage floor in rows
    230-280, the unlit foreground band from row 280 (the bottom 22%).
    Masks: canopy_l, canopy_r, canopy (lumpy V edges with 1 px notches; the right side has its
    own seed and +-4 px jitter), sky (the opening), monolith_l, monolith_r (framing stones at
    axis -+ 209..232 px from y 115 with notched tops), stage (the floor band), fg (the hedge band:
    a smooth noisy top with bush bumps r 6-14 and stairs cut at the axis), dark (everything that
    stays unlit). meta: axis, rows, emitters (two mirrored pairs plus one extra on one side, the
    deliberate break), focus, budget."""
    sx, sy = W / 640.0, H / 360.0
    axis = 0.494 * W if axis is None else axis
    top_open = 260 * sx if top_open is None else top_open
    stage_open = 60 * sx if stage_open is None else stage_open
    stage_y = (230 * sy, 280 * sy) if stage_y is None else stage_y
    fg_y = 280 * sy if fg_y is None else fg_y
    yy, xx = np.mgrid[0:H, 0:W]
    y = np.arange(H)
    s0 = stage_y[0]
    f = np.clip(y / max(1.0, s0), 0, 1)
    def side(sgn, sd, jit):
        x_edge = axis + sgn * (top_open / 2 + (stage_open / 2 - top_open / 2) * f)
        lump = np.round(3 * np.sin(y / 7.0 + _h1(sd, 1) * 6.28) + 2 * _vn(y, 9, sd) + jit)
        notch = (_hash(y, 3, sd) < 0.12) * sgn          # 1 px notches into the canopy
        e = x_edge + sgn * lump + notch
        m = (xx * sgn > e[:, None] * sgn) & (yy < s0)
        yc, k = 0.0, 0                                  # crown lobes bulging into the opening
        while yc < s0:
            r = (8 + _h1(k, 5, sd) * 14) * sx
            yi = int(min(H - 1, max(0, yc)))
            cx = x_edge[yi] + sgn * r * (0.45 + 0.3 * _h1(k, 6, sd))   # centred behind the edge: bulges of 0.25-0.55 r
            m |= ((xx - cx) ** 2 + (yy - yc) ** 2 <= r * r) & (yy < s0 - 6 * sy)
            yc += r * (0.9 + 0.7 * _h1(k, 7, sd))
            k += 1
        return m
    cl = side(-1, seed, 0)
    cr = side(1, seed + 101, (_h1(seed, 9) * 2 - 1) * 4)
    sky = (yy < s0) & ~cl & ~cr
    masks = {'canopy_l': cl, 'canopy_r': cr, 'canopy': cl | cr, 'sky': sky}
    stage_m = (yy >= stage_y[0]) & (yy < stage_y[1])
    masks['stage'] = stage_m
    bump = np.zeros(W)
    k, x = 0, 0.0
    while x < W:                                        # bush bumps along the hedge top
        r = (6 + _h1(k, 2, seed) * 8) * sx
        cx = x + r
        xs = np.arange(W)
        prof = np.sqrt(np.clip(r * r - (xs - cx) ** 2, 0, None)) * 0.55
        bump = np.maximum(bump, prof)
        x += r * (1.2 + _h1(k, 3, seed) * 0.8)
        k += 1
    top = fg_y + 4 * _vn(np.arange(W) / 20.0, 1, seed + 5) - bump
    fg = yy >= top[None, :]
    if stairs:
        half = 22 * sx
        cut = (np.abs(xx - axis) < half) & (yy < fg_y + 0.5 * (H - fg_y))
        fg &= ~cut
    masks['fg'] = fg
    if monoliths:
        for nm, sgn in (('monolith_l', -1), ('monolith_r', 1)):
            a, b = axis + sgn * 209 * sx, axis + sgn * 232 * sx
            x0, x1 = min(a, b), max(a, b)
            top_y = 115 * sy + (_h1(sgn, 4, seed) * 2 - 1) * 6 * sy
            m = (xx >= x0) & (xx < x1) & (yy >= top_y) & (yy < stage_y[1])
            nx = (_hash(xx, 5, seed + sgn) < 0.3) & (yy < top_y + 2)
            masks[nm] = m & ~nx
    masks['dark'] = masks['canopy'] | masks['fg'] | masks.get('monolith_l', False) | masks.get('monolith_r', False)
    em = mirror_points([(218 * sx, 45 * sy), (173 * sx, 123 * sy)], axis, (12 * sx, 8 * sy), seed)
    extra = (int(axis + (1 if _h1(seed, 11) < 0.5 else -1) * 135 * sx), int(113 * sy))
    return Plan(masks, axis=axis, rows=dict(stage=stage_y, fg=fg_y), emitters=em + [extra],
                focus=(int(axis), int(stage_y[0])),
                budget={'light_x': (0.19, 0.81, 0.94), 'band_energy': (fg_y / H, 0.01),
                        'L<0.25': (0.55, None), 'L>0.75': (None, 0.003)})

def stage(H, top=0.22, bottom=0.16, floor=0.70, W=None, fade=None, teeth=1.0, seed=0, shaft=None):
    """09's lit slab in a black void. The solid room runs over rows [top H, H - bottom H) (62% of
    the height at the defaults, 09 rows 53-198 of 240), the feet stand on row floor H, actors are
    about 0.175 H tall. Toward each void the room fades to black over a band outside that span:
    fade = (rows above, rows below), default (0.1 H, 0.05 H) (09: 21 and 11 rows), so exact
    black is the outer 12% and 11% (09: 25.7% of the frame). The black boundary is
    column-jittered by about `teeth` rows (09's teeth).
    Returns a Plan; with W it carries masks void_top, void_bottom, void (exact black), room
    (everything drawn, fades included), solid (the unfaded room), floor (rows from floor_y down),
    fade_top / fade_bottom (the fade bands, ramp them to black away from the room) and shaft (one
    vertical element (x, width) that keeps going up into the void at a frame edge).
    meta: void_top, floor_y, void_bottom (the solid room's rows), black_top, black_bottom (mean
    rows where exact black starts), actor_h, budget."""
    vt, vb, fy = int(round(top * H)), int(round(H - bottom * H)), int(round(floor * H))
    if fade is None:
        fade = (0.1 * H, 0.05 * H)
    elif np.ndim(fade) == 0:
        fade = (fade, fade)
    ft, fb = min(vt, int(round(fade[0]))), min(H - vb, int(round(fade[1])))
    meta = dict(void_top=vt, floor_y=fy, void_bottom=vb, black_top=vt - ft, black_bottom=vb + fb,
                actor_h=int(round(0.175 * H)), budget={'black': (0.2, 0.32), 'room_aspect': (2.6, 3.2)})
    if W is None:
        return Plan({}, **meta)
    yy, xx = np.mgrid[0:H, 0:W]
    x = np.arange(W)
    jt = np.round(teeth * (2 * _hash(x // 2, 1, seed) - 1) * (_hash(x // 5, 2, seed) < 0.7)).astype(int)
    jb = np.round(teeth * (2 * _hash(x // 2, 3, seed) - 1) * (_hash(x // 5, 4, seed) < 0.7)).astype(int)
    edge_t, edge_b = np.clip(vt - ft + jt, 0, vt), np.clip(vb + fb + jb, vb, H)
    room = (yy >= edge_t[None, :]) & (yy < edge_b[None, :])
    masks = {'void_top': yy < edge_t[None, :], 'void_bottom': yy >= edge_b[None, :], 'room': room,
             'solid': (yy >= vt) & (yy < vb), 'floor': (yy >= fy) & (yy < vb),
             'fade_top': room & (yy < vt), 'fade_bottom': room & (yy >= vb)}
    masks['void'] = ~room
    if shaft:
        sx0, sw = shaft
        masks['shaft'] = (xx >= sx0) & (xx < sx0 + sw) & (yy < fy)
    return Plan(masks, **meta)

def room(W, H, pts=None, seed=0, area=(0.40, 0.50), touch='right', wall_h=52, crown=3, lip=2, lump=3):
    """10's room: a hand-shaped blob (40-50% of the frame) that runs off one frame edge, its edges
    on 0 / 1:1 / 2:1 / vertical slopes; the back wall is a face wall_h px tall above a wall-base
    line with 3-5 setbacks of 8-24 px. The generated outline's floor edges (the side away from
    `touch` and the bottom) are then pushed in and out by up to `lump` px of value noise, so the
    floor lip reads hand-cut rather than ruled (10). pts: your own polygon (used as given, no
    lumps; the wall-base is then its top edge). Masks: room, wall (the face), crown (its top
    `crown` rows: the checker-dithered void edge), floor, lip (the floor's `lip` rows along the
    void), void. meta: wall_base (one row per column, -1 outside), lights (three lamps 60-75 px
    apart, each lower than the last: 10's diagonal lamp rhythm; on the wall face, or hung just
    below its base where a setback steps the wall up), subject, budget."""
    yy, xx = np.mgrid[0:H, 0:W]
    gen = pts is None
    if gen:
        pts = _room_poly(W, H, seed, area, touch, wall_h)
    blob = _poly(H, W, pts)
    if gen and lump:
        blob = _lumpy(blob, lump, seed, touch)
    has = blob.any(0)
    top = np.where(has, blob.argmax(0), -1)
    base = np.where(has, top + wall_h, -1)
    wall = blob & (yy < base[None, :])
    floor = blob & ~wall
    cr = wall & (yy < top[None, :] + crown)
    void = ~blob
    near_void = morph.dilate(void, lip, border=None) & floor
    masks = {'room': blob, 'wall': wall, 'crown': cr, 'floor': floor, 'lip': near_void, 'void': void}
    # three lamps stepping down a diagonal on the wall face: 60-75 px apart (10: 72-73 px), each
    # step 6-34 px lower (10: 33 then 7), never equally spaced
    cols = np.nonzero(has)[0]
    lights = []
    if len(cols):
        lo, hi = cols[0], cols[-1]
        x = lo + 0.2 * (hi - lo) if touch != 'left' else hi - 0.2 * (hi - lo)
        sgn = 1 if touch != 'left' else -1
        def band(xf):                                   # wall-face rows at a column (floor below a high setback)
            xi = int(min(W - 1, max(0, round(xf))))
            if not has[xi]:
                return xi, H // 4, H // 4 + wall_h
            return xi, top[xi] + crown + 2, base[xi] - 3
        xi, lo_, hi_ = band(x)
        y = min(max(lo_ + 0.3 * (hi_ - lo_) + (_h1(9, 1, seed) * 2 - 1) * 4, lo_), hi_)
        lights.append((xi, int(round(y))))
        for k in range(2):
            D = 62 + _h1(k, 3, seed) * 10
            dy = 6 + _h1(k, 4, seed) * 28
            for _ in range(3):                          # settle the step on the column it lands on
                nx = x + sgn * (math.sqrt(max(1.0, D * D - dy * dy)) + (_h1(k, 1, seed) * 2 - 1) * 2)
                xi, lo_, hi_ = band(nx)
                if hi_ - y < 3:                         # the wall base steps up: hang it just below
                    hi_ = y + 12
                dy = min(max(dy, lo_ - y, 3), hi_ - y)
            x, y = nx, y + dy
            lights.append((xi, int(round(y))))
    return Plan(masks, wall_base=base, lights=lights, pts=pts,
                subject=(int(0.5 * W + (_h1(5, 1, seed) * 2 - 1) * 0.03 * W),
                         int(0.55 * H + (_h1(5, 2, seed) * 2 - 1) * 0.03 * H)),
                budget={'L<0.1': (0.40, 0.60), 'L>0.8': (None, 0.005), 'room_share': area})

def _lumpy(blob, amp, seed, touch):
    """push the bottom edge (per column) and the free side edge (per row) of a blob in and out by
    up to amp px of smooth value noise"""
    H, W = blob.shape
    out = blob.copy()
    rows = np.arange(H)
    has = out.any(0)
    bot = np.where(has, H - 1 - out[::-1].argmax(0), -1)
    d = np.round(amp * (0.65 * _vn(np.arange(W), 13, seed + 31) + 0.35 * _vn(np.arange(W), 5, seed + 32))).astype(int)
    for x in np.nonzero(has & (bot < H - 1))[0]:
        b, nb = bot[x], min(H - 1, bot[x] + d[x])
        if nb > b:
            out[b + 1:nb + 1, x] = True
        elif nb < b:
            out[nb + 1:b + 1, x] = False
    has_r = out.any(1)
    if touch == 'left':
        side = np.where(has_r, W - 1 - out[:, ::-1].argmax(1), -1)
        sgn = 1
    else:
        side = np.where(has_r, out.argmax(1), -1)
        sgn = -1
    top_rows = np.nonzero(has_r)[0]
    if len(top_rows):
        e = np.round(amp * (0.65 * _vn(rows, 13, seed + 33) + 0.35 * _vn(rows, 5, seed + 34))).astype(int)
        for y in top_rows[top_rows > top_rows[0] + 4]:   # leave the wall's top corner square
            s0, ns = side[y], int(np.clip(side[y] + sgn * e[y], 0, W - 1))
            if sgn < 0:
                if ns < s0:
                    out[y, ns:s0] = True
                else:
                    out[y, s0:ns] = False
            else:
                if ns > s0:
                    out[y, s0 + 1:ns + 1] = True
                else:
                    out[y, ns + 1:s0 + 1] = False
    return out

def _room_poly(W, H, seed, area, touch, wall_h):
    """a room outline: a wall-base top edge with setbacks, chamfered 1:1 / 2:1 corners, run off
    `touch`; grown or shrunk until its share of the frame lands inside `area`"""
    target = 0.5 * (area[0] + area[1])
    def build(scale):
        x0 = W * (1 - scale * 0.78)
        y0, y1 = H * 0.12, H * (0.12 + 0.86 * min(1.0, 0.55 + scale * 0.5))
        y1 = min(y1, H * 0.98)
        n = 3 + int(_h1(1, 1, seed) * 3)                # setbacks along the top
        xs = np.linspace(x0, W + 8, n + 1)
        top = []
        for i in range(n):
            yv = y0 + (_h1(i, 2, seed) * 2 - 1) * 12 + (8 + _h1(i, 3, seed) * 16) * (i % 2)
            top += [(xs[i], yv), (xs[i + 1], yv)]
        c = 6 + _h1(4, 4, seed) * 6                     # chamfers
        ym = y0 + (y1 - y0) * (0.45 + 0.2 * _h1(7, 7, seed))
        dn = 10 + _h1(8, 8, seed) * 12                  # a 1:1 notch in the left wall
        left = [(x0 + c, y1), (x0, y1 - c * 0.5), (x0, ym + dn), (x0 + dn, ym), (x0 + dn, top[0][1] + c)]
        p = [(x0 + dn + c * 0.5, top[0][1])] + top[1:] + [(W + 8, top[-1][1]), (W + 8, y1)]
        jog = x0 + (W - x0) * (0.35 + _h1(5, 5, seed) * 0.3)
        jd = 8 + _h1(9, 9, seed) * 10
        p += [(jog + 2 * jd, y1), (jog + jd, y1 + jd * 0.5), (jog - 30, y1 + jd * 0.5), (jog - 30 - jd, y1)]
        p += left
        return p
    lo, hi = 0.3, 1.2
    pts = build(0.7)
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        pts = build(mid)
        a = _poly(H, W, pts).mean()
        if a < target:
            lo = mid
        else:
            hi = mid
    if touch == 'left':
        pts = [(W - x, y) for x, y in pts]
    return [(float(x), float(y)) for x, y in pts]

def frame_mask(W, H, inset=(52, 49, 16, 26), amp=8, wavelength=28, seed=0):
    """08's frame drawn into the art: the playfield is the rectangle inset (left, right, top,
    bottom) px from the edges with each edge displaced by amp * (0.6 vn(s / wavelength) +
    0.4 vn(s / 10)). Returns (void, signed_dist): void is the frame (flat maroon in 08, 15% of
    the frame), signed_dist > 0 inside the void and < 0 in the playfield (feed it to a leaf mass
    that hugs the inner edge: p(d) = 0.9 exp(-((d + 2) / 8)^2))."""
    l, r, t, b = inset
    ys, xs = np.arange(H), np.arange(W)
    el = l + _edge(H, amp, wavelength, seed)
    er = W - r - _edge(H, amp, wavelength, seed + 1)
    et = t + _edge(W, amp, wavelength, seed + 2)
    eb = H - b - _edge(W, amp, wavelength, seed + 3)
    field = ((xs[None, :] >= el[:, None]) & (xs[None, :] < er[:, None]) &
             (ys[:, None] >= et[None, :]) & (ys[:, None] < eb[None, :]))
    void = ~field
    return void, -morph.signed(void, 'euclid', border=True)

def bands_plan(H, hud=(0.0, 0.07), void=(0.07, 0.28), action=(0.28, 0.82), ground=(0.82, 1.0), W=None):
    """05's value bands: a HUD strip, a black void, one action band where every warm bright
    lives, the ground. Each band is (start, end) as fractions of H (or rows when > 1).
    Returns a Plan with masks hud, void, action, ground (with W) and meta rows + budget."""
    def rows(b):
        return tuple(int(round(v * H)) if v <= 1 else int(v) for v in b)
    R = dict(hud=rows(hud), void=rows(void), action=rows(action), ground=rows(ground))
    masks = {}
    if W is not None:
        y = np.arange(H)[:, None]
        for k, (a, b) in R.items():
            masks[k] = np.broadcast_to((y >= a) & (y < b), (H, W)).copy()
    return Plan(masks, rows=R, budget={'L<0.25': (0.45, None), 'warm_brights_in': 'action'})

def spine_plan(W, H, cx=None, sigma=None, flank=0.5):
    """03's value composition: a vertical light spine (Gaussian across x, sigma about 0.13 W,
    almost no fall-off down y) with dark flanks. Masks spine (|x - cx| < sigma), flank_l,
    flank_r (beyond flank * W / 2 from the spine centre on each side), mid (between). meta:
    weight (H x W in [0, 1], multiply a light pass or pick ramp steps by it) and the measured
    targets: spine L 0.6-0.7, flanks 0.23-0.31."""
    cx = W / 2.0 if cx is None else cx
    sigma = 0.13 * W if sigma is None else sigma
    x = np.arange(W) + 0.5
    w = np.exp(-((x - cx) ** 2) / (2 * sigma * sigma))
    weight = np.broadcast_to(w[None, :], (H, W)).copy()
    d = np.abs(x - cx)
    sp = np.broadcast_to((d < sigma)[None, :], (H, W)).copy()
    fl = np.broadcast_to(((x < cx) & (d > flank * W / 2))[None, :], (H, W)).copy()
    fr = np.broadcast_to(((x >= cx) & (d > flank * W / 2))[None, :], (H, W)).copy()
    return Plan({'spine': sp, 'flank_l': fl, 'flank_r': fr, 'mid': ~(sp | fl | fr)}, weight=weight,
                budget={'spine_L': (0.6, 0.7), 'flank_L': (0.23, 0.31)})

# ---------------------------------------------------------------- H2 strips and population
def strips(spec, start=0):
    """07's full-bleed layout: bands across the world's y axis, in world units. spec: [(name,
    width), ...] in order. Returns a list of (name, y0, y1); the same name may repeat (two roads)."""
    out, y = [], float(start)
    for name, w in spec:
        out.append((name, y, y + w))
        y += w
    return out

def paint_strips(s, bands, x0, x1, mats, z=0):
    """lay strips into an Iso scene as flat boxes from x0 to x1: mats {name: (mat, top)} where top
    is a slot or face function (or just a slot). Bands without a mat are skipped."""
    for name, y0, y1 in bands:
        if name not in mats:
            continue
        m = mats[name]
        mat, top = (m if isinstance(m, tuple) else (name, m))
        s.box(x0, y0, z, x1 - x0, y1 - y0, 0, mat, top=top, lines=False, cast=False)

KINDS = (('sedan', 0.58), ('pickup', 0.21), ('convertible', 0.13), ('bus', 0.08))
LENGTH = {'sedan': 40, 'pickup': 40, 'convertible': 40, 'bus': 84}

def _choose(table, u):
    tot = sum(w for _, w in table)
    acc = 0.0
    for k, w in table:
        acc += w / tot
        if u < acc:
            return k
    return table[-1][0]

def _poisson(lam, u):
    """inverse-CDF Poisson sample from one uniform"""
    k, p = 0, math.exp(-lam)
    c = p
    while u > c and k < 12:
        k += 1
        p *= lam / k
        c += p
    return k

def populate(s, lanes=(), walks=(), density=None, seed=0, t=0, T=None, schedule=None, paints=None,
             people=True, cars=True, walkers=0.25):
    """fill an Iso scene with 07 traffic and crowds.
    lanes: [(y, x0, x1, dir), ...] in world units: a lane of cars along x at y (its near side), a
    torus from x0 to x1 (make it longer than the frame: the world 25% larger on every side).
    Vehicles follow one another 2-6 units apart (a wider gap now and then), kinds weighted
    sedan .58 pickup .21 convertible .13 bus .08 (07's bikes are not built), paints by hash so neighbours differ. With T,
    lane k moves by anim-style whole-unit offsets: schedule [(frames, units per frame), ...]
    covering T (default one lap per loop); dir -1 drives toward -x.
    walks: [(x0, y0, x1, y1), ...] paving and plaza rects: groups of 1 + Poisson(1.6) people
    (density['person'] per 1000 screen px^2, default 0.11; 1 unit^2 = 4 px^2), centres at
    least 20 units apart, members on a circle of 4-7 units facing the centre. A share `walkers`
    of the singles pace back and forth at 1 unit per 2 frames instead, looping exactly over T.
    Returns a list of dicts (kind, x, y, oid, box (screen x0, y0, x1, y1))."""
    import props, figures as fg
    density = dict({'car': None, 'person': 0.11}, **(density or {}))
    paints = paints or props.PAINTS
    objs = []
    tyre = props.tyre().grid()
    for li, lane in enumerate(lanes if cars else ()):
        y, x0, x1, d = lane[:4]
        Lw = x1 - x0
        x, k, prev = 0.0, 0, None
        fleet = []
        while True:
            kind = _choose(KINDS, _h1(li, k, seed))
            L = LENGTH[kind]
            if x + L > Lw:
                break
            p = int(_h1(li, k + 50, seed) * len(paints))
            if paints[p] == prev:
                p = (p + 1) % len(paints)
            prev = paints[p]
            fleet.append((x, kind, paints[p], k))
            gap = 2 + _h1(li, k + 90, seed) * 4
            if _h1(li, k + 130, seed) < 0.15:
                gap += L * 0.6
            x += L + gap
            k += 1
        off = 0
        if T:
            sch = schedule or [(T, Lw / float(T))]
            dist, used = 0.0, 0
            tm = int(t) % T
            for f_, v in sch:
                n = min(f_, tm - used)
                if n <= 0:
                    break
                dist += n * v
                used += f_
            off = int(math.floor(dist + 1e-9))
        for (xa, kind, paint, k) in fleet:
            L = LENGTH[kind]
            pos = (xa + d * off) % Lw
            wx = x0 + pos
            depth = 24 if kind == 'bus' else 17
            ids = props.car(s, wx, y - depth, kind=kind, paint=paint, heading='x' if d > 0 else '-x',
                            seed=seed * 131 + li * 17 + k, tyre_grid=tyre)
            objs.append(dict(kind=kind, x=wx, y=y - depth, oid=ids, box=_box_of(s, wx, y - depth, L, depth, 50 if kind == 'bus' else 28)))
    if people:
        for wi, (ax0, ay0, ax1, ay1) in enumerate(walks):
            area = (ax1 - ax0) * (ay1 - ay0)
            n_people = density['person'] * area * 4 / 1000.0   # 1 unit^2 is 4 px^2 in 2:1 iso
            centres = []
            k = 0
            placed = 0
            while placed < n_people and k < 400:
                cx = ax0 + 4 + _h1(wi, 3 * k, seed + 7) * max(1, ax1 - ax0 - 8)
                cy = ay0 + 4 + _h1(wi, 3 * k + 1, seed + 7) * max(1, ay1 - ay0 - 8)
                k += 1
                if any((cx - a) ** 2 + (cy - b) ** 2 < 400 for a, b in centres):
                    continue
                centres.append((cx, cy))
                size = 1 + _poisson(1.6, _h1(wi, 3 * k + 2, seed + 7))
                if size == 1 and _h1(wi, k, seed + 9) < walkers and T:
                    objs.append(_walker(s, fg, (ax0, ay0, ax1, ay1), cy, seed * 977 + wi * 31 + k, t, T))
                    placed += 1
                    continue
                objs += vignette(s, cx, cy, size, seed=seed * 977 + wi * 31 + k, t=t)
                placed += size
    return objs

def _box_of(s, x, y, L, D, Hpx):
    pts = [s.to_screen(x + a, y + b, c) for a in (0, L) for b in (0, D) for c in (0, Hpx)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1)

def _walker(s, fg, rect, y, seed, t, T):
    """a pedestrian pacing along x at walking speed (07: 1 unit per 2 frames): out T // 4 units
    and back again, a closed path of T / 2 units, so frame T == frame 0 for any T divisible by 4
    (otherwise the turn lands within a frame of the start)"""
    ax0, ay0, ax1, ay1 = rect
    half = max(1, T // 4)
    span = max(1, (ax1 - ax0) - half)
    start = ax0 + int(_h1(seed, 2) * span)
    p = (int(t) + int(_h1(seed, 4) * T)) % T
    if p < 2 * half:
        pos, d = start + p // 2, 1
    else:
        pos, d = start + half - (p - 2 * half) // 2, -1
    pos = min(pos, start + half)
    f = fg.at(fg.iso_person, t, 'walk', phase=int(_h1(seed, 3) * 8), seed=seed, facing='se' if d > 0 else 'sw')
    oid = s.sprite(f.grid(), pos, y, 0, anchor=(f.ax, f.ay))
    sx, sy = s.to_screen(pos, y, 0)
    return dict(kind='person', x=pos, y=y, oid=oid, box=(int(sx) - f.ax, int(sy) - f.ay, int(sx) - f.ax + f.w, int(sy) - f.ay + f.h))

def vignette(s, cx, cy, n, seed=0, t=0, radius=(4, 7), poses=('stand', 'idle', 'wave')):
    """07's social vignette: n people on a circle of radius 4-7 units round (cx, cy), each facing
    the centre ('se' when the centre is to its right on screen, else 'sw'), with an idle bob or a
    wave on a hold table at a per-person phase. n = 1 is a lone figure at the centre.
    Returns a list of dicts like populate()."""
    import figures as fg
    out = []
    a0 = _h1(seed, 1) * 2 * math.pi
    for i in range(n):
        if n == 1:
            x, y = cx, cy
        else:
            r = radius[0] + _h1(seed, 10 + i) * (radius[1] - radius[0])
            a = a0 + 2 * math.pi * i / n + (_h1(seed, 20 + i) - 0.5) * 0.6
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        sx, _ = s.to_screen(x, y, 0)
        ccx, _ = s.to_screen(cx, cy, 0)
        facing = 'se' if (ccx - sx) >= 0 else 'sw'
        if n == 1:
            facing = 'se' if _h1(seed, 3) < 0.5 else 'sw'
        pose = poses[int(_h1(seed, 30 + i) * len(poses)) % len(poses)]
        ps = seed * 13 + i
        if pose == 'stand':
            f = fg.iso_person(seed=ps, facing=facing)
        else:
            f = fg.at(fg.iso_person, t, pose, phase=int(_h1(seed, 40 + i) * 24), seed=ps, facing=facing)
        oid = s.sprite(f.grid(), x, y, 0, anchor=(f.ax, f.ay))
        sx, sy = s.to_screen(x, y, 0)
        out.append(dict(kind='person', x=x, y=y, oid=oid,
                        box=(int(sx) - f.ax, int(sy) - f.ay, int(sx) - f.ax + f.w, int(sy) - f.ay + f.h)))
    return out

def check_density(objs, frame, road=None, window=120, max_road=0.85, min_edge=2, stride=20):
    """07's rejection rules -> a list of failure strings (empty = keep the layout):
    every frame edge must cut at least `min_edge` objects; no window x window box may be more
    than max_road road (road: an H x W bool mask in frame coordinates)."""
    fx0, fy0, fx1, fy1 = frame
    fails = []
    for name, test in (('left', lambda b: b[0] < fx0 < b[2]), ('right', lambda b: b[0] < fx1 < b[2]),
                       ('top', lambda b: b[1] < fy0 < b[3]), ('bottom', lambda b: b[1] < fy1 < b[3])):
        n = sum(1 for o in objs if test(o['box']))
        if n < min_edge:
            fails.append('%s edge cuts %d objects (< %d)' % (name, n, min_edge))
    if road is not None:
        r = np.asarray(road, float)
        H, W = r.shape
        ii = np.pad(r.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        worst = 0.0
        for y in range(0, max(1, H - window + 1), stride):
            for x in range(0, max(1, W - window + 1), stride):
                y1, x1 = min(H, y + window), min(W, x + window)
                v = (ii[y1, x1] - ii[y, x1] - ii[y1, x] + ii[y, x]) / float((y1 - y) * (x1 - x))
                worst = max(worst, v)
        if worst > max_road:
            fails.append('a %d px window is %.0f%% road (> %.0f%%)' % (window, 100 * worst, 100 * max_road))
    return fails
