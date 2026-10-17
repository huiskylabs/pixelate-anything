"""Signal from Tidewater: the J-card cover stills, 270x480 native, 4x nearest to 1080x1920.

A  "The radio in the storm": night, inside the keeper's room. A valve radio with a cassette deck
   sits on the windowsill, its dial the only warm light; through the sash window the storm, the
   heaving sea and, far out on its rock, the lighthouse whose beam ends at the radio's bent antenna.
B  "Lightning": the same frame at the strike: the window slots swap to palette.flash (cold
   white-blue), the lighthouse and its rock drop to a hard silhouette, the beam washes out, a bolt
   forks into the sea, every room edge facing the glass takes a cold rim; the dial stays warm.

Everything is a slot map drawn here: hand-placed parts, hand-listed crests and drops, seeded cloud
masses, hashed rain. Lofi rules: one strict palette per image, palette-step light, no post ops.
"""
import sys, json, math, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from PIL import Image
import palette, shapes, pixfont
from canvas import Canvas

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / 'out'
W, H, SCALE = 270, 480, 4
HZ = 236                       # horizon row (first sea row)
GX0, GX1, GY1 = 30, 247, 333   # the glass, inclusive
YY, XX = np.mgrid[0:H, 0:W]

# ------------------------------------------------------------------ palette (A), OKLCh roles
LCH = {
    # storm sky: slate teal-blue, darks cooler
    'S0': (.165, .030, 262), 'S1': (.205, .034, 256), 'S2': (.250, .036, 248), 'S3': (.305, .036, 240),
    'S4': (.375, .034, 230), 'S5': (.455, .030, 220),
    # sea: deep teal, darker toward the viewer
    'E0': (.135, .028, 238), 'E1': (.170, .032, 232), 'E2': (.215, .034, 226), 'E3': (.275, .034, 218),
    'E4': (.345, .032, 210), 'E5': (.425, .028, 204),
    # rain and foam: pale cool greys
    'N0': (.400, .022, 228), 'N1': (.500, .022, 222), 'N2': (.620, .020, 214), 'N3': (.730, .016, 205),
    # the lighthouse beam and lamp: pale lamp white, low chroma
    'B1': (.520, .028, 105), 'B2': (.610, .030, 100), 'B3': (.710, .032, 95), 'LP': (.860, .055, 92),
    # far rock and tower
    'R0': (.120, .018, 255), 'R1': (.170, .020, 250), 'R2': (.230, .020, 244), 'R3': (.300, .020, 236),
    # room darks: blue-violet, lights turn warm
    'K0': (.110, .022, 285), 'K1': (.140, .026, 292), 'K2': (.175, .028, 305), 'K3': (.220, .028, 330),
    # worn window paint: blue-grey
    'F0': (.150, .022, 255), 'F1': (.200, .026, 248), 'F2': (.255, .027, 240), 'F3': (.320, .025, 232),
    'F4': (.400, .022, 224),
    # radio cabinet: honey teak
    'W0': (.150, .032, 38), 'W1': (.215, .045, 45), 'W2': (.280, .056, 52), 'W3': (.345, .064, 58),
    'W4': (.420, .070, 64), 'W5': (.505, .074, 72),
    # oak sill
    'O0': (.165, .028, 50), 'O1': (.225, .036, 58), 'O2': (.290, .044, 64), 'O3': (.365, .052, 70),
    'O4': (.445, .058, 76), 'O5': (.530, .060, 82),
    # brass
    'A0': (.330, .050, 70), 'A1': (.470, .075, 80), 'A2': (.610, .085, 88),
    # the dial: amber to cream (peak value and peak chroma)
    'Y0': (.400, .100, 48), 'Y1': (.540, .140, 58), 'Y2': (.680, .160, 68), 'Y3': (.810, .125, 80),
    'Y4': (.925, .065, 92),
    # dull red: the dial pointer, the VU red zone, the pencil eraser
    'Q0': (.430, .130, 28),
    # speaker cloth
    'C0': (.120, .018, 45), 'C1': (.160, .022, 50), 'C2': (.205, .026, 55),
    # cassette charcoal
    'T0': (.110, .010, 260), 'T1': (.170, .012, 255), 'T2': (.235, .014, 250), 'T3': (.320, .014, 245),
    # paper: logbook pages, cassette label, spool hubs
    'P0': (.360, .025, 75), 'P1': (.470, .030, 80), 'P2': (.580, .034, 85), 'P3': (.680, .034, 90),
    # enamel mug and its navy rim
    'U0': (.240, .022, 250), 'U1': (.330, .020, 245), 'U2': (.430, .018, 240), 'U3': (.530, .016, 235),
    'V0': (.180, .045, 265), 'V1': (.250, .055, 262),
    # logbook cloth: bottle green
    'G0': (.150, .028, 170), 'G1': (.205, .034, 165), 'G2': (.265, .038, 160),
    # masking tape on the cracked pane (backlit)
    'M0': (.420, .028, 80), 'M1': (.520, .030, 85),
    # title lettering (quiet, never brighter than the dial)
    'L0': (.500, .020, 225), 'L1': (.700, .022, 85),
    # flash rims (B): in A they are the paint's cool edge steps
    'X0': (.320, .025, 232), 'X1': (.400, .022, 224),
    # the bolt (B only; in A it sits in the palette unused)
    'Z0': (.970, .020, 250),
}
PAL_A = {k: palette.from_lch(*v) for k, v in LCH.items()}

# the window: every slot that is outside the glass (or on it) blows out in the flash
WINDOW = [k for k in PAL_A if k[0] in 'SENBM' and k != 'LP'] + ['LP']
def flash_palette():
    sky = palette.flash({k: PAL_A[k] for k in PAL_A if k[0] in 'SB' or k in ('LP',)}, colour='#e6efff', amount=0.62, lift=0.615)
    sea = palette.flash({k: PAL_A[k] for k in PAL_A if k[0] == 'E'}, colour='#dce8ff', amount=0.55, lift=0.42)
    rain = palette.flash({k: PAL_A[k] for k in PAL_A if k[0] in 'NM'}, colour='#f0f6ff', amount=0.6, lift=0.55)
    pb = dict(PAL_A)
    pb.update(sky); pb.update(sea); pb.update(rain)
    pb['X0'] = palette.from_lch(.640, .030, 242)
    pb['X1'] = palette.from_lch(.790, .028, 246)
    return pb

# ------------------------------------------------------------------ hashing, noise, stamps
def hsh(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 15; h = (h * 2246822519) & 0xFFFFFFFF; h ^= h >> 13
    return (h & 0xFFFFFF) / 16777216.0

def vn(x, cell, seed):
    if isinstance(x, np.ndarray):
        return np.vectorize(lambda v: vn(float(v), cell, seed))(x)
    i = math.floor(x / cell); f = x / cell - i
    s = f * f * (3 - 2 * f)
    return (hsh(i, seed) * (1 - s) + hsh(i + 1, seed) * s) * 2 - 1

def stamp(c, art, key, ox, oy, mask=None):
    rows = [r for r in art.strip('\n').split('\n')]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in '. ':
                continue
            c.put(ox + i, oy + j, key[ch])
            if mask is not None and 0 <= oy + j < H and 0 <= ox + i < W:
                mask[oy + j, ox + i] = True

def rect(c, x0, y0, x1, y1, v):           # inclusive
    c.g[max(0, y0):y1 + 1, max(0, x0):x1 + 1] = v

def edge_px(m, d):
    """pixels of mask m whose neighbour in direction d=(dx, dy) is outside m"""
    dx, dy = d
    sh = np.zeros_like(m)
    ys = slice(max(0, -dy), H - max(0, dy)); yd = slice(max(0, dy), H - max(0, -dy))
    xs = slice(max(0, -dx), W - max(0, dx)); xd = slice(max(0, dx), W - max(0, -dx))
    sh[ys, xs] = m[yd, xd]
    return m & ~sh

def lift(slot, k, top):
    base, n = slot.rstrip('0123456789'), int(slot[len(slot.rstrip('0123456789')):])
    return '%s%d' % (base, max(0, min(top, n + k)))

# ------------------------------------------------------------------ the scene
class Cover:
    def __init__(self, frame='a'):
        self.f = frame
        self.c = Canvas(W, H, 'K1')
        self.m = {}                       # named masks for rims and checks
        self.intent = np.zeros((H, W), bool)

    # ---------------------------------------------------------- sky
    def sky(self):
        c = self.c; g = c.g
        c.bands(0, HZ, [('S1', 0), ('S2', 86, 14), ('S3', 178, 12), ('S4', 202, 14), ('S5', 225, 12)], x0=GX0, x1=GX1 + 1)
        def prof(x, base, heads):
            y = base
            for cx, rx, hg in heads:
                u = (x - cx) / rx
                if abs(u) < 1:
                    y = min(y, base - hg * math.sqrt(1 - u * u))
            return int(round(y))
        # three storm masses of very different width in the upper pane: billowed tops with lobes of
        # very different radius, long flat undersides, one lit edge on the beam side (right)
        masses = [  # x0, x1, underside, top base, heads (cx, rx, height)
            (24, 170, 146, 131, [(50, 15, 12), (86, 27, 25), (123, 9, 6), (148, 17, 12)]),
            (181, 253, 124, 113, [(199, 8, 6), (228, 19, 16)]),
            (134, 160, 88, 86, [(143, 7, 5), (153, 4, 2)])]
        cl_ = np.zeros((H, W), bool)
        for mi, (x0, x1, und, tb, heads) in enumerate(masses):
            mk = np.zeros((H, W), bool)
            for x in range(max(GX0, x0), min(GX1, x1) + 1):
                top = prof(x, tb + 1.5 * vn(x, 23, 40 + mi), heads)
                if x1 - x < 7 and x1 < GX1:                    # a rounded end
                    top = max(top, und - int(round(math.sqrt(max(0, 49 - (x - x1 + 7) ** 2)) * 1.4)))
                if x - x0 < 5 and x0 > GX0:
                    top = max(top, und - int(round(math.sqrt(max(0, 25 - (x0 + 5 - x) ** 2)) * 1.2)))
                u = und + (1 if (mi == 0 and x > 101) else 0)  # a 1 px step in the long underside
                if top <= u:
                    mk[top:u + 1, x] = True
            g[mk] = 'S1'
            g[edge_px(mk, (0, 1))] = 'S0'
            g[np.roll(edge_px(mk, (0, 1)), -1, 0) & mk & (vn(XX, 9, 44 + mi) > -0.3)] = 'S0'
            lit = edge_px(mk, (1, 0)) | (edge_px(mk, (0, -1)) & edge_px(np.roll(mk, -1, 1), (0, -1)) & ~np.roll(mk, -1, 1))
            lit &= ~edge_px(mk, (0, 1))
            g[lit] = 'S3'
            g[(np.roll(lit, -1, 1) | np.roll(lit, 1, 0)) & mk & ~lit & ~edge_px(mk, (0, 1))] = 'S2'
            cl_ |= mk
        # the storm's low ragged base in the lower pane, lying over the pale gap
        bot = [int(round(181 + 5 * vn(x, 27, 5) + 2.5 * vn(x, 9, 6))) for x in range(W)]
        deck = np.zeros((H, W), bool)
        for x in range(GX0, GX1 + 1):
            deck[171:bot[x] + 1, x] = True
            g[171:bot[x] + 1, x] = 'S1'
            g[bot[x], x] = 'S0'
            if vn(x, 7, 35) > 0.15:
                g[bot[x] - 1, x] = 'S0'
            t = 3 + int(round(1.5 * (1 + vn(x, 21, 33))))
            if bot[x] - t > 172:
                g[171:bot[x] - t, x] = 'S2'
        deck |= cl_
        # torn scud: long thin streaks under the deck, tapered, darker underside
        scud = np.zeros((H, W), bool)
        for x0, x1, y, th in []:
            for x in range(x0, x1):
                u = (x - x0) / (x1 - x0)
                t = max(1, int(round(th * math.sin(math.pi * u ** 0.8) + 0.3 * vn(x, 5, 63))))
                yt = y - t + 1 + int(round(0.6 * vn(x, 9, 65)))
                scud[yt:y + 1, x] = True
        g[scud] = 'S1'
        g[edge_px(scud, (0, 1))] = 'S0'
        self.m['deck'] = deck | scud
        # a long thin wisp at each side of the calm band, never behind the title
        for x0, x1, y in [(34, 62, 56), (40, 51, 61), (214, 244, 50), (226, 240, 66)]:
            g[y, x0:x1] = 'S2'

    # ---------------------------------------------------------- sea
    def sea(self):
        c = self.c; g = c.g
        c.bands(HZ, GY1 + 1, [('E4', HZ), ('E3', 251, 10), ('E2', 270, 14), ('E1', 295, 14), ('E0', 319, 12)], x0=GX0, x1=GX1 + 1)
        # a lumpy storm horizon: swell humps rising into the glow
        for x0, w, h in [(41, 5, 1), (57, 8, 2), (88, 4, 1), (128, 9, 2), (151, 3, 1), (170, 6, 1), (243, 5, 1)]:
            for i in range(w):
                hh = h if 0 < i < w - 1 else 1
                for k in range(1, hh + 1):
                    g[HZ - k, x0 + i] = 'E4'
        # rolling swells, far to near: each a lit back slope, a crest line at its peaks and a dark
        # face under it; steep face to the left (the wind), long back slope to the right
        swells = [(240, 0.6, 23, 0.1, 1), (244, 0.8, 31, 0.6, 1), (249, 1.0, 37, 0.3, 1), (255, 1.3, 43, 0.8, 1),
                  (262, 1.6, 51, 0.15, 2), (270, 2.0, 57, 0.55, 2), (279, 2.3, 63, 0.9, 2), (290, 2.6, 71, 0.35, 2),
                  (302, 3.0, 77, 0.7, 3), (316, 3.3, 83, 0.2, 3), (329, 3.5, 89, 0.6, 3)]
        def h_of(u):
            return u / 0.22 if u < 0.22 else 1 - (u - 0.22) / 0.78
        for si, (y0, amp, per, ph, th) in enumerate(swells):
            for x in range(GX0, GX1 + 1):
                if 284 <= y0 and 56 <= x <= 214:
                    continue
                u = (x / per + ph + 0.15 * vn(x, 29, 70 + si)) % 1.0
                hh = h_of(u)
                y = int(round(y0 - amp * hh + 0.6 * vn(x, 11, 90 + si)))
                if y < HZ or y > GY1:
                    continue
                band = g[min(GY1, y + 1), x]
                if not band.startswith('E'):
                    continue
                n = int(band[1:])
                if hh > 0.55:
                    g[y, x] = 'E%d' % min(5, n + 2)
                    if th > 1 and hh > 0.75:
                        g[y - 1, x] = 'E%d' % min(5, n + 1)
                else:
                    g[y, x] = 'E%d' % min(5, n + 1)
                for k in range(1, th + 1):
                    if y + k <= GY1:
                        g[y + k, x] = 'E%d' % max(0, n - 1)
            # whitecaps on a few peaks: foam on the steep face, spray blown left
            for k in range(0, 8):
                xc = int((k - ph + 1.0) * per)
                if not (GX0 + 4 <= xc <= GX1 - 4) or hsh(si, k, 77) > 0.45 or (284 <= y0 and 52 <= xc <= 218):
                    continue
                y = int(round(y0 - amp))
                foam = [(0, 0, 'N2'), (1, 0, 'N2'), (-1, 1, 'N1'), (0, 1, 'N1'), (2, 0, 'N1'), (-2, 1, 'N1'),
                        (1, 1, 'N1'), (-3, 2, 'N0')][:3 + int(hsh(si, k, 78) * 2 + th * 1.5)]
                for dx, dy, v in foam:
                    if GX0 <= xc + dx <= GX1 and HZ <= y + dy <= GY1:
                        g[y + dy, xc + dx] = v
                for j in range(int(hsh(si, k, 79) * 3)):
                    sx = xc - 4 - 3 * j
                    if GX0 <= sx <= GX1 and HZ <= y - 1 - (j % 2):
                        g[y - 1 - (j % 2), sx] = 'N0'
                        self.intent[y - 1 - (j % 2), sx] = True
        # the lamp's broken reflection under the far rock
        for y, x0, L in [(246, 217, 6), (251, 219, 3), (257, 216, 5), (264, 219, 3), (272, 218, 2), (281, 220, 2)]:
            g[y, x0:x0 + L] = 'B1' if (y < 260 and self.f == 'a') else 'E5'
        self.m['sea'] = (XX >= GX0) & (XX <= GX1) & (YY >= HZ) & (YY <= GY1)

    def crest(self, x, y, L, lit, face, trough, foam=False, seed=0):
        g = self.c.g
        hp = 1 if L < 12 else (2 if L < 22 else 3)
        a = max(2, L // 4)
        for i in range(L):
            if i < a:
                h = int(round(hp * (i + 1) / a))
            else:
                h = int(round(hp * (1 - (i - a) / max(1, L - a))))
            if x + i > GX1:
                break
            g[y - h, x + i] = lit
            for yy in range(y - h + 1, y + 1):
                g[yy, x + i] = face
        for i in range(-1, a + L // 3):
            if GX0 <= x + i <= GX1:
                g[y + 1, x + i] = trough
        if foam:
            px = x + a - 1
            blob = [(0, -hp), (1, -hp), (-1, -hp + 1), (0, -hp + 1), (1, -hp + 1), (2, -hp + 1), (-2, -hp + 2)]
            for k, (dx, dy) in enumerate(blob[:4 + int(hsh(seed, 3) * 4)]):
                if GX0 <= px + dx <= GX1:
                    g[y + dy - 1, px + dx] = 'N2' if k < 2 else 'N1'
            # spray blowing left off the crest
            for k in range(int(hsh(seed, 5) * 3)):
                sx = px - 3 - k * 3 - int(hsh(seed, k, 7) * 2)
                if sx >= GX0:
                    g[y - hp - 1 - (k % 2), sx] = 'N0'
                    self.intent[y - hp - 1 - (k % 2), sx] = True

    # ---------------------------------------------------------- lighthouse and rock
    def lighthouse(self):
        g = self.c.g
        sil = self.f == 'b'
        m = np.zeros((H, W), bool)
        def P(x, y, v):
            g[y, x] = 'R0' if sil else v
            m[y, x] = True
        # tower: tapering 8 -> 12 px, three dark bands, a door, a slit window
        bands = [(193, 199, 'd'), (200, 207, 'l'), (208, 214, 'd'), (215, 222, 'l'), (223, 229, 'd'), (230, 234, 'l')]
        for y in range(193, 235):
            hw = 4 + int(round((y - 193) * 2 / 41))
            x0, x1 = 221 - hw, 220 + hw
            kind = next(b[2] for b in bands if b[0] <= y <= b[1])
            shade, body, rim = ('R0', 'R1', 'R2') if kind == 'd' else ('R2', 'R3', 'R3')
            for x in range(x0, x1 + 1):
                v = 'R0' if x in (x0, x1) else (shade if x == x0 + 1 else (rim if x == x1 - 1 else body))
                P(x, y, v)
        for y in range(229, 234):
            P(220, y, 'R0'); P(221, y, 'R0')
        P(222, 211, 'R0'); P(222, 212, 'R0')
        # gallery: deck, posts with sky between, deck
        for x in range(216, 226):
            P(x, 190, 'R0'); P(x, 192, 'R0')
        for x in (216, 218, 221, 223, 225):
            P(x, 191, 'R0')
        # lantern room: frame, the lamp, lit glass
        for y in range(185, 190):
            P(217, y, 'R0'); P(224, y, 'R0')
        for y in (185, 189):
            P(218, y, 'R0'); P(223, y, 'R0')
            for x in range(219, 223):
                P(x, y, 'B3')
        for y in range(186, 189):
            P(218, y, 'B3'); P(223, y, 'B3')
            for x in range(219, 223):
                P(x, y, 'LP')
        # cap and finial
        for x in range(217, 225):
            P(x, 184, 'R0')
        P(218, 183, 'R0'); P(223, 183, 'R0')
        for x in range(219, 223):
            P(x, 183, 'R1')
        for x in range(219, 223):
            P(x, 182, 'R0')
        P(220, 181, 'R0'); P(221, 181, 'R0'); P(220, 180, 'R0')
        # the rock: a ledged mass, lit along its top, two crevices
        pts = [(195, 243), (197, 237), (201, 234), (205, 235), (208, 230), (213, 229), (222, 230), (227, 228),
               (232, 231), (238, 230), (243, 233), (246, 236), (249, 238), (250, 243)]
        rock = self.c.mask_poly(pts) & (XX <= GX1)
        g[rock] = 'R0' if sil else 'R1'
        top = edge_px(rock, (0, -1))
        if not sil:
            g[top] = 'R3'
            g[np.roll(top, 1, 0) & rock & (vn(XX, 6, 61) > -0.2)] = 'R2'
            for (xa, ya, xb, yb) in [(206, 236, 210, 242), (234, 234, 231, 241), (219, 233, 221, 238)]:
                self.c.line(xa, ya, xb, yb, 'R0')
        m |= rock
        # surf on the rock: foam along its foot and spray blown left off its seaward shoulder
        for x0, L in [(193, 4), (199, 7), (209, 3), (215, 9), (228, 5), (236, 8), (246, 2)]:
            g[243, x0:min(GX1 + 1, x0 + L)] = 'N1'
        for x0, L in [(196, 3), (204, 5), (224, 4), (240, 4)]:
            g[244, x0:x0 + L] = 'N0'
        spray = [(198, 231, 'N2'), (199, 231, 'N2'), (197, 232, 'N1'), (198, 232, 'N2'), (199, 232, 'N1'),
                 (196, 233, 'N1'), (193, 229, 'N1'), (192, 229, 'N1'), (193, 230, 'N0'), (188, 227, 'N0'),
                 (189, 227, 'N0'), (184, 226, 'N0'), (200, 233, 'N1'), (201, 232, 'N1')]
        for x, y, v in spray:
            g[y, x] = v
            self.intent[y, x] = True
        self.m['lighthouse'] = m

    def beam(self):
        if self.f == 'b':
            return
        ray = shapes.ray((H, W), 220, 187, angle=174, length=142, width=(3, 13))
        ray &= (XX >= GX0) & (XX < 219) & (YY < HZ)
        g = self.c.g
        cy = 187 + (220 - XX) * 0.1051                     # the beam's centre line
        off = np.abs(YY - cy)
        d = 220 - XX + 2.2 * (YY - cy)                       # slanted step boundaries
        wid = 1.5 + (220 - XX) * (5.0 / 142)                 # half-width along the beam
        core = ray & (off <= wid - 1.2)
        g[ray & (d < 118)] = 'B1'
        g[core & (d < 74)] = 'B2'
        g[ray & (d < 74) & ~core] = 'B1'
        g[core & (d < 30)] = 'B3'
        g[ray & (d < 30) & ~core] = 'B2'
        # past 118 px the beam is only the sky stepped up one slot, then it frays out at the antenna
        far = ray & (d >= 118)
        for y, x in zip(*np.nonzero(far)):
            v = g[y, x]
            if v.startswith('S') and hsh(x, y, 72) < 1.25 - (220 - x - 118) / 26.0:
                g[y, x] = lift(v, 1, 5)
        self.m['beam'] = ray

    # ---------------------------------------------------------- rain outside, drops on the glass
    def rain(self):
        g = self.c.g
        beam = self.m.get('beam', np.zeros((H, W), bool))
        title = (XX >= 52) & (XX <= 218) & (YY >= 10) & (YY <= 44)
        light_bg = ('S4', 'S5', 'B1', 'B2', 'B3', 'E5', 'N1', 'N2')
        n_far, n_near = 76, 42
        for i in range(n_far + n_near):
            near = i >= n_far
            L = (6 + int(hsh(i, 2) * 4)) if near else (3 + int(hsh(i, 2) * 3))
            x = GX0 + int(hsh(i, 3) * (GX1 - GX0 + 12))
            y = int(hsh(i, 4) * (GY1 + 4)) - 4
            for k in range(L):
                px, py = x - (k + y) // 3 + y // 3, y + k
                px = x - k // 3
                if not (GX0 <= px <= GX1 and 0 <= py <= GY1) or title[py, px]:
                    continue
                bg = g[py, px]
                if bg.startswith('R') or bg == 'LP':
                    continue
                if self.f == 'b':
                    v = 'N2' if near else 'N1'
                elif beam[py, px] and bg.startswith('B'):
                    v = {'B1': 'B2', 'B2': 'B3', 'B3': 'LP'}[bg]
                elif beam[py, px]:
                    v = lift(bg, 1, 5) if bg.startswith('S') else bg
                elif bg in light_bg:
                    v = 'N2' if near else 'N1'
                else:
                    v = 'N1' if near else 'N0'
                g[py, px] = v
                self.intent[py, px] = True

    def drops(self):
        g = self.c.g
        title = (XX >= 52) & (XX <= 218) & (YY >= 10) & (YY <= 44)
        A = ["h", "l"]
        B = ["hl", "ll", "dd"]
        C = [".h.", "hll", "lll", ".d."]
        D = ["hl.", "lll", ".dd"]
        E = [".hl.", "hlll", "llll", "llld", ".dd."]
        shapes_ = [A, B, C, D, E]
        # hand-listed: (x, y, shape, trail length); thicker toward the bottom rail
        spots = [(41, 70, 1, 0), (63, 96, 0, 0), (91, 58, 2, 6), (122, 84, 0, 0), (180, 66, 1, 0),
                 (233, 88, 3, 0), (207, 118, 0, 0), (36, 140, 2, 9), (150, 104, 1, 0), (240, 140, 0, 0),
                 (104, 150, 0, 0), (58, 188, 1, 0), (196, 186, 2, 0), (240, 212, 4, 12), (120, 214, 0, 0),
                 (37, 226, 3, 0), (150, 228, 1, 5), (90, 233, 0, 0), (232, 252, 1, 0), (44, 258, 2, 0),
                 (171, 249, 0, 0), (110, 262, 3, 7), (205, 270, 0, 0), (34, 274, 1, 0), (240, 279, 2, 0),
                 (66, 276, 0, 0), (186, 279, 1, 0), (227, 300, 3, 14), (44, 318, 4, 4), (236, 322, 1, 0),
                 (34, 306, 0, 0), (219, 316, 2, 0), (53, 329, 1, 0), (243, 330, 0, 0)]
        for idx, (x, y, si, trail) in enumerate(spots):
            sh = shapes_[si]
            if title[y, x]:
                continue
            for j, row in enumerate(sh):
                for i, ch in enumerate(row):
                    if ch == '.':
                        continue
                    px, py = x + i, y + j
                    if not (GX0 <= px <= GX1 and 0 <= py <= GY1):
                        continue
                    bg = g[py, px]
                    sea = bg.startswith('E')
                    if ch == 'h':
                        v = 'N3' if self.f == 'b' else 'N2'
                    elif ch == 'l':
                        v = 'N1' if (bg in ('S4', 'S5', 'E5', 'B1', 'B2', 'B3')) else 'N0'
                    else:
                        v = 'E0' if sea else 'S0'
                    g[py, px] = v
                    self.intent[py, px] = True
            for k in range(1, trail + 1):
                py = y - k
                if py < 0 or hsh(idx, k, 9) < 0.18:
                    continue
                bg = g[py, x]
                g[py, x] = 'N0' if not bg.startswith(('S4', 'S5', 'B')) else 'N1'
                self.intent[py, x] = True

    def crack(self):
        """the cracked lower-left pane and its two strips of masking tape"""
        g = self.c.g
        segs = [(30, 318, 35, 311), (35, 311, 41, 306), (41, 306, 46, 298), (46, 298, 52, 291), (41, 306, 49, 311)]
        import artlib
        for xa, ya, xb, yb in segs:
            for x, y in artlib.line(xa, ya, xb, yb):
                g[y, x] = 'N1'
                self.intent[y, x] = True
        g[307, 41] = 'N2'
        # tape: two strips crossing the crack, the second torn short
        t1 = self.c.mask_poly([(31, 297), (34, 294), (51, 309), (48, 312)])
        t2 = self.c.mask_poly([(33, 314), (47, 300), (50, 303), (38, 316), (36, 315)])
        for t in (t1, t2):
            g[t] = 'M1'
            g[edge_px(t, (0, 1)) | edge_px(t, (-1, 0))] = 'M0'
        g[316, 37] = 'M0'
        self.m['tape'] = t1 | t2

    # ---------------------------------------------------------- the room: frame, sill, wainscot
    def frame(self):
        c = self.c; g = c.g
        m = np.zeros((H, W), bool)
        # walls
        rect(c, 0, 0, 13, 341, 'K1'); rect(c, 262, 0, 269, 341, 'K1')
        g[0:342, 12:14] = 'K0'; g[0:342, 262] = 'K0'
        for x, y0, y1 in [(4, 40, 62), (7, 150, 171), (3, 260, 283), (265, 90, 112), (266, 230, 244)]:
            g[y0:y1, x] = 'K2'                    # faint plaster cracks
        # casings (architrave): outer edge, face, bead lit by the window, shadow into the sash
        for x0, x1, inner in [(14, 23, 'r'), (254, 261, 'l')]:
            rect(c, x0, 0, x1, 341, 'F2')
            if inner == 'r':
                g[0:342, x0] = 'F0'; g[0:342, x0 + 1] = 'F1'; g[0:342, x1 - 1] = 'F3'; g[0:342, x1] = 'F0'
            else:
                g[0:342, x1] = 'F0'; g[0:342, x1 - 1] = 'F1'; g[0:342, x0 + 1] = 'F3'; g[0:342, x0] = 'F0'
        # sash stiles
        for x0, x1, gl in [(24, 29, 29), (248, 253, 248)]:
            rect(c, x0, 0, x1, 341, 'F1')
            g[0:342, gl] = 'F3' if gl == 29 else 'F3'
            g[0:342, x0 if gl == 29 else x1] = 'F0'
        # meeting rail: upper sash bottom rail (behind) and lower sash top rail (in front)
        rect(c, 24, 158, 253, 163, 'F1'); g[158, 24:254] = 'F3'; g[163, 24:254] = 'F0'
        rect(c, 24, 164, 253, 170, 'F2'); g[164, 24:254] = 'F3'; g[170, 24:254] = 'F0'; g[169, 24:254] = 'F1'
        # sash lock: keeper on the upper rail, lever on the lower
        lock = """
....kkkkkk....
...kaAAAAak...
kkkkaaaaaakkkk
kAAAAAAAAAAAAk
kaaaaaaaaaaaak
kaaaaaaaaaaaak
.kkkkkkkkkkkk.
"""
        stamp(c, lock, {'k': 'W0', 'a': 'A0', 'A': 'A1'}, 128, 158, m)
        g[161, 132] = 'A2'
        # lower sash bottom rail, with a brass sash lift
        rect(c, 24, 334, 253, 341, 'F2'); g[334, 24:254] = 'F3'; g[335, 24:254] = 'F2'; g[341, 24:254] = 'F0'
        g[340, 24:254] = 'F1'
        stamp(c, "kaak\nkAAk\n.kk.", {'k': 'W0', 'a': 'A0', 'A': 'A1'}, 229, 336, m)
        fr = np.zeros((H, W), bool)
        fr[0:342, 0:30] = True; fr[0:342, 248:270] = True; fr[158:171, 24:254] = True; fr[334:342, 24:254] = True
        self.m['frame'] = fr | m

    def sill(self):
        c = self.c; g = c.g
        # sill top: two oak boards, grain runs, a knot, a ring stain
        rect(c, 8, 342, 265, 397, 'O1')
        g[342, 8:266] = 'O0'; g[343, 8:266] = 'O0'      # shadow under the rail
        g[369, 8:266] = 'O0'                           # board seam
        g[370, 8:266] = 'O2'
        grain = [(20, 349, 26, 'O2'), (64, 353, 18, 'O0'), (130, 347, 30, 'O2'), (201, 351, 22, 'O0'),
                 (236, 356, 20, 'O2'), (14, 361, 14, 'O0'), (100, 363, 24, 'O2'), (170, 359, 16, 'O0'),
                 (30, 377, 20, 'O2'), (88, 381, 28, 'O0'), (150, 376, 16, 'O2'), (210, 388, 26, 'O0'),
                 (242, 380, 18, 'O2'), (12, 391, 18, 'O0'), (120, 393, 22, 'O2'), (176, 395, 14, 'O0')]
        for x, y, L, v in grain:
            g[y, x:x + L] = v
        stamp(c, ".kk.\nkOOk\n.kk.", {'k': 'O0', 'O': 'O2'}, 33, 356)
        ring = [(246, 389), (247, 388), (248, 388), (249, 388), (250, 389), (249, 390), (248, 390), (247, 390)]
        for x, y in ring:
            g[y, x] = 'O0'
        # nosing: lit round edge, face, underside; a worn notch
        rect(c, 6, 398, 265, 409, 'O1')
        g[398, 6:266] = 'O2'; g[399, 6:266] = 'O3'; g[400, 6:266] = 'O2'
        g[407, 6:266] = 'O0'; g[408, 6:266] = 'O0'; g[409, 6:266] = 'K0'
        g[398:410, 6] = 'O0'; g[398:410, 265] = 'O0'
        for x in range(128, 134):
            g[398, x] = 'O0'; g[399, x] = 'O1' if x in (128, 133) else 'O0'
        g[400, 129:133] = 'O1'
        self.m['sill'] = (YY >= 342) & (YY <= 409) & (XX >= 6) & (XX <= 265)

    def wainscot(self):
        c = self.c; g = c.g
        rect(c, 0, 410, 269, 479, 'K1')
        widths = [12, 14, 10, 15, 11, 13, 9, 14, 12, 16, 10, 13, 11, 15, 12, 10, 14, 11, 8]
        x = 0
        for i, wd in enumerate(widths):
            x1 = min(269, x + wd - 1)
            face = 'K0' if i == 7 else 'K1'          # the replaced board, a step darker
            rect(c, x, 410, x1, 479, face)
            g[410:480, x] = 'K2' if i != 7 else 'K1'
            g[410:480, x1] = 'K0'
            if hsh(i, 81) < 0.7:
                g[414 + int(hsh(i, 82) * 4), x + 2] = 'K3'   # nail heads
            x = x1 + 1
        rect(c, 0, 410, 269, 413, 'K0')               # the nosing's shadow
        g[414, 0:270] = 'K0'
        for xx in range(0, 270):
            if hsh(xx, 83) < 0.5:
                g[415, xx] = 'K0'
        # socket and plug
        sock = """
kkkkkkkkkk
kFFFFFFFFk
kFffffffFk
kFfkffkfFk
kFfkffkfFk
kFffffffFk
kFffTTffFk
kFfTTTTfFk
kFfTTTTfFk
kFFFTTFFFk
kkkkkkkkkk
"""
        stamp(c, sock, {'k': 'K0', 'F': 'F2', 'f': 'F1', 'T': 'T2'}, 186, 450)
        # cord from the radio's foot over the nosing down to the plug
        cord = [(190, 387), (190, 388), (191, 389), (191, 390), (191, 391), (191, 392), (191, 393), (191, 394),
                (191, 395), (191, 396), (191, 397)]
        for x, y in cord:
            g[y, x] = 'T1'; g[y, x + 1] = 'T0'
        for y in range(398, 410):
            g[y, 191] = 'T2' if y < 401 else 'T1'; g[y, 192] = 'T0'
        for y in range(410, 457):
            xx = 191 + (1 if y > 428 else 0) + (1 if y > 446 else 0)
            g[y, xx] = 'T1'; g[y, xx - 1] = 'T0' if y > 446 else g[y, xx - 1]
            g[y, xx + 1] = 'T0'
        case = """
....kkkkkkkkkkkk
...kssssssssssk.
...kspppppppppsk
..kspppppppppsk.
..kspkkpkpkppsk.
..ksppppppppps k
.ksppkpkkpkppsk.
.kspppppppppsk..
.ksTTTTTTTTTTsk.
kssTkkTTTTkkTsk.
ksTTkkTTTTkkTk..
ksTTTTTTTTTTsk..
kssssssssssssk..
kTTTTTTTTTTTsk..
""".replace(' ', 's')
        stamp(c, case, {'k': 'K0', 's': 'T2', 'p': 'P0', 'T': 'T1'}, 34, 466)
        g[470:480, 33] = 'K0'
        self.m['wainscot'] = YY >= 410

    # ---------------------------------------------------------- the radio (hero)
    def radio(self, step=0):
        c = self.c; g = c.g
        X0, Y0, X1, Y1 = 56, 284, 214, 380
        m = np.zeros((H, W), bool)
        m[Y0:Y1 + 1, X0:X1 + 1] = True
        r = 6
        for dy in range(r):
            for dx in range(r):
                if (dx + 0.5 - r) ** 2 + (dy + 0.5 - r) ** 2 > r * r:
                    m[Y0 + dy, X0 + dx] = False
                    m[Y0 + dy, X1 - dx] = False
        g[m] = 'W2'
        # front border and the recessed panel
        panel = np.zeros((H, W), bool); panel[293:377, 62:209] = True
        g[panel] = 'W1'
        g[293, 62:209] = 'W0'; g[293:377, 62] = 'W0'; g[376, 63:209] = 'W3'; g[294:377, 208] = 'W2'
        # border grain
        for x, y0, y1 in [(58, 300, 330), (60, 340, 371), (211, 296, 318), (209, 330, 360), (212, 362, 374)]:
            g[y0:y1, x] = 'W1'
        for x0, x1, y in [(70, 98, 378), (130, 160, 379), (176, 200, 378), (90, 120, 290), (150, 184, 291)]:
            g[y, x0:x1] = 'W1' if y > 300 else 'W3'
        # top face: cool rim at its back edge, surface, the front edge catching light
        top = m & (YY <= 288)
        g[top & (YY >= 285)] = 'W2'
        g[m & (YY == 288)] = 'W3'
        g[top & (YY == 284)] = 'F3'
        for x0, x1 in [(80, 96), (104, 109), (120, 136), (186, 200)]:      # vent slots on the top
            g[286, x0:x1] = 'W1'
        # outline in the cabinet's own darkest step, except the lit top edge
        ol = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
        g[ol & (YY > 286)] = 'W0'
        g[ol & (YY <= 286) & ((XX < X0 + 3) | (XX > X1 - 3))] = 'W0'
        # cool rim down the upper sides (the window is behind the radio)
        for y in range(290, 322):
            if y % 9 != 4:
                g[y, X0 + 1] = 'F3' if y < 306 else 'W3'
                g[y, X1 - 1] = 'F3' if y < 306 else 'W3'
        # plinth and feet
        rect(c, 54, 381, 216, 384, 'W1'); g[381, 54:217] = 'W3'; g[384, 54:217] = 'W0'
        g[381:385, 54] = 'W0'; g[381:385, 216] = 'W0'
        for fx in (61, 199):
            rect(c, fx, 385, fx + 9, 386, 'W0'); g[385, fx + 1:fx + 9] = 'W1'
        g[385:387, 71:199] = 'O0'                           # shadow under the cabinet
        m[381:387, 54:217] = True
        # ---- dial: brass bezel, glowing glass, printed scale, pointer
        bz = np.zeros((H, W), bool); bz[295:323, 64:147] = True
        for (cx, cy) in [(64, 295), (146, 295), (64, 322), (146, 322)]:
            g_ = 1
        g[bz] = 'A1'
        g[295, 64:147] = 'A0'; g[322, 64:147] = 'A0'; g[295:323, 64] = 'A0'; g[295:323, 146] = 'A0'
        g[295, 64] = 'W1'; g[295, 146] = 'W1'; g[322, 64] = 'W1'; g[322, 146] = 'W1'
        g[321, 66:146] = 'A2'                               # the bezel's inner lip, lit by the glass
        gl = np.zeros((H, W), bool); gl[297:321, 66:145] = True
        g[gl] = 'Y3'
        g[gl & ((YY <= 298) | (YY >= 319) | (XX <= 67) | (XX >= 143))] = 'Y2'
        core = gl & (YY >= 302) & (YY <= 315) & (XX >= 72) & (XX <= 138)
        for (cx_, sx_) in [(72, 1), (138, -1)]:
            for k, cut in enumerate([3, 2, 1, 1]):
                core[302 + k, cx_ - (0 if sx_ > 0 else cut - 1): cx_ + (cut if sx_ > 0 else 1)] = False
                core[315 - k, cx_ - (0 if sx_ > 0 else cut - 1): cx_ + (cut if sx_ > 0 else 1)] = False
        g[core] = 'Y4'
        for (cx, cy, sx, sy) in [(66, 297, 1, 1), (144, 297, -1, 1), (66, 320, 1, -1), (144, 320, -1, -1)]:
            for k in range(3):
                for j in range(3 - k):
                    g[cy + sy * k, cx + sx * j] = 'Y1'
        # scale: ticks along the top and bottom, two lines of station marks
        for x in range(70, 142, 4):
            long_ = (x - 70) % 12 == 0
            g[299, x] = 'Y0'
            if long_:
                g[300, x] = 'Y0'
        for x in range(72, 142, 6):
            g[318, x] = 'Y0'
            if (x - 72) % 18 == 0:
                g[317, x] = 'Y0'
        g[301, 70:141] = 'Y2'
        for x0, L in [(74, 4), (82, 2), (88, 5), (98, 3), (106, 4), (116, 2), (122, 5), (132, 3)]:
            g[306, x0:x0 + L] = 'Y1'
        for x0, L in [(77, 3), (85, 5), (95, 2), (103, 4), (113, 3), (120, 2), (127, 4), (136, 2)]:
            g[311, x0:x0 + L] = 'Y1'
        px = 101 + (2 if self.f == 'b' else 0) * 0
        g[298:320, px] = 'Q0'
        g[297, px] = 'W0'; g[320, px] = 'W0'
        # warm spill on the panel around the bezel (1 px ring, longer below: the light falls)
        g[323, 63:148] = 'W4'; g[324, 66:144] = 'W3'
        g[296:323, 63] = 'W3'; g[296:323, 147] = 'W3'
        g[294, 66:145] = 'W2'
        self.m['dial'] = gl
        # ---- VU meter, needle kicked up
        rect(c, 124, 326, 143, 343, 'A1')
        g[326, 124:144] = 'W0'; g[343, 124:144] = 'W0'; g[326:344, 124] = 'W0'; g[326:344, 143] = 'W0'
        g[327, 125:143] = 'A0'
        face = np.zeros((H, W), bool); face[328:342, 126:142] = True
        g[face] = 'Y3'; g[face & (YY >= 337)] = 'Y2'
        cx, cy = 133.5, 341.5
        for ang, v in [(152, 'Y0'), (134, 'Y0'), (116, 'Y0'), (98, 'Y0'), (80, 'Y0'), (62, 'Q0'), (46, 'Q0')]:
            a = math.radians(ang)
            for rr in (10.5, 11.5):
                x, y = int(round(cx + rr * math.cos(a))), int(round(cy - rr * math.sin(a)))
                if face[y, x]:
                    g[y, x] = v
        needle = 52 if self.f == 'a' else 70
        a = math.radians(needle)
        for rr in np.arange(1, 11, 0.5):
            x, y = int(round(cx + rr * math.cos(a))), int(round(cy - rr * math.sin(a)))
            if face[y, x]:
                g[y, x] = 'W0'
        g[340:342, 132:136] = 'T1'; g[340, 133:135] = 'T2'
        # ---- brass plate with an engraved wave, under the VU meter
        rect(c, 124, 347, 143, 368, 'A0')
        g[347, 124:144] = 'W0'; g[368, 124:144] = 'W0'; g[347:369, 124] = 'W0'; g[347:369, 143] = 'W0'
        g[348, 125:143] = 'A1'
        for x in range(127, 141):
            y = 358 + int(round(1.5 * math.sin((x - 127) / 13 * 2 * math.pi)))
            g[y, x] = 'A1'
        g[351, 127] = 'A1'; g[351, 140] = 'A1'; g[365, 127] = 'A1'; g[365, 140] = 'A1'
        # ---- cassette deck: door, smoked window, the cassette and its spools, keys
        rect(c, 66, 326, 120, 370, 'T2')
        g[326, 66:121] = 'W0'; g[370, 66:121] = 'W0'; g[326:371, 66] = 'W0'; g[326:371, 120] = 'W0'
        g[327, 67:120] = 'T1'; g[369, 67:120] = 'T3'
        rect(c, 70, 330, 116, 355, 'T0')
        rect(c, 71, 331, 115, 355, 'T1')                    # cassette shell
        rect(c, 74, 333, 112, 339, 'P1')                    # label
        g[333, 74:113] = 'P2'; g[339, 74:113] = 'P0'
        for x0, L in [(77, 6), (85, 3), (90, 8), (100, 2), (104, 5)]:
            g[336, x0:x0 + L] = 'T1'
        rect(c, 79, 341, 107, 351, 'T0')                    # tape window
        def disc(cx_, cy_, rr, v, clip):
            for yy in range(int(cy_ - rr - 1), int(cy_ + rr + 2)):
                for xx in range(int(cx_ - rr - 1), int(cx_ + rr + 2)):
                    if (xx - cx_) ** 2 + (yy - cy_) ** 2 <= (rr + 0.35) ** 2 and clip[yy, xx]:
                        g[yy, xx] = v
        win = np.zeros((H, W), bool); win[341:352, 79:108] = True
        disc(86, 346, 5, 'W1', win)                         # the full pack
        disc(101, 346, 3, 'W1', win)                        # the thin pack
        for (x, y) in [(83, 342), (84, 341), (85, 341), (82, 343), (99, 343), (100, 343)]:
            g[y, x] = 'W2'                                  # sheen on the tape
        hubs = [["..p..", ".pPp.", "pPkPp", ".pPp.", "..p.."], ["..p..", ".PPp.", "pPkPp", ".pPP.", "..p.."],
                ["..p..", ".pPP.", "pPkPp", ".PPp.", "..p.."], ["..P..", ".pPp.", "PPkPP", ".pPp.", "..P.."]]
        for (hx, hy), off in [((86, 346), 0), ((101, 346), 1)]:
            art = hubs[(step + off) % 4]
            for j, row in enumerate(art):
                for i, ch in enumerate(row):
                    if ch != '.':
                        g[hy - 2 + j, hx - 2 + i] = {'p': 'P2', 'P': 'P3', 'k': 'T0'}[ch]
        g[352:356, 72:115] = 'T1'; g[353, 75:112] = 'T2'
        g[355, 70:117] = 'T0'
        # deck keys, PLAY held down
        for i, (x0, x1) in enumerate([(69, 77), (79, 87), (89, 97), (99, 107), (109, 117)]):
            dn = 2 if i == 1 else 0
            rect(c, x0, 358 + dn, x1, 367, 'T2')
            g[358 + dn, x0:x1 + 1] = 'T3' if not dn else 'T1'
            g[358 + dn:368, x0] = 'T0'; g[358 + dn:368, x1] = 'T0'; g[367, x0:x1 + 1] = 'T0'
        g[357, 68:119] = 'T0'
        # ---- speaker grille: arched cloth behind five frets
        rect(c, 152, 296, 206, 357, 'W2')
        g[296, 152:207] = 'W0'; g[357, 152:207] = 'W0'; g[296:358, 152] = 'W0'; g[296:358, 206] = 'W0'
        g[297, 153:206] = 'W3'; g[297:357, 153] = 'W3'; g[356, 153:206] = 'W1'; g[297:357, 205] = 'W1'
        cloth = np.zeros((H, W), bool)
        for x in range(156, 203):
            t = 303 - int(round(4 * (1 - ((x - 179) / 24.0) ** 2)))
            cloth[t:354, x] = True
        g[cloth] = 'C1'
        g[cloth & (YY >= 348)] = 'C0'
        g[edge_px(cloth, (0, -1))] = 'W0'
        g[(np.roll(edge_px(cloth, (0, -1)), 1, 0)) & cloth] = 'C2'
        for fx in (159, 167, 176, 185, 193):
            col = cloth[:, fx + 1]
            t = int(np.nonzero(col)[0][0])
            g[t:354, fx] = 'W3'; g[t:354, fx + 1] = 'W2'; g[t:354, fx + 2] = 'W0'
        g[354, 156:203] = 'W0'
        # ---- two knobs, lit from the dial side (upper left)
        knob = """
....kkkkk....
..kkMMMMWkk..
.kMMWWWWWmmk.
.kMWWWWWWmmk.
kMWWWWWWWmmnk
kMWWWWWWWmnnk
kMWWWWWWmmnnk
kmWWWWWWmmnnk
kmmWWWWmmnnnk
.kmmmmmmnnnk.
.knnnnnnnnnk.
..kknnnnnkk..
....kkkkk....
"""
        key = {'k': 'W0', 'n': 'W1', 'm': 'W2', 'W': 'W3', 'M': 'W4'}
        for (kx, ky, ang) in [(157, 362, 140), (187, 362, 35)]:
            stamp(c, knob, key, kx, ky)
            a = math.radians(ang)
            for rr in (2, 3, 4):
                g[int(round(ky + 6 - rr * math.sin(a))), int(round(kx + 6 + rr * math.cos(a)))] = 'W0'
            g[ky + 2, kx + 3] = 'W5'
        self.m['radio'] = m | panel

    def antenna(self):
        g = self.c.g
        m = np.zeros((H, W), bool)
        stamp(self.c, ".kk.\nkTTk\nkTtk", {'k': 'T0', 'T': 'T3', 't': 'T2'}, 71, 281, m)
        import artlib
        light = ('S4', 'S5', 'B1', 'B2', 'B3', 'E5', 'N1', 'N2')
        def rod(x, y, lit):
            bg = g[y, x]
            g[y, x] = ('T1' if bg in light else ('N1' if lit else 'T3'))
            m[y, x] = True
        for x, y in artlib.line(73, 280, 83, 241):
            g[y, x] = 'T1'; m[y, x] = True
            rod(x + 1, y, True)
        g[240:243, 82:86] = 'T2'; g[240, 83:85] = 'T3'; m[240:243, 82:86] = True   # the sleeve at the bend
        for i, (x, y) in enumerate(artlib.line(83, 239, 79, 203)):
            rod(x, y, i % 6 == 2)
        g[201:203, 78:80] = 'T1'; g[201, 79] = 'N1'; m[201:203, 78:80] = True        # the tip ball
        self.m['antenna'] = m

    def cassette_case(self):
        """a spare cassette case lying on the radio's top"""
        art = """
kkkkkkkkkkkkkkkkkkkkkkkkkkkk
kssssssssssssssssssssssssssk
kpPPPPPPPPPPPPPPPPPPPPPPPPpk
kpttttt.tttttttttt...ttttppk
kpppppppppppppppppppppppppk.
kkkkkkkkkkkkkkkkkkkkkkkkkk..
"""
        art = art.replace('.', 'p')
        m = np.zeros((H, W), bool)
        stamp(self.c, art, {'k': 'T0', 's': 'F3', 'p': 'P1', 'P': 'P2', 't': 'T1'}, 150, 278, m)
        self.c.g[283, 176:178] = 'W0'
        self.m['case'] = m

    # ---------------------------------------------------------- props on the sill
    def mug(self):
        c = self.c; g = c.g
        art = """
....VVVVVVVVVVVV........
..VVvvvvvvvvvvvvVV......
.VvkkkkkkkkkkkkkkvV.....
.VvkkkkkkkkkkkkkkvV.....
..VVvvvvvvvvvvvvVV......
..o1123322222221ooooo...
..o11233222222211o..oo..
..o112332222222211o..o..
..o112332222222211o...o.
..o112332222222211o...o.
..o112332222222211o...o.
..o112332222222211o..oo.
..o112332222222211o.oo..
..o112332222222211ooo...
..o112332222222211o.....
..o11233222222221o......
..o11222222222221o......
..o11222222222221o......
..VVvvvvvvvvvvvvVV......
...VVVVVVVVVVVVVV.......
"""
        key = {'V': 'V0', 'v': 'V1', 'k': 'K0', 'o': 'U0', '1': 'U1', '2': 'U2', '3': 'U3'}
        mm = np.zeros((H, W), bool)
        ox, oy = 219, 366
        stamp(c, art, key, ox, oy, mm)
        # the handle's inner face
        for (x, y) in [(20, 7), (21, 8), (21, 9), (21, 10), (20, 11), (19, 12)]:
            g[oy + y, ox + x] = 'U1'
        g[oy + 1, ox + 4:ox + 16] = 'X1'                     # the rim catches the window light
        g[oy + 4, ox + 8] = 'T1'; g[oy + 4, ox + 9] = 'K0'; g[oy + 5, ox + 9] = 'U0'   # the chip in the rim
        g[oy + 12, ox + 12] = 'K0'; g[oy + 12, ox + 13] = 'V0'                         # a chip on the body
        g[oy + 20, ox + 2:ox + 17] = 'O0'                     # contact shadow
        self.m['mug'] = mm

    def logbook(self):
        c = self.c; g = c.g
        art = """
..kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk.....
.kGgggggggggggggggggggggggggggggggggggggggggggggk.....
kGggggggggggggggggggggggggggggggggggggggggggggggqk....
kGgggggggggggggggggggggggggggggggggggggggggggggqppk...
kGggggggggggggggggggggggggggggggggggggggggggggqpppPk..
kGgggggggggggggggggggggggggggggggggggggggggggqppppPPk.
kGggggggggggggggggggggggggggggggggggggggggggqkkkkkkkkk
kGgggggggggggggggggggggggggggggggggggggggggggggggggggk
kGggggggggggggggggggggggggggggggggggggggggggggggggghk.
kGgggggggggggggggggggggggggggggggggggggggggggggggghhk.
kGggggggggggggggggggggggggggggggggggggggggggggggghhhk.
kGgggggggggggggggggggggggggggggggggggggggggggggghhhhk.
kGggggggggggggggggggggggggggggggggggggggggggggghhhhhk.
kGgggggggggggggggggggggggggggggggggggggggggggghhhhhhk.
kGgggggggggggggggggggggggggggggggggggggggggghhhhhhhhk.
kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk..
kpPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPpk..
kp0pp0ppp0pp0ppp0pp0ppp0pp0ppp0pp0pp0ppp0pp0pppp0pk..
kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk...
"""
        key = {'k': 'G0', 'G': 'G0', 'g': 'G1', 'h': 'G2', 'q': 'G0', 'p': 'P1', 'P': 'P2', '0': 'P0'}
        mm = np.zeros((H, W), bool)
        stamp(c, art, key, 13, 381, mm)
        # the cover's lit half and a cloth tape spine
        sub = mm & (XX >= 40) & (YY >= 382) & (YY <= 395)
        g[sub & (g == 'G1')] = 'G2'
        g[382:396, 15] = 'G0'; g[383:396, 16] = 'G0'
        # pencil, diagonal across the cover: eraser, ferrule, wood, cone, graphite tip
        pts = [(22, 393), (52, 384)]
        import artlib
        line = artlib.line(23, 393, 52, 385)
        for i, (x, y) in enumerate(line):
            if i < 2:
                v, v2 = 'Q0', 'Q0'
            elif i < 4:
                v, v2 = 'A1', 'A0'
            elif i < len(line) - 4:
                v, v2 = 'O4', 'O2'
            elif i < len(line) - 1:
                v, v2 = 'O5', 'O3'
            else:
                v, v2 = 'T0', 'T0'
            g[y, x] = v; g[y + 1, x] = v2
            mm[y, x] = mm[y + 1, x] = True
        self.m['logbook'] = mm

    def pool(self):
        """the dial's light on the sill in front of the radio, the nosing edge and the book"""
        g = self.c.g
        def blob(cx, cy, rx, ry, seed):
            ang = np.arctan2((YY - cy) / ry, (XX - cx) / rx)
            rr = np.hypot((XX - cx) / rx, (YY - cy) / ry)
            wob = 1 + 0.18 * np.sin(3 * ang + seed) + 0.1 * np.sin(5 * ang + 2 * seed)
            return rr < wob
        sill = (YY >= 387) & (YY <= 397)
        outer = blob(104, 386, 54, 12, 1.0) & sill
        inner = blob(100, 386, 33, 8, 2.3) & sill
        hot = blob(102, 386, 16, 5, 0.7) & sill
        for msk in (outer, inner, hot):
            for y, x in zip(*np.nonzero(msk)):
                v = g[y, x]
                if v.startswith('O'):
                    g[y, x] = lift(v, 1, 5)
        for x in range(56, 152):
            if g[399, x] == 'O3':
                g[399, x] = 'O4' if 76 <= x <= 128 else 'O3'
        for x in range(68, 140):
            if g[398, x] == 'O2':
                g[398, x] = 'O3'

    # ---------------------------------------------------------- title
    def title(self):
        c = self.c
        def text(s, x, y, adv, slot):
            for i, ch in enumerate(s):
                pixfont.draw(c, ch, x + i * adv, y, slot, shadow='K0')
        s1, s2 = 'SIGNAL FROM TIDEWATER', 'ORIGINAL SOUNDTRACK'
        w1 = len(s1) * 7 - 2
        x1 = (W - w1) // 2 + 1
        text(s1, x1, 18, 7, 'L1')
        w2 = len(s2) * 6 - 1
        x2 = (W - w2) // 2 + 1
        text(s2, x2, 31, 6, 'L0')
        c.g[35, x2 - 13:x2 - 3] = 'K0'; c.g[35, x2 + w2 + 5:x2 + w2 + 15] = 'K0'
        c.g[34, x2 - 14:x2 - 4] = 'L0'
        c.g[34, x2 + w2 + 4:x2 + w2 + 14] = 'L0'

    # ---------------------------------------------------------- B: the flash
    def bolt(self):
        g = self.c.g
        main = [(66, 84), (63, 97), (68, 108), (62, 121), (65, 133), (59, 146), (63, 157), (57, 171), (61, 183),
                (55, 197), (58, 209), (53, 222), (55, 235)]
        branch = [(61, 183), (68, 191), (66, 199), (74, 208), (72, 214)]
        import artlib
        for path, wide in [(main, True), (branch, False)]:
            for (xa, ya), (xb, yb) in zip(path, path[1:]):
                for x, y in artlib.line(xa, ya, xb, yb):
                    if GX0 <= x <= GX1 and y < HZ and not (158 <= y <= 170):
                        g[y, x] = 'Z0'
                        if wide and y > 100:
                            g[y, x + 1] = 'N3'
        # the root lights the cloud from inside: its billows step up around the bolt's head
        near = ((XX - 66) ** 2 / 900 + (YY - 92) ** 2 / 400 < 1) & self.m['deck']
        g[near & (g == 'S2')] = 'S4'
        g[near & (g == 'S3')] = 'S5'
        g[near & (g == 'S1')] = 'S3'
        # the strike on the sea: lit crests at its foot
        for x0, y, L in [(48, 236, 9), (44, 238, 4), (56, 238, 6), (50, 240, 3)]:
            g[y, x0:x0 + L] = 'N3' if L > 5 else 'N2'

    def flash_rims(self):
        """every room edge facing the glass takes a cold rim; the sill beside the radio is lit"""
        g = self.c.g
        # frame edges against the glass
        g[0:334, 29] = 'X1'; g[0:334, 248] = 'X1'; g[0:334, 28] = 'X0'; g[0:334, 249] = 'X0'
        g[158, 24:254] = 'X1'; g[170, 24:254] = 'X0'; g[164, 24:254] = 'X1'
        occ = self.m['radio'] | self.m['antenna'] | self.m['case'] | self.m['mug']
        for y, v in [(334, 'X1'), (335, 'X0')]:
            row = ~occ[y, 24:254]
            g[y, 24:254][row] = v
        g[0:342, 22] = 'X0'; g[0:342, 255] = 'X0'
        # the radio: top edge and upper sides, antenna's lit side, the cassette case
        rad = self.m['radio']
        top = edge_px(rad, (0, -1)) & (YY < 300)
        g[top] = 'X1'
        g[np.roll(top, 1, 0) & rad & (YY < 300)] = 'X0'
        for y in range(288, 336):
            g[y, 56] = 'X0' if y < 320 else g[y, 56]
            g[y, 214] = 'X1' if y < 320 else 'X0'
        ant = self.m['antenna']
        g[edge_px(ant, (1, 0)) & (YY < 279)] = 'X1'
        case = self.m['case']
        g[edge_px(case, (0, -1))] = 'X1'
        # mug: rim top, the window-side silhouette
        mug = self.m['mug']
        g[edge_px(mug, (0, -1))] = 'X1'
        g[edge_px(mug, (1, 0)) & (YY < 380)] = 'X0'
        g[edge_px(mug, (-1, 0)) & (YY < 380)] = 'X0'
        # logbook back edge, pencil top
        lb = self.m['logbook']
        g[edge_px(lb, (0, -1))] = 'X0'
        # the sill beside the radio, lit from the window: a flat strip with a stepped front edge
        runs = [(8, 3), (19, 5), (27, 4), (41, 2), (215, 4), (226, 2), (238, 5), (251, 3)]
        for i, (x0, dep) in enumerate(runs):
            x1 = runs[i + 1][0] if i + 1 < len(runs) and runs[i + 1][0] > x0 else (56 if x0 < 56 else 266)
            for x in range(x0, min(x1, 56 if x0 < 56 else 266)):
                for y in range(344, 346 + dep):
                    if g[y, x].startswith('O'):
                        g[y, x] = 'X0'
                if g[346 + dep, x].startswith('O'):
                    g[346 + dep, x] = 'O2'
        # the mug's shadow thrown toward the viewer across the lit strip
        for y in range(386, 394):
            for x in range(222 + (y - 386) // 3, 236 - (y - 386) // 2):
                if g[y, x].startswith(('O', 'X')):
                    g[y, x] = 'O0'

    # ---------------------------------------------------------- build
    def build(self):
        self.sky()
        self.sea()
        self.beam()
        self.lighthouse()
        if self.f == 'b':
            self.bolt()
        self.rain()
        self.drops()
        self.crack()
        self.frame()
        self.sill()
        self.wainscot()
        self.radio(step=0 if self.f == 'a' else 1)
        self.antenna()
        self.cassette_case()
        self.pool()
        self.mug()
        self.logbook()
        if self.f == 'b':
            self.flash_rims()
        self.title()
        return self

def render(frame):
    cv = Cover(frame).build()
    pal = PAL_A if frame == 'a' else flash_palette()
    img = cv.c.image(pal)
    return cv, img, pal

def main(frames='ab'):
    OUT.mkdir(exist_ok=True)
    for f in frames:
        cv, img, pal = render(f)
        img.save(OUT / ('10-%s@1x.png' % f))
        img.resize((W * SCALE, H * SCALE), Image.NEAREST).save(OUT / ('10-%s.png' % f))
        used = sorted(set(cv.c.g.ravel()))
        json.dump({k: pal[k] for k in sorted(pal)}, open(OUT / ('palette-%s.json' % f), 'w'), indent=1)
        Image.fromarray((cv.intent * 255).astype(np.uint8)).save(OUT / ('intent-%s.png' % f))
        print(f, 'slots used', len(used), 'palette', len(pal))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ab')
