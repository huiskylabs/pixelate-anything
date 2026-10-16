#!/usr/bin/env python3
"""Style routing: a plain request in, the style to build it in and a pre-filled scene brief out.

usage: route.py "a cosy rainy village at night"            the top 3 styles, with reasons, and what
                                                           the request leaves open (with defaults)
       route.py "..." --brief [STYLE] [-o brief.md]        the 11-section brief, pre-filled for the
                                                           top style (or STYLE), to finish by hand
       route.py --lint brief.md                            self-critique of a finished brief: what
                                                           is still vague, missing or thin
       route.py --catalog                                  regenerate guides/toolkit.md, every tool

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
        tools=['palette.ramp (lofi)', 'engine bands() and blit', 'artlib Grid sprites', 'sceneDynamic flick()',
               'pixelate check'],
        never=['glow blur, bloom, lens effects, soft shadows', 'narrow gradient bands that read as stripes']),
    'pastel-cell': dict(
        pick_if='a high-key, one-hue mood (pink, violet, dusk), a tiny expressive hero in a big vertical world, '
                'weather; soft glow but still whole pixels',
        projection='side', example='examples/indie/art/rose_squall.py', frames=(120, 30),
        signals=[(6, ['celeste', 'rose squall', '蔚蓝']),
                 (3, ['pastel', 'pink', 'rose', 'dreamy', 'platformer', 'climb', 'climbing', 'mountain',
                      '粉', '玫瑰', '梦幻', '平台跳跃', '攀爬', '登山', '山顶']),
                 (2, ['dusk', 'sunset', 'storm', 'squall', 'wind', 'cliff', 'scarf', 'jump', 'dash', 'cute',
                      '黄昏', '晚霞', '暴风', '风暴', '悬崖', '围巾', '冲刺', '可爱'])],
        rules=['All hues inside one window (about 245-350); the floor is lifted, no scenery below L .37.',
               'Sky in flat undithered strata locked by tapered wisps; boundaries walk in flat runs.',
               'Rock is a ledged, frayed silhouette with a lit rim and stacked flake dashes, no outline.',
               'Only the actor and one interactive prop are outlined (dark violet); they carry the top chroma.',
               'Bloom only from cloud and emitter masks, computed per art pixel.'],
        tools=['palette.ramp(style="window") + palette.grade(hue_window, floor_L)', 'sky.strata / sky.wisp / sky.smile',
               'shapes.cloud_mass, shapes.ledges, shapes.fray', 'texture.flakes', 'sprite.chain (scarf, hair)',
               'post.Post(res="native").glow(mask) / band / tint_field', 'post rain style "cell"', 'fx.burst'],
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
        tools=['palette.families / drift / drift_index', 'post.Post(res="native").glow(kernel="exp") / band / fade',
               'texture.tapestry, glyphs.rune', 'fx.pixel_motes'],
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
        rules=['Ramps of 5-9 steps at about 0.05 L, chroma rising toward the light (ramp style rise).',
               'Outlines per class in tinted near-blacks (terrain plum, characters navy, foliage green).',
               'Clouds are a translucent layer at an altitude, thinning as terrain rises into them.'],
        tools=['palette.ramp(style="rise")', 'layout.ashlar / texture.shade_cells (slab, pillow)',
               'veg.leaf_scales', 'water.depth_bands / foam_rings / waterfall', 'shapes.cloud', 'post.over',
               'figures.chibi'],
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
        tools=['palette.ramp(style="arcade")', 'fx.fireball / smoke_puff / trail / muzzle / casing / debris',
               'anim.Timeline / shake / timewarp', 'texture.pocks / segments / panels', 'era neogeo check'],
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
        tools=['iso.Iso render', 'palette.ramp(style="arch") + neutral_ramp', 'compose.stage', 'pixfont'],
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
        tools=['iso.Iso', 'palette.ramp(style="flat")', 'veg.leaf_glyphs', 'figures.iso_person', 'props.car / pole / tyre',
               'compose.populate / strips', 'anim.lane_offset'],
        never=['light of any kind', 'cast shadows', 'empty areas']),
    'illustrated': dict(
        pick_if='an illustration-grade sky world: floating islands, carved stone, a monument, painterly depth '
                'by palette haze',
        projection='side', example=None, frames=(96, 12),
        signals=[(6, ['owlboy']),
                 (3, ['floating island', 'sky island', 'monument', 'carved', 'statue', 'painterly', 'illustration',
                      '浮空岛', '天空岛', '纪念碑', '雕刻', '雕像', '插画']),
                 (2, ['sky', 'clouds', 'detailed', 'ornate', 'stone', 'vines', 'roots', 'flying',
                      '天空', '细致', '华丽', '石头', '藤', '根', '飞', 'dragon', 'giant', 'colossus', 'castle', 'airship',
                      '龙', '巨人', '城堡', '飞艇'])],
        rules=['The environment stays in L .30-.78 at low chroma; the extremes are for actors, effects and HUD.',
               'Stone is carved: cells with a lit rim, checker wear, selective outlines.',
               'Depth comes from palette haze per plane, never from blur; a frame of foliage is drawn into the art.'],
        tools=['palette.ramp(style="living") + palette.haze', 'layout.ashlar / polar_blocks + texture.shade_cells',
               'veg.leafmass / vine / fern', 'water.reflect (glaze)', 'compose.frame_mask'],
        never=['soft light layers', 'filters', 'dark scenery']),
    'neon-noir': dict(
        pick_if='a neon-lit night interior or city: noir, crime, a bar, a club, rain on neon; one lit room in black',
        projection='side', example=None, frames=(120, 12),
        signals=[(6, ['katana zero', 'katana']),
                 (3, ['neon', 'noir', 'cyberpunk', 'club', 'bar', 'crime', 'detective', 'nightclub', 'synthwave',
                      '霓虹', '黑色电影', '赛博', '夜店', '酒吧', '犯罪', '侦探']),
                 (2, ['night city', 'alley', 'motel', 'hotel', 'apartment', 'rain city', 'magenta',
                      '夜城', '小巷', '旅馆', '公寓', '城市夜', 'space station', 'spaceship', 'sci-fi', 'scifi', 'android',
                      '太空站', '飞船', '科幻', '太空', '机器人'])],
        rules=['A lit room slab floating in exact black; a multiplied wall-wash light per art pixel.',
               'One teal exit and one magenta hero carry the colour; everything else is wood, stone and black.',
               'Actors have no outline, only a 1 px warm rim on the lamp side.'],
        tools=['palette.ramp(style="lit")', 'post.Post(res="native").lightmap / band / glow(kernel="outer") / fade',
               'light.void_fade', 'figures.thin', 'texture.panels / slats'],
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
        tools=['palette.ramp(style="plum") / ramp(style="toy")', 'post.Post(res="screen").lightmap',
               'texture.pebbles / layout + texture.shade_cells(pillow)', 'shapes.void_edge', 'figures.chibi', 'compose.room'],
        never=['screen-blend light', 'filters', 'a lifted void']),
    'contre-jour': dict(
        pick_if='a cinematic, mysterious night: silhouettes against fog and glowing air, a ritual, a forest, a '
                'pillar of light; soft light at screen resolution between depth planes',
        projection='side', example=None, frames=(192, 12),
        signals=[(6, ['sworcery', 'superbrothers']),
                 (3, ['silhouette', 'backlit', 'contre-jour', 'fog', 'mist', 'cinematic', 'pillar of light', 'ritual',
                      'procession', 'pilgrim', 'shrine', '剪影', '逆光', '雾', '电影感', '光柱', '仪式', '朝圣', '神社']),
                 (2, ['mysterious', 'forest', 'moon', 'moonlight', 'night', 'standing stone', 'eerie', 'solemn',
                      '神秘', '森林', '月', '夜', '立石', '肃穆'])],
        rules=['One navy covers most of the frame; at least 55% of pixels below L .25, highlights rare.',
               'Near planes are flat near-black silhouettes with leafy broken edges; they never take light.',
               'All softness is a screen-resolution light layer composited between depth planes (post.Stack).',
               'Figures are slim, 20-30 px, 1 px legs, no outline; leaf-light flecks take their nearest light\'s colour.'],
        tools=['palette.ramp_between + palette.haze_levels', 'post.Stack + Post(res="screen").light / shaft / flare',
               'post rain style "hair"', 'texture.leaflight', 'figures.slim', 'compose.proscenium'],
        never=['outlines', 'dither', 'light on the near plane', 'filters']),
}

MODES = [
    ('rebuild', 3, ['photo', 'picture of', 'my photo', 'aerial', 'rebuild', 'this image', 'from this',
                    '照片', '这张图', '航拍', '重建']),
    ('era', 3, ['nes', 'game boy', 'gameboy', '8-bit', '8 bit', '16-bit', '16 bit', 'snes', 'genesis', 'mega drive',
                'gba', 'pico-8', 'pico8', '红白机', '8位', '16位']),
    ('assets', 2, ['sprite sheet', 'spritesheet', 'tileset', 'character sheet', 'icons', 'items', 'walk cycle',
                   '精灵表', '图块', '图标', '道具', '行走']),
    ('music', 3, ['soundtrack only', 'just music', 'music loop', 'chiptune', '只要音乐', '配乐']),
]
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
        if dark and name in BRIGHT_STYLES and name != 'pastel-cell':
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
    return dict(request=request, picks=picks, mode=mode, guide=GUIDE[mode], projection=proj)

# ---------------------------------------------------------------- tools by subject, whatever the style
# The style decides how things are shaded; the subject decides what gets drawn. Each entry: the words
# that bring it in and the kit calls that draw it.
TOPIC_TOOLS = [
    (['rain', 'storm', 'wet', 'puddle', '雨', '暴风', '湿', '水坑'],
     'rain and wet: fx.rain_cells (opaque streaks), fx.light_streaks, texture.wet_streaks (speculars on up-facing edges), '
     'water.reflect for puddles, Post rain:hair at screen res where the style allows it'),
    (['snow', 'winter', 'ice', '雪', '冬', '冰'],
     'snow and ice: texture.speckle for flakes on dark, texture.stipple for drifts, sky.strata for a flat winter sky'),
    (['fog', 'mist', 'haze', '雾', '霭'],
     'fog: palette.haze and haze_levels per depth plane, Post fog where allowed, canvas.loop_dissolve for drifting banks'),
    (['sea', 'ocean', 'lake', 'river', 'stream', 'harbour', 'harbor', 'coast', 'beach', 'waterfall', 'pond', 'canal',
      '海', '湖', '河', '溪', '港', '海岸', '沙滩', '瀑布', '池塘', '运河'],
     'water: water.depth_bands, water.foam_rings, water.pool, water.waterfall, water.reflect'),
    (['forest', 'tree', 'trees', 'garden', 'jungle', 'park', 'leaf', 'leaves', '森林', '树', '花园', '丛林', '公园', '叶'],
     'foliage: veg.leaf_scales (round canopies), veg.leaf_glyphs, veg.leafmass, texture.leaflight (flecks in dark '
     'foliage), props.trunk, shapes.lobes_along for far tree lines'),
    (['sky', 'cloud', 'clouds', 'sunset', 'dusk', 'dawn', '天空', '云', '日落', '黄昏', '清晨'],
     'sky: sky.strata, sky.wisp, sky.smile, sky.streaks, shapes.cloud / cloud_mass / cloud_mask'),
    (['cave', 'mine', 'rock', 'cliff', 'mountain', 'rubble', 'stone', '洞', '矿', '岩', '悬崖', '山', '石'],
     'rock: texture.stones (rubble, cave walls), texture.flakes (layered rock), texture.pebbles, shapes.ledges, '
     'shapes.noisy_edge, shapes.void_edge, props.rails and props.stairwell underground'),
    (['city', 'town', 'street', 'building', 'house', 'houses', 'village', 'alley', 'castle', 'wall', 'brick',
      '城', '镇', '街', '楼', '房', '村', '巷', '城堡', '墙', '砖'],
     'buildings: layout.ashlar and texture.shade_cells for stone, texture.bricks, texture.panels, texture.mottle, '
     'texture.inset_frame for trim, props.glass_streak for windows, iso.Iso boxes in iso'),
    (['industrial', 'factory', 'crane', 'construction', 'bridge', 'tower', 'harbour crane', '工厂', '吊车', '工地', '塔'],
     'structure: props.girders, props.truss, texture.grille, texture.pits for concrete'),
    (['tech', 'sci-fi', 'scifi', 'robot', 'mech', 'machine', 'computer', 'neon', 'space', '科技', '科幻', '机器', '机甲',
      '电脑', '霓虹', '太空'],
     'tech: texture.circuit, texture.emitter_grid (lamp panels), fx.indicator, texture.grille, fx.emissive for screens'),
    (['ruin', 'ruins', 'temple', 'rune', 'magic', 'spell', 'shrine', '遗迹', '神殿', '符文', '魔法', '法术', '神社'],
     'magic and ruins: glyphs.rune and glyphs.stamp, anim.cascade (runes lighting in turn), fx.pixel_motes, '
     'texture.tapestry, texture.circuit'),
    (['fire', 'explosion', 'battle', 'fight', 'gun', 'shoot', 'war', 'boss', 'sword', '火', '爆炸', '战斗', '打', '枪',
      '射击', '战争', '剑'],
     'action: fx.fireball, fx.puff, fx.burst, fx.shot, fx.muzzle_light, fx.hit_flash, fx.crescent (swing trails), '
     'fx.tumble, anim.recoil, anim.arc'),
    (['lamp', 'lantern', 'candle', 'torch', 'window', 'fireplace', 'neon sign', '灯', '灯笼', '蜡烛', '火把', '窗',
      '壁炉'],
     'small lights: light.flicker (held steps), light.rim, anim.chase (marquee and signal lights), '
     'Post lightmap / light / glow per the style'),
    (['crowd', 'people', 'busy', 'traffic', 'market', 'festival', 'car', 'cars', '人群', '热闹', '车', '集市', '夜市',
      '庙会'],
     'crowds: compose.populate (traffic and crowds in iso), props.car, figures.iso_person, compose.check_density'),
    (['cat', 'dog', 'deer', 'horse', 'animal', 'bird', 'birds', 'fish', 'slime', '猫', '狗', '鹿', '马', '动物', '鸟',
      '鱼'],
     'animals: figures.quadruped_slim, anim.hop (squash and hop), anim.orbit (birds, fish), anim.lag for tails'),
    (['person', 'people', 'character', 'hero', 'girl', 'boy', 'man', 'woman', 'kid', 'knight', 'samurai', 'walk',
      '人', '角色', '主角', '女孩', '男孩', '骑士', '武士', '走'],
     'figures: figures.chibi / slim / thin / iso_person per the style, anim.lag for hair, capes and scarves, '
     'sprite.chain for ropes and scarves, sprite.drop_shadow, sprite.spec_edges'),
]
ALWAYS_TOOLS = ('checks: stats.budget_report (the style budget), anim.check_periods (every period divides the loop), '
                'compose.check_density for busy scenes, styles.check on a delivered frame')

CATALOG = [('post', 'the light layer: Post (none/native/screen), Stack (depth planes), light, glow, shaft, flare, streak, lightmap, fog, rain, motes'),
           ('light', 'light drawn in palette steps: point lights, rims, flicker, void fades'),
           ('palette', 'ramps per style, palettes, haze, grading, hue families, slots'),
           ('texture', 'surface patterns: pebbles, stones, bricks, panels, flakes, leaf-light, stipples, wet speculars, circuits'),
           ('layout', 'cell layouts for masonry and blocks, and their shading'),
           ('shapes', 'silhouettes: clouds, ledges, frayed and noisy edges, lobes, void edges'),
           ('sky', 'skies: strata, wisps, streaks, crescents'),
           ('water', 'water: depth bands, foam rings, pools, waterfalls, reflections'),
           ('veg', 'foliage: leaf scales, leaf glyphs, leaf masses, framed fields'),
           ('props', 'built things: trunks, girders, trusses, rails, stairwells, cars, glass'),
           ('figures', 'characters per style: chibi, slim, thin, iso people, quadrupeds'),
           ('sprite', 'sprite helpers: chains (ropes, scarves), drop shadows, specular edges'),
           ('anim', 'motion: timelines, hold tables, hops, lag, recoil, arcs, orbits, chases, cascades, period checks'),
           ('fx', 'effects as pixels: rain cells, fireballs, puffs, bursts, shots, flashes, trails, motes, indicators'),
           ('glyphs', 'original runes and stamps'),
           ('compose', 'composition: frames, prosceniums, stages, rooms, plans, crowds, density checks'),
           ('canvas', 'the canvas: slots, thresholds, parallax, seamless loop dissolves'),
           ('morph', 'mask operations: dilate, erode, distance, normals, regions, relief'),
           ('iso', '2:1 isometric boxes and scenes'),
           ('stats', 'measuring a frame against a style budget'),
           ('styles', 'the 11 style presets, their budgets and checks')]

def catalog():
    """guides/toolkit.md: every public function and class in the kit with its first doc line, so an
    agent knows everything it can reach for before it writes a brief. Regenerate with --catalog."""
    import importlib, inspect
    L = ['# Toolkit', '',
         'Every function in the kit, with its first doc line. Generated by `python3 tools/route.py --catalog`;',
         'regenerate it after adding a tool. Read it before writing a brief: the router only suggests the',
         'tools its keywords know about, and the best brief uses whatever the scene needs.', '']
    L.append('## By subject\n')
    for words, line in TOPIC_TOOLS:
        L.append('- ' + line[0].upper() + line[1:] + '.')
    L.append('- ' + ALWAYS_TOOLS[0].upper() + ALWAYS_TOOLS[1:] + '.')
    for mod, what in CATALOG:
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

def topic_tools(request):
    t = ' ' + request.lower() + ' '
    return [line for words, line in TOPIC_TOOLS if _hits(t, words)]

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
    add('time and weather', WORDS['time'], TIME_DEFAULT.get(st['name'],
        'night, one main light source, light rain' if dark else 'late afternoon, clear, low warm sun'))
    add('phases', WORDS['phases'],
        'four seasons, each with its own signature elements (as Lantern Isle)' if st['name'] == 'lofi'
        else 'one phase, no cycle')
    add('figures', WORDS['figures'],
        'one or two small figures doing a quiet, specific task (%s)' % st['figures'])
    add('purpose and outputs', WORDS['purpose'],
        'a gallery showcase: seamless %s-frame loop at %d fps as 1080p MP4, a GIF excerpt and a still' % (
            frames or 'TODO', st['fps']))
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
    table without numbers, periods that don't divide the loop. Empty means it is ready to show."""
    probs = []
    left = text.count('TODO')
    if left:
        probs.append('%d TODO left: fill each with a concrete choice (or a default listed in section 0)' % left)
    parts = re.split(r'^##\s+(?:\d+\.\s*)?', text, flags=re.M)
    body = {}
    for part in parts[1:]:
        head, _, rest = part.partition('\n')
        body[head.strip()] = rest
    def find(name):
        return next((v for k, v in body.items() if k.lower().startswith(name.lower())), None)
    for sec in SECTIONS:
        b = find(sec)
        if b is None:
            probs.append('missing section: %s' % sec)
            continue
        n = len(re.findall(r'^\s*[-*]\s+\S', b, flags=re.M))
        if n < MIN_BULLETS.get(sec, 1):
            probs.append('%s is thin: %d items, want %d or more' % (sec, n, MIN_BULLETS.get(sec, 1)))
        for w in VAGUE:
            if re.search(r'\b' + re.escape(w.strip()) + r'\b', b.lower()):
                probs.append('%s says "%s": name the thing, the count or the colour instead' % (sec, w.strip()))
    m = find('Motion table')
    if m is not None and not re.search(r'\d+\s*(frames?|fps|drawings?|ticks?)', m):
        probs.append('Motion table has no frame counts or rates')
    head = re.search(r'Motion table[^\n]*?(\d+)\s*frames', text)
    if head and m:
        T = int(head.group(1))
        for k in re.findall(r'every\s+(\d+)\s+frames', m):
            if T % int(k):
                probs.append('Motion table: a period of %s frames does not divide the %d-frame loop' % (k, T))
    li = find('Light list')
    if li is not None and not re.search(r'\d', li):
        probs.append('Light list has no sizes or radii: give every emitter a colour, a radius and what hides it')
    sc = find('The scene')
    if sc is not None and not re.search(r'\d', sc):
        probs.append('The scene has no counts, sizes or positions')
    lv = find('Lived-in details')
    if lv is not None and re.search(r'imperfect|lean|sag|missing|broken|patched|worn', text.lower()) is None:
        probs.append('no built-in imperfections anywhere (a lean, a sag, a missing plank, a patch)')
    probs += _tool_refs(text)
    return probs

KIT_MODULES = ('post', 'light', 'palette', 'texture', 'layout', 'shapes', 'figures', 'props', 'compose', 'anim',
               'sprite', 'fx', 'glyphs', 'sky', 'veg', 'water', 'canvas', 'morph', 'stats', 'styles', 'assets')

def _tool_refs(text):
    """every `module.name` (or `module.Class.name`) in backticks must exist in the kit"""
    import importlib
    bad = []
    for ref in sorted(set(re.findall(r'`([a-z_]+(?:\.[A-Za-z_]+)+)', text))):
        mod, *path = ref.split('.')
        if mod not in KIT_MODULES:
            continue
        try:
            obj = importlib.import_module(mod)
            for k in path:
                obj = getattr(obj, k)
        except Exception:
            bad.append('`%s` is not in the kit: use a real function or name the tool gap' % ref)
    return bad

# ---------------------------------------------------------------- the pre-filled brief
def _fmt_budget(b):
    return '; '.join('%s %s' % (k, ('>= %s' % lo) if hi is None else ('<= %s' % hi) if lo is None else
                                '%s..%s' % (lo, hi)) for k, (lo, hi) in b.items()) or 'none (look at it)'

def brief(style, request='', projection=None, choices=None):
    """the craft.md brief as Markdown, with everything the style decides filled in and the
    scene-specific parts as TODO prompts; choices (from gaps()) adds section 0"""
    st = styles.get(style)
    r = ROUTE[st['name']]
    w, h = st['size']
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
    L.append('- Loop: %s frames at %d fps.%s' % (frames or 'TODO', fps, ' Delivered prescaled (screen light).' if st['res'] == 'screen' else ''))
    L.append('\n## 2. Style and light regime')
    L.append('- Style `%s` (learned from %s): %s.' % (st['name'], st['ref'], st['what']))
    L.append('- Light: %s; blend %s.' % (light, ', '.join(st['blend']) or 'none'))
    L.append('- Ramps: `%s`. Palette: %s.' % (', '.join(st['ramp']), st['palette']))
    L.append('- Outline: %s. Dither: %s.' % (st['outline'], (', '.join(st['dither']) + ', ' + st['dither_where']) if st['dither'] else 'none'))
    L.append('- Learn the grammar only: no characters, places, logos or UI layouts from %s. TODO name anything else to avoid.' % st['ref'])
    L.append('\n## 3. Art direction rules')
    for x in r['rules']:
        L.append('- ' + x)
    L.append('- TODO 3-5 rules for this scene: which silhouettes must read, where rims fall, the built-in imperfections '
             '(a lean, a sag, a missing plank, a mismatched part).')
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
    L.append('\n## 8. Motion table')
    L.append('- Motion: %s at about %d fps; every period divides the loop (anim.check_periods).' % (
        'stepped, hold tables' if st['motion'] == 'stepped' else 'actors move in screen pixels', fps))
    L.append('- TODO every moving thing with its frame count and rate; keep only a few things moving at once.')
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
    L.append('- Native %dx%d, %dx nearest to %dx%d; %s; about %d colours in the pixel layer.' % (
        w, h, st['scale'], w * st['scale'], h * st['scale'],
        'light layer at delivery size' if st['res'] == 'screen' else 'every cell flat at delivery size', st['colours']))
    L.append('- Figures: %s.' % st['figures'])
    L.append('- Budget (`styles.check`): %s.' % _fmt_budget(st['budgets']))
    L.append('- Checks: frame T equals frame 0; `python3 tools/styles.py %s frame.png --scale %d`; reads at 480 px wide.' % (
        st['name'], st['scale']))
    L.append('\nTools for this style: ' + '; '.join(r['tools']) + '.')
    tt = topic_tools(request)
    if tt:
        L.append('Tools for this subject:')
        L += ['- ' + x + '.' for x in tt]
    L.append('Always: ' + ALWAYS_TOOLS + '.')
    if r['example']:
        L.append('Closest example in the repo: %s.' % r['example'])
    return '\n'.join(L) + '\n'

def main(a):
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return 1
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
        text = brief(r['picks'][0]['style'] if want is True else want, req, choices=gaps(req, r))
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
    tt = topic_tools(req)
    if tt:
        print('\ntools for the subject:')
        for x in tt:
            print('   ' + x)
    print('\nleft open by the request (default for %s):' % r['picks'][0]['style'])
    for x in gaps(req, r):
        print('   %s: %s' % (x['topic'], ('stated (%s)' % x['stated']) if x['stated'] else x['default']))
    print('\nnext: route.py "%s" --brief %s -o brief.md, fill every TODO with the defaults,' % (req, r['picks'][0]['style']))
    print('      route.py --lint brief.md, then show the user the brief and section 0')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
