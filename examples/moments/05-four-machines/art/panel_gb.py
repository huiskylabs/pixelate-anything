"""4-shade handheld panel (Game Boy-style limits, tools/era.py 'gameboy'): 160x144, 4 shades.

Contrast does everything: shade 3 is rationed to the glider's cloth, the sun, its glitter, the crag's
rim, a few windows and the post office's sunlit gable; the crag behind the glider is shade 0. The sky
is shade 2 with 2-row checkers into shade 1 at the top and shade 3 round the sun. Sprites are 3 shades
plus transparent on object palette OBP0 (0, 2, 3): the wing, the postmaster (a shade 2 jacket so he
reads on the shade 0 crag), the satchel, gulls and the boat; 24 hardware sprites, at most 10 a line. The rock is one 32x32 metatile (periodic) so the 360 screen tiles fit the 256-tile table.

Run: python3 art/panel_gb.py -> out/panel-gb.png, out/panel-gb-bg.png (+ @4x)
"""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from common import Canvas, stamp, image, over, save, OUT, torus_cells, rock_facets

W, H = 160, 144
HZ = 76
PAL = {'g0': '#0f380f', 'g1': '#306230', 'g2': '#678e23', 'g3': '#9bbc0f'}
CRAG = [(50, 54), (55, 50), (61, 47), (66, 46), (70, 43), (74, 41), (78, 38), (81, 36), (84, 36), (86, 39),
        (89, 41), (92, 40), (95, 42), (100, 44), (105, 47), (110, 51), (115, 56), (120, 61), (125, 66),
        (129, 71), (133, 76)]

def chk(x, y):
    return (x + y) % 2 == 0

def background():
    c = Canvas(W, H, 'g2')
    # sky: shade 1 at the top, a 2-row checker into shade 2; shade 3 round the sun with a checker ring
    for y in range(0, HZ):
        for x in range(W):
            if y < 12 or (y < 14 and chk(x, y)):
                c.g[y, x] = 'g1'
    sx, r = 138, 9
    for y in range(HZ - 22, HZ):
        for x in range(sx - 26, min(W, sx + 27)):
            d = math.hypot(x + 0.5 - sx, (y + 0.5 - HZ) * 1.25)
            if d <= r:
                c.g[y, x] = 'g3'
            elif d <= r + 5 and chk(x, y):
                c.g[y, x] = 'g3'
    # one long cloud bank, lit underside (shade 3 line), body shade 1; a smaller trailing piece
    for x0, x1, y0, y1 in ((84, 150, 22, 25), (96, 140, 19, 22), (104, 124, 17, 19), (66, 88, 27, 29)):
        c.rect(x0, y0, x1, y1, 'g1')
    c.rect(86, 25, 148, 26, 'g3'); c.rect(68, 29, 86, 30, 'g3')
    c.rect(150, 22, 152, 24, 'g1'); c.put(83, 23, 'g1')
    # sea: shade 1 with shade 2 dashes on an 8 px rhythm; glitter in shade 3 under the sun
    c.rect(0, HZ, W, H, 'g1')
    wave = ["..22.........22.", "................", "........222.....", "................"]
    for y in range(HZ + 2, H):
        row = wave[y % 4]
        for x in range(W):
            if row[x % 16] == '2':
                c.g[y, x] = 'g2'
    glit = ["33......", "........", "....3...", "........", "......33", "........", ".3......", "........"]
    for ty in range(HZ // 8, 18):
        half = int(round(1 + 1.6 * (ty - HZ // 8) / 8.0))
        for tx in range(17 - half, 18 + half):
            for j in range(8):
                y = ty * 8 + j
                if y <= HZ:
                    continue
                for i in range(8):
                    if tx * 8 + i < W and glit[j][i] == "3" and (abs(tx - 17) <= half // 2 or (i + j) % 3 == 0):
                        c.g[y, tx * 8 + i] = 'g3'
    crag(c)
    town(c)
    near_cliff(c)
    office(c)
    return c

def crag(c):
    m = c.mask_poly(CRAG + [(133, 126), (50, 126)])
    c.fill(m, 'g0')
    top = np.full(W, H, int)
    for x in range(W):
        col = np.nonzero(m[:, x])[0]
        if len(col):
            top[x] = col[0]
    for x in range(W - 1):                                         # the sun-side rim, shade 3
        y, nxt = top[x], top[x + 1]
        if y < H and (nxt > y or (nxt == y and x >= 84)):
            c.g[y, x] = 'g3'
            if nxt > y + 1 and y + 1 < H:
                c.g[y + 1, x] = 'g2'
    for x0, x1, y in ((60, 68, 62), (100, 108, 66), (76, 84, 72), (112, 118, 74)):   # a few ledges
        for x in range(x0, x1):
            if m[y, x]:
                c.g[y, x] = 'g1'
    for xs, ys in (((70, 66, 69), (44, 70, 92)), ((93, 96, 92), (41, 66, 90)), ((112, 108), (54, 84))):
        for k in range(len(xs) - 1):
            c.line(xs[k], ys[k], xs[k + 1], ys[k + 1], 'g1')

def town(c):
    # the slope at the crag's foot: shade 1 ground with a shade 2 terrace wall
    c.poly([(62, 96), (80, 92), (100, 93), (118, 95), (130, 101), (133, 124), (62, 124)], 'g1')
    c.rect(64, 104, 122, 106, 'g2'); c.rect(64, 104, 122, 105, 'g3')
    def house(x0, base, w, wh, roof, rh, lit, door, chim=None):
        top = base - wh
        c.rect(x0 - 1, top - 1, x0 + w + 1, base, 'g0')
        c.rect(x0, top, x0 + w, base, 'g2')
        c.rect(x0 + w - 1, top, x0 + w, base, 'g3')                 # the sunlit corner
        if roof == 'gable':
            for k in range(rh + 1):
                a = x0 - 1 + k * (w + 2) // (2 * rh + 1); b = x0 + w + 1 - k * (w + 2) // (2 * rh + 1)
                c.rect(a - 1, top - k - 1, b + 1, top - k, 'g0'); c.rect(a, top - k, b, top - k + 1, 'g1')
        elif roof == 'hip':
            for k in range(rh):
                c.rect(x0 - 2 + k, top - k - 2, x0 + w + 2 - k, top - k - 1, 'g0')
                c.rect(x0 - 1 + k, top - k - 1, x0 + w + 1 - k, top - k, 'g1')
        elif roof == 'flat':
            c.rect(x0 - 1, top - 2, x0 + w + 1, top, 'g0'); c.rect(x0, top - 1, x0 + w, top, 'g3')
        if chim:
            c.rect(x0 + chim - 1, top - rh - 4, x0 + chim + 2, top - rh + 1, 'g0'); c.rect(x0 + chim, top - rh - 3, x0 + chim + 1, top - rh + 1, 'g1')
        for (wx, wy) in lit:
            c.rect(x0 + wx, top + wy, x0 + wx + 2, top + wy + 2, 'g3')
        if door is not None:
            c.rect(x0 + door, base - 4, x0 + door + 2, base, 'g0')
    house(66, 103, 7, 13, 'gable', 5, [(2, 3)], 3, chim=5)          # tall and narrow
    house(77, 101, 13, 6, 'hip', 2, [], 8)                           # squat cottage
    house(94, 104, 10, 9, 'flat', 0, [(2, 2)], 6)                    # flat roof
    house(109, 102, 9, 8, 'gable', 6, [], 4)                         # steep gable
    house(70, 121, 11, 6, 'hip', 2, [], 6)                           # the net shed
    house(85, 121, 9, 11, 'gable', 4, [(2, 3)], 5, chim=6)          # two storeys
    house(98, 122, 18, 8, 'hip', 3, [(2, 2), (7, 2), (12, 2)], 15)  # the harbour inn
    c.rect(120, 96, 121, 104, 'g0'); c.rect(119, 94, 122, 96, 'g3')   # the lamp post
    # quay and mole
    c.rect(62, 122, 132, 125, 'g2'); c.rect(62, 122, 132, 123, 'g3'); c.rect(62, 125, 132, 126, 'g0')
    c.rect(99, 126, 140, 129, 'g2'); c.rect(99, 126, 139, 127, 'g3'); c.rect(99, 129, 140, 130, 'g0')
    c.put(139, 126, 'g1')

ROCK = torus_cells(64, 64, [(8, 6), (30, 3), (50, 12), (19, 27), (42, 33), (60, 44), (9, 50), (31, 57)], aspect=1.6)

def near_cliff(c):
    PL = 49
    edges = [(PL, 56), (96, 62)]
    for y in range(PL, H):
        e = max(v for yy, v in edges if yy <= y)
        tile = np.tile(ROCK, (1, 2))[y % 64]
        for x in range(e):
            i = tile[x]
            if i == 0:
                l_, r_ = tile[x - 1] if x else 0, tile[x + 1]
                u_, d_ = ROCK[(y - 1) % 64, x % 64], ROCK[(y + 1) % 64, x % 64]
                s = 'g2' if (u_ > 0 and d_ > 0 and u_ != d_ and (l_ == 0 or r_ == 0)) else 'g0'
            elif tile[x + 1] != i:
                s = 'g2'
            else:
                s = 'g2' if i in (3, 7) else 'g1'
            c.g[y, x] = s
        for x in range(e - 6, e):                                  # the sunlit face, shade 3 at the edge
            c.g[y, x] = 'g3' if x >= e - 2 else ('g0' if x == e - 6 else 'g2')
    c.rect(56 - 6, 96, 62, 97, 'g3')                               # the jog is a ledge
    for x0, x1, y in ((6, 26, 76),):                               # a grassy ledge
        c.rect(x0, y, x1, y + 1, 'g3'); c.rect(x0, y + 1, x1, y + 2, 'g0')
        for tx in (9, 15, 22):
            c.rect(tx, y - 2, tx + 2, y, 'g2'); c.put(tx + 1, y - 3, 'g3')
    c.rect(0, PL - 2, 58, PL + 1, 'g2'); c.rect(0, PL - 2, 58, PL - 1, 'g3'); c.rect(0, PL + 1, 56, PL + 2, 'g0')
    for x in (5, 17, 30, 51):
        c.put(x, PL - 3, 'g2')

def office(c):
    x0, x1, wt, base = 9, 35, 33, 47
    c.rect(x0 - 1, wt - 1, x1 + 8, base, 'g0')
    c.rect(x0, wt, x1, base, 'g2')                                  # front wall in grazing light
    c.poly([(x1, wt + 0.5), (x1 + 3.5, wt - 9.5), (x1 + 7, wt + 0.5), (x1 + 7, base), (x1, base)], 'g3')
    c.rect(x1, wt, x1 + 1, base, 'g0')
    for k in range(10):                                            # slate roof, shade 1 with shade 0 courses
        y = wt - 1 - k
        a = x0 - 2 + int(round(3 * k / 9.0)); b = x1 + 1 + int(round(3 * k / 9.0))
        c.rect(a, y, b, y + 1, 'g0' if k % 3 == 0 else 'g1')
        c.put(a, y, 'g0'); c.put(b, y, 'g3')
    c.rect(x0 - 2, wt - 1, x1 + 2, wt, 'g0'); c.rect(x0 + 1, wt - 11, x1 + 4, wt - 10, 'g0')
    c.rect(14, wt - 15, 18, wt - 8, 'g0'); c.rect(15, wt - 14, 17, wt - 8, 'g2')   # chimney
    for (cx, cy, rx) in ((15, 15, 2), (10, 12, 3), (3, 9, 3)):     # smoke, streaming left
        c.rect(cx - rx, cy - 1, cx + rx, cy + 1, 'g3'); c.put(cx - rx, cy - 1, 'g2')
    c.rect(21, 39, 26, base, 'g0'); c.put(25, 43, 'g3')               # door
    c.rect(19, 34, 28, 38, 'g0')                                     # the sign with an envelope
    stamp(c, """
3333333
0333330
3033303
3300033
""".replace('3', 'w').replace('0', 'k'), {'w': 'g3', 'k': 'g0'}, 20, 34)
    c.rect(11, 39, 18, 45, 'g0'); c.rect(12, 40, 17, 44, 'g3'); c.rect(14, 40, 15, 44, 'g0')   # lit window
    c.rect(28, 39, 34, 45, 'g0'); c.rect(29, 40, 33, 44, 'g1'); c.rect(31, 42, 33, 44, 'g2')  # patched pane
    stamp(c, ".kk.\nk33k\nk33k", {'k': 'g0', '3': 'g3'}, 27, base - 3)  # mail sack
    stamp(c, ".k...k.\nkkkkkkk\nk.k.k.k\n.k...k.", {'k': 'g0'}, 1, base - 4)   # bicycle
    c.rect(43, 11, 45, base + 1, 'g0'); c.rect(44, 12, 45, base, 'g3')   # flag pole
    stamp(c, """
kkkkkkkkk
.kk33333k
..k3k3k3k
.kk33k33k
kkkkkkkkk
""".replace('3', 'w'), {'k': 'g0', 'w': 'g3'}, 34, 12)
    # the launching rail: a sloping beam, a trestle, a strut braced on the cliff face
    xa, ya, xb, yb = 43, 46, 67, 52
    for i in range(xb - xa + 1):
        x = xa + i; y = ya + int(round((yb - ya) * i / (xb - xa)))
        c.put(x, y, 'g3'); c.put(x, y + 1, 'g0')
    c.rect(66, 49, 68, 52, 'g3')
    c.line(48, 48, 46, 50, 'g0'); c.line(59, 63, 64, 52, 'g3'); c.line(60, 63, 65, 52, 'g0')

# ---------------------------------------------------------------- sprites
def wing(c):
    Lt, Nz, Rt = (65, 60), (92, 45), (112, 53)
    edge = lambda x: Lt[1] + (Rt[1] - Lt[1]) * (x - Lt[0]) / (Rt[0] - Lt[0])
    kx = Nz[0]
    tri = c.mask_poly([(Lt[0], Lt[1] + 0.5), (Nz[0] + 0.5, Nz[1]), (Rt[0] + 1, Rt[1] + 0.5)])
    bat = [72, 79, 86, 98, 105]
    stops = [Lt[0]] + bat[:3] + [kx] + bat[3:] + [Rt[0]]
    for a, b in zip(stops, stops[1:]):
        for x in range(a + 2, b - 1):
            tri[int(math.floor(edge(x))) + 1, x] = True
    for y, x in zip(*np.nonzero(tri)):
        band = y >= edge(x) - (1.5 if x < kx else 0.5)
        c.g[y, x] = 'g2' if band else 'g3'
    for bx in bat:
        for y in np.nonzero(tri[:, bx])[0][1:]:
            c.g[y, bx] = 'g2' if c.g[y, bx] == 'g3' else 'g0'
    c.line(Lt[0], Lt[1], Nz[0], Nz[1], 'g0'); c.line(Nz[0], Nz[1], Rt[0], Rt[1], 'g0')
    c.line(kx, 56, 85, 64, 'g3'); c.line(kx + 1, 56, 99, 64, 'g3')     # A-frame, light on the dark crag
    c.rect(84, 64, 101, 65, 'g3')

PILOT = """
..kkkk...
.kcccck..
.kkkkkk..
..k33k...
..k33k...
.kccccck.
kcccccccck
kcccccccck
.kccccck..
.kcckcck..
.kck.kck..
.kk..kk...
"""

def pilot(c, x, y):
    stamp(c, PILOT.replace('c', 'C'), {'k': 'g0', 'C': 'g2', '3': 'g3'}, x, y)
    c.line(x + 1, y + 5, x - 1, y, 'g2'); c.line(x + 7, y + 5, x + 9, y, 'g2')
    c.put(x - 1, y - 1, 'g3'); c.put(x + 9, y - 1, 'g3')
    for i, (sx, sy) in enumerate([(x + 1, y + 5), (x - 1, y + 5), (x - 3, y + 6), (x - 5, y + 5), (x - 7, y + 6)]):
        c.put(sx, sy, 'g3'); c.put(sx - 1, sy, 'g3')              # the scarf, light, streaming left
    c.put(x - 9, y + 7, 'g3')

def sprite_layer():
    objs = {}
    o = Canvas(W, H); wing(o); objs['wing'] = o
    o = Canvas(W, H); pilot(o, 86, 66); objs['pilot'] = o
    o = Canvas(W, H); stamp(o, "kkkk\nk22k\nk33k\nkkkk", {'k': 'g0', '2': 'g2', '3': 'g3'}, 94, 73); objs['satchel'] = o
    for name, (x, y, art) in {'gull_l': (56, 29, "k.......k\n.k3...3k.\n..k333k..\n....k...."),
                              'gull_m': (122, 41, "k.....k\n.k3.3k.\n..kkk.."),
                              'gull_s': (146, 59, "k...k\n.kkk.")}.items():
        o = Canvas(W, H); stamp(o, art, {'k': 'g0', '3': 'g3'}, x, y); objs[name] = o
    o = Canvas(W, H)
    stamp(o, """
......k.....
......k3....
......k33...
...kkkk333..
...k22k.....
kkkkkkkkkkkk
k3333333333k
.kkkkkkkkkk.
""", {'k': 'g0', '3': 'g3', '2': 'g2'}, 136, 123); objs['boat'] = o
    return objs

def oam(m):
    ys, xs = np.nonzero(m)
    out = []
    for cx in range(xs.min(), xs.max() + 1, 8):
        col = m[:, cx:cx + 8].any(1)
        rows = np.nonzero(col)[0]
        if not len(rows):
            continue
        y = rows[0]
        while y <= rows[-1]:
            if col[y:y + 8].any():
                out.append((int(cx), int(y), 8, 8))
            y += 8
    return out

def render():
    bg = background()
    objs = sprite_layer()
    # the boat's wake is background (it stays on the water)
    for k in range(0, 12, 2):
        if k % 6 != 4:
            bg.rect(134 - k, 129 - k // 5, 136 - k, 130 - k // 5, 'g2')
            bg.rect(134 - k, 131 + k // 4, 136 - k, 132 + k // 4, 'g2')
    full = over(bg, *[objs[k] for k in ('boat', 'gull_l', 'gull_m', 'gull_s', 'wing', 'pilot', 'satchel')])
    return bg, objs, full

if __name__ == '__main__':
    import era
    bg, objs, full = render()
    save('panel-gb-bg', image(bg, PAL))
    save('panel-gb', image(full, PAL))
    boxes = []
    for k, o in objs.items():
        boxes += oam(o.g != None)  # noqa: E711
    print('sprites:', era.check_sprites(boxes, 'gameboy'))
    print('tiles bg:', era.unique_tiles(image(bg, PAL), 'gameboy'), 'full:', era.unique_tiles(image(full, PAL), 'gameboy'))
