"""万剑诀 · Ten Thousand Swords: an original turn-based battle in the style of 90s Chinese wuxia
RPGs. 320x200 (VGA).

An azure dragon coils round a spirit vortex. On a ledge, the swordsman raises two fingers: a ring of
flying swords turns above him, then they go, one after another, and strike; numbers fly, the dragon
reels, and the ring forms again. Party status and a taiji command wheel along the bottom.

Made with the kit: the dragon is a chain of curved solids along a spline (tools/sdf.py RoundCones,
Plates for the fins), its head built from spheres and cones with antlers; the swordsman is the same
kind of figure as in the sword tomb; side camera with outlines. The vortex is a rotating
three-armed spiral in palette steps. 96 frames at 12 fps, a seamless loop.
"""
import math, sys
import numpy as np
from PIL import Image
from wuxia import palette, th, Canvas, to_image, NAME_RGB, TEXT_RGB, EDGE_RGB
import iso
from iso import Iso, hash2
from sdf import Sphere, RoundCone, Plate, Union, Smooth, Inter, Above
import cjkfont, pixfont

iso.RAMP_STEPS = 7
W, H = 320, 200
T, FPS = 96, 12
OY = 200                                           # side camera: screen y = OY - z
VC = (126, 84)                                     # the eye of the vortex

PAL = palette({
    'vor':   ['#07051a', '#0f0a2a', '#1a1040', '#291856', '#3c246e', '#55368a', '#7650a6'],
    'core':  ['#3a2440', '#6a3a4a', '#a45a46', '#d68a4a', '#f2bc62', '#fde49a', '#fff8dc'],
    'scale': ['#071c1c', '#0c2e2c', '#134440', '#1c5c52', '#287866', '#3a967a', '#5cb894'],
    'belly': ['#2e2210', '#4c381a', '#6e5226', '#947034', '#b89048', '#d6b064', '#eed294'],
    'fin':   ['#2e0a0e', '#521216', '#7c1a18', '#a8281c', '#d04422', '#ec6e32', '#f89c58'],
    'horn':  ['#261a0e', '#3e2c16', '#5c4220', '#7c5c2c', '#a07c3e', '#c49e58', '#e2c47e'],
    'pearl': ['#28304c', '#4a5a7c', '#7690b0', '#a6c2dc', '#cfe4f2', '#ecf8ff', '#ffffff'],
    'blade': ['#283146', '#3c4a64', '#566a88', '#7890ae', '#9db6d0', '#c6dcec', '#eaf6ff'],
    'qi':    ['#0c2a3a', '#124660', '#1a6a88', '#2c94b0', '#56bcd2', '#96e0ea', '#dcfcff'],
    'rock':  ['#0a0a12', '#12121c', '#1c1a28', '#282436', '#363046', '#463e58', '#5a5070'],
    'cloth': ['#2c3442', '#424c5e', '#5c687c', '#7a879a', '#9aa6b6', '#bcc6d2', '#dce4ec'],
    'skin':  ['#2a1a1a', '#4a2c28', '#6e4236', '#94604a', '#b88062', '#d0a07e', '#e4bc9a'],
    'hair':  ['#05050a', '#0a0a12', '#10101a', '#171724', '#20202e', '#2a2a3a', '#36364a'],
    'ribbon': ['#3a0c14', '#5a1420', '#7a1c28', '#9a2832', '#b8383e', '#d0524e', '#e2766a'],
    'ui':    ['#06060c', '#0e0e1a', '#181828', '#24243a', '#34344e', '#4a4a68', '#666686'],
    'gold':  ['#2a1e0e', '#4a3414', '#6e4e1c', '#967028', '#bc9438', '#dcb858', '#f2dc8c'],
    'hp':    ['#3a0a10', '#7a1420', '#c02a30', '#e8564a'],
    'mp':    ['#0a1a3a', '#14306a', '#2856a8', '#4a86d8'],
}, {'ol': '#03030a', 'eye': '#ffde5a', 'eye2': '#ff7a2a', 'white': '#fffbe8', 'tongue': '#c83a4a', 'maw': '#3a0a14'})

# ---------------------------------------------------------------- the vortex
def vortex(c, t):
    for y in range(H):
        for x in range(W):
            dx, dy = x - VC[0], (y - VC[1]) * 1.25
            r = math.hypot(dx, dy) + 1e-6
            a = math.atan2(dy, dx)
            ph = a / (2 * math.pi) * 3 + 1.15 * math.log(r / 6) - 2.0 * t / T     # three arms, turning
            s = (0.5 + 0.5 * math.sin(2 * math.pi * ph)) ** 1.6
            fall = max(0.0, 1 - r / 240)
            core = math.exp(-r / 16)
            gold = core * 1.2 + s * math.exp(-r / 42) * 0.9                  # gold rides the arms near the eye
            if gold + (th(x, y) - 0.5) * 0.25 > 0.62:
                c.ramp(x, y, 'core', 1.2 + 4.6 * min(1.0, gold - 0.3), 0, 6)
            else:
                c.ramp(x, y, 'vor', 0.3 + 4.6 * s * fall ** 1.2 + 2.6 * math.exp(-r / 40) + 0.5 * (1 - y / H), 0, 6)

# ---------------------------------------------------------------- the dragon
SPINE = [(226, 98), (212, 82), (196, 64), (176, 48), (152, 36), (126, 31), (100, 33), (76, 42), (56, 57),
         (42, 77), (38, 99), (45, 119), (60, 134), (83, 143), (109, 147), (135, 145), (157, 139), (173, 129)]

def catmull(P, u):
    n = len(P) - 1
    i = min(int(u * n), n - 1); f = u * n - i
    p0, p1, p2, p3 = P[max(0, i - 1)], P[i], P[i + 1], P[min(n, i + 2)]
    return tuple(0.5 * ((2 * b) + (-a + c_) * f + (2 * a - 5 * b + 4 * c_ - d) * f * f + (-a + 3 * b - 3 * c_ + d) * f ** 3)
                 for a, b, c_, d in zip(p0, p1, p2, p3))

def body_radius(u):
    """thickness along the body, u = 0 at the head, 1 at the tail"""
    if u < 0.1:
        return 7.5 + 4.0 * u / 0.1
    if u < 0.55:
        return 11.5 + 0.8 * math.sin((u - 0.1) / 0.45 * math.pi)
    return 11.5 - 8.5 * ((u - 0.55) / 0.45) ** 1.15

def dragon_pose(t, recoil=0.0):
    """spine points in world (x, depth, z): an undulation travels down the body; recoil pushes the head back"""
    pts = []
    for k in range(60):
        u = k / 59
        x, y = catmull(SPINE, u)
        wav = math.sin(2 * math.pi * (u * 1.6 - t / 48)) * 2.2 * min(1.0, u * 6)
        nx, ny = catmull(SPINE, min(1, u + 0.01)); px, py = catmull(SPINE, max(0, u - 0.01))
        tx, ty = nx - px, ny - py; L = math.hypot(tx, ty) or 1
        x += -ty / L * wav; y += tx / L * wav
        back = recoil * max(0.0, 1 - u * 4)
        x += 7 * back; y -= 3 * back
        pts.append((x, 4 * math.sin(u * 5.5), OY - y))
    return pts

VCW = (VC[0], OY - VC[1])                          # the vortex eye in world x, z

def scale_mat(m_=None):
    def m(p, n, step, t):
        x, y, z = p
        vx, vz = VCW[0] - x, VCW[1] - z; L = math.hypot(vx, vz) or 1
        if (n[0] * vx + n[2] * vz) / L > 0.42:                           # belly scutes on the side toward the vortex
            return 'belly%d' % max(0, min(6, step + 1 + (0 if int((x * vz - z * vx) / L) % 3 else -1)))
        row = int(math.floor((x * 0.6 + z) / 3.4))                         # scales: staggered crescents
        if (x * 0.6 + z) - row * 3.4 < 1.1 and int(x + (2 if row % 2 else 0)) % 4 < 2 and step >= 2:
            return 'scale%d' % (step - 1)
        return 'scale%d' % step
    return m

def dragon(s, t, recoil=0.0):
    pts = dragon_pose(t, recoil)
    mat = scale_mat()
    parts = []
    for k in range(len(pts) - 1):
        parts.append(RoundCone(pts[k], pts[k + 1], body_radius(k / 59), body_radius((k + 1) / 59), mat=mat))
    # legs reach out from the belly side (toward the vortex); the near front leg holds the pearl out
    legs_near, legs_far = [], []
    pearl = None
    for u, along, side in ((0.12, 6, 1), (0.17, -2, -1), (0.6, -3, 1), (0.66, 5, -1)):
        k = int(u * 59); bx, by, bz = pts[k]
        nx_, ny_, nz_ = pts[k + 1]
        tx, tz = nx_ - bx, nz_ - bz; L = math.hypot(tx, tz) or 1; tx, tz = tx / L, tz / L
        ix, iz = VCW[0] - bx, VCW[1] - bz; Li = math.hypot(ix, iz) or 1; ix, iz = ix / Li, iz / Li
        r = body_radius(u)
        yb = by + side * 8
        base = (bx + ix * r * 0.3, yb, bz + iz * r * 0.3)
        knee = (bx + ix * (r + 7) + tx * along * 0.4, yb, bz + iz * (r + 7) + tz * along * 0.4)
        foot = (bx + ix * (r + 13) + tx * along, yb, bz + iz * (r + 13) + tz * along)
        if u == 0.12:                                                  # this one reaches out toward the hero
            foot = (bx + ix * (r + 9) + 14, yb, bz + iz * (r + 9) - 4)
        L_ = [RoundCone(base, knee, 5.2, 3.8, mat=mat), RoundCone(knee, foot, 3.8, 2.8, mat=mat)]
        fx_, fz_ = foot[0] - knee[0], foot[2] - knee[2]; Lf = math.hypot(fx_, fz_) or 1
        for j in range(4):                                             # four talons fanned round the foot's direction
            a = math.atan2(fz_, fx_) + (-1.1 + j * 0.73)
            tip = (foot[0] + 5 * math.cos(a), yb + side * 0.5, foot[2] + 5 * math.sin(a))
            L_.append(RoundCone(foot, tip, 1.5, 0.45, mat='horn'))
        (legs_near if side > 0 else legs_far).extend(L_)
        if u == 0.12:
            pearl = (foot[0] + 4.5, yb + 3, foot[2] + 4)
    # the head, turned toward the hero below right
    hx, hy, hz = pts[0]
    fx, fz = 0.84, -0.54
    ux, uz = -fz, fx
    def at(a, b, d=0.0):
        return (hx + a * fx + b * ux, hy + d, hz + a * fz + b * uz)
    head = [Sphere(*at(2, 2), 10.0, mat=mat), RoundCone(at(3, 2.5), at(24, 1.0), 8.2, 5.4, mat=mat),
            Sphere(*at(25, 2.2), 5.4, mat=mat)]
    jaw = 0.5 + 0.12 * math.sin(2 * math.pi * t / 24) + 0.25 * recoil
    jx, jz = fx * math.cos(jaw) - ux * math.sin(jaw), fz * math.cos(jaw) - uz * math.sin(jaw)
    h0 = at(3, -4.5)
    head.append(RoundCone(h0, (h0[0] + 21 * jx, hy, h0[2] + 21 * jz), 5.8, 3.0, mat=mat))
    crisp = [RoundCone(at(-1, 9, 3), at(14, 6.6, 3), 4.2, 2.6, mat=mat)]          # the brow ridge
    for d, sc in ((-4, 0.9), (4, 1.0)):                                 # antlers: up and back, forked
        a0 = at(-1, 9, d); a1 = at(-6 * sc, 21 * sc, d); a2 = at(-15 * sc, 31 * sc, d)
        crisp += [RoundCone(a0, a1, 2.6, 1.9, mat='horn'), RoundCone(a1, a2, 1.9, 0.7, mat='horn'),
                  RoundCone(a1, at(3 * sc, 29 * sc, d), 1.5, 0.6, mat='horn'),
                  RoundCone(at(-10 * sc, 26 * sc, d), at(-20 * sc, 27 * sc, d), 1.2, 0.5, mat='horn')]
    mane = []                                                          # flame-red locks streaming along the neck
    for i in range(8):
        k0 = 1 + i
        w = math.sin(2 * math.pi * (t / 24 - i * 0.12))
        bx, by, bz = pts[k0]
        nx_, ny_, nz_ = pts[k0 + 5]
        ox, oz = -(nz_ - bz), (nx_ - bx); Lo = math.hypot(ox, oz) or 1; ox, oz = ox / Lo, oz / Lo
        if ox * (bx - VCW[0]) + oz * (bz - VCW[1]) < 0:
            ox, oz = -ox, -oz
        r = body_radius(k0 / 59)
        r0 = (bx + ox * r * 0.7, by - 3, bz + oz * r * 0.7)
        r1 = (nx_ + ox * (r + 4 + w * 2), by - 3, nz_ + oz * (r + 4 + w * 2))
        r2 = (pts[k0 + 9][0] + ox * (r + 7 + w * 4), by - 3, pts[k0 + 9][2] + oz * (r + 7 + w * 4))
        mane += [RoundCone(r0, r1, 3.0, 2.2, mat='fin'), RoundCone(r1, r2, 2.2, 0.5, mat='fin')]
    def fin_mat(p_, n_, st, tt):
        return 'fin%d' % max(0, min(6, st + 1))
    fins = []                                                          # the dorsal fin, on the outside of the coil
    for k in range(10, 57, 2):
        x, y, z = pts[k]
        nx, ny, nz = pts[k + 1]
        tx, tz = nx - x, nz - z; L = math.hypot(tx, tz) or 1
        ox, oz = -tz / L, tx / L
        if ox * (x - VCW[0]) + oz * (z - VCW[1]) < 0:
            ox, oz = -ox, -oz
        r = body_radius(k / 59)
        hgt = 5.5 + 3.0 * (0.5 + 0.5 * math.sin(k * 1.9))
        base = (x + ox * r * 0.6, y - 2, z + oz * r * 0.6)
        tip = (x + ox * (r + hgt) - tx / L * 4.5, y - 2, z + oz * (r + hgt) - tz / L * 4.5)
        fins.append(RoundCone(base, tip, 2.6, 0.3, mat=fin_mat))
    tail = pts[-1]
    for i in range(5):                                                 # a flame tuft at the tail's end
        a = -0.9 + i * 0.45 + 0.2 * math.sin(2 * math.pi * t / 24 + i)
        fins.append(RoundCone(tail, (tail[0] + 9 * math.cos(a), tail[1], tail[2] + 9 * math.sin(a)), 2.0, 0.4, mat='fin'))
    s.solid(Union(*legs_far))
    s.solid(Union(*mane))
    s.solid(Union(Smooth(2.4, *(parts + head)), *crisp, *fins))
    s.solid(Union(*legs_near))
    s.solid(Sphere(*pearl, 4.6, mat='pearl'), light=(-0.3, 0.5, 0.8))
    return dict(at=at, head=(hx, hz), jaw=jaw, h0=h0, j=(jx, jz), pts=pts, pearl=pearl)

def head_details(c, info, t, mask):
    at = info['at']
    def scr(p):
        return p[0], OY - p[2]
    ex, ey = scr(at(10.5, 4.6)); ex, ey = int(ex), int(ey)
    for dx, v in ((-1, 'eye2'), (0, 'eye'), (1, 'eye')):
        c.put(ex + dx, ey, v)
    c.put(ex + 1, ey - 1, 'ol'); c.put(ex, ey - 1, 'ol'); c.put(ex - 1, ey - 1, 'ol'); c.put(ex - 2, ey - 2, 'ol')
    nx_, ny_ = scr(at(27, 4.6)); c.put(nx_, ny_, 'ol'); c.put(nx_ + 1, ny_, 'ol')
    # whiskers: two long barbels from the nose, trailing back and waving
    for side, ph in ((1, 0.0), (-1, 0.5)):
        x0, y0 = scr(at(27, 1.5 + 1.2 * side))
        for k in range(48):
            u = k / 47
            x = x0 + u * 10 - u * u * 38 + 2.5 * math.sin(2 * math.pi * (t / 16 + ph) + u * 6) * u
            y = y0 + u * (10 + 6 * side) + 4 * math.sin(2 * math.pi * (t / 24 + ph) + u * 4) * u
            c.put(x, y, 'horn5' if k < 30 else 'horn3')
    # beard under the jaw
    px, pz = info['pearl'][0], info['pearl'][2]                           # the pearl's glow and glint
    cx, cy = px, OY - pz
    for yy in range(int(cy - 11), int(cy + 12)):
        for xx in range(int(cx - 11), int(cx + 12)):
            d = math.hypot(xx - cx, yy - cy)
            v = c.get(xx, yy)
            if 5 < d < 11 and v is not None and str(v).startswith(('vor', 'core')) and (1 - (d - 5) / 6) * 0.8 > th(xx, yy):
                c.put(xx, yy, 'qi%d' % (5 if d < 7 else 3))
    k = (t // 3) % 8
    if k < 3:
        for d in range(1, 2 + k):
            for ox, oy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                c.put(cx - 1 + ox, cy - 2 + oy, 'white')

# ---------------------------------------------------------------- frame
def frame(t):
    c = Canvas(W, H)
    vortex(c, t)
    s = Iso(W, H, origin=(0, OY), slots=PAL.keys(), camera='side')
    info = dragon(s, t)
    g = np.array(s.render(outline=True, between=True, rim=True).a, object)
    m = g != None
    c.g[m] = g[m]
    head_details(c, info, t, m)
    return to_image(c.g, PAL)

def render_frames(n=T):
    return [frame(t) for t in range(n)]

def export():
    return [{'name': 'dragon_battle', 'frames': [], 'images': [f.convert('RGBA') for f in render_frames()],
             'anchor': (0, 0), 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    import time
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/battle'
    for t in [int(a) for a in (sys.argv[2:] or ['0'])]:
        t0 = time.time()
        frame(t).resize((W * 3, H * 3), Image.NEAREST).save('%s-%03d.png' % (out, t))
        print(t, round(time.time() - t0, 2), 's')
