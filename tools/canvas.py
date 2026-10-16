"""A slot canvas for painted scenes: every pixel holds a palette slot name, never a colour.

    from canvas import Canvas, ramps
    PAL = ramps({'rock': '#5b5470', 'moss': '#4a7a3a'}, steps=7)   # rock0..rock6, moss0..moss6
    c = Canvas(320, 180)
    c.bands(0, 120, [('sky0', 0), ('sky2', 60, 14), ('sky4', 110, 12)])  # dithered gradient
    c.bands(0, 120, [('sky0', 0), ('sky2', 60), ('sky4', 110)], dither='none', edge='steps')  # strata
    c.ramp(x, y, 'rock', 3.4)        # rock3 or rock4, picked by an ordered dither
    c.poly([(10, 170), (60, 120), (110, 170)], 'rock2')
    c.outline(actor, mode='own')     # each ring pixel in the darkest step of what it wraps (05)
    c.mirror(643, 160, 30, 480, 300) # left half onto the right about x = 321.5, then wear it (08)
    c.catenary(20, 10, 140, 14, 18, 'ol')                        # a sagging cable (06, 07)
    g2, PAL = glaze(c.g, water, PAL, '#7389a1', 0.55)            # see-through water (08)
    img = c.image(PAL)               # PIL RGB at 1x, exact palette colours

Slots are named BASE + step (rock0 darkest .. rock6 lightest), so light.py can shift them along
their ramp and post.py can find the emissive ones. Shapes are filled on pixel centres with no
anti-aliasing. Helpers take fractional coordinates; the floor decides the pixel.

Dither is a style choice (study 08, plan section 6): 'bayer4' (lofi, 16-bit), 'checker' (a pure
50% checker, the only dither of illustrated and cosy styles: below a quarter of the way it is the
lower tone, then a checker strip, then the upper tone) or 'none' (hard edges: Celeste strata,
Into the Breach sky bands). th(), thresholds(), Canvas.ramp and Canvas.bands take dither=.

Loops: a drifting layer (clouds, strata) loops by wrapping, not by a dissolve: generate it with a
period (bands(period=...), a tile, or twice the screen wide) and draw drift(layer, t, T, trips).
parallax() stacks layers at integer offsets round(factor * cam).
"""
import math, pathlib, sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl

BAYER4 = np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4)
DITHERS = ('bayer4', 'checker', 'none')

def th(x, y, mode='bayer4'):
    """ordered-dither threshold in (0, 1) for pixel (x, y). mode 'checker' gives 0.25 / 0.75 by
    (x + y) parity (a value v becomes 3 states: low, a 50% checker, high); 'none' gives 0.5"""
    if mode == 'bayer4':
        return (BAYER4[int(y) & 3, int(x) & 3] + 0.5) / 16
    if mode == 'checker':
        return 0.25 if (int(x) + int(y)) & 1 == 0 else 0.75
    if mode == 'none':
        return 0.5
    raise ValueError('dither %r: one of %s' % (mode, ', '.join(DITHERS)))

def thresholds(h, w, mode='bayer4', x0=0, y0=0):
    """th() for a whole h x w block whose top-left pixel is (x0, y0) (keeps parity global)"""
    yy, xx = np.mgrid[y0:y0 + h, x0:x0 + w]
    if mode == 'bayer4':
        return (BAYER4[yy & 3, xx & 3] + 0.5) / 16
    if mode == 'checker':
        return np.where((xx + yy) & 1, 0.75, 0.25)
    if mode == 'none':
        return np.full((h, w), 0.5)
    raise ValueError('dither %r: one of %s' % (mode, ', '.join(DITHERS)))

def ramps(bases, steps=7, shift=26, extra=None):
    """{'rock': '#hex'} -> {'rock0': .., 'rock6': ..} with palette.ramp's hue-shifted steps.
    A list of hexes is taken as the ramp itself (darkest first)."""
    from palette import ramp
    pal = {}
    for name, base in bases.items():
        hexes = base if isinstance(base, (list, tuple)) else ramp(base, steps, shift)
        for i, h in enumerate(hexes):
            pal['%s%d' % (name, i)] = h
    pal.update(extra or {})
    return pal

def split(slot):
    """'rock3' -> ('rock', 3); 'eye' -> ('eye', None)"""
    s = str(slot)
    base = s.rstrip('0123456789')
    return (base, int(s[len(base):])) if base != s else (s, None)

def steps_of(pal):
    """{base: number of steps} read from a palette's keys: rock0..rock4 -> {'rock': 5}"""
    out = {}
    for k in pal:
        if str(k).startswith('#'):
            continue
        b, n = split(k)
        if n is not None:
            out[b] = max(out.get(b, 0), n + 1)
    return out

def _hash_arr(a, b, s=0):
    h = (np.asarray(a).astype(np.int64) * 374761393 + np.asarray(b).astype(np.int64) * 668265263
         + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _codes(g):
    """(codes, values): codes[y, x] indexes values; values[0] is None"""
    vals = [None] + sorted(set(g.ravel()) - {None}, key=str)
    idx = {v: i for i, v in enumerate(vals)}
    return np.frompyfunc(idx.__getitem__, 1, 1)(g).astype(np.int32), vals

def _ramp_arrays(g):
    """per pixel: base name (object, None where no ramp) and step (int, -1 where none)"""
    codes, vals = _codes(g)
    bases = np.array([None] + [split(v)[0] if split(v)[1] is not None and not str(v).startswith('#')
                               else None for v in vals[1:]], object)
    steps = np.array([-1] + [split(v)[1] if b is not None else -1 for v, b in zip(vals[1:], bases[1:])])
    return bases[codes], steps[codes]

def _nb(a, dx, dy, fill):
    """value of the neighbour at p + (dx, dy) for every p (fill beyond the frame)"""
    H, W = a.shape[:2]
    out = np.full_like(a, fill)
    ys, ye = max(0, -dy), H - max(0, dy)
    xs, xe = max(0, -dx), W - max(0, dx)
    out[ys:ye, xs:xe] = a[ys + dy:ye + dy, xs + dx:xe + dx]
    return out

def _value_noise(x, cell, seed, period=None):
    """1D smoothstep value noise in [-1, 1] at positions x; periodic in `period` when given"""
    x = np.asarray(x, float)
    if period:
        n = max(1, int(round(period / cell)))
        cell = period / n
    u = x / cell
    i = np.floor(u).astype(np.int64)
    f = u - i
    f = f * f * (3 - 2 * f)
    a, b = i, i + 1
    if period:
        a, b = a % n, b % n
    va = _hash_arr(a, 0, seed) * 2 - 1
    vb = _hash_arr(b, 0, seed) * 2 - 1
    return va + (vb - va) * f

def seam(x, kind, amp=None, seed=0, period=None, cells=(40, 13), run=(5, 15), teeth=(1, 3)):
    """integer row offsets of a band edge at columns x (the shape of a seam):
    'wave'  two octaves of value noise, amp=(3, 1.5) rows at cells (40, 13) px (Celeste strata, 02)
    'steps' flat runs of run=(5, 15) px joined by 1-row steps, within +-amp (02 band edges: a
            1-px step every 5-15 px)
    'teeth' runs of teeth=(1, 3) columns, each jittered by up to +-amp rows (Katana ZERO, 09)
    None or 'straight': zeros. period makes the shape repeat every `period` columns (wrap loops)."""
    x = np.asarray(x, np.int64)
    if kind in (None, 'straight'):
        return np.zeros(x.shape, int)
    if kind == 'wave':
        a = (3, 1.5) if amp is None else (amp if isinstance(amp, (tuple, list)) else (amp, amp / 2))
        v = a[0] * _value_noise(x, cells[0], seed, period) + a[1] * _value_noise(x, cells[1], seed + 7, period)
        return np.floor(v + 0.5).astype(int)
    span = int(period) if period else int(x.max()) - min(0, int(x.min())) + 1
    lo = 0 if period else min(0, int(x.min()))
    xm = (x - lo) % span
    prof = np.zeros(span, int)
    if kind == 'teeth':                            # runs of 1-3 columns, each hung by its own jitter
        a = 2 if amp is None else amp
        pos, k = 0, 0
        while pos < span:
            r = teeth[0] + int(_hash_arr(k, 1, seed) * (teeth[1] - teeth[0] + 1))
            prof[pos:pos + r] = int(math.floor(a * (2 * _hash_arr(k, 2, seed) - 1) + 0.5))
            pos, k = pos + r, k + 1
        cols = np.arange(span)
        prof += np.where(_hash_arr(cols, 5, seed + 2) < 0.1, np.where(prof >= 0, 1, -1), 0)
        return prof[xm]
    if kind == 'steps':                            # flat runs joined by 1-row steps
        a = 3 if amp is None else amp
        pos, v, k = 0, 0, 0
        while pos < span:
            r = run[0] + int(_hash_arr(k, 1, seed) * (run[1] - run[0] + 1))
            prof[pos:pos + r] = v
            pos, k = pos + r, k + 1
            if period and span - pos <= (abs(v) + 1) * run[1]:
                d = -int(np.sign(v))                   # head home so the period closes
            else:
                d = 1 if _hash_arr(k, 2, seed) < 0.5 - 0.35 * v / max(1, a) else -1
            if abs(v + d) > a:
                d = -d                                 # bounce off the clamp: no merged runs
            v = max(-a, min(a, v + d))
        return prof[xm]
    raise ValueError('seam %r: straight, wave, steps or teeth' % (kind,))

class Canvas:
    def __init__(self, w, h, fill=None):
        self.W, self.H = w, h
        self.g = np.full((h, w), fill, object)

    # pixels
    def put(self, x, y, v):
        x, y = int(math.floor(x)), int(math.floor(y))
        if 0 <= x < self.W and 0 <= y < self.H and v is not None:
            self.g[y, x] = v
    set = put                                   # so pixfont and cjkfont can draw into it
    def get(self, x, y):
        x, y = int(math.floor(x)), int(math.floor(y))
        return self.g[y, x] if (0 <= x < self.W and 0 <= y < self.H) else None
    def ramp(self, x, y, base, v, lo=0, hi=6, dither='bayer4', pal=None):
        """put base + a dithered step: v may be fractional (3.4 is rock3 mostly, rock4 sometimes).
        hi is the top step (4 for a 5-step ramp); pal= reads it from the palette instead."""
        if pal is not None:
            hi = min(hi, steps_of(pal).get(base, hi + 1) - 1)
        n = int(math.floor(v + th(x, y, dither)))
        self.put(x, y, '%s%d' % (base, max(lo, min(hi, n))))

    # shapes
    def rect(self, x0, y0, x1, y1, v):
        """fill [x0, x1) x [y0, y1)"""
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(self.W, int(x1)), min(self.H, int(y1))
        if x1 > x0 and y1 > y0:
            self.g[y0:y1, x0:x1] = v
    def hline(self, x0, x1, y, v):
        self.rect(x0, y, x1 + 1, y + 1, v)
    def vline(self, x, y0, y1, v):
        self.rect(x, y0, x + 1, y1 + 1, v)
    def line(self, x0, y0, x1, y1, v):
        import artlib
        for x, y in artlib.line(int(x0), int(y0), int(x1), int(y1)):
            self.put(x, y, v)
    def mask_poly(self, pts):
        """bool mask of the pixels whose centres fall inside the polygon"""
        yy, xx = np.mgrid[0:self.H, 0:self.W] + 0.5
        inside = np.zeros((self.H, self.W), bool)
        n = len(pts)
        for i in range(n):
            (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
            if ya == yb:
                continue
            cross = ((ya > yy) != (yb > yy)) & (xx < (xb - xa) * (yy - ya) / (yb - ya) + xa)
            inside ^= cross
        return inside
    def poly(self, pts, v):
        self.g[self.mask_poly(pts)] = v
    def disc(self, cx, cy, r, v):
        rr = r + 0.15
        x0, x1 = max(0, int(math.floor(cx - rr))), min(self.W, int(math.ceil(cx + rr)) + 1)
        y0, y1 = max(0, int(math.floor(cy - rr))), min(self.H, int(math.ceil(cy + rr)) + 1)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
        sub = self.g[y0:y1, x0:x1]
        sub[(xx - cx) ** 2 + (yy - cy) ** 2 <= rr ** 2] = v
    def fill(self, mask, v):
        self.g[mask] = v

    def bands(self, y0, y1, stops, x0=0, x1=None, dither='bayer4', edge=None, amp=None, seed=0, period=None):
        """vertical gradient of solid slots with seams between them.
        stops: [(slot, y), (slot, y, width), ...] top to bottom; a stop's width is its seam in rows.
        dither: 'bayer4' (craft.md lofi: 10 to 16 rows, narrower reads as stripes), 'checker' (a
        plain band, a 50% checker strip half the width, the next band: 08, 10) or 'none' (a hard
        edge at y: Celeste, Into the Breach; the width is then ignored).
        edge: the seam's shape across x (see seam()): None (ruler straight), 'wave' (Celeste
        strata), 'steps' (flat runs with 1-row steps) or 'teeth' (column-jittered runs); amp in
        rows; each stop gets its own seed. period: repeat the shape every `period` px (a layer
        that drifts with drift() and loops)."""
        x0, x1 = max(0, int(x0)), min(self.W, self.W if x1 is None else int(x1))
        y0, y1 = max(0, int(y0)), min(self.H, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        thr = thresholds(y1 - y0, x1 - x0, dither, x0, y0)
        rest = sorted(stops[1:], key=lambda s: s[1])
        n = np.zeros(yy.shape, np.int32)            # how many seams each pixel is past
        for i, st in enumerate(rest):
            sy, wd = st[1], (st[2] if len(st) > 2 else 0)
            if dither == 'none':
                wd = 0
            if edge not in (None, 'straight'):
                sy = sy + seam(np.arange(x0, x1), edge, amp, seed + 101 * (i + 1), period)[None, :]
            k = (yy - (sy - wd / 2)) / wd if wd else (yy >= sy).astype(float)
            n += (k >= 1) | ((k > 0) & (thr < k))
        lut = np.array([stops[0][0]] + [s[0] for s in rest], object)
        self.g[y0:y1, x0:x1] = lut[n]

    def paste(self, other, ox=0, oy=0):
        """another Canvas or object array (None = clear) on top, at an offset"""
        a = other.g if isinstance(other, Canvas) else np.asarray(other, object)
        h, w = a.shape
        ox, oy = int(ox), int(oy)
        sx0, sy0 = max(0, -ox), max(0, -oy)
        sx1, sy1 = min(w, self.W - ox), min(h, self.H - oy)
        if sx1 <= sx0 or sy1 <= sy0:
            return
        src = a[sy0:sy1, sx0:sx1]
        dst = self.g[oy + sy0:oy + sy1, ox + sx0:ox + sx1]
        m = ~np.equal(src, None)
        dst[m] = src[m]

    def tile(self, tile, x0=0, y0=0, x1=None, y1=None, phase=(0, 0)):
        """repeat a tile (Canvas, object array or list of slot rows; None = see-through) over
        [x0, x1) x [y0, y1). phase shifts the pattern (a drifting or offset-course tiling)."""
        a = tile.g if isinstance(tile, Canvas) else np.asarray(tile, object)
        th_, tw = a.shape
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1 = self.W if x1 is None else min(self.W, int(x1))
        y1 = self.H if y1 is None else min(self.H, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        ry = (np.arange(y0, y1) - y0 + int(phase[1])) % th_
        rx = (np.arange(x0, x1) - x0 + int(phase[0])) % tw
        src = a[ry][:, rx]
        dst = self.g[y0:y1, x0:x1]
        m = ~np.equal(src, None)
        dst[m] = src[m]

    def roll(self, dx, dy=0):
        """a copy moved by (dx, dy) with wrap-around (the content leaving one side re-enters)"""
        c = Canvas(self.W, self.H)
        c.g = np.roll(self.g, (int(dy), int(dx)), (0, 1))
        return c

    def mirror(self, axis2, x0=0, y0=0, x1=None, y1=None, side='left', swap=None, skip_none=False):
        """copy one half of [x0, x1) x [y0, y1) onto the other: g[:, axis2 - x] = g[:, x], so the
        axis sits at x = axis2 / 2 in pixel indices (even axis2: through the centre of column
        axis2 / 2; odd: between two columns, Owlboy's colossus at 321.5 is axis2 = 643).
        side: the source half ('left' or 'right'). swap maps slots that face a way ({'litL':
        'litR'}). skip_none keeps the target where the source is None. Mirror first, then run the
        seeded wear per side and the checker dither last (08: block correlation 0.7-0.85, never 1)."""
        x1 = self.W if x1 is None else min(self.W, int(x1))
        y1 = self.H if y1 is None else min(self.H, int(y1))
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        xs = np.arange(x0, x1)
        src = xs[2 * xs < axis2] if side == 'left' else xs[2 * xs > axis2]
        dst = axis2 - src
        ok = (dst >= x0) & (dst < x1)
        src, dst = src[ok], dst[ok]
        if not len(src):
            return
        a = self.g[y0:y1][:, src]
        if swap:
            a = np.frompyfunc(lambda v: swap.get(v, v), 1, 1)(a).astype(object)
        if skip_none:
            cur = self.g[y0:y1][:, dst]
            a = np.where(np.equal(a, None), cur, a)
        self.g[y0:y1, dst] = a

    def catenary(self, x0, y0, x1, y1, sag, slot, perfect=True):
        """a hanging cable from (x0, y0) to (x1, y1) sagging `sag` px at the middle:
        y = lerp + sag * 4t(1 - t). perfect drops L-corners so the line is 1 px clean (06, 07).
        Returns the pixel list."""
        n = int(3 * (abs(x1 - x0) + abs(y1 - y0) + 2 * abs(sag))) + 2
        t = np.linspace(0, 1, n)
        xs = np.floor(x0 + (x1 - x0) * t + 0.5).astype(int)
        ys = np.floor(y0 + (y1 - y0) * t + sag * 4 * t * (1 - t) + 0.5).astype(int)
        pts = [(int(xs[0]), int(ys[0]))]
        for x, y in zip(xs[1:], ys[1:]):
            if (x, y) != pts[-1]:
                pts.append((int(x), int(y)))
        if perfect and len(pts) > 2:
            out = [pts[0]]
            for i in range(1, len(pts) - 1):
                (ax, ay), (bx, by), (cx, cy) = out[-1], pts[i], pts[i + 1]
                if abs(ax - cx) == 1 and abs(ay - cy) == 1 and (ax == bx or ay == by):
                    continue                            # an L-corner: a and c already touch
                out.append(pts[i])
            out.append(pts[-1])
            pts = out
        for x, y in pts:
            self.put(x, y, slot)
        return pts

    def outline(self, mask, slot=None, outer=True, mode='slot', light=(-1, -1), lift=0.3, parts=None,
                step=0, inner=False, pal=None, seed=0):
        """a 1 px line around a bool mask (outside it if outer, else its own edge pixels).
        mode:
          'slot'       every ring pixel is `slot` (a global outline colour)
          'own'        each ring pixel takes step `step` (0) of the darkest-stepped slot it wraps;
                       the `lift` (30%) of the light-facing ring that faces `light` most takes
                       step + 1, a soft lit arc (Metal Slug 3, 05); lift=0 for none
          'part'       parts = {name: mask} (or a list), back to front: each part's ring in its own
                       darkest step, or slot[name] when slot is a dict (Stardew, 10); inner=True
                       also lines a farther part where a nearer one overlaps it ('auto' only when
                       the two parts are within 0.15 L of each other; needs pal)
          'selective'  ring pixels whose outward normal faces `light` (n.l > 0.2) take the own
                       darkest step, the rest `slot` (default 'ol', a near-black) (Owlboy, 08)
        light is the direction toward the light (y down: (-1, -1) is up-left). Returns the ring."""
        if mode not in ('slot', 'own', 'part', 'selective'):
            raise ValueError("outline mode %r: slot, own, part or selective" % (mode,))
        if mode == 'part':
            return self._part_outline(parts, slot, outer, step, inner, pal)
        mask = np.asarray(mask, bool)
        m = np.pad(mask, 1)
        n = m[:-2, 1:-1] | m[2:, 1:-1] | m[1:-1, :-2] | m[1:-1, 2:]
        if mode == 'slot':
            if outer:
                ring = n & ~mask
            else:
                ring = mask & ~(m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
            self.g[ring] = slot
            return ring
        import morph
        ring = (n & ~mask) if outer else (mask & ~(m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:]))
        own = self._own_slots(mask, ring, outer, step)
        lx, ly = light
        ln = math.hypot(lx, ly) or 1.0
        nx, ny = morph.normals(mask)
        facing = (nx * lx + ny * ly) / ln
        yy, xx = np.nonzero(ring)
        if mode == 'own':
            # the lifted share is the `lift` part of the light-facing ring that faces it most: one
            # soft lit arc per silhouette, not hashed specks (05 reads as runs); ties on a flat
            # side go to the pixels nearer the light, so the arc stays one run
            f = facing[yy, xx] - 1e-5 * (xx * lx + yy * ly) / ln
            lit = f > 0
            up = np.zeros(len(f), bool)
            if lift > 0 and lit.any():
                cut = np.quantile(f[lit], 1 - min(1.0, lift))
                up = lit & (f >= cut)
            vals = own[yy, xx]
            if up.any():
                vals[up] = self._own_slots(mask, ring, outer, step + 1)[yy[up], xx[up]]
            ok = ~np.equal(vals, None)
            self.g[yy[ok], xx[ok]] = vals[ok]
            if slot is not None:                        # rings around non-ramp slots ('eye')
                self.g[yy[~ok], xx[~ok]] = slot
        elif mode == 'selective':
            vals = own[yy, xx]
            dark = (facing[yy, xx] <= 0.2) | np.equal(vals, None)
            vals[dark] = 'ol' if slot is None else slot
            self.g[yy, xx] = vals
        else:
            raise ValueError("outline mode %r: slot, own, part or selective" % (mode,))
        return ring

    def _own_slots(self, mask, ring, outer, step):
        """per ring pixel: base + step of the lowest-stepped inside neighbour (None if none)"""
        bases, steps = _ramp_arrays(self.g)
        best_s = np.full(mask.shape, 1 << 20)
        best_b = np.full(mask.shape, None, object)
        if outer:
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                inside = _nb(mask, dx, dy, False)
                s = np.where(inside, _nb(steps, dx, dy, -1), -1)
                b = _nb(bases, dx, dy, None)
                take = inside & (s >= 0) & (s < best_s)
                best_s[take], best_b[take] = s[take], b[take]
        else:
            take = mask & (steps >= 0)
            best_b[take] = bases[take]
        out = np.full(mask.shape, None, object)
        ok = ring & ~np.equal(best_b, None)
        out[ok] = best_b[ok] + str(step)
        return out

    def _part_outline(self, parts, slot, outer, step, inner, pal):
        if parts is None or len(parts) == 0:
            raise ValueError("outline(mode='part') needs parts= (a dict or list of masks)")
        if isinstance(parts, dict):
            names, masks = list(parts), [np.asarray(parts[k], bool) for k in parts]
        else:
            masks = [np.asarray(p, bool) for p in parts]
            names = list(range(len(masks)))
        union = np.zeros(self.g.shape, bool)
        for pm in masks:
            union |= pm
        line = []
        for nm, pm in zip(names, masks):
            if isinstance(slot, dict) and nm in slot:
                line.append(slot[nm])
                continue
            bases, steps = _ramp_arrays(np.where(pm, self.g, None))
            vals, cnt = np.unique(bases[pm & ~np.equal(bases, None)].astype(str), return_counts=True)
            line.append(vals[cnt.argmax()] + str(step) if len(vals) else slot)
        ring = np.zeros(self.g.shape, bool)
        out = np.full(self.g.shape, None, object)
        for nm, pm, ls in zip(names, masks, line):     # later parts are nearer and win
            if outer:
                r = ~union & (_nb(pm, 0, -1, False) | _nb(pm, 0, 1, False) | _nb(pm, -1, 0, False) | _nb(pm, 1, 0, False))
            else:
                r = pm & ~(_nb(pm, 0, -1, False) & _nb(pm, 0, 1, False) & _nb(pm, -1, 0, False) & _nb(pm, 1, 0, False))
                r &= ~(_nb(union, 0, -1, True) & _nb(union, 0, 1, True) & _nb(union, -1, 0, True) & _nb(union, 1, 0, True))
            out[r] = ls
            ring |= r
        if inner:
            Ls = None
            if inner == 'auto':                         # compare the parts' dominant body slots
                if pal is None:
                    raise ValueError("outline(inner='auto') needs pal= to compare the parts' L")
                Ls = []
                for pm in masks:
                    v, n_ = np.unique(self.g[pm & ~np.equal(self.g, None)].astype(str), return_counts=True)
                    s_ = v[n_.argmax()] if len(v) else None
                    Ls.append(cl.rgb_to_oklab(np.array(cl.hex_to_rgb(pal[s_]), float))[0] if s_ in pal else -9)
            for i, (pi, li) in enumerate(zip(masks, line)):
                for j in range(i + 1, len(masks)):
                    if Ls is not None and abs(Ls[i] - Ls[j]) >= 0.15:
                        continue
                    pj = masks[j]
                    touch = pi & ~pj & (_nb(pj, 0, -1, False) | _nb(pj, 0, 1, False) | _nb(pj, -1, 0, False) | _nb(pj, 1, 0, False))
                    out[touch] = li
                    ring |= touch
        ok = ring & ~np.equal(out, None)
        self.g[ok] = out[ok]
        return ring

    def glaze(self, mask, pal, colour, alpha=0.5, **kw):
        """glaze() in place on this canvas; returns the palette with the new slots"""
        self.g, pal = glaze(self.g, mask, pal, colour, alpha, **kw)
        return pal

    def copy(self):
        c = Canvas(self.W, self.H)
        c.g = self.g.copy()
        return c

    def mask_of(self, *prefixes):
        """bool mask of pixels whose slot starts with any prefix (for post.glow, light, ...)"""
        out = np.zeros((self.H, self.W), bool)
        for v in set(self.g.ravel()) - {None}:
            if str(v).startswith(prefixes):
                out |= self.g == v
        return out

    def image(self, pal, background='#000000'):
        return to_image(self.g, pal, background)

def to_image(g, pal, background='#000000'):
    """object grid of slots -> PIL RGB (None -> background). Unknown slots raise."""
    keys = sorted(set(g.ravel()) - {None}, key=str)
    missing = [k for k in keys if k not in pal and not str(k).startswith('#')]
    if missing:
        raise KeyError('no colour for slots: ' + ', '.join(map(str, missing[:12])))
    idx = np.zeros(g.shape, np.int32)
    for i, k in enumerate(keys):
        idx[g == k] = i + 1
    col = lambda k: cl.hex_to_rgb(k if str(k).startswith('#') else pal[k])
    rgb = np.array([cl.hex_to_rgb(background)] + [col(k) for k in keys], np.uint8)
    return Image.fromarray(rgb[idx], 'RGB')

# ---------------------------------------------------------------- translucency in the palette
def glaze(g, mask, pal, colour, alpha=0.5, add_slots=True, prefix='glz', nearest=False, ramp=True):
    """see-through water, glass or mist as a palette lookup, never a blend at render time (08, 04).
    Every slot under `mask` becomes a glazed slot: OKLab mix(col(slot), colour, alpha), cached as
    '<prefix>_<slot>' in a copy of pal (ramp=True glazes the whole ramp, so light.py can still
    step it), or, with nearest=True (or add_slots=False), the nearest existing palette slot. A
    Canvas or an object grid; returns (new grid of the same kind, new pal). A second glaze of
    another colour or alpha under the same prefix never recolours the first: it takes the next
    free prefix (glz2, glz3, ...)."""
    is_c = isinstance(g, Canvas)
    a = (g.g if is_c else np.asarray(g, object)).copy()
    mask = np.asarray(mask, bool)
    pal = dict(pal)
    tgt = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(colour), float))
    col = lambda s: s if str(s).startswith('#') else pal[s]
    mix = lambda hx: cl.rgb_to_hex(cl.oklab_to_rgb(
        cl.rgb_to_oklab(np.array(cl.hex_to_rgb(hx), float)) * (1 - alpha) + tgt * alpha))
    under = sorted(set(a[mask].ravel()) - {None}, key=str)
    remap = {}
    nearest = nearest or not add_slots
    if nearest:
        keys = [k for k in pal if not str(k).startswith(prefix)]
        lab = cl.rgb_to_oklab(np.array([cl.hex_to_rgb(pal[k]) for k in keys], float))
        for s in under:
            want = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(mix(col(s))), float))
            remap[s] = keys[int(((lab - want) ** 2).sum(1).argmin())]
    else:
        st = steps_of(pal)
        want = {}
        for s in under:
            b, n = split(s)
            todo = ['%s%d' % (b, i) for i in range(st[b])] if (ramp and n is not None and b in st) else [s]
            for s2 in todo:
                want[s2] = mix(col(s2))
        pre, k = prefix, 1
        while any(str(pal.get('%s_%s' % (pre, s2), hx)).lower() != hx.lower() for s2, hx in want.items()):
            k += 1                                      # taken by another glaze colour: next prefix
            pre = '%s%d' % (prefix, k)
        for s2, hx in want.items():
            pal['%s_%s' % (pre, s2)] = hx
        for s in under:
            remap[s] = '%s_%s' % (pre, s)
    sub = a[mask]
    a[mask] = np.frompyfunc(lambda v: remap.get(v, v), 1, 1)(sub)
    if is_c:
        c = Canvas(g.W, g.H)
        c.g = a
        return c, pal
    return a, pal

# ---------------------------------------------------------------- loops, drift and parallax
def wrap_offset(t, T, width, trips=1):
    """the whole-pixel offset of a layer that travels `trips` times its `width` per loop of T
    frames: floor(width * trips * t / T) mod width. Frame T is frame 0 exactly. trips < 0 runs
    the other way."""
    if isinstance(t, (int, np.integer)) and isinstance(trips, (int, np.integer)):
        return (int(width) * int(trips) * int(t) // int(T)) % int(width)
    return int(math.floor(width * trips * t / T)) % int(width)

def drift(layer, t, T, trips=1, axis='x', size=None):
    """a wrapped layer drifting `trips` periods per loop (positive: right or down): no cross-fade,
    the layer's own period carries the loop (02, 06: generate it with that period, e.g. twice the
    screen wide or bands(period=...)). size=(w, h) crops the window. Returns a Canvas."""
    a = layer.g if isinstance(layer, Canvas) else np.asarray(layer, object)
    H, W = a.shape
    if axis == 'x':
        a = np.roll(a, wrap_offset(t, T, W, trips), 1)
    else:
        a = np.roll(a, wrap_offset(t, T, H, trips), 0)
    w, h = size or (W, H)
    c = Canvas(w, h)
    c.g = a[np.arange(h) % H][:, np.arange(w) % W]    # a window wider than the layer repeats it
    return c

def parallax(layers, cam, W, H, wrap=True):
    """compose layers back to front at whole-pixel offsets: layers = [(layer, factor), ...] or
    (layer, factor, (ox, oy)); factor is a number or (fx, fy). A layer pixel (lx, ly) lands at
    screen (lx + ox - round(fx * cam_x), ly + oy - round(fy * cam_y)); None is see-through.
    wrap=True repeats a layer across x (a tile or a looping strip); make factor * travel a whole
    multiple of its width so a pan loops (05, 08, 01). Returns a Canvas W x H."""
    out = Canvas(W, H)
    cx, cy = cam
    for item in layers:
        lay, f = item[0], item[1]
        ox, oy = item[2] if len(item) > 2 else (0, 0)
        fx, fy = (f, f) if not isinstance(f, (tuple, list)) else f
        a = lay.g if isinstance(lay, Canvas) else np.asarray(lay, object)
        lh, lw = a.shape
        dx = int(math.floor(fx * cx + 0.5)) - int(ox)
        dy = int(math.floor(fy * cy + 0.5)) - int(oy)
        ys = np.arange(H) + dy
        xs = np.arange(W) + dx
        vy = (ys >= 0) & (ys < lh)
        if wrap:
            xs, vx = xs % lw, np.ones(W, bool)
        else:
            vx = (xs >= 0) & (xs < lw)
        if not vy.any() or not vx.any():
            continue
        src = a[ys[vy]][:, xs[vx]]
        dst = out.g[np.ix_(np.nonzero(vy)[0], np.nonzero(vx)[0])]
        m = ~np.equal(src, None)
        dst[m] = src[m]
        out.g[np.ix_(np.nonzero(vy)[0], np.nonzero(vx)[0])] = dst
    return out

def loop_dissolve(layer, t, T):
    """make a drifting layer (clouds, mist) seamless: layer(t) and layer(t - T) cross-dissolve over
    the loop with an ordered dither, so frame T matches frame 0. layer(t) -> object grid.
    Lofi looks only: modern styles wrap the layer instead (drift(), wrap_offset())."""
    a, b = layer(t), layer(t - T)
    return np.where(thresholds(*a.shape) < t / T, b, a)

# ---------------------------------------------------------------- framed pictures
def picture(c, x, y, w, h, painter, frame='wood', bracket='stone', checker=(3, 6), steps=(1, 2, 3),
            border=2, seed=0):
    """a framed painting: the one dithered surface in an undithered room (Katana ZERO, 09).
    painter(sub) paints 3-4 flat slots into a Canvas of the inner size (w - 2 border) x (h - 2
    border); each boundary between two tones is then widened into a pure 50% checker strip of
    checker=(3, 6) px (width hashed per 6 px cell; parity is global, so it stays a checker).
    The frame is `border` px of the `frame` ramp at steps (dark, mid, light): outer ring lit top
    and left, dark bottom and right; inner ring the reverse (a raised moulding). 3x3 brackets of
    the `bracket` ramp sit on the corners (bracket=None: none). Keep the painter's tones mid-value
    (L 0.35-0.65) so a picture never outshines the actors."""
    import morph
    iw, ih = max(0, w - 2 * border), max(0, h - 2 * border)
    sub = Canvas(iw, ih)
    painter(sub)
    gi = sub.g
    if checker and iw > 0 and ih > 0:
        yy, xx = np.mgrid[0:ih, 0:iw]
        par = (xx + x + border + yy + y + border) & 1
        lo, hi = checker
        hw = (lo + (hi - lo) * _hash_arr((xx + x) // 6, (yy + y) // 6, seed)) / 2.0
        out = gi.copy()
        for v in sorted(set(gi.ravel()) - {None}, key=str):
            m = gi == v
            if m.all():
                continue
            d = morph.distance(m, 'euclid', border=None)
            ny, nx = morph.nearest(~m & ~np.equal(gi, None))
            if ny.min() < 0:
                continue
            other = gi[ny, nx]
            band = m & (d <= hw)
            o = other[band]
            first = np.array([str(v) < str(q) for q in o], bool)  # the pair's lower name: parity 0
            out[band] = np.where(par[band] == 0, np.where(first, v, o), np.where(first, o, v))
        gi = out
    c.paste(gi, x + border, y + border)
    dk, md, lt = ['%s%d' % (frame, s) for s in steps]
    for r in range(border):
        x0, y0, x1, y1 = x + r, y + r, x + w - 1 - r, y + h - 1 - r
        top, bot = (lt, dk) if r == 0 else (dk, lt)
        if r not in (0, border - 1):
            top = bot = md
        c.hline(x0, x1, y0, top); c.vline(x0, y0, y1, top)
        c.hline(x0, x1, y1, bot); c.vline(x1, y0, y1, bot)
        c.put(x1, y0, md); c.put(x0, y1, md)
    if bracket:                                    # light from the top-left: darker clockwise
        tones = ['%s%d' % (bracket, s_) for s_ in steps]
        pat = ((2, 2, 1), (2, 1, 0), (1, 0, None))
        for cx_, cy_, sx, sy in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
            dim = (sx < 0) + (sy < 0)
            for j in range(3):
                for i in range(3):
                    if pat[j][i] is not None:
                        c.put(cx_ + sx * i, cy_ + sy * j, tones[max(0, pat[j][i] - dim)])
    return c
