"""Fixes from the first end-to-end run (prompt 16): a written-out prompt is never a small ask, 'covers'
and 'cycle' in prose are not a cover or a phase cycle, and 'dark' is not the darkest band."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import check  # noqa: E402
import route  # noqa: E402


class E2EFixesTest(unittest.TestCase):
    def test_a_long_prompt_naming_palettes_is_a_full_scene(self):
        req = ('An animated loop of a temple garden in autumn. ' * 8 +
               'Use eight background palettes of 15 colours plus transparency.')
        self.assertIsNone(route.small_kind(req))
        self.assertEqual(route.small_kind('a palette for a desert at dusk'), 'palette')

    def test_prose_words_are_not_signals(self):
        gaps = {g['topic']: g for g in route.gaps('moss covers one side of the steps; every cycle divides the loop')}
        self.assertNotIn('cover', ' '.join(gaps.get('purpose', {}).get('stated', '') or ''))
        self.assertFalse(gaps.get('phases', {}).get('stated'))

    def test_dark_is_above_darkest_with_five_bands(self):
        self.assertEqual([check.band_index(t, 5) for t in ('darkest', 'dark', 'mid', 'light', 'brightest')],
                         [0, 1, 2, 3, 4])
        self.assertEqual(check.band_index('dark', 3), 0)


if __name__ == '__main__':
    unittest.main()
