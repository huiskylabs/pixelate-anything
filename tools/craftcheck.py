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

Composition, focus and repeat (what the gate's composition, focus and repeat lines read; see their
sections below): emptiness, banding, silhouettes (blocky, slab), focus (does the hero own the peak
value, contrast and chroma, and does any mass outside it outweigh it), repeats (rows of near-identical
lobes or units), and the block-in helpers value_bands, band_map, blockin_empty.

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
# Rose Squall (library/rose-squall, pastel-cell) measures .007 .255 .006 .106 0 6.0 .496 and passes.
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

# ---------------------------------------------------------------- composition
# What an art director sees at thumbnail size, as numbers: a frame with nothing in half of it, a
# mass drawn as a brick or a slab, light quantised into rings. Each metric is measured on the
# native 1x frame and held to COMPOSITION limits per style; None means the style has no limit yet
# (no failing draft to calibrate it on). See COMPOSITION below for the numbers they came from.
CELLS = 32          # composition grid: the frame cut into CELLS columns of square cells
DEPART = 0.12       # a cell has something in it when DEPART_SHARE of its pixels sit this far (OKLab)
DEPART_SHARE = 0.03 # from the cell's own median colour (texture on flat ground stays under it)
BAND_DE = (0.006, 0.035)   # one light step of a quantised light layer (a palette step is larger)
SEG_K = 5           # colour regions for the silhouette metrics

def _cells(F):
    c = max(2, int(round(F.W / CELLS)))
    gh, gw = F.H // c, F.W // c
    lab = F.lab[:gh * c, :gw * c].reshape(gh, c, gw, c, 3).transpose(0, 2, 1, 3, 4).reshape(gh, gw, c * c, 3)
    far = np.linalg.norm(lab - np.median(lab, axis=2, keepdims=True), axis=-1) > DEPART
    return far.mean(-1) >= DEPART_SHARE, c

def emptiness(img):
    """{'empty': share of the frame's cells with nothing in them, 'empty_low': the same share in the
    bottom third}. A cell has something in it when a few of its pixels depart strongly from its own
    ground colour: a figure, a prop, a lit edge. Even texture (snow, paving, planks) does not count."""
    F = _F(img)
    busy, _ = _cells(F)
    gh = busy.shape[0]
    return {'empty': float(1 - busy.mean()), 'empty_low': float(1 - busy[gh - gh // 3:].mean())}

def banding(img):
    """(share, ratio): the share of the frame on curved light-step contours (two flat plateaus a
    small lightness step apart, the contour turning both ways), and their share of all small steps
    (a smooth light gradient is made of steps under BAND_DE[0], a quantised one is not)"""
    F = _F(img)
    lo, hi = BAND_DE
    H, W = F.H, F.W
    sh = np.zeros((H, W), bool); sv = np.zeros((H, W), bool)
    for ax in (0, 1):
        L = F.lab if ax == 0 else F.lab.transpose(1, 0, 2)
        d = np.linalg.norm(L[1:] - L[:-1], axis=-1)
        st = (d > lo) & (d < hi) & (np.abs(L[1:, :, 0] - L[:-1, :, 0]) > 0.6 * d)
        fa = np.zeros_like(st); fb = np.zeros_like(st)
        fa[1:] = d[:-1] < 0.003; fb[:-1] = d[1:] < 0.003
        m = np.zeros(L.shape[:2], bool); m[1:] = st & fa & fb
        if ax == 0:
            sv |= m
        else:
            sh |= m.T
    step = sh | sv
    lab, n = _components(step, step[:, 1:] & step[:, :-1], step[1:] & step[:-1])
    if n == 0:
        return 0.0, 0.0
    l = lab[step]
    size = np.bincount(l, minlength=n)
    nh = np.bincount(lab[sh], minlength=n); nv = np.bincount(lab[sv], minlength=n)
    ys, xs = np.nonzero(step)
    y0 = np.full(n, H); y1 = np.zeros(n, int); x0 = np.full(n, W); x1 = np.zeros(n, int)
    np.minimum.at(y0, l, ys); np.maximum.at(y1, l, ys); np.minimum.at(x0, l, xs); np.maximum.at(x1, l, xs)
    curved = ((np.minimum(nh, nv) >= 0.3 * np.maximum(nh, nv)) & (y1 - y0 >= 5) & (x1 - x0 >= 5) & (size >= 12))
    cpx = int(size[curved].sum())
    tiny = sum(int(((d > 1e-6) & (d < lo)).sum()) for d in (F.dh[np.isfinite(F.dh)], F.dv[np.isfinite(F.dv)]))
    return float(cpx / (H * W)), float(cpx / max(1, cpx + tiny / 2))

def _box(a, r):
    k = 2 * r + 1
    p = np.pad(a, ((r, r), (r, r), (0, 0)), mode='edge')
    c = np.cumsum(np.cumsum(np.pad(p, ((1, 0), (1, 0), (0, 0))), 0), 1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)

def _regions(F):
    """the frame as SEG_K colour regions (k-means on a lightly blurred OKLab frame): masses, sky, ground"""
    sm = _box(F.lab, max(1, F.W // 160)).reshape(-1, 3)
    C = cl.kmeans(sm, SEG_K, seed=3)
    return cl.nearest(sm, C).reshape(F.H, F.W)

def _runs(b):
    p = np.pad(b, ((0, 0), (1, 1)))
    d = np.diff(p.astype(np.int8), axis=1)
    r, s = np.nonzero(d == 1)
    _, t = np.nonzero(d == -1)
    return r, s, t - s

def silhouettes(img, seg=None):
    """{'blocky': (score, (x, y, w, h)), 'slab': (share, where)}.
    blocky: for each colour region of at least 0.8% of the frame that floats free of the frame edge,
    holes filled, (area / bounding box) x (share of its outline on straight runs of 20%+ of its side);
    the worst one. A brick-shaped island scores near 0.2, a tapering rock under 0.05.
    slab: the longest straight horizontal or vertical boundary between two colour regions that does
    not run off the frame (a horizon does), as a share of the frame width or height."""
    F = _F(img)
    seg = _regions(F) if seg is None else seg
    H, W = F.H, F.W
    best = (0.0, None)
    for j in range(int(seg.max()) + 1):
        m0 = seg == j
        lab, n = _components(m0, m0[:, 1:] & m0[:, :-1], m0[1:] & m0[:-1])
        if n == 0:
            continue
        size = np.bincount(lab[lab >= 0], minlength=n)
        for i in np.nonzero(size >= 0.008 * H * W)[0]:
            ys, xs = np.nonzero(lab == i)
            y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
            if y0 == 0 or x0 == 0 or y1 == H - 1 or x1 == W - 1:
                continue
            m = lab[y0:y1 + 1, x0:x1 + 1] == i
            hl, hn = _components(~m, (~m)[:, 1:] & (~m)[:, :-1], (~m)[1:] & (~m)[:-1])
            if hn:
                rim = np.unique(np.concatenate([hl[0], hl[-1], hl[:, 0], hl[:, -1]]))
                m = m | ((hl >= 0) & ~np.isin(hl, rim))
            bw, bh = x1 - x0 + 1, y1 - y0 + 1
            p = np.pad(m, 1)
            mid = p[1:-1, 1:-1]
            hr = np.concatenate([_runs(mid & ~p[:-2, 1:-1])[2], _runs(mid & ~p[2:, 1:-1])[2]])
            vr = np.concatenate([_runs((mid & ~p[1:-1, :-2]).T)[2], _runs((mid & ~p[1:-1, 2:]).T)[2]])
            straight = (hr[hr >= max(6, 0.2 * bw)].sum() + vr[vr >= max(6, 0.2 * bh)].sum()) / max(1, hr.sum() + vr.sum())
            score = float(m.sum() / (bw * bh) * straight)
            if score > best[0]:
                best = (score, (int(x0), int(y0), int(bw), int(bh)))
    slab = (0.0, None)
    for horiz in (True, False):
        b = (seg[1:] != seg[:-1]) if horiz else (seg[:, 1:] != seg[:, :-1]).T
        span = W if horiz else H
        r, s, L = _runs(b)
        inner = (s > 0) & (s + L < span)
        if inner.any():
            k = np.argmax(np.where(inner, L, 0))
            if L[k] / span > slab[0]:
                slab = (float(L[k] / span), ('row %d, x %d..%d' if horiz else 'column %d, y %d..%d') % (r[k] + 1, s[k], s[k] + L[k] - 1))
    return {'blocky': best, 'slab': slab}

COMP_METRICS = ('empty', 'empty_low', 'blocky', 'slab', 'banding')

def _comp(empty=None, empty_low=0.88, blocky=None, slab=None, banding=None):
    return {'empty': (None, empty), 'empty_low': (None, empty_low), 'blocky': (None, blocky),
            'slab': (None, slab), 'banding': (None, banding)}

# Limits per style, from the five showcase stills (finals graded B to B+ pass; drafts with a half-empty
# street, bare paving, a brick island, a slab mountain or ringed light fail), Lantern Isle, Rose Squall
# and the nine reference natives of the style study. Measured (final / draft / worst reference):
#   empty_low  (bottom third with nothing in it) worst final 0.80 (observatory), ref 0.82 (contre-jour),
#              half-empty street draft 0.93 -> 0.88 for every style
#   empty      sticker-iso: canal final 0.18, ref 0.10, bare-paving draft 0.41 -> 0.30
#   blocky     pastel-cell: kite 0.03, Rose Squall 0.05, ref 0.03, brick island 0.18 -> 0.12;
#              contre-jour: observatory 0.04, ref 0.14 -> 0.20 (architecture styles stay off: a
#              shop front or a UI panel is a rectangle on purpose)
#   slab       contre-jour: observatory 0.14, ref 0.12, slab mountain 0.43 -> 0.25; pastel-cell:
#              kite 0.11, Rose Squall 0.14, ref 0.17 -> 0.25 (lofi is off: Lantern Isle's quay is 0.33)
#   banding    the screen-light styles only (contre-jour, cosy-lightmap): stepped contours over 0.20%
#              of the frame AND over 20% of the small light steps; noodle shop final 0.34% / 2%,
#              levels=24 draft 0.63% / 53% -> 0.0020 (a native light layer is stepped by design)
COMPOSITION = {
    'contre-jour':   _comp(blocky=0.20, slab=0.25, banding=0.002),
    'pastel-cell':   _comp(blocky=0.12, slab=0.25),
    'native-glow':   _comp(),
    'hd-overworld':  _comp(),
    'arcade':        _comp(),
    'tactics':       _comp(),
    'sticker-iso':   _comp(empty=0.30),
    'illustrated':   _comp(),
    'neon-noir':     _comp(),
    'cosy-lightmap': _comp(banding=0.002),
    'lofi':          _comp(),
}
BAND_RATIO = 0.20   # banding counts only when stepped contours are this share of the small light steps

def composition(img_1x, rules):
    """{metric: (value, detail)} for the metrics `rules` bounds (unbounded ones are not measured)"""
    F = _F(img_1x)
    live = {k for k, (lo, hi) in rules.items() if lo is not None or hi is not None}
    out = {}
    if live & {'empty', 'empty_low'}:
        e = emptiness(F)
        out['empty'] = (e['empty'], None); out['empty_low'] = (e['empty_low'], None)
    if live & {'blocky', 'slab'}:
        s = silhouettes(F)
        out['blocky'] = s['blocky']; out['slab'] = s['slab']
    if 'banding' in live:
        share, ratio = banding(F)
        out['banding'] = (share if ratio >= BAND_RATIO else 0.0, (share, ratio))
    return out

def comp_advice(key, v, detail, hi):
    """the plain-words line for a failing composition metric: what is wrong and what to do"""
    if key == 'empty':
        return ('%.0f%% of the frame has nothing in it (bare ground, water or sky with no object); fill it '
                'with the scene\'s props and people, move the subject into it, or crop' % (100 * v))
    if key == 'empty_low':
        return ('%.0f%% of the bottom third has nothing in it; bring the subject or a foreground down into '
                'it, or crop the bottom' % (100 * v))
    if key == 'blocky':
        x, y, w, h = detail
        return ('the mass at x %d, y %d (%dx%d px at 1x) reads as a brick: its outline is mostly long '
                'straight runs; break it with ledges, overhangs and a tapering underside' % (x, y, w, h))
    if key == 'slab':
        return ('a straight edge runs %.0f%% across the frame (%s): the mass reads as a flat slab; '
                'break the line with peaks, ledges or steps' % (100 * v, detail))
    if key == 'banding':
        share, ratio = detail
        return ('%.2f%% of the frame sits on stepped light rings (%.0f%% of the light steps are bands, not '
                'gradient); give the light more levels or none (levels=None)' % (100 * share, 100 * ratio))
    return '%s is %s, the limit is %s' % (key, comp_fmt(key, v), comp_fmt(key, hi))

def comp_fmt(key, v):
    if v is None or v != v:
        return '-'
    return '%.2f' % v if key == 'blocky' else '%.2f%%' % (100 * v)

# ---------------------------------------------------------------- focus: one hero, instantly
# Read at thumbnail size (the frame box-averaged to about FOCUS_THUMB cells across, so stars, dither
# and flecks melt into their ground the way they do at 320 px). The hero is a bbox at 1x (the brief's
# `- Hero:` line, or the --actor mask's bbox); `owners` are bboxes of named light sources that may
# carry the peak instead (`peak value: the sun disc (244,6,268,32)`).
FOCUS_THUMB = 160   # thumbnail width in cells
FOCUS_TOP = 0.005   # the frame's peak: its top 0.5% of cells by value and by local contrast
FOCUS_MASS_DE = 0.12   # a figure cell departs this far (OKLab) from its neighbourhood (1/8 frame wide)
FOCUS_HUE = 35.0    # chroma rivals: same hue family as the hero's most saturated cell, within this
# Limits, from the ten showcase stills (art director's hero score: kite 2 and 3, canal 3 and 3 fail;
# observatory 4 and 4, noodle 4 and 4, lighthouse 3 and 4, Lantern Isle pass). Measured pass / fail:
#   focus_value     share of the top values in the hero (or a named light): pass .83-1.00, kite r1 .22,
#                   canal 0 and 0 -> at least 0.50
#   focus_contrast  the same for local contrast: pass .59-1.00, canal 0 and 0 -> at least 0.50
#   focus_chroma    same-hue cells outside the hero at least as saturated as the hero's top 5%, as a
#                   multiple of those: pass .00-.92 (Lantern Isle 1.52 with its tightest cottage bbox),
#                   canal 11 and 24 -> at most 2.5
#   focus_rival     the loudest figure mass outside the hero, as a multiple of the hero's own (area x
#                   departure): pass .04-.22, kite 1.81 and 1.34 (island and blossom), canal 50-80 (the
#                   whole busy frame is one mass) -> at most 0.6 (the art director's own cap)
#   focus_size      the drawn hero (--actor bbox) over the brief's planned bbox: at least 0.85
# The lighthouse round 1 (hero 3: the boat is a speck) passes: a bbox cannot tell a readable hero from
# a speck inside it; the art director still judges that.
FOCUS = {'focus_value': (0.50, None), 'focus_contrast': (0.50, None), 'focus_chroma': (None, 2.5),
         'focus_rival': (None, 0.6), 'focus_size': (0.85, None)}

def _thumb(F, cells=FOCUS_THUMB):
    c = max(1, int(round(F.W / cells)))
    h, w = F.H // c, F.W // c
    return F.lab[:h * c, :w * c].reshape(h, c, w, c, 3).mean((1, 3)), c

def _boxmask(shape, c, boxes):
    m = np.zeros(shape, bool)
    for x0, y0, x1, y1 in boxes:
        m[max(0, y0 // c):max(0, y1 // c + 1), max(0, x0 // c):max(0, x1 // c + 1)] = True
    return m

def focus(img, hero, value_owners=(), chroma_owners=(), chroma=True):
    """{key: (value, detail)} for the FOCUS keys but focus_size. hero: (x0, y0, x1, y1) at 1x,
    inclusive; value_owners / chroma_owners: bboxes of named lights or objects that may hold the value
    or chroma peak outside the hero. chroma=False skips focus_chroma (an era palette, a greyscale
    block-in)."""
    F = _F(img)
    t, c = _thumb(F)
    h, w = t.shape[:2]
    L = t[..., 0]
    C = np.hypot(t[..., 1], t[..., 2])
    hue = np.degrees(np.arctan2(t[..., 2], t[..., 1]))
    hm = _boxmask((h, w), c, [hero])
    vo = _boxmask((h, w), c, value_owners) & ~hm
    co = _boxmask((h, w), c, chroma_owners) & ~hm
    out = {}
    k = max(3, int(round(FOCUS_TOP * L.size)))
    def peak(v, own):
        idx = np.argsort(v.ravel(), kind='stable')[::-1][:k]
        o = own.ravel()[idx]
        ys, xs = np.unravel_index(idx[~o], v.shape)
        where = (int(np.median(xs)) * c, int(np.median(ys)) * c) if len(xs) else None
        return float(o.mean()), where
    out['focus_value'] = peak(L, hm | vo)
    con = np.abs(L - _box(L[..., None], max(2, w // 16))[..., 0])
    out['focus_contrast'] = peak(con, hm | vo)
    if chroma:
        n = max(2, int(round(0.05 * hm.sum())))
        top = np.sort(C[hm])[::-1][:n]
        lev = top[-1]
        hh = hue.ravel()[np.argmax(np.where(hm, C, -1).ravel())]
        dh = np.abs((hue - hh + 180) % 360 - 180)
        riv = (C >= lev) & (dh < FOCUS_HUE) & ~hm & ~co & (lev > 0.02)
        ys, xs = np.nonzero(riv)
        out['focus_chroma'] = (float(riv.sum() / n), (int(np.median(xs)) * c, int(np.median(ys)) * c) if len(xs) else None)
    d = np.linalg.norm(t - _box(t, max(2, w // 8)), axis=-1)
    fg = d > FOCUS_MASS_DE
    lab, nc = _components(fg, fg[:, 1:] & fg[:, :-1], fg[1:] & fg[:-1])
    herol = float(d[fg & hm].sum())
    best = (0.0, None)
    if nc:
        ids = lab[fg]
        size = np.bincount(ids, minlength=nc)
        inh = np.bincount(ids, weights=hm[fg].astype(float), minlength=nc)
        inown = np.bincount(ids, weights=(vo | co)[fg].astype(float), minlength=nc)
        loud = np.bincount(ids, weights=d[fg], minlength=nc)
        cand = (inh < 0.25 * size) & (inown < 0.5 * size)
        if cand.any():
            i = int(np.argmax(np.where(cand, loud, -1)))
            ys, xs = np.nonzero(lab == i)
            best = (float(loud[i] / max(herol, 1e-9)) if herol > 0 else float('inf'),
                    (int(xs.min()) * c, int(ys.min()) * c, int(xs.max() + 1) * c - 1, int(ys.max() + 1) * c - 1))
    out['focus_rival'] = best
    return out

def focus_advice(key, v, detail, hero):
    """the plain-words line for a failing focus key"""
    x0, y0, x1, y1 = hero
    if key == 'focus_value':
        at = ' (most of them near x %d, y %d)' % detail if detail else ''
        return ('only %.0f%% of the brightest values sit on the hero (x %d-%d, y %d-%d); the peak is elsewhere%s. '
                'Give the hero the frame\'s top value (a rim, a lit face, a window) and take one step off the '
                'brightest thing outside it, or name that light in the brief: `peak value: NAME (x0,y0,x1,y1)`'
                % (100 * v, x0, x1, y0, y1, at))
    if key == 'focus_contrast':
        at = ' (most of it near x %d, y %d)' % detail if detail else ''
        return ('only %.0f%% of the frame\'s strongest light-dark contrast is on the hero%s; put the darkest '
                'dark against the lightest light at the hero and quiet the edges elsewhere' % (100 * v, at))
    if key == 'focus_chroma':
        at = ' near x %d, y %d' % detail if detail else ''
        return ('the hero\'s own colour is louder elsewhere: %.1fx as many cells of the same hue, at least as '
                'saturated, sit outside it%s. Drop those one chroma step, or keep the hue for the hero alone'
                % (v, at))
    if key == 'focus_rival':
        if detail is None:
            return 'a mass outside the hero outweighs it'
        a, b, c2, d2 = detail
        return ('a mass at x %d-%d, y %d-%d outweighs the hero %.2fx (size times contrast): the eye goes there '
                'first. Shrink it, haze it a value step toward its ground, or cut its edges, so nothing outside '
                'the hero weighs over 0.6x of it' % (a, c2, b, d2, v))
    if key == 'focus_size':
        return ('the drawn hero is only %.0f%% of its planned bbox; draw it at the planned size' % (100 * v))
    return '%s is %.2f' % (key, v)

# ---------------------------------------------------------------- repeat: rows of near-identical units
# The procedural tell: a row of equal-size lobes (cloud scallops, heather domes, gumdrop waves) or of
# the same unit stamped along a line (identical houses). Two detectors, at 1x:
#   lobes  the top and bottom silhouettes of each colour region (the k-means regions of silhouettes(),
#          so dither and texture melt), cut at their cusps; REPEAT_N lobes in a row whose widths have a
#          spread (std / mean) under REPEAT_CV, each at least REPEAT_LOBE of the frame wide and
#          REPEAT_DEPTH of its width deep
#   units  flat-colour shapes of at least REPEAT_AREA of the frame (walls, roof faces, domes; not
#          windows or paving), REPEAT_N or more along one constant step, widths and heights within
#          REPEAT_CV
# It prints WARN, never FAIL: on the showcase it finds the kite's cloud sea (rounds 1 and 2) and the
# canal's north row of houses (round 2), passes Lantern Isle and most examples, but misses the canal's
# round-1 south houses and the lighthouse's scallops, and flags the observatory's cloud sea, an iso
# city block, Santorini's houses and a title screen. Read the line as a pointer; the art director judges.
REPEAT_N = 4
REPEAT_CV = 0.15
REPEAT_LOBE = 1 / 24
REPEAT_DEPTH = 0.05
REPEAT_AREA = 0.003

def _bounds(lab, n, W, H):
    ys, xs = np.nonzero(lab >= 0); l = lab[ys, xs]
    x0 = np.full(n, W); x1 = np.zeros(n, int); y0 = np.full(n, H); y1 = np.zeros(n, int)
    np.minimum.at(x0, l, xs); np.maximum.at(x1, l, xs); np.minimum.at(y0, l, ys); np.maximum.at(y1, l, ys)
    return np.bincount(l, minlength=n), x0, x1, y0, y1

def _cusps(p, A, k, merge):
    """the cusps of a silhouette profile p (y down for a top edge): sharp local maxima, A deep on both
    sides within k; spikes within `merge` px of each other are one stepped cusp"""
    out = []
    for i in range(1, len(p) - 1):
        if p[i] >= p[i - 1] and p[i] >= p[i + 1]:
            if p[i] - p[max(0, i - k):i + 1].min() >= A and p[i] - p[i:i + k + 1].min() >= A:
                out.append(i)
    g = []
    for i in out:
        if g and i - g[-1][-1] <= merge:
            g[-1].append(i)
        else:
            g.append([i])
    return [int(round(np.mean(x))) for x in g]

def _lobe_rows(F, seg):
    H, W = F.H, F.W
    lab, n = _components(F.op, seg[:, 1:] == seg[:, :-1], seg[1:] == seg[:-1])
    if n == 0:
        return []
    size, x0, x1, y0, y1 = _bounds(lab, n, W, H)
    ys = np.arange(H)[:, None]
    wmin = max(6, W * REPEAT_LOBE)
    hits = []
    for i in np.nonzero((x1 - x0 + 1 >= W // 6) & (size >= 0.002 * H * W))[0]:
        mm = lab[:, x0[i]:x1[i] + 1] == i
        cols = mm.any(0)
        top = np.where(mm, ys, H).min(0).astype(float)
        bot = np.where(mm, ys, -1).max(0).astype(float)
        for side, p in (('a top edge', top), ('an underside', -bot)):
            ok = cols & (np.abs(p) > 0) & (np.abs(p) < H - 1)
            r = np.diff(np.concatenate([[0], ok.astype(int), [0]]))
            for a, b in zip(np.nonzero(r == 1)[0], np.nonzero(r == -1)[0]):
                if b - a < W // 6:
                    continue
                q = p[a:b]
                J = _cusps(q, max(2, H // 90), max(4, W // 24), 6)
                wl = np.diff(J).astype(float)
                for s in range(len(wl) - REPEAT_N + 1):
                    ww = wl[s:s + REPEAT_N]
                    if ww.min() < wmin:
                        continue
                    cv = ww.std() / ww.mean()
                    dep = min(min(q[J[s + j]], q[J[s + j + 1]]) - q[J[s + j]:J[s + j + 1] + 1].min() for j in range(REPEAT_N))
                    if cv <= REPEAT_CV and dep >= max(2, REPEAT_DEPTH * ww.mean()):
                        hits.append((float(cv), 'lobes', '%d lobes along %s, %.0f px wide each (spread %.0f%%), x %d-%d, y %d'
                                     % (REPEAT_N, side, ww.mean(), 100 * cv, x0[i] + a + J[s], x0[i] + a + J[s + REPEAT_N],
                                        int(np.median(np.abs(q))))))
                        break
    return hits

def _unit_rows(F):
    H, W = F.H, F.W
    lab, n = _components(F.op, F.dh < TOL, F.dv < TOL)
    if n == 0:
        return []
    size, x0, x1, y0, y1 = _bounds(lab, n, W, H)
    w = x1 - x0 + 1; h = y1 - y0 + 1
    keep = ((w >= max(5, W // 24)) & (h >= max(4, H // 45)) & (w <= W // 4) & (size >= 0.3 * w * h)
            & (w * h >= REPEAT_AREA * H * W) & (x0 > 0) & (x1 < W - 1) & (y0 > 0) & (y1 < H - 1))
    U = [int(u) for u in np.nonzero(keep)[0]]
    cx = (x0 + x1) / 2.0; cy = (y0 + y1) / 2.0
    like = lambda a, b: abs(w[a] - w[b]) <= 0.25 * w[b] and abs(h[a] - h[b]) <= 0.25 * h[b]
    hits = []
    for u in U:
        for v in U:
            if v == u or cx[v] <= cx[u] or not like(v, u):
                continue
            dx, dy = cx[v] - cx[u], cy[v] - cy[u]
            if dx > 1.6 * w[u] or abs(dy) > 0.8 * dx + 2:
                continue
            chain = [u, v]
            tol = max(2, 0.2 * np.hypot(dx, dy))
            while len(chain) < 12:
                ex, ey = cx[chain[-1]] + dx, cy[chain[-1]] + dy
                nx = [t for t in U if abs(cx[t] - ex) <= tol and abs(cy[t] - ey) <= tol and like(t, u) and t not in chain]
                if not nx:
                    break
                chain.append(nx[0])
            if len(chain) >= REPEAT_N:
                ws = w[chain].astype(float); hs = h[chain].astype(float)
                cv = max(ws.std() / ws.mean(), hs.std() / hs.mean())
                if cv <= REPEAT_CV:
                    hits.append((float(cv), 'units', '%d alike shapes of %.0fx%.0f px in a row, x %d-%d, y %d-%d'
                                 % (len(chain), ws.mean(), hs.mean(), x0[chain].min(), x1[chain].max(), y0[chain].min(), y1[chain].max())))
    return hits

def repeats(img, seg=None):
    """[(spread, kind, where)] rows of near-identical lobes or units, most alike first ([] = none)"""
    F = _F(img)
    seg = _regions(F) if seg is None else seg
    hits = _lobe_rows(F, seg) + _unit_rows(F)
    hits.sort(key=lambda x: x[0])
    out, seen = [], set()
    for hh in hits:                      # one line per place
        key = hh[2].split(', x ')[-1][:9]
        if key not in seen:
            seen.add(key); out.append(hh)
    return out

# ---------------------------------------------------------------- block-in
# A block-in is a greyscale layout drawn before any detail: one flat value per plane, the hero's
# light the brightest. BLOCK_* are what `pixelate check BLOCKIN.png --blockin` holds it to.
BLOCK_BANDS = (3, 4)       # distinct value bands (each at least BLOCK_MIN of the frame)
BLOCK_MIN = 0.01
BLOCK_MERGE = 0.05         # values closer than this (L) are one band
BLOCK_PLANE_TOL = 0.08     # a plane's share may miss the brief's by this much (of the frame)
BLOCK_HERO_IOU = 0.5       # the brightest band's mass overlaps the brief's hero bbox at least this much
BLOCK_SLAB = 0.5           # a block-in is made of rectangles: only an inner straight edge over half the frame fails

def value_bands(img):
    """[(L, share)] the block-in's value bands, darkest first: lightness values merged when within
    BLOCK_MERGE, bands under BLOCK_MIN of the frame dropped"""
    F = _F(img)
    L = np.round(F.L[F.op] / 0.01) * 0.01
    u, cnt = np.unique(L, return_counts=True)
    bands = []
    for v, c in zip(u, cnt):
        if bands and v - bands[-1][2] <= BLOCK_MERGE:
            b = bands[-1]; b[0] += v * c; b[1] += c; b[2] = v
        else:
            bands.append([v * c, c, v])
    tot = float(F.op.sum())
    return [(b[0] / b[1], b[1] / tot) for b in bands if b[1] / tot >= BLOCK_MIN]

def band_map(img, bands):
    """(H, W) index of the nearest band per pixel"""
    F = _F(img)
    v = np.array([b[0] for b in bands])
    return np.argmin(np.abs(F.L[..., None] - v), -1)

def blockin_empty(img, bands, cols=16):
    """{'empty', 'empty_low'} on a coarse grid of `cols` columns: a cell is empty when one value band
    covers 97% of it (a block-in has no texture, so the frame-mode test would call it all empty)"""
    F = _F(img)
    m = band_map(F, bands)
    c = max(2, int(round(F.W / cols)))
    gh, gw = F.H // c, F.W // c
    b = m[:gh * c, :gw * c].reshape(gh, c, gw, c).transpose(0, 2, 1, 3).reshape(gh, gw, c * c)
    top = np.stack([(b == k).mean(-1) for k in range(len(bands))], -1).max(-1)
    empty = top >= 0.97
    return {'empty': float(empty.mean()), 'empty_low': float(empty[gh - gh // 3:].mean())}

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
