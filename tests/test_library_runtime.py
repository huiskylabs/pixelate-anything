"""`pixelate find`, `pixelate library` and `pixelate render` on synthetic pieces; trusted fixture code only."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, PngImagePlugin

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / 'tools'
spec = importlib.util.spec_from_file_location('piece_library', TOOLS / 'library.py')
assert spec is not None and spec.loader is not None
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)
sys.path.insert(0, str(TOOLS))
import render  # noqa: E402  the module library.kit_render() imports

# Imports kit modules without a hard-coded kit path: render and test put kit tools/ on PYTHONPATH.
# The frame passes the arcade gate: a dark night, a lit block and a foreground of scattered stones.
DRAW = '''import sys
import colorlib
from PIL import Image
im = Image.new('RGB', (64, 48), (8, 10, 18))
im.paste((70, 40, 30), (0, 30, 64, 48))
for x in range(1, 64, 5):
    for y in range(32 + x % 3, 48, 4):
        im.paste((150, 120, 90) if (x + y) % 2 else (40, 90, 110), (x, y, x + 2, y + 2))
im.paste((150, 120, 90), (24, 8, 40, 20))
im.paste((90, 60, 40), (26, 10, 38, 18))
assert colorlib
im.save('out/a@1x.png')
im.resize((256, 192), Image.NEAREST).save('out/a.png')
'''
# A 256x240 frame of thousands of colours: no NES screen, palette or tile budget allows it.
NES_ILLEGAL = '''from PIL import Image
im = Image.new('RGB', (256, 240))
im.putdata([((x * 7) % 256, (y * 5) % 256, (x * y) % 256) for y in range(240) for x in range(256)])
im.save('out/a.png')
'''
# A 160x144 frame in the four Game Boy shades with four unique tiles: legal for that era.
GAMEBOY_LEGAL = '''from PIL import Image
im = Image.new('RGB', (160, 144), (155, 188, 15))
im.paste((15, 56, 15), (0, 112, 160, 144))
im.paste((48, 98, 48), (40, 40, 72, 112))
im.paste((103, 142, 35), (48, 48, 64, 64))
im.save('out/a.png')
'''
SOUND = '''import pathlib
pathlib.Path('sound/tone.wav').write_bytes(b'RIFF fixture audio')
'''


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def make_piece(library_root, piece_id='harbour'):
    """A study piece whose image renders at 4x, with a tracked 1x golden, an audio and an export output."""
    root = Path(library_root) / piece_id
    for folder in ('art', 'sound', 'out/golden'):
        (root / folder).mkdir(parents=True)
    (root / 'art' / 'draw.py').write_text(DRAW, encoding='utf-8')
    (root / 'sound' / 'make.py').write_text(SOUND, encoding='utf-8')
    subprocess.run([sys.executable, 'art/draw.py'], cwd=root, check=True, env={'PYTHONPATH': str(TOOLS)})
    (root / 'out' / 'a@1x.png').rename(root / 'out' / 'golden' / 'a.png')
    (root / 'sound' / 'tone.wav').write_bytes(b'stale committed audio')
    (root / 'out' / 'version.txt').write_text('stale committed export', encoding='utf-8')
    data = {'schema': 1, 'id': piece_id, 'title': 'Harbour', 'summary': 'A harbour wall at night.',
            'request': 'a harbour wall at night', 'status': 'study', 'mode': 'scene', 'runtime': 'script',
            'tags': {'subject': ['harbour', 'wall'], 'setting': ['night'], 'camera': 'side', 'style': 'arcade',
                     'era': 'none', 'motion': 'stills', 'sound': 'sfx'},
            'canvas': {'w': 64, 'h': 48, 'scale': 4},
            'outputs': [{'name': 'a', 'kind': 'image', 'run': f'{sys.executable} art/draw.py', 'frame': 'out/a.png',
                         'golden': 'out/golden/a.png', 'style': 'arcade', 'scale': 4},
                        {'name': 'tone', 'kind': 'audio', 'run': f'{sys.executable} sound/make.py',
                         'file': 'sound/tone.wav'},
                        {'name': 'version', 'kind': 'export', 'run': 'pixelate --version > out/version.txt',
                         'file': 'out/version.txt'}],
            'anatomy': [{'file': 'art/draw.py', 'draws': 'the harbour wall', 'change_for': 'the setting'}],
            'knobs': {}, 'provenance': {'made': '2026-10-18', 'by': 'fixture author'}, 'license': 'MIT'}
    save(root, data)
    return root, data


def make_era_piece(library_root, era, draw, size):
    """An accepted era piece: one 1x image gated by `--era` alone, its golden the frame its command draws."""
    root = Path(library_root) / f'{era}-screen'
    for folder in ('art', 'media', 'out/golden'):
        (root / folder).mkdir(parents=True)
    (root / 'art' / 'draw.py').write_text(draw, encoding='utf-8')
    subprocess.run([sys.executable, 'art/draw.py'], cwd=root, check=True)
    shutil.copy(root / 'out' / 'a.png', root / 'out' / 'golden' / 'a.png')
    for path in ('media/thumb.png', 'media/contact.png', 'notes.md'):
        (root / path).write_bytes(b'fixture')
    w, h = size
    data = {'schema': 1, 'id': root.name, 'title': 'Screen', 'summary': 'A console screen.',
            'request': f'a {era} screen', 'status': 'accepted', 'mode': 'era', 'runtime': 'script',
            'tags': {'subject': ['screen'], 'setting': ['night'], 'camera': 'none', 'style': 'none',
                     'era': era, 'motion': 'stills', 'sound': 'none'},
            'canvas': {'w': w, 'h': h, 'scale': 1},
            'outputs': [{'name': 'a', 'kind': 'image', 'run': f'{sys.executable} art/draw.py', 'frame': 'out/a.png',
                         'golden': 'out/golden/a.png', 'era': era}],
            'anatomy': [{'file': 'art/draw.py', 'draws': 'the screen', 'change_for': 'the screen'}],
            'knobs': {name: {'type': 'int', 'default': 1, 'edits': 'art/draw.py'} for name in ('seed', 'size')},
            'provenance': {'made': '2026-10-18', 'by': 'fixture author'},
            'media': {'thumb': 'media/thumb.png', 'contact': 'media/contact.png'},
            'review': {'notes': 'notes.md', 'approved_by': 'user', 'record': None}, 'license': 'MIT'}
    save(root, data)
    return root, data


def png(color, size=(256, 192)):
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, format='PNG')
    return buffer.getvalue()


def sha(data):
    return hashlib.sha256(data).hexdigest()


@contextlib.contextmanager
def lingering_writer(root, rel, data):
    """Patch render.read_regular so that right after the first read of rel under root, a process the
    run left behind replaces rel with data. Yields the list of reads of rel."""
    real = render.read_regular
    reads = []
    def read(base, path):
        content = real(base, path)
        if Path(base) == root and path == rel:
            reads.append(path)
            if len(reads) == 1:
                (root / rel).write_bytes(data)
        return content
    with mock.patch.object(render, 'read_regular', read):
        yield reads


@contextlib.contextmanager
def gated_frames():
    """Patch render.technical_gate to record the hash of the frame each gate run reads."""
    real = render.technical_gate
    hashes = []
    def gate(folder, im):
        hashes.append(sha((Path(folder) / im['frame']).read_bytes()))
        return real(folder, im)
    with mock.patch.object(render, 'technical_gate', gate):
        yield hashes


def write_canary(frame, path):
    """Copy frame's pixels to path with different bytes; following a link to it would pass every check."""
    info = PngImagePlugin.PngInfo()
    info.add_text('canary', 'outside the piece')
    with Image.open(frame) as image:
        image.save(path, pnginfo=info)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(root, data):
    (root / 'piece.json').write_text(json.dumps(data), encoding='utf-8')


def pixelate(*args, cwd=None, env=None):
    return subprocess.run([sys.executable, str(REPO / 'pixelate'), *args], capture_output=True, text=True, cwd=cwd,
                          env=env)


def caller_env(kit=None):
    """The caller's environment with PIXELATE_KIT unset, or set to kit (a wrong value)."""
    env = {key: value for key, value in os.environ.items() if key != 'PIXELATE_KIT'}
    if kit is not None:
        env['PIXELATE_KIT'] = kit
    return env


class Fixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.library = Path(temp.name) / 'library'
        self.library.mkdir()
        self.piece, self.data = make_piece(self.library)

    def library_test(self, *args):
        result = pixelate('library', '--library', str(self.library), 'test', *args)
        report = json.loads(result.stdout) if result.stdout else {}
        return result, report

    def outputs(self, report):
        return {o['name']: o for o in report['pieces'][0]['outputs']}


class StaticCommands(Fixture):
    def test_find_list_show_index_never_run_piece_commands(self):
        for output in self.data['outputs']:
            output['run'] = 'touch EXECUTED; ' + output['run']
        save(self.piece, self.data)
        before = snapshot(self.piece)
        found = pixelate('find', 'a harbour wall in the rain', '--library', str(self.library))
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertIn('1. harbour (study, score', found.stdout)
        self.assertIn('differs: unmatched term: rain', found.stdout)
        self.assertIn('fallback: no matching starter; author a new piece', found.stdout)
        as_json = json.loads(pixelate('find', 'harbour', '--json', '--library', str(self.library)).stdout)
        self.assertEqual(as_json['matches'][0]['id'], 'harbour')
        none = pixelate('find', 'jellyfish nebula', '--library', str(self.library))
        self.assertIn('no close piece', none.stdout)
        listed = pixelate('library', '--library', str(self.library), 'list')
        self.assertEqual(json.loads(listed.stdout), [{'id': 'harbour', 'title': 'Harbour', 'mode': 'scene',
                                                       'status': 'study'}])
        shown = pixelate('library', '--library', str(self.library), 'show', 'harbour')
        self.assertEqual(json.loads(shown.stdout)['outputs'][0]['golden'], 'out/golden/a.png')
        index = pixelate('library', '--library', str(self.library), 'index')
        self.assertEqual(index.returncode, 0, index.stderr)
        self.assertEqual(json.loads(index.stdout)['pieces'][0]['id'], 'harbour')
        self.assertEqual(snapshot(self.piece), before)
        self.assertFalse(list(self.library.parent.rglob('EXECUTED')))

    def test_malformed_and_unknown_ids_exit_2(self):
        for command in (('show', 'Bad_ID'), ('test', 'Bad_ID'), ('test', '../harbour'), ('test', 'missing')):
            with self.subTest(command=command):
                result = pixelate('library', '--library', str(self.library), *command)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertRegex(result.stderr, r'^library: .*(expected lowercase slug|unknown piece)')
        result = pixelate('find', 'harbour', '--mode', 'movie', '--library', str(self.library))
        self.assertEqual(result.returncode, 2)

    def test_no_selected_piece_exits_2(self):
        empty = self.library.parent / 'empty'
        empty.mkdir()
        for command, message in ((('test',), 'no pieces to test'), (('test', 'missing'), 'unknown piece'),
                                 (('test', '--quick'), 'no pieces to test')):
            with self.subTest(command=command):
                result = pixelate('library', '--library', str(empty), *command)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertIn(message, result.stderr)

    def test_golden_and_size_schema(self):
        image = self.data['outputs'][0]
        for change in ({'golden': 'out/a@1x.png'}, {'golden': 'out/golden/b.png'}, {'golden': 'out/golden/a.PNG'},
                       {'size': {'w': 64}}, {'size': {'w': 0, 'h': 48}}, {'size': {'w': True, 'h': 48}}):
            with self.subTest(change=change):
                self.data['outputs'][0] = {**image, **change}
                save(self.piece, self.data)
                with self.assertRaises(library.LibraryError):
                    library.validate(self.piece)
        self.data['outputs'][0] = {**image, 'name': 'b', 'frame': 'out/golden/b.png', 'golden': 'out/golden/b.png'}
        (self.piece / 'out' / 'golden' / 'b.png').write_bytes(b'png')
        save(self.piece, self.data)
        with self.assertRaisesRegex(library.LibraryError, 'distinct from frame'):
            library.validate(self.piece)
        self.data['outputs'][0] = {**image, 'size': {'w': 64, 'h': 48}}
        save(self.piece, self.data)
        library.validate(self.piece)
        (self.piece / 'out' / 'golden' / 'a.png').unlink()
        with self.assertRaisesRegex(library.LibraryError, 'output.golden'):
            library.validate(self.piece)

    def test_gitignore_tracks_only_library_goldens(self):
        def ignored(path):
            return subprocess.run(['git', 'check-ignore', '-q', '--no-index', path], cwd=REPO).returncode == 0
        self.assertFalse(ignored('library/harbour/out/golden/a.png'))
        for path in ('library/harbour/out/a.png', 'library/harbour/out/a@1x.png', 'library/harbour/art/out/a.png',
                     'library/harbour/out/golden/a.judge.png', 'examples/x/out/a.png', 'out/a.png'):
            with self.subTest(path=path):
                self.assertTrue(ignored(path))


class LibraryTest(Fixture):
    def test_4x_frame_matches_1x_golden_in_a_clean_copy(self):
        before = snapshot(self.piece)
        result, report = self.library_test('harbour')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report['ok'])
        self.assertFalse(report['quick'])
        outputs = self.outputs(report)
        self.assertEqual({name: o['status'] for name, o in outputs.items()},
                         {'a': 'passed', 'tone': 'passed', 'version': 'passed'})
        self.assertEqual(outputs['a']['golden'], {'ok': True, 'pixels': 0})
        self.assertEqual(outputs['a']['path'], 'out/a.png')
        self.assertEqual(outputs['tone']['sha256'], hashlib.sha256(b'RIFF fixture audio').hexdigest())
        self.assertNotIn('golden', outputs['tone'])
        self.assertEqual(snapshot(self.piece), before)
        everything, _ = self.library_test()
        self.assertEqual(everything.returncode, 0, everything.stdout)

    def test_outputs_absent_from_the_source_are_rendered_or_fail(self):
        # Only the 1x golden is checked in; the 4x frame, audio and export are generated by their commands.
        for path in ('out/a.png', 'sound/tone.wav', 'out/version.txt'):
            (self.piece / path).unlink()
        before = snapshot(self.piece)
        listed = pixelate('library', '--library', str(self.library), 'list')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        result, report = self.library_test('harbour')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outputs = self.outputs(report)
        self.assertEqual({name: o['status'] for name, o in outputs.items()},
                         {'a': 'passed', 'tone': 'passed', 'version': 'passed'})
        self.assertEqual(outputs['a']['golden'], {'ok': True, 'pixels': 0})
        self.assertEqual(snapshot(self.piece), before)
        # A declared output a command did not write is never green, whatever validation accepted.
        for output in self.data['outputs']:
            output['run'] = 'true'
        save(self.piece, self.data)
        result, report = self.library_test('harbour')
        self.assertEqual(result.returncode, 1)
        self.assertEqual({name: (o['status'], o['error']) for name, o in self.outputs(report).items()},
                         {'a': ('failed', 'not produced: out/a.png'), 'tone': ('failed', 'not produced: sound/tone.wav'),
                          'version': ('failed', 'not produced: out/version.txt')})

    def test_quick_skips_audio_and_export_explicitly(self):
        self.data['outputs'][1]['run'] = 'exit 3'
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(report['quick'])
        outputs = self.outputs(report)
        self.assertEqual(outputs['a']['status'], 'passed')
        for name, kind in (('tone', 'audio'), ('version', 'export')):
            self.assertEqual(outputs[name]['status'], 'skipped')
            self.assertEqual(outputs[name]['reason'], f'quick mode skips {kind} outputs')
            self.assertNotIn('run', outputs[name])
        full, report = self.library_test('harbour')
        self.assertEqual(full.returncode, 1)
        self.assertEqual(self.outputs(report)['tone']['status'], 'failed')

    def test_drift_is_reported_and_fails(self):
        golden = self.piece / 'out' / 'golden' / 'a.png'
        with Image.open(golden) as image:
            image = image.convert('RGB')
        image.putpixel((5, 7), (255, 0, 0))
        image.putpixel((9, 10), (255, 0, 0))
        image.save(golden)
        result, report = self.library_test('harbour')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report['ok'])
        check = self.outputs(report)['a']
        self.assertEqual(check['status'], 'failed')
        self.assertEqual(check['golden']['pixels'], 2)
        self.assertEqual(check['golden']['box'], [5, 7, 10, 11])
        self.assertEqual(check['golden']['max_delta'], 255 - 8)
        self.assertTrue(check['gate']['ok'])
        self.assertEqual(check['golden']['error'], '2 of 3072 1x pixels differ from the golden')

    def test_missing_golden_fails_after_dimension_check(self):
        del self.data['outputs'][0]['golden']
        save(self.piece, self.data)
        result, report = self.library_test('harbour')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.outputs(report)['a']['golden'],
                         {'ok': False, 'error': 'missing golden: declare out/golden/<output name>.png'})

    def test_dimension_mismatch(self):
        image = self.data['outputs'][0]
        for change, expected in (({'scale': 2}, 'expected 128x96 (64x48 at scale 2)'),
                                 ({'size': {'w': 32, 'h': 48}}, 'expected 128x192 (32x48 at scale 4)')):
            with self.subTest(change=change):
                self.data['outputs'][0] = {**image, **change}
                save(self.piece, self.data)
                result, report = self.library_test('harbour')
                self.assertEqual(result.returncode, 1)
                check = self.outputs(report)['a']
                self.assertEqual(check['golden']['error'], f'dimension mismatch: frame 256x192, {expected}')
        self.data['outputs'][0] = {**image, 'size': {'w': 64, 'h': 48}}
        self.data['canvas'] = {'w': 10, 'h': 10, 'scale': 1}
        save(self.piece, self.data)
        self.assertEqual(self.library_test('harbour')[0].returncode, 0)

    def test_failed_command_never_passes_on_stale_frame(self):
        self.assertTrue((self.piece / 'out' / 'a.png').is_file())
        self.data['outputs'][0]['run'] = f'{sys.executable} -c "raise SystemExit(\'boom\')"'
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 1)
        check = self.outputs(report)['a']
        self.assertEqual(check['status'], 'failed')
        self.assertEqual(check['error'], 'run failed')
        self.assertIn('boom', check['run']['error'])
        self.assertNotIn('golden', check)
        self.data['outputs'][0]['run'] = 'true'
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.outputs(report)['a']['error'], 'not produced: out/a.png')
        self.assertTrue((self.piece / 'out' / 'a.png').is_file())

    def test_shared_command_runs_once_and_timeout_kills(self):
        self.data['outputs'][1]['run'] = self.data['outputs'][2]['run'] = (
            f'echo x >> {self.library.parent / "count"} && {sys.executable} sound/make.py && '
            'pixelate --version > out/version.txt')
        save(self.piece, self.data)
        self.assertEqual(self.library_test('harbour')[0].returncode, 0)
        self.assertEqual((self.library.parent / 'count').read_text(), 'x\n')
        self.data['outputs'][0]['run'] = f'{sys.executable} -c "import time; time.sleep(60)"'
        save(self.piece, self.data)
        start = time.time()
        result, report = self.library_test('--quick', '--timeout', '1', 'harbour')
        self.assertLess(time.time() - start, 30)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.outputs(report)['a']['run']['error'], 'timed out after 1s')

    def test_gate_failure_blocks_all_but_study_even_on_an_exact_golden_match(self):
        self.data['outputs'][0]['style'] = 'pastel-cell'
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout)
        check = self.outputs(report)['a']
        self.assertEqual(check['golden'], {'ok': True, 'pixels': 0})
        self.assertFalse(check['gate']['ok'])
        self.assertIn('FAIL budget median_L', ' '.join(check['gate']['fail']))
        self.assertEqual((check['status'], check['gate_ok']), ('passed', False))
        self.assertEqual(check['diagnostic'], 'study: the technical gate failed; reported, not blocking')
        self.assertTrue(report['ok'])
        self.assertFalse(report['gate_ok'])
        self.assertFalse(report['pieces'][0]['gate_ok'])
        (self.piece / 'media').mkdir()
        for path in ('media/thumb.png', 'media/contact.png', 'notes.md'):
            (self.piece / path).write_bytes(b'fixture')
        accepted = {'status': 'accepted', 'media': {'thumb': 'media/thumb.png', 'contact': 'media/contact.png'},
                    'review': {'notes': 'notes.md', 'approved_by': 'user', 'record': None},
                    'knobs': {name: {'type': 'int', 'default': 1, 'edits': 'art/draw.py'} for name in ('seed', 'size')}}
        for change in ({'status': 'starter'}, accepted):
            with self.subTest(status=change['status']):
                save(self.piece, {**self.data, **change})
                result, report = self.library_test('--quick', 'harbour')
                self.assertEqual(result.returncode, 1, result.stdout)
                check = self.outputs(report)['a']
                self.assertEqual(check['golden'], {'ok': True, 'pixels': 0})
                self.assertEqual((check['status'], check['gate_ok']), ('failed', False))
                self.assertNotIn('diagnostic', check)
        save(self.piece, {**self.data, 'status': 'starter', 'outputs': [{**self.data['outputs'][0], 'style': 'arcade'}]})
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(report['gate_ok'])
        self.assertTrue(self.outputs(report)['a']['gate_ok'])

    def test_a_gate_error_blocks_a_study(self):
        self.data['outputs'][0].update(run=f'{sys.executable} art/draw.py && echo not-json > out/pal.json',
                                       pal='out/pal.json')
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 1)
        check = self.outputs(report)['a']
        self.assertEqual(check['golden'], {'ok': True, 'pixels': 0})
        self.assertIn('JSONDecodeError', check['gate']['error'])
        self.assertEqual((check['status'], check['gate_ok']), ('failed', False))
        self.assertNotIn('diagnostic', check)

    def test_each_command_must_write_its_own_outputs(self):
        shutil.copy(self.piece / 'out' / 'a.png', self.piece / 'out' / 'b.png')
        shutil.copy(self.piece / 'out' / 'golden' / 'a.png', self.piece / 'out' / 'golden' / 'b.png')
        a = self.data['outputs'][0]
        a['run'] = f'{sys.executable} art/draw.py && cp out/a.png out/b.png'
        self.data['outputs'].insert(1, {**a, 'name': 'b', 'run': 'true', 'frame': 'out/b.png',
                                        'golden': 'out/golden/b.png'})
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 1)
        outputs = self.outputs(report)
        self.assertEqual(outputs['a']['status'], 'passed')
        self.assertEqual((outputs['b']['status'], outputs['b']['error']), ('failed', 'not produced: out/b.png'))
        # Outputs meant to share a command declare the same command: it runs once and writes both.
        a['run'] = f'echo x >> {self.library.parent / "count"} && ' + a['run']
        self.data['outputs'][1]['run'] = a['run']
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((self.library.parent / 'count').read_text(), 'x\n')

    def test_links_and_pipes_written_by_a_command_are_never_read(self):
        outside = self.library.parent / 'outside'
        outside.mkdir()
        canary = write_canary(self.piece / 'out' / 'a.png', outside / 'a.png')
        (outside / 'version.txt').write_text('keep', encoding='utf-8')
        draw = f'{sys.executable} art/draw.py'
        for run, error, read in (
                (f'{draw} && rm out/a.png && ln -s {outside / "a.png"} out/a.png', 'unsafe output: out/a.png', False),
                (f'{draw} && mv out out-real && ln -s {outside} out', 'unsafe output: out/a.png: out is a link', False),
                (f'{draw} && rm out/a.png && mkfifo out/a.png', 'unsafe output: out/a.png', False),
                (f'{draw} && ln -s {outside / "a.png"} out/a-actor.png', 'unsafe gate input: out/a-actor.png', True)):
            with self.subTest(run=run):
                self.data['outputs'][0].update(run=run, actor='out/a-actor.png')
                self.data['outputs'][1]['run'] = f'{sys.executable} sound/make.py && rm sound/tone.wav && ln -s {outside / "a.png"} sound/tone.wav'
                save(self.piece, self.data)
                start = time.time()
                result, report = self.library_test('harbour')
                self.assertLess(time.time() - start, 60)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(canary, result.stdout)
                outputs = self.outputs(report)
                self.assertTrue(outputs['a']['error'].startswith(error), outputs['a']['error'])
                self.assertTrue(outputs['tone']['error'].startswith('unsafe output: sound/tone.wav'))
                self.assertNotIn('gate', outputs['a'])
                # Only the real frame the command drew is hashed and compared, never the canary.
                self.assertEqual(('sha256' in outputs['a'], 'golden' in outputs['a']), (read, read))
                self.assertNotIn('sha256', outputs['tone'])
                if 'out-real' in run:
                    # Deleting the export's stale file never follows the linked folder.
                    self.assertTrue(outputs['version']['error'].startswith('unsafe output: out/version.txt'))
                    self.assertNotIn('run', outputs['version'])
                self.assertEqual((outside / 'version.txt').read_text(encoding='utf-8'), 'keep')
                self.assertEqual(hashlib.sha256((outside / 'a.png').read_bytes()).hexdigest(), canary)

    def test_invalid_manifest_exits_2(self):
        (self.piece / 'piece.json').write_text('{"schema": 1, "schema": 1}', encoding='utf-8')
        result, _ = self.library_test('harbour')
        self.assertEqual(result.returncode, 2)
        self.assertIn('duplicate JSON key', result.stderr)


class QuickCoverage(Fixture):
    """`--quick` tests one kind per piece and never reports a piece green from skipped outputs alone."""

    def keep(self, *names):
        self.data['outputs'] = [o for o in self.data['outputs'] if o['name'] in names]
        save(self.piece, self.data)

    def test_images_are_tested_and_other_kinds_are_reported_untested(self):
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout)
        piece = report['pieces'][0]
        self.assertEqual(piece['kinds'], {'image': {'declared': 1, 'tested': 1}, 'audio': {'declared': 1, 'tested': 0},
                                          'export': {'declared': 1, 'tested': 0}})
        self.assertEqual({n: o['tested'] for n, o in self.outputs(report).items()},
                         {'a': True, 'tone': False, 'version': False})
        full, report = self.library_test('harbour')
        self.assertEqual(full.returncode, 0, full.stdout)
        self.assertEqual(report['pieces'][0]['kinds']['export'], {'declared': 1, 'tested': 1})

    def test_export_only_piece_runs_its_exports_in_quick_mode(self):
        self.keep('version')
        before = snapshot(self.piece)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.outputs(report)['version']
        self.assertEqual((output['status'], output['tested']), ('passed', True))
        self.assertNotEqual(output['sha256'], sha(b'stale committed export'))
        self.assertTrue(report['ok'])
        self.assertEqual(snapshot(self.piece), before)

    def test_export_only_piece_fails_when_the_command_is_a_no_op_despite_a_stale_export(self):
        self.keep('version')
        self.assertEqual((self.piece / 'out' / 'version.txt').read_text(), 'stale committed export')
        for run in ('true', 'exit 3'):
            with self.subTest(run=run):
                self.data['outputs'][0]['run'] = run
                save(self.piece, self.data)
                result, report = self.library_test('--quick', 'harbour')
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertFalse(report['ok'])
                output = self.outputs(report)['version']
                self.assertEqual(output['status'], 'failed')
                self.assertNotIn('sha256', output)

    def test_export_only_piece_does_not_run_its_audio(self):
        self.keep('version', 'tone')
        next(o for o in self.data['outputs'] if o['name'] == 'tone')['run'] = 'exit 3'
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout)
        outputs = self.outputs(report)
        self.assertEqual((outputs['version']['status'], outputs['tone']['status']), ('passed', 'skipped'))
        self.assertEqual(report['pieces'][0]['kinds']['audio'], {'declared': 1, 'tested': 0})

    def test_audio_only_piece_runs_its_first_audio_command_and_reports_the_rest_untested(self):
        self.keep('tone')
        self.data['outputs'].append({'name': 'tone2', 'kind': 'audio', 'run': 'exit 3', 'file': 'sound/tone2.wav'})
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outputs = self.outputs(report)
        self.assertEqual((outputs['tone']['status'], outputs['tone']['tested']), ('passed', True))
        self.assertEqual((outputs['tone2']['status'], outputs['tone2']['tested']), ('skipped', False))
        self.assertEqual(outputs['tone2']['reason'], 'quick mode runs only the first audio command')
        self.assertEqual(report['pieces'][0]['kinds']['audio'], {'declared': 2, 'tested': 1})
        self.data['outputs'][0]['run'] = 'true'
        save(self.piece, self.data)
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.outputs(report)['tone']['error'], 'not produced: sound/tone.wav')

    def test_a_piece_with_no_passed_output_is_never_ok(self):
        # validate() requires an output, so reach the all-skipped state through the function's own selection.
        self.keep('tone')
        with mock.patch.object(library, 'check_output', lambda *args: args[-1].update(status='skipped')):
            piece = library.test_piece(self.piece, quick=True)
        self.assertFalse(piece['ok'])

    def test_gate_ok_is_null_without_an_image_and_never_implies_pack_legality(self):
        self.keep('version')
        result, report = self.library_test('--quick', 'harbour')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIsNone(report['pieces'][0]['gate_ok'])
        self.assertIsNone(report['gate_ok'])
        self.assertNotIn('gate_ok', self.outputs(report)['version'])
        # Mixed with an image that fails its gate, the aggregate reports the image, not the exports.
        second, data = make_piece(self.library, 'dockside')
        data['outputs'][0]['style'] = 'pastel-cell'
        data['outputs'] = data['outputs'][:1]
        save(second, data)
        result, report = self.library_test('--quick')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual({p['id']: p['gate_ok'] for p in report['pieces']}, {'dockside': False, 'harbour': None})
        self.assertIs(report['gate_ok'], False)

    def test_actual_export_only_pieces_run_in_a_clean_copy(self):
        for piece_id, count in (('meadow-kit', 4), ('starter-assets', 3)):
            for label, env in (('unset', caller_env()), ('spoofed', caller_env('/nonexistent/kit'))):
                with self.subTest(piece=piece_id, PIXELATE_KIT=label):
                    result = pixelate('library', 'test', '--quick', piece_id, env=env)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    piece = json.loads(result.stdout)['pieces'][0]
                    self.assertTrue(piece['ok'])
                    self.assertIsNone(piece['gate_ok'])
                    self.assertEqual(piece['kinds'], {'export': {'declared': count, 'tested': count}})
                    self.assertEqual({o['status'] for o in piece['outputs']}, {'passed'})
                    self.assertTrue(all(o['sha256'] and o['run']['ok'] for o in piece['outputs']))


class ByteBinding(Fixture):
    """A process the run leaves behind may rewrite the frame between checks; one read binds them all."""

    def test_library_hashes_compares_and_gates_one_read_of_the_frame(self):
        work = self.library.parent / 'work' / 'harbour'
        shutil.copytree(self.piece, work)
        drawn, later = (work / 'out' / 'a.png').read_bytes(), png((250, 250, 250))
        output, result = self.data['outputs'][0], {}
        with lingering_writer(work, 'out/a.png', later) as reads, gated_frames() as gated:
            library.check_output(self.piece, work, self.library.parent, output, self.data['canvas'], 'accepted', result)
        self.assertEqual((work / 'out' / 'a.png').read_bytes(), later)  # the writer did change the file
        self.assertEqual(reads, ['out/a.png'])
        self.assertEqual((result['sha256'], gated), (sha(drawn), [sha(drawn)]))
        self.assertEqual(result['golden'], {'ok': True, 'pixels': 0})
        self.assertEqual((result['status'], result['gate_ok']), ('passed', True))

    def test_render_gates_and_judges_the_bytes_it_hashes(self):
        drawn, later = (self.piece / 'out' / 'a.png').read_bytes(), png((250, 250, 250))
        with mock.patch.dict(os.environ), lingering_writer(self.piece, 'out/a.png', later) as reads, \
                gated_frames() as gated:
            os.environ.pop('PIXELATE_NO_LOG', None)
            record = render.render_one(self.piece, self.data['outputs'][0], run=False, piece=True)
        self.assertEqual((self.piece / 'out' / 'a.png').read_bytes(), later)
        self.assertEqual(reads, ['out/a.png'])
        self.assertEqual((record['sha256'], gated), (sha(drawn), [sha(drawn)]))
        self.assertTrue(record['gate']['ok'], record['gate'])
        self.assertIn('defects', record['judge'])
        judged = json.loads((self.piece / '.pixelate' / 'judge-log.jsonl').read_text().splitlines()[-1])
        self.assertEqual(judged['sha256'], sha(drawn))
        # The judged frame outlives the render: the kept snapshot holds exactly the bytes logged.
        self.assertEqual(record['snapshot'], f'.pixelate/snapshots/{sha(drawn)}/a.png')
        self.assertEqual(judged['frame'], str(self.piece / record['snapshot']))
        self.assertEqual(sha(Path(judged['frame']).read_bytes()), judged['sha256'])
        self.assertTrue((self.piece / 'out' / 'a.judge.png').is_file())  # the overlay stays beside the frame


# Stands in for the art director: records the frame and brief the prompt names, with the frame's hash.
CRITIC = '''import hashlib, re, sys
text = sys.stdin.read()
frame = re.search(r'^- Frame at delivered size \\(\\d+x\\d+\\): (.+)$', text, re.M).group(1)
brief = re.search(r'^- The brief: (.+)$', text, re.M).group(1)
with open(frame, 'rb') as f:
    digest = hashlib.sha256(f.read()).hexdigest()
with open(sys.argv[1], 'a') as f:
    f.write(frame + ' ' + digest + ' ' + brief + '\\n')
print('GRADE: B')
'''
BRIEF = 'Request: a harbour wall at night\n'


class Snapshots(Fixture):
    """A logged piece render keeps the frame bytes it checked; its logs name a file that still holds them."""

    def setUp(self):
        super().setUp()
        (self.piece / 'brief.md').write_text(BRIEF, encoding='utf-8')
        self.data['outputs'][0]['brief'] = 'brief.md'
        save(self.piece, self.data)
        critic, self.seen = self.library.parent / 'critic.py', self.library.parent / 'seen.txt'
        critic.write_text(CRITIC, encoding='utf-8')
        patch = mock.patch.dict(os.environ, PIXELATE_CRITIC_CMD=shlex.join([sys.executable, str(critic), str(self.seen)]))
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop('PIXELATE_NO_LOG', None)

    def render(self, *args):
        """pixelate render in this process, so a test can patch it; returns (exit code, records)"""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            render.main([str(self.piece), '--image', 'a', '--json', *args])
        return exit.exception.code, json.loads(out.getvalue())

    def logs(self, name):
        return [json.loads(line) for line in (self.piece / '.pixelate' / name).read_text().splitlines()]

    def test_a_later_render_never_replaces_a_kept_snapshot(self):
        first = self.render('--no-run')[1][0]
        kept = self.piece / first['snapshot']
        (self.piece / 'out' / 'a.png').write_bytes(png((250, 250, 250)))
        second = self.render('--no-run')[1][0]
        self.assertEqual(second['sha256'], sha(png((250, 250, 250))))
        self.assertNotEqual(second['snapshot'], first['snapshot'])
        self.assertEqual(sha(kept.read_bytes()), first['sha256'])
        # The same bytes again reuse the kept file; a kept file that no longer matches its hash fails
        # the image and stays as it is.
        (self.piece / 'out' / 'a.png').write_bytes(kept.read_bytes())
        self.assertEqual(self.render('--no-run')[1][0]['snapshot'], first['snapshot'])
        kept.chmod(0o644)
        kept.write_bytes(b'tampered')
        code, records = self.render('--no-run')
        self.assertEqual(code, 1)
        self.assertEqual(records[0]['error'], f'unsafe snapshot: {first["snapshot"]}: holds other bytes than its hash')
        for key in ('sha256', 'gate', 'judge'):
            self.assertNotIn(key, records[0])
        self.assertEqual(kept.read_bytes(), b'tampered')
        self.assertEqual([j['sha256'] for j in self.logs('judge-log.jsonl')],
                         [first['sha256'], second['sha256'], first['sha256']])

    def test_critique_grades_the_snapshot_the_gate_checked(self):
        drawn, later = (self.piece / 'out' / 'a.png').read_bytes(), png((250, 250, 250))
        real = render.technical_gate
        def gate(folder, im):
            result = real(folder, im)
            (self.piece / 'out' / 'a.png').write_bytes(later)   # a lingering writer, after the gate
            (self.piece / 'brief.md').write_text('Request: something else\n', encoding='utf-8')
            return result
        with mock.patch.object(render, 'technical_gate', gate):
            records = self.render('--no-run', '--critique')[1]
        self.assertEqual((self.piece / 'out' / 'a.png').read_bytes(), later)
        record, run = records[0], self.logs('runs.jsonl')[-1]['images'][0]
        critiqued = [r for r in self.logs('judge-log.jsonl') if r['type'] == 'critique']
        self.assertEqual(len(critiqued), 1)
        self.assertEqual((record['sha256'], run['sha256'], critiqued[0]['sha256']), (sha(drawn),) * 3)
        self.assertEqual((run['snapshot'], run['grade']), (record['snapshot'], 'B'))
        frame, seen, brief = self.seen.read_text().split()
        self.assertEqual((frame, seen), (str(self.piece / record['snapshot']), sha(drawn)))
        self.assertEqual(critiqued[0]['frame'], frame)
        # The brief the critic read is the one the gate read, kept beside the frame snapshot.
        self.assertEqual((critiqued[0]['brief'], brief),
                         (str(self.piece / '.pixelate' / 'snapshots' / sha(BRIEF.encode()) / 'brief.md'),) * 2)
        self.assertEqual(Path(brief).read_text(encoding='utf-8'), BRIEF)
        saved = self.piece / 'out' / 'critique-a-lead-r1.md'
        self.assertEqual((record['critique']['file'], critiqued[0]['critique']), (str(saved),) * 2)
        self.assertEqual(saved.read_text(encoding='utf-8'), 'GRADE: B\n')

    def test_no_log_keeps_no_snapshot_and_saves_the_critique_beside_the_frame(self):
        drawn = (self.piece / 'out' / 'a.png').read_bytes()
        with mock.patch.dict(os.environ, PIXELATE_NO_LOG='1'):
            records = self.render('--no-run', '--critique')[1]
        self.assertFalse((self.piece / '.pixelate').exists())
        self.assertEqual(json.loads((self.piece / 'render-report.json').read_text()), records)
        record = records[0]
        self.assertNotIn('snapshot', record)
        frame, seen, brief = self.seen.read_text().split()
        self.assertEqual((seen, record['sha256']), (sha(drawn),) * 2)
        for path in (frame, brief):
            self.assertFalse(Path(path).is_relative_to(self.piece), path)   # the private copy, now gone
            self.assertFalse(Path(path).exists())
        saved = self.piece / 'out' / 'critique-a-lead-r1.md'
        self.assertEqual((record['critique']['file'], record['critique']['grade']), (str(saved), 'B'))
        self.assertTrue(saved.is_file())

    def test_a_linked_snapshot_folder_is_never_written_through(self):
        outside = self.library.parent / 'outside'
        outside.mkdir()
        draw = self.data['outputs'][0]['run']
        for link, error in (('.pixelate', '.pixelate is a link'),
                            ('.pixelate/snapshots', 'snapshots is a link')):
            with self.subTest(link=link):
                self.data['outputs'][0]['run'] = f'mkdir -p .pixelate && rm -rf {link} && ln -s {outside} {link} && {draw}'
                save(self.piece, self.data)
                result = pixelate('render', str(self.piece), '--image', 'a', '--critique', '--json')
                self.assertEqual(result.returncode, 1)
                record = json.loads(result.stdout)[0]
                self.assertTrue(record['run']['ok'])
                self.assertTrue(record['error'].startswith('unsafe snapshot: .pixelate/snapshots/'), record['error'])
                self.assertIn(error, record['error'])
                for key in ('sha256', 'snapshot', 'gate', 'judge', 'critique'):
                    self.assertNotIn(key, record)
                self.assertEqual(list(outside.iterdir()), [])
                if link == '.pixelate':
                    self.assertIn('run log not written: .pixelate: .pixelate is a link', result.stderr)
                else:
                    self.assertFalse(self.logs('runs.jsonl')[-1]['ok'])
                (self.piece / link).unlink()


class EraLegality(unittest.TestCase):
    """Era legality comes from the gate's `--era` lines; `pixelate era` only reports and exits 0."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.library = Path(temp.name) / 'library'
        self.library.mkdir()

    def library_test(self, piece_id):
        result = pixelate('library', '--library', str(self.library), 'test', piece_id)
        return result, json.loads(result.stdout)

    def test_illegal_era_frame_with_an_exact_golden_fails_an_accepted_piece(self):
        piece, data = make_era_piece(self.library, 'nes', NES_ILLEGAL, (256, 240))
        era = pixelate('era', 'out/a.png', '--era', 'nes', cwd=piece)
        self.assertEqual(era.returncode, 0, era.stderr)
        self.assertIn('the NES-style 8-bit screen is 256x224', era.stdout)
        self.assertNotIn('legal', era.stdout)
        check = pixelate('check', 'out/a.png', '--era', 'nes', cwd=piece)
        self.assertEqual(check.returncode, 1, check.stdout + check.stderr)
        self.assertRegex(check.stdout, r'(?m)^FAIL era nes ')
        self.assertRegex(check.stdout, r'(?m)^FAIL era tiles ')
        result, report = self.library_test(piece.name)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual((report['ok'], report['gate_ok']), (False, False))
        image = report['pieces'][0]['outputs'][0]
        self.assertEqual(image['golden'], {'ok': True, 'pixels': 0})
        self.assertTrue(image['era']['ran'])
        self.assertNotIn('ok', image['era'])
        self.assertFalse(image['gate']['ok'])
        self.assertNotIn('error', image['gate'])
        self.assertTrue(any(line.startswith('FAIL era nes ') for line in image['gate']['fail']), image['gate'])
        self.assertEqual((image['status'], image['gate_ok']), ('failed', False))
        self.assertNotIn('diagnostic', image)
        # A study only has to render: the same verdict is reported, not blocking, and gate_ok stays false.
        save(piece, {**data, 'status': 'study'})
        result, report = self.library_test(piece.name)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((report['ok'], report['gate_ok']), (True, False))
        image = report['pieces'][0]['outputs'][0]
        self.assertEqual((image['status'], image['gate_ok']), ('passed', False))
        self.assertEqual(image['diagnostic'], 'study: the technical gate failed; reported, not blocking')

    def test_legal_era_frame_passes_the_gate(self):
        piece, _ = make_era_piece(self.library, 'gameboy', GAMEBOY_LEGAL, (160, 144))
        check = pixelate('check', 'out/a.png', '--era', 'gameboy', cwd=piece)
        self.assertEqual(check.returncode, 0, check.stdout)
        result, report = self.library_test(piece.name)
        self.assertEqual(result.returncode, 0, result.stdout)
        image = report['pieces'][0]['outputs'][0]
        self.assertTrue(image['gate']['ok'])
        self.assertTrue(any(line.startswith('PASS era gameboy ') for line in check.stdout.splitlines()))
        self.assertEqual((image['status'], image['gate_ok'], report['gate_ok']), ('passed', True, True))


class RenderPiece(Fixture):
    def test_render_reads_typed_outputs_and_never_gates_audio(self):
        result = pixelate('render', str(self.piece), '--json')
        records = {r['name']: r for r in json.loads(result.stdout)}
        image, tone, version = records['a'], records['tone'], records['version']
        self.assertEqual((image['kind'], image['frame']), ('image', 'out/a.png'))
        self.assertTrue(image['run']['ok'])
        self.assertIn('gate', image)
        self.assertIn('defects', image['judge'])
        for record, kind, path in ((tone, 'audio', 'sound/tone.wav'), (version, 'export', 'out/version.txt')):
            self.assertEqual((record['kind'], record['file']), (kind, path))
            self.assertTrue(record['run']['ok'])
            self.assertEqual(record['sha256'], hashlib.sha256((self.piece / path).read_bytes()).hexdigest())
            for key in ('gate', 'judge', 'era', 'frame'):
                self.assertNotIn(key, record)
        self.assertTrue((self.piece / 'out' / 'version.txt').read_text().startswith('pixelate-anything '))
        report = json.loads((self.piece / 'render-report.json').read_text())
        self.assertEqual([r['name'] for r in report], ['a', 'tone', 'version'])
        run = json.loads((self.piece / '.pixelate' / 'runs.jsonl').read_text().splitlines()[-1])
        self.assertEqual([i['name'] for i in run['images']], ['a'])
        self.assertEqual([(f['name'], f['kind'], f['ok']) for f in run['files']],
                         [('tone', 'audio', True), ('version', 'export', True)])
        self.assertEqual(result.returncode, 0 if run['ok'] else 1)
        one = json.loads(pixelate('render', str(self.piece), '--image', 'tone', '--no-run', '--json').stdout)
        self.assertEqual([(r['name'], 'run' in r) for r in one], [('tone', False)])

    def test_render_never_hashes_or_gates_a_linked_output(self):
        outside = self.library.parent / 'outside'
        outside.mkdir()
        canary = write_canary(self.piece / 'out' / 'a.png', outside / 'a.png')
        drawn = (self.piece / 'out' / 'a.png').read_bytes()
        link = f'ln -sf {outside / "a.png"}'
        for image_run, error in ((f'rm -f out/a.png && {link} out/a.png', 'unsafe frame: out/a.png'),
                                 (f'{sys.executable} art/draw.py && {link} out/a-actor.png', 'unsafe gate input: out/a-actor.png')):
            with self.subTest(run=image_run):
                self.data['outputs'][0].update(run=image_run, actor='out/a-actor.png')
                self.data['outputs'][1]['run'] = f'rm -f sound/tone.wav && {link} sound/tone.wav'
                save(self.piece, self.data)
                result = pixelate('render', str(self.piece), '--json')
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(canary, result.stdout)
                records = {r['name']: r for r in json.loads(result.stdout)}
                self.assertTrue(records['a']['error'].startswith(error), records['a']['error'])
                self.assertTrue(records['tone']['error'].startswith('unsafe file: sound/tone.wav'))
                for name in ('a', 'tone'):
                    for key in ('sha256', 'gate', 'judge'):
                        self.assertNotIn(key, records[name])
                self.assertNotIn(canary, (self.piece / '.pixelate' / 'runs.jsonl').read_text())
                for path in ('out/a.png', 'out/a-actor.png', 'sound/tone.wav'):
                    (self.piece / path).unlink(missing_ok=True)
                (self.piece / 'out' / 'a.png').write_bytes(drawn)
                (self.piece / 'sound' / 'tone.wav').write_bytes(b'stale committed audio')

    def test_failed_audio_command_fails_the_render(self):
        self.data['outputs'][1]['run'] = 'exit 3'
        save(self.piece, self.data)
        result = pixelate('render', str(self.piece), '--image', 'tone')
        self.assertEqual(result.returncode, 1)
        self.assertIn('tone | RUN FAILED', result.stdout)

    def test_piece_json_errors(self):
        (self.piece / 'render.json').write_text('{"images": []}', encoding='utf-8')
        result = pixelate('render', str(self.piece))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('both piece.json and render.json', result.stderr)
        (self.piece / 'render.json').unlink()
        result = pixelate('render', str(self.piece), '--image', 'missing')
        self.assertIn('no output named missing in piece.json', result.stderr)
        self.data['outputs'][0]['style'] = 'baroque'
        save(self.piece, self.data)
        result = pixelate('render', str(self.piece))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('piece.json: output.style', result.stderr)


class PieceKitEnvironment(Fixture):
    KIT_VERSION = 'python3 "$PIXELATE_KIT/pixelate" --version > out/version.txt'

    def test_pieces_find_the_kit_without_an_exported_variable(self):
        self.data['outputs'][2]['run'] = self.KIT_VERSION
        save(self.piece, self.data)
        for label, env in (('unset', caller_env()), ('spoofed', caller_env('/nonexistent/kit'))):
            with self.subTest(PIXELATE_KIT=label):
                (self.piece / 'out' / 'version.txt').write_text('stale committed export', encoding='utf-8')
                result = pixelate('library', '--library', str(self.library), 'test', 'harbour', env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.outputs(json.loads(result.stdout))['version']['status'], 'passed')
                rendered = pixelate('render', str(self.piece), '--image', 'version', '--json', env=env)
                self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
                self.assertTrue((self.piece / 'out' / 'version.txt').read_text().startswith('pixelate-anything '))

    def test_piece_env_sets_the_canonical_kit_over_an_inherited_value(self):
        with mock.patch.dict(os.environ, PIXELATE_KIT='/nonexistent/kit'):
            env = render.piece_env()
        self.assertEqual(env['PIXELATE_KIT'], str(REPO))
        self.assertEqual(env['PYTHONPATH'].split(os.pathsep)[0], str(REPO / 'tools'))
        self.assertEqual(env['PATH'].split(os.pathsep)[0], str(REPO))

    def test_clean_copy_of_lantern_isle_runs_without_an_exported_variable(self):
        for label, env in (('unset', caller_env()), ('spoofed', caller_env('/nonexistent/kit'))):
            with self.subTest(PIXELATE_KIT=label):
                result = pixelate('library', 'test', '--quick', 'lantern-isle', env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertTrue(report['ok'])
                images = [o for o in report['pieces'][0]['outputs'] if o['kind'] == 'image']
                self.assertTrue(images)
                self.assertEqual({o['status'] for o in images}, {'passed'})


class RenderInPlace(Fixture):
    """`render DIR` on a piece.json renders in the source folder, so a stale declared output must not pass."""

    def render_json(self, *args):
        result = pixelate('render', str(self.piece), '--json', *args)
        return result, {r['name']: r for r in json.loads(result.stdout)}

    def logged(self):
        return json.loads((self.piece / '.pixelate' / 'runs.jsonl').read_text().splitlines()[-1])

    def test_stale_frame_and_a_no_op_command_fail_without_hashing_the_old_bytes(self):
        stale = sha((self.piece / 'out' / 'a.png').read_bytes())
        self.data['outputs'][0]['run'] = 'true'
        save(self.piece, self.data)
        result, records = self.render_json('--image', 'a')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(records['a']['error'], 'frame not found: out/a.png')
        for key in ('sha256', 'gate', 'judge', 'snapshot'):
            self.assertNotIn(key, records['a'])
        self.assertFalse((self.piece / 'out' / 'a.png').exists())
        entry = self.logged()['images'][0]
        self.assertEqual((entry['sha256'], entry['ok']), (None, False))
        self.assertNotIn(stale, (self.piece / '.pixelate' / 'runs.jsonl').read_text())
        self.assertFalse((self.piece / '.pixelate' / 'snapshots').exists())

    def test_stale_audio_and_export_with_a_no_op_command_fail(self):
        stale = {path: sha((self.piece / path).read_bytes()) for path in ('sound/tone.wav', 'out/version.txt')}
        self.data['outputs'][1]['run'] = 'true'
        self.data['outputs'][2]['run'] = 'true'
        save(self.piece, self.data)
        result, records = self.render_json('--image', 'tone')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(records['tone']['error'], 'file not found: sound/tone.wav')
        self.assertNotIn('sha256', records['tone'])
        self.assertTrue((self.piece / 'out' / 'version.txt').exists())      # not selected: left alone
        result, records = self.render_json()
        self.assertEqual(result.returncode, 1)
        for name, path in (('tone', 'sound/tone.wav'), ('version', 'out/version.txt')):
            self.assertEqual(records[name]['error'], f'file not found: {path}')
            self.assertNotIn('sha256', records[name])
            self.assertFalse((self.piece / path).exists())
        self.assertTrue(records['a']['run']['ok'])
        for digest in stale.values():
            self.assertNotIn(digest, json.dumps(self.logged()))
        self.assertEqual([(f['name'], f['sha256'], f['ok']) for f in self.logged()['files']],
                         [('tone', None, False), ('version', None, False)])

    def test_a_linked_parent_folder_fails_the_output_and_deletes_nothing_outside(self):
        outside = self.library.parent / 'outside'
        outside.mkdir()
        (outside / 'tone.wav').write_bytes(b'outside canary')
        self.data['outputs'][0]['run'] = f'{self.data["outputs"][0]["run"]} && mv sound sound.bak && ln -s {outside} sound'
        save(self.piece, self.data)
        result, records = self.render_json()
        self.assertEqual(result.returncode, 1)
        self.assertEqual((outside / 'tone.wav').read_bytes(), b'outside canary')
        tone = records['tone']
        self.assertFalse(tone['run']['ok'])
        self.assertTrue(tone['run']['error'].startswith('unsafe output: sound/tone.wav'), tone['run']['error'])
        self.assertNotIn('sha256', tone)
        self.assertTrue(records['a']['run']['ok'])

    def test_no_run_deletes_nothing_and_gates_what_is_there(self):
        before = snapshot(self.piece)
        result, records = self.render_json('--no-run')
        self.assertEqual(result.returncode, 0 if self.logged()['ok'] else 1)
        for path in ('out/a.png', 'sound/tone.wav', 'out/version.txt'):
            self.assertEqual(sha((self.piece / path).read_bytes()), before[path])
        for name, path in (('tone', 'sound/tone.wav'), ('version', 'out/version.txt')):
            self.assertNotIn('run', records[name])
            self.assertEqual(records[name]['sha256'], before[path])
        self.assertNotIn('run', records['a'])
        self.assertEqual(records['a']['sha256'], before['out/a.png'])

    def test_a_real_command_replaces_every_stale_output(self):
        stale = {path: sha((self.piece / path).read_bytes()) for path in ('out/a.png', 'sound/tone.wav', 'out/version.txt')}
        result, records = self.render_json()
        self.assertEqual(result.returncode, 0 if self.logged()['ok'] else 1)
        for name, path in (('a', 'out/a.png'), ('tone', 'sound/tone.wav'), ('version', 'out/version.txt')):
            self.assertTrue(records[name]['run']['ok'])
            self.assertEqual(records[name]['sha256'], sha((self.piece / path).read_bytes()))
            if name != 'a':                                  # the frame re-renders the same pixels
                self.assertNotEqual(records[name]['sha256'], stale[path])
        self.assertEqual(records['tone']['sha256'], sha(b'RIFF fixture audio'))
        self.assertTrue((self.piece / records['a']['snapshot']).is_file())

    def test_a_shared_command_runs_once_and_must_write_every_output(self):
        shared = f'echo run >> runs.txt; {sys.executable} sound/make.py; echo x > out/version.txt'
        self.data['outputs'][1]['run'] = self.data['outputs'][2]['run'] = shared
        save(self.piece, self.data)
        result, records = self.render_json()
        self.assertEqual((self.piece / 'runs.txt').read_text(), 'run\n')
        self.assertEqual(result.returncode, 0 if self.logged()['ok'] else 1)
        self.assertEqual(records['version']['sha256'], sha(b'x\n'))
        self.assertEqual(records['tone']['run'], records['version']['run'])
        # The same command no longer writes the export: its stale copy is gone, so it cannot pass.
        shared = f'{sys.executable} sound/make.py'
        self.data['outputs'][1]['run'] = self.data['outputs'][2]['run'] = shared
        save(self.piece, self.data)
        result, records = self.render_json()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(records['tone']['sha256'], sha(b'RIFF fixture audio'))
        self.assertEqual(records['version']['error'], 'file not found: out/version.txt')
        self.assertNotIn('sha256', records['version'])

    def test_a_legacy_render_json_keeps_its_stale_output_and_environment(self):
        (self.piece / 'piece.json').unlink()
        out = self.piece / 'out'
        command = f'{sys.executable} -c "import os; open(\'out/env.txt\', \'w\').write(repr((os.environ.get(\'PIXELATE_KIT\'), os.environ.get(\'PYTHONPATH\'))))"'
        (self.piece / 'render.json').write_text(json.dumps({'images': [
            {'name': 'a', 'run': 'true', 'frame': 'out/a.png', 'style': 'arcade', 'scale': 4},
            {'name': 'env', 'run': command, 'frame': 'out/a.png', 'style': 'arcade', 'scale': 4}]}))
        stale = sha((out / 'a.png').read_bytes())
        with mock.patch.dict(os.environ, {'PIXELATE_KIT': '/inherited/kit', 'PYTHONPATH': '/inherited/path'}):
            result = pixelate('render', str(self.piece), '--json')
        records = {r['name']: r for r in json.loads(result.stdout)}
        self.assertEqual(records['a']['sha256'], stale)            # legacy renders in place and keeps it
        self.assertEqual((out / 'env.txt').read_text(), repr(('/inherited/kit', '/inherited/path')))


class GoldenComparison(unittest.TestCase):
    def test_rgb_frame_matches_palette_golden_and_alpha_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            small = Image.new('RGBA', (3, 2), (10, 20, 30, 255))
            small.putpixel((1, 1), (10, 20, 30, 0))
            small.resize((9, 6), Image.Resampling.NEAREST).save(temp / 'frame.png')
            small.save(temp / 'golden.png')
            size = {'w': 3, 'h': 2}
            self.assertTrue(library.compare_golden(temp / 'frame.png', temp / 'golden.png', size, 3)['ok'])
            small.convert('RGB').save(temp / 'golden.png')
            self.assertEqual(library.compare_golden(temp / 'frame.png', temp / 'golden.png', size, 3)['box'], [1, 1, 2, 2])
            Image.new('RGB', (3, 2), (10, 20, 30)).convert('P', palette=Image.Palette.ADAPTIVE).save(temp / 'golden.png')
            Image.new('RGB', (9, 6), (10, 20, 30)).save(temp / 'frame.png')
            self.assertTrue(library.compare_golden(temp / 'frame.png', temp / 'golden.png', size, 3)['ok'])
            Image.new('RGB', (4, 2)).save(temp / 'golden.png')
            self.assertEqual(library.compare_golden(temp / 'frame.png', temp / 'golden.png', size, 3)['error'],
                             'golden is 4x2, expected 1x 3x2')
            (temp / 'frame.png').write_bytes(b'not a png')
            self.assertIn('unreadable frame', library.compare_golden(temp / 'frame.png', None, size, 3)['error'])


STARTERS = {'scene': 'starter-scene-loop', 'music': 'starter-music', 'assets': 'starter-assets'}


def starter_copy_files(source):
    """The files `pixelate new` keeps: everything but generated outputs and out/ other than out/golden."""
    manifest = json.loads((source / 'piece.json').read_text(encoding='utf-8'))
    generated = {o.get('frame') or o['file'] for o in manifest['outputs']}
    return {name for name in snapshot(source) if name not in generated and
            (not name.startswith('out/') or name.startswith('out/golden/'))}


class NewCommand(unittest.TestCase):
    """`pixelate new KIND DIR` copies a library starter into a new piece; it is not remix."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)

    def test_each_kind_copies_its_starter_as_a_valid_piece_named_by_its_folder(self):
        for kind, starter in STARTERS.items():
            with self.subTest(kind=kind):
                dest = self.work / 'pieces' / f'my-{kind}'
                result = pixelate('new', kind, str(dest.relative_to(self.work)), cwd=self.work, env=caller_env())
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'as a copy of library/{starter}', result.stdout)
                self.assertNotIn('remix', result.stdout)
                source = REPO / 'library' / starter
                manifest = library.validate(dest)
                self.assertEqual(manifest['id'], f'my-{kind}')
                self.assertEqual(manifest, {**json.loads((source / 'piece.json').read_text(encoding='utf-8')),
                                            'id': f'my-{kind}'})
                copied = snapshot(dest)
                expected = starter_copy_files(source)
                self.assertEqual(set(copied), expected)
                self.assertTrue(any(name.startswith('out/golden/') for name in expected) or kind == 'assets')
                for name in expected - {'piece.json'}:
                    self.assertEqual(copied[name], snapshot(source)[name], name)
        self.assertEqual(sorted(p.name for p in (self.work / 'pieces').iterdir()), ['my-assets', 'my-music', 'my-scene'])

    def test_run_data_and_stale_generated_outputs_are_not_copied(self):
        fake = self.work / 'library'
        shutil.copytree(REPO / 'library' / 'starter-scene-loop', fake / 'starter-scene-loop')
        source = fake / 'starter-scene-loop'
        for name in ('.pixelate/runs.jsonl', 'out/t0000.00.png', 'out/stray.png', 'dist/index.html',
                     'shots/t0.png', 'render-report.json', '__pycache__/scene.cpython-312.pyc'):
            (source / name).parent.mkdir(parents=True, exist_ok=True)
            (source / name).write_bytes(b'stale')
        spec = importlib.util.spec_from_file_location('pixelate_cli', TOOLS / 'cli.py')
        assert spec is not None and spec.loader is not None
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        dest = self.work / 'fresh'
        with mock.patch.dict(sys.modules, library=library), mock.patch.object(library, 'DEFAULT_LIBRARY', fake), \
                contextlib.redirect_stdout(io.StringIO()):
            cli.new('scene', str(dest))
        self.assertEqual(set(snapshot(dest)), starter_copy_files(REPO / 'library' / 'starter-scene-loop'))
        self.assertEqual(library.validate(dest)['id'], 'fresh')

    def test_unsafe_or_occupied_destinations_are_refused_untouched(self):
        (self.work / 'busy').mkdir()
        (self.work / 'busy' / 'keep.txt').write_text('mine', encoding='utf-8')
        (self.work / 'target').mkdir()
        (self.work / 'linked').symlink_to(self.work / 'target')
        (self.work / 'file').write_text('mine', encoding='utf-8')
        before = snapshot(self.work)
        for name, message in (('busy', 'exists and is not an empty folder'), ('file', 'exists and is not an empty folder'),
                              ('linked', 'is a symbolic link'), ('My Scene', 'use a lowercase slug'),
                              ('.', 'use a lowercase slug')):
            with self.subTest(dest=name):
                result = pixelate('new', 'scene', name, cwd=self.work, env=caller_env())
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)
        self.assertEqual(snapshot(self.work), before)
        self.assertEqual(list((self.work / 'target').iterdir()), [])
        self.assertEqual(sorted(p.name for p in self.work.iterdir()), ['busy', 'file', 'linked', 'target'])
        (self.work / 'empty').mkdir()
        result = pixelate('new', 'music', 'empty', cwd=self.work, env=caller_env())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(library.validate(self.work / 'empty')['id'], 'empty')

    def test_help_and_usage(self):
        for flag in ('-h', '--help'):
            with self.subTest(flag=flag):
                result = pixelate('new', flag)
                self.assertEqual(result.returncode, 0)
                self.assertIn('usage: pixelate new KIND DIR', result.stdout)
                self.assertIn('It is a plain copy', result.stdout)
                self.assertIn('alias of\n`pixelate remix STARTER DIR` once remix exists', result.stdout)
        missing = pixelate('new', 'scene')
        self.assertEqual(missing.returncode, 1)
        self.assertIn('usage: pixelate new KIND DIR', missing.stderr)
        unknown = pixelate('new', 'robot', 'robot', cwd=self.work)
        self.assertEqual(unknown.returncode, 1)
        self.assertIn('kinds: scene, music, assets', unknown.stderr)
        self.assertFalse((self.work / 'robot').exists())

    def test_new_pieces_render_in_quick_mode_without_an_exported_kit(self):
        pieces = self.work / 'pieces'
        for kind in STARTERS:
            self.assertEqual(pixelate('new', kind, str(pieces / f'new-{kind}'), env=caller_env()).returncode, 0)
        result = pixelate('library', '--library', str(pieces), 'test', '--quick', env=caller_env())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['ok'])
        kinds = {p['id']: (p['ok'], p['gate_ok'], p['kinds']) for p in report['pieces']}
        self.assertEqual(kinds, {
            'new-assets': (True, None, {'export': {'declared': 3, 'tested': 3}}),
            'new-music': (True, True, {'image': {'declared': 1, 'tested': 1}, 'audio': {'declared': 1, 'tested': 0}}),
            'new-scene': (True, True, {'image': {'declared': 2, 'tested': 2}})})


if __name__ == '__main__':
    unittest.main()
