# TODO title (scene brief)

Request: Use tactics at 640x360. Build a canal-side boatyard diorama floating in darkness, carried on five near-neutral greys with colour rationed to a few warm accents. It holds a wooden ship in dry dock, a timber crane (girders and trusses), a sawpit, a plank stack, a chandlery hut and a lock gate. Built as one 3D description in iso.py and sdf.py, turned on a lazy susan in four quarter-turns: bare ribs at dawn, planked hull at noon, deck and rails at dusk, mast and pennants at night with lanterns lit.

How to fill it: references/brief.md; each open item names the section to read and the command to run.

## 0. Choices to confirm

Defaults I picked where the request was open. Say OK to build as written, or change any line.

- **intent**: TODO one line on what the user most likely wants but did not say (the feeling, the use, the era or game it recalls, what would disappoint them; see references/brief.md#read-the-intent); every choice below follows from it
- **style**: `tactics` (a 2:1 iso diorama floating in the dark, five greys, rationed colour, hard cast shadows; UI on the screen grid at 1x/2x/3x); the runners-up are `cosy-lightmap`, `sticker-iso`
- **projection**: 2:1 iso (from the request: 2:1 iso)
- **time and weather**: night; the board lit by fire and impacts (from the request: night)
- **phases**: one phase, no cycle
- **figures**: one or two small figures doing a quiet, specific task (units 12-17 px, black outline)
- **purpose and outputs**: a gallery showcase: a seamless loop at 12 fps, its length set by the story beats: the longest action (a crossing, a lap of the procession, a door opening and closing) rounded up to a length every period divides (96 frames when nothing needs longer), as a 640x360 MP4, a GIF excerpt and a still
- **music**: a dark synth bass, sparse pulse arpeggios and low drum hits; 4/4, minor, tense and steady (100-110 bpm); sync point: a low hit on each impact or turn. Direction only: write the track in code (guides/music.md); `pixelate check TRACK.wav --style synthwave` judges it

## 1. Purpose and delivery
- TODO what it is for, where it will be seen (full screen, thumbnail, README), outputs (MP4, GIF/APNG, page, still) (see references/brief.md#1-purpose-and-delivery).
- Delivered at 640x360: native 320x180, 2x nearest.
- Loop: TODO the length at 12 fps from the story beats: list the beats with their frame counts; the loop is the longest action (a crossing, a lap of the procession, a door cycle) rounded up so every period divides it (anim.check_periods); 96 frames is the fallback when nothing needs longer (see references/drawing.md#motion).

## 2. Style and light regime
- Style `tactics`: a 2:1 iso diorama floating in the dark, five greys, rationed colour, hard cast shadows; UI on the screen grid at 1x/2x/3x.
- Light: no light layer: light is palette steps (warm slots, rims, a few highlight pixels); blend palette-step.
- Ramps: `arch, neutral`. Palette: about 30 world colours: 5 near-neutral greys > 72%, a 10-step sky, brass, unit accents.
- Outline: black. Dither: none.
- Learn the grammar only: no characters, places, logos or UI layouts from the work the style was measured on or any game the request names. TODO name anything else to avoid (see references/brief.md#2-style-and-light-regime; run `pixelate style tactics`).

## 3. Art direction rules
- Five near-neutral greys cover most of the frame; colour is rationed to units and threats.
- Black outlines with 1 px white spec strokes on upper-left edges; hard cast shadows.
- UI sits on the screen grid at 1x/2x/3x, crisp, never scaled softly.
- TODO 3-5 rules for this scene: which silhouettes must read, where rims fall, the built-in imperfections (a lean, a sag, a missing plank, a mismatched part) (see references/drawing.md#drawing-objects; run `pixelate style tactics` for the style's rules).
- Silhouette keys: TODO for each must-read object, the 2-3 features that make it that thing and its nearest misread (a kite: tall diamond, visible spars, no belly band; not an envelope); crowds in 3 or more poses, gathered in vignettes.
- Light direction: TODO where the one key light comes from; every rim, lit side and shadow follows it.
- Wind: TODO its direction and strength, or none; every lean, trail, smoke and drift follows it.
- Every object is drawn in this scene's code from the primitives; anything the kit has no primitive for is a slot map. references/assets has finished examples to study, never to call.

## 4. The scene
- Projection: 2:1 iso. Canvas 320x180.
- Hero: TODO x0,y0,x1,y1 (native px); peak value: TODO the object that alone holds the brightest values; peak chroma: TODO the object that alone holds the top chroma. A figure stays at least 40 px tall at the delivered cell; no other mass over 0.6x the hero's area or within 0.1 L of its peak (see references/drawing.md#composition).
- Planes: TODO each object or place and its share of the frame, with the grey band it takes in the block-in when you want it checked (darkest, dark, mid, light, brightest or 1-4; planes may share a band), e.g. street 45% (mid), sky 20% (light), houses 25% (dark), door wedge 10% (brightest).
- Layout: TODO what owns each region as boxes (x0-x1, y0-y1), the calm areas as boxes with what may sit in them; counts are maximums ("4 houses, no more").
- Masses: TODO three or four masses of very different size, with sizes (say 50%, 25%, 15% of the width), for every field that fills a band (cloud sea, sea, roofs, crowd, canopy); never an even row of equal lobes, domes or houses (see references/drawing.md#composition).
- Value plan: TODO three or four value groups with what falls in each and its L (far, middle, near, hero), one of them dark; the brightest group only at the one focal light and its one repeat.
- TODO the full object list with counts and rough positions (left third, on the ridge, by the door) (see references/brief.md#4-the-scene; run `pixelate tools TOPIC` for each subject).

## 5. Lived-in details
- TODO five to ten small, specific things that tell a story, each with its native size (at least 4x3 px) and the value step against what it sits on; three readable beat eight invisible; say which change per phase (see references/drawing.md#drawing-objects).

## 6. Phases
- Accent ration: TODO each accent hue, the only objects that may carry it, and its share of the frame.
- TODO for each phase: the palette by named roles, its signature elements (not a recolour), what the music does in it (see references/drawing.md#phases and references/drawing.md#palette).
- Music: a dark synth bass, sparse pulse arpeggios and low drum hits; 4/4, minor, tense and steady (100-110 bpm); sync point: a low hit on each impact or turn. Direction only: write the track in code (guides/music.md); `pixelate check TRACK.wav --style synthwave` judges it.

## 7. Light list
- Every light is drawn: TODO each emitter with its warm slots, the pool shape it casts, its flicker table (see references/drawing.md#light; run `pixelate tools lamp --style tactics`).

## 8. Motion table (TODO the loop length from section 1, frames at 12 fps)
- Motion: stepped, hold tables at about 12 fps; every period divides the loop (anim.check_periods).
- TODO every moving thing with its frame count and rate; keep only a few things moving at once (see references/drawing.md#motion).
- Drifting layers (clouds, fog, water) make whole trips per loop: a 320 px trip in a 96-frame loop moves 40 px/s; clouds should feel 15 px/s or slower, so a slow drift wants a longer loop or a shorter tile, and every period still divides the loop.

## 9. Particles
- TODO kinds, sprite variants, densities, depth layers, paths (hashed spawns, whole trips per loop) (see references/drawing.md#motion; run `pixelate tools rain` or the topic for the weather).

## 10. Never
- soft light.
- filters.
- saturated scenery.
- Banned light ops: light, lightmap, glow, shaft, flare, streak, band, tint_field, fade, fog, motes, over, ambient, darkness.
- TODO anything else this scene must not do (see references/brief.md#10-never; `pixelate style tactics` lists the bans).

## 11. Technical
- Native 320x180, 2x nearest to 640x360; every cell flat at delivery size; about 30 colours in the pixel layer.
- Figures: units 12-17 px, black outline, drawn as your own slot maps.
- That size is already scaled from the style's 640x360 canvas to this 180-row one (x0.50 by native height).
- On screen the hero is about 34 px tall (17 native rows x 2); in a collage cell or a small embed it stays at least 40 px tall at the delivered cell size (see references/drawing.md#characters).
- Budget (`styles.check`): C>0.08 <= 0.025; L<0.3 >= 0.7; median_C <= 0.02.
- Gate: `pixelate check frame.png --style tactics --scale 2` passes every line (redraw until it does); frame T equals frame 0; reads at 480 px wide (see references/delivery.md#gate).
- Gate overrides: none. If the scene cannot meet one bound, add a line `- Gate override: RULE <= V (the reason)` and pass `--brief` to the gate (see references/delivery.md#gate).
- Art director: `pixelate critique FRAME.png --brief brief.md` to a separate agent until it grades A (see references/delivery.md#art-director).
- Show the user one still for go/no-go; animate only after they accept it and confirm the motion table (see references/delivery.md#still and references/delivery.md#animation-plan).

Techniques for this style: the board from 2:1 iso boxes (iso.Iso.render); architecture ramps and a near-neutral grey ladder (palette.ramp(style="arch"), palette.neutral_ramp); the diorama floating in the dark (compose.stage); crisp UI text on the screen grid (pixfont.draw).
Techniques for this subject (more: `pixelate tools TOPIC --style tactics`; signatures: `pixelate tools MODULE.func`):
- water: sea in hard bands by distance from land, boats and fenders passed as floating= so they make no islands (water.depth_bands); dashed foam rings where things stand in water (water.foam_rings); reflections of hulls, posts and lights only (water.reflect); still basins and falls (water.pool, water.waterfall); boats, docks, barrels and crates as your own slot maps: the plan as a polygon, outlined per part, planks as seam rows (canvas.Canvas.poly, canvas.Canvas.outline, texture.planks) (study references/assets/props.py boat, dock, barrel, crate).
- sky: flat undithered strata locked by wisps and streaks (sky.strata, sky.wisp, sky.smile, sky.streaks); clouds as masses and masks (shapes.cloud, shapes.cloud_mass, shapes.cloud_mask, shapes.cloud_rgba).
- structure: girders and trusses as lines and lattices on the canvas (canvas.Canvas.line, texture.grille); how a girder or truss was built (study references/assets/props.py girders, truss); pitted concrete (texture.pits).
- small lights: lamps and lanterns as slot maps in warm slots (study references/assets/props.py lantern); flicker on held steps, passing t % T so the seam holds (light.flicker), and lamp-side rims (light.rim); marquee and signal lights (anim.chase); pools drawn in palette steps (light.Light.point, light.Light.apply).
- turning objects: a turning thing (a swing bridge, a turntable, a windmill) is a few key drawings, 4-8 for a quarter turn, held on a timeline with a longer hold at each end and a 1 px settle when it locks (anim.Timeline); keep it rigid across drawings: the same plank count, posts and rails in every key, only the angle changes; fix the jaggies by hand at the in-between angles; the box tools are axis-aligned: project the object's world corners per key angle (iso.Iso.to_screen) and fill the polygon yourself (canvas.Canvas.poly, canvas.Canvas.outline); the 0 and 90 degree keys can be boxes (iso.Iso.box). Units: +1 x is 2 px right and 1 px down, +1 z is 1 px up.
Always: checks: the gate `pixelate check FRAME --style S --scale N` on every delivered frame (budget, native cells, palette, readability, craftcheck), `pixelate check SCENE` for engine scenes, anim.check_periods (every period divides the loop), compose.check_density for busy scenes.
Closest example in the repo: examples/projections.
