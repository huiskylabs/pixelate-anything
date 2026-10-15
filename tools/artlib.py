"""Pixel-art authoring helpers.

Sprites are grids of slot names (None = transparent). Hand-drawn ASCII parts
are stamped into grids with their own readable keys; organic shapes are
rasterised from hand-placed parameters. The result is written out as
pixel maps (ASCII rows + key) for the page, plus zoomed PNG previews.
"""
import os, re, pathlib, string
from PIL import Image

# the scene being authored (gen_sprites.py sets PIXEL_SCENE); previews go to ROOT/shots
ROOT = pathlib.Path(os.environ.get('PIXEL_SCENE', '.')).resolve()

# ---------------------------------------------------------------- palettes
def load_palettes(aliases=None):
    """Palettes from the scene's palettes.js. aliases {slot: other_slot} fills
    dynamic slots (set per frame in the page) for previews."""
    src = (ROOT / 'palettes.js').read_text()
    pals = {}
    for m in re.finditer(r'(\w+):\s*\{([^}]*)\}', src):
        name, body = m.group(1), m.group(2)
        cols = dict(re.findall(r'(\w+):\s*\'(#[0-9a-fA-F]{6})\'', body))
        if cols:
            pals[name] = cols
    if aliases is None and all('Y0' in p for p in pals.values()):
        aliases = {f + n: 'Y' + n for f in ('WL', 'LN') for n in '0123'}   # Lantern Isle's lights
    for p in pals.values():
        for a, b in (aliases or {}).items():
            if a not in p and b in p:
                p[a] = p[b]
    return pals

def hexrgb(h):
    v = int(h[1:], 16)
    return ((v >> 16) & 255, (v >> 8) & 255, v & 255)

# ---------------------------------------------------------------- grid
class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.a = [[None] * w for _ in range(h)]

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.a[y][x]
        return None

    def set(self, x, y, s):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y][x] = s

    def stamp(self, art, key, ox=0, oy=0, only_if=None):
        """Stamp ASCII art. '.' or ' ' are transparent. key maps char->slot."""
        rows = parse_art(art)
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in '. ':
                    continue
                if ch not in key:
                    raise KeyError('char %r not in key (row %d col %d)' % (ch, j, i))
                x, y = ox + i, oy + j
                if only_if is not None and self.get(x, y) not in only_if:
                    continue
                self.set(x, y, key[ch])
        return self

    def paste(self, other, ox, oy):
        for y in range(other.h):
            for x in range(other.w):
                v = other.a[y][x]
                if v is not None:
                    self.set(ox + x, oy + y, v)

    def crop(self):
        xs = [x for y in range(self.h) for x in range(self.w) if self.a[y][x] is not None]
        ys = [y for y in range(self.h) for x in range(self.w) if self.a[y][x] is not None]
        if not xs:
            return self, 0, 0
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        g = Grid(x1 - x0 + 1, y1 - y0 + 1)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g.a[y - y0][x - x0] = self.a[y][x]
        return g, x0, y0

    def copy(self):
        g = Grid(self.w, self.h)
        g.a = [r[:] for r in self.a]
        return g

    def flipx(self):
        g = Grid(self.w, self.h)
        g.a = [r[::-1] for r in self.a]
        return g

    def replace(self, frm, to):
        for y in range(self.h):
            for x in range(self.w):
                if self.a[y][x] == frm:
                    self.a[y][x] = to
        return self

    def count_orphans(self):
        """pixels whose 4 neighbours all differ (stray single pixels)."""
        n = 0
        for y in range(self.h):
            for x in range(self.w):
                v = self.a[y][x]
                if v is None:
                    continue
                same = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if self.get(x + dx, y + dy) == v)
                if same == 0:
                    n += 1
        return n


def parse_art(art):
    lines = art.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return [l.rstrip() for l in lines]

# ---------------------------------------------------------------- output
KEYCHARS = string.ascii_letters + string.digits + '#%&*+=?@^~<>:;!|_'

def to_js(name, grids, ax=0, ay=0):
    """grids: list of Grid frames (same size). returns a def(...) call."""
    if isinstance(grids, Grid):
        grids = [grids]
    used = []
    for g in grids:
        for r in g.a:
            for v in r:
                if v is not None and v not in used:
                    used.append(v)
    if len(used) > len(KEYCHARS):
        raise ValueError('too many slots in ' + name)
    key = {s: KEYCHARS[i] for i, s in enumerate(used)}
    w = max(g.w for g in grids)
    frames = []
    for g in grids:
        rows = []
        for r in g.a:
            rows.append(''.join('.' if v is None else key[v] for v in r).ljust(w, '.'))
        frames.append('\n'.join(rows))
    keystr = ', '.join("'%s': '%s'" % (c, s) for s, c in key.items())
    opt = '' if not (ax or ay) else ', { ax: %d, ay: %d }' % (ax, ay)
    body = '\n---\n'.join(frames)
    return "def('%s', { %s }, `\n%s\n`%s);\n" % (name, keystr, body, opt)


def preview(grids, pal, path, zoom=6, bg=None, cols=None):
    if isinstance(grids, Grid):
        grids = [grids]
    gw = max(g.w for g in grids)
    gh = max(g.h for g in grids)
    n = len(grids)
    cols = cols or n
    rows = (n + cols - 1) // cols
    W = (gw + 2) * cols * zoom
    H = (gh + 2) * rows * zoom
    bgc = hexrgb(bg) if bg else hexrgb(pal.get('S2', '#202020'))
    im = Image.new('RGB', (W, H), bgc)
    px = im.load()
    for idx, g in enumerate(grids):
        ox = (idx % cols) * (gw + 2) * zoom + zoom
        oy = (idx // cols) * (gh + 2) * zoom + zoom
        for y in range(g.h):
            for x in range(g.w):
                v = g.a[y][x]
                if v is None:
                    continue
                c = hexrgb(pal.get(v, '#ff00ff'))
                for yy in range(zoom):
                    for xx in range(zoom):
                        px[ox + x * zoom + xx, oy + y * zoom + yy] = c
    im.save(path)
    return path

# ---------------------------------------------------------------- shapes
def disc_mask(r):
    """clean pixel-art disc of radius r (integer or .5), as set of (dx,dy) offsets."""
    pts = set()
    R = r + 0.35
    n = int(r) + 2
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            if dx * dx + dy * dy <= R * R:
                pts.add((dx, dy))
    return pts

def line(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy
    return pts

BAYER4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]
def bayer(x, y):
    return BAYER4[((y & 3) << 2) | (x & 3)]

def rng(seed):
    """tiny deterministic generator for authoring variety."""
    s = [seed & 0xffffffff or 1]
    def r():
        x = s[0]
        x ^= (x << 13) & 0xffffffff
        x ^= x >> 17
        x ^= (x << 5) & 0xffffffff
        s[0] = x & 0xffffffff
        return s[0] / 4294967296.0
    return r
