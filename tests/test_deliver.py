"""`pixelate deliver`: final render, gate, package and script-written DELIVERY.md facts; `--verify` runs nothing.

Fixture pieces are trusted code written by these tests; one test delivers a remix of the first-party
starter-scene-still."""
import contextlib
import hashlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
deliver = importlib.import_module('deliver')
review_status = importlib.import_module('review_status')

PY = sys.executable
# A frame that passes the arcade gate (as in tests/test_remix.py); `dusk` darkens the sky.
DRAW = '''import sys
from PIL import Image
from piece import knobs
k = knobs()
sky = (4, 4, 12) if k.get('time') == 'dusk' else (8, 10, 18)
im = Image.new('RGB', (64, 48), sky)
im.paste((70, 40, 30), (0, 30, 64, 48))
for x in range(1, 64, 5):
    for y in range(32 + x % 3, 48, 4):
        im.paste((150, 120, 90) if (x + y) % 2 else (40, 90, 110), (x, y, x + 2, y + 2))
im.paste((150, 120, 90), (24, 8, 40, 20))
im.paste((90, 60, 40), (26, 10, 38, 18))
im.resize((256, 192), Image.NEAREST).save('out/a.png')
'''
SOUND = '''import pathlib
pathlib.Path('sound/tone.wav').write_bytes(b'RIFF fixture audio')
'''
EXPORT = '''import json, pathlib
pathlib.Path('out/sheet.json').write_text(json.dumps({'frames': 4}))
'''
NOOP = f'{PY} -c "pass"'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lead(grade='A'):
    scores = ' '.join(f'{n}={5 if n in (1, 3, 4) else 4}' for n in range(1, 13))
    fixes = '' if grade == 'A' else '1. lift the hero\n2. vary the masses\n3. cut the stripes\n'
    return (f'GRADE: {grade}\nSCORES: {scores} originality: pass\nSIGNATURE MOMENT: the lit block\n'
            'BIGGEST PROBLEM: flat sky\nFIXES (ranked by impact, up to 5; 3 to 5 below A):\n' + fixes + 'KEEP: the block\n')


def image(**fields):
    return dict({'name': 'a', 'kind': 'image', 'run': f'{PY} art/draw.py', 'frame': 'out/a.png', 'style': 'arcade',
                 'scale': 4, 'brief': 'brief.md'}, **fields)


def make_piece(parent, piece_id='harbour', status='starter', outputs=None, runtime='script', **extra):
    root = Path(parent) / piece_id
    for folder in ('art', 'sound', 'out', 'media', 'history'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / 'art' / 'draw.py').write_text(DRAW, encoding='utf-8')
    (root / 'sound' / 'make.py').write_text(SOUND, encoding='utf-8')
    (root / 'art' / 'export.py').write_text(EXPORT, encoding='utf-8')
    (root / 'brief.md').write_text('# Harbour\n\nA harbour wall at night.\n', encoding='utf-8')
    manifest = {'schema': 1, 'id': piece_id, 'title': 'Harbour', 'summary': 'A harbour wall at night.',
                'request': 'a harbour wall at night', 'status': status, 'mode': 'scene', 'runtime': runtime,
                'tags': {'subject': ['harbour'], 'setting': ['night'], 'camera': 'side', 'style': 'arcade',
                         'era': 'none', 'motion': 'stills', 'sound': 'none'},
                'canvas': {'w': 64, 'h': 48, 'scale': 4}, 'outputs': outputs or [image()],
                'anatomy': [{'file': 'art/draw.py', 'draws': 'everything', 'change_for': 'anything'}],
                'knobs': {}, 'provenance': {'made': '2026-10-18', 'by': 'tests/test_deliver.py'}, 'license': 'MIT'}
    manifest.update(extra)
    (root / 'piece.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return root


KNOBS = {'time': {'values': ['day', 'dusk'], 'default': 'day', 'edits': 'art/draw.py'},
         'seed': {'type': 'int', 'default': 3, 'edits': 'art/draw.py'}}


def accepted_fields(root, approved_by='user'):
    for name in ('media/thumb.png', 'media/contact.png'):
        (root / name).write_bytes(b'fixture media')
    (root / 'history' / 'notes.md').write_text('The user said they like it.\n', encoding='utf-8')
    return {'knobs': KNOBS,
            'media': {'thumb': 'media/thumb.png', 'contact': 'media/contact.png'},
            'review': {'notes': 'history/notes.md', 'approved_by': approved_by, 'record': None}}


def runs(root):
    return [json.loads(line) for line in (root / '.pixelate' / 'runs.jsonl').read_text(encoding='utf-8').splitlines()]


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop('PIXELATE_NO_LOG', None)
        os.environ.pop('PIXELATE_KNOBS', None)

    def main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = deliver.main([str(a) for a in args])
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def delivered(self, root, *sets):
        result = deliver.deliver(root, sets)
        self.assertTrue(result['ok'], result['errors'])
        return result

    def failed(self, root, *sets, **kw):
        result = deliver.deliver(root, sets, **kw)
        self.assertFalse(result['ok'])
        self.assertFalse((root / deliver.PACKAGE).exists())
        return result

    def text(self, root):
        return (root / deliver.PACKAGE / deliver.DELIVERY).read_text(encoding='utf-8')


class Delivers(Base):
    def test_still_is_packaged_with_facts_a_fingerprint_and_a_run_record(self):
        root = make_piece(self.work)
        (root / '.pixelate').mkdir()
        (root / '.pixelate' / 'runs.jsonl').write_text('{"type": "earlier"}\n', encoding='utf-8')
        result = self.delivered(root)
        package = root / deliver.PACKAGE
        self.assertEqual(sorted(p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()),
                         ['DELIVERY.md', 'out/a.png'])
        frame = (package / 'out' / 'a.png').read_bytes()
        self.assertEqual(frame, (root / 'out' / 'a.png').read_bytes())
        before, facts, after = deliver.parse_delivery(self.text(root))
        self.assertEqual(result['fingerprint'], deliver.fingerprint(facts))
        self.assertIn(f"Fingerprint: sha256:{result['fingerprint']}", self.text(root))
        (out,) = facts['outputs']
        self.assertEqual((out['path'], out['sha256'], out['bytes']), ('out/a.png', sha(frame), len(frame)))
        self.assertTrue(out['gate']['ok'])
        self.assertEqual(out['snapshot'], f'.pixelate/snapshots/{sha(frame)}/a.png')
        self.assertEqual(out['review'], {'status': 'NOT REVIEWED'})
        self.assertEqual(facts['evidence']['critique'], 'NOT REVIEWED')
        self.assertEqual(facts['evidence']['approval'], {'declared_by': None, 'notes': None, 'verified': False})
        self.assertIn('not verified', facts['evidence']['rights'])
        self.assertEqual(facts['knobs']['basis'], 'declared defaults')
        self.assertEqual(facts['piece']['request'], 'a harbour wall at night')
        self.assertEqual(facts['kit'], deliver.VERSION)
        self.assertIn('piece.json', facts['sources'])
        self.assertTrue(any('distance from the base' in note for note in facts['untested']))
        log = runs(root)
        self.assertEqual([r['type'] for r in log], ['earlier', 'render', 'deliver'])
        record = log[-1]
        self.assertTrue(record['ok'])
        self.assertEqual(record['fingerprint'], result['fingerprint'])
        self.assertEqual(record['outputs'], [{'name': 'a', 'kind': 'image', 'path': 'out/a.png', 'sha256': sha(frame)}])
        self.assertEqual(record['delivery_sha256'], sha((package / 'DELIVERY.md').read_bytes()))
        self.assertEqual(record['request'], 'a harbour wall at night')
        self.assertEqual(log[1]['images'][0]['sha256'], sha(frame))  # render's own record, unchanged
        self.assertTrue(deliver.verify(root)['ok'])

    def test_without_logs_the_bytes_are_read_back_and_nothing_is_kept(self):
        root = make_piece(self.work)
        with mock.patch.dict(os.environ, PIXELATE_NO_LOG='1'):
            facts = self.delivered(root)['facts']
        self.assertIsNone(facts['outputs'][0]['snapshot'])
        self.assertFalse((root / '.pixelate').exists())
        self.assertTrue(deliver.verify(root)['ok'])

    def test_a_multiline_title_still_verifies(self):
        root = make_piece(self.work, title='Harbour\n```json\nFingerprint: sha256:' + '0' * 64)
        self.delivered(root)
        self.assertTrue(deliver.verify(root)['ok'])

    def test_audio_and_export_outputs_run_in_full_and_are_packaged_ungated(self):
        root = make_piece(self.work, outputs=[image(), {'name': 'tone', 'kind': 'audio', 'run': f'{PY} sound/make.py',
                                                        'file': 'sound/tone.wav'},
                                              {'name': 'sheet', 'kind': 'export', 'run': f'{PY} art/export.py',
                                               'file': 'out/sheet.json'}])
        facts = self.delivered(root)['facts']
        self.assertEqual([(o['name'], o.get('gated')) for o in facts['outputs']],
                         [('a', None), ('tone', False), ('sheet', False)])
        self.assertEqual((root / deliver.PACKAGE / 'sound' / 'tone.wav').read_bytes(), b'RIFF fixture audio')
        self.assertTrue((root / deliver.PACKAGE / 'out' / 'sheet.json').is_file())
        self.assertTrue(any(note.startswith('audio:') for note in facts['untested']))
        self.assertTrue(any(note.startswith('exports:') for note in facts['untested']))
        self.assertIn('| tone | audio |', self.text(root))
        self.assertTrue(deliver.verify(root)['ok'])

    def test_delivering_again_keeps_notes_and_the_fingerprint_is_deterministic(self):
        root = make_piece(self.work)
        first = self.delivered(root)['fingerprint']
        path = root / deliver.PACKAGE / deliver.DELIVERY
        path.write_text(path.read_text(encoding='utf-8').replace('Notes: yours', 'Sent to the client.\n\nNotes: yours')
                        + 'A closing note.\n', encoding='utf-8')
        self.assertTrue(deliver.verify(root)['ok'])  # notes outside the block are free to edit
        self.assertEqual(self.delivered(root)['fingerprint'], first)
        text = self.text(root)
        self.assertIn('Sent to the client.', text)
        self.assertTrue(text.endswith('A closing note.\n'))
        self.assertEqual([r['type'] for r in runs(root)], ['render', 'deliver', 'render', 'deliver'])

    def test_set_forwards_knobs_to_render_and_records_its_values(self):
        root = make_piece(self.work, knobs=KNOBS)
        facts = self.delivered(root, 'time=dusk')['facts']
        self.assertEqual(facts['knobs']['basis'], 'set')
        self.assertEqual(facts['knobs']['set'], {'time': 'dusk'})
        self.assertEqual(facts['knobs']['merged'], {'time': 'dusk', 'seed': 3})
        self.assertRegex(facts['knobs']['file_sha256'], r'^[0-9a-f]{64}$')
        self.assertTrue(deliver.verify(root)['ok'])
        defaults = self.delivered(root)['facts']['knobs']
        self.assertEqual(defaults['basis'], 'declared defaults')
        self.assertEqual(defaults['defaults'], {'time': 'day', 'seed': 3})
        self.assertIn('not proven', defaults['note'])
        self.assertIn('Knobs (declared defaults): seed=3, time="day"', self.text(root))

    def test_render_refusing_a_set_is_a_refusal(self):
        root = make_piece(self.work, runtime='pack')
        code, out, err = self.main(root, '--set', 'time=dusk')
        self.assertEqual(code, 2)
        self.assertIn('render refused', out)
        self.assertFalse((root / deliver.PACKAGE).exists())

    def test_first_party_starter_scene_still_remix(self):
        root = self.work / 'quiet-harbour'
        created = subprocess.run([PY, str(REPO / 'pixelate'), 'remix', 'starter-scene-still', str(root),
                                  '--request', 'a quiet harbour at dusk'], capture_output=True, text=True)
        self.assertEqual(created.returncode, 0, created.stderr)
        result = subprocess.run([PY, str(REPO / 'pixelate'), 'deliver', str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        _, facts, _ = deliver.parse_delivery(self.text(root))
        self.assertEqual(facts['piece']['lineage'], {'remixed_from': 'starter-scene-still'})
        self.assertEqual(facts['remix_baseline']['path'], '.pixelate/remix-baseline.json')
        verified = subprocess.run([PY, str(REPO / 'pixelate'), 'deliver', str(root), '--verify'],
                                  capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.assertIn('VERIFIED', verified.stdout)


class Refuses(Base):
    def test_a_no_op_command_cannot_pass_a_stale_frame(self):
        root = make_piece(self.work, outputs=[image(run=NOOP)])
        subprocess.run([PY, 'art/draw.py'], cwd=root, check=True, env=dict(os.environ, PYTHONPATH=str(REPO / 'tools')))
        result = self.failed(root)
        self.assertTrue(any('frame not found: out/a.png' in e for e in result['errors']), result['errors'])
        record = runs(root)[-1]
        self.assertEqual((record['type'], record['ok'], record['fingerprint']), ('deliver', False, None))

    def test_a_gate_failure_blocks_even_a_study(self):
        for status in ('starter', 'study'):
            with self.subTest(status=status):
                root = make_piece(self.work, f'era-{status}', status, outputs=[image(style='', era='nes')])
                result = self.failed(root)
                self.assertTrue(any('gate FAIL' in e and 'FAIL era' in e for e in result['errors']), result['errors'])
                self.assertEqual(status == 'study', any('a study blocks delivery' in e for e in result['errors']))

    def test_a_link_output_is_unsafe(self):
        outside = self.work / 'outside.png'
        outside.write_bytes(b'not the piece')
        root = make_piece(self.work, outputs=[image(run=f'mkdir -p out && ln -s {outside} out/a.png')])
        result = self.failed(root)
        self.assertTrue(any('unsafe frame' in e for e in result['errors']), result['errors'])
        self.assertEqual(outside.read_bytes(), b'not the piece')

    def test_a_linked_package_folder_is_refused_and_its_target_untouched(self):
        root = make_piece(self.work)
        outside = self.work / 'elsewhere'
        outside.mkdir()
        (root / 'dist').mkdir()
        (root / 'dist' / 'delivery').symlink_to(outside, target_is_directory=True)
        code, _, err = self.main(root)
        self.assertEqual(code, 2)
        self.assertIn('symlink', err)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(deliver.verify(root)['ok'])

    def test_an_unowned_package_folder_is_never_replaced(self):
        root = make_piece(self.work)
        (root / deliver.PACKAGE).mkdir(parents=True)
        (root / deliver.PACKAGE / 'client.txt').write_text('keep me', encoding='utf-8')
        result = deliver.deliver(root)
        self.assertFalse(result['ok'])
        self.assertTrue(any('holds no DELIVERY.md' in e for e in result['errors']), result['errors'])
        self.assertEqual((root / deliver.PACKAGE / 'client.txt').read_text(encoding='utf-8'), 'keep me')

    def test_a_package_with_edited_facts_or_extra_files_is_not_replaced(self):
        root = make_piece(self.work)
        self.delivered(root)
        extra = root / deliver.PACKAGE / 'client.txt'
        extra.write_text('keep me', encoding='utf-8')
        result = deliver.deliver(root)
        self.assertTrue(any('files deliver did not write (client.txt)' in e for e in result['errors']), result['errors'])
        extra.unlink()
        path = root / deliver.PACKAGE / deliver.DELIVERY
        edited = path.read_text(encoding='utf-8').replace('| PASS (', '| PASSED (') + 'my notes\n'
        path.write_text(edited, encoding='utf-8')
        result = deliver.deliver(root)
        self.assertTrue(any('does not verify' in e and 'no note is lost' in e for e in result['errors']), result['errors'])
        self.assertEqual(path.read_text(encoding='utf-8'), edited)

    def test_an_edited_deleted_or_linked_packaged_output_is_not_replaced(self):
        root = make_piece(self.work)
        self.delivered(root)
        packaged = root / deliver.PACKAGE / 'out' / 'a.png'
        md = root / deliver.PACKAGE / deliver.DELIVERY
        md.write_text(md.read_text(encoding='utf-8') + 'my notes\n', encoding='utf-8')
        original, md_text = packaged.read_bytes(), md.read_bytes()
        outside = self.work / 'outside.png'
        outside.write_bytes(original)
        for label, damage, expect in (
                ('edited', lambda: packaged.write_bytes(original + b'x'), 'a.png (edited)'),
                ('same size', lambda: packaged.write_bytes(bytes(len(original))), 'a.png (edited)'),
                ('deleted', lambda: None, 'a.png (missing)'),
                ('linked', lambda: packaged.symlink_to(outside), 'symlink in piece'),
                ('not regular', lambda: os.mkfifo(packaged), 'not a regular file in the package')):
            with self.subTest(damage=label):
                packaged.unlink(missing_ok=True)
                damage()
                before = sorted(p.name for p in packaged.parent.iterdir())
                try:
                    errors = deliver.deliver(root)['errors']
                except deliver.DeliveryError as exc:  # a link anywhere in the piece makes it invalid
                    errors = [str(exc)]
                self.assertTrue(any(expect in e for e in errors), errors)
                self.assertEqual(md.read_bytes(), md_text)
                self.assertEqual(sorted(p.name for p in packaged.parent.iterdir()), before)
                self.assertEqual(sorted(p.name for p in (root / 'dist').iterdir()), ['delivery'])
                self.assertEqual(outside.read_bytes(), original)
        packaged.unlink()
        packaged.write_bytes(original)
        self.delivered(root)
        self.assertIn('my notes', self.text(root))

    def test_edited_sources_still_redeliver_over_an_intact_package_and_keep_notes(self):
        root = make_piece(self.work)
        self.delivered(root)
        md = root / deliver.PACKAGE / deliver.DELIVERY
        md.write_text(md.read_text(encoding='utf-8') + 'Sent to the client.\n', encoding='utf-8')
        old = (root / deliver.PACKAGE / 'out' / 'a.png').read_bytes()
        draw = root / 'art' / 'draw.py'
        draw.write_text(draw.read_text(encoding='utf-8').replace('(24, 8, 40, 20)', '(20, 8, 40, 20)'), encoding='utf-8')
        (root / 'out' / 'a.png').write_bytes(b'stale')  # the current output differs from the delivered one too
        self.assertTrue(self.delivered(root)['ok'])
        self.assertNotEqual((root / deliver.PACKAGE / 'out' / 'a.png').read_bytes(), old)
        self.assertIn('Sent to the client.', self.text(root))
        self.assertTrue(deliver.verify(root)['ok'])

    def test_a_render_that_runs_too_long_is_killed(self):
        root = make_piece(self.work, outputs=[image(run=f'{PY} -c "import time; time.sleep(60)"')])
        result = self.failed(root, timeout=1)
        self.assertEqual(result['errors'], ['render timed out after 1s and was killed with its process group'])

    def test_legacy_render_json_and_bad_timeouts_exit_2(self):
        root = make_piece(self.work)
        self.assertEqual(self.main(root, '--timeout', '0')[0], 2)
        (root / 'render.json').write_text('{"images": []}', encoding='utf-8')
        code, _, err = self.main(root)
        self.assertEqual(code, 2)
        self.assertIn('legacy render.json', err)


class Review(Base):
    def record(self, root, grade='A'):
        (root / 'history' / 'lead.md').write_text(lead(grade), encoding='utf-8')
        review_status.record(root / 'brief.md', root / 'history' / 'lead.md', root / 'out' / 'a.png')

    def test_a_bound_a_review_is_reported_for_the_delivered_bytes(self):
        root = make_piece(self.work)
        self.delivered(root)
        self.record(root)
        facts = self.delivered(root)['facts']
        review = facts['outputs'][0]['review']
        self.assertEqual((review['status'], review['grade'], review['record']), ('A, bound', 'A', 'out/a.png.visual-review.json'))
        self.assertIn('a A, bound', facts['evidence']['critique'])
        self.assertIn('Reviewer independence is not verified', self.text(root))
        self.assertTrue(deliver.verify(root)['ok'])
        self.record(root, 'B')
        self.assertFalse(deliver.verify(root)['ok'])  # the record changed since delivery
        review = self.delivered(root)['facts']['outputs'][0]['review']
        self.assertEqual((review['status'], review['grade']), ('below A, bound', 'B'))

    def test_a_record_bound_to_other_bytes_blocks_delivery(self):
        root = make_piece(self.work)
        self.delivered(root)
        self.record(root)
        draw = root / 'art' / 'draw.py'
        draw.write_text(draw.read_text(encoding='utf-8').replace('(24, 8, 40, 20)', '(20, 8, 40, 20)'), encoding='utf-8')
        result = deliver.deliver(root)
        self.assertFalse(result['ok'])
        self.assertTrue(any('does not bind the delivered bytes' in e and 'frame changed since review' in e
                            for e in result['errors']), result['errors'])
        self.assertFalse(deliver.verify(root)['ok'])  # the earlier package no longer matches the piece

    def test_a_declared_approval_is_not_approval(self):
        root = make_piece(self.work, status='accepted')
        fields = accepted_fields(root)
        manifest = json.loads((root / 'piece.json').read_text(encoding='utf-8'))
        manifest.update(fields)
        (root / 'piece.json').write_text(json.dumps(manifest), encoding='utf-8')
        facts = self.delivered(root)['facts']
        self.assertEqual(facts['evidence']['approval'], {'declared_by': 'user', 'notes': 'history/notes.md', 'verified': False})
        self.assertEqual(facts['evidence']['critique'], 'NOT REVIEWED')
        self.assertEqual(facts['piece']['status'], 'accepted')
        text = self.text(root)
        self.assertIn('Approval: declared by `user` in `history/notes.md`: UNVERIFIED, not treated as approval.', text)
        self.assertIn('status `accepted` as declared', text)
        self.assertNotRegex(text.replace('not treated as approval', ''), r'(?i)\bapproved\b')


class Verify(Base):
    def setUp(self):
        super().setUp()
        self.root = make_piece(self.work)
        self.delivered(self.root)
        self.md = self.root / deliver.PACKAGE / deliver.DELIVERY

    def failing(self):
        result = deliver.verify(self.root)
        self.assertFalse(result['ok'])
        return [c for c in result['checks'] if not c['ok']]

    def test_verify_starts_no_process(self):
        boom = AssertionError('verify must not start a process')
        with mock.patch.object(subprocess, 'Popen', side_effect=boom), mock.patch.object(os, 'system', side_effect=boom), \
                mock.patch.object(os, 'posix_spawn', side_effect=boom), mock.patch.object(os, 'fork', side_effect=boom):
            code, out, _ = self.main(self.root, '--verify')
        self.assertEqual(code, 0, out)
        self.assertIn('VERIFIED', out)
        self.assertEqual(self.main(self.root, '--verify', '--set', 'time=dusk')[0], 2)

    def test_edited_facts_fail(self):
        text = self.md.read_text(encoding='utf-8')
        for old, new in (('| PASS (', '| PASSED ('), ('"status": "starter"', '"status": "reviewed"'),
                         ('Fingerprint: sha256:', 'Fingerprint: sha256:0')):
            with self.subTest(edit=old):
                self.md.write_text(text.replace(old, new, 1), encoding='utf-8')
                (failed,) = self.failing()
                self.assertEqual(failed['check'], 'facts')
        self.md.write_text(text, encoding='utf-8')
        self.assertTrue(deliver.verify(self.root)['ok'])

    def test_a_consistently_rewritten_fingerprint_still_fails_on_the_bytes(self):
        # The fingerprint detects edits, not a forger who recomputes it: the hashes still have to match.
        before, facts, after = deliver.parse_delivery(self.md.read_text(encoding='utf-8'))
        facts['outputs'][0]['sha256'] = '0' * 64
        self.md.write_text(before + deliver.facts_block(facts) + after, encoding='utf-8')
        names = [c['check'] for c in self.failing()]
        self.assertEqual(names, ['a package', 'a piece'])

    def test_changed_artifact_bytes_fail(self):
        packaged = self.root / deliver.PACKAGE / 'out' / 'a.png'
        packaged.write_bytes(packaged.read_bytes() + b'x')
        self.assertEqual([c['check'] for c in self.failing()], ['a package'])
        packaged.write_bytes(packaged.read_bytes()[:-1])
        frame = self.root / 'out' / 'a.png'
        frame.write_bytes(b'other')
        self.assertEqual([c['check'] for c in self.failing()], ['a piece'])

    def test_links_extra_files_and_source_edits_fail(self):
        packaged = self.root / deliver.PACKAGE / 'out' / 'a.png'
        keep = self.work / 'a.png'
        shutil.move(packaged, keep)
        packaged.symlink_to(keep)
        self.assertIn('package files', [c['check'] for c in self.failing()])
        packaged.unlink()
        shutil.move(keep, packaged)
        (self.root / deliver.PACKAGE / 'extra.txt').write_text('x', encoding='utf-8')
        self.assertEqual([c['check'] for c in self.failing()], ['package files'])
        (self.root / deliver.PACKAGE / 'extra.txt').unlink()
        (self.root / 'brief.md').write_text('# Changed\n', encoding='utf-8')
        (failed,) = self.failing()
        self.assertEqual((failed['check'], failed['detail']), ('sources', 'changed since delivery: brief.md'))

    def test_a_missing_package_is_not_delivered(self):
        shutil.rmtree(self.root / 'dist')
        code, out, _ = self.main(self.root, '--verify')
        self.assertEqual(code, 1)
        self.assertIn('not delivered', out)


class Command(unittest.TestCase):
    def test_help_is_honest(self):
        top = subprocess.run([PY, str(REPO / 'pixelate'), '--help'], capture_output=True, text=True).stdout
        self.assertIn('pixelate deliver DIR [--set KNOB=VALUE ...] [--timeout S]', top)
        self.assertIn('pixelate deliver DIR --verify', top)
        own = subprocess.run([PY, str(REPO / 'pixelate'), 'deliver', '--help'], capture_output=True, text=True)
        self.assertEqual(own.returncode, 0)
        for phrase in ('dist/delivery', 'without a sandbox', 'runs no piece code', 'not verified', 'No critique is run',
                       '--timeout', '--verify', 'unverified'):
            self.assertIn(phrase, own.stdout)


if __name__ == '__main__':
    unittest.main()
