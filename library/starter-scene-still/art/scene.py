#!/usr/bin/env python3
"""Starter Scene Still: a neutral sky-and-ground scaffold rendered as one still.

    python3 art/scene.py          writes out/still.png (4x) and out/palette.json

Everything drawn is a placeholder: a three-band sky, two flat blocks in it, flat ground with an
edge line, a foreground strip that keeps the bottom third in use, and one grey box with a marker.
Change the layout constants below, the colours in pal.py and the slot maps in sprites.py, then
draw your own subject in compose().
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
# canvas is a kit module: piece commands run with the kit's tools/ first on PYTHONPATH
import canvas  # pyright: ignore[reportMissingImports]
from pal import PALETTE
from sprites import BLOCK, MARKER, blit

W, H, SCALE = 320, 180, 4
HORIZON = 112                                 # first ground row
FOREGROUND = 153                              # top row of the foreground strip
SKY = [('S0', 0), ('S1', 40, 14), ('S2', 78, 14)]   # [slot, first row, dithered rows]
BLOCKS = [(52, 30), (214, 54)]                # flat blocks in the sky: top-left x, y
MARKER_AT = (160, HORIZON + 26)               # the box's anchor: base centre on the ground
OUT = pathlib.Path(__file__).resolve().parent.parent / 'out'

def compose():
    c = canvas.Canvas(W, H)
    c.bands(0, HORIZON, SKY)
    for x, y in BLOCKS:
        blit(c, BLOCK, x, y)
    # flat ground: an edge line, a mid tone and a deep tone with a dithered row between them
    c.bands(HORIZON, FOREGROUND, [('G0', HORIZON), ('G1', HORIZON + 1), ('G2', HORIZON + 14, 4)])
    blit(c, MARKER, *MARKER_AT)
    # a flat foreground strip with a lit edge
    c.rect(0, FOREGROUND, W, H, 'F0')
    c.hline(0, W - 1, FOREGROUND, 'F1')
    return c

def main():
    img = compose().image(PALETTE)
    OUT.mkdir(exist_ok=True)
    img.resize((W * SCALE, H * SCALE), 0).save(OUT / 'still.png')
    (OUT / 'palette.json').write_text(json.dumps(PALETTE, indent=1, sort_keys=True) + '\n')

if __name__ == '__main__':
    main()
