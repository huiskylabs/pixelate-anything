"""Lofi weather particles baked for the JS engine: petals, falling leaves, snow, drizzle and fireflies.

A lofi scene runs in the JS engine, so Python motion cannot run at play time: it must be baked.
Each helper here returns a Field: small hand-keyed slot drawings (artlib.Grid frames) plus
per-particle tables on the engine's 15 Hz particle clock (k2 = k >> 1). Every period divides
T2 = TICKS / 2, so step T2 is step 0 exactly. Field.export() hands gen_sprites the drawings and
one const table; the engine draws it with drawBaked (ENGINE_JS) inside sceneParticles.

    import particles as pt
    T2 = 5760 // 2                                              # TICKS / 2 (cycle 96, grand 2)
    pet = pt.petals((130, 92, 210, 138), n=22, T2=T2, floor=232)       # downwind from a canopy
    lea = pt.leaves((120, 96, 200, 140), n=18, T2=T2)                  # tumbling, gusty
    sno = pt.snow(320, 180, T2=T2, land=(124, 184))                    # three depths
    dri = pt.drizzle(320, 180, T2=T2)                                  # far dots, near streaks
    ffl = pt.fireflies([(114, 150), (150, 162), (210, 140)], T2=T2)    # wander and blink
    def export():                                               # an art module (art/art_fx.py)
        return pet.export('PETALS') + sno.export('SNOW') + ffl.export('FIREFLIES')
    # fx.js, in sceneParticles: drawBaked(PETALS, k >> 1, dens, out, D);
    g = pet.grid(40, 320, 180)                                  # the layer at step 40, for a preview
    pet.draw(c, 40)                                             # or into a Canvas / slot grid

Learned from Lantern Isle (this repo, examples/lantern-isle/fx.js): two- to five-pixel hand
drawings tumbling through four keys, a stepped sway table, spawns hashed per generation from
the particle index, depth layers that differ in size, tone, speed and sway, and periods that
divide TICKS / 2. The hash is the engine's own (core.js hash/hash2/hash3), ported bit for bit.
"""
import math, pathlib, sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import anim
from artlib import Grid
from sprite import paste as _paste

__all__ = ['Field', 'petals', 'leaves', 'snow', 'drizzle', 'fireflies', 'fit_period',
           'hash1', 'hash2', 'hash3', 'ENGINE_JS', 'SWAY', 'FIREFLY_PATH', 'FIREFLY_BLINK']

# ---------------------------------------------------------------- the engine's hash (core.js)
_M = 0xFFFFFFFF

def _imul(a, b):
    return ((a & _M) * (b & _M)) & _M

def hash1(n):
    """the engine's hash(n) -> [0, 1), bit for bit (engine/core.js)"""
    n = (int(n) & _M) ^ 0x9e3779b9
    n = _imul(n ^ (n >> 16), 0x85ebca6b)
    n = _imul(n ^ (n >> 13), 0xc2b2ae35)
    n ^= n >> 16
    return (n & _M) / 4294967296.0

def hash2(a, b):
    """the engine's hash2(a, b) -> [0, 1)"""
    return hash1(_imul(int(a), 73856093) ^ _imul(int(b), 19349663))

def hash3(a, b, c):
    """the engine's hash3(a, b, c) -> [0, 1)"""
    return hash1(_imul(int(a), 73856093) ^ _imul(int(b), 19349663) ^ _imul(int(c), 83492791))

def _divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]

def fit_period(T2, want, up=True):
    """the divisor of T2 closest to `want` (the smallest one >= want with up=True): a particle
    period that keeps the loop exact"""
    ds = _divisors(int(T2))
    if up:
        big = [d for d in ds if d >= want]
        return big[0] if big else ds[-1]
    return min(ds, key=lambda d: (abs(d - want), d))

def _gens(T2, P, cap):
    """distinct spawns stored per particle: the largest divisor of T2 / P not above cap"""
    return max(d for d in _divisors(T2 // P) if d <= max(1, cap))

# a stepped sideways sway, advanced every 2 steps (7.5 fps on the particle clock)
SWAY = (0, 0, 1, 1, 2, 2, 2, 1, 0, 0, -1, -1, -2, -2, -2, -1)

# the engine side: paste once (Field.export emits it as a const) and call it in sceneParticles
ENGINE_JS = """(F, k2, dens, out, D) => {
  for (let j = 0; j < F.per.length; j++) {
    if (F.gate[j] > dens) continue;
    const P = F.per[j], s = F.start[j], t = (k2 % F.T2) + F.off[j];
    const age = t % P, g = (Math.floor(t / P) % (s.length / 3)) * 3;
    const tr = F.tracks[s[g + 2]], f = tr[age * 3 + 2];
    if (f >= 0) putSpr(out, D, SPR[F.spr[j]], s[g] + tr[age * 3], s[g + 1] + tr[age * 3 + 1], f);
  }
}"""

def _frames(arts, key, w=None, h=None):
    """hand ASCII drawings -> same-size artlib.Grid frames (top-left aligned)"""
    rows = [a.strip('\n').split('\n') for a in arts]
    w = w or max(len(r) for rs in rows for r in rs)
    h = h or max(len(rs) for rs in rows)
    out = []
    for a in arts:
        g = Grid(w, h)
        g.stamp(a, key)
        out.append(g)
    return out

# ---------------------------------------------------------------- the baked field
class Field:
    """baked particles for the engine: drawings plus per-particle tables on the 15 Hz clock.
    sprites {name: ([Grid frames], ax, ay)}; tracks: list of int arrays (P, 3) of (dx, dy, frame),
    frame -1 = hidden; per[j] the period of particle j (divides T2), off[j] its phase, gate[j] the
    dens it needs (it fades out across a phase dissolve), spr[j] its sprite name, start[j] a list
    of (x, y, track) spawns, one per generation (the list repeats; its length divides T2 / per[j])."""

    def __init__(self, T2, sprites, tracks, per, off, gate, spr, start):
        self.T2, self.sprites, self.tracks = int(T2), sprites, tracks
        self.per, self.off, self.gate, self.spr, self.start = per, off, gate, spr, start
        self._np = {}
        anim.check_periods(self.T2, {'p%d' % j: p * len(start[j]) for j, p in enumerate(per)})

    def __len__(self):
        return len(self.per)

    def at(self, k2, dens=1.0):
        """[(x, y, sprite, frame)] drawn at particle step k2, exactly what drawBaked draws"""
        out = []
        k2 = int(k2) % self.T2
        for j, P in enumerate(self.per):
            if self.gate[j] > dens:
                continue
            t = k2 + self.off[j]
            s = self.start[j]
            x, y, ti = s[(t // P) % len(s)]
            dx, dy, f = self.tracks[ti][t % P]
            if f >= 0:
                out.append((x + int(dx), y + int(dy), self.spr[j], int(f)))
        return out

    def _arr(self, name, f):
        k = (name, f)
        if k not in self._np:
            frames = self.sprites[name][0]
            g = frames[f % len(frames)]
            self._np[k] = np.array(g.a, dtype=object).reshape(g.h, g.w)
        return self._np[k]

    def draw(self, target, k2, dens=1.0, ox=0, oy=0):
        """paste the particles at step k2 into a Canvas, a slot array or an artlib.Grid (offset
        ox, oy, like the engine's setOrigin) and return it"""
        for x, y, name, f in self.at(k2, dens):
            _, ax, ay = self.sprites[name]
            _paste(target, self._arr(name, f), x + ox - ax, y + oy - ay)
        return target

    def grid(self, k2, w, h, dens=1.0):
        """the particle layer at step k2 as an artlib.Grid (None = clear), for previews"""
        return self.draw(Grid(w, h), k2, dens)

    def to_js(self):
        """the JS literal drawBaked reads: { T2, spr, per, off, gate, tracks, start }"""
        L = lambda xs: '[' + ','.join(str(int(v)) for v in xs) + ']'
        tracks = ','.join(L(np.asarray(t).reshape(-1)) for t in self.tracks)
        start = ','.join(L([v for sp in s for v in sp]) for s in self.start)
        return ('{ T2: %d, spr: [%s], per: %s, off: %s, gate: [%s],\n  tracks: [%s],\n  start: [%s] }'
                % (self.T2, ','.join("'%s'" % n for n in self.spr), L(self.per), L(self.off),
                   ','.join('%.3f' % g for g in self.gate), tracks, start))

    def export(self, const):
        """gen_sprites items: every drawing as ('sprite', ...), the table as const `const`, and
        drawBaked (ENGINE_JS) once; return it from an art module's export()"""
        out = [('sprite', n, fr, ax, ay) for n, (fr, ax, ay) in self.sprites.items()]
        return out + [('const', const, self.to_js()), ('const', 'drawBaked', ENGINE_JS)]

def _build(T2, sprites, n, per_of, spr_of, track, nvar, spawn, seed, gens):
    """shared assembly: track(P, v) -> (P, 3) table; spawn(j, gen, P, fits) -> (x, y, v)"""
    tracks, index = [], {}
    def tid(P, v):
        if (P, v) not in index:
            index[(P, v)] = len(tracks)
            tracks.append(np.asarray(track(P, v), dtype=np.int16).reshape(P, 3))
        return index[(P, v)]
    per, off, gate, spr, start = [], [], [], [], []
    for j in range(n):
        P = int(per_of(j))
        if T2 % P:
            raise ValueError('period %d does not divide T2=%d' % (P, T2))
        G = _gens(T2, P, gens)
        s = []
        for gen in range(G):
            x, y, v = spawn(j, gen, P)
            s.append((int(x), int(y), tid(P, v % nvar)))
        per.append(P)
        off.append(int(hash2(j, seed) * P))
        gate.append(hash2(j, seed + 1))
        spr.append(spr_of(j))
        start.append(s)
    return Field(T2, sprites, tracks, per, off, gate, spr, start)

def _pick(variants, j, gen, seed, room, drop_of):
    """a track variant for this spawn, one whose drop fits `room` when a floor is set"""
    v = int(hash3(j, gen, seed) * variants)
    if room is None:
        return v
    fits = [u for u in range(variants) if drop_of(u) <= room]
    if not fits:
        return min(range(variants), key=drop_of)
    return fits[v % len(fits)]

# ---------------------------------------------------------------- petals
PETAL_KEY = ('P', 'p', 'q')            # lit, mid, shade
PETAL_ARTS = (
    ('PP', 'P.\n.p', 'p', '.P\np.'),               # flat, tilt, edge on, tilt back
    ('Pp', 'p\nq', 'q', 'q\np'),
    ('PP\n.q', '.P\npq', 'Pq', 'p\nq'),             # a curled petal, three pixels when flat
)

def petals(source=(130, 92, 210, 138), n=22, periods=(120, 144, 180, 240), wind=(60, 210),
           drop=(40, 110), floor=None, T2=2880, slots=('L4', 'L3', 'L2'), name='petal',
           variants=6, rest=0.0, sway=1.0, seed=1401, gens=12):
    """blossom petals drifting downwind from a canopy, tumbling through four keys (Lantern Isle's
    spring petals). source: the spawn box (x0, y0, x1, y1); wind: the (min, max) px a petal
    travels sideways over its period (negative blows left); drop: the (min, max) px it falls;
    floor: the lowest y a petal may reach (tracks that would pass it are not picked for that
    spawn); rest: the hidden fraction at the end of each period (gaps between petals); slots:
    (lit, mid, shade). Three drawings, `name`0..2, 4 frames each, keyed every 4 steps."""
    key = dict(zip(PETAL_KEY, slots))
    sprites = {'%s%d' % (name, i): (_frames(a, key, 2, 2), 0, 0) for i, a in enumerate(PETAL_ARTS)}
    def par(P, v, k):
        return hash3(P, v, seed + 10 + k)
    def drop_of(P):
        return lambda v: drop[0] + (drop[1] - drop[0]) * par(P, v, 1) + 1
    def track(P, v):
        dist = wind[0] + (wind[1] - wind[0]) * par(P, v, 0)
        dr = drop_of(P)(v) - 1
        ph = int(par(P, v, 2) * len(SWAY))
        rows = []
        for age in range(P):
            u = age / P
            sw = SWAY[((age >> 1) + ph) % len(SWAY)] * sway
            f = ((age >> 2) + v) % 4 if u < 1 - rest else -1
            rows.append((math.floor(dist * u + sw), math.floor(dr * u + abs(sw) * 0.5), f))
        return rows
    x0, y0, x1, y1 = source
    def spawn(j, gen, P):
        x = x0 + hash3(j, gen, seed + 2) * (x1 - x0)
        y = y0 + hash3(j, gen, seed + 3) * (y1 - y0)
        room = None if floor is None else floor - y
        return x, y, _pick(variants, j, gen, seed + 4, room, drop_of(P))
    return _build(int(T2), sprites, n, lambda j: periods[j % len(periods)],
                  lambda j: '%s%d' % (name, j % len(PETAL_ARTS)), track, variants, spawn, seed, gens)

# ---------------------------------------------------------------- leaves
LEAF_KEY = ('l', 'm', 's', 'd')        # lit, mid, shade, stem / accent
LEAF_ARTS = (
    ('.ll\nms.\n...', 'l..\nms.\n.s.', '...\nlmd\n...', '.m.\nsl.\nd..'),
    ('.lm\nmm.\nd..', 'm..\nlm.\n.d.', '...\ndml\n...', '.l.\nml.\n.d.'),
    ('.ms\nss.\nd..', 's..\nms.\n.d.', '...\nmsd\n...', '.m.\nss.\n.d.'),
)

def leaves(source=(120, 96, 200, 140), n=18, periods=(120, 144, 160, 180, 240), wind=(80, 280),
           drop=(30, 110), floor=None, T2=2880, slots=('L4', 'L3', 'L2', 'L1'), name='leaf',
           variants=6, rest=0.0, sway=2.0, seed=1601, gens=12):
    """autumn leaves torn off a tree, riding the wind and tumbling every 2 steps (Lantern Isle's
    fall leaves): a wider sway than petals and a fall that speeds up (drop * (0.6 u^2 + 0.4 u)).
    Arguments as petals(); slots: (lit, mid, shade, stem). Three 3x3 drawings, `name`0..2, 4
    frames each, anchored at their centre."""
    key = dict(zip(LEAF_KEY, slots))
    sprites = {'%s%d' % (name, i): (_frames(a, key, 3, 3), 1, 1) for i, a in enumerate(LEAF_ARTS)}
    def par(P, v, k):
        return hash3(P, v, seed + 10 + k)
    def drop_of(P):
        return lambda v: drop[0] + (drop[1] - drop[0]) * par(P, v, 1) + 2
    def track(P, v):
        dist = wind[0] + (wind[1] - wind[0]) * par(P, v, 0)
        dr = drop_of(P)(v) - 2
        ph = int(par(P, v, 2) * len(SWAY))
        rows = []
        for age in range(P):
            u = age / P
            sw = SWAY[((age >> 1) + ph) % len(SWAY)] * sway
            f = ((age >> 1) + v) % 4 if u < 1 - rest else -1
            rows.append((math.floor(dist * u + sw), math.floor(dr * (0.6 * u * u + 0.4 * u) + abs(sw) * 0.4), f))
        return rows
    x0, y0, x1, y1 = source
    def spawn(j, gen, P):
        x = x0 + hash3(j, gen, seed + 2) * (x1 - x0)
        y = y0 + hash3(j, gen, seed + 3) * (y1 - y0)
        room = None if floor is None else floor - y
        return x, y, _pick(variants, j, gen, seed + 4, room, drop_of(P))
    return _build(int(T2), sprites, n, lambda j: periods[j % len(periods)],
                  lambda j: '%s%d' % (name, j % len(LEAF_ARTS)), track, variants, spawn, seed, gens)

# ---------------------------------------------------------------- snow
SNOW_LAYERS = ((90, 1, (288, 320, 360)), (50, 2, (180, 192, 240)), (20, 3, (120, 144, 160)))

def snow(w=320, h=180, layers=SNOW_LAYERS, land=None, T2=2880, slots=('N0', 'N1', 'N3'),
         drift=6, sway=(1, 2, 3), name='flake', variants=4, seed=1701, gens=12):
    """snow in three depths, far 1 px dots to near 5 px crosses, swaying as it falls (Lantern
    Isle's winter). layers: (count, size 1-3, periods) per depth, far first; slots: the tone
    of sizes 1, 2 and 3 (size 3's arms take the size-2 tone); drift: px sideways per size over a
    fall; sway: the stepped sway amplitude per size; land: (y0, y1) where far and mid flakes come
    to rest on the ground plane (None: every flake falls past the bottom). Drawings: `name`_s
    (1 px), `name`_m (1 px that twinkles between two tones), `name`_l (a cross and a 2x2 knot)."""
    s0, s1, s2 = slots
    sprites = {name + '_s': (_frames(['a'], {'a': s0}), 0, 0),
               name + '_m': (_frames(['a', 'b'], {'a': s1, 'b': s2}), 0, 0),
               name + '_l': (_frames(['.a.\naAa\n.a.', 'Aa.\naa.\n...'],
                                     {'a': s1, 'A': s2}, 3, 3), 1, 1)}
    names = {1: name + '_s', 2: name + '_m', 3: name + '_l'}
    ids = []                                  # (size, period) per particle
    for count, size, pers in layers:
        ids += [(size, pers[i % len(pers)]) for i in range(count)]
    def total_drop(size, P, v):
        if land is None or size == 3:
            return h + 12
        return land[0] + (land[1] - land[0]) * hash3(P, v, seed + 20 + size) + 6
    tracks, index = [], {}
    def track_for(size, P, v):
        if (size, P, v) in index:
            return index[(size, P, v)]
        dr = total_drop(size, P, v)
        amp = sway[size - 1] * 0.5
        ph = int(hash3(P, v, seed + 30 + size) * len(SWAY))
        rows = []
        for age in range(P):
            u = age / P
            sw = SWAY[((age >> 2) + ph) % len(SWAY)] * amp
            f = 0 if size == 1 else ((age >> 3) + v) % 2
            rows.append((math.floor(u * drift * size + sw), math.floor(dr * u), f))
        index[(size, P, v)] = len(tracks)
        tracks.append(np.asarray(rows, dtype=np.int16))
        return index[(size, P, v)]
    T2 = int(T2)
    per, off, gate, spr, start = [], [], [], [], []
    for j, (size, P) in enumerate(ids):
        if T2 % P:
            raise ValueError('snow period %d does not divide T2=%d' % (P, T2))
        G = _gens(T2, P, gens)
        s = []
        for gen in range(G):
            x = hash3(j, gen, seed + 5) * (w + 40) - 20 - drift * size
            v = int(hash3(j, gen, seed + 6) * variants)
            s.append((int(math.floor(x)), -6, track_for(size, P, v)))
        per.append(P)
        off.append(int(hash2(j, seed) * P))
        gate.append(hash2(j, seed + 1))
        spr.append(names[size])
        start.append(s)
    return Field(T2, sprites, tracks, per, off, gate, spr, start)

# ---------------------------------------------------------------- drizzle
DRIZZLE_LAYERS = ((70, 1, 3, 0, 'N1'), (50, 3, 5, 3, 'N2'))

def drizzle(w=320, h=180, layers=DRIZZLE_LAYERS, T2=2880, lean=1, head=None, name='drizzle',
            seed=1301, gens=12):
    """fine drizzle in depth layers: short opaque streaks in palette slots, each falling a whole
    number of px per step (Lantern Isle's spring rain, thinned to a lofi drizzle). layers:
    (count, length px, speed px per step, slant: 1 px sideways per `slant` px down (0 straight),
    slot), far first; lean: +1 drifts right, -1 left; head: a slot for each streak's lowest pixel
    (None: the layer slot). Each layer's three periods are the divisors of T2 just above the time
    a streak takes to cross the frame. Drawings: `name`0, `name`1, ... one per layer."""
    T2 = int(T2)
    sprites, ids, tracks, index = {}, [], [], {}
    for li, (count, L, speed, slant, slot) in enumerate(layers):
        pts = [((i // slant) if slant else 0, i) for i in range(L)]
        wd = pts[-1][0] + 1
        g = Grid(wd, L)
        for i, (x, y) in enumerate(pts):
            g.set(x if lean > 0 else wd - 1 - x, y, head if (head and i == L - 1) else slot)
        sprites['%s%d' % (name, li)] = ([g], 0 if lean > 0 else wd - 1, 0)
        need = math.ceil((h + 2 * L + 4) / speed)
        big = [d for d in _divisors(T2) if d >= need][:3] or [T2]
        ids += [(li, big[i % len(big)]) for i in range(count)]
    def track_for(li, P):
        if (li, P) not in index:
            _, L, speed, slant, _ = layers[li]
            rows = []
            for age in range(P):
                dy = age * speed
                rows.append(((dy // slant) * lean if slant else 0, dy, 0 if dy < h + 2 * L + 2 else -1))
            index[(li, P)] = len(tracks)
            tracks.append(np.asarray(rows, dtype=np.int16))
        return index[(li, P)]
    per, off, gate, spr, start = [], [], [], [], []
    for j, (li, P) in enumerate(ids):
        _, L, speed, slant, _ = layers[li]
        reach = (P * speed // slant) if slant else 0
        G = _gens(T2, P, gens)
        s = []
        for gen in range(G):
            x = hash3(j, gen, seed + 5) * (w + reach) - (reach if lean > 0 else 0)
            s.append((int(math.floor(x)), -L - 1, track_for(li, P)))
        per.append(P)
        off.append(int(hash2(j, seed) * P))
        gate.append(hash2(j, seed + 1))
        spr.append('%s%d' % (name, li))
        start.append(s)
    return Field(T2, sprites, tracks, per, off, gate, spr, start)

# ---------------------------------------------------------------- fireflies
# a lazy closed wander in unit steps (24 keys), and a blink: 0 off, 1 dim, 2 bright, 3 glow
FIREFLY_PATH = ((0, 0), (1, 0), (1, -1), (2, -1), (2, -2), (2, -3), (1, -3), (1, -4), (0, -4),
                (-1, -4), (-1, -3), (-2, -3), (-2, -2), (-3, -2), (-3, -1), (-2, -1), (-2, 0),
                (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 2), (0, 2), (0, 1))
FIREFLY_BLINK = (0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 3, 3, 2, 2, 1, 1, 0, 0, 0, 0, 0, 0,
                 0, 0, 0, 1, 2, 1, 0, 0)

def fireflies(homes, periods=(96, 120, 144), T2=2880, slots=('A5', 'L4'), path=FIREFLY_PATH,
              blink=FIREFLY_BLINK, scale=1, jitter=2, name='firefly', seed=1501, gens=12):
    """fireflies wandering a small closed loop around hand-placed homes, swelling to a soft
    cross and going dark (Lantern Isle's summer). homes: [(x, y), ...], one firefly each;
    path: unit-step (dx, dy) keys, resampled over the period and scaled by `scale`; blink: keys
    over the period, 0 off, 1 dim dot, 2 bright dot, 3 bright dot with dim arms; slots: (core,
    dim); jitter: px each generation's home may shift. Every other firefly wanders mirrored.
    One drawing `name`, 3 frames (dim, bright, glow) on a 3x3 grid anchored at its centre."""
    core, dim = slots
    sprites = {name: (_frames(['...\n.d.\n...', '...\n.c.\n...', '.d.\ndcd\n.d.'],
                              {'c': core, 'd': dim}, 3, 3), 1, 1)}
    def track(P, v):
        m = -1 if v else 1
        rows = []
        for age in range(P):
            dx, dy = path[age * len(path) // P]
            b = blink[age * len(blink) // P]
            rows.append((dx * m * scale, dy * scale, b - 1))
        return rows
    def spawn(j, gen, P):
        hx, hy = homes[j]
        jx = int(math.floor((hash3(j, gen, seed + 2) * 2 - 1) * jitter + 0.5))
        jy = int(math.floor((hash3(j, gen, seed + 3) * 2 - 1) * jitter + 0.5))
        return hx + jx, hy + jy, j % 2
    return _build(int(T2), sprites, len(homes), lambda j: periods[j % len(periods)],
                  lambda j: name, track, 2, spawn, seed, gens)
