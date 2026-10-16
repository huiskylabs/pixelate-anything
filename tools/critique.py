#!/usr/bin/env python3
"""pixelate critique FRAME.png --brief brief.md [--style S] [--width 480] [--out DIR]

Prints the prompt for an independent art director: a separate agent (or model) that did not draw
the frame. It holds references/art-director.md, the brief's request, section 0 and signature
elements, and the paths to look at: the frame, a 480 px nearest-neighbour thumbnail and its
greyscale written next to it, and the bar image docs/lantern-isle-winter.png. Send the printed text
to a fresh agent, apply the fixes it returns, gate again, repeat until it grades A.
"""
import argparse, pathlib, re, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
RUBRIC = KIT / 'references' / 'art-director.md'
BAR = KIT / 'docs' / 'lantern-isle-winter.png'

def thumbnails(frame, width=480, out=None):
    """write FRAME.thumb.png (width px, nearest neighbour) and FRAME.thumb-grey.png next to the frame,
    or into `out`; return both paths"""
    from PIL import Image
    im = Image.open(frame).convert('RGB')
    w = min(width, im.width)
    h = max(1, round(im.height * w / im.width))
    small = im.resize((w, h), Image.NEAREST)
    d = pathlib.Path(out) if out else frame.parent
    d.mkdir(parents=True, exist_ok=True)
    tp = d / (frame.stem + '.thumb.png')
    gp = d / (frame.stem + '.thumb-grey.png')
    small.save(tp)
    small.convert('L').save(gp)
    return tp, gp, im.size, w

def brief_parts(text):
    """the request line, section 0, the style named in it and every signature-elements line"""
    req = re.search(r'^Request:\s*(.+)$', text, re.M)
    sec0 = re.search(r'^## 0\.[^\n]*\n(.*?)(?=^## )', text, re.M | re.S)
    sig = [m.strip() for m in re.findall(r'^\s*-?\s*\**signature elements?\**\s*:?\s*(.+)$', text, re.M | re.I)]
    style = re.search(r'\*\*style\*\*:\s*`([\w-]+)`', text) or re.search(r'^- Style `([\w-]+)`', text, re.M)
    return (req.group(1).strip() if req else ''), (sec0.group(1).strip() if sec0 else ''), sig, \
        (style.group(1) if style else '')

def prompt(frame, brief, style='', width=480, out=None):
    frame = pathlib.Path(frame).resolve()
    tp, gp, size, tw = thumbnails(frame, width, out)
    text = pathlib.Path(brief).read_text(encoding='utf-8')
    req, sec0, sig, bstyle = brief_parts(text)
    style = style or bstyle
    rubric = RUBRIC.read_text(encoding='utf-8').strip().replace('Read this only if you are the art director. ', '')
    L = ['You are the independent art director for one pixel-art still. You did not draw it. Judge it; '
         'do not edit any file. Look at every image below with your image-reading tool before you grade.',
         '', '## Look at', '',
         '- Thumbnail (%d px wide, nearest neighbour): %s' % (tw, tp),
         '- Greyscale thumbnail: %s' % gp,
         '- Frame at delivered size (%dx%d): %s' % (size[0], size[1], frame),
         '- The bar, Lantern Isle winter: %s' % BAR,
         '- The brief: %s' % pathlib.Path(brief).resolve()]
    if style:
        L.append('- Style preset: `%s` (its rules: `pixelate style %s`)' % (style, style))
    L += ['', '## What the brief promised', '']
    if req:
        L.append('Request: ' + req)
    sec0 = re.sub(r'^Defaults I picked.*\n+', '', sec0)
    if not sec0:   # an older brief: its opening paragraphs stand in for section 0
        body = text.split('\n---\n', 1)[-1] if '\n---\n' in text else text
        sec0 = '(no section 0; the brief opens:)\n\n' + body.strip()[:1500]
    L += ['', sec0, '']
    L.append('Signature elements: ' + (' | '.join(sig) if sig else '(none named; judge what the scene owns)'))
    L += ['', '## Rubric', '', rubric, '',
          'Return exactly the block under "What you return", nothing else.']
    return '\n'.join(L) + '\n'

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pixelate critique', description=__doc__.split('\n\n')[1])
    ap.add_argument('frame')
    ap.add_argument('--brief', required=True)
    ap.add_argument('--style', default='')
    ap.add_argument('--width', type=int, default=480, help='thumbnail width (default 480)')
    ap.add_argument('--out', default=None, help='folder for the thumbnails (default: next to the frame)')
    a = ap.parse_args(argv)
    for p in (a.frame, a.brief):
        if not pathlib.Path(p).exists():
            sys.exit('no such file: %s' % p)
    sys.stdout.write(prompt(a.frame, a.brief, a.style, a.width, a.out))

if __name__ == '__main__':
    main()
