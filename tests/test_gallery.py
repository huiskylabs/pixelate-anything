"""Static gallery projects the checked catalog without a permission ledger or piece execution."""
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
        (self.root / 'docs/gallery').mkdir(parents=True)
        (self.root / 'README.md').write_text('# Test\n\n' + gallery.START + '\nold\n' + gallery.END + '\n')
        library.write_index(self.catalog)

    def build(self, check=False):
        return gallery.build(self.catalog, self.root, check=check)

    def test_indexed_piece_becomes_card_without_execution_and_removal_prunes_media(self):
        with mock.patch('subprocess.Popen', side_effect=AssertionError('ran program')), \
                mock.patch('subprocess.run', side_effect=AssertionError('ran program')), \
                mock.patch('os.system', side_effect=AssertionError('ran program')):
            result = self.build()
            self.assertEqual(result, {'cards': 1, 'ids': ['starter-scene-still']})
            self.build(check=True)
        media = self.root / 'docs/gallery/media/starter-scene-still.png'
        self.assertEqual(media.read_bytes(), (self.piece / 'media/thumb.png').read_bytes())
        self.assertIn('pixelate remix starter-scene-still', (self.root / 'README.md').read_text())
        self.assertIn('Declared status', (self.root / 'docs/gallery/index.html').read_text())
        shutil.rmtree(self.piece)
        library.write_index(self.catalog)
        self.assertEqual(self.build(), {'cards': 0, 'ids': []})
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

    def test_declared_thumb_is_required_for_every_piece(self):
        path = self.piece / 'piece.json'
        data = json.loads(path.read_text())
        data['media']['thumb'] = None
        path.write_text(json.dumps(data))
        library.write_index(self.catalog)
        with self.assertRaisesRegex(gallery.GalleryError, 'needs a declared thumbnail'):
            self.build()

    def test_thumbnail_parent_link_cannot_escape_even_after_catalog_scan(self):
        indexed = library.index(self.catalog)
        manifests = library.scan(self.catalog)
        outside = self.root / 'outside-media'
        outside.mkdir()
        (outside / 'thumb.png').write_bytes((self.piece / 'media/thumb.png').read_bytes())
        shutil.rmtree(self.piece / 'media')
        os.symlink(outside, self.piece / 'media', target_is_directory=True)
        with mock.patch.object(gallery.library, 'index', return_value=indexed), \
                mock.patch.object(gallery.library, 'scan', return_value=manifests):
            with self.assertRaisesRegex(gallery.GalleryError, 'unsafe or missing component'):
                self.build()
        self.assertFalse((self.root / 'docs/gallery/media/starter-scene-still.png').exists())

    def test_hardlinked_thumbnail_is_not_published(self):
        thumbnail = self.piece / 'media/thumb.png'
        outside = self.root / 'outside.png'
        outside.write_bytes(thumbnail.read_bytes())
        thumbnail.unlink()
        os.link(outside, thumbnail)
        with self.assertRaisesRegex(gallery.GalleryError, 'singly linked'):
            self.build()
        self.assertFalse((self.root / 'docs/gallery/media/starter-scene-still.png').exists())

    def test_oversized_thumbnail_is_not_published(self):
        thumbnail = self.piece / 'media/thumb.png'
        thumbnail.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * gallery.MAX_MEDIA)
        with self.assertRaisesRegex(gallery.GalleryError, 'singly linked regular file'):
            self.build()
        self.assertFalse((self.root / 'docs/gallery/media/starter-scene-still.png').exists())

    def test_html_and_markdown_escape_manifest_text(self):
        data = json.loads((self.piece / 'piece.json').read_text())
        data['title'] = '<script>alert(1)</script>'
        data['summary'] = 'A [fake](https://invalid.example) card'
        (self.piece / 'piece.json').write_text(json.dumps(data))
        library.write_index(self.catalog)
        self.build()
        self.assertIn('&lt;script&gt;', (self.root / 'docs/gallery/index.html').read_text())
        self.assertNotIn('<script>', (self.root / 'docs/gallery/library.md').read_text())
        self.assertIn(r'\[fake\]', (self.root / 'docs/gallery/library.md').read_text())


if __name__ == '__main__':
    unittest.main()
