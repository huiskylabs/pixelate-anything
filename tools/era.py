#!/usr/bin/env python3
"""Console-era presets: the hardware limits that gave classic pixel art its look, and a checker
that holds an image to them (or forces it into them).

usage: era.py IMAGE --era nes|gameboy|snes|genesis|gba|pico-8|neogeo [-o OUT] [--scale 4]
              [--layer bg|full|sprite|fix] [--tiles]
       era.py --list

Without -o it reports. With -o it also writes OUT (the image made legal) and OUT@Nx.png.
--tiles also counts the unique background tiles (run it on the background-only render).
Sprite limits need the sprite boxes, so they are checked from Python: era.check_sprites(boxes, 'nes').

What each preset holds you to:
  nes      256x224, the 2C02 master palette (54 colours), at most 25 on screen;
           backgrounds: every 16x16 attribute block uses one 3-colour sub-palette plus the shared
           backdrop (4 colours); sprites: 3 colours + transparent.
  gameboy  160x144, 4 shades of green, everything.
  snes     256x224, 15-bit colour (5 bits per channel), 256 on screen, 16 colours per 8x8 tile.
  genesis  320x224, 9-bit colour (3 bits per channel), 61 on screen, 16 per 8x8 tile.
  gba      240x160, 15-bit colour, 256 on screen, 16 per 8x8 tile.
  pico-8   128x128, its 16 colours.
  neogeo   304x224, 15-bit colour (5 bits per channel; the hardware's extra dark bit is ignored),
           up to 4096 on screen from many palettes, no blending. Check each layer on its own:
           --layer sprite (actors, FX and backgrounds are all sprites): every 16x16 tile uses at
           most 15 colours plus transparent; --layer fix (the HUD): 8x8 tiles, 15 colours each.
Sprites and tiles (ERAS[era]['sprite_line'], 'sprite_total', 'bg_tiles'): NES 8 per scanline, 64 in
all, 256 unique 8x8 background tiles; Game Boy 10 per line, 40 in all, 256 tiles; SNES 32 / 128 /
1024 per layer; Mega Drive 20 / 80 / 2048 (the VRAM ceiling); GBA - / 128 / 1024; PICO-8 256 tiles;
Neo Geo 96 / 380 (16 px wide sprite columns).
The names describe hardware limits only; the art you make with them should be your own.
"""
import pathlib, sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl

ERAS = {
    'nes':     dict(name='NES-style 8-bit', size=(256, 224), palette='nes', max_colors=25, block=16, block_colors=4,
                    shared_backdrop=True, sprite_colors=3),
    'gameboy': dict(name='Game Boy-style', size=(160, 144), palette='gameboy', max_colors=4, block=8, block_colors=4),
    'snes':    dict(name='SNES-style 16-bit', size=(256, 224), bits=5, max_colors=256, block=8, block_colors=16),
    'genesis': dict(name='Mega Drive-style 16-bit', size=(320, 224), bits=3, max_colors=61, block=8, block_colors=16),
    'gba':     dict(name='GBA-style', size=(240, 160), bits=5, max_colors=256, block=8, block_colors=16),
    'pico-8':  dict(name='PICO-8', size=(128, 128), palette='pico-8', max_colors=16),
    'neogeo':  dict(name='Neo Geo-style arcade', size=(304, 224), bits=5, max_colors=4096, block=16, block_colors=15,
                    fix_block=8, layers={'sprite': (16, 15), 'bg': (16, 15), 'fix': (8, 15)}),
}

# Sprite and tile limits, added per era (None: the hardware has no such limit, or it is not a count).
#   sprite_line   hardware sprites that can share one scanline (more and the rest drop out: flicker)
#   sprite_total  hardware sprites on screen at once (OAM entries)
#   sprite_size   the largest single hardware sprite (w, h); a bigger figure is cut into several
#   sprite_cell   the size step a hardware sprite comes in (a 16x20 Mega Drive figure is one 16x24 sprite)
#   tile          background tile size; bg_tiles: unique background tiles the hardware can hold at once
#   tile_flips    the tile map can mirror a tile, so a tile and its mirror cost one
_LIMITS = {
    'nes':     dict(sprite_line=8,    sprite_total=64,   sprite_size=(8, 8),    sprite_cell=8,  tile=8,  bg_tiles=256,
                    tile_flips=False),
    'gameboy': dict(sprite_line=10,   sprite_total=40,   sprite_size=(8, 8),    sprite_cell=8,  tile=8,  bg_tiles=256,
                    tile_flips=False),
    'snes':    dict(sprite_line=32,   sprite_total=128,  sprite_size=(64, 64),  sprite_cell=8,  tile=8,  bg_tiles=1024,
                    tile_flips=True),
    'genesis': dict(sprite_line=20,   sprite_total=80,   sprite_size=(32, 32),  sprite_cell=8,  tile=8,  bg_tiles=2048,
                    tile_flips=True),
    'gba':     dict(sprite_line=None, sprite_total=128,  sprite_size=(64, 64),  sprite_cell=8,  tile=8,  bg_tiles=1024,
                    tile_flips=True),
    'pico-8':  dict(sprite_line=None, sprite_total=None, sprite_size=(8, 8),    sprite_cell=8,  tile=8,  bg_tiles=256,
                    tile_flips=False),
    'neogeo':  dict(sprite_line=96,   sprite_total=380,  sprite_size=(16, 512), sprite_cell=16, tile=16, bg_tiles=None,
                    tile_flips=True),
}
for _k, _v in _LIMITS.items():
    for _f, _x in _v.items():
        ERAS[_k].setdefault(_f, _x)

def _block_rule(e, layer):
    """(block size, colours per block) for a layer, or None when the layer has no block rule"""
    if layer in e.get('layers', {}):
        return e['layers'][layer]
    if layer == 'bg' and e.get('block'):
        return e['block'], e['block_colors']
    return None

def _rgb(img):
    return np.asarray(img.convert('RGBA'))

def palette_rgb(era):
    e = ERAS[era]
    if 'palette' in e:
        return np.array([cl.hex_to_rgb(h) for h in cl.palette_list(cl.load_palette(e['palette']))], float)
    return None

def check(img, era, layer='full', sprites=None, tiles=False):
    """problems with this image under the era's rules (layer 'bg' also applies the
    per-block rule; sprites over a background are exempt from it). sprites: the frame's sprite boxes
    (see hw_sprites) adds check_sprites; tiles=True (or 'pattern') adds check_tiles on this image"""
    e = ERAS[era]
    a = _rgb(img)
    opaque = a[..., 3] >= 128
    rgb = a[..., :3].reshape(-1, 3)[opaque.ravel()]
    issues = []
    W, H = img.size
    if (W, H) != e['size']:
        issues.append('size %dx%d, the %s screen is %dx%d' % (W, H, e['name'], *e['size']))
    cols = np.unique(rgb, axis=0) if len(rgb) else np.zeros((0, 3))
    if len(cols) > e['max_colors']:
        issues.append('%d colours on screen, the limit is %d' % (len(cols), e['max_colors']))
    pal = palette_rgb(era)
    if pal is not None and len(cols):
        off = [c for c in cols if not (np.abs(pal - c).sum(1) == 0).any()]
        if off:
            issues.append('%d colours outside the %s palette' % (len(off), e['name']))
    if 'bits' in e and len(cols):
        step = 255 / (2 ** e['bits'] - 1)
        off = int((np.round(np.round(cols / step) * step) != cols).any(1).sum())   # what enforce's snap gives
        if off:
            issues.append('%d colours not on the %d-bit-per-channel grid' % (off, e['bits']))
    rule = _block_rule(e, layer)
    if rule:
        b, lim = rule
        bad = 0
        backdrop = None
        if e.get('shared_backdrop') and len(rgb):
            u, c = np.unique(rgb, axis=0, return_counts=True); backdrop = tuple(u[c.argmax()])
        for y in range(0, H, b):
            for x in range(0, W, b):
                blk = a[y:y + b, x:x + b]
                m = blk[..., 3] >= 128
                cs = {tuple(v) for v in blk[..., :3][m]}
                if backdrop is not None:
                    cs.add(backdrop)
                if len(cs) > lim:
                    bad += 1
        if bad:
            issues.append('%d of %d %dx%d blocks use more than %d colours' % (bad, ((W + b - 1) // b) * ((H + b - 1) // b), b, b, lim))
    if sprites is not None:
        issues += check_sprites(sprites, era)[0]
    if tiles:
        issues += check_tiles(img, era, by='pattern' if tiles == 'pattern' else 'colour')[0]
    return issues, len(cols)

def enforce(img, era, layer='full'):
    """the image made legal: snapped to the palette or bit depth, cut to the colour limits"""
    e = ERAS[era]
    a = _rgb(img).copy()
    rgb = a[..., :3].astype(float)
    pal = palette_rgb(era)
    if pal is not None:
        lab = cl.rgb_to_oklab(rgb.reshape(-1, 3)); plab = cl.rgb_to_oklab(pal)
        rgb = pal[cl.nearest(lab, plab)].reshape(rgb.shape)
    elif 'bits' in e:
        step = 255 / (2 ** e['bits'] - 1)
        rgb = np.round(np.round(rgb / step) * step)
    a[..., :3] = rgb.astype(np.uint8)
    opaque = a[..., 3] >= 128
    def remap(region, keep):
        flat = region[..., :3].reshape(-1, 3).astype(float)
        k = np.array(keep, float)
        lab, klab = cl.rgb_to_oklab(flat), cl.rgb_to_oklab(k)
        step = max(256, 4000000 // max(1, len(k)))          # bounded memory for 4096-colour eras
        idx = np.concatenate([cl.nearest(lab[i:i + step], klab) for i in range(0, len(lab), step)]) if len(lab) else np.zeros(0, int)
        region[..., :3] = k[idx].reshape(region[..., :3].shape).astype(np.uint8)
    used, counts = np.unique(a[..., :3][opaque], axis=0, return_counts=True)
    if len(used) > e['max_colors']:                  # merge the rarest colours into their nearest kept one
        keep = used[np.argsort(-counts)[:e['max_colors']]]
        remap(a, keep)
    rule = _block_rule(e, layer)
    if rule:
        b, lim = rule
        used, counts = np.unique(a[..., :3][opaque], axis=0, return_counts=True)
        backdrop = tuple(used[counts.argmax()]) if e.get('shared_backdrop') and len(used) else None
        H, W = a.shape[:2]
        for y in range(0, H, b):
            for x in range(0, W, b):
                blk = a[y:y + b, x:x + b]
                m = blk[..., 3] >= 128 if layer in e.get('layers', {}) else np.ones(blk.shape[:2], bool)
                if not m.any(): continue
                u, c = np.unique(blk[..., :3][m].reshape(-1, 3), axis=0, return_counts=True)
                order = [tuple(v) for v in u[np.argsort(-c)]]
                keep = ([backdrop] if backdrop else []) + [v for v in order if v != backdrop]
                if len(set(keep)) > lim:
                    remap(blk, keep[:lim])
    return Image.fromarray(a, 'RGBA')

# ---------------------------------------------------------------- sprites per scanline, sprite total, unique tiles
def _mask(m):
    """a sprite's opaque mask from a bool/alpha array, an RGBA array or a PIL image"""
    if isinstance(m, Image.Image):
        m = np.asarray(m.convert('RGBA'))
    m = np.asarray(m)
    if m.ndim == 3:
        return m[..., 3] >= 128 if m.shape[2] == 4 else m.any(2)
    return m >= 128 if m.dtype == np.uint8 else m.astype(bool)

def hw_sprites(boxes, era='nes', sprite_size=None, height=None):
    """the hardware sprites a set of figures costs, learnt from the NES/Game Boy OAM (a 16x24 hero is
    2 x 3 sprites of 8x8): each box cut into sprites of at most sprite_size, each sprite rounded up to
    the era's sprite_cell. A box is (x, y, w, h) or (x, y, mask) (bool/alpha/RGBA array or PIL image);
    with a mask, cuts that hold no opaque pixel are not spent. Only sprites that touch the screen rows
    0..height-1 count (height: the era's screen). -> [(x, y, w, h)] in screen px"""
    e = ERAS[era]
    sw, sh = sprite_size or e.get('sprite_size') or (8, 8)
    cell = e.get('sprite_cell') or 8
    H = e['size'][1] if height is None else height
    up = lambda v: -(-v // cell) * cell
    out = []
    for b in boxes:
        if len(b) == 3:
            x, y, m = b; m = _mask(m); h, w = m.shape
        else:
            x, y, w, h = b; m = None
        x, y, w, h = int(x), int(y), int(w), int(h)
        for oy in range(0, h, sh):
            for ox in range(0, w, sw):
                cw, ch = min(sw, w - ox), min(sh, h - oy)
                if m is not None:
                    cut = m[oy:oy + ch, ox:ox + cw]
                    if not cut.any():
                        continue
                    ys = np.nonzero(cut.any(1))[0]             # a sprite starts at its first used row
                    oy2, ch = oy + int(ys[0]), int(ys[-1] - ys[0] + 1)
                else:
                    oy2 = oy
                r = (x + ox, y + oy2, up(cw), up(ch))
                if r[1] + r[3] > 0 and r[1] < H:
                    out.append(r)
    return out

def scanline_counts(boxes, era='nes', sprite_size=None, height=None):
    """hardware sprites on every screen row, learnt from the NES's 8-sprites-per-line rule (the 9th drops
    out and flickers). boxes as in hw_sprites. -> int32 array of the screen height"""
    H = ERAS[era]['size'][1] if height is None else height
    n = np.zeros(H, np.int32)
    for x, y, w, h in hw_sprites(boxes, era, sprite_size, H):
        n[max(0, y):max(0, min(H, y + h))] += 1
    return n

def check_sprites(boxes, era='nes', per_line=None, total=None, sprite_size=None, height=None):
    """problems with a frame's sprites under the era's sprite limits, learnt from the NES (8 per scanline,
    64 in all) and Game Boy (10 per line, 40 in all). per_line / total override the era's sprite_line /
    sprite_total (None keeps the era's; the era's None means no limit). boxes as in hw_sprites.
    -> (issues, number of hardware sprites)"""
    e = ERAS[era]
    per_line = e.get('sprite_line') if per_line is None else per_line
    total = e.get('sprite_total') if total is None else total
    spr = hw_sprites(boxes, era, sprite_size, height)
    issues = []
    if total is not None and len(spr) > total:
        issues.append('%d hardware sprites on screen, the limit is %d' % (len(spr), total))
    if per_line is not None:
        n = scanline_counts(boxes, era, sprite_size, height)
        over = np.nonzero(n > per_line)[0]
        if len(over):
            issues.append('%d scanlines carry more than %d sprites (worst: %d on row %d)' % (
                len(over), per_line, int(n.max()), int(n.argmax())))
    return issues, len(spr)

def _tile_keys(img, tile, flips, by, backdrop):
    """one hashable key per tile (row-major) of an image, RGBA array or 2D slot grid"""
    a = np.asarray(img.convert('RGBA')) if isinstance(img, Image.Image) else np.asarray(img)
    grid = a.ndim == 2
    if not grid:
        a = a if a.shape[2] == 4 else np.concatenate([a, np.full(a.shape[:2] + (1,), 255, a.dtype)], 2)
        a = np.where((a[..., 3:] >= 128), a, 0).astype(np.uint8)          # hidden rgb never makes a new tile
        a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    H, W = a.shape[:2]
    ph, pw = -H % tile, -W % tile
    if ph or pw:
        pad = ((0, ph), (0, pw)) + (((0, 0),) if not grid else ())
        a = np.pad(a, pad, constant_values=(0 if a.dtype != object else ''))
    if by == 'pattern' and not grid:
        lum = a[..., 0].astype(np.int64) * 299 + a[..., 1].astype(np.int64) * 587 + a[..., 2].astype(np.int64) * 114
        rgb = (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2]
        empty = a[..., 3] == 0
        if backdrop is not None:
            empty = empty | (rgb == ((backdrop[0] << 16) | (backdrop[1] << 8) | backdrop[2]))
    keys = []
    for ty in range(0, a.shape[0], tile):
        for tx in range(0, a.shape[1], tile):
            t = a[ty:ty + tile, tx:tx + tile]
            if by == 'pattern' and not grid:
                e = empty[ty:ty + tile, tx:tx + tile]
                c = np.where(e, -1, (lum[ty:ty + tile, tx:tx + tile] << 24) | rgb[ty:ty + tile, tx:tx + tile])
                u = np.unique(c[~e]) if (~e).any() else np.zeros(0, np.int64)   # colours dark to light
                t = np.where(e, 0, np.searchsorted(u, c) + 1).astype(np.uint8)
            vs = [t] + ([t[:, ::-1], t[::-1], t[::-1, ::-1]] if flips else [])
            ks = [(v.shape, v.tobytes()) if v.dtype != object else tuple(map(tuple, v)) for v in vs]
            keys.append(min(ks))
    return keys

def unique_tiles(img, era='nes', tile=None, flips=None, by='colour'):
    """how many different background tiles an image needs, learnt from the NES pattern table (256 tiles
    of 8x8 for the whole background). img: PIL, an RGB(A) array or a 2D slot-name grid. tile and flips
    default to the era's tile / tile_flips (a tile and its mirror cost one when the map can flip).
    by='colour' compares exact pixels (a safe upper bound); by='pattern' compares the index layout the
    hardware stores: transparent and the era's shared backdrop are index 0, the other colours of a tile
    ranked dark to light, so one leaf tile drawn in two sub-palettes costs one. -> int"""
    e = ERAS[era]
    tile = e.get('tile') or 8 if tile is None else tile
    flips = bool(e.get('tile_flips')) if flips is None else flips
    backdrop = None
    if by == 'pattern' and e.get('shared_backdrop') and not (np.asarray(img).ndim == 2 and not isinstance(img, Image.Image)):
        a = _rgb(img) if isinstance(img, Image.Image) else np.asarray(img)
        rgb = a[..., :3][a[..., 3] >= 128] if a.shape[2] == 4 else a[..., :3].reshape(-1, 3)
        if len(rgb):
            u, c = np.unique(rgb, axis=0, return_counts=True); backdrop = tuple(int(v) for v in u[c.argmax()])
    return len(set(_tile_keys(img, tile, flips, by, backdrop)))

def check_tiles(img, era='nes', limit=None, tile=None, flips=None, by='colour'):
    """problems with a background under the era's tile budget, learnt from the NES (256 unique 8x8 tiles).
    limit overrides the era's bg_tiles (the era's None means no limit). Check the background alone: on
    the hardware sprites are not tiles of the map. -> (issues, unique tile count)"""
    e = ERAS[era]
    limit = e.get('bg_tiles') if limit is None else limit
    n = unique_tiles(img, era, tile, flips, by)
    t = e.get('tile') or 8 if tile is None else tile
    issues = ['%d unique %dx%d tiles, the limit is %d' % (n, t, t, limit)] if limit is not None and n > limit else []
    return issues, n

def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__); return 1
    if argv[0] == '--list':
        for k, e in ERAS.items():
            print('%-8s %-24s %dx%d, %d colours on screen%s' % (k, e['name'], *e['size'], e['max_colors'],
                  (', %d per %dx%d block' % (e['block_colors'], e['block'], e['block'])) if e.get('block') else ''))
        return 0
    def opt(name, default=None):
        if name in argv:
            i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
        return default
    tiles = '--tiles' in argv
    if tiles: argv.remove('--tiles')
    era, out, scale, layer = opt('--era', 'nes'), opt('-o'), int(opt('--scale', '4')), opt('--layer', 'full')
    img = Image.open(argv[0])
    issues, n = check(img, era, layer, tiles='pattern' if tiles else False)
    print('%s: %d colours; %s' % (ERAS[era]['name'], n, 'legal' if not issues else '; '.join(issues)))
    if out:
        fixed = enforce(img, era, layer)
        fixed.save(out)
        fixed.resize((fixed.width * scale, fixed.height * scale), Image.NEAREST).save(
            str(pathlib.Path(out).with_suffix('')) + '@%dx.png' % scale)
        issues2, n2 = check(fixed, era, layer)
        print('wrote %s: %d colours; %s' % (out, n2, 'legal' if not issues2 else '; '.join(issues2)))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
