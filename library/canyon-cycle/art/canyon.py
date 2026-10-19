"""Canyon Cycle: the one index map (320x180), drawn back to front into a slot canvas.

Every pixel holds a slot name from palettes.SLOTS. Motion never redraws a pixel: the falls, the
river reaches and the stars are drawn in their cycling ranges (WA, WB, RA, RB, T), the rain and the
bolt in switched slots, the forge and lantern in flicker slots. Positions and shapes are placed by
hand (geo.py and the tables below); the code rasterises and shades them.
"""
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[3] / 'tools'))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from canvas import Canvas, seam
import shapes
import texture
import geo as G

W, H = G.W, G.H
YY, XX = G.YY, G.XX


def hsh(*a):
    """deterministic hash of ints -> [0, 1)"""
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xffffffff)) * 16777619) & 0xffffffff
        h ^= h >> 13
        h = (h * 1274126177) & 0xffffffff
    return (h & 0xffffff) / float(0x1000000)


def stamp(c, art, key, ox, oy):
    rows = [r for r in art.strip('\n').split('\n')]
    for j, row in enumerate(rows):
        for i, ch in enumerate(row.strip()):
            if ch in '. ':
                continue
            c.put(ox + i, oy + j, key[ch])


def inb(x, y):
    return 0 <= x < W and 0 <= y < H


# ================================================================ far plane
SKY_STOPS = [('S0', 0), ('S1', 20, 12), ('S2', 29, 10), ('S3', 38, 10), ('S4', 72, 14), ('S5', 88, 12)]

# stars: hand-placed (x, y, slot); two clusters and a loose arc, on solid S0 only (y < 17)
STARS = [(112, 8, 'T2'), (105, 9, 'T0'), (108, 2, 'T1'), (112, 6, 'T0'), (115, 11, 'T1'), (118, 3, 'T0'),
         (103, 12, 'T1'), (110, 13, 'T0'), (170, 0, 'T2'), (130, 1, 'T0'), (142, 0, 'T1'), (150, 2, 'T0'),
         (163, 1, 'T1'), (177, 0, 'T0'), (186, 2, 'T1'), (199, 1, 'T0'), (106, 1, 'T2'), (196, 0, 'T1'),
         (124, 2, 'T1'), (99, 7, 'T0')]


def sky(c):
    c.bands(0, 100, SKY_STOPS)
    for x, y, s in STARS:
        if c.get(x, y) == 'S0':
            c.put(x, y, s)


def lobe_shade(c, m, rim, lit, body, crease, prior):
    """one cloud billow: rim on the upper-left edge, a lit tier inside it, the body, and a dark
    crease along its lower-right edge where it sits on an earlier billow"""
    out = ~m
    def near(dx, dy, k):
        r = np.zeros_like(m)
        for s in range(1, k + 1):
            r |= np.roll(np.roll(out, -dy * s, 0), -dx * s, 1)
        return r
    c.fill(m, body)
    c.fill(m & (near(-1, -1, 3) | near(0, -1, 2)), lit)
    c.fill(m & (near(-1, -1, 1) | near(0, -1, 1)) & ~near(1, 1, 3), rim)
    c.fill(m & (near(1, 1, 1) | near(0, 1, 1)) & prior, crease)


def ell(cx, cy, rx, ry):
    return ((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2 < 1


def cloud(c):
    """the storm cell at sunset: a long flat anvil whose top holds the rose light, a tower of
    billows of very different size lit on the upper left, and a long dark flat base."""
    total = np.zeros((H, W), bool)
    anv = c.mask_poly([(118, 9), (124, 5), (138, 3), (158, 2), (180, 3), (200, 3), (218, 4), (218, 11),
                       (204, 11), (190, 13), (176, 15), (166, 18), (154, 19), (138, 17), (124, 14)])
    c.fill(anv, 'C1')
    out = ~anv
    c.fill(anv & (np.roll(out, 1, 0) | np.roll(out, 2, 0)) & (XX < 204), 'C2')
    c.fill(anv & np.roll(out, 1, 0) & (XX < 186), 'C3')
    c.fill(anv & (np.roll(out, -1, 0) | np.roll(out, -2, 0)) & (XX > 158), 'C0')
    total |= anv
    billows = [  # cx, cy, r (x stretch 1.25): back to front; radii 3..12, never two alike in a row
        (171, 25, 11), (159, 17, 7), (150, 11, 4), (156, 29, 9), (142, 19, 10), (133, 11, 3),
        (136, 28, 6), (126, 23, 5), (146, 33, 12), (124, 33, 7), (117, 37, 4), (184, 32, 8),
        (198, 35, 5), (165, 35, 6)]
    creased = {(142, 19, 10), (146, 33, 12), (171, 25, 11)}
    for cx, cy, r in billows:
        m = (((XX - cx) / (1.25 * r)) ** 2 + ((YY - cy) / r) ** 2 < 1) & (YY < 41)
        c.fill(m, 'C1')
        if (cx, cy, r) in creased:
            low_edge = m & ~np.roll(m, -1, 0) & total
            c.fill(low_edge & (XX > cx - r), 'C0')
        total |= m
    # the lit upper edge: only where the mass meets open sky above or up-left
    sky_ = ~total
    up1 = np.roll(sky_, 1, 0) | np.roll(np.roll(sky_, 1, 0), 1, 1)
    up3 = up1 | np.roll(sky_, 2, 0) | np.roll(sky_, 3, 0)
    c.fill(total & up3 & ~anv & (YY < 30), 'C2')
    c.fill(total & up1 & ~anv & (YY < 26), 'C3')
    c.fill(total & up1 & ~anv & (YY >= 26) & (XX < 150), 'C2')
    # the long flat base: one straight-ish underside with 1 px steps, dark
    base = c.mask_poly([(106, 40), (112, 35), (130, 33), (160, 32), (190, 33), (208, 35), (212, 40),
                        (200, 41), (170, 41), (140, 41), (118, 41)])
    c.fill(base & ~total, 'C0')
    out = ~(total | base)
    low = np.zeros_like(total)
    for s_ in range(1, 5):
        low |= np.roll(out, -s_, 0)
    c.fill((total | base) & low & (YY > 26), 'C0')
    total |= base
    return total


def mesa(c):
    m = G.poly(G.MESA)
    b = G.poly(G.BUTTE)
    cap = m & (YY < 77)
    talus = m & (YY >= 77)
    # the caprock cliff: lit left third, shadowed right, two strata seams; talus split by gullies
    # three strata bands of uneven thickness, told apart by tone (no seam lines, no joints)
    band_of = lambda x, y: 0 if y < 66 + (x // 9) % 2 else 1 if y < 71 + (x // 13) % 2 else 2
    for y, x in zip(*np.nonzero(cap)):
        b_ = band_of(x, y)
        side = 0 if x < 149 + 2 * b_ else 1 if x < 183 - b_ else 2
        c.put(x, y, [['M2', 'M1', 'M2'], ['M1', 'M0', 'M1'], ['M0', 'M0', 'M0']][side][b_])
    c.fill(talus, 'M1')
    c.fill(talus & (XX < 141), 'M2')
    c.fill(talus & (XX > 178), 'M0')
    for x in range(129, 193):
        col = np.nonzero(m[:, x])[0]
        if len(col):
            c.put(x, col.min(), 'M3' if x < 176 else 'M2')
            if x < 150:
                c.put(x, col.min() + 1, 'M3' if x < 140 else 'M2')
    # the overhang shadow where the talus starts
    for x in range(127, 196):
        if m[77, x] and hsh(x // 4, 77) > 0.3:
            c.put(x, 77, 'M0' if x > 136 else 'M1')
    gullies = [(130, 78, 10, -1), (136, 78, 14, -1), (143, 78, 7, -1), (153, 78, 18, 0), (162, 78, 9, 0),
               (170, 78, 15, 1), (179, 78, 8, 1), (187, 78, 13, 1), (196, 84, 8, 1), (124, 86, 6, -1)]
    for gx, gy, ln, lean in gullies:
        for k in range(ln):
            x = gx + (lean * k) // 3
            y = gy + k
            if inb(x, y) and m[y, x]:
                v = c.get(x, y)
                c.put(x, y, {'M2': 'M1', 'M1': 'M0', 'M0': 'M0', 'M3': 'M1'}.get(v, v))
                if lean < 0 and inb(x + 1, y) and m[y, x + 1] and c.get(x + 1, y) == 'M2' and k < ln - 3:
                    c.put(x + 1, y, 'M3')
    # the butte: flat top, lit left half
    c.fill(b, 'M1')
    c.fill(b & (XX < 110), 'M2')
    c.fill(b & (XX > 116), 'M0')
    for x in range(104, 118):
        col = np.nonzero(b[:, x])[0]
        if len(col):
            c.put(x, col.min(), 'M3' if x < 112 else 'M2')
    for x in range(103, 121):
        if b[89, x]:
            c.put(x, 89, 'M0')
    return m | b


def bolt(c):
    """the strike: a jagged main channel from the cloud base to the mesa top, 1-2 px wide (doubled
    at the kinks), with three short branches; drawn only on the sky (S3 and its dither with S2)"""
    main = [(156, 41), (156, 42), (155, 43), (154, 44), (154, 45), (155, 46), (157, 47), (158, 48),
            (158, 49), (157, 50), (156, 51), (157, 52), (159, 53), (160, 54), (160, 55), (159, 56),
            (160, 57), (162, 58), (163, 59), (163, 60), (164, 61)]
    thick = [(155, 44), (156, 46), (159, 48), (158, 52), (161, 54), (161, 58)]
    branches = [[(154, 45), (152, 46), (151, 47), (150, 49), (149, 50)],
                [(158, 49), (160, 50), (162, 51), (163, 52), (165, 54)],
                [(160, 56), (158, 58), (157, 59), (157, 60)]]
    for x, y in main + thick + [p for br in branches for p in br]:
        if c.get(x, y) in ('S3', 'S2'):
            c.put(x, y, 'BL')


def rain(c):
    """the storm's rain curtain, drawn once in switched slots under the right of the base, leaning
    left toward the mesa: streaks of 2-5 px, denser in the curtain's heart"""
    on = {'S3': 'RS3', 'C0': 'RC0', 'M0': 'RM0', 'M1': 'RM1'}
    for i in range(900):
        x = 166 + int(44 * hsh(i, 11))
        y = 40 + int(50 * hsh(i, 12))
        heart = abs(x - 186) < 11
        if hsh(i, 14) > (0.85 if heart else 0.45):
            continue
        if y > 64 + int(26 * hsh(i, 15)):
            continue
        ln = 2 + int(4 * hsh(i, 13))
        for k in range(ln):
            xx, yy = x - (k + (y % 3)) // 3, y + k
            v = c.get(xx, yy) if inb(xx, yy) else None
            if v in on:
                c.put(xx, yy, on[v])


# ================================================================ middle plane
def rock_step(c):
    m = G.step_mask()
    c.fill(m, 'H1')
    f = G.RIGHT_FALL
    joints = [116, 144, 151, 160, 168, 177, 189, 196, 203, 209]
    for jx in joints:
        top = next((y for y in range(85, 124) if m[y, jx]), 124)
        ln = 6 + int(12 * hsh(jx, 1))
        for y in range(top + 1, min(124, top + ln)):
            c.put(jx, y, 'H0')
            if m[y, jx + 1] and hsh(jx, y) < 0.8:
                c.put(jx + 1, y, 'H2')
    for x in range(96, 215):
        top = next((y for y in range(85, 124) if m[y, x]), None)
        if top is not None:
            c.put(x, top, 'H2')
    # wet dark rock either side of the right fall, ragged
    for ff in (f, G.RIGHT_FALL2):
        for y in range(ff['y0'] + 2, ff['y1']):
            for x in (ff['x0'] - 2, ff['x0'] - 3, ff['x1'] + 1, ff['x1'] + 2):
                if m[y, x] and hsh(x, y, 9) < (0.7 if x in (ff['x0'] - 2, ff['x1'] + 1) else 0.3):
                    c.put(x, y, 'H0')
    # the pinnacle's lip the fall pours over: lit, a dark notch behind the water
    for x in range(121, 140):
        c.put(x, 76 if 124 <= x <= 136 else 77, 'H2')
    for x in range(125, 135):
        c.put(x, 75, 'H0')
    return m


def fall(c, f, rng_name, hi_edge, lo_edge, flare, seed, foot=True, lip=True):
    """a fall in a 6-slot cycling range (each column keeps its own phase and streak length, so the
    rotation makes streaks fall at 10 fps). It pours: a domed curl over the lip with shoulders that
    overhang it and a shadow under them; ragged sides that step out unevenly as it widens; a few
    detached streaks beside it; a spray cloud at the base, wider than the fall, that dissolves at
    its edges. hi_edge / lo_edge are kept for the call signature (unused: no cylinder edges)."""
    x0, x1, y0, y1 = f['x0'], f['x1'], f['y0'], f['y1']
    col_phase = {x: int(24 * hsh(x, seed)) for x in range(x0 - 16, x1 + 17)}
    col_seg = {x: 3 + int(3 * hsh(x, seed + 1)) for x in range(x0 - 16, x1 + 17)}

    def slot(x, y):
        ph = col_phase[x] + (7 if hsh(x, y // 9, seed + 2) < 0.25 else 0)
        return '%s%d' % (rng_name, ((y + ph) // col_seg[x]) % 6)

    def jitter(side):
        out, y = {}, y0
        while y < y1:
            run = 3 + int(5 * hsh(y, side, seed + 20))
            j = int(3 * hsh(y, side, seed + 21) * min(1.0, 0.3 + (y - y0) / 12.0))
            for yy in range(y, min(y1, y + run)):
                out[yy] = j
            y += run
        return out
    jl, jr = jitter(0), jitter(1)
    m = np.zeros((H, W), bool)
    edges = {}
    for y in range(y0, y1):
        k = (y - y0) / max(1, y1 - y0)
        grow = flare * k ** 1.2
        a = int(round(x0 - grow)) - jl[y]
        b = int(round(x1 - 1 + grow)) + jr[y]
        r = y - y0
        if lip and r < 4:
            a, b = [(x0 + 1, x1 - 2), (x0, x1 - 1), (x0 - 1, x1), (x0 - 1, x1)][r]
        for x in range(a, b + 1):
            s = slot(x, y)
            if lip and r < 3:                                 # the curl: bright, shimmering sideways
                s = 'N1' if (r == 0 or (r == 1 and hsh(x, seed + 12) < 0.4)) else '%s%d' % (rng_name, (x + r) % 6)
            c.put(x, y, s)
            m[y, x] = True
        if lip and 2 <= r <= 5:                               # shadow under the overhanging shoulders
            for x in (a - 1, b + 1):
                c.put(x, y, 'K0' if rng_name == 'WA' else 'H0')
        edges[y] = (a, b)
    # detached streaks beside the fall: 2-4 px, 1-2 px off the edge, mismatched spacing
    for side in (0, 1):
        y = y0 + 7 + int(5 * hsh(side, seed + 30))
        while y < y1 - 5:
            a, b = edges[y]
            off = 2 + int(2 * hsh(y, side, seed + 31))
            x = a - off if side == 0 else b + off
            for yy in range(y, y + 2 + int(3 * hsh(y, side, seed + 32))):
                if yy < y1:
                    c.put(x, yy, slot(x, yy))
            y += 6 + int(9 * hsh(y, side, seed + 33))
    if foot:
        a, b = edges[y1 - 1]
        spray(c, (a + b) / 2.0, y1, (b - a) / 2.0 + 7, 7, rng_name, seed + 40)
    return m


def spray(c, cx, y, half, hgt, rng_name, seed):
    """a splash crown / spray cloud: dense and churning in the middle (range slots and foam), thinning
    to loose pixels at its edges and top, with droplets thrown above it"""
    for x in range(int(cx - half), int(cx + half) + 1):
        d = min(1.0, abs(x - cx) / half)
        h = int(hgt * (1 - d ** 1.4) + 2 * hsh(x, seed))
        for yy in range(y - h, y + 2):
            up = (y - yy) / max(1.0, h)
            if hsh(x, yy, seed + 1) < 1.1 - 0.75 * d - 0.35 * up:
                k = hsh(x, yy, seed + 2)
                c.put(x, yy, 'N1' if k < 0.12 else 'N0' if k < 0.3 else '%s%d' % (rng_name, int(6 * hsh(x, yy, seed + 3))))
    for i in range(9):                                        # droplets above and beside the crown
        x = int(cx - half + 2 * half * hsh(i, seed + 4))
        yy = y - hgt - 1 - int(4 * hsh(i, seed + 5)) + int(abs(x - cx) / half * 4)
        c.put(x, yy, 'N0')


# ================================================================ water
def water(c):
    pool = G.poly(G.POOL)
    river = G.poly(G.RIVER)
    w = pool | river
    tmp = Canvas(W, H, None)
    tmp.bands(118, 180, [('V1', 118), ('V2', 133, 10), ('V1', 150, 10), ('V0', 167, 12)])
    for y, x in zip(*np.nonzero(w)):
        c.put(x, y, tmp.get(x, y))
    # dark reflections along both banks (the banks' mirror), ragged inner edge
    land = ~w
    dl = np.zeros((H, W), int)
    for s in range(1, 9):
        dl += (np.roll(land, s, 1) | np.roll(land, -s, 1)) & w
    for y in range(127, H):
        for x in range(W):
            if not w[y, x]:
                continue
            near_l = any(land[y, x - s] for s in range(1, 1 + 3 + int(4 * hsh(y // 2, x // 9, 21))) if x - s >= 0)
            near_r = any(land[y, x + s] for s in range(1, 1 + 2 + int(3 * hsh(y // 2, x // 9, 22))) if x + s < W)
            if near_l or near_r:
                c.put(x, y, 'Q0')
    # the walls' feet mirrored in the pool: a stepped dark band under each wall
    for x in range(40, 232):
        if 100 <= x < 205:
            continue
        depth = 3 + int(4 * hsh(x // 3, 23))
        for k in range(depth):
            y = 124 + k
            if inb(x, y) and w[y, x] and hsh(x, y, 24) < (0.97 - 0.1 * k):
                c.put(x, y, 'Q0')
    return w


def river_glints(c, w):
    """sparse dashes in the cycling ranges: RA on the far reach (glints travel left), RB on the near
    reach (glints travel right). Each dash pixel's slot steps along x, so the highlight slides."""
    rows_a = [127, 129, 132, 134, 137, 140, 142, 145, 148, 150]
    rows_b = [153, 156, 158, 161, 163, 166, 169, 171, 174, 177]
    for rows, name, sign, seed in ((rows_a, 'RA', -1, 41), (rows_b, 'RB', 1, 57)):
        for r, y in enumerate(rows):
            xs = np.nonzero(w[y])[0]
            if len(xs) == 0:
                continue
            x = xs.min() + 4 + int(8 * hsh(y, seed))
            end = xs.max() - 4
            while x < end:
                ln = [4, 6, 9, 5, 11, 7, 3, 8][int(8 * hsh(x, y, seed + 1))]
                ph = int(5 * hsh(x, y, seed + 2))
                for k in range(ln):
                    xx = x + k
                    if xx < end and c.get(xx, y) in ('V0', 'V1', 'V2', 'Q0'):
                        c.put(xx, y, '%s%d' % (name, (ph + (sign * xx) // 2) % 5))
                gap = 7 + int(18 * hsh(x, y, seed + 3)) + (10 if hsh(y, x // 30, seed + 4) < 0.3 else 0)
                x += ln + gap


def foam(c, w):
    """static foam dashes drifting from the falls' feet, mismatched lengths"""
    dashes = [(80, 128, 4, 'N1'), (86, 130, 3, 'N0'), (110, 127, 5, 'N0'), (76, 131, 2, 'N0'),
              (104, 131, 3, 'N1'), (116, 129, 2, 'N0'), (95, 133, 4, 'N0'), (140, 127, 4, 'N0'),
              (146, 129, 6, 'N1'), (153, 127, 3, 'N0'), (127, 131, 5, 'N1'), (134, 134, 3, 'N0'),
              (158, 130, 2, 'N0'), (119, 135, 2, 'N0'), (149, 133, 4, 'N0'), (101, 136, 2, 'N0')]
    for x, y, ln, s in dashes:
        for k in range(ln):
            if w[y, x + k]:
                c.put(x + k, y, s)


FORGE_REFL = """
.hhhhh.hhh.hhh.
..hhh.hhhhh.h..
h.hh....hhh.hh.
...............
..wwhh..hhw.w..
.w....hhh...ww.
....www...ww...
.ww..w.........
...............
..ww..wwww.....
.....ww..w.....
...www.........
.......ww......
....w...www....
...............
......ww.......
....w..........
"""
LANTERN_REFL = """
.hhh.h.
..hhh..
.h..hh.
.......
..ww...
...ww..
.w..w..
.......
...ww..
..w....
.......
...w...
"""


def reflections(c, w):
    """warm columns reflected under the forge and the lantern: broken, stepped dashes of irregular
    length and spacing that taper and thin out with depth, hand-typed; the empty rows are where the
    far reach's current streaks cross (flicker slots, so they flicker with their source)"""
    for art, x0, y0, hot, warm in ((FORGE_REFL, 222, 124, 'F1', 'F0'), (LANTERN_REFL, 195, 124, 'L1', 'L0')):
        for j, row in enumerate(art.strip().split('\n')):
            for i, ch in enumerate(row.strip()):
                x, y = x0 + i, y0 + j
                if ch != '.' and inb(x, y) and w[y, x]:
                    c.put(x, y, hot if ch == 'h' else warm)
    for (xa, xb, y) in ((221, 231, 127), (226, 236, 132), (194, 201, 127), (196, 201, 131)):   # the crossings
        for x in range(xa, xb):
            if w[y, x]:
                c.put(x, y, 'RA%d' % ((-x) // 2 % 5))


# ================================================================ near banks
ROCKS = [  # hand-placed outlines, back to front; split: x of the lit/shadow facet line at the top
    ([(34, 128), (42, 125), (50, 126), (53, 131), (46, 134), (36, 133)], 42),
    ([(240, 134), (248, 129), (259, 130), (266, 136), (258, 141), (244, 141)], 250),
    ([(286, 128), (296, 123), (309, 124), (318, 130), (306, 134), (290, 134)], 297),
    ([(58, 146), (64, 141), (72, 142), (77, 147), (72, 151), (60, 151)], 66),
    ([(196, 161), (201, 156), (210, 155), (216, 159), (213, 164), (200, 165)], 205),
    ([(-2, 141), (8, 134), (22, 132), (35, 136), (45, 144), (51, 155), (49, 167), (55, 181), (-2, 181)], 22),
    ([(262, 181), (269, 162), (280, 150), (296, 142), (312, 140), (322, 141), (322, 181)], 292),
    ([(42, 181), (47, 168), (56, 160), (67, 158), (78, 162), (86, 171), (92, 181)], 64),
    ([(224, 181), (231, 171), (243, 166), (257, 168), (267, 176), (270, 181)], 244),
]


def rock(c, pts, split, seed):
    """a hand-shaped boulder in planes: a lit top plane, a mid left face, a shadow right face, its
    own dark outline, one crack. The floor of the gorge is in shadow, so the tops take R2/R3."""
    m = c.mask_poly(pts)
    if not m.any():
        return m
    above_out = m & ~np.roll(m, 1, 0)
    top = np.zeros_like(m)
    for s in range(0, 3):
        top |= np.roll(above_out, s, 0)
    top &= m
    ys, xs = np.nonzero(m)
    ytop = ys.min()
    c.fill(m, 'R1')
    xsplit = split + (YY - ytop) * 0.35
    c.fill(m & (XX > xsplit), 'R0')
    c.fill(top & (XX <= xsplit + 2), 'R2')
    c.fill(above_out & (XX < split), 'R3')
    ring = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    c.fill(ring & ~above_out, 'K0')
    c.fill(above_out & (XX >= split + 6), 'K0')
    # one crack, wandering down from the top edge
    if xs.max() - xs.min() > 18:
        x = split - 3
        y = ytop + 3
        for k in range(int((ys.max() - ytop) * 0.6)):
            if not (inb(x, y) and m[y, x]):
                break
            c.put(x, y, 'K0')
            if inb(x + 1, y) and m[y, x + 1] and c.get(x + 1, y) == 'R1':
                c.put(x + 1, y, 'R2')
            y += 1
            if hsh(k, seed) < 0.35:
                x += 1 if hsh(k, seed + 1) < 0.6 else -1
    return m


def banks(c, w):
    land = (YY >= G.WALL_FOOT - 1) & ~w
    c.fill(land, 'R0')
    # ground: pebble clusters, not noise
    for i in range(70):
        x = int(W * hsh(i, 71))
        y = G.WALL_FOOT + int((H - G.WALL_FOOT) * hsh(i, 72))
        for dx, dy, s in ((0, 0, 'R2'), (1, 0, 'R1'), (0, 1, 'K0'), (1, 1, 'K0')):
            if inb(x + dx, y + dy) and land[y + dy, x + dx]:
                c.put(x + dx, y + dy, s)
    # the pebble beach on the inner bend: a band following the bank
    for y in range(144, 166):
        xs = np.nonzero(w[y, 150:230])[0]
        if len(xs) == 0:
            continue
        xb = 150 + xs.max() + 1                     # first land pixel right of the water
        wd = 3 + int(4 * (1 - abs(y - 155) / 11.0))
        for x in range(xb, xb + wd):
            if inb(x, y) and land[y, x]:
                k = hsh(x, y, 73)
                c.put(x, y, 'H2' if k < 0.2 else 'H1' if k < 0.65 else 'H0')
    rocks = np.zeros((H, W), bool)
    for i, (pts, split) in enumerate(ROCKS):
        rocks |= rock(c, pts, split, 100 + i)
    # pebbles and foam where land meets water
    for y in range(G.WALL_FOOT, H):
        for x in range(1, W - 1):
            if w[y, x] and (land[y, x - 1] or land[y, x + 1]):
                if hsh(x // 2, y, 83) < 0.4 and c.get(x, y) in ('V0', 'V1', 'V2', 'Q0'):
                    c.put(x, y, 'N0')
    # reeds at the left bank's waterline: clusters of 1 px blades of mismatched height
    for rx, n in ((78, 4), (90, 3), (96, 5)):
        for k in range(n):
            x = rx + k * 2 - (k % 2)
            hgt = 3 + int(4 * hsh(rx, k, 74))
            col = np.nonzero(w[:, x] & (YY[:, x] > 134))[0]
            if len(col) == 0:
                continue
            yb = col.min() - 1
            for y in range(yb - hgt, yb + 1):
                c.put(x, y, 'G1' if y < yb - 1 else 'G0')
            c.put(x, yb - hgt, 'G2')


# ================================================================ near walls
# strata top to bottom: (top y, kind). Hard bands are ledges (7-22 px): they jut into the gap with
# an overhanging lip, take a lit top edge and carry the flake dashes. Soft bands (4-8 px) are the
# recesses under the lips, set back and dark.
LEFT_BANDS = [(0, 'hard'), (12, 'soft'), (18, 'hard'), (27, 'soft'), (32, 'hard'), (50, 'soft'),
              (56, 'hard'), (69, 'soft'), (75, 'hard'), (95, 'soft'), (100, 'hard'), (116, 'soft')]
RIGHT_BANDS = [(0, 'hard'), (13, 'soft'), (17, 'hard'), (33, 'soft'), (39, 'hard'), (48, 'soft'),
               (54, 'hard'), (76, 'soft'), (81, 'hard'), (110, 'hard'), (119, 'soft')]
# a few short cracks inside hard bands (x, y, length), never spanning a band
LEFT_CRACKS = [(70, 36, 9), (31, 59, 7), (84, 79, 11), (48, 103, 8), (16, 21, 6)]
RIGHT_CRACKS = [(232, 20, 9), (268, 42, 6), (226, 58, 12), (296, 85, 10), (258, 113, 5)]


def wall(c, side):
    """canyon rock in planes: ledges of uneven thickness with frayed overhanging lips and a lit
    top edge (sunset side), stacked flake dashes on the faces, dark recesses under the lips, darker
    toward the frame edge. No cells, no full-length seams."""
    L = side == 'L'
    bands = LEFT_BANDS if L else RIGHT_BANDS
    knots = G.LEFT_EDGE if L else G.RIGHT_EDGE
    seed = 300 if L else 500
    xs = np.arange(W)
    tilt = 0.035 if L else -0.03                     # strata dip gently toward the gap
    bounds = [np.zeros(W, int)]
    for i, (y, k) in enumerate(bands):
        if i:
            wav = seam(xs, 'wave', (2.0, 1.0), seed + 11 * i)
            bounds.append(np.round(y + wav + tilt * (xs - (100 if L else 220))).astype(int))
    band = np.zeros((H, W), int)
    for i in range(1, len(bounds)):
        band = np.where(YY >= bounds[i][None, :], i, band)
    hard = np.array([k == 'hard' for y, k in bands])
    jut = np.array([(3 + int(4 * hsh(i, seed))) if hard[i] else -(1 + int(2 * hsh(i, seed + 1)))
                    for i in range(len(bands))])
    edge = np.array([G.edge_x(knots, y) for y in range(H)])
    m = np.zeros((H, W), bool)
    for y in range(G.WALL_FOOT + 2):
        for x in range(W):
            b = band[y, x]
            depth = y - bounds[b][x]                 # rows below this band's top
            j = jut[b] - (depth // 4 if hard[b] else 0)  # the lip juts, the face undercuts
            e = edge[y] + (j if L else -j)
            m[y, x] = x < e if L else x >= e
    m = shapes.fray(m, teeth=0.18, notches=0.12, islands=0.0, depth=2, seed=seed,
                    facing=(1, 0) if L else (-1, 0))
    m &= YY <= G.WALL_FOOT + 1
    rows = [np.nonzero(m[y])[0] for y in range(H)]
    e_row = np.array([(r.max() if L else r.min()) if len(r) else 0 for r in rows])
    dist = (e_row[:, None] - XX) if L else (XX - e_row[:, None])
    for y in range(G.WALL_FOOT + 2):
        for x in range(W):
            if not m[y, x]:
                continue
            b = band[y, x]
            d = dist[y, x] + int(8 * hsh(b, x // 23, seed + 3)) - 4    # falloff edges jog per band
            depth = y - bounds[b][x]
            if L:
                tone = 2 if d < 5 else 1 if d < 42 else 0
                if hard[b] and d < 70:
                    tone = min(2, tone + 1)
            else:
                tone = 3 if d < 12 else 2 if d < 34 else 1 if d < 72 else 0
                if not hard[b]:
                    tone = max(0, tone - 1)
            s = 'R%d' % tone
            if hard[b] and b and depth == 0 and hsh(x // 5, b, seed + 4) > 0.14:
                s = 'R%d' % min(4, tone + (2 if (not L and d < 30) else 1))       # lit top edge, broken
            elif not hard[b] and b and depth < (2 if d < 36 else 1):
                s = 'K0' if tone <= 1 else 'R%d' % (tone - 2)                    # recess under the lip
            c.put(x, y, s)
    # stacked flake dashes on the ledge faces
    faces = m & np.isin(c.g, ['R1', 'R2', 'R3']) & hard[band] & (dist > 2)
    texture.flakes(c, faces & np.isin(c.g, ['R1']), 'R', base=1, cell=(10, 5), cluster=0.7, gate=0.75,
                   length=(3, 7), stack=(1, 3), lit_end=2, shadow=True, steps=5, seed=seed + 1)
    texture.flakes(c, faces & np.isin(c.g, ['R2']), 'R', base=2, cell=(9, 5), cluster=0.7, gate=0.75,
                   length=(3, 6), stack=(1, 3), lit_end=1, shadow=True, steps=5, seed=seed + 2)
    # short cracks with a lit right lip
    for cx, cy, ln in (LEFT_CRACKS if L else RIGHT_CRACKS):
        x = cx
        for k in range(ln):
            y = cy + k
            if k and hsh(cx, y, seed + 6) < 0.3:
                x += 1 if hsh(cx, y, seed + 7) < 0.55 else -1
            if inb(x, y) and m[y, x] and hard[band[y, x]]:
                c.put(x, y, 'K0')
                v = c.get(x + 1, y)
                if v and v[0] == 'R' and v[1:].isdigit() and m[y, x + 1]:
                    c.put(x + 1, y, 'R%d' % min(4, int(v[1:]) + 1))
    # the silhouette: the right wall's ledges take the rose rim, the left wall a dark outline
    for y in range(0, G.WALL_FOOT + 1):
        r = rows[y]
        if len(r) == 0:
            continue
        if L:
            c.put(r.max(), y, 'K0')
        else:
            x = r.min()
            b = band[y, x]
            c.put(x, y, 'R4' if hard[b] else 'R1')
            if hard[b] and inb(x + 1, y) and m[y, x + 1] and c.get(x + 1, y) in ('R1', 'R2'):
                c.put(x + 1, y, 'R3')
    return m


def left_fall_setting(c):
    """the lip the left fall pours over, the notch it comes from, the ledge it breaks on, wet rock
    beside it and moss in the spray"""
    f, f2 = G.LEFT_FALL, G.LEFT_FALL2
    notch = """
...kkkkkkkkk...
.kkKKKKKKKKKkk.
kKKKKKKKKKKKKKk
"""
    stamp(c, notch, {'k': 'R0', 'K': 'K0'}, f['x0'] - 3, f['y0'] - 5)
    lip = """
..RRRRRRRRRRR.
.RrrrrrrrrrrrR
"""
    stamp(c, lip, {'R': 'R2', 'r': 'R1'}, f['x0'] - 3, f['y0'] - 2)
    for ff in (f, f2):
        for y in range(ff['y0'] + 3, ff['y1']):
            k = (y - ff['y0']) / max(1, ff['y1'] - ff['y0'])
            grow = int(k * k * 3 + 0.5)
            for x, p in ((ff['x0'] - grow - 2, 0.45), (ff['x0'] - grow - 3, 0.2), (ff['x1'] + grow + 1, 0.45),
                         (ff['x1'] + grow + 2, 0.2)):
                if hsh(x, y, 91) < p:
                    c.put(x, y, 'R0')
    moss = [(f2['x0'] - 13, 108, 7, 3), (f2['x1'] + 4, 112, 5, 4), (f2['x0'] - 9, 96, 3, 2),
            (f2['x1'] + 3, 99, 4, 2), (f2['x0'] - 16, 117, 8, 3), (f['x1'] + 3, 60, 4, 2)]
    for mx, my, mw, mh in moss:
        for yy in range(my, my + mh):
            for xx in range(mx, mx + mw):
                e = ((xx - mx - mw / 2) / (mw / 2)) ** 2 + ((yy - my - mh / 2) / (mh / 2 + .3)) ** 2
                if e < 1.1 and hsh(xx, yy, 92) < 0.85:
                    c.put(xx, yy, 'G1' if yy == my or hsh(xx, yy, 93) < 0.3 else 'G0')
        c.put(mx + 1, my, 'G2')


def right_fall_break(c):
    """the rock the right fall breaks on, between its two tiers"""
    f = G.RIGHT_FALL
    brk = """
..HHHHHHH...
.HhhhhhhhHH.
khhhhhhhhhhk
.kkkkkkkkkk.
"""
    stamp(c, brk, {'H': 'H2', 'h': 'H1', 'k': 'H0'}, f['x0'] - 2, f['y1'] - 1)


FERN = """
.g..g.
gGg.Gg
.gGGg.
..ggg.
"""


def ferns(c):
    for x, y in ((74, 119), (112, 120), (150, 121)):
        stamp(c, FERN, {'g': 'G0', 'G': 'G2'}, x, y)


def ledge(c):
    """the left bridge anchor: a shelf on the left wall"""
    art = """
RRRRRRRRRRRRRRRRR
rrrrrrrrrrrrrrrrrr
.kkkkkkkkkkkkkkkk
..kkk..kkkk..kk..
"""
    stamp(c, art, {'R': 'R2', 'r': 'R1', 'k': 'K0'}, 44, 83)


# ================================================================ the forge (hero)
def forge(c):
    x0, y0, x1, y1 = G.DOOR                    # opening [220, 238) x [84, 107)
    fx0, fy0, fx1, fy1 = G.FRAME
    # stone frame: voussoir arch and jamb blocks, seams dark, lit by the fire on the inside
    for y in range(fy0, fy1):
        for x in range(fx0, fx1):
            c.put(x, y, 'R2')
    blocks_y = [80, 84, 89, 95, 100, 104, 108]
    for y in blocks_y[1:-1]:
        for x in list(range(fx0, x0)) + list(range(x1, fx1)):
            c.put(x, y, 'K0')
    for x in (fx0 + 2, x1 + 2):
        for y in range(84, 108):
            if (y // 5) % 2 == 0:
                c.put(x, y, 'K0')
    # the arch: opening top rounded
    cx = (x0 + x1 - 1) / 2.0
    op = np.zeros((H, W), bool)
    for y in range(y0 - 2, y1):
        for x in range(x0, x1):
            dy = (y0 + 4) - y
            if dy > 0 and ((x - cx) / ((x1 - x0) / 2.0)) ** 2 + (dy / 6.0) ** 2 > 1:
                continue
            op[y, x] = True
    # voussoirs over the arch
    for k, ang in enumerate(np.linspace(np.pi, 0, 9)):
        for r in range(9, 13):
            x = int(round(cx + np.cos(ang) * r * 1.05))
            y = int(round(y0 + 4 - np.sin(ang) * r * 0.62))
            if inb(x, y) and not op[y, x]:
                c.put(x, y, 'K0' if r == 12 or k % 2 == 0 and r == 9 else ('R3' if x < cx else 'R2'))
    c.put(int(cx), y0 - 5, 'R4')
    c.put(int(cx) + 1, y0 - 5, 'R3')
    # interior, hand-typed: warm back wall, the hood over the hearth fire (back right), lit hearth
    # bricks, and the anvil silhouette in front against the glow
    c.fill(op, 'F0')
    INTERIOR = """
000000111111100000
000011111111111100
000111111112211110
001111111222222110
011111112222222211
011111122222222221
111111222222332222
111112222233333322
111122223333333332
111222223333333332
112222222333333322
122222222233333221
1222222222kkkkkkkk
2kkkkkkkk22RRRRRRR
22kkkkkkk22rrrrrrr
1222kkkk222kkkkkkk
1122kkk2221rrrrrrr
1112kkk21111111111
111kkkkk1111111111
11kkkkkkk111111111
110000000011111111
111111111111111111
"""
    key = {'0': 'F0', '1': 'F1', '2': 'F2', '3': 'F3', 'k': 'I0', 'i': 'I1', 'r': 'FR0', 'R': 'FR1'}
    for j, row in enumerate(INTERIOR.strip().split('\n')):
        for i, ch in enumerate(row.strip()):
            if op[y0 + j, x0 + i]:
                c.put(x0 + i, y0 + j, key[ch])
    edge = op & ~(np.roll(op, 1, 0) & np.roll(op, 1, 1) & np.roll(op, -1, 1))
    c.fill(edge & (YY < y0 + 2), 'F0')
    # warm rim: the stones touching the opening, and the threshold
    ring = np.zeros((H, W), bool)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0)):
        ring |= np.roll(np.roll(op, dy, 0), dx, 1)
    ring &= ~op & (XX >= fx0) & (XX < fx1) & (YY >= fy0) & (YY < fy1)
    for y, x in zip(*np.nonzero(ring)):
        v = c.get(x, y)
        c.put(x, y, 'FR1' if v != 'K0' and abs(x - cx) > 6 and y > y0 + 6 else ('FR0' if v != 'K0' else 'K0'))
    for x in range(x0 - 1, x1 + 1):
        c.put(x, y1, 'FR1')
    return op


def door_leaf(c):
    """the leaf swung outward to the left: planks in perspective, inner face lit by the fire;
    it hangs one pixel off square at its outer end"""
    x_h = G.DOOR[0] - 1                        # hinge column
    for x in range(x_h - 8, x_h + 1):
        t = (x_h - x) / 8.0
        top = int(round(84 + 2.4 * t))
        bot = int(round(106 - 1.2 * t)) + (1 if x == x_h - 8 else 0)
        for y in range(top, bot + 1):
            if x == x_h - 8 or y in (top, bot):
                s = 'B0'
            elif (x_h - x) % 3 == 0:
                s = 'B1'                                      # plank seam
            else:
                s = 'FR1' if (x_h - x) < 3 else 'FR0'
            c.put(x, y, s)
        # iron straps
        for yy in (top + 4, bot - 4):
            if top < yy < bot:
                c.put(x, yy, 'I0')


def landing(c):
    x0, y0, x1, y1 = G.LANDING               # [196, 253) x [106, 111)
    widths = [3, 4, 3, 3, 4, 2, 4, 3, 3, 4, 3, 4, 3, 3, 4, 3, 2, 4]
    x = x0
    for i, wd in enumerate(widths):
        for xx in range(x, min(x1, x + wd)):
            lit = 214 <= xx <= 244
            for y in (y0, y0 + 1):
                if xx == x + wd - 1:
                    s = 'B0'
                elif y == y0:
                    s = ('FR1' if 218 <= xx <= 239 else 'FR0') if lit else ('B3' if i % 3 else 'B2')
                else:
                    s = 'FR0' if lit else 'B2'
                c.put(xx, y, s)
        x += wd
        if x >= x1:
            break
    for xx in range(x0, x1):
        c.put(xx, y0 + 2, 'FR0' if 216 <= xx <= 242 else 'B1')
        c.put(xx, y0 + 3, 'B1')
        c.put(xx, y0 + 4, 'K0')
    # brackets into the wall below
    for bx, d in ((200, 1), (247, -1)):
        for k in range(10):
            c.put(bx + d * (k // 2), y1 + k, 'B1')
            c.put(bx + d * (k // 2) + 1, y1 + k, 'B0')
    # ladder down to the bank
    for y in range(y1, 132):
        c.put(250, y, 'B2')
        c.put(253, y, 'B1')
        if (y - y1) % 4 == 2:
            for xx in (251, 252):
                c.put(xx, y, 'B3')


def props(c):
    # quench barrel right of the door, lit on its left by the fire
    barrel = """
.kkkk.
kFbbbk
kIIIIk
kFbbbk
kFbbbk
kIIIIk
.kkkk.
"""
    stamp(c, barrel, {'k': 'B0', 'b': 'B2', 'F': 'FR1', 'I': 'I1'}, 241, 99)
    # charcoal sacks, slumped, left of the bridge post on the landing
    sacks = """
..kk...
.kSSk..
kSsSSkk
kSsSSsk
"""
    stamp(c, sacks, {'k': 'K0', 'S': 'I1', 's': 'B1'}, 196, 102)
    # a horseshoe on the left jamb, lit by the spill
    shoe = """
k.k
k.k
.k.
"""
    stamp(c, shoe, {'k': 'I0'}, 216, 92)


def chimney(c):
    x0, y0, x1, y1 = G.CHIMNEY               # [242, 250) x [46, 84)
    for y in range(y0 + 2, y1):
        for x in range(x0, x1):
            s = 'R3' if x == x0 else 'R0' if x == x1 - 1 else 'R2'
            if (y - y0) % 9 == 0 or (y - y0) % 9 == 5 and x > x0 + 3:
                s = 'K0'
            elif (y - y0) % 9 == 1 and x < x1 - 2:
                s = 'R3' if x <= x0 + 1 else 'R2'
            if (y // 9) % 2 and x == x0 + 4 and (y - y0) % 9 not in (0, 1):
                s = 'K0'                                    # offset joints
            c.put(x, y, s)
    # cap
    for x in range(x0 - 1, x1 + 1):
        c.put(x, y0, 'I1' if x < x1 - 1 else 'I0')
        c.put(x, y0 + 1, 'I0')
    # the crack, with embers glowing in it
    crack = [(246, 57), (245, 58), (245, 59), (246, 60), (246, 61), (245, 62), (246, 63)]
    for x, y in crack:
        c.put(x, y, 'K0')
    for x, y in ((245, 60), (246, 59), (247, 62)):
        c.put(x, y, 'F0')
    c.put(246, 61, 'F1')


# ================================================================ bridge and lantern
def handrail_y(x):
    (x0, y0), (x1, y1) = (G.BRIDGE_L[0], G.BRIDGE_L[1] - 8), (G.BRIDGE_R[0], G.BRIDGE_R[1] - 8)
    t = (x - x0) / (x1 - x0)
    return y0 + (y1 - y0) * t + 14 * 4 * t * (1 - t) * (1.15 - 0.3 * t)


def bridge(c):
    xl, xr = G.BRIDGE_L[0], G.BRIDGE_R[0]
    missing = range(127, 131)
    broken_x = 131
    widths = [3, 2, 3, 3, 2, 3, 4, 2, 3, 3, 2, 3, 3, 4, 2, 3, 3, 2, 3, 3, 2, 4, 3, 2, 3, 3, 3, 2,
              3, 4, 2, 3, 3, 2, 3, 3, 4, 2, 3, 3, 2, 3, 3, 2, 4, 3, 3, 2, 3, 3, 2, 3, 4, 3, 2, 3]
    x, i = xl, 0
    deck = {}
    while x < xr:
        wd = widths[i % len(widths)]
        for xx in range(x, min(xr, x + wd)):
            y = int(round(G.deck_y(xx)))
            deck[xx] = y
            if xx in missing:
                c.put(xx, y + 1, 'B0')                     # the bottom rope still runs under the gap
                continue
            seam_px = xx == x + wd - 1
            near_forge = xx >= 196
            c.put(xx, y - 1, 'B0' if seam_px else ('FR0' if near_forge else 'B3'))
            c.put(xx, y, 'B0' if seam_px else ('B2' if hsh(i, 5) < 0.75 else 'B1'))
            c.put(xx, y + 1, 'B0')
        x += wd
        i += 1
    # the broken plank hanging below the gap
    by = deck.get(broken_x, 96)
    for k, (dx, s) in enumerate([(0, 'B2'), (0, 'B2'), (1, 'B1'), (1, 'B2'), (1, 'B1')]):
        c.put(broken_x + dx, by + 2 + k, s)
    c.put(broken_x + 2, by + 6, 'B0')
    # handrail rope: sags lower on the left
    hy = {}
    pts = c.catenary(xl + 1, int(round(handrail_y(xl + 1))), xr, int(round(handrail_y(xr))), 0, 'B0')
    for xx in range(xl + 1, xr + 1):
        y = int(round(handrail_y(xx)))
        hy[xx] = y
    # redraw the rope from the custom curve (the catenary above only set the ends)
    prev = None
    for xx in range(xl + 1, xr + 1):
        y = hy[xx]
        c.put(xx, y, 'B0')
        if prev is not None and abs(y - prev) > 1:
            for yy in range(min(y, prev) + 1, max(y, prev)):
                c.put(xx, yy, 'B0')
        prev = y
    # suspender cords, mismatched spacing; one snapped
    cords = [57, 63, 70, 76, 84, 89, 97, 104, 110, 118, 123, 134, 141, 147, 155, 160, 168, 175, 181,
             189, 194, 200]
    snapped = 147
    for cx in cords:
        y0, y1 = hy[cx] + 1, deck[cx] - 2
        if cx == snapped:
            y1 = y0 + 3
        for y in range(y0, y1 + 1):
            c.put(cx, y, 'B1')
    # posts
    for (px, top, bot) in ((xl - 1, 73, 84), (xr - 1, 76, 106)):
        for y in range(top, bot):
            c.put(px, y, 'B3' if px < 100 else 'FR0')
            c.put(px + 1, y, 'B1')
        c.put(px, top - 1, 'B2')
        c.put(px + 1, top - 1, 'B0')
    # rope lashings at the posts
    for (px, y) in ((xl - 1, 80), (xl - 1, 81), (xr - 1, 96), (xr - 1, 97), (xr - 1, 101)):
        c.put(px, y, 'B2')


def lantern(c):
    # the iron arm from the right post, a short chain, and the lantern
    px = G.BRIDGE_R[0] - 1
    for x in range(197, px):
        c.put(x, 77, 'I0')
    c.put(197, 76, 'I0')
    c.put(196, 76, 'I0')                       # the curl at the arm's end
    for y in (78, 80):
        c.put(198, y, 'I0')
    c.put(199, 79, 'I0')
    art = """
.ooo.
oiiio
ooooo
oL1Lo
o122o
oL22o
oLLLo
ooooo
.o.o.
"""
    stamp(c, art, {'o': 'I0', 'i': 'I1', 'L': 'L0', '1': 'L1', '2': 'L2'}, 196, 81)
    # warm rim on the post and the nearest cords
    for y in range(80, 92):
        c.put(px, y, 'L0' if y % 3 else 'FR0')
    for (x, y) in ((194, 92), (194, 93), (200, 92), (189, 92)):
        if c.get(x, y) == 'B1':
            c.put(x, y, 'L0')


# ================================================================ build
def build():
    c = Canvas(W, H, 'S0')
    sky(c)
    cloud(c)
    bolt(c)
    mesa(c)
    rain(c)
    rock_step(c)
    wall(c, 'R')
    wall(c, 'L')
    left_fall_setting(c)
    w = water(c)
    river_glints(c, w)
    reflections(c, w)
    banks(c, w)
    fall(c, G.RIGHT_FALL, 'WB', hi_edge=None, lo_edge=None, flare=1, seed=17, foot=False)
    fall(c, G.RIGHT_FALL2, 'WB', hi_edge=None, lo_edge=None, flare=2, seed=23, lip=False)
    fall(c, G.LEFT_FALL, 'WA', hi_edge=None, lo_edge=None, flare=2, seed=5, foot=False)
    fall(c, G.LEFT_FALL2, 'WA', hi_edge=None, lo_edge=None, flare=4, seed=9, lip=False)
    spray(c, 96.5, 72, 10, 6, 'WA', 141)            # the left fall breaks on its ledge: a crown, not a step
    spray(c, 129.5, 100, 8, 5, 'WB', 151)
    foam(c, w)
    ferns(c)
    ledge(c)
    chimney(c)
    forge(c)
    door_leaf(c)
    landing(c)
    props(c)
    bridge(c)
    lantern(c)
    return c


if __name__ == '__main__':
    import palettes as PP
    from PIL import Image
    c = build()
    bad = sorted({v for v in c.g.ravel() if v not in PP.INDEX})
    print('unknown slots:', bad)
