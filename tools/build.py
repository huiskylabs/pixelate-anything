#!/usr/bin/env python3
"""Build a scene into one self-contained HTML page.

usage: build.py SCENE_DIR [--release] [--out PATH]

A scene directory holds:
  scene.json   {"title", "description", "alt", "files": [drawing files in load order]}
  config.js    const SCENE = {...}   (size, phases, slots, timing)
  music.js     const SCENE_MUSIC = {...}   (optional: no music.js, no soundtrack)
  ...the files listed in scene.json (palettes, sprites, drawing code with the scene hooks)

Load order: config.js, engine/core.js, engine/render.js, scene files, music.js,
engine/audio.js, engine/main.js. Debug builds (default) expose window.__dbg and
the ?t= / ?freeze=1 query parameters; --release strips them.
Output defaults to SCENE_DIR/dist/dev.html or SCENE_DIR/dist/<slug>.html.

Knobs: when SCENE_DIR is a library piece (references/piece.md) whose piece.json declares knobs, the
first line after 'use strict' is `const PIXELATE_KNOBS = Object.freeze({...});`, every knob at its
default or at the value set in the PIXELATE_KNOBS file (`pixelate render DIR --set`), checked by
tools/piece.py; the scene's scripts read PIXELATE_KNOBS.name. The same JS feeds frames, video, audio
and the page. A PIXELATE_KNOBS file with no piece.json is an error, never ignored.
"""
import json, os, pathlib, re, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = KIT / 'engine'

def manifest(scene):
    scene = pathlib.Path(scene)
    m = json.loads((scene / 'scene.json').read_text())
    m.setdefault('title', scene.name)
    m.setdefault('description', '')
    m.setdefault('alt', m['title'])
    return m

def part(path):
    return '/* ---- %s ---- */\n%s' % (path.name, path.read_text())

def knob_js(scene):
    """the PIXELATE_KNOBS constant of a scene that is a piece declaring knobs, else ''"""
    if __package__:
        from . import piece
    else:
        import piece
    if not (pathlib.Path(scene) / 'piece.json').exists():
        if os.environ.get(piece.ENV):
            raise SystemExit('%s is set, but %s has no piece.json declaring knobs' % (piece.ENV, scene))
        return ''
    try:
        merged = piece.knobs(scene)
        return piece.js_constant(merged) if merged else ''
    except piece.KnobError as exc:
        raise SystemExit('knobs: %s' % exc)

def scene_js(scene, with_audio=True, with_main=True):
    """Concatenated JS for the scene. Without audio/main it runs in Node for frame export."""
    scene = pathlib.Path(scene)
    m = manifest(scene)
    knobs = knob_js(scene)
    parts = [part(scene / 'config.js'), part(ENGINE / 'core.js'), part(ENGINE / 'render.js')]
    for f in m['files']:
        parts.append(part(scene / f))
    if with_audio and (scene / 'music.js').exists():
        parts += [part(scene / 'music.js'), part(ENGINE / 'audio.js')]
    if with_main:
        parts.append(part(ENGINE / 'main.js'))
    js = '\n'.join(parts)
    # one 'use strict' at the very top
    js = "'use strict';\n" + knobs + js.replace("'use strict';", '')
    return js

def build(scene, release=False, out=None):
    scene = pathlib.Path(scene)
    m = manifest(scene)
    js = scene_js(scene)
    if release:
        js = js.replace('const DEBUG_BUILD = true;', 'const DEBUG_BUILD = false;')
    esc = lambda s: s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')
    html = (ENGINE / 'shell.html').read_text()
    html = html.replace('@TITLE@', esc(m['title'])).replace('@DESCRIPTION@', esc(m['description'])).replace('@ALT@', esc(m['alt']))
    html = html.replace('/*@JS@*/', js)
    if out is None:
        slug = re.sub(r'[^a-z0-9]+', '-', m['title'].lower()).strip('-') or 'scene'
        out = scene / 'dist' / ('%s.html' % slug if release else 'dev.html')
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print('wrote', out, len(html), 'bytes')
    return out

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0].startswith('-'):
        print(__doc__); sys.exit(1)
    out = None
    if '--out' in a:
        i = a.index('--out'); out = a[i + 1]; del a[i:i + 2]
    build(a[0], release='--release' in a, out=out)
