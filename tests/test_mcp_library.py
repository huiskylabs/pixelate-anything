"""MCP tools for the library: find, remix, render, deliver and opt-in add (tools/mcp_server.py).

The mcp package is optional, so the server module is loaded against a fake one whose tool() keeps the
function and whose Image records what it was given. The tools run the real `pixelate` CLI in a
subprocess; fixture pieces are trusted code written by these tests, and one test remixes the first-party
starter-scene-still. `add_piece` is opt-in and only stages trusted local code, never PR code."""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import tracemalloc
import types
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
library = importlib.import_module('library')

PY = sys.executable
LIBRARY = REPO / 'library'


class FakeImage:
    def __init__(self, path=None, data=None, format=None):
        self.path, self.data, self.format = path, data, format


def load_server():
    """tools/mcp_server.py executed against a fake mcp; returns (module, {tool name: function})"""
    tools = {}

    class FakeServer:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self):
            def register(function):
                tools[function.__name__] = function
                return function
            return register
    fastmcp = types.ModuleType('mcp.server.fastmcp')
    vars(fastmcp).update(FastMCP=FakeServer, Image=FakeImage)
    with mock.patch.dict(sys.modules, {'mcp': types.ModuleType('mcp'), 'mcp.server': types.ModuleType('mcp.server'),
                                       'mcp.server.fastmcp': fastmcp}):
        spec = importlib.util.spec_from_file_location('mcp_server_library_under_test', REPO / 'tools' / 'mcp_server.py')
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module, tools


def tree(root):
    """{relative path: sha256} of every file under root, for proving nothing was written"""
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob('*')) if p.is_file()}


# A frame that passes the arcade gate; `dusk` darkens the sky and the seed moves the hero block.
DRAW = '''import sys
from PIL import Image
from piece import knobs
k = knobs()
sky = (4, 4, 12) if k.get('time') == 'dusk' else (8, 10, 18)
im = Image.new('RGB', (64, 48), sky)
im.paste((70, 40, 30), (0, 30, 64, 48))
for x in range(1, 64, 5):
    for y in range(32 + x % 3, 48, 4):
        im.paste((150, 120, 90) if (x + y) % 2 else (40, 90, 110), (x, y, x + 2, y + 2))
shift = k.get('seed', 3) % 8
im.paste((150, 120, 90), (24 + shift, 8, 40 + shift, 20))
im.paste((90, 60, 40), (26 + shift, 10, 38 + shift, 18))
im.resize((256, 192), Image.NEAREST).save('out/a.png')
'''
FLAT = '''from PIL import Image
Image.new('RGB', (256, 192), (255, 255, 255)).save('out/a.png')
'''
MANY = '''import pathlib
for i in range(40):
    pathlib.Path('out/part-%02d.txt' % i).write_text('part %d' % i)
'''
KNOBS = {'time': {'values': ['day', 'dusk'], 'default': 'day', 'edits': 'art/draw.py'},
         'seed': {'type': 'int', 'default': 3, 'edits': 'art/draw.py'}}


def make_piece(parent, piece_id='harbour', draw=DRAW, outputs=None, knobs=None):
    root = Path(parent) / piece_id
    for folder in ('art', 'out'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / 'art' / 'draw.py').write_text(draw, encoding='utf-8')
    (root / 'art' / 'many.py').write_text(MANY, encoding='utf-8')
    (root / 'brief.md').write_text('# Harbour\n\nA harbour wall at night.\n', encoding='utf-8')
    manifest = {'schema': 1, 'id': piece_id, 'title': 'Harbour', 'summary': 'A harbour wall at night.',
                'request': 'a harbour wall at night', 'status': 'starter', 'mode': 'scene', 'runtime': 'script',
                'tags': {'subject': ['harbour'], 'setting': ['night'], 'camera': 'side', 'style': 'arcade',
                         'era': 'none', 'motion': 'stills', 'sound': 'none'},
                'canvas': {'w': 64, 'h': 48, 'scale': 4},
                'outputs': outputs or [{'name': 'a', 'kind': 'image', 'run': f'{PY} art/draw.py', 'frame': 'out/a.png',
                                        'style': 'arcade', 'scale': 4, 'brief': 'brief.md'}],
                'anatomy': [{'file': 'art/draw.py', 'draws': 'everything', 'change_for': 'anything'}],
                'knobs': KNOBS if knobs is None else knobs,
                'provenance': {'made': '2026-10-18', 'by': 'tests/test_mcp_library.py'}, 'license': 'MIT'}
    (root / 'piece.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return root


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mcp, cls.tools = load_server()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name).resolve()
        for patcher in (mock.patch.object(self.mcp, 'WORK', self.work),
                        mock.patch.dict(os.environ, PATH=str(Path(PY).parent) + os.pathsep + os.environ['PATH'])):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.environ.pop('PIXELATE_KNOBS', None)
        os.environ.pop('PIXELATE_NO_LOG', None)

    def call(self, name, *args, **kwargs):
        """(summary dict, [Image, ...]) of a tool that returns the JSON text first"""
        result = self.tools[name](*args, **kwargs)
        self.assertIsInstance(result[0], str)
        return json.loads(result[0]), result[1:]


class Surface(Server):
    def test_the_loop_and_opt_in_add_are_exposed(self):
        for name in ('find_pieces', 'remix_piece', 'render_piece', 'deliver_piece', 'add_piece'):
            self.assertIn(name, self.tools)
        self.assertNotIn('critique', ' '.join(n for n in self.tools if n.endswith('_piece')))

    def test_add_refuses_without_explicit_trust_before_running_anything(self):
        with mock.patch.object(self.mcp, 'cli_full', side_effect=AssertionError('ran')):
            for trust in (False, None, 1, 'true'):
                with self.subTest(trust=trust), self.assertRaisesRegex(ValueError, 'trust_local_code=true'):
                    self.tools['add_piece']('harbour', trust_local_code=trust)

    def test_add_cannot_write_kit_catalog_from_an_ancestor_workspace(self):
        with mock.patch.object(self.mcp, 'WORK', REPO.parent), \
                mock.patch.object(self.mcp, 'cli_full', side_effect=AssertionError('ran')):
            with self.assertRaisesRegex(ValueError, 'kit root is the workspace'):
                self.tools['add_piece']('not-a-piece', library_dir=str(REPO / 'library'),
                                        trust_local_code=True)

    def test_add_stages_only_in_a_workspace_catalog_and_claims_no_review_or_rights(self):
        copied, _ = self.call('remix_piece', 'starter-scene-still', 'harbour', 'a harbour at dusk')
        self.assertTrue(copied['created'])
        catalog = self.work / 'library'
        catalog.mkdir()
        summary, images = self.call('add_piece', 'harbour', library_dir='library', trust_local_code=True)
        self.assertTrue(summary['ok'] and summary['created'])
        self.assertEqual((summary['renders'], summary['status_declared'], summary['gate_ok']), (2, 'study', True))
        self.assertEqual(images, [])
        self.assertTrue((catalog / 'harbour/out/golden/still.png').is_file())
        self.assertEqual(json.loads((catalog / 'index.json').read_text())['pieces'][0]['id'], 'harbour')
        self.assertIn('No independent art grade', summary['notice'])
        self.assertIn('Manual PR required', summary['notice'])
        with self.assertRaisesRegex(ValueError, 'workspace'):
            self.tools['add_piece']('harbour', library_dir=str(REPO / 'library'), trust_local_code=True)

    def test_mcp_instructions_route_to_the_same_remix_loop(self):
        instructions = self.mcp.INSTRUCTIONS
        self.assertLess(instructions.index('find_pieces(request)'), instructions.index('remix_piece copies'))
        self.assertLess(instructions.index('remix_piece copies'), instructions.index('render_piece;'))
        self.assertLess(instructions.index('render_piece;'), instructions.index('deliver_piece runs'))
        self.assertIn("guide('authoring')", instructions)
        self.assertIn('NO INDEPENDENT REVIEW', instructions)
        self.assertIn('NOT REVIEWED', instructions)
        self.assertIn('without a sandbox', instructions)
        self.assertIn('The ten steps', self.tools['guide']('authoring'))
        self.assertIn('`pixelate remix`', self.tools['guide']('remix'))


class Find(Server):
    def test_find_is_static_and_returns_checked_in_thumbnails(self):
        before = tree(LIBRARY)
        loaded = set(sys.modules)
        with mock.patch('subprocess.Popen', side_effect=AssertionError('find started a process')), \
                mock.patch('subprocess.run', side_effect=AssertionError('find started a process')), \
                mock.patch('os.system', side_effect=AssertionError('find started a process')):
            summary, images = self.call('find_pieces', 'a quarry machine boss breaks out of the water')
        self.assertEqual([m['id'] for m in summary['matches']],
                         [m['id'] for m in library.find(LIBRARY, 'a quarry machine boss breaks out of the water')['matches']])
        self.assertEqual(summary['matches'][0]['id'], 'quarry-wakes')
        self.assertEqual(tree(LIBRARY), before)
        self.assertFalse([name for name in set(sys.modules) - loaded
                          if str(getattr(sys.modules[name], '__file__', None) or '').startswith(str(LIBRARY))])
        top = summary['matches'][0]
        self.assertEqual(top['thumbnail_image'], 1)
        self.assertEqual(images[0].format, 'png')
        self.assertEqual(images[0].data, (LIBRARY / 'quarry-wakes' / 'media' / 'thumb.png').read_bytes())
        for key in ('title', 'summary', 'tags', 'canvas', 'knobs', 'anatomy', 'status'):
            self.assertIn(key, top)
        self.assertEqual(len(images), sum(m['thumbnail_image'] is not None for m in summary['matches'])
                         + sum(s['thumbnail_image'] is not None for s in summary['fallback'].get('starters', [])))

    def test_no_close_piece_returns_starters_with_their_thumbnails(self):
        summary, images = self.call('find_pieces', 'zzzzqx unknowable request')
        self.assertEqual(summary['matches'], [])
        self.assertEqual(summary['fallback']['kind'], 'starter')
        self.assertTrue(summary['fallback']['starters'])
        self.assertEqual(len(images), len(summary['fallback']['starters']))
        self.assertTrue(all(s['status'] == 'starter' for s in summary['fallback']['starters']))

    def test_a_mode_outside_the_vocabulary_is_refused(self):
        with self.assertRaises(ValueError):
            self.tools['find_pieces']('a harbour', mode='painting')

    def test_a_linked_or_oversized_or_broken_thumbnail_has_no_image(self):
        library_root = self.work / 'lib'
        (library_root / 'harbour' / 'media').mkdir(parents=True)
        piece = {'id': 'harbour', 'media': {'thumb': 'media/thumb.png'}}
        thumb = library_root / 'harbour' / 'media' / 'thumb.png'
        outside = self.work / 'outside.png'
        shutil.copy(LIBRARY / 'quarry-wakes' / 'media' / 'thumb.png', outside)
        with mock.patch.object(self.mcp, 'LIBRARY', library_root):
            self.assertIsNone(self.mcp.library_thumb(piece))  # missing
            thumb.symlink_to(outside)
            self.assertIsNone(self.mcp.library_thumb(piece))  # link
            thumb.unlink()
            thumb.write_bytes(b'not a png')
            self.assertIsNone(self.mcp.library_thumb(piece))  # does not decode
            shutil.copy(outside, thumb)
            self.assertEqual(self.mcp.library_thumb(piece).data, outside.read_bytes())
            with mock.patch.object(self.mcp, 'MAX_THUMB_BYTES', 10):
                self.assertIsNone(self.mcp.library_thumb(piece))  # too large

    def test_a_sparse_oversized_thumbnail_is_refused_without_reading_it(self):
        library_root = self.work / 'lib'
        (library_root / 'harbour' / 'media').mkdir(parents=True)
        piece = {'id': 'harbour', 'media': {'thumb': 'media/thumb.png'}}
        with (library_root / 'harbour' / 'media' / 'thumb.png').open('wb') as fh:
            fh.truncate(self.mcp.MAX_THUMB_BYTES * 64)
        self.assertEqual(self.mcp.MAX_THUMB_BYTES, 2 * 1024 * 1024)
        with mock.patch.object(self.mcp, 'LIBRARY', library_root):
            tracemalloc.start()
            try:
                self.assertIsNone(self.mcp.library_thumb(piece))
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
        self.assertLess(peak, self.mcp.MAX_THUMB_BYTES // 2)

    def test_a_pipe_as_thumbnail_has_no_image_and_does_not_block(self):
        library_root = self.work / 'lib'
        (library_root / 'harbour' / 'media').mkdir(parents=True)
        os.mkfifo(library_root / 'harbour' / 'media' / 'thumb.png')
        with mock.patch.object(self.mcp, 'LIBRARY', library_root):
            self.assertIsNone(self.mcp.library_thumb({'id': 'harbour', 'media': {'thumb': 'media/thumb.png'}}))


class Remix(Server):
    def test_remix_of_a_trusted_starter_makes_a_copy_in_the_workspace(self):
        before = tree(LIBRARY)
        summary, images = self.call('remix_piece', 'starter-scene-still', 'work/temple', 'a temple under a jungle')
        dest = self.work / 'work' / 'temple'
        self.assertTrue(summary['created'] and summary['ok'])
        self.assertEqual((summary['piece_id'], summary['base'], summary['copy_status'], summary['reviewed']),
                         ('temple', 'starter-scene-still', 'starter', False))
        self.assertEqual(images, [])
        self.assertTrue((dest / 'REMIX.md').is_file())
        manifest = json.loads((dest / 'piece.json').read_text(encoding='utf-8'))
        self.assertEqual((manifest['id'], manifest['request'], manifest['lineage']),
                         ('temple', 'a temple under a jungle', {'remixed_from': 'starter-scene-still'}))
        self.assertTrue((dest / '.pixelate' / 'remix-baseline.json').is_file())
        self.assertEqual(summary['outputs'][0]['status'], 'passed')
        self.assertIn('no sandbox', summary['warning'])
        self.assertIn('not art quality', summary['notice'])
        self.assertEqual(tree(LIBRARY), before)

    def test_skipped_audio_and_exports_are_reported_untested(self):
        baseline = {'piece': 'night-mix', 'status': 'study', 'quick': True, 'base': {'id': 'starter-music', 'status': 'starter'},
                    'test': {'gate_ok': True, 'outputs': [
                        {'name': 'equaliser', 'kind': 'image', 'tested': True, 'status': 'passed', 'gate_ok': True},
                        {'name': 'soundtrack', 'kind': 'audio', 'tested': False, 'status': 'skipped',
                         'reason': 'quick mode skips audio outputs'}]},
                    'untested': [{'name': 'soundtrack', 'kind': 'audio', 'reason': 'quick mode skips audio outputs'}]}
        with mock.patch.object(self.mcp, 'cli_full', return_value=(0, json.dumps(baseline), '')):
            summary, _ = self.call('remix_piece', 'starter-music', 'night-mix', 'a night mix')
        self.assertTrue(summary['quick_baseline'])
        self.assertEqual(summary['not_tested'], ['audio soundtrack: quick mode skips audio outputs'])
        sound = next(o for o in summary['outputs'] if o['name'] == 'soundtrack')
        self.assertFalse(sound['tested'])
        self.assertIn('untested', sound['result'])

    def test_a_failed_baseline_reports_that_nothing_was_created(self):
        baseline = {'piece': 'bad', 'status': 'study', 'quick': True, 'base': {'id': 'x', 'status': 'study'},
                    'test': {'gate_ok': False, 'outputs': [{'name': 'a', 'kind': 'image', 'tested': True,
                                                            'status': 'failed', 'error': 'run failed'}]},
                    'untested': []}
        with mock.patch.object(self.mcp, 'cli_full', return_value=(1, json.dumps(baseline), 'remix: did not pass')):
            summary, _ = self.call('remix_piece', 'quarry-wakes', 'bad', 'a request')
        self.assertFalse(summary['created'] or summary['ok'])
        self.assertIsNone(summary['copy_status'])
        self.assertIn('nothing was created', summary['next'])
        self.assertIn('FAILED', summary['outputs'][0]['result'])

    def test_unknown_piece_is_refused_with_the_cli_message(self):
        summary, _ = self.call('remix_piece', 'no-such-piece', 'copy', 'a request')
        self.assertFalse(summary['created'])
        self.assertIn('unknown piece', summary['stderr'])
        self.assertFalse((self.work / 'copy').exists())

    def test_destinations_outside_the_workspace_are_refused(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, True)
        (self.work / 'escape').symlink_to(outside)
        for dest in ('../escape', str(outside / 'copy'), 'escape/copy', '.', str(self.work),
                     str(LIBRARY / 'copy')):
            with self.subTest(dest=dest), mock.patch.object(self.mcp, 'cli_full', side_effect=AssertionError('ran')):
                with self.assertRaises(ValueError):
                    self.tools['remix_piece']('starter-scene-still', dest, 'a request')
        self.assertEqual(list(outside.iterdir()), [])

    def test_a_destination_inside_the_kit_library_is_refused_even_when_the_workspace_is_the_kit(self):
        before = tree(LIBRARY)
        with mock.patch.object(self.mcp, 'WORK', REPO):
            with self.assertRaises(ValueError):
                self.tools['remix_piece']('starter-scene-still', 'library/copy', 'a request')
        self.assertEqual(tree(LIBRARY), before)


class Render(Server):
    def render(self, *args, **kwargs):
        return self.call('render_piece', *args, **kwargs)

    def test_render_returns_snapshot_gate_and_the_current_frame(self):
        root = make_piece(self.work)
        summary, images = self.render('harbour')
        (out,) = summary['outputs']
        frame = (root / 'out' / 'a.png').read_bytes()
        self.assertTrue(summary['ok'])
        self.assertEqual((out['ran'], out['gate']['ok'], out['sha256']), (True, True, hashlib.sha256(frame).hexdigest()))
        self.assertTrue(out['snapshot'].startswith('.pixelate/snapshots/'))
        self.assertEqual(out['preview_image'], 1)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].data, frame)
        self.assertIn('no sandbox', summary['warning'])
        self.assertIn('not art quality', summary['notice'])
        self.assertNotIn('critique', out)
        self.assertEqual(json.loads((root / 'render-report.json').read_text(encoding='utf-8'))[0]['sha256'], out['sha256'])

    def test_set_changes_the_output_and_forwards_typed_strings(self):
        root = make_piece(self.work)
        default, default_images = self.render('harbour')
        variant, images = self.render('harbour', sets=['time=dusk', 'seed=4'])
        self.assertTrue(variant['ok'])
        self.assertEqual(variant['knobs']['set'], {'time': 'dusk', 'seed': 4})
        self.assertEqual(variant['knobs']['merged'], {'time': 'dusk', 'seed': 4})
        self.assertNotEqual(variant['outputs'][0]['sha256'], default['outputs'][0]['sha256'])
        self.assertEqual(images[0].data, (root / 'out' / 'a.png').read_bytes())
        self.assertNotEqual(images[0].data, default_images[0].data)
        self.assertIsNone(default['knobs'])

    def test_set_values_are_arguments_never_shell_text(self):
        make_piece(self.work)
        marker = self.work / 'pwned'
        for value in (f'time=$(touch {marker})', f'time=dusk; touch {marker}', f'time=`touch {marker}`', 'time=-x'):
            with self.subTest(value=value):
                summary, images = self.render('harbour', sets=[value])
                self.assertFalse(summary['ok'])
                self.assertEqual(images, [])
                self.assertIn('expected one of', summary['stderr'])
        self.assertFalse(marker.exists())

    def test_bad_sets_are_refused_before_anything_runs(self):
        make_piece(self.work)
        for sets in ('time=dusk', ['time'], [3], ['time=dusk\0x'], ['seed=1'] * 65):
            with self.subTest(sets=sets), mock.patch.object(self.mcp, 'cli_full', side_effect=AssertionError('ran')):
                with self.assertRaises(ValueError):
                    self.tools['render_piece']('harbour', sets=sets)

    def test_an_unknown_knob_is_a_refusal_with_no_preview(self):
        make_piece(self.work)
        summary, images = self.render('harbour', sets=['mood=grim'])
        self.assertFalse(summary['ok'])
        self.assertEqual(images, [])
        self.assertIn('no such knob', summary['stderr'])
        self.assertFalse((self.work / 'harbour' / 'render-report.json').exists())

    def test_a_failed_command_leaves_no_stale_preview(self):
        root = make_piece(self.work)
        self.assertEqual(len(self.render('harbour')[1]), 1)
        self.assertTrue((root / 'out' / 'a.png').is_file())  # a good frame is on disk from the first render
        manifest = json.loads((root / 'piece.json').read_text(encoding='utf-8'))
        manifest['outputs'][0]['run'] = f'{PY} -c "raise SystemExit(3)"'
        (root / 'piece.json').write_text(json.dumps(manifest), encoding='utf-8')
        summary, images = self.render('harbour')
        (out,) = summary['outputs']
        self.assertFalse(summary['ok'])
        self.assertFalse(out['ran'])
        self.assertIsNone(out['preview_image'])
        self.assertEqual(images, [])

    def test_a_command_that_writes_nothing_or_a_link_gets_no_preview(self):
        root = make_piece(self.work)
        self.render('harbour')
        manifest = json.loads((root / 'piece.json').read_text(encoding='utf-8'))
        for command in (f'{PY} -c "pass"',
                        f'{PY} -c "import os; os.symlink(\'../art/draw.py\', \'out/a.png\')"'):
            with self.subTest(command=command):
                manifest['outputs'][0]['run'] = command
                (root / 'piece.json').write_text(json.dumps(manifest), encoding='utf-8')
                summary, images = self.render('harbour')
                self.assertFalse(summary['ok'])
                self.assertIn('error', summary['outputs'][0])
                self.assertEqual(images, [])

    def test_a_failed_gate_is_reported_and_its_current_frame_still_shown(self):
        root = make_piece(self.work, draw=FLAT)
        summary, images = self.render('harbour')
        self.assertFalse(summary['ok'])
        self.assertFalse(summary['outputs'][0]['gate']['ok'])
        self.assertTrue(summary['outputs'][0]['gate']['fail'])
        self.assertEqual([i.data for i in images], [(root / 'out' / 'a.png').read_bytes()])

    def test_a_preview_needs_the_exact_recorded_bytes_and_no_link(self):
        root = make_piece(self.work)
        self.render('harbour')
        frame = root / 'out' / 'a.png'
        digest = hashlib.sha256(frame.read_bytes()).hexdigest()
        self.assertIsNotNone(self.mcp.verified_preview(root, 'out/a.png', digest))
        self.assertIsNone(self.mcp.verified_preview(root, 'out/a.png', '0' * 64))
        self.assertIsNone(self.mcp.verified_preview(root, 'out/a.png', None))
        self.assertIsNone(self.mcp.verified_preview(root, 'out/missing.png', digest))
        other = self.work / 'other.png'
        other.write_bytes(frame.read_bytes())
        (root / 'out' / 'link.png').symlink_to(other)
        self.assertIsNone(self.mcp.verified_preview(root, 'out/link.png', digest))
        (root / 'linked').symlink_to(self.work)
        self.assertIsNone(self.mcp.verified_preview(root, 'linked/other.png', digest))

    def test_a_sparse_oversized_frame_has_no_preview_and_is_never_read_whole(self):
        root = make_piece(self.work)
        frame = root / 'out' / 'a.png'
        with frame.open('wb') as fh:
            fh.truncate(self.mcp.MAX_PREVIEW_BYTES + 1)
        self.assertEqual(self.mcp.MAX_PREVIEW_BYTES, 32 * 1024 * 1024)
        digest = hashlib.sha256(frame.read_bytes()).hexdigest()
        tracemalloc.start()
        try:
            self.assertIsNone(self.mcp.verified_preview(root, 'out/a.png', digest))
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 4 * 1024 * 1024)

    def test_a_file_that_grows_after_its_size_check_is_cut_off_at_the_cap(self):
        root = make_piece(self.work)
        frame = root / 'out' / 'a.png'
        frame.write_bytes(b'x' * 100)
        real_fstat = os.fstat

        def small(fd):
            info = real_fstat(fd)
            return types.SimpleNamespace(st_mode=info.st_mode, st_size=0)
        with mock.patch.object(self.mcp.os, 'fstat', small):
            with self.assertRaises(ValueError):
                self.mcp.read_capped(root, 'out/a.png', 10)
            self.assertEqual(self.mcp.read_capped(root, 'out/a.png', 100), b'x' * 100)
            self.assertIsNone(self.mcp.verified_preview(root, 'out/a.png', hashlib.sha256(b'x' * 100).hexdigest()))

    def test_a_pipe_as_frame_has_no_preview_and_does_not_block(self):
        root = make_piece(self.work)
        os.mkfifo(root / 'out' / 'a.png')
        self.assertIsNone(self.mcp.verified_preview(root, 'out/a.png', '0' * 64))

    def test_oversized_json_report_stays_intact(self):
        outputs = [{'name': 'a', 'kind': 'image', 'run': f'{PY} art/draw.py', 'frame': 'out/a.png', 'style': 'arcade',
                    'scale': 4, 'brief': 'brief.md'}]
        outputs += [{'name': 'part-%02d' % i, 'kind': 'export', 'run': f'{PY} art/many.py',
                     'file': 'out/part-%02d.txt' % i} for i in range(40)]
        make_piece(self.work, outputs=outputs)
        code, out, _ = self.mcp.cli_full('render', self.work / 'harbour', '--json')
        self.assertEqual(code, 0)
        self.assertGreater(len(out), 6000)  # more than cli() would have kept
        self.assertEqual(len(json.loads(out)), 41)
        summary, images = self.render('harbour')
        self.assertTrue(summary['ok'])
        self.assertEqual([o['name'] for o in summary['outputs']], ['a'] + ['part-%02d' % i for i in range(40)])
        self.assertEqual(len(images), 1)

    def test_a_command_over_the_timeout_is_killed_and_reported(self):
        root = make_piece(self.work)
        manifest = json.loads((root / 'piece.json').read_text(encoding='utf-8'))
        manifest['outputs'][0]['run'] = f'{PY} -c "import time; time.sleep(60)"'
        (root / 'piece.json').write_text(json.dumps(manifest), encoding='utf-8')
        summary, images = self.render('harbour', timeout=2)
        self.assertFalse(summary['ok'])
        self.assertIn('timed out', summary['error'])
        self.assertEqual(images, [])

    def test_folders_outside_the_workspace_or_inside_the_library_are_refused(self):
        make_piece(self.work)
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, True)
        make_piece(outside)
        (self.work / 'linked').symlink_to(outside / 'harbour')
        before = tree(LIBRARY)
        for path in ('../harbour', str(outside / 'harbour'), 'linked', 'missing', '.', 'harbour/art'):
            with self.subTest(path=path), mock.patch.object(self.mcp, 'cli_full', side_effect=AssertionError('ran')):
                with self.assertRaises(ValueError):
                    self.tools['render_piece'](path)
        with mock.patch.object(self.mcp, 'WORK', REPO):
            for tool in ('render_piece', 'deliver_piece'):
                with self.assertRaises(ValueError):
                    self.tools[tool]('library/starter-scene-still')
        self.assertEqual(tree(LIBRARY), before)
        self.assertFalse((outside / 'harbour' / 'render-report.json').exists())

    def test_render_with_image_renders_only_that_output(self):
        outputs = [{'name': 'a', 'kind': 'image', 'run': f'{PY} art/draw.py', 'frame': 'out/a.png', 'style': 'arcade',
                    'scale': 4, 'brief': 'brief.md'},
                   {'name': 'part', 'kind': 'export', 'run': f'{PY} art/many.py', 'file': 'out/part-00.txt'}]
        make_piece(self.work, outputs=outputs)
        summary, _ = self.render('harbour', image='part')
        self.assertEqual([o['name'] for o in summary['outputs']], ['part'])
        self.assertTrue(summary['ok'])


class Deliver(Server):
    def deliver(self, *args, **kwargs):
        return self.call('deliver_piece', *args, **kwargs)

    def declare_approver(self, root):
        (root / 'media').mkdir(exist_ok=True)
        (root / 'history').mkdir(exist_ok=True)
        (root / 'media' / 'thumb.png').write_bytes(b'fixture media')
        (root / 'media' / 'contact.png').write_bytes(b'fixture media')
        (root / 'history' / 'notes.md').write_text('The user said they like it.\n', encoding='utf-8')
        manifest = json.loads((root / 'piece.json').read_text(encoding='utf-8'))
        manifest.update(status='accepted', media={'thumb': 'media/thumb.png', 'contact': 'media/contact.png'},
                        review={'notes': 'history/notes.md', 'approved_by': 'user', 'record': None})
        (root / 'piece.json').write_text(json.dumps(manifest), encoding='utf-8')

    def test_deliver_packages_verifies_and_claims_no_art_approval(self):
        root = make_piece(self.work)
        self.declare_approver(root)
        summary, images = self.deliver('harbour', sets=['time=dusk'])
        package = root / 'dist' / 'delivery'
        self.assertTrue(summary['ok'] and summary['delivered'])
        self.assertTrue((package / 'DELIVERY.md').is_file())
        self.assertEqual(summary['package'], str(package))
        self.assertEqual(summary['knobs']['set'], {'time': 'dusk'})
        packaged = (package / 'out' / 'a.png').read_bytes()
        self.assertEqual([i.data for i in images], [packaged])
        self.assertEqual(summary['outputs'][0]['preview_image'], 1)
        self.assertEqual(summary['outputs'][0]['sha256'], hashlib.sha256(packaged).hexdigest())
        evidence = summary['evidence']
        self.assertEqual(evidence['critique'], 'NOT REVIEWED')
        self.assertEqual(evidence['approval'], {'declared_by': 'user', 'notes': 'history/notes.md', 'verified': False})
        self.assertIn('not verified', evidence['rights'])
        self.assertIn('legal, not good', evidence['gate'])
        self.assertEqual(evidence['paid_critique'], 'not run by deliver')
        self.assertTrue(summary['not_tested'])
        self.assertIn('does not mean the user approved the art', summary['notice'])
        self.assertIn('no critique or rating was run', summary['notice'].lower())
        verified, no_images = self.deliver('harbour', verify=True)
        self.assertTrue(verified['verified'])
        self.assertEqual(verified['fingerprint'], summary['fingerprint'])
        self.assertEqual(no_images, [])
        self.assertIn('ran no piece code', verified['notice'])
        self.assertIn('not art quality', verified['notice'])
        (package / 'out' / 'a.png').write_bytes(b'tampered')
        broken, _ = self.deliver('harbour', verify=True)
        self.assertFalse(broken['verified'] or broken['ok'])
        self.assertTrue([c for c in broken['checks'] if not c['ok']])

    def test_mcp_remix_render_and_delivery_expose_distance_warning(self):
        copied, _ = self.call('remix_piece', 'starter-scene-still', 'harbour', 'a harbour at dusk')
        self.assertTrue(copied['created'])
        rendered, _ = self.call('render_piece', 'harbour')
        self.assertTrue(rendered['ok'])
        distance = rendered['outputs'][0]['distance']
        self.assertTrue(distance['under_remixed'])
        self.assertIn('under-remixed', distance['warning'])
        self.assertEqual(len(distance['baseline_sha256']), 64)
        delivered, _ = self.deliver('harbour')
        self.assertTrue(delivered['ok'])
        self.assertEqual(delivered['outputs'][0]['distance'], distance)
        self.assertEqual(delivered['evidence']['critique'], 'NOT REVIEWED')

    def test_verify_runs_nothing_and_takes_no_sets(self):
        root = make_piece(self.work)
        self.deliver('harbour')
        marker = self.work / 'ran'
        manifest = json.loads((root / 'piece.json').read_text(encoding='utf-8'))
        manifest['outputs'][0]['run'] = f'{PY} -c "open({str(marker)!r}, \'w\')"'
        (root / 'piece.json').write_text(json.dumps(manifest), encoding='utf-8')
        summary, _ = self.deliver('harbour', verify=True)
        self.assertFalse(marker.exists())
        self.assertFalse(summary['verified'])  # the changed manifest no longer matches the delivered one
        with self.assertRaises(ValueError):
            self.tools['deliver_piece']('harbour', sets=['time=dusk'], verify=True)

    def test_a_failed_gate_delivers_nothing_and_shows_no_image(self):
        root = make_piece(self.work, draw=FLAT)
        summary, images = self.deliver('harbour')
        self.assertFalse(summary['ok'] or summary['delivered'])
        self.assertTrue(summary['errors'])
        self.assertIsNone(summary['package'])
        self.assertEqual(images, [])
        self.assertFalse((root / 'dist').exists())

    def test_a_refused_set_is_reported_and_nothing_is_packaged(self):
        root = make_piece(self.work)
        summary, images = self.deliver('harbour', sets=['time=midnight'])
        self.assertFalse(summary['delivered'])
        self.assertTrue(summary['refused'])
        self.assertIn('expected one of', ' '.join(summary['errors']))
        self.assertEqual(images, [])
        self.assertFalse((root / 'dist').exists())

    def test_an_earlier_package_is_not_previewed_after_a_failed_delivery(self):
        root = make_piece(self.work)
        self.assertEqual(len(self.deliver('harbour')[1]), 1)
        (root / 'art' / 'draw.py').write_text(FLAT, encoding='utf-8')
        summary, images = self.deliver('harbour')
        self.assertFalse(summary['delivered'])
        self.assertEqual(images, [])
        self.assertIn('earlier package was left', summary['note'])

    def test_oversized_delivery_report_stays_intact(self):
        outputs = [{'name': 'a', 'kind': 'image', 'run': f'{PY} art/draw.py', 'frame': 'out/a.png', 'style': 'arcade',
                    'scale': 4, 'brief': 'brief.md'}]
        outputs += [{'name': 'part-%02d' % i, 'kind': 'export', 'run': f'{PY} art/many.py',
                     'file': 'out/part-%02d.txt' % i} for i in range(40)]
        make_piece(self.work, outputs=outputs)
        code, out, _ = self.mcp.cli_full('deliver', self.work / 'harbour', '--json')
        self.assertEqual(code, 0)
        self.assertGreater(len(out), 6000)
        self.assertEqual(len(json.loads(out)['outputs']), 41)
        summary, images = self.deliver('harbour')
        self.assertTrue(summary['delivered'])
        self.assertEqual(len(summary['outputs']), 41)
        self.assertEqual(len(images), 1)

    def test_a_bad_timeout_is_refused(self):
        make_piece(self.work)
        for timeout in (0, -1, True, 1.5):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.tools['deliver_piece']('harbour', timeout=timeout)


if __name__ == '__main__':
    unittest.main()
