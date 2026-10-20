"""A brief directs by default (story, hero, what must read) and leaves composition, sizes and colour values
to the artist; --precise plans the scene to the pixel for the gate to measure."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import route  # noqa: E402


class DirectorBriefTest(unittest.TestCase):
    def test_default_skeleton_has_no_boxes(self):
        text = route.brief('lofi', 'a temple garden in autumn')
        self.assertIn('- Must read', text)
        self.assertIn('- Leave to the artist', text)
        self.assertNotIn('[x0,y0,x1,y1]', text)
        self.assertFalse(route._precise(text))

    def test_precise_skeleton_keeps_the_boxes(self):
        text = route.brief('lofi', 'a temple garden in autumn', precise=True)
        self.assertIn('- Key: TODO', text)
        self.assertIn('[x0,y0,x1,y1]', text)

    def test_a_directed_scene_needs_a_hero_and_three_things_to_read(self):
        self.assertEqual(route._director_scene('- Hero: the monk\n- Must read: the bell; the koi; the cat\n'), [])
        probs = route._director_scene('- Layout: a pond in the middle\n- Must read: the bell\n')
        self.assertEqual(len(probs), 2)

    def test_a_directed_brief_is_not_asked_for_boxes(self):
        text = route.brief('lofi', 'a temple garden in autumn')
        probs = route.lint(text)
        self.assertFalse([p for p in probs if 'Key' in p or 'density' in p or 'box' in p], probs)


if __name__ == '__main__':
    unittest.main()
