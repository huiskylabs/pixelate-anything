"""What four end-to-end runs at once (prompts 01 contre-jour, 07 sticker-iso, 12 Game Boy, 18 1-bit)
tripped on before drawing: the brief skeleton took the card's music, palette and figure sizes over the
request's own, told a crowd request to add nobody, read "no interior detail" and "inside, two
silhouettes" as a room, and its lint missed capitalised words; the Game Boy check took only the DMG's
green and `era --tiles` printed no count; find read a photo inside the scene as a rebuild; and the docs
disagreed on the brief review, the starter command and the number of styles."""
import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import era  # noqa: E402
import library  # noqa: E402
import route  # noqa: E402
import styles  # noqa: E402

FOREST = ('Make an animated pixel-art loop of a night procession in an old misty forest. The trees are flat dark '
          'silhouettes with no interior detail beyond a few rim pixels. Scene: a side view.\n\n'
          '- Music at 5 s: 96 BPM in 4/4, exactly 2 bars.\n\n'
          'Palette: deep teal-black, fog blue-green, moon-white for the pillar, lantern amber.\n\n'
          'Music: a breathy bamboo flute over low hand drums, D minor pentatonic, 96 BPM.\n\n'
          'Technical: native 384x216, delivered at 768x432 (2x nearest).')


class SkeletonTest(unittest.TestCase):
    def brief(self, style, request, **kw):          # as `pixelate route REQUEST --brief STYLE` builds it
        size, scale = route.asked_delivery(request)
        _, h, _, DW, DH = route.delivery(style, size, scale)
        return route.brief(style, request, choices=route.gaps(request, None, (DW, DH), h), size=size, scale=scale,
                           **kw)

    def line(self, text, start):
        return next(x for x in text.splitlines() if x.startswith(start))

    def test_the_request_names_its_own_music_and_palette(self):
        self.assertEqual(route.asked_line(FOREST, 'Music'), 'a breathy bamboo flute over low hand drums, D minor '
                                                             'pentatonic, 96 BPM')
        self.assertIsNone(route.asked_line('- Music at 5 s: 96 BPM', 'Music'))
        self.assertEqual(route.asked_line('音乐：慢，竹笛', 'Music', '音乐'), '慢，竹笛')
        text = self.brief('contre-jour', FOREST)
        self.assertIn("Music: the request's own: a breathy bamboo flute", self.line(text, '- Music:'))
        self.assertIn("Palette: the request's own: deep teal-black", self.line(text, '- Ramps:'))
        card = route.brief('contre-jour', 'a night procession in a misty forest')
        self.assertNotIn("the request's own", self.line(card, '- Music:'))

    def test_an_era_piece_keeps_its_chip_under_the_request_music(self):
        text = route.music_line('A Game Boy harbour.\nMusic: a slow sea shanty in A minor.', 'lofi', 'gameboy')
        self.assertTrue(text.startswith('chiptune on the Game Boy-style chip only'))
        self.assertIn("the request's own: a slow sea shanty in A minor", text)

    def test_one_figure_size_in_the_brief(self):
        text = self.brief('contre-jour', FOREST)
        rule = next(x for x in text.splitlines() if x.startswith('- Figures are slim'))
        self.assertIn('12-18 px', rule)
        self.assertNotIn('20-30 px', text)

    def test_a_crowd_is_not_nobody(self):
        crowd = 'A hillside town at noon in 2:1 isometric. The crowd is the subject: over 60 people, each its own pose.'
        fig = next(g for g in route.gaps(crowd) if g['topic'] == 'figures')
        self.assertIn('the crowd the request asks for', fig['default'])
        fig = next(g for g in route.gaps('a boy and his dog on a quiet pier') if g['topic'] == 'figures')
        self.assertIn('nobody added', fig['default'])

    def test_a_directed_brief_asks_for_the_hero_box_after_drawing(self):
        text = self.brief('contre-jour', FOREST)
        self.assertIn('Gate lines, measured after drawing', text)
        self.assertNotIn('Sprites', self.line(text, '- Gate lines'))

    def test_lint_reads_capitalised_words(self):
        text = self.brief('contre-jour', FOREST)
        sec = text.split('## 2. Style and light regime')[1].split('\n## ')[0]
        upper = text.replace(sec, sec.replace('screen', 'SCREEN').replace('none', 'NONE'))
        upper = re.sub(r'(?i)budget', 'BUDGET', upper)
        probs = route.lint(upper)
        self.assertFalse([p for p in probs if 'light layer' in p or 'value budget' in p], probs)


class IndoorsTest(unittest.TestCase):
    def test_a_silhouette_without_interior_detail_stays_outside(self):
        tw, said = route.time_weather(FOREST, 'contre-jour')
        self.assertFalse(tw.startswith('indoors'), tw)

    def test_inside_a_vehicle_in_a_blizzard_stays_outside(self):
        tw, _ = route.time_weather('a cable car over a chasm in a blizzard; inside, two silhouettes', '1-bit')
        self.assertFalse(tw.startswith('indoors'), tw)
        self.assertIn('snow', tw)

    def test_a_room_is_still_a_room(self):
        for req in ('inside the old library at night', 'the interior of a bakery at dawn',
                    'a cosy room on a snowy night'):
            self.assertTrue(route.time_weather(req, 'lofi')[0].startswith('indoors'), req)


class EraTest(unittest.TestCase):
    def frame(self, hexes):
        img = Image.new('RGB', (160, 144))
        px = img.load()
        cols = [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in hexes]
        for y in range(144):
            for x in range(160):
                px[x, y] = cols[(x // 40) % len(cols)]
        return img

    def test_any_one_hue_ramp_of_four_is_a_game_boy_screen(self):
        self.assertEqual(era.check(self.frame(['0f380f', '306230', '678e23', '9bbc0f']), 'gameboy')[0], [])
        self.assertEqual(era.check(self.frame(['1d2421', '3f4f45', '7c8f80', 'c4d0c0']), 'gameboy')[0], [])
        self.assertEqual(era.check(self.frame(['000000', '555555', 'aaaaaa', 'ffffff']), 'gameboy')[0], [])
        self.assertTrue(era.check(self.frame(['0f380f', '306230', 'c03030', '9bbc0f']), 'gameboy')[0])   # a red
        self.assertTrue(era.check(self.frame(['202020', '242424', '7c8f80', 'c4d0c0']), 'gameboy')[0])   # no step
        self.assertTrue(era.check(self.frame(['1d2421', '3f4f45', '7c8f80', 'c4d0c0']), 'cga')[0])

    def test_tiles_prints_its_count_against_a_budget(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bg.png'
            img = self.frame(['0f380f', '306230', '678e23', '9bbc0f'])
            for x, y in ((3, 3), (12, 21), (50, 30)):                      # three tiles with an odd pixel
                img.putpixel((x, y), (0x9b, 0xbc, 0x0f) if x < 40 else (0x0f, 0x38, 0x0f))
            img.save(path)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                era.main([str(path), '--era', 'gameboy', '--tiles', '--limit', '2'])
        self.assertIn('unique 8x8 background tiles, limit 2', out.getvalue())
        self.assertIn('the limit is 2', out.getvalue())


class FindTest(unittest.TestCase):
    def test_a_photo_in_the_scene_is_no_rebuild(self):
        self.assertEqual(library.query_tags('A hillside town in 2:1 isometric: a couple taking a photo on the '
                                            'footbridge.')['mode'], 'scene')
        self.assertEqual(library.query_tags('Rebuild this photo of a street')['mode'], 'rebuild')


class DocsTest(unittest.TestCase):
    def test_the_docs_agree_with_the_style_loop(self):
        brief = (REPO / 'references' / 'brief.md').read_text()
        self.assertIn('Author path only', brief.split('## Art director on the brief')[1].split('\n## ')[0])
        self.assertNotIn('pixelate new scene', (REPO / 'guides' / 'scenes.md').read_text())
        presets = (REPO / 'guides' / 'styles.md').read_text().split('## The presets')[1].split('\n## ')[0]
        for name in styles.STYLES:
            self.assertIn('`%s`' % name, presets, name)


if __name__ == '__main__':
    unittest.main()
