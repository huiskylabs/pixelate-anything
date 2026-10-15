#!/usr/bin/env python3
"""Turn an image into clean pixel art (not a blurry downscale).

usage: pixelate.py IMAGE -o OUT [--width 96 | --block 8] [--colors 16 | --palette P]
                   [--mode photo|art] [--match lab|luma] [--dither none|ordered]
                   [--sat 1.15] [--contrast 1.1] [--outline] [--alpha 128] [--no-clean] [--scale 8]

  --mode photo (default for .jpg): edge-preserving smoothing, then each block's mean colour.
                Best for photos and paintings: no texture noise.
  --mode art   (default otherwise): majority colour per block. Best for logos, line art,
                screenshots and renders with flat colours and hard edges.
  --match luma maps by brightness only (stretching the image's range onto the palette's):
                use it for monochrome palettes like gameboy. Picked automatically when the
                palette has little hue variety.

How it works:
  1. a small boost to saturation and contrast in OKLab (pixel art reads with more of both)
  2. a palette: --palette (preset, file or "#a,#b") or --colors N found by k-means in OKLab
  3. art mode: each output pixel is the MAJORITY palette colour inside its block, so edges
     and thin features stay crisp; blocks with no clear winner use the block's mean.
     photo mode: a median filter first (smooths texture, keeps edges), then block means.
     With --dither ordered, in-between colours become a Bayer dither of the two nearest.
  4. clean-up: lone pixels that no neighbour shares are merged into their surroundings
  5. --outline draws a 1 px outline in the darkest colour around opaque shapes
     (for sprites cut out on transparency)
Writes OUT (1x, indexed PNG) and OUT@{scale}x.png (nearest-neighbour preview).
"""
import pathlib, sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl

BAYER4 = np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4)

def adjust(lab, sat, contrast):
    lab = lab.copy()
    lab[..., 1:] *= sat
    lab[..., 0] = 0.5 + (lab[..., 0] - 0.5) * contrast
    return lab

def pixelate(src, width=None, block=None, colors=16, palette=None, dither='none',
             sat=1.15, contrast=1.1, alpha_th=128, clean=True, outline=False, sub=4, mode=None, match=None):
    from PIL import ImageFilter
    if mode is None:
        mode = 'photo' if str(src).lower().endswith(('.jpg', '.jpeg', '.webp')) else 'art'
    im = Image.open(src).convert('RGBA')
    w0, h0 = im.size
    if block:
        width = max(1, round(w0 / block))
    width = width or 96
    height = max(1, round(h0 * width / w0))
    # supersample: sub x sub source samples per output pixel
    bigim = im.resize((width * sub, height * sub), Image.LANCZOS)
    if mode == 'photo':
        rgb = bigim.convert('RGB').filter(ImageFilter.MedianFilter(sub + 1 if sub % 2 == 0 else sub))
        bigim = Image.merge('RGBA', (*rgb.split(), bigim.split()[3]))
    big = np.array(bigim, float)
    alpha = np.array(im.resize((width, height), Image.BOX), float)[..., 3]
    lab = adjust(cl.rgb_to_oklab(np.clip(big[..., :3], 0, 255)), sat, contrast)
    opaque_big = big[..., 3] >= alpha_th
    if palette:
        hexes = cl.palette_list(cl.load_palette(palette))
        pal_lab = cl.rgb_to_oklab(np.array([cl.hex_to_rgb(h) for h in hexes], float))
    else:
        if mode == 'photo':   # cluster the block colours that will actually be drawn
            mlab = lab.reshape(height, sub, width, sub, 3).mean((1, 3))
            mop = opaque_big.reshape(height, sub, width, sub).mean((1, 3)) >= 0.5
            pts = mlab[mop] if mop.any() else mlab.reshape(-1, 3)
        else:
            pts = lab[opaque_big] if opaque_big.any() else lab.reshape(-1, 3)
        L, C, H = cl.lch_of(pts)
        pal_lab = cl.kmeans(pts.reshape(-1, 3), colors, weights=1 + 0.7 * np.clip(C / 0.2, 0, 1))
        hexes = [cl.rgb_to_hex(c) for c in cl.oklab_to_rgb(pal_lab)]
        pal_lab = cl.rgb_to_oklab(np.array([cl.hex_to_rgb(h) for h in hexes], float))   # exact
    P = len(hexes)
    if match is None:
        Lp, Cp, Hp = cl.lch_of(pal_lab)
        hue_spread = np.ptp(Hp[Cp > 0.03]) if (Cp > 0.03).sum() > 1 else 0
        match = 'luma' if (Cp > 0.03).sum() <= 1 or hue_spread < 40 else 'lab'
    if match == 'luma':
        # stretch the image's lightness range onto the palette's, then match lightness only
        Li = lab[..., 0][opaque_big] if opaque_big.any() else lab[..., 0]
        lo, hi = np.percentile(Li, 2), np.percentile(Li, 98)
        Lp = pal_lab[:, 0]
        lab = lab.copy()
        lab[..., 0] = Lp.min() + (np.clip(lab[..., 0], lo, hi) - lo) / max(1e-6, hi - lo) * (Lp.max() - Lp.min())
        lab[..., 1:] = 0
        pal_lab = pal_lab.copy(); pal_lab[:, 1:] = 0
    idx_big = cl.nearest(lab, pal_lab).reshape(height * sub, width * sub)
    blocks = idx_big.reshape(height, sub, width, sub).transpose(0, 2, 1, 3).reshape(height, width, sub * sub)
    counts = np.zeros((height, width, P), np.int32)
    for j in range(sub * sub):
        np.add.at(counts, (np.arange(height)[:, None], np.arange(width)[None, :], blocks[..., j]), 1)
    major = counts.argmax(-1)
    share = counts.max(-1) / (sub * sub)
    mean_lab = lab.reshape(height, sub, width, sub, 3).mean((1, 3))
    d = ((mean_lab[:, :, None, :] - pal_lab[None, None]) ** 2).sum(-1)
    order = np.argsort(d, -1)
    n1, n2 = order[..., 0], order[..., 1]
    out = np.where(share >= (0.45 if mode == 'art' else 0.7), major, n1)
    if dither == 'ordered':
        d1 = np.take_along_axis(d, n1[..., None], -1)[..., 0] ** 0.5
        d2 = np.take_along_axis(d, n2[..., None], -1)[..., 0] ** 0.5
        t = d1 / (d1 + d2 + 1e-9)                                  # 0 (on n1) .. 0.5 (halfway)
        yy, xx = np.mgrid[0:height, 0:width]
        th = (BAYER4[yy & 3, xx & 3] + 0.5) / 16
        mixed = share < 0.6
        out = np.where(mixed & (th < t), n2, out)
    opaque = alpha >= alpha_th
    if clean:
        for _ in range(2 if mode == 'photo' else 1):
            out = despeckle(out, opaque)
    if outline:
        dark = int(np.argmin(pal_lab[:, 0]))
        ring = np.zeros_like(opaque)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ring |= np.roll(np.roll(opaque, dy, 0), dx, 1)
        ring &= ~opaque
        out = np.where(ring, dark, out)
        opaque = opaque | ring
    return out, opaque, hexes

def despeckle(idx, opaque):
    """merge lone pixels (no 4-neighbour shares their colour) into the dominant neighbour colour"""
    H, W = idx.shape
    out = idx.copy()
    pad = np.pad(idx, 1, mode='edge')
    nb = np.stack([pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], -1)
    four = nb[..., [1, 3, 4, 6]]
    lone = (four != idx[..., None]).all(-1) & opaque
    for y, x in zip(*np.nonzero(lone)):
        vals, cnt = np.unique(nb[y, x], return_counts=True)
        if cnt.max() >= 5:
            out[y, x] = vals[cnt.argmax()]
    return out

def save(out, opaque, hexes, path, scale):
    path = pathlib.Path(path)
    P = len(hexes)
    im = Image.fromarray(out.astype(np.uint8), 'P')
    flat = []
    for h in hexes: flat += list(cl.hex_to_rgb(h))
    im.putpalette(flat + [0, 0, 0] * (256 - P))
    if not opaque.all():
        a = np.where(opaque, out, P).astype(np.uint8)        # transparent index P
        im = Image.fromarray(a, 'P'); im.putpalette(flat + [0, 0, 0] * (256 - P))
        im.info['transparency'] = P
    im.save(path, transparency=P if not opaque.all() else None) if not opaque.all() else im.save(path)
    big = im.convert('RGBA').resize((out.shape[1] * scale, out.shape[0] * scale), Image.NEAREST)
    prev = path.with_name(path.stem + '@%dx.png' % scale)
    big.save(prev)
    used = len(np.unique(out[opaque])) if opaque.any() else 0
    print('wrote %s (%dx%d, %d colours used) and %s' % (path, out.shape[1], out.shape[0], used, prev))

def main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    flags = {f: (f in a) for f in ('--outline', '--no-clean')}
    a[:] = [x for x in a if x not in flags]
    out = opt('-o'); width = opt('--width'); block = opt('--block')
    res = pixelate(a[0], width=int(width) if width else None, block=float(block) if block else None,
                   colors=int(opt('--colors', '16')), palette=opt('--palette'), dither=opt('--dither', 'none'),
                   sat=float(opt('--sat', '1.15')), contrast=float(opt('--contrast', '1.1')),
                   alpha_th=int(opt('--alpha', '128')), clean=not flags['--no-clean'], outline=flags['--outline'],
                   mode=opt('--mode'), match=opt('--match'))
    out = out or str(pathlib.Path(a[0]).with_suffix('')) + '-pixel.png'
    save(*res, out, int(opt('--scale', '8')))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
