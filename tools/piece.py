#!/usr/bin/env python3
"""knobs(): the settings a piece program reads, its `piece.json` defaults merged with the values set.

    from piece import knobs
    k = knobs()             # {'time': 'day', 'seed': 17}, or the values `pixelate render . --set ...` chose

`pixelate render DIR --set time=dusk --set seed=4` checks each value against the manifest, writes the
chosen values as a JSON object to a temporary file outside DIR and passes its absolute path in
PIXELATE_KNOBS to the piece's commands only; the file is deleted after the render. Without --set, and
in `pixelate library test`, PIXELATE_KNOBS is removed from the commands' environment, so knobs()
returns the defaults whatever the caller exported. knobs() reads the manifest from the folder the
command runs in (the piece root) and checks the file again: it must be an absolute path to a regular
file owned by this user and writable by no one else, opened without following a link, holding a JSON
object of declared knob names and values of the declared type. Anything else raises KnobError, so a
program never draws with a value its manifest does not allow.
"""
import json, os, pathlib, re, stat

ENV = 'PIXELATE_KNOBS'
MAX_SET = 64 * 1024
# The integers JSON carries exactly to every runtime, JavaScript included.
INT_LIMIT = 2 ** 53 - 1
INT = re.compile(r'(0|-?[1-9][0-9]*)\Z')


class KnobError(ValueError):
    """a knob setting that does not fit the piece's manifest, or an unsafe PIXELATE_KNOBS file"""


def spelling(value):
    """how --set names a declared enum value: a string as it is, any other scalar as JSON (true, 3, 0.5)"""
    return value if isinstance(value, str) else json.dumps(value)


def check_value(name, knob, value):
    """value, when it is one knob may take: a declared enum value of the same JSON type, or an
    integer within INT_LIMIT for an int knob"""
    if 'values' in knob:
        if not any(type(v) is type(value) and v == value for v in knob['values']):
            raise KnobError(f"knob {name}: {json.dumps(value)} is not one of {json.dumps(knob['values'])}")
    elif type(value) is not int or abs(value) > INT_LIMIT:
        raise KnobError(f'knob {name}: expected an integer from -{INT_LIMIT} to {INT_LIMIT}, got {json.dumps(value)}')
    return value


def parse_sets(spec, sets):
    """{name: typed value} from `--set NAME=VALUE` strings, checked against spec, a manifest's knobs.
    Each name must be declared and set once; an enum value is matched by its spelling(), an int
    value must be a plain decimal integer"""
    chosen = {}
    for item in sets:
        name, sep, raw = item.partition('=')
        if not sep or not name:
            raise KnobError(f'--set {item!r}: expected NAME=VALUE')
        if name not in spec:
            raise KnobError(f"--set {name}: no such knob; the piece declares {', '.join(sorted(spec)) or 'none'}")
        if name in chosen:
            raise KnobError(f'--set {name}: set more than once')
        knob = spec[name]
        if 'values' in knob:
            matches = [v for v in knob['values'] if spelling(v) == raw]
            if not matches:
                raise KnobError(f"--set {name}={raw}: expected one of {', '.join(spelling(v) for v in knob['values'])}")
            if len(matches) > 1:
                raise KnobError(f'--set {name}={raw}: matches more than one declared value {json.dumps(matches)}')
            chosen[name] = matches[0]
        else:
            if not INT.fullmatch(raw):
                raise KnobError(f'--set {name}={raw}: expected a decimal integer')
            chosen[name] = check_value(name, knob, int(raw))
    return chosen


def merge(spec, chosen):
    """every knob of spec at its default, unless chosen sets it"""
    return {name: chosen.get(name, knob['default']) for name, knob in spec.items()}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise KnobError(f'{ENV}: duplicate key {key}')
        result[key] = value
    return result


def _nonfinite(value):
    raise KnobError(f'{ENV}: nonfinite JSON number {value}')


def read_set(path, spec):
    """the values in the PIXELATE_KNOBS file at path, each checked against spec"""
    if not os.path.isabs(path):
        raise KnobError(f'{ENV}: expected an absolute path, got {path!r}')
    try:
        # O_NONBLOCK: a pipe planted at the path must not hang the program.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        raise KnobError(f'{ENV}: {path}: missing, a link or unreadable ({exc.strerror})') from exc
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        os.close(fd)
        raise KnobError(f'{ENV}: {path}: not a regular file')
    with os.fdopen(fd, 'rb') as fh:
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise KnobError(f'{ENV}: {path}: must be owned by this user and writable by no one else')
        data = fh.read(MAX_SET + 1)
    if len(data) > MAX_SET:
        raise KnobError(f'{ENV}: {path}: larger than {MAX_SET} bytes')
    try:
        chosen = json.loads(data.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_nonfinite)
    except KnobError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise KnobError(f'{ENV}: {path}: invalid JSON ({exc})') from exc
    if not isinstance(chosen, dict):
        raise KnobError(f'{ENV}: {path}: expected a JSON object of knob values')
    for name, value in chosen.items():
        if name not in spec:
            raise KnobError(f"{ENV}: no such knob {name}; the piece declares {', '.join(sorted(spec)) or 'none'}")
        check_value(name, spec[name], value)
    return chosen


def manifest_knobs(root='.'):
    """the checked `knobs` object of the piece.json in root"""
    import library
    root = pathlib.Path(root).absolute()
    try:
        manifest = library.read_manifest(root)
        if not isinstance(manifest, dict) or 'knobs' not in manifest:
            raise library.LibraryError('piece.json: expected an object with knobs')
        library.check_knobs(root, manifest['knobs'])
    except library.LibraryError as exc:
        raise KnobError(str(exc)) from exc
    return manifest['knobs']


def knobs(root='.'):
    """{name: value} for every knob root's piece.json declares: its default, or the value the
    PIXELATE_KNOBS file sets. root defaults to the folder the command runs in, the piece root"""
    spec = manifest_knobs(root)
    path = os.environ.get(ENV)
    return merge(spec, read_set(path, spec) if path else {})
