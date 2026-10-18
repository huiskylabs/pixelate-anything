"""Hooded pilgrims for Tide Procession: slot maps drawn here (contre-jour: no outline, 1 px legs, a
cool 1 px rim on the moon side, a warm rim beside the lantern). Facing right, toward the island.

    f = pilgrim(31, 'staff', frame=0, seed=0, lead=True)
    f['g']       object grid (None = clear)
    f['anchor']  (ax, ay): the ground pixel between the feet
    f['lamp']    (lx, ly): the lantern core

Silhouette keys: a pointed hood whose tip leans back, a robe that tapers wider to a flared hem, a
staff (or pole, or crook) taller than the head, a lantern held out on the island side, 1 px legs.
Kinds: 'staff' upright with a staff; 'pack' a bedroll and a lantern on a forward pole; 'elder'
stooped on a crook staff with the lantern hung from the crook; 'high' the lantern raised ahead.
"""
import math
import numpy as np


def _h(a, b=0, s=0):
    h = (int(a) * 374761393 + int(b) * 668265263 + int(s) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


class _G:
    def __init__(self, w, h):
        self.g = np.full((h, w), None, object)
        self.W, self.H = w, h

    def put(self, x, y, v):
        x, y = int(x), int(y)
        if 0 <= x < self.W and 0 <= y < self.H:
            self.g[y, x] = v

    def span(self, y, x0, x1, v):
        for x in range(int(x0), int(x1) + 1):
            self.put(x, y, v)

    def line(self, x0, y0, x1, y1, v):
        n = int(max(abs(x1 - x0), abs(y1 - y0)))
        for i in range(n + 1):
            u = i / max(1, n)
            self.put(round(x0 + (x1 - x0) * u), round(y0 + (y1 - y0) * u), v)


def pilgrim(h=31, kind='staff', frame=0, seed=0, lead=False, tall=False):
    pad = 10 if tall else 5                                   # headroom for staffs and raised lanterns
    Wd = 28
    P = _G(Wd, h + pad)
    cx = 11                                    # body axis column
    top = pad                                  # hood tip row
    foot = h + pad - 1
    stoop = 2 if kind == 'elder' else 0
    hood_h = 7 if h >= 31 else 6
    hem = foot - 2 - (1 if _h(seed, 1) < 0.3 else 0)
    body = 'fig0'
    # --- the robe: from the shoulders to a flared hem, wider at the back, the hem leaning right
    sh = top + hood_h - 1
    for y in range(sh, hem + 1):
        u = (y - sh) / max(1, hem - sh)
        back = 3 + int(round((1.4 + (0.6 if _h(seed, 2) < 0.5 else 0)) * u ** 1.2))
        front = 2 + int(round(1.5 * u ** 1.4))
        bend = int(round(stoop * (1 - u) ** 2))                 # the elder's rounded back
        if kind == 'elder' and y < sh + 6:
            back += 1                                           # a hump over the shoulders
        P.span(y, cx - back + bend, cx + front + bend, body)
    # ragged hem: one side 1 px lower, a notch by the walking leg
    P.span(hem + 1, cx - 3, cx - 2 + (1 if frame % 2 else 0), body)
    if _h(seed, 3) < 0.5:
        P.put(cx + 3, hem + 1, body)
    # --- the hood: tip leaning back, a face opening on the island side
    hx = cx + stoop
    rows = [(-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 1), (-2, 1), (-3, 1)]
    if hood_h == 6:
        rows = [(-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 1), (-3, 1)]
    hx += 1 if (kind != 'elder' and frame % 2 == 0) else 0       # a walking lean on the open strides
    for k, (a, b) in enumerate(rows):
        y = top + k + stoop
        P.span(y, hx + a, hx + b, body)
    if kind == 'elder':
        P.span(top + stoop - 1, hx - 3, hx - 2, body)           # the hood tip droops back
    # --- legs: 1 px, by walk drawing
    legs = {0: (-2, 2, 0, 0), 1: (-1, 0, 0, 0), 2: (-3, 1, 0, 0), 3: (0, 1, 1, 0), 4: (-1, 1, 0, 0)}
    bl, fl, lift_b, lift_f = legs[frame % 5]
    for y in range(hem + 1, foot + 1):
        u = (y - hem) / max(1, foot - hem)
        P.put(cx - 1 + round(bl * u), y - (lift_b if y == foot else 0), 'fig0')
        P.put(cx + round(fl * u), y - (lift_f if y == foot else 0), 'fig0')
    # --- the staff (back hand) or pole or crook, and the lantern
    lamp = None
    if kind in ('staff', 'high'):
        sx = cx - 5 - (1 if _h(seed, 4) < 0.4 else 0)
        P.line(sx + 1, top - (8 if tall else 3), sx, foot, 'fig1')   # a staff leaning forward a little
        P.put(sx + 1, top + hood_h + 5, 'fig0')                 # the back hand on it
    if kind == 'staff':
        hand = (cx + 5, sh + 7)
        P.line(cx + 2, sh + 2, hand[0], hand[1], body)          # forearm out
        P.put(hand[0] + 1, hand[1] + 1, 'fig1')                 # the bail
        lamp = (hand[0] + 1, hand[1] + 3)
    elif kind == 'high':
        hand = (cx + 6, sh - 3)
        P.line(cx + 2, sh + 2, hand[0], hand[1], body)          # arm raised ahead
        P.put(hand[0], hand[1] + 1, 'fig1')
        lamp = (hand[0], hand[1] + 3)
    elif kind == 'pack':
        for y in range(sh + 1, sh + 6):                         # the bedroll on the back
            P.span(y, cx - 6, cx - 4, body)
        P.span(sh, cx - 5, cx - 4, body)
        hand = (cx + 4, sh + 5)
        P.line(cx + 2, sh + 2, hand[0], hand[1], body)
        P.line(hand[0], hand[1], hand[0] + 6, hand[1] - 6, 'fig1')   # the pole, forward and up
        P.put(hand[0] + 6, hand[1] - 5, 'fig1')
        lamp = (hand[0] + 6, hand[1] - 3)
    elif kind == 'elder':
        sx = cx + 7
        P.line(sx, foot, sx - 1, top + 1, 'fig1')               # crook staff planted ahead
        P.put(sx, top, 'fig1')
        P.put(sx + 1, top, 'fig1')
        P.put(sx + 2, top + 1, 'fig1')                          # the crook curls forward
        P.line(cx + 2, sh + 3, sx - 1, sh + 4, body)            # the arm on the staff
        lamp = (sx + 2, top + 4)
    # --- rims: cool on the island side (the moon is up and right), warm next to the lantern
    g = P.g
    m = ~np.equal(g, None)
    for y in range(top, hem + 1):
        xs = np.nonzero(m[y])[0]
        if not len(xs):
            continue
        xr = xs.max()
        if g[y, xr] == body and y >= top + 1:
            g[y, xr] = 'figr'
    for y in range(top, top + 3 + stoop):                       # the hood's crown catches it too
        xs = np.nonzero(m[y])[0]
        if len(xs) and g[y, xs.max() - 1] == body and y == top + 1 + stoop:
            g[y, xs.max() - 1] = 'figr'
    lx, ly = lamp
    for (y, x), v in np.ndenumerate(g):
        if v in ('figr', body) and abs(x - lx) <= 3 and -2 <= y - ly <= 1 and x >= cx and (
                x + 1 >= g.shape[1] or g[y, x + 1] is None or v == 'figr'):
            g[y, x] = 'figw'
    # --- the lantern: a warm core with a one-slot ring (the lead's is one size up)
    core = [(0, 0), (0, 1)] if not lead else [(0, 0), (1, 0), (0, 1), (1, 1)]
    ring = set()
    for dx, dy in core:
        for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ring.add((dx + ex, dy + ey))
    ring -= set(core)
    for dx, dy in ring:
        P.put(lx + dx, ly + dy, 'lamp1')
    for dx, dy in core:
        P.put(lx + dx, ly + dy, 'lamp3' if (dy == 0 or not lead) else 'lamp2')
    if lead:
        P.put(lx, ly + 2, 'lamp1')
    return {'g': P.g, 'anchor': (cx, foot), 'lamp': (lx, ly)}


if __name__ == '__main__':
    # a contact sheet of the four kinds and five drawings at 8x
    import sys
    sys.path.insert(0, '/home/user/pixelate-anything/tools')
    sys.path.insert(0, '/home/user/pixelate-anything/examples/moments/04-tide-procession/art')
    from PIL import Image
    import scene
    from canvas import to_image
    sheet = np.full((50, 30 * 10), None, object)
    k = 0
    for kind, h in (('staff', 31), ('pack', 33), ('elder', 29), ('high', 30), ('staff', 34)):
        for fr in (0, 1):
            f = pilgrim(h, kind, fr, seed=k, lead=(k == 0))
            g = f['g']
            sheet[45 - g.shape[0] + 1:46, k * 30:k * 30 + g.shape[1]] = g[:min(g.shape[0], 46)]
            k += 1
    img = to_image(sheet, scene.PAL, scene.PAL['sky4'])
    img.resize((img.width * 6, img.height * 6), Image.NEAREST).save(sys.argv[1] if len(sys.argv) > 1 else 'sheet.png')
