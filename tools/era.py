#!/usr/bin/env python3
"""Console-era presets: the hardware limits that gave classic pixel art its look, and a checker
that holds an image to them (or forces it into them).

usage: era.py IMAGE --era nes|gameboy|snes|genesis|gba|pico-8|neogeo [-o OUT] [--scale 4]
              [--layer bg|full|sprite|fix]
       era.py --list

Without -o it reports. With -o it also writes OUT (the image made legal) and OUT@Nx.png.

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

def check(img, era, layer='full'):
    """problems with this image under the era's rules (layer 'bg' also applies the
    per-block rule; sprites over a background are exempt from it)"""
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
    era, out, scale, layer = opt('--era', 'nes'), opt('-o'), int(opt('--scale', '4')), opt('--layer', 'full')
    img = Image.open(argv[0])
    issues, n = check(img, era, layer)
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
