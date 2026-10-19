"""Rooftop Run: an original 8-bit side-scrolling platformer screen, made under NES-style limits
(tools/era.py 'nes': the 2C02 master palette, 256x224, 3-colour sprites, few colours per block).

A courier runs over San Francisco rooftops at sunset: the Transamerica Pyramid on the far
skyline, a black mid-ground skyline with lit windows scrolling at half speed, brick rooftops with
chimneys, AC units, a neon sign and a fire escape; pigeons take off as she passes; fortune
cookies hang over the gaps. 160 frames at 20 fps, the camera scrolls 2 px a frame, and every
layer repeats exactly over the loop (near 320 px, mid 160 px, far fixed).
"""
import math, sys, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parents[2]
sys.path.insert(0, str(KIT / 'tools'))
import colorlib as cl
import pixfont

W, H = 256, 224
FRAMES, FPS, SPEED = 160, 20, 2
PERIOD = FRAMES * SPEED                   # 320 px of level per loop

# NES master palette entries, by role
C = {k: np.array(cl.hex_to_rgb(v), np.uint8) for k, v in {
    'K': '#000000', 'W': '#fcfcfc', 'g1': '#7c7c7c', 'g2': '#bcbcbc',
    's0': '#6844fc', 's1': '#9878f8', 's2': '#f878f8', 's3': '#f87858', 's4': '#fca044', 's5': '#f8d878',
    'sun': '#fce0a8', 'far': '#4428bc', 'farlit': '#f878f8',
    'brick': '#a81000', 'brick2': '#e45c10', 'lit': '#fca044', 'win': '#f8b800', 'win2': '#ac7c00', 'pane': '#0000bc',
    'neon': '#f85898', 'leaf': '#00a800',
    'hero': '#00a800', 'skin': '#fce0a8', 'bag': '#f8b800', 'scarf': '#e40058',
    'ck0': '#ac7c00', 'ck1': '#f8b800', 'ck2': '#fce0a8', 'heart': '#e40058',
}.items()}

class Layer:
    def __init__(self, w, h):
        self.rgb = np.zeros((h, w, 3), np.uint8)
        self.a = np.zeros((h, w), bool)
    def rect(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(self.rgb.shape[1], int(x1)), min(self.rgb.shape[0], int(y1))
        if x1 > x0 and y1 > y0:
            self.rgb[y0:y1, x0:x1] = C[c]; self.a[y0:y1, x0:x1] = True
    def px(self, x, y, c):
        if 0 <= x < self.rgb.shape[1] and 0 <= y < self.rgb.shape[0]:
            self.rgb[y, x] = C[c]; self.a[y, x] = True
    def set(self, x, y, c):
        self.px(int(x), int(y), c)

def stamp(layer, art, key, x, y, flip=False):
    rows = [r for r in art.strip('\n').split('\n')]
    for j, r in enumerate(rows):
        if flip:
            r = r[::-1]
        for i, ch in enumerate(r):
            if ch != '.':
                layer.px(x + i, y + j, key[ch])

# ---------------------------------------------------------------- sprites (3 colours + an overlay)
HEAD = """
......oooo......
.....oooooo.....
....ooooooooo...
..oooooooosss...
.oo.oooosssos...
.o...oossssss...
.....ossssss....
......sssss.....
.....rrrrrr.....
....gggrrrgg....
...gggggggggg...
"""
TORSO = {   # the arm swings: forward, down, back
    'f': "..ygggggggggs...\n..yyggggggggs...\n..yyggggggg.....\n...yggggggg.....\n....ggggggg.....",
    'd': "..yggggggggg....\n..yyggggggsg....\n..yyggggggsg....\n...ygggggggs....\n....ggggggg.....",
    'b': "..ygggggggggg...\n.syyggggggggg...\n.syyggggggg.....\n...yggggggg.....\n....ggggggg.....",
}
LEGS = {
    'A': ".....oooooo.....\n.....ooo.ooo....\n....ooo...ooo...\n...ooo.....ooo..\n..ooo.......ooo.\n.www.........ww.\nwww..........www\n................",
    'B': ".....oooooo.....\n......oooooo....\n.....ooo..ooo...\n....ooo....oo...\n...ooo.....oo...\n..www......www..\n.www.......www..\n................",
    'C': ".....oooooo.....\n.....oooooo.....\n......oooo......\n......oooo......\n.....ooooo......\n.....www.ooo....\n.....www..www...\n................",
    'D': ".....oooooo.....\n....oooooooooo..\n...ooo.....ooo..\n..ooo......oww..\n.ooo.......ww...\nwww.............\nww..............\n................",
    'U': ".....oooooo.....\n....ooooooooo...\n....ooo...oooo..\n...www.....www..\n...ww.......ww..\n................\n................\n................",
    'F': ".....oooooo.....\n.....ooo.ooo....\n.....oo...oo....\n.....oo...oo....\n....ooo...ooo...\n....www...www...\n...www.....www..\n................",
}
HERO_KEY = {'o': 'K', 's': 'skin', 'g': 'hero', 'r': 'scarf', 'y': 'bag', 'w': 'W'}
RUN = [('A', 'f', 0), ('B', 'd', 1), ('C', 'b', 0), ('D', 'd', -1)]

def hero_art(legs, arm, bob):
    rows = [r for r in HEAD.strip('\n').split('\n')] + TORSO[arm].split('\n') + LEGS[legs].split('\n')
    if bob > 0:
        rows = ['.' * 16] * bob + rows[:24 - bob]
    elif bob < 0:
        rows = rows[-bob:] + ['.' * 16] * (-bob)
    return '\n'.join(rows)

PIGEON_SIT = ["""
....ooo...
...ogggo..
...ogoggo.
..oKgggo..
.oKKKKKo..
oKKKKKo...
.ooooo....
..o..o....
""", """
..........
....ooo...
...ogggo..
...ogoggo.
.oKgggo...
oKKKKKo...
.ooooo....
..o..o....
"""]
PIGEON_FLY = ["""
o.......o.
oo.....oo.
.oo...oo..
..ogggo...
..oKKKKog.
...oooo...
""", """
...ooo....
..ogggo...
.oKKKKog..
oo.oo.oo..
o......o..
..........
"""]
PIG_KEY = {'o': 'K', 'g': 'g2', 'K': 'g1'}

COOKIE = """
..dddd..
.dyyyyd.
dyLLyyyd
dyLyyyyd
dyyyyddd
.ddddd..
"""
COOKIE_KEY = {'d': 'ck0', 'y': 'ck1', 'L': 'ck2'}
SPARK = ["..W..\n.W.W.\n..W..", "W...W\n.....\n..W..\n.....\nW...W"]

# ---------------------------------------------------------------- the level (one 320 px period)
BUILDINGS = [  # x0, x1, roof y, window rows, style
    (0, 96, 160, 'brick'), (120, 208, 136, 'brick2'), (224, 304, 176, 'brick')]
JUMPS = [(78, 126, 160, 136, 40), (196, 236, 136, 176, 28), (290, 334, 176, 160, 32)]

def roof_at(x):
    x %= PERIOD
    for x0, x1, ry, _ in BUILDINGS:
        if x0 <= x < x1:
            return ry
    return None

def hero_state(t):
    """foot position and pose of the hero at frame t (world x is camera + 64)"""
    wx = SPEED * t + 64
    xp = wx % PERIOD
    for x0, x1, y0, y1, hgt in JUMPS:
        a, b = x0, x1
        xx = xp if xp >= a or b <= PERIOD else xp + PERIOD
        if a <= xx < b:
            s = (xx - a) / (b - a)
            y = y0 + (y1 - y0) * s - hgt * 4 * s * (1 - s)
            return wx, y, 'jump_up' if s < 0.5 else 'jump_down'
        if b > PERIOD and xp < b - PERIOD:
            s = (xp + PERIOD - a) / (b - a)
            y = y0 + (y1 - y0) * s - hgt * 4 * s * (1 - s)
            return wx, y, 'jump_up' if s < 0.5 else 'jump_down'
    return wx, roof_at(xp), 'run'

def draw_building(L, x0, x1, ry, style, base):
    """brick walls, a lit coping, windows, and the props on the roof; x in strip coordinates"""
    b, m = ('brick', 'K') if style == 'brick' else ('brick2', 'brick')
    L.rect(x0, ry, x1, H, b)
    for y in range(ry + 6, H, 6):                                   # brick courses and joints
        L.rect(x0, y, x1, y + 1, m)
        off = 0 if (y // 6) % 2 else 4
        for x in range(x0 + off, x1, 8):
            L.rect(x, y - 5, x + 1, y, m)
    L.rect(x0, ry, x1, ry + 1, 'lit')                               # sunlit coping
    L.rect(x0, ry + 1, x1, ry + 4, 'brick2' if style == 'brick' else 'lit')
    L.rect(x0, ry + 4, x1, ry + 5, 'K')
    L.rect(x0, ry, x0 + 1, H, 'K'); L.rect(x1 - 1, ry, x1, H, 'K')  # outline
    for wy in range(ry + 14, H - 6, 26):                            # windows: frame, lit or dark panes, sill
        for wx in range(x0 + 8, x1 - 14, 20):
            lit = ((wx * 7 + wy * 3 + base) // 20) % 3 != 0
            L.rect(wx - 1, wy - 1, wx + 11, wy + 13, 'K')
            L.rect(wx, wy, wx + 10, wy + 12, 'win' if lit else 'pane')
            L.rect(wx + 4, wy, wx + 6, wy + 12, 'K'); L.rect(wx, wy + 5, wx + 10, wy + 6, 'K')
            if lit:
                L.rect(wx + 1, wy + 1, wx + 3, wy + 2, 'W')
            L.rect(wx - 2, wy + 13, wx + 12, wy + 14, 'lit')

def build_near():
    """two periods side by side so any 256 px window can be cut from it"""
    L = Layer(PERIOD * 2, H)
    for rep in (0, PERIOD):
        for i, (x0, x1, ry, style) in enumerate(BUILDINGS):
            draw_building(L, x0 + rep, x1 + rep, ry, style, i * 31)
        # roof props
        x = rep
        L.rect(x + 12, 140, x + 26, 160, 'brick'); L.rect(x + 11, 138, x + 27, 141, 'K'); L.rect(x + 12, 139, x + 26, 140, 'lit')
        for y in range(146, 160, 5):
            L.rect(x + 12, y, x + 26, y + 1, 'K')
        L.rect(x + 46, 148, x + 66, 160, 'g1'); L.rect(x + 46, 148, x + 66, 149, 'g2')        # AC unit
        L.rect(x + 45, 147, x + 67, 148, 'K'); L.rect(x + 45, 147, x + 46, 160, 'K'); L.rect(x + 66, 147, x + 67, 160, 'K')
        for gx in range(x + 49, x + 63, 2):
            L.rect(gx, 151, gx + 1, 158, 'K')
        L.rect(x + 86, 132, x + 87, 160, 'g1'); L.rect(x + 82, 138, x + 91, 139, 'g1'); L.rect(x + 83, 144, x + 90, 145, 'g1')
        # B2: a neon sign hanging on the front, and a skylight
        L.rect(x + 176, 150, x + 194, 206, 'K')
        for i, ch in enumerate('EAT'):
            pixfont.draw(L, ch, x + 183 - 1, 156 + i * 14, 'neon')
        L.rect(x + 140, 126, x + 164, 136, 'g2'); L.rect(x + 139, 125, x + 165, 126, 'K')
        for gx in range(x + 142, x + 164, 6):
            L.rect(gx, 127, gx + 4, 135, 'pane')
        # B3: a fire escape on the wall and a rooftop garden
        for fy in (190, 214):
            L.rect(x + 232, fy, x + 268, fy + 2, 'K')
            for rx in range(x + 232, x + 268, 4):
                L.rect(rx, fy - 8, rx + 1, fy, 'K')
            L.rect(x + 232, fy - 9, x + 268, fy - 8, 'K')
        for k in range(5):
            L.rect(x + 238 + k * 4, 199 - k * 3, x + 240 + k * 4, 200 - k * 3, 'K')
        for px_ in range(x + 270, x + 298, 9):
            L.rect(px_, 170, px_ + 7, 176, 'brick2'); L.rect(px_, 170, px_ + 7, 171, 'K')
            L.rect(px_ + 1, 164, px_ + 6, 170, 'leaf'); L.px(px_ + 3, 163, 'leaf')
    return L

def build_mid():
    """the black skyline with lit windows, 160 px period, three copies"""
    L = Layer(480, H)
    tops = [118, 132, 104, 126, 140, 112, 128, 120]
    widths = [22, 18, 26, 16, 20, 24, 18, 16]
    for rep in (0, 160, 320):
        x = rep
        for i, (tp, w) in enumerate(zip(tops, widths)):
            L.rect(x, tp, x + w, H, 'K')
            for wy in range(tp + 5, H, 6):
                for wx in range(x + 3, x + w - 3, 4):
                    h = (wx * 13 + wy * 7 + i * 5) % 11
                    if h < 3:
                        L.rect(wx, wy, wx + 2, wy + 2, 'win' if h else 'win2')
            if i % 3 == 0:
                L.rect(x + w // 2, tp - 10, x + w // 2 + 1, tp, 'K')
            x += w
    return L

def build_far_and_sky():
    sky = np.zeros((H, W, 3), np.uint8)
    bands = [('s0', 16), ('s1', 46), ('s2', 70), ('s3', 92), ('s4', 110), ('s5', 126)]
    for y in range(H):
        cur = bands[0][0]
        for name, start in bands:
            if y >= start:
                cur = name
        sky[y, :] = C[cur]
        for i, (name, start) in enumerate(bands[1:], 1):        # 2-row checker dither at each edge
            if start - 2 <= y < start:
                for x in range(W):
                    if (x + y) % 2 == 0:
                        sky[y, x] = C[name]
    far = Layer(W, H)
    cx, cy, r = 186, 124, 24                                    # the setting sun, banded
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and not (y > cy and (y - cy) % 5 in (0, 1)):
                far.px(x, y, 'sun' if (x - cx) ** 2 + (y - cy) ** 2 <= (r - 6) ** 2 else 's5')
    base = 150
    for x in range(W):                                          # hills behind the city
        hh = int(10 + 6 * math.sin(x / 23) + 4 * math.sin(x / 9 + 1))
        far.rect(x, base - hh, x + 1, H, 'far')
    towers = [(8, 12, 30), (24, 10, 22), (38, 14, 38), (60, 9, 26), (118, 12, 34), (134, 16, 44), (154, 10, 28), (214, 12, 36), (232, 14, 24)]
    for x, w, h in towers:
        far.rect(x, base - h, x + w, H, 'far')
        for wy in range(base - h + 4, base, 5):
            for wx in range(x + 2, x + w - 2, 3):
                if (wx * 5 + wy * 3) % 7 == 0:
                    far.px(wx, wy, 'farlit')
    px0, top, half = 92, 70, 9                                  # the Pyramid and its spire
    for y in range(top, base):
        f = (y - top) / (base - top)
        hw = 1 + f * half
        far.rect(int(px0 - hw), y, int(px0 + hw) + 1, y + 1, 'far')
    far.rect(px0, top - 14, px0 + 1, top, 'far')
    far.rect(px0 - 4, top + 16, px0 - 2, top + 34, 'far'); far.rect(px0 + 3, top + 16, px0 + 5, top + 36, 'far')
    return sky, far

def compose(t, sky, far, mid, near):
    img = sky.copy()
    for L, off in ((far, 0), (mid, (t * SPEED // 2) % 160), (near, (t * SPEED) % PERIOD)):
        a = L.a[:, off:off + W]; rgb = L.rgb[:, off:off + W]
        img[a] = rgb[a]
    spr = Layer(W, H)
    cam = t * SPEED
    # cookies: over each jump's apex and in a row on the low roof; gone (with a sparkle) once passed
    hx, hy, pose = hero_state(t)
    cookies = [((a + b) / 2, min(y0, y1) - hgt + (y0 + y1) / 2 - min(y0, y1) - 22) for a, b, y0, y1, hgt in JUMPS] + [(250, 160), (262, 160), (274, 160)]
    for rep in (-PERIOD, 0, PERIOD, 2 * PERIOD):
        for cx_, cy_ in cookies:
            wx = cx_ + rep
            sx = int(wx - cam)
            if -10 < sx < W + 10:
                passed = hx - wx
                bob = 1 if (t // 4) % 2 else 0
                if passed < -2:
                    stamp(spr, COOKIE, COOKIE_KEY, sx - 4, int(cy_) - 3 + bob)
                elif passed < 10:
                    stamp(spr, SPARK[int(passed // 6) % 2], {'W': 'W'}, sx - 2, int(cy_) - 2)
    # pigeons: one on the chimney takes off as the hero comes; one crosses the sky
    for rep in (-PERIOD, 0, PERIOD):
        px_, py_ = 18 + rep, 131
        k = (hx - (30 + rep)) / 2
        if k < 0:
            stamp(spr, PIGEON_SIT[(t // 6) % 2], PIG_KEY, int(px_ - cam), py_)
        elif k < 120:
            stamp(spr, PIGEON_FLY[(t // 2) % 2], PIG_KEY, int(px_ - cam + 1.6 * k), int(py_ - 1.3 * k))
    gx = int(W + 20 - (t * (W + 40) / FRAMES)) % (W + 40) - 20
    stamp(spr, PIGEON_FLY[(t // 3) % 2], PIG_KEY, gx, 48 + int(3 * math.sin(t / 8)), flip=True)
    # the hero
    if pose == 'run':
        legs, arm, bob = RUN[(t // 3) % 4]
        art = hero_art(legs, arm, bob)
    else:
        art = hero_art('U' if pose == 'jump_up' else 'F', 'b' if pose == 'jump_up' else 'f', 0)
    stamp(spr, art, HERO_KEY, 64 - 8, int(round(hy)) - 23)
    img[spr.a] = spr.rgb[spr.a]
    # HUD
    hud = Layer(W, H)
    hud.rect(0, 0, W, 16, 'K')
    for i in range(3):
        pixfont.draw(hud, '*', 8 + i * 7, 5, 'heart')
    stamp(hud, COOKIE, COOKIE_KEY, 64, 5)
    pixfont.draw(hud, 'x12', 76, 5, 'W')
    pixfont.draw(hud, 'ROOFTOP RUN', 104, 5, 's5')
    pixfont.draw(hud, '004250', W - 8 - pixfont.width('004250'), 5, 'W')
    img[hud.a] = hud.rgb[hud.a]
    return img

def render_frames(frames=FRAMES):
    sky, far = build_far_and_sky()
    mid, near = build_mid(), build_near()
    return [Image.fromarray(compose(t, sky, far, mid, near), 'RGB') for t in range(frames)]

def export():
    frames = [f.convert('RGBA') for f in render_frames()]
    return [{'name': 'rooftop_run', 'frames': [], 'images': frames, 'anchor': (0, 0), 'fps': FPS, 'kind': 'scene'}]

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/rooftop'
    fr = render_frames(80)
    for t in (0, 14, 40, 70):
        fr[t].resize((W * 3, H * 3), Image.NEAREST).save('%s-%02d.png' % (out, t))
    # the hero's poses, big
    sheet = Layer(16 * 7 + 6 * 8, 24)
    for i, (legs, arm, bob) in enumerate(RUN + [('U', 'b', 0), ('F', 'f', 0)]):
        stamp(sheet, hero_art(legs, arm, bob), HERO_KEY, i * 22, 0)
    im = Image.fromarray(np.where(sheet.a[..., None], sheet.rgb, np.array([60, 60, 80], np.uint8)), 'RGB')
    im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(out + '-hero.png')
