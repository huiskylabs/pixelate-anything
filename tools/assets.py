#!/usr/bin/env python3
"""Export a pack of pixel-art assets (sprites, animations, items, tiles) for games and the web.

usage: assets.py PACK_DIR [--scale 6] [--only NAME,...]

A pack folder holds:
  pack.json      {"name": "Meadow Kit", "palette": "palette.json", "scale": 6,
                  "preview_bg": "#2a2836", "maps": ["maps/meadow.txt"]}
  palette.json   {slot: "#hex"}  (make one with tools/palette.py ramps ... -o PACK/palette)
  sprites/*.px   hand-drawn sprites (format below), any number per file
  art/*.py       optional generators: export() returns sprites as
                 ('sprite', name, [Grid frames], ax, ay[, {"fps": 8, "tags": {...}, "tile": 16}])

.px format (one or more sprites per file):
  sprite: coin                 # name
  anchor: 4 7                  # optional pivot (x y), default 0 0
  fps: 8                       # or  durations: 120 80 80 120   (ms per frame)
  tags: spin 0-3               # optional animation tags (name from-to), repeatable
  key: o=outline Y=gold2 G=gold1 g=gold0     # char=slot (or char=#rrggbb); '.' is transparent
  frame
  ..oooo..
  .oYYGGo.
  ...
  frame
  ...

Writes PACK/out/:
  <name>.png            1x strip of all frames, left to right (transparent)
  <name>.json           frame rects, durations, tags, pivot (Aseprite "array" JSON layout)
  <name>@Nx.png         the strip scaled N x (nearest neighbour)
  <name>.gif            animated preview, scaled, on preview_bg (animations only)
  atlas.png/.json       every frame of every sprite packed in one sheet
  contact.png           everything at a glance, labelled: LOOK AT THIS
  silhouettes.png       every sprite as a solid shape: shapes must read on their own
  <map>.png             tilemap previews (see maps below)
Checks printed: unknown keys, ragged frames, lone pixels, colours per sprite.

Maps (optional, for tilesets): a text file with
  tileset: grass_dirt          # a sprite whose frames are 16 corner tiles (index = NW*8+NE*4+SW*2+SE);
                               # meta "variants" {index: [frames]} spreads alternates over plain areas
  tile: 16
  corners:                     # one char per tile CORNER: '.' first terrain, '#' second
  ..........
  ...##.....
  props:                       # name x y [frame]  (pixels, anchor-relative)
  bush 40 30
"""
import json, pathlib, re, sys
import numpy as np
from PIL import Image, ImageDraw

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / 'tools'))
import artlib, colorlib as cl

# ---------------------------------------------------------------- parsing
def parse_px(path):
    sprites, cur, frame = [], None, None
    def close():
        if cur is not None:
            if frame is not None: cur['rows'].append(frame)
            sprites.append(cur)
    for raw in pathlib.Path(path).read_text().splitlines():
        line = raw.split('  #')[0].rstrip() if not raw.lstrip().startswith('#') else ''
        if not line.strip():
            continue
        m = re.match(r'^\s*(sprite|anchor|fps|durations|tags|key|tile)\s*:\s*(.*)$', line)
        if m and (frame is None or m.group(1) == 'sprite'):
            k, v = m.group(1), m.group(2).strip()
            if k == 'sprite':
                if cur is not None:
                    if frame is not None: cur['rows'].append(frame)
                    sprites.append(cur)
                cur, frame = {'name': v, 'rows': [], 'key': {}, 'anchor': (0, 0), 'tags': {}, 'src': str(path)}, None
            elif k == 'anchor': cur['anchor'] = tuple(int(x) for x in v.split())
            elif k == 'fps': cur['fps'] = float(v)
            elif k == 'durations': cur['durations'] = [int(x) for x in v.split()]
            elif k == 'tile': cur['tile'] = int(v)
            elif k == 'tags':
                n, r = v.split()
                a, b = (int(x) for x in r.split('-'))
                cur['tags'][n] = (a, b)
            elif k == 'key':
                for pair in v.split():
                    c, s = pair.split('=', 1)
                    cur['key'][c] = s
            continue
        if line.strip() == 'frame':
            if frame is not None: cur['rows'].append(frame)
            frame = []
            continue
        if frame is None:
            raise SystemExit('%s: pixel rows before "frame": %r' % (path, line))
        frame.append(line.strip())
    if cur is not None:
        if frame is not None: cur['rows'].append(frame)
        sprites.append(cur)
    out = []
    for s in sprites:
        w = max(len(r) for f in s['rows'] for r in f)
        h = max(len(f) for f in s['rows'])
        warn = []
        if any(len(r) != w for f in s['rows'] for r in f) or any(len(f) != h for f in s['rows']):
            warn.append('ragged rows/frames (padded with transparency)')
        frames = []
        for f in s['rows']:
            g = artlib.Grid(w, h)
            for y, r in enumerate(f):
                for x, c in enumerate(r):
                    if c in '. ': continue
                    if c not in s['key']:
                        warn.append('unknown key %r at %d,%d' % (c, x, y)); continue
                    g.set(x, y, s['key'][c])
            frames.append(g)
        out.append({'name': s['name'], 'frames': frames, 'anchor': s['anchor'], 'tags': s['tags'],
                    'fps': s.get('fps'), 'durations': s.get('durations'), 'tile': s.get('tile'), 'warn': warn})
    return out

def from_module(item):
    if isinstance(item, dict):
        d = dict(item); d.setdefault('anchor', (0, 0)); d.setdefault('tags', {}); d.setdefault('warn', [])
        return d
    _, name, frames, ax, ay, *rest = item
    meta = rest[0] if rest else {}
    return {'name': name, 'frames': frames if isinstance(frames, list) else [frames], 'anchor': (ax, ay),
            'tags': meta.get('tags', {}), 'fps': meta.get('fps'), 'durations': meta.get('durations'),
            'tile': meta.get('tile'), 'variants': meta.get('variants'), 'warn': []}

def load_pack(pack):
    pack = pathlib.Path(pack)
    meta = json.loads((pack / 'pack.json').read_text())
    pal = json.loads((pack / meta.get('palette', 'palette.json')).read_text())
    if 'colors' in pal and isinstance(pal['colors'], list):
        pal = {'c%d' % i: h for i, h in enumerate(pal['colors'])}
    sprites = []
    for f in sorted((pack / 'sprites').glob('*.px')) if (pack / 'sprites').exists() else []:
        sprites += parse_px(f)
    if (pack / 'art').exists():
        sys.path.insert(0, str(pack / 'art'))
        import importlib, os
        os.environ['PIXEL_SCENE'] = str(pack)
        artlib.ROOT = pack
        for p in sorted((pack / 'art').glob('*.py')):
            mod = importlib.import_module(p.stem)
            if hasattr(mod, 'export'):
                sprites += [from_module(it) for it in mod.export() if (isinstance(it, dict) or it[0] == 'sprite')]
    return meta, pal, sprites

# ---------------------------------------------------------------- rendering
def colour(pal, slot):
    if slot.startswith('#'):
        return cl.hex_to_rgb(slot)
    if slot not in pal:
        raise KeyError(slot)
    return cl.hex_to_rgb(pal[slot])

def to_image(g, pal, missing):
    im = Image.new('RGBA', (g.w, g.h), (0, 0, 0, 0))
    px = im.load()
    for y in range(g.h):
        for x in range(g.w):
            v = g.a[y][x]
            if v is None: continue
            try:
                px[x, y] = colour(pal, v) + (255,)
            except KeyError:
                missing.add(v); px[x, y] = (255, 0, 255, 255)
    return im

def durations(s):
    n = len(s['frames'])
    if s.get('durations'):
        d = list(s['durations']) + [s['durations'][-1]] * n
        return d[:n]
    return [int(round(1000 / (s.get('fps') or 8)))] * n

def lone_pixels(g):
    n = 0
    for y in range(g.h):
        for x in range(g.w):
            v = g.a[y][x]
            if v is None: continue
            if all(g.get(x + dx, y + dy) != v for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                n += 1
    return n

def export(pack, scale=None, only=None):
    pack = pathlib.Path(pack)
    meta, pal, sprites = load_pack(pack)
    scale = scale or meta.get('scale', 6)
    bg = cl.hex_to_rgb(meta.get('preview_bg', '#2a2836'))
    out = pack / 'out'
    out.mkdir(exist_ok=True)
    if only:
        sprites = [s for s in sprites if s['name'] in only]
    rendered = {}
    report = []
    for s in [s for s in sprites if s.get('kind') == 'scene']:
        export_scene(s, out, meta.get('scene_scale', 3))
    sprites = [s for s in sprites if s.get('kind') != 'scene']
    for s in sprites:
        missing = set()
        frames = [to_image(g, pal, missing) for g in s['frames']]
        w, h = frames[0].size
        strip = Image.new('RGBA', (w * len(frames), h), (0, 0, 0, 0))
        for i, f in enumerate(frames):
            strip.paste(f, (i * w, 0))
        name = s['name']
        strip.save(out / (name + '.png'))
        strip.resize((strip.width * scale, strip.height * scale), Image.NEAREST).save(out / ('%s@%dx.png' % (name, scale)))
        durs = durations(s)
        js = {'frames': [{'filename': '%s %d' % (name, i), 'frame': {'x': i * w, 'y': 0, 'w': w, 'h': h},
                          'sourceSize': {'w': w, 'h': h}, 'duration': durs[i]} for i in range(len(frames))],
              'meta': {'image': name + '.png', 'size': {'w': strip.width, 'h': h}, 'scale': '1',
                       'pivot': {'x': s['anchor'][0], 'y': s['anchor'][1]},
                       'frameTags': [{'name': k, 'from': a, 'to': b, 'direction': 'forward'} for k, (a, b) in s['tags'].items()]}}
        if s.get('tile'):
            js['meta']['tile'] = s['tile']
        (out / (name + '.json')).write_text(json.dumps(js, indent=1))
        if len(frames) > 1:
            gif = []
            for f in frames:
                c = Image.new('RGBA', f.size, bg + (255,)); c.alpha_composite(f)
                gif.append(c.convert('RGB').resize((w * scale, h * scale), Image.NEAREST))
            gif[0].save(out / (name + '.gif'), save_all=True, append_images=gif[1:], duration=durs, loop=0, optimize=False)
        rendered[name] = (s, frames)
        cols = set()
        for f in frames:
            a = np.array(f).reshape(-1, 4)
            cols |= {tuple(c) for c in a[a[:, 3] > 0][:, :3]}
        lone = sum(lone_pixels(g) for g in s['frames'])
        warn = list(s['warn']) + (['no colour for slots: ' + ', '.join(sorted(missing))] if missing else [])
        report.append((name, w, h, len(frames), len(cols), lone, warn))
    if rendered:
        atlas(rendered, out)
        contact(rendered, out, scale, bg)
        silhouettes(rendered, out, scale)
    for m in meta.get('maps', []):
        render_map(pack / m, rendered, pal, out, scale, bg)
    print('%-22s %7s %6s %7s %5s  %s' % ('sprite', 'size', 'frames', 'colours', 'lone', 'notes'))
    bad = False
    for name, w, h, n, c, lone, warn in report:
        bad |= bool(warn)
        print('%-22s %3dx%-3d %6d %7d %5d  %s' % (name, w, h, n, c, lone, '; '.join(warn)))
    print('wrote', out, '(look at contact.png and silhouettes.png)')
    print('lone = pixels sharing no edge with their colour: fine as deliberate highlights, eyes and sparkle; '
          'many of them read as noise')
    return not bad

def export_scene(s, out, scale, prescaled=None):
    """a whole animated picture (art module returns {'kind': 'scene', 'images': [PIL frames]}):
    NAME.png (first frame, 1x), NAME@Nx.png, NAME.gif and NAME.mp4 (both scaled), no atlas.

    prescaled=True (or 'prescaled': True in the scene dict): the frames are already at delivery
    size (a screen-resolution light layer, post.Post.image()), so nothing is resized: NAME.png is
    the delivered frame, the MP4 keeps the frames' own size (an odd size is padded by one black
    pixel, never rescaled), and an APNG (NAME.png animated as NAME.apng) is written because a
    255-colour GIF bands soft light. scale then only names the @Nx file (the scene's 'scale')."""
    import shutil, subprocess
    frames = [f.convert('RGB') for f in s['images']]
    name, (w, h) = s['name'], frames[0].size
    if prescaled is None:
        prescaled = bool(s.get('prescaled'))
    if prescaled:
        scale = s.get('scale', scale)
        frames[0].save(out / (name + '.png'))
        frames[0].save(out / ('%s@%dx.png' % (name, scale)))
        if len(frames) > 1:
            ms = durations(dict(s, frames=frames))
            frames[0].save(out / (name + '.apng'), format='PNG', save_all=True, append_images=frames[1:],
                           duration=ms, loop=0)
            pal = [f.quantize(colors=255, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE) for f in frames]
            pal[0].save(out / (name + '.gif'), save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=False)
            if shutil.which('ffmpeg'):
                W2, H2 = w + w % 2, h + h % 2                         # yuv420p needs even sides: pad, don't scale
                fps = s.get('fps') or 1000.0 / ms[0]
                p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W2, H2),
                                      '-r', '%g' % fps, '-i', '-', '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                                      '-movflags', '+faststart', str(out / (name + '.mp4'))], stdin=subprocess.PIPE)
                for f in frames:
                    if (W2, H2) != (w, h):
                        g = Image.new('RGB', (W2, H2)); g.paste(f, (0, 0)); f = g
                    p.stdin.write(f.tobytes())
                p.stdin.close(); p.wait()
        print('scene %s: %dx%d prescaled, %d frames -> %s.png%s' % (name, w, h, len(frames), name,
              ', .apng, .gif, .mp4' if len(frames) > 1 else ''))
        return
    frames[0].save(out / (name + '.png'))
    big = [f.resize((w * scale, h * scale), Image.NEAREST) for f in frames]
    big[0].save(out / ('%s@%dx.png' % (name, scale)))
    if len(frames) > 1:
        ms = durations(dict(s, frames=frames))
        pal = [f.quantize(colors=255, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE) for f in big]
        pal[0].save(out / (name + '.gif'), save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=False)
        if shutil.which('ffmpeg'):
            s2 = scale + scale % 2
            fps = s.get('fps') or 1000.0 / ms[0]                         # the scene's own rate, not the GIF's rounded one
            p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (w * s2, h * s2),
                                  '-r', '%g' % fps, '-i', '-', '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                                  '-movflags', '+faststart', str(out / (name + '.mp4'))], stdin=subprocess.PIPE)
            for f in frames:
                p.stdin.write(f.resize((w * s2, h * s2), Image.NEAREST).tobytes())
            p.stdin.close(); p.wait()
    print('scene %s: %dx%d, %d frames -> %s.png, .gif%s' % (name, w, h, len(frames), name, ', .mp4' if len(frames) > 1 else ''))

def atlas(rendered, out):
    items = [(name, i, f) for name, (s, fr) in rendered.items() for i, f in enumerate(fr)]
    items.sort(key=lambda t: -t[2].size[1])
    width = max(256, max((f.size[0] for _, _, f in items), default=1))
    x = y = rowh = 0
    pos = []
    for name, i, f in items:
        w, h = f.size
        if x + w > width:
            x, y, rowh = 0, y + rowh + 1, 0
        pos.append((name, i, f, x, y)); x += w + 1; rowh = max(rowh, h)
    sheet = Image.new('RGBA', (width, y + rowh), (0, 0, 0, 0))
    frames = {}
    for name, i, f, x, y in pos:
        sheet.paste(f, (x, y))
        s = rendered[name][0]
        frames['%s %d' % (name, i)] = {'frame': {'x': x, 'y': y, 'w': f.size[0], 'h': f.size[1]},
                                       'duration': durations(s)[i]}
    sheet.save(out / 'atlas.png')
    (out / 'atlas.json').write_text(json.dumps({'frames': frames, 'meta': {'image': 'atlas.png', 'size': {'w': sheet.width, 'h': sheet.height}}}, indent=1))

def contact(rendered, out, scale, bg):
    cells = []
    for name, (s, fr) in rendered.items():
        w, h = fr[0].size
        row = Image.new('RGBA', ((w + 2) * len(fr) * scale, h * scale + 14), bg + (255,))
        for i, f in enumerate(fr):
            row.alpha_composite(f.resize((w * scale, h * scale), Image.NEAREST), ((w + 2) * i * scale, 14))
        ImageDraw.Draw(row).text((2, 1), '%s %dx%d%s' % (name, w, h, ' x%d' % len(fr) if len(fr) > 1 else ''), fill=(230, 230, 230))
        cells.append(row)
    if not cells: return
    W = min(1600, max(c.width for c in cells))
    # flow cells into rows
    rows, cur, cw = [], [], 0
    for c in cells:
        if cur and cw + c.width + 8 > W:
            rows.append(cur); cur, cw = [], 0
        cur.append(c); cw += c.width + 8
    rows.append(cur)
    H = sum(max(c.height for c in r) + 8 for r in rows)
    sheet = Image.new('RGBA', (max(W, max(sum(c.width + 8 for c in r) for r in rows)), H), bg + (255,))
    y = 0
    for r in rows:
        x = 0
        for c in r:
            sheet.paste(c, (x, y)); x += c.width + 8
        y += max(c.height for c in r) + 8
    sheet.convert('RGB').save(out / 'contact.png')

def silhouettes(rendered, out, scale):
    imgs = []
    for name, (s, fr) in rendered.items():
        f = fr[0]
        a = np.array(f)[..., 3] > 0
        im = Image.fromarray(np.where(a, 30, 235).astype(np.uint8), 'L').resize((f.size[0] * scale, f.size[1] * scale), Image.NEAREST)
        imgs.append(im)
    if not imgs: return
    W = sum(i.width + 10 for i in imgs); H = max(i.height for i in imgs)
    sheet = Image.new('L', (min(W, 4000), H + 10), 235)
    x = 0
    for i in imgs:
        if x + i.width > sheet.width: break
        sheet.paste(i, (x, 5)); x += i.width + 10
    sheet.save(out / 'silhouettes.png')

def render_map(path, rendered, pal, out, scale, bg):
    txt = pathlib.Path(path).read_text().splitlines()
    tileset, tile, corners, props, sec = None, 16, [], [], None
    for line in txt:
        if not line.strip() or line.lstrip().startswith('#'): continue
        m = re.match(r'^(tileset|tile)\s*:\s*(\S+)', line)
        if m:
            if m.group(1) == 'tileset': tileset = m.group(2)
            else: tile = int(m.group(2))
            continue
        if line.strip() in ('corners:', 'props:'):
            sec = line.strip()[:-1]; continue
        if sec == 'corners': corners.append(line.strip())
        elif sec == 'props':
            p = line.split(); props.append((p[0], int(p[1]), int(p[2]), int(p[3]) if len(p) > 3 else 0))
    if tileset not in rendered:
        print('map %s: no tileset sprite %r' % (path, tileset)); return
    tiles = rendered[tileset][1]
    variants = rendered[tileset][0].get('variants') or {}
    rows, cols = len(corners) - 1, len(corners[0]) - 1
    im = Image.new('RGBA', (cols * tile, rows * tile), bg + (255,))
    for ty in range(rows):
        for tx in range(cols):
            c = lambda x, y: 1 if corners[y][x] == '#' else 0
            idx = c(tx, ty) * 8 + c(tx + 1, ty) * 4 + c(tx, ty + 1) * 2 + c(tx + 1, ty + 1)
            opts = variants.get(idx) or variants.get(str(idx)) or [idx]
            pick = opts[(tx * 7 + ty * 13 + (tx * ty) % 5) % len(opts)]
            im.alpha_composite(tiles[pick % len(tiles)], (tx * tile, ty * tile))
    for name, x, y, fi in sorted(props, key=lambda p: p[2]):
        if name not in rendered: print('map: unknown prop', name); continue
        s, fr = rendered[name]
        f = fr[fi % len(fr)]
        im.alpha_composite(f, (x - s['anchor'][0], y - s['anchor'][1]))
    p = out / (pathlib.Path(path).stem + '.png')
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).convert('RGB').save(p)

KEYCHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*+=?@^~<>:;!|_'

def png_to_px(image, palette, name=None):
    """a PNG (e.g. pixelate output) as .px text keyed to a palette's slots, for hand editing"""
    pal = json.loads(pathlib.Path(palette).read_text()) if str(palette).endswith('.json') else None
    if pal is None:
        hexes = cl.palette_list(cl.load_palette(palette)); pal = {'c%d' % i: h for i, h in enumerate(hexes)}
    if 'colors' in pal and isinstance(pal['colors'], list):
        pal = {'c%d' % i: h for i, h in enumerate(pal['colors'])}
    slots = list(pal.keys())
    lab = cl.rgb_to_oklab(np.array([cl.hex_to_rgb(pal[k]) for k in slots], float))
    im = np.array(Image.open(image).convert('RGBA'))
    h, w = im.shape[:2]
    idx = cl.nearest(cl.rgb_to_oklab(im[..., :3].reshape(-1, 3).astype(float)), lab).reshape(h, w)
    used = sorted({int(i) for i, a in zip(idx.ravel(), im[..., 3].ravel()) if a >= 128})
    key = {}
    for i in used:
        c = next((ch for ch in (slots[i][0], slots[i][0].upper(), slots[i][-1]) if ch not in key.values() and ch not in '. '), None)
        key[i] = c or next(ch for ch in KEYCHARS if ch not in key.values())
    rows = [''.join(key[int(idx[y, x])] if im[y, x, 3] >= 128 else '.' for x in range(w)) for y in range(h)]
    head = ['sprite: %s' % (name or pathlib.Path(image).stem), 'key: ' + ' '.join('%s=%s' % (key[i], slots[i]) for i in used), 'frame']
    return '\n'.join(head + rows) + '\n'

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    if a[0] == '--topx':                         # assets.py --topx IMG PALETTE [NAME]
        print(png_to_px(a[1], a[2], a[3] if len(a) > 3 else None), end=''); sys.exit(0)
    sc = opt('--scale'); only = opt('--only')
    ok = export(a[0], int(sc) if sc else None, set(only.split(',')) if only else None)
    sys.exit(0 if ok else 1)
