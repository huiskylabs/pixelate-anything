"""Render Monsoon Street stills: python3 art/render.py [a|b|both]

Writes out/01-a.png and out/01-b.png (1920x1080, prescaled: the lamp map is smooth at screen
resolution), the 1x pixel layers out/01-a@1x.png and out/01-b@1x.png (strict palette, before light),
out/palette.json, and gate helpers (out/01-*-intent.png, out/01-b-actor.png)."""
import sys, json, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
from PIL import Image
from canvas import Canvas, to_image
import fx, post
import geom as G
from geom import W, H
from mpal import PAL, EMISSIVE
from street import Street, hsh, small_glyph, T_LOOP

OUT = HERE.parent / 'out'
SCALE = 4
AMBIENT = {'a': (0.31, 0.36, 0.51), 'b': (0.24, 0.27, 0.40)}
STILL_T = {'a': 40, 'b': 0}


def hoarding(phase, t):
    """the near-left corrugated hoarding: a flat dark near plane that never takes light"""
    c = Canvas(W, H, None)
    yy, xx = np.mgrid[0:H, 0:W]
    top = 70 + (xx * 6) // 56
    m = (xx < 56) & (yy >= top)
    # ribs of mismatched widths: a lit edge, the body, a shadow edge
    widths = [5, 4, 6, 4, 5, 3, 5, 6, 4, 5, 4, 6]
    x = 0
    for k, w in enumerate(widths):
        for i in range(w):
            colm = m[:, x + i] if x + i < W else None
            if colm is None:
                continue
            s = 'cool0' if i == 0 else ('plum' if i == 1 else 'void')
            c.g[colm, x + i] = s
        x += w
        if x >= 56:
            break
    # the top rail and its lit lip, a bottom kick plate
    for xi in range(56):
        t0 = top[0, xi]
        c.g[t0:t0 + 3, xi] = 'cool0'
        c.g[t0, xi] = 'cool1'
    # the striped post (warning stripes, diagonal)
    for y in range(140, H):
        for xi in range(6, 13):
            c.g[y, xi] = 'con1' if ((xi + y) // 4) % 2 == 0 else 'void'
    c.g[140:H, 13] = 'plum'
    # a notice with invented glyphs, one corner torn
    c.g[118:139, 24:42] = 'con1'
    c.g[118:120, 38:42] = None
    c.g[118:120, 38:42] = c.g[121, 30] if False else 'plum'
    for k in range(3):
        g = small_glyph(200 + k, 5, 4)
        for j in range(4):
            for i in range(5):
                if g[j, i]:
                    c.g[122 + k * 6 + j, 27 + i] = 'void'
    c.g[122:136, 35:39] = 'con0'
    # rain on the near plane (A): the near layer only, over the hoarding
    if phase == 'a':
        tmp = Canvas(W, H, None)
        fx.rain_cells(tmp, t, T_LOOP, n=46, length=9, slot='rn1', cycles=10, seed=19,
                      region=(0, 0, W, H), slant=7)
        r = (tmp.g == 'rn1') & m
        c.g[r] = 'rn0'
    mask = np.array(c.g != None) & m
    return c, mask


def build(phase):
    t = STILL_T[phase]
    S = Street(phase, t)
    S.awnings = []
    S.sky_and_far()
    S.ground()
    S.cross_street_wires()
    if phase == 'a':
        S.tram()
    S.left_wall()
    S.right_wall()
    S.tree()
    S.corner_block()
    S.hero()
    S.glass()
    S.poles()
    S.props()
    if phase == 'b':
        S.cat()
    S.reflect()
    S.light_columns()
    if phase == 'b':
        S.steam()
    if phase == 'a':
        S.rain()
    near, nmask = hoarding(phase, t)
    return S, near, nmask


def ambient_fn(phase, S):
    """the lamp map's ambient as a 1x colour field: cool, darker toward the top so wall crowns sink
    into the dark, plus soft warm spills (trapezoids and the lamp pool) built from masks"""
    r, g, b = AMBIENT[phase]
    yy = np.mgrid[0:H, 0:W][0].astype(float)
    k = 0.4 + 0.6 * np.clip((yy - 10) / 185.0, 0, 1) ** 1.2
    amb = np.stack([r * k, g * k, b * k], -1)
    for pts, gain, colour, blur in S.spills:
        m = S.c.mask_poly(pts).astype(float)
        m = post.blur(m, blur)
        amb += m[..., None] * gain * np.array(colour)[None, None, :]
    return amb.astype(np.float32)


def render(phase, save=True):
    S, near, nmask = build(phase)
    pal = PAL
    main = S.c.image(pal)
    layer = S.g.copy()
    layer[nmask] = near.g[nmask]
    pre = to_image(layer, pal)
    emit = np.isin(S.g, list(EMISSIVE)) | (np.char.startswith(S.g.astype(str), 'sky'))
    st = post.Stack(scale=SCALE, res='screen', background='#000000')
    st.plane(main, depth=1)
    st.light(lambda p: p.lightmap(ambient=ambient_fn(phase, S), lights=S.lights, cap=1.35, keep=emit), depth=1)
    near_img = to_image(np.where(nmask, near.g, 'void'), pal)
    st.plane(near_img, mask=nmask, depth=0)
    p = st.render()
    img = p.image()
    if save:
        OUT.mkdir(exist_ok=True)
        img.save(OUT / ('01-%s.png' % phase))
        pre.save(OUT / ('01-%s@1x.png' % phase))
        inten = S.INT.copy()
        Image.fromarray((inten * 255).astype(np.uint8)).save(OUT / ('01-%s-intent.png' % phase))
        if S.ACT.any():
            Image.fromarray((S.ACT * 255).astype(np.uint8)).save(OUT / ('01-%s-actor.png' % phase))
        used = sorted(set(layer.ravel()) - {None})
        json.dump({k: pal[k] for k in pal}, open(OUT / 'palette.json', 'w'), indent=1)
        print(phase, 'slots used', len(used))
    return S, img, pre


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    for ph in (('a', 'b') if which == 'both' else (which,)):
        render(ph)
