#!/usr/bin/env python3
"""pixelate-anything MCP server (stdio). Run with:  pixelate mcp

Exposes the same core as the CLI as typed tools. Preview tools return images, so the
agent can look at its own work: that is the main quality lever. File tools let clients
without a shell write palettes, sprites and scene code.

Paths are relative to the workspace: $PIXELATE_WORKSPACE, else the directory the server
was started in. Absolute paths are accepted for reading (an image to pixelate); writes
through write_file stay inside the workspace.
"""
import contextlib, hashlib, io, json, re, os, pathlib, signal, subprocess, sys

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
Library path, the default for a new request: find_pieces (look at the thumbnails), remix_piece, edit
what REMIX.md names, render_piece, deliver_piece. These run the piece's own shell commands without a
sandbox; a gate pass or a delivery is a technical result, not quality, approval or rights.
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

# ---------------------------------------------------------------- library: find, remix, render, deliver
LIBRARY = KIT / 'library'
EXEC_WARNING = ("This ran shell commands from the piece's manifest with your user's permissions and no sandbox. "
                "Use it only on checked-in library pieces and on folders you wrote or reviewed.")
RESULT_NOTICE = ("A gate pass is a technical check, not art quality. No critique or rating was run. It does not mean "
                 "the user approved the art, and rights to any source and the license are not verified.")
MAX_PREVIEW_BYTES = 32 * 1024 * 1024
MAX_THUMB_BYTES = 2 * 1024 * 1024
MAX_SETS = 64

def cli_full(*args, timeout=3600):
    """(exit code, stdout, stderr) of a `pixelate` command, never shortened (cli() keeps 6000 characters,
    which would cut a JSON report). On timeout the command's whole process group is killed and the code is None."""
    proc = subprocess.Popen([sys.executable, str(KIT / 'pixelate')] + [str(a) for a in args], cwd=str(WORK),
                            env=dict(os.environ, PYTHONIOENCODING='utf-8'), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, '', ''
    return proc.returncode, out, err

def json_report(text):
    """the JSON value a command printed to stdout, or None when stdout is not exactly one JSON document"""
    try:
        return json.loads(text)
    except ValueError:
        return None

def tail(text, n=2000):
    text = text.strip()
    return text[-n:]

def in_library(q):
    lib = LIBRARY.resolve()
    return q == lib or lib in q.parents

def work_folder(path, new=False):
    """the resolved workspace folder for `path`. A piece folder must already hold piece.json; a new folder
    (the remix destination) must be inside the workspace, not the workspace itself. Nothing in the kit's
    library is ever a place to write: a render or delivery writes reports, logs and packages there."""
    q = P(path, write=True)
    if in_library(q):
        raise ValueError('%s is inside the kit library, which is read-only; remix a piece into the workspace first' % q)
    if new:
        if q == WORK:
            raise ValueError('choose a new folder inside the workspace, not the workspace itself: %s' % WORK)
    elif not q.is_dir() or not (q / 'piece.json').is_file():
        raise ValueError('%s is not a piece folder (no piece.json)' % q)
    return q

def set_args(sets):
    """`--set=KNOB=VALUE` arguments for typed knob strings such as 'time=dusk', 'seed=4' or 'bloom=true'. Each
    is one argv entry, never interpolated into a shell; the CLI checks the knob and the value."""
    sets = [] if sets is None else sets
    if not isinstance(sets, list) or len(sets) > MAX_SETS or not all(
            isinstance(item, str) and '=' in item and len(item) <= 512 and '\0' not in item for item in sets):
        raise ValueError("sets: a list of 'KNOB=VALUE' strings, at most %d" % MAX_SETS)
    return ['--set=' + item for item in sets]

def check_timeout(timeout):
    if type(timeout) is not int or timeout < 1:
        raise ValueError('timeout: a positive number of seconds')
    return timeout

def png_image(data, max_w=1400):
    """an Image of PNG-compatible bytes, shrunk with nearest neighbour in memory when very wide, or None when
    they do not decode. Nothing is written to disk."""
    from PIL import Image as PImage
    try:
        im = PImage.open(io.BytesIO(data))
        im.load()
        if im.format == 'PNG' and im.width <= max_w:
            return Image(data=data, format='png')
        if im.width > max_w:
            f = max(2, -(-im.width // max_w))
            im = im.resize((max(1, im.width // f), max(1, im.height // f)), PImage.NEAREST)
        if im.mode not in ('1', 'L', 'LA', 'P', 'RGB', 'RGBA'):
            im = im.convert('RGBA')
        buf = io.BytesIO()
        im.save(buf, 'PNG')
        return Image(data=buf.getvalue(), format='png')
    except Exception:
        return None

def verified_preview(root, rel, digest):
    """an Image of the file `rel` under `root` only when it is a regular file reached without a link whose
    bytes hash to `digest` (what the command that wrote it recorded), else None. A stale, swapped, linked
    or unreadable frame has no preview."""
    import render
    if not isinstance(rel, str) or not isinstance(digest, str):
        return None
    try:
        data = render.read_regular(root, rel)
    except (OSError, ValueError):
        return None
    if len(data) > MAX_PREVIEW_BYTES or hashlib.sha256(data).hexdigest() != digest:
        return None
    return png_image(data)

def library_thumb(piece):
    """an Image of the piece's checked-in media.thumb, read as a regular file without following a link under the
    kit library; None when it is missing, too large or not an image. Reads only; writes nothing."""
    import render
    thumb = (piece.get('media') or {}).get('thumb')
    if not thumb:
        return None
    try:
        data = render.read_regular(LIBRARY, '%s/%s' % (piece['id'], thumb))
    except (OSError, ValueError):
        return None
    return png_image(data) if len(data) <= MAX_THUMB_BYTES else None

def report(summary, images=()):
    return [json.dumps(summary, indent=2, ensure_ascii=False)] + list(images)

def refusal(command, code, out, err, timeout):
    """the summary of a command that printed no JSON report: it refused its arguments, crashed or timed out"""
    if code is None:
        return {'ok': False, 'error': '%s timed out after %ss and was killed with its process group' % (command, timeout)}
    return {'ok': False, 'exit_code': code, 'error': '%s produced no JSON report' % command,
            'stderr': tail(err, 4000), 'stdout': tail(out, 1000)}

@server.tool()
def find_pieces(request: str, mode: str = '') -> list:
    """Find the closest library pieces for a request, as `pixelate find --json`, and look at them. Returns
    JSON (top matches with why they match and what differs, each piece's title, status, summary, tags, canvas,
    knobs and anatomy files, and the starters to use when nothing is close) followed by each piece's checked-in
    thumbnail image, in the order the JSON names them. Static: reads the catalog's manifests and thumbnails
    only, never imports or runs piece code and starts no process. mode: scene | rebuild | era | assets |
    music (default: detected from the request). A `reviewed` or `accepted` match is a better base than a
    `study`; a match is a starting point, not a verdict on the request."""
    import library
    found = library.find(LIBRARY, request, mode or None)
    pieces = library.scan(LIBRARY)
    fallback = dict(found['fallback'])
    images = []
    def entry(piece_id, ranked=None):
        piece = pieces[piece_id]
        thumb = library_thumb(piece)
        if thumb is not None:
            images.append(thumb)
        return dict(ranked or {'id': piece_id, 'status': piece['status']}, title=piece['title'], summary=piece['summary'],
                    mode=piece['mode'], tags=piece['tags'], canvas=piece['canvas'], knobs=piece['knobs'],
                    anatomy=[a['file'] for a in piece['anatomy']],
                    thumbnail_image=len(images) if thumb is not None else None)
    matches = [entry(m['id'], m) for m in found['matches']]
    if fallback['kind'] == 'starter':
        fallback['starters'] = [entry(i) for i in fallback['ids'][:3]]
    return report({'mode': found['mode'], 'matches': matches, 'fallback': fallback,
                   'note': 'Static catalog search: no piece code ran. Image N is the checked-in thumbnail named by '
                           'thumbnail_image; a score ranks keyword and tag overlap, not quality.'}, images)

@server.tool()
def remix_piece(piece: str, dest: str, request: str) -> list:
    """Copy library piece `piece` to the new workspace folder `dest` (its name, a lowercase slug, becomes the
    piece id) and write REMIX.md, as `pixelate remix --json`. Before moving the copy into place it renders
    the UNEDITED copy once in a clean temporary folder (quick baseline). That runs the base piece's shell
    commands without a sandbox: remix only checked-in library pieces. The baseline is quick: when the piece
    has images, its audio and exports are NOT rendered or tested, and the result lists them as untested. A
    golden match and a gate pass are technical regression checks, not approval or quality. The copy is
    unreviewed, never inherits the base's status or approval, and nothing is critiqued or rated. `dest` must
    be a new or empty folder inside the workspace; nothing outside it is written."""
    destination = work_folder(dest, new=True)
    code, out, err = cli_full('remix', piece, destination, '--request=' + request, '--json')
    baseline = json_report(out)
    if not isinstance(baseline, dict) or code not in (0, 1) or 'test' not in baseline:
        return report(dict(refusal('remix', code, out, err, 3600), created=False,
                           note='Nothing was created at %s unless the folder already existed empty.' % destination))
    import remix
    outputs = [{'name': r['name'], 'kind': r['kind'], 'tested': r['tested'], 'status': r['status'],
                'result': remix.describe(r)} for r in baseline['test']['outputs']]
    created = code == 0
    summary = {'created': created, 'ok': created, 'piece_id': baseline['piece'], 'base': baseline['base']['id'],
               'base_status': baseline['base']['status'], 'copy_status': baseline['status'] if created else None,
               'reviewed': False, 'quick_baseline': baseline['quick'], 'gate_ok': baseline['test']['gate_ok'],
               'outputs': outputs,
               'not_tested': ['%s %s: %s' % (u['kind'], u['name'], u['reason']) for u in baseline['untested']],
               'baseline_evidence': '%s/%s' % (destination, '.pixelate/remix-baseline.json') if created else None,
               'next': ('fill in the plan in %s/REMIX.md, edit what it names, then render_piece' % destination)
                       if created else 'nothing was created: the unedited base did not pass its baseline here',
               'warning': EXEC_WARNING, 'notice': RESULT_NOTICE}
    if not created:
        summary['stderr'] = tail(err, 4000)
    return report(summary)

@server.tool()
def render_piece(piece_dir: str, image: str = '', sets: list[str] | None = None, timeout: int = 3600) -> list:
    """Render a workspace piece folder (its piece.json) and gate it, as `pixelate render DIR --json`: runs each
    output's shell command (without a sandbox: only trusted library copies and code you wrote), gates and
    judges each frame. Returns JSON per output (run, gate, era, judge, hash) and an Image of each frame
    only when it is the file this render just produced (its bytes match the hash the render recorded, reached
    without a link). A failed run or an error returns no image. image: render only that output.
    sets: knob variants as typed 'KNOB=VALUE' strings, e.g. ['time=dusk', 'seed=4']; a variant is not
    compared with golden frames. Never runs a critique and never rates. A gate pass is technical: it does
    not mean the art is good, approved or cleared for rights."""
    folder = work_folder(piece_dir)
    args = ['render', folder, '--json'] + set_args(sets) + (['--image=' + image] if image else [])
    code, out, err = cli_full(*args, timeout=check_timeout(timeout))
    recs = json_report(out)
    if not isinstance(recs, list) or not all(isinstance(r, dict) and 'name' in r for r in recs):
        return report(dict(refusal('render', code, out, err, timeout), warning=EXEC_WARNING))
    import render
    images, outputs = [], []
    for rec in recs:
        gate = rec.get('gate') or {}
        judge = rec.get('judge') or {}
        item = {'name': rec['name'], 'kind': rec.get('kind', 'image'), 'ok': bool(render.ok(rec)),
                'path': rec.get('frame') or rec.get('file'), 'sha256': rec.get('sha256'),
                'ran': rec['run']['ok'] if 'run' in rec else None, 'preview_image': None}
        for key in ('error', 'snapshot'):
            if rec.get(key):
                item[key] = rec[key]
        if 'run' in rec and not rec['run']['ok']:
            item['run_error'] = rec['run'].get('error')
        if 'gate' in rec:
            item['gate'] = {key: gate[key] for key in ('ok', 'pass', 'fail', 'error') if key in gate}
        if 'era' in rec:
            item['era'] = rec['era']
        if 'judge' in rec:
            item['judge'] = {'error': judge['error']} if 'error' in judge else \
                {'defects': [{key: d.get(key) for key in ('kind', 'box', 'severity')} for d in judge['defects']]}
        if item['kind'] == 'image' and rec.get('frame') and not rec.get('error') and rec.get('run', {'ok': True})['ok']:
            preview = verified_preview(folder, rec['frame'], rec.get('sha256'))
            if preview is not None:
                images.append(preview)
                item['preview_image'] = len(images)
        outputs.append(item)
    knobs = next((rec['knobs'] for rec in recs if rec.get('knobs')), None)
    return report({'ok': code == 0 and all(o['ok'] for o in outputs), 'exit_code': code, 'dir': str(folder),
                   'outputs': outputs, 'knobs': knobs, 'stderr': tail(err), 'warning': EXEC_WARNING,
                   'notice': RESULT_NOTICE + ' preview_image N is the Nth image: it shows the frame whose hash is '
                             'listed, even when its gate failed.'}, images)

@server.tool()
def deliver_piece(piece_dir: str, sets: list[str] | None = None, verify: bool = False, timeout: int = 900) -> list:
    """Deliver a workspace piece folder, as `pixelate deliver DIR --json`: render every output once more
    (running the piece's shell commands without a sandbox: only trusted library copies and code you wrote),
    require every command to run and every image to pass the technical gate, then package the outputs and a
    script-written DELIVERY.md under DIR/dist/delivery. A failed delivery writes no package and returns no
    image. With verify=true it only checks an existing package's facts and hashes: it runs no piece code and
    takes no sets. sets: typed 'KNOB=VALUE' strings as in render_piece. Delivery never runs a critique or
    rates, and it does NOT mean the art is good, that anyone approved it, or that rights and the license are
    cleared: a declared approver in piece.json is reported as unverified."""
    folder = work_folder(piece_dir)
    if verify:
        if sets:
            raise ValueError('verify takes no sets: it runs nothing')
        code, out, err = cli_full('deliver', folder, '--verify', '--json', timeout=check_timeout(timeout))
        result = json_report(out)
        if not isinstance(result, dict) or 'checks' not in result:
            return report(refusal('deliver --verify', code, out, err, timeout))
        return report({'verified': bool(result['ok']) and code == 0, 'ok': bool(result['ok']) and code == 0,
                       'fingerprint': result.get('fingerprint'), 'checks': result['checks'],
                       'notice': 'Verified means the delivered facts, package and piece hashes match; it ran no piece '
                                 'code. ' + RESULT_NOTICE})
    args = ['deliver', folder, '--json', '--timeout=%d' % check_timeout(timeout)] + set_args(sets)
    code, out, err = cli_full(*args, timeout=timeout + 120)
    result = json_report(out)
    if not isinstance(result, dict) or 'errors' not in result:
        return report(dict(refusal('deliver', code, out, err, timeout + 120), warning=EXEC_WARNING))
    delivered = bool(result.get('ok')) and code == 0
    outputs = result.get('outputs') or []
    images = []
    if delivered:
        for o in outputs:
            if o.get('kind') == 'image':
                preview = verified_preview(folder, '%s/%s' % (result.get('package'), o.get('path')), o.get('sha256'))
                if preview is not None:
                    images.append(preview)
                    o['preview_image'] = len(images)
    facts = result.get('facts') or {}
    summary = {'ok': delivered, 'delivered': delivered, 'refused': bool(result.get('refused')), 'exit_code': code,
               'piece': result.get('piece'), 'errors': result['errors'], 'outputs': outputs,
               'fingerprint': result.get('fingerprint'),
               'package': '%s/%s' % (folder, result['package']) if result.get('package') else None,
               'delivery_sha256': result.get('delivery_sha256'), 'evidence': facts.get('evidence'),
               'not_tested': facts.get('untested'), 'knobs': facts.get('knobs'), 'log': result.get('log'),
               'stderr': tail(err), 'warning': EXEC_WARNING, 'notice': RESULT_NOTICE}
    if not delivered:
        summary['note'] = 'No package was written by this delivery; an earlier package was left as it was.'
    return report(summary, images)

def main():
    server.run('stdio')

if __name__ == '__main__':
    main()
