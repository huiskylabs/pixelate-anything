#!/usr/bin/env python3
"""Automated checks before every delivery: a scene, or one frame against its style (the gate).

usage: check.py SCENE_DIR [--page]
       check.py FRAME.png --style S --scale N [--pal palette.json] [--pre prelight.png]
                [--actor actor_mask.png] [--used op,op] [--intent mask.png]

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
     around it by READ_DL in rim or fill L, or READ_HUE degrees (stats.readability)
  6. craft: orphans, jaggies, stripes, doubled outlines, pillow shading and clusters inside
     the style's craftcheck.CRAFT limits (--intent marks sparkles and flecks placed on purpose)
Each check prints PASS, FAIL or SKIP with the measured value and the limit.
Exit status 1 if anything fails.
"""
import asyncio, pathlib, sys
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

def frame(path, style, scale=1, pal=None, pre=None, actor=None, used=(), intent=None):
    """the delivery gate for one frame: print a PASS / FAIL / SKIP line per check, return True
    when nothing fails"""
    from PIL import Image
    import stats, styles, craftcheck
    st = styles.get(style)
    big = Image.open(path).convert('RGB')
    rows = []
    def line(state, what, value='', limit=''):
        rows.append(state)
        print('%-4s %-26s %-12s %s' % (state, what, value, limit))
    W, H = big.size
    if W % scale or H % scale:
        line('FAIL', 'scale', '%dx%d' % (W, H), 'not a whole multiple of %d' % scale)
    img = stats.to_native(big, scale) if scale > 1 else big
    print('%s: %s style, %dx%d at 1x (x%d)' % (path, st['name'], img.size[0], img.size[1], scale))
    for key, v, lo, hi, state in stats.budget_report(img, st['name']):
        lim = '[%s .. %s]' % (stats._fmt(key, lo) if lo is not None else '', stats._fmt(key, hi) if hi is not None else '')
        line({'ok': 'PASS', 'fail': 'FAIL', 'skip': 'SKIP'}[state], 'budget ' + key, stats._fmt(key, v),
             lim + (' (needs masks)' if state == 'skip' else ''))
    if not st['budgets']:
        line('SKIP', 'budget', '', 'the style has no budget')
    if st['native_cells'] is not None and scale > 1:
        soft = stats.native_cells(big, scale)
        line('PASS' if soft <= st['native_cells'] else 'FAIL', 'native cells %dx%d' % (scale, scale),
             '%.2f%%' % (100 * soft), '[ .. %.2f%%] soft cells' % (100 * st['native_cells']))
    elif st['native_cells'] is None:
        line('SKIP', 'native cells', '', 'screen-resolution light layer')
    for op in used:
        line('PASS' if styles.allows(st['name'], op) else 'FAIL', 'post op ' + op, '',
             'allowed' if styles.allows(st['name'], op) else 'banned or not part of %s' % st['name'])
    if pal:
        src = pre
        if src is None and st['res'] != 'none':
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
    if actor:
        m = _load_mask(actor, (img.size[1], img.size[0]), scale)
        r = stats.readability(img, m)
        good = (abs(r['edge_dL']) >= READ_DL or abs(r['fill_dL']) >= READ_DL or
                (r['dhue'] == r['dhue'] and r['dhue'] >= READ_HUE))
        line('PASS' if good else 'FAIL', 'readability (actor)',
             'rim %+.2f fill %+.2f hue %s' % (r['edge_dL'], r['fill_dL'], '-' if r['dhue'] != r['dhue'] else '%.0f' % r['dhue']),
             '|rim| or |fill| >= %.2f L, or hue >= %.0f' % (READ_DL, READ_HUE))
    imask = _load_mask(intent, (img.size[1], img.size[0]), scale) if intent else None
    for key, v, lo, hi, state in craftcheck.report(img, st['name'], intent=imask):
        lim = '[%s .. %s]' % (craftcheck.fmt(key, lo) if lo is not None else '', craftcheck.fmt(key, hi) if hi is not None else '')
        line('PASS' if state == 'ok' else 'FAIL', 'craft ' + key, craftcheck.fmt(key, v), lim)
    ok = 'FAIL' not in rows
    print('ALL PASS' if ok else 'FAIL: %d of %d checks' % (rows.count('FAIL'), len(rows) - rows.count('SKIP')))
    return ok

def frame_main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    style = opt('--style')
    if not style:
        raise SystemExit('frame mode needs --style (one of styles.STYLES)')
    return frame(a[0], style, int(opt('--scale', '1')), opt('--pal'), opt('--pre'), opt('--actor'),
                 [o for o in (opt('--used') or '').split(',') if o], opt('--intent'))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if sys.argv[1].lower().endswith(IMAGE_EXT) and pathlib.Path(sys.argv[1]).is_file():
        sys.exit(0 if frame_main(sys.argv[1:]) else 1)
    sys.exit(0 if main(sys.argv[1], '--page' in sys.argv) else 1)
