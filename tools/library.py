#!/usr/bin/env python3
"""Static piece manifest validation, deterministic catalog and conservative search.

`index`, `list`, `show` and `find` never import or execute piece code. Only `test` runs a piece: it
renders a temporary copy of a trusted checked-in piece through `tools/render.py`, which runs the
manifest's shell commands without a sandbox.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path
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
RECIPE = re.compile(r'[a-z][a-z0-9_]*\Z')  # a function name in tools/recipes.py
# Optional string gate inputs of a `tools/render.py` image; as there, an empty string means unset.
IMAGE_GATE = ('style', 'era', 'scene', 'brief', 'pal', 'pre', 'actor', 'used', 'intent', 'judge_ignore')
# Gate inputs the run command may write; like an image `frame` or an audio or export `file`, they need not
# exist before a render.
GENERATED = ('pal', 'pre', 'actor', 'intent')
USED_OPS = re.compile(r'[a-z_]+(?::[a-z_]+)?(?:,[a-z_]+(?::[a-z_]+)?)*\Z')
JUDGE_KINDS = re.compile(r'[a-z_]+(?:,[a-z_]+)*\Z')
LIBRARY_EXTRAS = ('index.json', 'README.md', '.DS_Store')
# Words that never make a piece relevant: function words and generic request filler.
STOPWORDS = frozenset((
    'a', 'about', 'above', 'across', 'after', 'again', 'against', 'all', 'also', 'am', 'an', 'and',
    'any', 'are', 'around', 'as', 'at', 'away', 'back', 'be', 'been', 'before', 'behind', 'being',
    'below', 'beneath', 'between', 'both', 'but', 'by', 'can', 'could', 'did', 'do', 'does',
    'doing', 'down', 'during', 'each', 'every', 'few', 'for', 'from', 'further', 'get', 'gets',
    'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'him', 'his', 'how', 'i', 'if',
    'in', 'inside', 'into', 'is', 'it', 'its', 'itself', 'just', 'like', 'me', 'more', 'most', 'my',
    'near', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'one', 'only', 'onto', 'or',
    'other', 'our', 'out', 'outside', 'over', 'own', 'please', 'same', 'she', 'should', 'so',
    'some', 'such', 'than', 'that', 'the', 'their', 'them', 'then', 'there', 'these', 'they',
    'this', 'those', 'through', 'to', 'too', 'two', 'under', 'until', 'up', 'upon', 'very', 'via',
    'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'why', 'will', 'with',
    'within', 'without', 'would', 'you', 'your', 'art', 'artwork', 'big', 'create', 'draw',
    'drawing', 'generate', 'give', 'huge', 'image', 'large', 'little', 'make', 'new', 'nice', 'old',
    'original', 'picture', 'piece', 'pixel', 'pixelart', 'pixelate', 'render', 'scene', 'show',
    'small', 'style', 'tiny', 'want'))
# Words that name an asset deliverable rather than what it shows ("a sprite sheet of a spaceship"). Some pieces
# list them as subject tags, so they add score to a piece another subject word matched, but never make one.
FORMAT_WORDS = frozenset(('asset', 'icon', 'sheet', 'sprite', 'spritesheet', 'tile', 'tileset'))


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


def asset(root, value, where):
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
    if not (path.is_file() and stat.S_ISREG(path.stat().st_mode)):
        fail(where, f'wrong file type: {value}')
    return path


def generated(root, value, where):
    """A path a run command may write: safe and inside the piece, never a link, but not required yet.
    Whatever part exists is checked: a link, a file used as a folder or an existing target that is not a
    regular file fails. Validation never infers that a declared output was rendered."""
    relative(value, where)
    path = root
    for component in value.split('/'):
        path = path / component
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return root / value
        except OSError as exc:
            fail(where, f'unsafe path {value}: {exc}')
        if stat.S_ISLNK(mode):
            fail(where, f'symlink: {value}')
    if not path.is_file():
        fail(where, f'wrong file type: {value}')
    return path


def image_output(root, output):
    """Check one image entry against the `tools/render.py` image contract, plus a required run."""
    fields(output, ('name', 'kind', 'run', 'frame'), ('scale', 'size', 'golden', *IMAGE_GATE), 'output')
    gate = {key: output[key] for key in IMAGE_GATE if key in output}
    for key, value in gate.items():
        if not isinstance(value, str):
            fail(f'output.{key}', 'expected string (empty means unset)')
    gate = {key: value for key, value in gate.items() if value}
    if not ('style' in gate or 'era' in gate):
        fail('output', 'image needs style or era for the gate')
    if 'style' in gate:
        choice(gate['style'], STYLES[:-1], 'output.style')
    if 'era' in gate:
        choice(gate['era'], ERAS[:-1], 'output.era')
    if 'scene' in gate:
        # styles is a trusted, pure-Python kit table; its scene variants are the gate's --scene values.
        if __package__:
            from . import styles
        else:
            import styles
        if 'style' not in gate or gate['scene'] not in styles.STYLES[gate['style']].get('scenes', {}):
            fail('output.scene', 'expected a scene variant of the output style')
    if 'scale' in output:
        positive(output['scale'], 'output.scale')
    if 'size' in output:
        fields(output['size'], ('w', 'h'), where='output.size')
        for key, value in output['size'].items():
            positive(value, f'output.size.{key}')
    generated(root, output['frame'], 'output.frame')
    if 'golden' in output:
        if output['golden'] != f"out/golden/{output['name']}.png" or output['golden'] == output['frame']:
            fail('output.golden', 'expected out/golden/<output name>.png, distinct from frame')
        asset(root, output['golden'], 'output.golden')
    if 'brief' in gate:
        asset(root, gate['brief'], 'output.brief')
    for key in GENERATED:
        if key in gate:
            generated(root, gate[key], f'output.{key}')
    if 'used' in gate and not USED_OPS.fullmatch(gate['used']):
        fail('output.used', 'expected comma-separated post ops')
    if 'judge_ignore' in gate and not JUDGE_KINDS.fullmatch(gate['judge_ignore']):
        fail('output.judge_ignore', 'expected comma-separated judge defect kinds')


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
    for output in manifest['outputs']:
        if output['kind'] == 'image' and manifest['review']['record'] == output['frame'] + '.visual-review.json':
            if not output.get('brief'):
                fail(root, 'reviewed image output needs its brief')
            # Relocation-safe: only paths recorded inside this same piece are reanchored here.
            ready, reason = review_status.piece_status(root, output['brief'], output['frame'])
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
    except RecursionError:
        fail(path, 'invalid JSON: nested too deeply')
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
        choice(output.get('kind'), ('image', 'audio', 'export'), 'output.kind')
        if output['kind'] == 'image':
            image_output(root, output)
        else:
            fields(output, ('name', 'kind', 'run', 'file'), where='output')
            generated(root, output['file'], 'output.file')
        slug(output['name'], 'output.name')
        if output['name'] in seen:
            fail('outputs', 'duplicate name')
        seen.add(output['name'])
        text(output['run'], 'output.run')
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
        recipes = manifest['recipes']
        if (not isinstance(recipes, list) or not all(isinstance(r, str) and RECIPE.fullmatch(r) for r in recipes) or
                len(recipes) != len(set(recipes))):
            fail('recipes', 'expected distinct recipe function names')
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
        if path.name in LIBRARY_EXTRAS and not path.is_symlink() and path.is_file():
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
    """Generate stable catalog bytes; callers may write these to index.json. Paths are relative to the
    library root; `media` lists the manifest's declared media files."""
    return (json.dumps({'schema': 1, 'pieces': [{'id': p['id'], 'title': p['title'], 'status': p['status'],
                  'mode': p['mode'], 'summary': p['summary'], 'tags': p['tags'], 'path': f"{p['id']}/piece.json",
                  'media': {key: f"{p['id']}/{value}" for key, value in p.get('media', {}).items() if value}}
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


def terms(value):
    """Content words of free text, singularized; stopwords and single letters never count."""
    found = set()
    for word in TOKEN.findall(value.lower()):
        if len(word) > 4 and word.endswith('ies'):
            word = word[:-3] + 'y'
        elif len(word) > 3 and word.endswith('s') and not word.endswith(('ss', 'us', 'is')):
            word = word[:-1]
        if len(word) > 1 and word not in STOPWORDS:
            found.add(word)
    return found


def query_tags(request, mode=None):
    """Conservative router-style explicit signals; generic phrases never fabricate a match."""
    text(request, 'request')
    lower = request.lower()
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
            'era': explicit({e: (e.replace('-', ' '), e) + (('game boy',) if e == 'gameboy' else ()) for e in ERAS[:-1]}),
            'motion': explicit({'loop': ('loop', 'looping'), 'stills': ('still', 'stills'),
                                'sprite-sheet': ('sprite sheet', 'spritesheet')}),
            'words': terms(request)}


def find(library, request, mode=None, limit=3):
    """Return matched pieces and a fallback plan.

    Only a subject-tag word that is not an asset format word (FORMAT_WORDS) makes a piece relevant.
    Setting tags (`day`, `outdoor`), format words and words of the title, summary and request add score
    to a relevant piece but cannot make one; status only orders relevant pieces. Otherwise find abstains and returns the starter or author plan.
    A starter is offered only when it meets every explicit camera, style, era and motion of the request, as a finished piece must.
    """
    query = query_tags(request, mode)
    if type(limit) is not int or limit < 1:
        fail('limit', 'expected positive integer')
    words = query['words']
    ranked, starters = [], []
    for piece in scan(library).values():
        if piece['mode'] != query['mode']:
            continue
        tags = piece['tags']
        matched = [key for key in ('camera', 'style', 'era', 'motion') if query[key] and tags[key] == query[key]]
        if any(query[key] and tags[key] != query[key] for key in ('camera', 'style', 'era', 'motion')):
            continue
        if piece['status'] == 'starter':
            starters.append(piece['id'])
            continue
        subject = words & terms(' '.join(tags['subject']))
        if not subject - FORMAT_WORDS:
            continue
        setting = words & terms(' '.join(tags['setting'])) - subject
        described = words & terms(' '.join((piece['title'], piece['summary'], piece['request']))) - subject - setting
        tag_words = terms(' '.join(query[key] for key in matched))
        score = (5 * len(subject) + 2 * len(setting) + len(described) + 4 * sum(k in matched for k in ('camera', 'era')) +
                 3 * sum(k in matched for k in ('style', 'motion')) + {'study': 0, 'accepted': 1, 'reviewed': 2}[piece['status']])
        ranked.append({'id': piece['id'], 'status': piece['status'], 'score': score,
                       'why': matched + [f'{field}: {word}' for field, found in
                                         (('subject', subject), ('setting', setting), ('text', described))
                                         for word in sorted(found)],
                       'differs': [f'unmatched term: {word}' for word in
                                   sorted(words - subject - setting - described - tag_words)]})
    ranked.sort(key=lambda result: (-result['score'], result['id']))
    return {'mode': query['mode'], 'matches': ranked[:limit],
            'fallback': {'kind': 'starter', 'ids': starters} if starters else
                        {'kind': 'author', 'reason': 'no matching starter; author a new piece'}}


def compare_golden(frame, golden, size, scale):
    """Check a rendered frame is `size` at `scale`, then compare its nearest-neighbor 1x RGBA pixels
    with the golden 1x frame. A missing golden (None) fails after the dimension check."""
    import numpy as np
    from PIL import Image
    w, h = size['w'], size['h']
    try:
        with Image.open(frame) as image:
            rendered = image.convert('RGBA')
    except OSError as exc:
        return {'ok': False, 'error': f'unreadable frame: {exc}'}
    if rendered.size != (w * scale, h * scale):
        return {'ok': False, 'error': f'dimension mismatch: frame {rendered.width}x{rendered.height}, '
                                      f'expected {w * scale}x{h * scale} ({w}x{h} at scale {scale})'}
    if golden is None:
        return {'ok': False, 'error': 'missing golden: declare out/golden/<output name>.png'}
    try:
        with Image.open(golden) as image:
            expected = image.convert('RGBA')
    except OSError as exc:
        return {'ok': False, 'error': f'unreadable golden: {exc}'}
    if expected.size != (w, h):
        return {'ok': False, 'error': f'golden is {expected.width}x{expected.height}, expected 1x {w}x{h}'}
    delta = np.abs(np.asarray(rendered.resize((w, h), Image.Resampling.NEAREST), np.int16) -
                   np.asarray(expected, np.int16)).max(axis=2)
    ys, xs = np.nonzero(delta)
    if not len(xs):
        return {'ok': True, 'pixels': 0}
    return {'ok': False, 'pixels': int(len(xs)), 'max_delta': int(delta.max()),
            'box': [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
            'error': f'{len(xs)} of {w * h} 1x pixels differ from the golden'}


def kit_render():
    # render is a trusted kit tool; importing it runs no piece code.
    if __package__:
        from . import render
    else:
        import render
    return render


def check_output(source, work, temp, output, canvas, status, result):
    """Verify one output the group's run just wrote; records into `result`. The output is read once,
    without following a link; those bytes are hashed, compared with the golden and, in a private
    snapshot with the generated gate inputs from `work` and the brief from `source`, gated. A gate
    failure blocks every status but `study`, where plan section 2.1 asks only for a render; a gate that
    errors blocks every status."""
    render = kit_render()
    path = output.get('frame') or output['file']
    try:
        data = render.read_regular(work, path)
    except FileNotFoundError:
        result.update(status='failed', error=f'not produced: {path}')
        return
    except render.UnsafePath as exc:
        result.update(status='failed', error=f'unsafe output: {exc}')
        return
    result['sha256'] = hashlib.sha256(data).hexdigest()
    if output['kind'] != 'image':
        if data:
            result['status'] = 'passed'
        else:
            result.update(status='failed', error=f'empty file: {path}')
        return
    golden = None
    if 'golden' in output:
        try:
            golden = io.BytesIO(render.read_regular(source, output['golden']))
        except OSError as exc:
            result.update(status='failed', error=f'unreadable golden: {exc}')
            return
    result['golden'] = compare_golden(io.BytesIO(data), golden, output.get('size') or canvas, output.get('scale', 1))
    folder = Path(tempfile.mkdtemp(prefix=f"gate-{output['name']}-", dir=temp))
    error = render.gate_snapshot(folder, output, data, work, source)
    if error:
        result.update(status='failed', error=error)
        return
    gate = render.technical_gate(folder, output)
    result['gate'] = gate['gate']
    if 'era' in gate:
        # `pixelate era` prints violations yet exits 0, so its status says only that it ran; the gate's
        # own --era lines decide era legality.
        result['era'] = {'ran': gate['era']['ok'], 'report': gate['era']['report']}
    era_ran = result.get('era', {'ran': True})['ran']
    result['gate_ok'] = result['gate']['ok'] and era_ran
    errored = 'error' in result['gate'] or not era_ran
    if result['gate_ok'] or (status == 'study' and not errored):
        result['status'] = 'passed' if result['golden']['ok'] else 'failed'
        if not result['gate_ok']:
            result['diagnostic'] = 'study: the technical gate failed; reported, not blocking'
    else:
        result['status'] = 'failed'


def test_piece(root, quick=False, timeout=300):
    """Render a temporary copy of a trusted piece; gate every image and compare it with its golden 1x frame.

    Outputs with the same run command form a group, run once, for at most `timeout` seconds, in order
    of first appearance. Before a group runs, its declared frames and files are deleted from the copy,
    so neither a stale committed file nor another command's side effect can pass; each is checked
    right after its group runs. Outputs are read without following links. Quick mode tests one kind:
    the images when the piece has any, else its exports, else the audio outputs of the first audio command;
    every other output is reported as skipped. A piece is `ok` only if nothing failed and at least one
    output passed, so a piece whose outputs were all skipped never reads as green. `gate_ok` is null when
    the piece has no image to gate. The source piece is never written.
    """
    render = kit_render()
    source = Path(root).absolute()
    manifest = validate(source)
    results, groups = {}, {}
    declared = {output['kind'] for output in manifest['outputs']}
    quick_kind = next(kind for kind in ('image', 'export', 'audio') if kind in declared)
    quick_audio = next((o['run'] for o in manifest['outputs'] if o['kind'] == 'audio'), None)
    for output in manifest['outputs']:
        path = output.get('frame') or output['file']
        results[output['name']] = {'name': output['name'], 'kind': output['kind'], 'path': path}
        if quick and output['kind'] != quick_kind:
            results[output['name']].update(status='skipped', reason=f"quick mode skips {output['kind']} outputs")
        elif quick and quick_kind == 'audio' and output['run'] != quick_audio:
            results[output['name']].update(status='skipped', reason='quick mode runs only the first audio command')
        else:
            groups.setdefault(output['run'], []).append(output)
    with tempfile.TemporaryDirectory(prefix='pixelate-test-') as temp:
        work = Path(temp) / source.name
        shutil.copytree(source, work, symlinks=True, ignore=shutil.ignore_patterns('.pixelate', '__pycache__'))
        env = render.piece_env()
        for command, group in groups.items():
            try:
                for output in group:
                    render.remove_regular(work, output.get('frame') or output['file'])
            except render.UnsafePath as exc:
                for output in group:
                    results[output['name']].update(status='failed', error=f'unsafe output: {exc}')
                continue
            run = render.run_command(command, work, env, timeout)
            for output in group:
                result = results[output['name']]
                result['run'] = run
                if run['ok']:
                    check_output(source, work, temp, output, manifest['canvas'], manifest['status'], result)
                else:
                    result.update(status='failed', error='run failed')
    outputs = list(results.values())
    kinds = {}
    for result in outputs:
        result['tested'] = result['status'] != 'skipped'
        count = kinds.setdefault(result['kind'], {'declared': 0, 'tested': 0})
        count['declared'] += 1
        count['tested'] += result['tested']
    images = [r for r in outputs if r['kind'] == 'image']
    return {'id': manifest['id'],
            'ok': all(r['status'] != 'failed' for r in outputs) and any(r['status'] == 'passed' for r in outputs),
            'gate_ok': all(r.get('gate_ok') is True for r in images) if images else None,
            'kinds': kinds, 'outputs': outputs}


def test(library, ids=(), quick=False, timeout=300):
    """Render-test the named pieces, or every piece in the catalog, in temporary copies."""
    library = Path(library).absolute()
    positive(timeout, 'timeout')
    if ids:
        for piece_id in ids:
            slug(piece_id, 'id')
            if not (library / piece_id).is_dir():
                fail(piece_id, 'unknown piece')
        ids = list(dict.fromkeys(ids))
    else:
        ids = list(scan(library))
    if not ids:
        fail(library, 'no pieces to test')
    pieces = [test_piece(library / piece_id, quick, timeout) for piece_id in ids]
    gated = [p['gate_ok'] for p in pieces if p['gate_ok'] is not None]
    return {'ok': all(p['ok'] for p in pieces), 'gate_ok': all(gated) if gated else None, 'quick': quick,
            'pieces': pieces}


DEFAULT_LIBRARY = Path(__file__).resolve().parent.parent / 'library'


def main(argv=None, prog=None):
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument('--library', type=Path, default=DEFAULT_LIBRARY)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('index')
    commands.add_parser('list')
    commands.add_parser('show').add_argument('id')
    finding = commands.add_parser('find')
    finding.add_argument('request')
    finding.add_argument('--mode', choices=MODES)
    testing = commands.add_parser('test', help='render pieces in temporary copies, gate each image and compare '
                                               'golden 1x frames; runs trusted checked-in commands without a sandbox')
    testing.add_argument('ids', nargs='*', metavar='ID')
    testing.add_argument('--quick', action='store_true', help='test one kind per piece: its images, else its exports, else its first audio command')
    testing.add_argument('--timeout', type=int, default=300, help='seconds per run command (default 300)')
    args = parser.parse_args(argv)
    try:
        if args.command == 'test':
            report = test(args.library, args.ids, args.quick, args.timeout)
            print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
            raise SystemExit(0 if report['ok'] else 1)
        result = {'index': lambda: write_index(args.library).decode('utf-8'),
                  'list': lambda: list_pieces(args.library),
                  'show': lambda: show(args.library, args.id),
                  'find': lambda: find(args.library, args.request, args.mode)}[args.command]()
    except LibraryError as exc:
        parser.exit(2, f'library: {exc}\n')
    print(result if isinstance(result, str) else json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


def find_main(argv=None):
    """`pixelate find REQUEST [--mode M] [--json]`: the top pieces and the fallback, as text or JSON."""
    parser = argparse.ArgumentParser(prog='pixelate find', description='Rank library pieces for a request. '
                                     'Static: never runs piece code.')
    parser.add_argument('request')
    parser.add_argument('--mode', choices=MODES)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--library', type=Path, default=DEFAULT_LIBRARY)
    args = parser.parse_args(argv)
    try:
        result = find(args.library, args.request, args.mode)
    except LibraryError as exc:
        parser.exit(2, f'find: {exc}\n')
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return
    print(f"mode: {result['mode']}")
    if not result['matches']:
        print('no close piece')
    for rank, match in enumerate(result['matches'], 1):
        print(f"{rank}. {match['id']} ({match['status']}, score {match['score']})")
        print('   why: ' + ', '.join(match['why']))
        if match['differs']:
            print('   differs: ' + ', '.join(match['differs']))
    fallback = result['fallback']
    print('fallback: ' + (f"starter {', '.join(fallback['ids'])}" if fallback['kind'] == 'starter'
                          else fallback['reason']))


if __name__ == '__main__':
    main()
