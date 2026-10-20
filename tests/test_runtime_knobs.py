"""`pixelate render DIR --set` on engine and pack pieces: the PIXELATE_KNOBS constant the engine build puts
before a scene's scripts (tools/build.py), the pack.json options an export takes from knobs
(tools/assets.py), and the catalog rules that keep a declared knob reaching its program
(tools/library.py). Renders run on copies of the trusted starters `starter-scene-loop` and `starter-assets`."""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
LIBRARY = REPO / 'library'
sys.path.insert(0, str(REPO / 'tools'))
import build  # noqa: E402
import library  # noqa: E402
import piece  # noqa: E402

HAVE_NODE = shutil.which('node') is not None
SCENE_SOURCES = ('piece.json', 'scene.json', 'config.js', 'scene.js', 'palettes.js', 'sprites.js', 'music.js',
                 'out/golden/day.png', 'out/golden/night.png')
PACK_SOURCES = ('piece.json', 'pack.json', 'palette.json', 'sprites/slots.px', 'out/atlas.png', 'out/atlas.json',
                'out/contact.png')
# The day palette's ground edge (G0) and lowest sky band (S2) of starter-scene-loop/palettes.js.
G0, S2 = (0x80, 0x96, 0x6f, 255), (0x6f, 0x8e, 0x9c, 255)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def clean_env():
    return {key: value for key, value in os.environ.items() if key not in (piece.ENV, 'PIXELATE_NO_LOG')}


def pixelate(*args, env=None, cwd=None):
    return subprocess.run([sys.executable, str(REPO / 'pixelate'), *args], capture_output=True, text=True,
                          env=env or clean_env(), cwd=cwd)


def one_x(path, size):
    with Image.open(path) as im:
        return im.convert('RGBA').resize(size, Image.NEAREST)


class Copy(unittest.TestCase):
    """A temporary library holding a copy of one checked-in starter."""
    PIECE = ''

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.library = self.temp / 'library'
        self.root = self.library / self.PIECE
        shutil.copytree(LIBRARY / self.PIECE, self.root,
                        ignore=shutil.ignore_patterns('__pycache__', '.pixelate', 'render-report.json'))
        self.data = json.loads((self.root / 'piece.json').read_text(encoding='utf-8'))

    def render(self, *args, env=None):
        result = pixelate('render', str(self.root), '--json', *args, env=env)
        return result, (json.loads(result.stdout) if result.stdout.startswith('[') else [])

    def sets(self, *values):
        return [arg for value in values for arg in ('--set', value)]

    def knob_file(self, content, name='knobs.json'):
        path = self.temp / name
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding='utf-8')
        path.chmod(0o600)
        return path

    def write_manifest(self, data):
        (self.root / 'piece.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    def sources(self, names):
        return {name: sha((self.root / name).read_bytes()) for name in names}

    def assert_refused_before_anything_runs(self, sets, message):
        (self.root / 'out' / 'stale.png').write_bytes(b'stale')
        before = tree(self.root)
        result, _ = self.render(*self.sets(*sets))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)
        self.assertEqual(tree(self.root), before)


class JsConstant(unittest.TestCase):
    """piece.js_constant: the engine constant, safe in a script, in a page and under the builder's text edits."""
    HOSTILE = "</script><script>alert(1)</script>'use strict';\" \\ \u2028\u2029 é 😀 const DEBUG_BUILD = true;"

    def test_every_character_outside_a_slug_alphabet_is_an_escape(self):
        line = piece.js_constant({'horizon': 84, 'label': self.HOSTILE, 'zoom': 0.5, 'lit': True, 'off': False})
        self.assertEqual(line[:37], 'const PIXELATE_KNOBS = Object.freeze(')
        self.assertTrue(line.endswith('});\n'))
        body = line[len('const PIXELATE_KNOBS = Object.freeze('):-len(');\n')]
        for unsafe in ('<', '>', "'", '/script', 'use strict', 'DEBUG_BUILD = true', '\u2028', 'é', '\\\\'):
            self.assertNotIn(unsafe, body)
        self.assertTrue(body.isascii())
        self.assertIn('"horizon": 84', body)
        self.assertIn('"zoom": 0.5, "lit": true, "off": false', body)
        self.assertIn('\\ud83d\\ude00', body)

    @unittest.skipUnless(HAVE_NODE, 'evaluates the constant in Node')
    def test_node_reads_back_the_exact_values_and_cannot_change_them(self):
        merged = {'horizon': -84, 'label': self.HOSTILE, 'zoom': 0.5, 'lit': True, 'big': piece.INT_LIMIT}
        script = piece.js_constant(merged) + (
            "'use strict'; try { PIXELATE_KNOBS.horizon = 1; } catch (e) {}"
            " console.log(JSON.stringify(PIXELATE_KNOBS));")
        out = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), merged)

    def test_values_no_runtime_carries_exactly_are_refused(self):
        for value in (2 ** 53, float('nan'), float('inf'), None, [1], {'a': 1}):
            with self.subTest(value=value):
                with self.assertRaises(piece.KnobError):
                    piece.js_constant({'k': value})


class Catalog(Copy):
    """Declared engine and pack knobs must reach their program; the catalog refuses the rest."""
    PIECE = 'starter-scene-loop'

    def refused(self, knobs, message):
        self.write_manifest(dict(self.data, knobs=knobs))
        with self.assertRaises(library.LibraryError) as caught:
            library.validate(self.root)
        self.assertIn(message, str(caught.exception))

    def test_an_engine_knob_must_be_read_by_a_script_the_build_loads(self):
        horizon = self.data['knobs']['horizon']
        self.assertEqual(library.validate(self.root)['knobs'], {'horizon': horizon})
        self.refused({'horizon': dict(horizon, edits='scene.json')}, 'edits scene.json is not a script the build loads')
        self.refused({'horizon': dict(horizon, edits='piece.json')}, 'is not a script the build loads')
        self.refused({'ground': dict(horizon)}, 'scene.js does not read PIXELATE_KNOBS.ground')
        self.refused({'hori': dict(horizon)}, 'scene.js does not read PIXELATE_KNOBS.hori')
        self.refused({'horizon': dict(horizon, edits='config.js')}, 'config.js does not read PIXELATE_KNOBS.horizon')
        # A name the scripts read in brackets counts too.
        (self.root / 'sprites.js').write_text((self.root / 'sprites.js').read_text() +
                                              "\nconst SKY_ROW = PIXELATE_KNOBS['sky-row'];\n", encoding='utf-8')
        self.write_manifest(dict(self.data, knobs={'sky-row': dict(horizon, edits='sprites.js')}))
        self.assertIn('sky-row', library.validate(self.root)['knobs'])
        (self.root / 'scene.json').write_text('{"files": "scene.js"}', encoding='utf-8')
        self.refused({'horizon': horizon}, 'scene.json: expected files')

    def test_a_pack_knob_must_set_an_allowed_pack_json_option_it_defaults_to(self):
        pack = Path(self.temp / 'library' / 'starter-assets')
        shutil.copytree(LIBRARY / 'starter-assets', pack)
        self.root, self.data = pack, json.loads((pack / 'piece.json').read_text(encoding='utf-8'))
        scale = self.data['knobs']['scale']
        self.assertEqual(library.validate(pack)['knobs'], {'scale': scale})
        for knobs, message in (({'scale': dict(scale, edits='palette.json')}, 'edits pack.json'),
                               ({'scale': {'type': 'int', 'default': 8, 'edits': 'pack.json'}}, 'an enum of values'),
                               ({'name': {'values': ['a', 'b'], 'default': 'a', 'edits': 'pack.json'}},
                                'a pack knob sets a pack.json option (scale) of its name'),
                               ({'palette': {'values': ['palette.json', '../x.json'], 'default': 'palette.json',
                                             'edits': 'pack.json'}}, 'a pack knob sets a pack.json option'),
                               ({'scale': dict(scale, values=[8, 0])}, 'pack.json scale must be an integer from 1 to 64, got 0'),
                               ({'scale': dict(scale, values=[8, 65])}, 'got 65'),
                               ({'scale': dict(scale, values=[8, True])}, 'got true'),
                               ({'scale': dict(scale, values=[8, 4.0])}, 'got 4.0'),
                               ({'scale': dict(scale, values=[8, '4'])}, 'got "4"'),
                               ({'scale': dict(scale, values=[4, 8], default=4)}, 'default 4 must equal pack.json scale 8')):
            with self.subTest(knobs=knobs):
                self.refused(knobs, message)
        (pack / 'pack.json').write_text((pack / 'pack.json').read_text().replace('"scale": 8', '"scale": 8.0'))
        self.refused({'scale': scale}, 'default 8 must equal pack.json scale 8.0')


class BuildConstant(Copy):
    """tools/build.py puts the constant before every engine script, from the piece's knobs and the set file."""
    PIECE = 'starter-scene-loop'

    def scene_js(self, path=None):
        with mock.patch.dict(os.environ, {piece.ENV: str(path)} if path else {}):
            if path is None:
                os.environ.pop(piece.ENV, None)
            return build.scene_js(self.root, with_audio=False, with_main=False)

    def test_the_constant_follows_use_strict_with_defaults_or_set_values(self):
        self.assertTrue(self.scene_js().startswith(
            "'use strict';\nconst PIXELATE_KNOBS = Object.freeze({\"horizon\": 84});\n/* ---- config.js ---- */"))
        self.assertIn('Object.freeze({"horizon": 88})', self.scene_js(self.knob_file({'horizon': 88})))

    def test_a_bad_file_a_strict_type_or_no_manifest_stops_the_build(self):
        for content, message in (({'horizon': 86}, 'knob horizon: 86 is not one of [80, 84, 88]'),
                                 ({'horizon': 84.0}, 'knob horizon: 84.0 is not one of'),
                                 ({'horizon': '88'}, 'knob horizon: "88" is not one of'),
                                 ({'season': 'winter'}, 'no such knob season'),
                                 ('{"horizon": 80, "horizon": 88}', 'duplicate key horizon')):
            with self.subTest(content=content):
                with self.assertRaises(SystemExit) as caught:
                    self.scene_js(self.knob_file(content))
                self.assertIn(message, str(caught.exception))
        path = self.knob_file({'horizon': 88})
        (self.root / 'piece.json').unlink()
        with self.assertRaises(SystemExit) as caught:
            self.scene_js(path)
        self.assertIn('PIXELATE_KNOBS is set, but', str(caught.exception))
        # A scene that is not a piece builds as before, with no constant.
        self.assertNotIn('PIXELATE_KNOBS =', build.scene_js(LIBRARY / 'lantern-isle', with_audio=False, with_main=False))

    def test_a_declared_string_cannot_break_out_of_the_page(self):
        hostile = JsConstant.HOSTILE
        (self.root / 'scene.js').write_text((self.root / 'scene.js').read_text() +
                                            '\nconst LABEL = PIXELATE_KNOBS.label;\n', encoding='utf-8')
        self.write_manifest(dict(self.data, knobs=dict(self.data['knobs'], label={
            'values': ['plain', hostile], 'default': 'plain', 'edits': 'scene.js'})))
        library.validate(self.root)
        path = self.knob_file({'label': hostile})
        with contextlib.redirect_stdout(io.StringIO()):
            plain = build.build(self.root, release=True, out=self.temp / 'plain.html').read_text()
            with mock.patch.dict(os.environ, {piece.ENV: str(path)}):
                page = build.build(self.root, release=True, out=self.temp / 'page.html').read_text()
        self.assertEqual(page.count('</script>'), plain.count('</script>'))
        self.assertEqual(page.count('<script'), plain.count('<script'))
        self.assertIn('const DEBUG_BUILD = false;', page)
        self.assertNotIn('alert(1)', page)
        if HAVE_NODE:
            # The scene's own script reads the declared string back exactly.
            script = self.scene_js(path) + '\nconsole.log(JSON.stringify([LABEL, PIXELATE_KNOBS.horizon]));'
            out = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True).stdout
            self.assertEqual(json.loads(out), [hostile, 84])


@unittest.skipUnless(HAVE_NODE, 'engine frames are rendered in Node')
class EngineStarter(Copy):
    """starter-scene-loop's `horizon` knob, read by scene.js as PIXELATE_KNOBS.horizon."""
    PIECE = 'starter-scene-loop'
    SIZE = (240, 135)

    def frames(self):
        return {name: (self.root / f'out/t{t}.png').read_bytes() for name, t in (('day', '0000.00'), ('night', '0030.00'))}

    def test_defaults_match_the_goldens_and_each_horizon_draws_its_own_deterministic_frames(self):
        sources = self.sources(SCENE_SOURCES)
        result, records = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('knobs', records[0])
        for name in ('day', 'night'):
            golden = one_x(self.root / f'out/golden/{name}.png', self.SIZE)
            self.assertEqual(one_x(self.root / f"out/t{'0000.00' if name == 'day' else '0030.00'}.png",
                                   self.SIZE).tobytes(), golden.tobytes(), name)
        hashes = {84: {(r['name'], r['sha256']) for r in records}}
        for horizon in (80, 88):
            seen = set()
            for attempt in range(2):
                with self.subTest(horizon=horizon, attempt=attempt):
                    result, records = self.render('--set', f'horizon={horizon}')
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    for r in records:
                        self.assertTrue(r['gate']['ok'], r['gate'])
                        self.assertEqual(r['knobs']['set'], {'horizon': horizon})
                        self.assertEqual(r['knobs']['merged'], {'horizon': horizon})
                        self.assertEqual(r['knobs']['sha256'], sha(json.dumps({'horizon': horizon}).encode()))
                    frames = self.frames()
                    self.assertEqual({(r['name'], r['sha256']) for r in records},
                                     {(name, sha(data)) for name, data in frames.items()})
                    with Image.open(self.root / 'out/t0000.00.png') as im:
                        self.assertEqual(im.size, (1920, 1080))
                    day = one_x(self.root / 'out/t0000.00.png', self.SIZE)
                    # The ground edge is drawn at the row the knob names, sky just above it.
                    self.assertEqual(day.getpixel((10, horizon)), G0)
                    self.assertEqual(day.getpixel((10, horizon - 1)), S2)
                    for name in ('day', 'night'):
                        golden = one_x(self.root / f'out/golden/{name}.png', self.SIZE)
                        self.assertNotEqual(one_x(self.root / f"out/t{'0000.00' if name == 'day' else '0030.00'}.png",
                                                  self.SIZE).tobytes(), golden.tobytes())
                    seen.add(frozenset((r['name'], r['sha256']) for r in records))
            self.assertEqual(len(seen), 1, 'a repeat render draws the same bytes')
            hashes[horizon] = set(next(iter(seen)))
        every = [h for pairs in hashes.values() for _, h in pairs]
        self.assertEqual(len(every), 6)
        self.assertEqual(len(set(every)), 6, 'every horizon draws different day and night frames')
        self.assertEqual(self.sources(SCENE_SOURCES), sources)
        run = json.loads((self.root / '.pixelate/runs.jsonl').read_text().splitlines()[-1])
        self.assertEqual(run['knobs']['set'], {'horizon': 88})
        tested = pixelate('library', '--library', str(self.library), 'test', self.PIECE)
        self.assertEqual(tested.returncode, 0, tested.stdout + tested.stderr)
        outputs = json.loads(tested.stdout)['pieces'][0]['outputs']
        self.assertEqual([(o['status'], o['golden']['ok'], o['gate_ok']) for o in outputs], [('passed', True, True)] * 2)

    def test_invalid_sets_exit_2_before_any_output_is_deleted(self):
        for sets, message in ((['horizon=86'], 'expected one of 80, 84, 88'),
                              (['horizon=084'], 'expected one of 80, 84, 88'),
                              (['horizon=88.0'], 'expected one of 80, 84, 88'),
                              (['horizon'], 'expected NAME=VALUE'),
                              (['season=winter'], 'no such knob; the piece declares horizon'),
                              (['horizon=80', 'horizon=88'], 'set more than once'),
                              (['horizon=88', 'season=winter'], 'no such knob')):
            with self.subTest(sets=sets):
                self.assert_refused_before_anything_runs(sets, message)

    def test_a_shot_given_a_file_of_the_wrong_type_fails_rather_than_draws(self):
        for content, message in (({'horizon': '88'}, 'knob horizon: "88" is not one of'),
                                 ({'horizon': 88.0}, 'knob horizon: 88.0 is not one of')):
            with self.subTest(content=content):
                env = dict(clean_env(), PIXELATE_KNOBS=str(self.knob_file(content)))
                result = pixelate('shot', '.', '0', '--out', 'shots', env=env, cwd=self.root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stdout + result.stderr)
                self.assertFalse((self.root / 'shots' / 't0000.00.png').exists())


class PackStarter(Copy):
    """starter-assets' `scale` knob, the pack.json export scale for one render."""
    PIECE = 'starter-assets'

    def exports(self):
        return {name: (self.root / 'out' / name).read_bytes() for name in ('atlas.png', 'atlas.json', 'contact.png')}

    def test_defaults_match_the_tracked_exports_and_scale_4_redraws_the_contact_sheet(self):
        tracked = self.exports()
        sources = self.sources(PACK_SOURCES)
        result, records = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.exports(), tracked, 'the defaults write the tracked exports byte for byte')
        self.assertEqual({r['name']: r['sha256'] for r in records},
                         {'atlas-image': sha(tracked['atlas.png']), 'atlas-data': sha(tracked['atlas.json']),
                          'contact-sheet': sha(tracked['contact.png'])})
        with Image.open(self.root / 'out' / 'contact.png') as im:
            self.assertEqual(im.size, (328, 172))
        seen = set()
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                result, records = self.render('--set', 'scale=4')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual({r['knobs']['merged']['scale'] for r in records}, {4})
                exports = self.exports()
                self.assertNotEqual(exports['contact.png'], tracked['contact.png'])
                with Image.open(self.root / 'out' / 'contact.png') as im:
                    self.assertEqual(im.size, (168, 108))
                with Image.open(self.root / 'out' / 'slot_a@4x.png') as im:
                    self.assertEqual(im.size, (8 * 4 * 4, 8 * 4))
                # The atlas is 1x: the knob does not change it, and nothing claims it does.
                self.assertEqual((exports['atlas.png'], exports['atlas.json']), (tracked['atlas.png'], tracked['atlas.json']))
                seen.add(sha(exports['contact.png']))
        self.assertEqual(len(seen), 1, 'a repeat render writes the same bytes')
        self.assertEqual(self.sources(PACK_SOURCES)['pack.json'], sources['pack.json'])
        self.assertEqual(json.loads((self.root / 'pack.json').read_text())['scale'], 8)
        self.assertEqual(self.sources(PACK_SOURCES)['piece.json'], sources['piece.json'])
        tested = pixelate('library', '--library', str(self.library), 'test', self.PIECE)
        self.assertEqual(tested.returncode, 0, tested.stdout + tested.stderr)
        self.assertTrue(all(o['status'] == 'passed' for o in json.loads(tested.stdout)['pieces'][0]['outputs']))

    def test_invalid_sets_exit_2_before_any_output_is_deleted(self):
        for sets, message in ((['scale=2'], 'expected one of 8, 4'), (['scale=08'], 'expected one of 8, 4'),
                              (['scale=4.0'], 'expected one of 8, 4'), (['palette=x.json'], 'no such knob'),
                              (['scale=4', 'scale=8'], 'set more than once'),
                              (['scale=4', 'name=x'], 'no such knob')):
            with self.subTest(sets=sets):
                self.assert_refused_before_anything_runs(sets, message)

    def assets(self, content, *args):
        env = dict(clean_env(), PIXELATE_KNOBS=str(self.knob_file(content))) if content is not None else clean_env()
        return pixelate('assets', '.', *args, env=env, cwd=self.root)

    def test_the_export_refuses_a_bad_file_a_scale_conflict_and_a_drifted_default(self):
        for content, message in (({'scale': 4.0}, 'knob scale: 4.0 is not one of [8, 4]'),
                                 ({'scale': '4'}, 'knob scale: "4" is not one of'),
                                 ({'name': 'x'}, 'no such knob name')):
            with self.subTest(content=content):
                result = self.assets(content)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
        result = self.assets({'scale': 4}, '--scale', '6')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--scale 6 and the scale knob both set the export scale', result.stderr)
        self.assertEqual(self.assets(None, '--scale', '6').returncode, 0)
        (self.root / 'pack.json').write_text((self.root / 'pack.json').read_text().replace('"scale": 8', '"scale": 6'))
        result = self.assets(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('knob scale: default 8 is not pack.json scale 6', result.stderr)
        (self.root / 'piece.json').unlink()
        result = self.assets({'scale': 4})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PIXELATE_KNOBS is set, but . has no piece.json', result.stderr)

    def test_an_explicit_export_scale_is_checked_before_anything_is_written(self):
        before = tree(self.root)
        for knob, scale, message in (({'scale': 4}, '0', '--scale must be an integer from 1 to 64, got 0'),
                                     (None, '0', '--scale must be an integer from 1 to 64, got 0'),
                                     (None, '-1', 'got -1'), ({'scale': 4}, '-1', 'got -1'),
                                     (None, '65', 'got 65'), (None, '2.5', "--scale must be an integer, got '2.5'"),
                                     (None, 'six', "--scale must be an integer, got 'six'"),
                                     (None, '', "--scale must be an integer, got ''")):
            with self.subTest(knob=knob, scale=scale):
                result = self.assets(knob, '--scale', scale)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(tree(self.root), before, 'a refused scale leaves sources and outputs as they were')
        with self.subTest(scale='missing'):
            result = self.assets(None, '--scale')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('--scale needs a value', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual(tree(self.root), before)

    def test_a_positive_explicit_export_scale_sets_the_scale_and_without_one_the_pack_default_applies(self):
        for scale in (1, 6, 64):
            with self.subTest(scale=scale):
                result = self.assets(None, '--scale', str(scale))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                with Image.open(self.root / 'out' / ('slot_a@%dx.png' % scale)) as im:
                    self.assertEqual(im.size, (8 * 4 * scale, 8 * scale))
        self.assertEqual(json.loads((self.root / 'pack.json').read_text())['scale'], 8)
        result = self.assets(None)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / 'out' / 'slot_a@8x.png').exists())


if __name__ == '__main__':
    unittest.main()
