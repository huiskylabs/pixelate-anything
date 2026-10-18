"""Moment A, "The trunk town": the gondola passes the clock face of a town carved into a colossal trunk.

Dusk-blue, 270x480 native, 4x nearest to 1080x1920. Light: cool skylight from the upper left; the
passenger's lantern is the one warm peak. Everything is a slot on the integer grid.
"""
import sys, math
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/02-endless-ascent/art')
import numpy as np
from canvas import Canvas
from common import (W, H, YY, XX, hsh, hsh_arr, noise1, bayer, build, new_grid, put, stamp, art_mask,
                    nb4, shift, sag_line, line_pts, save, crop_zoom)
import geometry as G
import gondola as GD

# ------------------------------------------------------------------ palette (OKLCh, darkest first)
RAMPS = {
    'haze': [(.30, .050, 268), (.335, .052, 272), (.365, .052, 280), (.395, .050, 290), (.42, .048, 300)],
    'ftr': [(.32, .036, 285), (.36, .038, 292), (.405, .036, 302)],
    'fleaf': [(.31, .040, 240), (.355, .044, 228), (.40, .042, 214)],
    'bark': [(.15, .035, 285), (.205, .040, 292), (.26, .045, 302), (.315, .046, 316), (.37, .045, 332), (.44, .042, 352)],
    'hw': [(.25, .045, 332), (.30, .055, 346), (.355, .058, 4), (.405, .060, 22), (.45, .056, 42)],
    'wood': [(.17, .035, 300), (.23, .045, 325), (.295, .055, 350), (.365, .060, 15), (.44, .060, 40)],
    'win': [(.31, .045, 40), (.365, .060, 52), (.41, .072, 62), (.445, .072, 72)],
    'dial': [(.32, .022, 255), (.36, .025, 250), (.395, .026, 245), (.425, .024, 240)],
    'rose': [(.33, .065, 5), (.38, .072, 12), (.43, .070, 22)],
    'teal': [(.30, .048, 215), (.355, .052, 205), (.41, .048, 195)],
    'cream': [(.36, .028, 70), (.41, .028, 78), (.45, .026, 85)],
    'cab': [(.24, .030, 290), (.29, .035, 300), (.35, .038, 330), (.41, .038, 20)],
    'coat': [(.19, .045, 250), (.26, .060, 240), (.34, .065, 228), (.42, .060, 214)],
    'scarf': [(.32, .090, 18), (.41, .100, 26), (.49, .090, 36)],
    'skin': [(.42, .060, 40), (.56, .070, 55), (.68, .075, 66)],
    'gw': [(.45, .095, 48), (.56, .120, 58), (.66, .135, 68), (.75, .130, 78)],
    'lamp': [(.63, .165, 55), (.77, .170, 70), (.87, .160, 85), (.96, .080, 100)],
    'iron': [(.18, .020, 270), (.27, .025, 265), (.37, .030, 260), (.46, .030, 250)],
    'leaf': [(.28, .050, 165), (.36, .060, 150)],
    'smoke': [(.385, .020, 285), (.425, .018, 295)],
    'rim': [(.355, .040, 282), (.395, .040, 276)],
}
PAL = build(RAMPS, {'eye': (.56, .080, 130)})


# ------------------------------------------------------------------ 1. the far haze in the cleft
def far(g, xl, xr):
    c = Canvas(W, H)
    c.bands(0, H, [('haze0', 0), ('haze1', 62, 14), ('haze2', 122, 14), ('haze3', 176, 14),
                   ('haze4', 292, 16), ('haze3', 384, 16), ('haze2', 452, 14)], edge='steps', amp=2, seed=4)
    g[:] = c.g
    # two far trunks: a wide one left (darker, nearer) and a thin one right (paler, farther)
    for (x0, wd, lean, ramp_lo, seed) in ((97, 15, -0.035, 0, 21), (166, 8, 0.02, 1, 22)):
        for y in range(H):
            xc = x0 + lean * (y - 240) + 1.5 * noise1(y / 60, seed)
            w_ = wd + 2 * noise1(y / 45, seed + 1)
            a, b = int(round(xc)), int(round(xc + w_))
            for x in range(a, b):
                v = 'ftr%d' % (ramp_lo + (1 if x - a < 2 else 0))
                if x >= b - 2:
                    v = 'ftr%d' % ramp_lo if ramp_lo == 0 else 'ftr1'
                put(g, x, y, v)
            # bark seams in broken runs on the far trunk
            if hsh(y // 5, seed) < 0.4 and b - a > 9:
                put(g, a + 4 + int(hsh(y // 9, seed + 2) * 5), y, 'ftr0')
    # three dim far windows of another tree town on the wide far trunk
    for (x, y, h_) in ((101, 166, 2), (104, 212, 1), (99, 356, 2)):
        for d in range(h_):
            put(g, x, y + d, 'win0')


# ------------------------------------------------------------------ 2. the trunk walls
def bark_walls(g, xl, xr):
    """vertical bark plates between meandering furrows, a lit left edge per plate, broken cross
    cracks; the cleft's inner side walls (left in shadow, right catching the skylight)"""
    wall = (XX < xl[:, None]) | (XX >= xr[:, None])
    # furrow centres: uneven spacing 13-30 px, each meandering
    furrows = []
    x = -6
    k = 0
    while x < W + 10:
        furrows.append((x, k))
        x += 13 + int(hsh(k, 51) * 18)
        k += 1
    fx = np.zeros((len(furrows), H))
    fw = np.zeros((len(furrows), H))
    for i, (x0, k) in enumerate(furrows):
        for y in range(H):
            fx[i, y] = x0 + 4.0 * noise1(y / 70, 60 + k) + 1.5 * noise1(y / 23, 80 + k)
            s = noise1(y / 85, 95 + k) + (0.55 if k % 3 else 0.15)      # some furrows fade out: plates merge
            fw[i, y] = (1.6 + 2.6 * (0.5 + 0.5 * noise1(y / 31, 90 + k))) * min(1.0, max(0.0, s * 2.2))
    # distance to the nearest furrow and which side of it
    d = np.full((H, W), 99.0)
    side = np.zeros((H, W))
    owner = np.zeros((H, W), int)
    for i in range(len(furrows)):
        dd = XX - fx[i][:, None]
        live = fw[i][:, None] > 0.6
        ad = np.where(live, np.abs(dd) - fw[i][:, None] / 2, 99.0)
        better = ad < d
        d = np.where(better, ad, d)
        side = np.where(better, np.sign(dd), side)
        owner += ((dd > 0) & live)
    tone = np.full((H, W), 3.0)
    # per-plate value: plates split at uneven heights, a third of them a step darker
    seg = (YY + (hsh_arr(owner, 0, 55) * 140).astype(int)) // (60 + (hsh_arr(owner, 1, 56) * 90).astype(int))
    dark_plate = hsh_arr(owner * 7 + seg, seg, 57) < 0.33
    tone[dark_plate] = 2.0
    tone[(d > 0) & (d < 3) & (side > 0)] = np.where(dark_plate, 3.0, 4.0)[(d > 0) & (d < 3) & (side > 0)]
    tone[(d > 0) & (d < 1.2) & (side > 0)] = 5.0      # plate's left edge (right of a furrow): lit
    tone[(d > 0) & (d < 2.5) & (side < 0)] = np.where(dark_plate, 1.0, 2.0)[(d > 0) & (d < 2.5) & (side < 0)]
    tone[d <= 0] = 1.0                                 # furrow
    tone[d <= -1.0] = 0.0
    # rim only where the plate edge faces up-left: thin it out by a hash in runs
    rim = (tone == 5.0) & (hsh_arr(XX // 3, YY // 7, 7) < 0.55)
    tone[(tone == 5.0) & ~rim] = 4.0
    # plate cross cracks: broken horizontal runs, a dark row with a lit lip below
    for i in range(len(furrows) - 1):
        for j in range(24):
            y = int(hsh(i, j, 3) * H)
            if hsh(i, j, 4) < 0.45:
                continue
            xa = int(fx[i][y] + fw[i][y] / 2 + 1)
            xb = int(fx[i + 1][y] - fw[i + 1][y] / 2 - 1)
            if xb - xa < 5:
                continue
            l0 = xa + int(hsh(i, j, 5) * 3)
            l1 = min(xb, l0 + 4 + int(hsh(i, j, 6) * (xb - xa)))
            for x in range(l0, l1):
                if 0 <= x < W:
                    tone[y, x] = 1.0
                    if y + 1 < H and tone[y + 1, x] >= 3:
                        tone[y + 1, x] = 4.0
    # large-scale shading: the walls turn darker toward the cleft (the trunk rounds into it)
    dl = xl[:, None] - XX
    dr = XX - xr[:, None]
    near_l = (dl > 0) & (dl < 14)
    near_r = (dr >= 0) & (dr < 10)
    tone = np.where(near_l & (tone >= 3), tone - 1, tone)
    # flake dashes on the plate bodies (stacked 1 px runs, clustered, never noise)
    for gy in range(0, H, 6):
        for gx in range(0, W, 10):
            if hsh(gx // 20, gy // 12, 9) > 0.5 or hsh(gx, gy, 10) > 0.6:
                continue
            ax = gx + int(hsh(gx, gy, 11) * 10)
            ay = gy + int(hsh(gx, gy, 12) * 6)
            L0 = 3 + int(hsh(gx, gy, 13) * 4)
            for kk in range(L0):
                x = ax + kk
                if 0 <= x < W and 0 <= ay < H and tone[ay, x] in (2.0, 3.0):
                    tone[ay, x] += 1.0
                if 0 <= x - 1 < W and ay + 1 < H and tone[ay + 1, x - 1] in (2.0, 3.0) and kk < L0 - 1:
                    tone[ay + 1, x - 1] -= 1.0
    for y in range(H):
        for x in range(W):
            if wall[y, x]:
                g[y, x] = 'bark%d' % int(tone[y, x])
    # the cleft's inner side walls: left wall's (facing right, in shadow), right wall's (lit)
    for y in range(H):
        a = xl[y]
        wl = 5 + int(2 * (0.5 + 0.5 * noise1(y / 29, 70)))
        for x in range(a - wl, a):
            v = 'bark1' if x < a - 1 else 'bark0'
            if (x - (a - wl)) == 0:
                v = 'bark2'                    # the front lip catches a little light
            if hsh(x, y // 4, 71) < 0.12:
                v = 'bark2'                    # grain flecks in short vertical runs
            put(g, x, y, v)
        b = xr[y]
        wr = 6 + int(2 * (0.5 + 0.5 * noise1(y / 33, 72)))
        for x in range(b, b + wr):
            v = 'bark3' if x > b + 1 else 'bark3'
            if x == b:
                v = 'bark4' if hsh(y // 3, 73) < 0.7 else 'bark3'
            if x == b + wr - 1:
                v = 'bark1'                    # where the inner wall meets the front face
            if hsh(x, y // 5, 74) < 0.15 and x > b:
                v = 'bark2'
            put(g, x, y, v)
    for y in range(H):
        put(g, xl[y] - 1, y, 'rim0' if hsh(y // 4, 75) < 0.8 else 'bark2')
        put(g, xr[y], y, 'rim1' if hsh(y // 3, 76) < 0.85 else 'rim0')
    return wall


# ------------------------------------------------------------------ 3. carved fronts, windows, doors
import shapes as SH


def opening(x0, y0, x1, y1, kind, seed):
    """the outline of a cut through the bark: 'arch' (round top), 'tall' (a taller, narrower arch),
    'oval' (a wide rounded front), 'rect' (rounded corners); the edge frayed like broken bark"""
    m = np.zeros((H, W), bool)
    w, h = x1 - x0, y1 - y0
    if kind in ('arch', 'tall'):
        r = w / 2
        m[int(y0 + r):y1, x0:x1] = True
        m |= ((XX + 0.5 - x0 - r) ** 2 / r ** 2 + (YY + 0.5 - y0 - r) ** 2 / r ** 2 <= 1) & (YY < y0 + r + 1)
    elif kind == 'oval':
        cx, cy = x0 + w / 2, y0 + h / 2
        m = (np.abs(XX + 0.5 - cx) / (w / 2)) ** 3 + (np.abs(YY + 0.5 - cy) / (h / 2)) ** 3 <= 1
    else:
        m[y0:y1, x0:x1] = True
        for (cx, cy) in ((x0 + 4, y0 + 4), (x1 - 5, y0 + 4)):
            corner = ((XX - cx) ** 2 + (YY - cy) ** 2 > 16) & (np.abs(XX - cx) <= 4) & (YY < cy) & (
                (XX < cx) if cx < (x0 + x1) / 2 else (XX > cx))
            m &= ~(corner & (YY >= y0) & (YY < y0 + 4))
    m &= (YY >= y0) & (YY < y1) & (XX >= x0) & (XX < x1)
    return SH.fray(m, teeth=0.16, notches=0.14, islands=0.0, depth=2, seed=seed)


def dwelling(g, x0, y0, x1, y1, kind='rect', seed=1, deep=4):
    """a front carved into the trunk: the heartwood face set back behind a broken bark lip; the lip
    throws a stepped shadow along the top and left inside, its cut face is lit along the bottom and
    right, long wavy grain lines and one knot on the face"""
    m = opening(x0, y0, x1, y1, kind, seed)
    lip = nb4(nb4(m)) & ~m
    g[nb4(lip) & ~lip & ~m] = 'bark1'
    g[lip] = 'bark2'
    # the lip's cut face, lit where it faces up-left (bottom and right of the opening)
    g[lip & shift(m, 0, 1)] = 'bark4'
    g[lip & shift(m, 0, 2) & ~shift(m, 0, 1)] = 'bark3'
    g[lip & shift(m, 1, 0)] = 'bark4'
    g[lip & shift(m, 2, 0) & ~shift(m, 1, 0)] = 'bark3'
    g[m] = 'hw2'
    # grain: a few long wavy lines, uneven spacing, broken
    xs = [x0 + 3 + int(hsh(seed, i, 81) * (x1 - x0 - 6)) for i in range(2 + (x1 - x0) // 16)]
    for i, gx in enumerate(xs):
        for y in range(y0, y1):
            x = int(round(gx + 1.5 * noise1(y / 11, seed * 7 + i)))
            if 0 <= x < W and m[y, x] and hsh(i, y // 5, seed + 83) < 0.75:
                g[y, x] = 'hw1' if i % 2 == 0 else 'hw3'
    kx, ky = x0 + int(hsh(seed, 84) * (x1 - x0 - 8)) + 4, y0 + int(hsh(seed, 85) * (y1 - y0 - 10)) + 6
    knot = """
    .ab.
    abba
    .ab.
    """
    if m[ky, kx]:
        stamp(g, knot, {'a': 'hw1', 'b': 'hw0'}, kx - 1, ky - 1)
    # the cast shadow inside: the lip's shadow along the top (deep px, stepped) and the left (2 px)
    top = m & ~shift(m, 0, 1)
    sh = top.copy()
    for k in range(1, deep):
        step = shift(top, 0, k) & m & (hsh_arr(XX // (3 + k), YY // 9, seed + 86 + k) < (1.0 - 0.18 * k))
        sh |= step
    left = m & ~shift(m, 1, 0)
    sh |= left | (shift(left, 1, 0) & m)
    g[sh] = 'hw1'
    g[top | left] = 'hw0'
    # the lit bottom inside edge (a sill where the face meets the floor of the cut)
    g[m & ~shift(m, 0, -1)] = 'hw3'
    return m


def awning(g, x0, x1, y, slot_top='wood3'):
    """a small shingle hood over a door or window: lit top course, shadowed lip, shadow under it"""
    for x in range(x0, x1):
        put(g, x, y, 'wood0' if x in (x0, x1 - 1) else slot_top)
        put(g, x, y + 1, 'wood2' if (x - x0) % 3 else 'wood1')
        put(g, x, y + 2, 'wood0')
        v = g[y + 3, x] if 0 <= y + 3 < H and 0 <= x < W else None
        if isinstance(v, str) and v.startswith('hw'):
            g[y + 3, x] = 'hw0' if v in ('hw1', 'hw0') else 'hw1'
    put(g, x0 + 1, y + 3, 'wood1'); put(g, x1 - 2, y + 3, 'wood1')


def window(g, x, y, kind, lit, w=6, h=8, shutters=None):
    """kinds: arch, round, square, slit, boarded. Lit: an amber pane with a darker top-left, a
    brighter lower-right core and a timber mullion; dark: deep glass with one haze reflection"""
    m = np.zeros((H, W), bool)
    if kind == 'round':
        r = w / 2
        m = ((XX + 0.5 - x - r) ** 2 + (YY + 0.5 - y - r) ** 2) <= r * r
        h = w
    else:
        m[y:y + h, x:x + w] = True
        if kind == 'arch':
            r = w / 2
            for yy in range(y, y + int(r)):
                for xx in range(x, x + w):
                    if ((xx + 0.5 - x - r) ** 2 + (yy + 0.5 - y - r) ** 2) > r * r:
                        m[yy, xx] = False
    frame = nb4(m) & ~m
    g[frame] = 'wood2' if lit else 'wood1'
    g[frame & ~shift(nb4(m), 0, -1)] = 'wood3'          # the sill under the window
    if kind == 'boarded':
        g[m] = 'bark0'
        for (px, py) in line_pts(x, y + 1, x + w - 1, y + h - 2) + line_pts(x, y + h - 2, x + w - 1, y + 1):
            put(g, px, py, 'wood3')
        return m
    if lit:
        g[m] = 'win2'
        g[m & ~shift(m, 0, 1)] = 'win1'
        g[m & ~shift(m, 1, 0)] = 'win1'
        core = m & shift(m, 0, 1) & shift(m, 1, 0) & shift(m, 0, -1) & shift(m, -1, 0)
        core &= (XX >= x + w // 2 - 1) & (YY >= y + h // 2 - 1)
        g[core] = 'win3'
        if kind in ('square', 'arch') and w >= 6:
            if w >= 11:                                   # three panes
                for cx in (x + w // 3, x + 2 * w // 3):
                    g[m & (XX == cx)] = 'wood1'
            else:
                cx = x + w // 2 - (1 if hsh(x, y, 92) < 0.5 else 0)
                g[m & (XX == cx)] = 'wood1'
            if h >= 9 and w >= 9:
                g[m & (YY == y + h // 2)] = 'wood1'
    else:
        g[m] = 'bark1'
        refl = m & ~shift(m, 1, 0) & ~shift(m, 0, 1)
        g[refl | (m & (XX == x + 1) & (YY == y + 2))] = 'haze0'
    if shutters:
        # mismatched shutters: the left one hangs open flat, the right one crooked and shorter
        for yy in range(y, y + h):
            put(g, x - 3, yy, 'teal1' if shutters == 'teal' else 'rose1')
            put(g, x - 2, yy, 'teal0' if shutters == 'teal' else 'rose0')
        for yy in range(y + 1, y + h - 1):
            put(g, x + w + 1, yy + 1, 'teal1' if shutters == 'teal' else 'rose1')
            put(g, x + w + 2, yy + 1, 'teal0' if shutters == 'teal' else 'rose0')
    return m


def door(g, x, y, w=7, h=11, lit=False, shape='arch'):
    """a plank door: 'arch' in a carved lintel arc, 'square' under a timber beam, 'hatch' a round
    door; an iron ring and a lit step"""
    m = np.zeros((H, W), bool)
    r = w / 2
    if shape == 'hatch':
        m = ((XX + 0.5 - x - r) ** 2 + (YY + 0.5 - y - h + w - r) ** 2) <= r * r
        y = y + h - w
        h = w
    else:
        m[y:y + h, x:x + w] = True
    if shape == 'arch':
        for yy in range(y, y + int(r)):
            for xx in range(x, x + w):
                if ((xx + 0.5 - x - r) ** 2 + (yy + 0.5 - y - r) ** 2) > r * r:
                    m[yy, xx] = False
    if shape == 'square':
        for xx in range(x - 2, x + w + 2):
            put(g, xx, y - 2, 'wood3'); put(g, xx, y - 1, 'wood1')
    if shape == 'arch':
        lintel = nb4(nb4(m)) & ~m & (YY < y + h)
        g[lintel & (YY < y + int(r) + 2)] = 'hw3'       # a carved arch band over the door
        g[lintel & (YY < y + int(r) + 2) & ((XX - x - w / 2) > 1)] = 'hw2'
    g[nb4(m) & ~m] = 'wood0'
    g[m] = 'wood2'
    for xx in range(x + 2, x + w, 2):
        g[m & (XX == xx)] = 'wood1'
    g[m & (XX == x)] = 'wood3'
    if lit:   # a door ajar: a sliver of amber at the latch side
        g[m & (XX == x + w - 2) & (YY > y + 2)] = 'win1'
    put(g, x + w - 2 - (1 if lit else 0), y + h // 2 + 1, 'iron3')
    for xx in range(x - 1, x + w + 1):
        put(g, xx, y + h, 'hw4')
        put(g, xx, y + h + 1, 'hw1')


def fronts(g):
    """the carved fronts with windows in five shapes and three sizes: 7 lit, the rest dark"""
    # L1 medium (top left): a rounded front with a lit square window under an awning, a dark slit, a door
    dwelling(g, 18, 32, 76, 82, 'rect', seed=3)
    awning(g, 41, 56, 42)
    window(g, 44, 47, 'square', True, 9, 8, shutters='teal')
    window(g, 64, 46, 'slit', False, 3, 11)
    door(g, 26, 62, 8, 15)
    # L2 small: a tall arch around the balcony door
    dwelling(g, 36, 112, 72, 162, 'tall', seed=5)
    door(g, 49, 138, 9, 15, lit=True)
    window(g, 40, 126, 'round', False, 5)
    # L3 big (bottom left): oval front, round lit window with a flower box, a lit arch, a boarded window
    dwelling(g, 4, 356, 84, 432, 'oval', seed=7, deep=5)
    window(g, 15, 373, 'round', True, 10)
    awning(g, 37, 52, 365)
    window(g, 40, 370, 'arch', True, 8, 13)
    window(g, 63, 380, 'boarded', False, 7, 8)
    door(g, 28, 410, 11, 16, shape='hatch')
    # R1 medium (top right)
    dwelling(g, 198, 56, 256, 106, 'arch', seed=9)
    window(g, 207, 78, 'arch', False, 7, 10)
    awning(g, 221, 238, 66)
    window(g, 224, 71, 'square', True, 11, 9)
    window(g, 246, 80, 'slit', True, 3, 9)
    door(g, 228, 88, 9, 14, shape='square')
    # R2 small
    dwelling(g, 214, 122, 250, 156, 'oval', seed=11)
    window(g, 222, 129, 'round', True, 8)
    door(g, 236, 140, 9, 9, shape='hatch')
    # R3 small: the watcher's lit window
    dwelling(g, 202, 270, 250, 302, 'rect', seed=13)
    window(g, 212, 279, 'square', True, 10, 9)
    window(g, 234, 278, 'slit', False, 3, 12)
    # R4 big: uneven windows, a door, the laundry balcony
    dwelling(g, 190, 344, 266, 412, 'arch', seed=15, deep=5)
    window(g, 199, 380, 'arch', True, 7, 11, shutters='rose')
    window(g, 216, 384, 'square', False, 6, 6)
    window(g, 238, 372, 'round', True, 9)
    window(g, 252, 388, 'slit', False, 3, 10)
    door(g, 224, 392, 9, 16)
    # R5 small landing front
    dwelling(g, 196, 436, 242, 478, 'rect', seed=17)
    window(g, 204, 446, 'square', False, 7, 7)
    door(g, 222, 454, 8, 12, shape='square')
    # small windows punched straight through the bark between the fronts (no carved face)
    for (x, y, kind, lit, w, h) in ((12, 160, 'round', False, 7, 7), (26, 300, 'arch', False, 5, 8),
                                    (244, 186, 'round', False, 6, 6), (258, 248, 'slit', True, 3, 8),
                                    (10, 470, 'square', False, 5, 5)):
        rim = window(g, x, y, kind, lit, w, h)
        ring = nb4(nb4(rim)) & ~nb4(rim)
        g[ring & ~shift(nb4(nb4(rim)), 1, 1)] = 'hw3'


# ------------------------------------------------------------------ 4. the clock
def clock(g):
    cx, cy, R = G.CLOCK
    rd = 22
    dx = XX + 0.5 - cx
    dy = YY + 0.5 - cy
    r2 = dx * dx + dy * dy
    ros = r2 <= R * R
    # the carved rosette: heartwood rings with scalloped petals, lit upper left
    ang = np.arctan2(dy, dx)
    redge = R - 2.2 + 2.2 * np.cos(ang * 12)
    ros = np.sqrt(r2) <= redge
    petal = (np.cos(ang * 12) > 0.35) & (r2 > (rd + 4) ** 2)
    g[nb4(ros) & ~ros] = 'bark1'
    g[ros] = 'hw2'
    g[ros & petal] = 'hw3'
    lit = ros & ((dx + dy) < -R * 0.3)
    g[lit & petal & (hsh_arr(XX // 2, YY // 2, 5) < 0.5)] = 'hw4'
    g[ros & ((dx + dy) > R * 0.55)] = 'hw1'
    ring = (r2 > (rd + 1) ** 2) & (r2 <= (rd + 3) ** 2)
    g[ring] = 'wood1'
    g[ring & ((dx + dy) < -rd * 0.5)] = 'wood3'
    g[ros & (r2 > (R - 1) ** 2)] = 'hw1'
    # the dial, 1 px off level: drawn about a centre nudged down-right by a pixel on one side
    dial = r2 <= (rd + 0.5) ** 2
    g[dial] = 'dial2'
    rr_ = np.sqrt(r2)
    # a lit crescent inside the upper-left rim, a shaded one inside the lower-right rim (concentric)
    g[dial & (rr_ > rd - 4) & ((dx + dy) < -rd * 0.35)] = 'dial3'
    g[dial & (rr_ > rd - 4) & ((dx + dy) > rd * 0.45)] = 'dial1'
    g[dial & (r2 > (rd - 1) ** 2)] = 'dial0'
    # hour ticks: 12, the quarters longer; the 4 o'clock tick chipped
    for hr in range(12):
        a = math.radians(hr * 30 - 90)
        L = 4 if hr % 3 == 0 else 2
        if hr == 4:
            L = 1
        for k in range(L):
            rr = rd - 2 - k
            put(g, cx + rr * math.cos(a) - 0.5 + 0.5, cy + rr * math.sin(a), 'bark0')
        if hr % 3 == 0:
            rr = rd - 3
            px = cx + rr * math.cos(a); py = cy + rr * math.sin(a)
            put(g, px + (1 if hr in (0, 6) else 0), py + (1 if hr in (3, 9) else 0), 'bark0')
    # hands at 8:10: minute hand toward the 2 (up-right, at the gondola's grip), hour hand near the 8
    def hand(deg, L, th):
        a = math.radians(deg - 90)
        for k in range(L):
            x = cx + k * math.cos(a); y = cy + k * math.sin(a)
            put(g, x, y, 'bark0')
            if th > 1 and k < L - 2:
                put(g, x + (1 if abs(math.sin(a)) > 0.5 else 0), y + (1 if abs(math.sin(a)) <= 0.5 else 0), 'bark0')
    hand(96, 18, 1)      # minute hand: 16 past, pointing at the gondola
    hand(218, 12, 2)     # hour hand: past 7
    put(g, cx, cy, 'wood4'); put(g, cx - 1, cy, 'bark0'); put(g, cx, cy - 1, 'bark0')
    # the clock ledge below the rosette with a pail
    for x in range(cx - 18, cx + 20):
        put(g, x, cy + R + 2, 'wood4' if x < cx + 6 else 'wood3')
        put(g, x, cy + R + 3, 'wood2')
        put(g, x, cy + R + 4, 'wood0')
    pail = """
    .oooo.
    oJjjjo
    .ojjo.
    .oiio.
    """
    stamp(g, pail, {'o': 'iron0', 'J': 'iron3', 'j': 'iron2', 'i': 'iron1'}, cx + 10, cy + R - 2)


# ------------------------------------------------------------------ 5. balconies, stairs, ladder, hoist
def balcony(g, x0, x1, y, rail=True, missing=None, struts=True, facing=1):
    """a timber platform: lit top plank, face, dark underside, brackets to the wall, a rail with
    balusters every 3-4 px (one missing), its shadow on the wall below"""
    for x in range(x0, x1):
        put(g, x, y, 'wood4' if hsh(x, y, 101) < 0.8 else 'wood3')
        put(g, x, y + 1, 'wood2')
        put(g, x, y + 2, 'wood1')
        put(g, x, y + 3, 'wood1' if hsh(x, 3, 102) < 0.5 else 'wood0')
    # shadow on the wall under it (one step down, 2 rows)
    for x in range(x0, x1):
        for yy in (y + 4, y + 5):
            v = g[yy, x] if 0 <= yy < H and 0 <= x < W else None
            if isinstance(v, str) and v[:-1] in ('bark', 'hw') and v[-1].isdigit():
                n = int(v[-1])
                g[yy, x] = '%s%d' % (v[:-1], max(0, n - 1))
    if struts:
        wall_x = x0 if facing > 0 else x1 - 1
        for k in range(6):
            put(g, wall_x + facing * k, y + 4 + k, 'wood1')
            put(g, wall_x + facing * k, y + 5 + k, 'wood0')
    if rail:
        for x in range(x0, x1):
            put(g, x, y - 6, 'wood3')
            put(g, x, y - 5, 'wood1')
        xs = list(range(x0, x1, 3)) + [x1 - 1]
        for i, x in enumerate(xs):
            if missing is not None and i == missing:
                continue
            for yy in range(y - 4, y):
                put(g, x, yy, 'wood2' if yy == y - 4 else 'wood1')


def ladder(g, x, y0, y1):
    for y in range(y0, y1):
        put(g, x, y, 'wood3'); put(g, x + 1, y, 'wood1')
        put(g, x + 6, y, 'wood3'); put(g, x + 7, y, 'wood1')
        if (y - y0) % 4 == 2:
            for xx in range(x + 2, x + 6):
                put(g, xx, y, 'wood3')
                put(g, xx, y + 1, 'wood0')


def stairs(g, x0, y0, n, dx=4, dy=3):
    """steps cut diagonally into the bark, climbing left: lit treads, shadowed risers, a rope rail"""
    for i in range(n):
        x = x0 - i * dx
        y = y0 - i * dy
        for xx in range(x, x + dx + 2):
            put(g, xx, y, 'hw4')
            put(g, xx, y + 1, 'hw2')
            for yy in range(y + 2, y + dy + 2):
                put(g, xx, yy, 'hw1')
        put(g, x + dx + 2, y, 'bark1')
        for yy in range(y + 1, y + dy + 3):
            put(g, x + dx + 2, yy, 'bark0')
    # rail posts and a sagging rope rail
    for i in range(0, n, 3):
        x = x0 - i * dx + 2
        y = y0 - i * dy
        for yy in range(y - 6, y):
            put(g, x, yy, 'wood2')
        put(g, x, y - 7, 'wood3')


def hoist(g):
    """the hoist arm off the left balcony with its pulley; the crate hangs in the cleft below"""
    y = 296
    x0, x1 = 70, 116
    for x in range(x0, x1):
        put(g, x, y, 'wood3'); put(g, x, y + 1, 'wood2'); put(g, x, y + 2, 'wood0')
    for (x, yy) in line_pts(x0 + 4, y + 16, x0 + 20, y + 3):
        put(g, x, yy, 'wood1'); put(g, x + 1, yy, 'wood0')
    # pulley wheel at the arm's end
    wheel = """
    .iii.
    iJjIi
    ijiji
    iIjIi
    .iii.
    """
    stamp(g, wheel, {'i': 'iron0', 'J': 'iron3', 'j': 'iron2', 'I': 'iron1'}, x1 - 6, y + 2)
    # two ropes down to the crate
    cx0 = x1 - 9
    for yy in range(y + 7, 322):
        put(g, cx0 + 1, yy, 'cab1')
        put(g, cx0 + 8, yy, 'cab1')
    crate = """
    oooooooooooo
    oLLlLLLLlLLo
    olmmmdmmmmlo
    odoooooooodo
    olmdmmmmdmlo
    olmmdmmdmmlo
    olmmmddmmmlo
    olmmdmmdmmlo
    oddddddddddo
    oooooooooooo
    """
    stamp(g, crate, {'o': 'wood0', 'L': 'wood4', 'l': 'wood3', 'm': 'wood2', 'd': 'wood1'}, cx0 - 1, 322)
    # the cat sitting on the crate lid, facing the gondola: ears, bean body, tail down the side
    cat = """
    .o...o...
    .oo.oo...
    .oOOOo...
    oOOeOOo..
    oOOOOOo..
    .oOOOo...
    oOOOOOo..
    oOoOOOOo.
    oOOOOOOOo
    .ooooooo.
    """
    stamp(g, cat, {'o': 'bark0', 'O': 'bark1', 'e': 'eye'}, cx0 + 2, 313)
    # a rim of skylight on the cat's head and back (upper left)
    for (x, yy) in ((cx0 + 4, 315), (cx0 + 3, 316), (cx0 + 3, 319), (cx0 + 2, 320)):
        put(g, x, yy, 'bark2')
    # the tail curling down the crate side
    for (x, yy) in ((cx0 + 11, 320), (cx0 + 12, 321), (cx0 + 12, 322), (cx0 + 12, 323), (cx0 + 12, 324), (cx0 + 11, 325)):
        put(g, x, yy, 'bark0')


def structures(g, xl, xr):
    # top bridge across the cleft: deck, rail, a shallow arched beam under it
    yb = 14
    a, b = xl[yb] - 10, xr[yb] + 10
    for x in range(a, b):
        put(g, x, yb, 'wood3'); put(g, x, yb + 1, 'wood2'); put(g, x, yb + 2, 'wood0')
        put(g, x, yb - 6, 'wood2'); put(g, x, yb - 5, 'wood0')
    for x in range(a, b, 4):
        for yy in range(yb - 4, yb):
            put(g, x, yy, 'wood1')
    for x in range(a + 4, b - 4):
        u = (x - a - 4) / (b - a - 8)
        yy = yb + 3 + int(round(7 * (1 - (2 * u - 1) ** 2)))
        put(g, x, yy + 0, 'wood1'); put(g, x, yy + 1, 'wood0')
    for x in (a + 18, b - 20):
        for yy in range(yb + 3, yb + 9):
            put(g, x, yy, 'wood1')
    # balconies (left wall's face right, right wall's face left)
    balcony(g, 54, xl[38] + 4, 38, missing=2, facing=1)          # L1 balcony, laundry post
    balcony(g, 44, xl[153] + 2, 153, missing=None, facing=1)      # L2 door balcony
    balcony(g, xr[42] - 4, 214, 42, missing=None, facing=-1)      # R1 balcony, laundry post
    balcony(g, xr[268] - 6, 222, 268, missing=3, facing=-1)       # the watcher's balcony
    balcony(g, 196, 232, 418, rail=True, missing=None, facing=-1) # R4 balcony
    balcony(g, xr[350] - 2, 210, 350, rail=True, facing=-1)       # R4 upper
    balcony(g, xr[466] - 4, 214, 466, rail=False, facing=-1)      # landing
    balcony(g, 46, xl[436] + 2, 436, missing=1, facing=1)         # L3 balcony
    # the hoist balcony on the left
    balcony(g, 60, xl[300] + 3, 300, missing=None, facing=1)
    ladder(g, 62, 157, 210)
    stairs(g, 246, 228, 14)
    hoist(g)
    # laundry posts
    for (x, y0, y1) in ((xl[38] + 2, 24, 34), (xr[42] - 3, 28, 38), (198, 330, 346), (230, 336, 350)):
        for yy in range(y0, y1):
            put(g, x, yy, 'wood2')
        put(g, x, y0, 'wood3')


# ------------------------------------------------------------------ 6. laundry
GARMENTS = {
    'shirt': """
    rrr...rrr
    rRRrrrRRr
    rRRRRRRRr
    .rrRRRrr.
    ..rRRRr..
    ..rRRRr..
    ..rRRRr..
    ..rrrrr..
    """,
    'tunic': """
    rr...rr
    rRRrRRr
    .rRRRr.
    .rRRRr.
    .rRRRr.
    .rrrrr.
    """,
    'towel': """
    ttttttt
    tTTTTTt
    twwwwwt
    tTTTTTt
    tTTTTTt
    twwwwwt
    tTTTTTt
    tTTTTTt
    ttttttt
    """,
    'sock': """
    cC
    cC
    cC
    cCc
    """,
    'pants': """
    ttttttt
    tTTTTTt
    tTTtTTt
    tTt.tTt
    tTt.tTt
    tTt.tTt
    tTt.tTt
    ttt.ttt
    """,
    'dress': """
    .ccc.
    .cCc.
    cCCCc
    cCCCCc
    ccccccc
    """,
    'sheet': """
    cccccccc
    cCCCCCCc
    cCCCCCCc
    cCCCCCCc
    cCCCCCCc
    .cCCCCCc
    ..ccccc.
    """,
}
GKEYS = {
    'rose': {'r': 'rose0', 'R': 'rose2', 't': 'rose0', 'T': 'rose1', 'c': 'rose0', 'C': 'rose1', 'w': 'rose2'},
    'teal': {'r': 'teal0', 'R': 'teal2', 't': 'teal0', 'T': 'teal1', 'c': 'teal0', 'C': 'teal1', 'w': 'teal2'},
    'cream': {'r': 'cream0', 'R': 'cream2', 't': 'cream0', 'T': 'cream1', 'c': 'cream0', 'C': 'cream2', 'w': 'cream1'},
}


def laundry(g, x0, y0, x1, y1, sag, items):
    pts = sag_line(x0, y0, x1, y1, sag)
    for (x, y) in pts:
        put(g, x, y, 'cab1')
    ys = {x: y for (x, y) in pts}
    for (x, kind, col) in items:
        art = GARMENTS[kind]
        rows = [r.strip() for r in art.strip('\n').split('\n') if r.strip()]
        half = len(rows) // 2
        rows = rows[:half] + ['.' + r for r in rows[half:]]       # the breeze from the left bellies them right
        stamp(g, '\n'.join(rows), GKEYS[col], x, ys.get(x, y0) + 1)
        # pegs
        put(g, x, ys.get(x, y0), 'cream2')


def laundry_all(g, xl, xr):
    laundry(g, xl[38] + 2, 25, xr[42] - 3, 29, 17, [
        (xl[38] + 5, 'shirt', 'cream'), (xl[38] + 17, 'sock', 'rose'), (xl[38] + 21, 'sock', 'teal'),
        (xl[38] + 27, 'towel', 'rose'), (xl[38] + 52, 'pants', 'teal'), (xl[38] + 63, 'dress', 'cream'),
        (xl[38] + 74, 'sock', 'cream')])
    laundry(g, 198, 331, 230, 337, 6, [(201, 'sheet', 'cream'), (212, 'tunic', 'rose'), (223, 'sock', 'teal')])


# ------------------------------------------------------------------ 7. townsfolk
FOLK_KEY = {'o': 'wood0', 'h': 'wood1', 'f': 'skin0', 'F': 'skin1', 'c': 'teal0', 'C': 'teal1',
            'r': 'rose0', 'R': 'rose1', 'k': 'cream0', 'K': 'cream1', 'b': 'wood2', 'w': 'wood3', 'y': 'win1'}
WATCHER = """
..ooo..
.ohhho.
.ohFFo.
.ofFFo.
..ofo..
.oRRRo.
oRRRRRo
wwwwwww
"""
CLIMBER = """
..ooo...
.ohhho..
.ohfFo..
..oFo...
.occco..
oCcCCco.
oco.cCo.
.ocCCo..
.oc.co..
.oc.co..
.oo.oo..
"""
SWEEPER = """
...ooo....
..ohhho...
..oFfho...
...oFo....
..okkKo...
.okKKKKo..
.okkKKoFo.
..okKKo.ob
..okkko..b
..ok.ko...
..oo.oo..b
.........bww
"""


def folk(g):
    stamp(g, WATCHER, FOLK_KEY, 222, 255)                 # leaning on the rail, watching the gondola
    put(g, 223, 258, 'win1')                              # the window behind rims his cheek
    stamp(g, CLIMBER, FOLK_KEY, 61, 182)                  # on the ladder
    stamp(g, SWEEPER, FOLK_KEY, 196, 454)                 # sweeping the landing


# ------------------------------------------------------------------ 8. flower box
def flowerbox(g):
    x, y = 14, 384
    for xx in range(x, x + 12):
        put(g, xx, y, 'wood3'); put(g, xx, y + 1, 'wood2'); put(g, xx, y + 2, 'wood0')
    for (xx, yy, v) in ((x + 1, y - 1, 'leaf1'), (x + 2, y - 2, 'leaf0'), (x + 3, y - 1, 'leaf1'), (x + 5, y - 1, 'leaf0'),
                        (x + 6, y - 2, 'leaf1'), (x + 8, y - 1, 'leaf1'), (x + 9, y - 2, 'leaf0'), (x + 10, y - 1, 'leaf1'),
                        (x + 2, y - 3, 'rose2'), (x + 6, y - 3, 'cream2'), (x + 9, y - 3, 'rose2')):
        put(g, xx, yy, v)


def chimney(g):
    """a stovepipe out of the left wall's bark by the cleft edge; its smoke rises, leans right with the
    breeze across the cleft and thins into a loose puff: a hand-shaped plume of two tones, never dots"""
    x, y = 79, 100
    for yy in range(y, y + 9):
        put(g, x, yy, 'iron2'); put(g, x + 1, yy, 'iron1'); put(g, x + 2, yy, 'iron0')
    for xx in range(x - 1, x + 4):
        put(g, xx, y, 'iron3' if xx < x + 2 else 'iron1'); put(g, xx, y + 1, 'iron0')
    plume = """
    .......................bbbbb........
    ..................bbbbbaaaaabb......
    ..............bbbbaaaaaaaaaaab......
    ...........bbbaaaaaaaaaabbbbb.......
    .........bbaaaaaaabbbbb.......bbbb..
    .......bbaaaaabbbb...........baaaab.
    ......baaaabb.................bbbb..
    .....baaabb.........................
    ....baab............................
    ....bab.............................
    ...baab.............................
    ...bab..............................
    ...bb...............................
    """
    stamp(g, plume, {'a': 'smoke1', 'b': 'smoke0'}, x - 3, y - 13)


def birds(g):
    for (x, y, f) in ((150, 6, 0), (157, 7, 1), (196, 36, 0)):
        art = ".o.\nooo\n.o." if f == 0 else "o..\nooo\n..."
        stamp(g, """
        .oo.
        oooo
        .o..
        """ if f == 0 else """
        oo..
        oooo
        ..o.
        """, {'o': 'bark0'}, x, y)


# ------------------------------------------------------------------ compose
def render():
    xl, xr = G.cleft_edges()
    g = new_grid()
    far(g, xl, xr)
    laundry_all(g, xl, xr)       # the cross-cleft line hangs behind the walls' lips? no: drawn first, walls clip it
    bark_walls(g, xl, xr)
    fronts(g)
    clock(g)
    structures(g, xl, xr)
    laundry_all(g, xl, xr)
    flowerbox(g)
    chimney(g)
    birds(g)
    folk(g)
    # the cable: everywhere except where the gondola covers it (it redraws its own inside)
    GD.draw_cable(g, 0, H)
    GD.gondola(g)
    return g


if __name__ == '__main__':
    g = render()
    save(g, PAL, '02-a', scale=4)
    crop_zoom('02-a', (96, 180, 186, 290), 5, 'hero')
    crop_zoom('02-a', (0, 190, 120, 290), 4, 'clock')
    crop_zoom('02-a', (150, 0, 270, 120), 4, 'topright')
    crop_zoom('02-a', (0, 0, 135, 240), 3, 'q1')
    crop_zoom('02-a', (135, 0, 270, 240), 3, 'q2')
    crop_zoom('02-a', (0, 240, 135, 480), 3, 'q3')
    crop_zoom('02-a', (135, 240, 270, 480), 3, 'q4')
    print('ok', len(set(g.ravel()) - {None}), 'slots used')
