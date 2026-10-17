"""Quarry Wakes: compose image A ("It rises") and image B ("The slam") from the world, the boss
part sprites, the soldier and the FX; export the delivered 4x frames, 1x copies, the four era
layers per image (bg, boss, soldier, fx on transparent), the actor masks, the palette and the
boss part sheet with pivots."""
import sys, json, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from PIL import Image
from canvas import Canvas
from pal import PAL, write as write_pal
import world, boss, soldier, fx_cells as F

W, H = 304, 224
OUT = pathlib.Path(__file__).resolve().parents[1] / 'out'

def rgba(g):
    """slot grid -> RGBA image, None transparent"""
    a = np.zeros((H, W, 4), np.uint8)
    for k in set(g.ravel()) - {None}:
        hx = PAL[k]
        a[g == k] = (int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16), 255)
    return Image.fromarray(a, 'RGBA')

def over(dst, src, where=None):
    m = ~np.equal(src.g, None)
    if where is not None:
        m &= where
    dst.g[m] = src.g[m]

import palette as _P
_SUBL = {}
def sub_slot(v):
    """a boss slot as it looks under the water: one of three deep teal steps by its value"""
    if v not in _SUBL:
        Lv = _P.lch(PAL[v])[0]
        _SUBL[v] = 'sub0' if Lv < 0.33 else ('sub1' if Lv < 0.5 else 'sub2')
    return _SUBL[v]

def surface(wy, seed=17):
    """the wobbling water surface row per column: wy + (-1, 0, 1) in runs of 3-7 px"""
    ys = np.zeros(W, int)
    x, k = 0, 0
    while x < W:
        n = 3 + int(F._h(k, 1, seed) * 5)
        ys[x:x + n] = wy + int(F._h(k, 2, seed) * 3) - 1
        x += n
        k += 1
    return ys

def rim_y(near):
    """the near rim's top row per column (from the near canvas's rock slots)"""
    ys = np.full(W, H, int)
    for x in range(W):
        col = [y for y in range(140, H) if str(near.g[y, x]).startswith('rock')]
        if col:
            ys[x] = col[0]
    return ys

def build(moment):
    p = boss.POSES[moment]
    far, near = world.build(slam=(moment == 'B'))
    parts = {P.name: P for P in boss.assemble(moment)}
    order = boss.assemble(moment)
    parts = {P.name: P for P in order}
    wy = p['water']
    # layers (each a full-frame canvas, None = clear)
    bg = Canvas(W, H, None); over(bg, far)
    rockm = np.vectorize(lambda v: str(v).startswith('rock'))(near.g)
    back = Canvas(W, H, None)                    # drawn behind the near rim
    front = Canvas(W, H, None)                   # what reaches over the rim (claws, legs below the surface)
    ys = surface(wy) if moment == 'A' else np.full(W, wy)
    yy = np.arange(H)[:, None]
    below = yy >= ys[None, :]
    depth = np.zeros(W, int)
    x, k = 0, 0
    while x < W:                                 # how deep the hull still shows under the water
        n = 3 + int(F._h(k, 3, 23) * 6)
        depth[x:x + n] = 8 + int(F._h(k, 4, 23) * 7)
        x += n
        k += 1
    for P in order:
        g = P.c.g
        m = ~np.equal(g, None)
        if P.name in ('leg_r', 'leg_f'):
            up = m & ~below
            back.g[up] = g[up]
            dn = m & below
            if moment == 'A':
                on_rim = dn & rockm
                front.g[on_rim] = g[on_rim]
                wet = dn & ~rockm
                front.g[wet] = np.vectorize(sub_slot, otypes=[object])(g[wet]) if wet.any() else front.g[wet]
            else:
                front.g[dn] = g[dn]
        else:
            up = m & ~below
            back.g[up] = g[up]
            if moment == 'A':
                wet = m & below & (yy < (ys + depth)[None, :])
                if wet.any():
                    back.g[wet] = np.vectorize(sub_slot, otypes=[object])(g[wet])
    if moment == 'A':                            # a broken sheen along the surface over the drowned parts
        for x in range(W):
            y = ys[x]
            for cv in (back, front):
                if cv.g[y, x] is not None and str(cv.g[y, x]).startswith('sub') and F._h(x // 2, 5, 29) < 0.55:
                    cv.g[y, x] = 'water4'
    bosscv = Canvas(W, H, None)
    over(bosscv, back)
    over(bosscv, front)
    win = parts['cabin'].anchors['window']
    # the window's reflection: three gold dashes on the dark water under the hull
    for (dx, dy, n) in ((-2, 9, 4), (1, 15, 3), (-1, 22, 5)):
        for k in range(n):
            bg.put(win[0] + dx + k, wy + dy, 'wglint1' if k == 1 else 'wglint0')
    if moment == 'A':
        sol, sbox = soldier.draw(266, 189, 'brace')
    else:
        sol, sbox = soldier.draw(263, 190, 'flinch')
    fxc = Canvas(W, H, None)
    fxb = Canvas(W, H, None)
    ry = rim_y(near)
    if moment == 'A':
        # the water crown along the hull's waterline: foam lobes, jets of shrinking cells
        hull = np.nonzero(~np.equal(parts['body'].c.g[wy - 1], None))[0]
        hx0, hx1 = int(hull.min()) - 4, int(hull.max()) + 4
        # water sheeting off the deck edge: clustered at the bow (under the jaw) and the stern,
        # mismatched spacing, length and width, some breaking into drops
        bg_ = parts['body'].c.g
        i = 0
        for (cx, n, spread) in ((hx1 - 16, 5, 13), (hx0 + 10, 4, 9), (hx0 + 66, 2, 6), (hx0 + 104, 1, 3)):
            for j in range(n):
                xs = int(cx + (F._h(i, 1, 61) - 0.5) * 2 * spread)
                col = [y for y in range(60, wy) if bg_[y, xs] == 'rust5']
                i += 1
                if not col:
                    continue
                y0 = col[0] + 2
                longs = F._h(i, 2, 61) < 0.55
                y1 = wy - 2 if longs else y0 + 4 + int(F._h(i, 3, 61) * 12)
                wd = 1 + (F._h(i, 4, 61) < 0.35) + (F._h(i, 5, 61) < 0.1)
                F.sheet(fxc, xs, y0, y1, seed=60 + i, width=wd)
                if not longs:
                    for kk in range(2):
                        F.cell(fxc, xs, y1 + 3 + kk * 5 + int(F._h(i, 6 + kk, 61) * 3), 1 + (kk == 0 and wd > 1), 'spray3')
        F.foam(fxc, hx0, hx1, wy, seed=3, height=(3, 8))
        # splash crowns of mismatched size erupting around the body
        for i, (x, size, arms, ln) in enumerate(((hx0 + 3, 30, 5, -0.25), (hx0 + 54, 15, 3, -0.1),
                                                 (hx0 + 86, 21, 4, 0.05), (hx0 + 118, 12, 3, 0.1),
                                                 (hx1 - 4, 38, 6, 0.3))):
            F.crown(fxc, x, wy - 1, size, seed=11 + i, arms=arms, lean=ln)
        for i, (x, age, n) in enumerate(((hx0 + 2, 12, 12), (hx1 + 2, 14, 16), (hx0 + 86, 8, 8))):
            F.jet(fxc, x, wy - 16, age, n, seed=21 + i, sizes=(2, 2, 1, 1, 1), up=(1.6, 3.0),
                  lean=0.25 * (1 if x > 120 else -1))
        # where the legs break the surface
        for nm in ('leg_r', 'leg_f'):
            gm = ~np.equal(parts[nm].c.g[wy + 2], None)
            xs = np.nonzero(gm)[0]
            if len(xs):
                F.foam(fxc, int(xs.min()) - 4, int(xs.max()) + 5, wy + 3, seed=7 + len(nm), height=(2, 6))
        # cascades pouring from the three hanging buckets
        for i in range(3):
            Lk = parts['link%d' % (i + 1)]
            for side, key in ((0, 'lipL'), (1, 'lipR')):
                x, y = Lk.anchors[key]
                if (i + side) % 2 == 0 or i == 2:
                    F.cascade(fxc, x - (2 if side == 0 else -1), y + 1, wy, seed=31 + 3 * i + side)
        # drips under the jaw's buckets
        jg = parts['jaw'].c.g
        pts = []
        for x in range(0, W, 7):
            col = np.nonzero(~np.equal(jg[:, x], None))[0]
            if len(col) and col.max() < wy - 6:
                pts.append((x, int(col.max())))
        F.drips(fxc, pts[::2], seed=5)
        # one hand-shaped puff coughed from the stack
        mx, my = parts['stack'].anchors['mouth']
        F.smoke(fxc, mx + 6, my - 10, 0.28, seed=4, r=(4.0, 14.0), rise=8.0)
    if moment == 'B':
        import fx as kitfx
        ff = parts['leg_f'].anchors['foot']
        ix, iy = ff[0], int(ry[ff[0]])
        # cracks radiating from the claws into the rim (near layer, dark seams with a lit lip)
        for i, (dx, dy, n) in enumerate(((-1, 1, 9), (1, 1, 11), (-1, 0, 7), (1, 0, 8), (0, 1, 6))):
            x, y = ix + (i - 2) * 3, iy + 2
            for k in range(n):
                x += dx if (k % 2 == 0 or dy == 0) else 0
                y += dy if (k % 3 != 2) else 0
                if 0 <= x < W and 0 <= y < H and str(near.g[y, x]).startswith('rock'):
                    near.g[y, x] = 'rock0'
                    if y - 1 >= 0 and str(near.g[y - 1, x]).startswith('rock'):
                        near.g[y - 1, x] = 'rock3'
        # the dust wall across the full width, crowns along the rim, debris arcing
        yr = lambda x: int(ry[min(W - 1, max(0, int(x)))])
        F.dust_wall(fxc, ix, iy, yr, seed=5, back=fxb, calm=(sbox[0], sbox[2]))
        F.bursts(fxb, [(x, yr(x)) for x in (22, 61, 104, 139, 168, 241, 268, 293)], 40, seed=9, n=7)
        kitfx.debris(fxc, ix - 2, iy - 3, 0.42, n=14, seed=3, speed=(30, 62), g=46.0, spread=(0.08, 0.92),
                     slots=('rock4', 'rock3', 'rock3', 'rock1'), size=(1, 2))
        kitfx.debris(fxc, ix + 3, iy - 2, 0.6, n=8, seed=8, speed=(40, 70), g=40.0, spread=(0.15, 0.6),
                     slots=('dust3', 'dust2', 'dust1'), size=(1, 2))
        # chunks: a few hand-placed rock lumps in flight (3x2 to 5x4), lit cap
        for (x, y, w, h) in ((ix - 31, iy - 30, 4, 3), (ix + 24, iy - 36, 5, 4), (ix - 12, iy - 44, 3, 2),
                             (ix + 44, iy - 18, 3, 3)):
            fxc.rect(x, y, x + w, y + h, 'rock2')
            fxc.rect(x, y, x + w - 1, y + 1, 'rock4')
            fxc.put(x + w - 1, y + h - 1, 'rock0')
        # water streaming off the hull bottom: irregular streams, a few breaking into drops
        bgm = ~np.equal(parts['body'].c.g, None)
        hxs = np.nonzero(bgm.any(0))[0]
        x = int(hxs.min()) + 5
        i = 0
        while x < int(hxs.max()) - 3:
            col = np.nonzero(bgm[:, x])[0]
            if len(col) and col.max() < wy:
                y0 = int(col.max()) + 1
                y1 = wy - 1 if F._h(i, 1, 81) < 0.6 else y0 + 3 + int(F._h(i, 2, 81) * 6)
                F.sheet(fxc, x, y0, y1, seed=80 + i, width=1 + (F._h(i, 3, 81) < 0.35))
                if y1 >= wy - 1:
                    F.cell(fxc, x - 1, wy - 2, 3, 'spray2', rim='spray3')
            x += 6 + int(F._h(i, 4, 81) * 13)
            i += 1
        for i in range(3):
            Lk = parts['link%d' % (i + 1)]
            x, y = Lk.anchors['lipR']
            for k in range(4 + i):
                F.cell(fxc, x + 3 + k * 3 + i, y - 2 - k * 2 + (k * k) // 3, 2 if k < 2 else 1, 'spray3' if k % 2 else 'spray2')
        # three exhaust puffs, the oldest highest and thinnest
        mx, my = parts['stack'].anchors['mouth']
        for i, (age, dx, dy) in enumerate(((0.9, 60, 12), (0.62, 36, 10), (0.34, 15, 8))):
            F.smoke(fxc, mx + dx, my + dy, age, seed=40 + i, r=(4.0, 12.0), rise=6.0)
    return dict(bg=bg, near=near, boss=bosscv, back=back, front=front, soldier=sol, fx=fxc, fxb=fxb, parts=parts, order=order,
                sbox=sbox, rim=ry)

def frame_of(L, moment):
    c = Canvas(W, H, None)
    for k in ('bg', 'back', 'soldier', 'near', 'fxb', 'front', 'fx'):
        over(c, L[k])
    return c

def export(moment, tag):
    L = build(moment)
    fr = frame_of(L, moment)
    img = fr.image(PAL)
    img.save(OUT / ('06-%s@1x.png' % tag))
    img.resize((W * 4, H * 4), Image.NEAREST).save(OUT / ('06-%s.png' % tag))
    # era layers: bg (far + near world), boss, soldier, fx, each on transparent
    bgl = Canvas(W, H, None); over(bgl, L['bg']); over(bgl, L['near'])
    fxl = Canvas(W, H, None); over(fxl, L['fxb']); over(fxl, L['fx'])
    for name, cv in (('bg', bgl), ('boss', L['boss']), ('soldier', L['soldier']), ('fx', fxl)):
        rgba(cv.g).save(OUT / ('06-%s-layer-%s.png' % (tag, name)))
    # actor mask: boss and soldier pixels as they show in the frame
    act = np.zeros((H, W), bool)
    for nm in ('back', 'front', 'soldier'):
        cv = L[nm]
        m = ~np.equal(cv.g, None)
        act |= m & (fr.g == cv.g)
    Image.fromarray((act * 255).astype(np.uint8), 'L').save(OUT / ('06-%s-actor.png' % tag))
    return L, fr

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    write_pal(OUT / 'palette.json')
    for m in sys.argv[1:] or ['A', 'B']:
        export(m, m.lower())
