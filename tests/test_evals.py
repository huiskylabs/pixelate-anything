import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evals'))
import run  # noqa: E402
import score  # noqa: E402


class RunTest(unittest.TestCase):
    def test_ten_prompts_and_arm_notes(self):
        self.assertEqual(len(run.tasks('')), 10)
        task = run.tasks('03')[0]
        skill, bare = run.prompt_for(task, 'skill'), run.prompt_for(task, 'bare')
        self.assertIn('SKILL.md', skill)
        self.assertNotIn('SKILL.md', bare)
        for text in (skill, bare):
            self.assertIn('out/sample.wav', text)
            self.assertIn(task.read_text().strip()[:60], text)

    def test_dry_run_runs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(ROOT / 'evals' / 'run.py'), '--tasks', '01,05', '--out', tmp],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('4 runs', r.stdout)
            self.assertIn('dry run', r.stdout)
            self.assertEqual(list(pathlib.Path(tmp).iterdir()), [])

    def test_usage_parsed_from_agent_json(self):
        u = run.usage_of(json.dumps({'usage': {'input_tokens': 10, 'output_tokens': 20,
                                                'cache_read_input_tokens': 5}, 'total_cost_usd': 0.5,
                                     'num_turns': 3}))
        self.assertEqual((u['output_tokens'], u['cost_usd'], u['turns'], u['total_tokens']), (20, 0.5, 3, 35))
        self.assertEqual(run.usage_of('not json'), {})

    def test_go_with_a_fake_agent_writes_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'agent.py'
            fake.write_text('import json, sys\nsys.stdin.read()\nprint(json.dumps({"usage": {"output_tokens": 7}}))\n')
            prompts = pathlib.Path(tmp) / 'prompts'
            prompts.mkdir()
            (prompts / '99-fresh.md').write_text('An unseen scene. Draw two moments from this photo.')
            refs = pathlib.Path(tmp, 'refs')
            refs.mkdir()
            (refs / '99.jpg').write_bytes(b'photo bytes')
            r = subprocess.run([sys.executable, str(ROOT / 'evals' / 'run.py'), '--tasks', '99', '--arms', 'bare,skill',
                                '--prompts', str(prompts), '--refs', str(refs), '--budget-usd', '1', '--out', tmp + '/runs',
                                '--agent-cmd', '%s %s {budget_usd}' % (sys.executable, fake), '--go'],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            meta = json.loads(next(pathlib.Path(tmp, 'runs').glob('*/bare-1/meta.json')).read_text())
            self.assertEqual((meta['arm'], meta['exit'], meta['output_tokens'], meta['budget_usd']),
                             ('bare', 0, 7, 1.0))
            kit = pathlib.Path(tmp, 'runs', '_kit')
            self.assertTrue((kit / 'SKILL.md').is_file())
            self.assertFalse((kit / 'examples' / 'moments').exists())
            self.assertFalse((kit / 'evals').exists())
            smoke = subprocess.run([sys.executable, str(kit / 'pixelate'), 'tools', 'rock'],
                                   capture_output=True, text=True)
            self.assertEqual(smoke.returncode, 0, smoke.stderr)
            skill_prompt = next(pathlib.Path(tmp, 'runs').glob('*/skill-1/prompt.md')).read_text()
            self.assertIn(str(kit), skill_prompt)
            for arm in ('bare', 'skill'):
                workspace = next(pathlib.Path(tmp, 'runs').glob(f'*/{arm}-1/workspace'))
                self.assertEqual((workspace / 'reference.jpg').read_bytes(), b'photo bytes')

    def test_skill_snapshot_drops_only_the_library_answers_to_the_bundled_prompts(self):
        ids = [path.stem.split('-', 1)[1] for path in sorted((ROOT / 'evals' / 'prompts').glob('*.md'))]
        self.assertEqual(len(ids), 10)
        self.assertEqual(run.ANSWER_PIECES, tuple('library/%s/' % piece for piece in ids))
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp, 'kit')
            files = ['SKILL.md', 'examples/moments/legacy.md', 'docs/a.md', 'library/index.json',
                     'library/market-day/piece.json', 'library/market-day/art/scene.py',
                     'library/market-day-extra/piece.json', 'library/new-starter/piece.json',
                     'library/new-starter/art/scene.py', 'library/README.md']
            for name in files:
                (repo / name).parent.mkdir(parents=True, exist_ok=True)
                (repo / name).write_text(name)
            subprocess.run(['git', 'init', '-q'], cwd=repo, check=True)
            subprocess.run(['git', 'add', '-A'], cwd=repo, check=True)
            with mock.patch.object(run, 'KIT', repo):
                snapshot = run.isolated_kit(pathlib.Path(tmp, 'runs'))
            kept = sorted(str(path.relative_to(snapshot)) for path in snapshot.rglob('*') if path.is_file())
            self.assertEqual(kept, ['SKILL.md', 'library/README.md', 'library/market-day-extra/piece.json',
                                    'library/new-starter/art/scene.py', 'library/new-starter/piece.json'])

    def test_real_skill_snapshot_has_no_moved_moment_and_keeps_the_rest_of_the_kit(self):
        if subprocess.run(['git', '-C', str(ROOT), 'rev-parse'], capture_output=True).returncode:
            self.skipTest('not a git checkout')
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = run.isolated_kit(pathlib.Path(tmp))
            for answer in run.ANSWER_PIECES:
                self.assertFalse((snapshot / answer).exists(), answer)
            self.assertFalse((snapshot / 'library' / 'index.json').exists())
            self.assertTrue((snapshot / 'tools' / 'library.py').is_file())
            self.assertTrue((snapshot / 'SKILL.md').is_file())

    def test_missing_reference_fails_before_any_agent_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompts = pathlib.Path(tmp, 'prompts')
            prompts.mkdir()
            (prompts / '99-rebuild.md').write_text('Rebuild this reference photo as pixel art.')
            refs = pathlib.Path(tmp, 'refs')
            refs.mkdir()
            result = subprocess.run([sys.executable, str(ROOT / 'evals' / 'run.py'), '--prompts', str(prompts),
                                     '--refs', str(refs), '--budget-usd', '1', '--out', tmp + '/runs', '--go'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('missing reference photo', result.stderr)
            self.assertFalse(pathlib.Path(tmp, 'runs').exists())

    def test_live_runs_require_held_out_prompts_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [sys.executable, str(ROOT / 'evals' / 'run.py'), '--tasks', '01', '--out', tmp + '/runs', '--go']
            missing = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('--prompts', missing.stderr)
            duplicate = pathlib.Path(tmp) / 'prompts'
            duplicate.mkdir()
            (duplicate / '01-copy.md').write_bytes(run.tasks('01')[0].read_bytes())
            rejected = subprocess.run(cmd + ['--prompts', str(duplicate), '--budget-usd', '1'],
                                      capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('not held out', rejected.stderr)
            self.assertFalse(pathlib.Path(tmp, 'runs').exists())


class ScoreTest(unittest.TestCase):
    def test_blind_grade_hides_arm_from_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            img = pathlib.Path(tmp, 'skill-1', 'workspace', 'out', 'a.png')
            img.parent.mkdir(parents=True)
            img.write_bytes(b'image bytes')
            prompt = pathlib.Path(tmp, 'skill-1', 'prompt.md')
            prompt.write_text('Fresh brief\n\n## Tools available\nSkill arm')
            (img.parent.parent / 'reference.jpg').write_bytes(b'reference bytes')
            def check(frame, brief, work):
                self.assertEqual(frame.name, 'frame.png')
                self.assertNotIn('skill-1', str(frame))
                self.assertEqual(frame.read_bytes(), img.read_bytes())
                self.assertEqual((work / 'reference.jpg').read_bytes(), b'reference bytes')
                self.assertNotIn('skill-1', str(work / 'reference.jpg'))
                self.assertEqual(brief, prompt)
                return 'A'
            with mock.patch.object(score, 'critique', side_effect=check):
                self.assertEqual(score.blind_grade(img, prompt), 'A')

    def test_scores_a_synthetic_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for arm, full in (('bare', False), ('skill', True)):
                d = root / '01-task' / ('%s-1' % arm)
                out = d / 'workspace' / 'out'
                out.mkdir(parents=True)
                (d / 'meta.json').write_text(json.dumps({'task': '01-task', 'arm': arm, 'run': 1, 'exit': 0,
                                                         'wall_s': 100.0, 'output_tokens': 1000}))
                im = Image.new('RGB', (64, 48), '#1b2233')
                im.paste((232, 216, 160), (21, 11, 40, 30))
                im.putpixel((33, 7), (200, 120, 90))
                im.resize((192, 144), Image.NEAREST).save(out / 'a.png')
                if full:
                    im.resize((192, 144), Image.NEAREST).save(out / 'b.png')
                    with wave.open(str(out / 'sample.wav'), 'w') as w:
                        w.setnchannels(2), w.setsampwidth(2), w.setframerate(48000)
                        t = np.arange(48000 * 5) / 48000.0
                        s = (0.5 * 32767 * np.sin(2 * np.pi * 220 * t)).astype('<i2')
                        w.writeframes(np.repeat(s, 2).tobytes())
            r = subprocess.run([sys.executable, str(ROOT / 'evals' / 'score.py'), str(root)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((root / 'scores.json').read_text())
            by = {x['arm']: x for x in data['runs']}
            self.assertEqual(by['bare']['delivered'], {'a': True, 'b': False, 'sample': False})
            self.assertEqual(by['skill']['sample']['seconds'], 5.0)
            self.assertFalse(by['skill']['sample']['clipped'])
            self.assertIn('defects', by['skill']['judge_a'])
            self.assertEqual((data['summary']['bare']['delivered_all'], data['summary']['skill']['delivered_all']), (0, 1))


if __name__ == '__main__':
    unittest.main()
