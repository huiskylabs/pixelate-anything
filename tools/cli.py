#!/usr/bin/env python3
"""pixelate: one command for everything in pixelate-anything.

  pixelate route "REQUEST" [--brief [STYLE] -o brief.md] [--size WxH] [--scale N]   pick a style, expand to a brief
  pixelate route --lint brief.md         self-critique a brief before showing it
  pixelate style --list                  every style, one line each
  pixelate style NAME                    one style's card: rules, light, budgets, craft limits, techniques, check
  pixelate tools                         every topic and module of the kit, one line each
  pixelate tools TOPIC [--style S]       techniques for a subject (rain, 雨, fog, water, small lights)
  pixelate tools MODULE[.func]           a module's functions with signatures, or one function's docstring
  pixelate image IMG -o OUT [...]        photo or art -> clean pixel art          (guides/pixelate.md)
  pixelate palette extract|ramps|show|js|list ...   palettes                      (guides/palettes.md)
  pixelate assets PACK                   export sprites, sheets, GIFs, tilemaps   (guides/assets.md)
  pixelate topx IMG PALETTE [NAME]       a PNG as an editable .px sprite (palette: .json/.hex/preset)
  pixelate era IMG --era nes|gameboy|snes|genesis|gba|pico-8|neogeo|cga [-o OUT]   check (or force) console-era limits
  pixelate sprites SCENE                 generate sprites.js from SCENE/art/*.py
  pixelate new scene|music|assets DIR    copy a library starter into a new piece folder (DIR's name is its id)
  pixelate remix PIECE DIR --request "..."   copy a library piece to DIR, render the unedited copy once, write REMIX.md
                                         (runs the trusted piece's commands without a sandbox)
  pixelate shot SCENE t [t...] [--grid]  preview frames                            (guides/scenes.md)
  pixelate check SCENE [--page]          palettes, timing, loop seam, page
  pixelate check FRAME.png --style S --scale N [--pal P] [--pre IMG] [--actor MASK] [--used op,op] [--brief B]   the delivery gate
  pixelate check BLOCKIN.png --blockin --brief brief.md [--scale N]   the greyscale block-in, before drawing
                         [--scene NAME] [--era ERA] [--brief brief.md] [--budget 'RULE BOUND (reason)']
  pixelate judge FRAME.png [--overlay OUT.png] [--json] [--log]   locate what the gate passes and an art director rejects
  pixelate reference PHOTO -o reference.json [--marks reference.json]   correctable photo evidence + overlay (experimental)
  pixelate render DIR [--image NAME] [--critique]   draw, gate, era-check and judge every image in DIR/piece.json or DIR/render.json
                         [--set KNOB=VALUE ...]   a variant from the piece's declared knobs (script, engine and pack pieces)
  pixelate deliver DIR [--set KNOB=VALUE ...] [--timeout S]   render every output once more, require each image's gate,
                                         package the outputs and DELIVERY.md (facts written by the script) in DIR/dist/delivery
                                         (runs the trusted piece's commands without a sandbox; runs no critique)
  pixelate deliver DIR --verify          check DELIVERY.md's facts, fingerprint and hashes (runs no piece code)
  pixelate find "REQUEST" [--mode M] [--json]   the closest library pieces, or a starter (static: runs no piece code)
  pixelate library list | show ID | recipes [NAME] | index   browse catalog and declared recipe users (static)
  pixelate library test [ID...] [--quick]      render trusted pieces in temporary copies and compare golden 1x frames
  pixelate library add DIR [--status study|accepted|reviewed] --trust-local-code   run a trusted local piece twice,
                                         stage it with 1x goldens and rebuild the index (NO sandbox; never in PR CI)
  pixelate gallery [--check]              generate/check index-driven README cards and static docs/gallery page
  pixelate critique [FRAME.png] --brief brief.md [--block B] [--prev P] [--role lead|composition|lighting|set|character] [--consult NOTE.md]   independent visual review (--run: run it and save the critique)
  pixelate critique-music TRACK.wav --brief brief.md [--prev LAST.md]   prompt an independent listening agent after the music gate
  pixelate review record --brief B [--frame F] --critique REPORT   bind external lead critique to artifact
  pixelate review status --brief B [--frame F]   READY only for matching A evidence
  pixelate check TRACK.wav [--style S] [--use loop|showcase|song] [--bpm N] [--key K] [--sheet P]   the music gate
  pixelate build SCENE [--release]       one self-contained HTML page
  pixelate audio SCENE out.{wav,ogg,flac,mp3}   one seamless loop of the music     (guides/music.md)
  pixelate video SCENE out.mp4 [--scale S] [--audio loop.wav]   crisp MP4
  pixelate gif SCENE out.gif [--scale S] [--fps 15] [--frames K0:K1]
  pixelate doctor                        check node, ffmpeg, python packages, Chromium
  pixelate --version                     the kit's version
  pixelate mcp                           run the MCP server (stdio) for any MCP client
  pixelate setup [--yes] [--only claude,cursor,codex,gemini]   register MCP + skill with your agents

What each mode needs: image, palette and assets modes need Python with pillow and numpy only;
scenes add node; video and GIF add ffmpeg; music and the page check add Playwright Chromium.
"""
import argparse, json, os, pathlib, runpy, shutil, subprocess, sys, tempfile

TOOLS = pathlib.Path(__file__).resolve().parent
KIT = TOOLS.parent
SCRIPTS = {'image': 'pixelate.py', 'palette': 'palette.py', 'assets': 'assets.py', 'sprites': 'gen_sprites.py', 'era': 'era.py',
           'shot': 'shot.py', 'check': 'check.py', 'build': 'build.py', 'audio': 'render_audio.py',
           'route': 'route.py', 'style': 'styles.py', 'tools': 'kit.py', 'critique': 'critique.py', 'critique-music': 'critique_music.py',
           'judge': 'judge.py', 'render': 'render.py', 'reference': 'reference.py', 'gallery': 'gallery.py'}
STARTERS = {'scene': 'starter-scene-loop', 'music': 'starter-music', 'assets': 'starter-assets'}
GUIDES = {'scene': 'scenes', 'music': 'music', 'assets': 'assets'}
NEW_USAGE = '''usage: pixelate new KIND DIR   (kinds: %s)

Copies the kind's library starter into the new folder DIR as a piece whose id is DIR's name
(a lowercase slug such as my-scene):
  %s
DIR must not exist, or be an empty folder that is not a link. The copy keeps the starter's sources,
media, history and 1x goldens, but no generated outputs or .pixelate run data. It is a plain copy: it
records no lineage and renders nothing, unlike `pixelate remix STARTER DIR --request ...`. The library
plan makes `new` an alias of remix later; it is not one yet.''' % (
    ', '.join(STARTERS), '\n  '.join('%-7s library/%s' % item for item in STARTERS.items()))

def run(script, args):
    sys.argv = [str(TOOLS / script)] + args
    sys.path.insert(0, str(TOOLS))
    runpy.run_path(str(TOOLS / script), run_name='__main__')

def new(kind, dest):
    """Copy a library starter to `dest` as a piece whose id is the folder name; validate the copy, then move
    it into place, so a failure leaves `dest` as it was."""
    sys.path.insert(0, str(TOOLS))
    import library
    if kind not in STARTERS:
        sys.exit('kinds: ' + ', '.join(STARTERS))
    dest = pathlib.Path(dest)
    if not library.SLUG.fullmatch(dest.name):
        sys.exit('%s: the folder name becomes the piece id; use a lowercase slug such as my-%s' % (dest, kind))
    if dest.is_symlink():
        sys.exit('%s is a symbolic link; choose a new folder' % dest)
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        sys.exit('%s exists and is not an empty folder' % dest)
    source = library.DEFAULT_LIBRARY / STARTERS[kind]
    try:
        manifest = library.validate(source)  # also rejects a link anywhere in the starter
    except library.LibraryError as exc:
        sys.exit('starter %s is invalid: %s' % (STARTERS[kind], exc))
    generated = {output.get('frame') or output['file'] for output in manifest['outputs']}

    def ignore(folder, entries):
        # Keep sources, media, history and out/golden; leave out run data and generated outputs.
        rel = pathlib.Path(folder).relative_to(source)
        return {entry for entry in entries
                if entry in ('.pixelate', 'dist', 'shots', '__pycache__', 'render-report.json')
                or (rel / entry).as_posix() in generated or (rel.as_posix() == 'out' and entry != 'golden')}
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        build = pathlib.Path(tempfile.mkdtemp(prefix='.%s-' % dest.name, dir=dest.parent))
    except OSError as exc:
        sys.exit('cannot create %s: %s' % (dest, exc))
    try:
        work = build / dest.name
        shutil.copytree(source, work, symlinks=True, ignore=ignore)
        manifest['id'] = dest.name
        (work / 'piece.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        try:
            library.validate(work)
        except library.LibraryError as exc:
            sys.exit('the copy of %s does not validate: %s' % (STARTERS[kind], exc))
        os.rename(work, dest)  # replaces only a missing path or an empty folder
    except OSError as exc:
        sys.exit('cannot create %s: %s' % (dest, exc))
    finally:
        shutil.rmtree(build, ignore_errors=True)
    print('created %s (piece id %s) as a copy of library/%s. Next: read guides/%s.md, then run its '
          'outputs with `pixelate render %s`.' % (dest, dest.name, STARTERS[kind], GUIDES[kind], dest))

def doctor():
    ok = True
    def line(good, what, fix=''):
        nonlocal ok
        ok &= good
        print(('ok   ' if good else 'MISS ') + what + ('' if good else '   -> ' + fix))
    for mod, fix in (('PIL', 'pip install pillow'), ('numpy', 'pip install numpy')):
        try:
            __import__(mod); line(True, 'python: ' + mod)
        except ImportError:
            line(False, 'python: ' + mod, fix)
    node = shutil.which('node')
    v = subprocess.run([node, '-v'], capture_output=True, text=True).stdout.strip() if node else ''
    line(bool(node) and int(v.lstrip('v').split('.')[0] or 0) >= 18, 'node %s (frames, scenes)' % v, 'install Node.js 18+')
    ff = shutil.which('ffmpeg')
    enc = subprocess.run([ff, '-hide_banner', '-encoders'], capture_output=True, text=True).stdout if ff else ''
    line('libx264' in enc, 'ffmpeg with libx264 (MP4, GIF, audio formats)', 'install ffmpeg (e.g. brew install ffmpeg)')
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        have = os.environ.get('PLAYWRIGHT_BROWSERS_PATH') or str(pathlib.Path.home() / '.cache' / 'ms-playwright')
        found = pathlib.Path(have).is_dir() and any(pathlib.Path(have).glob('chromium*'))
        line(False, 'python: playwright (only for music and page checks)',
             'pip install playwright' + ('   (Chromium is already in %s)' % have if found
                                         else ' && playwright install chromium'))
    else:
        try:
            with sync_playwright() as p:
                b = p.chromium.launch(); b.close()
            line(True, 'playwright chromium (soundtrack render, page check)')
        except Exception as e:
            line(False, 'playwright chromium (only for music and page checks)',
                 'playwright install chromium   (launch failed: %s)' % str(e).splitlines()[0][:80])
    try:
        __import__('mcp'); line(True, 'python: mcp (MCP server)')
    except ImportError:
        line(False, 'python: mcp (only for the MCP server)', 'pip install mcp')
    print('all good' if ok else 'image, palette and asset modes need only python; scenes need node; video needs ffmpeg')

def review(args):
    import review_status
    parser = argparse.ArgumentParser(prog='pixelate review')
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('record', 'status'):
        command = sub.add_parser(action)
        command.add_argument('--brief', required=True)
        command.add_argument('--frame', default='')
        if action == 'record':
            command.add_argument('--critique', required=True)
    options = parser.parse_args(args)
    if options.action == 'record':
        try:
            print(review_status.record(options.brief, options.critique, options.frame))
        except (review_status.ReviewError, OSError) as exc:
            print(f'NOT RECORDED: {exc}')
            return 1
        return 0
    ready, reason = review_status.status(options.brief, options.frame)
    print(reason)
    return 0 if ready else 1

def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] in ('-h', '--help', 'help'):
        print(__doc__); return
    cmd, rest = a[0], a[1:]
    if cmd in ('--version', 'version'):
        sys.path.insert(0, str(TOOLS))
        from version import VERSION
        print('pixelate-anything %s' % VERSION); return
    if cmd in SCRIPTS:
        run(SCRIPTS[cmd], rest)
    elif cmd == 'review':
        sys.path.insert(0, str(TOOLS))
        sys.exit(review(rest))
    elif cmd == 'find':
        sys.path.insert(0, str(TOOLS))
        import library
        library.find_main(rest)
    elif cmd == 'library':
        sys.path.insert(0, str(TOOLS))
        import library
        library.main(rest, prog='pixelate library')
    elif cmd == 'remix':
        sys.path.insert(0, str(TOOLS))
        import remix
        sys.exit(remix.main(rest))
    elif cmd == 'deliver':
        sys.path.insert(0, str(TOOLS))
        import deliver
        sys.exit(deliver.main(rest))
    elif cmd == 'topx':
        run('assets.py', ['--topx'] + rest)
    elif cmd == 'video':
        run('render_video.py', rest)
    elif cmd == 'gif':
        run('render_video.py', [rest[0], '--gif'] + rest[1:])
    elif cmd == 'new':
        if rest[:1] in (['-h'], ['--help']):
            print(NEW_USAGE); return
        if len(rest) != 2:
            sys.exit(NEW_USAGE)
        new(rest[0], rest[1])
    elif cmd == 'doctor':
        doctor()
    elif cmd == 'mcp':
        sys.path.insert(0, str(TOOLS))
        import mcp_server
        mcp_server.main()
    elif cmd == 'setup':
        sys.path.insert(0, str(TOOLS))
        import setup_agents
        setup_agents.main(rest)
    else:
        print(__doc__); sys.exit(1)

if __name__ == '__main__':
    main()
