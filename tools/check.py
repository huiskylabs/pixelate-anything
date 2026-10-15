#!/usr/bin/env python3
"""Automated checks for a scene. Run before every delivery.

usage: check.py SCENE_DIR [--page]

  1. sprites and palettes: unknown sprite keys, slots missing a colour
  2. timing: the cycle fits the phases' natural length (tempos barely scaled)
  3. determinism: a frame renders the same twice (no Math.random, no state)
  4. loop seam: the jump from the last frame back to frame 0 is no bigger than
     ordinary steps at the same animation phase (every period divides the loop)
  5. --page: the built page loads without errors and the play button starts audio
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

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    sys.exit(0 if main(sys.argv[1], '--page' in sys.argv) else 1)
