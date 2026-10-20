#!/usr/bin/env python3
"""pixelate critique [FRAME.png] --brief brief.md [--role ROLE] [--consult NOTE.md] [--prev LEAD.md]

Prints one visual review prompt. The default lead art director grades a full brief (with an optional
--block) or still; --prev supplies only its previous graded critique. Choose composition, lighting,
set or character with --role for scoped observations without a grade. A later lead call may receive
up to two specialist notes with --consult, distinct from --prev. The prompt names the brief and bar;
for a still it writes a nearest-neighbour thumbnail and greyscale next to the frame. Send it to a
separate agent that did not write or draw the work. For a still, the prompt carries the judge's
detector findings (`pixelate judge`) and an overlay of their boxes as a checklist. --run sends the
prompt to a separate model process itself (the `claude` CLI, or the command in PIXELATE_CRITIC_CMD,
which reads the prompt on stdin) and saves the critique as critique-<frame>-<role>-rN.md for the next
round's --prev; --log adds it to the judge's corpus log. The caller tracks the graded rounds (one per stage by default)
and total specialist consults per artifact (references/delivery.md#art-director); this command does
not enforce a session budget.
"""
import argparse, os, pathlib, re, shlex, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

KIT = pathlib.Path(__file__).resolve().parent.parent
RUBRIC = KIT / 'references' / 'art-director.md'
SPECIALIST_RUBRIC = KIT / 'references' / 'visual-specialists.md'
MUSIC_RUBRIC = KIT / 'references' / 'music-review.md'
ROLES = ('lead', 'composition', 'lighting', 'set', 'character')
BAR = KIT / 'docs' / 'lantern-isle-winter.png'
BAR_BRIEF = KIT / 'library' / 'lantern-isle' / 'brief.md'

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

def specialist_scope(role):
    text = SPECIALIST_RUBRIC.read_text(encoding='utf-8').strip()
    scope = next(line for line in text.splitlines() if line.startswith(f'- **{role}:** '))
    return scope + '\n\n' + text.rsplit('\n\n', 1)[-1]

def prompt(frame, brief, style='', width=480, out=None, prev=None, block=None, role='lead', consults=None):
    """Visual review prompt. Only the lead grades; consults are specialist notes for the lead."""
    if role not in ROLES:
        raise ValueError('role must be one of: ' + ', '.join(ROLES))
    consults = list(consults or [])
    if len(consults) > 2:
        raise ValueError('at most two specialist consult notes per visual artifact')
    if role != 'lead' and (consults or prev):
        raise ValueError('only the lead may receive --consult or --prev')
    text = pathlib.Path(brief).read_text(encoding='utf-8')
    req, sec0, sig, bstyle = brief_parts(text)
    style = style or bstyle
    bp = pathlib.Path(os.path.abspath(brief))
    if frame:
        frame = pathlib.Path(os.path.abspath(frame))
        tp, gp, size, tw = thumbnails(frame, width, out)
        L = ['You are the independent art director for one pixel-art still. You did not draw it. Judge it; '
             'do not edit any file. Look at every image below with your image-reading tool before you grade.'
             if role == 'lead' else
             'You are an independent %s visual specialist. You did not draw this still. Look at every image '
             'below with your image-reading tool; report concrete observations only, do not edit files.' % role,
             '', '## Look at', '',
             '- Thumbnail (%d px wide, nearest neighbour): %s' % (tw, tp),
             '- Greyscale thumbnail: %s' % gp,
             '- Frame at delivered size (%dx%d): %s' % (size[0], size[1], frame),
             '- The bar, Lantern Isle winter: %s' % BAR,
             '- The brief: %s' % bp]
        found, ov = findings(frame, out)
        if ov:
            L.append('- Detector overlay, numbered boxes from `pixelate judge`: %s' % ov)
        L += ['', 'The painter\'s own report or grade is not evidence: judge only what you see.']
    else:
        L = ['You are the independent art director for one pixel-art brief, before anything is drawn. You did not '
             'write it. Judge it as the picture a cold run would draw from it; do not edit any file. Read the whole '
             'brief and the bar brief, and look at the bar image, before you grade. Use "Grading a brief" below.'
             if role == 'lead' else
             'You are an independent %s visual specialist. You did not write this brief. Read it in full and '
             'inspect the block-in if provided; report concrete observations only, do not edit files.' % role,
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
    if frame and found is not None:
        L += ['', '## Detector findings (pixelate judge)', '',
              'The detectors point at failures the gate passes. Look at each box: a confirmed one is a fix '
              '(name it and its box in your fixes), a false one you dismiss in one line. They do not replace '
              'your own look.' if found else 'The detectors (masonry, repeat_units, scallops, outline_loop, '
              'murky) found nothing; look for what they cannot see.', '']
        import judge
        L.append(judge.report(found).strip()) if found else None
    L += ['', 'Every fix you propose must agree with the brief\'s light direction, wind and physics.']
    if role == 'lead':
        if prev:
            L += ['', '## The previous lead critique (not specialist notes)', '',
                  pathlib.Path(prev).read_text(encoding='utf-8').strip(), '',
                  'Before anything else, check each of its fixes in what you see now. Start your block with one line '
                  '`PRIOR FIXES: 1=fixed|partly|not 2=... (what is still missing)`.']
        if consults:
            L += ['', '## Specialist observations (not previous lead fixes)',
                  'Use these in this same graded round. Reconcile any disagreement against the brief and what you '
                  'see; do not delegate the grade or repeat a specialist claim without checking it.']
            for i, note in enumerate(consults, 1):
                L += ['', '### Consult %d: %s' % (i, pathlib.Path(note).resolve()),
                      pathlib.Path(note).read_text(encoding='utf-8').strip()]
        L += ['', '## Rubric', '', rubric('still' if frame else 'brief'), '',
              'Return exactly the block under "What you return", nothing else.']
    else:
        L += ['', '## Specialist scope', '', specialist_scope(role), '',
              'Focus only on the %s scope. Report observed evidence and concrete, located suggestions '
              'consistent with the brief. No grade, scores, ranking of final fixes or final verdict; '
              'the lead art director owns those.' % role]
    return '\n'.join(L) + '\n'

def findings(frame, out=None):
    """the judge's defects for a frame and the path of their overlay (None when nothing was found or
    the judge could not read the frame)"""
    try:
        import judge
        found = judge.detect(frame)
    except Exception:                                   # never let a detector break the review prompt
        return None, None
    if not found:
        return found, None
    d = pathlib.Path(out) if out else pathlib.Path(frame).parent
    return found, judge.overlay(frame, found, d / (pathlib.Path(frame).stem + '.judge.png'))

def run_critic(text, cmd=None, timeout=1800):
    """send a prompt to a separate model process on stdin and return its reply. cmd: a shell-style
    command, default $PIXELATE_CRITIC_CMD or `claude -p --allowedTools Read` (it must be able to read
    the image files the prompt names)"""
    argv = shlex.split(cmd or os.environ.get('PIXELATE_CRITIC_CMD') or 'claude -p --allowedTools Read')
    if not shutil.which(argv[0]):
        raise FileNotFoundError('critic command not found: %s (install the Claude CLI or set '
                                'PIXELATE_CRITIC_CMD to a command that reads a prompt on stdin)' % argv[0])
    r = subprocess.run(argv, input=text, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError('critic failed (exit %d): %s' % (r.returncode, (r.stderr or r.stdout).strip()[-1500:]))
    return r.stdout.strip() + '\n'

def save_path(frame, brief, role='lead', out=None):
    """the next free critique-<frame or brief>-<role>-rN.md beside the frame (or the brief)"""
    src = pathlib.Path(frame) if frame else pathlib.Path(brief)
    d = pathlib.Path(out) if out else src.parent
    d.mkdir(parents=True, exist_ok=True)
    n = 1
    while (d / ('critique-%s-%s-r%d.md' % (src.stem, role, n))).exists():
        n += 1
    return d / ('critique-%s-%s-r%d.md' % (src.stem, role, n))

def music_prompt(track, brief, prev=None):
    """Prompt for a separate listening agent, not an audio analysis or an automatic review."""
    track = pathlib.Path(track).resolve()
    brief = pathlib.Path(brief).resolve()
    if not track.is_file() or not brief.is_file():
        raise FileNotFoundError('track and brief must exist before music review')
    lines = ['You are an independent music reviewer. You did not compose this track. Do not edit files.',
             'Only review after the rendered track passes `pixelate check TRACK.wav` (or MCP check_music).',
             'You must actually LISTEN to the rendered audio with an audio-capable tool and read the whole brief.',
             'Do not infer how it sounds from a waveform, code, sheet, file name or the composer\'s report.',
             'If you cannot hear the audio, return `NOT REVIEWED: audio could not be heard` instead of a grade.',
             '', 'Track to listen to: %s' % track, 'Brief to read: %s' % brief,
             '', '## What the brief promised', '', brief.read_text(encoding='utf-8').strip()]
    if prev:
        lines += ['', '## Previous music critique', '', pathlib.Path(prev).read_text(encoding='utf-8').strip(),
                  '', 'Check every previous fix against what you hear now before grading.']
    lines += ['', MUSIC_RUBRIC.read_text(encoding='utf-8').strip()]
    return '\n'.join(lines) + '\n'

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pixelate critique', description=(__doc__ or '').split('\n\n')[1])
    ap.add_argument('frame', nargs='?', default='', help='the still; leave it out to grade the brief')
    ap.add_argument('--brief', required=True)
    ap.add_argument('--brief-only', action='store_true', help='grade the brief (the same as leaving out FRAME)')
    ap.add_argument('--block', default=None, help='a greyscale block-in of the layout, for the brief stage')
    ap.add_argument('--prev', default=None, help='previous lead critique only: its fixes are checked first')
    ap.add_argument('--role', choices=ROLES, default='lead', help='lead grades; specialists report observations only')
    ap.add_argument('--consult', action='append', default=[], metavar='NOTE.md',
                    help='specialist notes for the lead (repeat at most twice per artifact)')
    ap.add_argument('--style', default='')
    ap.add_argument('--width', type=int, default=480, help='thumbnail width (default 480)')
    ap.add_argument('--out', default=None, help='folder for the thumbnails (default: next to the frame)')
    ap.add_argument('--run', action='store_true',
                    help='run the review with a separate model process and save the critique (see PIXELATE_CRITIC_CMD)')
    ap.add_argument('--save', default=None, help='with --run: where to save the critique (default critique-*-rN.md)')
    ap.add_argument('--log', nargs='?', const='', default=None,
                    help='with --run: add the critique to the judge corpus log (default .pixelate/judge-log.jsonl)')
    a = ap.parse_args(argv)
    if a.brief_only:
        a.frame = ''
    for p in (a.frame, a.brief, a.block, a.prev, *a.consult):
        if p and not pathlib.Path(p).exists():
            sys.exit(f'no such file: {p}')
    try:
        text = prompt(a.frame, a.brief, a.style, a.width, a.out, a.prev, a.block, a.role, a.consult)
    except ValueError as e:
        ap.error(str(e))
    if not a.run:
        sys.stdout.write(text)
        return
    try:
        reply = run_critic(text)
    except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired) as e:
        sys.exit(str(e))
    dest = pathlib.Path(a.save) if a.save else save_path(a.frame, a.brief, a.role, a.out)
    dest.write_text(reply, encoding='utf-8')
    if a.log is not None:
        import judge
        grade = re.search(r'^GRADE:\s*([ABC])', reply, re.M)
        judge.log({'type': 'critique', 'role': a.role, 'frame': os.path.abspath(a.frame) if a.frame else None,
                   'sha256': judge.digest(a.frame) if a.frame else None, 'brief': os.path.abspath(a.brief),
                   'critique': str(dest.resolve()), 'grade': grade.group(1) if grade else None,
                   'prev': os.path.abspath(a.prev) if a.prev else None}, a.log or None)
    sys.stdout.write(reply)
    print('saved: %s' % dest)

def music_main(argv=None):
    ap = argparse.ArgumentParser(prog='pixelate critique-music',
                                 description='Print a prompt for an independent listening agent; no audio is played here.')
    ap.add_argument('track', help='rendered track to listen to')
    ap.add_argument('--brief', required=True, help='scene or music brief')
    ap.add_argument('--prev', help='previous music critique (not a visual critique)')
    a = ap.parse_args(argv)
    for p in (a.track, a.brief, a.prev):
        if p and not pathlib.Path(p).is_file():
            ap.error(f'no such file: {p}')
    sys.stdout.write(music_prompt(a.track, a.brief, a.prev))

if __name__ == '__main__':
    main()
