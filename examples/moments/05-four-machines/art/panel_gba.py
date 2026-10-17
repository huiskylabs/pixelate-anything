"""32-bit handheld panel (GBA-style limits, tools/era.py 'gba'): 240x160, 15-bit colour, at most
16 colours in any 8x8 tile; BG layers plus sprites.

Rethought for the machine, not scaled: the screen is wide and short, so the composition keeps its
proportions (the shared layout at 0.78 of the 16-bit size) and the extra 40 px of width go to open
sea and the boat. The palette is high-key and saturated, made for an unlit handheld screen: lifted
shadows, a pastel sunrise. Every object is drawn here at this size.

  far   BG: sky in 8 steps with 2-row checker seams, the sun and halo, the cloud bank
  mid   BG: the crag, the town on its terraces, the harbour, the sea, the boat
  near  BG: the near cliff, the post office, the flag, the rail, smoke
  sprites: the glider (wing palette), the postmaster (pilot palette), gulls

Run: python3 art/panel_gba.py  ->  out/panel-gba.png (+ -bg, -bg-far/-mid/-near, @4x)
"""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from common import Canvas, stamp, q15, image, over, save, OUT, band_sky
from panel_snes import house, _fx
import shapes, texture

W, H = 240, 160
HZ = 85
SUN = (172, HZ, 11)

PAL = {k: q15(v) for k, v in {
    'sk0': '#4a58b8', 'sk1': '#6862c4', 'sk2': '#8a6ccc', 'sk3': '#b278c8', 'sk4': '#da88bc',
    'sk5': '#f2a0aa', 'sk6': '#fcbc9a', 'sk7': '#fcd6a0', 'halo': '#fce2aa', 'sun': '#fcecb8',
    'cl0': '#9478c4', 'cl1': '#c08ac6', 'cl2': '#e8a0c0', 'cl3': '#fcc2a8', 'cl4': '#fcdcb4',
    'cr0': '#382a58', 'cr1': '#4a386c', 'cr2': '#5c487e', 'cr3': '#76568c', 'rim0': '#d07878', 'rim1': '#fca880',
    'nc0': '#583a50', 'nc1': '#784c5a', 'nc2': '#a06864', 'nc3': '#c8886c', 'nc4': '#eaa874', 'nc5': '#fcd08c',
    'gr0': '#3c5852', 'gr1': '#587852', 'gr2': '#8c9e5a', 'gr3': '#c8c470',
    'wl0': '#584c76', 'wl1': '#9886a6', 'wl2': '#ceb8c2', 'wl3': '#fcdcc0', 'wl4': '#fff0d8',
    'rf0': '#2c386a', 'rf1': '#42548c', 'rf2': '#5a72aa', 'rf3': '#889ec8', 'rf4': '#c8c4d4',
    'wd0': '#482a34', 'wd1': '#7c4c40', 'wd2': '#b27a50', 'wd3': '#e2aa6c',
    'win': '#fcd86c', 'win1': '#ee9e48', 'gls': '#6a76b6', 'fl0': '#be2848', 'fl1': '#fc4850',
    'sm0': '#b29ac0', 'sm1': '#dac2d8',
    'tw0': '#48426e', 'tw1': '#6c628e', 'tw2': '#9286aa', 'tw3': '#eec2a4', 'tw4': '#fcdebc',
    'tr0': '#5c2c48', 'tr1': '#8c3c50', 'tr2': '#be5858', 'tr3': '#e67e60', 'tr4': '#fcaa74',
    'st0': '#484260', 'st1': '#6c6682', 'st2': '#988ea2', 'st3': '#c6b6b2', 'st4': '#eed6be',
    'se0': '#283876', 'se1': '#364a8e', 'se2': '#4a5ea2', 'se3': '#6a72b2', 'se4': '#9886ba', 'se5': '#ca96b2',
    'gl0': '#fcae7c', 'gl1': '#fcce8c', 'gl2': '#fff0bc',
    'bt0': '#28284a', 'bt1': '#38788a', 'bt2': '#f4ece0',
    'cv0': '#c29280', 'cv1': '#e6ba98', 'cv2': '#fcdab0', 'cv3': '#ffeed0', 'cv4': '#fffcf2',
    'gw0': '#382028', 'gw1': '#784a38', 'gw2': '#ba8250',
    'pj0': '#20306a', 'pj1': '#3c62b2', 'pj2': '#6a96de', 'sk': '#fcc29e', 'skd': '#d68a76',
    'sa0': '#4c2a1e', 'sa1': '#985c34', 'sa2': '#d29654', 'bk': '#fce070',
    'sc0': '#c41838', 'sc1': '#ff3a46',
    'gu0': '#5c5280', 'gu1': '#cec6da', 'gu2': '#fff2f2',
}.items()}

# ---------------------------------------------------------------- far
def far_layer():
    c = Canvas(W, H)
    band_sky(c, [('sk0', 0), ('sk1', 9), ('sk2', 21), ('sk3', 33), ('sk4', 45), ('sk5', 56),
                 ('sk6', 67), ('sk7', 77)])
    c.rect(0, HZ, W, H, 'sk7')
    sx, sy, r = SUN
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    chk = (xx.astype(int) + yy.astype(int)) % 2 == 0
    d = np.hypot(xx - sx, (yy - sy) * 1.3)
    for rr, sl in ((24, 'sk7'), (16, 'halo')):
        m = (d <= rr) & (yy < HZ) & ((d <= rr - 2) | chk)
        for (y, x) in zip(*np.nonzero(m)):
            if sl == 'halo' or c.g[y, x] in ('sk5', 'sk6', 'sk7'):
                c.g[y, x] = sl
    c.fill((np.hypot(xx - sx, yy - sy) <= r) & (yy < HZ), 'sun')
    m = shapes.cloud_mask((H, W), 158, 25, 46, 5, r=(3, 7), spacing=8, belly=1, seed=21, vary=1.0)
    m |= shapes.cloud_mask((H, W), 206, 20, 15, 4, r=(3, 6), spacing=9, belly=0, seed=8, vary=1.0)
    m |= shapes.cloud_mask((H, W), 104, 33, 13, 2, r=(2, 3), spacing=9, belly=0, seed=6, vary=0.5)
    m[31:, 118:] = False; m[35:, :118] = False
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        b1, b2 = m[min(H - 1, y + 1), x], m[min(H - 1, y + 2), x]
        rt = m[y, min(W - 1, x + 1)] and m[y, min(W - 1, x + 2)]
        if not b1:
            s = 'cl4' if x > 150 else 'cl3'
        elif not b2:
            s = 'cl3' if x > 135 else 'cl2'
        elif not rt:
            s = 'cl2'
        elif not m[max(0, y - 1), x]:
            s = 'cl0'
        else:
            s = 'cl1'
        c.g[y, x] = s
    for x0, x1, y in ((14, 44, 9), (20, 34, 10), (46, 58, 8)):
        c.rect(x0, y, x1, y + 1, 'cl0' if y != 10 else 'sk1')
    return c

# ---------------------------------------------------------------- mid
CRAG = [(59, 63), (64, 58), (70, 56), (76, 53), (81, 52), (86, 49), (91, 46), (95, 43), (99, 40), (102, 38),
        (105, 39), (108, 42), (112, 44), (116, 43), (120, 46), (126, 48), (132, 51), (138, 56), (144, 61),
        (150, 67), (156, 72), (161, 78), (165, 83), (167, 86)]
FISS = [[(76, 53), (73, 70), (75, 88), (71, 108)],
        [(91, 46), (88, 62), (91, 78), (87, 98), (89, 112)],
        [(107, 41), (110, 58), (106, 74), (109, 96), (105, 112)],
        [(121, 46), (125, 64), (120, 82), (124, 104)],
        [(137, 55), (134, 71), (139, 88), (136, 108)],
        [(153, 70), (150, 86), (154, 104)]]

def mid_layer():
    c = Canvas(W, H)
    sea = np.zeros((H, W), bool); sea[HZ:, :] = True
    band_sky(c, [('se5', HZ), ('se4', 88), ('se3', 96), ('se2', 109), ('se1', 127), ('se0', 147)], mask=sea)
    rng = np.random.default_rng(15)
    for y in range(HZ + 3, H - 1, 3):
        t = (y - HZ) / (H - HZ)
        last = -10
        for x in np.sort(rng.choice(np.arange(76, W - 3), int(4 + 10 * t), replace=False)):
            if x - last < 6:
                continue
            base = c.get(x, y)
            if base is None or not str(base).startswith('se'):
                continue
            k = int(str(base)[2]); L = int(2 + rng.integers(0, 3) + 4 * t)
            c.rect(x, y, x + L, y + 1, 'se%d' % min(5, k + 1))
            c.rect(x + 1, y + 1, x + L + 1, y + 2, 'se%d' % max(0, k - 1))
            last = x + L
    sx = SUN[0]
    for y in range(HZ + 1, H, 2):
        t = (y - HZ) / (H - HZ)
        half = 3 + 21 * t
        for _ in range(int(2 + 5 * t)):
            x = int(sx + rng.uniform(-half, half)); L = int(1 + rng.integers(1, 3) + 4 * t)
            s = 'gl2' if (abs(x - sx) < half * 0.35 and rng.random() < 0.6) or y < HZ + 5 else ('gl1' if rng.random() < 0.7 else 'gl0')
            c.rect(x, y, x + L, y + 1, s)
    cm = c.mask_poly(CRAG + [(167, 146), (59, 146)])
    c.fill(cm, 'cr1')
    crag_rock(c, cm)
    slope(c)
    town(c)
    harbour(c)
    boat(c, 193, 153)
    return c

def crag_rock(c, cm):
    top = np.full(W, H, int)
    for x in range(W):
        col = np.nonzero(cm[:, x])[0]
        if len(col):
            top[x] = col[0]
    for y, x in zip(*np.nonzero(cm)):
        fx = [_fx(f, y) for f in FISS if y >= f[0][1] - 1]
        left = max([v for v in fx if v <= x], default=None)
        right = min([v for v in fx if v > x], default=None)
        depth = y - top[x]
        if left is not None and x - left < 1:
            c.g[y, x] = 'cr0' if depth < 66 else 'cr1'
            continue
        lo = left if left is not None else 59
        hi = right if right is not None else 168
        if (x - lo) / max(1, hi - lo) > 0.6 and depth < 58:
            c.g[y, x] = 'cr2'
        if depth > 60 and (x + y) % 2 == 0:
            c.g[y, x] = 'cr0'
    for x0, x1, y in ((66, 74, 72), (78, 86, 64), (94, 103, 60), (111, 118, 75), (126, 133, 66), (140, 147, 82),
                      (97, 106, 86), (80, 90, 94), (115, 125, 96)):
        for x in range(x0, x1):
            if cm[y, x] and cm[y - 1, x]:
                c.g[y, x] = 'cr0'; c.g[y - 1, x] = 'cr3' if x >= x1 - 2 else 'cr2'
    for x in range(104, W):
        y = top[x]
        if y >= H:
            continue
        for k in range(1, 4 + (x - 104) // 16):
            if cm[min(H - 1, y + k), x] and c.g[y + k, x] in ('cr1', 'cr2'):
                c.g[y + k, x] = 'cr3' if k < 3 else 'cr2'
    for x in range(W - 1):
        y = top[x]
        if y >= H:
            continue
        nxt = top[x + 1]
        if nxt > y:
            for k in range(min(3, nxt - y) if nxt < H else 3):
                c.g[y + k, x] = 'rim1' if k == 0 else 'rim0'
        elif nxt == y and x >= 103:
            c.g[y, x] = 'rim0'
    for x in range(1, W):
        y = top[x]
        if y < H and top[x - 1] > y and c.g[y, x] in ('cr1', 'cr2'):
            c.g[y, x] = 'cr3'

def slope(c):
    pts = [(77, 110), (90, 106), (104, 105), (118, 107), (134, 106), (148, 109), (158, 114), (166, 122),
           (168, 146), (77, 146)]
    m = c.mask_poly(pts)
    c.fill(m, 'gr0')
    yy, xx = np.mgrid[0:H, 0:W]
    c.fill(m & (yy < 113) & ((xx + yy) % 2 == 0), 'gr1')
    for x0, x1, y in ((79, 136, 120), (84, 164, 131)):
        c.rect(x0, y, x1, y + 2, 'st1'); c.rect(x0, y, x1, y + 1, 'st3')
    c.rect(152, 110, 153, 120, 'wd0'); c.rect(151, 108, 154, 110, 'win'); c.put(151, 110, 'win1')

def town(c):
    # back row on the upper terrace
    house(c, 81, 118, 13, 9, 'gable', 5, 3, [(2, 3, 2, 2)], [(8, 3, 2, 2)], door=(5, 2))
    house(c, 98, 116, 10, 12, 'lean', 4, 2, [(2, 2, 2, 2)], [(6, 7, 2, 2)])
    house(c, 113, 119, 17, 9, 'hip', 4, 3, [(3, 2, 2, 2), (12, 2, 2, 2)], [(7, 2, 2, 2)], door=(8, 2))
    house(c, 138, 117, 11, 10, 'gable', 5, 3, [], [(3, 3, 2, 2), (7, 3, 2, 2)], door=(4, 2))
    c.line(109, 108, 114, 109, 'tw2')
    c.rect(110, 109, 112, 111, 'wl4'); c.rect(112, 109, 114, 111, 'cv2')
    # front row by the quay
    house(c, 86, 140, 16, 10, 'hip', 5, 3, [(3, 3, 2, 2)], [(10, 3, 2, 2)], door=(7, 2))
    house(c, 106, 141, 12, 8, 'side', 3, 2, [], [], door=(4, 3), sag=True)
    house(c, 123, 141, 19, 12, 'gable', 6, 3, [(3, 3, 2, 2), (13, 3, 2, 2)], [(8, 7, 2, 2)], door=(8, 2))
    for k, x in enumerate(range(147, 155, 2)):
        c.rect(x, 123 + k * 3, x + 4, 124 + k * 3, 'st3')

def harbour(c):
    c.rect(78, 141, 160, 145, 'st1'); c.rect(78, 141, 160, 142, 'st3')
    for x in range(81, 160, 6):
        c.rect(x, 143, x + 1, 145, 'st0')
    c.rect(124, 145, 176, 149, 'st2'); c.rect(124, 145, 176, 146, 'st4'); c.rect(124, 148, 176, 149, 'st0')
    c.rect(174, 145, 176, 146, 'se3')
    for (x, y) in ((138, 143), (141, 143), (139, 141)):
        c.rect(x, y, x + 3, y + 2, 'wd1'); c.rect(x, y, x + 3, y + 1, 'wd3')
    for x in (95, 118, 156):
        c.rect(x, 137, x + 2, 141, 'wd0'); c.put(x + 1, 137, 'wd2')

def boat(c, x, y):
    hull = """
.........k.......
.........kw......
.........kww.....
.....kkkkkwww....
.....kssSk.......
kkkkkkkkkkkkkkkk.
kwwwwwwwwwwwwwwWk
.kbbbbbbbbbbbbbk.
..kkkkkkkkkkkkk..
"""
    stamp(c, hull, {'k': 'bt0', 'w': 'bt2', 'W': 'tw4', 'b': 'bt1', 's': 'tw3', 'S': 'win'}, x, y - 8)
    for x0, x1, yy in ((x - 12, x - 6, y), (x - 4, x, y + 1), (x - 19, x - 15, y - 1)):
        c.rect(x0, yy, x1, yy + 1, 'gl2')

# ---------------------------------------------------------------- near
CRACKS = [[(12, 53), (10, 70), (14, 92), (10, 116), (12, 160)],
          [(27, 53), (29, 76), (25, 98), (28, 124), (25, 160)],
          [(43, 53), (41, 70), (45, 92), (42, 112), (45, 136), (43, 160)],
          [(56, 53), (58, 78), (55, 102), (59, 130), (56, 160)]]
STRATA = [(0, 24, 68), (28, 42, 64), (14, 38, 85), (44, 58, 81), (0, 12, 101), (29, 54, 105),
          (14, 27, 122), (46, 60, 127), (0, 18, 142)]

def near_layer():
    c = Canvas(W, H)
    PL = 52
    xe = shapes.ledges(PL, H, 66, step=(6, 13), jog=(1, 3), drift=0.11, lo=64, hi=82, noise=0, seed=7)
    rock = np.zeros((H, W), bool)
    for y in range(PL, H):
        rock[y, :int(xe[y - PL])] = True
    c.fill(rock, 'nc2')
    cuts = sorted(set([PL] + [y for _, _, y in STRATA] + [H]))
    for y in range(PL + 1, H):
        band = sum(1 for cy in cuts if cy <= y)
        xs = [_fx(cr, y) + ((band * 5 + i * 3) % 5) - 2 for i, cr in enumerate(CRACKS)]
        e = int(xe[y - PL])
        for x in range(0, e):
            left = max([v for v in xs if v <= x], default=0)
            right = min([v for v in xs if v > x], default=e)
            if x - left < 1 and left > 0:
                c.g[y, x] = 'nc0'
            elif right - x <= 2:
                c.g[y, x] = 'nc3'
            elif x - left <= 1 and left > 0:
                c.g[y, x] = 'nc1'
        for x in range(0, min(e, 9 - (y - PL) // 16)):
            c.g[y, x] = 'nc1'
    for pts, sl in (([(30, 58), (47, 56), (51, 68), (45, 80), (33, 76)], 'nc3'),
                    ([(13, 90), (24, 87), (27, 106), (17, 111)], 'nc1'),
                    ([(37, 108), (51, 104), (55, 122), (42, 127)], 'nc3')):
        m = c.mask_poly(pts) & rock
        for (yv, xv) in zip(*np.nonzero(m)):
            if c.g[yv, xv] == 'nc2':
                c.g[yv, xv] = sl
    for x0, x1, y in STRATA:
        for x in range(x0, x1):
            if rock[y, x] and c.g[y, x] != 'nc0':
                c.g[y, x] = 'nc0'
                if c.g[y - 1, x] in ('nc2', 'nc1'):
                    c.g[y - 1, x] = 'nc3'
    for y in range(PL, H):
        e = int(xe[y - PL])
        wlit = 4 + int(2 * math.sin(y * 0.23)) + (2 if (y // 9) % 3 == 0 else 0)
        for x in range(max(0, e - wlit), e):
            c.g[y, x] = 'nc4' if x < e - 1 else 'nc5'
        c.g[y, max(0, e - wlit - 1)] = 'nc1'
    for y in range(PL + 1, H):
        e0, e1 = int(xe[y - PL - 1]), int(xe[y - PL])
        if e1 > e0:
            c.rect(e0 - 5, y, e1, y + 1, 'nc5'); c.rect(e0 - 6, y + 1, e1 - 1, y + 2, 'nc3')
    c.rect(0, PL - 3, 68, PL, 'gr2'); c.rect(0, PL - 3, 68, PL - 2, 'gr3'); c.rect(0, PL, 67, PL + 1, 'gr1')
    for x, h in ((4, 1), (15, 2), (29, 1), (41, 2), (60, 1)):
        c.rect(x, PL - 3 - h, x + 2, PL - 3, 'gr2'); c.put(x + 1, PL - 4 - h, 'gr3')
    for x, h in ((64, 2), (67, 3)):
        c.rect(x, PL, x + 1, PL + h, 'gr1')
    c.rect(0, PL + 1, 66, PL + 2, 'nc0')
    office(c)
    rail(c)
    flag(c)
    smoke(c)
    return c

def office(c):
    x0, x1, wt, base = 12, 43, 34, 50
    c.rect(x0, wt, x1, base, 'wl2')
    c.rect(x0, wt, x0 + 1, base, 'wl0'); c.rect(x0 + 1, wt, x0 + 2, base, 'wl1')
    c.rect(x0, wt, x1, wt + 1, 'wl1')
    c.poly([(x1, wt + 0.5), (x1 + 4, wt - 10.5), (x1 + 8, wt + 0.5), (x1 + 8, base), (x1, base)], 'wl3')
    c.rect(x1 + 7, wt, x1 + 8, base, 'wl4'); c.rect(x1, wt, x1 + 1, base, 'wl1')
    c.rect(x0, base - 1, x1 + 8, base, 'wl0')
    for k in range(11):
        y = wt - 1 - k
        a = x0 - 2 + int(round(3 * k / 10.0)); b = x1 + 1 + int(round(3 * k / 10.0))
        c.rect(a, y, b, y + 1, 'rf1' if k % 3 == 0 else 'rf2')
        c.rect(b - 2, y, b, y + 1, 'rf3'); c.put(b, y, 'rf4')
    for k, x in enumerate(range(x0 + 1, x1 - 1, 5)):
        c.put(x + (k % 2) * 2, wt - 3, 'rf1'); c.put(x + 3 - (k % 2), wt - 6, 'rf1')
    c.rect(x0 - 2, wt - 1, x1 + 2, wt, 'rf0')
    c.rect(x0 + 1, wt - 12, x1 + 5, wt - 11, 'rf0'); c.rect(x0 + 1, wt - 11, x1 + 3, wt - 10, 'rf3')
    c.line(x1 + 5, wt - 11, x1 + 9, wt, 'rf1')
    c.rect(18, wt - 17, 23, wt - 9, 'st2'); c.rect(22, wt - 17, 23, wt - 9, 'st3')
    c.rect(17, wt - 18, 24, wt - 16, 'st1'); c.rect(17, wt - 18, 24, wt - 17, 'st3')
    # door and the envelope sign
    c.rect(25, 41, 30, base - 1, 'wd1'); c.rect(25, 41, 26, base - 1, 'wd0'); c.rect(29, 41, 30, base - 1, 'wd2')
    c.rect(24, 40, 31, 41, 'wl0'); c.put(28, 45, 'win')
    c.rect(23, 35, 33, 39, 'wd1'); c.rect(23, 38, 33, 39, 'wd0')
    stamp(c, """
dwwwwd
wdwwdw
wwddww
""", {'w': 'wl4', 'd': 'wd0'}, 25, 35)
    # windows: lamp-lit left, dark right with a patched pane
    c.rect(15, 40, 22, 46, 'wl0'); c.rect(16, 41, 21, 45, 'win'); c.rect(16, 44, 21, 45, 'win1')
    c.rect(18, 41, 19, 45, 'wl0'); c.rect(15, 46, 22, 47, 'wl4')
    c.rect(34, 40, 41, 46, 'wl0'); c.rect(35, 41, 40, 45, 'gls'); c.rect(37, 41, 38, 45, 'wl0')
    c.rect(38, 43, 40, 45, 'wd2'); c.rect(34, 46, 41, 47, 'wl4')
    stamp(c, """
.ss.
sSss
sSSs
.dd.
""", {'s': 'sa2', 'S': 'wl4', 'd': 'sa1'}, 31, base - 4)
    stamp(c, """
.k....k.
kkkkkkkk
k.kk.k.k
.k....k.
""", {'k': 'wd0'}, 3, base - 4)
    c.rect(51, 45, 57, 47, 'wd2'); c.rect(51, 46, 57, 47, 'wd0'); c.rect(52, 47, 53, 50, 'wd0')

def rail(c):
    xa, ya, xb, yb = 55, 44, 84, 54
    n = xb - xa
    for i in range(n + 1):
        x = xa + i; yi = int(round(ya + (yb - ya) * i / n))
        c.put(x, yi, 'wd3'); c.put(x, yi + 1, 'wd2'); c.put(x, yi + 2, 'wd0')
    for k, i in enumerate(range(3, n - 1, 4)):
        if k == 3:
            continue
        x = xa + i; yi = int(round(ya + (yb - ya) * i / n))
        c.put(x, yi + 3, 'wd0')
    c.rect(xb - 1, yb - 2, xb + 1, yb, 'wd2'); c.put(xb, yb - 2, 'wd3')
    c.line(60, 47, 58, 51, 'wd0'); c.line(61, 47, 63, 51, 'wd1')
    c.line(71, 70, 79, 53, 'wd0'); c.line(72, 70, 80, 53, 'wd1')

def flag(c):
    c.rect(55, 9, 56, 51, 'wd0'); c.rect(56, 10, 57, 51, 'wd2')
    c.rect(55, 7, 57, 9, 'win')
    stamp(c, """
FFFFFFFFFFFF
.FFFFFFFFFFF
..FfwwwwfFFF
...wfwwfwFFF
..FwwffwwFFF
.FFFFFFFFFFF
FFFFFFfFFFF.
""", {'F': 'fl1', 'f': 'fl0', 'w': 'wl4'}, 43, 10)

def smoke(c):
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    for (cx, cy, rx, ry) in ((21.0, 14.5, 1.8, 1.5), (18.0, 12.5, 2.4, 1.8), (13.5, 10.5, 3.0, 2.2), (7.0, 8.5, 3.6, 2.4)):
        m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
        for (yv, xv) in zip(*np.nonzero(m)):
            c.g[yv, xv] = 'sm1' if (yv + 0.5 < cy) or (xv + 0.5 > cx + rx * 0.4) else 'sm0'

# ---------------------------------------------------------------- sprites
def glider(c):
    """the wing at this size: 60 px, a two-tone rib shading, a scalloped hem, the spar on top"""
    xa, ya, xb, yb = 84, 63, 143, 53
    lead = lambda x: ya + (yb - ya) * (x - xa) / (xb - xa)
    chord = lambda x: max(4.0, 10.0 - 5.5 * abs(x - 111) / 32.0)
    ribs = [90, 97, 104, 111, 118, 124, 130, 136]
    wing = np.zeros((H, W), bool)
    for x in range(xa, xb + 1):
        y0, y1 = lead(x), lead(x) + chord(x)
        for y in range(int(math.floor(y0)), int(math.ceil(y1)) + 1):
            if y0 - 0.5 <= y < y1:
                wing[y, x] = True
    bounds = [xa] + ribs + [xb]
    for r0, r1 in zip(bounds, bounds[1:]):
        for x in range(r0 + 2, r1 - 1):
            col = np.nonzero(wing[:, x])[0]
            if len(col) > 4:
                wing[col[-1], x] = False
    top, bot = {}, {}
    for x in range(xa, xb + 1):
        col = np.nonzero(wing[:, x])[0]
        if len(col):
            top[x], bot[x] = col[0], col[-1]
    for x in top:
        n = bot[x] - top[x]
        glow = (x - xa) / (xb - xa)
        for y in range(top[x], bot[x] + 1):
            t = (y - top[x]) / max(1, n)
            c.g[y, x] = 'cv1' if y == bot[x] else ('cv3' if t < 0.25 else (('cv4' if glow > 0.3 else 'cv3') if t < 0.8 else 'cv2'))
    for r in ribs:                                                  # two-tone ribs: shadow left, lit right
        for y in range(top[r] + 1, bot[r] + 1):
            c.g[y, r] = 'cv1'
            if r + 1 in top and top[r + 1] < y < bot[r + 1]:
                c.g[y, r + 1] = 'cv4' if c.g[y, r + 1] != 'cv1' else 'cv1'
    for x in top:
        c.g[top[x] - 1, x] = 'gw0'; c.g[top[x], x] = 'gw2'
    c.rect(xa, top[xa] - 1, xa + 1, bot[xa] + 1, 'gw0')
    c.rect(xb, top[xb] - 1, xb + 1, bot[xb] + 1, 'gw0')
    c.line(106, bot[106] + 1, 105, 72, 'gw1'); c.line(116, bot[116] + 1, 118, 72, 'gw1')
    c.rect(102, 72, 121, 73, 'gw0'); c.rect(103, 71, 120, 72, 'gw2')
    c.line(86, 68, 107, 75, 'gw2'); c.line(86, 69, 107, 76, 'gw0')
    stamp(c, """
...k......
..kck.....
..kcck....
kkkcckkkk.
kccccccccK
.kkkkkkkk.
""", {'k': 'gw0', 'K': 'gw0', 'c': 'cv2'}, 77, 64)
    c.put(80, 67, 'cv3'); c.put(81, 68, 'cv3')
    return wing

PILOT = """
....kkkk......
...kcccgk.....
...kccccck....
...kkvvvk.....
....ksssd.....
....kssdd.....
...rkssk......
..kjjjjJJk....
.kjjjjjJJJk...
.kjjjtjJJJk...
.kjjjjtjJJk...
..kbbbbtbk....
..kbbkkbbk....
..kbk..kbk....
.kbk...kbk....
.kmk...kmmk...
kmmk...kmmk...
"""

def pilot(c, x, y):
    key = {'k': 'pj0', 'c': 'pj1', 'g': 'bk', 'v': 'pj0', 's': 'sk', 'd': 'skd', 'j': 'pj1', 'J': 'pj2',
           'b': 'pj1', 'r': 'sc1', 't': 'sa1', 'm': 'sa0'}
    stamp(c, PILOT, key, x, y)
    for i, (sx, sy) in enumerate([(x + 2, y + 6), (x, y + 6), (x - 2, y + 7), (x - 4, y + 6), (x - 6, y + 7)]):
        c.put(sx, sy, 'sc1'); c.put(sx - 1, sy, 'sc1'); c.put(sx, sy + 1, 'sc0' if i % 2 else 'sc1'); c.put(sx - 1, sy + 1, 'sc1')
    c.put(x - 8, y + 7, 'sc1'); c.put(x - 8, y + 9, 'sc0')
    c.line(x + 3, y + 7, x + 1, y + 1, 'pj1'); c.line(x + 10, y + 7, x + 12, y + 1, 'pj2')
    c.put(x + 1, y, 'sk'); c.put(x + 12, y, 'sk')
    for yy in range(y + 7, y + 11):
        col = [xx for xx in range(x, x + 14) if c.get(xx, yy) in ('pj1', 'pj2')]
        if col:
            c.put(max(col), yy, 'cv2')
    # the satchel with its brass buckle
    stamp(c, """
kkkkk
kaaak
kAbAk
kaaak
.kkk.
""", {'k': 'sa0', 'a': 'sa1', 'A': 'sa2', 'b': 'bk'}, x + 10, y + 9)

GULLS = [(70, 27, """
k........k
.kw....wk.
..kwggwk..
....kk....
"""), (152, 43, """
k......k
.kw..wk.
..kggk..
"""), (183, 63, """
k...k
.kgk.
""")]

def sprites():
    c = Canvas(W, H)
    glider(c)
    pilot(c, 103, 72)
    for x, y, g in GULLS:
        stamp(c, g, {'k': 'gu0', 'w': 'gu1', 'g': 'gu2'}, x, y)
    return c

def render():
    far, mid, near, spr = far_layer(), mid_layer(), near_layer(), sprites()
    return far, mid, near, spr, over(far, mid, near), over(far, mid, near, spr)

if __name__ == '__main__':
    far, mid, near, spr, bg, full = render()
    for name, L in (('panel-gba-bg-far', far), ('panel-gba-bg-mid', mid), ('panel-gba-bg-near', near)):
        image(L, PAL).save(OUT / ('%s.png' % name))
    save('panel-gba-bg', image(bg, PAL))
    save('panel-gba', image(full, PAL))
    import era
    boxes = [(76, 50, spr.g[50:92, 76:146] != None)] + [(x, y, spr.g[y:y + 5, x:x + 11] != None) for x, y, g in GULLS]
    print('sprites:', era.check_sprites(boxes, 'gba'))
