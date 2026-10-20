#!/usr/bin/env python3
"""pixelate deliver DIR [--set KNOB=VALUE ...] [--timeout S] [--json]
pixelate deliver DIR --verify [--json]

Final render, checks and package of a piece folder (DIR/piece.json; see references/piece.md).
Delivery runs `pixelate render DIR --json` once for every declared output, images, audio and exports
alike, killed with its process group after --timeout seconds (default 900). Render deletes each
declared frame and file before its command runs, so a stale output cannot pass. Delivery then requires:
every command ran; every image passed the technical gate, era images included (era legality is the
gate's own --era lines); every frame on disk, and its kept snapshot when logging is on, holds the
exact bytes render hashed, gated and judged; every audio and export file is a nonempty regular file
with the bytes render hashed; no output is reached through a link; and piece.json and the files it
references did not change while the piece rendered. A study's gate failure blocks delivery, though
`library test --quick` only reports it. A review record beside a frame (FRAME.visual-review.json)
is checked with review_status: a record that does not bind the delivered bytes blocks delivery, and
status `reviewed` needs a matching A. No critique is run and no paid reviewer is called.

On success the outputs are copied into DIR/dist/delivery/ with DELIVERY.md, whose facts block is
written by this script: the output paths and SHA-256 hashes, the gate, judge and review evidence each
on its own, the request and lineage, the kit version, the knob values render recorded (or the declared
defaults), what was not tested, and that approval and rights are not verified. The block ends with
the SHA-256 fingerprint of its canonical JSON. Notes outside the block are yours: delivering again
keeps them. An existing DIR/dist/delivery is replaced only when it is a package deliver wrote whose
facts still verify and that holds no other file; otherwise nothing is replaced. One `type: deliver`
record, with the hashes, is appended to DIR/.pixelate/runs.jsonl after render's own record
(PIXELATE_NO_LOG=1 turns both off). A failed delivery writes no package.

--verify runs no piece code and starts no process. It checks that the facts block is exactly what
the script writes for its JSON, that the fingerprint matches, that the package holds exactly the
listed files with those hashes, and that the piece still validates and its piece.json, referenced
sources, outputs and review records hold the delivered bytes. Every path is read without following
a link.

A gate pass is a technical check, not art quality. Judge findings are heuristic and never block. A
declared approval (`review.approved_by`) is reported as unverified, never as approval; rights to
sources and the license are not verified. Deliver runs the piece's commands through the shell
without a sandbox: deliver only trusted pieces.

Exit status: 0 delivered (or verified); 1 delivery or verification failed; 2 an invalid piece, a
legacy render.json, or a --set render refused.
"""
import argparse, contextlib, datetime, hashlib, importlib, json, os, re, shutil, signal, stat, subprocess, sys
from pathlib import Path

if __package__:
    from . import render, review_status
    from .version import VERSION
else:
    import render, review_status
    from version import VERSION
# By name: `library` is both tools/library.py and the kit's library/ folder of pieces.
library = importlib.import_module(f'{__package__}.library' if __package__ else 'library')

SCHEMA = 1
PACKAGE = 'dist/delivery'
DELIVERY = 'DELIVERY.md'
BEGIN = '<!-- pixelate deliver: facts begin. Written by the script; `pixelate deliver DIR --verify` checks this block. -->'
END = '<!-- pixelate deliver: facts end -->'
FINGERPRINT = re.compile(r'^Fingerprint: sha256:([0-9a-f]{64})$', re.M)
MAX_DELIVERY = 1024 * 1024
MAX_REPORT = 16 * 1024 * 1024
MAX_SIDECAR = review_status.MAX_MANIFEST
DEFAULT_TIMEOUT = 900
SIDECAR = '.visual-review.json'


class DeliveryError(ValueError):
    """the piece cannot be delivered, or a delivery does not verify"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(facts):
    return json.dumps(facts, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def fingerprint(facts):
    return sha(canonical(facts))


def strict_json(text, where):
    """JSON with unique keys and finite numbers, or DeliveryError"""
    def constant(value):
        raise DeliveryError(f'{where}: nonfinite JSON number {value}')
    try:
        return json.loads(text, object_pairs_hook=library.unique_pairs, parse_constant=constant)
    except library.LibraryError as exc:
        raise DeliveryError(f'{where}: {exc}') from None
    except RecursionError:
        raise DeliveryError(f'{where}: JSON nested too deeply') from None
    except ValueError as exc:
        raise DeliveryError(f'{where}: invalid JSON: {exc}') from None


def read_limited(root, rel, limit):
    """the bytes of the regular file rel under root, at most limit, read without following any link"""
    fd, name = render._parent(root, rel)
    try:
        try:
            f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise render.UnsafePath(f'{rel}: a link or not a regular file ({exc.strerror})') from exc
    finally:
        os.close(fd)
    with os.fdopen(f, 'rb') as fh:
        info = os.fstat(fh.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise render.UnsafePath(f'{rel}: not a regular file')
        if info.st_size > limit:
            raise DeliveryError(f'{rel}: larger than {limit} bytes')
        data = fh.read(limit + 1)
    if len(data) > limit:
        raise DeliveryError(f'{rel}: larger than {limit} bytes')
    return data


def hash_regular(root, rel):
    """(sha256, size) of the regular file rel under root, streamed, without following any link"""
    fd, name = render._parent(root, rel)
    try:
        try:
            f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise render.UnsafePath(f'{rel}: a link or not a regular file ({exc.strerror})') from exc
    finally:
        os.close(fd)
    digest, size = hashlib.sha256(), 0
    with os.fdopen(f, 'rb') as fh:
        if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
            raise render.UnsafePath(f'{rel}: not a regular file')
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def output_path(output):
    return output.get('frame') or output['file']


def source_paths(manifest):
    """piece.json and the checked-in files it references: anatomy files, knob edits, image briefs and
    goldens, media and review files. Not every file a program imports."""
    paths = {'piece.json'}
    paths.update(entry['file'] for entry in manifest['anatomy'])
    paths.update(knob['edits'] for knob in manifest['knobs'].values())
    for output in manifest['outputs']:
        paths.update(output[key] for key in ('brief', 'golden') if output.get(key))
    paths.update(value for value in (manifest.get('media') or {}).values() if value)
    paths.update(value for key, value in (manifest.get('review') or {}).items() if key != 'approved_by' and value)
    return sorted(paths)


def source_hashes(d, manifest):
    hashes = {}
    for rel in source_paths(manifest):
        try:
            hashes[rel] = hash_regular(d, rel)[0]
        except (OSError, DeliveryError) as exc:
            raise DeliveryError(f'source {rel}: {exc}') from None
    return hashes


def check_declared(manifest):
    """refuse outputs that would collide with the package"""
    for output in manifest['outputs']:
        path = output_path(output)
        if path == PACKAGE or path.startswith(PACKAGE + '/') or path == DELIVERY:
            raise DeliveryError(f'output {output["name"]}: {path} collides with the delivery package {PACKAGE}/')


def load_piece(d):
    """the validated manifest of the piece folder d (never a legacy render.json)"""
    if d.is_symlink() or not d.is_dir():
        raise DeliveryError(f'{d}: not a folder (or a link)')
    if (d / 'render.json').exists() or (d / 'render.json').is_symlink():
        raise DeliveryError(f'{d}: deliver needs piece.json; a legacy render.json is not delivered')
    try:
        manifest = library.validate(d)
    except library.LibraryError as exc:
        raise DeliveryError(f'piece.json: {exc}') from None
    check_declared(manifest)
    return manifest


# ---------------------------------------------------------------- render

def run_render(d, sets, timeout):
    """(exit code or None on timeout, stdout bytes, stderr text) of `pixelate render DIR --json`,
    killed with its process group after timeout seconds"""
    command = render.PIXELATE + ['render', str(d), '--json']
    for item in sets:
        command += ['--set', item]
    proc = subprocess.Popen(command, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
        return None, out, err.decode('utf-8', 'replace')
    return proc.returncode, out, err.decode('utf-8', 'replace')


def tail(text, n=6):
    return '\n'.join([line for line in text.strip().splitlines() if line.strip()][-n:])


def parse_report(out):
    if len(out) > MAX_REPORT:
        raise DeliveryError('render report larger than %d bytes' % MAX_REPORT)
    try:
        text = out.decode('utf-8')
    except UnicodeDecodeError:
        raise DeliveryError('render report is not UTF-8') from None
    recs = strict_json(text, 'render report')
    if not isinstance(recs, list) or not all(isinstance(r, dict) for r in recs):
        raise DeliveryError('render report: expected a list of records')
    return recs


def image_failure(rec, status):
    """why an image record does not pass delivery, or None"""
    run = rec.get('run')
    if not isinstance(run, dict) or run.get('ok') is not True:
        return 'command failed: %s' % (run or {}).get('error', 'not run')
    if rec.get('error'):
        return str(rec['error'])
    gate = rec.get('gate')
    if not isinstance(gate, dict):
        return 'not gated'
    if gate.get('error'):
        return 'gate error: %s' % gate['error']
    if gate.get('ok') is not True:
        fails = '; '.join(' '.join(str(line).split()) for line in gate.get('fail', [])[:4])
        return 'gate FAIL: %s%s' % (fails, ' (a study blocks delivery until its gate passes)' if status == 'study' else '')
    if 'era' in rec and (not isinstance(rec['era'], dict) or rec['era'].get('ok') is not True):
        return 'era check did not run'
    return None


def judge_facts(rec):
    jd = rec.get('judge')
    if not isinstance(jd, dict) or 'defects' not in jd:
        return {'ran': False, 'error': str((jd or {}).get('error', 'not run'))}
    counts = {}
    for defect in jd['defects']:
        counts[str(defect.get('kind'))] = counts.get(str(defect.get('kind')), 0) + 1
    return {'ran': True, 'defects': dict(sorted(counts.items()))}


def review_facts(d, manifest, output, digest):
    """(facts, blocking error or None) for the review record beside an image's frame"""
    sidecar = output['frame'] + SIDECAR
    try:
        raw = read_limited(d, sidecar, MAX_SIDECAR)
    except FileNotFoundError:
        if manifest['status'] == 'reviewed' and manifest['review']['record'] == sidecar:
            return {'status': 'NOT REVIEWED'}, f'status reviewed but {sidecar} is missing'
        return {'status': 'NOT REVIEWED'}, None
    except (OSError, DeliveryError) as exc:
        return {'status': 'unsafe record', 'record': sidecar}, f'review record {sidecar}: {exc}'
    facts = {'record': sidecar, 'record_sha256': sha(raw)}
    if not output.get('brief'):
        return dict(facts, status='not verified'), f'review record {sidecar}: the image declares no brief to bind'
    ready, reason = review_status.piece_status(d, output['brief'], output['frame'])
    try:
        recorded = strict_json(raw.decode('utf-8'), sidecar)
    except (DeliveryError, UnicodeDecodeError):
        recorded = {}
    bound = isinstance(recorded, dict) and recorded.get('frame_sha256') == digest
    if reason.startswith('NOT READY') or not bound:
        return dict(facts, status='does not bind', reason=reason), \
            f'review record {sidecar} does not bind the delivered bytes: {reason}'
    facts.update(grade=recorded.get('grade'), reason=reason, status='A, bound' if ready else 'below A, bound')
    if manifest['status'] == 'reviewed' and manifest['review']['record'] == sidecar and not ready:
        return facts, f'status reviewed needs a matching A: {reason}'
    return facts, None


def gate_inputs(d, output):
    found = {}
    for key in ('pal', 'pre', 'actor', 'intent'):
        if output.get(key):
            try:
                found[key] = {'path': output[key], 'sha256': hash_regular(d, output[key])[0]}
            except FileNotFoundError:
                found[key] = {'path': output[key], 'sha256': None}
            except OSError as exc:
                raise DeliveryError(f'gate input {output[key]}: {exc}') from None
    return found


def knob_facts(manifest, recs, sets):
    reported = [r.get('knobs') for r in recs]
    if not sets:
        if any(k is not None for k in reported):
            raise DeliveryError('render recorded knobs that deliver did not set')
        return {'basis': 'declared defaults', 'defaults': {name: knob['default'] for name, knob in manifest['knobs'].items()},
                'note': 'No --set: render removed PIXELATE_KNOBS, so the commands were given no values; that the '
                        'program drew these declared defaults is not proven'}
    first = reported[0]
    if (not isinstance(first, dict) or any(k != first for k in reported) or
            set(first) != {'set', 'merged', 'sha256'} or not isinstance(first['set'], dict)):
        raise DeliveryError('render did not record the knobs it was given for every output')
    if sorted(first['set']) != sorted(item.partition('=')[0] for item in sets):
        raise DeliveryError('render recorded other knobs than --set gave')
    return {'basis': 'set', 'set': first['set'], 'merged': first['merged'], 'file_sha256': first['sha256'],
            'note': 'What render gave the commands in PIXELATE_KNOBS, not proof the program read them'}


def collect(d, manifest, recs, sets):
    """(output facts, {package path: bytes}, errors) from render's records, every output's bytes read
    back without following a link and compared with the hash render gated and judged"""
    errors, facts, artifacts = [], [], {}
    declared = manifest['outputs']
    names = [r.get('name') for r in recs]
    if names != [o['name'] for o in declared]:
        return [], {}, ['render reported outputs %s, the piece declares %s' % (names, [o['name'] for o in declared])]
    for output, rec in zip(declared, recs):
        name, path = output['name'], output_path(output)
        where = rec.get('frame') if output['kind'] == 'image' else rec.get('file')
        if where != path or rec.get('kind') != output['kind']:
            errors.append(f'{name}: render reported {where!r}, the piece declares {path}')
            continue
        digest = rec.get('sha256')
        if output['kind'] == 'image':
            why = image_failure(rec, manifest['status'])
            if why:
                errors.append(f'{name}: {why}')
                continue
        else:
            run = rec.get('run')
            if not isinstance(run, dict) or run.get('ok') is not True:
                errors.append(f"{name}: command failed: {(run or {}).get('error', 'not run')}")
                continue
            if rec.get('error'):
                errors.append(f"{name}: {rec['error']}")
                continue
            if output.get('loop') and not (rec.get('seam') or {}).get('ok'):
                errors.append(f"{name}: loop seam: {(rec.get('seam') or {}).get('message', 'not checked')}")
                continue
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            errors.append(f'{name}: render recorded no hash')
            continue
        try:
            data = render.read_regular(d, path)
        except FileNotFoundError:
            errors.append(f'{name}: {path} is missing after render')
            continue
        except render.UnsafePath as exc:
            errors.append(f'{name}: unsafe output: {exc}')
            continue
        if sha(data) != digest:
            errors.append(f'{name}: {path} changed after render hashed it (sha256 {sha(data)}, render checked {digest})')
            continue
        if not data:
            errors.append(f'{name}: {path} is empty')
            continue
        entry = {'name': name, 'kind': output['kind'], 'path': path, 'sha256': digest, 'bytes': len(data)}
        if output['kind'] == 'image':
            snapshot = rec.get('snapshot')
            if snapshot is not None:
                try:
                    library.relative(snapshot, 'snapshot')
                    if not snapshot.startswith(f'{render.SNAPSHOTS}/{digest}/') or render.read_regular(d, snapshot) != data:
                        raise DeliveryError('does not hold the gated bytes')
                except (library.LibraryError, OSError, DeliveryError) as exc:
                    errors.append(f'{name}: snapshot {snapshot}: {exc}')
                    continue
            gate = rec['gate']
            entry.update(snapshot=snapshot, gate={'ok': True, 'pass': gate.get('pass'), 'fail': list(gate.get('fail', []))},
                         era={'era': output['era'], 'check_ran': True, 'legal': True} if output.get('era') else None,
                         judge=judge_facts(rec))
            try:
                entry['gate_inputs'] = gate_inputs(d, output)
            except DeliveryError as exc:
                errors.append(f'{name}: {exc}')
                continue
            entry['review'], blocking = review_facts(d, manifest, output, digest)
            if blocking:
                errors.append(f'{name}: {blocking}')
                continue
            if not isinstance(rec.get('distance'), dict):
                errors.append(f'{name}: render recorded no distance result for these gated bytes')
                continue
            entry['distance'] = rec['distance']
        else:
            entry['gated'] = False
            if output.get('loop'):
                entry['seam'] = dict(rec['seam'])
        facts.append(entry)
        artifacts[path] = data
    return facts, artifacts, errors


def untested(manifest, outputs):
    kinds = {o['kind'] for o in manifest['outputs']}
    notes = ['determinism: every output was rendered once; deliver does not re-render to compare bytes',
             'golden frames: deliver does not compare outputs with out/golden (`pixelate library test` does)',
             'distance from the base: per-image uncalibrated heuristic when a bound base exists; '
             'null with a reason otherwise, never a quality grade or delivery gate',
             'art quality: a gate pass is a technical check; no independent grade unless an image review is "A, bound"',
             'gate inputs (pal, pre, actor, intent) were hashed after the render, not when the gate read them',
             'sources: hashes cover piece.json and the files it references, not every file a program imports',
             'no sandbox: piece commands ran through the shell with the user\'s permissions']
    if 'audio' in kinds:
        notes.append('audio: hashed and checked nonempty; never gated or listened to, only the loop seam of one '
                     'declared "loop": true is measured')
    if 'export' in kinds:
        notes.append('exports: hashed and checked nonempty; never gated, only the loop seam of one declared '
                     '"loop": true is measured')
    if any(o['kind'] == 'image' and o['judge'].get('ran') is False for o in outputs):
        notes.append('judge: did not run for an image (see its judge entry)')
    return notes


def baseline_hash(d):
    """SHA-256 of the local remix baseline, or None when absent; reject an unsafe file."""
    try:
        return hash_regular(d, '.pixelate/remix-baseline.json')[0]
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise DeliveryError(f'remix baseline: {exc}') from None


def build_facts(d, manifest, outputs, knobs, sources, baseline_sha256):
    review = manifest.get('review') or {}
    images = [o for o in outputs if o['kind'] == 'image']
    reviews = {o['name']: o['review']['status'] for o in images}
    baseline = ({'path': '.pixelate/remix-baseline.json', 'sha256': baseline_sha256}
                if baseline_sha256 is not None else None)
    return {
        'schema': SCHEMA, 'type': 'pixelate-delivery', 'kit': VERSION, 'package': PACKAGE,
        'piece': {'id': manifest['id'], 'title': manifest['title'], 'status': manifest['status'],
                  'mode': manifest['mode'], 'runtime': manifest['runtime'], 'request': manifest['request'],
                  'lineage': manifest.get('lineage') or {'remixed_from': None},
                  'kit_tested': (manifest.get('kit') or {}).get('tested'), 'license_declared': manifest['license'],
                  'provenance': manifest['provenance']},
        'remix_baseline': baseline,
        'knobs': knobs, 'sources': sources, 'outputs': outputs,
        'evidence': {
            'gate': ('passed: every image passed the technical gate (legal, not good)' if images
                     else 'none: no image output to gate'),
            'era': ('passed by the gate\'s --era lines' if any(o['era'] for o in images) else 'no era image'),
            'judge': 'heuristic findings, reported per image; not calibrated and never blocking',
            'critique': ('NOT REVIEWED' if not images or all(s == 'NOT REVIEWED' for s in reviews.values())
                         else 'review records, per image: ' + ', '.join(f'{n} {s}' for n, s in reviews.items())),
            'paid_critique': 'not run by deliver',
            'approval': {'declared_by': review.get('approved_by'), 'notes': review.get('notes'), 'verified': False},
            'rights': 'not verified: the declared license and the rights to any source were not checked'},
        'untested': untested(manifest, outputs),
    }


# ---------------------------------------------------------------- DELIVERY.md

def cell(value):
    return str(value).replace('\n', ' ').replace('|', '\\|')


def summary(facts):
    piece, ev = facts['piece'], facts['evidence']
    lines = ['## Facts', '', f"Written by `pixelate deliver` with kit {facts['kit']}. Edit notes only outside this block.", '',
             f"- Piece: `{piece['id']}`, {cell(piece['title'])}; status `{piece['status']}` as declared; mode `{piece['mode']}`, "
             f"runtime `{piece['runtime']}`; kit tested {cell(piece['kit_tested'] or 'not declared')}.",
             '- Request:']
    lines += ['  > ' + line if line else '  >' for line in piece['request'].splitlines()]
    remixed = piece['lineage'].get('remixed_from')
    lines.append(f'- Lineage: remixed from `{remixed}`.' if remixed else '- Lineage: not a remix.')
    if facts['remix_baseline']:
        lines.append(f"- Remix baseline: `{facts['remix_baseline']['path']}` sha256 `{facts['remix_baseline']['sha256']}`.")
    knobs = facts['knobs']
    shown = knobs['merged'] if knobs['basis'] == 'set' else knobs['defaults']
    lines.append(f"- Knobs ({knobs['basis']}): " + (', '.join(f'{k}={cell(json.dumps(v, ensure_ascii=False))}' for k, v in shown.items())
                                                     or 'none declared') + f". {knobs['note']}.")
    lines += ['', '| Output | Kind | Delivered file | SHA-256 | Gate | Judge | Review |', '|---|---|---|---|---|---|---|']
    for o in facts['outputs']:
        if o['kind'] == 'image':
            gate = f"PASS ({o['gate']['pass']} lines)" + (f", era {o['era']['era']} legal by the gate" if o['era'] else '')
            judge = (', '.join(f'{n} {k}' for k, n in o['judge']['defects'].items()) or 'clean') if o['judge']['ran'] else 'did not run'
            rev = o['review']['status']
        else:
            gate, judge, rev = 'not gated', 'n/a', 'n/a'
        lines.append(f"| {cell(o['name'])} | {o['kind']} | `{cell(facts['package'] + '/' + o['path'])}` | `{o['sha256']}` | "
                     f'{cell(gate)} | {cell(judge)} | {cell(rev)} |')
    for o in facts['outputs']:
        if o['kind'] != 'image':
            continue
        distance = o['distance']
        if distance['base'] is None:
            summary_distance = 'not a remix'
        elif distance['pixels'] is None and distance['palette'] is None:
            summary_distance = f"unavailable ({cell(distance['reason'])})"
        else:
            pixels = (f"{distance['pixels']['share']:.1%} of 1x pixels differ" if distance['pixels'] else
                      f"pixels unavailable ({cell(distance['reason'])})")
            summary_distance = f"{pixels}; {distance['palette']['share']:.1%} of colours differ"
            if distance['warning']:
                summary_distance += '; WARNING under-remixed (uncalibrated, non-blocking)'
        lines.append(f"- Distance for `{cell(o['name'])}`: {summary_distance}.")
    approval = ev['approval']
    lines += ['', 'Evidence, each separate; none proves another:', '',
              f"- Technical gate: {ev['gate']}. Era: {ev['era']}.",
              f"- Judge: {ev['judge']}.",
              f"- Critique: {ev['critique']}. Paid critique: {ev['paid_critique']}. Reviewer independence is not verified.",
              '- Approval: ' + (f"declared by `{approval['declared_by']}`" + (f" in `{approval['notes']}`" if approval['notes'] else '')
                                + ': UNVERIFIED, not treated as approval.' if approval['declared_by']
                                else 'none declared; no user approval is recorded.'),
              f"- Rights: {ev['rights']}; license declared `{facts['piece']['license_declared']}`.",
              '', 'Not tested:', '']
    lines += [f'- {note}' for note in facts['untested']]
    return lines


def facts_block(facts):
    # Rendered from the key-sorted facts, so the block is the same after a round trip through its JSON.
    facts = json.loads(json.dumps(facts, sort_keys=True))
    body = '\n'.join(summary(facts))
    data = json.dumps(facts, indent=2, sort_keys=True, ensure_ascii=False)
    return f'{BEGIN}\n{body}\n\n```json\n{data}\n```\n\nFingerprint: sha256:{fingerprint(facts)}\n{END}'


def default_notes(piece_id):
    before = (f'# Delivery: {piece_id}\n\nNotes: yours to write here or below the facts block. `pixelate deliver` keeps '
              'everything outside the block when it delivers again; `pixelate deliver DIR --verify` checks only the block '
              'and the files it names.\n\n')
    return before, '\n'


def parse_delivery(text):
    """(text before the facts block, facts, text after it); the block must be exactly what facts_block
    writes for its JSON, and its fingerprint must match"""
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise DeliveryError('expected exactly one facts block')
    start = text.index(BEGIN)
    end = text.index(END) + len(END)
    if end < start:
        raise DeliveryError('facts block markers out of order')
    block = text[start:end]
    found = re.search(r'\n```json\n(.*)\n```\n', block, re.S)
    if not found:
        raise DeliveryError('facts block has no JSON')
    facts = strict_json(found.group(1), 'facts')
    if not isinstance(facts, dict) or facts.get('schema') != SCHEMA or facts.get('type') != 'pixelate-delivery':
        raise DeliveryError('facts: unsupported schema')
    stated = FINGERPRINT.findall(block)
    if stated != [fingerprint(facts)]:
        raise DeliveryError('fingerprint does not match the facts')
    try:
        expected = facts_block(facts)
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise DeliveryError(f'facts: malformed ({exc!r})') from None
    if block != expected:
        raise DeliveryError('facts block was edited: it differs from what deliver writes for its facts')
    return text[:start], facts, text[end:]


def read_delivery(d):
    """(before, facts, after) of DIR/dist/delivery/DELIVERY.md, read without following a link"""
    raw = read_limited(d, f'{PACKAGE}/{DELIVERY}', MAX_DELIVERY)
    try:
        return parse_delivery(raw.decode('utf-8'))
    except UnicodeDecodeError:
        raise DeliveryError('DELIVERY.md is not UTF-8') from None


def _raise(exc):
    raise exc


def package_files(d):
    """every file under DIR/dist/delivery as a relative path, refusing a link or a special file"""
    base = d / PACKAGE
    found = []
    for folder, dirs, files in os.walk(base, followlinks=False, onerror=_raise):
        for entry in dirs + files:
            path = Path(folder) / entry
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise DeliveryError(f'link in the package: {path.relative_to(d)}')
            if entry in files:
                if not stat.S_ISREG(mode):
                    raise DeliveryError(f'not a regular file in the package: {path.relative_to(d)}')
                found.append(path.relative_to(base).as_posix())
    return sorted(found)


def checked_outputs(d, facts):
    """(piece id, outputs) of facts that name this piece and package with well-formed output entries"""
    try:
        piece_id, outputs = facts['piece']['id'], facts['outputs']
        if piece_id != d.name or facts['package'] != PACKAGE or not isinstance(outputs, list):
            raise DeliveryError('facts name another piece or package')
        for o in outputs:
            library.relative(o['path'], 'facts output path')
            if (o['path'] == DELIVERY or not isinstance(o['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', o['sha256'])
                    or type(o['bytes']) is not int):
                raise DeliveryError(f"facts: bad output entry {o['name']}")
        for rel in facts['sources']:
            library.relative(rel, 'facts source path')
    except (library.LibraryError, KeyError, TypeError, AttributeError) as exc:
        raise DeliveryError(f'facts: malformed ({exc!r})') from None
    return piece_id, outputs


def owned_package(d):
    """(before, after) notes of an existing package deliver wrote, None when there is none; raises
    DeliveryError for anything deliver must not replace"""
    try:
        info = os.lstat(d / PACKAGE)
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(info.st_mode):
        raise DeliveryError(f'{PACKAGE} exists and is not a folder deliver wrote (a link or a file); move it away')
    try:
        before, facts, after = read_delivery(d)
    except FileNotFoundError:
        raise DeliveryError(f'{PACKAGE} holds no {DELIVERY}: it is not a package deliver wrote; move it away') from None
    except (OSError, DeliveryError) as exc:
        raise DeliveryError(f'{PACKAGE}/{DELIVERY} does not verify ({exc}); it was not replaced, so no note is lost; '
                            'move it away or restore it') from None
    try:
        _, outputs = checked_outputs(d, facts)
    except DeliveryError as exc:
        raise DeliveryError(f'{PACKAGE}/{DELIVERY} does not verify ({exc}); it was not replaced, so no note is lost; '
                            'move it away or restore it') from None
    listed = {DELIVERY} | {o['path'] for o in outputs}
    extra = sorted(set(package_files(d)) - listed)
    if extra:
        raise DeliveryError(f'{PACKAGE} holds files deliver did not write ({", ".join(extra[:5])}); move them away')
    # The packaged outputs are the user's copy: replace them only while each still is what was delivered.
    # Sources and art may have changed since (that is why to deliver again), so they are not compared.
    altered = []
    for o in outputs:
        try:
            now = hash_regular(d, f"{PACKAGE}/{o['path']}")
        except FileNotFoundError:
            altered.append(f"{o['path']} (missing)")
        except OSError as exc:
            altered.append(f"{o['path']} ({exc})")
        else:
            if now != (o['sha256'], o['bytes']):
                altered.append(f"{o['path']} (edited)")
    if altered:
        raise DeliveryError(f'{PACKAGE} holds packaged outputs that are not what was delivered ({", ".join(altered[:5])}); '
                            'it was not replaced; restore them or move the package away')
    return before, after


def write_at(dir_fd, rel, data):
    parts = rel.split('/')
    fd = os.dup(dir_fd)
    try:
        for part in parts[:-1]:
            with contextlib.suppress(FileExistsError):
                os.mkdir(part, 0o755, dir_fd=fd)
            sub = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = sub
        f = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644, dir_fd=fd)
        with os.fdopen(f, 'wb') as fh:
            fh.write(data)
    finally:
        os.close(fd)


def write_package(d, facts, artifacts):
    """write the outputs and DELIVERY.md to a new folder beside DIR/dist/delivery and swap it in;
    returns the bytes of DELIVERY.md"""
    owned = owned_package(d)
    notes = owned or default_notes(facts['piece']['id'])
    text = (notes[0] + facts_block(facts) + notes[1]).encode('utf-8')
    dist = render._folder(d, 'dist')
    fresh = '.delivery-%s' % os.urandom(6).hex()
    old = None
    try:
        os.mkdir(fresh, 0o755, dir_fd=dist)
        try:
            fd = os.open(fresh, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dist)
            try:
                for rel, data in sorted(artifacts.items()):
                    write_at(fd, rel, data)
                write_at(fd, DELIVERY, text)
            finally:
                os.close(fd)
            if owned:
                old = '.delivery-old-%s' % os.urandom(6).hex()
                os.rename('delivery', old, src_dir_fd=dist, dst_dir_fd=dist)
            os.rename(fresh, 'delivery', src_dir_fd=dist, dst_dir_fd=dist)
        except BaseException:
            with contextlib.suppress(OSError):
                shutil.rmtree(fresh, dir_fd=dist)
            if old:
                with contextlib.suppress(OSError):
                    os.rename(old, 'delivery', src_dir_fd=dist, dst_dir_fd=dist)
            raise
        if old:
            shutil.rmtree(old, dir_fd=dist)
    finally:
        os.close(dist)
    return text


# ---------------------------------------------------------------- run log

def log_delivery(d, record):
    """append record to DIR/.pixelate/runs.jsonl, opened without following a link; an error string
    instead of writing through one. PIXELATE_NO_LOG=1 writes nothing"""
    if not render.logging():
        return None
    text = json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n'
    try:
        fd = render._folder(d, '.pixelate')
        try:
            f = os.open('runs.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
                        | os.O_CLOEXEC, 0o644, dir_fd=fd)
        except OSError as exc:
            raise render.UnsafePath('.pixelate/runs.jsonl: a link or not a regular file (%s)' % exc.strerror) from exc
        finally:
            os.close(fd)
    except render.UnsafePath as exc:
        return 'run log not written: %s' % exc
    with os.fdopen(f, 'a', encoding='utf-8') as fh:
        if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
            return 'run log not written: .pixelate/runs.jsonl: not a regular file'
        fh.write(text)
    return None


# ---------------------------------------------------------------- deliver and verify

def deliver(d, sets=(), timeout=DEFAULT_TIMEOUT):
    """deliver the piece folder d: {ok, errors, outputs, fingerprint, package, delivery_sha256, log}.
    Raises DeliveryError for an invalid piece (exit 2)"""
    d = Path(d).absolute()
    library.positive(timeout, 'timeout')
    manifest = load_piece(d)
    sources = source_hashes(d, manifest)
    before_baseline = baseline_hash(d)
    result = {'ok': False, 'piece': manifest['id'], 'errors': [], 'outputs': [], 'fingerprint': None,
              'package': None, 'delivery_sha256': None, 'refused': False}
    code, out, err = run_render(d, sets, timeout)
    recs = []
    if code is None:
        result['errors'].append(f'render timed out after {timeout}s and was killed with its process group')
    elif code == 2:
        result['refused'] = True
        result['errors'].append('render refused: ' + tail(err, 3))
    else:
        try:
            recs = parse_report(out)
        except DeliveryError as exc:
            result['errors'].append(f'{exc}; render exited {code}: {tail(err, 3)}')
    if recs:
        outputs, artifacts, errors = collect(d, manifest, recs, sets)
        result['errors'] += errors
        if code and not errors:
            result['errors'].append(f'render exited {code}: {tail(err, 3)}')
        knobs = None
        try:
            if load_piece(d) != manifest or source_hashes(d, manifest) != sources:
                raise DeliveryError('piece.json or a source it references changed while the piece rendered')
            knobs = knob_facts(manifest, recs, sets)
        except DeliveryError as exc:
            result['errors'].append(str(exc))
        result['outputs'] = [{k: o[k] for k in ('name', 'kind', 'path', 'sha256')} for o in outputs]
        if not result['errors'] and knobs:
            try:
                after_baseline = baseline_hash(d)
                if after_baseline != before_baseline:
                    raise DeliveryError('remix baseline changed or disappeared while rendering')
                for image in (o for o in outputs if o['kind'] == 'image'):
                    used = image['distance'].get('baseline_sha256')
                    if used != after_baseline and (used is not None or (manifest.get('lineage') or {}).get('remixed_from')):
                        raise DeliveryError(f"{image['name']}: render measured distance with a different remix baseline")
                facts = build_facts(d, manifest, outputs, knobs, sources, after_baseline)
                text = write_package(d, facts, artifacts)
            except (OSError, DeliveryError) as exc:
                result['errors'].append(f'package not written: {exc}')
            else:
                result.update(ok=True, fingerprint=fingerprint(facts), package=PACKAGE, delivery_sha256=sha(text),
                              facts=facts)
    record = {'type': 'deliver', 'time': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
              'kit': VERSION, 'dir': d.name, 'piece': manifest['id'], 'status': manifest['status'],
              'request': manifest['request'], 'lineage': manifest.get('lineage') or {'remixed_from': None},
              'sets': list(sets), 'ok': result['ok'], 'errors': result['errors'], 'outputs': result['outputs'],
              'fingerprint': result['fingerprint'],
              'delivery': f'{PACKAGE}/{DELIVERY}' if result['ok'] else None, 'delivery_sha256': result['delivery_sha256']}
    result['log'] = log_delivery(d, record)
    return result


def verify(d):
    """{ok, fingerprint, checks: [{check, ok, detail}]}; reads files only and runs nothing"""
    d = Path(d).absolute()
    checks = []

    def check(name, good, detail=''):
        checks.append({'check': name, 'ok': bool(good), 'detail': detail})
        return good
    result = {'ok': False, 'fingerprint': None, 'checks': checks}
    if d.is_symlink() or not d.is_dir():
        check('piece folder', False, f'{d}: not a folder (or a link)')
        return result
    try:
        _, facts, _ = read_delivery(d)
        piece_id, outputs = checked_outputs(d, facts)
    except FileNotFoundError:
        check('facts', False, f'no {PACKAGE}/{DELIVERY}: not delivered')
        return result
    except (OSError, DeliveryError, library.LibraryError, KeyError, TypeError, AttributeError) as exc:
        check('facts', False, f'{PACKAGE}/{DELIVERY}: {exc}')
        return result
    result['fingerprint'] = fingerprint(facts)
    check('facts', True, f'block and fingerprint sha256:{result["fingerprint"]} match')
    try:
        present = package_files(d)
        listed = sorted({DELIVERY} | {o['path'] for o in outputs})
        check('package files', present == listed,
              '' if present == listed else 'holds %s, facts list %s' % (present, listed))
    except (OSError, DeliveryError) as exc:
        check('package files', False, str(exc))
    for o in outputs:
        for where, root_rel in (('package', f"{PACKAGE}/{o['path']}"), ('piece', o['path'])):
            try:
                digest, size = hash_regular(d, root_rel)
                check(f"{o['name']} {where}", (digest, size) == (o['sha256'], o['bytes']),
                      root_rel if digest == o['sha256'] else f'{root_rel}: sha256 {digest}, delivered {o["sha256"]}')
            except FileNotFoundError:
                check(f"{o['name']} {where}", False, f'{root_rel} is missing')
            except OSError as exc:
                check(f"{o['name']} {where}", False, str(exc))
    try:
        manifest = load_piece(d)
        declared = [(o['name'], o['kind'], output_path(o)) for o in manifest['outputs']]
        delivered = [(o['name'], o['kind'], o['path']) for o in outputs]
        check('piece manifest', declared == delivered and manifest['id'] == piece_id,
              '' if declared == delivered else 'the piece now declares other outputs than were delivered')
        current = source_hashes(d, manifest)
        changed = sorted(k for k in set(current) | set(facts['sources']) if current.get(k) != facts['sources'].get(k))
        check('sources', not changed, 'changed since delivery: ' + ', '.join(changed) if changed else
              f'{len(current)} files match')
        baseline = facts.get('remix_baseline')
        record_path = '.pixelate/remix-baseline.json'
        try:
            now = hash_regular(d, record_path)[0]
        except FileNotFoundError:
            check('remix baseline', baseline is None,
                  'not recorded or present' if baseline is None else f'{record_path} disappeared since delivery')
        except OSError as exc:
            check('remix baseline', False, str(exc))
        else:
            expected = baseline.get('sha256') if isinstance(baseline, dict) and baseline.get('path') == record_path else None
            check('remix baseline', isinstance(expected, str) and
                  re.fullmatch(r'[0-9a-f]{64}', expected) is not None and now == expected,
                  'unchanged' if now == expected else f'{record_path} changed or appeared since delivery')
        expected_baseline = baseline.get('sha256') if isinstance(baseline, dict) else None
        for o in outputs:
            if o['kind'] != 'image':
                continue
            distance = o.get('distance')
            used = distance.get('baseline_sha256') if isinstance(distance, dict) else None
            measured = isinstance(distance, dict) and (distance.get('pixels') is not None or
                                                       distance.get('palette') is not None)
            check(f"{o['name']} distance baseline", isinstance(distance, dict) and used == expected_baseline and
                  (not measured or used is not None),
                  'matches the packaged baseline' if used == expected_baseline else 'render used another baseline')
            record = o['path'] + SIDECAR
            try:
                now = hash_regular(d, record)[0]
            except FileNotFoundError:
                now = None
            had = o['review'].get('record_sha256')
            check(f"{o['name']} review record", now == had,
                  'unchanged' if now == had else f'{record} changed, appeared or disappeared since delivery; deliver again')
    except (OSError, DeliveryError, KeyError, TypeError) as exc:
        check('piece', False, str(exc))
    result['ok'] = all(c['ok'] for c in checks)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog='pixelate deliver', description=(__doc__ or '').split('\n\n', 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dir', metavar='DIR', help='a piece folder with piece.json')
    parser.add_argument('--verify', action='store_true',
                        help='check DIR/dist/delivery/DELIVERY.md and the files it names; runs no piece code')
    parser.add_argument('--set', action='append', default=[], metavar='KNOB=VALUE',
                        help='passed to `pixelate render`, which checks it and refuses what it does not support (repeatable)')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT,
                        help=f'seconds for the whole render before it is killed (default {DEFAULT_TIMEOUT})')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    d = Path(args.dir)
    if args.verify:
        if args.set:
            parser.error('--verify takes no --set: it runs nothing')
        result = verify(d)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            for c in result['checks']:
                print(('ok   ' if c['ok'] else 'FAIL ') + c['check'] + (': ' + c['detail'] if c['detail'] else ''))
            print('VERIFIED: the facts, the package and the piece match (not a quality, approval or rights check)'
                  if result['ok'] else 'NOT VERIFIED')
        return 0 if result['ok'] else 1
    try:
        result = deliver(d, args.set, args.timeout)
    except (DeliveryError, library.LibraryError) as exc:
        print(f'deliver: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        for o in result['outputs']:
            print(f"ok   {o['name']:<12} {o['kind']:<6} {o['path']} sha256 {o['sha256']}")
        for error in result['errors']:
            print(f'FAIL {error}')
        if result['ok']:
            ev = result['facts']['evidence']
            print(f"delivered: {d / PACKAGE / DELIVERY} (fingerprint sha256:{result['fingerprint']})")
            print(f"gate: {ev['gate']}; critique: {ev['critique']}; approval: "
                  + (f"declared by {ev['approval']['declared_by']}, UNVERIFIED" if ev['approval']['declared_by'] else 'none declared')
                  + '; rights: not verified')
        else:
            print(f'NOT DELIVERED: no package was written; an earlier {PACKAGE} was left as it was')
    if result['log']:
        print(result['log'], file=sys.stderr)
    if result['refused']:
        return 2
    return 0 if result['ok'] and not result['log'] else 1


if __name__ == '__main__':
    sys.exit(main())
