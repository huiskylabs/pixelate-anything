"""The three styles set from a medium's own rules (ink-wash, 1-bit, cutaway) and the CGA era."""
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import era  # noqa: E402
import route  # noqa: E402
import stats  # noqa: E402
import styles  # noqa: E402


def frame(colours, size=(64, 36)):
    """a frame striped in the given hexes"""
    a = np.zeros((size[1], size[0], 3), np.uint8)
    for i in range(size[0]):
        h = colours[i % len(colours)].lstrip('#')
        a[:, i] = [int(h[j:j + 2], 16) for j in (0, 2, 4)]
    return Image.fromarray(a)


class MediaStylesTest(unittest.TestCase):
    def test_routing_picks_each_style(self):
        for req, name in (('水墨 river boatman in mist', 'ink-wash'), ('1-bit cable car in a blizzard', '1-bit'),
                          ('a cutaway of a seabed station', 'cutaway')):
            self.assertEqual(route.route(req)['picks'][0]['style'], name, req)

    def test_cutaway_is_military(self):
        self.assertEqual(route.ROUTE['cutaway']['projection'], 'military')

    def test_one_bit_allows_two_colours_only(self):
        rules = styles.get('1-bit')['budgets']
        self.assertEqual(stats.budget(frame(['#000000', '#f0ecdc']), rules), [])
        self.assertTrue(stats.budget(frame(['#000000', '#f0ecdc', '#808080']), rules))

    def test_ink_wash_needs_bare_paper(self):
        rules = styles.get('ink-wash')['budgets']
        self.assertEqual(stats.budget(frame(['#efe6d2', '#efe6d2', '#8a8478', '#1c1a18']), rules), [])
        self.assertTrue(stats.budget(frame(['#8a8478', '#1c1a18']), rules))


class CgaEraTest(unittest.TestCase):
    def test_named_in_a_request(self):
        self.assertEqual(route.era_of('an alchemy room like an early PC game, CGA colours'), 'cga')

    def test_four_colours_are_legal(self):
        img = frame(['#000000', '#55ffff', '#ff55ff', '#ffffff'], era.ERAS['cga']['size'])
        self.assertEqual(era.check(img, 'cga')[0], [])

    def test_a_fifth_colour_is_not(self):
        img = frame(['#000000', '#55ffff', '#ff55ff', '#ffffff', '#aa5500'], era.ERAS['cga']['size'])
        self.assertTrue(era.check(img, 'cga')[0])


if __name__ == '__main__':
    unittest.main()
