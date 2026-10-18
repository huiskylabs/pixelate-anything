"""Santorini: a cliffside village rebuilt as a 2:1 isometric diorama, after an aerial photo by
Vasilis Karkalas (Pexels 11222833): white cubes and barrel vaults stacked on terraces that climb
away from the caldera, turquoise plunge pools, zig-zag stairs, a blue-domed chapel, bougainvillea,
and an Oia windmill on the top terrace. The loop goes day -> golden sunset -> blue hour, with pools
shimmering, the windmill turning and a catamaran crossing the caldera. 144 frames at 12 fps.
"""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
import artlib, colorlib as cl
from iso import Iso, clone, windows, hash2, ground_dither, BAYER4, shade
from sdf import RBox, Cyl, Sphere, Cone, Union, Smooth, Sub, Inter, Above, Arch, Terrain
from palette import ramp
from oklab_relight import relight

W, H = 288, 288
FRAMES, FPS = 144, 12

# ---------------------------------------------------------------- palettes
MATS = {'pave': '#9da3b0', 'plaster': '#e9eef0', 'stone': '#8d6f62', 'rock': '#5b4846', 'pool': '#4fd2e2', 'sea': '#2a6db4',
        'dome': '#2f6ad8', 'bloom': '#d8327e', 'palm': '#4f9a48', 'clay': '#c8663e', 'wood': '#8a5a3c',
        'cream': '#efe0c2', 'sky': '#8fcaf0', 'boat': '#f2f2ee', 'metal': '#7b8291', 'shirt': '#e0b040'}

def day():
    p = {'ol': '#2a2236'}
    for k, base in MATS.items():
        for i, h in enumerate(ramp(base, 5, 26)):
            p['%s%d' % (k, i)] = h
    for i, h in enumerate(['#4f5878', '#8a98b8', '#c3cee0', '#e9eff3', '#ffffff']):   # whitewash: blue shadows
        p['plaster%d' % i] = h
    for i, h in enumerate(['#7a6458', '#a88e78', '#cdb69a', '#e6d6bc', '#f6ecda']):   # sandy paving
        p['cream%d' % i] = h
    p.update({'skyA': '#78bdeb', 'skyB': '#a3d4f3', 'skyC': '#cfe9f7', 'sun': '#fffbe6', 'sunB': '#ffeab0',
              'glass': '#4a6a9a', 'door': '#2f5fb8', 'litA': '#4a6a9a', 'litB': '#4a6a9a', 'lamp': '#d8d6c8',
              'foam': '#ffffff', 'star': '#a3d4f3', 'sail': '#ffffff'})
    return p

KEEP = tuple('pool%d' % i for i in range(5)) + ('door', 'glass')

def sunset():
    p = relight(day(), 0.92, 0.02, 35, 0.35, 1.12, keep=KEEP)
    p.update({'skyA': '#5b3f8c', 'skyB': '#d3608a', 'skyC': '#ffa860', 'sun': '#ffe08a', 'sunB': '#ff8c50',
              'litA': '#ffcf70', 'litB': '#7a6a8a', 'lamp': '#ffe7a0', 'star': '#d3608a', 'sail': '#ffd8b0'})
    return p

def night():
    p = relight(day(), 0.5, 0.03, 262, 0.45, 0.75)
    for i, h in enumerate(['#1c2040', '#2e3660', '#46527e', '#64729a', '#8c98b8']):   # moonlit whitewash
        p['plaster%d' % i] = h
    p.update({'skyA': '#0e1236', 'skyB': '#1c2556', 'skyC': '#33407a', 'sun': '#f2ecd0', 'sunB': '#bcb6a2',
              'litA': '#ffd27a', 'litB': '#ffb35a', 'lamp': '#fff1b0', 'star': '#f4f0d0', 'ol': '#0d0a18',
              'pool2': '#2fb8d8', 'pool3': '#58d8ec', 'pool4': '#a6f2ff', 'sail': '#c8c4d8'})
    return p

PALS = {'day': day(), 'sunset': sunset(), 'night': night()}
for _p in PALS.values():
    for _i in range(4):
        _p['pw%d' % _i] = _p['pool4']; _p['sw%d' % _i] = _p['sea3']; _p['sf%d' % _i] = _p['foam']

# ---------------------------------------------------------------- shape language
# What the reference is made of (read from the photo before building anything):
#   rounded whitewashed cubes that merge into each other and into the hillside; flat roofs that are
#   the terrace of the house above, edged by rounded parapets; white and blue barrel vaults; a few
#   domes; arched doors and windows cut deep into thick walls; curving terrace walls of volcanic
#   stone; stairs winding down between houses; kidney and rounded pools; bougainvillea and palms.
# So the kit is curved (tools/sdf.py): RBox with big corner radii, Smooth unions, Arch cut-outs,
# vaults and domes, a Terrain with curved, rounded terrace edges.

N = 96                                    # the shoreline: terraces for y < N, the caldera beyond
XR = (-110, 250)
def edge_off(x):
    return 4.5 * np.sin(np.asarray(x) / 17.0) + 2.5 * np.sin(np.asarray(x) / 6.3 + 1.3)
def tcoord(x, y):
    return (N - np.asarray(y) + edge_off(x)) / 16.0
def tindex(y, x=0.0):
    return int(np.floor(tcoord(x, y)))
def smoothstep(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
def height(x, y):
    u = tcoord(x, y)
    lvl = np.floor(u)
    hgt = 8 * (lvl + smoothstep(0.91, 1.0, u - lvl))
    return np.where(u < 0, -14 + 14 * smoothstep(-0.12, 0.0, u), hgt)
def level(y, x=0.0):
    return float(height(np.array([x]), np.array([y]))[0])
def front_y(x, lvl):
    """the downhill edge of terrace lvl at x"""
    return N + float(edge_off(x)) - 16 * lvl

POOLS = {}                                # terrace -> [(cx, cy, rx, ry, kidney)]
for ti in range(0, 14):
    x = XR[0] + int(hash2(ti, 3, 5) * 30)
    while x < XR[1]:
        if hash2(int(x), ti, 6) < 0.5:
            rx, ry = 3.2 + hash2(int(x), ti, 7) * 2, 1.8 + hash2(int(x), ti, 8) * 0.8
            POOLS.setdefault(ti, []).append((x + rx, front_y(x + rx, ti) - ry - 1.6, rx, ry, hash2(int(x), ti, 10) < 0.4))
        x += 30 + int(hash2(int(x), ti, 9) * 34)

def in_pool(x, y, ti):
    for cx, cy, rx, ry, kid in POOLS.get(ti, ()):
        if kid:                                   # a kidney: two rounded lobes
            d = min(np.hypot((x - cx + rx * 0.4) / (rx * 0.65), (y - cy) / ry), np.hypot((x - cx - rx * 0.45) / (rx * 0.5), (y - cy + 0.3) / (ry * 0.85)))
        else:                                     # a rounded rectangle
            qx, qy = max(abs(x - cx) - (rx - 1.2), 0), max(abs(y - cy) - (ry - 1.2), 0)
            d = np.hypot(qx, qy) / 1.2
        if d < 1.35:
            return d
    return None

def ground_mat(p, n, step, t):
    x, y, z = p
    if n[2] > 0.8:                                # terrace tops: paving, pools
        ti = tindex(y, x)
        d = in_pool(x, y, ti)
        if d is not None:
            if d >= 1.0:
                return 'plaster4'                 # the pool's rounded coping
            sx, sy = 2 * (x - y), x + y
            if (int(sx) + int(sy) * 2) % 7 == 0 and d < 0.8:
                return 'pw%d' % (int(sx // 7 + sy // 3) % 3)      # glints, animated by palette cycling
            return 'pool2' if d > 0.8 else ('pool3' if ground_dither(sx, sy, 0.4) else 'pool2')
        fy = front_y(x, ti)
        if fy - y < 2.6:                                  # the stone path along the terrace edge
            return 'pave1' if (int(x * 1.3) + int(y * 2)) % 4 == 0 else 'pave2'
        if int(x) % 6 == 0 or int(y) % 6 == 0:
            return 'pave3'
        return 'plaster3'
    top = 8 * np.ceil(z / 8 - 1e-6)               # retaining walls: stone with a whitewashed coping
    if top - z < 1.4:
        return 'plaster%d' % min(4, step + 1)
    if (int(x * 0.7) + int(z // 2.5) * 3) % 5 == 0 or int(z) % 3 == 0:
        return 'stone%d' % max(0, step - 1)
    return 'stone%d' % step

def sea_top(u, v, t, face_step=3, X=0, Y=0, **_):
    x, y = u + X, v + Y
    sx, sy = 2 * (x - y), x + y
    if (int(sx // 3) + int(sy) * 5) % 13 == 0:
        return 'sw%d' % (int(sx // 3 + sy) % 4)                 # wave crests, animated by palette cycling
    if tcoord(x, y) > -0.2:
        return 'sf%d' % (int(sx) % 3)                           # surf along the shore
    return 'sea3' if ground_dither(sx, sy, max(0.1, 0.7 - 0.5 * (y - N) / 40)) else 'sea2'

# ---------------------------------------------------------------- the kit
def facade_mat(seed):
    """whitewash, with the occasional pastel or stone house as in the photo"""
    r = hash2(seed, 1, 13)
    return 'cream' if r < 0.08 else ('stone' if r < 0.12 else 'plaster')

def cyc_house(x, yb, z, w, d, h, seed):
    """one Cycladic house: a rounded cube, its roof a terrace with a rounded parapet, arched
    door and windows cut in; sometimes a vault, a dome or a second storey set back"""
    mat = facade_mat(seed)
    body = RBox(x, yb, z, x + w, yb + d, z + h, r=1.4, mat=mat)
    parts = [body]
    r = hash2(seed, 2, 13)
    top = z + h
    if r < 0.3:                                                    # barrel vault
        vm = 'dome' if hash2(seed, 3, 13) < 0.18 else 'plaster'
        parts.append(Inter(Cyl(yb + d / 2, top - 0.6, None, d / 2 - 0.3, axis='x', x0=x + 0.4, x1=x + w - 0.4, mat=vm), Above(top - 0.6)))
    elif r < 0.325 and min(w, d) >= 7:                             # a small dome
        parts.append(Inter(Sphere(x + w / 2, yb + d / 2, top - 0.8, min(w, d) / 2 - 2.0, mat='dome'), Above(top - 0.5)))
    else:                                                          # flat roof terrace with a parapet
        rim = Sub(RBox(x + 0.2, yb + 0.2, top - 0.6, x + w - 0.2, yb + d - 0.2, top + 1.3, r=0.6, mat=mat),
                  RBox(x + 1.0, yb + 1.0, top - 1, x + w - 1.0, yb + d - 1.0, top + 3, r=0.8, mat=mat))
        parts.append(rim)
        if hash2(seed, 4, 13) < 0.4 and w > 8:                     # a second storey at the back
            w2, d2, h2 = w * 0.55, d * 0.55, 6 + int(hash2(seed, 5, 13) * 3)
            parts.append(RBox(x + 0.6, yb + 0.4, top - 0.5, x + 0.6 + w2, yb + 0.4 + d2, top + h2, r=1.2, mat=mat))
    house = Smooth(0.7, *parts)
    cuts = []
    dx = x + 1.5 + hash2(seed, 6, 13) * max(0.5, w - 5)           # arched door on the front (+y)
    cuts.append(Arch(dx, yb + d - 0.9, z, 2.0, 2.0, 5.2, axis='y', mat='door' if hash2(seed, 7, 13) < 0.6 else 'wood'))
    for k in range(int(w // 4)):                                   # arched windows, front and side
        wx = x + 1.6 + k * 4
        if abs(wx - dx) > 2.5 and wx + 1.4 < x + w - 1:
            cuts.append(Arch(wx, yb + d - 0.8, z + 3.2, 1.3, 1.6, 2.6, axis='y', mat='litA' if hash2(seed, k, 14) < 0.55 else 'glass'))
    if d > 6:
        cuts.append(Arch(x + w - 0.8, yb + d / 2 - 0.6, z + 3.2, 1.3, 1.6, 2.6, axis='x', mat='litB'))
    return Sub(house, *cuts)

def stair(x, lvl):
    """a whitewashed stair from terrace lvl+1 down to lvl, with a rounded side wall"""
    yb = front_y(x + 1.5, lvl + 1) - 0.8
    parts = []
    for i in range(8):
        z = 8 * lvl + 8 - (i + 1)
        parts.append(RBox(x, yb + i * 0.8 - 0.8, 8 * lvl - 0.5, x + 3, yb + (i + 1) * 0.8, z + 1, r=0.25, mat='plaster'))
    parts.append(RBox(x - 0.8, yb - 1, 8 * lvl - 0.5, x, yb + 6.6, 8 * lvl + 9, r=0.4, mat='plaster'))
    return Union(*parts)

def chapel(x, lvl):
    yb = front_y(x + 6, lvl + 1) + 1.0
    z = 8 * lvl
    body = RBox(x, yb, z, x + 12, yb + 9, z + 11, r=1.2, mat='plaster')
    dome_ = Union(Cyl(x + 6, yb + 4.5, z + 10.5, 3.6, hi=z + 12.5, mat='plaster'), Inter(Sphere(x + 6, yb + 4.5, z + 12.5, 3.6, mat='dome'), Above(z + 12.5)))
    bell = Sub(RBox(x + 0.5, yb + 7.4, z + 10.5, x + 5.5, yb + 8.6, z + 17, r=0.5, mat='plaster'),
               Arch(x + 1.3, yb + 7.0, z + 12.2, 1.4, 2.0, 3.0, mat='glass'), Arch(x + 3.3, yb + 7.0, z + 12.2, 1.4, 2.0, 3.0, mat='glass'))
    cross = Union(RBox(x + 5.8, yb + 4.3, z + 16, x + 6.2, yb + 4.7, z + 19, mat='plaster'), RBox(x + 5.1, yb + 4.3, z + 17.6, x + 6.9, yb + 4.7, z + 18.0, mat='plaster'))
    return Sub(Smooth(0.6, body, dome_, bell, cross), Arch(x + 7.5, yb + 8.2, z, 2.4, 2, 6, mat='door'))

CHAPEL = (88, 2)                           # x, terrace
WINDMILL = (46, 5)

BLOOM = """
..oBo..
.oBbBBo
oBbBbBo
oBBbBbo
.obBbo.
..oww..
..oww..
"""
UMBRELLA = """
..oSo..
.oSsSo.
oSsSsSo
...w...
...w...
"""
PALM = """
o.....o
Pp...pP
.PpopP.
..PPp..
...b...
...b...
...b...
"""
def sprite(art, key):
    rows = art.strip().splitlines()
    g = artlib.Grid(len(rows[0]), len(rows))
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != '.':
                g.set(i, j, key[c])
    return g
BLOOM_G = sprite(BLOOM, {'o': 'bloom1', 'B': 'bloom3', 'b': 'bloom2', 'w': 'plaster2'})
UMB_G = sprite(UMBRELLA, {'o': 'ol', 'S': 'plaster4', 's': 'dome3', 'w': 'wood1'})
PALM_G = sprite(PALM, {'o': 'palm1', 'P': 'palm3', 'p': 'palm2', 'b': 'wood2'})


def build_static():
    s = Iso(W, H, origin=(70, 24), slots=PALS['day'].keys(), camera='iso')
    s.box(XR[0], N - 30, -22, XR[1] - XR[0], 200, 12, 'sea', top=lambda u, v, t, **k: sea_top(u, v, t, X=XR[0], Y=N - 30, **k),
          left='sea1', right='sea1', cast=False, lines=False)
    s.solid(Terrain(height, XR[0], -140, XR[1], N + 6, -16, 8 * 15, mat=ground_mat, k=0.13), lines=True)
    k = 0
    for lvl in range(0, 14):
        x = XR[0] + int(hash2(lvl, 1, 9) * 6)
        while x < XR[1] - 6:
            w = 6 + int(hash2(k, 2, 9) ** 1.5 * 13)
            gap = 0 if hash2(k, 7, 9) < 0.6 else 2 + int(hash2(k, 8, 9) * 3)
            xm = x + w / 2
            yb = front_y(xm, lvl + 1) + 1.0                              # back against the wall above
            pool = any(abs(xm - cx) < rx + w / 2 + 1 for cx, cy, rx, ry, kid in POOLS.get(lvl, ()))
            room = front_y(xm, lvl) - yb - (7.5 if pool else 1.6)
            d = min(room, 8 + int(hash2(k, 3, 9) * 6))
            blocked = False
            if lvl == CHAPEL[1] and CHAPEL[0] - 4 < xm < CHAPEL[0] + 18:
                blocked = True
            if lvl == WINDMILL[1] and abs(xm - WINDMILL[0] - 4) < 9:
                blocked = True
            if not blocked and d >= 6:
                h = 6 + int(hash2(k, 4, 9) * 7)
                s.solid(cyc_house(x, yb, 8 * lvl, w, d, h, k))
                if hash2(k, 9, 9) < 0.28:
                    s.sprite(BLOOM_G, x + 0.4, yb + d + 0.6, 8 * lvl, upright=False)
            elif gap == 0 and hash2(k, 10, 9) < 0.5 and lvl < 13:
                s.solid(stair(x + 1, lvl))
            x += w + gap; k += 1
    s.solid(chapel(CHAPEL[0], CHAPEL[1]))
    wx, wl = WINDMILL; wy = front_y(wx, wl + 1) + 6; wz = 8 * wl
    s.solid(Sub(Union(Cyl(wx, wy, wz, 4.5, hi=wz + 17, mat='plaster'), Cone(wx, wy, wz + 16.5, wz + 23, 5.2, 0.6, mat='wood')),
                Arch(wx - 1, wy + 3.2, wz, 2.0, 2.5, 4.5, mat='door')))
    for ti, pools in POOLS.items():
        for cx, cy, rx, ry, kid in pools:
            s.sprite(UMB_G, cx + rx + 1.2, cy - ry + 0.5, 8 * ti, upright=False)
            if hash2(int(cx), ti, 11) < 0.5:
                s.sprite(PALM_G, cx - rx - 1.5, cy - 0.5, 8 * ti, upright=False)
    return s

# ---------------------------------------------------------------- moving things
def draw_windmill(s, t):
    """the sails, turning an eighth of a turn every 18 frames (8 steps per loop)"""
    wx, wl = WINDMILL; wy = front_y(wx, wl + 1) + 6; wz = 8 * wl
    ang = (t // 18) * (math.pi / 16) + (t % 18 >= 9) * (math.pi / 32)
    g = artlib.Grid(37, 37)
    for k in range(4):
        a = ang + k * math.pi / 2
        for r in range(2, 18):
            px, py = 18 + r * math.cos(a), 18 + r * math.sin(a)
            g.set(int(round(px)), int(round(py)), 'wood1')
            if r > 4:
                for w in range(1, 4):
                    qx, qy = px + w * math.cos(a + math.pi / 2), py + w * math.sin(a + math.pi / 2)
                    g.set(int(round(qx)), int(round(qy)), 'sail')
    g.set(18, 18, 'wood0')
    s.sprite(g, wx + 3.4, wy + 3.4, wz + 18, anchor=(18, 18), upright=False)

def draw_boat(s, t):
    x = 60 + t * 95 / FRAMES                                        # enters left, leaves past the bottom edge
    y = N + 14
    s.box(x, y, -10, 8, 3, 1.5, 'boat', top='boat4', left='boat3', right='boat2', cast=False)
    s.box(x + 2, y + 0.5, -8.5, 3, 2, 1.5, 'boat', top='boat3', cast=False)
    s.box(x + 4, y + 1.2, -8.5, 0.4, 0.4, 10, 'metal', lines=False, cast=False)
    s.box(x + 1.2, y + 1.3, -7, 2.6, 0.2, 8, 'boat', top='sail', left='sail', right='boat3', lines=False, cast=False)

PEOPLE = [(70, 1, 0), (110, 1, 40), (60, 2, 80), (120, 3, 20), (40, 2, 100), (95, 0, 60)]
def draw_people(s, t):
    for i, (x0, lvl, off) in enumerate(PEOPLE):
        f = ((t + off) % FRAMES) / (FRAMES / 2)
        x = x0 + 10 * (f if f <= 1 else 2 - f)
        y = front_y(x, lvl) - 1.5
        g = artlib.Grid(1, 3)
        g.set(0, 0, 'cream1'); g.set(0, 1, ['shirt3', 'bloom3', 'dome3', 'palm3', 'clay3', 'sea3'][i % 6]); g.set(0, 2, 'ol')
        s.sprite(g, x, y, 8 * lvl, anchor=(0, 2), upright=False)

# ---------------------------------------------------------------- sky, timeline, frames
def sky_slots():
    g = np.empty((H, W), object)
    for y in range(H):
        for x in range(W):
            th = (BAYER4[y & 3, x & 3] + 0.5) / 16
            f = y / H
            g[y, x] = 'skyA' if f < 0.3 + 0.1 * th else ('skyB' if f < 0.62 + 0.1 * th else 'skyC')
    for i in range(60):
        g[int(hash2(i, 2, 7) * 170), int(hash2(i, 1, 7) * W)] = 'star'
    for dy in range(-8, 9):
        for dx in range(-8, 9):
            r = math.hypot(dx, dy)
            if r <= 8:
                g[52 + dy, 60 + dx] = 'sun' if r <= 6.5 else 'sunB'
    return g

def cycle(p, t):
    """palette cycling: glints run across the pools, crests across the sea, surf breaks on shore"""
    p = dict(p)
    for i in range(3):
        p['pw%d' % i] = p['pool4'] if i == (t // 4) % 3 else p['pool3']
        p['sf%d' % i] = p['foam'] if i == (t // 3) % 3 else p['sea3']
    for i in range(4):
        p['sw%d' % i] = p['foam'] if i == (t // 3) % 4 else (p['sea3'] if i == (t // 3 + 1) % 4 else p['sea2'])
    return p

def timeline(t):
    seq = [('day', 36), ('sunset', 12), ('sunset', 36), ('night', 12), ('night', 36), ('day', 12)]
    k = 0
    for i, (name, n) in enumerate(seq):
        if t < k + n:
            if i in (1, 3, 5):
                return seq[i - 1][0], name, (t - k + 1) / (n + 1)
            return name, name, 0.0
        k += n
    return 'day', 'day', 0.0

def render_frames(frames=FRAMES):
    base = build_static()
    base.cast_shadows(sun=(-0.55, 0.65, 0.65), step=-2)
    sky = sky_slots()
    yy, xx = np.mgrid[0:H, 0:W]
    th = (BAYER4[yy & 3, xx & 3] + 0.5) / 16
    out = []
    for t in range(frames):
        s = clone(base); s.t = t
        # animated tops (pools, sea) are re-evaluated by redrawing those surfaces each frame
        draw_windmill(s, t); draw_boat(s, t); draw_people(s, t)
        slots = np.array(s.render().a, object)
        slots = np.where(slots == None, 'sea2', slots)
        a, b, f = timeline(t)
        pa, pb = cycle(PALS[a], t), cycle(PALS[b], t)
        keys = sorted(set(slots.ravel()))
        idx = np.vectorize({k: i for i, k in enumerate(keys)}.get)(slots)
        A = np.array([cl.hex_to_rgb(pa[k]) for k in keys], np.uint8)[idx]
        B = np.array([cl.hex_to_rgb(pb[k]) for k in keys], np.uint8)[idx]
        out.append(Image.fromarray(np.where((th < f)[..., None], B, A), 'RGB').convert('RGBA'))
    return out

def export():
    return [{'name': 'santorini', 'frames': [], 'images': render_frames(), 'anchor': (0, 0),
             'tags': {'day_sunset_night': (0, FRAMES - 1)}, 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    s = build_static(); s.cast_shadows(sun=(-0.55, 0.65, 0.65), step=-2); draw_windmill(s, 0); draw_boat(s, 40); draw_people(s, 0)
    slots = np.array(s.render().a, object); slots = np.where(slots == None, 'sea2', slots)
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/santorini'
    for name in ('day', 'sunset', 'night'):
        p = cycle(PALS[name], 0)
        im = Image.new('RGB', (W, H)); im.putdata([cl.hex_to_rgb(p[k]) for k in slots.ravel()])
        im.resize((W * 3, H * 3), Image.NEAREST).save('%s-%s.png' % (out, name))
