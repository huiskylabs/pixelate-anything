#!/usr/bin/env python3
"""Style routing: a plain request in, the style to build it in and a pre-filled scene brief out.

usage:
  pixelate route "a cosy rainy village at night"   the top 3 styles, with reasons, and what the
                                                   request leaves open (with defaults)
  pixelate route --intake "REQUEST"              JSON plan: optional scene questions and the route result
  pixelate route "..." --brief [STYLE] [-o FILE]   the 11-section brief, pre-filled for the top style
                                                   (or STYLE), to finish by hand; a small ask (a
                                                   palette, one sprite, an icon set, a photo, assets,
                                                   music) gets a short brief instead
  pixelate route "..." --brief --full              the 11 sections even for a small ask (--full or -o
                                                   alone imply --brief)
  pixelate route "..." --brief --size 1920x1080 [--scale N]
                                                   the delivered picture: the canvas is size / scale,
                                                   the scale picked to keep the style's native height
                                                   when not given; a size in the request (3840x2160,
                                                   4k, 1080p) works too; figure sizes follow
  pixelate route --lint brief.md                   self-critique of a finished brief: what is still
                                                   vague, missing or thin
  pixelate route --catalog                         regenerate guides/toolkit.md, the index of the kit
                                                   (the kit itself: `pixelate tools`)
  pixelate route --selftest [-v]                   route the regression cases (CASES)

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

The brief it writes is the template from references/brief.md with every section the style decides
already filled in. The scene-specific sections (the objects, the lived-in details, the palette by
role, the light list, the motion table) are left as TODO prompts, each naming the section to read
(references/brief.md, drawing.md, delivery.md) and the command to run (`pixelate style S`,
`pixelate tools TOPIC`): write them to the density of library/lantern-isle/brief.md before building
anything.

A one-line request ("make me a pixel island") is not a brief. gaps() lists what the request leaves
open (time and weather, phases, figures, purpose and outputs, music, projection, the style itself)
and the default each one takes for the chosen style. The agent expands the request into the full
brief using those defaults, runs lint() on it as a self-critique, and shows the user the brief with
the list of choices it made. If the user says OK, one round turns the one line into a Lantern Isle
level brief; if not, they change what they want and the brief is revised, a round at a time.
"""
import json
import pathlib
import re
import sys
from typing import Literal, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import styles

# ---------------------------------------------------------------- what each style is for
# signals: (weight, words). English words match whole words (plurals with -s too), Chinese as substrings.
# A named reference game or a repo example is the strongest signal (6); subject and mood 2-3.
ROUTE = {
    'lofi': dict(
        pick_if='a calm looping cover for music: a cottage, an island, seasons, a window at night; light drawn '
                'with palette colours only',
        projection='side', example='library/lantern-isle (brief.md is the bar)', frames=(None, 30),
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
        projection='side', example='library/rose-squall/art/rose_squall.py', frames=(120, 30),
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
        rules=['Sun and shade are palette steps, not a light layer: light.Light.mask / apply for pools; '
               'post.over only for translucent clouds.',
               ("Hard cast shadows from iso.Iso(camera='topdown').cast_shadows.", 'topdown'),
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
        projection='2:1 iso', example='library/projections', frames=(96, 12),
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
        projection='2:1 iso', example='library/san-francisco (iso diorama)', frames=(96, 12),
        signals=[(6, ['freitas', 'eboy']),
                 (3, ['isometric city', 'iso city', 'street', 'market', 'crowd', 'busy', 'town square', 'traffic',
                      '等距城市', '街道', '集市', '人群', '热闹', '广场', '车流', '夜市', '古镇', '庙会', 'festival', 'fair']),
                 (2, ['isometric', 'iso', 'city', 'town', 'noon', 'shops', 'tram', 'canal',
                      '等距', '城市', '小镇', '中午', '商店', '电车', '运河'])],
        rules=['Paint at the gamut edge, black silhouettes, no light and no shadows.',
               'Density is the subject: a readable little story in every 100 px window.',
               'Trees are leaf-glyph canopies on black; people are 3.3-head iso figures.'],
        tools=['iso boxes (iso.Iso)', 'the black silhouette round every object in a full-bleed scene (iso.Iso.render(silhouette=True))',
               'flat paints at the gamut edge (palette.ramp(style="flat"))',
               'leaf-glyph canopies on black (veg.leaf_glyphs)',
               'people and cars as your own slot maps (study references/assets/figures.py iso_person and props.py car, pole, tyre)',
               'your own cars and people placed on lanes and plazas: compose only lays them out, your car= and person= functions draw them (compose.populate, compose.strips, anim.lane_offset)'],
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
               'Near planes are flat near-black silhouettes with leafy broken edges; they never take light. Keep them at least '
               '0.06 darker in OkLab L than the sky or fog right behind them (sky navy about L .24-.28, the near plane L .16 '
               'or lower), or the silhouette vanishes into the sky.',
               'All softness is a screen-resolution light layer composited between depth planes (post.Stack).',
               'Figures are slim, 20-30 px, 1 px legs, no outline; leaf-light flecks take their nearest light\'s colour.'],
        tools=['a bridge ramp between two hues, hazed per plane (palette.ramp_between, palette.haze_levels)',
               'soft light between depth planes at screen resolution (post.Stack, Post(res="screen").light, shaft, flare)',
               'hairline rain (Post rain style "hair")', 'leaf-light flecks in dark foliage (texture.leaflight)',
               'slim 20-30 px figures as your own slot maps (study references/assets/figures.py slim)',
               'a proscenium of near silhouettes (compose.proscenium)'],
        never=['outlines', 'dither', 'light on the near plane', 'filters']),
    'ink-wash': dict(
        pick_if='an East Asian ink painting in pixels: rice paper, mountains in mist, a boat, a lone figure; '
                'a few ink values, empty paper as space, one red accent',
        projection='side', example=None, frames=(None, 12),
        signals=[(6, ['ink wash', 'ink-wash', 'sumi-e', '水墨', '水墨画']),
                 (3, ['ink painting', 'brush painting', 'shan shui', 'rice paper', 'calligraphy', 'seal stamp',
                      '山水', '宣纸', '书法', '印章', '国画']),
                 (2, ['boatman', 'ferry', 'misty river', 'bamboo', 'crane', '渔翁', '渡船', '竹', '鹤'])],
        rules=['A strict ramp of five to seven ink values from paper to dense black; no other colour except one '
               'small red accent (a seal, a lantern).',
               'Empty paper is the space: at least 40% of the frame stays bare paper.',
               'Strokes are pixel brush clusters that taper and break (dry brush), never vector lines or outlines.',
               'Depth is wash: far mountains in the palest tone, near rocks in dense ink; no light, no shadow casting.'],
        tools=['the ink values as a neutral ramp on a warm paper (palette.ramp_between paper to ink)',
               'tapering, broken brush strokes as your own slot maps (artlib.Grid)',
               'mist as bare paper bands between ridges (no fog op)',
               'one red accent: a hand-drawn 6-10 px seal or a small lantern'],
        never=['outlines', 'light ops or glow', 'saturated colour beyond the one accent', 'a filled sky']),
    '1-bit': dict(
        pick_if='a stark two-colour screen: black and one paper white, dither patterns as the only greys, like an '
                'early Mac or a 1-bit indie game; blizzards, night, silhouettes, posters',
        projection='side', example=None, frames=(None, 12),
        signals=[(6, ['1-bit', '1 bit', 'one-bit', 'one bit', '1位', '一位色']),
                 (3, ['two-colour', 'two colour', 'two-color', 'two color', 'black and white only', 'monochrome',
                      'early mac', '双色', '黑白两色', '只有黑白', '单色']),
                 (2, ['blizzard', 'stark', 'woodcut', 'engraving', '暴风雪', '版画'])],
        rules=['Exactly two colours on screen: one black and one paper white (warm or cool), nothing else.',
               'Greys are a small fixed set of hand-chosen dither patterns (five at most: solid, 75%, checker, 25%, '
               'sparse), each with one role; never noise or error-diffusion dither.',
               'Silhouettes carry the read: every key object reads as a solid shape before any pattern.',
               'Light is white space: a lit window is a hole of paper in black, never a halo.'],
        tools=['two-colour slot maps (artlib.Grid with one ink, one paper)',
               'fixed dither patterns per role as tiles (checker 50%, 25% grid, line hatches)',
               'snow and rain as opaque single-pixel sprites on hold tables'],
        never=['a third colour, grey or tint', 'smooth or ordered gradient dither', 'light ops', 'anti-aliasing']),
    'cutaway': dict(
        pick_if='a cross-section of a building, ship, base or station with its front wall removed, rooms full of '
                'tiny people at work, drawn on a strict military (45-degree plan) projection',
        projection='military', example=None, frames=(None, 12),
        signals=[(6, ['cutaway', 'cut-away', 'cross-section', 'cross section', '剖面', '剖视', '剖面图']),
                 (3, ['military projection', 'dollhouse', 'ant farm', 'x-ray view', '军事投影', '娃娃屋', '蚂蚁农场']),
                 (2, ['seabed', 'base', 'station', 'bunker', 'colony', 'submarine', '海底', '基地', '站', '潜艇'])],
        rules=['Military projection only: plan at true shape turned 45 degrees, verticals straight up at 1:1 '
               '(iso military mode); no perspective and no 2:1 iso.',
               'The cut face is one flat colour with a hard edge that frames every room; rooms read as lit boxes.',
               'Every room holds one readable task by tiny figures (10-14 px); no empty rooms.',
               'Light is flat per room with a palette step for the floor and back wall; no light ops.'],
        tools=['military projection blocks and floors (iso, mode "military")',
               'rooms as boxes with a cut face (compose.room, then cut the front wall)',
               'tiny workers as your own slot maps (study references/assets/figures.py lofi)',
               'pipes, cables and ladders that link rooms as 1-2 px runs'],
        never=['perspective or 2:1 iso', 'light ops', 'a room with nobody in it', 'a cut face with texture']),
}

MODES = [
    ('rebuild', 3, ['photo', 'picture of', 'my photo', 'aerial', 'rebuild', 'this image', 'from this',
                    'reference image', 'reference photo',
                    '照片', '这张图', '航拍', '重建']),
    ('era', 3, ['nes', 'game boy', 'gameboy', '8-bit', '8 bit', '16-bit', '16 bit', 'snes', 'genesis', 'mega drive',
                'gba', 'pico-8', 'pico8', '红白机', '8位', '16位', '掌机', '四色绿', '超任', 'famicom',
                'four-shade green', '4-shade green', 'four-colour green', '4-colour green', 'four-color green',
                '4-color green', 'handheld game', 'handheld screen', 'dot-matrix', 'dot matrix', '四色', '绿屏',
                'cga', 'ms-dos', 'dos game', 'early pc']),
    ('assets', 2, ['sprite sheet', 'spritesheet', 'tileset', 'character sheet', 'icons', 'items', 'walk cycle',
                   '精灵表', '图块', '图标', '道具', '行走']),
    ('music', 3, ['soundtrack only', 'just music', 'music loop', 'chiptune', '只要音乐', '配乐']),
]
ERA_WORDS = [('cga', ['cga', 'ms-dos', 'dos game', 'early pc', 'cyan and magenta', '青色和品红', '早期电脑']),
             ('gameboy', ['game boy', 'gameboy', 'gb style', 'dmg', '掌机', '四色绿', 'four shades of green',
                         'four-shade green', '4-shade green', 'four-colour green', '4-colour green',
                         'four-color green', '4-color green', 'handheld game', 'handheld screen', 'dot-matrix', 'dot matrix', '四色', '绿屏']),
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

CAMERA_INTENTS = {
    'one-point perspective': ['one-point perspective', 'one point perspective', '1-point perspective',
                              '1 point perspective', 'single vanishing point', '一点透视'],
    'two-point perspective': ['two-point perspective', 'two point perspective', '2-point perspective',
                              '2 point perspective', 'two vanishing points', '两点透视'],
    '2:1 iso': ['isometric', 'iso ', 'iso-', '等距', '2:1'],
    '3/4 top-down': ['top-down', 'top down', 'from above', 'overhead', 'bird', '俯视', '鸟瞰', '顶视'],
    'side': ['side view', 'side-on', 'side on', 'profile', 'platformer', '侧视', '横版'],
    'oblique': ['oblique projection', 'oblique view', '斜投影'],
    'military': ['military projection', 'military view', '军事投影'],
}


DARK = ['night', 'dark', 'midnight', 'underground', 'cave', '夜', '暗', '深夜', '地下']
BRIGHT = ['day', 'noon', 'sunny', 'morning', 'bright', '白天', '中午', '晴', '早晨', '明亮']
DARK_STYLES = ('contre-jour', 'neon-noir', 'cosy-lightmap', 'tactics', 'native-glow')
BRIGHT_STYLES = ('sticker-iso', 'hd-overworld', 'illustrated', 'pastel-cell')

def _hit(text, w):
    if w.isascii() and w[:1].isalnum():          # English: whole words, so 'nes' is not in 'japanese'
        return re.search(r'(?<![a-z0-9])' + re.escape(w.strip()) + (r'(?:e?s|y)?(?![a-z0-9])' if w[-1:].isalnum() else ''),
                         text) is not None
    return w in text                              # Chinese: substrings

def _hits(text, words):
    return [w for w in words if _hit(text, w)]

def camera_intent(request):
    """-> (stated camera or None, request without explicitly negated camera phrases)."""
    t = ' ' + request.lower().replace('’', "'") + ' '
    positive = set()
    excluded = set()
    negated = []
    for label, phrases in CAMERA_INTENTS.items():
        for phrase in phrases:
            word = phrase.strip()
            pattern = (r'(?<![a-z0-9])' + re.escape(word) +
                       (r'(?:e?s|y)?(?![a-z0-9])' if word[:1].isascii() and word[:1].isalnum() and word[-1:].isalnum() else ''))
            for match in re.finditer(pattern, t):
                if re.match(r'-(?:looking|inspired|like)\b', t[match.end():]):
                    continue
                if re.search(r"\b(?:not|no|without|avoid|don't|do not|instead of|rather than|over)\s+"
                             r'(?:(?:longer|use|using|draw|choose|in|an?|the)\s+){0,3}$', t[:match.start()]):
                    excluded.add(label)
                    negated.append(match.span())
                else:
                    positive.add(label)
    for start, end in reversed(sorted(set(negated))):
        t = t[:start] + ' ' * (end - start) + t[end:]
    positive -= excluded
    return next(iter(positive)) if len(positive) == 1 else None, t, excluded

def route(request, n=3):
    """-> {'picks': [{style, score, why, projection, pick_if, example}], 'mode', 'guide', 'projection'}"""
    t0 = ' ' + request.lower() + ' '
    proj, camera_text, excluded = camera_intent(request)
    t = _no_era(camera_text)                          # 'Game Boy' names an era, not a boy or a game level
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
    if proj:                                         # a stated projection favours the styles drawn in it
        for name in scores:
            if ROUTE[name]['projection'] == proj:
                scores[name][0] += 2
    mode, best = 'scene', 0
    for m, w, words in MODES:
        h = _hits(t0, words)
        if h and w * len(h) > best:
            mode, best = m, w * len(h)
    if mode == 'era':                                # console limits: no light layer on top
        for name in scores:
            if styles.get(name)['res'] != 'none':
                scores[name][0] -= 3
    order = sorted(scores, key=lambda k: (-scores[k][0], list(ROUTE).index(k)))
    camera = proj or ('inspect reference' if mode == 'rebuild' else None)
    def pick_camera(style):
        default = ROUTE[style]['projection']
        return camera or ('choose camera' if default in excluded else default)
    picks = []
    for name in order[:n]:
        s, why = scores[name]
        r = ROUTE[name]
        picks.append(dict(style=name, score=s, why=why or ['no signal in the request'],
                          projection=pick_camera(name), pick_if=r['pick_if'], example=r['example']))
    if picks[0]['score'] <= 0:                       # nothing matched: the toolkit's own look first
        lofi = next((p for p in picks if p['style'] == 'lofi'), None)
        if lofi is None:
            r = ROUTE['lofi']
            lofi = dict(style='lofi', score=0, why=['no strong signal: the default for a calm scene'],
                        projection=pick_camera('lofi'), pick_if=r['pick_if'], example=r['example'])
        picks = [lofi] + [p for p in picks if p['style'] != 'lofi'][:n - 1]
    if mode != 'scene' and picks[0]['score'] <= 0:
        picks[0]['why'] = ['no style signal: follow %s first; pick the finish style from the %s' % (
            GUIDE[mode], {'rebuild': "photo's light and subject", 'era': "console's limits",
                          'assets': 'game the assets are for', 'music': 'scene the music goes with'}[mode])]
    return dict(request=request, picks=picks, mode=mode, guide=GUIDE[mode], projection=proj,
                excluded_cameras=[label for label in CAMERA_INTENTS if label in excluded],
                era=era_of(request) if mode == 'era' else None)

class IntakePlan(TypedDict):
    disposition: Literal['offer', 'direct']
    questions: list[str]
    route: dict


_GENERIC_SCENE_EN = re.compile(
    r'(?:(?:please\s+)?(?:make|create|draw)(?:\s+me)?|i\s+want)\s+(?:a\s+)?'
    r'(?:pixel(?:[- ]art)?\s+scene|pixel\s+art|pixel\s+scene)(?:\s+for\s+me)?[.!?]?',
    re.IGNORECASE,
)
_GENERIC_SCENE_ZH = re.compile(
    r'(?:我想要|(?:请)?(?:帮我)?(?:做|画|制作|创作|生成))(?:一[张幅个])?'
    r'(?:像素(?:画|场景|艺术)|像素风(?:格)?(?:的)?(?:画|场景|图片))(?:吧|好吗|可以吗)?[。！？!?]?'
)


def intake_plan(request: str) -> IntakePlan:
    """Offer optional questions only when the entire request is a generic scene ask."""
    text = request.strip()
    if _GENERIC_SCENE_ZH.fullmatch(text):
        questions = [
            '你想画什么场景？比如小岛、集市，或用自己的话描述；也可以跳过。',
            '想要什么视觉方向或用途？比如温馨夜景循环、明亮的游戏背景，或用自己的话描述；也可以跳过。',
        ]
    elif _GENERIC_SCENE_EN.fullmatch(text):
        questions = [
            'What should the scene show? For example, an island, a market, or anything in your own words. You can skip this.',
            'What visual direction or use do you want? For example, a cozy night loop, a bright game backdrop, or your own words. You can skip this.',
        ]
    else:
        questions = []
    return {'disposition': 'offer' if questions else 'direct', 'questions': questions, 'route': route(request)}


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
        ('a flat winter sky in undithered bands (sky.strata)', 'nodither'),
        ('snow as baked engine tables (study references/assets/particles.py snow)', 'lofi')]),
    (['fog', 'mist', 'haze', '雾', '霭'], 'fog', [
        'fog as haze per depth plane, each plane pulled toward the fog colour (palette.haze, palette.haze_levels)',
        ('a fog layer over the planes (Post.fog)', 'post:fog'),
        'drifting banks that wrap seamlessly (anim.wrap_offset, or canvas.loop_dissolve in lofi only)']),
    (['sea', 'ocean', 'lake', 'river', 'stream', 'harbour', 'harbor', 'port', 'coast', 'beach', 'waterfall', 'pond',
      'canal', 'boat', 'ship', 'dock', 'pier', '海', '湖', '河', '溪', '港', '海岸', '沙滩', '瀑布', '池塘', '运河', '船',
      '码头', 'island', 'islands', 'islet', 'isle', '岛', '小岛', '海岛'], 'water', [
        'sea in hard bands by distance from land, boats and fenders passed as floating= so they make no islands (water.depth_bands)',
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
        ('flat undithered strata locked by wisps and streaks (sky.strata, sky.wisp, sky.smile, sky.streaks)', 'nodither'),
        ('sky as Bayer-dithered bands between ramp steps, 10-16 rows per transition (canvas.Canvas.bands)', 'bayer'),
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
        ('planks, bricks and shingles laid along an iso wall face, courses on the 2:1 slope (texture.iso_face)', 'iso'),
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
    (['sun ray', 'sunray', 'sunbeam', 'god ray', 'light shaft', 'shaft of light', 'shaft', 'beam', 'ray',
      'spotlight', 'searchlight', 'pillar of light', '光柱', '光束', '丁达尔', '探照灯', '耶稣光'], 'light beams', [
        ('soft angled shafts on the light layer, angle 90 points down (post.Post.shaft)', 'post:shaft'),
        ('a hard-edged angled ray in palette slots: a stepped band filled one ramp step lighter, no blend '
         '(shapes.ray, canvas.Canvas.fill)', '!post:shaft'),
        'what the beam crosses steps up one slot: rain, flakes, wave crests inside the ray mask (shapes.ray as the mask)',
        'a sweeping beam (a lighthouse, a searchlight): the angle stepped per frame on a hold table whose period '
        'divides the loop (shapes.ray, anim.hold)',
        ('one big beam breaks the highlight budget: gate it with `--scene beam`', 'style:contre-jour')]),
    (['lamp', 'lantern', 'candle', 'torch', 'window', 'fireplace', 'neon sign', '灯', '灯笼', '蜡烛', '火把', '窗',
      '壁炉'], 'small lights', [
        'lamps and lanterns as slot maps in warm slots (study references/assets/props.py lantern)',
        'flicker on held steps, passing t % T so the seam holds (light.flicker), and lamp-side rims (light.rim)',
        'marquee and signal lights (anim.chase)',
        ('multiplied pools, walls blocking light with occlude= (occlude_soft=2 so thin strips only dim it) and per-light flicker in the light tuple (Post.lightmap)',
         'post:lightmap'),
        ('shaped pools (Post.light)', 'post:light'), ('glow from an emitter mask (Post.glow)', 'post:glow'),
        ('pools drawn in palette steps (light.Light.point, light.Light.apply)', 'strict')]),
    (['crowd', 'people', 'busy', 'traffic', 'market', 'festival', 'car', 'cars', '人群', '热闹', '车', '集市', '夜市',
      '庙会'], 'crowds', [
        ('traffic and crowds placed on lanes, drawn by your own car= and person= functions (compose.populate, compose.vignette)', 'iso'),
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
    (['star', 'stars', 'starfield', 'starry', 'night sky', 'milky way', 'constellation', '星', '星空', '银河'],
     'night sky', [
        'stars hand-placed in clusters, never an even scatter: 1 px flecks in 2-3 tones, only a handful at the '
        'brightest (texture.speckle inside a hand-drawn mask, or a hand-typed point list)',
        'a few stars twinkle between two tones on holds whose periods divide the loop; the rest stay still '
        '(texture.jitter_dots with t and T, anim.hold)',
        'a milky way as a curved band of denser, dimmer flecks, never a blur (texture.speckle in a curved mask)',
        ('the sky behind in flat undithered strata (sky.strata)', 'nodither'),
        ('the sky behind in Bayer bands, 10-16 rows per transition (canvas.Canvas.bands)', 'bayer'),
        ('a small glow on the brightest few from their mask (post.Post.glow)', 'post:glow')]),
    (['stairs', 'stair', 'staircase', 'steps', 'stone steps', 'stairway', 'terrace', 'terraces', '台阶', '石阶', '楼梯',
      '阶梯'], 'stairs and steps', [
        'each step a slot map: a lit tread, a riser one step darker, a 1 px nosing, 2-6 px of rise at native size '
        '(canvas.Canvas.rect, canvas.Canvas.hline)',
        'stone steps as carved cells with a lit rim and wear (layout.ashlar, texture.shade_cells)',
        'switchbacks: each flight a separate diagonal with a landing at the turn, so the zig-zag reads at 1x',
        'figures on stairs snap to step tops: a stepped bob, never a smooth slope',
        'a stair down into the dark (study references/assets/props.py stairwell)',
        ('iso steps as boxes one tread deep each (iso.Iso.box), or a stepped block (iso.Iso.pyramid)', 'iso')]),
    (['procession', 'pilgrim', 'pilgrims', 'parade', 'march', 'marching', 'caravan', 'single file', 'in line',
      '队列', '队伍', '游行', '朝圣', '行进'], 'procession', [
        'the path as a polyline in native px, walkers at whole-pixel points along it by distance; a repeating unit '
        'of 3-5 different walkers so the line is not a row of clones',
        'loop arithmetic: the unit repeats every P px of path and moves a whole number of P per loop (speed x loop '
        '= k x P), so frame T is frame 0; walk cycles on holds whose periods divide the loop (anim.hold, '
        'anim.check_periods)',
        'the line enters and leaves behind something (a near rock, a door) so the lap seam is hidden',
        'carried lights move with their bearer and flicker on the loop (light.flicker passing t % T)',
        ('a pool per carried lantern on the light layer (post.Post.light)', 'post:light'),
        ('a pool per carried lantern in palette steps (light.Light.point, light.Light.apply)', 'strict'),
        ('walkers on lanes in world units, your own figure passed as person= (anim.lane_offset, compose.populate walks)', 'iso')]),
    (['steam', 'steaming', 'vapour', 'vapor', 'smoke', 'chimney', 'kettle', 'hot spring', 'breath', '蒸汽', '热气',
      '水汽', '冒烟', '炊烟', '温泉'], 'steam and smoke', [
        'steam and smoke as hand-shaped plume sprites with a few drawings that rise and thin, never dotted squares '
        '(fx.smoke_puff, fx.trail)',
        'a curling column: 3-5 puffs spawned on a period that divides the loop, each rising with a stepped sway '
        '(anim.age, anim.stepped_sin)',
        ('steam as opaque light slots that step up a slot where it crosses a lamp mask', 'strict'),
        ('soft rising specks in a lamp pool (post.Post.motes)', 'post:motes'),
        ('a faint glow where the steam crosses a light (post.Post.glow)', 'post:glow')]),
    (['door', 'doorway', 'door opens', 'open door', 'light spills', 'spill', 'spills', '门', '门口', '门缝', '开门'],
     'door light spill', [
        'the spill is a wedge on the ground from the door frame outward, its edges set by the frame '
        '(canvas.Canvas.mask_poly for the wedge)',
        'the door opening as 3-6 held drawings; the wedge widens with the leaf (anim.Timeline)',
        'a figure in the doorway casts a long shadow down the wedge: cut it out of the light',
        ('a lamp inside the room with the wall, the door leaf and anyone in the doorway as the occluder, so the '
         'wedge and the long shadow come out of the light (post.Post.lightmap with occlude=); a moving occluder '
         'is a new mask each frame, so keep it to a few held drawings and they cache', 'post:lightmap'),
        ('a pool masked to the doorway (post.Post.light with mask= and behind=)', 'post:light'),
        ('the wedge in palette steps: the ground one or two ramp steps lighter inside it (light.Light.cone, '
         'light.Light.levels, light.Light.apply)', 'strict')]),
    (['lighthouse', 'beacon', '灯塔'], 'lighthouse', [
        'the tower as a slot map: a tapered body with stripes or courses, a gallery rail, the lamp room with glazing '
        'bars (canvas.Canvas.poly, canvas.Canvas.outline)',
        'the beam: the light beams topic (`pixelate tools beam`); a sweeping beam steps its angle per frame on a hold '
        'table whose period divides the loop (shapes.ray, anim.hold)',
        'what the beam crosses (rain, wave crests, a boat) steps up one slot inside the ray mask, only on the frames '
        'it passes',
        'the lamp turned at the viewer: one or two frames with the lamp room at the top slot',
        ('a round tower as unit slices (iso.Iso.cylinder)', 'iso'),
        ('a halo round the lamp room (post.Post.glow)', 'post:glow')]),
    (['lightning', 'thunder', 'thunderstorm', 'bolt', '闪电', '雷', '雷暴', '暴风雨'], 'lightning', [
        'the bolt as a jagged polyline 1-2 px wide with a branch or two, on screen for one or two frames '
        '(canvas.Canvas.line)',
        'the flash: swap to a lifted palette for exactly those frames (palette.flash), or step every ramp up under '
        'a mask (fx.hit_flash)',
        'near forms drop to their darkest slot against the lifted sky: a silhouette for the flash frames',
        'timing: one strike (or two) per loop with a 1-frame pre-flash and a 2-3 frame decay (anim.pulse)',
        ('the strike lighting the ground in palette steps along a line (light.Light.segment, light.Light.apply)',
         'strict'),
        ('a glow from the bolt mask for the strike frames (post.Post.glow)', 'post:glow')]),
    (['wave', 'waves', 'surf', 'breaker', 'breakers', 'swell', 'crest', 'crests', 'spray', '浪', '海浪', '浪花'],
     'waves and surf', [
        'the sea in hard bands by distance, darker toward the viewer (water.depth_bands)',
        'crests as short light dashes in rows that move a whole tile per loop (texture.flecks, anim.wrap_offset)',
        'foam where water meets rock or hull, pulsing on the loop (water.foam_rings with t and T)',
        'a breaking wave as 3-6 held drawings (swell, curl, crash, wash), spray on impact as hard cells '
        '(anim.Timeline, fx.burst)',
        'boats ride the swell on a stepped bob of 1 px, on a period that divides the loop (anim.stepped_sin)']),
    (['rotate', 'rotating', 'rotates', 'turns', 'turning', 'spins', 'spinning', 'swing bridge', 'swings open',
      'turntable', 'revolving', 'windmill', '旋转', '转动', '转开', '风车'], 'turning objects', [
        'a turning thing (a swing bridge, a turntable, a windmill) is a few key drawings, 4-8 for a quarter turn, '
        'held on a timeline with a longer hold at each end and a 1 px settle when it locks (anim.Timeline)',
        'keep it rigid across drawings: the same plank count, posts and rails in every key, only the angle changes; '
        'fix the jaggies by hand at the in-between angles',
        ('the box tools are axis-aligned: project the object\'s world corners per key angle (iso.Iso.to_screen) and '
         'fill the polygon yourself (canvas.Canvas.poly, canvas.Canvas.outline); the 0 and 90 degree keys can be '
         'boxes (iso.Iso.box). Units: +1 x is 2 px right and 1 px down, +1 z is 1 px up', 'iso'),
        ('project the corners per key angle yourself and fill the polygon (canvas.Canvas.poly, canvas.Canvas.outline)',
         '!iso')]),
    (['released', 'release', 'queue', 'queues', 'in rows', 'rank by rank', 'level crossing', 'gate opens',
      'rush hour', '放行', '排队', '人潮', '涌过', '一排排'], 'crowds released in rows', [
        'queues as rows of walkers held at a line, released front to back one rank every few frames (anim.cascade '
        'for the stagger)',
        'every walker\'s path (arrive, wait, cross, leave) closes over the loop, so frame T is frame 0',
        ('lanes that stop and go on a schedule of (frames, speed) segments covering the loop, a whole number of '
         'laps in all (anim.lane_offset, compose.populate with schedule=)', 'iso'),
        ('density per window stays readable while they bunch (compose.check_density)', 'iso')]),
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
           ('judge', 'the defects the gate passes, located with a fix: masonry, repeated units, scallops, outline loops, murky values'),
           ('recipes', 'composed generators that work on the first try: Perspective, rock_face, pouring_fall, cloud_bank, crowd_vignettes'),
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
    """guides/toolkit.md: a short index of the kit that says how to query it. The kit itself is read
    from the source on demand by `pixelate tools` (tools/kit.py). Regenerate with --catalog."""
    L = ['# Toolkit', '',
         'An index of the kit. The detail is served from the source on demand, so read only what the',
         'step needs. Generated by `python3 tools/route.py --catalog`; regenerate it after adding a module.', '',
         '## How to query', '', '```',
         'pixelate tools                      every topic and module, one line each',
         'pixelate tools TOPIC [--style S]    the techniques for a subject: rain, 雨, fog, water, lamp ...',
         'pixelate tools MODULE               a module\'s functions and classes: signature, first doc line',
         'pixelate tools MODULE.func          the full signature and docstring (MODULE.Class.method too)',
         'pixelate style NAME                 one style\'s rules, light, budgets, craft limits, techniques',
         '```', '',
         'The same queries exist as MCP tools: `kit_tools(query)` and `style_card(name)`. The router only',
         'suggests the techniques its keywords know about; the best brief uses whatever the scene needs.', '',
         '## Topics', '',
         ', '.join(label for _, label, _ in TOPIC_TOOLS) + '.', '',
         '## Modules', '']
    L += ['- `%s`: %s' % (m, w) for m, w in CATALOG]
    L += ['', 'The other tools/*.py (`sdf` for curved solids, `colorlib`, the pipeline scripts) are listed by '
          '`pixelate tools` with their docstrings.']
    L += ['', '## Examples in references/assets', '',
          'Read them to see how a finished thing was built, never call them.', '']
    L += ['- `%s`: %s' % (m, w) for m, w in EXAMPLES]
    L += ['', '## Always', '', ALWAYS_TOOLS[0].upper() + ALWAYS_TOOLS[1:] + '.']
    return '\n'.join(L) + '\n'

def _fits(cond, style, projection):
    if cond.startswith('!'):
        return not _fits(cond[1:], style, projection)
    if cond.startswith('style:'):
        return styles.get(style)['name'] == cond[6:]
    st = styles.get(style)
    if cond in ('iso', 'topdown', 'side'):
        return {'iso': '2:1 iso', 'topdown': '3/4 top-down', 'side': 'side'}[cond] == projection
    if cond == 'lofi':
        return style == 'lofi'
    if cond == 'soft':
        return st['res'] != 'none'
    if cond == 'strict':
        return st['res'] == 'none'
    if cond == 'nodither':
        return not st['dither']
    if cond == 'bayer':
        return 'bayer4' in st['dither']
    if cond.startswith('post:'):
        return styles.allows(style, cond[5:])
    return True

def topic_tools(request, style=None, projection=None):
    """-> ['label: call, call, ...'] for the subjects the request names, filtered to what the style
    and projection allow (a banned light op or an iso-only prop is left out); console-era phrases
    ('Game Boy', '8-bit') are taken out first"""
    t = _no_era(' ' + request.lower() + ' ')
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
          'fog', 'foggy', 'mist', 'storm', 'winter', 'summer', 'spring', 'autumn',
          '夜', '黄昏', '清晨', '日落', '日出', '中午', '早晨', '傍晚', '白天', '雨', '雪', '雾', '风暴', '冬', '夏', '春', '秋'],
    phases=['seasons', 'four seasons', 'day to night', 'day and night', 'cycle', 'phases', 'timelapse',
            '四季', '昼夜', '日夜', '循环', '轮换'],
    figures=['person', 'people', 'character', 'hero', 'girl', 'boy', 'man', 'woman', 'kid', 'crowd', 'cat', 'dog',
             'bird', 'animal', 'knight', 'villager', '人', '角色', '主角', '女孩', '男孩', '人群', '猫', '狗', '鸟', '动物'],
    purpose=['wallpaper', 'cover', 'thumbnail', 'banner', 'video', 'gif', 'loop', 'stream', 'key art', 'poster',
             'readme', 'showcase', '壁纸', '封面', '缩略图', '横幅', '视频', '动图', '循环', '直播', '海报', '展示'],
    music=['music', 'soundtrack', 'lofi', 'lo-fi', 'chiptune', 'song', 'audio', '音乐', '配乐', '歌'],
)

# what the style looks like when the request says nothing: (time, light bucket, weather, light)
TIME_DEFAULT = {
    'lofi': ('late evening', 'night', '', 'lit windows and a lantern against a gradient sky'),
    'pastel-cell': ('a bright day', 'day', 'windy, high clouds', 'one hue window over sky and land'),
    'native-glow': ('dusk', 'dusk', '', 'a low cold sun, glowing sigils and water'),
    'hd-overworld': ('late morning', 'day', 'clear', 'clear water, soft cloud shadows'),
    'arcade': ('day', 'day', 'overcast', 'smoke and fire as the warm accents'),
    'tactics': ('night', 'night', 'storm', 'the board lit by fire and impacts'),
    'sticker-iso': ('midday', 'day', 'clear', 'flat bright light, no cast shadows'),
    'illustrated': ('golden hour', 'dusk', 'big clouds', 'a long view'),
    'neon-noir': ('midnight', 'night', 'rain', 'neon signs as the only colour'),
    'cosy-lightmap': ('night', 'night', 'rain', 'many warm windows and lamps pooling light in the dark'),
    'contre-jour': ('night', 'night', 'fog', 'one strong backlight behind the subject'),
}
# the request's own words come first: (words, phrase, bucket); the first hit in each list wins
TIME_WORDS = [(['midnight', '午夜', '深夜'], 'midnight', 'night'), (['night', 'nightfall', '夜'], 'night', 'night'),
              (['sunset', 'dusk', 'evening', 'twilight', 'golden hour', '黄昏', '日落', '傍晚', '晚霞'], 'dusk', 'dusk'),
              (['sunrise', 'dawn', '日出', '黎明', '朝霞'], 'dawn', 'dawn'),
              (['noon', 'midday', '正午', '中午'], 'noon', 'day'),
              (['morning', 'early morning', '清晨', '早晨', '上午'], 'morning', 'dawn'),
              (['afternoon', 'day', 'daytime', 'sunny', '下午', '白天', '晴'], 'day', 'day')]
WEATHER_WORDS = [(['storm', 'stormy', 'thunderstorm', 'thunder', 'lightning', 'gale', '暴风雨', '暴风', '风暴', '雷', '闪电'],
                  'storm: wind-driven rain, spray, a churning sky'),
                 (['snow', 'snowy', 'snowing', 'blizzard', 'snowfall', '雪'],
                  'snow falling, snow lying on every up-facing surface'),
                 (['rain', 'rainy', 'raining', 'drizzle', '雨'], 'rain'),
                 (['fog', 'foggy', 'mist', 'misty', 'haze', '雾', '霭'], 'fog'),
                 (['clear', 'cloudless', 'starry', '晴朗', '星空'], 'clear')]
PRECIP = ('rain', 'storm', 'snow')
ASKED_ONLY = PRECIP + ('fog',)     # weather a default never adds once the request names its time
BUCKET_LIGHT = {'night': "the scene's own lights (windows, lamps, the subject) are the only light",
                'dusk': 'a low sun or its afterglow, the first lamps lit',
                'dawn': 'low, cool early light',
                'day': 'high sun, bright and even'}

UNDERGROUND = ['mine', 'cave', 'underground', 'dungeon', 'tunnel', 'sewer', 'crypt', '矿', '洞', '地下', '地牢',
               '隧道', '下水道']
INTERIOR = ['interior', 'inside', 'indoor', 'indoors', '室内', '屋内', '里面']   # always indoors
ROOMS = ['bedroom', 'kitchen', 'living room', 'classroom', 'attic', '房间', '卧室', '厨房']
# a bare 'room' only with an owner or a room adjective: 'clear room around it' and 'the lantern room' stay outside
ROOM = re.compile(r'\b(?:a|the|my|his|her|their|our|cosy|cozy|small|tiny|little|empty|quiet|dark|messy|study|'
                  r'reading|dining|throne|music|hotel)\s+room\b')
PLACES = ['cafe', 'coffee shop', 'shop', 'library', 'tavern', 'inn', 'restaurant', 'bakery', 'studio',
          '咖啡', '店', '馆', '图书馆', '酒馆', '客栈']   # a building: inside unless the request is outdoors
OUTDOOR = ['outdoor', 'outdoors', 'outside', 'exterior', 'street', 'road', 'square', 'plaza', 'garden', 'yard',
           'rooftop', 'from above', 'seen from above', 'lane', 'alley', 'harbour', 'harbor', 'market',
           '室外', '户外', '屋外', '街', '路', '广场', '院子', '屋顶', '从上往下', 'sky']
# an outdoor subject: outside even when a room word shows up (the lighthouse's lantern room)
OUTDOOR_SUBJECTS = ['canal', 'market', 'harbour', 'harbor', 'lighthouse', 'street', 'sea', 'ocean', 'island',
                    'bridge', 'beach', 'coast', 'shore', 'headland', 'cliff', 'river', 'lake', 'mountain', 'forest',
                    'field', 'meadow', 'pier', 'dock', 'port', '运河', '市场', '集市', '港', '灯塔', '大海', '海边',
                    '海上', '岛', '桥', '河', '湖', '山', '森林']

def _strip(t, words):
    """t with every whole-word (English) or substring (Chinese) hit of words blanked out"""
    for w in sorted(words, key=len, reverse=True):
        if w.isascii() and w[:1].isalnum():
            t = re.sub(r'(?<![a-z0-9])' + re.escape(w.strip()) + (r'(?:e?s|y)?(?![a-z0-9])' if w[-1:].isalnum() else ''),
                       ' ', t)
        else:
            t = t.replace(w, ' ')
    return t

def _no_era(t):
    """the request with its console-era phrases removed, so 'Game Boy' is neither a boy nor a game level"""
    return _strip(t, [w for _, ws in ERA_WORDS for w in ws] + MODES[1][2])

def time_weather(request, style):
    """-> (text, stated): the time and weather line. The request's own words come first (night, storm,
    snow, noon, indoors, a street); the style's default fills only what the request leaves open, and
    never adds rain, snow, a storm or fog the request did not ask for once it names a time (a
    midnight observatory is a clear night unless the request says mist)."""
    t = _no_era(' ' + request.lower() + ' ')
    st = styles.get(style)['name']
    d_time, d_bucket, d_weather, d_light = TIME_DEFAULT.get(st, ('late afternoon', 'day', 'clear', 'a low warm sun'))
    when = next(((ph, b, h) for ws, ph, b in TIME_WORDS for h in [_hits(t, ws)] if h), None)
    sky = next(((ph, h) for ws, ph in WEATHER_WORDS for h in [_hits(t, ws)] if h), None)
    stated = [x for x in ((when[2][0] if when else None), (sky[1][0] if sky else None)) if x]
    under = _hits(t, UNDERGROUND)
    if under:
        return ('underground, no sky: the lamps are the only light, and one shaft or opening shows the world above',
                '/'.join(under[:2]))
    if not when and not sky:
        time, bucket, weather, light = d_time, d_bucket, d_weather, d_light
    else:
        time, bucket = (when[0], when[1]) if when else (d_time, d_bucket)
        weather = sky[0] if sky else ('' if d_weather.split(':')[0] in ASKED_ONLY else d_weather)
        light = d_light if bucket == d_bucket else BUCKET_LIGHT[bucket]
    subject = _hits(t, OUTDOOR_SUBJECTS)
    inside = _hits(t, INTERIOR) or ([] if subject else _hits(t, ROOMS) + ROOM.findall(t))
    place = _hits(t, PLACES)
    outdoors = subject or _hits(t, OUTDOOR) or (sky and sky[0].split(':')[0] in PRECIP)
    if inside or (place and not outdoors):
        return ('indoors%s: the room lit by its own lamps and one window showing %s outside' % (
            (' at ' + time if time in ('night', 'midnight', 'dusk', 'dawn', 'noon') else ', ' + time) if when else '',
            ('the ' + weather.split(':')[0]) if weather and weather != 'clear' else 'the weather'),
            '/'.join((inside or place)[:1] + stated))
    text = ', '.join(x for x in (time, weather) if x) + '; ' + light
    if place and bucket in ('night', 'dusk'):
        text += "; seen from outside, the building's windows and door spill light onto the ground"
    return text, '/'.join(stated + (outdoors[:1] if place and isinstance(outdoors, list) else []))

SILENT = ['silent', 'no music', 'no sound', 'without music', 'without sound', 'mute', 'muted', 'no audio',
          '无声', '静音', '不要音乐', '没有音乐', '不要声音']
# an era piece plays on the console's own sound chip
ERA_VOICES = {'gameboy': 'two pulse voices, one wave and one noise (the handheld\'s four channels)',
              'nes': 'two pulse voices, a triangle bass and one noise',
              'snes': 'up to eight sampled voices with the chip\'s echo',
              'genesis': 'six FM voices with three square voices and one noise',
              'gba': 'two pulses, a wave and a noise plus two sample channels',
              'pico-8': 'four channels from its eight built-in waveforms',
              'neogeo': 'FM voices, three square voices and sampled drums',
              'cga': 'the PC speaker: one square voice, chords as fast arpeggios, drums as short noise clicks'}
SOUND_BEDS = [(['storm', 'thunder', 'lightning', '暴风', '风暴', '雷'], 'rain and thunder'),
              (['rain', 'drizzle', '雨'], 'rain'), (['snow', 'snowy', '雪'], 'a snowy hush'),
              (['sea', 'ocean', 'wave', 'waves', 'harbour', 'harbor', '海', '浪'], 'the sea'),
              (['wind', 'windy', '风'], 'wind')]

def music_line(request, style, era=None):
    """the Music line for a scene brief: the style's direction (styles.STYLES[..]['music']), the console's
    chip voices for an era piece, a sound bed from the request's weather; 'none' only when the request asks
    for silence. Direction only: the agent writes the track, `pixelate check TRACK.wav` judges it."""
    t = _no_era(' ' + (request or '').lower() + ' ')
    hush = _hits(' ' + (request or '').lower() + ' ', SILENT)
    if hush:
        return 'none: the request asks for %s' % hush[0]
    m = styles.get(style)['music']
    bed = next((b for ws, b in SOUND_BEDS if _hits(t, ws)), None)
    if era:
        import era as eramod
        voices = 'chiptune on the %s chip only: %s' % (eramod.ERAS[era]['name'], ERA_VOICES[era])
        feel, sync, check = ('a short tune in the console\'s idiom, simple triads, its metre, mode and tempo '
                             'from the scene\'s mood', 'an arpeggio or a noise hit on the loop\'s main event '
                             '(a beam sweeping past, a wave breaking)', 'chiptune')
        bed = bed and '%s on the noise channel' % bed
    else:
        voices, feel, sync, check = m['voices'], m['feel'], m['sync'], m['check']
    return ('%s; %s%s; sync point: %s. Direction only: write the track in code (guides/music.md); '
            '`pixelate check TRACK.wav --style %s` judges it' % (
                voices, feel, ('; under a bed of %s' % bed) if bed else '', sync, check))

def loop_default(style):
    """the loop line for a non-lofi style: the length comes from the story beats, the style's default
    only when nothing in the scene needs longer"""
    st = styles.get(style)
    frames = ROUTE[st['name']]['frames'][0]
    return ('a seamless loop at %d fps, its length set by the story beats: the longest action (a crossing, a lap '
            'of the procession, a door opening and closing) rounded up to a length every period divides%s' % (
                st['fps'], (' (%d frames when nothing needs longer)' % frames) if frames else ''))

def gaps(request, r=None, delivered=None, native_h=None):
    """-> [{topic, stated, default}]: each open choice in the request and the default it takes for the
    top style. Fill the brief with the defaults, then list them for the user to confirm or change."""
    r = r or route(request)
    t = _no_era(' ' + request.lower() + ' ')
    p = r['picks'][0]
    st = styles.get(p['style'])
    out = []
    def add(topic, words, default):
        h = _hits(t, words) if words else []
        out.append(dict(topic=topic, stated='/'.join(h[:3]) if h else '', default=default))
    margin = p['score'] - (r['picks'][1]['score'] if len(r['picks']) > 1 else 0)
    camera_override = p['projection'] in ('one-point perspective', 'two-point perspective',
                                           'inspect reference', 'choose camera')
    out.append(dict(topic='style', stated='/'.join(p['why'][:2]) if p['score'] > 3 and margin >= 3 else '',
                    default='`%s` (%s); the runners-up are %s%s' % (
                        st['name'], st['what'], ', '.join('`%s`' % q['style'] for q in r['picks'][1:]),
                        '; this style sets the finish, not the camera' if camera_override else '')))
    out.append(dict(topic='projection', stated=r['projection'] or '', default=(
        'inspect the reference camera before choosing a projection' if p['projection'] == 'inspect reference'
        else 'choose a camera other than %s' % ', '.join(r['excluded_cameras'])
        if p['projection'] == 'choose camera' else p['projection'])))
    tw, said = time_weather(request, st['name'])
    out.append(dict(topic='time and weather', stated=said, default=tw))
    add('phases', WORDS['phases'],
        'one phase; for a long stream cover, a cycle of 3-4 phases each with its own signature elements '
        '(not Lantern Isle\'s four seasons again unless asked)' if st['name'] == 'lofi'
        else 'one phase, no cycle')
    named = _hits(t, WORDS['figures'] + ['slime', 'robot', 'samurai', '史莱姆', '武士', '机器人'])
    add('figures', WORDS['figures'],
        'only the actors the request names, nobody added' if named else
        'one or two small figures doing a quiet, specific task (%s)' % (
            _as_example(figure_size(st, native_h)[0]).replace('iso people', 'figures sized for the camera')
            if camera_override else _as_example(figure_size(st, native_h)[0])))
    loop = ('the engine\'s 30-tick clock, sprites at 10, 5 or 2 fps; the loop is the music\'s length'
            if st['name'] == 'lofi' else loop_default(st['name']))
    excerpt = 'a GIF excerpt' if st['res'] == 'none' else 'an APNG excerpt (a GIF bands soft light)'
    add('purpose and outputs', WORDS['purpose'],
        'a gallery showcase: %s, as %s MP4, %s and a still' % (
            loop, ('a %dx%d' % delivered) if delivered else '1080p', excerpt))
    if r.get('era'):
        import era as eramod
        e = eramod.ERAS[r['era']]
        out.append(dict(topic='era limits', stated=r['era'], default='%s: %dx%d, at most %d colours%s%s; no light '
                        'layer; check with `pixelate era IMG --era %s`' % (
                            e['name'], e['size'][0], e['size'][1], e['max_colors'],
                            (', palette %s' % e['palette']) if e.get('palette') else '',
                            (', %d colours per %dx%d block' % (e['block_colors'], e['block'], e['block']))
                            if e.get('block') else '', r['era'])))
    add('music', WORDS['music'] + SILENT, music_line(request, st['name'], r.get('era')))
    return out

def gaps_md(g):
    L = ['## 0. Choices to confirm', '',
         'Defaults I picked where the request was open. Say OK to build as written, or change any line.', '',
         '- **intent**: TODO one line on what the user most likely wants but did not say (the feeling, the use, '
         'the era or game it recalls, what would disappoint them; see references/brief.md#read-the-intent); '
         'every choice below follows from it']
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
        n = len(re.findall(r'^\s*[-*]\s+\S', b, flags=re.M)) + len(_table_rows(b))   # nested items and table rows count
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
                r'(?:once|one \w+) (?:every|per) (\d+)\s+frames', r'period(?: of)?\s+(\d+)' + NOT_FRAMES]
        for pat in pats:
            for k in re.findall(pat, m):
                if int(k) and T % int(k):
                    probs.append('Motion table: a period of %s frames does not divide the %d-frame loop' % (k, T))
        for n, k in re.findall(r'(\d+)\s+drawings?,?\s+(\d+)\s+frames? each', m):
            if int(n) * int(k) and T % (int(n) * int(k)):
                probs.append('Motion table: %s drawings x %s frames = %d does not divide the %d-frame loop' % (
                    n, k, int(n) * int(k), T))
    if m is not None:
        slow = [b for b in _bullets(m) if not re.match(r'(todo|checks?|motion|note|keep|at most|only)\b', b, re.I)
                and not b.endswith(':') and not re.search(RATE, b, re.I)]
        if slow:
            probs.append('Motion table: %d line(s) with no rate or frame count: %s' % (len(slow), _quote(slow)))
    probs += _music(text)
    li = find('Light list')
    soft = _has_light_layer(text)
    if li is not None and not re.search(r'\d', li) and (soft or not re.search(PALETTE_STEP, li, re.I)):
        probs.append('Light list has no sizes or radii: give every emitter a colour, a radius and what hides it'
                     if soft else 'Light list says nothing concrete: name the slots each light steps up and the '
                     'shape or size of its pool')
    sl = find('Style and light regime')
    if sl is not None:
        if not re.search(r'\b(none|native|screen)\b|no light layer', sl):
            probs.append('Style and light regime does not name the light layer (none, native or screen)')
        if not re.search(r'budget|L\s*[<>]|below L|above L', text):
            probs.append('no value budget anywhere (how much of the frame is dark, how rare the highlights are)')
    hides_flagged = False
    if soft and li is not None and not re.search(r'hide|hidden|occlud|block|behind', li.lower()):
        probs.append('Light list never says what hides a light: write "hidden by", "blocked by" or "behind" and '
                     'the near plane, a wall or a door frame')
        hides_flagged = True
    if li is not None and soft:
        lights = [b for b in _bullets(li) if not re.match(NOT_A_LIGHT, b.lstrip('*'), re.I)
                  and not re.search(r'\bunlit\b|no light of its own|not a light|no pool', b, re.I)]
        for what, pat in (('no colour', COLOUR), ('no radius or size', RADIUS)) + (
                () if hides_flagged else (('nothing that hides it', HIDES),)):
            miss = [b for b in lights if not re.search(pat, b, re.I)]
            if miss:
                probs.append('Light list: %d light(s) with %s: %s (%s)' % (len(miss), what, _quote(miss), FIX[what]))
                if not any('not a light' in x for x in probs):
                    probs[-1] += '; a line that is not a light starts with "ambient", "no " or "per-light", ' \
                                 'or says "not a light"'
    sc = find('The scene')
    if sc is not None and not re.search(r'\d', sc):
        probs.append('The scene has no counts, sizes or positions')
    elif sc is not None:
        loose = [b for b in _bullets(sc) if not b.startswith('TODO') and not b.endswith(':')
                 and not re.search(PLACED, b, re.I)]
        if loose:
            probs.append('The scene: %d object line(s) with no count, size or position: %s' % (len(loose), _quote(loose)))
    probs += _scene_plan(sc)
    probs += _key_plan(text)
    probs += _one_line(text, 'light direction', True)
    probs += _one_line(text, 'wind', bool(re.search(r'\b(?:lean|sway|trail|scarf|flag|smoke|steam|drift|gust)', text, re.I)))
    probs += _hex_check(text)
    lv0 = find('Lived-in details')
    if lv0 is not None:
        tiny = [b for b in _bullets(lv0) if not re.search(r'\d', b) and not b.startswith('TODO')]
        if tiny:
            probs.append('Lived-in details: %d line(s) with no size or position: %s (give each its native size, at '
                         'least 4x3 px, or cut it: three readable beat eight invisible)' % (len(tiny), _quote(tiny)))
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
    probs += _banned_ops(text, find)
    probs += _canvas_mismatch(find)
    probs += _trip_arithmetic(m, _loop_len(text))
    probs += _asset_calls(text)
    probs += _not_the_reference(text)
    probs += _tool_refs(text)
    return probs

# the scene's plan lines: the hero, its value and chroma owners and the plane shares are parsed by the gate
# (`pixelate check BLOCKIN.png --blockin --brief brief.md`), so their formats are fixed
SCENE_PLAN = [
    ('hero', r'hero', r'\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+.*peak value\s*:\s*\w.*peak chroma\s*:\s*\w',
     '`- Hero: x0,y0,x1,y1 (native px); peak value: OBJECT; peak chroma: OBJECT`'),
    ('planes', r'planes', None, '`- Planes: street 45% (mid), sky 20% (light), houses 35% (dark)`, two or more '
     '`NAME NN%` pairs, each band tag optional'),
    ('layout', r'layout', r'\d', 'what owns each region as boxes and the calm areas as boxes with their content'),
    ('masses', r'masses', r'(?:\d+\D+){2}\d', 'three or four masses of very different size with their sizes '
     '(`- Masses: one 140 px cloud bank, a 60 px trough, tufts of 20 and 12 px`)'),
    ('value plan', r'value plan', r'\d.*\b(?:focal|brightest)\b|\b(?:focal|brightest)\b.*\d',
     'three or four value groups with what falls in each and its L, one dark, and the focal light that alone '
     'holds the brightest (`- Value plan: rocks L .1; clouds .3; island .5; brightest only at the lamp`)'),
]
PLANE_MIN = {'topdown': (('ground', 'street', 'floor', 'road', 'plaza', 'yard', 'field'), 40,
                         '; 3/4 top-down: the ground is the largest plane, at least 40%, and roofs show as planes '
                         'seen from above')}

def _proj_key(proj):
    return 'topdown' if re.fullmatch(r'(?:3/4\s+)?top[\s-]*down|俯视|from above', (proj or '').strip(), re.I) else ''

def _planes(line):
    """the `NAME NN%` pairs of a Planes line (check.parse_planes): [(name, share, band tag or None)]"""
    import check
    return check.parse_planes(line.split(':', 1)[1] if ':' in line else line)

def _plan_line(sc, label):
    return next((b for b in _bullets(sc) if re.match(r'\**%s\b[^:]{0,24}:' % label, b, re.I)), None)

def _scene_plan(sc):
    """The scene's hero, planes, layout, masses and value plan lines: what the art director grades hardest and
    every weak first draft lacked (a hero smaller or duller than its scenery, a facade for a top-down request,
    even rows of equal lobes, no dark group). A top-down projection needs the ground at 40% or more."""
    if sc is None:
        return []
    out = []
    for name, label, want, fix in SCENE_PLAN:
        line = _plan_line(sc, label)
        if line is None:
            out.append('The scene has no %s line: write %s' % (name, fix))
        elif 'TODO' not in line and not (len(_planes(line)) >= 2 if want is None else re.search(want, line, re.I)):
            out.append('The scene: the %s line is not in the form %s' % (name, fix))
    pl = _plan_line(sc, 'planes')
    proj = re.search(r'Projection:\s*([^.\n]+)', sc)
    if pl and proj and _proj_key(proj.group(1)) == 'topdown':
        words, mn, _ = PLANE_MIN['topdown']
        got = sum(100 * v for n, v, _ in _planes(pl) if set(n.lower().split()) & set(words))
        if 'TODO' not in pl and got < mn:
            out.append('The scene: 3/4 top-down gives the ground %d%% of the frame; it is the largest plane, at least '
                       '%d%% (the street, plaza or yard), or the picture reads as a facade' % (got, mn))
    return out

# ---------------------------------------------------------------- object boxes: keys, values, calm areas
# The scene's box lines (native px, inclusive, square brackets), one object or region per line:
#   - Key: OBJECT [x0,y0,x1,y1]; L .30 on PLANE .15      a secondary object or named story beat that must read
#   - Key: OBJECT [x0,y0,x1,y1]; rim: DESCRIPTION          ... or read by a rim slot instead of a value step
#   - Value: PLANE [x0,y0,x1,y1] L .40                     the planned mean L of a plane region
#   - Calm: NAME [x0,y0,x1,y1]; texture: DESCRIPTION       a planned calm area and its designed texture
#   - Sprites: NAME [x0,y0,x1,y1], NAME [x0,y0,x1,y1]      an era scene's hardware-sprite actors
# A Key whose box overlaps the hero or another Key on purpose says "overlaps NAME on purpose".
BOX_RE = r'\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]'
KEY_MIN_DL = 0.10           # a Key differs from the plane behind it by this much L, or names a rim
CALM_MAX = 0.30             # calm areas total at most this share of the frame
DENSITY_WIN = 100           # outside calm areas every window this wide holds a Key or the hero
_NUM = r'(?<![\d.])(0?\.\d+|[01](?:\.\d+)?)(?![\d.%])'
_STOP = {'the', 'and', 'with', 'its', 'his', 'her', 'their', 'from', 'into', 'over', 'under', 'onto', 'for',
         'one', 'two', 'three', 'small', 'big', 'little', 'tiny', 'near', 'far', 'left', 'right', 'top', 'bottom',
         'side', 'that', 'this', 'each', 'every', 'only'}

def _words(name):
    """the content words of a name, plural s dropped: 'The keeper's window' -> {'keeper', 'window'}"""
    out = set()
    for w in re.findall(r'[a-z一-鿿]+', re.sub(r"'s\b", '', (name or '').lower())):
        if len(w) >= 3 and w not in _STOP:
            out.add(w[:-1] if w.endswith('s') and len(w) > 3 and not w.endswith('ss') else w)
    return out

def _same(a, b):
    return bool(_words(a) & _words(b))

def _clean(name):
    """a box's name as written, without markup, a line label or a leading article"""
    n = re.sub(r'[`*_]', '', (name or '').strip())
    n = re.sub(r'^[-*\s]*(?:key|value|calm|sprites?|hero|layout|planes)\s*:\s*', '', n, flags=re.I)
    n = re.sub(r'^(?:(?:and|with|plus|then|or|its|their|the|an|a)\s+)*', '', n.strip(' -'), flags=re.I)
    return re.sub(r'\s+', ' ', n).strip(' ,;:.-')

def _norm(name):
    return _clean(name).lower()

def _box_lines(text, label):
    """[(name, (x0, y0, x1, y1), rest of the line, whole line)] of every `- LABEL:` line with a box"""
    out = []
    for line in re.findall(r'^\s*[-*]\s+\**%s\**\s*:\s*(.*)$' % label, text, re.M | re.I):
        if 'TODO' in line:
            continue
        items = re.split(r'(?<=\])\s*,\s*', line) if label.lower().startswith('sprite') else [line]
        for it in items:
            m = re.search(BOX_RE, it)
            if m:
                out.append((_clean(it[:m.start()]), tuple(int(v) for v in m.groups()), it[m.end():], line))
    return out

def _canvas(text):
    m = re.search(r'\bcanvas\s+(\d+)\s*[x×]\s*(\d+)', text, re.I) or re.search(r'\bnative\s+(\d+)\s*[x×]\s*(\d+)', text, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else None

def _hero_box(text):
    m = re.search(r'^\s*[-*]\s*\**Hero\**:\s*\**\s*\[?\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', text, re.M | re.I)
    return tuple(int(v) for v in m.groups()) if m else None

def _overlap(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]

def _fmt_box(b):
    return '[%d,%d,%d,%d]' % b

def _on_purpose(line, other):
    return any(_same(n, other) or _norm(n) == _norm(other) for n in
               re.findall(r'overlaps?\s+(.+?)\s+on purpose', line, re.I))

def _union_area(boxes, W, H):
    import numpy as np
    m = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in boxes:
        m[max(0, y0):min(H, y1 + 1), max(0, x0):min(W, x1 + 1)] = True
    return m

def _beats(text):
    """the named story beats of section 5: its `- NAME: ...` bullets (a name of at most six words)"""
    sec = _sections(text)('Lived-in details') or ''
    out = []
    for b in _bullets(sec):
        m = re.match(r'\**([^:*\d][^:]{1,60}?)\**\s*:\s*\S', b)
        if m and 'TODO' not in b and len(m.group(1).split()) <= 6 and \
                not re.match(r'(?:key|value|calm|sprites?|changes?|per phase)\b', m.group(1), re.I):
            out.append(m.group(1).strip())
    return out

def eramod_limit(name):
    """the era's unique background tile limit, or None"""
    import era as eramod
    return eramod.ERAS.get(name, {}).get('bg_tiles')

def _key_plan(text):
    """the box lines of section 4 against each other and the brief: every Key reads against its plane
    (.10 L or a rim), sits inside the canvas and does not collide with the hero or another Key unless it
    says so, the calm areas stay under 30% with a texture each, the Value lines agree with the Value
    plan, every named story beat has a Key, the same object never gets two boxes, and outside the calm
    areas every 100 px window holds a Key or the hero. An era brief counts its sprites per scanline."""
    sc = _sections(text)('The scene')
    if sc is None:
        return []
    out = []
    keys, vals, calm = _box_lines(sc, 'Key'), _box_lines(sc, 'Value'), _box_lines(sc, 'Calm')
    sprites = _box_lines(sc, 'Sprites?')
    todo = lambda lab: re.search(r'^\s*[-*]\s+\**%s\**\s*:.*TODO' % lab, sc, re.M | re.I)
    for lab, got, fix in (('Key', keys, '`- Key: OBJECT [x0,y0,x1,y1]; L .30 on PLANE .15` (or `; rim: DESCRIPTION`)'),
                          ('Value', vals, '`- Value: PLANE [x0,y0,x1,y1] L .40`'),
                          ('Calm', calm, '`- Calm: NAME [x0,y0,x1,y1]; texture: DESCRIPTION`')):
        if not got and not todo(lab):
            out.append('The scene has no %s line: write one per %s as %s' % (
                lab, {'Key': 'secondary object and named story beat that must read', 'Value': 'plane region',
                      'Calm': 'calm area (or `- Calm: none`)'}[lab], fix))
    if not calm and re.search(r'^\s*[-*]\s+\**Calm\**\s*:\s*none\b', sc, re.M | re.I):
        out = [x for x in out if 'no Calm line' not in x]
    canvas = _canvas(text)
    hero = _hero_box(sc)
    vL = {}
    for n, b, rest, _ in vals:
        m = re.search(r'\bL\s*' + _NUM, rest)
        if not m:
            out.append('Value: %s %s has no planned L (`L .40`)' % (n, _fmt_box(b)))
        else:
            vL[n] = float(m.group(1))
    plane_L = lambda name: next((v for n, v in vL.items() if _norm(n) == _norm(name)), None) or \
        next((v for n, v in vL.items() if _same(n, name)), None)
    for n, b, rest, line in keys:
        if re.search(r'\brim\s*:\s*\S', rest, re.I):
            continue
        m = re.search(r'\bL\s*' + _NUM + r'\s+on\s+(?:the\s+)?(.+?)(?:\s+(?:L\s*)?' + _NUM + r')?\s*(?:[;,(]|$)', rest)
        if not m:
            out.append('Key: %s has no planned read: write `; L .30 on PLANE .15` (at least %.2f L apart) or '
                       '`; rim: DESCRIPTION`' % (n, KEY_MIN_DL))
            continue
        kl, pn, pl = float(m.group(1)), m.group(2).strip(), m.group(3)
        vp = plane_L(pn)
        if pl is not None and vp is not None and abs(float(pl) - vp) > 0.05:
            out.append('Key: %s puts %s at L %s but its Value line says %s: one number for the plane' % (
                n, pn, pl, ('%.2f' % vp).lstrip('0')))
        pl = float(pl) if pl is not None else vp
        if pl is None:
            out.append('Key: %s sits on %s with no L for it: give the plane\'s L here or in a Value line' % (n, pn))
        elif abs(kl - pl) < KEY_MIN_DL - 1e-9:
            out.append('Key: %s at L %s on %s at %s is %.2f apart: it will not read; move it %.2f or more '
                       'from the plane, or name a rim (`; rim: the light-facing edge in SLOT`)' % (
                           n, ('%.2f' % kl).lstrip('0'), pn, ('%.2f' % pl).lstrip('0'), abs(kl - pl), KEY_MIN_DL))
    if canvas:
        W, H = canvas
        for lab, got in (('Key', keys), ('Value', vals), ('Calm', calm), ('Sprites', sprites)):
            for n, b, _, _ in got:
                if b[2] < b[0] or b[3] < b[1]:
                    out.append('%s: %s %s is not x0,y0,x1,y1 with x1 >= x0 and y1 >= y0' % (lab, n, _fmt_box(b)))
                elif not (0 <= b[0] and b[2] < W and 0 <= b[1] and b[3] < H):
                    out.append('%s: %s %s runs off the %dx%d canvas (boxes are native px, inclusive)' % (
                        lab, n, _fmt_box(b), W, H))
    for i, (n, b, _, line) in enumerate(keys):
        if hero and _overlap(b, hero) and not _on_purpose(line, 'hero'):
            out.append('Key: %s %s overlaps the hero %s: move it clear, or say "overlaps hero on purpose"' % (
                n, _fmt_box(b), _fmt_box(hero)))
        for n2, b2, _, line2 in keys[i + 1:]:
            if _overlap(b, b2) and not (_on_purpose(line, n2) or _on_purpose(line2, n)):
                out.append('Key: %s %s and %s %s overlap: separate them, or say "overlaps %s on purpose"' % (
                    n, _fmt_box(b), n2, _fmt_box(b2), n2))
    if canvas and calm:
        W, H = canvas
        share = _union_area([b for _, b, _, _ in calm], W, H).mean()
        if share > CALM_MAX + 1e-9:
            out.append('Calm areas cover %d%% of the frame; at most %d%%: give the rest objects or story' % (
                round(100 * share), round(100 * CALM_MAX)))
    for n, b, rest, _ in calm:
        if not re.search(r'texture\s*:\s*\S', rest, re.I):
            out.append('Calm: %s %s names no texture: write `; texture: DESCRIPTION` (long swell dashes, a '
                       'stipple at one step, wet flags)' % (n, _fmt_box(b)))
    vp_line = _plan_line(sc, 'value plan')
    if vp_line and vals and 'TODO' not in vp_line:
        clauses = re.split(r';|\.\s', vp_line.split(':', 1)[1] if ':' in vp_line else vp_line)
        for n, v in vL.items():
            nums = [float(x) for c in clauses if _words(n) & _words(c) for x in re.findall(_NUM, c)]
            nums = [x for x in nums if x <= 1]
            if nums and min(abs(v - x) for x in nums) > 0.05 + 1e-9:
                out.append('Value: %s at L %s, but the Value plan puts it at %s: one number for each plane' % (
                    n, ('%.2f' % v).lstrip('0'), ', '.join(sorted({('%.2f' % x).lstrip('0') for x in nums}))))
    beats = _beats(text)
    miss = [bt for bt in beats if not any(_same(bt, n) for n, _, _, _ in keys)]
    if keys and miss:
        out.append('Lived-in details: %d named story beat(s) with no Key line: %s (give each `- Key: NAME '
                   '[x0,y0,x1,y1]; L .30 on PLANE .15` in section 4, or fold it into plain text)' % (len(miss), _quote(miss)))
    seen = {}
    for line in text.splitlines():
        if 'TODO' in line:
            continue
        last = 0
        for m in re.finditer(BOX_RE, line):
            head = line[last:m.start()]
            last = m.end()
            n = _norm(re.split(r'[:;,(]', head)[-1])
            if n and _words(n):
                seen.setdefault(n, []).append(tuple(int(v) for v in m.groups()))
    for n, bs in seen.items():
        if len(set(bs)) > 1:
            out.append('%s has %d different boxes in the brief (%s): one box per object' % (
                n, len(set(bs)), ', '.join(_fmt_box(b) for b in dict.fromkeys(bs))))
    if canvas and keys:
        W, H = canvas
        busy = [b for _, b, _, _ in keys] + ([hero] if hero else [])
        cm = _union_area([b for _, b, _, _ in calm], W, H)
        empty = []
        w = min(DENSITY_WIN, W, H)
        for y in sorted({*range(0, H - w + 1, w // 2), H - w}):
            for x in sorted({*range(0, W - w + 1, w // 2), W - w}):
                win = (x, y, x + w - 1, y + w - 1)
                if cm[y:y + w, x:x + w].mean() >= 0.5 or any(_overlap(win, b) for b in busy):
                    continue
                empty.append(win)
        if empty:
            out.append('density: %d window(s) of %d px hold no Key, no hero and no calm area (%s): put a readable '
                       'object or story there, or plan it as calm with a texture' % (
                           len(empty), w, ', '.join(_fmt_box(b) for b in empty[:3])))
    era = re.search(r'--era\s+([\w-]+)', text)
    if era and sprites:
        import era as eramod
        E = eramod.ERAS.get(era.group(1), {})
        sw, sh = E.get('sprite_size') or (8, 8)
        cols = lambda b: -(-(b[2] - b[0] + 1) // sw)
        rows = lambda b: -(-(b[3] - b[1] + 1) // sh)
        if E.get('sprite_line') and canvas:
            worst = max(sum(cols(b) for _, b, _, _ in sprites if b[1] <= y <= b[3]) for y in range(canvas[1]))
            if worst > E['sprite_line']:
                out.append('Sprites: %d hardware sprites share one scanline; %s allows %d (stagger the actors '
                           'vertically or draw one into the background)' % (worst, E['name'], E['sprite_line']))
        tot = sum(cols(b) * rows(b) for _, b, _, _ in sprites)
        if E.get('sprite_total') and tot > E['sprite_total']:
            out.append('Sprites: %d hardware sprites in all; %s allows %d' % (tot, E['name'], E['sprite_total']))
    if era:
        tb = re.search(r'^\s*[-*]\s+\**Tile budget\**\s*:(.*)$', text, re.M | re.I)
        nums = re.findall(r'(?<![\dx])(\d+)(?![\dx])', tb.group(1)) if tb and 'TODO' not in tb.group(1) else []
        lim = str(eramod_limit(era.group(1)))
        if tb is None or ('TODO' not in tb.group(1) and not [n for n in nums if n != lim]):
            out.append('Technical has no tile budget: write `- Tile budget: N unique 8x8 background tiles against '
                       'the limit of 256` from `pixelate era bg.png --era %s --tiles`' % era.group(1))
    return out

def _music(text):
    """a scene brief has a `- Music:` line from the style's direction; `none` only when the request asks for silence"""
    ml = re.findall(r'^\s*[-*]\s+\**Music\**\s*:\s*(.*)$', text, re.M | re.I)
    if not ml:
        return ['no "Music:" line (in Phases): write the music direction for this style (`pixelate style S` has '
                'it), or none when the request asks for silence']
    req = re.search(r'^Request:\s*(.*)$', text, re.M)
    if re.match(r'\**none\b', ml[0].strip(), re.I) and not _hits(' ' + (req.group(1) if req else '').lower() + ' ', SILENT):
        return ['Music is none but the request does not ask for silence: write the style\'s music direction '
                '(`pixelate style S`)']
    return []

ONE_LINE = {'light direction': 'every rim, lit side and shadow', 'wind': 'every lean, trail, smoke and drift'}

def _one_line(text, label, needed):
    """exactly one `- LABEL:` line; needed says whether a missing one is a problem"""
    n = len(re.findall(r'^\s*[-*]\s+\**%s\**\s*:' % label, text, re.M | re.I))
    if n > 1:
        return ['%d "%s:" lines: state it once; %s follows that one line' % (n, label, ONE_LINE[label])]
    if not n and needed:
        return ['no "%s:" line (in Art direction rules): state it once; %s follows it' % (label, ONE_LINE[label])]
    return []

def _palette_hexes(name):
    f = pathlib.Path(__file__).resolve().parent.parent / 'palettes' / ('%s.hex' % name)
    if not name or not f.exists():
        return []
    return ['#' + x.strip().lower().lstrip('#') for x in f.read_text().split() if re.fullmatch(r'#?[0-9a-fA-F]{6}', x.strip())]

def _hex_check(text):
    """every hex in a brief that cites a palette file (palettes/NAME.hex, or an era with a fixed palette) must be
    in it: an era's shades written from memory are the usual slip"""
    names = set(re.findall(r'palettes/([\w-]+)\.hex', text))
    for e in re.findall(r'--era\s+([\w-]+)', text):
        try:
            import era as eramod
            if eramod.ERAS.get(e, {}).get('palette'):
                names.add(eramod.ERAS[e]['palette'])
        except ImportError:
            pass
    allowed = set(h for n in names for h in _palette_hexes(n))
    if not allowed:
        return []
    bad = sorted(set(h.lower() for h in re.findall(r'#[0-9a-fA-F]{6}\b', text)) - allowed)
    return ['%d hex(es) not in %s: %s (copy the shades from the file)' % (
        len(bad), ', '.join('palettes/%s.hex' % n for n in sorted(names)), ', '.join(bad[:6]))] if bad else []

SHORT_SECTIONS = ['Style', ('Palette and size', 'Length and sound'), 'The work', 'Gate', 'Show the user']

def _is_short(text):
    first = text.lstrip().split('\n', 1)[0]
    gate = re.search(r'^##\s+(?:\d+\.\s*)?Gate\s*$', text, re.M | re.I)
    show = re.search(r'^##\s+(?:\d+\.\s*)?Show the user\b', text, re.M | re.I)
    later = re.search(r'^##\s+(?:[6-9]|1[01])\.', text, re.M)
    return 'short brief' in first.lower() or bool(gate and show and not later)

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
    probs += _not_the_reference(text)
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
FIX = {'no colour': 'name a colour word, a slot or a #hex',
       'no radius or size': 'give "radius N", "N px" or "sigma N"',
       'nothing that hides it': 'say "hidden by", "blocked by" or "behind" what'}
NOT_A_LIGHT = r'(todo|allowed|banned|everything|every light|no |ambient|per-light|reflections?|puddle reflections|void edges?|check)\b'
PLACED = (r'\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a pair|a single|dozen|left|right|'
          r'centre|center|middle|top|bottom|behind|front|foreground|background|above|below|under|over|beside|along|'
          r'edge|corner|third|half|quarter|near|far|between|across|horizon|on the|by the|at the|in the)\b')
NOT_FRAMES = r'(?!\.\d|\s*(?:px|pixels?|units?|cells?|rows?|columns?|cols?|%|deg|degrees?|s\b|seconds?|beats?|bpm))'
PALETTE_STEP = r'slot|step|ramp|palette|pool|rim|warm|cold|cool|glow|lit|none|no light'
IMPERFECT = r'imperfect|lean|sag|missing|broken|patched|worn|chipped|crooked|cracked|mismatch|faded|tilt|dent|peel'

def _sections(text):
    parts = re.split(r'^##\s+(?:\d+\.\s*)?', text, flags=re.M)
    body = {}
    for part in parts[1:]:
        head, _, rest = part.partition('\n')
        body[head.strip()] = rest
    return lambda name: next((v for k, v in body.items() if k.lower().startswith(name.lower())), None)

def _table_rows(b):
    """the data rows of every markdown table in b (not the header row or the |---| rule), cells joined by ' | '"""
    lines = b.splitlines()
    out = []
    for i, x in enumerate(lines):
        if not re.match(r'^\s*\|.*\|\s*$', x) or re.match(r'^\s*\|[\s:|-]+\|\s*$', x):
            continue
        if i + 1 < len(lines) and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i + 1]):
            continue                                   # the header row
        cells = [c.strip() for c in x.strip().strip('|').split('|')]
        if any(cells):
            out.append(' | '.join(c for c in cells if c))
    return out

def _bullets(b):
    return [x.strip() for x in re.findall(r'^[-*]\s+(\S.*)$', b, flags=re.M)] + _table_rows(b)

def _quote(items, n=3):
    q = ['"%s"' % (x if len(x) <= 48 else x[:45].rsplit(' ', 1)[0] + '...') for x in items[:n]]
    return ', '.join(q) + (' and %d more' % (len(items) - n) if len(items) > n else '')

TEMPERATURE_SECTIONS = ('Phase', 'Light list', 'Style and light regime', 'Art direction rules', 'Palette')
TEMPERATURE = (r'light|colou?r|tone|hue|tint|shade|shadow|side|rim|glow|pool|ramp|palette|slot|key|cast|'
               r'blue|teal|cyan|navy|grey|gray|green|violet|purple|white|silver|ice|steel|slate|moon|night|dawn|'
               r'warm|cold|counterpoint|accent|half|step|pixel')

def _vague(sec, b):
    out = []
    low = b.lower()
    for w in VAGUE:
        hits = list(re.finditer(r'\b' + re.escape(w.strip()) + r'\b', low))
        if w == 'cool':                    # colour temperature is not vague: cool light, cool blue, warm and cool
            if any(sec.lower().startswith(x.lower()) for x in TEMPERATURE_SECTIONS):
                continue
            near = r'\b(?:%s)(?:s|es|ed|er|ing)?\b' % TEMPERATURE
            hits = [h for h in hits if not re.search(near, low[max(0, h.start() - 30):h.start()] + ' ' +
                                                     low[h.end():h.end() + 30])]
        if hits:
            out.append('%s says "%s": name the thing, the count or the colour instead' % (sec, w.strip()))
    return out

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

def _style_of(text):
    m = re.search(r'^\s*[-*]\s+Style\s+`([a-z0-9-]+)`', text, re.M) or re.search(r'[Ss]tyle\W{0,4}`([a-z0-9-]+)`', text)
    try:
        return styles.get(m.group(1))['name'] if m else None
    except KeyError:
        return None

LIGHT_OPS = ('light', 'lightmap', 'glow', 'shaft', 'flare', 'streak', 'band', 'tint_field', 'fade', 'fog', 'motes',
             'over', 'ambient', 'darkness', 'rain', 'vignette', 'grain', 'scanlines', 'aberration')
NEGATED = (r"\b(?:no|not|never|banned|bans|without|instead|avoid|rather than|fallback|forbidden|nor|don't|do not|"
           r"isn't|is not|unlike)\b")

ALLOW_LINE = re.compile(r'^\s*[-*]\s*Gate override:\s*allow\s+(.+?)\s*$', re.M | re.I)
REASON = re.compile(r'\([^()]*[A-Za-z\u4e00-\u9fff][^()]*\)\s*\.?\s*$')

def _banned_ops(text, find):
    """a light op the brief's style does not allow (`Post.shaft` in pastel-cell, any Post op in a
    no-light-layer style), unless a line declares it as a deviation or override. Clauses that say
    no, never, banned or instead are skipped, and so is the Never section. The override form is
    `- Gate override: allow Post.shaft (the reason)`: one or more ops after `allow`, the reason in
    brackets (an allow line without one is a problem)."""
    style = _style_of(text)
    if not style:
        return []
    never = find('Never') or ''
    body = text.replace(never, '') if never else text
    probs, unreasoned = [], set()
    for m in ALLOW_LINE.finditer(text):
        if not REASON.search(m.group(1)):
            unreasoned.add(m.group(0).strip())
            probs.append('`Gate override: allow %s` has no reason: write it as `- Gate override: allow Post.OP '
                         '(the reason)`' % m.group(1).strip())
    declared = ' '.join(x for x in text.splitlines()
                        if re.search(r'deviat|override|exception', x, re.I) and x.strip() not in unreasoned)
    used = []
    for line in body.splitlines():
        for clause in re.split(r';|\.\s', line):
            if re.search(NEGATED, clause, re.I):
                continue
            for op in re.findall(r'(?<![\w])(?:post\.)?Post(?:\([^)]*\))?\.([a-z_]+)', clause):
                if op in LIGHT_OPS and op not in used:
                    used.append(op)
    for m in re.findall(r'--used\s+([\w:,]+)', body):
        used += [op for op in m.split(',') if op.split(':')[0] in LIGHT_OPS and op not in used]
    bad = [op for op in used if not styles.allows(style, op)
           and not re.search(r'\b%s\b' % re.escape(op.split(':')[0]), declared)]
    if not bad:
        return probs
    st = styles.get(style)
    return probs + ['uses %s, which `%s` does not allow (%s): use an allowed op, or add `- Gate override: allow '
                    'Post.%s (the reason)` (or declare it in section 0 as a deviation with the reason)' % (
                        ', '.join('`Post.%s`' % op for op in bad), style,
                        ('allowed: ' + ', '.join(st['allowed_post'])) if st['allowed_post'] and st['res'] != 'none'
                        else 'no light layer: light is palette steps', bad[0].split(':')[0])]

def _canvas_mismatch(find):
    """the scene's canvas against Technical's native size, and native x scale against the delivered size"""
    sc, te = find('The scene') or '', find('Technical') or ''
    out = []
    a = re.search(r'\bcanvas\s+(\d+)\s*[x×]\s*(\d+)', sc, re.I)
    b = re.search(r'\bnative\s+(\d+)\s*[x×]\s*(\d+)', te, re.I)
    if a and b and a.groups() != b.groups():
        out.append('The scene says canvas %sx%s but Technical says native %sx%s: one size for both' % (a.groups() + b.groups()))
    for line in te.splitlines():
        m = re.search(r'\bnative\s+(\d+)\s*[x×]\s*(\d+),?\s+(\d+)\s*x\s+nearest\s+to\s+(\d+)\s*[x×]\s*(\d+)', line, re.I)
        if m and not re.search(r'centred|centered|border|letterbox|pillarbox|crop', line, re.I):
            w, h, n, W, H = map(int, m.groups())
            if (w * n, h * n) != (W, H):
                out.append('Technical: native %dx%d at %dx is %dx%d, not %dx%d' % (w, h, n, w * n, h * n, W, H))
    return out

def _loop_len(text):
    head = (re.search(r'Motion table[^\n]*?(\d+)\s*frames', text) or
            re.search(r'Loop:\s*(?:a seamless\s*)?(\d+)[\s-]*frames', text) or
            re.search(r'(\d+)[\s-]*frame loop', text))
    return int(head.group(1)) if head else None

def _trip_arithmetic(m, T=None):
    """a motion line with one speed (N px per frame, 1 px every K frames) and one path length (across W px,
    a W px lap or tile, every W px of path) must make a whole number of trips in the loop. Lines with a
    frame window (72-191), a start or a wait are left alone: their speed holds for part of the loop."""
    if m is None or not T:
        return []
    out = []
    for b in _bullets(m):
        low = b.lower()
        if re.search(r'\b\d+\s*(?:-|–|to)\s*\d+\b|\b(?:start|starts|stop|stops|wait|waits|until|then|beat|pause|'
                     r'once the|after|before|while)\b', low):
            continue
        speeds = set()
        for v, u in re.findall(r'(\d+(?:\.\d+)?)\s*(px|units?)\s*(?:per|a|/)\s*frame\b', low):
            speeds.add((float(v), u[:2]))
        for v, u, k in re.findall(r'(\d+)\s*(px|units?)\s+(?:every|per)\s+(\d+)\s+frames', low):
            speeds.add((int(v) / int(k), u[:2]))
        lengths = set()
        for pat in (r'across\s+(?:a\s+|the\s+)?(\d+)[\s-]*(px|units?)\b',
                    r'(\d+)[\s-]*(px|units?)(?:\s+[a-z-]+){0,2}?\s+(?:trip|lap|path|tile|torus|track|circuit)s?\b',
                    r'every\s+(\d+)\s+(px|units?)\s+of\s+(?:path|track)'):
            for w, u in re.findall(pat, low):
                lengths.add((int(w), u[:2]))
        if len(speeds) != 1 or len(lengths) != 1:
            continue
        (v, u1), (W, u2) = next(iter(speeds)), next(iter(lengths))
        if u1 != u2 or not W:
            continue
        trips = v * T / W
        if abs(trips - round(trips)) > 1e-6 or round(trips) == 0:
            out.append('Motion table: %g %s per frame over %d %s is %.2f trips in the %d-frame loop, not a whole '
                       'number: "%s" (change the speed, the length or the loop)' % (
                           v, 'px' if u1 == 'px' else 'units', W, 'px' if u1 == 'px' else 'units', trips, T,
                           b if len(b) <= 60 else b[:57].rsplit(' ', 1)[0] + '...'))
    return out

EXAMPLE_MODULES = ('props', 'figures', 'glyphs', 'particles')
EXAMPLE_WORDS = ('example', 'study', 'studied', 'references/assets', 'modelled on', 'modeled on', 'for reference',
                 'see how', 'read ')

DIFFER_AXES = ('subject', 'composition', 'camera', 'palette', 'light', 'motion')

def _library_ids():
    """the ids of the kit's library pieces a brief may study, starters left out"""
    lib = pathlib.Path(__file__).resolve().parent.parent / 'library'
    return sorted(p.name for p in lib.iterdir() if (p / 'piece.json').is_file() and not p.name.startswith('starter-'))

def _not_the_reference(text):
    """a brief that names a library piece it studied must say how the new piece differs from it: a line
    `Differs from ID: AXIS, AXIS, ...` naming at least four of subject, composition, camera, palette, light, motion.
    A studied piece teaches technique; four of six changed keeps the result from being that piece again."""
    out = []
    for pid in _library_ids():
        if not re.search(r'library/%s\b|`%s`' % (re.escape(pid), re.escape(pid)), text):
            continue
        m = re.search(r'differs from `?(?:library/)?%s`?\s*:([^\n]*)' % re.escape(pid), text, flags=re.I)
        axes = {a for a in DIFFER_AXES if m and re.search(r'\b%s\b' % a, m.group(1), flags=re.I)}
        if len(axes) < 4:
            out.append('the brief studies `%s` but %s: write `Differs from %s: ...` naming at least four of %s, each '
                       'with what changes (references/brief.md#not-the-reference)' % (
                           pid, 'names %d %s of difference' % (len(axes), 'axis' if len(axes) == 1 else 'axes') if m
                           else 'has no "Differs from" line', pid, ', '.join(DIFFER_AXES)))
    return out

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

# ---------------------------------------------------------------- delivery size and gate variants
SIZE_WORDS = {'4k': (3840, 2160), '2160p': (3840, 2160), '1440p': (2560, 1440), '1080p': (1920, 1080),
              '720p': (1280, 720)}
_SIZE = re.compile(r'(?<![\w.])(\d{2,5})\s*[x×]\s*(\d{2,5})(?![\w.])')
MIN_HERO_PX = 40            # a hero stays at least this tall on screen, at the delivered cell size

def size_of(text):
    """'1920x1080', '4k' or a request naming one -> (W, H) or None; in a request only a screen-sized
    WxH counts (both sides 480 or more), so '16x16 icons' is not a delivery size"""
    m = _SIZE.search(text or '')
    if m and (min(int(m.group(1)), int(m.group(2))) >= 480 or _SIZE.fullmatch((text or '').strip())):
        return int(m.group(1)), int(m.group(2))
    t = ' ' + (text or '').lower() + ' '
    return next((v for k, v in SIZE_WORDS.items() if _hit(t, k)), None)

def delivery(style, size=None, scale=None, era=None):
    """-> (w, h, scale, W, H): the native canvas, the whole scale and the delivered picture. size is the
    delivered (W, H): with a scale the canvas is size / scale; without one the scale is the whole divisor
    of both sides, at least 2, that puts the native height nearest the style's own (ties: nearest the
    style's scale), so a pixel-art delivery never lands at 1x (sticker-iso at 1280x720 is 640x360 at 2x).
    An era keeps its screen and takes the largest scale that fits (the rest is border)."""
    import math
    st = styles.get(style)
    w0, h0 = st['size']
    if era:
        import era as eramod
        w0, h0 = eramod.ERAS[era]['size']
        s = scale or (max(1, min(size[0] // w0, size[1] // h0)) if size else st['scale'])
        return w0, h0, s, w0 * s, h0 * s
    if not size:
        s = scale or st['scale']
        return w0, h0, s, w0 * s, h0 * s
    W, H = size
    if scale:
        if W % scale or H % scale:
            raise SystemExit('%dx%d is not a whole multiple of %d' % (W, H, scale))
        return W // scale, H // scale, scale, W, H
    ks = [k for k in range(2, min(W, H) + 1) if W % k == 0 and H % k == 0]
    if not ks:                                       # never 1x: the pixel grid has to show
        raise SystemExit('%dx%d has no whole scale of 2 or more; pick a size whose sides share a factor '
                         '(e.g. %dx%d) or pass --scale' % (W, H, W - W % 2, H - H % 2))
    s = min(ks, key=lambda k: (round(abs(math.log(H / k / h0)), 6), abs(math.log(k / st['scale']))))
    return W // s, H // s, s, W, H

FIG_SIZE = re.compile(r'(\d+)x(\d+)|(\d+)(?:-(\d+))? px')

def figure_size(st, h):
    """the style's figure line with its size scaled to a canvas h rows high (the style's size is for its own
    canvas height): -> (text, factor, tall rows at this canvas or None)"""
    m = FIG_SIZE.search(st['figures'])
    if not m:
        return st['figures'], 1.0, None
    f = h / st['size'][1] if h else 1.0
    tall = int(m.group(2) or m.group(4) or m.group(3))
    if abs(f - 1) <= 0.05:
        return st['figures'], f, tall
    size = ('%dx%d' % (round(int(m.group(1)) * f), round(tall * f)) if m.group(1) else
            '%d-%d px' % (round(int(m.group(3)) * f), round(tall * f)) if m.group(4) else '%d px' % round(tall * f))
    return st['figures'][:m.start()] + size + st['figures'][m.end():], f, round(tall * f)

def _figure_lines(st, h, scale, framed=None):
    """the figure size for this canvas: the style's size is for its own canvas height, scaled by native
    height, plus how tall the hero is on screen"""
    text, f, tall = figure_size(st, h)
    L = ['- Figures: %s, drawn as your own slot maps.' % _as_example(text)]
    if tall is None:
        return L
    if abs(f - 1) > 0.05:
        L.append('- That size is already scaled from the style\'s %dx%d canvas to this %d-row one (x%.2f by native '
                 'height).' % (st['size'][0], st['size'][1], h, f))
    L.append('- On screen the hero is about %d px tall (%d native rows x %d); in a collage cell or a small embed it '
             'stays at least %d px tall at the delivered cell size (see references/drawing.md#characters).' % (
                 tall * scale, tall, scale, MIN_HERO_PX))
    return L

def scene_of(style, request):
    """the style's scene variant the request matches (styles.STYLES[...]['scenes']), or None"""
    t = ' ' + (request or '').lower() + ' '
    for name, v in styles.get(style).get('scenes', {}).items():
        if _hits(t, v['words']):
            return name
    return None

def gate_cmd(st, scale, file='frame.png', era=None, scene=None):
    return 'pixelate check %s --style %s%s%s --scale %d' % (file, st['name'], (' --era %s' % era) if era else '',
                                                            (' --scene %s' % scene) if scene else '', scale)

# ---------------------------------------------------------------- the pre-filled brief
def _top_budget_note(b):
    """the hero-band note for a tight highlight bound: L > .8 at 2% or less means a big lit shape (a door
    wedge, a beam) is brightest only at its source and a step darker beyond it"""
    top = [(float(k[2:]), hi) for k, (lo, hi) in b.items() if k.startswith('L>') and not k.startswith('L>=')
           and hi is not None and hi <= 0.03]
    if not top:
        return ''
    t, hi = max(top)
    return ('; the budget keeps L > %s to %s%% of the frame, so a big lit shape (a door wedge, a beam) is brightest '
            'only at its source (near the door, at the lamp) and a step darker beyond it' % (
                ('%.2f' % t).rstrip('0').lstrip('0'), ('%.1f' % (100 * hi)).rstrip('0').rstrip('.')))

def _fmt_budget(b):
    return '; '.join('%s %s' % (k, ('>= %s' % lo) if hi is None else ('<= %s' % hi) if lo is None else
                                '%s..%s' % (lo, hi)) for k, (lo, hi) in b.items()) or 'none (look at it)'

def brief(style, request='', projection=None, choices=None, era=None, size=None, scale=None):
    """the references/brief.md brief as Markdown, with everything the style decides filled in and the
    scene-specific parts as TODO prompts; choices (from gaps()) adds section 0; size (W, H) is the
    delivered picture and scale the whole scale (delivery())"""
    st = styles.get(style)
    r = ROUTE[st['name']]
    w, h, N, DW, DH = delivery(st['name'], size, scale, era)
    scene = None if era else scene_of(st['name'], request)
    E = None
    if era:
        import era as eramod
        E = eramod.ERAS[era]
    frames, fps = r['frames'][0], st['fps']
    rebuild = bool(_hits(' ' + request.lower() + ' ', MODES[0][2]))
    stated, _, excluded = camera_intent(request)
    proj = projection or stated or ('inspect reference' if rebuild else
                                   'choose camera' if r['projection'] in excluded else r['projection'])
    screen_camera = proj in ('one-point perspective', 'two-point perspective', 'inspect reference', 'choose camera')
    light = {'none': 'no light layer: light is palette steps (warm slots, rims, a few highlight pixels)',
             'native': 'a light layer computed per art pixel from the scene\'s masks, scaled up last (post.Post(res="native"))',
             'screen': 'a light layer smooth inside each art pixel, composited at delivery size (post.Post(res="screen"))'}[st['res']]
    L = []
    L.append('# TODO title (scene brief)\n')
    L.append('Request: %s\n' % (request or 'TODO'))
    L.append('How to fill it: references/brief.md; each open item names the section to read and the command to run.\n')
    if choices:
        L.append(gaps_md(choices))
    L.append('## 1. Purpose and delivery')
    L.append('- TODO what it is for, where it will be seen (full screen, thumbnail, README), outputs (MP4, GIF/APNG, page, still) '
             '(see references/brief.md#1-purpose-and-delivery).')
    L.append('- Delivered at %dx%d: native %dx%d, %dx nearest%s.' % (
        DW, DH, w, h, N, (', centred in a %dx%d frame' % size) if size and (DW, DH) != tuple(size) else ''))
    if st['name'] == 'lofi':
        L.append('- Loop: the engine runs on a 30-tick clock (TICKS = cycle * grand * 30); sprites step at 10, 5 '
                 'or 2 fps; TODO the loop length (the music length for a stream cover; see references/drawing.md#motion).')
    else:
        L.append('- Loop: TODO the length at %d fps from the story beats: list the beats with their frame counts; '
                 'the loop is the longest action (a crossing, a lap of the procession, a door cycle) rounded up so '
                 'every period divides it (anim.check_periods)%s (see references/drawing.md#motion).%s' % (
                     fps, ('; %d frames is the fallback when nothing needs longer' % frames) if frames else '',
                     ' Delivered prescaled (screen light); excerpts as APNG, since a GIF bands soft light.'
                     if st['res'] == 'screen' else ' Excerpts as APNG (soft light bands in a GIF).'
                     if st['res'] == 'native' else ''))
    L.append('\n## 2. Style and light regime')
    L.append('- Style `%s`: %s.%s' % (
        st['name'], st['what'], ' Use its finish, not its geometry; the camera below controls the drawing.'
        if screen_camera else ''))
    L.append('- Light: %s; blend %s.' % (light, ', '.join(st['blend']) or 'none'))
    if E:
        L.append('- Ramps: 3-4 steps picked by hand from the %s palette. Palette: at most %d colours%s.' % (
            E.get('palette', era), E['max_colors'], ', shared backdrop' if E.get('shared_backdrop') else ''))
        hx = _palette_hexes(E.get('palette'))
        if hx and len(hx) <= 16:
            L.append('- Palette `palettes/%s.hex`, darkest first as listed: %s (copy these; never from memory).' % (
                E['palette'], ', '.join(hx)))
    else:
        L.append('- Ramps: `%s`. Palette: %s.' % (', '.join(st['ramp']), st['palette']))
    L.append('- Outline: %s. Dither: %s.' % (st['outline'], (', '.join(st['dither']) + ', ' + st['dither_where']) if st['dither'] else 'none'))
    L.append('- Learn the grammar only: no characters, places, logos or UI layouts from the work the style was measured '
             'on or any game the request names. TODO name anything else to avoid '
             '(see references/brief.md#2-style-and-light-regime; run `pixelate style %s`).' % st['name'])
    L.append('\n## 3. Art direction rules')
    for rule in r['rules']:
        if isinstance(rule, tuple):
            x, condition = rule
            if not _fits(condition, st['name'], proj):
                continue
        else:
            x = rule
        L.append('- ' + (x.replace('3.3-head iso figures', 'figures scaled for depth') if screen_camera else x))
    L.append('- TODO 3-5 rules for this scene: which silhouettes must read, where rims fall, the built-in imperfections '
             '(a lean, a sag, a missing plank, a mismatched part) (see references/drawing.md#drawing-objects; run '
             '`pixelate style %s` for the style\'s rules).' % st['name'])
    L.append('- Silhouette keys: TODO for each must-read object, the 2-3 features that make it that thing and its '
             'nearest misread (a kite: tall diamond, visible spars, no belly band; not an envelope); crowds in 3 or '
             'more poses, gathered in vignettes. Each of these objects also gets a Key line in section 4 (its box '
             'and how it reads).')
    L.append('- Light direction: TODO where the one key light comes from; every rim, lit side and shadow follows it.')
    L.append('- Wind: TODO its direction and strength, or none; every lean, trail, smoke and drift follows it.')
    L.append('- Every object is drawn in this scene\'s code from the primitives; anything the kit has no primitive for '
             'is a slot map. references/assets has finished examples to study, never to call.')
    L.append('\n## 4. The scene')
    L.append('- Projection: %s. Canvas %dx%d.' % (proj, w, h))
    if proj == 'choose camera':
        L.append('- Camera: TODO choose a view other than the one the request excludes. Record its framing and '
                 'construction at native-pixel size before drawing (see guides/rebuild.md#2-pick-the-camera).')
    elif screen_camera:
        vanishing = ('the vanishing point in native px' if proj == 'one-point perspective' else
                     'both vanishing points in native px' if proj == 'two-point perspective' else
                     'the reference vanishing point(s) in native px, if visible')
        construction = ('Decide from the reference whether edges converge; if they do, draw them on the '
                        'screen-space native-pixel grid.' if proj == 'inspect reference' else
                        'Draw converging edges and receding spacing on the screen-space native-pixel grid.')
        L.append('- Camera: TODO inspect the reference if one was supplied; route reads the request, not the image. '
                 f'Record the horizon in native px (or say it is outside the frame), {vanishing}, the crop and '
                 f'focal framing, and the near/far scale changes. {construction} Adapt figure sizes to depth, '
                 'not iso.Iso geometry (see guides/rebuild.md#2-pick-the-camera).')
    L.append('- Hero: TODO x0,y0,x1,y1 (native px); peak value: TODO the object that alone holds the brightest '
             'values; peak chroma: TODO the object that alone holds the top chroma%s. A figure stays at least %d px '
             'tall at the delivered cell; no other mass over 0.6x the hero\'s area or within 0.1 L of its peak '
             '(see references/drawing.md#composition).' % (
                 (' (the style\'s paints sit at C >= %.2f, so the hero\'s accent goes above that floor, about C %.2f; '
                  'both are clamped per hue to the sRGB gamut%s: `styles.chroma_floor(STYLE, HUE)` gives the paint '
                  'floor and the hero\'s target for a hue)' % (
                      st['paint_C'], st['paint_C'] + 0.04, ''.join(
                          (', where %s' % ', '.join('%s tops out at C %s' % (n, ('%.2f' % styles.gamut_C(h))[1:])
                                                    for n, h in styles.HUES
                                                    if styles.gamut_C(h) < st['paint_C'] + 0.04)) or '')))
                 if st.get('paint_C') and not E else '', MIN_HERO_PX))
    L.append('- Planes: TODO each object or place and its share of the frame, with the grey band it takes in the '
             'block-in when you want it checked (darkest, dark, mid, light, brightest or 1-4; planes may share a band), '
             'e.g. street 45%% (mid), sky 20%% (light), houses 25%% (dark), door wedge 10%% (brightest)%s.' % (
        PLANE_MIN.get(_proj_key(proj), ('', 0, ''))[2]))
    L.append('- Layout: TODO what owns each region as boxes [x0,y0,x1,y1] (native px, inclusive), the calm areas as '
             'boxes with what may sit in them; counts are maximums ("4 houses, no more"). One box per object: the '
             'same name never gets two boxes in the brief.')
    L.append('- Masses: TODO three or four masses of very different size, with sizes (say 50%, 25%, 15% of the '
             'width), for every field that fills a band (cloud sea, sea, roofs, crowd, canopy); never an even row '
             'of equal lobes, domes or houses (see references/drawing.md#composition).')
    L.append('- Value plan: TODO three or four value groups with what falls in each and its L (far, middle, near, '
             'hero), one of them dark; the brightest group only at the one focal light and its one repeat%s.' % (
                 _top_budget_note(styles.budgets(st['name'], scene)) if not E else ''))
    L.append('- Value: TODO one line per plane region, `- Value: PLANE [x0,y0,x1,y1] L .40`, its planned mean L; '
             'the numbers match the Value plan\'s groups.')
    L.append('- Key: TODO one line per secondary object and per named story beat that must read (the gate '
             'measures each box): `- Key: OBJECT [x0,y0,x1,y1]; L .30 on PLANE .15`, at least .10 L '
             'from the plane behind it, or `- Key: OBJECT [x0,y0,x1,y1]; rim: DESCRIPTION` (a rim slot on its '
             'light-facing edge). Keep Key boxes clear of the hero and of each other; a box that overlaps one on '
             'purpose says "overlaps NAME on purpose" (see references/drawing.md#drawing-objects).')
    L.append('- Calm: TODO one line per calm area, `- Calm: NAME [x0,y0,x1,y1]; texture: DESCRIPTION` (a designed '
             'texture: swell dashes, a one-step stipple, wet flags), all of them at most 30% of the frame; outside '
             'them every 100 px window holds a readable object or story (see references/drawing.md#composition).')
    if E:
        L.append('- Sprites: TODO each actor drawn as hardware sprites, `- Sprites: NAME [x0,y0,x1,y1], NAME '
                 '[x0,y0,x1,y1]`; lint counts them per scanline against the %s limits (era.check_sprites).' % E['name'])
    L.append('- TODO the full object list with counts and rough positions (left third, on the ridge, by the door) '
             '(see references/brief.md#4-the-scene; run `pixelate tools TOPIC` for each subject).')
    if st.get('stack'):
        L.append('- TODO the depth planes: far (hazed), middle (lit), near (flat dark silhouettes that occlude light) '
                 '(see references/drawing.md#composition).')
    L.append('\n## 5. Lived-in details')
    L.append('- TODO five to ten small, specific things that tell a story, each with its native size (at least 4x3 '
             'px) and the value step against what it sits on; three readable beat eight invisible; say which change per phase '
             '(see references/drawing.md#drawing-objects). Write each named story beat as `- NAME: ...` and give it a '
             'Key line in section 4 (lint checks every one has a Key).')
    L.append('\n## 6. Phases')
    L.append('- Accent ration: TODO each accent hue, the only objects that may carry it, and its share of the frame.')
    L.append('- TODO for each phase: the palette by named roles, its signature elements (not a recolour), what the '
             'music does in it (see references/drawing.md#phases and references/drawing.md#palette).')
    L.append('- Music: %s.' % music_line(request, st['name'], era))
    L.append('\n## 7. Light list')
    if st['res'] == 'none':
        L.append('- Every light is drawn: TODO each emitter with its warm slots, the pool shape it casts, its flicker table '
                 '(see references/drawing.md#light; run `pixelate tools lamp --style %s`).' % st['name'])
    else:
        L.append('- TODO each emitter: what, where, colour, radius or width, flicker or pulse, what it lights, what hides it '
                 '(each occluder opaque, partial with a float opacity, or gapped with slits) '
                 '(see references/drawing.md#light; run `pixelate tools lamp --style %s`).' % st['name'])
        L.append('- Allowed light ops: %s.' % (', '.join(st['allowed_post']) or 'none'))
    L.append('\n## 8. Motion table' + ('' if st['name'] == 'lofi' or not frames else
                                       ' (TODO the loop length from section 1, frames at %d fps)' % fps))
    L.append('- Motion: %s at about %d fps; every period divides the loop (anim.check_periods).' % (
        'stepped, hold tables' if st['motion'] == 'stepped' else 'actors move in screen pixels', fps))
    L.append('- TODO every moving thing with its frame count and rate; keep only a few things moving at once '
             '(see references/drawing.md#motion).')
    if frames and st['name'] != 'lofi':
        L.append('- Drifting layers (clouds, fog, water) make whole trips per loop: a %d px trip in a %d-frame loop '
                 'moves %.0f px/s; clouds should feel 15 px/s or slower, so a slow drift wants a longer loop or a '
                 'shorter tile, and every period still divides the loop.' % (w, frames, w * fps / frames))
    L.append('\n## 9. Particles')
    L.append('- TODO kinds, sprite variants, densities, depth layers, paths (hashed spawns, whole trips per loop) '
             '(see references/drawing.md#motion; run `pixelate tools rain` or the topic for the weather).')
    L.append('\n## 10. Never')
    for x in r['never']:
        L.append('- ' + x + '.')
    banned = [b for b in st['banned_post'] if b not in ('vignette', 'grain', 'scanlines', 'aberration')]
    if banned:
        L.append('- Banned light ops: %s.' % ', '.join(banned))
    L.append('- TODO anything else this scene must not do (see references/brief.md#10-never; `pixelate style %s` '
             'lists the bans).' % st['name'])
    L.append('\n## 11. Technical')
    if E:
        L.append('- %s limits: native %dx%d, at most %d colours on screen%s%s%s. No light layer, no dither the '
                 'console could not show. These override the style\'s canvas and colour count.' % (
                     E['name'], w, h, E['max_colors'], (', palette `%s`' % E['palette']) if E.get('palette') else '',
                     (', %d colours per %dx%d block' % (E['block_colors'], E['block'], E['block'])) if E.get('block') else '',
                     (', %d-colour sprites' % E['sprite_colors']) if E.get('sprite_colors') else ''))
        L.append('- Check: `pixelate era frame.png --era %s` (and `--force` to snap a draft); ramps picked from the '
                 'era palette, not palette.ramp.' % era)
        lim = [x for x in (
            ('at most %d per scanline' % E['sprite_line']) if E.get('sprite_line') else '',
            ('%d on screen' % E['sprite_total']) if E.get('sprite_total') else '',
            ('each up to %dx%d' % E['sprite_size']) if E.get('sprite_size') else '') if x]
        L.append('- Tile budget: TODO the unique %dx%d background tiles this screen needs%s (count them with '
                 '`pixelate era bg.png --era %s --tiles` on the background-only render); sprites: TODO each actor '
                 'as hardware sprites, %s (era.check_sprites).' % (
                     E['tile'], E['tile'], (' against the limit of %d' % E['bg_tiles']) if E.get('bg_tiles') else '',
                     era, ', '.join(lim) or 'no hardware sprite limit'))
    else:
        L.append('- Native %dx%d, %dx nearest to %dx%d; %s; about %d colours in the pixel layer.' % (
            w, h, N, DW, DH,
            'light layer at delivery size' if st['res'] == 'screen' else 'every cell flat at delivery size', st['colours']))
    L += [line.replace('iso people', 'figures adapted to the camera') if screen_camera else line
          for line in _figure_lines(st, h, N)]
    if E:
        L.append('- Budget: the %s checks replace the style\'s value budget in the gate (`--era %s`): screen size, '
                 'colour count, palette, colours per block, unique tiles; the style still sets the craft limits.' % (
                     E['name'], era))
    elif scene:
        L.append('- Budget: %s (scene `%s`: %s; provisional; the style\'s own: %s).' % (
            _fmt_budget(styles.budgets(st['name'], scene)), scene, st['scenes'][scene]['what'],
            _fmt_budget(st['budgets'])))
    else:
        L.append('- Budget (`styles.check`): %s.' % _fmt_budget(st['budgets']))
    L.append('- Gate: `%s` passes every line (redraw until it does)%s; frame T equals frame 0; reads at 480 px '
             'wide (see references/delivery.md#gate).' % (
                 gate_cmd(st, N, era=era, scene=scene),
                 '; `pixelate check SCENE` for the engine scene' if st['name'] == 'lofi' else ''))
    L.append('- Gate overrides: none. If the scene cannot meet one bound, add a line `- Gate override: RULE <= V '
             '(the reason)` and pass `--brief` to the gate (see references/delivery.md#gate).')
    L.append('- Art director: `pixelate critique --brief brief.md --block BLOCKIN.png` for this full brief, '
             'then `pixelate critique FRAME.png --brief brief.md` for the still; each stage allows at most '
             'three critique rounds by default, counting the first, unless the user explicitly allows more '
             '(see references/delivery.md#art-director).')
    L.append('- Show the user one still for go/no-go; animate only after they accept it and confirm the motion table '
             '(see references/delivery.md#still and references/delivery.md#animation-plan).')
    style_tools = [x for x in r['tools'] if not screen_camera or not re.search(
        r'\biso\b|iso_|compose\.(?:populate|strips)', x, re.I)]
    L.append('\nTechniques for this style: ' + '; '.join(style_tools) + '.')
    tt = topic_tools(request, st['name'], proj)
    if tt:
        L.append('Techniques for this subject (more: `pixelate tools TOPIC --style %s`; signatures: '
                 '`pixelate tools MODULE.func`):' % st['name'])
        L += ['- ' + x + '.' for x in tt]
    L.append('Always: ' + ALWAYS_TOOLS + '.')
    if r['example']:
        L.append('Closest example in the repo: %s.%s' % (
            r['example'], ' Study its finish, not its camera.' if screen_camera else ''))
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

def short_brief(style, request='', kind='sprite', r=None, era=None, size=None, scale=None):
    """the short brief for a small ask: section 0 (intent and defaults), style, palette and size, the
    work, the gate command, what to show the user"""
    st = styles.get(style)
    S = st['name']
    w, h, N, DW, DH = delivery(S, size, scale, era)
    E = None
    if era:
        import era as eramod
        E = eramod.ERAS[era]
    g = {x['topic']: x for x in gaps(request, r)} if r else {}
    file = {'palette': 'test.png', 'icons': 'icons.png', 'photo': 'out.png', 'assets': 'SHEET.png',
            'sprite': 'sprite.png', 'music': None}[kind]
    L = ['# TODO title (short brief: %s)\n' % kind, 'Request: %s\n' % (request or 'TODO'),
         'How to fill it: references/brief.md#short-brief; each open item names the section to read and the command to run.\n']
    L += ['## 0. Choices to confirm', '',
          'Defaults I picked where the request was open. Say OK to build as written, or change any line.', '',
          '- **intent**: TODO one line on what the user most likely wants but did not say (the feeling, the use, '
          'the game it is for, what would disappoint them; see references/brief.md#read-the-intent)']
    if 'style' in g:
        L.append('- **style**: %s' % g['style']['default'])
    if kind == 'photo' and 'projection' in g:
        L.append('- **camera**: %s' % g['projection']['default'])
    size = {'palette': 'about %d colours in `%s` ramps, 4-6 steps per role' % (st['colours'], ', '.join(st['ramp'])),
            'icons': '12 icons at 16x16 on one shared palette, lit from the upper left',
            'photo': 'native %dx%d, %dx nearest to %dx%d, about %d colours' % (w, h, N, DW, DH, st['colours']),
            'assets': 'TODO each sprite or tile with its size and frame count, for TODO the engine (see guides/assets.md)',
            'sprite': 'one sprite, %s, one pose facing right' % _as_example(st['figures']),
            'music': 'a seamless 60-120 s loop, calm, about 70-80 bpm'}[kind]
    L.append('- **%s**: %s' % ('length and mood' if kind == 'music' else 'size', size))
    if kind in ('sprite', 'assets', 'icons'):
        L.append('- **animation**: none until the still is accepted; then the frames and rates are confirmed first')
    if E:
        L.append('- **era limits**: %s: at most %d colours%s; check with `pixelate era IMG --era %s`' % (
            E['name'], E['max_colors'], (', palette %s' % E['palette']) if E.get('palette') else '', era))
    L.append('\n## 1. Style')
    L.append('- `%s`: %s.' % (S, st['what']))
    if kind != 'music':
        L.append('- Outline: %s. Dither: %s.' % (st['outline'], (', '.join(st['dither']) + ', ' + st['dither_where'])
                                                 if st['dither'] else 'none'))
    L.append('- Learn the grammar only: no characters, logos or UI from the work the style was measured on or any '
             'game the request names.')
    if kind == 'music':
        L.append('\n## 2. Length and sound')
        L.append('- TODO the loop length in seconds, the tempo, the instruments, the motif (see guides/music.md).')
    else:
        L.append('\n## 2. Palette and size')
        if E:
            L.append('- %s: at most %d colours%s; ramps picked by hand from the era palette.' % (
                E['name'], E['max_colors'], (', palette `%s`' % E['palette']) if E.get('palette') else ''))
        else:
            L.append('- Ramps `%s` (palette.ramp(style="%s")): %s.' % (', '.join(st['ramp']), st['ramp'][0], st['palette']))
        L.append('- Size: %s.' % size.replace('TODO ', 'TODO: '))
    L.append('\n## 3. The work')
    L += {'palette': ['- TODO the roles (outline, shadow, mid, light, highlight per material, one accent) and the steps per role '
                      '(see references/drawing.md#palette; run `pixelate style %s`).' % S,
                      '- A palette is judged on a sprite, not as chips: draw one small test sprite with it '
                      '(canvas.Canvas, palette.swatch for the chips).'],
          'icons': ['- TODO the icon list, one line each: the object and the one shape that tells it apart at 16 px '
                    '(see references/drawing.md#drawing-objects).',
                    '- One ramp set, one outline rule and one light direction across the set.',
                    '- Each icon is a slot map in code; for a small readable mark, study references/assets/glyphs.py stamp.'],
          'photo': ['- TODO what the photo shows and what must survive: the subject, camera and framing, the light, '
                    'the one detail people look for (inspect the reference; route reads only the request).',
                    '- First pass `pixelate image IMG -o out.png` (guides/pixelate.md), then fix by hand what it gets '
                    'wrong: the subject\'s edges, orphan pixels, outlines.',
                    '- A rebuilt, moving scene is a full brief: `pixelate route "..." --brief --full` with guides/rebuild.md.'],
          'assets': ['- TODO the list: each sprite or tile, its size, its frames (walk 4-8, idle 2-4) (see guides/assets.md; '
                     'run `pixelate tools figures --style %s`).' % S,
                     '- Each sprite is a slot map in code; for a similar finished thing, study references/assets/ '
                     'and draw your own at this size.',
                     '- Tiles seam on every edge pair (canvas.Canvas.tile); export with `pixelate assets PACK` (guides/assets.md).'],
          'sprite': ['- TODO the subject, its silhouette and the one feature that must read at 1x '
                     '(see references/drawing.md#characters; run `pixelate tools figures --style %s`).' % S,
                     '- Drawn as a slot map in code (canvas.Canvas, sprite.spec_edges, sprite.drop_shadow); for a '
                     'similar finished thing, study references/assets/ and draw your own.'],
          'music': ['- Start from `pixelate new music DIR` (guides/music.md).',
                    '- TODO what changes over the loop, and where the loop seam falls (see guides/music.md).']}[kind]
    projection = r['picks'][0]['projection'] if r else None
    tt = topic_tools(request, S, projection)
    if tt and kind != 'music':
        L.append('- Techniques for this subject (more: `pixelate tools TOPIC --style %s`):' % S)
        L += ['  - ' + x + '.' for x in tt]
    L.append('\n## 4. Gate')
    if kind == 'music':
        L.append('- `pixelate check DIR`, then `pixelate audio DIR loop.wav`: the seam holds below -60 dB.')
    else:
        L.append('- `%s%s`; redraw until every line passes (see references/delivery.md#gate).' % (
            gate_cmd(st, N, file, era=era), ' --pal PALETTE' if kind == 'palette' else ''))
        if E:
            L.append('- `pixelate era %s --era %s`.' % (file, era))
        L.append('- Art director: `pixelate critique %s --brief brief.md` for the still after the gate; '
                 'at most three critique rounds by default, counting the first, unless the user explicitly '
                 'allows more. If round 3 is below A, report the grade and unresolved ranked fixes and ask '
                 'whether to continue or change the brief; show only an A result as finished '
                 '(see references/delivery.md#art-director).' % file)
    L.append('\n## 5. Show the user (see references/delivery.md#still)')
    L.append('- ' + {'palette': 'The chips and the test sprite side by side at 1x and %dx, for go/no-go.' % N,
                     'icons': 'The sheet at 1x and %dx, and one row at the size it will be used, for go/no-go.' % N,
                     'photo': 'The photo and the result side by side at the same size, for go/no-go.',
                     'assets': 'One finished sprite (or a 3x3 tile patch) as a still for go/no-go; then the frame '
                               'and rate plan for a go before animating.',
                     'sprite': 'The sprite at 1x and %dx on the style\'s background, for go/no-go; frames only '
                               'after that, with the plan confirmed.' % N,
                     'music': 'A 20-30 s excerpt for go/no-go before the full loop.'}[kind])
    return '\n'.join(L) + '\n'

def _lint_case(fn, arg):
    if fn == 'vague':
        return bool(_vague(*arg))
    if fn == 'bullets':
        return len(_bullets(arg))
    if fn == 'periods':
        return any('does not divide' in x for x in lint('## 8. Motion table (96 frames at 12 fps)\n' + arg + '\n'))
    if fn == 'trips':
        return bool(_trip_arithmetic(arg, 96))
    if fn == 'banned':
        return bool(_banned_ops(arg, _sections(arg)))
    if fn == 'plan':
        return len(_scene_plan(arg + '\n'))
    if fn == 'music':
        return len(_music(arg))
    if fn == 'oneline':
        return len(_one_line(arg, 'light direction', True) + _one_line(arg, 'wind', 'trail' in arg))
    if fn == 'hex':
        return len(_hex_check(arg))
    if fn == 'keys':
        return len(_key_plan(arg))

def selftest(verbose=False):
    """-> number of cases that route wrong or whose brief misses a line (printed)"""
    from route_regression_cases import (
        CASES, CAMERA_CASES, CAMERA_DEFAULT_CASES, BRIEF_CASES, BRIEF_AVOID_CASES,
        SHORT_BRIEF_CASES, GAP_CASES, LINT_CASES,
    )

    bad = 0
    for q, topic, want, avoid, empty in GAP_CASES:
        g = next(x for x in gaps(q) if x['topic'] == topic)
        wrong = [w for w in want if w not in g['default']] + [w for w in avoid if w in g['default']] + (
            ['stated %r' % g['stated']] if empty and g['stated'] else [])
        bad += bool(wrong)
        if wrong or verbose:
            print('%s gaps    %-16s %s%s' % ('XX' if wrong else '  ', topic, q[:56], ('  wrong: %s' % wrong) if wrong else ''))
    for q in ('A Game Boy style lighthouse on a stormy night.', 'a game boy style forest'):
        wrong = any(x.startswith(('figures', 'game level')) for x in topic_tools(q, 'lofi'))
        bad += wrong
        if wrong or verbose:
            print('%s era     %-16s %s' % ('XX' if wrong else '  ', 'no figure/level', q))
    for fn, arg, expect in LINT_CASES:
        got = _lint_case(fn, arg)
        wrong = got != expect
        bad += wrong
        if wrong or verbose:
            print('%s lint    %-16s %s  (got %r)' % ('XX' if wrong else '  ', fn, str(arg)[:56].replace('\n', ' '), got))
    for q, size, scale, want in BRIEF_CASES:
        r = route(q)
        text = brief(r['picks'][0]['style'], q, projection=r['picks'][0]['projection'], era=r.get('era'),
                     size=size or size_of(q), scale=scale)
        miss = [w for w in want if w not in text]
        bad += bool(miss)
        if miss or verbose:
            print('%s brief   %-14s %s%s' % ('XX' if miss else '  ', r['picks'][0]['style'], q[:60],
                                            ('  missing: %s' % miss) if miss else ''))
    for q, avoid in BRIEF_AVOID_CASES:
        r = route(q)
        text = brief(r['picks'][0]['style'], q)
        found = [phrase for phrase in avoid if phrase in text]
        bad += bool(found)
        if found or verbose:
            print(f"{'XX' if found else '  '} camera brief {q[:48]}" + (f'  unexpected: {found}' if found else ''))
    for q, want, avoid in SHORT_BRIEF_CASES:
        r = route(q)
        text = short_brief(r['picks'][0]['style'], q, 'photo', r)
        missing = [phrase for phrase in want if phrase not in text]
        found = [phrase for phrase in avoid if phrase in text]
        bad += bool(missing or found)
        if missing or found or verbose:
            print(f"{'XX' if missing or found else '  '} short camera {q[:48]}" +
                  (f' missing: {missing}; unexpected: {found}' if missing or found else ''))
    for q, projection in CAMERA_DEFAULT_CASES:
        r = route(q)
        wrong = r['picks'][0]['projection'] != projection or r['projection'] is not None
        bad += wrong
        if wrong or verbose:
            print(f"{'XX' if wrong else '  '} camera default {projection:<22} {q[:50]}")
    for neg in ('Post.shaft' in brief('pastel-cell', 'sun rays over the clouds'),
                '(shapes.ray, canvas.Canvas.fill)' in brief('contre-jour', 'a beam of light')):
        bad += neg
        if neg:
            print('XX the light-beams topic gives a style the wrong ray')
    for q, projection in CAMERA_CASES:
        r = route(q)
        wrong = r['picks'][0]['projection'] != projection or r['projection'] != projection
        bad += wrong
        if wrong or verbose:
            print(f"{'XX' if wrong else '  '} camera  {projection:<22} {q[:70]}")
    for q, mode, ok in CASES:
        r = route(q)
        top = r['picks'][0]['style']
        wrong = r['mode'] != mode or (ok is not None and top not in ok)
        bad += wrong
        if wrong or verbose:
            print('%s %-7s %-14s %s' % ('XX' if wrong else '  ', r['mode'], top, q[:70]))
    n = (len(CASES) + len(CAMERA_CASES) + len(CAMERA_DEFAULT_CASES) + len(BRIEF_CASES) +
         len(BRIEF_AVOID_CASES) + len(SHORT_BRIEF_CASES) + len(GAP_CASES) + len(LINT_CASES) + 4)
    print('%d/%d cases route as expected' % (n - bad, n))
    return bad

def main(a):
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return 1
    if a[0] == '--selftest':
        return 1 if selftest('-v' in a) else 0
    if a[0] == '--intake':
        if len(a) < 2:
            raise SystemExit('--intake requires a request')
        print(json.dumps(intake_plan(' '.join(a[1:])), ensure_ascii=False))
        return 0
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
    size = scale = None
    if '--size' in a:
        i = a.index('--size'); size = size_of(a[i + 1]); del a[i:i + 2]
        if not size:
            raise SystemExit('--size takes WxH, e.g. 1920x1080 (the delivered picture)')
    if '--scale' in a:
        i = a.index('--scale'); scale = int(a[i + 1]); del a[i:i + 2]
    want = None
    if '--brief' in a:
        i = a.index('--brief')
        if i + 1 < len(a) and not a[i + 1].startswith('-') and a[i + 1] in list(styles.STYLES) + list(styles.ALIASES):
            want = a[i + 1]; del a[i + 1]
        del a[i]
        want = want or True
    elif full or out:                                # --full and -o only mean something for a brief
        want = True
    req = ' '.join(a)
    r = route(req)
    size = size or size_of(req)
    if want:
        style = r['picks'][0]['style'] if want is True else styles.get(want)['name']
        if style != r['picks'][0]['style']:            # a named style leads section 0 too
            rt = ROUTE[style]
            pick = next((q for q in r['picks'] if q['style'] == style), None) or dict(
                style=style, score=0, why=['named with --brief'],
                projection=r['projection'] or ('inspect reference' if r['mode'] == 'rebuild' else
                                               'choose camera' if rt['projection'] in r['excluded_cameras']
                                               else rt['projection']),
                pick_if=rt['pick_if'], example=rt['example'])
            r['picks'] = [pick] + [q for q in r['picks'] if q['style'] != style][:2]
        kind = None if full else small_kind(req, r)
        _, NH, _, DW, DH = delivery(style, size, scale, r.get('era'))
        if kind:
            text = short_brief(style, req, kind, r, era=r.get('era'), size=size, scale=scale)
        else:
            text = brief(style, req, projection=r['picks'][0]['projection'],
                         choices=gaps(req, r, (DW, DH) if size or scale else None, NH), era=r.get('era'),
                         size=size, scale=scale)
        if out:
            pathlib.Path(out).write_text(text); print('wrote', out)
        else:
            print(text)
        return 0
    print('request: %s' % req)
    when = 'read it now for the limits the brief needs' if r['mode'] == 'era' else 'it is for drawing, step 6'
    print('mode: %s (%s: %s)%s' % (r['mode'], r['guide'], when, '' if r['mode'] == 'scene' else ', then a style for the finish'))
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
    print('\nnext: pixelate route "%s" --brief %s -o brief.md, fill every TODO with the defaults,' % (req, r['picks'][0]['style']))
    print('      pixelate route --lint brief.md, then show the user the brief and section 0')
    return 0

if __name__ == '__main__':
    import signal
    if hasattr(signal, 'SIGPIPE'):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # quiet when piped to head
    sys.exit(main(sys.argv[1:]))
