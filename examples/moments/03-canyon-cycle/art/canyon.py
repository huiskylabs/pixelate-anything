"""Canyon Cycle: the one index map (320x180), drawn back to front into a slot canvas.

Every pixel holds a slot name from palettes.SLOTS. Motion never redraws a pixel: the falls, the
river reaches and the stars are drawn in their cycling ranges (WA, WB, RA, RB, T), the rain and the
bolt in switched slots, the forge and lantern in flicker slots. Positions and shapes are placed by
hand (geo.py and the tables below); the code rasterises and shades them.
"""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/03-canyon-cycle/art')
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
SKY_STOPS = [('S0', 0), ('S1', 23, 12), ('S2', 33, 10), ('S3', 42, 10), ('S4', 72, 14), ('S5', 88, 12)]

# stars: hand-placed (x, y, slot); two clusters and a loose arc, on solid S0 only (y < 17)
STARS = [(104, 3, 'T2'), (108, 9, 'T0'), (111, 5, 'T1'), (116, 12, 'T0'), (113, 15, 'T1'),
         (121, 2, 'T0'), (126, 7, 'T2'), (130, 4, 'T1'), (124, 13, 'T0'), (137, 10, 'T1'),
         (141, 2, 'T0'), (147, 6, 'T1'), (183, 3, 'T0'), (189, 7, 'T1'), (192, 2, 'T2'),
         (197, 5, 'T0'), (201, 10, 'T1'), (205, 3, 'T0'), (171, 2, 'T1'), (163, 4, 'T0'),
         (156, 1, 'T1'), (118, 6, 'T1')]


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
    """the storm cell at sunset: a flat anvil whose top still holds the rose light, a cauliflower
    tower lit on its upper-left billows, a dark flat belly. Billows hand-placed, very different
    radii; each has a lit rim, a cap, a body and a crease where it sits on an earlier one."""
    total = np.zeros((H, W), bool)
    anv = c.mask_poly([(121, 12), (127, 8), (140, 6), (158, 5), (178, 6), (198, 6), (217, 7), (217, 14),
                       (204, 14), (190, 16), (176, 18), (166, 22), (156, 23), (140, 20), (126, 17)])
    c.fill(anv, 'C1')
    out = ~anv
    up = np.roll(out, 1, 0) | np.roll(out, 2, 0)
    c.fill(anv & up & (XX < 200), 'C2')
    c.fill(anv & np.roll(out, 1, 0) & (XX < 182), 'C3')
    c.fill(anv & (np.roll(out, -1, 0) | np.roll(out, -2, 0)) & (XX > 160), 'C0')
    total |= anv
    billows = [  # cx, cy, r (x stretch 1.25): back to front, right to left on the lit flank
        (170, 30, 11), (160, 22, 8), (150, 15, 6), (157, 34, 10), (143, 22, 10), (134, 13, 5),
        (138, 31, 7), (127, 25, 6), (147, 40, 9), (126, 37, 8), (119, 42, 5), (184, 37, 9),
        (197, 41, 6)]
    for cx, cy, r in billows:
        m = (((XX - cx) / (1.25 * r)) ** 2 + ((YY - cy) / r) ** 2 < 1) & (YY < 49)
        hi = cy < 30
        lobe_shade(c, m, 'C3' if hi else 'C2', 'C2' if hi else 'C1', 'C1', 'C0', total)
        total |= m
    belly = c.mask_poly([(108, 47), (114, 42), (130, 41), (160, 40), (186, 41), (202, 43), (207, 47),
                         (196, 49), (170, 49), (150, 50), (126, 49)])
    c.fill(belly & ~total, 'C0')
    out = ~(total | belly)
    low = np.zeros_like(total)
    for s in range(1, 5):
        low |= np.roll(out, -s, 0)
    c.fill((total | belly) & low & (YY > 33), 'C0')
    total |= belly
    # a darker heart in the lower tower so the mass reads heavy, not hollow
    heart = total & (YY > 30) & (YY < 44) & (XX > 140) & (XX < 190) & ~low
    c.fill(heart & np.isin(c.g, ['C1']), 'C1')
    for (x0, x1, y) in ((112, 120, 50), (127, 132, 51), (171, 178, 50), (189, 193, 50)):
        for x in range(x0, x1):
            c.put(x, y, 'C0')
    return total


def mesa(c):
    m = G.poly(G.MESA)
    b = G.poly(G.BUTTE)
    cap = m & (YY < 77)
    talus = m & (YY >= 77)
    # the caprock cliff: lit left third, shadowed right, two strata seams; talus split by gullies
    c.fill(cap, 'M1')
    c.fill(cap & (XX < 149), 'M2')
    c.fill(cap & (XX > 182), 'M0')
    c.fill(talus, 'M1')
    c.fill(talus & (XX < 141), 'M2')
    c.fill(talus & (XX > 178), 'M0')
    for x in range(129, 193):
        col = np.nonzero(m[:, x])[0]
        if len(col):
            c.put(x, col.min(), 'M3' if x < 176 else 'M2')
            if x < 150:
                c.put(x, col.min() + 1, 'M3' if x < 140 else 'M2')
    for (x0, x1, y) in ((131, 140, 68), (151, 163, 67), (176, 190, 69), (143, 171, 72)):
        for x in range(x0, x1):
            if m[y, x]:
                v = c.get(x, y)
                c.put(x, y, {'M2': 'M1', 'M1': 'M0', 'M0': 'M0', 'M3': 'M1'}[v])
    # the overhang shadow where the talus starts
    for x in range(127, 196):
        if m[77, x]:
            c.put(x, 77, 'M0' if x > 136 else 'M1')
    # vertical joints in the caprock face, lit lip to their right on the sunny side
    for jx, y0, y1 in ((136, 64, 75), (145, 66, 76), (184, 65, 74)):
        for y in range(y0, y1):
            if m[y, jx]:
                c.put(jx, y, 'M0')
                if jx < 150 and m[y, jx + 1]:
                    c.put(jx + 1, y, 'M3')
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
    """the strike: a jagged 1 px path with one branch, only over solid S3"""
    path = [(142, 47), (142, 48), (141, 49), (140, 50), (140, 51), (141, 52), (142, 53), (141, 54),
            (140, 55), (139, 56), (139, 57), (138, 58), (137, 59), (138, 60), (137, 61), (136, 62)]
    branch = [(142, 53), (143, 54), (144, 55), (144, 56), (145, 57), (146, 58), (146, 59)]
    for x, y in path + branch:
        if c.get(x, y) == 'S3':
            c.put(x, y, 'BL')


def rain(c):
    """faint streaks under the storm, drawn once; visible only when the rain slots are on"""
    on = {'S3': 'RS3', 'C0': 'RC0', 'M0': 'RM0', 'M1': 'RM1'}
    n = 0
    for i in range(500):
        x = 110 + int(100 * hsh(i, 11))
        y = 42 + int(56 * hsh(i, 12))
        ln = 2 + int(3 * hsh(i, 13))
        if hsh(i, 14) < 0.35:
            continue
        hit = 0
        for k in range(ln):
            xx, yy = x - (k + (y % 3)) // 3, y + k
            v = c.get(xx, yy) if inb(xx, yy) else None
            if v in on:
                c.put(xx, yy, on[v])
                hit += 1
        n += hit > 0
        if n >= 70:
            break


# ================================================================ middle plane
def rock_step(c):
    m = G.step_mask()
    c.fill(m, 'H1')
    f = G.RIGHT_FALL
    joints = [101, 110, 118, 129, 137, 146, 158, 166, 196, 203, 209]
    for jx in joints:
        top = next((y for y in range(85, 124) if m[y, jx]), 124)
        ln = 6 + int(12 * hsh(jx, 1))
        for y in range(top + 1, min(124, top + ln)):
            c.put(jx, y, 'H0')
            if m[y, jx + 1] and hsh(jx, y) < 0.8:
                c.put(jx + 1, y, 'H2')
    for (x0, x1, y) in ((97, 126, 104), (131, 152, 101), (156, 172, 103), (192, 212, 106),
                        (99, 118, 114), (124, 141, 112), (148, 168, 115), (194, 206, 113)):
        for x in range(x0, x1):
            if m[y, x]:
                c.put(x, y, 'H0')
                if m[y - 1, x] and c.get(x, y - 1) == 'H1' and hsh(x, y, 2) < 0.5:
                    c.put(x, y - 1, 'H2')
    for x in range(96, 215):
        top = next((y for y in range(85, 124) if m[y, x]), None)
        if top is not None:
            c.put(x, top, 'H2')
    # wet dark rock either side of the right fall, ragged
    for y in range(f['y0'] + 2, 124):
        for x in (f['x0'] - 1, f['x0'] - 2, f['x1'], f['x1'] + 1):
            if m[y, x] and hsh(x, y, 9) < (0.85 if x in (f['x0'] - 1, f['x1']) else 0.4):
                c.put(x, y, 'H0')
    return m


def fall(c, f, rng_name, hi_edge, lo_edge, flare, seed, foot=True, lip=True):
    """a fall in a 6-slot cycling range: each column keeps its own phase and streak length, so the
    rotation makes streaks fall at 10 fps. Edges bulge a pixel here and there; hi_edge / lo_edge
    are static edge slots (broken, never a ruled line)."""
    x0, x1, y0, y1 = f['x0'], f['x1'], f['y0'], f['y1']
    col_phase = {x: int(24 * hsh(x, seed)) for x in range(x0 - 8, x1 + 9)}
    col_seg = {x: 3 + int(3 * hsh(x, seed + 1)) for x in range(x0 - 8, x1 + 9)}
    m = np.zeros((H, W), bool)
    for y in range(y0, y1):
        k = (y - y0) / max(1, y1 - y0)
        grow = int(k * k * flare + 0.5)
        a, b = x0 - grow, x1 - 1 + grow
        seg = (y - y0) // 6
        if hsh(seg, seed + 3) < 0.3:
            a -= 1
        if hsh(seg, seed + 4) < 0.3:
            b += 1
        for x in range(a, b + 1):
            ph = col_phase[x] + (7 if hsh(x, y // 9, seed + 2) < 0.25 else 0)
            s = '%s%d' % (rng_name, ((y + ph) // col_seg[x]) % 6)
            if x == a and hi_edge and hsh(x, y, seed + 7) < 0.75:
                s = hi_edge
            elif x == b and lo_edge and hsh(x, y, seed + 8) < 0.8:
                s = lo_edge
            c.put(x, y, s)
            m[y, x] = True
    if lip:
        for kk, y in enumerate((y0, y0 + 1)):
            for x in range(x0 - 1, x1 + 1):
                c.put(x, y, 'N1' if (kk == 0 and hsh(x, seed + 12) < 0.45) else '%s%d' % (rng_name, (x + 2 * kk) % 6))
    if foot:
        # a churning crown, wider than the fall, taller in the middle; foam at its skirts
        grow = flare
        a, b = x0 - grow - 4, x1 + grow + 3
        mid = (a + b) / 2.0
        for x in range(a, b + 1):
            hgt = int(6 - 4.5 * abs(x - mid) / ((b - a) / 2.0) + 2 * hsh(x, seed + 5))
            for y in range(y1 - hgt, y1 + 2):
                s = '%s%d' % (rng_name, int(6 * hsh(x, y, seed + 6)))
                if (x in (a, b) or y == y1 - hgt) and hsh(x, y, seed + 9) < 0.5:
                    s = 'N0'
                c.put(x, y, s)
    return m


# ================================================================ water
def water(c):
    pool = G.poly(G.POOL)
    river = G.poly(G.RIVER)
    w = pool | river
    tmp = Canvas(W, H, None)
    tmp.bands(118, 180, [('V2', 118), ('V1', 147, 10), ('V0', 166, 12)])
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
                ln = [2, 3, 5, 3, 7, 4, 2, 6][int(8 * hsh(x, y, seed + 1))]
                ph = int(5 * hsh(x, y, seed + 2))
                for k in range(ln):
                    xx = x + k
                    if xx < end and c.get(xx, y) in ('V0', 'V1', 'V2'):
                        c.put(xx, y, '%s%d' % (name, (ph + (sign * xx) // 2) % 5))
                gap = 5 + int(16 * hsh(x, y, seed + 3)) + (9 if hsh(y, x // 30, seed + 4) < 0.3 else 0)
                x += ln + gap


def foam(c, w):
    """static foam dashes drifting from the falls' feet, mismatched lengths"""
    dashes = [(54, 127, 4, 'N1'), (60, 129, 3, 'N0'), (73, 127, 5, 'N0'), (50, 130, 2, 'N0'),
              (69, 131, 3, 'N1'), (79, 129, 2, 'N0'), (85, 131, 4, 'N0'), (167, 126, 4, 'N0'),
              (173, 128, 6, 'N1'), (188, 127, 3, 'N0'), (193, 126, 5, 'N1'), (181, 130, 3, 'N0'),
              (198, 129, 2, 'N0'), (163, 129, 2, 'N0'), (190, 132, 4, 'N0'), (175, 133, 2, 'N0')]
    for x, y, ln, s in dashes:
        for k in range(ln):
            if w[y, x + k]:
                c.put(x + k, y, s)


def reflections(c, w):
    """the forge and lantern in the water: broken warm dashes under them (flicker slots)"""
    for (x0, x1, y0, y1, s1, s0) in ((222, 236, 126, 133, 'F1', 'F0'), (196, 201, 125, 132, 'L1', 'L0')):
        for y in range(y0, y1):
            for x in range(x0, x1):
                if not w[y, x]:
                    continue
                k = hsh(x, y, 61)
                if (y - y0) % 2 == 0 and k < 0.55:
                    c.put(x, y, s1 if (k < 0.2 and y < y0 + 4) else s0)


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
# strata: (top y, kind) top to bottom; 'hard' bands protrude, take a lit lip and shade the band below
LEFT_STRATA = [(0, 'soft'), (10, 'hard'), (24, 'soft'), (31, 'hard'), (49, 'soft'), (58, 'hard'),
               (66, 'soft'), (84, 'hard'), (90, 'soft'), (108, 'hard'), (118, 'soft')]
RIGHT_STRATA = [(0, 'hard'), (9, 'soft'), (27, 'hard'), (36, 'soft'), (46, 'hard'), (59, 'soft'),
                (77, 'soft'), (110, 'hard'), (119, 'soft')]
# long fissures, as distance from the inner edge; each wanders and stops at a stratum
LEFT_FISSURES = [(12, 0, 58), (27, 10, 90), (49, 0, 49), (55, 66, 127), (78, 24, 108), (90, 84, 127)]
RIGHT_FISSURES = [(9, 0, 46), (21, 46, 127), (38, 0, 77), (63, 9, 110), (88, 27, 127), (101, 0, 36)]


def wall(c, side):
    """canyon sandstone in planes: strata bands with wavy bounds (hard bands lighter, jutting 3-5 px
    into the gap with a lit lip; soft bands recessed and shaded under the lip above), a few long
    fissures with a lit right lip, varnish streaks hanging from the lips, darker toward the frame
    edge. The right wall takes the rose sun on its inner faces; the left wall is in shadow."""
    L = side == 'L'
    strata = LEFT_STRATA if L else RIGHT_STRATA
    fiss = LEFT_FISSURES if L else RIGHT_FISSURES
    knots = G.LEFT_EDGE if L else G.RIGHT_EDGE
    seed = 300 if L else 500
    xs = np.arange(W)
    bounds = [np.zeros(W, int)] + [np.round(y + seam(xs, 'wave', (2.5, 1.0), seed + 11 * i)
                                            ).astype(int) for i, (y, k) in enumerate(strata) if i]
    band = np.zeros((H, W), int)
    for i in range(1, len(bounds)):
        band += YY >= bounds[i][None, :]
    kind = np.array([k == 'hard' for y, k in strata])
    jut = np.array([(3 + int(3 * hsh(i, seed))) if k == 'hard' else -int(2 * hsh(i, seed + 1))
                    for i, (y, k) in enumerate(strata)])
    edge = np.array([G.edge_x(knots, y) for y in range(H)])
    m = np.zeros((H, W), bool)
    for y in range(G.WALL_FOOT + 2):
        for x in range(W):
            e = edge[y] + (jut[band[y, x]] if L else -jut[band[y, x]])
            m[y, x] = x < e if L else x >= e
    m = shapes.fray(m, teeth=0.16, notches=0.10, islands=0.0, depth=2, seed=seed, facing=(1, 0) if L else (-1, 0))
    m &= YY <= G.WALL_FOOT + 1
    e_row = np.array([np.nonzero(m[y])[0].max() if L and m[y].any() else
                      (np.nonzero(m[y])[0].min() if m[y].any() else 0) for y in range(H)])
    dist = (e_row[:, None] - XX) if L else (XX - e_row[:, None])
    # fissure masks (wandering lines at a distance from the edge)
    fis = np.zeros((H, W), bool)
    for d0, ya, yb in fiss:
        off = 0
        for y in range(ya, min(yb, G.WALL_FOOT + 1)):
            if hsh(d0, y, seed + 5) < 0.16:
                off += 1 if hsh(d0, y, seed + 6) < 0.5 else -1
            x = (edge[y] - d0 - off) if L else (edge[y] + d0 + off)
            if 0 <= x < W:
                fis[y, x] = True
    for y in range(G.WALL_FOOT + 2):
        for x in range(W):
            if not m[y, x]:
                continue
            b = band[y, x]
            d = dist[y, x]
            hard = kind[b]
            # which column (between fissures) this pixel is in, counted from the gap
            col = sum(1 for d0, ya, yb in fiss if ya <= y < yb and d > d0)
            if L:
                tone = 2 if d < 5 else 1 if d < 40 else 0
                tone += 1 if hard and d < 64 else 0
                tone = min(2, tone)
            else:
                tone = 3 if col == 0 else 2 if col == 1 else 1 if col <= 3 else 0
                if not hard:
                    tone = max(0, tone - 1)
                if d > 96:
                    tone = 0
            s = 'R%d' % tone
            top = y == bounds[b][x] if b else False
            if top and hard:
                s = 'R%d' % min(4, tone + (2 if (not L and col == 0) else 1))
            if b and not hard and kind[b - 1] and y == bounds[b][x]:
                s = 'K0' if tone <= 1 else 'R%d' % (tone - 1)       # shade under the lip above
            c.put(x, y, s)
    # fissures: dark line, lit right lip (the light comes from the left)
    for y, x in zip(*np.nonzero(fis & m)):
        c.put(x, y, 'K0')
        if inb(x + 1, y) and m[y, x + 1]:
            v = c.get(x + 1, y)
            if v[0] == 'R' and v[1:].isdigit():
                c.put(x + 1, y, 'R%d' % min(4, int(v[1:]) + 1))
    # varnish streaks hanging from the hard lips: 1 px, mismatched length, sparse
    for i in range(1, len(strata)):
        if not kind[i]:
            continue
        x = int(10 * hsh(i, seed + 8))
        while x < W:
            yb = bounds[i][x] + 2
            ln = 3 + int(9 * hsh(x, i, seed + 9))
            for y in range(yb, yb + ln):
                if inb(x, y) and m[y, x] and band[y, x] == i:
                    v = c.get(x, y)
                    if v[0] == 'R' and v[1:].isdigit() and int(v[1:]) > 0:
                        c.put(x, y, 'R%d' % (int(v[1:]) - 1))
            x += 5 + int(13 * hsh(x, i, seed + 10))
    # grain: sparse flake dashes in the mid tones
    body = m & np.isin(c.g, ['R1', 'R2']) & (dist > 3)
    texture.flakes(c, body, 'R', base=1, cell=(15, 8), cluster=0.3, gate=0.4, length=(3, 6),
                   stack=(1, 2), lit_end=1, shadow=True, steps=5, seed=seed + 1)
    # the silhouette edge: the right wall takes the rose sun rim, the left wall a dark outline
    for y in range(0, G.WALL_FOOT + 1):
        row = np.nonzero(m[y])[0]
        if len(row) == 0:
            continue
        if not L:
            x = row.min()
            c.put(x, y, 'R4' if kind[band[y, x]] or hsh(x, y, seed) < 0.6 else 'R3')
        else:
            c.put(row.max(), y, 'K0')
    return m


def left_fall_setting(c):
    """the cleft the left fall leaves from, the ledge it splashes on, wet rock, moss in the spray"""
    f, f2 = G.LEFT_FALL, G.LEFT_FALL2
    cleft = """
...kkkkkkkk...
.kkKKKKKKKKkk.
kKKKKKKKKKKKKk
"""
    stamp(c, cleft, {'k': 'R0', 'K': 'K0'}, f['x0'] - 4, f['y0'] - 3)
    # the ledge between the tiers: a jutting shelf with a lit lip and a shadow under it
    bump = """
..RRRR...
.RrrrrRR.
krrrrrrrk
.kkrrrkk.
...kkk...
"""
    stamp(c, bump, {'R': 'R2', 'r': 'R1', 'k': 'K0'}, f['x1'] - 3, f['y1'] - 1)
    # wet rock beside both tiers: ragged, darker, not a ruled outline
    for ff in (f, f2):
        for y in range(ff['y0'] + 2, ff['y1']):
            k = (y - ff['y0']) / max(1, ff['y1'] - ff['y0'])
            grow = int(k * k * 2 + 0.5)
            for x, p in ((ff['x0'] - grow - 2, 0.45), (ff['x0'] - grow - 3, 0.2), (ff['x1'] + grow + 1, 0.45),
                         (ff['x1'] + grow + 2, 0.2)):
                if hsh(x, y, 91) < p:
                    c.put(x, y, 'R0')
    # moss patches in the spray, low on the wall near the foot, mismatched
    moss = [(f2['x0'] - 12, 108, 7, 3), (f2['x1'] + 4, 112, 5, 4), (f2['x0'] - 9, 97, 3, 2),
            (f2['x1'] + 3, 100, 4, 2), (f2['x0'] - 15, 117, 8, 3), (f2['x1'] + 5, 119, 7, 3),
            (f['x1'] + 3, 52, 4, 2)]
    for mx, my, mw, mh in moss:
        for yy in range(my, my + mh):
            for xx in range(mx, mx + mw):
                e = ((xx - mx - mw / 2) / (mw / 2)) ** 2 + ((yy - my - mh / 2) / (mh / 2 + .3)) ** 2
                if e < 1.1 and hsh(xx, yy, 92) < 0.85:
                    c.put(xx, yy, 'G1' if yy == my or hsh(xx, yy, 93) < 0.3 else 'G0')
        c.put(mx + 1, my, 'G2')


FERN = """
.g..g.
gGg.Gg
.gGGg.
..ggg.
"""


def ferns(c):
    for x, y in ((47, 120), (80, 119), (206, 120)):
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
0001111111kkkkk110
0011111111kkkkkk10
0111111112kkkkkk10
0111111122kkkkkkk1
1111111222kkkkkkk1
111111222iiiiiiiii
111112222233333322
111122223333333332
111222223333333332
112222222233333322
122222222rRrRRrRr2
2kkkkkkkk2krrkrrk2
22kkkkkkk2rRrrRrr1
1222kkkk22krrkrrk1
1122kkk22211111111
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
            if (y - y0) % 6 == 0:
                s = 'K0' if x < x1 - 1 else 'K0'
            elif (y - y0) % 6 == 1 and x < x1 - 2:
                s = 'R3' if x <= x0 + 1 else 'R2'
            if (y // 6) % 2 and x == x0 + 4 and (y - y0) % 6 not in (0, 1):
                s = 'K0'                                    # offset joints
            if (y // 6) % 2 == 0 and x == x0 + 2 and (y - y0) % 6 not in (0, 1):
                s = 'K0'
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
    cl = cloud(c)
    bolt(c)
    rain(c)
    mesa(c)
    rain(c)
    rock_step(c)
    w = water(c)
    fall(c, G.RIGHT_FALL, 'WB', hi_edge=None, lo_edge=None, flare=2, seed=17)
    river_glints(c, w)
    foam(c, w)
    reflections(c, w)
    banks(c, w)
    wall(c, 'R')
    wall(c, 'L')
    left_fall_setting(c)
    fall(c, G.LEFT_FALL, 'WA', hi_edge=None, lo_edge=None, flare=1, seed=5, foot=False)
    fall(c, G.LEFT_FALL2, 'WA', hi_edge=None, lo_edge=None, flare=3, seed=9)
    # the splash on the ledge between the tiers
    f = G.LEFT_FALL
    for x in range(f['x0'] - 4, f['x1'] + 4):
        hgt = 3 - abs(x - (f['x0'] + f['x1']) // 2) // 3 + int(2 * hsh(x, 95))
        for y in range(f['y1'] - hgt, f['y1'] + 1):
            c.put(x, y, 'WA%d' % int(6 * hsh(x, y, 96)) if hsh(x, y, 97) < 0.8 else 'N0')
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
