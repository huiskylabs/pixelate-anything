"""Island Village: an original Game Boy-style top-down RPG screen (tools/era.py 'gameboy':
160x144, 4 shades), set in the Cycladic village of the Santorini rebuild.

A traveller in a sun hat stops on the lane; a cat sits on the sea wall; the windmill turns, the
waves drift, a gull crosses, the pool glints, and the dialogue box waits with a blinking arrow.
Drawn in the RPG 3/4 view: flat roofs from above, house fronts facing the viewer. 96 frames at
12 fps; every motion divides the loop.
"""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
import colorlib as cl
import pixfont

W, H = 160, 144
FRAMES, FPS = 96, 12
SHADES = [np.array(cl.hex_to_rgb(h), np.uint8) for h in ('#0f380f', '#306230', '#678e23', '#9bbc0f')]   # 0 dark .. 3 light

class Canvas:
    def __init__(self):
        self.a = np.full((H, W), 3, np.int8)
    def set(self, x, y, v):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H:
            self.a[y, x] = int(v)
    def rect(self, x0, y0, x1, y1, v):
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(W, int(x1)), min(H, int(y1))
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = v
    def stamp(self, art, x, y, flip=False):
        for j, r in enumerate(art.strip('\n').split('\n')):
            if flip:
                r = r[::-1]
            for i, ch in enumerate(r):
                if ch in '0123':
                    self.set(x + i, y + j, ch)

# ---------------------------------------------------------------- parts
def sea(c, x0, y0, x1, y1, t):
    c.rect(x0, y0, x1, y1, 1)
    sh = t // 6                                                  # 16 px pattern, 1 px per 6 frames
    for y in range(y0 + 2, y1, 4):
        for x in range(x0 - 16, x1 + 16, 16):
            xx = x + ((y // 4) % 2) * 8 + sh % 16
            for k in range(3):
                if x0 <= xx + k < x1:
                    c.set(xx + k, y, 2)
            if x0 <= xx + 1 < x1 and (y // 4) % 3 == 0:
                c.set(xx + 1, y - 1, 3)

def house(c, x, y, w, roof_h, wall_h, door=True, windows=2, shade_right=True):
    """a whitewashed cube in 3/4 view: flat roof from above with a parapet, front wall below"""
    c.rect(x, y, x + w, y + roof_h, 3)
    c.rect(x + 1, y + 1, x + w - 1, y + 2, 2)                        # parapet inner edge
    c.rect(x + 1, y + 1, x + 2, y + roof_h - 1, 2)
    c.rect(x, y + roof_h, x + w, y + roof_h + wall_h, 2)              # the front wall, in shade
    c.rect(x, y + roof_h, x + w, y + roof_h + 1, 0)                  # the roof lip
    c.rect(x + 1, y + roof_h + 1, x + w - 1, y + roof_h + 2, 1)      # its shadow on the wall
    if shade_right:
        c.rect(x + 1, y + roof_h + 2, x + 2, y + roof_h + wall_h - 1, 3)   # a sunlit corner
    c.rect(x, y, x + w, y + 1, 0); c.rect(x, y, x + 1, y + roof_h + wall_h, 0)
    c.rect(x + w - 1, y, x + w, y + roof_h + wall_h, 0); c.rect(x, y + roof_h + wall_h - 1, x + w, y + roof_h + wall_h, 0)
    by = y + roof_h + wall_h - 1
    if door:
        dx = x + w // 2 - 3 if windows != 1 else x + 3
        arch(c, dx, by - 9, 6, 9, 1)
        c.rect(dx + 4, by - 5, dx + 5, by - 4, 3)                    # the door knob
    k = 0
    for i in range(windows):
        wx = x + 3 + i * (w - 10) // max(1, windows - 1) if windows > 1 else x + w - 8
        if door and abs(wx - (x + w // 2 - 3)) < 7:
            continue
        window(c, wx, y + roof_h + 3)

def arch(c, x, y, w, h, v):
    c.rect(x + 1, y, x + w - 1, y + 1, v)
    c.rect(x, y + 1, x + w, y + h, v)
    c.rect(x + 1, y, x + w - 1, y + 1, 0) if v != 0 else None

def window(c, x, y):
    arch(c, x + 1, y, 3, 5, 0)
    c.rect(x, y + 1, x + 1, y + 5, 1); c.rect(x + 4, y + 1, x + 5, y + 5, 1)   # shutters

def dome(c, cx, cy, r):
    for y in range(-r, 1):
        for x in range(-r, r + 1):
            d = math.hypot(x, y)
            if d <= r:
                v = 0 if d > r - 1 else (2 if (x < -r * 0.2 and y < -r * 0.35 and d < r - 1.5) else 1)
                c.set(cx + x, cy + y, v)
    c.rect(cx - r, cy, cx + r + 1, cy + 1, 0)
    c.rect(cx, cy - r - 5, cx + 1, cy - r, 0); c.rect(cx - 2, cy - r - 4, cx + 3, cy - r - 3, 0)    # the cross

def wall(c, x0, x1, y, h=7):
    """the low sea wall: whitewashed coping on stone"""
    c.rect(x0, y, x1, y + 2, 3); c.rect(x0, y + 2, x1, y + 3, 2)
    c.rect(x0, y + 3, x1, y + h, 2)
    for x in range(x0, x1, 5):
        c.rect(x, y + 3 + (x // 5) % 2, x + 1, y + h, 1)
    c.rect(x0, y + h - 1, x1, y + h, 1); c.rect(x0, y - 1, x1, y, 0)

def cobbles(c, x0, y0, x1, y1):
    c.rect(x0, y0, x1, y1, 2)
    for y in range(y0, y1, 4):
        off = 0 if (y // 4) % 2 else 3
        for x in range(x0 + off, x1, 6):
            c.rect(x, y + 3, x + 4, y + 4, 1); c.set(x + 4, y + 2, 1)
            c.set(x + 1, y + 1, 3)

HERO = ["""
....000000......
...03333330.....
..0333333330....
.000000000000...
...0110110......
...0131131......
....01111.......
...0222220......
..022222220.....
..0212222120....
...0122221......
....022220......
....01001.......
....01.01.......
...001.001......
................
""", """
................
....000000......
...03333330.....
..0333333330....
.000000000000...
...0110110......
...0131131......
....01111.......
...0222220......
..022222220.....
..0212222120....
...0122221......
....022220......
....01001.......
...001.001......
................
"""]
CAT = ["""
.0...0....
.00.00....
.01010....
.03130....
.01110....
..0110..0.
..01110.0.
..011110..
..01111...
..00000...
""", """
.0...0....
.00.00....
.01010....
.03130....
.01110....
..0110....
..01110...
..0111100.
..01111..0
..00000...
""", """
.0...0....
.00.00....
.01010....
.03130....
.01110....
..0110....
..01110...
..011110..
..0111100.
..00000.00
"""]
BUSH = """
..1101..
.131113.
11131311
13111131
.111311.
..1101..
"""

def windmill(c, x, y, t):
    """a round tower in 3/4 view: white wall with a door, conical thatch, four lattice sails"""
    c.rect(x + 4, y + 12, x + 24, y + 38, 2)                          # the tower front, in shade
    c.rect(x + 5, y + 13, x + 7, y + 37, 3)                           # its sunlit curve
    c.rect(x + 3, y + 12, x + 4, y + 38, 0); c.rect(x + 24, y + 12, x + 25, y + 38, 0); c.rect(x + 3, y + 37, x + 25, y + 38, 0)
    arch(c, x + 11, y + 28, 6, 9, 1)
    window(c, x + 12, y + 18)
    for yy in range(0, 14):                                          # the conical thatch
        hw = 2 + yy * 0.9
        for xx in range(int(-hw), int(hw) + 1):
            v = 0 if abs(xx) >= int(hw) or yy == 13 else (1 if (xx + yy) % 3 == 0 else 2)
            c.set(x + 14 + xx, y + yy, v)
    hx, hy = x + 14, y + 9
    a0 = (t // 12) * math.pi / 4                                     # 45 degrees every 12 frames
    for k in range(4):
        a = a0 + k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        for py in range(hy - 20, hy + 21):
            for px in range(hx - 20, hx + 21):
                u = (px - hx) * ca + (py - hy) * sa                  # along the blade
                v = -(px - hx) * sa + (py - hy) * ca                 # across it
                if 1.5 <= u <= 18 and -0.5 <= v <= 4.5:
                    edge = u > 17 or v < 0.5 or v > 3.5 or u < 3
                    lat = int(u) % 4 == 0
                    c.set(px, py, 0 if (edge or lat) else 3)
    c.rect(hx - 1, hy - 1, hx + 2, hy + 2, 0)

def chapel(c, x, y):
    dome(c, x + 21, y + 16, 11)
    house(c, x, y + 16, 36, 5, 22, door=True, windows=2)
    c.rect(x + 1, y + 4, x + 10, y + 17, 3); c.rect(x + 1, y + 4, x + 10, y + 5, 0)       # the bell wall
    c.rect(x + 1, y + 4, x + 2, y + 17, 0); c.rect(x + 9, y + 4, x + 10, y + 17, 0)
    c.rect(x + 4, y + 2, x + 7, y + 4, 3); c.rect(x + 4, y + 1, x + 7, y + 2, 0)
    arch(c, x + 3, y + 8, 2, 5, 0); arch(c, x + 6, y + 8, 2, 5, 0)
    c.set(x + 3, y + 11, 2); c.set(x + 7, y + 11, 2)

def pool(c, x0, y0, x1, y1, t):
    c.rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1, 3); c.rect(x0, y0, x1, y1, 2)
    c.rect(x0, y0, x1, y0 + 1, 1); c.rect(x0, y0, x0 + 1, y1, 1)
    for k in range(3):
        gx = x0 + 3 + ((k * 7 + (t // 12) * 5) % (x1 - x0 - 5)); gy = y0 + 2 + k * 2
        c.set(gx, gy, 3); c.set(gx + 1, gy, 3)

def dialog(c, t):
    y0 = 98
    c.rect(2, y0, W - 2, H - 2, 3)
    c.rect(2, y0, W - 2, y0 + 1, 0); c.rect(2, H - 3, W - 2, H - 2, 0)
    c.rect(2, y0, 3, H - 2, 0); c.rect(W - 3, y0, W - 2, H - 2, 0)
    c.rect(4, y0 + 2, W - 4, y0 + 3, 1); c.rect(4, H - 5, W - 4, H - 4, 1)
    c.rect(4, y0 + 2, 5, H - 4, 1); c.rect(W - 5, y0 + 2, W - 4, H - 4, 1)
    lines = ['THE CAT WATCHES THE SEA.', 'IT HAS SEEN A THOUSAND', 'SUNSETS FROM THIS WALL.']
    for i, s in enumerate(lines):
        pixfont.draw(c, s, 9, y0 + 7 + i * 11, 0)
    if (t // 12) % 2 == 0:
        pixfont.draw(c, '>', W - 16, H - 13, 0)

def frame(t):
    c = Canvas()
    sea(c, 0, 0, W, 11, t)
    c.rect(0, 11, W, 26, 3); c.rect(0, 11, W, 12, 0)                    # the cliff-top terrace
    for x in range(2, W, 6):
        c.rect(x, 12, x + 1, 15, 1)                                    # railing posts
    c.rect(0, 14, W, 15, 1)
    # gull over the water
    gx = int(W + 10 - t * (W + 20) / FRAMES) % (W + 20) - 10
    for dx, dy in ([(0, 1), (1, 0), (2, 1), (3, 1), (4, 0), (5, 1)] if (t // 4) % 2 else [(0, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 0)]):
        c.set(gx + dx, 6 + dy, 3)
    # the row of buildings facing the lane
    house(c, 28, 18, 26, 8, 24, windows=2)
    chapel(c, 56, 6)
    house(c, 94, 20, 28, 8, 22, windows=2)
    c.rect(96, 21, 120, 23, 2); c.rect(96, 23, 120, 25, 1)          # a barrel vault seen from above
    house(c, 124, 16, 36, 8, 26, windows=3)
    c.stamp(BUSH, 128, 40); c.stamp(BUSH, 136, 38)
    windmill(c, 0, 6, t)
    # the lane
    cobbles(c, 0, 50, W, 66)
    c.rect(0, 50, W, 51, 1)
    # the sea wall below the lane, the steps down, lower roofs, a pool, the sea
    wall(c, 0, 62, 66); wall(c, 82, W, 66)
    for i in range(6):                                            # steps going down
        c.rect(62, 66 + i * 4, 82, 68 + i * 4, 3); c.rect(62, 68 + i * 4, 82, 70 + i * 4, 2)
    c.rect(61, 66, 62, 96, 0); c.rect(82, 66, 83, 96, 0)
    c.rect(0, 73, 61, 96, 3)
    house(c, 2, 76, 28, 20, 4, door=False, windows=0)
    pool(c, 34, 78, 56, 90, t)
    for i in range(3):                                               # a barrel vault on the lower-left roof
        c.rect(4, 79 + i * 2, 28, 80 + i * 2, 2 if i % 2 else 1)
    for lx in (36, 46):                                              # loungers by the pool
        c.rect(lx, 92, lx + 7, 94, 1); c.rect(lx, 91, lx + 2, 92, 1)
    for px_ in (66, 72, 78):
        c.rect(px_, 62, px_ + 3, 65, 1); c.set(px_ + 1, 61, 2)
    c.rect(83, 73, W, 96, 3)
    house(c, 86, 76, 22, 20, 4, door=False, windows=0)
    dome(c, 97, 88, 7)
    sea(c, 112, 76, W, 96, t)
    c.rect(111, 76, 112, 96, 0)
    c.stamp(BUSH, 20, 60); c.stamp(BUSH, 100, 60)
    # the cat on the wall, the traveller on the lane
    c.stamp(CAT[[0, 1, 2, 1][(t // 8) % 4]], 44, 56)
    c.stamp(HERO[(t // 24) % 2], 66, 40, flip=True)
    dialog(c, t)
    rgb = np.stack(SHADES)[c.a]
    return Image.fromarray(rgb.astype(np.uint8), 'RGB')

def render_frames(frames=FRAMES):
    return [frame(t) for t in range(frames)]

def export():
    return [{'name': 'island_village', 'frames': [], 'images': [f.convert('RGBA') for f in render_frames()],
             'anchor': (0, 0), 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/village'
    for t in (0, 30):
        frame(t).resize((W * 5, H * 5), Image.NEAREST).save('%s-%02d.png' % (out, t))
