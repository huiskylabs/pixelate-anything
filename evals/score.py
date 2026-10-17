#!/usr/bin/env python3
"""Score a benchmark run directory written by evals/run.py and compare the arms.

usage: python3 evals/score.py RUNS_DIR [--critique] [--json]

For every run it checks the deliverables (out/a.png, out/b.png, out/sample.wav), judges both stills
with `pixelate judge` (defect count and summed severity: lower is better), measures the sample
(seconds, peak, clipping) and, with --critique, asks a blind art director for a grade
(`pixelate critique --run` against a brief made from the task prompt; the critic never sees which
arm made the image). It writes RUNS_DIR/scores.json and prints one table per task and a summary
per arm: delivered, wall time, tokens, cost, judge defects and grades. Both arms are judged by the
same repo tools, so the judge favours neither: it was calibrated on accepted art, not on arm output.
"""
import argparse, json, pathlib, re, subprocess, sys, wave

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(KIT / 'tools'))
PIXELATE = [sys.executable, str(KIT / 'pixelate')]

def sample_info(p):
    try:
        import numpy as np
        with wave.open(str(p)) as w:
            n, sr, ch, sw = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(n)
        dt = {1: np.int8, 2: np.int16, 4: np.int32}[sw]
        a = np.frombuffer(raw, dt).astype(float) / float(np.iinfo(dt).max)
        peak = float(np.abs(a).max()) if len(a) else 0.0
        return {'seconds': round(n / float(sr), 2), 'rate': sr, 'channels': ch, 'peak': round(peak, 3),
                'clipped': bool(peak >= 0.999)}
    except Exception as e:                          # a broken file is a result, not a crash
        return {'error': str(e)[:120]}

def judge(img):
    r = subprocess.run(PIXELATE + ['judge', str(img), '--json'], capture_output=True, text=True)
    if r.returncode:
        return {'error': (r.stderr or r.stdout).strip()[-200:]}
    found = json.loads(r.stdout)['defects']
    return {'defects': len(found), 'severity': round(sum(d['severity'] for d in found), 2),
            'kinds': sorted({d['kind'] for d in found}), 'scale': json.loads(r.stdout)['scale']}

def critique(img, prompt_md, work):
    brief = work / 'blind-brief.md'
    text = prompt_md.read_text()
    first = text.strip().split('\n\n')[0].replace('\n', ' ')
    brief.write_text('Request: %s\n\n## 0. Choices to confirm\n\n%s\n' % (first, text.split('## Tools available')[0].strip()))
    r = subprocess.run(PIXELATE + ['critique', str(img), '--brief', str(brief), '--run', '--save',
                                   str(work / ('blind-critique-%s.md' % img.stem))], capture_output=True, text=True)
    g = re.search(r'^GRADE:\s*([ABC])', r.stdout, re.M)
    return g.group(1) if g else None

def score_run(d, do_critique=False):
    meta = json.loads((d / 'meta.json').read_text())
    ws = d / 'workspace'
    rec = {k: meta.get(k) for k in ('task', 'arm', 'run', 'exit', 'wall_s', 'output_tokens', 'input_tokens', 'cost_usd', 'turns')}
    files = {k: ws / 'out' / f for k, f in (('a', 'a.png'), ('b', 'b.png'), ('sample', 'sample.wav'))}
    rec['delivered'] = {k: p.is_file() for k, p in files.items()}
    for k in ('a', 'b'):
        if files[k].is_file():
            rec['judge_' + k] = judge(files[k])
            if do_critique:
                rec['grade_' + k] = critique(files[k], d / 'prompt.md', d)
    if files['sample'].is_file():
        rec['sample'] = sample_info(files['sample'])
    return rec

def summarise(recs):
    arms = {}
    for r in recs:
        s = arms.setdefault(r['arm'], {'runs': 0, 'delivered_all': 0, 'wall_s': [], 'output_tokens': [], 'cost_usd': [],
                                       'defects': [], 'severity': [], 'grades': []})
        s['runs'] += 1
        s['delivered_all'] += all(r['delivered'].values())
        for k in ('wall_s', 'output_tokens', 'cost_usd'):
            if isinstance(r.get(k), (int, float)):
                s[k].append(r[k])
        for k in ('a', 'b'):
            j = r.get('judge_' + k) or {}
            if 'defects' in j:
                s['defects'].append(j['defects'])
                s['severity'].append(j['severity'])
            if r.get('grade_' + k):
                s['grades'].append(r['grade_' + k])
    mean = lambda v: round(sum(v) / len(v), 2) if v else None
    return {arm: {'runs': s['runs'], 'delivered_all': s['delivered_all'], 'mean_wall_s': mean(s['wall_s']),
                  'mean_output_tokens': mean(s['output_tokens']), 'mean_cost_usd': mean(s['cost_usd']),
                  'mean_defects_per_still': mean(s['defects']), 'mean_severity_per_still': mean(s['severity']),
                  'grades': {g: s['grades'].count(g) for g in 'ABC' if g in s['grades']}}
            for arm, s in sorted(arms.items())}

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('runs')
    ap.add_argument('--critique', action='store_true', help='blind art-director grades (costs tokens)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    root = pathlib.Path(a.runs)
    dirs = sorted(p.parent for p in root.glob('*/*/meta.json'))
    if not dirs:
        raise SystemExit('no runs (*/*/meta.json) in %s' % root)
    recs = [score_run(d, a.critique) for d in dirs]
    out = {'runs': recs, 'summary': summarise(recs)}
    (root / 'scores.json').write_text(json.dumps(out, indent=1))
    if a.json:
        print(json.dumps(out, indent=1))
        return
    print('%-24s %-5s %-3s %-9s %7s %9s %8s %8s %6s' % ('task', 'arm', 'n', 'delivered', 'wall s', 'tokens out',
                                                        'defects', 'severity', 'grades'))
    for r in recs:
        dl = ''.join(k if v else '-' for k, v in r['delivered'].items())
        dfs = sum((r.get('judge_' + k) or {}).get('defects', 0) for k in 'ab')
        sev = sum((r.get('judge_' + k) or {}).get('severity', 0) for k in 'ab')
        gr = ''.join(r.get('grade_' + k) or '.' for k in 'ab')
        print('%-24s %-5s %-3s %-9s %7s %9s %8d %8.2f %6s' % (r['task'], r['arm'], r['run'], dl, r.get('wall_s'),
                                                              r.get('output_tokens'), dfs, sev, gr))
    print()
    for arm, s in out['summary'].items():
        print('%-5s %s' % (arm, json.dumps(s)))
    print('scores: %s' % (root / 'scores.json'))

if __name__ == '__main__':
    main()
