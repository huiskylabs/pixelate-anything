"""SKILL.md is the router: at most 1,500 words, the style loop by default, authoring behind one pointer.
Its links resolve, every command and flag it offers exists in `pixelate --help`, the pieces it names
exist with the status it implies, and it neither offers what is not built nor calls anything ready."""
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_authoring_docs import LINK, anchors, status_of  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / 'SKILL.md'
TEXT = SKILL.read_text(encoding='utf-8')
_spec = importlib.util.spec_from_file_location('library_search_cases', REPO / 'tools' / 'library_search_cases.py')
assert _spec is not None and _spec.loader is not None
_cases = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cases)
CASES, NO_MATCH_CASES = _cases.CASES, _cases.NO_MATCH_CASES


def pixelate(*args):
    return subprocess.run([sys.executable, str(REPO / 'pixelate'), *args], capture_output=True, text=True, check=True).stdout


def section(heading):
    """the body of one `## heading` section"""
    return TEXT.split(f'\n## {heading}\n', 1)[1].split('\n## ', 1)[0]


class SkillRouterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.help = pixelate('--help')

    def test_at_most_1500_words(self):
        self.assertLessEqual(len(TEXT.split()), 1500)

    def test_links_and_anchors_resolve(self):
        targets = LINK.findall(TEXT)
        self.assertTrue(targets)
        for target in targets:
            name, _, fragment = target.partition('#')
            path = (REPO / name).resolve() if name else SKILL
            self.assertTrue(path.is_file(), f'SKILL.md links to missing {target}')
            if fragment:
                self.assertIn(fragment, anchors(path), f'SKILL.md: no heading {fragment} in {path.name}')

    def test_every_offered_command_and_flag_is_in_help(self):
        commands = set(re.findall(r'`pixelate ([a-z][a-z-]*)', TEXT))
        self.assertTrue(commands)
        for command in commands:
            self.assertIn(f'pixelate {command}', self.help, f'SKILL.md offers `pixelate {command}`')
        for sub in re.search(r'`library ([a-z|]+)`', TEXT).group(1).split('|'):
            self.assertRegex(self.help, rf'pixelate library .*\b{sub}\b', f'SKILL.md offers `library {sub}`')
        for flag in set(re.findall(r'(?<![\w-])(--[a-z][a-z-]*)', TEXT)) - {'--help'}:
            self.assertIn(flag, self.help, f'SKILL.md offers {flag}')

    def test_the_default_is_the_style_loop(self):
        self.assertIn('The default for every model is the style loop', TEXT)
        loop = section('The style loop')
        steps = re.findall(r'^\d+\. \*\*([^*]+)\*\*', loop, re.M)
        self.assertEqual(steps[:3], ['Style.', 'Brief.', 'Find, for technique.'])
        order = [loop.index(command) for command in ('`pixelate route', '`pixelate style', '`pixelate find', '`pixelate remix',
                                                     '`pixelate render', '`pixelate deliver')]
        self.assertEqual(order, sorted(order))
        self.assertIn('references/remix.md', loop)
        self.assertIn('Differs from ID:', loop)
        self.assertIn('no brief review, no block-in, no specialists', loop)

    def test_remix_and_author_are_branches(self):
        loop = section('The style loop')
        self.assertIn('If the person asks for a variant of one piece', loop)
        self.assertIn('go to [Author a new piece]', loop)
        author = section('Author a new piece')
        self.assertIn('[references/authoring.md](references/authoring.md)', author)
        self.assertIn('the person asks for something new', author)
        request, mode = NO_MATCH_CASES[0]
        self.assertIn('no close piece', pixelate('find', request, '--mode', mode))
        request, _ = CASES[0]
        self.assertIn('why: ', pixelate('find', request))

    def test_the_ten_steps_are_not_duplicated(self):
        self.assertNotIn('10 steps', TEXT)
        for phrase in ('route --intake', '--blockin', 'review record', '--consult'):
            self.assertNotIn(phrase, TEXT, phrase)
            self.assertIn(phrase, (REPO / 'references' / 'authoring.md').read_text(encoding='utf-8'), phrase)

    def test_nothing_unbuilt_is_offered(self):
        self.assertIn('pixelate library add work/NAME', TEXT)
        self.assertIn('pixelate library add', self.help)
        self.assertIn('manual pull request', section('The style loop'))
        for tool in ('find_pieces', 'remix_piece', 'render_piece', 'deliver_piece'):
            self.assertIn(f'`{tool}`', TEXT)
        self.assertIn('`add_piece`', TEXT)
        self.assertIn('`trust_local_code=true`', TEXT)
        self.assertIn('render\'s distance-from-base or under-remixed warning, which is uncalibrated and never blocks', TEXT)

    def test_nothing_is_called_ready_or_approved(self):
        self.assertNotIn('READY', TEXT)
        self.assertNotRegex(TEXT, r'(?i)\b(is|are) (now )?(ready|accepted|reviewed|approved|finished)\b')
        for piece_id in set(re.findall(r'`(starter-[a-z-]+)`', TEXT)):
            self.assertEqual(status_of(piece_id), 'starter', piece_id)
        self.assertIn('never a finished or reviewed piece', TEXT)
        self.assertIn('No gate pass, golden match, heuristic or self-assessment raises a piece', TEXT)
        self.assertIn('Never grade your own work', TEXT)

    def test_unreviewed_remix_branch_is_separate_from_the_author_stop(self):
        loop = section('The style loop')
        step6 = next(line for line in loop.splitlines() if line.startswith('7. '))
        step7 = next(line for line in loop.splitlines() if line.startswith('8. '))
        self.assertIn('and the user has approved a budget', step6)
        self.assertIn('do not ask anyone to run it: print the prompt', step6)
        self.assertIn('take the unreviewed branch of step 8', step6)
        self.assertIn('**Unreviewed branch** (style loop only, no critique in step 7)', step7)
        for phrase in ('say NO INDEPENDENT REVIEW and give no grade or art-quality claim',
                       'report the delivery\'s facts as NOT REVIEWED',
                       'ask the user separately to approve before calling it finished',
                       'never call it accepted or reviewed',
                       'The author path has no such branch: a review stage without budget or lead stops'):
            self.assertIn(phrase, step7, phrase)
        trust = section('Trust and evidence')
        self.assertIn('on the author path the stage stops for a budget or a lead; the style loop continues only as the unreviewed branch of step 8', trust)

    def test_knob_claims_match_the_library(self):
        declared = {}
        for manifest in (REPO / 'library').glob('*/piece.json'):
            knobs = json.loads(manifest.read_text(encoding='utf-8')).get('knobs') or {}
            if knobs:
                declared[manifest.parent.name] = sorted(knobs)
        self.assertEqual(declared, {'starter-scene-loop': ['horizon'], 'starter-assets': ['scale']})
        variants = section('Variants')
        self.assertIn('`starter-scene-loop` (`horizon`) and `starter-assets` (`scale`)', variants)
        self.assertIn('for script, engine and pack pieces', variants)
        self.assertIn('(script, engine and pack pieces)', self.help)
        self.assertIn('not proof the program used them', variants)

    def test_trust_and_budget(self):
        trust = section('Trust and evidence')
        self.assertIn('without a sandbox', trust)
        self.assertIn('never on contributed or user-supplied code', trust)
        self.assertIn('needs a budget the user has given', trust)
        self.assertIn('Static: never runs piece code', pixelate('find', '--help').replace('\n', ' '))
        self.assertIn('Pull request checks are static and run no contributed code', TEXT)

    def test_every_mode_names_its_starter_and_guide(self):
        modes = section('Modes')
        for starter, guide in (('starter-scene-still', 'scenes.md'), ('starter-scene-loop', 'music.md'),
                               ('starter-era-nes', 'eras.md'), ('starter-rebuild-perspective', 'rebuild.md'),
                               ('starter-assets', 'assets.md'), ('starter-music', 'music.md')):
            line = next(text for text in modes.splitlines() if f'`{starter}`' in text)
            self.assertIn(f'(guides/{guide})', line, starter)
        self.assertIn('not an isometric preset', modes)
        self.assertIn('(guides/pixelate.md)', modes)
        self.assertIn('(guides/palettes.md)', modes)

    def test_hard_rules_are_kept(self):
        rules = section('Hard rules')
        for phrase in ('Original subjects only', 'no borrowed characters, logos, UI', 'Every effect is done in code',
                       'orthographic presets', 'real projection on the native-pixel grid', 'Rebuild, don\'t convert'):
            self.assertIn(phrase, rules)


if __name__ == '__main__':
    unittest.main()
