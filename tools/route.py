#!/usr/bin/env python3
"""Style routing: a plain request in, the style to build it in and a pre-filled scene brief out.

usage: route.py "a cosy rainy village at night"            the top 3 styles, with reasons, and what
                                                           the request leaves open (with defaults)
       route.py "..." --brief [STYLE] [-o brief.md]        the 11-section brief, pre-filled for the
                                                           top style (or STYLE), to finish by hand; a
                                                           small ask (a palette, one sprite, an icon
                                                           set, a photo, assets, music) gets a short
                                                           brief instead
       route.py "..." --brief --full                       the 11 sections even for a small ask
       route.py --lint brief.md                            self-critique of a finished brief: what
                                                           is still vague, missing or thin
       route.py --catalog                                  regenerate guides/toolkit.md, every tool
       route.py --selftest [-v]                            route the regression cases (CASES)

    import route
    r = route.route('一个雨夜里温馨的小村庄')
    r['picks'][0]        # {'style': 'cosy-lightmap', 'score': 9, 'why': [...], 'projection': ...}
    r['mode']            # 'scene', 'rebuild', 'era', 'assets' or 'music': which guide to read too
    print(route.brief(r['picks'][0]['style'], '一个雨夜里温馨的小村庄'))

Picking the style is the decision that sets everything after it: where the light lives (none,
native or screen), how ramps bend, outlines, dither, canvas and scale, figure sizes, motion rates
and the numbers a finished frame must hit (tools/styles.py, guides/styles.md). The router reads the
request for five kinds of signal (subject, mood and key, time and weather, what it is for, a named
reference game or example) and scores every preset. It is a starting point: read the reasons,
override it when the request means something else, and say which style you chose and why.

Its subject hints are techniques (how to draw rain, stone, a boat), each naming the primitive in tools/
that does the work. Finished objects are drawn in the scene's own code; references/assets holds
examples of them to study, never to call.

The brief it writes is the template from references/craft.md with every section the style decides
already filled in. The scene-specific sections (the objects, the lived-in details, the palette by
role, the light list, the motion table) are left as TODO prompts: write them to the density of
examples/lantern-isle/BRIEF.md before building anything.

A one-line request ("make me a pixel island") is not a brief. gaps() lists what the request leaves
open (time and weather, phases, figures, purpose and outputs, music, projection, the style itself)
and the default each one takes for the chosen style. The agent expands the request into the full
brief using those defaults, runs lint() on it as a self-critique, and shows the user the brief with
the list of choices it made. If the user says OK, one round turns the one line into a Lantern Isle
level brief; if not, they change what they want and the brief is revised, a round at a time.
"""
import re, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import styles

# ---------------------------------------------------------------- what each style is for
# signals: (weight, words). English words match whole words (plurals with -s too), Chinese as substrings.
# A named reference game or a repo example is the strongest signal (6); subject and mood 2-3.
ROUTE = {
    'lofi': dict(
        pick_if='a calm looping cover for music: a cottage, an island, seasons, a window at night; light drawn '
                'with palette colours only',
        projection='side', example='examples/lantern-isle (BRIEF.md is the bar)', frames=(None, 30),
        signals=[(6, ['lantern isle', 'lantern-isle', '灯塔岛']),
                 (4, ['lofi', 'lo-fi', 'music video', 'study music', '音乐视频', '学习音乐', '助眠']),
                 (3, ['cover', 'loop for', 'hours', 'seasons', 'four seasons', 'chill', 'relax', 'cozy cottage',
                      '封面', '循环', '四季', '季节', '放松', '治愈', '小木屋']),
                 (2, ['cottage', 'cabin', 'window', 'diorama', 'island', 'calm', 'peaceful', 'quiet', 'lighthouse',
                      '小屋', '窗', '小岛', '岛', '安静', '宁静', '灯塔', 'cafe', 'coffee', 'bedroom', 'desk', 'rooftop',
                      '咖啡', '卧室', '书桌', '屋顶'])],
        rules=['Every object is a hand-authored slot map (sprites.js or artlib), never a primitive shape.',
               'Gradients are bands with 10-16 row Bayer transitions; no other dither.',
               'Light is warm palette slots: window glow, lantern pools and rims, a few highlight pixels.'],
        tools=['ramps per material (palette.ramp(style="lofi"))',
               'skies and gradients as bands with 10-16 row Bayer transitions (engine bands() and blit)',
               'every object a hand-authored slot map (artlib.Grid, exported to sprites.js)',
               'lamp and window flicker on hold tables (sceneDynamic flick())'],
        never=['glow blur, bloom, lens effects, soft shadows', 'narrow gradient bands that read as stripes']),
    'pastel-cell': dict(
        pick_if='a high-key, one-hue mood (pink, violet, dusk), a tiny expressive hero in a big vertical world, '
                'weather; soft glow but still whole pixels',
        projection='side', example='examples/indie/art/rose_squall.py', frames=(120, 30),
        signals=[(6, ['celeste', 'rose squall', '蔚蓝']),
                 (3, ['pastel', 'pink', 'rose', 'dreamy', 'platformer', 'kite', 'glide', 'gliding', 'sea of clouds',
                      '粉', '玫瑰', '梦幻', '平台跳跃', '风筝', '滑翔', '云海']),
                 (2, ['dusk', 'sunset', 'sunrise', 'storm', 'squall', 'wind', 'cliff', 'scarf', 'jump', 'dash', 'cute',
                      'climb', 'climbing', 'mountain', 'summit',
                      '黄昏', '晚霞', '日出', '朝霞', '暴风', '风暴', '悬崖', '围巾', '冲刺', '可爱', '攀爬', '登山', '山顶'])],
        rules=['All hues inside one window (about 245-350); the floor is lifted, no scenery below L .37.',
               'Sky in flat undithered strata locked by tapered wisps; boundaries walk in flat runs.',
               'Rock is a ledged, frayed silhouette with a lit rim and stacked flake dashes, no outline.',
               'Only the actor and one interactive prop are outlined (dark violet); they carry the top chroma.',
               'Bloom only from cloud and emitter masks, computed per art pixel.'],
        tools=['ramps inside one hue window with a lifted floor (palette.ramp(style="window"), palette.grade(hue_window, floor_L))',
               'flat sky strata locked by tapered wisps (sky.strata, sky.wisp, sky.smile)',
               'cloud banks and ledged, frayed rock silhouettes (shapes.cloud_mass, shapes.ledges, shapes.fray)',
               'stacked flake dashes on rock faces (texture.flakes)', 'scarf and hair that trail the hero (sprite.chain)',
               'bloom only from cloud and emitter masks (post.Post(res="native").glow(mask), band, tint_field)',
               'rain as opaque cell columns (Post rain style "cell")', 'landing and dash puffs (fx.burst)'],
        never=['dither', 'vignette, grain, scanlines', 'hairline rain', 'dark scenery']),
    'native-glow': dict(
        pick_if='low-key ancient ruins or tech temples, magenta and cyan, glowing runes and a spine of light; '
                'continuous light snapped to the art grid',
        projection='3/4 top-down', example=None, frames=(96, 12),
        signals=[(6, ['hyper light', 'drifter', 'hld']),
                 (3, ['ruin', 'ruins', 'temple', 'ancient', 'rune', 'runes', 'relic', 'sanctum', 'monolith',
                      '遗迹', '废墟', '神殿', '古代', '符文', '遗物', '圣所']),
                 (2, ['magenta', 'cyan', 'glowing', 'mysterious', 'dungeon', 'tech', 'drone',
                      '品红', '青色', '发光', '神秘', '地牢', '科技', 'underwater', 'reef', 'deep sea', 'abyss', 'jellyfish',
                      '海底', '水下', '珊瑚', '深海', '水母'])],
        rules=['Role families of colour (frame, heart, warm, hot, spark, void); the frame hue drifts across x.',
               'Emitters get exponential halos computed per art pixel; no outlines.',
               'A vertical light band or spine organises the frame; the void stays drawn, not filtered.'],
        tools=['colour in role families, the frame hue drifting across x (palette.families, palette.drift, palette.drift_index)',
               'exponential halos per art pixel from emitter masks, a light band, a fade (post.Post(res="native").glow(kernel="exp"), band, fade)',
               'woven walls (texture.tapestry)', 'runes as your own slot maps (study references/assets/glyphs.py rune)',
               'drifting motes (fx.pixel_motes)'],
        never=['screen-resolution softness', 'grain, scanlines, aberration']),
    'hd-overworld': dict(
        pick_if='a bright adventure world seen from 3/4 above: coasts, villages, cliffs, day into night; long '
                'ramps and translucent clouds',
        projection='3/4 top-down', example=None, frames=(96, 12),
        signals=[(6, ['sea of stars', 'chrono']),
                 (3, ['overworld', 'world map', 'rpg', 'adventure', 'coast', 'atoll', 'party', 'jrpg',
                      '大地图', '世界地图', '冒险', '海岸', '小队', '角色扮演']),
                 (2, ['day', 'sunny', 'bright', 'clouds', 'village', 'tide', 'bridge', 'waterfall',
                      '白天', '晴', '明亮', '云', '村', '潮', '桥', '瀑布'])],
        rules=['Sun and shade are palette steps, not a light layer: light.Light.mask / apply for pools, '
               "iso.Iso(camera='topdown').cast_shadows for hard cast shadows; post.over only for translucent clouds.",
               'A sunny read comes from contrast inside the low-key budget: a few bright lit faces and sparkle on '
               'the water against deep shade, not from lifting everything.',
               'Ramps of 5-9 steps at about 0.05 L, chroma rising toward the light (ramp style rise).',
               'Outlines per class in tinted near-blacks (terrain plum, characters navy, foliage green).',
               'Clouds are a translucent layer at an altitude, thinning as terrain rises into them.'],
        tools=['ramps with chroma rising toward the light (palette.ramp(style="rise"))',
               'coursed slabs and pillow blocks (layout.ashlar, texture.shade_cells)', 'round shingled canopies (veg.leaf_scales)',
               'sea bands, foam rings and falls (water.depth_bands, water.foam_rings, water.waterfall)',
               'translucent clouds at an altitude (shapes.cloud, post.over)',
               'chibi figures as your own slot maps (study references/assets/figures.py chibi)'],
        never=['screen light shafts or flares', 'hairline rain', 'filters']),
    'arcade': dict(
        pick_if='loud action: soldiers, machines, explosions, a boss; hand-modelled warm actors on a cold world, '
                'effects as opaque sprites',
        projection='side', example=None, frames=(120, 30),
        signals=[(6, ['metal slug', 'neo geo', 'neogeo']),
                 (3, ['explosion', 'boss', 'battle', 'soldier', 'tank', 'run and gun', 'shoot', 'arcade', 'mech',
                      '爆炸', 'boss战', '战斗', '士兵', '坦克', '射击', '街机', '机甲']),
                 (2, ['action', 'fire', 'gun', 'smoke', 'debris', 'war', 'chaos', 'robot',
                      '动作', '火', '枪', '烟', '碎片', '战争', '混乱', '机器人'])],
        rules=['Actors carry the chroma and the detail (at least 1.8x the world); the world stays cold and dark.',
               'Effects are opaque palette sprites: fireballs, smoke, muzzle flashes, debris; no light layer.',
               'Outlines in each material\'s own darkest step; animation on hold tables at 30 fps.'],
        tools=['hand-modelled warm ramps (palette.ramp(style="arcade"))',
               'effects as opaque palette sprites (fx.fireball, fx.smoke_puff, fx.trail, fx.muzzle, fx.casing, fx.debris)',
               'hold tables at 30 fps, shake and timewarp (anim.Timeline, anim.shake, anim.timewarp)',
               'machine surfaces (texture.pocks, texture.segments, texture.panels)',
               'console limits (pixelate era IMG --era neogeo)'],
        never=['any soft light layer', 'filters']),
    'tactics': dict(
        pick_if='a calm, readable strategy board: a 2:1 iso diorama floating in the dark, rationed colour, UI',
        projection='2:1 iso', example='examples/projections', frames=(96, 12),
        signals=[(6, ['into the breach', 'itb']),
                 (3, ['tactics', 'tactical', 'strategy', 'siege', 'battle', 'army', 'war', 'turn-based', 'turn based', 'board', 'grid', 'squad',
                      '战术', '策略', '回合', '棋盘', '网格']),
                 (2, ['ui', 'hud', 'minimal', 'mechs', 'units', 'map', '界面', '极简', '单位'])],
        rules=['Five near-neutral greys cover most of the frame; colour is rationed to units and threats.',
               'Black outlines with 1 px white spec strokes on upper-left edges; hard cast shadows.',
               'UI sits on the screen grid at 1x/2x/3x, crisp, never scaled softly.'],
        tools=['the board from 2:1 iso boxes (iso.Iso.render)',
               'architecture ramps and a near-neutral grey ladder (palette.ramp(style="arch"), palette.neutral_ramp)',
               'the diorama floating in the dark (compose.stage)', 'crisp UI text on the screen grid (pixfont.draw)'],
        never=['soft light', 'filters', 'saturated scenery']),
    'sticker-iso': dict(
        pick_if='a dense, sunny isometric town where the crowd and the little stories are the subject',
        projection='2:1 iso', example='examples/san-francisco (iso diorama)', frames=(96, 12),
        signals=[(6, ['freitas', 'eboy']),
                 (3, ['isometric city', 'iso city', 'street', 'market', 'crowd', 'busy', 'town square', 'traffic',
                      '等距城市', '街道', '集市', '人群', '热闹', '广场', '车流', '夜市', '古镇', '庙会', 'festival', 'fair']),
                 (2, ['isometric', 'iso', 'city', 'town', 'noon', 'shops', 'tram', 'canal',
                      '等距', '城市', '小镇', '中午', '商店', '电车', '运河'])],
        rules=['Paint at the gamut edge, black silhouettes, no light and no shadows.',
               'Density is the subject: a readable little story in every 100 px window.',
               'Trees are leaf-glyph canopies on black; people are 3.3-head iso figures.'],
        tools=['iso boxes (iso.Iso)', 'flat paints at the gamut edge (palette.ramp(style="flat"))',
               'leaf-glyph canopies on black (veg.leaf_glyphs)',
               'people and cars as your own slot maps (study references/assets/figures.py iso_person and props.py car, pole, tyre)',
               'crowds and traffic on lanes (compose.populate, compose.strips, anim.lane_offset)'],
        never=['light of any kind', 'cast shadows', 'empty areas']),
    'illustrated': dict(
        pick_if='an illustration-grade sky world: floating islands, carved stone, a monument, painterly depth '
                'by palette haze',
        projection='side', example=None, frames=(96, 12),
        signals=[(6, ['owlboy']),
                 (3, ['floating island', 'sky island', 'monument', 'carved', 'statue', 'painterly', 'illustration',
                      'viaduct', 'aqueduct', 'gorge', 'canyon', 'stone arch', '高架桥', '渡槽', '峡谷', '石拱',
                      '浮空岛', '天空岛', '纪念碑', '雕刻', '雕像', '插画']),
                 (2, ['sky', 'clouds', 'detailed', 'ornate', 'stone', 'vines', 'roots', 'flying',
                      '天空', '细致', '华丽', '石头', '藤', '根', '飞', 'dragon', 'giant', 'colossus', 'castle', 'airship',
                      '龙', '巨人', '城堡', '飞艇'])],
        rules=['The environment stays in L .30-.78 at low chroma; the extremes are for actors, effects and HUD.',
               'Stone is carved: cells with a lit rim, checker wear, selective outlines.',
               'Depth comes from palette haze per plane, never from blur; a frame of foliage is drawn into the art.'],
        tools=['living ramps hazed per plane (palette.ramp(style="living"), palette.haze)',
               'carved stone cells with a lit rim (layout.ashlar, layout.polar_blocks, texture.shade_cells)',
               'leaf masses, vines and ferns (veg.leafmass, veg.vine, veg.fern)', 'glazed water (water.reflect)',
               'a frame of foliage drawn into the art (compose.frame_mask)'],
        never=['soft light layers', 'filters', 'dark scenery']),
    'neon-noir': dict(
        pick_if='a neon-lit night interior or city: noir, crime, a bar, a club, rain on neon; one lit room in black',
        projection='side', example=None, frames=(120, 12),
        signals=[(6, ['katana zero', 'katana']),
                 (3, ['neon', 'noir', 'cyberpunk', 'samurai', 'ninja', 'club', 'bar', 'crime', 'detective', 'nightclub', 'synthwave',
                      '霓虹', '黑色电影', '赛博', '武士', '忍者', '夜店', '酒吧', '犯罪', '侦探']),
                 (2, ['night city', 'alley', 'motel', 'hotel', 'apartment', 'rain city', 'magenta',
                      '夜城', '小巷', '旅馆', '公寓', '城市夜', 'space station', 'spaceship', 'sci-fi', 'scifi', 'android',
                      '太空站', '飞船', '科幻', '太空', '机器人'])],
        rules=['A lit room slab floating in exact black; a multiplied wall-wash light per art pixel.',
               'One teal exit and one magenta hero carry the colour; everything else is wood, stone and black.',
               'Actors have no outline, only a 1 px warm rim on the lamp side.'],
        tools=['lit wood and stone ramps (palette.ramp(style="lit"))',
               'one multiplied wall-wash per art pixel, a band, an outer glow, a fade '
               '(post.Post(res="native").lightmap, band, glow(kernel="outer"), fade)',
               'the room slab fading into exact black (light.void_fade)',
               'slim 38-42 px actors as your own slot maps (study references/assets/figures.py thin)',
               'wood panels and slats (texture.panels, texture.slats)'],
        never=['screen-blend light', 'hairline rain', 'grain, scanlines, aberration']),
    'cosy-lightmap': dict(
        pick_if='a warm, cosy 16-bit place at night or underground: a farm, a cave, a cabin interior, lamps in '
                'the dark; one smooth multiplied lamp map',
        projection='3/4 top-down', example=None, frames=(96, 12),
        signals=[(6, ['stardew', 'harvest moon']),
                 (3, ['cozy', 'cosy', 'farm', 'mine', 'cave', 'lamp', 'lantern', 'cabin interior', 'village at night',
                      '温馨', '农场', '矿洞', '洞穴', '油灯', '灯笼', '屋内', '夜晚的村']),
                 (2, ['warm', 'night', 'village', 'harvest', 'torch', 'underground', 'home',
                      '温暖', '夜', '村', '丰收', '火把', '地下', '家'])],
        rules=['Albedo palette of 4-6 tones per material sharing one plum dark; outlines per part in that plum.',
               'One smooth lamp map multiplied at screen resolution; the void stays #000 inside the halo.',
               'Ground reads as paired cells, a lit cap over its shadow (pebbles, cobbles, tilled rows, planks); '
               'built walls are pillow blocks with plum seams.',
               'Many small warm sources (windows, lamps, a hearth) each pool their own light; between the pools the '
               'world sinks to the plum dark, never to grey.'],
        tools=['albedo ramps sharing one plum dark (palette.ramp(style="plum"), palette.ramp(style="toy"))',
               'one smooth multiplied lamp map at screen resolution (post.Post(res="screen").lightmap)',
               'ground as paired cells (texture.pebbles)', 'built walls as pillow blocks (layout.ashlar, texture.shade_cells)',
               'the edge into the void (shapes.void_edge)',
               'chibi figures as your own slot maps (study references/assets/figures.py chibi)', 'rooms (compose.room)'],
        never=['screen-blend light', 'filters', 'a lifted void']),
    'contre-jour': dict(
        pick_if='a cinematic, mysterious night: silhouettes against fog and glowing air, a ritual, a forest, a '
                'pillar of light; soft light at screen resolution between depth planes',
        projection='side', example=None, frames=(192, 12),
        signals=[(6, ['sworcery', 'superbrothers']),
                 (3, ['silhouette', 'backlit', 'contre-jour', 'fog', 'mist', 'cinematic', 'pillar of light', 'ritual',
                      'observatory', 'light pours', 'beam of light', 'midnight', 'vigil', '天文台', '午夜', '守夜',
                      'procession', 'pilgrim', 'shrine', '剪影', '逆光', '雾', '电影感', '光柱', '仪式', '朝圣', '神社']),
                 (2, ['mysterious', 'forest', 'moon', 'moonlight', 'night', 'standing stone', 'eerie', 'solemn',
                      '神秘', '森林', '月', '夜', '立石', '肃穆'])],
        rules=['One navy covers most of the frame; at least 55% of pixels below L .25, highlights rare.',
               'Near planes are flat near-black silhouettes with leafy broken edges; they never take light.',
               'All softness is a screen-resolution light layer composited between depth planes (post.Stack).',
               'Figures are slim, 20-30 px, 1 px legs, no outline; leaf-light flecks take their nearest light\'s colour.'],
        tools=['a bridge ramp between two hues, hazed per plane (palette.ramp_between, palette.haze_levels)',
               'soft light between depth planes at screen resolution (post.Stack, Post(res="screen").light, shaft, flare)',
               'hairline rain (Post rain style "hair")', 'leaf-light flecks in dark foliage (texture.leaflight)',
               'slim 20-30 px figures as your own slot maps (study references/assets/figures.py slim)',
               'a proscenium of near silhouettes (compose.proscenium)'],
        never=['outlines', 'dither', 'light on the near plane', 'filters']),
}

MODES = [
    ('rebuild', 3, ['photo', 'picture of', 'my photo', 'aerial', 'rebuild', 'this image', 'from this',
                    '照片', '这张图', '航拍', '重建']),
    ('era', 3, ['nes', 'game boy', 'gameboy', '8-bit', '8 bit', '16-bit', '16 bit', 'snes', 'genesis', 'mega drive',
                'gba', 'pico-8', 'pico8', '红白机', '8位', '16位', '掌机', '四色绿', '超任', 'famicom']),
    ('assets', 2, ['sprite sheet', 'spritesheet', 'tileset', 'character sheet', 'icons', 'items', 'walk cycle',
                   '精灵表', '图块', '图标', '道具', '行走']),
    ('music', 3, ['soundtrack only', 'just music', 'music loop', 'chiptune', '只要音乐', '配乐']),
]
ERA_WORDS = [('gameboy', ['game boy', 'gameboy', 'gb style', 'dmg', '掌机', '四色绿', 'four shades of green']),
             ('pico-8', ['pico-8', 'pico8']),
             ('nes', ['nes', 'famicom', '8-bit', '8 bit', '红白机', '8位', 'fc']),
             ('genesis', ['genesis', 'mega drive', 'megadrive', '世嘉']),
             ('gba', ['gba', 'game boy advance']),
             ('neogeo', ['neo geo', 'neogeo']),
             ('snes', ['snes', 'super nintendo', 'super famicom', '16-bit', '16 bit', '16位', '超任'])]

def era_of(request):
    """the console era a request names (a key of era.ERAS), or None"""
    t = ' ' + request.lower() + ' '
    for key, words in ERA_WORDS:
        if _hits(t, words):
            return key
    return None

GUIDE = {'scene': 'guides/scenes.md', 'rebuild': 'guides/rebuild.md', 'era': 'guides/eras.md',
         'assets': 'guides/assets.md', 'music': 'guides/music.md'}

PROJECTION = [('2:1 iso', ['isometric', 'iso ', 'iso-', '等距', '2:1']),
              ('3/4 top-down', ['top-down', 'top down', 'from above', 'overhead', 'bird', '俯视', '鸟瞰', '顶视']),
              ('side', ['side view', 'side-on', 'side on', 'profile', 'platformer', '侧视', '横版'])]

DARK = ['night', 'dark', 'midnight', 'underground', 'cave', '夜', '暗', '深夜', '地下']
BRIGHT = ['day', 'noon', 'sunny', 'morning', 'bright', '白天', '中午', '晴', '早晨', '明亮']
DARK_STYLES = ('contre-jour', 'neon-noir', 'cosy-lightmap', 'tactics', 'native-glow')
BRIGHT_STYLES = ('sticker-iso', 'hd-overworld', 'illustrated', 'pastel-cell')

def _hit(text, w):
    if w.isascii() and w[:1].isalnum():          # English: whole words, so 'nes' is not in 'japanese'
        return re.search(r'(?<![a-z0-9])' + re.escape(w.strip()) + (r'(?:e?s)?(?![a-z0-9])' if w[-1:].isalnum() else ''),
                         text) is not None
    return w in text                              # Chinese: substrings

def _hits(text, words):
    return [w for w in words if _hit(text, w)]

def route(request, n=3):
    """-> {'picks': [{style, score, why, projection, pick_if, example}], 'mode', 'guide', 'projection'}"""
    t = ' ' + request.lower() + ' '
    scores = {}
    for name, r in ROUTE.items():
        s, why = 0, []
        for w, words in r['signals']:
            h = _hits(t, words)
            if h:
                s += w * min(2, len(h))
                why.append('/'.join(h[:3]))
        scores[name] = [s, why]
    dark, bright = _hits(t, DARK), _hits(t, BRIGHT)
    for name in scores:
        if dark and name in DARK_STYLES:
            scores[name][0] += 1
        if dark and name in BRIGHT_STYLES:
            scores[name][0] -= 2
        if bright and name in DARK_STYLES:
            scores[name][0] -= 2
    proj = None
    for p, words in PROJECTION:
        if _hits(t, words):
            proj = p
            break
    if proj:                                         # a stated projection favours the styles drawn in it
        for name in scores:
            if ROUTE[name]['projection'] == proj:
                scores[name][0] += 2
    mode, best = 'scene', 0
    for m, w, words in MODES:
        h = _hits(t, words)
        if h and w * len(h) > best:
            mode, best = m, w * len(h)
    if mode == 'era':                                # console limits: no light layer on top
        for name in scores:
            if styles.get(name)['res'] != 'none':
                scores[name][0] -= 3
    order = sorted(scores, key=lambda k: (-scores[k][0], list(ROUTE).index(k)))
    picks = []
    for name in order[:n]:
        s, why = scores[name]
        r = ROUTE[name]
        picks.append(dict(style=name, score=s, why=why or ['no signal in the request'],
                          projection=proj or r['projection'], pick_if=r['pick_if'], example=r['example']))
    if picks[0]['score'] <= 0:                       # nothing matched: the toolkit's own look first
        lofi = next((p for p in picks if p['style'] == 'lofi'), None)
        if lofi is None:
            r = ROUTE['lofi']
            lofi = dict(style='lofi', score=0, why=['no strong signal: the default for a calm scene'],
                        projection=proj or r['projection'], pick_if=r['pick_if'], example=r['example'])
        picks = [lofi] + [p for p in picks if p['style'] != 'lofi'][:n - 1]
    if mode != 'scene' and picks[0]['score'] <= 0:
        picks[0]['why'] = ['no style signal: follow %s first; pick the finish style from the %s' % (
            GUIDE[mode], {'rebuild': "photo's light and subject", 'era': "console's limits",
                          'assets': 'game the assets are for', 'music': 'scene the music goes with'}[mode])]
    return dict(request=request, picks=picks, mode=mode, guide=GUIDE[mode], projection=proj,
                era=era_of(request) if mode == 'era' else None)

# ---------------------------------------------------------------- techniques by subject, whatever the style
# The style decides how things are shaded; the subject decides what gets drawn. Each entry: the words
# that bring it in and the techniques that draw it, each naming the primitive that does the work. Finished
# objects (boats, cats, lanterns, runes) are drawn in the scene's own code; references/assets has
# examples of each to study, never to call.
TOPIC_TOOLS = [   # (words, label, items); an item is 'technique (primitive)' or ('technique (primitive)', condition)
    # conditions: 'lofi' the JS-engine style, 'iso' / 'topdown' / 'side' projection, 'post:OP' the style allows that light op,
    # 'soft' the style has a light layer (alpha is fine), 'strict' it has none (opaque slots only)
    (['rain', 'storm', 'wet', 'puddle', '雨', '暴风', '湿', '水坑'], 'rain and wet', [
        'rain as opaque streaks in palette slots, crowns where they land (fx.rain_cells, fx.rain_splashes, fx.splash_field)',
        'puddle rings and drips off the eaves (fx.ripple, fx.ripples, fx.drip)',
        'wet cobbles: speculars on up-facing edges (texture.wet_streaks)',
        'puddles mirror what stands over them (water.reflect)',
        ('drizzle as baked engine tables (study references/assets/particles.py drizzle)', 'lofi'),
        ('rain lit inside a lamp radius: alpha streaks with a stepped tail (fx.light_streaks)', 'soft'),
        ('screen-res hairline rain (Post.rain)', 'post:rain')]),
    (['snow', 'winter', 'ice', '雪', '冬', '冰'], 'snow and ice', [
        'flakes as single light pixels on dark (texture.speckle)', 'drifts as stippled banks against walls (texture.stipple)',
        'a flat winter sky in undithered bands (sky.strata)',
        ('snow as baked engine tables (study references/assets/particles.py snow)', 'lofi')]),
    (['fog', 'mist', 'haze', '雾', '霭'], 'fog', [
        'fog as haze per depth plane, each plane pulled toward the fog colour (palette.haze, palette.haze_levels)',
        ('a fog layer over the planes (Post.fog)', 'post:fog'),
        'drifting banks that wrap seamlessly (canvas.wrap_offset, or canvas.loop_dissolve in lofi only)']),
    (['sea', 'ocean', 'lake', 'river', 'stream', 'harbour', 'harbor', 'port', 'coast', 'beach', 'waterfall', 'pond',
      'canal', 'boat', 'ship', 'dock', 'pier', '海', '湖', '河', '溪', '港', '海岸', '沙滩', '瀑布', '池塘', '运河', '船',
      '码头'], 'water', [
        'sea in hard bands by distance from land (water.depth_bands)',
        'dashed foam rings where things stand in water (water.foam_rings)',
        'reflections of hulls, posts and lights only (water.reflect)', 'still basins and falls (water.pool, water.waterfall)',
        ('a translucent glaze over the shallows (post.over)', 'post:over'),
        'boats, docks, barrels and crates as your own slot maps: the plan as a polygon, outlined per part, planks as '
        'seam rows (canvas.Canvas.poly, canvas.Canvas.outline, texture.planks) (study references/assets/props.py '
        'boat, dock, barrel, crate)']),
    (['forest', 'tree', 'trees', 'garden', 'jungle', 'park', 'leaf', 'leaves', 'grass', 'bush', '森林', '树', '花园',
      '丛林', '公园', '叶', '草', '灌木'], 'foliage', [
        'grass and bush clumps (texture.clumps), ferns and vines (veg.fern, veg.vine)',
        'round shingled canopies (veg.leaf_scales), a leaf mass lining the frame (veg.leafmass)',
        'flecks of light in dark foliage (texture.leaflight)', 'far tree lines as lobed silhouettes (shapes.lobes_along)',
        'trunks as a bark ramp on a tapered slot map (study references/assets/props.py trunk)',
        ('falling leaves, petals and fireflies as baked engine tables (study references/assets/particles.py)', 'lofi'),
        ('2:1 leaf glyphs, the iso sticker look (veg.leaf_glyphs)', 'iso')]),
    (['sky', 'cloud', 'clouds', 'sunset', 'dusk', 'dawn', '天空', '云', '日落', '黄昏', '清晨'], 'sky', [
        'flat undithered strata locked by wisps and streaks (sky.strata, sky.wisp, sky.smile, sky.streaks)',
        'clouds as masses and masks (shapes.cloud, shapes.cloud_mass, shapes.cloud_mask, shapes.cloud_rgba)']),
    (['cave', 'mine', 'rock', 'cliff', 'mountain', 'rubble', 'stone', 'underground', '洞', '矿', '岩', '悬崖', '山',
      '石', '地下'], 'rock', [
        'rubble and cave walls (texture.stones), layered rock (texture.flakes), gravel (texture.pebbles)',
        'ledged and noisy silhouettes (shapes.ledges, shapes.noisy_edge), the edge into the void (shapes.void_edge)',
        'rails, ladders, stairwells, carts, ore and crates as your own slot maps on the canvas (canvas.Canvas.line, '
        'canvas.Canvas.rect, canvas.Canvas.outline) (study references/assets/props.py rails, ladder, stairwell, '
        'mine_cart, ore_node, crate, barrel)']),
    (['city', 'town', 'street', 'building', 'house', 'houses', 'village', 'alley', 'castle', 'wall', 'brick', 'roof',
      '城', '镇', '街', '楼', '房', '村', '巷', '城堡', '墙', '砖', '屋顶'], 'buildings', [
        'coursed stone: cells laid out, then carved (layout.ashlar, texture.shade_cells)',
        'bricks, panels, mottled plaster and trim (texture.bricks, texture.panels, texture.mottle, texture.inset_frame)',
        'roofs and walls: tiles with slipped and missing ones and moss, thatch, boards (texture.shingles, '
        'texture.thatch, texture.planks)',
        'cables and washing lines that sag (canvas.Canvas.catenary)',
        ("boxes and gables seen from above with hard cast shadows (iso.Iso(camera='topdown'), iso.Iso.cast_shadows)",
         'topdown'),
        ('iso boxes (iso.Iso.box)', 'iso'),
        ('glass faces as diagonal streaks (study references/assets/props.py glass_streak)', 'iso'),
        'lanterns, pipes, drains and barrels as slot maps with a lit edge (study references/assets/props.py lantern, '
        'pipe, drain, barrel)']),
    (['industrial', 'factory', 'crane', 'construction', 'tower', '工厂', '吊车', '工地', '塔'], 'structure', [
        'girders and trusses as lines and lattices on the canvas (canvas.Canvas.line, texture.grille)',
        'how a girder or truss was built (study references/assets/props.py girders, truss)', 'pitted concrete (texture.pits)']),
    (['tech', 'sci-fi', 'scifi', 'robot', 'mech', 'machine', 'computer', 'neon', 'space', 'cyberpunk', '科技', '科幻',
      '机器', '机甲', '电脑', '霓虹', '太空', '赛博'], 'tech', [
        'circuits, lamp panels and grilles (texture.circuit, texture.emitter_grid, texture.grille)',
        'status lights, screens and tubes (fx.indicator, fx.emissive)',
        'neon tube letters with buzzing broken letters, returning the emitter mask for a glow (fx.neon_sign)',
        'pipes and drains as banded slot maps (study references/assets/props.py pipe, drain)']),
    (['ruin', 'ruins', 'temple', 'rune', 'magic', 'spell', 'shrine', '遗迹', '神殿', '符文', '魔法', '法术', '神社'],
     'magic and ruins', [
        'runes as your own glyphs, slot maps from strokes (study references/assets/glyphs.py rune, stamp)',
        'runes lighting in turn (anim.cascade), drifting motes (fx.pixel_motes)',
        'woven and carved surfaces (texture.tapestry, texture.circuit)']),
    (['fire', 'explosion', 'battle', 'fight', 'gun', 'shoot', 'war', 'boss', 'sword', 'samurai', 'ninja', '火', '爆炸',
      '战斗', '打', '枪', '射击', '战争', '剑', '武士', '忍者'], 'action', [
        'fireballs, puffs, bursts and sparks as opaque sprites (fx.fireball, fx.puff, fx.smoke_puff, fx.burst, fx.sparks)',
        'shots, muzzle light and hit flashes (fx.shot, fx.muzzle_light, fx.hit_flash)',
        'swing trails, motion trails and tumbling debris (fx.crescent, fx.trail, fx.tumble)',
        'recoil and arcs on hold tables (anim.recoil, anim.arc)']),
    (['level', 'stage', 'platformer', 'game', 'gameplay', 'hud', '关卡', '平台', '游戏', '玩法'], 'game level', [
        'jumps and hops (anim.arc, anim.hop), landing dust (fx.burst)', 'layer scroll and tiles (canvas.parallax, '
        'canvas.Canvas.tile)', 'HUD text (pixfont.draw)',
        'pickups and icons as small slot maps (study references/assets/glyphs.py stamp)']),
    (['lamp', 'lantern', 'candle', 'torch', 'window', 'fireplace', 'neon sign', '灯', '灯笼', '蜡烛', '火把', '窗',
      '壁炉'], 'small lights', [
        'lamps and lanterns as slot maps in warm slots (study references/assets/props.py lantern)',
        'flicker on held steps, passing t % T so the seam holds (light.flicker), and lamp-side rims (light.rim)',
        'marquee and signal lights (anim.chase)',
        ('multiplied pools, walls blocking light with occlude= and per-light flicker in the light tuple (Post.lightmap)',
         'post:lightmap'),
        ('shaped pools (Post.light)', 'post:light'), ('glow from an emitter mask (Post.glow)', 'post:glow'),
        ('pools drawn in palette steps (light.Light.point, light.Light.apply)', 'strict')]),
    (['crowd', 'people', 'busy', 'traffic', 'market', 'festival', 'car', 'cars', '人群', '热闹', '车', '集市', '夜市',
      '庙会'], 'crowds', [
        ('traffic and crowds placed on lanes (compose.populate)', 'iso'),
        ('iso people and cars as your own slot maps (study references/assets/figures.py iso_person and props.py car)',
         'iso'),
        'density per window (compose.check_density)']),
    (['cat', 'dog', 'deer', 'horse', 'animal', 'bird', 'birds', 'gull', 'gulls', 'seagull', 'crow', 'fish', '猫',
      '狗', '鹿', '马', '动物', '鸟', '海鸥', '乌鸦', '鱼'], 'animals', [
        'each animal as your own slot map at the scene\'s size and pose: sit, sleep, walk, fly (study '
        'references/assets/figures.py cat, gull, quadruped_slim for the silhouette and the frame changes)',
        'birds circling and fish (anim.orbit), tails that lag (anim.lag), shadows on the slot grid (sprite.drop_shadow)']),
    (['slime', 'blob', '史莱姆', '黏液'], 'slimes', [
        'squash-and-hop sizes per frame (anim.hop), a shadow under it (sprite.drop_shadow)',
        'the dome drawn from the hop size (study references/assets/figures.py slime)']),
    (['person', 'people', 'character', 'hero', 'girl', 'boy', 'man', 'woman', 'kid', 'knight', 'samurai', 'walk',
      '人', '角色', '主角', '女孩', '男孩', '骑士', '武士', '走'], 'figures', [
        'the style\'s figure size and outline (section 11), drawn as your own slot maps per pose',
        ('10-14 px diorama people (idle, walk, sit) (study references/assets/figures.py lofi)', 'lofi'),
        'proportions and poses: study references/assets/figures.py chibi, thin, slim',
        'hair, capes and scarves that trail (anim.lag, sprite.chain)',
        'shadows and lit edges (sprite.drop_shadow, sprite.spec_edges)', 'poses on hold tables (anim.hold, anim.Timeline)']),
]
ALWAYS_TOOLS = ('checks: the gate `pixelate check FRAME --style S --scale N` on every delivered frame (budget, '
                'native cells, palette, readability, craftcheck), `pixelate check SCENE` for engine scenes, '
                'anim.check_periods (every period divides the loop), compose.check_density for busy scenes')

CATALOG = [('post', 'the light layer: Post (none/native/screen), Stack (depth planes), light, glow, shaft, flare, streak, lightmap, fog, rain, motes'),
           ('light', 'light drawn in palette steps: point lights, rims, flicker, void fades'),
           ('palette', 'ramps per style, palettes, haze, grading, hue families, slots'),
           ('texture', 'surface patterns: pebbles, stones, bricks, panels, flakes, leaf-light, stipples, wet speculars, circuits'),
           ('layout', 'cell layouts for masonry and blocks, and their shading'),
           ('shapes', 'silhouettes: clouds, ledges, frayed and noisy edges, lobes, void edges'),
           ('sky', 'skies: strata, wisps, streaks, crescents'),
           ('water', 'water: depth bands, foam rings, pools, waterfalls, reflections'),
           ('veg', 'foliage: leaf scales, leaf glyphs, leaf masses, framed fields'),

           ('sprite', 'sprite helpers: chains (ropes, scarves), drop shadows, specular edges'),
           ('anim', 'motion: timelines, hold tables, hops, lag, recoil, arcs, orbits, chases, cascades, period checks'),
           ('fx', 'effects as pixels: rain cells, fireballs, puffs, bursts, shots, flashes, trails, motes, indicators'),
           ('compose', 'composition: frames, prosceniums, stages, rooms, plans, crowds, density checks'),
           ('canvas', 'the canvas: slots, thresholds, parallax, seamless loop dissolves'),
           ('morph', 'mask operations: dilate, erode, distance, normals, regions, relief'),
           ('iso', '2:1 isometric boxes and scenes'),
           ('stats', 'measuring a frame against a style budget'),
           ('craftcheck', 'pixel craft by numbers: orphans, jaggies, stripes, doubled outlines, pillow shading, clusters, limits per style'),
           ('styles', 'the 11 style presets, their budgets and checks'),
           ('artlib', 'slot-map sprites for the lofi JS engine: Grid, stamping, orphan checks, export to sprites.js'),
           ('era', 'console-era limits (NES, Game Boy, SNES, Genesis, GBA, PICO-8, Neo Geo): check and force'),
           ('pixfont', 'the pixel font for HUD and captions'),
           ('cjkfont', 'a CJK pixel font for Chinese and Japanese text')]
EXAMPLES = [('props', 'built things: trunks, girders, trusses, rails, stairwells, cars, glass, boats, docks, crates'),
            ('figures', 'characters per style: chibi, slim, thin, iso people, quadrupeds, cats, gulls, slimes'),
            ('glyphs', 'original runes and stamps'),
            ('particles', 'lofi particles baked to engine tables: petals, leaves, snow, drizzle, fireflies')]

def catalog():
    """guides/toolkit.md: every public function and class in the kit with its first doc line, so an
    agent knows everything it can reach for before it writes a brief. Regenerate with --catalog."""
    import importlib, inspect
    L = ['# Toolkit', '',
         'Every function in the kit, with its first doc line. Generated by `python3 tools/route.py --catalog`;',
         'regenerate it after adding a tool. Read it before writing a brief: the router only suggests the',
         'techniques its keywords know about, and the best brief uses whatever the scene needs. The last',
         'sections list the examples in references/assets: read them to see how a finished thing was built,',
         'never call them.', '']
    L.append('## By subject\n')
    for words, label, items in TOPIC_TOOLS:
        L.append('- %s: %s.' % (label[0].upper() + label[1:],
                                ', '.join(it if isinstance(it, str) else '%s [%s]' % it for it in items)))
    L.append('- ' + ALWAYS_TOOLS[0].upper() + ALWAYS_TOOLS[1:] + '.')
    ex = str(pathlib.Path(__file__).resolve().parent.parent / 'references' / 'assets')
    if ex not in sys.path:
        sys.path.append(ex)
    for mod, what in CATALOG + [(m, w + ' (an example in references/assets: read, never call)') for m, w in EXAMPLES]:
        try:
            m = importlib.import_module(mod)
        except Exception:
            continue
        L.append('\n## %s\n\n%s.\n' % (mod, what[0].upper() + what[1:]))
        for n, o in vars(m).items():
            if n.startswith('_') or not (inspect.isfunction(o) or inspect.isclass(o)) or getattr(o, '__module__', '') != mod:
                continue
            d = ' '.join((inspect.getdoc(o) or '').split('\n\n')[0].split())
            d = d if len(d) < 160 else d[:157].rsplit(' ', 1)[0] + '...'
            L.append('- `%s.%s`%s' % (mod, n, (': ' + d) if d else ''))
            if inspect.isclass(o):
                for mn, mo in vars(o).items():
                    if mn.startswith('_') or not callable(getattr(o, mn, None)):
                        continue
                    md = ' '.join((inspect.getdoc(getattr(o, mn)) or '').split('\n\n')[0].split())
                    md = md if len(md) < 140 else md[:137].rsplit(' ', 1)[0] + '...'
                    L.append('  - `.%s`%s' % (mn, (': ' + md) if md else ''))
    return '\n'.join(L) + '\n'

def _fits(cond, style, projection):
    st = styles.get(style)
    if cond in ('iso', 'topdown', 'side'):
        return {'iso': '2:1 iso', 'topdown': '3/4 top-down', 'side': 'side'}[cond] == projection
    if cond == 'lofi':
        return style == 'lofi'
    if cond == 'soft':
        return st['res'] != 'none'
    if cond == 'strict':
        return st['res'] == 'none'
    if cond.startswith('post:'):
        return styles.allows(style, cond[5:])
    return True

def topic_tools(request, style=None, projection=None):
    """-> ['label: call, call, ...'] for the subjects the request names, filtered to what the style
    and projection allow (a banned light op or an iso-only prop is left out)"""
    t = ' ' + request.lower() + ' '
    out = []
    for words, label, items in TOPIC_TOOLS:
        if not _hits(t, words):
            continue
        keep = []
        for it in items:
            if isinstance(it, tuple):
                if style is None or _fits(it[1], style, projection or ROUTE[style]['projection']):
                    keep.append(it[0])
            else:
                keep.append(it)
        out.append('%s: %s' % (label, '; '.join(keep)))
    return out

# ---------------------------------------------------------------- what the request leaves open
WORDS = dict(
    time=['night', 'dusk', 'dawn', 'sunset', 'sunrise', 'noon', 'morning', 'evening', 'day', 'rain', 'snow',
          'fog', 'mist', 'storm', 'winter', 'summer', 'spring', 'autumn',
          '夜', '黄昏', '清晨', '日落', '日出', '中午', '早晨', '傍晚', '白天', '雨', '雪', '雾', '风暴', '冬', '夏', '春', '秋'],
    phases=['seasons', 'four seasons', 'day to night', 'day and night', 'cycle', 'phases', 'timelapse',
            '四季', '昼夜', '日夜', '循环', '轮换'],
    figures=['person', 'people', 'character', 'hero', 'girl', 'boy', 'man', 'woman', 'kid', 'crowd', 'cat', 'dog',
             'bird', 'animal', 'knight', 'villager', '人', '角色', '主角', '女孩', '男孩', '人群', '猫', '狗', '鸟', '动物'],
    purpose=['wallpaper', 'cover', 'thumbnail', 'banner', 'video', 'gif', 'loop', 'stream', 'key art', 'poster',
             'readme', 'showcase', '壁纸', '封面', '缩略图', '横幅', '视频', '动图', '循环', '直播', '海报', '展示'],
    music=['music', 'soundtrack', 'lofi', 'lo-fi', 'chiptune', 'song', 'audio', '音乐', '配乐', '歌'],
)

TIME_DEFAULT = {
    'lofi': 'late evening, lit windows and a lantern, the sky a calm gradient',
    'pastel-cell': 'bright windy day, high clouds, one hue window',
    'native-glow': 'dusk, low cold sun, glowing sigils and water',
    'hd-overworld': 'late morning sun, clear water, soft cloud shadows',
    'arcade': 'overcast day, smoke and fire as the warm accents',
    'tactics': 'night storm, the board lit by fire and impacts',
    'sticker-iso': 'midday, flat bright light, no cast shadows',
    'illustrated': 'golden hour, big clouds, a long view',
    'neon-noir': 'midnight rain, neon signs as the only colour',
    'cosy-lightmap': 'rainy night, many warm windows and lamps pooling light in the dark',
    'contre-jour': 'night fog, one strong backlight behind the subject, sparse rain',
}

UNDERGROUND = ['mine', 'cave', 'underground', 'dungeon', 'tunnel', 'sewer', 'crypt', '矿', '洞', '地下', '地牢',
               '隧道', '下水道']
INDOOR = ['interior', 'inside', 'room', 'bedroom', 'kitchen', 'cafe', 'shop', 'library', 'tavern', 'inn',
          '室内', '屋内', '房间', '卧室', '厨房', '咖啡', '店', '图书馆', '酒馆', '客栈']

def gaps(request, r=None):
    """-> [{topic, stated, default}]: each open choice in the request and the default it takes for the
    top style. Fill the brief with the defaults, then list them for the user to confirm or change."""
    r = r or route(request)
    t = ' ' + request.lower() + ' '
    p = r['picks'][0]
    st = styles.get(p['style'])
    rt = ROUTE[st['name']]
    dark = st['name'] in DARK_STYLES
    frames = rt['frames'][0]
    out = []
    def add(topic, words, default):
        h = _hits(t, words) if words else []
        out.append(dict(topic=topic, stated='/'.join(h[:3]) if h else '', default=default))
    margin = p['score'] - (r['picks'][1]['score'] if len(r['picks']) > 1 else 0)
    out.append(dict(topic='style', stated='/'.join(p['why'][:2]) if p['score'] > 3 and margin >= 3 else '',
                    default='`%s` (%s); the runners-up are %s' % (
                        st['name'], st['what'], ', '.join('`%s`' % q['style'] for q in r['picks'][1:]))))
    out.append(dict(topic='projection', stated=r['projection'] or '', default=p['projection']))
    under = _hits(t, UNDERGROUND)
    inside = _hits(t, INDOOR)
    add('time and weather', WORDS['time'],
        'underground, no sky: the lamps are the only light, and one shaft or opening shows the world above'
        if under else 'indoors: the room lit by its own lamps and one window showing the weather outside'
        if inside else TIME_DEFAULT.get(st['name'],
        'night, one main light source, light rain' if dark else 'late afternoon, clear, low warm sun'))
    add('phases', WORDS['phases'],
        'one phase; for a long stream cover, a cycle of 3-4 phases each with its own signature elements '
        '(not Lantern Isle\'s four seasons again unless asked)' if st['name'] == 'lofi'
        else 'one phase, no cycle')
    named = _hits(t, WORDS['figures'] + ['slime', 'robot', 'samurai', '史莱姆', '武士', '机器人'])
    add('figures', WORDS['figures'],
        'only the actors the request names, nobody added' if named else
        'one or two small figures doing a quiet, specific task (%s)' % _as_example(st['figures']))
    loop = ('the engine\'s 30-tick clock, sprites at 10, 5 or 2 fps; the loop is the music\'s length'
            if st['name'] == 'lofi' else 'a seamless %s-frame loop at %d fps' % (frames or 'TODO', st['fps']))
    excerpt = 'a GIF excerpt' if st['res'] == 'none' else 'an APNG excerpt (a GIF bands soft light)'
    add('purpose and outputs', WORDS['purpose'],
        'a gallery showcase: %s, as 1080p MP4, %s and a still' % (loop, excerpt))
    if r.get('era'):
        import era as eramod
        e = eramod.ERAS[r['era']]
        out.append(dict(topic='era limits', stated=r['era'], default='%s: %dx%d, at most %d colours%s%s; no light '
                        'layer; check with `pixelate era IMG --era %s`' % (
                            e['name'], e['size'][0], e['size'][1], e['max_colors'],
                            (', palette %s' % e['palette']) if e.get('palette') else '',
                            (', %d colours per %dx%d block' % (e['block_colors'], e['block'], e['block']))
                            if e.get('block') else '', r['era'])))
    add('music', WORDS['music'],
        'a lofi track with one motif per phase (guides/music.md)' if st['name'] == 'lofi' else 'none')
    return out

def gaps_md(g):
    L = ['## 0. Choices to confirm', '',
         'Defaults I picked where the request was open. Say OK to build as written, or change any line.', '',
         '- **intent**: TODO one line on what the user most likely wants but did not say (the feeling, the use, '
         'the era or game it recalls, what would disappoint them); every choice below follows from it']
    for x in g:
        L.append('- **%s**: %s%s' % (x['topic'], x['default'],
                                     '' if not x['stated'] else ' (from the request: %s)' % x['stated']))
    return '\n'.join(L) + '\n'

# ---------------------------------------------------------------- self-critique of a finished brief
SECTIONS = ['Purpose and delivery', 'Style and light regime', 'Art direction rules', 'The scene',
            'Lived-in details', 'Phase', 'Light list', 'Motion table', 'Particles', 'Never', 'Technical']
MIN_BULLETS = {'Art direction rules': 6, 'The scene': 4, 'Lived-in details': 5, 'Light list': 2,
               'Motion table': 4, 'Never': 3}
VAGUE = ['nice', 'beautiful', 'cool', 'some ', 'various', 'etc', 'stuff', 'things like', 'and so on',
         'as needed', 'appropriate', 'interesting']

def lint(text):
    """-> a list of problems in a brief: TODOs left, missing or thin sections, vague words, a motion
    table without numbers, periods that don't divide the loop, and the quality checks (section 0 intent,
    scene objects placed and counted, lights with colour, radius and what hides them, motion with rates,
    phases with signature elements, an imperfection, examples studied rather than called, the gate in
    Technical). A short brief gets the matching light lint. Empty means it is ready to show."""
    if _is_short(text):
        return lint_short(text)
    probs = []
    left = text.count('TODO')
    if left:
        probs.append('%d TODO left: fill each with a concrete choice (or a default listed in section 0)' % left)
    find = _sections(text)
    probs += _intent(find)
    for sec in SECTIONS:
        b = find(sec)
        if b is None:
            probs.append('missing section: %s' % sec)
            continue
        n = len(_bullets(b))
        if n < MIN_BULLETS.get(sec, 1):
            probs.append('%s is thin: %d items, want %d or more' % (sec, n, MIN_BULLETS.get(sec, 1)))
        probs += _vague(sec, b)
    m = find('Motion table')
    if m is not None and not re.search(r'\d+\s*(frames?|fps|drawings?|ticks?)', m):
        probs.append('Motion table has no frame counts or rates')
    head = (re.search(r'Motion table[^\n]*?(\d+)\s*frames', text) or
            re.search(r'Loop:\s*(?:a seamless\s*)?(\d+)[\s-]*frames', text) or
            re.search(r'(\d+)[\s-]*frame loop', text))
    if head and m:
        T = int(head.group(1))
        pats = [r'every\s+(\d+)\s+frames', r'(\d+)[\s-]*frame (?:cycle|period|action|loop|turn)',
                r'(?:once|one \w+) (?:every|per) (\d+)\s+frames', r'period(?: of)?\s+(\d+)']
        for pat in pats:
            for k in re.findall(pat, m):
                if int(k) and T % int(k):
                    probs.append('Motion table: a period of %s frames does not divide the %d-frame loop' % (k, T))
        for n, k in re.findall(r'(\d+)\s+drawings?,?\s+(\d+)\s+frames? each', m):
            if int(n) * int(k) and T % (int(n) * int(k)):
                probs.append('Motion table: %s drawings x %s frames = %d does not divide the %d-frame loop' % (
                    n, k, int(n) * int(k), T))
    if m is not None:
        slow = [b for b in _bullets(m) if not re.match(r'(todo|checks?|motion|note)\b', b, re.I)
                and not b.endswith(':') and not re.search(RATE, b, re.I)]
        if slow:
            probs.append('Motion table: %d line(s) with no rate or frame count: %s' % (len(slow), _quote(slow)))
    li = find('Light list')
    if li is not None and not re.search(r'\d', li):
        probs.append('Light list has no sizes or radii: give every emitter a colour, a radius and what hides it')
    sl = find('Style and light regime')
    if sl is not None:
        if not re.search(r'\b(none|native|screen)\b|no light layer', sl):
            probs.append('Style and light regime does not name the light layer (none, native or screen)')
        if not re.search(r'budget|L\s*[<>]|below L|above L', text):
            probs.append('no value budget anywhere (how much of the frame is dark, how rare the highlights are)')
    hides_flagged = False
    if re.search(r'res\W*(native|screen)|light layer\W*(native|screen)', text.lower()) and li is not None \
            and not re.search(r'hide|hidden|occlud|block|behind', li.lower()):
        probs.append('Light list never says what hides a light (the near plane, a wall, a door frame)')
        hides_flagged = True
    if li is not None and _has_light_layer(text):
        lights = [b for b in _bullets(li) if not re.match(NOT_A_LIGHT, b.lstrip('*'), re.I)
                  and not re.search(r'\bunlit\b|no light of its own|not a light|no pool', b, re.I)]
        for what, pat in (('no colour', COLOUR), ('no radius or size', RADIUS)) + (
                () if hides_flagged else (('nothing that hides it', HIDES),)):
            miss = [b for b in lights if not re.search(pat, b, re.I)]
            if miss:
                probs.append('Light list: %d light(s) with %s: %s' % (len(miss), what, _quote(miss)))
    sc = find('The scene')
    if sc is not None and not re.search(r'\d', sc):
        probs.append('The scene has no counts, sizes or positions')
    elif sc is not None:
        loose = [b for b in _bullets(sc) if not b.startswith('TODO') and not b.endswith(':')
                 and not re.search(PLACED, b, re.I)]
        if loose:
            probs.append('The scene: %d object line(s) with no count, size or position: %s' % (len(loose), _quote(loose)))
    ph = find('Phase')
    if ph is not None and not re.search(r'signature|only in (?:this|that) phase|unique to', ph, re.I):
        if re.search(r'recolou?r|palette swap|same scene|only the palette', ph, re.I) or \
                not re.search(r'\b(?:one|single) phase|no cycle', ph, re.I):
            probs.append('Phases name no signature element (something drawn only in that phase); a recolour is not a phase')
    lv = find('Lived-in details')
    if lv is not None and re.search(IMPERFECT, text.lower()) is None:
        probs.append('no built-in imperfections anywhere (a lean, a sag, a missing plank, a patch)')
    te = find('Technical')
    if te is not None and 'pixelate check' not in te:
        probs.append('Technical has no gate command: add `pixelate check FRAME.png --style S --scale N` '
                     '(and `pixelate check SCENE` for engine scenes)')
    probs += _asset_calls(text)
    probs += _tool_refs(text)
    return probs

SHORT_SECTIONS = ['Style', ('Palette and size', 'Length and sound'), 'The work', 'Gate', 'Show the user']

def _is_short(text):
    first = text.lstrip().split('\n', 1)[0]
    return 'short brief' in first.lower() or (re.search(r'^##\s+(?:\d+\.\s*)?Gate\b', text, re.M) is not None
                                              and 'Motion table' not in text)

def lint_short(text):
    """the light lint for a short brief: TODOs, its six sections, section 0 intent, vague words, a size,
    the gate command, what the user sees, examples studied rather than called, real kit names"""
    probs = []
    left = text.count('TODO')
    if left:
        probs.append('%d TODO left: fill each with a concrete choice (or a default listed in section 0)' % left)
    find = _sections(text)
    probs += _intent(find)
    for sec in SHORT_SECTIONS:
        names = sec if isinstance(sec, tuple) else (sec,)
        b = next((find(n) for n in names if find(n) is not None), None)
        if b is None:
            probs.append('missing section: %s' % names[0])
            continue
        if not _bullets(b):
            probs.append('%s is empty' % names[0])
        probs += _vague(names[0], b)
    music = find('Palette and size') is None and find('Length and sound') is not None
    ps = find('Length and sound') if music else find('Palette and size')
    if ps is not None and 'TODO' not in ps and not re.search(r'\d', ps):
        probs.append('Length and sound has no numbers: the loop length, the tempo' if music else
                     'Palette and size has no numbers: the colour count, the sprite or canvas size')
    g = find('Gate')
    if g is not None and 'pixelate' not in g:
        probs.append('Gate has no command: add `pixelate check FILE.png --style S --scale N`')
    probs += _asset_calls(text)
    probs += _tool_refs(text)
    return probs

RATE = (r'\d+\s*(?:frames?|fps|ticks?|drawings?|px|cycles?|s\b|seconds?|beats?|bpm)|every\s+\d+|hold\s*=?\s*\d+'
        r'|\bx\s*\d+|\d+\s*x\b|per (?:loop|frame|tick|second)|\bstill\b|static|\bnone\b|frame\s+\d+|\d+\s*/\s*s')
COLOUR = (r'#[0-9a-f]{3,6}|\b(?:amber|orange|red|yellow|gold|golden|lemon|cream|white|warm|cool|cold|teal|cyan|blue|'
          r'navy|green|magenta|pink|rose|violet|purple|plum|honey|ochre|copper|brass|tint|hue|colou?r|lilac|peach|'
          r'apricot|coral|umber|grey|gray|silver|turquoise|candle|hearth|fire|moon|sun|slots?|ramp)\w*')
RADIUS = r'radius|sigma|falloff|\br\s*=?\s*\d|\d+\s*px|\d+\s*x\s*\d+|width|wide|reach|within \d|\d+\s*(?:cells?|pixels?)'
HIDES = (r'hid|occlud|block|behind|mask|cut (?:by|off)|shield|cover|stops? at|never (?:reaches|lights)|swallow'
         r'|stays? (?:black|dark)|do(?:es)? not reach|doesn\'t reach')
NOT_A_LIGHT = r'(todo|allowed|banned|everything|every light|no |ambient|per-light|reflections?|puddle reflections|void edges?|check)\b'
PLACED = (r'\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a pair|a single|dozen|left|right|'
          r'centre|center|middle|top|bottom|behind|front|foreground|background|above|below|under|over|beside|along|'
          r'edge|corner|third|half|quarter|near|far|between|across|horizon|on the|by the|at the|in the)\b')
IMPERFECT = r'imperfect|lean|sag|missing|broken|patched|worn|chipped|crooked|cracked|mismatch|faded|tilt|dent|peel'

def _sections(text):
    parts = re.split(r'^##\s+(?:\d+\.\s*)?', text, flags=re.M)
    body = {}
    for part in parts[1:]:
        head, _, rest = part.partition('\n')
        body[head.strip()] = rest
    return lambda name: next((v for k, v in body.items() if k.lower().startswith(name.lower())), None)

def _bullets(b):
    return [x.strip() for x in re.findall(r'^[-*]\s+(\S.*)$', b, flags=re.M)]

def _quote(items, n=3):
    q = ['"%s"' % (x if len(x) <= 48 else x[:45].rsplit(' ', 1)[0] + '...') for x in items[:n]]
    return ', '.join(q) + (' and %d more' % (len(items) - n) if len(items) > n else '')

def _vague(sec, b):
    return ['%s says "%s": name the thing, the count or the colour instead' % (sec, w.strip())
            for w in VAGUE if re.search(r'\b' + re.escape(w.strip()) + r'\b', b.lower())]

def _intent(find):
    z = find('Choices to confirm')
    if z is None:
        return ['missing section 0 (Choices to confirm): the intent and the defaults the user confirms']
    m = re.search(r'^\s*[-*]\s+\*{0,2}intent\*{0,2}\s*:(.*)$', z, flags=re.M | re.I)
    if m is None:
        return ['section 0 has no intent line: what the user most likely wants but did not say']
    if 'TODO' in m.group(1) or len(m.group(1).split()) < 3:
        return ['section 0 intent is still TODO: write what the user most likely wants but did not say']
    return []

def _has_light_layer(text):
    m = re.search(r'[Ss]tyle\W{0,3}`([a-z0-9-]+)`', text)
    if m:
        try:
            return styles.get(m.group(1))['res'] != 'none'
        except Exception:
            pass
    return re.search(r'res\W*(native|screen)|light layer\W*(native|screen)', text.lower()) is not None

EXAMPLE_MODULES = ('props', 'figures', 'glyphs', 'particles')
EXAMPLE_WORDS = ('example', 'study', 'studied', 'references/assets', 'modelled on', 'modeled on', 'for reference',
                 'see how', 'read ')

def _asset_calls(text):
    """a references/assets module (props., figures., glyphs., particles.) named as a call, not an example"""
    bad = []
    for line in text.splitlines():
        for clause in re.split(r';|\.\s', line):
            low = clause.lower()
            if any(w in low for w in EXAMPLE_WORDS):
                continue
            for ref in re.findall(r'(?<![\w./])((?:%s)\.[A-Za-z_]\w*)' % '|'.join(EXAMPLE_MODULES), clause):
                if ref.split('.')[1] not in ('py', 'md') and ref not in bad:
                    bad.append(ref)
    if not bad:
        return []
    return ['%s written as something to call: references/assets holds examples to study, never to call; draw it in '
            'the scene\'s own code and say which example you studied' % ', '.join('`%s`' % b for b in bad)]

KIT_MODULES = ('post', 'light', 'palette', 'texture', 'layout', 'shapes', 'figures', 'props', 'compose', 'anim',
               'sprite', 'fx', 'glyphs', 'sky', 'veg', 'water', 'canvas', 'morph', 'stats', 'styles', 'assets',
               'iso', 'artlib', 'era', 'pixfont', 'cjkfont', 'particles')

def _tool_refs(text):
    """every `module.name` (or `module.Class.name`) in backticks must exist in the kit"""
    import importlib
    ex = str(pathlib.Path(__file__).resolve().parent.parent / 'references' / 'assets')
    if ex not in sys.path:                          # the examples resolve the same way whatever was imported first
        sys.path.append(ex)
    bad = []
    for ref in sorted(set(re.findall(r'(?<![\w./])([a-z_]+(?:\.[A-Za-z_]+)+)(?=[\s`(),;:.]|$)', text))):
        mod, *path = ref.split('.')
        if mod not in KIT_MODULES or path[-1] in ('js', 'py', 'md', 'json', 'hex', 'png'):
            continue
        try:
            obj = importlib.import_module(mod)
            for k in path:
                obj = getattr(obj, k)
        except Exception:
            hint = ''
            try:
                m = importlib.import_module(mod)
                cls = [n for n, o in vars(m).items() if isinstance(o, type) and hasattr(o, path[-1])]
                if cls:
                    hint = ' (did you mean `%s.%s.%s`?)' % (mod, cls[0], path[-1])
            except Exception:
                pass
            bad.append(('`%s` is not in references/assets either%s' if mod in EXAMPLE_MODULES else
                        '`%s` is not in the kit%s: use a real function or name the tool gap') % (ref, hint))
    return bad

# ---------------------------------------------------------------- the pre-filled brief
def _fmt_budget(b):
    return '; '.join('%s %s' % (k, ('>= %s' % lo) if hi is None else ('<= %s' % hi) if lo is None else
                                '%s..%s' % (lo, hi)) for k, (lo, hi) in b.items()) or 'none (look at it)'

def brief(style, request='', projection=None, choices=None, era=None):
    """the craft.md brief as Markdown, with everything the style decides filled in and the
    scene-specific parts as TODO prompts; choices (from gaps()) adds section 0"""
    st = styles.get(style)
    r = ROUTE[st['name']]
    w, h = st['size']
    E = None
    if era:
        import era as eramod
        E = eramod.ERAS[era]
        w, h = E['size']
    frames, fps = r['frames'][0], st['fps']
    proj = projection or r['projection']
    light = {'none': 'no light layer: light is palette steps (warm slots, rims, a few highlight pixels)',
             'native': 'a light layer computed per art pixel from the scene\'s masks, scaled up last (post.Post(res="native"))',
             'screen': 'a light layer smooth inside each art pixel, composited at delivery size (post.Post(res="screen"))'}[st['res']]
    L = []
    L.append('# TODO title (scene brief)\n')
    L.append('Request: %s\n' % (request or 'TODO'))
    if choices:
        L.append(gaps_md(choices))
    L.append('## 1. Purpose and delivery')
    L.append('- TODO what it is for, where it will be seen (full screen, thumbnail, README), outputs (MP4, GIF/APNG, page, still).')
    if st['name'] == 'lofi':
        L.append('- Loop: the engine runs on a 30-tick clock (TICKS = cycle * grand * 30); sprites step at 10, 5 '
                 'or 2 fps; TODO the loop length (the music length for a stream cover).')
    else:
        L.append('- Loop: %s frames at %d fps.%s' % (frames or 'TODO', fps,
                 ' Delivered prescaled (screen light); excerpts as APNG, since a GIF bands soft light.'
                 if st['res'] == 'screen' else ' Excerpts as APNG (soft light bands in a GIF).'
                 if st['res'] == 'native' else ''))
    L.append('\n## 2. Style and light regime')
    L.append('- Style `%s` (learned from %s): %s.' % (st['name'], st['ref'], st['what']))
    L.append('- Light: %s; blend %s.' % (light, ', '.join(st['blend']) or 'none'))
    if E:
        L.append('- Ramps: 3-4 steps picked by hand from the %s palette. Palette: at most %d colours%s.' % (
            E.get('palette', era), E['max_colors'], ', shared backdrop' if E.get('shared_backdrop') else ''))
    else:
        L.append('- Ramps: `%s`. Palette: %s.' % (', '.join(st['ramp']), st['palette']))
    L.append('- Outline: %s. Dither: %s.' % (st['outline'], (', '.join(st['dither']) + ', ' + st['dither_where']) if st['dither'] else 'none'))
    L.append('- Learn the grammar only: no characters, places, logos or UI layouts from %s. TODO name anything else to avoid.' % st['ref'])
    L.append('\n## 3. Art direction rules')
    for x in r['rules']:
        L.append('- ' + x)
    L.append('- TODO 3-5 rules for this scene: which silhouettes must read, where rims fall, the built-in imperfections '
             '(a lean, a sag, a missing plank, a mismatched part).')
    L.append('- Every object is drawn in this scene\'s code from the primitives; anything the kit has no primitive for '
             'is a slot map. references/assets has finished examples to study, never to call.')
    L.append('\n## 4. The scene')
    L.append('- Projection: %s. Canvas %dx%d.' % (proj, w, h))
    L.append('- TODO the subject and how much of the frame it fills; the horizon; the calm areas.')
    L.append('- TODO the full object list with counts and rough positions (left third, on the ridge, by the door).')
    if st.get('stack'):
        L.append('- TODO the depth planes: far (hazed), middle (lit), near (flat dark silhouettes that occlude light).')
    L.append('\n## 5. Lived-in details')
    L.append('- TODO five to ten small, specific things that tell a story; say which change per phase.')
    L.append('\n## 6. Phases')
    L.append('- TODO for each phase: the palette by named roles, its signature elements (not a recolour), music if any.')
    L.append('\n## 7. Light list')
    if st['res'] == 'none':
        L.append('- Every light is drawn: TODO each emitter with its warm slots, the pool shape it casts, its flicker table.')
    else:
        L.append('- TODO each emitter: what, where, colour, radius or width, flicker or pulse, what it lights, what hides it.')
        L.append('- Allowed light ops: %s.' % (', '.join(st['allowed_post']) or 'none'))
    L.append('\n## 8. Motion table' + ('' if st['name'] == 'lofi' or not frames else
                                       ' (%d frames at %d fps)' % (frames, fps)))
    L.append('- Motion: %s at about %d fps; every period divides the loop (anim.check_periods).' % (
        'stepped, hold tables' if st['motion'] == 'stepped' else 'actors move in screen pixels', fps))
    L.append('- TODO every moving thing with its frame count and rate; keep only a few things moving at once.')
    if frames and st['name'] != 'lofi':
        L.append('- Drifting layers (clouds, fog, water) make whole trips per loop: at %d frames a %d px trip moves '
                 '%.0f px/s; if that is faster than the drift should feel (clouds 15 px/s or less), lengthen the '
                 'loop to a multiple of %d.' % (frames, w, w * fps / frames, frames))
    L.append('\n## 9. Particles')
    L.append('- TODO kinds, sprite variants, densities, depth layers, paths (hashed spawns, whole trips per loop).')
    L.append('\n## 10. Never')
    for x in r['never']:
        L.append('- ' + x + '.')
    banned = [b for b in st['banned_post'] if b not in ('vignette', 'grain', 'scanlines', 'aberration')]
    if banned:
        L.append('- Banned light ops: %s.' % ', '.join(banned))
    L.append('- TODO anything else this scene must not do.')
    L.append('\n## 11. Technical')
    if E:
        L.append('- %s limits: native %dx%d, at most %d colours on screen%s%s%s. No light layer, no dither the '
                 'console could not show. These override the style\'s canvas and colour count.' % (
                     E['name'], w, h, E['max_colors'], (', palette `%s`' % E['palette']) if E.get('palette') else '',
                     (', %d colours per %dx%d block' % (E['block_colors'], E['block'], E['block'])) if E.get('block') else '',
                     (', %d-colour sprites' % E['sprite_colors']) if E.get('sprite_colors') else ''))
        L.append('- Check: `pixelate era frame.png --era %s` (and `--force` to snap a draft); ramps picked from the '
                 'era palette, not palette.ramp.' % era)
    else:
        L.append('- Native %dx%d, %dx nearest to %dx%d; %s; about %d colours in the pixel layer.' % (
            w, h, st['scale'], w * st['scale'], h * st['scale'],
            'light layer at delivery size' if st['res'] == 'screen' else 'every cell flat at delivery size', st['colours']))
    L.append('- Figures: %s, drawn as your own slot maps.' % _as_example(st['figures']))
    L.append('- Budget (`styles.check`): %s.' % _fmt_budget(st['budgets']))
    L.append('- Gate: `pixelate check frame.png --style %s --scale %d` passes every line (redraw until it does)%s; '
             'frame T equals frame 0; reads at 480 px wide.' % (
                 st['name'], st['scale'], '; `pixelate check SCENE` for the engine scene' if st['name'] == 'lofi' else ''))
    L.append('- Show the user one still for go/no-go; animate only after they accept it and confirm the motion table.')
    L.append('\nTechniques for this style: ' + '; '.join(r['tools']) + '.')
    tt = topic_tools(request, st['name'], proj)
    if tt:
        L.append('Techniques for this subject:')
        L += ['- ' + x + '.' for x in tt]
    L.append('Always: ' + ALWAYS_TOOLS + '.')
    if r['example']:
        L.append('Closest example in the repo: %s.' % r['example'])
    return '\n'.join(L) + '\n'

# ---------------------------------------------------------------- the short brief, for small asks
# A palette, one sprite, an icon set, a pixelated photo, an asset sheet or a music loop does not need
# eleven sections. It gets a short brief: the intent, the style, the palette and size, the work, the gate
# command and what the user sees for go/no-go. --full forces the long brief anyway.
SMALL_WORDS = [
    ('palette', ['a palette', 'palette for', 'palette of', 'colour palette', 'color palette', 'just a palette',
                 'palette only', '调色板', '配色方案', '一套配色']),
    ('icons', ['icon', 'icon set', '图标']),
    ('photo', ['pixelate my', 'pixelate this', 'pixelate a', 'into pixel art', 'to pixel art', 'pixelated version',
               'convert', '转成像素', '变成像素', '像素化']),
]
SPRITE_WORDS = ['a sprite', 'one sprite', 'single sprite', 'sprite of', 'character sprite', 'avatar',
                'a pixel portrait', '一个精灵', '头像', '立绘']

def small_kind(request, r=None):
    """-> 'palette', 'icons', 'photo', 'assets', 'sprite', 'music' for a small ask (a short brief), else None"""
    r = r or route(request)
    t = ' ' + request.lower() + ' '
    if r['mode'] == 'music':
        return 'music'
    for kind, words in SMALL_WORDS:
        if _hits(t, words) and (kind != 'photo' or r['mode'] == 'rebuild'):
            return kind
    if r['mode'] == 'assets':
        return 'assets'
    if _hits(t, SPRITE_WORDS):
        return 'sprite'
    return None

def _as_example(s):
    """'chibi 13x26 (figures.chibi)' -> '... (study references/assets/figures.py chibi)': examples, not calls"""
    return re.sub(r'(?<![\w/.])(%s)\.(?!py\b|md\b)([A-Za-z_]\w*)' % '|'.join(EXAMPLE_MODULES),
                  r'study references/assets/\1.py \2', s)

def short_brief(style, request='', kind='sprite', r=None, era=None):
    """the short brief for a small ask: section 0 (intent and defaults), style, palette and size, the
    work, the gate command, what to show the user"""
    st = styles.get(style)
    w, h = st['size']
    S, N = st['name'], st['scale']
    E = None
    if era:
        import era as eramod
        E = eramod.ERAS[era]
        w, h = E['size']
    g = {x['topic']: x for x in gaps(request, r)} if r else {}
    file = {'palette': 'test.png', 'icons': 'icons.png', 'photo': 'out.png', 'assets': 'SHEET.png',
            'sprite': 'sprite.png', 'music': None}[kind]
    L = ['# TODO title (short brief: %s)\n' % kind, 'Request: %s\n' % (request or 'TODO')]
    L += ['## 0. Choices to confirm', '',
          'Defaults I picked where the request was open. Say OK to build as written, or change any line.', '',
          '- **intent**: TODO one line on what the user most likely wants but did not say (the feeling, the use, '
          'the game it is for, what would disappoint them)']
    if 'style' in g:
        L.append('- **style**: %s' % g['style']['default'])
    size = {'palette': 'about %d colours in `%s` ramps, 4-6 steps per role' % (st['colours'], ', '.join(st['ramp'])),
            'icons': '12 icons at 16x16 on one shared palette, lit from the upper left',
            'photo': 'native %dx%d, %dx nearest to %dx%d, about %d colours' % (w, h, N, w * N, h * N, st['colours']),
            'assets': 'TODO each sprite or tile with its size and frame count, for TODO the engine',
            'sprite': 'one sprite, %s, one pose facing right' % _as_example(st['figures']),
            'music': 'a seamless 60-120 s loop, calm, about 70-80 bpm'}[kind]
    L.append('- **%s**: %s' % ('length and mood' if kind == 'music' else 'size', size))
    if kind in ('sprite', 'assets', 'icons'):
        L.append('- **animation**: none until the still is accepted; then the frames and rates are confirmed first')
    if E:
        L.append('- **era limits**: %s: at most %d colours%s; check with `pixelate era IMG --era %s`' % (
            E['name'], E['max_colors'], (', palette %s' % E['palette']) if E.get('palette') else '', era))
    L.append('\n## 1. Style')
    L.append('- `%s` (learned from %s): %s.' % (S, st['ref'], st['what']))
    if kind != 'music':
        L.append('- Outline: %s. Dither: %s.' % (st['outline'], (', '.join(st['dither']) + ', ' + st['dither_where'])
                                                 if st['dither'] else 'none'))
    L.append('- Learn the grammar only: no characters, logos or UI from %s.' % st['ref'])
    if kind == 'music':
        L.append('\n## 2. Length and sound')
        L.append('- TODO the loop length in seconds, the tempo, the instruments, the motif.')
    else:
        L.append('\n## 2. Palette and size')
        if E:
            L.append('- %s: at most %d colours%s; ramps picked by hand from the era palette.' % (
                E['name'], E['max_colors'], (', palette `%s`' % E['palette']) if E.get('palette') else ''))
        else:
            L.append('- Ramps `%s` (palette.ramp(style="%s")): %s.' % (', '.join(st['ramp']), st['ramp'][0], st['palette']))
        L.append('- Size: %s.' % size.replace('TODO ', 'TODO: '))
    L.append('\n## 3. The work')
    L += {'palette': ['- TODO the roles (outline, shadow, mid, light, highlight per material, one accent) and the steps per role.',
                      '- A palette is judged on a sprite, not as chips: draw one small test sprite with it '
                      '(canvas.Canvas, palette.swatch for the chips).'],
          'icons': ['- TODO the icon list, one line each: the object and the one shape that tells it apart at 16 px.',
                    '- One ramp set, one outline rule and one light direction across the set.',
                    '- Each icon is a slot map in code; for a small readable mark, study references/assets/glyphs.py stamp.'],
          'photo': ['- TODO what the photo shows and what must survive: the subject, the light, the one detail people look for.',
                    '- First pass `pixelate image IMG -o out.png` (guides/pixelate.md), then fix by hand what it gets '
                    'wrong: the subject\'s edges, orphan pixels, outlines.',
                    '- A rebuilt, moving scene is a full brief: `route.py "..." --brief --full` with guides/rebuild.md.'],
          'assets': ['- TODO the list: each sprite or tile, its size, its frames (walk 4-8, idle 2-4).',
                     '- Each sprite is a slot map in code; for a similar finished thing, study references/assets/ '
                     'and draw your own at this size.',
                     '- Tiles seam on every edge pair (canvas.Canvas.tile); export with `pixelate assets PACK` (guides/assets.md).'],
          'sprite': ['- TODO the subject, its silhouette and the one feature that must read at 1x.',
                     '- Drawn as a slot map in code (canvas.Canvas, sprite.spec_edges, sprite.drop_shadow); for a '
                     'similar finished thing, study references/assets/ and draw your own.'],
          'music': ['- Start from `pixelate new music DIR` (guides/music.md).',
                    '- TODO what changes over the loop, and where the loop seam falls.']}[kind]
    tt = topic_tools(request, S)
    if tt and kind != 'music':
        L.append('- Techniques for this subject:')
        L += ['  - ' + x + '.' for x in tt]
    L.append('\n## 4. Gate')
    if kind == 'music':
        L.append('- `pixelate check DIR`, then `pixelate audio DIR loop.wav`: the seam holds below -60 dB.')
    else:
        L.append('- `pixelate check %s --style %s --scale %d`%s; redraw until every line passes.' % (
            file, S, N, ' --pal PALETTE' if kind == 'palette' else ''))
        if E:
            L.append('- `pixelate era %s --era %s`.' % (file, era))
    L.append('\n## 5. Show the user')
    L.append('- ' + {'palette': 'The chips and the test sprite side by side at 1x and %dx, for go/no-go.' % N,
                     'icons': 'The sheet at 1x and %dx, and one row at the size it will be used, for go/no-go.' % N,
                     'photo': 'The photo and the result side by side at the same size, for go/no-go.',
                     'assets': 'One finished sprite (or a 3x3 tile patch) as a still for go/no-go; then the frame '
                               'and rate plan for a go before animating.',
                     'sprite': 'The sprite at 1x and %dx on the style\'s background, for go/no-go; frames only '
                               'after that, with the plan confirmed.' % N,
                     'music': 'A 20-30 s excerpt for go/no-go before the full loop.'}[kind])
    return '\n'.join(L) + '\n'

# ---------------------------------------------------------------- regression cases
# (request, mode, acceptable top styles or None). The showcase video's prompts are here so the video
# can be reproduced from its one-liners; add a case whenever a request routes wrong.
CASES = [
    ('Rebuild this photo of an old stone viaduct over a misty gorge as pixel art. Keep the angle, and let a little '
     'red train cross it.', 'rebuild', {'illustrated'}),
    ('把这张雾中山谷石拱高架桥的照片重建成像素画，保持角度，让一列小红火车开过去。', 'rebuild', {'illustrated'}),
    ('A kid on a paper kite glides over a pink sea of clouds at sunrise, past little floating islands.', 'scene',
     {'pastel-cell'}),
    ('日出时分，一个小孩抓着纸风筝滑过一片粉色云海，经过几座漂浮的小岛。', 'scene', {'pastel-cell'}),
    ('Midnight on a mountain top. Light pours up out of a cracked-open observatory, and pilgrims with paper lanterns '
     'climb the steps.', 'scene', {'contre-jour'}),
    ('午夜山顶，一座裂开的天文台里涌出一道光柱，提着纸灯的朝圣者正沿石阶往上走。', 'scene', {'contre-jour'}),
    ('A busy canal market at noon in isometric. A swing bridge turns to let a tiny tram through, and there are people '
     'everywhere.', 'scene', {'sticker-iso'}),
    ('正午热闹的运河集市，等距视角。一座旋转桥转开让一辆小电车通过，到处都是小人。', 'scene', {'sticker-iso'}),
    ('A tiny noodle shop on a snowy night, seen from above. Warm lamps, steam rising, a cat by the window.', 'scene',
     {'cosy-lightmap'}),
    ('下雪的夜里，一家小面馆，从上往下看。暖黄的灯，热气往上冒，窗边趴着一只猫。', 'scene', {'cosy-lightmap'}),
    ('A Game Boy style lighthouse on a stormy night. Four shades of green, the beam sweeping over the waves.', 'era',
     None),
    ('掌机四色绿风格，暴风雨夜里的一座灯塔，光束扫过海浪。', 'era', None),
    ('A neon city at night, rain, a lone samurai under a ramen stall sign.', 'scene', {'neon-noir'}),
    ('Ancient ruins at dusk. A lone wanderer walks past, and glowing sigils wake up one by one.', 'scene',
     {'native-glow'}),
    ('把这张照片转成像素画', 'rebuild', None), ('turn my photo of the beach into pixel art', 'rebuild', None),
    ('make it look like a game boy game', 'era', None), ('SNES style castle', 'era', None),
    ('红白机风格的森林关卡', 'era', None), ('pico-8 style beach', 'era', None),
    ('a sprite sheet for a knight walk cycle', 'assets', None), ('a tileset for a forest', 'assets', None),
    ('游戏道具图标', 'assets', None), ('a chiptune music loop', 'music', None), ('只要音乐', 'music', None),
    ('make a pixel island', 'scene', {'lofi'}), ('做一个像素小岛', 'scene', {'lofi'}),
    ('lofi study music video with a cat at a window', 'scene', {'lofi'}),
    ('a windy mountain summit, celeste vibes', 'scene', {'pastel-cell'}),
    ('a lone wanderer in glowing ancient ruins', 'scene', {'native-glow'}),
    ('a sunny jrpg harbour town', 'scene', {'hd-overworld'}),
    ('metal slug style tank battle', 'scene', {'arcade'}), ('soldiers and explosions', 'scene', {'arcade'}),
    ('mechs fighting on a grid, into the breach', 'scene', {'tactics'}),
    ('a turn-based battle map', 'scene', {'tactics'}), ('an isometric castle siege', 'scene', {'tactics'}),
    ('an isometric city block with tiny people', 'scene', {'sticker-iso'}),
    ('a busy japanese street market', 'scene', {'sticker-iso'}),
    ('一个热闹的中国古镇夜市', 'scene', {'sticker-iso'}),
    ('a giant stone monument with an airship', 'scene', {'illustrated'}),
    ('owlboy style floating island', 'scene', {'illustrated'}),
    ('a samurai in a neon alley in the rain', 'scene', {'neon-noir'}), ('赛博朋克霓虹雨夜', 'scene', {'neon-noir'}),
    ('一个赛博朋克雨夜的小巷，有个武士', 'scene', {'neon-noir'}),
    ('a cosy farm at night', 'scene', {'cosy-lightmap'}), ('矿洞里的油灯', 'scene', {'cosy-lightmap'}),
    ('a cosy mine with lanterns and a slime', 'scene', {'cosy-lightmap'}),
    ('雨夜里温馨的小村庄', 'scene', {'cosy-lightmap'}),
    ('a backlit forest ritual in fog', 'scene', {'contre-jour'}),
    ('sword and sworcery style mountain', 'scene', {'contre-jour'}), ('雾中的森林剪影', 'scene', {'contre-jour'}),
    ('一个夜晚的山顶天文台, 有雾和光柱', 'scene', {'contre-jour'}),
    ('a lighthouse in a storm', 'scene', {'lofi', 'pastel-cell', 'contre-jour'}),
    ('a cosy coffee shop interior in the morning', 'scene', {'lofi', 'cosy-lightmap'}),
    ('a sunny harbour town with boats and gulls', 'scene', {'hd-overworld', 'sticker-iso'}),
]

def selftest(verbose=False):
    """-> number of cases that route wrong (printed)"""
    bad = 0
    for q, mode, ok in CASES:
        r = route(q)
        top = r['picks'][0]['style']
        wrong = r['mode'] != mode or (ok is not None and top not in ok)
        bad += wrong
        if wrong or verbose:
            print('%s %-7s %-14s %s' % ('XX' if wrong else '  ', r['mode'], top, q[:70]))
    print('%d/%d cases route as expected' % (len(CASES) - bad, len(CASES)))
    return bad

def main(a):
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return 1
    if a[0] == '--selftest':
        return 1 if selftest('-v' in a) else 0
    if a[0] == '--catalog':
        dest = pathlib.Path(__file__).resolve().parent.parent / 'guides' / 'toolkit.md'
        dest.write_text(catalog()); print('wrote', dest)
        return 0
    if a[0] == '--lint':
        probs = lint(pathlib.Path(a[1]).read_text())
        for x in probs:
            print('- ' + x)
        print('ready to show' if not probs else '\n%d problem(s): fix them before showing the brief' % len(probs))
        return 1 if probs else 0
    out = None
    if '-o' in a:
        i = a.index('-o'); out = a[i + 1]; del a[i:i + 2]
    full = '--full' in a
    if full:
        a.remove('--full')
    want = None
    if '--brief' in a:
        i = a.index('--brief')
        if i + 1 < len(a) and not a[i + 1].startswith('-') and a[i + 1] in list(styles.STYLES) + list(styles.ALIASES):
            want = a[i + 1]; del a[i + 1]
        del a[i]
        want = want or True
    req = ' '.join(a)
    r = route(req)
    if want:
        style = r['picks'][0]['style'] if want is True else want
        kind = None if full else small_kind(req, r)
        if kind:
            text = short_brief(style, req, kind, r, era=r.get('era'))
        else:
            text = brief(style, req, choices=gaps(req, r), era=r.get('era'))
        if out:
            pathlib.Path(out).write_text(text); print('wrote', out)
        else:
            print(text)
        return 0
    print('request: %s' % req)
    print('mode: %s (read %s)%s' % (r['mode'], r['guide'], '' if r['mode'] == 'scene' else ', then a style for the finish'))
    for i, p in enumerate(r['picks']):
        st = styles.get(p['style'])
        print('\n%d. %s  (score %d, %s, light %s, %dx %dx%d)' % (i + 1, p['style'], p['score'], p['projection'],
              st['res'], st['scale'], *st['size']))
        print('   why: ' + '; '.join(p['why']))
        print('   pick it for: ' + p['pick_if'])
        if p['example']:
            print('   example: ' + p['example'])
    tt = topic_tools(req, r['picks'][0]['style'], r['picks'][0]['projection'])
    if tt:
        print('\ntechniques for the subject:')
        for x in tt:
            print('   ' + x)
    print('\nleft open by the request (default for %s):' % r['picks'][0]['style'])
    for x in gaps(req, r):
        print('   %s: %s' % (x['topic'], ('stated (%s)' % x['stated']) if x['stated'] else x['default']))
    kind = small_kind(req, r)
    if kind:
        print('\na small ask (%s): --brief writes the short brief; add --full for all 11 sections' % kind)
    print('\nnext: route.py "%s" --brief %s -o brief.md, fill every TODO with the defaults,' % (req, r['picks'][0]['style']))
    print('      route.py --lint brief.md, then show the user the brief and section 0')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
