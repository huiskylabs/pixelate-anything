"""Curved solids for pixel-art rebuilds: signed distance fields rendered by tools/iso.py.

Boxes alone turn every place into a box city. Real places have rounded corners, vaults,
domes, arches, cones and walls that flow into each other and into the ground. Describe them
here, then draw them with Iso.solid(node), in any pixel-art camera, with the same outlines,
lit rims, ramp shading and cast shadows as boxes.

    from sdf import RBox, Cyl, Sphere, Cone, Union, Smooth, Sub, Inter, Above, Terrain
    house = Smooth(1.2,
        RBox(0, 0, 0, 10, 8, 9, r=1.2, mat='plaster'),             # rounded whitewashed cube
        Inter(Cyl(5, 4, 9, 4, axis='x', x0=0, x1=10, mat='dome'), Above(9)))   # a blue barrel vault
    house = Sub(house, Arch(2, 7.6, 0, 3, 1, 5, mat='door'))   # an arched door, cut in as a recess
    s.solid(house)

Every leaf carries a material: a ramp name ('plaster' -> plaster0..4, the step chosen from the
surface normal) or a function f(p, n, step, t) -> slot for patterns. A Sub's cut surfaces take
the cutter's material (door recesses, window reveals, pool basins).
"""
import numpy as np

class Node:
    bbox = None
    def leaves(self):
        return [self]

class Prim(Node):
    def __init__(self, bbox, mat):
        self.bbox, self.mat = tuple(float(v) for v in bbox), mat

class RBox(Prim):
    """box from (x0, y0, z0) to (x1, y1, z1) with every edge rounded by r"""
    def __init__(self, x0, y0, z0, x1, y1, z1, r=0.0, mat='plaster'):
        super().__init__((x0, y0, z0, x1, y1, z1), mat)
        self.c = np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
        self.h = np.array([(x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2])
        self.r = min(r, float(self.h.min()) - 1e-3) if r else 0.0
    def d(self, x, y, z):
        qx = np.abs(x - self.c[0]) - (self.h[0] - self.r)
        qy = np.abs(y - self.c[1]) - (self.h[1] - self.r)
        qz = np.abs(z - self.c[2]) - (self.h[2] - self.r)
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
        return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - self.r

class Cyl(Prim):
    """a capped cylinder. axis 'z': centre (a, b) = (x, y), from z0 to z1.
    axis 'x': (a, b) = (y, z), from x0 to x1. axis 'y': (a, b) = (x, z), from y0 to y1."""
    def __init__(self, a, b, lo, r, axis='z', hi=None, mat='plaster', x0=None, x1=None, y0=None, y1=None):
        self.a, self.b, self.rad, self.axis = float(a), float(b), float(r), axis
        if axis == 'z':
            self.lo, self.hi = float(lo), float(hi)
            bbox = (a - r, b - r, lo, a + r, b + r, hi)
        elif axis == 'x':
            self.lo, self.hi = float(x0), float(x1)
            bbox = (x0, a - r, b - r, x1, a + r, b + r)
        else:
            self.lo, self.hi = float(y0), float(y1)
            bbox = (a - r, y0, b - r, a + r, y1, b + r)
        super().__init__(bbox, mat)
    def d(self, x, y, z):
        if self.axis == 'z':
            u, v, w = x - self.a, y - self.b, z
        elif self.axis == 'x':
            u, v, w = y - self.a, z - self.b, x
        else:
            u, v, w = x - self.a, z - self.b, y
        dr = np.sqrt(u * u + v * v) - self.rad
        dh = np.maximum(self.lo - w, w - self.hi)
        return np.minimum(np.maximum(dr, dh), 0) + np.sqrt(np.maximum(dr, 0) ** 2 + np.maximum(dh, 0) ** 2)

class Sphere(Prim):
    def __init__(self, cx, cy, cz, r, mat='plaster'):
        super().__init__((cx - r, cy - r, cz - r, cx + r, cy + r, cz + r), mat)
        self.c, self.r = np.array([cx, cy, cz], float), float(r)
    def d(self, x, y, z):
        return np.sqrt((x - self.c[0]) ** 2 + (y - self.c[1]) ** 2 + (z - self.c[2]) ** 2) - self.r

class Cone(Prim):
    """a vertical cone or frustum from radius r0 at z0 to r1 at z1 (windmill roofs, towers)"""
    def __init__(self, cx, cy, z0, z1, r0, r1=0.0, mat='plaster'):
        R = max(r0, r1)
        super().__init__((cx - R, cy - R, z0, cx + R, cy + R, z1), mat)
        self.cx, self.cy, self.z0, self.z1, self.r0, self.r1 = cx, cy, z0, z1, r0, r1
        self.k = 1.0 / np.sqrt(1 + ((r0 - r1) / max(1e-6, z1 - z0)) ** 2)
    def d(self, x, y, z):
        t = np.clip((z - self.z0) / (self.z1 - self.z0), 0, 1)
        rr = self.r0 + (self.r1 - self.r0) * t
        dr = (np.sqrt((x - self.cx) ** 2 + (y - self.cy) ** 2) - rr) * self.k
        dh = np.maximum(self.z0 - z, z - self.z1)
        return np.maximum(dr, dh)

class Above(Prim):
    """the half space z >= z0 (intersect with it to keep the top half: domes, vaults)"""
    def __init__(self, z0):
        super().__init__((-1e9, -1e9, z0, 1e9, 1e9, 1e9), None)
        self.z0 = z0
    def d(self, x, y, z):
        return self.z0 - z

class Terrain(Prim):
    """ground under a height function height(x, y) (vectorised), inside the given xy bounds.
    Terraces, slopes, curved retaining walls. lip rounds terrace edges."""
    def __init__(self, height, x0, y0, x1, y1, zmin, zmax, mat='ground', k=0.45):
        super().__init__((x0, y0, zmin, x1, y1, zmax), mat)
        self.height, self.k, self.zmin = height, k, zmin
        self.box = RBox(x0, y0, zmin - 50, x1, y1, zmax)
    def d(self, x, y, z):
        return np.maximum((z - self.height(x, y)) * self.k, self.box.d(x, y, z))

class Union(Node):
    def __init__(self, *kids):
        self.kids = [k for k in kids if k is not None]
        b = np.array([k.bbox for k in self.kids])
        self.bbox = tuple(b[:, :3].min(0)) + tuple(b[:, 3:].max(0))
    def d(self, x, y, z):
        out = self.kids[0].d(x, y, z)
        for k in self.kids[1:]:
            out = np.minimum(out, k.d(x, y, z))
        return out
    def leaves(self):
        return [l for k in self.kids for l in k.leaves()]
    def owner(self, x, y, z):
        ds = np.stack([k.d(x, y, z) for k in self.kids])
        i = np.argmin(ds, 0)
        out = np.empty(x.shape, object)
        for j, k in enumerate(self.kids):
            m = i == j
            if m.any():
                out[m] = owner(k, x[m], y[m], z[m])
        return out

class Smooth(Union):
    """union that blends the parts with radius k: plaster flowing between houses and walls"""
    def __init__(self, k, *kids):
        super().__init__(*kids)
        self.k = float(k)
        b = list(self.bbox)
        self.bbox = tuple(b[:3]) + (b[3], b[4], b[5] + self.k)
    def d(self, x, y, z):
        out = self.kids[0].d(x, y, z)
        for kd in self.kids[1:]:
            b = kd.d(x, y, z)
            h = np.clip(0.5 + 0.5 * (b - out) / self.k, 0, 1)
            out = b * (1 - h) + out * h - self.k * h * (1 - h)
        return out

class Sub(Node):
    """a minus b; surfaces cut by b take b's material"""
    def __init__(self, a, *bs):
        self.a, self.bs = a, list(bs)
        self.bbox = a.bbox
    def d(self, x, y, z):
        out = self.a.d(x, y, z)
        for b in self.bs:
            out = np.maximum(out, -b.d(x, y, z))
        return out
    def leaves(self):
        return self.a.leaves() + [l for b in self.bs for l in b.leaves()]
    def owner(self, x, y, z):
        da = self.a.d(x, y, z)
        out = owner(self.a, x, y, z)
        for b in self.bs:
            nb = -b.d(x, y, z)
            m = nb > da
            if m.any():
                out[m] = owner(b, x[m], y[m], z[m])
            da = np.maximum(da, nb)
        return out

class Inter(Node):
    def __init__(self, a, b):
        self.a, self.b = a, b
        A, B = np.array(a.bbox), np.array(b.bbox)
        self.bbox = tuple(np.maximum(A[:3], B[:3])) + tuple(np.minimum(A[3:], B[3:]))
    def d(self, x, y, z):
        return np.maximum(self.a.d(x, y, z), self.b.d(x, y, z))
    def leaves(self):
        return self.a.leaves()
    def owner(self, x, y, z):
        return owner(self.a, x, y, z)

def owner(node, x, y, z):
    """the leaf whose surface a point lies on (for materials)"""
    if hasattr(node, 'owner'):
        return node.owner(x, y, z)
    out = np.empty(np.shape(x), object)
    out[...] = node
    return out

def Arch(x0, y0, z0, w, depth, h, axis='y', mat='door'):
    """an arched opening cutter: a box with a round top, w wide and h tall; axis is the
    direction it cuts through (its depth runs along it)"""
    r = w / 2
    if axis == 'y':
        return Union(RBox(x0, y0, z0 - 1, x0 + w, y0 + depth, z0 + h - r, mat=mat),
                     Cyl(x0 + r, z0 + h - r, None, r, axis='y', y0=y0, y1=y0 + depth, mat=mat))
    return Union(RBox(x0, y0, z0 - 1, x0 + depth, y0 + w, z0 + h - r, mat=mat),
                 Cyl(y0 + r, z0 + h - r, None, r, axis='x', x0=x0, x1=x0 + depth, mat=mat))

class RoundCone(Prim):
    """a limb: a segment from a to b with radius ra at a and rb at b (necks, tails, legs, horns)"""
    def __init__(self, a, b, ra, rb, mat='plaster'):
        a, b = np.array(a, float), np.array(b, float)
        lo = np.minimum(a - ra, b - rb); hi = np.maximum(a + ra, b + rb)
        super().__init__(tuple(lo) + tuple(hi), mat)
        self.A, self.B, self.ra, self.rb = a, b, float(ra), float(rb)
        ba = b - a
        self.l2 = float(ba @ ba); self.rr = self.ra - self.rb
        self.a2 = self.l2 - self.rr * self.rr; self.ba = ba
    def d(self, x, y, z):
        pa = np.stack([x - self.A[0], y - self.A[1], z - self.A[2]], -1)
        l2, rr, a2 = self.l2, self.rr, self.a2
        yy = pa @ self.ba
        zz = yy - l2
        v = pa * l2 - yy[..., None] * self.ba
        x2 = (v * v).sum(-1)
        y2 = yy * yy * l2; z2 = zz * zz * l2
        k = np.sign(rr) * rr * rr * x2
        il2 = 1.0 / l2
        d1 = np.sqrt(x2 + z2) * il2 - self.rb
        d2 = np.sqrt(x2 + y2) * il2 - self.ra
        d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + yy * rr) * il2 - self.ra
        return np.where(np.sign(zz) * a2 * z2 > k, d1, np.where(np.sign(yy) * a2 * y2 < k, d2, d3))

class Plate(Prim):
    """a flat shape: a polygon in the x-z plane (seen face-on by the side camera), thickness t
    around depth y0. Wings, banners, blades, flames, signs."""
    def __init__(self, pts, y0=0.0, t=0.6, mat='plaster'):
        P = np.array(pts, float)
        super().__init__((P[:, 0].min(), y0 - t, P[:, 1].min(), P[:, 0].max(), y0 + t, P[:, 1].max()), mat)
        self.P, self.y0, self.t = P, float(y0), float(t)
    def d(self, x, y, z):
        P = self.P
        dmin = (x - P[0, 0]) ** 2 + (z - P[0, 1]) ** 2
        s = np.ones(np.shape(x))
        n = len(P)
        for i in range(n):
            vi, vj = P[i], P[i - 1]
            ex, ez = vj[0] - vi[0], vj[1] - vi[1]
            wx, wz = x - vi[0], z - vi[1]
            h = np.clip((wx * ex + wz * ez) / (ex * ex + ez * ez + 1e-12), 0, 1)
            bx, bz = wx - ex * h, wz - ez * h
            dmin = np.minimum(dmin, bx * bx + bz * bz)
            c1 = z >= vi[1]; c2 = z < vj[1]; c3 = ex * wz > ez * wx
            flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
            s = np.where(flip, -s, s)
        d2 = s * np.sqrt(dmin)
        return np.maximum(d2, np.abs(y - self.y0) - self.t)
