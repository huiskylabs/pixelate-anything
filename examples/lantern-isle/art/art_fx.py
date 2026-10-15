"""Smoke puffs, weather particles and water rings: several hand-drawn variants each."""
from artlib import Grid

def frames(arts, key):
    gs = []
    for a in arts:
        rows = a.strip('\n').split('\n')
        g = Grid(max(len(r) for r in rows), len(rows))
        g.stamp(a, key)
        gs.append(g)
    w = max(g.w for g in gs); h = max(g.h for g in gs)
    out = []
    for g in gs:
        n = Grid(w, h); n.paste(g, 0, 0); out.append(n)
    return out

SK = {'a': 'N1', 'b': 'N0', 'c': 'C0'}
PUFFS = [
"""
.a.
abb
""",
"""
.aa.
aabb
abbc
.bc.
""",
"""
..aa...
.aaabb.
aabbbbc
abbbbcc
.bbccc.
""",
"""
...aaa...
.aaaabbb.
aaabbbbbc
abbbbbbcc
abbbbbccc
.bbbcccc.
""",
"""
....aaa....
..aaaabbb..
.aaabbbbbb.
aaabbbbbbcc
abbbbbbbccc
.bbbbbcccc.
..bcccccc..
""",
]

PK = {'p': 'L3', 'P': 'L4', 'q': 'L2'}
PETALS = [
    ["pP", "P.\n.p", "P\np", ".P\np."],
    ["P", "pq", "q\nP", "Pq"],
    ["qP\np.", "P", ".P\nqp", "Pp"],
]
LK = {'r': 'L1', 'o': 'L2', 'y': 'L3', 'Y': 'L4', 'a': 'A1'}
LEAVES = [
    [".oy\nor.", "o.\nyo\n.r", ".ro\nyo.", "r.\noy\n.o"],
    [".yY\nyo.", "y.\nYy\n.o", ".oy\nYy.", "o.\nyY\n.y"],
    [".ra\nro.", "r.\nar\n.o", ".or\nar.", "o.\nra\n.r"],
]
FK = {'a': 'N1', 'A': 'N3', 'b': 'N2'}
FLAKE_L = [".a.\naAa\n.a.", "a.a\n.A.\na.a", "bA.\nAb.\n..."]
FLAKE_M = ["b", "A"]
CK = {'c': 'C0', 'C': 'C1', 'v': 'C2'}
SPLASH = [".C.\nC.C", "C...C\n....."]
RING_FAR = ["..C..", ".C.C.", "c...c"]
RING_NEAR = ["...C...\n.......\n.......", "..CCC..\n.C...C.\n..CCC..", ".ccccc.\nc.....c\n.ccccc."]

def export():
    out = []
    for i, p in enumerate(PUFFS):
        out.append(('sprite', 'puff%d' % i, frames([p], SK), 0, 0))
    for i, fs in enumerate(PETALS):
        out.append(('sprite', 'petal%d' % i, frames(fs, PK), 0, 0))
    for i, fs in enumerate(LEAVES):
        out.append(('sprite', 'leaf%d' % i, frames(fs, LK), 1, 1))
    out.append(('sprite', 'flake_l', frames(FLAKE_L, FK), 1, 1))
    out.append(('sprite', 'flake_m', frames(FLAKE_M, FK), 0, 0))
    out.append(('sprite', 'splash', frames(SPLASH, CK), 2, 1))
    out.append(('sprite', 'ring_far', frames(RING_FAR, CK), 2, 0))
    out.append(('sprite', 'ring_near', frames(RING_NEAR, CK), 3, 1))
    return out + export_more()


# ---------------------------------------------------------------- chimney smoke column
# a looping hand-shaped column: puffs ride a drifting path, step toward the sky
# colour as they rise instead of dithering away.
SMOKE_DRIFT = [0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 17, 18, 20, 21, 23]   # x per 2 px of rise
SMOKE_WOB = [0, 0, 1, 1, 2, 1, 1, 0, -1, -1, -1, 0, 0, 1, 1, 0, -1, 0]
def smoke_column(frames=8, height=48, width=34, spacing=4, thick=1.0):
    from artlib import disc_mask
    out = []
    for f in range(frames):
        g = Grid(width, height)
        owner = {}
        ph = f * spacing / frames
        hs = []
        i = 0
        while True:
            h = i * spacing + ph
            if h > height - 3:
                break
            hs.append(h)
            i += 1
        for h in reversed(hs):              # older puffs first; newer ones overlap them
            k = min(len(SMOKE_DRIFT) - 1, int(h / 2))
            cx = 3 + SMOKE_DRIFT[k] + SMOKE_WOB[int(h / 3) % len(SMOKE_WOB)]
            cy = height - 2 - int(round(h))
            r = max(1.6, (1.5 + h * 0.1) * thick)
            for (dx, dy) in disc_mask(r):
                owner[(cx + dx, cy + dy)] = (h, dx, dy, r)
        for (x, y), (h, dx, dy, r) in owner.items():
            if not (0 <= x < width and 0 <= y < height):
                continue
            lum = -(dx * 0.7 + dy * 0.7) / r
            right_edge = (x + 1, y) not in owner or (x, y + 1) not in owner
            if h < 14:
                v = 'N1' if lum > 0.45 else ('C0' if (right_edge and lum < -0.2) else 'N0')
            elif h < 26:
                v = 'N0' if lum > 0.1 else 'C0'
            else:
                # the plume breaks into wisps: the pattern rides with each puff and
                # thins as it climbs, in horizontal pairs of pixels
                dens = max(0.0, 1 - (h - 24) / 20)
                hv = ((int(dx) // 2 * 73856093) ^ (int(dy) * 19349663)) & 1023
                if hv / 1023 > dens:
                    continue
                v = 'C0' if h > 30 or lum < 0.2 else 'N0'
            g.set(x, y, v)
        out.append(g)
    return out

# ---------------------------------------------------------------- low mist as streaks
def mist_streaks(w, h, rows, seed, bright='N0', dim='C0'):
    """rows: list of (row, density 0..1). Streak lengths and gaps are drawn from
    a small seeded generator, then kept to clean runs of 3+ pixels."""
    from artlib import rng
    R = rng(seed)
    g = Grid(w, h)
    for (y, dens) in rows:
        x = int(R() * 10)
        while x < w:
            ln = 3 + int(R() * (8 + 30 * dens))
            gap = 3 + int(R() * (24 * (1 - dens) + 4))
            slot = bright if dens > 0.55 else dim
            # taper the streak ends with the dim tone
            for i in range(ln):
                xx = x + i
                if xx >= w:
                    break
                g.set(xx, y, dim if (i == 0 or i == ln - 1) and slot == bright else slot)
            x += ln + gap
    return g

def export_more():
    out = []
    out.append(('sprite', 'smoke_thick', smoke_column(thick=1.1, width=40), 3, 46))
    out.append(('sprite', 'smoke_mid', smoke_column(thick=0.9, width=40), 3, 46))
    out.append(('sprite', 'smoke_thin', smoke_column(thick=0.7, height=34), 3, 32))
    out.append(('sprite', 'mist_a', [mist_streaks(300, 7, [(0, 0.2), (1, 0.45), (2, 0.7), (3, 0.8), (4, 0.6), (5, 0.35), (6, 0.15)], 5)], 0, 0))
    out.append(('sprite', 'mist_b', [mist_streaks(340, 5, [(0, 0.2), (1, 0.5), (2, 0.65), (3, 0.4), (4, 0.15)], 9)], 0, 0))
    out.append(('sprite', 'mist_c', [mist_streaks(280, 6, [(0, 0.15), (1, 0.4), (2, 0.6), (3, 0.5), (4, 0.3), (5, 0.1)], 13)], 0, 0))
    out.append(('sprite', 'haze', [mist_streaks(360, 3, [(0, 0.15), (1, 0.3), (2, 0.12)], 21, bright='C0', dim='C0')], 0, 0))
    out.append(('sprite', 'haze_wide', [mist_streaks(480, 3, [(0, 0.15), (1, 0.3), (2, 0.12)], 21, bright='C0', dim='C0')], 0, 0))
    return out
