"""Animation timing: keyed drawings held for whole frames, stepped clocks and exact loops.

Every function is a pure function of the frame t (and the loop length T): no state, no
tweening between keyed drawings, positions floored to whole pixels. Every period must divide
T so frame T is frame 0 exactly; check_periods() says which ones do not.

    import anim
    T = 96
    idle = anim.Timeline([(0, 4), (1, 3), (2, 3), (1, 4)])     # drawing ids with holds (05)
    pose = idle.at(t)                                          # no interpolation
    pack = anim.lag(idle, t)                                   # secondary part: one key behind
    bob = anim.hold([0, 0, -1, -1, -1, 0], t, div=2)           # a hand hold table at 6 fps (06)
    dy = anim.stepped_sin(t, T, cycles=2, amp=1, hold=3)       # +-1 px bob, held 3 frames (03)
    lit = anim.cascade(t, T, n=6, stagger=3)                   # rune j lights up 3 frames after j-1
    h = anim.hop(t, T, w=12, h=13, phase=5)                    # slime squash and hop (10)
    x, y = anim.orbit(t, T, 120, 60, 12, 6, cycles=(1, 2))     # a fly's figure-of-eight (10)
    ox = anim.wrap_offset(t, T, 400, trips=1)                  # a drifting layer (02)
    x, y = anim.arc(t, 10, (40, 90), (1.5, -4), 0.35)          # a jump, floored per frame (02)
    dx, dy = anim.shake(t, [30, 70], T=T)                      # 6-frame shake after a blast (05)
    gx, gy = anim.recoil(t - t_shot)                           # gun kicked back 2 px, settling (05)
    tw = anim.timewarp(t, T, [(40, 64, 0.25)])                 # slow motion that still loops (09)
    on = anim.chase(3, t, hold=3, steps=4)                     # indicator bars (06)
    g = anim.lane_offset(t, T, 60, [(48, 1.25), (48, 0)])      # stop-and-go traffic (07)
    anim.check_periods(T, {'chase': 12, 'hop': idle.total})

Learned from all ten references: Metal Slug 3 key tables and overlapping action, Into the Breach
hold tables and indicator chases, Stardew hops and orbiting fliers, Hyper Light Drifter stepped
bobs and rune cascades, Celeste arcs and wrapped parallax, Katana ZERO slow motion, Freitas
stop-and-go traffic.
"""
import math
from collections import namedtuple

import numpy as np

__all__ = ['hold', 'Timeline', 'lag', 'pulse', 'stepped_sin', 'cascade', 'hop', 'orbit',
           'wrap_offset', 'arc', 'shake', 'timewarp', 'chase', 'lane_offset', 'check_periods',
           'age', 'recoil', 'SHAKE6', 'HOP8', 'Hop']

# Metal Slug's big-blast shake: 6 frames of 1 px offsets, ending at rest (05)
SHAKE6 = ((1, 0), (-1, 1), (1, -1), (0, 1), (-1, 0), (0, 0))

# Stardew slime hop (10): (dw, dh, alt) per pose and the hold of each pose (sum 12)
HOP8 = (((0, 0, 0), 3),      # rest
        ((2, -2, 0), 2),     # squash, wider
        ((-2, 2, 2), 1),     # stretch at takeoff
        ((-1, 1, 4), 1),     # air
        ((0, 0, 4), 1),      # apex
        ((-1, 1, 2), 1),     # fall
        ((2, -2, 0), 2),     # land squash
        ((0, 0, 0), 1))      # rest

Hop = namedtuple('Hop', 'pose w h alt dx')

def _i(t):
    return int(math.floor(t))

# ---------------------------------------------------------------- held tables and keyed drawings
def hold(table, t, div=1):
    """table[(t // div) % len(table)]: a hand hold table played at one entry per `div` frames
    (period len(table) * div)"""
    return table[(_i(t) // int(div)) % len(table)]

class Timeline:
    """keyed drawings with cumulative holds: keys [(drawing, frames), ...]; at(t) is the drawing
    whose hold covers t mod total. No interpolation (05: hand keys held 2-4 ticks)."""
    def __init__(self, keys):
        self.keys = [(k[0], int(k[1])) for k in keys]
        if not self.keys or any(f <= 0 for _, f in self.keys):
            raise ValueError('Timeline keys need whole positive holds')
        self.starts = np.cumsum([0] + [f for _, f in self.keys])
        self.total = int(self.starts[-1])

    def index(self, t):
        """which key (0..n-1) covers frame t"""
        return int(np.searchsorted(self.starts, _i(t) % self.total, side='right') - 1)

    def at(self, t):
        return self.keys[self.index(t)][0]

    def local(self, t):
        """frames since the current key began"""
        return _i(t) % self.total - int(self.starts[self.index(t)])

    def __len__(self):
        return len(self.keys)

def lag(tl, t, keys_back=1):
    """overlapping action: the drawing `keys_back` keys before the one at t (a pack, hair or
    antenna that follows the body one key late, 05)"""
    return tl.keys[(tl.index(t) - keys_back) % len(tl)][0]

def age(t, t0, life, T):
    """((t - t0) mod T) / life, the normalised age of an event spawned at t0 in a loop of T
    frames, or None once it is over (age >= 1). Events of the previous loop carry over, so a
    looped effect never pops at the seam."""
    a = ((_i(t) - _i(t0)) % int(T)) / float(life)
    return a if a < 1 else None

def recoil(frame, kick=(-2, 0), settle=(1, 1), hold=1):
    """(dx, dy) offset of a part that kicks on a shot and settles back (05: the gun -2 px and the
    shoulder -1 px on the fire drawing): `kick` at frame 0..hold-1, then each axis steps back
    toward 0 by `settle` px per frame. frame < 0 (before the shot) -> (0, 0)."""
    f = _i(frame)
    if f < 0:
        return 0, 0
    k = max(0, f - int(hold) + 1)
    out = []
    for v, s in zip(kick, settle):
        v = int(v)
        out.append(0 if s <= 0 and k else int(math.copysign(max(0, abs(v) - int(s) * k), v)) if v else 0)
    return tuple(out)

# ---------------------------------------------------------------- stepped clocks
def pulse(t, period, decay=4.0, phase=0, hold=1):
    """a spike that decays: exp(-k / decay), with k the frames since the last beat (one beat
    every `period` frames, held `hold` frames). 1 on the beat, falling toward 0."""
    k = ((_i(t) + int(phase)) % int(period)) // int(hold) * int(hold)
    return math.exp(-k / float(decay))

def stepped_sin(t, T, cycles=1, amp=1, hold=3, phase=0.0):
    """round(amp * sin(2 pi (cycles * t_h / T + phase))), with t sampled every `hold` frames:
    a whole-pixel bob on a stepped clock (03: +-1 px held 3 frames). The clock restarts at each
    loop, so frame T is frame 0 even when hold does not divide T (the last step is then short)."""
    th = (_i(t) % int(T)) // int(hold) * int(hold)          # stepped inside the loop: exact at T
    return int(math.floor(amp * math.sin(2 * math.pi * (cycles * th / T + phase)) + 0.5))

def cascade(t, T, n, start=0, stagger=3, ramp=(0, 0.33, 0.66, 1.0), release=12, floor=0.0):
    """strengths of n items lighting up in turn (03 rune cascade): item j steps through `ramp`
    one entry per frame starting at start + stagger * j, holds the last entry, then all fade
    back to `floor` in whole steps over the last `release` frames of the loop. -> array (n,)"""
    tm = _i(t) % int(T)
    u = tm - int(start) - int(stagger) * np.arange(n)
    r = np.asarray(ramp, float)
    s = np.where(u < 0, floor, r[np.clip(u, 0, len(r) - 1)])
    s = np.maximum(s, floor)
    if release and tm >= T - release:
        k = (T - tm) / float(release)                     # 1 -> 1/release, stepped by the frame
        s = floor + (s - floor) * k
    return s

def hop(t, T, w, h, holds=None, phase=0, poses=None, travel=0):
    """a squash-and-hop cycle (10 slime): -> Hop(pose, w, h, alt, dx), the pose index, the
    sprite's size this frame (squash wider and shorter, stretch the other way), its lift above
    the ground in px and dx, the forward progress (0..travel px) within this hop, spread over
    the air poses (add travel * hops done yourself; keep the total a whole lap of the loop).
    poses [(dw, dh, alt), ...] default HOP8; holds default (3, 2, 1, 1, 1, 1, 2, 1) = 12."""
    poses = [p for p, _ in HOP8] if poses is None else list(poses)
    holds = [f for _, f in HOP8] if holds is None else list(holds)
    tl = Timeline(list(zip(range(len(poses)), holds)))
    if T % tl.total:
        raise ValueError('hop cycle %d does not divide T=%d' % (tl.total, T))
    tt = _i(t) + int(phase)
    i = tl.index(tt)
    dw, dh, alt = poses[i]
    air = [k for k, p in enumerate(poses) if p[2] > 0]
    dx = 0
    if travel and air:
        done = sum(1 for k in air if k < i) + (1 if i in air else 0)
        dx = int(math.floor(travel * done / len(air)))
    return Hop(i, w + dw, h + dh, alt, dx)

def orbit(t, T, x0, y0, ax, ay, cycles=(1, 2), phase=0.0):
    """(x, y) on a closed Lissajous path, rounded to whole pixels: cycles=(1, 1) an ellipse,
    (1, 2) a figure of eight (10 fly). Whole cycles, so frame T is frame 0."""
    a = 2 * math.pi * (_i(t) % T) / T
    x = x0 + ax * math.sin(cycles[0] * a + 2 * math.pi * phase)
    y = y0 + ay * math.sin(cycles[1] * a + 2 * math.pi * phase)
    return int(math.floor(x + 0.5)), int(math.floor(y + 0.5))

def wrap_offset(t, T, width, trips=1):
    """floor(width * trips * t / T) mod width: a layer that travels `trips` whole widths per
    loop (02 clouds, strata). trips may be negative (the other way). Same as canvas.wrap_offset."""
    if isinstance(trips, (int, np.integer)):
        return (int(width) * int(trips) * _i(t) // int(T)) % int(width)
    return int(math.floor(width * trips * t / T)) % int(width)

def arc(t, t0, p0, v, g=0.35, floor=True):
    """ballistic position p0 + v (t - t0) + g (t - t0)^2 / 2 (g on y, or a (gx, gy) pair),
    floored to whole pixels each frame (02 jump: g = 0.35 px/frame^2)"""
    s = t - t0
    gx, gy = (0.0, g) if np.isscalar(g) else g
    x = p0[0] + v[0] * s + 0.5 * gx * s * s
    y = p0[1] + v[1] * s + 0.5 * gy * s * s
    return (int(math.floor(x)), int(math.floor(y))) if floor else (x, y)

def shake(t, events, table=SHAKE6, T=None):
    """(dx, dy) camera offset: `table` is played from each event frame (later events win).
    events: frames, or (frame, table) pairs. T wraps events across the loop seam. Apply it to
    the world layers only, never the HUD (05)."""
    dx = dy = 0
    best = None
    for e in events:
        t0, tab = (e, table) if np.isscalar(e) else (e[0], e[1])
        k = _i(t) - int(t0)
        if T:
            k %= int(T)
        if 0 <= k < len(tab) and (best is None or k < best):
            best = k
            dx, dy = tab[k]
    return int(dx), int(dy)

def timewarp(t, T, windows, step=False):
    """warped time for slow motion inside a loop (09): windows [(t0, t1, rate), ...] run at
    `rate` (0.25 = quarter speed); the rest of the loop runs faster so the warp is the identity
    at 0 and T. Piecewise linear; step=True floors it to a whole frame."""
    tm = float(t % T) if not isinstance(t, (int, np.integer)) else float(_i(t) % T)
    slow = sum((b - a) for a, b, _ in windows)
    fast_w = T - slow
    spent = sum((b - a) * r for a, b, r in windows)
    if fast_w <= 0 or spent >= T:
        raise ValueError('timewarp windows leave no time to catch up')
    k = (T - spent) / fast_w                               # speed outside the windows
    def warped(x):
        s = 0.0
        prev = 0.0
        for a, b, r in sorted(windows):
            if x <= a:
                break
            s += k * (a - prev)
            s += r * (min(x, b) - a)
            prev = b
            if x <= b:
                return s
        return s + k * (x - prev)
    w = warped(tm)
    return int(math.floor(w + 1e-9)) if step else w

def chase(n, t, hold=3, phase=0, steps=None):
    """which of n lights are on: light i is on when ((t // hold) + phase - i) % steps == 0
    (06 indicator: 3 bars, steps 4, hold 3 -> a 12-frame chase). -> bool array (n,)"""
    steps = n if steps is None else steps
    k = _i(t) // int(hold) + int(phase)
    return (k - np.arange(n)) % int(steps) == 0

def lane_offset(t, T, Lw, schedule=None):
    """whole-unit offset of a lane of traffic on a torus of length Lw (07): schedule [(frames,
    speed), ...] (units per frame) covering exactly T frames, whose distance is a whole number
    of laps, so frame T is frame 0. None = one lap at constant speed."""
    if schedule is None:
        schedule = [(T, Lw / float(T))]
    if sum(f for f, _ in schedule) != T:
        raise ValueError('schedule must cover T=%d frames' % T)
    dist = sum(f * v for f, v in schedule)
    if abs(dist / Lw - round(dist / Lw)) > 1e-9:
        raise ValueError('schedule travels %.3f units, not whole laps of %d' % (dist, Lw))
    tm = _i(t) % T
    d, used = 0.0, 0
    for f, v in schedule:
        k = min(f, tm - used)
        if k <= 0:
            break
        d += k * v
        used += f
    return int(math.floor(d + 1e-9)) % int(Lw)

def check_periods(T, periods):
    """raise ValueError naming every period that does not divide T. periods: a list or a dict
    {name: period}. Returns True."""
    items = periods.items() if isinstance(periods, dict) else [(str(p), p) for p in periods]
    bad = ['%s=%s' % (k, p) for k, p in items if p and (int(T) % int(p) or int(p) != p)]
    if bad:
        raise ValueError('periods that do not divide T=%d: %s' % (T, ', '.join(bad)))
    return True
