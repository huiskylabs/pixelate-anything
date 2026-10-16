"""Parametric figures per style: small people and animals as slot grids, posed by drawing index.

    import figures as fg
    f = fg.slim(h=26, seed=3, frame=fg.drawing('slim', 'walk', t))   # a 01 backlit pilgrim
    f.stamp(c, x, y)                                 # anchor (between the feet) lands on (x, y)
    f = fg.at(fg.chibi, t, 'walk', seed=2, facing='side')            # picks the drawing for frame t
    f = fg.iso_person(seed=7, facing='sw', pose='walk', frame=1)     # 07 sticker person, black outline
    g = f.grid()                                     # artlib.Grid for Iso.sprite / previews
    PAL.update(fg.PALETTES['chibi'])                 # demo ramps for every slot a style uses

Every function returns a Figure: g (H x W object array of slots, None = clear) and the anchor
(ax, ay), the ground pixel between the feet. All frames of one style and size share one box and
one anchor, so a walk cycle never jitters. Drawings are keyed poses, never tweens: HOLDS[style]
[pose] is a hold table [(drawing, frames), ...] (05: hand keys held 2-4 ticks) whose total
divides 96 and 120, so any loop of those lengths closes (frame T == frame 0).

Styles (proportions measured in the style study, every design original):
  slim            01 Sword & Sworcery: no outline, head 10%, torso 40%, 1 px legs 50%, 3 tones,
                  a 1 px lit column toward the light; idle breath, walk, a held lantern
  quadruped_slim  01: a slim deer: 18 x 8 body with dapple specks and a lit back line, a 2 px
                  neck, 1 px legs, branched 1 px antlers; idle, walk, graze
  block           03 Hyper Light Drifter: 12 x 27 flat rects, 7 colours, mirrored, no outline;
                  idle (hem breathes, head bobs) and walk
  chibi           04 Sea of Stars / 10 Stardew: 26 px, head about 45%, outline per part (10) or
                  one tinted near-black (04), facing down / up / side, idle and walk
  iso_person      07 Freitas: 14 x 36 at 3.3 heads, black outline and seams, loud hair, 3 tones
                  per material, facing 'se' or 'sw'; stand, walk, wave
  thin            09 Katana ZERO: 0.175 H tall at 4.7 heads, 2-4 px limbs from a joint rig, no
                  outline, a 1 px warm rim on the side that faces the lamp; stand, walk, run;
                  optional hat ('brim', 'cone') and sword ('sheathed', 'drawn')
  slime           10 Stardew creatures: a toy-ramp dome sized per frame by anim.hop, own-step
                  line, a 2 px glint, dash eyes that blink
  cat             10: a small side-view cat; sit (tail flick), sleep (breath, flick), walk
  gull            10 / 04 coast: perched 6 x 7, flying 11 x 5 (3 flap drawings), far 5 x 3
  lofi            lantern-isle (this repo): 10-14 px people with own-material outlines for a
                  320 x 180 diorama; idle, walk, sit (chibi also sits, and takes size 22-32)

Randomness only from an integer hash of (seed, k): the same arguments always give the same pixels.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

__all__ = ['Figure', 'slim', 'quadruped_slim', 'block', 'chibi', 'iso_person', 'thin', 'at',
           'drawing', 'HOLDS', 'PALETTES', 'drop_shadow', 'BLOCK_HERO', 'slime', 'cat', 'gull', 'lofi']

# ---------------------------------------------------------------- hashing (iso.hash2's mix)
def _h(a, b=0, s=0):
    h = (int(a) * 374761393 + int(b) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def _pick(seq, seed, k):
    return seq[int(_h(seed, k, 7) * len(seq)) % len(seq)]

# ---------------------------------------------------------------- figure and painter
class Figure:
    """a posed figure: g (object array, None = clear) and the anchor (ax, ay), the ground pixel
    between the feet. parts: optional {name: bool mask} (for outlines and rims done later)."""
    def __init__(self, g, ax, ay, parts=None):
        self.g, self.ax, self.ay = g, int(ax), int(ay)
        self.parts = parts or {}

    h = property(lambda self: self.g.shape[0])
    w = property(lambda self: self.g.shape[1])

    def mask(self):
        return ~np.equal(self.g, None)

    def grid(self):
        """an artlib.Grid (Iso.sprite(grid, x, y, z, anchor=(f.ax, f.ay)), artlib.preview)"""
        import artlib
        gr = artlib.Grid(self.w, self.h)
        gr.a = [list(r) for r in self.g]
        return gr

    def flip(self):
        """mirrored left-right, the anchor mirrored with it"""
        return Figure(self.g[:, ::-1].copy(), self.w - 1 - self.ax, self.ay,
                      {k: v[:, ::-1] for k, v in self.parts.items()})

    def stamp(self, c, x, y, only=None):
        """paste onto a Canvas (or an object array) so the anchor lands on (x, y). only: a set of
        slots the figure may cover (None = anything). Returns the screen box (x0, y0, x1, y1)."""
        dst = c.g if hasattr(c, 'g') else c
        H, W = dst.shape
        ox, oy = int(math.floor(x)) - self.ax, int(math.floor(y)) - self.ay
        sx0, sy0 = max(0, -ox), max(0, -oy)
        sx1, sy1 = min(self.w, W - ox), min(self.h, H - oy)
        if sx1 > sx0 and sy1 > sy0:
            src = self.g[sy0:sy1, sx0:sx1]
            d = dst[oy + sy0:oy + sy1, ox + sx0:ox + sx1]
            m = ~np.equal(src, None)
            if only is not None:
                m &= np.isin(d, list(only))
            d[m] = src[m]
        return ox, oy, ox + self.w, oy + self.h

    def recolor(self, mapping):
        """a copy with slots renamed: {'shirt': 'coat'} maps shirt0.. to coat0.. (prefix match on
        ramp names) and exact slot names map directly"""
        def f(v):
            if v is None:
                return None
            if v in mapping:
                return mapping[v]
            base = str(v).rstrip('0123456789')
            return mapping[base] + str(v)[len(base):] if base in mapping else v
        return Figure(np.frompyfunc(f, 1, 1)(self.g).astype(object), self.ax, self.ay, self.parts)


class _P:
    """a tiny slot painter on an object array (x right, y down, rects half-open)"""
    def __init__(self, w, h, oy=0):
        self.W, self.H, self.oy = w, h, oy              # oy: headroom rows above the drawing's y = 0
        self.g = np.full((h, w), None, object)

    def put(self, x, y, v):
        x, y = int(math.floor(x)), int(math.floor(y)) + self.oy
        if 0 <= x < self.W and 0 <= y < self.H:
            self.g[y, x] = v

    def get(self, x, y):
        x, y = int(math.floor(x)), int(math.floor(y)) + self.oy
        return self.g[y, x] if 0 <= x < self.W and 0 <= y < self.H else None

    def rect(self, x0, y0, x1, y1, v):
        y0, y1 = int(math.floor(y0)) + self.oy, int(math.floor(y1)) + self.oy
        x0, y0, x1, y1 = max(0, int(math.floor(x0))), max(0, y0), min(self.W, int(math.floor(x1))), min(self.H, y1)
        if x1 > x0 and y1 > y0:
            self.g[y0:y1, x0:x1] = v

    def line(self, x0, y0, x1, y1, v):
        for x, y in _bresenham(int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))):
            self.put(x, y, v)

    def stroke(self, x0, y0, x1, y1, w0, w1=None, v=None, only_empty=False):
        """a limb: constant-width runs across the segment's minor axis (clean at 1-4 px,
        unlike a disc-swept capsule). w tapers from w0 to w1."""
        w1 = w0 if w1 is None else w1
        dx, dy = x1 - x0, y1 - y0
        n = int(max(abs(dx), abs(dy))) + 1
        vertical = abs(dy) >= abs(dx)
        for i in range(n):
            u = i / max(1, n - 1)
            cx, cy = x0 + dx * u, y0 + dy * u
            w = int(round(w0 + (w1 - w0) * u))
            if vertical:
                xs = int(math.floor(cx - w / 2 + 0.5))
                for k in range(w):
                    if not only_empty or self.get(xs + k, cy) is None:
                        self.put(xs + k, cy, v)
            else:
                ys = int(math.floor(cy - w / 2 + 0.5))
                for k in range(w):
                    if not only_empty or self.get(cx, ys + k) is None:
                        self.put(cx, ys + k, v)

    def stamp(self, art, key, ox=0, oy=0):
        for j, row in enumerate(_rows(art)):
            for i, ch in enumerate(row):
                if ch in '. ':
                    continue
                self.put(ox + i, oy + j, key[ch])

    def shift(self, rows, dx=0, dy=0):
        """move the content of rows [r0, r1) by (dx, dy), clearing what it leaves behind"""
        r0, r1 = rows
        band = self.g[r0:r1].copy()
        self.g[r0:r1] = None
        for j in range(r1 - r0):
            y = r0 + j + dy
            if 0 <= y < self.H:
                row = band[j]
                m = ~np.equal(row, None)
                xs = np.nonzero(m)[0] + dx
                ok = (xs >= 0) & (xs < self.W)
                self.g[y, xs[ok]] = row[np.nonzero(m)[0][ok]]

def _rows(art):
    lines = art.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return [l.strip() for l in lines]

def _bresenham(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy

def _nb4(m):
    """bool: any 4-neighbour set"""
    p = np.pad(m, 1)
    return p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]

def _base(v):
    s = str(v)
    b = s.rstrip('0123456789')
    return b if b != s else None

def _outline(g, mode, ol='ol', step=0, parts=None):
    """add a 1 px outer outline to a slot grid in place (the grid must have a free margin).
    mode 'slot': every ring pixel is `ol`; 'part': each ring pixel takes step `step` of the ramp
    it wraps (the lowest-stepped inside neighbour wins; non-ramp slots fall back to `ol`)."""
    m = ~np.equal(g, None)
    ring = _nb4(m) & ~m
    if mode == 'slot':
        g[ring] = ol
        return ring
    H, W = g.shape
    best = np.full((H, W), None, object)
    bstep = np.full((H, W), 99)
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):     # below first: ground contact wins ties
        src = np.full((H, W), None, object)
        ys, ye, xs, xe = max(0, -dy), H - max(0, dy), max(0, -dx), W - max(0, dx)
        src[ys:ye, xs:xe] = g[ys + dy:ye + dy, xs + dx:xe + dx]
        for (y, x) in zip(*np.nonzero(ring & ~np.equal(src, None))):
            v = src[y, x]
            b = _base(v)
            if b is None or b in ('eye', 'glint', 'lamp'):
                continue
            k = int(str(v)[len(b):])
            if k < bstep[y, x]:
                bstep[y, x], best[y, x] = k, b + str(step)
    out = ring.copy()
    g[ring] = np.where(np.equal(best[ring], None), ol, best[ring])
    return out

def _shade_edge(g, side, frm, to):
    """pixels of slot `frm` whose neighbour on `side` (-1 left, +1 right) is not frm -> `to`"""
    m = np.equal(g, frm)
    nb = np.zeros_like(m)
    if side < 0:
        nb[:, 1:] = m[:, :-1]
    else:
        nb[:, :-1] = m[:, 1:]
    g[m & ~nb] = to

# ---------------------------------------------------------------- hold tables
# drawing indices with holds (frames at the scene rate). Every total divides 96 and 120.
HOLDS = {
    'slim': {'idle': [(0, 8), (1, 4), (0, 12)], 'walk': [(0, 3), (1, 3), (2, 3), (3, 3)],
             'still': [(0, 24)]},
    'quadruped_slim': {'idle': [(0, 16), (1, 2), (0, 4), (2, 2)], 'walk': [(0, 3), (1, 3), (2, 3), (3, 3)],
                       'graze': [(0, 8), (1, 12), (2, 4)]},
    'block': {'idle': [(0, 4), (1, 4), (3, 4), (2, 4), (0, 8)], 'walk': [(0, 3), (1, 3), (2, 3), (3, 3)]},
    'chibi': {'idle': [(0, 4), (1, 4)], 'walk': [(0, 3), (1, 3), (2, 3), (3, 3)], 'sit': [(0, 16), (1, 8)]},
    'iso_person': {'stand': [(0, 24)], 'walk': [(0, 3), (1, 3), (2, 3), (3, 3)],
                   'wave': [(0, 4), (1, 4)], 'idle': [(0, 16), (1, 8)], 'sit': [(0, 24)]},
    'thin': {'stand': [(0, 16), (1, 8)], 'walk': [(0, 3), (1, 3), (2, 3), (3, 3)],
             'run': [(0, 2), (1, 2), (2, 2), (3, 2)]},
    'cat': {'sit': [(0, 16), (1, 2), (2, 2), (1, 4)], 'sleep': [(0, 12), (1, 8), (0, 2), (2, 2)],
            'walk': [(0, 3), (1, 3), (2, 3), (3, 3)]},
    'gull': {'perch': [(0, 20), (1, 4)], 'fly': [(0, 2), (1, 2), (2, 2), (1, 2)], 'glide': [(1, 24)],
             'far': [(0, 2), (1, 2)]},
    'lofi': {'idle': [(0, 16), (1, 8)], 'walk': [(0, 3), (1, 3), (2, 3), (3, 3)], 'sit': [(0, 16), (1, 8)]},
}

def drawing(style, pose, t, phase=0):
    """the drawing index style/pose shows at frame t (hold table HOLDS[style][pose])"""
    keys = HOLDS[style][pose]
    total = sum(f for _, f in keys)
    k = (int(math.floor(t)) + int(phase)) % total
    for d, f in keys:
        if k < f:
            return d
        k -= f
    return keys[-1][0]

def at(fn, t, pose, phase=0, **kw):
    """fn(..., pose=pose, frame=drawing(fn's style, pose, t)): the figure frame t shows"""
    return fn(pose=pose, frame=drawing(fn.__name__, pose, t, phase), **kw)

# ---------------------------------------------------------------- 01 slim figures
SLIM_KINDS = ('plain', 'coat', 'hat', 'hood', 'pack')

def slim(h=24, seed=0, slots=None, light_dir=-1, frame=0, pose='idle', kind=None, item=None):
    """a slim backlit figure (01): no outline, head 10%, torso 40%, legs 50% as two 1 px columns.
    slots: {'head', 'body', 'lit', 'arm', 'leg', 'item', 'glow', 'glow_lo'} (defaults: a 4-step
    'fig' ramp plus 'lamp' for an item). light_dir -1: light on the left, +1 right. kind: one of
    SLIM_KINDS (default by seed). item 'lantern' | 'staff' | None, held in the light-side hand.
    pose 'idle' (frame 0 rest, 1 breath: head and torso 1 px down), 'walk' (frames 0-3: open,
    pass, open, pass with the other foot up; the body rises 1 px on the passes), 'still'."""
    S = dict(head='fig0', body='fig2', lit='fig3', arm='fig1', leg='fig0',
             item='fig0', glow='lamp2', glow_lo='lamp1')
    S.update(slots or {})
    kind = kind or _pick(SLIM_KINDS, seed, 1)
    head_h = max(2, int(round(0.1 * h)))
    head_w = 3 if head_h >= 3 else 2 + (1 if _h(seed, 2) < 0.4 else 0)
    torso_h = int(round(0.4 * h))
    tw = max(5, int(round(0.22 * h)) + (1 if _h(seed, 3) < 0.5 else 0))   # arms included
    W = tw + 8
    pad = 3                                             # headroom: the walk passes lift the head, a staff tops it
    P = _P(W, h + 1 + pad, oy=pad)
    ax = W // 2
    tx = ax - tw // 2                                   # left arm column
    bob = 1 if (pose == 'idle' and frame == 1) else (-1 if pose == 'walk' and frame in (1, 3) else 0)
    hip = head_h + torso_h + bob                        # first leg row
    # legs: 1 px lines from the hips to the feet, a pelvis band joining them
    hl, hr = tx + 1, tx + tw - 2
    fl, fr, lift = 0, 0, (0, 0)
    if pose == 'walk':
        fl, fr = {0: (-2, 2), 1: (0, 1), 2: (-2, 2), 3: (-1, 0)}[frame % 4]
        lift = {0: (0, 0), 1: (0, 1), 2: (0, 0), 3: (1, 0)}[frame % 4]
    foot = h - 1
    P.line(hl, hip, hl + fl, foot - lift[0], S['leg'])
    P.line(hr, hip, hr + fr, foot - lift[1], S['leg'])
    P.rect(hl, hip, hr + 1, hip + max(1, int(round(0.06 * h))), S['leg'])
    # torso: flat, the column toward the light lit (the arms frame it)
    ty0 = head_h + bob
    bottom = hip + (2 if kind == 'coat' else 0)
    P.rect(tx + 1, ty0, tx + tw - 1, bottom, S['body'])
    if kind == 'coat':                                  # a coat skirts the thighs
        P.rect(tx, hip, tx + tw, bottom, S['body'])
    lit_x = tx + 1 if light_dir < 0 else tx + tw - 2
    P.rect(lit_x, ty0 + 1, lit_x + 1, bottom, S['lit'])
    if kind == 'pack':                                  # a bedroll on the back, away from the light
        bx = tx + tw - 1 if light_dir < 0 else tx - 1
        P.rect(bx, ty0, bx + 2, ty0 + max(3, torso_h // 2), S['arm'])
    # arms: 1 px columns down the torso sides, hands 1 px below the torso when the torso is long
    arm_len = max(3, int(round(0.8 * torso_h)))
    swing = {0: (1, -1), 1: (0, 0), 2: (-1, 1), 3: (0, 0)}[frame % 4] if pose == 'walk' else (0, 0)
    for side, sw in ((-1, swing[0]), (1, swing[1])):
        x = tx if side < 0 else tx + tw - 1
        y0 = ty0 + 1
        if item is not None and side == light_dir:      # forearm forward, hand out
            ln = arm_len - 2
            P.rect(x, y0, x + 1, y0 + ln, S['arm'])
            hx = x + side
            P.put(hx, y0 + ln - 1, S['arm'])
            if item == 'lantern':                       # a paper lantern on a 1 px cord
                P.put(hx + side, y0 + ln - 1, S['arm'])
                lx = hx + side
                P.put(lx, y0 + ln, S['item'])
                P.rect(lx - (1 if side < 0 else 0), y0 + ln + 1, lx + (1 if side < 0 else 2), y0 + ln + 3, S['glow'])
                P.put(lx, y0 + ln + 2, S['glow_lo'])
            elif item == 'staff':
                P.line(hx, ty0 - 2, hx, h - 1, S['item'])
        elif not (kind == 'pack' and side == -light_dir):
            P.line(x, y0, x + sw, y0 + arm_len - 1, S['arm'])
    # head: the column toward the light lit (01's single face pixel)
    hx0 = tx + (tw - head_w) // 2 + (1 if (tw - head_w) % 2 and light_dir > 0 else 0)
    hy0 = bob
    if kind == 'hat':
        P.rect(hx0 - 1, hy0, hx0 + head_w + 1, hy0 + 1, S['head'])
        P.rect(hx0, hy0 + 1, hx0 + head_w, hy0 + head_h + 1, S['head'])
    elif kind == 'hood':
        P.rect(hx0, hy0, hx0 + head_w, hy0 + head_h, S['arm'])
        P.put(hx0 + (head_w - 1 if light_dir > 0 else 0), hy0 + head_h - 1, S['head'])
    else:
        P.rect(hx0, hy0, hx0 + head_w, hy0 + head_h, S['head'])
        if head_h >= 3:
            P.put(hx0 if light_dir < 0 else hx0 + head_w - 1, hy0 + 1, S['lit'])
    return Figure(P.g, ax, h - 1 + pad)

def quadruped_slim(seed=0, length=18, slots=None, light_dir=-1, frame=0, pose='idle', antlers=None,
                   facing=1):
    """a slim deer (01): an 18 x 8 body with lighter single-pixel specks every 2-4 px and a 1 px lit
    back line, a 2 px neck over 10 rows, a small head, branched 1 px antlers, 1 px legs over 9 rows.
    slots: {'body', 'lit', 'speck', 'dark', 'antler'} (default 'deer' ramp steps 1-3, 'deer0').
    facing 1 = head to the right. pose 'idle' (0 rest, 1 ear flick, 2 tail flick), 'walk' (4
    drawings), 'graze' (0 rest, 1 head down, 2 head half way)."""
    S = dict(body='deer2', lit='deer3', speck='deer3', dark='deer1', leg='deer1', antler='deer3', eye='deer0')
    S.update(slots or {})
    antlers = (_h(seed, 11) < 0.7) if antlers is None else antlers
    L = int(length)
    bh = max(5, int(round(L * 0.42)))                   # 8 for 18
    leg = int(round(L * 0.5))                           # 9
    neck = int(round(L * 0.55))                         # 10
    Wd = L + 14
    Hd = 6 + neck + bh + leg
    P = _P(Wd, Hd)
    bx0 = 3
    by0 = Hd - leg - bh
    by1 = by0 + bh
    # body: rounded corners, a slight belly sag
    P.rect(bx0, by0, bx0 + L, by1 - 1, S['body'])
    P.rect(bx0 + 2, by1 - 1, bx0 + L - 2, by1, S['body'])
    P.put(bx0, by0, None); P.put(bx0 + L - 1, by0, None)
    P.rect(bx0 + 1, by0, bx0 + L - 1, by0 + 1, S['lit'])               # lit back line
    P.rect(bx0, by1 - 2, bx0 + L, by1 - 1, S['dark'])                  # belly shade
    P.rect(bx0 + 2, by1 - 1, bx0 + L - 2, by1, S['dark'])
    for i in range(bx0 + 2, bx0 + L - 2):                               # dapple specks
        for j in range(by0 + 2, by1 - 2):
            if (i + j) % 3 == 0 and (j - by0) % 2 == 0 and _h(i, j, seed) < 0.8:
                P.put(i, j, S['speck'])
    # tail: a 1 px column off the rump
    flick = pose == 'idle' and frame == 2
    P.rect(bx0 - 1, by0 + 1, bx0, by0 + (3 if flick else 4), S['dark'])
    if flick:
        P.put(bx0 - 2, by0, S['dark'])
    # legs: 1 px, hind pair under the rump, fore pair under the chest; thighs 2 px
    hind, fore = bx0 + 2, bx0 + L - 3
    feet = Hd - 1
    if pose == 'walk':
        off = {0: (-1, 1, 1, -1), 1: (0, 0, 0, 0), 2: (1, -1, -1, 1), 3: (0, 0, 0, 0)}[frame % 4]
    else:
        off = (0, 0, 0, 0)
    for k, (x, o) in enumerate(((hind, off[0]), (hind + 2, off[1]), (fore - 2, off[2]), (fore, off[3]))):
        P.line(x, by1, x + o, feet, S['leg'] if k % 2 == 0 else S['dark'])
    P.rect(hind, by1, hind + 3, by1 + 2, S['body'])                     # haunch tapers into the hocks
    P.put(hind + 1, by1 + 2, S['body'])
    # neck and head
    flick = pose == 'idle' and frame == 1
    def head(hx, top, antler_rows=5):
        """the side head: 3 rows, muzzle forward, ears back, two Y tines (hx = the neck column)"""
        P.rect(hx - 1, top, hx + 3, top + 1, S['body'])
        P.rect(hx - 1, top + 1, hx + 5, top + 2, S['body'])
        P.rect(hx, top + 2, hx + 4, top + 3, S['dark'])                  # jaw
        P.put(hx + 5, top + 1, S['dark'])
        P.put(hx + 1, top + 1, S['eye'])
        P.put(hx - 2, top + (0 if flick else 1), S['dark']); P.put(hx - 3, top - (1 if flick else 0), S['dark'])
        if antlers:
            for ax_, d in ((hx, -1), (hx + 2, 1)):
                P.line(ax_, top - 1, ax_, top - antler_rows, S['antler'])
                P.line(ax_, top - 3, ax_ + 2 * d, top - 3, S['antler'])
                P.put(ax_ + 2 * d, top - 4, S['antler'])
    nx0 = bx0 + L - 3
    if pose == 'graze' and frame == 1:                  # head down: the neck arcs forward, muzzle in the grass
        hx, hy = nx0 + 4, feet - 4
        P.stroke(nx0, by0, nx0 + 3, by0 + 3, 2, v=S['body'])
        P.stroke(nx0 + 3, by0 + 3, hx, hy + 1, 2, v=S['body'])
        P.rect(hx, hy, hx + 2, hy + 1, S['body'])
        P.rect(hx, hy + 1, hx + 3, hy + 2, S['body'])
        P.rect(hx + 1, hy + 2, hx + 3, hy + 3, S['body'])
        P.rect(hx + 1, hy + 3, hx + 3, hy + 4, S['dark'])               # muzzle
        P.put(hx + 1, hy + 1, S['eye'])
        P.put(hx - 1, hy, S['dark'])                                     # ear
        if antlers:                                                      # the beam sweeps forward, one tine up
            P.line(hx + 1, hy - 1, hx + 4, hy - 4, S['antler'])
            P.line(hx + 3, hy - 3, hx + 5, hy - 3, S['antler'])
            P.put(hx + 2, hy - 4, S['antler']); P.put(hx + 2, hy - 5, S['antler'])
    elif pose == 'graze' and frame == 2:                # half way: the head reaches forward at back height
        top = by0 - 4
        P.stroke(nx0, by0 + 1, nx0 + 4, top + 2, 2, v=S['body'])
        head(nx0 + 4, top, 4)
    else:
        top = by0 - neck
        P.rect(nx0, top + 3, nx0 + 2, by0 + 1, S['body'])               # neck, 2 px
        P.rect(nx0 - 1, by0 - 2, nx0, by0 + 1, S['body'])               # widening into the withers
        P.rect(nx0, top + 3, nx0 + 1, by0 - 2, S['lit'])
        head(nx0, top)
    g = P.g if facing > 0 else P.g[:, ::-1].copy()
    ax = (bx0 + L // 2) if facing > 0 else Wd - 1 - (bx0 + L // 2)
    return Figure(g, ax, Hd - 1)

# ---------------------------------------------------------------- 03 block figures
# The default block hero (original): a wide-brimmed hat over a shadowed face with two pale eye
# pixels, a coral collar, a cream mantle, a long teal cloak crossed by a coral strap to a satchel, 1 px legs.
# Rects are (y0, y1, x0, x1, slot) on a 12-wide box; mirror_x reflects each about the centre.
BLOCK_HERO = [
    (0, 1, 5, 6, 'hat'), (1, 2, 4, 6, 'hat'), (2, 3, 1, 6, 'hat'), (3, 4, 2, 6, 'hat_shade'),
    (4, 8, 3, 6, 'head'), (5, 6, 4, 5, 'visor'),
    (8, 10, 2, 6, 'collar'),
    (10, 11, 1, 6, 'mantle'), (11, 15, 0, 6, 'mantle'),
    (15, 22, 0, 6, 'cloak'), (22, 23, 1, 6, 'cloak'),
    (15, 16, 1, 3, 'emblem', False), (16, 17, 2, 4, 'emblem', False), (17, 18, 3, 5, 'emblem', False),
    (18, 19, 4, 6, 'emblem', False), (19, 20, 5, 7, 'emblem', False), (20, 21, 6, 8, 'emblem', False),
    (21, 22, 7, 9, 'emblem', False), (19, 22, 8, 11, 'satchel', False), (19, 20, 8, 11, 'emblem', False),
    (23, 27, 3, 4, 'leg'), (26, 27, 2, 3, 'foot'),
]

def block(parts=None, mirror_x=True, w=12, h=27, frame=0, pose='idle', slots=None):
    """an outline-free flat-block figure (03): a list of rects (y0, y1, x0, x1, slot[, mirror])
    painted in order, each mirrored about the centre column unless mirror_x is False or its 6th
    field is False. Separate it from the background by value, not by line. slots renames parts
    ({'cloak': 'robe2'}). pose 'idle' drawings 0-3 (bit 0: head and hat 1 px down, bit 1: the
    cloak hem 1 px wider), 'walk' 0-3 (one leg lifted 1 px with the hem swung toward it, pass,
    the other leg, pass)."""
    parts = BLOCK_HERO if parts is None else parts
    S = dict(slots or {})
    P = _P(w + 2, h + 1)
    ox = 1
    head_rows = [r for r in parts if r[4] in ('hat', 'hat_shade', 'head', 'visor')]
    head_bottom = max([r[1] for r in head_rows], default=0)
    for r in parts:
        y0, y1, x0, x1, s = r[:5]
        mir = mirror_x and (len(r) < 6 or r[5])
        P.rect(ox + x0, y0, ox + x1, y1, S.get(s, s))
        if mir:
            P.rect(ox + w - x1, y0, ox + w - x0, y1, S.get(s, s))
    cloak = S.get('cloak', 'cloak')
    hem = max([r[1] for r in parts if r[4] == 'cloak'], default=None)
    if pose == 'idle':
        if frame & 2 and hem:                           # the hem breathes out a pixel
            row = P.g[hem - 1]
            xs = np.nonzero(np.equal(row, cloak))[0]
            if len(xs):
                P.put(xs[0] - 1, hem - 1, cloak); P.put(xs[-1] + 1, hem - 1, cloak)
        if frame & 1:                                   # head bob: everything above the collar
            P.shift((0, head_bottom), 0, 1)
    elif pose == 'walk':
        f = frame % 4
        legs = [(ox + x0) for (y0, y1, x0, x1, s, *m) in parts if s == 'leg'] + [ox + w - 1 - x0 for (y0, y1, x0, x1, s, *m) in parts if s == 'leg']
        if f in (0, 2) and legs:
            lx = min(legs) if f == 0 else max(legs)
            col = P.g[:, lx]
            leg_rows = np.nonzero(np.equal(col, S.get('leg', 'leg')))[0]
            if len(leg_rows):                           # lift: the foot rises a row
                lo = leg_rows[-1]
                P.put(lx, lo, None)
                fx = lx - 1 if lx == min(legs) else lx + 1
                foot = S.get('foot', 'foot')
                if P.get(fx, lo) == foot:
                    P.put(fx, lo, None); P.put(fx, lo - 1, foot)
            if hem:
                P.shift((hem - 3, hem), -1 if f == 0 else 1, 0)
    return Figure(P.g, ox + w // 2, h - 1)

# ---------------------------------------------------------------- 04 / 10 chibi figures
# Hand-drawn parts (inner art, no outline: the outline pass adds it). Keys: hair K/H/h (3, 2, 1),
# skin L/S/s, eye E with glint w, shirt U/T/t, belt b, pants P/p, boots B/o, hat Z/A/a.
CHIBI_KEY = {'K': 'hair3', 'H': 'hair2', 'h': 'hair1', 'L': 'skin3', 'S': 'skin2', 's': 'skin1',
             'E': 'eye', 'w': 'glint', 'U': 'shirt3', 'T': 'shirt2', 't': 'shirt1', 'b': 'belt',
             'P': 'pants2', 'p': 'pants1', 'B': 'boot2', 'o': 'boot1', 'Z': 'hat3', 'A': 'hat2', 'a': 'hat1'}

CHIBI_HEADS = {
    ('down', 'tousle'): """
        ...HHHHH...
        .hHKKHHHHh.
        hHKKHHHHHHh
        hHKHHHHHHHh
        hHHHhHHHhHh
        hHShSSHSShh
        hhSSSSSSShh
        hSSESSSESSh
        hSSESSSESSh
        .sSSSSSSSs.
        ..ssSSSss..""",
    ('down', 'bob'): """
        ...HHHHH...
        .hHKKKHHHh.
        hHKKHHHHHHh
        hHHHHHHHHHh
        HHHHHHHHHHH
        HHhSSSSShHH
        HHSSSSSSSHH
        HhSESSSEShH
        HhSESSSEShH
        Hh.SSSSS.hH
        h...sSs...h""",
    ('down', 'spiky'): """
        .K..H.H..H.
        .HK.HHH.HH.
        hKKHHHHHHHh
        hHKHHHHHHHh
        hHHhHHHhHHh
        hHShSShSShh
        hhSSSSSSShh
        hSSESSSESSh
        hSSESSSESSh
        .sSSSSSSSs.
        ..ssSSSss..""",
    ('down', 'cap'): """
        ...AZZAA...
        ..AZZAAAA..
        .AAAAAAAAA.
        aaaaaaaaaaa
        hHSSSSSSSHh
        hhSSSSSSShh
        hSSESSSESSh
        hSSESSSESSh
        .sSSSSSSSs.
        ..ssSSSss..
        ...........""",
    ('up', '*'): """
        ...HHHHH...
        .hHKKHHHHh.
        hHKKHHHHHHh
        hHKHHHHHHHh
        hHHHHHHHHHh
        hHHHHHHHHHh
        hHHHHHHHHHh
        hhHHHHHHHhh
        .hhHHHHHhh.
        .shhhhhhhs.
        ..ssSSSss..""",
    ('side', 'tousle'): """
        ..HHHHH....
        .HKKHHHHh..
        HKKHHHHHHh.
        HKHHHHHHHh.
        HHHHHHhHhh.
        HHHHHhSSShS
        HHHHhSSSSSS
        hHHhSSSSESS
        hHHhSSSSESs
        .hhsSSSSSs.
        ...ssSSSs..""",
    ('side', 'bob'): """
        ..HHHHH....
        .HKKKHHHh..
        HKKHHHHHHh.
        HHHHHHHHHh.
        HHHHHHHHHH.
        HHHHHhSSSSH
        HHHHhSSSSSS
        HHHhSSSSESS
        HHHhSSSSESs
        HHh.SSSSSs.
        hh...sSSs..""",
    ('side', 'spiky'): """
        K...H..H...
        .KK.HHHH...
        HKKHHHHHHh.
        HKHHHHHHHh.
        HHHHHHhHhh.
        HHHHHhSSShS
        HHHHhSSSSSS
        hHHhSSSSESS
        hHHhSSSSESs
        .hhsSSSSSs.
        ...ssSSSs..""",
    ('side', 'cap'): """
        ..AZZAA....
        .AZZAAAAA..
        .AAAAAAAAA.
        .aaaaaaaaaaa
        HHHHhSSSShS
        HHHHhSSSSSS
        hHHhSSSSESS
        hHHhSSSSESs
        .hhsSSSSSs.
        ...ssSSSs..
        ...........""",
}
CHIBI_HAIR = ('tousle', 'bob', 'spiky', 'cap')

CHIBI_BODY = {
    'down': """
        ...tTTTt...
        .tTTUUTTTt.
        tTTTUTTTTTt
        tTtTTTTTtTt
        sStTTTTTtSs
        .sbbbbbbbs.
        ..PPPPPPP..""",
    'up': """
        ...tTTTt...
        .tTTTTTTTt.
        tTTUTTTTTTt
        tTtTTTTTtTt
        sStTTTTTtSs
        .sbbbbbbbs.
        ..PPPPPPP..""",
    'side': """
        ...tTTTt...
        ..tTUTTTt..
        ..tTUtTTt..
        ..tTUtTTt..
        ..tTTtTTt..
        ..bbbSbbb..
        ..PPPPPPP..""",
}
CHIBI_LEGS = {          # rows below the body; columns: left leg 2-4, right leg 6-8
    'down': """
        ..PPp.pPP..
        ..PPp.PPp..
        ..ppp.ppp..
        ..BBo.BBo..
        ..oBo.oBo..""",
    'side': """
        ...PPPPp...
        ...PPpPp...
        ...ppppp...
        ...BBBBBo..
        ...oooooo..""",
}

CHIBI_SIT = {           # seated legs, stamped where the standing legs start
    'down': """
        .pPPPPPPPp.
        ..PPp.pPP..
        ..BBo.BBo..
        ..oBo.oBo..""",
    'side': """
        ..PPPPPPPp.
        ..ppppPPPp.
        .......PPp.
        .......BBBo
        .......ooo.""",
    'up': """
        .pPPPPPPPp.""",
}

def chibi(seed=0, facing='down', hair=None, outline='part', ol='ol_char', frame=0, pose='idle', slots=None,
          parts=None, size=26):
    """a chibi actor (04 Sea of Stars, 10 Stardew): 13 x 26 with the outline, the head about 45%.
    facing 'down' (front), 'up' (back), 'side' (profile to the right; .flip() for left).
    hair: one of CHIBI_HAIR (default by seed; 'cap' is a brimmed hat). outline 'part' (each part
    lined in its own darkest step: hair0, skin0, shirt0 ..., 10), 'slot' (one tinted near-black
    `ol` round the silhouette, 04) or None. Slots are ramps hair/skin/shirt/pants/boot/hat
    (steps 0-3, 0 = the line colour) plus eye, glint, belt; slots={'shirt': 'coat'} renames a ramp.
    pose 'idle' (0 rest, 1 head and torso 1 px down) or 'walk' (0 left foot up, 1 pass with the
    body 1 px up, 2 right foot up, 3 pass). parts: your own ASCII {'head', 'body', 'legs', 'key'}
    (any subset; 11 columns, legs columns 2-4 and 6-8 so the walk can lift them; key extends
    CHIBI_KEY, 'sit' replaces the seated legs) in place of the built-in drawings.
    pose 'sit' (0 rest, 1 breath; CHIBI_SIT legs: lap and dangling shins from the front, thigh
    forward and shin down in profile, only the seat from the back): the anchor is the hips'
    lowest row, so stamp it on the row just above the seat (the outline lands on its edge).
    size: the height with the outline, 22-32 (default 26 = the 13 x 26 drawings unchanged); the
    head keeps its 11 rows and torso and leg rows are dropped or repeated (older figures get
    longer legs first). Every pose of one size shares one box."""
    hair = hair or _pick(CHIBI_HAIR, seed, 21)
    if facing not in ('down', 'up', 'side'):
        raise ValueError("facing: 'down', 'up' or 'side'")
    head = CHIBI_HEADS[(facing, '*')] if facing == 'up' else CHIBI_HEADS[(facing, hair)]
    body = CHIBI_BODY[facing]
    legs = CHIBI_LEGS['side' if facing == 'side' else 'down']
    key = CHIBI_KEY
    if parts:
        head, body, legs = parts.get('head', head), parts.get('body', body), parts.get('legs', legs)
        key = dict(CHIBI_KEY, **parts.get('key', {}))
    d = int(size) - 26
    if d:
        if not -4 <= d <= 6:
            raise ValueError('chibi size: 22-32')
        if not (parts and 'body' in parts):             # torso rows: drop or repeat the arm rows
            b = _rows(body)
            b = b[:2] + b[4:] if d <= -2 else b[:3] + b[4:] if d < 0 else b[:3] + [b[3]] * (1 + d // 2) + b[4:]
            body = '\n'.join(b)
        if not (parts and 'legs' in parts):             # leg rows: drop or repeat the shins
            l = _rows(legs)
            l = l[:1] + l[3:] if d <= -4 else l[:1] + l[2:] if d == -3 else l if d < 0 else \
                l[:1] + [l[1]] * (1 + (d + 1) // 2) + l[2:]
            legs = '\n'.join(l)
    hr, br, lr = _rows(head), _rows(body), _rows(legs)
    Hh, Hb, Hl = len(hr), len(br), len(lr)
    hand = 4 if not d else Hb - 3                       # the hand row inside the body drawing
    W, H = 13, Hh + Hb + Hl + 2
    P = _P(W + 2, H + 2)
    ox, oy = 2, 2                                       # 2 rows of headroom: the pass frames lift the head under its outline
    legy = oy + Hh + Hb
    if pose == 'sit':
        legs = parts.get('sit', CHIBI_SIT[facing]) if parts else CHIBI_SIT[facing]
    P.stamp(legs, key, ox, legy)
    P.stamp(body, key, ox, oy + Hh)
    P.stamp(head, key, ox, oy)
    if pose == 'walk' and facing != 'up':                # arms swing: one hand a row lower
        y = oy + Hh + hand
        if frame in (0, 2):
            near, far = (ox, ox + 10) if frame == 0 else (ox + 10, ox)
            if facing == 'down':
                P.put(near, y + 1, 'skin1')
                P.put(far, y, 'shirt1')
            else:
                for yy in range(oy + Hh + 2, oy + Hh + hand + 2):   # the near arm swings a column
                    if P.get(ox + 5, yy) in ('shirt1', 'skin2'):
                        P.put(ox + 5, yy, 'shirt2' if yy < oy + Hh + hand + 1 else 'belt')
                        P.put(ox + 5 + (1 if frame == 0 else -1), yy, 'shirt1' if yy < oy + Hh + hand + 1 else 'skin2')
    if pose == 'walk' and frame in (0, 2):              # a foot lifts: its leg columns rise a row
        if facing == 'side':
            cols = range(ox + 3, ox + 6) if frame == 0 else range(ox + 6, ox + 9)
        else:
            cols = range(ox + 2, ox + 5) if frame == 0 else range(ox + 6, ox + 9)
        for x in cols:
            col = P.g[legy + 1:legy + Hl, x].copy()
            P.g[legy + 1:legy + Hl, x] = None
            P.g[legy + 1:legy + Hl - 1, x] = col[1:]
    if pose == 'walk' and frame in (1, 3):              # pass: the body rises, the hips stretch
        P.shift((0, legy), 0, -1)
        P.g[legy - 1] = P.g[legy]
    if pose in ('idle', 'sit') and frame == 1:          # breath: head and torso settle a pixel
        P.shift((0, legy), 0, 1)
    if outline:
        _outline(P.g, outline, ol=ol)
    f = Figure(P.g, ox + 5, oy + H - 3 if pose != 'sit' else legy + (1 if facing == 'side' else 0))
    return f.recolor(slots) if slots else f

# ---------------------------------------------------------------- 07 iso people
# Inner art 12 x 34 (the black outline makes it 14 x 36), 3/4 view facing 'se', light from the
# right (07's convention). Keys: hair K/H/h, skin L/S/s with features f, shirt U/T/t, pants
# Q/P/p, shoes B/b, black seams o. Parts are stacked: head rows 0-10, neck 11, torso 12-21,
# legs 22-33.
ISO_KEY = {'K': 'hair3', 'H': 'hair2', 'h': 'hair1', 'L': 'skin3', 'S': 'skin2', 's': 'skin1',
           'f': 'skin0', 'U': 'shirt3', 'T': 'shirt2', 't': 'shirt1', 'Q': 'pants3', 'P': 'pants2',
           'p': 'pants1', 'B': 'shoe2', 'b': 'shoe1', 'o': 'ol', 'Z': 'hat3', 'A': 'hat2', 'a': 'hat1'}

ISO_HEADS = {
    'crop': """
        ....hhHH....
        ..hhHHHHKK..
        .hHHHHHHHKK.
        .hHHHHHHHHK.
        .hHHHSSSSSH.
        .hHHSSSSSSS.
        .hHSSfSSfSS.
        ..hSSSSSSSSL
        ..hsSSSSSSS.
        ...sSSffSS..
        ....sSSSS...""",
    'long': """
        ....hhHH....
        ..hhHHHHKK..
        .hHHHHHHHKK.
        hHHHHHHHHHK.
        hHHHHSSSSSH.
        hHHHSSSSSSS.
        hHHSSfSSfSS.
        hhHSSSSSSSSL
        hhHsSSSSSSS.
        hhH.sSffSS..
        .hh.sSSSS...""",
    'pigtails': """
        ....hhHH....
        ..hhHHHHKK..
        hhHHHHHHHKKh
        hHhHHHHHHHKH
        .h.hHSSSSSH.
        ...HSSSSSSS.
        ..hSSfSSfSS.
        ..hSSSSSSSSL
        ..hsSSSSSSS.
        ...sSSffSS..
        ....sSSSS...""",
    'afro': """
        ..hhHHHHKK..
        .hHHHHHHHKK.
        hHHHHHHHHHKK
        hHHHHHHHHHHK
        hHHHHSSSSSHH
        hHHHSSSSSSSH
        .hHSSfSSfSS.
        ..hSSSSSSSSL
        ..hsSSSSSSS.
        ...sSSffSS..
        ....sSSSS...""",
    'cap': """
        ....aAAAZ...
        ...aAAAAAZ..
        ..aAAAAAAAZ.
        ..aaaaaaaAAAA
        .hHHHaaaaaa.
        .hHHSSSSSSS.
        .hHSSfSSfSS.
        ..hSSSSSSSSL
        ..hsSSSSSSS.
        ...sSSffSS..
        ....sSSSS...""",
}
ISO_HAIR = ('crop', 'long', 'pigtails', 'afro', 'cap')

ISO_TORSO = {
    'tee': """
        .....sSS....
        ...tTTTTUU..
        ..tTTTTTTUU.
        .ttTTTTTTTUU
        .tToTTTTToUU
        .tToTTTTToUU
        .tToTTTTToUU
        .sSoTTTTToSL
        .sSotTTTToSL
        .sSotTTTToSL
        .ss.tTTTT.sS""",
    'tank': """
        .....sSS....
        ...sTTTTSL..
        ..sSTTTTTSL.
        .sSoTTTTToSL
        .sSoTTTTToSL
        .sSoTTTTToSL
        .sSoTTTTToSL
        .sSoTTTTToSL
        .sSotTTTToSL
        .sSotTTTToSL
        .ss.tTTTT.sS""",
    'jacket': """
        .....sSS....
        ...tTTUTUU..
        ..tTTTUTTUU.
        .ttTTTUTTTUU
        .tToTTUTToUU
        .tToTTUTToUU
        .tToTTUTToUU
        .tToTTUTToUU
        .tTotTUTToTU
        .sSotTUTToSL
        .ss.tTUTT.sS""",
}
ISO_CUT = ('tee', 'tank', 'jacket')

ISO_LEGS = {
    'stand': """
        ...pPPPPQ...
        ...pPPoPPQ..
        ...pPPoPPQ..
        ...pPP.pPQ..
        ...pPP.pPQ..
        ...pPP.pPQ..
        ...pPP.pPQ..
        ...pPP.pPQ..
        ...pPP.pPQ..
        ...pPP.pPQ..
        ..bBBB.bBBB.
        ..bbbb.bbbb.""",
    'walk0': """
        ...pPPPPQ...
        ...pPPoPPQ..
        ..pPPPoPPQ..
        ..pPP..pPQ..
        ..pPP..pPQ..
        .pPP...pPPQ.
        .pPP....pPQ.
        .pPP....pPQ.
        pPP.....pPQ.
        pPP......pPQ
        bBBB.....bBBB
        bbbb.....bbbb""",
    'walk1': """
        ...pPPPPQ...
        ...pPPoPPQ..
        ...pPPoPPQ..
        ...pPPopPQ..
        ....pPPpQ...
        ....pPPPQ...
        ....pPPPQ...
        ....pPPPQ...
        ....pPPPQ...
        ....pPPPQ...
        ...bBBBB....
        ...bbbbb....""",
    'sit': """
        ...pPPPPQ...
        ...pPPPPPQQQ
        ...pPPPPPPPQ
        .......pPPP.
        .......pPP..
        .......pPP..
        ......bBBB..
        ......bbbb..
        ............
        ............
        ............
        ............""",
}

def iso_person(seed=0, facing='se', pose='stand', frame=0, pal=None, hair=None, cut=None):
    """a 07 sticker person: 14 x 36 at 3.3 heads, a black outline and black seams, loud hair, 3 tones
    per material (steps 1-3), light from the right. facing 'se' (3/4 toward the viewer, right)
    or 'sw' (mirrored). pal: {'hair', 'skin', 'shirt', 'pants', 'shoe'} -> ramp names (default by
    seed from ISO_RAMPS, which PALETTES['iso_person'] defines). hair: one of ISO_HAIR, cut: one
    of ISO_CUT (default by seed). pose 'stand', 'idle' (1: a 1 px head bob), 'walk' (0 stride,
    1 pass, 2 the other stride, 3 pass; arms swing with the stride), 'wave' (1: the near arm up),
    'sit' (legs forward: place the anchor on the seat)."""
    hair = hair or _pick(ISO_HAIR, seed, 31)
    cut = cut or _pick(ISO_CUT, seed, 32)
    ramps = {k: _pick(v, seed, 40 + i) for i, (k, v) in enumerate(ISO_RAMPS.items())}
    if ramps['pants'] == ramps['shirt']:
        ramps['pants'] = 'jeans'
    ramps['hat'] = _pick([r for r in ISO_RAMPS['shirt'] if r != ramps['shirt']], seed, 49)
    ramps.update(pal or {})
    legs = 'stand'
    if pose == 'walk':
        legs = ('walk0', 'walk1', 'walk0', 'walk1')[frame % 4]
    elif pose == 'sit':
        legs = 'sit'
    W, H = 15, 39
    P = _P(W, H)
    ox, oy = 1, 2                                       # 2 rows of headroom: the walk passes lift the head
    P.stamp(ISO_LEGS[legs], ISO_KEY, ox, oy + 22)
    if pose == 'walk' and frame % 4 == 2:               # the other stride: swap which leg leads
        band = P.g[oy + 22 + 3:oy + 34].copy()
        P.g[oy + 22 + 3:oy + 34] = None
        P.g[oy + 22 + 3:oy + 34, ox:ox + 12] = band[:, ox:ox + 12][:, ::-1]
    P.stamp(ISO_TORSO[cut], ISO_KEY, ox, oy + 11)
    P.stamp(ISO_HEADS[hair], ISO_KEY, ox, oy)
    bob = 0
    if pose == 'walk' and frame % 4 in (1, 3):
        bob = -1
    if pose == 'idle' and frame == 1:
        bob = 1
    if pose == 'walk' and frame % 4 in (0, 2):          # arms swing: hands trade a row
        d = 1 if frame % 4 == 0 else -1
        for x0 in (ox + 1, ox + 10):
            col = P.g[oy + 18:oy + 22, x0:x0 + 2].copy()
            P.g[oy + 18:oy + 22, x0:x0 + 2] = None
            sh = d if x0 > ox + 5 else -d
            P.g[oy + 18 + max(0, sh):oy + 22 + min(0, sh), x0:x0 + 2] = col[max(0, -sh):4 - max(0, sh)]
    if pose == 'wave' and frame % 2 == 1:               # the near forearm up beside the head
        P.g[oy + 18:oy + 22, ox + 10:ox + 12] = None
        P.g[oy + 18:oy + 21, ox + 10] = 'ol'
        P.rect(ox + 11, oy + 7, ox + 13, oy + 16, 'skin2')
        P.rect(ox + 12, oy + 7, ox + 13, oy + 16, 'skin3')
        P.rect(ox + 11, oy + 5, ox + 13, oy + 7, 'skin3')
    if bob:
        P.shift((0, oy + 22), 0, bob)
        if bob < 0:
            P.g[oy + 21] = np.where(np.equal(P.g[oy + 21], None), P.g[oy + 22], P.g[oy + 21])
    _outline(P.g, 'slot', ol='ol')
    g = P.g
    mapping = {'hair': ramps['hair'], 'skin': ramps['skin'], 'shirt': ramps['shirt'],
               'pants': ramps['pants'], 'shoe': ramps['shoe'], 'hat': ramps['hat']}
    f = Figure(g, ox + 6, oy + 33 + (1 if pose != 'sit' else -4)).recolor(mapping)
    if pose == 'sit':
        f.ay = oy + 22 + 3
    return f.flip() if facing == 'sw' else f

ISO_RAMPS = {
    'hair': ('hgreen', 'hred', 'hblond', 'hblack', 'hbrown', 'hblack'),
    'skin': ('skinA', 'skinB', 'skinC', 'skinD'),          # each ramp has a step 0 for features
    'shirt': ('red', 'yellow', 'pink', 'white', 'teal', 'green', 'blue'),
    'pants': ('jeans', 'khaki', 'black', 'red', 'green'),
    'shoe': ('brown', 'black', 'orange'),
}

# ---------------------------------------------------------------- 09 thin figures
# A joint rig in 42 px units (the measured 09 standing man: 42 px, head 7 x 9, 4.7 heads), y down
# from the top of the head, x from the body's centre line, + toward the facing side. Keys: head
# (centre), sh (shoulders back/front), el, ha (elbow, hand), hip, kn, ft (back b / front f).
# The rig is scaled by h / 42 and every limb drawn as a constant-width run (arms 3 to 2 px,
# legs 4 to 3 px at 42), back limbs one step darker.
THIN_POSES = {
    'stand': [
        dict(head=(0.5, 4.5), shb=(-5, 11), shf=(5, 11), elb=(-6, 18), hab=(-6, 25), elf=(6, 18), haf=(6.5, 25),
             hipb=(-2, 23), knb=(-3, 32), ftb=(-4, 40), hipf=(2, 23), knf=(3, 32), ftf=(4.5, 40), waist=4, lean=0),
        dict(head=(0.5, 5.5), shb=(-5, 12), shf=(5, 12), elb=(-6, 19), hab=(-6, 25), elf=(6, 19), haf=(6.5, 25),
             hipb=(-2, 23), knb=(-3, 32), ftb=(-4, 40), hipf=(2, 23), knf=(3, 32), ftf=(4.5, 40), waist=4, lean=0)],
    'walk': [
        dict(head=(1, 4.5), shb=(-2.5, 11), shf=(2.5, 11), elb=(1.5, 18), hab=(4.5, 23), elf=(-2, 18), haf=(-4.5, 24),
             hipb=(-1, 23), knb=(-3.5, 32), ftb=(-7, 40), hipf=(1, 23), knf=(4.5, 31), ftf=(7.5, 40), waist=2.5, lean=0),
        dict(head=(1, 3.5), shb=(-2.5, 10), shf=(2.5, 10), elb=(0, 17), hab=(1, 23), elf=(0, 17), haf=(-0.5, 23),
             hipb=(-1, 22), knb=(1.5, 30), ftb=(-1.5, 37), hipf=(1, 22), knf=(1, 31), ftf=(1, 40), waist=2.5, lean=0),
        dict(head=(1, 4.5), shb=(-2.5, 11), shf=(2.5, 11), elb=(-2, 18), hab=(-4.5, 24), elf=(1.5, 18), haf=(4.5, 23),
             hipb=(-1, 23), knb=(4.5, 31), ftb=(7.5, 40), hipf=(1, 23), knf=(-3.5, 32), ftf=(-7, 40), waist=2.5, lean=0),
        dict(head=(1, 3.5), shb=(-2.5, 10), shf=(2.5, 10), elb=(0, 17), hab=(-0.5, 23), elf=(0, 17), haf=(1, 23),
             hipb=(-1, 22), knb=(1, 31), ftb=(1, 40), hipf=(1, 22), knf=(1.5, 30), ftf=(-1.5, 37), waist=2.5, lean=0)],
    'run': [
        dict(head=(4, 5.5), shb=(0, 12), shf=(4, 12), elb=(5, 17), hab=(9, 15), elf=(-3, 17), haf=(-6, 21),
             hipb=(-1, 24), knb=(-6, 30), ftb=(-12, 33), hipf=(1, 24), knf=(7, 30), ftf=(8, 39), waist=2.5, lean=2),
        dict(head=(4, 4.5), shb=(0, 11), shf=(4, 11), elb=(1, 17), hab=(4, 20), elf=(1, 17), haf=(3, 21),
             hipb=(-1, 23), knb=(4, 29), ftb=(-1, 34), hipf=(1, 23), knf=(1, 31), ftf=(0, 40), waist=2.5, lean=2),
        dict(head=(4, 5.5), shb=(0, 12), shf=(4, 12), elb=(-3, 17), hab=(-6, 21), elf=(5, 17), haf=(9, 15),
             hipb=(-1, 24), knb=(7, 30), ftb=(8, 39), hipf=(1, 24), knf=(-6, 30), ftf=(-12, 33), waist=2.5, lean=2),
        dict(head=(4, 4.5), shb=(0, 11), shf=(4, 11), elb=(1, 17), hab=(3, 21), elf=(1, 17), haf=(4, 20),
             hipb=(-1, 23), knb=(1, 31), ftb=(0, 40), hipf=(1, 23), knf=(4, 29), ftf=(-1, 34), waist=2.5, lean=2)],
}

def thin(h=38, seed=0, facing=1, pose='stand', frame=0, light_dir=1, rim=True, slots=None, vest=None,
         hat=None, sword=None):
    """a thin noir actor (09): 0.175 H tall (38 px on 216 lines), 4.7 heads, no outline, limbs 2-4 px
    from a joint rig, back limbs one step darker. facing 1 = right. light_dir: the side the lamp is
    on (+1 right, -1 left, 0 none); rim=True draws a 1 px warm rim down that contour ('rim1' on
    the shirt and skin, 'rim0' elsewhere), never on the soles. vest: a dark waistcoat over the
    shirt (default by seed). Ramps shirt/vest/pants/skin/hair/shoe steps 1-3; slots renames them.
    pose 'stand' (0, 1 breath), 'walk' (4 keys), 'run' (4 keys, leaning).
    hat: None, 'brim' (a low crown under a 1 px flat brim 13 px wide at 42, its front tip 1 px
    down) or 'cone' (a wide shallow cone with a 1 px rim, a straw rain hat); ramp 'hat' steps
    1-3. sword: None, 'sheathed' (a 2 px scabbard off the back hip, 25 degrees down, the hilt
    forward of the belt) or 'drawn' (the empty scabbard plus a 1 px blade held low and forward
    in the front hand); ramps 'sheath' and 'blade' steps 1-3, 'grip' for the hilt wrap.
    Both default to None, which draws exactly the plain figure."""
    S = dict(slots or {})
    if facing < 0:                                      # draw facing right with the lamp mirrored
        return thin(h, seed, 1, pose, frame, -light_dir, rim, slots, vest, hat, sword).flip()
    sc = h / 42.0
    vest = (_h(seed, 61) < 0.6) if vest is None else vest
    keys = THIN_POSES[pose][frame % len(THIN_POSES[pose])]
    W = int(round(30 * sc)) + 6
    pad = int(math.ceil(1.2 * sc)) + (int(math.ceil(3 * sc)) if hat else 0)   # headroom: the walk passes lift the head (and a hat)
    P = _P(W, h + 2 + pad, oy=pad)
    cx = W // 2
    def pt(k):
        x, y = keys[k]
        return cx + x * sc, y * sc
    def lw(a):
        return max(1, int(round(a * sc)))
    r = lambda b, k: S.get(b, b) + str(k)
    # back limbs (one step darker)
    for a, b, w0, w1, slot in (('hipb', 'knb', 4, 3, r('pants', 1)), ('knb', 'ftb', 3, 3, r('pants', 1))):
        P.stroke(*pt(a), *pt(b), lw(w0), lw(w1), v=slot)
    x, y = pt('ftb'); P.rect(x - lw(2), y - lw(1.5), x + lw(3), y + 1, r('shoe', 1))
    for a, b, w0, w1, slot in (('shb', 'elb', 3, 3, r('shirt', 1)), ('elb', 'hab', 2.5, 2, r('shirt', 1))):
        P.stroke(*pt(a), *pt(b), lw(w0), lw(w1), v=slot)
    x, y = pt('hab'); P.rect(x - lw(1), y, x + lw(1) + 1, y + lw(2), r('skin', 1))
    # torso: shoulders to waist, a shirt with a dark vest panel and a collar
    (sbx, sby), (sfx, sfy) = pt('shb'), pt('shf')
    wy = (keys['hipb'][1] + 0.5) * sc
    lean = keys['lean'] * sc
    hw = keys['waist'] * sc
    y0, y1 = int(math.floor(min(sby, sfy) - 1 * sc)), int(math.floor(wy))
    for yy in range(y0, y1):
        u = (yy - y0) / max(1, y1 - y0)
        xl = sbx + (cx - hw - sbx) * u - lean * (1 - u) * 0 + lean * (1 - u) * 0
        xr = sfx + (cx + hw - sfx) * u
        xl, xr = int(math.floor(xl + 0.5)), int(math.floor(xr + 0.5))
        P.rect(xl, yy, xr + 1, yy + 1, r('shirt', 2))
        if vest and u > 0.12:                           # an open waistcoat: dark sides, a shirt
            m = (xr - xl) / 2.0                         # front with a dark tie down the middle
            if keys['waist'] < 3.5:                     # side view: the vest covers the back half
                P.rect(xl, yy, int(math.floor(xl + m + 0.5)), yy + 1, r('vest', 2))
            else:
                k = max(1, int(round(m * 0.55)))
                P.rect(xl, yy, xl + k, yy + 1, r('vest', 2))
                P.rect(xr - k + 1, yy, xr + 1, yy + 1, r('vest', 2))
                if u < 0.7:
                    P.put(int(math.floor((xl + xr) / 2.0 + 0.5)), yy, r('vest', 1))
        P.put(xr if light_dir >= 0 else xl, yy, r('shirt', 3))
    P.rect(int(math.floor(cx - hw + 0.5)), y1 - 1, int(math.floor(cx + hw + 0.5)) + 1, y1, r('pants', 1))   # belt
    # front leg, shoes, front arm
    P.stroke(*pt('hipf'), *pt('knf'), lw(4), lw(3.5), v=r('pants', 2))
    P.stroke(*pt('knf'), *pt('ftf'), lw(3.5), lw(3), v=r('pants', 2))
    x, y = pt('ftf'); P.rect(x - lw(2), y - lw(1.5), x + lw(3.5), y + 1, r('shoe', 2))
    if sword:                                           # scabbard off the back hip, the hilt forward
        hx_, hy_ = cx + 0.5 * sc, (keys['hipb'][1] - 0.5) * sc
        ang = math.radians(25)
        L = 17 * sc
        ex, ey = hx_ - L * math.cos(ang), hy_ + L * math.sin(ang)
        P.stroke(hx_, hy_, ex, ey, lw(2), lw(2), v=r('sheath', 2))
        P.line(hx_, hy_ - 1, ex, ey - 1, r('sheath', 3))                  # the lit top edge
        P.put(ex, ey, r('sheath', 1))                                     # the chape
        gx, gy = hx_ + 1.5 * sc, hy_ - 0.7 * sc
        P.rect(gx, gy - lw(1.5), gx + 1, gy + lw(1.5) + 1, r('sheath', 1)) # the guard
        if sword != 'drawn':
            P.line(gx + 1, gy, gx + 5.5 * sc * math.cos(ang), gy - 5.5 * sc * math.sin(ang), S.get('grip', 'grip'))
    P.stroke(*pt('shf'), *pt('elf'), lw(3), lw(3), v=r('shirt', 2))
    P.stroke(*pt('elf'), *pt('haf'), lw(2.5), lw(2), v=r('shirt', 2))
    x, y = pt('haf'); P.rect(x - lw(1), y, x + lw(1) + 1, y + lw(2.5), r('skin', 2))
    if sword == 'drawn':                                # the blade low and forward from the front hand
        hx_, hy_ = x + 0.5, y + lw(1.2)
        bl = 20 * sc
        a2 = math.radians(30)
        P.line(hx_, hy_, hx_ - 3 * sc * math.cos(a2), hy_ - 3 * sc * math.sin(a2), S.get('grip', 'grip'))
        P.line(hx_ + 1, hy_, hx_ + bl * math.cos(a2), hy_ + bl * math.sin(a2), r('blade', 2))
        P.put(hx_ + 1, hy_ - 1, r('blade', 1))                            # the guard
        P.put(hx_ + 1, hy_ + 1, r('blade', 1))
    # head: a 7 x 9 oval (at 42), hair over the top and the back, one eye pixel, a jaw shadow
    hx, hy = pt('head')
    hw2, hh2 = 3.5 * sc, 4.5 * sc
    for yy in range(int(math.floor(hy - hh2)), int(math.ceil(hy + hh2))):
        v = (yy + 0.5 - hy) / hh2
        half = hw2 * math.sqrt(max(0.0, 1 - v ** 4))
        xl, xr = int(math.floor(hx - half + 0.5)), int(math.floor(hx + half - 0.5))
        for xx in range(xl, xr + 1):
            back = (xx - hx) < -0.3 * hw2
            hair = v < -0.35 or (back and v < 0.45)
            P.put(xx, yy, r('hair', 2 if xx > hx - hw2 * 0.6 and v < -0.6 else 1) if hair else
                  r('skin', 3 if (xx - hx) * (light_dir or 1) > 0.4 * hw2 else 2))
    P.put(hx + 1.6 * sc, hy - 0.1 * hh2, r('hair', 1))           # the eye
    P.rect(int(hx - 1 * sc), int(hy + hh2) - 1, int(hx + 2.5 * sc) + 1, int(hy + hh2), r('skin', 1))   # jaw
    P.rect(int(math.floor(hx - 1 * sc)), int(hy + hh2), int(math.floor(hx + 1.5 * sc)) + 1, y0 + 1, r('skin', 1))  # neck
    if hat == 'brim':                                   # a low crown, a flat brim tipped down at the front
        top = int(math.floor(hy - hh2))
        by = top + max(2, int(round(2.5 * sc)))
        P.rect(int(math.floor(hx - 3 * sc + 0.5)), top - 1, int(math.floor(hx + 3 * sc + 0.5)) + 1, by, r('hat', 2))
        P.rect(int(math.floor(hx - 3 * sc + 0.5)), top - 1, int(math.floor(hx + 3 * sc + 0.5)) + 1, top, r('hat', 3))
        bx0, bx1 = int(math.floor(hx - 6 * sc + 0.5)), int(math.floor(hx + 6.5 * sc + 0.5))
        P.rect(bx0, by, bx1 - 1, by + 1, r('hat', 1))
        P.put(bx1 - 1, by + 1, r('hat', 1))
        P.put(bx1 - 2, by + 1, r('hat', 1))
    elif hat == 'cone':                                 # a wide shallow cone: the slope steps 2 px per row
        top = int(math.floor(hy - hh2)) - 2
        rows = max(3, int(round(4 * sc)))
        for k in range(rows):
            half = 1 + int(round(k * (7 * sc - 1) / max(1, rows - 1)))
            P.rect(int(math.floor(hx + 0.5)) - half, top + k, int(math.floor(hx + 0.5)) + half + 1, top + k + 1,
                   r('hat', 3 if k < rows // 2 else 2))
        half = 1 + int(round(7 * sc - 1))
        P.rect(int(math.floor(hx + 0.5)) - half, top + rows, int(math.floor(hx + 0.5)) + half + 1, top + rows + 1, r('hat', 1))
    # rim: contour pixels facing the lamp, warm, from the eye row down to the hips (09: neck to
    # hips); never on the hair, the soles or the crown
    g = P.g
    if rim and light_dir:
        m = ~np.equal(g, None)
        cols = np.arange(g.shape[1])
        rows = np.nonzero(m.any(1))[0]
        start = int(math.floor(hy)) + pad
        stop = int(round(keys['hipb'][1] * sc)) + pad   # 09: the rim runs down the torso only
        hair = S.get('hair', 'hair')
        for yy in rows[(rows >= start) & (rows < stop)]:
            xs = cols[m[yy]]
            xx = xs.max() if light_dir > 0 else xs.min()
            v = str(g[yy, xx])
            if v.startswith(hair):
                continue
            g[yy, xx] = 'rim1' if v.startswith((S.get('shirt', 'shirt'), S.get('skin', 'skin'))) else 'rim0'
    f = Figure(g, cx, int(round(40 * sc)) + pad)
    return f

# ---------------------------------------------------------------- 10 creatures: slime, cat, gull
def _inner(m):
    """bool: set pixels whose 4 neighbours are all set (the mask minus its 1 px ring)"""
    p = np.pad(m, 1)
    return m & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]

def slime(hop=None, w=12, h=13, seed=0, facing=1, blink=False, slots=None, light_dir=-1, inside=None,
          glint=True):
    """a slime body (10 Stardew creatures, an original design): a toy-ramp dome on a flat base,
    sized each frame by anim.hop, outlined in its own darkest step, lit from the upper left, a
    2 px near-white glint and two 1 x 2 dash eyes (no antenna, no dot eyes).
    hop: an anim.Hop (its w, h and alt) or a (w, h) pair; None = at rest at w x h (outline
    included: 12 x 13 by default). Slots: the 'slime' ramp, steps 0-4 as palette.ramp(base,
    style='toy') gives them (0 the line, 1 shade, 2 body, 3 light, 4 glint), plus 'eye'
    (default slime0); slots={'slime': 'goo'} renames the ramp. facing +1/-1: the eyes sit 1 px
    toward that side. blink: the eyes close (2 x 1 dashes). light_dir -1: light from the upper
    left, +1 upper right. inside: a slot for a 2 x 2 swallowed lump low in the body (place by
    seed), None for none. The box is (w + 4) x (h + 7) for every HOP8 pose (alt up to 4), the
    anchor the ground pixel under the centre; alt lifts the body off it, so stamp on the ground.
        h = anim.hop(t, T, 12, 13); fg.slime(h, facing=1, blink=anim.hold(tab, t)).stamp(c, x, y)"""
    if hop is None:
        bw, bh, alt = int(w), int(h), 0
    elif hasattr(hop, 'alt'):
        bw, bh, alt = int(hop.w), int(hop.h), int(hop.alt)
    else:
        bw, bh, alt = int(hop[0]), int(hop[1]), 0
    S = dict(slots or {})
    r = lambda k: S.get('slime', 'slime') + str(k)
    eye = S.get('eye', r(0))
    W, H = int(w) + 4, int(h) + 3 + max(4, alt)
    g = np.full((H, W), None, object)
    x0 = (W - bw) // 2
    base = H - 1 - alt                                  # the body's bottom row
    top = base - bh + 1
    # silhouette: a half superellipse standing on the base, the bottom corners cut by a pixel;
    # the inset only grows going up, so every curve is a clean stair
    a = bw / 2.0
    m = np.zeros((H, W), bool)
    prev = 0
    for j in range(bh):                                 # j = 0 is the base row
        if j == 0:
            k = 1
        else:
            v = min(1.0, (j - 0.5) / max(1.0, bh - 1.0))
            k = int(math.floor(a - a * (1 - v ** 2.8) ** (1 / 2.8) + 0.5))
            k = 0 if j == 1 else max(k, prev)
        prev = k if j else 0
        if bw - 2 * k <= 0:
            break
        m[base - j, x0 + k:x0 + bw - k] = True
    rows = np.nonzero(m.any(1))[0]
    top = int(rows.min())
    bh = base - top + 1
    ring = m & ~_inner(m)
    cx = x0 + (bw - 1) / 2.0
    ld = -1 if light_dir < 0 else 1
    lx, ly = cx + ld * 0.3 * a, top + bh * 0.36
    for y, x in zip(*np.nonzero(m)):
        u = (x - cx) / a * (-ld)                        # +1 on the side away from the light
        v = (y - (top + bh * 0.5)) / (bh * 0.5)         # +1 at the base
        g[y, x] = r(2)
        if y >= base - 1 or u * 0.7 + v * 0.7 > 0.6:    # a core shadow on the far low side
            g[y, x] = r(1)
        if ((x - lx) / (0.4 * a)) ** 2 + ((y - ly) / (0.24 * bh)) ** 2 < 1.0:
            g[y, x] = r(3)
    g[ring] = r(0)
    if glint:                                           # 2 px near white at the lit patch's light-side top
        lit = np.argwhere(np.equal(g, r(3)))
        if len(lit):
            y = lit[:, 0].min()
            xs = lit[lit[:, 0] == y][:, 1]
            gx = xs.min() if ld < 0 else xs.max()
            g[y, gx] = r(4)
            if g[y + 1, gx] == r(3):
                g[y + 1, gx] = r(4)
    # eyes: two dashes just above the middle, 1 px toward the facing side
    ey = top + int(round(bh * 0.42))
    half = max(1, int(round(bw * 0.1)))
    f = 1 if facing > 0 else -1
    for ex in (int(math.floor(cx)) - half + f, int(math.ceil(cx)) + half + f):
        while ring[ey, ex] or ring[ey + 1, ex] or (blink and ring[ey + 1, ex - f]):
            ex -= f                                     # keep both eyes off the line
        if blink:
            g[ey + 1, ex] = eye
            g[ey + 1, ex - f] = eye
        else:
            g[ey, ex] = eye
            g[ey + 1, ex] = eye
    if inside:                                          # a swallowed lump, 2 x 2, low in the body
        ix = int(math.floor(cx)) - 2 + int(_h(seed, 81) * 3)
        iy = base - 3 - int(_h(seed, 82) * 2)
        if iy > ey + 2:
            g[iy:iy + 2, ix:ix + 2] = inside
    return Figure(g, W // 2, H - 1, {'body': m})

# Cat drawings, side view facing right, the line drawn by hand (at this size an outline pass
# would swallow the ears). Keys: o line, D shade, F fur, L lit back, e eye. Bottom aligned in one
# 16 x 11 box; the walk's last two rows are its legs, one pair of rows per drawing (CAT_WALK_LEGS).
CAT_SIT = """
        ..o...o.....
        .oLo.oLo....
        .oLLLLLLo...
        .oFFFFeFFo..
        .oFFFFFFo...
        ..oFFFFo....
        .oLFFFFFo...
        oLFFFFFFFo..
        oFFFFFFLLoo.
        oDDDDDDDDDDo
        .oooooooooo."""
CAT_SLEEP = """
        ...oooo..o..o
        ..oLLLLooLooLo
        .oLFFFFLoLLLLo
        oLFFFFFFFFeFFo
        oDFFFFFFFDDDo.
        oDDDDDDDDDDDo.
        .ooooooooooo.."""
CAT_WALK = """
        .o.........o..o.
        oDo.......oLooLo
        .oDo......oLLLLo
        ..oLoooooooFFeFFo
        ..oLLLLLLLFFFFoo.
        ..oFFFFFFFFFDo...
        ..oDDDDDDDDDDo...
        .................
        ................."""
CAT_WALK_LEGS = (("...oo.....oo...", "..o..o....oo..."),   # stride: hind pair spread, fore pair under
                 ("...o.o....o.o..", "...o.o....o.o.."),   # pass
                 ("...oo.....oo...", "...oo....o..o.."),   # the other stride: fore pair spread
                 ("..o.o.....o.o..", "..o.o.....o.o.."))   # pass

def _cat_edit(rows, edits):
    """rows with single pixels replaced: edits [(y, x, ch), ...], y counted from the bottom row"""
    rows = [list(r) for r in rows]
    for y, x, ch in edits:
        rr = rows[len(rows) - 1 - y]
        rr.extend('.' * (x + 1 - len(rr)))
        rr[x] = ch
    return [''.join(r) for r in rows]

def cat(seed=0, pose='sit', frame=0, facing=1, slots=None, outline='part', ol='ol_char'):
    """a small cat (10 Stardew's farm animals, an original design), side view: 'sit' 12 x 11
    (the tail along the paws; frames 0 rest, 1 tail tip up, 2 tail tip curled high: the flick),
    'sleep' 14 x 7 (a curled loaf, chin on the paws, eye shut; 0 rest, 1 breath: the back rises
    a pixel, 2 the tail tip flicks up), 'walk' 17 x 9 (4 drawings: stride, pass, other stride,
    pass; tail up). All poses share one 17 x 11 box, so a pose change never jumps. facing 1 =
    right. Slots: the 'cat' ramp, steps 0-3 (0 the line, 1 shade, 2 fur, 3 lit back) and
    'cateye'; slots={'cat': 'ginger'} renames the ramp. outline 'part' (the line in cat0),
    'slot' (one tinted near-black `ol`) or None (the line in cat1: a black cat in a no-outline
    style keeps its ears)."""
    if pose not in ('sit', 'sleep', 'walk'):
        raise ValueError("pose: 'sit', 'sleep' or 'walk'")
    S = dict(slots or {})
    r = lambda k: S.get('cat', 'cat') + str(k)
    line = {'part': r(0), 'slot': ol}.get(outline, r(1))
    key = {'o': line, 'D': r(1), 'F': r(2), 'L': r(3), 'e': S.get('cateye', 'cateye')}
    k = frame % (4 if pose == 'walk' else 3)
    if pose == 'sit':
        rows = _rows(CAT_SIT)
        if k == 1:
            rows = _cat_edit(rows, [(3, 10, 'o'), (2, 10, 'D'), (2, 11, 'o')])
        elif k == 2:
            rows = _cat_edit(rows, [(4, 10, 'o'), (3, 10, 'D'), (3, 11, 'o'), (2, 10, 'D'), (2, 11, 'o')])
    elif pose == 'sleep':
        rows = _rows(CAT_SLEEP)
        rows[3] = rows[3].replace('e', 'F')             # asleep: the eye shut
        if k == 1:                                      # breath: the back rises a pixel, the head stays
            rows = ['...oooo', '..oLLLLo' + rows[0][8:], '.oLFFFFLo' + rows[1][9:],
                    'oLFFFFFFo' + rows[2][9:]] + rows[3:]
        elif k == 2:
            rows = _cat_edit(rows, [(1, 13, 'o'), (2, 13, 'o'), (1, 12, 'D'), (0, 12, 'o')])
    else:
        rows = _rows(CAT_WALK)
        legs = CAT_WALK_LEGS[k]
        rows = rows[:7] + ([legs[0]] if k % 2 else []) + list(legs)   # passes: the body rides a pixel up
    W, H = 17, 11
    P = _P(W, H)
    art = '\n'.join(rows)
    P.stamp(art, key, 0, H - len(rows))
    f = Figure(P.g, 7, H - 1)
    return f if facing > 0 else f.flip()

# Gull drawings (original), facing right. Keys: W white (gull4), w white shade (gull3), M mantle
# (gull2), m mantle shade (gull1), t wingtip and eye (gull0), b beak and legs.
GULL_ART = {
    'perch': ["""
        ..WW..
        .wWtWb
        ..WW..
        mMwW..
        tmMW..
        .tmw..
        ..b...""", """
        ..WW..
        bWtWw.
        ..WW..
        mMwW..
        tmMW..
        .tmw..
        ..b..."""],
    'fly': ["""
        t.........t
        .m.......m.
        ..M.....M..
        ...MwWwMb..
        ....ww.....""", """
        ...........
        .mMM...MMm.
        t...MwM...t
        ....wWWb...
        ...........""", """
        ...........
        ....wWWb...
        ..MMwwwMM..
        .m.......m.
        t.........t"""],
    'far': ["""
        t...t
        .M.M.
        ..W..""", """
        .....
        .MWM.
        t...t"""],
}

def gull(seed=0, pose='perch', frame=0, facing=1, slots=None):
    """a gull (10 Stardew's birds and 04's coast, an original design): 'perch' 6 x 7 side view
    (0 head forward, 1 head turned back), 'fly' 11 x 5 seen from below (0 wings up, 1 glide with
    the 1 px elbow bend, 2 wings down; flap [0, 1, 2, 1]), 'far' 5 x 3 for the distant sky (0 up,
    1 down). facing 1 = right (the beak side). Slots: the 'gull' ramp, steps 0-4 (0 wingtips and
    eye, 1-2 the grey mantle, 3-4 the white body) and 'beak'; slots={'gull': 'tern'} renames
    the ramp. No outline: the navy tips and the grey mantle carry the silhouette."""
    if pose not in GULL_ART:
        raise ValueError("pose: 'perch', 'fly' or 'far'")
    S = dict(slots or {})
    r = lambda k: S.get('gull', 'gull') + str(k)
    key = {'t': r(0), 'm': r(1), 'M': r(2), 'w': r(3), 'W': r(4), 'b': S.get('beak', 'beak')}
    arts = GULL_ART[pose]
    rows = _rows(arts[frame % len(arts)])
    W, H = len(rows[0]), max(len(_rows(a)) for a in arts)
    P = _P(W, H)
    P.stamp('\n'.join(rows), key, 0, H - len(rows))
    f = Figure(P.g, 2 if pose == 'perch' else W // 2, H - 1)
    return f if facing > 0 else f.flip()

# ---------------------------------------------------------------- lofi small figures
# Inner art 5 wide (the own-material outline makes it 7), 12 px tall with the outline: head rows
# 0-3, torso 4-6, legs 7-9. Keys as CHIBI_KEY (hair K/H/h, skin S/s, eye E, shirt T/t, pants
# P/p, boots B/o, hat A/a).
LOFI_HEAD = {
    ('side', 'short'): """
        .HHH.
        HHHHH
        hHSES
        .hSSS""",
    ('side', 'long'): """
        .HHH.
        HHHHH
        HHSES
        hhSSS""",
    ('side', 'cap'): """
        .AAA.
        aaaaa
        hHSES
        .hSSS""",
    ('down', 'short'): """
        .HHH.
        HHHHH
        hSSSh
        .ESE.""",
    ('down', 'long'): """
        .HHH.
        HHHHH
        HSSSH
        hESEh""",
    ('down', 'cap'): """
        .AAA.
        aaaaa
        hSSSh
        .ESE.""",
}
LOFI_HAIR = ('short', 'long', 'cap')
LOFI_TORSO = {'side': """
        .TtT.
        .TtT.
        .TsT.""", 'down': """
        tTTTt
        tTTTt
        sTTTs"""}
LOFI_LEGS = {
    ('side', 'stand'): """
        .pPP.
        .pPP.
        .oBBB""",
    ('side', 'stride'): """
        .pPP.
        pP.pP
        o..oB""",
    ('side', 'sit'): """
        .pPPP
        ...pP
        ...oB""",
    ('down', 'stand'): """
        .PPP.
        .P.P.
        .B.B.""",
    ('down', 'sit'): """
        pPPPp
        .P.P.
        .B.B.""",
}

def lofi(h=12, seed=0, facing='side', hair=None, pose='idle', frame=0, slots=None, outline='part', ol='ol_char'):
    """a small lofi figure for a 320 x 180 diorama (lantern-isle, this repo; an original design):
    10-14 px tall with the outline (h), 7 px wide, a 4-row head, lined in each material's own
    darkest step (hair0, skin0, shirt0 ...). facing 'side' (profile to the right; .flip() for
    left) or 'down' (front). hair: one of LOFI_HAIR (default by seed; 'cap' is a brimmed cap).
    pose 'idle' (0 rest, 1 breath: head and torso a pixel down), 'walk' (0 stride, 1 pass with the
    body a pixel up, 2 the other stride, 3 pass; the hand swings), 'sit' (0 rest, 1 breath; legs
    forward: the anchor is the hips' lowest row, stamp it just above the seat). Ramps
    hair/skin/shirt/pants/boot/hat steps 0-3 (PALETTES['chibi'] works) plus eye; slots renames
    them. outline 'part', 'slot' (one `ol`) or None. Every pose and frame of one h share a box."""
    if facing not in ('side', 'down'):
        raise ValueError("facing: 'side' or 'down'")
    if not 10 <= int(h) <= 14:
        raise ValueError('lofi figures are 10-14 px tall')
    hair = hair or _pick(LOFI_HAIR, seed, 91)
    head = _rows(LOFI_HEAD[(facing, hair)])
    torso = _rows(LOFI_TORSO[facing])
    f4 = frame % 4
    if pose == 'sit':
        lk = 'sit'
    elif pose == 'walk' and facing == 'side' and f4 in (0, 2):
        lk = 'stride'
    else:
        lk = 'stand'
    legs = _rows(LOFI_LEGS[(facing, lk)])
    d = int(h) - 12                                     # height: torso and leg rows added or dropped
    if d < 0:
        torso = torso[:1] + torso[2:]
    if d < -1:
        legs = legs[:1] + legs[2:]
    if d > 0:
        legs = legs[:1] + legs
    if d > 1:
        torso = torso[:1] + torso
    Hi = len(head) + len(torso) + len(legs)
    W, H = 7, Hi + 3                                    # outline ring plus a row of headroom for the passes
    P = _P(W, H)
    ox, oy = 1, 2
    legy = oy + len(head) + len(torso)
    P.stamp('\n'.join(legs), CHIBI_KEY, ox, legy)
    if lk == 'stride' and f4 == 2:                      # the other stride: the back leg in front
        for y in range(legy + 1, legy + len(legs)):
            row = P.g[y, ox:ox + 5].copy()
            P.g[y, ox:ox + 5] = [{'pants2': 'pants1', 'pants1': 'pants2'}.get(v, v) for v in row]
    P.stamp('\n'.join(torso), CHIBI_KEY, ox, oy + len(head))
    P.stamp('\n'.join(head), CHIBI_KEY, ox, oy)
    hand = legy - 1
    if pose == 'walk' and f4 in (0, 2):
        if facing == 'side':                            # the hand swings a column fore or aft
            sx = 1 if f4 == 0 else -1
            P.put(ox + 2, hand, 'shirt1')
            P.put(ox + 2 + sx, hand, 'skin1')
        else:                                           # front: a foot lifts, its hand drops
            lx = ox + (1 if f4 == 0 else 3)
            P.put(lx, legy + len(legs) - 1, None)
            P.put(lx, legy + len(legs) - 2, 'boot2')
    if pose == 'walk' and f4 in (1, 3):                 # pass: the body rises, the hips stretch
        P.shift((0, legy), 0, -1)
        P.g[legy - 1] = np.where(np.equal(P.g[legy - 1], None), P.g[legy], P.g[legy - 1])
    if pose in ('idle', 'sit') and frame % 2 == 1:      # breath: head and torso settle a pixel
        P.shift((0, legy), 0, 1)
    if outline:
        _outline(P.g, outline, ol=ol)
    f = Figure(P.g, ox + 2, legy if pose == 'sit' else legy + len(legs) - 1)
    return f.recolor(slots) if slots else f

# ---------------------------------------------------------------- demo palettes
PALETTES = {
    'thin': {'shirt1': '#7d7468', 'shirt2': '#aea395', 'shirt3': '#dfd9d4', 'vest1': '#1c1716', 'vest2': '#2b2422',
             'vest3': '#3d3431', 'pants1': '#2e2d2c', 'pants2': '#4f4e4c', 'pants3': '#6a6866',
             'skin1': '#8c5a3e', 'skin2': '#c98f62', 'skin3': '#eab98a', 'hair1': '#141011', 'hair2': '#2e2622',
             'hair3': '#4a3c34', 'shoe1': '#9a958e', 'shoe2': '#d8d4cc', 'shoe3': '#f4f2ec',
             'rim0': '#fee187', 'rim1': '#fef9c4',
             'hat1': '#2a201c', 'hat2': '#4a3a30', 'hat3': '#6e5a48', 'sheath1': '#1a1214', 'sheath2': '#3a2428',
             'sheath3': '#5e3a3e', 'blade1': '#6a6e78', 'blade2': '#c4c8d0', 'blade3': '#f0f2f4', 'grip': '#4a4450'},
    'iso_person': {
        'ol': '#000000',
        'hgreen1': '#009a00', 'hgreen2': '#00d400', 'hgreen3': '#00ff00',
        'hred1': '#9a0000', 'hred2': '#e00000', 'hred3': '#ff4a3a',
        'hblond1': '#a8a000', 'hblond2': '#d8d800', 'hblond3': '#e2ff00',
        'hblack1': '#000000', 'hblack2': '#1c1c1c', 'hblack3': '#3a3a3a',
        'hbrown1': '#4a2200', 'hbrown2': '#7a3a08', 'hbrown3': '#a8601c',
        'skinA0': '#5a5230', 'skinA1': '#82774d', 'skinA2': '#b9b36e', 'skinA3': '#e7d498',
        'skinB0': '#5a3420', 'skinB1': '#8a5a3a', 'skinB2': '#c08860', 'skinB3': '#e8b88a',
        'skinC0': '#2a1a0a', 'skinC1': '#4a3218', 'skinC2': '#6e4e2a', 'skinC3': '#94703e',
        'skinD0': '#7a4a3a', 'skinD1': '#a8705a', 'skinD2': '#e8b896', 'skinD3': '#ffe0c4',
        'red1': '#a00000', 'red2': '#e00000', 'red3': '#ff5e5f',
        'yellow1': '#a8a800', 'yellow2': '#e2e200', 'yellow3': '#ffff5a',
        'pink1': '#c0006a', 'pink2': '#ff2e9a', 'pink3': '#ff8ac8',
        'white1': '#a8a8a8', 'white2': '#e6e6e6', 'white3': '#ffffff',
        'teal1': '#005a7a', 'teal2': '#0095c8', 'teal3': '#3ac8ff',
        'green1': '#006a1c', 'green2': '#00a82e', 'green3': '#3ae05a',
        'blue1': '#1a2a9a', 'blue2': '#2e4ae0', 'blue3': '#6a8aff',
        'jeans1': '#004a62', 'jeans2': '#006684', 'jeans3': '#0095c8',
        'khaki1': '#7a6a3a', 'khaki2': '#b0985a', 'khaki3': '#d8c080',
        'black1': '#101010', 'black2': '#2a2a2a', 'black3': '#4a4a4a',
        'brown1': '#4a2200', 'brown2': '#7a3a12', 'brown3': '#a85a22',
        'orange1': '#a84a00', 'orange2': '#e07a1c', 'orange3': '#ffa84a'},
    'chibi': {'hair0': '#1b0f12', 'hair1': '#5c2e1c', 'hair2': '#94532a', 'hair3': '#d49a4c',
              'skin0': '#4a1c1c', 'skin1': '#b8674a', 'skin2': '#eaa77a', 'skin3': '#ffd6b0',
              'shirt0': '#123020', 'shirt1': '#2f6b4a', 'shirt2': '#4f9e6a', 'shirt3': '#8fd096',
              'pants0': '#141226', 'pants1': '#2c2c52', 'pants2': '#454a7c', 'pants3': '#6a74a8',
              'boot0': '#1d0d0a', 'boot1': '#4a2a1a', 'boot2': '#7a4a2a', 'boot3': '#a8703e',
              'hat0': '#2a0f0c', 'hat1': '#6c290c', 'hat2': '#a4521c', 'hat3': '#d8843a',
              'eye': '#1a1830', 'glint': '#f4f0e0', 'belt': '#c6a844', 'ol_char': '#020815'},
    'slim': {'fig0': '#141518', 'fig1': '#262830', 'fig2': '#3d4352', 'fig3': '#6b7891',
             'lamp1': '#c9723e', 'lamp2': '#ffd27a'},
    'slime': dict(zip(['slime0', 'slime1', 'slime2', 'slime3', 'slime4'],
                      ['#2a6550', '#44997b', '#5fd0a8', '#6dedc0', '#dcf5ea'])),   # palette.ramp('#5fd0a8', style='toy')
    'cat': {'cat0': '#2a1410', 'cat1': '#8a3e1c', 'cat2': '#c8682a', 'cat3': '#eaa04e', 'cateye': '#a8d84a',
            'ol_char': '#020815'},
    'gull': {'gull0': '#1c2340', 'gull1': '#6c7a94', 'gull2': '#9aa8c0', 'gull3': '#d4dae4', 'gull4': '#fbfcfa',
             'beak': '#e0a838'},
    'quadruped_slim': {'deer0': '#17140f', 'deer1': '#4a3a2a', 'deer2': '#6e5638', 'deer3': '#9a7f55'},
    'block': {'hat': '#a8743f', 'hat_shade': '#6e4a2c', 'head': '#24323d', 'visor': '#bff2e2',
              'collar': '#e8574a', 'mantle': '#ecd9a8', 'cloak': '#2f8a8c', 'emblem': '#e8574a', 'satchel': '#a8743f',
              'leg': '#24323d', 'foot': '#c9d6c4'},
}
PALETTES['lofi'] = dict(PALETTES['chibi'])
