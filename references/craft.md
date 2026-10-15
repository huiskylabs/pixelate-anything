# Craft: making it look hand-made

These are the rules that separate a scene a pixel artist would sign from generic
"AI pixel art". They come from building Lantern Isle and fixing everything that
looked wrong along the way.

## Palette

- **One strict palette per phase.** Write the palette before drawing: the palette *is* the mood. Roughly 40 to 80 slots for a full scene.
- **3 to 5 tones per material.** Shift the hue across the ramp: shadows move toward blue or purple and get more saturated, lights move toward yellow or orange and get less saturated. A ramp that only changes brightness looks dead.
- **No pure black or white.** The darkest dark carries the scene's hue (a night sea's black is deep teal).
- **Slots keep their role across phases.** `F2` is "roof, mid tone" in every season, so one roof sprite works everywhere and the phase dissolve stays coherent.
- **Light is a palette swap, never a blend.** Window glow, lantern pools and rim light are drawn with the warm slots.
- **Use dynamic slots for flicker.** In `sceneDynamic`, remap warm slots with `flick()`, held for 3 to 5 steps at 10 fps. The steadiness is what makes flame read as flame.

## Gradients

- Skies and seas are bands of solid colour with **wide dithered transitions** of 10 to 16 rows (`bands()`, using the third value of each stop). Narrow transitions read as stripes.
- Seas get darker toward the viewer, with lighter swell streaks drifting slowly.
- **Reflections** mirror the objects into darker slots (a reflect map), with a stepped wobble and moving ripple gaps. Lights stay bright in the reflection; everything else fades with distance.

## Drawing objects

- **Outline and lit side.** Choose one light source and keep it everywhere. Outline with the darkest tone of the material, not with black. Put lit edges on the side facing the light.
- **Canopies are clumps.** Draw 6 to 12 overlapping lobes, each with a lit upper rim, a mid body and a dark underside. Leave holes for sky. Never a ball with noise on it.
- **Roofs are courses of shingles**, offset row by row, with the odd patched tile. Uniform tiles read as a brick wall.
- **Rock and soil:**
  - Hand-shaped boulders with a highlight and a shadow each.
  - Strata seams.
  - Roots, and the odd stone poking out.
- **Smoke and mist are hand-shaped:**
  - Smoke is a plume sprite with a few frames.
  - Mist is long streaks of one or two tones.
  - Never dotted squares or noise.
- **Light pools are hand-shaped masks** on the ground, never circles.
- **Lived-in details carry the scene.**
  - Examples: a cat on a sill, a mug on the rail, laundry, firewood, boots by the door, a worn path, a kite, a rake, pumpkins, a wreath.
  - Three to six small props per phase say more than one big effect.
- **Asymmetry and hand placement.** Pick coordinates yourself. Spread things unevenly in clusters, and let nothing line up by accident.

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
- **Use few frames.** Blinks, flicks and waves take 2 to 6 frames. Give each its own hold timings from a hand-written table (`[0, 0, 1, 1, 1, 0, ...]`).
- **Keep motion sparse.** At any moment only a few things should move. A calm frame with one blinking light is better than everything wiggling.
- **Particles:**
  - Use 2 or 3 depth layers: far ones small and dim, near ones larger and brighter.
  - Densities that look right: about 200 rain streaks or 300 snowflakes on a 480x270 canvas.
  - Spawn them from hashed positions per generation, never from a fixed grid.

## Composition

- The subject fills about 40 to 60% of the frame width, and the horizon sits about two-thirds of the way down.
- Leave calm areas (sky, water) for the eye to rest and for the title on a thumbnail.
- **Test at the delivered size and at thumbnail size.** If the subject reads as a speck at 320x180, crop in or move to a smaller canvas.

## Failure checklist (look at shots at zoom 3-4 for each)

- [ ] Any colour outside the palette, or blur? There should be none: the engine only outputs palette colours, so look for raw RGB in particles.
- [ ] Sky or sea reads as stripes: widen the dither transitions.
- [ ] A canopy reads as a ball, or a roof as a brick wall: redraw with clumps or offset courses.
- [ ] Smoke, mist or light reads as dots or squares: hand-shape it.
- [ ] Too busy: cut particles and motion.
- [ ] Subject too small, or empty half-frame: recompose.
- [ ] A phase only looks like a recolour: add signature elements.
- [ ] The seam jumps at loop end: `check.py` flags it; find the period that does not divide `TICKS`.
