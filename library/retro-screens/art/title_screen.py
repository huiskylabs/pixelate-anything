"""Pixel Harbor: an original title screen. The isometric San Francisco at night (harbor_city.py,
a copy of the san-francisco piece's city.py) is cropped to 256x224 and pushed through the NES-style preset
(tools/era.py: snapped to the 2C02 master palette, cut to 25 colours), then a logo and a blinking
menu go on top. Shows the point of the era presets: any scene, retargeted to an era.
144 frames at 12 fps (the city's own loop).
"""
import sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
import colorlib as cl
import pixfont, era

W, H = 256, 224
FRAMES, FPS = 144, 12

def big_text(img, s, x, y, top, bottom, outline, scale=2):
    """the 5x7 font at 2x with a two-tone vertical gradient and a 1 px outline: a logo"""
    a = np.zeros((H, W), np.int8)
    class G:
        def set(self, px, py, v):
            for dy in range(scale):
                for dx in range(scale):
                    X, Y = x + (px - x) * scale + dx, y + (py - y) * scale + dy
                    if 0 <= X < W and 0 <= Y < H:
                        a[Y, X] = 1
    pixfont.draw(G(), s, x, y, 1)
    ring = np.zeros_like(a, bool)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        ring |= np.roll(np.roll(a == 1, dy, 0), dx, 1)
    ring &= a == 0
    img[ring] = cl.hex_to_rgb(outline)
    ys = np.nonzero(a == 1)[0]
    if len(ys):
        mid = (ys.min() + ys.max()) / 2
        for Y, X in zip(*np.nonzero(a == 1)):
            img[Y, X] = cl.hex_to_rgb(top if Y <= mid else bottom)

NIGHT_RAMP = ['#000000', '#0000bc', '#4428bc', '#6888fc', '#b8b8f8', '#fcfcfc']   # an NES night, by lightness

def night_ramp(rgb):
    """retarget a night picture to the NES way of doing night: everything that is not a light
    goes onto a blue ramp by lightness; lights (bright, saturated) snap to their nearest NES colour.
    Then the era preset checks the result."""
    flat = rgb.reshape(-1, 3)
    u, inv = np.unique(flat, axis=0, return_inverse=True)
    lab = cl.rgb_to_oklab(u.astype(float))
    L, C, Hh = cl.lch_of(lab)
    ramp = np.array([cl.hex_to_rgb(h) for h in NIGHT_RAMP], float)
    nes = era.palette_rgb('nes')
    nearest = nes[cl.nearest(lab, cl.rgb_to_oklab(nes))]
    q = np.clip(((L - 0.12) / 0.62) * (len(ramp) - 1), 0, len(ramp) - 1)
    mapped = ramp[np.round(q).astype(int)]
    light = (C > 0.09) & (L > 0.55)
    out = np.where(light[:, None], nearest, mapped)
    res = out[inv.ravel()].reshape(rgb.shape).astype(np.uint8)
    return np.asarray(era.enforce(Image.fromarray(res, 'RGB'), 'nes').convert('RGB')).copy()

def render_frames(frames=FRAMES):
    import harbor_city as city
    from iso import clone
    base = city.build_static()
    out = []
    for t in range(frames):
        s = clone(base); s.t = t
        city.draw_cars(s, t); city.draw_boats(s, t); city.draw_people(s, t)
        slots = np.array(s.render().a, object)
        slots = np.where(slots == None, 'water1', slots)
        p = city.phase_palette('night', t)
        rgb = np.array([[cl.hex_to_rgb(p[k]) for k in row] for row in slots], np.uint8)
        crop = rgb[40:40 + H, 16:16 + W].astype(float)
        crop[:56] *= 0.45; crop[56:64] *= 0.7                      # quiet the sky area under the logo
        nes = night_ramp(crop.astype(np.uint8))
        big_text(nes, 'PIXEL', (W - pixfont.width('PIXEL') * 3) // 2, 8, '#f8d878', '#fca044', '#000000', 3)
        big_text(nes, 'HARBOR', (W - pixfont.width('HARBOR') * 3) // 2, 32, '#f8d878', '#f87858', '#000000', 3)
        nes[176:212, 70:186] = 0
        im = Image.fromarray(nes, 'RGB')
        if (t // 6) % 2 == 0:
            pixfont.draw_pil(im, '}', 84, 184, (252, 252, 252))
        pixfont.draw_pil(im, 'NEW GAME', 96, 184, (252, 252, 252))
        pixfont.draw_pil(im, 'CONTINUE', 96, 196, (188, 188, 188))
        if (t // 12) % 2 == 0:
            pixfont.draw_pil(im, 'PRESS START', (W - pixfont.width('PRESS START')) // 2, 162, (252, 252, 252), shadow=(0, 0, 0))
        out.append(im)
    return out

def export():
    return [{'name': 'title_screen', 'frames': [], 'images': [f.convert('RGBA') for f in render_frames()],
             'anchor': (0, 0), 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/title'
    f = render_frames(1)[0]
    f.resize((W * 3, H * 3), Image.NEAREST).save(out + '.png')
    print(era.check(f, 'nes'))
