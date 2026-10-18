"""Synthetic catalog fixtures: these are not real-corpus search quality claims."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
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


if __name__ == '__main__':
    unittest.main()
