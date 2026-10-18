#!/usr/bin/env python3
"""pixelate-anything MCP server (stdio). Run with:  pixelate mcp

Exposes the same core as the CLI as typed tools. Preview tools return images, so the
agent can look at its own work: that is the main quality lever. File tools let clients
without a shell write palettes, sprites and scene code.

Paths are relative to the workspace: $PIXELATE_WORKSPACE, else the directory the server
was started in. Absolute paths are accepted for reading (an image to pixelate); writes
through write_file stay inside the workspace.
"""
import json, re, os, pathlib, subprocess, sys

TOOLS = pathlib.Path(__file__).resolve().parent
KIT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
WORK = pathlib.Path(os.environ.get('PIXELATE_WORKSPACE') or os.getcwd()).resolve()

try:                                    # mcp 2.x
    from mcp.server.mcpserver import MCPServer as Server, Image
except ImportError:                     # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server, Image

GUIDES = {p.stem: p for p in sorted((KIT / 'guides').glob('*.md'))}
GUIDES.update({'brief': KIT / 'references' / 'brief.md', 'drawing': KIT / 'references' / 'drawing.md',
               'delivery': KIT / 'references' / 'delivery.md', 'craft': KIT / 'references' / 'craft.md',
               'scene-contract': KIT / 'references' / 'scene-contract.md', 'skill': KIT / 'SKILL.md',
               'art-director': KIT / 'references' / 'art-director.md',
               'visual-specialists': KIT / 'references' / 'visual-specialists.md',
               'music-review': KIT / 'references' / 'music-review.md'})

INSTRUCTIONS = """pixelate-anything: hand-crafted pixel art for agents. Read only what each step needs.
1. intake_request: if disposition is offer, optionally ask its two questions. Accept answers in the user's
   own words, or skip; combine explicit answers with the original request before writing the brief.
   If direct, proceed without intake questions. Read the intent (guide('brief')).
2. route_request: ranks styles and names the mode; a hint, not the decision. Read the mode's guide:
   scenes (+ music), rebuild, eras, assets, music; a quick conversion is pixelate, a palette is palettes.
3. write_brief (a short brief for a small ask), fill every TODO (each names its section and command),
   lint_brief until it says ready. style_card(name) prints one style's rules, light, budgets and limits.
4. Draw a greyscale block-in of the layout (flat value shapes from the brief's boxes; its gate is
   `pixelate check BLOCKIN.png --blockin --brief brief.md`), then critique_prompt(brief, block=...):
   send the prompt to a separate agent that did not write the brief, apply its changes, lint_brief
   again within the stage's review budget (guide('delivery'), Art director). A short brief skips
   brief-stage review. Save the external lead report, call record_visual_review(brief, report),
   and require visual_review_status(brief) to return READY for an A full brief. If the budget ends
   below A, report grade and unresolved ranked fixes and ask whether to continue or change the brief.
5. Show the user an A full brief (or a short brief, which skips brief-stage review)
   with section 0 and wait for OK.
6. Draw everything yourself in code (guide('drawing')). kit_tools() lists topics and modules,
   kit_tools('rain') the techniques for a subject, kit_tools('post.Post.lightmap') one signature.
   references/assets holds examples to read, never to call.
7. check_frame and redraw until every line passes (guide('delivery')); then judge_frame and fix each
   box it finds or say why it stays.
8. critique_prompt(brief, frame, prev=last lead critique): the same for the still; optional
   role=composition|lighting|set|character consults observe only; pass at most two notes total
   via consults to a later lead round. The lead alone grades and reconciles notes. Apply its fixes,
   check_frame again within the stage's review budget (guide('delivery'), Art director). Save the
   lead report, call record_visual_review(brief, report, frame), and require
   visual_review_status(brief, frame) to return READY for this still. If the budget ends below A,
   stop automatic review, report grade and unresolved ranked fixes and ask whether to continue or
   change the brief. Passing the gate means legal, not good: never self-grade.
9. Show one still for go/no-go only once it is graded A; never present a below-A still as finished.
10. Confirm the animation plan (loop length, what moves, rates), then animate.
Hard rules: the five orthographic views (side, 3/4 top-down, 2:1 iso, oblique, military) are
presets, not limits. Keep a reference's camera or an explicit one- or two-point perspective;
draw converging edges on the native-pixel grid. Draw original scenes without borrowed characters,
logos or UI; a rebuild may depict the supplied place and camera. Rebuild a photo rather than convert
it; every effect is done in code. Every rendered track goes through check_music until it passes;
then optionally use music_critique_prompt with a separate agent that can actually listen. Look at
every preview image you get back and fix what looks wrong before going on. Paths are relative to
the workspace."""

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

# ---------------------------------------------------------------- one line to a brief, and the gate
@server.tool()
def intake_request(request: str) -> str:
    """JSON intake plan: optional questions for a generic scene ask, plus the route result.
    For direct requests, proceed without questions. Answers are free text; skipping is fine."""
    import route
    return json.dumps(route.intake_plan(request), ensure_ascii=False)

@server.tool()
def route_request(request: str) -> str:
    """Rank the style presets for a plain request, with reasons, the mode, technique hints for the
    subject and the defaults for what the request leaves open. A hint: choose with the user's intent."""
    return cli('route', request)[1]

@server.tool()
def write_brief(request: str, out: str, style: str = '', size: str = '', scale: int = 0) -> str:
    """Write the pre-filled scene brief (section 0 choices to confirm, then 11 sections) to `out`,
    for the top style or `style`. size: the delivered picture, e.g. '1920x1080' (the canvas is size /
    scale; without scale the scale keeps the style's native height); figure sizes follow. Fill every
    TODO with concrete choices, then lint_brief."""
    return cli('route', request, '--brief', *([style] if style else []), *(['--size', size] if size else []),
               *(['--scale', scale] if scale else []), '-o', P(out, write=True))[1]

@server.tool()
def lint_brief(path: str) -> str:
    """Self-critique a filled brief: TODOs left, thin or missing sections, vague words, motion periods
    that don't divide the loop, kit names that don't exist. Fix until it says ready; a full brief
    needs an independent A within the review budget before asking the user to approve it. A short
    brief skips brief-stage review."""
    return cli('route', '--lint', P(path))[1]

@server.tool()
def check_frame(frame: str, style: str = '', scale: int = 1, palette: str = '', prelight: str = '',
                actor: str = '', used: str = '', scene: str = '', era: str = '', brief: str = '',
                blockin: bool = False) -> list:
    """The delivery gate for one frame: the style's value budget, square native pixels, banned light ops,
    palette subset, actor readability and pixel craft (orphans, jaggies, banding, pillow shading,
    clusters). scene: the style's scene variant (style_card lists them); era: the console era's checks
    replace the value budget; brief: apply its `- Gate override: RULE BOUND (reason)` lines and its
    Hero and Planes lines (focus checks); blockin: check a greyscale block-in instead (value bands,
    hero placement and size, plane shares). Redraw until every line passes; no frame is shown as
    final before that."""
    args = ['check', P(frame), '--scale', scale] + (['--style', style] if style else [])
    if blockin:
        args.append('--blockin')
    for flag, v in (('--pal', palette), ('--pre', prelight), ('--actor', actor), ('--used', used),
                    ('--scene', scene), ('--era', era), ('--brief', brief)):
        if v:
            args += [flag, P(v) if flag in ('--pal', '--pre', '--actor', '--brief') else v]
    code, text = cli(*args)
    return [('PASS\n' if code == 0 else 'FAIL\n') + text, thumb(P(frame))]

@server.tool()
def inspect_reference(photo: str, out: str, marks: str = '') -> list:
    """Experimental rebuild evidence: sample a source photo's value bands and edge directions,
    write a correctable JSON record and return its overlay. Does not infer horizon, vanishing points,
    silhouettes, focal point or art quality. Add manual camera/landmark marks to the JSON and pass it
    as marks to re-render the overlay. out must be a workspace .json path."""
    destination = P(out, write=True)
    args = ['reference', P(photo), '-o', destination]
    if marks:
        args += ['--marks', P(marks)]
    code, text = cli(*args)
    return [text, Image(path=str(destination.with_suffix('.overlay.png')))] if code == 0 else [text]

@server.tool()
def judge_frame(frame: str, scale: int = 0, ignore: str = '') -> list:
    """The judge, as `pixelate judge`: finds what the gate passes and an art director rejects (rock
    drawn as masonry, rows of identical units, scalloped edges, masses drawn as 1 px contours, murky
    values) and returns each defect's box in native px, why it reads wrong and a fix, plus an overlay
    of the frame with numbered boxes. Run it after check_frame passes and before critique_prompt;
    fix each box or say why it stays. ignore: comma-separated kinds to skip (masonry for a brick town)."""
    out = str(P(frame, write=True)) + '.judge.png'
    args = ['judge', P(frame), '--overlay', out] + (['--scale', scale] if scale else []) + \
           (['--ignore', ignore] if ignore else [])
    code, text = cli(*args)
    return [text, Image(path=out)] if code == 0 else [text]

@server.tool()
def critique_prompt(brief: str, frame: str = '', block: str = '', prev: str = '', style: str = '',
                    role: str = 'lead', consults: list[str] | None = None) -> str:
    """The prompt for an independent art director, as `pixelate critique`. With no frame it grades
    the brief before anything is drawn (step 4), with the greyscale block-in `block` if given; drawing
    waits for an A. With a frame it grades the still (step 8), writing a 480 px nearest-neighbour
    thumbnail and its greyscale next to the frame. prev: the previous critique's file, so each earlier
    fix is checked first as fixed, partly or not. It holds the rubric (references/art-director.md, the
    part for that stage), the brief's request, section 0 and signature elements, and the paths of the
    brief and the bar. Send it to a separate agent or model that did not write or draw the work; apply
    the fixes it returns, then lint_brief or check_frame again. This tool produces one prompt per
    call; track the brief or still review budget in guide('delivery') yourself. role selects the
    lead (default) or one observational specialist; consults are up to two specialist note paths
    passed only to the lead, while prev is only the prior lead critique."""
    import critique
    notes = consults or []
    if len(notes) > 2:
        raise ValueError('at most two specialist consult notes per visual artifact')
    return critique.prompt(P(frame, write=True) if frame else None, P(brief), style,
                           prev=P(prev) if prev else None,
                           block=P(block) if block else None,
                           role=role, consults=[P(note) for note in notes])

@server.tool()
def record_visual_review(brief: str, report: str, frame: str = '') -> str:
    """Record an existing external lead critique for this exact full brief or still. The artifact
    and its adjacent manifest must be in the workspace; the report may be read-only outside it.
    This validates rubric structure, not reviewer independence or authenticity."""
    import review_status
    artifact = P(frame or brief, write=True)
    try:
        return review_status.record(P(brief), P(report), artifact if frame else '')
    except (review_status.ReviewError, OSError) as exc:
        return f'NOT RECORDED: {exc}'

@server.tool()
def visual_review_status(brief: str, frame: str = '') -> str:
    """Read-only artifact-bound review status. READY requires matching A evidence, not a gate pass
    or user approval; a short brief skips brief-stage review."""
    import review_status
    return review_status.status(P(brief), P(frame) if frame else '')[1]

@server.tool()
def music_critique_prompt(track: str, brief: str, prev: str = '') -> str:
    """Prompt a separate listening agent after rendering and passing check_music. Does not play
    audio, check the gate, or invoke an agent. Without actual audio access the agent must return
    NOT REVIEWED, not a grade. prev is the previous music critique only; see guide('delivery')."""
    import critique
    return critique.music_prompt(P(track), P(brief), P(prev) if prev else None)

@server.tool()
def check_music(track: str, style: str = 'any', use: str = 'loop', bpm: float = 0, key: str = '') -> list:
    """The music gate for a rendered track (any code made it): clipping, loudness, clicks, stereo,
    silence, loop seam, band balance, tilt, dynamics, steady tempo, clear key, variety, a hook that
    returns (use='showcase') and an arc. style: any, lofi, chiptune, ambient, orchestral, synthwave,
    eastern. use: loop, showcase, song. Returns the report and an ear sheet (spectrogram, loudness,
    pitch classes, bar similarity) to look at. Rewrite the music until every line passes."""
    sheet = P(pathlib.Path(track).with_suffix('.sheet.png'), write=True)
    args = ['check', P(track), '--style', style, '--use', use, '--sheet', sheet]
    if bpm: args += ['--bpm', bpm]
    if key: args += ['--key', key]
    code, text = cli(*args)
    return [('PASS\n' if code == 0 else 'FAIL\n') + text] + ([thumb(sheet)] if sheet.exists() else [])

@server.tool()
def style_card(name: str = '') -> str:
    """One style's card: what it is, when to pick it, the light regime, palette and ramps, outline and
    dither, canvas and figure sizes, the value budget, the craftcheck limits, its rules, techniques and
    bans, and the gate command. An empty name lists every style with one line each."""
    import styles
    if not name:
        return styles.listing()
    try:
        return styles.card(name)
    except KeyError as e:
        return e.args[0]

@server.tool()
def kit_tools(query: str = '', style: str = '') -> str:
    """The kit on demand, read from the source. '' lists every topic and module; a topic word (rain,
    雨, fog, water, lamp: the keywords routing uses) gives its techniques, filtered to `style` if given;
    a module ('post') gives its functions with signatures and first doc lines; 'post.Post.lightmap'
    gives one full signature and docstring."""
    import kit
    return kit.query(query, style or None)

# ---------------------------------------------------------------- guides and files
@server.tool()
def guide(name: str) -> str:
    """Read a guide. names: rebuild, eras, pixelate, palettes, assets, scenes, music, styles, toolkit, brief,
    drawing, delivery, craft (an index of the last three), scene-contract, skill, art-director. Read the guide
    for the task's mode first, 'brief' to write the brief, 'drawing' before drawing, 'delivery' for the gate,
    'art-director' only if you are the art director."""
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
    """Read a text file (a library piece, a starter, your own files). Library pieces live under the kit:
    use kit:library/lantern-isle/scene.js style paths to read them."""
    q = KIT / path[4:] if path.startswith('kit:') else P(path)
    return q.read_text()[:60000]

@server.tool()
def list_files(path: str = '.') -> str:
    """List files under a workspace folder (or kit:library)."""
    q = KIT / path[4:] if path.startswith('kit:') else P(path)
    skip = ('dist', 'out', 'shots', '__pycache__', '.git')
    files = [str(f.relative_to(q)) for f in sorted(q.rglob('*')) if f.is_file() and not any(s in f.parts for s in skip)]
    return '\n'.join(files[:400])

# ---------------------------------------------------------------- image, palette, assets
@server.tool()
def pixelate_image(image: str, out: str, width: int = 96, colors: int = 16, palette: str = '',
                   mode: str = '', match: str = '', dither: str = 'none', outline: bool = False, smooth: int = 1, scale: int = 6,
                   crop: str = '', cutout: float = 0.0, flatten: int = 0, grade: float = 0.0) -> list:
    """Turn an image into clean pixel art. width: output pixels across. palette: preset name
    (see palette action=list), a palette file, or '#a,#b,...'; empty = find `colors` colours.
    mode: photo | art (default: detected from the image). match: lab | luma (luma for monochrome
    palettes). dither: none | ordered. outline: 1 px outline around cut-out shapes.
    smooth: 2-4 flattens heavy texture (fur, wood grain) in photo mode. crop: 'x,y,w,h' (pixels
    or fractions). cutout: remove a plain background (try 0.09) to make a sprite. flatten: 1-3
    edge-preserving passes for busy photos. grade: e.g. 28, cool shadows and warm lights.
    A video or GIF source (with out ending .gif or .mp4) becomes an animated pixel clip.
    Returns the result to look at."""
    args = ['image', P(image), '-o', P(out, write=True), '--width', width, '--dither', dither, '--scale', scale]
    if palette: args += ['--palette', palette]
    else: args += ['--colors', colors]
    if mode: args += ['--mode', mode]
    if match: args += ['--match', match]
    if outline: args += ['--outline']
    if smooth > 1: args += ['--smooth', smooth]
    if crop: args += ['--crop', crop]
    if cutout: args += ['--cutout', cutout]
    if flatten: args += ['--flatten', flatten]
    if grade: args += ['--grade', grade]
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
def era(image: str, era: str = 'nes', out: str = '', layer: str = 'full', scale: int = 4) -> list:
    """Hold an image to a console era's limits. era: nes | gameboy | snes | genesis | gba | pico-8
    (screen size, palette or bit depth, colours on screen, colours per block for layer='bg').
    Reports what breaks the rules; with out, also writes the image made legal and returns it."""
    args = ['era', P(image), '--era', era, '--layer', layer, '--scale', scale]
    if out:
        args += ['-o', P(out, write=True)]
    code, text = cli(*args)
    if out:
        prev = P(out).with_name(P(out).stem + '@%dx.png' % scale)
        return [text] + ([thumb(prev)] if prev.exists() else [])
    return [text]

@server.tool()
def export_assets(pack: str) -> list:
    """Export an asset pack (pack.json, palette.json, sprites/*.px, art/*.py): PNGs, strips with
    frame JSON, GIFs, atlas, map previews. Returns the report, the contact sheet and the
    silhouettes to look at."""
    code, text = cli('assets', P(pack))
    o = P(pack) / 'out'
    imgs = [thumb(o / n) for n in ('contact.png', 'silhouettes.png') if (o / n).exists()]
    for name in re.findall(r'^scene (\S+):', text, re.M):          # whole animated pictures: first frame
        big = sorted(o.glob(name + '@*x.png'))
        if big or (o / (name + '.png')).exists():
            imgs.append(thumb(big[0] if big else o / (name + '.png')))
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
