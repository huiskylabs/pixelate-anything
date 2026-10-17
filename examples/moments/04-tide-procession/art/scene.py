"""Tide Procession: the two stills, drawn from scratch in code (contre-jour, screen light).

    python3 art/scene.py a      -> out/04-a.png (1920x1080), out/04-a-pre.png (640x360 pixel layer),
                                   out/04-a-actor.png, out/04-a-intent.png, out/palette.json
    python3 art/scene.py b      -> the same for "The door opens"

Planes (post.Stack, far to near): sky (depth 4: strata, stars, clouds, moon) -> moon halo;
far (depth 3: headland, far sea, island and monastery) -> the shaft; middle (depth 2: causeway,
flats, pools, reflections, pilgrims) -> lantern pools and glows, the door spill (B); near (depth 0:
bank, boat, posts, bent pine), which takes no light.
"""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/04-tide-procession/art')
import json
import math
import pathlib
import numpy as np
from PIL import Image

import palette as P
import post
import shapes
import morph
import sky as skymod
from canvas import Canvas, to_image
import geom as G
import figures_tp as FG

ROOT = pathlib.Path('/home/user/pixelate-anything/examples/moments/04-tide-procession')
OUT = ROOT / 'out'
W, H = G.W, G.H
SCALE = 3


# ---------------------------------------------------------------- hashing
def hh(a, b=0, s=0):
    h = (int(a) * 374761393 + int(b) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


# ---------------------------------------------------------------- palette (OKLCh targets by role)
def _r(name, specs):
    return {'%s%d' % (name, i): P.from_lch(L, C, h) for i, (L, C, h) in enumerate(specs)}


PAL = {}
PAL.update(_r('sky', [(.170, .020, 248), (.188, .021, 246), (.206, .022, 244), (.224, .022, 242),
                      (.243, .021, 240), (.264, .020, 246), (.296, .018, 286)]))
PAL.update(_r('cl', [(.124, .015, 250), (.142, .016, 250), (.162, .017, 252)]))
PAL.update(_r('rim', [(.255, .020, 300), (.320, .024, 322), (.440, .020, 250), (.600, .014, 240)]))
PAL.update(_r('moon', [(.800, .020, 238), (.885, .014, 232), (.955, .008, 220)]))
PAL.update(_r('star', [(.380, .018, 240), (.520, .014, 236), (.720, .010, 232)]))
PAL.update(_r('head', [(.196, .018, 252), (.214, .018, 256)]))
PAL.update(_r('sea', [(.184, .022, 232), (.200, .022, 232), (.216, .022, 234), (.250, .022, 236),
                      (.285, .020, 236), (.380, .018, 236), (.500, .014, 234)]))
PAL.update(_r('mon', [(.126, .014, 242), (.152, .014, 242)]))
PAL.update(_r('mrim', [(.235, .018, 238), (.350, .018, 236)]))
PAL.update(_r('st', [(.116, .012, 240), (.146, .013, 240), (.178, .014, 238), (.218, .015, 236),
                     (.300, .016, 234), (.430, .014, 232)]))
PAL.update(_r('sand', [(.138, .012, 250), (.156, .012, 252), (.178, .013, 254)]))
PAL.update(_r('pool', [(.200, .020, 238), (.236, .021, 238), (.266, .020, 240), (.306, .018, 244)]))
PAL.update(_r('fig', [(.098, .012, 252), (.122, .012, 252)]))
PAL['figr'] = P.from_lch(.270, .018, 236)
PAL['figw'] = P.from_lch(.460, .085, 58)
PAL.update(_r('lamp', [(.420, .095, 48), (.620, .135, 58), (.780, .125, 70), (.885, .085, 82)]))
PAL.update(_r('door', [(.300, .070, 48), (.520, .110, 58), (.720, .120, 68), (.860, .085, 80)]))
PAL['halo0'] = P.from_lch(.560, .016, 236)
PAL['wisp0'] = P.from_lch(.318, .020, 300)
PAL['pool4'] = P.from_lch(.380, .016, 240)
PAL.update(_r('deep', [(.176, .020, 236), (.200, .020, 236)]))
PAL['leaf0'] = P.from_lch(.138, .012, 60)
PAL['sil0'] = P.from_lch(.112, .012, 246)

LIGHT = {'moon': '#c8d6e0', 'dome': '#3c4b5c', 'shaft': '#b9c9d6', 'lamp': '#ffb860',
         'door': '#ffc070'}


def rgba(c):
    """a Canvas -> RGBA uint8 array (None = clear)"""
    img = np.asarray(to_image(c.g, PAL, '#000000').convert('RGB'))
    a = np.where(np.equal(c.g, None), 0, 255).astype(np.uint8)
    return np.dstack([img, a])


# ---------------------------------------------------------------- the sky plane (depth 4)
STAR_CLUSTERS = [  # (cx, cy, radius, count) hand-placed, away from the moon and under the clouds
    (34, 14, 26, 6), (262, 8, 30, 7), (330, 76, 34, 9), (212, 96, 30, 7), (566, 64, 36, 9),
    (618, 118, 22, 5), (300, 150, 26, 5), (372, 112, 20, 4), (140, 160, 24, 4), (606, 168, 18, 3)]
STARS_BRIGHT = [(296, 74), (581, 61), (219, 101), (339, 9)]


def _bank(top, bot, seed):
    t = shapes.noisy_edge(top, amp=2.2, wavelength=20, seed=seed)
    b = shapes.noisy_edge(bot, amp=1.2, wavelength=14, seed=seed + 1)
    return G.mask_poly([tuple(p) for p in t] + [tuple(p) for p in b])


def cloud_masks(moment):
    """one long bank (two thirds of the width) with a ragged break above the moon, where the shaft
    comes through; two small filled wisps low over the horizon"""
    yy, xx = np.mgrid[0:H, 0:W]
    bank = _bank([(214, 44), (232, 33), (256, 26), (284, 29), (312, 25), (340, 28), (368, 32),
                  (396, 29), (424, 33), (450, 36), (478, 31), (506, 25), (536, 21), (566, 19), (598, 16),
                  (642, 14)],
                 [(642, 49), (612, 51), (584, 50), (556, 53), (528, 55), (500, 57), (476, 60), (452, 61),
                  (424, 61), (394, 62), (364, 61), (334, 60), (304, 62), (272, 60), (246, 58), (226, 53),
                  (214, 46)], 31)
    gx0, gy0, gx1, gy1 = G.GAP
    cx = (gx0 + gx1) / 2.0
    half = 2.5 + 9.5 * np.clip((yy - gy0) / float(gy1 - gy0), 0, 1) ** 1.3
    tear = np.abs(xx - cx - np.round(2 * np.sin(yy / 4.0))) <= half
    bank &= ~(tear & (yy >= gy0))
    wisps = np.zeros((H, W), bool)
    for x0, x1, y, th in ((112, 204, 171, 3), (232, 296, 184, 2), (520, 600, 178, 2)):
        for x in range(x0, x1):
            k = min(x - x0, x1 - 1 - x)
            t = 1 if k < 8 else th
            wisps[y - t + 1:y + 1, x] = True
    return bank, wisps


def draw_sky(moment):
    c = Canvas(W, H)
    bands = [('sky0', 0), ('sky1', 36), ('sky2', 72), ('sky3', 106), ('sky4', 138), ('sky5', 166),
             ('sky6', 192)]
    skymod.strata(c, bands, x0=0, x1=W, y0=0, y1=G.HORIZON + 1, amp=(3, 1.2), cells=(70, 19),
                  wisps=2, length=(30, 70), thick=(1, 2), echo=0.0, seed=11)
    intent = np.zeros((H, W), bool)
    mx, my, mr = G.MOON
    yy, xx = np.mgrid[0:H, 0:W]
    bank, wisps = cloud_masks(moment)
    # stars: hand-placed clusters, 3 tones, a handful bright, none on the clouds or by the moon
    for k, (cx, cy, r, n) in enumerate(STAR_CLUSTERS):
        for i in range(n):
            a = hh(k, i, 1) * 2 * math.pi
            d = r * math.sqrt(hh(k, i, 2))
            x, y = int(cx + d * math.cos(a)), int(cy + 0.6 * d * math.sin(a))
            if not (0 <= x < W and 0 <= y < G.HORIZON - 12) or math.hypot(x - mx, y - my) < 70:
                continue
            if bank[max(0, y - 2):y + 3, max(0, x - 2):x + 3].any():
                continue
            c.put(x, y, 'star0' if hh(k, i, 3) < 0.62 else 'star1')
            intent[y, x] = True
    for x, y in STARS_BRIGHT:
        c.put(x, y, 'star2')
        intent[y, x] = True
        if (x, y) == (296, 74):            # the one star big enough for a cross
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c.put(x + dx, y + dy, 'star0')
                intent[y + dy, x + dx] = True
    # the cloud bank: a filled mass one step darker than the sky, a paler belly, two thin inner
    # strata; a silver rim only on the moon-facing underside, brightest at the break, and the
    # break's own walls lit where the shaft comes through
    gx = (G.GAP[0] + G.GAP[2]) / 2.0
    c.g[bank] = 'cl0'
    for x in np.nonzero(bank.any(0))[0]:
        ys = np.nonzero(bank[:, x])[0]
        y0, y1 = ys.min(), ys.max()
        c.g[int(y0 + (y1 - y0) * 0.6):y1 + 1, x] = 'cl1'
        dx = abs(x - gx)
        if dx < 60:
            c.g[y1, x] = 'rim3'
            c.g[y1 - 1, x] = 'rim2'
        elif dx < 130:
            c.g[y1, x] = 'rim2'
        elif dx < 220 and x % 2 == 0:
            c.g[y1, x] = 'rim1'
    for y in range(G.GAP[1], G.GAP[3] + 1):
        row = bank[y]
        for x in range(G.GAP[0] - 12, G.GAP[2] + 12):
            if row[x] and (not row[x + 1] or not row[x - 1]):
                c.g[y, x] = 'rim3' if y > G.GAP[1] + 8 else 'rim2'
    for x0, x1, y in ((262, 340, 54), (286, 316, 55), (548, 600, 44), (560, 584, 45)):
        for x in range(x0, x1):
            if c.g[y, x] in ('cl0', 'cl1'):
                c.g[y, x] = 'cl2'
    c.g[wisps] = 'wisp0'
    # the moon: a flat disc, a one-slot ring that rounds it, one big irregular mare and a small one
    disc = G.disc(mx, my, mr)
    halo = G.disc(mx, my, mr + 2) & ~G.disc(mx, my, mr)       # a one-slot halo ring, 2 px even
    c.g[halo] = 'halo0'
    c.g[disc] = 'moon2'
    ring = disc & ~morph.erode(disc, 1, metric='cross')
    c.g[ring] = 'moon1'
    mare = G.mask_poly([(mx - 13, my - 6), (mx - 9, my - 11), (mx - 3, my - 12), (mx + 1, my - 8),
                        (mx - 1, my - 3), (mx + 3, my + 1), (mx - 2, my + 3), (mx - 8, my + 1),
                        (mx - 12, my - 1)])
    small = G.mask_poly([(mx - 9, my + 8), (mx - 4, my + 6), (mx + 1, my + 9), (mx - 5, my + 12)])
    c.g[(mare | small) & disc & ~ring] = 'moon1'
    for x, y in ((mx - 7, my - 6), (mx - 5, my - 9), (mx + 3, my + 13)):
        c.put(x, y, 'moon0')
    return c, intent, disc


# ---------------------------------------------------------------- the far plane (depth 3)
def ray_mask(sh):
    return shapes.ray((H, W), sh['x'], sh['y'], sh['angle'], sh['length'], sh['width'])


def draw_far(moment):
    c = Canvas(W, H)
    intent = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W]
    # the far sea, darker toward the viewer, in hard bands with stepped seams
    c.bands(G.HORIZON, H, [('sea2', G.HORIZON), ('sea1', 213, 0), ('sea0', 226, 0)], dither='none',
            edge='steps', amp=1, seed=5)
    # swell streaks: mismatched dashes, sparse near the horizon, longer nearer
    sh = G.SHAFT[moment]
    ray = ray_mask(sh)
    a = math.radians(sh['angle'])
    ex, ey = sh['x'] + math.cos(a) * sh['length'], sh['y'] + math.sin(a) * sh['length']
    foot = (((xx - ex) / 44.0) ** 2 + ((yy - G.HORIZON - 16) / 16.0) ** 2 <= 1) & (yy > G.HORIZON)
    y = G.HORIZON + 2
    k = 0
    while y < H:
        step = 2 if y < 222 else 3
        x = int(hh(y, 1, 7) * 30) - 20
        while x < W:
            ln = 2 + int(hh(x, y, 9) ** 1.6 * (8 if y < 220 else 16))
            gap = 6 + int(hh(x, y, 10) * (26 if y < 220 else 34))
            for i in range(ln):
                px = x + i
                if 0 <= px < W:
                    base = c.g[y, px]
                    up = {'sea2': 'sea3', 'sea1': 'sea2', 'sea0': 'sea1'}.get(base, base)
                    if ray[y, px] or foot[y, px]:
                        up = 'sea4' if not foot[y, px] else ('sea5' if (i + k) % 5 else 'sea6')
                        if up == 'sea6':
                            intent[y, px] = True
                    c.g[y, px] = up
            x += ln + gap
            k += 1
        y += step + (1 if hh(y, 3, 3) < 0.3 else 0)
    # the far headland on the horizon (hazed, two values, no rim)
    head = G.mask_poly([(108, 207), (122, 203), (146, 200), (168, 198), (186, 196), (200, 197),
                        (222, 195), (240, 197), (262, 199), (280, 202), (300, 205), (314, 207)])
    c.g[head] = 'head0'
    c.g[head & (yy <= 199)] = 'head1'
    # the island and the monastery
    isl = draw_island(c, moment)
    return c, intent, isl


def draw_island(c, moment):
    yy, xx = np.mgrid[0:H, 0:W]
    m = G.island_mask()
    t0, t1 = G.TOWER
    # string courses on the tower, eaves on the cap, chimneys, the cross
    for y in (114, 160):
        m[y, t0 - 1:t1 + 2] = True
    m[G.TOWER_TOP, t0 - 2:t1 + 3] = True
    m[134:141, 558:561] = True                      # chimney on the nave ridge
    m[173:181, 612:615] = True                      # dormitory chimney
    cx, cy = G.CAP_TIP
    m[cy - 6:cy, cx] = True                         # the cross
    m[cy - 4, cx - 1:cx + 2] = True
    # boulders at the waterline
    for x0, x1, y0 in ((404, 412, 235), (406, 410, 234), (598, 609, 235), (600, 606, 234)):
        m[y0:G.WATERLINE + 1, x0:x1] = True
    # belfry openings: arches cut through the tower (the moon and sky show behind)
    holes = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in G.BELFRY:
        holes[y0 + 1:y1 + 1, x0:x1 + 1] = True
        holes[y0, x0 + 1:x1] = True
    m &= ~holes
    bx = G.BELFRY[0][0]                             # the bell hanging in the left opening
    for y, x0, x1 in ((100, bx + 1, bx + 2), (101, bx + 1, bx + 2), (102, bx, bx + 3), (103, bx, bx + 3)):
        m[y, x0:x1 + 1] = True
    # the small bent tree on the east shoulder, leaning right with the wind
    tx, ty = G.ISLAND_TREE
    for i in range(16):
        m[ty - i, min(W - 1, tx - 4 + i // 4)] = True
    for x0, x1, y in ((628, 640, 195), (626, 640, 196), (630, 640, 197), (632, 638, 198),
                      (631, 639, 191), (629, 640, 192)):
        m[y, x0:x1] = True
    c.g[m] = 'mon0'
    # stair treads and the terrace floor one step lighter, so the flight reads at 1x
    for i, (sx, sy) in enumerate(G.STEPS):
        nxt = G.STEPS[i + 1][0] if i + 1 < len(G.STEPS) else 477
        for x in range(sx, nxt):
            if m[sy, x]:
                c.g[sy, x] = 'mon1'
    for x in range(477, 540):
        if m[G.TERRACE_Y, x]:
            c.g[G.TERRACE_Y, x] = 'mon1'
    door = portal_mask()
    if moment == 'a':
        x0, x1, ytop, yth = G.PORTAL
        c.g[door] = 'leaf0'
        c.g[yth - 1, x0 + 3:x1 - 2] = 'lamp0'      # a thread of light under the shut door
    # cold rims on the silhouette edges that face the moon
    mx, my, mr = G.MOON
    nx, ny = morph.normals(m, blur=1)
    d = np.hypot(mx - xx, my - yy) + 1e-6
    face = (nx * (mx - xx) + ny * (my - yy)) / d
    edge = morph.edges(m) & m
    rim = edge & (face > 0.3)
    near = rim & (d < 46)
    mid = rim & (d >= 46) & (d < 125)
    far = rim & (d >= 125) & (d < 180) & ((xx + yy) % 2 == 0)
    c.g[far] = 'mrim0'
    c.g[mid] = 'mrim0'
    c.g[near] = 'mrim1'
    return m


def portal_mask():
    x0, x1, ytop, yth = G.PORTAL
    m = np.zeros((H, W), bool)
    w = x1 - x0 + 1
    for y in range(ytop, yth):
        k = y - ytop
        inset = {0: 4, 1: 2, 2: 1, 3: 1}.get(k, 0) if w > 8 else 0
        m[y, x0 + inset:x1 + 1 - inset] = True
    return m


# ---------------------------------------------------------------- the middle plane (depth 2)
def front_line():
    """the row where the middle plane starts at each column (the road top, then the island foot)"""
    return np.array([G.road_y(x) if x <= 418 else G.WATERLINE for x in range(W)])


def water_masks(moment):
    """the shallow pools beside the causeway (lighter: they take the moon and the shaft) and the
    deeper channel between them and the near shore (darker)"""
    yy, xx = np.mgrid[0:H, 0:W]
    shallow = np.zeros((H, W), bool)
    for x in range(22, W):
        if x <= 418:
            y0 = G.road_y(x) + sum(G.road_th(x))
            y1 = y0 + 30 + int(round(3 * math.sin(x / 37.0) + 1.5 * math.sin(x / 11.0)))
        else:
            y0 = G.WATERLINE + 1
            y1 = 266 + int(round(2 * math.sin(x / 23.0)))
        if moment == 'b' and x < 236:
            y1 += 10                                   # the flood spreads behind the last pilgrim
        shallow[y0:y1, x] = True
    deep = (yy < H) & ~shallow
    return shallow, deep


def draw_middle(moment):
    c = Canvas(W, H)
    intent = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W]
    fl = front_line()
    region = yy >= fl[None, :]
    # the flats: wet sand with ripple marks as mismatched light dashes
    c.g[region] = 'sand1'
    for y in range(240, H):
        if hh(y, 4, 2) < 0.4:
            continue
        x = int(hh(y, 5, 2) * 40)
        while x < W:
            ln = 3 + int(hh(x, y, 13) * 9)
            for i in range(ln):
                if x + i < W and region[y, x + i]:
                    c.g[y, x + i] = 'sand2'
            x += ln + 10 + int(hh(x, y, 14) * 40)
    lag, deep = water_masks(moment)
    lag &= region
    deep &= region
    c.g[lag] = 'pool2'
    c.g[deep] = 'deep0'
    sh = G.SHAFT[moment]
    ang = math.radians(sh['angle'])
    fx_, fy_ = sh['x'] + math.cos(ang) * sh['length'], sh['y'] + math.sin(ang) * sh['length']
    lit = (((xx - fx_) / 40.0) ** 2 + ((yy - fy_ - 8) / 14.0) ** 2) <= 1
    # long ripple streaks, mismatched: lighter and darker in the shallows, sparse in the channel
    for y in range(240, H):
        x = int(hh(y, 6, 3) * 30)
        while x < W:
            ln = 3 + int(hh(x, y, 15) * 14)
            up = hh(x, y, 16) < 0.55
            for i in range(ln):
                X = x + i
                if X >= W:
                    break
                if lag[y, X]:
                    c.g[y, X] = ('pool4' if lit[y, X] else 'pool3') if up else 'pool1'
                elif deep[y, X] and hh(x, y, 18) < 0.45:
                    c.g[y, X] = 'deep1'
            x += ln + 8 + int(hh(x, y, 17) * 34)
    # where the shaft lands, the shallows take its light in more, longer streaks
    for y in range(int(fy_) - 2, int(fy_) + 24):
        for x in range(int(fx_) - 40, int(fx_) + 40):
            if 0 <= x < W and 0 <= y < H and lit[y, x] and lag[y, x] and hh(x // 5, y, 19) < 0.35:
                c.g[y, x] = 'pool4'
    # under the road the lagoon mirrors the causeway: two dark rows, broken
    for x in range(26, 419):
        y0 = G.road_y(x) + sum(G.road_th(x))
        for k in range(3):
            if lag[y0 + k, x] and (k < 2 or (x // 3) % 2):
                c.g[y0 + k, x] = 'pool0'
    # the island's reflection in the channel in front of it (dark streaks with ripple gaps)
    isl = G.island_mask()
    for k in range(1, 30):
        y = G.WATERLINE + 1 + k
        src = G.WATERLINE - k
        if k % 3 == 0:
            continue
        sh = int(round(math.sin(k * 1.7) * 1.2))
        row = np.roll(isl[src], sh)
        put = row & lag[y] & (xx[0] > 404)
        c.g[y, put] = 'pool0'
    road = draw_causeway(c, moment, intent)
    actor = np.zeros((H, W), bool)
    lamps = []
    for i, spec in enumerate(G.PILGRIMS[moment]):
        fx, h, kind, fr = spec[:4]
        fy = G.feet_y(fx, moment)
        fig = FG.pilgrim(h, kind, fr, seed=i, lead=(i == 0), tall=('tall' in spec))
        g, (ax, ay), (lx, ly) = fig['g'], fig['anchor'], fig['lamp']
        ox, oy = fx - ax, fy - ay
        for (y, x), v in np.ndenumerate(g):
            if v is None:
                continue
            X, Y = x + ox, y + oy
            if 0 <= X < W and 0 <= Y < H:
                c.g[Y, X] = v
                if str(v).startswith('lamp'):
                    intent[Y, X] = True
                else:
                    actor[Y, X] = True
        LX, LY = lx + ox, ly + oy
        lamps.append((LX, LY, i))
        if fx <= 418:
            reflect_pilgrim(c, g, ox, oy, lag, intent, LX, LY, i)
    return c, intent, actor, lamps, road


def draw_causeway(c, moment, intent):
    """the road of wet stones: a top surface of mismatched setts with wet rims, a coursed face"""
    road = np.zeros((H, W), bool)
    xs = range(G.CAUSEWAY[0][0], G.CAUSEWAY[-1][0] + 1)
    # stone boundaries along the road (3-8 px), two missing stones that hold water
    cuts, x = [], G.CAUSEWAY[0][0]
    k = 0
    while x < 420:
        cuts.append(x)
        x += 3 + int(hh(k, 2, 31) * 6)
        k += 1
    missing = {9, 38}
    flooded = moment == 'b'
    for i, x0 in enumerate(cuts[:-1]):
        x1 = cuts[i + 1]
        for x in range(x0, x1):
            y = G.road_y(x)
            top, face = G.road_th(x)
            for r in range(top + face):
                road[y + r, x] = True
            under = flooded and x < 190
            if i in missing and not under:
                c.g[y, x] = 'pool2'
                c.g[y + 1, x] = 'pool1'
                for r in range(2, top):
                    c.g[y + r, x] = 'st1'
            else:
                c.g[y, x] = 'st4' if x == x0 + 1 or (x == x0 + 2 and x1 - x0 > 5) else 'st3'
                for r in range(1, top):
                    c.g[y + r, x] = 'st2'
                if x == x0:
                    for r in range(0, top):
                        c.g[y + r, x] = 'st0' if r else 'st1'
            # the face: coursed blocks, a dark seam every 4-7 px, offset per course
            for r in range(top, top + face):
                course = r - top
                off = 3 if course % 2 else 0
                seam = ((x + off + int(hh(x // 6, course, 33) * 2)) % 6 == 0)
                c.g[y + r, x] = 'st0' if seam or r == top + face - 1 else ('st1' if course % 2 else 'st2')
            if under:
                for r in range(0, top):
                    c.g[y + r, x] = 'pool2' if (x + r) % 7 else 'pool3'
    # glints: bright wet points on the stones, most where the shaft lands
    sh = G.SHAFT[moment]
    ang = math.radians(sh['angle'])
    fx_ = sh['x'] + math.cos(ang) * sh['length']
    for x in xs:
        y = G.road_y(x)
        inpool = abs(x - fx_) < 30
        if c.g[y, x] in ('st3', 'st4') and inpool and hh(x, 8, 41) < 0.6:
            c.g[y, x] = 'st4' if c.g[y, x] == 'st3' else 'st5'
            if c.g[y, x] == 'st5':
                intent[y, x] = True
        elif c.g[y, x] == 'st4' and hh(x, 7, 41) < 0.12 and x > 250:
            c.g[y, x] = 'st5'
            intent[y, x] = True
    # weed tufts hanging off the seaward face
    for x in (58, 117, 176, 203, 288, 341, 397):
        y = G.road_y(x)
        top, face = G.road_th(x)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (2, 0)):
            yy_ = y + top + face + dy
            if c.g[yy_, x + dx] is not None:
                c.g[yy_, x + dx] = 'st0'
    return road


def reflect_pilgrim(c, g, ox, oy, lag, intent, LX, LY, i):
    """the figure mirrored dark in the road-front lagoon, the lantern as stepped warm dashes"""
    xr = min(max(LX, 22), 418)
    wl = G.road_y(xr) + sum(G.road_th(xr))
    for (y, xg), v in np.ndenumerate(g):
        if v is None or str(v).startswith('lamp'):
            continue
        Y = 2 * wl - (y + oy) - 1
        X = xg + ox + (1 if (Y // 2) % 3 == 0 else 0)
        if 0 <= X < W and 0 <= Y < H and lag[Y, X] and (Y - wl) % 3 != 2:
            c.g[Y, X] = 'pool0'
    cy = 2 * wl - LY - 1
    dashes = [(-4, 1, 'lamp1'), (-2, 3, 'lamp2'), (0, 2, 'lamp1'), (1, 4, 'lamp1'), (3, 3, 'lamp0'),
              (5, 2, 'lamp0'), (6, 3, 'lamp0'), (8, 1, 'lamp0')]
    for j, (d, ln, slot) in enumerate(dashes):
        Y = cy + d
        sh = int(round(math.sin(j * 2.1 + i) * 1.0))
        x0 = LX - ln // 2 + sh
        for x in range(x0, x0 + ln):
            if 0 <= x < W and 0 <= Y < H and lag[Y, x]:
                c.g[Y, x] = slot
                intent[Y, x] = True


# ---------------------------------------------------------------- the near plane (depth 0)
def draw_near(moment):
    c = Canvas(W, H)
    yy, xx = np.mgrid[0:H, 0:W]
    bank = G.mask_poly(G.BANK + [(640, 360), (0, 360)])
    # tussocks: blades leaning right with the wind, in clusters of mismatched height
    for k, (cx, n, hmax) in enumerate(((12, 5, 7), (66, 4, 5), (138, 7, 9), (214, 3, 4), (288, 6, 7),
                                       (352, 4, 5), (446, 6, 8), (470, 3, 4), (612, 5, 6))):
        for i in range(n):
            bx = cx + int((i - n / 2) * 2.3 + hh(k, i, 51) * 2)
            if not 0 <= bx < W:
                continue
            col = np.nonzero(bank[:, bx])[0]
            if not len(col):
                continue
            by = col.min()
            hgt = 2 + int(hh(k, i, 52) * hmax)
            for j in range(hgt):
                lean = (j * (1 if hh(k, i, 53) < 0.7 else 0)) // 3
                if 0 <= bx + lean < W:
                    bank[by - j, bx + lean] = True
    # a few stones poking up from the bank edge
    for x0, x1, y in ((96, 103, 321), (98, 101, 320), (374, 384, 339), (376, 382, 338), (532, 541, 320),
                      (534, 539, 319)):
        bank[y, x0:x1] = True
    c.g[bank] = 'sil0'
    draw_pine(c)
    draw_boat(c)
    draw_posts(c)
    return c


def _pad(m, x0, x1, cy, th, seed, lift=3):
    """a flat swept pine pad: a flat underside, a low dome on top, needle tufts on both edges, the
    leeward (right) tip lifted by the wind"""
    for x in range(x0, x1 + 1):
        u = (x - x0) / float(x1 - x0)
        dome = math.sin(math.pi * u) ** 0.55
        base = cy - int(round(lift * u))
        top = base - int(round(th * dome * (0.8 + 0.35 * hh(x // 4, seed, 71))))
        if hh(x, seed, 72) < 0.3:
            top -= 1 + (1 if hh(x, seed, 73) < 0.35 else 0)
        bot = base + int(round(2 * dome)) + (1 if hh(x // 2, seed, 74) < 0.25 else 0)
        if hh(x, seed, 75) < 0.12:
            bot += 2
        m[top:bot + 1, x] = True


def draw_pine(c):
    m = np.zeros((H, W), bool)
    trunk = [(24, 306, 10), (28, 290, 9), (36, 272, 8), (48, 254, 7), (62, 236, 7), (73, 216, 6),
             (80, 196, 6), (86, 176, 5), (94, 156, 5), (104, 136, 4), (116, 117, 4), (128, 99, 3),
             (140, 82, 3), (150, 66, 2)]
    for (x0, y0, w0), (x1, y1, w1) in zip(trunk, trunk[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            u = i / n
            x, y, w = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, w0 + (w1 - w0) * u
            m[int(y), int(round(x - w / 2)):int(round(x + w / 2))] = True
    # angular limbs to the pads, and the dead stub
    for pts, w in ((((102, 140), (90, 126), (78, 110)), 2), (((118, 116), (138, 106), (152, 96)), 2),
                   (((142, 80), (164, 66), (180, 52)), 2), (((128, 100), (112, 90)), 1),
                   (((150, 66), (156, 50), (160, 44)), 2),
                   (((74, 214), (60, 202), (52, 192)), 2), (((60, 202), (57, 192)), 1)):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for i in range(n + 1):
                u = i / n
                x, y = int(round(x0 + (x1 - x0) * u)), int(round(y0 + (y1 - y0) * u))
                m[y:y + w, x] = True
    pads = np.zeros((H, W), bool)
    _pad(pads, 96, 214, 46, 13, 1, lift=5)            # the crown pad, 118 px
    _pad(pads, 114, 190, 98, 9, 2, lift=3)            # 76 px
    _pad(pads, 50, 110, 114, 8, 3, lift=2)            # 60 px, on the windward side
    _pad(pads, 138, 168, 74, 5, 4, lift=2)            # 30 px
    for x0, y0, w, h in ((118, 40, 5, 2), (158, 41, 7, 2), (190, 36, 3, 2), (132, 94, 6, 2),
                         (166, 92, 3, 1), (74, 110, 4, 2), (148, 72, 3, 1)):
        pads[y0:y0 + h, x0:x0 + w] = False
    m |= pads
    c.g[m] = 'sil0'


def draw_boat(c):
    x0, y0, x1, y1 = G.BOAT
    m = np.zeros((H, W), bool)
    # hull: a curved sheer rising to a pointed stem (right), listing 3 px toward the stern
    for x in range(x0, x1 + 1):
        u = (x - x0) / (x1 - x0)
        sheer = y0 + 9 - 4 * u - 10 * max(0, u - 0.78) ** 1.6 * 9 + 3 * (1 - u) ** 2
        keel = y1 - 3 * math.sin(math.pi * min(1, u * 1.05)) - (6 * (u - 0.86) / 0.14 if u > 0.86 else 0)
        if keel > sheer:
            m[int(sheer):int(keel) + 1, x] = True
    m[y0 - 1:y0 + 6, x1 - 1:x1 + 1] = True           # the stem post
    m[y0 + 5:y0 + 16, x0:x0 + 2] = True               # the transom
    # an oar leaning on the hull to the sand
    for i in range(22):
        m[y0 + 2 + i // 2, x0 + 34 + i] = True
    m[y0 + 12:y0 + 15, x0 + 55:x0 + 58] = True        # its blade
    # a bailer by the stem
    m[y1 - 1:y1 + 2, x1 + 6:x1 + 10] = True
    m[y1 - 2, x1 + 6] = True
    # gap between the hull and the sand under the listing side
    m[y1 - 1:y1 + 1, x0 + 14:x0 + 24] = False
    c.g[m] = 'sil0'


def draw_posts(c):
    m = np.zeros((H, W), bool)
    for k, (px, top, w) in enumerate(G.POSTS):
        lean = (1 / 6.0) if k == 2 else (0.06 if k == 0 else 0)
        for y in range(top, 344):
            dx = int(round((y - top) * -lean)) if lean else 0
            m[y, px + dx:px + dx + w] = True
        # tops: a slant cut, a broken stub (k == 2, it has lost its top), a cap
        if k == 0:
            m[top, px + w - 1] = False
        if k == 2:
            m[top:top + 2, px + 2:px + w] = False
            m[top + 2, px + 3:px + w] = False
        if k == 3:
            m[top - 1, px:px + w] = True
    # the rope coil on the second post and the rope sagging from post 1 to post 3
    m[306:309, 521:527] = True
    m[305, 522:526] = True
    c.catenary(500, 296, 553, 292, 9, 'sil0')
    c.g[m] = 'sil0'


# ---------------------------------------------------------------- render
def render(moment):
    sky_c, i_sky, moon = draw_sky(moment)
    far_c, i_far, isl = draw_far(moment)
    mid_c, i_mid, actor, lamps, road = draw_middle(moment)
    near_c = draw_near(moment)
    near = ~np.equal(near_c.g, None)
    # the pre-light pixel layer
    pre = Canvas(W, H)
    for c in (sky_c, far_c, mid_c, near_c):
        pre.paste(c)
    pre_img = to_image(pre.g, PAL, '#000000')
    s = post.Stack(scale=SCALE, res='screen', background=PAL['sky0'])
    s.plane(rgba(sky_c), depth=4)
    mx, my, mr = G.MOON

    def sky_light(p):
        p.light(mx, my + 40, 230, LIGHT['dome'], strength=0.10, squash=0.5, falloff=1.4, behind=moon)
        p.light(mx, my, 44, LIGHT['moon'], strength=0.30, falloff=1.6, core=mr, behind=moon)
    s.light(sky_light, depth=4)
    s.plane(rgba(far_c), depth=3)
    sh = G.SHAFT[moment]

    s.plane(rgba(mid_c), depth=2)
    lampmask = mid_c.mask_of('lamp') & ~near
    figs = actor

    ang = math.radians(sh['angle'])
    fx_, fy_ = sh['x'] + math.cos(ang) * sh['length'], sh['y'] + math.sin(ang) * sh['length']

    def mid_light(p):
        p.shaft(sh['x'], sh['y'], angle=sh['angle'], length=sh['length'], width=sh['width'],
                colour=LIGHT['shaft'], strength=0.30, floor=0.55, tail=10, head=8,
                behind=isl | moon | figs | lampmask, striate=0.03, seed=3)
        p.light(fx_, fy_ + 6, 34, LIGHT['shaft'], strength=0.20, squash=0.32, falloff=1.4,
                behind=isl | figs | lampmask)
        for lx, ly, i in lamps:
            p.light(lx, ly + 5, 10, LIGHT['lamp'], strength=0.36 if i else 0.42, squash=0.55,
                    falloff=1.3, behind=figs | lampmask)
        p.glow(mask=lampmask, kernel='gauss', radius=(1.0, 2.5), weights=(0.6, 0.4), strength=0.26,
               tint=LIGHT['lamp'])
    s.light(mid_light, depth=2)
    s.plane(rgba(near_c), depth=0)
    p = s.render()
    img = p.image()
    intent = i_sky | i_far | i_mid
    intent &= ~near
    return img, pre_img, actor & ~near, intent, pre


def save(moment):
    OUT.mkdir(parents=True, exist_ok=True)
    img, pre_img, actor, intent, pre = render(moment)
    img.save(OUT / ('04-%s.png' % moment))
    pre_img.save(OUT / ('04-%s-pre.png' % moment))
    Image.fromarray((actor * 255).astype(np.uint8), 'L').save(OUT / ('04-%s-actor.png' % moment))
    Image.fromarray((intent * 255).astype(np.uint8), 'L').save(OUT / ('04-%s-intent.png' % moment))
    used = sorted(set(pre.g.ravel()) - {None})
    pj = OUT / 'palette.json'
    allp = json.loads(pj.read_text()) if pj.exists() else {}
    allp.update({k: PAL[k] for k in used})
    pj.write_text(json.dumps(dict(sorted(allp.items())), indent=1))
    print('wrote', OUT / ('04-%s.png' % moment), img.size, '%d slots' % len(used))


if __name__ == '__main__':
    for m in (sys.argv[1:] or ['a']):
        save(m)
