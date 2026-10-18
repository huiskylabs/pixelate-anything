"""One little scene (a cottage, a tree, a well, a pond, a fence) rendered in the five projections
pixel art uses, from the same 3D description: tools/iso.py CAMERAS. Pick by game type:
side view for platformers, 3/4 top-down for RPGs, 2:1 isometric for strategy and dioramas,
oblique for building-heavy worlds, military for a steep graphic plan view."""
import sys, pathlib
import numpy as np
from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
sys.path.insert(0, str(KIT / 'library' / 'san-francisco' / 'art'))
import artlib, colorlib as cl
from iso import Iso, windows, hash2
import palettes

PAL = palettes.day()
TREE = """
..oooo..
.oTTTto.
oTTTtTto
oTtTtttO
otttttdo
.otdddo.
..oobo..
...obo..
"""
def tree_grid():
    key = {'o': 'ol', 'T': 'tree4', 't': 'tree3', 'd': 'tree2', 'O': 'tree2', 'b': 'earth1'}
    rows = TREE.strip().splitlines()
    g = artlib.Grid(len(rows[0]), len(rows))
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c != '.': g.set(i, j, key[c])
    return g

def ground(u, v, t, face_step=3, **_):
    if 30 <= u < 44 and 6 <= v < 16:
        return 'water3' if (int(u) + int(v) * 3) % 11 else 'water4'
    if 17 <= u < 21 and v >= 24:
        return 'walk3'
    return 'grass3' if hash2(int(u), int(v), 2) > 0.1 else 'grass2'

def side_face(u, v, t, face_step=2, **_):
    return 'earth%d' % face_step if v < 4.5 else 'grass%d' % face_step

def scene(s):
    s.box(0, 0, -6, 48, 48, 6, 'earth', top=ground, left=side_face, right=side_face)
    win = windows('cream', 'glass', every=(4, 6), size=(2, 3), margin=(2, 3))
    s.box(10, 12, 0, 20, 12, 14, 'cream', left=win, right=win)
    s.gable(10, 12, 14, 20, 12, 9, 'brick', along='x')
    s.box(24, 14, 18, 3, 3, 9, 'brick')                                       # chimney
    s.box(18, 23.5, 0, 4, 0.5, 9, 'earth', top='earth3', left='earth2')       # door
    s.cylinder(38, 34, 0, 3, 5, 'roof')                                       # well
    s.box(35, 33.5, 5, 0.6, 1, 7, 'earth', lines=False); s.box(40.4, 33.5, 5, 0.6, 1, 7, 'earth', lines=False)
    s.box(34.5, 32, 12, 7, 4, 2, 'brick')
    for x in range(2, 46, 4):                                                 # fence
        s.box(x, 45, 0, 1, 1, 5, 'earth', top='earth4')
    s.box(2, 45.2, 3, 44, 0.6, 1, 'earth', top='earth4', lines=False)
    for tx, ty in ((6, 8), (40, 22), (5, 36)):
        s.sprite(tree_grid(), tx, ty, 0)

CAMS = [('side', 'side view', 'platformers'), ('topdown', '3/4 top-down', 'RPGs, town builders'),
        ('iso', '2:1 isometric', 'strategy, dioramas'), ('oblique', 'oblique', 'building-heavy worlds'),
        ('military', 'military 45', 'graphic plan views')]

def render(cam, depth=1.0):
    sc = 1 if cam == 'iso' else 2
    probe = Iso(1, 1, camera=cam, depth=depth, scale=sc)
    pts = [probe.to_screen(x, y, z) for x in (0, 48) for y in (0, 48) for z in (-6, 40)]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    W, H = int(x1 - x0) + 12, int(y1 - y0) + 12
    s = Iso(W, H, origin=(6 - x0, 6 - y0), slots=PAL.keys(), camera=cam, depth=depth, scale=sc)
    scene(s)
    s.cast_shadows(sun=(-0.6, 0.45, 0.7))
    g = s.render()
    im = Image.new('RGB', (W, H), cl.hex_to_rgb('#2a2836'))
    px = im.load()
    for y in range(H):
        for x in range(W):
            v = g.a[y][x]
            if v is not None:
                px[x, y] = cl.hex_to_rgb(PAL[v])
    return im

def sheet(scale=2):
    ims = [(render(c, 0.7 if c == 'topdown' else 1.0), name, use) for c, name, use in CAMS]
    pad, lab = 10, 34
    H = max(i.height for i, _, _ in ims) * scale + lab + pad * 2
    W = sum(i.width * scale + pad for i, _, _ in ims) + pad
    out = Image.new('RGB', (W, H), cl.hex_to_rgb('#2a2836'))
    d = ImageDraw.Draw(out)
    x = pad
    for im, name, use in ims:
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        out.paste(big, (x, H - pad - big.height))
        d.text((x + 4, pad), name, fill=(240, 236, 226)); d.text((x + 4, pad + 14), use, fill=(160, 160, 176))
        x += big.width + pad
    return out

def export():
    return [{'name': 'projections', 'frames': [], 'images': [sheet(1)], 'anchor': (0, 0), 'kind': 'scene'}]

if __name__ == '__main__':
    sheet(2).save(sys.argv[1] if len(sys.argv) > 1 else '/tmp/projections.png')
