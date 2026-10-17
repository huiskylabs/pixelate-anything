import json
import pathlib
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

from tools import route

ROOT = pathlib.Path(__file__).resolve().parents[1]


class IntakeTest(unittest.TestCase):
    def cli_plan(self, request):
        result = subprocess.run([sys.executable, str(ROOT / 'pixelate'), 'route', '--intake', request],
                                cwd=ROOT, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_generic_scene_offers_optional_questions_in_request_language(self):
        for request, subject, direction, own_words, skip in [
            ('make a pixel scene', 'island', 'night loop', 'own words', 'skip'),
            ('Please draw me pixel art!', 'island', 'night loop', 'own words', 'skip'),
            ('I want a pixel art scene', 'island', 'night loop', 'own words', 'skip'),
            ('I want a pixel scene!', 'island', 'night loop', 'own words', 'skip'),
            ('请帮我做一张像素画。', '小岛', '夜景', '用自己的话', '跳过'),
            ('画一个像素场景', '小岛', '夜景', '用自己的话', '跳过'),
            ('我想要一个像素场景', '小岛', '夜景', '用自己的话', '跳过'),
            ('我想要一张像素画。', '小岛', '夜景', '用自己的话', '跳过'),
        ]:
            with self.subTest(request=request):
                plan = self.cli_plan(request)
                self.assertEqual(plan['disposition'], 'offer')
                self.assertEqual(len(plan['questions']), 2)
                self.assertIn(subject, plan['questions'][0])
                self.assertIn(direction, plan['questions'][1])
                self.assertTrue(all(own_words in question and skip in question for question in plan['questions']))
                self.assertTrue(all('？' in question or '?' in question for question in plan['questions']))
                self.assertEqual(plan['route'], route.route(request))

    def test_specific_requests_proceed_without_questions(self):
        requests = [
            'make a pixel island',
            'make a pixel scene of an island',
            'I want a pixel art scene of an island',
            'I want a pixel scene with a cozy night market',
            'make a cozy pixel scene',
            'A tiny noodle shop on a snowy night, seen from above. Warm lamps and a cat by the window.',
            'rebuild this photo as pixel art',
            'make pixel art icons for a game',
            'Game Boy style pixel scene',
            'just music',
            '画一个像素小岛',
            '我想要一个像素场景，画一座小岛',
            '我想要一个像素场景里的小岛',
            '做一张像素画，夜晚的小村庄有灯笼',
        ]
        for request in requests:
            with self.subTest(request=request):
                plan = self.cli_plan(request)
                self.assertEqual(plan['disposition'], 'direct')
                self.assertEqual(plan['questions'], [])
                self.assertEqual(plan['route'], route.route(request))

    def test_mcp_intake_matches_cli(self):
        server_module = types.ModuleType('mcp.server.fastmcp')
        server_module.__dict__.update(FastMCP=lambda *args, **kwargs: types.SimpleNamespace(tool=lambda: lambda f: f),
                                      Image=object)
        with patch.dict(sys.modules, {'mcp': types.ModuleType('mcp'),
                                      'mcp.server': types.ModuleType('mcp.server'),
                                      'mcp.server.fastmcp': server_module}):
            from tools import mcp_server
            for request in ('make a pixel scene', '画一个像素场景', 'make a pixel island',
                            'make a pixel island ' + 'with lanterns ' * 500):
                with self.subTest(request=request):
                    self.assertEqual(json.loads(mcp_server.intake_request(request)), self.cli_plan(request))


if __name__ == '__main__':
    unittest.main()
