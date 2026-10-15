"""Colour maths shared by the palette and pixelate tools (numpy only).

OKLab is used for every distance and average: it is perceptually even, so
clustering and nearest-colour matching pick what an eye would pick.
"""
import json, pathlib, re
import numpy as np

KIT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- conversions
def _lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def _gam(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255.0

def rgb_to_oklab(rgb):
    """rgb: (..., 3) 0..255 -> (..., 3) OKLab"""
    r, g, b = [_lin(np.asarray(rgb, float)[..., i]) for i in range(3)]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], -1)

def oklab_to_rgb(lab):
    lab = np.asarray(lab, float)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return np.stack([_gam(r), _gam(g), _gam(bb)], -1)

def oklch(L, C, h_deg):
    h = np.radians(h_deg)
    return np.array([L, C * np.cos(h), C * np.sin(h)])

def lch_of(lab):
    lab = np.asarray(lab, float)
    return lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360

def in_gamut(lab):
    l, a, b = lab
    lms = [(l + 0.3963377774 * a + 0.2158037573 * b) ** 3, (l - 0.1055613458 * a - 0.0638541728 * b) ** 3,
           (l - 0.0894841775 * a - 1.2914855480 * b) ** 3]
    r = 4.0767416621 * lms[0] - 3.3077115913 * lms[1] + 0.2309699292 * lms[2]
    g = -1.2684380046 * lms[0] + 2.6097574011 * lms[1] - 0.3413193965 * lms[2]
    bb = -0.0041960863 * lms[0] - 0.7034186147 * lms[1] + 1.7076147010 * lms[2]
    return all(-1e-4 <= v <= 1 + 1e-4 for v in (r, g, bb))

def clamp_chroma(L, C, h):
    """largest chroma <= C that is displayable at this lightness and hue"""
    lo, hi = 0.0, C
    if in_gamut(oklch(L, C, h)):
        return C
    for _ in range(24):
        mid = (lo + hi) / 2
        if in_gamut(oklch(L, mid, h)): lo = mid
        else: hi = mid
    return lo

# ---------------------------------------------------------------- hex helpers
def hex_to_rgb(h):
    h = h.strip().lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def rgb_to_hex(c):
    return '#%02x%02x%02x' % tuple(int(round(max(0, min(255, v)))) for v in c)

# ---------------------------------------------------------------- clustering
def kmeans(lab, k, weights=None, iters=24, seed=1):
    """k-means++ in OKLab. lab: (N, 3). returns centres (k, 3)."""
    rng = np.random.default_rng(seed)
    n = len(lab)
    if n > 60000:
        idx = rng.choice(n, 60000, replace=False)
        lab = lab[idx]; weights = None if weights is None else weights[idx]; n = 60000
    w = np.ones(n) if weights is None else weights
    centres = [lab[rng.choice(n, p=w / w.sum())]]
    d2 = ((lab - centres[0]) ** 2).sum(1)
    for _ in range(1, k):
        p = d2 * w
        if p.sum() <= 0: break
        centres.append(lab[rng.choice(n, p=p / p.sum())])
        d2 = np.minimum(d2, ((lab - centres[-1]) ** 2).sum(1))
    C = np.array(centres)
    for _ in range(iters):
        lab_idx = nearest(lab, C)
        newC = C.copy()
        for j in range(len(C)):
            m = lab_idx == j
            if m.any():
                newC[j] = (lab[m] * w[m, None]).sum(0) / w[m].sum()
        if np.abs(newC - C).max() < 1e-5:
            C = newC; break
        C = newC
    return C

def nearest(lab, pal_lab):
    """index of the nearest palette colour for every row of lab"""
    lab = np.asarray(lab, float).reshape(-1, 3)
    out = np.empty(len(lab), np.int32)
    for i in range(0, len(lab), 200000):
        d = ((lab[i:i + 200000, None, :] - pal_lab[None, :, :]) ** 2).sum(-1)
        out[i:i + 200000] = d.argmin(1)
    return out

# ---------------------------------------------------------------- palette files
def sort_palette(hexes):
    """group into hue families, each dark -> light; greys first"""
    lab = rgb_to_oklab(np.array([hex_to_rgb(h) for h in hexes]))
    L, C, H = lch_of(lab)
    keys = []
    for i in range(len(hexes)):
        fam = -1 if C[i] < 0.03 else int(((H[i] + 15) % 360) // 30)
        keys.append((fam, L[i]))
    return [hexes[i] for i in sorted(range(len(hexes)), key=lambda i: keys[i])]

def load_palette(src):
    """hex list or {slot: hex} from: a preset name, .hex/.txt, .gpl, .json, an image of swatches, or 'a,b,c'"""
    p = pathlib.Path(src)
    if not p.exists():
        pre = KIT / 'palettes' / (src + '.hex')
        if pre.exists():
            p = pre
        elif ',' in src or src.startswith('#'):
            return [h if h.startswith('#') else '#' + h for h in src.split(',')]
        else:
            raise SystemExit('no palette file or preset named %r (see palettes/)' % src)
    t = p.suffix.lower()
    if t in ('.hex', '.txt'):
        return ['#' + l.strip().lstrip('#')[:6] for l in p.read_text().splitlines() if re.match(r'^\s*#?[0-9a-fA-F]{6}', l)]
    if t == '.gpl':
        out = []
        for l in p.read_text().splitlines():
            m = re.match(r'^\s*(\d+)\s+(\d+)\s+(\d+)', l)
            if m: out.append(rgb_to_hex([int(x) for x in m.groups()]))
        return out
    if t == '.json':
        d = json.loads(p.read_text())
        return d.get('colors', d) if isinstance(d, dict) else d
    if t in ('.png', '.gif', '.bmp'):
        from PIL import Image
        im = np.array(Image.open(p).convert('RGBA')).reshape(-1, 4)
        im = im[im[:, 3] > 0][:, :3]
        uniq = []
        for c in map(tuple, im):
            h = rgb_to_hex(c)
            if h not in uniq: uniq.append(h)
            if len(uniq) > 256: break
        return uniq
    raise SystemExit('unknown palette format: ' + src)

def palette_list(pal):
    return list(pal.values()) if isinstance(pal, dict) else list(pal)
