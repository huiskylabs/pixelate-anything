"""FX as opaque palette cells that shrink as they age: the water crown where the hull breaks the
surface, the cascades pouring from the bucket lips, the exhaust puffs, and the slam's dust wall
and debris. Built on fx.burst, fx.debris and fx.smoke_puff plus cell sprites drawn here."""
import sys, math
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from canvas import Canvas
import fx

W, H = 304, 224

def _h(a, b=0, s=0):
    h = (int(a) * 374761393 + int(b) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def cell(c, x, y, s, slot, rim=None, shade=None):
    """one opaque cell of size s at (x, y) (top-left): s >= 4 loses its corners; a lit top-left
    rim slot and a shaded bottom-right slot when given"""
    x, y, s = int(x), int(y), int(s)
    for dy in range(s):
        for dx in range(s):
            if s >= 4 and (dx, dy) in ((0, 0), (s - 1, 0), (0, s - 1), (s - 1, s - 1)):
                continue
            v = slot
            if shade and s >= 3 and (dx == s - 1 or dy == s - 1):
                v = shade
            if rim and s >= 3 and (dx + dy) <= 1:
                v = rim
            c.put(x + dx, y + dy, v)

def jet(c, x, y, t_age, n, seed, up=(2.2, 4.2), spread=0.45, g=0.16, lean=0.25, sizes=(5, 4, 3, 2, 1),
        slots=('spray1', 'spray2', 'spray3', 'spray3', 'spray2'), life=22):
    """a column of spray cells thrown up from (x, y): cell i leaves at a hashed frame, flies a
    ballistic arc and shrinks through `sizes` (and `slots`) as it ages. t_age: frames since the
    jet began; cells spawned over its first 14 frames."""
    for i in range(n):
        t0 = _h(i, 1, seed) * 14
        k = t_age - t0
        if k < 0 or k >= life:
            continue
        a = -math.pi / 2 + (2 * _h(i, 2, seed) - 1) * spread + lean * 0.3
        sp = up[0] + (up[1] - up[0]) * _h(i, 3, seed)
        px = x + (2 * _h(i, 4, seed) - 1) * 4 + math.cos(a) * sp * k + lean * k
        py = y + math.sin(a) * sp * k + 0.5 * g * k * k
        if py > y + 2:
            continue
        st = min(len(sizes) - 1, int(k / life * len(sizes)))
        s = sizes[st]
        cell(c, px - s // 2, py - s // 2, s, slots[st], rim='spray3' if s >= 4 else None,
             shade='spray1' if s >= 4 else None)

def foam(c, x0, x1, y, seed, height=(3, 9), body='spray2', cap='spray3', base='spray1', gap='water1'):
    """the foam mass where a hull breaks the surface: lobes of mismatched size along [x0, x1),
    a white cap on each lobe, a teal body, a dark base line and a few dark gaps"""
    x = x0
    k = 0
    while x < x1:
        w = 4 + int(_h(k, 1, seed) * 10)
        hgt = height[0] + int(_h(k, 2, seed) * (height[1] - height[0]))
        if _h(k, 6, seed) < 0.18:
            hgt = max(2, hgt // 2)
        for dx in range(w):
            u = (dx + 0.5) / w
            top = int(round(hgt * math.sqrt(max(0.0, 1 - (2 * u - 1) ** 2))))
            for dy in range(top + 1):
                yy = y - dy
                v = body
                if dy >= top - 1:
                    v = cap
                elif dy <= 1:
                    v = base
                c.put(x + dx, yy, v)
            c.put(x + dx, y + 1, base)
            if _h(x + dx, 3, seed) < 0.4:
                c.put(x + dx, y + 2, 'spray0')
        if _h(k, 4, seed) < 0.3:
            c.put(x + w - 1, y - 1, gap)
        x += w - 1 - int(_h(k, 5, seed) * 2)
        k += 1

def cascade(c, x, y0, y1, seed, width=2):
    """water pouring from a lip at (x, y0) down to the surface at y1: a stream that breaks into
    cells as it falls (white core, teal edge), a splash at the bottom"""
    y = y0
    k = 0
    while y < y1:
        seg = 3 + int(_h(k, 1, seed) * 6)
        gap = 1 if (y - y0) > 10 and _h(k, 2, seed) < 0.45 else 0
        wob = 1 if _h(k, 3, seed) < 0.3 else 0
        wd = width + (1 if (y - y0) > (y1 - y0) * 0.6 else 0)
        for dy in range(seg):
            if y + dy >= y1:
                break
            for dx in range(wd):
                c.put(x + dx + wob, y + dy, 'spray3' if dx == 0 else 'spray2')
        y += seg + gap
        k += 1
    for i in range(7):                                     # the splash: a small crown of cells
        a = math.pi * (0.1 + 0.8 * _h(i, 4, seed))
        r = 2 + 5 * _h(i, 5, seed)
        s = 1 + int(_h(i, 6, seed) * 2.2)
        cell(c, x + math.cos(a) * r * 1.4 - 1, y1 - math.sin(a) * r - 1, s, 'spray3' if s < 2 else 'spray2')

def drips(c, pts, seed, n=3):
    """short falling drips under wet edges: 1x2 cells below each point, hashed lengths"""
    for i, (x, y) in enumerate(pts):
        for k in range(n):
            dy = 2 + int(_h(i, k, seed) * 10) + k * 4
            c.put(x, y + dy, 'spray2')
            c.put(x, y + dy + 1, 'spray1')

def smoke(c, cx, cy, age, seed, r=(3.0, 10.0), rise=6.0, sway=1.5):
    """one opaque sooty puff (fx.smoke_puff on the smoke ramp)"""
    fx.smoke_puff(c, cx, cy, age, seed=seed, r=r, ramp=['smoke%d' % i for i in range(6)],
                  lobes=7, rise=rise, sway=sway)

DUST_LOBE = dict(lit='dust3', body='dust2', shade='dust1', rim='dust1')

def mound(c, x, y, scale, seed, lobes=6, width=1.0):
    """a dust billow sitting on the rim at (x, y): lobes of mismatched radius, the biggest low in
    the middle, upper lobes drawn over lower ones (lit up-left), the crest breaking into cells"""
    pts = []
    for i in range(lobes):
        u = (2 * _h(i, 1, seed) - 1)
        h = _h(i, 2, seed)
        r = scale * (0.45 + 0.55 * (1 - abs(u))) * (0.7 + 0.5 * _h(i, 3, seed))
        px = x + u * scale * 1.5 * width
        py = y - r * 0.5 - h * scale * 1.1 * (1 - abs(u) * 0.6)
        pts.append((py, px, max(1.2, r)))
    top = min(p[0] for p in pts)
    for py, px, r in sorted(pts, reverse=True):         # lower lobes first, the crest last
        if r < 1.8:
            cell(c, px - 1, py - 1, 2, 'dust3')
        else:
            crest = py - top < scale * 0.5
            lobe(c, px, py, r, lit='dust4' if crest else 'dust3', body='dust2' if crest else 'dust1',
                 shade='dust1' if crest else 'dust0', rim='dust1' if crest else 'dust0')
    for i in range(int(3 + scale)):                     # the crest breaks into shrinking cells
        a = math.radians(-150 + 120 * _h(i, 5, seed))
        d = scale * (1.6 + 1.2 * _h(i, 6, seed))
        sz = max(1, int(round(scale * 0.35 * (1 - _h(i, 7, seed) * 0.6))))
        cell(c, x + math.cos(a) * d * 1.3 - sz / 2.0, y - scale * 0.8 + math.sin(a) * d - sz / 2.0, min(4, sz),
             'dust3' if sz < 3 else 'dust2', rim='dust4' if sz >= 3 else None)

def dust_wall(c, ix, iy, y_rim, seed, reach=(0, W), back=None, calm=None):
    """the slam's dust thrown across the full width: a big billow at the impact (ix, iy), mounds
    shrinking (older) toward both edges, loose cells flung ahead. calm: (x0, x1) kept low (the
    soldier must stay readable). back: the canvas for the billows."""
    back = back if back is not None else c
    for side in (-1, 1):
        span = (ix - reach[0]) if side < 0 else (reach[1] - ix)
        d = 14.0
        k = 0
        while d < span + 6:
            u = min(1.0, d / float(span))
            x = ix + side * d
            scale = (9.0 * (1 - u) ** 1.1 + 2.2) * (0.62 + 0.75 * _h(k, 9, seed + side))
            if calm and calm[0] - 6 <= x <= calm[1] + 6:
                scale = min(scale, 3.0)
            mound(back, x, y_rim(x) + 2, scale, seed * 7 + k * 3 + (side > 0), lobes=4 + int(3 * (1 - u)),
                  width=0.8)
            d += scale * (1.5 + 0.8 * _h(k, 1, seed + side))
            k += 1
        for i in range(12):                              # leading cells, shrinking as they go
            u = 0.6 + 0.42 * _h(i, 2, seed + side)
            x = ix + side * u * span
            if calm and calm[0] <= x <= calm[1]:
                continue
            y = y_rim(x) - 4 - 14 * _h(i, 3, seed + side) * (1.2 - u)
            sz = max(1, int(round(3.0 * (1 - u) + 0.9)))
            cell(c, x, y, sz, 'dust3' if sz < 3 else 'dust2', rim='dust4' if sz >= 3 else None)
    # a continuous low band along the rim, edge to edge: lumpy top, taller near the impact
    for x in range(reach[0], reach[1]):
        u = abs(x - ix) / float(max(ix - reach[0], reach[1] - ix))
        if calm and calm[0] <= x <= calm[1]:
            hgt = 2
        else:
            hgt = int(round(2 + 7 * (1 - u) ** 1.4 + 2 * _h(x // 5, 3, seed)))
        y0 = y_rim(x) + 2
        for k in range(hgt):
            back.put(x, y0 - k, 'dust1' if k < 2 else ('dust3' if k == hgt - 1 else 'dust2'))
    # the impact billow behind the claw and a crown of big cells thrown up
    mound(back, ix - 6, iy + 2, 12.0, seed + 99, lobes=11, width=1.1)
    mound(back, ix + 10, iy + 1, 9.0, seed + 98, lobes=8, width=0.9)
    for i in range(24):
        a = math.radians(-165 + 150 * _h(i, 11, seed))
        r = 16 + 30 * _h(i, 12, seed) ** 0.8
        sz = max(1, int(round(5 * (1 - r / 48.0) + 0.8)))
        x = ix + math.cos(a) * r * 1.3
        y = iy - 10 + math.sin(a) * r * 0.9
        cell(c, x - sz / 2.0, y - sz / 2.0, sz, 'dust3' if sz < 3 else 'dust2', rim='dust4' if sz >= 3 else None,
             shade='dust1' if sz >= 4 else None)

def bursts(c, pts, t, seed, slots=('dust3', 'dust2', 'dust1'), n=9):
    """fx.burst crowns at hashed rim points (each spawned at its own frame before t)"""
    for i, (x, y) in enumerate(pts):
        t0 = t - 1 - int(_h(i, 1, seed) * 8)
        fx.burst(c, x, y, t, t0, n=n, slots=slots, life=12, speed=(0.6, 1.8), normal=(0, -1),
                 spread=70, g=0.08, seed=seed + i)

def plume(c, x, y, height, width, seed, lean=0.0):
    """an erupting column of water from the surface at (x, y): a solid tapered base (lit left,
    shaded right) that breaks into shrinking cells toward the top, droplets falling outward"""
    solid = int(height * 0.55)
    for dy in range(solid):
        u = dy / float(height)
        half = width / 2.0 * (1 - u) ** 0.7 + 0.6 * (_h(dy // 2, 1, seed) - 0.5)
        cx = x + lean * dy
        xl, xr = int(round(cx - half)), int(round(cx + half))
        for xx in range(xl, xr + 1):
            v = 'spray2'
            if xx <= xl + max(0, int(half * 0.35)):
                v = 'spray3'
            elif xx >= xr - max(0, int(half * 0.3)):
                v = 'spray1'
            c.put(xx, y - dy, v)
        if _h(dy, 2, seed) < 0.18 and half > 2:          # a notch: the column is not a cone
            c.put(xr, y - dy, None) if False else c.put(xr, y - dy, 'spray0')
    # breaking top: cells shrink with height (age), scatter outward
    k = 0
    yy = y - solid
    while yy > y - height - 6:
        u = (y - yy) / float(height)
        s = max(1, int(round(width * 0.42 * (1.25 - u))))
        s = min(s, 5)
        off = (2 * _h(k, 3, seed) - 1) * width * 0.45 * u
        cell(c, x + lean * (y - yy) + off - s / 2.0, yy - s / 2.0, s, 'spray3' if s <= 2 else 'spray2',
             rim='spray3', shade='spray1')
        yy -= s + 1 + int(_h(k, 4, seed) * 2)
        k += 1
    for i in range(5):                                     # droplets falling back outward
        side = -1 if i % 2 else 1
        dx = side * (width * 0.5 + 2 + 6 * _h(i, 5, seed))
        dy = height * (0.35 + 0.5 * _h(i, 6, seed))
        s = 2 if _h(i, 7, seed) < 0.4 else 1
        cell(c, x + dx, y - dy, s, 'spray3' if s == 1 else 'spray2')

def sheet(c, x, y0, y1, seed, width=2):
    """water sheeting off an edge: a thin falling streak with breaks, white core and teal edge"""
    y = y0
    k = 0
    while y < y1:
        seg = 2 + int(_h(k, 1, seed) * 7)
        for dy in range(seg):
            if y + dy >= y1:
                break
            for dx in range(width):
                c.put(x + dx, y + dy, 'spray3' if (dx == 0 and k % 3 != 2) else 'spray2')
        y += seg + (1 if _h(k, 2, seed) < 0.5 else 2)
        k += 1

def lobe(c, cx, cy, r, lit='spray3', body='spray2', shade='spray1', rim='spray0'):
    """one opaque water lobe: a lit cap up-left, a shaded crescent down-right"""
    rr = r + 0.2
    for y in range(int(math.floor(cy - rr)), int(math.ceil(cy + rr)) + 1):
        for x in range(int(math.floor(cx - rr)), int(math.ceil(cx + rr)) + 1):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d2 = dx * dx + dy * dy
            if d2 > rr * rr:
                continue
            v = body
            s = (dx + dy) / max(0.8, rr)
            if s < -0.45:
                v = lit
            elif s > 0.55:
                v = shade if (r >= 2 or s < 0.95) else rim
            if r >= 3 and d2 > (rr - 1) ** 2 and s > 0.7:
                v = rim
            c.put(x, y, v)

def crown(c, x, y, size, seed, arms=5, spread=(-155, -25), lean=0.0):
    """a splash crown erupting from (x, y): `arms` fans of lobes that are big and merged at the
    base and shrink to separate cells toward the tips (the cells' age), arcing over with gravity"""
    angs = []
    for i in range(arms):
        u = (i + 0.5 + 0.6 * (_h(i, 1, seed) - 0.5)) / arms
        angs.append(math.radians(spread[0] + (spread[1] - spread[0]) * u))
    for i, a in enumerate(angs):
        Ln = size * (0.55 + 0.6 * _h(i, 2, seed)) * (1.15 if abs(math.cos(a)) < 0.4 else 0.85)
        r0 = max(1.6, size * (0.13 + 0.06 * _h(i, 3, seed)))
        pts = []
        t = 0.0
        while t < 1.0:
            r = r0 * (1 - t) ** 0.85 + 0.55
            px = x + math.cos(a) * Ln * t + lean * Ln * t
            py = y + math.sin(a) * Ln * t + 0.35 * Ln * t * t
            pts.append((px, py, r))
            gap = 1.0 if t < 0.45 else 1.9
            t += max(0.05, (r * gap) / Ln)
        for (px, py, r) in reversed(pts):
            if r < 1.2:
                cell(c, px, py, 1, 'spray3')
            elif r < 1.8:
                cell(c, px - 1, py - 1, 2, 'spray3' if _h(int(px), int(py), seed) < 0.5 else 'spray2')
            else:
                lobe(c, px, py, r)
    lobe(c, x, y - size * 0.08, max(2.0, size * 0.2))
