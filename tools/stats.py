#!/usr/bin/env python3
"""Frame statistics and numeric budgets: measure a rendered frame the way the ten reference studies
measured the games, and hold a scene to its style's numbers.

usage: stats.py IMAGE [--scale N] [--style NAME] [--pal PALETTE] [--json]
       (--scale N: IMAGE is a delivered N x frame; it is sampled back to 1x and its cells checked)

    import stats
    s = stats.frame_stats(img_1x)                         # dict: 'L<0.25', 'C>0.08', 'black', 'median_L', ...
    s = stats.frame_stats(img_1x, masks={'actor': hero}, grid=c.g)    # + per-mask stats (s['masks'])
    fails = stats.budget(img_1x, 'neon-noir')             # [] when the frame is on its style's budget
    fails = stats.budget(img_1x, {'L<0.1': (0.4, 0.6), 'L>0.8': (None, 0.005)})
    stats.native_cells(big, 4)        # share of 4x4 cells that are not one flat colour: 0 for native styles
    stats.palette_subset(img_1x, PAL) # the strict pixel layer: pixels whose colour is not a palette colour
    stats.readability(img_1x, hero)   # outline / fill against the 8 px ring around the actor (Celeste)

Rules are {metric: (lo, hi)} with None for an open end; shares are fractions (0.015 = 1.5%).
Metrics (all in OKLab, 'chromatic' means C > 0.03):
  L<x L>x L<=x L>=x C>x C<x     share of pixels          L[a,b]  C[a,b]   share with a <= value < b
  black white                   share of exactly #000000 / #ffffff
  hue[a,b]                      share of chromatic pixels with hue in a..b degrees (wraps past 360)
  median_L mean_L std_L p5_L p95_L p99_L median_C mean_C p95_C      colours (distinct)
  warm cool                     share of chromatic pixels with hue in 345..115 / 150..300
  detail                        mean |dL| between neighbours (both inside the mask)
  share                         the mask's share of the frame
  edge_dL                       mean L of the mask's 1 px rim minus mean L of the 8 px ring outside it
  bright_offset                 distance of the L > 0.8 centroid from the 'subject' mask's centroid
                                (or the frame centre), in frame widths
  mask:metric                   a metric inside one mask        a/b:metric   ratio between two masks
  gap:a,b                       |mean L of mask a - mean L of mask b| (layer separation)
Masks are H x W bool arrays, or slot names resolved on grid=c.g: 'hero' is the ramp hero0..heroN,
('hero', 'ol_hero') several ramps, 'far_' or 'hero*' every slot with that prefix.

Learned from the reference measurements (study/NN): Sword & Sworcery keeps 65% of its pixels
below L .25 and 0.08% above .75; Stardew's mine is 52% below L .1; Katana ZERO is 25.7% exact
black with 0.5% above C .10; Celeste holds 99.5% of its colour in 240-360 degrees.
"""
import json, pathlib, re, sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl

CHROMA = 0.03                                   # below this a pixel has no hue worth counting

# ---------------------------------------------------------------- input
def _rgb(img):
    """PIL image or array -> (H, W, 3) uint8 and an (H, W) opaque mask"""
    if isinstance(img, Image.Image):
        a = np.asarray(img.convert('RGBA'))
        return a[..., :3], a[..., 3] >= 128
    a = np.asarray(img)
    if a.dtype != np.uint8:
        a = np.clip(np.round(a * 255 if a.max() <= 1.0 else a), 0, 255).astype(np.uint8)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, -1)
    op = a[..., 3] >= 128 if a.shape[-1] == 4 else np.ones(a.shape[:2], bool)
    return a[..., :3], op

def _masks(masks, grid, shape):
    out = {}
    for k, m in (masks or {}).items():
        if isinstance(m, (str, tuple, list)) and not isinstance(m, np.ndarray):
            if grid is None:
                raise ValueError('mask %r is given as slot prefixes: pass grid=c.g' % k)
            pre = (m,) if isinstance(m, str) else tuple(m)
            g = np.asarray(grid)
            vals = [v for v in set(g.ravel()) - {None} if _slot_match(str(v), pre)]
            mm = np.zeros(g.shape, bool)
            for v in vals:
                mm |= g == v
            out[k] = mm
        else:
            out[k] = np.asarray(m, bool)
        if out[k].shape != shape:
            raise ValueError('mask %r is %s, the frame is %s (masks are at 1x)' % (k, out[k].shape, shape))
    return out

def _slot_match(v, pats):
    """'hero' matches the ramp hero0..heroN (not heroine2); 'far_' or 'hero*' match by prefix"""
    base = v.rstrip('0123456789')
    for p in pats:
        if p.endswith('*'):
            if v.startswith(p[:-1]): return True
        elif p.endswith('_'):
            if v.startswith(p): return True
        elif v == p or base == p:
            return True
    return False

class _Frame:
    """one conversion to OKLab, shared by every metric"""
    def __init__(self, img, masks=None, grid=None):
        self.rgb, self.op = _rgb(img)
        self.H, self.W = self.rgb.shape[:2]
        key = self.rgb.reshape(-1, 3).astype(np.uint32) @ np.array([65536, 256, 1], np.uint32)
        u, inv = np.unique(key, return_inverse=True)   # convert each distinct colour once
        urgb = np.stack([u >> 16, (u >> 8) & 255, u & 255], 1).astype(float)
        ulab = cl.rgb_to_oklab(urgb)
        uL, uC = ulab[:, 0], np.hypot(ulab[:, 1], ulab[:, 2])
        uh = np.degrees(np.arctan2(ulab[:, 2], ulab[:, 1])) % 360
        inv = inv.reshape(self.H, self.W)
        self.L, self.C, self.h = uL[inv], uC[inv], uh[inv]
        self.masks = _masks(masks, grid, (self.H, self.W))

    def sel(self, name=None):
        m = self.op if name is None else (self.masks[name] & self.op)
        return m

# ---------------------------------------------------------------- metrics
_CMP = re.compile(r'^([LC])\s*(<=|>=|<|>)\s*([0-9.]+)$')
_RNG = re.compile(r'^([LC])\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]$')
_HUE = re.compile(r'^hue\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]$')
_STAT = re.compile(r'^(median|mean|std|p\d+)_([LC])$')

def _hue_in(h, a, b):
    return ((h - a) % 360) <= ((b - a) % 360)

def _metric(F, name, mask=None):
    m = F.sel(mask)
    n = int(m.sum())
    if name == 'share':
        return n / max(1, F.op.sum())
    if n == 0:
        return float('nan')
    L, C, h = F.L[m], F.C[m], F.h[m]
    g = _CMP.match(name)
    if g:
        v = L if g.group(1) == 'L' else C
        x = float(g.group(3))
        op = {'<': np.less, '>': np.greater, '<=': np.less_equal, '>=': np.greater_equal}[g.group(2)]
        return float(op(v, x).mean())
    g = _RNG.match(name)
    if g:
        v = L if g.group(1) == 'L' else C
        return float(((v >= float(g.group(2))) & (v < float(g.group(3)))).mean())
    g = _HUE.match(name)
    if g:
        ch = C > CHROMA
        return float(_hue_in(h[ch], float(g.group(1)), float(g.group(2))).mean()) if ch.any() else 1.0
    g = _STAT.match(name)
    if g:
        v = L if g.group(2) == 'L' else C
        k = g.group(1)
        return float(np.median(v) if k == 'median' else v.mean() if k == 'mean' else v.std() if k == 'std'
                     else np.percentile(v, float(k[1:])))
    rgb = F.rgb[m]
    if name == 'black':
        return float((rgb.sum(1) == 0).mean())
    if name == 'white':
        return float((rgb.min(1) == 255).mean())
    if name == 'colours' or name == 'colors':
        return int(len(np.unique(rgb.astype(np.uint32) @ np.array([65536, 256, 1], np.uint32))))
    if name in ('warm', 'cool'):
        ch = C > CHROMA
        if not ch.any():
            return 0.0
        hh = h[ch]
        return float((_hue_in(hh, 345, 115) if name == 'warm' else _hue_in(hh, 150, 300)).mean())
    if name == 'detail':
        d = []
        for a, b in ((F.L[:, 1:], F.L[:, :-1]), (F.L[1:], F.L[:-1])):
            mm = (m[:, 1:] & m[:, :-1]) if a.shape[1] != F.W else (m[1:] & m[:-1])
            d.append(np.abs(a - b)[mm])
        d = np.concatenate(d)
        return float(d.mean()) if len(d) else float('nan')
    if name == 'edge_dL':
        return readability(F, mask)['edge_dL']
    if name == 'bright_offset':
        b = F.sel() & (F.L > 0.8)
        if not b.any():
            return 0.0
        ys, xs = np.nonzero(b)
        if 'subject' in F.masks and F.masks['subject'].any():
            sy, sx = np.nonzero(F.masks['subject']); cx, cy = sx.mean(), sy.mean()
        else:
            cx, cy = F.W / 2, F.H / 2
        return float(np.hypot(xs.mean() - cx, ys.mean() - cy) / F.W)
    raise ValueError('unknown metric %r (see stats.py docstring)' % name)

def metric(F, key):
    """one rule key: 'L<0.25', 'actor:detail', 'actor/world:detail', 'gap:far,near'"""
    if key.startswith('gap:'):
        a, b = key[4:].split(',')
        return abs(_metric(F, 'mean_L', a.strip()) - _metric(F, 'mean_L', b.strip()))
    if ':' in key:
        where, name = key.split(':', 1)
        if '/' in where:
            a, b = where.split('/')
            return _metric(F, name, a) / max(1e-9, _metric(F, name, b))
        return _metric(F, name, where)
    return _metric(F, key)

def _need(key):
    """the masks a rule key needs"""
    if key.startswith('gap:'):
        return [s.strip() for s in key[4:].split(',')]
    if ':' in key:
        return key.split(':', 1)[0].split('/')
    return ['subject'] if key == 'bright_offset' else []

STANDARD = ('L<0.1', 'L<0.25', 'L<0.3', 'L>0.6', 'L>=0.7', 'L>0.75', 'L>0.8', 'L>0.9', 'C>0.08', 'C>0.1',
            'C>0.15', 'black', 'white', 'median_L', 'mean_L', 'std_L', 'p5_L', 'p95_L', 'median_C', 'p95_C',
            'warm', 'cool', 'colours', 'detail')
MASK_STANDARD = ('share', 'mean_L', 'std_L', 'p5_L', 'p95_L', 'median_C', 'C>0.08', 'detail', 'edge_dL')

def frame_stats(img_1x, masks=None, grid=None):
    """every standard metric of the frame, plus 'hue_hist' (share of chromatic pixels per 30 degrees,
    from 0), 'bright_centroid' (x, y of the L > 0.8 pixels as fractions of the frame) and, with masks,
    'masks': {name: {share, mean_L, ...}} and 'gaps': {'a,b': mean-L gap}"""
    F = img_1x if isinstance(img_1x, _Frame) else _Frame(img_1x, masks, grid)
    s = {k: metric(F, k) for k in STANDARD}
    s['size'] = (F.W, F.H)
    m = F.sel()
    ch = m & (F.C > CHROMA)
    hist = np.bincount((F.h[ch] // 30).astype(int), minlength=12)[:12]
    s['hue_hist'] = [round(float(v), 4) for v in hist / max(1, ch.sum())]
    b = m & (F.L > 0.8)
    if b.any():
        ys, xs = np.nonzero(b); s['bright_centroid'] = (round(xs.mean() / F.W, 3), round(ys.mean() / F.H, 3))
    if F.masks:
        s['masks'] = {k: {n: metric(F, '%s:%s' % (k, n)) for n in MASK_STANDARD} for k in F.masks}
        names = list(F.masks)
        s['gaps'] = {'%s,%s' % (a, b): metric(F, 'gap:%s,%s' % (a, b)) for i, a in enumerate(names) for b in names[i + 1:]}
    return s

def readability(img_1x, mask, ring=8, masks=None, grid=None):
    """how an actor reads against what is around it: edge_dL (mean L of its 1 px rim minus mean L of
    the `ring` px outside it; Celeste outlines sit <= -0.25), fill_dL (its mean L minus the ring's)
    and dhue (degrees between its dominant hue and the ring's)"""
    import morph
    F = img_1x if isinstance(img_1x, _Frame) else _Frame(img_1x, masks, grid)
    m = F.masks[mask] if isinstance(mask, str) else np.asarray(mask, bool)
    if not m.any():
        return {'edge_dL': float('nan'), 'fill_dL': float('nan'), 'dhue': float('nan')}
    rim = m & ~morph.erode(m, 1, 'cross', border=False)
    out = morph.dilate(m, ring, 'square') & ~m
    if not out.any():
        return {'edge_dL': float('nan'), 'fill_dL': float('nan'), 'dhue': float('nan')}
    def dom(sel):
        sel = sel & (F.C > CHROMA)
        if not sel.any():
            return None
        return float(np.degrees(np.arctan2(np.sin(np.radians(F.h[sel])).mean(), np.cos(np.radians(F.h[sel])).mean())) % 360)
    ha, hb = dom(m), dom(out)
    return {'edge_dL': float(F.L[rim].mean() - F.L[out].mean()),
            'fill_dL': float(F.L[m].mean() - F.L[out].mean()),
            'dhue': float(abs(((ha - hb + 180) % 360) - 180)) if ha is not None and hb is not None else float('nan')}

# ---------------------------------------------------------------- budgets
def _rules(rules):
    if isinstance(rules, str):
        import styles
        st = styles.get(rules)
        return st['budgets'], st['name']
    return dict(rules), 'given'

def budget_report(img_1x, rules, masks=None, grid=None):
    """[(rule, value, lo, hi, 'ok'|'fail'|'skip')] for a rules dict or a style name (styles.STYLES)"""
    rules, _ = _rules(rules)
    F = img_1x if isinstance(img_1x, _Frame) else _Frame(img_1x, masks, grid)
    rows = []
    for key, (lo, hi) in rules.items():
        missing = [n for n in _need(key) if n not in F.masks and not (key == 'bright_offset')]
        if missing:
            rows.append((key, None, lo, hi, 'skip')); continue
        v = metric(F, key)
        bad = v != v or (lo is not None and v < lo) or (hi is not None and v > hi)
        rows.append((key, v, lo, hi, 'fail' if bad else 'ok'))
    return rows

def _fmt(key, v):
    if v is None or v != v:
        return '-'
    share = (_CMP.match(key.split(':')[-1]) or _RNG.match(key.split(':')[-1]) or _HUE.match(key.split(':')[-1])
             or key.split(':')[-1] in ('black', 'white', 'warm', 'cool', 'share'))
    return ('%.2f%%' % (100 * v)) if share and '/' not in key.split(':')[0] else ('%d' % v if isinstance(v, int) else '%.3f' % v)

def budget(img_1x, rules, masks=None, grid=None):
    """the rules a frame breaks, as readable lines ([] = on budget). rules: {metric: (lo, hi)} or a
    style name from styles.STYLES. Rules that need a mask you did not pass are skipped."""
    rules_d, who = _rules(rules)
    out = []
    for key, v, lo, hi, st in budget_report(img_1x, rules_d, masks, grid):
        if st != 'fail':
            continue
        want = ('between %s and %s' % (_fmt(key, lo), _fmt(key, hi)) if lo is not None and hi is not None else
                'at least %s' % _fmt(key, lo) if lo is not None else 'at most %s' % _fmt(key, hi))
        out.append('%s is %s, the %s budget is %s' % (key, _fmt(key, v), who, want))
    return out

# ---------------------------------------------------------------- grid and palette checks
def to_native(img, scale, phase=(0, 0)):
    """a delivered scale x frame sampled back to 1x (the centre pixel of each cell)"""
    rgb, op = _rgb(img)
    s = int(scale); px, py = phase
    H, W = (rgb.shape[0] - py) // s, (rgb.shape[1] - px) // s
    ys = py + s * np.arange(H) + s // 2; xs = px + s * np.arange(W) + s // 2
    return Image.fromarray(rgb[ys][:, xs].copy(), 'RGB')

def native_cells(img, scale, tol=0, phase=(0, 0), return_map=False):
    """share of scale x scale cells that are not one flat colour (channel range > tol). A native-grid
    style (all of the pixel layer, and native light) must give 0; a screen-resolution light layer
    does not. return_map=True also returns the (H/s, W/s) bool map of the soft cells."""
    rgb, _ = _rgb(img)
    s = int(scale); px, py = phase
    H, W = (rgb.shape[0] - py) // s, (rgb.shape[1] - px) // s
    a = rgb[py:py + H * s, px:px + W * s].reshape(H, s, W, s, 3).astype(np.int16)
    rng = a.max(axis=(1, 3)) - a.min(axis=(1, 3))
    soft = (rng > tol).any(-1)
    share = float(soft.mean()) if soft.size else 0.0
    return (share, soft) if return_map else share

def palette_subset(img, pal):
    """the pixels of a frame whose colour is not in `pal` ({slot: hex}, [hex] or a palette name):
    {'ok', 'off_pixels', 'off_share', 'off_colours', 'top': [(hex, pixels), ...]}. Run it on the
    pixel layer before any light: a strict pixel layer has none."""
    if isinstance(pal, str) and not pal.startswith('#'):
        pal = cl.load_palette(pal)
    elif isinstance(pal, str):
        pal = pal.split(',')
    hexes = cl.palette_list(pal)
    rgb, op = _rgb(img)
    key = rgb.astype(np.uint32) @ np.array([65536, 256, 1], np.uint32)
    allowed = np.array(sorted({int(h.lstrip('#')[:6], 16) for h in hexes}), np.uint32)
    off = op & ~np.isin(key, allowed)
    u, c = np.unique(key[off], return_counts=True)
    o = np.argsort(-c)[:10]
    return {'ok': not off.any(), 'off_pixels': int(off.sum()), 'off_share': float(off.sum() / max(1, op.sum())),
            'off_colours': int(len(u)), 'top': [('#%06x' % int(u[i]), int(c[i])) for i in o]}

# ---------------------------------------------------------------- cli
def main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return 1
    scale, style, pal = int(opt('--scale', '1')), opt('--style'), opt('--pal')
    as_json = '--json' in a
    if as_json: a.remove('--json')
    img = Image.open(a[0])
    res = {}
    if scale > 1:
        res['native_cells'] = native_cells(img, scale)
        img = to_native(img, scale)
    s = frame_stats(img)
    res.update(s)
    if pal:
        res['palette_subset'] = palette_subset(img, pal)
    rows = budget_report(img, style) if style else []
    if as_json:
        res['budget'] = [list(r) for r in rows]
        print(json.dumps(res, indent=1, default=float)); return 0
    W, H = s['size']
    print('%s: %dx%d at 1x, %d colours' % (a[0], W, H, s['colours']))
    if 'native_cells' in res:
        print('  soft %dx%d cells: %.2f%% (0 for a native-grid style)' % (scale, scale, 100 * res['native_cells']))
    for k in STANDARD:
        if k != 'colours':
            print('  %-10s %s' % (k, _fmt(k, s[k])))
    print('  hue_hist   ' + ' '.join('%d:%.0f%%' % (30 * i, 100 * v) for i, v in enumerate(s['hue_hist']) if v >= 0.005))
    if 'palette_subset' in res:
        p = res['palette_subset']
        print('  palette    %s (%d off-palette pixels in %d colours)' % ('ok' if p['ok'] else 'OFF', p['off_pixels'], p['off_colours']))
    bad = False
    if rows:
        print('budget %s:' % style)
        for key, v, lo, hi, st in rows:
            bad |= st == 'fail'
            print('  %-4s %-18s %-9s [%s .. %s]' % (st, key, _fmt(key, v), _fmt(key, lo) if lo is not None else '',
                                                  _fmt(key, hi) if hi is not None else ''))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
