#!/usr/bin/env python3
"""Pixel-craft metrics: the things a pixel artist sees at zoom (stray pixels, jaggy lines, stripes,
pillow shading, dirty clusters), measured on a native 1x frame as numbers, and held to limits per
style that were measured on the ten reference games.

usage: craftcheck.py IMAGE [--scale N] [--style NAME] [--intent MASK.png] [--json]
       (--scale N: IMAGE is a delivered N x frame, sampled back to 1x first)

    import craftcheck as cc
    m = cc.measure(img_1x)                               # {'orphans': .., 'jaggies': .., ...}
    m = cc.measure(img_1x, intent=sparkle_mask, objects={'hut': hut_mask, 'rock': rock_mask})
    fails = cc.check(img_1x, 'lofi')                     # [] when every metric is inside CRAFT['lofi']
    rows = cc.report(img_1x, 'neon-noir')                # [(metric, value, lo, hi, 'ok'|'fail')]
    cc.orphans(img_1x, intent=flecks)                    # each metric is also its own function

Metrics (one number each; 'same colour' means an OKLab distance under TOL, so JPEG noise and a
native light field read as one colour while palette steps never do):
  orphans         share of pixels with no 4-neighbour of the same colour. Pixels in `intent` (sparkles,
                  flecks, stars, rain heads placed on purpose) are left out of the count, and so is
                  dither: a lone pixel repeated on both sides at 2 or 4 px, or on both corners of a
                  diagonal (checkerboard, Bayer dots, dotted rims).
  jaggies         along strong colour edges (OKLab distance >= EDGE), the staircases of 3+ runs: the
                  share of inner runs that break the pattern, longer or shorter than both neighbours
                  (1-1-2-1, 3-1-3), unless the line alternates evenly (2-3-2-3); over JAG_MIN+ runs
  stripes         share of pixels in parallel bands: 3+ runs of equal width (>= 2 px) stepping one
                  way through near ramp steps down a column (or along a row), repeated across 3+
                  columns. A gradient that reads as stripes; dither or uneven strata do not count.
  doubled         share of thin dark-line pixels (1-2 px runs darker than both sides by LINE_DL)
                  that are two different dark colours side by side: two outlines touching
  pillow          share of pixels (of the `objects` masks, if given) shaded in concentric rings: a
                  core wholly ringed by a darker cluster, ringed by a darker one again (3+ levels).
                  Shading that follows the outline inward on all sides instead of one light.
  cluster_px      median over colours of the mean 4-connected cluster size (bigger = cleaner)
  small_clusters  share of clusters under 3 px (intent and dither pixels left out)

CRAFT holds the limits per style, {metric: (lo, hi)} like stats budgets, each from the reference
the style is learned from (its native frame recovered from the screenshot: integer scale, median of
each cell) with a margin, plus the toolkit's own frames for lofi. Deterministic, numpy only.
"""
import json, pathlib, sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl

TOL = 0.03          # OKLab distance under which two neighbours are the same colour
EDGE = 0.08         # a strong edge, for jaggies
JAG_MIN = 100       # jaggies divides by at least this many runs
LINE_DL = 0.10      # a dark line is this much darker (L) than both sides
RAMP_DL = (0.015, 0.15)   # one ramp step, for stripes
PILLOW_DL = 0.03    # pillow rings: each ring at least PILLOW_DL / 1.5 darker (L) than the one inside

# ---------------------------------------------------------------- input
def _lab(img):
    """PIL image or array -> (H, W, 3) OKLab and an (H, W) opaque mask"""
    if isinstance(img, Image.Image):
        a = np.asarray(img.convert('RGBA'))
    else:
        a = np.asarray(img)
        if a.ndim == 2:
            a = np.repeat(a[..., None], 3, -1)
        if a.dtype != np.uint8:
            a = np.clip(np.round(a * 255 if a.max() <= 1.0 else a), 0, 255).astype(np.uint8)
        if a.shape[-1] == 3:
            a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255, np.uint8)], -1)
    rgb, op = a[..., :3], a[..., 3] >= 128
    key = rgb.reshape(-1, 3).astype(np.uint32) @ np.array([65536, 256, 1], np.uint32)
    u, inv = np.unique(key, return_inverse=True)            # convert each distinct colour once
    ulab = cl.rgb_to_oklab(np.stack([u >> 16, (u >> 8) & 255, u & 255], 1).astype(float))
    return ulab[inv.reshape(rgb.shape[:2])], op

class _Frame:
    """one OKLab conversion and the neighbour tests every metric shares"""
    def __init__(self, img, intent=None):
        self.lab, self.op = _lab(img)
        self.H, self.W = self.op.shape
        self.L = self.lab[..., 0]
        self.intent = np.zeros_like(self.op) if intent is None else _mask(intent, self.op.shape)
        dh = np.linalg.norm(self.lab[:, 1:] - self.lab[:, :-1], axis=-1)
        dv = np.linalg.norm(self.lab[1:] - self.lab[:-1], axis=-1)
        bh, bv = self.op[:, 1:] & self.op[:, :-1], self.op[1:] & self.op[:-1]
        self.dh, self.dv = np.where(bh, dh, np.inf), np.where(bv, dv, np.inf)
        self._lone = None

    def lone(self, tol=TOL):
        """(orphan, pattern): pixels with no 4-neighbour of the same colour, and those of them
        that repeat on both sides at a dither period (2 or 4 px along a row or column, or both
        corners of one diagonal: checkerboard, Bayer dots, dotted rims)"""
        if self._lone is not None and self._lone[0] == tol:
            return self._lone[1:]
        same = np.zeros((self.H, self.W), bool)
        sh, sv = self.dh < tol, self.dv < tol
        same[:, 1:] |= sh; same[:, :-1] |= sh; same[1:] |= sv; same[:-1] |= sv
        orphan = self.op & ~same
        pat = np.zeros_like(orphan)
        P = np.pad(self.lab, ((4, 4), (4, 4), (0, 0)), constant_values=np.nan)
        H, W = self.H, self.W
        for dx, dy in ((2, 0), (0, 2), (4, 0), (0, 4), (1, 1), (1, -1)):
            a = np.linalg.norm(P[4 + dy:4 + dy + H, 4 + dx:4 + dx + W] - self.lab, axis=-1) < tol
            b = np.linalg.norm(P[4 - dy:4 - dy + H, 4 - dx:4 - dx + W] - self.lab, axis=-1) < tol
            pat |= a & b
        self._lone = (tol, orphan, orphan & pat)
        return orphan, orphan & pat

def _mask(m, shape):
    if isinstance(m, Image.Image):
        a = np.asarray(m.convert('RGBA'))
        m = (a[..., 3] >= 128) & (a[..., :3].max(-1) >= 128)
    m = np.asarray(m, bool)
    if m.shape != shape:
        raise ValueError('mask is %s, the frame is %s (masks are at 1x)' % (m.shape, shape))
    return m

def _F(img, intent=None):
    return img if isinstance(img, _Frame) else _Frame(img, intent)

# ---------------------------------------------------------------- connected parts
def _components(op, join_h, join_v):
    """label pixels of op joined by join_h (H, W-1) and join_v (H-1, W): (labels, n), -1 outside.
    Rows are cut into runs, runs joined across rows by vectorised hook-and-compress rounds."""
    H, W = op.shape
    start = op.copy()
    start[:, 1:] &= ~join_h
    run = (np.cumsum(start.ravel()) - 1).reshape(H, W)
    nr = int(start.sum())
    lab = np.full((H, W), -1, np.int64)
    if nr == 0:
        return lab, 0
    a, b = run[:-1][join_v], run[1:][join_v]
    parent = np.arange(nr)
    if len(a):
        key = np.unique(a * nr + b)
        a, b = key // nr, key % nr
        while len(a):
            ra, rb = parent[a], parent[b]
            live = ra != rb
            if not live.any():
                break
            a, b, ra, rb = a[live], b[live], ra[live], rb[live]
            np.minimum.at(parent, np.maximum(ra, rb), np.minimum(ra, rb))
            while True:
                pp = parent[parent]
                if np.array_equal(pp, parent):
                    break
                parent = pp
    _, ranked = np.unique(parent, return_inverse=True)
    lab[op] = ranked.ravel()[run[op]]
    return lab, int(ranked.max()) + 1

# ---------------------------------------------------------------- metrics
def orphans(img, intent=None, tol=TOL):
    """share of opaque pixels (outside `intent`) with no 4-neighbour of the same colour and no
    dither period to belong to (F.lone)"""
    F = _F(img, intent)
    orphan, pattern = F.lone(tol)
    pool = F.op & ~F.intent
    return float((pool & orphan & ~pattern).sum() / max(1, pool.sum()))

def clusters(img, intent=None, tol=TOL):
    """{'cluster_px': median over colours of the mean cluster size, 'small_clusters': share of
    clusters under 3 px}; clusters are 4-connected runs of the same colour, those wholly in
    `intent` or dither (F.lone) left out. A colour is the OKLab cell (0.05 wide) of a cluster's first pixel."""
    F = _F(img, intent)
    lab, n = _components(F.op, F.dh < tol, F.dv < tol)
    if n == 0:
        return {'cluster_px': float('nan'), 'small_clusters': float('nan')}
    ids = lab[F.op]
    size = np.bincount(ids, minlength=n)
    skip = F.intent | F.lone(tol)[1]
    inint = np.bincount(ids, weights=skip[F.op].astype(float), minlength=n)
    keep = inint < size
    _, first = np.unique(lab.ravel(), return_index=True)
    first = first[1:] if lab.ravel()[first[0]] < 0 else first
    q = np.round(F.lab.reshape(-1, 3)[first] / 0.05).astype(np.int64)
    colour = np.unique(q, axis=0, return_inverse=True)[1].ravel()
    k = keep
    nc = int(colour.max()) + 1
    cnt = np.bincount(colour[k], minlength=nc)
    px = np.bincount(colour[k], weights=size[k].astype(float), minlength=nc)
    per = px[cnt > 0] / cnt[cnt > 0]
    return {'cluster_px': float(np.median(per)) if len(per) else float('nan'),
            'small_clusters': float((size[k] < 3).mean()) if k.any() else 0.0}

def _runs_1d(e):
    """(row, start, end) of the True runs of a 2-D bool array, row by row"""
    p = np.pad(e, ((0, 0), (1, 1)))
    d = np.diff(p.astype(np.int8), axis=1)
    r0, s = np.nonzero(d == 1)
    r1, t = np.nonzero(d == -1)
    return r0, s, t - 1

def _jag_counts(d_across):
    """breaks and judged runs of the staircases in one orientation. d_across[y, x] is the colour
    distance between (x, y) and (x, y + 1): a horizontal edge segment when >= EDGE"""
    rows, s, e = _runs_1d(d_across >= EDGE)
    if len(rows) < 3:
        return 0, 0
    W = d_across.shape[1] + 2
    idx = {int(r) * W + int(a): i for i, (r, a) in enumerate(zip(rows, s))}
    length = e - s + 1
    breaks = judged = 0
    for dy in (1, -1):                                    # stairs going down-right, then up-right
        nxt = np.array([idx.get(int(r + dy) * W + int(b + 1), -1) for r, b in zip(rows, e)])
        has_prev = np.zeros(len(rows), bool)
        has_prev[nxt[nxt >= 0]] = True
        for i0 in np.nonzero(~has_prev & (nxt >= 0))[0]:
            seq, i = [], i0
            while i >= 0 and len(seq) < 10000:
                seq.append(int(length[i])); i = nxt[i]
            for k in range(1, len(seq) - 1):
                a, b, c = seq[k - 1], seq[k], seq[k + 1]
                judged += 1
                if (b > a and b > c) or (b < a and b < c):
                    even = a == c and abs(b - a) == 1 and (
                        (k >= 2 and seq[k - 2] == b) or (k + 2 < len(seq) and seq[k + 2] == b))
                    breaks += not even
    return breaks, judged

def jaggies(img):
    """share of inner staircase runs along strong edges that break the line's rhythm (counted
    over at least JAG_MIN runs, so a frame with a few staircases is not judged on a handful)"""
    F = _F(img)
    b1, j1 = _jag_counts(F.dv)                       # near-horizontal edges
    b2, j2 = _jag_counts(F.dh.T)                     # near-vertical edges
    return float((b1 + b2) / max(JAG_MIN, j1 + j2))

def _stripe_mark(lab, op, dnext):
    """pixels in stripe runs down each column of lab (H, W, 3); dnext (H-1, W) = distance to the
    pixel below"""
    H, W = op.shape
    mark = np.zeros((H, W), bool)
    for x in range(W):
        cut = np.nonzero(~(dnext[:, x] < TOL))[0] + 1
        starts = np.concatenate([[0], cut]); ends = np.concatenate([cut, [H]])
        if len(starts) < 3:
            continue
        w = ends - starts
        L = lab[starts, x, 0]
        okp = op[starts, x]
        dL = np.diff(L)
        dE = np.linalg.norm(np.diff(lab[starts, x], axis=0), axis=-1)
        step = (np.abs(dL) > RAMP_DL[0]) & (np.abs(dL) < RAMP_DL[1]) & (dE < RAMP_DL[1]) & okp[1:] & okp[:-1]
        sgn = np.sign(dL)
        k = 0
        n = len(starts)
        while k < n - 2:
            j = k
            while (j + 1 < n and step[j] and w[j] >= 2 and w[j + 1] >= 2
                   and abs(int(w[j + 1]) - int(w[k])) <= (1 if w[k] >= 4 else 0)
                   and (j == k or sgn[j] == sgn[k])):
                j += 1
            if j - k + 1 >= 3:
                mark[starts[k]:ends[j], x] = True
                k = j
            else:
                k += 1
    core = mark.copy()                                  # parallel: 3+ columns side by side
    core[:, 1:] &= mark[:, :-1]; core[:, :-1] &= mark[:, 1:]
    core[:, 0] = core[:, -1] = False
    out = core.copy()
    out[:, 1:] |= core[:, :-1]; out[:, :-1] |= core[:, 1:]
    return out & mark

def stripes(img):
    """share of pixels in parallel same-width bands of adjacent ramp steps (columns and rows)"""
    F = _F(img)
    m = _stripe_mark(F.lab, F.op, F.dv)
    m |= _stripe_mark(F.lab.transpose(1, 0, 2), F.op.T, F.dh.T).T
    return float((m & F.op).sum() / max(1, F.op.sum()))

def doubled(img):
    """share of thin dark-line pixels that are two different dark colours side by side"""
    F = _F(img)
    line = np.zeros((F.H, F.W), bool); dbl = np.zeros_like(line)
    for L, d, T in ((F.L, F.dh, False), (F.L.T, F.dv.T, True)):
        a, m, b = L[:, :-2], L[:, 1:-1], L[:, 2:]
        one = (a - m >= LINE_DL) & (b - m >= LINE_DL)
        a2, m1, m2, b2 = L[:, :-3], L[:, 1:-2], L[:, 2:-1], L[:, 3:]
        two = ((a2 - m1 >= LINE_DL) & (a2 - m2 >= LINE_DL) & (b2 - m1 >= LINE_DL) & (b2 - m2 >= LINE_DL))
        diff = two & (d[:, 1:-1] >= TOL) & (np.abs(m1 - m2) < LINE_DL)
        ln = np.zeros(L.shape, bool); db = np.zeros(L.shape, bool)
        ln[:, 1:-1] |= one
        ln[:, 1:-2] |= two; ln[:, 2:-1] |= two
        db[:, 1:-2] |= diff; db[:, 2:-1] |= diff
        line |= ln.T if T else ln
        dbl |= db.T if T else db
    line &= F.op
    return float((dbl & line).sum() / line.sum()) if line.any() else 0.0

def _objects(F, objects):
    """one bool mask of every object pixel, or None for the whole frame"""
    if objects is None:
        return None
    if isinstance(objects, dict):
        objects = list(objects.values())
    if isinstance(objects, np.ndarray) and objects.ndim == 2:
        return objects > 0 if objects.dtype != bool else objects
    m = np.zeros(F.op.shape, bool)
    for o in objects:
        m |= _mask(o, F.op.shape)
    return m

def pillow(img, objects=None, tol=TOL):
    """share of the frame (or of the `objects` masks) shaded in concentric rings: a core cluster
    of 4+ px wholly ringed by one darker cluster, itself wholly ringed by a darker one again (3+
    levels, each PILLOW_DL / 1.5 darker going out). One light direction breaks the rings: the lit
    side of the core touches the outline, so nothing is enclosed."""
    F = _F(img)
    lab, n = _components(F.op, F.dh < tol, F.dv < tol)
    if n == 0:
        return 0.0
    ids = lab[F.op]
    size = np.bincount(ids, minlength=n)
    Lm = np.bincount(ids, weights=F.L[F.op], minlength=n) / np.maximum(1, size)
    touch = np.zeros(n, bool)                       # on the frame edge or next to transparency
    edge = ~F.op
    near = np.zeros_like(edge)
    near[:, 1:] |= edge[:, :-1]; near[:, :-1] |= edge[:, 1:]; near[1:] |= edge[:-1]; near[:-1] |= edge[1:]
    near[0] = near[-1] = True; near[:, 0] = near[:, -1] = True
    touch[np.unique(lab[near & F.op])] = True
    a = np.concatenate([lab[:, 1:].ravel(), lab[1:].ravel()])
    b = np.concatenate([lab[:, :-1].ravel(), lab[:-1].ravel()])
    k = (a != b) & (a >= 0) & (b >= 0)
    pr = np.unique(np.concatenate([np.stack([a[k], b[k]], 1), np.stack([b[k], a[k]], 1)]), axis=0)
    nb = [[] for _ in range(n)]
    for x, y in pr.tolist():
        nb[x].append(y)
    by = np.full(n, -1)                             # by[A] = the one cluster that rings A
    for A in range(n):
        if not touch[A] and len(nb[A]) == 1:
            by[A] = nb[A][0]
    for _ in range(8):                              # rings around rings: ignore what is inside
        changed = False
        for A in np.nonzero((by < 0) & ~touch)[0]:
            outer = []
            for C in nb[A]:
                c, steps = C, 0
                while by[c] >= 0 and by[c] != A and steps < 64:
                    c = by[c]; steps += 1
                if by[c] != A:
                    outer.append(C)
                    if len(outer) > 1:
                        break
            if len(outer) == 1:
                by[A] = outer[0]; changed = True
        if not changed:
            break
    hit = np.zeros(n, bool)
    step = PILLOW_DL / 1.5
    for A in np.nonzero((by >= 0) & (size >= 4))[0]:
        chain = [A]
        while by[chain[-1]] >= 0 and len(chain) < 32 and Lm[by[chain[-1]]] <= Lm[chain[-1]] - step:
            chain.append(by[chain[-1]])
        if len(chain) >= 3:
            hit[chain] = True
    obj = _objects(F, objects)
    pool = F.op if obj is None else (F.op & obj)
    return float((hit[lab[pool]]).sum() / max(1, pool.sum()))

METRICS = ('orphans', 'jaggies', 'stripes', 'doubled', 'pillow', 'cluster_px', 'small_clusters')

def measure(img_1x, intent=None, objects=None):
    """every metric of a native 1x frame (PIL image or array): {name: value}"""
    F = _F(img_1x, intent)
    out = {'orphans': orphans(F), 'jaggies': jaggies(F), 'stripes': stripes(F), 'doubled': doubled(F),
           'pillow': pillow(F, objects)}
    out.update(clusters(F))
    return out

# ---------------------------------------------------------------- limits per style
# Measured on each reference's native frame (the study's integer scale, cell phase by least in-cell
# variance, median of each cell's inner pixels; 09 sampled at 4.5x cell centres) and, for lofi, the
# worst of 13 Lantern Isle frames across its seasons. The source numbers are in the comment, in the
# order orphans / jaggies / stripes / doubled / pillow / cluster_px / small_clusters. Margins:
# orphans 1.5x + 0.01, jaggies + 0.10, stripes max(0.01, 3x), doubled 1.5x + 0.08, pillow 0.01
# (every reference measures 0; 0.02 for Stardew's pillow-cut stones), cluster_px at least half,
# small_clusters + 0.08. JPEG noise and 05's smooth-upscale blur inflate the reference orphans.
# Rose Squall (examples/indie, pastel-cell) measures .007 .255 .006 .106 0 6.0 .496 and passes.
def _lim(o, j, s, d, p, c, sm):
    return {'orphans': (None, o), 'jaggies': (None, j), 'stripes': (None, s), 'doubled': (None, d),
            'pillow': (None, p), 'cluster_px': (c, None), 'small_clusters': (None, sm)}

CRAFT = {
    'contre-jour':   _lim(0.033, 0.344, 0.01, 0.228, 0.01, 1.33, 0.856),   # 01: .015 .244 .000 .099 0 2.7 .776
    'pastel-cell':   _lim(0.018, 0.334, 0.01, 0.136, 0.01, 2.6, 0.525),    # 02: .005 .234 .000 .037 0 5.2 .445
    'native-glow':   _lim(0.019, 0.212, 0.01, 0.184, 0.01, 4.05, 0.552),   # 03: .006 .112 .000 .069 0 8.1 .472
    'hd-overworld':  _lim(0.11, 0.359, 0.01, 0.303, 0.01, 1.21, 0.782),    # 04: .067 .259 .000 .149 0 2.4 .702
    'arcade':        _lim(0.198, 0.494, 0.01, 0.615, 0.01, 0.81, 0.914),   # 05: .125 .394 .000 .357 0 1.6 .834
    'tactics':       _lim(0.034, 0.292, 0.016, 0.208, 0.01, 1.0, 0.766),   # 06: .016 .192 .005 .085 0 2.0 .686
    'sticker-iso':   _lim(0.119, 0.341, 0.01, 0.08, 0.01, 3.39, 0.927),    # 07: .073 .241 .000 .000 0 6.8 .847
    'illustrated':   _lim(0.067, 0.402, 0.01, 0.183, 0.01, 2.55, 0.628),   # 08: .038 .302 .000 .069 0 5.1 .548
    'neon-noir':     _lim(0.055, 0.422, 0.01, 0.388, 0.01, 1.18, 0.661),   # 09: .030 .322 .000 .206 0 2.4 .581
    'cosy-lightmap': _lim(0.12, 0.34, 0.01, 0.391, 0.02, 1.0, 0.822),      # 10: .073 .240 .000 .207 0 2.0 .742
    'lofi':          _lim(0.051, 0.398, 0.01, 0.266, 0.01, 1.91, 0.773),   # Lantern Isle: .027 .298 .001 .124 0 3.8 .693
}

def report(img_1x, style, intent=None, objects=None, values=None):
    """[(metric, value, lo, hi, 'ok'|'fail')] against CRAFT[style] (a name or {metric: (lo, hi)})"""
    if isinstance(style, str):
        import styles
        rules = CRAFT[styles.get(style)['name']]
    else:
        rules = dict(style)
    v = values or measure(img_1x, intent, objects)
    rows = []
    for k, (lo, hi) in rules.items():
        x = v[k]
        bad = x != x or (lo is not None and x < lo) or (hi is not None and x > hi)
        rows.append((k, x, lo, hi, 'fail' if bad else 'ok'))
    return rows

def check(img_1x, style, intent=None, objects=None):
    """the craft limits a frame breaks, as readable lines ([] = clean)"""
    out = []
    for k, x, lo, hi, st in report(img_1x, style, intent, objects):
        if st == 'fail':
            want = ('between %s and %s' % (fmt(k, lo), fmt(k, hi)) if lo is not None and hi is not None else
                    'at least %s' % fmt(k, lo) if lo is not None else 'at most %s' % fmt(k, hi))
            out.append('%s is %s, the limit is %s' % (k, fmt(k, x), want))
    return out

def fmt(k, v):
    if v is None or v != v:
        return '-'
    return '%.1f px' % v if k == 'cluster_px' else '%.2f%%' % (100 * v)

# ---------------------------------------------------------------- cli
def main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return 1
    scale, style, intent = int(opt('--scale', '1')), opt('--style'), opt('--intent')
    as_json = '--json' in a
    if as_json: a.remove('--json')
    img = Image.open(a[0])
    if scale > 1:
        import stats
        img = stats.to_native(img, scale)
    v = measure(img, Image.open(intent) if intent else None)
    if as_json:
        print(json.dumps(v, indent=1)); return 0
    rows = report(img, style, values=v) if style else [(k, v[k], None, None, '') for k in METRICS]
    bad = False
    for k, x, lo, hi, st in rows:
        bad |= st == 'fail'
        print('%-4s %-15s %-9s %s' % (st, k, fmt(k, x), '' if not style else '[%s .. %s]' % (
            fmt(k, lo) if lo is not None else '', fmt(k, hi) if hi is not None else '')))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
