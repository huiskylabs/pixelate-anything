import pathlib
import sys
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import canvas  # noqa: E402
import judge  # noqa: E402
import recipes  # noqa: E402
import shapes  # noqa: E402

PAL = {'bg': '#1b2233', 'foam1': '#cfe9ee', 'foam2': '#ffffff'}
for name, hexes in (('rock', ['#2a1f2e', '#4a3240', '#6e4a4f', '#93695f', '#b98d76']),
                    ('pool', ['#13283a', '#1b3a52', '#24506a', '#2f6a84', '#3f879e', '#5aa6b8', '#86c6d2', '#c4e8ec']),
                    ('cloud', ['#454a6a', '#6a6f92', '#9aa0c0', '#d6d9ec'])):
    for i, h in enumerate(hexes):
        PAL['%s%d' % (name, i)] = h


def render(c):
    return np.array(c.image(PAL)).astype('uint8')


class RecipeTest(unittest.TestCase):
    def cliff(self, seed=3):
        c = canvas.Canvas(200, 140, 'bg')
        yy, xx = np.mgrid[0:140, 0:200]
        xe = shapes.ledges(0, 140, 120, seed=4, lo=80, hi=130)
        m = recipes.rock_face(c, (xx <= xe[:, None]) & (yy > 20), 'rock', steps=5, light='left', seed=seed)
        return c, m

    def test_rock_face_is_strata_not_masonry(self):
        c, m = self.cliff()
        rgb = render(c)
        self.assertGreater(m.sum(), 5000)
        self.assertNotIn('masonry', {d['kind'] for d in judge.detect_rgb(rgb)})
        used = {v for v in c.g.ravel() if v}
        self.assertTrue({'rock1', 'rock2', 'rock3'} <= used)

    def test_rock_face_is_deterministic(self):
        a, _ = self.cliff(seed=5)
        b, _ = self.cliff(seed=5)
        self.assertTrue((a.g == b.g).all())

    def test_pouring_fall_widens_and_sprays(self):
        c = canvas.Canvas(120, 140, 'bg')
        box = recipes.pouring_fall(c, 55, 20, 120, w=10, ramp='pool', foam=('foam1', 'foam2'), seed=2)
        g = c.g
        width = lambda y: sum(1 for v in g[y] if v and str(v).startswith('pool'))
        self.assertGreater(width(112), width(24) + 4)          # wider near the foot than at the lip
        self.assertTrue(any(v in ('foam1', 'foam2') for v in g[121]))
        self.assertLess(box[0], 55)

    def test_cloud_bank_masses_differ_and_bases_are_flat(self):
        c = canvas.Canvas(320, 100, 'bg')
        m = recipes.cloud_bank(c, 20, 300, 70, 'cloud', steps=4, seed=1)
        self.assertGreater(m.sum(), 2000)
        self.assertFalse(m[71:].any())                          # nothing below the flat underside
        rgb = render(c)
        self.assertNotIn('scallops', {d['kind'] for d in judge.detect_rgb(rgb)})
        used = {v for v in c.g.ravel() if v}
        self.assertTrue({'cloud0', 'cloud1', 'cloud3'} <= used)

    def test_perspective_repeat_shrinks_toward_the_vanishing_point(self):
        p = recipes.Perspective(horizon=60, vps=[(200, 60)])
        pts = p.repeat((20, 150), 6, gap=0.8)
        xs = [x for x, y, s in pts]
        scales = [s for x, y, s in pts]
        steps = np.diff(xs)
        self.assertTrue(all(np.diff(scales) < 0))
        self.assertTrue(all(steps[i] >= steps[i + 1] for i in range(len(steps) - 1)))
        c = canvas.Canvas(220, 160, 'bg')
        a, b = p.edge(c, (20, 150), 1.0, 'rock2')
        self.assertEqual(b, (200, 60))
        polys = p.box(c, 40, 80, 80, 140, 0.3, 'rock2', side='rock1', top='rock3')
        self.assertEqual(len(polys), 2)                         # the vp is right of and above the block
        with self.assertRaises(ValueError):
            recipes.Perspective(60, [])

    def test_crowd_vignettes_keep_groups_apart_with_varied_poses(self):
        groups = recipes.crowd_vignettes((0, 100, 320, 180), [('ring', 7), ('line', 5), ('cluster', 4)], seed=1)
        self.assertEqual([g['kind'] for g in groups], ['ring', 'line', 'cluster'])
        for g in groups:
            poses = [m['pose'] for m in g['members']]
            self.assertGreaterEqual(len(set(poses)), 3)
            self.assertTrue(all(a != b for a, b in zip(poses, poses[1:])))
        line = groups[1]
        self.assertEqual(len({m['face'] for m in line['members']}), 1)
        with self.assertRaises(ValueError):
            recipes.crowd_vignettes((0, 0, 30, 20), [('ring', 30), ('ring', 30)])


if __name__ == '__main__':
    unittest.main()
