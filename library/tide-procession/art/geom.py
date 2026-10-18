"""Tide Procession: the hand-placed layout shared by the block-in and the final art (native 640x360).

Every coordinate here is chosen by hand (no scatter): the island, the monastery, the causeway, the
pilgrims' places for each moment, the near-plane silhouettes, the moon, the cloud gap and the shaft.
"""
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[3] / 'tools'))
import math
import numpy as np

W, H = 640, 360
HORIZON = 206                     # sea meets sky

# ---------------------------------------------------------------- sky emitters
MOON = (468, 108, 22)             # cx, cy, r: low, behind the bell tower's west face
MOON_BOX = (446, 86, 490, 130)
GAP = (418, 34, 442, 62)          # the ragged break in the cloud bank, over the moon's west limb
# the shaft per moment: it breathes across the water between the two stills
SHAFT = {
    # from the break in the bank to the causeway round the leading pilgrims (the leading line)
    'a': dict(x=430, y=61, angle=102, length=185, width=(8, 38)),
    'b': dict(x=428, y=61, angle=106, length=182, width=(8, 34)),
}

# ---------------------------------------------------------------- the island and the monastery
# The west outline IS the stair flight (13 treads, rises 3 px, one 2 px and one 4 px: built
# irregular), so the steps read as silhouette against the sea; then the terrace, the tower, the long
# nave, the apse, and roofs stepping down to the right to a boathouse at the foot of the east cliff.
STEPS = [(414, 236), (419, 233), (424, 230), (429, 227), (435, 224), (440, 221), (446, 217),
         (451, 214), (457, 211), (462, 208), (467, 205), (472, 202), (476, 199)]
TERRACE_Y = 199
ROCK = ([(406, 240), (408, 237), (411, 236)] +
        [p for sx, sy in STEPS for p in ((sx, sy + 3 if (sx, sy) != STEPS[0] else 239), (sx, sy))][1:] +
        [(476, 199), (540, 199), (548, 196), (560, 194), (576, 193), (592, 193), (606, 195),
         (614, 199), (622, 205), (628, 210), (631, 216), (630, 222), (634, 229), (637, 235), (639, 240)])
WATERLINE = 239
TOWER = (474, 494)                # bell tower x range (21 px)
TOWER_TOP = 90                    # top of the belfry stage
CAP_TIP = (484, 72)               # low pyramidal cap tip
BELFRY = [(477, 96, 480, 110), (488, 96, 491, 110)]    # two arched openings (x0, y0, x1, y1 incl.)
NAVE = (494, 578, 158, 199)       # x0, x1, eave y, foot y
ROOF = [(491, 159), (500, 140), (572, 140), (581, 159)]
APSE = (578, 594, 164, 199)
APSE_ROOF = [(576, 165), (586, 152), (597, 165)]
DORM = [(594, 206), (594, 175), (623, 184), (623, 206)]                     # lean-to roof
HOUSE = [(612, 217), (612, 203), (621, 196), (630, 203), (630, 217)]
BOATHOUSE = [(610, 240), (610, 228), (619, 222), (630, 228), (630, 240)]
PORTAL = (500, 513, 165, 199)     # x0, x1 (incl.), arch top y, threshold y
ISLAND_TREE = (633, 212)          # root of the small bent tree on the east shoulder

# ---------------------------------------------------------------- the causeway
CAUSEWAY = [(22, 271), (70, 268), (120, 265), (165, 262), (200, 260), (245, 256), (290, 251),
            (330, 247), (372, 243), (418, 238)]


def road_y(x):
    """the causeway's top surface row at column x"""
    pts = CAUSEWAY
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return int(round(y0 + (y1 - y0) * (x - x0) / (x1 - x0)))
    return pts[-1][1]


def road_th(x):
    """(top, face) thickness at column x: nearer (left) is thicker"""
    u = (x - 22) / (418 - 22)
    return (3 if u < 0.55 else 2), (5 if u < 0.3 else 4 if u < 0.75 else 3)


def step_y(x):
    """the stair tread row under column x (the flight's walking surface): the feet stand on the
    tread, so the walker's anchor row is the row just above it"""
    y = WATERLINE - 3
    for sx, sy in STEPS:
        if x >= sx:
            y = sy
    return y - 1


# ---------------------------------------------------------------- pilgrims per moment
# (feet x, height, kind, walk drawing, surface) -- gaps 23 41 19 54 31 27 46 38: pairs, a trio,
# two stragglers; kinds: 'staff' tall with staff, 'pack' bedroll and a lantern pole,
# 'elder' stooped with staff, 'high' lantern raised
PILGRIMS = {
    # A: the leader pulls ahead at the island end; a tight pair; one; a loose trio; a wide gap; one;
    # a straggler far behind. (feet x, height, kind, walk drawing[, 'tall' staff])
    'a': [(410, 31, 'staff', 0), (358, 33, 'pack', 2), (347, 29, 'elder', 1), (309, 32, 'high', 3),
          (281, 30, 'staff', 2, 'tall'), (262, 34, 'pack', 0), (244, 31, 'staff', 1), (190, 30, 'high', 3),
          (124, 32, 'elder', 0)],
    # B: the first at the door, two on the flight, one at the landing, the rest strung out on the road
    'b': [(505, 31, 'staff', 4), (466, 33, 'pack', 0), (443, 29, 'elder', 2), (409, 32, 'high', 1),
          (360, 30, 'staff', 3, 'tall'), (338, 34, 'pack', 0), (300, 31, 'staff', 2), (251, 30, 'high', 1),
          (214, 32, 'elder', 3)],
}


def feet_y(x, moment):
    if moment == 'b' and x >= 414:
        return TERRACE_Y - 1 if x >= 476 else step_y(x)
    return road_y(x)


# ---------------------------------------------------------------- near plane
BANK = [(0, 300), (14, 296), (30, 299), (46, 304), (62, 311), (80, 318), (104, 324), (128, 327),
        (150, 331), (176, 333), (204, 331), (232, 335), (262, 338), (296, 339), (330, 337),
        (366, 340), (398, 341), (430, 338), (458, 333), (482, 327), (506, 323), (532, 321),
        (556, 323), (584, 326), (610, 322), (628, 318), (640, 317)]
PINE_ROOT = (30, 302)
BOAT = (168, 312, 252, 334)       # bbox of the beached boat
POSTS = [(497, 286, 4), (523, 300, 3), (552, 280, 5), (589, 307, 3)]   # (x, top y, width)

# ---------------------------------------------------------------- the flats (low tide)
# shallow pools along the road front and out on the sand: (x0, x1, y0, y1), mismatched
POOLS = [(18, 104, 281, 291), (96, 236, 276, 289), (226, 352, 266, 282), (344, 420, 256, 270),
         (60, 150, 299, 306), (262, 470, 291, 303), (420, 640, 246, 266), (468, 560, 274, 281),
         (150, 214, 312, 318)]


_C = None


def _canvas():
    global _C
    if _C is None:
        from canvas import Canvas
        _C = Canvas(W, H)
    return _C


def mask_poly(pts):
    """bool mask of the pixels whose centres fall inside the polygon (the kit's Canvas.mask_poly)"""
    return _canvas().mask_poly(pts)


def disc(cx, cy, r):
    """bool mask of a disc (the kit's Canvas.disc rule)"""
    rr = r + 0.15
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= rr ** 2


def island_mask():
    m = mask_poly(ROCK + [(640, 241), (406, 241)])
    for poly in (ROOF, DORM, HOUSE, BOATHOUSE, APSE_ROOF):
        m |= mask_poly(poly)
    x0, x1, ey, fy = NAVE
    m[ey:fy + 1, x0:x1 + 1] = True
    ax0, ax1, ay, afy = APSE
    m[ay:afy + 1, ax0:ax1 + 1] = True
    t0, t1 = TOWER
    m[TOWER_TOP:TERRACE_Y + 1, t0:t1 + 1] = True
    m |= mask_poly([(t0 - 2, TOWER_TOP), (CAP_TIP[0], CAP_TIP[1]), (t1 + 3, TOWER_TOP)])
    return m
