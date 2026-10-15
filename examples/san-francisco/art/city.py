"""Iso City: an isometric pixel-art diorama of San Francisco's North Beach and Financial District,
after an aerial photo: the Transamerica Pyramid, Redwood Park, the dark towers in front, row houses
and Saints Peter and Paul on Washington Square behind. Cars loop the blocks while the day turns
to dusk and night (one render, three palettes, dithered dissolves). 144 frames at 12 fps.

Built with tools/iso.py: boxes, a frustum, gable roofs, sprites; faces patterned by functions.
"""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
sys.path.insert(0, str(HERE))
import artlib, colorlib as cl
from iso import Iso, clone, frustum, windows, hash2, ground_dither, BAYER4
import palettes

W, H = 288, 288
N = 96                         # island size in units
STREETS = tuple(33 + 36 * k for k in range(-4, 8))   # street centre lines (both axes), every 36 units
ROAD, WALK = 3.0, 1.5          # road half-width, sidewalk width
LAMPS = [(cx + dx, cy + dy) for cx in STREETS for cy in STREETS for dx, dy in ((-4.8, -4.8), (4.8, 4.8))]
def nearest_c(v):
    return 33 + 36 * round((v - 33) / 36)
FRAMES, FPS = 144, 12

# ---------------------------------------------------------------- ground
def near_street(v):
    return abs(v - nearest_c(v))

def ground(u, v, t, face_step=3, **_):
    x, y = u, v
    dx, dy = near_street(x), near_street(y)
    sx, sy = 2 * (x - y), x + y
    lit = 0.0
    cx_, cy_ = nearest_c(x), nearest_c(y)
    for lx, ly in ((cx_ - 4.8, cy_ - 4.8), (cx_ + 4.8, cy_ + 4.8)):
        r = math.hypot(x - lx, y - ly)
        lit = max(lit, 1.0 if r < 3.5 else max(0.0, 1 - (r - 3.5) / 4.0))
    def L(slot):
        if lit >= 1 or (lit > 0 and ground_dither(sx, sy, lit)):
            return slot + 'L'
        return slot
    if dx < ROAD or dy < ROAD:
        if dx < ROAD and dy < ROAD:
            return L('road2')
        along_y = dx < ROAD
        a, b = (x, y) if along_y else (y, x)          # a: across the road, b: along it
        cb = abs(b - nearest_c(b))
        if ROAD + 0.2 < cb < ROAD + WALK + 1.2 and int((a - 0.25) * 2) % 2 == 0:
            return 'zebra'
        if abs(a - nearest_c(a)) < 0.3 and int(b / 3) % 2 == 0 and cb > ROAD + WALK:
            return 'lane'
        return L('road1' if hash2(int(x * 2), int(y * 2), 5) < 0.06 else 'road2')
    if dx < ROAD + WALK or dy < ROAD + WALK:
        seam = (int(x) % 4 == 0 if dy < ROAD + WALK and dx >= ROAD + WALK else int(y) % 4 == 0)
        return L('walk2' if seam else 'walk3')
    if x < 28.5 and 37.5 < y < 64.5:                  # Washington Square
        if abs((x - 2) - (y - 40) * 1.1) < 0.9 or abs(x - 15) < 0.7:
            return L('walk3')
        return L('grass3' if hash2(int(x), int(y), 9) > 0.12 else 'grass2')
    if 52 < x < 64.5 and 37.5 < y < 64.5:             # Redwood Park
        return L('grass2' if hash2(int(x), int(y), 4) < 0.25 else 'grass3')
    return L('walk2' if (x % 8 < 0.5 or y % 8 < 0.5) else 'walk3')        # paving, seams every 8

def water(u, v, t, face_step=3, **_):
    x, y = u, v - 22
    sx, sy = 2 * (x - y), x + y
    if (int(sx // 2) + int(sy) * 3) % 11 == 0 and hash2(int(sx // 6), int(sy), 2) < 0.6:
        return 'ww%d' % (int(sx // 2 + sy) % 4)                  # crests, animated by palette cycling
    if y > -12.0:                                              # foam along the seawall
        return 'wf%d' % (int(sx) % 3)
    return 'water2' if ground_dither(sx, sy, 0.2 + 0.6 * min(1.0, max(0.0, (y + 70) / 60)) ** 2) else 'water1'

def clock(u, v, t, face_step=2, **_):
    if 12 <= v < 15 and 0.8 <= u < 2.2:
        return 'white4'
    if int(v) % 4 == 2 and 3 < v < 11 and 1 <= u < 2:
        return 'glass'
    return 'cream%d' % face_step

def pier_deck(u, v, t, face_step=3, **_):
    return 'walk2' if int(u) % 2 == 0 else 'walk3'

def strata_low(u, v, t, face_step=2, **_):
    return strata(u, v + 4, t, face_step)

def strata(u, v, t, face_step=2, **_):
    if v >= 10.5:
        return 'walk%d' % (face_step + 1)
    if v >= 9.5:
        return 'grass%d' % face_step
    if abs(v - 5) < 0.5:
        return 'earth%d' % max(0, face_step - 1)
    if hash2(int(u * 2), int(v / 2), 3) < 0.07:
        return 'earth%d' % (face_step + 1)
    return 'earth%d' % face_step

# ---------------------------------------------------------------- sprites
TREE = """
..oooo..
.oTTTto.
oTTTtTto
oTtTtttO
otttttdo
.otdddo.
..oobo..
...obo..
"""
REDWOOD = """
..o..
.oTo.
.oTto
oTtto
otTdo
otttd
oTtdo
otddo
.obo.
.obo.
"""
def sprite(art, key):
    rows = [r for r in art.strip().splitlines()]
    g = artlib.Grid(len(rows[0]), len(rows))
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != '.':
                g.set(i, j, key[c])
    return g

TK = {'o': 'ol', 'T': 'tree4', 't': 'tree3', 'd': 'tree2', 'O': 'tree2', 'b': 'earth1'}
TREE_G, REDWOOD_G = sprite(TREE, TK), sprite(REDWOOD, TK)

# ---------------------------------------------------------------- buildings
def house(s, x, y, w, d, h, mat, seed, roof='flat'):
    win = windows(mat, 'glass', lit='lit' + 'ABCD'[seed % 4], every=(2, 4), size=(1, 2), margin=(1, 1), lit_share=0.5, seed=seed)
    s.box(x, y, 0, w, d, h, mat, top='roof%d' % (2 + seed % 2), left=win, right=win)
    if roof == 'gable':
        s.gable(x, y, h, w, d, 4, 'brick', along='x')
    elif seed % 3 == 0:                                   # rooftop box: stairs, water tank
        s.box(x + 1, y + 1, h, 2, 2, 2, 'roof')

def tower_windows(mat, glass='glass', every=(2, 3), seed=0, share=0.4):
    return windows(mat, glass, lit='lit' + 'ABCD'[seed % 4], every=every, size=(1, 2), margin=(0, 1), lit_share=share, seed=seed)

def bands(mat, glass='glass', period=3, seed=0):
    """horizontal ribbon windows (the Pyramid, the round tower)"""
    def f(u, v, t, face_step=2, **_):
        if int(v) % period == 1 and int(v) > 2:
            return 'lit' + 'ABCD'[seed % 4] if hash2(int(u // 2), int(v // period), seed) < 0.45 else glass
        return '%s%d' % (mat, face_step + 1)
    return f

def build_static():
    s = Iso(W, H, origin=(150, 66), slots=PALS['day'].keys())
    # the bay beyond the waterfront: water a little below the street, a pier, moored boats
    s.box(-140, -80, -12, 420, 70, 9, 'earth', top=lambda u, v, t, **k: water(u + -140, v + -80 + 22, t, **k), cast=False, lines=False)
    s.box(4, -24, -4, 3, 14, 4, 'brick', top='earth3', lines=True)                  # the pier
    s.box(22, -21, -4, 26, 11, 4, 'roof', top=pier_deck)                          # the wharf
    s.box(24, -19, 0, 20, 6, 7, 'cream', top='roof3', left=windows('cream', 'glass', every=(2, 7), size=(1, 4), margin=(0, 1)),
          right=windows('cream', 'glass', every=(2, 7), size=(1, 4), margin=(0, 1)))   # the Ferry Building
    s.box(32, -17.5, 7, 3, 3, 18, 'cream', top='roof3', left=clock, right=clock)
    s.pyramid(32, -17.5, 25, 3, 3, 5, 'roof', step_h=2, shrink=0.5, cap=1)
    s.box(-140, -10, -2, 420, 400, 2, 'walk', top=lambda u, v, t, **k: ground(u - 140, v - 10, t, **k), cast=False, lines=False)
    fill_blocks(s)
    rnd = lambda a, b, k: a + int(hash2(k, 7, 1) * (b - a + 1))
    pastel = ['cream', 'white', 'pink', 'mint', 'blue', 'cream', 'white']
    # back blocks: dense row houses (north beach)
    k = 0
    for bx0, by0 in ((0, 0), (37.5, 0), (0, 72.5 - 72.5)):
        pass
    for bx0, bx1 in ((0, 28.5), (37.5, 64.5), (72.5, 96)):
        for by0, by1 in ((0, 28.5),):
            x = bx0 + 1
            while x + 6 <= bx1:
                y = by0 + 1
                w = 6 if (k % 3) else 7
                while y + 6 <= by1:
                    d = 6 + (k % 2) * 2
                    if y + d > by1: d = int(by1 - y)
                    if d >= 5:
                        house(s, x, y, w - 0.5, d - 0.5, rnd(8, 15, k), pastel[k % len(pastel)], k,
                              roof='gable' if k % 5 == 2 else 'flat')
                    y += d; k += 1
                x += w
    # a mid-rise behind, the white slab with a grid (Coit-era apartment block)
    s.box(74, 2, 0, 12, 10, 34, 'white', top='roof3', left=tower_windows('white', seed=3), right=tower_windows('white', seed=4))
    # Washington Square, Saints Peter and Paul
    s.box(3, 39, 0, 16, 9, 14, 'white', left=windows('white', 'paneHi', every=(4, 6), size=(1, 3), margin=(1, 3)), right=windows('white', 'paneHi', every=(3, 6), size=(1, 3), margin=(1, 3)))
    s.gable(3, 39, 14, 16, 9, 5, 'roof', along='x')
    for sx in (3, 16):
        s.box(sx, 45, 0, 3, 3, 24, 'white', left=windows('white', 'paneHi', every=(3, 5), size=(1, 2), margin=(1, 14)))
        s.pyramid(sx, 45, 24, 3, 3, 8, 'white', step_h=3, shrink=0.5, cap=1)
    for i, (tx, ty) in enumerate([(6, 52), (11, 57), (20, 50), (24, 58), (7, 61), (22, 42), (14, 62), (25, 46)]):
        s.sprite(TREE_G, tx, ty, 0)
    # the Pyramid
    frustum(s, 41, 41, 0, 10, 10, 116, 'quartz', top_w=2.0, face=bands('quartz', period=3, seed=1), top='quartz4')
    s.box(41.5, 45, 70, 1, 2, 30, 'quartz', top='quartz4')          # the elevator wing
    s.box(44.5, 44.5, 116, 1, 1, 22, 'quartz', top='quartz4')       # the spire
    s.box(44.5, 44.5, 138, 1, 1, 1, 'quartz', top='beacon', left='beacon', right='beacon')
    # Redwood Park
    for i, (tx, ty) in enumerate([(55, 40), (58, 44), (61, 41), (56, 49), (60, 53), (63, 48), (57, 58), (61, 61), (54, 63)]):
        s.sprite(REDWOOD_G if i % 2 == 0 else TREE_G, tx, ty, 0)
    # a mid-rise beside the pyramid (back-right)
    s.box(39, 56, 0, 10, 8, 26, 'cream', top='roof2', left=tower_windows('cream', seed=6), right=tower_windows('cream', seed=7))
    # right block: the white tower with a grid
    s.box(75, 39, 0, 14, 12, 66, 'white', top='roof3', left=tower_windows('white', seed=8, share=0.5), right=tower_windows('white', seed=9, share=0.5))
    s.box(78, 42, 66, 6, 6, 5, 'roof')
    s.box(90, 52, 0, 5, 11, 22, 'brick', top='roof2', left=tower_windows('brick', seed=10), right=tower_windows('brick', seed=11))
    # left block (front-left): brick and cream mid-rises
    s.box(2, 75, 0, 12, 10, 30, 'brick', top='roof2', left=tower_windows('brick', seed=12), right=tower_windows('brick', seed=13))
    s.box(16, 75, 0, 11, 18, 40, 'cream', top='roof3', left=tower_windows('cream', seed=14), right=tower_windows('cream', seed=15))
    s.box(2, 87, 0, 12, 8, 16, 'pink', top='roof2', left=tower_windows('pink', seed=16), right=tower_windows('pink', seed=17))
    # front centre: the round dark tower
    s.cylinder(51, 84, 0, 9, 44, 'glassy', left=bands('glassy', 'paneHi', 3, seed=18), right=bands('glassy', 'paneHi', 3, seed=19), top='roof1')
    s.box(48, 81, 44, 6, 6, 4, 'metal')
    # front corner: the dark granite tower with a sawtooth crown
    s.box(74, 74, 0, 18, 18, 58, 'granite', top='roof1', left=tower_windows('granite', 'glass', every=(2, 3), seed=20, share=0.3), right=tower_windows('granite', 'glass', every=(2, 3), seed=21, share=0.3))
    for i in range(0, 18, 4):
        s.box(74 + i, 74, 58, 2, 18, 6 - (i % 8) // 2, 'granite', top='granite3')
    # lamps
    for lx, ly in LAMPS:
        s.box(lx, ly, 0, 0.5, 0.5, 6, 'metal', lines=False)
        s.box(lx - 0.25, ly - 0.25, 6, 1, 1, 1, 'metal', top='lamp', left='lamp', right='lamp', lines=False)
    return s

def fill_blocks(s):
    """the city past the hand-built centre: row houses behind, mid-rises and towers toward the
    Financial District in front, so the frame is city to every edge"""
    pastel = ['cream', 'white', 'pink', 'mint', 'blue', 'cream', 'white', 'brick']
    k = 1000
    cs = sorted(STREETS)
    for i in range(len(cs) - 1):
        x0, x1 = cs[i] + ROAD + WALK + 0.5, cs[i + 1] - ROAD - WALK - 0.5
        for j in range(len(cs) - 1):
            y0, y1 = cs[j] + ROAD + WALK + 0.5, cs[j + 1] - ROAD - WALK - 0.5
            if y1 < 0 or (-1 < x0 < 100 and -1 < y0 < 100):
                continue                                         # the bay, and the hand-built centre
            y0 = max(y0, -9)
            ctr = (x0 + x1 + y0 + y1) / 2                        # x + y: larger is nearer the viewer
            if hash2(i, j, 31) < 0.12:                           # a small park
                for n in range(6):
                    s.sprite(TREE_G, x0 + 3 + hash2(n, i, 32) * (x1 - x0 - 6), y0 + 3 + hash2(n, j, 33) * (y1 - y0 - 6), 0)
                continue
            nx = 2 if ctr > 150 else 3
            ny = 2 if ctr > 150 else 3
            for a in range(nx):
                for b in range(ny):
                    lx0 = x0 + (x1 - x0) * a / nx; lx1 = x0 + (x1 - x0) * (a + 1) / nx - 1
                    ly0 = y0 + (y1 - y0) * b / ny; ly1 = y0 + (y1 - y0) * (b + 1) / ny - 1
                    r = hash2(k, 3, 7)
                    if ctr > 170:
                        h = 30 + int(r * r * 60); mat = ['white', 'cream', 'granite', 'glassy', 'white'][k % 5]
                    elif ctr > 110:
                        h = 16 + int(r * 24); mat = ['cream', 'white', 'brick', 'cream'][k % 4]
                    else:
                        h = 7 + int(r * 9); mat = pastel[k % len(pastel)]
                    win = tower_windows(mat, seed=k, share=0.45) if h > 15 else windows(mat, 'glass', lit='lit' + 'ABCD'[k % 4], every=(2, 4), size=(1, 2), margin=(1, 1), lit_share=0.5, seed=k)
                    s.box(lx0, ly0, 0, lx1 - lx0, ly1 - ly0, h, mat, top='roof%d' % (1 + k % 3 if h > 15 else 2 + k % 2), left=win, right=win)
                    if h > 30 and hash2(k, 4, 7) < 0.5:
                        s.box(lx0 + 2, ly0 + 2, h, lx1 - lx0 - 4, ly1 - ly0 - 4, 4, 'metal')
                    k += 1

# ---------------------------------------------------------------- cars
LOOP = [(33, 33), (69, 33), (69, 69), (33, 69)]
CARS = [(0, 'carR', 1.6), (40, 'carY', 1.6), (90, 'carB', 1.6), (20, 'carW', -1.6), (70, 'carR', -1.6), (115, 'carY', -1.6)]

def car_at(p, lane):
    """position along the block loop (perimeter 144): x, y, direction (dx, dy)"""
    p %= 144
    i, f = int(p // 36), p % 36
    (x0, y0), (x1, y1) = LOOP[i], LOOP[(i + 1) % 4]
    dx, dy = (x1 - x0) / 36, (y1 - y0) / 36
    x, y = x0 + dx * f, y0 + dy * f
    # keep to the right of travel: offset perpendicular
    return x - dy * lane, y + dx * lane, (round(dx), round(dy))

def draw_cars(s, t):
    for off, mat, lane in CARS:
        direction = 1 if lane > 0 else -1
        p = (off + direction * t) % 144
        x, y, (dx, dy) = car_at(p, abs(lane))
        if direction < 0:
            dx, dy = -dx, -dy
            x, y = x, y
        L, Wd = 4, 2
        if dx:      # along x
            X, Y, w, d = x - L / 2, y - Wd / 2, L, Wd
        else:
            X, Y, w, d = x - Wd / 2, y - L / 2, Wd, L
        def lights(front):
            def f(u, v, tt, face_step=2, W=None, H=None):
                if 0.6 <= v < 1.6 and (u < 0.6 or u > (W or 2) - 0.6):
                    return 'head' if front else 'tail'
                return '%s%d' % (mat, face_step)
            return f
        right = lights(dx > 0) if dx else None          # +x face
        left = lights(dy > 0) if dy else None           # +y face
        s.box(X, Y, 0, w, d, 2, mat, top='%s4' % mat, left=left, right=right)
        s.box(X + (0.8 if dx else 0.3), Y + (0.3 if dx else 0.8), 2, w - (1.6 if dx else 0.6), d - (0.6 if dx else 1.6), 1, mat, top='paneHi', left='glass', right='glass')

BOATS = [(-10, -26, 0), (56, -30, 1), (12, -34, 2), (80, -40, 0)]

def draw_boats(s, t):
    for i, (bx, by, k) in enumerate(BOATS):
        bob = 0.5 if ((t // 12) + k) % 2 else 0.0
        z = -4.5 + bob
        s.box(bx, by, z, 6, 2, 1.5, 'white', top='earth3')
        s.box(bx + 2.5, by + 0.75, z + 1.5, 0.5, 0.5, 9, 'metal', lines=False)
        s.box(bx + 0.5, by + 0.9, z + 3, 2, 0.2, 6, 'white', top='white4', left='white4', right='white3', lines=False)
        s.box(bx + 3, by + 0.9, z + 3, 2.5, 0.2, 5, 'white', top='white4', left='white3', right='white2', lines=False)

GULL = [[(0, 0), (1, 1), (2, 1), (3, 0)], [(0, 1), (1, 0), (2, 0), (3, 1)]]

def draw_gulls(slots, t):
    for i, (y0, off) in enumerate(((60, 0), (78, 150), (52, 300))):
        x = int((off + t * (W + 40) / FRAMES)) % (W + 40) - 20
        y = y0 + (1 if (t // 6 + i) % 3 == 0 else 0)
        for dx, dy in GULL[(t // 3 + i) % 2]:
            X, Y = x + dx, y + dy
            if 0 <= X < W and 0 <= Y < H:
                slots[Y, X] = 'gull'

PEOPLE = [(35.9, 40, 'y', 0), (30.1, 50, 'y', 40), (40, 30.1, 'x', 80), (50, 35.9, 'x', 20), (66.1, 45, 'y', 60),
          (71.9, 80, 'y', 100), (80, 66.1, 'x', 10), (12, 71.9, 'x', 50), (20, 30.1, 'x', 120)]
SHIRTS = ['carR3', 'carB3', 'carY3', 'mint3', 'pink2', 'carW3']

def draw_people(s, t):
    for i, (px, py, axis, off) in enumerate(PEOPLE):
        f = ((t + off) % 144) / 72.0
        d = 18 * (f if f <= 1 else 2 - f)                       # 18 units out and back
        x, y = (px + d, py) if axis == 'x' else (px, py + d)
        g = artlib.Grid(1, 3)
        g.set(0, 0, 'pink3' if i % 2 else 'earth2'); g.set(0, 1, SHIRTS[i % len(SHIRTS)]); g.set(0, 2, 'ol')
        if (t // 3) % 2:
            g.set(0, 2, 'road1')
        s.sprite(g, x, y, 0, anchor=(0, 2))

# ---------------------------------------------------------------- sky and phases
STARS = [(int(hash2(i, 1, 2) * W), int(hash2(i, 2, 2) * 150)) for i in range(70)]

def sky_slots():
    g = np.empty((H, W), object)
    for y in range(H):
        f = y / H
        for x in range(W):
            th = (BAYER4[y & 3, x & 3] + 0.5) / 16
            band = 0 if f < 0.28 + 0.1 * th else (1 if f < 0.58 + 0.12 * th else 2)
            g[y, x] = 'sky%d' % band
    for i, (x, y) in enumerate(STARS):
        g[y, x] = 'star'
    for dy in range(-7, 8):                              # sun by day, moon by night
        for dx in range(-7, 8):
            r = math.hypot(dx, dy)
            if r <= 7:
                g[40 + dy, 70 + dx] = 'sun' if r <= 5.6 else 'sunB'
    return g

def timeline(t):
    """(palette A, palette B, fraction of B)"""
    seq = [('day', 30), ('dusk', 12), ('dusk', 24), ('night', 12), ('night', 54), ('day', 12)]
    k = 0
    for i, (name, n) in enumerate(seq):
        if t < k + n:
            if i in (1, 3, 5):
                prev = seq[i - 1][0]
                return prev, name, (t - k + 1) / (n + 1)
            return name, name, 0.0
        k += n
    return 'day', 'day', 0.0

def phase_palette(name, t):
    p = dict(PALS[name])
    for i in range(4):
        p['ww%d' % i] = p['water4'] if i == (t // 3) % 4 else (p['water3'] if i == (t // 3 + 1) % 4 else p['water2'])
    for i in range(3):
        p['wf%d' % i] = p['water4'] if i == (t // 3) % 3 else p['water3']
    if name != 'day':
        on = (t // 6) % 2 == 0
        p['beacon'] = p['beacon'] if on else p['quartz3']
        if hash2(t // 8, 3, 1) < 0.5:
            p['litD'] = p['litC']
        if name == 'night' and hash2(t // 10, 4, 1) < 0.3:
            p['litB'] = p['litC']
    return p

PALS = {k: f() for k, f in palettes.PHASES.items()}
for _p in PALS.values():
    for _i in range(4):
        _p['ww%d' % _i] = _p['water3']; _p['wf%d' % _i] = _p['water4']

def render_frames():
    base = build_static()
    sky = sky_slots()
    frames = []
    yy, xx = np.mgrid[0:H, 0:W]
    th = (BAYER4[yy & 3, xx & 3] + 0.5) / 16
    for t in range(FRAMES):
        s = clone(base)
        s.t = t
        draw_cars(s, t); draw_boats(s, t); draw_people(s, t)
        g = s.render()
        slots = np.array(g.a, object)
        slots = np.where(slots == None, sky, slots)
        draw_gulls(slots, t)
        a, b, f = timeline(t)
        pa, pb = phase_palette(a, t), phase_palette(b, t)
        keys = sorted(set(slots.ravel()))
        ia = {k: cl.hex_to_rgb(pa[k]) for k in keys}
        ib = {k: cl.hex_to_rgb(pb[k]) for k in keys}
        idx = np.vectorize({k: i for i, k in enumerate(keys)}.get)(slots)
        A = np.array([ia[k] for k in keys], np.uint8)[idx]
        B = np.array([ib[k] for k in keys], np.uint8)[idx]
        rgb = np.where((th < f)[..., None], B, A)
        frames.append(Image.fromarray(rgb, 'RGB').convert('RGBA'))
    return frames

def export():
    frames = render_frames()
    return [{'name': 'iso_city', 'frames': [], 'images': frames, 'anchor': (0, 0), 'tags': {'day_to_night': (0, FRAMES - 1)},
             'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    import time
    t0 = time.time()
    s = build_static(); s.t = 0; draw_cars(s, 0); draw_boats(s, 0); draw_people(s, 0)
    g = s.render()
    print('static + render', time.time() - t0)
    slots = np.array(g.a, object); sky = sky_slots(); slots = np.where(slots == None, sky, slots); draw_gulls(slots, 0)
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/iso_city')
    for name in ('day', 'dusk', 'night'):
        p = phase_palette(name, 0)
        im = Image.new('RGB', (W, H))
        im.putdata([cl.hex_to_rgb(p[k]) for k in slots.ravel()])
        im.resize((W * 3, H * 3), Image.NEAREST).save(str(out) + '-%s.png' % name)
    print('done', time.time() - t0)
