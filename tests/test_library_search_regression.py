"""`find` on the real checked-in library with the labelled cases in tools/library_search_cases.py.

The cases are author-created and corpus-aware: an in-sample routing regression, not a held-out search
benchmark and not evidence of art quality or status. Search is static, so the test also checks it
neither runs piece code nor writes the library.
"""
import hashlib
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / 'tools'
LIBRARY = REPO / 'library'
sys.path.insert(0, str(TOOLS))  # validate imports the kit's styles table


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


library = load('piece_library', TOOLS / 'library.py')
cases = load('library_search_cases', TOOLS / 'library_search_cases.py')
CASES, NO_MATCH_CASES = cases.CASES, cases.NO_MATCH_CASES

THRESHOLD = 16  # plan section 12: the expected piece in the top 3 for at least 80% of 20 requests


def tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def outcome(request, expected):
    """(hit, top ids, fallback) for one case."""
    result = library.find(LIBRARY, request)
    top = [match['id'] for match in result['matches']]
    if isinstance(expected, tuple):
        hit = not top and result['fallback'] == {'kind': 'starter', 'ids': [expected[1]]}
    else:
        hit = expected in top
    return hit, top, result['fallback']


class LabelledCases(unittest.TestCase):
    def test_cases_cover_every_piece_once_and_each_starter_kind(self):
        pieces = library.scan(LIBRARY)
        self.assertEqual(len(CASES), 20)
        finished = [expected for _, expected in CASES if isinstance(expected, str)]
        starters = [expected[1] for _, expected in CASES if isinstance(expected, tuple)]
        self.assertEqual(sorted(finished), sorted(p for p, m in pieces.items() if m['status'] != 'starter'))
        self.assertEqual(sorted(starters), sorted(p for p, m in pieces.items() if m['status'] == 'starter'))
        for request, expected in CASES:
            with self.subTest(request=request):
                piece = pieces[expected[1] if isinstance(expected, tuple) else expected]
                if '-' in piece['id']:  # a place name such as Santorini may appear; a slug may not
                    self.assertNotIn(piece['id'], request.lower())
                self.assertNotIn(request.lower(), (piece['request'] + ' ' + piece['summary']).lower())

    def test_at_least_16_of_20_cases_rank_the_expected_piece_or_starter(self):
        misses = []
        for request, expected in CASES:
            hit, top, fallback = outcome(request, expected)
            if not hit:
                misses.append(f'{request!r}: expected {expected}, got {top} with fallback {fallback}')
        score = len(CASES) - len(misses)
        self.assertGreaterEqual(score, THRESHOLD, f'{score}/20; misses:\n' + '\n'.join(misses))

    def test_starter_cases_match_no_finished_piece(self):
        # The assets case has no image: a sprite-sheet request must fall back to starter-assets rather than
        # match a pack only because its tags name the same asset format.
        for request, expected in CASES:
            if isinstance(expected, tuple):
                with self.subTest(request=request):
                    result = library.find(LIBRARY, request)
                    self.assertEqual(result['matches'], [])
                    self.assertEqual(result['fallback'], {'kind': 'starter', 'ids': [expected[1]]})
                    self.assertEqual(result['mode'], library.show(LIBRARY, expected[1])['mode'])

    def test_no_match_requests_abstain(self):
        starters = {m['mode']: p for p, m in library.scan(LIBRARY).items() if m['status'] == 'starter'}
        for request, mode in NO_MATCH_CASES:
            with self.subTest(request=request):
                result = library.find(LIBRARY, request)
                self.assertEqual(result['mode'], mode)
                self.assertEqual(result['matches'], [])
                # era and rebuild have no starter yet, so find returns the author-new-piece plan.
                self.assertEqual(result['fallback'], {'kind': 'starter', 'ids': [starters[mode]]} if mode in starters
                                 else {'kind': 'author', 'reason': 'no matching starter; author a new piece'})

    def test_search_runs_no_piece_code_and_writes_nothing(self):
        before = tree(LIBRARY)
        modules = set(sys.modules)
        refuse = mock.Mock(side_effect=AssertionError('search started a process'))
        with mock.patch.object(subprocess, 'Popen', refuse), mock.patch.object(os, 'system', refuse), \
                mock.patch.object(os, 'posix_spawn', refuse), mock.patch.object(os, 'fork', refuse):
            for request, _ in CASES + NO_MATCH_CASES:
                library.find(LIBRARY, request)
            library.index(LIBRARY)
        loaded = [name for name in set(sys.modules) - modules
                  if str(getattr(sys.modules[name], '__file__', '') or '').startswith(str(LIBRARY))]
        self.assertEqual(loaded, [])
        refuse.assert_not_called()
        self.assertEqual(tree(LIBRARY), before)


if __name__ == '__main__':
    unittest.main()
