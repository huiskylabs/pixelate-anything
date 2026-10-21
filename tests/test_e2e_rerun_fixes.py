"""What the second end-to-end run (prompt 16, SNES temple garden) tripped on: a measured Hero box or
Sprites line flipped a directed brief to precise mode, the lint missed common rate wording, the skeleton
ignored the request's own canvas, scale and loop length and planned a light layer for an era, a small
hero fell under the 40 px rule, keys that read by hue failed, and render era-checked the 2x frame. Checking
the next four prompts found three routing slips: a photo inside the scene, a scene's walk cycles and a
console's tile grid switched the mode or the style."""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import craftcheck  # noqa: E402
import library  # noqa: E402
import render  # noqa: E402
import route  # noqa: E402

SNES = ('A 3/4 top-down autumn temple garden that obeys the SNES limits, a monk sweeping leaves. The frame '
        'count is 12 x seconds (60 frames at 5 s). Technical: native 256x224, scaled to 512x432 (2x) with '
        'nearest neighbour; on its own 1024x896 (4x).')


class LintTest(unittest.TestCase):
    def test_rate_wording(self):
        for line in ('leaves on 3-frame tumbles', 'frames 24-35: the gust', 'a ripple with period 60'):
            self.assertRegex(line, route.RATE, line)

    def test_measured_hero_box_and_sprites_stay_directed(self):
        self.assertFalse(route._precise('- Hero: 120,150,135,173 (native px); peak value: the robe\n'
                                        '- Sprites: monk [120,150,135,173], cat [200,40,207,47]\n'))
        self.assertTrue(route._precise('- Key: bell [40,20,52,34]; L .30 on wall .15\n'))
        text = route.brief('hd-overworld', SNES, era='snes')
        text = text.replace('- Hero: TODO', '- Hero: 120,150,135,173 (native px); peak value: the robe; peak '
                            'chroma: the robe. TODO', 1)
        text = text.replace('- Story:', '- Sprites: monk [120,150,135,173]\n- Story:', 1)
        self.assertFalse(route._precise(text))
        probs = route.lint(text)
        self.assertFalse([p for p in probs if any(w in p for w in ('Key', 'Value plan', 'Masses', 'Planes', 'Calm'))],
                         probs)


class SkeletonTest(unittest.TestCase):
    def test_the_request_sets_canvas_scale_and_loop(self):
        self.assertEqual(route.asked_delivery('native 384x216, delivered at 768x432 (2x nearest)'), ((768, 432), 2))
        self.assertEqual(route.asked_delivery('native 160x144, scaled to 480x432 (3x) with nearest'), ((480, 432), 3))
        self.assertEqual(route.asked_delivery('native 320x200, scaled 2x with nearest neighbour'), ((640, 400), 2))
        self.assertEqual(route.asked_delivery('a 1920x1080 still'), ((1920, 1080), None))
        self.assertEqual(route.asked_delivery('x', (800, 600), 2), ((800, 600), 2))
        self.assertEqual(route.frames_of(SNES), 60)
        self.assertIsNone(route.frames_of('sweeping on 4 frames at 12 fps'))

    def test_an_era_brief_keeps_the_era(self):
        size, scale = route.asked_delivery(SNES)
        text = route.brief('hd-overworld', SNES, era='snes', size=size, scale=scale)
        self.assertIn('Delivered at 512x448: native 256x224, 2x nearest.', text)
        self.assertIn('- Loop: 60 frames at 12 fps', text)
        self.assertIn('## 8. Motion table (60 frames at 12 fps)', text)
        self.assertIn('- Light: no light layer', text)
        self.assertIn('--era snes --scale 2', text)
        self.assertIn('Gate lines, measured after drawing', text)
        body = text.split('## 2. Style and light regime')[1]
        for word in ('post.', 'translucent', 'APNG', 'glow'):
            self.assertNotIn(word, body.split('\n', 2)[2], word)    # after the style's own description line
        self.assertIn('draw a hero figure at least 20 native rows tall', text)

    def test_the_still_critique_comes_first_on_the_style_loop(self):
        text = route.brief('lofi', 'a temple garden in autumn')
        line = next(x for x in text.splitlines() if x.startswith('- Art director:'))
        self.assertLess(line.index('FRAME.png'), line.index('BLOCKIN.png'))
        self.assertIn('SKILL.md step 7', line)


class RoutingTest(unittest.TestCase):
    def test_words_inside_a_scene_do_not_switch_the_mode(self):
        self.assertEqual(route.route('Make an animated pixel-art loop of a hillside town in 2:1 isometric: '
                                     'a couple taking a photo on the footbridge.')['mode'], 'scene')
        self.assertEqual(route.route('Make an animated pixel-art loop of a night procession; walk cycles of 6 '
                                     'frames at 12 fps.')['mode'], 'scene')
        self.assertEqual(route.route('Rebuild this photo of a street in one-point perspective.')['mode'], 'rebuild')
        self.assertEqual(route.route('a walk cycle for my knight')['mode'], 'assets')

    def test_a_tile_grid_is_no_strategy_board(self):
        r = route.route('A Game Boy cliff post office in a storm, side view. Background drawn on an 8x8 tile '
                        'grid; pixels on a 160x144 grid.')
        self.assertEqual(r['mode'], 'era')
        self.assertNotEqual(r['picks'][0]['style'], 'tactics')


class ChecksTest(unittest.TestCase):
    def test_a_key_reads_by_colour(self):
        img = Image.new('RGB', (64, 48), (40, 140, 130))
        ImageDraw.Draw(img).rectangle([24, 16, 39, 31], fill=(200, 110, 60))
        r = craftcheck.presence(img, (24, 16, 39, 31))
        self.assertLess(abs(r['dL']), craftcheck.PRESENCE_DL)
        self.assertEqual((r['ok'], r['why']), (True, 'colour'))
        flat = Image.new('RGB', (64, 48), (40, 140, 130))
        ImageDraw.Draw(flat).rectangle([24, 16, 39, 31], fill=(44, 146, 128))
        self.assertFalse(craftcheck.presence(flat, (24, 16, 39, 31))['ok'])

    def test_render_era_checks_the_native_screen(self):
        with tempfile.TemporaryDirectory() as d:
            Image.new('RGB', (512, 448), (40, 140, 130)).save(Path(d) / 'still.png')
            rec = render.technical_gate(Path(d), {'name': 'still', 'frame': 'still.png', 'scale': 2,
                                                  'era': 'snes', 'style': 'hd-overworld'})
            self.assertTrue(rec['era']['ok'])
            self.assertNotIn('size 512x448', rec['era']['report'])
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ['still.png'])

    def test_find_does_not_push_authoring(self):
        result = library.find(REPO / 'library', 'a 16-bit SNES-style autumn temple garden', 'era')
        self.assertIn('adapt the nearest starter', result['fallback'].get('reason', ''))


if __name__ == '__main__':
    unittest.main()
