"""Sprite helpers: trailing chains (scarf, hair, tail), specular edge strokes and drop shadows.

Sprites here are object grids of slot names (None = transparent): a Canvas's c.g, a numpy object
array, or an artlib.Grid (converted on the way in and written back).

    import sprite, anim
    head = lambda t: (40 + anim.stepped_sin(t, 48, 1, 3, hold=2), 30)       # where the chain hangs
    g, x0, y0 = sprite.chain(head, t, 48, n=5, droop=(-2.2, 0.9))          # hair streams left (02)
    sprite.paste(c, g, x0, y0)                                              # behind: paste first
    c.g[body] = ...                                                         # then the body over it
    sprite.spec_edges(c, unit_mask, slot='spec', min_step=0)               # 1px white strokes (06)
    sprite.drop_shadow(c, 60, 101, rx=5)                                    # ground steps down 2 (10)
    sprite.drop_shadow(rgb, 60*4, 101*4, rx=20, ry=8)                       # or a plum lerp at screen res

Learned from Celeste's hair and Katana ZERO's scarf (a kinematic chain, each node replaying the
anchor a few frames late), Into the Breach's speculars (white 2-5 px strokes on edges facing the
upper left, next to the black outline, about 4% of the unit) and Stardew's plum drop shadows.
"""
import math, pathlib, sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph

__all__ = ['chain', 'paste', 'spec_edges', 'drop_shadow', 'grid_of']

def _h(a, b, s=0):
    h = (np.asarray(a).astype(np.int64) * 374761393 + np.asarray(b).astype(np.int64) * 668265263
         + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def grid_of(target):
    """(object array, commit): the slot grid of a Canvas / array / artlib.Grid, and a function
    that writes changes back (a no-op for the first two, which are edited in place)"""
    if hasattr(target, 'g') and isinstance(getattr(target, 'g'), np.ndarray):
        return target.g, lambda: None
    if hasattr(target, 'a') and isinstance(getattr(target, 'a'), list):      # artlib.Grid
        arr = np.empty((target.h, target.w), object)
        for y, row in enumerate(target.a):
            arr[y, :] = row
        def commit():
            target.a = [list(r) for r in arr]
        return arr, commit
    return np.asarray(target, object), lambda: None

def _step(slot):
    s = str(slot)
    if slot is None or s.startswith('#'):
        return None, None
    b = s.rstrip('0123456789')
    return (b, int(s[len(b):])) if b != s else (s, None)

# ---------------------------------------------------------------- trailing chain
def chain(anchor_path, t, T, n=5, radii=(4, 3.5, 3, 2.5, 2), lag=2, droop=(-2.2, 0.9), wind=None,
          slots=('acc2', 'acc1', 'ol'), light=(1, -1), outline=True):
    """a scarf, hair mass or tail that trails its anchor (02 hair, 09 scarf, 05 packs).
    node_i(t) = anchor(t_i) + i*droop + i*0.5*wind(t_i) with t_i = (t - lag*i) mod T, floored
    (a gust travels down the chain as a wave: a scarf flaps rather than tilts); the union of
    discs (radius radii[i]) joined by a tapered capsule where two discs would part, so fast motion never tears it
    (closer nodes stay a lumpy union of discs, the drawn look).
    slots = (lit, shade, outline): pixels whose neighbour away from the light is outside take
    the shade (the default light (1, -1) shades the lower-left rim, as the plan and 02's hair),
    the 1 px outer ring the outline (None skips it).
    anchor_path(t) -> (x, y) in canvas px; wind: (wx, wy), or a function of t (use a stepped
    table for gusts). -> (grid, x0, y0): an object array to paste at (x0, y0), None outside."""
    n = min(n, len(radii))
    pts = []
    for i in range(n):
        tl = (t - lag * i) % T
        w = wind(tl) if callable(wind) else (wind or (0.0, 0.0))
        ax, ay = anchor_path(tl)
        pts.append((math.floor(ax + i * droop[0] + i * 0.5 * w[0]) + 0.5,
                    math.floor(ay + i * droop[1] + i * 0.5 * w[1]) + 0.5, float(radii[i])))
    rmax = max(r for _, _, r in pts) + 2
    x0 = int(math.floor(min(p[0] for p in pts) - rmax))
    y0 = int(math.floor(min(p[1] for p in pts) - rmax))
    x1 = int(math.ceil(max(p[0] for p in pts) + rmax)) + 1
    y1 = int(math.ceil(max(p[1] for p in pts) + rmax)) + 1
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    m = np.zeros(xx.shape, bool)
    for i, (px, py, r) in enumerate(pts):
        m |= (xx - px) ** 2 + (yy - py) ** 2 <= (r + 0.15) ** 2
        if i:                                              # capsule to the previous node
            qx, qy, rq = pts[i - 1]
            dx, dy = px - qx, py - qy
            l2 = dx * dx + dy * dy
            if l2 > (0.7 * (r + rq)) ** 2:                 # only where the discs would part
                s = np.clip(((xx - qx) * dx + (yy - qy) * dy) / l2, 0, 1)
                rr = rq + (r - rq) * s
                m |= (xx - qx - s * dx) ** 2 + (yy - qy - s * dy) ** 2 <= (rr + 0.15) ** 2
    lit, shade, ol = slots
    g = np.full(m.shape, None, object)
    g[m] = lit
    sx = 1 if light[0] < 0 else -1 if light[0] > 0 else 0
    sy = 1 if light[1] < 0 else -1 if light[1] > 0 else 0
    away = np.zeros_like(m)
    if sx:
        away |= ~morph.shift(m, -sx, 0, False)
    if sy:
        away |= ~morph.shift(m, 0, -sy, False)
    g[m & away] = shade
    if outline and ol is not None:
        g[morph.boundary(m, outer=True, conn=4, border=False)] = ol
    return g, x0, y0

def paste(target, g, x0, y0, behind=None):
    """write the non-None pixels of g into target at (x0, y0). behind: a bool mask (target's
    size) of pixels to leave alone, e.g. the body when the chain hangs behind it"""
    arr, commit = grid_of(target)
    H, W = arr.shape
    h, w = g.shape
    ax0, ay0 = max(0, x0), max(0, y0)
    ax1, ay1 = min(W, x0 + w), min(H, y0 + h)
    if ax1 <= ax0 or ay1 <= ay0:
        return target
    sub = g[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
    m = np.array([[v is not None for v in row] for row in sub], bool) if sub.size else sub
    if behind is not None:
        m &= ~np.asarray(behind, bool)[ay0:ay1, ax0:ax1]
    arr[ay0:ay1, ax0:ax1][m] = sub[m]
    commit()
    return target

# ---------------------------------------------------------------- specular edge strokes
def spec_edges(grid, mask=None, light=(-1, -1), slot='spec', min_step=3, run=(2, 5), cap=0.04,
               ol='ol', seed=0):
    """1 px specular strokes on the edges that face the light (06 Into the Breach units, 05
    shoulders): candidates are unit pixels whose neighbour toward the light (left / top for the
    default upper-left light) is outline or empty. Each edge run is cut into strokes of
    run=(2, 5) px with one pixel dropped between strokes; shorter leftovers are dropped; strokes
    nearest the light win (every edge's first stroke before any second) until each unit (8-connected
    piece of the mask) holds cap * its bounding-box area. Pixels below ramp step
    `min_step` are skipped (min_step=0 for an all-dark body that reads only by its speculars).
    mask: the unit (default: every non-None, non-outline pixel). Edits grid; returns the mask
    of the strokes."""
    arr, commit = grid_of(grid)
    H, W = arr.shape
    olm = np.zeros((H, W), bool) if ol is None else (arr == ol)
    filled = np.not_equal(arr, None)
    unit = (filled & ~olm) if mask is None else (np.asarray(mask, bool) & ~olm)
    outside = ~unit | olm
    steps = np.vectorize(lambda v: (_step(v)[1] if _step(v)[1] is not None else -1),
                         otypes=[int])(arr) if unit.any() else np.zeros((H, W), int)
    ok = unit & (steps >= min_step)
    sx = -1 if light[0] < 0 else 1 if light[0] > 0 else 0
    sy = -1 if light[1] < 0 else 1 if light[1] > 0 else 0
    strokes = []                                           # (priority, [(y, x), ...])
    lx, ly = light
    def cut(cells, key):
        k, i = 0, 0
        while i < len(cells):
            L = run[0] + int(_h(key, k, seed + 3) ** 2 * (run[1] - run[0] + 1))   # mostly 2-3 px
            piece = cells[i:i + L]
            if len(piece) >= run[0]:
                cy = np.mean([p[0] for p in piece]); cx = np.mean([p[1] for p in piece])
                # every edge's first stroke before any second one, nearest the light first
                pri = 2.0 * k - (lx * cx + ly * cy) / max(H, W) + 0.15 * _h(key, k, seed + 5)
                strokes.append((pri, piece))
            i += L + 1                                     # one pixel dropped after each stroke
            k += 1
    if sx:                                                 # vertical runs on the lit side
        c = ok & morph.shift(outside, -sx, 0, True)
        for x in range(W):
            col = np.nonzero(c[:, x])[0]
            if len(col):
                for seg in np.split(col, np.nonzero(np.diff(col) > 1)[0] + 1):
                    cut([(int(y), x) for y in seg], x * 7919)
    if sy:                                                 # horizontal runs on the lit top
        c = ok & morph.shift(outside, 0, -sy, True)
        if sx:                                             # corners already taken by a column,
            col = ok & morph.shift(outside, -sx, 0, True)  # and a 1 px gap after them: separate
            c &= ~col & ~morph.shift(col, -sx, 0, False)   # strokes, never an L
        for y in range(H):
            row = np.nonzero(c[y])[0]
            if len(row):
                for seg in np.split(row, np.nonzero(np.diff(row) > 1)[0] + 1):
                    cut([(y, int(x)) for x in seg], y * 104729 + 1)
    strokes.sort(key=lambda s: s[0])
    # budget per unit (8-connected piece): cap * its bounding-box area (06: 8-10 strokes of 2-5 px
    # on a 27x24 mech), so a mask holding many units never lets one starve the others
    lab, nl = morph.label(unit, 8)
    idx = np.nonzero(lab.ravel())[0]                     # each piece's bbox in one pass
    ly_, lx_ = np.divmod(idx, W)
    lb = lab.ravel()[idx]
    y0 = np.full(nl + 1, H); y1 = np.full(nl + 1, -1); x0 = np.full(nl + 1, W); x1 = np.full(nl + 1, -1)
    np.minimum.at(y0, lb, ly_); np.maximum.at(y1, lb, ly_)
    np.minimum.at(x0, lb, lx_); np.maximum.at(x1, lb, lx_)
    budget = cap * (y1 - y0 + 1) * (x1 - x0 + 1)
    out = np.zeros((H, W), bool)
    used = {}
    for _, piece in strokes:
        k = int(lab[piece[0]])
        if used.get(k, 0) + len(piece) > round(budget[k]):
            continue
        for y, x in piece:
            out[y, x] = True
        used[k] = used.get(k, 0) + len(piece)
    arr[out] = slot
    commit()
    return out

# ---------------------------------------------------------------- drop shadow
def _ellipse(H, W, x, y, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    return ((xx - x) / max(rx, 0.5)) ** 2 + ((yy - y) / max(ry, 0.5)) ** 2 <= 1.0

def drop_shadow(target, x, y, rx, ry=2, colour='#140818', alpha=0.65, steps=-2, altitude=0,
                keep=('ol',), only=None):
    """an elliptical shadow centred on (x, y) (10 Stardew, 04 Sea of Stars, 06 units).
    target an RGB array (H, W, 3) or PIL image: lerp toward `colour` by alpha (a plum shadow at
    screen resolution; returns the new image for PIL). target a slot grid / Canvas: every ramp
    slot under it steps by `steps` (strict palette mode), except slots in `keep`; only: a tuple
    of base prefixes allowed to darken (the ground). A flyer's shadow shrinks with its height:
    rx *= 1 - 0.01 * altitude. Returns the target."""
    rx = rx * (1 - 0.01 * altitude)
    try:
        from PIL import Image
        is_pil = isinstance(target, Image.Image)
    except ImportError:                                    # pragma: no cover
        is_pil = False
    if is_pil or (isinstance(target, np.ndarray) and target.ndim == 3):
        mode = (target.mode if target.mode in ('RGB', 'RGBA') else 'RGB') if is_pil else None
        a = np.asarray(target.convert(mode)).copy() if is_pil else target
        m = _ellipse(a.shape[0], a.shape[1], x, y, rx, ry)
        c = np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], float)
        rgb = a[..., :3].astype(float)
        rgb[m] = rgb[m] * (1 - alpha) + c * alpha
        if np.issubdtype(a.dtype, np.integer):
            rgb = np.clip(np.floor(rgb + 0.5), 0, 255)
        a[..., :3] = rgb.astype(a.dtype)                   # an alpha channel is left alone
        return Image.fromarray(a, mode) if is_pil else target
    arr, commit = grid_of(target)
    m = _ellipse(arr.shape[0], arr.shape[1], x, y, rx, ry)
    for v in set(arr[m].tolist()) - {None}:
        if v in keep:
            continue
        b, n = _step(v)
        if n is None or (only and not b.startswith(tuple(only))):
            continue
        arr[m & (arr == v)] = '%s%d' % (b, max(0, n + steps))
    commit()
    return target
