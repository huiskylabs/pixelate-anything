"""Canyon Cycle: the layout, as hand-placed polylines and boxes (native 320x180).

Everything that owns a region of the frame is defined here once, so the greyscale block-in and
the final index map share one layout. Points are placed by hand; the code only rasterises them.
"""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from canvas import Canvas

W, H = 320, 180
YY, XX = np.mgrid[0:H, 0:W]

# ---------------------------------------------------------------- near walls
# inner edge of the LEFT wall: (y, x) knots, piecewise constant between knots (ledged)
LEFT_EDGE = [(0, 107), (6, 105), (10, 102), (16, 99), (25, 97), (37, 96), (44, 99), (49, 98),
             (58, 96), (64, 94), (71, 95), (79, 92), (85, 89), (94, 91), (106, 93), (113, 96),
             (120, 98), (127, 98)]
# inner edge of the RIGHT wall
RIGHT_EDGE = [(0, 203), (5, 205), (9, 208), (16, 210), (27, 208), (38, 211), (46, 207), (55, 206),
              (61, 209), (69, 211), (77, 213), (104, 211), (111, 214), (119, 212), (128, 211)]
WALL_FOOT = 126          # rows below this belong to the pool, river and foreground banks


def edge_x(knots, y):
    """piecewise-constant edge with 1 px steps blended over 2 rows between knots"""
    x = knots[0][1]
    for ky, kx in knots:
        if y >= ky:
            x = kx
    return x


def left_wall():
    m = np.zeros((H, W), bool)
    for y in range(0, WALL_FOOT + 2):
        m[y, :edge_x(LEFT_EDGE, y)] = True
    return m


def right_wall():
    m = np.zeros((H, W), bool)
    for y in range(0, WALL_FOOT + 2):
        m[y, edge_x(RIGHT_EDGE, y):] = True
    return m


# ---------------------------------------------------------------- far plane
MESA = [(115, 97), (119, 92), (123, 86), (127, 79), (129, 76), (129, 70), (130, 66), (132, 63), (150, 63),
        (171, 62), (190, 62), (191, 65), (192, 70), (193, 76), (197, 81), (202, 87), (207, 93), (211, 97)]
BUTTE = [(99, 97), (102, 91), (104, 86), (107, 84), (115, 84), (117, 88), (120, 93), (122, 97)]
CLOUD = dict(cx=158, cy=30, rx=44, ry=16)

# ---------------------------------------------------------------- middle plane
# the hazed rock step at the gorge's far end: top edge knots (x, y)
STEP_TOP = [(96, 94), (103, 93), (109, 91), (116, 93), (124, 95), (131, 92), (139, 90), (147, 91),
            (155, 93), (163, 92), (170, 90), (175, 88), (189, 88), (193, 90), (200, 93), (207, 95), (214, 94)]
STEP_FOOT = 124

LEFT_FALL = dict(x0=66, x1=71, y0=22, y1=61)        # upper tier, x1 exclusive
LEFT_FALL2 = dict(x0=62, x1=71, y0=65, y1=124)      # lower tier, after the ledge splash
RIGHT_FALL = dict(x0=176, x1=188, y0=88, y1=124)

# ---------------------------------------------------------------- water and banks
POOL = [(44, 125), (60, 121), (100, 121), (140, 122), (180, 121), (214, 123), (226, 128), (214, 134),
        (186, 137), (150, 138), (110, 137), (70, 135), (52, 131)]
RIVER = [  # one closed outline: left bank down, bottom edge, right bank up
    (100, 134), (90, 138), (80, 143), (72, 149), (68, 155), (71, 161), (80, 167), (93, 173), (106, 180),
    (266, 180), (246, 174), (222, 168), (199, 163), (180, 158), (168, 153), (170, 148), (182, 143),
    (198, 138), (210, 134)]

# ---------------------------------------------------------------- hero group
DOOR = (220, 84, 238, 107)          # opening x0, y0, x1, y1 (exclusive)
FRAME = (215, 80, 243, 108)
LANDING = (196, 106, 253, 111)
CHIMNEY = (242, 46, 250, 84)
LANTERN = (196, 84, 201, 91)         # the glass box
HERO = (194, 74, 252, 112)

BRIDGE_L = (52, 82)                  # deck end on the left ledge
BRIDGE_R = (205, 104)                # deck end on the landing
BRIDGE_SAG = 11


def poly(pts):
    return Canvas(W, H).mask_poly(pts)


def step_mask():
    top = np.full(W, H)
    for (x0, y0), (x1, y1) in zip(STEP_TOP, STEP_TOP[1:]):
        for x in range(x0, x1 + 1):
            top[x] = int(round(y0 + (y1 - y0) * (x - x0) / max(1, x1 - x0)))
    m = (YY >= top[None, :]) & (YY < STEP_FOOT)
    m[:, :STEP_TOP[0][0]] = False
    m[:, STEP_TOP[-1][0] + 1:] = False
    return m


def fall_mask(f, flare=2):
    m = np.zeros((H, W), bool)
    for y in range(f['y0'], f['y1']):
        k = (y - f['y0']) / max(1, f['y1'] - f['y0'])
        grow = int(k * k * flare + 0.5)
        m[y, f['x0'] - grow:f['x1'] + grow] = True
    return m


def deck_y(x):
    (x0, y0), (x1, y1) = BRIDGE_L, BRIDGE_R
    t = (x - x0) / (x1 - x0)
    return y0 + (y1 - y0) * t + BRIDGE_SAG * 4 * t * (1 - t)
