"""The boss part sprites of pose A on one transparent sheet (1x and 4x), with each part's rect on
the sheet, its pivot and its anchors (sprite-local px) in boss-parts.json."""
import sys, json, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from PIL import Image
import boss
from scene import rgba, OUT

def main():
    parts = boss.assemble('A')
    crops, meta = [], {}
    for P in parts:
        m = ~np.equal(P.c.g, None)
        ys, xs = np.nonzero(m)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        crops.append((P, rgba(P.c.g).crop((int(x0), int(y0), int(x1), int(y1))), int(x0), int(y0)))
    W = sum(c[1].width for c in crops) + 4 * (len(crops) + 1)
    H = max(c[1].height for c in crops) + 8
    sheet = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    x = 4
    for P, im, x0, y0 in crops:
        sheet.paste(im, (x, 4), im)
        meta[P.name] = dict(rect=[x, 4, im.width, im.height],
                            pivot=[P.pivot[0] - x0, P.pivot[1] - y0],
                            anchors={k: [v[0] - x0, v[1] - y0] for k, v in P.anchors.items()})
        x += im.width + 4
    sheet.save(OUT / 'boss-parts.png')
    sheet.resize((W * 4, H * 4), Image.NEAREST).save(OUT / 'boss-parts@4x.png')
    json.dump(dict(pose='A', note='pivot and anchors are sprite-local px; rect is x, y, w, h on the 1x sheet',
                   parts=meta), open(OUT / 'boss-parts.json', 'w'), indent=1)
    print(len(meta), 'parts:', ', '.join(meta))

if __name__ == '__main__':
    main()
