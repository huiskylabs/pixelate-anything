"""Local library add runs trusted programs twice; PR CI must never invoke it."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import contribute  # noqa: E402
import library  # noqa: E402


class Contribution(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.catalog = self.root / 'library'
        self.catalog.mkdir()
        self.source = self.root / 'harbour'
        shutil.copytree(REPO / 'library/starter-scene-still', self.source)
        manifest = json.loads((self.source / 'piece.json').read_text(encoding='utf-8'))
        manifest['id'] = 'harbour'
        manifest['request'] = 'a harbour at dusk'
        (self.source / 'piece.json').write_text(json.dumps(manifest), encoding='utf-8')
        self.addCleanup(lambda: os.environ.pop('PIXELATE_KNOBS', None))

    def command(self, *extra):
        return subprocess.run([sys.executable, str(REPO / 'pixelate'), 'library', '--library', str(self.catalog),
                               'add', str(self.source), *extra], capture_output=True, text=True, timeout=180)

    def run_line(self, suffix):
        path = self.source / 'piece.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['outputs'][0]['run'] += suffix
        path.write_text(json.dumps(manifest), encoding='utf-8')

    def test_refuses_untrusted_execution_and_leaves_catalog_unchanged(self):
        with mock.patch.object(contribute.deliver, 'run_render', side_effect=AssertionError('ran')):
            with self.assertRaisesRegex(contribute.ContributionError, '--trust-local-code'):
                contribute.add(self.source, self.catalog)
        self.assertEqual(list(self.catalog.iterdir()), [])

    def test_two_clean_renders_gate_generate_golden_and_update_index(self):
        p = self.command('--status', 'study', '--trust-local-code')
        self.assertEqual(p.returncode, 0, p.stdout[-1200:] + p.stderr[-1200:])
        result = json.loads(p.stdout)
        self.assertEqual((result['renders'], result['status'], result['gate_ok']), (2, 'study', True))
        self.assertIn('No independent art grade, user approval or redistribution', result['notice'])
        piece = self.catalog / 'harbour'
        manifest = library.validate(piece)
        golden = piece / manifest['outputs'][0]['golden']
        self.assertTrue(golden.is_file())
        self.assertFalse((piece / '.pixelate').exists())
        self.assertFalse((piece / 'dist').exists())
        self.assertFalse((piece / 'out/still.png').exists())
        self.assertIn('harbour', json.loads((self.catalog / 'index.json').read_text())['pieces'][0]['id'])
        self.assertEqual(library.index(self.catalog), (self.catalog / 'index.json').read_bytes())
        trail = json.loads((piece / 'history/add-report.json').read_text())
        self.assertEqual((trail['clean_renders'], trail['byte_equal'], trail['outputs'][0]['gate_ok']),
                         (2, True, True))
        self.assertEqual((trail['independent_review'], trail['approval'], trail['redistribution_rights']),
                         ('not established', 'not verified', 'not verified'))
        tested = library.test(self.catalog, ['harbour'], quick=True)
        self.assertTrue(tested['ok'], tested)
        self.assertEqual(tested['pieces'][0]['outputs'][0]['golden']['pixels'], 0)

    def test_gate_fail_blocks_even_a_study(self):
        self.run_line(" && python3 -c 'from PIL import Image; p="
                      "\"out/still.png\"; im=Image.open(p); Image.new(\"RGB\",im.size,\"white\").save(p)'")
        p = self.command('--status', 'study', '--trust-local-code')
        self.assertEqual(p.returncode, 1, p.stdout[-1000:] + p.stderr[-1000:])
        self.assertIn('gate FAIL', p.stderr)
        self.assertEqual(list(self.catalog.iterdir()), [])

    def test_nondeterministic_image_bytes_block_before_copy(self):
        self.run_line(" && python3 -c 'import os; open(\"out/still.png\",\"ab\").write(os.urandom(16))'")
        p = self.command('--status', 'study', '--trust-local-code')
        self.assertEqual(p.returncode, 1, p.stdout[-1000:] + p.stderr[-1000:])
        self.assertIn('outputs differ between two clean renders', p.stderr)
        self.assertEqual(list(self.catalog.iterdir()), [])

    def test_gate_cannot_promote_starter_to_accepted_without_evidence(self):
        p = self.command('--status', 'accepted', '--trust-local-code')
        self.assertEqual(p.returncode, 1)
        self.assertIn('accepted requires', p.stderr)
        self.assertEqual(list(self.catalog.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
