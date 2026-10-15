"""Dragonfire Keep: an original dungeon boss fight in 16-bit style, side view, 320x180 (16:9).

A knight braces behind a shield on a stone ledge; across a river of lava, on a hoard of gold,
Ashmaw the ember wyrm rears, draws breath and pours fire. Torches flicker, embers rise, banners
sway; the fire lights the hall in palette steps (no blending), the screen shakes on the blast.

Made with the kit's tools: the dragon and the knight are curved solids (tools/sdf.py: limbs as
RoundCones, wings and the cape as Plates, smooth unions) rendered by the 'side' camera with
outlines; the hall is drawn in palette slots; light is a ramp shift per pixel from torches, lava
and fire with an ordered dither at the edges. 120 frames at 15 fps, a seamless loop.
"""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
import colorlib as cl
import iso
from iso import Iso, hash2, BAYER4
from sdf import RBox, Sphere, RoundCone, Plate, Union, Smooth, Sub, Inter, Above
from palette import ramp
import pixfont

iso.RAMP_STEPS = 7
W, H = 320, 180
FRAMES, FPS = 120, 15
OY = 172                                       # screen row of world z = 0 (side camera: sy = OY - z)

# ---------------------------------------------------------------- palette (7-step ramps)
RAMPS = {'stone': '#5b5470', 'wood': '#7a4a2a', 'steel': '#8e9bb0', 'cape': '#2f58b8', 'plume': '#d23a3a',
         'drag': '#a8262a', 'belly': '#d89a5a', 'wing': '#7a2436', 'horn': '#d8ccb0', 'gold': '#e0a62a',
         'bone': '#cfc6ad', 'banner': '#6a2a7a', 'chain': '#4a4658', 'rock': '#4a3a3e', 'shield': '#b0303a',
         'ruby': '#c81e4e', 'sapph': '#2f66d8'}
PAL = {'ol': '#0e0a12', 'void': '#140c16', 'void2': '#22101a'}
for name, base in RAMPS.items():
    for i, h in enumerate(ramp(base, 7, 30)):
        PAL['%s%d' % (name, i)] = h
for i, h in enumerate(['#2a0e10', '#5a1a14', '#a8281a', '#e8541c', '#ff9a2a', '#ffd84a', '#fff8d0']):
    PAL['fire%d' % i] = h
for i, h in enumerate(['#5a1a14', '#a8281a', '#e8541c', '#ff8a1a', '#ffc040']):
    PAL['lava%d' % i] = h
for i, h in enumerate(['#2a2230', '#3e3448', '#5a4e64']):
    PAL['smoke%d' % i] = h
PAL.update({'eye': '#ffe060', 'pupil': '#2a0e10', 'glint': '#fffbe0'})
PAL.update({'smoke0': '#3a3240', 'smoke1': '#5e5466', 'smoke2': '#8a7f8e'})
EMISSIVE = ('fire', 'lava', 'eye', 'glint', 'smoke', 'pupil', 'ol', 'void')

# ---------------------------------------------------------------- timeline
def phase(t):
    """idle 0-29, inhale 30-47, breath 48-89, settle 90-119; returns (name, 0..1 progress)"""
    for name, a, b in (('idle', 0, 30), ('inhale', 30, 48), ('breath', 48, 90), ('settle', 90, 120)):
        if a <= t < b:
            return name, (t - a) / (b - a)
    return 'idle', 0.0

def ease(x):
    return x * x * (3 - 2 * x)

def pose(t):
    """neck control points, head direction, jaw opening, wing angle, body bob"""
    name, p = phase(t)
    idle = dict(neck=[(212, 86), (198, 104), (188, 118), (178, 117)], f=(-1.0, -0.12), jaw=0.06, wing=0.0)
    up = dict(neck=[(214, 88), (206, 112), (198, 130), (190, 131)], f=(-0.92, 0.38), jaw=0.18, wing=0.22)
    fire = dict(neck=[(212, 84), (194, 100), (178, 104), (166, 99)], f=(-0.93, -0.36), jaw=0.62, wing=-0.12)
    def mix(a, b, k):
        return dict(neck=[(ax + (bx - ax) * k, az + (bz - az) * k) for (ax, az), (bx, bz) in zip(a['neck'], b['neck'])],
                    f=(a['f'][0] + (b['f'][0] - a['f'][0]) * k, a['f'][1] + (b['f'][1] - a['f'][1]) * k),
                    jaw=a['jaw'] + (b['jaw'] - a['jaw']) * k, wing=a['wing'] + (b['wing'] - a['wing']) * k)
    if name == 'idle':
        s = mix(idle, idle, 0)
    elif name == 'inhale':
        s = mix(idle, up, ease(p))
    elif name == 'breath':
        s = mix(up, fire, ease(min(1, p * 4)))
    else:
        s = mix(fire, idle, ease(p))
    s['bob'] = math.sin(t / FRAMES * 2 * math.pi * 3) * 1.2       # three breaths per loop
    fx, fz = s['f']; n = math.hypot(fx, fz); s['f'] = (fx / n, fz / n)
    return s

# ---------------------------------------------------------------- the dragon (curved solids)
def bezier(P, k):
    (x0, z0), (x1, z1), (x2, z2), (x3, z3) = P
    u = 1 - k
    return (u ** 3 * x0 + 3 * u * u * k * x1 + 3 * u * k * k * x2 + k ** 3 * x3,
            u ** 3 * z0 + 3 * u * u * k * z1 + 3 * u * k * k * z2 + k ** 3 * z3)

def dragon_mat(base):
    def m(p, n, step, t):
        x, y, z = p
        if base == 'torso':
            if n[2] < -0.38 or (x < 234 and 56 < z < 88 and n[0] < -0.5 and abs(n[2]) < 0.55):
                return 'belly%d' % min(6, step + (0 if int(z) % 3 else -1) + 1)      # belly plates: underside, chest
        if base in ('torso', 'drag'):
            if step >= 3:                                            # scales: a sparse staggered stipple where
                row = int(math.floor(z / 3))                         # the light catches them
                if z - row * 3 < 1 and int(x + (2 if row % 2 else 0)) % 4 == 0:
                    return 'drag%d' % (step - 1)
            return 'drag%d' % step
        return '%s%d' % (base, step)
    return m

def seg_dist(x, z, a, b):
    ax, az = a; bx, bz = b
    dx, dz = bx - ax, bz - az
    k = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz + 1e-9)))
    return math.hypot(x - ax - k * dx, z - az - k * dz)

def membrane_mat(bones):
    """the wing membrane: taut and light along the finger bones, sagging darker between them"""
    def m(p, n, step, t):
        d = min(seg_dist(p[0], p[2], a, b) for a, b in bones)
        return 'wing4' if d < 2.2 else ('wing3' if d < 6.5 else 'wing2')
    return m

def wing_points(sx, sz, ang, spread=1.0):
    """a bat wing: arm to the wrist, fingers to their tips, the membrane scalloped between them"""
    def rot(px, pz):
        dx, dz = px - sx, pz - sz
        c, s_ = math.cos(ang), math.sin(ang)
        return (sx + dx * c - dz * s_, sz + dx * s_ + dz * c)
    elbow = rot(sx + 14, sz + 34 * spread)
    wrist = rot(sx + 4, sz + 58 * spread)
    tips = [rot(sx - 22, sz + 64 * spread), rot(sx + 16, sz + 76 * spread), rot(sx + 50, sz + 64 * spread), rot(sx + 70, sz + 34 * spread)]
    attach = (sx + 40, sz - 8)
    poly = [(sx, sz), elbow, wrist, tips[0]]
    chain = tips + [attach]
    for a, b in zip(chain[:-1], chain[1:]):
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        cx_, cz_ = (wrist[0] + mx) / 2, (wrist[1] + mz) / 2       # sag toward the wrist between fingers
        for k in (0.25, 0.5, 0.75):
            sagk = math.sin(k * math.pi) * 0.38
            px = a[0] + (b[0] - a[0]) * k; pz = a[1] + (b[1] - a[1]) * k
            poly.append((px + (cx_ - px) * sagk, pz + (cz_ - pz) * sagk))
        poly.append(b)
    return poly, elbow, wrist, tips

def dragon(s, t):
    P = pose(t)
    bob = P['bob']
    fx, fz = P['f']; ux, uz = fz, -fx                               # forward and up for the head
    neck = [(x, z + bob * (1 - i / 3)) for i, (x, z) in enumerate(P['neck'])]
    E = neck[-1]
    def at(a, b):                                                    # head-local -> world
        return (E[0] + a * fx + b * ux, E[1] + a * fz + b * uz)
    wing_ang = P['wing']
    # far wing, far legs first (behind)
    poly, elbow, wrist, tips = wing_points(240, 94 + bob, wing_ang + 0.08, 0.95)
    far_wing = [Plate([(x + 8, z + 3) for x, z in poly], y0=-14, t=0.7, mat='wing1')]
    far_wing += [RoundCone((240 + 8, -13, 97 + bob), (elbow[0] + 8, -13, elbow[1] + 3), 3, 2.2, mat='wing2'),
                 RoundCone((elbow[0] + 8, -13, elbow[1] + 3), (wrist[0] + 8, -13, wrist[1] + 3), 2.2, 1.8, mat='wing2')]
    for tip in tips:
        far_wing.append(RoundCone((wrist[0] + 8, -13, wrist[1] + 3), (tip[0] + 8, -13, tip[1] + 3), 1.5, 0.5, mat='wing3'))
    s.solid(Union(*far_wing))
    legs_far = Union(
        RoundCone((228, -9, 70 + bob), (222, -9, 56), 7, 5, mat=dragon_mat('drag')), RoundCone((222, -9, 56), (218, -9, 47), 5, 4, mat=dragon_mat('drag')),
        RoundCone((218, -9, 47), (209, -9, 45), 4, 2.4, mat=dragon_mat('drag')),
        Sphere(262, -9, 60 + bob, 10, mat=dragon_mat('drag')), RoundCone((266, -9, 56), (259, -9, 47), 6, 4.4, mat=dragon_mat('drag')),
        RoundCone((259, -9, 47), (249, -9, 45), 4.4, 2.8, mat=dragon_mat('drag')))
    s.solid(legs_far)
    # the body: torso, neck, head, tail, smooth-unioned
    parts = [Sphere(226, 0, 74 + bob, 20, mat=dragon_mat('torso')), Sphere(252, 0, 71 + bob, 19, mat=dragon_mat('torso'))]
    N = 7
    pts = [bezier(neck, k / N) for k in range(N + 1)]
    for i in range(N):
        r0 = 11.5 - 4.6 * i / N; r1 = 11.5 - 4.6 * (i + 1) / N
        parts.append(RoundCone((pts[i][0], 0, pts[i][1]), (pts[i + 1][0], 0, pts[i + 1][1]), r0, r1, mat=dragon_mat('torso')))
    tail = [(268, 68), (288, 62), (302, 54), (314, 48), (326, 46), (338, 50)]
    tail = [(x, z + bob * 0.5) for x, z in tail]
    for i in range(len(tail) - 1):
        r0 = 12 - 2 * i; r1 = 12 - 2 * (i + 1)
        parts.append(RoundCone((tail[i][0], 0, tail[i][1]), (tail[i + 1][0], 0, tail[i + 1][1]), max(1.6, r0), max(1.2, r1), mat=dragon_mat('torso')))
    # the head: a cranium, a long wedge of a snout, the jaw on its hinge
    sk = at(0, 1); parts.append(Sphere(sk[0], 0, sk[1], 7.4, mat=dragon_mat('drag')))
    a0, a1 = at(2, 1.2), at(21, -0.4)
    parts.append(RoundCone((a0[0], 0, a0[1]), (a1[0], 0, a1[1]), 5.6, 3.0, mat=dragon_mat('drag')))
    jaw = P['jaw']
    jx, jz = fx * math.cos(jaw) - ux * math.sin(jaw), fz * math.cos(jaw) - uz * math.sin(jaw)
    jux, juz = ux * math.cos(jaw) + fx * math.sin(jaw), uz * math.cos(jaw) + fz * math.sin(jaw)
    h0 = at(1, -3)
    j1 = (h0[0] + 17 * jx, h0[1] + 17 * jz)
    parts.append(RoundCone((h0[0], 0, h0[1]), (j1[0], 0, j1[1]), 4.0, 2.0, mat=dragon_mat('drag')))
    body = Smooth(3.0, *parts)
    # crisp features: a heavy brow over the eye, the nose, horns swept back, a cheek spike, spines
    feats = []
    b0, b1 = at(-1, 6.6), at(10.5, 4.6)
    feats.append(RoundCone((b0[0], 2.0, b0[1]), (b1[0], 2.0, b1[1]), 3.1, 1.9, mat=dragon_mat('drag')))
    nb = at(19.6, 1.8); feats.append(Sphere(nb[0], 1.0, nb[1], 2.3, mat=dragon_mat('drag')))
    horn = lambda p_, n_, st, tt: 'horn%d' % max(0, min(6, st + 1))
    spine_mat = lambda p_, n_, st, tt: 'horn%d' % max(0, min(6, st - 1))
    for segs, r0 in ((((-2, 6), (-11, 11.5), (-22, 12)), 2.9), (((-5, 2.5), (-13, 4.5), (-20, 2.5)), 2.1)):
        hp = [at(a_, b_) for a_, b_ in segs]
        rr = (r0, r0 * 0.55, 0.35)
        for i in range(2):
            feats.append(RoundCone((hp[i][0], 1, hp[i][1]), (hp[i + 1][0], 1, hp[i + 1][1]), rr[i], rr[i + 1], mat=horn))
    c0, c1 = at(-2, -4), at(-10, -8)
    feats.append(RoundCone((c0[0], 1, c0[1]), (c1[0], 1, c1[1]), 2.0, 0.4, mat=spine_mat))
    spine = [(x, z + (11.5 - 4.6 * k / N) * 0.75, 0.45, 0.9, 5) for k, (x, z) in enumerate(pts[1:-1], 1)]
    spine += [(222, 92 + bob, 0.3, 1.0, 7), (234, 92 + bob, 0.3, 1.0, 7), (247, 89 + bob, 0.3, 1.0, 6), (259, 87 + bob, 0.35, 1.0, 6)]
    spine += [(x, z + (12 - 2 * (i + 1)) * 0.7, 0.4, 1.0, 5 - i) for i, (x, z) in enumerate(tail[1:4])]
    for x, z, nx_, nz_, hgt in spine:
        feats.append(RoundCone((x, 0, z - 1), (x + nx_ * hgt, 0, z - 1 + nz_ * hgt), 2.6, 0.3, mat=spine_mat))
    s.solid(Union(body, *feats))
    # near legs
    legs_near = Union(
        RoundCone((222, 9, 70 + bob), (214, 9, 56), 7.5, 5.2, mat=dragon_mat('drag')), RoundCone((214, 9, 56), (210, 9, 46), 5.2, 4.2, mat=dragon_mat('drag')),
        RoundCone((210, 9, 46), (199, 9, 44), 4.2, 2.6, mat=dragon_mat('drag')),
        Sphere(256, 9, 60 + bob, 10.5, mat=dragon_mat('drag')), RoundCone((260, 9, 56), (253, 9, 47), 6.2, 4.6, mat=dragon_mat('drag')),
        RoundCone((253, 9, 47), (242, 9, 44.5), 4.6, 2.8, mat=dragon_mat('drag')),
        RoundCone((200, 9, 44), (195, 9, 41), 1.6, 0.4, mat=horn), RoundCone((203, 9, 44), (198.5, 9, 40.5), 1.5, 0.4, mat=horn),
        RoundCone((243, 9, 44.5), (238, 9, 41), 1.6, 0.4, mat=horn), RoundCone((246, 9, 44.5), (241.5, 9, 40.5), 1.5, 0.4, mat=horn))
    s.solid(legs_near)
    # near wing, in front
    poly, elbow, wrist, tips = wing_points(234, 92 + bob, wing_ang, 1.0)
    bones = [((234, 92 + bob), elbow), (elbow, wrist)] + [(wrist, tp) for tp in tips]
    near = [Plate(poly, y0=14, t=0.7, mat=membrane_mat(bones))]
    near += [RoundCone((234, 14.8, 92 + bob), (elbow[0], 14.8, elbow[1]), 3.2, 2.4, mat=dragon_mat('drag')),
             RoundCone((elbow[0], 14.8, elbow[1]), (wrist[0], 14.8, wrist[1]), 2.4, 2.0, mat=dragon_mat('drag'))]
    for tip in tips:
        near.append(RoundCone((wrist[0], 15, wrist[1]), (tip[0], 15, tip[1]), 1.7, 0.6, mat='drag4'))
    near.append(RoundCone((wrist[0], 15.5, wrist[1]), (wrist[0] - 6, 15.5, wrist[1] + 5), 1.6, 0.4, mat=horn))   # the wing claw
    s.solid(Union(*near))
    eye = at(7.6, 2.9); mouth = at(22, -3.5); throat = [bezier(neck, k) for k in (0.35, 0.55, 0.75, 0.95)]
    return dict(eye=eye, mouth=mouth, throat=throat, neck=neck, head=E, f=(fx, fz), u=(ux, uz), at=at, jaw=jaw,
                h0=h0, jdir=(jx, jz), jup=(jux, juz))

# ---------------------------------------------------------------- the knight
def knight(s, t):
    _, p = phase(t)
    name, _ = phase(t)
    brace = 1.0 if name == 'breath' else (0.5 if name in ('inhale', 'settle') else 0.0)
    lean = -2.5 * brace
    wave = math.sin(t / FRAMES * 2 * math.pi * 4)
    gust = 1.0 + 1.6 * brace
    cape = [(65 + lean, 72), (60 + lean, 73), (52 - 5 * gust, 62 + 2 * wave), (47 - 7 * gust, 50 + 3 * wave), (55 - 4 * gust, 46 - wave),
            (61 - 2 * gust, 48 + wave), (65 + lean, 54)]
    def cape_mat(pp, n, step, tt):                                       # folds fan out from the shoulders
        ang = math.atan2(pp[2] - 72, pp[0] - (64 + lean))
        k = (ang * 5.5 + 0.35 * wave) % 2
        return 'cape%d' % max(0, min(6, step + (1 if k < 0.45 else (-1 if k > 1.55 else 0))))
    s.solid(Plate(cape, y0=-8, t=0.8, mat=cape_mat))
    legs = Union(RoundCone((69 + lean, -3, 55), (63, -3, 44), 4.0, 3.3, mat='steel2'), RoundCone((63, -3, 44), (67, -3, 41.3), 3.3, 2.4, mat='wood1'),
                 RoundCone((76 + lean, 3, 55), (81, 3, 44), 4.2, 3.4, mat='steel3'), RoundCone((81, 3, 44), (86, 3, 41.3), 3.4, 2.4, mat='wood2'))
    s.solid(legs)
    def armour(pp, n, step, tt):
        x, y, z = pp
        if 55 < z < 69 and n[1] > 0.5 and abs(x - (72 + lean)) < 5.5:          # the tabard
            if abs(x - (72 + lean)) > 4.4 or z < 56.2:
                return 'gold%d' % min(6, step + 1)
            return 'cape%d' % min(6, step + 1)
        if 74 < z < 78.2 and x > 72 + lean:                                       # the visor slit
            return 'ol' if z < 76.4 else 'steel%d' % max(0, step - 1)
        return 'steel%d' % step
    body = Smooth(1.4, RBox(63 + lean, -6, 53, 81 + lean, 6, 72, r=4.0, mat=armour),
                  Sphere(72.5 + lean, 0, 78, 7.2, mat=armour),
                  RoundCone((72 + lean, 0, 85), (63 + lean, 0, 90), 3.0, 2.2, mat='plume3'),
                  RoundCone((63 + lean, 0, 90), (54 + lean, 0, 85 + wave), 2.2, 1.0, mat='plume2'))
    s.solid(body)
    s.solid(Union(Sphere(69 + lean, 6, 70, 5.2, mat='steel'), RoundCone((69 + lean, 6, 67), (61 + lean, 6, 59), 3.0, 2.6, mat='steel'),
                  Plate([(61 + lean, 61), (63 + lean, 58.5), (40 + lean, 49), (38.5 + lean, 51.5)], y0=7, t=0.5, mat='steel5'),
                  RBox(59 + lean, 5.5, 57, 64 + lean, 7.5, 62.5, r=0.8, mat='gold3')))
    # the shield, face on, raised toward the fire
    cx, cz, rx, rz = 91 + lean, 67, 10.5, 12.5
    pts = [(cx + rx * math.cos(a), cz + rz * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    def shield_mat(pp, n, step, tt):
        dx, dz = (pp[0] - cx) / rx, (pp[2] - cz) / rz
        r = math.hypot(dx, dz)
        if r > 0.84:
            return 'steel%d' % min(6, step + 1)
        if r < 0.36 or (abs(dx) < 0.1 and r < 0.8) or (abs(dz) < 0.1 and r < 0.8):
            return 'gold%d' % min(6, step + 1)                       # a sun cross
        return 'shield%d' % step
    s.solid(Plate(pts, y0=8, t=1.0, mat=shield_mat))
    return dict(shield=(cx, cz))

# ---------------------------------------------------------------- the hall
def front_y(x):
    """the screen row where the coins meet the dragon's feet: the front lip of the hoard"""
    if x < 182:
        return 130 + (182 - x) * 0.8
    return 130 + 1.4 * math.sin(x / 7.3) + 0.9 * math.sin(x / 3.1 + 1)

def pile_y(x):
    """the top of the heap behind the dragon"""
    h = 4 + 24 * math.exp(-((x - 298) / 19) ** 2) + 13 * math.exp(-((x - 236) / 22) ** 2) + 1.5 * math.sin(x / 4.1)
    return front_y(x) - max(0.0, h) * min(1.0, max(0.0, (x - 166) / 14))

COIN = [[0, 3, 4, 3, 0], [2, 3, 3, 2, 1], [0, 1, 1, 1, 0]]          # one coin seen from the side and a little above

def coin_tile(w=96, h=60, seed=7):
    """a heap texture: coins stamped back to front with a little jitter, some on their edge"""
    T = np.ones((h, w), int)
    for row in range(-1, h // 2 + 1):
        for col in range(-1, w // 4 + 1):
            jx = int(hash2(col, row, seed) * 3) - 1; jy = int(hash2(col, row, seed + 1) * 2)
            x0, y0 = col * 4 + (2 if row % 2 else 0) + jx, row * 2 + jy
            edge = hash2(col, row, seed + 2) < 0.1
            stamp = [[3, 2], [3, 1], [2, 1]] if edge else COIN
            for j, r in enumerate(stamp):
                for i, v in enumerate(r):
                    if v:
                        T[(y0 + j) % h, (x0 + i) % w] = v
    return T

TILE = coin_tile()

def coin(x, y):
    """the heap: the tile, brighter along the top of the pile and its front lip, darker deeper in"""
    v = TILE[y % TILE.shape[0], x % TILE.shape[1]]
    d_top = y - pile_y(x); d_front = y - front_y(x)
    d = d_front if d_front >= 0 else d_top
    v += 0 if d < 2.5 else (-1 if d < 7 else -2)
    return 'gold%d' % max(0, min(5, v))

SPRITES = {
    'chalice': ["ooooooooo", "oBAAABCDo", "oCssssssD", ".oBCCCDo.", ".oBCrCDo.", "..oBCDo..", "...oCo...", "...oCo...",
                "..oBCDo..", ".oBCCCDDo", ".ooooooo."],
    'crown': [".o...o...o.", "oAo.oAo.oAo", "oBo.oBo.oDo", "oBCoBCCoCDo", "oBCCCrCCCDo", "oBCgCCCgCDo", "oABBBBBBCDo", "ooooooooooo"],
}
SPRITE_SLOTS = {'o': 'ol', 'A': 'gold6', 'B': 'gold5', 'C': 'gold4', 'D': 'gold3', 'E': 'gold2', 'r': 'ruby4',
                's': 'ruby1', 'g': 'sapph4'}

def sprite(G, name, x, y):
    """draw a little hand-placed sprite with its bottom-left at (x, y)"""
    rows = SPRITES[name]
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c != '.':
                put(G, x + i, y - len(rows) + 1 + j, SPRITE_SLOTS[c])

def hoard_front(G, t):
    """the front lip of the hoard drawn over the dragon's feet (the claws sink into the gold), and the treasure"""
    for x in range(166, W):
        for y in range(int(math.ceil(front_y(x))) + 1, 146):
            put(G, x, y, coin(x, y))
    for x, y, slot in ((214, 140, 'ruby'), (262, 138, 'sapph'), (288, 142, 'ruby'), (238, 143, 'sapph')):   # gems
        put(G, x, y, slot + '5'); put(G, x + 1, y, slot + '3'); put(G, x, y + 1, slot + '3'); put(G, x + 1, y + 1, slot + '2')
        put(G, x - 1, y, 'ol'); put(G, x + 2, y + 1, 'ol')
    for i in range(16):                                              # a sword someone left in the pile
        bx, by = 176 - i * 0.38, 136 - i
        put(G, bx, by, 'steel5' if i < 15 else 'steel6'); put(G, bx + 1, by, 'steel2')
    for i in range(-3, 4):
        put(G, 170 + i, 120 + i * 0.35, 'gold4' if i < 1 else 'gold3')
    for i in range(3):
        put(G, 169.6 - i * 0.38, 119 - i, 'wood2')
    put(G, 168.5, 115, 'ruby4'); put(G, 169.5, 115, 'ruby2')
    sprite(G, 'chalice', 186, int(front_y(190)) + 2)
    sprite(G, 'crown', 296, int(front_y(301)) + 1)
    for x, y in ((169, 147), (172, 149), (167, 150)):                # coins spilled down the rock
        put(G, x, y, 'gold5'); put(G, x + 1, y, 'gold3')

def glints(G, t):
    """coins and gems catching the light, one at a time"""
    for k, (x, y) in enumerate(((193, 137), (230, 141), (277, 135), (306, 127), (214, 140), (252, 144), (186, 122))):
        ph = (t + k * 17) % 40
        if ph < 5:
            arm = (0, 1, 2, 1, 0)[ph]
            put(G, x, y, 'glint')
            for d in range(1, arm + 1):
                for ox, oy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                    put(G, x + ox, y + oy, 'fire6' if d == 1 else 'fire5')

def put(G, x, y, v):
    if 0 <= x < W and 0 <= y < H:
        G[int(y), int(x)] = v

def hall(t):
    G = np.empty((H, W), object)
    for y in range(H):                                              # stone blocks
        row = y // 10
        off = 9 if row % 2 else 0
        for x in range(W):
            bx = (x + off) // 18
            v = 1 + (1 if hash2(bx, row, 21) < 0.35 else 0)
            if y % 10 == 0 or (x + off) % 18 == 0:
                G[y, x] = 'stone0'
            elif y % 10 == 1:
                G[y, x] = 'stone%d' % (v + 1)
            elif y % 10 == 9:
                G[y, x] = 'stone%d' % (v - 1)
            else:
                G[y, x] = 'stone%d' % v
    # the great arch behind the dragon: darkness with a red glow far below
    acx, acy, ar = 246, 44, 50
    for y in range(0, 134):
        for x in range(acx - ar - 6, acx + ar + 6):
            inside = (y >= acy and abs(x - acx) <= ar) or ((x - acx) ** 2 + (y - acy) ** 2 <= ar * ar)
            rim = (y >= acy and ar < abs(x - acx) <= ar + 5) or (ar * ar < (x - acx) ** 2 + (y - acy) ** 2 <= (ar + 5) ** 2 and y < acy)
            if inside:
                g = (y - 70) / 64
                v = 'void2' if (g > 0 and (BAYER4[y & 3, x & 3] + 0.5) / 16 < g) else 'void'
                put(G, x, y, v)
            elif rim:
                put(G, x, y, 'stone3' if ((x + y) // 4) % 3 else 'stone2')
    # pillars
    for px in (6, 124):
        for y in range(0, 150):
            for i, v in enumerate([1, 2, 3, 3, 3, 2, 2, 2, 1, 1, 1, 0, 0, 0]):
                put(G, px + 2 + i, y, 'stone%d' % (v + 1))
            put(G, px + 1, y, 'ol'); put(G, px + 16, y, 'ol')
        for y0 in (10, 132):
            for y in range(y0, y0 + 7):
                for x in range(px - 2, px + 20):
                    put(G, x, y, 'stone%d' % (4 if y == y0 else (3 if y < y0 + 4 else 2)))
                put(G, px - 3, y, 'ol'); put(G, px + 20, y, 'ol')
            for x in range(px - 3, px + 21):
                put(G, x, y0 - 1, 'ol'); put(G, x, y0 + 7, 'ol')
    # chains
    for cx in (100, 178):
        for y in range(0, 62):
            if y % 4 in (0, 3):
                put(G, cx, y, 'chain3'); put(G, cx + 1, y, 'chain2')
            else:
                put(G, cx - 1, y, 'chain2'); put(G, cx + 2, y, 'chain1')
    # banners (they sway)
    sway = 1 if (t // 10) % 2 else 0
    for bx in (34, 152):
        for y in range(0, 58):
            shift = sway if y > 30 else 0
            for x in range(bx, bx + 18):
                xx = x + shift
                tear = y > 52 and ((x - bx) % 6) in (0, 5) or y > 55 and ((x - bx) % 6) in (1, 4)
                if tear:
                    continue
                v = 'banner%d' % (3 if x - bx < 6 else (2 if x - bx < 13 else 1))
                if 18 <= y <= 30 and abs(x - bx - 9) + abs(y - 24) < 6:
                    v = 'gold%d' % (4 if abs(x - bx - 9) + abs(y - 24) < 3 else 3)
                put(G, xx, y, v)
            put(G, bx - 1 + shift, y, 'ol'); put(G, bx + 18 + shift, y, 'ol')
        for x in range(bx - 3, bx + 21):
            put(G, x, 0, 'wood3'); put(G, x, 1, 'wood1')
    # torch brackets on the pillars
    for tx, ty in TORCHES:
        for y in range(ty + 4, ty + 12):
            put(G, tx, y, 'wood2'); put(G, tx + 1, y, 'wood1')
        for x in range(tx - 2, tx + 4):
            put(G, x, ty + 3, 'steel2'); put(G, x, ty + 4, 'steel1')
    # the left ledge
    for y in range(132, 158):
        for x in range(0, 106 - max(0, y - 150)):
            row = (y - 132) // 8
            if y == 132:
                v = 'stone5'
            elif y == 133:
                v = 'stone4'
            elif (y - 132) % 8 == 0 or (x + (6 if row % 2 else 0)) % 14 == 0:
                v = 'stone0'
            else:
                v = 'stone%d' % (2 if (y - 132) % 8 < 3 else 1)
            put(G, x, y, v)
        put(G, 106 - max(0, y - 150), y, 'ol')
    for x in range(0, 106):
        put(G, x, 131, 'ol')
    # a fallen helm and a broken blade on the ledge: the last one who came
    for x, y, v in [(28, 129, 'steel3'), (29, 129, 'steel3'), (30, 129, 'steel2'), (27, 130, 'steel2'), (28, 130, 'steel4'), (29, 130, 'steel3'),
                    (30, 130, 'steel2'), (31, 130, 'steel1'), (27, 131, 'ol'), (31, 131, 'ol')]:
        put(G, x, y, v)
    for i in range(9):
        put(G, 12 + i, 130 - (i // 3), 'steel4' if i % 2 else 'steel3')
    # the hoard: coins heaped behind the dragon (the front lip is drawn over its feet later), rock under it
    for x in range(160, W):
        py = int(pile_y(x))
        for y in range(py, 146):
            put(G, x, y, coin(x, y))
        if py < 146:
            put(G, x, py - 1, 'ol'); put(G, x, py, 'gold5')
        for y in range(145, 158):
            if x >= 164 - (y - 145) * 0.7:
                put(G, x, y, 'rock%d' % (3 if y < 147 else (2 if hash2(x // 2, y // 2, 5) > 0.35 else 1)))
    # lava
    for y in range(150, H):
        for x in range(W):
            if G[y, x] is not None and str(G[y, x]).startswith(('rock', 'stone', 'ol')) and y < 158:
                continue
            put(G, x, y, 'lavaA')
    return G

TORCHES = [(13, 48), (131, 46)]

def lava_and_effects(G, t, L):
    """lava surface (palette cycled), bubbles, foreground stalagmites with lava rim light"""
    for y in range(150, H):
        for x in range(W):
            if G[y, x] == 'lavaA':
                wv = int(2 * math.sin(x / 9 + t / FRAMES * 2 * math.pi * 2) + 1.5 * math.sin(x / 4.3 - t / FRAMES * 2 * math.pi * 3))
                d = y - 150 - wv
                k = (x // 3 + y * 2 + t // 2) % 10
                G[y, x] = 'lava4' if d < 2 else ('lava3' if d < 5 or k == 0 else ('lava2' if d < 12 else 'lava1'))
    for i in range(6):                                               # bubbles: grow, pop
        bx = int(hash2(i, 1, 9) * W); period = 40; ph = (t + i * 17) % period
        if ph < 12:
            r = ph // 4
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        put(G, bx + dx, 154 + dy, 'lava4' if dx * dx + dy * dy < r * r - 1 else 'lava2')
    for base, flip in ((0, False), (W - 1, True)):                  # stalagmites framing the bottom corners
        for y in range(118, H):
            w = int((y - 118) * 0.55 + 3 * math.sin(y / 5))
            for k in range(max(0, w)):
                x = base + (k if not flip else -k)
                put(G, x, y, 'ol')
            edge = base + (w if not flip else -w)
            put(G, edge, y, 'lava2' if y > 140 else 'rock2')

def light_map(t, info):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    Lm = np.zeros((H, W))
    for tx, ty in TORCHES:
        fl = 1.0 + 0.12 * math.sin(t * 1.7 + tx) + 0.08 * math.sin(t * 3.1)
        r = np.hypot(xx - tx, yy - ty)
        Lm += np.clip(1.6 * fl * (1 - r / (46 * fl)), 0, None)
    Lm += np.clip(1.5 * (yy - 112) / 60, 0, None)                    # lava glow from below
    name, p = phase(t)
    mx, mz = info['mouth']; msx, msy = mx, OY - mz
    for gx, gy, gi, gr in throat_glow(t, info):
        r = np.hypot(xx - gx, yy - gy)
        Lm += np.clip(1.5 * gi * (1 - r / (gr * 2.4)), 0, None)
    if name in ('breath', 'settle'):
        k = 1.0 if name == 'breath' else max(0.0, 1 - p * 1.6)
        kx, kz = info['shield']; ksx, ksy = kx, OY - kz
        dx, dy = ksx - msx, ksy - msy; l2 = dx * dx + dy * dy
        s_ = np.clip(((xx - msx) * dx + (yy - msy) * dy) / l2, 0, 1)
        d = np.hypot(xx - (msx + s_ * dx), yy - (msy + s_ * dy))
        flick = 1 + 0.15 * math.sin(t * 2.3)
        Lm += np.clip(3.2 * k * flick * (1 - d / 70), 0, None)
    return Lm

def lit(G, Lm, flash=0):
    th = (BAYER4[np.arange(H)[:, None] & 3, np.arange(W)[None, :] & 3] + 0.5) / 16
    lvl = np.floor(np.clip(Lm, 0, 3.4) + th).astype(int) - 1 + flash  # -1 in the dark .. +3 in the fire
    out = G.copy()
    for y in range(H):
        for x in range(W):
            v = G[y, x]
            if v is None or str(v).startswith(EMISSIVE):
                continue
            base = str(v).rstrip('0123456789')
            if base == str(v):
                continue
            n = int(str(v)[len(base):]) + lvl[y, x]
            out[y, x] = '%s%d' % (base, max(0, min(6, n)))
    return out

def throat_glow(t, info):
    """fire building in the chest and climbing the throat: (screen x, y, intensity, radius) blobs"""
    name, p = phase(t)
    neck = info['neck']
    def at_k(k):
        x, z = bezier(neck, k)
        return x - 3, OY - z + 4                                       # toward the belly side of the neck
    if name == 'inhale':
        return [at_k(0.04 + 0.9 * ease(p)) + (0.7 + 0.35 * p, 9 + 5 * p)]
    if name == 'breath':
        gi = 1.0 - 0.6 * p
        return [at_k(k) + (gi * (0.55 + 0.45 * k), 7.0) for k in (0.45, 0.65, 0.85, 1.0)]
    if name == 'settle' and p < 0.3:
        return [at_k(0.9) + (0.4 * (1 - p / 0.3), 6.0)]
    return []

def scr(P):
    return P[0], OY - P[1]

def head_details(G, t, info, mask):
    """after lighting: the glowing belly plates, the inside of the mouth, teeth and the eye"""
    name, p = phase(t)
    blobs = throat_glow(t, info)
    if blobs:
        ys, xs = np.nonzero(np.vectorize(lambda v: isinstance(v, str) and v.startswith('belly'))(G))
        for y, x in zip(ys, xs):
            g = max(gi * (1 - math.hypot(x - gx, y - gy) / gr) for gx, gy, gi, gr in blobs)
            g += (BAYER4[y & 3, x & 3] / 16 - 0.5) * 0.14
            lv = 5 if g > 0.62 else (4 if g > 0.4 else (3 if g > 0.18 else 0))
            if lv:
                if int(OY - y) % 3 == 0:
                    lv -= 1                                               # the seams between the plates
                G[y, x] = 'fire%d' % lv
    at, (fx, fz), (ux, uz) = info['at'], info['f'], info['u']
    jaw, h0, (jx, jz), (jux, juz) = info['jaw'], info['h0'], info['jdir'], info['jup']
    hinge = scr(at(1.5, -2.0)); up_tip = scr(at(20, -2.8))
    lo_tip = scr((h0[0] + 15.5 * jx + 1.2 * jux, h0[1] + 15.5 * jz + 1.2 * juz))
    inner = {'idle': 'fire1', 'settle': 'fire1', 'inhale': 'fire2' if p < 0.5 else 'fire3', 'breath': 'fire4'}[name]
    xs_ = [hinge[0], up_tip[0], lo_tip[0]]; ys_ = [hinge[1], up_tip[1], lo_tip[1]]
    def inside(x, y):
        (x1, y1), (x2, y2), (x3, y3) = hinge, up_tip, lo_tip
        d1 = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
        d2 = (x - x3) * (y2 - y3) - (x2 - x3) * (y - y3)
        d3 = (x - x1) * (y3 - y1) - (x3 - x1) * (y - y1)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))
    for y in range(int(min(ys_)), int(max(ys_)) + 2):
        for x in range(int(min(xs_)), int(max(xs_)) + 2):
            if 0 <= x < W and 0 <= y < H and not mask[y, x] and inside(x + 0.5, y + 0.5):
                d = math.hypot(x - hinge[0], y - hinge[1])
                G[y, x] = 'fire5' if (name == 'breath' and d < 4) else ('fire4' if (name == 'breath' and d < 8) else inner)
    if jaw > 0.25:                                                     # teeth along both jaws, into the gap
        def tooth(ax, az, dx, dz, n):
            x, y = ax, OY - az
            for _ in range(24):                                          # march to the edge of the jaw
                if not (0 <= int(x) < W and 0 <= int(y) < H) or not mask[int(y), int(x)]:
                    break
                x += dx * 0.5; y -= dz * 0.5
            for k in range(n):
                X, Y = int(x + dx * k), int(y - dz * k)
                if 0 <= X < W and 0 <= Y < H and not mask[Y, X]:
                    G[Y, X] = 'glint' if k == n - 1 else 'horn6'
        for a_, n in ((7, 2), (10, 2), (13, 2), (16, 2), (18.5, 3)):
            b_ax = 1.2 - 1.6 * (a_ - 2) / 19
            ax, az = at(a_, b_ax)
            tooth(ax, az, -ux, -uz, n)
        for s_, n in ((5, 2), (8, 2), (11, 2), (14.5, 3)):
            ax, az = h0[0] + s_ * jx, h0[1] + s_ * jz
            tooth(ax, az, jux, juz, n)
    nx_, ny_ = scr(at(19.4, 1.9))                                         # a nostril
    if 0 <= int(ny_) < H and 0 <= int(nx_) < W and mask[int(ny_), int(nx_)]:
        G[int(ny_), int(nx_)] = 'ol'
    if jaw < 0.25:                                                     # the line of the closed mouth, curling up at the back
        for k in range(26):
            a_ = 2 + k * 0.7
            bx, bz = at(a_, -2.6 - 0.02 * a_ + (0.9 if a_ < 4 else 0))
            X, Y = int(round(bx)), int(round(OY - bz))
            if 0 <= X < W and 0 <= Y < H and mask[Y, X]:
                G[Y, X] = 'drag0'
    ex, ey = scr(info['eye']); ex, ey = int(round(ex)), int(round(ey))     # the eye under a heavy brow
    hot = name in ('inhale', 'breath')
    put(G, ex - 1, ey, 'glint' if hot else 'eye'); put(G, ex, ey, 'eye'); put(G, ex + 1, ey, 'pupil')
    put(G, ex - 2, ey - 1, 'ol'); put(G, ex - 1, ey - 1, 'ol'); put(G, ex, ey - 1, 'ol'); put(G, ex + 1, ey - 2, 'ol')

def fire_particles(G, t, info):
    name, p = phase(t)
    mx, mz = info['mouth']; kx, kz = info['shield']
    msx, msy, ksx, ksy = mx, OY - mz, kx + 2, OY - kz
    dx, dy = ksx - msx, ksy - msy; dist = math.hypot(dx, dy); ux, uy = dx / dist, dy / dist; px_, py_ = -uy, ux
    parts = []
    if name == 'breath' or (name == 'settle' and p < 0.25):
        for i in range(140):
            spawn = 48 + i * 0.3
            age = t - spawn
            life = 11.0
            if not (0 <= age < life) or spawn > 88:
                continue
            q = age / life
            s_ = min(q * 1.25, 1.0) * dist
            wob = math.sin(i * 1.7 + age * 0.9) * (2 + 7 * q)
            x = msx + ux * s_ + px_ * wob; y = msy + uy * s_ + py_ * wob
            r = 2.2 + 5.5 * q
            heat = 1 - q * 0.85
            if q > 0.78:                                               # it hits the shield and spreads over its face,
                sp = (q - 0.78) / 0.22                                 # licking around the rim
                side = 1 if i % 2 else -1
                spread = 24 * sp * (0.6 + 0.4 * hash2(i, 5, 5))
                y = ksy + side * spread + py_ * wob * 0.25
                x = ksx + 4 - 9 * sp * min(1.0, spread / 12)
                r *= 1 - 0.5 * sp
                heat = max(heat, 0.45 - 0.2 * sp)
            flick = hash2(i, t, 7)
            parts.append((heat, x, y, r * (0.85 + 0.3 * flick)))
    elif name == 'inhale':                                             # motes of fire drawn into the jaws
        for i in range(int(14 * p) + 2):
            a = hash2(i, 3, 11) * 2 * math.pi; k = (t * 0.06 + hash2(i, 4, 11)) % 1
            d = 4 + 22 * (1 - k)
            put(G, msx + math.cos(a) * d, msy + math.sin(a) * d * 0.7, 'fire5' if k > 0.6 else 'fire4')
    sx0, sz0 = info['shield']; srx, srz = 11.5, 13.5                 # the shield's face blocks the flames
    def blocked(x, y):
        return ((x - sx0) / srx) ** 2 + ((y - (OY - sz0)) / srz) ** 2 < 1.0 and name == 'breath'
    def disc(x, y, r, v):
        ri = int(r) + 1
        for oy in range(-ri, ri + 1):
            for ox in range(-ri, ri + 1):
                if ox * ox + oy * oy <= r * r and not blocked(x + ox, y + oy):
                    put(G, x + ox, y + oy, v)
    heat_slot = lambda h: 'fire6' if h > 0.8 else ('fire5' if h > 0.6 else ('fire4' if h > 0.4 else ('fire3' if h > 0.18 else 'fire2')))
    for heat, x, y, r in parts:                                          # the dark-red skin of the whole flame
        disc(x, y, r + 1.0, 'fire2')
    for heat, x, y, r in sorted(parts):                                  # its body, cooler first
        disc(x, y, r, heat_slot(heat - 0.12))
    for heat, x, y, r in sorted(parts):                                  # bright cores where it is hottest
        if heat > 0.35:
            disc(x, y, max(1.0, r * 0.55), heat_slot(heat + 0.15))
    if name == 'breath':                                               # sparks off the shield
        for i in range(10):
            a = hash2(i, t, 3) * math.pi - math.pi / 2
            sp = (t * 3 + i * 7) % 14
            put(G, ksx - 6 - sp * math.cos(a) * 1.4, ksy + sp * math.sin(a) * 1.6 - (sp * sp) * 0.04, 'fire6' if sp < 6 else 'fire4')
    if name == 'settle':                                               # wisps of smoke curl up from the jaws and the shield
        for i in range(10):
            age = (t - 90) - i * 2.0
            if age < 0:
                continue
            for k, (ox_, oy_) in enumerate(((msx, msy - 1), (ksx - 4, ksy - 12))):
                x = ox_ + math.sin(i * 2.1 + age * 0.25 + k) * (2 + age * 0.12); y = oy_ - age * 1.1 - i * 0.6
                r = 1.2 + age * 0.09
                fade = age / 26.0
                for oy in range(-int(r) - 1, int(r) + 2):
                    for ox in range(-int(r) - 1, int(r) + 2):
                        d = math.hypot(ox, oy) / max(r, 0.5)
                        th = (BAYER4[int(y + oy) & 3, int(x + ox) & 3] + 0.5) / 16
                        if d < 1 and th > fade * 0.8 + d * 0.35:
                            put(G, x + ox, y + oy, 'smoke2' if d < 0.5 and fade < 0.5 else 'smoke1')

def embers(G, t):
    for i in range(46):
        period = FRAMES / (1 + i % 3)
        ph = ((t + hash2(i, 2, 4) * period) % period) / period
        x = hash2(i, 1, 4) * W + 6 * math.sin(ph * 2 * math.pi * 2 + i)
        y = 160 - ph * 175
        put(G, x, y, 'fire5' if ph < 0.4 else ('fire4' if ph < 0.75 else 'fire3'))

def torch_flames(G, t):
    for k, (tx, ty) in enumerate(TORCHES):
        f = (t // 2 + k) % 4
        shape = [[(0, 0), (1, 0), (0, -1), (1, -1), (0, -2), (1, -3), (0, -4)],
                 [(0, 0), (1, 0), (0, -1), (1, -1), (1, -2), (0, -3), (1, -4)],
                 [(0, 0), (1, 0), (0, -1), (1, -1), (0, -2), (0, -3), (-1, -4)],
                 [(0, 0), (1, 0), (0, -1), (1, -1), (1, -2), (1, -3), (2, -4)]][f]
        for i, (dx, dy) in enumerate(shape):
            put(G, tx + dx, ty + 3 + dy, 'fire6' if i < 3 else ('fire5' if i < 5 else 'fire4'))
            put(G, tx + dx - 1, ty + 3 + dy, 'fire4' if i < 4 else 'fire3')
            put(G, tx + dx + 1, ty + 3 + dy, 'fire3')

def hud(G, t):
    for y in range(160, 179):
        for x in range(70, 250):
            put(G, x, y, 'ol')
    for x in range(69, 251):
        put(G, x, 159, 'stone1')
    for y in range(159, 180):
        put(G, 69, y, 'stone1'); put(G, 250, y, 'stone1')
    pixfont.draw(_GridSet(G), 'ASHMAW, THE EMBER WYRM', 160 - pixfont.width('ASHMAW, THE EMBER WYRM') // 2, 162, 'gold5', shadow='wood0')
    for x in range(78, 242):
        put(G, x, 173, 'fire3' if x < 200 else 'smoke1'); put(G, x, 174, 'fire2' if x < 200 else 'smoke0')
    for x in range(77, 243):
        put(G, x, 172, 'stone3'); put(G, x, 175, 'stone2')
    for i in range(3):
        pixfont.draw(_GridSet(G), '*', 6 + i * 7, 4, 'plume4')

class _GridSet:
    def __init__(self, G):
        self.G = G
    def set(self, x, y, v):
        put(self.G, x, y, v)

def frame(t):
    name, p = phase(t)
    shake = (1 if t % 2 else -1) if (name == 'breath' and p < 0.25) else 0
    s = Iso(W, H, origin=(0, OY), slots=PAL.keys(), camera='side')
    info = dragon(s, t)
    info.update(knight(s, t))
    actors = np.array(s.render(between=True, rim=True).a, object)
    G = hall(t)
    torch_flames(G, t)
    m = actors != None
    G[m] = actors[m]
    hoard_front(G, t)
    lava_and_effects(G, t, None)
    G = lit(G, light_map(t, info), flash=1 if (name == 'breath' and t - 48 < 2) else 0)
    head_details(G, t, info, m)
    glints(G, t)
    fire_particles(G, t, info)
    embers(G, t)
    hud(G, t)
    G = np.where(G == None, 'ol', G)
    if shake:
        G = np.roll(G, shake, axis=1)
    keys = sorted(set(G.ravel()))
    idx = np.vectorize({k: i for i, k in enumerate(keys)}.get)(G)
    rgb = np.array([cl.hex_to_rgb(PAL[k]) for k in keys], np.uint8)[idx]
    return Image.fromarray(rgb, 'RGB')

def render_frames(frames=FRAMES):
    return [frame(t) for t in range(frames)]

def export():
    return [{'name': 'dragonfire', 'frames': [], 'images': [f.convert('RGBA') for f in render_frames()],
             'anchor': (0, 0), 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    import time
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/dragon'
    for t in [int(a) for a in (sys.argv[2:] or ['10', '44', '60'])]:
        t0 = time.time()
        frame(t).resize((W * 3, H * 3), Image.NEAREST).save('%s-%03d.png' % (out, t))
        print(t, round(time.time() - t0, 2), 's')
