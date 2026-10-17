"""The soldier: a crouched figure in a mustard greatcoat, round helmet, rifle, small pack, facing
left at the boss. A joint rig per pose drawn with strokes shaded across their width (lit side
up-left), outlined in each material's own darkest step. Pose 'brace' (A) and 'flinch' (B)."""
import sys, math
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from canvas import Canvas
from boss import strut, W, H, LIGHT

POSES = {
    # joint offsets from the ground point between the feet (x left is forward, y up negative)
    'brace': dict(foot_f=(-7, 0), knee_f=(-9, -8), hip=(0, -12), foot_b=(7, 0), knee_b=(4, -3),
                  neck=(-3, -23), head=(-4, -27), sh_f=(-3, -21), el_f=(-9, -17), ha_f=(-12, -21),
                  sh_b=(1, -21), el_b=(3, -15), ha_b=(-3, -17), stock=(5, -15), muzzle=(-18, -25),
                  pack=(5, -19), hem=(9, -5), hem_f=(-6, -6), tuck=0),
    'flinch': dict(foot_f=(-3, 0), knee_f=(-1, -7), hip=(2, -10), foot_b=(9, 0), knee_b=(8, -5),
                   neck=(5, -18), head=(7, -21), sh_f=(3, -16), el_f=(-4, -21), ha_f=(10, -22),
                   sh_b=(7, -17), el_b=(11, -12), ha_b=(7, -10), stock=(12, -8), muzzle=(-8, -3),
                   pack=(-1, -15), hem=(14, -3), hem_f=(-5, -4), tuck=1, face=1),
}

COAT = [(-0.6, 'coat4'), (0.1, 'coat3'), (0.6, 'coat2'), (1.0, 'coat1')]
COAT_B = [(-0.4, 'coat3'), (0.3, 'coat2'), (1.0, 'coat1')]          # the far arm, a step darker
OLIV = [(-0.4, 'oliv3'), (0.3, 'oliv2'), (1.0, 'oliv1')]
OLIV_B = [(-0.2, 'oliv2'), (1.0, 'oliv1')]

def draw(ax, ay, pose):
    """-> Canvas (frame size, None = clear) with the soldier whose ground point is (ax, ay),
    and its bbox"""
    p = POSES[pose]
    c = Canvas(W, H, None)
    J = {k: (ax + v[0], ay + v[1]) for k, v in p.items() if isinstance(v, tuple)}
    def disc(pt, r, v):
        c.disc(pt[0], pt[1], r, v)
    # far leg (folded under), far boot
    strut(c, J['hip'], J['knee_b'], 5, OLIV_B)
    strut(c, J['knee_b'], J['foot_b'], 4, OLIV_B)
    disc(J['knee_b'], 2.2, 'oliv1')
    fb = J['foot_b']
    c.rect(fb[0] - 2, fb[1] - 2, fb[0] + 3, fb[1] + 1, 'boot1')
    c.rect(fb[0] - 2, fb[1], fb[0] + 3, fb[1] + 1, 'boot0')
    # far arm
    strut(c, J['sh_b'], J['el_b'], 4, COAT_B)
    strut(c, J['el_b'], J['ha_b'], 3, COAT_B)
    disc(J['el_b'], 1.8, 'coat2')
    # the pack on the back
    px, py = J['pack']
    c.rect(px - 3, py - 4, px + 3, py + 4, 'oliv2')
    c.rect(px - 3, py - 4, px - 1, py + 4, 'oliv3')
    c.rect(px + 2, py - 3, px + 3, py + 4, 'oliv1')
    c.rect(px - 3, py + 1, px + 3, py + 2, 'oliv1')                 # the flap strap
    # greatcoat: a tapered body from the neck to a flared hem (behind) and the front skirt
    nx, ny = J['neck']
    hx, hy = J['hip']
    bx, by = J['hem']
    fx, fy = J['hem_f']
    coat = [(nx - 3, ny), (nx + 4, ny), (hx + 5, hy - 2), (bx, by), (bx - 3, by + 2), (fx + 2, fy + 1),
            (fx, fy), (hx - 6, hy - 3), (nx - 4, ny + 3)]
    m = c.mask_poly(coat)
    c.g[m] = 'coat3'
    # shading across the body: the left (lit) third, a shadow down the back, the hem fold
    yy, xx = np.mgrid[0:H, 0:W]
    span = np.where(m, xx, 0)
    xl = np.where(m.any(1), np.where(m, xx, 9999).min(1), 0)
    xr = np.where(m.any(1), span.max(1), 0)
    wdt = np.maximum(1, xr - xl)
    t = (xx - xl[:, None]) / wdt[:, None]
    c.g[m & (xx <= xl[:, None] + 1)] = 'coat4'
    c.g[m & (t > 0.55)] = 'coat2'
    c.g[m & (t > 0.85)] = 'coat1'
    c.g[m & (yy >= by - 1)] = 'coat2'
    # the belt and a buckle
    belt = m & (yy == hy - 4)
    c.g[belt] = 'boot1'
    c.put(hx - 3 + p['tuck'], hy - 4, 'skin2')
    # collar turned up
    c.rect(nx - 3, ny - 2, nx + 3, ny + 1, 'coat3')
    c.rect(nx - 3, ny - 2, nx - 1, ny + 1, 'coat4')
    c.put(nx - 3, ny - 2, 'coat5')
    # head: a small skin oval facing left, an eye, under the helmet
    hcx, hcy = J['head']
    for y in range(int(hcy) - 3, int(hcy) + 3):
        for x in range(int(hcx) - 3, int(hcx) + 3):
            if ((x + 0.5 - hcx) / 3.1) ** 2 + ((y + 0.5 - hcy) / 3.2) ** 2 <= 1:
                c.put(x, y, 'skin2' if x < hcx - 0.5 else ('skin1' if x < hcx + 1.5 else 'skin0'))
    f = p.get('face', -1)                                            # -1 faces left, 1 turned away right
    c.put(hcx + 3 * f, hcy, 'skin1' if f > 0 else 'skin2')           # the nose
    c.put(hcx + 2 * f, hcy - 1, 'boot0')                             # the eye
    c.put(hcx - 1 * f, hcy + 2, 'skin0')                             # jaw shadow
    # helmet: a dome with a brim, lit cap up-left, the strap down the cheek
    for y in range(int(hcy) - 7, int(hcy) - 1):
        for x in range(int(hcx) - 5, int(hcx) + 6):
            dx, dy = (x + 0.5 - hcx) / 5.2, (y + 0.5 - (hcy - 1.5)) / 5.4
            if dx * dx + dy * dy <= 1 and y < hcy - 1:
                v = 'oliv2'
                if dx + dy < -0.75:
                    v = 'oliv3'
                elif dx > 0.45:
                    v = 'oliv1'
                c.put(x, y, v)
    if f < 0:
        c.rect(hcx - 6, hcy - 2, hcx + 5, hcy - 1, 'oliv1')           # brim
        c.put(hcx - 6, hcy - 2, 'oliv2')
    else:
        c.rect(hcx - 5, hcy - 2, hcx + 6, hcy - 1, 'oliv1')
        c.put(hcx - 5, hcy - 2, 'oliv2')
    c.put(hcx - f, hcy + 1, 'oliv0'); c.put(hcx - f, hcy + 2, 'oliv0')  # strap
    # rifle: a 2 px dark barrel and a brown stock
    sx, sy = J['stock']
    mx, my = J['muzzle']
    c.line(sx, sy, mx, my, 'boot0')
    c.line(sx, sy - 1, mx, my - 1, 'oliv2')
    L = math.hypot(mx - sx, my - sy)
    ux, uy = (mx - sx) / L, (my - sy) / L
    c.line(sx, sy, sx + ux * 6, sy + uy * 6, 'boot1')
    c.line(sx, sy + 1, sx + ux * 5, sy + uy * 5 + 1, 'boot1')
    c.put(mx, my, 'oliv3')
    # near leg: thigh and shin in olive, the boot in front
    strut(c, J['hip'], J['knee_f'], 5, OLIV)
    strut(c, J['knee_f'], J['foot_f'], 4, OLIV)
    disc(J['knee_f'], 2.4, 'oliv2')
    ff = J['foot_f']
    c.rect(ff[0] - 3, ff[1] - 2, ff[0] + 2, ff[1] + 1, 'boot1')
    c.rect(ff[0] - 3, ff[1] - 2, ff[0] - 1, ff[1] - 1, 'oliv2')
    c.rect(ff[0] - 3, ff[1], ff[0] + 2, ff[1] + 1, 'boot0')
    # near arm over everything (coat sleeve, a skin hand)
    strut(c, J['sh_f'], J['el_f'], 4, COAT)
    strut(c, J['el_f'], J['ha_f'], 4, COAT)
    disc(J['el_f'], 2.0, 'coat3')
    hx_, hy_ = J['ha_f']
    c.rect(hx_ - 1, hy_ - 1, hx_ + 2, hy_ + 2, 'skin1')
    c.put(hx_ - 1, hy_ - 1, 'skin2')
    hb = J['ha_b']
    c.rect(hb[0] - 1, hb[1] - 1, hb[0] + 1, hb[1] + 1, 'skin1')
    m = ~np.equal(c.g, None)
    c.outline(m, mode='own', light=LIGHT, lift=0.25)
    ys, xs = np.nonzero(~np.equal(c.g, None))
    return c, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
