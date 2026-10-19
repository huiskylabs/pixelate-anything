"""The greyscale block-in of the shared composition at 256x224 (the 16-bit panel's grid): four
flat greys, one per value group of the brief. Run: python3 art/blockin.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Canvas, COMP, px, image, save, OUT

W, H = 256, 224
PAL = {'d': '#2e2e2e', 'm': '#6a6a6a', 'l': '#a8a8a8', 'b': '#f2f2f2'}

def build():
    c = Canvas(W, H, 'l')                                          # sky (light)
    hz = px(COMP['horizon'], H)
    # crag + town (darkest)
    pts = [(px(u, W), px(v, H)) for u, v in COMP['crag']] + [(px(0.83, W), 200), (px(0.28, W), 200)]
    c.poly(pts, 'd')
    t0, t1, t2, t3 = COMP['town']
    c.rect(px(t0, W), px(t1, H), px(t2, W) + 6, px(COMP['harbour'], H), 'd')
    # open sea right of the crag and the harbour (mid)
    c.rect(px(0.83, W), hz, W, H, 'm')
    c.rect(px(0.40, W), px(COMP['harbour'], H), W, H, 'm')
    # near cliff and post office (mid)
    pl, ce, cf = px(COMP['plateau'], H), COMP['cliff_edge'], COMP['cliff_foot']
    c.poly([(0, pl), (px(ce, W), pl), (px(ce + 0.02, W), px(0.5, H)), (px(cf - 0.01, W), px(0.7, H)),
            (px(cf, W), H), (0, H)], 'm')
    o0, o1, o2, o3 = COMP['office']
    c.rect(px(o0, W), px(0.21, H), px(o2, W), pl, 'm')             # walls
    c.poly([(px(o0, W) - 3, px(0.215, H)), (px((o0 + o2) / 2, W), px(o1, H)), (px(o2, W) + 3, px(0.215, H))], 'm')
    c.rect(px(0.20, W), px(0.11, H), px(0.215, W) + 2, px(0.18, H), 'm')   # chimney
    c.rect(px(COMP['pole'][0], W), px(COMP['pole'][1], H), px(COMP['pole'][0], W) + 1, pl, 'm')
    (ru0, rv0), (ru1, rv1) = COMP['rail']
    c.poly([(px(ru0, W), px(rv0, H)), (px(ru1, W), px(rv1, H)), (px(ru1, W), px(rv1, H) + 3), (px(ru0, W), px(rv0, H) + 3)], 'm')
    # the glider (brightest): wing, pilot, satchel, boom and fin
    w0, wv0, w1, wv1 = COMP['wing']
    x0, x1, y0, y1 = px(w0, W), px(w1, W), px(wv0, H), px(wv1, H)
    c.poly([(x0, y0 + 6), (x0 + 8, y0 + 2), (x1 - 6, y0), (x1, y0 + 2), (x1 - 4, y1 - 1), (x0 + 6, y1 + 2)], 'b')
    c.rect(px(0.53, W), y1, px(0.57, W), px(0.50, H), 'b')           # pilot
    c.rect(px(0.535, W), px(0.47, H), px(0.565, W) + 1, px(0.54, H), 'b')    # satchel
    c.rect(x0 + 2, px(0.445, H), px(0.53, W), px(0.445, H) + 2, 'b')   # boom
    c.rect(x0, px(0.415, H), x0 + 6, px(0.465, H), 'b')                # fin
    return c

if __name__ == '__main__':
    c = build()
    im = image(c, PAL)
    im.convert('RGB').save(OUT / 'blockin-a.png')
    im.convert('RGB').resize((W * 3, H * 3), 0).save(OUT / 'blockin-a@3x.png')
    import numpy as np
    g = c.g
    for k in 'dmlb':
        print(k, '%.1f%%' % (100 * (g == k).mean()))
