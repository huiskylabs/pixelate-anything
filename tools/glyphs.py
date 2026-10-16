"""Procedural emissive runes: blocky, mirror-symmetric glyphs grown from a seed, stamped with a
two-tone split (hot top, deeper bottom) in a recessed frame.

    import glyphs, anim
    r = glyphs.rune(7, w=7, h=9)                         # bool (9, 7): reseeded until it reads
    glyphs.stamp(c, 120, 40, r, hi='emit_hi', lo='emit_lo', split=0.35, recess='pillar0')
    lit = anim.cascade(t, T, n=6, stagger=3)             # light a column of runes in turn
    for j, y in enumerate(range(30, 130, 18)):
        glyphs.stamp(c, 183, y, glyphs.rune(j), lit=lit[j], off='pillar1')
    print(glyphs.preview(r))                             # '#' and '.' rows

Learned from Hyper Light Drifter's pillar panels (03): orange top bars over red-pink stems,
E-bars, blocks, a 'TT' pair and a U in a box, all blocky and mirror-symmetric, filling 40-65%
of their box, in 1 px recessed frames. A rune is half-width stroke primitives picked by hash,
mirrored, and kept only when its fill is in range and it is one 4-connected piece. The emitter
masks feed a glow (post.py) with the cascade strength.
"""
import pathlib, sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph
from sprite import grid_of

__all__ = ['rune', 'stamp', 'preview', 'PRIMITIVES']

def _hf(a, b, s=0):
    h = (int(a) * 374761393 + int(b) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

# ---------------------------------------------------------------- stroke primitives
# each draws into g (h x hw: the left half, the last column is the centre line for odd w)
def _top_bar(g, r):
    h, hw = g.shape
    g[:1 + int(r(0) * 3), :] = True                       # rows 0..0-2, full half width

def _stem(g, r):
    h, hw = g.shape
    w = 1 + int(r(1) * 2)                                  # 1-2 columns beside the centre
    y0 = int(r(2) * h * 0.4)
    g[y0:, hw - w:] = True

def _ebars(g, r):
    h, hw = g.shape
    x0 = int(r(3) * max(1, hw - 2))
    g[0, x0:] = True
    g[h // 2, x0 + 1:] = True
    g[h - 1, x0:] = True
    g[:, x0] = True

def _box_ring(g, r):
    h, hw = g.shape
    y0 = int(r(4) * h * 0.45)
    g[y0, :] = True
    g[h - 1, :] = True
    g[y0:, 0] = True

def _u_inner(g, r):
    h, hw = g.shape
    if hw < 3 or h < 5:
        return
    x = max(1, hw - 2 - int(r(5) * 2))
    y0 = h // 3 + int(r(6) * 2)
    g[y0:h - 2, x] = True
    g[h - 3, x:] = True

def _ticks(g, r):
    h, hw = g.shape
    y = min(h - 1, 1 + int(r(7) * max(0, h - 3)))
    g[y, :max(1, hw // 2)] = True
    if r(8) < 0.5 and y + 2 < h:
        g[y + 2, :max(1, hw // 2)] = True

def _block(g, r):
    h, hw = g.shape
    y0 = int(r(9) * h * 0.5)
    y1 = min(h, y0 + 3 + int(r(10) * (h // 2)))
    x0 = int(r(11) * max(1, hw - 1))
    g[y0:y1, x0:] = True

def _diag(g, r):
    h, hw = g.shape
    y0 = int(r(12) * (h // 2))
    for k in range(hw):
        y = y0 + k
        if y < h:
            g[y, k] = True
            if y + 1 < h:
                g[y + 1, k] = True

def _legs(g, r):
    h, hw = g.shape
    x = int(r(13) * max(1, hw - 1))
    g[max(0, h - 2 - int(r(14) * 2)):, x] = True

PRIMITIVES = (_top_bar, _stem, _ebars, _box_ring, _u_inner, _ticks, _block, _diag, _legs)
_WEIGHTS = (1.0, 1.0, 0.45, 0.4, 0.5, 0.6, 0.5, 0.25, 0.5)

def _one(seed, w, h, symmetric):
    hw = (w + 1) // 2 if symmetric else w
    g = np.zeros((h, hw), bool)
    r = lambda k: _hf(seed, k, 977)
    n = 2 + int(r(20) * 3)                                 # 2-4 primitives
    cum = np.cumsum(_WEIGHTS) / sum(_WEIGHTS)
    used = set()
    k = 0
    while len(used) < n and k < 24:                        # n distinct primitives
        i = int(np.searchsorted(cum, _hf(seed, 30 + k, 977), side='right'))
        i = min(i, len(PRIMITIVES) - 1)
        if i not in used:
            used.add(i)
            PRIMITIVES[i](g, lambda j, k=k: _hf(seed * 31 + k, j, 991))
        k += 1
    if not symmetric:
        return g
    right = g[:, :w - hw][:, ::-1] if w % 2 else g[:, ::-1]
    return np.concatenate([g, right], 1)

def rune(seed, w=7, h=9, symmetric=True, fill=(0.4, 0.65), tries=200):
    """a blocky glyph as a bool array (h, w): 2-4 stroke primitives (top bar, stem, E-bars, box
    ring, inner U, side ticks, block, diagonal step, legs) drawn on the left half and mirrored.
    Reseeded until its fill fraction lies in `fill` and it is one 4-connected piece (03)."""
    best = None
    for k in range(tries):
        g = _one(seed * 7919 + k, w, h, symmetric)
        f = g.mean()
        _, nlab = morph.label(g, 4)
        if nlab == 1 and fill[0] <= f <= fill[1]:
            return g
        if nlab == 1 and (best is None or abs(f - sum(fill) / 2) < abs(best.mean() - sum(fill) / 2)):
            best = g
    return best if best is not None else g

def stamp(c, x, y, r, hi='emit_hi', lo='emit_lo', split=0.35, recess=None, lit=1.0, off=None,
          threshold=0.5):
    """stamp rune r at (x, y): rows above split * h take `hi` (the hot orange top), the rest `lo`
    (the red-pink stem) (03). recess: a 1 px frame slot drawn one pixel outside the rune's box
    (the recessed panel). lit: the rune's strength (from anim.cascade); below `threshold` it is
    drawn in `off` (a dim engraving) or not at all. Returns the rune's bool mask in grid size
    (feed it, times lit, to a glow)."""
    arr, commit = grid_of(c)
    H, W = arr.shape
    h, w = r.shape
    if recess is not None:
        for yy in range(y - 1, y + h + 1):
            for xx in (x - 1, x + w):
                if 0 <= yy < H and 0 <= xx < W:
                    arr[yy, xx] = recess
        for xx in range(x - 1, x + w + 1):
            for yy in (y - 1, y + h):
                if 0 <= yy < H and 0 <= xx < W:
                    arr[yy, xx] = recess
    full = np.zeros((H, W), bool)
    on = lit >= threshold
    ys, xs = np.nonzero(r)
    cut = split * h
    for yy, xx in zip(ys, xs):
        px, py = x + xx, y + yy
        if not (0 <= px < W and 0 <= py < H):
            continue
        full[py, px] = True
        v = (hi if yy < cut else lo) if on else off
        if v is not None:
            arr[py, px] = v
    commit()
    return full

def preview(r):
    """rows of '#' and '.'"""
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in r)
