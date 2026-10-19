"""The ten examples/moments pieces as moved into library/: manifests, goldens, media and run commands.

Static checks only by default: nothing here executes a piece. `golden` and `size` (image outputs) are
not yet in the catalog schema, so manifests are validated from a copy without those two keys.
The trusted, checked-in programs of 03, 04 and 08 (kit tools, numpy and Pillow only) are rendered from clean
copies on every run, to keep their output paths relative to the piece. Set PIXELATE_RUN_MOMENTS_RENDER=1 to
render all ten the same way (01's art needs scipy).
"""
import importlib.util
import json
import os
import re
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
TOOLS = REPO / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('piece_library', TOOLS / 'library.py')
assert spec is not None and spec.loader is not None
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)

MOMENT_IDS = ('monsoon-street', 'endless-ascent', 'canyon-cycle', 'tide-procession', 'four-machines',
              'quarry-wakes', 'turntable-shipyard', 'market-day', 'lanternmoss-mire', 'tidewater-signal')
# Their art code once wrote to absolute /home/user/pixelate-anything/... paths and could not render in a clean copy.
PORTABLE_ART = ('canyon-cycle', 'tide-procession', 'market-day')
LEGACY_ROOT = Path('/home/user/pixelate-anything')
SCRIPT = re.compile(r'(?:art|sound|maps)/[\w.-]+\.py')


def manifest(piece_id):
    return json.loads((LIBRARY / piece_id / 'piece.json').read_text(encoding='utf-8'))


def image_size(piece, output):
    size = output.get('size', piece['canvas'])
    return size['w'], size['h']


class MomentsMigration(unittest.TestCase):
    def test_ten_pieces_exist_and_old_folders_are_gone(self):
        for piece_id in MOMENT_IDS:
            self.assertTrue((LIBRARY / piece_id / 'piece.json').is_file(), piece_id)
            self.assertEqual(manifest(piece_id)['id'], piece_id)
        leftovers = sorted(p.name for p in (REPO / 'examples' / 'moments').glob('[0-9][0-9]-*'))
        self.assertEqual(leftovers, [])

    def test_manifests_validate_without_the_golden_and_size_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            for piece_id in MOMENT_IDS:
                shutil.copytree(LIBRARY / piece_id, Path(temp) / piece_id, ignore=shutil.ignore_patterns('__pycache__'))
                path = Path(temp) / piece_id / 'piece.json'
                data = json.loads(path.read_text(encoding='utf-8'))
                for output in data['outputs']:
                    output.pop('golden', None)
                    output.pop('size', None)
                path.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(sorted(library.scan(temp)), sorted(MOMENT_IDS))

    def test_pack_runtime_is_only_the_asset_pack(self):
        runtimes = {piece_id: manifest(piece_id)['runtime'] for piece_id in MOMENT_IDS}
        self.assertEqual(runtimes.pop('lanternmoss-mire'), 'pack')
        self.assertEqual(set(runtimes.values()), {'script'})
        self.assertTrue((LIBRARY / 'lanternmoss-mire' / 'pack.json').is_file())

    def test_no_status_above_study_without_evidence(self):
        for piece_id in MOMENT_IDS:
            piece = manifest(piece_id)
            self.assertEqual(piece['status'], 'study', piece_id)
            self.assertEqual(piece['knobs'], {}, piece_id)
            self.assertNotIn('review', piece, piece_id)

    def test_request_is_the_brief_request_or_says_none_is_recorded(self):
        for piece_id in MOMENT_IDS:
            request = manifest(piece_id)['request']
            brief = (LIBRARY / piece_id / 'brief.md').read_text(encoding='utf-8')
            line = next((text for text in brief.splitlines() if text.startswith('Request: ')), None)
            if line:
                joined = ' '.join(x.strip() for x in brief[brief.index(line):].split('\n\n')[0].splitlines())
                self.assertEqual(request, joined[len('Request: '):], piece_id)
            else:
                self.assertTrue(request.startswith('No verbatim user request is recorded'), piece_id)

    def test_goldens_are_nearest_1x_of_the_delivered_frame(self):
        for piece_id in MOMENT_IDS:
            piece = manifest(piece_id)
            for output in piece['outputs']:
                if output['kind'] != 'image':
                    self.assertNotIn('golden', output)
                    continue
                self.assertEqual(output['golden'], f"out/golden/{output['name']}.png", piece_id)
                width, height = image_size(piece, output)
                frame = Image.open(LIBRARY / piece_id / output['frame']).convert('RGBA')
                self.assertEqual(frame.size, (width * output['scale'], height * output['scale']), (piece_id, output['name']))
                golden = Image.open(LIBRARY / piece_id / output['golden'])
                self.assertEqual(golden.size, (width, height), (piece_id, output['name']))
                self.assertEqual(golden.convert('RGBA').tobytes(), frame.resize((width, height), Image.Resampling.NEAREST).tobytes(),
                                 (piece_id, output['name']))

    def test_media_is_bounded(self):
        for piece_id in MOMENT_IDS:
            media = manifest(piece_id)['media']
            thumb = Image.open(LIBRARY / piece_id / media['thumb'])
            self.assertLessEqual(max(thumb.size), 256, piece_id)
            contact = Image.open(LIBRARY / piece_id / media['contact'])
            self.assertLessEqual(contact.height, 256, piece_id)
            self.assertLessEqual(contact.width, 2 * 256 + 4, piece_id)

    def test_run_commands_name_existing_sources_and_write_the_declared_file(self):
        for piece_id in MOMENT_IDS:
            root = LIBRARY / piece_id
            for output in manifest(piece_id)['outputs']:
                scripts = SCRIPT.findall(output['run'])
                for script in scripts:
                    self.assertTrue((root / script).is_file(), (piece_id, output['name'], script))
                if 'pixelate audio music' in output['run']:
                    self.assertTrue((root / 'music' / 'music.js').is_file(), piece_id)
                if output['kind'] == 'audio':
                    written = Path(output['file']).name
                    text = output['run'] + ''.join((root / s).read_text(encoding='utf-8') for s in scripts)
                    self.assertIn(written, text, (piece_id, 'run never names', written))

    def test_portable_art_has_no_absolute_home_paths(self):
        for piece_id in PORTABLE_ART:
            for path in sorted((LIBRARY / piece_id).rglob('*.py')):
                self.assertNotIn('/home/user', path.read_text(encoding='utf-8'), str(path.relative_to(REPO)))

    def test_market_day_b_is_a_gated_image_with_its_own_hero_not_an_export(self):
        piece = manifest('market-day')
        outputs = {o['name']: o for o in piece['outputs']}
        self.assertEqual(outputs['b']['kind'], 'image')
        self.assertEqual((outputs['b']['style'], outputs['b']['scale'], outputs['b']['size']),
                         ('sticker-iso', 8, {'w': 140, 'h': 140}))
        self.assertEqual(outputs['b']['golden'], 'out/golden/b.png')
        self.assertIn('## Image B', (LIBRARY / 'market-day' / 'brief.md').read_text(encoding='utf-8'))

    def test_market_day_b_fails_the_gate_in_exactly_the_two_documented_lines(self):
        """B is an unresolved blocker: a crop of A cannot pass the sticker-iso budget. This pins the failure so a
        change to B (or to the gate) shows up here, and so nothing else fails silently."""
        root = LIBRARY / 'market-day'
        output = {o['name']: o for o in manifest('market-day')['outputs']}['b']
        done = subprocess.run([sys.executable, str(REPO / 'pixelate'), 'check', output['frame'], '--style', output['style'],
                               '--scale', str(output['scale']), '--brief', output['brief'], '--image', 'b'],
                              cwd=root, capture_output=True, text=True, env=dict(os.environ, PIXELATE_NO_LOG='1'))
        failed = sorted(line.split()[2] for line in done.stdout.splitlines() if line.startswith('FAIL ') and 'checks' not in line)
        self.assertEqual(done.returncode, 1, done.stdout[-600:] + done.stderr[-600:])
        self.assertEqual(failed, ['L<=0.3', 'empty'])

    def test_four_machines_exports_are_a_composite_poster_and_a_copy_of_a_gated_panel(self):
        root = LIBRARY / 'four-machines'
        outputs = {o['name']: o for o in manifest('four-machines')['outputs']}
        self.assertEqual({n for n, o in outputs.items() if o['kind'] == 'export'}, {'poster', 'b'})
        self.assertEqual({n for n, o in outputs.items() if o['kind'] == 'image'}, {'gb', 'nes', 'snes', 'gba'})
        self.assertEqual((root / outputs['b']['file']).read_bytes(), (root / outputs['snes']['frame']).read_bytes())

    def test_every_piece_anatomy_lists_a_drawing_source(self):
        for piece_id in MOMENT_IDS:
            piece = manifest(piece_id)
            self.assertTrue(any(entry['file'].endswith(('.py', '.px')) for entry in piece['anatomy']), piece_id)

    def test_goldens_frames_and_media_are_tracked_in_git(self):
        if shutil.which('git') is None or not (REPO / '.git').exists():
            self.skipTest('not a git checkout')
        tracked = set(subprocess.run(['git', 'ls-files', 'library'], cwd=REPO, capture_output=True, text=True,
                                     check=True).stdout.splitlines())
        for piece_id in MOMENT_IDS:
            piece = manifest(piece_id)
            wanted = [f'library/{piece_id}/{o[key]}' for o in piece['outputs'] for key in ('frame', 'file', 'golden') if key in o]
            wanted += [f'library/{piece_id}/{path}' for path in piece['media'].values()]
            wanted.append(f'library/{piece_id}/piece.json')
            for path in wanted:
                self.assertTrue(path in tracked, f'{path} is not tracked')

    def test_repo_ignore_exception_does_not_hide_new_goldens(self):
        if shutil.which('git') is None or not (REPO / '.git').exists():
            self.skipTest('not a git checkout')
        for piece_id in MOMENT_IDS:
            probe = f'library/{piece_id}/out/golden/probe.png'
            result = subprocess.run(['git', 'check-ignore', '-q', probe], cwd=REPO)
            self.assertEqual(result.returncode, 1, f'{probe} is ignored')


def render_from_clean_copy(case, piece_id):
    """Run every non-audio run command of a piece in a clean copy and compare with the tracked frames and goldens.

    The copy is not rewritten: only the expected outputs are deleted first. The kit comes from PYTHONPATH."""
    env = dict(os.environ, PYTHONPATH=str(TOOLS), PIXELATE_NO_LOG='1',
               PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'])
    legacy_before = LEGACY_ROOT.exists()
    with tempfile.TemporaryDirectory() as temp:
        clean = Path(temp) / piece_id
        shutil.copytree(LIBRARY / piece_id, clean, ignore=shutil.ignore_patterns('__pycache__'))
        outputs = [o for o in manifest(piece_id)['outputs'] if o['kind'] != 'audio']
        for output in outputs:
            (clean / output.get('frame', output.get('file'))).unlink()
        for command in dict.fromkeys(o['run'] for o in outputs):
            done = subprocess.run(['bash', '-c', command], cwd=clean, env=env, capture_output=True, text=True, timeout=300)
            case.assertEqual(done.returncode, 0, (command, done.stderr[-400:]))
        for output in outputs:
            path = output.get('frame', output.get('file'))
            case.assertEqual((clean / path).read_bytes(), (LIBRARY / piece_id / path).read_bytes(), (piece_id, path))
            if output['kind'] == 'image':
                width, height = image_size(manifest(piece_id), output)
                rendered = Image.open(clean / path).convert('RGBA').resize((width, height), Image.Resampling.NEAREST)
                golden = Image.open(LIBRARY / piece_id / output['golden']).convert('RGBA')
                case.assertEqual(rendered.tobytes(), golden.tobytes(), (piece_id, output['name'], 'golden'))
    case.assertEqual(LEGACY_ROOT.exists(), legacy_before, f'{LEGACY_ROOT} was created')


class PortableArtRender(unittest.TestCase):
    """03, 04 and 08 render from a clean copy with only the kit tools on PYTHONPATH (no scipy, no ffmpeg)."""

    def test_canyon_cycle_images_and_index_reproduce(self):
        render_from_clean_copy(self, 'canyon-cycle')

    def test_tide_procession_images_reproduce(self):
        render_from_clean_copy(self, 'tide-procession')

    def test_market_day_images_reproduce(self):
        render_from_clean_copy(self, 'market-day')

    def test_market_day_images_reproduce_with_a_different_blas_core(self):
        with mock.patch.dict(os.environ, OPENBLAS_CORETYPE='Haswell'):
            render_from_clean_copy(self, 'market-day')


@unittest.skipUnless(os.environ.get('PIXELATE_RUN_MOMENTS_RENDER') == '1',
                     'set PIXELATE_RUN_MOMENTS_RENDER=1 to render all ten trusted moments programs')
class MomentsRender(unittest.TestCase):
    """Run every checked-in first-party image command from a clean copy and compare with the tracked frames."""

    def test_image_and_export_outputs_reproduce_from_a_clean_copy(self):
        for piece_id in MOMENT_IDS:
            with self.subTest(piece=piece_id):
                if piece_id == 'monsoon-street' and importlib.util.find_spec('scipy') is None:  # 01's art imports it
                    self.skipTest('scipy is not installed')
                render_from_clean_copy(self, piece_id)


if __name__ == '__main__':
    unittest.main()
