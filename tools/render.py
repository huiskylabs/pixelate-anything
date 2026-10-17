#!/usr/bin/env python3
"""pixelate render DIR [--image NAME] [--no-run] [--critique] [--json]

One command from art to a verified still. DIR/render.json names each image: the command that draws
it, the frame it writes and how it is gated. For every image, render runs the command, gates the
frame (`pixelate check`, with the brief's `## Image NAME` lines via --image), era-checks it when it
names an era, judges it (`pixelate judge`, overlay beside the frame, logged to the corpus) and, with
--critique, runs the art director (`pixelate critique --run`). It prints one compact line per image
and writes DIR/render-report.json; it exits 1 when any image fails its command or its gate.

render.json:

    {"images": [
      {"name": "a", "run": "python3 art/render.py a", "frame": "out/01-a.png",
       "style": "cosy-lightmap", "scene": "exterior", "scale": 4, "brief": "brief.md",
       "pal": "out/palette.json", "pre": "out/01-a@1x.png", "used": "light,shaft",
       "actor": "", "era": "", "judge_ignore": ""}
    ]}

Paths are relative to DIR. `run` may be omitted for a frame drawn some other way; `style` or `era` is
required for the gate.
"""
import argparse, json, os, pathlib, re, shlex, subprocess, sys, time

KIT = pathlib.Path(__file__).resolve().parent.parent
PIXELATE = [sys.executable, str(KIT / 'pixelate')]
GATE_FLAGS = (('style', '--style'), ('scene', '--scene'), ('era', '--era'), ('pal', '--pal'), ('pre', '--pre'),
              ('actor', '--actor'), ('used', '--used'), ('intent', '--intent'))

def load(dirpath):
    spec = pathlib.Path(dirpath) / 'render.json'
    if not spec.is_file():
        raise SystemExit('no render.json in %s (see `pixelate render --help`)' % dirpath)
    data = json.loads(spec.read_text())
    images = data.get('images') if isinstance(data, dict) else data
    if not images:
        raise SystemExit('render.json lists no images')
    for im in images:
        for k in ('name', 'frame'):
            if not im.get(k):
                raise SystemExit('every image in render.json needs "%s"' % k)
        if not (im.get('style') or im.get('era')):
            raise SystemExit('image %s needs "style" or "era" for the gate' % im['name'])
    return images

def _tail(text, n=6):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return '\n'.join(lines[-n:])

def gate_args(im):
    args = ['check', im['frame'], '--scale', str(im.get('scale', 1))]
    for key, flag in GATE_FLAGS:
        if im.get(key):
            args += [flag, str(im[key])]
    if im.get('brief'):
        args += ['--brief', im['brief'], '--image', im['name']]
    return args

def render_one(d, im, run=True, critique=False):
    rec = {'name': im['name'], 'frame': im['frame']}
    if run and im.get('run'):
        t = time.time()
        r = subprocess.run(im['run'], shell=True, cwd=d, capture_output=True, text=True)
        rec['run'] = {'ok': r.returncode == 0, 'seconds': round(time.time() - t, 1)}
        if r.returncode:
            rec['run']['error'] = _tail(r.stderr or r.stdout)
            return rec
    if not (d / im['frame']).is_file():
        rec['error'] = 'frame not found: %s' % im['frame']
        return rec
    g = subprocess.run(PIXELATE + gate_args(im), cwd=d, capture_output=True, text=True)
    fails = [l.strip() for l in g.stdout.splitlines() if re.match(r'^\s*FAIL\b', l)]
    passes = [l for l in g.stdout.splitlines() if re.match(r'^\s*PASS\b', l)]
    rec['gate'] = {'ok': g.returncode == 0, 'pass': len(passes), 'fail': fails[:8]}
    if g.returncode and not fails:
        rec['gate']['error'] = _tail(g.stderr or g.stdout)
    if im.get('era'):
        e = subprocess.run(PIXELATE + ['era', im['frame'], '--era', im['era']], cwd=d, capture_output=True, text=True)
        rec['era'] = {'ok': e.returncode == 0, 'report': _tail(e.stdout, 3)}
    frame = d / im['frame']
    overlay = frame.with_suffix('.judge.png')
    jargs = ['judge', im['frame'], '--json', '--overlay', str(overlay.relative_to(d)), '--log', '--note', 'render']
    if im.get('scale'):
        jargs += ['--scale', str(im['scale'])]
    if im.get('judge_ignore'):
        jargs += ['--ignore', im['judge_ignore']]
    j = subprocess.run(PIXELATE + jargs, cwd=d, capture_output=True, text=True)
    if j.returncode == 0:
        found = json.loads(j.stdout)['defects']
        rec['judge'] = {'defects': [{k: x[k] for k in ('id', 'kind', 'box', 'severity')} for x in found],
                        'overlay': str(overlay.relative_to(d)) if found else None}
    else:
        rec['judge'] = {'error': _tail(j.stderr or j.stdout)}
    if critique and im.get('brief'):
        c = subprocess.run(PIXELATE + ['critique', im['frame'], '--brief', im['brief'], '--run', '--log'],
                           cwd=d, capture_output=True, text=True)
        saved = re.search(r'^saved: (.+)$', c.stdout, re.M)
        grade = re.search(r'^GRADE:\s*([ABC])', c.stdout, re.M)
        rec['critique'] = {'ok': c.returncode == 0, 'grade': grade.group(1) if grade else None,
                           'file': saved.group(1) if saved else None}
        if c.returncode:
            rec['critique']['error'] = _tail(c.stderr or c.stdout, 2)
    return rec

def line(rec):
    parts = [rec['name']]
    if 'run' in rec:
        parts.append('run ok %.1fs' % rec['run']['seconds'] if rec['run']['ok'] else 'RUN FAILED')
    if rec.get('error'):
        parts.append(rec['error'])
    if 'gate' in rec:
        g = rec['gate']
        parts.append('gate PASS (%d lines)' % g['pass'] if g['ok'] else 'gate FAIL: ' + ('; '.join(g['fail'][:3]) or g.get('error', '')))
    if 'era' in rec:
        parts.append('era ok' if rec['era']['ok'] else 'era FAIL')
    if 'judge' in rec:
        jd = rec['judge']
        if 'error' in jd:
            parts.append('judge error')
        else:
            ks = [x['kind'] for x in jd['defects']]
            parts.append('judge: ' + (', '.join('%d %s' % (ks.count(k), k) for k in dict.fromkeys(ks)) if ks else 'clean')
                         + (' (overlay %s)' % jd['overlay'] if jd.get('overlay') else ''))
    if 'critique' in rec:
        cr = rec['critique']
        parts.append('critique %s' % (cr['grade'] or '?') if cr['ok'] else 'critique failed')
    return ' | '.join(parts)

def ok(rec):
    return rec.get('run', {'ok': True})['ok'] and not rec.get('error') and rec.get('gate', {}).get('ok', False) \
        and rec.get('era', {'ok': True})['ok']

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pixelate render', description=(__doc__ or '').split('\n\n')[1])
    ap.add_argument('dir')
    ap.add_argument('--image', default=None, help='only this image')
    ap.add_argument('--no-run', action='store_true', help='skip the draw commands; gate and judge what is there')
    ap.add_argument('--critique', action='store_true', help='also run the art director (pixelate critique --run)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    d = pathlib.Path(a.dir).resolve()
    images = [im for im in load(d) if not a.image or im['name'] == a.image]
    if not images:
        raise SystemExit('no image named %s in render.json' % a.image)
    recs = [render_one(d, im, not a.no_run, a.critique) for im in images]
    (d / 'render-report.json').write_text(json.dumps(recs, indent=1))
    if a.json:
        print(json.dumps(recs, indent=1))
    else:
        for r in recs:
            print(line(r))
        print('report: %s' % (d / 'render-report.json'))
    sys.exit(0 if all(ok(r) for r in recs) else 1)

if __name__ == '__main__':
    main()
