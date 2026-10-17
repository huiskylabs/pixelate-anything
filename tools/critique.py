#!/usr/bin/env python3
"""pixelate critique [FRAME.png] --brief brief.md [--block BLOCKIN.png] [--prev PREV.md] [--style S]

Prints the prompt for an independent art director: a separate agent (or model) that did not write
the brief or draw the frame. With no FRAME (or --brief-only) it grades the brief before anything is
drawn, with the greyscale block-in if --block names one; with a FRAME it grades the still. --prev
hands it the previous critique, so it first checks each earlier fix as fixed, partly or not. The
prompt holds references/art-director.md (the part for that stage), the brief's request, section 0,
signature elements and, for a still, its rules, scene and light list; and the paths to read: the
brief, the bar (docs/lantern-isle-winter.png and its brief) and, for a still, the frame plus a 480 px
nearest-neighbour thumbnail and its greyscale written next to it. Send the printed text to a fresh
agent, then follow the brief or still review budget in references/delivery.md#art-director. This
command generates one prompt per call; it does not orchestrate or cap the review loop.
"""
import argparse, os, pathlib, re, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
RUBRIC = KIT / 'references' / 'art-director.md'
BAR = KIT / 'docs' / 'lantern-isle-winter.png'
BAR_BRIEF = KIT / 'examples' / 'lantern-isle' / 'BRIEF.md'

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

def rubric(stage):
    """art-director.md for one stage: a brief drops the still's "How to look" section, a still drops
    "Grading a brief"""
    text = RUBRIC.read_text(encoding='utf-8').strip().replace('Read this only if you are the art director. ', '')
    drop = 'How to look' if stage == 'brief' else 'Grading a brief'
    return re.sub(r'^## %s.*?(?=^## )' % re.escape(drop), '', text, flags=re.M | re.S)

def sections(text, names):
    """the named numbered sections of a brief (## 3. Art direction rules ...), as one Markdown block"""
    out = []
    for m in re.finditer(r'^## \d+\.\s*([^\n]*)\n(.*?)(?=^## |\Z)', text, re.M | re.S):
        if any(m.group(1).lower().startswith(n.lower()) for n in names):
            out.append('### ' + m.group(1).strip() + '\n\n' + m.group(2).strip())
    return '\n\n'.join(out)

def prompt(frame, brief, style='', width=480, out=None, prev=None, block=None):
    """the art-director prompt; frame None or '' grades the brief before anything is drawn (with the
    block-in image `block` if given); prev is the previous critique's file, whose fixes it checks first"""
    text = pathlib.Path(brief).read_text(encoding='utf-8')
    req, sec0, sig, bstyle = brief_parts(text)
    style = style or bstyle
    bp = pathlib.Path(os.path.abspath(brief))
    if frame:
        frame = pathlib.Path(os.path.abspath(frame))
        tp, gp, size, tw = thumbnails(frame, width, out)
        L = ['You are the independent art director for one pixel-art still. You did not draw it. Judge it; '
             'do not edit any file. Look at every image below with your image-reading tool before you grade.',
             '', '## Look at', '',
             '- Thumbnail (%d px wide, nearest neighbour): %s' % (tw, tp),
             '- Greyscale thumbnail: %s' % gp,
             '- Frame at delivered size (%dx%d): %s' % (size[0], size[1], frame),
             '- The bar, Lantern Isle winter: %s' % BAR,
             '- The brief: %s' % bp]
        L += ['', 'The painter\'s own report or grade is not evidence: judge only what you see.']
    else:
        L = ['You are the independent art director for one pixel-art brief, before anything is drawn. You did not '
             'write it. Judge it as the picture a cold run would draw from it; do not edit any file. Read the whole '
             'brief and the bar brief, and look at the bar image, before you grade. Use "Grading a brief" below.',
             '', '## Read', '',
             '- The brief, in full: %s' % bp,
             '- The bar brief, Lantern Isle: %s' % BAR_BRIEF,
             '- The bar image, Lantern Isle winter: %s' % BAR]
        if block:
            L.append('- The greyscale block-in (flat value shapes at native size, drawn from the brief): %s; judge '
                     'the hero, the plane shares, the masses and the value plan on it as well'
                     % os.path.abspath(block))
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
    if frame:
        more = sections(text, ['Art direction', 'The scene', 'Light list'])
        if more:
            L += ['', 'The brief\'s rules, scene and lights:', '', more]
    L += ['', 'Every fix you propose must agree with the brief\'s light direction, wind and physics.']
    if prev:
        L += ['', '## The previous critique', '', pathlib.Path(prev).read_text(encoding='utf-8').strip(), '',
              'Before anything else, check each of its fixes in what you see now. Start your block with one line '
              '`PRIOR FIXES: 1=fixed|partly|not 2=... (what is still missing)`.']
    L += ['', '## Rubric', '', rubric('still' if frame else 'brief'), '',
          'Return exactly the block under "What you return", nothing else.']
    return '\n'.join(L) + '\n'

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pixelate critique', description=__doc__.split('\n\n')[1])
    ap.add_argument('frame', nargs='?', default='', help='the still; leave it out to grade the brief')
    ap.add_argument('--brief', required=True)
    ap.add_argument('--brief-only', action='store_true', help='grade the brief (the same as leaving out FRAME)')
    ap.add_argument('--block', default=None, help='a greyscale block-in of the layout, for the brief stage')
    ap.add_argument('--prev', default=None, help='the previous critique: its fixes are checked first')
    ap.add_argument('--style', default='')
    ap.add_argument('--width', type=int, default=480, help='thumbnail width (default 480)')
    ap.add_argument('--out', default=None, help='folder for the thumbnails (default: next to the frame)')
    a = ap.parse_args(argv)
    if a.brief_only:
        a.frame = ''
    for p in (a.frame, a.brief, a.block, a.prev):
        if p and not pathlib.Path(p).exists():
            sys.exit('no such file: %s' % p)
    sys.stdout.write(prompt(a.frame, a.brief, a.style, a.width, a.out, a.prev, a.block))

if __name__ == '__main__':
    main()
