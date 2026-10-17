#!/usr/bin/env python3
"""Artifact-bound records for externally produced visual lead critiques; no model is run here."""
import hashlib
import json
import os
import pathlib
import re
import stat
import tempfile

MAX_REPORT = 128 * 1024
MAX_MANIFEST = 8 * 1024
VERSION = 1


class ReviewError(ValueError):
    """Evidence is absent, unsafe, or not a valid visual lead review."""


def _file(path, limit=None):
    path = pathlib.Path(path)
    if not path.is_file():
        raise ReviewError(f'missing file: {path}')
    if limit is not None and path.stat().st_size > limit:
        raise ReviewError(f'file too large: {path}')
    with path.open('rb') as handle:
        data = handle.read((limit + 1) if limit is not None else -1)
    if limit is not None and len(data) > limit:
        raise ReviewError(f'file too large: {path}')
    return data


def _path(path):
    if not path or not str(path).strip():
        raise ReviewError('empty path')
    return pathlib.Path(path).resolve()


def _manifest(brief, frame):
    artifact = frame or brief
    return artifact.with_name(artifact.name + '.visual-review.json')


def _short(brief_bytes):
    try:
        text = brief_bytes.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ReviewError('brief is not UTF-8') from exc
    first = text.lstrip().split('\n', 1)[0]
    gate = re.search(r'^##\s+(?:\d+\.\s*)?Gate\s*$', text, re.M | re.I)
    show = re.search(r'^##\s+(?:\d+\.\s*)?Show the user\s*$', text, re.M | re.I)
    later = re.search(r'^##\s+(?:[6-9]|1[01])\.', text, re.M)
    return 'short brief' in first.lower() or bool(gate and show and not later)


def _report(data):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ReviewError('report is not UTF-8') from exc
    if re.search(r'\bNOT REVIEWED\b|^\s*(?:ROLE|SPECIALIST|MOTIF|ARRANGEMENT|MOOD|MIX|SCENE FIT)\s*:', text, re.I | re.M):
        raise ReviewError('not a graded visual lead critique')
    lines = text.splitlines()
    def field(label, required=True):
        found = [i for i, line in enumerate(lines) if re.match(r'^' + label + r'\s*:', line, re.I)]
        if len(found) != 1:
            raise ReviewError(f'expected one {label} line')
        value = lines[found[0]].split(':', 1)[1].strip()
        if required and not value:
            raise ReviewError(f'empty {label}')
        return found[0], value
    grade_i, grade = field('GRADE')
    score_i, score_line = field('SCORES')
    sig_i, signature = field('SIGNATURE MOMENT')
    problem_i, _ = field('BIGGEST PROBLEM')
    fixes_i, fixes = field('FIXES(?: \\(ranked by impact, up to 5; 3 to 5 below A\\))?', required=False)
    if fixes:
        raise ReviewError('fixes belong on ranked lines after FIXES')
    keep_i, _ = field('KEEP')
    if not (grade_i < score_i < sig_i < problem_i < fixes_i < keep_i) or grade not in ('A', 'B', 'C'):
        raise ReviewError('malformed visual lead rubric or grade')
    before = [line.strip() for line in lines[:grade_i] if line.strip()]
    if len(before) > 1 or (before and not before[0].startswith('PRIOR FIXES:')):
        raise ReviewError('unexpected text before visual lead rubric')
    for start, end in ((grade_i, score_i), (score_i, sig_i), (sig_i, problem_i), (problem_i, fixes_i)):
        if any(line.strip() for line in lines[start + 1:end]):
            raise ReviewError('unexpected text in visual lead rubric')
    score_match = re.fullmatch(r'\s*' + r'\s+'.join(rf'{n}\s*=\s*([1-5])' for n in range(1, 13)) +
                               r'\s+originality\s*:\s*(pass|fail)\s*', score_line, re.I)
    if not score_match:
        raise ReviewError('expected 12 ordered scores (1-5) and originality pass/fail')
    scores = [int(n) for n in score_match.groups()[:12]]
    originality = score_match.group(13).lower()
    if grade == 'A' and (originality != 'pass' or re.fullmatch(r'\W*(?:none|n/a|not applicable)\W*', signature, re.I) or
                         any(n < 4 for n in scores) or any(scores[n - 1] != 5 for n in (1, 3, 4))):
        raise ReviewError('A contradicts the visual rubric')
    if originality == 'fail' and grade != 'C':
        raise ReviewError('copied IP requires C')
    ranked = [line for line in lines[fixes_i + 1:keep_i] if line.strip()]
    if len(ranked) > 5 or (grade != 'A' and len(ranked) < 3):
        raise ReviewError('expected up to five ranked fixes (3-5 below A)')
    if any(not re.match(rf'^{i}\.\s+\S.*', line) for i, line in enumerate(ranked, 1)):
        raise ReviewError('fixes must be consecutively ranked and nonempty')
    if any(line.strip() for line in lines[keep_i + 1:]):
        raise ReviewError('unexpected text after KEEP')
    return grade


def _context(brief, frame):
    brief = _path(brief)
    frame = _path(frame) if frame else None
    brief_data = _file(brief)
    if frame:
        frame_data = _file(frame)
        if frame == brief:
            raise ReviewError('frame and brief must differ')
    else:
        frame_data = None
        if _short(brief_data):
            raise ReviewError('short brief skips brief-stage review')
    return brief, frame, brief_data, frame_data


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def record(brief, report, frame: str | pathlib.Path | None = ''):
    """Validate an external report and atomically bind it to exact current artifact bytes."""
    brief, frame, brief_data, frame_data = _context(brief, frame)
    report = _path(report)
    manifest = _manifest(brief, frame)
    if report in (brief, frame, manifest):
        raise ReviewError('report must be separate from artifacts and manifest')
    report_data = _file(report, MAX_REPORT)
    grade = _report(report_data)
    if manifest.is_symlink() or (manifest.exists() and not stat.S_ISREG(manifest.lstat().st_mode)):
        raise ReviewError(f'unsafe manifest path: {manifest}')
    payload = {'version': VERSION, 'stage': 'still' if frame else 'brief',
               'brief': str(brief), 'brief_sha256': _hash(brief_data),
               'frame': str(frame) if frame else None, 'frame_sha256': _hash(frame_data) if frame else None,
               'report': str(report), 'report_sha256': _hash(report_data), 'grade': grade}
    content = (json.dumps(payload, indent=2, sort_keys=True) + '\n').encode('utf-8')
    if len(content) > MAX_MANIFEST:
        raise ReviewError('manifest too large')
    # Never replace a report with the manifest. Replace an existing regular manifest atomically.
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=manifest.parent, prefix='.visual-review-',
                                         delete=False) as handle:
            name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, manifest)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return f"RECORDED {grade} {payload['stage']} review: {manifest}"


def status(brief, frame: str | pathlib.Path | None = ''):
    """Return (ready, reason). Revalidate both report rubric and exact artifact hashes."""
    try:
        brief, frame, brief_data, frame_data = _context(brief, frame)
        manifest = _manifest(brief, frame)
        if manifest.is_symlink() or (manifest.exists() and not stat.S_ISREG(manifest.lstat().st_mode)):
            raise ReviewError(f'unsafe manifest path: {manifest}')
        raw = _file(manifest, MAX_MANIFEST)
        try:
            payload = json.loads(raw)
        except (UnicodeError, ValueError) as exc:
            raise ReviewError('invalid manifest') from exc
        if not isinstance(payload, dict) or set(payload) != {'version', 'stage', 'brief', 'brief_sha256',
                                                               'frame', 'frame_sha256', 'report', 'report_sha256', 'grade'}:
            raise ReviewError('invalid manifest schema')
        if raw != (json.dumps(payload, indent=2, sort_keys=True) + '\n').encode('utf-8'):
            raise ReviewError('manifest bytes changed or noncanonical')
        if type(payload['version']) is not int or payload['version'] != VERSION or payload['stage'] != ('still' if frame else 'brief'):
            raise ReviewError('manifest version or stage mismatch')
        if payload['brief'] != str(brief) or payload['frame'] != (str(frame) if frame else None):
            raise ReviewError('manifest artifact mismatch')
        if payload['brief_sha256'] != _hash(brief_data):
            raise ReviewError('brief changed since review')
        if frame and payload['frame_sha256'] != _hash(frame_data):
            raise ReviewError('frame changed since review')
        if not frame and payload['frame_sha256'] is not None:
            raise ReviewError('unexpected frame hash')
        report_path = payload['report']
        if not isinstance(report_path, str) or not pathlib.Path(report_path).is_absolute() or pathlib.Path(report_path).resolve() != pathlib.Path(report_path) or report_path in (str(brief), str(frame), str(manifest)):
            raise ReviewError('unsafe report path in manifest')
        report_data = _file(report_path, MAX_REPORT)
        if payload['report_sha256'] != _hash(report_data):
            raise ReviewError('report changed since review')
        grade = _report(report_data)
        if payload['grade'] != grade:
            raise ReviewError('manifest grade mismatch')
        if grade != 'A':
            return False, f'grade {grade} (requires A)'
        return True, f"READY: matching A {payload['stage']} review ({manifest})"
    except (ReviewError, OSError) as exc:
        return False, f'NOT READY: {exc}'
