"""Market Day: the scene renderer (block-in and final share the layout).

    python3 scene.py blockin OUT.png      greyscale block-in at native size
"""
import sys, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from PIL import Image
from iso import Iso, hash2
import colorlib as cl
import mkit as kit
import town as L

W, H = L.W, L.H

# ---------------------------------------------------------------- block-in
BLOCK = {'B1': '#636363', 'B2': '#808080', 'B3': '#a4a4a4', 'B4': '#f5f5f5'}   # roofs .50, facades .60, paving .72, hero .97
ROOF_M = ('terra', 'brown', 'tile', 'slate')

def block_grey(slot):
    if slot is None:
        return 'B3'
    if slot in BLOCK:
        return slot
    base = slot.rstrip('0123456789')
    if base in ROOF_M:
        return 'B1'
    if slot.startswith('g') and base == 'g':
        return 'B3'
    return 'B2'

def house_mass(s, b):
    X, Y, w, d, h = b['X'], b['Y'], b['w'], b['d'], b['h']
    s.box(X, Y, 0, w, d, h, b['wall'])
    if b['gable']:
        kit.roof_y(s, X, Y, h, w, d, 1.5 * w, b['roof'] + '3', b['wall'] + '2')
    else:
        kit.roof_x(s, X, Y, h, w, d, 1.5 * d, b['roof'] + '2', b['roof'] + '1', hip=b['hip'])

def hall_mass(s):
    a = L.HALL
    s.box(a['X'], a['Y'], 0, a['w'], a['d'], a['h'], 'stone')
    kit.roof_y(s, a['X'], a['Y'], a['h'], a['w'], a['d'], a['roof'], 'tile3', 'tile2', hip=a['hip'])

def steps_mass(s, slot='B4'):
    st = L.STEPS
    x0, y0, y1 = st['x0'], st['y0'], st['y1']
    z = st['n'] * st['rise'] + st['rise']
    s.box(x0, y0, 0, st['landing'], y1 - y0, z, 'stone', top=slot, left=slot, right=slot)
    x = x0 + st['landing']
    for i in range(st['n']):
        z -= st['rise']
        s.box(x, y0, 0, st['tread'], y1 - y0, z, 'stone', top=slot, left=slot, right=slot)
        x += st['tread']

def blockin():
    s = Iso(W, H, origin=L.ORIGIN, slots=list(kit.SLOTS) + list(BLOCK))
    s.box(-400, -400, -2, 900, 900, 2, 'g', top='g6', lines=False, cast=False)
    for b in L.buildings():
        house_mass(s, b)
    hall_mass(s)
    steps_mass(s)
    # the wedding party: one bright mass standing on the steps (the hero)
    st = L.STEPS
    s.box(st['x0'] + 0.5, st['y0'] + 6, st['n'] * st['rise'] + st['rise'], 3.5, st['y1'] - st['y0'] - 12, 14, 'stone',
          top='B4', left='B4', right='B4')
    # stalls and crowd (mid masses) along the far side of the street and in the squares
    for x in range(4, 136, 13):
        if L.ALLEY_N[0] - 4 < x < L.ALLEY_N[1] + 2:
            continue
        s.box(x, 3, 0, 9, 6, 12, 'cream')
    for (cx, cy, r) in ((40, 18, 5), (72, 22, 6), (110, 20, 5), (-20, -50, 5), (-30, 8, 4), (170, 70, 7)):
        s.box(cx - r, cy - r, 0, 2 * r, 2 * r, 14, 'cream')
    g = s.render(outline=False, rim=False, between=False)
    slots = np.array(g.a, object)
    out = np.vectorize(block_grey)(slots)
    return out


# ---------------------------------------------------------------- the final frame
import mbld, mfig, mprops, json, math
GX0, GY0 = -420, -420

def ground(u, v, t, face_step=3, W=None, H=None):
    x, y = u + GX0, v + GY0
    st = L.STREET; sq = L.SQUARE
    if -49 <= x < -40 and -19.5 <= y < -12.5:                    # the runner spills onto the paving
        return 'rose2' if -18.9 <= y < -13.1 else 'rose1'
    if st[0] <= x < st[2] and st[1] <= y < st[3]:
        if 23 <= y < 24.6:
            return 'p1'                                           # the central gutter
        if y < 1.0:
            return 'p1'
        ix, iy = int(x // 1.6), int(y // 1.0)
        if hash2(ix, iy, 71) < 0.05 and (x % 1.6) < 1.1:
            return 'p1'
        return 'p2'
    if -48 <= x < -38 and -42 <= y < 10:                         # a granite apron frames the steps
        return 'p0' if ((x % 3.0) < 0.5 or (y % 3.0) < 0.5) else 'p1'
    if (sq[0] <= x < sq[2] and sq[1] <= y < sq[3]) or x >= st[2]:
        if (x % 9.0) < 0.5 or (y % 9.0) < 0.5:
            return 'p1'
        return 'p2'
    return 'p1'

def sbox(X, Y, z0, w, d, h):
    """screen bbox of a world box (x0, y0, x1, y1)"""
    pts = [L.ORIGIN[0] + 2 * (X + a - (Y + b)) for a in (0, w) for b in (0, d)]
    ys = [L.ORIGIN[1] + (X + a + Y + b) - z for a in (0, w) for b in (0, d) for z in (z0, z0 + h)]
    return (min(pts), min(ys), max(pts), max(ys))

def scr(x, y, z=0):
    return (L.ORIGIN[0] + 2 * (x - y), L.ORIGIN[1] + (x + y) - z)

def final():
    s = Iso(W, H, origin=L.ORIGIN, slots=kit.SLOTS)
    objs = []
    hero_ids = set()
    g_oid = s.box(GX0, GY0, -2, 900, 900, 2, 'g', top=ground, lines=False, cast=False)
    for b in L.buildings():
        mbld.house(s, b)
        hr = 1.5 * (b['w'] if b['gable'] else b['d'])
        objs.append({'kind': 'house', 'box': sbox(b['X'], b['Y'], 0, b['w'], b['d'], b['h'] + hr)})
    A = L.HALL
    steps = dict(L.STEPS, runner=(-19.5, -12.5))
    hero_ids |= set(mbld.hall(s, A, steps))
    objs.append({'kind': 'hall', 'box': sbox(A['X'], A['Y'], 0, A['w'], A['d'], A['h'] + A['roof'])})

    def put(g, x, y, z=0, hero=False, kind='person'):
        oid = s.sprite(g, x, y, z, upright=True)
        if hero:
            hero_ids.add(oid)
        sx, sy = scr(x, y, z)
        objs.append({'kind': kind, 'box': (sx - g.w / 2, sy - g.h, sx + g.w / 2, sy)})
        return oid

    # ---- stalls: far row and two in the middle of the street
    STALLS = [(2, 2, 'bread'), (13.5, 2, 'fruit'), (25, 2, 'flower'), (37.5, 2, 'fish'), (61, 2, 'fruit'),
              (72, 2, 'bread'), (84.5, 2, 'flower'), (97, 2, 'fish'), (109, 2, 'fruit'), (31, 19, 'flower'), (80, 19.5, 'bread')]
    for i, (x, y, kind) in enumerate(STALLS):
        mbld.stall(s, x, y, kind, seed=i)
        objs.append({'kind': 'stall', 'box': sbox(x, y, 0, 9, 5, 19)})
    # crates and baskets by the fruit and flower stalls
    for (x, y, goods) in ((22.6, 7.5, ['fruit2', 'fruit1']), (70.2, 7.6, ['leaf2', 'leaf1']), (118.4, 4, ['bread2', 'fruit2']),
                          (34.5, 7.4, ['flower2', 'bread2']), (93.8, 3.5, ['flower3', 'leaf2'])):
        mprops.crate(s, x, y, goods, seed=int(x))

    # ---- the hero: the wedding on the white hall steps (landing z 6, treads z 4 and 2)
    zl = steps['n'] * steps['rise'] + steps['rise']
    put(mfig.wedding('groom', 5, 'se'), -57.6, -17.6, zl, hero=True)
    put(mfig.wedding('bride', 6, 'sw'), -57.2, -13.6, zl, hero=True)
    put(mfig.wedding('maid', 7, 'sw', h='hb'), -53.6, -23.5, 4, hero=True)
    put(mfig.wedding('maid', 8, 'se', h='hy'), -53.4, -7.2, 4, hero=True)
    put(mfig.wedding('thrower', 9, 'sw'), -50.5, -29.5, 2, hero=True)
    put(mfig.wedding('thrower', 10, 'se'), -50.4, -1.5, 2, hero=True)
    put(mfig.person(11, 'up', 'sw', t='sky2', p='g1'), -57.2, -31.5, zl, hero=True)
    put(mfig.person(12, 'both', 'se', t='cream2'), -57.0, 1.0, zl, hero=True)
    put(mfig.person(13, 'up', 'sw', t='mint2'), -46.2, -34.2, 0, hero=True)
    put(mfig.kid(14, 'reach', 'se', t='white'), -45.2, -12.0, 0, hero=True)          # the flower girl
    put(mfig.person(15, 'back', 'se', t='slate2'), -40.5, -8.5, 0)                    # a guest watching from the square
    put(mfig.person(16, 'stand', 'sw', t='pink2'), -41.5, -27.5, 0)
    put(mfig.person(17, 'skirt', 'se', t='ochre2'), -39.0, -24.0, 0)
    for (y, z) in ((-21.6, zl), (-10.4, zl)):
        put(mprops.pot(), -59.0, y, z, hero=True, kind='pot')

    # ---- Place Gutenberg: fountain, kids and pigeons, the juggler and ring
    mprops.fountain(s, -30, -64)
    objs.append({'kind': 'fountain', 'box': sbox(-35, -69, 0, 10, 10, 16)})
    put(mfig.kid(20, 'run', 'se'), -24.5, -45.5)
    put(mfig.kid(21, 'run', 'sw'), -19.0, -40.5)
    put(mfig.kid(22, 'stand', 'se', t='fruit2'), -26.5, -38.0)
    for i, (x, y) in enumerate(((-12.5, -46.0), (-10.0, -43.5), (-14.0, -41.5), (-8.5, -47.5), (-31, -40.5), (-6.5, -40))):
        put(mfig.pigeon('sit', 'se' if i % 2 else 'sw'), x, y, kind='pigeon')
    for i, (x, y, z, k) in enumerate(((-12, -45, 9, 'up'), (-9.5, -44, 14, 'down'), (-14.5, -43, 18, 'glide'), (-7, -46, 22, 'up'),
                                        (-11, -48, 27, 'down'), (-5.5, -42.5, 12, 'glide'), (-13, -49, 32, 'up'), (-8, -45, 31, 'glide'))):
        put(mfig.pigeon(k, 'se' if i % 3 else 'sw', 'g4' if i % 2 else 'g3'), x, y, z, kind='pigeon')
    jx, jy = -14.0, 19.0
    put(mfig.story('juggler', 23, 'se'), jx, jy)
    ring = [(-19.5, 18.5, 'se', 'stand'), (-18.0, 23.5, 'se', 'skirt'), (-13.0, 24.6, 'sw', 'up'), (-8.6, 22.0, 'sw', 'stand'),
            (-8.8, 14.6, 'sw', 'back'), (-17.6, 13.6, 'se', 'back')]
    for i, (x, y, f, pose) in enumerate(ring):
        put(mfig.person(30 + i, pose, f), x, y)
    put(mfig.kid(37, 'stand', 'sw'), -11.0, 25.5)
    # strollers in the square: a couple, an old man, a woman with a basket
    put(mfig.person(40, 'walk', 'sw'), -32.0, -6.0)
    put(mfig.person(41, 'walk', 'sw', t='terra2'), -30.5, -3.5)
    put(mfig.person(42, 'stride', 'se', h='g5'), -36.0, 30.0)
    put(mfig.person(43, 'walk', 'se'), -22.0, -76.0)
    put(mfig.person(44, 'stand', 'sw'), -40.0, -60.0)
    put(mfig.person(45, 'skirt', 'se'), -44.0, -56.5)
    put(mfig.person(46, 'walk', 'sw'), -4.0, -28.0)
    mprops_lamp = mprops.lamp()
    for (x, y) in ((-2.5, -20.0), (-58.5, 42.0), (126.0, 46.0)):
        put(mprops_lamp, x, y, kind='lamp')
    put(mprops.tree(3), -6.0, -80.0, kind='tree')

    # ---- the street: the band snaking through the stalls, shoppers, the melon, the dog and the fish
    band = [('drum', 22.0, 13.5), ('cymbal', 27.5, 15.8), ('trumpet', 34.0, 15.4), ('trumpet', 40.5, 17.0),
            ('trombone', 45.5, 21.0), ('tuba', 49.5, 26.5)]
    for i, (n, x, y) in enumerate(band):
        put(mfig.band(n, 50 + i, 'sw'), x, y)
    shoppers = [(6.0, 10.5, 'back', 'se'), (8.5, 11.0, 'stand', 'sw'), (17.0, 10.0, 'back', 'sw'), (19.5, 11.5, 'skirt', 'se'),
                (29.0, 10.2, 'back', 'se'), (42.0, 9.8, 'back', 'sw'), (44.5, 10.6, 'stand', 'se'),
                (64.0, 10.0, 'back', 'se'), (77.0, 10.4, 'back', 'sw'), (79.5, 9.6, 'skirt', 'se'), (88.0, 10.0, 'back', 'se'),
                (90.5, 11.0, 'walk', 'sw'), (113.0, 10.0, 'back', 'sw'), (115.5, 11.0, 'stand', 'se'),
                (58.0, 18.0, 'walk', 'se'), (61.0, 21.5, 'walk', 'sw'), (66.5, 27.0, 'stride', 'se'), (93.0, 24.0, 'walk', 'sw'),
                (100.5, 29.0, 'stand', 'se'), (103.0, 28.5, 'skirt', 'sw'), (12.0, 22.0, 'walk', 'se'), (8.0, 28.0, 'stride', 'sw'),
                (73.5, 25.0, 'walk', 'se'), (36.0, 27.0, 'stand', 'sw'), (55.0, 30.0, 'walk', 'sw')]
    for i, (x, y, pose, f) in enumerate(shoppers):
        put(mfig.person(60 + i, pose, f), x, y)
    put(mfig.story('melon', 90, 'se'), 70.0, 9.0)                    # the vendor holds the melon up
    put(mfig.person(91, 'out', 'sw', t='sky1'), 74.2, 10.6)          # the customer haggles
    put(mfig.story('fishmonger', 92, 'se'), 105.8, 8.6)
    put(mfig.dog('se'), 110.5, 13.0, kind='dog')
    put(mfig.person(93, 'up', 'sw'), 108.0, 15.5)                     # a passer-by points at the thief
    put(mprops.bike(), 116.5, 26.0, kind='bike')                       # the cyclist with the bread crate

    # ---- the cathedral square: cafe terraces on the end houses, the flower cart, strollers
    cafes = [(129.5, 55.0, 'terra'), (134.0, 63.5, 'plaster'), (128.0, 78.0, 'plaster'), (132.5, 86.0, 'brown'),
             (127.0, 101.0, 'terra'), (131.0, 110.0, 'plaster'), (126.0, 125.0, 'plaster'), (130.5, 133.0, 'brown')]
    for i, (x, y, paint) in enumerate(cafes):
        put(mprops.cafe_table(), x, y, kind='table')
        put(mfig.story('sitter', 100 + i, 'se'), x - 1.6, y + 1.2)
        if i % 3 != 1:
            put(mfig.story('sitter', 120 + i, 'sw'), x + 1.8, y - 1.0)
        put(mprops.parasol(paint), x + 0.2, y - 0.2, kind='parasol')
    put(mfig.story('waiter', 130, 'sw'), 136.5, 72.0)
    put(mprops.flower_cart(), 140.0, 28.0, kind='cart')
    put(mfig.person(131, 'stand', 'se', t='leaf2'), 137.0, 30.5)
    for i, (x, y, pose, f) in enumerate(((150, 20, 'walk', 'sw'), (153, 23, 'walk', 'sw'), (162, 48, 'stride', 'se'),
                                          (146, 92, 'stand', 'sw'), (149, 95, 'skirt', 'se'), (170, 86, 'walk', 'se'),
                                          (158, 120, 'walk', 'sw'), (178, 60, 'back', 'se'), (144, 40, 'walk', 'se'),
                                          (190, 40, 'stand', 'sw'), (193, 43, 'stand', 'se'))):
        put(mfig.person(140 + i, pose, f), x, y)
    for i, (x, y) in enumerate(((166, 70), (168, 73), (171, 69), (156, 105))):
        put(mfig.pigeon('sit', 'se' if i % 2 else 'sw'), x, y, kind='pigeon')
    put(mprops.tree(7), 176.0, 104.0, kind='tree')
    put(mprops.tree(11, 20, 15), 196.0, 18.0, kind='tree')
    put(mprops.tree(5, 22, 16), 214.0, 86.0, kind='tree')
    put(mprops.tree(9, 20, 15), 160.0, 150.0, kind='tree')
    # a tour group round its guide, a family, strollers, pigeons, more cafe tables
    gx, gy = 168.0, 62.0
    put(mfig.person(200, 'up', 'sw', t='bread2'), gx, gy)
    for i, (dx, dy, f, pose) in enumerate(((-4.5, 1.0, 'se', 'back'), (-3.0, 4.5, 'se', 'stand'), (1.5, 5.0, 'sw', 'skirt'),
                                             (4.8, 2.0, 'sw', 'stand'), (4.0, -3.0, 'sw', 'back'), (-1.0, -4.6, 'se', 'back'),
                                             (-4.6, -2.5, 'se', 'stand'))):
        put(mfig.person(201 + i, pose, f), gx + dx, gy + dy)
    put(mfig.person(210, 'walk', 'se', t='leaf2'), 186.0, 96.0)
    put(mfig.kid(211, 'run', 'se'), 189.0, 98.5)
    put(mfig.kid(212, 'stand', 'se'), 184.5, 99.5)
    for i, (x, y, pose, f) in enumerate(((140, 104, 'walk', 'sw'), (150, 132, 'walk', 'se'), (166, 140, 'stride', 'sw'),
                                          (186, 122, 'walk', 'se'), (200, 70, 'walk', 'sw'), (206, 102, 'stand', 'se'),
                                          (209, 104, 'skirt', 'sw'), (214, 58, 'walk', 'se'), (176, 30, 'walk', 'sw'),
                                          (204, 36, 'back', 'se'), (222, 112, 'walk', 'sw'), (196, 140, 'stand', 'se'))):
        put(mfig.person(220 + i, pose, f), x, y)
    for i, (x, y) in enumerate(((192, 80), (194, 83), (190, 84), (198, 116), (201, 118), (180, 136))):
        put(mfig.pigeon('sit', 'se' if i % 2 else 'sw', 'g4' if i % 3 else 'g3'), x, y, kind='pigeon')
    # the north end of the cathedral square, by the right edge: a street sweeper, two friends, a couple, pigeons
    for i, (x, y, pose, f) in enumerate(((158, 30, 'stand', 'se'), (160.5, 32.5, 'up', 'sw'), (172, 14, 'walk', 'sw'),
                                          (174.5, 16.5, 'walk', 'sw'), (186, 50, 'back', 'se'), (152, 46, 'stride', 'se'),
                                          (166, 4, 'walk', 'se'), (182, 26, 'skirt', 'sw'))):
        put(mfig.person(260 + i, pose, f), x, y)
    for i, (x, y) in enumerate(((168, 38), (170, 40), (165, 41), (178, 34))):
        put(mfig.pigeon('sit', 'se' if i % 2 else 'sw', 'g4'), x, y, kind='pigeon')
    put(mprops.tree(13, 22, 16), 192.0, 60.0, kind='tree')
    for i, (x, y, pose, f) in enumerate(((190, 100, 'stand', 'se'), (192.5, 102.5, 'skirt', 'sw'), (188, 104, 'back', 'se'),
                                          (204, 92, 'walk', 'sw'), (200, 112, 'stride', 'se'))):
        put(mfig.person(280 + i, pose, f), x, y)
    put(mfig.kid(290, 'run', 'se'), 196.5, 108.0)
    for i, (x, y) in enumerate(((199, 105), (201.5, 106.5), (197, 103.5))):
        put(mfig.pigeon('up' if i == 1 else 'sit', 'sw', 'g3'), x, y, 5 if i == 1 else 0, kind='pigeon')
    put(mprops.lamp(), 178.0, 92.0, kind='lamp')
    # a fruit barrow of crates at the square's north end (crates and baskets of fruit)
    for i, (x, y, z, goods) in enumerate(((147.0, 36.0, 0, ['fruit2', 'fruit1']), (149.2, 36.0, 0, ['leaf2', 'bread2']),
                                           (151.4, 36.3, 0, ['fruit2', 'leaf2']), (148.0, 38.4, 0, ['bread2', 'fruit1']),
                                           (150.5, 38.6, 0, ['leaf1', 'leaf2']), (148.2, 36.2, 2, ['fruit2', 'bread2']))):
        mprops.crate(s, x, y, goods, seed=300 + i, z=z)
        objs.append({'kind': 'crate', 'box': sbox(x, y, z, 2, 2, 2)})
    put(mfig.story('melon', 301, 'sw', T='plaster2'), 154.0, 39.5)
    put(mfig.person(302, 'out', 'se'), 145.0, 41.5)
    for (x, y) in ((150.0, 62.0), (186.0, 132.0), (208.0, 40.0)):
        put(mprops.lamp(), x, y, kind='lamp')
    for i, (x, y, paint) in enumerate(((127.5, 148.0, 'terra'), (131.5, 156.0, 'plaster'), (125.0, 170.0, 'brown'))):
        put(mprops.cafe_table(), x, y, kind='table')
        put(mfig.story('sitter', 240 + i, 'se'), x - 1.6, y + 1.2)
        put(mfig.story('sitter', 250 + i, 'sw'), x + 1.8, y - 1.0)
        put(mprops.parasol(paint), x + 0.2, y - 0.2, kind='parasol')

    # ---- the kite snagged on a hall dormer, near the ridge
    put(mprops.kite(), -73.0, -44.0, 81.0, kind='kite')

    g = s.render(outline=True, rim=False, between=False, silhouette=True)
    slots = np.array(g.a, object)
    slots = np.where(slots == None, 'p2', slots)
    intent = np.zeros((H, W), bool)
    # the kite's tail: bows drifting right on a sagging string
    kx, ky = scr(-73.0, -44.0, 81.0)
    kx, ky = int(round(kx)), int(round(ky))
    pts = [(kx + 1 + i, ky + 1 + int(round(0.06 * i * i))) for i in range(0, 15)]
    for i, (x, y) in enumerate(pts):
        if 0 <= x < W and 0 <= y < H:
            slots[y, x] = 'g1'
            if i in (4, 8, 12):
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    slots[y + dy, x + dx] = 'fish2' if i != 8 else 'bread2'
                slots[y, x] = 'ol'
    # petals: a fan of rose and white flecks over the couple, drifting right
    cx, cy = scr(-57.4, -15.6, zl + 14)
    for i in range(64):
        a = hash2(i, 1, 99) * math.pi
        r = 4 + hash2(i, 2, 99) * 30
        x = int(round(cx + math.cos(a) * r * 1.3 + 6 * hash2(i, 5, 99)))
        y = int(round(cy - math.sin(a) * r * 0.55 + 6))
        c = 'rose3' if hash2(i, 3, 99) < 0.55 else 'white'
        if 0 <= x < W - 1 and 0 <= y < H and s.obj[y, x] not in hero_ids:
            slots[y, x] = c
            intent[y, x] = True
            if hash2(i, 4, 99) < 0.4:
                slots[y, x + 1] = c
                intent[y, x + 1] = True
    actor = np.isin(s.obj, list(hero_ids)) | intent & (np.abs(np.arange(W)[None, :] - cx) < 60)
    road = (s.obj == g_oid) & np.isin(slots, ['p1', 'p2'])
    return slots, objs, actor, intent, road

def export(outdir):
    import pathlib, time
    import compose
    t0 = time.time()
    slots, objs, actor, intent, road = final()
    out = pathlib.Path(outdir)
    rgb = to_rgb(slots, kit.PAL)
    im = Image.fromarray(rgb)
    im.save(out / '08-a@1x.png')
    im.resize((W * 2, H * 2), Image.NEAREST).save(out / '08-a@2x.png')
    im.resize((W * 4, H * 4), Image.NEAREST).save(out / '08-a.png')
    Image.fromarray((actor * 255).astype(np.uint8)).save(out / '08-a-actor.png')
    Image.fromarray((intent * 255).astype(np.uint8)).save(out / '08-a-intent.png')
    used = sorted(set(slots.ravel()))
    json.dump({k: kit.PAL[k] for k in used}, open(pathlib.Path(__file__).parent / 'palette.json', 'w'), indent=1)
    ys, xs = np.nonzero(actor)
    print('actor bbox', xs.min(), ys.min(), xs.max(), ys.max(), 'colours', len(used), 'time %.1f' % (time.time() - t0))
    fails = compose.check_density(objs, (0, 0, W, H), road=road)
    ii = np.pad(road.astype(float).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    worst = max(((ii[y + 120, x + 120] - ii[y, x + 120] - ii[y + 120, x] + ii[y, x]) / 14400.0, x, y)
                for y in range(0, 481, 20) for x in range(0, 481, 20))
    print('worst road window %.0f%% at x %d y %d' % (100 * worst[0], worst[1], worst[2]))
    print('check_density:', 'PASS' if not fails else fails, '| objects', len(objs), '| bare paving %.1f%%' % (100 * road.mean()))
    # image B: a 150 x 150 native crop around the wedding at 8x
    bx0, by0 = int(sys.argv[3]) if len(sys.argv) > 3 else 128, int(sys.argv[4]) if len(sys.argv) > 4 else 128
    crop = im.crop((bx0, by0, bx0 + 150, by0 + 150))
    crop.resize((1200, 1200), Image.NEAREST).save(out / '08-b.png')
    return slots

def to_rgb(slots, pal):
    keys = sorted(set(slots.ravel()))
    lut = {k: cl.hex_to_rgb(pal[k]) for k in keys}
    idx = {k: i for i, k in enumerate(keys)}
    arr = np.array([lut[k] for k in keys], np.uint8)
    return arr[np.vectorize(idx.get)(slots)]

if __name__ == '__main__':
    mode = sys.argv[1]
    out = sys.argv[2]
    if mode == 'final':
        export(out)
    if mode == 'blockin':
        sl = blockin()
        rgb = to_rgb(sl, BLOCK)
        Image.fromarray(rgb).save(out)
        Image.fromarray(rgb).resize((W * 2, H * 2), Image.NEAREST).save(out.replace('.png', '@2x.png'))
        print('wrote', out)
