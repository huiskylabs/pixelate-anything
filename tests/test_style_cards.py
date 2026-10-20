"""Every style preset has a written card (references/styles/NAME.md) that `pixelate style NAME` prints, and a
brief that studies a library piece must say how it differs on four of six axes (`route --lint`)."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import route  # noqa: E402
import styles  # noqa: E402

HEADINGS = ('## Essence', '## What it is not', '## Pitfalls', '## Variation space')


class StyleCardTest(unittest.TestCase):
    def test_every_preset_has_a_written_card(self):
        for name in styles.STYLES:
            path = REPO / 'references' / 'styles' / (name + '.md')
            self.assertTrue(path.is_file(), name)
            text = path.read_text(encoding='utf-8')
            for heading in HEADINGS:
                self.assertIn(heading, text, f'{name}: {heading}')
            card = styles.card(name)
            for heading in HEADINGS:
                self.assertIn(heading, card, f'{name} card: {heading}')
            self.assertLess(card.index('## Essence'), card.index('## Light regime'), name)

    def test_no_card_without_a_preset(self):
        for path in (REPO / 'references' / 'styles').glob('*.md'):
            self.assertIn(path.stem, styles.STYLES, path.name)


class NotTheReferenceTest(unittest.TestCase):
    def test_a_brief_without_a_studied_piece_needs_no_line(self):
        self.assertEqual(route._not_the_reference('A lighthouse at night, drawn from scratch.'), [])

    def test_a_studied_piece_needs_a_differs_line(self):
        probs = route._not_the_reference('- Studied `library/lantern-isle` for the snow.')
        self.assertEqual(len(probs), 1)
        self.assertIn('no "Differs from" line', probs[0])

    def test_three_axes_are_not_enough(self):
        text = ('- Studied `lantern-isle` for the snow.\n'
                '- Differs from lantern-isle: subject (a lighthouse), camera (low), palette (teal)\n')
        probs = route._not_the_reference(text)
        self.assertEqual(len(probs), 1)
        self.assertIn('names 3 axes', probs[0])

    def test_four_axes_pass(self):
        text = ('- Studied `library/lantern-isle` for the snow.\n'
                '- Differs from lantern-isle: subject (a lighthouse), camera (low side), palette (teal night), '
                'motion (beam sweep)\n')
        self.assertEqual(route._not_the_reference(text), [])

    def test_starters_are_exempt(self):
        self.assertEqual(route._not_the_reference('Begin from `starter-scene-still`.'), [])


if __name__ == '__main__':
    unittest.main()
