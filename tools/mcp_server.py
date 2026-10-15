#!/usr/bin/env python3
"""pixelate-anything MCP server (stdio). Run with:  pixelate mcp

Exposes the same core as the CLI as typed tools. Preview tools return images, so the
agent can look at its own work: that is the main quality lever. File tools let clients
without a shell write palettes, sprites and scene code.

Paths are relative to the workspace: $PIXELATE_WORKSPACE, else the directory the server
was started in. Absolute paths are accepted for reading (an image to pixelate); writes
through write_file stay inside the workspace.
"""
import json, os, pathlib, subprocess, sys

TOOLS = pathlib.Path(__file__).resolve().parent
KIT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
WORK = pathlib.Path(os.environ.get('PIXELATE_WORKSPACE') or os.getcwd()).resolve()

try:                                    # mcp 2.x
    from mcp.server.mcpserver import MCPServer as Server, Image
except ImportError:                     # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server, Image

GUIDES = {p.stem: p for p in sorted((KIT / 'guides').glob('*.md'))}
GUIDES.update({'craft': KIT / 'references' / 'craft.md', 'scene-contract': KIT / 'references' / 'scene-contract.md',
               'skill': KIT / 'SKILL.md'})

INSTRUCTIONS = """pixelate-anything: hand-crafted pixel art for agents.
Modes: pixelate an image (pixelate_image), palettes (palette), sprites/characters/items/tilesets
(new_project kind=assets, write .px files, export_assets), scenes and animated loops with a
generative soundtrack (new_project kind=scene, preview_scene, check_scene, build_page,
render_audio, render_video, render_gif), and music on its own (new_project kind=music, render_audio).
Start every task by reading guide(name) for its mode ('pixelate', 'palettes', 'assets', 'scenes',
'music') and guide('craft') before drawing. Look at every preview image you get back and fix what
looks wrong before going on: the art is only as good as that loop. Paths are relative to the workspace."""

server = Server('pixelate-anything', instructions=INSTRUCTIONS)

def P(p, write=False):
    q = pathlib.Path(p)
    q = (q if q.is_absolute() else WORK / q).resolve()
    if write and WORK not in q.parents and q != WORK:
        raise ValueError('writes must stay inside the workspace: %s' % WORK)
    return q

def cli(*args, timeout=3600):
    r = subprocess.run([sys.executable, str(KIT / 'pixelate')] + [str(a) for a in args], cwd=str(WORK),
                       capture_output=True, text=True, timeout=timeout)
    out = (r.stdout + ('\n' + r.stderr if r.stderr.strip() else '')).strip()
    return r.returncode, out[-6000:]

def thumb(path, max_w=1400):
    """an image for the model to look at, shrunk with nearest neighbour if very large"""
    from PIL import Image as PImage
    path = pathlib.Path(path)
    im = PImage.open(path)
    if im.width <= max_w:
        return Image(path=str(path))
    f = max(2, -(-im.width // max_w))
    small = im.resize((im.width // f, im.height // f), PImage.NEAREST)
    tp = path.with_name(path.stem + '.preview.png')
    small.save(tp)
    return Image(path=str(tp))

# ---------------------------------------------------------------- guides and files
@server.tool()
def guide(name: str) -> str:
    """Read a guide. names: pixelate, palettes, assets, scenes, music, craft, scene-contract, skill.
    Read the guide for the task's mode first, and 'craft' before drawing anything."""
    if name not in GUIDES:
        return 'guides: ' + ', '.join(GUIDES)
    return GUIDES[name].read_text()

@server.tool()
def new_project(kind: str, path: str) -> str:
    """Start a project from a template. kind: scene (animated loop with music), music (music first),
    assets (sprite / tile pack). Returns the files created."""
    code, out = cli('new', kind, P(path, write=True))
    files = sorted(str(f.relative_to(P(path))) for f in P(path).rglob('*') if f.is_file()) if code == 0 else []
    return out + ('\nfiles:\n  ' + '\n  '.join(files) if files else '')

@server.tool()
def write_file(path: str, content: str) -> str:
    """Write a text file inside the workspace (palettes, .px sprites, scene.js, music.js, config.js...)."""
    try:
        q = P(path, write=True)
    except ValueError as e:
        return 'refused: %s' % e
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text(content)
    return 'wrote %s (%d bytes)' % (q.relative_to(WORK), len(content))

@server.tool()
def read_file(path: str) -> str:
    """Read a text file (a template, an example, your own files). Examples live under the kit:
    use kit:examples/lantern-isle/scene.js style paths to read them."""
    q = KIT / path[4:] if path.startswith('kit:') else P(path)
    return q.read_text()[:60000]

@server.tool()
def list_files(path: str = '.') -> str:
    """List files under a workspace folder (or kit:examples, kit:templates)."""
    q = KIT / path[4:] if path.startswith('kit:') else P(path)
    skip = ('dist', 'out', 'shots', '__pycache__', '.git')
    files = [str(f.relative_to(q)) for f in sorted(q.rglob('*')) if f.is_file() and not any(s in f.parts for s in skip)]
    return '\n'.join(files[:400])

# ---------------------------------------------------------------- image, palette, assets
@server.tool()
def pixelate_image(image: str, out: str, width: int = 96, colors: int = 16, palette: str = '',
                   mode: str = '', match: str = '', dither: str = 'none', outline: bool = False, scale: int = 6) -> list:
    """Turn an image into clean pixel art. width: output pixels across. palette: preset name
    (see palette action=list), a palette file, or '#a,#b,...'; empty = find `colors` colours.
    mode: photo | art (default from the file type). match: lab | luma (luma for monochrome
    palettes). dither: none | ordered. outline: 1 px outline around cut-out shapes.
    Returns the result to look at."""
    args = ['image', P(image), '-o', P(out, write=True), '--width', width, '--dither', dither, '--scale', scale]
    if palette: args += ['--palette', palette]
    else: args += ['--colors', colors]
    if mode: args += ['--mode', mode]
    if match: args += ['--match', match]
    if outline: args += ['--outline']
    code, text = cli(*args)
    o = P(out)
    prev = o.with_name(o.stem + '@%dx.png' % scale)
    return [text] + ([thumb(prev)] if code == 0 and prev.exists() else [])

@server.tool()
def palette(action: str, image: str = '', colors: int = 16, ramps: dict | None = None, steps: int = 5,
            shift: float = 22.0, source: str = '', out: str = '') -> list:
    """Palettes. action:
    extract (from `image`, `colors` colours) | ramps ({name: '#base'} -> hue-shifted ramps of `steps`)
    | show (`source`: preset, file or '#a,#b') | list (presets) | js (`source` as a palettes.js entry).
    out: base path to write .hex .gpl .json .png and a labelled swatch. Returns colours and a swatch."""
    if action == 'list':
        return [cli('palette', 'list')[1]]
    if action == 'extract':
        args = ['palette', 'extract', P(image), '-n', colors]
    elif action == 'ramps':
        args = ['palette', 'ramps'] + ['%s=%s' % kv for kv in (ramps or {}).items()] + ['--steps', steps, '--shift', shift]
    elif action in ('show', 'js'):
        args = ['palette', action, source]
    else:
        return ['actions: extract, ramps, show, list, js']
    base = P(out, write=True) if out else P('.pixelate-tmp/palette', write=True)
    base.parent.mkdir(parents=True, exist_ok=True)
    if action != 'js':
        args += ['-o', base]
    code, text = cli(*args)
    sw = base.parent / (base.name + '-swatch.png')
    return [text] + ([thumb(sw)] if code == 0 and sw.exists() else [])

@server.tool()
def export_assets(pack: str) -> list:
    """Export an asset pack (pack.json, palette.json, sprites/*.px, art/*.py): PNGs, strips with
    frame JSON, GIFs, atlas, map previews. Returns the report, the contact sheet and the
    silhouettes to look at."""
    code, text = cli('assets', P(pack))
    o = P(pack) / 'out'
    imgs = [thumb(o / n) for n in ('contact.png', 'silhouettes.png') if (o / n).exists()]
    for m in json.loads((P(pack) / 'pack.json').read_text()).get('maps', []) if (P(pack) / 'pack.json').exists() else []:
        mp = o / (pathlib.Path(m).stem + '.png')
        if mp.exists(): imgs.append(thumb(mp))
    return [text] + imgs

@server.tool()
def generate_sprites(scene: str) -> str:
    """Run SCENE/art/*.py generators into SCENE/sprites.js (for code-built sprites)."""
    return cli('sprites', P(scene))[1]

# ---------------------------------------------------------------- scenes, loops, music
@server.tool()
def preview_scene(scene: str, times: list[float], zoom: int = 2) -> list:
    """Render frames of a scene at the given seconds into the picture loop, as one sheet.
    Look at it: every phase and mid-transition."""
    out = P(scene) / 'shots'
    code, text = cli('shot', P(scene), *times, '--zoom', zoom, '--grid', '--out', out)
    sheet = out / 'grid.png' if len(times) > 1 else out / ('t%07.2f.png' % float(times[0]))
    return [text] + ([thumb(sheet)] if code == 0 and sheet.exists() else [])

@server.tool()
def check_scene(scene: str, page: bool = False) -> str:
    """Automated checks: sprites and palettes, timing, determinism, loop seam (and with page=True,
    that the built page loads and its play button starts the music)."""
    return cli('check', P(scene), *(['--page'] if page else []))[1]

@server.tool()
def build_page(scene: str, release: bool = True) -> str:
    """Build the scene into one self-contained HTML page (live generative music on tap)."""
    return cli('build', P(scene), *(['--release'] if release else []))[1]

@server.tool()
def render_audio(scene: str, out: str) -> str:
    """Render one seamless loop of the scene's music: .wav (for video), .ogg (games), .flac, .mp3.
    A 2 minute loop takes about a minute; 6 minutes about 8."""
    return cli('audio', P(scene), P(out, write=True))[1]

@server.tool()
def render_video(scene: str, out: str, scale: int = 0, audio: str = '') -> str:
    """Render the picture loop to MP4 (H.264, BT.709), scaled by whole pixels; add audio= a loop
    from render_audio. scale 0 = largest whole scale up to 1080p; use 2x that for 4K."""
    args = ['video', P(scene), P(out, write=True)]
    if scale: args += ['--scale', scale]
    if audio: args += ['--audio', P(audio)]
    return cli(*args, timeout=7200)[1]

@server.tool()
def render_gif(scene: str, out: str, scale: int = 0, fps: float = 15, start_s: float = -1, end_s: float = -1) -> list:
    """Render an animated GIF (no sound) of the loop or of a slice [start_s, end_s) in seconds."""
    args = ['gif', P(scene), P(out, write=True), '--fps', fps]
    if scale: args += ['--scale', scale]
    if start_s >= 0 and end_s > start_s:
        args += ['--frames', '%d:%d' % (round(start_s * 30), round(end_s * 30))]
    code, text = cli(*args)
    return [text]

def main():
    server.run('stdio')

if __name__ == '__main__':
    main()
