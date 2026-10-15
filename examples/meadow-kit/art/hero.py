"""The hero: one hand-drawn 16x16 front view, animated by moving parts of it.

idle (2 frames): the head and arms sink a pixel on the out-breath.
walk (4 frames): contact, left foot up with the body risen a pixel, contact, right foot up.
Deriving frames from one drawing keeps every frame consistent; fix the base and all follow.
"""
from artlib import Grid

KEY = {'o': 'ol', 'H': 'hair3', 'h': 'hair2', 'S': 'skin3', 's': 'skin2',
       'T': 'tunic3', 't': 'tunic2', 'P': 'pants2', 'p': 'pants1', 'B': 'boot2', 'b': 'boot1'}
BASE = """
................
....oooooooo....
...oHHHHHHHHo...
...oHHHHHHhho...
...ohSSSSSsho...
...ohSoSSosho...
...ohSSSSSsho...
....osSSSSso....
.....oossoo.....
...ooTTTTttoo...
..oTTTTTTtttto..
..oSTTTTttttSo..
...oPPPPppppo...
...oPPPoopppo...
...oBBo..oBbo...
...oooo..oooo...
"""

def base():
    g = Grid(16, 16)
    g.stamp(BASE, KEY)
    return g

def shifted_rows(g, rows, dy):
    """copy of g with the given rows moved by dy (rows vacated become transparent)"""
    out = Grid(g.w, g.h)
    moved = {y + dy: g.a[y][:] for y in rows}
    for y in range(g.h):
        if y in moved:
            out.a[y] = moved[y]
        elif y in rows:
            out.a[y] = [None] * g.w
        else:
            out.a[y] = g.a[y][:]
    return out

def lift_foot(g, left):
    """raise one boot a pixel: its boot row moves up over the pants, its sole row clears"""
    out = Grid(g.w, g.h)
    out.a = [r[:] for r in g.a]
    xs = range(3, 7) if left else range(9, 13)
    for x in xs:
        out.a[13][x] = g.a[14][x]
        out.a[14][x] = g.a[15][x]
        out.a[15][x] = None
    return out

def body_up(g):
    """rows 1-12 rise a pixel; the pants row repeats so the legs stretch"""
    out = Grid(g.w, g.h)
    out.a = [r[:] for r in g.a]
    for y in range(0, 12):
        out.a[y] = g.a[y + 1][:]
    return out

def export():
    b = base()
    breathe = shifted_rows(b, range(1, 12), 1)
    breathe.a[12] = b.a[11][:]           # hands rest on the hips
    walk = [b, body_up(lift_foot(b, True)), b, body_up(lift_foot(b, False))]
    return [
        ('sprite', 'hero_idle', [b, breathe], 8, 15, {'durations': [600, 450], 'tags': {'idle': (0, 1)}}),
        ('sprite', 'hero_walk', walk, 8, 15, {'fps': 8, 'tags': {'walk': (0, 3)}}),
    ]
