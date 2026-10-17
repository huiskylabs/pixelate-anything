"""Greyscale block-in from the real 3D description: every plane flattened to one grey per value
group (void darkest; dock pit, canal and the slab's cut faces dark; the yard and its props mid; the
ship brightest). Prints each plane's share for the brief's Planes line."""
import sys, pathlib
import numpy as np
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import yard

GREY = {'darkest': 18, 'dark': 52, 'mid': 98, 'brightest': 215}

def planes(Y, slots):
    s = Y.s
    out = np.full(slots.shape, 'void', object)
    tagged = {}
    for tag, ids in Y.tag.items():
        for i in ids:
            tagged[i] = tag
    obj = s.obj
    for (yy, xx), o in np.ndenumerate(obj):
        if o < 0:
            continue
        t = tagged.get(o, 'prop')
        if o in Y.hero:
            out[yy, xx] = 'ship'
        elif t in ('dock', 'water', 'shore', 'blocks'):
            out[yy, xx] = 'dock pit and canal'
        elif t == 'slab':
            out[yy, xx] = 'yard ground' if s.face[yy, xx] == 1 else 'slab cut faces'
        else:
            out[yy, xx] = 'crane, sawpit, plank stack, hut'
    return out

BAND = {'void': 'darkest', 'dock pit and canal': 'dark', 'slab cut faces': 'dark', 'yard ground': 'mid',
        'crane, sawpit, plank stack, hut': 'mid', 'ship': 'brightest'}

if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'a'
    Y, slots, pal = yard.render(0, 1, 'dawn') if which == 'a' else yard.render(3, 4, 'night')
    P = planes(Y, slots)
    img = np.zeros(P.shape, np.uint8)
    for name, band in BAND.items():
        img[P == name] = GREY[band]
    for name in BAND:
        print('%-34s %5.1f%%  (%s)' % (name, 100 * (P == name).mean(), BAND[name]))
    Image.fromarray(img, 'L').convert('RGB').save(yard.OUT / ('blockin-%s.png' % which))
