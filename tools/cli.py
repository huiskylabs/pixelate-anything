#!/usr/bin/env python3
"""pixelate: one command for everything in pixelate-anything.

  pixelate image IMG -o OUT [...]        photo or art -> clean pixel art          (guides/pixelate.md)
  pixelate palette extract|ramps|show|js|list ...   palettes                      (guides/palettes.md)
  pixelate assets PACK                   export sprites, sheets, GIFs, tilemaps   (guides/assets.md)
  pixelate topx IMG PALETTE [NAME]       a PNG as an editable .px sprite (palette: .json/.hex/preset)
  pixelate sprites SCENE                 generate sprites.js from SCENE/art/*.py
  pixelate new scene|music|assets DIR    start a project from a template
  pixelate shot SCENE t [t...] [--grid]  preview frames                            (guides/scenes.md)
  pixelate check SCENE [--page]          palettes, timing, loop seam, page
  pixelate build SCENE [--release]       one self-contained HTML page
  pixelate audio SCENE out.{wav,ogg,flac,mp3}   one seamless loop of the music     (guides/music.md)
  pixelate video SCENE out.mp4 [--scale S] [--audio loop.wav]   crisp MP4
  pixelate gif SCENE out.gif [--scale S] [--fps 15] [--frames K0:K1]
  pixelate doctor                        check node, ffmpeg, python packages, Chromium
  pixelate mcp                           run the MCP server (stdio) for any MCP client
  pixelate setup [--yes] [--only claude,cursor,codex,gemini]   register MCP + skill with your agents
"""
import os, pathlib, runpy, shutil, subprocess, sys

TOOLS = pathlib.Path(__file__).resolve().parent
KIT = TOOLS.parent
SCRIPTS = {'image': 'pixelate.py', 'palette': 'palette.py', 'assets': 'assets.py', 'sprites': 'gen_sprites.py',
           'shot': 'shot.py', 'check': 'check.py', 'build': 'build.py', 'audio': 'render_audio.py'}
TEMPLATES = {'scene': 'starter', 'music': 'music', 'assets': 'assets'}

def run(script, args):
    sys.argv = [str(TOOLS / script)] + args
    sys.path.insert(0, str(TOOLS))
    runpy.run_path(str(TOOLS / script), run_name='__main__')

def new(kind, dest):
    if kind not in TEMPLATES:
        sys.exit('kinds: ' + ', '.join(TEMPLATES))
    dest = pathlib.Path(dest)
    if dest.exists() and any(dest.iterdir()):
        sys.exit('%s exists and is not empty' % dest)
    shutil.copytree(KIT / 'templates' / TEMPLATES[kind], dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('dist', 'shots', 'out', '__pycache__'))
    print('created %s from templates/%s. Next: read guides/%s.md' % (dest, TEMPLATES[kind], {'scene': 'scenes', 'music': 'music', 'assets': 'assets'}[kind]))

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
        with sync_playwright() as p:
            b = p.chromium.launch(); b.close()
        line(True, 'playwright chromium (soundtrack render, page check)')
    except Exception:
        line(False, 'playwright chromium (only for music and page checks)', 'pip install playwright && playwright install chromium')
    try:
        __import__('mcp'); line(True, 'python: mcp (MCP server)')
    except ImportError:
        line(False, 'python: mcp (only for the MCP server)', 'pip install mcp')
    print('all good' if ok else 'image, palette and asset modes need only python; scenes need node; video needs ffmpeg')

def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] in ('-h', '--help', 'help'):
        print(__doc__); return
    cmd, rest = a[0], a[1:]
    if cmd in SCRIPTS:
        run(SCRIPTS[cmd], rest)
    elif cmd == 'topx':
        run('assets.py', ['--topx'] + rest)
    elif cmd == 'video':
        run('render_video.py', rest)
    elif cmd == 'gif':
        run('render_video.py', [rest[0], '--gif'] + rest[1:])
    elif cmd == 'new':
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
