"""Rose Squall: an original side-view platformer moment in the modern pastel style, 320x180 (16:9).

A lighthouse stands on a sea stack in a rose squall at dusk. Its beam turns through the rain while
a courier with a coral scarf clings to the stack's sunlit face: she kicks off, dashes back up the
wall (the scarf flips to teal as the dash is spent) and slides down to where she started. Waves
break on the stack's foot; lightning forks once behind the far stacks.

What it learns from the modern pastel platformer (study 02 in the style study):
  - one mood hue window (indigo to rose to cream) and a lifted floor: no scenery is dark
  - the sky in flat, undithered strata locked together by tapered wisps and smile strokes
  - rock as a ledged, frayed silhouette with a lit rim and stacked flake dashes, no outline
  - only the actor is outlined; she carries the frame's top chroma
  - every light is computed on the art's own grid (bloom from the cloud and lamp masks, the
    beam as stepped bands, a low gradient tint), so even the glow comes in whole pixels
  - rain as opaque 1 px streaks over everything, white where the beam catches them
Everything is code: slot grids, seeded shapes, a native light pass, nearest-neighbour scale.
120 frames at 30 fps, a seamless loop.
"""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
import colorlib as cl

W, H = 320, 180
FRAMES, FPS = 120, 30
YY, XX = np.mgrid[0:H, 0:W]
HZ = 134                       # horizon row
SUNX = 222                     # the hidden sun, low behind the far stacks
LX, LY = 70, 21                # the lighthouse lamp

# ---------------------------------------------------------------- hashing and noise
def hsh(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 15; h = (h * 2246822519) & 0xFFFFFFFF; h ^= h >> 13
    return (h & 0xFFFFFF) / 16777216.0

def hsh_arr(a, b, seed):
    h = (a.astype(np.int64) * 374761393 + b.astype(np.int64) * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def noise1(u, seed):
    """smooth value noise in [-1, 1]"""
    i = math.floor(u); f = u - i
    s = f * f * (3 - 2 * f)
    return (hsh(i, seed) * (1 - s) + hsh(i + 1, seed) * s) * 2 - 1

# ---------------------------------------------------------------- palette
def lch(L, C, h):
    return cl.rgb_to_hex(cl.oklab_to_rgb(cl.oklch(L, cl.clamp_chroma(L, C, h), h)))

RAMPS = {
    # sky, darkest streak to horizon cream: indigo, violet, rose, blush, cream
    'sky': [(0.52, 0.080, 280), (0.58, 0.090, 284), (0.645, 0.100, 294), (0.71, 0.120, 318),
            (0.77, 0.130, 340), (0.83, 0.105, 352), (0.885, 0.070, 10), (0.935, 0.040, 45)],
    'far': [(0.73, 0.070, 312), (0.79, 0.065, 322), (0.88, 0.050, 345)],
    'sea': [(0.60, 0.080, 296), (0.665, 0.085, 304), (0.735, 0.095, 318), (0.83, 0.090, 342), (0.92, 0.050, 20)],
    # sandstone stack: plum darks to rose lights (the light end turns rose, never yellow)
    'rock': [(0.42, 0.070, 300), (0.48, 0.080, 304), (0.55, 0.090, 314), (0.63, 0.105, 328),
             (0.71, 0.120, 340), (0.80, 0.105, 350)],
    'mid': [(0.54, 0.075, 306), (0.60, 0.085, 314), (0.67, 0.095, 326), (0.75, 0.100, 338), (0.82, 0.085, 348)],
    'moss': [(0.52, 0.060, 200), (0.62, 0.075, 188), (0.74, 0.080, 175)],
    # the lighthouse: slate, the cool complement of the rose world
    'wall': [(0.53, 0.060, 268), (0.61, 0.065, 262), (0.70, 0.070, 254), (0.80, 0.060, 238)],
    'iron': [(0.40, 0.050, 298), (0.50, 0.060, 302), (0.62, 0.070, 320)],
    'glass': [(0.86, 0.090, 60), (0.97, 0.050, 85)],
    'cloud': [(0.80, 0.115, 336), (0.86, 0.110, 340), (0.92, 0.075, 346)],
    'foam': [(0.88, 0.040, 330), (0.97, 0.015, 340)],
    # courier
    'coat': [(0.38, 0.090, 282), (0.45, 0.100, 278), (0.54, 0.100, 272)],
    'scarf': [(0.62, 0.170, 25), (0.71, 0.160, 35), (0.81, 0.115, 48)],
    'teal': [(0.62, 0.110, 200), (0.73, 0.120, 192), (0.85, 0.085, 185)],
    'skin': [(0.80, 0.060, 32), (0.89, 0.045, 55)],
    'hair': [(0.42, 0.090, 335), (0.52, 0.110, 345)],
    'boot': [(0.48, 0.070, 335), (0.57, 0.080, 345)],
}
PAL = {}
for name, stops in RAMPS.items():
    for i, s in enumerate(stops):
        PAL['%s%d' % (name, i)] = lch(*s)
PAL.update({'ol': lch(0.36, 0.070, 296), 'rain': lch(0.93, 0.030, 310), 'flash': '#ffffff',
            'dust': lch(0.94, 0.035, 352), 'bolt': lch(0.99, 0.015, 300)})
ACTOR = ('coat', 'scarf', 'teal', 'skin', 'hair', 'boot', 'ol', 'flash')

# ---------------------------------------------------------------- shape helpers
def walk_edge(y0, seed, amp=5, bow=0.0):
    """a strata boundary: flat runs of 5-15 px joined by 1 px steps, wandering around y0; bow
    lifts it toward the sun so the light domes over the horizon"""
    e = np.zeros(W, int)
    y, x = y0, 0
    while x < W:
        run = 5 + int(hsh(x, seed) * 11)
        target = y0 + amp * noise1(x / 47, seed) + amp * 0.5 * noise1(x / 15, seed + 1) \
            + bow * ((x - SUNX) / W) ** 2 * 4
        e[x:x + run] = y
        y += 1 if target > y + 0.5 else -1 if target < y - 0.5 else 0
        x += run
    return e

def wisp(g, e, x0, L, T, tail, dirn, slot, bow, k, up=False):
    """a tapered wisp on boundary e: one long pointed tail, a notched edge. up=False hangs the
    darker band's colour below the boundary; up=True raises the lighter band's colour above it"""
    for i in range(L):
        u = i / (L - 1) * 2 - 1
        s_ = (u + 1) / 2 if dirn > 0 else (1 - u) / 2
        h = T * math.sin(math.pi * min(1.0, s_) ** (1 / tail)) ** 1.4
        x = x0 + i
        if not 0 <= x < W or h < 0.6:
            continue
        yc = e[x] + bow * u * u
        notch = int(2 * hsh(x // 3, k)) if h > 2.5 else 0
        if up:
            ys = range(int(yc - 0.7 * h), int(yc + 0.3 * h - notch) + 1)
        else:
            ys = range(int(yc - 0.3 * h + notch), int(yc + 0.7 * h) + 1)
        for y in ys:
            if 0 <= y < H:
                g[y, x] = slot

def smile(g, x0, y0, L, slot, depth=2.5, thick=2):
    """the little arc strokes that float inside a band (a darker tone, thickest in the middle)"""
    for i in range(L):
        u = i / (L - 1) * 2 - 1
        y = int(round(y0 + depth * (u * u - 1)))
        if 0 <= x0 + i < W:
            for d in range(thick if abs(u) < 0.55 else 1):
                if 0 <= y + d < H:
                    g[y + d, x0 + i] = slot

def fray(mask, side_left=True, seed=3, rate=1.0):
    """frayed micro edge in 2-row pieces: a tooth out, a notch in, the odd chip off the edge"""
    m = mask.copy()
    for y in range(H):
        xs = np.nonzero(mask[y])[0]
        if not len(xs):
            continue
        x = xs[0] if side_left else xs[-1]
        if (side_left and x == 0) or (not side_left and x == W - 1):
            continue
        d = -1 if side_left else 1
        r = y // 2 + (1 if hsh(y // 2, seed + 9) < 0.3 else 0)
        h = hsh(r, seed) / rate
        if h < 0.12:
            for k in range(1, 1 + (1 if hsh(r, seed + 1) < 0.6 else 2)):
                if 0 <= x + d * k < W:
                    m[y, x + d * k] = True
        elif h < 0.22:
            for k in range(0, 1 + (hsh(r, seed + 2) < 0.4)):
                m[y, x - d * k] = False
        elif h < 0.25 and 0 <= x + d * 3 < W and y % 2 == 0:
            m[y, x + d * 3] = True
            if hsh(r, seed + 3) < 0.5:
                m[y, x + d * 4] = True
    return m

def cloud_mass(cx, cy, rx, ry, n, seed, belly=5):
    """a cloud mass: an ellipse core with perimeter lobes, heavier on the belly, one flat tone
    (loose discs would read as bubbles)"""
    m = ((XX + 0.5 - cx) / rx) ** 2 + ((YY + 0.5 - cy) / ry) ** 2 <= 1
    for i in range(n):
        a = 2 * math.pi * (i + 0.4 * hsh(i, seed)) / n
        r = 4 + 6 * hsh(i, seed + 1) + (belly if math.sin(a) > 0.25 else 0)
        px, py = cx + rx * math.cos(a), cy + ry * math.sin(a)
        m |= (XX + 0.5 - px) ** 2 + (YY + 0.5 - py) ** 2 <= (r + 0.15) ** 2
    return m

def shade_cloud(g, m, seed):
    """flat body; the upper lobes a tone lighter where they face the sun, the belly a tone deeper"""
    g[m] = 'cloud1'
    up = m & ~np.roll(m, 3, 0)
    lit = up & (hsh_arr(XX // 5, YY // 3, seed) < 0.75)
    g[lit] = 'cloud2'
    low = m & ~np.roll(m, -1, 0)
    g[low] = 'cloud0'
    g[low & np.roll(low, -1, 0) == False] = g[low & np.roll(low, -1, 0) == False]
    low2 = np.roll(low, -1, 0) & m & (hsh_arr(XX // 2, YY, seed + 1) < 0.55)
    g[low2] = 'cloud0'

def flakes(g, mask, base, seed, cell=(11, 6), gate=0.5, lens=(4, 9), top=5, body=1):
    """stacked 1 px flake dashes (the rock texture of the pastel platformer): each stack is 1-3
    rows, each row shifted right and 2 px shorter, its last 2 px a step lighter, with a shadow
    dash under-left; stacks gather in clusters so it never reads as a brick grid"""
    cw, ch = cell
    for gy in range(-1, H // ch + 2):
        for gx in range(-1, W // cw + 2):
            if hsh(gx // 2, gy // 2, seed) > gate or hsh(gx, gy, seed + 1) > 0.8:
                continue
            ax = gx * cw + int(hsh(gx, gy, seed + 2) * cw) + (3 if gy % 2 else 0)
            ay = gy * ch + int(hsh(gx, gy, seed + 3) * ch)
            L0 = lens[0] + int(hsh(gx, gy, seed + 4) * (lens[1] - lens[0] + 1))
            stack = 1 + int(hsh(gx, gy, seed + 5) * 2.6)
            x = ax
            for j in range(stack):
                Lj = max(2, L0 - 2 * j)
                y = ay - j
                for k in range(Lj):
                    xx = x + k
                    if 0 <= y < H and 0 <= xx < W and mask[y, xx]:
                        g[y, xx] = '%s%d' % (base, min(top, body + (2 if j == 0 and k >= Lj - 2 else 1)))
                x += 1 + int(hsh(gx, gy, j, seed + 6) * 2)
            y = ay + 1
            for k in range(L0 - 1):
                xx = ax - 2 + k
                if 0 <= y < H and 0 <= xx < W and mask[y, xx] and g[y, xx] == '%s%d' % (base, body):
                    g[y, xx] = '%s%d' % (base, max(0, body - 1))

def strata(y0, y1, seed, hmin=6, hmax=14):
    """bedding layers: [(top, bottom, k)], 6-14 rows each"""
    out, y, k = [], y0, 0
    while y < y1:
        h = hmin + int(hsh(k, seed) * (hmax - hmin + 1))
        out.append((y, min(y1, y + h), k))
        y += h; k += 1
    return out

def layered_rock(g, ramp, layers, lx, rx, seed, lit_right=True, body=1, top=5, moss=False, rate=1.0, flake_gate=0.45):
    """a sedimentary stack seen from the side. Each layer juts or recedes a few px on either side
    and its face leans a pixel or two, so the silhouette is ledged. Shading: a flat body with flake
    dashes, a lit band of 2-5 px along the sunlit face (its width walked per layer), a deeper band
    along the shadow edge, lit ledge tops, a dark undercut under every overhang, bedding seams in
    broken runs. moss=True tufts some ledges. Returns the mask."""
    m = np.zeros((H, W), bool)
    seam = np.zeros((H, W), bool)
    for ya, yb, k in layers:
        jr = int(round((hsh(k, seed + 1) - 0.4) * 10))
        jl = int(round((hsh(k, seed + 2) - 0.5) * 8))
        lean = int(round((hsh(k, seed + 3) - 0.5) * 5))
        for y in range(max(0, ya), min(H, yb)):
            v = (y - ya) / max(1, yb - ya - 1)
            a = int(lx(y)) + jl
            b = int(rx(y)) + jr + int(round(lean * v))
            m[y, max(0, a):max(0, min(W, b))] = True
        if 0 <= ya < H and hsh(k, seed + 8) < 0.6:
            seam[ya] = True
    m = fray(m, not lit_right, seed + 4, rate)
    m = fray(m, lit_right, seed + 5, rate)
    R = lambda i: '%s%d' % (ramp, max(0, min(top, i)))
    g[m] = R(body)
    flakes(g, m, ramp, seed + 10, cell=(10, 5), gate=flake_gate, lens=(3, 8), body=body, top=top - 1)
    # the lit band along the sun face and the deep band along the shadow edge, walked per layer
    for ya, yb, k in layers:
        wl = 2 + int(hsh(k, seed + 6) * 4)
        wd = 2 + int(hsh(k, seed + 7) * 3)
        for y in range(max(0, ya), min(H, yb)):
            xs = np.nonzero(m[y])[0]
            if not len(xs):
                continue
            a, b = xs[0], xs[-1]
            w_ = wl + (1 if hsh(y // 3, k, seed + 9) < 0.3 else 0)
            if lit_right:
                lit, dark = slice(b - w_ + 1, b + 1), slice(a, a + wd)
            else:
                lit, dark = slice(a, a + w_), slice(b - wd + 1, b + 1)
            row = g[y]
            row[lit] = np.where(m[y, lit], R(body + 2), row[lit])
            if lit_right and a == 0 or not lit_right and b == W - 1:
                continue
            row[dark] = np.where(m[y, dark], R(body - 1), row[dark])
    # bedding seams in broken runs, with a lit lip below
    runs = hsh_arr(XX // 6, YY, seed + 11) < 0.45
    s = seam & m & runs
    g[s] = R(0)
    lip = np.roll(s, 1, 0) & m & (hsh_arr(XX // 3, YY, seed + 12) < 0.6)
    g[lip] = R(body + 1)
    # rims: sunlit face, ledge tops, undercuts
    face = m & ~np.roll(m, -1 if lit_right else 1, 1)
    face &= (XX > 0) & (XX < W - 1)
    g[face] = R(top - 1)
    g[face & (hsh_arr(XX, YY, seed + 14) < 0.3)] = R(top)
    ledge = m & ~np.roll(m, 1, 0)
    g[ledge] = R(top)
    g[np.roll(ledge, 1, 0) & m & ~face] = R(top - 2)
    under = m & ~np.roll(m, -1, 0)
    g[under] = R(0)
    if moss:
        tuft = ledge & (hsh_arr(XX // 4, YY, seed + 15) < 0.5)
        g[tuft] = 'moss1'
        g[np.roll(tuft, 1, 0) & m & (hsh_arr(XX, YY, seed + 16) < 0.5)] = 'moss0'
        blade = np.roll(tuft, -1, 0) & ~m & (hsh_arr(XX, YY, seed + 17) < 0.45)
        g[blade] = 'moss2'
    return m

# ---------------------------------------------------------------- the scene (static)
STACK_TOP = 48

def _cap(y):
    return 1.3 * max(0, STACK_TOP + 12 - y)       # the crown rounds off in steps

def stack_lx(y):
    return 46 - 0.22 * (y - STACK_TOP) + 3 * noise1(y / 19, 61) + _cap(y)

def stack_rx(y):
    return 98 + 0.13 * (y - STACK_TOP) + 2 * noise1(y / 23, 62) - _cap(y)

def mid_lx(y):
    return 270 - 0.10 * (y - 30) + 2 * noise1(y / 17, 71)

def build_static():
    g = np.full((H, W), None, object)

    # sky strata, domed over the hidden sun, with wisps and smile strokes locking them together
    bounds = [(2, 14), (3, 36), (4, 60), (5, 84), (6, 104), (7, 121)]
    g[:, :] = 'sky1'
    edges = {}
    for k, (slot, y0) in enumerate(bounds):
        e = walk_edge(y0, 7 + 13 * k, amp=3 + (k < 3) * 2, bow=10 + 4 * k)
        edges[k] = e
        g[YY >= e[None, :]] = 'sky%d' % slot
    n = 0
    for k, (slot, y0) in enumerate(bounds):
        for j in range(7):
            n += 1
            x0 = int(-30 + (j + hsh(k, j, 3) * 0.8) * (W + 40) / 7)
            L = 26 + int(hsh(k, j, 4) * 44)
            T = 3 + int(hsh(k, j, 5) * (5 if k < 4 else 3))
            dirn = 1 if hsh(k, j, 6) < 0.5 else -1
            up = hsh(k, j, 7) < 0.3
            wisp(g, edges[k], x0, L, T, 1.4 + 0.5 * hsh(k, j, 8), dirn,
                 'sky%d' % (slot if up else slot - 1), int(round((hsh(k, j, 9) - 0.4) * 5)), n, up=up)
    # smile strokes: a tone darker than the band they float in
    for i in range(16):
        band = int(hsh(i, 21) * 5)
        y0a = bounds[band][1] + 4 + int(hsh(i, 22) * 12)
        x0 = int(hsh(i, 23) * (W - 20))
        L = 9 + int(hsh(i, 24) * 14)
        smile(g, x0, y0a, L, 'sky%d' % (bounds[band][0] - 1), depth=1.5 + 1.5 * hsh(i, 25))
    # dark streaks in the indigo zenith
    for i in range(7):
        x0 = int(hsh(i, 31) * W) - 20
        y0a = 3 + int(hsh(i, 32) * 9)
        L = 20 + int(hsh(i, 33) * 40)
        e = np.full(W, y0a)
        wisp(g, e, x0, L, 2 + int(hsh(i, 34) * 3), 1.6, 1 if i % 2 else -1, 'sky0', 1, 50 + i)

    # far stacks and a sea arch on the horizon, backlit by the hidden sun: ledged, tapering,
    # a lit flank toward the sun and a light rim on top
    far = [(152, 6, 17), (165, 3, 8), (186, 9, 25), (203, 4, 10), (251, 7, 19), (265, 3, 9)]
    fm = np.zeros((H, W), bool)
    for n_, (x0, w, ht) in enumerate(far):
        top = HZ - ht
        for y in range(top, HZ):
            k = (y - top) / ht
            half = w / 2 * (0.45 + 0.55 * k ** 0.7) + (hsh(n_, (y - top) // 3, 9) - 0.5) * 1.6
            cx = x0 + w / 2 + 1.5 * noise1(y / 6, n_ + 20)
            fm[y, int(round(cx - half)):int(round(cx + half)) + 1] = True
    arch = (XX >= 226) & (XX <= 244) & (YY >= HZ - 13 - (np.abs(XX - 233) // 4)) & (YY < HZ)
    arch &= ~(((XX + 0.5 - 235) / 5.5) ** 2 + ((YY + 0.5 - HZ) / 8.5) ** 2 <= 1)
    fm |= arch
    g[fm] = 'far0'
    sunward = (fm & ~np.roll(fm, -1, 1) & (XX < SUNX)) | (fm & ~np.roll(fm, 1, 1) & (XX >= SUNX))
    g[sunward] = 'far1'
    g[fm & ~np.roll(fm, 1, 0)] = 'far2'

    # the sea: light under the sun, darker toward us, a glitter road of short dashes
    g[HZ:, :] = 'sea2'
    for x in range(W):
        g[HZ + 7 + int(2 * noise1(x / 21, 3)):, x] = 'sea1'
        g[HZ + 24 + int(2 * noise1(x / 17, 4)):, x] = 'sea0'
    for x in range(W):
        if abs(x - SUNX) < 30 - 0 and noise1(x / 5, 5) > 0.1:
            g[HZ, x] = 'sea3'
        if noise1(x / 7, 6) > 0.55:
            g[HZ + 3, x] = 'sea3' if abs(x - SUNX) < 40 else 'sea2'

    # the near stack on the left: sandstone layers, lit on its sun side
    layers = strata(STACK_TOP + 2, 162, 41)
    layers = [(STACK_TOP, STACK_TOP + 2, -1)] + layers
    stack = layered_rock(g, 'rock', layers, stack_lx, stack_rx, 40, moss=True)

    # the farther stack on the right edge, its top lost in the cloud
    mlayers = strata(30, 160, 81, 5, 12)
    mid = layered_rock(g, 'mid', mlayers, mid_lx, lambda y: W + 4, 80, lit_right=False, body=1, top=4, rate=0.5, flake_gate=0.32)

    # cloud masses: one over the far stack's head, a low bank of sea mist at the near stack's foot
    c1 = cloud_mass(300, 26, 58, 30, 26, 41)
    c2 = cloud_mass(-4, 152, 44, 12, 18, 47, belly=2) | cloud_mass(42, 164, 18, 6, 10, 49, belly=1)
    cloud = c1 | c2
    shade_cloud(g, c1, 3)
    shade_cloud(g, c2, 5)
    # teeth of the far stack biting up into the cloud's belly
    for x in range(250, W):
        ys = np.nonzero(c1[:, x])[0]
        if len(ys) and hsh(x // 2, 31) < 0.4:
            yb = ys[-1]
            k = 1 + int(4 * hsh(x // 2, 32))
            if mid[min(H - 1, yb + 1), x]:
                g[yb - k + 1:yb + 1, x] = g[min(H - 1, yb + 2), x]

    # boulders at the near stack's foot: round, lit on their sun shoulder, a dark waterline
    fx = int(np.nonzero(stack[156, :160])[0][-1])
    rocks = np.zeros((H, W), bool)
    for i, (dx, dy, rx_, ry_) in enumerate(((3, 157, 5, 5), (12, 160, 4, 3), (-3, 160, 4, 4))):
        rocks |= ((XX + 0.5 - fx - dx) / rx_) ** 2 + ((YY + 0.5 - dy) / ry_) ** 2 <= 1
    rocks &= YY < 162
    rocks &= ~stack | (YY > 150)
    g[rocks] = 'rock1'
    g[rocks & (hsh_arr(XX // 3, YY // 2, 9) < 0.35)] = 'rock2'
    g[rocks & ~np.roll(rocks, -1, 1) | rocks & ~np.roll(np.roll(rocks, 1, 0), -1, 1)] = 'rock3'
    g[rocks & ~np.roll(rocks, 1, 0)] = 'rock4'
    g[rocks & ~np.roll(rocks, -1, 0)] = 'rock0'
    sea = np.isin(g, ['sea0', 'sea1', 'sea2', 'sea3'])
    return g, {'stack': stack, 'mid': mid, 'cloud': cloud, 'c1': c1, 'c2': c2, 'sea': sea, 'foot': (fx, 156)}

# ---------------------------------------------------------------- the lighthouse
TOWER = [
    #   0123456789abcdefghi
    "........f..........",
    ".......dDd.........",
    "......dDDDd........",
    ".....ddDDDDd.......",
    ".....mGGmGGm.......",
    ".....mGGmGGm.......",
    ".....mGGmGGm.......",
    ".....mGGmGGm.......",
    ".....mmmmmmm.......",
    "..rrrrrrrrrrrrr....",
    "..r.r.r.r.r.r.r....",
    "..ppppppppppppp....",
    "....qWWWWWWWw......",
    "....qWWWWWWWw......",
    "....qWWWWWWWww.....",
    "....qWWWWWWWww.....",
    "...qqWWWWWWLww.....",
    "...qWWWWWWWLww.....",
    "...qWWWWWWWWww.....",
    "...qWWWWWWWWww.....",
    "...qWWWWWWWWww.....",
    "..qqWWWWWWWWwww....",
    "..qWWWWWWWWWwww....",
    "..qWWWWWWWWWwww....",
    "..qWWWWWWWWWwww....",
    "..qWWWWWWWWWwww....",
    "..qWWWWWWWWWwww....",
    ".qqWWWWWWWWWwwww...",
    ".qWWWWkkWWWWwwww...",
    ".qWWWkkkkWWWwwww...",
    ".qWWWkkkkWWWwwww...",
    ".qWWWkkkkWWWwwww...",
    ".qWWWkkkkWWWwwww...",
]
TKEY = {'f': 'iron1', 'd': 'iron0', 'D': 'iron1', 'm': 'iron0', 'G': 'glass1', 'r': 'iron0',
        'p': 'iron1', 'q': 'wall0', 'W': 'wall1', 'w': 'wall2', 'L': 'glass0', 'k': 'iron0'}

def lighthouse(g, t):
    """the tower drawn from a slot map, then shaded in code: stone courses, a sunlit right edge,
    a lit dome rim; the lantern glass is the emitter (it flares when the beam faces us)"""
    x0, y0 = LX - 9, STACK_TOP - len(TOWER) + 1
    glass = np.zeros((H, W), bool)
    for j, row in enumerate(TOWER):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            v = TKEY[ch]
            y, x = y0 + j, x0 + i
            if v.startswith('wall'):
                if j % 4 == 2 and ch == 'W' and hsh(i // 3, j, 5) < 0.6:
                    v = 'wall0'                                  # stone courses
                elif ch == 'w' and i == len(row.rstrip('.')) - 1:
                    v = 'wall3'                                  # the sunlit edge
            if ch == 'd' and i >= 9:
                v = 'iron2'                                      # dome rim facing the sun
            g[y, x] = v
            if ch == 'G':
                glass[y, x] = True
    return glass

def beam_angle(t):
    """the lamp turns once per loop, stepped on twos; 0 = pointing right, pi/2 = toward us"""
    return 2 * math.pi * ((t - t % 2) / FRAMES) + 0.35

BEAM_LEVELS = np.array([0.0, 0.10, 0.20, 0.32, 0.46, 0.62])

def beam_field(t):
    """the beam as the eye sees it from the side: a wedge whose length is its sideways component,
    wider and brighter as it swings toward us, dimmed behind the lantern when it points away.
    Intensity = strength x across x along, snapped to six levels so it comes in hard-edged
    bands like everything else. Returns (levels, glare)."""
    a = beam_angle(t)
    side, toward = math.cos(a), math.sin(a)
    d = np.where(side >= 0, XX - LX, LX - XX).astype(float)
    dy = (YY - LY - 0.05 * d).astype(float)
    half = np.maximum(0.5, 1.5 + d * (0.05 + 0.11 * max(0, toward)))
    length = 430 * abs(side) ** 0.7
    q = np.abs(dy) / half
    across = np.where(q < 0.3, 1.0, np.where(q < 0.65, 0.66, np.where(q <= 1.0, 0.36, 0.0)))
    along = np.clip(1 - d / max(1, length), 0, 1) ** 1.1 * (d > 2)
    strength = (0.75 + 0.5 * max(0, toward)) * (0.4 if toward < -0.25 else 1)
    v = strength * across * along
    lv = np.digitize(v, [0.06, 0.16, 0.30, 0.46, 0.66])
    return BEAM_LEVELS[lv], max(0, toward) ** 4

# ---------------------------------------------------------------- the courier
# 13 x 18 chibi (head half the height), drawn facing right; the outline comes from dilation
HEAD = [
    "....hHHHh....",
    "...hHHHHHHh..",
    "..hHHHHHHHHh.",
    "..hHHHHHHSHh.",
    "..hHHHHSSSS..",
    "..hHHHSSeSs..",
    "..hhHHSSSSs..",
    "...hhHSSSs...",
]
NECK = "....FFFFF...."
POSES = {
 'cling': [
    "...fLCCCCSS..",
    "...cLCCCC....",
    "...cCCCCC....",
    "...cCCCCcSS..",
    "....kkkkk....",
    "....kk.kkB...",
    "....kk..BB...",
    "....BB.......",
    "....bb.......",
 ],
 'rise': [
    "..SfLCCCCS...",
    "..S.LCCCC.S..",
    "...cCCCCC....",
    "...ccCCCc....",
    "....kkkkk....",
    "....kkkkk....",
    "....kBkB.....",
    "....bB.bB....",
    ".............",
 ],
 'fall': [
    "...fLCCCC....",
    "..ScLCCCCS...",
    "..S.CCCCC.S..",
    "...ccCCCc....",
    "....kkkkk....",
    "....kk.kk....",
    "....kk.kk....",
    "....BB.BB....",
    "....bb.bb....",
 ],
 'dash': [
    "...fLCCCCSSS.",
    "...cLCCCC....",
    "...cCCCCC....",
    "..kkcCCCc....",
    ".kkkkkkk.....",
    "BBkk.........",
    "bb...........",
    ".............",
    ".............",
 ],
 'land': [
    ".............",
    "...fLCCCC....",
    "..ScLCCCCSS..",
    "...cCCCCC....",
    "...ccCCCcSS..",
    "....kkkkk....",
    "....kk.kkB...",
    "....kk..BB...",
    "....BB.......",
 ],
}
KEY = {'H': 'hair1', 'h': 'hair0', 'S': 'skin1', 's': 'skin0', 'e': 'ol', 'F': 'S1', 'f': 'S0',
       'C': 'coat1', 'c': 'coat0', 'L': 'coat2', 'k': 'coat0', 'B': 'boot1', 'b': 'boot0'}

def courier(pose, facing, scarf):
    """-> (object grid 20 x 15, anchor x, anchor y): anchor = feet centre, bottom row"""
    rows = HEAD + [NECK] + POSES[pose]
    if pose == 'land':                               # squash: the head sits a row lower
        rows = ['.' * 13] + HEAD + [NECK] + POSES[pose][1:]
    g = np.full((20, 15), None, object)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            v = KEY[ch]
            if v in ('S1', 'S0'):
                v = scarf + v[1]
            g[1 + j, 1 + i] = v
    m = g != None
    ring = (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)) & ~m
    g[ring] = 'ol'
    if facing < 0:
        g = g[:, ::-1]
    return g, 7, 19

# ---------------------------------------------------------------- motion
CLING_Y = 112                    # feet row of the clinging start pose
G = 0.32
KICK_T = 22
DASH_T, DASH_N = 40, 6           # dash start, frames
GRAB_Y = 86
SLIDE_T = 66

_FACE = {}
def face_x(y):
    """the sunlit face's x at row y (the courier's hands go one px right of it)"""
    if not _FACE:
        st = static()[1]['stack']
        for yy in range(H):
            xs = np.nonzero(st[yy, :160])[0]
            _FACE[yy] = xs[-1] if len(xs) else 0
    return _FACE[int(y)]

def wall_x(y):
    """the courier hugs the furthest-out rock across her body's rows"""
    return max(face_x(int(y) - k) for k in range(2, 16)) + 6

def state(t):
    """courier (x, y, pose, facing, scarf ramp) at frame t; facing -1 = toward the wall"""
    t = t % FRAMES
    x0 = wall_x(CLING_Y)
    if t < KICK_T:
        return x0, CLING_Y, 'cling', -1, 'scarf'
    # kick: out and up, away from the wall
    vx, vy = 2.0, -3.4
    if t < DASH_T:
        d = t - KICK_T
        x, y = x0 + vx * d * (1 - d / 60), CLING_Y + vy * d + 0.5 * G * d * d
        return x, y, 'rise' if vy + G * d < 0 else 'fall', 1, 'scarf'
    d = DASH_T - KICK_T
    xa, ya = x0 + vx * d * (1 - d / 60), CLING_Y + vy * d + 0.5 * G * d * d
    xg = wall_x(GRAB_Y)
    if t < DASH_T + DASH_N:
        k = (t - DASH_T + 1) / DASH_N
        return xa + (xg - xa) * k, ya + (GRAB_Y - ya) * k, 'dash', -1, 'flash' if t < DASH_T + 1 else 'teal'
    if t < DASH_T + DASH_N + 3:
        return xg, GRAB_Y, 'land', -1, 'teal'
    if t < SLIDE_T:
        return xg, GRAB_Y, 'cling', -1, 'teal' if t < SLIDE_T - 6 else 'flash' if t < SLIDE_T - 5 else 'scarf'
    k = (t - SLIDE_T) / (FRAMES - SLIDE_T)
    y = GRAB_Y + int(round((CLING_Y - GRAB_Y) * (k * k * (3 - 2 * k))))
    return wall_x(y), y, 'cling', -1, 'scarf'

def neck(t):
    x, y, pose, f, _ = state(t)
    return x - 0.5 * f, y - 10 + (1 if pose == 'land' else 0)

def scarf_chain(A, t, ramp, seg=2.0, n=6):
    """the scarf: a rope of n nodes, seg px apart, each pulled toward where the neck was 2i frames
    ago (so it trails her motion and loops exactly) plus the wind, with a flutter travelling down
    it, stepped every 2 frames; 2 px wide tapering to 1"""
    tt = t - t % 2
    x0, y0 = neck(t)
    pts = [(x0, y0)]
    for i in range(1, n):
        lx_, ly_ = neck((t - 2 * i) % FRAMES)
        flut = 0.9 * math.sin(2 * math.pi * (tt / 15 - i / 3.0)) * min(1, i / 2)
        tx, ty = lx_ + 1.4 * i, ly_ + 0.3 * i + flut
        px, py = pts[-1]
        dx, dy = tx - px, ty - py
        L = math.hypot(dx, dy)
        if L < 1e-6:
            dx, dy, L = 1.0, 0.2, math.hypot(1.0, 0.2)
        pts.append((px + dx / L * seg, py + dy / L * seg))
    m1 = np.zeros((H, W), bool)
    shade = np.zeros((H, W), bool)
    for i in range(len(pts) - 1):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        k_n = int(max(abs(xb - xa), abs(yb - ya))) + 1
        for k in range(k_n + 1):
            u = k / k_n
            px, py = int(math.floor(xa + (xb - xa) * u)), int(math.floor(ya + (yb - ya) * u))
            if 0 <= px < W and 0 <= py < H:
                m1[py, px] = True
                if i < 3 and py + 1 < H:
                    m1[py + 1, px] = True
                    shade[py + 1, px] = True
    ring = (np.roll(m1, 1, 0) | np.roll(m1, -1, 0) | np.roll(m1, 1, 1) | np.roll(m1, -1, 1)) & ~m1
    A[ring & (A == None)] = 'ol'
    A[m1] = ramp + '1'
    A[shade & m1] = ramp + '0'
    top = m1 & ~np.roll(m1, 1, 0)
    A[top & m1 & ~shade] = ramp + '2'

def put_sprite(A, spr, ox, oy, only=None):
    for j in range(spr.shape[0]):
        for i in range(spr.shape[1]):
            v = spr[j, i]
            if v is not None and 0 <= oy + j < H and 0 <= ox + i < W:
                A[oy + j, ox + i] = only or v

# ---------------------------------------------------------------- effects
def rain_cells(A, t, n=42, cycles=7, seed=77):
    """opaque 1 px streaks over everything, 12-30 px long; whole spans per loop, so it loops"""
    for i in range(n):
        L = 12 + int(hsh(i, seed + 2) * 19)
        S = H + L
        x = int(hsh(i, seed) * W)
        y = int((hsh(i, seed + 1) * S + cycles * S * t / FRAMES) % S) - L
        A[max(0, y):max(0, min(H, y + L)), x] = 'rain'

def burst(A, t, t0, x, y, normal, seed, n=8, life=12):
    """a dust burst in hard cells: hashed velocities around the wall normal, gravity, size 3-2-1"""
    d = (t - t0) % FRAMES
    if d > life:
        return
    for i in range(n):
        a = math.atan2(normal[1], normal[0]) + (hsh(i, seed) - 0.5) * 2.1
        v = 0.6 + 1.0 * hsh(i, seed + 1)
        px = x + math.cos(a) * v * d
        py = y + math.sin(a) * v * d + 0.05 * d * d
        size = 3 if d < 3 else 2 if d < 7 else 1
        slot = 'flash' if d < 4 else 'dust'
        for dy in range(size):
            for dx in range(size):
                X, Y = int(px) + dx, int(py) + dy
                if 0 <= X < W and 0 <= Y < H and (size < 3 or (dx, dy) not in ((0, 0), (2, 2))):
                    A[Y, X] = slot

def slide_dust(A, t):
    """little puffs scraped off the wall while she slides, one every 6 frames"""
    if not SLIDE_T <= t < FRAMES - 4:
        return
    for k in range(4):
        t0 = t - (t - SLIDE_T) % 6 - 6 * k
        if t0 < SLIDE_T:
            continue
        d = t - t0
        x, y, *_ = state(t0)
        px, py = int(x) - 4 + d // 3, int(y) - 1 - d // 2
        size = 2 if d < 5 else 1
        if d < 12:
            A[py:py + size, px:px + size] = 'dust'

WAVES = (8, 68)                   # frames when a wave breaks on the stack's foot

def surf(A, t, foot_x, foot_y, seed=5):
    """a wave breaking on the stack's foot: a crest rolls in, then spray is thrown up the face in
    hard round clots (launched over 6 frames so it climbs like a column), which shrink as they
    fall; a foam skirt spreads and thins on the water"""
    for w, t0 in enumerate(WAVES):
        d = (t - t0) % FRAMES
        if d >= FRAMES - 12:                          # the crest rolling in
            k = FRAMES - d
            cx = foot_x + 4 + 3.5 * k
            for x in range(int(cx) - 7, int(cx) + 4):
                if 0 <= x < W:
                    hgt = 2 if abs(x - cx + 1) < 3 else 1
                    A[foot_y - hgt + 1:foot_y + 2, x] = 'foam0'
                    A[foot_y - hgt + 1, x] = 'foam1'
        if d < 40:
            for i in range(26):
                st = int(hsh(i, w, seed + 2) * 7)
                dd = d - st
                if dd < 0:
                    continue
                a = math.radians(-96 + 46 * hsh(i, w, seed) ** 1.5)
                v = 1.4 + 2.2 * hsh(i, w, seed + 1)
                px = foot_x + 2 + math.cos(a) * v * dd
                py = foot_y + math.sin(a) * v * dd + 0.13 * dd * dd
                r = 3.0 - dd / 8 - 0.8 * hsh(i, w, seed + 3)
                if r < 0.5 or py > foot_y + 1:
                    continue
                m = (XX + 0.5 - px) ** 2 + (YY + 0.5 - py) ** 2 <= r * r
                A[m] = 'foam1' if dd < 9 else 'foam0'
        if d < 44:                                   # the skirt of foam on the water
            half = 5 + d // 2
            for x in range(foot_x - 2, min(W, foot_x + half)):
                if hsh(x, d // 4, w, seed + 3) < 0.8 - d / 55:
                    A[foot_y + 1, x] = 'foam1' if d < 16 else 'foam0'
                if d > 6 and hsh(x, d // 4, w, seed + 4) < 0.5 - d / 90:
                    A[foot_y + 3, x + 2] = 'foam0'

def ridges(g, t, sea):
    """the swell: crest runs over troughs, undithered; each row's pattern repeats every P px and
    slides one whole P per loop toward the stack (P grows toward us, so near rows move faster)"""
    for i in range(14):
        y = HZ + 9 + int(i * (2.2 + 0.12 * i))
        if y >= H - 1:
            break
        P = 40 + 10 * (i // 3)
        sh = int(P * t / FRAMES)
        xs = (np.arange(W) + sh) % P
        crest = hsh_arr(xs // 4, np.full(W, i), 70) < 0.45 + 0.02 * i
        lead = crest & ~np.roll(crest, 1)
        row, row2 = sea[y], sea[y + 1]
        g[y][crest & row] = 'sea2' if i < 6 else 'sea1'
        g[y + 1][np.roll(crest, 2) & row2 & (i > 4)] = 'sea1' if i < 9 else 'sea0'
        g[y][lead & row & (i > 3)] = 'sea3' if i < 8 else 'sea2'

def swell(A, t):
    """foam lines riding in toward the stack, whole spans per loop"""
    for i in range(9):
        y = HZ + 10 + int(hsh(i, 61) * 34)
        L = 6 + int(hsh(i, 62) * 14) + (y - HZ) // 4
        x = int((hsh(i, 63) * (W + L) - 2 * (W + L) * t / FRAMES) % (W + L)) - L
        for k in range(L):
            if 0 <= x + k < W and hsh(x + k, i, 64) < 0.8:
                A[y, x + k] = 'foam0'

GULL = [["#...#", ".#.#.", "..#.."], ["##.##", "..#.."], [".....", "..#..", "##.##"], ["##.##", "..#.."]]

def gulls(A, t):
    """two gulls hanging in the gale, beating now and then; they hold their place in small loops"""
    for i, (x0, y0, ph) in enumerate(((150, 74, 0), (171, 60, 37))):
        u = 2 * math.pi * (t + ph) / FRAMES
        x = int(round(x0 + 5 * math.sin(u) + 2 * math.sin(3 * u)))
        y = int(round(y0 + 2.5 * math.sin(2 * u + 1)))
        k = ((t + ph) // 3) % 8
        art = GULL[k % 4] if k < 4 else GULL[1]
        for j, row in enumerate(art):
            for c, ch in enumerate(row):
                if ch == '#':
                    A[y + j, x + c - 2] = 'rock0'

def bolt(A, x=168):
    """a 1 px jagged bolt from the dark strata down behind the far stacks, with one fork"""
    y = 12
    while y < HZ - 6:
        A[y, x] = 'bolt'
        y += 1
        if hsh(y, 5) < 0.4:
            x += 1 if hsh(y, 6) < 0.45 else -1
            A[y, x] = 'bolt'
        if y == 78:
            fx, fy = x, y
            for k in range(26):
                fx += 1 if hsh(k, 8) < 0.6 else 0
                fy += 1
                A[fy, fx] = 'bolt'
BOLT_T = 92

# ---------------------------------------------------------------- native light
def gblur(a, sigma):
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    p = np.pad(a, ((r, r), (0, 0)), mode='edge')
    a = sum(w * p[i:i + a.shape[0]] for i, w in enumerate(k))
    p = np.pad(a, ((0, 0), (r, r)), mode='edge')
    return sum(w * p[:, i:i + a.shape[1]] for i, w in enumerate(k))

def rgbf(h):
    return np.array(cl.hex_to_rgb(h), float) / 255

_STATIC = {}
def static():
    if not _STATIC:
        g, info = build_static()
        cloud = info['cloud'].astype(float)
        info['cloud_glow'] = 0.6 * gblur(cloud, 3) + 0.4 * gblur(cloud, 14)
        sun = np.exp(-(((XX - SUNX) / 70.0) ** 2 + ((YY - HZ) / 30.0) ** 2))
        info['tint'] = 0.04 * np.clip(YY / H, 0, 1) + 0.05 * gblur(cloud, 30) + 0.05 * sun
        _STATIC['g'], _STATIC['info'] = g, info
    return _STATIC['g'], _STATIC['info']

def frame(t, post=True):
    g0, info = static()
    g = g0.copy()
    glass = lighthouse(g, t)
    A = np.full((H, W), None, object)                 # actors and effects layer
    ridges(g, t, info['sea'])
    swell(A, t)
    gulls(A, t)
    x, y, pose, f, ramp = state(t)
    if DASH_T + 2 <= t < DASH_T + DASH_N + 2:              # dash afterimages: checker silhouettes
        for k, lag in enumerate((2, 4)):
            xs, ys, ps, fs, _ = state(t - lag)
            if t - lag < DASH_T:
                continue
            spr, ax, ay = courier(ps, fs, 'teal')
            sil = np.zeros((H, W), bool)
            ox, oy = int(xs) - ax, int(ys) - ay
            for j, i in zip(*np.nonzero(spr != None)):
                if 0 <= oy + j < H and 0 <= ox + i < W:
                    sil[oy + j, ox + i] = True
            sil &= ((XX + YY + k) % 2 == 0) if k == 0 else ((XX % 2 == 0) & (YY % 2 == 0))
            A[sil] = 'teal1' if k == 0 else 'teal0'
    spr, ax, ay = courier(pose, f, 'scarf' if ramp in ('flash', 'scarf') else ramp)
    if ramp == 'flash':                               # dash spent / recharged: 2 white frames
        spr = np.where((spr != None) & (spr != 'ol'), 'flash', spr)
    scarf_chain(A, t, 'teal' if ramp == 'teal' else 'scarf')
    put_sprite(A, spr, int(math.floor(x)) - ax, int(math.floor(y)) - ay)
    burst(A, t, KICK_T, int(wall_x(CLING_Y)) - 5, CLING_Y - 3, (1, -0.3), 3)
    burst(A, t, DASH_T + DASH_N, int(wall_x(GRAB_Y)) - 5, GRAB_Y - 6, (1, -0.5), 4, n=6)
    slide_dust(A, t)
    surf(A, t, *info['foot'])
    flash = t in (BOLT_T, BOLT_T + 1)
    if BOLT_T <= t < BOLT_T + 3:
        bolt(A)
    rain_cells(A, t)
    m = A != None
    g[m] = A[m]
    rain = g == 'rain'
    keys = sorted(set(g.ravel()) - {None})
    idx = np.zeros((H, W), np.int32)
    for i, k in enumerate(keys):
        idx[g == k] = i
    rgb = np.array([cl.hex_to_rgb(PAL[k]) for k in keys], float)[idx] / 255
    if not post:
        return Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), 'RGB')
    # native light: the beam in three stepped bands (it whitens the rain it crosses), the lamp's
    # glare, the cloud masses' glow, a low gradient tint, then the lightning lift
    band, glare = beam_field(t)
    beam_c = rgbf(lch(0.95, 0.075, 75))
    actor = np.isin(g, [k for k in keys if str(k).startswith(ACTOR)])
    band = band * ~actor
    add = band[..., None] * beam_c
    rgb[rain & (band > 0)] = 1.0
    gl = glass.astype(float)
    lamp_glow = (0.6 * gblur(gl, 2) + 0.4 * gblur(gl, 8)) * (0.9 + 1.6 * glare)
    r2 = (XX - LX) ** 2 + (YY - LY) ** 2
    lamp_glow += (0.22 + 0.5 * glare) * np.exp(-r2 / (2 * (9.0 + 14 * glare) ** 2))
    boost = 1.8 if flash else 1.0
    add = add + 0.20 * boost * info['cloud_glow'][..., None] * rgbf('#ff74c0') \
        + lamp_glow[..., None] * rgbf(lch(0.95, 0.07, 70))
    rgb = 1 - (1 - rgb) * (1 - np.clip(add, 0, 1))
    lab = cl.rgb_to_oklab(np.clip(rgb, 0, 1).reshape(-1, 3) * 255).reshape(H, W, 3)
    f_ = info['tint']
    lab[..., 0] += f_
    lab[..., 1] += 0.4 * f_ * math.cos(math.radians(335))
    lab[..., 2] += 0.4 * f_ * math.sin(math.radians(335))
    rgb = cl.oklab_to_rgb(lab.reshape(-1, 3)).reshape(H, W, 3) / 255
    if flash:
        rgb = rgb * 0.7 + 0.3 * rgbf('#fbf0ff')
    return Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')

def render_frames(frames=FRAMES):
    return [frame(t) for t in range(frames)]

def export():
    return [{'name': 'rose_squall', 'frames': [], 'images': [f.convert('RGBA') for f in render_frames()],
             'anchor': (0, 0), 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    import time
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/rose'
    for t in [int(a) for a in (sys.argv[2:] or ['0', '30', '42', '60', '92'])]:
        t0 = time.time()
        frame(t).resize((W * 4, H * 4), Image.NEAREST).save('%s-%03d.png' % (out, t))
        print(t, round(time.time() - t0, 2), 's')
