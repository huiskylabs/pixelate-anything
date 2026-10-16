#!/usr/bin/env python3
"""Style presets: the decisions that make a modern pixel-art look, written down as data.

usage: styles.py                 list the presets
       styles.py NAME            print one preset
       styles.py NAME IMAGE [--scale N]   check a rendered frame against the preset (budget + grid)

    import styles, stats
    st = styles.get('neon-noir')
    st['res']            # 'native': light fields per art pixel, nearest-neighbour upscale last
    st['blend']          # ('multiply', 'add'): wall wash multiplies, the exit's outer glow adds
    st['ramp']           # palette.ramp(style=...) to build materials with
    stats.budget(frame_1x, 'neon-noir')      # [] when the frame sits inside the measured numbers
    styles.check(frame_1x, 'neon-noir', big=frame_5x)   # budget + native-cell + banned-op report

Each preset is measured from one reference game (study/NN, guides/styles.md) and says:
  res          'none' (no light layer: light is palette steps), 'native' (the light layer is
               computed per art pixel, cells stay flat) or 'screen' (smooth inside each art pixel)
  blend        the light layer's blend modes (post.BLENDS), in order of use
  dither       the dither vocabulary: () none, 'checker' (50% checkerboard) or 'bayer4', each with
               where it is allowed (dither_where)
  outline      'none', 'own' (the material's darkest step), 'part' (per part), 'selective'
               (lit side material, shadow side near-black), 'black' (full #000 silhouette),
               'actors' (only actors and interactive objects)
  ramp         palette.ramp style names for materials (first = default) and ramp_kw
  allowed_post / banned_post   post.Post methods the style may / must not use
  budgets      stats rules {metric: (lo, hi)} measured on the reference, with headroom
  motion       'stepped' (hold tables, 2-12 fps) or 'subpixel' (actors move in screen pixels)
  scale, size  integer delivery scale and native canvas size; fps
  colours      rough count of authored colours on screen
The two-layer rule: the pixel layer is always strict (slots, integer grid, no anti-aliasing,
nearest-neighbour integer scale). The light layer is optional, generated in code from the scene's
own masks, and declared here (res, blend). Nothing is hand-painted and nothing is AI-generated.
"""
import copy, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

_SOFT = ('light', 'lightmap', 'glow', 'shaft', 'flare', 'streak', 'band', 'tint_field', 'fade', 'fog',
         'motes', 'over', 'ambient', 'darkness')
_FILTERS = ('vignette', 'grain', 'scanlines', 'aberration')

STYLES = {
    'contre-jour': dict(
        ref='01 Sword & Sworcery', what='backlit night stage: flat silhouettes, all softness in a screen light layer '
                                        'composited between depth planes',
        res='screen', blend=('screen',), stack=True,
        dither=(), dither_where='none',
        outline='none', rims='1 px directional rims on the light side, dotted on far planes',
        ramp=('between', 'lofi'), ramp_kw=dict(between=('#0d151a', '#a07167')),
        palette='about 20 colours: one navy covers 55-70%, a rose bridge ramp, 3-5 emitter accents',
        haze=dict(fog='#1c2a35', levels=(0.12, 0.25, 0.40)),
        allowed_post=('light', 'shaft', 'flare', 'streak', 'glow', 'motes', 'rain:hair', 'fog'),
        banned_post=_FILTERS,
        budgets={'L<0.25': (0.55, None), 'L>0.6': (None, 0.02), 'L>0.75': (None, 0.003), 'C>0.08': (None, 0.02),
                 'median_C': (None, 0.035)},
        motion='stepped', fps=12, scale=3, size=(640, 360), colours=22,
        figures='20-30 px, 1 px legs, no outline'),
    'pastel-cell': dict(
        ref='02 Celeste', what='high-key one-hue mood: undithered sky strata, flat cloud masses, native bloom from cloud masks',
        res='native', blend=('screen',), stack=False,
        dither=(), dither_where='none',
        outline='actors', outline_colour='dark violet (L .37-.44, h 280-300), never black',
        ramp=('window',), ramp_kw=dict(window=(245, 350)),
        palette='45-55 hand colours in one hue window (240-360), lifted floor L .37',
        grade=dict(hue_window=(245, 350), floor_L=0.37),
        allowed_post=('glow', 'band', 'tint_field', 'rain:cell'),
        banned_post=_FILTERS + ('darkness', 'rain:hair'),
        budgets={'hue[240,360]': (0.97, None), 'L<0.35': (None, 0.003), 'median_L': (0.6, None)},
        motion='stepped', fps=30, scale=6, size=(320, 180), colours=50,
        figures='11x18 with a hair trail, the frame\'s darkest pixels are its outline'),
    'native-glow': dict(
        ref='03 Hyper Light Drifter', what='low-key ruins on a vertical light spine; continuous light per art pixel, '
                                           'exponential halos on emitters',
        res='native', blend=('add', 'lerp'), stack=False,
        dither=(), dither_where='none',
        outline='none',
        ramp=('lofi', 'rise'), families=True,
        palette='40-60 base colours in role families (frame, heart, warm, hot, spark, void); frame hue drifts across x',
        allowed_post=('glow:exp', 'band', 'ambient', 'fade', 'vignette:hue', 'motes'),
        banned_post=('grain', 'scanlines', 'aberration', 'rain:hair'),
        budgets={'L[0.2,0.4]': (0.5, None), 'L>=0.7': (None, 0.05), 'black': (None, 0.04), 'L<0.1': (None, 0.05)},
        motion='stepped', fps=12, scale=4, size=(480, 270), colours=50,
        figures='12x27, 7 flat colours, no outline'),
    'hd-overworld': dict(
        ref='04 Sea of Stars', what='3/4 top-down coast: long low-key ramps whose chroma rises to the light, '
                                    'translucent clouds at an altitude on the native grid',
        res='native', blend=('lerp',), stack=False,
        dither=('checker',), dither_where='only between near tones inside clouds',
        outline='part', outline_colour='tinted near-blacks per class: terrain plum, characters navy, foliage green',
        ramp=('rise',),
        palette='100-130 base colours, 5-9 steps per material at 0.05 L a step',
        allowed_post=('over',),
        banned_post=_FILTERS + ('light', 'shaft', 'flare', 'rain:hair'),
        budgets={'median_C': (0.025, 0.06), 'C>0.12': (None, 0.05), 'L>0.8': (None, 0.1), 'median_L': (0.25, 0.5)},
        motion='stepped', fps=12, scale=3, size=(640, 360), colours=120,
        figures='chibi 13x26 (figures.chibi)'),
    'arcade': dict(
        ref='05 Metal Slug 3', what='Neo Geo density: warm hand-modelled actors on a cold dark world; FX are '
                                    'opaque palette sprites, no light layer',
        res='none', blend=('palette-step',), stack=False,
        dither=('checker',), dither_where='only on HUD gauges',
        outline='own',
        ramp=('arcade', 'lofi'), ramp_kw=dict(arcade=dict(steps=7, l_max=0.82)),
        palette='80-130 colours in many 15-colour sprite palettes (era neogeo)',
        era='neogeo',
        allowed_post=(),
        banned_post=_SOFT + _FILTERS,
        budgets={'L<0.25': (0.45, None), 'L>0.75': (None, 0.07), 'actor:median_C': (0.06, None),
                 'world:median_C': (None, 0.03), 'actor/world:detail': (1.8, None)},
        motion='stepped', fps=30, scale=4, size=(304, 224), colours=110,
        figures='heroes 32-40 px (3.6 heads), a boss 80-95 px cut by the frame edge'),
    'tactics': dict(
        ref='06 Into the Breach', what='a 2:1 iso diorama floating in the dark, five greys, rationed colour, '
                                       'hard cast shadows; UI on the screen grid at 1x/2x/3x',
        res='none', blend=('palette-step',), stack=False,
        dither=(), dither_where='none',
        outline='black', spec_strokes='1 px white strokes on upper-left edges of units',
        ramp=('arch', 'neutral'), ramp_kw=dict(neutral=dict(Ls=(0.13, 0.18, 0.24, 0.28, 0.34))),
        palette='about 30 world colours: 5 near-neutral greys > 72%, a 10-step sky, brass, unit accents',
        allowed_post=(),
        banned_post=_SOFT + _FILTERS,
        budgets={'C>0.08': (None, 0.025), 'L<0.3': (0.7, None), 'median_C': (None, 0.02)},
        motion='stepped', fps=12, scale=2, size=(640, 360), colours=30,
        figures='units 24-34 px, black outline'),
    'sticker-iso': dict(
        ref='07 Peterson Freitas', what='full-bleed noon iso: gamut-edge paint, black silhouettes, no light, '
                                        'no shadow, density is the subject',
        res='none', blend=(), stack=False,
        dither=(), dither_where='none',
        outline='black',
        ramp=('flat', 'neutral'),
        palette='60-75 slots (176 exact): 8-12 paints at C >= .18, neutral grey ladder, #000 and #fff',
        allowed_post=(),
        banned_post=_SOFT + _FILTERS + ('cast_shadows',),
        budgets={'black': (0.08, 0.3), 'L<=0.3': (0.3, None), 'L>0.7': (0.15, None), 'C>0.04': (0.2, 0.55)},
        native_cells=0.0,
        motion='stepped', fps=12, scale=4, size=(600, 600), colours=70,
        figures='33-37 px iso people, 3.3 heads'),
    'illustrated': dict(
        ref='08 Owlboy', what='illustration-grade carved stone, a frame drawn into the art, depth by palette haze; '
                              'water is a native palette glaze',
        res='none', blend=('glaze',), stack=False,
        dither=('checker',), dither_where='wear patches on stone (about 13%), none on far layers',
        outline='selective',
        ramp=('living',),
        palette='85-100 colours; environment L .30-.78 C < .06, extremes reserved for actors, FX, HUD',
        haze=dict(far=('#4e3c52', 0.8, 0.4), mid=('#565470', 0.4, 0.8)),
        allowed_post=(),
        banned_post=_SOFT + _FILTERS,
        budgets={'L<0.25': (None, 0.01), 'L>0.85': (None, 0.015), 'L[0.3,0.8]': (0.92, None), 'C>0.08': (None, 0.04),
                 'env:L[0.3,0.78]': (0.97, None), 'env:p95_C': (None, 0.08)},
        motion='stepped', fps=12, scale=2, size=(640, 360), colours=95,
        figures='actors carry the frame\'s extremes (outline L < .25, cores L > .85)'),
    'neon-noir': dict(
        ref='09 Katana ZERO', what='a lit room slab floating in exact black; multiplied wall-wash light per art '
                                   'pixel, one teal exit, one magenta hero',
        res='native', blend=('multiply', 'add'), stack=False,
        dither=('checker',), dither_where='inside paintings only; void fades jitter per column',
        outline='none', rims='1 px warm rim on the lamp side of actors',
        ramp=('lit',),
        palette='about 50 authored: 9-step wood and stone ramps, 6 void blacks, 3-5 tone accents',
        allowed_post=('lightmap', 'band', 'glow:outer', 'fade'),
        banned_post=_FILTERS + ('light:screen', 'rain:hair'),
        budgets={'C>0.1': (None, 0.015), 'black': (0.15, None), 'L>=0.7': (None, 0.035), 'median_C': (None, 0.035)},
        motion='stepped', fps=12, scale=5, size=(384, 216), colours=50,
        figures='38-42 px (figures.thin, h=38 by default), thin limbs, no outline, brightest values in the frame'),
    'cosy-lightmap': dict(
        ref='10 Stardew Valley mine', what='16-bit cosy cave: pixel layer under one smooth multiplied lamp map at '
                                           'screen resolution; the void stays black',
        res='screen', blend=('multiply',), stack=False,
        dither=('checker',), dither_where='wall crowns sinking into the void',
        outline='part', outline_colour='the shared plum dark for every brown material',
        ramp=('plum', 'toy'),
        palette='40-50 albedo colours: 4-6 per material, one shared plum, #000 void, toy-hue creatures',
        allowed_post=('lightmap', 'motes', 'sprite', 'from_world'),
        banned_post=_FILTERS + ('light:screen',),
        budgets={'L<0.1': (0.35, 0.65), 'L>0.8': (None, 0.006), 'C>0.1': (None, 0.015)},
        motion='subpixel', fps=12, scale=4, size=(480, 270), colours=45,
        figures='chibi 13x26 (figures.chibi), outlines per part, camera-following'),
    'lofi': dict(
        ref='lantern-isle (this repo)', what='the toolkit\'s original look: 16-bit-ish palette-step light, '
                                             'Bayer gradients, own-material outlines',
        res='none', blend=('palette-step',), stack=False,
        dither=('bayer4',), dither_where='gradients 10-16 rows wide',
        outline='own',
        ramp=('lofi',),
        palette='40-80 slots over several moods (palettes.js)',
        allowed_post=(),
        banned_post=_SOFT + _FILTERS,
        budgets={'L<0.1': (None, 0.01), 'black': (None, 0.001), 'L>=0.7': (None, 0.04),
                 'L>0.8': (None, 0.02), 'median_C': (0.02, 0.1)},
        # Lantern Isle, 13 frames over the four seasons: L<0.1 0, black 0, L<0.3 .45-.76, L>=0.7 .003-.020,
        # L>0.8 .001-.009, median_L .22-.31, median_C .032-.085. The key (L<0.3, median_L) is left out: lofi
        # covers day scenes too; the rules kept are the style's own (no pure black, rare highlights, low chroma)
        motion='stepped', fps=10, scale=6, size=(320, 180), colours=60,
        figures='sprite-sheet characters'),
}
ALIASES = {'01': 'contre-jour', '02': 'pastel-cell', '03': 'native-glow', '04': 'hd-overworld', '05': 'arcade',
           '06': 'tactics', '07': 'sticker-iso', '08': 'illustrated', '09': 'neon-noir', '10': 'cosy-lightmap',
           'sworcery': 'contre-jour', 'celeste': 'pastel-cell', 'hld': 'native-glow', 'seaofstars': 'hd-overworld',
           'metalslug': 'arcade', 'itb': 'tactics', 'freitas': 'sticker-iso', 'owlboy': 'illustrated',
           'katana': 'neon-noir', 'stardew': 'cosy-lightmap'}
for _k, _v in STYLES.items():
    _v['name'] = _k
    _v.setdefault('native_cells', 0.0 if _v['res'] in ('none', 'native') else None)

def get(name):
    """a copy of a preset by name, reference number ('09') or nickname ('katana')"""
    key = ALIASES.get(str(name).lower(), str(name).lower())
    if key not in STYLES:
        raise KeyError('no style %r: one of %s' % (name, ', '.join(STYLES)))
    return copy.deepcopy(STYLES[key])

def allows(name, op):
    """is post op `op` ('glow', 'rain:hair', 'vignette') allowed in this style?"""
    st = get(name)
    base = op.split(':')[0]
    if op in st['banned_post'] or base in st['banned_post']:
        return False
    if st['res'] == 'none':
        return False
    return not st['allowed_post'] or op in st['allowed_post'] or base in [a.split(':')[0] for a in st['allowed_post']]

def ramps(name, bases, steps=None, **kw):
    """{'rock': '#hex'} -> {'rock0': ...} built with the style's default ramp style"""
    import palette
    st = get(name)
    rs = st['ramp'][0]
    if rs in ('between', 'neutral'):
        rs = 'lofi'
    if rs == 'arcade':
        kw = dict(st['ramp_kw']['arcade'], **kw)
        kw.pop('steps', None)
        steps = steps or 7
    return palette.ramps(bases, steps, style=None if rs == 'lofi' else rs, **kw)

def check(img_1x, name, big=None, scale=None, masks=None, grid=None, pal=None, used=()):
    """everything a style can check on a frame -> list of problems ([] = fine):
    the numeric budget (stats.budget), native cells of the delivered frame `big` for 'none' and
    'native' styles (must be 0), the strict pixel layer against `pal` (pass the pre-light frame
    as img_1x for that), and any post ops listed in `used` that the style bans"""
    import stats
    st = get(name)
    out = list(stats.budget(img_1x, st['name'], masks, grid))
    if big is not None and st['native_cells'] is not None:
        w1 = img_1x.size[0] if hasattr(img_1x, 'size') and not hasattr(img_1x, 'shape') else len(img_1x[0])
        s = scale or max(1, big.size[0] // max(1, w1))
        soft = stats.native_cells(big, s)
        if soft > st['native_cells']:
            out.append('%.2f%% of %dx%d cells are not flat: %s is a %s-grid style' % (100 * soft, s, s, name,
                       'native' if st['res'] == 'native' else 'pixel-only'))
    if pal is not None:
        p = stats.palette_subset(img_1x, pal)
        if not p['ok']:
            out.append('%d pixels (%d colours) outside the palette, e.g. %s' % (p['off_pixels'], p['off_colours'],
                       ', '.join(h for h, _ in p['top'][:3])))
    for op in used:
        if not allows(name, op):
            out.append('post op %r is not part of the %s style' % (op, name))
    return out

def describe(name):
    st = get(name)
    lines = ['%s  (%s)' % (st['name'], st['ref']), '  ' + st['what']]
    for k in ('res', 'blend', 'dither', 'dither_where', 'outline', 'ramp', 'palette', 'allowed_post', 'banned_post',
              'motion', 'fps', 'scale', 'size', 'colours', 'figures'):
        v = st.get(k)
        if isinstance(v, (tuple, list)):
            v = ', '.join(map(str, v)) or '-'
        lines.append('  %-13s %s' % (k, v))
    lines.append('  budgets       ' + ('; '.join('%s %s..%s' % (k, '' if lo is None else lo, '' if hi is None else hi)
                                               for k, (lo, hi) in st['budgets'].items()) or '-'))
    return '\n'.join(lines)

def main(a):
    if not a:
        for k, v in STYLES.items():
            print('%-14s %-26s res %-6s x%d  %s' % (k, v['ref'], v['res'], v['scale'], v['what'][:70]))
        return 0
    if len(a) == 1:
        print(describe(a[0])); return 0
    from PIL import Image
    import stats
    scale = None
    if '--scale' in a:
        i = a.index('--scale'); scale = int(a[i + 1]); del a[i:i + 2]
    img = Image.open(a[1])
    big = None
    if scale and scale > 1:
        big, img = img, stats.to_native(img, scale)
    probs = check(img, a[0], big=big, scale=scale)
    print('\n'.join(probs) if probs else 'on the %s budget' % get(a[0])['name'])
    return 1 if probs else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
