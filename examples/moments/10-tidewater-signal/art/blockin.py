"""Greyscale block-in of image A at native size (270x480): one flat grey per value group.

darkest: the room near plane (walls, frame, rails, sill nosing, wainscot), the far rock and tower,
         the antenna
dark:    the cloud deck (upper sky), the sea, the sill top and the cassette door
mid:     the pale gap of sky under the cloud deck, the radio cabinet, the mug and the logbook
bright:  the dial window (the hero's light)
"""
import sys, pathlib
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
from PIL import Image
import colorlib as cl

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / 'out'
W, H = 270, 480

def grey(L):
    return np.array(cl.oklab_to_rgb(cl.oklch(L, 0.0, 0.0)), dtype=float).clip(0, 255).round().astype(np.uint8)

G = {'darkest': grey(0.15), 'dark': grey(0.26), 'mid': grey(0.40), 'bright': grey(0.90)}

def main():
    lab = np.full((H, W), 'room', dtype=object)
    def box(x0, y0, x1, y1, name):          # inclusive box
        lab[y0:y1 + 1, x0:x1 + 1] = name
    box(26, 0, 251, 235, 'deck')          # the cloud deck, dark
    for y in range(186, 236):             # the pale gap under the deck, its top edge walking
        x0 = 26
        lift = [0, 2, 3, 1, 0, 4, 6, 5, 3, 2]
        for i in range(10):
            xa, xb = 26 + i * 23, 26 + (i + 1) * 23
            if y >= 186 + lift[i]:
                lab[y, xa:min(xb, 252)] = 'glow'
    box(26, 236, 251, 333, 'sea')
    box(26, 160, 251, 169, 'room')        # meeting rail
    box(128, 157, 141, 172, 'room')       # the sash lock straddles the rail
    box(196, 230, 250, 242, 'rock')
    box(214, 182, 227, 233, 'rock')       # the tower, a dark mass on the horizon
    box(14, 342, 259, 397, 'sill')
    box(4, 398, 265, 409, 'room')         # nosing
    box(56, 284, 214, 386, 'radio')
    box(66, 297, 144, 320, 'dial')
    box(150, 277, 177, 283, 'props')      # a spare cassette case lying on the radio's top
    box(68, 326, 120, 368, 'sill')        # the cassette door reads as a dark window
    box(222, 362, 240, 384, 'props')      # mug
    box(14, 374, 70, 401, 'props')        # logbook, its front corner over the nosing
    for i in range(80):                   # the antenna, bent at its second section
        y = 283 - i
        x = 72 + (i * 10) // 48 if i < 48 else 82 - ((i - 48) * 4) // 32
        lab[y, x:x + 2] = 'room'
    for y in range(380, 452):             # the power cord from the radio's foot over the nosing to the socket
        xc = 190 + (1 if y > 420 else 0)
        lab[y, xc:xc + 2] = 'sill' if y >= 398 else 'room'
    box(186, 450, 195, 461, 'props')      # socket
    box(128, 396, 133, 399, 'sill')       # a worn notch in the nosing
    band = {'room': 'darkest', 'rock': 'darkest', 'sea': 'dark', 'sill': 'dark', 'deck': 'dark', 'glow': 'mid',
            'radio': 'mid', 'props': 'mid', 'dial': 'bright'}
    img = np.zeros((H, W, 3), np.uint8)
    for k, b in band.items():
        img[lab == k] = G[b]
    OUT.mkdir(exist_ok=True)
    Image.fromarray(img).save(OUT / 'blockin-a.png')
    tot = W * H
    for k in band:
        print('%-6s %5.1f%%  (%s)' % (k, 100 * (lab == k).sum() / tot, band[k]))
    for b in G:
        print('band %-8s %5.1f%%' % (b, 100 * sum((lab == k).sum() for k in band if band[k] == b) / tot))

if __name__ == '__main__':
    main()
