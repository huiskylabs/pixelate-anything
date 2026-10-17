# TODO title (scene brief)

Request: Rebuild the photo: a street-level one-point-perspective shot of a narrow shopping street at night after rain, overhead signs, wires and awnings going back to a vanishing point; a lit corner shopfront with a red paper lantern; a lit tram crossing the far end; a wet road and a foreground puddle mirroring the street; downpour rain; a cat; steam from a vent

How to fill it: references/brief.md; each open item names the section to read and the command to run.

## 0. Choices to confirm

Defaults I picked where the request was open. Say OK to build as written, or change any line.

- **intent**: TODO one line on what the user most likely wants but did not say (the feeling, the use, the era or game it recalls, what would disappoint them; see references/brief.md#read-the-intent); every choice below follows from it
- **style**: `cosy-lightmap` (16-bit cosy cave: pixel layer under one smooth multiplied lamp map at screen resolution; the void stays black); the runners-up are `native-glow`, `sticker-iso` (from the request: lantern/night)
- **projection**: 3/4 top-down (from the request: 3/4 top-down)
- **time and weather**: night, rain; many warm windows and lamps pooling light in the dark (from the request: night/rain)
- **phases**: one phase, no cycle
- **figures**: only the actors the request names, nobody added (from the request: cat)
- **purpose and outputs**: a gallery showcase: a seamless loop at 12 fps, its length set by the story beats: the longest action (a crossing, a lap of the procession, a door opening and closing) rounded up to a length every period divides (96 frames when nothing needs longer), as a 480x270 MP4, an APNG excerpt (a GIF bands soft light) and a still
- **music**: warm electric piano, soft drums and vinyl crackle; 4/4 swung, major sevenths, slow (70-80 bpm); under a bed of rain; sync point: a soft chime as a lamp flickers or a door opens. Direction only: write the track in code (guides/music.md); `pixelate check TRACK.wav --style lofi` judges it

## 1. Purpose and delivery
- TODO what it is for, where it will be seen (full screen, thumbnail, README), outputs (MP4, GIF/APNG, page, still) (see references/brief.md#1-purpose-and-delivery).
- Delivered at 480x270: native 240x135, 2x nearest.
- Loop: TODO the length at 12 fps from the story beats: list the beats with their frame counts; the loop is the longest action (a crossing, a lap of the procession, a door cycle) rounded up so every period divides it (anim.check_periods); 96 frames is the fallback when nothing needs longer (see references/drawing.md#motion). Delivered prescaled (screen light); excerpts as APNG, since a GIF bands soft light.

## 2. Style and light regime
- Style `cosy-lightmap`: 16-bit cosy cave: pixel layer under one smooth multiplied lamp map at screen resolution; the void stays black.
- Light: a light layer smooth inside each art pixel, composited at delivery size (post.Post(res="screen")); blend multiply.
- Ramps: `plum, toy`. Palette: 40-50 albedo colours: 4-6 per material, one shared plum, #000 void, toy-hue creatures.
- Outline: part. Dither: checker, wall crowns sinking into the void.
- Learn the grammar only: no characters, places, logos or UI layouts from the work the style was measured on or any game the request names. TODO name anything else to avoid (see references/brief.md#2-style-and-light-regime; run `pixelate style cosy-lightmap`).

## 3. Art direction rules
- Albedo palette of 4-6 tones per material sharing one plum dark; outlines per part in that plum.
- One smooth lamp map multiplied at screen resolution; the void stays #000 inside the halo.
- Ground reads as paired cells, a lit cap over its shadow (pebbles, cobbles, tilled rows, planks); built walls are pillow blocks with plum seams.
- Many small warm sources (windows, lamps, a hearth) each pool their own light; between the pools the world sinks to the plum dark, never to grey.
- TODO 3-5 rules for this scene: which silhouettes must read, where rims fall, the built-in imperfections (a lean, a sag, a missing plank, a mismatched part) (see references/drawing.md#drawing-objects; run `pixelate style cosy-lightmap` for the style's rules).
- Silhouette keys: TODO for each must-read object, the 2-3 features that make it that thing and its nearest misread (a kite: tall diamond, visible spars, no belly band; not an envelope); crowds in 3 or more poses, gathered in vignettes.
- Light direction: TODO where the one key light comes from; every rim, lit side and shadow follows it.
- Wind: TODO its direction and strength, or none; every lean, trail, smoke and drift follows it.
- Every object is drawn in this scene's code from the primitives; anything the kit has no primitive for is a slot map. references/assets has finished examples to study, never to call.

## 4. The scene
- Projection: 3/4 top-down. Canvas 240x135.
- Hero: TODO x0,y0,x1,y1 (native px); peak value: TODO the object that alone holds the brightest values; peak chroma: TODO the object that alone holds the top chroma. A figure stays at least 40 px tall at the delivered cell; no other mass over 0.6x the hero's area or within 0.1 L of its peak (see references/drawing.md#composition).
- Planes: TODO each object or place and its share of the frame, with the grey band it takes in the block-in when you want it checked (darkest, dark, mid, light, brightest or 1-4; planes may share a band), e.g. street 45% (mid), sky 20% (light), houses 25% (dark), door wedge 10% (brightest); 3/4 top-down: the ground is the largest plane, at least 40%, and roofs show as planes seen from above.
- Layout: TODO what owns each region as boxes (x0-x1, y0-y1), the calm areas as boxes with what may sit in them; counts are maximums ("4 houses, no more").
- Masses: TODO three or four masses of very different size, with sizes (say 50%, 25%, 15% of the width), for every field that fills a band (cloud sea, sea, roofs, crowd, canopy); never an even row of equal lobes, domes or houses (see references/drawing.md#composition).
- Value plan: TODO three or four value groups with what falls in each and its L (far, middle, near, hero), one of them dark; the brightest group only at the one focal light and its one repeat; the budget keeps L > .8 to 2% of the frame, so a big lit shape (a door wedge, a beam) is brightest only at its source (near the door, at the lamp) and a step darker beyond it.
- TODO the full object list with counts and rough positions (left third, on the ridge, by the door) (see references/brief.md#4-the-scene; run `pixelate tools TOPIC` for each subject).

## 5. Lived-in details
- TODO five to ten small, specific things that tell a story, each with its native size (at least 4x3 px) and the value step against what it sits on; three readable beat eight invisible; say which change per phase (see references/drawing.md#drawing-objects).

## 6. Phases
- Accent ration: TODO each accent hue, the only objects that may carry it, and its share of the frame.
- TODO for each phase: the palette by named roles, its signature elements (not a recolour), what the music does in it (see references/drawing.md#phases and references/drawing.md#palette).
- Music: warm electric piano, soft drums and vinyl crackle; 4/4 swung, major sevenths, slow (70-80 bpm); under a bed of rain; sync point: a soft chime as a lamp flickers or a door opens. Direction only: write the track in code (guides/music.md); `pixelate check TRACK.wav --style lofi` judges it.

## 7. Light list
- TODO each emitter: what, where, colour, radius or width, flicker or pulse, what it lights, what hides it (each occluder opaque, partial with a float opacity, or gapped with slits) (see references/drawing.md#light; run `pixelate tools lamp --style cosy-lightmap`).
- Allowed light ops: lightmap, motes, sprite, from_world.

## 8. Motion table (TODO the loop length from section 1, frames at 12 fps)
- Motion: actors move in screen pixels at about 12 fps; every period divides the loop (anim.check_periods).
- TODO every moving thing with its frame count and rate; keep only a few things moving at once (see references/drawing.md#motion).
- Drifting layers (clouds, fog, water) make whole trips per loop: a 240 px trip in a 96-frame loop moves 30 px/s; clouds should feel 15 px/s or slower, so a slow drift wants a longer loop or a shorter tile, and every period still divides the loop.

## 9. Particles
- TODO kinds, sprite variants, densities, depth layers, paths (hashed spawns, whole trips per loop) (see references/drawing.md#motion; run `pixelate tools rain` or the topic for the weather).

## 10. Never
- screen-blend light.
- filters.
- a lifted void.
- Banned light ops: light:screen.
- TODO anything else this scene must not do (see references/brief.md#10-never; `pixelate style cosy-lightmap` lists the bans).

## 11. Technical
- Native 240x135, 2x nearest to 480x270; light layer at delivery size; about 45 colours in the pixel layer.
- Figures: chibi 6x13 (study references/assets/figures.py chibi), outlines per part, camera-following, drawn as your own slot maps.
- That size is already scaled from the style's 480x270 canvas to this 135-row one (x0.50 by native height).
- On screen the hero is about 26 px tall (13 native rows x 2); in a collage cell or a small embed it stays at least 40 px tall at the delivered cell size (see references/drawing.md#characters).
- Budget: L<0.1 0.1..0.45; L>0.8 <= 0.02; C>0.1 <= 0.03 (scene `exterior`: a night exterior: snow, a street, outdoors; provisional; the style's own: L<0.1 0.35..0.65; L>0.8 <= 0.006; C>0.1 <= 0.015).
- Gate: `pixelate check frame.png --style cosy-lightmap --scene exterior --scale 2` passes every line (redraw until it does); frame T equals frame 0; reads at 480 px wide (see references/delivery.md#gate).
- Gate overrides: none. If the scene cannot meet one bound, add a line `- Gate override: RULE <= V (the reason)` and pass `--brief` to the gate (see references/delivery.md#gate).
- Art director: `pixelate critique FRAME.png --brief brief.md` to a separate agent until it grades A (see references/delivery.md#art-director).
- Show the user one still for go/no-go; animate only after they accept it and confirm the motion table (see references/delivery.md#still and references/delivery.md#animation-plan).

Techniques for this style: albedo ramps sharing one plum dark (palette.ramp(style="plum"), palette.ramp(style="toy")); one smooth multiplied lamp map at screen resolution (post.Post(res="screen").lightmap); ground as paired cells (texture.pebbles); built walls as pillow blocks (layout.ashlar, texture.shade_cells); the edge into the void (shapes.void_edge); chibi figures as your own slot maps (study references/assets/figures.py chibi); rooms (compose.room).
Techniques for this subject (more: `pixelate tools TOPIC --style cosy-lightmap`; signatures: `pixelate tools MODULE.func`):
- rain and wet: rain as opaque streaks in palette slots, crowns where they land (fx.rain_cells, fx.rain_splashes, fx.splash_field); puddle rings and drips off the eaves (fx.ripple, fx.ripples, fx.drip); wet cobbles: speculars on up-facing edges (texture.wet_streaks); puddles mirror what stands over them (water.reflect); rain lit inside a lamp radius: alpha streaks with a stepped tail (fx.light_streaks).
- buildings: coursed stone: cells laid out, then carved (layout.ashlar, texture.shade_cells); bricks, panels, mottled plaster and trim (texture.bricks, texture.panels, texture.mottle, texture.inset_frame); roofs and walls: tiles with slipped and missing ones and moss, thatch, boards (texture.shingles, texture.thatch, texture.planks); cables and washing lines that sag (canvas.Canvas.catenary); boxes and gables seen from above with hard cast shadows (iso.Iso(camera='topdown'), iso.Iso.cast_shadows); lanterns, pipes, drains and barrels as slot maps with a lit edge (study references/assets/props.py lantern, pipe, drain, barrel).
- game level: jumps and hops (anim.arc, anim.hop), landing dust (fx.burst); layer scroll and tiles (canvas.parallax, canvas.Canvas.tile); HUD text (pixfont.draw); pickups and icons as small slot maps (study references/assets/glyphs.py stamp).
- small lights: lamps and lanterns as slot maps in warm slots (study references/assets/props.py lantern); flicker on held steps, passing t % T so the seam holds (light.flicker), and lamp-side rims (light.rim); marquee and signal lights (anim.chase); multiplied pools, walls blocking light with occlude= (occlude_soft=2 so thin strips only dim it) and per-light flicker in the light tuple (Post.lightmap).
- animals: each animal as your own slot map at the scene's size and pose: sit, sleep, walk, fly (study references/assets/figures.py cat, gull, quadruped_slim for the silhouette and the frame changes); birds circling and fish (anim.orbit), tails that lag (anim.lag), shadows on the slot grid (sprite.drop_shadow).
- steam and smoke: steam and smoke as hand-shaped plume sprites with a few drawings that rise and thin, never dotted squares (fx.smoke_puff, fx.trail); a curling column: 3-5 puffs spawned on a period that divides the loop, each rising with a stepped sway (anim.age, anim.stepped_sin); soft rising specks in a lamp pool (post.Post.motes).
Always: checks: the gate `pixelate check FRAME --style S --scale N` on every delivered frame (budget, native cells, palette, readability, craftcheck), `pixelate check SCENE` for engine scenes, anim.check_periods (every period divides the loop), compose.check_density for busy scenes.
