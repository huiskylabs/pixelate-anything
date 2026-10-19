"""Assemble image A (the 2x2 poster, every panel at 3x on a dark mat, pixfont captions) and image B
(the 16-bit panel alone at 4x). Run after the four panel scripts: python3 art/poster.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from PIL import Image
from common import OUT
import pixfont

S = 3                                   # every panel at the same whole scale
MAT, FRAME = (21, 19, 28), (46, 42, 56)
CAP, TITLE = (150, 144, 166), (214, 208, 228)
M, G, CAPH = 48, 48, 21 + 24            # outer margin, gutter, caption band (3x glyph + gap)

def text(s, scale, rgb):
    w = pixfont.width(s)
    im = Image.new('RGBA', (w + 1, 8), (0, 0, 0, 0))
    pixfont.draw_pil(im, s, 0, 0, rgb + (255,))
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)

def main():
    cells = [('panel-gb', '4-SHADE HANDHELD'), ('panel-nes', '8-BIT CONSOLE'),
             ('panel-snes', '16-BIT CONSOLE'), ('panel-gba', '32-BIT HANDHELD')]
    ims = [Image.open(OUT / ('%s.png' % n)).convert('RGB') for n, _ in cells]
    ims = [im.resize((im.width * S, im.height * S), Image.NEAREST) for im in ims]
    colw = [max(ims[0].width, ims[2].width), max(ims[1].width, ims[3].width)]
    rowh = [max(ims[0].height, ims[1].height), max(ims[2].height, ims[3].height)]
    title = text('ONE MORNING, FOUR MACHINES', S, TITLE)
    top = M + title.height + 30
    Wp = M + colw[0] + G + colw[1] + M
    Hp = top + rowh[0] + CAPH + G + rowh[1] + CAPH + M - 12
    poster = Image.new('RGB', (Wp, Hp), MAT)
    poster.paste(title, ((Wp - title.width) // 2, M), title)
    for i, (im, (_, cap)) in enumerate(zip(ims, cells)):
        col, row = i % 2, i // 2
        cx = M + (colw[0] + G) * col
        cy = top + (rowh[0] + CAPH + G) * row
        x = cx + (colw[col] - im.width) // 2
        y = cy + rowh[row] - im.height                       # panels stand on a shared floor per row
        poster.paste(FRAME, (x - S, y - S, x + im.width + S, y + im.height + S))
        poster.paste(im, (x, y))
        t = text(cap, S, CAP)
        poster.paste(t, (cx + (colw[col] - t.width) // 2, cy + rowh[row] + 15), t)
    poster.save(OUT / '05-a.png')
    snes = Image.open(OUT / 'panel-snes.png').convert('RGB')
    snes.resize((snes.width * 4, snes.height * 4), Image.NEAREST).save(OUT / '05-b.png')
    print('05-a.png', poster.size, '05-b.png', (snes.width * 4, snes.height * 4))

if __name__ == '__main__':
    main()
