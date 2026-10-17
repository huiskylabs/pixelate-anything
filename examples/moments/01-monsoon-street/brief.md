# Monsoon Street (rebuild brief)

Request: rebuild Pexels 18867525 (a one-point-perspective shopping street after rain) as a dim
blue-hour / night street in its own camera, cosy-lightmap `--scene exterior`, 480x270 at 4x. Two
stills of the best moments (A "Downpour: the tram crosses", B "2 a.m.: the mirror") and a 5 s
lofi sample of the downpour phase.

## 0. Choices to confirm

- **intent**: a showcase still a stranger stops on: the warm rationed lights of one corner shop
  winning against a cold wet street, the photo's camera kept, no red flood, no real brands.
- **style**: `cosy-lightmap`, scene `exterior` (pixel layer of albedo slots under one smooth
  multiplied lamp map at screen resolution; Stack planes so the near hoarding stays flat dark).
- **projection**: one-point perspective in screen space on the native grid (not iso), the photo's camera.
- **time and weather**: A downpour at blue hour turning night; B 2 a.m. after the rain, still.
- **phases**: blue hour, downpour, 2 a.m.; this delivery draws downpour (A) and 2 a.m. (B).
- **figures**: no people; one cat (B), one arm pulling in laundry (A).
- **purpose and outputs**: two 1920x1080 stills (prescaled screen light) plus their 1x pixel layers,
  palette.json, a 5.0 s WAV/MP3 sample.
- **music**: lofi, B minor, 66 bpm, felt piano lead and comp, brushes, sparse hats, heavy rain
  bed; sync point: a soft two-tone tram bell at about 2 s.

## 1. Purpose and delivery
- A gallery showcase of the pixelate-anything toolkit, seen full screen and as a 480 px thumbnail.
- Delivered at 1920x1080: native 480x270, light layer at delivery size (prescaled), nearest-neighbour pixel layer.
- Stills only; the motion table below fixes the moment each still freezes.

## 2. Style and light regime
- Style `cosy-lightmap` (learned from the measured Stardew-mine grammar only; no game assets,
  characters, logos or UI): `post.Stack(res='screen')`, `Post.lightmap` multiply, cool ambient,
  warm pools; emitters kept at albedo (`keep=`); allowed ops used: lightmap only.
- Ramps: `plum` shape (every material's darkest step leans into the shared plum), toy hue for the cat.
- Outline: part, in the shared plum. Dither: checker only, at the sky/roofline and wall crowns.
- Avoid: the photo's red flood, its real shop names, logos and the convenience-store mark; invented glyphs only.

## 3. Art direction rules
- Every receding edge meets the vanishing point; repeats (signs, windows, awnings, poles) are
  hand-placed at mismatched depths, sizes and gaps along the guides, never a stamped row.
- Facades are flat planes split along structure (wall, recess, awning underside, fascia), seams in plum.
- Light only in the lamp map; warm is rationed to the hero, the windows that are lit and the
  tram; everything between the pools sinks to the cool plum dark, never grey.
- Wet ground reflects in screen columns: each object mirrored about its own base row in darker
  slots; lights stay bright and stretch into stepped dash columns toward the viewer.
- Imperfections: a sagging awning lip on the left, one sign hanging askew, a dead tube in the
  hero sign's border, mismatched shutter slats, a patched slab on the right pavement.
- Silhouette keys: tram = long box with a window strip, pantograph diamond and overhead wire (not a
  bus: wire plus pantograph); paper lantern = fat oval with dark top and bottom caps and ribs (not
  a ball: caps and tassel); cat = pointed ears, arched back, upright tail hook (not a dog: tail and
  ears); bicycle = two open rings with a diamond frame and bars, chained to the lamp post; folded
  stool = an X of legs under a flat seat; bucket = a trapezoid with a lip and a drip above it.
- Light direction: the key light is the hero shop (right, at street level, facing left and toward
  the viewer); a secondary sodium street lamp on the left; rims face those two.
- Wind: light, from the left: rain leans 1 px right every 7 rows; the steam plume (B) bends right.

## 4. The scene
- Projection: one-point perspective. Canvas 480x270. Horizon y=168; vanishing point (276,168).
  Camera height 1.5 m, focal 400 px: ground row = 168 + 600/Z, x = 276 + 400 X/Z.
- Crop (kept from the photo): near-left corrugated hoarding x 0-56; left corner block facing the
  camera x 56-167, base row 207; left street wall receding x 167-225 (X -4.2 m); far opening
  x 225-316 at rows 183-187 (the far cross street, Z 33-41 m); right street wall receding x 316-351
  (X +3.3 m); hero corner shop x 351-461 (side face 351-373, front face 373-461, base row 212);
  near glass building sliver x 461-480; road from row 186 down to the bottom; overhead wires converge.
- Near/far scale: 67 px per metre on the bottom row, 12 px per metre at the far cross street
  (5.5x); the tram is 40 px tall, a far window 10 px, a near puddle ring 20 px.
- Hero: 344,120,462,210 (native px); peak value: the hero shop's lit fascia sign; peak chroma: the red paper lantern at its corner.
- Planes: hoarding 8% (1), far building and sky 13% (2), left corner block and street wall 27% (2), right street wall, hero upper floors and glass 20% (2), road and puddle 15% (3), pavements 8% (3), hero shopfront 8% (4)
- Layout: sky strip x 225-316, y 0-30 (calm: wires only); far building x 225-316, y 26-183 (few lit
  windows, traffic signal at 300,120); tram on the cross street x 225-316, y 138-186 (A only);
  puddle x 246-392, y 234-262; bicycle at the left lamp post x 104-140, y 204-222.
- Masses: left wall 58 px, corner block 111 px, hoarding 56 px, opening 91 px, right wall 35 px,
  hero 110 px: no two neighbours within 25% of each other.
- Value plan: hoarding, gaps, upper walls and sky L .08; walls, far building and road away from the pools L .2; pools, awnings, tram body and reflections L .45; brightest only at the hero sign L .92 (the tram window strip a step under it, L .75).
- Full object list: 1 hero shop (sign, lantern, window, door, indigo awning), 2 left shops with
  awnings, 4 projecting signs at mismatched depths (2 left, 2 right), 1 box sign on the corner
  block, 1 street lamp, 3 poles, 9 wires, 1 traffic signal, 1 tram (A), 1 vent with steam (B), 1 cat (B).

## 5. Lived-in details
- Folded stool under the hero awning, 5x9 px, wood one step above the dark wall (A, B).
- Bicycle chained to the lamp post, 30x16 px, in the lamp pool (A, B).
- Bucket under the awning leak, 7x6 px, metal two steps over the pavement, a drip stream into it (A; B dry, still there).
- Laundry: a window on the corner block with a pole, a shirt and a towel, an arm pulling them in, 26x14 px (A); in B the window is dark and the pole bare.
- Shutter half-down on the corner block's shop, 60x30 px, a warm strip under it (B); up in A.
- Patched pavement slab and a manhole/vent grate 12x4 px; steam plume from it (B).

## 6. Phases
- Accent ration: lantern red (the lantern only, plus its darker reflection, under 0.2%); sign glyph
  red-brown (hero sign glyphs only); cool teal neon (one box sign and the green signal, under 0.3%);
  warm window ramp (lit windows, tram windows, the lamp and their reflections, under 4%).
- Palette by roles (one strict palette shared by both stills; the light map changes per phase):
  shared plum dark, void, night-navy sky, cool slate (far building, metal, poles), warm-grey
  concrete (walls, pavement), brick brown (hero upper floors), wet asphalt blue-grey, teal glass,
  muted teal/maroon/indigo awnings, warm window ramp (dim amber to cream), hero sign warm white,
  glyph red, lantern red, teal neon, rain greys, steam greys, laundry white, stool wood, plant green.
- Blue hour: shops lighting up, damp pavement (not drawn here).
- Downpour (A), signature elements only in this phase: two rain layers, dripping stepped streams off awnings, an overflowing gutter,
  rings in the puddle, the tram crossing with its warm window strip and long stepped reflection
  columns, laundry pulled in; ambient cool grey-blue.
- 2 a.m. (B), signature elements only in this phase: rain gone, the puddle glass-smooth and mirroring the street, one vent steaming,
  one cat crossing in the shop's light pool, one shutter half-down, fewer lit windows, amber signal.
- Music: lofi, B minor, 66 bpm, felt piano lead and comp, brushes, sparse hats, rain bed 0.5;
  Bm9 - Gmaj7 - Em9 - F#7b9; sync point: the tram bell between 1.5 and 2.5 s.

## 7. Light list
- Hero sign: (402,127) warm white, sigma (26,10), gain 1.0; lights the awning, wall and pavement; hidden by nothing (no occluder: a flat 2D map).
- Hero window: (418,170) warm amber, sigma (30,22), gain 1.1; plus a ground spill (412,222) sigma (34,9); hidden by nothing, the stool and bucket stay in its light.
- Lantern: (377,145) red-orange, sigma 9, gain 0.5; hidden by nothing.
- Street lamp: (175,37) sodium amber, sigma (30,40), gain 0.8; pool on the left pavement (150,214) sigma (32,8); behind the hoarding, which is the near Stack plane and never takes light.
- Tram (A): window strip (270,163) warm, sigma (40,8), gain 0.6; lights the cross street; hidden by the street walls at the opening edges (they sit outside its sigma).
- Left shop windows, the corner shop strip under the shutter (B), far windows: small warm pools, sigma 6-14, gain 0.2-0.4; hidden by nothing.
- Signal: (300,124) green (A) / amber (B), sigma 4, gain 0.25; hidden by nothing.
- Allowed light ops: lightmap, motes, sprite, from_world; used: lightmap.

## 8. Motion table
- Stills freeze one frame of a 96-frame (8 s) loop at 12 fps (A at t=40, B at t=0).
- Tram: crosses once per loop (91 px opening plus 170 px tram), about 2.7 px per frame, window strip moving as one.
- Rain: 8 spans per loop for both layers; splashes 3 frames each.
- Puddle rings (A): 5 sources, a ring every 24 frames each; awning drips every 48 frames, offsets hashed.
- Steam (B): 4 puffs on a 24-frame period rising with a stepped sway; the cat walks 4 drawings held 3 ticks.

## 9. Particles
- Rain (A): far layer 150 streaks 1x4 px dim, near layer 55 streaks 1x9 px brighter, slant 7 to the right; splashes on the road and pavements; rings in the puddle (5 sources).

## 10. Never
- screen-blend light, filters, a lifted void, glow halos.
- alpha, blur or anti-aliasing in the pixel layer.
- readable brands or real shop names, the photo's red flood.
- symmetric or stamped rows of signs, windows or awnings.
- people other than the one arm at the laundry window.

## 11. Technical
- Native 480x270, 4x to 1920x1080; light layer at delivery size; about 55 slots in the pixel layer.
- Figures: the cat 16x9 px, an arm 5 px; animals as my own slot maps.
- Budget: L<0.1 0.1..0.45; L>0.8 <= 0.02; C>0.1 <= 0.03 (scene exterior).
- Gate: `pixelate check out/01-a.png --style cosy-lightmap --scene exterior --scale 4 --brief brief.md --pal out/palette.json --pre out/01-a@1x.png --used lightmap` passes every line; reads at 480 px wide.
- Gate overrides: none.
