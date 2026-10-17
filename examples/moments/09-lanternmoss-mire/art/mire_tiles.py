"""Mire tiles, generated: moss-on-peat corner autotiles (16 x 3 variants), a peat bank over water
(16, the water left transparent so the animated water shows through), bog water (2 variants x 4
frames) and the boardwalk.

Corner sets: tile index = NW*8 + NE*4 + SW*2 + SE, 1 = the second terrain (moss / peat).
The shape blends the four corner values across the tile and is roughened by noise that fades to
zero at the tile edges, so neighbours always meet. Texture is placed (clods, tufts, cushions),
never per-pixel speckle, and stays off the edges.

Edges, light from the upper left, 3/4 top-down:
  moss   lit fringe (moss3) on the north and west edges, dark rim (moss1) on the east, a front lip
         on the south edge with a shadow (peat0) on the peat below it.
  bank   lit rim (peat2) on the north and west, dark rim on the east; the south edge shows the
         bank face (lip, two rows of peat0 with roots) and a dark wet line in the water below it;
         short water2 laps along the shore (these glow at night).
Water: ripples are short crests (water2) over a trough (water0) that slide 4 px a frame:
16 px over 4 frames, an exact wrap.
"""
from mire_kit import h32
from artlib import Grid

T = 16


def _vnoise(x, y, seed, cell=5):
    """smooth value noise on a coarse lattice: the edge wobbles in runs, not single pixels"""
    gx, gy = x / cell, y / cell
    x0, y0 = int(gx // 1), int(gy // 1)
    fx, fy = gx - x0, gy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = h32(x0, y0, seed), h32(x0 + 1, y0, seed)
    c, d = h32(x0, y0 + 1, seed), h32(x0 + 1, y0 + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _bilinear(mask, u, v):
    nw, ne, sw, se = (mask >> 3) & 1, (mask >> 2) & 1, (mask >> 1) & 1, mask & 1
    return nw * (1 - u) * (1 - v) + ne * u * (1 - v) + sw * (1 - u) * v + se * u * v


def blend(mask, x, y, seed, amp=0.34, cell=5):
    u = min(1.0, max(0.0, (x + 0.5) / T)); v = min(1.0, max(0.0, (y + 0.5) / T))
    if mask in (6, 9):                       # saddles: the union of the two single-corner shapes
        f = max(_bilinear(m, u, v) for m in ((4, 2) if mask == 6 else (8, 1)))
    else:
        f = _bilinear(mask, u, v)
    fade = min(1.0, 4 * min(u, 1 - u, v, 1 - v))
    return f + (_vnoise(x, y, seed, cell) - 0.5) * amp * fade


def shape(mask, seed, amp, x0=-1, x1=T + 1, y0=-1, y1=T + 4, cell=5):
    """the boolean terrain over a margin around the tile, cleaned of 1 px notches and islands
    (only away from the tile edges, so neighbours still meet exactly)"""
    M = {(x, y): blend(mask, x, y, seed, amp, cell) > 0.5 for x in range(x0, x1) for y in range(y0, y1)}
    for _ in range(2):
        N = dict(M)
        for y in range(1, T - 1):
            for x in range(1, T - 1):
                same = sum(M.get((x + dx, y + dy), M[(x, y)]) == M[(x, y)]
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if same <= 1:
                    N[(x, y)] = not M[(x, y)]
        M = N
    return lambda x, y: M.get((x, y), M.get((min(max(x, x0), x1 - 1), min(max(y, y0), y1 - 1))))


def peat_texture(g, region, seed):
    """placed clods on the peat: a lit cap over a dark base, 2-3 per tile, off the edges"""
    for i in range(3):
        x = 2 + int(h32(i, seed, 31) * 11); y = 2 + int(h32(seed, i, 37) * 11)
        if all(region(x + dx, y + dy) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)):
            g.set(x, y, 'peat2'); g.set(x + 1, y, 'peat2' if i % 2 else 'peat1')
            g.set(x, y + 1, 'peat0'); g.set(x + 1, y + 1, 'peat0')
    if h32(seed, 8, 53) < 0.45:                # reed stubble: two short ticks, lit tip over a dark base
        x = 2 + int(h32(seed, 9, 59) * 10); y = 2 + int(h32(seed, 10, 61) * 10)
        if all(region(x + dx, y + dy) for dx in range(-1, 4) for dy in range(-1, 3)):
            g.set(x, y, 'reed1'); g.set(x, y + 1, 'reed0'); g.set(x + 2, y + 1, 'reed1'); g.set(x + 2, y + 2, 'reed0')
    # one thin root, a 3 px stepped dash, sometimes
    if h32(seed, 5, 41) < 0.5:
        x = 3 + int(h32(seed, 6, 43) * 8); y = 3 + int(h32(seed, 7, 47) * 9)
        if all(region(x + dx, y + dy) for dx in range(-1, 5) for dy in (-1, 0, 1, 2)):
            g.set(x, y, 'peat0'); g.set(x + 1, y, 'peat0'); g.set(x + 2, y + 1, 'peat0'); g.set(x + 3, y + 1, 'peat0')


def moss_texture(g, region, seed):
    """placed tufts (a straw tip over a dark root) and one cushion, off the edges; straw (reed1)
    rather than the lit moss tip, so the interior stays dark at night"""
    for i in range(4):
        x = 2 + int(h32(i, seed, 3) * 12); y = 2 + int(h32(seed, i, 5) * 11)
        if all(region(x + dx, y + dy) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)):
            g.set(x + (i % 2), y, 'reed1')
            g.set(x, y + 1, 'moss1'); g.set(x + 1, y + 1, 'moss1')
    if h32(seed, 9, 11) < 0.7:
        x = 3 + int(h32(seed, 10, 13) * 8); y = 3 + int(h32(seed, 12, 17) * 8)
        if all(region(x + dx, y + dy) for dx in range(-1, 6) for dy in range(-1, 5)):
            for dx, dy, s in ((1, 0, 'reed1'), (2, 0, 'reed1'), (3, 0, 'moss2'),
                              (0, 1, 'reed1'), (1, 1, 'moss2'), (2, 1, 'moss2'), (3, 1, 'moss2'), (4, 1, 'moss1'),
                              (0, 2, 'moss2'), (1, 2, 'moss2'), (2, 2, 'moss1'), (3, 2, 'moss1'), (4, 2, 'moss0'),
                              (1, 3, 'moss0'), (2, 3, 'moss0'), (3, 3, 'moss0')):
                g.set(x + dx, y + dy, s)


def moss_tile(mask, var):
    seed = 100 + mask * 7 + var * 131
    g = Grid(T, T)
    moss = shape(mask, 900 + var * 17 + mask, 0.5, cell=7)
    peat = lambda x, y: not moss(x, y)
    for y in range(T):
        for x in range(T):
            if moss(x, y):
                if not moss(x, y + 1):
                    s = 'moss3'                              # lit lip where the mat overhangs
                elif not moss(x, y - 1) or not moss(x - 1, y):
                    s = 'moss3'                              # lit fringe, north and west
                elif not moss(x + 1, y):
                    s = 'moss1'                              # shade rim, east
                else:
                    s = 'moss2'
            else:
                s = 'peat0' if moss(x, y - 1) else 'peat1'   # shadow under the lip
            g.set(x, y, s)
    peat_texture(g, lambda x, y: peat(x, y) and not moss(x, y - 1) and not moss(x, y - 2), seed)
    inner = lambda x, y: moss(x, y) and moss(x, y - 1) and moss(x - 1, y) and moss(x + 1, y) and moss(x, y + 1)
    moss_texture(g, lambda x, y: all(inner(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)), seed)
    # glow speckles: single lit pixels 2-3 px inside the fringe, a few per tile (clusters at night)
    n = 0
    for y in range(1, T - 1):
        for x in range(1, T - 1):
            if n >= 3 or g.a[y][x] != 'moss2' or not inner(x, y):
                continue
            near = any(not moss(x + dx, y + dy) for dx in range(-3, 4) for dy in range(-3, 4))
            if near and h32(x, y, seed + 77) < 0.16:
                g.set(x, y, 'moss3'); n += 1
    return g


def _fade(x, y):
    u = min(1.0, max(0.0, (x + 0.5) / T)); v = min(1.0, max(0.0, (y + 0.5) / T))
    return min(1.0, 4 * min(u, 1 - u, v, 1 - v))


def bank_tile(mask, var=0):
    seed = 500 + mask * 7 + var * 131
    fs = 700 + mask + var * 29
    g = Grid(T, T)
    land = shape(mask, fs, 0.26, cell=7)
    # shallows: the same field at a lower threshold whose margin wobbles (but not at the tile
    # edges, where the field is shared with the neighbour), so the band hugs the shore seamlessly
    raw = {(x, y): blend(mask, x, y, fs, 0.26, 7) > 0.5 - (0.27 + (_vnoise(x, y, 1300 + var, 4) - 0.5) * 0.26 * _fade(x, y))
           for x in range(-1, T + 1) for y in range(-1, T + 1)}
    for _ in range(2):                                   # no 1 px holes or crumbs, edges untouched
        nxt = dict(raw)
        for y in range(1, T - 1):
            for x in range(1, T - 1):
                if sum(raw[(x + dx, y + dy)] == raw[(x, y)] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) <= 1:
                    nxt[(x, y)] = not raw[(x, y)]
        raw = nxt
    shallow = lambda x, y: raw.get((x, y), False)
    for y in range(T):
        for x in range(T):
            if land(x, y):
                below = [land(x, y + k) for k in (1, 2, 3)]
                if not below[0]:
                    s = 'peat0'                              # bank face, bottom row
                elif not below[1]:
                    s = 'peat0' if h32(x, y, seed) > 0.25 else 'peat1'   # face with a root
                elif not below[2]:
                    s = 'peat2'                              # lip: the lit edge of the top
                elif not land(x, y - 1) or not land(x - 1, y):
                    s = 'peat2'                              # lit rim, north and west
                elif not land(x + 1, y):
                    s = 'peat0'                              # shade rim, east
                else:
                    s = 'peat1'
                g.set(x, y, s)
            elif land(x, y - 1):
                g.set(x, y, 'water0')                        # dark wet line under the face
            elif shallow(x, y):
                s = 'shallow'
                if land(x, y - 2) and h32(x // 3, y, seed + 3) < 0.6:
                    s = 'lap'                                # a lap of light along the face
                elif (land(x, y + 1) or land(x + 1, y) or land(x - 1, y)) and h32(x // 3, y // 2, seed + 4) < 0.5:
                    s = 'lap'                                # laps against the far shore
                g.set(x, y, s)
    peat_texture(g, lambda x, y: land(x, y) and all(land(x, y + k) for k in (1, 2, 3, 4))
                 and land(x, y - 1) and land(x - 1, y) and land(x + 1, y), seed)
    return g


def deep_tile(mask):
    """deep channels: water0 where the corners say deep, with two faint long crests; transparent
    elsewhere so the animated water shows"""
    g = Grid(T, T)
    deep = shape(mask, 1600 + mask, 0.3, cell=6)
    for y in range(T):
        for x in range(T):
            if deep(x, y):
                g.set(x, y, 'water0')
    for i, (x0, y, n) in enumerate(((2, 4, 5), (8, 11, 4))):
        if all(deep(x0 + k, y) and deep(x0 + k, y - 1) and deep(x0 + k, y + 1) for k in range(-1, n + 1)):
            for k in range(n):
                g.set(x0 + k, y, 'water1')
    return g


RIPPLES = [  # (x0, y, length) per water variant; each ripple: crest over a trough one row down
    [],                                  # calm
    [(3, 6, 5)],                         # one crest
    [(9, 3, 4), (1, 11, 3)],             # two crests
    [(5, 9, 7)],                         # one long crest
]


def water(var, frame):
    g = Grid(T, T)
    for y in range(T):
        for x in range(T):
            g.set(x, y, 'water1')
    for i, (x0, y, n) in enumerate(RIPPLES[var]):
        for dx in range(n):
            x = (x0 + dx + frame * 4) % T
            g.set(x, y, 'water2')
            if 0 < dx < n - 1:
                g.set((x + 1) % T, (y + 1) % T, 'water0')
    return g


# ---------------------------------------------------------------------------- boardwalk
# characters: o ol, B wood2 (lit board end), b wood1 (board), d wood0 (seam, face), s water0 (shadow)
#             w water2 (ring at a pile)
BW_KEY = {'o': 'ol', 'B': 'wood2', 'b': 'wood1', 'd': 'wood0', 's': 'water0', 'w': 'water2'}

H_A = """
................
................
................
oooooooooooooooo
BBBdBBBBdBBBdBBB
bbbdbbbbdbbbdbbb
bbbdbbbbdbbdbbbb
bbbdbdbbdbbbdbbb
bbbdbbbbdbbbdbbb
bbbdbbbbdbbbdbbb
bbbdbbbbdbbbdbbb
dddddddddddddddd
oooooooooooooooo
.Bd.sssssBd.ssss
.Bd.ssss.Bd.....
wwww....wwww....
"""
H_B = """
................
................
................
oooooooooooooooo
BBdBBBBdBBBdBBBB
bbdbbbbdbbbdbbbb
bbdbbbbdbbbdbbbb
bbdbbbbdbdbdbbbb
bbdbbbbdbbbdbbbb
bbdbbbbdbbbdbbbb
bbdbbbbdbbbdbbbb
dddddddddddddddd
oooooooooooooooo
ssss.Bd.sssss.Bd
.....Bd.ssss..Bd
....wwww....wwww
"""
H_BROKEN = """
................
................
................
oooooooo.ooooooo
BBBdBBBo.oBBdBBB
bbbdbbbo.Bbbdbbb
bbbdbbbo..Bbdbbb
bbbdbbbo..obdbbb
bbbdbbbo.ddddbbb
bbbdbbbo...obdbb
bbbdbbbo....obbb
ddddddddddoddddd
ooooooooo.oooooo
.Bd.sssssBd.ssss
.Bd.ssss.Bd.....
wwww....wwww....
"""
H_END_W = """
................
................
................
....oooooooooooo
...oBBBBdBBBdBBB
...oBbbbdbbbdbbb
...oBbbbdbbbdbbb
...oBbbbdbbbdbbb
...oBbbbdbbbdbbb
...oBbbbdbbbdbbb
...oBbbbdbbbdbbb
...odddddddddddd
....oooooooooooo
....Bd..ssssBd.s
....Bd...sss.Bd.
...wwww....wwww.
"""
V_A = """
..oBbbbbbbbbdo..
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbdbbbdos.
..oBbbbbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
.BdBbbbbbbbbdos.
.Bdddddddddddos.
..oBbbbbbbbbdos.
..oBbbdbbbbbdos.
..oBbbbbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
"""
V_B = """
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbbbbdbos.
..oBbbbbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
..oBbbdbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
"""
V_END_N = """
................
................
................
...oooooooooo...
..oBBBBBBBBBBo..
..oBbbbbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
..oBbbbbbbbbdos.
..oBbbdbbbbbdos.
..oddddddddddos.
..oBbbbbbbbbdos.
"""
LANDING = """
..oBbbbbbbbbdo..
..oddddddddddo..
ooodBbbbbbbbdooo
BBBdBbbbbbbbdBBB
bbbdBbbbbbbbdbbb
bbbdddddddddddbb
bbbdBbbbbbbbdbbb
bbbdBbbbbbbbdbbb
bbbdBbbbbbbbdbbb
bbbdddddddddddbb
bbbdBbbbbbbbdbbb
dddddddddddddddd
oooooooooooooooo
.Bd.sssssBd.ssss
.Bd.ssss.Bd.....
wwww....wwww....
"""


def bw(art):
    from mire_kit import grid_from
    return grid_from(art, BW_KEY, T, T)


def boardwalk():
    def flip(g):
        out = Grid(T, T)
        for y in range(T):
            for x in range(T):
                v = g.a[y][T - 1 - x]
                # mirrored end: the lit board end stays lit, the post keeps its lit side left
                out.a[y][x] = v
        return out
    end_w = bw(H_END_W)
    end_e = flip(end_w)
    # keep light from the upper left on the mirrored end: its outer board end turns to shade
    for y in range(T):
        for x in range(T):
            if end_e.a[y][x] == 'wood2' and 4 <= y <= 10 and x >= 11:
                end_e.a[y][x] = 'wood0'
    v_end_s = bw(V_A)
    for y in range(11, 16):
        v_end_s.a[y] = [None] * T
    front = bw(H_A)
    for y in (11, 12):
        for x in range(2, 14):
            v_end_s.a[y][x] = front.a[y][x]
    v_end_s.a[11][2] = 'ol'; v_end_s.a[11][13] = 'ol'
    v_end_s.a[12][2] = 'ol'; v_end_s.a[12][13] = 'ol'
    for y, row in ((13, '...Bd....Bd.s...'), (14, '...Bd....Bd.....'), (15, '..wwww..wwww....')):
        for x, c in enumerate(row):
            v_end_s.a[y][x] = BW_KEY[c] if c != '.' else None
    return [bw(H_A), bw(H_B), bw(H_BROKEN), end_w, end_e, bw(V_A), bw(V_B), bw(V_END_N), v_end_s, bw(LANDING)]


BOARDWALK_FRAMES = ['h_a', 'h_b', 'h_broken', 'h_end_w', 'h_end_e', 'v_a', 'v_b', 'v_end_n', 'v_end_s', 'landing']


def export():
    out = []
    for var, name in enumerate(('moss_peat', 'moss_peat_b', 'moss_peat_c')):
        out.append(('sprite', name, [moss_tile(m, var) for m in range(16)], 0, 0, {'tile': T}))
    out.append(('sprite', 'deep_water', [deep_tile(m) for m in range(16)], 0, 0, {'tile': T}))
    for var, name in enumerate(('peat_bank', 'peat_bank_b', 'peat_bank_c')):
        out.append(('sprite', name, [bank_tile(m, var) for m in range(16)], 0, 0, {'tile': T}))
    # bog water: 4 variants x 4 frames in one strip (variant v = frames 4v..4v+3)
    out.append(('sprite', 'bog_water', [water(v, f) for v in range(4) for f in range(4)], 0, 0,
                {'fps': 4, 'tile': T, 'tags': {'calm': (0, 3), 'ripple': (4, 7), 'ripples': (8, 11), 'long': (12, 15)}}))
    out.append(('sprite', 'boardwalk', boardwalk(), 0, 0,
                {'tile': T, 'tags': {n: (i, i) for i, n in enumerate(BOARDWALK_FRAMES)}}))
    return out
