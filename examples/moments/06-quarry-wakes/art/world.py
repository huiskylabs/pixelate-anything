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
            # cracks: uneven vertical seams down the face
            if _h(x, k, seed + 5) < 0.06:
                ln = 2 + int(_h(x, k, seed + 6) * (hgt - 3))
                for yy in range(ty + 2, min(ty + hgt - 1, ty + 2 + ln)):
                    c.put(x, yy, ramp[0])
        y += hgt
        k += 1
    return y

def side_wall(c, benches, side, seed, bottom=150):
    """a terraced side wall: benches [(top_y, edge_x), ...] top down; each bench reaches from the
    frame edge to edge_x (left) or from edge_x to the edge (right), so the profile steps inward."""
    ramp = ('side0', 'side1', 'side2', 'side3', 'side4')
    for k, (ty, ex) in enumerate(benches):
        ny = benches[k + 1][0] if k + 1 < len(benches) else bottom
        xs = range(0, ex) if side == 'left' else range(ex, W)
        for x in xs:
            jog = 1 if _h(x // 7, k, seed) < 0.3 else 0
            for y in range(ty + jog, ny + 2):
                d = y - ty - jog
                v = 'side1'
                if d < 2:
                    v = 'side3' if d == 0 else 'side2'          # lit bench lip, 2 rows
                elif d == 2:
                    v = 'side0'                                  # shadow under the lip
                c.put(x, y, v)
            if _h(x, k, seed + 5) < 0.07:                        # drill lines and cracks
                ln = 3 + int(_h(x, k, seed + 6) * max(1, ny - ty - 6))
                for y in range(ty + 4, min(ny - 1, ty + 4 + ln)):
                    c.put(x, y, 'side0')
        # the bench's end face toward the pit: 1 px lit edge on the left wall, dark on the right
        ex2 = ex - 1 if side == 'left' else ex
        for y in range(ty + 1, ny + 2):
            c.put(ex2, y, 'side2' if side == 'left' else 'side0')
        c.put(ex2, ty, 'side4' if side == 'left' else 'side3')

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
    """a toppled lattice crane: the boom lying on the rim (tip broken over the edge at the
    left), its cab tipped on its side at the right. Cold steel, chipped. Returns its mask."""
    before = c.g.copy()
    # boom: two chords from (200, 196) to (300, 171), 9 px apart, lattice between
    x0, y0, x1, y1 = 205, 196, 292, 182
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = uy, -ux                                     # perpendicular (up-left side)
    w = 9
    top = [(x0 + nx * w, y0 + ny * w), (x1 + nx * w, y1 + ny * w)]
    # lattice diagonals (a zig-zag, bays of uneven length), drawn first, chords over them
    s, k = 2.0, 0
    while s < L - 4:
        bay = 7 + (k % 3)
        a = (x0 + ux * s, y0 + uy * s)
        b = (x0 + ux * (s + bay) + nx * (w - 1), y0 + uy * (s + bay) + ny * (w - 1))
        if k % 2:
            a, b = (a[0] + nx * (w - 1), a[1] + ny * (w - 1)), (b[0] - nx * (w - 1), b[1] - ny * (w - 1))
        if not (k == 5):                                 # one bay's diagonal snapped off
            c.line(a[0], a[1], b[0], b[1], 'crane2')
        s += bay
        k += 1
    c.line(x0, y0, x1, y1, 'crane3')                    # bottom chord
    c.line(x0 + ux, y0 + uy + 1, x1 + ux, y1 + uy + 1, 'crane0')
    c.line(top[0][0], top[0][1], top[1][0], top[1][1], 'crane3')   # lit top chord
    c.line(top[0][0], top[0][1] + 1, top[1][0], top[1][1] + 1, 'crane1')
    # the broken tip: chords bent down over the rim, a sheave and a hook on a slack cable
    c.line(x0, y0, x0 - 6, y0 + 7, 'crane2')
    c.line(top[0][0], top[0][1], top[0][0] - 4, top[0][1] + 10, 'crane2')
    c.disc(x0 - 5, y0 + 6, 2, 'crane3')
    c.put(x0 - 5, y0 + 6, 'crane0')
    for t in range(0, 14):
        c.put(x0 - 6 + (1 if t > 9 else 0), y0 + 8 + t, 'crane1')
    c.rect(x0 - 7, y0 + 22, x0 - 4, y0 + 23, 'crane2')
    c.put(x0 - 7, y0 + 23, 'crane2'); c.put(x0 - 7, y0 + 24, 'crane3')
    # cab tipped on its side: an 18x14 box, roof facing left, one broken window
    cx0, cy0 = 286, 171
    c.rect(cx0, cy0, cx0 + 18, cy0 + 16, 'crane1')
    c.rect(cx0, cy0, cx0 + 18, cy0 + 2, 'crane3')       # lit top edge (was its side)
    c.rect(cx0, cy0 + 2, cx0 + 2, cy0 + 16, 'crane2')   # the roof, now facing left
    c.rect(cx0 + 5, cy0 + 4, cx0 + 13, cy0 + 10, 'crane0')   # window hole
    c.put(cx0 + 6, cy0 + 5, 'crane3'); c.put(cx0 + 7, cy0 + 5, 'crane2')   # glass shard
    c.put(cx0 + 12, cy0 + 9, 'crane2')
    c.rect(cx0 + 3, cy0 + 12, cx0 + 17, cy0 + 13, 'crane0')               # a door seam
    c.put(cx0 + 15, cy0 + 4, 'crane3')
    return ~np.equal(c.g, before)

def details(c):
    """fence posts, a drum barrel, a dead floodlight mast on the far terraces"""
    for (x, y, h, lean) in ((222, 192, 9, 1), (262, 188, 7, -1)):
        for k in range(h):
            xx = x + (lean if k > h // 2 else 0)
            c.put(xx, y - k, 'crane2'); c.put(xx + 1, y - k, 'crane0')
        c.put(x + (lean if h > 2 else 0), y - h + 1, 'crane3')
    # barrel 7x9 by the soldier
    bx, by = 246, 182
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
    terraces(far, 0, W, 92, [(14, 0), (6, 0), (11, 0), (17, 0)], ('far0', 'far1', 'far2', 'far3'), 7)
    # haul road zig-zag down the far benches (a lighter 1 px line)
    for (xa, ya, xb, yb) in ((176, 94, 214, 105), (214, 106, 160, 117), (160, 118, 205, 131)):
        far.line(xa, ya, xb, yb, 'far3')
    # side walls: benches stepping toward the pit (a staircase profile), mismatched heights
    side_wall(far, [(36, 46), (57, 55), (69, 61), (96, 70), (113, 77), (131, 83)], 'left', 3)
    side_wall(far, [(52, 250), (66, 243), (90, 236), (101, 231), (128, 224)], 'right', 9)
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
