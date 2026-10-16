# Craft: making it look hand-made

These rules apply to every mode: scenes, sprites, tiles, and finishing a pixelated image.

These are the rules that separate a scene a pixel artist would sign from generic
"AI pixel art". They come from building Lantern Isle, from measuring ten reference games
(`guides/styles.md`), and from fixing everything that looked wrong along the way.

## Write the brief first

A scene is only as good as its brief. Lantern Isle came out almost in one pass because its
brief (`examples/lantern-isle/BRIEF.md`) decided everything before a pixel was placed: the
art rules, every object, the lived-in details, a palette and signature elements per phase,
motion rates, and the technical numbers. Write every new scene's brief to that density, show
it, and only then build. If you can't fill a section, you don't know the scene yet.

### From one line to a brief

Users usually give one line: "make me a pixel island". Turning that line into a brief at the
density of `examples/lantern-isle/BRIEF.md` is the skill's main job. That brief is the floor, not
the ceiling: it predates the light layer, so a brief today also decides the light regime and every
emitter, the allowed post ops, the value budget and the depth planes, which Lantern Isle never had
to. Do it in this order, before drawing anything:

1. **Read the intent, then route.** Before any tool, write one line on what the user most
   likely wants but didn't say: the feeling (calm, epic, eerie, cute), the use (a stream cover, a
   game mock, a wallpaper), the era or game it recalls, and what would disappoint them. "A pixel
   island" from someone making lofi videos is a calm diorama with seasons; the same words from a
   game developer are a top-down overworld tile. Then run `python3 tools/route.py "the request"`.
   It ranks the styles with reasons, names the mode (scene, rebuild, era, assets, music), suggests
   the kit calls for the subject, and lists what the request leaves open with defaults. It matches
   keywords, so it is a hint, not the decision: choose with the questions in "Picking a style"
   (`guides/styles.md`) and your read of the intent, and say why in section 0.
   Know the whole kit, not only what the router names: `guides/toolkit.md` lists every function
   with one line on what it does, by subject and by module. The best brief reaches for whatever
   the scene needs (a scarf on `sprite.chain`, wet cobbles from `texture.wet_streaks`, a crowd from
   `compose.populate`) and names each by its real function.
2. **Expand.** `python3 tools/route.py "the request" --brief -o brief.md` writes the 11 sections
   with everything the style decides already filled in, plus section 0, the choices to confirm.
   Fill every TODO yourself with a concrete choice: the objects with counts and positions, five to
   ten lived-in details, the palette by named roles, every light, every motion rate. Invent the
   specifics the user didn't give; never leave them to the user.
3. **Self-critique.** `python3 tools/route.py --lint brief.md` flags TODOs left, thin or missing
   sections, vague words, a motion table without numbers and periods that don't divide the loop.
   Then read the brief against Lantern Isle's: would it build at least that quality in one pass? Is
   every object specific enough to draw, every imperfection named, every phase more than a
   recolour? Fix what falls short and lint again.
4. **Confirm.** Show the user the brief with section 0 on top: "these are the choices I made; say
   OK, or change any line". One OK should be enough to build. If they change something, revise
   the brief and show only what changed. Build only from an approved brief.

The brief has these sections. Each one is concrete: names, counts, positions, colours, rates.

1. **Purpose and delivery.** What it is for (a video cover, a game key art, a showcase of one
   style), the loop length, the outputs (MP4, GIF, page, still) and where it will be seen
   (full screen, a thumbnail, a README).
2. **Style and light regime.** One preset from `tools/styles.py` (or `lofi`), and what that
   fixes: light layer `none`, `native` or `screen`, the blend, the ramp style, the outline
   mode, the dither vocabulary, the value budget. Name the reference style it learns from and
   what it must not copy (characters, places, logos, UI layouts).
3. **Art direction rules.** Six to ten rules written for this scene, not generic ones: how
   objects are authored (slot maps, seeded shapes), where anti-aliasing and dither are allowed,
   which silhouettes must read, where rim light falls, which imperfections to build in (a leaning
   tree, a sagging roof, a missing plank, a mismatched shutter).
4. **The scene.** Camera and projection, what fills how much of the frame, the horizon line,
   and the full object list with counts and rough positions (left third, on the ridge, by the
   door). Name the subject and the calm areas where the eye rests.
5. **Lived-in details.** Five to ten small, specific things that tell a story: a cat on the
   sill, a mug on the rail, firewood by the wall, a patched tile, a worn path. Say which change
   per phase.
6. **Phases.** For each: a palette written as named roles ("misty teal sky, sage canopy, blossom
   pink, warm amber windows"), its signature elements (things only it has, not a recolour), and
   its music if there is any.
7. **Light list.** Every emitter: what it is, where, its colour, its size or radius, how it
   moves or flickers, and what it lights or what hides it (the near plane, a door frame).
8. **Motion table.** Every moving thing with its rate and frame count: "flames 4 frames at
   10 fps on a hold table; trees sway 2 frames at 2 fps; clouds one trip per loop; a character
   cycle of 4 drawings held 3 ticks". Every period must divide the loop.
9. **Particles.** Kinds, sprite variants, densities, depth layers and paths (petals on irregular
   paths in 3 variants, about 200 rain streaks at 480x270 in two layers).
10. **Never.** What this scene must not do: the effects its style bans, symmetry, clutter, text,
    people (if so), anything that would make it read as a filter.
11. **Technical.** Native canvas, scale to the delivered size, fps, loop length in frames, palette
    size, and the checks it must pass (`styles.check`, the loop seam, a thumbnail test).

Then build in the order of the brief, and look at every step at zoom.

## Light: palette steps or a code light layer

The pixel layer is always strict: every pixel is a palette slot on the integer grid. Light comes
in one of three regimes, one per scene (`guides/styles.md` has the measurements):

- **None** (`lofi`, `arcade`, `tactics`, `sticker-iso`, `illustrated`). Light is a palette swap,
  never a blend. Window glow, lantern pools and rim light are drawn with the warm slots, with a
  few deliberate highlight pixels. No glow blur, bloom or soft shadows. Lantern Isle is this.
- **Native** (`pastel-cell`, `native-glow`, `hd-overworld`, `neon-noir`). A light layer is
  computed once per art pixel from the scene's own masks (`tools/post.py`, `res='native'`) and
  scaled up last, so even the glow comes in whole pixels.
- **Screen** (`contre-jour`, `cosy-lightmap`). The light layer is smooth inside each art pixel,
  composited between depth planes so near silhouettes stay flat dark (`post.Stack`).

Whatever the regime, light is code: a pure function of masks, positions, t and a seed, never
painted in an editor. Mixing regimes in one frame makes it read as a filter. Vignette, grain,
scanlines and chromatic aberration stay off unless the preset lists them.

## Palette

- **One strict palette per phase.** Write the palette before drawing: the palette *is* the mood. Roughly 40 to 80 slots for a full scene.
- **3 to 5 tones per material.** Shift the hue across the ramp: shadows move toward blue or purple and get more saturated, lights move toward yellow or orange and get less saturated. A ramp that only changes brightness looks dead. `palette.ramp(base, steps, style=...)` builds the measured ramp shapes (`lofi`, `rise`, `arch`, `flat`, `living`, `lit`, `plum`, `window`, `toy`, `arcade`).
- **No pure black or white.** The darkest dark carries the scene's hue (a night sea's black is deep teal). Styles that measure a true black (`neon-noir`) say so.
- **Ration chroma and highlights.** The top chroma belongs to the actor or the one interactive prop; the brightest values sit at the focal point. Check the numbers with `styles.check` (for example, contre-jour keeps L>0.75 under 0.1% of the frame).
- **Slots keep their role across phases.** `F2` is "roof, mid tone" in every season, so one roof sprite works everywhere and the phase dissolve stays coherent.
- **Use dynamic slots for flicker.** In `sceneDynamic`, remap warm slots with `flick()`, held for 3 to 5 steps at 10 fps. The steadiness is what makes flame read as flame.

## Gradients

- In the `lofi` style, skies and seas are bands of solid colour with **wide dithered transitions** of 10 to 16 rows (`bands()`, using the third value of each stop). Narrow transitions read as stripes.
- In the pastel and HD styles, skies are flat undithered strata locked together by tapered wisps (`sky.strata`, `sky.wisp`, `sky.smile`). The boundary walks in flat runs joined by 1 px steps.
- Seas get darker toward the viewer, with lighter swell streaks drifting slowly (`water.depth_bands`, `water.foam_rings`).
- **Reflections** mirror the objects into darker slots (a reflect map, `water.reflect`), with a stepped wobble and moving ripple gaps. Lights stay bright in the reflection; everything else fades with distance.

## Drawing objects

- **Outline and lit side.** Choose one light source and keep it everywhere. Outline with the darkest tone of the material, not with black (`Canvas.outline` modes: own, part, selective, slot). Put lit edges on the side facing the light. Styles differ: scenery in `pastel-cell` has no outline and only the actor does; `contre-jour` figures have none at all.
- **Canopies are clumps.** Draw 6 to 12 overlapping lobes, each with a lit upper rim, a mid body and a dark underside (`texture.clumps`, `veg.lobe_light`, `veg.leafmass`). Leave holes for sky. Never a ball with noise on it.
- **Roofs are courses of shingles**, offset row by row, with the odd patched tile. Uniform tiles read as a brick wall.
- **Materials are shaped units, never raw noise:**
  - Stone as cells with a lit rim and a dark seam (`layout.ashlar`, `layout.polar_blocks`, `texture.shade_cells`).
  - Floors as pebbles with a lit cap over a shadow (`texture.pebbles`).
  - Cliff rock as stacked flake dashes over ledged, frayed silhouettes (`texture.flakes`, `shapes.ledges`, `shapes.fray`).
  - Hand-shaped boulders with a highlight and a shadow each, strata seams, roots, the odd stone poking out.
- **Clouds are flat masses**, an ellipse core with perimeter lobes, a lit top tier and a deeper belly (`shapes.cloud_mass`, `shapes.cloud`). Loose discs read as bubbles.
- **Smoke and mist are hand-shaped:**
  - Smoke is a plume sprite with a few frames (`fx.smoke_puff`, `fx.trail`).
  - Mist is long streaks of one or two tones.
  - Never dotted squares or noise.
- **Light pools are hand-shaped masks** on the ground, never circles.
- **Lived-in details carry the scene.**
  - Examples: a cat on a sill, a mug on the rail, laundry, firewood, boots by the door, a worn path, a kite, a rake, pumpkins, a wreath.
  - Three to six small props per phase say more than one big effect.
- **Asymmetry and hand placement.** Pick coordinates yourself. Spread things unevenly in clusters, and let nothing line up by accident.
- **No tool for it? Build it in code anyway.** The kit's functions are shortcuts, not the limit. Anything the scene needs (a lobster pot, a kite, a tram, a cat in a pose no function has) is a slot map you write: a silhouette from `canvas.Canvas` shapes or a hand-typed grid, the material's ramp, an outline mode, a lit edge on the light side, then the same checks as everything else (reads at 1x, clean clusters, no orphan pixels). Name it in the brief as "slot map" with its size and parts. If the same object keeps coming back across scenes, that is when it becomes a tool.

## Characters

- **Readable at native size first.** A 13x18 chibi, a 20-px slim figure with 1 px legs or a 3.3-head iso person must read before any light is added (`figures.chibi`, `figures.slim`, `figures.iso_person`). Look at it at 1x.
- **The actor carries the frame's top chroma** and, in styles that outline, the only dark outline in the frame.
- **Trailing parts are chains.** Scarves, hair and tails are a rope of nodes a fixed distance apart, pulled toward where the anchor was a few frames ago plus the wind (`sprite.chain`). A chain that stretches with speed reads as a stick.
- **State shows in colour.** A dash spent, a power charged: a ramp swap on the hair or scarf, one white frame at the change, never more.

## Phases

- Each phase needs **signature elements** that only it has, not just new colours. Lantern Isle's:
  - Spring: rain, blossom, petals and a puddle.
  - Summer: fireflies, a hammock and a lighthouse beam.
  - Fall: falling leaves, chimney smoke, mist, pumpkins and birds crossing the moon.
  - Winter: snow on every surface, icicles, embers and an aurora.
- **Overlay sprites keep variants consistent.** Draw a snow layer laid over the roof, a bare tree under a snow overlay, a fall leaf layer on the ground. Don't redraw objects from scratch per phase.
- The dissolve between phases is a weather front of dither. Good palettes make it look like time passing.

## Motion

- **Step everything.**
  - Hand-animated rates: trees sway at 2 fps, flames at 10, flags and laundry at 2 to 4, clouds and mist at 15 px/s or slower.
  - Weather particles may move every tick, because rain is fast.
  - Smooth 30 fps easing looks like software; stepped motion looks drawn.
- **Use few frames.** Blinks, flicks and waves take 2 to 6 frames. Give each its own hold timings from a hand-written table (`[0, 0, 1, 1, 1, 0, ...]`, `anim.hold`). A sequence of beats is an `anim.Timeline`.
- **Keep motion sparse.** At any moment only a few things should move. A calm frame with one blinking light is better than everything wiggling.
- **Every period divides the loop.** `anim.check_periods` lists the ones that don't. Drifting layers make whole trips per loop (`anim.wrap_offset`).
- **Particles:**
  - Use 2 or 3 depth layers: far ones small and dim, near ones larger and brighter.
  - Densities that look right: about 200 rain streaks or 300 snowflakes on a 480x270 canvas in the `lofi` style. The pastel style uses about 30 opaque 1 px streaks at 320x180; contre-jour about 18 hairlines.
  - Spawn them from hashed positions per generation, never from a fixed grid.
  - Bursts, sparks and debris come in hard cells that shrink as they age (`fx.burst`, `fx.sparks`, `fx.debris`).

## Composition

- The subject fills about 40 to 60% of the frame width, and the horizon sits about two-thirds of the way down.
- Leave calm areas (sky, water) for the eye to rest and for the title on a thumbnail.
- Frame with planes: a dark near plane (a tree, a monolith, a bush band) in front of a lit middle and a hazed far plane gives depth (`compose.proscenium`, `compose.stage`, `palette.haze`).
- **Test at the delivered size and at thumbnail size.** If the subject reads as a speck at 320x180, crop in or move to a smaller canvas.

## Failure checklist (look at shots at zoom 3-4 for each)

The gate measures most of these: `pixelate check FRAME.png --style S --scale N` (add `--pal`, `--pre`, `--actor`, `--used`) must print ALL PASS before a frame is final; engine scenes also run `pixelate check SCENE`. The rest is judged by eye.


- [ ] Any colour outside the palette, or blur in the pixel layer? There should be none: light belongs in the light layer, and only in styles that have one.
- [ ] Sky or sea reads as stripes: widen the dither transitions, or walk the strata boundaries.
- [ ] A canopy reads as a ball, a roof as a brick wall, rock as noise: redraw with clumps, offset courses, shaped cells.
- [ ] Smoke, mist or light reads as dots or squares: hand-shape it.
- [ ] A trailing scarf or tail reads as a stick: shorten the chain and fix its segment length.
- [ ] Too busy: cut particles and motion.
- [ ] Subject too small, or empty half-frame: recompose.
- [ ] A phase only looks like a recolour: add signature elements.
- [ ] The frame breaks its style's budget or craft limits (orphans, jaggies, stripes, doubled outlines, pillow shading, clusters): `pixelate check frame.png --style STYLE --scale S`.
- [ ] The seam jumps at loop end: `pixelate check` flags it in engine scenes; in Python scenes compare `frame(T)` with `frame(0)`.
- [ ] The brief has a section you skipped: go back and write it.
