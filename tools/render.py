#!/usr/bin/env python3
"""pixelate render DIR [--image NAME] [--set KNOB=VALUE ...] [--no-run] [--critique] [--json]

One command from art to a verified still. DIR/piece.json (a library piece, `references/piece.md`) or
DIR/render.json names each image: the command that draws it, the frame it writes and how it is
gated. For every image, render runs the command, gates the frame (`pixelate check`, with the brief's
`## Image NAME` lines via --image), era-checks it when it names an era (`pixelate era` reports
violations but exits 0, so `era.ok` means the check ran; the gate's --era lines decide era legality),
judges it (`pixelate judge`, overlay beside the frame, logged to the corpus) and, with --critique,
runs the art director (`pixelate critique --run`). It prints one compact line per image and writes DIR/render-report.json,
plus one record in DIR/.pixelate/runs.jsonl; it exits 1 when any image fails its command or its
gate. PIXELATE_NO_LOG=1 turns off all of its logs (run, judge, critique).

render.json:

    {"images": [
      {"name": "a", "run": "python3 art/render.py a", "frame": "out/01-a.png",
       "style": "cosy-lightmap", "scene": "exterior", "scale": 4, "brief": "brief.md",
       "pal": "out/palette.json", "pre": "out/01-a@1x.png", "used": "light,shaft",
       "actor": "", "era": "", "judge_ignore": ""}
    ]}

Paths are relative to DIR. `run` may be omitted for a frame drawn some other way; `style` or `era` is
required for the gate.

piece.json outputs replace render.json: an image output takes the same fields plus `kind`, and audio
and export outputs are run and hashed but never gated. Piece commands run with the kit's `tools/` first
on PYTHONPATH and the kit root (the `pixelate` command) first on PATH, and PIXELATE_KIT set to the kit
root, whatever the caller exported. Outputs that share a run command run it once, in order of first
appearance. Before it runs, each of its declared frames and files is deleted from DIR (never through a
link), so a stale output from an earlier render cannot pass: the command must write it again, and a
render that cannot delete one fails that command. --no-run deletes nothing. After a piece command, a frame,
file or gate input reached through a link, or not a regular file, fails. The frame is read once without
following links, and the gate and era check run on a private copy of those bytes and of the gate inputs;
the judge and --critique read the same bytes, so the hash is of the bytes they all checked. With logging
on, the frame (and, for --critique, the brief the gate read) is kept write-once at
DIR/.pixelate/snapshots/<sha256>/<file name>, the path the judge and critique logs name; with
PIXELATE_NO_LOG=1 they read the private copy. The critique's thumbnails and saved critique go beside the
frame in DIR. render.json images are hashed, gated, judged and critiqued in place. A folder with both
files is an error.

--set KNOB=VALUE (repeatable) renders a variant of a script, engine or pack piece: each value is checked
against the manifest's knobs, the chosen values go to a temporary JSON file outside DIR whose path the
piece's commands get in PIXELATE_KNOBS, and the runtime reads it: a script's `knobs()` (tools/piece.py)
merges them with the defaults; an engine build (tools/build.py, so `pixelate shot`, `video`, `gif`,
`audio`, `build`) puts every knob in a PIXELATE_KNOBS constant before the scene's scripts; a pack export
(`pixelate assets`) sets the pack.json options its knobs name. Neither piece.json, scene.json, pack.json
nor any source is changed, and the file is deleted afterwards. The values, the merged settings and the
file's SHA-256 go into the report and the run record; they say what the commands were given, not that
the program drew them. A variant is not compared with golden frames. --set is refused for render.json
and with --no-run. Without --set, PIXELATE_KNOBS is removed from the piece commands' environment, so
they draw the defaults.

A piece whose lineage.remixed_from names a base gets a `distance` in each image record, the run record
and its line (tools/distance.py): how many 1x pixels and what share of distinct colours of the hashed
frame bytes differ from the golden of the base output of the same name. The base is looked up only in
the kit's checked-in library, validated statically and read before any command runs; none of its code
runs. It must match the SHA-256 of the base piece.json and goldens that DIR/.pixelate/remix-baseline.json
records (a consistency check; the file is not signed). No usable baseline, a kit piece that does not
match it, a missing or invalid base, an output or golden it lacks, or a frame that was not read leaves
the distance unavailable with a reason, and a size change leaves the pixel count unavailable; neither
is reported as 0. When the request differs from the base's and both shares are small, the record carries
an "under-remixed" WARNING. It is an uncalibrated heuristic, not a grade or a gate: it never changes
the exit status. Other pieces' images record `distance` with base null and the reason.
"""
import argparse, contextlib, datetime, hashlib, json, os, pathlib, re, shlex, signal, stat, subprocess, sys, tempfile, time

KIT = pathlib.Path(__file__).resolve().parent.parent
PIXELATE = [sys.executable, str(KIT / 'pixelate')]
GATE_FLAGS = (('style', '--style'), ('scene', '--scene'), ('era', '--era'), ('pal', '--pal'), ('pre', '--pre'),
              ('actor', '--actor'), ('used', '--used'), ('intent', '--intent'))
# The files the image gate reads besides the frame.
GATE_FILES = ('brief', 'pal', 'pre', 'actor', 'intent')
# Under a piece: the frame and brief bytes a logged render checked, each kept at <sha256>/<file name>.
SNAPSHOTS = '.pixelate/snapshots'

def knob_helper():
    """tools/piece.py, the knob contract shared with the programs that read knobs()"""
    if __package__:
        from . import piece
    else:
        import piece
    return piece

def distance_helper():
    """tools/distance.py, the distance of a remix's frames from its base"""
    if __package__:
        from . import distance
    else:
        import distance
    return distance

class UnsafePath(OSError):
    """a piece path that goes through a link or does not end at a regular file"""

def _parent(root, rel):
    """(descriptor of the folder holding rel under root, last component), reached without following
    a link; rel is a validated piece path. The caller closes the descriptor."""
    parts = rel.split('/')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in parts[:-1]:
            try:
                sub = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            except FileNotFoundError:
                raise
            except OSError as exc:
                raise UnsafePath('%s: %s is a link or not a folder (%s)' % (rel, part, exc.strerror)) from exc
            os.close(fd)
            fd = sub
    except BaseException:
        os.close(fd)
        raise
    return fd, parts[-1]

def _read_at(fd, name, rel):
    """the bytes of the regular file name in the folder fd, opened without following a link; rel
    names it in errors"""
    try:
        # O_NONBLOCK: opening a pipe planted at rel must not hang the checker.
        f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise UnsafePath('%s: a link or not a regular file (%s)' % (rel, exc.strerror)) from exc
    with os.fdopen(f, 'rb') as fh:
        if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
            raise UnsafePath('%s: not a regular file' % rel)
        return fh.read()

def read_regular(root, rel):
    """the bytes of the regular file rel under root, opened without following any link; raises
    FileNotFoundError when it is missing and UnsafePath for a link, folder, pipe or device"""
    fd, name = _parent(root, rel)
    try:
        return _read_at(fd, name, rel)
    finally:
        os.close(fd)

def _folder(root, rel):
    """descriptor of the folder rel under root, each missing component made, every one reached
    without following a link; raises UnsafePath for a link or a file on the way. The caller closes it"""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in rel.split('/'):
            with contextlib.suppress(FileExistsError):
                os.mkdir(part, dir_fd=fd)
            try:
                sub = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            except OSError as exc:
                raise UnsafePath('%s: %s is a link or not a folder (%s)' % (rel, part, exc.strerror)) from exc
            os.close(fd)
            fd = sub
    except BaseException:
        os.close(fd)
        raise
    return fd

def keep_snapshot(d, data, name):
    """store data at .pixelate/snapshots/<its sha256>/name under d and return that path relative to d.
    A file already there is never replaced: it must hold exactly data. Nothing on the way may be a
    link; raises UnsafePath otherwise"""
    digest = hashlib.sha256(data).hexdigest()
    rel = '%s/%s' % (SNAPSHOTS, digest)
    fd = _folder(d, rel)
    try:
        try:
            kept = _read_at(fd, name, rel + '/' + name)
        except FileNotFoundError:
            # Written whole under a private name, then linked in: a link never replaces a file.
            tmp = '.%s.%s.tmp' % (name, os.urandom(6).hex())
            f = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o444, dir_fd=fd)
            try:
                with os.fdopen(f, 'wb') as fh:
                    fh.write(data)
                with contextlib.suppress(FileExistsError):
                    os.link(tmp, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            finally:
                os.unlink(tmp, dir_fd=fd)
            kept = _read_at(fd, name, rel + '/' + name)
        if hashlib.sha256(kept).hexdigest() != digest:
            raise UnsafePath('%s/%s: holds other bytes than its hash' % (rel, name))
    finally:
        os.close(fd)
    return rel + '/' + name

def remove_regular(root, rel):
    """delete rel under root if it is there, without following a link in its folders; a link at rel
    itself is removed, never its target"""
    try:
        fd, name = _parent(root, rel)
    except FileNotFoundError:
        return
    try:
        os.unlink(name, dir_fd=fd)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise UnsafePath('%s: cannot remove (%s)' % (rel, exc.strerror)) from exc
    finally:
        os.close(fd)

def gate_snapshot(folder, im, frame, d, brief_root=None):
    """write a private copy of what the image gate reads into folder: the bytes `frame` at im's frame
    path, and each existing gate input of im read once from d (the brief from brief_root, when given)
    without following a link. Returns 'unsafe gate input: ...' for an input that is a link or not a
    regular file, else None; a missing input is left for the gate to report"""
    files = {im['frame']: frame}
    for key in GATE_FILES:
        if im.get(key) and im[key] not in files:
            try:
                files[im[key]] = read_regular(brief_root if key == 'brief' and brief_root else d, im[key])
            except FileNotFoundError:
                pass
            except UnsafePath as exc:
                return 'unsafe gate input: %s' % exc
    for rel, data in files.items():
        target = pathlib.Path(folder) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return None

def load(dirpath):
    """the outputs to render, the manifest they came from ('piece.json' or 'render.json') and, for a
    piece, its validated manifest (else None)"""
    piece, spec = pathlib.Path(dirpath) / 'piece.json', pathlib.Path(dirpath) / 'render.json'
    if piece.is_file() and spec.is_file():
        raise SystemExit('%s has both piece.json and render.json; piece.json outputs replace render.json, '
                         'so remove one' % dirpath)
    if piece.is_file():
        import library
        try:
            manifest = library.validate(dirpath)
            return manifest['outputs'], 'piece.json', manifest
        except library.LibraryError as exc:
            raise SystemExit('piece.json: %s' % exc)
    if not spec.is_file():
        raise SystemExit('no piece.json or render.json in %s (see `pixelate render --help`)' % dirpath)
    data = json.loads(spec.read_text())
    images = data.get('images') if isinstance(data, dict) else data
    if not images:
        raise SystemExit('render.json lists no images')
    for im in images:
        for k in ('name', 'frame'):
            if not im.get(k):
                raise SystemExit('every image in render.json needs "%s"' % k)
        if not (im.get('style') or im.get('era')):
            raise SystemExit('image %s needs "style" or "era" for the gate' % im['name'])
    return images, 'render.json', None

def _tail(text, n=6):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return '\n'.join(lines[-n:])

def gate_args(im):
    args = ['check', im['frame'], '--scale', str(im.get('scale', 1))]
    for key, flag in GATE_FLAGS:
        if im.get(key):
            args += [flag, str(im[key])]
    if im.get('brief'):
        args += ['--brief', im['brief'], '--image', im['name']]
    return args

def logging():
    """PIXELATE_NO_LOG=1 turns off every log a render writes: the run log and the judge and critique
    corpus records"""
    return not os.environ.get('PIXELATE_NO_LOG')

def piece_env(knobs=None):
    """the environment piece commands run in: the kit's tools/ importable, `pixelate` on PATH and
    PIXELATE_KIT the kit root (never an inherited value), so a checked-in program runs from any folder
    without a hard-coded kit path or an exported variable. PIXELATE_KNOBS is knobs, the path of the
    file `--set` wrote, and never an inherited value: without it the commands draw the defaults"""
    env = dict(os.environ, PIXELATE_KIT=str(KIT))
    env.pop(knob_helper().ENV, None)
    if knobs:
        env[knob_helper().ENV] = str(knobs)
    for key, path in (('PYTHONPATH', KIT / 'tools'), ('PATH', KIT)):
        env[key] = os.pathsep.join(filter(None, (str(path), env.get(key))))
    return env

@contextlib.contextmanager
def knob_file(chosen):
    """(path, bytes) of a new read-only file holding chosen, the --set values, as JSON, in a private
    temporary folder outside the piece; the folder is deleted on exit"""
    data = json.dumps(chosen, sort_keys=True, ensure_ascii=False).encode('utf-8')
    with tempfile.TemporaryDirectory(prefix='pixelate-knobs-') as folder:
        path = os.path.join(folder, 'knobs.json')
        f = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o400)
        with os.fdopen(f, 'wb') as fh:
            fh.write(data)
        yield path, data

def run_command(command, cwd, env=None, timeout=None):
    """run one shell command; with a timeout, kill its whole process group when time runs out. The
    shell is not a sandbox: run only trusted commands"""
    t = time.time()
    proc = subprocess.Popen(command, shell=True, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=timeout is not None)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return {'ok': False, 'seconds': round(time.time() - t, 1), 'error': 'timed out after %ss' % timeout}
    rec = {'ok': proc.returncode == 0, 'seconds': round(time.time() - t, 1)}
    if proc.returncode:
        rec['error'] = _tail(err or out)
    return rec

def technical_gate(d, im):
    """{'gate': ..., 'era': ...}: the image gate (`pixelate check`) on im's frame in d and, when im names
    an era, the era check. A technical result, not a quality judgment."""
    rec = {}
    g = subprocess.run(PIXELATE + gate_args(im), cwd=d, capture_output=True, text=True)
    fails = [l.strip() for l in g.stdout.splitlines() if re.match(r'^\s*FAIL\b', l)]
    passes = [l for l in g.stdout.splitlines() if re.match(r'^\s*PASS\b', l)]
    rec['gate'] = {'ok': g.returncode == 0, 'pass': len(passes), 'fail': fails[:8]}
    # A failing gate that finished exits 1 with its summary as the last line and no traceback; any
    # other failure, such as a crash after the summary, is an error, not a gate verdict.
    last = (g.stdout.strip().splitlines() or [''])[-1]
    if g.returncode and (g.returncode != 1 or not re.match(r'FAIL: \d+ of \d+ checks', last)
                         or 'Traceback (most recent call last)' in g.stderr):
        rec['gate']['error'] = _tail(g.stderr or g.stdout)
    if im.get('era'):
        # `pixelate era` prints violations and exits 0; nonzero only when it could not run. Era
        # legality is the gate's own --era lines above.
        e = subprocess.run(PIXELATE + ['era', im['frame'], '--era', im['era']], cwd=d, capture_output=True, text=True)
        rec['era'] = {'ok': e.returncode == 0, 'report': _tail(e.stdout, 3)}
    return rec

def judge(d, im, frame):
    """`pixelate judge` on frame (a path from d), the overlay beside im's frame in d"""
    overlay = (d / im['frame']).with_suffix('.judge.png')
    jargs = ['judge', str(frame), '--json', '--overlay', str(overlay.relative_to(d))]
    if logging():
        jargs += ['--log', '--note', 'render']
    if im.get('scale'):
        jargs += ['--scale', str(im['scale'])]
    if im.get('judge_ignore'):
        jargs += ['--ignore', im['judge_ignore']]
    j = subprocess.run(PIXELATE + jargs, cwd=d, capture_output=True, text=True)
    if j.returncode:
        return {'error': _tail(j.stderr or j.stdout)}
    found = json.loads(j.stdout)['defects']
    return {'defects': [{k: x[k] for k in ('id', 'kind', 'box', 'severity')} for x in found],
            'overlay': str(overlay.relative_to(d)) if found else None}

def critique_frame(d, frame, brief, out=None):
    """`pixelate critique --run` on frame with brief (paths from d); out: the folder for its
    thumbnails, overlay and saved critique, else beside the frame"""
    c = subprocess.run(PIXELATE + ['critique', str(frame), '--brief', str(brief), '--run']
                       + (['--out', str(out)] if out else []) + (['--log'] if logging() else []),
                       cwd=d, capture_output=True, text=True)
    saved = re.search(r'^saved: (.+)$', c.stdout, re.M)
    grade = re.search(r'^GRADE:\s*([ABC])', c.stdout, re.M)
    rec = {'ok': c.returncode == 0, 'grade': grade.group(1) if grade else None,
           'file': saved.group(1) if saved else None}
    if c.returncode:
        rec['error'] = _tail(c.stderr or c.stdout, 2)
    return rec

def run_group(d, group, env):
    """delete every declared frame and file of group, the piece outputs that share one run command,
    from d, then run that command once: its run record. A path that cannot be deleted without
    following a link fails the command unrun"""
    try:
        for out in group:
            remove_regular(d, out.get('frame') or out['file'])
    except UnsafePath as exc:
        return {'ok': False, 'seconds': 0.0, 'error': 'unsafe output: %s' % exc}
    return run_command(group[0]['run'], d, env)

def render_one(d, im, run=True, critique=False, env=None, piece=False, ran=None, distance=None):
    """ran: the run record of im's command, already run for a piece (see run_group); distance: for a
    piece, the function from the frame bytes to rec['distance'] (see tools/distance.py), given the bytes
    that are hashed; piece: im is a piece.json output, so its frame and gate inputs must be regular files reached
    without a link; its frame is read once, the gate and era check run on a private copy of those
    bytes and of the gate inputs, and the judge and critique read the same bytes, so the recorded hash
    is of the bytes they checked. With logging on, the frame the judge and critique logs name is kept under
    DIR/.pixelate/snapshots (rec['snapshot']), and so is the brief the critique reads"""
    rec = {'name': im['name'], 'frame': im['frame']}
    if ran is not None:
        rec['run'] = dict(ran)
        if not ran['ok']:
            return rec
    elif run and im.get('run'):
        rec['run'] = run_command(im['run'], d, env)
        if not rec['run']['ok']:
            return rec
    if piece:
        try:
            data = read_regular(d, im['frame'])
        except FileNotFoundError:
            rec['error'] = 'frame not found: %s' % im['frame']
            return rec
        except UnsafePath as exc:
            rec['error'] = 'unsafe frame: %s' % exc
            return rec
        if distance:
            rec['distance'] = distance(data)
        with tempfile.TemporaryDirectory(prefix='pixelate-render-') as folder:
            folder = pathlib.Path(folder)
            unsafe = gate_snapshot(folder, im, data, d)
            if unsafe:
                rec['error'] = unsafe
                return rec
            frame = folder / im['frame']
            if logging():
                try:
                    rec['snapshot'] = keep_snapshot(d, data, frame.name)
                except UnsafePath as exc:
                    rec['error'] = 'unsafe snapshot: %s' % exc
                    return rec
                frame = d / rec['snapshot']
            rec['sha256'] = hashlib.sha256(data).hexdigest()
            rec.update(technical_gate(folder, im))
            rec['judge'] = judge(d, im, frame)
            if critique and im.get('brief'):
                # The brief the gate read; a missing one is left for critique to report.
                brief = folder / im['brief']
                try:
                    if logging() and brief.is_file():
                        brief = d / keep_snapshot(d, brief.read_bytes(), brief.name)
                except UnsafePath as exc:
                    rec['critique'] = {'ok': False, 'grade': None, 'file': None, 'error': 'unsafe snapshot: %s' % exc}
                else:
                    rec['critique'] = critique_frame(d, frame, brief, (d / im['frame']).parent)
        return rec
    if (d / im['frame']).is_file():
        data = (d / im['frame']).read_bytes()
        rec['sha256'] = hashlib.sha256(data).hexdigest()   # the gate and judge reopen the path
        rec.update(technical_gate(d, im))
        rec['judge'] = judge(d, im, im['frame'])
    else:
        rec['error'] = 'frame not found: %s' % im['frame']
        return rec
    if critique and im.get('brief'):
        rec['critique'] = critique_frame(d, im['frame'], im['brief'])
    return rec

def render_file(d, out, run=True, env=None, ran=None):
    """hash the file an audio or export output writes, after running its command (or with ran, the
    run record it already has); these files are never gated"""
    rec = {'name': out['name'], 'kind': out['kind'], 'file': out['file']}
    if ran is not None:
        rec['run'] = dict(ran)
        if not ran['ok']:
            return rec
    elif run:
        rec['run'] = run_command(out['run'], d, env)
        if not rec['run']['ok']:
            return rec
    try:
        rec['sha256'] = hashlib.sha256(read_regular(d, out['file'])).hexdigest()
    except FileNotFoundError:
        rec['error'] = 'file not found: %s' % out['file']
    except UnsafePath as exc:
        rec['error'] = 'unsafe file: %s' % exc
    return rec

def line(rec):
    parts = [rec['name']]
    if 'run' in rec:
        parts.append('run ok %.1fs' % rec['run']['seconds'] if rec['run']['ok'] else 'RUN FAILED')
    if rec.get('error'):
        parts.append(rec['error'])
    if 'file' in rec and 'sha256' in rec:
        parts.append('%s %s (not gated)' % (rec['kind'], rec['file']))
    if 'gate' in rec:
        g = rec['gate']
        parts.append('gate PASS (%d lines)' % g['pass'] if g['ok'] else 'gate FAIL: ' + ('; '.join(g['fail'][:3]) or g.get('error', '')))
    if 'era' in rec:
        parts.append('era ok' if rec['era']['ok'] else 'era FAIL')
    if 'judge' in rec:
        jd = rec['judge']
        if 'error' in jd:
            parts.append('judge error')
        else:
            ks = [x['kind'] for x in jd['defects']]
            parts.append('judge: ' + (', '.join('%d %s' % (ks.count(k), k) for k in dict.fromkeys(ks)) if ks else 'clean')
                         + (' (overlay %s)' % jd['overlay'] if jd.get('overlay') else ''))
    if 'critique' in rec:
        cr = rec['critique']
        parts.append('critique %s' % (cr['grade'] or '?') if cr['ok'] else 'critique failed')
    if rec.get('distance') and distance_helper().line(rec['distance']):
        parts.append(distance_helper().line(rec['distance']))
    return ' | '.join(parts)

def ok(rec):
    if 'file' in rec:
        return rec.get('run', {'ok': True})['ok'] and 'sha256' in rec
    return rec.get('run', {'ok': True})['ok'] and not rec.get('error') and rec.get('gate', {}).get('ok', False) \
        and rec.get('era', {'ok': True})['ok']

def log_run(d, recs, piece=False, knobs=None, base=None):
    """append this render to DIR/.pixelate/runs.jsonl (next to the judge log), the run record the
    library's flywheel is built from. piece: the log is opened without following a link, and an
    error is returned instead of writing through one. knobs: what --set gave the commands; base: the
    remix's base as tools/distance.py looked it up"""
    if not logging():
        return None
    sys.path.insert(0, str(KIT / 'tools'))
    from version import VERSION
    images, files = [], []
    for r in recs:
        if 'file' in r:
            files.append({'name': r['name'], 'kind': r['kind'], 'file': r['file'], 'sha256': r.get('sha256'),
                          'run_ok': r.get('run', {'ok': True})['ok'], 'ok': ok(r)})
            continue
        images.append({'name': r['name'], 'frame': r['frame'], 'sha256': r.get('sha256'),
                       'run_ok': r.get('run', {'ok': True})['ok'], 'gate_ok': r.get('gate', {}).get('ok'),
                       'gate_fail': len(r.get('gate', {}).get('fail', [])),
                       'judge': sorted({x['kind'] for x in r.get('judge', {}).get('defects', [])}),
                       'grade': r.get('critique', {}).get('grade'), 'ok': ok(r)})
        if 'snapshot' in r:
            images[-1]['snapshot'] = r['snapshot']
        if 'distance' in r:
            images[-1]['distance'] = r['distance']
    record = {'type': 'render', 'time': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
              'kit': VERSION, 'dir': d.name, 'images': images, 'ok': all(i['ok'] for i in images + files)}
    if files:
        record['files'] = files
    if knobs:
        record['knobs'] = knobs
    if base:
        record['base'] = {k: base[k] for k in ('id', 'library', 'status', 'piece_sha256', 'error') if k in base}
    text = json.dumps(record, ensure_ascii=False) + '\n'
    if not piece:
        p = d / '.pixelate' / 'runs.jsonl'
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('a', encoding='utf-8') as fh:
            fh.write(text)
        return None
    try:
        fd = _folder(d, '.pixelate')
        try:
            f = os.open('runs.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
                        | os.O_CLOEXEC, 0o644, dir_fd=fd)
        except OSError as exc:
            raise UnsafePath('.pixelate/runs.jsonl: a link or not a regular file (%s)' % exc.strerror) from exc
        finally:
            os.close(fd)
    except UnsafePath as exc:
        return 'run log not written: %s' % exc
    with os.fdopen(f, 'a', encoding='utf-8') as fh:
        if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
            return 'run log not written: .pixelate/runs.jsonl: not a regular file'
        fh.write(text)
    return None

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pixelate render', description=(__doc__ or '').split('\n\n')[1])
    ap.add_argument('dir')
    ap.add_argument('--image', default=None, help='only this image (with piece.json: this output)')
    ap.add_argument('--no-run', action='store_true', help='skip the draw commands; gate and judge what is there')
    ap.add_argument('--critique', action='store_true', help='also run the art director (pixelate critique --run)')
    ap.add_argument('--set', action='append', default=[], metavar='KNOB=VALUE',
                    help='render a variant with this knob value: script, engine and pack pieces (repeatable; see tools/piece.py)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    d = pathlib.Path(a.dir).resolve()
    outputs, source, manifest = load(d)
    knobs, chosen = None, {}
    if a.set:
        if source == 'render.json':
            ap.error('--set needs a piece.json that declares knobs; render.json images take no knobs')
        if a.no_run:
            ap.error('--set cannot be used with --no-run: the frames there were not drawn with those knobs')
        helper = knob_helper()
        try:
            chosen = helper.parse_sets(manifest['knobs'], a.set)
        except helper.KnobError as exc:
            ap.error(str(exc))
    outputs = [o for o in outputs if not a.image or o['name'] == a.image]
    if not outputs:
        raise SystemExit('no %s named %s in %s' % ('output' if source == 'piece.json' else 'image', a.image, source))
    base = None
    if source == 'render.json':
        recs = [render_one(d, im, not a.no_run, a.critique) for im in outputs]
    else:
        assert manifest is not None  # load returns the manifest of every piece.json
        # Read before any command runs, from the kit library; the base's code never runs.
        dist = distance_helper()
        base = dist.lookup(d, manifest)

        def measure(o):
            if base is not None:
                return lambda data: dist.measure(data, o, manifest['canvas'], manifest['request'], base)
            return None
        with contextlib.ExitStack() as stack:
            path = None
            if a.set:
                path, data = stack.enter_context(knob_file(chosen))
                # What the commands were given, not proof that the program read it.
                knobs = {'set': chosen, 'merged': knob_helper().merge(manifest['knobs'], chosen),
                         'sha256': hashlib.sha256(data).hexdigest()}
            env = piece_env(path)
            ran, recs = {}, []
            for o in outputs:
                if not a.no_run and o['run'] not in ran:
                    ran[o['run']] = run_group(d, [x for x in outputs if x['run'] == o['run']], env)
                if o['kind'] == 'image':
                    rec = render_one(d, o, False, a.critique, env, piece=True, ran=ran.get(o['run']), distance=measure(o))
                    if 'distance' not in rec:
                        rec['distance'] = dist.unavailable(
                            base, o['name'], 'not a remix: piece.json names no lineage.remixed_from' if base is None
                            else 'no frame was read: ' + (rec.get('error') or 'its run command failed'))
                    recs.append(dict(rec, kind='image'))
                else:
                    recs.append(render_file(d, o, False, env, ran=ran.get(o['run'])))
        if knobs:
            for r in recs:
                r['knobs'] = knobs
    (d / 'render-report.json').write_text(json.dumps(recs, indent=1))
    unlogged = log_run(d, recs, piece=source == 'piece.json', knobs=knobs, base=base)
    if unlogged:
        print(unlogged, file=sys.stderr)
    if a.json:
        print(json.dumps(recs, indent=1))
    else:
        if knobs:
            print('knobs: %s (file sha256 %s)' % (', '.join('%s=%s' % (k, knob_helper().spelling(v))
                                                          for k, v in knobs['merged'].items()), knobs['sha256']))
        for r in recs:
            print(line(r))
        print('report: %s' % (d / 'render-report.json'))
    sys.exit(0 if all(ok(r) for r in recs) and not unlogged else 1)

if __name__ == '__main__':
    main()
