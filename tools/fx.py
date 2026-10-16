"""Effects as opaque palette sprites driven by age: fire, smoke, dust, shots, muzzle flashes,
sparks, casings, debris, crisp motes, cell rain, light streaks, indicator lights, neon signs,
rain splashes, drips and puddle ripples.

Every effect is a pure function of (inputs, age or t, seed): no state, no blur, no alpha in the
pixel layer. Slot effects write ramp slots (fire0..fire6, smoke0..smoke5, dust0..dust4, ...) into
a Canvas, an object array or an artlib.Grid; merge fx.PALETTE into the scene palette (or name
your own ramps with the same step counts). Ages run 0..1 over an effect's life; for an exact
loop spawn from a table and take age = ((t - t0) mod T) / life (anim.age does this).

    import fx, anim
    PAL.update(fx.PALETTE)
    a = anim.age(t, 12, 22, T)                      # a blast spawned at frame 12, 22 frames long
    if a is not None:
        fx.fireball(c, 120, 90, a, R=14, seed=3)    # 14 rising lobes cool to smoke, then crumble (05)
    fx.trail(c, rocket_path, t, T, every=3, life=24)               # age-graded smoke puffs (05)
    fx.puff(c, 60, 140, frame=(t // 2) % 6)                        # floor dust, held 2 ticks (09)
    d = fx.muzzle(c, 40, 80, angle=0, frame=t - t_shot, shot=k)    # 3 drawings held [1, 1, 2] (05)
    fx.casing(c, 38, 78, age=(t - t_shot) / 14, ground_y=96)
    fx.sparks(c, 90, 70, age=(t - t_hit) / 10, seed=k)
    fx.hit_flash(c, crab_mask, on=(t % 6) < 2, lift=3)             # palette lift, not a blend
    fx.emissive(c, shot_mask, forward=(1, 0))                      # cream core, saturated rim (08)
    img = fx.crescent(img, 4 * 70, 4 * 60, 56, 44, a0=-75, sweep=150, k=2)  # swing trail (10)
    fx.tumble(c, fx.CARDS, (260, 110), (1.2, -1.5), t, T=T, spin=0.75)   # a card in the air (09)
    fx.burst(c, 170, 120, t, t0=40, T=T)                           # Celeste wall-kick dust (02)
    fx.rain_cells(c, t, T, n=30, length=30, cycles=8)              # 1 px opaque cell rain (02)
    img = fx.pixel_motes(img, t, T, region=side_mask)              # twinkling dots and diamonds (03)
    img = fx.light_streaks(img, t, T, region=(200, 60, 300, 232))  # stepped-alpha streaks (03)
    fx.indicator(c, 225, 121, t=t, phase=2)                        # amber chase in a brass frame (06)
    tube, emit = fx.neon_sign(c, 40, 20, 'OPEN', t=t, T=T, broken=(2,))  # 1 px tubes, a buzzing P (09)
    fx.rain_splashes(c, t, T, n=30, length=30, cycles=8)           # crowns where those streaks land (02)
    fx.splash_field(c, t, T, (0, 150, 384, 178), n=12, every=12)   # hashed floor splashes (02)
    fx.drip(c, 104, 101, 152, t, period=20, offset=7)              # bead, fall, splash, loops (10)
    fx.ripples(c, t, T, puddle_mask, n=3, life=24, squash=0.4)     # 1 px rings squashed for 3/4 (10)
    fx.drop_shadow(c, 60, 101, rx=5)                               # see sprite.drop_shadow

References: Metal Slug 3 (fireball, smoke, muzzle, casings, sparks, hit flash), Owlboy (emissive
shots with an inverted ramp), Katana ZERO (lobed dust puffs), Celeste (cell rain, wall dust),
Hyper Light Drifter (crisp motes, light streaks), Into the Breach (indicator lights), Stardew
Valley (drop shadows, swing crescent), Katana ZERO (tumbling cards). Built from the prototype study/05/proto_fx2.py (smoke under heat 0.45).
"""
import math, pathlib, sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import morph
from sprite import grid_of, drop_shadow

__all__ = ['PALETTE', 'fireball', 'smoke_puff', 'trail', 'puff', 'burst', 'emissive', 'shot',
           'muzzle', 'muzzle_light', 'casing', 'sparks', 'hit_flash', 'debris', 'crescent', 'tumble',
           'CARDS', 'pixel_motes',
           'rain_cells', 'light_streaks', 'indicator', 'drop_shadow',
           'neon_tube', 'neon_state', 'neon_sign', 'splash', 'rain_splashes', 'splash_field',
           'ripple', 'ripples', 'drip', 'SPLASH']

# measured ramps (05 fire and smoke, 09 dust, 08 emissive, 06 indicator), darkest first
FIRE = ['#2a0602', '#611e05', '#a8420f', '#d86f1e', '#eda13f', '#f7d98e', '#fbf4dc']
SMOKE = ['#3e332d', '#5f544d', '#837a77', '#a39a98', '#bdb3b2', '#e6e1d6']
DUST = ['#ba9a7a', '#d2a274', '#e2be98', '#f2d1aa', '#fce5b2']
PALETTE = {}
for _n, _r in (('fire', FIRE), ('smoke', SMOKE), ('dust', DUST)):
    PALETTE.update({'%s%d' % (_n, i): h for i, h in enumerate(_r)})
PALETTE.update({'fx_rim': '#e47815', 'fx_mid': '#dec04e', 'fx_core': '#eadbbd',
                'brass0': '#4a3410', 'brass1': '#9a7428', 'brass2': '#e0c060',
                'amber2': '#745a24', 'amber4': '#e8b040', 'frame0': '#2d2510', 'halo': '#2c2924',
                'rain': '#ffffff', 'spec': '#e6e8ec', 'mote1': '#1afc88', 'mote0': '#13a868',
                'neon_core': '#f2fffd', 'neon_rim': '#16b8b0', 'neon_off': '#1c2e30',
                'drip': '#a8c8e0', 'ripple1': '#8fb0c8', 'ripple0': '#4e6a82'})

def _h(a, b, s=0):
    """integer hash -> [0, 1) (the hash of iso.hash2 and texture._hash_arr), vectorised"""
    h = (np.asarray(a).astype(np.int64) * 374761393 + np.asarray(b).astype(np.int64) * 668265263
         + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _hf(a, b, s=0):
    return float(_h(a, b, s))

def _window(arr, x0, y0, x1, y1):
    """clip a box to the grid: (x0, y0, x1, y1) ints, or None when empty"""
    H, W = arr.shape[:2]
    x0, y0 = max(0, int(math.floor(x0))), max(0, int(math.floor(y0)))
    x1, y1 = min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1)))
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None

def _put(arr, x, y, v):
    x, y = int(math.floor(x)), int(math.floor(y))
    if v is not None and 0 <= y < arr.shape[0] and 0 <= x < arr.shape[1]:
        arr[y, x] = v

def _write(arr, box, code, names):
    """code (local int array, 0 = nothing) -> slot names[code] into arr inside box"""
    x0, y0, x1, y1 = box
    sub = arr[y0:y1, x0:x1]
    for k in np.unique(code):
        if k > 0:
            sub[code == k] = names[int(k)]

def _ring4(m):
    return morph.boundary(m, outer=True, conn=4, border=False)

# ---------------------------------------------------------------- fireball
def fireball(c, cx, cy, age, R=14, seed=0, lobes=14, debris=12, fire='fire', smoke='smoke',
             smoke_heat=0.45, skin=True):
    """a cauliflower explosion (05): `lobes` round lobes that grow, rise and cool along a 7-step
    fire ramp (fire0 dark red .. fire6 cream), with a dark crease where a lobe's lower rim
    overlaps another. Under heat `smoke_heat` the cooler pixels turn to smoke (6 steps); from
    age 0.5 it crumbles in 2x2 clusters, and `debris` chunks fly out on ballistic paths.
    age 0..1 over a life of 18-24 frames. (cx, cy) is the blast's base centre."""
    if not 0 <= age < 1:
        return
    arr, commit = grid_of(c)
    grow = 1 - (1 - min(1.0, age / 0.3)) ** 2
    rise = 12 * age ** 1.2 * R / 14.0
    heat = max(0.0, 1 - age ** 0.8 * 1.15)
    lob = []
    for i in range(lobes):
        a = -math.pi / 2 + (_hf(i, 1, seed) - 0.5) * math.radians(195)
        d = R * (0.15 + 0.7 * _hf(i, 2, seed)) * (0.4 + 0.6 * grow)
        r = R * (0.24 + 0.16 * _hf(i, 3, seed)) * (0.45 + 0.55 * grow) * (1 + 0.3 * age)
        lob.append((cx + math.cos(a) * d * 0.9, cy + math.sin(a) * d * 1.05 - rise * (0.6 + 0.4 * _hf(i, 4, seed)), r))
    lob.append((cx, cy - rise * 0.5, R * 0.42 * (0.45 + 0.55 * grow) * (1 + 0.3 * age)))  # a core
    lob.sort(key=lambda q: -q[1])                          # lower lobes first, upper ones over them
    if debris:                                             # under the body: no hot specks inside it
        _debris(arr, cx, cy - R * 0.2, age, debris, seed, R, fire)
    box = _window(arr, cx - 1.6 * R - 3, cy - 1.7 * R - rise - 3, cx + 1.6 * R + 4, cy + 1.0 * R + 4)
    if box:
        x0, y0, x1, y1 = box
        yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
        code = np.zeros(xx.shape, int)                     # 1..7 fire step + 1, 11..16 smoke step + 1
        for lx, ly, r in lob:
            d = np.hypot(xx - lx, yy - ly) / r
            m = d < 1
            if not m.any():
                continue
            l = (-(xx - lx) * 0.5 - (yy - ly) * 0.85) / r          # -1 shadow .. 1 lit (upper left)
            hgt = np.clip((cy - rise - ly) / R, -1, 1)
            # upper lobes stay cream while the lower ones are orange (05: cream tops over orange)
            v = heat * 5.0 + 1.6 * l + 0.4 + hgt * (1.5 - 1.6 * age)
            crease = m & (d > 0.78) & (l < 0.1) & (code > 0)
            v = np.where(crease, v - 2.2, v)
            k = np.clip(np.floor(v + 0.5), 0, 6) + 1
            if heat < smoke_heat:
                sm = v < 2.4 + (smoke_heat - heat) * 5
                k = np.where(sm, 11 + np.clip(np.floor(2.7 + 1.6 * l - 1.5 * crease), 0, 5), k)
            code = np.where(m, k, code)
        ix, iy = xx.astype(int), yy.astype(int)
        if age > 0.5:                                      # crumble in 2x2 clusters
            kk = (age - 0.5) / 0.5
            kill = (_h(ix // 2, iy // 2, seed + 7) < kk * 1.15) | (_h(ix, iy, seed + 9) < kk * 0.3)
            code[kill] = 0
        if skin and heat > 0.3:                            # 1 px dark skin on the lower half
            m = code > 0
            ring = _ring4(m) & (yy > cy - rise - 2)
            code[ring] = 1
        names = [None] + ['%s%d' % (fire, i) for i in range(7)] + [None] * 3 + \
                ['%s%d' % (smoke, i) for i in range(6)]
        _write(arr, box, code, names)
    commit()

def _debris(arr, x, y, age, n, seed, R, fire):
    """burning chunks: 1-2 px hot heads with a 1 px cooler tail, cooling as they fly (05)"""
    if not 0.1 < age < 0.85:
        return
    tt = age * 1.4
    hot = 6 if age < 0.3 else (5 if age < 0.5 else 4)
    for i in range(n):
        a = -math.pi * (0.05 + 0.9 * _hf(i, 4, seed + 1))
        sp = (16 + 18 * _hf(i, 5, seed + 1)) * R / 14.0
        px = x + math.cos(a) * sp * tt
        py = y + math.sin(a) * sp * tt + 30 * tt * tt * R / 14.0
        vx, vy = math.cos(a) * sp, math.sin(a) * sp + 60 * tt * R / 14.0
        nv = math.hypot(vx, vy) or 1
        _put(arr, px - vx / nv * 1.5, py - vy / nv * 1.5, '%s%d' % (fire, 2))
        _put(arr, px, py, '%s%d' % (fire, hot))
        if _hf(i, 6, seed + 1) < 0.5:
            _put(arr, px + 1, py, '%s%d' % (fire, hot - 1))

def debris(c, x, y, age, n=8, seed=0, speed=(16, 34), g=30.0, spread=(0.05, 0.95),
           slots=('fire6', 'fire5', 'fire4', 'fire2'), size=(1, 2), ground_y=None):
    """ballistic chunks thrown up from (x, y): chunk i leaves at angle -pi * lerp(spread, hash)
    with speed lerp(speed) px per life; position x + vx a, y + vy a + g a^2 (a = age), floored.
    slots: head colours from hot to cool (picked by age) and the tail slot last. size (1, 2):
    some heads are 2 px wide. ground_y: chunks stop and rest on that row."""
    if not 0 <= age < 1:
        return
    arr, commit = grid_of(c)
    heads, tail = slots[:-1], slots[-1]
    head = heads[min(len(heads) - 1, int(age * len(heads)))]
    for i in range(n):
        a = -math.pi * (spread[0] + (spread[1] - spread[0]) * _hf(i, 4, seed))
        sp = speed[0] + (speed[1] - speed[0]) * _hf(i, 5, seed)
        vx, vy = math.cos(a) * sp, math.sin(a) * sp
        px, py = x + vx * age, y + vy * age + g * age * age
        if ground_y is not None and py >= ground_y:
            ta = max(0.0, (-vy + math.sqrt(max(0, vy * vy + 4 * g * (ground_y - y)))) / (2 * g)) if g else age
            px, py = x + vx * ta, ground_y
            _put(arr, px, py, head)
            continue
        dvx, dvy = vx, vy + 2 * g * age
        nv = math.hypot(dvx, dvy) or 1
        _put(arr, px - dvx / nv * 1.5, py - dvy / nv * 1.5, tail)
        _put(arr, px, py, head)
        if size[1] > 1 and _hf(i, 6, seed) < 0.5:
            _put(arr, px + 1, py, head)
    commit()

# ---------------------------------------------------------------- smoke, trails, dust
def smoke_puff(c, cx, cy, age, seed=0, r=(1.5, 6.5), ramp='smoke', pores=0.1, lobes=7, rise=3.0,
               sway=1.5):
    """an opaque cauliflower smoke puff (05): `lobes` lobes (radius base * (0.6 + 0.5 h), base
    growing from r[0] to r[1] with sqrt(age)) set round the rim so the silhouette scallops, lit
    from the upper left on a 6-step ramp: a pale cap, a light main tone (step 4, the measured
    #b5aaa9 band), a step-2 shadow side and a 1 px dark crease where a lobe's lower rim covers
    another. Dark 1-2 px pores sit in the shadow half and spread with age, a broken 2 px fringe
    while young, and a clustered 2x2 dissolve from age 0.55. It rises `rise` px over its life
    and sways sideways."""
    if not 0 <= age < 1:
        return
    arr, commit = grid_of(c)
    base_r = r[0] + (r[1] - r[0]) * math.sqrt(age)
    sw = sway * math.sin(2 * math.pi * age + _hf(0, 6, seed) * 6)
    lob = []
    for i in range(lobes):
        rr = base_r * ((0.5 + 0.35 * _hf(i, 1, seed)) if i else 0.7)
        a = 2 * math.pi * (i / max(1, lobes - 1) + 0.3 * _hf(i, 2, seed))      # lobes round the rim
        d = base_r * (0.6 + 0.35 * _hf(i, 3, seed)) if i else 0.0
        lob.append((cx + math.cos(a) * d + sw, cy + math.sin(a) * d * 0.8 - rise * age, rr))
    lob.sort(key=lambda q: -q[1])                          # lower lobes first, upper ones over them
    ext = base_r * 2.0 + abs(sway) + 3
    box = _window(arr, cx - ext, cy - ext - rise, cx + ext + 1, cy + ext + 1)
    if not box:
        commit(); return
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    ix, iy = xx.astype(int), yy.astype(int)
    code = np.zeros(xx.shape, int)
    lit = np.zeros(xx.shape)
    for lx, ly, rr in lob:
        d = np.hypot(xx - lx, yy - ly) / rr
        m = d < 1
        if not m.any():
            continue
        l = (-(xx - lx) * 0.5 - (yy - ly) * 0.85) / rr     # -1 shadow .. 1 lit
        k = np.floor(3.5 + 1.9 * l - 0.9 * age)
        crease = m & (d > 1 - 1.3 / rr) & (l < 0.15) & (code > 0)
        k = np.where(crease, 1, k)
        code = np.where(m, np.clip(k, 1, 5) + 1, code)
        lit = np.where(m, l, lit)
    body = code > 0
    pore = body & (lit < 0.25) & (_h(ix // 2, iy // 2, seed + 11) < pores + 0.15 * age) \
        & (_h(ix, iy, seed + 12) < 0.45) & morph.erode(body, 1, 'cross', border=False)
    code[pore] = 2
    fr = morph.dilate(body, 2, 'disc') & ~body
    fringe = fr & (_h(ix // 2, iy // 2, seed + 3) < 0.25 * (1 - age)) & (_h(ix, iy, seed + 4) < 0.55)
    code[fringe] = 4
    if age > 0.55:                                         # crumble from the edge in 2x2 clusters
        kk = (age - 0.55) / 0.45
        edge = 1 - np.minimum(1, morph.distance(code > 0, 'chessboard', border=False) / max(1.0, base_r))
        kill = (_h(ix // 2, iy // 2, seed + 7) < kk * (0.7 + 0.8 * edge)) | (_h(ix, iy, seed + 9) < kk * 0.15)
        code[kill] = 0
    _write(arr, box, code, [None] + ['%s%d' % (ramp, i) for i in range(6)])
    commit()

def trail(c, path, t, T, every=3, life=24, puff=None, seed=0, **kw):
    """age-graded puffs along a moving path (05 rocket smoke): puff k spawns at t_k = k*every at
    path(t_k) and ages ((t - t_k) mod T) / life, so puffs of the previous loop carry over and
    the loop is seamless. Older puffs are drawn first. puff defaults to smoke_puff; kw go to it."""
    if T % every:
        raise ValueError('trail: every=%d must divide T=%d' % (every, T))
    puff = puff or smoke_puff
    items = []
    for k in range(T // every):
        tk = k * every
        a = ((t - tk) % T) / float(life)
        if a < 1:
            items.append((a, tk, k))
    for a, tk, k in sorted(items, reverse=True):
        x, y = path(tk)
        puff(c, x, y, a, seed=seed * 1000 + k, **kw)

def puff(c, x, y_floor, frame, frames=6, ramp='dust', lobes=6, light=(1, -1), seed=0, width=22,
         size=(5, 9)):
    """a lobed dust puff sitting on the floor (09 Katana ZERO): `lobes` lobes spread across
    `width` px that grow and rise, lighter at the centres and toward `light`, flat 5-step tones
    with no dither; from frame 3 it is punched by 1-2 px holes and the last frame keeps a few
    specks. frame 0..frames-1 (hold each frame 2 ticks)."""
    if not 0 <= frame < frames:
        return
    arr, commit = grid_of(c)
    f = float(frame)
    L = np.array(light, float); L /= np.hypot(*L) or 1
    box = _window(arr, x - width, y_floor - size[1] * 3 - frames, x + width + 1, y_floor + 1)
    if not box:
        commit(); return
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    ix, iy = xx.astype(int), yy.astype(int)
    tone = np.full(xx.shape, -9.0)
    pos = [((k + 0.5) / lobes - 0.5) + (_hf(k, 0, seed) - 0.5) * 0.6 / lobes for k in range(lobes)]
    order = sorted(range(lobes), key=lambda k: abs(pos[k]))[::-1]          # outer lobes first
    for k in order:
        cx = x + pos[k] * width                            # evenly spread, jittered: one mound
        r = (size[0] + (size[1] - size[0]) * _hf(k, 1, seed)) * (0.6 + 0.5 * f / frames)
        r *= 1 - 0.9 * abs(pos[k])                         # tallest in the middle
        cy = y_floor - 0.6 * r - f // 2
        d = np.hypot(xx - cx, yy - cy)
        m = (d <= r) & (yy < y_floor + 0.5)
        nx, ny = (xx - cx) / np.maximum(d, 1e-6), (yy - cy) / np.maximum(d, 1e-6)
        v = 4.3 - 2.4 * (d / r) + 0.8 * np.maximum(0, nx * L[0] + ny * L[1]) - 1.2 * f / frames
        tone = np.where(m, v, tone)
    body = tone > -9
    code = np.where(body, np.clip(np.floor(tone), 0, 4) + 1, 0).astype(int)
    rag = body & ~morph.erode(body, 1, 'cross', border=False) & (_h(ix, iy, seed + 4) < 0.3)
    code[rag & (iy < y_floor)] = 0                          # ragged 1 px edge
    if frame >= 3:
        p = (f - 2) / frames
        holes = (_h(ix // 2, iy, seed + 5) < p) | (_h(ix, iy, seed + 6) < p * 0.6)
        code[holes] = 0
    if frame == frames - 1:                                 # a few specks left
        keep = body & (_h(ix, iy, seed + 8) < 4.0 / max(1, body.sum()))
        code = np.where(keep, 2, 0)
    _write(arr, box, code, [None] + ['%s%d' % (ramp, i) for i in range(5)])
    commit()

def burst(c, x, y, t, t0, n=8, slots=('dust4', 'dust3', 'dust1'), life=12, speed=(0.5, 1.5),
          normal=(0, -1), spread=60, g=0.05, seed=0, T=None):
    """event dust in hard cells (02 wall kick): n particles leave (x, y) at frame t0 within
    `spread` degrees of `normal`, size 3 -> 2 -> 1 px and slot slots[0] -> [1] -> [2] in steps of
    3 frames, positions floored. T wraps the event across the loop seam."""
    k = t - t0
    if T:
        k %= T
    if not 0 <= k < life:
        return
    arr, commit = grid_of(c)
    base = math.atan2(normal[1], normal[0])
    stage = min(2, int(k) // 3)
    sz = 3 - stage
    for i in range(n):
        li = life - 3 * _hf(i, 3, seed)                    # 9-12 frames each
        if k >= li:
            continue
        a = base + math.radians(spread) * (2 * _hf(i, 1, seed) - 1)
        sp = speed[0] + (speed[1] - speed[0]) * _hf(i, 2, seed)
        j = 3 * (2 * _hf(i, 5, seed) - 1)                   # spawn spread along the surface
        px = x - math.sin(base) * j + math.cos(a) * sp * (k + 1)
        py = y + math.cos(base) * j + math.sin(a) * sp * (k + 1) + 0.5 * g * k * k
        s = max(1, sz - (1 if _hf(i, 4, seed) < 0.3 else 0))
        slot = slots[min(len(slots) - 1, stage)]
        x0, y0 = int(math.floor(px - (s - 1) / 2)), int(math.floor(py - (s - 1) / 2))
        for dy in range(s):
            for dx in range(s):
                if s == 3 and dx != 1 and dy != 1:         # a 3 px blob is a plus, not a square
                    continue
                _put(arr, x0 + dx, y0 + dy, slot)
    commit()

# ---------------------------------------------------------------- emissive shots
def emissive(c, mask, slots=('fx_rim', 'fx_mid', 'fx_core'), forward=(0, 0)):
    """fill a mask with an inverted ramp (08): a 1 px saturated rim, a 1 px mid ring and a cream
    core, with no outline and no glow. forward (dx, dy): the core shifts that way, so the rim
    thickens at the back of a moving shot."""
    arr, commit = grid_of(c)
    m = np.asarray(mask, bool)
    d = morph.distance(m, 'chessboard', border=False)
    fx_, fy_ = int(np.sign(forward[0])), int(np.sign(forward[1]))
    if fx_ or fy_:
        d = np.where(m, np.minimum(d, morph.shift(d, fx_, fy_, 0.0)), 0)
    rim, mid, core = slots
    arr[m & (d < 1.5)] = rim
    arr[m & (d >= 1.5) & (d < 2.5)] = mid
    arr[m & (d >= 2.5)] = core
    commit()

def shot(c, x, y, vx, vy, length=6, width=4, slots=('fx_rim', 'fx_mid', 'fx_core'), tail=0):
    """an emissive projectile at (x, y) heading (vx, vy): an oval `length` x `width` along its
    velocity filled by emissive() with the core pushed forward, plus an optional tail of `tail`
    px in the mid slot (a cream band behind it, 08). Move it at whole px per frame."""
    arr, commit = grid_of(c)
    n = math.hypot(vx, vy) or 1.0
    ux, uy = vx / n, vy / n
    ext = max(length, width) + tail + 2
    box = _window(arr, x - ext, y - ext, x + ext + 1, y + ext + 1)
    if not box:
        return
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    s = (xx - x) * ux + (yy - y) * uy
    p = -(xx - x) * uy + (yy - y) * ux
    m = (s / (length / 2.0)) ** 2 + (p / (width / 2.0)) ** 2 <= 1.0
    if tail:
        tm = (s < 0) & (s > -length / 2.0 - tail) & (np.abs(p) <= 0.5 + 0.5 * (s + length / 2.0 + tail) / tail)
        sub = arr[y0:y1, x0:x1]
        sub[tm & ~m] = slots[0]
    full = np.zeros(arr.shape, bool)
    full[y0:y1, x0:x1] = m
    emissive(arr, full, slots, forward=(round(ux), round(uy)))
    commit()

# ---------------------------------------------------------------- guns and hits
MUZZLE_HOLDS = (1, 1, 2)

def muzzle(c, x, y, angle, frame, shot=0, scale=1.0, ramp='fire', holds=MUZZLE_HOLDS):
    """a muzzle flash at the barrel tip (x, y) firing toward `angle` degrees (0 right, 90 down),
    `frame` ticks after the shot (05): 3 drawings held holds=[1, 1, 2]. Drawing 0: a cream core
    ellipse, a pale ring and 6 hashed spikes biased along the barrel with sparks 8-12 px out;
    drawing 1: the core shrunk by 1 and the spikes re-hashed; drawing 2: the ring broken into
    2x2 clusters plus the sparks. Returns the drawing index (or None when over): on drawing 0
    call muzzle_light() so nearby ramps step up for exactly one frame."""
    if frame < 0:
        return None
    acc, d = 0, None
    for i, hd in enumerate(holds):
        if frame < acc + hd:
            d = i
            break
        acc += hd
    if d is None:
        return None
    arr, commit = grid_of(c)
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    s = scale
    cx, cy = x + ux * 3.5 * s, y + uy * 3.5 * s
    ext = 16 * s
    box = _window(arr, cx - ext, cy - ext, cx + ext + 1, cy + ext + 1)
    if not box:
        return d
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    ix, iy = xx.astype(int), yy.astype(int)
    du, dv = (xx - cx) * ux + (yy - cy) * uy, -(xx - cx) * uy + (yy - cy) * ux
    shrink = 1.0 if d == 1 else 0.0
    rx, ry = 3.5 * s - shrink, 3.0 * s - shrink
    core = (du / rx) ** 2 + (dv / ry) ** 2 <= 1.0
    ring = morph.dilate(core, 2 if d != 1 else 1, 'disc', border=False) & ~core
    code = np.zeros(xx.shape, int)
    key = shot * 7 + (3 if d == 1 else 0)                  # drawing 1 re-hashes (never the next shot's)
    if d in (0, 1):
        for i in range(6):                                 # spikes: wedges from the core's edge
            u = 2 * _hf(key, i, 31) - 1
            sa = a + math.radians(75 * math.copysign(abs(u) ** 1.6, u))   # most spikes near the barrel
            L = (3 + 6 * _hf(key, i, 32)) * s * (1 + 0.6 * max(0.0, math.cos(sa - a)))
            if d == 1:
                L *= 0.8
            sx, sy = math.cos(sa), math.sin(sa)
            r0 = 2.0 * s
            along = (xx - cx) * sx + (yy - cy) * sy - r0
            perp = np.abs(-(xx - cx) * sy + (yy - cy) * sx)
            f = along / L
            wdg = (f >= 0) & (f <= 1) & (perp <= 1.5 * (1 - f) + 0.5 * f)
            code = np.where(wdg & (code == 0), np.where(f < 0.6, 5, np.where(f < 0.85, 4, 3)) + 1, code)
        code[ring] = 6
        code[core] = 7
    else:
        puffm = morph.dilate(core, 1, 'disc', border=False)          # the burnt-out flash:
        keep = _h(ix // 2, iy // 2, shot + 41) < 0.65                # the ring in 2x2 clusters
        code[puffm & keep] = 5
        inner = morph.erode(core, 1, 'cross', border=False)
        code[inner & keep] = 6
    _write(arr, box, code, [None] + ['%s%d' % (ramp, i) for i in range(7)])
    for i in range(5):                                     # detached sparks
        u = 2 * _hf(shot, i, 33) - 1
        sa = a + math.radians(70 * u)
        rr = (8 + 4 * _hf(shot, i, 34)) * s * (1.3 if d == 2 else 1.0)
        _put(arr, cx + math.cos(sa) * rr, cy + math.sin(sa) * rr, '%s%d' % (ramp, 5 if d == 0 else 4))
    commit()
    return d

def muzzle_light(g, x, y, radius=14, power=1.0, pal=None, emissive=('fire', 'smoke'), **kw):
    """the one-frame flash of drawing 0: ramps within `radius` step up by one (light.Light.point,
    hard steps). Returns a new grid."""
    import light
    arr, _ = grid_of(g)
    H, W = arr.shape
    L = light.Light(W, H).point(x, y, radius, power=power)
    return L.apply(arr, emissive=emissive, pal=pal, dither='none', **kw)

def casing(c, x0, y0, age, seed=0, ground_y=None, v=(-1.2, -2.2), g=0.35, damping=0.4, life=14,
           slots=('brass2', 'brass1')):
    """an ejected shell casing (05): 2x1 px of brass tumbling (horizontal, diagonal, vertical,
    2 ticks each) on a ballistic arc at v px/frame with gravity g, one bounce on ground_y damped
    by `damping`, then at rest. age 0..1 over `life` frames."""
    if not 0 <= age < 1:
        return
    arr, commit = grid_of(c)
    tau = age * life
    jit = 0.15 * (_hf(seed, 1, 51) - 0.5)
    vx, vy = v[0] * (1 + jit), v[1] * (1 - jit)
    px, py = x0 + vx * tau, y0 + vy * tau + 0.5 * g * tau * tau
    rest = False
    if ground_y is not None and py >= ground_y:
        disc = vy * vy + 2 * g * (ground_y - y0)
        t1 = (-vy + math.sqrt(max(0.0, disc))) / g
        bx = x0 + vx * t1
        vy2 = -(vy + g * t1) * damping
        vx2 = vx * damping
        s = tau - t1
        px, py = bx + vx2 * s, ground_y + vy2 * s + 0.5 * g * s * s
        if py >= ground_y:
            px, py, rest = bx + vx2 * (-2 * vy2 / g), ground_y, True
    hi, lo = slots
    spin = 0 if rest else int(tau // 2 + seed) % 3
    _put(arr, px, py, hi)
    if spin == 0:
        _put(arr, px + 1, py, lo)
    elif spin == 1:
        _put(arr, px + 1, py - 1, lo)
    else:
        _put(arr, px, py - 1, lo)
    commit()

def sparks(c, x, y, age, n=6, seed=0, life=10, slots=('fire6', 'fire5', 'fire4', 'fire3'), g=0.25,
           speed=(1.5, 3.0), star=True):
    """impact sparks (05): a 5x5 plus-shaped star (slots[0] centre, slots[1] arms) for the first 2
    frames, then n one-pixel sparks flying out at speed 1.5-3 px/frame under gravity g with a
    1 px tail, cooling through the slots. age 0..1 over `life` frames."""
    if not 0 <= age < 1:
        return
    arr, commit = grid_of(c)
    k = age * life
    if star and k < 2:
        for dx, dy in ((-2, 0), (-1, 0), (1, 0), (2, 0), (0, -2), (0, -1), (0, 1), (0, 2)):
            if abs(dx) + abs(dy) == 2 and k >= 1:
                continue
            _put(arr, x + dx, y + dy, slots[1])
        _put(arr, x, y, slots[0])
    else:
        kk = k - (2 if star else 0)
        span = life - (2 if star else 0)
        hot = slots[min(len(slots) - 1, 1 + int(kk / max(1, span) * (len(slots) - 1)))]
        tail = slots[-1]
        for i in range(n):
            a = 2 * math.pi * _hf(i, 1, seed + 61)
            sp = speed[0] + (speed[1] - speed[0]) * _hf(i, 2, seed + 61)
            vx, vy = math.cos(a) * sp, math.sin(a) * sp
            px, py = x + vx * kk, y + vy * kk + 0.5 * g * kk * kk
            qx, qy = x + vx * (kk - 1), y + vy * (kk - 1) + 0.5 * g * (kk - 1) ** 2
            if kk >= 1:
                _put(arr, qx, qy, tail)
            _put(arr, px, py, hot)
    commit()

def hit_flash(g, mask, on, lift=3, keep=('ol',), top=6, pal=None, slot=None):
    """the damage flash (05): while `on`, every ramp slot under mask moves up `lift` steps
    (base n -> base min(top, n + lift)), a pure palette swap; outline slots in `keep` stay.
    pal: read each ramp's top step from the palette. slot: paint the whole mask that one slot
    instead (02: 2 frames all white). Edits g in place."""
    if not on:
        return g
    arr, commit = grid_of(g)
    m = np.asarray(mask, bool)
    if slot is not None:
        arr[m & np.not_equal(arr, None) & ~np.isin(arr, list(keep))] = slot
        commit()
        return g
    tops = {}
    if pal:
        for k in pal:
            b = str(k).rstrip('0123456789')
            if b != k:
                tops[b] = max(tops.get(b, 0), int(str(k)[len(b):]))
    for v in set(arr[m].tolist()) - {None}:
        s = str(v)
        if v in keep or s.startswith('#'):
            continue
        b = s.rstrip('0123456789')
        if b == s:
            continue
        n = int(s[len(b):])
        arr[m & (arr == v)] = '%s%d' % (b, min(tops.get(b, top), n + lift))
    commit()
    return g

def crescent(target, cx, cy, r_out=14, r_in=11, a0=-75, sweep=150, k=0, frames=5,
             colours=('#968375', '#766559'), alpha=0.6, shift=6, band=2, scale=1):
    """a weapon swing trail (10 Stardew): the crescent disc(c, r_out) minus disc(c - shift *
    dir(a_mid), r_in) (thick in the middle of the arc, thin at its ends), clipped to the angles
    a0 .. a0 + sweep * (k + 1) / frames (degrees, 0 right, 90 down), drawn for frame k of
    `frames`. The outer `band` px take colours[0] (light), the rest colours[1].
    target a PIL image / RGB array (colours hex): lerped by alpha * (1 - k / frames), the
    measured ~50% see-through, drawn at screen resolution in native-size blocks: every length
    is in native px and the image is `scale` times native (the blend stays soft, the shape
    stays on the grid); target a slot grid (colours slots): a 50% checker, the strict-palette
    stand-in.
    Returns the target (a new image for PIL); nothing is drawn once k >= frames."""
    rgb_mode = not (hasattr(target, 'g') or (isinstance(target, np.ndarray) and target.dtype == object)
                    or hasattr(target, 'a'))
    if not 0 <= k < frames:
        return target
    if rgb_mode:
        a, finish = _target_rgb(target)
        H, W = a.shape[:2]
    else:
        arr, finish = grid_of(target)
        H, W = arr.shape
    sc = int(scale) if rgb_mode else 1
    box = _window(np.empty((H, W)), (cx - r_out - 1) * sc, (cy - r_out - 1) * sc,
                  (cx + r_out + 2) * sc, (cy + r_out + 2) * sc)
    if box is None:
        out = finish()
        return out if rgb_mode else target
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1] // sc + 0.5            # native cell centres
    am = math.radians(a0 + sweep / 2.0)
    ix_, iy_ = cx - shift * math.cos(am), cy - shift * math.sin(am)
    d = np.hypot(xx - cx, yy - cy)
    m = (d <= r_out) & (np.hypot(xx - ix_, yy - iy_) > r_in)
    ang = (np.degrees(np.arctan2(yy - cy, xx - cx)) - a0) % 360
    m &= ang <= sweep * (k + 1) / float(frames)
    outer = m & (d > r_out - band)
    if rgb_mode:
        al = alpha * (1 - k / float(frames))
        sub = a[y0:y1, x0:x1]
        for msk, col in ((m & ~outer, colours[1]), (outer, colours[0])):
            sub[msk] = sub[msk] * (1 - al) + _rgb(col) * al
        out = finish()
        return out
    chk = ((xx.astype(int) + yy.astype(int)) & 1) == 0
    sub = arr[y0:y1, x0:x1]
    sub[m & ~outer & chk] = colours[1]
    sub[outer & chk] = colours[0]
    finish()
    return target

# Katana ZERO's cards (09): 3x5, the 45 degree diagonal, 5x3 and the other diagonal; w body, r pip
CARDS = tuple(np.array([[{'w': 'card', 'r': 'pip', '.': None}[ch] for ch in row] for row in rows], object)
              for rows in (('www', 'www', 'wrw', 'www', 'www'),
                           ('ww..', 'www.', '.wrw', '..ww'),
                           ('wwwww', 'wwrww', 'wwwww'),
                           ('..ww', '.www', 'wrw.', 'ww..')))

def tumble(c, sprites, p0, v0, t, g=0.08, spin=0.75, phase=0, timewarp=None, T=None, period=8):
    """a small prop tumbling through the air (09 cards): world time tau = timewarp(t) (a callable,
    e.g. lambda t: anim.timewarp(t, T, [(40, 64, 1 / 3.)])) or t (mod T when T is given);
    position p0 + v0 tau + g tau^2 / 2, floored; drawing sprites[(phase + floor(tau * spin *
    len(sprites) / period)) % len(sprites)]: spin turns per `period` frames, hand-drawn rotations
    (CARDS), never a rotated bitmap. For a loop, give it T and make it leave the frame (or hide
    behind something) before the seam. Returns (x, y, drawing index)."""
    tau = timewarp(t) if timewarp is not None else ((t % T) if T else t)
    x = int(math.floor(p0[0] + v0[0] * tau))
    y = int(math.floor(p0[1] + v0[1] * tau + 0.5 * g * tau * tau))
    n = len(sprites)
    i = (int(phase) + int(math.floor(tau * spin * n / float(period)))) % n
    spr = np.asarray(sprites[i], object)
    arr, commit = grid_of(c)
    h, w = spr.shape
    for yy in range(h):
        for xx in range(w):
            v = spr[yy, xx]
            if v is not None:
                _put(arr, x - w // 2 + xx, y - h // 2 + yy, v)
    commit()
    return x, y, i

# ---------------------------------------------------------------- crisp motes
def _rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)

def _target_rgb(target):
    """(float array to draw on, finish) for a PIL image or an (H, W, 3) array"""
    from PIL import Image
    if isinstance(target, Image.Image):
        mode = target.mode if target.mode in ('RGB', 'RGBA') else 'RGB'
        src = np.asarray(target.convert(mode))
        a = src[..., :3].astype(float)
        def fin_img():
            out = src.copy()                               # alpha (RGBA) is kept as it was
            out[..., :3] = np.clip(np.floor(a + 0.5), 0, 255).astype(np.uint8)
            return Image.fromarray(out, mode)
        return a, fin_img
    t = target
    a = t[..., :3].astype(float)
    def fin():
        v = np.floor(a + 0.5) if np.issubdtype(t.dtype, np.integer) else a
        t[..., :3] = np.clip(v, 0, 255).astype(t.dtype)
        return t
    return a, fin

MOTE_STATES = {                     # 8-state twinkle tables (03): 0 off, 1 dim, 2 dot, 3 pair, 4 diamond
    'dot': (0, 1, 2, 2, 2, 2, 1, 0),
    'pair': (0, 2, 3, 3, 3, 2, 1, 0),
    'diamond': (0, 2, 2, 4, 4, 2, 1, 0),
}

def pixel_motes(target, t, T, region=None, density=1.4e-3, colour='#1afc88', dim=None,
                shapes=None, rise_cycles=1, exclude=None, seed=0, cycles=(1, 2, 3), sway=1):
    """crisp native-pixel motes that twinkle (03 Hyper Light Drifter): single dots, 2 px pairs
    and 4 px diamonds with an empty centre, each stepping through an 8-state table
    [off, dot, dot, diamond, diamond, dot, dim, off] `c` whole times per loop (c in cycles) at
    its own phase, rising rise_cycles whole region heights per loop with a 1 px stepped sway.
    Draw after the light pass; never blurred.
    target: a PIL image or (H, W, 3) array at 1x (colour / dim are hex; dim None = colour half
    way to the pixel underneath), or a slot grid / Canvas (colour / dim are slots, dim None =
    colour). region: bool mask where motes live (None = everywhere); exclude: where they never
    draw. density: motes per region pixel (03 measures 1.4e-3). Returns the target (a new image
    for PIL)."""
    shapes = shapes or {'dot': 0.65, 'pair': 0.19, 'diamond': 0.16}
    rgb_mode = not (hasattr(target, 'g') or (isinstance(target, np.ndarray) and target.dtype == object)
                    or hasattr(target, 'a'))
    if rgb_mode:
        a, finish = _target_rgb(target)
        H, W = a.shape[:2]
    else:
        arr, finish = grid_of(target)
        H, W = arr.shape
    reg = np.ones((H, W), bool) if region is None else np.asarray(region, bool)
    ys, xs = np.nonzero(reg)
    if not len(ys):
        return target if not rgb_mode else finish()
    ry0, ry1 = ys.min(), ys.max() + 1
    Hr = ry1 - ry0
    n = int(round(density * reg.sum()))
    # deterministic darts inside the region: hash-ordered region pixels, first n
    order = np.argsort(_h(xs, ys, seed + 101), kind='stable')[:n]
    mx, my = xs[order], ys[order]
    i = np.arange(len(mx))
    phi = _h(i, 2, seed + 7)
    cyc = np.asarray(cycles)[(_h(i, 3, seed + 7) * len(cycles)).astype(int)]
    u = _h(i, 4, seed + 7)
    names = list(shapes)
    cum = np.cumsum([shapes[k] for k in names]); cum /= cum[-1]
    kind = np.searchsorted(cum, u, side='right')
    q = np.floor(8 * phi * T).astype(np.int64)
    state_idx = ((8 * cyc * int(t) + q) // T) % 8
    rise = (rise_cycles * Hr * int(t)) // T
    y_t = ry0 + (my - ry0 - rise) % Hr
    x_t = mx + np.floor(sway * np.sin(2 * np.pi * (int(t) % T) / T + 2 * np.pi * phi) + 0.5).astype(int)
    vert = _h(i, 5, seed + 7) < 0.4
    tables = np.array([MOTE_STATES.get(k, MOTE_STATES['dot']) for k in names])
    st = tables[kind, state_idx]
    ok = np.ones((H, W), bool) if exclude is None else ~np.asarray(exclude, bool)
    col = _rgb(colour) if rgb_mode else colour
    for j in np.nonzero(st > 0)[0]:
        s, x, y = st[j], int(x_t[j]), int(y_t[j])
        if s == 3:
            pts = [(x, y), (x, y + 1) if vert[j] else (x + 1, y)]
        elif s == 4:
            pts = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        else:
            pts = [(x, y)]
        for px, py in pts:
            if not (0 <= px < W and 0 <= py < H) or not ok[py, px] or not reg[py, px]:
                continue
            if rgb_mode:
                if s == 1:
                    a[py, px] = _rgb(dim) if dim else (a[py, px] + col) * 0.5
                else:
                    a[py, px] = col
            else:
                arr[py, px] = (dim or colour) if s == 1 else colour
    out = finish()
    return out if rgb_mode else target

# ---------------------------------------------------------------- rain and streaks
def rain_cells(c, t, T, n=30, length=30, slot='rain', cycles=8, seed=11, region=None, slant=0,
               over=None):
    """Celeste rain (02): n opaque streaks 1 px wide and `length` px long written straight into
    the slot grid over everything. Streak i sits in column floor(hash*W) and falls `cycles`
    whole spans (H + length) per loop: y = (o_i + cycles*S*t // T) mod S - length, so frame T is
    frame 0. cycles may be a tuple (each streak picks one, whole numbers). slant k > 0: the gust
    look, the column steps 1 px right every k rows (Bresenham cells, never anti-aliased).
    region (x0, y0, x1, y1) limits it; over: a bool mask where rain is not drawn (a HUD)."""
    arr, commit = grid_of(c)
    H, W = arr.shape
    x0, y0, x1, y1 = region or (0, 0, W, H)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0 or n <= 0:
        commit()
        return c
    Hh = y1 - y0
    S = Hh + length
    cyc = cycles if isinstance(cycles, (tuple, list)) else (cycles,)
    i = np.arange(n)
    xs = x0 + (_h(i, 0, seed) * (x1 - x0)).astype(int)
    off = (_h(i, 1, seed) * S).astype(np.int64)
    cy = np.asarray(cyc)[(_h(i, 2, seed) * len(cyc)).astype(int)]
    ytop = (off + (cy * S * int(t)) // T) % S - length + y0
    blk = None if over is None else np.asarray(over, bool)
    for k in range(n):
        rows = np.arange(max(y0, ytop[k]), min(y1, ytop[k] + length))
        if not len(rows):
            continue
        cols = xs[k] + (rows // slant if slant else np.zeros_like(rows))
        cols = x0 + (cols - x0) % (x1 - x0)
        if blk is not None:
            keep = ~blk[rows, cols]
            rows, cols = rows[keep], cols[keep]
        arr[rows, cols] = slot
    commit()
    return c

def light_streaks(target, t, T, n=3, length=24, segments=(4, 4, 4, 12), alphas=(0.25, 0.45, 0.7, 1.0),
                  slant=0.09, head='#26f4ea', cycles=2, region=None, splash=True, seed=0):
    """falling 1 px light streaks with a stepped tail (03): segments and alphas run tail to head
    (4 px at 0.25, 4 at 0.45, 4 at 0.7, 12 px of head at 1.0, mixed toward `head`), drifting
    left by `slant` px per row. Streak i falls cycles or cycles+1 whole spans per loop. When a
    head reaches the floor (the region's last row) a 4 px diamond splash shows for 2 frames.
    target: a PIL image / RGB array (head a hex), or a slot grid (head a tuple of slots, one per
    segment, tail to head). Draw after the light pass. Returns the target (a new PIL image)."""
    rgb_mode = not (hasattr(target, 'g') or (isinstance(target, np.ndarray) and target.dtype == object)
                    or hasattr(target, 'a'))
    if rgb_mode:
        a, finish = _target_rgb(target)
        H, W = a.shape[:2]
        hc = _rgb(head)
    else:
        arr, finish = grid_of(target)
        H, W = arr.shape
    x0, y0, x1, y1 = region or (0, 0, W, H)
    span = (y1 - y0) + length
    seg_of = np.repeat(np.arange(len(segments))[::-1], list(segments)[::-1])  # r=0 (head) -> last segment
    def pos(tt, cyc, off):                                 # unwrapped head travel (exact at the seam)
        tt = int(tt) % T if tt >= 0 else int(tt)
        return off + (cyc * span * tt) // T
    hit = (y1 - 1) - y0
    for i in range(n):
        x_start = x0 + int(_hf(i, 0, seed) * (x1 - x0))
        off = int(_hf(i, 1, seed) * span)
        cyc = cycles + (1 if _hf(i, 2, seed) < 0.5 else 0)
        yh = y0 + pos(t, cyc, off) % span                  # head row; rows above it are the tail
        for r in range(min(length, len(seg_of))):
            yy = yh - r
            if not (y0 <= yy < y1):
                continue
            xx = x_start - int(math.floor(slant * (yy - y0)))
            if not (0 <= xx < W):
                continue
            sgi = seg_of[r]
            if rgb_mode:
                al = alphas[sgi]
                a[yy, xx] = a[yy, xx] * (1 - al) + hc * al
            else:
                arr[yy, xx] = head[sgi]
        if splash:
            tm = int(t) % T
            for back in (0, 1):                              # the head reached the floor 0 or 1 frames ago
                pa, pb = pos(tm - back, cyc, off), pos(tm - back - 1, cyc, off)
                if (pa - hit) // span > (pb - hit) // span:
                    xx = x_start - int(math.floor(slant * hit))
                    pts = ((-1, 0), (1, 0), (0, -1), (0, 1)) if back == 0 else ((-2, 0), (2, 0), (0, -1))
                    for dx, dy in pts:
                        px, py = xx + dx, y1 - 1 + dy
                        if 0 <= px < W and 0 <= py < H:
                            if rgb_mode:
                                a[py, px] = a[py, px] * 0.3 + hc * 0.7
                            else:
                                arr[py, px] = head[-1]
                    break
    out = finish()
    return out if rgb_mode else target

# ---------------------------------------------------------------- indicator lights
def indicator(grid, x, y, vertical=False, t=0, phase=0, hold=3, slots=('amber2', 'amber4', 'frame0', 'halo'),
              n=3, steps=4, halo_over=None):
    """an indicator cluster (06): n 1x2 bars 1 px apart inside a dark frame (7x4 for n=3), with a
    1 px halo ring around the frame. Bar i is lit (slots[1]) when ((t // hold) + phase - i) %
    steps == 0, else dim (slots[0]): a 12-frame chase with hold 3, steps 4. vertical: the
    cluster turned 90 degrees (2x5 bars below a pedestal). halo_over: base prefixes the halo may
    cover (None: anything already drawn there; empty pixels stay empty). Returns the frame's
    bool mask in grid size (feed it to a glow)."""
    arr, commit = grid_of(grid)
    dimc, lit, frame, halo = slots
    w, h = 2 * n + 1, 4
    m = np.zeros((h, w), object)
    m[:, :] = frame
    on = ((t // hold) + phase - np.arange(n)) % steps == 0
    for i in range(n):
        m[1:3, 1 + 2 * i] = lit if on[i] else dimc
    if vertical:
        m = m.T
    hh, ww = m.shape
    H, W = arr.shape
    full = np.zeros((H, W), bool)
    ys, xs = slice(max(0, y), min(H, y + hh)), slice(max(0, x), min(W, x + ww))
    full[ys, xs] = True
    if halo is not None:
        ring = _ring4(full)
        cur = arr[ring]
        okv = np.array([v is not None and (halo_over is None or str(v).startswith(tuple(halo_over)))
                        for v in cur], bool) if len(cur) else np.zeros(0, bool)
        idx = np.nonzero(ring)
        arr[idx[0][okv], idx[1][okv]] = halo
    if full.any():
        arr[ys, xs] = m[ys.start - y:ys.stop - y, xs.start - x:xs.stop - x]
    commit()
    return full

# ---------------------------------------------------------------- neon signs
NEON_STATES = ('off', 'dim', 'on')

def _glyph_bool(g):
    """a glyph as a bool array: a bool/int array, or a '#'/'.' string with rows split by '|'"""
    if isinstance(g, str):
        rows = g.split('|')
        return np.array([[ch == '#' for ch in r] for r in rows], bool)
    return np.asarray(g, bool)

def _line_cells(x0, y0, x1, y1):
    """Bresenham cells from (x0, y0) to (x1, y1), both ends included"""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x1 > x0 else -1), (1 if y1 > y0 else -1)
    e, out = dx + dy, []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return out
        e2 = 2 * e
        if e2 >= dy:
            e += dy
            x0 += sx
        if e2 <= dx:
            e += dx
            y0 += sy

def neon_tube(g, scale=1, trace='stroke'):
    """a 1 px neon tube path (bool array) bent from a glyph, learned from 09 Katana ZERO's club
    signs (1 px tubes, a hot core, a saturated rim, a short outer glow). trace 'stroke': every
    glyph pixel is a point of the tube, spaced `scale` px apart and joined to its side and corner
    neighbours by 1 px Bresenham runs (a corner join is skipped when a side pixel already turns
    it, so bends stay single-width), which suits thin fonts (pixfont). trace 'edge': the glyph is
    blown up by `scale` and only its 4-connected inner edge is kept, the outline tube of a filled
    shape (a glyphs.rune, a heart mask)."""
    m = _glyph_bool(g)
    s = max(1, int(scale))
    h, w = m.shape
    if trace == 'edge':
        big = np.kron(m, np.ones((s, s), bool))
        return morph.boundary(big, outer=False, conn=4, border=False) if big.any() else big
    out = np.zeros(((h - 1) * s + 1, (w - 1) * s + 1), bool)
    for j, i in zip(*np.nonzero(m)):
        out[j * s, i * s] = True
        for dj, di in ((0, 1), (1, 0), (1, 1), (1, -1)):
            jj, ii = j + dj, i + di
            if not (0 <= jj < h and 0 <= ii < w and m[jj, ii]):
                continue
            if dj and di and (m[j, ii] or m[jj, i]):
                continue
            for xx, yy in _line_cells(i * s, j * s, ii * s, jj * s):
                out[yy, xx] = True
    return out

def neon_state(t, T=None, k=0, broken=False, buzz=0.35, flicker=0.0, hold=1, seed=0):
    """the state of neon letter k at frame t: 2 on, 1 dim, 0 off (09: a dying tube buzzes in
    short hashed bursts, the rest of the sign holds). Hashed per `hold` frames on (t mod T), so
    with hold dividing T frame T is frame 0. broken: the letter buzzes, off with chance buzz/2
    and dim with chance buzz/2 on each hold. flicker: the chance per hold that the whole sign
    (every letter, same hash) drops to dim."""
    tt = int(t) % int(T) if T else int(t)
    step = tt // max(1, int(hold))
    if flicker and _hf(step, 977, seed) < flicker:
        return 1
    if broken:
        r = _hf(step, 31 + int(k), seed)
        if r < buzz * 0.5:
            return 0
        if r < buzz:
            return 1
    return 2

def neon_sign(c, x, y, text=None, glyphs=None, scale=1, trace='stroke', gap=2, vertical=False,
              core='neon_core', rim='neon_rim', off='neon_off', dim=None, lit=None, t=0, T=None,
              broken=(), buzz=0.35, flicker=0.0, hold=2, seed=0, rim_conn=8):
    """a neon sign of 1 px tubes, each tube pixel in the hot `core` slot with a 1 px `rim` slot
    hugging it on both sides, learned from 09 Katana ZERO's club signs (the tube burns
    near-white, its glass edge carries the hue, and post.Post.glow kernel 'outer' adds the halo).
    Letters come from `text` through pixfont's 5x7 font (lower case folds to upper; spaces
    advance) or from `glyphs`, a list of bool arrays or '#.|' strings (glyphs.rune, your own
    shapes), bent into tubes by neon_tube(scale, trace). Letters run left to right `gap` px
    apart, or top to bottom when vertical. Each letter's state (2 on, 1 dim, 0 off) comes from
    lit (a sequence, one per letter, of states or bools) or else from neon_state(t, T, k, k in
    broken, buzz, flicker, hold, seed): broken letters buzz on a hashed hold table that loops
    over T. On: rim then core. Dim: the tube in `dim` (default the rim slot), no rim. Off: the
    tube in `off` (unlit glass; None draws nothing). rim_conn 8 also fills the rim's corners,
    4 gives a thinner rim. Returns (tube, emit): bool masks in grid size, tube every tube
    pixel drawn, emit the core and rim of the lit letters (feed it to post.Post.glow)."""
    arr, commit = grid_of(c)
    H, W = arr.shape
    if glyphs is None:
        import pixfont
        glyphs = [None if ch == ' ' else pixfont.GLYPHS.get(ch.upper(), pixfont.GLYPHS['?'])
                  for ch in (text or '')]
    tubes = [None if g is None else neon_tube(g, scale, trace) for g in glyphs]
    adv = (5 - 1) * max(1, int(scale)) + 1 if trace == 'stroke' else 5 * max(1, int(scale))
    tube = np.zeros((H, W), bool)
    emit = np.zeros((H, W), bool)
    placed, cx, k = [], 0, 0
    for tb in tubes:
        if tb is None:
            cx += adv + gap
            continue
        th, tw = tb.shape
        ox, oy = (x, y + cx) if vertical else (x + cx, y)
        m = np.zeros((H, W), bool)
        ys, xs = np.nonzero(tb)
        ys, xs = ys + oy, xs + ox
        ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
        m[ys[ok], xs[ok]] = True
        if lit is not None:
            st = lit[k] if k < len(lit) else 2
            st = 2 if st is True else (0 if st is False else int(st))
        else:
            st = neon_state(t, T, k, k in tuple(broken), buzz, flicker, hold, seed)
        placed.append((m, st))
        cx += (th if vertical else tw) + gap
        k += 1
    for m, st in placed:                                   # rims first, so cores win overlaps
        if st == 2 and rim is not None:
            r = morph.boundary(m, outer=True, conn=rim_conn, border=False)
            arr[r] = rim
            emit |= r
    for m, st in placed:
        tube |= m
        v = core if st == 2 else ((dim or rim) if st == 1 else off)
        if v is not None:
            arr[m] = v
        if st:
            emit |= m
    commit()
    return tube, emit

# ---------------------------------------------------------------- splashes, drips, ripples
SPLASH = {                       # bottom-aligned at the hit row, centred on the hit column
    1: (('#.#', '.#.'),          # a 3 px crown
        ('#...#', '.....', '.....'),   # two split drops thrown up and out
        ('#...#',)),             # landing back as 2 dots
    2: (('#.#.#', '.###.'),      # a 5 px crown with 3 prongs
        ('#.....#', '.#...#.', '.......'),
        ('#.....#',)),
}

def splash(c, x, y, frame, size=1, slots=('rain', 'rain'), over=None):
    """a rain splash crown at its hit point (x, y), drawing `frame` 0..2 (02 Celeste rain, read as
    opaque cells): 0 a 3 px crown (size 2: a 5 px three-prong crown) in slots[0], 1 two split
    drops thrown up and out, 2 the two drops landing, both in slots[-1]. Any other frame draws
    nothing. over: a bool mask where nothing is drawn. Returns True when it drew."""
    seq = SPLASH[2 if size >= 2 else 1]
    if not 0 <= int(frame) < len(seq):
        return False
    arr, commit = grid_of(c)
    H, W = arr.shape
    rows = seq[int(frame)]
    v = slots[0] if int(frame) == 0 else slots[-1]
    blk = None if over is None else np.asarray(over, bool)
    for j, row in enumerate(rows):
        yy = y - (len(rows) - 1 - j)
        for i, ch in enumerate(row):
            xx = x - len(row) // 2 + i
            if ch == '#' and 0 <= xx < W and 0 <= yy < H and (blk is None or not blk[yy, xx]):
                arr[yy, xx] = v
    commit()
    return True

def rain_splashes(c, t, T, n=30, length=30, cycles=8, seed=11, region=None, slant=0, floor=None,
                  size=1, frames=3, slots=('rain', 'rain'), over=None, big=0.0):
    """crowns where fx.rain_cells streaks hit the ground (02 Celeste rain): pass the same n,
    length, cycles, seed, region and slant as the rain_cells call and each streak's head is
    tracked exactly; on the frame it crosses its floor row a splash() plays for `frames`
    (1..3) frames at the column it reached. floor: None (the region's last row), an int row,
    a (lo, hi) band where each streak lands on its own hashed row (a floor seen in 3/4), or a
    per-column array of rows (a curb, steps). big: the share of splashes drawn at size 2
    (hashed per hit). The head moves on whole spans per loop, so frame T is frame 0. over: a
    bool mask where no splash is drawn (the awning shelter). Returns the hit points drawn."""
    arr, commit = grid_of(c)
    H, W = arr.shape
    x0, y0, x1, y1 = region or (0, 0, W, H)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    hits = []
    if x1 <= x0 or y1 <= y0 or n <= 0:
        commit()
        return hits
    S = (y1 - y0) + length
    cyc = cycles if isinstance(cycles, (tuple, list)) else (cycles,)
    tm = int(t) % int(T)
    for i in range(n):
        xs = x0 + int(_hf(i, 0, seed) * (x1 - x0))
        off = int(_hf(i, 1, seed) * S)
        cy = cyc[int(_hf(i, 2, seed) * len(cyc))]
        if floor is None:
            fy = y1 - 1
        elif isinstance(floor, (tuple, list)) and len(floor) == 2:
            fy = int(floor[0]) + int(_hf(i, 7, seed) * (int(floor[1]) - int(floor[0]) + 1))
        elif np.ndim(floor) == 0:
            fy = int(floor)
        else:
            fy = int(np.asarray(floor)[min(W - 1, max(0, xs))])
        fy = min(y1 - 1, max(y0, fy))
        k = fy - y0 + 1                          # head row fy <=> (u mod S) == k
        u = lambda tt: off + (cy * S * tt) // int(T)
        for back in range(max(1, min(3, int(frames)))):
            a, b = u(tm - back), u(tm - back - 1)
            if (a - k) // S > (b - k) // S:
                hx = xs + (fy // slant if slant else 0)
                hx = x0 + (hx - x0) % (x1 - x0)
                gen = (a - k) // S
                sz = 2 if (big and _hf(i, 5000 + gen % 4096, seed) < big) else size
                if splash(arr, hx, fy, back, sz, slots, over):
                    hits.append((hx, fy))
                break
    commit()
    return hits

def splash_field(c, t, T, region, n=12, every=12, size=1, slots=('rain', 'rain'), over=None,
                 seed=0, big=0.0):
    """splashes at hashed floor spots (02, for a floor the streaks don't reach): n crowns per
    generation inside region (x0, y0, x1, y1), a new generation every `every` frames, each crown
    starting on its own hashed frame of the generation and playing 3 frames. Generations are
    hashed on (t mod T) // every, so with every dividing T frame T is frame 0."""
    arr, commit = grid_of(c)
    x0, y0, x1, y1 = region
    tm = int(t) % int(T)
    gen, ph = tm // int(every), tm % int(every)
    for i in range(n):
        for g in (gen, gen - 1):                  # a crown started late in the last generation
            gg = g % max(1, int(T) // int(every))
            start = int(_hf(i, 3 + 11 * gg, seed) * int(every))
            f = (ph if g == gen else ph + int(every)) - start
            if 0 <= f < 3:
                hx = x0 + int(_hf(i, 1 + 11 * gg, seed) * (x1 - x0))
                hy = y0 + int(_hf(i, 2 + 11 * gg, seed) * (y1 - y0))
                sz = 2 if (big and _hf(i, 9 + 11 * gg, seed) < big) else size
                splash(arr, hx, hy, f, sz, slots, over)
                break
    commit()
    return c

def _ellipse_ring(rx, ry):
    """the midpoint-ellipse outline (8-connected, single width) as a set of (dx, dy)"""
    rx, ry = int(rx), int(ry)
    pts = set()
    if rx <= 0 and ry <= 0:
        return {(0, 0)}
    if ry <= 0:
        return {(-rx, 0), (rx, 0)}
    if rx <= 0:
        return {(0, -ry), (0, ry)}
    def add(a, b):
        pts.update({(a, b), (-a, b), (a, -b), (-a, -b)})
    rx2, ry2 = rx * rx, ry * ry
    xx, yy = 0, ry
    dx, dy = 0, 2 * rx2 * yy
    d1 = ry2 - rx2 * ry + 0.25 * rx2
    while dx < dy:
        add(xx, yy)
        xx += 1
        dx += 2 * ry2
        if d1 < 0:
            d1 += dx + ry2
        else:
            yy -= 1
            dy -= 2 * rx2
            d1 += dx - dy + ry2
    d2 = ry2 * (xx + 0.5) ** 2 + rx2 * (yy - 1) ** 2 - rx2 * ry2
    while yy >= 0:
        add(xx, yy)
        yy -= 1
        dy -= 2 * rx2
        if d2 > 0:
            d2 += rx2 - dy
        else:
            xx += 1
            dx += 2 * ry2
            d2 += dx - dy + rx2
    return pts

def ripple(c, x, y, age, r=(1, 6), squash=0.4, slots=('ripple1', 'ripple0'), back=None,
           rings=1, gap=3, mask=None):
    """an expanding 1 px ripple ring on still water at (x, y), age 0..1 (10 Stardew Valley
    puddles, ponds in 3/4): radius r[0] -> r[1] with age, drawn as a midpoint ellipse squashed
    to ry = rx * squash for the 3/4 view (1.0 seen from above), so its outline stays single
    width with no doubled corners. The slot steps through `slots` with age (bright first).
    back: a slot for the far (upper) half of the ring, which a 3/4 view reads darker. rings > 1
    adds inner rings `gap` px behind the first, each born when the outer one has spread that
    far. mask: bool, the ring only shows inside it (the puddle). Returns the drawn bool mask."""
    arr, commit = grid_of(c)
    H, W = arr.shape
    out = np.zeros((H, W), bool)
    if not 0 <= age < 1:
        return out
    blk = None if mask is None else np.asarray(mask, bool)
    rad = r[0] + (r[1] - r[0]) * age
    v = slots[min(len(slots) - 1, int(age * len(slots)))]
    for q in range(max(1, int(rings))):
        rr = rad - q * gap
        if rr < r[0] - 0.01:
            break
        rx = int(round(rr))
        ry = int(round(rr * squash))
        for dx, dy in _ellipse_ring(rx, ry):
            px, py = x + dx, y + dy
            if 0 <= px < W and 0 <= py < H and (blk is None or blk[py, px]):
                arr[py, px] = back if (back is not None and dy < 0) else v
                out[py, px] = True
    commit()
    return out

def ripples(c, t, T, mask, n=3, life=24, seed=0, **kw):
    """puddle ripples (10 Stardew Valley rain on ponds): n ripple sources inside a bool mask, each
    spawning a ripple() every `life` frames (snapped so a whole number fit the loop) at a hashed
    pixel of the mask, with its own hashed start phase; spots are hashed per generation on
    (t mod T), so frame T is frame 0. kw goes to ripple() (r, squash, slots, back, rings, gap);
    the ring is clipped to the mask. Returns the drawn bool mask."""
    m = np.asarray(mask, bool)
    ys, xs = np.nonzero(m)
    arr, commit = grid_of(c)
    out = np.zeros(arr.shape, bool)
    if not len(ys):
        return out
    gens = max(1, int(round(int(T) / float(life))))
    L = int(T) / gens
    tm = int(t) % int(T)
    for i in range(n):
        ph = _hf(i, 0, seed) * L
        tt = (tm + ph) % int(T)
        g = int(tt // L)
        age = (tt - g * L) / L
        j = int(_hf(i, 1 + 13 * g, seed) * len(ys))
        kw.setdefault('mask', m)
        out |= ripple(arr, int(xs[j]), int(ys[j]), age, **kw)
    commit()
    return out

def drip(c, x, y, y_floor, t, period=48, offset=0, form=None, swell=4, fall=None, g=2.0,
         splash_frames=3, rings=0, ring_hold=4, idle=0, slots=('drip', 'drip'), splash_slots=None,
         ring_kw=None, size=1):
    """a drip that forms, falls and splashes, looping every `period` frames (10 Stardew Valley
    cave drips): a 1 px bead at the tip (x, y) for `form` frames, a 1x2 hanging drop for `swell`
    frames, a 1x2 streak falling to row y_floor under gravity g px/frame^2 (fall frames, default
    from the drop height: 18 px in 4 frames), a splash() of `splash_frames` (0..3) frames, then
    `rings` ripple rings held `ring_hold` frames each (ring_kw goes to ripple(); r and squash
    default to a 1 px ring growing by 2 px per ring, squash 0.4), then `idle` empty frames.
    form None fills what the period leaves. k = (t - offset) mod period, so with period
    dividing T frame T is frame 0; x, y may move (a hat brim). slots: (bead, falling drop).
    Returns the stage drawn: 'form', 'swell', 'fall', 'splash', 'ring' or 'idle'."""
    arr, commit = grid_of(c)
    d = max(1, int(y_floor) - int(y))
    if fall is None:
        fall = max(2, int(round(math.sqrt(2.0 * d / g))))
    splash_frames = max(0, min(3, int(splash_frames)))
    rest = swell + fall + splash_frames + rings * ring_hold + idle
    if form is None:
        form = max(0, int(period) - rest)
    k = (int(t) - int(offset)) % int(period)
    bead, drop = slots[0], slots[-1]
    stage = 'idle'
    if k < form:
        _put(arr, x, y, bead)
        stage = 'form'
    elif k < form + swell:
        _put(arr, x, y, bead)
        _put(arr, x, y + 1, drop)
        stage = 'swell'
    elif k < form + swell + fall:
        f = (k - form - swell + 1) / float(fall)
        yy = int(y) + 1 + int(round((d - 1) * f * f))
        yy = min(int(y_floor) - 1, yy)
        _put(arr, x, yy - 1, drop)
        _put(arr, x, yy, drop)
        stage = 'fall'
    elif k < form + swell + fall + splash_frames:
        splash(arr, int(x), int(y_floor), k - form - swell - fall, size, splash_slots or (drop, drop))
        stage = 'splash'
    elif k < form + swell + fall + splash_frames + rings * ring_hold:
        q = (k - form - swell - fall - splash_frames) // ring_hold
        kw = dict(r=(1, 1 + 2 * rings), squash=0.4)
        kw.update(ring_kw or {})
        r0, r1 = kw.pop('r')
        rad = r0 + (r1 - r0) * (q + 1) / float(rings + 1)
        ripple(arr, int(x), int(y_floor), 0.0, r=(rad, rad), **kw)
        stage = 'ring'
    commit()
    return stage
