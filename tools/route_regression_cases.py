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
    ('Rebuild this photo of a street in one-point perspective.', 'rebuild', None),
    ('Rebuild this photo of a corner in two-point perspective.', 'rebuild', None),
]

BRIEF_CASES = [
    ('A tiny noodle shop on a snowy street at night, seen from above.', (1920, 1080), None,
     ['Canvas 480x270', '--style cosy-lightmap --scene exterior --scale 4', 'scene `exterior`',
      '`pixelate critique --brief brief.md --block BLOCKIN.png` for this full brief',
      '`pixelate critique FRAME.png --brief brief.md` for the still; each stage allows at most '
      'three critique rounds by default, counting the first, unless the user explicitly allows more']),
    ('下雪的夜里，一家小面馆，从上往下看。3840x2160', None, None,
     ['Native 480x270, 8x nearest to 3840x2160', '--scene exterior --scale 8']),
    ('午夜山顶，一座裂开的天文台里涌出一道光柱，提着纸灯的朝圣者正沿石阶往上走。', None, None,
     ['--style contre-jour --scene beam', 'post.Post.shaft', '`--scene beam`']),
    ('A kid on a paper kite glides over a pink sea of clouds, sun rays through the gaps.', (1280, 720), None,
     ['Canvas 320x180', '4x nearest to 1280x720', 'shapes.ray']),
    ('A Game Boy style lighthouse on a stormy night. Four shades of green, the beam sweeping over the waves.',
     (1920, 1080), None, ['--style lofi --era gameboy --scale 7', 'replace the style\'s value budget', 'shapes.ray']),
    ('A busy canal market at noon in isometric.', (1920, 1080), 3, ['Canvas 640x360', 'Figures: 20-22 px iso people', 'x0.60 by native height']),
    ('A busy canal market at noon in isometric.', (1280, 720), None, ['Canvas 640x360', '2x nearest to 1280x720']),
    ('A busy canal market at noon in isometric.', None, None, ['- Music: an accordion-like lead', 'TRACK.wav']),
    ('Rebuild this photo of a street in one-point perspective.', None, None,
     ['- Projection: one-point perspective.', 'the vanishing point in native px',
      'route reads the request, not the image', 'screen-space native-pixel grid',
      'Use its finish, not its geometry']),
    ('Rebuild this photo of a corner in two-point perspective.', None, None,
     ['- Projection: two-point perspective.', 'both vanishing points in native px']),
    ('Rebuild this photo in two-point perspective instead of one-point perspective.', None, None,
     ['- Projection: two-point perspective.', 'both vanishing points in native px']),
    ('Rebuild this photo using two-point perspective over one-point perspective.', None, None,
     ['- Projection: two-point perspective.', 'both vanishing points in native px']),
    ('Rebuild this photo of a street.', None, None,
     ['- Projection: inspect reference.', '- Camera: TODO inspect the reference',
      'reference vanishing point(s) in native px', 'Use its finish, not its geometry']),
    ('A sunny coast in two-point perspective.', None, None,
     ['- Projection: two-point perspective.', 'Sun and shade are palette steps']),
    ('A sunny coast from above.', None, None,
     ["iso.Iso(camera='topdown').cast_shadows"]),
    ('Make a full HD overworld, not top-down.', None, None,
     ['- Projection: choose camera.', 'choose a view other than the one the request excludes']),
]

GAP_CASES = [
    ('A Game Boy style lighthouse on a stormy night, handheld.', 'time and weather', ['night', 'storm'],
     ['evening', 'dusk', 'calm'], False),
    ('A tiny noodle shop on a snowy night, seen from above.', 'time and weather', ['night', 'snow', 'from outside'],
     ['indoors', 'rain'], False),
    ('下雪的夜里，一家小面馆，从上往下看。', 'time and weather', ['night', 'snow'], ['indoors', 'rain'], False),
    ('Midnight on a mountain top. Light pours up out of a cracked-open observatory.', 'time and weather',
     ['midnight'], ['rain', 'fog'], False),
    ('a misty midnight forest ritual', 'time and weather', ['midnight', 'fog'], [], False),
    ('a cosy coffee shop interior in the morning', 'time and weather', ['indoors', 'morning'], [], False),
    ('a cosy farm at noon', 'time and weather', ['noon'], ['rain', 'night'], False),
    ('An old four-shade green handheld game screen: a lighthouse on a rocky headland on a stormy night. The beam '
     'sweeps out from the lantern room and ends on a small fishing boat.', 'time and weather', ['night', 'storm'],
     ['indoors', 'room'], False),
    ('A busy canal market at noon, in isometric. A lemon-yellow tram rolls across a swing bridge, with clear room '
     'around it on the rails.', 'time and weather', ['noon'], ['indoors', 'room'], False),
    ('An old four-shade green handheld game screen: a lighthouse on a stormy night.', 'music', ['Game Boy'],
     ['lofi'], False),
    ('A busy canal market at noon in isometric.', 'music', ['accordion', 'pixelate check TRACK.wav'], ['none'], False),
    ('A silent canal market at noon in isometric, no music.', 'music', ['none'], ['accordion'], False),
    ('A Game Boy style lighthouse on a stormy night.', 'figures', ['one or two small figures'], [], True),
    ('A busy canal market at noon in isometric.', 'purpose and outputs', ['story beats', 'every period divides'],
     [], False),
    ('Rebuild this photo of a street in one-point perspective.', 'style', ['finish, not the camera'], [], False),
    ('Rebuild this photo of a street in one-point perspective.', 'figures', ['sized for the camera'],
     ['iso people'], True),
]
LINT_CASES = [
    ('vague', ('Phases', '- a cool blue rim on the left'), False),
    ('vague', ('The scene', '- the far peaks in cool grey, the near ones warm'), False),
    ('vague', ('The scene', '- something cool in the corner'), True),
    ('bullets', '| what | where |\n|---|---|\n| cat | sill, x 12 |\n| lamp | door, x 40 |\n', 2),
    ('periods', '- Pine sway: 2 drawings (period 12), the tile period 320 px wide, every 12 frames', False),
    ('periods', '- Flags: 3 drawings (period 7)', True),
    ('trips', '- Tram: 1 px per frame across 300 px', True),
    ('trips', '- Tram: 1 px every 2 frames across 48 px', False),
    ('banned', 'Style `pastel-cell`\n- Rays: Post.shaft from the gap', True),
    ('banned', 'Style `pastel-cell`\n- **light deviation**: Post.shaft for the rays\n- Rays: Post.shaft from the gap', False),
    ('banned', 'Style `sticker-iso`\n- No Post.glow, no shaft: light is palette steps', False),
    ('banned', 'Style `pastel-cell`\n- Gate override: allow Post.shaft (the rays through the gap are the subject)\n'
               '- Rays: Post.shaft from the gap', False),
    ('banned', 'Style `pastel-cell`\n- Gate override: allow Post.shaft\n- Rays: Post.shaft from the gap', True),
    ('plan', '- Projection: side view.\n- Hero: 100,60,220,150 (native px); peak value: the lamp; peak chroma: the kite\n'
             '- Planes: sky 55%, sea 30%, island 15%\n- Layout: island x 180-250, y 60-110; calm sky x 0-150\n'
             '- Masses: cloud sea as a 140 px bank, a 60 px trough, tufts of 20 and 12 px\n'
             '- Value plan: sea L .2, clouds .5, island .6; brightest only at the lamp, 3%', 0),
    ('plan', '- Projection: side view.\n- Subject: the shop front, x 128 to 512\n- the object list, 3 houses', 5),
    ('plan', '- Projection: side view.\n- Hero: the kid, about 48x26 px\n- Planes: mostly sky\n- Layout: x 0-100\n'
             '- Masses: big clouds\n- Value plan: dark sea, bright sun', 4),
    ('plan', '- Projection: 3/4 top-down.\n- Hero: 128,34,512,262 (native px); peak value: the door wedge; peak '
             'chroma: the cat\n- Planes: roof 40%, street 27%, back row 10%, walls 23%\n- Layout: shop x 128-512\n'
             '- Masses: roof 384 px, neighbours 112 and 112 px\n- Value plan: void L .05, walls .15; brightest at '
             'the door, 2%', 1),
    ('plan', '- Projection: 3/4 top-down.\n- Hero: 128,34,512,262 (native px); peak value: the door wedge; peak '
             'chroma: the cat\n- Planes: street 40% (mid, the canal bank), canal 15% (mid), sky 10% [light] because '
             'it is open, houses 25% (dark), wedge 10% (brightest)\n- Layout: shop x 128-512\n'
             '- Masses: roof 384 px, neighbours 112 and 112 px\n- Value plan: void L .05, walls .15; brightest at '
             'the door, 2%', 0),
    ('oneline', '- Light direction: upper right\n- Wind: from the left\n- Light direction: the lamp', 1),
    ('oneline', '- Light direction: upper right\n- the scarf trails left', 1),
    ('oneline', '- Light direction: upper right\n- Wind: none', 0),
    ('music', 'Request: a canal market at noon\n## 6. Phases\n- one phase\n', 1),
    ('music', 'Request: a canal market at noon\n## 6. Phases\n- Music: none\n', 1),
    ('music', 'Request: a silent canal market at noon\n## 6. Phases\n- Music: none (silent)\n', 0),
    ('music', 'Request: a canal market\n## 6. Phases\n- Music: an accordion lead, 4/4 swing\n', 0),
    ('hex', 'gate `--era gameboy`; gb2 #8bac0f, gb3 #9bbc0f', 1),
    ('hex', 'palette `palettes/gameboy.hex`: #0f380f #306230 #678e23 #9bbc0f', 0),
    ('hex', 'our own palette: #123456 #abcdef', 0),
    ('plan', '- Projection: two-point perspective from above.\n- Hero: 128,34,512,262 (native px); peak value: the door wedge; peak '
             'chroma: the cat\n- Planes: roof 40%, street 27%, back row 10%, walls 23%\n- Layout: shop x 128-512\n'
             '- Masses: roof 384 px, neighbours 112 and 112 px\n- Value plan: void L .05, walls .15; brightest at '
             'the door, 2%', 0),
]

CAMERA_CASES = [
    ('A street seen in one-point perspective, not isometric.', 'one-point perspective'),
    ('Rebuild this photo in two-point perspective, not one-point perspective.', 'two-point perspective'),
    ('Rebuild this photo in two-point perspective instead of one-point perspective.', 'two-point perspective'),
    ('Rebuild this photo in two-point perspective rather than one-point perspective.', 'two-point perspective'),
    ('Rebuild this photo in two-point perspective; avoid one-point perspective.', 'two-point perspective'),
    ('Rebuild this photo in two-point perspective; avoid using one-point perspective.', 'two-point perspective'),
    ('Rebuild this photo in two-point perspective, not in one-point perspective.', 'two-point perspective'),
    ('Rebuild this photo using two-point perspective over one-point perspective.', 'two-point perspective'),
    ('Rebuild this photo; do not use one-point perspective; choose two-point perspective.', 'two-point perspective'),
    ('Rebuild this photo in one-point perspective, not two-point perspective.', 'one-point perspective'),
    ('Rebuild this photo in one-point perspective instead of two-point perspective.', 'one-point perspective'),
    ('Rebuild this two-point perspective photo of an isometric-looking city.', 'two-point perspective'),
    ('A corridor with a single vanishing point.', 'one-point perspective'),
    ('A corner with two vanishing points.', 'two-point perspective'),
    ('An isometric castle siege.', '2:1 iso'),
    ('A village from above.', '3/4 top-down'),
    ('A side view of a street.', 'side'),
    ('An oblique projection of a house.', 'oblique'),
    ('A military projection of a town.', 'military'),
]

CAMERA_DEFAULT_CASES = [
    ('a cosy farm at night', '3/4 top-down'),
    ('make a pixel island', 'side'),
    ('Rebuild this reference image of a street.', 'inspect reference'),
    ('Rebuild this photo, not one-point perspective.', 'inspect reference'),
    ('Rebuild this photo, not isometric.', 'inspect reference'),
    ('Rebuild this photo, without an isometric view.', 'inspect reference'),
    ('Rebuild this photo of a city; do not use one-point perspective.', 'inspect reference'),
    ("Rebuild this photo; don't use one-point perspective.", 'inspect reference'),
    ('Rebuild this photo; avoid using one-point perspective.', 'inspect reference'),
    ('Rebuild this isometric city; do not use isometric projection.', 'inspect reference'),
    ('A city, do not use isometric projection.', 'choose camera'),
    ('Make a full HD overworld, not top-down.', 'choose camera'),
    ('Rebuild this photo, no longer in one-point perspective.', 'inspect reference'),
    ('Rebuild this photo in one-point perspective or two-point perspective.', 'inspect reference'),
]

BRIEF_AVOID_CASES = [
    ('Rebuild this photo of a street in one-point perspective.', ['iso boxes', 'iso_person']),
    ('Rebuild this photo of a corner in two-point perspective.', ['iso boxes', 'iso_person']),
    ('Rebuild this photo of a street.', ['- Projection: 2:1 iso.', 'iso boxes']),
    ('A sunny coast in two-point perspective.', ["iso.Iso(camera='topdown').cast_shadows"]),
    ('Make a full HD overworld, not top-down.', ["iso.Iso(camera='topdown').cast_shadows"]),
]

SHORT_BRIEF_CASES = [
    ('pixelate this reference photo of a street in two-point perspective',
     ['**camera**: two-point perspective', '`pixelate critique out.png --brief brief.md`',
      'at most three critique rounds by default'], ['iso.Iso.box', '2:1 slope']),
]
