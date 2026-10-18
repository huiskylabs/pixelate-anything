#!/usr/bin/env python3
"""Starter Era NES: a neutral NES-style screen built the way the hardware builds one.

    python3 art/screen.py     writes out/screen.png (3x), out/palette.json (the colours declared in
                              nespal.py), out/bg.png (1x background alone, for the 16x16 block rule)
                              and out/oam.json (the hardware sprite boxes, for era.check_sprites)

The screen is the kit's `nes` preset, 256x224: the 224 lines an NTSC set shows of the 256x240
picture the console draws. It is a nametable of 32x28 tiles from tiles.py, an attribute table
that gives every 16x16 block one background sub-palette, and a short sprite list (OAM) drawn on
top. Everything is a placeholder: a status bar, a plain sky with a dithered lower band, a flat
far strip, flat ground, a foreground strip, one floating platform and one 16x16 marker sprite.
Edit nametable(), attributes() and OAM below, the tiles in tiles.py and the colours in nespal.py.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# era is a kit module: piece commands run with the kit's tools/ first on PYTHONPATH
import era  # noqa: E402  # pyright: ignore[reportMissingImports]
import nespal  # noqa: E402  # pyright: ignore[reportMissingImports]
from tiles import BG_TILES, SPRITE_TILES  # noqa: E402  # pyright: ignore[reportMissingImports]

COLS, ROWS, SCALE = 32, 28, 3
W, H = COLS * 8, ROWS * 8
OUT = HERE.parent / 'out'
PLATFORM = (20, 10, 6)                     # first column, top row, width in tiles
FOREGROUND = 24                            # tile row where the foreground strip starts

def nametable():
    """the tile name of every 8x8 cell, row by row"""
    rows = [['hud_panel'] * COLS for _ in range(3)] + [['hud_rule'] * COLS]
    rows[1][2:5] = ['hud_pip'] * 3
    rows[1][22:30] = ['hud_gauge_l'] + ['hud_gauge_m'] * 6 + ['hud_gauge_r']
    rows += [['blank'] * COLS for _ in range(10)]
    rows.append(['sky_step'] * COLS)
    rows.append(['sky_low'] * COLS)
    runs = (5, 3, 6, 4, 2, 7, 5)               # far strip heights alternate in uneven runs
    far, k = [], 0
    while len(far) < COLS:
        far += [('far_top_a', 'far_top_b')[k % 2]] * runs[k % len(runs)]
        k += 1
    rows.append(far[:COLS])
    rows.append(['far_fill'] * COLS)
    rows.append(['ground_top'] * COLS)
    rows.append(['ground_mid'] * COLS)
    rows += [['ground_deep'] * COLS for _ in range(FOREGROUND - len(rows))]
    rows.append(['fore_top'] * COLS)
    rows += [['fore_fill'] * COLS for _ in range(ROWS - len(rows))]
    c, r, w = PLATFORM
    rows[r][c:c + w] = ['plat_top'] + ['plat_top_mid'] * (w - 2) + ['plat_top_end']
    rows[r + 1][c:c + w] = ['plat_low'] + ['plat_low_mid'] * (w - 2) + ['plat_low_end']
    return rows

def attributes():
    """the background sub-palette (nespal.BG index) of every 16x16 block"""
    # status bar (block rows 0-1), sky, band and far strip (2-8), ground and foreground (9-13)
    table = [[3 if by < 2 else 1 if by >= 9 else 0] * (COLS // 2) for by in range(ROWS // 2)]
    c, r, w = PLATFORM
    for bx in range(c // 2, (c + w + 1) // 2):
        table[r // 2][bx] = 2
    return table

# hardware sprites: x, y, tile, sprite palette (a 16x16 marker standing on the ground row 144)
MARKER_AT = (56, 128)
OAM = [(MARKER_AT[0] + dx, MARKER_AT[1] + dy, name, 0)
       for dy, dx, name in ((0, 0, 'marker_tl'), (0, 8, 'marker_tr'), (8, 0, 'marker_bl'), (8, 8, 'marker_br'))]

def rgb(hexes):
    return np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in hexes], np.uint8)

def render():
    """(composited RGB, background-only RGB) arrays at 1x"""
    names, attr = nametable(), attributes()
    bg = np.zeros((H, W, 3), np.uint8)
    for ty in range(ROWS):
        for tx in range(COLS):
            idx = np.array(BG_TILES[names[ty][tx]])
            cols = rgb([nespal.BACKDROP] + nespal.BG[attr[ty // 2][tx // 2]])
            bg[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = cols[idx]
    screen = bg.copy()
    for x, y, name, pal in OAM:
        idx = np.array(SPRITE_TILES[name])
        cols = rgb(['000000'] + nespal.SPRITES[pal])
        view = screen[y:y + 8, x:x + 8]
        view[idx > 0] = cols[idx][idx > 0]
    return screen, bg

def main():
    nespal.check({''.join(f'{int(v):02x}' for v in c) for c in era.palette_rgb('nes')})
    screen, bg = render()
    OUT.mkdir(exist_ok=True)
    Image.fromarray(screen).resize((W * SCALE, H * SCALE), Image.Resampling.NEAREST).save(OUT / 'screen.png')
    Image.fromarray(bg).save(OUT / 'bg.png')
    hexes = [nespal.BACKDROP] + [h for sub in nespal.BG + nespal.SPRITES for h in sub]
    (OUT / 'palette.json').write_text(json.dumps(sorted({f'#{h}' for h in hexes}), indent=1) + '\n')
    (OUT / 'oam.json').write_text(json.dumps({'sprites': [[x, y, 8, 8] for x, y, _, _ in OAM]}) + '\n')

if __name__ == '__main__':
    main()
