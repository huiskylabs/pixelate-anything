#!/usr/bin/env python3
"""Render a scene's picture loop frame by frame (Node) and encode it (ffmpeg).

Every frame is a pure function of its tick, so the TICKS frames of one picture
loop are rendered exactly, scaled by whole pixels (nearest neighbour), converted
to BT.709 4:2:0 with chroma kept inside each art pixel (even scales), and encoded
as H.264. Add the soundtrack with --audio (a loop WAV from render_audio.py).

usage:
  render_video.py SCENE_DIR out.mp4 [--scale S] [--crf C] [--preset P] [--frames K0:K1]
                  [--audio loop.wav] [--gain dB]
  render_video.py SCENE_DIR --info            canvas size, ticks, phase timing
  render_video.py SCENE_DIR --hash k [k...]   frame hashes (determinism checks)
  render_video.py SCENE_DIR --png k out.png [--scale S]   one frame as a PNG
  render_video.py SCENE_DIR --gif out.gif [--scale S] [--fps 15] [--frames K0:K1]
                  animated GIF (no sound) for social posts and READMEs; keep it short:
                  design a scene with a small cycle (one phase, few bars) for a GIF that loops

Defaults: --scale picks the largest whole scale with height <= 1080 (use --scale 8
on a 480x270 canvas for 4K); --crf 14; --preset slow.
"""
import json, pathlib, subprocess, sys, tempfile, time

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / 'tools'))
import build

DRIVER = r"""
const fs = require('fs');
initPalettes();
function fnv(u8) { let h = 0x811c9dc5; for (let i = 0; i < u8.length; i++) { h ^= u8[i]; h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); }
function writeAll(buf) {
  let off = 0;
  while (off < buf.length) {
    try { off += fs.writeSync(1, buf, off, buf.length - off); }
    catch (e) { if (e.code !== 'EAGAIN') throw e; Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2); }
  }
}
const mode = process.argv[2];
if (mode === 'info') {
  console.error(JSON.stringify({ W, H, TICKS, HZ, CYCLE, GRAND, loopSeconds: TICKS / HZ,
    bpm: TIMELINE.bpm.map(b => +b.toFixed(2)), baseBpm: BASE_BPM,
    segments: TIMELINE.seg.map(g => ({ kind: g.kind, phase: SCENE.phases[g.s].name, start: +g.start.toFixed(2), dur: +g.dur.toFixed(2) })),
    warnings: SPRITE_WARN.concat(PALETTE_WARN).slice(0, 40) }));
} else if (mode === 'hash') {
  const out = new Uint32Array(NPX), res = {};
  for (const a of process.argv.slice(3)) { renderFrame(+a, out); res[a] = fnv(new Uint8Array(out.buffer)); }
  console.error(JSON.stringify(res));
} else if (mode === 'frames') {
  const k0 = +process.argv[3], k1 = +process.argv[4], t0 = Date.now();
  for (let k = k0; k < k1; k++) {
    const out = new Uint32Array(NPX);
    renderFrame(mod(k, TICKS), out);
    writeAll(Buffer.from(out.buffer));
    if ((k - k0) % 1800 === 1799) console.error('  frames ' + (k + 1 - k0) + '/' + (k1 - k0) + ' ' + ((Date.now() - t0) / 1000).toFixed(0) + ' s');
  }
}
"""

def bundle(scene):
    js = build.scene_js(scene, with_audio=False, with_main=False) + DRIVER
    fn = pathlib.Path(tempfile.gettempdir()) / ('pixelate-anything-%s.js' % abs(hash(str(pathlib.Path(scene).resolve()))))
    fn.write_text(js)
    return fn

def node(scene, *args):
    r = subprocess.run(['node', str(bundle(scene))] + [str(a) for a in args], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr); sys.exit(1)
    return r.stderr

def info(scene):
    return json.loads(node(scene, 'info'))

def frames(scene, k0, k1):
    """raw RGBA frames (bytes) for ticks k0..k1-1"""
    r = subprocess.run(['node', str(bundle(scene)), 'frames', str(k0), str(k1)], capture_output=True)
    if r.returncode:
        print(r.stderr.decode()); sys.exit(1)
    return r.stdout

def png(scene, k, out, scale=1):
    from PIL import Image
    i = info(scene)
    im = Image.frombytes('RGBA', (i['W'], i['H']), frames(scene, k, k + 1)).convert('RGB')
    if scale > 1:
        im = im.resize((i['W'] * scale, i['H'] * scale), Image.NEAREST)
    im.save(out)
    print('wrote', out)

def encode(scene, out, scale=None, k0=0, k1=None, crf=14, preset='slow', audio=None, gain=0.0):
    i = info(scene)
    W, H = i['W'], i['H']
    if i['warnings']:
        print('warnings:', *i['warnings'], sep='\n  ')
    scale = scale or max(1, 1080 // H)
    if scale % 2:
        print('note: odd scale %d: 4:2:0 colour may bleed one pixel at colour edges; even scales are exact' % scale)
    k1 = i['TICKS'] if k1 is None else k1
    vf = ('scale=%d:%d:flags=neighbor,'
          'scale=out_color_matrix=bt709:out_range=tv:flags=neighbor,format=yuv420p') % (W * scale, H * scale)
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostats', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '%dx%d' % (W, H), '-framerate', str(i['HZ']), '-i', 'pipe:0']
    if audio:
        cmd += ['-i', str(audio)]
    cmd += ['-vf', vf, '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-tune', 'animation',
            '-g', '240', '-keyint_min', '30', '-profile:v', 'high',
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']
    if audio:
        cmd += ['-map', '0:v:0', '-map', '1:a:0', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-shortest']
        if gain:
            cmd += ['-af', 'volume=%.2fdB' % gain]
    else:
        cmd += ['-an']
    cmd += ['-movflags', '+faststart', str(out)]
    t0 = time.time()
    pn = subprocess.Popen(['node', str(bundle(scene)), 'frames', str(k0), str(k1)], stdout=subprocess.PIPE)
    pf = subprocess.Popen(cmd, stdin=pn.stdout)
    pn.stdout.close()
    rf, rn = pf.wait(), pn.wait()
    if rf or rn:
        print('failed: ffmpeg %s node %s' % (rf, rn)); sys.exit(1)
    dt = time.time() - t0
    size = pathlib.Path(out).stat().st_size
    print('%s: %dx%d (%dx), %d frames in %.0f s, %.1f MB' % (out, W * scale, H * scale, scale, k1 - k0, dt, size / 1e6))

def gif(scene, out, scale=None, fps=15, k0=0, k1=None):
    """GIF via ffmpeg: one palette for the whole clip, no dithering (the art is already palettised)"""
    i = info(scene)
    W, H = i['W'], i['H']
    scale = scale or max(1, 540 // H)
    k1 = i['TICKS'] if k1 is None else k1
    step = max(1, round(30 / fps))
    raw = frames(scene, k0, k1)
    n = (k1 - k0)
    fsz = W * H * 4
    sel = b''.join(raw[j * fsz:(j + 1) * fsz] for j in range(0, n, step))
    vf = ('scale=%d:%d:flags=neighbor,split[a][b];[a]palettegen=max_colors=256:stats_mode=full:reserve_transparent=0[p];'
          '[b][p]paletteuse=dither=none') % (W * scale, H * scale)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '%dx%d' % (W, H),
                    '-framerate', '%g' % (30 / step), '-i', 'pipe:0', '-vf', vf, '-loop', '0', str(out)], input=sel, check=True)
    print('wrote %s: %dx%d, %d frames at %g fps, %.1f MB' % (out, W * scale, H * scale, len(range(0, n, step)), 30 / step,
          pathlib.Path(out).stat().st_size / 1e6))
    if i['TICKS'] % step:
        print('note: the loop length is not a whole number of GIF frames; the GIF may not loop seamlessly')

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__); sys.exit(1)
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    scene = a.pop(0)
    if a[0] == '--info':
        print(json.dumps(info(scene), indent=1))
    elif a[0] == '--hash':
        print(node(scene, 'hash', *a[1:]).strip())
    elif a[0] == '--gif':
        sc = opt('--scale'); fr = opt('--frames'); fps = float(opt('--fps', '15'))
        k0, k1 = (int(x) for x in fr.split(':')) if fr else (0, None)
        gif(scene, a[1], int(sc) if sc else None, fps, k0, k1)
    elif a[0] == '--png':
        sc = int(opt('--scale', '1'))
        png(scene, int(a[1]), a[2], sc)
    else:
        sc = opt('--scale'); fr = opt('--frames')
        k0, k1 = (int(x) for x in fr.split(':')) if fr else (0, None)
        encode(scene, a[0], int(sc) if sc else None, k0, k1, opt('--crf', '14'), opt('--preset', 'slow'),
               opt('--audio'), float(opt('--gain', '0')))
