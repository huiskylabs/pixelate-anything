#!/usr/bin/env python3
"""Static piece manifest validation, deterministic catalog and conservative search.

No contributed program, run command, or module is imported or executed here.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import NoReturn

MAX_MANIFEST = 128 * 1024
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
MODES = ('scene', 'rebuild', 'era', 'assets', 'music')
STATUSES = ('starter', 'study', 'accepted', 'reviewed')
RUNTIMES = ('script', 'pack', 'engine')
CAMERAS = ('side', '2:1 iso', '3/4 top-down', 'one-point perspective',
           'two-point perspective', 'oblique', 'military', 'none')
STYLES = ('lofi', 'pastel-cell', 'native-glow', 'hd-overworld', 'arcade', 'tactics',
          'sticker-iso', 'illustrated', 'neon-noir', 'cosy-lightmap', 'contre-jour', 'none')
ERAS = ('nes', 'gameboy', 'pico-8', 'genesis', 'gba', 'neogeo', 'snes', 'none')
MOTIONS = ('stills', 'loop', 'sprite-sheet', 'none')
SOUNDS = ('none', 'music', 'sting', 'sfx')
TOKEN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


class LibraryError(ValueError):
    """A piece declaration or catalog path is invalid."""


def fail(where, message) -> NoReturn:
    raise LibraryError(f'{where}: {message}')


def fields(value, required, optional=(), where='object'):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        fail(where, f'expected fields {sorted(required)}; optional {sorted(optional)}')


def text(value, where):
    if not isinstance(value, str) or not value.strip():
        fail(where, 'expected nonempty string')


def slug(value, where):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        fail(where, 'expected lowercase slug')


def choice(value, allowed, where):
    if value not in allowed or not isinstance(value, str):
        fail(where, f'expected one of {allowed}')


def positive(value, where):
    if type(value) is not int or value <= 0:
        fail(where, 'expected positive integer')


def names(value, where, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        fail(where, 'expected array of slugs')
    for name in value:
        slug(name, where)
    if len(value) != len(set(value)):
        fail(where, 'duplicate tag')


def relative(value, where):
    if (not isinstance(value, str) or not value or '\\' in value or '\x00' in value or
            value.startswith('/') or any(part in ('', '.', '..') for part in value.split('/'))):
        fail(where, 'unsafe relative path')
    return value


def asset(root, value, where, directory=False):
    relative(value, where)
    path = root
    for component in value.split('/'):
        path = path / component
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            fail(where, f'missing path {value}: {exc}')
        if stat.S_ISLNK(mode):
            fail(where, f'symlink: {value}')
    if not (path.is_dir() if directory else path.is_file() and stat.S_ISREG(path.stat().st_mode)):
        fail(where, f'wrong file type: {value}')
    return path


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LibraryError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def review_binding(root, manifest):
    # review_status is a trusted tool; it reads files but never executes piece code.
    if __package__:
        from . import review_status
    else:
        import review_status
    record = root / manifest['review']['record']
    try:
        payload = json.loads(record.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs)
        report = Path(payload['report'])
        report_relative = report.relative_to(root)
        asset(root, report_relative.as_posix(), 'review report')
    except (ValueError, KeyError, TypeError, UnicodeError, OSError) as exc:
        fail(root, f'unsafe review report: {exc}')
    for output in manifest['outputs']:
        if output['kind'] != 'image':
            continue
        frame = root / output['frame']
        brief = root / output['brief']
        if record != frame.with_name(frame.name + '.visual-review.json'):
            continue
        ready, reason = review_status.status(brief, frame)
        if ready:
            return
        fail(root, reason)
    fail(root, 'review record does not match an image output')


def validate(root):
    """Return validated manifest for one piece directory; never execute its run commands."""
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        fail(root, 'unsafe piece directory')
    slug(root.name, root)
    # Reject links even if they are not referenced in the manifest.
    for base, dirs, files in os.walk(root, followlinks=False, onerror=lambda exc: fail(root, exc)):
        for name in dirs + files:
            if (Path(base) / name).is_symlink():
                fail(root, f'symlink in piece: {Path(base) / name}')
    path = asset(root, 'piece.json', 'piece.json')
    if path.stat().st_size > MAX_MANIFEST:
        fail(path, 'manifest too large')
    try:
        manifest = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs,
                              parse_constant=lambda value: fail(path, f'nonfinite JSON number: {value}'))
    except (ValueError, UnicodeError) as exc:
        fail(path, f'invalid JSON: {exc}')
    fields(manifest, ('schema', 'id', 'title', 'summary', 'request', 'status', 'mode', 'runtime',
                      'tags', 'canvas', 'outputs', 'anatomy', 'knobs', 'provenance', 'license'),
           ('recipes', 'kit', 'media', 'lineage', 'review'), str(path))
    if type(manifest['schema']) is not int or manifest['schema'] != 1:
        fail(path, 'unsupported schema')
    slug(manifest['id'], 'id')
    if manifest['id'] != root.name:
        fail(path, 'id must match directory')
    for key in ('title', 'summary', 'request'):
        text(manifest[key], key)
    choice(manifest['status'], STATUSES, 'status')
    choice(manifest['mode'], MODES, 'mode')
    choice(manifest['runtime'], RUNTIMES, 'runtime')
    tags = manifest['tags']
    fields(tags, ('subject', 'setting', 'camera', 'style', 'era', 'motion', 'sound'), where='tags')
    for key in ('subject', 'setting'):
        names(tags[key], f'tags.{key}', nonempty=True)
    for key, values in (('camera', CAMERAS), ('style', STYLES), ('era', ERAS),
                        ('motion', MOTIONS), ('sound', SOUNDS)):
        choice(tags[key], values, f'tags.{key}')
    fields(manifest['canvas'], ('w', 'h', 'scale'), where='canvas')
    for key, value in manifest['canvas'].items():
        positive(value, f'canvas.{key}')
    outputs = manifest['outputs']
    if not isinstance(outputs, list) or not outputs:
        fail('outputs', 'expected nonempty array')
    seen = set()
    for output in outputs:
        if not isinstance(output, dict):
            fail('outputs', 'expected objects')
        kind = output.get('kind')
        choice(kind, ('image', 'audio', 'export'), 'output.kind')
        if kind not in ('image', 'audio', 'export'):
            fail('output.kind', 'invalid kind')
        extra = {'image': ('frame', 'style', 'scale', 'brief'), 'audio': ('file',), 'export': ('file',)}[kind]
        fields(output, ('name', 'kind', 'run', *extra), ('pal',) if kind == 'image' else (), 'output')
        slug(output['name'], 'output.name')
        if output['name'] in seen:
            fail('outputs', 'duplicate name')
        seen.add(output['name'])
        text(output['run'], 'output.run')
        if kind == 'image':
            choice(output['style'], STYLES[:-1], 'output.style')
            positive(output['scale'], 'output.scale')
            for key in ('frame', 'brief', 'pal'):
                if key in output:
                    asset(root, output[key], f'output.{key}')
        else:
            asset(root, output['file'], 'output.file')
    anatomy = manifest['anatomy']
    if not isinstance(anatomy, list) or not anatomy:
        fail('anatomy', 'expected nonempty array')
    for entry in anatomy:
        fields(entry, ('file', 'draws', 'change_for'), where='anatomy')
        asset(root, entry['file'], 'anatomy.file')
        for key in ('draws', 'change_for'):
            text(entry[key], f'anatomy.{key}')
    knobs = manifest['knobs']
    if not isinstance(knobs, dict):
        fail('knobs', 'expected object')
    for name, knob in knobs.items():
        slug(name, 'knob name')
        if not isinstance(knob, dict):
            fail(name, 'expected knob object')
        if 'values' in knob:
            fields(knob, ('values', 'default', 'edits'), where=name)
            values = knob['values']
            if (not isinstance(values, list) or not values or
                    any(type(v) not in (str, int, float, bool) for v in values) or
                    len({(type(v).__name__, v) for v in values}) != len(values) or
                    not any(type(v) is type(knob['default']) and v == knob['default'] for v in values)):
                fail(name, 'expected distinct scalar values and matching default')
        else:
            fields(knob, ('type', 'default', 'edits'), where=name)
            if knob['type'] != 'int' or type(knob['default']) is not int:
                fail(name, 'expected integer knob')
        asset(root, knob['edits'], f'knobs.{name}.edits')
    provenance = manifest['provenance']
    fields(provenance, ('made', 'by'), where='provenance')
    text(provenance['by'], 'provenance.by')
    try:
        if not isinstance(provenance['made'], str) or datetime.date.fromisoformat(provenance['made']).isoformat() != provenance['made']:
            raise ValueError('invalid date')
    except ValueError:
        fail('provenance.made', 'expected YYYY-MM-DD date')
    if manifest['license'] != 'MIT':
        fail('license', 'expected MIT')
    if 'recipes' in manifest:
        names(manifest['recipes'], 'recipes')
    if 'kit' in manifest:
        fields(manifest['kit'], ('tested',), where='kit')
        text(manifest['kit']['tested'], 'kit.tested')
    if 'lineage' in manifest:
        fields(manifest['lineage'], ('remixed_from',), where='lineage')
        if manifest['lineage']['remixed_from'] is not None:
            slug(manifest['lineage']['remixed_from'], 'lineage.remixed_from')
    if 'media' in manifest:
        fields(manifest['media'], (), ('thumb', 'contact', 'video', 'gif'), 'media')
        for key, value in manifest['media'].items():
            if value is not None:
                asset(root, value, f'media.{key}')
    if 'review' in manifest:
        review = manifest['review']
        fields(review, ('notes', 'approved_by', 'record'), where='review')
        for key in ('notes', 'record'):
            if review[key] is not None:
                asset(root, review[key], f'review.{key}')
        if review['approved_by'] is not None:
            choice(review['approved_by'], ('user', 'art-director'), 'review.approved_by')
    if (manifest['status'] in ('accepted', 'reviewed') and
            (len(knobs) < 2 or not any(o['kind'] == 'image' for o in outputs) or
             'media' not in manifest or not all(manifest['media'].get(k) for k in ('thumb', 'contact')) or
             'review' not in manifest or not manifest['review']['notes'] or
             not manifest['review']['approved_by'])):
        fail(path, 'accepted requires two knobs, golden image, media, approval and review notes')
    if manifest['status'] in ('accepted', 'reviewed') and asset(root, manifest['review']['notes'], 'review.notes').stat().st_size == 0:
        fail(path, 'review notes cannot be empty')
    if manifest['status'] == 'reviewed' and not manifest['review']['record']:
        fail(path, 'reviewed requires review record')
    if manifest['status'] == 'reviewed':
        review_binding(root, manifest)
    return manifest


def scan(library):
    """Read all immediate piece directories in id order, rejecting duplicate IDs and links."""
    library = Path(library).absolute()
    if library.is_symlink() or not library.is_dir():
        fail(library, 'missing or unsafe library directory')
    pieces = {}
    for path in sorted(library.iterdir()):
        if path.name == 'index.json':
            continue
        if path.is_symlink():
            fail(path, 'symlink in library')
        if not path.is_dir():
            fail(path, 'unexpected catalog entry')
        piece = validate(path)
        if piece['id'] in pieces:
            fail(path, 'duplicate id')
        pieces[piece['id']] = piece
    return pieces


def index(library):
    """Generate stable catalog bytes; callers may write these to index.json."""
    return (json.dumps({'schema': 1, 'pieces': [{'id': p['id'], 'title': p['title'], 'status': p['status'],
                  'mode': p['mode'], 'summary': p['summary'], 'tags': p['tags'], 'path': f"{p['id']}/piece.json"}
                  for p in scan(library).values()]}, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def write_index(library):
    library = Path(library).absolute()
    content = index(library)
    target = library / 'index.json'
    if target.is_symlink() or (target.exists() and not target.is_file()):
        fail(target, 'unsafe index path')
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=library, prefix='.index-', delete=False) as handle:
            name = handle.name
            handle.write(content)
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return content


def list_pieces(library):
    return [{'id': p['id'], 'title': p['title'], 'mode': p['mode'], 'status': p['status']}
            for p in scan(library).values()]


def show(library, piece_id):
    slug(piece_id, 'id')
    pieces = scan(library)
    if piece_id not in pieces:
        fail(piece_id, 'unknown piece')
    return pieces[piece_id]


def query_tags(request, mode=None):
    """Conservative router-style explicit signals; generic phrases never fabricate a match."""
    text(request, 'request')
    lower = request.lower()
    tokens = set(TOKEN.findall(lower))
    def phrase(word):
        return bool(re.search(r'(?<![a-z0-9])' + re.escape(word) + r'(?![a-z0-9])', lower))
    detected = mode or next((m for m, terms in (
        ('rebuild', ('photo', 'rebuild', 'reference image')),
        ('era', ('nes', 'game boy', 'gameboy', 'snes', 'pico-8', 'genesis', 'gba', 'neogeo')),
        ('assets', ('sprite sheet', 'spritesheet', 'tileset', 'icons', 'assets')),
        ('music', ('music only', 'soundtrack only', 'just music', 'chiptune')))
        if any(phrase(term) for term in terms)), 'scene')
    choice(detected, MODES, 'mode')
    camera_terms = {'2:1 iso': ('isometric', 'iso', '2:1'), 'side': ('side view', 'side-on', 'platformer'),
                    '3/4 top-down': ('top-down', 'top down', 'overhead'),
                    'one-point perspective': ('one-point perspective',),
                    'two-point perspective': ('two-point perspective',)}
    def explicit(terms):
        matches = [key for key, phrases in terms.items() if any(phrase(w) for w in phrases)]
        return matches[0] if len(matches) == 1 else None
    return {'mode': detected, 'camera': explicit(camera_terms),
            'style': explicit({s: (s,) for s in STYLES[:-1]}),
            'era': explicit({e: (e.replace('-', ' '), e) for e in ERAS[:-1]}),
            'motion': explicit({'loop': ('loop', 'looping'), 'stills': ('still', 'stills'),
                                'sprite-sheet': ('sprite sheet', 'spritesheet')}),
            'words': tokens - {'a', 'an', 'the', 'of', 'in', 'and', 'for', 'pixel', 'art', 'make', 'me',
                               'with', 'scene', 'draw', 'please', 'my', 'at', 'on', 'to', 'create',
                               'original', 'image', 'picture', 'some', 'this', 'show'}}


def find(library, request, mode=None, limit=3):
    """Return matched pieces and a fallback plan. Status only breaks relevant ties."""
    query = query_tags(request, mode)
    if type(limit) is not int or limit < 1:
        fail('limit', 'expected positive integer')
    ranked, starters = [], []
    for piece in scan(library).values():
        if piece['mode'] != query['mode']:
            continue
        if piece['status'] == 'starter':
            starters.append(piece['id'])
            continue
        tags = piece['tags']
        differences, reasons = [], []
        for key in ('camera', 'style', 'era', 'motion'):
            if query[key]:
                if tags[key] == query[key]:
                    reasons.append(key)
                else:
                    differences.append(key)
        relevant = query['words'] & (set(tags['subject']) | set(tags['setting']) |
                   set(TOKEN.findall(' '.join((piece['title'], piece['summary'], piece['request'])).lower())))
        reasons.extend(sorted(relevant))
        # A tag-only camera/style match is not enough to recommend a base.
        if differences or not relevant:
            continue
        intent_words = set(TOKEN.findall(' '.join(str(query[key]) for key in
                        ('camera', 'style', 'era', 'motion') if query[key]).lower()))
        differences = [f'unmatched term: {word}' for word in sorted(query['words'] - relevant - intent_words)]
        score = 5 * len(relevant) + 4 * sum(k in reasons for k in ('camera', 'era')) + 3 * sum(
            k in reasons for k in ('style', 'motion')) + {'study': 0, 'accepted': 1, 'reviewed': 2}[piece['status']]
        ranked.append({'id': piece['id'], 'status': piece['status'], 'score': score, 'why': reasons,
                       'differs': differences})
    ranked.sort(key=lambda result: (-result['score'], result['id']))
    return {'mode': query['mode'], 'matches': ranked[:limit],
            'fallback': {'kind': 'starter', 'ids': starters} if starters else
                        {'kind': 'author', 'reason': 'no matching starter; author a new piece'}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=Path(__file__).resolve().parent.parent / 'library')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('index')
    commands.add_parser('list')
    commands.add_parser('show').add_argument('id')
    finding = commands.add_parser('find')
    finding.add_argument('request')
    finding.add_argument('--mode', choices=MODES)
    args = parser.parse_args(argv)
    try:
        result = {'index': lambda: write_index(args.library).decode('utf-8'),
                  'list': lambda: list_pieces(args.library),
                  'show': lambda: show(args.library, args.id),
                  'find': lambda: find(args.library, args.request, args.mode)}[args.command]()
    except LibraryError as exc:
        parser.exit(2, f'library: {exc}\n')
    print(result if isinstance(result, str) else json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == '__main__':
    main()
