"""The author-path guide and the mode guides that point at library pieces: links resolve, the pieces and
starters they name exist with the status the prose claims, the hard rules are still written down, and
commands that are not built yet are not offered as callable."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUTHORING = REPO / 'references' / 'authoring.md'
GUIDES = [REPO / 'guides' / name for name in ('scenes.md', 'assets.md', 'eras.md', 'rebuild.md', 'music.md')]
DOCS = [AUTHORING] + GUIDES
STARTERS = ('starter-scene-still', 'starter-era-nes', 'starter-rebuild-perspective')
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def anchors(path):
    """GitHub-style heading slugs of a markdown file"""
    slugs = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'#{1,6}\s+(.*)', line)
        if match:
            slug = re.sub(r'[^\w\s-]', '', match.group(1).lower().replace('`', ''))
            slugs.add(re.sub(r'\s', '-', slug.strip()))
    return slugs


def status_of(piece_id):
    return json.loads((REPO / 'library' / piece_id / 'piece.json').read_text(encoding='utf-8'))['status']


class AuthoringDocsTest(unittest.TestCase):
    def test_relative_links_and_anchors_resolve(self):
        for doc in DOCS:
            for target in LINK.findall(doc.read_text(encoding='utf-8')):
                if re.match(r'[a-z]+:', target):
                    continue
                name, _, fragment = target.partition('#')
                path = (doc.parent / name).resolve() if name else doc
                self.assertTrue(path.is_file(), f'{doc.name} links to missing {target}')
                if fragment:
                    self.assertIn(fragment, anchors(path), f'{doc.name}: no heading {fragment} in {path.name}')

    def test_named_library_pieces_exist(self):
        for doc in DOCS:
            for piece_id in set(re.findall(r'library/([a-z0-9]+(?:-[a-z0-9]+)*)(?=[/\s`.,;:)]|$)', doc.read_text(encoding='utf-8'))):
                self.assertTrue((REPO / 'library' / piece_id / 'piece.json').is_file(), f'{doc.name} names missing library/{piece_id}')

    def test_the_three_starters_are_named_and_are_starters(self):
        text = '\n'.join(path.read_text(encoding='utf-8') for path in DOCS)
        for piece_id in STARTERS:
            self.assertIn(piece_id, text)
            self.assertEqual(status_of(piece_id), 'starter')
        self.assertIn('starter-scene-still', (REPO / 'guides' / 'scenes.md').read_text(encoding='utf-8'))
        self.assertIn('starter-era-nes', (REPO / 'guides' / 'eras.md').read_text(encoding='utf-8'))
        self.assertIn('starter-rebuild-perspective', (REPO / 'guides' / 'rebuild.md').read_text(encoding='utf-8'))

    def test_every_mode_guide_points_to_the_author_path_and_a_starter(self):
        starters = {'scenes.md': 'starter-scene-loop', 'assets.md': 'starter-assets', 'eras.md': 'starter-era-nes',
                    'rebuild.md': 'starter-rebuild-perspective', 'music.md': 'starter-music'}
        for guide in GUIDES:
            text = guide.read_text(encoding='utf-8')
            self.assertIn('references/authoring.md', text, guide.name)
            self.assertIn(starters[guide.name], text, guide.name)
            self.assertTrue((REPO / 'library' / starters[guide.name]).is_dir())

    def test_no_prose_claims_a_review_the_library_does_not_have(self):
        nonstarters = [p.parent.name for p in (REPO / 'library').glob('*/piece.json') if status_of(p.parent.name) != 'starter']
        self.assertTrue(all(status_of(p) == 'study' for p in nonstarters), 'a piece was promoted: revisit the guides')
        for doc in DOCS:
            text = doc.read_text(encoding='utf-8')
            self.assertNotRegex(text, r'(?i)\b(is|are) (graded )?(A-reviewed|reviewed|accepted)\b', doc.name)

    def test_perspective_is_not_called_iso(self):
        rebuild = (REPO / 'guides' / 'rebuild.md').read_text(encoding='utf-8')
        self.assertIn('true pinhole two-point camera', rebuild)
        self.assertIn('not an isometric preset', rebuild)
        self.assertIn('orthographic', rebuild)

    def test_hard_rules_are_written_down(self):
        text = AUTHORING.read_text(encoding='utf-8')
        for phrase in ('author path', 'not the default remix path', 'brief approval', '--blockin', 'three graded lead rounds',
                       'Specialists observe and never grade', 'The gate is not art quality', 'go/no-go',
                       'confirm the animation plan', 'No borrowed characters', 'Paid or outside review needs a budget',
                       'ask whether to continue or change the brief', 'Only the user can extend'):
            self.assertIn(phrase.lower(), text.lower(), phrase)

    def test_only_existing_commands_are_offered(self):
        help_text = subprocess.run([sys.executable, str(REPO / 'pixelate'), '--help'], capture_output=True, text=True, check=True).stdout
        text = AUTHORING.read_text(encoding='utf-8')
        not_built = text[text.index('Not built yet'):]
        offered = text[:text.index('Not built yet')]
        for command, sub in re.findall(r'`pixelate ([a-z-]+)(?: ([a-z-]+))?', offered):
            self.assertIn(f'pixelate {command}', help_text, f'authoring.md offers `pixelate {command}`')
            if command in ('library', 'review'):
                self.assertIn(sub, help_text, f'authoring.md offers `pixelate {command} {sub}`')
        for unbuilt in ('pixelate deliver', 'pixelate library add'):
            self.assertNotIn(unbuilt, offered)
            self.assertNotIn(unbuilt, help_text)
        self.assertIn('render DIR --set name=value', offered)
        self.assertIn('--set', help_text)
        self.assertIn('engine/pack `render --set`', not_built)
        self.assertIn('pixelate deliver', not_built)
        self.assertNotRegex(offered, r'(?i)\bMCP (tools? )?(for )?(find|remix|deliver)')

    def test_skill_still_describes_today_not_the_planned_loop(self):
        skill = (REPO / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('Copy these 10 steps into your todo list first', skill)
        self.assertNotIn('pixelate deliver', skill)


if __name__ == '__main__':
    unittest.main()
