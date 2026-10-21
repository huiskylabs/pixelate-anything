"""What the twenty 5 s GIF runs tripped on: "a modern 16-bit-style JRPG" routed as the SNES era, the
brief ignored a stated 12 fps clock (30 fps, 120 frames, APNG excerpts), and `pixelate gif` only took
engine scenes, so every piece drawn in Python wrote its own GIF exporter."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import route  # noqa: E402


class BitLook(unittest.TestCase):
    def test_descriptive_bit_words_are_not_an_era(self):
        for text in ('a rich modern 16-bit-style JRPG overworld', 'an 8-bit inspired forest',
                     'a 16 bit style castle', 'a modern 16-bit JRPG town'):
            self.assertIsNone(route.era_of(text), text)
            self.assertEqual(route.route(text)['mode'], 'scene', text)

    def test_consoles_and_bare_bit_words_still_name_an_era(self):
        self.assertEqual(route.era_of('a 16-bit game screen'), 'snes')
        self.assertEqual(route.era_of('like a 16-bit RPG town that obeys the SNES limits'), 'snes')
        self.assertEqual(route.era_of('an 8-bit NES platformer'), 'nes')


class StatedClock(unittest.TestCase):
    REQ = 'a lantern procession at dusk. Length: 5 s, 60 frames on a 12 fps clock.'

    def test_fps_and_frames_parse(self):
        self.assertEqual(route.fps_of(self.REQ), 12)
        self.assertEqual(route.frames_of(self.REQ), 60)

    def test_brief_uses_the_stated_clock(self):
        for style in ('lofi', 'contre-jour'):
            loop = [l for l in route.brief(style, self.REQ).splitlines() if l.startswith('- Loop:')]
            self.assertEqual(len(loop), 1, style)
            self.assertIn('60 frames at 12 fps', loop[0])
            self.assertNotIn('APNG excerpts', loop[0])


class FramesGif(unittest.TestCase):
    def test_folder_of_frames_to_exact_gif(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp) / 'frames'
            frames.mkdir()
            for k in range(60):
                im = Image.new('RGB', (160, 144), (20, 30, 20))
                im.putpixel((k * 2, 70), (200, 220, 180))
                im.save(frames / ('%03d.png' % k))
            out = Path(tmp) / 'loop.gif'
            subprocess.run([str(REPO / 'pixelate'), 'gif', str(frames), str(out), '--fps', '12', '--size', '768x432'],
                           check=True, capture_output=True)
            gif = Image.open(out)
            self.assertEqual(gif.size, (768, 432))
            total = 0
            for k in range(gif.n_frames):
                gif.seek(k)
                total += gif.info['duration']
            self.assertEqual(total, 5000)
            gif.seek(0)
            rgb = gif.convert('RGB')
            self.assertEqual(rgb.getpixel((0, 0)), (20, 30, 20))      # pillarbox in the darkest colour
            self.assertEqual(rgb.getpixel((144, 70 * 3)), (200, 220, 180))


if __name__ == '__main__':
    unittest.main()
