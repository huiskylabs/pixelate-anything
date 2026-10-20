#!/usr/bin/env python3
"""Distance of a remix's rendered frames from its base piece, for `pixelate render`.

A piece whose `lineage.remixed_from` names a base is measured, one image output at a time, against
the base output of the same name: the share of 1x pixels that differ from the base's checked-in 1x
golden, and the share of distinct colours the two do not have in common. The frame is the exact
bytes render read once and hashed; nothing is read again from DIR.

The base is looked up only in the kit's checked-in library (`library/<id>`), never in another
folder, and is validated statically: none of its code runs. Its piece.json and goldens are read once,
before the remix's commands run, without following a link. It counts as the remix's base only when
the SHA-256 of its piece.json matches the one `pixelate remix` recorded in .pixelate/remix-baseline.json
and each golden matches the hash of the copy the baseline recorded under `files`. The baseline is not
signed, so this is a consistency check, not proof of origin; the remix's own edited files are not
rehashed. A missing, linked, corrupt or older baseline, a kit piece of the same id that does not match
it, a base that is missing or invalid, an output it does not have, a golden it lacks and a frame that
cannot be read leave the distance unavailable, with the reason; a size change leaves the pixel share
unavailable. None of them reads as 0, and none warns.

When the remix's request differs from the base's and both shares are under UNDER_REMIX, the record
carries an "under-remixed" warning. The thresholds are an uncalibrated heuristic chosen to warn only
on near-copies: not a quality grade, not approval and not a gate, so a warning never fails a render.
"""
import hashlib
import io
import json
import re

import library  # the static manifest checks; tools/ is on the path, as for render.py

DEFAULT_LIBRARY = library.DEFAULT_LIBRARY
BASELINE = '.pixelate/remix-baseline.json'  # remix.BASELINE, written by `pixelate remix`
SHA256 = re.compile('[0-9a-f]{64}')
# Under both shares, with a changed request, a remix is reported as under-remixed. Uncalibrated:
# no labelled set of remixes backs these numbers, so they stay a warning (plan section 7.3).
UNDER_REMIX = {'pixels': 0.02, 'palette': 0.05}
NOTE = ('Uncalibrated heuristic against the base golden: not a quality grade, not approval and not a '
        'gate. Look at the frame to judge whether the request changed it. The base is the kit piece whose '
        'piece.json and golden match the SHA-256 the remix baseline records: a consistency check against an '
        'unsigned local file, not proof of where the remix came from.')


def same_request(a, b):
    return ' '.join(a.lower().split()) == ' '.join(b.lower().split())


def recorded_base(d, manifest, base_id):
    """(the base piece.json SHA-256, copied file hashes, baseline SHA-256) that the remix baseline at d
    records, or raise ValueError with the reason. The file is read without following a link. It is not
    signed: a match with it is a consistency check, not proof of where the piece came from."""
    render = library.kit_render()
    try:
        data = render.read_regular(d, BASELINE)
    except FileNotFoundError:
        raise ValueError(f'no remix baseline {BASELINE}: distance is measured only for a copy `pixelate remix` '
                         'made, against the base identity it recorded') from None
    except OSError as exc:
        raise ValueError(f'unreadable remix baseline {BASELINE}: {exc}') from None
    try:
        baseline = json.loads(data)
    except (ValueError, RecursionError) as exc:
        raise ValueError(f'invalid remix baseline {BASELINE}: {exc}') from None
    if (not isinstance(baseline, dict) or baseline.get('schema') != 1 or baseline.get('type') != 'remix-baseline'
            or not isinstance(baseline.get('base'), dict) or not isinstance(baseline.get('files'), dict)):
        raise ValueError(f'invalid remix baseline {BASELINE}: not a schema 1 remix-baseline with base and files')
    if baseline.get('piece') != manifest.get('id'):
        raise ValueError(f"remix baseline {BASELINE} is of piece {baseline.get('piece')!r}, not {manifest.get('id')!r}")
    if baseline['base'].get('id') != base_id:
        raise ValueError(f"remix baseline {BASELINE} names base {baseline['base'].get('id')!r}, but "
                         f'lineage.remixed_from names {base_id!r}')
    digest = baseline['base'].get('piece_sha256')
    if digest is None:
        raise ValueError(f"remix baseline {BASELINE} records no SHA-256 of the base's piece.json (an older "
                         '`pixelate remix` made it), so the base cannot be identified; remix the base again to '
                         'measure distance')
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError(f'invalid remix baseline {BASELINE}: base.piece_sha256 is not a SHA-256')
    return digest, baseline['files'], hashlib.sha256(data).hexdigest()


def lookup(d, manifest, library_root=None):
    """The base of the piece at d with its validated manifest: None when it is not a remix, else
    {'id', 'library', and 'error' or 'status', 'request', 'piece_sha256', 'images'}, where images maps
    each base image output name to {'golden', 'sha256', 'data'} or {'error'}. The base is the kit piece
    only when its piece.json and each golden hash as the remix baseline recorded. Static: runs no piece code."""
    base_id = (manifest.get('lineage') or {}).get('remixed_from')
    if not base_id:
        return None
    root = (DEFAULT_LIBRARY if library_root is None else library_root).absolute()
    base = {'id': base_id, 'library': str(root)}
    try:
        digest, files, baseline_hash = recorded_base(d, manifest, base_id)
    except ValueError as exc:
        return dict(base, error=str(exc))
    base['baseline_sha256'] = baseline_hash
    source = root / base_id
    if root.is_symlink() or not root.is_dir():
        return dict(base, error=f'the kit library {root} is missing or a link')
    if not source.is_dir() and not source.is_symlink():
        return dict(base, error=f'base {base_id} is not in the kit library {root}; distance is measured only '
                                'against checked-in kit pieces')
    if source.resolve() == d.resolve():
        return dict(base, error='the base is this piece itself')
    render = library.kit_render()
    try:
        found = library.validate(source)  # rejects a link anywhere in the base; runs nothing
        piece_json = render.read_regular(source, 'piece.json')
        if json.loads(piece_json) != found:
            raise library.LibraryError(f'{source}/piece.json changed while it was read')
    except (library.LibraryError, OSError, ValueError) as exc:
        return dict(base, error=f'base {base_id} is not a valid library piece: {exc}')
    if hashlib.sha256(piece_json).hexdigest() != digest:
        return dict(base, error=f'base {base_id} in the kit library is not the base this remix recorded: its '
                                f'piece.json SHA-256 {hashlib.sha256(piece_json).hexdigest()} differs from {digest} '
                                f'in {BASELINE} (remixed from another library, or the kit piece changed since)')
    images = {}
    for output in found['outputs']:
        if output['kind'] != 'image':
            continue
        if 'golden' not in output:
            images[output['name']] = {'error': f"base output {output['name']} declares no golden"}
            continue
        try:
            data = render.read_regular(source, output['golden'])
        except OSError as exc:
            images[output['name']] = {'error': f"base golden {output['golden']} unreadable: {exc}"}
            continue
        golden = hashlib.sha256(data).hexdigest()
        if output['golden'] not in files:
            images[output['name']] = {'error': f"{BASELINE} records no copied {output['golden']}"}
            continue
        if files[output['golden']] != golden:
            images[output['name']] = {'error': (
                f"base golden {output['golden']} is not the one this remix copied: SHA-256 {golden} in the kit "
                f"library, {files[output['golden']]} in {BASELINE} (the kit golden changed since the remix, or "
                'the remix was made from another library)')}
            continue
        images[output['name']] = {'golden': output['golden'], 'sha256': golden, 'data': data}
    return dict(base, status=found['status'], request=found['request'], piece_sha256=digest, images=images)


def unavailable(base, name, reason):
    """The distance record of output name when nothing could be measured"""
    rec = {'base': None if base is None else {'id': base['id'], 'library': base['library'], 'output': name},
           'baseline_sha256': None if base is None else base.get('baseline_sha256'),
           'pixels': None, 'palette': None, 'request_differs': None, 'under_remixed': None, 'warning': None,
           'reason': reason}
    if base is not None and 'status' in base:
        rec['base'].update(status=base['status'], piece_sha256=base['piece_sha256'])
    return rec


def _rgba(data):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        return image.convert('RGBA')


def _colours(pixels):
    """the distinct RGBA values of an (h, w, 4) uint8 array as packed integers; every fully
    transparent pixel counts as one colour, whatever its RGB"""
    import numpy as np
    packed = pixels.astype(np.uint32)
    packed = (packed[..., 0] << 24) | (packed[..., 1] << 16) | (packed[..., 2] << 8) | packed[..., 3]
    return set(np.unique(np.where(pixels[..., 3] == 0, 0, packed)).tolist())


def measure(data, output, canvas, request, base):
    """The distance record of image output from the frame bytes data, the bytes render hashed. canvas:
    the piece canvas (the 1x size unless output declares size); request: the piece's request; base:
    what lookup returned for it, not None"""
    import numpy as np
    from PIL import Image
    name = output['name']
    if 'error' in base:
        return unavailable(base, name, base['error'])
    golden = base['images'].get(name)
    if golden is None:
        return unavailable(base, name, f"base {base['id']} has no image output named {name}")
    if 'error' in golden:
        return unavailable(base, name, golden['error'])
    rec = unavailable(base, name, None)
    rec['base'].update(golden=golden['golden'], golden_sha256=golden['sha256'])
    rec['request_differs'] = not same_request(request, base['request'])
    size, scale = output.get('size') or canvas, output.get('scale', 1)
    w, h = size['w'], size['h']
    try:
        frame = _rgba(data)
    except Exception as exc:  # any decoder failure, including Pillow's decompression-bomb guard
        return dict(rec, reason=f'unreadable frame: {exc}')
    if frame.size != (w * scale, h * scale):
        return dict(rec, reason=f'frame is {frame.width}x{frame.height}, expected {w * scale}x{h * scale} '
                                f'({w}x{h} at scale {scale})')
    try:
        expected = np.asarray(_rgba(golden['data']), np.uint8)
    except Exception as exc:
        return dict(rec, reason=f"unreadable base golden {golden['golden']}: {exc}")
    small = np.asarray(frame.resize((w, h), Image.Resampling.NEAREST), np.uint8)
    mine, theirs = _colours(small), _colours(expected)
    palette = 1 - len(mine & theirs) / len(mine | theirs)
    rec['palette'] = {'colours': len(mine), 'base_colours': len(theirs), 'shared': len(mine & theirs),
                      'share': round(palette, 4)}
    if small.shape != expected.shape:
        rec['reason'] = (f'size changed: the base golden is {expected.shape[1]}x{expected.shape[0]} at 1x, this '
                         f'output {w}x{h}; pixels are not compared')
    else:
        clear = expected[..., 3] == 0
        differ = (np.any(small != expected, axis=2) & ~(clear & (small[..., 3] == 0)))
        pixels = int(differ.sum()) / (w * h)
        rec['pixels'] = {'differ': int(differ.sum()), 'total': w * h, 'share': round(pixels, 4)}
        rec['under_remixed'] = (rec['request_differs'] and pixels < UNDER_REMIX['pixels']
                                and palette < UNDER_REMIX['palette'])
        if rec['under_remixed']:
            rec['warning'] = (f"under-remixed: the request differs from the request of base {base['id']}, but "
                              f"{rec['pixels']['differ']} of {rec['pixels']['total']} 1x pixels and "
                              f"{rec['palette']['share']:.1%} of colours differ from its golden (heuristic: under "
                              f"{UNDER_REMIX['pixels']:.0%} and {UNDER_REMIX['palette']:.0%}); check that what the "
                              'request asks for is drawn')
    rec.update(thresholds=dict(UNDER_REMIX), note=NOTE)
    return rec


def line(rec):
    """the compact text of a distance record for render's line; '' for a piece that is not a remix"""
    if rec['base'] is None:
        return ''
    where = f"distance from {rec['base']['id']}/{rec['base']['output']}"
    if rec['pixels'] is None and rec['palette'] is None:
        return f"{where} unavailable: {rec['reason']}"
    pixels = (f"pixels unavailable ({rec['reason']})" if rec['pixels'] is None else
              f"{rec['pixels']['share']:.1%} of 1x pixels differ ({rec['pixels']['differ']} of {rec['pixels']['total']})")
    text = f"{where}: {pixels}, {rec['palette']['share']:.1%} of colours"
    return text + (f" | WARNING {rec['warning']}" if rec['warning'] else '')
