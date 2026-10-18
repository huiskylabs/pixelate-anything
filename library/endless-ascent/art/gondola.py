"""The hero both stills share: the climbing gondola, its passenger, the lantern and the cable.

Slot names are shared across the two palettes (A dusk, B night), so the same drawing serves both:
  wood0-4 timber, iron0-3 fittings, cab0-3 the cable, coat0-3 the passenger's hooded coat,
  scarf0-2 the muffler, skin0-2 face and hand, gw0-3 lantern-lit timber, lamp0-3 the lantern itself.
"""
import math
import numpy as np
from common import W, H, put, stamp, hsh
import geometry as G

GX0, GY0 = 114, 200          # the gondola sprite's top-left on screen (hero bbox origin)

KEY = {
    'o': 'wood0', 'd': 'wood1', 'm': 'wood2', 'l': 'wood3', 'L': 'wood4',
    'i': 'iron0', 'I': 'iron1', 'j': 'iron2', 'J': 'iron3',
    '1': 'gw0', '2': 'gw1', '3': 'gw2', '4': 'gw3',
    '5': 'lamp0', '6': 'lamp1', '7': 'lamp2', '8': 'lamp3',
    'c': 'coat0', 'C': 'coat1', 'v': 'coat2', 'V': 'coat3',
    's': 'scarf0', 'S': 'scarf1', 'z': 'scarf2',
    'f': 'skin0', 'F': 'skin1', 'g': 'skin2',
    'q': 'cab0', 'Q': 'cab1', 'w': 'cab2', 'W': 'cab3',
}


def cable_x(y):
    """the cable's left column at row y: a long slack S through the gondola's grip"""
    return G.CABLE_X + int(round(2.6 * math.sin((y - 240) * math.pi / 330) + 0.8 * math.sin((y - 240) * math.pi / 97)))


def draw_cable(g, y0=0, y1=H, skip=None):
    """the cable as a chain rope: nodes 3 px apart along the S, 2 px wide, a lay twist every 3 px
    (a lit fleck that steps across the rope), its right side in the darkest step. skip(y) -> True leaves a row out."""
    for y in range(y0, y1):
        if skip is not None and skip(y):
            continue
        # node positions every 3 px, rows in between follow the segment (a chain, not a ruler)
        n0 = (y // 3) * 3
        xa, xb = cable_x(n0), cable_x(n0 + 3)
        x = xa if (y - n0) < 2 else xb
        ph = y % 3
        left = 'cab2' if ph == 0 else ('cab1' if ph == 1 else 'cab1')
        right = 'cab0' if ph != 1 else 'cab1'
        if ph == 0:
            left, right = 'cab2', 'cab0'
        elif ph == 1:
            left, right = 'cab1', 'cab2'
        else:
            left, right = 'cab1', 'cab0'
        put(g, x, y, left)
        put(g, x + 1, y, right)


# ------------------------------------------------------------------ slot maps (hand-typed)
# the grip: an iron shoe with a pulley wheel riding the cable, bolted to the roof ridge
GRIP = """
...iiiii...
..iIjJjIi..
.iIjiiijIi.
.ijiIJIijI.
.iJiJiJiJi.
.ijiIJIiji.
.iIjiiijIi.
..iIjjjIi..
...iiiii...
"""

# the passenger, facing right toward the lantern: round hood, lit face, muffler tail, arm out
PASSENGER = """
....ccccc.......
..ccCCCCCcc.....
.cCCvvvvvCCc....
.cCvvVVVVvCc....
cCvvVcccccVc....
cCvVcfFggg2.....
cCvVcfFcgg3.....
cCvVcffggFc.....
.cCvcsSSSzzs....
.cCsSSSzzSSzzs..
cCCvsSzzSScsSs..
cCvvVcVVVV22gg..
cCvvVcVVVcc232..
cCvvvVcvVVc.....
cCvvvVcvvVc.....
cCvvvVcvvVc.....
cCvvvVccvVc.....
cCvvvVcvvVc.....
"""

# the lantern on its crook: iron cap and ring, glass, flame, base; the halo is the lamp0 ring
LANTERN = """
...jj....
..j..j...
...ii....
..iJJi...
.i6776i..
.5788765.
.578876.5
.5677765.
.i6776i..
..iJJi...
...ii....
"""


def roof(g, x0, y0, w):
    """the peaked roof: two shingle courses with a sag-free ridge, eaves 2 px past the posts,
    one patched lighter shingle; the underside eave a dark row; lantern side lit warm"""
    cx = x0 + w // 2
    rows = 8
    for r in range(rows):
        half = 4 + int(round((w // 2 - 4) * (r + 1) / rows))
        y = y0 + r
        for x in range(cx - half, cx + half + 1):
            edge = x in (cx - half, cx + half) or r == 0
            if edge:
                v = 'wood0'
            else:
                # shingle courses: rows 1-3 course A, 4-6 course B, offset joints
                course = 0 if r < 4 else 1
                joint = ((x - cx + (3 if course else 0)) % 6 == 0)
                lip = r in (3, 6)
                if lip:
                    v = 'wood1'
                elif joint:
                    v = 'wood1'
                else:
                    # light from the upper left: the left slope lighter
                    v = 'wood3' if x < cx else 'wood2'
                    if r in (1, 4) and x < cx:
                        v = 'wood4' if (x - cx) % 6 not in (1, 2) else 'wood3'
            put(g, x, y, v)
    # the patched shingle: a newer board, a step lighter, on the right slope
    for x in range(cx + 7, cx + 11):
        for y in (y0 + 4, y0 + 5):
            put(g, x, y, 'wood3')
    put(g, cx + 7, y0 + 4, 'wood4')
    # eave underside
    for x in range(cx - (w // 2) + 1, cx + (w // 2)):
        put(g, x, y0 + rows, 'wood0')


def gondola(g, lit=True):
    """the whole hero onto grid g at its fixed screen spot"""
    X, Y = GX0, GY0
    cab_l, cab_r = X + 5, X + 36           # cabin outer x range (inclusive)
    roof_y = Y + 9
    body_y0, body_y1 = roof_y + 9, Y + 60  # cabin from under the eave to the keel
    # back wall seen through the open upper half
    for y in range(body_y0, body_y0 + 21):
        for x in range(cab_l + 1, cab_r):
            put(g, x, y, 'wood0')
    # back wall boards: faint vertical seams at uneven spacing
    for x in (cab_l + 4, cab_l + 9, cab_l + 13, cab_l + 20, cab_l + 24, cab_l + 29):
        for y in range(body_y0 + 2, body_y0 + 21):
            put(g, x, y, 'wood1')
    # the cable inside the cabin (behind the passenger)
    draw_cable(g, body_y0, body_y0 + 21)
    # passenger
    stamp(g, PASSENGER, KEY, X + 17, body_y0 + 3)
    # corner posts (front two), 2 px each with a lit left face
    for x, lit_side in ((cab_l, 'wood3'), (cab_r - 1, 'wood2')):
        for y in range(body_y0, body_y1):
            put(g, x, y, 'wood0')
            put(g, x + 1, y, lit_side)
    # right post faces the lantern: warm steps on its right column
    for y in range(body_y0, body_y0 + 22):
        put(g, cab_r, y, 'wood3')
    # waist rail
    for x in range(cab_l, cab_r + 1):
        put(g, x, body_y0 + 21, 'wood4')
        put(g, x, body_y0 + 22, 'wood2')
        put(g, x, body_y0 + 23, 'wood0')
    # lower half: vertical planks with seams, lit warm toward the lantern side
    py0, py1 = body_y0 + 24, body_y1 - 4
    for y in range(py0, py1):
        for x in range(cab_l, cab_r + 1):
            if x in (cab_l, cab_r):
                v = 'wood0'
            elif (x - cab_l) % 5 == 0:
                v = 'wood0'
            else:
                v = 'wood2' if (x - cab_l) % 5 != 1 else 'wood3'
            put(g, x, y, v)
    # a knot and a short board (the odd plank)
    put(g, cab_l + 8, py0 + 5, 'wood1')
    put(g, cab_l + 9, py0 + 5, 'wood1')
    for x in range(cab_l + 16, cab_l + 19):
        put(g, x, py0 + 9, 'wood0')
    # keel beam with iron straps
    for y in range(py1, body_y1):
        for x in range(cab_l - 1, cab_r + 2):
            v = 'wood1' if y > py1 else 'wood3'
            if y == body_y1 - 1 or x in (cab_l - 1, cab_r + 1):
                v = 'wood0'
            put(g, x, y, v)
    for sx in (cab_l + 2, cab_r - 3):          # two iron corner brackets on the keel
        put(g, sx, py1 - 1, 'iron1'); put(g, sx + 1, py1 - 1, 'iron1')
        put(g, sx, py1 - 2, 'iron2')
    # the roof and the grip on its ridge
    roof(g, cab_l - 4, roof_y, (cab_r - cab_l) + 9)
    cx = cable_x(Y + 4)
    stamp(g, GRIP, KEY, cx - 4, Y + 1)
    # the cable above the grip and below the keel is drawn by the scene; the bottom bob
    for y in range(body_y1, body_y1 + 3):
        put(g, cable_x(y), y, 'iron1'); put(g, cable_x(y) + 1, y, 'iron0')
    # the crook pole from the passenger's hand out past the right post, the lantern hanging from it
    hx, hy = X + 30, body_y0 + 15
    for x in range(hx, hx + 12):
        put(g, x, hy - (1 if x > hx + 8 else 0), 'wood1')
        put(g, x, hy + 1 - (1 if x > hx + 8 else 0), 'wood0')
    put(g, hx + 12, hy - 1, 'wood1'); put(g, hx + 12, hy, 'wood1')
    lx, ly = hx + 8, hy + 1
    before = g.copy()
    stamp(g, LANTERN, KEY, lx, ly)
    lm = np.zeros(g.shape, bool)
    lm[ly + 3:ly + 10, lx:lx + 9] = True
    lm &= np.array([[isinstance(v, str) and v.startswith(('lamp', 'iron')) for v in row] for row in g])
    ring = np.zeros(g.shape, bool)
    ring[1:] |= lm[:-1]; ring[:-1] |= lm[1:]; ring[:, 1:] |= lm[:, :-1]; ring[:, :-1] |= lm[:, 1:]
    ring &= ~lm
    for (y, x) in zip(*np.nonzero(ring)):
        v = g[y, x]
        if not (isinstance(v, str) and v.startswith(('wood', 'coat', 'skin', 'scarf', 'gw', 'cab'))):
            g[y, x] = 'gw1'                     # a 1 px halo ring where the lantern meets the air
    lantern_light(g, lx + 4, ly + 6, X, Y, X + 50, Y + 66,
                  planks=(cab_l, cab_r, py0, py1), rail=(cab_l, cab_r, body_y0 + 21), post=(cab_r - 1, cab_r, body_y0, body_y1))
    return (X, Y)


# the lantern's pool in palette steps: timber facing the lantern climbs the gw ramp by distance
WARM = [  # (max distance, {slot: lit slot})
    (9.5, {'wood4': 'gw3', 'wood3': 'gw3', 'wood2': 'gw2', 'wood1': 'gw1', 'iron2': 'gw1', 'iron3': 'gw2', 'iron1': 'gw0'}),
    (16.0, {'wood4': 'gw2', 'wood3': 'gw2', 'wood2': 'gw1', 'wood1': 'gw0', 'iron3': 'gw1', 'iron2': 'gw0'}),
    (23.0, {'wood4': 'gw1', 'wood3': 'gw1', 'wood2': 'gw1', 'wood1': 'gw0'}),
    (31.0, {'wood4': 'gw0', 'wood3': 'gw0', 'wood2': 'gw0'}),
]


def lantern_light(g, cx, cy, x0, y0, x1, y1, planks=None, rail=None, post=None):
    """steps follow the objects: a whole plank (top part and bottom part) takes one step, the rail
    and the post step in segments, so the pool reads as light on boards, not a circle cut through them"""
    def snapped(x, y):
        if planks:
            pl, pr, p0, p1 = planks
            if pl <= x <= pr and p0 <= y < p1:
                k = (x - pl) // 5
                sx = pl + 5 * k + 2
                split = p0 + 4 + max(0, 8 - k)          # nearer planks stay lit further down
                return sx, (p0 + 1 if y < split else y + 3)
        if rail:
            rl, rr, ry = rail
            if rl <= x <= rr and ry <= y <= ry + 2:
                return rl + 4 * ((x - rl) // 4) + 2, ry
        if post:
            a, b, q0, q1 = post
            if a <= x <= b and q0 <= y < q1:
                return x, q0 + 4 * ((y - q0) // 4) + 2
        return x, y
    for y in range(max(0, y0), min(H, y1)):
        for x in range(max(0, x0), min(W, x1)):
            v = g[y, x]
            if not isinstance(v, str):
                continue
            sx, sy = snapped(x, y)
            d = ((sx - cx) ** 2 + ((sy - cy) * 1.15) ** 2) ** 0.5
            if x < cx - 26:
                continue
            for (r, m) in WARM:
                if d <= r:
                    if v in m:
                        g[y, x] = m[v]
                    break
            # a warm rim on the passenger's coat where it faces the lantern
            if v.startswith('coat') and d < 15 and x + 1 < W:
                nv = g[y, x + 1]
                if not (isinstance(nv, str) and nv.startswith(('coat', 'skin', 'scarf'))):
                    g[y, x] = 'gw1' if d < 10 else 'gw0'

