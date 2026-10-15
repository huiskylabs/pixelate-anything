"""The cottage: hand-drawn parts layered like Aseprite layers."""
from artlib import Grid, line

W, H = 82, 64

# shared key for hand-drawn cottage parts
K = {
    'k': 'K0', 'K': 'K1', 'j': 'K2',
    'q': 'F0', 'r': 'F1', 'R': 'F2', 'T': 'F3',
    'b': 'B0', 'n': 'B1', 'm': 'B2', 'M': 'B3',
    'h': 'H0', 'w': 'H1', 'W': 'H2', 'X': 'H3',
    's': 'R0', 't': 'R1', 'u': 'R2', 'U': 'R3',
    '1': 'WL0', '2': 'WL1', '3': 'WL2', '4': 'WL3',
    'c': 'C0', 'C': 'C1', 'g': 'G0', 'G': 'G1',
    'a': 'A2', 'A': 'A5', 'e': 'N0',
}

CHIMNEY = """
.kkkkkkkkk.
kUUUuuuuutk
kuuuttttssk
.kkkkkkkkk.
.kUutstuts.
.kuttsttss.
.ksssssssk.
.kuutsuutk.
.kttssttsk.
.ksssssssk.
.kUuttstuk.
.kutttstsk.
.ksssssssk.
.kuusuttsk.
.kttsttssk.
.ksssssssk.
.kuuttsutk.
.kttsttssk.
.ksssssssk.
.kutsuttsk.
.kttstttsk.
.ksssssssk.
.kuuttsutk.
.kttsttssk.
"""

WINDOW = """
..kkkkkkkkkkk..
.knnnnnnnnnnnk.
.kn2333b3332nk.
.kn3334b4333nk.
.kn3344b4433nk.
.kn3344b4433nk.
.knbbbbbbbbbnk.
.kn3444b4443nk.
.kn3444b4443nk.
.kn3344b4433nk.
.kn2333b3332nk.
kMMM1M1MM1MMMMk
knnnnnnnnnnnnnk
.kkkkkkkkkkkkk.
"""

# left window has half-drawn curtains (a = fabric)
WINDOW_CURTAIN = """
..kkkkkkkkkkk..
.knnnnnnnnnnnk.
.kn2333b3332nk.
.kn2234b4322nk.
.kn2224b4222nk.
.kn2344b4432nk.
.knbbbbbbbbbnk.
.kn2444b4442nk.
.kn3444b4443nk.
.kn3344b4433nk.
.kn2333b3332nk.
kMMM1M1MM1MMMMk
knnnnnnnnnnnnnk
.kkkkkkkkkkkkk.
"""

SHUTTER = """
kkkk
kmnk
knnk
kbbk
kmnk
knnk
kbbk
kmnk
knnk
kbbk
kmnk
kkkk
"""

DOOR = """
.kkkkkkkkk.
kbbbbbbbbbk
kbmnmnmnmbk
kbmn343mnbk
kbmn444nmbk
kbmn343mnbk
kbmnmnmnmbk
kbbbbbbbbbk
kbmnmnmnmbk
kbmnmnmnmbk
kbmnmnm2mbk
kbmnmnmnmbk
kbmnmnmnmbk
kbbbbbbbbbk
kbmnmnmnmbk
kbmnmnmnmbk
kbmnmnmnmbk
k112111211k
"""

ROUND_WINDOW = """
..kkkkk..
.kk343kk.
.k34443k.
k3344433k
kbbbbbbbk
k3444443k
.k34443k.
.kk343kk.
..kkkkk..
"""

PORCH_ROOF = """
.kkkkkkkkkkkkkkkkkkkkkkk.
kTRRRRRRRRRRRRRRRRRRRRRRk
krrqrrrrrqrrrrrqrrrrrqrrk
kkkkkkkkkkkkkkkkkkkkkkkkk
..knk...............knk..
...k.................k...
"""

DECK = """
.kkkkkkkkkkkkkkkkkkkkkkkkkk.
kMMMM1M11M12111M11MMM1MMMMMk
knnnnbnnnnnnbnnnnnnnbnnnnnnk
kbbbbbbbbbbbbbbbbbbbbbbbbbbk
....kmmMmmmmMmmmmmmMmmk.....
....knnnnnnnnnnnnnnnnnk.....
.....kuUuuuuuUuuuuuuuk......
.....ktttttttttttttttk......
"""

RAIL = """
kmmmmmk
knnnnnk
.kn.kn.
.kn.kn.
.kn.kn.
.kn.kn.
.kn.kn.
"""

FOUNDATION = None   # built from hand-placed stone joints in foundation()


def roof(g):
    """Main hipped roof: hand-laid shingle courses (foreshortened toward the
    ridge), a slight ridge sag, a missing shingle and a newer patched one."""
    from artlib import rng
    R = rng(7)
    ridge, eave = 9, 33
    lx0, rx0 = 14, 67
    def sag(x):
        return 1 if 31 <= x <= 50 else 0
    def left(y):
        return lx0 - (y - ridge) // 2
    def right(y):
        return rx0 + (y - ridge) // 2
    # course heights from the ridge down (thinner near the ridge = depth)
    heights = [2, 2, 3, 3, 3, 3, 4]
    starts = []
    y = ridge + 3
    for hgt in heights:
        starts.append((y, hgt)); y += hgt
    # each course gets its own irregular shingle widths
    joints = []
    for ci in range(len(heights)):
        js, x = set(), 2 + (ci % 2) * 2 + int(R() * 2)
        while x < 80:
            js.add(x)
            x += 3 + int(R() * 4)
        joints.append(js)
    lit = {}
    for ci in range(len(heights)):
        for x in range(80):
            lit[(ci, x)] = R()
    for y in range(ridge, eave + 1):
        for x in range(left(y), right(y) + 1):
            s_ = sag(x)
            if y < ridge + s_:
                continue
            yy = y - s_
            if y == ridge + s_ or x == right(y) or y == eave or x == left(y):
                g.set(x, y, 'K0'); continue
            if x == left(y) + 1 and y < eave - 1:
                g.set(x, y, 'F3' if (y % 4) else 'F2'); continue
            if x == right(y) - 1:
                g.set(x, y, 'F0'); continue
            if yy == ridge + 1:
                g.set(x, y, 'F3' if (x % 4) in (0, 1) else 'F2'); continue
            if yy == ridge + 2:
                g.set(x, y, 'F0'); continue
            if y == eave - 1:
                g.set(x, y, 'F0'); continue
            ci = None
            for i, (y0, hgt) in enumerate(starts):
                if y0 <= yy < y0 + hgt:
                    ci, r, hh = i, yy - y0, hgt
            if ci is None:
                g.set(x, y, 'F1'); continue
            if r == hh - 1:
                g.set(x, y, 'F0')                       # shadow under the next course
            elif x in joints[ci] and r < hh - 1:
                g.set(x, y, 'F0')
            elif r == 0:
                # shingle tops catch the moon unevenly
                prevj = max([j for j in joints[ci] if j <= x] or [0])
                v = lit[(ci, prevj)]
                g.set(x, y, 'F2' if (v > 0.35 and x - prevj <= 3) else 'F1')
            else:
                g.set(x, y, 'F1')
    # missing shingle (dark hole) and the newer patched shingle with one nail
    g.stamp("KKK\nKkK", K, 21, 25)
    g.stamp("TTTT\nTTkT\nRRRR", K, 61, 21)
    g.stamp(".g.\ngGg", K, 15, 22)


def cross_gable(g):
    """Front gable over the door: bargeboards, board siding, round window."""
    peak, eave, cx = 3, 33, 41
    def half(y):
        return (y - peak) // 2
    for y in range(peak, eave + 1):
        h = half(y)
        xl, xr = cx - h, cx + h
        for x in range(xl, xr + 1):
            if x <= xl + 0:
                g.set(x, y, 'K0')
            elif x == xl + 1:
                g.set(x, y, 'F2')
            elif x == xl + 2:
                g.set(x, y, 'B1')
            elif x >= xr:
                g.set(x, y, 'K0')
            elif x == xr - 1:
                g.set(x, y, 'F1')
            elif x == xr - 2:
                g.set(x, y, 'B0')
            else:
                # vertical boards, darker joints every 3 px, shadow under the bargeboard
                if y <= peak + 2:
                    g.set(x, y, 'B1')
                elif (x - cx) % 3 == 0:
                    g.set(x, y, 'H0')
                else:
                    g.set(x, y, 'H2' if y < 27 else 'H1')
    # peak finial
    g.stamp("k\nk\nm", K, cx, peak - 3)
    # beam across the gable foot
    for x in range(cx - 13, cx + 14):
        g.set(x, eave - 1, 'B1')
        g.set(x, eave, 'K0')
    g.stamp(ROUND_WINDOW, K, cx - 4, 18)


def walls(g):
    x0, x1, y0, y1 = 6, 75, 34, 57
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if y == y0:
                v = 'K0'                        # deep shadow under the fascia
            elif y <= y0 + 2:
                v = 'H0'
            elif y == y0 + 3:
                v = 'H0' if (x % 2) else 'H1'
            elif y >= y1 - 1:
                v = 'B0' if y == y1 else 'B1'   # sill beam
            elif y >= 53:
                v = 'H1'
            elif y == 52:
                v = 'H1' if (x % 4 == 0) else 'H2'
            else:
                v = 'H2'
            g.set(x, y, v)
    # corner posts
    for y in range(y0 + 1, y1 + 1):
        g.set(x0, y, 'K0'); g.set(x0 + 1, y, 'B2'); g.set(x0 + 2, y, 'B1')
        g.set(x1, y, 'K0'); g.set(x1 - 1, y, 'B0'); g.set(x1 - 2, y, 'B1')
    # plaster wear: cracks and a patched rectangle of newer plaster
    for (x, y) in [(52, 40), (53, 41), (53, 42), (54, 43), (29, 44), (30, 45), (30, 46), (63, 53), (64, 54),
                   (12, 52), (11, 53)]:
        g.set(x, y, 'H1')
    g.stamp("XXXX\nXWXX\nXXXW", K, 47, 37)
    # downspout on the left corner
    for y in range(y0, y1 + 3):
        g.set(4, y, 'K0'); g.set(5, y, 'B1')
    g.set(3, y1 + 2, 'K0'); g.set(4, y1 + 2, 'B1'); g.set(5, y1 + 2, 'B1')


def foundation(g, x0=5, y0=58, w=72):
    """two courses of irregular stones; joints placed by hand."""
    c1 = [0, 6, 11, 19, 24, 30, 37, 43, 48, 55, 61, 66, 71]
    c2 = [0, 3, 9, 15, 22, 27, 34, 40, 46, 52, 58, 64, 69, 71]
    tall = {11, 37, 61}           # stones in course 1 that are three rows tall
    for x in range(w):
        X = x0 + x
        edge = x == 0 or x == w - 1
        # course 1: rows 0-1, mortar row 2 (except tall stones)
        j1 = max(j for j in c1 if j <= x)
        for r in range(3):
            if edge: v = 'K0'
            elif x in c1: v = 'R0'
            elif r == 0: v = 'R3' if x == j1 + 1 else 'R2'
            elif r == 1: v = 'R1'
            else: v = 'R1' if j1 in tall else 'R0'
            g.set(X, y0 + r, v)
        j2 = max(j for j in c2 if j <= x)
        for r in range(3, 5):
            if edge: v = 'K0'
            elif x in c2: v = 'R0'
            elif r == 3: v = 'R2' if x - j2 <= 2 else 'R1'
            else: v = 'R1'
            g.set(X, y0 + r, v)
        g.set(X, y0 + 5, 'K1')


def build():
    g = Grid(W, H)
    g.stamp(CHIMNEY, K, 9, 0)
    roof(g)
    cross_gable(g)
    walls(g)
    # windows (left has curtains, right is clear for the cat)
    g.stamp(WINDOW_CURTAIN, K, 12, 38)
    g.stamp(WINDOW, K, 55, 38)
    # shutters: left pair (right one hangs crooked), right window lost its right shutter
    g.stamp(SHUTTER, K, 8, 39)
    sh = SHUTTER.strip().split('\n')
    g.stamp('\n'.join(sh[:6]), K, 27, 39)
    g.stamp('\n'.join(sh[6:]), K, 28, 45)
    g.stamp(SHUTTER, K, 51, 39)
    g.set(69, 41, 'K0'); g.set(69, 47, 'K0')          # bare hinges
    g.stamp(DOOR, K, 36, 40)
    g.stamp(PORCH_ROOF, K, 29, 35)
    # porch posts
    for y in range(41, 58):
        g.set(31, y, 'K0'); g.set(32, y, 'B2'); g.set(33, y, 'B1')
        g.set(49, y, 'B1'); g.set(50, y, 'B0'); g.set(51, y, 'K0')
    g.stamp(RAIL, K, 25, 49)
    foundation(g)
    g.stamp(DECK, K, 27, 56)
    return g


if __name__ == '__main__':
    import artlib
    pals = artlib.load_palettes()
    g = build()
    for s in ('spring', 'summer', 'fall', 'winter'):
        artlib.preview(g, pals[s], str(artlib.ROOT / 'shots' / ('cottage_%s.png' % s)), zoom=6)
    print('orphans', g.count_orphans())


def export():
    g = build()
    return [('sprite', 'cottage', [g], 0, 0)]
