import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import reference


class ReferenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.photo = self.root / 'photo.png'
        image = Image.new('RGB', (120, 90), (110, 110, 110))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 39, 89), fill=(20, 20, 20))
        draw.rectangle((80, 0, 119, 89), fill=(235, 235, 235))
        image.save(self.photo)
        self.report = self.root / 'reference.json'

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'pixelate'), 'reference', str(self.photo),
                               '-o', str(self.report), *[str(x) for x in args]], capture_output=True, text=True)

    def test_observations_are_bounded_and_camera_remains_unknown(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.report.read_text())
        self.assertEqual(data['size'], [120, 90])
        self.assertEqual(data['camera']['projection'], 'unknown')
        self.assertIsNone(data['camera']['horizon_y'])
        self.assertEqual(data['camera']['vanishing_points'], [])
        self.assertEqual(data['value_evidence']['fractions'], [0.3333, 0.3333, 0.3333])
        self.assertTrue(data['edge_evidence']['sampled_edge_pixels'] > 0)
        self.assertIn('not vanishing points', data['edge_evidence']['method'])
        with Image.open(data['overlay']) as overlay:
            self.assertEqual(overlay.size, (120, 90))
        self.assertEqual(data['source_sha256'], reference.digest(self.photo))

    def test_manual_marks_round_trip_and_reject_stale_photo(self):
        self.assertEqual(self.cli().returncode, 0)
        data = json.loads(self.report.read_text())
        data['camera'] = {'projection': 'one-point', 'horizon_y': 35,
                          'vanishing_points': [[160, 35]], 'notes': 'VP outside crop'}
        data['landmarks'] = [{'name': 'bridge', 'box': [20, 25, 64, 70]}]
        self.report.write_text(json.dumps(data))
        result = self.cli('--marks', self.report)
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads(self.report.read_text())
        self.assertEqual(updated['camera'], data['camera'])
        self.assertEqual(updated['landmarks'], data['landmarks'])
        with Image.open(updated['overlay']) as overlay:
            self.assertNotEqual(overlay.getpixel((20, 25)), (20, 20, 20))
        Image.new('RGB', (120, 90), 'red').save(self.photo)
        result = self.cli('--marks', self.report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('another photo', result.stderr)
        self.assertEqual(json.loads(self.report.read_text())['source_sha256'], data['source_sha256'])

    def test_photo_exif_orientation_sets_report_coordinates(self):
        self.photo = self.root / 'rotated.jpg'
        exif = Image.Exif()
        exif[274] = 6
        Image.new('RGB', (40, 20), '#335577').save(self.photo, exif=exif)
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.report.read_text())['size'], [20, 40])

    def test_tiny_photo_does_not_invent_camera_or_edges(self):
        Image.new('RGB', (1, 1), '#222222').save(self.photo)
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.report.read_text())
        self.assertEqual(data['edge_evidence']['sampled_edge_pixels'], 0)
        self.assertEqual(data['edge_evidence']['directions'], [])
        self.assertEqual(data['camera']['projection'], 'unknown')

    def test_invalid_marks_do_not_overwrite_report(self):
        marks = self.root / 'marks.json'
        for camera, landmarks in [({'horizon_y': float('nan')}, []),
                                  ({'vanishing_points': [[3]]}, []),
                                  ({}, [{'name': 'outside', 'box': [-1, 0, 10, 10]}])]:
            with self.subTest(camera=camera, landmarks=landmarks):
                marks.write_text(json.dumps({'camera': camera, 'landmarks': landmarks}))
                result = self.cli('--marks', marks)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.report.exists())

    def test_mcp_returns_report_and_overlay_in_workspace(self):
        server_module = types.ModuleType('mcp.server.fastmcp')
        server_module.__dict__.update(FastMCP=lambda *a, **kw: types.SimpleNamespace(tool=lambda: lambda f: f),
                                      Image=lambda path: path)
        with patch.dict(sys.modules, {'mcp': types.ModuleType('mcp'),
                                      'mcp.server': types.ModuleType('mcp.server'),
                                      'mcp.server.fastmcp': server_module}):
            from tools import mcp_server
            with patch.object(mcp_server, 'WORK', self.root):
                result = mcp_server.inspect_reference(str(self.photo), 'mcp.json')
                self.assertIn('camera: unknown', result[0])
                self.assertEqual(result[1], str(self.root / 'mcp.overlay.png'))
                self.assertTrue((self.root / 'mcp.json').is_file())
                with self.assertRaises(ValueError):
                    mcp_server.inspect_reference(str(self.photo), '../outside.json')


if __name__ == '__main__':
    unittest.main()
