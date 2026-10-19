"""Lived-in details and seasonal props. Hand-drawn ASCII throughout."""
from artlib import Grid, line, rng, bayer, disc_mask

K = {'k': 'K0', 'K': 'K1', 'j': 'K2', 'b': 'B0', 'n': 'B1', 'm': 'B2', 'M': 'B3',
     'g': 'G0', 'G': 'G1', 'h': 'G2', 'H': 'G3', 'l': 'L1', 'L': 'L2', 'p': 'L3', 'P': 'L4',
     'a': 'A0', 'A': 'A1', 'c': 'A2', 'C': 'A3', 'd': 'A4', 'D': 'A5',
     'e': 'N0', 'E': 'N1', 'w': 'N2', 'W': 'N3', 'v': 'C1', 'V': 'C2',
     '1': 'WL0', '2': 'WL1', '3': 'WL2', '4': 'WL3', 'r': 'R0', 't': 'R1', 'u': 'R2', 'U': 'R3',
     'h0': 'H0', 'x': 'H1', 'X': 'H2', 'f': 'F1', 'F': 'F2'}

def art(s, key=K):
    rows = [r for r in s.strip('\n').split('\n')]
    g = Grid(max(len(r) for r in rows), len(rows))
    g.stamp(s, key)
    return g

def frames(*arts, key=K):
    gs = [art(a, key) for a in arts]
    w = max(g.w for g in gs); h = max(g.h for g in gs)
    out = []
    for g in gs:
        n = Grid(w, h); n.paste(g, 0, 0); out.append(n)
    return out

# ------------------------------------------------------------------ cat in the window
# body is the darkest tone; its back catches the lamplight from inside (rim)
CAT = frames("""
.k.k.....
.kkk.....
2kkk22k..
kkkkkkkk.
kkkkkkkkk
.kkkkkkkk
""", """
.k.k.....
.kkk.....
2kkk222k.
kkkkkkkk.
kkkkkkkkk
.kkkkkkkk
""", """
.k.k.....
.kkk....k
2kkk22kk.
kkkkkkkk.
kkkkkkkkk
.kkkkkkkk
""")

# ------------------------------------------------------------------ mug and steam
MUG = art("""
WwwK.
wwwKK
ewwK.
.ee..
""")
STEAM = frames("""
..e
.e.
.E.
e..
""", """
.e.
e..
.e.
..E
""", """
e..
.e.
..e
.E.
""", """
...
.e.
e..
.e.
""")

# ------------------------------------------------------------------ kite tied to the porch post
KITE = frames("""
k.......
.k......
..k.....
...k....
....k...
....kk..
...kaak.
..kaamAk
.kaaamAAk
.knnnnnnk
..kccmAk.
...kcmk..
....kk...
.....k...
......A..
.....k...
....a....
.....k...
""", """
k.......
.k......
..k.....
...k....
....k...
....kk..
...kaak.
..kaamAk
.kaaamAAk
.knnnnnnk
..kccmAk.
...kcmk..
....kk...
....k....
...A.....
....k....
.....a...
....k....
""", """
k.......
.k......
..k.....
...k....
....k...
....kk..
...kaak.
..kaamAk
.kaaamAAk
.knnnnnnk
..kccmAk.
...kcmk..
....kk...
.....k...
.....A...
......k..
......a..
.....k...
""")

# ------------------------------------------------------------------ hammock (summer)
def hammock():
    g = Grid(40, 12)
    # ropes from each tree to the spreader bars
    for (x, y) in line(0, 0, 5, 4):
        g.set(x, y, 'B1')
    for (x, y) in line(39, 0, 34, 4):
        g.set(x, y, 'B1')
    # fabric: hand-tuned sag per column (relative rows)
    sag = [0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3, 2, 2, 1, 1, 0]
    x0 = 6
    for i, d in enumerate(sag + [0, 0, 0, 0, 0]):
        x = x0 + i
        if x > 33:
            break
        dd = sag[min(i, len(sag) - 1)] if i < len(sag) else 0
        dd = int(round((dd if i < len(sag) else 0)))
        for r in range(3):
            y = 4 + dd + r
            stripe = (x // 3) % 2
            if r == 0:
                v = 'A1' if stripe else 'A0'
            elif r == 1:
                v = 'A0' if stripe else 'A1'
            else:
                v = 'K0'
            g.set(x, y, v)
    # a pillow and a book left in the hammock
    g.stamp("WWw\nwwe", K, 10, 4)
    g.set(5, 4, 'B2'); g.set(34, 4, 'B2'); g.set(5, 5, 'B1'); g.set(34, 5, 'B1')
    return g

# ------------------------------------------------------------------ pumpkins (fall)
PUMPKIN_BIG = art("""
....C....
..kkCkk..
.kAaaaAak
kAaAaaAaak
kaaAaaAaak
kaaaaaaaak
.kaaaaaak.
..kkkkkk..
""".replace('A', 'A'))
PUMPKIN_MED = art("""
...C...
.kkCkk.
kAaaAak
kaAaaak
kaaaaak
.kkkkk.
""")
PUMPKIN_SMALL = art("""
..C..
.kCk.
kAaak
kaaak
.kkk.
""")
# jack-o'-lantern: carved face lit from inside (flickers with the windows)
JACK = art("""
....C....
..kkCkk..
.kAaaaAak
kA3aaa3ak
kaa4aa4aak
kaaaaaaaak
ka3a3a3aak
.kaa3aaak.
..kkkkkk..
""")

# ------------------------------------------------------------------ laundry line, per season
def laundry(season, frame):
    g = Grid(46, 22)
    # line: hand-tuned sag
    sag = [0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3,
           3, 3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0]
    for x in range(46):
        g.set(x, sag[x], 'N0' if season != 'winter' else 'N1')
    def hang(art_s, x0):
        rows = art_s.strip('\n').split('\n')
        top = sag[min(45, x0 + len(rows[0]) // 2)] + 1
        g.stamp(art_s, K, x0, top)
        # pegs
        g.set(x0 + 1, top - 1, 'B2'); g.set(x0 + len(rows[0]) - 2, top - 1, 'B2')
    sway = frame % 2
    if season == 'spring':
        hang(""".cccc.
cccccc
cVccVc
.cccc.
.cccc.
""" if not sway else """.cccc.
cccccc
cVccVc
.cccc.
..cccc
""", 8)
        hang("""wwW
wwW
www
ww.
""", 24)
    elif season == 'summer':
        hang("""WWWwWWW
WWWWWWw
.WWWWw.
.WWWWw.
.wWWWw.
""" if not sway else """WWWwWWW
WWWWWWw
.WWWWw.
.WWWWw.
..wWWWw
""", 6)
        hang("""aAaAa
aAaAa
aAaAa
aAaAa
aAaAa
aAaAa
""", 19)
        hang("""ccccc
ccccc
.ccc.
.ccc.
ccccc
cc.cc
""" if not sway else """ccccc
ccccc
.ccc.
.ccc.
.ccccc
.cc.cc
""", 30)
    elif season == 'fall':
        hang("""DDDDDDD
DDDdDDD
DDDDDDD
.DDDDD.
.DDDDD.
.dDdDd.
""" if not sway else """DDDDDDD
DDDdDDD
DDDDDDD
.DDDDD.
..DDDDD
..dDdDd
""", 7)
        hang("""dd
dd
dd
dd
dd
dd
dd
dD
""" if not sway else """dd
dd
dd
dd
.dd
.dd
..dd
..dD
""", 22)
        hang("""ee
eE
ee
""", 32)
    elif season == 'winter':
        # snow along the line, one pair of frozen mittens
        for x in range(46):
            if x % 5 in (1, 2, 3) and 3 < x < 42:
                g.set(x, sag[x] - 1, 'N3')
        hang("""aa.aa
aa.aa
.a..a
""", 19)
    return g

# ------------------------------------------------------------------ garden patch, per season
def garden(season):
    g = Grid(30, 12)
    # low log border and furrowed soil (the patch sits on the grass strip)
    for x in range(30):
        g.set(x, 11, 'B0')
        g.set(x, 10, 'B1' if x % 6 else 'B0')
        g.set(x, 9, 'B2' if x % 6 else 'B1')
    for x in range(1, 29):
        for y in (6, 7, 8):
            g.set(x, y, 'B1' if (y == 7 and x % 4) else 'B0')
    g.set(0, 9, 'K0'); g.set(29, 9, 'K0')
    plants = {
        'spring': ([(2, ".h.\nhGh"), (7, "d.d\nGhG"), (12, ".h.\nhGh"), (17, "d.d\nGhG"), (22, ".h.\nhGh"),
                    (26, "d.\nhG")], 4),
        'summer': ([(2, ".CC.\nCMMC\n.CC.\n.h..\n.hG.\n.G.."), (8, "..d.\n.hGd\nhGh.\n.G.."),
                    (14, ".CC.\nCMMC\n.CC.\n..h.\n.Gh.\n..G."), (20, "..d.\nhdG.\n.Gh.\n..G."),
                    (25, ".CC.\nCMMC\n.CC.\n.h..\n.hG.")], 0),
        'fall': ([(2, ".hH.\nhGGh\n.gg."), (9, "..C\n.aa\naAa"), (15, ".hH.\nhGGh\n.gg."),
                  (21, ".u.\n.u.\nuGu"), (25, "aa\nAa")], 3),
        'winter': ([(1, "..WWWW..\n.WwwwwW.\nWwwwwwwwW"), (10, ".WWWWW.\nWwwwwwW"),
                    (18, "..WWW...\n.WwwwWW.\nWwwwwwwW"), (26, ".WW\nWww")], 4),
    }
    items, base = plants[season]
    for (x, a) in items:
        rows = a.split('\n')
        g.stamp(a, K, x, 8 - len(rows) + 1)
    return g

# ------------------------------------------------------------------ firewood stack and chopping stump
FIREWOOD = art("""
....kkkkkkkk....
..kkMmmMmmMmkk..
.kMnbmMnbmMnbk..
kmMbbnmbbnmbbnk.
kmnmmMnmmMnmmMmk
kMnbbmMnbbmMnbbk
kmmbbnmmbbnmmbbk
kmnmmMnmmMnmmMnk
kMnbbmMnbbmMnbbk
kmmbbnmmbbnmmbbk
kkkkkkkkkkkkkkkk
""")
FIREWOOD_SNOW = art("""
....WWWWWWWW....
..WWwwwwwwwwWW..
.Wwe........ewW.
We............eW
""")
STUMP_AXE = art("""
......kk.
.....kVk.
....kVVk.
...kmk...
..kmk....
.kkmkkk..
kMMmMMMk.
kmnnnnmk.
kmnnnnmk.
.kkkkkk..
""")

# ------------------------------------------------------------------ rain barrel
BARREL = art("""
.kkkkkkk.
kMmmmmmnk
kvVvvvvvk
kbbbbbbbk
kmMmmmnnk
kbbbbbbbk
kmMmmmnnk
kmMmmmnnk
kbbbbbbbk
kmMmmmnnk
.kkkkkkk.
""")
BARREL_RIPPLE = frames("""
kvVvvvvvk
""", """
kvvVvVvvk
""", """
kvvvvvVvk
""", """
kVvvvvvvk
""")
BARREL_SNOW = art("""
.WWWWWWW.
WwwwwwwwW
""")

# ------------------------------------------------------------------ window boxes
def window_box(season):
    g = Grid(15, 6)
    for x in range(1, 14):
        g.set(x, 3, 'B2'); g.set(x, 4, 'B1'); g.set(x, 5, 'K0')
    g.set(0, 3, 'K0'); g.set(14, 3, 'K0'); g.set(0, 4, 'K0'); g.set(14, 4, 'K0')
    plants = {
        'spring': "..d..d...d.d.\n.hGhdhGh.hGhd\nhGhGhGhGhGhGh",
        'summer': ".a..a.aa..a..\naAahaAahaAah.\nhGhGhGhGhGhGh",
        'fall': "..p...P..p...\n.hgHhgh.Hgh..\nggGgGggGgGgg.",
        'winter': ".WWW..WWWW.WW\nWwwwWWwwwwWww\nwwwwwwwwwwwww",
    }[season]
    g.stamp(plants, K, 1, 0)
    return g

# ------------------------------------------------------------------ small seasonal props
WREATH = art("""
..CCC..
.CA.AC.
CA...AC
C.....C
CA...AC
.CAaAC.
..CaC..
...a...
""", key={**K, 'C': 'A1', 'A': 'A2', 'a': 'A0'})
SLED = art("""
.kk.
kmMk
kmnk
kmnk
kmnk
kmnk
kmnk
kmnk
kmnk
kmnk
kmnk
kmnk
kmnk
.kk.
..ak
...a
""", key={**K, 'a': 'A0', 'm': 'A3', 'M': 'B3', 'n': 'A3'})
RAKE = art("""
.kmk.
kmMmk
.kmk.
..m..
..m..
..m..
..m..
..m..
..n..
..n..
..n..
..n..
..n..
..n..
..n..
..n..
..n..
..n..
""".replace('kmMmk', 'kmmmk'))
BOOTS = art("""
kddk.kddk
kddk.kddk
kddk.kddk
kdddkkdddk
kkkkkkkkkk
""", key={**K, 'd': 'A2'})
CAN = art("""
...kk...
..kVVk..
.kvvvvk.k
kVvvvvvkk
kvvvvvvk.
kvvvvvvk.
.kkkkkk..
""", key={**K, 'v': 'A3', 'V': 'A5'})
HAT = art("""
...kkkk...
..kAAAAk..
..kaaaak..
kkAAAAAAkk
.kkkkkkkk.
""", key={**K, 'A': 'A1', 'a': 'A0'})
ROD = art("""
................e
...............e.
..............e..
.............m...
............m....
...........m.....
..........m......
.........m.......
........m........
.......n.........
......n..........
.....n...........
....n............
...b.............
..b..............
""")

# ------------------------------------------------------------------ export
def export():
    out = []
    out.append(('sprite', 'cat', CAT, 0, 0))
    out.append(('sprite', 'mug', [MUG], 0, 0))
    out.append(('sprite', 'steam', STEAM, 0, 0))
    out.append(('sprite', 'kite', KITE, 0, 0))
    out.append(('sprite', 'hammock', [hammock()], 0, 0))
    out.append(('sprite', 'pumpkin_big', [PUMPKIN_BIG], 0, 0))
    out.append(('sprite', 'pumpkin_med', [PUMPKIN_MED], 0, 0))
    out.append(('sprite', 'pumpkin_small', [PUMPKIN_SMALL], 0, 0))
    out.append(('sprite', 'jack', [JACK], 0, 0))
    for s in ('spring', 'summer', 'fall', 'winter'):
        out.append(('sprite', 'laundry_' + s, [laundry(s, 0), laundry(s, 1)], 0, 0))
        out.append(('sprite', 'garden_' + s, [garden(s)], 0, 0))
        out.append(('sprite', 'wbox_' + s, [window_box(s)], 0, 0))
    out.append(('sprite', 'firewood', [FIREWOOD], 0, 0))
    out.append(('sprite', 'firewood_snow', [FIREWOOD_SNOW], 0, 0))
    out.append(('sprite', 'stump', [STUMP_AXE], 0, 0))
    out.append(('sprite', 'barrel', [BARREL], 0, 0))
    out.append(('sprite', 'barrel_ripple', BARREL_RIPPLE, 0, 0))
    out.append(('sprite', 'barrel_snow', [BARREL_SNOW], 0, 0))
    out.append(('sprite', 'wreath', [WREATH], 0, 0))
    out.append(('sprite', 'sled', [SLED], 0, 0))
    out.append(('sprite', 'rake', [RAKE], 0, 0))
    out.append(('sprite', 'boots', [BOOTS], 0, 0))
    out.append(('sprite', 'can', [CAN], 0, 0))
    out.append(('sprite', 'hat', [HAT], 0, 0))
    out.append(('sprite', 'rod', [ROD], 0, 0))
    return out


if __name__ == '__main__':
    import artlib
    pals = artlib.load_palettes()
    items = [it[2][0] for it in export()]
    for s in ('spring', 'summer', 'fall', 'winter'):
        artlib.preview(items, pals[s], str(artlib.ROOT / 'shots' / ('details_%s.png' % s)), zoom=5, cols=8)
