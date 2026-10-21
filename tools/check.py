#!/usr/bin/env python3
"""Automated checks before every delivery: a scene, or one frame against its style (the gate).

usage: check.py SCENE_DIR [--page]
       check.py FRAME.png --style S --scale N [--pal palette.json] [--pre prelight.png]
                [--actor actor_mask.png] [--used op,op] [--intent mask.png]
                [--scene NAME] [--era ERA] [--brief brief.md [--image B]] [--budget 'RULE BOUND (reason)']
       check.py BLOCKIN.png --blockin [--scale N] [--brief brief.md [--image B]] [--style S]
       --scale N is the factor the image is already enlarged by (a 512x448 file of a 256x224 screen is
       --scale 2); a native-size image takes --scale 1, or the check reads it at 1/N size
       (--image B: a brief that serves several images reads the Hero, Planes and Gate override
        lines under its `## Image B` heading first, then its own)
       check.py TRACK.wav [--style S] [--use loop|showcase|song] [--bpm N] [--key K] [--sheet P]
                (the music gate: see musiccheck.py)

Scene mode (an engine scene directory):
  1. sprites and palettes: unknown sprite keys, slots missing a colour
  2. timing: the cycle fits the phases' natural length (tempos barely scaled)
  3. determinism: a frame renders the same twice (no Math.random, no state)
  4. loop seam: the jump from the last frame back to frame 0 is no bigger than
     ordinary steps at the same animation phase (every period divides the loop)
  5. --page: the built page loads without errors and the play button starts audio

Frame mode (FRAME is an image: any scene, Python or engine, at its delivered N x scale):
  1. budget: every rule of the style's numeric budget (stats.budget_report, styles.STYLES)
  2. native cells: every N x N cell flat, for 'none' and 'native' styles (stats.native_cells)
  3. post ops: each op in --used is allowed by the style (styles.allows)
  4. palette: the pre-light frame (--pre, 1x or N x; the frame itself for pixel-only styles)
     has no colour outside --pal (stats.palette_subset)
  5. readability: the actor (--actor, white or opaque = actor) differs from the 8 px ring
     around it by READ_DL in rim or fill L, or by READ_HUE degrees with at least READ_LUM L
     (never hue alone) (stats.readability)
  6. craft: orphans, jaggies, stripes, doubled outlines, pillow shading and clusters inside
     the style's craftcheck.CRAFT limits (--intent marks sparkles and flecks placed on purpose)
  7. composition: a near-empty bottom third, a bare frame, a brick-shaped mass, a flat-slab edge and
     light banded into rings, inside the style's craftcheck.COMPOSITION limits; each failing line
     says what to change
  8. focus: with a hero (the brief's `- Hero: x0,y0,x1,y1 (native px); peak value: OBJECT; peak chroma:
     OBJECT` line, else the --actor mask's bbox), read at thumbnail size: the hero holds the frame's
     top values and its strongest local contrast (or a light the brief names with its own bbox,
     `peak value: the sun disc (244,6,268,32)`), no same-hue colour outside it out-saturates it, no
     mass outside it outweighs it, and with both --actor and the Hero line the drawn hero fills 85% of
     the planned bbox (craftcheck.focus, craftcheck.FOCUS)
  9. repeat (WARN, never FAIL): rows of near-identical lobes or units, e.g. equal cloud scallops or the
     same house stamped along a street (craftcheck.repeats)
  --blockin: the frame is a greyscale block-in (flat value masses, no detail): 3-4 value bands with the
     hero's light the brightest, the hero placed and sized as the brief's bbox, the shares of the
     brief's `- Planes: street 45% (mid), sky 20% (light)` summed per tagged band, empty cells on a
     coarse grid, a long inner slab edge, focus
  --scene NAME: the style's scene variant budget (`pixelate style S` lists them), e.g. cosy-lightmap
     exterior, contre-jour beam
  --era ERA: the console era's own checks (size, colour count, fixed palette or bit depth, colours per
     block, unique tiles; tools/era.py) replace the value budget; --style still sets the craft limits
  --brief brief.md: apply its `- Gate override: RULE BOUND (reason)` lines; --budget adds one from the
     command line in the same form, e.g. --budget 'L>0.75 <= 0.02 (the beam is the subject)'. BOUND is
     `<= V`, `>= V`, `LO..HI` or `off`, for a budget rule, a craft limit, a composition limit or a
     focus key (focus_value, focus_contrast, focus_chroma, focus_rival, focus_size, `focus off`,
     `repeat off`, `repeat <= N`); an
     override without a reason is rejected, and the report still says how far the frame is from the
     style's own bound. `- Gate override: allow Post.OP (reason)` is for route lint: noted, no bound moves
Each check prints PASS, FAIL, WARN or SKIP with the measured value and the limit; WARN never fails.
Exit status 1 if anything fails.
"""
import asyncio, os, pathlib, re, sys
import numpy as np

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / 'tools'))
import build, render_video as rv

def main(scene, page=False):
    ok = True
    i = rv.info(scene)
    W, H, T = i['W'], i['H'], i['TICKS']
    print('canvas %dx%d, picture loop %d s (%d frames), phases: %s' % (W, H, i['loopSeconds'], T,
          ', '.join('%s %.1fs' % (g['phase'], g['dur']) for g in i['segments'] if g['kind'] == 'season')))
    if i['warnings']:
        ok = False
        print('FAIL sprites/palettes:', *i['warnings'], sep='\n  ')
    else:
        print('ok   sprites and palettes')
    ratio = i['bpm'][0] / i['baseBpm'][0]
    natural = i['loopSeconds'] / i['GRAND'] * ratio
    has_music = (pathlib.Path(scene) / 'music.js').exists()
    if abs(ratio - 1) > 0.03 and has_music:
        ok = False
        target = max(1, round(natural))
        if target != i['loopSeconds'] / i['GRAND']:
            print('FAIL timing: tempos scaled by %.3f; set cycle to %d s (natural length %.1f s)' % (ratio, target, natural))
        else:
            bpms = ', '.join('%.1f' % (b * natural / target) for b in i['baseBpm'])
            print('FAIL timing: tempos scaled by %.3f; the natural length %.1f s is not near a whole second: '
                  'set the bpms to %s (or change bars) for exactly %d s' % (ratio, natural, bpms, target))
    else:
        print('ok   timing (tempos scaled by %.3f)' % ratio if has_music else 'ok   timing (no music)')
    fr = lambda k0, k1: np.frombuffer(rv.frames(scene, k0, k1), np.uint32).reshape(-1, H, W)
    h = rv.node(scene, 'hash', 1234 % T, 1234 % T, 77 % T)
    import json
    hh = json.loads(h)
    if len(set(hh.values())) and rv.node(scene, 'hash', 1234 % T) == rv.node(scene, 'hash', 1234 % T):
        print('ok   determinism')
    else:
        ok = False; print('FAIL determinism: the same tick renders differently')
    seam = fr(T - 1, T + 1)          # frames T-1 and T (== 0)
    jump = int((seam[0] != seam[1]).sum())
    first = next(g for g in i['segments'] if g['kind'] == 'season')
    span = max(60, int(first['dur'] * 30) - 30)
    f = fr(0, span)
    same = [int((f[k - 1] != f[k]).sum()) for k in range(30, span, 30)]
    lim = max(same) * 1.15 + 50
    if jump <= lim:
        print('ok   loop seam: %d px change (same-phase steps %d..%d)' % (jump, min(same), max(same)))
    else:
        ok = False
        print('FAIL loop seam: %d px change vs same-phase steps %d..%d: some animation period does not divide %d ticks'
              % (jump, min(same), max(same), T))
    if page:
        ok = asyncio.run(page_check(scene)) and ok
    print('ALL OK' if ok else 'SOME CHECKS FAILED')
    return ok

async def page_check(scene):
    from playwright.async_api import async_playwright
    out = build.build(scene, release=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        pg = await b.new_page(viewport={'width': 1280, 'height': 720})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(out.resolve().as_uri())
        await pg.wait_for_timeout(500)
        await pg.click('#play')
        gone = False
        for _ in range(30):
            await pg.wait_for_timeout(500)
            if await pg.evaluate("document.getElementById('play').hidden"):
                gone = True; break
        await b.close()
    good = gone and not errs
    print(('ok  ' if good else 'FAIL') + ' page: %s, play button %s' % ('no errors' if not errs else errs[:3], 'started audio' if gone else 'did not finish'))
    return good

# ---------------------------------------------------------------- frame mode (the delivery gate)
IMAGE_EXT = ('.png', '.gif', '.jpg', '.jpeg', '.webp', '.bmp')
READ_DL, READ_HUE = 0.10, 40.0          # an actor reads when its rim or fill is this far from its ring
READ_LUM = 0.025    # ... or by hue, but never with less lightness difference than this: the showcase
                    # observatory's lantern pilgrims (fill -0.031, hue 160) are the lowest that read

def _load_mask(path, shape, scale):
    """a mask image (opaque, or white on black) at 1x or at the delivered scale -> 1x bool array"""
    from PIL import Image
    import stats
    im = Image.open(path).convert('RGBA')
    if im.size == (shape[1] * scale, shape[0] * scale) and scale > 1:
        im = Image.fromarray(np.asarray(im)[scale // 2::scale, scale // 2::scale].copy(), 'RGBA')
    a = np.asarray(im)
    if a.shape[:2] != shape:
        raise SystemExit('%s is %dx%d; the frame is %dx%d at 1x' % (path, a.shape[1], a.shape[0], shape[1], shape[0]))
    if (a[..., 3] < 128).any():
        return a[..., 3] >= 128
    return a[..., :3].astype(int).sum(-1) >= 3 * 128

# Overrides: a brief may move one budget or craft bound when the scene clearly needs it, with the
# reason in the same line, in its Technical section:  - Gate override: L>0.75 <= 0.02 (the beam is the subject)
# The bound forms are `<= V`, `>= V`, `LO..HI` and `off`; V may be a fraction or a percentage.
OVERRIDE_LINE = re.compile(r'^\s*[-*]\s*Gate override:\s*(.+?)\s*$', re.M)
_OVR = re.compile(r'^(?P<rule>[^()]+?)\s*\((?P<reason>[^()]*[A-Za-z\u4e00-\u9fff][^()]*)\)\s*\.?$')
_BOUND = re.compile(r'^(?P<key>\S.*?)\s*(?:(?P<op><=|>=)\s*(?P<v>[0-9.]+%?)|\s(?P<lo>[0-9.]+%?)\s*\.\.\s*(?P<hi>[0-9.]+%?)'
                    r'|\s+(?P<off>off))$')

def _num(x):
    return float(x[:-1]) / 100 if x.endswith('%') else float(x)

def _canon(key):
    """'L > .8' -> 'L>0.8', so a brief's key matches the style's"""
    return re.sub(r'(?<![0-9])\.(\d)', r'0.\1', re.sub(r'\s+', '', key))

_ALLOW = re.compile(r'^allow\s+(?P<op>\S+)\s*\((?P<reason>[^()]*[A-Za-z一-鿿][^()]*)\)\s*\.?$', re.I)

def parse_override(text):
    """'L>0.75 <= 0.02 (the beam is the subject)' -> (key, op, lo, hi, reason); op is '<=', '>=', '..'
    or 'off'. 'allow Post.shaft (reason)' -> ('Post.shaft', 'allow', None, None, reason): an allowed-effect
    override, which route lint checks; the gate notes it and moves no bound. An override without a
    reason in brackets is rejected (SystemExit)."""
    a = _ALLOW.match(text.strip())
    if a:
        return a.group('op'), 'allow', None, None, a.group('reason').strip()
    m = _OVR.match(text.strip())
    if not m:
        raise SystemExit('gate override %r has no reason: write it as RULE BOUND (reason), e.g. '
                         '"L>0.75 <= 0.02 (the beam is the subject)"' % text)
    b = _BOUND.match(m.group('rule').strip())
    if not b:
        raise SystemExit('gate override %r: the bound is `<= V`, `>= V`, `LO..HI` or `off`' % text)
    key, reason = _canon(b.group('key')), m.group('reason').strip()
    if b.group('off'):
        return key, 'off', None, None, reason
    if b.group('op'):
        v = _num(b.group('v'))
        return (key, '<=', None, v, reason) if b.group('op') == '<=' else (key, '>=', v, None, reason)
    return key, '..', _num(b.group('lo')), _num(b.group('hi')), reason

IMAGE_HEAD = r'^#{2,4}\s*Image\s+%s\b.*$'

def brief_for_image(path, image):
    """a brief that serves several images can give each its own lines under `## Image B` (its Hero,
    Planes and `- Gate override:` lines). Returns the path of a derived brief in which that section's
    lines come first and its overrides join the Technical section's, or the brief itself when it has
    no such section."""
    text = pathlib.Path(path).read_text()
    m = re.search(IMAGE_HEAD % re.escape(str(image)), text, re.M | re.I)
    if not m:
        return path
    body = text[m.end():]
    nxt = re.search(r'^#{1,4}\s', body, re.M)
    body = body[:nxt.start()] if nxt else body
    tech = ''
    t = re.search(r'^#+\s*(?:\d+\.\s*)?Technical.*$', text, re.M | re.I)
    if t:
        tech = text[t.end():]
        n2 = re.search(r'^#{1,2}\s', tech, re.M)
        tech = tech[:n2.start()] if n2 else tech
    inherited = [l for l in tech.splitlines() if OVERRIDE_LINE.match(l)]
    import tempfile
    fd, out = tempfile.mkstemp(prefix='brief-%s-' % image, suffix='.md')
    with os.fdopen(fd, 'w') as f:
        f.write('## Technical (image %s)\n%s\n%s\n\n%s' % (image, body.strip(), '\n'.join(inherited), text))
    return out

def brief_overrides(path):
    """the `- Gate override:` lines of a brief (its Technical section when it has one)"""
    text = pathlib.Path(path).read_text()
    m = re.search(r'^#+\s*(?:\d+\.\s*)?Technical.*$', text, re.M | re.I)
    if m:
        text = text[m.end():]
        nxt = re.search(r'^#{1,2}\s', text, re.M)
        text = text[:nxt.start()] if nxt else text
    return [parse_override(x) for x in OVERRIDE_LINE.findall(text) if x.lower().rstrip('.') != 'none']

# The hero line of a brief (section 4), read by the gate's focus lines and by --blockin:
#   - Hero: x0,y0,x1,y1 (native px); peak value: OBJECT; peak chroma: OBJECT
# The bbox is inclusive, at 1x. An OBJECT that is not the hero (a sun, a lamp) gives its own bbox in
# brackets, `peak value: the sun disc (244,6,268,32)` or `[244,6,268,32]`, so the peak may sit there
# instead; several boxes are allowed, and other brackets (reasons) may come before or after them.
# The plane line, read by --blockin:   - Planes: street 45% (mid), sky 20% (light), houses 25% (dark)
# Planes name objects or places, and a name may hold commas (`cloud banks A, B and D 35% (mid)`). A
# plane may carry a band tag in brackets: darkest, dark, mid, light, brightest, or a band number 1-7
# counted from the darkest. Ignored: text after a share up to the next comma (a reason), a last part
# with no share, and everything after the line's first sentence.
_BOX = r'(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)'
HERO_LINE = re.compile(r'^\s*[-*]\s*\**Hero\**:\s*\**\s*\[?\s*' + _BOX + r'\s*\]?(.*)$', re.M | re.I)
PLANES_LINE = re.compile(r'^\s*[-*]\s*\**Planes\**:\s*(.+?)\s*$', re.M | re.I)

def _split_top(text, seps=';'):
    """split on any of seps outside round and square brackets"""
    out, depth, cur = [], 0, ''
    for ch in text:
        depth = max(0, depth + (ch in '([') - (ch in ')]'))
        if ch in seps and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
    return out + [cur]

def _boxes_in(text, where, problems):
    """every inclusive x0,y0,x1,y1 box inside a (...) or [...] of text; a reversed box is a problem"""
    out = []
    for inner in re.findall(r'[(\[]([^()\[\]]*)[)\]]', text):
        for b in re.finditer(_BOX, inner):
            x0, y0, x1, y1 = (int(v) for v in b.groups())
            if x1 < x0 or y1 < y0:
                problems.append('%s: box %d,%d,%d,%d is reversed (write x0,y0,x1,y1 with x1 >= x0, y1 >= y0)'
                                % (where, x0, y0, x1, y1))
            else:
                out.append((x0, y0, x1, y1))
    return out

def _owner(rest, what, problems=None):
    """the OBJECT of `what: OBJECT` in the Hero line's rest -> (name, [boxes]); `;` inside brackets
    does not end it"""
    problems = [] if problems is None else problems
    for part in _split_top(rest):
        m = re.match(r'\s*' + what + r'\s*:\s*(.+)$', part.strip(), re.I | re.S)
        if m:
            name = m.group(1).strip().rstrip('.')
            boxes = _boxes_in(name, what, problems)
            return re.sub(r'\s*[(\[][^()\[\]]*[)\]]\s*', ' ', name).strip(), boxes
    return None, []

def brief_hero(path):
    """the brief's `- Hero:` line -> {'bbox', 'value', 'value_box', 'value_boxes', 'chroma',
    'chroma_box', 'chroma_boxes', 'problems'}, or None"""
    m = HERO_LINE.search(pathlib.Path(path).read_text())
    if not m:
        return None
    x0, y0, x1, y1 = (int(v) for v in m.groups()[:4])
    if x1 < x0 or y1 < y0:
        raise SystemExit('brief Hero bbox %d,%d,%d,%d: write it as x0,y0,x1,y1 with x1 >= x0 and y1 >= y0' % (x0, y0, x1, y1))
    problems = []
    v, vb = _owner(m.group(5), 'peak value', problems)
    c, cb = _owner(m.group(5), 'peak chroma', problems)
    return {'bbox': (x0, y0, x1, y1), 'value': v, 'value_box': vb[0] if vb else None, 'value_boxes': vb,
            'chroma': c, 'chroma_box': cb[0] if cb else None, 'chroma_boxes': cb, 'problems': problems}

BAND_WORDS = ('darkest', 'dark', 'mid', 'light', 'brightest')

def _band_tag(text):
    """the band a bracket names: 'mid' -> 'mid', '3' or 'band 3' -> 3, a reason alone -> None"""
    m = re.match(r'\s*(?:band\s*)?([1-9])(?![\d.%])', text, re.I)
    if m:
        return int(m.group(1))
    m = re.match(r'\s*(darkest|brightest|dark|mid|light)\b', text, re.I)
    return m.group(1).lower() if m else None

_SHARE = re.compile(r'\s*(?P<n>[^%\x00]*?[^\s%\x00\d~.][^%\x00]*?)\s+~?(?P<v>\d+(?:\.\d+)?)\s*%\s*(?:\x00(?P<t>[^\x00]*)\x00)?')

def parse_planes(text):
    """the text after `Planes:` -> [(name, share, tag)]: each `NAME NN%` pair, with the band tag of the
    bracket right after it (None when untagged). A comma part with no share joins the next name, so
    `cloud banks A, B and D 35%` is one plane; text after a share up to the next comma, notes in
    brackets, a last part with no share and everything after the first sentence are ignored."""
    text = re.sub(r'(?:\(|\[)([^)\]]*)(?:\)|\])', lambda m: ' \x00%s\x00 ' % (_band_tag(m.group(1)) or ''), text)
    end = re.search(r'(?<![\d\s])\.(?:\s+(?=[A-Z])|\s*$)|\x00\s*\.\s+(?=[A-Z])', text)   # the first sentence ends
    text = text[:end.end()].rstrip(' .') if end else text
    out, pending = [], []
    for part in re.split(r'[,;]', text):
        m = _SHARE.match(part)
        if not m or ':' in m.group('n'):
            pending = [] if m else pending + [part.strip()]
            continue
        name = ', '.join([p for p in pending if p] + [m.group('n').strip()])
        pending = []
        tag = m.group('t') or ''
        out.append((re.sub(r'\s+', ' ', name), float(m.group('v')) / 100, (int(tag) if tag.isdigit() else tag) or None))
    return out

def brief_planes(path):
    """the brief's `- Planes: street 45% (mid), sky 20%` line -> [(name, share, tag)], or None"""
    m = PLANES_LINE.search(pathlib.Path(path).read_text())
    return (parse_planes(m.group(1)) or None) if m else None

# The object lines of a brief, read by the gate and by --blockin (boxes native px, inclusive, in square
# brackets; any section; one line each):
#   - Key: OBJECT [x0,y0,x1,y1]; L .30 on PLANE .15     a secondary object that must read, its planned L
#   - Key: OBJECT [x0,y0,x1,y1]; rim: DESCRIPTION       ... or one that reads by a rim
#   - Value: PLANE [x0,y0,x1,y1] L .40                  the planned mean OKLab L of a plane region
#   - Calm: NAME [x0,y0,x1,y1]                          a planned calm area
#   - Sprites: NAME [x0,y0,x1,y1], NAME [x0,y0,x1,y1]   hardware sprites, for --era's sprite limits
def _line_re(word):
    return re.compile(r'^\s*[-*]\s*\**' + word + r'\**\s*:\s*\**\s*(.+?)\s*$', re.M | re.I)

KEY_LINE, VALUE_LINE, CALM_LINE, SPRITES_LINE = (_line_re(w) for w in ('Key', 'Value', 'Calm', 'Sprites'))

def _boxed(rx, text):
    """the bodies of rx's lines that hold a [ box: a line of prose under the same label (an era
    brief's `- Sprites: 8x8, 3 colours`) is not a box line, so it is neither read nor a problem"""
    return [b for b in rx.findall(text) if '[' in b]
_SQ = r'\[\s*' + _BOX + r'\s*\]'
_NUM = r'(\d*\.\d+|\d+(?:\.\d+)?)'

def _sq_box(text, where, problems):
    """(name before the [box], box, text after it), or None with a problem noted"""
    m = re.search(_SQ, text)
    if not m:
        problems.append('%s line %r has no [x0,y0,x1,y1] box' % (where, text.strip()))
        return None
    x0, y0, x1, y1 = (int(v) for v in m.groups())
    if x1 < x0 or y1 < y0:
        problems.append('%s line %r: box %d,%d,%d,%d is reversed (x1 >= x0, y1 >= y0)' % (where, text.strip(), x0, y0, x1, y1))
        return None
    return text[:m.start()].strip(' :;,-*'), (x0, y0, x1, y1), text[m.end():]

def brief_plan(path):
    """the brief's Key, Value, Calm and Sprites lines -> {'keys': [{'name', 'box', 'L', 'plane',
    'plane_L', 'rim'}], 'values': [{'name', 'box', 'L'}], 'calm': [(name, box)], 'sprites': [(name,
    box)], 'problems': [text]}. A line that cannot be read is a problem, never silently dropped."""
    text = pathlib.Path(path).read_text()
    out = {'keys': [], 'values': [], 'calm': [], 'sprites': [], 'problems': []}
    P = out['problems']
    for body in _boxed(KEY_LINE, text):
        r = _sq_box(body, 'Key', P)
        if not r:
            continue
        name, box, rest = r
        k = {'name': name or 'the object', 'box': box, 'L': None, 'plane': None, 'plane_L': None, 'rim': None}
        rest = rest.strip(' ;,.')
        rm = re.search(r'\brim\s*:\s*(.+)$', rest, re.I)
        lm = re.search(r'\bL\s*' + _NUM + r'\s+(?:on|against|over)\s+(.+?)(?:\s+(?:L\s*)?' + _NUM + r'(?![\d]))?\s*(?:[;,]|$)',
                       rest, re.I)
        if rm:
            k['rim'] = rm.group(1).strip()
        if lm:
            k['L'], k['plane'] = float(lm.group(1)), lm.group(2).strip()
            k['plane_L'] = float(lm.group(3)) if lm.group(3) else None
        if not rm and not lm:
            P.append('Key line %r: after the box write `; L .30 on PLANE .15` or `; rim: DESCRIPTION`' % body.strip())
        out['keys'].append(k)
    for body in _boxed(VALUE_LINE, text):
        r = _sq_box(body, 'Value', P)
        if not r:
            continue
        name, box, rest = r
        lm = re.search(r'\bL\s*' + _NUM, rest)
        if not lm:
            P.append('Value line %r: write the planned L after the box, `- Value: PLANE [x0,y0,x1,y1] L .40`' % body.strip())
            continue
        out['values'].append({'name': name or 'the plane', 'box': box, 'L': float(lm.group(1))})
    for body in _boxed(CALM_LINE, text):
        r = _sq_box(body, 'Calm', P)
        if r:
            out['calm'].append((r[0] or 'calm area', r[1]))
    for body in _boxed(SPRITES_LINE, text):
        for part in _split_top(body, ','):
            if part.strip():
                r = _sq_box(part, 'Sprites', P)
                if r:
                    out['sprites'].append((r[0] or 'sprite', r[1]))
    return out

def band_index(tag, n):
    """a plane's band tag -> the band's index (0 darkest) among n bands, or None when there is no such band.
    brightest is the top band (the hero's light); dark, mid and light spread over the bands below it."""
    if isinstance(tag, int):
        return tag - 1 if tag <= n else None
    if tag == 'darkest':
        return 0
    if tag == 'brightest':
        return n - 1
    r = max(1, n - 1)                       # the bands below the brightest; darkest owns index 0
    return {'dark': 1 if n >= 4 else 0, 'mid': r // 2, 'light': r - 1}[tag]

FOCUS_KEYS = ('focus_value', 'focus_contrast', 'focus_chroma', 'focus_rival', 'focus_size')

def _focus_lines(img, hero, actor_box, line, note, ovr, chroma=True, size=True):
    """the focus lines (craftcheck.focus) for a hero bbox; ovr: {key: (lo, hi, reason)} or 'focus' off"""
    import craftcheck
    if 'focus' in ovr:
        line('SKIP', 'focus', '', 'off by override (%s)' % ovr['focus'][2])
        return
    hb = hero['bbox'] if hero else actor_box
    src = 'brief Hero line' if hero else '--actor bbox'
    owners_v = list(hero.get('value_boxes') or []) if hero else []
    owners_c = list(hero.get('chroma_boxes') or []) if hero else []
    vals = craftcheck.focus(img, hb, owners_v, owners_c, chroma=chroma)
    if hero and actor_box:
        a = (actor_box[2] - actor_box[0] + 1) * (actor_box[3] - actor_box[1] + 1)
        p = (hb[2] - hb[0] + 1) * (hb[3] - hb[1] + 1)
        vals['focus_size'] = (a / p, None)
    note('focus: hero x %d-%d, y %d-%d (%s)%s%s' % (hb[0], hb[2], hb[1], hb[3], src,
         ('; peak value: %s%s' % (hero['value'], ' ' + ' '.join('[%d,%d,%d,%d]' % b for b in owners_v) if owners_v else '')) if hero and hero.get('value') else '',
         ('; peak chroma: %s' % hero['chroma']) if hero and hero.get('chroma') else ''))
    for key in FOCUS_KEYS:
        lo, hi = craftcheck.FOCUS[key]
        reason = None
        if key in ovr:
            olo, ohi, reason = ovr[key]
            if olo == 'off':
                line('SKIP', key.replace('_', ' '), '', 'off by override (%s)' % reason); continue
            lo, hi = (olo if olo is not None else lo), (ohi if ohi is not None else hi)
        if key not in vals:
            if key == 'focus_chroma':
                line('SKIP', 'focus chroma', '', 'a fixed era palette or a greyscale block-in')
            elif key == 'focus_size' and size:
                line('SKIP', 'focus size', '', 'needs both --actor and a brief Hero line')
            continue
        v, detail = vals[key]
        bad = (lo is not None and v < lo) or (hi is not None and v > hi)
        fmt = (lambda x: '%.0f%%' % (100 * x)) if key in ('focus_value', 'focus_contrast', 'focus_size') else (lambda x: '%.2fx' % x)
        line('FAIL' if bad else 'PASS', key.replace('_', ' '), fmt(v),
             '[%s .. %s]' % (fmt(lo) if lo is not None else '', fmt(hi) if hi is not None else '') + (' override' if reason else ''))
        if bad:
            note(craftcheck.focus_advice(key, v, detail, hb))
        if reason:
            b = craftcheck.FOCUS[key]
            note('limit [%s .. %s] (override: %s)' % (fmt(b[0]) if b[0] is not None else '', fmt(b[1]) if b[1] is not None else '', reason))

PLAN_KEYS = ('key', 'value', 'calm', 'density')

def _bx(b):
    return '[%d,%d,%d,%d]' % b

def _plan_lines(img, plan, hero, line, note, ovr, scale=1, blockin=False):
    """the brief's Key, Value and Calm lines against the frame (craftcheck.presence, plane_value,
    calm_share, density); ovr: {key: (lo, hi, reason)} for 'key', 'value', 'calm', 'density'"""
    import craftcheck as cc
    H, W = img.size[1], img.size[0]
    probs = list(plan['problems']) + list((hero or {}).get('problems') or [])
    if probs:
        line('FAIL', 'brief lines', '%d unread' % len(probs), 'every Key, Value, Calm, Sprites and Hero box is read')
        for p in probs:
            note(p)
    hb = [hero['bbox']] if hero else []
    keys = plan['keys']
    def off(k):
        if k in ovr and ovr[k][0] == 'off':
            line('SKIP', k, '', 'off by override (%s)' % ovr[k][2]); return True
        return False
    if not keys:
        line('SKIP', 'key objects', '', 'no `- Key: OBJECT [x0,y0,x1,y1]; L .30 on PLANE .15` lines in the brief')
    elif not off('key'):
        dl = ovr['key'][0] if 'key' in ovr and ovr['key'][0] is not None else cc.PRESENCE_DL
        for k in keys:
            others = hb + [o['box'] for o in keys if o is not k]
            r = cc.presence(img, k['box'], others, rim=bool(k['rim']), dl=dl)
            name = k['name'] if len(k['name']) <= 18 else k['name'][:17] + '.'
            val = 'outside' if r['why'] == 'outside' else 'dE %.2f' % r['dE'] if r['why'] == 'colour' else 'dL %+.2f' % r['dL']
            lim = '|dL| >= %.2f or dE >= %.2f vs its ring%s' % (dl, cc.PRESENCE_DE, ' or a rim' if k['rim'] else '') + (
                ' override' if 'key' in ovr else '')
            line('PASS' if r['ok'] else 'FAIL', 'key ' + name, val, lim)
            where = '%s at %s' % (k['name'], _bx(k['box']))
            plane = k['plane'] or 'its surroundings'
            plan_txt = (' (planned L %.2f on %s%s; measured %.2f on %.2f)' % (
                k['L'], k['plane'], ' %.2f' % k['plane_L'] if k['plane_L'] is not None else '', r['obj'], r['ring'])
                        if k['L'] is not None and r.get('obj') is not None else
                        (' (measured %.2f on %.2f)' % (r['obj'], r['ring']) if r.get('obj') is not None else ''))
            if r['why'] == 'outside':
                note('%s lies outside the %dx%d frame: fix the box in the brief' % (where, W, H))
            elif r['why'] == 'missing':
                note('%s is missing or flat (dL %.2f, L spread %.3f)%s: draw it in its box, %s' % (
                    where, abs(r['dL']), r['std'], plan_txt, 'one flat grey that differs from %s by %.2f' % (plane, dl)
                    if blockin else 'with its own value step of %.2f from %s and its key shapes' % (dl, plane)))
            elif not r['ok']:
                note('%s blends into %s (dL %.2f)%s: make it %.2f L %s than %s, or give it a 1 px rim along '
                     'its lit edge%s' % (where, plane, abs(r['dL']), plan_txt, dl,
                                         'darker' if r['dL'] < 0 else 'lighter', plane,
                                         ' (the rim reaches %d of %d px)' % (r['rim'], r['rim_need']) if k['rim'] else
                                         ' and say so in the brief (`; rim: ...`)'))
    vals = plan['values']
    if not vals:
        line('SKIP', 'plane values', '', 'no `- Value: PLANE [x0,y0,x1,y1] L .40` lines in the brief')
    elif not off('value'):
        tol = ovr['value'][1] if 'value' in ovr and ovr['value'][1] is not None else cc.PLANE_TOL
        mask = hb + [k['box'] for k in keys]
        for v in vals:
            m, share = cc.plane_value(img, v['box'], mask)
            if m is None:
                m, share = cc.plane_value(img, v['box'])
            name = v['name'] if len(v['name']) <= 16 else v['name'][:15] + '.'
            if m is None:
                line('FAIL', 'value ' + name, 'off frame', 'the box lies outside the %dx%d frame (is --scale the '
                     'factor the image is already enlarged by?)' % (img.size[0], img.size[1]))
                continue
            d = m - v['L']
            bad = abs(d) > tol
            line('FAIL' if bad else 'PASS', 'value ' + name, 'L %.2f' % m, 'plan %.2f +- %.2f' % (v['L'], tol)
                 + (' override' if 'value' in ovr else ''))
            if bad:
                note('%s %s is %.2f %s than planned (L %.2f, plan %.2f, measured on %.0f%% of its box, keys and hero '
                     'masked): %s its albedo or its light until it lands within %.2f, or change the plan' % (
                         v['name'], _bx(v['box']), abs(d), 'darker' if d < 0 else 'lighter', m, v['L'], 100 * share,
                         'lift' if d < 0 else 'lower', tol))
    calm = plan['calm']
    if not calm:
        line('SKIP', 'calm', '', 'no `- Calm: NAME [x0,y0,x1,y1]` lines in the brief')
    elif not off('calm'):
        cap = ovr['calm'][1] if 'calm' in ovr and ovr['calm'][1] is not None else cc.CALM_MAX
        s = cc.calm_share((H, W), [b for _, b in calm])
        line('FAIL' if s > cap else 'PASS', 'calm areas', '%.0f%%' % (100 * s), '[ .. %.0f%%] of the frame' % (100 * cap)
             + (' override' if 'calm' in ovr else ''))
        if s > cap:
            note('the calm boxes (%s) cover %.0f%% of the frame: shrink them to %.0f%% or less and fill the rest with '
                 'the scene\'s objects and stories; a calm area still needs a designed texture' % (
                     ', '.join('%s %s' % (n, _bx(b)) for n, b in calm), 100 * s, 100 * cap))
    if blockin:
        return
    if not keys and not calm:
        line('SKIP', 'density', '', 'needs the brief\'s Key or Calm boxes to tell planned calm from empty')
        return
    if 'density' in ovr and ovr['density'][0] == 'off':
        line('SKIP', 'density', '', 'off by override (%s)' % ovr['density'][2]); return
    win = cc.DENSITY_WIN
    r = cc.density(img, scale, [b for _, b in calm], win)
    state = 'WARN' if r['empty'] else 'PASS'
    line(state, 'density', '%d empty' % r['empty'], '[ .. 0] %d px windows (delivered) with nothing readable, outside '
         'calm boxes (a warning)' % win)
    if r['empty']:
        x0, y0, x1, y1 = r['worst']
        note('%d of %d windows of %d px (delivered) hold nothing readable; the emptiest is x %d-%d, y %d-%d at 1x '
             '(x %d-%d, y %d-%d delivered). Put an object or a small story there, or plan it as a Calm box '
             '(calm stays at most %.0f%% of the frame)' % (r['empty'], r['windows'], win, x0, x1, y0, y1,
             x0 * scale, (x1 + 1) * scale - 1, y0 * scale, (y1 + 1) * scale - 1, 100 * cc.CALM_MAX))

def _sprite_line(img, plan, era, line, note):
    import era as eramod
    if not plan or not plan['sprites']:
        line('SKIP', 'era sprites', '', 'no `- Sprites: NAME [x0,y0,x1,y1], ...` line in the brief')
        return
    boxes = [(b[0], b[1], b[2] - b[0] + 1, b[3] - b[1] + 1) for _, b in plan['sprites']]
    issues, n = eramod.check_sprites(boxes, era)
    e = eramod.ERAS[era]
    line('FAIL' if issues else 'PASS', 'era sprites', '%d sprites' % n, '; '.join(issues) if issues else
         'limit %s per line, %s in all (%d boxes from the brief)' % (e.get('sprite_line'), e.get('sprite_total'), len(boxes)))

def _repeat_line(img, line, note, ovr):
    import craftcheck
    if 'repeat' in ovr and ovr['repeat'][0] == 'off':
        line('SKIP', 'repeat', '', 'off by override (%s)' % ovr['repeat'][2]); return
    hits = craftcheck.repeats(img)
    allow = int(ovr['repeat'][1]) if 'repeat' in ovr and ovr['repeat'][1] is not None else 0
    line('WARN' if len(hits) > allow else 'PASS', 'repeat', '%d rows' % len(hits),
         '[ .. %d] rows of near-identical lobes or units (a warning)' % allow + (' override' if 'repeat' in ovr else ''))
    for _, kind, where in hits[:3]:
        note('%s: make them 3 to 6 of mismatched size (no two neighbours within 25%%), with uneven gaps, '
             'or vary the units (size, roof, windows)' % where)
    if 'repeat' in ovr:
        note('override: %s' % ovr['repeat'][2])

def _ovr_map(ovr, keys):
    """parse_override tuples for these keys -> {key: (lo, hi, reason)} ('off' as lo for off)"""
    out = {}
    for key, op, lo, hi, reason in ovr:
        if key in keys:
            out[key] = ('off', None, reason) if op == 'off' else (lo, hi, reason)
    return out

def _actor_box(m):
    ys, xs = np.nonzero(m)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None

def _apply(rules, ovr):
    """rules with the overrides applied -> (rules, {key: ((lo, hi) before the override, reason)})"""
    out, notes = dict(rules), {}
    for key, op, lo, hi, reason in ovr:
        base = out.get(key, (None, None))
        notes[key] = (base, reason)
        if op == 'off':
            out.pop(key, None)
        else:
            out[key] = (lo if op != '<=' else base[0], hi if op != '>=' else base[1])
    return out, notes

def _away(v, lo, hi, fmt):
    """how far v sits outside (lo, hi), as text"""
    if v is None or v != v:
        return 'not measured'
    if lo is None and hi is None:
        return 'no bound in the style'
    if lo is not None and v < lo:
        return '%s below it' % fmt(lo - v)
    if hi is not None and v > hi:
        return '%s over it' % fmt(v - hi)
    return 'inside it too'

def frame(path, style=None, scale=1, pal=None, pre=None, actor=None, used=(), intent=None, scene=None, era=None,
          overrides=(), hero=None, plan=None):
    """the delivery gate for one frame: print a PASS / FAIL / SKIP line per check, return True
    when nothing fails. scene: a style's scene variant (styles.budgets); era: the console era's own
    checks replace the value budget (tools/era.py); overrides: parse_override tuples, each moving one
    budget or craft bound, printed with its reason and how far the frame is from the style's own bound;
    hero: brief_hero() of the brief, for the focus lines (else the --actor mask's bbox); plan: brief_plan()
    of the brief, for its Key, Value, Calm and Sprites lines"""
    from PIL import Image
    import stats, styles, craftcheck
    if style is None and era is None:
        raise SystemExit('frame mode needs --style (one of styles.STYLES) or --era (one of era.ERAS)')
    st = styles.get(style) if style else None
    big = Image.open(path).convert('RGB')
    rows = []
    def line(state, what, value='', limit=''):
        rows.append(state)
        print('%-4s %-26s %-12s %s' % (state, what, value, limit))
    def note(text):
        print('     %s' % text)
    W, H = big.size
    if W % scale or H % scale:
        line('FAIL', 'scale', '%dx%d' % (W, H), 'not a whole multiple of %d' % scale)
    img = stats.to_native(big, scale) if scale > 1 else big
    print('%s: %s%s%s, %dx%d at 1x (x%d)' % (path, ('%s style' % st['name']) if st else 'no style',
          (', scene %s' % scene) if scene else '', (', era %s' % era) if era else '', img.size[0], img.size[1], scale))
    for key, op, lo, hi, reason in overrides:
        if op == 'allow':
            note('override allow %s (%s): an allowed-effect override, checked by route lint; the gate '
                 'moves no bound for it' % (key, reason))
    overrides = [o for o in overrides if o[1] != 'allow']
    f_ovr = _ovr_map(overrides, FOCUS_KEYS + ('focus', 'repeat') + PLAN_KEYS)
    overrides = [o for o in overrides if o[0] not in f_ovr]
    crafts = set(next(iter(craftcheck.CRAFT.values())))
    comps = set(craftcheck.COMP_METRICS)
    b_ovr = [o for o in overrides if o[0] not in crafts and o[0] not in comps]
    c_ovr = [o for o in overrides if o[0] in crafts]
    k_ovr = [o for o in overrides if o[0] in comps]
    for key, op, lo, hi, reason in overrides:
        print('override %s %s (%s)' % (key, {'<=': '<= %s' % hi, '>=': '>= %s' % lo, '..': '%s..%s' % (lo, hi),
                                             'off': 'off'}[op], reason))
    if era:
        import era as eramod
        if b_ovr:
            raise SystemExit('--era replaces the value budget: a budget override has nothing to move')
        issues, n = eramod.check(img, era)
        e = eramod.ERAS[era]
        line('FAIL' if issues else 'PASS', 'era %s' % era, '%d colours' % n,
             '; '.join(issues) if issues else 'size %dx%d, at most %d colours%s%s' % (
                 e['size'][0], e['size'][1], e['max_colors'], (', palette %s' % e['palette']) if e.get('palette') else '',
                 (', %d per %dx%d block' % (e['block_colors'], e['block'], e['block'])) if e.get('block') else ''))
        t_issues, nt = eramod.check_tiles(img, era)
        line('FAIL' if t_issues else 'PASS', 'era tiles (whole frame)', '%d tiles' % nt,
             'limit %s; run `pixelate era BG.png --era %s --tiles` on the background alone' % (e.get('bg_tiles'), era)
             if t_issues else 'limit %s unique %dx%d' % (e.get('bg_tiles'), e.get('tile') or 8, e.get('tile') or 8))
        _sprite_line(img, plan, era, line, note)
    else:
        try:
            base = styles.budgets(st['name'], scene)
        except KeyError as e:
            raise SystemExit(e.args[0])
        rules, notes = _apply(base, b_ovr)
        F = stats._Frame(img)
        for key, *_ in b_ovr:
            if key not in base and not stats._need(key):
                try:
                    stats.metric(F, key)
                except ValueError as e:
                    raise SystemExit('gate override: %s' % e)
        for key, v, lo, hi, state in stats.budget_report(img, rules):
            lim = '[%s .. %s]' % (stats._fmt(key, lo) if lo is not None else '', stats._fmt(key, hi) if hi is not None else '')
            line({'ok': 'PASS', 'fail': 'FAIL', 'skip': 'SKIP'}[state], 'budget ' + key, stats._fmt(key, v),
                 lim + (' (needs masks)' if state == 'skip' else '') + (' override' if key in notes else ''))
            if key in notes:
                (blo, bhi), reason = notes[key]
                f = lambda x, k=key: stats._fmt(k, x)
                note('style budget%s [%s .. %s]: %s (override: %s)' % ((' (scene %s)' % scene) if scene else '',
                     f(blo) if blo is not None else '', f(bhi) if bhi is not None else '', _away(v, blo, bhi, f), reason))
        for key, (bnd, reason) in notes.items():
            if key not in rules:
                v = stats.metric(F, key) if not stats._need(key) else None
                f = lambda x, k=key: stats._fmt(k, x)
                line('SKIP', 'budget ' + key, f(v), 'off by override (%s); style budget [%s .. %s]: %s' % (
                    reason, f(bnd[0]) if bnd[0] is not None else '', f(bnd[1]) if bnd[1] is not None else '',
                    _away(v, *bnd, f)))
        if not base:
            line('SKIP', 'budget', '', 'the style has no budget')
    cells = st['native_cells'] if st else 0.0
    if cells is not None and scale > 1:
        soft = stats.native_cells(big, scale)
        line('PASS' if soft <= cells else 'FAIL', 'native cells %dx%d' % (scale, scale),
             '%.2f%%' % (100 * soft), '[ .. %.2f%%] soft cells' % (100 * cells))
    elif cells is None:
        line('SKIP', 'native cells', '', 'screen-resolution light layer')
    for op in used:
        ok = bool(st) and not era and styles.allows(st['name'], op)
        line('PASS' if ok else 'FAIL', 'post op ' + op, '',
             'allowed' if ok else 'an era frame has no light layer' if era else 'banned or not part of %s' % st['name'])
    if pal:
        src = pre
        if src is None and st and st['res'] != 'none' and not era:
            line('FAIL', 'palette', '', 'pass --pre: the frame before its light layer')
        else:
            p_img = Image.open(src).convert('RGBA') if src else img
            if src and p_img.size == (img.size[0] * scale, img.size[1] * scale) and scale > 1:
                p_img = stats.to_native(p_img, scale)
            p = stats.palette_subset(p_img, pal)
            line('PASS' if p['ok'] else 'FAIL', 'palette' + (' (pre-light)' if src else ''), '%d px' % p['off_pixels'],
                 'off-palette, limit 0' + ('; e.g. ' + ', '.join(h for h, _ in p['top'][:3]) if not p['ok'] else ''))
    else:
        line('SKIP', 'palette', '', 'no --pal')
    actor_box = None
    if actor:
        m = _load_mask(actor, (img.size[1], img.size[0]), scale)
        actor_box = _actor_box(m)
        r = stats.readability(img, m)
        dl = max(abs(r['edge_dL']), abs(r['fill_dL']))
        hue = r['dhue'] == r['dhue'] and r['dhue'] >= READ_HUE
        good = dl >= READ_DL or (hue and dl >= READ_LUM)
        line('PASS' if good else 'FAIL', 'readability (actor)',
             'rim %+.2f fill %+.2f hue %s' % (r['edge_dL'], r['fill_dL'], '-' if r['dhue'] != r['dhue'] else '%.0f' % r['dhue']),
             '|rim| or |fill| >= %.2f L, or hue >= %.0f with >= %.3f L' % (READ_DL, READ_HUE, READ_LUM))
        if not good:
            note('the actor is only %.3f lighter or darker than what is around it%s; make it darker or lighter '
                 'than its background, or give it a rim' % (dl, ' and reads by hue alone, which a thumbnail '
                 'or a colour-blind viewer loses' if hue else ''))
    if st:
        imask = _load_mask(intent, (img.size[1], img.size[0]), scale) if intent else None
        rules, notes = _apply(craftcheck.CRAFT[st['name']], c_ovr)
        vals = craftcheck.measure(img, imask)
        for key, v, lo, hi, state in craftcheck.report(img, rules, values=vals):
            lim = '[%s .. %s]' % (craftcheck.fmt(key, lo) if lo is not None else '', craftcheck.fmt(key, hi) if hi is not None else '')
            line('PASS' if state == 'ok' else 'FAIL', 'craft ' + key, craftcheck.fmt(key, v),
                 lim + (' override' if key in notes else ''))
            if key in notes:
                (blo, bhi), reason = notes[key]
                f = lambda x, k=key: craftcheck.fmt(k, x)
                note('style limit [%s .. %s]: %s (override: %s)' % (f(blo) if blo is not None else '',
                     f(bhi) if bhi is not None else '', _away(v, blo, bhi, f), reason))
        for key, (bnd, reason) in notes.items():
            if key not in rules:
                f = lambda x, k=key: craftcheck.fmt(k, x)
                line('SKIP', 'craft ' + key, f(vals[key]), 'off by override (%s); style limit [%s .. %s]: %s' % (
                    reason, f(bnd[0]) if bnd[0] is not None else '', f(bnd[1]) if bnd[1] is not None else '',
                    _away(vals[key], *bnd, f)))
        base = craftcheck.COMPOSITION[st['name']]
        rules, notes = _apply(base, k_ovr)
        cv = craftcheck.composition(img, {**rules, **{k: b for k, (b, _) in notes.items()}})
        f = craftcheck.comp_fmt
        for key in craftcheck.COMP_METRICS:
            lo, hi = rules.get(key, (None, None))
            if key not in rules or (lo is None and hi is None):
                if key in notes:
                    (blo, bhi), reason = notes[key]
                    v = cv.get(key, (None, None))[0]
                    line('SKIP', 'composition ' + key, f(key, v), 'off by override (%s); style limit [ .. %s]: %s' % (
                        reason, f(key, bhi), _away(v, blo, bhi, lambda x, k=key: f(k, x))))
                continue
            v, detail = cv[key]
            bad = (lo is not None and v < lo) or (hi is not None and v > hi)
            line('FAIL' if bad else 'PASS', 'composition ' + key, f(key, v),
                 '[ .. %s]' % f(key, hi) + (' override' if key in notes else ''))
            if bad:
                note(craftcheck.comp_advice(key, v, detail, hi))
            if key in notes:
                (blo, bhi), reason = notes[key]
                note('style limit [ .. %s]: %s (override: %s)' % (f(key, bhi), _away(v, blo, bhi, lambda x, k=key: f(k, x)), reason))
    else:
        line('SKIP', 'craft', '', 'no --style: no craft limits')
    if hero or actor_box:
        _focus_lines(img, hero, actor_box, line, note, f_ovr, chroma=not era)
    else:
        line('SKIP', 'focus', '', 'no hero: pass --actor, or a brief with a `- Hero: x0,y0,x1,y1` line')
    _repeat_line(img, line, note, f_ovr)
    if plan is not None:
        _plan_lines(img, plan, hero, line, note, f_ovr, scale)
    else:
        line('SKIP', 'brief objects', '', 'no --brief: no Key, Value or Calm lines')
    ok = 'FAIL' not in rows
    print(('ALL PASS' if ok else 'FAIL: %d of %d checks' % (rows.count('FAIL'), len(rows) - rows.count('SKIP')))
          + (' (%d warning%s)' % (rows.count('WARN'), 's' * (rows.count('WARN') > 1)) if 'WARN' in rows else ''))
    return ok

def blockin(path, scale=1, brief=None, style=None, overrides=()):
    """the block-in gate: a greyscale layout of flat value masses, judged before any drawing. Prints a
    PASS / FAIL / SKIP line per check and returns True when nothing fails."""
    from PIL import Image
    import stats, craftcheck
    big = Image.open(path).convert('RGB')
    img = stats.to_native(big, scale) if scale > 1 else big
    W, H = img.size
    rows = []
    def line(state, what, value='', limit=''):
        rows.append(state)
        print('%-4s %-26s %-12s %s' % (state, what, value, limit))
    def note(text):
        print('     %s' % text)
    print('%s: block-in, %dx%d at 1x (x%d)%s' % (path, W, H, scale, (', brief %s' % brief) if brief else ''))
    hero = brief_hero(brief) if brief else None
    planes = brief_planes(brief) if brief else None
    f_ovr = _ovr_map([o for o in overrides if o[1] != 'allow'], FOCUS_KEYS + ('focus', 'repeat', 'slab', 'empty', 'empty_low')
                     + PLAN_KEYS)
    F = craftcheck._Frame(img)
    chroma = float(np.hypot(F.lab[..., 1], F.lab[..., 2]).max())
    if chroma > 0.03:
        note('the block-in has colour (chroma up to %.2f); it is judged on lightness alone' % chroma)
    bands = craftcheck.value_bands(F)
    lo, hi = craftcheck.BLOCK_BANDS
    nb = len(bands)
    line('PASS' if lo <= nb <= hi else 'FAIL', 'value bands', '%d' % nb, '[%d .. %d] flat values over %.0f%% of the frame'
         % (lo, hi, 100 * craftcheck.BLOCK_MIN))
    note('bands (L, share): ' + ', '.join('%.2f %.0f%%' % (b[0], 100 * b[1]) for b in bands))
    if nb < lo:
        note('only %d value bands: separate the planes (far, middle, near) into their own flat greys and keep the '
             'hero\'s light as the brightest' % nb)
    elif nb > hi:
        note('%d value bands: a block-in groups the frame into 3 value groups of at most %d greys; merge the bands '
             'closer than %.2f L and leave detail for the drawing' % (nb, hi, 0.1))
    m = craftcheck.band_map(F, bands) if bands else None
    top = None
    if bands:
        bright = m == len(bands) - 1
        lab, n = craftcheck._components(bright, bright[:, 1:] & bright[:, :-1], bright[1:] & bright[:-1])
        if n:
            size = np.bincount(lab[lab >= 0], minlength=n)
            ys, xs = np.nonzero(lab == int(np.argmax(size)))
            top = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    if hero and top:
        hb = hero['bbox']
        ex = list(hero.get('value_boxes') or [])
        bright = m == len(bands) - 1
        inside = craftcheck._boxmask(bright.shape, 1, [hb] + ex)
        share = float((bright & inside).sum() / max(1, bright.sum()))
        line('PASS' if share >= 0.5 else 'FAIL', 'focal light brightest', '%.0f%%' % (100 * share),
             '[50% .. ] of the brightest band inside the hero bbox' + (' or the named light' if ex else ''))
        if share < 0.5:
            note('the brightest grey sits mostly outside the hero (its largest patch is x %d-%d, y %d-%d): make the '
                 'hero\'s light the one brightest value' % (top[0], top[2], top[1], top[3]))
        inside_top = float(craftcheck._boxmask(m.shape, 1, [hb])[top[1]:top[3] + 1, top[0]:top[2] + 1].mean())
        line('PASS' if inside_top >= 0.8 else 'FAIL', 'hero placement', '%.0f%%' % (100 * inside_top),
             '[80% .. ] of the brightest patch inside the hero bbox')
        if inside_top < 0.8:
            note('the brightest patch is x %d-%d, y %d-%d; the brief puts the hero at x %d-%d, y %d-%d. Move the '
                 'hero\'s light onto the hero (or fix the bbox in the brief)' % (top[0], top[2], top[1], top[3], hb[0], hb[2], hb[1], hb[3]))
        # the hero's size: what inside the bbox stands out from the band around it
        r = 3
        ring = np.zeros(m.shape, bool)
        ring[max(0, hb[1] - r):hb[3] + r + 1, max(0, hb[0] - r):hb[2] + r + 1] = True
        box = craftcheck._boxmask(m.shape, 1, [hb])
        ring &= ~box
        ground = np.bincount(m[ring], minlength=len(bands)).argmax() if ring.any() else -1
        ys, xs = np.nonzero(box & (m != ground))
        if len(xs):
            drawn = (xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)
            ratio = drawn / float((hb[2] - hb[0] + 1) * (hb[3] - hb[1] + 1))
            line('PASS' if ratio >= 0.85 else 'FAIL', 'hero size', '%.0f%%' % (100 * ratio), '[85% .. ] of the planned bbox')
            if ratio < 0.85:
                note('the hero mass is x %d-%d, y %d-%d, only %.0f%% of its planned bbox: block it in at full size'
                     % (xs.min(), xs.max(), ys.min(), ys.max(), 100 * ratio))
        else:
            line('FAIL', 'hero size', '0%', 'nothing in the hero bbox stands out from its surroundings')
    else:
        line('SKIP', 'hero placement', '', 'needs a brief with a `- Hero: x0,y0,x1,y1` line')
    tagged = [p for p in planes or () if p[2] is not None]
    if planes and not tagged:
        line('SKIP', 'plane shares', '', 'no plane carries a band tag')
        note('planes: ' + ', '.join('%s %.0f%%' % (p[0], 100 * p[1]) for p in planes) + '. Untagged planes are not '
             'matched to bands; to check them, tag each with its grey: `street 45% (mid), houses 25% (dark)`')
    elif tagged and bands:
        TOL = craftcheck.BLOCK_PLANE_TOL
        want, bad = {}, []
        for name, share, tag in tagged:
            i = band_index(tag, len(bands))
            if i is None:
                bad.append('%s is tagged band %s; the block-in has %d bands' % (name, tag, len(bands)))
            else:
                want.setdefault(i, []).append((name, share))
        for i in sorted(want):
            got, need = bands[i][1], sum(s for _, s in want[i])
            if abs(need - got) > TOL:
                bad.append('band %d (L %.2f) is %.0f%% of the frame; its planes (%s) add to %.0f%%: %s that grey, or retag a plane' % (
                    i + 1, bands[i][0], 100 * got, ', '.join(n for n, _ in want[i]), 100 * need,
                    'grow' if got < need else 'shrink'))
        line('FAIL' if bad else 'PASS', 'plane shares', '%d bands' % len(want), 'each band within %.0f points of '
             'the planes tagged to it' % (100 * TOL))
        note('brief by band: ' + '; '.join('%d (L %.2f, %.0f%%): %s' % (i + 1, bands[i][0], 100 * bands[i][1], ', '.join(
            '%s %.0f%%' % (n, 100 * s) for n, s in want[i])) for i in sorted(want)))
        for b in bad:
            note(b)
        loose = [p for p in planes if p[2] is None]
        if loose:
            note('untagged, not matched: ' + ', '.join('%s %.0f%%' % (p[0], 100 * p[1]) for p in loose))
    else:
        line('SKIP', 'plane shares', '', 'needs a brief with a `- Planes: street 45% (mid), sky 20% (light)` line')
    if bands:
        e = craftcheck.blockin_empty(F, bands)
        lim = {'empty': craftcheck.COMPOSITION[style]['empty'][1] if style else None, 'empty_low': 0.88}
        for key in ('empty', 'empty_low'):
            hi = lim[key]
            if key in f_ovr:
                if f_ovr[key][0] == 'off':
                    line('SKIP', 'block-in ' + key, '%.0f%%' % (100 * e[key]), 'off by override (%s)' % f_ovr[key][2]); continue
                hi = f_ovr[key][1]
            if hi is None:
                line('PASS', 'block-in ' + key, '%.0f%%' % (100 * e[key]), 'no limit (%s)' % ('the style has none' if style else 'no --style'))
                continue
            bad = e[key] > hi
            line('FAIL' if bad else 'PASS', 'block-in ' + key, '%.0f%%' % (100 * e[key]), '[ .. %.0f%%] of coarse cells one flat value' % (100 * hi))
            if bad:
                note('%.0f%% of the %s is one flat value with no mass in it; bring a mass into it or crop' % (
                    100 * e[key], 'bottom third' if key == 'empty_low' else 'frame'))
        s = craftcheck.silhouettes(F)['slab']
        hi = craftcheck.BLOCK_SLAB
        if 'slab' in f_ovr and f_ovr['slab'][0] == 'off':
            line('SKIP', 'block-in slab', '%.0f%%' % (100 * s[0]), 'off by override (%s)' % f_ovr['slab'][2])
        else:
            hi = f_ovr['slab'][1] if 'slab' in f_ovr else hi
            line('FAIL' if s[0] > hi else 'PASS', 'block-in slab', '%.0f%%' % (100 * s[0]), '[ .. %.0f%%] one inner straight edge' % (100 * hi))
            if s[0] > hi:
                note(craftcheck.comp_advice('slab', s[0], s[1], hi))
        line('SKIP', 'block-in blocky', '', 'a block-in is made of blocks')
    if hero:
        _focus_lines(F, hero, None, line, note, f_ovr, chroma=False, size=False)
    else:
        line('SKIP', 'focus', '', 'needs a brief with a `- Hero: x0,y0,x1,y1` line')
    if brief:
        _plan_lines(img, brief_plan(brief), hero, line, note, f_ovr, scale, blockin=True)
    ok = 'FAIL' not in rows
    print('ALL PASS' if ok else 'FAIL: %d of %d checks' % (rows.count('FAIL'), len(rows) - rows.count('SKIP')))
    return ok

def frame_main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    ovr = []
    while '--budget' in a:
        ovr.append(parse_override(opt('--budget')))
    brief, image = opt('--brief'), opt('--image')
    if brief and image:
        brief = brief_for_image(brief, image)
    if brief:
        ovr = brief_overrides(brief) + ovr
    if '--blockin' in a:
        a.remove('--blockin')
        return blockin(a[0], int(opt('--scale', '1')), brief, opt('--style'), ovr)
    style, era = opt('--style'), opt('--era')
    if not style and not era:
        raise SystemExit('frame mode needs --style (one of styles.STYLES) or --era (one of era.ERAS)')
    return frame(a[0], style, int(opt('--scale', '1')), opt('--pal'), opt('--pre'), opt('--actor'),
                 [o for o in (opt('--used') or '').split(',') if o], opt('--intent'), opt('--scene'), era, ovr,
                 brief_hero(brief) if brief else None, brief_plan(brief) if brief else None)

def _run():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 1)
    if sys.argv[1].lower().endswith(IMAGE_EXT) and pathlib.Path(sys.argv[1]).is_file():
        sys.exit(0 if frame_main(sys.argv[1:]) else 1)
    import musiccheck
    if sys.argv[1].lower().endswith(musiccheck.AUDIO_EXT) and pathlib.Path(sys.argv[1]).is_file():
        sys.exit(musiccheck.main(sys.argv[1:]))
    sys.exit(0 if main(sys.argv[1], '--page' in sys.argv) else 1)

if __name__ == '__main__':
    try:
        _run()
    except BrokenPipeError:              # piped into head: the reader left, stop quietly
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
