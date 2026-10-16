"""Isometric and 3/4 pixel art: build a scene from boxes, roofs, pyramids, cylinders and
sprites, get clean pixel art back in a projection pixel art actually uses (CAMERAS: 2:1 iso,
military, 3/4 top-down, oblique, side), with cast shadows if you want them.

    from iso import Iso
    s = Iso(400, 300, origin=(200, 60))
    s.box(0, 0, 0, 32, 32, 6, 'grass')                  # x, y, z, w, d, h, material
    s.box(4, 4, 6, 8, 8, 20, 'brick', top='roof')        # faces can differ
    s.box(16, 4, 6, 10, 8, 14, 'cream', left=windows('cream', 'glass'))
    g = s.render()                                       # artlib.Grid of palette slots

Projection (2:1 "pixel isometric"): +1 x is 2 px right and 1 down, +1 y is 2 px left and
1 down, +1 z is 1 px up. A 16 x 16 unit floor is the classic 32 x 16 px diamond. Edges come out
as perfect 2-1 stairs because every pixel is resolved by inverse projection at its centre, with
a depth buffer, so any arrangement of shapes occludes correctly; no sorting needed.

Units, so a brief can size things: positions and sizes are world units, never screen px. At
scale=1 a unit floor square covers 4 px^2 of screen (compose.populate's densities use this), a
box h units tall stands h px, so a figure H px tall is H units of z, and a run of n units along
x or y spans 2n px across and n px down. Iso(scale=k) multiplies all of it by k (k px per unit
of z). to_screen(x, y, z) gives the screen point of any world point: project the corners of
anything the boxes cannot draw (a bridge turned to an angle) and fill the polygon yourself.

Materials are palette-ramp names: 'brick' means slots brick0 (darkest) .. brick4 (lightest).
By default the top face uses step 3, the left (lit) face step 2 and the right (shade) face
step 1; light comes from the upper left. A face can instead be a slot ('#hex' works too) or a
function f(u, v, t) -> slot, with u, v the face-local unit coordinates and t the frame, for
windows, tiles, water and anything animated.

Finishing passes (render(outline=True, rim=True)):
  - a dark outline ('ol' slot) where a shape meets the background,
  - a one-step-darker line where a shape stands in front of another (selective outline),
  - a one-step-lighter rim along the lit front edges of top faces.
These three are what make iso art read as drawn rather than rendered. render(silhouette=True)
draws the between line in 'ol' too: the sticker-iso black silhouette for a full-bleed scene.
Sprites stand upright (sprite(upright=True)): each row takes the depth of the point that far
above its feet, so a tall figure is not cut by a box behind it.
"""
import math, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import artlib

BAYER4 = np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4)

RAMP_STEPS = 5      # ramps are NAME0..NAME4 (pixelate palette ramps --steps 5)

def shade(slot, step):
    """'brick3', -1 -> 'brick2' (clamped to the ramp); other slots unchanged"""
    if isinstance(slot, str) and slot[-1:].isdigit() and not slot.startswith('#'):
        base, n = slot.rstrip('0123456789'), int(slot[len(slot.rstrip('0123456789')):])
        return '%s%d' % (base, max(0, min(RAMP_STEPS - 1, n + step)))
    return slot

def hash2(x, y, s=0):
    h = (int(x) * 374761393 + int(y) * 668265263 + s * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

# ---------------------------------------------------------------- face patterns
def windows(wall, glass='glass', lit=None, every=(2, 4), size=(1, 2), margin=(1, 2), lit_share=0.35, seed=0, step=None):
    """window grid on a wall. every=(units across, px up) per window cell, size=window (units, px).
    lit: slot for windows that are lit at night (same colour as glass in a day palette).
    The returned function takes the face's own lit/shade step through `step` (set by the face)."""
    def f(u, v, t, face_step=2, W=None, H=None):
        cu, cv = int(u) % every[0], int(v) % every[1]
        inside = cu < size[0] and margin[1] <= cv < margin[1] + size[1]
        if W is not None:
            inside = inside and margin[0] <= u < W - margin[0] and v < H - 1
        if inside:
            if lit and hash2(int(u) // every[0] + seed * 31, int(v) // every[1], seed) < lit_share:
                return lit
            return glass
        return '%s%d' % (wall, face_step if step is None else step)
    return f

def stripes(a, b, period=4, axis=1):
    def f(u, v, t, face_step=2, W=None, H=None):
        return a if (int(v if axis else u) % period) else b
    return f

# ---------------------------------------------------------------- cameras
# Orthographic projections whose edges land on clean pixel steps (the ones pixel art uses).
# Each maps world (x, y, z) to screen: sx = A[0] . p, sy = A[1] . p (+ origin). z is up, +y is
# toward the viewer in the front-facing views.
CAMERAS = {
    'iso':      ((2, -2, 0), (1, 1, -1)),     # 2:1 dimetric, the pixel-art "isometric": 2-px steps
    'military': ((1, -1, 0), (1, 1, -1)),     # 45 degree plan view, 1:1 steps, steep and graphic
    'topdown':  ((1, 0, 0), (0, 1, -1)),      # 3/4 top-down RPG view: tops and front faces, all lines straight
    'oblique':  ((1, -1, 0), (0, 0.5, -1)),   # true front face, depth receding up-left at 2:1, half length
    'side':     ((1, 0, 0), (0, 0, -1)),      # flat side view: front faces only (platformers)
}

class Iso:
    def __init__(self, w, h, origin=(0, 0), slots=None, camera='iso', depth=1.0, height=1.0, scale=1):
        """camera: one of CAMERAS or a 2x3 matrix. For 'topdown' and 'oblique', depth and height
        scale the ground's y axis and the vertical (e.g. depth=0.75 looks down less steeply).
        slots: the palette's slot names, so shading never steps outside a ramp."""
        self.W, self.H = w, h
        self.slots = set(slots) if slots else None
        self.ox, self.oy = origin
        A = np.array(CAMERAS[camera] if isinstance(camera, str) else camera, float)
        if camera in ('topdown', 'oblique'):
            A[1, 1] *= depth; A[1, 2] *= height
        self.A = A * scale                          # e.g. scale=2: 2 px per unit in the 1 px cameras
        n = np.cross(A[0], A[1])                    # the direction toward the viewer
        if n[2] < 0 or (n[2] == 0 and n[1] < 0):
            n = -n
        self.view = n / np.linalg.norm(n)
        self.camera = camera
        self.slot = np.full((h, w), None, object)
        self.depth = np.full((h, w), -1e9)
        self.obj = np.full((h, w), -1, int)
        self.face = np.zeros((h, w), np.int8)       # 1 top, 2 y-face ("left"), 3 x-face ("right"), 4 sprite
        self.norm = np.zeros((h, w, 3), np.int8)
        self.world = np.zeros((h, w, 3), np.float32)
        self.shadow = np.zeros((h, w), bool)
        self.boxes = []                             # occluders for cast shadows
        self.solids = []
        self.dither_curves = False
        self.nobj = 0
        self.t = 0
        self.nolines = set()                        # objects that get no outline / rim

    def to_screen(self, x, y, z):
        p = np.array([x, y, z], float)
        return self.ox + float(self.A[0] @ p), self.oy + float(self.A[1] @ p)

    def _window(self, X, Y, Z, w, d, h):
        corners = [self.to_screen(X + a, Y + b, Z + c) for a in (0, w) for b in (0, d) for c in (0, h)]
        x0 = max(0, int(math.floor(min(c[0] for c in corners))) - 1)
        x1 = min(self.W, int(math.ceil(max(c[0] for c in corners))) + 1)
        y0 = max(0, int(math.floor(min(c[1] for c in corners))) - 1)
        y1 = min(self.H, int(math.ceil(max(c[1] for c in corners))) + 1)
        if x1 <= x0 or y1 <= y0:
            return None
        py, px = np.mgrid[y0:y1, x0:x1]
        return (y0, y1, x0, x1), px + 0.5 - self.ox, py + 0.5 - self.oy

    def _paint(self, win, mask, depth, fill, face, oid, world=None, normal=None):
        y0, y1, x0, x1 = win
        sub_d = self.depth[y0:y1, x0:x1]
        m = mask & (depth > sub_d)
        if not m.any():
            return
        sub_d[m] = depth[m]
        self.obj[y0:y1, x0:x1][m] = oid
        self.face[y0:y1, x0:x1][m] = face
        self.shadow[y0:y1, x0:x1][m] = False
        if world is not None:
            wv = self.world[y0:y1, x0:x1]
            for i in range(3):
                wv[..., i][m] = world[i][m] if np.ndim(world[i]) else world[i]
            self.norm[y0:y1, x0:x1][m] = normal
        sl = self.slot[y0:y1, x0:x1]
        if callable(fill):
            ys, xs = np.nonzero(m)
            for yy, xx in zip(ys, xs):
                sl[yy, xx] = fill(yy, xx)
        else:
            sl[m] = fill

    def _face_fill(self, spec, mat, step, u, v, W, H):
        if spec is None:
            return '%s%d' % (mat, step)
        if callable(spec):
            t = self.t
            def f(yy, xx):
                try:
                    return spec(u[yy, xx], v[yy, xx], t, face_step=step, W=W, H=H)
                except TypeError:
                    return spec(u[yy, xx], v[yy, xx], t)
            return f
        return spec

    def box(self, X, Y, Z, w, d, h, mat='stone', top=None, left=None, right=None, steps=(3, 2, 1), lines=True, cast=True):
        """an axis-aligned box. mat: ramp name. top / left (the y face: iso's left face, the front
        face in topdown, oblique and side) / right (the x face) override a face with a slot or
        f(u, v, t). cast=False: no cast shadow."""
        self.nobj += 1; oid = self.nobj
        if not lines:
            self.nolines.add(oid)
        if cast and h > 0:
            self.boxes.append((X, Y, Z, w, d, h))
        g = self._window(X, Y, Z, w, d, h)
        if g is None:
            return oid
        win, sx, sy = g
        eps = 1e-6
        lo, size = (X, Y, Z), (w, d, h)
        for k in (2, 1, 0):                          # top, y face, x face
            if self.view[k] == 0 or (k != 2 and h <= 0):
                continue
            sgn = 1 if self.view[k] > 0 else -1
            c = lo[k] + (size[k] if sgn > 0 else 0)
            i, j = [a for a in (0, 1, 2) if a != k]
            M = self.A[:, [i, j]]
            det = M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]
            if abs(det) < 1e-9:
                continue
            rx = sx - self.A[0, k] * c; ry = sy - self.A[1, k] * c
            ai = (M[1, 1] * rx - M[0, 1] * ry) / det
            aj = (-M[1, 0] * rx + M[0, 0] * ry) / det
            m = (ai >= lo[i] - eps) & (ai < lo[i] + size[i] - eps) & (aj >= lo[j] - eps) & (aj < lo[j] + size[j] - eps)
            P = [None, None, None]; P[k] = c; P[i] = ai; P[j] = aj
            dep = self.view[0] * (P[0]) + self.view[1] * (P[1]) + self.view[2] * (P[2])
            if np.ndim(dep) == 0:
                dep = np.full(sx.shape, dep)
            normal = [0, 0, 0]; normal[k] = sgn
            if k == 2:
                fill = self._face_fill(top, mat, steps[0], ai - X, aj - Y, w, d); role = 1
            elif k == 1:
                fill = self._face_fill(left, mat, steps[1], ai - X, aj - Z, w, h); role = 2
            else:
                fill = self._face_fill(right, mat, steps[2], ai - Y, aj - Z, d, h); role = 3
            world = [np.full(sx.shape, P[a]) if np.ndim(P[a]) == 0 else P[a] for a in range(3)]
            self._paint(win, m, dep, fill, role, oid, world, normal)
        return oid

    def solid(self, node, lines=True, cast=True, steps=None, eps=0.04, maxit=80, light=(-0.4, 0.45, 0.8)):
        """a curved solid from tools/sdf.py (rounded boxes, vaults, domes, cones, smooth unions,
        cut-outs, terrain), ray-marched per pixel along the camera's view direction. Shading comes
        from the surface normal: flat faces get the box steps (top 3, lit side 2, shade side 1),
        curved ones step through the ramp with an ordered dither."""
        from sdf import owner
        self.nobj += 1; oid = self.nobj
        if not lines:
            self.nolines.add(oid)
        if cast:
            self.solids.append(node)
        x0, y0, z0, x1, y1, z1 = node.bbox
        g = self._window(x0, y0, z0, x1 - x0, y1 - y0, z1 - z0)
        if g is None:
            return oid
        win, sx, sy = g
        n = self.view
        q0 = (np.linalg.pinv(self.A) @ np.stack([sx.ravel(), sy.ravel()])).T          # a point on each pixel's ray
        lo, hi = np.array([x0, y0, z0]) - 0.01, np.array([x1, y1, z1]) + 0.01
        with np.errstate(divide='ignore', invalid='ignore'):
            ta = np.where(n != 0, (lo - q0) / n, -np.inf)
            tb = np.where(n != 0, (hi - q0) / n, np.inf)
        inside_par = np.all(np.where(n == 0, (q0 >= lo) & (q0 <= hi), True), 1)
        tmin = np.max(np.where(n != 0, np.minimum(ta, tb), -np.inf), 1)
        tmax = np.min(np.where(n != 0, np.maximum(ta, tb), np.inf), 1)
        act = inside_par & (tmin <= tmax)
        idx = np.nonzero(act)[0]
        t = tmax[idx].copy(); tl = tmin[idx]
        hit = np.zeros(len(idx), bool)
        live = np.ones(len(idx), bool)
        for _ in range(maxit):
            if not live.any():
                break
            li = np.nonzero(live)[0]
            P = q0[idx[li]] + t[li, None] * n
            d = node.d(P[:, 0], P[:, 1], P[:, 2])
            h = d < eps
            hit[li[h]] = True; live[li[h]] = False
            t[li[~h]] -= np.maximum(d[~h], eps * 0.5)
            out = t < tl
            live &= ~out
        if not hit.any():
            return oid
        hi_ = idx[hit]
        P = q0[hi_] + t[hit, None] * n
        e = 0.03
        X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
        N = np.stack([node.d(X + e, Y, Z) - node.d(X - e, Y, Z), node.d(X, Y + e, Z) - node.d(X, Y - e, Z),
                      node.d(X, Y, Z + e) - node.d(X, Y, Z - e)], 1)
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
        L = np.array(light, float); L /= np.linalg.norm(L)
        b = N @ L
        v = 1 + (b + 0.4) / 1.2 * 2                                 # +x side 1, +y side ~2, top 3
        v = np.where(b > 0.93, 4, v)
        H_, W_ = sx.shape
        py, px = np.divmod(hi_, W_)
        Y0, X0 = win[0], win[2]
        curved = np.abs(N).max(1) < 0.97
        th = (BAYER4[(py + Y0) & 3, (px + X0) & 3] + 0.5) / 16
        # curved surfaces step through the ramp in clean bands (how pixel artists shade a dome or a
        # rounded corner); dither=True blends the band edges with an ordered dither instead
        step = np.where(curved & self.dither_curves, np.floor(v + th), np.round(v)).astype(int)
        step = np.clip(step, 0, RAMP_STEPS - 1)
        own = owner(node, X, Y, Z)
        dep = P @ n
        role = np.where(N[:, 2] >= np.maximum(np.abs(N[:, 0]), np.abs(N[:, 1])), 1, np.where(np.abs(N[:, 1]) >= np.abs(N[:, 0]), 2, 3))
        sub_d = self.depth[win[0]:win[1], win[2]:win[3]]
        for k in range(len(hi_)):
            yy, xx = py[k], px[k]
            if dep[k] <= sub_d[yy, xx]:
                continue
            leaf = own[k]
            mat = leaf.mat
            if callable(mat):
                slot = mat(P[k], N[k], int(step[k]), self.t)
            elif isinstance(mat, str) and (mat.startswith('#') or not mat[-1:].isalpha()):
                slot = mat
            elif isinstance(mat, str) and self.slots is not None and mat in self.slots:
                slot = mat
            else:
                slot = '%s%d' % (mat, step[k])
            sub_d[yy, xx] = dep[k]
            Y_, X_ = yy + Y0, xx + X0
            self.slot[Y_, X_] = slot; self.obj[Y_, X_] = oid; self.face[Y_, X_] = role[k]
            self.shadow[Y_, X_] = False
            self.world[Y_, X_] = P[k]
            self.norm[Y_, X_] = np.sign(np.round(N[k] * 1.4)).astype(np.int8) if role[k] != 1 else (0, 0, 1)
        return oid

    def cast_shadows(self, sun=(-0.6, 0.5, 0.8), reach=220, step=-1):
        """darken (one ramp step) every lit surface that a box blocks from the sun. sun points
        toward the sun; call after the static world is drawn. Moving things drawn later clear it."""
        if not self.boxes and not self.solids:
            return
        L = np.array(sun, float)
        lxy = math.hypot(L[0], L[1]) or 1e-6
        ext = [(X, Y, X + w, Y + d) for X, Y, Z, w, d, h in self.boxes] + [n.bbox[:2] + n.bbox[3:5] for n in self.solids]
        E = np.array(ext, float)
        x0, y0 = int(math.floor(E[:, 0].min())), int(math.floor(E[:, 1].min()))
        x1, y1 = int(math.ceil(E[:, 2].max())), int(math.ceil(E[:, 3].max()))
        hm = np.full((y1 - y0 + 1, x1 - x0 + 1), -1e9, np.float32)
        for X, Y, Z, w, d, h in self.boxes:
            ix0, ix1 = int(math.floor(X - x0 + 0.5)), int(math.floor(X + w - x0 - 0.5))
            iy0, iy1 = int(math.floor(Y - y0 + 0.5)), int(math.floor(Y + d - y0 - 0.5))
            if ix1 >= ix0 and iy1 >= iy0:
                v = hm[iy0:iy1 + 1, ix0:ix1 + 1]
                np.maximum(v, Z + h, out=v)
        for node in self.solids:                    # curved solids: sample their top surface per cell
            bx0, by0, bz0, bx1, by1, bz1 = node.bbox
            cx = np.arange(max(x0, int(np.floor(bx0))), min(x1, int(np.ceil(bx1))) + 1)
            cy = np.arange(max(y0, int(np.floor(by0))), min(y1, int(np.ceil(by1))) + 1)
            if not len(cx) or not len(cy):
                continue
            GX, GY = np.meshgrid(cx + 0.5, cy + 0.5)
            if hasattr(node, 'height'):
                top = node.height(GX, GY)
            else:
                top = np.full(GX.shape, -1e9)
                for zz in np.arange(np.ceil(bz1), np.floor(bz0) - 1, -1.0):
                    inside = node.d(GX, GY, np.full(GX.shape, zz)) < 0
                    top = np.where(inside & (top < -1e8), zz, top)
            v = hm[cy[0] - y0:cy[-1] - y0 + 1, cx[0] - x0:cx[-1] - x0 + 1]
            np.maximum(v, top.astype(np.float32), out=v)
        m = (self.obj >= 0) & (self.face != 4)
        ys, xs = np.nonzero(m)
        P = self.world[ys, xs].astype(float)
        N = self.norm[ys, xs].astype(float)
        facing = (N @ L) > 0
        ys, xs, P = ys[facing], xs[facing], P[facing] + N[facing] * 0.01
        hit = np.zeros(len(ys), bool)
        dx, dy, dz = L[0] / lxy, L[1] / lxy, L[2] / lxy
        for t in range(1, reach):
            qx = np.floor(P[:, 0] + dx * t - x0).astype(int)
            qy = np.floor(P[:, 1] + dy * t - y0).astype(int)
            qz = P[:, 2] + dz * t
            ok = (qx >= 0) & (qx < hm.shape[1]) & (qy >= 0) & (qy < hm.shape[0]) & ~hit
            if not ok.any():
                if (qz > hm.max()).all():
                    break
                continue
            hit[ok] |= hm[qy[ok], qx[ok]] > qz[ok] + 0.5
        self.shadow[ys[hit], xs[hit]] = True
        self.shadow_step = step

    def pyramid(self, X, Y, Z, w, d, h, mat, step_h=3, shrink=1, cap=2, **faces):
        """a stepped pyramid or tower: boxes shrinking by `shrink` units per side every `step_h` px,
        until `cap` units remain. The ledges read as floors."""
        i = 0
        while w - 2 * i * shrink >= cap and d - 2 * i * shrink >= cap and i * step_h < h:
            hh = min(step_h, h - i * step_h)
            self.box(X + i * shrink, Y + i * shrink, Z + i * step_h, w - 2 * i * shrink, d - 2 * i * shrink, hh, mat, **faces)
            i += 1
        return Z + i * step_h

    def gable(self, X, Y, Z, w, d, h, mat, along='x', **faces):
        """a gable (pitched) roof over a w x d footprint, ridge along x or y, made of 1-unit steps"""
        n = int((d if along == 'x' else w) // 2)
        for i in range(n):
            if along == 'x':
                self.box(X, Y + i, Z + i * h // max(1, n), w, d - 2 * i, max(1, h // max(1, n)), mat, **faces)
            else:
                self.box(X + i, Y, Z + i * h // max(1, n), w - 2 * i, d, max(1, h // max(1, n)), mat, **faces)

    def cylinder(self, cx, cy, Z, r, h, mat, **faces):
        """a round tower as unit slices (reads round at pixel scale)"""
        for yy in range(-r, r):
            half = int(math.sqrt(max(0, r * r - (yy + 0.5) ** 2)) + 0.5)
            if half > 0:
                self.box(cx - half, cy + yy, Z, 2 * half, 1, h, mat, **faces)

    def sprite(self, grid, x, y, z, anchor=None, lines=False, upright=True):
        """a hand-drawn sprite (artlib.Grid or rows+key) standing at world point x, y, z.
        anchor: the sprite pixel that sits on that point (default bottom centre).
        upright=True: the sprite is a standing card, so each row's depth is the depth of the
        world point that far above the anchor (a tall figure in front of a box keeps its head
        instead of being cut by the box behind it, and a box in front still hides it).
        upright=False: one depth for the whole sprite, taken at the anchor (a decal lying flat,
        or the older behaviour)."""
        self.nobj += 1; oid = self.nobj
        if not lines:
            self.nolines.add(oid)
        ax, ay = anchor if anchor else (grid.w // 2, grid.h - 1)
        sx, sy = self.to_screen(x, y, z)
        d = float(self.view @ np.array([x, y, z], float)) + 0.3
        zpx = -float(self.A[1, 2])                  # screen px up per unit of z
        rise = self.view[2] / zpx if upright and zpx > 0 else 0.0
        # round the origin once (half up), then step whole pixels: rounding each pixel's own
        # position rounds half to even, so a sprite sitting on .5 skipped or doubled rows and columns
        ox, oy = math.floor(sx - ax + 0.5), math.floor(sy - ay + 0.5)
        for j in range(grid.h):
            dj = d + rise * (ay - j)
            for i in range(grid.w):
                v = grid.a[j][i]
                if v is None: continue
                X, Y = ox + i, oy + j
                if 0 <= X < self.W and 0 <= Y < self.H and dj >= self.depth[Y, X]:
                    self.depth[Y, X] = dj; self.slot[Y, X] = v; self.obj[Y, X] = oid; self.face[Y, X] = 4
                    self.shadow[Y, X] = False
        return oid

    def line(self, a, b, slot, sag=0, bias=0.3):
        """a 1 px line between world points a = (x, y, z) and b (a wire, a rail, a rope, a pole
        stay, a tram cable): the endpoints are projected, and the line steps along its main screen
        axis with its slope snapped to a pixel-art ratio (1 px every n, or n px every 1), so a line
        along x or y of the floor is the clean 2:1 stair (2 across, 1 down, every run equal), a
        vertical one (only z changes) is a straight column, and nothing jags. Each pixel takes the
        depth of its point on the segment plus `bias`, so the line draws over the face it runs on
        and boxes in front still hide it. sag: px the middle droops (a hanging wire), one parabola
        added to the stair and rounded once (lines flatter than 45 degrees on screen; a steeper one
        ignores it). The line gets no outline or rim (it would turn into the outline
        colour); give it a dark slot against a light ground or a light one against a dark ground.
        Returns its object id."""
        self.nobj += 1; oid = self.nobj
        self.nolines.add(oid)
        pa, pb = np.array(a, float), np.array(b, float)
        x0, y0 = self.to_screen(*pa)
        x1, y1 = self.to_screen(*pb)
        dx, dy = x1 - x0, y1 - y0
        steep = abs(dy) > abs(dx)
        L = abs(dy) if steep else abs(dx)
        n = int(math.floor(L + 0.5))
        sgn = 1 if (dy if steep else dx) >= 0 else -1
        k = ((dx / dy) if steep else (dy / dx)) if L > 1e-9 else 0.0
        cs = 1 if (dx if steep else dy) >= 0 else -1     # which way the across steps go
        if abs(k) < 1e-3:
            off = lambda i: 0
        elif abs(k) <= 1:
            run = max(1, int(round(1 / abs(k))))             # 1 px across every `run` px along
            off = lambda i: cs * (i // run)
        else:
            off = lambda i: cs * int(round(abs(k))) * i
        sx0, sy0 = math.floor(x0 + 0.5), math.floor(y0 + 0.5)
        prev = None
        for i in range(n + 1):
            u = i / n if n else 0.0
            X, Y = (sx0 + off(i), sy0 + sgn * i) if steep else (sx0 + sgn * i, sy0 + off(i))
            if sag and not steep:                            # one curve, rounded once: no zigzag
                ks = 0.0 if abs(k) < 1e-3 else cs / run if abs(k) <= 1 else cs * round(abs(k))
                Y = sy0 + int(math.floor(ks * i + 4 * sag * u * (1 - u) + 1e-9))
            d = float(self.view @ (pa + (pb - pa) * u)) + bias
            pts = [(X, Y)]
            if prev is not None and abs(Y - prev[1]) > 1 and X != prev[0]:      # keep a sagging wire unbroken
                st = 1 if Y > prev[1] else -1
                pts = [(X, yy) for yy in range(prev[1] + st, Y + st, st)]
            prev = (X, Y)
            for X, Y in pts:
                if 0 <= X < self.W and 0 <= Y < self.H and d >= self.depth[Y, X]:
                    self.depth[Y, X] = d; self.slot[Y, X] = slot; self.obj[Y, X] = oid; self.face[Y, X] = 4
                    self.shadow[Y, X] = False
        return oid

    def _shade(self, slot, step):
        s2 = shade(slot, step)
        return s2 if self.slots is None or s2 in self.slots else slot

    def render(self, outline=True, rim=True, between=True, ol='ol', silhouette=False):
        """the finished slot grid. outline: an 'ol' line where a shape meets empty background.
        between: one step darker where a shape stands in front of a different, farther one.
        rim: one step lighter on the lit front edges of top faces. silhouette=True (or a depth
        gap, default 1.5): the between line is drawn in 'ol' instead, so a full-bleed scene with
        no empty background still gets the sticker-iso black silhouette round every object that
        stands in front of another (the line goes on the nearer object where the object id
        changes, and on the object's own side where it meets a lines=False object such as the
        ground, so a box standing on the ground is closed at its foot; lines=False objects and
        sprites, which carry their own outline, get none)."""
        out = self.slot.copy()
        for yy, xx in zip(*np.nonzero(self.shadow)):
            out[yy, xx] = self._shade(out[yy, xx], getattr(self, 'shadow_step', -1))
        obj, dep, face = self.obj, self.depth, self.face
        H, W = obj.shape
        pad = lambda a, v: np.pad(a, 1, constant_values=v)
        po, pd = pad(obj, -1), pad(dep, -1e9)
        nl = np.isin(obj, list(self.nolines)) if self.nolines else np.zeros_like(obj, bool)
        filled = obj >= 0
        sil = np.zeros_like(filled)
        gap = 1.5 if silhouette is True else float(silhouette or 1.5)
        pnl = np.pad(nl, 1, constant_values=False)
        if between or silhouette:
            # in front of a different, farther object (or a different face of a very different depth)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                no = po[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
                nd = pd[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
                if silhouette:                       # farther neighbour, or a line-less one (the ground)
                    nn = pnl[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
                    sil |= filled & ~nl & (no >= 0) & (no != obj) & ((nd < dep - gap) | nn)
                if between:
                    m = filled & ~nl & (no >= 0) & (no != obj) & (nd < dep - 1.5) & ~sil
                    for yy, xx in zip(*np.nonzero(m)):
                        out[yy, xx] = self._shade(out[yy, xx], -1)
        if rim:
            # top-face pixels right above this object's own side faces: the lit front edges
            below_face = np.pad(face, ((0, 1), (0, 0)))[1:]
            below_obj = np.pad(obj, ((0, 1), (0, 0)), constant_values=-1)[1:]
            m = filled & ~nl & (face == 1) & (below_obj == obj) & ((below_face == 2) | (below_face == 3))
            for yy, xx in zip(*np.nonzero(m)):
                out[yy, xx] = self._shade(out[yy, xx], +1)
        if outline:
            m = np.zeros_like(filled)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                m |= po[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] < 0
            m &= filled & ~nl
            out[m] = ol
        if silhouette:
            out[sil] = ol
        g = artlib.Grid(W, H)
        g.a = [list(r) for r in out]
        return g

def ground_dither(x, y, frac):
    """True for a share `frac` (0..1) of pixels in an even Bayer pattern: light pools, haze"""
    return (BAYER4[int(y) & 3, int(x) & 3] + 0.5) / 16 < frac

def clone(s):
    """a copy of a scene (draw the static world once, then add moving things per frame)"""
    c = Iso.__new__(Iso)
    c.__dict__.update(s.__dict__)
    for k in ('slot', 'depth', 'obj', 'face', 'norm', 'world', 'shadow'):
        setattr(c, k, getattr(s, k).copy())
    c.boxes = list(s.boxes); c.solids = list(s.solids)
    c.nolines = set(s.nolines)
    return c

def frustum(s, X, Y, Z, w, d, h, mat, top_w=2, top_d=None, face=None, **faces):
    """a tapering tower (Transamerica-style): footprint shrinks linearly from w x d to top_w x top_d
    over h px, built from 1 px slices so the slanted edges come out as clean steps. face(u, v, t)
    patterns receive tower-wide coordinates (v = px above the base)."""
    top_d = top_w if top_d is None else top_d
    for z in range(int(h)):
        f = z / max(1, h - 1)
        sw, sd = (w - top_w) * f / 2, (d - top_d) * f / 2
        kw = dict(faces)
        if face is not None:
            kw['left'] = kw['right'] = (lambda z0, ox: (lambda u, v, t, **k: face(u + ox, v + z0, t, **k)))(z, sw)
        s.box(X + sw, Y + sd, Z + z, w - 2 * sw, d - 2 * sd, 1, mat, **kw)
