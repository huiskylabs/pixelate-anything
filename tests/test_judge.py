import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import canvas  # noqa: E402
import judge  # noqa: E402
import shapes  # noqa: E402

PAL = {'bg': '#1b2233', 'brick0': '#2a1f2e', 'brick1': '#7a4a3f', 'cloud1': '#6a6f92', 'rim': '#c9cce0',
       'wall': '#8a7a6a', 'roof': '#3a2a2a', 'hi': '#e8d8a0'}


def render(c):
    return np.array(c.image(PAL)).astype('uint8')


def kinds(rgb):
    return {d['kind'] for d in judge.detect_rgb(rgb)}


def bricks(w=160, h=96):
    b = canvas.Canvas(w, h, 'brick1')
    for y in range(0, h, 6):
        b.hline(0, w - 1, y, 'brick0')
        for x in range(0 if (y // 6) % 2 == 0 else 6, w, 12):
            b.vline(x, y, y + 5, 'brick0')
    return b


class DetectorTest(unittest.TestCase):
    def test_brick_grid_reads_as_masonry(self):
        self.assertIn('masonry', kinds(render(bricks())))

    def test_flat_field_has_no_defects(self):
        c = canvas.Canvas(120, 80, 'bg')
        c.rect(10, 50, 110, 79, 'wall')
        c.rect(40, 10, 70, 30, 'hi')
        self.assertEqual(kinds(render(c)), set())

    def test_even_cloud_scallops_are_found_and_varied_lobes_pass(self):
        found = []
        for seed in range(4):
            for vary in (0.0, 1.0):
                c = canvas.Canvas(320, 90, 'bg')
                c.fill(shapes.cloud_mask((90, 320), 130, 50, 80, 18, r=(7, 7), spacing=9, belly=0, seed=seed,
                                         vary=vary), 'cloud1')
                found.append((vary, 'scallops' in kinds(render(c))))
        self.assertTrue(any(hit for vary, hit in found if vary == 0.0))
        self.assertFalse(any(hit for vary, hit in found if vary == 1.0))

    def test_outline_loop_is_found_and_filled_mass_passes(self):
        loop = canvas.Canvas(120, 80, 'bg')
        m = np.zeros((80, 120), bool)
        yy, xx = np.mgrid[0:80, 0:120]
        m[((xx - 60) / 40.0) ** 2 + ((yy - 40) / 20.0) ** 2 <= 1] = True
        ring = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
        loop.fill(ring, 'rim')
        self.assertIn('outline_loop', kinds(render(loop)))
        filled = canvas.Canvas(120, 80, 'bg')
        filled.fill(m, 'cloud1')
        filled.fill(ring & (yy < 40), 'rim')
        self.assertNotIn('outline_loop', kinds(render(filled)))

    def test_stamped_units_repeat(self):
        c = canvas.Canvas(200, 60, 'bg')
        for i in range(7):
            c.rect(10 + i * 26, 20, 10 + i * 26 + 9, 32, 'wall')
        self.assertIn('repeat_units', kinds(render(c)))
        v = canvas.Canvas(200, 60, 'bg')
        x = 6
        for i, (w, h) in enumerate([(9, 12), (14, 8), (6, 15), (11, 10), (7, 6), (16, 13), (10, 9)]):
            v.rect(x, 40 - h, x + w, 40, 'wall')
            x += w + 4 + (i * 7) % 11
        self.assertNotIn('repeat_units', kinds(render(v)))

    def test_murky_frame(self):
        c = canvas.Canvas(100, 60, 'brick0')
        c.rect(0, 30, 99, 59, 'roof')
        self.assertIn('murky', kinds(render(c)))

    def test_scale_detection_and_screen_light(self):
        rgb = render(bricks(80, 48))
        big = np.repeat(np.repeat(rgb, 4, 0), 4, 1)
        self.assertEqual(judge.native_scale(big), 4)
        soft = big.astype(int) + (np.indices(big.shape[:2]).sum(0) % 4)[..., None]   # light smooth inside cells
        self.assertEqual(judge.native_scale(np.clip(soft, 0, 255).astype('uint8')), 4)

    def test_defects_carry_box_why_and_fix(self):
        d = judge.detect_rgb(render(bricks()))[0]
        self.assertEqual(set(d) >= {'kind', 'box', 'severity', 'why', 'fix', 'id'}, True)
        x0, y0, x1, y1 = d['box']
        self.assertTrue(0 <= x0 <= x1 and 0 <= y0 <= y1)


class CliTest(unittest.TestCase):
    def test_cli_overlay_json_and_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            frame = tmp / 'wall@3x.png'
            rgb = render(bricks())
            Image.fromarray(np.repeat(np.repeat(rgb, 3, 0), 3, 1)).save(frame)
            r = subprocess.run([sys.executable, str(ROOT / 'pixelate'), 'judge', str(frame), '--json',
                                '--overlay', str(tmp / 'ov.png'), '--log', str(tmp / 'log.jsonl'), '--note', 'draft'],
                               capture_output=True, text=True, cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(out['scale'], 3)
            self.assertIn('masonry', {d['kind'] for d in out['defects']})
            self.assertTrue((tmp / 'ov.png').exists())
            rec = json.loads((tmp / 'log.jsonl').read_text().splitlines()[0])
            self.assertEqual((rec['type'], rec['note'], rec['scale']), ('judge', 'draft', 3))
            self.assertEqual(len(rec['sha256']), 64)

    def test_ignore_rejects_unknown_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame = pathlib.Path(tmp) / 'f.png'
            Image.fromarray(render(bricks())).save(frame)
            r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'judge.py'), str(frame), '--ignore', 'nope'],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'judge.py'), str(frame), '--json', '--ignore',
                                'masonry,repeat_units,scallops'], capture_output=True, text=True)
            self.assertNotIn('masonry', {d['kind'] for d in json.loads(r.stdout)['defects']})


if __name__ == '__main__':
    unittest.main()
