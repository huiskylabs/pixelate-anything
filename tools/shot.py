#!/usr/bin/env python3
"""Preview frames of a scene as PNGs (rendered in Node, exactly as the video).

usage: shot.py SCENE_DIR t1 [t2 ...] [--zoom 2] [--crop x,y,w,h] [--grid] [--out DIR]
  t     seconds into the picture loop (frame k = round(t * 30))
  --grid  also writes one sheet with every frame (2 columns)
Look at every shot yourself: it is the only way to judge the art.
"""
import pathlib, sys
from PIL import Image

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / 'tools'))
import render_video as rv

def main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    zoom = int(opt('--zoom', '2'))
    crop = opt('--crop')
    grid = '--grid' in a
    if grid:
        a.remove('--grid')
    scene = pathlib.Path(a.pop(0))
    outdir = pathlib.Path(opt('--out', str(scene / 'shots')))
    outdir.mkdir(parents=True, exist_ok=True)
    i = rv.info(scene)
    if i['warnings']:
        print('warnings:', *i['warnings'], sep='\n  ')
    ims = []
    for t in [float(x) for x in a] or [0.0]:
        k = int(round(t * 30)) % i['TICKS']
        im = Image.frombytes('RGBA', (i['W'], i['H']), rv.frames(scene, k, k + 1)).convert('RGB')
        if crop:
            x, y, w, h = (int(v) for v in crop.split(','))
            im = im.crop((x, y, x + w, y + h))
        im = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
        fn = outdir / ('t%07.2f.png' % t)
        im.save(fn); ims.append(im)
        print(fn)
    if grid and len(ims) > 1:
        w, h = ims[0].size
        rows = (len(ims) + 1) // 2
        G = Image.new('RGB', (w * 2, h * rows))
        for j, im in enumerate(ims):
            G.paste(im, ((j % 2) * w, (j // 2) * h))
        fn = outdir / 'grid.png'
        G.save(fn)
        print(fn)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
