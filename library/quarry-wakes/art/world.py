"""The cold world: dusk sky with a low ember band, terraced quarry walls, flooded pit water, the near
rim with a toppled lattice crane. Two canvases: far (behind the boss) and near (in front of the
soldier). Every pixel is a palette slot; no dither, hard bands of uneven height."""
import sys, math
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from canvas import Canvas, seam
import morph

W, H = 304, 224

def _h(a, b=0, s=0):
    h = (int(a) * 374761393 + int(b) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def stepped(x, pts):
    """piecewise-constant edge: pts = [(x_start, y), ...] sorted by x -> y at x"""
    y = pts[0][1]
    for xs, ys in pts:
        if x >= xs:
            y = ys
    return y

def sky(c):
    cols = np.arange(W)
    # band boundaries walk in flat runs joined by 1 px steps (seam 'steps'); heights uneven
    def edge(y, seed, amp=1):
        return y + seam(cols, 'steps', amp, seed)
    b1, b2, b3, b4 = edge(29, 3, 2), edge(51, 5, 1), edge(63, 7, 1), edge(73, 11, 1)
    # the ember band is a lens behind the boss: thick at x ~ 135, gone at the frame edges
    lens = np.clip(1 - ((cols - 138) / 118.0) ** 2, 0, 1)
    g0 = 92 - np.round(15 * lens ** 0.8).astype(int) + seam(cols, 'steps', 1, 13)
    g1 = 92 - np.round(9 * lens ** 1.1).astype(int) + seam(cols, 'steps', 1, 17)
    g2 = 92 - np.round(4 * lens ** 1.6).astype(int)
    for x in range(W):
        for y in range(0, 100):
            v = 'sky0'
            if y >= b1[x]: v = 'sky1'
            if y >= b2[x]: v = 'sky2'
            if y >= b3[x]: v = 'sky3'
            if y >= b4[x]: v = 'sky4'
            if lens[x] > 0.05 and y >= g0[x]: v = 'glow0'
            if lens[x] > 0.2 and y >= g1[x]: v = 'glow1'
            if lens[x] > 0.45 and y >= g2[x]: v = 'glow2'
            c.g[y, x] = v
    # long flat cloud streaks: one dominant bank, two thin ones, lit bellies over the band
    for (x0, x1, y, th, seed) in ((18, 196, 40, 4, 1), (150, 300, 22, 2, 2), (206, 262, 58, 2, 3)):
        for x in range(x0, x1):
            u = (x - x0) / float(x1 - x0)
            taper = min(1.0, u * 6, (1 - u) * 3)
            t = int(round(th * taper + 0.6 * math.sin(x * 0.07 + seed)))
            top = y - t + (1 if _h(x // 9, seed, 4) < 0.3 else 0)
            for yy in range(top, y + 1):
                c.put(x, yy, 'sky2' if y < 50 else 'sky3')
            c.put(x, y + 1, 'sky3' if y < 50 else 'sky4')         # lit belly toward the band
            if yy == top and _h(x, seed, 9) < 0.5:
                c.put(x, top, 'sky1' if y < 50 else 'sky2')

def terraces(c, x0, x1, top_y, benches, ramp, seed, lip_rows=1, road=None):
    """a terraced quarry wall: benches [(height, inset), ...] from the top down; each bench is a
    lit top lip, a face with uneven vertical cracks, a shadow row under the next lip."""
    total = sum(b[0] for b in benches)
    c.rect(x0, top_y + 1, x1, min(H, top_y + total + 1), ramp[1])     # base: no gaps under jogged lips
    y = top_y
    k = 0
    for (hgt, jog) in benches:
        edge = [(x0, y)]
        xx = x0
        while xx < x1:                                   # the lip walks in flat runs with 1 px jogs
            xx += 9 + int(_h(xx, k, seed) * 22)
            edge.append((xx, y + (1 if _h(xx, k + 7, seed) < 0.35 else 0) - (1 if _h(xx, k + 3, seed) < 0.15 else 0)))
        for x in range(x0, x1):
            ty = stepped(x, edge)
            for yy in range(ty, ty + hgt):
                if yy < 0 or yy >= H:
                    continue
                d = yy - ty
                v = ramp[2]
                if d < lip_rows:
                    v = ramp[3]                          # lit bench top
                elif d == lip_rows:
                    v = ramp[1]                          # the lip's shadow
                elif d >= hgt - 2:
                    v = ramp[1]
                c.g[yy, x] = v
        drill_marks(c, x0, x1, y + lip_rows + 2, y + hgt - 1, ramp[0], ramp[2] if ramp[2] != ramp[1] else ramp[3],
                    seed + 7 * k, every=(4, 9), frac=(0.3, 0.8))
        y += hgt
        k += 1
    return y

def drill_marks(c, x0, x1, ya, yb, dark, lit, seed, every=(3, 7), frac=(0.4, 0.95)):
    """vertical drill-hole scores down a bench face: a lit 1 px line with a dark partner to its
    right, every 3-7 px, of uneven length, some broken"""
    x = x0 + int(_h(x0, ya, seed) * every[1])
    k = 0
    while x < x1 - 1:
        n = int((yb - ya) * (frac[0] + (frac[1] - frac[0]) * _h(k, 1, seed)))
        brk = ya + 2 + int(_h(k, 2, seed) * max(1, n)) if _h(k, 3, seed) < 0.35 else -1
        for y in range(ya, min(yb, ya + n)):
            if y == brk:
                continue
            c.put(x, y, lit)
            c.put(x + 1, y, dark)
        x += every[0] + int(_h(k, 4, seed) * (every[1] - every[0] + 1))
        k += 1

def side_wall(c, benches, side, seed, bottom=150, band=(30, 250)):
    """a terraced side wall: benches [(top_y, edge_x), ...] top down; each bench reaches from the
    frame edge to a jagged end at edge_x, so the profile steps toward the pit. Each bench: a lit
    lip (warmed near the dusk band), a 2 px top, a shadow row, a face scored by drill marks; the
    end face toward the pit is lit on the right wall (it faces the light) and dark on the left."""
    for k, (ty, ex) in enumerate(benches):
        ny = benches[k + 1][0] if k + 1 < len(benches) else bottom
        for y in range(ty, ny + 2):
            j = int(_h((y - ty) // (2 + k % 3), k, seed + 3) * 3)          # jagged end in short runs
            xe = ex - j if side == 'left' else ex + j
            xs = range(0, xe) if side == 'left' else range(xe, W)
            d = y - ty
            for x in xs:
                v = 'side1'
                if d == 0:
                    near_band = ty < 104 and band[0] <= x <= band[1]
                    v = ('lipw1' if abs(x - xe) < 6 else 'lipw0') if near_band else 'side4'
                elif d <= 2:
                    v = 'side3' if d == 1 else 'side2'
                elif d == 3:
                    v = 'side0'
                c.put(x, y, v)
            if d > 3:                                                    # the end face
                if side == 'left':
                    c.put(xe - 1, y, 'side0'); c.put(xe - 2, y, 'side0')
                else:
                    c.put(xe, y, 'side3'); c.put(xe + 1, y, 'side2')
        x0, x1 = (0, ex - 3) if side == 'left' else (ex + 3, W)
        drill_marks(c, x0, x1, ty + 5, ny, 'side0', 'side2', seed + 11 * k)

def fallen_blocks(c, blocks, ramp=('side0', 'side1', 'side3', 'side4')):
    """fallen blocks at the foot of a wall: mismatched sizes, a lit top, a dark right side"""
    for (x, y, w, h) in blocks:
        c.rect(x, y, x + w, y + h, ramp[1])
        c.rect(x, y, x + w, y + 1, ramp[3])
        c.rect(x, y + 1, x + 1, y + h, ramp[2])
        c.rect(x + w - 1, y + 1, x + w, y + h, ramp[0])
        c.rect(x, y + h - 1, x + w, y + h, ramp[0])

def water(c, y0):
    cols = np.arange(W)
    e1 = y0 + 12 + seam(cols, 'steps', 1, 21)
    e2 = y0 + 33 + seam(cols, 'steps', 1, 23)
    e3 = y0 + 56 + seam(cols, 'steps', 2, 29)
    for x in range(W):
        for y in range(y0, H):
            v = 'water3'
            if y >= e1[x]: v = 'water2'
            if y >= e2[x]: v = 'water1'
            if y >= e3[x]: v = 'water0'
            c.g[y, x] = v
    # the far shore line: a dark row where the wall meets the water
    for x in range(W):
        c.put(x, y0, 'water1')
    # swell streaks: short light dashes, mismatched, leaning with the wind; fewer and darker near
    for i in range(46):
        x = int(_h(i, 1, 31) * W)
        y = y0 + 3 + int((_h(i, 2, 31) ** 1.3) * (H - y0 - 6))
        n = 3 + int(_h(i, 3, 31) * (12 if y < y0 + 30 else 7))
        slot = 'water4' if y < y0 + 34 else 'water3'
        if y >= e3[min(W - 1, x)]:
            slot = 'water2'
        for k in range(n):
            c.put(x + k, y, slot)

def flakes_face(c, mask, ramp, seed, density=0.05):
    """stacked flake dashes on a rock face (lit end on the left), hand-scattered"""
    ys, xs = np.nonzero(mask)
    for i in range(len(xs)):
        x, y = xs[i], ys[i]
        if _h(x // 3, y, seed) < density and _h(x, y, seed + 1) < 0.5:
            n = 2 + int(_h(x, y, seed + 2) * 5)
            for k in range(n):
                if 0 <= x + k < W and mask[y, x + k]:
                    c.g[y, x + k] = ramp[3] if k == 0 else ramp[2]
                    if y + 1 < H and mask[y + 1, x + k] and k > 0:
                        c.g[y + 1, x + k] = ramp[1]

def near_rim(c):
    """the near quarry lip across the full width: low and broken at the left, rising to the
    soldier's ledge at the right; a lit lip, flake dashes on the face, mismatched boulders"""
    m = np.zeros((H, W), bool)
    top = [(0, 203), (11, 201), (19, 204), (33, 206), (47, 205), (58, 207), (74, 206), (90, 204),
           (104, 205), (121, 203), (137, 202), (150, 200), (166, 201), (179, 199), (190, 197),
           (199, 193), (211, 191), (226, 192), (238, 189), (251, 190), (263, 188), (281, 187),
           (296, 185)]
    for x in range(W):
        m[stepped(x, top):, x] = True
    c.fill(m, 'rock2')
    face = m & ~morph.shift(m, 0, 1, False)
    c.fill(face, 'rock4')
    lip2 = morph.shift(face, 0, 1, False) & m
    c.fill(lip2, 'rock3')
    lower = m.copy()
    lower[:213] = False
    c.fill(lower & ~lip2 & ~face, 'rock1')
    flakes_face(c, m & ~face & ~lip2, ('rock0', 'rock1', 'rock2', 'rock3'), 41, 0.06)
    # boulders on the rim: mismatched sizes, lit cap up-left
    for (bx, by, bw, bh) in ((214, 189, 9, 5), (231, 188, 5, 3), (296, 182, 8, 4), (8, 199, 7, 4),
                             (63, 203, 11, 5), (140, 199, 6, 4)):
        for yy in range(by, by + bh):
            for xx in range(bx, bx + bw):
                u, v = (xx - bx) / bw - 0.5, (yy - by) / bh - 0.5
                if u * u + v * v * 1.3 <= 0.27:
                    c.put(xx, yy, 'rock3' if (u + v) < -0.25 else ('rock1' if (u + v) > 0.3 else 'rock2'))
    return m

def crane(c):
    """a toppled lattice crane lying diagonally across the lower right: the boom's tip broken
    over the rim at the lower left, its cab tipped on its side at the right. Cold steel a value
    step above the rim (chords crane3-crane4), a cast shadow under it. Returns its mask."""
    before = c.g.copy()
    x0, y0, x1, y1 = 199, 209, 288, 181
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = uy, -ux                                     # perpendicular (up-left side)
    w = 10
    for t in range(int(L)):                              # cast shadow on the rim under the boom
        c.put(x0 + ux * t + 1, y0 + uy * t + 2, 'rock0')
        c.put(x0 + ux * t + 1, y0 + uy * t + 3, 'rock1')
    s_, k = 3.0, 0
    while s_ < L - 4:                                    # lattice web, bays of uneven length
        bay = 8 + (k * 3) % 4
        a = (x0 + ux * s_ + nx * 1.5, y0 + uy * s_ + ny * 1.5)
        b = (x0 + ux * (s_ + bay) + nx * (w - 1.5), y0 + uy * (s_ + bay) + ny * (w - 1.5))
        if k % 2:
            a, b = (a[0] + nx * (w - 3), a[1] + ny * (w - 3)), (b[0] - nx * (w - 3), b[1] - ny * (w - 3))
        if k != 4:                                       # one bay's diagonal snapped off
            c.line(a[0], a[1], b[0], b[1], 'crane3')
        else:
            c.line(a[0], a[1], (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 2, 'crane3')
        c.line(x0 + ux * s_ + nx * 1.5, y0 + uy * s_ + ny * 1.5, x0 + ux * s_ + nx * (w - 1.5),
               y0 + uy * s_ + ny * (w - 1.5), 'crane2')
        s_ += bay
        k += 1
    for (off, sl) in ((0, 'crane2'), (1, 'crane1')):    # bottom chord, 2 px
        c.line(x0 + nx * off, y0 + ny * off + 0, x1 + nx * off, y1 + ny * off, sl)
    for (off, sl) in ((w, 'crane4'), (w - 1, 'crane3')):  # lit top chord, 2 px
        c.line(x0 + nx * off, y0 + ny * off, x1 + nx * off, y1 + ny * off, sl)
    # the broken tip: chords bent down over the rim edge, a sheave, a hook on a slack cable
    c.line(x0, y0, x0 - 5, y0 + 6, 'crane3')
    c.line(x0 + nx * w, y0 + ny * w, x0 - 6, y0 - 2, 'crane3')
    c.disc(x0 - 6, y0 + 3, 2.4, 'crane3'); c.put(x0 - 6, y0 + 3, 'crane0'); c.put(x0 - 7, y0 + 2, 'crane4')
    for t in range(0, 9):
        c.put(x0 - 8 + (1 if t > 5 else 0), y0 + 5 + t, 'crane2')
    c.rect(x0 - 9, y0 + 14, x0 - 6, y0 + 15, 'crane3'); c.put(x0 - 9, y0 + 15, 'crane3'); c.put(x0 - 9, y0 + 16, 'crane4')
    # cab tipped on its side at the boom's base: 20 x 15, its roof now facing left
    cx0, cy0 = 284, 166
    c.rect(cx0, cy0, cx0 + 20, cy0 + 16, 'crane2')
    c.rect(cx0, cy0, cx0 + 20, cy0 + 2, 'crane4')       # lit top edge (was its side)
    c.rect(cx0, cy0 + 2, cx0 + 2, cy0 + 16, 'crane3')   # the roof, now facing left, lit
    c.rect(cx0, cy0 + 15, cx0 + 20, cy0 + 16, 'crane0')
    c.rect(cx0 + 5, cy0 + 4, cx0 + 14, cy0 + 10, 'crane0')   # the window hole
    c.put(cx0 + 6, cy0 + 5, 'crane4'); c.put(cx0 + 7, cy0 + 5, 'crane3'); c.put(cx0 + 6, cy0 + 6, 'crane3')
    c.rect(cx0 + 3, cy0 + 12, cx0 + 18, cy0 + 13, 'crane1')                # a door seam
    for (rx, ry) in ((16, 4), (17, 9), (3, 6)):
        c.put(cx0 + rx, cy0 + ry, 'crane4')
    c.disc(x1 + 1, y1 + nx * 0 - 3, 3.2, 'crane3'); c.disc(x1 + 1, y1 - 3, 1.5, 'crane0')   # boom foot pin
    return ~np.equal(c.g, before)

def details(c):
    """fence posts, a drum barrel, a dead floodlight mast on the far terraces"""
    for (x, y, h, lean) in ((216, 191, 9, 1), (231, 190, 7, -1)):
        for k in range(h):
            xx = x + (lean if k > h // 2 else 0)
            c.put(xx, y - k, 'crane2'); c.put(xx + 1, y - k, 'crane0')
        c.put(x + (lean if h > 2 else 0), y - h + 1, 'crane3')
    # barrel 7x9 by the soldier
    bx, by = 290, 181
    c.rect(bx, by, bx + 7, by + 9, 'crane1')
    c.rect(bx, by, bx + 2, by + 9, 'crane2')
    c.rect(bx + 6, by, bx + 7, by + 9, 'crane0')
    c.rect(bx, by + 2, bx + 7, by + 3, 'crane0'); c.rect(bx, by + 6, bx + 7, by + 7, 'crane0')
    c.rect(bx, by, bx + 7, by + 1, 'crane3')
    # floodlight mast, far terrace (1 x 12) with a bent head
    for k in range(12):
        c.put(232, 104 - k, 'far0')
    c.put(233, 92, 'far0'); c.put(234, 92, 'far0'); c.put(234, 93, 'far0')

def build(slam=False):
    """-> (far, near): two canvases (None = clear). near holds the rim, crane and props."""
    far = Canvas(W, H, None)
    sky(far)
    # far terraced wall behind the boss: benches of uneven height (14, 6, 11, 17 rows)
    terraces(far, 0, W, 92, [(14, 0), (6, 0)], ('haze0', 'haze1', 'haze2', 'haze3'), 7)       # far tier, hazed
    terraces(far, 0, W, 112, [(11, 0), (17, 0)], ('far0', 'far1', 'far2', 'far3'), 8)       # nearer tier
    # haul road zig-zag down the far benches (a lighter 1 px line)
    for (xa, ya, xb, yb) in ((176, 94, 214, 105), (214, 106, 160, 117), (160, 118, 205, 131)):
        far.line(xa, ya, xb, yb, 'far3')
    # side walls: benches stepping toward the pit (a staircase profile), mismatched heights
    side_wall(far, [(36, 46), (57, 55), (69, 61), (96, 70), (113, 77), (131, 83)], 'left', 3)
    side_wall(far, [(52, 250), (66, 243), (90, 236), (101, 231), (128, 224)], 'right', 9)
    fallen_blocks(far, [(84, 144, 7, 4), (93, 146, 4, 3), (71, 146, 10, 4), (214, 145, 6, 4), (205, 147, 3, 2),
                        (226, 147, 9, 3)])
    water(far, 140)
    # the window's reflection: three gold dashes on the water under the boss (set by the scene)
    near = Canvas(W, H, None)
    rim = near_rim(near)
    crane(near)
    details(near)
    return far, near

if __name__ == '__main__':
    sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/06-quarry-wakes/art')
    from pal import PAL
    f, n = build()
    f.paste(n)
    f.image(PAL).resize((W * 3, H * 3), 0).save(sys.argv[1] if len(sys.argv) > 1 else '/tmp/world.png')
