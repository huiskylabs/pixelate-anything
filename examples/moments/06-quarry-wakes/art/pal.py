"""Quarry Wakes palette: one strict palette by named roles, every slot on the Neo Geo 15-bit grid
(5 bits per channel). The world is cold, dark and low-chroma and is hand-picked as 5-bit triplets
(the grid is coarse in the darks); the boss and the soldier carry the warm chroma, the mustard
coat the top of it (C .16), the rust and the window below it (C <= .13)."""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import json, math
import numpy as np
import colorlib as cl
import palette as P

_V = np.round(np.arange(32) * 255 / 31).astype(int)
_R, _G, _B = np.meshgrid(_V, _V, _V, indexing='ij')
_RGB = np.stack([_R.ravel(), _G.ravel(), _B.ravel()], 1)
_LAB = cl.rgb_to_oklab(_RGB.astype(float))
_BLACK = (_RGB.sum(1) == 0)

def L(Lv, C, h):
    """the 15-bit colour nearest to OKLCh (Lv, C, h) (L weighted double); never pure black"""
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    d = 4 * (_LAB[:, 0] - Lv) ** 2 + (_LAB[:, 1] - a) ** 2 + (_LAB[:, 2] - b) ** 2
    d[_BLACK] = 9
    return '#%02x%02x%02x' % tuple(_RGB[int(np.argmin(d))])

def T(r, g, b):
    """a 5-bit triplet (0..31 each) as hex"""
    return '#%02x%02x%02x' % (_V[r], _V[g], _V[b])

def build():
    pal = {}
    def put(name, hexes):
        for i, hx in enumerate(hexes):
            pal['%s%d' % (name, i)] = hx
    # ---------------- world: cold, dark, low chroma (5-bit triplets)
    put('sky', [T(1, 1, 3), T(2, 2, 4), T(3, 2, 5), T(4, 3, 5), T(6, 4, 6)])     # indigo -> mauve
    put('glow', [T(8, 5, 6), T(11, 7, 6), T(13, 9, 7)])                           # the ember band
    put('far', [T(2, 3, 4), T(3, 4, 5), T(4, 5, 7), T(6, 7, 8)])                  # far terraces
    put('side', [T(1, 1, 2), T(2, 2, 3), T(3, 3, 4), T(4, 4, 6), T(5, 6, 7)])     # side walls
    put('water', [T(0, 1, 2), T(1, 2, 3), T(1, 3, 4), T(2, 4, 5), T(3, 6, 7)])
    put('rock', [T(1, 0, 2), T(1, 1, 2), T(2, 2, 3), T(3, 3, 5), T(4, 5, 6)])     # near rim
    put('crane', [T(1, 2, 2), T(2, 3, 4), T(4, 5, 6), T(6, 8, 9)])                # cold steel
    put('wglint', [T(21, 14, 5), T(25, 21, 12)])                                  # window dashes on water
    # ---------------- boss: warm, saturated, hand-modelled
    put('rust', P.ramp('#9a4426', steps=7, style='arcade', l_max=0.82))
    put('iron', [T(4, 1, 1), T(6, 3, 2), T(8, 6, 5), T(11, 9, 7), T(15, 12, 10)])
    put('pist', [T(8, 6, 4), T(13, 11, 8), T(18, 17, 14), T(24, 23, 20)])
    put('moss', [T(3, 5, 1), T(5, 8, 2), T(10, 10, 2)])
    put('win', [T(15, 7, 1), T(22, 14, 5), T(27, 21, 12), T(30, 28, 22)])
    put('dglass', [T(1, 1, 3), T(3, 4, 6)])
    # ---------------- soldier: the mustard coat holds the frame's top chroma
    put('coat', [L(.27, .060, 55), T(14, 9, 0), T(19, 14, 0), T(24, 18, 0), T(28, 22, 0), L(.92, .080, 95)])
    put('oliv', [T(2, 3, 1), T(5, 5, 2), T(8, 8, 4), T(11, 11, 7)])
    put('skin', [T(13, 8, 6), T(19, 12, 9), T(22, 18, 14)])
    put('boot', [T(2, 1, 1), T(5, 3, 2)])
    # ---------------- fx
    put('spray', [T(3, 10, 11), T(10, 15, 16), T(17, 22, 22), T(26, 27, 27)])
    put('smoke', [T(2, 2, 1), T(4, 4, 3), T(7, 6, 5), T(10, 9, 8), T(13, 12, 11), T(16, 16, 15)])
    put('dust', [T(7, 5, 4), T(10, 8, 7), T(14, 12, 10), T(17, 16, 15), T(21, 20, 18)])
    for k, v in pal.items():                       # every slot must already sit on the grid
        q = tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
        if any(c not in _V for c in q):
            pal[k] = L(*P.lch(v))
    return pal

PAL = build()

def write(path):
    json.dump(PAL, open(path, 'w'), indent=1, sort_keys=True)

if __name__ == '__main__':
    for k, v in PAL.items():
        Lv, C, h = P.lch(v)
        print('%-8s %s  L %.3f  C %.3f  h %5.1f' % (k, v, Lv, C, h))
    print(len(PAL), 'slots,', len(set(PAL.values())), 'distinct colours')
