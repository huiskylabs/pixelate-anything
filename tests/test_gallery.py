"""The gallery is static and rights-filtered; a ledger is not proof a permission is genuine."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
import gallery  # noqa: E402
import library  # noqa: E402


class Gallery(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.catalog = self.root / 'library'
        self.catalog.mkdir()
        self.piece = self.catalog / 'starter-scene-still'
        shutil.copytree(REPO / 'library/starter-scene-still', self.piece)
        (self.piece / 'history').mkdir(exist_ok=True)
        (self.piece / 'history/rights.md').write_text('Test fixture only: a rights record.\n')
        (self.root / 'docs/gallery').mkdir(parents=True)
        (self.root / 'README.md').write_text('# Test\n\n' + gallery.START + '\nold\n' + gallery.END + '\n')
        self.ledger = self.root / 'docs/gallery/permissions.json'
        self.set_permissions({})
        library.write_index(self.catalog)

    def set_permissions(self, records):
        self.ledger.write_text(json.dumps({'schema': 1, 'pieces': records}), encoding='utf-8')

    def build(self, check=False):
        return gallery.build(self.catalog, self.ledger, self.root, check=check)

    def test_no_permission_publishes_no_cards_or_media(self):
        with mock.patch('subprocess.Popen', side_effect=AssertionError('ran program')), \
                mock.patch('subprocess.run', side_effect=AssertionError('ran program')), \
                mock.patch('os.system', side_effect=AssertionError('ran program')):
            result = self.build()
            self.assertEqual(result, {'cards': 0, 'ids': [], 'withheld': 1})
            self.build(check=True)
        text = (self.root / 'README.md').read_text()
        self.assertIn('permissions still need human review', text)
        self.assertNotIn('starter-scene-still', text)
        self.assertEqual(list((self.root / 'docs/gallery/media').iterdir()), [])

    def test_permission_entry_uses_index_and_copies_thumb_then_revocation_removes_it(self):
        self.set_permissions({'starter-scene-still': {'evidence': 'history/rights.md'}})
        result = self.build()
        self.assertEqual(result['ids'], ['starter-scene-still'])
        media = self.root / 'docs/gallery/media/starter-scene-still.png'
        self.assertEqual(media.read_bytes(), (self.piece / 'media/thumb.png').read_bytes())
        self.assertIn('pixelate remix starter-scene-still', (self.root / 'README.md').read_text())
        self.assertIn('Declared status', (self.root / 'docs/gallery/index.html').read_text())
        self.build(check=True)
        self.set_permissions({})
        self.build()
        self.assertFalse(media.exists())
        self.assertNotIn('starter-scene-still', (self.root / 'docs/gallery/index.html').read_text())
        self.build(check=True)

    def test_check_never_writes_and_stale_index_is_rejected(self):
        self.build()
        page = self.root / 'docs/gallery/index.html'
        page.write_text('edited')
        with self.assertRaisesRegex(gallery.GalleryError, 'not generated'):
            self.build(check=True)
        self.assertEqual(page.read_text(), 'edited')
        manifest = self.piece / 'piece.json'
        data = json.loads(manifest.read_text())
        data['summary'] += ' changed'
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(gallery.GalleryError, 'index is stale'):
            self.build()
        self.assertEqual(page.read_text(), 'edited')

    def test_unknown_or_unsafe_rights_evidence_is_refused(self):
        for pieces in ({'unknown-piece': {'evidence': 'history/rights.md'}},
                       {'starter-scene-still': {'evidence': '../secrets'}},
                       {'starter-scene-still': {'evidence': 'history/missing.md'}}):
            with self.subTest(pieces=pieces):
                self.set_permissions(pieces)
                with self.assertRaises((gallery.GalleryError, library.LibraryError)):
                    self.build()
        self.assertFalse((self.root / 'docs/gallery/index.html').exists())

    def test_evidence_parent_link_cannot_escape_even_after_catalog_scan(self):
        self.set_permissions({'starter-scene-still': {'evidence': 'history/rights.md'}})
        indexed = library.index(self.catalog)
        manifests = library.scan(self.catalog)
        outside = self.root / 'outside-history'
        outside.mkdir()
        (outside / 'rights.md').write_text('Not evidence from this piece.\n')
        shutil.rmtree(self.piece / 'history')
        os.symlink(outside, self.piece / 'history', target_is_directory=True)
        # Simulate the parent changing after index/manifest validation; the actual open must still refuse it.
        with mock.patch.object(gallery.library, 'index', return_value=indexed), \
                mock.patch.object(gallery.library, 'scan', return_value=manifests):
            with self.assertRaisesRegex(gallery.GalleryError, 'unsafe or missing component'):
                self.build()
        self.assertFalse((self.root / 'docs/gallery/media/starter-scene-still.png').exists())

    def test_hardlinked_thumbnail_is_not_published(self):
        self.set_permissions({'starter-scene-still': {'evidence': 'history/rights.md'}})
        thumbnail = self.piece / 'media/thumb.png'
        outside = self.root / 'outside.png'
        outside.write_bytes(thumbnail.read_bytes())
        thumbnail.unlink()
        os.link(outside, thumbnail)
        with self.assertRaisesRegex(gallery.GalleryError, 'singly linked'):
            self.build()
        self.assertFalse((self.root / 'docs/gallery/media/starter-scene-still.png').exists())

    def test_html_and_markdown_escape_manifest_text(self):
        data = json.loads((self.piece / 'piece.json').read_text())
        data['title'] = '<script>alert(1)</script>'
        data['summary'] = 'A [fake](https://invalid.example) card'
        (self.piece / 'piece.json').write_text(json.dumps(data))
        library.write_index(self.catalog)
        self.set_permissions({'starter-scene-still': {'evidence': 'history/rights.md'}})
        self.build()
        self.assertIn('&lt;script&gt;', (self.root / 'docs/gallery/index.html').read_text())
        self.assertNotIn('<script>', (self.root / 'docs/gallery/library.md').read_text())
        self.assertIn(r'\[fake\]', (self.root / 'docs/gallery/library.md').read_text())


if __name__ == '__main__':
    unittest.main()
