"""8-bit console panel (NES-style limits, tools/era.py 'nes'): 256x224, 2C02 master palette.

Designed on the hardware's grid, not snapped from the 16-bit panel:
  backdrop  black, shared by every block (outlines, the crag's silhouette, the dark sea)
  BG0  dark blue, violet, white        upper sky, the post office, stars, smoke, far sea waves
  BG1  violet, pink, orange            lower sky, the crag's crest and rim, sea near the horizon, glitter
  BG2  dark brown, rust, orange        near cliff, plateau, rail, trestle
  BG3  cream, red, lamp yellow         town, terraces, quay, mole
Each 16x16 block takes one of them (checked by common.attr_report). The plateau sits on the block
line y=80 and the violet band runs to y=80 so the post office never shares a block with pink sky.
  SP0  black, white, orange            wing, tail, gulls, boat
  SP1  black, blue, skin               the postmaster
  SP2  dark brown, red, white          the overlapping scarf and satchel sprite, the mail flag
  SP3  orange, pale yellow, white      the sun, the lamp-lit post office window
The near cliff is one 32x32 rock metatile repeated (with a 64 px offset rhythm) so the frame stays
under the 256-tile pattern table; the crag is a flat silhouette with a rim, as backlit 8-bit art.

Run: python3 art/panel_nes.py -> out/panel-nes.png, out/panel-nes-bg.png (+ @4x)
"""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from common import Canvas, stamp, image, over, save, OUT, attr_report, torus_cells

W, H = 256, 224
HZ = 119
PAL = {'K': '#000000', 'B': '#0000bc', 'V': '#6844fc', 'Wt': '#fcfcfc', 'P': '#f878f8', 'O': '#fca044',
       'D': '#881400', 'N': '#e45c10', 'C': '#f0d0b0', 'R': '#a81000', 'Y': '#f8b800',
       'sU': '#0058f8', 'sS': '#fce0a8', 'sR': '#e40058', 'sL': '#f8d878'}
SUBPALS = [('#0000bc', '#6844fc', '#fcfcfc'), ('#6844fc', '#f878f8', '#fca044'),
           ('#881400', '#e45c10', '#fca044'), ('#f0d0b0', '#a81000', '#f8b800')]
SPRPALS = [('#000000', '#fcfcfc', '#fca044'), ('#000000', '#0058f8', '#fce0a8'),
           ('#881400', '#e40058', '#fcfcfc'), ('#fca044', '#f8d878', '#fcfcfc')]

CRAG = [(84, 80), (90, 76), (97, 73), (104, 72), (110, 69), (117, 65), (123, 62), (127, 58), (130, 55),
        (134, 55), (137, 59), (141, 62), (146, 61), (150, 64), (157, 67), (164, 70), (171, 76), (178, 83),
        (186, 91), (194, 99), (201, 107), (207, 113), (212, 119)]

def chk(x, y):
    return (x + y) % 2 == 0

# ---------------------------------------------------------------- background
def sky(c):
    for y in range(0, HZ):
        for x in range(W):
            if y < 34: s = 'B'
            elif y < 36: s = 'V' if chk(x, y) else 'B'
            elif y < 80: s = 'V'
            elif y < 82: s = 'P' if chk(x, y) else 'V'
            elif y < 100: s = 'P'
            elif y < 102: s = 'O' if chk(x, y) else 'P'
            else: s = 'O'
            c.g[y, x] = s
    # the sun's warmth: a checker of orange into the pink above it
    for y in range(82, 102):
        for x in range(190, 252):
            if math.hypot(x - 220, (y - HZ) * 1.3) < 27 and chk(x, y):
                c.g[y, x] = 'O'
    for x, y in ((106, 9), (151, 4), (183, 14), (236, 7), (9, 6)):    # the last stars
        c.g[y, x] = 'Wt'
    # cloud bars: dark blue in the violet band, violet with an orange underline in the pink band
    for x0, x1, y in ((150, 196, 50), (164, 222, 52), (205, 240, 45)):
        c.rect(x0, y, x1, y + 1, 'B')
    for x0, x1, y in ((182, 250, 86), (196, 238, 88), (226, 255, 93)):
        c.rect(x0, y, x1, y + 2, 'V'); c.rect(x0 + 3, y + 2, x1 - 2, y + 3, 'O')

def sea(c):
    for y in range(HZ, H):
        c.rect(0, y, W, y + 1, 'K')
    # waves: short dashes on a 32 px rhythm per row band (so tiles repeat); near the horizon pink
    for y in range(HZ + 2, H, 4):
        band = (y - HZ) // 4
        t = (y - HZ) / (H - HZ)
        for x0 in range(0, W, 32):
            for off, L in ((3 + (band * 11) % 16, 3 + int(3 * t)), (19 + (band * 7) % 10, 2 + int(4 * t))):
                x = x0 + off
                s = 'P' if y < 132 else ('V' if (band % 3) else 'B')
                c.rect(x, y, x + L, y + 1, s)
    # the glitter column under the sun: orange dashes, narrowing to the horizon
    rng = np.random.default_rng(3)
    for y in range(HZ + 1, H, 2):
        t = (y - HZ) / (H - HZ)
        half = 3 + 19 * t
        for _ in range(int(2 + 5 * t)):
            x = int(220 + rng.uniform(-half, half))
            L = int(2 + rng.integers(0, 2) + 3 * t)
            c.rect(x, y, x + L, y + 1, 'O' if rng.random() < 0.75 else 'P')

def crag(c):
    m = c.mask_poly(CRAG + [(212, 200), (84, 200)])
    c.fill(m, 'K')
    top = np.full(W, H, int)
    for x in range(W):
        col = np.nonzero(m[:, x])[0]
        if len(col):
            top[x] = col[0]
    for x in range(W - 1):                                        # the orange rim on sun-facing crest
        y, nxt = top[x], top[x + 1]
        if y >= H:
            continue
        if nxt > y:
            for k in range(min(2, nxt - y) if nxt < H else 2):
                c.g[y + k, x] = 'O'
        elif nxt == y and x >= 132:
            c.g[y, x] = 'O'
    for x in range(1, W):
        y = top[x]
        if y < H and top[x - 1] > y and c.g[y, x] == 'K':
            c.g[y, x] = 'V'
    return m

def near_cliff(c):
    PL = 80
    # the cliff edge: x of the face per row, jogging only at 8 px rows (edge tiles repeat)
    edge = {}
    jogs = [(80, 88), (96, 90), (112, 92), (128, 91), (144, 95), (168, 97), (192, 99), (208, 101)]
    for y in range(PL, H):
        e = max(v for yy, v in jogs if yy <= y)
        edge[y] = e
    for y in range(PL, H):
        for x in range(edge[y]):
            c.g[y, x] = rock(x, y)
        e = edge[y]
        for x in range(e - 5, e):                                 # the sunlit strip
            c.g[y, x] = 'O' if x == e - 1 or (x == e - 2 and y % 8 < 5) else 'N'
        c.g[y, e - 6] = 'K'
    for yy, v in jogs[1:]:                                       # each jog is a lit ledge
        p = edge[yy - 1]
        c.rect(p - 6, yy, v, yy + 1, 'O'); c.rect(p - 6, yy + 1, v - 1, yy + 2, 'N')
    for x0, x1, y in ((8, 40, 120), (48, 72, 152), (16, 48, 184)):
        c.rect(x0, y, x1, y + 1, 'O'); c.rect(x0, y + 1, x1, y + 2, 'K')
        for tx in range(x0 + 3, x1 - 2, 9):
            c.rect(tx, y - 2, tx + 2, y, 'N'); c.put(tx + 1, y - 3, 'O')
    # plateau grass on the block line, sunlit gold on a 16 px rhythm
    c.rect(0, PL, 90, PL + 4, 'N')
    for x in range(0, 90):
        if x % 16 in (2, 3, 9, 13):
            c.g[PL, x] = 'O'
        if x % 16 in (5, 11):
            c.g[PL + 1, x] = 'O'
    c.rect(0, PL + 4, 89, PL + 5, 'K')
    for x, h in ((86, 3), (89, 2)):
        c.rect(x, PL + 4, x + 1, PL + 4 + h, 'N')
    return edge

ROCK_IDS = torus_cells(32, 32, [(5, 4), (19, 9), (28, 22), (11, 20), (23, 31), (2, 28)], aspect=2.0)

def rock(x, y):
    """one 32x32 metatile of angular facets (periodic, so the pattern table holds it in 16 tiles),
    shifted 16 rows in every other 32 px column: planes dark brown or rust, a lit sun-side edge on
    each, fractures black, lips orange"""
    u = x % 32
    v = (y + (16 if (x // 32) % 2 else 0)) % 32
    i = ROCK_IDS[v, u]
    if i == 0:
        l_, r_ = ROCK_IDS[v, (u - 1) % 32], ROCK_IDS[v, (u + 1) % 32]
        up, dn = ROCK_IDS[(v - 1) % 32, u], ROCK_IDS[(v + 1) % 32, u]
        return 'O' if (up > 0 and dn > 0 and up != dn and (l_ == 0 or r_ == 0)) else 'K'
    lit_plane = i in (2, 5)
    if ROCK_IDS[v, (u + 1) % 32] != i:
        return 'O' if lit_plane else 'N'
    return 'N' if lit_plane else 'D'

def office(c):
    x0, x1, wt, base = 16, 58, 52, 80
    c.rect(x0, wt, x1 + 10, base, 'Wt')
    c.rect(x0, wt, x0 + 1, base, 'K'); c.rect(x1, wt, x1 + 1, base, 'K'); c.rect(x1 + 10, wt - 1, x1 + 11, base, 'K')
    c.poly([(x1, wt + 0.5), (x1 + 5, wt - 12.5), (x1 + 10, wt + 0.5)], 'Wt')
    c.line(x1 + 5, wt - 13, x1 + 11, wt - 1, 'K')
    for k in range(13):                                          # dark blue slate, violet courses
        y = wt - 1 - k
        a = x0 - 2 + int(round(4 * k / 12.0)); b = x1 + 1 + int(round(4 * k / 12.0))
        c.rect(a, y, b, y + 1, 'V' if k % 4 == 2 else 'B')
        c.put(a, y, 'K'); c.put(b, y, 'K')
    c.rect(x0 - 2, wt - 1, x1 + 2, wt, 'K'); c.rect(x0 + 2, wt - 14, x1 + 6, wt - 13, 'K')
    c.rect(x0, wt, x1, wt + 1, 'B')                              # the eave's shadow
    c.rect(24, wt - 24, 30, wt - 12, 'Wt'); c.rect(23, wt - 25, 31, wt - 23, 'K')
    c.rect(23, wt - 23, 24, wt - 12, 'K'); c.rect(30, wt - 23, 31, wt - 12, 'K'); c.rect(25, wt - 19, 30, wt - 18, 'B')
    for (cx, cy, r) in ((27, 24, 2), (22, 21, 3), (15, 18, 3), (8, 15, 4)):     # smoke, streaming left
        for y in range(cy - r, cy + r):
            for x in range(cx - r - 1, cx + r + 1):
                if ((x - cx) / (r + 1.0)) ** 2 + ((y - cy + 0.5) / float(r)) ** 2 <= 1:
                    c.g[y, x] = 'Wt' if (y < cy or chk(x, y)) else c.g[y, x]
    # door, sign, windows (the left one is lamp-lit by a sprite over black mullions)
    c.rect(33, 64, 41, base, 'K'); c.rect(34, 65, 40, base, 'B'); c.put(38, 71, 'Wt')
    c.rect(30, 55, 44, 62, 'K')
    stamp(c, """
WkkkkkkW
kWkkkkWk
kkWkkWkk
kkkWWkkk
""", {'W': 'Wt', 'k': 'K'}, 33, 56)
    c.rect(19, 61, 29, 71, 'K'); c.rect(45, 61, 55, 71, 'K')
    c.rect(46, 62, 54, 70, 'B'); c.rect(49, 62, 50, 70, 'K'); c.rect(46, 65, 54, 66, 'K')
    c.rect(51, 66, 54, 70, 'Wt')                                  # the patched pane
    stamp(c, """
.KK..
KWWK.
KWWWK
KWWWK
.KKK.
""", {'K': 'K', 'W': 'Wt'}, 42, base - 5)                         # the mail sack
    stamp(c, """
..K.....K.
.KKKK.KKK.
KK.KKKK.KK
K.K.K..K.K
KK.K..K.KK
.KK....KK.
""", {'K': 'K'}, 4, base - 6)                                    # the bicycle
    c.rect(70, 18, 74, base, 'K'); c.rect(71, 19, 73, base, 'Wt')   # the white flag pole

def rail(c):
    xa, ya, xb, yb = 70, 82, 110, 90
    for i in range(xb - xa + 1):
        x = xa + i; y = ya + int(round((yb - ya) * i / (xb - xa)))
        c.put(x, y - 1, 'K'); c.put(x, y, 'O'); c.put(x, y + 1, 'N'); c.put(x, y + 2, 'K')
    for k, i in enumerate(range(4, xb - xa, 5)):
        if k == 4:
            continue                                             # the missing tie
        x = xa + i; y = ya + int(round((yb - ya) * i / (xb - xa)))
        c.rect(x, y + 3, x + 2, y + 4, 'K')
    c.rect(xb - 1, yb - 3, xb + 1, yb, 'N'); c.put(xb, yb - 3, 'O')
    c.line(97, 108, 105, 91, 'K'); c.line(98, 108, 106, 91, 'N')
    c.rect(77, 84, 79, 92, 'N')

def town(c):
    def house(x0, base, w, wh, roof, rh, lit, dark, door, chim=None):
        top = base - wh
        c.rect(x0 - 1, top - 1, x0 + w + 1, base + 1, 'K')
        c.rect(x0, top, x0 + w, base, 'C')
        if roof == 'gable':
            for k in range(rh + 1):
                a = x0 - 1 + k * (w + 2) // (2 * rh + 1); b = x0 + w + 1 - k * (w + 2) // (2 * rh + 1)
                c.rect(a - 1, top - k - 1, b + 1, top - k, 'K')
                c.rect(a, top - k, b, top - k + 1, 'R')
        elif roof in ('hip', 'shed'):
            for k in range(rh):
                inset = k if roof == 'hip' else 0
                c.rect(x0 - 2 + inset, top - k - 2, x0 + w + 2 - inset, top - k - 1, 'K')
                c.rect(x0 - 1 + inset, top - k - 1, x0 + w + 1 - inset, top - k, 'R')
            if roof == 'shed':                                    # the sagging ridge
                mid = x0 + w // 2
                c.rect(mid - 3, top - rh - 1, mid + 4, top - rh, 'R'); c.rect(mid - 3, top - rh - 2, mid + 4, top - rh - 1, 'K')
        elif roof == 'lean':
            for k in range(rh):
                c.rect(x0 - 2, top - k - 2, x0 + w + 2 - k * w // rh, top - k - 1, 'K')
                c.rect(x0 - 1, top - k - 1, x0 + w + 1 - k * w // rh, top - k, 'R')
        elif roof == 'flat':                                      # parapet with a cream coping
            c.rect(x0 - 1, top - 3, x0 + w + 1, top, 'K'); c.rect(x0, top - 2, x0 + w, top, 'C')
            c.rect(x0, top - 1, x0 + w, top, 'R')
        if chim:
            cx, ch = chim
            yb = top - (rh if roof != 'flat' else 2)
            c.rect(x0 + cx - 1, yb - ch - 1, x0 + cx + 3, yb + 1, 'K'); c.rect(x0 + cx, yb - ch, x0 + cx + 2, yb + 1, 'R')
        for (wx, wy) in lit:
            c.rect(x0 + wx, top + wy, x0 + wx + 3, top + wy + 3, 'Y')
        for (wx, wy) in dark:
            c.rect(x0 + wx, top + wy, x0 + wx + 3, top + wy + 3, 'K')
        if door is not None:
            c.rect(x0 + door, base - 6, x0 + door + 3, base, 'K')
        c.rect(x0 + w - 1, top, x0 + w, base, 'R')                # the sunlit corner turns warm
    c.rect(112, 161, 202, 164, 'R'); c.rect(112, 161, 202, 162, 'C')     # the terrace wall
    for x in range(115, 202, 8):
        c.put(x, 163, 'K')
    house(114, 160, 11, 21, 'gable', 8, [(2, 3), (2, 11)], [(6, 11)], 6, chim=(7, 3))   # tall and narrow
    house(130, 157, 19, 8, 'hip', 3, [(3, 3)], [], 11)                                   # squat cottage
    house(155, 160, 15, 13, 'flat', 0, [(2, 3)], [(9, 3), (2, 8)], 9)                    # flat roof
    house(176, 158, 14, 11, 'gable', 9, [], [(3, 4), (8, 4)], 5)                         # steep gable
    house(116, 187, 18, 9, 'shed', 3, [], [(4, 3)], 10)                                  # the net shed
    house(139, 187, 13, 16, 'hip', 5, [(2, 4)], [(8, 4), (2, 10)], 8, chim=(9, 3))      # two storeys
    house(160, 186, 27, 12, 'hip', 5, [(3, 3), (10, 3), (17, 3)], [(23, 3)], 14)         # the harbour inn
    c.rect(199, 149, 200, 161, 'C'); c.rect(198, 147, 201, 150, 'Y')    # the lamp post
    c.line(148, 147, 154, 149, 'C')                                       # washing line
    c.rect(149, 148, 151, 151, 'C'); c.rect(152, 148, 154, 151, 'Y')
    # quay and mole, a chipped end, lobster pots
    c.rect(112, 188, 208, 192, 'R'); c.rect(112, 188, 208, 189, 'C')
    for x in range(116, 208, 8):
        c.rect(x, 190, x + 1, 192, 'K')
    c.rect(160, 193, 207, 198, 'R'); c.rect(160, 193, 205, 194, 'C'); c.rect(160, 197, 207, 198, 'K')
    c.rect(205, 193, 207, 195, 'K')
    for (x, y) in ((176, 190), (180, 190), (178, 187)):
        c.rect(x, y, x + 4, y + 3, 'K'); c.rect(x + 1, y + 1, x + 3, y + 2, 'Y')

def background():
    c = Canvas(W, H)
    sky(c)
    sea(c)
    cm = crag(c)
    near_cliff(c)
    office(c)
    rail(c)
    town(c)
    clean_blocks(c)
    return c

def clean_blocks(c):
    """enforce the attribute plan where two regions meet: in each 16x16 block, colours outside the
    block's sub-palette fall back to the backdrop (a wave dash under the mole, a glitter dash in a
    town block). Reports what it changed."""
    changed = 0
    for by in range(0, H, 16):
        for bx in range(0, W, 16):
            blk = c.g[by:by + 16, bx:bx + 16]
            cols = {PAL[s] for s in blk.ravel()} - {'#000000'}
            if any(cols <= set(sp) for sp in SUBPALS):
                continue
            # keep the sub-palette that covers the most pixels, drop the rest to black
            best, score = None, -1
            for sp in SUBPALS:
                n = sum(1 for s in blk.ravel() if PAL[s] in sp)
                if n > score:
                    best, score = sp, n
            for (y, x), s in np.ndenumerate(blk):
                if PAL[s] not in best and PAL[s] != '#000000':
                    blk[y, x] = 'K'; changed += 1
    print('attribute clean-up: %d px moved to the backdrop' % changed)

# ---------------------------------------------------------------- sprites
def wing(c):
    """the delta in three sprite colours: a black spar from the nose to two clean points, white cloth,
    orange battens, the shade panel's underside band in orange; the A-frame and bar under the keel"""
    Lt, Nz, Rt = (112, 92), (146, 76), (175, 85)
    edge = lambda x: Lt[1] + (Rt[1] - Lt[1]) * (x - Lt[0]) / (Rt[0] - Lt[0])
    kx = Nz[0]
    tri = c.mask_poly([(Lt[0], Lt[1] + 0.5), (Nz[0] + 0.5, Nz[1]), (Rt[0] + 1, Rt[1] + 0.5)])
    bat = [121, 130, 138, 154, 161, 168]
    stops = [Lt[0]] + bat[:3] + [kx] + bat[3:] + [Rt[0]]
    for a, b in zip(stops, stops[1:]):
        for x in range(a + 1, b):
            f = (x - a) / max(1, b - a)
            if 0.2 < f < 0.8:
                tri[int(math.floor(edge(x))) + 1, x] = True
    for y, x in zip(*np.nonzero(tri)):
        band = y >= edge(x) - (2.5 if x < kx else 0.5)
        c.g[y, x] = 'O' if band else 'Wt'
    for bx in bat:
        for y in np.nonzero(tri[:, bx])[0][1:]:
            c.g[y, bx] = 'K' if c.g[y, bx] == 'O' else 'O'
    for y in np.nonzero(tri[:, kx])[0]:
        c.g[y, kx] = 'O'
    c.line(Lt[0], Lt[1], Nz[0], Nz[1], 'K'); c.line(Nz[0], Nz[1], Rt[0], Rt[1], 'K')
    c.line(kx, 88, 136, 100, 'K'); c.line(kx + 1, 88, 157, 100, 'K')       # A-frame
    c.rect(134, 100, 159, 101, 'K')                                       # control bar

def tail(c):
    pass

PILOT = """
...kkkk.....
..kuuuuk....
..kuuuuuk...
..kkkkkkk...
...kssssk...
...kssssk...
...kkssk....
..kuuuuuuk..
.kuuuuuuuuk.
.kuuuuuuuuk.
.kuuuuuuuuk.
..kuuuuuuk..
..kuukkuuk..
..kuk..kuk..
.kuuk..kuuk.
.kkkk..kkkk.
"""

def pilot(c, x, y):
    stamp(c, PILOT, {'k': 'K', 'u': 'sU', 's': 'sS'}, x, y)
    c.line(x + 2, y + 7, x - 1, y - 1, 'sU'); c.line(x + 9, y + 7, x + 12, y - 1, 'sU')
    c.put(x - 1, y - 2, 'sS'); c.put(x + 12, y - 2, 'sS')

def overlay(c, x, y):
    """the second sprite laid over the pilot: the red scarf (trailing left in the wind) and the satchel"""
    for i, (sx, sy) in enumerate([(x + 7, y + 7), (x + 5, y + 7), (x + 3, y + 7), (x + 1, y + 7), (x - 1, y + 8),
                                  (x - 3, y + 8), (x - 5, y + 7), (x - 7, y + 8)]):
        c.put(sx, sy, 'sR'); c.put(sx - 1, sy, 'sR'); c.put(sx, sy + 1, 'sR' if i < 4 else ('D' if i % 2 else 'sR'))
    c.put(x - 9, y + 8, 'sR'); c.put(x - 9, y + 10, 'sR')
    stamp(c, """
DDDDD
DsssD
DWWWD
DsssD
DDDDD
""", {'D': 'D', 's': 'sR', 'W': 'Wt'}, x + 9, y + 9)

GULL_L = """
K..........K
KK........KK
.KWW....WWK.
..KWWWWWWK..
....KWOK....
.....KK.....
"""
GULL_M = """
K........K
.KW....WK.
..KWWWWK..
....KK....
"""
GULL_S = """
K...K
.KWK.
"""
BOAT = """
.........K..........
.........KW.........
.........KWW........
.........KWWW.......
.....KKKKKWWWW......
.....KOOK...........
KKKKKKKKKKKKKKKKKKK.
KWWWWWWWWWWWWWWWWWWK
.KWWWWWWWWWWWWWWWWK.
..KKKKKKKKKKKKKKKK..
"""
FLAG = """
RRRRRRRRRRRR
.RRRRRRRRRRR
..RDWWWWDRRR
...WDWWDWRRR
..RWWDDWWRRR
.RRRRRRRRRRR
RRRRRRDRRRR.
"""

def sun(c, cx, cy, r):
    for y in range(cy - r, cy):
        for x in range(cx - r, cx + r + 1):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= r:
                c.put(x, y, 'Wt' if math.hypot(x + 0.5 - cx - 2, y + 0.5 - cy + 4) < r - 5 else 'sL')

def sprite_layer():
    objs = {}
    def new():
        return Canvas(W, H)
    o = new(); wing(o); objs['wing'] = o
    o = new(); pilot(o, 138, 103); objs['pilot'] = o
    o = new(); overlay(o, 138, 103); objs['overlay'] = o
    o = new(); sun(o, 220, HZ, 11); objs['sun'] = o
    o = new(); stamp(o, GULL_L, {'K': 'K', 'W': 'Wt', 'O': 'O'}, 90, 45); objs['gull_l'] = o
    o = new(); stamp(o, GULL_M, {'K': 'K', 'W': 'Wt'}, 195, 64); objs['gull_m'] = o
    o = new(); stamp(o, GULL_S, {'K': 'K', 'W': 'Wt'}, 233, 74); objs['gull_s'] = o
    o = new(); stamp(o, BOAT, {'K': 'K', 'W': 'Wt', 'O': 'O'}, 214, 199); objs['boat'] = o
    o = new(); stamp(o, FLAG, {'R': 'sR', 'D': 'D', 'W': 'Wt'}, 59, 19); objs['flag'] = o
    o = new(); c = o
    for (x0, y0) in ((20, 62), (25, 62), (20, 66), (25, 66)):
        c.rect(x0, y0, x0 + 4, y0 + 4, 'sL')
    c.put(20, 62, 'Wt'); objs['window'] = o
    return objs

def render():
    bg = background()
    objs = sprite_layer()
    order = ['sun', 'boat', 'gull_l', 'gull_m', 'gull_s', 'flag', 'window', 'wing', 'pilot', 'overlay']
    full = over(bg, *[objs[k] for k in order])
    return bg, objs, full

def sprite_report(objs):
    import era
    boxes = []
    for k, o in objs.items():
        m = o.g != None  # noqa: E711
        ys, xs = np.nonzero(m)
        x0, y0 = xs.min(), ys.min()
        boxes.append((int(x0), int(y0), m[y0:ys.max() + 1, x0:xs.max() + 1]))
        cols = {PAL[s] for s in o.g.ravel() if s is not None}
        if not any(cols <= set(sp) for sp in SPRPALS):
            print('sprite %s uses %s: not one sprite palette' % (k, sorted(cols)))
    return era.check_sprites(boxes, 'nes')

if __name__ == '__main__':
    bg, objs, full = render()
    save('panel-nes-bg', image(bg, PAL))
    save('panel-nes', image(full, PAL))
    bad, attr = attr_report(bg, PAL, SUBPALS, '#000000')
    print('attribute blocks off-plan:', bad[:6], len(bad))
    print('BG sub-palettes in use:', sorted(set(attr.values())))
    print('sprites:', sprite_report(objs))
    import era
    print('tiles bg:', era.unique_tiles(image(bg, PAL), 'nes'), 'full:', era.unique_tiles(image(full, PAL), 'nes'))
    print('colours:', len({PAL[s] for s in full.g.ravel()}))
