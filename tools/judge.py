#!/usr/bin/env python3
"""pixelate judge FRAME.png [--scale N] [--json] [--overlay OUT.png] [--log [PATH]] [--ignore KIND,...]

The judge: finds the pixel-art failures the gate passes and an art director rejects, and says where
they are and how to fix them. The gate (`pixelate check`) proves a frame is legal; the judge points
at what still reads wrong. Each defect has a kind, a box in native pixels (x0, y0, x1, y1, inclusive),
a severity 0..1, why it reads wrong and a fix. The detectors came from the art-director rounds of the
showcase moments run (the ten library pieces listed in docs/gallery/moments.md):

  masonry       straight seam grids with T-junctions: rock, cliff or bark that reads as brick
  repeat_units  rows of same-size units at even spacing: stamped houses, ribs, drips, windows
  scallops      an edge made of near-identical bumps: cloud, wave or canopy scallops
  outline_loop  a 1 px ring of one colour around the same colour it sits on: a mass drawn as a contour
  murky         most of the frame in one narrow value band: no value structure

They report; they do not fail the gate. A rectilinear building can trip masonry, a deliberate row
(a fence, a colonnade) can trip repeat_units: read the box, then fix it or say why it stays.
--overlay writes the frame with numbered boxes; --log appends the run to .pixelate/judge-log.jsonl,
the corpus of drafts, defects and critiques the detectors are later calibrated on.

    import judge
    for d in judge.detect('still@4x.png', scale=4): print(d['kind'], d['box'], d['fix'])
"""
import argparse, datetime, hashlib, json, os, pathlib, sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl
import morph

KINDS = ('masonry', 'repeat_units', 'scallops', 'outline_loop', 'murky')
LOG = pathlib.Path('.pixelate') / 'judge-log.jsonl'

FIX = {
    'masonry': 'Natural material drawn as bricks or tiles: replace the straight seam grid with strata of uneven '
               'thickness, frayed overhanging lips, a lit top edge on each ledge and flake dashes '
               '(recipes.rock_face). Leave it if this really is masonry, planks or a window grid.',
    'repeat_units': 'Units repeat at one size and one spacing: vary their size by 25% or more between '
                    'neighbours, make the gaps uneven, give one or two a different shape (roof, door, '
                    'missing piece). Leave it if the row is deliberate (a fence, a colonnade).',
    'scallops': 'The edge is a row of near-identical bumps: make it three or four lobes of very '
                'different radius with one long flat run (recipes.cloud_bank, shapes.cloud_mass).',
    'outline_loop': 'A mass drawn as a 1 px contour around the ground colour: fill it one value off its '
                    'neighbour, and keep a lit rim only on the side facing the light.',
    'murky': 'Most of the frame sits in one value band: plan three or four value groups, give one plane '
             'a clearly darker or lighter range, and keep the brightest values at the focal point.',
}

# ---------------------------------------------------------------- loading
def native_scale(img, max_scale=16, tol=10):
    """the largest whole scale s at which img is made of s x s cells: exactly flat cells, or for a
    screen-light frame (smooth light inside each art pixel) cells within `tol` levels of their centre"""
    H, W = img.shape[:2]
    a = img.astype(np.int16)
    for s in range(max_scale, 1, -1):
        if H % s or W % s:
            continue
        cells = a.reshape(H // s, s, W // s, s, -1)
        centre = cells[:, s // 2:s // 2 + 1, :, s // 2:s // 2 + 1]
        dev = np.abs(cells - centre).max(axis=-1)
        if (dev == 0).mean() >= 0.97 or (dev <= tol).mean() >= 0.97:
            return s
    return 1

def load(frame, scale=None):
    """the frame at 1x as (rgb uint8 HxWx3, scale): cells sampled at their centres, so a screen-light
    frame (smooth inside each cell) still gives one colour per art pixel"""
    from PIL import Image
    im = np.asarray(Image.open(frame).convert('RGB'))
    s = int(scale) if scale else native_scale(im)
    if s > 1:
        im = im[s // 2::s, s // 2::s][:im.shape[0] // s, :im.shape[1] // s]
    return np.ascontiguousarray(im), s

def lightness(rgb):
    return cl.rgb_to_oklab(rgb.reshape(-1, 3))[:, 0].reshape(rgb.shape[:2])

def indexed(rgb, max_colours=96):
    """(index map, number of colours): one integer per distinct colour. A frame with more colours
    than max_colours (a smooth light layer) is clustered in OKLab to max_colours first."""
    flat = rgb.reshape(-1, 3).astype(np.int32)
    keys = (flat[:, 0] << 16) | (flat[:, 1] << 8) | flat[:, 2]
    uniq, inv, counts = np.unique(keys, return_inverse=True, return_counts=True)
    if len(uniq) > max_colours:
        cols = np.stack([(uniq >> 16) & 255, (uniq >> 8) & 255, uniq & 255], axis=1)
        lab = cl.rgb_to_oklab(cols)
        centres = cl.kmeans(lab, max_colours, weights=counts.astype(float))
        inv = cl.nearest(lab, centres)[inv]
    idx = np.asarray(inv).reshape(rgb.shape[:2])
    _, idx = np.unique(idx, return_inverse=True)
    idx = idx.reshape(rgb.shape[:2])
    return idx, int(idx.max()) + 1

def _defect(kind, box, severity, why, **extra):
    x0, y0, x1, y1 = (int(v) for v in box)
    d = {'kind': kind, 'box': [x0, y0, x1, y1], 'severity': round(float(min(1.0, max(0.0, severity))), 2),
         'why': why, 'fix': FIX[kind]}
    d.update(extra)
    return d

def _runs(mask, axis, min_len):
    """keep only straight runs of mask along axis (1 = rows, 0 = columns) at least min_len long"""
    m = mask if axis == 1 else mask.T
    out = np.zeros_like(m)
    for r in range(m.shape[0]):
        row = m[r]
        if not row.any():
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        for a, b in zip(starts, ends):
            if b - a >= min_len:
                out[r, a:b] = True
    return out if axis == 1 else out.T

# ---------------------------------------------------------------- detectors
def masonry(rgb, L=None, tile=24, min_share=0.05, min_junctions=3, min_tiles=2):
    """straight dark seams (1 px lines darker than both sides) that form a grid with T-junctions"""
    L = lightness(rgb) if L is None else L
    H, W = L.shape
    t = 0.035
    up, dn = np.roll(L, 1, 0), np.roll(L, -1, 0)
    lf, rt = np.roll(L, 1, 1), np.roll(L, -1, 1)
    hseam = (L < up - t) & (L < dn - t)
    vseam = (L < lf - t) & (L < rt - t)
    hseam[[0, -1], :] = False
    vseam[:, [0, -1]] = False
    # bridge the 1 px break a joint makes (the gap pixel is itself dark against one side), never the
    # light gaps of a checker dither
    hseam |= np.roll(hseam, 1, 1) & np.roll(hseam, -1, 1) & ((L < up - t) | (L < dn - t)) & (L <= np.roll(L, 1, 1) + 0.01)
    vseam |= np.roll(vseam, 1, 0) & np.roll(vseam, -1, 0) & ((L < lf - t) | (L < rt - t)) & (L <= np.roll(L, 1, 0) + 0.01)
    h = _runs(hseam, 1, 6)
    v = _runs(vseam, 0, 3)
    vend = v & ~(np.roll(v, 1, 0) & np.roll(v, -1, 0))        # the ends of vertical seams
    junction = vend & (np.roll(h, 1, 0) | np.roll(h, -1, 0) | h)
    ty, tx = (H + tile - 1) // tile, (W + tile - 1) // tile
    hit = np.zeros((ty, tx), bool)
    score = np.zeros((ty, tx))
    for j in range(ty):
        for i in range(tx):
            sl = (slice(j * tile, (j + 1) * tile), slice(i * tile, (i + 1) * tile))
            area = h[sl].size
            share = (h[sl].sum() + v[sl].sum()) / area
            rows = np.flatnonzero(h[sl].any(axis=1))
            courses = len(rows) - np.count_nonzero(np.diff(rows) == 1) if len(rows) else 0
            if share >= min_share and junction[sl].sum() >= min_junctions and courses >= 2:
                hit[j, i] = True
                score[j, i] = share
    out = []
    lab, n = morph.label(hit, connectivity=8)
    for k in range(1, n + 1):
        ys, xs = np.nonzero(lab == k)
        if len(xs) < min_tiles:
            continue
        box = (xs.min() * tile, ys.min() * tile, min(W, (xs.max() + 1) * tile) - 1, min(H, (ys.max() + 1) * tile) - 1)
        sev = min(1.0, score[lab == k].mean() / 0.15) * min(1.0, len(xs) / 2)
        out.append(_defect('masonry', box, sev, 'straight seams cross in a grid (%d tiles of %d px): '
                                                'it reads as brick or blocks' % (len(xs), tile)))
    return out

def _components(idx, ncol, min_px, max_px):
    """connected same-colour regions as (colour, x0, y0, x1, y1, area), 8-connected"""
    out = []
    counts = np.bincount(idx.ravel(), minlength=ncol)
    for c in np.flatnonzero(counts >= min_px):
        lab, n = morph.label(idx == c, connectivity=8)
        if n == 0:
            continue
        areas = np.bincount(lab.ravel())
        ys, xs = np.nonzero(lab)
        ids = lab[ys, xs]
        x0 = np.full(n + 1, 1 << 30); y0 = x0.copy()
        x1 = np.full(n + 1, -1); y1 = x1.copy()
        np.minimum.at(x0, ids, xs); np.minimum.at(y0, ids, ys)
        np.maximum.at(x1, ids, xs); np.maximum.at(y1, ids, ys)
        for k in range(1, n + 1):
            if min_px <= areas[k] <= max_px:
                out.append((int(c), int(x0[k]), int(y0[k]), int(x1[k]), int(y1[k]), int(areas[k])))
    return out

def _cv(a):
    a = np.asarray(a, float)
    return float(a.std() / a.mean()) if len(a) and a.mean() > 0 else 1.0

def repeat_units(rgb, idx=None, ncol=None, min_count=5, size_cv=0.12, gap_cv=0.2):
    """five or more same-colour units of one size on one row band at even spacing"""
    if idx is None:
        idx, ncol = indexed(rgb)
    comps = [t for t in _components(idx, ncol, 12, 600) if t[4] - t[2] >= 2]
    out, used = [], set()
    by_colour = {}
    for comp in comps:
        by_colour.setdefault(comp[0], []).append(comp)
    for c, items in by_colour.items():
        items.sort(key=lambda t: (t[2] + t[4], t[1]))
        for i, a in enumerate(items):
            if (c, i) in used:
                continue
            wa, ha = a[3] - a[1] + 1, a[4] - a[2] + 1
            row = [(j, b) for j, b in enumerate(items)
                   if (c, j) not in used and abs(b[2] - a[2]) <= 1 and abs(b[4] - a[4]) <= 1
                   and abs((b[3] - b[1] + 1) - wa) <= max(1, 0.2 * wa) and abs((b[4] - b[2] + 1) - ha) <= max(1, 0.2 * ha)]
            if len(row) < min_count:
                continue
            row.sort(key=lambda t: t[1][1])
            xs = np.array([(b[1] + b[3]) / 2 for _, b in row])
            gaps = np.diff(xs)
            if len(gaps) < min_count - 1 or gaps.min() <= 0:
                continue
            widths = [b[3] - b[1] + 1 for _, b in row]
            areas = [b[5] for _, b in row]
            if _cv(widths) <= size_cv and _cv(areas) <= size_cv * 1.5 and _cv(gaps) <= gap_cv:
                for j, _ in row:
                    used.add((c, j))
                bs = [b for _, b in row]
                box = (min(b[1] for b in bs), min(b[2] for b in bs), max(b[3] for b in bs), max(b[4] for b in bs))
                sev = min(1.0, len(row) / 10) * (1 - _cv(gaps) / gap_cv * 0.5)
                out.append(_defect('repeat_units', box, sev, '%d units %dx%d px at near-even spacing (gap %.1f px)'
                                   % (len(row), wa, ha, float(np.median(gaps)))))
    return out

def _bumps(profile, min_prom=2):
    """the bumps of an edge profile (bigger = further out): positions and prominences of the maxima
    that stand at least min_prom px above the lowest point between them and their neighbours"""
    p = np.asarray(profile, float)
    pk = [i for i in range(1, len(p) - 1) if p[i] > p[i - 1] and p[i] >= p[i + 1]]
    while True:
        prom = []
        for j, i in enumerate(pk):
            lo = p[pk[j - 1]:i + 1].min() if j else p[:i + 1].min()
            ro = p[i:pk[j + 1] + 1].min() if j + 1 < len(pk) else p[i:].min()
            prom.append(p[i] - max(lo, ro))
        if not pk or min(prom) >= min_prom:
            return np.array(pk), np.array(prom)
        pk.pop(int(np.argmin(prom)))

def scallops(rgb, idx=None, ncol=None, min_bumps=5, gap_cv=0.25, height_cv=0.35, min_width=40, min_gap=6):
    """an edge (top or bottom) of a wide region made of near-identical bumps at even spacing"""
    if idx is None:
        idx, ncol = indexed(rgb)
    H, W = idx.shape
    out = []
    for c, x0, y0, x1, y1, area in _components(idx, ncol, 200, H * W // 2):
        w = x1 - x0 + 1
        if w < min_width or y1 - y0 < 4 or w >= 0.75 * W:   # frame-wide bands are sky or sea strata
            continue
        m = idx[y0:y1 + 1, x0:x1 + 1] == c
        cols = m.any(axis=0)
        if cols.mean() < 0.85:
            continue
        top = np.where(cols, m.argmax(axis=0), m.shape[0] - 1)
        bot = np.where(cols, m.shape[0] - 1 - m[::-1].argmax(axis=0), 0)
        for name, prof in (('top', -top), ('underside', bot)):
            prof = prof.astype(float)
            k = 15
            pad = np.pad(prof, k // 2, mode='edge')
            prof = prof - np.convolve(pad, np.ones(k) / k, mode='valid')   # bumps relative to the dome
            pk, ht = _bumps(prof, 2)
            if len(pk) < min_bumps:
                continue
            widths = []                                   # lobe width at half prominence: dither spikes are 1-2 px
            for i, h in zip(pk, ht):
                a = b = i
                while a > 0 and prof[a - 1] >= prof[i] - h / 2:
                    a -= 1
                while b < len(prof) - 1 and prof[b + 1] >= prof[i] - h / 2:
                    b += 1
                widths.append(b - a + 1)
            if np.median(widths) < 3:
                continue
            gaps = np.diff(pk)
            if np.median(gaps) <= 8 and _cv(gaps) < 0.08:      # a dither or seam rhythm, not lobes
                continue
            if _cv(gaps) <= gap_cv and _cv(ht) <= height_cv and np.median(gaps) >= min_gap:
                yy = (y0 + int(top.min()), y0 + int(top.max()) + 2) if name == 'top' else \
                     (y0 + int(bot.min()) - 2, y0 + int(bot.max()))
                box = (x0 + int(pk.min()) - 2, yy[0], x0 + int(pk.max()) + 2, yy[1])
                sev = min(1.0, len(pk) / 8) * (1 - _cv(gaps) / gap_cv * 0.5)
                out.append(_defect('scallops', box, sev, '%s edge: %d bumps of similar height every %.0f px'
                                   % (name, len(pk), float(np.median(gaps)))))
    return out

def outline_loop(rgb, idx=None, ncol=None, min_px=16, min_inside=24, min_dim=4):
    """a thin (1 px) ring of colour A whose inside is the same colour as its outside"""
    if idx is None:
        idx, ncol = indexed(rgb)
    H, W = idx.shape
    pad = np.pad(idx, 1, mode='edge')
    lr = (pad[1:-1, :-2] != idx) & (pad[1:-1, 2:] != idx)
    ud = (pad[:-2, 1:-1] != idx) & (pad[2:, 1:-1] != idx)
    line = lr | ud
    out = []
    for c in np.flatnonzero(np.bincount(idx.ravel(), minlength=ncol) >= min_px):
        lab, n = morph.label(idx == c, connectivity=8)
        if n == 0:
            continue
        sizes = np.bincount(lab.ravel(), minlength=n + 1)
        lines = np.bincount(lab.ravel(), weights=line.ravel(), minlength=n + 1)
        for k in np.flatnonzero((sizes >= min_px) & (lines >= 0.85 * sizes)):
            if k == 0:
                continue
            ys, xs = np.nonzero(lab == k)
            y0, y1, x0, x1 = max(0, ys.min() - 1), min(H, ys.max() + 2), max(0, xs.min() - 1), min(W, xs.max() + 2)
            if (y1 - y0) < 5 or (x1 - x0) < 5:
                continue
            comp = lab[y0:y1, x0:x1] == k
            sub = idx[y0:y1, x0:x1]
            filled = morph.fill_holes(comp)
            inside = filled & ~comp
            if inside.sum() < min_inside:
                continue
            holes, nh = morph.label(inside, connectivity=4)
            if nh != 1:                                   # a lattice (paving, panels) encloses many cells
                continue
            iy, ix = np.nonzero(inside)
            if iy.max() - iy.min() + 1 < min_dim or ix.max() - ix.min() + 1 < min_dim:
                continue                                  # a thin swell or seam loop, not a mass
            ring = morph.dilate(filled, 1) & ~filled
            if not ring.any():
                continue
            iv, ov = np.bincount(sub[inside]).argmax(), np.bincount(sub[ring]).argmax()
            share = (sub[inside] == iv).mean()
            if iv == ov and share >= 0.6:
                npx = int(sizes[k])
                sev = min(1.0, npx / 60) * share
                out.append(_defect('outline_loop', (xs.min(), ys.min(), xs.max(), ys.max()), sev,
                                   'a %d px one-pixel ring encloses the same colour it sits on' % npx))
    return out

def murky(rgb, L=None, window=0.10, max_share=0.72, min_spread=0.2):
    """most pixels inside one narrow lightness window and a short overall value range"""
    L = lightness(rgb) if L is None else L
    v = np.sort(L.ravel())
    n = len(v)
    j = np.searchsorted(v, v + window, side='right')
    share = float((j - np.arange(n)).max() / n)
    spread = float(np.percentile(v, 95) - np.percentile(v, 5))
    if share >= max_share and spread < min_spread:
        H, W = L.shape
        sev = min(1.0, (share - max_share) / (1 - max_share) + (min_spread - spread) / min_spread)
        return [_defect('murky', (0, 0, W - 1, H - 1), sev,
                        '%.0f%% of the frame sits in one %.2f-wide value band; the 5-95%% value range is %.2f'
                        % (share * 100, window, spread))]
    return []

# ---------------------------------------------------------------- running
def detect(frame, scale=None, ignore=()):
    """every defect in the frame, most severe first"""
    rgb, _s = load(frame, scale)
    return detect_rgb(rgb, ignore)

def detect_rgb(rgb, ignore=()):
    L = lightness(rgb)
    idx, ncol = indexed(rgb)
    found = []
    if 'masonry' not in ignore:
        found += masonry(rgb, L)
    if 'repeat_units' not in ignore:
        found += repeat_units(rgb, idx, ncol)
    if 'scallops' not in ignore:
        found += scallops(rgb, idx, ncol)
    if 'outline_loop' not in ignore:
        found += outline_loop(rgb, idx, ncol)
    if 'murky' not in ignore:
        found += murky(rgb, L)
    found.sort(key=lambda d: -d['severity'])
    for i, d in enumerate(found, 1):
        d['id'] = i
    return found

def overlay(frame, defects, out, scale=None, width=960):
    """the frame enlarged by a whole factor, with each defect boxed and numbered"""
    from PIL import Image, ImageDraw
    rgb, _s = load(frame, scale)
    H, W = rgb.shape[:2]
    k = max(2, width // W)
    im = Image.fromarray(rgb).resize((W * k, H * k), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for d in defects:
        x0, y0, x1, y1 = d['box']
        dr.rectangle([x0 * k, y0 * k, (x1 + 1) * k - 1, (y1 + 1) * k - 1], outline=(255, 0, 200), width=2)
        tag = '%d %s' % (d['id'], d['kind'])
        tx, ty = x0 * k + 3, max(0, y0 * k - 12) if y0 * k >= 12 else y0 * k + 3
        dr.rectangle([tx - 2, ty - 1, tx + 6 * len(tag) + 2, ty + 10], fill=(20, 0, 20))
        dr.text((tx, ty), tag, fill=(255, 120, 230))
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def log(record, path=None):
    """append one record (a judge run or a critique) to the corpus log"""
    p = pathlib.Path(path) if path else LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    record = dict(record, time=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return p

def report(defects):
    if not defects:
        return 'judge: no defects found (masonry, repeat_units, scallops, outline_loop, murky)\n'
    L = ['judge: %d defect%s (boxes in native px, inclusive)' % (len(defects), '' if len(defects) == 1 else 's')]
    for d in defects:
        L.append('%2d. %-12s sev %.2f  box %s  %s' % (d['id'], d['kind'], d['severity'], tuple(d['box']), d['why']))
        L.append('    fix: ' + d['fix'])
    return '\n'.join(L) + '\n'

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pixelate judge', description=(__doc__ or '').split('\n\n')[1])
    ap.add_argument('frame')
    ap.add_argument('--scale', type=int, default=None, help='delivered scale (default: detected)')
    ap.add_argument('--json', action='store_true', help='print the defects as JSON')
    ap.add_argument('--overlay', default=None, help='write the frame with numbered defect boxes here')
    ap.add_argument('--ignore', default='', help='comma-separated kinds to skip, e.g. masonry for a brick town')
    ap.add_argument('--log', nargs='?', const='', default=None,
                    help='append this run to the corpus log (default .pixelate/judge-log.jsonl)')
    ap.add_argument('--note', default='', help='a note stored with the log record (draft, after fix, ...)')
    a = ap.parse_args(argv)
    if not pathlib.Path(a.frame).is_file():
        sys.exit('no such file: %s' % a.frame)
    ignore = tuple(k.strip() for k in a.ignore.split(',') if k.strip())
    bad = [k for k in ignore if k not in KINDS]
    if bad:
        ap.error('unknown kind(s): %s (kinds: %s)' % (', '.join(bad), ', '.join(KINDS)))
    rgb, s = load(a.frame, a.scale)
    defects = detect_rgb(rgb, ignore)
    if a.overlay:
        overlay(a.frame, defects, a.overlay, s)
    if a.log is not None:
        log({'type': 'judge', 'frame': os.path.abspath(a.frame), 'sha256': digest(a.frame), 'scale': s,
             'native': [int(rgb.shape[1]), int(rgb.shape[0])], 'defects': defects, 'note': a.note,
             'overlay': os.path.abspath(a.overlay) if a.overlay else None}, a.log or None)
    if a.json:
        print(json.dumps({'frame': a.frame, 'scale': s, 'defects': defects}, indent=1))
    else:
        sys.stdout.write(report(defects))
        if a.overlay:
            print('overlay: %s' % a.overlay)

if __name__ == '__main__':
    main()
