"""8x8 placeholder tiles as 2-bit index rows: '0' backdrop (transparent in a sprite), '1'-'3' the
colours of the tile's sub-palette (nespal.py). Each pattern is one entry of a pattern table.

Replace these with your own tiles; keep each 8 rows of 8 digits. The background and the sprites
use separate tables, as on the hardware.
"""

def tile(rows):
    rows = rows.split()
    if len(rows) != 8 or any(len(r) != 8 or set(r) - set('0123') for r in rows):
        raise ValueError('a tile is 8 rows of 8 digits 0-3')
    return [[int(ch) for ch in r] for r in rows]

BG_TILES = {
    'blank': tile('00000000 ' * 8),
    # sky: a 2-row checker step from the backdrop into the lower band (guides/eras.md)
    'sky_step': tile('00000000 00000000 00000000 00000000 10101010 01010101 11111111 11111111'),
    'sky_low': tile('11111111 ' * 8),
    # a flat far strip in two heights, with one shade row
    'far_top_a': tile('11111111 11111111 11111111 22222222 22222222 22222222 22222222 22222222'),
    'far_top_b': tile('11111111 11111111 11111111 11111111 11111111 22222222 22222222 22222222'),
    'far_fill': tile('22222222 22222222 22222222 22222222 23232323 32323232 33333333 33333333'),
    # flat ground: a lit edge, then a mid tone stepping into a deep tone
    'ground_top': tile('33333333 22222222 22222222 22222222 22222222 22222222 22222222 22222222'),
    'ground_mid': tile('22222222 22222222 22222222 22222222 21212121 12121212 11111111 11111111'),
    'ground_deep': tile('11111111 ' * 8),
    # a flat foreground strip with a lit edge keeps the bottom of the screen in use
    'fore_top': tile('33333333 22222222 22222222 22222222 22222222 22222222 22222222 22222222'),
    'fore_fill': tile('22222222 ' * 8),
    # a placeholder platform: lit top, body, outline
    'plat_top': tile('11111111 13333333 13333333 12222222 12222222 12222222 12222222 12222222'),
    'plat_low': tile('12222222 12222222 12222222 12222222 12222222 12222222 11111111 11111111'),
    'plat_top_end': tile('11111111 33333331 33333331 22222221 22222221 22222221 22222221 22222221'),
    'plat_low_end': tile('22222221 22222221 22222221 22222221 22222221 22222221 11111111 11111111'),
    'plat_top_mid': tile('11111111 33333333 33333333 22222222 22222222 22222222 22222222 22222222'),
    'plat_low_mid': tile('22222222 22222222 22222222 22222222 22222222 22222222 11111111 11111111'),
    # status bar: a framed panel, placeholder pips and an empty gauge
    'hud_panel': tile('11111111 ' * 8),
    'hud_rule': tile('11111111 11111111 11111111 22222222 11111111 11111111 11111111 11111111'),
    'hud_pip': tile('11111111 11333311 11333311 11333311 11333311 11111111 11111111 11111111'),
    'hud_gauge_l': tile('11111111 11222222 11211111 11211111 11211111 11222222 11111111 11111111'),
    'hud_gauge_m': tile('11111111 22222222 11111111 11111111 11111111 22222222 11111111 11111111'),
    'hud_gauge_r': tile('11111111 22222211 11111211 11111211 11111211 22222211 11111111 11111111'),
}

# a 16x16 placeholder marker as four hardware sprites (top-left, top-right, bottom-left, bottom-right)
SPRITE_TILES = {
    'marker_tl': tile('11111111 13333333 13333333 13322222 13322222 13322222 13322222 13322222'),
    'marker_tr': tile('11111111 33333331 22222221 22222221 22222221 22222221 22222221 22222221'),
    'marker_bl': tile('13322222 13322222 13322222 13322222 13322222 13322222 12222222 11111111'),
    'marker_br': tile('22222221 22222221 22222221 22222221 22222221 22222221 22222221 11111111'),
}
