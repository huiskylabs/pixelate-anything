"""Recipe reverse lookup reads manifest declarations, never imports or runs a piece."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import library  # noqa: E402


class RecipeUsage(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.catalog = Path(temporary.name) / 'library'
        self.catalog.mkdir()
        self.piece = self.catalog / 'starter-scene-still'
        shutil.copytree(REPO / 'library/starter-scene-still', self.piece)

    def declare(self, names):
        path = self.piece / 'piece.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['recipes'] = names
        path.write_text(json.dumps(manifest), encoding='utf-8')

    def test_declared_reverse_lookup_is_static_not_verified_use(self):
        self.declare(['rock_face'])
        with mock.patch('subprocess.Popen', side_effect=AssertionError('ran program')), \
                mock.patch('subprocess.run', side_effect=AssertionError('ran program')):
            result = library.recipe_usage(self.catalog)
            selected = library.recipe_usage(self.catalog, 'rock_face')
        self.assertIn('not proof', result['note'])
        self.assertEqual(selected['pieces'], ['starter-scene-still'])
        self.assertEqual(next(r['pieces'] for r in result['recipes'] if r['name'] == 'rock_face'),
                         ['starter-scene-still'])
        self.assertEqual(next(r['pieces'] for r in result['recipes'] if r['name'] == 'pouring_fall'), [])
        self.assertEqual(list(self.catalog.iterdir()), [self.piece])

    def test_unknown_recipe_is_refused_without_running_any_code(self):
        self.declare(['invented_recipe'])
        with self.assertRaisesRegex(library.LibraryError, 'not a function'):
            library.recipe_usage(self.catalog)
        with self.assertRaisesRegex(library.LibraryError, 'unknown function'):
            library.recipe_usage(self.catalog, 'invented_recipe')

    def test_cli_lists_existing_functions_even_with_no_declared_users(self):
        result = library.recipe_usage(self.catalog)
        self.assertIn('rock_face', [r['name'] for r in result['recipes']])
        self.assertTrue(all(r['pieces'] == [] for r in result['recipes']))


if __name__ == '__main__':
    unittest.main()
