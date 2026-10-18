import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check  # noqa: E402
import render  # noqa: E402

ART = '''import sys
from PIL import Image
im = Image.new('RGB', (64, 48), '#1b2233')
im.paste((122, 74, 63), (0, 30, 64, 48))
im.paste((232, 216, 160), (24, 8, 40, 20))
im.resize((256, 192), Image.NEAREST).save('out/%s.png' % sys.argv[1])
'''

# Stands in for `pixelate`: `check` prints a finished failing gate, then behaves as GATE_END says.
FAKE_PIXELATE = '''import os, sys
if sys.argv[1] == 'era':
    print('NES-style 8-bit: 3 colours; size 64x48, the NES-style 8-bit screen is 256x224')
    sys.exit(0)
print('FAIL era nes                    3 colours    size 64x48')
print('FAIL: 1 of 1 checks')
end = os.environ['GATE_END']
if end == 'crash':
    raise RuntimeError('crashed after the summary')
if end == 'more':
    print('trailing output')
sys.exit(int(end) if end.isdigit() else 1)
'''


class TechnicalGateTest(unittest.TestCase):
    def gate(self, end):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'pixelate'
            fake.write_text(FAKE_PIXELATE)
            with mock.patch.object(render, 'PIXELATE', [sys.executable, str(fake)]), \
                    mock.patch.dict(os.environ, GATE_END=end):
                return render.technical_gate(pathlib.Path(tmp), {'name': 'a', 'frame': 'a.png', 'era': 'nes'})

    def test_a_finished_failing_gate_is_a_verdict(self):
        rec = self.gate('1')
        self.assertFalse(rec['gate']['ok'])
        self.assertNotIn('error', rec['gate'])
        self.assertIn('FAIL era nes                    3 colours    size 64x48', rec['gate']['fail'])
        # The era command exits 0 with violations: era.ok is its exit status, never legality.
        self.assertTrue(rec['era']['ok'])
        self.assertIn('256x224', rec['era']['report'])

    def test_a_crash_or_odd_exit_after_the_summary_is_an_error(self):
        for end, shown in (('crash', 'RuntimeError: crashed after the summary'), ('more', 'trailing output'),
                           ('2', 'FAIL: 1 of 1 checks')):
            with self.subTest(end=end):
                rec = self.gate(end)
                self.assertFalse(rec['gate']['ok'])
                self.assertIn(shown, rec['gate']['error'])


class BriefForImageTest(unittest.TestCase):
    def test_image_section_comes_first_and_inherits_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / 'brief.md'
            p.write_text('Request: x\n## 4. The scene\n- Hero: tower\n## Image B\n- Hero: harbour\n'
                         '- Gate override: palette, two ramps on purpose\n## 9. Technical\n'
                         '- Gate override: focal, wide shot\n')
            out = check.brief_for_image(str(p), 'b')
            self.assertNotEqual(out, str(p))
            text = pathlib.Path(out).read_text()
            head = text.split('\n\n')[0]
            self.assertIn('- Hero: harbour', head)
            self.assertIn('palette, two ramps', head)
            self.assertIn('focal, wide shot', head)
            self.assertIn('Request: x', text)
            self.assertEqual(check.brief_for_image(str(p), 'c'), str(p))


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = pathlib.Path(self.tmp.name)
        (self.d / 'out').mkdir()
        (self.d / 'art.py').write_text(ART)

    def spec(self, images):
        (self.d / 'render.json').write_text(json.dumps({'images': images}))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'pixelate'), 'render', str(self.d), *args],
                              capture_output=True, text=True)

    def test_runs_gates_judges_and_reports(self):
        self.spec([{'name': 'a', 'run': '%s art.py a' % sys.executable, 'frame': 'out/a.png', 'style': 'arcade',
                    'scale': 4},
                   {'name': 'b', 'run': '%s art.py b' % sys.executable, 'frame': 'out/b.png', 'style': 'arcade',
                    'scale': 4}])
        r = self.cli('--json')
        recs = json.loads(r.stdout)
        self.assertEqual([x['name'] for x in recs], ['a', 'b'])
        for rec in recs:
            self.assertNotIn('kind', rec)
            self.assertTrue(rec['run']['ok'])
            self.assertIn('gate', rec)
            self.assertIn('defects', rec['judge'])
        self.assertEqual(r.returncode, 0 if all(render.ok(x) for x in recs) else 1)
        self.assertTrue((self.d / 'render-report.json').exists())
        runs = [json.loads(l) for l in (self.d / '.pixelate' / 'runs.jsonl').read_text().splitlines()]
        self.assertEqual(runs[-1]['type'], 'render')
        self.assertNotIn('files', runs[-1])
        self.assertEqual([i['name'] for i in runs[-1]['images']], ['a', 'b'])
        self.assertEqual(len(runs[-1]['images'][0]['sha256']), 64)
        one = json.loads(self.cli('--image', 'b', '--no-run', '--json').stdout)
        self.assertEqual([x['name'] for x in one], ['b'])
        self.assertNotIn('run', one[0])

    def test_run_log_hashes_the_bytes_each_image_was_checked_with(self):
        (self.d / 'art.py').write_text(ART.replace("(232, 216, 160)", "(232, 216, 160) if sys.argv[1] == 'a' else (90, 200, 90)"))
        self.spec([{'name': 'a', 'run': '%s art.py a' % sys.executable, 'frame': 'out/a.png', 'style': 'arcade', 'scale': 4},
                   {'name': 'b', 'run': '%s art.py b && %s -c "import shutil; shutil.copy(\'out/b.png\', \'out/a.png\')"'
                    % (sys.executable, sys.executable), 'frame': 'out/b.png', 'style': 'arcade', 'scale': 4}])
        self.cli('--json')
        run = json.loads((self.d / '.pixelate' / 'runs.jsonl').read_text().splitlines()[-1])
        a, b = run['images']
        self.assertNotEqual(a['sha256'], b['sha256'])              # a was hashed before b overwrote it
        self.assertEqual(hashlib.sha256((self.d / 'out/a.png').read_bytes()).hexdigest(), b['sha256'])

    def test_no_log_turns_off_every_log(self):
        self.spec([{'name': 'a', 'run': '%s art.py a' % sys.executable, 'frame': 'out/a.png', 'style': 'arcade', 'scale': 4}])
        r = subprocess.run([sys.executable, str(ROOT / 'pixelate'), 'render', str(self.d)], capture_output=True,
                           text=True, env=dict(os.environ, PIXELATE_NO_LOG='1'))
        self.assertTrue((self.d / 'render-report.json').exists(), r.stderr)
        self.assertFalse((self.d / '.pixelate').exists())

    def test_failed_command_fails_the_render(self):
        self.spec([{'name': 'a', 'run': '%s -c "raise SystemExit(\'boom\')"' % sys.executable, 'frame': 'out/a.png',
                    'style': 'arcade'}])
        r = self.cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn('RUN FAILED', r.stdout)

    def test_spec_needs_a_gate_style(self):
        self.spec([{'name': 'a', 'frame': 'out/a.png'}])
        r = self.cli()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('style', r.stderr)

    def test_legacy_era_record_keeps_ok(self):
        self.spec([{'name': 'a', 'run': '%s art.py a' % sys.executable, 'frame': 'out/a.png', 'era': 'nes', 'scale': 4}])
        r = self.cli('--json')
        rec = json.loads(r.stdout)[0]
        self.assertEqual(set(rec['era']), {'ok', 'report'})
        self.assertTrue(rec['era']['ok'])
        self.assertFalse(rec['gate']['ok'])
        self.assertNotIn('error', rec['gate'])
        self.assertIn('era ok', render.line(rec))
        self.assertEqual(r.returncode, 1)

    def test_gate_args_pass_brief_and_image(self):
        args = render.gate_args({'name': 'b', 'frame': 'f.png', 'style': 'arcade', 'scale': 3, 'brief': 'brief.md'})
        self.assertEqual(args[-4:], ['--brief', 'brief.md', '--image', 'b'])
        self.assertIn('--style', args)


if __name__ == '__main__':
    unittest.main()
