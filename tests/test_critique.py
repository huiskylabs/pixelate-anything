import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from PIL import Image
from tools import critique

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CritiqueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = pathlib.Path(self.tmp.name)
        self.brief = self.work / 'brief.md'
        self.brief.write_text('Request: a lighthouse\n## 0. Choices\nA cold coast.\n## 4. The scene\n- Hero: lighthouse\n')
        self.frame = self.work / 'still.png'
        Image.new('RGB', (32, 24), '#334455').save(self.frame)
        self.note1 = self.work / 'lighting.md'
        self.note2 = self.work / 'set.md'
        self.note3 = self.work / 'character.md'
        for p in (self.note1, self.note2, self.note3):
            p.write_text('OBSERVATION ' + p.stem)
        self.prev = self.work / 'last-lead.md'
        self.prev.write_text('PRIOR LEAD FIX: move tower')
        self.track = self.work / 'track.wav'
        self.track.write_bytes(b'RIFFtest')

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'pixelate'), *map(str, args)],
                              cwd=self.work, capture_output=True, text=True)

    def test_lead_default_backward_compatible_and_prior_distinct_from_consults(self):
        original = critique.prompt(self.frame, self.brief)
        self.assertIn('independent art director', original)
        self.assertIn('SCORES:', original)
        self.assertEqual(original, critique.prompt(self.frame, self.brief, role='lead'))
        result = critique.prompt(self.frame, self.brief, prev=self.prev, consults=[self.note1, self.note2])
        self.assertIn('PRIOR LEAD FIX: move tower', result)
        self.assertIn('PRIOR FIXES:', result)
        self.assertIn('OBSERVATION lighting', result)
        self.assertIn('OBSERVATION set', result)
        self.assertLess(result.index('previous lead critique'), result.index('Specialist observations'))
        self.assertNotIn('OBSERVATION lighting', result.split('## The previous lead critique')[1].split('## Specialist observations')[0])

    def test_specialists_scope_and_never_grade(self):
        for role, subject in [('composition', 'camera'), ('lighting', 'light direction'),
                              ('set', 'architecture'), ('character', 'pose')]:
            with self.subTest(role=role):
                result = critique.prompt(None, self.brief, role=role)
                self.assertIn(f'independent {role} visual specialist', result)
                self.assertIn(subject, result)
                self.assertNotIn('SCORES:', result)
                self.assertNotIn('## Grade', result)
                self.assertIn('No grade, scores', result)
                for other in ('composition', 'lighting', 'set', 'character'):
                    if other != role:
                        self.assertNotIn(f'**{other}:**', result)
        self.assertIn('Greyscale thumbnail', critique.prompt(self.frame, self.brief, role='lighting'))

    def test_consults_bounded_and_invalid_for_specialist(self):
        self.assertIn('SCORES:', critique.prompt(None, self.brief, consults=[]))
        self.assertIn('OBSERVATION set', critique.prompt(None, self.brief, consults=[self.note1, self.note2]))
        with self.assertRaisesRegex(ValueError, 'at most two'):
            critique.prompt(None, self.brief, consults=[self.note1, self.note2, self.note3])
        with self.assertRaisesRegex(ValueError, 'only the lead'):
            critique.prompt(None, self.brief, role='set', consults=[self.note1])
        with self.assertRaisesRegex(ValueError, 'only the lead'):
            critique.prompt(None, self.brief, role='lighting', prev=self.prev)
        self.assertNotEqual(self.cli('critique', '--brief', self.brief, '--consult', self.note1,
                                     '--consult', self.note2, '--consult', self.note3).returncode, 0)

    def test_music_cli_listen_prerequisite_and_missing_track(self):
        result = self.cli('critique-music', self.track, '--brief', self.brief, '--prev', self.prev)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('actually LISTEN', result.stdout)
        self.assertIn('passes `pixelate check TRACK.wav`', result.stdout)
        self.assertIn('NOT REVIEWED', result.stdout)
        self.assertIn('Previous music critique', result.stdout)
        self.assertIn('motif', result.stdout)
        self.assertNotIn('PRIOR FIXES: 1=', result.stdout)
        self.assertNotEqual(self.cli('critique-music', self.work / 'missing.wav', '--brief', self.brief).returncode, 0)
        self.assertNotEqual(self.cli('critique', '--brief', self.brief, '--role', 'set', '--consult', self.note1).returncode, 0)

    def test_mcp_parity_and_workspace_safety(self):
        stub = types.ModuleType('mcp.server.fastmcp')
        stub.__dict__.update(FastMCP=lambda *args, **kwargs: types.SimpleNamespace(tool=lambda: lambda f: f),
                             Image=object)
        with patch.dict(sys.modules, {'mcp': types.ModuleType('mcp'), 'mcp.server': types.ModuleType('mcp.server'),
                                      'mcp.server.fastmcp': stub}):
            from tools import mcp_server
            with patch.object(mcp_server, 'WORK', self.work):
                self.assertEqual(mcp_server.critique_prompt('brief.md', role='composition'),
                                 critique.prompt(None, self.brief, role='composition'))
                self.assertEqual(mcp_server.critique_prompt('brief.md', consults=['lighting.md']),
                                 critique.prompt(None, self.brief, consults=[self.note1]))
                self.assertEqual(mcp_server.music_critique_prompt('track.wav', 'brief.md'),
                                 critique.music_prompt(self.track, self.brief))
                with self.assertRaisesRegex(ValueError, 'at most two'):
                    mcp_server.critique_prompt('brief.md', consults=['lighting.md', 'set.md', 'character.md'])
                external = ROOT / 'examples/lantern-isle/BRIEF.md'
                self.assertIn(str(external), mcp_server.critique_prompt(str(external)))
                self.assertIn(str(external), mcp_server.music_critique_prompt('track.wav', str(external)))
                with self.assertRaisesRegex(ValueError, 'inside the workspace'):
                    mcp_server.critique_prompt('brief.md', frame=str(ROOT / 'docs/lantern-isle-winter.png'))


if __name__ == '__main__':
    unittest.main()
