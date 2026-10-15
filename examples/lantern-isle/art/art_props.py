"""Dock, rowboat, lantern post, far lighthouse, moons and small sky sprites."""
from artlib import Grid, line, rng, bayer, disc_mask

KW = {'k': 'K0', 'K': 'K1', 'j': 'K2', 'b': 'B0', 'n': 'B1', 'm': 'B2', 'M': 'B3',
      'a': 'A0', 'A': 'A1', 'e': 'N0', 'E': 'N1', 'r': 'R0', 't': 'R1', 'u': 'R2',
      '1': 'LN0', '2': 'LN1', '3': 'LN2', '4': 'LN3', 'c': 'C0', 'C': 'C1', 'v': 'C2'}

# ------------------------------------------------------------------ dock
DOCK_W, DOCK_H = 98, 20
def dock(length=98, posts=(3, 25, 47, 69, 90)):
    DOCK_W = length
    g = Grid(DOCK_W, DOCK_H)
    R = rng(41)
    # plank widths laid by hand; 0 marks the missing plank
    widths = [4, 4, 3, 4, 5, 4, 3, 4, 4, 0, 4, 3, 4, 4, 5, 4, 3, 4, 4, 4, 3, 5, 4, 4]
    x = 0
    darker = {5, 13, 19}
    newer = {16}
    for i, w in enumerate(widths):
        if w == 0:
            # missing plank: dark gap, the beam edge shows below
            for xx in range(x, x + 4):
                for y in range(0, 3):
                    g.set(xx, y, 'K0' if y > 0 else 'K1')
            x += 4
            continue
        for xx in range(x, min(DOCK_W - 4, x + w)):
            for y in range(0, 3):
                if xx == x + w - 1:
                    v = 'B0'
                elif y == 0:
                    v = 'B3' if (xx == x and i not in darker) else ('B1' if i in darker else 'B2')
                    if i in newer:
                        v = 'B3'
                elif y == 1:
                    v = 'B1' if i in darker else 'B2'
                else:
                    v = 'B1'
                g.set(xx, y, v)
        x += w
    # one plank warped a pixel proud of the deck
    g.set(30, -1 + 1, 'B3')
    # front beam
    for xx in range(0, DOCK_W - 4):
        g.set(xx, 3, 'B2' if xx % 23 else 'B3')
        g.set(xx, 4, 'B1')
        g.set(xx, 5, 'K0')
    # posts and cross braces
    posts = list(posts)
    for i in range(len(posts) - 1):
        for (bx, by) in line(posts[i] + 3, 6, posts[i + 1] - 1, 11):
            g.set(bx, by, 'B0')
    for p in posts:
        for y in range(5, 13):
            g.set(p, y, 'B2'); g.set(p + 1, y, 'B1'); g.set(p + 2, y, 'K0')
        g.set(p + 1, 3, 'B0')                 # nail head on the beam
    # end bollard rising above the deck, rope wrapped twice
    for y in range(-4, 13):
        if 0 <= y < DOCK_H:
            pass
    return g

def dock_bollard():
    """the end post rises above the deck: separate so it can sit in front of the boat rope."""
    g = Grid(4, 8)
    for y in range(8):
        g.set(0, y, 'B2'); g.set(1, y, 'B1'); g.set(2, y, 'K0')
    g.set(0, 0, 'B3'); g.set(1, 0, 'B2')
    for x in range(3):
        g.set(x, 3, 'N0'); g.set(x, 5, 'N0')
    g.set(1, 4, 'N1')
    return g


# ------------------------------------------------------------------ rowboat
BOAT = """
k......................................kk.
kk....................................kMk.
kMkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkMk.
.kKKKKKKmMmKKKKKKKKKKKKKKmMmKKKKKKKKKKKKk.
.kMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMk.
..kmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmk..
..kaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaak..
...knnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnk...
.....kbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbk....
.......kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.....
"""
def boat():
    g = Grid(42, 11)
    g.stamp(BOAT, KW, 0, 1)
    # an oar resting across the thwarts, blade over the far gunwale
    for (x, y) in line(6, 3, 30, 0):
        g.set(x, y, 'B2')
    g.stamp("mMM\nMmm", KW, 30, 0)
    return g


# ------------------------------------------------------------------ lantern post
LANTERN = """
.kk.........
kMmkkkkkkk..
kmmnnnnnnnk.
kmn....kk...
kmn...kmmk..
kmn..kbbbbk.
kmn..k3443k.
kmn..k3443k.
kmn..k2332k.
kmn..kbbbbk.
kmn...kbbk..
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kmn.........
kbn.........
kkkk........
"""
FLAME_ROWS = [("3443", "3443", "2332"), ("3343", "3443", "2332"), ("3433", "3443", "2332"), ("3443", "3343", "2332")]
def lantern():
    frames = []
    for f in FLAME_ROWS:
        g = Grid(12, 30)
        g.stamp(LANTERN, KW)
        for i, row in enumerate(f):
            g.stamp(row, KW, 6, 6 + i)
        frames.append(g)
    return frames


# ------------------------------------------------------------------ far lighthouse
LIGHTHOUSE = """
.......k.......
......kjk......
......k4k......
.....kkkkk.....
......kCk......
......kCk......
......kjk......
......kjk......
.....kCCjk.....
.....kCCjk.....
.....kjjjk.....
.....kjjjk.....
.....kCCjk.....
....kCCCjjk....
..kkkkkkkkkkk..
.kjjKKKKKKKKKk.
kjKKKKKKKKKKKKk
"""
def lighthouse():
    g = Grid(15, 17)
    g.stamp(LIGHTHOUSE, KW)
    return g


# ------------------------------------------------------------------ moons
def moon_fall():
    r = 12.5
    g = Grid(26, 26)
    cx = cy = 12.5
    pts = set()
    for y in range(26):
        for x in range(26):
            dx, dy = x - cx + 0.5 - 0.5, y - cy + 0.5 - 0.5
            if (x - 12.5) ** 2 + (y - 12.5) ** 2 <= (r - 0.2) ** 2:
                pts.add((x, y))
    for (x, y) in pts:
        dx, dy = (x - 12.5) / r, (y - 12.5) / r
        lum = -(dx * 0.5 + dy * 0.6)
        if lum > 0.55:
            v = 'M3'
        elif lum > -0.35:
            v = 'M2'
        else:
            v = 'M1'
        # limb: one pixel ring a step darker on the shadow side
        edge = any((x + ox, y + oy) not in pts for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge and lum < 0:
            v = 'M1'
        g.set(x, y, v)
    # maria and craters placed by hand
    maria = [(8, 9, 3), (15, 7, 2), (14, 14, 4), (7, 16, 2), (18, 17, 2), (11, 19, 2)]
    for (mx, my, mr) in maria:
        for (dx, dy) in disc_mask(mr):
            x, y = mx + dx, my + dy
            if (x, y) in pts and g.get(x, y) in ('M2', 'M3'):
                g.set(x, y, 'M1' if (dx + dy) < mr else 'M1')
    for (x, y) in [(9, 8), (15, 13), (14, 15), (8, 16)]:
        g.set(x, y, 'M0')
    for (x, y) in [(6, 5), (5, 6), (10, 4), (4, 10)]:
        if (x, y) in pts:
            g.set(x, y, 'M3')
    return g

def moon_crescent():
    g = Grid(12, 12)
    a = disc_mask(5)
    b = disc_mask(5)
    for (dx, dy) in a:
        x, y = 6 + dx, 6 + dy
        if (dx - 3, dy - 2) in b:
            continue
        lum = -(dx * 0.6 + dy * 0.4)
        g.set(x, y, 'M3' if lum > 1.5 else 'M2')
    return g

def moon_veiled():
    g = Grid(22, 22)
    for (dx, dy) in disc_mask(10):
        x, y = 11 + dx, 11 + dy
        d2 = dx * dx + dy * dy
        if d2 > 49:
            if bayer(x, y) < (5 if d2 > 81 else 9):
                g.set(x, y, 'C0')
        elif d2 > 25:
            g.set(x, y, 'M0' if bayer(x, y) < 10 else 'C0')
        else:
            g.set(x, y, 'M1' if -(dx + dy) > 2 else 'M0')
    return g

TWINKLE = [""".C.
CvC
.C.""", """...
.v.
..."""]
FLARE = """.Y.
YZY
.Y."""

BIRD = ["""k...k
.kkk.
.....""", """.....
kkkkk
.....""", """.....
.kkk.
k...k"""]
BIRD_FAR = ["""k.k
.k.""", """kkk
...""", """.k.
k.k"""]


def dock_short():
    return dock(66, (3, 24, 45, 60))

def export():
    out = []
    out.append(('sprite', 'dock', [dock()], 0, 0))
    out.append(('sprite', 'dock_short', [dock_short()], 0, 0))
    out.append(('sprite', 'bollard', [dock_bollard()], 0, 0))
    out.append(('sprite', 'boat', [boat()], 0, 0))
    out.append(('sprite', 'lantern', lantern(), 1, 29))
    lh = lighthouse()
    out.append(('sprite', 'lighthouse', [lh], 7, 16))
    out.append(('sprite', 'moon_fall', [moon_fall()], 0, 0))
    out.append(('sprite', 'moon_crescent', [moon_crescent()], 0, 0))
    out.append(('sprite', 'moon_veiled', [moon_veiled()], 0, 0))
    K2 = {'.': None, 'C': 'C1', 'v': 'C2', 'Y': 'Y2', 'Z': 'Y3', 'k': 'K0'}
    def frames(arts, key):
        fs = []
        for a in arts:
            rows = a.split('\n')
            g = Grid(max(len(r) for r in rows), len(rows))
            g.stamp(a, {k: v for k, v in key.items() if v})
            fs.append(g)
        return fs
    out.append(('sprite', 'twinkle', frames(TWINKLE, K2), 0, 0))
    out.append(('sprite', 'flare', frames([FLARE], K2), 0, 0))
    out.append(('sprite', 'bird', frames(BIRD, K2), 2, 1))
    out.append(('sprite', 'bird_far', frames(BIRD_FAR, K2), 1, 1))
    return out


if __name__ == '__main__':
    import artlib
    pals = artlib.load_palettes()
    items = [it[2][0] for it in export() if it[0] == 'sprite']
    for s in ('summer', 'fall'):
        artlib.preview(items, pals[s], str(artlib.ROOT / 'shots' / ('props_%s.png' % s)), zoom=5, cols=4)

BUOY = """
..k..
.kak.
kaAak
kWwwk
kaaak
kWwwk
.kak.
..k..
"""
def buoy():
    g = Grid(5, 8)
    g.stamp(BUOY, {**KW, 'a': 'A0', 'A': 'A1', 'W': 'N3', 'w': 'N2'})
    return g

_export_base = export
def export():
    return _export_base() + [('sprite', 'buoy', [buoy()], 0, 0)]
