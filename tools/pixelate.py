#!/usr/bin/env python3
"""Turn an image into clean pixel art (not a blurry downscale).

usage: pixelate.py IMAGE -o OUT [--width 96 | --block 8] [--colors 16 | --palette P]
                   [--mode photo|art] [--match lab|luma] [--dither none|ordered] [--smooth 1]
                   [--sat 1.15] [--contrast 1.1] [--crop X,Y,W,H] [--cutout [TOL]] [--outline]
                   [--alpha 128] [--no-clean] [--scale 8]
       pixelate.py CLIP.mp4|.gif -o OUT.gif|.mp4 [--start 0] [--duration 4] [--fps 12] [same options]

  --crop X,Y,W,H  crop the source first, in pixels, or as fractions when every value is <= 1
                (0.25,0.3,0.5,0.4 is the middle half across, 30-70% down).
  --flatten N  photo mode: N edge-preserving passes (mean shift, with OpenCV installed). Busy
                scenes (cities, crowds, foliage) become flat planes with crisp borders.
  --grade DEG  grade a found palette like a pixel artist: shadows shift up to DEG degrees toward
                blue-violet, lights toward warm yellow, greys get a tint (try 28).
  --cutout [TOL] removes a flat background (the colour around the border, flood-filled inward,
                OKLab tolerance TOL, default 0.09) so a photographed object becomes a sprite.
                Combine with --outline.
  Video and animated GIF sources become an animated pixel GIF (or a crisp MP4): one palette for
                the whole clip, and pixels only change when the picture really does, so flat
                areas don't shimmer.

  --mode photo (picked automatically for images with thousands of distinct colours): smoothing,
                then each block's mean colour.
                Best for photos and paintings: no texture noise.
  --mode art   (picked for images with few colours): majority colour per block. Best for logos, line art,
                screenshots and renders with flat colours and hard edges.
  --smooth N   photo mode: N median passes (default 1). 2-4 turn heavy texture (fur, wood
                grain, foliage) into flat shapes; use it with small palettes.
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
    lab[..., 0] = np.clip(0.5 + (lab[..., 0] - 0.5) * contrast, 0, 1)   # never darker than black
    return lab

def crop_box(size, spec):
    v = [float(x) for x in str(spec).split(',')]
    if all(x <= 1 for x in v):
        v = [v[0] * size[0], v[1] * size[1], v[2] * size[0], v[3] * size[1]]
    x, y, w, h = [int(round(t)) for t in v]
    return (x, y, x + w, y + h)

def cutout(im, tol=0.09):
    """make the flat background around an object transparent: pixels close to the border colour,
    connected to the border"""
    from scipy import ndimage
    a = np.array(im.convert('RGBA'), float)
    lab = cl.rgb_to_oklab(a[..., :3])
    border = np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    bg = np.median(border, 0)
    near = ((lab - bg) ** 2).sum(-1) ** 0.5 < tol
    lbl, _ = ndimage.label(near)
    edge = np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))
    mask = np.isin(lbl, edge[edge > 0])
    mask = ndimage.binary_opening(mask, iterations=1)
    obj, n = ndimage.label(~mask)                    # drop specks (scale bars, dust) far smaller than the subject
    if n > 1:
        sizes = ndimage.sum(np.ones_like(obj), obj, range(1, n + 1))
        mask |= np.isin(obj, 1 + np.nonzero(sizes < 0.03 * sizes.max())[0])
    a[..., 3] = np.where(mask, 0, a[..., 3])
    return Image.fromarray(a.astype(np.uint8), 'RGBA')

def flatten_regions(rgb, passes, sub):
    """edge-preserving flattening (mean shift): texture and window grids become flat planes with
    crisp borders, the way a pixel artist simplifies. Uses OpenCV when installed, else median passes."""
    try:
        import cv2
    except ImportError:
        from PIL import ImageFilter
        for _ in range(passes):
            rgb = rgb.filter(ImageFilter.MedianFilter(5))
        return rgb
    bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
    for _ in range(passes):
        bgr = cv2.pyrMeanShiftFiltering(bgr, 3 * sub, 30)
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

def grade_palette(lab, shift=28.0, cool=270.0, warm=75.0, cmin=0.03):
    """pixel-art colour grading of a found palette: shadows lean blue-violet, lights lean warm,
    and greys get a tint, so a photo's palette reads as chosen rather than sampled"""
    L, C, H = cl.lch_of(lab)
    out = []
    for l, c, h in zip(np.atleast_1d(L), np.atleast_1d(C), np.atleast_1d(H)):
        t = float(np.clip((l - 0.55) / 0.35, -1, 1))          # -1 dark .. +1 light
        target = warm if t > -0.15 else cool
        d = ((target - h + 180) % 360) - 180
        if c < 0.035:                                         # greys take the tint outright: beige or slate
            h2 = target
        else:                                                 # colours lean toward it, more when muted
            h2 = h + np.sign(d) * min(abs(d), shift * abs(t) * (1.0 if c < 0.08 else 0.5))
        c2 = max(c * 1.15, cmin * (0.6 + 0.4 * abs(t)))
        out.append([l, c2 * np.cos(np.radians(h2)), c2 * np.sin(np.radians(h2))])
    return np.array(out)

def open_src(src, crop=None, cut=None):
    im = src if isinstance(src, Image.Image) else Image.open(src)
    im = im.convert('RGBA')
    if crop:
        im = im.crop(crop_box(im.size, crop))
    if cut:
        im = cutout(im, cut)
    return im

def pixelate(src, width=None, block=None, colors=16, palette=None, dither='none',
             sat=1.15, contrast=1.1, alpha_th=128, clean=True, outline=False, sub=4, mode=None, match=None, smooth=1,
             crop=None, cut=None, prev=None, sticky=0.0, flatten=0, grade=0.0):
    from PIL import ImageFilter
    im = open_src(src, crop, cut)
    if mode is None:   # photos and paintings have thousands of distinct colours; pixel art, logos and flat renders few
        probe = im.convert('RGB'); probe.thumbnail((256, 256), Image.NEAREST)
        mode = 'photo' if len(np.unique(np.asarray(probe).reshape(-1, 3), axis=0)) > 2500 else 'art'
    w0, h0 = im.size
    if block:
        width = max(1, round(w0 / block))
    width = width or 96
    height = max(1, round(h0 * width / w0))
    # supersample: sub x sub source samples per output pixel
    bigim = im.resize((width * sub, height * sub), Image.LANCZOS)
    if mode == 'photo':
        rgb = bigim.convert('RGB')
        for _ in range(0 if flatten else max(1, smooth)):   # more passes flatten fur, grain and noise into shapes
            rgb = rgb.filter(ImageFilter.MedianFilter(sub + 1 if sub % 2 == 0 else sub))
        if flatten:
            rgb = flatten_regions(rgb, flatten, sub)
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
        pal_lab = cl.kmeans(pts.reshape(-1, 3), colors, weights=(1 + 1.5 * np.clip(C / 0.15, 0, 1)) if grade else (1 + 0.7 * np.clip(C / 0.2, 0, 1)))
        hexes = [cl.rgb_to_hex(c) for c in cl.oklab_to_rgb(pal_lab)]
        pal_lab = cl.rgb_to_oklab(np.array([cl.hex_to_rgb(h) for h in hexes], float))   # exact
        if grade:   # match against the found colours, draw with their graded versions
            hexes = [cl.rgb_to_hex(c) for c in cl.oklab_to_rgb(grade_palette(pal_lab, grade))]
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
    if prev is not None and prev.shape == out.shape:
        # video: keep last frame's colour unless the new one is clearly better (no shimmer on flat areas)
        dp = np.take_along_axis(d, prev[..., None], -1)[..., 0]
        do = np.take_along_axis(d, out[..., None], -1)[..., 0]
        out = np.where(dp <= do + sticky, prev, out)
    if dither == 'ordered':
        d1 = np.take_along_axis(d, n1[..., None], -1)[..., 0] ** 0.5
        d2 = np.take_along_axis(d, n2[..., None], -1)[..., 0] ** 0.5
        t = d1 / (d1 + d2 + 1e-9)                                  # 0 (on n1) .. 0.5 (halfway)
        yy, xx = np.mgrid[0:height, 0:width]
        th = (BAYER4[yy & 3, xx & 3] + 0.5) / 16
        # art: only blocks that really mix two colours; photo: every in-between tone (gradients, skies
        # that fall between a fixed palette's colours)
        mixed = share < 0.6 if mode == 'art' else (t > 0.12) & (d1 > 0.03)
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

VIDEO = ('.mp4', '.mov', '.webm', '.mkv', '.m4v', '.avi')

def read_frames(src, start=0.0, duration=4.0, fps=12, crop=None, maxw=960):
    """frames of a video (via ffmpeg) or an animated GIF, as RGBA PIL images, cropped first"""
    import json, subprocess
    if pathlib.Path(src).suffix.lower() == '.gif':
        g = Image.open(src); frames = []
        for i in range(getattr(g, 'n_frames', 1)):
            g.seek(i); f = g.convert('RGBA')
            frames.append(f.crop(crop_box(f.size, crop)) if crop else f)
        return frames, g.info.get('duration', 100)
    info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                      'stream=width,height', '-of', 'json', str(src)], capture_output=True, text=True).stdout)
    W, H = info['streams'][0]['width'], info['streams'][0]['height']
    x0, y0, x1, y1 = crop_box((W, H), crop) if crop else (0, 0, W, H)
    cw, ch = x1 - x0, y1 - y0
    ow = min(maxw, cw); oh = round(ch * ow / cw)
    vf = 'crop=%d:%d:%d:%d,fps=%s,scale=%d:%d:flags=area' % (cw, ch, x0, y0, fps, ow, oh)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(duration), '-i', str(src),
                          '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'], capture_output=True).stdout
    n = len(raw) // (ow * oh * 4)
    arr = np.frombuffer(raw[:n * ow * oh * 4], np.uint8).reshape(n, oh, ow, 4)
    return [Image.fromarray(f, 'RGBA') for f in arr], round(1000 / float(fps))

def pixelate_clip(src, out, start=0.0, duration=4.0, fps=12, scale=4, crop=None, palette=None, colors=16,
                  sticky=0.004, **kw):
    """a video or GIF -> an animated pixel GIF (or MP4) with one palette and no shimmer"""
    frames, ms = read_frames(src, start, duration, fps, crop)
    if not frames:
        raise SystemExit('no frames read from %s' % src)
    if not palette:   # fit one palette to a strip of sample frames
        picks = frames[::max(1, len(frames) // 8)][:8]
        tw = 320; th = round(frames[0].height * tw / frames[0].width)
        strip = Image.new('RGBA', (tw, th * len(picks)))
        for i, f in enumerate(picks):
            strip.paste(f.resize((tw, th), Image.LANCZOS), (0, th * i))
        palette = ','.join(pixelate(strip, colors=colors, **{k: v for k, v in kw.items() if k in ('sat', 'contrast', 'mode', 'smooth')}, width=kw.get('width') or 96)[2])
    idxs = []; prev = None
    for f in frames:
        o, opaque, hexes = pixelate(f, palette=palette, prev=prev, sticky=sticky, **kw)
        idxs.append((o, opaque)); prev = o
    out = pathlib.Path(out)
    P = len(hexes); flat = sum((list(cl.hex_to_rgb(h)) for h in hexes), [])
    def frame_img(o, opaque, s):
        a = np.where(opaque, o, P).astype(np.uint8)
        im = Image.fromarray(a, 'P'); im.putpalette(flat + [0, 0, 0] * (256 - P))
        return im.resize((a.shape[1] * s, a.shape[0] * s), Image.NEAREST) if s > 1 else im
    hgt, wid = idxs[0][0].shape
    if out.suffix.lower() == '.mp4':
        import subprocess
        s = scale + (scale % 2)
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (wid * s, hgt * s),
                              '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p',
                              '-movflags', '+faststart', str(out)], stdin=subprocess.PIPE)
        for o, opaque in idxs:
            p.stdin.write(np.asarray(frame_img(o, opaque, s).convert('RGB')).tobytes())
        p.stdin.close(); p.wait()
        print('wrote %s (%dx%d pixels at %dx, %d frames, %d colours)' % (out, wid, hgt, s, len(idxs), P))
        return
    for s, path in ((1, out), (scale, out.with_name(out.stem + '@%dx.gif' % scale))):
        ims = [frame_img(o, opaque, s) for o, opaque in idxs]
        extra = {'transparency': P, 'disposal': 2} if any(not op.all() for _, op in idxs) else {}
        ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0, optimize=False, **extra)
    print('wrote %s (%dx%d, %d frames, %d colours) and its @%dx preview' % (out, wid, hgt, len(idxs), P, scale))

def main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    flags = {f: (f in a) for f in ('--outline', '--no-clean')}
    a[:] = [x for x in a if x not in flags]
    cut = None
    if '--cutout' in a:
        i = a.index('--cutout')
        if i + 1 < len(a) and re_num(a[i + 1]):
            cut = float(a[i + 1]); del a[i:i + 2]
        else:
            cut = 0.09; del a[i]
    out = opt('-o'); width = opt('--width'); block = opt('--block')
    kw = dict(width=int(width) if width else None, block=float(block) if block else None,
              dither=opt('--dither', 'none'), sat=float(opt('--sat', '1.15')), contrast=float(opt('--contrast', '1.1')),
              alpha_th=int(opt('--alpha', '128')), clean=not flags['--no-clean'], outline=flags['--outline'],
              mode=opt('--mode'), match=opt('--match'), smooth=int(opt('--smooth', '1')), cut=cut,
              flatten=int(opt('--flatten', '0')), grade=float(opt('--grade', '0')))
    colors, palette, crop, scale = int(opt('--colors', '16')), opt('--palette'), opt('--crop'), opt('--scale')
    src = a[0]
    animated = pathlib.Path(src).suffix.lower() in VIDEO or (
        pathlib.Path(src).suffix.lower() == '.gif' and getattr(Image.open(src), 'n_frames', 1) > 1)
    if animated:
        out = out or str(pathlib.Path(src).with_suffix('')) + '-pixel.gif'
        pixelate_clip(src, out, start=float(opt('--start', '0')), duration=float(opt('--duration', '4')),
                      fps=float(opt('--fps', '12')), scale=int(scale or 4), crop=crop, palette=palette, colors=colors, **kw)
        return
    res = pixelate(src, colors=colors, palette=palette, crop=crop, **kw)
    out = out or str(pathlib.Path(src).with_suffix('')) + '-pixel.png'
    save(*res, out, int(scale or 8))

def re_num(x):
    try:
        float(x); return True
    except ValueError:
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
