"""NES-style colours: the shared backdrop plus four background and four sprite sub-palettes.

Every hex must be one of the kit's 2C02 master palette colours (palettes/nes.hex); `check()` stops
the render otherwise. A background tile pixel is an index 0-3: 0 is the shared backdrop, 1-3 pick from
its 16x16 block's sub-palette. A sprite pixel 0 is transparent, 1-3 pick from its sprite palette.
Recolour by swapping hexes for other master-palette entries; keep one role per sub-palette.
"""
BACKDROP = 'a4e4fc'                      # the sky, and index 0 of every background tile
BG = [
    ['3cbcfc', '6888fc', '0058f8'],      # 0 lower sky band, far strip, far strip shade
    ['004058', '008888', '58f898'],      # 1 ground: deep, mid, lit edge
    ['000000', '7c7c7c', 'bcbcbc'],      # 2 placeholder platform: outline, body, lit
    ['000000', '7c7c7c', 'fcfcfc'],      # 3 status bar: panel, frame, pips
]
SPRITES = [
    ['000000', 'ac7c00', 'f8b800'],      # 0 placeholder marker: outline, body, lit
]

def check(master):
    """master: the kit's 2C02 colours as lowercase hexes (screen.py reads them from tools/era.py)"""
    used = [BACKDROP] + [h for sub in BG + SPRITES for h in sub]
    off = sorted({h for h in used if h.lower() not in master})
    if off:
        raise SystemExit('not 2C02 master palette colours: ' + ', '.join(off))
    if len(BG) > 4 or len(SPRITES) > 4 or any(len(sub) != 3 for sub in BG + SPRITES):
        raise SystemExit('the NES has 4 background and 4 sprite sub-palettes of 3 colours each')
