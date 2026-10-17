"""07 Turntable shipyard: one 3D description of a canal-side boatyard, turned on a lazy susan.

The yard is a 136 x 100 unit slab floating in the dark, described once in MODEL coordinates: a
graving dock with stepped altars, the ship (a hull field: keel, stem, frames, ribbands, planking,
deck, bulwarks, mast and bowsprit), a timber crane (lattice mast, laddered jib, hanging block), a
sawpit, a plank stack, a pair of mitred lock-gate leaves, the canal, and the chandlery hut on the
far bank with its landing stage and a moored dory.

A turn rotates every model coordinate by k quarter-turns about the slab's centre (Turn.pt) before
it reaches tools/iso.py, so the 2:1 camera and the sun stay put while the model spins. The build
stage (1 frames .. 4 rigged) decides which ship parts exist. The light (a sun or moon direction in
camera space) shades every face in palette steps from N.L (lstep) and drives iso's hard cast
shadows (two steps down); there is no light layer. Turn 1 (dawn, stage 1, 0 deg) and turn 4
(night, stage 4, 270 deg) are the delivered stills.
"""
import sys, math, json, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from PIL import Image
import artlib
import colorlib as cl
from palette import from_lch
from iso import Iso, hash2
import sdf

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / 'out'
W, H = 640, 360
SX, SY = 140, 100                 # slab footprint, model units
CX, CY = 70, 50                   # the lazy susan's axis (integers keep the unit grid on turns)

# ================================================================ palettes
def _L(L, C, h):
    return from_lch(L, C, h)

def _ramp(p, name, Ls, Cs, hs):
    for i, (L, C, h) in enumerate(zip(Ls, Cs, hs)):
        p['%s%d' % (name, i)] = _L(L, C, h)

def dawn_palette():
    """turn 1: low warm sun from the left; five near-neutral greys carry the stage, the ship's
    oak is the only warm chroma"""
    p = {'void': _L(0.085, 0.010, 285), 'ol': '#050407'}
    _ramp(p, 'stone', (.16, .23, .31, .39, .47), (.009, .008, .008, .010, .013), (265, 255, 80, 72, 68))
    _ramp(p, 'soil', (.10, .125, .15, .18, .21), (.012, .013, .014, .014, .014), (40, 42, 45, 50, 55))
    _ramp(p, 'oak', (.22, .33, .46, .60, .74), (.035, .055, .078, .095, .088), (42, 50, 58, 66, 74))
    _ramp(p, 'timber', (.16, .22, .29, .36, .44), (.010, .014, .020, .026, .032), (50, 56, 62, 68, 74))
    _ramp(p, 'water', (.075, .095, .12, .15, .20), (.016, .020, .024, .026, .028), (240, 238, 234, 230, 225))
    _ramp(p, 'canvas', (.17, .23, .30, .37, .44), (.008, .010, .013, .015, .017), (110, 105, 100, 96, 92))
    _ramp(p, 'tar', (.10, .13, .17, .21, .26), (.012, .012, .013, .014, .015), (40, 42, 45, 48, 50))
    _ramp(p, 'trim', (.20, .28, .36, .44, .52), (.05, .07, .085, .09, .085), (30, 32, 36, 40, 45))
    p.update({'spec': _L(.93, .03, 85), 'rope': _L(.40, .03, 78), 'ropeD': _L(.27, .02, 70),
              'iron': _L(.16, .008, 260), 'ironL': _L(.30, .01, 250),
              'lampH': _L(.30, .01, 250), 'lampH2': _L(.20, .01, 250),
              'lampA': _L(.30, .01, 250), 'lampA2': _L(.20, .01, 250),
              'win': _L(.22, .015, 240), 'winD': _L(.16, .012, 240),
              'refl0': _L(.12, .02, 240), 'refl1': _L(.15, .02, 238),
              'pen': _L(.40, .10, 30), 'penD': _L(.30, .08, 28),
              'smoke0': _L(.43, .012, 70), 'smoke1': _L(.53, .014, 75),
              'wet': _L(.11, .015, 240), 'glint': _L(.36, .025, 225)})
    for i in range(5):                            # pool slots: no lanterns by day
        p['stoneW%d' % i] = p['stone%d' % i]; p['oakW%d' % i] = p['oak%d' % i]; p['timberW%d' % i] = p['timber%d' % i]
    p['specW'] = p['spec']
    return p

def night_palette():
    """turn 4: moonlight from the right in cool greys; warm lantern slots are the only chroma"""
    p = {'void': _L(0.060, 0.012, 275), 'ol': '#040306'}
    _ramp(p, 'stone', (.10, .14, .19, .245, .30), (.012, .013, .014, .016, .018), (268, 262, 256, 250, 244))
    _ramp(p, 'stoneW', (.16, .21, .27, .33, .40), (.040, .050, .060, .065, .065), (55, 58, 62, 66, 70))
    _ramp(p, 'soil', (.06, .075, .095, .115, .135), (.012, .012, .012, .013, .013), (275, 272, 270, 265, 260))
    _ramp(p, 'oak', (.15, .22, .31, .41, .52), (.022, .028, .033, .036, .034), (55, 62, 70, 82, 95))
    _ramp(p, 'oakW', (.26, .36, .48, .61, .74), (.060, .080, .100, .110, .100), (48, 54, 60, 67, 74))
    _ramp(p, 'timber', (.10, .14, .185, .23, .285), (.010, .011, .012, .013, .015), (60, 62, 250, 245, 240))
    _ramp(p, 'timberW', (.18, .25, .33, .41, .50), (.050, .060, .070, .075, .070), (52, 56, 60, 64, 70))
    _ramp(p, 'water', (.055, .07, .09, .115, .15), (.016, .020, .024, .026, .028), (250, 248, 245, 240, 235))
    _ramp(p, 'canvas', (.11, .15, .19, .24, .29), (.008, .010, .011, .012, .013), (250, 250, 248, 245, 240))
    _ramp(p, 'tar', (.07, .09, .12, .15, .19), (.010, .010, .011, .012, .013), (270, 265, 260, 255, 250))
    _ramp(p, 'trim', (.16, .22, .29, .36, .43), (.050, .065, .080, .085, .080), (28, 30, 33, 36, 40))
    p.update({'spec': _L(.80, .02, 235), 'specW': _L(.92, .05, 82),
              'rope': _L(.30, .02, 70), 'ropeD': _L(.20, .015, 260),
              'iron': _L(.12, .008, 260), 'ironL': _L(.24, .01, 250),
              'lampH': _L(.95, .11, 88), 'lampH2': _L(.78, .14, 72),
              'lampA': _L(.84, .12, 80), 'lampA2': _L(.64, .13, 62),
              'win': _L(.74, .125, 72), 'winD': _L(.55, .12, 58),
              'refl0': _L(.40, .10, 58), 'refl1': _L(.58, .12, 68),
              'pen': _L(.48, .16, 28), 'penD': _L(.36, .13, 25),
              'smoke0': _L(.14, .01, 260), 'smoke1': _L(.18, .01, 255),
              'wet': _L(.07, .015, 250), 'glint': _L(.24, .03, 230)})
    return p

# ================================================================ the turntable
class Turn:
    """k quarter-turns of the model about (CX, CY): model +x goes to world +y for k = 1"""
    def __init__(self, k):
        self.k = k % 4
    def vec(self, x, y):
        for _ in range(self.k):
            x, y = -y, x
        return x, y
    def ivec(self, x, y):
        for _ in range(self.k):
            x, y = y, -x
        return x, y
    def pt(self, x, y):
        dx, dy = self.vec(x - CX, y - CY)
        return CX + dx, CY + dy
    def inv(self, x, y):
        dx, dy = self.ivec(x - CX, y - CY)
        return CX + dx, CY + dy
    def box(self, X, Y, w, d):
        xa, ya = self.pt(X, Y)
        xb, yb = self.pt(X + w, Y + d)
        return min(xa, xb), min(ya, yb), abs(xb - xa), abs(yb - ya)

TURN = Turn(0)
LIGHT = np.array([-0.45, 0.8, 0.42]) / np.linalg.norm([-0.45, 0.8, 0.42])

def lstep(b):
    """N.L -> ramp step: shade 1, glancing 2, lit 3, full face-on 4"""
    return 1 if b < -0.05 else (2 if b < 0.30 else (3 if b < 0.62 else 4))

def M(ramp, tex=None, bias=0):
    """an sdf material: the step from the world normal and LIGHT, the texture in model space"""
    def f(P, N, step, t):
        st = max(0, min(4, lstep(float(np.dot(N, LIGHT))) + bias))
        if tex is None:
            return '%s%d' % (ramp, st)
        mx, my = TURN.inv(float(P[0]), float(P[1]))
        nx, ny = TURN.ivec(float(N[0]), float(N[1]))
        return tex(mx, my, float(P[2]), (nx, ny, float(N[2])), st)
    return f

class Rot(sdf.Node):
    """a model-space sdf node seen through the current turn"""
    def __init__(self, node):
        self.node, self.T = node, TURN
        x0, y0, z0, x1, y1, z1 = node.bbox
        X, Y, w, d = TURN.box(x0, y0, x1 - x0, y1 - y0)
        self.bbox = (X, Y, z0, X + w, Y + d, z1)
    def d(self, x, y, z):
        mx, my = self.T.inv(x, y)
        return self.node.d(mx, my, z)
    def leaves(self):
        return self.node.leaves()
    def owner(self, x, y, z):
        mx, my = self.T.inv(x, y)
        return sdf.owner(self.node, mx, my, z)

class Field(sdf.Node):
    """a hand-written distance field with one material"""
    def __init__(self, fn, bbox, mat):
        self.fn, self.bbox, self.mat = fn, tuple(float(v) for v in bbox), mat
    def d(self, x, y, z):
        return self.fn(x, y, z)

class Swap(sdf.Node):
    """a node with two axes exchanged: 'xy' lays a boat built along x into the canal (along y),
    'yz' lays a plate (polygon in x-z) flat on the ground (polygon in x-y)"""
    def __init__(self, node, axes='xy'):
        self.node, self.axes = node, axes
        b = node.bbox
        self.bbox = (b[1], b[0], b[2], b[4], b[3], b[5]) if axes == 'xy' else (b[0], b[2], b[1], b[3], b[5], b[4])
        self.mat = getattr(node, 'mat', None)
    def d(self, x, y, z):
        return self.node.d(y, x, z) if self.axes == 'xy' else self.node.d(x, z, y)
    def leaves(self):
        return [self]

class Beam(sdf.Node):
    """a square-section timber from p0 to p1 (w across, h deep): shores, braces, gate leaves"""
    def __init__(self, p0, p1, w=1.0, h=1.0, mat=None, up=(0, 0, 1)):
        self.p0, self.p1 = np.array(p0, float), np.array(p1, float)
        e1 = self.p1 - self.p0
        self.len = float(np.linalg.norm(e1)); e1 /= self.len
        u = np.array(up, float)
        e2 = np.cross(u, e1)
        if np.linalg.norm(e2) < 1e-6:
            e2 = np.cross(np.array([1.0, 0, 0]), e1)
        e2 /= np.linalg.norm(e2); e3 = np.cross(e1, e2)
        self.E = np.stack([e1, e2, e3]); self.hw, self.hh = w / 2, h / 2
        self.c = (self.p0 + self.p1) / 2
        r = max(w, h)
        lo = np.minimum(self.p0, self.p1) - r; hi = np.maximum(self.p0, self.p1) + r
        self.bbox = tuple(lo) + tuple(hi)
        self.mat = mat
    def d(self, x, y, z):
        q = np.stack([x - self.c[0], y - self.c[1], z - self.c[2]], -1) @ self.E.T
        a = np.abs(q) - np.array([self.len / 2, self.hw, self.hh])
        out = np.sqrt((np.maximum(a, 0) ** 2).sum(-1))
        return out + np.minimum(a.max(-1), 0)

# ================================================================ the ship's lines
class Ship:
    """the hull as functions of station u (0 transom .. 1 stem head) and height z"""
    def __init__(self, x0=15.0, L=87.0, yc=47.0, zk=-4.0, B=11.0, D=18.0, sa=5.5, sf=9.0, wl=8.6):
        self.x0, self.L, self.yc, self.zk, self.B, self.D, self.sa, self.sf = x0, L, yc, zk, B, D, sa, sf
        self.keel = 2.2 if L > 30 else 0.6
        self.zwl = zk + wl                       # the painted waterline
    def u(self, x):
        return (np.asarray(x, float) - self.x0) / self.L
    def zs(self, u):
        u = np.asarray(u, float)
        return self.zk + self.D + np.where(u < 0.55, self.sa * ((0.55 - u) / 0.55) ** 2,
                                           self.sf * ((u - 0.55) / 0.45) ** 2)
    def zb(self, u):
        u = np.asarray(u, float)
        base = self.zk + self.keel
        fore = np.clip((u - 0.78) / 0.22, 0, 1)
        aft = np.clip((0.09 - u) / 0.09, 0, 1)
        run = np.clip((0.24 - u) / 0.24, 0, 1) if self.L > 30 else 0.0
        return base + (self.zs(1.0) - 0.6 - base) * fore ** 2.1 + 0.5 * self.D * aft ** 1.3 + 0.22 * self.D * run ** 1.6
    def bm(self, u):
        u = np.clip(np.asarray(u, float), 0, 1)
        uf = np.clip((u - 0.5) / 0.5, 0, 1); ua = np.clip((0.5 - u) / 0.5, 0, 1)
        return self.B * np.where(u >= 0.5, (1 - uf ** 2.0) ** 0.8, 0.62 + 0.38 * (1 - ua ** 2))
    def eta(self, u, z):
        zb, zs = self.zb(u), self.zs(u)
        return (np.asarray(z, float) - zb) / np.maximum(zs - zb, 0.5)
    def hb(self, u, z):
        e = np.clip(self.eta(u, z), 0, 1)
        end = np.clip(np.abs(np.asarray(u, float) - 0.5) / 0.5, 0, 1) ** 2
        sc = np.sin(np.clip(e / (0.42 + 0.40 * end), 0, 1) * np.pi / 2) ** (0.7 + 0.7 * end)
        sc = sc * (1 - 0.05 * np.clip((e - 0.8) / 0.2, 0, 1))
        k = 0.9 if self.L > 30 else 0.35
        return k + np.maximum(self.bm(u) - k, 0) * sc
    def xaft(self, z):
        return self.x0 + 0.3 * np.clip(float(self.zs(0.0)) - np.asarray(z, float), 0, None)
    def side(self, x, y, z):
        """(signed distance to the side, |y|, hb, u) with the side term normalised by its slope"""
        u = self.u(x); uc = np.clip(u, 0, 1)
        hb = self.hb(uc, z)
        e = 0.05
        gz = (self.hb(uc, z + e) - self.hb(uc, z - e)) / (2 * e)
        gx = (self.hb(np.clip(uc + e / self.L, 0, 1), z) - self.hb(np.clip(uc - e / self.L, 0, 1), z)) / (2 * e)
        ay = np.abs(y - self.yc)
        return (ay - hb) / np.sqrt(1 + gz * gz + gx * gx), ay, hb, uc
    def solid_d(self, x, y, z):
        ds, ay, hb, uc = self.side(x, y, z)
        return np.maximum.reduce([ds * 0.85, z - self.zs(uc), self.zb(uc) - z, self.xaft(z) - x,
                                  x - (self.x0 + self.L)])
    def open_d(self, x, y, z, t=0.7):
        """an open boat: the planked shell with its inside hollow (the dory)"""
        ds, ay, hb, uc = self.side(x, y, z)
        return np.maximum.reduce([ds * 0.85, z - self.zs(uc), self.zb(uc) - z, self.xaft(z) - x,
                                  x - (self.x0 + self.L), np.minimum((hb - t) - ay, (self.zb(uc) + t) - z)])
    def frames_d(self, x, y, z, ribs, mould=1.5):
        ds, ay, hb, uc = self.side(x, y, z)
        base = np.maximum.reduce([ds * 0.8, self.zb(uc) - z, (hb - mould) - ay, self.xaft(z) - x])
        out = np.full(np.shape(x), 1e9)
        for xr, sided, over in ribs:
            top = float(self.zs(self.u(xr))) + over
            out = np.minimum(out, np.maximum.reduce([base, np.abs(x - xr) - sided / 2, z - top]))
        return out
    def band_d(self, x, y, z, eta0, u0, u1, side=1, t=0.55, hgt=0.9):
        """a ribband: a batten outside the frames along the line eta = eta0 (follows the sheer)"""
        u = self.u(x); uc = np.clip(u, 0, 1)
        zc = self.zb(uc) + eta0 * (self.zs(uc) - self.zb(uc))
        hb = self.hb(uc, zc)
        yy = (y - self.yc) * side
        return np.maximum.reduce([np.abs(yy - (hb + t / 2)) - t / 2, np.abs(z - zc) - hgt / 2,
                                  (self.x0 + u0 * self.L) - x, x - (self.x0 + u1 * self.L)])
    def bulwark_d(self, x, y, z, h=2.3, t=0.6):
        u = self.u(x); uc = np.clip(u, 0.0, 1.0)
        zs = self.zs(uc); hbt = self.hb(uc, zs)
        ay = np.abs(y - self.yc)
        return np.maximum.reduce([np.abs(ay - (hbt - t / 2)) - t / 2, z - (zs + h), (zs - 0.6) - z,
                                  self.xaft(z) - x, x - (self.x0 + self.L - 0.6)])
    def cap_d(self, x, y, z, h=2.3):
        u = self.u(x); uc = np.clip(u, 0.0, 1.0)
        zs = self.zs(uc); hbt = self.hb(uc, zs)
        ay = np.abs(y - self.yc)
        return np.maximum.reduce([np.abs(ay - (hbt - 0.45)) - 0.6, np.abs(z - (zs + h + 0.25)) - 0.35,
                                  self.xaft(z) - x - 0.3, x - (self.x0 + self.L - 0.3)])
    def bbox(self, pad=1.5, top=0.0):
        return (self.x0 - 3, self.yc - self.B - pad, self.zk, self.x0 + self.L + 1.5, self.yc + self.B + pad,
                float(self.zs(1.0)) + top + 1)

SHIP = Ship()
# frames: (station u, sided width, head above the sheer); hand-spaced, a doubled pair amidships, a
# two-frame gap aft where the next frames go in (one waits on the ground)
_RU = [(0.105, 1.3, 0.6), (0.16, 1.2, 1.4), (0.212, 1.3, 0.2), (0.372, 1.4, 1.6), (0.398, 1.2, 1.0),
       (0.452, 1.3, 2.2), (0.503, 1.2, 0.0), (0.556, 1.4, 1.2), (0.611, 1.2, 2.0), (0.659, 1.3, 0.4),
       (0.712, 1.2, 1.5), (0.761, 1.3, 0.0), (0.806, 1.2, 0.9), (0.851, 1.2, 0.3), (0.893, 1.2, 0.0)]
RIBS = [(math.floor(SHIP.x0 + u * SHIP.L) + 0.5, sd, ov) for u, sd, ov in _RU]

# ================================================================ layout (model units)
DOCK = (7.0, 106.0, 27.0, 67.0)                  # x0, x1, y0, y1 of the graving dock at the coping
STEPS = [(-1.5, 2.0), (-3.0, 2.0), (-4.5, 2.0)]  # altar treads: top z, width
FLOOR = -6.0
ENTR = (106.0, 112.0, 36.0, 58.0)                # the dock mouth, closed by stop-logs at x 108
STOP = 108.0
CANAL = (112.0, 126.0)
WATER, LOW = -2.6, -4.8                          # the canal above and below the lock
LOCK = dict(yh=85.0, ym=82.2)                    # leaf hinges at the canal walls (y yh), the mitre at y ym
SAWPIT = (20.0, 38.0, 76.0, 82.0)
HUT = (128.4, 56.0, 10.6, 18.0)                  # x, y, w, d on the far bank
CRANE = dict(x=48.0, y=11.0, w=6.0, h=46.0)

# ================================================================ textures (model space)
def _bounds(lo, seed, step=(2.6, 4.4)):
    out, v, k = [], lo, 0
    while v < lo + 400:
        out.append(v)
        v += step[0] + hash2(k, 3, seed) * (step[1] - step[0]); k += 1
    return np.array(out)

_CB = {s: _bounds(-20, s) for s in range(12)}

def _seam(v, seed, tol=0.32):
    b = _CB[seed % 12]
    i = int(np.searchsorted(b, v))
    d = min(abs(v - b[max(0, i - 1)]), abs(b[min(len(b) - 1, i)] - v))
    return d < tol

def _in(mx, my, x0, x1, y0, y1, e=0.02):
    return x0 - e <= mx <= x1 + e and y0 - e <= my <= y1 + e

def tex_ground(mx, my, mz, n, st):
    if n[2] > 0.5:                                # the yard's top: coping, quay, packed earth
        x0, x1, y0, y1 = DOCK
        cop = 2.4
        if y0 - cop <= my < y0 and x0 - cop <= mx < CANAL[0]:
            return 'stone%d' % (st - 1 if _seam(mx, 1) or my < y0 - cop + 0.35 else st)
        if y1 <= my < y1 + cop and x0 - cop <= mx < CANAL[0]:
            return 'stone%d' % (st - 1 if _seam(mx, 2) or my > y1 + cop - 0.35 else st)
        if x0 - cop <= mx < x0 and y0 <= my < y1:
            return 'stone%d' % (st - 1 if _seam(my, 3) or mx < x0 - cop + 0.35 else st)
        if CANAL[0] - 2.4 <= mx < CANAL[0]:
            return 'stone%d' % (st - 1 if _seam(my, 4) or mx < CANAL[0] - 2.05 else st)
        if CANAL[1] <= mx < CANAL[1] + 2.0:
            return 'stone%d' % (st - 1 if _seam(my, 5) or mx > CANAL[1] + 1.7 else st)
        if mx >= CANAL[1] + 2.0:                   # far bank: packed gravel
            return 'stone%d' % (st - 1 if hash2(int(mx * 2), int(my * 1.5), 9) < 0.05 else st)
        if _worn(mx, my) and st >= 2:
            return 'stone%d' % min(4, st + 1)
        if _chips(mx, my):
            return 'timber%d' % min(4, st + 1)
        if hash2(int(mx * 1.3), int(my * 1.3), 7) < 0.03:
            return 'stone%d' % (st - 1)
        return 'stone%d' % st
    if _in(mx, my, *SAWPIT):                      # the sawpit is boarded
        return tex_boards(mx, my, mz, n, st, 'timber')
    if mz > -10.2 and (abs(mx - CANAL[0]) < 0.05 or abs(mx - CANAL[1]) < 0.05 or
                       (ENTR[0] <= mx <= ENTR[1] and (abs(my - ENTR[2]) < 0.05 or abs(my - ENTR[3]) < 0.05))):
        return tex_wall(mx, my, mz, n, st)
    # the slab's cut faces: coursed stone over strata
    a = my if abs(n[0]) > 0.5 else mx
    if mz > -6:
        course = int((mz + 6) // 2)
        if (mz + 6) % 2 < 0.45 or _seam(a + course * 1.7, 6 + course % 3, 0.28):
            return 'stone%d' % max(0, st - 1)
        return 'stone%d' % st
    if mz > -7:
        return 'stone%d' % max(0, st - 2)
    band = int((-mz - 7) // 3.5)
    s2 = max(0, min(4, st - 1 - (band % 2)))
    if hash2(int(a * 1.2), int(mz), 11) < 0.04:
        s2 = min(4, s2 + 1)
    return 'soil%d' % s2

WORN = [(36, 70.5, 9, 2.2), (62, 71.0, 11, 2.6), (88, 70.2, 8, 2.0), (106, 69.8, 5, 1.6)]

def _worn(mx, my):
    """trodden patches along the dock's front coping, the way the shipwrights walk"""
    for cx, cy, rx, ry in WORN:
        dx, dy = (mx - cx) / rx, (my - cy) / ry
        if dx * dx + dy * dy < 1.0 - 0.25 * math.sin(mx * 0.9 + my):
            return True
    return False

def _chips(mx, my):
    x0, x1, y0, y1 = SAWPIT
    if not (x0 - 6 < mx < x1 + 8 and y0 - 5 < my < y1 + 7):
        return False
    dx = max(x0 - mx, 0, mx - x1); dy = max(y0 - my, 0, my - y1)
    r = math.hypot(dx, dy)
    return hash2(int(mx * 2), int(my * 2), 13) < 0.22 * max(0.0, 1 - r / 6.0)

def tex_floor(mx, my, mz, n, st):
    """dock floor and altar treads: flags with seams; a wet patch below the weeping gate"""
    if n[2] > 0.5:
        if mz < FLOOR + 0.5:
            if mx > ENTR[0] - 9 and _puddle(mx, my):
                return 'wet'
            row = int((my - 20) // 3.1)
            off = 2.1 if row % 2 else 0.0
            if (my - 20) % 3.1 < 0.35 or _seam(mx + off, 7 + row % 3, 0.3):
                return 'stone%d' % max(0, st - 1)
            return 'stone%d' % st
        return 'stone%d' % (st - 1 if _seam(mx if abs(my - 47) > 15 else my, 8, 0.3) else st)
    return 'stone%d' % (st if ((mz - FLOOR) % 1.5) > 0.4 else max(0, st - 1))

def _puddle(mx, my):
    # below the mitre: a long irregular wet tongue running back from the gate
    t = (STOP - mx) / 10.0
    if t < -0.4 or t > 1.0:
        return False
    w = 2.2 * (1 - t) + 0.6 * math.sin(mx * 1.7)
    return abs(my - 47.3 - 0.8 * math.sin(mx * 0.6)) < max(0.0, w)

def tex_wall(mx, my, mz, n, st):
    """vertical stone walls of the dock entrance and canal: courses, a dark tide line"""
    a = my if abs(n[0]) > 0.5 else mx
    course = int((mz + 20) // 2)
    if mz < WATER + 0.7 and mz > WATER - 0.6:
        return 'stone%d' % max(0, st - 2)
    if (mz + 20) % 2 < 0.45 or _seam(a + course * 1.3, 9 + course % 3, 0.28):
        return 'stone%d' % max(0, st - 1)
    return 'stone%d' % st

def tex_water(mx, my, mz, n, st):
    if n[2] > 0.5:
        # dark canal: hand-placed ripple dashes along the flow (model y), shadow bands at the walls
        if mx < CANAL[0] + 0.7 or mx > CANAL[1] - 0.5:
            return 'water0'
        k = int(my // 3.0)
        lane = int((mx - CANAL[0]) // 1.0)
        h = hash2(lane, k, 21)
        if h < 0.09 and (my % 3.0) < 1.0 + 1.6 * hash2(lane, k, 22):
            return 'water3' if h < 0.025 else 'water2'
        return 'water1'
    return 'water0' if mz < -6 else 'water1'

def tex_boards(mx, my, mz, n, st, ramp='timber'):
    """boards: a seam every ~1.3 units up a wall, offset butts"""
    if n[2] > 0.5:
        return '%s%d' % (ramp, st)
    row = int((mz + 20) // 1.3)
    a = my if abs(n[0]) > 0.5 else mx
    if (mz + 20) % 1.3 < 0.3 or _seam(a + row * 2.3, row % 12, 0.22):
        return '%s%d' % (ramp, max(0, st - 1))
    return '%s%d' % (ramp, st)

def tex_timber(mx, my, mz, n, st):
    return tex_boards(mx, my, mz, n, st, 'timber')

def tex_endgrain(mx, my, mz, n, st):
    return 'timber%d' % (min(4, st + 1) if n[2] > 0.8 else st)

def tex_frame(mx, my, mz, n, st):
    """the bare frames: end grain lighter, a scarf line on a few futtocks"""
    if n[2] > 0.8:
        return 'oak%d' % min(4, st + 1)
    for xr, j in ((35.5, 3.2), (56.5, 6.0), (74.5, 4.5), (87.5, 7.0)):
        if abs(mx - xr) < 0.8 and abs(mz - j) < 0.32:
            return 'oak%d' % max(0, st - 1)
    return 'oak%d' % st

def tex_hull(mx, my, mz, n, st):
    """planked topsides over a tarred bottom: strakes follow the sheer, staggered butts, a wale"""
    S = SHIP
    u = float(S.u(mx)); uc = min(max(u, 0.0), 1.0)
    zs = float(S.zs(uc))
    if n[2] > 0.9 and mz > zs - 0.7:                       # the deck: calm, a step under the lit side
        k = int((my - S.yc + 30) // 2.9)
        if (my - S.yc + 30) % 2.9 < 0.35:
            return 'oak%d' % max(0, st - 2)
        return 'oak%d' % max(0, st - 1)
    if n[0] < -0.7 and u < 0.06:                            # the transom: lit stern windows
        if zs - 4.2 < mz < zs - 2.2:
            for wy in (-5.2, -1.6, 2.0):
                if wy < my - S.yc < wy + 2.4:
                    return 'win' if (my - S.yc - wy) % 2.4 > 0.5 else 'winD'
        return 'oak%d' % (st - 1 if (mz % 1.3) < 0.3 else st)
    if mz < S.zwl:
        return 'tar%d' % st
    if mz < S.zwl + 0.75:
        return 'trim%d' % st
    e = float(S.eta(uc, mz))
    if 0.80 <= e < 0.88:
        return 'oak%d' % max(0, st - 1) if e < 0.865 else 'oak%d' % min(4, st + 1)
    strake = int(e * 11)
    if (e * 11) % 1 < 0.16:
        return 'oak%d' % max(0, st - 1)
    if _seam(mx + strake * 4.7, strake % 12, 0.2):
        return 'oak%d' % max(0, st - 1)
    return 'oak%d' % st

def tex_roof(mx, my, mz, n, st):
    """shingle courses parallel to the ridge, offset joints, two patched shingles"""
    if abs(n[0]) < 0.3:                                     # the gable ends: boards
        return tex_boards(mx, my, mz, n, st)
    row = int((mz - 8) // 1.05)
    if (mz - 8) % 1.05 < 0.28:
        return 'timber%d' % max(0, st - 1)
    if _seam(my + row * 1.9, row % 12, 0.2):
        return 'timber%d' % max(0, st - 1)
    if row == 3 and 66.5 < my < 69.6:
        return 'timber%d' % min(4, st + 1)                  # the new shingles, still pale
    return 'timber%d' % st

def tex_hutwall(mx, my, mz, n, st):
    x, y, w, d = HUT
    if n[0] < -0.7:                                         # canal side: the shop window
        if 3.4 < mz < 7.0 and y + 5.0 < my < y + 10.4:
            if abs(my - (y + 7.7)) < 0.35 or abs(mz - 5.2) < 0.3:
                return 'timber0'
            return 'win' if (my - y - 5.0 + mz) % 4.0 > 0.6 else 'winD'
        if (3.0 < mz < 7.4 and y + 4.6 < my < y + 10.8):
            return 'timber%d' % min(4, st + 1)              # the frame
    if n[1] > 0.7:                                          # front: the door and a small window
        if mz < 6.6 and x + 2.0 < mx < x + 5.0:
            if abs(mx - (x + 3.5)) < 0.25 or mz > 6.2:
                return 'timber0'
            return 'timber%d' % max(0, st - 2)
        if 3.8 < mz < 6.4 and x + 6.6 < mx < x + 8.6:
            return 'win' if mz > 5.1 else 'winD'
    return tex_boards(mx, my, mz, n, st)

def tex_bark(mx, my, mz, n, st):
    if abs(n[0]) > 0.8:                                     # the sawn ends: pale rings
        return 'timber%d' % min(4, st + 1)
    if hash2(int(mx * 1.6), int((mz + my) * 2.0), 17) < 0.10:
        return 'timber%d' % max(0, st - 1)
    return 'timber%d' % st

def tex_canvas(mx, my, mz, n, st):
    if 72.0 < mx < 75.6 and 80.5 < my < 84.5 and n[2] > 0.5:   # the patch, stitched on in a darker cloth
        if abs(mx - 72.0) < 0.3 or abs(mx - 75.6) < 0.3 or abs(my - 80.5) < 0.3 or abs(my - 84.5) < 0.3:
            return 'canvas%d' % max(0, st - 2)
        return 'canvas%d' % max(0, st - 1)
    if abs(mx - 77.6) < 0.35:
        return 'ropeD'                                       # the lashing
    return 'canvas%d' % st

def tex_plank(mx, my, mz, n, st):
    """fresh-sawn boards: pale faces, paler end grain"""
    if n[2] > 0.8 or abs(n[0]) > 0.8:
        return 'timber%d' % min(4, st + 1)
    return 'timber%d' % st

# ================================================================ the scene
def origin(k, dy=26):
    xs, ys = [], []
    T = Turn(k)
    for x in (0, SX):
        for y in (0, SY):
            wx, wy = T.pt(x, y)
            for z in (0, -27):
                xs.append(2 * wx - 2 * wy); ys.append(wx + wy - z)
    ox = (W - (max(xs) + min(xs))) / 2.0
    oy = (H - (max(ys) + min(ys))) / 2.0 + dy
    return int(round(ox)), int(round(oy))

class Yard:
    def __init__(self, k, light, pal, stage, phase):
        global TURN, LIGHT
        TURN = Turn(k)
        LIGHT = np.array(light, float) / np.linalg.norm(light)
        self.k, self.stage, self.pal, self.phase = k, stage, pal, phase
        self.s = Iso(W, H, origin=origin(k), slots=list(pal.keys()))
        self.hero = set()
        self.tag = {}
        self.lamps = []                              # (model point, kind) for pools and reflections

    def _note(self, oid, hero, tag):
        if hero:
            self.hero.add(oid)
        if tag:
            self.tag.setdefault(tag, set()).add(oid)

    def box(self, X, Y, Z, w, d, h, mat, tex=None, lines=True, cast=True, hero=False, tag=None, bias=0):
        Xw, Yw, ww, dw = TURN.box(X, Y, w, d)
        faces = {}
        for key, nw in (('top', (0, 0, 1)), ('left', (0, 1, 0)), ('right', (1, 0, 0))):
            st = max(0, min(4, lstep(float(np.dot(nw, LIGHT))) + bias))
            nm = TURN.ivec(nw[0], nw[1]) + (nw[2],)
            if tex is None:
                faces[key] = '%s%d' % (mat, st)
                continue
            def f(u, v, t, face_step=2, W=None, H=None, key=key, st=st, nm=nm):
                if key == 'top':
                    px, py, pz = Xw + u, Yw + v, Z + h
                elif key == 'left':
                    px, py, pz = Xw + u, Yw + dw, Z + v
                else:
                    px, py, pz = Xw + ww, Yw + u, Z + v
                mx, my = TURN.inv(px, py)
                return tex(mx, my, pz, nm, st)
            faces[key] = f
        oid = self.s.box(Xw, Yw, Z, ww, dw, h, mat, top=faces['top'], left=faces['left'],
                         right=faces['right'], lines=lines, cast=cast)
        self._note(oid, hero, tag)
        return oid

    def solid(self, node, hero=False, lines=True, cast=True, tag=None, maxit=140):
        oid = self.s.solid(Rot(node), lines=lines, cast=cast, maxit=maxit)
        self._note(oid, hero, tag)
        return oid

    def sprite(self, grid, x, y, z, anchor=None, hero=False, tag=None, upright=True):
        wx, wy = TURN.pt(x, y)
        oid = self.s.sprite(grid, wx, wy, z, anchor=anchor, upright=upright)
        self._note(oid, hero, tag)
        return oid

    def to_screen(self, x, y, z):
        wx, wy = TURN.pt(x, y)
        return self.s.to_screen(wx, wy, z)

    def depth_of(self, x, y, z):
        wx, wy = TURN.pt(x, y)
        return float(self.s.view @ np.array([wx, wy, z], float))

# ---------------------------------------------------------------- the slab, dock and canal
def build_ground(Y):
    s = Y.box
    # underside tiers (a floating chunk, irregular insets)
    s(0, 0, -18, SX, SY, 8, 'soil', tex=tex_ground, tag='slab')
    s(5, 7, -23, 124, 86, 5, 'soil', tex=tex_ground, tag='slab')
    s(17, 15, -27, 96, 66, 4, 'soil', tex=tex_ground, tag='slab')
    s(104, 4, -21, 28, 9, 3, 'soil', tex=tex_ground, tag='slab')
    # the yard level (z -10 .. 0) around the dock, the entrance, the canal and the sawpit
    x0, x1, y0, y1 = DOCK
    for (a, b, c, d) in ((0, CANAL[0], 0, y0), (0, SAWPIT[0], y1, SY), (SAWPIT[0], SAWPIT[1], y1, SAWPIT[2]),
                         (SAWPIT[0], SAWPIT[1], SAWPIT[3], SY), (SAWPIT[1], CANAL[0], y1, SY), (0, x0, y0, y1),
                         (x1, CANAL[0], y0, ENTR[2]), (x1, CANAL[0], ENTR[3], y1), (CANAL[1], SX, 0, SY)):
        s(a, c, -10, b - a, d - c, 10, 'stone', tex=tex_ground, tag='slab')
    s(SAWPIT[0], SAWPIT[2], -10, SAWPIT[1] - SAWPIT[0], SAWPIT[3] - SAWPIT[2], 5.5, 'timber', tex=tex_chipfloor, tag='slab')
    # dock floor and altars
    s(x0, y0, -10, ENTR[1] - x0, y1 - y0, 10 + FLOOR, 'stone', tex=tex_floor, tag='dock')
    for i, (zt, wd) in enumerate(STEPS):
        off = sum(w for _, w in STEPS[:i])
        s(x0 + off, y0 + off, -10, x1 - x0 - off, wd, zt + 10, 'stone', tex=tex_floor, tag='dock')
        s(x0 + off, y1 - off - wd, -10, x1 - x0 - off, wd, zt + 10, 'stone', tex=tex_floor, tag='dock')
        s(x0 + off, y0 + off, -10, wd, y1 - y0 - 2 * off, zt + 10, 'stone', tex=tex_floor, tag='dock')
    # the canal: high water above the lock, low water below it, the dock mouth flooded to the stop-logs
    def lockline(x):
        return LOCK['ym'] + (LOCK['yh'] - LOCK['ym']) * np.abs(x - (CANAL[0] + CANAL[1]) / 2) / ((CANAL[1] - CANAL[0]) / 2)
    def upfn(x, y, z):
        return np.maximum.reduce([CANAL[0] - x, x - CANAL[1], -y, y - (lockline(x) - 0.9), z - WATER, -10 - z])
    def lowfn(x, y, z):
        return np.maximum.reduce([CANAL[0] - x, x - CANAL[1], (lockline(x) + 0.9) - y, y - SY, z - LOW, -10 - z])
    Y.solid(Field(upfn, (CANAL[0], 0, -10, CANAL[1], LOCK['yh'], WATER), M('water', tex_water)), cast=False,
            tag='water', lines=False, maxit=60)
    Y.solid(Field(lowfn, (CANAL[0], LOCK['ym'], -10, CANAL[1], SY, LOW), M('water', tex_water)), cast=False,
            tag='water', lines=False, maxit=60)
    s(STOP + 1.0, ENTR[2], -10, CANAL[0] - STOP - 1.0, ENTR[3] - ENTR[2], 10 + WATER, 'water', tex=tex_water,
      cast=False, tag='water')
    # stop-logs: horizontal timbers dropped in grooves across the mouth, holding the canal out
    s(STOP, ENTR[2], FLOOR, 1.4, ENTR[3] - ENTR[2], 0.4 - FLOOR, 'timber', tex=tex_stoplogs, tag='gate')

def tex_stoplogs(mx, my, mz, n, st):
    if n[2] > 0.5:
        return 'timber%d' % min(4, st + 1)
    k = int((mz - FLOOR) // 1.25)
    if (mz - FLOOR) % 1.25 < 0.3:
        return 'timber%d' % max(0, st - 1)
    if mz < WATER and mx > STOP + 0.7:
        return 'timber%d' % max(0, st - 2)
    return 'timber%d' % (st if k % 3 else max(0, st - 1) if n[0] > 0.5 else st)

def tex_chipfloor(mx, my, mz, n, st):
    if n[2] > 0.5:
        # sawdust: a pale heap under the cut, chips round it
        d = math.hypot((mx - 29.0) / 4.0, (my - 79.0) / 2.2)
        if d < 1.0:
            return 'timber%d' % min(4, st + 1 + (1 if d < 0.5 else 0))
        return 'timber%d' % (min(4, st + 1) if hash2(int(mx * 2), int(my * 2), 5) < 0.18 else max(0, st - 1))
    return tex_boards(mx, my, mz, n, st)

def build_gate(Y):
    """the canal lock: two mitred leaves meeting in a V that points upstream, balance beams on the banks"""
    xc = (CANAL[0] + CANAL[1]) / 2
    for side in (-1, 1):
        hinge = np.array([xc + side * (CANAL[1] - CANAL[0]) / 2, LOCK['yh']])
        mitre = np.array([xc, LOCK['ym']])
        Y.solid(Beam((hinge[0], hinge[1], -4.0), (mitre[0], mitre[1], -4.0), w=1.6, h=11.4,
                     mat=M('timber', tex_gate, bias=1)), tag='gate')
        d = hinge - mitre; d /= np.linalg.norm(d)
        far = hinge + d * 11.0
        Y.solid(Beam((mitre[0] + 0.0, mitre[1] + 0.2, 2.6), (far[0], far[1] + 0.3, 2.6), w=1.6, h=1.6,
                     mat=M('timber', tex_endgrain, bias=1)), tag='gate')                    # balance beam
        Y.solid(Beam((far[0], far[1] + 0.3, 0.0), (far[0], far[1] + 0.3, 1.8), w=1.0, h=1.0, mat=M('timber')),
                tag='gate', lines=False)                                                    # its rest post
        Y.solid(Beam((hinge[0], hinge[1] - 0.9, 1.75), (mitre[0], mitre[1] - 0.9, 1.75), w=1.1, h=0.4,
                     mat=M('timber')), tag='gate')                                          # walkway
        for f in (0.1, 0.55, 0.95):
            q = hinge + (mitre - hinge) * f
            Y.solid(Beam((q[0], q[1] - 1.4, 1.9), (q[0], q[1] - 1.4, 4.4), w=0.5, h=0.5, mat=M('timber')), tag='gate',
                    lines=False)
        Y.solid(Beam((hinge[0], hinge[1] - 1.4, 4.3), (mitre[0] - side * 0.3, mitre[1] - 1.4, 4.3), w=0.5, h=0.5,
                     mat=M('timber', bias=1)), tag='gate', lines=False)                     # handrail

def tex_gate(mx, my, mz, n, st):
    if mz < LOW + 0.2 and n[2] < 0.5:
        return 'timber%d' % max(0, st - 2)                # wet below the low water
    if (mz + 10) % 2.0 < 0.35:
        return 'timber%d' % max(0, st - 1)
    return 'timber%d' % st

# ---------------------------------------------------------------- the ship
def build_ship(Y, stage):
    S = SHIP
    # keel blocks: stacked, mismatched, hand-spaced
    for i, (bx, bw, bh2) in enumerate(((21, 3.0, 0.9), (30.5, 2.4, 1.1), (40, 3.4, 0.8), (49.5, 2.6, 1.2),
                                        (59, 3.0, 0.9), (68.5, 2.2, 1.0), (78, 3.2, 1.1), (87, 2.6, 0.7))):
        Y.box(bx, S.yc - 2.2, FLOOR, bw, 4.4, 2.0 - bh2 * 0.6, 'timber', tag='blocks')
        Y.box(bx + 0.3, S.yc - 1.6 + 0.3 * (i % 2), FLOOR + 2.0 - bh2 * 0.6, bw - 0.6, 3.2, bh2 * 0.6,
              'timber', tag='blocks')
    # the backbone: keel, stem and sternpost as one profile plate
    us = np.linspace(0.78, 1.0, 9)
    outer = [(S.x0 + S.L * u + 1.3 * (u - 0.78) / 0.22, float(S.zb(u)) - S.keel * (1 - (u - 0.78) / 0.22))
             for u in us]
    inner = [(S.x0 + S.L * u - 1.2, float(S.zb(u)) + 1.2) for u in us[::-1]]
    aft_top = float(S.zs(0.0)) + (4.5 if stage == 1 else 0.6)
    head = float(S.zs(1.0))
    pts = ([(S.x0 + 2.4, S.zk), (S.x0 + S.L * 0.78, S.zk)] + outer[1:] +
           [(S.x0 + S.L + 1.6, head + (4.0 if stage == 1 else 0.8)), (S.x0 + S.L - 0.8, head + (3.4 if stage == 1 else 1.0))] +
           inner[1:] + [(S.x0 + 3.6, S.zk + S.keel), (S.x0 + 1.2, aft_top - 0.5), (S.x0 - 0.6, aft_top),
                        (S.x0 + 0.6, S.zk + 2.0)])
    Y.solid(sdf.Plate(pts, y0=S.yc, t=1.0, mat=M('oak', tex_frame)), hero=True, tag='ship')
    if stage == 1:
        bb = S.bbox(top=3)
        Y.solid(Field(lambda x, y, z: S.frames_d(x, y, z, RIBS), bb, M('oak', tex_frame)), hero=True, tag='ship',
                maxit=220)
        Y.solid(Beam((S.x0 + 9, S.yc, S.zk + S.keel + 1.9), (S.x0 + S.L * 0.84, S.yc, S.zk + S.keel + 1.9),
                     w=1.3, h=1.1, mat=M('oak')), hero=True, tag='ship')
        # one sheer ribband each side, fastened along part of the run (the near one stops short)
        Y.solid(Field(lambda x, y, z: S.band_d(x, y, z, 0.93, 0.14, 0.70, side=-1), bb, M('oak', bias=1)),
                hero=True, tag='ship', maxit=200)
    else:
        Y.solid(Field(S.solid_d, S.bbox(), M('oak', tex_hull)), hero=True, tag='ship', maxit=200)
    # six shores from the dock floor to the bilge, each at its own angle
    for (xs_, side, zs_, lean) in ((26, 1, 3.0, 0.0), (49, 1, 4.5, 1.6), (73, 1, 4.0, -1.0),
                                   (36, -1, 3.5, 0.6), (60, -1, 4.5, -0.8), (84, -1, 3.0, 1.2)):
        u = float(S.u(xs_))
        yb = S.yc + side * (float(S.hb(u, zs_)) + 0.5)
        foot_y = (DOCK[3] - 7.4) if side > 0 else (DOCK[2] + 7.4)
        Y.solid(Beam((xs_ + lean, foot_y, FLOOR + 0.6), (xs_, yb, zs_), w=1.3, h=1.3,
                     mat=M('timber', tex_endgrain, bias=1)), tag='shore')
    if stage >= 3:
        Y.solid(Field(S.bulwark_d, S.bbox(top=3), M('oak', tex_hull)), hero=True, tag='ship', maxit=200)
        oid = Y.solid(Field(S.cap_d, S.bbox(top=4), M('oak', bias=1)), hero=True, tag='ship', maxit=200)
        Y.tag.setdefault('cap', set()).add(oid)
        z0 = float(S.zs(0.1))
        Y.box(S.x0 + 5, S.yc - 3.6, z0 - 0.5, 9, 7.2, 4.4, 'oak', tex=tex_house, hero=True, tag='ship')   # deckhouse
        Y.box(S.x0 + 4.6, S.yc - 4.0, z0 + 3.9, 9.8, 8.0, 0.7, 'oak', bias=1, hero=True, tag='ship')
        zh = float(S.zs(0.42))
        Y.box(S.x0 + 31, S.yc - 2.6, zh - 0.5, 6.5, 5.2, 1.6, 'oak', hero=True, tag='ship')               # hatch
        Y.solid(sdf.Cyl(S.x0 + 47.5, S.yc + 0.3, float(S.zs(0.59)) - 0.5, 1.0, hi=float(S.zs(0.59)) + 1.8,
                        mat=M('oak')), hero=True, tag='ship')                                              # capstan
    if stage >= 4:
        xm = S.x0 + S.L * 0.53
        zd = float(S.zs(0.53))
        Y.solid(sdf.Cyl(xm, S.yc, zd - 0.5, 0.95, hi=zd + 40, mat=M('oak', bias=0)), hero=True, tag='ship')
        Y.solid(sdf.Cyl(xm, S.yc, zd + 40, 0.6, hi=zd + 50, mat=M('oak')), hero=True, tag='ship')
        Y.box(xm - 1.4, S.yc - 1.4, zd + 38.5, 2.8, 2.8, 1.0, 'oak', hero=True, tag='ship')                 # top
        Y.solid(sdf.Cyl(xm + 0.9, zd + 31, None, 0.45, axis='y', y0=S.yc - 9.0, y1=S.yc + 9.0, mat=M('oak')),
                hero=True, tag='ship')                                                                       # yard
        Y.solid(sdf.RBox(xm + 0.3, S.yc - 8.0, zd + 29.4, xm + 2.2, S.yc + 8.0, zd + 31.0, r=0.7,
                         mat=M('canvas', bias=1)), hero=True, tag='ship')                                   # furled sail
        Y.solid(Beam((S.x0 + S.L - 0.5, S.yc, head + 0.4), (S.x0 + S.L + 13, S.yc, head + 4.5), w=0.9, h=0.9,
                     mat=M('oak')), hero=True, tag='ship')                                                   # bowsprit

def tex_house(mx, my, mz, n, st):
    S = SHIP
    z0 = float(S.zs(0.1))
    if n[1] > 0.7 or n[1] < -0.7:
        if z0 + 1.2 < mz < z0 + 3.0 and S.x0 + 7.0 < mx < S.x0 + 11.6:
            return 'win' if (mx - S.x0) % 2.3 > 0.5 else 'winD'
    if n[0] < -0.7 and mz < z0 + 3.4 and abs(my - S.yc) < 1.2:
        return 'oak%d' % max(0, st - 2)                     # the companion door
    return tex_boards(mx, my, mz, n, st, 'oak')

# ---------------------------------------------------------------- crane
def build_crane(Y, stage):
    c = CRANE
    x0, y0, w, h = c['x'], c['y'], c['w'], c['h']
    Y.box(x0 - 1.5, y0 - 1.5, 0, w + 3, w + 3, 2.2, 'stone', tex=tex_wall, tag='crane')     # footing
    posts = [(x0, y0), (x0 + w - 1.4, y0), (x0, y0 + w - 1.4), (x0 + w - 1.4, y0 + w - 1.4)]
    for (px, py) in posts:
        Y.box(px, py, 2.2, 1.4, 1.4, h - 2.2, 'timber', tex=tex_endgrain, tag='crane', lines=False)
    girts = [9.0, 18.5, 27.0, 37.0, h - 1.2]
    for z in girts:
        Y.box(x0, y0, z, w, 1.0, 1.0, 'timber', tag='crane', lines=False)
        Y.box(x0, y0 + w - 1.0, z, w, 1.0, 1.0, 'timber', tag='crane', lines=False)
        Y.box(x0, y0, z, 1.0, w, 1.0, 'timber', tag='crane', lines=False)
        Y.box(x0 + w - 1.0, y0, z, 1.0, w, 1.0, 'timber', tag='crane', lines=False)
    zz = [2.2] + girts
    for i in range(len(zz) - 1):
        a, b = zz[i] + 0.8, zz[i + 1]
        crook = 1.1 if i == 2 else 0.0            # the crooked brace, re-pinned off its line
        if i % 2 == 0:
            Y.solid(Beam((x0 + 0.7, y0 + w - 0.5, a), (x0 + w - 0.7, y0 + w - 0.5, b - crook),
                         w=0.8, h=0.8, mat=M('timber')), tag='crane', lines=False)
            Y.solid(Beam((x0 + w - 0.5, y0 + 0.7, b), (x0 + w - 0.5, y0 + w - 0.7, a), w=0.8, h=0.8,
                         mat=M('timber')), tag='crane', lines=False)
        else:
            Y.solid(Beam((x0 + w - 0.7, y0 + w - 0.5, a), (x0 + 0.7, y0 + w - 0.5, b), w=0.8, h=0.8,
                         mat=M('timber')), tag='crane', lines=False)
            Y.solid(Beam((x0 + w - 0.5, y0 + 0.7, a), (x0 + w - 0.5, y0 + w - 0.7, b), w=0.8, h=0.8,
                         mat=M('timber')), tag='crane', lines=False)
    Y.box(x0 - 0.8, y0 - 0.8, h, w + 1.6, w + 1.6, 1.2, 'timber', tex=tex_endgrain, tag='crane')   # cap
    # the jib: two chords laddered with spacers, from a pivot low on the mast out over the dock
    piv = np.array([x0 + w / 2, y0 + w, 7.0])
    tip = np.array([x0 + w / 2 + 2.0, 31.5, 33.0])
    for dx in (-1.1, 1.1):
        Y.solid(Beam(piv + [dx, 0, 0], tip + [dx * 0.55, 0, 0], w=1.0, h=1.4, mat=M('timber', tex_endgrain)),
                tag='crane', lines=False)
    for f in (0.12, 0.3, 0.47, 0.63, 0.8, 0.95):
        p = piv + (tip - piv) * f
        Y.solid(Beam(p + [-1.1 + 0.5 * f, 0, 0], p + [1.1 - 0.5 * f, 0, 0], w=0.7, h=0.7, mat=M('timber')),
                tag='crane', lines=False)
    Y.solid(Beam((x0 + w / 2, y0 + w - 0.5, h + 0.5), tip + [0, -0.6, 0.7], w=0.8, h=0.8, mat=M('timber')),
            tag='crane', lines=False)
    Y.box(tip[0] - 1.2, tip[1] - 1.0, tip[2] - 0.6, 2.4, 2.0, 1.4, 'timber', tag='crane', lines=False)   # sheave head
    Y.solid(sdf.Cyl(y0 - 2.4, 3.6, None, 1.3, axis='x', x0=x0 - 0.5, x1=x0 + w + 0.5, mat=M('timber')),
            tag='crane')                                                                              # winch drum
    for xx in (x0 - 0.8, x0 + w + 0.4):
        Y.box(xx, y0 - 3.4, 0, 0.5, 2.0, 4.9, 'timber', tag='crane', lines=False)
    return tip

# ---------------------------------------------------------------- the yard's other things
def build_props(Y, stage, phase):
    b = Y.box
    # --- sawpit: trestles across the pit, the log (sawn into boards by turn 4), the pit saw
    for tx in (22.0, 35.5):
        b(tx, SAWPIT[2] - 1.0, 2.4, 1.3, SAWPIT[3] - SAWPIT[2] + 2.0, 1.0, 'timber', tex=tex_endgrain, tag='saw')
        for ly, dyf in ((SAWPIT[2] - 0.6, -1.0), (SAWPIT[3] + 0.6, 1.0)):
            Y.solid(Beam((tx + 0.65, ly, 2.4), (tx + 0.65 + 0.8, ly + dyf * 0.9, 0.0), w=0.6, h=0.6, mat=M('timber')),
                    tag='saw', lines=False)
            Y.solid(Beam((tx + 0.65, ly, 2.4), (tx + 0.65 - 0.8, ly + dyf * 0.9, 0.0), w=0.6, h=0.6, mat=M('timber')),
                    tag='saw', lines=False)
    if stage == 1:
        Y.solid(sdf.Cyl(79.0, 5.3, None, 1.9, axis='x', x0=18.5, x1=40.5, mat=M('timber', tex_bark)), tag='saw')
        Y.solid(Beam((30.0, 79.0, -1.5), (30.0, 79.0, 11.5), w=0.3, h=1.4, mat=M('stone', bias=1)), tag='saw',
                lines=False)                                                                              # blade
        Y.solid(Beam((30.0, 77.4, 11.5), (30.0, 80.6, 11.5), w=0.6, h=0.6, mat=M('timber')), tag='saw', lines=False)
    else:
        for i, (zz, ww) in enumerate(((3.4, 3.4), (4.1, 3.0), (4.8, 3.2))):
            b(18.8 + 0.4 * i, 77.3 + 0.2 * i, zz, 21.5 - 0.6 * i, ww, 0.7, 'timber', tex=tex_endgrain, tag='saw')
        Y.solid(Beam((40.6, 82.2, 0.0), (41.6, 79.8, 9.5), w=0.3, h=1.4, mat=M('stone', bias=1)), tag='saw',
                lines=False)
    # off-cuts: a pile of short ends, all different
    for (ox, oy, oz, ow, od, oh) in ((40.5, 85.0, 0, 3.1, 1.2, 0.8), (41.2, 86.4, 0, 2.2, 1.0, 0.7),
                                     (40.0, 86.0, 0.8, 1.6, 1.1, 0.7), (43.2, 85.4, 0, 1.3, 2.0, 0.9),
                                     (42.0, 84.4, 0.8, 2.6, 0.9, 0.6)):
        b(ox, oy, oz, ow, od, oh, 'timber', tex=tex_endgrain, tag='saw')
    # --- the plank stack on three bearers: stickered layers, uneven boards, one board askew
    for bx in (49.0, 61.5, 73.0):
        b(bx, 76.8, 0, 1.5, 10.6, 1.1, 'timber', tag='stack')
    layers = 4 if stage == 1 else 2
    z = 1.1
    for L_ in range(layers):
        for j_, (py, pw) in enumerate(((77.6, 2.4), (80.5, 2.2), (83.2, 2.5))):
            xs0 = 46.5 + 3.6 * hash2(L_, j_, 41)
            ln = 22.0 + 9.0 * hash2(L_, j_, 42)
            if L_ == layers - 1 and j_ == 1:
                continue                                   # a board already taken from the top
            b(xs0, py, z, ln, pw, 1.0, 'timber', tex=tex_plank, tag='stack')
        z += 1.0
        for sx_ in (50.0, 61.8, 73.4):
            b(sx_ + 0.7 * hash2(L_, 1, 43), 76.9, z, 0.8, 10.4, 1.0, 'timber', bias=-1, tag='stack', lines=False)
        z += 1.0
    Y.solid(Beam((50.0, 80.0, z + 0.5), (76.0, 82.6, z + 2.6), w=2.3, h=1.0, mat=M('timber', tex_plank)),
            tag='stack')                                                                    # the askew, sprung board
    # --- the logs, waiting at the back
    for (lx0, lx1, ly, lz, r) in ((64.0, 90.0, 6.0, 0.0, 1.7), (66.5, 93.0, 9.6, 0.0, 1.9), (63.0, 88.0, 13.3, 0.0, 1.6),
                                  (65.5, 91.0, 7.9, 3.1, 1.5), (64.5, 89.5, 11.5, 3.3, 1.6)):
        Y.solid(sdf.Cyl(ly, lz + r, None, r, axis='x', x0=lx0, x1=lx1, mat=M('timber', tex_bark)), tag='logs')
    b(62.0, 4.0, 0, 1.0, 11.5, 1.2, 'timber', tag='logs')
    # --- turn 1: the next frame waits on two blocks, laid flat
    if stage == 1:
        S = SHIP
        zs_ = np.linspace(float(S.zb(0.5)), float(S.zs(0.5)) + 0.8, 10)
        outer = [(16.0 + (zz - zs_[0]) * 1.0, float(S.hb(0.5, zz))) for zz in zs_]
        pts = ([(x_, 14.0 + y_) for x_, y_ in outer[::-1]] + [(16.0, 14.0)] +
               [(x_, 14.0 - y_) for x_, y_ in outer] +
               [(x_, 14.0 - max(0.0, y_ - 1.5)) for x_, y_ in outer[::-1]] +
               [(x_, 14.0 + max(0.0, y_ - 1.5)) for x_, y_ in outer])
        Y.solid(Swap(sdf.Plate([(p[0], p[1]) for p in pts], y0=1.9, t=0.6, mat=M('timber', tex_plank)), 'yz'),
                tag='frame')
        b(19.0, 5.5, 0, 2.0, 17.0, 1.3, 'timber', tag='frame')
        b(29.0, 6.0, 0, 2.2, 16.0, 1.3, 'timber', tag='frame')
    # --- the tar pot on its tripod by the dock coping
    tp = (84.0, 72.0)
    for ang in (0.3, 2.4, 4.3):
        Y.solid(Beam((tp[0] + 2.2 * math.cos(ang), tp[1] + 2.2 * math.sin(ang), 0.0), (tp[0], tp[1], 6.2), w=0.5, h=0.5,
                     mat=M('timber')), tag='tar', lines=False)
    Y.solid(sdf.Cyl(tp[0], tp[1], 1.4, 1.3, hi=3.4, mat=M('stone', bias=-1)), tag='tar')
    # --- the far bank: the chandlery, its landing stage, barrels, a coil of rope, the dory
    hx, hy, hw, hd = HUT
    b(hx, hy, 0, hw, hd, 9.0, 'timber', tex=tex_hutwall, tag='hut')
    roof = [(hx - 1.0, 8.6), (hx + hw / 2, 15.0), (hx + hw + 1.0, 8.6), (hx + hw + 1.0, 7.9), (hx + hw / 2, 14.2),
            (hx - 1.0, 7.9)]
    Y.solid(sdf.Plate(roof, y0=hy + hd / 2, t=hd / 2 + 0.9, mat=M('timber', tex_roof, bias=1)), tag='hut')
    Y.solid(sdf.Plate([(hx, 9.0), (hx + hw / 2, 14.4), (hx + hw, 9.0)], y0=hy + hd / 2, t=hd / 2 - 0.2,
                      mat=M('timber', tex_boards)), tag='hut')
    Y.solid(sdf.Cyl(hx + 7.6, hy + 4.0, 11.0, 0.6, hi=17.4, mat=M('stone', bias=-1)), tag='hut', lines=False)
    Y.stovepipe = (hx + 7.6, hy + 4.0, 17.4)
    b(CANAL[1] - 3.6, hy + 11.5, -1.2, 3.8, 6.0, 0.6, 'timber', tex=tex_endgrain, tag='hut')          # landing stage
    for (px, py) in ((CANAL[1] - 3.4, hy + 11.7), (CANAL[1] - 3.4, hy + 16.6)):
        b(px, py, -6.0, 0.8, 0.8, 7.6, 'timber', tag='hut', lines=False)
    for (bx_, by_, r) in ((hx + 8.2, hy + hd + 1.6, 1.1), (hx + 6.0, hy + hd + 2.1, 1.0)):
        Y.solid(sdf.Cyl(bx_, by_, 0.0, r, hi=2.7, mat=M('timber', tex_endgrain)), tag='hut')
    b(hx + 1.2, hy + hd + 1.0, 0, 2.4, 2.2, 2.0, 'timber', tex=tex_endgrain, tag='hut')               # crate
    Y.solid(sdf.Cyl(CANAL[1] + 1.4, hy - 3.0, 0.0, 1.2, hi=0.7, mat=M('rope_', None) if False else M('timber', bias=1)),
            tag='hut')
    for by_ in (18.0, 41.0, 84.0):                                                                    # bollards
        Y.solid(sdf.Cyl(CANAL[1] + 1.1, by_, 0.0, 0.7, hi=1.6, mat=M('stone', bias=-1)), tag='hut')
    dory = Ship(x0=hy - 4.0, L=14.0, yc=CANAL[1] - 4.6, zk=WATER - 1.2, B=2.4, D=2.6, sa=0.8, sf=1.2, wl=1.0)
    Y.solid(Swap(Field(dory.open_d, dory.bbox(pad=0.5, top=1), M('timber', tex_endgrain)), 'xy'), tag='dory',
            maxit=200)


# ---------------------------------------------------------------- finishing passes (screen space)
def _shade_slot(v, k, slots_ok):
    if isinstance(v, str) and v[-1:].isdigit():
        base = v.rstrip('0123456789'); n = int(v[len(base):])
        v2 = '%s%d' % (base, max(0, min(4, n + k)))
        return v2 if v2 in slots_ok else v
    return v

def line3(Y, slots, p0, p1, slot, gap=0.8):
    """a 1 px rope between two model points, hidden where something stands in front of it"""
    (ax, ay), (bx, by) = Y.to_screen(*p0), Y.to_screen(*p1)
    d0, d1 = Y.depth_of(*p0), Y.depth_of(*p1)
    pts = artlib.line(int(math.floor(ax)), int(math.floor(ay)), int(math.floor(bx)), int(math.floor(by)))
    n = max(1, len(pts) - 1)
    for i, (x, y) in enumerate(pts):
        dep = d0 + (d1 - d0) * i / n
        if 0 <= x < W and 0 <= y < H and dep >= Y.s.depth[y, x] - gap:
            slots[y, x] = slot
            Y.s.depth[y, x] = max(Y.s.depth[y, x], dep)

def stamp(Y, slots, rows, key, x, y, anchor, depth=None, hero=False):
    """a hand-typed slot map at a screen point, depth-tested against the scene"""
    ax, ay = anchor
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c == '.':
                continue
            X, Yy = int(x) - ax + i, int(y) - ay + j
            if 0 <= X < W and 0 <= Yy < H and (depth is None or depth >= Y.s.depth[Yy, X] - 0.8):
                slots[Yy, X] = key[c]
                if hero:
                    Y.s.obj[Yy, X] = next(iter(Y.hero))

BLOCK_OLD = ["..o..", ".oSo.", "oSTTo", "oTkto", "oTTto", "ottto", ".ooo.", "..i..", "..i..", ".i.i.", "..ii."]


LANTERN = [".o.", "ooo", "oHo", "ohH", "oHo", "ooo"]       # bail, cap, glass round a hot core

def night_lights(Y, slots):
    """lanterns as warm slot maps, hand-shaped pools in palette steps, their reflections on the canal"""
    S = SHIP
    s = Y.s
    ok = set(Y.pal.keys())
    head = float(S.zs(1.0))
    lamps = [((S.x0 + 1.4, S.yc, float(S.zs(0.0)) + 6.2), 'H', 6.0, 4.0),          # stern lantern on its post
             ((S.x0 + S.L - 2.6, S.yc - 0.6, head + 4.4), 'H', 5.0, 3.5),          # bow lantern on the stem head
             ((CRANE['x'] + CRANE['w'] / 2, CRANE['y'] + CRANE['w'] + 0.7, 9.0), 'A', 6.5, 4.5)]  # crane
    # the stern lantern's post and the bow lantern's crook
    line3(Y, slots, (S.x0 + 1.4, S.yc, float(S.zs(0.0)) + 2.6), (S.x0 + 1.4, S.yc, float(S.zs(0.0)) + 5.0), 'oak1')
    # pools: warm steps on whatever lies under each lantern, an irregular lobed outline
    W_, H_ = s.W, s.H
    m = (s.obj >= 0) & (s.face == 1)
    ys, xs = np.nonzero(m)
    wx, wy, wz = s.world[ys, xs, 0], s.world[ys, xs, 1], s.world[ys, xs, 2]
    mx, my = TURN.inv(wx, wy)
    for (p, kind, rx, ry) in lamps:
        dx, dy = (mx - p[0]), (my - p[1])
        ang = np.arctan2(dy, dx)
        lobe = 1.0 + 0.18 * np.sin(3 * ang + 1.3) + 0.12 * np.sin(5 * ang + 0.4)
        r = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2) / lobe
        near = (wz <= p[2] - 1.0) & (wz >= p[2] - 26)
        for k in np.nonzero((r < 1.0) & near)[0]:
            v = slots[ys[k], xs[k]]
            if not isinstance(v, str) or not v[-1:].isdigit():
                continue
            base = v.rstrip('0123456789'); n = int(v[len(base):])
            warm = {'stone': 'stoneW', 'oak': 'oakW', 'timber': 'timberW'}.get(base)
            if warm is None:
                continue
            n2 = min(4, n + (1 if r[k] < 0.5 else 0))
            slots[ys[k], xs[k]] = '%s%d' % (warm, n2)
    for (p, kind, rx, ry) in lamps:
        sx, sy = Y.to_screen(*p)
        key = {'o': 'ol', 'H': 'lamp%s2' % kind, 'h': 'lamp%s' % kind}
        stamp(Y, slots, LANTERN, key, sx, sy, (1, 3), depth=Y.depth_of(*p) + 0.5)
    # the shop window's broken reflection: a column of short dashes on the high water below it
    hx, hy, hw, hd = HUT
    for wy_, seed in ((hy + 6.4, 0), (hy + 9.0, 1)):
        sx, sy = Y.to_screen(hx - 0.1, wy_, WATER)
        for j, (wd, sl) in enumerate(((3, 'refl1'), (2, 'refl1'), (3, 'refl0'), (2, 'refl1'), (2, 'refl0'),
                                      (1, 'refl0'), (2, 'refl0'))):
            Yy = int(sy) + 1 + 2 * j
            X0 = int(sx) - 1 - (1 if (j + seed) % 3 == 0 else 0)
            for X in range(X0, X0 + wd):
                if 0 <= X < W and 0 <= Yy < H and isinstance(slots[Yy, X], str) and slots[Yy, X].startswith('water'):
                    slots[Yy, X] = sl
    # the landing stage catches the window spill
    for (yy, xx) in zip(*np.nonzero(np.isin(s.obj, list(Y.tag.get('hut', ()))))):
        v = slots[yy, xx]
        P = s.world[yy, xx]; qx, qy = TURN.inv(float(P[0]), float(P[1]))
        if isinstance(v, str) and v.startswith('timber') and v[-1:].isdigit() and qx < hx - 0.2 and hy + 10 < qy < hy + 18 and P[2] < 0.5:
            slots[yy, xx] = 'timberW%s' % min(4, int(v[-1]) + 1)

PEN_TOP = ["oPPPPPPPPp", "oPPPPp...."]
PEN_YARD = ["oPPPPp", "oPp..."]

def rigging(Y, slots):
    S = SHIP
    xm = S.x0 + S.L * 0.53
    zd = float(S.zs(0.53))
    head = float(S.zs(1.0))
    top = (xm, S.yc, zd + 38.8)
    sprit = (S.x0 + S.L + 13, S.yc, head + 4.5)
    line3(Y, slots, (xm + 0.3, S.yc, zd + 49.5), sprit, 'ropeD')                       # forestay
    line3(Y, slots, (xm - 0.3, S.yc, zd + 49.0), (S.x0 + 1.0, S.yc, float(S.zs(0.0)) + 2.6), 'ropeD')  # backstay
    for side in (-1, 1):
        for dx in (-3.6, -1.6, 0.6):
            u = float(S.u(xm + dx)); zr = float(S.zs(u)) + 2.5
            line3(Y, slots, top, (xm + dx, S.yc + side * (float(S.hb(u, zr - 2.5)) - 0.2), zr), 'ropeD')
    sx, sy = Y.to_screen(xm, S.yc, zd + 50.2)
    stamp(Y, slots, PEN_TOP, {'o': 'ol', 'P': 'pen', 'p': 'penD'}, sx, sy, (0, 0))
    sx, sy = Y.to_screen(xm + 0.9, S.yc - 9.0, zd + 31.6)
    stamp(Y, slots, PEN_YARD, {'o': 'ol', 'P': 'pen', 'p': 'penD'}, sx, sy, (0, 1))

BLOCK = ["..o..", ".oSo.", "oSTTo", "oTkto", "oTTto", "ottto", ".ooo.", "..i..", "..i..", ".i.i.", "..ii."]

def finish(Y, slots, phase):
    pal = Y.pal
    ok = set(pal.keys())
    s = Y.s
    hero = np.isin(s.obj, list(Y.hero))
    lit_left = lstep(float(LIGHT[1])) >= 3                     # which side faces take the light
    litface = 2 if lit_left else 3
    # lit rims: the top-face edge over a lit side face, one step up (scenery only)
    below_obj = np.full_like(s.obj, -1); below_obj[:-1] = s.obj[1:]
    below_face = np.zeros_like(s.face); below_face[:-1] = s.face[1:]
    m = (s.face == 1) & (below_obj == s.obj) & (below_face == litface) & ~hero & (s.obj >= 0)
    for yy, xx in zip(*np.nonzero(m)):
        slots[yy, xx] = _shade_slot(slots[yy, xx], 1, ok)
    # spec strokes: 1 px white on the hero's upper edges and the edges toward the light
    isl = np.vectorize(lambda v: isinstance(v, str) and v in ('oak4', 'oak3', 'oak2'))(slots) & hero
    top4 = np.vectorize(lambda v: v in ('oak4', 'oak3'))(slots) & hero
    up = np.zeros_like(hero); up[1:] = ~hero[:-1]
    sd = np.zeros_like(hero)
    if lit_left:
        sd[:, 1:] = ~hero[:, :-1]
    else:
        sd[:, :-1] = ~hero[:, 1:]
    m = (isl & up) | (top4 & sd)
    cap = np.isin(s.obj, list(Y.tag.get('cap', ())))
    capu = np.zeros_like(cap); capu[1:] = ~cap[:-1]
    m |= cap & capu & (s.face == 1)
    slots[m] = 'spec'
    # the crane's hoist: rope from the sheave head to the block, a back rope to the winch
    tip = Y.jib
    zb = 19.0 if Y.stage == 1 else 23.0
    line3(Y, slots, (tip[0], tip[1], tip[2] - 0.7), (tip[0], tip[1], zb + 1.0), 'rope')
    line3(Y, slots, (tip[0] - 0.6, tip[1] - 0.8, tip[2] - 0.2), (CRANE['x'] + 1.0, CRANE['y'] - 2.4, 4.6), 'ropeD')
    bx, by = Y.to_screen(tip[0], tip[1], zb)
    stamp(Y, slots, BLOCK, {'o': 'ol', 'S': 'trim3', 'T': 'trim2', 't': 'trim1', 'k': 'ol', 'i': 'ironL'},
          bx, by, (2, 1), depth=Y.depth_of(tip[0], tip[1], zb))
    if phase == 'night':
        if Y.stage >= 4:
            rigging(Y, slots)
        night_lights(Y, slots)
    if phase == 'dawn':
        # the chandler is up: a thin smoke from the stovepipe, leaning off on the morning air
        px, py = Y.to_screen(*Y.stovepipe)
        plume = ["..........sss..",
                 "........sssssss",
                 "......sssssoo..",
                 ".....sssoo.....",
                 "....ssoo.......",
                 "...ssoo........",
                 "...so..........",
                 "..sso..........",
                 "..so...........",
                 ".so............",
                 ".so............",
                 "so.............",
                 "so............."]
        stamp(Y, slots, plume, {'s': 'smoke1', 'o': 'smoke0'}, px, py, (0, len(plume)))
    return slots

# ---------------------------------------------------------------- render
SUN = {'dawn': (-0.45, 0.8, 0.42), 'night': (0.85, -0.3, 0.55)}

def render(turn, stage, phase):
    pal = dawn_palette() if phase == 'dawn' else night_palette()
    Y = Yard(turn, SUN[phase], pal, stage, phase)
    build_ground(Y)
    build_gate(Y)
    build_ship(Y, stage)
    Y.jib = build_crane(Y, stage)
    build_props(Y, stage, phase)
    Y.s.cast_shadows(sun=tuple(LIGHT), step=-2, reach=260)
    g = Y.s.render(outline=True, rim=False, between=True, ol='ol')
    slots = np.array(g.a, object)
    slots[slots == None] = 'void'
    slots = finish(Y, slots, phase)
    return Y, slots, pal

def to_image(slots, pal):
    keys = sorted(set(slots.ravel()))
    lut = {k: cl.hex_to_rgb(pal[k]) for k in keys}
    idx = {k: i for i, k in enumerate(keys)}
    arr = np.array([lut[k] for k in keys], np.uint8)
    ix = np.vectorize(idx.get)(slots)
    return Image.fromarray(arr[ix], 'RGB')

def hero_bbox(Y):
    m = np.isin(Y.s.obj, list(Y.hero))
    ys, xs = np.nonzero(m)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

def export():
    """the two stills: 1x, 3x nearest, the palette as JSON, and the hero's mask for the gate"""
    OUT.mkdir(exist_ok=True)
    for name, (turn, stage, phase) in (('07-a', (0, 1, 'dawn')), ('07-b', (3, 4, 'night'))):
        Y, slots, pal = render(turn, stage, phase)
        im = to_image(slots, pal)
        im.save(OUT / ('%s@1x.png' % name))
        im.resize((W * 3, H * 3), Image.NEAREST).save(OUT / ('%s.png' % name))
        used = sorted(set(slots.ravel()))
        json.dump({k: pal[k] for k in sorted(pal)}, open(OUT / ('%s-palette.json' % name), 'w'), indent=1)
        hero = np.isin(Y.s.obj, list(Y.hero))
        Image.fromarray((hero * 255).astype(np.uint8), 'L').save(OUT / ('%s-hero.png' % name))
        print(name, 'hero bbox', hero_bbox(Y), 'slots used', len(used), 'of', len(pal))

if __name__ == '__main__':
    import time
    t0 = time.time()
    which = sys.argv[1] if len(sys.argv) > 1 else 'a'
    if which == 'export':
        export(); sys.exit(0)
    if which == 'a':
        Y, slots, pal = render(0, 1, 'dawn')
    else:
        Y, slots, pal = render(3, 4, 'night')
    im = to_image(slots, pal)
    OUT.mkdir(exist_ok=True)
    im.save(OUT / ('draft-%s@1x.png' % which))
    im.resize((W * 3, H * 3), Image.NEAREST).save(OUT / ('draft-%s.png' % which))
    print('hero bbox', hero_bbox(Y), 'done', round(time.time() - t0, 1))
