"""The dredger boss as part sprites with pivots: body (hull, deck, gantry), cabin, exhaust stack,
jaw (the bucket ladder), three hanging bucket links, two piston legs. Each part is drawn by code
on its own transparent canvas at its pose (pivot in frame px, angle), outlined in its materials'
own darkest steps with a lit arc up-left, and returned as a Part (canvas, pivot, anchors). The
pose dicts at the bottom place the same parts for image A and image B."""
import sys, math
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from canvas import Canvas
import morph

W, H = 304, 224
LIGHT = (-1, -1)          # toward the light: up-left

def _h(a, b=0, s=0):
    h = (int(a) * 374761393 + int(b) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

class Part:
    def __init__(self, name, pivot):
        self.name = name
        self.c = Canvas(W, H, None)
        self.pivot = (int(pivot[0]), int(pivot[1]))
        self.anchors = {}
    def mask(self):
        return ~np.equal(self.c.g, None)
    def finish(self, lift=0.3):
        m = self.mask()
        self.c.outline(m, mode='own', light=LIGHT, lift=lift)
        return self

def rot(u, v, ang):
    """local (u along, v across) -> frame offset for a direction at `ang` degrees (y down)"""
    a = math.radians(ang)
    return (u * math.cos(a) - v * math.sin(a), u * math.sin(a) + v * math.cos(a))

def quad(px, py, ang, u0, u1, v0, v1):
    """the 4 frame corners of the local box [u0,u1] x [v0,v1] at pivot (px, py), angle ang"""
    pts = []
    for (u, v) in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
        dx, dy = rot(u, v, ang)
        pts.append((px + dx, py + dy))
    return pts

def local_uv(px, py, ang):
    """(u, v) arrays of every frame pixel centre in the frame of (px, py, ang)"""
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    a = math.radians(ang)
    dx, dy = xx - px, yy - py
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)

def strut(c, p0, p1, w, bands, clip=None):
    """a straight cylinder from p0 to p1, `w` px across, shaded across its width only:
    bands = [(s_max, slot), ...] with s from -1 (the side facing the light) to 1. Returns the mask."""
    (x0, y0), (x1, y1) = p0, p1
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    Ln = math.hypot(x1 - x0, y1 - y0)
    u, v = local_uv(x0, y0, ang)
    m = (u >= 0) & (u <= Ln) & (np.abs(v) <= w / 2.0)
    if clip is not None:
        m &= clip
    # which side of the strut faces the light: the normal (−sin, cos) dotted with LIGHT
    n = (-math.sin(math.radians(ang)), math.cos(math.radians(ang)))
    sgn = -1 if (n[0] * LIGHT[0] + n[1] * LIGHT[1]) > 0 else 1
    s = sgn * v / (w / 2.0)
    out = np.full(m.shape, None, object)
    prev = -9
    for smax, slot in bands:
        sel = m & (s > prev) & (s <= smax)
        out[sel] = slot
        prev = smax
    c.g[m] = out[m]
    return m

def rivets(c, pts, lit='rust5', dark='rust1', skip=()):
    for i, (x, y) in enumerate(pts):
        if i in skip:
            continue
        c.put(x, y, lit)
        c.put(x + 1, y + 1, dark)

# ---------------------------------------------------------------- body: hull, deck, gantry
def body(ox, oy, wet_line=None):
    """hull deck-left corner at (ox, oy). Anchors: cabin, stack, jaw (gantry tumbler), hips."""
    P = Part('body', (ox, oy))
    c = P.c
    X = lambda x: ox + x
    Y = lambda y: oy + y
    # hull silhouette (local): deck 0..140 at y 0; raked bow to 154; stern counter
    hull = [(X(0), Y(0)), (X(140), Y(0)), (X(153), Y(12)), (X(151), Y(16)), (X(148), Y(58)),
            (X(2), Y(58)), (X(-3), Y(14)), (X(-1), Y(4))]
    m = c.mask_poly(hull)
    # strakes of uneven height: 0-3 gunwale, 4-14, 15-23, rub rail 24-26, 27-38, 39-58
    strakes = [(4, 14), (15, 23), (27, 38), (39, 58)]
    yy, xx = np.mgrid[0:H, 0:W]
    c.g[m] = 'rust1'
    base_k = [2, 2, 1, 1]                       # a dark heavy mass; light only on what protrudes
    for k, (a, b) in enumerate(strakes):
        x = -4 + int(_h(k, 2, 5) * 9)
        j = 0
        while x < 156:
            w = 14 + int(_h(j, k, 6) * 17)
            xr = x + w
            tone = base_k[k] - (1 if x > 108 else 0) + (1 if x < 22 and k < 2 else 0)
            r = _h(j, k, 7)
            tone += (1 if r < 0.12 else -1 if r > 0.86 else 0)          # a mismatched plate
            tone = max(0, min(3, tone))
            sel = m & (yy >= Y(a)) & (yy <= Y(b)) & (xx >= X(x)) & (xx < X(xr))
            c.g[sel] = 'rust%d' % tone
            c.g[sel & (yy == Y(b))] = 'rust0'                              # the seam row
            c.g[sel & (xx == X(xr) - 1)] = 'rust0'                         # the seam column
            c.g[sel & (xx == X(xr) - 2) & (yy < Y(b))] = 'rust%d' % max(0, tone - 1)
            c.put(X(x), Y(a), 'rust%d' % min(5, tone + 2))                 # lit plate corner
            c.put(X(x) + 1, Y(a), 'rust%d' % min(5, tone + 1))
            c.put(X(x), Y(a) + 1, 'rust%d' % min(5, tone + 1))
            # rivets in pairs down the seam (lit dot over a dark one), spacing 3-6, gaps
            if not (k == 2 and 40 < x < 80):
                ry = a + 2
                while ry < b - 1:
                    if m[Y(ry), X(xr) - 3] and _h(ry, j, 9) < 0.8:
                        c.put(X(xr) - 3, Y(ry), 'rust%d' % min(5, tone + 2))
                        c.put(X(xr) - 3, Y(ry) + 1, 'rust0')
                    ry += 3 + int(_h(ry, k, 8) * 4)
            x = xr
            j += 1
    # big rust blooms and wet streaks over the plates (shapes, not noise)
    for i in range(9):
        sx = 8 + int(_h(i, 3, 12) * 130)
        sy = 5 + int(_h(i, 4, 12) * 20)
        ln = 5 + int(_h(i, 5, 12) * 14)
        for kk in range(ln):
            y_ = Y(sy + kk)
            if y_ < H and m[y_, X(sx)]:
                c.put(X(sx), y_, 'rust3' if kk < ln // 3 else 'rust0')
                if kk < 3:
                    c.put(X(sx) + 1, y_, 'rust3')
    # rub rail: a protruding beam with a lit top and a dark shadow under it
    c.g[m & (yy == Y(24))] = 'rust5'
    c.g[m & (yy == Y(25))] = 'rust3'
    c.g[m & (yy == Y(26))] = 'rust0'
    c.g[m & (yy == Y(25)) & (xx > X(110))] = 'rust2'
    # gunwale: lit lip, shadow under it
    c.g[m & (yy == Y(0))] = 'rust5'
    c.g[m & (yy == Y(1))] = 'rust4'
    c.g[m & (yy == Y(2))] = 'rust3'
    c.g[m & (yy == Y(3))] = 'rust0'
    # bow: the raked face turns away from the light
    bow = m & (xx >= X(141) + (yy - Y(0)) * 0.95) & (yy <= Y(14))
    bow |= m & (xx >= X(146))
    c.g[bow] = 'rust1'
    c.g[bow & (xx >= X(149))] = 'rust0'
    c.g[m & (yy == Y(0)) & bow] = 'rust3'
    # stern counter: the rounded left end catches the light
    c.g[m & (xx <= X(1)) & (yy > Y(3))] = 'rust4'
    # rivet runs under the gunwale, uneven spacing
    x = 4
    while x < 140:
        c.put(X(x), Y(5), 'rust5'); c.put(X(x), Y(6), 'rust1')
        x += 4 + int(_h(x, 2, 9) * 4)
    # a patch plate (10x7) one step lighter with its own rivets
    c.rect(X(92), Y(16), X(102), Y(23), 'rust4')
    c.rect(X(92), Y(22), X(102), Y(23), 'rust2')
    c.rect(X(101), Y(16), X(102), Y(23), 'rust2')
    for (rx, ry) in ((93, 17), (100, 17), (93, 21), (99, 21)):
        c.put(X(rx), Y(ry), 'rust5')
    # moss in the lower seams and along the waterline (olive, two steps below the rust)
    for k, (a, b) in enumerate(strakes[1:], 1):
        for x in range(0, 148):
            if _h(x // 3, k, 13) < 0.42 and m[Y(b), X(x)]:
                c.put(X(x), Y(b), 'moss1' if _h(x, k, 14) < 0.6 else 'moss0')
                if _h(x, k, 15) < 0.35:
                    c.put(X(x), Y(b) - 1, 'moss2' if k < 3 else 'moss1')
                if _h(x, k, 16) < 0.25 and m[Y(b) + 1, X(x)]:
                    c.put(X(x), Y(b) + 1, 'moss0')
    if wet_line is not None:                       # moss band where the water was
        for x in range(0, 150):
            for y in range(wet_line - 2, wet_line + 1):
                yy_ = Y(y)
                if 0 <= yy_ < H and m[yy_, X(x)] and _h(x // 2, y, 17) < 0.55:
                    c.put(X(x), yy_, 'moss0' if _h(x, y, 18) < 0.5 else 'moss1')
    # hawse pipe and a stub of anchor chain at the bow
    c.disc(X(136), Y(9), 2.2, 'iron0'); c.put(X(135), Y(8), 'iron1')
    for k in range(6):
        c.put(X(137) + (k % 2), Y(12) + k, 'iron2' if k % 2 else 'iron1')
    # deck rail: posts at uneven spacing, a top rail broken in one place
    x = 2
    posts = []
    while x < 136:
        posts.append(x)
        x += 6 + int(_h(x, 1, 19) * 4)
    for px in posts:
        if 24 <= px <= 60:             # the cabin stands there
            continue
        for k in range(1, 6):
            c.put(X(px), Y(-k), 'iron2')
        c.put(X(px), Y(-6), 'iron3')
    for x in range(0, 138):
        if 24 <= x <= 60 or 100 <= x <= 107:
            continue
        c.put(X(x), Y(-6), 'iron3' if x % 7 else 'iron4')
    c.put(X(99), Y(-5), 'iron3'); c.put(X(108), Y(-7), 'iron3')       # the broken ends bent
    # a winch drum on the deck between cabin and gantry
    c.rect(X(70), Y(-8), X(84), Y(0), 'iron2')
    c.rect(X(70), Y(-8), X(84), Y(-7), 'iron4')
    c.rect(X(70), Y(-6), X(84), Y(-5), 'iron3')
    c.rect(X(70), Y(-2), X(84), Y(-1), 'iron1')
    c.rect(X(68), Y(-9), X(70), Y(0), 'iron1'); c.rect(X(84), Y(-9), X(86), Y(0), 'iron1')
    # gantry: an A-frame of channel girders from the deck to the tumbler housing
    top = (X(112), Y(-74))
    gb = [(X(92), Y(0)), (X(108), Y(-70))]          # back leg
    gf = [(X(134), Y(0)), (X(118), Y(-70))]         # front leg
    gird = [(-0.55, 'iron4'), (-0.1, 'iron3'), (0.45, 'iron2'), (1.0, 'iron1')]
    # cross-braces behind the legs
    for (yb, th) in ((-22, 3), (-46, 2)):
        xa = X(92) + (X(108) - X(92)) * (-yb) / 70.0
        xb = X(134) + (X(118) - X(134)) * (-yb) / 70.0
        c.rect(int(xa), Y(yb), int(xb) + 1, Y(yb) + th, 'iron2')
        c.rect(int(xa), Y(yb), int(xb) + 1, Y(yb) + 1, 'iron3')
        c.line(int(xa) + 2, Y(yb) + th, int(xb) - 2, Y(yb) + th + 18 if yb == -46 else Y(yb) + th + 12, 'iron1')
    strut(c, gb[0], gb[1], 7, gird)
    strut(c, gf[0], gf[1], 7, gird)
    for (p0, p1) in (gb, gf):                       # rivet lines along the girders
        for k in range(4, 68, 5 + int(_h(p0[0], 3, 20) * 2)):
            t = k / 70.0
            rx = p0[0] + (p1[0] - p0[0]) * t
            ry = p0[1] + (p1[1] - p0[1]) * t
            c.put(rx - 1, ry, 'iron4')
    # tumbler housing: a riveted block at the top
    hx0, hy0 = X(100), Y(-80)
    c.rect(hx0, hy0, hx0 + 26, hy0 + 12, 'rust2')
    c.rect(hx0, hy0, hx0 + 26, hy0 + 2, 'rust4')
    c.rect(hx0, hy0 + 2, hx0 + 2, hy0 + 12, 'rust3')
    c.rect(hx0 + 24, hy0 + 2, hx0 + 26, hy0 + 12, 'rust1')
    c.rect(hx0, hy0 + 11, hx0 + 26, hy0 + 12, 'rust1')
    for rx in (3, 8, 14, 21):
        c.put(hx0 + rx, hy0 + 4, 'rust5'); c.put(hx0 + rx, hy0 + 5, 'rust1')
    # moss on the deck edge and in the gantry foot
    for x in range(88, 100):
        if _h(x, 7, 21) < 0.6:
            c.put(X(x), Y(-1), 'moss1')
    P.anchors = {'cabin': (X(26), Y(0)), 'stack': (X(14), Y(0)), 'jaw': (X(112), Y(-74)),
                 'hip_r': (X(18), Y(34)), 'hip_f': (X(128), Y(36)), 'cable': (X(124), Y(-77))}
    P.finish()
    # snapped cable from the housing: a hanging catenary, 1 px, frayed end (after the outline)
    cx, cy = P.anchors['cable']
    c.catenary(cx, cy, cx + 9, cy + 20, 6, 'iron1')
    c.put(cx + 9, cy + 21, 'iron3'); c.put(cx + 10, cy + 21, 'iron1')
    return P

# ---------------------------------------------------------------- cabin
def cabin(bx, by, glare=False):
    """wheelhouse standing on the deck with its base-left corner at (bx, by): 50 x 40, roof lip,
    four windows (the third lit and cracked), a door, a ladder."""
    P = Part('cabin', (bx, by))
    c = P.c
    x0, y0, x1, y1 = bx, by - 40, bx + 50, by
    c.rect(x0, y0, x1, y1, 'rust2')
    c.rect(x0, y0, x0 + 3, y1, 'rust3')                 # lit left corner post
    c.put(x0, y0, 'rust4')
    c.rect(x0, y0, x0 + 1, y1, 'rust4')
    c.rect(x1 - 4, y0, x1, y1, 'rust1')                 # shadow side
    c.rect(x1 - 1, y0, x1, y1, 'rust0')
    # panels: a horizontal seam with rivets, uneven vertical seams
    c.rect(x0, y0 + 20, x1, y0 + 21, 'rust0')
    c.rect(x0 + 3, y0 + 21, x1 - 4, y0 + 22, 'rust3')
    for sx in (13, 31, 40):
        c.rect(x0 + sx, y0 + 21, x0 + sx + 1, y1, 'rust1')
    for rx in (5, 9, 16, 22, 27, 35, 43):
        c.put(x0 + rx, y0 + 23, 'rust4'); c.put(x0 + rx, y0 + 24, 'rust0')
    # roof: overhanging lip, lit top, shadow row under
    c.rect(x0 - 3, y0 - 4, x1 + 3, y0, 'rust3')
    c.rect(x0 - 3, y0 - 4, x1 + 3, y0 - 3, 'rust5')
    c.rect(x0 - 3, y0 - 3, x1 + 3, y0 - 2, 'rust4')
    c.rect(x0, y0, x1, y0 + 1, 'rust1')
    c.rect(x1, y0 - 2, x1 + 3, y0, 'rust1')
    # a vent cowl and a mast stub on the roof
    c.rect(x0 + 8, y0 - 9, x0 + 13, y0 - 4, 'rust2')
    c.rect(x0 + 8, y0 - 9, x0 + 10, y0 - 4, 'rust4')
    c.rect(x0 + 7, y0 - 11, x0 + 15, y0 - 9, 'rust3')
    c.rect(x0 + 7, y0 - 11, x0 + 15, y0 - 10, 'rust5')
    for k in range(4, 15):
        c.put(x0 + 38, y0 - k, 'rust3'); c.put(x0 + 39, y0 - k, 'rust1')
    c.rect(x0 + 35, y0 - 13, x0 + 43, y0 - 12, 'rust4')
    # windows: y 9..16 (8 rows), four panes; the third is lit and cracked
    wy0, wy1 = y0 + 9, y0 + 16
    panes = [(5, 12), (16, 23), (27, 36), (39, 45)]
    for i, (a, b) in enumerate(panes):
        c.rect(x0 + a - 1, wy0 - 1, x0 + b + 1, wy1 + 1, 'iron0')            # frame
        if i == 2:
            continue
        c.rect(x0 + a, wy0, x0 + b, wy1, 'dglass0')
        c.rect(x0 + a, wy0, x0 + b, wy0 + 1, 'dglass1')                        # sky glint on top
        c.put(x0 + a, wy0 + 1, 'dglass1')
    # pane 2 has a shard missing (frame showing through), pane 4 a diagonal glint
    c.rect(x0 + 19, wy0 + 3, x0 + 23, wy1, 'iron0')
    c.put(x0 + 20, wy0 + 2, 'iron0'); c.put(x0 + 21, wy0 + 2, 'iron0')
    c.put(x0 + 41, wy0 + 3, 'dglass1'); c.put(x0 + 42, wy0 + 2, 'dglass1')
    # the lit window (9 x 7 glass): cream core, gold ring, orange edge, a dark crack across it
    a, b = panes[2]
    gx0, gy0, gx1, gy1 = x0 + a, wy0, x0 + b, wy1
    c.rect(gx0, gy0, gx1, gy1, 'win1')
    c.rect(gx0 + 1, gy0 + 1, gx1 - 1, gy1 - 1, 'win2')
    c.rect(gx0 + 2, gy0 + 2, gx1 - 2, gy1 - 2, 'win3')
    c.put(gx0 + 1, gy1 - 2, 'win3'); c.put(gx1 - 3, gy0 + 1, 'win3')         # core is not a box
    for (px, py) in ((gx0, gy0), (gx1 - 1, gy0), (gx0, gy1 - 1), (gx1 - 1, gy1 - 1)):
        c.put(px, py, 'win0')
    crack = [(gx0, gy0 + 1), (gx0 + 1, gy0 + 2), (gx0 + 2, gy0 + 2), (gx0 + 3, gy0 + 3), (gx0 + 4, gy0 + 4),
             (gx0 + 5, gy0 + 4), (gx0 + 6, gy0 + 5), (gx0 + 7, gy0 + 6), (gx0 + 8, gy0 + 6)]
    for (px, py) in crack:
        c.put(px, py, 'iron0')
    c.put(gx0 + 4, gy0 + 3, 'iron0'); c.put(gx0 + 4, gy0 + 2, 'win1')        # a branch of the crack
    c.put(gx0 + 6, gy0 + 6, 'win1')
    if glare:                                      # B: the window glares: the frame lights up
        c.rect(gx0 - 1, gy0 - 1, gx1 + 1, gy0, 'win1')
        c.rect(gx0 - 1, gy1, gx1 + 1, gy1 + 1, 'win0')
        c.rect(gx0 - 1, gy0, gx0, gy1, 'win1')
        c.rect(gx1, gy0, gx1 + 1, gy1, 'win0')
        c.rect(gx0 + 1, gy0 + 1, gx1 - 1, gy1 - 1, 'win3')
        c.put(gx0 + 2, gy0 + 1, 'win2')
        for (px, py) in crack:
            c.put(px, py, 'win1' if px % 2 else 'iron0')
    # the warm sill under the lit window, and its light on the panel below (one step up)
    c.rect(gx0 - 1, gy1 + 1, gx1 + 1, gy1 + 2, 'rust5')
    c.rect(gx0, gy1 + 2, gx1, gy1 + 3, 'rust4')
    c.rect(gx0 + 2, gy1 + 3, gx1 - 2, gy1 + 4, 'rust4')
    # door with rivets and a handle, a step plate
    c.rect(x0 + 5, y0 + 25, x0 + 12, y1, 'iron1')
    c.rect(x0 + 5, y0 + 25, x0 + 6, y1, 'iron3')
    c.put(x0 + 10, y0 + 32, 'iron4')
    c.put(x0 + 7, y0 + 27, 'iron3'); c.put(x0 + 7, y0 + 36, 'iron3')
    # ladder up the right side to the roof
    for y in range(y0 - 2, y1, 1):
        c.put(x1 + 2, y, 'iron1')
        if (y - y0) % 4 == 0:
            c.put(x1 + 1, y, 'iron3'); c.put(x1 + 3, y, 'iron1')
    # moss creeping out of the roof seam and the panel seam (left)
    for x in range(x0, x0 + 21):
        if _h(x, 3, 31) < 0.35:
            c.put(x, y0 + 1, 'moss1')
    for x in range(x0 + 4, x0 + 21):
        if _h(x, 5, 32) < 0.3:
            c.put(x, y0 + 21, 'moss1')
    P.anchors = {'window': ((gx0 + gx1) // 2, (gy0 + gy1) // 2)}
    m = P.mask()
    win = np.zeros_like(m)
    win[gy0 - 1:gy1 + 1, gx0 - 1:gx1 + 1] = True
    c.outline(m, mode='own', light=LIGHT, lift=0.3)
    return P

# ---------------------------------------------------------------- exhaust stack
def stack(bx, by, lean=-4, height=92):
    """a banded funnel from its base centre (bx, by) up `height` px, leaning `lean` px at the top.
    Anchor: mouth (where smoke leaves)."""
    P = Part('stack', (bx, by))
    c = P.c
    tx, ty = bx + lean, by - height
    bands = [(-0.62, 'rust4'), (-0.2, 'rust3'), (0.35, 'rust2'), (1.0, 'rust1')]
    strut(c, (bx, by), (tx, ty), 13, bands)
    # rings at uneven spacing; soot darkens the top 14 px
    for k, t in enumerate((0.12, 0.31, 0.47, 0.66, 0.79)):
        y = int(by - height * t)
        x = bx + lean * t
        ring = [(-0.62, 'iron3'), (-0.2, 'iron2'), (0.35, 'iron1'), (1.0, 'iron0')]
        strut(c, (x, y), (x + lean * 0.02, y - 2 - (k % 2)), 15, ring)
    soot = {'rust4': 'iron3', 'rust3': 'iron2', 'rust2': 'iron1', 'rust1': 'iron0'}
    for x in range(int(tx) - 8, int(tx) + 9):
        depth = 9 + int(_h(x // 3, 1, 41) * 6)              # a ragged lower edge in 3 px runs
        for y in range(ty, ty + depth):
            v = c.get(x, y)
            if v in soot:
                c.put(x, y, soot[v])
    # the flared mouth and a half-open rain flap
    c.rect(int(tx) - 7, ty - 2, int(tx) + 8, ty + 1, 'iron2')
    c.rect(int(tx) - 7, ty - 2, int(tx) + 8, ty - 1, 'iron3')
    c.rect(int(tx) - 5, ty - 3, int(tx) + 6, ty - 2, 'smoke0')
    c.line(int(tx) + 6, ty - 3, int(tx) + 12, ty - 9, 'iron3')
    c.line(int(tx) + 6, ty - 2, int(tx) + 12, ty - 8, 'iron1')
    # ladder rungs up the shadow side
    for y in range(by - 6, ty + 16, -4):
        t = (by - y) / float(height)
        x = bx + lean * t + 7
        c.put(x, y, 'iron2'); c.put(x + 1, y, 'iron1')
    for y in range(by - 6, ty + 16, -1):
        t = (by - y) / float(height)
        c.put(bx + lean * t + 8, y, 'iron1')
    # a rust bloom and moss at the foot
    for x in range(bx - 6, bx + 7):
        if _h(x, 1, 43) < 0.55:
            c.put(x, by - 1, 'moss1')
            if _h(x, 2, 43) < 0.4:
                c.put(x, by - 2, 'moss0')
    P.anchors = {'mouth': (int(tx), ty - 4)}
    return P.finish()

# ---------------------------------------------------------------- jaw: the bucket ladder
def jaw(px, py, ang, length=92, missing=(4,), dented=(1,)):
    """the bucket ladder pivoting on the upper tumbler at (px, py), pointing `ang` degrees (y down)
    out to the lower tumbler. A box girder 12 px deep with lattice holes, chain links on top,
    scoop buckets on the chain underneath (mismatched, one dented, one missing). Anchor: tip."""
    P = Part('jaw', (px, py))
    c = P.c
    u, v = local_uv(px, py, ang)
    half = 7
    body = (u >= 0) & (u <= length) & (np.abs(v) <= half)
    # girder: lit top chord, dark bottom chord, a Warren web between them (holes see through)
    top = body & (v < -half + 3.2)
    bot = body & (v > half - 3.2)
    c.g[top] = 'rust3'
    c.g[body & (v < -half + 1.2)] = 'rust5'
    c.g[body & (v >= -half + 1.2) & (v < -half + 2.2)] = 'rust4'
    c.g[bot] = 'rust1'
    c.g[body & (v > half - 1.2)] = 'rust0'
    c.g[body & (v >= half - 3.2) & (v < half - 2.2)] = 'rust2'
    web = body & ~top & ~bot
    c.g[web] = None
    s_, k = 9.0, 0
    while s_ < length - 6:
        bay = 13 + (k * 7) % 5
        # a diagonal web member 2 px wide from top to bottom chord, alternating lean
        ua, ub = (s_, s_ + bay) if k % 2 == 0 else (s_ + bay, s_)
        t = (v - (-half + 3.2)) / (2 * half - 6.4)
        uc = ua + (ub - ua) * t
        mem = web & (np.abs(u - uc) <= 1.1)
        c.g[mem] = 'rust2'
        c.g[mem & (u - uc < -0.1)] = 'rust3'
        if k % 2 == 0:                                   # a vertical post every other bay
            post = web & (np.abs(u - s_) <= 0.9)
            c.g[post] = 'rust2'
        s_ += bay
        k += 1
    endcap = body & ((u < 7) | (u > length - 6))
    c.g[endcap & web] = 'rust2'
    # rivets along the top flange at uneven spacing
    uu = 6.0
    while uu < length - 4:
        dx, dy = rot(uu, -half + 2.6, ang)
        c.put(px + dx, py + dy, 'rust5')
        uu += 4 + _h(int(uu), 3, 51) * 4
    # chain links riding the top flange: alternating 2x1 dark and lit dashes
    uu = 4.0
    k = 0
    while uu < length:
        dx, dy = rot(uu, -half - 1, ang)
        c.put(px + dx, py + dy, 'iron1' if k % 2 else 'iron3')
        dx, dy = rot(uu + 1, -half - 1, ang)
        c.put(px + dx, py + dy, 'iron1' if k % 2 else 'iron3')
        uu += 2.0
        k += 1
    # buckets underneath, scoops opening toward the tip (the chain runs out along the ladder)
    sizes = [13, 11, 14, 12, 13, 11, 14]
    uu = 11.0
    for i, bw in enumerate(sizes):
        if uu + bw > length + 2:
            break
        bh = 8 + (i % 3 == 1)
        if i in missing:            # an empty socket: just the chain lug hanging
            q = quad(px, py, ang, uu + 3, uu + 5, half, half + 3)
            c.poly(q, 'iron1')
            uu += bw + 2
            continue
        dent = i in dented
        shell = quad(px, py, ang, uu, uu + bw, half - 1, half + bh)
        c.poly(shell, 'rust2')
        lit = quad(px, py, ang, uu, uu + bw, half - 1, half + 1)
        c.poly(lit, 'rust3')
        mouth = quad(px, py, ang, uu + bw - 3, uu + bw, half + 1, half + bh - 1)
        c.poly(mouth, 'iron0')
        lip = quad(px, py, ang, uu + bw - 1, uu + bw + 1, half - 1, half + bh)
        c.poly(lip, 'rust4')
        bot = quad(px, py, ang, uu, uu + bw - 2, half + bh - 1, half + bh)
        c.poly(bot, 'rust1')
        if dent:                    # a dented bucket: a bent lip and a crushed corner
            q = quad(px, py, ang, uu + 3, uu + 6, half + bh - 2, half + bh + 1)
            c.poly(q, 'rust1')
            dx, dy = rot(uu + 4, half + 3, ang)
            c.put(px + dx, py + dy, 'rust4')
        # weed hanging off the bucket (strands 1x3 to 1x6)
        if _h(i, 7, 53) < 0.7:
            dx, dy = rot(uu + bw * 0.5, half + bh, ang)
            n = 3 + int(_h(i, 8, 53) * 4)
            for kk in range(n):
                c.put(px + dx + (kk > 2) * (1 if i % 2 else -1), py + dy + kk + 1, 'moss1' if kk < n - 1 else 'moss0')
        uu += bw + 2 + int(_h(i, 9, 53) * 2)
    # upper and lower tumblers: hex drums with bolts
    for (cu, r) in ((0, 8.5), (length, 6.5)):
        dx, dy = rot(cu, 0, ang)
        cx, cy = px + dx, py + dy
        c.disc(cx, cy, r, 'iron2')
        c.disc(cx - 0.8, cy - 0.8, r - 2, 'iron3')
        c.disc(cx, cy, r - 3.5, 'iron1')
        c.disc(cx, cy, 1.5, 'pist2')
        for kk in range(5):
            a = kk * 72 + 20
            bx_, by_ = cx + math.cos(math.radians(a)) * (r - 1.6), cy + math.sin(math.radians(a)) * (r - 1.6)
            c.put(bx_, by_, 'iron4' if math.cos(math.radians(a)) + math.sin(math.radians(a)) < 0 else 'iron0')
    dx, dy = rot(length, 6, ang)
    P.anchors = {'tip': (int(round(px + dx)), int(round(py + dy)))}
    return P.finish()

# ---------------------------------------------------------------- the three hanging bucket links
LINKS = [dict(bw=13, bh=10, bar=7, dent=False), dict(bw=11, bh=9, bar=6, dent=True),
         dict(bw=14, bh=11, bar=8, dent=False)]

def link(i, px, py, ang):
    """bucket link i hanging from (px, py), swung `ang` degrees from straight down (positive
    swings right). A 2 px link bar, then an open scoop hanging mouth-up. Anchor: bottom."""
    k = LINKS[i]
    P = Part('link%d' % (i + 1), (px, py))
    c = P.c
    a = 90 - ang                                    # direction of the hang in screen degrees
    bar, bw, bh = k['bar'], k['bw'], k['bh']
    # the link bar: two plates with a pin
    q = quad(px, py, a, 0, bar, -1.2, 1.2)
    c.poly(q, 'iron2')
    q = quad(px, py, a, 0, bar, -1.2, -0.2)
    c.poly(q, 'iron4' if ang <= 10 else 'iron3')
    c.disc(px, py, 1.6, 'iron3'); c.put(px, py, 'iron0')
    # the scoop: a trapezoid wider at the mouth, hanging below the bar
    u0 = bar
    pts = []
    for (uu, vv) in ((u0, -bw / 2.0), (u0, bw / 2.0), (u0 + bh, bw / 2.0 - 2.5), (u0 + bh, -bw / 2.0 + 2.5)):
        dx, dy = rot(uu, vv, a)
        pts.append((px + dx, py + dy))
    c.poly(pts, 'rust3')
    m = c.mask_poly(pts)
    uu_, vv_ = local_uv(px, py, a)
    # shading across: the left (light) side lit, the right side dark; bottom row darker
    lightside = vv_ > 0 if math.cos(math.radians(a)) < 0 else vv_ < 0
    sgn = 1 if (rot(0, 1, a)[0] * LIGHT[0] + rot(0, 1, a)[1] * LIGHT[1]) > 0 else -1
    s = sgn * vv_ / (bw / 2.0)
    c.g[m & (s > 0.2)] = 'rust4'
    c.g[m & (s > 0.62)] = 'rust5'
    c.g[m & (s < -0.45)] = 'rust2'
    c.g[m & (uu_ > u0 + bh - 1.6)] = 'rust1'
    # the mouth: a dark lip band at the top of the scoop (it hangs mouth-up toward the bar)
    c.g[m & (uu_ < u0 + 2.0)] = 'iron1'
    c.g[m & (uu_ < u0 + 1.0)] = 'rust5'
    # ribs and rivets
    for f in (0.35, 0.7):
        rib = m & (np.abs(vv_ - (f - 0.5) * bw * 0.7) < 0.5) & (uu_ > u0 + 2.4)
        c.g[rib] = 'rust2'
    dx, dy = rot(u0 + 4, -bw / 2.0 + 2.6, a)
    c.put(px + dx, py + dy, 'rust5')
    if k['dent']:
        dx, dy = rot(u0 + bh - 3, bw / 2.0 - 3.5, a)
        c.put(px + dx, py + dy, 'rust1'); c.put(px + dx + 1, py + dy, 'rust1')
        dx, dy = rot(u0 + bh - 4, bw / 2.0 - 4.5, a)
        c.put(px + dx, py + dy, 'rust4')
    # weed draped over the rim
    dx, dy = rot(u0 + 1, -bw / 2.0 + 1, a)
    for kk in range(3 + i):
        c.put(px + dx - 1, py + dy + kk, 'moss1' if kk < 2 + i else 'moss0')
    dx, dy = rot(u0 + bh + 1, 0, a)
    P.anchors = {'bottom': (int(round(px + dx)), int(round(py + dy))),
                 'mouth': tuple(int(round(v)) for v in (px + rot(u0 + 1, 0, a)[0], py + rot(u0 + 1, 0, a)[1])),
                 'lipL': tuple(int(round(v)) for v in (px + rot(u0, -bw / 2.0, a)[0], py + rot(u0, -bw / 2.0, a)[1])),
                 'lipR': tuple(int(round(v)) for v in (px + rot(u0, bw / 2.0, a)[0], py + rot(u0, bw / 2.0, a)[1]))}
    return P.finish(lift=0.25)

# ---------------------------------------------------------------- piston legs
def leg(name, hx, hy, fx, fy, barrel=30, claw_dir=1):
    """a telescoping piston leg from the hip bearing (hx, hy) to the clamp foot at (fx, fy): a
    rust barrel with a collar, a chrome rod, and a three-prong clamp foot. Anchor: foot."""
    P = Part(name, (hx, hy))
    c = P.c
    Ln = math.hypot(fx - hx, fy - hy)
    ang = math.degrees(math.atan2(fy - hy, fx - hx))
    ux, uy = (fx - hx) / Ln, (fy - hy) / Ln
    bl = min(barrel, Ln - 8)
    cx, cy = hx + ux * bl, hy + uy * bl
    rod = [(-0.7, 'pist3'), (-0.15, 'pist2'), (0.5, 'pist1'), (1.0, 'pist0')]
    strut(c, (cx, cy), (fx - ux * 4, fy - uy * 4), 6, rod)
    barrel_b = [(-0.55, 'rust4'), (-0.05, 'rust3'), (0.5, 'rust2'), (1.0, 'rust1')]
    strut(c, (hx, hy), (cx, cy), 11, barrel_b)
    # collar at the barrel's end and a gland ring
    strut(c, (cx - ux * 3, cy - uy * 3), (cx, cy), 13, [(-0.5, 'iron4'), (0.1, 'iron3'), (0.6, 'iron2'), (1.0, 'iron1')])
    # a hydraulic hose along the barrel (a 1 px line with a sag)
    nx, ny = -uy, ux
    if nx + ny > 0:
        nx, ny = -nx, -ny
    for t in np.linspace(0.1, 0.9, 30):
        sag = math.sin(t * math.pi) * 2.5
        c.put(hx + ux * bl * t - nx * (7 + sag), hy + uy * bl * t - ny * (7 + sag), 'iron1')
    # barrel bands with rivets
    for t in (0.35, 0.62):
        bx_, by_ = hx + ux * bl * t, hy + uy * bl * t
        strut(c, (bx_, by_), (bx_ + ux * 2, by_ + uy * 2), 11, [(-0.5, 'rust5'), (0.3, 'rust3'), (1.0, 'rust1')])
    # moss in the collar seam (one olive step only: the tile budget)
    for t in range(-5, 6):
        if _h(t, 1, 61) < 0.4:
            c.put(cx + nx * t * 0.9 - ux, cy + ny * t * 0.9 - uy, 'moss1')
    # the hip bearing: a bolted disc
    c.disc(hx, hy, 7.5, 'iron2')
    c.disc(hx - 1, hy - 1, 5.5, 'iron3')
    c.disc(hx, hy, 4, 'iron1')
    c.disc(hx - 0.5, hy - 0.5, 2, 'pist2')
    for kk in range(6):
        a = kk * 60 + 10
        c.put(hx + math.cos(math.radians(a)) * 6, hy + math.sin(math.radians(a)) * 6, 'iron4' if kk in (3, 4) else 'iron0')
    # the clamp foot: a heavy block with three hooked prongs, mismatched lengths
    fx0, fy0 = fx - ux * 5, fy - uy * 5
    c.disc(fx0, fy0, 4.2, 'iron2'); c.disc(fx0 - 1, fy0 - 1, 2.6, 'iron3'); c.put(fx0, fy0, 'iron0')
    blk = [(fx - 8, fy - 3), (fx + 8, fy - 3), (fx + 9, fy + 2), (fx - 9, fy + 2)]
    c.poly(blk, 'iron2')
    c.rect(fx - 8, fy - 3, fx + 8, fy - 2, 'iron4')
    c.rect(fx - 9, fy + 1, fx + 9, fy + 2, 'iron1')
    for j, (dxp, ln) in enumerate(((-8, 6), (-1, 8), (6, 5))):
        x = fx + dxp
        for kk in range(ln):
            bend = (kk * kk) // 10 * claw_dir
            c.put(x + bend, fy + 2 + kk, 'iron3' if kk < 2 else 'iron2')
            c.put(x + bend + 1, fy + 2 + kk, 'iron1')
        c.put(x + ((ln - 1) * (ln - 1)) // 10 * claw_dir + claw_dir, fy + 1 + ln, 'pist2')
    P.anchors = {'foot': (int(fx), int(fy) + 9)}
    return P.finish()

# ---------------------------------------------------------------- poses
def shear(parts, x0, k):
    """tilt the hull group: each column moves up by round((x - x0) * k) px (k > 0 lifts the bow).
    A vertical shear keeps verticals vertical and steps the horizontals in even runs."""
    sh = lambda x: int(round((x - x0) * k))
    for P in parts:
        g = P.c.g
        out = np.full(g.shape, None, object)
        for x in range(W):
            d = sh(x)
            if d > 0:
                out[:H - d, x] = g[d:, x]
            elif d < 0:
                out[-d:, x] = g[:H + d, x]
            else:
                out[:, x] = g[:, x]
        P.c.g = out
        P.anchors = {n: (ax, ay - sh(ax)) for n, (ax, ay) in P.anchors.items()}
        P.pivot = (P.pivot[0], P.pivot[1] - sh(P.pivot[0]))
    return sh

POSES = {
    'A': dict(body=(46, 124), tilt=0.075, jaw_ang=24, links=(4, 7, 10), stack_lean=-4,
              leg_r=(-26, 42), leg_f=(22, 40), water=166, glare=False),
    'B': dict(body=(52, 97), tilt=-0.035, jaw_ang=10, links=(26, 34, 43), stack_lean=-6,
              leg_r=(-22, 67), leg_f=(30, 43), water=166, glare=True),
}

def assemble(pose):
    """-> parts in draw order. The hull group (body, cabin, stack) is drawn, then tilted; the
    jaw, links and legs are posed from its tilted anchors."""
    p = POSES[pose]
    B = body(*p['body'], wet_line=None if pose == 'A' else 48)
    an = B.anchors
    S = stack(an['stack'][0], an['stack'][1], lean=p['stack_lean'])
    C = cabin(an['cabin'][0], an['cabin'][1], glare=p['glare'])
    shear([B, S, C], p['body'][0] + 70, p['tilt'])
    an = B.anchors
    J = jaw(an['jaw'][0], an['jaw'][1], p['jaw_ang'])
    links = []
    px, py = J.anchors['tip']
    for i, a in enumerate(p['links']):
        Lk = link(i, px, py, a)
        links.append(Lk)
        px, py = Lk.anchors['bottom']
    hr, hf = an['hip_r'], an['hip_f']
    LR = leg('leg_r', hr[0], hr[1], hr[0] + p['leg_r'][0], hr[1] + p['leg_r'][1], claw_dir=-1)
    LF = leg('leg_f', hf[0], hf[1], hf[0] + p['leg_f'][0], hf[1] + p['leg_f'][1], claw_dir=1)
    order = [LR, S, B, C, J] + links + [LF]
    return order

def compose(order, water_y=None, keep_below=()):
    c = Canvas(W, H, None)
    for P in order:
        g = P.c.g
        if water_y is not None and P.name not in keep_below:
            g = g.copy()
            g[water_y:] = None
        m = ~np.equal(g, None)
        c.g[m] = g[m]
    return c
