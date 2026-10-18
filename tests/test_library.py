"""Synthetic catalog fixtures: these are not real-corpus search quality claims."""
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / 'tools'
QUARRY = REPO / 'library' / 'quarry-wakes'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('piece_library', TOOLS / 'library.py')
assert spec is not None and spec.loader is not None
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


def fixture(root, piece_id='quarry', status='study', mode='scene', subject='quarry', **tags):
    root = Path(root) / piece_id
    root.mkdir()
    for name in ('art.py', 'brief.md', 'out.png', 'song.wav', 'export.json', 'thumb.png', 'contact.png', 'notes.md'):
        (root / name).write_bytes(b'fixture')
    data = {'schema': 1, 'id': piece_id, 'title': piece_id, 'summary': f'{subject} original scene',
            'request': f'create a {subject}', 'status': status, 'mode': mode, 'runtime': 'script',
            'tags': {'subject': [subject], 'setting': ['outdoor'], 'camera': 'side',
                     'style': 'arcade', 'era': 'none', 'motion': 'stills', 'sound': 'none'},
            'canvas': {'w': 32, 'h': 32, 'scale': 4},
            'outputs': [{'name': 'image', 'kind': 'image', 'run': 'python3 art.py', 'frame': 'out.png',
                         'style': 'arcade', 'scale': 4, 'brief': 'brief.md'},
                        {'name': 'audio', 'kind': 'audio', 'run': 'python3 art.py', 'file': 'song.wav'},
                        {'name': 'export', 'kind': 'export', 'run': 'python3 art.py', 'file': 'export.json'}],
            'anatomy': [{'file': 'art.py', 'draws': 'terrain', 'change_for': 'setting'}],
            'knobs': {}, 'provenance': {'made': '2026-10-18', 'by': 'fixture author'}, 'license': 'MIT'}
    data['tags'].update(tags)
    if status in ('accepted', 'reviewed'):
        data['knobs'] = {'time': {'values': ['day', 'night'], 'default': 'day', 'edits': 'art.py'},
                         'seed': {'type': 'int', 'default': 4, 'edits': 'art.py'}}
        data['media'] = {'thumb': 'thumb.png', 'contact': 'contact.png'}
        data['review'] = {'notes': 'notes.md', 'approved_by': 'art-director', 'record': None}
    save(root, data)
    return root, data


def save(root, data):
    (root / 'piece.json').write_text(json.dumps(data), encoding='utf-8')


class PieceValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.piece, self.data = fixture(self.root)

    def test_typed_outputs_and_source_never_runs(self):
        self.data['outputs'][0]['run'] = 'python3 art.py; touch EXECUTED'
        save(self.piece, self.data)
        self.assertEqual(library.validate(self.piece)['id'], 'quarry')
        self.assertFalse((self.piece / 'EXECUTED').exists())
        self.data['outputs'][1]['frame'] = 'out.png'
        save(self.piece, self.data)
        with self.assertRaises(library.LibraryError):
            library.validate(self.piece)

    def test_status_evidence_not_inferred_from_gate(self):
        for status in ('starter', 'study'):
            self.data['status'] = status
            save(self.piece, self.data)
            self.assertEqual(library.validate(self.piece)['status'], status)
        self.data['status'] = 'accepted'
        save(self.piece, self.data)
        with self.assertRaises(library.LibraryError):
            library.validate(self.piece)
        self.data.update(fixture_accepted(self.data))
        save(self.piece, self.data)
        library.validate(self.piece)
        (self.piece / 'notes.md').write_bytes(b'')
        with self.assertRaisesRegex(library.LibraryError, 'notes cannot be empty'):
            library.validate(self.piece)
        (self.piece / 'notes.md').write_bytes(b'fixture')
        self.data['review']['approved_by'] = None
        save(self.piece, self.data)
        with self.assertRaises(library.LibraryError):
            library.validate(self.piece)

    def test_reviewed_rejects_missing_or_stale_record(self):
        self.data.update(fixture_accepted(self.data))
        self.data['status'] = 'reviewed'
        save(self.piece, self.data)
        with self.assertRaises(library.LibraryError):
            library.validate(self.piece)
        self.data['review']['record'] = 'notes.md'
        save(self.piece, self.data)
        with self.assertRaises(library.LibraryError):
            library.validate(self.piece)

    def test_reviewed_exact_bytes_and_status_ranking(self):
        from tools import review_status
        self.data.update(fixture_accepted(self.data))
        self.data['status'] = 'reviewed'
        report = self.piece / 'lead.md'
        report.write_text('GRADE: A\nSCORES: ' + ' '.join(
            f'{i}={5 if i in (1, 3, 4) else 4}' for i in range(1, 13)) +
            ' originality: pass\nSIGNATURE MOMENT: a striking quarry\n'
            'BIGGEST PROBLEM: small figures\nFIXES (ranked by impact, up to 5; 3 to 5 below A):\n'
            'KEEP: strong hero\n', encoding='utf-8')
        review_status.record(self.piece / 'brief.md', report, self.piece / 'out.png')
        self.data['review']['record'] = 'out.png.visual-review.json'
        save(self.piece, self.data)
        library.validate(self.piece)
        fixture(self.root, 'quarry-study', 'study', subject='quarry')
        fixture(self.root, 'quarry-accepted', 'accepted', subject='quarry')
        self.assertEqual([m['status'] for m in library.find(self.root, 'quarry')['matches']],
                         ['reviewed', 'accepted', 'study'])
        (self.piece / 'out.png').write_bytes(b'changed')
        with self.assertRaisesRegex(library.LibraryError, 'frame changed'):
            library.validate(self.piece)

    def test_unsafe_paths_and_symlinks(self):
        for bad in ('../other', str(self.root / 'other'), 'art/../art.py', 'art\\file', 'a//b', 'a/./b'):
            with self.subTest(path=bad):
                self.data['anatomy'][0]['file'] = bad
                save(self.piece, self.data)
                with self.assertRaises(library.LibraryError):
                    library.validate(self.piece)
        self.data['anatomy'][0]['file'] = 'art.py'
        (self.piece / 'hidden').symlink_to(self.root)
        save(self.piece, self.data)
        with self.assertRaisesRegex(library.LibraryError, 'symlink'):
            library.validate(self.piece)

    def test_schema_tags_knobs_and_duplicates(self):
        for key, invalid in (('schema', True), ('status', 'approved')):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.data)
                changed[key] = invalid
                save(self.piece, changed)
                with self.assertRaises(library.LibraryError):
                    library.validate(self.piece)
        for key, invalid in (('subject', ['quarry', 'quarry']), ('camera', 'underwater'), ('motion', 'movie')):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.data)
                changed['tags'][key] = invalid
                save(self.piece, changed)
                with self.assertRaises(library.LibraryError):
                    library.validate(self.piece)
        save(self.piece, self.data)
        self.data['knobs'] = {'time': {'values': [True, 1], 'default': None, 'edits': 'art.py'}}
        save(self.piece, self.data)
        with self.assertRaises(library.LibraryError):
            library.validate(self.piece)
        (self.piece / 'piece.json').write_text('{"schema": 1, "schema": 1}', encoding='utf-8')
        with self.assertRaisesRegex(library.LibraryError, 'duplicate JSON key'):
            library.validate(self.piece)
        (self.piece / 'piece.json').write_text('{"schema": NaN}', encoding='utf-8')
        with self.assertRaisesRegex(library.LibraryError, 'nonfinite JSON number'):
            library.validate(self.piece)


A_LEAD = ('GRADE: A\nSCORES: ' + ' '.join(f'{i}={5 if i in (1, 3, 4) else 4}' for i in range(1, 13)) +
          ' originality: pass\nSIGNATURE MOMENT: a striking quarry\nBIGGEST PROBLEM: small figures\n'
          'FIXES (ranked by impact, up to 5; 3 to 5 below A):\nKEEP: strong hero\n')


class ImageOutputContract(unittest.TestCase):
    """Image outputs carry the `tools/render.py` render.json image fields."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_converted_06_quarry_wakes_render_json_keeps_gate_fields(self):
        piece = self.root / 'quarry-wakes'
        shutil.copytree(QUARRY, piece, ignore=shutil.ignore_patterns('__pycache__'))
        # render.json was folded into piece.json outputs; its image fields are what the manifest keeps.
        images = [{key: value for key, value in output.items() if key not in ('kind', 'golden')}
                  for output in json.loads((QUARRY / 'piece.json').read_text(encoding='utf-8'))['outputs']
                  if output['kind'] == 'image']
        outputs = [{'kind': 'image', **image} for image in images]
        outputs.append({'name': 'sound', 'kind': 'audio', 'run': 'python3 sound/sting.py', 'file': 'sound/06-sample.mp3'})
        request = next(line for line in (QUARRY / 'brief.md').read_text(encoding='utf-8').splitlines()
                       if line.startswith('Request: '))[len('Request: '):]
        data = {'schema': 1, 'id': 'quarry-wakes', 'title': 'The Quarry Wakes', 'status': 'study',
                'summary': 'A dredging machine breaks out of a flooded quarry; its leg slams the rim.',
                'request': request, 'mode': 'scene', 'runtime': 'script',
                'tags': {'subject': ['quarry', 'machine', 'boss', 'water', 'rock', 'dust'],
                         'setting': ['industrial', 'outdoor', 'day'], 'camera': 'side', 'style': 'arcade',
                         'era': 'neogeo', 'motion': 'stills', 'sound': 'sting'},
                'canvas': {'w': 304, 'h': 224, 'scale': 4}, 'outputs': outputs,
                'knobs': {'time': {'values': ['day', 'dusk'], 'default': 'day', 'edits': 'art/pal.py'},
                          'seed': {'type': 'int', 'default': 17, 'edits': 'art/scene.py'}},
                'anatomy': [{'file': f'art/{name}.py', 'draws': draws, 'change_for': change} for name, draws, change in (
                    ('pal', 'palette slots and ramps', 'colour, time of day'),
                    ('world', 'terrain, rock strata, water', 'the setting'),
                    ('boss', 'the machine', 'the hero creature or machine'),
                    ('soldier', 'small figures', 'people, scale cues'),
                    ('fx_cells', 'dust and spray', 'effects'),
                    ('scene', 'composition of moments A and B', 'camera, framing, story beat'))],
                'provenance': {'made': '2026-10-17', 'by': 'agent with art director'}, 'license': 'MIT'}
        save(piece, data)
        generated = [image[key] for image in images for key in ('pal', 'actor')]
        self.assertTrue(generated)
        self.assertFalse(any((piece / path).exists() for path in generated))
        manifest = library.validate(piece)
        self.assertEqual([o for o in manifest['outputs'] if o['kind'] == 'image'], outputs[:2])
        self.assertEqual(library.find(self.root, 'a giant boss machine bursts from a flooded quarry')['matches'][0]['id'],
                         'quarry-wakes')
        # A generated path, once written by a render, is still checked: regular file, never a link.
        (piece / images[0]['pal']).write_text('{}', encoding='utf-8')
        library.validate(piece)
        (piece / images[0]['pal']).unlink()
        (piece / images[0]['pal']).mkdir()
        with self.assertRaisesRegex(library.LibraryError, 'wrong file type'):
            library.validate(piece)

    def test_render_docstring_fields_and_style_or_era(self):
        piece, data = fixture(self.root)
        image = {'name': 'image', 'kind': 'image', 'run': 'python3 art.py', 'frame': 'out.png',
                 'style': 'cosy-lightmap', 'scene': 'exterior', 'scale': 4, 'brief': 'brief.md',
                 'pal': 'gen/palette.json', 'pre': 'gen/01-a@1x.png', 'used': 'light,shaft,rain:hair',
                 'intent': 'gen/intent.png', 'actor': '', 'era': '', 'judge_ignore': 'masonry,repeat_units'}
        data['outputs'][0] = image
        save(piece, data)
        library.validate(piece)
        for change in ({'style': '', 'scene': '', 'era': 'neogeo'}, {'style': 'arcade', 'scene': ''},
                       {'era': 'nes'}):
            with self.subTest(change=change):
                data['outputs'][0] = {**image, **change}
                save(piece, data)
                library.validate(piece)
        minimal = {'name': 'image', 'kind': 'image', 'run': 'python3 art.py', 'frame': 'out.png', 'era': 'gameboy'}
        data['outputs'][0] = minimal
        save(piece, data)
        library.validate(piece)
        bad = ({'era': ''}, {'era': 'atari'}, {'style': 'arcade', 'scene': 'exterior'}, {'scene': 'beam'},
               {'scale': 0}, {'scale': '4'}, {'brief': 'missing.md'}, {'pal': '../palette.json'},
               {'pre': '/tmp/pre.png'}, {'actor': 'out.png/mask.png'}, {'intent': 'a//b.png'}, {'used': 'glow;rm'},
               {'judge_ignore': 'masonry, murky'}, {'actor': 4}, {'frame': '../out.png'}, {'lights': 'on'})
        for change in bad:
            with self.subTest(change=change):
                data['outputs'][0] = {**minimal, **change}
                save(piece, data)
                with self.assertRaises(library.LibraryError):
                    library.validate(piece)
        data['outputs'][0] = {**minimal, 'pal': 'gen/palette.json'}
        save(piece, data)
        (piece / 'gen').symlink_to(self.root)
        with self.assertRaisesRegex(library.LibraryError, 'symlink'):
            library.validate(piece)


class GeneratedOutputs(unittest.TestCase):
    """An image `frame` and an audio or export `file` are written by the run command: validation needs a
    safe path inside the piece, not a rendered file, and never takes a declaration as a render."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.piece, self.data = fixture(self.root)
        self.data['outputs'][0]['frame'] = 'out/a.png'
        self.data['outputs'][1]['file'] = 'sound/song.wav'
        self.data['outputs'][2]['file'] = 'out/export.json'
        save(self.piece, self.data)

    def test_missing_but_safe_frame_and_files_validate_without_being_written(self):
        before = sorted(p.relative_to(self.piece).as_posix() for p in self.piece.rglob('*'))
        self.assertEqual(library.validate(self.piece)['id'], 'quarry')
        (self.piece / 'out').mkdir()
        library.validate(self.piece)
        self.assertEqual(sorted(p.relative_to(self.piece).as_posix() for p in self.piece.rglob('*')), sorted(before + ['out']))
        (self.piece / 'out' / 'a.png').write_bytes(b'rendered')
        library.validate(self.piece)

    def test_checked_in_inputs_are_still_required(self):
        for where, change in (('output.golden', {'golden': 'out/golden/image.png'}),
                              ('output.brief', {'brief': 'missing.md'})):
            with self.subTest(field=where):
                data = copy.deepcopy(self.data)
                data['outputs'][0].update(change)
                save(self.piece, data)
                with self.assertRaisesRegex(library.LibraryError, where):
                    library.validate(self.piece)
        for key, value in (('anatomy', [{'file': 'missing.py', 'draws': 'x', 'change_for': 'y'}]),
                           ('media', {'thumb': 'missing.png'})):
            with self.subTest(field=key):
                save(self.piece, {**self.data, key: value})
                with self.assertRaisesRegex(library.LibraryError, 'missing path'):
                    library.validate(self.piece)
        save(self.piece, {**self.data, 'review': {'notes': 'missing.md', 'approved_by': None, 'record': None}})
        with self.assertRaisesRegex(library.LibraryError, 'review.notes'):
            library.validate(self.piece)

    def test_unsafe_generated_paths_fail(self):
        (self.piece / 'out').mkdir()
        (self.piece / 'out' / 'dir.png').mkdir()
        os.mkfifo(self.piece / 'out' / 'pipe.wav')
        for index, key in ((0, 'frame'), (1, 'file'), (2, 'file')):
            for bad, message in (('../outside.png', 'unsafe relative path'), ('out/../a.png', 'unsafe relative path'),
                                 (str(self.root / 'a.png'), 'unsafe relative path'),
                                 ('art.py/a.png', 'unsafe path'), ('out/dir.png', 'wrong file type'),
                                 ('out/pipe.wav', 'wrong file type')):
                with self.subTest(output=index, path=bad):
                    data = copy.deepcopy(self.data)
                    data['outputs'][index][key] = bad
                    save(self.piece, data)
                    with self.assertRaisesRegex(library.LibraryError, f'output.{key}: {message}'):
                        library.validate(self.piece)

    def test_linked_generated_paths_fail(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'a.png').write_bytes(b'canary')
        for link, target in (('out', outside), ('out/a.png', outside / 'a.png'), ('out/a.png', outside / 'gone.png'),
                             ('sound', outside)):
            with self.subTest(link=link, target=target.name):
                if link.startswith('out/'):
                    (self.piece / 'out').mkdir(exist_ok=True)
                (self.piece / link).symlink_to(target)
                with self.assertRaisesRegex(library.LibraryError, 'symlink'):
                    library.validate(self.piece)
                # A link is a declaration error even where the catalog-wide link scan does not reach.
                with self.assertRaisesRegex(library.LibraryError, 'symlink'):
                    library.generated(self.piece, 'out/a.png' if link != 'sound' else 'sound/song.wav', 'output')
                (self.piece / link).unlink()


class RealLibrary(unittest.TestCase):
    """The checked-in manifests validate as committed, with their goldens and sizes, before any render."""

    def test_lantern_isle_validates_unmodified_before_its_frames_are_rendered(self):
        source = REPO / 'library' / 'lantern-isle'
        with tempfile.TemporaryDirectory() as temp:
            piece = Path(temp) / 'lantern-isle'
            shutil.copytree(source, piece, ignore=shutil.ignore_patterns('.pixelate', '__pycache__'))
            outputs = json.loads((piece / 'piece.json').read_text(encoding='utf-8'))['outputs']
            for output in outputs:
                (piece / output['frame']).unlink(missing_ok=True)
            self.assertEqual((piece / 'piece.json').read_bytes(), (source / 'piece.json').read_bytes())
            manifest = library.validate(piece)
            self.assertEqual([o['golden'] for o in manifest['outputs']],
                             [f"out/golden/{name}.png" for name in ('spring', 'summer', 'fall', 'winter')])
            self.assertTrue(all('size' in o for o in manifest['outputs']))
            self.assertFalse(any((piece / o['frame']).exists() for o in outputs))
            (piece / 'out' / 'golden' / 'spring.png').unlink()
            with self.assertRaisesRegex(library.LibraryError, 'output.golden'):
                library.validate(piece)

    def test_every_checked_in_piece_validates(self):
        pieces = library.scan(REPO / 'library')
        self.assertIn('lantern-isle', pieces)
        self.assertTrue(all(p['status'] in library.STATUSES for p in pieces.values()))


def documented_example(path, marker):
    """The JSON example after `marker` in a doc, written into a temporary piece with stand-in files."""
    doc = path.read_text(encoding='utf-8')
    return json.loads(doc[doc.index('```json\n', doc.index(marker)) + 8:].split('```', 1)[0])


class DocumentedExamples(unittest.TestCase):
    def test_plan_and_spec_examples_validate(self):
        for path, marker in ((REPO / 'docs' / 'PLAN-library.md', 'Example for The Quarry Wakes'),
                             (REPO / 'references' / 'piece.md', 'Example (')):
            with self.subTest(doc=path.name), tempfile.TemporaryDirectory() as temp:
                data = documented_example(path, marker)
                piece = Path(temp) / data['id']
                files = [o.get('frame') or o['file'] for o in data['outputs']] + [o['brief'] for o in data['outputs'] if 'brief' in o]
                files += [a['file'] for a in data['anatomy']] + [k['edits'] for k in data['knobs'].values()]
                files += [v for v in data['media'].values() if v] + [data['review']['notes']]
                for name in files:
                    (piece / name).parent.mkdir(parents=True, exist_ok=True)
                    (piece / name).write_bytes(b'stand-in')
                save(piece, data)
                self.assertEqual(library.validate(piece)['status'], 'accepted')
                self.assertFalse((piece / 'out' / 'palette.json').exists())
                data['recipes'] = ['rock_face', 'rock_face']
                save(piece, data)
                with self.assertRaisesRegex(library.LibraryError, 'recipe'):
                    library.validate(piece)


def run_review_record(piece, report):
    result = subprocess.run([sys.executable, str(REPO / 'pixelate'), 'review', 'record', '--brief', 'brief.md',
                             '--frame', 'out.png', '--critique', str(report)], cwd=piece, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


class RelocatedReview(unittest.TestCase):
    """A reviewed piece stays reviewed when its folder moves, and only then."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'checkout-a').mkdir()
        self.piece, self.data = fixture(self.root / 'checkout-a', status='reviewed')
        (self.piece / 'brief.md').write_text('# Full brief\n## 0. Choices\nA quarry\n', encoding='utf-8')
        (self.piece / 'history').mkdir()
        (self.piece / 'history' / 'lead.md').write_text(A_LEAD, encoding='utf-8')
        self.data['review']['record'] = 'out.png.visual-review.json'
        save(self.piece, self.data)

    def copy(self):
        target = self.root / 'elsewhere' / 'nested' / 'quarry'
        shutil.copytree(self.piece, target)
        return target

    def test_recorded_piece_validates_after_copy_to_another_parent(self):
        self.assertIn('RECORDED A still review', run_review_record(self.piece, Path('history/lead.md')))
        record = json.loads((self.piece / 'out.png.visual-review.json').read_text(encoding='utf-8'))
        self.assertTrue(Path(record['report']).is_absolute())
        library.validate(self.piece)
        moved = self.copy()
        shutil.rmtree(self.piece)
        self.assertEqual(library.validate(moved)['status'], 'reviewed')
        self.assertEqual(library.find(moved.parent, 'quarry')['matches'][0]['status'], 'reviewed')
        for name, expected in (('history/lead.md', 'report changed'), ('out.png', 'frame changed'),
                               ('brief.md', 'brief changed')):
            with self.subTest(tampered=name):
                original = (moved / name).read_bytes()
                (moved / name).write_bytes(original + b'!')
                with self.assertRaisesRegex(library.LibraryError, expected):
                    library.validate(moved)
                (moved / name).write_bytes(original)
        library.validate(moved)
        sidecar = moved / 'out.png.visual-review.json'
        sidecar.write_bytes(sidecar.read_bytes().replace(b'"grade": "A"', b'"grade":"A"'))
        with self.assertRaisesRegex(library.LibraryError, 'noncanonical'):
            library.validate(moved)

    def test_reviewed_needs_the_reviewed_frame_and_sidecar_to_exist(self):
        # A frame is a generated output and may be absent for other statuses; a review binds its bytes.
        run_review_record(self.piece, Path('history/lead.md'))
        library.validate(self.piece)
        frame = (self.piece / 'out.png').read_bytes()
        (self.piece / 'out.png').unlink()
        with self.assertRaisesRegex(library.LibraryError, 'NOT READY: .*out.png'):
            library.validate(self.piece)
        (self.piece / 'out.png').write_bytes(frame)
        library.validate(self.piece)
        (self.piece / 'out.png.visual-review.json').unlink()
        with self.assertRaisesRegex(library.LibraryError, 'review.record: missing path'):
            library.validate(self.piece)

    def test_renamed_external_report_and_symlink_copies_fail(self):
        run_review_record(self.piece, Path('history/lead.md'))
        renamed = self.root / 'renamed' / 'other-quarry'
        shutil.copytree(self.piece, renamed)
        self.data['id'] = 'other-quarry'
        save(renamed, self.data)
        with self.assertRaisesRegex(library.LibraryError, 'do not match this piece'):
            library.validate(renamed)
        linked = self.copy()
        report = linked / 'history' / 'lead.md'
        (self.root / 'lead.md').write_bytes(report.read_bytes())
        report.unlink()
        report.symlink_to(self.root / 'lead.md')
        with self.assertRaisesRegex(library.LibraryError, 'symlink'):
            library.validate(linked)
        external = self.root / 'external-lead.md'
        external.write_text(A_LEAD, encoding='utf-8')
        run_review_record(self.piece, external)
        with self.assertRaisesRegex(library.LibraryError, 'outside the piece'):
            library.validate(self.piece)


def fixture_accepted(data):
    return {'knobs': {'time': {'values': ['day', 'night'], 'default': 'day', 'edits': 'art.py'},
                      'seed': {'type': 'int', 'default': 4, 'edits': 'art.py'}},
            'media': {'thumb': 'thumb.png', 'contact': 'contact.png'},
            'review': {'notes': 'notes.md', 'approved_by': 'art-director', 'record': None}}


class CatalogSearch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture(self.root, 'quarry', 'accepted', subject='quarry')
        fixture(self.root, 'forest', 'study', subject='forest')
        fixture(self.root, 'ocean', 'study', subject='ocean')
        fixture(self.root, 'castle', 'study', subject='castle')
        fixture(self.root, 'starter-scene', 'starter', subject='blank')
        fixture(self.root, 'tiles', 'study', 'assets', subject='tileset')

    def test_stable_index_list_show_and_entry_point(self):
        first = library.write_index(self.root)
        self.assertEqual(first, library.write_index(self.root))
        self.assertEqual(first, (self.root / 'index.json').read_bytes())
        self.assertEqual([p['id'] for p in library.list_pieces(self.root)], sorted(library.scan(self.root)))
        self.assertEqual(library.show(self.root, 'forest')['id'], 'forest')
        output = subprocess.check_output([sys.executable, str(TOOLS / 'library.py'), '--library',
                                          str(self.root), 'find', 'forest'], text=True)
        self.assertEqual(json.loads(output)['matches'][0]['id'], 'forest')
        (self.root / 'index.json').unlink()
        (self.root / 'index.json').symlink_to(self.root / 'unsafe-index')
        with self.assertRaises(library.LibraryError):
            library.write_index(self.root)

    def test_20_labelled_search_cases(self):
        # Requests against synthetic pieces; expected top result, None means abstain.
        cases = [
            ('quarry at dusk', 'quarry'), ('a quarry machine', 'quarry'),
            ('quarry industrial', 'quarry'), ('quarry with rocks', 'quarry'),
            ('the quarry returns', 'quarry'), ('forest at dawn', 'forest'),
            ('a forest in rain', 'forest'), ('forest canopy', 'forest'),
            ('a forest machine', 'forest'), ('forest wildlife', 'forest'),
            ('ocean at night', 'ocean'), ('an ocean boat', 'ocean'),
            ('ocean storm', 'ocean'), ('ocean waves', 'ocean'),
            ('ocean sunset', 'ocean'), ('castle walls', 'castle'),
            ('castle towers', 'castle'), ('castle interior', 'castle'),
            ('castle under siege', 'castle'), ('jellyfish nebula', None),
        ]
        self.assertEqual(len(cases), 20)
        for request, expected in cases:
            with self.subTest(request=request):
                matches = library.find(self.root, request)['matches']
                self.assertEqual(matches[0]['id'] if matches else None, expected)
                self.assertEqual(library.find(self.root, request)['fallback']['ids'], ['starter-scene'])

    def test_library_root_ignores_readme_and_ds_store_only(self):
        (self.root / 'README.md').write_text('# Library\n', encoding='utf-8')
        (self.root / '.DS_Store').write_bytes(b'\x00')
        self.assertIn('quarry', library.scan(self.root))
        (self.root / 'notes.txt').write_text('stray', encoding='utf-8')
        with self.assertRaisesRegex(library.LibraryError, 'unexpected catalog entry'):
            library.scan(self.root)

    def test_deeply_nested_manifest_is_library_error_exit_2(self):
        (self.root / 'quarry' / 'piece.json').write_text('[' * 100000, encoding='utf-8')
        with self.assertRaisesRegex(library.LibraryError, 'nested too deeply'):
            library.validate(self.root / 'quarry')
        result = subprocess.run([sys.executable, str(TOOLS / 'library.py'), '--library', str(self.root), 'list'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('nested too deeply', result.stderr)

    def test_mode_required_conflicts_and_no_match(self):
        self.assertEqual(library.find(self.root, 'tileset', mode='assets')['matches'][0]['id'], 'tiles')
        self.assertEqual(library.find(self.root, 'tileset', mode='scene')['matches'], [])
        self.assertEqual(library.find(self.root, 'quarry top-down')['matches'], [])
        self.assertEqual(library.find(self.root, 'quarry nes')['matches'], [])
        self.assertEqual(library.find(self.root, 'unicorn galaxies')['matches'], [])
        self.assertEqual(library.find(self.root, 'side view')['matches'], [])
        self.assertEqual(library.find(self.root, 'make original pixel art')['matches'], [])
        self.assertEqual(library.find(self.root, 'quarry', mode='music')['fallback']['kind'], 'author')
        self.assertIn('unmatched term: dusk', library.find(self.root, 'quarry at dusk')['matches'][0]['differs'])


class RealisticSearch(unittest.TestCase):
    """Common words in a real title, summary and request must not make an unrelated request match."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        request = next(line for line in (QUARRY / 'brief.md').read_text(encoding='utf-8').splitlines()
                       if line.startswith('Request: '))[len('Request: '):]
        _, quarry = fixture(self.root, 'quarry-wakes', 'accepted', subject='quarry', style='arcade', era='neogeo')
        quarry.update(title='The Quarry Wakes', request=request,
                      summary='A dredging machine breaks out of a flooded quarry; its leg slams the rim.')
        quarry['tags'].update(subject=['quarry', 'machine', 'boss', 'water', 'rock', 'dust'],
                              setting=['industrial', 'outdoor', 'day'])
        save(self.root / 'quarry-wakes', quarry)
        _, signal = fixture(self.root, 'tidewater-signal', 'study', subject='lighthouse')
        signal.update(title='Tidewater Signal', summary='A lighthouse keeps its lamp lit through a storm at sea.',
                      request='a lighthouse in a storm, its beam sweeping out over the sea at night')
        signal['tags'].update(subject=['lighthouse', 'storm', 'sea'], setting=['coast', 'night'])
        save(self.root / 'tidewater-signal', signal)
        fixture(self.root, 'starter-scene', 'starter', subject='blank')

    def top(self, request):
        matches = library.find(self.root, request)['matches']
        return [match['id'] for match in matches]

    def test_common_and_descriptive_words_alone_abstain(self):
        for request in ('a cosy cafe interior on a rainy day',
                        'its tail curls up as the cat naps in a sunny window',
                        "a kid's day out at the fair",
                        'an old train pulls out of the station',
                        'wake up to a sunrise over lavender fields',
                        'a snowy log cabin at dusk with one lit window',
                        'a soldier in a mustard coat at a bus stop, outdoor day',
                        'make some original pixel art of it'):
            with self.subTest(request=request):
                result = library.find(self.root, request)
                self.assertEqual(result['matches'], [])
                self.assertEqual(result['fallback'], {'kind': 'starter', 'ids': ['starter-scene']})

    def test_useful_positives_rank_the_relevant_piece(self):
        for request, expected in (('a giant machine rises from a flooded quarry', 'quarry-wakes'),
                                  ('arcade boss fight: a rusted dredger bursts out of water', 'quarry-wakes'),
                                  ('quarries and falling rocks at dusk', 'quarry-wakes'),
                                  ('an old lighthouse keeper looks out to sea', 'tidewater-signal'),
                                  ('a storm batters the lighthouse at night', 'tidewater-signal')):
            with self.subTest(request=request):
                self.assertEqual(self.top(request), [expected])
        why = library.find(self.root, 'a dusty quarry machine on a rainy day')['matches'][0]
        self.assertEqual(why['why'], ['subject: machine', 'subject: quarry', 'setting: day'])
        self.assertIn('unmatched term: rainy', why['differs'])

    def test_status_never_creates_relevance(self):
        self.assertEqual(self.top('dust'), ['quarry-wakes'])
        self.assertEqual(self.top('day industrial outdoor arcade neogeo'), [])
        self.assertEqual(self.top('side view at night'), [])


if __name__ == '__main__':
    unittest.main()
