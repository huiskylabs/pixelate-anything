"""Shared helpers for the Lanternmoss Mire pack (no export(): imported by the other art modules).

Everything here is mechanical: stamping hand-typed slot maps, moving parts between frames,
deterministic hashing. The drawings themselves live in the modules that use these.
"""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
from artlib import Grid


def grid_from(art, key, w=None, h=None):
    """a Grid from a hand-typed block; '.' is transparent; rows must be equal length"""
    rows = [r for r in art.strip('\n').split('\n')]
    rows = [r.strip() for r in rows if r.strip()]
    W = w or max(len(r) for r in rows)
    H = h or len(rows)
    bad = [i for i, r in enumerate(rows) if len(r) != len(rows[0])]
    if bad:
        raise ValueError('ragged rows %s (widths %s)' % (bad, [len(rows[i]) for i in bad]))
    g = Grid(W, H)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c in '. ':
                continue
            if c not in key:
                raise KeyError('unknown key %r at %d,%d' % (c, x, y))
            g.set(x, y, key[c])
    return g


def blank(w, h):
    return Grid(w, h)


def copy(g):
    out = Grid(g.w, g.h)
    out.a = [r[:] for r in g.a]
    return out


def over(dst, src, ox=0, oy=0):
    """paste src's opaque pixels onto dst at (ox, oy), in place; returns dst"""
    for y in range(src.h):
        for x in range(src.w):
            v = src.a[y][x]
            if v is not None and 0 <= x + ox < dst.w and 0 <= y + oy < dst.h:
                dst.a[y + oy][x + ox] = v
    return dst


def shift_rows(g, y0, y1, dy, fill_from_below=False):
    """copy of g with rows y0..y1 (inclusive) moved by dy; vacated rows take the row that was
    under them (fill_from_below) or become transparent"""
    out = copy(g)
    src = [g.a[y][:] for y in range(y0, y1 + 1)]
    for y in range(y0, y1 + 1):
        out.a[y] = [None] * g.w
    for i, row in enumerate(src):
        y = y0 + i + dy
        if 0 <= y < g.h:
            out.a[y] = row
    if fill_from_below and dy > 0:
        for y in range(y0, y0 + dy):
            out.a[y] = [None] * g.w
    return out


def move_region(g, x0, y0, x1, y1, dx, dy):
    """copy of g with the box (inclusive) lifted and put down dx, dy away (vacated -> transparent)"""
    out = copy(g)
    box = [[g.a[y][x] for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            out.a[y][x] = None
    for j, row in enumerate(box):
        for i, v in enumerate(row):
            X, Y = x0 + i + dx, y0 + j + dy
            if v is not None and 0 <= X < g.w and 0 <= Y < g.h:
                out.a[Y][X] = v
    return out


def recolor(g, mapping):
    out = copy(g)
    for y in range(g.h):
        for x in range(g.w):
            v = out.a[y][x]
            if v in mapping:
                out.a[y][x] = mapping[v]
    return out


def flipx(g):
    out = Grid(g.w, g.h)
    out.a = [r[::-1] for r in g.a]
    return out


def h32(x, y, s):
    """deterministic hash -> [0, 1)"""
    n = ((x * 73856093) ^ (y * 19349663) ^ (s * 83492791)) & 0xffffffff
    n ^= 0x9e3779b9
    n = ((n ^ (n >> 16)) * 0x85ebca6b) & 0xffffffff
    n = ((n ^ (n >> 13)) * 0xc2b2ae35) & 0xffffffff
    n ^= n >> 16
    return n / 4294967296.0
