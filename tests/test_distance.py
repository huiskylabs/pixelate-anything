"""tools/distance.py and the distance `pixelate render` reports for a remix: trusted fixture code, and
checked-in kit pieces read statically (none of their code runs)."""
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
sys.path.insert(0, str(REPO / 'tools'))
import distance  # noqa: E402
import remix  # noqa: E402

library = distance.library  # the module distance validates with
render = library.kit_render()  # the render module distance reads the base golden with

# A frame that passes the arcade gate: a dark night, a lit block and a foreground of scattered stones.
DRAW = '''from PIL import Image
im = Image.new('RGB', (64, 48), (8, 10, 18))
im.paste((70, 40, 30), (0, 30, 64, 48))
for x in range(1, 64, 5):
    for y in range(32 + x % 3, 48, 4):
        im.paste((150, 120, 90) if (x + y) % 2 else (40, 90, 110), (x, y, x + 2, y + 2))
im.paste((150, 120, 90), (24, 8, 40, 20))
im.paste((90, 60, 40), (26, 10, 38, 18))
im.resize((256, 192), Image.Resampling.NEAREST).save('out/a.png')
'''
# The request's edit: a jungle sky in new colours and a stepped temple where the block was.
TEMPLE = DRAW.replace('(8, 10, 18)', '(20, 46, 30)').replace(
    "im.paste((150, 120, 90), (24, 8, 40, 20))\nim.paste((90, 60, 40), (26, 10, 38, 18))",
    "for i in range(4):\n    im.paste((120 + 20 * i, 130, 100), (14 + 4 * i, 8 + 5 * i, 50 - 4 * i, 30))\n"
    "im.paste((60, 160, 70), (0, 0, 64, 4))")
BASE_REQUEST = 'a harbour wall at night'
REQUEST = 'an ancient temple wakes under a jungle at night'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest(piece_id, request, **extra):
    return {'schema': 1, 'id': piece_id, 'title': 'Harbour', 'summary': 'A harbour wall at night.',
            'request': request, 'status': 'study', 'mode': 'scene', 'runtime': 'script',
            'tags': {'subject': ['harbour', 'wall'], 'setting': ['night'], 'camera': 'side', 'style': 'arcade',
                     'era': 'none', 'motion': 'stills', 'sound': 'none'},
            'canvas': {'w': 64, 'h': 48, 'scale': 4},
            'outputs': [{'name': 'a', 'kind': 'image', 'run': f'{sys.executable} art/draw.py', 'frame': 'out/a.png',
                         'golden': 'out/golden/a.png', 'style': 'arcade', 'scale': 4}],
            'anatomy': [{'file': 'art/draw.py', 'draws': 'the harbour wall', 'change_for': 'the setting'}],
            'knobs': {}, 'provenance': {'made': '2026-10-18', 'by': 'fixture author'}, 'license': 'MIT', **extra}


def make_piece(root, piece_id, request, draw=DRAW, **extra):
    """A script piece at root/piece_id whose golden is the 1x of what draw renders."""
    piece = Path(root) / piece_id
    (piece / 'art').mkdir(parents=True)
    (piece / 'out' / 'golden').mkdir(parents=True)
    (piece / 'art' / 'draw.py').write_text(draw, encoding='utf-8')
    subprocess.run([sys.executable, 'art/draw.py'], cwd=piece, check=True)
    with Image.open(piece / 'out' / 'a.png') as frame:
        frame.resize((64, 48), Image.Resampling.NEAREST).save(piece / 'out' / 'golden' / 'a.png')
    (piece / 'out' / 'a.png').unlink()
    (piece / 'piece.json').write_text(json.dumps(manifest(piece_id, request, **extra)), encoding='utf-8')
    return piece


def png(image):
    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    return buffer.getvalue()


def frame_bytes(piece, scale=4):
    """The bytes of the base golden at scale: what an unedited remix renders."""
    with Image.open(piece / 'out' / 'golden' / 'a.png') as golden:
        return png(golden.resize((golden.width * scale, golden.height * scale), Image.Resampling.NEAREST))


def evidence(d, base, piece='temple', **fields):
    """The remix baseline `pixelate remix` writes into d for a copy of base, built from base's current files:
    the SHA-256 of its piece.json and of every file, as copied. fields replace or, as None, drop base fields."""
    files = {p.relative_to(base).as_posix(): sha(p.read_bytes()) for p in sorted(base.rglob('*'))
             if p.is_file() and not p.is_symlink()}
    record = {'schema': 1, 'type': 'remix-baseline', 'piece': piece, 'files': files,
              'base': {'id': base.name, 'piece_sha256': sha((base / 'piece.json').read_bytes())}}
    record['base'].update(fields)
    record['base'] = {k: v for k, v in record['base'].items() if v is not None}
    (d / '.pixelate').mkdir(parents=True, exist_ok=True)
    (d / distance.BASELINE).write_text(json.dumps(record), encoding='utf-8')
    return record


class Fixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.library = self.temp / 'library'
        self.base = make_piece(self.library, 'harbour', BASE_REQUEST)
        patch = mock.patch.object(distance, 'DEFAULT_LIBRARY', self.library)
        patch.start()
        self.addCleanup(patch.stop)

    def remix(self, request=REQUEST, draw=None, **extra):
        """work/temple: a copy of the base as `pixelate remix` makes it, with draw as its program."""
        dest = self.temp / 'work' / 'temple'
        shutil.copytree(self.base, dest)
        data = manifest('temple', request, lineage={'remixed_from': 'harbour'}, **extra)
        (dest / 'piece.json').write_text(json.dumps(data), encoding='utf-8')
        if draw:
            (dest / 'art' / 'draw.py').write_text(draw, encoding='utf-8')
        evidence(dest, self.base)
        return dest

    def render(self, d, *args, env=None):
        """(exit status, stdout, report records) of `pixelate render d` in this process"""
        out, err, code = io.StringIO(), io.StringIO(), None
        (d / 'render-report.json').unlink(missing_ok=True)   # never read an earlier render's report
        with mock.patch.dict(os.environ, env or {}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                render.main([str(d), *args])
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), json.loads((d / 'render-report.json').read_text())

    def runs(self, d):
        return [json.loads(line) for line in (d / '.pixelate' / 'runs.jsonl').read_text().splitlines()]


class Measure(Fixture):
    """distance.measure on controlled 1x fixtures, against the base's statically read golden."""

    def setUp(self):
        super().setUp()
        piece = self.remix()
        self.base_record = distance.lookup(piece, library.validate(piece))

    def measure(self, data, request=REQUEST, output=None, canvas=None):
        return distance.measure(data, output or {'name': 'a', 'scale': 4}, canvas or {'w': 64, 'h': 48},
                                request, self.base_record)

    def test_an_unchanged_frame_for_a_changed_request_warns(self):
        rec = self.measure(frame_bytes(self.base))
        self.assertEqual(rec['pixels'], {'differ': 0, 'total': 3072, 'share': 0.0})
        self.assertEqual(rec['palette']['share'], 0.0)
        self.assertTrue(rec['request_differs'])
        self.assertTrue(rec['under_remixed'])
        self.assertIn('under-remixed: the request differs from the request of base harbour, but 0 of 3072', rec['warning'])
        self.assertIn('heuristic', rec['warning'])
        self.assertEqual(rec['thresholds'], distance.UNDER_REMIX)
        self.assertIn('not a quality grade', rec['note'])
        golden = (self.base / 'out' / 'golden' / 'a.png').read_bytes()
        self.assertEqual(rec['base'], {'id': 'harbour', 'library': str(self.library), 'output': 'a', 'status': 'study',
                                       'piece_sha256': sha((self.base / 'piece.json').read_bytes()),
                                       'golden': 'out/golden/a.png', 'golden_sha256': sha(golden)})
        self.assertIn('consistency check against an unsigned local file', rec['note'])
        self.assertIn('WARNING under-remixed', distance.line(rec))

    def test_the_same_request_never_warns(self):
        rec = self.measure(frame_bytes(self.base), request='  A harbour wall\nat NIGHT ')
        self.assertFalse(rec['request_differs'])
        self.assertFalse(rec['under_remixed'])
        self.assertIsNone(rec['warning'])
        self.assertEqual(rec['pixels']['differ'], 0)

    def test_a_subject_and_palette_edit_measures_larger_and_does_not_warn(self):
        edited = self.temp / 'edited'
        make_piece(edited, 'temple', REQUEST, TEMPLE)
        rec = self.measure(frame_bytes(edited / 'temple'))
        unchanged = self.measure(frame_bytes(self.base))
        self.assertGreater(rec['pixels']['share'], unchanged['pixels']['share'])
        self.assertGreater(rec['pixels']['share'], 0.5)
        self.assertGreater(rec['palette']['share'], 0.3)
        self.assertFalse(rec['under_remixed'])
        self.assertIsNone(rec['warning'])
        self.assertNotIn('WARNING', distance.line(rec))

    def test_a_small_edit_under_both_thresholds_still_warns(self):
        with Image.open(io.BytesIO(frame_bytes(self.base, 1))) as image:
            image = image.convert('RGB')
            image.paste((90, 60, 40), (0, 0, 8, 4))   # 32 of 3072 pixels, in a colour the base has
            rec = self.measure(png(image.resize((256, 192), Image.Resampling.NEAREST)))
        self.assertEqual(rec['pixels']['differ'], 32)
        self.assertEqual(rec['palette']['share'], 0.0)
        self.assertTrue(rec['under_remixed'])

    def test_a_new_colour_alone_lifts_the_palette_share_over_its_threshold(self):
        with Image.open(io.BytesIO(frame_bytes(self.base, 1))) as image:
            image = image.convert('RGB')
            image.paste((250, 20, 200), (0, 0, 2, 2))
            rec = self.measure(png(image.resize((256, 192), Image.Resampling.NEAREST)))
        self.assertEqual(rec['pixels']['differ'], 4)
        self.assertGreaterEqual(rec['palette']['share'], distance.UNDER_REMIX['palette'])
        self.assertFalse(rec['under_remixed'])

    def test_a_changed_canvas_compares_colours_but_never_counts_pixels(self):
        wide = png(Image.new('RGB', (320, 192), (8, 10, 18)))
        rec = self.measure(wide, canvas={'w': 80, 'h': 48})
        self.assertIsNone(rec['pixels'])
        self.assertIsNone(rec['under_remixed'])
        self.assertIsNone(rec['warning'])
        self.assertIn('size changed: the base golden is 64x48 at 1x, this output 80x48', rec['reason'])
        self.assertEqual(rec['palette']['colours'], 1)
        self.assertIn('pixels unavailable (size changed', distance.line(rec))

    def test_a_frame_off_its_declared_size_is_unavailable_not_zero(self):
        rec = self.measure(png(Image.new('RGB', (100, 100))))
        self.assertEqual((rec['pixels'], rec['palette'], rec['under_remixed']), (None, None, None))
        self.assertIn('frame is 100x100, expected 256x192', rec['reason'])
        self.assertIn('distance from harbour/a unavailable: frame is 100x100', distance.line(rec))

    def test_an_unreadable_frame_is_unavailable(self):
        rec = self.measure(b'not a png')
        self.assertIsNone(rec['pixels'])
        self.assertIn('unreadable frame', rec['reason'])

    def test_transparent_pixels_compare_equal_whatever_their_rgb(self):
        clear = self.temp / 'clear'
        piece = make_piece(clear, 'harbour', BASE_REQUEST)
        Image.new('RGBA', (64, 48), (255, 0, 0, 0)).save(piece / 'out' / 'golden' / 'a.png')
        evidence(self.temp / 'temple', piece)
        base = distance.lookup(self.temp / 'temple', {'id': 'temple', 'lineage': {'remixed_from': 'harbour'}}, clear)
        rec = distance.measure(png(Image.new('RGBA', (256, 192), (0, 0, 255, 0))), {'name': 'a', 'scale': 4},
                               {'w': 64, 'h': 48}, REQUEST, base)
        self.assertEqual((rec['pixels']['differ'], rec['palette']['share']), (0, 0.0))


class Lookup(Fixture):
    """The base comes only from the kit library, validated statically; anything else is unavailable."""

    def lookup(self, base_id, root=None, d=None, recorded=None):
        """lookup for the piece d (default temp/temple) after `pixelate remix` recorded the piece at recorded
        (default the base's folder in root, when there is one) as its base"""
        d = d or self.temp / 'temple'
        recorded = recorded or (root or self.library) / base_id
        if recorded.is_dir():
            evidence(d, recorded, piece=d.name, id=base_id)
        return distance.lookup(d, {'id': d.name, 'lineage': {'remixed_from': base_id}}, root)

    def test_a_piece_without_lineage_is_not_a_remix(self):
        self.assertIsNone(distance.lookup(self.base, {'lineage': {'remixed_from': None}}))
        self.assertIsNone(distance.lookup(self.base, {}))
        rec = distance.unavailable(None, 'a', 'not a remix')
        self.assertEqual(distance.line(rec), '')
        self.assertIsNone(rec['pixels'])

    def test_lookup_reads_the_golden_and_runs_no_base_code(self):
        marker = self.temp / 'ran'
        data = json.loads((self.base / 'piece.json').read_text())
        data['outputs'][0]['run'] = f'touch {marker}'
        (self.base / 'piece.json').write_text(json.dumps(data))
        base = self.lookup('harbour')
        self.assertFalse(marker.exists())
        self.assertEqual(base['images']['a']['data'], (self.base / 'out' / 'golden' / 'a.png').read_bytes())
        self.assertEqual((base['status'], base['request']), ('study', BASE_REQUEST))

    def test_a_base_outside_the_kit_library_is_unavailable(self):
        # As for `pixelate remix --library L`: render looks only in the kit library and searches no other path.
        other = self.temp / 'other'
        make_piece(other, 'lighthouse', BASE_REQUEST)
        base = self.lookup('lighthouse', recorded=other / 'lighthouse')
        self.assertIn('base lighthouse is not in the kit library', base['error'])
        rec = distance.measure(b'', {'name': 'a'}, {'w': 64, 'h': 48}, REQUEST, base)
        self.assertEqual((rec['pixels'], rec['palette'], rec['under_remixed']), (None, None, None))
        self.assertIn('only against checked-in kit pieces', rec['reason'])

    def test_an_invalid_or_linked_base_is_unavailable(self):
        (self.library / 'harbour' / 'link').symlink_to(self.base / 'art')
        self.assertIn('base harbour is not a valid library piece: ', self.lookup('harbour')['error'])
        (self.library / 'harbour' / 'link').unlink()
        (self.library / 'linked').symlink_to(self.base)
        self.assertIn('not a valid library piece', self.lookup('linked')['error'])
        (self.base / 'piece.json').write_text('{')
        self.assertIn('invalid JSON', self.lookup('harbour')['error'])

    def test_a_missing_output_or_golden_is_unavailable(self):
        data = json.loads((self.base / 'piece.json').read_text())
        del data['outputs'][0]['golden']
        (self.base / 'piece.json').write_text(json.dumps(data))
        base = self.lookup('harbour')
        rec = distance.measure(frame_bytes(self.base), {'name': 'a', 'scale': 4}, {'w': 64, 'h': 48}, REQUEST, base)
        self.assertEqual(rec['reason'], 'base output a declares no golden')
        self.assertIsNone(rec['pixels'])
        rec = distance.measure(frame_bytes(self.base), {'name': 'b', 'scale': 4}, {'w': 64, 'h': 48}, REQUEST, base)
        self.assertEqual(rec['reason'], 'base harbour has no image output named b')

    def test_the_base_is_never_the_piece_itself(self):
        self.assertEqual(self.lookup('harbour', d=self.base)['error'], 'the base is this piece itself')

    def test_a_checked_in_kit_piece_is_read_statically(self):
        # A real kit study whose own gate fails is still a base: its golden is the comparison, unrun.
        with mock.patch.object(distance, 'DEFAULT_LIBRARY', library.DEFAULT_LIBRARY):
            base = self.lookup('quarry-wakes', recorded=library.DEFAULT_LIBRARY / 'quarry-wakes')
        self.assertNotIn('error', base)
        self.assertEqual(base['library'], str(library.DEFAULT_LIBRARY))
        golden = library.DEFAULT_LIBRARY / 'quarry-wakes' / 'out' / 'golden' / 'a.png'
        self.assertEqual(base['images']['a']['sha256'], sha(golden.read_bytes()))
        output = next(o for o in library.validate(library.DEFAULT_LIBRARY / 'quarry-wakes')['outputs'] if o['name'] == 'a')
        canvas = library.validate(library.DEFAULT_LIBRARY / 'quarry-wakes')['canvas']
        with Image.open(golden) as image:
            scale = output.get('scale', 1)
            data = png(image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST))
        rec = distance.measure(data, output, canvas, REQUEST, base)
        self.assertEqual(rec['pixels']['differ'], 0)
        self.assertTrue(rec['under_remixed'])


class Render(Fixture):
    """`pixelate render` of a remix: the distance of the hashed bytes, reported, logged and never blocking."""

    def test_an_unedited_remix_warns_but_its_gate_alone_sets_the_exit_status(self):
        d = self.remix()
        code, out, [rec] = self.render(d)
        self.assertTrue(rec['gate']['ok'], rec['gate'])
        self.assertEqual(code, 0)
        self.assertTrue(render.ok(rec))
        self.assertEqual(rec['distance']['pixels']['differ'], 0)
        self.assertTrue(rec['distance']['under_remixed'])
        self.assertIn('| distance from harbour/a: 0.0% of 1x pixels differ (0 of 3072), 0.0% of colours | WARNING '
                      'under-remixed', out)
        [run] = self.runs(d)
        self.assertEqual(run['base'], {'id': 'harbour', 'library': str(self.library), 'status': 'study',
                                       'piece_sha256': sha((self.base / 'piece.json').read_bytes())})
        self.assertEqual(run['images'][0]['distance'], rec['distance'])
        self.assertTrue(run['ok'])

    def test_an_edited_remix_reports_a_larger_distance_and_no_warning(self):
        d = self.remix(draw=TEMPLE)
        code, out, [rec] = self.render(d)
        self.assertGreater(rec['distance']['pixels']['share'], 0.5)
        self.assertFalse(rec['distance']['under_remixed'])
        self.assertNotIn('WARNING', out)
        self.assertEqual(code, 0 if render.ok(rec) else 1)

    def test_a_failing_gate_fails_the_render_and_the_distance_still_reports(self):
        d = self.remix()
        data = json.loads((d / 'piece.json').read_text())
        data['outputs'][0]['style'] = 'pastel-cell'
        (d / 'piece.json').write_text(json.dumps(data))
        code, out, [rec] = self.render(d)
        self.assertFalse(rec['gate']['ok'])
        self.assertEqual(code, 1)
        self.assertTrue(rec['distance']['under_remixed'])
        self.assertIn('gate FAIL', out)
        self.assertIn('WARNING under-remixed', out)

    def test_the_distance_is_of_the_bytes_read_once_even_if_the_frame_changes_after(self):
        d = self.remix()
        edited = self.temp / 'edited'
        other = frame_bytes(make_piece(edited, 'temple', REQUEST, TEMPLE))
        gate = render.technical_gate

        def rewrite_then_gate(folder, im):
            (d / im['frame']).write_bytes(other)   # a process the command left running
            return gate(folder, im)
        with mock.patch.object(render, 'technical_gate', rewrite_then_gate):
            code, out, [rec] = self.render(d)
        self.assertEqual((d / 'out' / 'a.png').read_bytes(), other)
        self.assertNotEqual(rec['sha256'], sha(other))
        self.assertEqual(rec['distance']['pixels']['differ'], 0)
        self.assertTrue(rec['distance']['under_remixed'])

    def test_no_log_reports_the_distance_without_snapshots_or_a_run_log(self):
        d = self.remix()
        code, out, [rec] = self.render(d, env={'PIXELATE_NO_LOG': '1'})
        self.assertNotIn('snapshot', rec)
        self.assertEqual(sorted(p.name for p in (d / '.pixelate').iterdir()), ['remix-baseline.json'])
        self.assertTrue(rec['distance']['under_remixed'])
        self.assertIn('WARNING under-remixed', out)

    def test_a_failed_command_or_no_frame_is_unavailable_never_zero(self):
        d = self.remix(draw='raise SystemExit("boom")\n')
        code, out, [rec] = self.render(d)
        self.assertEqual(code, 1)
        self.assertEqual(rec['distance']['reason'], 'no frame was read: its run command failed')
        self.assertIsNone(rec['distance']['pixels'])
        self.assertIn('distance from harbour/a unavailable: no frame was read', out)
        code, out, [rec] = self.render(d, '--no-run')
        self.assertEqual(rec['distance']['reason'], 'no frame was read: frame not found: out/a.png')
        self.assertIsNone(self.runs(d)[-1]['images'][0]['distance']['pixels'])
        # A link the command leaves at the frame is never followed, even to the base's own golden.
        (d / 'art' / 'draw.py').write_text(f"import os\nos.symlink({str(self.base / 'out/golden/a.png')!r}, 'out/a.png')\n")
        code, out, [rec] = self.render(d)
        self.assertEqual(code, 1)
        self.assertTrue(rec['distance']['reason'].startswith('no frame was read: unsafe frame: '))
        self.assertIsNone(rec['distance']['pixels'])

    def test_a_remix_of_a_base_outside_the_kit_library_reports_why(self):
        with mock.patch.object(distance, 'DEFAULT_LIBRARY', self.temp / 'kit-library'):
            (self.temp / 'kit-library').mkdir()
            d = self.remix()
            code, out, [rec] = self.render(d)
        self.assertEqual(code, 0)
        self.assertIn('base harbour is not in the kit library', rec['distance']['reason'])
        self.assertIsNone(rec['distance']['pixels'])
        self.assertIn('distance from harbour/a unavailable: base harbour is not in the kit library', out)
        self.assertIn('not in the kit library', self.runs(d)[-1]['base']['error'])

    def test_a_piece_that_is_not_a_remix_records_why_and_prints_nothing(self):
        code, out, [rec] = self.render(self.base)
        self.assertEqual(rec['distance']['base'], None)
        self.assertEqual(rec['distance']['reason'], 'not a remix: piece.json names no lineage.remixed_from')
        self.assertNotIn('distance', out)
        self.assertNotIn('base', self.runs(self.base)[-1])


class Provenance(Fixture):
    """The kit piece is the base only when it matches the base identity the remix baseline records."""

    def remixed(self, library_root, base_id='harbour', request=REQUEST):
        """work/temple as `pixelate remix --library library_root` makes it (fixture code runs once)"""
        dest = self.temp / 'work' / 'temple'
        created, baseline = remix.remix(base_id, dest, request, library_root, timeout=60)
        self.assertTrue(created, baseline)
        return dest

    def assert_unavailable(self, d, reason, logged_error=True):
        code, out, [rec] = self.render(d)
        self.assertEqual(code, 0 if render.ok(rec) else 1)   # an unavailable distance never fails a render
        self.assertIn(reason, rec['distance']['reason'])
        self.assertEqual({k: rec['distance'][k] for k in ('pixels', 'palette', 'under_remixed', 'warning')},
                         dict.fromkeys(('pixels', 'palette', 'under_remixed', 'warning')))
        self.assertIn('distance from harbour/a unavailable: ', out)
        self.assertIn(reason, out)
        self.assertNotIn('WARNING', out)
        run = self.runs(d)[-1]
        self.assertEqual(run['images'][0]['distance'], rec['distance'])
        if logged_error:
            self.assertIn(reason, run['base']['error'])
        return rec

    def test_a_remix_of_its_own_kit_base_measures_and_its_edits_are_not_rehashed(self):
        d = self.remixed(self.library)
        recorded = json.loads((d / remix.BASELINE).read_text())['base']['piece_sha256']
        self.assertEqual(recorded, sha((self.base / 'piece.json').read_bytes()))
        code, out, [rec] = self.render(d)
        self.assertTrue(rec['distance']['under_remixed'])
        self.assertEqual(rec['distance']['base']['piece_sha256'], recorded)
        self.assertIn('WARNING under-remixed', out)
        # Edits to the copy, its own golden included, are intended: only the kit base is checked.
        (d / 'art' / 'draw.py').write_text(TEMPLE, encoding='utf-8')
        Image.new('RGB', (64, 48), (255, 255, 255)).save(d / 'out' / 'golden' / 'a.png')
        code, out, [rec] = self.render(d)
        self.assertGreater(rec['distance']['pixels']['share'], 0.5)
        self.assertNotIn('WARNING', out)

    def test_a_colliding_base_from_another_library_with_another_golden_is_unavailable(self):
        other = self.temp / 'other'
        make_piece(other, 'harbour', BASE_REQUEST, TEMPLE)
        self.assertEqual((other / 'harbour' / 'piece.json').read_bytes(), (self.base / 'piece.json').read_bytes())
        d = self.remixed(other)
        self.assert_unavailable(d, 'base golden out/golden/a.png is not the one this remix copied', logged_error=False)

    def test_a_colliding_base_with_the_same_golden_but_another_manifest_is_unavailable(self):
        other = self.temp / 'other'
        make_piece(other, 'harbour', 'a harbour wall at dusk')
        golden = 'out/golden/a.png'
        self.assertEqual((other / 'harbour' / golden).read_bytes(), (self.base / golden).read_bytes())
        d = self.remixed(other)
        self.assert_unavailable(d, 'base harbour in the kit library is not the base this remix recorded')

    def test_a_base_missing_from_the_kit_library_is_unavailable(self):
        other = self.temp / 'other'
        make_piece(other, 'lighthouse', BASE_REQUEST)
        d = self.remixed(other, 'lighthouse')
        code, out, [rec] = self.render(d)
        self.assertIn('base lighthouse is not in the kit library', rec['distance']['reason'])
        self.assertIsNone(rec['distance']['pixels'])
        self.assertNotIn('WARNING', out)

    def test_a_kit_base_changed_after_the_remix_is_unavailable(self):
        d = self.remix()
        golden = self.base / 'out' / 'golden' / 'a.png'
        before = golden.read_bytes()
        with Image.open(golden) as image:
            image = image.convert('RGB')
        image.putpixel((0, 0), (250, 20, 200))
        image.save(golden)
        self.assert_unavailable(d, 'base golden out/golden/a.png is not the one this remix copied', logged_error=False)
        golden.write_bytes(before)
        data = json.loads((self.base / 'piece.json').read_text())
        (self.base / 'piece.json').write_text(json.dumps(dict(data, request='a harbour wall at dawn')))
        self.assert_unavailable(d, 'is not the base this remix recorded')

    def test_a_missing_legacy_or_corrupt_baseline_is_unavailable_without_a_warning(self):
        d = self.remix()
        path = d / distance.BASELINE
        good = path.read_text()
        record = json.loads(good)
        legacy = dict(record, base={'id': 'harbour', 'title': 'Harbour', 'status': 'study'})
        cases = {'no remix baseline .pixelate/remix-baseline.json': None,
                 "records no SHA-256 of the base's piece.json": json.dumps(legacy),
                 'invalid remix baseline .pixelate/remix-baseline.json: ': '{',
                 'not a schema 1 remix-baseline': '[]',
                 "is of piece 'other', not 'temple'": json.dumps(dict(record, piece='other')),
                 "names base 'lighthouse', but lineage.remixed_from names 'harbour'":
                     json.dumps(dict(record, base=dict(record['base'], id='lighthouse'))),
                 'base.piece_sha256 is not a SHA-256': json.dumps(dict(record, base=dict(record['base'], piece_sha256='ab'))),
                 '.pixelate/remix-baseline.json records no copied out/golden/a.png':
                     json.dumps(dict(record, files={'piece.json': record['files']['piece.json']}))}
        for reason, text in cases.items():
            with self.subTest(reason=reason):
                path.unlink(missing_ok=True)
                if text is not None:
                    path.write_text(text)
                self.assert_unavailable(d, reason, logged_error='records no copied' not in reason)

    def test_a_linked_baseline_or_baseline_folder_is_never_followed(self):
        # Render refuses a piece with a link anywhere in it first; lookup on its own refuses one too.
        d = self.remix()
        data = json.loads((d / 'piece.json').read_text())
        (d / '.pixelate').rename(self.temp / 'pixelate')
        (d / '.pixelate').symlink_to(self.temp / 'pixelate')
        self.assert_link_refused(d, data)
        (d / '.pixelate').unlink()
        (d / '.pixelate').mkdir()
        (d / distance.BASELINE).symlink_to(self.temp / 'pixelate' / 'remix-baseline.json')
        self.assert_link_refused(d, data)

    def assert_link_refused(self, d, data):
        base = distance.lookup(d, data)
        self.assertIn('unreadable remix baseline .pixelate/remix-baseline.json: ', base['error'])
        rec = distance.measure(frame_bytes(self.base), {'name': 'a', 'scale': 4}, {'w': 64, 'h': 48}, REQUEST, base)
        self.assertEqual((rec['pixels'], rec['palette'], rec['warning']), (None, None, None))


if __name__ == '__main__':
    unittest.main()
