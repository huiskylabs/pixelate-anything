"""What four end-to-end runs at once (prompts 01 contre-jour, 07 sticker-iso, 12 Game Boy, 18 1-bit)
tripped on in the gate and the review: the gate crashed on the styles added last (no composition limits),
focus settled ties by position and judged value where a style has no value peak, a Hero line without a
box quietly fell back to the --actor bbox, the critic's thumbnail was a non-integer shrink that broke
dither and 1 px lines and its fixes could break the request's own rules, render printed a distance from
the starter on every run, and piece.json errors came one per render."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import check  # noqa: E402
import craftcheck  # noqa: E402
import critique  # noqa: E402
import distance  # noqa: E402
import library  # noqa: E402
import remix  # noqa: E402
import styles  # noqa: E402


def scene(size=(96, 54), colours=((30, 40, 60), (200, 120, 60), (240, 230, 200))):
    img = Image.new('RGB', size, colours[0])
    d = ImageDraw.Draw(img)
    d.rectangle([0, size[1] * 2 // 3, size[0] - 1, size[1] - 1], fill=colours[1])
    d.rectangle([40, 20, 52, 40], fill=colours[2])
    return img


class GateTest(unittest.TestCase):
    def test_every_style_has_limits_and_a_gate_that_runs(self):
        for name in styles.STYLES:
            self.assertIn(name, craftcheck.CRAFT, name)
            self.assertIn(name, craftcheck.COMPOSITION, name)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'f.png'
            scene().save(path)
            for name in styles.STYLES:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    check.frame(str(path), name)
                self.assertRegex(out.getvalue(), r'ALL PASS|FAIL: \d+ of \d+ checks', name)

    def test_focus_ties_are_not_settled_by_position(self):
        img = Image.new('RGB', (160, 90), (0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([20, 10, 39, 29], fill=(255, 255, 255))      # the hero, top left
        d.rectangle([120, 60, 139, 79], fill=(255, 255, 255))    # an equal light, bottom right
        hero = (20, 10, 39, 29)
        v = craftcheck.focus(img, hero)['focus_value'][0]
        flipped = craftcheck.focus(img.transpose(Image.ROTATE_180), (120, 60, 139, 79))['focus_value'][0]
        self.assertAlmostEqual(v, 0.5, delta=0.05)
        self.assertAlmostEqual(v, flipped, delta=0.01)

    def test_focus_keys_a_frame_cannot_be_judged_on(self):
        self.assertEqual(set(craftcheck.focus_off(scene(), 'sticker-iso')), {'focus_value', 'focus_contrast'})
        self.assertEqual(craftcheck.focus_off(scene(), 'lofi'), {})
        two = scene(colours=((0, 0, 0), (255, 255, 255), (255, 255, 255)))
        self.assertEqual(set(craftcheck.focus_off(two, '1-bit')), {'focus_value'})
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'f.png'
            two.save(path)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                check.frame(str(path), '1-bit', hero={'bbox': (40, 20, 52, 40)})
        self.assertRegex(out.getvalue(), r'SKIP focus value +two colours')
        self.assertRegex(out.getvalue(), r'(PASS|FAIL) focus contrast')

    def test_a_hero_line_without_a_box_is_a_problem(self):
        with tempfile.TemporaryDirectory() as d:
            brief = Path(d) / 'brief.md'
            brief.write_text('## 4. The scene\n- Hero: the lantern girl; peak value: her lantern; peak chroma: it\n')
            self.assertIsNone(check.brief_hero(brief))
            self.assertTrue(any('Hero line has no x0,y0,x1,y1 box' in p for p in check.brief_plan(brief)['problems']))
            brief.write_text('## 4. The scene\n- Hero: 40,20,52,40 (native px); peak value: her lantern; peak '
                             'chroma: it\n')
            self.assertEqual(check.brief_plan(brief)['problems'], [])


class CriticTest(unittest.TestCase):
    def thumb(self, native, scale):
        with tempfile.TemporaryDirectory() as d:
            frame = Path(d) / 'f.png'
            native.resize((native.width * scale, native.height * scale), Image.NEAREST).save(frame)
            tp, _, _, w = critique.thumbnails(frame)
            return Image.open(tp).convert('RGB'), w

    def test_the_thumbnail_is_a_whole_number_scale_of_the_art(self):
        art = Image.new('RGB', (384, 216), (0, 0, 0))
        px = art.load()
        for y in range(216):
            for x in range(0, 384, 2):
                px[x + (y % 2), y] = (255, 255, 255)              # a checker dither of 1 px dots
        for scale in (2, 4, 5):
            thumb, w = self.thumb(art, scale)
            self.assertEqual(w, 384, scale)
            self.assertEqual(thumb.tobytes(), art.tobytes(), scale)
        gb = scene((160, 144))
        thumb, w = self.thumb(gb, 3)
        self.assertEqual(w, 480)
        self.assertEqual(thumb.resize((160, 144), Image.NEAREST).tobytes(), gb.tobytes())

    def test_the_critic_keeps_the_request_rules(self):
        with tempfile.TemporaryDirectory() as d:
            frame = Path(d) / 'f.png'
            scene().resize((192, 108), Image.NEAREST).save(frame)
            brief = Path(d) / 'brief.md'
            brief.write_text('Request: a Game Boy post office\n\n## 0. Choices\nx\n\n## 10. Never\n- Rain longer than '
                             '2 px.\n\n## 11. Technical\n- x\n')
            text = critique.prompt(frame, brief)
        self.assertIn('Rain longer than 2 px', text)
        self.assertIn('A fix that would break one is not a fix', text)
        self.assertIn('find it in the frame at delivered size', text)


class PieceTest(unittest.TestCase):
    def test_a_starter_base_prints_no_distance(self):
        rec = {'base': {'id': 'starter-scene-still', 'library': 'x', 'output': 'still', 'status': 'starter'},
               'pixels': None, 'palette': None, 'reason': 'size changed', 'warning': None}
        self.assertEqual(distance.line(rec), '')
        rec['base'].update(id='harbour', status='study')
        self.assertIn('distance from harbour/still', distance.line(rec))

    def test_every_wrong_tag_in_one_message(self):
        data = json.loads((REPO / 'library' / 'starter-scene-still' / 'piece.json').read_text())
        data['tags'].update(camera='iso', motion='still')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'starter-scene-still'
            import shutil
            shutil.copytree(REPO / 'library' / 'starter-scene-still', root)
            (root / 'piece.json').write_text(json.dumps(data))
            with self.assertRaises(library.LibraryError) as e:
                library.validate(root)
            self.assertIn('tags.camera', str(e.exception))
            self.assertIn('tags.motion', str(e.exception))
            del data['knobs']
            data['tags'].update(camera='side', motion='stills')
            (root / 'piece.json').write_text(json.dumps(data))
            with self.assertRaises(library.LibraryError) as e:
                library.validate(root)
            self.assertIn("missing ['knobs']", str(e.exception))

    def test_remix_md_lists_the_manifest_fields(self):
        base = library.validate(REPO / 'library' / 'starter-scene-still')
        manifest = dict(base, id='temple', lineage={'remixed_from': base['id']})
        text = remix.remix_md(manifest, base, {'test': {'outputs': []}}, '0' * 64)
        self.assertIn('`canvas`, each image output\'s `size`, `scale`', text)
        self.assertIn('keep `knobs`', text)
        self.assertNotIn('Read the distance from the base', text)


if __name__ == '__main__':
    unittest.main()
