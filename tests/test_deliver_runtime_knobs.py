"""Exercise delivery of real engine and pack variants across the two phase-2 units."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class DeliveryRuntimeKnobs(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)

    def command(self, *args):
        env = os.environ.copy()
        for key in ('PIXELATE_KIT', 'PIXELATE_KNOBS', 'PIXELATE_NO_LOG'):
            env.pop(key, None)
        process = subprocess.run([sys.executable, str(REPO / 'pixelate'), 'deliver', *map(str, args), '--json'],
                                 capture_output=True, text=True, env=env, timeout=360)
        self.assertEqual(process.returncode, 0, process.stdout[-1500:] + process.stderr[-1500:])
        return json.loads(process.stdout)

    def exercise(self, piece, key, value, output, source, expected_outputs):
        folder = self.work / piece
        shutil.copytree(REPO / 'library' / piece, folder)
        original_source = (folder / source).read_bytes()
        default = self.command(folder)
        self.assertTrue(default['ok'])
        self.assertEqual(default['facts']['knobs']['basis'], 'declared defaults')
        before = hashlib.sha256((folder / output).read_bytes()).hexdigest()

        variant = self.command(folder, '--set', f'{key}={value}')
        self.assertTrue(variant['ok'])
        self.assertEqual(variant['facts']['knobs']['basis'], 'set')
        self.assertEqual(variant['facts']['knobs']['set'], {key: value})
        self.assertEqual(variant['facts']['knobs']['merged'], {key: value})
        self.assertEqual(len(variant['facts']['outputs']), expected_outputs)
        self.assertNotEqual(before, hashlib.sha256((folder / output).read_bytes()).hexdigest())
        self.assertEqual((folder / source).read_bytes(), original_source)
        self.assertTrue(self.command(folder, '--verify')['ok'])

    @unittest.skipUnless(shutil.which('node'), 'engine scenes require Node')
    def test_engine_horizon_variant_is_delivered_and_verifies(self):
        self.exercise('starter-scene-loop', 'horizon', 80, 'out/t0000.00.png', 'scene.js', 2)

    def test_pack_scale_variant_is_delivered_and_verifies(self):
        self.exercise('starter-assets', 'scale', 4, 'out/contact.png', 'pack.json', 3)

    def test_remix_distance_and_its_baseline_are_bound_to_delivery(self):
        root = self.work / 'harbour-remix'
        process = subprocess.run([sys.executable, str(REPO / 'pixelate'), 'remix', 'starter-scene-still', str(root),
                                  '--request', 'a harbour at dusk', '--json'], capture_output=True, text=True,
                                 timeout=360)
        self.assertEqual(process.returncode, 0, process.stdout[-1200:] + process.stderr[-1200:])
        delivered = self.command(root)
        self.assertTrue(delivered['ok'])
        (image,) = delivered['facts']['outputs']
        distance = image['distance']
        self.assertEqual(distance['base']['id'], 'starter-scene-still')
        self.assertEqual(distance['pixels']['differ'], 0)
        self.assertTrue(distance['under_remixed'])
        self.assertIn('under-remixed', distance['warning'])
        self.assertIn('WARNING under-remixed', (root / 'dist/delivery/DELIVERY.md').read_text())
        self.assertTrue(self.command(root, '--verify')['ok'])

        baseline = root / '.pixelate/remix-baseline.json'
        baseline.write_bytes(baseline.read_bytes() + b' ')
        verified = subprocess.run([sys.executable, str(REPO / 'pixelate'), 'deliver', str(root), '--verify', '--json'],
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(verified.returncode, 1)
        report = json.loads(verified.stdout)
        self.assertFalse(report['ok'])
        self.assertTrue(any(c['check'] == 'remix baseline' and not c['ok'] for c in report['checks']))


if __name__ == '__main__':
    unittest.main()
