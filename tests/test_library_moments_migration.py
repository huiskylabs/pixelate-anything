"""The ten examples/moments pieces as moved into library/: manifests, goldens, media and run commands.

Static checks only by default: nothing here executes a piece. `golden` and `size` (image outputs) are
not yet in the catalog schema, so manifests are validated from a copy without those two keys.
Set PIXELATE_RUN_MOMENTS_RENDER=1 to also render these trusted, checked-in programs from clean copies
(needs scipy, and for 03 and 04 their hardcoded /home/user output paths make them skip).
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
# These two write to absolute /home/user/pixelate-anything/... paths, so they cannot render in a clean copy.
HARDCODED_OUTPUT = ('canyon-cycle', 'tide-procession')
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


@unittest.skipUnless(os.environ.get('PIXELATE_RUN_MOMENTS_RENDER') == '1',
                     'set PIXELATE_RUN_MOMENTS_RENDER=1 to render the trusted moments programs')
class MomentsRender(unittest.TestCase):
    """Run the checked-in first-party commands from a clean copy and compare with the tracked frames."""

    def test_image_and_export_outputs_reproduce_from_a_clean_copy(self):
        if importlib.util.find_spec('scipy') is None:  # 01's art imports it
            self.skipTest('scipy is not installed')
        env = dict(os.environ, PYTHONPATH=str(TOOLS), PIXELATE_NO_LOG='1',
                   PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'])
        for piece_id in MOMENT_IDS:
            if piece_id in HARDCODED_OUTPUT:
                continue
            with self.subTest(piece=piece_id), tempfile.TemporaryDirectory() as temp:
                clean = Path(temp) / piece_id
                shutil.copytree(LIBRARY / piece_id, clean, ignore=shutil.ignore_patterns('__pycache__'))
                outputs = [o for o in manifest(piece_id)['outputs'] if o['kind'] != 'audio']
                for output in outputs:
                    (clean / output.get('frame', output.get('file'))).unlink()
                for command in dict.fromkeys(o['run'] for o in outputs):
                    done = subprocess.run(['bash', '-c', command], cwd=clean, env=env, capture_output=True, text=True,
                                          timeout=300)
                    self.assertEqual(done.returncode, 0, (command, done.stderr[-400:]))
                for output in outputs:
                    path = output.get('frame', output.get('file'))
                    self.assertEqual((clean / path).read_bytes(), (LIBRARY / piece_id / path).read_bytes(), (piece_id, path))


if __name__ == '__main__':
    unittest.main()
