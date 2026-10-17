#!/usr/bin/env python3
"""Render maps/mire.txt as one slot grid, then paint it with each palette.

usage: python3 maps/render_map.py [--frame K] [--gif]

The map is composed once as palette SLOTS (water, banks, moss, boardwalk, props in y order), so
day and night share every tile index and sprite frame; only the palette changes. Writes
  out/09-a@1x.png  out/09-a.png (4x, 1280x768)    day
  out/09-b@1x.png  out/09-b.png (4x, 1280x768)    glowing night
and with --gif out/09-a.gif / out/09-b.gif: 8 frames (water flows, idles cycle).
"""
import json, pathlib, sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import assets
from artlib import Grid
from PIL import Image

PACK = pathlib.Path(__file__).resolve().parent.parent
T = 16
DECK = {'-': None, '=': 'h_broken', '<': 'h_end_w', '>': 'h_end_e', '|': None, '^': 'v_end_n',
        'v': 'v_end_s', '+': 'landing'}
DECK_FRAMES = ['h_a', 'h_b', 'h_broken', 'h_end_w', 'h_end_e', 'v_a', 'v_b', 'v_end_n', 'v_end_s', 'landing']


def h(x, y, s):
    n = ((x * 73856093) ^ (y * 19349663) ^ (s * 83492791)) & 0xffffffff
    n ^= 0x9e3779b9
    n = ((n ^ (n >> 16)) * 0x85ebca6b) & 0xffffffff
    n = ((n ^ (n >> 13)) * 0xc2b2ae35) & 0xffffffff
    return (n ^ (n >> 16)) / 4294967296.0


def parse(path):
    corners, deck, props, sec = [], [], [], None
    for line in pathlib.Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line.strip() in ('corners:', 'deck:', 'props:'):
            sec = line.strip()[:-1]
            continue
        if line.startswith('tile:'):
            continue
        if sec == 'corners':
            corners.append(line.strip())
        elif sec == 'deck':
            deck.append(line.strip())
        elif sec == 'props':
            p = line.split()
            props.append((p[0], int(p[1]), int(p[2]), int(p[3]) if len(p) > 3 and p[3].isdigit() else 0,
                          'flip' in p[3:]))
    return corners, deck, props


def check_corners(corners):
    bad = []
    for y, row in enumerate(corners):
        for x, c in enumerate(row):
            if c == '#':
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < len(corners) and 0 <= xx < len(row) and corners[yy][xx] == '~':
                            bad.append((x, y))
    return sorted(set(bad))


def flipx(g):
    out = Grid(g.w, g.h)
    out.a = [r[::-1] for r in g.a]
    return out


def stamp(dst, g, ox, oy):
    for y in range(g.h):
        Y = y + oy
        if not 0 <= Y < dst.h:
            continue
        for x in range(g.w):
            v = g.a[y][x]
            X = x + ox
            if v is not None and 0 <= X < dst.w:
                dst.a[Y][X] = v


def compose(sprites, corners, deck, props, k=0):
    """the map as a slot Grid; k advances the water and the idles (for the GIF)"""
    S = {s['name']: s for s in sprites}
    rows, cols = len(corners) - 1, len(corners[0]) - 1
    g = Grid(cols * T, rows * T)
    lv = lambda x, y: {'~': 0, '.': 1, '#': 2}[corners[y][x]]
    for ty in range(rows):
        for tx in range(cols):
            c = [lv(tx, ty), lv(tx + 1, ty), lv(tx, ty + 1), lv(tx + 1, ty + 1)]
            q = h(tx, ty, 3)
            wv = 0 if q < 0.5 else 1 if q < 0.72 else 2 if q < 0.86 else 3
            if min(c) == 0:
                stamp(g, S['bog_water']['frames'][wv * 4 + (k + tx) % 4], tx * T, ty * T)
                if max(c) > 0:
                    idx = sum((1 if v > 0 else 0) << (3 - i) for i, v in enumerate(c))
                    bank = ('peat_bank', 'peat_bank_b', 'peat_bank_c')[int(h(tx, ty, 23) * 3)]
                    stamp(g, S[bank]['frames'][idx], tx * T, ty * T)
            else:
                idx = sum((1 if v > 1 else 0) << (3 - i) for i, v in enumerate(c))
                var = ('moss_peat', 'moss_peat_b', 'moss_peat_c')[int(h(tx, ty, 11) * 3)]
                stamp(g, S[var]['frames'][idx], tx * T, ty * T)
    bw = S['boardwalk']['frames']
    for ty, row in enumerate(deck):
        for tx, ch in enumerate(row):
            if ch == '.':
                continue
            if ch == '-':
                name = 'h_a' if (tx * 5 + ty) % 3 else 'h_b'
            elif ch == '|':
                name = 'v_a' if (tx + ty) % 2 else 'v_b'
            else:
                name = DECK[ch]
            stamp(g, bw[DECK_FRAMES.index(name)], tx * T, ty * T)
    for name, x, y, fi, fl in sorted(props, key=lambda p: p[2]):
        if name not in S:
            print('map: unknown prop', name)
            continue
        s = S[name]
        n = len(s['frames'])
        f = s['frames'][(fi + (k if n > 1 else 0)) % n]
        ax, ay = s['anchor']
        if fl:
            f = flipx(f)
            ax = f.w - 1 - ax
        stamp(g, f, x - ax, y - ay)
    return g


def paint(g, pal, scale=1):
    im = Image.new('RGB', (g.w, g.h))
    px = im.load()
    rgb = {k: tuple(int(v.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) for k, v in pal.items()}
    for y in range(g.h):
        for x in range(g.w):
            v = g.a[y][x]
            px[x, y] = rgb[v] if v is not None else (255, 0, 255)
    return im.resize((g.w * scale, g.h * scale), Image.NEAREST) if scale > 1 else im


def main(a):
    k = int(a[a.index('--frame') + 1]) if '--frame' in a else 0
    meta, day, sprites = assets.load_pack(PACK)
    night = json.loads((PACK / 'palette-night.json').read_text())
    assert set(day) == set(night), 'palettes must share slot names'
    corners, deck, props = parse(PACK / 'maps' / 'mire.txt')
    bad = check_corners(corners)
    if bad:
        print('moss corners touching water (fix the map):', bad)
    g = compose(sprites, corners, deck, props, k)
    out = PACK / 'out'
    out.mkdir(exist_ok=True)
    for tag, pal in (('a', day), ('b', night)):
        paint(g, pal).save(out / ('09-%s@1x.png' % tag))
        paint(g, pal, 4).save(out / ('09-%s.png' % tag))
    print('wrote out/09-a.png, out/09-b.png (1280x768) and their @1x (320x192)')
    if '--gif' in a:
        for tag, pal in (('a', day), ('b', night)):
            frames = [paint(compose(sprites, corners, deck, props, i), pal, 3) for i in range(8)]
            frames[0].save(out / ('09-%s.gif' % tag), save_all=True, append_images=frames[1:],
                           duration=250, loop=0, optimize=False)
        print('wrote out/09-a.gif, out/09-b.gif')


if __name__ == '__main__':
    main(sys.argv[1:])
