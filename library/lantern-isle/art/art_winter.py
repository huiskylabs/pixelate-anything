"""Winter overlays: snow laid over the roof, sills, dock, boat, lantern and
shore stones, plus icicles placed by hand along the eaves."""
from artlib import Grid, bayer
import art_cottage, art_props, art_island

ROOF = {'F0', 'F1', 'F2', 'F3'}

def roof_snow():
    c = art_cottage.build()
    s = Grid(c.w, c.h + 2)          # two extra rows on top for snow above the chimney cap
    def S(x, y, v):
        s.set(x, y + 2, v)
    for x in range(c.w):
        # topmost painted pixel in this column above the wall line
        top = None
        for y in range(0, 34):
            if c.get(x, y) is not None:
                top = y; break
        if top is None:
            continue
        S(x, top - 1, 'N2')
        if 14 <= x <= 67 and top <= 11:
            S(x, top - 2, 'N1' if (x % 7) else None)     # a soft drift along the ridge
    for y in range(0, 34):
        for x in range(c.w):
            v = c.get(x, y)
            if v not in ROOF:
                continue
            # main roof and gable edges become snow; course shadows stay as soft lines
            if v == 'F0':
                S(x, y, 'N0')
            elif v == 'F3':
                S(x, y, 'N3')
            else:
                S(x, y, 'N1' if y > 14 else 'N2')
    # snow lip curling over the eave
    for x in range(3, 79):
        if x % 9 in (2, 3, 4, 5) or x % 13 == 0:
            S(x, 33, 'N1')
            if x % 9 in (3, 4):
                S(x, 34, 'N0')
    # porch roof and window sills
    for x in range(30, 53):
        if c.get(x, 36) in ROOF:
            S(x, 36, 'N3' if x % 5 else 'N2')
        if c.get(x, 37) in ROOF:
            S(x, 37, 'N1')
        S(x, 35, 'N2' if 30 < x < 52 else None)
    for x0 in (12, 55):
        for x in range(x0, x0 + 15):
            if c.get(x, 49) is not None:
                S(x, 49, 'N2')
    # chimney cap
    for x in range(9, 20):
        S(x, -1, 'N2' if x in (9, 19) else 'N3')
        if c.get(x, 1) is not None and c.get(x, 1) != 'K0':
            S(x, 1, 'N2')
    # clear stray None writes
    return s

ICICLES = [(8, 2), (12, 3), (17, 1), (21, 2), (27, 1), (29, 3), (34, 1), (53, 2), (57, 1), (60, 3),
           (64, 2), (68, 1), (71, 3), (75, 2)]
PORCH_ICICLES = [(32, 1), (37, 2), (44, 1), (48, 2)]
def icicles():
    s = Grid(82, 46)
    for (x, n) in ICICLES:
        for i in range(n):
            s.set(x, 34 + i, 'C2' if i == n - 1 else 'C1')
    for (x, n) in PORCH_ICICLES:
        for i in range(n):
            s.set(x, 39 + i, 'C2' if i == n - 1 else 'C1')
    return s

def dock_snow(d=None):
    d = d or art_props.dock()
    s = Grid(d.w, d.h)
    for x in range(d.w):
        v = d.get(x, 0)
        if v in ('B1', 'B2', 'B3', 'B0'):
            s.set(x, 0, 'N2' if x % 11 else 'N3')
            if d.get(x, 1) in ('B1', 'B2') and x % 3:
                s.set(x, 1, 'N1')
        if d.get(x, 3) in ('B2', 'B3') and x % 5 == 0:
            s.set(x, 3, 'N1')
    return s

def boat_snow():
    b = art_props.boat()
    s = Grid(b.w, b.h)
    for x in range(b.w):
        for y in range(b.h):
            if b.get(x, y) in ('K1',) or (b.get(x, y) in ('B2', 'B3') and y <= 4):
                s.set(x, y, 'N2' if y < 4 else 'N1')
        if b.get(x, 4) is not None and 3 < x < 38:
            s.set(x, 3, 'N3' if x % 6 else 'N2')
    return s

def lantern_snow():
    s = Grid(12, 30)
    for x in range(1, 10):
        s.set(x, 0, 'N2')
    for x in range(6, 10):
        s.set(x, 4, 'N3')
    s.set(0, 0, 'N3'); s.set(1, 0, 'N3')
    return s

def island_snow():
    g = art_island.build()
    c, ox, oy = g.crop()
    s = Grid(c.w, c.h)
    for y in range(1, c.h):
        for x in range(c.w):
            v = c.get(x, y)
            if v in ('R3', 'R2') and c.get(x, y - 1) in (None, 'K0', 'K1', 'B1', 'B0', 'R0'):
                s.set(x, y, 'N2' if v == 'R3' else 'N1')
    return s

def export():
    return [
        ('sprite', 'roof_snow', [roof_snow()], 0, 2),
        ('sprite', 'icicles', [icicles()], 0, 0),
        ('sprite', 'dock_snow', [dock_snow()], 0, 0),
        ('sprite', 'dock_short_snow', [dock_snow(art_props.dock_short())], 0, 0),
        ('sprite', 'boat_snow', [boat_snow()], 0, 0),
        ('sprite', 'lantern_snow', [lantern_snow()], 1, 29),
        ('sprite', 'island_snow', [island_snow()], 0, 0),
    ]

if __name__ == '__main__':
    import artlib
    pals = artlib.load_palettes()
    c = art_cottage.build()
    rs = roof_snow()
    comp = Grid(c.w, c.h + 2)
    comp.paste(c, 0, 2); comp.paste(rs, 0, 0)
    ic = icicles(); comp.paste(ic, 0, 2)
    artlib.preview([comp], pals['winter'], str(artlib.ROOT / 'shots' / 'cottage_winter_snow.png'), zoom=6)
