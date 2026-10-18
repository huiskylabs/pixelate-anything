"""Moment B, "Above the cloud sea": the gondola rises out of the cloud sea into thin air.

Night, 270x480 native, 4x nearest to 1080x1920. Below: three cloud masses of very different size
(long flat tops, a lit top tier, a deeper belly) with two kite-sailed skiffs; above: aurora curtains
and three kinds of hand-placed stars. The passenger's lantern is the only warm peak.
"""
import math
import numpy as np
from canvas import Canvas
from common import (W, H, YY, XX, hsh, hsh_arr, noise1, bayer, build, new_grid, put, stamp, nb4, shift,
                    line_pts, sag_line, save, crop_zoom)
import geometry as G
import gondola as GD

RAMPS = {
    'sky': [(.125, .040, 275), (.15, .046, 278), (.18, .050, 282), (.21, .052, 286), (.24, .052, 292)],
    'aur': [(.205, .034, 210), (.245, .042, 188), (.29, .052, 168), (.345, .062, 154)],
    'auv': [(.215, .045, 325), (.25, .050, 335)],
    'st': [(.33, .030, 262), (.50, .030, 252), (.66, .030, 242), (.82, .025, 95)],
    'cl': [(.205, .035, 292), (.265, .040, 284), (.31, .042, 276), (.35, .040, 262), (.375, .036, 240), (.395, .030, 225)],
    'wood': [(.15, .030, 285), (.21, .040, 305), (.28, .050, 330), (.35, .055, 355), (.42, .055, 20)],
    'rose': [(.30, .065, 8), (.37, .075, 16), (.44, .070, 26)],
    'sand': [(.36, .035, 70), (.44, .035, 78)],
    'cab': [(.165, .030, 290), (.195, .034, 300), (.23, .036, 320), (.27, .036, 350)],
    'coat': [(.19, .045, 250), (.26, .060, 240), (.34, .065, 228), (.42, .060, 214)],
    'scarf': [(.32, .090, 18), (.41, .100, 26), (.49, .090, 36)],
    'skin': [(.42, .060, 40), (.56, .070, 55), (.68, .075, 66)],
    'gw': [(.45, .095, 48), (.56, .120, 58), (.66, .135, 68), (.75, .130, 78)],
    'lamp': [(.63, .165, 55), (.77, .170, 70), (.87, .160, 85), (.96, .080, 100)],
    'iron': [(.17, .020, 270), (.25, .025, 265), (.34, .030, 260), (.43, .030, 250)],
}
PAL = build(RAMPS)


# ------------------------------------------------------------------ sky
def sky(g):
    c = Canvas(W, H)
    c.bands(0, H, [('sky0', 0), ('sky1', 64, 14), ('sky2', 138, 16), ('sky3', 222, 16), ('sky4', 300, 14)],
            edge='steps', amp=2, seed=8)
    g[:] = c.g


def aurora(g):
    """rippling curtains: a bright 1-2 px hem on an S-curve; rays whose height follows an envelope with
    two or three tall places (small per-ray variation, no comb of gaps); green steps to teal to night
    upward through a wide ordered dither; a narrow bright crease where the curtain folds; faint
    magenta only on the tips of the tallest rays"""
    def curtain(x0, x1, hem, env, top, seed, fold=None):
        for x in range(x0, x1):
            yh = hem(x)
            grp = (x + int(3 * noise1(x / 7, seed))) // 3
            Lx = env(x) * (0.72 + 0.38 * hsh(grp, seed))           # rays: groups of uneven height, no gaps
            Lx = int(Lx)
            seam = hsh(grp, seed + 5) < 0.3 and (x % 3 == 0)      # a darker seam between some rays
            for k in range(0, Lx + 6):
                y = yh - k
                if not 0 <= y < H:
                    continue
                u = k / max(1, Lx)
                th = (bayer(x, y) + 0.5) / 16
                lv = top - 0.4 - 3.6 * u + (th - 0.5) * 1.6        # a wide ordered dither between steps
                if k == 0:
                    lv = top
                if lv < -0.5:
                    if u > 0.92 and Lx > 40 and th < 0.3 and k <= Lx + 3:
                        put(g, x, y, 'auv1' if th < 0.12 else 'auv0')   # magenta on the tallest tips
                    continue
                lvl = max(0, min(top, int(round(lv))))
                if seam and k > 2 and lvl > 0:
                    lvl -= 1
                put(g, x, y, 'aur%d' % lvl)
            # the hem's lower lip: a darker row under it where the curtain hangs toward us
            if hsh(x // 5, seed + 1) < 0.55:
                put(g, x, yh + 1, 'aur%d' % max(0, top - 2))
        if fold:
            fx, fy0, fy1 = fold
            for y in range(fy0, fy1):
                put(g, fx, y, 'aur3' if y > fy0 + 3 else 'aur2')
                if y > fy0 + 8:
                    put(g, fx + 1, y, 'aur2')
    def bump(x, c, w):
        return math.exp(-((x - c) / w) ** 2)
    def hem1(x):
        u = (x - 6) / 252
        return int(round(78 + 26 * math.sin(math.pi * 1.6 * u + 0.3) + 10 * u + 3 * math.sin(x / 9)))
    def env1(x):
        return 12 + 46 * bump(x, 54, 26) + 38 * bump(x, 150, 20) + 30 * bump(x, 226, 22)
    curtain(6, 262, hem1, env1, 3, 11, fold=(150, hem1(150) - 30, hem1(150) + 1))
    def hem2(x):
        u = (x - 150) / 112
        return int(round(176 - 14 * math.sin(math.pi * 1.3 * u) + 2 * math.sin(x / 7)))
    def env2(x):
        return 8 + 22 * bump(x, 196, 16) + 14 * bump(x, 246, 12)
    curtain(150, 266, hem2, env2, 2, 12)


def stars(g, intent):
    """three kinds, hand-placed in clusters: dust (1 px, dim; a stream that thickens toward the top
    edge), points (1 px, a few 2 px), sparkles (5x5 four-point crosses, five only)"""
    sky_ok = lambda x, y: isinstance(g[y, x], str) and g[y, x].startswith('sky')
    # dust: a diagonal stream from the top-left corner region down to the right, denser near the top
    for i in range(900):
        x = int(hsh(i, 1) * W); y = int(hsh(i, 2) * 300)
        along = (x * 0.55 + y) / 300.0
        stream = abs((y - (20 + 0.62 * x)) / 38.0)
        p = 0.10 + 0.55 * math.exp(-stream * stream) + 0.9 * max(0, 1 - y / 60)
        if hsh(i, 3) < p * 0.5 and sky_ok(x, y) and not (108 <= x <= 170 and 196 <= y <= 272):
            g[y, x] = 'st0'; intent[y, x] = True
    # points: hand-placed list (x, y, size)
    pts = [(14, 22, 1), (31, 61, 2), (52, 14, 1), (66, 120, 1), (80, 41, 1), (97, 9, 2), (118, 58, 1), (127, 30, 1),
           (146, 12, 1), (171, 49, 1), (183, 26, 2), (203, 8, 1), (219, 63, 1), (241, 19, 1), (259, 47, 2),
           (24, 150, 1), (41, 181, 1), (11, 214, 2), (58, 236, 1), (79, 198, 1), (92, 262, 1), (35, 278, 1),
           (186, 205, 1), (201, 232, 2), (227, 209, 1), (247, 251, 1), (262, 196, 1), (214, 274, 1), (172, 262, 1),
           (240, 118, 1), (196, 131, 1), (102, 160, 1), (61, 92, 1), (153, 168, 1), (229, 156, 1), (17, 108, 1)]
    for (x, y, s) in pts:
        if sky_ok(x, y) or g[y, x] == 'st0':
            g[y, x] = 'st1'; intent[y, x] = True
            if s == 2 and sky_ok(x + 1, y):
                g[y, x + 1] = 'st0'; intent[y, x + 1] = True
    # sparkles: five crosses, none near the hero
    for (x, y, big) in ((44, 48, 1), (209, 34, 0), (76, 170, 0), (238, 228, 1), (27, 252, 0)):
        g[y, x] = 'st3'; intent[y, x] = True
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            g[y + dy, x + dx] = 'st2'; intent[y + dy, x + dx] = True
            if big:
                g[y + 2 * dy, x + 2 * dx] = 'st1'; intent[y + 2 * dy, x + 2 * dx] = True


# ------------------------------------------------------------------ cloud sea
import shapes as SH


def cloud_mass(g, x0, x1, top, lobes, seed, dim=0, body=11, ends=12, height=44):
    """one mass: a long flat top (walked in flat runs with 1 px steps) from x0 to x1 with rounded ends,
    a few lobes of very different radius rising from it; shaded by depth under each column's top: a
    1 px rim, a lit top tier, the mid body, then a belly that dissolves downward through a wide Bayer
    dither (cl3 -> cl2 -> cl1 -> cl0); the lobes' lower-right flank a step darker. No outline."""
    D = lambda k: 'cl%d' % max(0, min(5, k - dim))
    m = np.zeros((H, W), bool)
    y = top
    x = x0
    while x < x1:
        run = 9 + int(hsh(x, seed) * 16)
        for xx in range(x, min(x1, x + run)):
            e = min(xx - x0, x1 - 1 - xx)
            lift = 0 if e >= ends else int(round(ends - math.sqrt(max(0, ends * ends - (ends - e) ** 2))))
            if 0 <= xx < W:
                lb = 0 if e >= ends * 2 else int(round((ends * 2 - e) ** 1.5 / (ends * 0.9)))
                m[max(0, y + lift):max(0, min(H, top + height - lb)), xx] = True
        y = top + (1 if hsh(x, seed + 1) < 0.35 else 0) - (1 if hsh(x, seed + 2) < 0.2 else 0)
        x += run
    lob = np.zeros((H, W), bool)
    flank = np.zeros((H, W), bool)
    for (lx, lr, sq) in lobes:
        cy = top + lr * 0.35
        dx = XX + 0.5 - lx; dy = (YY + 0.5 - cy) / sq
        rr = np.sqrt(dx * dx + dy * dy)
        inside = rr <= lr
        lob |= inside
        flank |= inside & (rr > lr - 2.5) & (dx > lr * 0.25) & (dy > -lr * 0.5)
    m |= lob
    cols = np.where(m.any(0), m.argmax(0), H)
    depth = YY - cols[None, :]
    th = (BAY + 0.5) / 16
    tone = np.full((H, W), 3)
    tone[(depth >= 1) & (depth <= 2)] = 4
    tone[(depth == 3) & (th < 0.5)] = 4
    tone[depth <= 0] = 5
    tone[flank & (depth > 2)] = 2
    # the belly: below the flat top's body, dissolve downward step by step through wide dithers
    yb = top + body
    lv = 3 - (YY - yb) / 12.0 + (th - 0.5) * 1.3
    tone = np.where((YY > yb) & (depth > 3), np.minimum(tone, np.round(lv).astype(int)), tone)
    tone = np.clip(tone, 0, 5)
    # the last rows of the belly dissolve into whatever lies behind (a wide ordered dither, no edge)
    yb2 = top + height
    keep = th < np.clip((yb2 - YY) / 12.0, 0, 1)
    m &= keep | (depth <= 3)
    for k in range(6):
        g[m & (tone == k)] = D(k)
    return m


BAY = None


def strata(g, layers, seed, lobes=()):
    """the bank's lower layers filling the bottom: wide strata of deeper values, each with a lit
    upper edge, a hollow of shadow under its lip, lobes of very different radius with a crease where
    they sit on the layer, and a long Bayer seam into the next"""
    for i, (top, slot_rim, slot_body, slot_low) in enumerate(layers):
        # the hollow: the 2 rows just above this layer's top, in the layer behind, fall into shadow
        for x in range(W):
            lump = max(0.0, noise1(x / (31 + 9 * i), seed + 20 + i)) * (6 + 2 * i) + max(0.0, noise1(x / 70, seed + 30 + i)) * 5
            yt = top - int(round(lump)) + int(round(1.0 * noise1(x / 13, seed + 10 + i)))
            for d in (1, 2):
                v = g[yt - d, x] if 0 <= yt - d < H else None
                if isinstance(v, str) and v.startswith('cl') and (d == 1 or bayer(x, yt - d) < 8):
                    g[yt - d, x] = 'cl0'
        for x in range(W):
            lump = max(0.0, noise1(x / (31 + 9 * i), seed + 20 + i)) * (6 + 2 * i) + max(0.0, noise1(x / 70, seed + 30 + i)) * 5
            yt = top - int(round(lump)) + int(round(1.0 * noise1(x / 13, seed + 10 + i)))
            for y in range(max(0, yt), H):
                d = y - yt
                th = (bayer(x, y) + 0.5) / 16
                if d == 0:
                    v = slot_rim
                elif d <= 2 and th < 0.6:
                    v = slot_rim
                elif d < 10 + th * 4:
                    v = slot_body
                else:
                    v = slot_low if th < min(1.0, (d - 10) / 14.0) else slot_body
                put(g, x, y, v)
    for (lx, ly, lr, rim, body, crease) in lobes:
        dx = XX + 0.5 - lx; dy = (YY + 0.5 - ly) / 0.6
        rr = np.sqrt(dx * dx + dy * dy)
        inside = (rr <= lr) & (YY <= ly + 2)
        g[inside] = body
        g[inside & (rr > lr - 1.6) & (dy < 0)] = rim
        g[inside & (rr > lr - 3.2) & (rr <= lr - 1.6) & (dy < -lr * 0.3) & (dx < 0) & (BAY < 8)] = rim
        base = (YY == ly + 3) & (np.abs(dx) < lr - 1)
        g[base] = crease
        g[inside & (rr > lr - 1.5) & (dx > lr * 0.4) & (dy > -lr * 0.4)] = crease


def wisp(g, pts, th, slot_core, slot_edge):
    """a torn cloud shred along a polyline: thick in the middle, tapering, edge tone around the core"""
    n = len(pts) - 1
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        for (x, y) in line_pts(xa, ya, xb, yb):
            u = i / max(1, n)
            t_ = max(1, int(round(th * math.sin(math.pi * min(0.98, max(0.08, u + 0.5 / n))))))
            for d in range(-(t_ // 2) - 1, t_ - t_ // 2 + 1):
                v = slot_core if -(t_ // 2) <= d < t_ - t_ // 2 else slot_edge
                cur = g[y + d, x] if 0 <= y + d < H and 0 <= x < W else None
                if v == slot_edge and isinstance(cur, str) and cur == slot_core:
                    continue
                put(g, x, y + d, v)


def cloud_sea(g):
    global BAY
    BAY = np.vectorize(lambda x, y: bayer(x, y))(XX, YY)
    # the bank's lower layers first (they sit behind the masses' bellies)
    strata(g, [(366, 'cl3', 'cl2', 'cl1'), (388, 'cl4', 'cl2', 'cl1'), (410, 'cl4', 'cl3', 'cl2'),
               (434, 'cl5', 'cl3', 'cl2'), (458, 'cl5', 'cl3', 'cl2')], 41)
    # far small mass: about 15% of the width, high on the right, one step dimmer
    cloud_mass(g, 206, 248, 304, [(222, 6, 0.8)], seed=31, dim=1, body=7, ends=8, height=22)
    # mid mass: about 30%, right, one big lobe and one small
    cloud_mass(g, 172, 266, 322, [(200, 13, 0.85), (243, 5, 0.9)], seed=32, body=10, ends=11, height=40)
    # near huge mass: about 60%, left of centre; its biggest lobe rises under the gondola
    cloud_mass(g, -10, 164, 340, [(132, 22, 0.75), (70, 10, 0.9), (20, 5, 0.9)], seed=33, body=14, ends=14, height=58)
    # torn wisps off the big lobe, toward the gondola's floor and trailing right with the wind
    wisp(g, [(116, 304), (128, 300), (142, 298), (156, 298), (168, 300)], 3, 'cl3', 'cl2')
    wisp(g, [(146, 289), (156, 287), (167, 287), (176, 289)], 2, 'cl2', 'cl1')
    wisp(g, [(186, 316), (198, 312), (210, 313)], 2, 'cl4', 'cl3')


# ------------------------------------------------------------------ skiffs and kites
SKIFF = """
........................oo
.......................oLo
oo.....................olo
oLo...................olmo
olloooooooooooooooooooolmo
oLlllllLllllllllllllllllmo
.ommmmmmmmmmmmmmmmmmmmmmo.
..ommmdmmmmmmmmmmdmmmmmo..
...oddddddddddddddddddo...
....oooooooooooooooooo....
"""
SKIFF_FAR = """
..............oo
.............olo
oo...........olo
olooooooooooolmo
.ollllllllllllo.
..ommmmmmmmmmo..
...oooooooooo...
"""
KITE = """
......o......
.....oRo.....
....oRRro....
....oRRro....
...oRRRrro...
...oRRRrro...
..oRRRRrrro..
.ooooooooooo.
..orrrrssso..
...orrrsso...
...orrrsso...
....orsso....
....orsso....
.....oso.....
......o......
"""
KITE_FAR = """
....o....
...oRo...
...oRro..
..oRRrro.
.ooooooo.
..orrsso.
...orso..
...orso..
....oo...
"""


def skiffs(g):
    key = {'o': 'wood0', 'L': 'wood4', 'l': 'wood3', 'm': 'wood2', 'd': 'wood1'}
    kkey = {'o': 'wood0', 'R': 'rose2', 'r': 'rose1', 's': 'rose0'}
    kkey2 = {'o': 'wood0', 'R': 'sand1', 'r': 'sand0', 's': 'rose0'}
    def kite(art, k, kx, ky, spar_slot, notch=False):
        stamp(g, art, k, kx, ky)
        rows = [r.strip() for r in art.strip('\n').split('\n') if r.strip()]
        cx = len(rows[0]) // 2
        for j in range(1, len(rows) - 1):           # the vertical spar, a step lighter through the sail
            v = g[ky + j, kx + cx]
            if isinstance(v, str) and v.startswith(('rose', 'sand')):
                put(g, kx + cx, ky + j, spar_slot)
        if notch:                                    # the torn corner: a 3 px bite out of the upper right
            for (x, y) in ((kx + cx + 3, ky + 5), (kx + cx + 3, ky + 6), (kx + cx + 4, ky + 6)):
                put(g, x, y, 'sky3')
            put(g, kx + cx + 2, ky + 5, 'wood0'); put(g, kx + cx + 2, ky + 6, 'wood0')
        return kx + cx, ky + len(rows) - 1
    def line(a, b, sag):
        for (x, y) in sag_line(a[0], a[1], b[0], b[1], sag):
            v = g[y, x] if 0 <= y < H and 0 <= x < W else None
            if isinstance(v, str) and v.startswith(('sky', 'cl', 'st', 'aur')):
                put(g, x, y, 'cab2')
    def tail(x, y, n, dx):
        for i in range(n):
            px, py = x + i * dx // 3, y + 1 + i
            put(g, px, py, 'cab2')
            if i in (3, 7, 11):
                put(g, px - 1, py, 'rose1'); put(g, px + 1, py, 'rose1')
    def wake(x0, x1, y):
        for x in range(x0, x1):
            if hsh(x, 7) < 0.75:
                put(g, x, y, 'cl5')
            if hsh(x, 8) < 0.4:
                put(g, x - 2, y + 1, 'cl4')
    # near skiff: on the huge mass's flat top, lower left of the gondola, sailing right
    sx, sy = 66, 330
    stamp(g, SKIFF, key, sx, sy)
    for y in range(sy - 10, sy + 4):
        put(g, sx + 11, y, 'wood1')
    put(g, sx + 11, sy - 11, 'wood3')
    stamp(g, """
    .oo.
    oCCo
    oFCo
    oCCo
    """, {'o': 'coat0', 'C': 'coat2', 'F': 'skin0'}, sx + 3, sy)
    stamp(g, """
    .ll.
    lddl
    .ll.
    """, {'l': 'sand1', 'd': 'sand0'}, sx + 15, sy + 2)
    for x in range(sx, sx + 26):                      # the cloud lip over the waterline: sailing IN the tops
        put(g, x, sy + 9, 'cl4' if hsh(x, 9) < 0.7 else 'cl5')
        put(g, x, sy + 10, 'cl3')
    wake(sx - 14, sx + 1, sy + 9)
    kb = kite(KITE, kkey, 96, 276, 'sand1', notch=True)
    line((sx + 24, sy + 1), kb, 6)
    tail(kb[0], kb[1], 13, -5)
    # far skiff: smaller, on the mid mass's top at the right, a sand kite
    fx, fy = 214, 316
    stamp(g, SKIFF_FAR, key, fx, fy)
    for y in range(fy - 7, fy + 3):
        put(g, fx + 6, y, 'wood1')
    for x in range(fx, fx + 16):
        put(g, x, fy + 6, 'cl4' if hsh(x, 10) < 0.7 else 'cl5')
    wake(fx - 8, fx + 1, fy + 6)
    kb2 = kite(KITE_FAR, kkey2, 238, 282, 'sand1')
    line((fx + 14, fy + 1), kb2, 3)
    tail(kb2[0], kb2[1], 7, -3)


# ------------------------------------------------------------------ compose
def render():
    g = new_grid()
    intent = np.zeros((H, W), bool)
    sky(g)
    stars(g, intent)
    aurora(g)
    # the cable rises out of the clouds: drawn before the cloud sea so the clouds swallow it
    GD.draw_cable(g, 0, H)
    cloud_sea(g)
    skiffs(g)
    # the cable over the wisp right under the gondola (it passes through the shred)
    GD.draw_cable(g, 266, 286)
    GD.gondola(g)
    intent &= np.array([[isinstance(v, str) and v.startswith('st') for v in row] for row in g])
    return g, intent


if __name__ == '__main__':
    from PIL import Image
    g, intent = render()
    save(g, PAL, '02-b', scale=4)
    Image.fromarray((intent * 255).astype(np.uint8)).save(str(G.__file__).replace('art/geometry.py', 'out/02-b-intent.png'))
    crop_zoom('02-b', (90, 190, 190, 300), 5, 'hero')
    crop_zoom('02-b', (0, 250, 135, 400), 4, 'skiff')
    crop_zoom('02-b', (135, 250, 270, 400), 4, 'right')
    crop_zoom('02-b', (0, 0, 270, 200), 2, 'sky')
    print('ok', len(set(g.ravel()) - {None}), 'slots used')
