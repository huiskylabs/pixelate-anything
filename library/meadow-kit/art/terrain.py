"""Terrain tiles, generated: a 16-tile corner set (grass / dirt) and animated water.

Corner set: tile index = NW*8 + NE*4 + SW*2 + SE, where 1 means that corner is dirt.
Plain tiles get variants (frames 16+) so large areas do not show a 16 px repeat.
The dirt shape comes from the four corners blended across the tile (so neighbouring
tiles always meet), roughened by a little noise that fades to zero at the tile edges.
Edges get pixel-art treatment: a light grass lip where grass overhangs dirt below it,
a dark grass rim elsewhere, and a shadow on the dirt just under the lip.
"""
from artlib import Grid

T = 16

def h(x, y, s):
    """deterministic hash -> [0, 1) (same mixing as the engine's hash)"""
    n = ((x * 73856093) ^ (y * 19349663) ^ (s * 83492791)) & 0xffffffff
    n ^= 0x9e3779b9
    n = ((n ^ (n >> 16)) * 0x85ebca6b) & 0xffffffff
    n = ((n ^ (n >> 13)) * 0xc2b2ae35) & 0xffffffff
    n ^= n >> 16
    return n / 4294967296.0

def dirt_at(mask, x, y):
    nw, ne, sw, se = (mask >> 3) & 1, (mask >> 2) & 1, (mask >> 1) & 1, mask & 1
    u = min(1.0, max(0.0, (x + 0.5) / T)); v = min(1.0, max(0.0, (y + 0.5) / T))
    f = nw * (1 - u) * (1 - v) + ne * u * (1 - v) + sw * (1 - u) * v + se * u * v
    fade = min(1.0, 4 * min(u, 1 - u, v, 1 - v))
    f += (h(x, y, mask) - 0.5) * 0.3 * fade
    return f > 0.5

def tile(mask, var=0):
    g = Grid(T, T)
    D = [[dirt_at(mask, x, y) for x in range(-1, T + 1)] for y in range(-1, T + 1)]
    dirt = lambda x, y: D[y + 1][x + 1]
    for y in range(T):
        for x in range(T):
            if dirt(x, y):
                s = 'dirt0' if not dirt(x, y - 1) else ('dirt1' if h(x, y, 7) < 0.06 else 'dirt2')
            elif dirt(x, y + 1):
                s = 'grass3'                       # light lip where grass overhangs the dirt
            elif dirt(x - 1, y) or dirt(x + 1, y) or dirt(x, y - 1):
                s = 'grass1'                       # dark rim on the other sides
            else:
                s = 'grass1' if h(x, y, 11 + var) < 0.04 else 'grass2'
            g.set(x, y, s)
    # placed details: grass tufts (light tip over a dark root) and pebbles (light top, dark base)
    for i in range(6):
        x, y = 1 + int(h(i, mask + 16 * var, 3) * 13), 1 + int(h(mask + 16 * var, i, 5) * 12)
        if not any(dirt(x + dx, y + dy) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)):
            g.set(x, y, 'grass3'); g.set(x + 1, y - 1 if i % 2 else y, 'grass3')
            g.set(x, y + 1, 'grass1'); g.set(x + 1, y + 1, 'grass1')
    for i in range(3):
        x, y = 1 + int(h(i, mask + 16 * var, 13) * 13), 1 + int(h(mask + 16 * var, i, 17) * 13)
        if all(dirt(x + dx, y + dy) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)):
            g.set(x, y, 'dirt3'); g.set(x + 1, y, 'dirt3' if i else 'dirt2'); g.set(x, y + 1, 'dirt1'); g.set(x + 1, y + 1, 'dirt0')
    return g

def water(frame):
    g = Grid(T, T)
    for y in range(T):
        for x in range(T):
            g.set(x, y, 'tunic1' if (y // 4) % 2 else 'tunic2')
    # wave crests: short light dashes that slide 4 px per frame (16 px over 4 frames: a seamless loop)
    for i, (x0, y) in enumerate([(1, 1), (9, 3), (4, 6), (12, 9), (2, 12), (8, 14)]):
        for dx in range(3):
            x = (x0 + dx + frame * 4 + (i % 2) * 2) % T
            g.set(x, y, 'glass3' if dx == 1 else 'glass2')
    return g

def export():
    return [
        # frames 0-15: the corner set; 16-18: plain grass variants; 19-20: plain dirt variants
        ('sprite', 'grass_dirt', [tile(m) for m in range(16)] + [tile(0, v) for v in (1, 2, 3)] + [tile(15, v) for v in (1, 2)],
         0, 0, {'tile': T, 'variants': {0: [0, 16, 17, 18], 15: [15, 19, 20]}}),
        ('sprite', 'water', [water(f) for f in range(4)], 0, 0, {'fps': 4, 'tile': T, 'tags': {'flow': (0, 3)}}),
    ]
