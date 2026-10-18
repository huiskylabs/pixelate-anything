"""The island: grassy cap draped over a cliff of stacked boulders, a pebble
beach under the dock, shore rocks and a worn path. All shapes, masses and
details are placed by hand; the code only rasterises and shades them."""
from artlib import Grid, rng, bayer

CW, CH = 480, 270
AXIS = 207

# back edge of the grass top (x, y)
TOP = [(95, 208), (98, 204), (101, 200), (105, 196), (109, 192), (114, 188), (119, 184), (125, 180),
       (132, 176), (140, 173), (148, 171), (156, 170), (164, 169), (172, 169), (180, 170), (188, 172),
       (196, 174), (204, 175), (214, 176), (292, 176), (300, 177), (308, 178), (316, 179), (323, 181),
       (329, 183), (335, 185), (341, 188), (347, 191), (353, 194), (359, 197), (365, 200), (370, 203),
       (374, 206), (377, 208)]
# visible depth of the top strip
DEPTH = [(95, 1), (103, 3), (112, 5), (124, 7), (140, 8), (200, 9), (300, 9), (322, 8), (336, 6),
         (350, 4), (362, 3), (372, 2), (377, 1)]
WATER = [(95, 208), (140, 207), (200, 207), (260, 208), (320, 207), (377, 208)]


def interp(tab, x):
    if x <= tab[0][0]:
        return tab[0][1]
    for (x0, y0), (x1, y1) in zip(tab, tab[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return tab[-1][1]

def top(x):   return int(round(interp(TOP, x)))
def lip(x):   return top(x) + int(round(interp(DEPTH, x)))
def water(x): return int(round(interp(WATER, x)))

K = {'k': 'K0', 'K': 'K1', 's': 'R0', 't': 'R1', 'u': 'R2', 'U': 'R3',
     'g': 'G0', 'G': 'G1', 'h': 'G2', 'H': 'G3', 'b': 'B0', 'n': 'B1', 'm': 'B2', 'M': 'B3',
     'c': 'C0', 'C': 'C1'}

BEACH_X = 334

# hand-drawn shore boulders (U lit top, u top plane, t body, s shadow facet)
BOULDER_ART = {
'A': """
.....kkkkkkk......
...kkUUuuuuukk....
..kUuuuuuuuuttkk..
.kuuuuuuuttttttsk.
kuuutttttttttsssk.
kttttttttttssssssk
kttttttsssssssssKk
.kKKKKKKKKKKKKKKk.
""",
'B': """
....kkk....
..kkUuukk..
.kUuuuuttk.
.kuuutttsk.
kUuutttttsk
kuuttttttsk
kuutttttssk
ktttttttssk
kttttttsssk
ktttttssssk
.ktttsssskk
..kKKKKKKk.
""",
'C': """
....kkkkk....
..kkUUuuukk..
.kUuuuuuuttk.
kuuuuutttttsk
kuuutttttttsk
ktttttttttssk
kttttttttsssk
.kttttssssskk
..kKKKKKKKk..
""",
'D': """
..kkkkkkkkkk....
.kUUUuuuuuuukkk.
kuuuuuuuuuttttsk
kttttttttttttssk
ktttttttttsssssk
.ktttsssssssssk.
..kKKKKKKKKKKk..
""",
'E': """
..kkk..
.kUuuk.
kuuttsk
kttsssk
.kKKKk.
""",
'F': """
......kkkk....
....kkUuuukk..
..kkUuuuutttk.
.kUuuuuttttssk
kuuuuttttttssk
kuutttttttsssk
kttttttttssssk
ktttttttsssssk
.kttttsssssskk
..kKKKKKKKKk..
""",
}
# placements (shape, x, y of top-left); later ones overlap earlier ones
BOULDERS = [
    ('C', 93, 199), ('F', 104, 196), ('B', 118, 194), ('A', 128, 199), ('F', 146, 196), ('C', 158, 199),
    ('D', 170, 200), ('E', 186, 202), ('A', 192, 199), ('C', 209, 200), ('D', 222, 201), ('E', 238, 203),
    ('F', 245, 198), ('A', 258, 200), ('E', 275, 203), ('C', 281, 199), ('D', 293, 201), ('B', 309, 196),
    ('A', 318, 200), ('E', 158, 192), ('E', 228, 194), ('E', 300, 193),
]

# small pebbles in the soil: (x, y)
PEBBLES = [(128, 192), (147, 184), (160, 189), (183, 189), (196, 186), (219, 193), (243, 189),
           (268, 192), (276, 187), (298, 192), (318, 190), (153, 191), (205, 192), (229, 186)]

# horizontal soil streaks: (x0, x1, y)
STREAKS = [(118, 128, 191), (141, 152, 189), (165, 181, 192), (190, 204, 188), (216, 228, 191),
           (240, 252, 194), (262, 275, 189), (288, 300, 194), (305, 318, 188), (150, 161, 195),
           (183, 194, 196), (230, 241, 196), (272, 283, 196), (110, 116, 196)]

CRACKS = []

# moss / snow caps on boulder tops: (x0, x1, y)
CAPS = [(150, 155, 198), (121, 124, 196), (196, 201, 200), (249, 253, 200), (311, 314, 197),
        (108, 112, 198), (226, 231, 202)]

# grass drooping over the lip: (x0, x1, extra rows)
DROOP = [(110, 116, 2), (128, 133, 1), (143, 151, 3), (160, 166, 1), (176, 184, 2), (198, 203, 1),
         (226, 230, 1), (258, 263, 2), (285, 292, 1), (304, 309, 2), (319, 323, 1)]


def in_face(x, y):
    return lip(x) < y <= water(x) and x < BEACH_X + (0 if y < 200 else 6)


def boulder(g, x0, y0, w, h, rad, clip=True):
    """faceted stone: lit top plane, mid front, shadowed right facet."""
    rf = max(2, w // 4)
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            dx, dy = x - x0, y - y0
            bx, by = x0 + w - 1 - x, y0 + h - 1 - y
            cut = edge = False
            for (cx, cy) in ((dx, dy), (bx, dy), (dx, by), (bx, by)):
                if cx < rad and cy < rad:
                    d2 = (rad - cx - 0.5) ** 2 + (rad - cy - 0.5) ** 2
                    if d2 > (rad + 0.1) ** 2: cut = True
                    elif d2 > (rad - 0.9) ** 2: edge = True
            if cut or (clip and not (x < BEACH_X + 4 and y <= water(x) + 1)):
                continue
            if dx == 0 or dy == 0 or bx == 0 or by == 0:
                edge = True
            if edge:
                v = 'K1'
            elif dy == 1:
                v = 'R3' if dx <= max(2, w // 5) else 'R2'
            elif dy == 2 and bx > rf:
                v = 'R2' if bayer(x, y) < 8 else 'R1'
            elif bx <= rf - (1 if dy < 3 else 0):
                v = 'R0'
            elif dx == 1:
                v = 'R2'
            elif by == 1:
                v = 'R0'
            else:
                v = 'R1'
            g.set(x, y, v)


def build():
    g = Grid(CW, CH)
    xs = range(95, 378)
    # ---- face: dark soil under the grass, stones set into it ----
    for x in xs:
        l, w = lip(x), water(x)
        for y in range(l + 1, w + 1):
            if not in_face(x, y):
                continue
            r = y - l
            if r <= 1:
                v = 'K1'
            elif r == 2:
                v = 'K1' if bayer(x, y) < 10 else 'B0'
            elif r == 3:
                v = 'B0' if bayer(x, y) < 10 else 'B1'
            else:
                v = 'B1'
            g.set(x, y, v)
    # two soil strata cross the face: a dark seam with a lit ledge above it
    seams = [
        [(100, 196), (118, 192), (136, 190), (160, 191), (182, 193), (204, 192), (230, 194), (256, 193),
         (280, 195), (304, 194), (330, 196)],
        [(120, 199), (146, 196), (170, 197), (196, 198), (220, 197), (246, 199), (272, 198), (298, 199),
         (320, 200)],
    ]
    for seam in seams:
        for (x0, y0), (x1, y1) in zip(seam, seam[1:]):
            for x in range(x0, x1):
                y = int(round(y0 + (y1 - y0) * (x - x0) / (x1 - x0)))
                if g.get(x, y) in ('B1', 'B0'):
                    g.set(x, y, 'B0')
                    if g.get(x, y - 1) == 'B1' and (x % 9) not in (0, 4):
                        g.set(x, y - 1, 'B2')
                    if g.get(x, y + 1) == 'B1' and (x % 5) == 0:
                        g.set(x, y + 1, 'B0')
    for (x0, x1, y) in STREAKS:
        for x in range(x0, x1 + 1):
            if g.get(x, y) in ('B1', 'B0'):
                g.set(x, y, 'B0')
            if x0 + 1 < x < x1 - 1 and g.get(x, y - 1) == 'B1':
                g.set(x, y - 1, 'B2' if (x % 3 == 0) else 'B1')
    for (x, y) in PEBBLES:
        if g.get(x, y) in ('B1', 'B0', 'B2'):
            g.set(x, y, 'R2'); g.set(x + 1, y, 'R1')
            if g.get(x, y + 1) in ('B1', 'B0', 'B2'): g.set(x, y + 1, 'K1'); g.set(x + 1, y + 1, 'K1')
    # half-buried stones of a few sizes (hand placed)
    STONES = {
        'a': "kUuk\nkuttk\n.KKK",
        'b': ".kUk.\nkUutk\nkuttk\n.KKK.",
        'c': "kUk\nKKK",
        'd': ".kUuuk.\nkUuuttk\nkutttsk\n.KKKKK.",
    }
    for (name, x, y) in [('b', 128, 186), ('c', 146, 189), ('d', 166, 186), ('a', 190, 191), ('c', 214, 190),
                         ('b', 236, 193), ('c', 262, 191), ('d', 284, 188), ('a', 306, 192), ('c', 322, 194),
                         ('a', 112, 195), ('c', 176, 196), ('c', 250, 196), ('b', 296, 196)]:
        rows = STONES[name].split('\n')
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == '.':
                    continue
                if g.get(x + i, y + j) in ('B0', 'B1', 'B2', 'K1'):
                    g.set(x + i, y + j, K[ch])
    # roots hanging out of the face under the trees
    ROOTS = [[(150, 0), (150, 1), (151, 2), (151, 3), (152, 4), (152, 5)],
             [(158, 0), (157, 1), (157, 2), (156, 3)],
             [(166, 0), (166, 1), (167, 2), (167, 3), (168, 4), (169, 5), (169, 6)],
             [(174, 0), (175, 1), (175, 2)],
             [(119, 0), (119, 1), (118, 2), (118, 3)],
             [(318, 0), (318, 1), (319, 2), (319, 3), (320, 4)], [(326, 0), (325, 1), (325, 2)]]
    for rt in ROOTS:
        for (x, dy) in rt:
            y = lip(x) + 2 + dy
            if g.get(x, y) in ('B0', 'B1', 'B2', 'K1'):
                g.set(x, y, 'B2' if dy < 3 else 'B3')
    # small tufts growing sideways out of ledges
    for (x, y) in [(138, 193), (204, 195), (268, 194), (312, 197), (124, 197)]:
        for (dx, dy, v) in ((0, 0, 'G1'), (1, -1, 'G2'), (2, -1, 'G2'), (1, 0, 'G0'), (-1, -1, 'G2')):
            if g.get(x + dx, y + dy) in ('B0', 'B1', 'B2', 'K1'):
                g.set(x + dx, y + dy, v)
    for (name, x, y) in BOULDERS:
        g.stamp(BOULDER_ART[name], K, x, y)
    for (x0, x1, y) in CAPS:
        for x in range(x0, x1 + 1):
            if g.get(x, y) in ('R2', 'R3'):
                g.set(x, y, 'G2' if x in (x0, x1) else 'G3')
            if g.get(x, y + 1) in ('R2', 'R1') and x0 < x < x1:
                g.set(x, y + 1, 'G1')
    # wet band at the waterline with a cool sheen
    for x in xs:
        w = water(x)
        if g.get(x, w) is not None:
            g.set(x, w, 'K1')
        if g.get(x, w - 1) in ('R1', 'R2', 'R0'):
            g.set(x, w - 1, 'R0')
        if g.get(x, w - 2) in ('R1', 'R2') and x % 7 in (0, 1, 2):
            g.set(x, w - 2, 'C0')
    # ---- beach: sand and pebbles under the dock ----
    for x in range(BEACH_X - 6, 378):
        for y in range(lip(x), water(x) + 1):
            if g.get(x, y) is not None and x < BEACH_X:
                continue
            r = y - lip(x)
            if y >= water(x):
                v = 'R0'
            elif r == 0:
                v = 'B3'
            elif r < 3:
                v = 'B2'
            else:
                v = 'B2' if bayer(x, y) < 5 else 'B1'
            g.set(x, y, v)
    PEB = ".kk.\nkUtk\n.ks."
    for (x, y) in [(339, 196), (345, 199), (351, 197), (356, 201), (343, 203), (361, 203), (349, 204),
                   (366, 204), (336, 201), (370, 205)]:
        g.stamp(PEB, K, x - 2, y - 1)
    # ---- grass cap ----
    for x in xs:
        t, l = top(x), lip(x)
        for y in range(t, l + 1):
            r = y - t
            if r == 0:
                v = 'G2'
            elif y == l:
                v = 'G0'
            elif r == 1:
                v = 'G2' if bayer(x, y) < 6 else 'G1'
            elif y == l - 1:
                v = 'G1' if bayer(x, y) < 10 else 'G0'
            else:
                v = 'G1'
            if x >= BEACH_X and y == l:
                v = 'G1'
            g.set(x, y, v)
    for (x0, x1, n) in DROOP:
        for x in range(x0, x1 + 1):
            edge = x in (x0, x1)
            depth = n - (1 if edge else 0)
            for i in range(1, depth + 1):
                g.set(x, lip(x) + i, 'G0' if i == depth else 'G1')
            g.set(x, lip(x) + depth + 1, 'K1')
    # darker grass clumps on the strip
    for (cx, cy, w) in [(140, 177, 6), (166, 175, 8), (196, 180, 5), (226, 181, 7), (306, 181, 6),
                        (322, 185, 4), (152, 176, 4), (270, 180, 5), (124, 183, 4)]:
        for dx in range(-w, w + 1):
            if g.get(cx + dx, cy) == 'G1':
                g.set(cx + dx, cy, 'G0' if abs(dx) > w - 2 else 'G1')
            if abs(dx) < w - 1 and g.get(cx + dx, cy + 1) == 'G1':
                g.set(cx + dx, cy + 1, 'G0')
    # ---- worn path: porch steps -> along the strip -> beach ----
    path = [(244, 1), (248, 2), (252, 3), (258, 4), (266, 5), (276, 5), (288, 5), (300, 5), (310, 4),
            (318, 4), (326, 3), (332, 2), (338, 1)]
    for i in range(len(path) - 1):
        (x0, r0), (x1, r1) = path[i], path[i + 1]
        for x in range(x0, x1):
            r = r0 + (r1 - r0) * (x - x0) / (x1 - x0)
            yc = top(x) + int(round(r))
            for dy in (-1, 0, 1):
                y = yc + dy
                if not (top(x) < y < lip(x) - 1):
                    continue
                v = 'B2' if dy == 0 else ('B2' if (dy == -1 and x % 6) else 'B1')
                g.set(x, y, v)
    for (x, y) in [(262, 180), (281, 181), (297, 181), (313, 182), (327, 184)]:
        if g.get(x, y) in ('B2', 'B1'):
            g.set(x, y, 'B3')
    # ---- shore rocks standing in the water ----
    ROCK_BIG = """
...kkkkkk....
.kkUUuuuukk..
kUuuuuutttk..
kuuutttttssk.
ktttttttsssk.
kttttssssssk.
.kKKKKKKKKKk.
"""
    ROCK_MID = """
..kkkkk..
.kUuuutk.
kuuutttsk
kttttsssk
.kKKKKKk.
"""
    ROCK_SMALL = """
.kkk.
kUutk
ktssk
.kKk.
"""
    for art, x, y in [(ROCK_BIG, 86, 202), (ROCK_SMALL, 100, 205), (ROCK_MID, 372, 203),
                      (ROCK_SMALL, 384, 206), (ROCK_SMALL, 160, 206), (ROCK_MID, 284, 204)]:
        g.stamp(art, K, x, y)
    # tufts standing proud of the back edge
    tufts = {'a': ".H.H\nhGhG", 'b': "..H..\n.hGH.\nhGGGh", 'c': "H.\nGh", 'd': ".H..H.\nhGHhGh"}
    for name, x in [('b', 112), ('a', 124), ('d', 134), ('c', 146), ('a', 182), ('b', 194), ('c', 202),
                    ('d', 300), ('a', 312), ('b', 326), ('c', 338)]:
        t = tufts[name].split('\n')
        g.stamp(tufts[name], K, x, top(x + 1) - len(t) + 1)
    return g


if __name__ == '__main__':
    import artlib
    pals = artlib.load_palettes()
    g = build()
    c, ox, oy = g.crop()
    print('island crop', ox, oy, c.w, c.h, 'orphans', c.count_orphans())
    for sname in ('summer', 'winter', 'fall', 'spring'):
        artlib.preview(c, pals[sname], str(artlib.ROOT / 'shots' / ('island_%s.png' % sname)), zoom=4,
                       bg=pals[sname]['E1'])


def export():
    g = build()
    c, ox, oy = g.crop()
    return [('sprite', 'island', [c], 0, 0), ('const', 'ISLAND_POS', '[%d, %d]' % (ox, oy))]
