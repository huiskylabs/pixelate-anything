# Drawing: making it look hand-made

Step 5 of every job: draw everything from scratch in code. These rules apply to every mode:
scenes, sprites, tiles, and finishing a pixelated image. Read the section for what you are drawing.
The brief comes first ([brief.md](brief.md)); the gate, the still and the animation plan come after
([delivery.md](delivery.md)).

These are the rules that separate a scene a pixel artist would sign from generic
"AI pixel art". They come from building Lantern Isle, from measuring ten reference games
(`guides/styles.md`), and from fixing everything that looked wrong along the way.

## Draw from scratch in code

Draw with the primitives, in the order of the brief. The tools in `tools/` are drawing primitives
with no look of their own (canvas and slot grid, palettes and ramps, outlines, dither, shapes and
masks, material textures, light layers, projections, animation timing) plus the checks. Find them
with `pixelate tools` (topics and modules), `pixelate tools TOPIC` (the techniques for rain, fog,
water and the rest) and `pixelate tools MODULE` or `MODULE.func` (signatures and docstrings).
Finished objects in `references/assets/` (boats, cats, props, runes, particle sprites) are examples
to read, never call (`references/assets/README.md`). Anything missing is a slot map you write.

## Rules for every mode

- **Palette first, and keep it strict.**
  - Each material gets 3 to 5 hue-shifted tones: shadows cooler, lights warmer.
  - The same slot names keep the same meaning everywhere.
  - Use no colour outside the palette, and no blur, anti-aliasing or alpha blending.
- **Draw it yourself, in code.** Never paste or trace an image, and never call a finished object from `references/assets/`; read it, then draw your own at the scene's size and style.
- **Hand-place and keep it asymmetric.** Pick positions yourself; uniform scatter and symmetry read as generated.
- **Outlines and one light direction.** Every form has a dark outline from its own ramp, a lit side and a shadow side.
- **Look at every preview at zoom.** The usual failures are mush, noise, stripes, a subject too small, and a recolour sold as a variation. Fix them before adding more.

The tools handle the mechanical parts (colour maths, exact loops, exports). The quality comes from
the art decisions and from looking at every preview at zoom.

## Light

Palette steps or a code light layer.

The pixel layer is always strict: every pixel is a palette slot on the integer grid. Light comes
in one of three regimes, one per scene (`guides/styles.md` has the concepts; `pixelate style NAME` prints one style's regime and numbers):

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

- **Readable at native size first.** A 13x18 chibi, a 20-px slim figure with 1 px legs or a 3.3-head iso person must read before any light is added. `references/assets/figures.py` (`chibi`, `slim`, `iso_person`) shows how each is built; read it, then draw your own. Look at it at 1x.
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

## Examples to study

- `examples/san-francisco`: an aerial photo rebuilt in its own 3/4 camera and as an isometric diorama, day to night. The quality bar for rebuilds.
- `examples/projections`: one scene in the five projections (side, 3/4 top-down, 2:1 iso, oblique, military).
- `examples/retro`: original classic-genre screens under console-era limits (8-bit platformer, Game Boy-style RPG, title screen).
- `examples/lantern-isle`: a 4-season loop, the quality bar for scenes.
- `examples/meadow-kit`: a hero, items, an autotile set and a map.
- `examples/gallery`: what the `demo/` scripts make through the CLI and the MCP server.
