"""Trees: a cherry (blossom / green / autumn / bare), a young tree, and a pine.
Branches are hand-placed polylines; canopies are hand-placed clumps."""
from artlib import Grid, line, rng, bayer

# ------------------------------------------------------------------ helpers
def thick_line(g, pts, t0, t1, shade=True, only_empty=False):
    """polyline whose thickness tapers from t0 to t1; lit on the left."""
    segs = list(zip(pts, pts[1:]))
    total = sum(max(abs(b[0] - a[0]), abs(b[1] - a[1])) for a, b in segs) or 1
    run = 0
    for a, b in segs:
        for (x, y) in line(a[0], a[1], b[0], b[1]):
            u = run / total
            t = t0 + (t1 - t0) * u
            w = max(1, int(round(t)))
            xs = range(x - (w - 1) // 2, x + w // 2 + 1)
            for i, xx in enumerate(xs):
                if only_empty and g.get(xx, y) is not None:
                    continue
                if w == 1:
                    v = 'B1'
                elif w == 2:
                    v = 'B2' if i == 0 else 'B0'
                else:
                    if i == 0:
                        v = 'B2'
                    elif i == w - 1:
                        v = 'K0'
                    elif i == w - 2:
                        v = 'B0'
                    else:
                        v = 'B1'
                g.set(xx, y, v)
            run += 1
        run -= 1


def bumpy_disc(cx, cy, r, seed):
    """a disc whose rim wobbles a little, so clumps never look compass-drawn."""
    R = rng(seed)
    bumps = [R() * 1.4 - 0.4 for _ in range(8)]
    pts = set()
    import math
    n = int(r) + 3
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            ang = (math.atan2(dy, dx) + math.pi) / (2 * math.pi) * 8
            i0 = int(ang) % 8
            f = ang - int(ang)
            rr = r + bumps[i0] * (1 - f) + bumps[(i0 + 1) % 8] * f
            if dx * dx + dy * dy <= (rr + 0.3) ** 2:
                pts.add((cx + dx, cy + dy))
    return pts


def canopy(g, clumps, ramp, seed, holes=(), sparkle=0.0, sparkle_slot=None, marks=1.0):
    """Leaf masses lit as one crown (top-left) with scalloped overlaps.
    clumps are back-to-front; no dithering, clean tone clusters."""
    import math
    R = rng(seed)
    d0, d1, m, l, hi = ramp
    owner = {}
    for idx, (cx, cy, r) in enumerate(clumps):
        for p in bumpy_disc(cx, cy, r, seed * 31 + idx):
            owner[p] = idx
    xs = [p[0] for p in owner]; ys = [p[1] for p in owner]
    gx0, gx1, gy0, gy1 = min(xs), max(xs), min(ys), max(ys)
    gcx, gcy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
    grx, gry = max(1, (gx1 - gx0) / 2), max(1, (gy1 - gy0) / 2)
    tone = {}
    for (x, y), idx in owner.items():
        cx, cy, r = clumps[idx]
        loc = -(((x - cx) / r) * 0.55 + ((y - cy) / r) * 0.84)
        glo = -(((x - gcx) / grx) * 0.42 + ((y - gcy) / gry) * 0.9)
        v = 0.62 * loc + 0.55 * glo
        if v > 0.62:   t = 3
        elif v > 0.18: t = 2
        elif v > -0.38: t = 1
        else:          t = 0
        # scallop: a clump's lower edge sitting on a clump in front darkens
        below = owner.get((x, y + 1))
        if below is not None and below > idx:
            t = min(t, 1) if t > 1 else 0
        # outer silhouette, lower-right side: darkest
        if (x, y + 1) not in owner or (x + 1, y) not in owner:
            if v < 0.25:
                t = 0
        tone[(x, y)] = t
    ramp4 = [d0, d1, m, l]
    for (x, y), t in tone.items():
        g.set(x, y, ramp4[t])
    # leaf marks: tiny lit strokes in mid tones, dark strokes in shadow
    taken = []
    for _ in range(int(900 * marks)):
        x = int(R() * g.w); y = int(R() * g.h)
        if (x, y) not in owner or any(abs(x - a) < 4 and abs(y - b) < 3 for a, b in taken):
            continue
        t = tone[(x, y)]
        if t in (1, 2) and tone.get((x + 1, y)) == t and tone.get((x, y + 1)) in (t, t - 1):
            g.set(x, y, ramp4[t + 1]); g.set(x + 1, y, ramp4[t + 1])
            if tone.get((x - 1, y + 1)) is not None:
                g.set(x - 1, y + 1, ramp4[max(0, t - 1)])
            taken.append((x, y))
    if sparkle and sparkle_slot:
        n = 0
        for _ in range(4000):
            if n >= int(120 * sparkle):
                break
            x = int(R() * g.w); y = int(R() * g.h)
            if tone.get((x, y)) == 3 and tone.get((x, y - 1)) in (3, 2) and tone.get((x + 1, y)) == 3:
                if any(abs(x - a) < 3 and abs(y - b) < 3 for a, b in taken):
                    continue
                g.set(x, y, sparkle_slot); taken.append((x, y)); n += 1
    for (x, y) in holes:
        for (hx, hy) in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1), (x + 2, y), (x + 1, y - 1)):
            g.set(hx, hy, None)
    return owner


# ------------------------------------------------------------------ cherry
CH_W, CH_H = 90, 96
CH_BASE = (42, 95)
TRUNK = [(42, 95), (42, 88), (43, 80), (44, 72), (44, 66)]
BRANCHES = [
    ([(44, 70), (37, 63), (29, 57), (20, 52), (10, 49)], 4, 1),
    ([(44, 66), (40, 56), (37, 46), (35, 35), (34, 24)], 4, 1),
    ([(44, 66), (49, 56), (54, 46), (59, 36), (62, 27)], 4, 1),
    ([(45, 71), (54, 65), (64, 60), (74, 56), (82, 53)], 3, 1),
    ([(44, 66), (45, 55), (46, 44), (46, 32), (45, 19)], 3, 1),
    ([(29, 57), (25, 49), (22, 41)], 2, 1),
    ([(20, 52), (14, 55), (7, 57)], 1, 1),
    ([(37, 46), (31, 38), (25, 30)], 2, 1),
    ([(35, 35), (30, 28), (27, 20)], 1, 1),
    ([(34, 24), (37, 16), (39, 11)], 1, 1),
    ([(54, 46), (61, 44), (68, 40)], 2, 1),
    ([(59, 36), (55, 28), (52, 21)], 1, 1),
    ([(62, 27), (66, 21), (68, 15)], 1, 1),
    ([(64, 60), (68, 52), (70, 45)], 1, 1),
    ([(74, 56), (79, 49), (81, 43)], 1, 1),
    ([(46, 44), (50, 36), (53, 30)], 1, 1),
    ([(46, 32), (42, 25), (40, 18)], 1, 1),
    ([(10, 49), (5, 45), (3, 41)], 1, 1),
    ([(22, 41), (17, 36), (14, 31)], 1, 1),
    ([(68, 40), (74, 35), (77, 30)], 1, 1),
]
TWIGS = [[(3, 41), (2, 38)], [(3, 41), (0, 42)], [(14, 31), (12, 27)], [(14, 31), (17, 28)],
         [(25, 30), (23, 26)], [(25, 30), (28, 26)], [(27, 20), (25, 16)], [(27, 20), (30, 17)],
         [(39, 11), (38, 7)], [(39, 11), (42, 8)], [(45, 19), (44, 14)], [(45, 19), (48, 15)],
         [(52, 21), (50, 17)], [(52, 21), (55, 18)], [(68, 15), (70, 11)], [(68, 15), (66, 11)],
         [(77, 30), (80, 27)], [(77, 30), (79, 33)], [(81, 43), (84, 40)], [(81, 43), (84, 45)],
         [(82, 53), (86, 51)], [(82, 53), (85, 56)], [(70, 45), (73, 43)], [(7, 57), (3, 58)],
         [(53, 30), (56, 27)], [(40, 18), (37, 15)], [(22, 41), (20, 44)], [(62, 27), (60, 23)],
         [(37, 63), (33, 66)], [(54, 65), (58, 69)], [(29, 57), (32, 52)], [(64, 60), (62, 56)]]
CLUMPS = [
    # back / top
    (30, 22, 8), (44, 17, 9), (58, 21, 8), (70, 29, 7), (18, 30, 7), (24, 17, 4), (66, 14, 4), (44, 9, 4),
    # second
    (10, 40, 6), (22, 36, 9), (36, 30, 10), (51, 30, 10), (64, 36, 9), (77, 42, 6), (3, 44, 3), (86, 47, 3),
    # third
    (6, 50, 5), (17, 47, 8), (31, 43, 9), (46, 42, 9), (60, 45, 9), (73, 50, 7), (83, 54, 4),
    # front, low and drooping at the sides
    (12, 58, 6), (25, 55, 7), (38, 53, 6), (52, 54, 7), (65, 57, 7), (78, 60, 5), (6, 62, 3), (85, 62, 3),
]
BLOOM_DROP = {7, 14, 22, 26, 29}
FALL_DROP = {5, 7, 14, 15, 22, 29, 30}
HOLES = [(30, 42), (58, 34), (47, 56), (18, 46), (71, 47), (38, 22)]
BLOOM_HOLES = HOLES + [(24, 50), (62, 50), (52, 26), (12, 38)]
FALL_HOLES = HOLES + [(24, 48), (60, 46), (50, 24), (12, 40), (34, 34), (66, 30), (42, 46), (20, 56), (74, 54), (56, 58)]
LRAMP = ['L0', 'L1', 'L2', 'L3', 'L4']


ROOTS = [(36, 94, 'B1'), (37, 94, 'B2'), (47, 94, 'B0'), (48, 94, 'K0'), (38, 93, 'B2'),
         (46, 93, 'B0'), (35, 95, 'K0'), (36, 95, 'B1'), (37, 95, 'B2'), (48, 95, 'K0'), (47, 95, 'B0'),
         (49, 95, 'K0'), (42, 82, 'B0'), (43, 82, 'B0'), (42, 83, 'K0'), (44, 76, 'B2')]


def cherry_branches():
    g = Grid(CH_W, CH_H)
    for b in BRANCHES:
        thick_line(g, *b)
    for t in TWIGS:
        thick_line(g, t, 1, 1)
    thick_line(g, TRUNK, 8, 6)
    for (x, y, v) in ROOTS:
        g.set(x, y, v)
    return g


def cherry(variant):
    g = cherry_branches()
    if variant == 'bare':
        return g
    drop = {'fall': FALL_DROP, 'bloom': BLOOM_DROP}.get(variant, set())
    clumps = [c for i, c in enumerate(CLUMPS) if i not in drop]
    cg = Grid(CH_W, CH_H)
    canopy(cg, clumps, LRAMP, seed={'full': 5, 'bloom': 6, 'fall': 9}[variant],
           holes={'bloom': BLOOM_HOLES, 'fall': FALL_HOLES}.get(variant, HOLES),
           sparkle={'full': 0.35, 'bloom': 1.0, 'fall': 0.4}[variant], sparkle_slot='L4',
           marks=1.0 if variant != 'bloom' else 0.6)
    g.paste(cg, 0, 0)
    # trunk and limbs below the crown sit in front of it
    lower = Grid(CH_W, CH_H)
    for b in BRANCHES[:5]:
        thick_line(lower, b[0][:2], b[1], b[1])
    thick_line(lower, TRUNK, 8, 6)
    for (x, y, v) in ROOTS:
        lower.set(x, y, v)
    for y in range(60 if variant != 'fall' else 52, CH_H):
        for x in range(CH_W):
            v = lower.get(x, y)
            if v is not None:
                g.set(x, y, v)
    if variant == 'fall':
        # limbs show through the thinned crown
        b = cherry_branches()
        for y in range(CH_H):
            for x in range(CH_W):
                if g.get(x, y) is None and b.get(x, y) is not None:
                    g.set(x, y, b.get(x, y))
    return g


def cherry_snow():
    """snow resting along the upper side of the thicker limbs only."""
    g = Grid(CH_W, CH_H)
    for b in BRANCHES:
        if b[1] >= 2:
            pts = b[0]
            thick_line(g, pts[:max(2, len(pts) - 1)], b[1], max(2, b[2]))
    thick_line(g, TRUNK, 8, 6)
    s = Grid(CH_W, CH_H)
    for y in range(2, 72):
        for x in range(CH_W):
            if g.get(x, y) is not None and g.get(x, y - 1) is None:
                s.set(x, y - 1, 'N2' if (x % 5) else 'N1')
    return s


# ------------------------------------------------------------------ young birch
YT_W, YT_H = 36, 54
YT_BASE = (17, 53)
def birch_trunk(g):
    # pale bark with dark marks, a slight lean to the left
    pts = [(17, 53), (17, 46), (16, 38), (16, 30), (15, 22)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for (x, y) in line(x0, y0, x1, y1):
            g.set(x - 1, y, 'H3'); g.set(x, y, 'H2'); g.set(x + 1, y, 'K1')
    for (x, y) in [(16, 50), (17, 44), (15, 39), (17, 35), (15, 28), (16, 25), (17, 48), (15, 33)]:
        g.set(x, y, 'K0')
    for b in ([(16, 34), (11, 28), (7, 24)], [(16, 31), (21, 26), (26, 22)], [(15, 24), (13, 17), (12, 11)],
              [(15, 26), (19, 19), (22, 13)], [(7, 24), (4, 21)], [(26, 22), (29, 19)], [(12, 11), (10, 7)],
              [(22, 13), (24, 9)], [(11, 28), (8, 30)], [(21, 26), (25, 28)]):
        thick_line(g, b, 1, 1)


def young_tree(variant):
    g = Grid(YT_W, YT_H)
    birch_trunk(g)
    if variant == 'bare':
        return g
    clumps = [(10, 22, 5), (24, 20, 6), (16, 13, 6), (9, 30, 4), (25, 29, 4), (17, 23, 6), (20, 8, 3), (6, 17, 3)]
    if variant == 'fall':
        clumps = [clumps[i] for i in (0, 2, 3, 5, 6)]
    cg = Grid(YT_W, YT_H)
    canopy(cg, clumps, ['G0', 'G1', 'G2', 'G3', 'G3'], seed=21 if variant != 'fall' else 23,
           holes=[(14, 18)] if variant != 'fall' else [(14, 18), (20, 14)])
    g.paste(cg, 0, 0)
    lower = Grid(YT_W, YT_H)
    birch_trunk(lower)
    for y in range(33, YT_H):
        for x in range(YT_W):
            if lower.get(x, y) is not None:
                g.set(x, y, lower.get(x, y))
    if variant == 'fall':
        b = Grid(YT_W, YT_H); birch_trunk(b)
        for y in range(YT_H):
            for x in range(YT_W):
                if g.get(x, y) is None and b.get(x, y) is not None:
                    g.set(x, y, b.get(x, y))
    return g


def young_snow():
    g = young_tree('bare')
    s = Grid(YT_W, YT_H)
    for y in range(1, 40):
        for x in range(YT_W):
            if g.get(x, y) is not None and g.get(x, y - 1) is None and (x + y) % 2 == 0:
                s.set(x, y - 1, 'N2')
    return s


# ------------------------------------------------------------------ pine
PN_W, PN_H = 40, 88
PN_BASE = (19, 87)
TIERS = [  # y_top, half width at the bottom, height (hand tuned, a little uneven)
    (0, 2, 7), (4, 5, 9), (10, 6, 9), (16, 9, 11), (24, 10, 11), (32, 13, 13), (42, 14, 12),
    (51, 17, 14), (62, 18, 12)]
def pine(snow=False):
    g = Grid(PN_W, PN_H)
    R = rng(3)
    # trunk
    for y in range(70, PN_H):
        g.set(18, y, 'B2'); g.set(19, y, 'B1'); g.set(20, y, 'B0'); g.set(21, y, 'K0')
    g.set(17, PN_H - 1, 'B1'); g.set(22, PN_H - 1, 'K0')
    for i, (y0, hw, h) in enumerate(TIERS):
        lean = (len(TIERS) - i) // 3          # top leans a little to the right
        cx = 19 + lean
        for r in range(h):
            y = y0 + r
            half = max(0, int(round(hw * (r + 1) / h)))
            # droop: the tier tips hang down at the ends
            for x in range(cx - half, cx + half + 1):
                d = (x - cx) / max(1, half)
                if r == h - 1 and abs(d) < 0.35 and i > 0:
                    continue                    # notch under the middle of each tier
                if abs(d) > 0.85 and r < h - 3:
                    continue
                if d < -0.35:
                    v = 'P3' if (r < 2 or (d < -0.6 and r < h - 3)) else 'P2'
                elif d < 0.15:
                    v = 'P2' if r < h - 2 else 'P1'
                elif d < 0.6:
                    v = 'P1'
                else:
                    v = 'P0'
                if r == h - 1:
                    v = 'P0' if d > -0.5 else 'P1'
                g.set(x, y, v)
            # bough tips hang one pixel lower at the far ends
        g.set(cx - hw, y0 + h, 'P1'); g.set(cx + hw, y0 + h, 'P0')
        g.set(cx - hw + 1, y0 + h, 'P2')
    # needles texture: short dark strokes
    for _ in range(140):
        x = int(R() * PN_W); y = int(R() * 70)
        if g.get(x, y) in ('P2', 'P1') and g.get(x + 1, y + 1) in ('P2', 'P1'):
            g.set(x, y, 'P1' if g.get(x, y) == 'P2' else 'P0')
    if not snow:
        return g
    s = Grid(PN_W, PN_H)
    for y in range(1, 72):
        for x in range(PN_W):
            if g.get(x, y) is not None and g.get(x, y - 1) is None:
                s.set(x, y, 'N3' if (x < 16 and y > 8) else 'N2')
                if g.get(x, y + 1) is not None and x < 20 and bayer(x, y) < 8:
                    s.set(x, y + 1, 'N1')
    return s


def export():
    return [
        ('sprite', 'cherry_full', [cherry('full')], CH_BASE[0], CH_BASE[1]),
        ('sprite', 'cherry_bloom', [cherry('bloom')], CH_BASE[0], CH_BASE[1]),
        ('sprite', 'cherry_fall', [cherry('fall')], CH_BASE[0], CH_BASE[1]),
        ('sprite', 'cherry_bare', [cherry('bare')], CH_BASE[0], CH_BASE[1]),
        ('sprite', 'cherry_snow', [cherry_snow()], CH_BASE[0], CH_BASE[1]),
        ('sprite', 'young_full', [young_tree('full')], YT_BASE[0], YT_BASE[1]),
        ('sprite', 'young_fall', [young_tree('fall')], YT_BASE[0], YT_BASE[1]),
        ('sprite', 'young_bare', [young_tree('bare')], YT_BASE[0], YT_BASE[1]),
        ('sprite', 'young_snow', [young_snow()], YT_BASE[0], YT_BASE[1]),
        ('sprite', 'pine', [pine()], PN_BASE[0], PN_BASE[1]),
        ('sprite', 'pine_snow', [pine(True)], PN_BASE[0], PN_BASE[1]),
    ]


if __name__ == '__main__':
    import artlib
    pals = artlib.load_palettes()
    for sname, var in (('spring', 'bloom'), ('summer', 'full'), ('fall', 'fall'), ('winter', 'bare')):
        gs = [cherry(var), young_tree('full' if var in ('full', 'bloom') else var), pine()]
        if sname == 'winter':
            c = cherry('bare'); c.paste(cherry_snow(), 0, 0)
            y = young_tree('bare'); y.paste(young_snow(), 0, 0)
            p = pine(); p.paste(pine(True), 0, 0)
            gs = [c, y, p]
        artlib.preview(gs, pals[sname], str(artlib.ROOT / 'shots' / ('trees_%s.png' % sname)), zoom=4)
