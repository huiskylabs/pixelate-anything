"""Render the two moments from ONE index array, export palettes, verify, and write zoom crops.

    python3 art/render.py            # index map, A, B, palettes, verification
    python3 art/render.py --crops    # also 4x crops of the focal and busy areas for looking
"""
import sys, json, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[3] / 'tools'))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from PIL import Image
import palette as P
import palettes as PP
import canyon

ROOT = str(pathlib.Path(__file__).resolve().parents[1]) + '/'
OUT = ROOT + 'out/'
SCALE = 6


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def index_array(c):
    idx = np.vectorize(PP.INDEX.get, otypes=[np.int32])(c.g)
    assert (idx >= 0).all()
    return idx.astype(np.uint8)


def lut(pal):
    return np.array([rgb(pal[s]) for s in PP.SLOTS], np.uint8)


def decode(idx, pal):
    return lut(pal)[idx]


def export_palette(pal, base, title):
    with open(base + '.json', 'w') as f:
        json.dump(pal, f, indent=1)
    with open(base + '.hex', 'w') as f:
        f.write('\n'.join(pal[s][1:] for s in PP.SLOTS) + '\n')
    with open(base + '.gpl', 'w') as f:
        f.write('GIMP Palette\nName: %s\nColumns: 8\n#\n' % title)
        for s in PP.SLOTS:
            r, g, b = rgb(pal[s])
            f.write('%3d %3d %3d\t%s\n' % (r, g, b, s))


def main(crops=False):
    c = canyon.build()
    idx = index_array(c)
    pa = PP.moment(**PP.A_MOMENT)
    pb = PP.moment(**PP.B_MOMENT)
    # the index map as a P-mode PNG (1x), carrying the sunset-flash palette so it previews
    im = Image.fromarray(idx, 'P')
    flat = [v for s in PP.SLOTS for v in rgb(pa[s])]
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.save(OUT + '03-index.png')
    export_palette(pa, OUT + '03-sunset', 'Canyon Cycle - rose sunset, lightning instant')
    export_palette(pb, OUT + '03-night', 'Canyon Cycle - indigo night')
    a = decode(idx, pa)
    b = decode(idx, pb)
    Image.fromarray(a).resize((320 * SCALE, 180 * SCALE), Image.NEAREST).save(OUT + '03-a.png')
    Image.fromarray(b).resize((320 * SCALE, 180 * SCALE), Image.NEAREST).save(OUT + '03-b.png')
    Image.fromarray(a).save(OUT + 'native-a.png')
    Image.fromarray(b).save(OUT + 'native-b.png')
    verify()
    if crops:
        for name, img in (('a', a), ('b', b)):
            for tag, (x0, y0, x1, y1) in {'hero': (180, 66, 262, 118), 'falls': (40, 14, 170, 132),
                                          'sky': (96, 0, 216, 100), 'river': (40, 118, 280, 180)}.items():
                Image.fromarray(img[y0:y1, x0:x1]).resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.NEAREST).save(
                    OUT + 'crop-%s-%s.png' % (name, tag))
            Image.fromarray(img).resize((960, 540), Image.NEAREST).save(OUT + 'view-%s.png' % name)
    used = sorted(set(PP.SLOTS[i] for i in np.unique(idx)))
    print('slots used: %d of %d' % (len(used), len(PP.SLOTS)), [s for s in PP.SLOTS if s not in used])
    print('distinct colours: A %d, B %d' % (len(np.unique(a.reshape(-1, 3), axis=0)),
                                            len(np.unique(b.reshape(-1, 3), axis=0))))


def verify():
    """A and B decode from the identical index array: re-read the saved files and compare"""
    idx = np.asarray(Image.open(OUT + '03-index.png'))
    assert Image.open(OUT + '03-index.png').mode == 'P'
    pa = json.load(open(OUT + '03-sunset.json'))
    pb = json.load(open(OUT + '03-night.json'))
    a = np.asarray(Image.open(OUT + '03-a.png').convert('RGB'))
    b = np.asarray(Image.open(OUT + '03-b.png').convert('RGB'))
    big = np.repeat(np.repeat(idx, SCALE, 0), SCALE, 1)
    okA = np.array_equal(lut(pa)[big], a)
    okB = np.array_equal(lut(pb)[big], b)
    # and every 6x6 cell is flat (nearest at a whole scale)
    flat = all(np.all(img.reshape(180, SCALE, 320, SCALE, 3) == img[::SCALE, ::SCALE][:, None, :, None])
               for img in (a, b))
    print('verify: A == sunset[index] %s, B == night[index] %s, cells flat %s' % (okA, okB, flat))
    assert okA and okB and flat


if __name__ == '__main__':
    main(crops='--crops' in sys.argv)
