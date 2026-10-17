"""16-bit console panel (SNES-style limits, tools/era.py 'snes'): 256x224, 15-bit colour,
at most 16 colours in any 8x8 tile, three parallax background layers and a sprite layer.

  far   BG: the sunrise sky in 8 steps with 2-row checker seams, the sun and its halo, the cloud bank
  mid   BG: the crag (the cove's back wall, contre-jour), the town, the harbour, the sea, the boat
  near  BG: the near cliff, the plateau, the post office, the mail flag, the launching rail, smoke
  sprites: the glider (wing palette), the postmaster with scarf and satchel (pilot palette), 3 gulls

Run: python3 art/panel_snes.py  ->  out/panel-snes.png (+ -bg, -bg-far/-mid/-near, @4x)
"""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from common import Canvas, COMP, px, stamp, q15, image, over, save, OUT, band_sky, sprite_boxes, shade_facets, rock_facets, torus_cells
import shapes, texture, layout

W, H = 256, 224
HZ = 119                                        # the sea horizon

PAL = {k: q15(v) for k, v in {
    # sky, top to horizon
    'sk0': '#2c2a6a', 'sk1': '#433888', 'sk2': '#62479c', 'sk3': '#8c55a6', 'sk4': '#b8649e',
    'sk5': '#dc7c8e', 'sk6': '#f09c80', 'sk7': '#f6bc7c',
    'halo': '#f8d088', 'sun': '#fadc90', 'sunc': '#fce6a8',
    # cloud bank, lit from below
    'cl0': '#6e4a8e', 'cl1': '#9a5e9c', 'cl2': '#c87c98', 'cl3': '#f2ae8a', 'cl4': '#f8cc96',
    # crag (contre-jour plum) and its warm rim
    'cr0': '#1c1834', 'cr1': '#29213f', 'cr2': '#372a4f', 'cr3': '#4a3460', 'rim0': '#a85a62', 'rim1': '#e88e6a',
    # near cliff rock (ochre, lit from the right) and grass
    'nc0': '#2e2034', 'nc1': '#4a2e3e', 'nc2': '#6c4248', 'nc3': '#935a52', 'nc4': '#c27c5c', 'nc5': '#e8a46c',
    'gr0': '#2a3038', 'gr1': '#465440', 'gr2': '#76764a', 'gr3': '#b8a25c',
    # post office: plaster, slate, wood
    'wl0': '#3e3452', 'wl1': '#7a6880', 'wl2': '#ac94a0', 'wl3': '#e6c4a6', 'wl4': '#f8dcb8',
    'rf0': '#221e3a', 'rf1': '#363458', 'rf2': '#4e4c74', 'rf3': '#787294', 'rf4': '#b4949c',
    'wd0': '#2e1c26', 'wd1': '#5e3a34', 'wd2': '#946044', 'wd3': '#c8905c',
    'win': '#f8c45c', 'win1': '#d88a3c', 'gls': '#4c4a7e',
    'fl0': '#8e1e34', 'fl1': '#d8343c',
    'sm0': '#8a6c96', 'sm1': '#b68ea8',
    # town: walls in blue morning shade, sunlit side walls, terracotta roofs
    'tw0': '#2a2440', 'tw1': '#4a3e5c', 'tw2': '#6e5a76', 'tw3': '#d8a888', 'tw4': '#f0c69c',
    'tr0': '#3a1e32', 'tr1': '#5e2c3a', 'tr2': '#844040', 'tr3': '#b8604c', 'tr4': '#e08c5c',
    # stone quay and mole
    'st0': '#2c2638', 'st1': '#4a4258', 'st2': '#706478', 'st3': '#a88e8c', 'st4': '#d8b496',
    # sea: darker toward the viewer; glitter
    'se0': '#1a2242', 'se1': '#24305a', 'se2': '#34406e', 'se3': '#505480', 'se4': '#80688e', 'se5': '#b0788a',
    'gl0': '#e89a6c', 'gl1': '#f8c47c', 'gl2': '#fce0a0',
    # boat
    'bt0': '#1c1a30', 'bt1': '#2e4a5a', 'bt2': '#d0c0b4',
    # glider canvas and frame, pilot, satchel, scarf
    'cv0': '#a87868', 'cv1': '#d8a684', 'cv2': '#f0cc9e', 'cv3': '#fae6c0', 'cv4': '#fff8e6',
    'gw0': '#2a1820', 'gw1': '#6a4030', 'gw2': '#a86c44',
    'pj0': '#1c2246', 'pj1': '#36528e', 'pj2': '#6284c4', 'sk': '#f2b08c', 'skd': '#c07062',
    'sa0': '#3e2218', 'sa1': '#7a4a2a', 'sa2': '#b47a44',
    'sc0': '#a0102a', 'sc1': '#f02838',
    'gu0': '#4a4062', 'gu1': '#b4a8c0', 'gu2': '#ece0e4',
}.items()}

# ---------------------------------------------------------------- far: sky, sun, clouds
def far_layer():
    c = Canvas(W, H)
    band_sky(c, [('sk0', 0), ('sk1', 13), ('sk2', 31), ('sk3', 46), ('sk4', 64), ('sk5', 79),
                 ('sk6', 94), ('sk7', 108)])
    c.rect(0, HZ, W, H, 'sk7')
    sx, sy, r = 220, HZ, 13
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    d = np.hypot(xx - sx, (yy - sy) * 1.25)                       # the halo is a little flattened
    halo = (d <= 30) & (yy < HZ)
    chk = ((xx.astype(int) + yy.astype(int)) % 2 == 0)
    edge = (d > 27) & (d <= 30)
    for (y, x) in zip(*np.nonzero(halo & (~edge | chk))):
        if c.g[y, x] in ('sk5', 'sk6', 'sk7'):
            c.g[y, x] = 'sk7'
    inner = (d <= 21) & (yy < HZ)
    edge2 = (d > 19) & (d <= 21)
    c.fill(inner & (~edge2 | chk), 'halo')
    sun = (np.hypot(xx - sx, yy - sy) <= r) & (yy < HZ)
    c.fill(sun, 'sun')
    c.fill((np.hypot(xx - sx - 2, yy - sy + 3) <= r - 4) & (yy < HZ), 'sunc')
    # the cloud bank: one long flat mass, heads of very different size, a flat lit belly
    m = shapes.cloud_mask((H, W), 186, 37, 54, 6, r=(3, 9), spacing=8, belly=1, seed=11, vary=1.0)
    m |= shapes.cloud_mask((H, W), 214, 33, 18, 5, r=(4, 8), spacing=9, belly=0, seed=4, vary=1.0)
    m |= shapes.cloud_mask((H, W), 128, 45, 17, 2.5, r=(2, 4), spacing=9, belly=0, seed=7, vary=0.6)
    m[44:, 150:] = False; m[47:, :150] = False                     # long flat bottoms
    shade_cloud(c, m)
    # a thin high wisp behind the flag
    for x0, x1, y in ((22, 61, 12), (30, 52, 13), (60, 74, 11)):
        c.rect(x0, y, x1, y + 1, 'cl0' if y != 13 else 'sk1')
    c.rect(26, 11, 46, 12, 'cl0')
    return c

def shade_cloud(c, m):
    H_, W_ = m.shape
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        below = [m[min(H_ - 1, y + k), x] for k in (1, 2, 3)]
        right = [m[y, min(W_ - 1, x + k)] for k in (1, 2)]
        up = m[max(0, y - 1), x]
        if not below[0]:
            s = 'cl4' if x > 175 else 'cl3'                        # the lit belly, brightest toward the sun
        elif not below[1]:
            s = 'cl3' if x > 160 else 'cl2'
        elif not right[0] or not right[1]:
            s = 'cl2'
        elif not up:
            s = 'cl0'
        else:
            s = 'cl1'
        c.g[y, x] = s

# ---------------------------------------------------------------- mid: crag, town, harbour, sea, boat
CRAG = [(76, 88), (82, 82), (90, 79), (97, 75), (104, 74), (110, 70), (117, 66), (123, 63), (127, 59),
        (130, 56), (133, 56), (136, 60), (140, 63), (145, 62), (149, 65), (156, 68), (163, 71), (170, 77),
        (177, 84), (185, 92), (193, 100), (200, 108), (206, 114), (211, 119), (213, 121)]

def crag_mask():
    c = Canvas(W, H)
    return c.mask_poly(CRAG + [(213, 196), (76, 196)])

def mid_layer():
    c = Canvas(W, H)
    # sea first (right of the crag and in the harbour), darker toward the viewer
    sea = np.zeros((H, W), bool); sea[HZ:, :] = True
    band_sky(c, [('se5', HZ), ('se4', 123), ('se3', 133), ('se2', 151), ('se1', 176), ('se0', 205)], mask=sea)
    waves(c)
    glitter(c)
    # the crag
    cm = crag_mask()
    c.fill(cm, 'cr1')
    crag_rock(c, cm)
    slope(c)
    town(c)
    harbour(c)
    boat(c, 221, 207)
    return c

def waves(c):
    """short leaning dashes: a lighter top with a darker trough below, mismatched lengths"""
    rng = np.random.default_rng(5)
    rows = list(range(HZ + 3, H - 2, 3))
    for y in rows:
        t = (y - HZ) / (H - HZ)
        n = int(4 + 9 * t)
        xs = np.sort(rng.choice(np.arange(100, W - 4), n, replace=False))
        last = -10
        for x in xs:
            if x - last < 6:
                continue
            L = int(2 + rng.integers(0, 3) + 5 * t)
            base = c.get(x, y)
            if base is None or not str(base).startswith('se'):
                continue
            k = int(str(base)[2])
            up, dn = 'se%d' % min(5, k + 1), 'se%d' % max(0, k - 1)
            c.rect(x, y, x + L, y + 1, up)
            c.rect(x + 1, y + 1, x + L + 1 + (L > 4), y + 2, dn)
            last = x + L

def glitter(c):
    """the sun's path: gold dashes in a cone that narrows to the horizon"""
    rng = np.random.default_rng(9)
    sx = 220
    for y in range(HZ + 1, H, 2):
        t = (y - HZ) / (H - HZ)
        half = 3 + 20 * t
        n = int(2 + 5 * t)
        for _ in range(n):
            x = int(sx + rng.uniform(-half, half))
            L = int(1 + rng.integers(1, 3) + 4 * t)
            s = 'gl2' if (abs(x - sx) < half * 0.35 and rng.random() < 0.6) else ('gl1' if rng.random() < 0.7 else 'gl0')
            if y < HZ + 6:
                s = 'gl2'
            c.rect(x, y, x + L, y + 1, s)

FISSURES = [[(97, 76), (93, 96), (96, 120), (91, 150)],
            [(117, 66), (113, 86), (117, 104), (111, 130), (113, 152)],
            [(136, 60), (139, 80), (134, 99), (138, 126), (133, 152)],
            [(152, 67), (157, 90), (151, 112), (157, 140)],
            [(172, 79), (168, 99), (175, 121), (171, 150)],
            [(192, 99), (187, 119), (193, 142)]]

def _fx(poly, y):
    """x of a fissure polyline at row y (extended straight past its ends)"""
    for (xa, ya), (xb, yb) in zip(poly, poly[1:]):
        if ya <= y <= yb:
            return xa + (xb - xa) * (y - ya) / max(1, yb - ya)
    (xa, ya), (xb, yb) = (poly[0], poly[1]) if y < poly[0][1] else (poly[-2], poly[-1])
    return xa + (xb - xa) * (y - ya) / max(1, yb - ya)

def crag_rock(c, cm):
    """slabs split by hand-placed fissures (each slab lighter on its sun side), a few strata ledges,
    the warm rim on the right-facing crest"""
    H_, W_ = cm.shape
    top = np.full(W_, H_, int)
    for x in range(W_):
        col = np.nonzero(cm[:, x])[0]
        if len(col):
            top[x] = col[0]
    ys, xs = np.nonzero(cm)
    for y, x in zip(ys, xs):
        fx = [_fx(f, y) for f in FISSURES if y >= f[0][1] - 1]
        left = max([v for v in fx if v <= x], default=None)
        right = min([v for v in fx if v > x], default=None)
        depth = y - top[x]
        if left is not None and x - left < 1:
            c.g[y, x] = 'cr0' if depth < 92 else 'cr1'
            continue
        lo = left if left is not None else 76
        hi = right if right is not None else 214
        f = (x - lo) / max(1, hi - lo)
        if f > 0.6 and depth < 80:
            c.g[y, x] = 'cr2'
        if depth > 84 and (x + y) % 2 == 0:
            c.g[y, x] = 'cr0'
    for x0, x1, y in ((84, 96, 98), (99, 110, 87), (120, 133, 82), (142, 151, 101), (160, 170, 90),
                      (178, 186, 110), (124, 136, 115), (101, 114, 127), (147, 161, 129), (186, 199, 127)):
        for x in range(x0, x1):
            if cm[y, x] and cm[y - 1, x]:
                c.g[y, x] = 'cr0'
                c.g[y - 1, x] = 'cr3' if x >= x1 - 3 else 'cr2'
    # the sun side: the right shoulder catches grazing light in a band along the crest
    for x in range(133, W_):
        y = top[x]
        if y >= H_:
            continue
        for k in range(1, 5 + (x - 133) // 18):
            if y + k < H_ and cm[y + k, x] and c.g[y + k, x] in ('cr1', 'cr2'):
                c.g[y + k, x] = 'cr3' if k < 3 else 'cr2'
    # the warm rim on right-facing crest pixels
    for x in range(W_ - 1):
        y = top[x]
        if y >= H_:
            continue
        nxt = top[x + 1]
        if nxt > y:
            drop = min(3, nxt - y) if nxt < H_ else 3
            for k in range(drop):
                c.g[y + k, x] = 'rim1' if k == 0 else 'rim0'
        elif nxt == y and x >= 132:
            c.g[y, x] = 'rim0'
    for x in range(1, W_):
        y = top[x]
        if y < H_ and top[x - 1] > y and c.g[y, x] in ('cr1', 'cr2'):
            c.g[y, x] = 'cr3'

def slope(c):
    """the cove's foot: a shaded grassy slope with two terrace walls for the town to stand on"""
    pts = [(96, 152), (112, 147), (128, 146), (146, 148), (166, 147), (186, 150), (200, 156), (212, 166),
           (214, 194), (96, 194)]
    m = c.mask_poly(pts)
    c.fill(m, 'gr0')
    yy, xx = np.mgrid[0:H, 0:W]
    c.fill(m & (yy < 156) & ((xx + yy) % 2 == 0), 'gr1')
    for x0, x1, y in ((98, 172, 163), (104, 208, 177)):
        c.rect(x0, y, x1, y + 3, 'st1'); c.rect(x0, y, x1, y + 1, 'st3')
        for x in range(x0 + 3, x1, 6):
            c.put(x, y + 2, 'st0')
    # a lit lamp post on the upper terrace
    c.rect(197, 151, 198, 163, 'wd0'); c.rect(196, 149, 199, 151, 'win'); c.put(196, 151, 'win1')

def house(c, x0, base, w, wh, roof, rh, side, lit_windows, dark_windows=(), door=None, sag=False):
    """one town house: a front wall in morning shade, a sunlit side wall on the right, a roof"""
    top = base - wh
    c.rect(x0, top, x0 + w, base, 'tw1')
    c.rect(x0, top, x0 + 1, base, 'tw0')                          # shadow edge
    if side:
        c.rect(x0 + w, top, x0 + w + side, base, 'tw3')
        c.rect(x0 + w + side - 1, top + 1, x0 + w + side, base, 'tw4')
    c.rect(x0, base - 1, x0 + w + side, base, 'tw0')
    if roof == 'gable':                                            # gable end facing us
        for k in range(rh + 1):
            a = x0 - 1 + k * (w + 2) // (2 * rh + 1)
            b = x0 + w + 1 - k * (w + 2) // (2 * rh + 1)
            y = top - k
            c.rect(a, y, b, y + 1, 'tw1')
            c.put(a, y, 'tr1'); c.put(a + 1, y, 'tr1')
            c.put(b - 1, y, 'tr3'); c.put(b - 2, y, 'tr3')
        if side:
            c.poly([(x0 + w, top), (x0 + w + side, top - 1), (x0 + w + side, top - 2), (x0 + w // 2 + side, top - rh - 1), (x0 + w // 2, top - rh)], 'tr2')
            c.line(x0 + w // 2, top - rh, x0 + w + side, top - 2, 'tr4')
    elif roof in ('hip', 'side'):                                  # ridge parallel to the front
        for k in range(rh):
            inset = (k * 2) // 2 if roof == 'hip' else 0
            y = top - 1 - k
            sag_k = 1 if (sag and k == rh - 1) else 0
            c.rect(x0 - 1 + inset, y, x0 + w + side + 1 - inset, y + 1, 'tr2' if k % 2 == 0 else 'tr1')
            c.rect(x0 + w + side - inset - 2, y, x0 + w + side + 1 - inset, y + 1, 'tr4' if k < rh - 1 else 'tr3')
        c.rect(x0 - 1, top - 1, x0 + w + side + 1, top, 'tr0')
        ridge = top - rh
        c.rect(x0 + (rh - 1 if roof == 'hip' else 0), ridge, x0 + w + side - (rh - 1 if roof == 'hip' else 0), ridge + 1, 'tr3')
        if sag:
            mid = x0 + (w + side) // 2
            for x in range(mid - 3, mid + 4):
                c.put(x, ridge, 'tr2'); c.put(x, ridge + 1, 'tr3')
    elif roof == 'lean':                                           # single slope rising to the left
        for k in range(rh):
            y = top - 1 - k
            c.rect(x0 - 1, y, x0 + w + side + 1 - k * (w + side) // (rh + 1), y + 1, 'tr2' if k % 2 == 0 else 'tr1')
        c.line(x0 - 1, top - rh, x0 + w + side, top - 1, 'tr4')
        c.rect(x0 - 1, top - 1, x0 + w + side + 1, top, 'tr0')
    for (wx, wy, ww, whh) in lit_windows:
        c.rect(x0 + wx, top + wy, x0 + wx + ww, top + wy + whh, 'win')
        c.rect(x0 + wx, top + wy + whh - 1, x0 + wx + ww, top + wy + whh, 'win1')
    for (wx, wy, ww, whh) in dark_windows:
        c.rect(x0 + wx, top + wy, x0 + wx + ww, top + wy + whh, 'tw0')
    if door:
        dx, dw = door
        c.rect(x0 + dx, base - 6, x0 + dx + dw, base - 1, 'tw0')

def chimney(c, x, y, h, smoke=False):
    c.rect(x, y - h, x + 3, y, 'st1'); c.rect(x + 2, y - h, x + 3, y, 'st3'); c.rect(x - 1, y - h - 1, x + 4, y - h, 'st0')
    if smoke:
        for (sx, sy) in ((x, y - h - 3), (x - 2, y - h - 5), (x - 5, y - h - 6)):
            c.rect(sx, sy, sx + 3, sy + 2, 'sm0'); c.put(sx + 2, sy, 'sm1')

def flat_house(c, x0, base, w, wh, side, lit, dark, door):
    """a flat-roofed house with a parapet and a roof-terrace rail"""
    top = base - wh
    c.rect(x0, top, x0 + w, base, 'tw2'); c.rect(x0, top, x0 + 1, base, 'tw0')
    c.rect(x0 + w, top, x0 + w + side, base, 'tw3'); c.rect(x0 + w + side - 1, top, x0 + w + side, base, 'tw4')
    c.rect(x0 - 1, top - 2, x0 + w + side + 1, top, 'tw3'); c.rect(x0 - 1, top, x0 + w + side + 1, top + 1, 'tw0')
    for x in range(x0 + 1, x0 + w + side, 3):
        c.put(x, top - 3, 'tw1')
    c.rect(x0, top - 4, x0 + w + side, top - 3, 'tw1')
    for (wx, wy, ww, whh) in lit:
        c.rect(x0 + wx, top + wy, x0 + wx + ww, top + wy + whh, 'win'); c.rect(x0 + wx, top + wy + whh - 1, x0 + wx + ww, top + wy + whh, 'win1')
    for (wx, wy, ww, whh) in dark:
        c.rect(x0 + wx, top + wy, x0 + wx + ww, top + wy + whh, 'tw0')
    dx, dw = door
    c.rect(x0 + dx, base - 6, x0 + dx + dw, base - 1, 'tw0')
    c.rect(x0, base - 1, x0 + w + side, base, 'tw0')

def town(c):
    # upper terrace: a tall narrow townhouse, a squat hip-roofed cottage, a flat-roofed house, a steep gable
    house(c, 103, 160, 11, 21, 'gable', 9, 3, [(2, 3, 2, 3), (2, 10, 2, 3)], [(7, 3, 2, 3), (7, 10, 2, 3)], door=(6, 3))
    chimney(c, 108, 150, 4, smoke=True)
    house(c, 119, 157, 19, 8, 'hip', 3, 4, [(3, 3, 3, 2)], [], door=(11, 3))
    flat_house(c, 144, 163, 15, 14, 4, [(3, 3, 2, 3)], [(10, 3, 2, 3), (3, 8, 2, 3)], (9, 3))
    house(c, 168, 159, 13, 11, 'gable', 8, 3, [], [(3, 4, 2, 3), (8, 4, 2, 3)], door=(5, 3))
    c.disc(174.5, 144.5, 1.2, 'tw0')                                # a round window in the steep gable
    chimney(c, 136, 153, 3)
    # the washing line between the cottage and the flat-roofed house: three small shirts
    c.line(138, 148, 145, 149, 'tw2')
    for x, sl in ((139, 'wl4'), (142, 'cv2')):
        c.rect(x, 149, x + 2, 152, sl); c.put(x - 1, 149, sl); c.put(x + 2, 149, sl)
    # by the quay: the fisherman's shed (sagging ridge), a two-storey house with a lean-to, the harbour inn
    house(c, 108, 189, 17, 9, 'side', 4, 3, [], [(4, 3, 2, 2)], door=(9, 4), sag=True)
    house(c, 131, 188, 14, 16, 'side', 6, 3, [(3, 4, 2, 3)], [(9, 4, 2, 3), (3, 10, 2, 3)], door=(8, 3))
    house(c, 148, 188, 8, 7, 'lean', 3, 0, [(2, 2, 2, 2)], [])
    chimney(c, 140, 174, 4)
    house(c, 160, 187, 27, 12, 'hip', 5, 4, [(3, 3, 3, 3), (10, 3, 3, 3), (17, 3, 3, 3)], [(23, 3, 2, 3)], door=(14, 3))
    c.rect(186, 176, 187, 181, 'wd0'); c.rect(187, 177, 191, 180, 'wd2'); c.put(188, 178, 'win')   # the inn's sign
    # steps and a lamp on the lane
    for k, x in enumerate(range(190, 198, 2)):
        c.rect(x, 166 + k * 5, x + 6, 168 + k * 5, 'st2'); c.rect(x, 166 + k * 5, x + 6, 167 + k * 5, 'st3')

def harbour(c):
    # quay along the front row
    c.rect(100, 190, 206, 196, 'st1'); c.rect(100, 190, 206, 191, 'st3')
    for x in range(103, 206, 7):
        c.rect(x, 192, x + 1, 196, 'st0')
    c.rect(100, 195, 206, 196, 'st0')
    # the mole runs out to the right; its end is chipped
    c.rect(159, 195, 224, 200, 'st2'); c.rect(159, 195, 224, 196, 'st4'); c.rect(159, 199, 224, 200, 'st0')
    for x in range(163, 224, 6):
        c.rect(x, 197, x + 1, 199, 'st1')
    c.rect(222, 195, 224, 197, 'se3'); c.put(221, 195, 'st3')            # the chipped corner
    # lobster pots stacked on the mole
    for (x, y) in ((176, 192), (180, 192), (178, 189)):
        c.rect(x, y, x + 4, y + 3, 'wd1'); c.rect(x, y, x + 4, y + 1, 'wd3'); c.put(x + 1, y + 1, 'wd0'); c.put(x + 3, y + 2, 'wd0')
    # mooring posts with lit caps
    for x in (118, 147, 199):
        c.rect(x, 186, x + 2, 191, 'wd0'); c.put(x + 1, 186, 'wd2')

def boat(c, x, y):
    """a small fishing boat leaving the harbour, heading right: a dark hull on the glitter, a lit
    wheelhouse, a steadying sail, a broken wake behind"""
    hull = """
..........k.........
..........kw........
..........kww.......
..........kwww......
.....kkkkkkwwww.....
.....kssSk..........
.....kssSk..........
kkkkkkkkkkkkkkkkkkk.
kwwwwwwwwwwwwwwwwwWk
.kbbbbbbbbbbbbbbbbk.
..kkkkkkkkkkkkkkkk..
"""
    stamp(c, hull, {'k': 'bt0', 'w': 'bt2', 'W': 'tw4', 'b': 'bt1', 's': 'tw3', 'S': 'win'}, x, y - 10)
    for k in range(0, 22, 2):                                       # a V-wake opening behind the stern
        if k % 6 != 4:
            c.rect(x - 2 - k, y - 1 - k // 5, x - k, y - k // 5, 'gl2' if k < 10 else 'se5')
            c.rect(x - 2 - k, y + 1 + k // 4, x - k, y + 2 + k // 4, 'gl2' if k < 10 else 'se5')
    c.rect(x + 18, y - 2, x + 21, y - 1, 'gl2')
    c.rect(x + 6, y - 13, x + 8, y - 11, 'sm1'); c.rect(x + 3, y - 15, x + 6, y - 13, 'sm0')

# ---------------------------------------------------------------- near: cliff, plateau, post office, rail
CRACKS = [[(15, 77), (13, 100), (17, 128), (12, 160), (15, 224)],
          [(33, 77), (36, 104), (31, 134), (35, 170), (31, 224)],
          [(54, 77), (51, 96), (56, 122), (52, 150), (57, 190), (54, 224)],
          [(70, 77), (73, 108), (69, 140), (74, 180), (71, 224)]]
STRATA = [(0, 30, 96), (34, 52, 91), (16, 47, 118), (55, 72, 112), (0, 15, 141), (36, 68, 146),
          (18, 34, 170), (57, 75, 176), (0, 22, 197), (38, 60, 204)]

def near_layer():
    c = Canvas(W, H)
    PL = 76
    xe = shapes.ledges(PL, H, 84, step=(7, 16), jog=(1, 4), drift=0.12, lo=82, hi=104, noise=0, seed=3)
    rock = np.zeros((H, W), bool)
    for y in range(PL, H):
        rock[y, :int(xe[y - PL])] = True
    c.fill(rock, 'nc2')
    rng = np.random.default_rng(12)
    sites = [(int(x + rng.integers(-5, 6)), int(y + rng.integers(-8, 9))) for y in range(84, 232, 30)
             for x in range(4 + (y // 30 % 2) * 9, 100, 19)]
    ids = torus_cells(W, H, sites, aspect=2.1)
    rock_facets(c, rock, ids, [('nc2', 'nc3'), ('nc3', 'nc4'), ('nc1', 'nc2'), ('nc2', 'nc3'), ('nc2', 'nc4')],
                'nc0', 'nc3')
    yy, xx = np.mgrid[0:H, 0:W]
    for y in range(PL, H):                                          # the frame edge sinks into shade
        for x in range(0, 7 - (y - PL) // 30):
            if rock[y, x] and c.g[y, x] != 'nc0':
                c.g[y, x] = 'nc1'
    # ledges: a lit lip, a dark undercut, grass tufts in mismatched clumps
    for x0, x1, y, tufts in ((6, 31, 112, (9, 17, 26)), (40, 66, 139, (44, 57)), (14, 36, 171, (18, 29)),
                             (52, 74, 196, (55, 63, 70))):
        for x in range(x0, x1):
            if rock[y, x]:
                c.g[y, x] = 'nc4'; c.g[y + 1, x] = 'nc0'
                if rock[y + 2, x] and x % 3:
                    c.g[y + 2, x] = 'nc1'
        for k, tx in enumerate(tufts):
            h_ = (2, 3, 1)[k % 3]
            c.rect(tx, y - h_, tx + 2 + k % 2, y, 'gr1'); c.put(tx + 1, y - h_, 'gr2'); c.put(tx, y - 1, 'gr2')
    # the sun-facing strip along the right edge
    for y in range(PL, H):
        e = int(xe[y - PL])
        wlit = 5 + int(2.5 * math.sin(y * 0.19)) + (3 if (y // 11) % 3 == 0 else 0)
        for x in range(max(0, e - wlit), e):
            c.g[y, x] = 'nc4' if x < e - 1 else 'nc5'
        c.g[y, max(0, e - wlit - 1)] = 'nc1'
    for y in range(PL + 1, H):                                      # each jog of the edge is a ledge top
        e0, e1 = int(xe[y - PL - 1]), int(xe[y - PL])
        if e1 > e0:
            c.rect(e0 - 6, y, e1, y + 1, 'nc5')
            c.rect(e0 - 8, y + 1, e1 - 1, y + 2, 'nc3')
    # plateau grass and its lip
    c.rect(0, PL - 3, 86, PL, 'gr2')
    c.rect(0, PL - 3, 86, PL - 2, 'gr3')
    c.rect(0, PL, 85, PL + 1, 'gr1')
    for x, h in ((5, 2), (19, 1), (31, 2), (47, 1), (58, 2), (76, 1), (83, 2)):
        c.rect(x, PL - 3 - h, x + 2, PL - 3, 'gr2'); c.put(x + 1, PL - 4 - h, 'gr3')
    for x, h in ((81, 3), (84, 2), (86, 4)):                       # tufts dangling over the edge
        c.rect(x, PL, x + 1, PL + h, 'gr1')
    c.rect(0, PL + 1, 84, PL + 2, 'nc0')
    office(c)
    rail(c)
    flag(c)
    smoke(c)
    return c

def office(c):
    x0, x1, wt, base = 16, 58, 50, 73
    # front wall (grazing light) and the right gable wall (full sun)
    c.rect(x0, wt, x1, base, 'wl2')
    c.rect(x0, wt, x0 + 1, base, 'wl0')
    c.rect(x0 + 1, wt, x0 + 3, base, 'wl1')
    c.rect(x0, wt, x1, wt + 1, 'wl1')                               # the eave's shadow
    c.poly([(x1, wt + 0.5), (x1 + 5, wt - 13.5), (x1 + 10, wt + 0.5), (x1 + 10, base), (x1, base)], 'wl3')
    c.rect(x1 + 9, wt, x1 + 10, base, 'wl4')
    c.rect(x1, wt, x1 + 1, base, 'wl1')
    c.rect(x0, base - 1, x1 + 10, base, 'wl0')
    # the front roof slope: a parallelogram from the eave to the ridge, slate courses
    for k in range(14):
        y = wt - 1 - k
        a = x0 - 2 + int(round(4 * k / 13.0))
        b = x1 + 1 + int(round(4 * k / 13.0))
        c.rect(a, y, b, y + 1, 'rf1' if k % 3 == 0 else 'rf2')
        c.rect(b - 2, y, b, y + 1, 'rf3')
        c.put(b, y, 'rf4')                                           # the barge board, sunlit
    for k, x in enumerate(range(x0 + 1, x1 - 1, 5)):                 # slate joints, staggered
        c.put(x + (k % 2) * 2, wt - 3, 'rf1'); c.put(x + 3 - (k % 2), wt - 6, 'rf1'); c.put(x + 1 + (k % 3), wt - 9, 'rf1')
    c.put(x0 + 21, wt - 5, 'rf3'); c.put(x0 + 22, wt - 5, 'rf3')    # one new slate
    c.rect(x0 - 2, wt - 1, x1 + 2, wt, 'rf0')
    c.rect(x0 + 2, wt - 15, x1 + 6, wt - 14, 'rf0')
    c.rect(x0 + 2, wt - 14, x1 + 4, wt - 13, 'rf3')
    c.line(x1 + 6, wt - 14, x1 + 11, wt, 'rf1')                      # the far barge board
    # chimney (left), stone with a lit right edge
    c.rect(24, wt - 22, 30, wt - 12, 'st2'); c.rect(29, wt - 22, 30, wt - 12, 'st3')
    c.rect(23, wt - 23, 31, wt - 21, 'st1'); c.rect(23, wt - 23, 31, wt - 22, 'st3')
    c.rect(24, wt - 17, 30, wt - 16, 'st1')
    # door, a sign with an envelope, windows
    c.rect(33, 61, 40, base - 1, 'wd1'); c.rect(33, 61, 34, base - 1, 'wd0'); c.rect(32, 60, 41, 61, 'wl0')
    c.rect(39, 61, 40, base - 1, 'wd2'); c.put(38, 67, 'win')
    c.rect(30, 53, 43, 59, 'wd1'); c.rect(30, 53, 43, 54, 'wd2'); c.rect(30, 58, 43, 59, 'wd0')
    env = """
dwwwwwd
wdwwwdw
wwdwdww
wwwdwww
"""
    stamp(c, env, {'w': 'wl4', 'd': 'wd0'}, 33, 54)
    c.rect(20, 59, 28, 67, 'wl0'); c.rect(21, 60, 27, 66, 'win'); c.rect(21, 64, 27, 66, 'win1')
    c.rect(24, 60, 25, 66, 'wl0'); c.rect(21, 62, 27, 63, 'wl0'); c.rect(19, 67, 29, 68, 'wl4')
    c.rect(45, 59, 53, 67, 'wl0'); c.rect(46, 60, 52, 66, 'gls'); c.rect(49, 60, 50, 66, 'wl0'); c.rect(46, 62, 52, 63, 'wl0')
    c.rect(50, 63, 52, 66, 'wd2'); c.put(51, 64, 'wd1')                    # the patched pane
    c.put(47, 60, 'rf3'); c.rect(44, 67, 54, 68, 'wl4')
    # the mail sack slumped by the door, a bicycle against the left wall
    sack = """
.ss..
ssss.
sSSss
sSSSs
ssssd
.ddd.
"""
    stamp(c, sack, {'s': 'sa2', 'S': 'wl4', 'd': 'sa1'}, 42, base - 6)
    bike = """
..k.....k.
.kkkk.kkk.
kk.kkkk.kk
k.k.k..k.k
kk.k..k.kk
.kk....kk.
"""
    stamp(c, bike, {'k': 'wd0'}, 5, base - 6)
    c.put(7, base - 5, 'wd2'); c.put(13, base - 5, 'wd2')
    # the porch deck at the gable end where the rail starts
    c.rect(68, 68, 75, 70, 'wd2'); c.rect(68, 69, 75, 70, 'wd0')
    c.rect(69, 70, 70, 74, 'wd0'); c.rect(73, 70, 74, 74, 'wd0')

def rail(c):
    """the launching rail: a sloping beam on a trestle, braced against the cliff face, one tie missing"""
    xa, ya, xb, yb = 70, 67, 108, 79
    n = xb - xa
    for i in range(n + 1):
        x = xa + i
        y = ya + (yb - ya) * i / n
        yi = int(round(y))
        c.put(x, yi, 'wd3'); c.put(x, yi + 1, 'wd2'); c.put(x, yi + 2, 'wd1'); c.put(x, yi + 3, 'wd0')
    for k, i in enumerate(range(3, n - 1, 5)):
        if k == 4:
            continue                                               # the missing tie
        x = xa + i
        yi = int(round(ya + (yb - ya) * i / n))
        c.rect(x, yi + 4, x + 2, yi + 5, 'wd0')
    c.rect(xb - 1, yb - 2, xb + 1, yb, 'wd2')                      # the kicker at the end
    c.put(xb, yb - 2, 'wd3')
    # trestle on the plateau
    c.line(76, 70, 73, 75, 'wd0'); c.line(77, 70, 80, 75, 'wd1'); c.rect(74, 72, 80, 73, 'wd0')
    # strut braced against the cliff face
    c.line(91, 100, 101, 78, 'wd0'); c.line(92, 100, 102, 78, 'wd1')

def flag(c):
    c.rect(71, 18, 72, 74, 'wd0'); c.rect(72, 19, 73, 74, 'wd2')
    c.rect(71, 16, 73, 18, 'win'); c.put(71, 16, 'win1')
    f = """
FFFFFFFFFFFFFFF
.FFFFFFFFFFFFFF
..FFfwwwwwfFFFF
...FwfwwwfwFFFF
..FFwwfwfwwFFFF
.FFFwwwfwwwFFfF
FFFFwwwwwwwFFFF
FFFFFFFfFFFFFF.
"""
    stamp(c, f, {'F': 'fl1', 'f': 'fl0', 'w': 'wl4'}, 56, 19)

def smoke(c):
    """a plume leaving the chimney, streaming left with the wind and breaking up"""
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    for (cx, cy, rx, ry) in ((27.5, 26.0, 2.2, 1.8), (24.0, 23.5, 2.8, 2.2), (19.0, 21.0, 3.5, 2.6),
                             (12.5, 18.5, 4.2, 2.8), (4.0, 15.5, 4.6, 3.0)):
        m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
        for (yv, xv) in zip(*np.nonzero(m)):
            c.g[yv, xv] = 'sm1' if (yv + 0.5 < cy) or (xv + 0.5 > cx + rx * 0.4) else 'sm0'

# ---------------------------------------------------------------- sprites: glider, pilot, gulls
def glider(c):
    """a shallow delta canvas wing seen slightly from below: a dark leading-edge spar from the nose to
    two clean points, four battens a side showing through the cloth, the left (shade) panel darker,
    the right panel glowing with the sun behind it, a billowing hem; an A-frame under the keel"""
    Lt, Nz, Rt = (104, 91), (147, 77), (181, 82)
    edge = lambda x: Lt[1] + (Rt[1] - Lt[1]) * (x - Lt[0]) / (Rt[0] - Lt[0])     # the trailing edge line
    keel_x = Nz[0]
    tri = c.mask_poly([(Lt[0], Lt[1] + 0.5), (Nz[0] + 0.5, Nz[1]), (Rt[0] + 1, Rt[1] + 0.5)])
    left_b = [Nz[0] + (Lt[0] - Nz[0]) * f for f in (0.2, 0.42, 0.62, 0.8)]
    right_b = [Nz[0] + (Rt[0] - Nz[0]) * f for f in (0.24, 0.48, 0.7, 0.88)]
    bat = sorted(int(round(v)) for v in left_b + right_b)
    # billow: the cloth sags 1-2 px below the edge line between battens
    stops = [Lt[0]] + bat[:4] + [keel_x] + bat[4:] + [Rt[0]]
    for a, b in zip(stops, stops[1:]):
        for x in range(a + 1, b):
            f = (x - a) / max(1, b - a)
            sag = 2 if 0.3 < f < 0.7 and b - a > 8 else (1 if 0.12 < f < 0.88 else 0)
            for k in range(1, sag + 1):
                tri[int(math.floor(edge(x))) + k, x] = True
    ys, xs = np.nonzero(tri)
    for y, x in zip(ys, xs):
        depth = y - (Nz[1] + (abs(x - keel_x) / (keel_x - Lt[0] if x < keel_x else Rt[0] - keel_x)) * ((Lt[1] if x < keel_x else Rt[1]) - Nz[1]))
        low = y >= edge(x) - 1
        if x < keel_x:                                              # the shade panel
            s_ = 'cv1' if low else ('cv2' if depth > 1 else 'cv3')
        else:                                                        # the sunlit panel
            s_ = 'cv2' if low else ('cv4' if depth > 1.5 else 'cv3')
        c.g[y, x] = s_
    for bx in bat:                                                   # battens through the cloth
        col = np.nonzero(tri[:, bx])[0]
        for y in col[1:]:
            c.g[y, bx] = 'cv1' if bx > keel_x else 'cv0'
    col = np.nonzero(tri[:, keel_x])[0]
    for y in col:
        c.g[y, keel_x] = 'gw1'
    c.line(Lt[0], Lt[1], Nz[0], Nz[1], 'gw0'); c.line(Nz[0], Nz[1], Rt[0], Rt[1], 'gw0')
    c.line(Lt[0] + 2, Lt[1], Nz[0], Nz[1] + 1, 'gw2'); c.line(Nz[0] + 1, Nz[1] + 1, Rt[0] - 2, Rt[1], 'gw2')
    # the A-frame and the control bar under the keel
    c.line(keel_x, 86, 137, 101, 'gw1'); c.line(keel_x + 1, 86, 158, 101, 'gw1')
    c.rect(135, 101, 161, 102, 'gw0'); c.rect(136, 100, 160, 101, 'gw2')
    c.line(keel_x, 86, keel_x - 1, 104, 'gw0')                         # the hang strap

PILOT = """
......kkkkk......
.....kcccgck.....
.....kcccccck....
.....kkvvvvvk....
......kssssd.....
......ksssdd.....
....rrRkssk......
..rRRrRRjjjJjk...
.rR..kjjjjjJJJk..
rR...kjjjjjJJJJk.
.....kjjjjjjJJJk.
.....kjjjtjjjJk..
.....kjjjjtjjJk..
......kbbbbtbbk..
......kbbkkbbbk..
......kbbk.kbbk..
.....kbbk...kbbk.
.....kbbk...kbbk.
.....kmmk...kmmk.
....kmmmk...kmmmk
"""

def pilot(c, x, y):
    key = {'k': 'pj0', 'c': 'pj1', 'g': 'win', 'v': 'pj0', 's': 'sk', 'd': 'skd', 'j': 'pj1', 'J': 'pj2',
           'b': 'pj1', 'r': 'sc0', 'R': 'sc1', 't': 'sa1', 'm': 'sa0'}
    stamp(c, PILOT, key, x, y)
    # the scarf streams left with the wind: a 2 px ribbon off the collar, a forked end
    rib = [(x + 4, y + 6), (x + 2, y + 6), (x, y + 7), (x - 2, y + 7), (x - 4, y + 6), (x - 6, y + 7), (x - 8, y + 8)]
    for i, (sx, sy) in enumerate(rib):
        for k in range(2):
            c.put(sx - k, sy, 'sc1'); c.put(sx - k, sy + 1, 'sc0' if i % 3 == 2 else 'sc1')
    c.put(x - 10, y + 7, 'sc1'); c.put(x - 10, y + 10, 'sc0'); c.put(x - 9, y + 10, 'sc1')
    # arms reach up and out to the bar
    c.line(x + 6, y + 8, x + 3, y + 1, 'pj1'); c.line(x + 7, y + 8, x + 4, y + 1, 'pj1')
    c.line(x + 13, y + 8, x + 15, y + 1, 'pj2'); c.line(x + 14, y + 8, x + 16, y + 1, 'pj2')
    c.put(x + 3, y, 'sk'); c.put(x + 4, y, 'sk'); c.put(x + 15, y, 'sk'); c.put(x + 16, y, 'sk')
    for yy in range(y + 8, y + 13):                                 # the sun-side rim on the jacket
        col = [xx for xx in range(x, x + 18) if c.get(xx, yy) in ('pj1', 'pj2')]
        if col:
            c.put(max(col), yy, 'cv2')

SATCHEL = """
.kkkkkk.
kaaaaaak
kAAAAAAk
kaaWWaak
kaaaaaak
.kkkkkk.
"""

GULLS = {
    'L': """
k..........k
kk........kk
.kww....wwk.
..kwwggwwk..
....kggk....
.....kk.....
""",
    'M': """
k........k
.kw....wk.
..kwggwk..
....kk....
""",
    'S': """
k...k
.kgk.
""",
}

def sprites():
    c = Canvas(W, H)
    glider(c)
    pilot(c, 136, 102)
    stamp(c, SATCHEL, {'k': 'sa0', 'a': 'sa1', 'A': 'sa2', 'W': 'cv3'}, 150, 112)
    for (u, v, s) in COMP['gulls']:
        g = GULLS[s]
        stamp(c, g, {'k': 'gu0', 'w': 'gu1', 'g': 'gu2'}, px(u, W), px(v, H))
    return c

def render():
    far, mid, near, spr = far_layer(), mid_layer(), near_layer(), sprites()
    bg = over(far, mid, near)
    full = over(far, mid, near, spr)
    return far, mid, near, spr, bg, full

if __name__ == '__main__':
    far, mid, near, spr, bg, full = render()
    for name, L in (('panel-snes-bg-far', far), ('panel-snes-bg-mid', mid), ('panel-snes-bg-near', near)):
        image(L, PAL).save(OUT / ('%s.png' % name))
    save('panel-snes-bg', image(bg, PAL))
    save('panel-snes', image(full, PAL))
    import era
    boxes = [(100, 74, spr.g[74:124, 100:186] != None)] + \
            [(px(u, W), px(v, H), spr.g[px(v, H):px(v, H) + 6, px(u, W):px(u, W) + 12] != None) for u, v, s in COMP['gulls']]
    print('sprites:', era.check_sprites(boxes, 'snes'))
    print('colours:', len(set(full.g.ravel()) - {None}))
