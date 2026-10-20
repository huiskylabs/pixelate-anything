"""`knobs()` (tools/piece.py) and `pixelate render DIR --set`, on a synthetic script piece; trusted fixture code only.
Engine and pack pieces: tests/test_runtime_knobs.py."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import library  # noqa: E402
import piece  # noqa: E402
import render  # noqa: E402

# Draws the harbour frame of test_library_runtime with knobs: `time` colours the lit block, `seed` moves it.
# Every variant passes the arcade gate. It records what knobs() returned and the PIXELATE_KNOBS it saw.
DRAW = '''import json, os
import colorlib
from PIL import Image
from piece import knobs
k = knobs()
lit = {'night': (150, 120, 90), 'dusk': (200, 120, 70)}[k['time']]
x0 = 16 + 2 * (k['seed'] % 8)
im = Image.new('RGB', (64, 48), (8, 10, 18))
im.paste((70, 40, 30), (0, 30, 64, 48))
for x in range(1, 64, 5):
    for y in range(32 + x % 3, 48, 4):
        im.paste((150, 120, 90) if (x + y) % 2 else (40, 90, 110), (x, y, x + 2, y + 2))
im.paste(lit, (x0, 8, x0 + 16, 20))
im.paste((90, 60, 40), (x0 + 2, 10, x0 + 14, 18))
assert colorlib
im.save('out/a@1x.png')
im.resize((256, 192), Image.NEAREST).save('out/a.png')
with open('out/seen.json', 'w') as fh:
    json.dump({'knobs': k, 'env': os.environ.get('PIXELATE_KNOBS')}, fh)
'''
KNOBS = {'time': {'values': ['night', 'dusk'], 'default': 'night', 'edits': 'art/draw.py'},
         'seed': {'type': 'int', 'default': 0, 'edits': 'art/draw.py'}}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def pixelate(*args, env=None):
    return subprocess.run([sys.executable, str(REPO / 'pixelate'), *args], capture_output=True, text=True, env=env)


def make_piece(library_root, runtime='script'):
    """A study script piece with two knobs whose 1x golden is the frame its defaults draw."""
    root = Path(library_root) / 'harbour'
    for folder in ('art', 'out/golden'):
        (root / folder).mkdir(parents=True)
    (root / 'art' / 'draw.py').write_text(DRAW, encoding='utf-8')
    data = {'schema': 1, 'id': 'harbour', 'title': 'Harbour', 'summary': 'A harbour wall at night.',
            'request': 'a harbour wall at night', 'status': 'study', 'mode': 'scene', 'runtime': runtime,
            'tags': {'subject': ['harbour', 'wall'], 'setting': ['night'], 'camera': 'side', 'style': 'arcade',
                     'era': 'none', 'motion': 'stills', 'sound': 'none'},
            'canvas': {'w': 64, 'h': 48, 'scale': 4},
            'outputs': [{'name': 'a', 'kind': 'image', 'run': f'{sys.executable} art/draw.py', 'frame': 'out/a.png',
                         'golden': 'out/golden/a.png', 'style': 'arcade', 'scale': 4}],
            'anatomy': [{'file': 'art/draw.py', 'draws': 'the harbour wall', 'change_for': 'the setting'}],
            'knobs': KNOBS, 'provenance': {'made': '2026-10-18', 'by': 'fixture author'}, 'license': 'MIT'}
    (root / 'piece.json').write_text(json.dumps(data), encoding='utf-8')
    (root / 'out' / 'golden' / 'a.png').write_bytes(b'')       # the program draws the real one below
    env = {key: value for key, value in os.environ.items() if key != piece.ENV}
    subprocess.run([sys.executable, 'art/draw.py'], cwd=root, check=True,
                   env=dict(env, PYTHONPATH=str(REPO / 'tools')))
    (root / 'out' / 'a@1x.png').replace(root / 'out' / 'golden' / 'a.png')
    (root / 'out' / 'seen.json').unlink()
    return root, data


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)

    def knob_file(self, content, name='knobs.json', mode=0o600):
        path = self.temp / name
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding='utf-8')
        path.chmod(mode)
        return path


class ParseSets(unittest.TestCase):
    SPEC = {'time': {'values': ['day', 'dusk'], 'default': 'day', 'edits': 'a.py'},
            'seed': {'type': 'int', 'default': 17, 'edits': 'a.py'},
            'lit': {'values': [True, False], 'default': False, 'edits': 'a.py'},
            'zoom': {'values': [1, 0.5], 'default': 1, 'edits': 'a.py'}}

    def test_values_are_typed_by_the_manifest_and_merged_over_the_defaults(self):
        chosen = piece.parse_sets(self.SPEC, ['time=dusk', 'seed=-4', 'lit=true', 'zoom=0.5'])
        self.assertEqual(chosen, {'time': 'dusk', 'seed': -4, 'lit': True, 'zoom': 0.5})
        self.assertIs(type(chosen['zoom']), float)
        self.assertEqual(piece.merge(self.SPEC, {'seed': 4}), {'time': 'day', 'seed': 4, 'lit': False, 'zoom': 1})
        self.assertEqual(piece.parse_sets(self.SPEC, []), {})
        self.assertEqual(piece.parse_sets(self.SPEC, ['seed=0', 'zoom=1']), {'seed': 0, 'zoom': 1})

    def test_unknown_malformed_duplicate_and_out_of_range_sets_are_rejected(self):
        for sets, message in ((['time'], 'expected NAME=VALUE'), (['=dusk'], 'expected NAME=VALUE'),
                              (['season=winter'], 'no such knob; the piece declares lit, seed, time, zoom'),
                              (['time=dusk', 'time=day'], 'set more than once'),
                              (['time=night'], 'expected one of day, dusk'), (['time=Dusk'], 'expected one of'),
                              (['lit=True'], 'expected one of true, false'), (['zoom=1.0'], 'expected one of 1, 0.5'),
                              (['seed=1.5'], 'expected a decimal integer'), (['seed=+3'], 'expected a decimal integer'),
                              (['seed= 3'], 'expected a decimal integer'), (['seed=1_0'], 'expected a decimal integer'),
                              (['seed=07'], 'expected a decimal integer'), (['seed=-0'], 'expected a decimal integer'),
                              (['seed='], 'expected a decimal integer'),
                              ([f'seed={2 ** 53}'], 'expected an integer from'),
                              ([f'seed=-{2 ** 53}'], 'expected an integer from')):
            with self.subTest(sets=sets):
                with self.assertRaises(piece.KnobError) as caught:
                    piece.parse_sets(self.SPEC, sets)
                self.assertIn(message, str(caught.exception))
        self.assertEqual(piece.parse_sets(self.SPEC, [f'seed={2 ** 53 - 1}']), {'seed': 2 ** 53 - 1})
        with self.assertRaises(piece.KnobError) as caught:
            piece.parse_sets({}, ['seed=1'])
        self.assertIn('the piece declares none', str(caught.exception))

    def test_a_spelling_shared_by_two_declared_values_is_ambiguous(self):
        spec = {'mode': {'values': ['true', True], 'default': True, 'edits': 'a.py'}}
        with self.assertRaises(piece.KnobError) as caught:
            piece.parse_sets(spec, ['mode=true'])
        self.assertIn('matches more than one declared value', str(caught.exception))


class KnobsHelper(Temp):
    """knobs() in the program: the manifest's defaults, or the checked values of a safe PIXELATE_KNOBS file."""

    def setUp(self):
        super().setUp()
        self.root, self.data = make_piece(self.temp / 'library')

    def knobs(self, path=None):
        env = {piece.ENV: str(path)} if path is not None else {}
        with mock.patch.dict(os.environ, env):
            if path is None:
                os.environ.pop(piece.ENV, None)
            return piece.knobs(self.root)

    def test_defaults_without_the_variable_and_values_from_a_safe_file(self):
        self.assertEqual(self.knobs(), {'time': 'night', 'seed': 0})
        self.assertEqual(self.knobs(''), {'time': 'night', 'seed': 0})
        self.assertEqual(self.knobs(self.knob_file({'seed': 5})), {'time': 'night', 'seed': 5})
        self.assertEqual(self.knobs(self.knob_file({'time': 'dusk', 'seed': -2})), {'time': 'dusk', 'seed': -2})

    def test_unsafe_or_invalid_files_are_rejected(self):
        good = self.knob_file({'time': 'dusk'})
        link = self.temp / 'link.json'
        link.symlink_to(good)
        folder = self.temp / 'folder'
        folder.mkdir()
        fifo = self.temp / 'fifo'
        os.mkfifo(fifo)
        cases = ((link, 'missing, a link or unreadable'), (self.temp / 'absent.json', 'missing, a link or unreadable'),
                 (folder, 'not a regular file'), (fifo, 'not a regular file'),
                 ('knobs.json', 'expected an absolute path'),
                 (self.knob_file({'time': 'dusk'}, 'shared.json', 0o622), 'writable by no one else'),
                 (self.knob_file('x' * (piece.MAX_SET + 1), 'big.json'), 'larger than'),
                 (self.knob_file('{"time": "dusk"', 'cut.json'), 'invalid JSON'),
                 (self.knob_file('{"seed": NaN}', 'nan.json'), 'nonfinite JSON number'),
                 (self.knob_file('{"seed": 1, "seed": 2}', 'twice.json'), 'duplicate key seed'),
                 (self.knob_file(['time', 'dusk'], 'list.json'), 'expected a JSON object'),
                 (self.knob_file({'season': 'winter'}, 'unknown.json'), 'no such knob season'),
                 (self.knob_file({'time': 'noon'}, 'value.json'), 'knob time: "noon" is not one of'),
                 (self.knob_file({'seed': '3'}, 'string.json'), 'knob seed: expected an integer'),
                 (self.knob_file({'seed': True}, 'bool.json'), 'knob seed: expected an integer'),
                 (self.knob_file({'seed': 2 ** 53}, 'huge.json'), 'knob seed: expected an integer'))
        for path, message in cases:
            with self.subTest(path=str(path)):
                with self.assertRaises(piece.KnobError) as caught:
                    self.knobs(path)
                self.assertIn(message, str(caught.exception))

    def test_an_invalid_manifest_knob_is_rejected_before_any_value(self):
        self.data['knobs'] = {'time': {'values': ['night'], 'default': 'noon', 'edits': 'art/draw.py'}}
        (self.root / 'piece.json').write_text(json.dumps(self.data), encoding='utf-8')
        with self.assertRaises(piece.KnobError) as caught:
            self.knobs()
        self.assertIn('matching default', str(caught.exception))
        (self.root / 'piece.json').unlink()
        with self.assertRaises(piece.KnobError):
            self.knobs()

    def set_seed_default(self, default):
        self.data['knobs'] = dict(KNOBS, seed={'type': 'int', 'default': default, 'edits': 'art/draw.py'})
        (self.root / 'piece.json').write_text(json.dumps(self.data), encoding='utf-8')

    def test_an_int_default_is_held_to_the_bound_of_set_values_by_validate_and_knobs(self):
        limit = piece.INT_LIMIT
        for default in (limit, -limit):
            with self.subTest(default=default):
                self.set_seed_default(default)
                self.assertEqual(library.validate(self.root)['knobs']['seed']['default'], default)
                self.assertEqual(self.knobs()['seed'], default)
        for default in (limit + 1, -limit - 1, 2 ** 60, True, False, 1.0, '3'):
            with self.subTest(default=default):
                self.set_seed_default(default)
                with self.assertRaises(library.LibraryError):
                    library.validate(self.root)
                with self.assertRaises(piece.KnobError) as caught:
                    self.knobs()
                self.assertIn('seed', str(caught.exception))

    def test_piece_env_never_passes_an_inherited_value(self):
        with mock.patch.dict(os.environ, {piece.ENV: '/inherited/knobs.json'}):
            self.assertNotIn(piece.ENV, render.piece_env())
            self.assertEqual(render.piece_env('/render/knobs.json')[piece.ENV], '/render/knobs.json')


class RenderSet(Temp):
    """`pixelate render DIR --set` on a script piece whose program reads knobs()."""

    def setUp(self):
        super().setUp()
        self.library = self.temp / 'library'
        self.root, self.data = make_piece(self.library)
        self.env = {key: value for key, value in os.environ.items() if key not in (piece.ENV, 'PIXELATE_NO_LOG')}

    def render(self, *args, env=None):
        result = pixelate('render', str(self.root), '--json', *args, env=env or self.env)
        return result, (json.loads(result.stdout) if result.stdout else [])

    def logged(self):
        return json.loads((self.root / '.pixelate' / 'runs.jsonl').read_text().splitlines()[-1])

    def seen(self):
        return json.loads((self.root / 'out' / 'seen.json').read_text())

    def sources(self):
        return {path: digest for path, digest in tree(self.root).items()
                if path in ('piece.json', 'art/draw.py', 'out/golden/a.png')}

    def test_two_variants_render_distinct_deterministic_gate_passing_frames(self):
        sources = self.sources()
        result, default = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('knobs', default[0])
        self.assertNotIn('knobs', self.logged())
        self.assertEqual(self.seen(), {'knobs': {'time': 'night', 'seed': 0}, 'env': None})
        hashes = {}
        for sets in (('time=dusk',), ('time=dusk', 'seed=3')):
            for attempt in range(2):
                with self.subTest(sets=sets, attempt=attempt):
                    args = [arg for value in sets for arg in ('--set', value)]
                    result, records = self.render(*args)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    image = records[0]
                    self.assertTrue(image['gate']['ok'], image['gate'])
                    chosen = dict(value.split('=') for value in sets)
                    chosen = {k: int(v) if k == 'seed' else v for k, v in chosen.items()}
                    merged = dict({'time': 'night', 'seed': 0}, **chosen)
                    file_sha = sha(json.dumps(chosen, sort_keys=True).encode('utf-8'))
                    self.assertEqual(image['knobs'], {'set': chosen, 'merged': merged, 'sha256': file_sha})
                    seen = self.seen()
                    self.assertEqual(seen['knobs'], merged)
                    # The program got render's own private file, which is gone after the render.
                    self.assertTrue(Path(seen['env']).is_absolute())
                    self.assertFalse(Path(seen['env']).exists())
                    self.assertFalse(Path(seen['env']).parent.exists())
                    self.assertFalse(str(Path(seen['env'])).startswith(str(self.root)))
                    self.assertEqual(image['sha256'], sha((self.root / 'out' / 'a.png').read_bytes()))
                    run = self.logged()
                    self.assertEqual(run['knobs'], image['knobs'])
                    self.assertEqual((run['images'][0]['sha256'], run['images'][0]['gate_ok']), (image['sha256'], True))
                    report = json.loads((self.root / 'render-report.json').read_text())
                    self.assertEqual(report[0]['knobs'], image['knobs'])
                    hashes.setdefault(sets, set()).add(image['sha256'])
        self.assertEqual([len(v) for v in hashes.values()], [1, 1])
        variants = {h for v in hashes.values() for h in v}
        self.assertEqual(len(variants | {default[0]['sha256']}), 3)
        # Nothing set is a source change: the manifest, the program and the golden are as they were.
        self.assertEqual(self.sources(), sources)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         ['.pixelate', 'art', 'out', 'piece.json', 'render-report.json'])
        self.assertEqual({p.name for p in (self.root / 'out').iterdir()} - {'a.judge.png'},
                         {'a.png', 'a@1x.png', 'golden', 'seen.json'})
        # The library test still renders the defaults and matches the golden, whatever was set before.
        tested = pixelate('library', '--library', str(self.library), 'test', 'harbour', env=self.env)
        self.assertEqual(tested.returncode, 0, tested.stdout + tested.stderr)
        output = json.loads(tested.stdout)['pieces'][0]['outputs'][0]
        self.assertEqual((output['status'], output['golden']['ok'], output['gate_ok']), ('passed', True, True))

    def test_text_output_names_the_knobs(self):
        result = pixelate('render', str(self.root), '--set', 'seed=2', env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('knobs: time=night, seed=2 (file sha256 ', result.stdout)

    def test_an_inherited_variable_never_reaches_the_commands(self):
        planted = self.knob_file({'time': 'dusk', 'seed': 5}, 'planted.json')
        env = dict(self.env, PIXELATE_KNOBS=str(planted))
        result, records = self.render(env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.seen(), {'knobs': {'time': 'night', 'seed': 0}, 'env': None})
        result, records = self.render('--set', 'seed=1', env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.seen()['knobs'], {'time': 'night', 'seed': 1})
        self.assertNotEqual(self.seen()['env'], str(planted))
        tested = pixelate('library', '--library', str(self.library), 'test', 'harbour', env=env)
        self.assertEqual(tested.returncode, 0, tested.stdout + tested.stderr)
        self.assertTrue(json.loads(tested.stdout)['pieces'][0]['outputs'][0]['golden']['ok'])
        self.assertTrue(planted.is_file())

    def test_invalid_sets_exit_2_before_anything_runs_or_is_deleted(self):
        before = tree(self.root)
        for sets, message in ((['time'], 'expected NAME=VALUE'), (['season=winter'], 'no such knob'),
                              (['time=dusk', 'time=night'], 'set more than once'),
                              (['time=noon'], 'expected one of night, dusk'),
                              (['seed=x'], 'expected a decimal integer'),
                              ([f'seed={2 ** 60}'], 'expected an integer from')):
            with self.subTest(sets=sets):
                result, _ = self.render(*[arg for value in sets for arg in ('--set', value)])
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(message, result.stderr)
                self.assertEqual(tree(self.root), before)

    def test_an_out_of_range_int_default_is_refused_before_anything_runs_or_is_deleted(self):
        self.data['knobs'] = dict(KNOBS, seed={'type': 'int', 'default': piece.INT_LIMIT + 1, 'edits': 'art/draw.py'})
        (self.root / 'piece.json').write_text(json.dumps(self.data), encoding='utf-8')
        (self.root / 'out' / 'stale.png').write_bytes(b'stale')
        before = tree(self.root)
        result, _ = self.render('--set', 'seed=1')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('seed: default: knob seed: expected an integer from', result.stderr)
        self.assertEqual(tree(self.root), before)

    def test_set_is_refused_with_no_run_and_for_render_json(self):
        before = tree(self.root)
        result, _ = self.render('--set', 'seed=1', '--no-run')
        self.assertEqual(result.returncode, 2)
        self.assertIn('--set cannot be used with --no-run', result.stderr)
        self.assertEqual(tree(self.root), before)
        (self.root / 'piece.json').unlink()
        (self.root / 'render.json').write_text(json.dumps({'images': [
            {'name': 'a', 'run': 'touch EXECUTED', 'frame': 'out/a.png', 'style': 'arcade', 'scale': 4}]}))
        result, _ = self.render('--set', 'seed=1')
        self.assertEqual(result.returncode, 2)
        self.assertIn('--set needs a piece.json that declares knobs; render.json images take no knobs', result.stderr)
        self.assertFalse((self.root / 'EXECUTED').exists())

    def test_engine_and_pack_knobs_this_script_never_reads_are_refused_by_the_catalog(self):
        # The script program reads knobs(); declared as an engine or pack piece, nothing would read them.
        before = tree(self.root)
        for runtime, message in (('engine', 'scene.json: missing path'),
                                 ('pack', 'pack.json: missing path')):
            with self.subTest(runtime=runtime):
                (self.root / 'piece.json').write_text(json.dumps(dict(self.data, runtime=runtime)), encoding='utf-8')
                result, _ = self.render('--set', 'seed=1')
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(message, result.stderr)
                self.assertFalse((self.root / 'render-report.json').exists())
        (self.root / 'piece.json').write_text(json.dumps(self.data), encoding='utf-8')
        self.assertEqual(tree(self.root), before)

    def test_a_program_given_an_invalid_value_fails_its_command(self):
        # A value only reaches the program through render's checks; a direct run with a bad file fails loudly.
        bad = self.knob_file({'time': 'noon'}, 'bad.json')
        run = subprocess.run([sys.executable, 'art/draw.py'], cwd=self.root, capture_output=True, text=True,
                             env=dict(self.env, PYTHONPATH=str(REPO / 'tools'), PIXELATE_KNOBS=str(bad)))
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('KnobError: knob time: "noon" is not one of ["night", "dusk"]', run.stderr)


if __name__ == '__main__':
    unittest.main()
