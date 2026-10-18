"""`pixelate remix`: copy, baseline render of the unedited copy, REMIX.md; trusted fixture code and checked-in pieces only."""
import contextlib
import hashlib
import importlib.util
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

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('remix', TOOLS / 'remix.py')
assert spec is not None and spec.loader is not None
remix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remix)
library = remix.library  # the module remix calls, so a patch here applies to it

# A frame that passes the arcade gate: a dark night, a lit block and a foreground of scattered stones.
DRAW = '''from PIL import Image
im = Image.new('RGB', (64, 48), (8, 10, 18))
im.paste((70, 40, 30), (0, 30, 64, 48))
for x in range(1, 64, 5):
    for y in range(32 + x % 3, 48, 4):
        im.paste((150, 120, 90) if (x + y) % 2 else (40, 90, 110), (x, y, x + 2, y + 2))
im.paste((150, 120, 90), (24, 8, 40, 20))
im.paste((90, 60, 40), (26, 10, 38, 18))
im.save('out/a@1x.png')
im.resize((256, 192), Image.NEAREST).save('out/a.png')
'''
SOUND = '''import pathlib
pathlib.Path('sound/tone.wav').write_bytes(b'RIFF fixture audio')
'''
# What a render or delivery leaves in a piece, and a review sidecar; none of it is copied.
RUN_DATA = ('.pixelate/runs.jsonl', 'dist/index.html', 'shots/t0.png', 'render-report.json',
            'art/__pycache__/draw.cpython-312.pyc', 'out/a.png.visual-review.json', 'out/stray.png',
            'history/a.png.visual-review.json')
KEPT = {'piece.json', 'brief.md', 'art/draw.py', 'sound/make.py', 'out/golden/a.png', 'media/thumb.png',
        'media/contact.png', 'history/notes.md'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(Path(root).rglob('*'))
            if p.is_file() and not p.is_symlink()}


def make_piece(library_root, piece_id='harbour', status='study'):
    """A piece at any status, with the evidence `accepted` requires, a stale frame, run data and a review sidecar."""
    root = Path(library_root) / piece_id
    for folder in ('art', 'sound', 'out/golden', 'media', 'history'):
        (root / folder).mkdir(parents=True)
    (root / 'art' / 'draw.py').write_text(DRAW, encoding='utf-8')
    (root / 'sound' / 'make.py').write_text(SOUND, encoding='utf-8')
    subprocess.run([sys.executable, 'art/draw.py'], cwd=root, check=True)
    (root / 'out' / 'a@1x.png').rename(root / 'out' / 'golden' / 'a.png')
    (root / 'brief.md').write_text('# Harbour\n\nA harbour wall at night.\n', encoding='utf-8')
    (root / 'history' / 'notes.md').write_text('Approved by the user on the base frame.\n', encoding='utf-8')
    for name in ('media/thumb.png', 'media/contact.png'):
        (root / name).write_bytes(b'fixture media')
    for name in RUN_DATA:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(b'stale')
    data = {'schema': 1, 'id': piece_id, 'title': 'Harbour', 'summary': 'A harbour wall at night.',
            'request': 'a harbour wall at night', 'status': status, 'mode': 'scene', 'runtime': 'script',
            'tags': {'subject': ['harbour', 'wall'], 'setting': ['night'], 'camera': 'side', 'style': 'arcade',
                     'era': 'none', 'motion': 'stills', 'sound': 'sfx'},
            'canvas': {'w': 64, 'h': 48, 'scale': 4},
            'outputs': [{'name': 'a', 'kind': 'image', 'run': f'{sys.executable} art/draw.py', 'frame': 'out/a.png',
                         'golden': 'out/golden/a.png', 'style': 'arcade', 'scale': 4, 'brief': 'brief.md'},
                        {'name': 'tone', 'kind': 'audio', 'run': f'{sys.executable} sound/make.py',
                         'file': 'sound/tone.wav'}],
            'anatomy': [{'file': 'art/draw.py', 'draws': 'the harbour wall | stones', 'change_for': 'the setting'},
                        {'file': 'sound/make.py', 'draws': 'the tone', 'change_for': 'the sound'}],
            'knobs': {'time': {'values': ['night', 'dusk'], 'default': 'night', 'edits': 'art/draw.py'},
                      'seed': {'type': 'int', 'default': 7, 'edits': 'art/draw.py'}},
            'provenance': {'made': '2026-10-17', 'by': 'fixture author, from fixture photo 42'},
            'media': {'thumb': 'media/thumb.png', 'contact': 'media/contact.png'},
            'review': {'notes': 'history/notes.md', 'approved_by': 'user',
                       'record': 'history/a.png.visual-review.json' if status == 'reviewed' else None},
            'lineage': {'remixed_from': None}, 'license': 'MIT'}
    save(root, data)
    return root, data


def save(root, data):
    (root / 'piece.json').write_text(json.dumps(data), encoding='utf-8')


def pixelate(*args, cwd=None):
    return subprocess.run([sys.executable, str(REPO / 'pixelate'), *args], capture_output=True, text=True, cwd=cwd)


class Fixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.library = self.temp / 'library'
        self.library.mkdir()
        self.work = self.temp / 'work'
        self.work.mkdir()
        self.piece, self.data = make_piece(self.library)
        self.dest = self.work / 'temple'

    def remix(self, piece='harbour', dest=None, request='an old temple at night', *extra):
        """(exit status, stdout, stderr) of `pixelate remix` in this process."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = remix.main([piece, str(dest or self.dest), '--request', request, '--library', str(self.library),
                               *extra])
        return code, out.getvalue(), err.getvalue()

    def baseline(self, dest=None):
        return json.loads((Path(dest or self.dest) / remix.BASELINE).read_text(encoding='utf-8'))

    def assertNothingCreated(self):
        self.assertEqual(list(self.work.iterdir()), [])


class Copy(Fixture):
    def test_copy_keeps_sources_goldens_media_and_history_but_no_run_data_or_review_sidecar(self):
        before = snapshot(self.piece)
        code, out, err = self.remix()
        self.assertEqual(code, 0, err)
        self.assertIn('created', out)
        self.assertEqual(set(snapshot(self.dest)), KEPT | {'REMIX.md', remix.BASELINE})
        for name in KEPT - {'piece.json'}:
            self.assertEqual(snapshot(self.dest)[name], before[name], name)
        self.assertEqual(snapshot(self.piece), before)
        self.assertEqual([p.name for p in self.work.iterdir()], ['temple'])

    def test_manifest_records_request_lineage_and_an_unreviewed_status(self):
        self.assertEqual(self.remix(request='an old temple\nat night')[0], 0)
        manifest = library.validate(self.dest)
        self.assertEqual((manifest['id'], manifest['request'], manifest['status'], manifest['lineage']),
                         ('temple', 'an old temple\nat night', 'study', {'remixed_from': 'harbour'}))
        self.assertNotIn('review', manifest)
        self.assertEqual(manifest['license'], 'MIT')
        self.assertIn('base provenance 2026-10-17: fixture author, from fixture photo 42', manifest['provenance']['by'])
        unchanged = {k: v for k, v in self.data.items()
                     if k not in ('id', 'request', 'status', 'lineage', 'provenance', 'review')}
        self.assertEqual({k: manifest[k] for k in unchanged}, unchanged)

    def test_accepted_and_reviewed_bases_are_downgraded_to_an_unreviewed_study(self):
        # A real reviewed record binds the base's exact bytes; the binding is library.validate's concern.
        with mock.patch.object(library, 'review_binding', lambda root, manifest: None):
            for status in ('accepted', 'reviewed'):
                with self.subTest(status=status):
                    make_piece(self.library, status, status)
                    self.assertEqual(library.validate(self.library / status)['status'], status)
                    dest = self.work / f'from-{status}'
                    code, out, err = self.remix(status, dest)
                    self.assertEqual(code, 0, err)
                    self.assertIn(f'status study, unreviewed) as a remix of {status} (status {status})', out)
                    manifest = library.validate(dest)
                    self.assertEqual(manifest['status'], 'study')
                    self.assertNotIn('review', manifest)
                    self.assertFalse(any(name.endswith('.visual-review.json') for name in snapshot(dest)))
                    baseline = self.baseline(dest)
                    self.assertEqual((baseline['status'], baseline['base']['status']), ('study', status))
                    text = (dest / 'REMIX.md').read_text(encoding='utf-8')
                    self.assertIn(f'Base status: `{status}`; approved by user', text)
                    self.assertIn('This copy: status `study`', text)
                    self.assertIn('approval do not carry over', text)

    def test_a_starter_stays_a_starter_and_must_pass_its_gate(self):
        save(self.piece, {**self.data, 'status': 'starter'})
        code, out, err = self.remix()
        self.assertEqual(code, 0, err)
        self.assertEqual(library.validate(self.dest)['status'], 'starter')
        self.assertTrue(self.baseline()['test']['gate_ok'])
        shutil.rmtree(self.dest)
        outputs = [{**self.data['outputs'][0], 'style': 'pastel-cell'}, self.data['outputs'][1]]
        save(self.piece, {**self.data, 'status': 'starter', 'outputs': outputs})
        code, out, err = self.remix()
        self.assertEqual(code, 1)
        self.assertIn('did not pass its baseline render; nothing was created', err)
        self.assertNothingCreated()

    def test_remix_md_has_request_base_anatomy_knobs_plan_and_checklist(self):
        self.assertEqual(self.remix(request='an old temple\nat night')[0], 0)
        text = (self.dest / 'REMIX.md').read_text(encoding='utf-8')
        for expected in ('> an old temple\n> at night', '## Base: harbour (Harbour)', 'A harbour wall at night.',
                         'Base status: `study`; approved by user.', 'License: `MIT` as the base declares it',
                         'copied, not verified', 'fixture author, from fixture photo 42',
                         '| `art/draw.py` | the harbour wall \\| stones | the setting |',
                         '| time | night, dusk | night | `art/draw.py` |', '| seed | int | 7 | `art/draw.py` |',
                         '`pixelate render` does not apply knobs yet', '| subject | harbour, wall |  |  |',
                         '| camera | side |  |  |', '| palette |  |  |  |', '| composition |  |  |  |',
                         '| motion | stills |  |  |', '| sound | sfx |  |  |', 'What stays:', 'What changes:',
                         '## Checklist', '- [ ] Status stays `study`', '| a | image | passed: golden match, technical gate PASS |',
                         '| tone | audio | skipped, untested (quick mode skips audio outputs) |'):
            self.assertIn(expected, text)
        self.assertIn(sha((self.dest / remix.BASELINE).read_bytes()), text)
        self.assertFalse([line for line in text.splitlines() if line != line.rstrip()])


class Baseline(Fixture):
    def test_the_baseline_renders_a_clean_temporary_copy_once(self):
        log = self.temp / 'cwd.log'
        self.data['outputs'][0]['run'] = f'pwd >> {log} && {sys.executable} art/draw.py'
        save(self.piece, self.data)
        before = snapshot(self.piece)
        self.assertEqual(self.remix()[0], 0)
        runs = log.read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(runs), 1)
        self.assertIn('pixelate-test-', runs[0])
        self.assertFalse(runs[0].startswith(str(self.work)))
        self.assertFalse((self.dest / 'out' / 'a.png').exists())
        self.assertEqual(snapshot(self.piece), before)

    def test_the_baseline_binds_the_copied_bytes_and_the_rendered_frame(self):
        code, out, err = self.remix()
        self.assertEqual(code, 0, err)
        data = (self.dest / remix.BASELINE).read_bytes()
        self.assertIn(f'(sha256 {sha(data)})', out)
        baseline = json.loads(data)
        copied = {name: digest for name, digest in snapshot(self.dest).items()
                  if name not in ('REMIX.md', remix.BASELINE)}
        self.assertEqual(baseline['files'], copied)
        self.assertEqual(baseline['files_sha256'], sha(json.dumps(copied, sort_keys=True).encode()))
        # The frame the baseline hashed is the one a fresh run of the copied program draws.
        fresh = self.temp / 'fresh'
        shutil.copytree(self.dest, fresh)
        subprocess.run([sys.executable, 'art/draw.py'], cwd=fresh, check=True)
        outputs = {o['name']: o for o in baseline['test']['outputs']}
        self.assertEqual(outputs['a']['sha256'], sha((fresh / 'out' / 'a.png').read_bytes()))
        self.assertEqual((outputs['a']['status'], outputs['a']['golden'], outputs['a']['gate_ok']),
                         ('passed', {'ok': True, 'pixels': 0}, True))
        self.assertEqual(baseline['untested'], [{'name': 'tone', 'kind': 'audio',
                                                 'reason': 'quick mode skips audio outputs'}])
        self.assertEqual((baseline['quick'], baseline['piece'], baseline['request'], baseline['base']['id']),
                         (True, 'temple', 'an old temple at night', 'harbour'))
        self.assertTrue(baseline['test']['ok'])

    def test_a_no_op_failing_or_drifting_command_creates_nothing(self):
        self.assertTrue((self.piece / 'out' / 'a.png').is_file())  # a stale frame cannot pass
        drifted = self.temp / 'drifted.png'
        shutil.copy(self.piece / 'out' / 'golden' / 'a.png', drifted)
        from PIL import Image
        with Image.open(drifted) as image:
            image = image.convert('RGB')
            image.putpixel((0, 0), (255, 0, 0))
            image.save(drifted)
        for case, change, message in (
                ('no-op', lambda: self.data['outputs'][0].update(run='true'), 'not produced: out/a.png'),
                ('fails', lambda: self.data['outputs'][0].update(run=f'{sys.executable} -c "raise SystemExit(3)"'),
                 'run failed'),
                ('drift', lambda: shutil.copy(drifted, self.piece / 'out' / 'golden' / 'a.png'),
                 '1 of 3072 1x pixels differ from the golden')):
            with self.subTest(case=case):
                piece, self.data = make_piece(self.library, f'piece-{case}')
                self.piece = piece
                change()
                save(piece, self.data)
                code, out, err = self.remix(f'piece-{case}')
                self.assertEqual(code, 1, out)
                self.assertIn('baseline of the unedited copy: FAILED', err)
                self.assertIn(message, err)
                self.assertIn('nothing was created', err)
                self.assertNothingCreated()

    def test_a_study_gate_failure_is_a_diagnostic_never_gate_legal(self):
        self.data['outputs'][0]['style'] = 'pastel-cell'
        save(self.piece, self.data)
        code, out, err = self.remix()
        self.assertEqual(code, 0, err)
        self.assertIn('NOT gate-legal and not approved', out)
        self.assertIn('gate_ok: false: rendered and matched its goldens, but not gate-legal', out)
        self.assertNotIn('gate PASS', out)
        baseline = self.baseline()
        image = baseline['test']['outputs'][0]
        self.assertEqual((image['status'], image['gate_ok'], image['golden']['ok']), ('passed', False, True))
        self.assertEqual(image['diagnostic'], 'study: the technical gate failed; reported, not blocking')
        self.assertIs(baseline['test']['gate_ok'], False)
        text = (self.dest / 'REMIX.md').read_text(encoding='utf-8')
        self.assertIn('it is NOT gate-legal and not approved', text)
        self.assertNotIn('technical gate PASS', text)

    def test_a_copy_changed_during_its_baseline_creates_nothing(self):
        real = library.test_piece
        def tampering(root, quick=False, timeout=300):
            (Path(root) / 'art' / 'draw.py').write_text(DRAW + '# edited\n', encoding='utf-8')
            return real(root, quick, timeout)
        with mock.patch.object(library, 'test_piece', tampering):
            code, out, err = self.remix()
        self.assertEqual(code, 1)
        self.assertIn('FAILED: the copy changed while its baseline rendered', err)
        self.assertNothingCreated()

    def test_an_error_during_the_baseline_leaves_nothing_behind(self):
        with mock.patch.object(library, 'test_piece', side_effect=RuntimeError('interrupted')), \
                self.assertRaises(RuntimeError):
            self.remix()
        self.assertNothingCreated()


class Destinations(Fixture):
    def setUp(self):
        super().setUp()
        self.marker = self.temp / 'EXECUTED'
        self.data['outputs'][0]['run'] = f'touch {self.marker} && ' + self.data['outputs'][0]['run']
        save(self.piece, self.data)

    def test_occupied_or_unsafe_destinations_are_refused_untouched_without_running_anything(self):
        (self.work / 'busy').mkdir()
        (self.work / 'busy' / 'keep.txt').write_text('mine', encoding='utf-8')
        (self.work / 'target').mkdir()
        (self.work / 'linked').symlink_to(self.work / 'target')
        (self.work / 'file').write_text('mine', encoding='utf-8')
        before = snapshot(self.work)
        for name, message in (('busy', 'exists and is not an empty folder'),
                              ('file', 'exists and is not an empty folder'), ('linked', 'is a symbolic link'),
                              ('My Temple', 'use a lowercase slug'), ('busy/../busy', 'exists and is not an empty folder')):
            with self.subTest(dest=name):
                code, out, err = self.remix(dest=self.work / name)
                self.assertEqual(code, 2)
                self.assertIn(message, err)
        for name in ('.', '..'):
            with self.subTest(dest=name):
                result = pixelate('remix', 'harbour', name, '--request', 'a temple', '--library', str(self.library),
                                  cwd=self.work / 'target')
                self.assertEqual(result.returncode, 2)
                self.assertIn('use a lowercase slug', result.stderr)
        self.assertEqual(snapshot(self.work), before)
        self.assertEqual(list((self.work / 'target').iterdir()), [])
        self.assertEqual(sorted(p.name for p in self.work.iterdir()), ['busy', 'file', 'linked', 'target'])
        self.assertFalse(self.marker.exists())

    def test_an_empty_folder_becomes_the_piece(self):
        self.dest.mkdir()
        self.assertEqual(self.remix()[0], 0)
        self.assertEqual(library.validate(self.dest)['id'], 'temple')

    def test_a_destination_inside_the_library_is_refused(self):
        for dest in (self.library / 'temple', self.piece / 'temple', self.library):
            with self.subTest(dest=dest):
                code, out, err = self.remix(dest=dest)
                self.assertEqual(code, 2)
                self.assertIn('inside the library', err)
        self.assertEqual(sorted(p.name for p in self.library.iterdir()), ['harbour'])
        self.assertFalse(self.marker.exists())

    def test_links_unknown_and_malformed_pieces_are_refused(self):
        (self.temp / 'outside.txt').write_text('outside', encoding='utf-8')
        (self.piece / 'history' / 'link.txt').symlink_to(self.temp / 'outside.txt')
        code, out, err = self.remix()
        self.assertEqual(code, 2)
        self.assertIn('symlink in piece', err)
        (self.piece / 'history' / 'link.txt').unlink()
        shutil.copytree(self.piece, self.temp / 'elsewhere' / 'harbour-link')
        (self.library / 'harbour-link').symlink_to(self.temp / 'elsewhere' / 'harbour-link')
        for piece, message in (('harbour-link', 'unsafe piece directory'), ('missing', 'unknown piece'),
                               ('../harbour', 'expected lowercase slug'), ('Harbour', 'expected lowercase slug')):
            with self.subTest(piece=piece):
                code, out, err = self.remix(piece)
                self.assertEqual(code, 2)
                self.assertIn(message, err)
        self.assertNothingCreated()
        self.assertFalse(self.marker.exists())
        code, out, err = self.remix(request='   ')
        self.assertEqual(code, 2)
        self.assertIn('request: expected nonempty string', err)


class Command(unittest.TestCase):
    def test_help_names_only_what_remix_does(self):
        result = pixelate('remix', '--help')
        self.assertEqual(result.returncode, 0)
        for expected in ('usage: pixelate remix', '--request', '--library', '--timeout', '--json',
                         'without a sandbox', 'nothing is created'):
            self.assertIn(expected, result.stdout)
        for future in ('--set', 'deliver', 'distance', '--critique'):
            self.assertNotIn(future, result.stdout)
        self.assertIn('pixelate remix PIECE DIR --request', pixelate('--help').stdout)

    def test_usage_and_lookup_errors_exit_2(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = pixelate('remix', 'market-day', 'temple', cwd=temp)
            self.assertEqual(missing.returncode, 2)
            self.assertIn('--request', missing.stderr)
            unknown = pixelate('remix', 'no-such-piece', 'temple', '--request', 'a temple', cwd=temp)
            self.assertEqual(unknown.returncode, 2)
            self.assertIn('unknown piece', unknown.stderr)
            self.assertEqual(os.listdir(temp), [])


class MigratedPieces(unittest.TestCase):
    """Real checked-in pieces, remixed into a temporary folder with their actual dependencies."""

    def test_lantern_isle_market_day_and_a_starter_baseline_in_a_temporary_destination(self):
        expected = {'lantern-isle': ('study', True, {'image': {'declared': 4, 'tested': 4}}),
                    'market-day': ('study', False, {'image': {'declared': 2, 'tested': 2},
                                                    'audio': {'declared': 1, 'tested': 0}}),
                    'starter-scene-loop': ('starter', True, {'image': {'declared': 2, 'tested': 2}})}
        with tempfile.TemporaryDirectory() as temp:
            for piece, (status, gate_ok, kinds) in expected.items():
                with self.subTest(piece=piece):
                    source = REPO / 'library' / piece
                    before = snapshot(source)
                    dest = Path(temp) / f'remix-of-{piece}'
                    result = pixelate('remix', piece, str(dest), '--request', 'a lighthouse keeper at dawn', '--json')
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    baseline = json.loads(result.stdout)
                    self.assertEqual(baseline['sha256'], sha((dest / remix.BASELINE).read_bytes()))
                    self.assertEqual((baseline['status'], baseline['test']['gate_ok'], baseline['test']['kinds']),
                                     (status, gate_ok, kinds))
                    self.assertTrue(baseline['test']['ok'])
                    manifest = library.validate(dest)
                    self.assertEqual((manifest['id'], manifest['status'], manifest['lineage']),
                                     (dest.name, status, {'remixed_from': piece}))
                    self.assertEqual(baseline['files'], {name: digest for name, digest in snapshot(dest).items()
                                                         if name not in ('REMIX.md', remix.BASELINE)})
                    self.assertEqual(snapshot(source), before)
                    if piece == 'market-day':
                        outputs = {o['name']: o for o in baseline['test']['outputs']}
                        self.assertEqual((outputs['b']['status'], outputs['b']['gate_ok']), ('passed', False))
                        self.assertIn('diagnostic', outputs['b'])
                        self.assertEqual(outputs['sample']['status'], 'skipped')
                        self.assertIn('NOT gate-legal and not approved', (dest / 'REMIX.md').read_text(encoding='utf-8'))
                        self.assertFalse((dest / 'out' / '08-a.png').exists())


if __name__ == '__main__':
    unittest.main()
