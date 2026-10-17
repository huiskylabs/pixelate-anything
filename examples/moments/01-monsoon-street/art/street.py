"""Monsoon Street: the photo's street rebuilt in its own one-point camera (geom.py), drawn as albedo
slots on the native 480x270 grid, then lit by one multiplied lamp map at screen resolution.

Phases drawn here: 'a' downpour (the tram crosses) and 'b' 2 a.m. (the mirror). Every vertical
surface records its ground-contact row in B, so the wet ground mirrors each object about its own
base line in screen columns (the one-point mirror); lights stretch into stepped dash columns.
"""
import sys, math, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
from canvas import Canvas
import fx
import geom as G
from geom import W, H, P, row, col, yh
from mpal import PAL, EMISSIVE, darker

T_LOOP = 96


def hsh(*a):
    """deterministic hash in [0, 1)"""
    v = 0x9E3779B1
    for k in a:
        v = (v ^ (int(k) * 0x85EBCA77 + 0x165667B1)) & 0xFFFFFFFF
        v = (v * 0xC2B2AE3D) & 0xFFFFFFFF
        v ^= v >> 15
    return (v & 0xFFFFFF) / float(0x1000000)


# ---------------------------------------------------------------- invented glyphs
# My own blocky stroke primitives, drawn on the left half and mirrored (thick, symmetric, 40-62% fill,
# one connected piece): they read as a sign script but are no letter of any real script. Each sign
# speaks its own dialect (a primitive subset), so no two signs share a look.
def _crown(g, r):
    h, hw = g.shape
    g[0, :] = True
    g[1, ::2] = True


def _post(g, r):
    h, hw = g.shape
    g[int(r(1) * h * 0.4):, max(0, hw - 2):] = True


def _fork(g, r):
    h, hw = g.shape
    g[h - 1 - h // 3:, 0] = True
    g[h - 1 - h // 3, :] = True


def _eye(g, r):
    h, hw = g.shape
    y = h // 2 - 1 + int(r(2) * 2)
    y = min(max(1, y), h - 3)
    g[y - 1:y + 2, max(0, hw - 3):] = True
    g[y, hw - 1] = False


def _step(g, r):
    h, hw = g.shape
    for k in range(hw):
        y = h - 1 - k * 2
        if 0 <= y < h:
            g[max(0, y - 1):y + 1, k] = True


def _bar2(g, r):
    h, hw = g.shape
    y = int(r(3) * (h - 2))
    g[y:y + 2, int(r(4) * 2):] = True


def _hook(g, r):
    h, hw = g.shape
    g[h // 2:, 0] = True
    g[h - 1, :max(2, hw - 1)] = True


def _cap(g, r):
    h, hw = g.shape
    g[0:2, max(0, hw - 2):] = True
    g[1, max(0, hw - 3)] = True


DIALECTS = [(_crown, _eye, _fork, _post, _bar2), (_post, _step, _hook, _bar2), (_cap, _eye, _hook, _fork),
            (_bar2, _post, _step, _cap), (_crown, _hook, _eye, _step)]


def _runs(v):
    v = np.asarray(v, int)
    return int(((v[1:] == 1) & (v[:-1] == 0)).sum() + v[0])


def _label_ok(g):
    """one piece, and complex both ways (some row and some column cross two strokes), so it is
    never a bare T, I, L or a Greek pi"""
    from scipy import ndimage
    if ndimage.label(g)[1] != 1:
        return False
    if g.shape[1] <= 3:
        return True
    return max(_runs(r) for r in g) >= 2 and max(_runs(c) for c in g.T) >= 2


def rune(seed, w=7, h=9, dialect=0, fill=(0.38, 0.62)):
    """an invented sign glyph (bool h x w) in one dialect, reseeded until it is one piece in range"""
    hw = (w + 1) // 2
    prims = DIALECTS[dialect % len(DIALECTS)]
    best = None
    for k in range(600):
        if k == 300:                                    # a dialect too poor for this box: borrow
            prims = prims + DIALECTS[(dialect + 2) % len(DIALECTS)]
        rs = lambda j, k=k: hsh(seed, k, j, dialect)
        g = np.zeros((h, hw), bool)
        n = 2 + int(rs(0) * 2)
        chosen = []
        for j in range(8):
            pr = prims[int(rs(10 + j) * len(prims))]
            if pr not in chosen:
                chosen.append(pr)
            if len(chosen) == n:
                break
        for q, pr in enumerate(chosen):
            pr(g, lambda z, q=q: rs(40 + q * 9 + z))
        full = np.concatenate([g, g[:, :w - hw][:, ::-1]], 1)
        f = full.mean()
        if full.any() and _label_ok(full):
            if fill[0] <= f <= fill[1]:
                return full
            if best is None or abs(f - 0.5) < abs(best.mean() - 0.5):
                best = full
    return best


def parse(art):
    rows = [r for r in art.strip('\n').split('\n')]
    return np.array([[ch == '#' for ch in r] for r in rows], bool)


def small_glyph(seed, w=5, h=5, dialect=3):
    return rune(seed, w, h, dialect, fill=(0.36, 0.66))


class Street:
    def __init__(self, phase='a', t=40):
        self.ph, self.t = phase, t
        self.c = Canvas(W, H, 'void')
        self.g = self.c.g
        self.B = np.full((H, W), np.nan, np.float32)     # ground-contact row of each vertical pixel
        self.GR = np.zeros((H, W), np.int8)               # 1 road, 2 pavement, 3 puddle
        self.INT = np.zeros((H, W), bool)                 # deliberate flecks (rain, drips, glints)
        self.ACT = np.zeros((H, W), bool)                 # the actor (the cat)
        self.NOREF = np.zeros((H, W), bool)               # vertical pixels that must not mirror
        self.lights = []
        self.cols = []
        self.spills = []                                  # soft warm ground spills (masks -> lamp map)
        self.awnings = []
        self.yy, self.xx = np.mgrid[0:H, 0:W]

    # ------------------------------------------------------------ primitives
    def put(self, m, slot, base=None, wallX=None):
        self.g[m] = slot
        if wallX is not None:
            xs = self.xx[m] + 0.5
            Z = G.F * wallX / (xs - G.VPX)
            self.B[m] = G.HZ + G.F * G.CAM_H / Z
        elif base is not None:
            self.B[m] = base
        return m

    def poly(self, pts, slot, base=None, wallX=None):
        return self.put(self.c.mask_poly(pts), slot, base, wallX)

    def wall(self, X, Z0, Z1, Y0, Y1, slot):
        return self.poly([P(X, Y0, Z0), P(X, Y0, Z1), P(X, Y1, Z1), P(X, Y1, Z0)], slot, wallX=X)

    def front(self, Z, X0, X1, Y0, Y1, slot):
        return self.poly([P(X0, Y0, Z), P(X1, Y0, Z), P(X1, Y1, Z), P(X0, Y1, Z)], slot, base=row(Z))

    def rect(self, x0, y0, x1, y1, slot, base=None):
        m = np.zeros((H, W), bool)
        m[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))] = True
        return self.put(m, slot, base)

    def px(self, x, y, slot, base=None):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H:
            self.g[y, x] = slot
            if base is not None:
                self.B[y, x] = base

    def stamp(self, mask, x0, y0, slot, base=None):
        h, w = mask.shape
        for j in range(h):
            for i in range(w):
                if mask[j, i]:
                    self.px(x0 + i, y0 + j, slot, base)

    def light(self, x, y, sig, colour, gain):
        self.lights.append((x, y, sig, colour, gain))

    def spill(self, pts, gain, colour=(1.0, 0.72, 0.42), blur=2.5):
        """a soft warm trapezoid of light on the ground in front of a lit opening"""
        self.spills.append((pts, gain, colour, blur))

    def gspill(self, X, z0, z1, out, gain):
        """a spill on the ground beside a receding wall at X: from its base out `out` metres"""
        s = 1 if X < 0 else -1
        self.spill([P(X, 0, z0), P(X, 0, z1), P(X + s * out, 0, z1 + 0.6), P(X + s * out, 0, z0 - 0.6)], gain)

    def wire(self, x0, y0, x1, y1, sag, slot='plum'):
        pts = self.c.catenary(x0, y0, x1, y1, sag, slot)
        for (x, y) in pts:
            if 0 <= x < W and 0 <= y < H:
                self.NOREF[int(y), int(x)] = True

    # ------------------------------------------------------------ far end
    def sky_and_far(self):
        a = self.ph == 'a'
        # night sky strip over the far roofline (rain cloud lit by the city in A, clear navy in B)
        self.c.bands(0, 60, [('sky0', 0), ('sky1', 14 if a else 24, 8), ('sky2', 30 if a else 40, 6)],
                     dither='checker')
        self.B[0:60, :] = G.HZ
        # the far building across the cross street: Z 41, 9.8 px per metre, six storeys
        Z = G.Z_FARWALL
        roof = 28
        self.rect(150, roof, 380, int(G.FARWALL_ROW) + 1, 'plum', base=row(Z))
        # parapet with a lit lip, a water tank and a rooftop sign frame (silhouettes on the sky)
        self.rect(150, roof - 2, 380, roof, 'cool1', base=row(Z))
        self.rect(236, roof - 9, 247, roof - 2, 'cool0', base=row(Z))          # tank body
        self.rect(235, roof - 10, 248, roof - 9, 'cool1', base=row(Z))
        for lx in (237, 245):
            self.rect(lx, roof - 3, lx + 1, roof, 'cool0', base=row(Z))
        for fx_ in range(268, 297, 7):                                           # sign frame lattice
            self.rect(fx_, roof - 14, fx_ + 1, roof - 2, 'cool0', base=row(Z))
        self.rect(268, roof - 14, 297, roof - 13, 'cool0', base=row(Z))
        self.rect(268, roof - 8, 297, roof - 7, 'cool0', base=row(Z))
        # storeys: floor bands, window recesses; a stairwell column with a dim landing light
        floor_rows = [int(yh(3.1 * k, Z)) for k in range(1, 6)]
        for fr in floor_rows:
            self.rect(150, fr, 380, fr + 1, 'cool1', base=row(Z))
        wins = [(229, 1), (246, 1), (262, 1), (291, 1), (305, 1), (233, 2), (257, 2), (284, 2), (300, 2),
                (238, 3), (252, 3), (273, 3), (297, 3), (228, 4), (264, 4), (289, 4), (309, 4)]
        lit_a = {(257, 2), (289, 4), (238, 3)}
        lit_b = {(289, 4)}
        lit = lit_a if a else lit_b
        for (wx, fl) in wins:
            y1 = int(yh(3.1 * fl + 0.7, Z)); y0 = int(yh(3.1 * fl + 2.1, Z))
            ww = 9 + int(hsh(wx, fl) * 4)
            self.rect(wx, y0, wx + ww, y1, 'void', base=row(Z))
            if (wx, fl) in lit:
                self.rect(wx + 1, y0 + 1, wx + ww - 1, y1, 'win1', base=row(Z))
                self.rect(wx + 1, y0 + 1, wx + ww - 1, y0 + 3, 'win2', base=row(Z))
                self.light(wx + ww / 2, (y0 + y1) / 2, 7, (1.0, 0.78, 0.5), 0.18)
            else:
                self.rect(wx + 1, y1 - 2, wx + ww - 1, y1, 'cool1', base=row(Z))  # sill catches the glow
        self.rect(276, 40, 281, int(yh(3.1, Z)), 'cool1', base=row(Z))            # stairwell
        self.rect(277, int(yh(6.6, Z)), 280, int(yh(6.0, Z)), 'win0', base=row(Z))
        # its ground floor: a closed far shop with one lit display, a dark doorway
        gy0 = int(yh(2.8, Z))
        self.rect(226, gy0, 318, int(G.FARWALL_ROW) + 1, 'cool1', base=row(Z))
        self.rect(252, gy0 + 4, 279, int(G.FARWALL_ROW) - 1, 'win0', base=row(Z))
        self.rect(252, gy0 + 4, 279, gy0 + 8, 'win1', base=row(Z))
        self.rect(284, gy0 + 6, 292, int(G.FARWALL_ROW), 'void', base=row(Z))
        self.light(265, 172, (16, 7), (1.0, 0.75, 0.45), 0.3)
        self.spill([(252, 183), (280, 183), (286, 188), (246, 188)], 0.3, blur=1.2)

    def cross_street_wires(self):
        Zt = G.Z_TRAM
        yw = int(round(yh(5.5, Zt)))
        self.rect(200, yw, 340, yw + 1, 'cool2', base=row(Zt))                   # tram contact wire
        self.NOREF[yw, 200:340] = True
        self.wire(200, yw - 7, 340, yw - 6, 2, 'plum')                            # messenger wire
        # the signal: a pole at the far right corner, a three-lamp head over the cross street
        px_, base = int(col(3.0, 34)), row(34)
        self.rect(px_, int(yh(5.4, 34)), px_ + 1, int(base), 'cool1', base=base)
        hy = int(yh(5.0, 34))
        self.rect(296, hy, px_, hy + 1, 'cool1', base=base)
        self.rect(296, hy + 1, 306, hy + 5, 'cool0', base=base)
        if self.ph == 'a':
            self.rect(303, hy + 2, 305, hy + 4, 'neo1', base=base)               # green
            self.light(304, hy + 3, 5, (0.4, 1.0, 0.8), 0.25)
        else:
            self.rect(300, hy + 2, 302, hy + 4, 'win3', base=base)               # amber blink
            self.light(301, hy + 3, 5, (1.0, 0.75, 0.3), 0.25)

    def tram(self):
        """the lit tram on the cross street, moving left: a long box with a window strip, a
        pantograph diamond to the contact wire, its rear end inside the opening"""
        Zt = G.Z_TRAM
        rear = 236 - int(2.7 * (self.t - 40))
        L = 172
        x0, x1 = rear, rear + L
        r_wheel, r_skirt, r_band = row(Zt), yh(0.35, Zt), yh(1.2, Zt)
        r_win0, r_win1 = yh(1.3, Zt), yh(2.35, Zt)
        r_head, r_roof = yh(2.85, Zt), yh(3.15, Zt)
        base = row(Zt)
        Y = lambda v: int(round(v))
        # body: skirt teal, cream band, window strip, teal header, cool roof with a rounded rear
        self.rect(x0, Y(r_roof), x1, Y(r_wheel) - 1, 'awa0', base=base)
        self.rect(x0, Y(r_band), x1, Y(r_skirt), 'awa1', base=base)
        self.rect(x0, Y(r_win0), x1, Y(r_band) + 1, 'con3', base=base)
        self.rect(x0, Y(r_win1), x1, Y(r_win0), 'con2', base=base)
        self.rect(x0, Y(r_head), x1, Y(r_win1), 'awa1', base=base)
        self.rect(x0 + 2, Y(r_roof), x1 - 2, Y(r_head), 'cool2', base=base)
        self.rect(x0 + 1, Y(r_roof) + 1, x0 + 2, Y(r_head), 'cool2', base=base)
        self.px(x0, Y(r_roof), 'void'); self.px(x0, Y(r_roof) + 1, 'void')
        # bogies and wheels: dark under the skirt, two wheel humps per bogie
        self.rect(x0 + 2, Y(r_skirt), x1 - 2, Y(r_wheel), 'void', base=base)
        for bx in (x0 + 18, x0 + 30, x1 - 34, x1 - 22):
            self.rect(bx, Y(r_skirt) + 1, bx + 7, Y(r_wheel), 'cool1', base=base)
            self.rect(bx + 2, Y(r_wheel) - 1, bx + 5, Y(r_wheel), 'cool2', base=base)
        # rear: a dim tail light and a vertical grab rail
        self.rect(x0 + 1, Y(r_band) + 1, x0 + 3, Y(r_band) + 3, 'lan0', base=base)
        self.rect(x0 + 1, Y(r_win1), x0 + 2, Y(r_band), 'con3', base=base)
        # the window strip: mismatched cells (doors are narrower, pillars vary)
        widths = [9, 10, 6, 10, 11, 10, 6, 10, 9, 10, 11]
        pillars = [3, 3, 2, 3, 4, 3, 2, 3, 3, 4, 3]
        x = x0 + 5
        k = 0
        y0, y1 = Y(r_win1) + 1, Y(r_win0)
        while x < x1 - 6 and k < len(widths):
            w = widths[k]
            door = w < 8
            self.rect(x, y0, x + w, y1 + (4 if door else 0), 'win2', base=base)
            self.rect(x, y0, x + w, y0 + 2, 'win3', base=base)                    # ceiling light row
            if door:
                self.rect(x + w // 2, y0 + 2, x + w // 2 + 1, y1 + 4, 'win1', base=base)
            else:
                for hx in range(x + 2, x + w - 1, 4):                                # hand straps
                    self.px(hx, y0 + 3, 'win1', base)
                if hsh(k, 7) < 0.45:                                                 # a passenger
                    sx = x + 2 + int(hsh(k, 8) * (w - 6))
                    self.rect(sx, y1 - 5, sx + 3, y1, 'win0', base=base)
                    self.rect(sx + 1, y1 - 7, sx + 3, y1 - 5, 'win0', base=base)
            if x + w // 2 > G.X_OPEN0 and x + w // 2 < G.X_OPEN1:
                self.cols.append(dict(x0=max(x, int(G.X_OPEN0)), x1=min(x + w, int(G.X_OPEN1)),
                                      y=(y0 + y1) / 2, b=base, slots=('win0', 'win1', 'win2'), p=0.5, reach=270))
            x += w + pillars[k]
            k += 1
        # destination board on the header (invented glyphs)
        self.rect(x0 + 6, Y(r_head) + 1, x0 + 26, Y(r_win1) - 1, 'win1', base=base)
        for gi in range(3):
            g = rune(gi * 13 + 5, 3, 3, 3, fill=(0.4, 0.8))
            self.stamp(g, x0 + 8 + gi * 6, Y(r_head) + 2, 'win0', base)
        # pantograph: a diamond from the roof to the contact wire
        pxc = rear + 66
        top = int(round(yh(5.5, Zt))) + 1
        rr = Y(r_roof)
        mid = (top + rr) // 2
        self.c.line(pxc - 6, rr - 1, pxc, mid, 'cool3')
        self.c.line(pxc, mid, pxc - 4, top + 1, 'cool3')
        self.c.line(pxc + 5, rr - 1, pxc, mid, 'cool3')
        self.rect(pxc - 7, top, pxc + 3, top + 1, 'cool4', base=base)
        self.rect(pxc - 7, rr - 1, pxc + 6, rr, 'cool2', base=base)
        for yy_ in range(top, rr):
            for xx_ in range(pxc - 8, pxc + 7):
                if self.g[yy_, xx_] in ('cool2', 'cool3', 'cool4'):
                    self.B[yy_, xx_] = base
        self.light(272, 163, (44, 9), (1.0, 0.78, 0.48), 0.75)
        self.light(272, 186, (52, 5), (1.0, 0.74, 0.45), 0.5)

    # ------------------------------------------------------------ the ground
    def ground(self):
        a = self.ph == 'a'
        yy, xx = self.yy + 0.5, self.xx + 0.5
        below = yy > G.FARWALL_ROW
        d = np.maximum(yy - G.HZ, 1e-3)
        Zr = G.F * G.CAM_H / d
        Xr = (xx - G.VPX) * Zr / G.F
        Zp = G.F * (G.CAM_H - 0.12) / d
        Xp = (xx - G.VPX) * Zp / G.F
        far_pav = (Zp > G.Z_FARWALL - 1.5) & (Zp < G.Z_FARWALL + 2)
        pav_L = (Xp < G.X_CURB_L) & (Zp > G.Z_LCURB) & (Zp < G.Z_FAR)
        pav_R = (Xp > G.X_CURB_R) & (Zp < G.Z_FAR)
        pav = below & (pav_L | pav_R | far_pav)
        road_side = (Xr >= G.X_CURB_L) | (Zr < G.Z_LCURB)
        road = below & ~pav & road_side & (Xr <= G.X_CURB_R)
        cross = below & ~pav & (Zr >= G.Z_FAR) & ~road
        road |= cross
        curb = below & ~pav & ~road
        # road: wet asphalt, a darker gutter by each curb, short sheen dashes longer near the viewer
        self.g[road] = 'rd0'
        gut = road & ((np.abs(Xr - G.X_CURB_R) < 0.35) | ((np.abs(Xr - G.X_CURB_L) < 0.3) & (Zr > G.Z_LCURB)))
        self.g[gut] = 'void'
        self.GR[road] = 1
        for j in range(160):
            y = 188 + int(hsh(j, 1) ** 0.8 * 81)
            ln = 2 + int((y - 186) / 9 * (0.5 + hsh(j, 2)))
            x = int(hsh(j, 3) * W)
            for i in range(ln):
                if 0 <= x + i < W and road[y, x + i] and self.g[y, x + i] == 'rd0':
                    self.g[y, x + i] = 'rd1' if hsh(j, 4) < 0.75 else 'rd2'
        # stop line before the cross street, faded and broken
        sl = road & (np.abs(Zr - 30.5) < 0.22) & (Xr > -2.6) & (Xr < 1.8)
        brk = (self.xx % 9 < 2) & (hsh(3, 3) < 2)
        self.g[sl & ~brk] = 'con2'
        # tram rails on the cross street
        for zr in (35.0, 36.2):
            m = cross & (np.abs(Zr - zr) < 0.25)
            self.g[m] = 'rd2'
        # pavements: slabs as paired cells (a lit cap row under each joint, a dark seam)
        self.g[pav] = 'con1'
        self.GR[pav] = 2
        sx, sz = 0.62, 0.9
        cu = np.floor(Xp / sx); cz = np.floor(Zp / sz)
        near = Zp < 13.4
        seam_z = pav & near & (cz != np.roll(cz, 1, axis=0))
        seam_u = pav & (Zp < 24) & (cu != np.roll(cu, 1, axis=1))
        tone = np.where(((cu * 7 + cz * 13) % 5) == 0, 'con2', 'con1')
        self.g[pav] = tone[pav]
        cap = pav & near & np.roll(seam_z, 1, axis=0) & ~seam_z
        self.g[cap] = 'con2'
        self.g[seam_z | seam_u] = 'con0'
        # a patched slab on the right pavement
        patch = pav & (np.abs(Xp - 3.0) < 0.3) & (np.abs(Zp - 9.4) < 0.45)
        self.g[patch] = 'con2'
        # curb faces dark with a lit cap above each
        self.g[curb] = 'con0'
        capc = np.roll(curb, -1, axis=0) & pav & ~curb
        self.g[capc] = 'con3'
        self.GR[curb] = 0
        self.road, self.pav, self.curb = road, pav, curb
        self.Zr, self.Xr = Zr, Xr
        # the puddle: hand-shaped, in the gutter by the right curb, wider toward the viewer
        pts = [(282, 232), (301, 230), (326, 231), (349, 233), (372, 232), (396, 234), (419, 237),
               (438, 241), (451, 247), (461, 255), (457, 262), (439, 268), (402, 270), (350, 270),
               (306, 269), (268, 266), (247, 261), (244, 254), (253, 247), (262, 242), (270, 236)]
        pud = self.c.mask_poly(pts) & (road | pav | curb)
        self.pud_curb = pud & curb
        self.pud = pud
        self.g[pud] = 'void'
        self.GR[pud] = 3
        # the vent / manhole grate in the road (B steams from it)
        vx, vy = 214, 228
        self.rect(vx, vy, vx + 13, vy + 3, 'cool0')
        for i in range(vx + 1, vx + 12, 2):
            self.px(i, vy + 1, 'cool2')
        self.rect(vx, vy - 1, vx + 13, vy, 'cool1')
        self.GR[vy - 1:vy + 3, vx:vx + 13] = 0
        self.vent = (vx + 6, vy)

    # ------------------------------------------------------------ the left street wall
    def left_wall(self):
        a = self.ph == 'a'
        X = G.X_L
        Zs = [(15.4, 19.0), (19.0, 23.5), (23.5, 27.6), (27.6, 33.0)]
        mats = ['con1', 'con0', 'con1', 'cool1']
        for (z0, z1), m in zip(Zs, mats):
            self.wall(X, z0, z1, 0.0, 20.0, m)
            self.wall(X, z0, z1, 3.1, 3.3, 'con2' if m != 'cool1' else 'cool2')     # cornice band
            self.wall(X, z0, z0 + 0.25, 0.0, 20.0, 'plum')                          # party wall seam
        # L1: a narrow lit shop under a teal awning (sagging lip)
        self.wall(X, 15.9, 18.3, 0.0, 2.5, 'win0')
        self.wall(X, 16.0, 18.2, 0.9, 2.3, 'win1')
        self.wall(X, 16.0, 18.2, 2.0, 2.3, 'win2')
        self.wall(X, 16.9, 17.2, 0.0, 2.5, 'con0')
        self.awning_L(15.7, 18.6, 2.55, 0.95, 'awa', sag=1)
        self.light(col(X + 0.6, 17), yh(1.4, 17), (8, 10), (1.0, 0.75, 0.45), 0.55)
        self.gspill(X, 15.9, 18.3, 1.6, 0.32)
        self.cols.append(dict(x0=int(col(X, 16.2)), x1=int(col(X, 18.0)), y=yh(1.6, 17), b=row(17),
                              slots=('win0', 'win0'), p=0.22, reach=240))
        # L2: shutter down (mismatched slats), a lit upper window in A
        self.wall(X, 19.4, 23.0, 0.0, 2.6, 'cool2')
        for k, yv in enumerate((0.25, 0.55, 0.8, 1.15, 1.4, 1.75, 2.0, 2.35)):
            self.wall(X, 19.4, 23.0, yv, yv + 0.07, 'cool1')
        self.wall(X, 19.4, 23.0, 2.6, 2.8, 'cool0')
        self.wall(X, 20.0, 21.6, 4.2, 5.6, 'void')
        if a:
            self.wall(X, 20.1, 21.5, 4.3, 5.5, 'win0')
            self.wall(X, 20.1, 21.5, 5.2, 5.5, 'win1')
            self.light(col(X, 20.8), yh(4.9, 20.8), 6, (1.0, 0.75, 0.45), 0.25)
        self.wall(X, 21.9, 22.8, 4.4, 5.4, 'void')
        self.wall(X, 21.9, 22.8, 3.5, 4.0, 'cool2')                               # AC unit
        # L3: a tiny eatery, noren in the door, maroon awning
        self.wall(X, 23.9, 27.0, 0.0, 2.4, 'win0')
        self.wall(X, 24.1, 26.8, 1.0, 2.2, 'win1')
        self.wall(X, 25.2, 26.2, 1.3, 2.3, 'awh1')                                # noren
        self.awning_L(23.7, 27.2, 2.5, 0.8, 'awb', sag=0)
        self.light(col(X + 0.5, 25.5), yh(1.4, 25.5), (7, 8), (1.0, 0.75, 0.45), 0.45)
        self.gspill(X, 23.9, 27.0, 1.5, 0.28)
        self.cols.append(dict(x0=int(col(X, 24.2)), x1=int(col(X, 26.6)), y=yh(1.6, 25.5), b=row(25.5),
                              slots=('win0', 'win0'), p=0.2, reach=230))
        # L4: the corner at the cross street: a dim vending machine glow, dark above
        self.wall(X, 29.0, 30.6, 0.0, 1.8, 'cool3')
        self.wall(X, 29.15, 30.45, 0.4, 1.6, 'neo0')
        self.light(col(X + 0.4, 29.8), yh(1.0, 29.8), 5, (0.6, 0.9, 1.0), 0.25)
        for (z0, z1, y0, y1) in ((16.2, 17.6, 4.6, 6.2), (16.0, 17.8, 7.6, 9.2), (24.4, 25.9, 4.0, 5.4),
                                  (24.2, 26.0, 6.8, 8.2), (28.4, 29.8, 3.9, 5.1), (31.0, 32.4, 4.1, 5.3)):
            self.wall(X, z0, z1, y0, y1, 'void')
        if a:
            self.wall(X, 24.5, 25.8, 6.9, 8.1, 'win0')
        # projecting signs (perpendicular to the wall, face-on): mismatched depths and sizes
        self.vsign(X, 18.3, 0.62, 3.2, 6.6, panel='con0', ink='win1', seed=11, lit=True, askew=0)
        self.vsign(X, 22.2, 0.7, 2.9, 5.0, panel='win1', ink='plum', seed=23, lit=True, askew=0)
        self.vsign(X, 26.6, 0.55, 3.0, 4.5, panel='con3', ink='con0', seed=31, lit=False, askew=1)

    def awning_L(self, z0, z1, ytop, depth, ramp, sag=0):
        """an awning on the left wall: from the wall at ytop out `depth` m, dropping 0.35 m; we see
        its underside (dark) and its valance strip (the lit lip)"""
        X = G.X_L
        Xo = X + depth
        yl = ytop - 0.35
        und = [P(X, ytop, z0), P(X, ytop, z1), P(Xo, yl, z1), P(Xo, yl, z0)]
        self.poly(und, ramp + '0', wallX=None, base=None)
        m = self.c.mask_poly(und)
        xs = self.xx[m] + 0.5
        # base: the ground under the awning lip (approximately the lip's own depth per column)
        Zc = G.F * Xo / (xs - G.VPX)
        self.B[m] = G.HZ + G.F * G.CAM_H / np.clip(Zc, z0, z1)
        val = [P(Xo, yl, z0), P(Xo, yl, z1), P(Xo, yl - 0.18, z1), P(Xo, yl - 0.18 - 0.05 * sag, z0)]
        mv = self.poly(val, ramp + '1', wallX=Xo)
        self.awnings.append(dict(side='L', X=Xo, z0=z0, z1=z1, y=yl - 0.18, mask=mv))

    def vsign(self, X, Z, d, y0, y1, panel, ink, seed, lit, askew=0, right=False):
        """a vertical sign projecting from the wall at X, face-on at depth Z: invented glyphs"""
        s = 1 if right else -1
        xa, xb = col(X, Z), col(X - s * d * (-1 if right else 1) * (-1), Z)
        xa, xb = col(X, Z), col(X + (d if not right else -d), Z)
        x0, x1 = int(round(min(xa, xb))), int(round(max(xa, xb)))
        r0, r1 = int(round(yh(y1, Z))), int(round(yh(y0, Z)))
        base = row(Z)
        self.rect(x0, r0, x1, r1, 'plum', base=base)
        self.rect(x0 + 1, r0 + 1, x1 - 1, r1 - 1, panel, base=base)
        if askew:
            self.rect(x1 - 1, r0 + 1, x1, r0 + 3, 'plum', base=base)
        gw = max(3, min(7, x1 - x0 - 4))
        gw -= (gw + 1) % 2                      # odd widths mirror about a centre column
        gh = gw + 1
        gy = r0 + 3
        k = 0
        seen = set()
        while gy + gh <= r1 - 3:
            for rr in range(30):                       # no rune twice on one sign
                g = rune(seed * 7 + k + rr * 101, gw, gh, (seed + rr // 6) % 5)
                if g.tobytes() not in seen:
                    break
            seen.add(g.tobytes())
            self.stamp(g, x0 + (x1 - x0 - gw) // 2, gy, ink, base)
            gy += gh + 2 + (k % 2)
            k += 1
        # bracket to the wall
        self.rect(min(x1, int(col(X, Z))) - 1, r0 - 2, max(x1, int(col(X, Z))), r0 - 1, 'cool1', base=base)
        if lit:
            self.light((x0 + x1) / 2, (r0 + r1) / 2, (max(4, (x1 - x0) * 0.6), (r1 - r0) * 0.5),
                       (1.0, 0.8, 0.55), 0.22)
        return (x0, r0, x1, r1)

    # ------------------------------------------------------------ the right street wall
    def right_wall(self):
        a = self.ph == 'a'
        X = G.X_R
        segs = [(17.6, 21.6, 'con1'), (21.6, 27.0, 'brk0'), (27.0, 33.0, 'con0')]
        for z0, z1, m in segs:
            self.wall(X, z0, z1, 0.0, 22.0, m)
            self.wall(X, z0, z1, 3.0, 3.25, 'con2' if m != 'brk0' else 'brk1')
            self.wall(X, z1 - 0.25, z1, 0.0, 22.0, 'plum')
        # R3 next to the hero: a narrow shop with a lit display and a hanging lamp
        self.wall(X, 18.0, 21.2, 0.0, 2.5, 'cool0')
        self.wall(X, 18.3, 20.9, 0.7, 2.2, 'win0')
        self.wall(X, 18.4, 20.8, 1.7, 2.2, 'win1')
        self.light(col(X - 0.5, 19.6), yh(1.5, 19.6), (6, 9), (1.0, 0.75, 0.45), 0.4)
        self.gspill(X, 18.3, 20.9, 1.4, 0.3)
        self.cols.append(dict(x0=int(col(X, 20.8)), x1=int(col(X, 18.4)), y=yh(1.5, 19.6), b=row(19.6),
                              slots=('win0', 'win0'), p=0.22, reach=240))
        # R2: maroon awning over a shop, shutter half down in B
        self.wall(X, 22.0, 26.6, 0.0, 2.6, 'win0' if a else 'cool1')
        if a:
            self.wall(X, 22.2, 26.4, 1.0, 2.3, 'win1')
            self.light(col(X - 0.5, 24.3), yh(1.4, 24.3), (6, 8), (1.0, 0.75, 0.45), 0.4)
            self.gspill(X, 22.2, 26.4, 1.3, 0.26)
            self.cols.append(dict(x0=int(col(X, 26.2)), x1=int(col(X, 22.4)), y=yh(1.5, 24.3), b=row(24.3),
                                  slots=('win0', 'win0'), p=0.18, reach=230))
        self.awning_R(21.8, 26.8, 2.6, 0.7, 'awb')
        # R1: the corner at the cross street, shuttered
        self.wall(X, 27.4, 32.6, 0.0, 2.5, 'cool2')
        for yv in (0.3, 0.7, 1.0, 1.45, 1.8, 2.2):
            self.wall(X, 27.4, 32.6, yv, yv + 0.08, 'cool1')
        # upper windows (few lit), an AC unit
        for (z0, z1, y0, y1) in ((18.4, 19.8, 4.2, 5.7), (22.6, 24.0, 4.0, 5.4), (25.0, 26.2, 4.0, 5.4),
                                  (28.2, 29.6, 3.9, 5.2), (30.6, 32.0, 4.0, 5.3), (22.4, 24.2, 6.8, 8.2)):
            self.wall(X, z0, z1, y0, y1, 'void')
        if a:
            self.wall(X, 25.1, 26.1, 4.1, 5.3, 'win0')
        self.wall(X, 28.4, 29.4, 3.4, 3.8, 'cool2')
        # projecting signs: the tall maroon one beside the hero (dim), a pale unlit one, a small box
        self.vsign(X, 18.8, 0.8, 3.7, 7.4, panel='awb0', ink='win0', seed=41, lit=True, right=True)
        self.vsign(X, 25.0, 0.6, 3.0, 5.0, panel='con3', ink='con0', seed=53, lit=False, right=True)
        self.vsign(X, 30.4, 0.5, 2.9, 3.9, panel='neo0', ink='neo1', seed=67, lit=True, right=True)

    def awning_R(self, z0, z1, ytop, depth, ramp):
        X = G.X_R
        Xo = X - depth
        yl = ytop - 0.32
        und = [P(X, ytop, z0), P(X, ytop, z1), P(Xo, yl, z1), P(Xo, yl, z0)]
        m = self.c.mask_poly(und)
        self.g[m] = ramp + '0'
        xs = self.xx[m] + 0.5
        Zc = G.F * Xo / (xs - G.VPX)
        self.B[m] = G.HZ + G.F * G.CAM_H / np.clip(Zc, z0, z1)
        val = [P(Xo, yl, z0), P(Xo, yl, z1), P(Xo, yl - 0.17, z1), P(Xo, yl - 0.17, z0)]
        mv = self.poly(val, ramp + '1', wallX=Xo)
        self.awnings.append(dict(side='R', X=Xo, z0=z0, z1=z1, y=yl - 0.17, mask=mv))

    def tree(self):
        """the street tree on the right pavement: a clumped canopy, lit from below by the shops"""
        Zt, Xt = 22.5, 2.55
        tx, base = int(round(col(Xt, Zt))), row(Zt)
        self.rect(tx, int(yh(3.2, Zt)), tx + 2, int(base) + 1, 'brk0', base=base)
        self.px(tx + 1, int(yh(1.4, Zt)), 'brk1', base)
        lobes = [(-14, -64, 12), (2, -71, 10), (13, -60, 11), (-3, -52, 13), (-17, -47, 8), (11, -45, 9),
                 (-8, -78, 7), (6, -84, 6)]
        cy0 = base
        m_all = np.zeros((H, W), bool)
        for i, (dx, dy, r) in enumerate(lobes):
            cx, cy = tx + dx, cy0 + dy
            m = ((self.xx + 0.5 - cx) ** 2 + ((self.yy + 0.5 - cy) * 1.15) ** 2) <= r * r
            self.g[m] = 'pl0'
            up = m & (((self.xx + 0.5 - cx + 3) ** 2 + ((self.yy + 0.5 - cy + 4) * 1.15) ** 2) > (r - 1) ** 2) \
                & (self.yy + 0.5 < cy - r * 0.3)
            self.g[up] = 'pl1'
            m_all |= m
        # holes and a ragged rim so it is not a ball
        for j in range(30):
            hx = tx - 26 + int(hsh(j, 41) * 46)
            hy = int(cy0 - 92 + hsh(j, 43) * 56)
            if m_all[hy, hx] and hsh(j, 47) < 0.6:
                self.g[hy, hx] = 'plum'
                if hy + 1 < H:
                    self.g[hy + 1, hx] = 'plum'
        under = m_all & (self.yy + 0.5 > cy0 - 52)
        self.g[under & ((self.xx + self.yy) % 2 == 0)] = 'pl0'
        self.B[m_all] = base
        self.NOREF[m_all] = False

    # ------------------------------------------------------------ the left corner block (faces us)
    def corner_block(self):
        a = self.ph == 'a'
        Z = G.Z_LC
        x0w, x1w = G.X_LC0 - 2.0, G.X_L
        self.front(Z, x0w, x1w, 0.0, 20.0, 'con1')
        self.front(Z, x0w, x1w, 3.25, 3.45, 'con2')
        self.front(Z, x0w, x1w, 6.35, 6.5, 'con2')
        self.front(Z, x1w - 0.12, x1w, 0.0, 20.0, 'con0')                            # corner edge
        # ground floor shop: shutter up in A (interior lit), half down in B (a warm strip under it)
        sx0, sx1 = -8.2, -5.9
        self.front(Z, sx0, sx1, 0.0, 2.6, 'con0')
        self.front(Z, sx0 + 0.1, sx1 - 0.1, 0.0, 2.35, 'win0')
        self.front(Z, sx0 + 0.1, sx1 - 0.1, 2.15, 2.35, 'win1')                     # tube light
        for k, yv in enumerate((1.2, 1.75)):                                        # shelves
            self.front(Z, sx0 + 0.15, sx1 - 0.15, yv, yv + 0.06, 'brk1')
        for k in range(9):                                                          # goods on shelves
            xg = sx0 + 0.25 + k * 0.24 + hsh(k, 5) * 0.06
            hg = 0.12 + hsh(k, 6) * 0.18
            yb = 1.26 if k % 2 else 1.81
            self.front(Z, xg, xg + 0.12, yb, yb + hg, 'win1' if k % 3 == 0 else 'brk2')
        self.front(Z, sx0 + 0.1, sx1 - 0.1, 0.0, 0.85, 'brk0')                      # counter
        self.front(Z, sx0 + 0.1, sx1 - 0.1, 0.8, 0.85, 'brk2')
        self.front(Z, sx0, sx1, 2.6, 2.85, 'cool1')                                 # shutter box
        if a:
            self.light(col((sx0 + sx1) / 2, Z), yh(1.4, Z), (22, 12), (1.0, 0.74, 0.45), 0.4)
            self.spill([(64, 207), (122, 207), (136, 238), (50, 238)], 0.36)
            self.cols.append(dict(x0=int(col(sx0, Z)) + 2, x1=int(col(sx1, Z)) - 2, y=yh(1.6, Z), b=row(Z),
                                  slots=('win0', 'win1'), p=0.26, reach=262))
        else:
            self.front(Z, sx0, sx1, 1.0, 2.6, 'cool2')                              # half-down shutter
            for k, yv in enumerate((1.12, 1.33, 1.5, 1.74, 1.92, 2.18, 2.37)):
                self.front(Z, sx0, sx1, yv, yv + 0.05, 'cool1')
            self.front(Z, sx0, sx1, 0.96, 1.02, 'cool3')
            self.light(col((sx0 + sx1) / 2, Z), yh(0.6, Z), (24, 8), (1.0, 0.72, 0.42), 0.45)
            self.spill([(64, 207), (122, 207), (130, 228), (56, 228)], 0.3)
            self.cols.append(dict(x0=int(col(sx0, Z)) + 2, x1=int(col(sx1, Z)) - 2, y=yh(0.5, Z), b=row(Z),
                                  slots=('win0',), p=0.35, reach=260))
        # the door (dim) and a standing poster board
        self.front(Z, -5.6, -5.0, 0.0, 2.2, 'cool0')
        self.front(Z, -5.52, -5.08, 0.1, 2.05, 'awh0')
        self.front(Z, -5.15, -5.11, 0.9, 1.1, 'cool3')
        self.front(Z, -4.9, -4.38, 0.15, 1.9, 'con3')
        for k in range(3):
            g = rune(90 + k, 5, 5, 2)
            self.stamp(g, int(col(-4.84, Z)) + 3, int(yh(1.75, Z)) + k * 8, 'con0', row(Z))
        self.front(Z, -4.9, -4.38, 0.0, 0.15, 'con0')
        # the billboard over the shop: unlit, glyph rows, lit only by the street lamp
        self.front(Z, -8.35, -5.75, 2.9, 3.2, 'con0')
        self.front(Z, -8.3, -5.8, 2.93, 3.17, 'ps0')
        for k in range(6):
            g = rune(120 + k, 5, 5, 1)
            self.stamp(g, int(col(-8.15, Z)) + k * 9 + (k % 2), int(yh(3.13, Z)) + 1, 'con0', row(Z))
        # the teal neon box sign (a cool accent), an invented mark
        bx0, bx1, by0, by1 = int(col(-8.42, Z)), int(col(-7.3, Z)), int(yh(5.0, Z)), int(yh(4.1, Z))
        self.rect(bx0, by0, bx1, by1, 'plum', base=row(Z))
        self.rect(bx0 + 1, by0 + 1, bx1 - 1, by1 - 1, 'neo0', base=row(Z))
        self.rect(bx0 + 2, by0 + 2, bx1 - 2, by0 + 3, 'neo1', base=row(Z))
        mark = rune(61, 9, 9, 4)
        self.stamp(mark, (bx0 + bx1) // 2 - 4, by0 + 5, 'neo1', row(Z))
        self.rect(bx1, by0 + 3, bx1 + 3, by0 + 4, 'cool1', base=row(Z))
        self.light((bx0 + bx1) / 2, (by0 + by1) / 2, (14, 10), (0.5, 0.9, 1.0), 0.32)
        # upper windows: the laundry window (lit in A), a small dark one, a blind
        wx0, wx1, wy0, wy1 = -7.75, -7.1, 4.2, 5.3
        self.front(Z, wx0 - 0.08, wx1 + 0.08, wy0 - 0.12, wy1 + 0.06, 'con2')
        self.front(Z, wx0, wx1, wy0, wy1, 'win0' if a else 'void')
        if a:
            self.front(Z, wx0 + 0.04, wx0 + 0.2, wy0, wy1, 'awb0')                  # curtain
            self.light(col(-7.4, Z), yh(4.8, Z), (9, 8), (1.0, 0.75, 0.45), 0.22)
        self.front(Z, wx0 - 0.15, wx1 + 0.15, wy0 - 0.2, wy0 - 0.12, 'con0')       # sill
        self.laundry(Z, wx1, wy1)
        self.front(Z, -6.2, -5.7, 4.2, 5.4, 'void')
        self.front(Z, -5.1, -4.5, 3.9, 5.6, 'cool1')
        for k in range(6):
            yv = 4.0 + k * 0.27
            self.front(Z, -5.05, -4.55, yv, yv + 0.05, 'cool0')
        self.front(Z, -8.0, -6.6, 7.0, 8.6, 'void')
        self.front(Z, -7.9, -6.7, 6.6, 6.95, 'cool2')                              # AC unit
        self.front(Z, -5.6, -4.7, 7.2, 8.6, 'void')
        self.front(Z, -4.42, -4.33, 0.0, 20.0, 'cool1')                             # downpipe

    def laundry(self, Z, wx1, wy1):
        """a pole out of the window with a shirt and a towel; in A an arm pulls them in"""
        a = self.ph == 'a'
        base = row(Z)
        px0, py = int(col(wx1, Z)), int(yh(wy1 - 0.1, Z))
        pole_end = px0 + 21
        self.rect(px0 - 1, py, pole_end, py + 1, 'cool3', base=base)
        self.px(pole_end - 1, py - 1, 'cool3', base)
        if a:
            # a pale shirt (shoulders, sleeves) and a darker towel hang under the pole; an arm reaches out
            shirt = parse("""
#########
#########
###...###
##.....##
.#######.
.#######.
.#######.
.#######.""")
            self.stamp(shirt, px0 + 1, py + 1, 'clw', base)
            self.rect(px0 + 3, py + 6, px0 + 9, py + 9, 'con4', base=base)
            self.rect(px0 + 12, py + 1, px0 + 18, py + 12, 'awh2', base=base)
            self.rect(px0 + 12, py + 11, px0 + 18, py + 12, 'awh0', base=base)
            self.rect(px0 + 14, py + 1, px0 + 15, py + 11, 'awh1', base=base)
            self.rect(px0 - 5, py + 2, px0 + 1, py + 4, 'win1', base=base)      # sleeve
            self.rect(px0 + 1, py + 1, px0 + 3, py + 4, 'con4', base=base)      # hand on the shirt
            self.light(px0 + 9, py + 6, (10, 8), (1.0, 0.8, 0.55), 0.35)
        else:
            self.px(px0 + 5, py + 1, 'cool2', base); self.px(px0 + 13, py + 1, 'cool2', base)

    # ------------------------------------------------------------ the hero corner shop
    def hero(self):
        a = self.ph == 'a'
        Z, Zb = G.Z_HERO, G.Z_HERO_BACK
        X0, X1 = G.X_R, G.X_HERO1
        # masses: side face (receding) and front face (facing us), brick upper floors
        self.wall(X0, Z, Zb, 0.0, 22.0, 'brk1')
        self.front(Z, X0, X1, 0.0, 22.0, 'brk1')
        self.front(Z, X0, X0 + 0.1, 0.0, 22.0, 'brk2')                              # lit corner edge
        self.front(Z, X0, X1, 3.2, 3.42, 'brk3')                                    # cornice
        self.wall(X0, Z, Zb, 3.2, 3.42, 'brk2')
        # brick courses on the upper front, offset, a few patched bricks
        for k in range(14):
            yv = 3.6 + k * 0.38
            self.front(Z, X0 + 0.1, X1, yv, yv + 0.04, 'brk0')
        # upper windows: one lit behind a curtain in A; the unlit box sign
        self.front(Z, 3.75, 4.95, 3.95, 5.65, 'brk0')
        self.front(Z, 3.82, 4.88, 4.0, 5.6, 'void')
        self.front(Z, 3.82, 4.88, 4.0, 5.6, 'awh0' if a else 'void')
        if a:
            self.front(Z, 4.28, 4.42, 4.0, 5.6, 'win1')                              # light between curtains
            self.front(Z, 3.82, 4.88, 4.0, 4.12, 'win0')
            self.light(col(4.35, Z), yh(4.8, Z), (8, 10), (1.0, 0.75, 0.45), 0.18)
        self.front(Z, 3.7, 5.0, 3.85, 3.95, 'brk3')                                 # sill
        bs = (5.2, 6.15, 4.4, 6.4)
        self.front(Z, bs[0], bs[1], bs[2], bs[3], 'plum')
        self.front(Z, bs[0] + 0.05, bs[1] - 0.05, bs[2] + 0.05, bs[3] - 0.05, 'awh1')
        cx, cy = col((bs[0] + bs[1]) / 2, Z), yh((bs[2] + bs[3]) / 2, Z)
        ring = ((self.xx + 0.5 - cx) ** 2 + (self.yy + 0.5 - cy) ** 2)
        self.put((ring < 9.5 ** 2) & (ring > 7.6 ** 2), 'awh2', base=row(Z))
        self.put((np.abs(self.xx + 0.5 - cx - 1) < 1.1) & (np.abs(self.yy + 0.5 - cy) < 5), 'awh2', base=row(Z))
        self.front(Z, 5.3, 5.9, 3.55, 4.05, 'cool2')                                # AC unit
        self.front(Z, 5.33, 5.87, 3.6, 3.72, 'cool3')
        # the downpipe at the back edge of the side face; in A its joint overflows
        pz = Zb - 0.15
        self.wall(X0, pz - 0.2, pz, 0.0, 22.0, 'cool1')
        # ---- ground floor, front face
        # plinth tiles and the shop window: warm interior with shelves, jars and a counter
        self.front(Z, X0 + 0.1, X1, 0.0, 0.45, 'brk0')
        wX0, wX1 = 3.5, 5.3
        self.front(Z, wX0 - 0.06, wX1 + 0.06, 0.4, 2.45, 'cool1')                  # frame
        self.front(Z, wX0, wX1, 0.45, 2.4, 'win2')
        self.front(Z, wX0, wX1, 2.0, 2.4, 'win3')                                   # ceiling lamp glow
        for yv in (0.95, 1.45):
            self.front(Z, wX0, wX1, yv, yv + 0.05, 'win0')
        for k in range(12):                                                         # jars and bottles
            xg = wX0 + 0.08 + k * 0.145 + hsh(k, 9) * 0.04
            shelf = 1.0 if k % 2 == 0 else 1.5
            hg = 0.16 + hsh(k, 10) * 0.2
            self.front(Z, xg, xg + 0.08 + 0.04 * (k % 3 == 0), shelf, shelf + hg, 'win1' if k % 4 else 'brk2')
        self.front(Z, wX0, wX1, 0.45, 0.7, 'win1')                                  # counter front
        self.front(Z, 4.4, 4.44, 0.45, 2.4, 'cool1')                                # mullion
        # the door: glass with a noren (indigo, a pale invented mark), warm inside
        dX0, dX1 = 5.45, 6.1
        self.front(Z, dX0 - 0.05, dX1 + 0.05, 0.0, 2.45, 'cool1')
        self.front(Z, dX0, dX1, 0.0, 2.4, 'win1')
        self.front(Z, dX0 + 0.06, dX1 - 0.06, 0.12, 1.65, 'win2')
        self.front(Z, dX0 + 0.06, dX1 - 0.06, 0.9, 0.95, 'win1')
        self.front(Z, dX1 - 0.16, dX1 - 0.12, 0.8, 1.15, 'cool1')                   # handle
        self.front(Z, dX0, dX1, 1.7, 2.4, 'awh1')
        self.front(Z, dX0 + 0.3, dX0 + 0.34, 1.7, 2.4, 'awh0')
        nm = rune(77, 5, 5, 4)
        self.stamp(nm, int(col(dX0 + 0.08, Z)) + 1, int(yh(2.2, Z)) + 1, 'win1', row(Z))
        self.front(Z, dX0, dX1, 0.0, 0.08, 'win1')
        # ---- the fascia sign: the frame's peak value; one dead tube in its border
        sX0, sX1, sy0, sy1 = 3.45, 6.15, 2.72, 3.16
        self.front(Z, sX0 - 0.06, sX1 + 0.06, sy0 - 0.05, sy1 + 0.05, 'plum')
        self.front(Z, sX0, sX1, sy0, sy1, 'hs0')
        sxa, sxb = int(round(col(sX0, Z))), int(round(col(sX1, Z)))
        sya, syb = int(round(yh(sy1, Z))), int(round(yh(sy0, Z)))
        self.rect(sxa + 1, sya + 1, sxb - 1, sya + 2, 'hs1', base=row(Z))
        self.rect(sxa + 1, syb - 2, sxb - 1, syb - 1, 'hs1', base=row(Z))
        self.rect(sxa + 9, syb - 2, sxa + 16, syb - 1, 'win3', base=row(Z))         # the dead tube
        gx = sxa + 7
        for i, sd in enumerate((10, 16, 17, 2)):
            gg = rune(sd, 7, 9, 0)
            self.stamp(gg, gx, sya + 2, 'gl0', row(Z))
            gx += 7 + (11 if i != 1 else 14)
        self.sign_box = (sxa, sya, sxb, syb)
        # ---- the awning over the window: indigo with pale stripes converging to the vanishing point
        Za, yt, yl = Z - 0.75, 2.62, 2.25
        aw = [P(3.4, yt, Z), P(6.25, yt, Z), P(6.0, yl, Za), P(3.3, yl, Za)]
        m = self.poly(aw, 'awh1', base=row(Za))
        xs = self.xx + 0.5
        u = (xs - G.VPX) / (col(1, Z) - G.VPX)                  # X at the wall row, per pixel (approx)
        stripe = m & ((np.floor(u * 2.6) % 2) == 0)
        self.g[stripe] = 'awh2'
        lip = [P(3.3, yl, Za), P(6.0, yl, Za), P(6.0, yl - 0.13, Za), P(3.3, yl - 0.13, Za)]
        ml = self.poly(lip, 'awh0', base=row(Za))
        self.awnings.append(dict(side='F', Z=Za, X0=3.3, X1=6.0, y=yl - 0.13, mask=ml))
        # ---- side face ground floor: an open stall under a side awning
        self.wall(X0, Z + 0.15, Zb - 0.4, 0.0, 2.5, 'win0')
        self.wall(X0, Z + 0.2, Zb - 0.5, 0.95, 2.35, 'win1')
        self.wall(X0, Z + 0.2, Zb - 0.5, 1.6, 1.66, 'win0')
        self.wall(X0, Z + 0.15, Zb - 0.4, 0.0, 0.95, 'wd0')                         # counter
        self.wall(X0, Z + 0.15, Zb - 0.4, 0.88, 0.95, 'wd1')
        for k in range(6):                                                          # crates of produce
            z0 = Z + 0.3 + k * 0.55 + hsh(k, 21) * 0.12
            self.wall(X0 - 0.02, z0, z0 + 0.42, 0.95, 1.15 + hsh(k, 22) * 0.08, ('pl1', 'awb1', 'wd1')[k % 3])
        Xo = X0 - 0.75
        und = [P(X0, 2.5, Z + 0.05), P(X0, 2.5, Zb - 0.3), P(Xo, 2.18, Zb - 0.3), P(Xo, 2.18, Z + 0.05)]
        mu = self.c.mask_poly(und)
        self.g[mu] = 'awa0'
        Zc = G.F * Xo / (self.xx[mu] + 0.5 - G.VPX)
        self.B[mu] = G.HZ + G.F * G.CAM_H / np.clip(Zc, Z, Zb)
        val = [P(Xo, 2.18, Z + 0.05), P(Xo, 2.18, Zb - 0.3), P(Xo, 2.02, Zb - 0.3), P(Xo, 2.02, Z + 0.05)]
        mv = self.poly(val, 'awa1', wallX=Xo)
        self.awnings.append(dict(side='R', X=Xo, z0=Z + 0.05, z1=Zb - 0.3, y=2.02, mask=mv))
        # ---- the red paper lantern at the corner: fat oval, dark caps, ribs, a tassel
        lx, ly = 373, 153
        self.rect(lx + 6, int(yh(2.25, Za)), lx + 7, ly, 'plum', base=row(13.0))
        lan = parse("""
....#####....
..#########..
.###########.
#############
#############
#############
#############
#############
#############
#############
.###########.
..#########..
....#####....""")
        h_, w_ = lan.shape
        for j in range(h_):
            for i in range(w_):
                if not lan[j, i]:
                    continue
                edge = (i == 0 or i == w_ - 1 or not lan[j, i - 1] or not lan[j, i + 1] or j in (0, h_ - 1))
                s = 'lan2' if (3 <= i <= 8 and 2 <= j <= 9) else 'lan1'
                if j in (3, 6, 9) and not edge:
                    s = 'lan1'                                                      # ribs
                if edge:
                    s = 'lan0'
                if i >= 10 and not edge:
                    s = 'lan1' if s == 'lan2' else s                                # the shadow side
                self.px(lx + i, ly + j, s, row(13.0))
        self.rect(lx + 3, ly - 1, lx + 10, ly + 1, 'plum', base=row(13.0))          # top cap
        self.rect(lx + 3, ly + h_ - 1, lx + 10, ly + h_ + 1, 'plum', base=row(13.0))  # bottom cap
        self.rect(lx + 5, ly + 5, lx + 7, ly + 7, 'win3', base=row(13.0))           # the flame behind the paper
        self.rect(lx + 6, ly + h_ + 1, lx + 7, ly + h_ + 5, 'lan0', base=row(13.0))  # tassel
        self.px(lx + 5, ly + h_ + 5, 'lan0', row(13.0)); self.px(lx + 7, ly + h_ + 5, 'lan0', row(13.0))
        self.lantern = (lx, ly - 1, lx + w_, ly + h_ + 5)
        # ---- lights: the sign, the window and its spill, the lantern
        self.light((sxa + sxb) / 2, (sya + syb) / 2, (34, 13), (1.0, 0.88, 0.66), 1.15)
        self.light(col(4.5, Z), yh(1.3, Z), (30, 22), (1.0, 0.74, 0.44), 1.0)
        self.light(col(4.6, 11.5), row(11.5), (44, 11), (1.0, 0.72, 0.42), 0.6)
        self.spill([(377, 212), (457, 212), (480, 268), (344, 268)], 0.8, blur=3.0)
        self.gspill(X0, Z + 0.2, Zb - 0.4, 1.3, 0.32)
        self.light(lx + 6.5, ly + 6, 11, (1.0, 0.32, 0.2), 0.6)
        self.light(col(X0 - 0.3, 15.5), yh(1.3, 15.5), (9, 14), (1.0, 0.74, 0.44), 0.5)
        # reflection columns under the hero's lights
        self.cols.append(dict(x0=sxa + 2, x1=sxb - 2, y=(sya + syb) / 2, b=row(Z), slots=('win1', 'win2', 'win3'),
                              p=0.55, reach=270))
        self.cols.append(dict(x0=int(col(wX0, Z)) + 1, x1=int(col(wX1, Z)) - 1, y=yh(1.4, Z), b=row(Z),
                              slots=('win1', 'win2', 'win2'), p=0.6, reach=270))
        self.cols.append(dict(x0=lx + 3, x1=lx + 10, y=ly + 6, b=row(13.0), slots=('lan0', 'lan0', 'win0'),
                              p=0.5, reach=268))

    def glass(self):
        """the near glass building: a sliver receding along X 6.3, teal panes, a warm streak"""
        X = G.X_HERO1
        self.wall(X, 11.0, G.Z_HERO, 0.0, 25.0, 'gls0')
        for z in (12.0, 12.45, 12.95, 13.35):
            self.wall(X, z - 0.06, z, 0.0, 25.0, 'cool1')
        for yv in (3.2, 6.4, 9.6):
            self.wall(X, 11.0, G.Z_HERO, yv, yv + 0.25, 'cool2')
        self.wall(X, 12.05, 12.9, 0.3, 2.9, 'gls1')
        self.wall(X, 12.5, 12.9, 3.6, 6.0, 'gls1')
        self.wall(X, 11.0, G.Z_HERO, 0.0, 0.3, 'cool0')

    # ------------------------------------------------------------ poles and wires
    def poles(self):
        # the sodium street lamp on the left corner
        lx, lb = 138, row(11.0)
        top = int(yh(5.7, 11.0))
        self.rect(lx, top, lx + 2, int(lb) + 1, 'cool1', base=lb)
        self.rect(lx + 1, top, lx + 2, int(lb) + 1, 'cool2', base=lb)
        self.rect(lx - 1, int(lb) - 3, lx + 3, int(lb) + 1, 'cool1', base=lb)
        arm = [(lx + 1, top), (lx + 4, top - 2), (lx + 10, top - 3), (lx + 20, top - 2), (lx + 29, top + 1)]
        for (xa, ya), (xb, yb) in zip(arm[:-1], arm[1:]):
            self.c.line(xa, ya, xb, yb, 'cool1')
        hx, hy = lx + 26, top + 1
        self.rect(hx, hy, hx + 9, hy + 2, 'cool0', base=lb)
        self.rect(hx + 1, hy + 2, hx + 8, hy + 3, 'win4', base=lb)
        self.rect(hx + 2, hy + 3, hx + 7, hy + 4, 'win3', base=lb)
        for yy_ in range(top - 4, hy + 4):
            for xx_ in range(lx, hx + 10):
                if self.g[yy_, xx_] in ('cool0', 'cool1', 'win3', 'win4') and np.isnan(self.B[yy_, xx_]):
                    self.B[yy_, xx_] = lb
        self.lamp = (hx + 4.5, hy + 3)
        self.light(hx + 4.5, hy + 6, (24, 30), (1.0, 0.78, 0.45), 0.85)
        pool = [(128, 223), (140, 217), (158, 214), (176, 213), (196, 215), (211, 219), (221, 225),
                (214, 230), (196, 234), (170, 235), (149, 232), (134, 228)]
        self.spill(pool, 1.0, (1.0, 0.78, 0.48), blur=3.0)
        pm = self.c.mask_poly(pool) & (self.GR > 0) & np.isnan(self.B)
        lift = {'rd0': 'rd1', 'void': 'rd0', 'rd1': 'rd2', 'con1': 'con2', 'con0': 'con1'}
        for k_, v_ in lift.items():
            self.g[pm & (self.g == k_)] = v_
        for j in range(22):                                                      # glints on the wet ground
            gx = 136 + int(hsh(j, 61) * 80); gy = 216 + int(hsh(j, 62) * 17)
            if pm[gy, gx]:
                ln = 2 + int(hsh(j, 63) * 4)
                for i in range(ln):
                    if gx + i < W and pm[gy, gx + i]:
                        self.g[gy, gx + i] = 'rd3'
        self.cols.append(dict(x0=hx + 2, x1=hx + 7, y=hy + 3, b=lb, slots=('win1', 'win2'), p=0.42, reach=270))
        # utility poles: mismatched heights, crossarms, a transformer; thinner with distance
        poles = [(-3.55, 19.5, 9.4, 2), (-3.5, 27.5, 8.6, 1), (2.45, 26.0, 9.0, 1)]
        tops = []
        for X, Z, hgt, wd in poles:
            x, b = int(round(col(X, Z))), row(Z)
            t = int(yh(hgt, Z))
            self.rect(x, t, x + wd, int(b) + 1, 'cool1', base=b)
            ca = int(yh(hgt - 0.6, Z))
            arm = int(0.9 * G.F / Z)
            self.rect(x - arm, ca, x + arm + wd, ca + 1, 'cool1', base=b)
            tops.append((x, t, ca, arm))
            if wd == 2:
                tr = int(yh(hgt - 2.6, Z))
                self.rect(x + 2, tr, x + 6, tr + 8, 'cool2', base=b)
                self.rect(x + 2, tr, x + 6, tr + 1, 'cool3', base=b)
        (p1x, p1t, p1c, p1a), (p2x, p2t, p2c, p2a), (p3x, p3t, p3c, p3a) = tops
        # wires: catenaries that converge down the street, a few across, two leave the frame
        self.wire(0, 34, lx + 1, top + 4, 5)
        self.wire(lx + 1, top + 3, p1x - p1a, p1c, 4)
        self.wire(p1x + p1a, p1c, 352, 46, 9)
        self.wire(p1x, p1c + 4, p2x, p2c, 2)
        self.wire(p1x - p1a, p1c, p2x - p2a, p2c, 3)
        self.wire(p2x + p2a, p2c, p3x - p3a, p3c, 4)
        self.wire(p2x, p2c + 2, 336, 74, 3)
        self.wire(p3x + p3a, p3c, 373, 18, 4)
        self.wire(167, 6, 470, 24, 16)
        self.wire(0, 12, p1x - p1a, p1c - 1, 11)

    # ------------------------------------------------------------ reflections
    def reflect(self):
        a = self.ph == 'a'
        g, B = self.g, self.B
        src = g.copy()
        vert = np.isfinite(B) & ~self.NOREF
        ys, xs = np.nonzero(vert)
        b = B[ys, xs]
        ok = b > ys + 0.5
        ys, xs, b = ys[ok], xs[ok], b[ok]
        yr = np.floor(2 * b - ys - 0.5).astype(int)
        ok = (yr >= 0) & (yr < H)
        ys, xs, b, yr = ys[ok], xs[ok], b[ok], yr[ok]
        wet = self.GR[yr, xs] > 0
        ys, xs, b, yr = ys[wet], xs[wet], b[wet], yr[wet]
        # the nearest object (largest base row) wins each target pixel
        key = yr * W + xs
        order = np.lexsort((b, key))
        key_s = key[order]
        last = np.r_[key_s[1:] != key_s[:-1], True]
        sel = order[last]
        R = np.full((H, W), None, object)
        R[yr[sel], xs[sel]] = g[ys[sel], xs[sel]]
        self.R = R
        slots = set(R.ravel()) - {None}
        d1 = {s: (s if s in EMISSIVE else darker(s, 0.05)) for s in slots}
        d2 = {s: darker(s, 0.11, 0.6) for s in slots}
        step = {'hs1': 'hs0', 'hs0': 'win4', 'win4': 'win3', 'win3': 'win2', 'win2': 'win1', 'win1': 'win0',
                'win0': 'brk2', 'lan2': 'lan1', 'lan1': 'lan0', 'lan0': 'awb0', 'neo1': 'neo0', 'neo0': 'awa1',
                'gl0': 'awb0'}
        for y in range(H):
            for x in range(W):
                s = R[y, x]
                if s is None:
                    continue
                gt = self.GR[y, x]
                emi = s in EMISSIVE
                if gt == 3:
                    continue
                elif gt == 1:                                           # the wet road: streaky, dark
                    if (y + int(hsh(y // 2, x // 23, 2) * 3)) % (2 if a else 3) == 0:
                        continue
                    v = d2[s]
                    if emi:
                        v = 'rd2'
                    if v not in ('void', 'plum'):
                        g[y, x] = v if v.startswith(('rd', 'cool', 'awh', 'awa', 'gls', 'sky')) else 'rd2'
                elif gt == 2:                                           # wet slabs: faint
                    if emi and (y + x // 4) % 4 == 0:
                        g[y, x] = step.get(step.get(s, s), 'con1')
        self.puddle_mirror(src, step)

    def puddle_mirror(self, src, step):
        """the puddle mirrors the street above it upside down, anchored at its far edge: each column
        starts from the base row of the nearest thing standing in it, compressed 2.3x so the street
        from the ground to the signs fits (the tram strip, the hero shopfront and its sign) in
        darker slots, lights a step down. A: broken into concentric ring arcs. B: glass-smooth."""
        a = self.ph == 'a'
        g, B, pud = self.g, self.B, self.pud
        k = 2.3
        sl = set(src.ravel()) - {None}
        d1 = {s: darker(s, 0.05) for s in sl}
        d2 = {s: darker(s, 0.1, 0.65) for s in sl}
        rings = []
        if a:
            ys_, xs_ = np.nonzero(pud)
            for i in range(7):
                ph = ((self.t + int(hsh(i, 71) * 24)) % 24) / 24.0
                gen = (self.t + int(hsh(i, 71) * 24)) // 24
                j = int(hsh(i, gen, 73) * len(xs_))
                rings.append((xs_[j], ys_[j], 3 + 15 * ph))
        for x in np.nonzero(pud.any(0))[0]:
            ys = np.nonzero(pud[:, x])[0]
            ye = ys.min()
            colB = B[:ye, x]
            fin = np.isfinite(colB)
            if not fin.any():
                continue
            bs = colB[fin].max()
            for y in ys:
                ysrc = int(bs - 1 - (y - ye) * k)
                if ysrc < 0:
                    continue
                s = src[ysrc, x]
                if s is None:
                    continue
                emi = s in EMISSIVE
                if a:
                    v = step.get(s, d1[s]) if emi else d2[s]
                    cut = False
                    for (cx, cy, R) in rings:
                        e = np.hypot(x - cx, (y - cy) / 0.3)
                        if e < R:
                            dd = R - e
                            if dd % 4 < 1.0:
                                v = 'cool4' if y <= cy else 'rn1'               # a ring crest arc
                                cut = False
                                break
                            if int(dd // 4) % 2 == 1:
                                cut = True
                    if cut:
                        v = 'rd0'
                else:
                    v = step.get(s, s) if emi else d1[s]
                g[y, x] = v
        # the edge: a 1 px lighter lip on the far side, a dark lip elsewhere
        edge = pud & ~(np.roll(pud, 1, 0) & np.roll(pud, -1, 0) & np.roll(pud, 1, 1) & np.roll(pud, -1, 1))
        top_edge = pud & ~np.roll(pud, 1, 0)
        g[edge & ~top_edge] = 'rd0'
        g[top_edge] = 'cool4'
        if a:
            g[self.pud_curb & ~edge & (self.yy % 3 != 0)] = 'rd1'           # the drowned curb

    def light_columns(self):
        """lights stretch into stepped dash columns down the wet road toward the viewer"""
        a = self.ph == 'a'
        g = self.g
        for ci, cdef in enumerate(self.cols):
            x0, x1, ysrc, b = cdef['x0'], cdef['x1'], cdef['y'], cdef['b']
            sl = cdef['slots']
            ym = 2 * b - ysrc
            start = int(b) + 1
            reach = cdef.get('reach', 270)
            wc = max(1, x1 - x0)
            cx = (x0 + x1) / 2
            for y in range(start, min(H, reach)):
                gt = self.GR[y, int(np.clip(cx, 0, W - 1))]
                if gt == 0 or gt == 3:
                    continue
                dist = abs(y - ym)
                near_m = max(0.0, 1 - dist / 40.0)
                p = cdef['p'] * (0.55 + 0.45 * near_m)
                if gt == 2:
                    p *= 0.5
                if hsh(y, ci, 11, self.t // 3 if a else 0) > p:
                    continue
                grow = (y - G.HZ) / max(1.0, (b - G.HZ))
                hw = max(0.5, wc * 0.32 * min(1.5, 0.6 + 0.3 * grow))
                off = (hsh(y, ci, 13) - 0.5) * hw * 0.7
                ln = max(1, int(round(hw * (0.35 + 0.65 * hsh(y, ci, 17)))))
                lev = hsh(y, ci, 19) + 0.35 * near_m
                idx = 0 if lev < 0.6 else (1 if lev < 0.95 else 2)
                s = sl[min(idx, len(sl) - 1)]
                xa = int(round(cx + off - ln / 2))
                for x in range(xa, xa + ln):
                    if 0 <= x < W and self.GR[y, x] in (1, 2):
                        g[y, x] = s

    # ------------------------------------------------------------ props
    def props(self):
        a = self.ph == 'a'
        # the folded stool leaning on the hero's side wall: an X of legs under a flat seat
        sx, sb = int(col(3.12, 14.6)), int(row(14.6))
        stool = parse("""
######
.#..#.
..##..
..##..
.#..#.
.#..#.
#....#
#....#""")
        self.stamp(stool, sx - 3, sb - 8, 'wd1', sb)
        self.rect(sx - 3, sb - 8, sx + 3, sb - 7, 'wd0', base=sb)
        # the bucket under the awning leak: trapezoid, lip, water
        bx, bb = int(col(2.9, 16.2)), int(row(16.2))
        bucket = parse("""
#######
.#####.
.#####.
.#####.
..###..""")
        self.stamp(bucket, bx - 3, bb - 5, 'cool3', bb)
        self.rect(bx - 3, bb - 5, bx + 4, bb - 4, 'cool4', base=bb)
        self.rect(bx - 2, bb - 4, bx + 3, bb - 3, 'rd2' if a else 'cool2', base=bb)
        self.rect(bx - 2, bb - 2, bx - 1, bb, 'cool2', base=bb)
        self.bucket = (bx, bb - 5)
        # a potted plant by the hero's door
        ppx, ppb = int(col(6.15, 13.3)), int(row(13.3))
        self.rect(ppx - 3, ppb - 5, ppx + 3, ppb, 'brk2', base=ppb)
        self.rect(ppx - 3, ppb - 5, ppx + 3, ppb - 4, 'brk3', base=ppb)
        leaves = parse("""
..#.#..
.##.##.
#.###.#
.#####.
..###..""")
        self.stamp(leaves, ppx - 3, ppb - 10, 'pl1', ppb)
        self.px(ppx, ppb - 10, 'pl0', ppb); self.px(ppx - 2, ppb - 7, 'pl0', ppb)
        # the bicycle chained to the street lamp: two open rings, a diamond frame, bars, a basket
        self.bicycle(96, int(row(13.0)))
        # a chalk A-board in front of the hero
        ax, ab = int(col(3.0, 12.4)), int(row(12.4))
        self.rect(ax - 4, ab - 11, ax + 4, ab - 1, 'con0', base=ab)
        self.rect(ax - 3, ab - 10, ax + 3, ab - 2, 'cool1', base=ab)
        for k in range(3):
            self.rect(ax - 2, ab - 9 + k * 3, ax + 1 + (k % 2), ab - 8 + k * 3, 'con3', base=ab)
        self.px(ax - 4, ab - 1, 'con0', ab); self.px(ax + 3, ab - 1, 'con0', ab)
        self.rect(ax - 4, ab - 1, ax - 3, ab, 'con0', base=ab); self.rect(ax + 3, ab - 1, ax + 4, ab, 'con0', base=ab)

    def bicycle(self, x0, base):
        r = 8
        cyw = base - r - 1
        ring = lambda cx: ((self.xx + 0.5 - cx) ** 2 + ((self.yy + 0.5 - cyw) * 1.0) ** 2)
        for cx in (x0 + 9, x0 + 33):
            d = ring(cx)
            m = (d <= (r + 0.5) ** 2) & (d >= (r - 0.6) ** 2)
            self.put(m, 'cool3', base=base)
            self.put(m & (self.yy + 0.5 > cyw + r - 1.5), 'cool1', base=base)
            hub = d <= 1.3
            self.put(hub, 'cool3', base=base)
            sp = (d < (r - 1) ** 2) & ((self.xx + self.yy) % 4 == 0) & (np.abs(self.yy - cyw) + np.abs(self.xx - cx) < r)
            self.put(sp & ((self.xx - cx) == (self.yy - cyw)), 'cool2', base=base)
        f = lambda xa, ya, xb, yb, s='con4': self.c.line(xa, ya, xb, yb, s)
        bb = (x0 + 20, cyw + 1)            # bottom bracket
        st = (x0 + 17, cyw - 9)            # seat tube top
        ht = (x0 + 30, cyw - 9)            # head tube top
        f(x0 + 9, cyw, *bb); f(x0 + 9, cyw, *st); f(*bb, *st); f(*st, *ht); f(*bb, ht[0] + 1, ht[1] + 2)
        f(ht[0], ht[1], x0 + 33, cyw)
        self.rect(st[0] - 3, st[1] - 1, st[0] + 2, st[1], 'plum', base=base)          # saddle
        self.rect(ht[0] - 1, ht[1] - 2, ht[0] + 4, ht[1] - 1, 'cool2', base=base)     # bars
        self.rect(ht[0] + 2, ht[1] - 1, ht[0] + 7, ht[1] + 4, 'cool1', base=base)     # basket
        self.rect(ht[0] + 3, ht[1], ht[0] + 6, ht[1] + 3, 'cool0', base=base)
        for yy_ in range(cyw - r - 4, base + 1):
            for xx_ in range(x0, x0 + 44):
                if self.g[yy_, xx_] in ('con4',) and np.isnan(self.B[yy_, xx_]):
                    self.B[yy_, xx_] = base
        # the chain loops round the lamp post (138) and the rear wheel
        for k in range(5):
            self.px(x0 + 38 + k, cyw - 2 + (k % 2), 'cool4', base)

    def cat(self):
        self.light(400, 227, (30, 8), (1.0, 0.72, 0.42), 1.3)                       # the shop's light where it walks
        """one cat crossing the road in the shop's light pool, walking left: pointed ears, an
        arched back, the tail up in a hook; dark body with a warm rim on the shop side"""
        art = parse("""
......................
..#.#.............##..
..###..............#..
.#####.............#..
######.###########.#..
#####################.
.###################..
..#################...
..###..........####...
..#.#..........#..#...
.#..#.........#...#...""")
        cx, by = 398, 232
        h_, w_ = art.shape
        x0, y0 = cx - w_ // 2, by - h_
        for j in range(h_):
            for i in range(w_):
                if art[j, i]:
                    self.px(x0 + i, y0 + j, 'void', by)
                    self.ACT[y0 + j, x0 + i] = True
        # warm rim on the top and right (the shop is to the right), eye
        for j in range(h_):
            for i in range(w_):
                if art[j, i] and (j == 0 or not art[j - 1, i]) and i > 4:
                    self.px(x0 + i, y0 + j, 'win1', by)
        for j in range(h_):
            for i in range(w_ - 1, -1, -1):
                if art[j, i]:
                    self.px(x0 + i, y0 + j, 'win1', by)
                    break
        self.px(x0 + 1, y0 + 4, 'win3', by)
        self.px(x0 + 3, y0 + 1, 'cool1', by)
        self.cat_box = (x0, y0, x0 + w_, by)

    def steam(self):
        """one vent breathes a hand-shaped plume that leans right and thins as it rises"""
        vx, vy = self.vent
        self.light(vx + 6, vy - 18, (12, 18), (0.85, 0.85, 0.9), 0.3)               # the plume scatters lamp light
        puffs = [(0, -3, 0.08, 3), (1, -8, 0.25, 5), (3, -14, 0.42, 6), (6, -21, 0.58, 7), (10, -28, 0.72, 2),
                 (15, -35, 0.85, 9), (21, -41, 0.95, 4)]
        for k, (dx, dy, age, seed) in enumerate(puffs):
            fx.smoke_puff(self.c, vx + dx, vy + dy, age, seed=seed + 11, r=(1.4, 5.0),
                          ramp=['rd1', 'rd2', 'stm0', 'stm0', 'stm1', 'stm1'], lobes=6, rise=0, sway=0.4)

    # ------------------------------------------------------------ weather (A)
    def rain(self):
        t = self.t
        before = self.g.copy()
        over = np.zeros((H, W), bool)
        sxa, sya, sxb, syb = self.sign_box
        over[sya - 1:syb + 1, sxa - 1:sxb + 1] = True
        lx0, ly0, lx1, ly1 = self.lantern
        over[ly0:ly1, lx0 - 1:lx1 + 1] = True
        fx.rain_cells(self.c, t, T_LOOP, n=175, length=4, slot='rn0', cycles=8, seed=5,
                      region=(0, 0, W, 262), slant=7, over=over)
        tmp = Canvas(W, H, None)
        fx.rain_cells(tmp, t, T_LOOP, n=64, length=11, slot='rn1', cycles=10, seed=19,
                      region=(0, 0, W, H), slant=7, over=over)
        near = tmp.g == 'rn1'
        lit = np.isin(before, list(EMISSIVE))
        self.g[near & ~lit] = 'rn1'
        self.g[near & lit] = 'win3'
        fx.splash_field(self.c, t, T_LOOP, (60, 190, 470, 236), n=18, every=12, size=1,
                        slots=('rn1', 'rn0'), over=self.pud | (self.GR == 0), seed=3)
        for j in range(14):                                                     # crowns near the viewer
            sx_ = 70 + int(hsh(j, 81) * 380); sy_ = 240 + int(hsh(j, 82) * 28)
            if 0 <= sy_ < H and self.GR[sy_, sx_] in (1, 2) and not self.pud[sy_, sx_]:
                fx.splash(self.c, sx_, sy_, (t + j) % 3, size=2, slots=('cool4', 'rn1'))
        # awnings drip in stepped streams; the hero's side awning leaks into the bucket
        for ai, aw in enumerate(self.awnings):
            m = aw['mask']
            ys, xs = np.nonzero(m)
            if not len(xs):
                continue
            cols_ = sorted(set(xs))
            n = max(2, min(6, len(cols_) // 9))
            picks = sorted({cols_[int(hsh(ai, k, 31) * len(cols_))] for k in range(n)})
            for k, x in enumerate(picks):
                ylip = ys[xs == x].max() + 1
                Zg = G.depth_on_wall(x + 0.5, aw['X']) if aw['side'] in ('L', 'R') else aw['Z']
                yg = int(row(Zg))
                ph = int(hsh(ai, k, 33) * 5)
                on, off = 2 + (k % 2), 1 + int(hsh(ai, k, 35) * 2)
                for y in range(ylip, min(H, yg)):
                    if ((y - ylip + ph + t) % (on + off)) < on:
                        self.g[y, x] = 'rn1'
                if 0 < yg < H and self.GR[min(H - 1, yg), x] > 0:
                    fx.splash(self.c, x, yg, (t + k) % 4, slots=('rn1', 'rn1'))
        # the leak into the bucket
        bx, by = self.bucket
        ytop = int(yh(2.3, 16.2))
        for y in range(ytop, by):
            if (y + t) % 3 != 0:
                self.g[y, bx] = 'rn1'
        # the overflowing gutter joint on the hero's side face: a thick stepped stream
        gx = int(col(G.X_R, G.Z_HERO_BACK - 0.25)) - 1
        gy0, gy1 = int(yh(4.3, G.Z_HERO_BACK)), int(row(G.Z_HERO_BACK - 0.6))
        self.rect(gx - 1, gy0 - 1, gx + 2, gy0 + 1, 'cool2')
        for y in range(gy0 + 1, gy1):
            w = 2 if (y - gy0) < 30 else 1
            if ((y + t * 2) % 7) < 5:
                self.rect(gx - (y - gy0) // 40, y, gx - (y - gy0) // 40 + w, y + 1, 'rn1')
        fx.splash(self.c, gx - 2, gy1, t % 3, size=2, slots=('rn1', 'rn1'))
        self.INT |= (self.g != before)
