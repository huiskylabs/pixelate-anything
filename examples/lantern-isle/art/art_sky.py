"""Clouds and low mist. Lobes are hand-placed; shading is by altitude band."""
from artlib import Grid, bayer

def cloud(w, h, lobes, top, mid, low, fringe=True, base=None):
    """lobes: (cx, cy, rx, ry). base: flat bottom row (None = h-1)."""
    base = h - 1 if base is None else base
    inside = set()
    for (cx, cy, rx, ry) in lobes:
        for y in range(h):
            for x in range(w):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 and y <= base:
                    inside.add((x, y))
    g = Grid(w, h)
    for (x, y) in inside:
        up = (x, y - 1) in inside
        up2 = (x, y - 2) in inside
        down = (x, y + 1) in inside
        edge = not all(((x + dx, y + dy) in inside) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if not up:
            v = top
        elif not up2 and bayer(x, y) < 8:
            v = top
        elif not down or y >= base - 1:
            v = low
        else:
            v = mid
        if fringe and edge and bayer(x, y) < 6:
            continue
        g.set(x, y, v)
    return g

def mist(w, h, lobes, slot, core=8, edge=4, seed=0):
    """translucent mist through ordered dither: denser in the core."""
    g = Grid(w, h)
    for y in range(h):
        for x in range(w):
            d = 9.0
            for (cx, cy, rx, ry) in lobes:
                d = min(d, ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
            if d > 1.0:
                continue
            th = core if d < 0.45 else (edge if d < 0.8 else 2)
            if bayer(x, y) < th:
                g.set(x, y, slot)
    return g

def export():
    out = []
    # spring overcast banks (teal sky): slots chosen per altitude
    out.append(('sprite', 'cloud_bank_a', [cloud(230, 16, [(20, 10, 22, 7), (52, 8, 26, 8), (90, 9, 30, 8),
        (128, 7, 28, 8), (164, 9, 30, 7), (200, 10, 26, 6)], 'S2', 'S1', 'S0', base=13)], 0, 0))
    out.append(('sprite', 'cloud_bank_b', [cloud(260, 18, [(24, 11, 26, 7), (62, 9, 30, 9), (104, 10, 32, 8),
        (146, 8, 30, 9), (188, 10, 32, 8), (228, 11, 28, 7)], 'S3', 'S2', 'S1', base=15)], 0, 0))
    out.append(('sprite', 'cloud_bank_c', [cloud(210, 15, [(22, 9, 24, 6), (58, 7, 28, 7), (98, 8, 28, 7),
        (138, 7, 26, 7), (180, 9, 28, 6)], 'S4', 'S3', 'S2', base=12)], 0, 0))
    out.append(('sprite', 'cloud_wisp_a', [cloud(130, 7, [(20, 4, 22, 3), (55, 3, 28, 3), (95, 4, 30, 3)],
        'S5', 'S4', 'S3', base=5)], 0, 0))
    out.append(('sprite', 'cloud_wisp_b', [cloud(110, 6, [(18, 3, 20, 3), (52, 3, 26, 3), (88, 3, 20, 2)],
        'S6', 'S5', 'S4', base=4)], 0, 0))
    # summer dusk streaks lit from below by the afterglow
    out.append(('sprite', 'cloud_dusk_a', [cloud(150, 8, [(20, 4, 22, 3), (58, 3, 34, 4), (104, 4, 36, 3),
        (136, 5, 14, 2)], 'S3', 'S4', 'S6', base=6)], 0, 0))
    out.append(('sprite', 'cloud_dusk_b', [cloud(116, 7, [(18, 4, 20, 3), (52, 3, 30, 3), (92, 4, 24, 3)],
        'S4', 'S5', 'S6', base=5)], 0, 0))
    out.append(('sprite', 'cloud_dusk_c', [cloud(96, 6, [(16, 3, 18, 2), (46, 3, 26, 3), (80, 3, 16, 2)],
        'S5', 'S5', 'S6', base=4)], 0, 0))
    # fall: thin violet clouds that slide across the moon
    out.append(('sprite', 'cloud_thin_a', [cloud(130, 7, [(18, 4, 20, 3), (50, 3, 30, 3), (92, 4, 32, 3),
        (120, 4, 10, 2)], 'C0', 'S2', 'S1', base=5)], 0, 0))
    out.append(('sprite', 'cloud_thin_b', [cloud(150, 8, [(24, 4, 26, 3), (64, 4, 36, 4), (110, 4, 34, 3)],
        'C0', 'S3', 'S2', base=6)], 0, 0))
    out.append(('sprite', 'cloud_thin_c', [cloud(110, 6, [(20, 3, 22, 2), (56, 3, 30, 3), (92, 3, 18, 2)],
        'S5', 'S4', 'S3', base=4)], 0, 0))
    return out


if __name__ == '__main__':
    import artlib
    pals = artlib.load_palettes()
    items = [it[2][0] for it in export()]
    artlib.preview(items, pals['spring'], str(artlib.ROOT / 'shots' / 'clouds.png'), zoom=3, cols=3)
