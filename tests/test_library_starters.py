"""The three phase-2 starters (docs/PLAN-library.md section 6.2): `starter-scene-still`,
`starter-era-nes` and `starter-rebuild-perspective`.

They pin what the starters claim: a schema-1 `starter` manifest with one image output and its tracked
1x golden, placeholders only, a clean-copy render that reproduces the golden losslessly and passes its
technical gate (`library test`), NES limits for the era starter, and a genuine two-point camera for
the rebuild starter. A passing gate is a technical check, not review or approval of any piece.
"""
import ast
import contextlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
LIBRARY = REPO / 'library'
TOOLS = REPO / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('piece_library_starters', TOOLS / 'library.py')
assert spec is not None and spec.loader is not None
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)
import era  # noqa: E402  # pyright: ignore[reportMissingImports]
import render  # noqa: E402  # pyright: ignore[reportMissingImports]  the module library.kit_render() imports

# id: (mode, camera, era tag, output name, 1x size, scale)
STARTERS = {
    'starter-scene-still': ('scene', 'side', 'none', 'still', (320, 180), 4),
    'starter-era-nes': ('era', 'side', 'nes', 'screen', (256, 224), 3),
    'starter-rebuild-perspective': ('rebuild', 'two-point perspective', 'none', 'corner', (320, 180), 4),
}
# an authored subject or a borrowed one; history notes may say what is not drawn, so they are not scanned
SUBJECT_WORDS = re.compile(
    r'\b(cabins?|pines?|hills?|rain|moons?|clouds?|houses?|fireflies|trees?|stars?|windows?|doors?|roofs?|'
    r'buildings?|towers?|castles?|people|person|characters?|creatures?|animals?|mario|zelda|mega ?man|sonic|'
    r'metroid|castlevania|pok[eé]mon|kirby|nintendo|mushrooms?|koopas?|goombas?|coins?)\b', re.I)


def manifest(piece_id):
    return json.loads((LIBRARY / piece_id / 'piece.json').read_text(encoding='utf-8'))


def image_output(piece_id):
    (output,) = [o for o in manifest(piece_id)['outputs'] if o['kind'] == 'image']
    return output


def load(path):
    with Image.open(path) as im:
        return im.convert('RGBA')


def render_alone(piece_id, where):
    """copy the piece, without its generated out/ files, into a folder of its own and run its command
    the way `pixelate render` and `library test` do; returns the copy"""
    root = Path(where) / 'elsewhere' / piece_id
    shutil.copytree(LIBRARY / piece_id, root, ignore=shutil.ignore_patterns('__pycache__', '.pixelate'))
    for path in (root / 'out').iterdir():
        if path.name != 'golden':
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    result = render.run_command(image_output(piece_id)['run'], root, render.piece_env(), timeout=300)
    assert result['ok'], result
    return root


@contextlib.contextmanager
def piece_modules(piece_id, *names):
    """import a starter's art modules by name, then drop them again, so two pieces' `pal` never meet;
    no bytecode is written into the library"""
    art = str(LIBRARY / piece_id / 'art')
    before, bytecode = set(sys.modules), sys.dont_write_bytecode
    sys.path.insert(0, art)
    sys.dont_write_bytecode = True
    try:
        yield [importlib.import_module(name) for name in names]
    finally:
        sys.path.remove(art)
        sys.dont_write_bytecode = bytecode
        for name in set(sys.modules) - before:
            if str(getattr(sys.modules[name], '__file__', '') or '').startswith(art):
                del sys.modules[name]


class StarterManifestTest(unittest.TestCase):
    def test_schema_1_starters_with_one_image_and_honest_status(self):
        for piece_id, (mode, camera, era_tag, name, (w, h), scale) in STARTERS.items():
            with self.subTest(piece=piece_id):
                data = library.validate(LIBRARY / piece_id)
                self.assertEqual((data['schema'], data['id'], data['status'], data['mode'], data['runtime']),
                                 (1, piece_id, 'starter', mode, 'script'))
                self.assertEqual((data['tags']['camera'], data['tags']['era'], data['tags']['motion']),
                                 (camera, era_tag, 'stills'))
                self.assertNotIn('review', data)          # no review or approval is claimed
                self.assertEqual(data['knobs'], {})
                self.assertEqual(data['license'], 'MIT')
                self.assertEqual(data['lineage'], {'remixed_from': None})
                (output,) = data['outputs']
                self.assertEqual((output['name'], output['golden'], output['size'], output['scale']),
                                 (name, f'out/golden/{name}.png', {'w': w, 'h': h}, scale))
                self.assertEqual(output['brief'], 'brief.md')
                self.assertNotRegex(data['summary'] + data['request'], r'(?i)accepted|reviewed|approved')

    def test_goldens_and_media_are_small_bounded_rgba_files(self):
        for piece_id, (*_, name, size, _scale) in STARTERS.items():
            with self.subTest(piece=piece_id):
                golden = LIBRARY / piece_id / 'out' / 'golden' / f'{name}.png'
                with Image.open(golden) as im:
                    self.assertEqual((im.mode, im.size), ('RGBA', size))
                self.assertLess(golden.stat().st_size, 100_000)
                media = manifest(piece_id)['media']
                self.assertLessEqual(max(load(LIBRARY / piece_id / media['thumb']).size), 256)
                self.assertLessEqual(max(load(LIBRARY / piece_id / media['contact']).size), 520)
                for key in ('thumb', 'contact'):
                    self.assertLess((LIBRARY / piece_id / media[key]).stat().st_size, 250_000)

    @unittest.skipUnless((REPO / '.git').exists(), 'needs a git checkout')
    def test_golden_and_media_are_tracked_and_the_full_size_frame_is_not(self):
        # --cached alone: an untracked file would pass a check that includes --others
        listed = subprocess.run(['git', 'ls-files', '--cached', 'library'],
                                cwd=REPO, capture_output=True, text=True, check=True).stdout.split('\n')
        for piece_id in STARTERS:
            output, media = image_output(piece_id), manifest(piece_id)['media']
            with self.subTest(piece=piece_id):
                for path in (output['golden'], media['thumb'], media['contact']):
                    self.assertIn(f'library/{piece_id}/{path}', listed)
                for path in (output['frame'], output['pal']):
                    self.assertNotIn(f'library/{piece_id}/{path}', listed)

    def test_index_lists_the_three_starters_among_23_pieces(self):
        index = json.loads((LIBRARY / 'index.json').read_text(encoding='utf-8'))
        self.assertEqual((LIBRARY / 'index.json').read_bytes(), library.index(LIBRARY))
        ids = [p['id'] for p in index['pieces']]
        self.assertEqual(len(ids), 23)
        self.assertEqual(ids, sorted(ids))
        self.assertLessEqual(set(STARTERS), set(ids))
        self.assertEqual(sorted(p['id'] for p in index['pieces'] if p['status'] == 'starter'),
                         sorted(['starter-assets', 'starter-music', 'starter-scene-loop', *STARTERS]))


class StarterNeutralityTest(unittest.TestCase):
    """Starters are empty pieces (plan section 2.1): placeholders, no authored or borrowed subject."""

    def sources(self, piece_id):
        root = LIBRARY / piece_id
        return {str(p.relative_to(root)): p.read_text(encoding='utf-8') for p in sorted(root.rglob('*'))
                if p.is_file() and p.suffix in ('.py', '.md', '.json') and 'history' not in p.parts
                and '__pycache__' not in p.parts}

    def test_no_authored_or_borrowed_subject(self):
        for piece_id in STARTERS:
            for name, text in self.sources(piece_id).items():
                with self.subTest(piece=piece_id, file=name):
                    self.assertIsNone(SUBJECT_WORDS.search(text), SUBJECT_WORDS.search(text))

    def test_code_stays_small_and_imports_only_the_kit_and_itself(self):
        allowed = set(sys.stdlib_module_names) | {'numpy', 'PIL'} | {p.stem for p in TOOLS.glob('*.py')}
        for piece_id in STARTERS:
            sources = sorted((LIBRARY / piece_id / 'art').glob('*.py'))
            own = {p.stem for p in sources}
            self.assertLessEqual(sum(len(p.read_text().splitlines()) for p in sources), 260, piece_id)
            for path in sources:
                for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                        [node.module or ''] if isinstance(node, ast.ImportFrom) else []
                    for name in names:
                        with self.subTest(piece=piece_id, file=path.name, name=name):
                            self.assertIn(name.split('.')[0], allowed | own)
                            self.assertNotEqual(name.split('.')[0], 'iso')   # no orthographic preset

    def test_scene_still_draws_only_its_two_placeholder_slot_maps(self):
        with piece_modules('starter-scene-still', 'sprites') as (sprites,):
            maps = sorted(k for k, v in vars(sprites).items() if isinstance(v, dict) and 'px' in v)
        self.assertEqual(maps, ['BLOCK', 'MARKER'])


class StarterRenderTest(unittest.TestCase):
    """`library test` on each starter, plus a render of a lone clean copy compared pixel for pixel."""

    @classmethod
    def setUpClass(cls):
        cls.report = library.test(LIBRARY, list(STARTERS), quick=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.copies = {piece_id: render_alone(piece_id, cls.tmp.name) for piece_id in STARTERS}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_library_test_quick_matches_goldens_and_passes_the_gate(self):
        self.assertTrue(self.report['ok'])
        self.assertTrue(self.report['gate_ok'])
        for piece in self.report['pieces']:
            with self.subTest(piece=piece['id']):
                (output,) = piece['outputs']
                self.assertEqual((output['status'], output['tested'], output['gate_ok']), ('passed', True, True))
                self.assertEqual(output['golden'], {'ok': True, 'pixels': 0})
                self.assertEqual(output['gate']['fail'], [])

    def test_lone_clean_copy_reproduces_the_golden_losslessly_and_deterministically(self):
        for piece_id, root in self.copies.items():
            output = image_output(piece_id)
            with self.subTest(piece=piece_id):
                frame, golden = load(root / output['frame']), load(LIBRARY / piece_id / output['golden'])
                scale = output['scale']
                self.assertEqual(frame.size, (golden.width * scale, golden.height * scale))
                # every native cell is flat, so the 1x golden plus the scale is the whole frame
                self.assertEqual(frame.tobytes(), golden.resize(frame.size, Image.Resampling.NEAREST).tobytes())
                first = (root / output['frame']).read_bytes()
                again = render.run_command(output['run'], root, render.piece_env(), timeout=300)
                self.assertTrue(again['ok'], again)
                self.assertEqual((root / output['frame']).read_bytes(), first)

    def test_frames_pass_the_declared_gate_with_their_palette_and_brief(self):
        for piece_id, root in self.copies.items():
            output = image_output(piece_id)
            with self.subTest(piece=piece_id):
                result = subprocess.run([sys.executable, str(REPO / 'pixelate'), *render.gate_args(output)],
                                        cwd=root, capture_output=True, text=True, timeout=300)
                self.assertEqual(result.returncode, 0, result.stdout[-1500:])
                self.assertIn('PASS palette', result.stdout)
                self.assertTrue(result.stdout.rstrip().endswith('ALL PASS'), result.stdout[-300:])

    def test_nes_frame_passes_check_era_nes_alone(self):
        root = self.copies['starter-era-nes']
        result = subprocess.run([sys.executable, str(REPO / 'pixelate'), 'check', 'out/screen.png', '--era', 'nes',
                                 '--scale', '3'], cwd=root, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertRegex(result.stdout, r'PASS era nes\s+13 colours')
        self.assertRegex(result.stdout, r'PASS era tiles \(whole frame\)')

    def test_nes_background_sprites_and_palette_keep_the_hardware_limits(self):
        root = self.copies['starter-era-nes']
        screen = Image.open(root / 'out' / 'screen.png').convert('RGB')
        native = screen.resize((256, 224), Image.Resampling.NEAREST)
        bg = Image.open(root / 'out' / 'bg.png').convert('RGB')
        self.assertEqual(era.ERAS['nes']['size'], bg.size)
        self.assertEqual(era.check(native, 'nes')[0], [])
        # the background alone: every 16x16 attribute block one 3-colour sub-palette plus the backdrop
        self.assertEqual(era.check(bg, 'nes', layer='bg', tiles=True)[0], [])
        self.assertLessEqual(era.unique_tiles(bg, 'nes'), era.ERAS['nes']['bg_tiles'])
        # the declared sprites: 8 per scanline, 64 in all; the marker is four 8x8 hardware sprites
        boxes = json.loads((root / 'out' / 'oam.json').read_text())['sprites']
        issues, count = era.check_sprites(boxes, 'nes')
        self.assertEqual((issues, count), ([], 4))
        with piece_modules('starter-era-nes', 'nespal', 'tiles', 'screen') as (nespal, tiles, screen_mod):
            master = {line.strip().lower() for line in (REPO / 'palettes' / 'nes.hex').read_text().splitlines() if line.strip()}
            declared = [nespal.BACKDROP] + [h for sub in nespal.BG + nespal.SPRITES for h in sub]
            self.assertLessEqual(set(declared), master)
            self.assertLessEqual(len(nespal.BG), 4)
            self.assertLessEqual(len(nespal.SPRITES), 4)
            for name, pattern in tiles.SPRITE_TILES.items():
                # 3 colours plus transparent per sprite
                self.assertLessEqual({v for row in pattern for v in row}, {0, 1, 2, 3}, name)
            self.assertEqual([(x, y, 8, 8) for x, y, _, _ in screen_mod.OAM], [tuple(b) for b in boxes])
        # outside the sprite boxes the screen is the background, pixel for pixel
        outside = np.ones((224, 256), bool)
        for bx, by, w, h in boxes:
            outside[by:by + h, bx:bx + w] = False
        self.assertTrue((np.asarray(native)[outside] == np.asarray(bg)[outside]).all())


class TwoPointCameraTest(unittest.TestCase):
    """The rebuild starter's camera is a real two-point projection, not an orthographic preset."""

    @classmethod
    def setUpClass(cls):
        with piece_modules('starter-rebuild-perspective', 'scene', 'massing') as (scene, massing):
            cls.scene, cls.massing = scene, massing
            cls.cam = scene.camera()
            cls.faces = [(block, axis, quad) for block in scene.BLOCKS for axis, quad in massing.faces(cls.cam, block)]
            cls.panels = [(axis, panel) for _, axis, quad in cls.faces for panel in massing.panels(quad)]

    def vp(self, axis):
        return self.cam.vanishing_point((1, 0) if axis == 'x' else (0, 1))

    def assertThrough(self, a, b, point):
        """the screen line a-b, extended, passes through point (to float precision)"""
        (ax, ay), (bx, by), (px, py) = a, b, point
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        self.assertAlmostEqual(cross / ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5, 0.0, places=6)

    def test_two_distinct_finite_vanishing_points_on_the_horizon(self):
        left, right = self.vp('y'), self.vp('x')
        self.assertAlmostEqual(left[0], self.scene.VP_LEFT, places=9)
        self.assertAlmostEqual(right[0], self.scene.VP_RIGHT, places=9)
        self.assertEqual(left[1], right[1])
        self.assertEqual(left[1], self.scene.HORIZON)
        self.assertLess(left[0], self.scene.CX)
        self.assertLess(self.scene.CX, right[0])
        self.assertGreater(right[0] - left[0], self.scene.W)       # distinct, and both off the frame here
        # the two axes are perpendicular in the world: (vR - cx)(cx - vL) = f^2
        self.assertAlmostEqual((right[0] - self.cam.cx) * (self.cam.cx - left[0]), self.cam.f ** 2, places=6)

    def test_receding_edges_of_every_face_and_panel_meet_their_own_vanishing_point(self):
        quads = [(axis, quad) for _, axis, quad in self.faces] + self.panels
        self.assertEqual(sorted({axis for _, axis, _ in self.faces}), ['x', 'y'])
        for axis, quad in quads:
            s = [self.cam.project(p) for p in quad]
            self.assertThrough(s[0], s[1], self.vp(axis))           # bottom edge
            self.assertThrough(s[3], s[2], self.vp(axis))           # top edge
            self.assertAlmostEqual(s[0][0], s[3][0], places=9)      # verticals stay vertical
            self.assertAlmostEqual(s[1][0], s[2][0], places=9)

    def test_depth_foreshortens_unlike_an_orthographic_view(self):
        # equal world steps along a receding edge get shorter on screen, and a face's far edge is
        # shorter than its near edge; an orthographic or isometric view keeps both equal
        for block, axis, quad in self.faces:
            with self.subTest(block=block, axis=axis):
                s = [self.cam.project(p) for p in quad]
                (x0, y0, _), (x1, y1, _) = quad[0], quad[1]
                xs = [self.cam.project((x0 + (x1 - x0) * k / 4, y0 + (y1 - y0) * k / 4, 0))[0] for k in range(5)]
                steps = [abs(b - a) for a, b in zip(xs, xs[1:], strict=False)]
                self.assertTrue(all(b < a for a, b in zip(steps, steps[1:], strict=False)), steps)
                near, far = abs(s[3][1] - s[0][1]), abs(s[2][1] - s[1][1])
                self.assertLess(far, near * 0.95)

    def test_rendered_corner_and_camera_record_follow_the_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = render_alone('starter-rebuild-perspective', tmp)
            frame = load(root / 'out' / 'corner.png').resize((320, 180), Image.Resampling.NEAREST).convert('RGB')
            guides = json.loads((root / 'out' / 'camera.json').read_text())
        self.assertEqual(guides['vanishing_points'], [list(self.vp('y')), list(self.vp('x'))])
        self.assertEqual(guides['horizon_y'], self.scene.HORIZON)
        # the near block's corner: its lit face (along y, left of the corner) and its shaded face (along x)
        near = min(self.scene.BLOCKS, key=lambda b: self.cam.depth((b[0], b[1], 0)))
        cx, top = self.cam.project((near[0], near[1], near[4]))
        _, bottom = self.cam.project((near[0], near[1], 0))
        y = round((top + bottom) / 2)
        hexes = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in self.scene.PALETTE.items()}
        self.assertEqual(frame.getpixel((round(cx) - 3, y)), hexes['A0'])
        self.assertEqual(frame.getpixel((round(cx) + 3, y)), hexes['A1'])


if __name__ == '__main__':
    unittest.main()
