#!/usr/bin/env python3
"""Stage a trusted local program as a library contribution. Never call this from PR CI.

This command runs the source piece's shell commands twice without a sandbox. It proves only
technical gate legality and byte-for-byte reproducibility, not quality, approval or rights.
"""
import argparse
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import deliver
import library
import render


class ContributionError(ValueError):
    pass


def clean_copy(source, dest, manifest, keep_reviewed=False):
    """Copy sources and evidence, but not logs or packages. A reviewed frame binds its sidecar."""
    record = (manifest.get('review') or {}).get('record') if keep_reviewed else None
    generated = {o.get('frame') or o.get('file') for o in manifest['outputs']
                 if o.get('frame', '') + '.visual-review.json' != record}

    def ignore(folder, entries):
        rel = Path(folder).relative_to(source)
        return {entry for entry in entries if entry in ('.pixelate', 'dist', '__pycache__', 'render-report.json')
                or (rel / entry).as_posix() in generated}

    shutil.copytree(source, dest, symlinks=True, ignore=ignore)


def run_once(folder, timeout):
    code, out, err = deliver.run_render(folder, (), timeout)
    if code is None:
        raise ContributionError(f'render timed out after {timeout}s')
    recs = deliver.parse_report(out)
    manifest = deliver.load_piece(folder)
    outputs, artifacts, errors = deliver.collect(folder, manifest, recs, ())
    if errors:
        raise ContributionError('; '.join(errors))
    if code != 0:
        raise ContributionError(f'render exited {code}: {deliver.tail(err, 5)}')
    if len(outputs) != len(manifest['outputs']):
        raise ContributionError('render did not produce every declared output')
    return manifest, outputs, artifacts


def golden_bytes(data, output, canvas):
    from PIL import Image
    size = output.get('size') or canvas
    with Image.open(io.BytesIO(data)) as frame:
        expected = (size['w'] * output.get('scale', 1), size['h'] * output.get('scale', 1))
        if frame.size != expected:
            raise ContributionError(f"{output['name']}: frame size {frame.size} differs from {expected}")
        small = frame.convert('RGBA').resize((size['w'], size['h']), Image.Resampling.NEAREST)
        buf = io.BytesIO()
        small.save(buf, format='PNG')
        return buf.getvalue()


def add(source, catalog, status=None, timeout=300, trust_local_code=False):
    """Return a report; raise ContributionError before modifying the catalog on any failure."""
    if not trust_local_code:
        raise ContributionError('refusing to execute piece commands without --trust-local-code; there is no sandbox')
    source, catalog = Path(source).absolute(), Path(catalog).absolute()
    if source.is_symlink() or not source.is_dir() or catalog.is_symlink() or not catalog.is_dir():
        raise ContributionError('source and library must be real directories, not links')
    if source == catalog or catalog in source.parents or source in catalog.parents:
        raise ContributionError('source must be outside the catalog')
    try:
        manifest = library.validate(source)
        library.scan(catalog)
        if status is not None:
            library.choice(status, ('study', 'accepted', 'reviewed'), 'status')
        library.positive(timeout, 'timeout')
    except library.LibraryError as exc:
        raise ContributionError(str(exc)) from None
    piece_id = manifest['id']
    effective_status = status or manifest['status']
    if effective_status == 'starter':
        raise ContributionError('a contributed piece must be a study or have outside status evidence; use --status study')
    target = catalog / piece_id
    if target.exists() or target.is_symlink():
        raise ContributionError(f'{target}: a piece of this id already exists')
    with tempfile.TemporaryDirectory(prefix='.pixelate-add-', dir=catalog.parent) as tmp:
        scratch = Path(tmp)
        first, second, staged = (scratch / name / piece_id for name in ('first', 'second', 'staged'))
        for folder in (first, second, staged):
            folder.parent.mkdir(parents=True)
            clean_copy(source, folder, manifest, keep_reviewed=effective_status == 'reviewed')
            if status is not None:
                candidate = json.loads((folder / 'piece.json').read_text(encoding='utf-8'))
                candidate['status'] = status
                (folder / 'piece.json').write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + '\n',
                                                   encoding='utf-8')
            deliver.load_piece(folder)
        first_manifest, first_outputs, first_artifacts = run_once(first, timeout)
        _, second_outputs, second_artifacts = run_once(second, timeout)
        if first_artifacts != second_artifacts:
            changed = sorted(k for k in set(first_artifacts) | set(second_artifacts)
                             if first_artifacts.get(k) != second_artifacts.get(k))
            raise ContributionError('outputs differ between two clean renders: ' + ', '.join(changed))
        for output in first_manifest['outputs']:
            if output['kind'] != 'image':
                continue
            path = output['frame']
            golden = f"out/golden/{output['name']}.png"
            pixels = golden_bytes(first_artifacts[path], output, first_manifest['canvas'])
            target_golden = staged / golden
            target_golden.parent.mkdir(parents=True, exist_ok=True)
            if target_golden.is_symlink():
                raise ContributionError(f'{golden}: link instead of golden file')
            target_golden.write_bytes(pixels)
            output['golden'] = golden
        (staged / 'piece.json').write_text(json.dumps(first_manifest, indent=2, ensure_ascii=False) + '\n',
                                          encoding='utf-8')
        trail = staged / 'history/add-report.json'
        if trail.exists() or trail.is_symlink():
            raise ContributionError('history/add-report.json exists: keep the prior report and choose another id')
        trail.parent.mkdir(parents=True, exist_ok=True)
        trail.write_text(json.dumps({'schema': 1, 'type': 'library-add', 'status_declared': first_manifest['status'],
                                     'clean_renders': 2, 'byte_equal': True,
                                     'outputs': [{'name': o['name'], 'kind': o['kind'], 'sha256': o['sha256'],
                                                  'gate_ok': o['gate']['ok'] if o['kind'] == 'image' else None}
                                                 for o in first_outputs],
                                     'independent_review': 'not established', 'approval': 'not verified',
                                     'redistribution_rights': 'not verified'},
                                    indent=2, sort_keys=True) + '\n', encoding='utf-8')
        library.validate(staged)
        try:
            os.rename(staged, target)
            try:
                library.write_index(catalog)
            except BaseException:
                shutil.rmtree(target)
                raise
        except OSError as exc:
            raise ContributionError(f'could not stage {target}: {exc}') from None
    return {'ok': True, 'piece': piece_id, 'status': first_manifest['status'],
            'outputs': [{'name': o['name'], 'kind': o['kind'], 'sha256': o['sha256']}
                        for o in first_outputs], 'renders': 2, 'deterministic': True, 'gate_ok': True,
            'path': str(target), 'index': str(catalog / 'index.json'),
            'notice': 'Technical evidence only. No independent art grade, user approval or redistribution '
                      'rights were established. Inspect every source and file before a manual pull request.'}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='pixelate library add', description=__doc__)
    parser.add_argument('dir', metavar='DIR')
    parser.add_argument('--library', type=Path, default=library.DEFAULT_LIBRARY)
    parser.add_argument('--status', choices=('study', 'accepted', 'reviewed'))
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--trust-local-code', action='store_true', help='explicitly allow two unsandboxed renders of this local program')
    args = parser.parse_args(argv)
    try:
        result = add(args.dir, args.library, args.status, args.timeout, args.trust_local_code)
    except (ContributionError, library.LibraryError, deliver.DeliveryError, OSError) as exc:
        parser.exit(1, f'library add: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == '__main__':
    main()
