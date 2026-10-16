"""Undithered skies: strata with interlocking tapered wisps (Celeste, 02), crescent 'smile'
strokes, and posterised horizontal cloud streaks (Into the Breach, 06). No dither anywhere: the
softness comes from shape, not from Bayer seams.

    import sky
    from canvas import Canvas, drift
    c = Canvas(320, 180)
    edges = sky.strata(c, [('s0', 0), ('s1', 26), ('s2', 58), ('s3', 104), ('s4', 124)], seed=2)
    sky.wisp(c, 60, 40, 46, 6, 's0', bow=-2)          # one hand-placed wisp
    sky.smile(c, 110, 44, 14, 's1')                   # a 1-2 px crescent stroke
    sky.streaks(c, 0, 120, 320, 180, ['d0', 'd1', 'd2', 'd3', 'd4'])   # an 06 cloud deck
    # a drifting loop: build the layer with period=its width, then canvas.drift(layer, t, T)
    layer = Canvas(640, 180); sky.strata(layer, bands, period=640); frame = drift(layer, t, T, 1, size=(320, 180))

Measured (study 02): band edges e_k(x) = round(y_k + 3 n(x/40) + 1.5 n(x/13)), flat runs of
5-15 px between 1 px steps; 3-6 wisps per edge, ~70% hanging from it, 25-55 px long, 2-8 px
thick, one long 1 px tail; 2-4 smiles per screen, 10-16 px. Study 06: streak runs median 5 px,
p90 24, tones lighter toward the bottom.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from shapes import _h, _hs, vnoise1, _grid

def _put_cols(g, xs, top, bot, slot, period=None):
    """fill rows [top, bot] (inclusive) in columns xs; wraps xs by period, else clips"""
    H, W = g.shape
    if period:
        xs = xs % period
    reps = range(0, W, int(period)) if period else (0,)   # a layer wider than its period repeats
    for x, a, b in zip(xs, top, bot):
        a, b = max(0, int(a)), min(H - 1, int(b))
        if b < a:
            continue
        for o in reps:
            if 0 <= x + o < W:
                g[a:b + 1, x + o] = slot

def wisp(c, cx, cy, length, thick, slot, bow=0.0, tail=1.6, tilt=0.0, flip=False, seed=0,
         attach=None, period=None):
    """one tapered wisp: across u in [-1, 1] the thickness is h(u) = thick * sin(pi s^(1/tail))^1.4
    with s = (u + 1)/2, so it swells near one end and runs out in a long 1 px tail at the other
    (flip=True puts the tail on the left). The centre row is cy + bow u^2 + tilt u (bow < 0
    lifts both ends, tilt > 0 drops the right end). Rows [y - .35h - notch, y + .65h], where a
    hashed 1 px notch on 40% of 4 px runs roughens the top. attach: an edge array e(x) of the canvas
    width; where the wisp's top lies within 3 px below it, the gap is filled so the wisp hangs
    from the edge. period wraps x (a layer that drifts)."""
    g = _grid(c)
    half = length / 2.0
    if half < 0.5 or thick <= 0:
        return
    xs = np.arange(int(math.floor(cx - half)), int(math.ceil(cx + half)) + 1)
    u = (xs + 0.5 - cx) / half
    ok = np.abs(u) <= 1
    xs, u = xs[ok], u[ok]
    s = (1 - u) / 2 if flip else (u + 1) / 2
    hh = thick * np.sin(math.pi * np.clip(s, 0, 1) ** (1.0 / tail)) ** 1.4
    keep = hh >= 0.5
    xs, u, hh, s = xs[keep], u[keep], hh[keep], s[keep]
    yc = cy + bow * u * u + tilt * u
    notch = np.where((hh > 2.5) & (_h(xs // 4, 1, seed) < 0.4), 1, 0)
    top = np.floor(yc - 0.35 * hh - notch + 0.5).astype(int)
    bot = np.floor(yc + 0.65 * hh + 0.5).astype(int) - 1
    bot = np.maximum(bot, top)
    if attach is not None:                             # the head joins the edge, the tail floats
        e_arr, side = attach if isinstance(attach, tuple) else (attach, 'below')
        W = len(e_arr)
        e = np.asarray(e_arr)[(xs % period) if period else np.clip(xs, 0, W - 1)]
        head = s < 0.5 ** tail * 1.6
        if side == 'below':
            gap = top - e
            top = np.where(head & (gap > 0) & (gap <= 4), e, top)
        else:
            gap = e - 1 - bot
            bot = np.where(head & (gap > 0) & (gap <= 4), e - 1, bot)
    _put_cols(g, xs, top, bot, slot, period)

def smile(c, cx, cy, length, slot, bow=2.5, thick=2, seed=0, period=None):
    """a crescent stroke (02): ends `bow` px above the middle, `thick` px thick over the middle
    half and 1 px toward the tips. cy is the row of the middle."""
    g = _grid(c)
    half = length / 2.0
    if half < 0.5:
        return
    xs = np.arange(int(math.floor(cx - half)), int(math.ceil(cx + half)))
    u = (xs + 0.5 - cx) / half
    y = np.floor(cy - bow * u * u + 0.5).astype(int)
    t = np.where(np.abs(u) < 0.5, thick, 1)
    _put_cols(g, xs, y - t + 1, y, slot, period)

def strata(c, bands, x0=0, x1=None, y0=0, y1=None, amp=(3, 1.5), cells=(40, 13), wisps=7,
           smiles=0, length=(25, 55), thick=(2, 8), attached=0.7, echo=0.4, seed=0, period=None):
    """undithered sky strata (Celeste, 02). bands = [(slot, y_top), ...] top to bottom; the first
    starts at y0. Boundary k is e_k(x) = round(y_k + amp[0] n(x/cells[0]) + amp[1] n(x/cells[1]))
    and a pixel takes the slot of the last boundary above it. Then each boundary is interlocked
    with about `wisps` wisps per 160 px of width: `attached` (70%) grow out of the edge (two
    thirds hang down in the upper band's slot, a third rise in the lower band's), the rest float
    inside a band in a neighbour band's slot; `echo` of the hanging ones get a thinner, shorter
    strand 2-4 px under them (the feathered look). `smiles` adds
    that many crescents per 320 px in the darker band of where they land.
    Returns the edges: a list of int arrays (one per boundary, indexed by canvas column).
    period: every shape repeats every `period` px (generate a layer that wide and drift it)."""
    g = _grid(c)
    H, W = g.shape
    x1 = W if x1 is None else min(W, int(x1))
    y1 = H if y1 is None else min(H, int(y1))
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    xs = np.arange(W)
    edges = []
    for k, (slot, yk) in enumerate(bands[1:]):
        n = amp[0] * vnoise1(xs, cells[0], seed + 101 * (k + 1), period) + \
            amp[1] * vnoise1(xs, cells[1], seed + 101 * (k + 1) + 7, period)
        edges.append(np.floor(yk + n + 0.5).astype(int))
    yy = np.arange(y0, y1)[:, None]
    idx = np.zeros((y1 - y0, x1 - x0), np.int32)
    for e in edges:
        idx += yy >= e[None, x0:x1]
    lut = np.array([b[0] for b in bands], object)
    g[y0:y1, x0:x1] = lut[idx]
    span = (period or (x1 - x0))
    sub = np.full((H, W), None, object)               # wisps land here, then inside the box
    for k, e in enumerate(edges):
        above, below = bands[k][0], bands[k + 1][0]
        nxt = edges[k + 1] if k + 1 < len(edges) else np.full(W, y1)
        prv = edges[k - 1] if k > 0 else np.full(W, y0)
        nw = int(round(wisps * span / 160.0 * (0.75 + 0.5 * _hs(k, 1, seed))))
        for i in range(nw):
            hs = lambda j: _hs(i, 100 * k + j, seed)
            cx = x0 + (i + 0.1 + 0.8 * hs(2)) * span / max(1, nw)
            L = length[0] + (length[1] - length[0]) * hs(3)
            T = thick[0] + (thick[1] - thick[0]) * hs(4) ** 0.8      # median ~5 px, as measured
            bow = -7 + 10 * hs(5)                 # mostly lifting tips, sometimes drooping
            tilt = (hs(6) * 2 - 1) * 4
            tl = 1.4 + 0.6 * hs(7)
            flip = hs(8) < 0.5
            col = int(cx) % W
            sd = seed + 1000 * k + i
            r = hs(9)
            if r < attached * 0.65:                                  # hangs below the edge
                cy = e[col] + 0.35 * T + 1 + 2 * hs(13)
                wisp(sub, cx, cy, L, T, above, bow, tl, tilt, flip, sd, attach=(e, 'below'), period=period)
                if hs(14) < echo and T > 3:                          # a thinner strand under it
                    wisp(sub, cx + (hs(15) - 0.3) * L * 0.4, cy + 0.65 * T + 2 + hs(16) * 2, L * 0.65,
                         max(1.5, T * 0.4), above, bow * 0.6, tl, tilt, flip, sd + 7, period=period)
            elif r < attached:                                       # rises above it
                cy = e[col] - 0.65 * T - 1 - 2 * hs(13)
                wisp(sub, cx, cy, L, T * 0.8, below, -bow, tl, tilt, flip, sd, attach=(e, 'above'), period=period)
            elif hs(10) < 0.5 and nxt[col] - e[col] > T + 4:        # a darker wisp adrift below
                cy = e[col] + (nxt[col] - e[col]) * (0.25 + 0.5 * hs(11))
                wisp(sub, cx, cy, L, T, above, bow, tl, tilt, flip, sd, period=period)
            elif e[col] - prv[col] > T + 4:                          # a lighter one adrift above
                cy = prv[col] + (e[col] - prv[col]) * (0.3 + 0.5 * hs(12))
                wisp(sub, cx, cy, L, T * 0.8, below, -bow, tl, tilt, flip, sd, period=period)
    ns = int(round(smiles * span / 320.0))
    for i in range(ns):
        cx = x0 + (i + 0.2 + 0.6 * _hs(i, 1, seed + 77)) * span / max(1, ns)
        col = int(cx) % W
        cy = y0 + (y1 - y0) * (0.12 + 0.6 * _hs(i, 2, seed + 77))
        b = int(np.sum(cy >= np.array([e[col] for e in edges])))
        slot = bands[max(0, b - 1)][0] if b > 0 else bands[0][0]
        if b == 0:
            continue
        smile(sub, cx, cy, 10 + 6 * _hs(i, 3, seed + 77), slot, 2 + _hs(i, 4, seed + 77), 2, period=period)
    a = sub[y0:y1, x0:x1]
    m = ~np.equal(a, None)
    g[y0:y1, x0:x1][m] = a[m]
    return edges

def streaks(c, x0, y0, x1, y1, tones, cover=None, run=(2, 24), rows=(1, 3), every=(6, 10),
            period=None, offset=0, seed=0):
    """horizontal cloud streaks (Into the Breach's cloud deck, 06) filling [x0, x1) x [y0, y1).
    tones: slots dark to light. Each row has a base tone that steps one lighter every every=(6,
    10) rows down; the row is walked in runs of 2 + floor(h^2 * 23) px (median ~5, p90 ~24),
    each run the next tone up when a hash falls under cover(v) (v = 0 at the top .. 1 at the
    bottom; default 0.2 + 0.5 v), else the base tone. Rows start at a hashed 0-5 px offset; a
    row pattern is repeated over rows=(1, 3) rows (vertical runs median ~2-3), each repeat nudged
    1-2 px right, so the run ends stair-step.
    period: the pattern repeats every `period` px; offset shifts it (a drift loop: offset =
    canvas.wrap_offset(t, T, period, trips))."""
    g = _grid(c)
    H, W = g.shape
    x0, x1 = max(0, int(x0)), min(W, int(x1))
    y0i, y1i = int(y0), int(y1)
    if x1 <= x0 or y1i <= y0i:
        return
    if cover is None:
        cover = lambda v: 0.2 + 0.5 * v
    P = int(period) if period else (x1 - x0)
    nt = len(tones)
    # base tone per row: one step lighter every 6-10 rows
    base, b, nxt, k = [], 0, y0i, 0
    for y in range(y0i, y1i):
        if y >= nxt and y > y0i:
            b += 1
        if y >= nxt:
            nxt = y + every[0] + int((every[1] - every[0] + 1) * _hs(k, 1, seed))
            k += 1
        base.append(min(max(0, nt - 2), b))
    y = y0i
    cols = (np.arange(x0, x1) - x0 - int(offset)) % P
    while y < y1i:
        rh = rows[0] + int(_hs(y, 3, seed) ** 1.5 * (rows[1] - rows[0] + 1))
        bt = base[y - y0i]
        v = (y - y0i) / max(1, y1i - y0i - 1)
        row = np.empty(P, object)
        x = -int(_hs(y, 7, seed) * 6)
        i = 0
        while x < P:
            r = run[0] + int(_hs(y, 1000 + i, seed) ** 2 * (run[1] - run[0] + 1))
            up = _hs(y, 5000 + i, seed) < cover(v)
            row[max(0, x):min(P, x + r)] = tones[min(nt - 1, bt + 1)] if up else tones[bt]
            x += r
            i += 1
        sh = 0
        for yy in range(y, min(y1i, y + rh)):          # a block of rows, each nudged 1-2 px
            if 0 <= yy < H:
                g[yy, x0:x1] = row[(cols - sh) % P]
            sh += 1 + int(_hs(yy, 9, seed) < 0.4)
        y += rh
