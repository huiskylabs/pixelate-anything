#!/usr/bin/env python3
"""pixelate remix PIECE DIR --request "..." [--library L] [--timeout S] [--json]

Copy library piece PIECE into the new folder DIR as a piece whose id is DIR's name, render the
unedited copy once in a clean temporary copy (`pixelate library test --quick` semantics), and only
if it passes move it into place with REMIX.md and the baseline evidence .pixelate/remix-baseline.json.
A copy that does not pass leaves DIR as it was.

The copy keeps sources, media, history and 1x goldens, but no generated outputs, run data or review
sidecar. Its manifest records the request, `lineage.remixed_from` and status `study`; a starter
stays `starter`. Review and approval evidence is dropped, because it was bound to the base, not to
the copy. The license declaration is copied as declared, not verified.

Looking a piece up runs nothing. The baseline render runs the base piece's commands through the shell,
without a sandbox: remix only trusted, checked-in pieces.

Exit status: 0 when the copy was created; 1 when its baseline failed (nothing is created) or it could
not be written; 2 for an unknown or invalid piece, an empty request or an unusable DIR.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

if __package__:
    from . import library
    from .version import VERSION
else:
    import library
    from version import VERSION

BASELINE = '.pixelate/remix-baseline.json'
# Folders and files a render or delivery writes; never copied, as in `pixelate new`.
RUN_DATA = ('.pixelate', 'dist', 'shots', '__pycache__', 'render-report.json')
# The plan's aspects a remix keeps or changes; REMIX.md asks for a decision on each.
ASPECTS = (('subject', 'tags.subject'), ('setting', 'tags.setting'), ('camera', 'tags.camera'),
           ('palette', None), ('composition', None), ('motion', 'tags.motion'), ('sound', 'tags.sound'))


class RemixError(ValueError):
    """The piece, request or destination cannot be remixed; nothing was created."""


def file_hashes(root):
    """{relative POSIX path: sha256} of every regular file under root, never following a link."""
    hashes = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(files):
            path = Path(base) / name
            if path.is_symlink() or not path.is_file():
                raise RemixError(f'not a regular file in the copy: {path}')
            hashes[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def copy_ignore(source, manifest):
    generated = {output.get('frame') or output['file'] for output in manifest['outputs']}
    record = (manifest.get('review') or {}).get('record')

    def ignore(folder, entries):
        # Keep sources, media, history and out/golden; leave out run data, generated outputs and any
        # review sidecar, which binds the base's bytes and is no evidence for the copy.
        rel = Path(folder).relative_to(source)
        return {entry for entry in entries
                if entry in RUN_DATA or entry.endswith('.visual-review.json')
                or (rel / entry).as_posix() in generated or (rel / entry).as_posix() == record
                or (rel.as_posix() == 'out' and entry != 'golden')}
    return ignore


def remix_manifest(base, piece_id, request, today):
    manifest = {key: value for key, value in base.items() if key != 'review'}
    manifest.update(id=piece_id, request=request, status='starter' if base['status'] == 'starter' else 'study',
                    lineage={'remixed_from': base['id']},
                    provenance={'made': today, 'by': f"pixelate remix of {base['id']}; base provenance "
                                                     f"{base['provenance']['made']}: {base['provenance']['by']}"})
    return manifest


def cell(value):
    if isinstance(value, list):
        value = ', '.join(str(v) for v in value)
    return str(value).replace('\n', ' ').replace('|', '\\|')


def describe(result):
    """One line for one output of the baseline report."""
    if result['status'] == 'skipped':
        return f"skipped, untested ({result['reason']})"
    if result['status'] == 'failed':
        return 'FAILED: ' + result.get('error', '') + (f" ({result['golden']['error']})"
                                                      if result.get('golden', {}).get('error') else '')
    if result['kind'] != 'image':
        return f"passed: rendered a nonempty {result['kind']} file (not gated)"
    if result.get('gate_ok'):
        return 'passed: golden match, technical gate PASS'
    fails = '; '.join(' '.join(line.split()) for line in result['gate']['fail'][:3])
    return ('passed as a study: golden match, but the technical gate FAILED (' + fails +
            '); it is NOT gate-legal and not approved')


def remix_md(manifest, base, baseline, baseline_sha):
    tags = manifest['tags']
    review = base.get('review') or {}
    lines = [f"# Remix: {manifest['id']}", '', 'Request:', '']
    lines += ['> ' + line if line else '>' for line in manifest['request'].splitlines()]
    lines += ['', f"## Base: {base['id']} ({base['title']})", '', base['summary'], '',
              f"- Base status: `{base['status']}`" + (f"; approved by {review['approved_by']}" if review.get('approved_by') else '')
              + (f"; review record {review['record']}" if review.get('record') else '') + '.',
              f"- This copy: status `{manifest['status']}`, `lineage.remixed_from: {base['id']}`. The base's review and "
              'approval do not carry over: they were bound to the base, and this copy is unreviewed.',
              f"- Mode `{manifest['mode']}`, runtime `{manifest['runtime']}`, canvas {manifest['canvas']['w']}x"
              f"{manifest['canvas']['h']} at scale {manifest['canvas']['scale']}.",
              f"- License: `{manifest['license']}` as the base declares it. The declaration was copied, not verified; "
              'it does not establish rights to any source the base was made from. Base provenance: '
              f"{base['provenance']['by']}", '',
              '## Baseline: the unedited copy', '',
              'Rendered once in a clean temporary copy before any edit (`pixelate library test --quick` semantics), so a '
              'later failure is your edit, not the base. A golden match is a regression test and a gate pass is a '
              'technical check; neither is a quality judgment or approval.', '',
              f"Evidence: `{BASELINE}` (sha256 `{baseline_sha}`), with the hash of every copied file.", '',
              '| Output | Kind | Result |', '|---|---|---|']
    lines += [f"| {r['name']} | {r['kind']} | {cell(describe(r))} |" for r in baseline['test']['outputs']]
    lines += ['', '## Anatomy', '', '| File | Draws | Change for |', '|---|---|---|']
    lines += [f"| `{a['file']}` | {cell(a['draws'])} | {cell(a['change_for'])} |" for a in manifest['anatomy']]
    lines += ['', '## Knobs', '']
    if manifest['knobs']:
        lines += ['Declared settings and the file that reads each. For a script piece whose program reads `knobs()`, '
                  '`pixelate render DIR --set KNOB=VALUE` renders a variant without an edit; engine and pack pieces '
                  'take no `--set` yet, so there a knob change is an edit to its file.', '',
                  '| Knob | Values | Default | Edits |', '|---|---|---|---|']
        lines += [f"| {name} | {cell(knob.get('values', knob.get('type')))} | {cell(knob['default'])} | `{knob['edits']}` |"
                  for name, knob in manifest['knobs'].items()]
    else:
        lines += ['None declared: every change is an edit to a file the anatomy names.']
    lines += ['', '## Plan', '', 'Fill this in before editing. For each aspect, say whether it stays or changes, '
              'and how, and which anatomy file you will edit.', '',
              '| Aspect | Base | Stays or changes | How, and which file |', '|---|---|---|---|']
    lines += [f"| {aspect} | {cell(tags[source[5:]]) if source else ''} |  |  |" for aspect, source in ASPECTS]
    lines += ['', 'What stays:', '', '- (fill in)', '', 'What changes:', '', '- (fill in)', '',
              '## Checklist', '',
              '- [ ] The plan above names what stays and what changes for every aspect.',
              '- [ ] Change knob files first, then the files the anatomy names, then anything else.',
              '- [ ] `piece.json`: update `title`, `summary`, `tags` and `anatomy` to what the piece now draws.',
              '- [ ] `pixelate render DIR`: every image runs and passes the technical gate.',
              '- [ ] Update `out/golden/` only for intended changes, and regenerate `media/` (it still shows the base).',
              '- [ ] Status stays `' + manifest['status'] + '`: no gate pass, golden match or self-assessment approves it.',
              '- [ ] Check the rights to every source and the license before publishing.', '']
    return '\n'.join(lines)


def baseline_lines(report):
    yield f"baseline of the unedited copy: {'ok' if report['ok'] else 'FAILED'}" + (f": {report['error']}" if 'error' in report else '')
    for result in report['outputs']:
        yield f"  {result['name']:<12} {result['kind']:<6} {describe(result)}"


def remix(piece_id, dest, request, library_root=library.DEFAULT_LIBRARY, timeout=300) -> tuple[bool, dict]:
    """Create DIR from the piece, or raise RemixError (input) / return a failed baseline untouched.

    Returns (created, baseline): created is False when the unedited copy did not pass its baseline, in
    which case nothing was created and baseline holds the report."""
    library.slug(piece_id, 'piece id')
    library.text(request, 'request')
    library.positive(timeout, 'timeout')
    library_root = Path(library_root).absolute()
    if library_root.is_symlink() or not library_root.is_dir():
        raise RemixError(f'{library_root}: missing or unsafe library directory')
    source = library_root / piece_id
    if not source.is_dir() and not source.is_symlink():
        raise RemixError(f'{piece_id}: unknown piece in {library_root}')
    base = library.validate(source)  # rejects a link anywhere in the piece; runs nothing
    if not library.SLUG.fullmatch(Path(dest).name):  # before absolute(), so `.` is no name
        raise RemixError(f'{dest}: the folder name becomes the piece id; use a lowercase slug such as my-{piece_id}')
    dest = Path(dest).absolute()
    resolved = dest.parent.resolve() / dest.name
    for root in {library_root.resolve(), library.DEFAULT_LIBRARY.resolve()}:
        if resolved == root or root in resolved.parents:
            raise RemixError(f'{dest} is inside the library {root}; remix into a work folder')
    if dest.is_symlink():
        raise RemixError(f'{dest} is a symbolic link; choose a new folder')
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise RemixError(f'{dest} exists and is not an empty folder')
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        build = Path(tempfile.mkdtemp(prefix=f'.{dest.name}-', dir=dest.parent))
    except OSError as exc:
        raise OSError(f'cannot create {dest}: {exc}') from exc
    try:
        work = build / dest.name
        shutil.copytree(source, work, symlinks=True, ignore=copy_ignore(source, base))
        today = datetime.date.today().isoformat()
        manifest = remix_manifest(base, dest.name, request, today)
        (work / 'piece.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        library.validate(work)  # also rejects a link raced into the copy
        files = file_hashes(work)
        report: dict = library.test_piece(work, quick=True, timeout=timeout)
        if file_hashes(work) != files:
            report = dict(report, ok=False, error='the copy changed while its baseline rendered')
        baseline: dict = {
            'schema': 1, 'type': 'remix-baseline',
            'time': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            'kit': VERSION, 'piece': dest.name, 'request': request, 'status': manifest['status'],
            'base': {'id': base['id'], 'title': base['title'], 'status': base['status'],
                     'review': base.get('review'), 'license': base['license']},
            'quick': True, 'files': files,
            'files_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
            'test': report,
            'untested': [{'name': r['name'], 'kind': r['kind'], 'reason': r['reason']}
                         for r in report['outputs'] if not r['tested']],
            'note': 'Rendered in a clean temporary copy of these files. A golden match is a regression test and a '
                    'gate pass a technical check; neither is approval. gate_ok false with ok true means a study '
                    'rendered and matched its goldens but is not gate-legal.'}
        if not report['ok']:
            return False, baseline
        data = (json.dumps(baseline, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
        (work / '.pixelate').mkdir()
        (work / BASELINE).write_bytes(data)
        baseline_sha = hashlib.sha256(data).hexdigest()
        (work / 'REMIX.md').write_text(remix_md(manifest, base, baseline, baseline_sha), encoding='utf-8')
        try:
            os.rename(work, dest)  # replaces only a missing path or an empty folder
        except OSError as exc:
            raise OSError(f'cannot create {dest}: {exc}') from exc
        return True, dict(baseline, sha256=baseline_sha)
    finally:
        shutil.rmtree(build, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='pixelate remix', description=(__doc__ or '').split('\n\n', 1)[-1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('piece', metavar='PIECE', help='library piece id, such as market-day')
    parser.add_argument('dir', metavar='DIR', help="new folder; its name becomes the piece id")
    parser.add_argument('--request', required=True, help='the request this remix answers, word for word')
    parser.add_argument('--library', type=Path, default=library.DEFAULT_LIBRARY,
                        help='library folder (default: the kit library); its pieces must be trusted')
    parser.add_argument('--timeout', type=int, default=300, help='seconds per run command (default 300)')
    parser.add_argument('--json', action='store_true', help='print the baseline record as JSON')
    args = parser.parse_args(argv)
    try:
        created, baseline = remix(args.piece, args.dir, args.request, args.library, args.timeout)
    except (RemixError, library.LibraryError) as exc:
        print(f'remix: {exc}', file=sys.stderr)
        return 2
    except OSError as exc:
        print(f'remix: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(baseline, indent=2, sort_keys=True, ensure_ascii=False))
    if not created:
        print('\n'.join(baseline_lines(baseline['test'])), file=sys.stderr)
        print(f"remix: the unedited copy of {args.piece} did not pass its baseline render; nothing was created at "
              f"{args.dir}", file=sys.stderr)
        return 1
    if not args.json:
        dest = Path(args.dir)
        print(f"created {dest} (piece id {baseline['piece']}, status {baseline['status']}, unreviewed) as a remix of "
              f"{args.piece} (status {baseline['base']['status']})")
        print('\n'.join(baseline_lines(baseline['test'])))
        gate = baseline['test']['gate_ok']
        print('gate_ok: ' + ('true' if gate else 'null (no image to gate)' if gate is None else
                             'false: rendered and matched its goldens, but not gate-legal'))
        print(f"evidence: {dest / BASELINE} (sha256 {baseline['sha256']})")
        print(f'next: fill in the plan in {dest / "REMIX.md"}, edit, then `pixelate render {dest}`')
    return 0


if __name__ == '__main__':
    sys.exit(main())
