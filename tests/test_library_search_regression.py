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
AUTHOR = {'kind': 'author', 'reason': 'no matching starter; author a new piece'}
# no-match requests whose explicit tags exclude every starter of their mode: the honest plan is to author
AUTHOR_NO_MATCH = {'a Game Boy style dungeon crawler with skeletons and torches'}


def tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def mode_starters():
    """{mode: [starter ids]}: find falls back to every starter of the request's mode, in id order."""
    starters = {}
    for piece_id, manifest in library.scan(LIBRARY).items():
        if manifest['status'] == 'starter':
            starters.setdefault(manifest['mode'], []).append(piece_id)
    return starters


def outcome(request, expected):
    """(hit, top ids, fallback) for one case. A starter case hits when find abstains and falls back to
    exactly the starters of the expected starter's mode (the expected one among them)."""
    result = library.find(LIBRARY, request)
    top = [match['id'] for match in result['matches']]
    if isinstance(expected, tuple):
        ids = mode_starters()[library.show(LIBRARY, expected[1])['mode']]
        hit = not top and result['fallback'] == {'kind': 'starter', 'ids': ids}
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
        # the scored starter cases name the three phase-1 starters, one per kind
        self.assertEqual(sorted(starters), ['starter-assets', 'starter-music', 'starter-scene-loop'])
        # the phase-2 starters have no scored case of their own (the 20 cases are frozen); every starter
        # is still the fallback of at least one labelled request, scored or no-match
        offered = set()
        for request, _ in CASES + NO_MATCH_CASES:
            fallback = library.find(LIBRARY, request)['fallback']
            offered |= set(fallback.get('ids', ()))
        self.assertEqual(sorted(offered), sorted(p for p, m in pieces.items() if m['status'] == 'starter'))
        self.assertLessEqual(set(starters), offered)
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
                    ids = mode_starters()[library.show(LIBRARY, expected[1])['mode']]
                    self.assertEqual(result['fallback'], {'kind': 'starter', 'ids': ids})
                    self.assertEqual(result['mode'], library.show(LIBRARY, expected[1])['mode'])

    def test_no_match_requests_abstain(self):
        starters = mode_starters()
        for request, mode in NO_MATCH_CASES:
            with self.subTest(request=request):
                result = library.find(LIBRARY, request)
                self.assertEqual(result['mode'], mode)
                self.assertEqual(result['matches'], [])
                # a mode with no starter, or only starters its explicit tags exclude, gets the author plan.
                self.assertEqual(result['fallback'], {'kind': 'starter', 'ids': starters[mode]}
                                 if mode in starters and request not in AUTHOR_NO_MATCH else AUTHOR)

    def test_explicit_tags_gate_starters_like_finished_pieces(self):
        # (request, expected fallback ids or None for the author plan)
        for request, ids in [
            ('a Game Boy quiet meadow screen', None),                       # the only era starter is NES
            ('a gameboy title screen', None),
            ('an NES quiet meadow screen', ['starter-era-nes']),
            ('a quiet meadow on the nes console, no tags', ['starter-era-nes']),
            ('rebuild my photo in one-point perspective', None),          # the only rebuild starter is two-point
            ('rebuild my photo in two-point perspective', ['starter-rebuild-perspective']),
            ('rebuild my photo', ['starter-rebuild-perspective']),
            ('a looping seaside scene', ['starter-scene-loop']),
            ('a still seaside scene', ['starter-scene-still']),
            ('a seaside scene', ['starter-scene-loop', 'starter-scene-still']),
            ('a seaside scene in pico-8 style', None),
            ('a pastel-cell seaside scene', None),                         # both scene starters are lofi
            ('a lofi seaside scene', ['starter-scene-loop', 'starter-scene-still']),
            ('an isometric seaside scene', None),                          # both scene starters are side
            ('a side view seaside scene', ['starter-scene-loop', 'starter-scene-still']),
        ]:
            with self.subTest(request=request):
                result = library.find(LIBRARY, request)
                self.assertEqual(result['matches'], [])
                self.assertEqual(result['fallback'], {'kind': 'starter', 'ids': ids} if ids else AUTHOR)

    def test_mode_without_explicit_tags_offers_every_starter_of_the_mode(self):
        for mode, ids in mode_starters().items():
            with self.subTest(mode=mode):
                result = library.find(LIBRARY, 'zzz', mode=mode)
                self.assertEqual(result['fallback'], {'kind': 'starter', 'ids': ids})

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
