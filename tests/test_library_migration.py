"""Migration checks for the seven examples and three templates moved into library/.

These pin what the phase-1 migration claimed about those ten pieces: ids, honest statuses, the typed
outputs and their 1x goldens (`out/golden/<name>.png`), bounded media, tracked files, that the
declared commands recreate the declared files in a clean copy of the kit, that no piece imports a
sibling piece (a copied piece renders with just itself and the kit), and that every `starter` passes
its technical gate. A passing gate is not review or approval of any piece. The slow packs run only
with PIXELATE_SLOW_LIBRARY=1.
"""
import importlib.util
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
LIBRARY = REPO / 'library'
TOOLS = REPO / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('piece_library_migration', TOOLS / 'library.py')
assert spec is not None and spec.loader is not None
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)

# id: (status, mode, runtime, where it came from)
MIGRATED = {
    'lantern-isle': ('study', 'scene', 'engine', 'examples/lantern-isle'),
    'san-francisco': ('study', 'rebuild', 'pack', 'examples/san-francisco'),
    'santorini': ('study', 'rebuild', 'pack', 'examples/santorini'),
    'retro-screens': ('study', 'era', 'pack', 'examples/retro'),
    'rose-squall': ('study', 'scene', 'pack', 'examples/indie'),
    'meadow-kit': ('study', 'assets', 'pack', 'examples/meadow-kit'),
    'projections': ('study', 'scene', 'pack', 'examples/projections'),
    'starter-scene-loop': ('starter', 'scene', 'engine', 'templates/starter'),
    'starter-music': ('starter', 'music', 'engine', 'templates/music'),
    'starter-assets': ('starter', 'assets', 'pack', 'templates/assets'),
}
# Output commands run the checked-in first-party kit from the piece folder; $PIXELATE_KIT is the kit root.
RUN = re.compile(r'(mkdir -p out && )?python3 "\$PIXELATE_KIT/pixelate" '
                 r'(assets \.|shot \. \d+ --zoom \d+ --out out|audio \. out/loop\.ogg)\Z')
SLOW = ('san-francisco', 'santorini', 'retro-screens', 'rose-squall')
HAVE_NODE = shutil.which('node') is not None


def manifest(piece_id):
    return json.loads((LIBRARY / piece_id / 'piece.json').read_text(encoding='utf-8'))


def images(data):
    return [o for o in data['outputs'] if o['kind'] == 'image']


def downsample(frame, size):
    """The 1x RGBA a golden holds: NEAREST from the delivered frame."""
    with Image.open(frame) as im:
        return im.convert('RGBA').resize((size['w'], size['h']), Image.NEAREST)


def load(path):
    with Image.open(path) as im:
        return im.convert('RGBA')


class MigratedPieceTest(unittest.TestCase):
    def test_ten_pieces_with_expected_identity_and_honest_status(self):
        self.assertTrue(set(MIGRATED) <= {p.name for p in LIBRARY.iterdir() if p.is_dir()})
        for piece_id, (status, mode, runtime, _) in MIGRATED.items():
            with self.subTest(piece=piece_id):
                data = manifest(piece_id)
                self.assertEqual((data['id'], data['status'], data['mode'], data['runtime']),
                                 (piece_id, status, mode, runtime))
                # no review, approval or knob is claimed that the migration could not evidence
                self.assertNotIn('review', data)
                self.assertEqual(data['knobs'], {})
                self.assertEqual(data['license'], 'MIT')
                self.assertTrue((LIBRARY / piece_id / 'history' / 'migration.md').is_file())

    def test_sources_moved_not_copied(self):
        for piece_id, (_, _, _, source) in MIGRATED.items():
            with self.subTest(piece=piece_id):
                self.assertFalse((REPO / source).exists(), source)

    def test_no_source_still_names_an_examples_or_templates_path(self):
        for piece_id in MIGRATED:
            for path in (LIBRARY / piece_id).rglob('*'):
                if path.suffix in ('.py', '.js', '.json', '.txt') and path.is_file() and 'out' not in path.parts:
                    self.assertNotRegex(path.read_text(encoding='utf-8', errors='replace'),
                                        r"examples['/ ]+(san-francisco|santorini|retro|indie|meadow-kit|projections|lantern-isle)",
                                        str(path))

    def test_declaration_validates_with_golden_and_size_stripped(self):
        # `golden` and `size` are the runtime contract (out/golden/<name>.png, frame = size x scale); the
        # catalog schema that landed with the migration does not know them yet, and a frame is a generated
        # file. Validate the rest of the declaration on a copy with those two keys removed and the frames
        # materialised from the goldens.
        for piece_id in MIGRATED:
            with self.subTest(piece=piece_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / piece_id
                shutil.copytree(LIBRARY / piece_id, root, symlinks=True)
                data = manifest(piece_id)
                for output in images(data):
                    self.assertEqual(output['golden'], f"out/golden/{output['name']}.png")
                    golden = load(LIBRARY / piece_id / output['golden'])
                    self.assertEqual(golden.size, (output['size']['w'], output['size']['h']))
                    frame = root / output['frame']
                    frame.parent.mkdir(parents=True, exist_ok=True)
                    golden.resize((golden.width * output['scale'], golden.height * output['scale']),
                                                  Image.NEAREST).save(frame)
                    del output['golden'], output['size']
                (root / 'piece.json').write_text(json.dumps(data), encoding='utf-8')
                self.assertEqual(library.validate(root)['id'], piece_id)

    def test_run_commands_are_trusted_kit_commands_that_name_their_files(self):
        for piece_id in MIGRATED:
            data = manifest(piece_id)
            for output in data['outputs']:
                with self.subTest(piece=piece_id, output=output['name']):
                    self.assertRegex(output['run'], RUN)
                    if output['kind'] == 'image' and 'shot .' in output['run']:
                        t = re.search(r'shot \. (\d+) --zoom (\d+)', output['run'])
                        self.assertIsNotNone(t)
                        self.assertEqual(output['frame'], f'out/t{int(t.group(1)):04d}.00.png')
                        self.assertEqual(output['scale'], int(t.group(2)))

    def test_goldens_and_media_are_small_and_bounded(self):
        total = 0
        for piece_id in MIGRATED:
            data = manifest(piece_id)
            for output in images(data):
                golden = LIBRARY / piece_id / output['golden']
                self.assertLess(golden.stat().st_size, 100_000, golden)
                with Image.open(golden) as im:
                    self.assertEqual(im.mode, 'RGBA')
            self.assertLessEqual(max(load(LIBRARY / piece_id / data['media']['thumb']).size), 256, piece_id)
            self.assertLessEqual(max(load(LIBRARY / piece_id / data['media']['contact']).size), 520, piece_id)
            for name in ('thumb', 'contact'):
                self.assertLess((LIBRARY / piece_id / data['media'][name]).stat().st_size, 250_000)
            total += sum(p.stat().st_size for p in (LIBRARY / piece_id / 'out').rglob('*') if p.is_file())
        # goldens, exports and the one 48 s ogg of starter-music, far under the 50 MB repository policy
        self.assertLess(total, 3_000_000)

    @unittest.skipUnless((REPO / '.git').exists(), 'needs a git checkout')
    def test_goldens_media_and_committed_exports_are_tracked(self):
        tracked = set(subprocess.run(['git', 'ls-files', 'library'], cwd=REPO, capture_output=True, text=True,
                                     check=True).stdout.split('\n'))
        for piece_id in MIGRATED:
            data = manifest(piece_id)
            wanted = [data['media']['thumb'], data['media']['contact']]
            wanted += [o['golden'] for o in images(data)] + [o['file'] for o in data['outputs'] if o['kind'] != 'image']
            for path in wanted:
                self.assertIn(f'library/{piece_id}/{path}', tracked)

    def test_art_imports_resolve_without_a_sibling_piece(self):
        # Each program may import the standard library, numpy, Pillow, a kit tool, or a file inside its own
        # piece. A name that only exists in another library piece breaks a remix copied out of library/.
        allowed = set(sys.stdlib_module_names) | {'numpy', 'PIL'} | {p.stem for p in TOOLS.glob('*.py')}
        for piece_id in set(MIGRATED) | {'san-francisco'}:
            own = {p.stem for p in (LIBRARY / piece_id).rglob('*.py')}
            for path in (LIBRARY / piece_id).rglob('*.py'):
                source = path.read_text(encoding='utf-8')
                self.assertNotRegex(source, r"['\"]library['\"]", f'{path} reaches into library/')
                for node in ast.walk(ast.parse(source)):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                        [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else []
                    for name in names:
                        with self.subTest(piece=piece_id, file=path.name, name=name):
                            self.assertIn(name.split('.')[0], allowed | own)

    def test_no_symlinks_in_migrated_pieces(self):
        for piece_id in MIGRATED:
            for path in (LIBRARY / piece_id).rglob('*'):
                self.assertFalse(path.is_symlink(), path)


class KitCopyTest(unittest.TestCase):
    """Run each declared command from a copy of the kit and compare with the committed files."""
    KEEP_LIBRARY = True

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.kit = Path(cls.tmp.name) / 'kit'
        ignore = ['.git', 'docs', 'demo', 'evals', 'examples', 'tests', '__pycache__', '.pixelate']
        shutil.copytree(REPO, cls.kit, ignore=shutil.ignore_patterns(*ignore, *([] if cls.KEEP_LIBRARY else ['library'])))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def stage(self, piece_id):
        """The folder the piece is rendered in."""
        return self.kit / 'library' / piece_id

    def run_kit(self, command, root):
        env = dict(os.environ, PIXELATE_KIT=str(self.kit))
        return subprocess.run(command, shell=True, cwd=root, env=env, capture_output=True, text=True, timeout=600)

    def kit_check(self, root, *args):
        """`pixelate check ...` without a shell; exit 0 means every gate check passed."""
        return subprocess.run([sys.executable, str(self.kit / 'pixelate'), 'check', *args], cwd=root,
                              capture_output=True, text=True, timeout=600)

    def render(self, piece_id):
        data = manifest(piece_id)
        root = self.stage(piece_id)
        for output in data['outputs']:
            for key in ('file', 'frame'):
                if key in output and (root / output[key]).exists():
                    (root / output[key]).unlink()      # the command, not the committed copy, must make it
        done = set()
        for output in data['outputs']:
            if output['kind'] == 'audio' or output['run'] in done:     # audio is covered by the notes, not bytes
                continue
            done.add(output['run'])
            self.assertRegex(output['run'], RUN)           # only the allowlisted first-party kit commands reach the shell
            result = self.run_kit(output['run'], root)
            self.assertEqual(result.returncode, 0, result.stderr[-500:])
        for output in data['outputs']:
            if output['kind'] == 'image':
                frame = root / output['frame']
                self.assertTrue(frame.is_file(), frame)
                self.assertEqual(load(frame).size, (output['size']['w'] * output['scale'],
                                                    output['size']['h'] * output['scale']))
                golden = load(LIBRARY / piece_id / output['golden'])
                self.assertEqual(downsample(frame, output['size']).tobytes(), golden.tobytes(),
                                 f"{piece_id}/{output['name']} differs from its golden")
            elif output['kind'] == 'export':
                self.assertEqual((root / output['file']).read_bytes(), (LIBRARY / piece_id / output['file']).read_bytes(),
                                 f"{piece_id}/{output['name']}")
        return root


class CleanCopyRenderTest(KitCopyTest):
    def test_packs_that_render_in_seconds(self):
        for piece_id in ('meadow-kit', 'projections', 'starter-assets'):
            with self.subTest(piece=piece_id):
                self.render(piece_id)

    @unittest.skipUnless(HAVE_NODE, 'engine frames are rendered in Node')
    def test_engine_frames(self):
        for piece_id in ('lantern-isle', 'starter-scene-loop', 'starter-music'):
            with self.subTest(piece=piece_id):
                self.render(piece_id)

    @unittest.skipUnless(os.environ.get('PIXELATE_SLOW_LIBRARY'), 'about two minutes: set PIXELATE_SLOW_LIBRARY=1')
    def test_slow_packs(self):
        for piece_id in SLOW:
            with self.subTest(piece=piece_id):
                self.render(piece_id)


class IsolatedCopyTest(KitCopyTest):
    """A piece copied out of library/ renders with just itself and the kit: the kit copy holds no library/
    and the piece sits in a folder of its own, so a sibling piece cannot be found by any path."""
    KEEP_LIBRARY = False

    def stage(self, piece_id):
        root = Path(self.tmp.name) / 'elsewhere' / piece_id
        if not root.exists():
            shutil.copytree(LIBRARY / piece_id, root, ignore=shutil.ignore_patterns('__pycache__'))
        return root

    def test_kit_copy_has_no_library(self):
        self.assertFalse((self.kit / 'library').exists())

    def test_fast_pieces_render_to_their_goldens(self):
        for piece_id in ('projections', 'starter-assets'):
            with self.subTest(piece=piece_id):
                self.render(piece_id)

    @unittest.skipUnless(HAVE_NODE, 'engine frames are rendered in Node')
    def test_starters_render_and_pass_their_gate_alone(self):
        starters = [i for i, (status, *_) in MIGRATED.items() if status == 'starter']
        self.assertEqual(sorted(starters), ['starter-assets', 'starter-music', 'starter-scene-loop'])
        for piece_id in starters:
            with self.subTest(piece=piece_id):
                root = self.render(piece_id)
                for output in images(manifest(piece_id)):
                    result = self.kit_check(root, output['frame'], '--scale', str(output['scale']),
                                            '--style', output['style'])
                    self.assertEqual(result.returncode, 0, f"{piece_id}/{output['name']}\n{result.stdout[-800:]}")
                if manifest(piece_id)['runtime'] == 'engine':
                    result = self.kit_check(root, '.')
                    self.assertEqual(result.returncode, 0, result.stdout[-800:])

    @unittest.skipUnless(os.environ.get('PIXELATE_SLOW_LIBRARY'), 'about two minutes: set PIXELATE_SLOW_LIBRARY=1')
    def test_slow_pieces_that_used_to_import_a_sibling(self):
        for piece_id in ('santorini', 'retro-screens'):
            with self.subTest(piece=piece_id):
                self.render(piece_id)


if __name__ == '__main__':
    unittest.main()
