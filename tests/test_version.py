import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from version import VERSION  # noqa: E402


class VersionTest(unittest.TestCase):
    def test_cli_prints_the_kit_version(self):
        r = subprocess.run([sys.executable, str(ROOT / 'pixelate'), '--version'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), 'pixelate-anything %s' % VERSION)

    def test_skill_metadata_matches(self):
        head = (ROOT / 'SKILL.md').read_text().split('---')[1]
        self.assertEqual(re.search(r'^\s+version:\s*"?([^"\n]+)"?', head, re.M).group(1), VERSION)


if __name__ == '__main__':
    unittest.main()
