"""Light in palette steps: the retro way to light a scene, with no colour outside the palette.

Build a light map from point lights, cones and bands, then shift every slot along its own ramp
(rock3 -> rock5 near a torch, rock3 -> rock1 in the dark) with a dither at the edges of each
step. The result is still a grid of palette slots, so era limits and palette swaps hold.
For the modern look (soft glow over crisp pixels) use post.py on top, or instead.

    from light import Light, rim, void_fade
    L = Light(320, 180, ambient=-1)              # -1: everything one step darker than drawn
    L.point(120, 90, radius=46, power=2.0)       # +2 steps at the centre, fading to 0 at the radius
    L.gauss(240, 60, 18, power=2.0)              # a soft lamp pool (Stardew: sigma 18 px, 10)
    L.cone(160, 20, angle=90, spread=18, length=150, power=1.5)    # a lamp or a light shaft
    L.band(y0=140, y1=180, power=1.5)            # glow from below (lava), or a sunlit floor
    g2 = L.apply(canvas.g, emissive=('fire', 'lamp'), pal=PAL, dither='checker')
    rim(c, actor, lights=[(250, 60, 2.0)])       # 1 px warm rim from the nearest lamp (09)
    rim(c, pillar, 'rim_lav', toward=('left', 'right'), behind=sky, second='checker')  # back rim (08)
    rim(c, monolith, 'stone3', toward='up', every=2)                # a dotted rim (01)
    void_fade(c, 52, 18, 'top', pal=PAL)         # the slab fades into exact black in teeth (09)

Pass pal= so each ramp keeps to its own length (5-step iso ramps, 7-step canvas ramps): a step
past the top or bottom of a ramp clamps there. dither: 'bayer4' (lofi), 'checker' (one 50%
checker between two steps: illustrated, cosy styles) or 'none' (hard steps).

Rules that keep it looking drawn (from Dragonfire Keep):
  - Lights are wide and few: 2 to 4 per scene. A dozen small ones read as polka dots.
  - Flicker the power, not the position, and hold it a few frames (use flicker()).
  - Emissive slots (flames, lit windows, eyes, outlines) are never shifted.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import canvas as _cv
import morph

BAYER4 = np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4)

def flicker(t, seed=0, hold=3, amount=0.15, T=None):
    """a stepped flicker factor around 1.0, held for `hold` frames (flame reads as flame).
    T: the loop length; t is wrapped into [0, T) so flicker(T) == flicker(0) and the loop is
    seamless (pick T % hold == 0 so the last hold is as long as the others; None: no wrap)."""
    if T:
        t = t % T
    k = int(t // hold)
    h = ((k * 374761393 + seed * 668265263) & 0xFFFFFFFF)
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return 1.0 + amount * (((h ^ (h >> 16)) & 0xFFFF) / 32768.0 - 1.0)

def _step_table(g, pal, steps, emissive, keep):
    """per distinct slot: (base, step, ramp length) or None when it must not move"""
    if isinstance(emissive, str):
        emissive = (emissive,)
    emissive = tuple(emissive or ())
    keep = (keep,) if isinstance(keep, str) else tuple(keep or ())
    nsteps = _cv.steps_of(pal) if pal is not None else {}
    codes, vals = _cv._codes(g)
    info = [None]
    for v in vals[1:]:
        s = str(v)
        b, n = _cv.split(s)
        if s.startswith('#') or n is None or s in keep or (emissive and s.startswith(emissive)):
            info.append(None)
            continue
        k = nsteps.get(b) if pal is not None else steps
        if k is None:
            k = steps if steps is not None else n + 1   # not in pal: never step past what is drawn
        info.append((b, n, int(k)))
    return codes, vals, info

def _shift(g, lv, pal=None, steps=7, emissive=(), keep=('ol',)):
    """every ramp slot moved by lv steps (an int array), clamped to its ramp; vectorised"""
    codes, vals, info = _step_table(g, pal, steps, emissive, keep)
    n = np.array([-1] + [i[1] if i else -1 for i in info[1:]])
    k = np.array([0] + [i[2] if i else 0 for i in info[1:]])
    kmax = int(k.max()) if len(k) else 0
    table = np.full((len(vals), max(1, kmax)), None, object)
    for c_, i in enumerate(info):
        if i:
            for s in range(i[2]):
                table[c_, s] = '%s%d' % (i[0], s)
    movable = n[codes] >= 0
    new = np.clip(n[codes] + lv, 0, np.maximum(k[codes] - 1, 0))
    out = np.array(g, object, copy=True)
    out[movable] = table[codes[movable], new[movable]]
    return out

class Light:
    def __init__(self, w, h, ambient=0.0):
        self.W, self.H = w, h
        self.map = np.full((h, w), float(ambient))
        self.yy, self.xx = np.mgrid[0:h, 0:w].astype(float) + 0.5

    def point(self, x, y, radius, power=1.5, squash=1.0, falloff=1.0):
        """a round pool of light; squash < 1 flattens it into an ellipse on a floor"""
        r = np.hypot(self.xx - x, (self.yy - y) / squash)
        self.map += power * np.clip(1 - r / radius, 0, None) ** falloff
        return self

    def gauss(self, x, y, sx, sy=None, power=1.5):
        """a soft Gaussian pool: power * exp(-d^2 / 2 sigma^2), sy for an elliptical floor pool.
        Stardew's lamps measure sigma 18 native px (10)."""
        sy = sx if sy is None else sy
        self.map += power * np.exp(-0.5 * (((self.xx - x) / sx) ** 2 + ((self.yy - y) / sy) ** 2))
        return self

    def cone(self, x, y, angle, spread, length, power=1.5, soft=0.35):
        """light from (x, y) toward `angle` degrees (0 = right, 90 = down), `spread` degrees each side"""
        a = math.radians(angle)
        dx, dy = self.xx - x, self.yy - y
        d = np.hypot(dx, dy)
        off = np.abs((np.degrees(np.arctan2(dy, dx) - a) + 180) % 360 - 180)
        edge = np.clip((spread - off) / max(1e-6, spread * soft), 0, 1)
        self.map += power * edge * np.clip(1 - d / length, 0, None)
        return self

    def segment(self, x0, y0, x1, y1, radius, power=1.5):
        """light along a line (a neon tube, a fire breath, a lava crack)"""
        dx, dy = x1 - x0, y1 - y0
        l2 = dx * dx + dy * dy or 1
        s = np.clip(((self.xx - x0) * dx + (self.yy - y0) * dy) / l2, 0, 1)
        d = np.hypot(self.xx - (x0 + s * dx), self.yy - (y0 + s * dy))
        self.map += power * np.clip(1 - d / radius, 0, None)
        return self

    def band(self, y0, y1, power=1.0):
        """a vertical ramp: 0 at y0 rising to `power` at y1 (y1 < y0 for light from above)"""
        if y1 == y0:
            k = (self.yy >= y0).astype(float)
        else:
            k = np.clip((self.yy - y0) / (y1 - y0), 0, 1)
        self.map += power * k
        return self

    def mask(self, m, power):
        """add power where a bool mask is set (a sunlit patch drawn by hand)"""
        self.map += power * m
        return self

    def levels(self, lo=-3, hi=3, dither='bayer4'):
        """integer step per pixel, dithered between steps: 'bayer4' (16 levels), 'checker' (low,
        a 50% checker, high: thresholds 0.25 / 0.75 by (x + y) parity) or 'none' (rounded)"""
        thr = _cv.thresholds(self.H, self.W, dither)
        return np.clip(np.floor(self.map + thr), lo, hi).astype(int)

    def apply(self, g, emissive=(), steps=7, lo=-3, hi=3, keep=('ol',), pal=None, dither='bayer4'):
        """shift every ramp slot (BASE + digit) by the light level; others stay as drawn.
        pal: read each base's ramp length from the palette (rock0..rock4 -> 5 steps), so a step
        never leaves the ramp; without pal every ramp is `steps` long (default 7). Slots that are
        hex colours, in `keep`, or start with an `emissive` prefix never move. g: a slot grid
        or a Canvas; returns a new slot grid."""
        if isinstance(g, _cv.Canvas):
            g = g.g
        return _shift(g, self.levels(lo, hi, dither), pal, steps, emissive, keep)

# ---------------------------------------------------------------- rim light
def _dirs(toward):
    if toward is None:
        return [(0, -1), (0, 1), (-1, 0), (1, 0)]
    return morph._facings(toward, 4)

def _paint(g, where, slot, pal, steps):
    """write slot at where: a slot name, a callable(old) -> new, or an int k (the pixel's own
    ramp moved k steps, clamped)"""
    if not where.any():
        return
    if isinstance(slot, (int, np.integer)):
        lv = np.zeros(g.shape, int)
        lv[where] = int(slot)
        sh = _shift(np.where(where, g, None), lv, pal, steps if steps else 7, (), ())
        g[where] = sh[where]
    elif callable(slot):
        g[where] = np.frompyfunc(slot, 1, 1)(g[where])
    else:
        g[where] = slot

def rim(c, mask, slot='rim1', toward=(0, -1), lights=None, behind=None, every=1, phase=0,
        cos=(0.3, 0.55), slots=('rim0', 'rim1'), second=None, skip_bottom=0.7, tips=False, corner=None,
        pal=None, steps=None, seed=0, occlude=8):
    """a 1 px edge light on the pixels of `mask`, painted into c (a Canvas or slot grid) in place.
    Returns the bool mask of painted pixels. Three ways to pick the edge:
      toward   the pixels whose neighbour toward the light ('up', 'left', (dx, dy), a light
               vector, or a list) is outside the mask: a directional rim (01, 02, 06).
               corner= paints the pixels that are edges in two of the directions (02: the
               brightest step on corners)
      behind   only where that neighbour is `behind` (a bool mask of sky or farther layers, or a
               tuple of slot prefixes): a back rim where a layer meets the background (06, 08).
               toward=None means any side. second paints the next pixel inward in slots[0]:
               a share in [0, 1] (hashed) or 'checker'; slot then defaults to slots[1]
      lights   [(x, y, power), ...]: per edge pixel the light with the largest power / d^1.5;
               k = n . l with the outward normal n; slots[1] where k > cos[1], slots[0] where
               cos[0] < k <= cos[1]; skips bottom-facing edges (n_y > skip_bottom) and, unless
               tips, 1 px tips, and edges the shape itself shades: a march of up to `occlude`
               px toward the lamp that meets the mask (the inside of the far leg). Recompute
               each frame when lamps move (09)
    every=2 lights every other pixel along the edge (a dotted rim, 01), from `phase`.
    A slot can be a name, a callable(old_slot) -> slot, or an int: the pixel's own ramp lifted
    that many steps (pal= or steps= bound it)."""
    g = c.g if isinstance(c, _cv.Canvas) else c
    mask = np.asarray(mask, bool)
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W]
    painted = np.zeros((H, W), bool)

    def dotted(m, dx, dy):
        if every <= 1:
            return m
        idx = xx if abs(dy) >= abs(dx) else yy      # walk along the edge
        return m & ((idx + phase) % every == 0)

    if lights is not None:
        nx, ny = morph.normals(mask)
        edge = morph.edges(mask)
        if not tips:
            nb = sum(_cv._nb(mask, dx, dy, False).astype(int) for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)))
            edge &= nb >= 2
        edge &= ny <= skip_bottom
        px, py = xx + 0.5, yy + 0.5
        best = np.full((H, W), -1.0)
        lx = np.zeros((H, W)); ly = np.zeros((H, W))
        for (x, y, p) in lights:
            dx, dy = x - px, y - py
            d = np.hypot(dx, dy) + 1e-6
            s = p / d ** 1.5
            take = s > best
            best[take] = s[take]
            lx[take], ly[take] = dx[take] / d[take], dy[take] / d[take]
        k = nx * lx + ny * ly
        e = dotted(edge, 0, 1) if every > 1 else edge
        cand = e & (k > cos[0])
        if occlude and cand.any():                      # self-shadow: the shape blocks the lamp
            cy, cx = np.nonzero(cand)
            ux, uy = lx[cy, cx], ly[cy, cx]
            n_in = np.zeros(len(cy), int)               # from 2.5 px out, 2 hits: a stair-step
            for st in np.arange(2.5, float(occlude) + 0.5, 1.0):     # edge never shades itself
                qx = np.floor(cx + 0.5 + ux * st).astype(int)
                qy = np.floor(cy + 0.5 + uy * st).astype(int)
                ok = (qx >= 0) & (qx < W) & (qy >= 0) & (qy < H)
                n_in[ok] += mask[qy[ok], qx[ok]]
            hit = n_in >= 2
            e = e.copy()
            e[cy[hit], cx[hit]] = False
        hi = e & (k > cos[1])
        lo_ = e & (k > cos[0]) & ~hi
        _paint(g, lo_, slots[0], pal, steps)
        _paint(g, hi, slots[1], pal, steps)
        return hi | lo_

    if behind is not None and not isinstance(behind, np.ndarray):
        prefixes = (behind,) if isinstance(behind, str) else tuple(behind)
        b = np.zeros((H, W), bool)
        for v in set(g.ravel()) - {None}:
            if str(v).startswith(prefixes):
                b |= g == v
        behind = b
    if behind is not None and slot == 'rim1' and second is not None:
        slot = slots[1]
    hits = []
    for dx, dy in _dirs(toward if (toward is not None or behind is None) else None):
        out = ~_cv._nb(mask, dx, dy, True)              # the art carries on past the frame: no rim there
        if behind is not None:
            out &= _cv._nb(np.asarray(behind, bool), dx, dy, False) | np.equal(_cv._nb(g, dx, dy, None), None)
        e = dotted(mask & out, dx, dy)
        hits.append(e)
        painted |= e
        if second is not None:
            inner = _cv._nb(e, dx, dy, False) & mask & ~painted
            if second == 'checker':
                inner &= (xx + yy) & 1 == 0
            else:
                inner &= _cv._hash_arr(xx, yy, seed + 9) < float(second)
            _paint(g, inner, slots[0], pal, steps)
    _paint(g, painted, slot, pal, steps)
    if corner is not None and len(hits) > 1:
        cnt = sum(h.astype(int) for h in hits)
        _paint(g, cnt >= 2, corner, pal, steps)
    return painted

# ---------------------------------------------------------------- void fade
def _fade_d(H, W, y_edge, length, side, jitter, run, seed):
    """d in [0, 1+] per pixel: 0 on the lit side of the edge, 1 where the void is complete"""
    along = W if side in ('top', 'bottom') else H
    length = max(float(length), 1e-6)                   # length 0: a hard cut at y_edge
    j = _cv.seam(np.arange(along), 'teeth', jitter, seed, teeth=run) if jitter else np.zeros(along, int)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    if side == 'top':
        return (y_edge + j[None, :] - yy) / length
    if side == 'bottom':
        return (yy - (y_edge + j[None, :])) / length
    if side == 'left':
        return (y_edge + j[:, None] - xx) / length
    if side == 'right':
        return (xx - (y_edge + j[:, None])) / length
    raise ValueError("side %r: top, bottom, left or right" % (side,))

def void_fade(img, y_edge, length=18, side='top', jitter=2, run=(1, 4), levels=8, gamma=1.6, seed=0,
              void=None, steps_down=4, pal=None):
    """fade a lit slab into exact black across `length` px past `y_edge` (a row for top and
    bottom, a column for left and right), with a column-jittered edge: runs of run=(1, 4)
    columns, each hung by up to +-jitter px, so the dark comes down in teeth (Katana ZERO, 09:
    ceiling 16 rows, floor 22, jitter 2). y_edge is where the fade starts; the void lies
    `length` px further out.
    img: a PIL image or an H x W x 3 array (q = floor(d * levels) / levels, rgb * (1 - q)^gamma,
    exact #000000 where d >= 1), or a Canvas or slot grid (each slot steps down round(q *
    steps_down) along its ramp, and becomes `void` where d >= 1; None renders as the background).
    Returns the same kind (a Canvas is changed in place)."""
    from PIL import Image
    is_img = isinstance(img, Image.Image)
    is_c = isinstance(img, _cv.Canvas)
    if is_c or (isinstance(img, np.ndarray) and img.dtype == object):
        g = img.g if is_c else img
        H, W = g.shape
        d = _fade_d(H, W, y_edge, length, side, jitter, run, seed)
        q = np.floor(np.clip(d, 0, 1) * levels) / levels
        out = _shift(g, -np.floor(q * steps_down + 0.5).astype(int), pal, None, (), ())
        out[d >= 1] = void
        if is_c:
            img.g = out
            return img
        return out
    mode = img.mode if is_img else None
    if is_img and mode not in ('RGB', 'RGBA', 'L'):
        img, mode = img.convert('RGB'), 'RGB'
    src = np.asarray(img)
    a = src.astype(float)
    H, W = a.shape[:2]
    d = _fade_d(H, W, y_edge, length, side, jitter, run, seed)
    q = np.floor(np.clip(d, 0, 1) * levels) / levels
    k = (1 - q) ** gamma
    k[d >= 1] = 0                                       # exact black past the fade
    if a.ndim == 2:
        a = a * k
    else:                                               # colour channels only; alpha stays
        a[..., :3] = a[..., :3] * k[..., None]
    a = np.clip(np.floor(a + 0.5), 0, 255).astype(src.dtype if src.dtype == np.uint8 else np.uint8)
    return Image.fromarray(a, mode) if is_img else a
