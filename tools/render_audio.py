#!/usr/bin/env python3
"""Render one picture loop of a scene's soundtrack, seeded so it repeats exactly.

The render starts PRE seconds early (reverb, compressor and note tails are already
running at the loop point), keeps exactly one picture loop (CYCLE * GRAND seconds),
then checks that the audio after the loop matches the audio at its start: proof
that the file plays seamlessly on repeat. Needs Playwright's Chromium.

usage: render_audio.py SCENE_DIR out.wav
Long renders cost more than linearly (every note is scheduled up front): a 6 minute
loop takes roughly 8 minutes on two cores.
"""
import asyncio, base64, pathlib, struct, subprocess, sys
import numpy as np
from playwright.async_api import async_playwright

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / 'tools'))
import build

SR, PRE, POST = 48000, 30, 6
RENDER = """
async ([v0, sec]) => {
  const t0 = performance.now();
  window.__AUD = await window.LOFI.renderOffline(v0, sec, 48000, null, true);
  return { ms: performance.now() - t0, n: window.__AUD.length };
}
"""
CHUNK = """
([ch, i0, n]) => {
  const d = window.__AUD.getChannelData(ch).subarray(i0, i0 + n);
  const u = new Uint8Array(d.buffer, d.byteOffset, d.byteLength);
  let s = '';
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
  return btoa(s);
}
"""

def write_wav_f32(fn, x):
    data = x.astype('<f4').tobytes()
    hdr = b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVE'
    hdr += b'fmt ' + struct.pack('<IHHIIHH', 16, 3, 2, SR, SR * 8, 8, 32)
    hdr += b'data' + struct.pack('<I', len(data))
    with open(fn, 'wb') as f:
        f.write(hdr); f.write(data)

async def main(scene, out):
    page = build.build(scene)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(page.resolve().as_uri() + '?freeze=1&t=0')
        await pg.wait_for_timeout(300)
        if not await pg.evaluate('!!window.LOFI'):
            print('this scene has no music.js'); sys.exit(1)
        loop = int(round(await pg.evaluate('CYCLE * GRAND')))
        v0, sec = loop - PRE, PRE + loop + POST
        res = await pg.evaluate(RENDER, [v0, sec])
        print('rendered %.0f s of audio in %.0f s' % (res['n'] / SR, res['ms'] / 1000), flush=True)
        n, step, chans = res['n'], SR * 10, []
        for ch in (0, 1):
            parts = []
            for i0 in range(0, n, step):
                s = await pg.evaluate(CHUNK, [ch, i0, min(step, n - i0)])
                parts.append(np.frombuffer(base64.b64decode(s), dtype='<f4'))
            chans.append(np.concatenate(parts))
        await b.close()
    if errs:
        print('page errors:', errs)
    x = np.stack(chans, axis=1)
    a0 = PRE * SR
    head, tail = x[a0:a0 + POST * SR], x[a0 + loop * SR:a0 + loop * SR + POST * SR]
    d = tail - head
    db = 20 * np.log10(np.sqrt(np.mean(d ** 2)) / (np.sqrt(np.mean(head ** 2)) + 1e-12) + 1e-15)
    print('loop check: audio after the loop vs its start: %.1f dB (below -60 dB is seamless)' % db)
    clip = x[a0:a0 + loop * SR]
    print('peak %.3f, rms %.1f dBFS' % (np.abs(clip).max(), 20 * np.log10(np.sqrt(np.mean(clip ** 2)))))
    write_wav_f32(out, clip)
    print('wrote', out, '(%d s)' % loop)
    if db > -60:
        print('WARNING: the loop is not seamless; see references/music.md (continuous sources must fit the loop)')
        sys.exit(2)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
