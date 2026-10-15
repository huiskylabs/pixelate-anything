"""San Francisco, rebuilt from the aerial photo in its own camera angle: looking north over the
Financial District from high up, the Transamerica Pyramid in the middle, dark towers cut off by
the bottom edge, North Beach, Washington Square and Saints Peter and Paul receding to the top.

Projection: 3/4 top-down (tools/iso.py camera 'topdown'): tops and front faces, every edge
horizontal or vertical. Buildings are placed by tracing the photo: bld() takes where a building's
roof sits on screen and how tall its front face is, and works out the 3D box. Afternoon sun from
the west casts shadows up and to the right, as in the photo; the far city fades into haze.
"""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
sys.path.insert(0, str(HERE))
import artlib, colorlib as cl
from iso import Iso, clone, frustum, windows, hash2, ground_dither, BAYER4, shade
import city                                     # palettes, trees, window patterns, phases
from city import PALS, TREE_G, REDWOOD_G, tower_windows, bands, timeline, phase_palette

W, H = 240, 360
DEP = 0.62                                      # ground foreshortening (looking down ~50 degrees)
FRAMES, FPS = 144, 12

def gy(sy):                                     # screen row of a ground point -> world y
    return sy / DEP

# ---------------------------------------------------------------- the street plan (world units)
VSTREETS = [(44, 52), (146, 154), (206, 213)]                       # north-south, x ranges
HSTREETS = [(gy(26), gy(32)), (gy(84), gy(90)), (gy(140), gy(146)), (gy(238), gy(244)), (gy(330), gy(337))]
def on_columbus(x, y):                                               # the diagonal avenue
    sx, sy = x, y * DEP
    d = abs((sx - 150) + (sy - 232) * 0.55) / math.hypot(1, 0.55)
    return d, (40 < sy < 232 and sx > 140)

def ground(u, v, t, face_step=3, **_):
    x, y = u, v
    for a, b in VSTREETS:
        if a <= x < b:
            if abs(x - (a + b) / 2) < 0.5 and int(y / 6) % 2 == 0:
                return 'lane'
            return 'road3'
        if a - 2 <= x < a or b <= x < b + 2:
            return 'walk3'
    for a, b in HSTREETS:
        if a <= y < b:
            return 'road3'
        if a - 3 <= y < a or b <= y < b + 3:
            return 'walk3'
    d, on = on_columbus(x, y)
    if on and d < 4:
        return 'road3'
    if on and d < 6:
        return 'walk3'
    if 150 <= x < 186 and gy(58) <= y < gy(80):                      # Washington Square
        return 'grass3' if hash2(int(x), int(y / 2), 3) > 0.1 else 'grass2'
    return 'walk2' if (int(x) % 9 == 0 or int(y) % 14 == 0) else 'walk3'

# ---------------------------------------------------------------- buildings, traced from the photo
RESERVED = []

def bld(s, x0, x1, top_back, top_front, h, mat, top=None, left=None, roof=True, reserve=True, **kw):
    """a building whose roof spans screen rows top_back..top_front and whose front face is h px tall"""
    Y = (top_back + h) / DEP
    d = max(1.0, (top_front - top_back) / DEP)
    s.box(x0, Y, 0, x1 - x0, d, h, mat, top=top or 'roof3', left=left, **kw)
    if reserve:
        RESERVED.append((x0 - 1, x1 + 1, Y - 2, Y + d + 2))
    return Y, d

def free(x0, x1, y0, y1):
    return not any(a < x1 and x0 < b and c < y1 and y0 < d for a, b, c, d in RESERVED)

def grid(mat, glass='glass', every=(3, 4), size=(2, 2), share=0.4, seed=0, margin=(1, 2)):
    return windows(mat, glass, lit='lit' + 'ABCD'[seed % 4], every=every, size=size, margin=margin, lit_share=share, seed=seed)

def vfins(mat, glass='glass', seed=0, period=3):
    """dark glass towers: vertical mullions, lit floors at night"""
    def f(u, v, t, face_step=1, **_):
        if int(u) % period == 0:
            return '%s%d' % (mat, face_step + 1)
        if int(v) % 4 == 1 and hash2(int(u) // period, int(v) // 4, seed) < 0.3:
            return 'lit' + 'ABCD'[seed % 4]
        return '%s%d' % (mat, face_step)
    return f

def pyramid_face(u, v, t, face_step=2, **_):
    """the Pyramid seen corner-on in the photo: lit west half, shaded east half, ribbon windows"""
    east = u >= 15
    if int(v) % 3 == 1 and v > 2:
        return ('lit' + 'ABCD'[int(hash2(int(u // 2), int(v // 3), 1) * 4)]) if hash2(int(u // 2), int(v // 3), 2) < 0.4 else 'glass'
    return 'quartz%d' % (2 if east else 4)

def flag(s, x, y, z):
    s.box(x, y, z, 0.5, 0.5, 14, 'metal', lines=False, cast=False)
    g = artlib.Grid(5, 3)
    for i in range(5):
        for j in range(3):
            g.set(i, j, 'carR3' if j != 1 else 'white4')
    for i in range(2):
        g.set(i, 0, 'carB2')
    s.sprite(g, x + 0.5, y, z + 14, anchor=(0, 0))

def landmarks(s):
    # the Pyramid, its wings and spire
    frustum(s, 109, 344, 0, 30, 30, 140, 'quartz', top_w=4, face=pyramid_face, top='quartz4')
    s.box(114, 354, 84, 2, 6, 66, 'quartz', top='quartz4')            # west wing (stairs)
    s.box(132, 354, 84, 2, 6, 70, 'quartz', top='quartz4')            # east wing (elevators)
    s.box(123.5, 358, 140, 1, 1, 22, 'quartz', top='quartz4', lines=False)
    s.box(123.5, 358, 162, 1, 1, 1, 'quartz', top='beacon', left='beacon', right='beacon', lines=False)
    RESERVED.append((104, 144, 338, 380))
    # Redwood Park, east of the Pyramid
    RESERVED.append((154, 176, gy(140), gy(160)))
    for i, (tx, sy) in enumerate([(158, 148), (163, 152), (168, 147), (172, 153), (160, 157), (167, 158)]):
        s.sprite(REDWOOD_G if i % 2 == 0 else TREE_G, tx, gy(sy), 0)
    # Washington Square and Saints Peter and Paul
    RESERVED.append((148, 188, gy(56), gy(82)))
    for tx, sy in [(153, 64), (160, 70), (170, 62), (178, 72), (183, 66), (165, 77), (156, 78), (175, 79)]:
        s.sprite(TREE_G, tx, gy(sy), 0)
    Y, d = bld(s, 194, 222, 52, 60, 14, 'white', left=grid('white', 'paneHi', every=(4, 6), size=(1, 3), margin=(2, 3)))
    s.gable(194, Y, 14, 28, d, 6, 'roof', along='x')
    for sx in (195, 216):
        s.box(sx, Y + d - 3, 0, 5, 3, 30, 'white', left=grid('white', 'paneHi', every=(5, 6), size=(1, 3), margin=(2, 20)))
        s.pyramid(sx, Y + d - 3, 30, 5, 3, 9, 'white', step_h=3, shrink=0.5, cap=1)
    # a smaller church on Columbus
    Y, d = bld(s, 163, 182, 96, 102, 10, 'white', left=grid('white', 'paneHi', every=(3, 5), size=(1, 2)))
    s.gable(163, Y, 10, 19, d, 4, 'roof', along='x')
    s.box(171, Y + d - 2, 0, 3, 2, 22, 'white')
    s.pyramid(171, Y + d - 2, 22, 3, 2, 5, 'white', step_h=2, shrink=0.5, cap=1)
    # the white apartment tower, top left
    bld(s, 14, 34, -12, 2, 48, 'white', left=grid('white', every=(3, 3), size=(2, 2), seed=2))
    # the long white block, mid left
    bld(s, 8, 50, 100, 116, 24, 'white', left=grid('white', every=(3, 4), size=(2, 2), seed=3))

def foreground(s):
    """the Financial District towers, nearest first in the photo's bottom half"""
    bld(s, 54, 92, 186, 196, 66, 'brick', left=grid('brick', every=(3, 4), size=(2, 2), seed=4))      # brown tower
    bld(s, 60, 98, 160, 176, 42, 'cream', left=grid('cream', every=(3, 4), size=(2, 2), seed=5))      # 60s block by the pyramid
    bld(s, 198, 236, 170, 190, 30, 'cream', left=grid('cream', every=(4, 4), size=(2, 2), seed=6))    # terraced offices
    bld(s, 200, 232, 160, 172, 10, 'cream', reserve=False)
    bld(s, 150, 186, 222, 232, 22, 'brick', left=grid('brick', every=(3, 4), size=(2, 2), seed=7))    # low offices
    bld(s, 30, 66, 196, 204, 150, 'cream', left=grid('cream', every=(3, 3), size=(2, 2), seed=8, share=0.45))
    bld(s, 0, 28, 186, 204, 190, 'white', left=grid('white', every=(3, 3), size=(2, 2), seed=9, share=0.45))
    flag(s, 14, (186 + 190) / DEP + 4, 190)
    bld(s, 8, 38, 230, 238, 168, 'white', left=grid('white', every=(3, 3), size=(2, 2), seed=10, share=0.45))
    bld(s, 40, 90, 264, 272, 112, 'white', left=grid('white', every=(4, 4), size=(3, 2), seed=11))
    bld(s, 58, 108, 306, 316, 84, 'white', left=grid('white', every=(4, 4), size=(3, 2), seed=12))
    # the dark granite tower with the sawtooth crown (centre)
    Y, d = bld(s, 98, 150, 250, 266, 140, 'granite', left=vfins('granite', seed=13), top='granite2')
    for i in range(0, 52, 8):
        s.box(98 + i, Y + 1, 140, 5, d - 2, 8, 'granite', top='granite3', left=vfins('granite', seed=14))
    # the white tower behind the round one
    bld(s, 142, 190, 250, 262, 122, 'white', left=grid('white', every=(3, 3), size=(2, 2), seed=15, share=0.5))
    # the big dark tower, right
    bld(s, 190, 240, 204, 226, 200, 'glassy', left=vfins('glassy', seed=16, period=4), top='glassy1')
    # the round dark tower, bottom centre
    cy = (292 + 112) / DEP + 32
    s.cylinder(170, cy, 0, 32, 112, 'glassy', left=bands('glassy', 'paneHi', 3, seed=17), top='roof1')
    s.box(160, cy - 12, 112, 20, 14, 6, 'metal')
    s.box(164, cy - 9, 118, 12, 8, 4, 'roof')

def north_beach(s):
    """fill the rest with row houses and small apartment blocks, back to front"""
    pastel = ['white', 'cream', 'white', 'cream', 'pink', 'blue', 'mint', 'white', 'cream']
    k = 0
    ys = sorted(set([0.0] + [b for a, b in HSTREETS] + [a for a, b in HSTREETS] + [gy(330)]))
    bands_y = [(a, b) for a, b in zip(ys[:-1], ys[1:]) if all(not (a >= s0 and b <= s1) for s0, s1 in HSTREETS)]
    xs = sorted(set([0, W] + [v for a, b in VSTREETS for v in (a - 2, b + 2)]))
    blocks_x = [(a, b) for a, b in zip(xs[:-1], xs[1:]) if all(not (a >= s0 - 2 and b <= s1 + 2) for s0, s1 in VSTREETS)]
    for y0, y1 in bands_y:
        if y0 > gy(250):
            continue
        y = y0 + 3
        while y + 12 < y1 - 3:
            dpt = 24 + int(hash2(k, 1, 4) * 14)
            dpt = min(dpt, y1 - 3 - y)
            for x0, x1 in blocks_x:
                x = x0 + 1
                while x + 6 < x1:
                    w = 10 + int(hash2(k, 2, 4) * 12)
                    w = min(w, x1 - 1 - x)
                    if w < 6:
                        break
                    dcol, on = on_columbus(x + w / 2, y + dpt / 2)
                    if free(x, x + w, y, y + dpt) and not (on and dcol < 8):
                        h = 5 + int(hash2(k, 3, 4) ** 2 * 10) + (8 if hash2(k, 5, 4) > 0.92 else 0)
                        mat = pastel[k % len(pastel)]
                        roof = '%s4' % mat if hash2(k, 6, 4) < 0.7 else 'roof%d' % (3 + k % 2)
                        s.box(x, y, 0, w - 0.5, dpt - 0.5, h, mat, top=roof,
                              left=grid(mat, every=(3, 4), size=(1, 2), seed=k, margin=(1, 1)))
                        if k % 3 == 0:
                            s.box(x + 1 + k % 3, y + 2, h, 3, 3, 3, 'roof')
                        elif k % 7 == 1:
                            s.box(x + w - 4, y + 1, h, 2, 2, 4, 'earth')          # a water tank
                    x += w; k += 1
            y += dpt
    # trees along Columbus
    for i in range(14):
        sy = 60 + i * 12
        sx = 150 - (sy - 232) * 0.55
        for side in (-7, 7):
            if free(sx + side - 2, sx + side + 2, gy(sy) - 2, gy(sy) + 2):
                s.sprite(TREE_G, sx + side, gy(sy), 0)

def build_static():
    RESERVED.clear()
    s = Iso(W, H, origin=(0, 0), slots=PALS['day'].keys(), camera='topdown', depth=DEP)
    s.box(-4, -40, -2, W + 8, 760, 2, 'walk', top=ground, cast=False)
    landmarks(s)
    foreground(s)
    north_beach(s)
    s.cast_shadows(sun=(-0.75, 0.35, 0.62), step=-1)
    return s

def haze(slots, s):
    """the far city fades: one step lighter, dithered in toward the top"""
    yy, xx = np.mgrid[0:H, 0:W]
    th = (BAYER4[yy & 3, xx & 3] + 0.5) / 16
    f = np.clip((gy(46) - s.world[..., 1]) / gy(14), 0, 1)
    m = (s.obj >= 0) & (th < f)
    for y, x in zip(*np.nonzero(m)):
        slots[y, x] = shade(slots[y, x], +1) if shade(slots[y, x], +1) in PALS['day'] else slots[y, x]
    return slots

# ---------------------------------------------------------------- traffic
CARS = [(0, 'carR', 0, 1), (60, 'carY', 0, -1), (20, 'carW', 1, 1), (90, 'carB', 1, -1), (45, 'carR', 2, 1),
        (110, 'carW', 2, -1), (30, 'carB', 3, 1), (100, 'carY', 4, -1)]

def draw_cars(s, t):
    for off, mat, street, direction in CARS:
        if street < 3:                                   # north-south streets (vertical on screen)
            a, b = VSTREETS[street]
            lane = (a + b) / 2 + (1.2 if direction > 0 else -3.2)
            span = 600
            y = (off * 5 + direction * t * span / FRAMES) % span - 20
            s.box(lane, y, 0, 2, 5, 2, mat, top='%s4' % mat, left='head' if direction > 0 else 'tail', cast=False)
            s.box(lane + 0.3, y + 1.4, 2, 1.4, 2.2, 1, mat, top='paneHi', left='glass', cast=False, lines=False)
        else:                                            # east-west streets
            a, b = HSTREETS[1 if street == 3 else 2]
            lane = (a + b) / 2 + (1 if direction > 0 else -4)
            x = (off * 2 + direction * t * (W + 20) / FRAMES) % (W + 20) - 10
            s.box(x, lane, 0, 5, 3, 2, mat, top='%s4' % mat, left='%s2' % mat, cast=False)
            s.box(x + 1.2, lane + 0.5, 2, 2.4, 2, 1, mat, top='paneHi', left='glass', cast=False, lines=False)

GULLS = [(30, 0), (52, 90), (80, 200)]
def draw_gulls(slots, t):
    for i, (y0, off) in enumerate(GULLS):
        x = int(off + t * (W + 30) / FRAMES) % (W + 30) - 15
        y = y0 + (1 if (t // 6 + i) % 3 == 0 else 0)
        for dx, dy in city.GULL[(t // 3 + i) % 2]:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                slots[y + dy, x + dx] = 'gull'

def render_frames(frames=FRAMES):
    base = build_static()
    out = []
    yy, xx = np.mgrid[0:H, 0:W]
    th = (BAYER4[yy & 3, xx & 3] + 0.5) / 16
    for t in range(frames):
        s = clone(base); s.t = t
        draw_cars(s, t)
        slots = np.array(s.render().a, object)
        slots = haze(slots, s)
        draw_gulls(slots, t)
        slots = np.where(slots == None, 'walk3', slots)
        a, b, f = timeline(t)
        pa, pb = phase_palette(a, t), phase_palette(b, t)
        keys = sorted(set(slots.ravel()))
        idx = np.vectorize({k: i for i, k in enumerate(keys)}.get)(slots)
        A = np.array([cl.hex_to_rgb(pa[k]) for k in keys], np.uint8)[idx]
        B = np.array([cl.hex_to_rgb(pb[k]) for k in keys], np.uint8)[idx]
        out.append(Image.fromarray(np.where((th < f)[..., None], B, A), 'RGB').convert('RGBA'))
    return out

def export():
    return [{'name': 'sf_rebuild', 'frames': [], 'images': render_frames(), 'anchor': (0, 0),
             'tags': {'day_to_night': (0, FRAMES - 1)}, 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    import time
    t0 = time.time()
    s = build_static(); draw_cars(s, 0)
    slots = np.array(s.render().a, object); slots = haze(slots, s); draw_gulls(slots, 0)
    slots = np.where(slots == None, 'walk3', slots)
    print('render', round(time.time() - t0, 2))
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/sf'
    for name in ('day', 'night'):
        p = phase_palette(name, 0)
        im = Image.new('RGB', (W, H)); im.putdata([cl.hex_to_rgb(p[k]) for k in slots.ravel()])
        im.resize((W * 3, H * 3), Image.NEAREST).save('%s-%s.png' % (out, name))
