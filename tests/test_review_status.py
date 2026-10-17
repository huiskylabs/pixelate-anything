import importlib
import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from tools import route
review_status = importlib.import_module('tools.review_status')

ROOT = pathlib.Path(__file__).resolve().parents[1]


def lead(grade='A', scores=None, originality='pass', signature='a lantern reflected in the waves', fixes=None):
    scores = scores or [5 if n in (1, 3, 4) else 4 for n in range(1, 13)]
    if fixes is None:
        fixes = [] if grade == 'A' else ['section 4: change the hero box', 'section 5: lift the light',
                                         'section 6: vary the masses']
    return (f'GRADE: {grade}\nSCORES: ' + ' '.join(f'{n}={score}' for n, score in enumerate(scores, 1)) +
            f' originality: {originality}\nSIGNATURE MOMENT: {signature}\nBIGGEST PROBLEM: flat sky\n'
            'FIXES (ranked by impact, up to 5; 3 to 5 below A):\n' +
            ''.join(f'{n}. {fix}\n' for n, fix in enumerate(fixes, 1)) + 'KEEP: strong hero\n')


class ReviewStatusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = pathlib.Path(self.tmp.name)
        self.brief = self.work / 'brief.md'
        self.brief.write_text('# Full brief\n## 0. Choices\nA lighthouse\n')
        self.frame = self.work / 'still.png'
        self.frame.write_bytes(b'PNG still one')
        self.report = self.work / 'lead.md'
        self.report.write_text(lead())

    def cli(self, action, *args):
        return subprocess.run([sys.executable, str(ROOT / 'pixelate'), 'review', action,
                               '--brief', str(self.brief), *map(str, args)],
                              cwd=self.work, capture_output=True, text=True)

    def test_brief_and_still_a_b_cli_return_codes(self):
        self.assertNotEqual(self.cli('status').returncode, 0)
        self.assertIn('missing file', self.cli('status').stdout)
        self.assertIn('RECORDED A', self.cli('record', '--critique', self.report).stdout)
        self.assertEqual(self.cli('status').returncode, 0)
        self.assertIn('READY', self.cli('status').stdout)
        self.assertNotEqual(self.cli('status', '--frame', self.frame).returncode, 0)
        self.assertEqual(self.cli('record', '--frame', self.frame, '--critique', self.report).returncode, 0)
        self.assertEqual(self.cli('status', '--frame', self.frame).returncode, 0)
        self.report.write_text(lead('B'))
        self.assertIn('report changed', self.cli('status').stdout)
        self.assertEqual(self.cli('record', '--critique', self.report).returncode, 0)
        self.assertNotEqual(self.cli('status').returncode, 0)
        self.assertIn('grade B', self.cli('status').stdout)
        self.assertEqual(self.cli('record', '--frame', self.frame, '--critique', self.report).returncode, 0)
        self.assertIn('grade B', self.cli('status', '--frame', self.frame).stdout)

    def test_stale_brief_frame_report_and_manifest(self):
        review_status.record(self.brief, self.report, self.frame)
        manifest = self.work / 'still.png.visual-review.json'
        self.assertEqual(json.loads(manifest.read_text())['version'], 1)
        for path, expected in ((self.brief, 'brief changed'), (self.frame, 'frame changed'),
                               (self.report, 'report changed')):
            original = path.read_bytes()
            path.write_bytes(original + b'!')
            self.assertIn(expected, review_status.status(self.brief, self.frame)[1])
            path.write_bytes(original)
        self.assertTrue(review_status.status(self.brief, self.frame)[0])
        original_manifest = manifest.read_bytes()
        manifest.write_bytes(original_manifest + b'\n')
        self.assertIn('manifest bytes changed', review_status.status(self.brief, self.frame)[1])
        manifest.write_text('{}')
        self.assertIn('manifest schema', review_status.status(self.brief, self.frame)[1])
        manifest.unlink()
        self.assertIn('missing file', review_status.status(self.brief, self.frame)[1])
        review_status.record(self.brief, self.report, self.frame)
        self.report.unlink()
        self.assertIn('missing file', review_status.status(self.brief, self.frame)[1])
        self.report.write_text(lead())
        self.frame.unlink()
        self.assertIn('missing file', review_status.status(self.brief, self.frame)[1])

    def test_two_frames_one_brief_are_independent(self):
        other = self.work / 'another.png'
        other.write_bytes(b'PNG still two')
        review_status.record(self.brief, self.report, self.frame)
        review_status.record(self.brief, self.report, other)
        self.frame.write_bytes(b'changed')
        self.assertFalse(review_status.status(self.brief, self.frame)[0])
        self.assertTrue(review_status.status(self.brief, other)[0])
        self.assertFalse(review_status.status(self.brief)[0])

    def test_malformed_specialist_music_and_ambiguous_rejected(self):
        invalid = [lead().replace('GRADE: A', 'GRADE: A\nGRADE: B'),
                   lead().replace('12=4', '12=6'), lead().replace('originality: pass', 'originality: fail'),
                   lead().replace('1=5', '1=3'), lead(signature='none'),
                   lead().replace('KEEP:', 'ROLE: composition\nKEEP:'),
                   'SPECIALIST: lighting\nThe light is flat',
                   'NOT REVIEWED: no audio access', 'GRADE: A\nMOTIF: not clear\nKEEP: beat']
        for report in invalid:
            with self.subTest(report=report[:50]):
                self.report.write_text(report)
                self.assertNotEqual(self.cli('record', '--critique', self.report).returncode, 0)
        self.assertFalse(review_status.status(self.brief)[0])

    def test_full_brief_with_gate_without_motion_table_is_not_short(self):
        self.brief.write_text('# Full brief\n## Gate\nCheck the still.\n')
        self.assertFalse(route._is_short(self.brief.read_text()))
        self.assertIn('RECORDED A', review_status.record(self.brief, self.report))
        self.assertTrue(review_status.status(self.brief)[0])

    def test_unmarked_short_brief_skips_brief_stage(self):
        self.brief.write_text('# Lantern\n## 4. Gate\ncheck\n## 5. Show the user\nshow still\n')
        self.assertTrue(route._is_short(self.brief.read_text()))
        self.assertIn('short brief skips', review_status.status(self.brief)[1])
        with self.assertRaisesRegex(review_status.ReviewError, 'short brief skips'):
            review_status.record(self.brief, self.report)
        self.assertIn('RECORDED A', review_status.record(self.brief, self.report, self.frame))

    def test_short_brief_size_and_unsafe_manifest(self):
        self.brief.write_text('# Lantern (short brief: sprite)\n## Gate\ncheck\n')
        self.assertIn('short brief skips', review_status.status(self.brief)[1])
        with self.assertRaisesRegex(review_status.ReviewError, 'short brief skips'):
            review_status.record(self.brief, self.report)
        self.assertTrue(review_status.record(self.brief, self.report, self.frame).startswith('RECORDED'))
        self.report.write_bytes(b'x' * (review_status.MAX_REPORT + 1))
        with self.assertRaisesRegex(review_status.ReviewError, 'too large'):
            review_status.record(self.brief, self.report, self.frame)
        self.report.write_text(lead())
        manifest = self.work / 'still.png.visual-review.json'
        manifest.unlink()
        outside = self.work / 'outside.json'
        outside.write_text('safe')
        manifest.symlink_to(outside)
        with self.assertRaisesRegex(review_status.ReviewError, 'unsafe manifest'):
            review_status.record(self.brief, self.report, self.frame)
        self.assertEqual(outside.read_text(), 'safe')
        self.assertFalse(review_status.status(self.brief, self.frame)[0])

    def test_mcp_stub_parity_workspace_and_external_report(self):
        stub = types.ModuleType('mcp.server.fastmcp')
        stub.__dict__.update(FastMCP=lambda *a, **kw: types.SimpleNamespace(tool=lambda: lambda f: f), Image=object)
        with patch.dict(sys.modules, {'mcp': types.ModuleType('mcp'), 'mcp.server': types.ModuleType('mcp.server'),
                                      'mcp.server.fastmcp': stub}):
            from tools import mcp_server
            self.assertIn('record_visual_review(brief, report)', mcp_server.INSTRUCTIONS)
            self.assertIn('visual_review_status(brief, frame)', mcp_server.INSTRUCTIONS)
            with patch.object(mcp_server, 'WORK', self.work):
                external_dir = tempfile.TemporaryDirectory()
                self.addCleanup(external_dir.cleanup)
                external = pathlib.Path(external_dir.name) / 'lead.md'
                external.write_text(lead())
                self.assertIn('RECORDED A', mcp_server.record_visual_review('brief.md', str(external), 'still.png'))
                self.assertEqual(mcp_server.visual_review_status('brief.md', 'still.png'),
                                 review_status.status(self.brief, self.frame)[1])
                self.assertIn('READY', mcp_server.visual_review_status('brief.md', 'still.png'))
                self.assertIn('missing file', mcp_server.visual_review_status('brief.md'))
                with self.assertRaisesRegex(ValueError, 'inside the workspace'):
                    mcp_server.record_visual_review(str(self.brief), str(external), str(external))
                outside_artifact = pathlib.Path(external_dir.name) / 'brief.md'
                outside_artifact.write_text('# Full brief')
                with self.assertRaisesRegex(ValueError, 'inside the workspace'):
                    mcp_server.record_visual_review(str(outside_artifact), str(external))
                self.assertFalse((pathlib.Path(external_dir.name) / 'brief.md.visual-review.json').exists())
                self.assertIn('missing file', mcp_server.visual_review_status(str(outside_artifact)))


if __name__ == '__main__':
    unittest.main()
