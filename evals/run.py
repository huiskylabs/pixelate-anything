#!/usr/bin/env python3
"""Run the skill-vs-bare-model benchmark (docs/PLAN-moat.md, workstream 4).

usage: python3 evals/run.py [--tasks 01,03] [--arms bare,skill] [--runs 1] [--out evals/runs/NAME]
                            [--agent-cmd CMD] [--timeout 5400] [--refs DIR]
                            [--prompts HELD_OUT_DIR --budget-usd N --go]

Each live run gives one agent the same held-out prompt in a fresh, empty workspace. The bundled
showcase prompts may be used for planning only; they are contaminated as comparative tasks:

  bare   the model with a shell and Python (Pillow, numpy); no skill
  skill  the same, plus the pixelate-anything skill: the agent is told where the kit is and to
         follow its SKILL.md

Both arms get the same deliverable contract (out/a.png, out/b.png, out/sample.wav), timeout and
provider spend ceiling. The agent command reads the prompt on stdin, runs in the workspace, and should print JSON
with usage (the default, `claude -p --output-format json ...`, does). Without --go nothing runs: the
plan is printed. Results: OUT/<task>/<arm>-<n>/ holds the workspace, prompt.md, agent.json (stdout),
agent.err and meta.json (wall time, exit code, tokens and cost when the agent reports them).
Score them with evals/score.py.
"""
import argparse, datetime, hashlib, json, os, pathlib, shlex, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parent
PROMPTS = HERE / 'prompts'
# The bundled prompts are named NN-<library id>.md, and library/<id>/ holds each one's answer. A skill-arm
# snapshot leaves these out, and the generated catalog that lists them; the other library pieces stay.
ANSWER_PIECES = tuple('library/%s/' % p.stem.split('-', 1)[1] for p in sorted(PROMPTS.glob('*.md')))
HELD_OUT_EXCLUDED = ('examples/moments/', 'evals/', 'docs/', 'tests/', 'library/index.json') + ANSWER_PIECES
DEFAULT_AGENT = 'claude -p --output-format json --permission-mode bypassPermissions'

CONTRACT = """
## Deliverables (the same for every agent)

Work only inside the current directory. When you are done, these files must exist:
- out/a.png: still A, the first moment, at a whole-number scale (nearest neighbour)
- out/b.png: still B, the second moment, at a whole-number scale
- out/sample.wav: the 5-second sound sample (48 kHz, 16-bit, stereo)
Draw everything in code; no pasted, traced or generated images. Finish with one paragraph saying what
you made.
"""

SKILL_NOTE = """
## Tools available

The pixelate-anything skill is installed at {kit}. Read {kit}/SKILL.md first and follow it; run its
CLI as `{kit}/pixelate ...` (for example `{kit}/pixelate tools rock`, `{kit}/pixelate check`,
`{kit}/pixelate judge`). Skip the steps that ask the user to confirm: there is no user in this run;
make the choices yourself.
"""

BARE_NOTE = """
## Tools available

You have a shell and Python 3 with Pillow and numpy (and ffmpeg for audio). There is no other library
or skill for this task.
"""

def tasks(sel, prompt_dir=PROMPTS):
    found = sorted(pathlib.Path(prompt_dir).glob('*.md'))
    if sel:
        want = set(sel.split(','))
        found = [p for p in found if p.stem.split('-')[0] in want]
    if not found:
        raise SystemExit('no prompts match %s in %s' % (sel, prompt_dir))
    return found

def prompt_for(task, arm, ref=None, kit=KIT):
    text = task.read_text().strip()
    if ref:
        text += '\n\nThe reference photo is reference.jpg in this directory.'
    note = SKILL_NOTE.format(kit=kit) if arm == 'skill' else BARE_NOTE
    return text + '\n' + note + CONTRACT

def usage_of(stdout):
    """tokens and cost from the agent's JSON reply, when it reports them"""
    try:
        data = json.loads(stdout)
    except (ValueError, TypeError):
        return {}
    u = data.get('usage') or {}
    usage = {k: v for k, v in {
        'input_tokens': u.get('input_tokens'), 'output_tokens': u.get('output_tokens'),
        'cache_read_tokens': u.get('cache_read_input_tokens'), 'cache_write_tokens': u.get('cache_creation_input_tokens'),
        'cost_usd': data.get('total_cost_usd') or data.get('cost_usd'), 'turns': data.get('num_turns'),
        'agent_ms': data.get('duration_ms')}.items() if v is not None}
    if 'input_tokens' in usage and 'output_tokens' in usage:
        usage['total_tokens'] = sum(usage.get(k, 0) for k in
                                    ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens'))
    return usage

def run_one(task, arm, n, out, agent, timeout, refs, kit=KIT, budget_usd=None):
    d = out / task.stem / ('%s-%d' % (arm, n))
    ws = d / 'workspace'
    ws.mkdir(parents=True, exist_ok=True)
    ref = None
    if refs:
        cand = pathlib.Path(refs) / (task.stem.split('-')[0] + '.jpg')
        if not cand.is_file():
            raise SystemExit('missing reference photo: %s' % cand)
        shutil.copy(cand, ws / 'reference.jpg')
        ref = cand
    text = prompt_for(task, arm, ref, kit)
    (d / 'prompt.md').write_text(text)
    t = time.time()
    try:
        r = subprocess.run(shlex.split(agent), input=text, cwd=ws, capture_output=True, text=True, timeout=timeout)
        code, so, se = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        code, so, se = 'timeout', (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or ''), ''
    meta = {'task': task.stem, 'arm': arm, 'run': n, 'exit': code, 'wall_s': round(time.time() - t, 1),
            'budget_usd': budget_usd,
            'agent_cmd': agent, 'kit_rev': rev(), 'time': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    meta.update(usage_of(so))
    (d / 'agent.json').write_text(so or '')
    (d / 'agent.err').write_text(se or '')
    (d / 'meta.json').write_text(json.dumps(meta, indent=1))
    return meta

def rev():
    r = subprocess.run(['git', '-C', str(KIT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True)
    return r.stdout.strip() or None

def isolated_kit(out):
    target = out / '_kit'
    if target.exists():
        raise SystemExit('kit snapshot already exists: %s (choose a fresh --out)' % target)
    tracked = subprocess.check_output(['git', '-C', str(KIT), 'ls-files', '-z']).decode().split('\0')
    for name in tracked:
        if not name or name.startswith(HELD_OUT_EXCLUDED):
            continue
        src = KIT / name
        if not src.is_file() or src.is_symlink():
            continue
        dst = target / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return target.resolve()


def held_out_prompts(directory):
    path = pathlib.Path(directory).resolve()
    if path.is_relative_to(KIT.resolve()):
        raise SystemExit('held-out prompts must be outside the kit checkout')
    known = {hashlib.sha256(p.read_bytes()).digest() for p in PROMPTS.glob('*.md')}
    for p in path.glob('*.md'):
        if hashlib.sha256(p.read_bytes()).digest() in known:
            raise SystemExit('showcase prompt is not held out: %s' % p)
    return path


def budgeted_agent(command, budget):
    if command == DEFAULT_AGENT:
        return command + ' --max-budget-usd ' + str(budget)
    if command.count('{budget_usd}') != 1:
        raise SystemExit('custom --agent-cmd must contain {budget_usd} for its provider-enforced cap')
    return command.replace('{budget_usd}', str(budget))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('--tasks', default='', help='comma-separated task ids (default all)')
    ap.add_argument('--prompts', help='held-out .md prompt directory outside the kit; required with --go')
    ap.add_argument('--budget-usd', type=float, help='same provider-enforced spend ceiling per run; required with --go')
    ap.add_argument('--arms', default='bare,skill')
    ap.add_argument('--runs', type=int, default=1)
    ap.add_argument('--out', default=None)
    ap.add_argument('--agent-cmd', default=os.environ.get('PIXELATE_EVAL_AGENT', DEFAULT_AGENT))
    ap.add_argument('--timeout', type=int, default=5400, help='seconds per run (the same for both arms)')
    ap.add_argument('--refs', default=None, help='folder with NN.jpg reference photos for the rebuild tasks')
    ap.add_argument('--go', action='store_true', help='actually run the agents (it costs tokens)')
    a = ap.parse_args(argv)
    arms = [x for x in a.arms.split(',') if x]
    bad = [x for x in arms if x not in ('bare', 'skill')]
    if bad:
        ap.error('unknown arm(s): %s' % ', '.join(bad))
    out = pathlib.Path(a.out or HERE / 'runs' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S')).resolve()
    if a.go:
        if not a.prompts or not a.budget_usd or a.budget_usd <= 0:
            ap.error('--go requires --prompts outside the kit and a positive --budget-usd')
        prompt_dir = held_out_prompts(a.prompts)
        agent = budgeted_agent(a.agent_cmd, a.budget_usd)
    else:
        prompt_dir, agent = pathlib.Path(a.prompts or PROMPTS), a.agent_cmd
    selected = tasks(a.tasks, prompt_dir)
    if a.go and a.refs:
        missing = [str(pathlib.Path(a.refs) / (t.stem.split('-')[0] + '.jpg')) for t in selected
                   if not (pathlib.Path(a.refs) / (t.stem.split('-')[0] + '.jpg')).is_file()]
        if missing:
            ap.error('missing reference photo(s): ' + ', '.join(missing))
    plan = [(t, arm, n) for t in selected for n in range(1, a.runs + 1) for arm in arms]
    print('%d runs -> %s   agent: %s   timeout %ds' % (len(plan), out, agent, a.timeout))
    for t, arm, n in plan:
        print('  %-24s %-5s run %d' % (t.stem, arm, n))
    if not a.go:
        print('dry run: add --go to run them (each run is a full agent session and costs tokens)')
        return
    kit = isolated_kit(out)
    for t, arm, n in plan:
        meta = run_one(t, arm, n, out, agent, a.timeout, a.refs, kit, a.budget_usd)
        print('%-24s %-5s run %d: exit %s, %.0fs, %s tokens out' % (t.stem, arm, n, meta['exit'], meta['wall_s'],
                                                                  meta.get('output_tokens', '?')))
    print('score with: python3 evals/score.py %s' % out)

if __name__ == '__main__':
    main()
