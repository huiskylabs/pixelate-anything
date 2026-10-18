"""`pixelate find`, `pixelate library` and `pixelate render` on synthetic pieces; trusted fixture code only."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image, PngImagePlugin

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / 'tools'
spec = importlib.util.spec_from_file_location('piece_library', TOOLS / 'library.py')
assert spec is not None and spec.loader is not None
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)

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


def write_canary(frame, path):
    """Copy frame's pixels to path with different bytes; following a link to it would pass every check."""
    info = PngImagePlugin.PngInfo()
    info.add_text('canary', 'outside the piece')
    with Image.open(frame) as image:
        image.save(path, pnginfo=info)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(root, data):
    (root / 'piece.json').write_text(json.dumps(data), encoding='utf-8')


def pixelate(*args, cwd=None):
    return subprocess.run([sys.executable, str(REPO / 'pixelate'), *args], capture_output=True, text=True, cwd=cwd)


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
        for image_run, error in ((f'rm out/a.png && {link} out/a.png', 'unsafe frame: out/a.png'),
                                 (f'{link} out/a-actor.png', 'unsafe gate input: out/a-actor.png')):
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


if __name__ == '__main__':
    unittest.main()
