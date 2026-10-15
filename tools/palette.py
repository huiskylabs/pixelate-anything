#!/usr/bin/env python3
"""Palettes: extract from an image, build hue-shifted ramps, load presets, export.

usage:
  palette.py extract IMAGE [-n 16] [-o OUT]       k-means in OKLab, sorted into hue families
  palette.py ramps NAME=#hex [NAME=#hex ...] [--steps 5] [--shift 22] [-o OUT]
                                                  one ramp per material, named NAME0..NAME{steps-1}
  palette.py ramp #hex [--steps 5] [--shift 22]   print one ramp
  palette.py show PALETTE [-o OUT]                swatch sheet of any palette
  palette.py js PALETTE --name KEY                print a palettes.js entry ({slot: hex}) for a scene
  palette.py list                                 bundled presets

PALETTE is a preset name (palettes/*.hex), a .hex/.gpl/.json/.png file, or "#a,#b,...".
-o OUT writes OUT.hex, OUT.gpl (GIMP/Aseprite/Krita), OUT.json, OUT.png (1 px per colour,
loadable as a palette in Aseprite) and OUT-swatch.png (labelled, for looking at).

Ramps: darks drift toward blue-violet and get a touch more saturated, lights drift toward
warm yellow and lose saturation (--shift degrees at the ends), the base colour stays exact.
"""
import json, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl

def ramp(base, steps=5, shift=22.0):
    L0, C0, h0 = cl.lch_of(cl.rgb_to_oklab(np.array(cl.hex_to_rgb(base))))
    L0, C0, h0 = float(L0), float(C0), float(h0)
    bi = min(steps - 1, max(0, round((steps - 1) * 0.55)))
    Lmin, Lmax = max(0.2, L0 - 0.125 * bi), min(0.95, L0 + 0.13 * (steps - 1 - bi))   # ~0.125 L per step
    out = []
    for i in range(steps):
        if i == bi:
            out.append(base.lower()); continue
        t = (i - bi) / max(1, bi) if i < bi else (i - bi) / max(1, steps - 1 - bi)   # -1 .. 1
        L = L0 + (L0 - Lmin) * t if t < 0 else L0 + (Lmax - L0) * t
        target = 275.0 if t < 0 else 85.0          # shadows cool, lights warm
        d = ((target - h0 + 180) % 360) - 180
        h = h0 + np.sign(d) * min(abs(d), shift * abs(t))
        C = C0 * (L / L0) ** 0.8 * (1 + 0.15 * abs(t)) if t < 0 else C0 * (1 - 0.28 * t)
        C = cl.clamp_chroma(L, max(C, 0.0), h)
        out.append(cl.rgb_to_hex(cl.oklab_to_rgb(cl.oklch(L, C, h))))
    return out

def extract(image, n=16):
    im = np.array(Image.open(image).convert('RGBA')).reshape(-1, 4)
    px = im[im[:, 3] > 127][:, :3]
    lab = cl.rgb_to_oklab(px)
    # weight saturated colours up a little so small accents survive
    L, C, H = cl.lch_of(lab)
    C = cl.kmeans(lab, n, weights=1 + 3 * np.clip(C / 0.2, 0, 1))
    return cl.sort_palette([cl.rgb_to_hex(c) for c in cl.oklab_to_rgb(C)])

def swatch(pal, path, cols=None):
    items = list(pal.items()) if isinstance(pal, dict) else [(None, h) for h in pal]
    n = len(items)
    cols = cols or min(n, 8)
    rows = (n + cols - 1) // cols
    cw, ch = 72, 56
    im = Image.new('RGB', (cols * cw, rows * ch), (24, 24, 28))
    d = ImageDraw.Draw(im)
    for i, (name, h) in enumerate(items):
        x, y = (i % cols) * cw, (i // cols) * ch
        d.rectangle([x + 2, y + 2, x + cw - 3, y + ch - 18], fill=cl.hex_to_rgb(h))
        d.text((x + 4, y + ch - 16), (name + ' ' if name else '') + h, fill=(220, 220, 220))
    im.save(path)

def write_all(pal, out, title='palette'):
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    hexes = cl.palette_list(pal)
    out.with_suffix('.hex').write_text('\n'.join(h.lstrip('#') for h in hexes) + '\n')
    gpl = ['GIMP Palette', 'Name: ' + title, 'Columns: 8', '#']
    names = list(pal.keys()) if isinstance(pal, dict) else [h for h in hexes]
    for name, h in zip(names, hexes):
        r, g, b = cl.hex_to_rgb(h)
        gpl.append('%3d %3d %3d\t%s' % (r, g, b, name))
    out.with_suffix('.gpl').write_text('\n'.join(gpl) + '\n')
    out.with_suffix('.json').write_text(json.dumps(pal if isinstance(pal, dict) else {'colors': hexes}, indent=1))
    strip = Image.new('RGB', (len(hexes), 1))
    strip.putdata([cl.hex_to_rgb(h) for h in hexes])
    strip.save(out.with_suffix('.png'))
    swatch(pal, out.parent / (out.name + '-swatch.png'))
    print('wrote %s.{hex,gpl,json,png} and %s-swatch.png (%d colours)' % (out, out.name, len(hexes)))

def main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    if not a:
        print(__doc__); return
    cmd = a.pop(0)
    out = opt('-o')
    if cmd == 'list':
        for p in sorted((cl.KIT / 'palettes').glob('*.hex')):
            print('%-24s %d colours' % (p.stem, len(cl.load_palette(str(p)))))
    elif cmd == 'extract':
        n = int(opt('-n', '16'))
        pal = extract(a[0], n)
        print(' '.join(pal))
        if out: write_all(pal, out, pathlib.Path(a[0]).stem)
    elif cmd == 'ramp':
        steps, shift = int(opt('--steps', '5')), float(opt('--shift', '22'))
        print(' '.join(ramp(a[0], steps, shift)))
    elif cmd == 'ramps':
        steps, shift = int(opt('--steps', '5')), float(opt('--shift', '22'))
        pal = {}
        for spec in a:
            name, base = spec.split('=')
            for i, h in enumerate(ramp(base, steps, shift)):
                pal['%s%d' % (name, i)] = h
        for k, v in pal.items():
            print(k, v)
        if out: write_all(pal, out, pathlib.Path(out).stem)
    elif cmd == 'show':
        pal = cl.load_palette(a[0])
        path = (out or pathlib.Path(a[0]).stem) + '-swatch.png'
        swatch(pal, path); print('wrote', path)
    elif cmd == 'js':
        pal = cl.load_palette(a[0])
        key = opt('--name', 'phase')
        if not isinstance(pal, dict):
            pal = {'C%d' % i: h for i, h in enumerate(pal)}
        body = ', '.join("%s: '%s'" % (k, v) for k, v in pal.items())
        print('  %s: { %s },' % (key, body))
    else:
        print(__doc__)

if __name__ == '__main__':
    main(sys.argv[1:])
