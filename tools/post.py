"""The light layer: soft light over strict pixels, computed in code from the scene's own masks.

The pixel layer is always strict (palette slots, whole pixels, nearest-neighbour integer scale).
A light layer is optional, and a style uses exactly one of three regimes (measured on ten games,
study README section 1.3). Mixing two in one frame reads as a filter:

  regime            games (measured)                          here
  none              Metal Slug 3, Into the Breach, Freitas,    light is a palette step (light.py),
                    Owlboy (in-cell variance at noise level)   or don't call this module
  native light      Celeste, Hyper Light Drifter, Sea of        Post(img, scale, res='native'): every
                    Stars clouds, Katana ZERO (in-cell slope    field is evaluated once per art pixel
                    ratio 0.12, void cells std 0.00)            on the 1x array, upscaled last
  screen light      Sword & Sworcery (41% soft steps, rain     Post(img, scale, res='screen'): fields
                    off the 3 px grid), Stardew's lamp map      are smooth inside each art pixel
                    (halo inner/outer half-cell ratio 0.99)

Every light hangs off something drawn: a slot mask (glow), a lamp position (light, lightmap), a
depth plane (Stack). Every op is a pure function of its inputs, t, T and seed; anything animated
takes t and the loop length T and wraps t into [0, T), so frame T is frame 0 exactly.

    from post import Post, Stack
    p = Post(frame_1x, scale=4)                                   # res='native' (the default)
    p.glow(c.mask_of('lamp'), kernel='exp', length=3.5)           # HLD halo, emitters untouched
    p.lightmap(0.32, [(212, 64, 18, (1, .85, .45), 1.0)], t=t, T=96)   # Stardew: the void stays black
    p.light(120, 40, 58, '#c87868', core=15, falloff=1.1)         # S&S plateau halo (screen blend)
    p.band(240, 62, (0.05, 0.36, 0.04), mask=floor)               # HLD light spine
    p.rain(t, 96, style='cell')                                   # Celeste: 1x30 opaque columns
    big = p.image()                                               # PIL RGB at 1x * scale

    s = Stack(scale=3, res='screen')                              # S&S: light between planes
    s.plane(far_1x, depth=2).plane(stage_1x, stage_mask, depth=1).plane(near_1x, near_mask, depth=0)
    s.light(lambda p: p.light(316, 60, 58, '#c87868', core=15), depth=1)    # near planes stay dark
    big = s.render().rain(t, 96, style='hair').image()

What is here, by the reference it was measured on:
  light, lightmap, ambient    lamp pools: S&S plateau halos (core 15, radius 58, falloff 1.1);
                              Stardew's multiplied lamp map; Katana ZERO's wall wash (geo = wall)
  glow                        from a slot mask only: Celeste's two-scale bloom ('gauss'), HLD's
                              hue-shifted exp halo ('exp'), Katana's outer glow ('outer')
  shaft, flare, streak        S&S light pillar (floor, striations), anamorphic flare stack
  band, tint_field, fade      HLD light spine and stairwell fade, Celeste's OKLab gradient tint
  vignette(colour_right=)     HLD's edge falloff toward a hue that drifts across x
  fog, tile_noise             drifting fog on noise that wraps exactly
  rain(style=)                'hair' (S&S), 'cell' (Celeste), 'streak' (HLD)
  motes                       soft specks for the screen styles (crisp ones: fx.pixel_motes)
  Stack, paste                depth planes with light between them (S&S occlusion)
  over, Post.over             a translucent layer with an altitude fade and rim (Sea of Stars)
  Post.from_world, sprite     quarter-pixel camera and rotated screen-res sprites (Stardew)
  light_field                 a light's field at 1x, for texture code that follows the light

Coordinates, radii and sigmas are in 1x art pixels, so they match the scene code. Blend modes:
'screen' (soft, lifts black: fine for 01 and 02), 'add' (03 halos), 'multiply' (09 wall wash,
10 lamp map: black stays black), 'lerp'. Vignette, grain, scanlines and aberration exist, but none
of the ten references uses them; the style presets (tools/styles.py, guides/styles.md) say which
ops a style allows. Don't use this module to rescue weak pixel art.
"""
import hashlib, math, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph
import colorlib as cl

BLENDS = ('screen', 'add', 'multiply', 'lerp')

# ---------------------------------------------------------------- small helpers
def rgbf(c):
    """'#rrggbb', (r, g, b) in 0..255 ints, or floats in 0..1 -> float rgb array in 0..1"""
    if isinstance(c, str):
        v = int(c.lstrip('#'), 16)
        return np.array(((v >> 16) & 255, (v >> 8) & 255, v & 255), float) / 255.0
    a = np.asarray(c, float)
    return a if a.size and a.max() <= 1.0 + 1e-9 else a / 255.0      # (1, .85, .45) or (255, 216, 115)

def _as_rgb(img):
    """PIL image or array -> float (h, w, 3) in 0..1"""
    if isinstance(img, Image.Image):
        return np.asarray(img.convert('RGB'), float) / 255.0
    a = np.asarray(img)
    a = a[..., :3]
    return a.astype(float) / 255.0 if a.dtype.kind in 'ui' else a.astype(float).copy()

def _as_rgba(img):
    if isinstance(img, Image.Image):
        return np.asarray(img.convert('RGBA'), float) / 255.0
    a = np.asarray(img)
    a = a.astype(float) / 255.0 if a.dtype.kind in 'ui' else a.astype(float)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.ones(a.shape[:2] + (1,))], -1)
    return a

def _gauss1d(r):
    r = max(0.5, float(r))
    n = int(math.ceil(r * 3))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / r) ** 2)
    return k / k.sum()

def _conv_axis(a, k, axis):
    n = len(k) // 2
    pad = [(0, 0)] * a.ndim
    pad[axis] = (n, n)
    p = np.pad(a, pad, mode='edge')
    if len(k) <= 31:
        out = np.zeros_like(a)
        for i, w in enumerate(k):
            sl = [slice(None)] * a.ndim
            sl[axis] = slice(i, i + a.shape[axis])
            out += w * p[tuple(sl)]
        return out
    L = p.shape[axis] + len(k)                          # long kernels: FFT, same result
    shape = [1] * a.ndim
    shape[axis] = L // 2 + 1
    F = np.fft.rfft(p, L, axis=axis) * np.fft.rfft(k, L).reshape(shape)
    full = np.fft.irfft(F, L, axis=axis)
    sl = [slice(None)] * a.ndim
    sl[axis] = slice(2 * n, 2 * n + a.shape[axis])
    return full[tuple(sl)]

def blur(a, r):
    """separable gaussian blur (sigma r) of an (h, w[, c]) float array, edges clamped"""
    k = _gauss1d(r)
    a = np.asarray(a, float)
    return _conv_axis(_conv_axis(a, k, 0), k, 1)

def smooth_up(a, w, h):
    """resize a float (h0, w0[, c]) array to (h, w) with bicubic filtering (for soft light)"""
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32), 'F').resize((w, h), Image.BICUBIC))
    return np.stack([smooth_up(a[..., i], w, h) for i in range(a.shape[2])], -1)

def screen(a, b):
    return 1 - (1 - a) * (1 - np.clip(b, 0, 1))

def _hash(i, seed):
    h = (np.asarray(i, np.int64) * 374761393 + seed * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _hash2(x, y, s=0):
    """the integer hash of iso.hash2 / texture._hash_arr, on arrays"""
    h = (np.asarray(x, np.int64) * 374761393 + np.asarray(y, np.int64) * 668265263 + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _either(a, b):
    """the union of two optional 1x masks"""
    if a is None or b is None:
        return b if a is None else a
    return np.asarray(a, bool) | np.asarray(b, bool)

def _wrap_t(t, T):
    return t if (t is None or not T) else t % T

def _flicker(t, T, seed=0, hold=3, amount=0.06):
    """light.flicker, but periodic: held for `hold` frames and wrapped into the loop"""
    k = int(_wrap_t(t, T) // hold)
    return 1.0 + amount * (2.0 * float(_hash2(k, 7, seed + 101)) - 1.0)

_VIS1, _VISW = {}, {}                       # occlusion caches: 1x visibility, and lifted

def _cache_put(d, key, val, limit):
    if len(d) >= limit:
        d.pop(next(iter(d)))
    d[key] = val
    return val

def visibility(block, x, y, reach, cell=1, near=1.5):
    """a 1x visibility map of a point light: 1 where the straight line from the pixel centre to
    (x, y) crosses no blocker pixel, 0 in its shadow (Stardew's mine walls, Katana ZERO's door
    frames: lamp pools stop at the wall, the wall's own face still catches the light).
    block: a 1x bool mask (walls, crates, the near boulder). Only pixels within `reach` px
    (a box) are tested; the rest stay 1. Marches each ray in steps of at most 1 px; the target
    pixel itself and anything within `near` px of the source never block, so a light set on a
    lamp drawn into a wall still shines. cell > 1 tests every cell-th pixel (a coarse grid) and
    resizes the result bicubically (softer, faster). Cached per (mask, light, reach, cell)."""
    block = np.asarray(block, bool)
    H, W = block.shape
    key = (block.shape, block.tobytes() if block.size < 4096 else
           hashlib.sha1(np.packbits(block).tobytes()).digest(),
           round(float(x), 3), round(float(y), 3), round(float(reach), 3), int(cell), float(near))
    hit = _VIS1.get(key)
    if hit is not None:
        return hit
    vis = np.ones((H, W), np.float32)
    x0, x1 = max(0, int(math.floor(x - reach))), min(W, int(math.ceil(x + reach)))
    y0, y1 = max(0, int(math.floor(y - reach))), min(H, int(math.ceil(y + reach)))
    if x1 > x0 and y1 > y0 and block.any():
        cell = max(1, int(cell))
        cols, rows = np.arange(x0, x1, cell), np.arange(y0, y1, cell)
        ti, tj = np.meshgrid(rows, cols, indexing='ij')
        tx, ty = tj + 0.5, ti + 0.5
        dx, dy = x - tx, y - ty
        d = np.hypot(dx, dy)
        n = int(math.ceil(d.max())) + 1
        shadow = np.zeros(tx.shape, bool)
        for k in range(1, n):
            f = k / n
            px, py = tx + f * dx, ty + f * dy
            ix, iy = np.floor(px).astype(np.int64), np.floor(py).astype(np.int64)
            ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H) & ~((ix == tj) & (iy == ti))
            ok &= (1 - f) * d >= near                     # distance from this sample to the light
            shadow |= ok & block[np.clip(iy, 0, H - 1), np.clip(ix, 0, W - 1)]
        v = (~shadow).astype(np.float32)
        if cell > 1:
            v = np.clip(smooth_up(v, len(cols) * cell, len(rows) * cell), 0, 1)
        vis[y0:y1, x0:x1] = v[:y1 - y0, :x1 - x0]
    return _cache_put(_VIS1, key, vis, 64)

def _smoothstep(e0, e1, x):
    if e1 == e0:
        return (x >= e0).astype(float)
    u = np.clip((x - e0) / (e1 - e0), 0, 1)
    return u * u * (3 - 2 * u)

def _cubic_wrap(g, n, axis, off=0.0):
    """sample the periodic lattice g along `axis` at n points spanning one period, with
    Catmull-Rom interpolation (indices taken mod the lattice size, so it wraps exactly)"""
    m = g.shape[axis]
    u = ((np.arange(n) - off) % n) * (m / n)
    i0 = np.floor(u).astype(int)
    f = u - i0
    f2, f3 = f * f, f * f * f
    ws = ((-f3 + 2 * f2 - f) / 2, (3 * f3 - 5 * f2 + 2) / 2, (-3 * f3 + 4 * f2 + f) / 2, (f3 - f2) / 2)
    out = 0
    for j, w in zip((-1, 0, 1, 2), ws):
        v = np.take(g, (i0 + j) % m, axis=axis)
        shape = [1] * g.ndim
        shape[axis] = n
        out = out + v * w.reshape(shape)
    return out

def tile_noise(w, h, cell, seed=0, octaves=2, ox=0.0, oy=0.0):
    """smooth value noise in 0..1 that wraps exactly on both axes: column w continues column 0,
    row h continues row 0. ox, oy shift it by any (sub-pixel) amount, so a fog that drifts a whole
    number of widths per loop meets itself (Post.fog)."""
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    gw, gh = max(1, int(round(w / cell))), max(1, int(round(h / cell)))
    for o in range(octaves):
        g = _hash(np.arange(gw * gh), seed + 17 * o).reshape(gh, gw)
        rows = _cubic_wrap(g, w, 1, ox)                 # (gh, w)
        out += amp * _cubic_wrap(rows, h, 0, oy)
        tot += amp
        amp *= 0.5
        gw, gh = min(w, gw * 2), min(h, gh * 2)
    return np.clip(out / tot, 0, 1)

def _profile(dx, dy, radius, core=0.0, falloff=1.1, profile='linear', squash=1.0):
    """the shape of one light: 'linear' is a plateau of radius `core` then (1 - r)^falloff out to
    `radius` (S&S lamp: core 15, radius 58, falloff 1.1); 'gauss' is exp(-d^2 / 2 sigma^2) with
    sigma = radius across and radius * squash down (Stardew lamp: 18; Katana wall wash: 35, 80)"""
    if profile == 'gauss':
        sx, sy = float(radius), float(radius) * squash
        return np.exp(-0.5 * (dx / sx) ** 2) * np.exp(-0.5 * (dy / sy) ** 2)
    if profile != 'linear':
        raise ValueError("profile is 'linear' or 'gauss', got %r" % (profile,))
    r = np.hypot(dx, dy / squash)
    span = max(1e-6, radius - core)
    return np.clip(1 - (r - core) / span, 0, 1) ** falloff

def light_field(w, h, x, y, radius, core=0.0, falloff=1.1, profile='linear', squash=1.0):
    """the same field Post.light uses, evaluated once per 1x pixel centre (for texture code that
    must follow the light, such as leaf flecks whose density and colour track the nearest lamp)"""
    xs = np.arange(w) + 0.5 - x
    ys = np.arange(h)[:, None] + 0.5 - y
    return _profile(xs[None, :], ys, radius, core, falloff, profile, squash) * np.ones((h, w))

def _oklch_shift(rgb, dL=0.0, hue=0.0, chroma=1.0, cmax=None):
    """rotate hue (degrees), scale chroma and lift L of an (..., 3) 0..1 array in OKLCh"""
    lab = cl.rgb_to_oklab(np.clip(rgb, 0, 1) * 255)
    L, C, h = cl.lch_of(lab)
    C = C * chroma
    if cmax is not None:
        C = np.minimum(C, cmax)
    h = np.radians(h + hue)
    out = np.stack([L + dL, C * np.cos(h), C * np.sin(h)], -1)
    return cl.oklab_to_rgb(out) / 255.0

_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
_M2i, _M1i = np.linalg.inv(_M2).astype(np.float32), np.linalg.inv(_M1).astype(np.float32)

def _oklab32(rgb):
    """0..1 sRGB -> OKLab in float32 (colorlib's maths, fast enough for a 1080p frame)"""
    c = np.clip(rgb, 0, 1).astype(np.float32)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.cbrt(lin @ _M1.T) @ _M2.T

def _srgb32(lab):
    lin = np.clip((lab @ _M2i.T) ** 3 @ _M1i.T, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055).astype(np.float32)

# ---------------------------------------------------------------- translucent layer (A4)
def _lin(c):
    c = np.clip(c, 0, 1).astype(np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def _gam(c):
    c = np.clip(c, 0, 1).astype(np.float32)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def _place(H, W, arr, ox, oy, fill=0.0):
    """arr (h, w[, c]) placed at integer (ox, oy) on an H x W frame; the rest is fill"""
    out = np.full((H, W) + arr.shape[2:], fill, float)
    h, w = arr.shape[:2]
    x0, y0 = max(0, ox), max(0, oy)
    x1, y1 = min(W, ox + w), min(H, oy + h)
    if x1 > x0 and y1 > y0:
        out[y0:y1, x0:x1] = arr[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    return out

def _over_alpha(H, W, layer, alpha, ox, oy, height, z, fade):
    """the layer and its effective alpha on the full 1x frame"""
    lay = _as_rgb(layer)
    h, w = lay.shape[:2]
    al = np.broadcast_to(np.asarray(alpha, float), (h, w))
    ox, oy = int(math.floor(ox)), int(math.floor(oy))
    L = _place(H, W, lay, ox, oy)
    A0 = _place(H, W, al, ox, oy)
    A = A0
    if height is not None:
        Z = np.asarray(height, float)
        A = A0 * np.clip((z - Z) / max(1e-6, fade), 0, 1)
    return L, A, A0

def _rim_mask(A, rim, thr=0.3):
    """layer edge pixels whose outward normal faces `rim` (default lower right)"""
    if rim is False or rim is None:
        return np.zeros(A.shape, bool)
    d = np.array((1.0, 1.0) if rim is True else rim, float)
    d /= max(1e-6, np.hypot(*d))
    m = A > thr
    if not m.any():
        return m
    nx, ny = morph.normals(m)
    return morph.edges(m) & (nx * d[0] + ny * d[1] > 0.35)          # 04: nx + ny > 0.5

def _rim_colour(base):
    """oklch(L + 0.18, min(2 C, 0.12), h) of the colour underneath (04's cloud rim on deep water)"""
    lab = cl.rgb_to_oklab(np.clip(base, 0, 1) * 255)
    L, C, h = cl.lch_of(lab)
    C = np.minimum(2 * C, 0.12)
    hr = np.radians(h)
    return cl.oklab_to_rgb(np.stack([L + 0.18, C * np.cos(hr), C * np.sin(hr)], -1)) / 255.0

def over(base, layer, alpha=0.88, ox=0, oy=0, height=None, z=0.0, fade=8.0, rim=True, space='linear'):
    """a translucent layer (cloud, mist, water glaze) over a 1x frame, Sea of Stars style.
    alpha: a number or an (h, w) array the size of the layer (0 where there is no layer).
    height: an (H, W) height map of the base (Iso.world[..., 2]); where the terrain rises within
    `fade` units of the layer's altitude z the layer thins out, so tall stacks pierce the cloud
    over several rows: a = alpha * clip((z - Z) / fade, 0, 1). rim: the layer's lower-right edge
    (or the edge facing a given (dx, dy)) becomes the base colour lifted by L 0.18 with doubled
    chroma. Blends in linear RGB. Returns the same kind as base (PIL in, PIL out)."""
    pil = isinstance(base, Image.Image)
    B = _as_rgb(base)
    H, W = B.shape[:2]
    L, A, A0 = _over_alpha(H, W, layer, alpha, ox, oy, height, z, fade)
    out = _blend_over(B, L, A, _rim_mask(A0, rim) & (A > 0.3), space)   # rim on the outline only
    if pil:
        return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')
    return out

def _blend_over(B, L, A, rim, space):
    a = A[..., None]
    if space == 'linear':
        out = _gam(_lin(B) * (1 - a) + _lin(L) * a)
    else:
        out = B * (1 - a) + L * a
    if rim.any():
        out[rim] = _rim_colour(B[rim])
    return out

# ---------------------------------------------------------------- rain presets (F3)
RAIN = {
    # Sword & Sworcery: ~18 vertical anti-aliased hairlines, 8-10 art px, 3 screen px wide
    'hair': dict(n=18, angle=90, length=(8, 10), colour='#c8ccd2', alpha=(0.15, 0.45), cycles=(3, 5), layers=3),
    # Celeste: 30 opaque white columns, 1 x 30 art px, whole cells, over everything
    'cell': dict(n=30, angle=90, length=(30, 30), colour='#ffffff', alpha=(1.0, 1.0), cycles=(8, 8), layers=1),
    # Hyper Light Drifter: 2-3 falling 1 px light streaks, stepped alpha tails, slant 0.09
    'streak': dict(n=3, angle=95.14, length=(24, 24), colour='#26f4ea', alpha=(1.0, 1.0), cycles=(2, 3), layers=2),
}

# ---------------------------------------------------------------- Post
class Post:
    def __init__(self, img, scale=4, res='native', screen=None):
        """img: the finished pixel frame at 1x (PIL or array). scale: the integer delivery scale.
        res='native' (default): every effect is computed once per art pixel on the 1x array and
        the result is scaled up with nearest neighbour in image() (Celeste, HLD, Sea of Stars,
        Katana ZERO). res='screen': effects are computed on the scaled-up frame and stay smooth
        inside each art pixel (Sword & Sworcery, Stardew's lamp map). screen=True/False is the
        older spelling of the same switch."""
        if screen is not None:
            res = 'screen' if screen else 'native'
        if res not in ('native', 'screen'):
            raise ValueError("res is 'native' or 'screen', got %r" % (res,))
        self.res = res
        self.out = int(scale)
        self.s = self.out if res == 'screen' else 1
        self.src = _as_rgb(img)                                         # 1x
        self.h0, self.w0 = self.src.shape[:2]
        self.W, self.H = self.w0 * self.s, self.h0 * self.s
        self.a = self._rep(self.src)
        self._grid = None
        self._view = None                   # (ix, iy, ox, oy, world shape) for from_world
        self._late = []                     # screen-pixel ops run after the native upscale

    # ------------------------------------------------------------ resolution plumbing
    def _rep(self, a):
        s = self.s
        a = a.astype(np.float32)
        return a if s == 1 else np.repeat(np.repeat(a, s, 0), s, 1)

    def _crop1x(self, m):
        """a 1x array aligned with self.src (for from_world posts: cut out of the world)"""
        m = np.asarray(m)
        if self._view is None:
            if m.shape[:2] != self.src.shape[:2]:
                raise ValueError('1x array is %s, the frame is %s' % (m.shape[:2], self.src.shape[:2]))
            return m
        ix, iy, _, _, wshape = self._view
        hh, ww = self.src.shape[:2]
        if m.shape[:2] == wshape:
            yi = np.clip(np.arange(iy, iy + hh), 0, wshape[0] - 1)
            xi = np.clip(np.arange(ix, ix + ww), 0, wshape[1] - 1)
            return m[yi][:, xi]
        if m.shape[:2] == (hh, ww):
            return m
        if m.shape[:2] == (self.h0, self.w0):
            return np.pad(m, ((0, 1), (0, 1)) + ((0, 0),) * (m.ndim - 2), mode='edge')
        raise ValueError('1x array is %s; expected the view %s or the world %s'
                         % (m.shape[:2], (self.h0, self.w0), wshape))

    def _lift(self, m, smooth=False):
        """a 1x array aligned with self.src -> working resolution"""
        m = np.asarray(m)
        if self.s == 1 and self._view is None:
            return m
        s = self.s
        if smooth:
            hh, ww = m.shape[:2]
            u = smooth_up(m.astype(float), ww * s, hh * s)
        else:
            u = np.repeat(np.repeat(m, s, 0), s, 1)
        if self._view is not None:
            _, _, ox, oy, _ = self._view
            u = u[oy:oy + self.H, ox:ox + self.W]
        return u

    def up(self, m, smooth=False):
        """a 1x mask or field (frame-sized, or world-sized for from_world) at working resolution:
        nearest neighbour, or bicubic with smooth=True"""
        return self._lift(self._crop1x(m), smooth)

    def grid(self):
        """working-resolution pixel centres in 1x units: (yy, xx)"""
        if self._grid is None:
            yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
            self._grid = ((yy + 0.5) / self.s, (xx + 0.5) / self.s)
        return self._grid

    def _box(self, x0, y0, x1, y1):
        """working-res slices covering the 1x box, and the 1x centres of its pixels"""
        s = self.s
        i0, i1 = max(0, int(math.floor(x0 * s))), min(self.W, int(math.ceil(x1 * s)))
        j0, j1 = max(0, int(math.floor(y0 * s))), min(self.H, int(math.ceil(y1 * s)))
        if i1 <= i0 or j1 <= j0:
            return None
        xs = (np.arange(i0, i1) + 0.5) / s
        ys = (np.arange(j0, j1) + 0.5) / s
        return (slice(j0, j1), slice(i0, i1)), ys[:, None], xs[None, :]

    def _weights(self, k, sl, behind=None, mask=None):
        """k * (1 - behind) * mask on the slice sl (masks are 1x, nearest-upscaled)"""
        if behind is not None:
            k = k * (1 - self.up(np.asarray(behind, float))[sl])
        if mask is not None:
            k = k * self.up(np.asarray(mask, float))[sl]
        return k

    def _mix(self, k, colour, blend, sl=(slice(None), slice(None))):
        """blend colour (rgb, or an rgb field) into the slice with weight k"""
        a = self.a[sl]                                   # a view: updated in place
        c = rgbf(colour) if not isinstance(colour, np.ndarray) or colour.ndim == 1 else colour
        c = np.asarray(c, np.float32)
        k = np.asarray(k, np.float32)
        if blend == 'lerp':
            a += (c - a) * np.clip(k, 0, 1)[..., None]
            return
        kc = k[..., None] * c
        if blend == 'screen':                            # 1 - (1 - a)(1 - kc)
            np.clip(kc, 0, 1, out=kc)
            a += kc * (1 - a)
        elif blend == 'add':
            a += kc
        elif blend == 'multiply':
            kc += 1
            a *= kc
        else:
            raise ValueError('blend is one of %s, got %r' % (BLENDS, blend))

    def _field3(self, v):
        """a number, colour, callable(xx, yy) or 1x array -> working-res (H, W, 3) field"""
        if callable(v):
            yy, xx = self.grid()
            f = np.asarray(v(xx, yy), np.float32) * np.ones((self.H, self.W), np.float32)
        elif isinstance(v, np.ndarray) and v.ndim >= 2:
            f = self.up(v.astype(np.float32), smooth=True).astype(np.float32)
        elif np.isscalar(v) and not isinstance(v, str):
            return np.full((self.H, self.W, 3), float(v), np.float32)
        else:
            return np.broadcast_to(rgbf(v).astype(np.float32), (self.H, self.W, 3)).copy()
        return np.repeat(f[..., None], 3, -1) if f.ndim == 2 else f

    # ------------------------------------------------------------ point and area lights (A2)
    def light(self, x, y, radius, colour, strength=0.5, squash=1.0, falloff=1.1, core=0.0,
              profile='linear', blend='screen', behind=None, mask=None):
        """a pool of coloured light on a drawn emitter (a lamp bank, a window, a sign).
        profile 'linear': flat out to `core`, then (1 - r)^falloff to `radius` (01: core 15,
        radius 58, falloff 1.1, a halo twice the size of its emitter). profile 'gauss': sigma =
        radius (x) and radius * squash (y). blend 'screen' lifts black (fine on a lit sky);
        use 'multiply' or lightmap() where the void must stay black. behind: a 1x mask of pixels
        in front of the light (it skips them); mask: a 1x weight for where it lands (walls 1,
        floor 0.15)."""
        R = 4.0 * radius if profile == 'gauss' else float(radius)
        box = self._box(x - R, y - R * squash, x + R, y + R * squash)
        if box is None:
            return self
        sl, ys, xs = box
        k = strength * _profile(xs - x, ys - y, radius, core, falloff, profile, squash) * np.ones((ys.size, xs.size))
        self._mix(self._weights(k, sl, behind, mask), colour, blend, sl)
        return self

    def lightmap(self, ambient=0.3, lights=(), cap=1.3, geo=None, levels=None, t=None, T=None,
                 flicker=0.06, hold=3, keep=None, behind=None, occlude=None, occlude_cell=1):
        """multiplicative light: L = ambient + sum(gain * colour * gauss), clipped to cap, and
        out = frame * L, so black stays black and overlapping pools add (Stardew's mine: ambient
        (0.30, 0.33, 0.36), lamps sigma 18, colour (1, .85, .45), gain ~1, 4x the ambient at the
        peak; Katana ZERO's wall wash: ambient 1, gain 0.25-0.35, sigma (35, 80), geo = wall).
        lights: [(x, y, sigma | (sx, sy), colour, gain), ...] in 1x px. ambient: number, colour,
        1x array or callable(xx, yy). geo: a 1x weight on the lamps only (wall 1, floor 0.15,
        void 0). levels: quantise L to 1/levels steps (bounds the colour count). With t and T the
        gains flicker by +-flicker, held `hold` frames (T % hold == 0 keeps the seam a hold).
        keep (or behind, the Stack spelling): a 1x mask left untouched (lamp cores, UI).
        Per-light flicker: a light may carry a 6th and 7th item, (..., gain, flicker, hold), or
        (..., gain, (flicker, hold)); None or a missing item falls back to the call's flicker /
        hold (a sputtering wick: (432, 72, 16, (1, .8, .42), 0.7, 0.25, 2); steady: 0).
        occlude: a 1x blocker mask (walls, crates); a light does not pass through it (see
        visibility(); hard 1x shadow edges at res='native', softened inside the art pixel at
        res='screen'). occlude_cell: test every n-th pixel (coarse, soft). Cached per light."""
        keep = _either(keep, behind)
        L = self._field3(ambient)
        g = None if geo is None else self.up(np.asarray(geo, float))         # crisp: art edges
        blk = None if occlude is None else self._crop1x(np.asarray(occlude, bool))
        for i, lt in enumerate(lights):
            x, y, sig, colour, gain = lt[:5]
            sx, sy = (sig, sig) if np.isscalar(sig) else sig
            amt, hd = flicker, hold
            if len(lt) > 5 and lt[5] is not None:
                if np.isscalar(lt[5]):
                    amt = lt[5]
                else:
                    amt, hd = lt[5]
            if len(lt) > 6 and lt[6] is not None:
                hd = lt[6]
            vis = None
            if blk is not None:                           # unflickered reach: cached across t
                vis = self._occlusion(blk, x, y, 4.0 * max(sx, sy) * (1 + 0.3 * abs(amt or 0)) + 1,
                                      occlude_cell)
            if t is not None and amt:
                f = _flicker(t, T, seed=i, hold=hd, amount=amt)
                gain, sx, sy = gain * f, sx * (1 + 0.3 * (f - 1)), sy * (1 + 0.3 * (f - 1))
            box = self._box(x - 4 * sx, y - 4 * sy, x + 4 * sx, y + 4 * sy)
            if box is None:
                continue
            sl, ys, xs = box
            k = gain * np.exp(-0.5 * ((xs - x) / sx) ** 2) * np.exp(-0.5 * ((ys - y) / sy) ** 2)
            if g is not None:
                k = k * g[sl]
            if vis is not None:
                k = k * vis[sl]
            L[sl] += (k[..., None] * rgbf(colour)).astype(np.float32)
        np.clip(L, 0, cap if cap is not None else np.inf, out=L)
        if levels:
            L = np.round(L * levels) / levels
        out = self.a * L
        if keep is not None:
            km = self.up(np.asarray(keep, bool))
            out[km] = self.a[km]
        self.a = out.astype(np.float32, copy=False)
        return self

    def _occlusion(self, blk, x, y, reach, cell):
        """visibility() of one light at working resolution (nearest at native, bicubic at
        screen), cached with the view so a 96-frame loop computes each light once"""
        vis = visibility(blk, x, y, reach, cell)
        key = (id(vis), self.s, self.res, self._view and tuple(self._view[:4]), self.H, self.W)
        hit = _VISW.get(key)
        if hit is not None and hit[0] is vis:
            return hit[1]
        up = self._lift(vis, smooth=self.res == 'screen')
        up = np.clip(up, 0, 1).astype(np.float32) if self.s > 1 else up
        _cache_put(_VISW, key, (vis, up), 16)
        return up

    def ambient(self, amb, keep=None, behind=None):
        """multiply the frame by an ambient map: a number, colour, 1x array or callable(xx, yy)
        (HLD: amb(x) = 0.72 + 0.28 * exp(-0.5 ((x - cx) / 150)^2), bright on the spine).
        keep / behind: a 1x mask left untouched."""
        keep = _either(keep, behind)
        f = self._field3(amb)
        if keep is not None:
            f[self.up(np.asarray(keep, bool))] = 1.0
        self.a *= f
        return self

    def darkness(self, amount=0.7, lights=(), colour='#000000'):
        """(older draft) darken toward colour except near lights [(x, y, radius), ...]. Pools
        don't add and can't tint; lightmap() is the multiplicative model that replaces this."""
        yy, xx = self.grid()
        lit = np.zeros((self.H, self.W))
        for lx, ly, r in lights:
            lit = np.maximum(lit, np.clip(1 - np.hypot(xx - lx, yy - ly) / r, 0, 1) ** 1.5)
        k = (amount * (1 - lit))[..., None]
        self.a = (self.a * (1 - k) + rgbf(colour) * k).astype(np.float32)
        return self

    # ------------------------------------------------------------ glow from slot masks (A5)
    def glow(self, mask=None, kernel='gauss', radius=(3, 14), weights=(0.6, 0.4), strength=None,
             tint=None, length=3.5, reach=None, hue_shift=-15.0, chroma=0.8, falloff=0.62,
             outside_only=None, blend=None, threshold=None, behind=None):
        """light bleeding from an emitter mask (canvas.mask_of('lamp', 'cloud')), never from a
        brightness threshold (02's high-key frame is 46% above L 0.8). Kernels:
          'gauss': sum of blurs of the emitters' colour (or tint), weights x radius in 1x px,
                   screen-blended (02: radius (3, 14), weights (0.6, 0.4), strength 0.22, pink)
          'exp':   strength * exp(-d / length) out to `reach` (12), d = chamfer distance from the
                   mask, additive, in the emitters' own colour turned hue_shift degrees with
                   chroma x0.8; the emitters keep their palette colours (03: length 3.5; strength
                   0.4 reproduces the measured red deltas +75 +58 +47 .. +4 at d = 1..10)
          'outer': strength * falloff^(d - 1) for d <= reach (4) outside the mask, additive, in
                   tint (09: the one teal door, falloff 0.62)
        threshold: opt in to the old luminance mask. behind: a 1x mask the glow doesn't touch."""
        src = self.src
        if mask is None:
            if threshold is None:
                raise ValueError('glow needs an emitter mask (or an explicit threshold)')
            mask = (src @ np.array([0.299, 0.587, 0.114])) > threshold
        m = self._crop1x(np.asarray(mask, bool))
        mf = m.astype(float)[..., None]
        if kernel == 'gauss':
            strength = 0.22 if strength is None else strength
            light = mf * (rgbf(tint) if tint is not None else src)
            rs = (radius,) if np.isscalar(radius) else tuple(radius)
            ws = (1.0,) if len(rs) == 1 else tuple(weights)
            b = sum(w * blur(light, r) for w, r in zip(ws, rs))
            if outside_only:
                b = b * (1 - mf)
            k, col = strength * np.ones(m.shape), b
            blend = blend or 'screen'
        elif kernel in ('exp', 'outer'):
            outer = kernel == 'outer'
            reach = (4 if outer else 12) if reach is None else reach
            strength = (1.0 if outer else 0.4) if strength is None else strength
            d = morph.distance_outside(m, 'chessboard' if outer else 'chamfer34', max=reach + 1)
            ring = (d > 0) & (d <= reach)
            k = np.where(ring, falloff ** (d - 1) if outer else np.exp(-d / length), 0.0) * strength
            if not (outside_only is False):
                k = k * ~m
            if tint is not None:
                col = rgbf(tint)
            else:                                   # each pixel takes its nearest emitters' colour
                r = max(1.5, reach / 3.0)
                num, den = blur(mf * src, r), blur(mf[..., 0], r)
                col = np.where(den[..., None] > 1e-6, num / np.maximum(den, 1e-6)[..., None], 0)
                if not outer and (hue_shift or chroma != 1.0):
                    col = _oklch_shift(col, 0.0, hue_shift, chroma)
            blend = blend or 'add'
        else:
            raise ValueError("kernel is 'gauss', 'exp' or 'outer', got %r" % (kernel,))
        field = k[..., None] * (col if np.ndim(col) == 3 else np.broadcast_to(col, m.shape + (3,)))
        field = self._lift(field, smooth=True) if self.s > 1 else field
        kk = np.ones(field.shape[:2])
        kk = self._weights(kk, (slice(None), slice(None)), behind)
        self._mix(kk, field, blend)
        return self

    # ------------------------------------------------------------ shafts and flares (A6, A7)
    def shaft(self, x, y, angle=90, length=100, width=(6, 30), colour='#ffe0c0', strength=0.35,
              floor=0.38, flat=0.6, soft=1.0, striate=0.03, freqs=(1.7, 2.9, 4.3), cycles=(1, 2, 3),
              t=None, T=None, shimmer=0.0, head=6, tail=None, seed=0, behind=None, mask=None,
              blend='screen', profile='plateau'):
        """a light pillar from (x, y) toward `angle` degrees (90 = straight down), brightest at
        its source: intensity 1 - (1 - floor) * progress, so `floor` is what is left at `length`
        (01: 38% at the performer), then it fades out over `tail`. width: (w0, w1) from start
        to end, or a table [(along, w), ...] (01: [(0, 33), (60, 23), (115, 26)]), w being the
        full width at half strength. Across: flat for u < flat (u = |across| / half-width),
        cosine shoulders over `soft` (profile='smooth': the older smoothstep edge, soft = its
        share of the half-width). striate adds faint lengthwise striations (01: 2-3%) that drift
        with integer cycles per loop; shimmer breathes the whole shaft once per loop."""
        a = math.radians(angle)
        ux, uy = math.cos(a), math.sin(a)
        if np.ndim(width) == 1 and len(width) == 2 and np.isscalar(width[0]):
            table = np.array([(0.0, width[0]), (float(length), width[1])])
        else:
            table = np.array(sorted(width), float)
        tail = max(4.0, 0.2 * length) if tail is None else tail
        reach = length + tail
        half = table[:, 1].max() / 2 * (flat + soft)
        cx = [x - ux * head - uy * half, x - ux * head + uy * half,
              x + ux * reach - uy * half, x + ux * reach + uy * half]
        cy = [y - uy * head + ux * half, y - uy * head - ux * half,
              y + uy * reach + ux * half, y + uy * reach - ux * half]
        box = self._box(min(cx), min(cy), max(cx), max(cy))
        if box is None:
            return self
        sl, ys, xs = box
        along = (xs - x) * ux + (ys - y) * uy
        across = -(xs - x) * uy + (ys - y) * ux
        w = np.interp(along, table[:, 0], table[:, 1])
        u = np.abs(across) / np.maximum(w / 2, 1e-6)
        if profile == 'smooth':
            e = np.clip((1 - u) / max(soft, 1e-6), 0, 1)
            prof = e * e * (3 - 2 * e)
        else:
            prof = np.where(u < flat, 1.0, 0.5 * (1 + np.cos(math.pi * np.clip((u - flat) / soft, 0, 1))))
        I = 1 - (1 - floor) * np.clip(along / max(length, 1e-6), 0, 1)
        I = I * (_smoothstep(0, head, along) if head else (along >= 0))
        I = I * np.clip(1 - (along - length) / tail, 0, 1)
        k = strength * prof * I
        t = _wrap_t(t, T)
        if striate:
            st = 1.0
            for j, f in enumerate(freqs):
                m = cycles[j % len(cycles)] if t is not None else 0
                ph = 2 * math.pi * (_hash(j, seed + 41) + (m * t / T if t is not None else 0))
                st = st + striate * np.sin(2 * math.pi * f * across / np.maximum(w, 1e-6) + ph)
            k = k * st
        if shimmer and t is not None:
            k = k * (1 + shimmer * math.sin(2 * math.pi * t / (T or 60)))
        self._mix(self._weights(k, sl, behind, mask), colour, blend, sl)
        return self

    def flare(self, xs, ys, colour='#5f8fd0', A=0.45, n=5, spread=14, length=(120, 220), sigma=0.7,
              band_sigma=5, band_len=180, band_A=0.25, taper=1.2, strength=1.0, seed=0,
              behind=None, mask=None, blend='screen'):
        """an anamorphic flare stack on a lamp at (xs, ys): n thin horizontal lines of hashed
        offset (+-spread), length and amplitude, plus a broad haze band (01: 3-6 lines with 4-6
        screen px FWHM, a 17 px band). Lines may cross the whole frame; pass behind= the near
        planes (or use a Stack) so they pass over far stones and behind near ones. strength
        scales everything (follow the lamp's flicker)."""
        ext = max(max(length), band_len)
        dy = spread + 4 * max(sigma, band_sigma)
        box = self._box(xs - ext, ys - dy, xs + ext, ys + dy)
        if box is None:
            return self
        sl, yy, xx = box
        ax = np.abs(xx - xs)
        k = band_A * np.exp(-0.5 * ((yy - ys) / band_sigma) ** 2) * np.clip(1 - ax / band_len, 0, None) ** 1.5
        for j in range(n):
            yj = ys + spread * (2 * _hash(j, seed + 1) - 1) if n > 1 else ys
            Lj = length[0] + (length[1] - length[0]) * _hash(j, seed + 2)
            Aj = A * (0.35 + 0.65 * _hash(j, seed + 3))
            k = k + Aj * np.exp(-0.5 * ((yy - yj) / sigma) ** 2) * np.clip(1 - ax / Lj, 0, None) ** taper
        self._mix(self._weights(strength * k, sl, behind, mask), colour, blend, sl)
        return self

    def streak(self, x, y, length, colour='#7aa0ff', strength=0.5, thickness=1.2, behind=None):
        """a single anamorphic lens streak through a bright point (flare() makes the stack)"""
        box = self._box(x - length, y - 4 * thickness, x + length, y + 4 * thickness)
        if box is None:
            return self
        sl, yy, xx = box
        k = np.exp(-0.5 * ((yy - y) / thickness) ** 2) * np.clip(1 - np.abs(xx - x) / length, 0, None) ** 1.5
        self._mix(self._weights(strength * k, sl, behind), colour, 'screen', sl)
        return self

    # ------------------------------------------------------------ field lights (A8)
    def band(self, cx, sigma, colour, strength=1.0, axis='x', mask=None, y_fade=None, blend='add',
             behind=None):
        """a gaussian light band, not a radial pool (HLD's floor spine: centre column 240, sigma
        62, (0.05, 0.36, 0.04) added, almost constant down its length). axis='x': the band is a
        column centred on x = cx; axis='y': a row centred on y = cx. y_fade=(a, b) ramps it in
        along the band from a (0) to b (1) with a smoothstep. mask: a 1x weight (the floor)."""
        yy, xx = self.grid()
        along, acr = (yy, xx) if axis == 'x' else (xx, yy)
        k = strength * np.exp(-0.5 * ((acr - cx) / sigma) ** 2)
        if y_fade is not None:
            a0, a1 = y_fade
            k = k * (_smoothstep(a0, a1, along) if a1 >= a0 else 1 - _smoothstep(a1, a0, along))
        sl = (slice(None), slice(None))
        self._mix(self._weights(k, sl, behind, mask), colour, blend)
        return self

    def tint_field(self, field, hue=335.0, amount=1.0, chroma=0.4, mask=None, space='oklab', behind=None):
        """a low-frequency colour drift inside flat tones, in OKLab: L += f and (a, b) +=
        chroma * f * (cos hue, sin hue) (02: f = 0.06 down the frame + 0.05 exp(-d / 40) near
        the bright masses, hue 335). field: a 1x array, a callable(xx, yy) or a number."""
        if space != 'oklab':
            raise ValueError("tint_field works in space='oklab'")
        f = self._field3(field)[..., 0] * np.float32(amount)
        if mask is not None:
            f = f * self.up(np.asarray(mask, np.float32))
        if behind is not None:
            f = f * (1 - self.up(np.asarray(behind, np.float32)))
        h = math.radians(hue)
        lab = _oklab32(self.a)
        lab += f[..., None] * np.array([1.0, chroma * math.cos(h), chroma * math.sin(h)], np.float32)
        self.a = _srgb32(lab)
        return self

    def fade(self, mask=None, y0=0, y1=None, colour='#000000', amount=(1.0, 0.0), gamma=1.3,
             axis='y', levels=None, behind=None):
        """mix toward colour by a0 + (a1 - a0) * p^gamma, p = 0 at y0 .. 1 at y1 (HLD's stairwell
        into the void: amount (0.88, 0) over the treads, gamma 1.3). axis='x' fades across x.
        levels: step the amount (a stepped fade). mask: a 1x weight (only the stairs)."""
        yy, xx = self.grid()
        v = yy if axis == 'y' else xx
        y1 = (self.h0 if axis == 'y' else self.w0) if y1 is None else y1
        p = np.clip((v - y0) / (y1 - y0), 0, 1) ** gamma if y1 != y0 else (v >= y0).astype(np.float32)
        k = amount[0] + (amount[1] - amount[0]) * p
        if levels:
            k = np.floor(k * levels + 1e-9) / levels
        sl = (slice(None), slice(None))
        self._mix(self._weights(k, sl, behind, mask), colour, 'lerp')
        return self

    # ------------------------------------------------------------ air
    def fog(self, colour, y0, y1, amount=(0.0, 0.5), t=None, T=None, drift=1, cell=24, breakup=0.5,
            seed=3, behind=None):
        """height fog: blends toward colour from amount[0] at y0 to amount[1] at y1, broken up by
        soft noise (breakup 0..1). With t and T it drifts sideways `drift` frame widths per loop
        (a whole number, so the loop is exact; the noise wraps, so there is no seam)."""
        yy, xx = self.grid()
        k = np.clip((yy - y0) / (y1 - y0), 0, 1) if y1 != y0 else (yy >= y0).astype(np.float32)
        f = amount[0] + (amount[1] - amount[0]) * k
        if breakup:
            t = _wrap_t(t, T)
            off = (drift * self.W * t / (T or 1)) % self.W if t is not None else 0.0
            n = tile_noise(self.W, self.H, cell * self.s, seed, ox=off)
            f = f * (1 - breakup + 2 * breakup * n)
        f = self._weights(np.clip(f, 0, 1), (slice(None), slice(None)), behind)
        self._mix(f, colour, 'lerp')
        return self

    def motes(self, t, T, n=40, colour='#ffd890', region=None, size=0.9, strength=0.8, seed=5, rise=1,
              sway=3.0, behind=None):
        """soft floating specks (dust in a lamp pool, spores, fireflies): the screen-res look of
        Sword & Sworcery and Stardew. For HLD's crisp 1 px motes use fx.pixel_motes. Each speck
        sways, twinkles and rises `rise` whole region heights per loop (0 = hover in place), and
        fades in and out at the region's top and bottom, so nothing pops at the wrap."""
        t = t % T
        x0, y0, x1, y1 = region or (0, 0, self.w0, self.h0)
        rise = max(1, int(round(rise))) if rise > 0 else 0
        acc = np.zeros((self.H, self.W))
        i = np.arange(n)
        px = x0 + _hash(i, seed) * (x1 - x0)
        py = y0 + _hash(i, seed + 1) * (y1 - y0)
        ph = _hash(i, seed + 2) * 2 * math.pi
        cyc = 1 + (_hash(i, seed + 3) * 2).astype(int)
        span = y1 - y0
        for j in range(n):
            a = 2 * math.pi * cyc[j] * t / T + ph[j]
            cx = px[j] + sway * math.sin(a)
            if rise:
                cy = y0 + (py[j] - y0 - rise * span * t / T) % span
                edge = min(cy - y0, y1 - cy) / max(1.0, min(6.0, span / 4))
                tw = (0.5 + 0.5 * math.sin(a * 2)) * min(1.0, max(0.0, edge))
            else:
                cy = py[j] + 2 * math.cos(a)
                tw = 0.5 + 0.5 * math.sin(a * 2)
            r = size * (0.7 + 0.6 * _hash(j, seed + 4))
            box = self._box(cx - 4 * r - 1, cy - 4 * r - 1, cx + 4 * r + 1, cy + 4 * r + 1)
            if box is None or tw <= 0:
                continue
            sl, ys, xs = box
            acc[sl] += tw * np.exp(-0.5 * ((xs - cx) ** 2 + (ys - cy) ** 2) / r ** 2)
        acc = self._weights(acc, (slice(None), slice(None)), behind)
        self._mix(strength * acc, colour, 'screen')
        return self

    # ------------------------------------------------------------ rain (F3)
    def rain(self, t, T, style='hair', n=None, angle=None, length=None, colour=None, alpha=None,
             width=None, cycles=None, seed=11, layers=None, region=None, behind=None,
             segments=(4, 4, 4, 12), alphas=(0.25, 0.45, 0.7, 1.0), splash=True, ends=3, width_px=None):
        """rain in one of three measured looks; every drop falls a whole number of spans per
        loop, so the loop is exact.
          'hair'   Sword & Sworcery: ~18 vertical anti-aliased hairlines, 8-10 art px long,
                   `width` working px wide (3 at screen res: a 2 px core and soft shoulders),
                   analytic coverage with `ends`-px end ramps, alpha by depth layer. Off the art
                   grid in res='screen', 1 art px wide in res='native'.
          'cell'   Celeste: 30 opaque white columns 1 x 30 art px, whole cells, over everything.
          'streak' Hyper Light Drifter: 2-3 falling 1 px light streaks with stepped alpha
                   `segments` (tail to head) and a 1 px splash diamond where they land
                   (region's bottom); slant from `angle` (95.14 = 0.09 px per row).
        length, alpha and cycles take (far, near) pairs spread over `layers` depth bins (near drops
        are longer, brighter, faster); width_px is another name for width; region=(x0, y0, x1, y1)
        in 1x px; behind: a 1x mask the rain passes behind (fx.rain_cells writes slots instead)."""
        width = width_px if width_px is not None else width
        P = dict(RAIN[style])
        for k, v in (('n', n), ('angle', angle), ('length', length), ('colour', colour),
                     ('alpha', alpha), ('cycles', cycles), ('layers', layers)):
            if v is not None:
                P[k] = v
        pair = lambda v: (v, v) if np.isscalar(v) else tuple(v)
        P['length'], P['alpha'], P['cycles'] = pair(P['length']), pair(P['alpha']), pair(P['cycles'])
        t = t % T
        region = region or (0, 0, self.w0, self.h0)
        before = None if behind is None else self.a.copy()
        if style == 'hair':
            self._rain_hair(t, T, P, width, seed, region, ends)
        elif style == 'cell':
            self._rain_cell(t, T, P, seed, region)
        elif style == 'streak':
            self._rain_streak(t, T, P, seed, region, segments, alphas, splash)
        else:
            raise ValueError("style is 'hair', 'cell' or 'streak', got %r" % (style,))
        if before is not None:
            m = self.up(np.asarray(behind, bool))
            self.a[m] = before[m]
        return self

    @staticmethod
    def _bins(i, P):
        lay = max(1, int(P['layers']))
        d = (i % lay + 1) / lay if lay > 1 else 1.0          # 1 = nearest
        lo, hi = P['length']; L = lo + (hi - lo) * d
        a0, a1 = P['alpha']; al = a0 + (a1 - a0) * d
        c0, c1 = P['cycles']; c = int(round(c0 + (c1 - c0) * d))
        return L, al, max(1, c)

    def _rain_hair(self, t, T, P, width, seed, region, ends):
        s = self.s
        width = (3.0 if s > 1 else 1.0) if width is None else float(width)
        a = math.radians(P['angle'])
        ux, uy = math.cos(a), math.sin(a)
        q = ux / uy                                          # sideways drift per row
        rx0, ry0, rx1, ry1 = [v * s for v in region]
        col = rgbf(P['colour'])
        for i in range(int(P['n'])):
            Ln, al, c = self._bins(i, P)
            L = Ln * s
            span = (ry1 - ry0) + L
            lo, hi = min(rx0, rx0 - q * span), max(rx1, rx1 - q * span)
            x0 = lo + _hash(i, seed) * (hi - lo)
            Y = ry0 + (_hash(i, seed + 1) * span + c * span * t / T) % span - L     # top end
            X = x0 + q * (Y - ry0 + L)
            if s == 1:                                       # native: centred on an art pixel column
                X = math.floor(X) + 0.5
            ex, ey = X + ux * L, Y + uy * L
            pad = width + 1
            j0, j1 = int(max(ry0, math.floor(min(Y, ey) - pad))), int(min(ry1, math.ceil(max(Y, ey) + pad)))
            i0, i1 = int(max(rx0, math.floor(min(X, ex) - pad))), int(min(rx1, math.ceil(max(X, ex) + pad)))
            if j1 <= j0 or i1 <= i0:
                continue
            py = np.arange(j0, j1)[:, None] + 0.5 - Y
            px = np.arange(i0, i1)[None, :] + 0.5 - X
            along = px * ux + py * uy
            perp = np.abs(-px * uy + py * ux)
            cov = np.clip(width / 2 + 0.5 - perp, 0, 1) * np.clip(np.minimum(along, L - along) / ends + 0.5, 0, 1)
            sl = (slice(j0, j1), slice(i0, i1))
            self._mix(al * cov, col, 'lerp', sl)

    def _rain_cell(self, t, T, P, seed, region):
        s = self.s
        x0, y0, x1, y1 = [int(v) for v in region]
        col = rgbf(P['colour'])
        slant = math.cos(math.radians(P['angle'])) / math.sin(math.radians(P['angle']))
        if abs(slant) < 1e-9:
            slant = 0.0
        for i in range(int(P['n'])):
            Ln, al, c = self._bins(i, P)
            L = int(round(Ln))
            S = (y1 - y0) + L
            drift = slant * S                                             # sideways travel per fall
            lo, hi = min(x0, x0 - drift), max(x1, x1 - drift)             # spawn so drops cover the region
            x = int(math.floor(lo + _hash(i, seed) * (hi - lo)))
            y = y0 + (int(_hash(i, seed + 1) * S) + (c * S * t) // T) % S - L    # integer: exact
            rows = np.arange(max(y0, y), min(y1, y + L))
            if not len(rows):
                continue
            if slant == 0.0:                                              # straight down: one column
                if not x0 <= x < x1:
                    continue
                sl = (slice(rows[0] * s, (rows[-1] + 1) * s), slice(x * s, x * s + s))
                self._mix(np.full((len(rows) * s, s), al), col, 'lerp', sl)
                continue
            # the column is a fixed line in the frame, x = x + slant * (row - y0 + L): the drop
            # moves along its own slant, stepping sideways every 1/slant rows (gusts)
            xs = x + np.floor(slant * (rows - y0 + L)).astype(int)
            ok = (xs >= x0) & (xs < x1)
            for r, cx in zip(rows[ok], xs[ok]):
                sl = (slice(r * s, r * s + s), slice(cx * s, cx * s + s))
                self._mix(np.full((s, s), al), col, 'lerp', sl)

    def _rain_streak(self, t, T, P, seed, region, segments, alphas, splash):
        s = self.s
        x0, y0, x1, y1 = [int(v) for v in region]
        col = rgbf(P['colour'])
        slant = math.cos(math.radians(P['angle'])) / math.sin(math.radians(P['angle']))
        seg_of = np.repeat(np.arange(len(segments))[::-1], np.array(segments)[::-1])   # r=0 head
        al_of = np.array(alphas, float)

        def cell(x, y, k):
            if x0 <= x < x1 and y0 <= y < y1 and k > 0:
                self._mix(np.full((s, s), k), col, 'lerp', (slice(y * s, y * s + s), slice(x * s, x * s + s)))

        for i in range(int(P['n'])):
            Ln, al, c = self._bins(i, P)
            L = int(round(Ln))
            span = (y1 - y0) + L
            xh = x0 + int(_hash(i, seed) * (x1 - x0))
            ph = int(_hash(i, seed + 1) * span)

            def head(tt):
                return y0 + (ph + (c * span * (tt % T)) // T) % span

            yh = head(t)
            for r in range(min(L, len(seg_of))):
                yy = yh - r
                xx = xh + int(math.floor(slant * (yy - y0)))
                cell(xx, yy, al * al_of[seg_of[r]])
            if splash:
                hit = y1 - 1                             # the floor row the streak lands on
                for back in (0, 1):                      # the landing shows for 2 frames
                    a_, b_ = head(t - back - 1), head(t - back)
                    if a_ <= b_ and a_ < hit <= b_:
                        xx = xh + int(math.floor(slant * (hit - y0)))
                        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            cell(xx + dx, hit - 1 + dy, al * (0.8 if back == 0 else 0.45))
                        break

    # ------------------------------------------------------------ planes, layers and sprites (A3, A4, E5)
    def paste(self, img, mask=None, ox=0, oy=0):
        """paste a crisp 1x plane (or sprite) over the frame with a hard mask (default: its alpha,
        or everything). (ox, oy) in 1x px; in res='screen' they may be fractional and land on
        the nearest screen pixel (sub-pixel parallax)."""
        rgba = _as_rgba(img)
        h, w = rgba.shape[:2]
        m = rgba[..., 3] > 0.5 if mask is None else np.asarray(mask, bool)
        s = self.s
        rgb = np.repeat(np.repeat(rgba[..., :3], s, 0), s, 1)
        mm = np.repeat(np.repeat(m, s, 0), s, 1)
        X, Y = int(round(ox * s)), int(round(oy * s))
        j0, j1 = max(0, Y), min(self.H, Y + h * s)
        i0, i1 = max(0, X), min(self.W, X + w * s)
        if j1 <= j0 or i1 <= i0:
            return self
        sub = mm[j0 - Y:j1 - Y, i0 - X:i1 - X]
        tgt = self.a[j0:j1, i0:i1]
        tgt[sub] = rgb[j0 - Y:j1 - Y, i0 - X:i1 - X][sub]
        hh, ww = self.src.shape[:2]                      # keep the 1x source in step (glow colours)
        x, y = int(round(ox)), int(round(oy))
        b0, b1, a0, a1 = max(0, y), min(hh, y + h), max(0, x), min(ww, x + w)
        if b1 > b0 and a1 > a0:
            m1 = m[b0 - y:b1 - y, a0 - x:a1 - x]
            self.src[b0:b1, a0:a1][m1] = rgba[b0 - y:b1 - y, a0 - x:a1 - x, :3][m1]
        return self

    def over(self, layer, alpha=0.88, ox=0, oy=0, height=None, z=0.0, fade=8.0, rim=True, space='linear'):
        """the module's over() on this frame: a translucent layer (cloud) at altitude z, thinned
        where the 1x height map rises toward it, with a 1 art px rim, all on the art grid"""
        hh, ww = self.src.shape[:2]
        L, A, A0 = _over_alpha(hh, ww, layer, alpha, ox, oy,
                           None if height is None else self._crop1x(np.asarray(height, float)), z, fade)
        rim_m = _rim_mask(A0, rim) & (A > 0.3)          # the cloud's outline, not where stacks pierce it
        ys, xs = np.nonzero((A > 0) | rim_m)
        if len(ys):                                      # only the layer's box, not the whole frame
            sl, (Lb, Ab, Rb) = self._lift_box((L, A, rim_m), ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)
            self.a[sl] = _blend_over(self.a[sl], Lb, Ab, Rb, space)
        return self

    def _lift_box(self, arrs, j0, j1, i0, i1):
        """the 1x box [j0:j1, i0:i1] of each array at working resolution, and its slice"""
        s = self.s
        ox, oy = (self._view[2], self._view[3]) if self._view is not None else (0, 0)
        Y, X = j0 * s - oy, i0 * s - ox
        J0, J1, I0, I1 = max(0, Y), min(self.H, j1 * s - oy), max(0, X), min(self.W, i1 * s - ox)
        out = []
        for a in arrs:
            b = a[j0:j1, i0:i1]
            if s > 1:
                b = np.repeat(np.repeat(b, s, 0), s, 1)
            out.append(b[J0 - Y:J1 - Y, I0 - X:I1 - X])
        return (slice(J0, J1), slice(I0, I1)), out

    @classmethod
    def from_world(cls, world, cam=(0.0, 0.0), size=(480, 270), scale=4):
        """a screen-res Post looking at a bigger 1x world through a camera at a fractional
        position: the world is cut one pixel larger, scaled up with nearest neighbour and cropped
        at round(scale * frac(cam)), so the camera pans in 1/scale art px while every texel stays
        a square block (Stardew). Later coordinates are view coordinates (world minus cam)."""
        W0 = _as_rgb(world)
        cx, cy = cam
        w, h = size
        ix, iy = int(math.floor(cx)), int(math.floor(cy))
        ox, oy = int(round(scale * (cx - ix))), int(round(scale * (cy - iy)))
        if ox >= scale:
            ix, ox = ix + 1, 0
        if oy >= scale:
            iy, oy = iy + 1, 0
        yi = np.clip(np.arange(iy, iy + h + 1), 0, W0.shape[0] - 1)
        xi = np.clip(np.arange(ix, ix + w + 1), 0, W0.shape[1] - 1)
        crop = W0[yi][:, xi]
        p = cls(crop[:h, :w], scale=scale, res='screen')
        p.src = crop
        p._view = (ix, iy, ox, oy, W0.shape[:2])
        p.a = p._lift(crop)
        p.cam = (cx, cy)
        return p

    def sprite(self, img, x, y, angle=0.0, pivot=(0.0, 0.0), alpha=1.0, flip=False):
        """draw a 1x RGBA sprite with its pivot (sprite px) at (x, y) (1x px, fractional ok),
        rotated `angle` degrees clockwise, sampled with nearest neighbour at working resolution:
        in res='screen' the texels stay whole art pixels turned on the screen grid (Stardew's
        sword: 45-degree diamonds). alpha < 1 for a translucent swing trail."""
        spr = _as_rgba(img)
        if flip:
            spr = spr[:, ::-1]
        h, w = spr.shape[:2]
        px, py = pivot
        a = math.radians(angle % 360.0)                  # 360 is 0 exactly (frame T == frame 0)
        ca, sa = round(math.cos(a), 12), round(math.sin(a), 12)
        corners = [(-px, -py), (w - px, -py), (-px, h - py), (w - px, h - py)]
        rx = [x + ca * u - sa * v for u, v in corners]
        ry = [y + sa * u + ca * v for u, v in corners]
        box = self._box(min(rx) - 1, min(ry) - 1, max(rx) + 1, max(ry) + 1)
        if box is None:
            return self
        sl, ys, xs = box
        dx, dy = xs - x, ys - y
        u = ca * dx + sa * dy + px                       # inverse rotation into sprite px
        v = -sa * dx + ca * dy + py
        iu, iv = np.floor(u).astype(int), np.floor(v).astype(int)
        ok = (iu >= 0) & (iu < w) & (iv >= 0) & (iv < h)
        smp = spr[np.clip(iv, 0, h - 1), np.clip(iu, 0, w - 1)]
        k = np.where(ok, smp[..., 3], 0.0) * alpha
        self._mix(k, smp[..., :3], 'lerp', sl)
        return self

    # ------------------------------------------------------------ lens and screen
    def vignette(self, amount=0.4, colour='#000000', power=2.2, colour_right=None, squash=1.0):
        """edge falloff toward colour (HLD: amount 0.30, power 2.0, squash 0.9, deep teal on the
        left drifting to indigo on the right via colour_right). Eight of the ten references have
        no vignette: frame with drawn darkness first."""
        yy, xx = self.grid()
        r = np.hypot((xx / self.w0 - 0.5) * 2, (yy / self.h0 - 0.5) * 2 * squash) / math.sqrt(2)
        k = np.clip(amount * r ** power, 0, 1)
        c = rgbf(colour).astype(np.float32)
        if colour_right is not None:
            f = np.clip(xx / self.w0, 0, 1)[..., None]
            c = c * (1 - f) + rgbf(colour_right).astype(np.float32) * f
        self._mix(k, c, 'lerp')
        return self

    def grade(self, tint=None, amount=0.0, lift=0.0, gain=1.0, saturation=1.0):
        """an overall colour grade: lift the blacks, scale the whites, mix toward a tint"""
        a = self.a
        if saturation != 1.0:
            g = a @ np.array([0.299, 0.587, 0.114])
            a = g[..., None] + (a - g[..., None]) * saturation
        a = lift + a * (gain - lift)
        if tint is not None and amount:
            a = a * (1 - amount) + a * rgbf(tint) * amount * 1.6
        self.a = np.clip(a, 0, 1).astype(np.float32)
        return self

    def scanlines(self, amount=0.18, every=None):
        """CRT scanlines: darken the last screen row of every art pixel row (or every `every`
        screen rows). In res='native' it runs on the delivered frame in image()."""
        if self.s == 1 and self.out > 1:
            self._late.append(('scanlines', amount, every))
            return self
        e = every or max(2, self.s)                      # at 1x: every other row
        rows = (np.arange(self.H) % e) == e - 1
        self.a[rows] *= 1 - amount
        return self

    def aberration(self, px=1):
        """chromatic aberration: red right, blue left by px screen pixels"""
        if not px:
            return self
        if self.s == 1 and self.out > 1:
            self._late.append(('aberration', px))
            return self
        self.a = _aberrate(self.a, px)
        return self

    def grain(self, t, amount=0.03, seed=9, T=None):
        """per-pixel noise, re-rolled every frame (T wraps it so the loop is exact)"""
        t = int(_wrap_t(t, T))
        n = _hash(np.arange(self.W * self.H) + t * 7919, seed).reshape(self.H, self.W) - 0.5
        self.a = np.clip(self.a + (amount * n[..., None]).astype(np.float32), 0, 1)
        return self

    # ------------------------------------------------------------ out
    def array(self):
        """the working float array (H, W, 3), unclipped (light can overbright before image())"""
        return self.a.copy()

    def image(self, upscale=None):
        """the finished frame as PIL RGB: in res='native' each art pixel is rounded to 8 bits and
        then scaled by `upscale` (default: scale) with nearest neighbour, so every cell is flat;
        in res='screen' the working frame as it is (already at scale)."""
        im = Image.fromarray((np.clip(self.a, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')
        k = self.out if upscale is None else int(upscale)
        if self.s == 1 and k != 1:
            im = im.resize((self.w0 * k, self.h0 * k), Image.NEAREST)
        elif self.s > 1 and upscale is not None and k != self.s:
            im = im.resize((self.w0 * k, self.h0 * k), Image.NEAREST)
        if self._late and (self.s > 1 or k > 1):
            a = np.asarray(im, float) / 255.0
            for op in self._late:
                if op[0] == 'scanlines':
                    e = op[2] or k
                    a[(np.arange(a.shape[0]) % e) == e - 1] *= 1 - op[1]
                else:
                    a = _aberrate(a, op[1])
            im = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')
        return im

def _aberrate(a, px):
    out = a.copy()
    out[:, px:, 0] = a[:, :-px, 0]
    out[:, :-px, 2] = a[:, px:, 2]
    return out

# ---------------------------------------------------------------- depth planes (A3)
class Stack:
    """depth planes composited far to near, each light applied at its own depth, so near
    silhouettes stay their flat dark while the air behind them glows (Sword & Sworcery: the near
    monolith is exactly #0c1013 inside the flare rows; the far one is washed).

        s = Stack(scale=3, res='screen', background='#0d151a')
        s.plane(sky, depth=3).plane(ruins, ruins_mask, depth=2).plane(near, near_mask, depth=0)
        s.light(lambda p: p.flare(157, 176, '#5f8fd0'), depth=2)    # over the ruins, behind near
        p = s.render()                                              # a Post: add rain, then UI
        p.rain(t, 96, style='hair').image()

    depth: larger is farther. A light at depth d runs after every plane with depth >= d and
    before the nearer ones; at equal depth the plane goes first, so it receives the light.
    size=(w, h) in 1x px; by default the size of the first plane."""
    def __init__(self, scale=4, res='native', background='#000000', size=None):
        self.scale, self.res, self.size = scale, res, size
        self.background = background
        self.items = []

    def plane(self, img, mask=None, depth=0, offset=(0, 0)):
        """a 1x plane (PIL or array, any size) with its hard mask (default: alpha, or all),
        placed at offset (1x px; fractional lands on screen pixels in res='screen')"""
        self.items.append((-depth, 0, len(self.items), ('plane', img, mask, offset)))
        return self

    def light(self, fn, depth=0):
        """fn(post) runs on the composite so far: any Post op (light, glow, shaft, flare, fog)"""
        self.items.append((-depth, 1, len(self.items), ('light', fn)))
        return self

    def render(self):
        """composite everything and return the Post (add rain and UI, then .image())"""
        planes = [it[3][1] for it in self.items if it[3][0] == 'plane']
        if self.size is None and not planes:
            raise ValueError('Stack.render needs a plane or size=(w, h)')
        w, h = self.size or _as_rgba(planes[0]).shape[1::-1]
        bg = np.broadcast_to(rgbf(self.background), (h, w, 3))
        p = Post(bg, self.scale, self.res)
        for _, _, _, it in sorted(self.items, key=lambda e: e[:3]):
            if it[0] == 'plane':
                _, img, mask, (ox, oy) = it
                p.paste(img, mask, ox, oy)
            else:
                it[1](p)
        return p
