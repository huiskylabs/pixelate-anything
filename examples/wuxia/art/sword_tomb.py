"""剑冢 · The Sword Tomb: an original scene in the style of 90s Chinese wuxia RPGs. 320x200 (VGA).

Night. A field of old swords planted in the earth under a jade moon; a stone stele carved 剑冢.
A swordsman in a pale robe reaches out, and one sword rises from the ground to meet him; a ripple
of light runs through every blade in the field. Clouds drift over the moon, mist breathes along
the ground, fireflies wander, his ribbon and sleeves move in the wind. Then the line of dialogue.

Made with the kit: the swordsman is curved solids (tools/sdf.py) seen by the 3/4 top-down camera;
the field, sky and swords are drawn into palette slots with ordered dithering; the dialogue is the
kit's CJK pixel font (tools/cjkfont.py). 96 frames at 12 fps, a seamless loop.
"""
import math, sys
import numpy as np
from PIL import Image
from wuxia import KIT, palette, th, Canvas, to_image, dialogue, loop_dissolve
import iso
from iso import Iso, hash2
from sdf import Sphere, RoundCone, Plate, Union, Smooth, Inter, Above
import cjkfont

iso.RAMP_STEPS = 7
W, H = 320, 200
T, FPS = 96, 12
FIELD = 74                                     # far edge of the field

PAL = palette({
    'sky':   ['#04061a', '#080d2a', '#0e163c', '#152050', '#1d2b66', '#283a7e', '#354a94'],
    'moon':  ['#5e6a44', '#86945c', '#aebc7c', '#cad89a', '#dee9b4', '#eef5d0', '#fafde8'],
    'cloud': ['#14163a', '#1e2250', '#2a2f68', '#383f80', '#4b5498', '#646eb2', '#8890cc'],
    'mtn':   ['#080b1e', '#0d1228', '#131a36', '#1a2344', '#222d54', '#2c3a66', '#3a4a7a'],
    'mist':  ['#26345e', '#34466e', '#46587e'],
    'earth': ['#08090e', '#0e1016', '#14171f', '#1b1f29', '#242834', '#2f3442', '#3d4352'],
    'grass': ['#0a120f', '#101c17', '#16271f', '#1f3529', '#2a4535', '#3a5a44', '#4f7357'],
    'stone': ['#141620', '#1d202c', '#282c3a', '#363b4c', '#474d62', '#5c6379', '#767e94'],
    'blade': ['#283146', '#3c4a64', '#566a88', '#7890ae', '#9db6d0', '#c6dcec', '#eaf6ff'],
    'glow':  ['#0c2834', '#103a48', '#16505e', '#227078', '#3a989a', '#6cc6c0', '#b4f0e4'],
    'gold':  ['#2a1e0e', '#4a3414', '#6e4e1c', '#967028', '#bc9438', '#dcb858', '#f2dc8c'],
    'grip':  ['#1a0c12', '#2e121a', '#461a22', '#5e242a', '#7a3034', '#984440', '#b45c50'],
    'jade':  ['#0c241c', '#12362a', '#1a4c3a', '#24644c', '#32805e', '#46a074', '#68c08e'],
    'robe':  ['#141c2c', '#1e2a3e', '#2c3c54', '#3e526c', '#546a86', '#6e86a0', '#90a6bc'],
    'cloth': ['#2c3442', '#424c5e', '#5c687c', '#7a879a', '#9aa6b6', '#bcc6d2', '#dce4ec'],
    'skin':  ['#2a1a1a', '#4a2c28', '#6e4236', '#94604a', '#b88062', '#d0a07e', '#e4bc9a'],
    'hair':  ['#05050a', '#0a0a12', '#10101a', '#171724', '#20202e', '#2a2a3a', '#36364a'],
    'ribbon': ['#3a0c14', '#5a1420', '#7a1c28', '#9a2832', '#b8383e', '#d0524e', '#e2766a'],
    'bark':  ['#08080c', '#0e0d14', '#15131c', '#1d1a26', '#272332', '#332e40', '#423b50'],
    'pine':  ['#050a0c', '#081014', '#0c181c', '#112226', '#172d30', '#1f3a3c', '#2a4a4a'],
}, {'ol': '#04050c', 'star': '#f6f4dc', 'star2': '#9aa6d0', 'fly': '#e2f48a', 'fly2': '#9ab858'})

# ---------------------------------------------------------------- the static world
def sky(c):
    for y in range(0, FIELD + 6):
        for x in range(W):
            v = 0.6 + 4.6 * (y / (FIELD + 6)) ** 1.25
            d = math.hypot(x - 62, y - 26)                                # the moon brightens the sky round it
            v += max(0.0, 1.9 * (1 - d / 70)) ** 1.4
            c.ramp(x, y, 'sky', v)
    for i in range(90):                                                    # stars, fewer near the moon
        x, y = hash2(i, 1, 41) * W, hash2(i, 2, 41) * 62
        if math.hypot(x - 62, y - 26) > 34:
            c.put(x, y, 'star' if hash2(i, 3, 41) > 0.75 else 'star2')

def moon(c):
    cx, cy, r = 62, 26, 13.5
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
            if d <= 1:
                v = 5.6 - 1.6 * d ** 3                                      # limb darkening
                for mx, my, mr, dv in ((-4, -3, 3.5, 1.1), (3, 2, 4.2, 0.9), (-1, 6, 2.6, 0.8), (5, -5, 2.2, 0.7)):
                    if math.hypot(x + 0.5 - cx - mx, y + 0.5 - cy - my) < mr:   # maria
                        v -= dv
                c.ramp(x, y, 'moon', v)
            elif d < 1.55:                                                   # halo
                c.ramp(x, y, 'sky', 6.4 - (d - 1) * 6)

def ridge(x, base, a, seed):
    return (base + a * (0.55 * math.sin(x / 31 + seed) + 0.3 * math.sin(x / 13.7 + seed * 2)
                        + 0.15 * math.sin(x / 5.3 + seed * 3)))

def mountains(c):
    for x in range(W):                                                       # far range, hazy, with a moonlit rim
        top = ridge(x, 56, 9, 1.0) - 8 * math.exp(-((x - 248) / 22) ** 2)
        for y in range(int(top), FIELD + 2):
            v = 5.0 - (y - top) * 0.13
            c.ramp(x, y, 'mtn', v)
        lit = ridge(x - 1, 56, 9, 1.0) - 8 * math.exp(-((x - 1 - 248) / 22) ** 2) > top
        c.put(x, int(top), 'mtn6' if lit else 'mtn5')
    for i, (px, py) in enumerate(((250, 42),)):                              # a pagoda on the far peak
        for k, w in enumerate((1, 5, 3, 5, 3, 5, 3, 7)):
            for dx in range(-(w // 2), w // 2 + 1):
                c.put(px + dx, py + k, 'mtn2' if w > 3 else 'mtn1')
        c.put(px, py - 1, 'mtn2')
    for x in range(W):                                                       # near range, darker
        top = ridge(x, 63, 6, 4.0)
        for y in range(int(top), FIELD + 4):
            c.ramp(x, y, 'mtn', 3.0 - (y - top) * 0.16)
        c.put(x, int(top), 'mtn4' if ridge(x - 1, 63, 6, 4.0) > top else 'mtn3')

CRACKS = [[(96, 150), (104, 154), (110, 153), (118, 158), (122, 166)], [(232, 122), (240, 126), (248, 125), (256, 130)],
          [(60, 112), (70, 114), (74, 119)], [(140, 182), (150, 178), (158, 181), (170, 179), (176, 184)],
          [(270, 170), (280, 168), (290, 173)]]

def path_mid(y):
    """the centre of the worn path to the stele"""
    k = (y - 108) / 92
    return 160 + 22 * k * k + 6 * math.sin(k * 4.2)

def ground(c):
    for y in range(FIELD, H):
        f = (y - FIELD) / (H - FIELD)
        for x in range(W):
            n = (0.5 * math.sin(x * 0.045 + y * 0.11) + 0.35 * math.sin(x * 0.11 - y * 0.07 + 1.3)
                 + 0.25 * (hash2(x // 3, y // 2, 5) - 0.5))
            v = 2.2 + 0.55 * n + 1.5 * (1 - f) ** 1.6 * (1 - x / W * 0.55)  # moonlight sheen toward the back left
            v -= 1.1 * max(0.0, abs(x - 165) / 165 - 0.55) + 0.9 * max(0.0, f - 0.75)   # a vignette at the edges
            if y > 108:
                hw = 4 + 9 * (y - 108) / 92
                if abs(x - path_mid(y)) < hw:
                    v += 0.9 * (1 - abs(x - path_mid(y)) / hw) + 0.3
            c.ramp(x, y, 'earth', v, 0, 5)
    for poly in CRACKS:
        for (x0, y0), (x1, y1) in zip(poly[:-1], poly[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0)))
            for k in range(n + 1):
                x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
                c.put(x, y, 'earth0'); c.put(x, y + 1, 'earth4')
    for gy in range(FIELD + 2, H, 5):                                         # grass tufts on a jittered grid
        for gx in range(0, W, 7):
            h_ = hash2(gx, gy, 9)
            x, y = gx + int(hash2(gx, gy, 10) * 6), gy + int(hash2(gx, gy, 11) * 4)
            if h_ < 0.7 or abs(x - path_mid(y)) < 6 + 9 * max(0, y - 108) / 92 and y > 108:
                continue
            tall = 2 + int((h_ - 0.7) * 8)
            for dx in (-1, 0, 1):
                for k in range(tall - abs(dx)):
                    c.put(x + dx, y - k, 'grass%d' % min(6, 1 + k + (1 if dx < 0 else 0)))
    for i in range(36):                                                        # pebbles along the path
        y = 112 + hash2(i, 1, 17) * 86
        x = path_mid(y) + (hash2(i, 2, 17) - 0.5) * 2 * (4 + 9 * (y - 108) / 92)
        c.put(x, y, 'stone4'); c.put(x + 1, y, 'stone2'); c.put(x, y + 1, 'earth1')

def far_edge(c):
    """low shrubs and stones along the far edge of the field, their tops catching the moon"""
    for x in range(W):
        h_ = 3 + 3 * (0.5 + 0.5 * math.sin(x / 7.1)) * (0.5 + 0.5 * math.sin(x / 19.3 + 1)) + 2 * hash2(x // 4, 1, 81)
        top = FIELD + 3 - h_
        for y in range(int(top), FIELD + 5):
            v = 3.2 - (y - top) * 0.55 + (0.8 if y - top < 1.2 else 0)
            c.ramp(x, y, 'pine', v, 0, 6)

def stele(c):
    x0, x1, top, base = 149, 171, 74, 112
    for y in range(top, base):
        for x in range(x0, x1):
            r = 4
            if y < top + r:                                                    # rounded shoulders
                if x < x0 + r and math.hypot(x - (x0 + r), y - (top + r)) > r:
                    continue
                if x >= x1 - r and math.hypot(x - (x1 - r - 1), y - (top + r)) > r:
                    continue
            u = (x - x0) / (x1 - x0)
            v = 4.6 - 2.6 * u + 0.4 * (hash2(x, y // 2, 31) - 0.5) - (y - top) * 0.012
            c.ramp(x, y, 'stone', v, 1, 6)
    for y in range(base, base + 4):                                            # the plinth
        for x in range(x0 - 4, x1 + 4):
            c.put(x, y, 'stone%d' % (5 if y == base else (3 if x < (x0 + x1) // 2 else 2)))
    for x in range(x0 - 5, x1 + 5):
        c.put(x, base + 4, 'ol')
    glyphs = Canvas(W, H)                                                      # 剑冢, carved: dark strokes, a lit lower lip
    for k, ch in enumerate('剑冢'):
        cjkfont.draw(glyphs, ch, x0 + 5, top + 6 + k * 14, 'cut')
    ys, xs = np.nonzero(glyphs.g == 'cut')
    cut = set(zip(xs, ys))
    for x, y in cut:
        c.put(x, y, 'stone0')
        if (x + 1, y + 1) not in cut:
            c.put(x + 1, y + 1, 'stone5')
    for i in range(14):                                                        # moss at the foot
        x = x0 - 3 + hash2(i, 1, 33) * (x1 - x0 + 6)
        c.put(x, base + 1 + int(hash2(i, 2, 33) * 2), 'grass%d' % (3 + int(hash2(i, 3, 33) * 3)))
    for y in range(top - 1, base):                                             # outline
        for x in range(x0 - 1, x1 + 1):
            if c.get(x, y) is not None and str(c.get(x, y)).startswith(('sky', 'mtn', 'earth', 'grass')):
                nb = [c.get(x + 1, y), c.get(x - 1, y), c.get(x, y + 1)]
                if any(n is not None and str(n).startswith('stone') for n in nb):
                    c.put(x, y, 'ol')

def tree(c):
    """a dead tree at the left edge, a pine at the right, boulders in the near corners"""
    def limb(x0, y0, x1, y1, r0, r1, lit=True):
        n = int(math.hypot(x1 - x0, y1 - y0)) + 1
        for k in range(n + 1):
            u = k / n; x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u; r = r0 + (r1 - r0) * u
            for dy in range(-int(r) - 1, int(r) + 2):
                for dx in range(-int(r) - 1, int(r) + 2):
                    d = math.hypot(dx, dy)
                    if d <= r + 0.5:
                        side = (dx - dy * 0.3) / max(r, 0.5)
                        c.ramp(x + dx, y + dy, 'bark', 2.0 - 1.4 * side + (0.5 if (lit and side < -0.6) else 0), 0, 6)
    limb(10, 200, 14, 120, 9, 5); limb(14, 122, 22, 70, 5, 3); limb(21, 74, 40, 48, 3, 1.2); limb(20, 82, 6, 60, 2.5, 1)
    limb(30, 60, 58, 54, 1.8, 0.6); limb(16, 104, 44, 92, 3, 1.2); limb(40, 93, 66, 96, 1.6, 0.5); limb(36, 52, 44, 36, 1.4, 0.5)
    limb(8, 66, -4, 50, 1.6, 0.6); limb(48, 92, 54, 82, 1.0, 0.4)
    for i in range(46):                                                        # pine at the right edge
        layer = i // 6
        cy = 70 + layer * 17 + hash2(i, 1, 51) * 6; cx = 316 - layer * 2 + (hash2(i, 2, 51) - 0.5) * 24
        rw, rh = 10 + layer * 2.5, 5
        for y in range(int(cy - rh), int(cy + rh) + 1):
            for x in range(int(cx - rw), int(cx + rw) + 1):
                d = ((x - cx) / rw) ** 2 + ((y - cy) / rh) ** 2
                if d <= 1 and hash2(x, y, 52) > d * 0.5:
                    v = 2.6 - (y - cy) / rh * 1.4 + (0.8 if x < cx - rw * 0.4 else 0) - d
                    c.ramp(x, y, 'pine', v, 0, 6)
    for bx, by, rx, ry in ((44, 190, 22, 12), (70, 196, 14, 8), (300, 194, 26, 13), (276, 199, 12, 7)):
        for y in range(int(by - ry), int(by + ry) + 1):
            for x in range(int(bx - rx), int(bx + rx) + 1):
                dx, dy = (x - bx) / rx, (y - by) / ry
                if dx * dx + dy * dy <= 1:
                    nz = -dy - 0.35 * dx
                    c.ramp(x, y, 'stone', 1.6 + 2.4 * max(0.0, nz) + 0.3 * (hash2(x // 2, y // 2, 61) - 0.5), 0, 5)
        for x in range(int(bx - rx), int(bx + rx) + 1):                       # dark contact line, grass at the foot
            dx = (x - bx) / rx
            if abs(dx) < 1:
                yy = by - ry * math.sqrt(1 - dx * dx)
                c.put(x, yy - 1, 'ol')

def build_static():
    c = Canvas(W, H)
    sky(c); moon(c); mountains(c); ground(c); far_edge(c); stele(c); tree(c)
    return c

# ---------------------------------------------------------------- what moves
SWORDS = [  # x, ground y, kind, tilt (px across per px up), tassel slot or None
    (96, 104, 'jian', -0.08, None), (124, 98, 'jian', 0.06, 'ribbon'), (204, 100, 'dao', -0.05, None), (232, 106, 'jian', 0.14, 'jade'),
    (78, 120, 'broken', 0.22, None), (112, 124, 'jian', -0.1, 'jade'), (250, 126, 'dao', 0.08, None), (276, 118, 'jian', 0.05, None),
    (60, 142, 'jian', -0.04, 'ribbon'), (92, 146, 'dao', 0.12, None), (136, 140, 'short', 0.03, None), (232, 146, 'jian', 0.18, None),
    (264, 152, 'jian', -0.1, 'ribbon'), (118, 168, 'broken', -0.26, None), (82, 176, 'jian', 0.1, 'jade'), (240, 176, 'dao', -0.12, None),
    (212, 186, 'jian', -0.08, None), (150, 186, 'short', 0.07, None), (54, 162, 'dao', 0.02, None), (288, 172, 'jian', 0.08, 'jade'),
    (186, 122, 'broken', 0.1, None), (300, 136, 'jian', -0.16, None),
]
CALLED = (178, 157)                                # the sword that answers him
HERO = (206, 160)

def rise(t):
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / T)

def ripple(t, x, y):
    """the wave of light that runs out through the field from the called sword: 0..1 at this sword"""
    d = math.hypot(x - CALLED[0], (y - CALLED[1]) * 1.6)
    r = (t - 34) * 4.2
    return max(0.0, 1 - abs(r - d) / 10) if 34 <= t < 84 else 0.0

def glow_pool(c, x, y, k):
    rx, ry = 5 + 6 * k, 2 + 2.4 * k
    for yy in range(int(y - ry), int(y + ry) + 1):
        for xx in range(int(x - rx), int(x + rx) + 1):
            d = ((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2
            if d < 1:
                v = (1 - d) * (1.5 + 3.5 * k)
                if v + th(xx, yy) > 1.1:
                    c.ramp(xx, yy, 'glow', v, 0, 6)

KINDS = {  # blade length, blade width, curve (saber), guard half-width, grip length, guard ramp
    'jian': (15, 2, 0.0, 3, 4, 'gold'), 'short': (10, 2, 0.0, 2, 3, 'gold'), 'dao': (14, 2, 3.2, 1, 5, 'gold'),
    'great': (21, 3, 0.0, 5, 6, 'jade'), 'broken': (7, 2, 0.0, 0, 0, None)}

def sword(c, x, y, kind, tilt, tassel, t, lift=0.0, shine=0.0, wind=0.0):
    """a sword planted point-down. jian: straight and double-edged; dao: a curved saber with a disc
    guard; great: the long sword with a jade guard; broken: a jagged piece of blade, no hilt"""
    L, bw, curve, gw, gl, gr = KINDS[kind]
    base = y - lift
    pts = []
    def axis(k):                                                           # the blade's centre k px up from the ground
        return x + tilt * k + curve * (k / L) ** 2, base - k
    for k in range(L):
        cx_, cy_ = axis(k)
        g = shine > 0 and abs(k - shine * (L + 6)) < 2.2
        cols = (['blade6', 'glow6'] if g else (['blade5', 'blade3'] if bw == 2 else ['blade5', 'blade4', 'blade2']))
        if kind == 'dao':                                                  # the back of a saber is dark, the edge bright
            cols = ['blade6', 'blade2'] if not g else ['glow6', 'blade4']
        if k < 2 and not g:
            cols = ['blade3'] * (bw - 1) + ['blade2']
        for j, v in enumerate(cols):
            pts.append((cx_ - bw // 2 + j, cy_, v))
    if kind == 'broken':                                                   # a jagged top
        cx_, cy_ = axis(L)
        pts += [(cx_ - 1, cy_, 'blade5'), (cx_ - 1, cy_ - 1, 'blade4')]
    else:
        gx, gy = axis(L)
        for dx in range(-gw, gw + 1):                                      # the guard
            pts.append((gx + dx - 0.5, gy, gr + ('5' if dx < 0 else '3')))
            pts.append((gx + dx - 0.5, gy + 1, gr + '2'))
        if kind == 'dao':
            pts += [(gx - 2.5, gy, gr + '4'), (gx + 1.5, gy, gr + '2')]
        for k in range(1, gl + 1):                                         # the grip, wrapped
            pts.append((gx - 1 + tilt * k, gy - k, 'grip4' if k % 2 else 'grip2'))
            pts.append((gx + tilt * k, gy - k, 'grip2' if k % 2 else 'grip1'))
        px_ = gx + tilt * (gl + 1)
        py_ = gy - gl - 1
        pts += [(px_ - 1, py_, gr + '5'), (px_, py_, gr + '3'), (px_ - 1, py_ - 1, gr + '4'), (px_, py_ - 1, gr + '2')]
        if tassel:                                                         # a cord and a tassel that sway in the wind
            sw = wind * 1.6
            for k in range(5):
                pts.append((px_ + 0.5 + sw * k / 5, py_ + k, tassel + '2'))
            for k in range(4):
                for dx in (-1, 0, 1):
                    pts.append((px_ + 0.5 + sw + dx + (k * 0.3 * (1 if dx > 0 else -1) if k > 1 else 0), py_ + 5 + k,
                                tassel + ('4' if dx < 0 else ('3' if dx == 0 else '2'))))
    occ = set((int(math.floor(a)), int(math.floor(b))) for a, b, _ in pts)
    for a, b, v in pts:                                                    # outline first, then the sword
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (int(math.floor(a)) + dx, int(math.floor(b)) + dy)
            if q not in occ and q[1] < base:
                c.put(q[0], q[1], 'ol')
    for a, b, v in pts:
        c.put(a, b, v)
    if lift < 0.5:
        for j in range(bw):
            c.put(x - bw // 2 + j, y + 1, 'earth0')                        # where it bites the ground
    else:                                                                  # the slot it left in the earth
        for j in range(bw):
            c.put(x - bw // 2 + j, y, 'earth0'); c.put(x - bw // 2 + j, y + 1, 'earth1')

# the swordsman: curved solids, 3/4 top-down camera
def robe_mat(p, n, step, t):
    x, y, z = p
    if 19.6 < z < 21.4:
        return 'hair%d' % min(6, step + 1)                                  # sash
    if 22 < z < 29.5 and n[1] > 0.25 and abs((x + 0.3) - (29.5 - z) * 0.55) < 0.9:
        return 'cloth%d' % min(6, step + 2)                                # the crossed collar
    return 'cloth%d' % max(0, step - 1)

def hero(t):
    wind = math.sin(2 * math.pi * t / 24)
    reach = max(0.0, min(1.0, (rise(t) - 0.15) / 0.5))
    s = Iso(W, H, origin=HERO, slots=PAL.keys(), camera='topdown', depth=0.55, height=1.0)
    L = (-0.6, 0.15, 0.78)
    hem = 1.6 + 0.8 * wind
    body = [Inter(RoundCone((0, 0, 21), (hem, 0, 3.0), 4.0, 6.4, mat=robe_mat), Above(0.0)),
            RoundCone((0, 0, 21), (0.4, 0, 28.6), 4.1, 4.5, mat=robe_mat),
            Sphere(0.2, 0, 30.0, 2.0, mat='skin')]                              # neck
    s.solid(Union(RoundCone((0.6, -4.0, 28.0), (1.6 + 0.6 * wind, -4.6, 19.5), 1.7, 2.7, mat=robe_mat),
                  Sphere(1.6 + 0.6 * wind, -4.8, 18.6, 1.1, mat='skin')), light=L)        # far arm, behind
    s.solid(Smooth(1.2, *body), light=L)
    head = Union(Sphere(-0.6, 0, 33.6, 3.4, mat='skin'),
                 Sphere(0.7, 0.1, 34.6, 3.6, mat='hair'), Sphere(0.8, 0, 38.4, 1.7, mat='hair'),
                 RoundCone((2.8, 0, 36.6), (6.5 + 1.5 * wind, 0, 28.5), 1.5, 0.7, mat='hair'))
    s.solid(head, light=L)
    rib = []                                                               # the ribbon from his topknot
    for k in range(9):
        u = k / 8
        rib.append((1.5 + u * 12, 38.6 - u * 4 + math.sin(2 * math.pi * (t / 12 - u * 0.9)) * (0.5 + 2.2 * u)))
    pts = rib + [(x + 0.8, z - 1.6 - 0.3 * i) for i, (x, z) in enumerate(reversed(rib))]
    s.solid(Plate(pts, y0=0.4, t=0.3, mat='ribbon'), light=L)
    ex = -1.5 - 6.5 * reach; ez = 19.5 + 3.5 * reach                        # near arm: hangs, then reaches out
    s.solid(Union(RoundCone((-0.4, 4.2, 28.0), (ex, 4.6, ez), 1.8, 2.9, mat=robe_mat),
                  Sphere(ex - 0.9 * reach, 4.6, ez - 0.6, 1.15, mat='skin')), light=L)
    s.solid(Union(RoundCone((-3.4, 1.8, 0.9), (-5.0, 1.8, 0.8), 1.15, 1.0, mat='hair'),
                  RoundCone((-2.2, -1.8, 0.9), (-3.8, -1.8, 0.8), 1.1, 0.9, mat='hair')), light=L)
    g = np.array(s.render(outline=True, between=True, rim=True).a, object)
    return g

def fireflies(c, t):
    for i in range(12):
        bx, by = 40 + hash2(i, 1, 71) * 250, 92 + hash2(i, 2, 71) * 90
        k = 2 * math.pi * t / T
        x = bx + 14 * math.sin(k * (1 + i % 2) + i) + 4 * math.sin(k * 3 + i * 2)
        y = by + 6 * math.sin(k * (1 + (i + 1) % 2) + i * 1.7)
        on = (math.sin(k * (2 + i % 3) + i) + 1) / 2
        if on > 0.35:
            c.put(x, y, 'fly' if on > 0.7 else 'fly2')
            if on > 0.85:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if str(c.get(x + dx, y + dy)).startswith(('earth', 'grass', 'sky', 'mtn')):
                        c.put(x + dx, y + dy, 'glow3')

CLOUDS = [  # a bank of puffs: (x, y, radius) relative to the cloud's anchor
    (30, 36, [(0, 0, 5), (8, -2, 6), (17, 0, 5), (25, 1, 4), (-8, 1, 4), (33, 2, 3), (-15, 2, 3), (42, 3, 2.5), (12, 3, 4)]),
    (196, 16, [(0, 0, 4), (7, -1, 5), (15, 0, 4), (-7, 1, 3.5), (22, 1, 3), (-13, 2, 2.5), (29, 2, 2.2), (37, 3, 2)]),
    (128, 44, [(0, 0, 3.5), (6, -1, 4.5), (13, 0, 3.5), (-6, 1, 3), (19, 1, 2.6), (-11, 2, 2), (25, 2, 2)]),
    (276, 34, [(0, 0, 3), (6, -1, 4), (12, 0, 3.4), (18, 1, 2.6), (-5, 1, 2.6), (24, 2, 2)]),
]

def clouds_layer(t):
    """banks of moonlit cloud: lit along their tops, dark beneath, flattened; one crosses the moon"""
    c = Canvas(W, H)
    drift = t * 0.2
    for ax, ay, puffs in CLOUDS:
        ax = (ax + drift + 60) % (W + 120) - 60
        x0 = int(ax - 30); x1 = int(ax + 60)
        for y in range(int(ay - 10), int(ay + 8)):
            for x in range(x0, x1):
                best = None
                for px, py, r in puffs:
                    d = math.hypot((x - ax - px) / 1.6, (y - ay - py)) / r      # flattened puffs
                    if d < 1 and (best is None or d < best[0]):
                        best = (d, (y - ay - py) / r)
                if best is None or y > ay + 3:
                    continue
                d, dy = best
                v = 4.2 - 2.4 * (dy + 1) / 2 - 0.8 * d
                if math.hypot(x - 62, y - 26) < 24:
                    v += 1.3                                                   # brighter where it crosses the moon
                c.ramp(x, y, 'cloud', v, 0, 6)
    return c.g

def mist_layer(t):
    c = Canvas(W, H)
    drift = t * 0.25
    for i, (y0, a) in enumerate(((78, 0.30), (86, 0.22), (96, 0.14))):
        for y in range(y0 - 3, y0 + 4):
            for x in range(W):
                k = 0.5 + 0.5 * math.sin((x - drift * (1 + i * 0.4)) / 23 + i) * math.sin((x + drift) / 41 + i * 2)
                dens = a * k * (1 - abs(y - y0) / 4)
                if th(x, y) < dens:
                    c.put(x, y, 'mist%d' % (2 - i if dens > 0.2 else 0))
    return c.g

STATIC = None

def frame(t):
    global STATIC
    if STATIC is None:
        STATIC = build_static()
    c = Canvas(W, H); c.g = STATIC.g.copy()
    cl_ = loop_dissolve(clouds_layer, t, T)
    m = cl_ != None
    c.g[m] = cl_[m]
    for i in range(90):                                                    # a few stars twinkle
        if hash2(i, 4, 41) > 0.82 and ((t // 4 + i) % 6 == 0):
            x, y = hash2(i, 1, 41) * W, hash2(i, 2, 41) * 62
            if str(c.get(x, y)).startswith(('star', 'sky')):
                c.put(x, y, 'sky3')
    k_call = rise(t)
    wind = math.sin(2 * math.pi * t / 24)
    for x, y, *_ in SWORDS:                                                # glow pools first, under everything
        glow_pool(c, x, y + 1, 0.15 + 0.85 * ripple(t, x, y))
    glow_pool(c, CALLED[0], CALLED[1] + 1, 0.4 + 0.6 * k_call)
    items = [(y, 'sword', (x, y, kind, tilt, tas)) for x, y, kind, tilt, tas in SWORDS]
    items.append((CALLED[1], 'called', None)); items.append((HERO[1], 'hero', None))
    for _, kind, a in sorted(items, key=lambda r: r[0]):
        if kind == 'sword':
            x, y, kind, tilt, tas = a
            r = ripple(t, x, y)
            sword(c, x, y, kind, tilt, tas, t, shine=(1 - r) if r > 0.05 else 0.0, wind=wind)
        elif kind == 'called':
            lift = 13 * k_call
            sh = ((t * 0.08) % 1) if k_call > 0.4 else 0.0
            if k_call > 0.15:                                              # a halo of light round it
                cy0 = CALLED[1] - lift - 14
                for yy in range(int(cy0 - 26), int(CALLED[1] + 2)):
                    for xx in range(CALLED[0] - 10, CALLED[0] + 11):
                        d = math.hypot((xx - CALLED[0]) / 7.5, (yy - cy0) / 20)
                        a_ = (1 - d) * (k_call - 0.15) * 2.2
                        if a_ > th(xx, yy) * 0.8 + 0.1:
                            v = c.get(xx, yy)
                            if v is not None and not str(v).startswith(('cloth', 'skin', 'hair', 'ribbon', 'ol', 'glow')):
                                c.put(xx, yy, 'glow%d' % min(5, 1 + int(a_ * 3.2)))
            sword(c, CALLED[0], CALLED[1], 'great', 0.0, 'ribbon', t, lift=lift, shine=sh, wind=wind)
            if k_call > 0.3:                                               # motes rising round it
                for i in range(8):
                    ph = (t * 0.05 + hash2(i, 9, 3)) % 1
                    mx = CALLED[0] + (hash2(i, 8, 3) - 0.5) * 14; my = CALLED[1] - ph * 30
                    c.put(mx, my, 'glow6' if ph < 0.5 else 'glow4')
        else:
            g = hero(t)
            sh_y, sh_x = HERO[1] + 1, HERO[0] + 3                           # his shadow, cast forward by the moon
            for yy in range(-2, 3):
                for xx in range(-7, 9):
                    if (xx / 8) ** 2 + (yy / 2.4) ** 2 < 1:
                        v = c.get(sh_x + xx, sh_y + yy)
                        if v is not None and str(v).startswith(('earth', 'grass')):
                            c.put(sh_x + xx, sh_y + yy, 'earth1')
            m = g != None
            c.g[m] = g[m]
    mi = loop_dissolve(mist_layer, t, T)
    m = mi != None
    c.g[m] = mi[m]
    fireflies(c, t)
    img = to_image(c.g, PAL)
    dialogue(img, '谢云归', ['剑冢千锋，皆已沉睡。', '唯有你，还在等我？'], t, start=12, cps=0.5, x=150, y=6, end=T - 4)
    return img

def render_frames(n=T):
    return [frame(t) for t in range(n)]

def export():
    return [{'name': 'sword_tomb', 'frames': [], 'images': [f.convert('RGBA') for f in render_frames()],
             'anchor': (0, 0), 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    import time
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/tomb'
    for t in [int(a) for a in (sys.argv[2:] or ['0', '48'])]:
        t0 = time.time()
        frame(t).resize((W * 3, H * 3), Image.NEAREST).save('%s-%03d.png' % (out, t))
        print(t, round(time.time() - t0, 2), 's')
