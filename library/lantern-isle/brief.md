# Lantern Isle: the original brief

The prompt that produced this scene and its soundtrack almost in one pass. It is the bar for the
density of a scene brief: every rule, object, detail, palette, motion rate and technical number is
written down before anything is drawn. See `references/brief.md`, "Write the brief first".

---

Make an animated pixel-art diorama of a small island in a calm sea, built to be the looping cover for a 10-hour lofi music video, with its own generative lofi soundtrack that changes with the seasons.

Art direction: It must look hand-pixeled by a skilled artist, at the quality of hand-crafted indie game key art, with no AI or procedural feel.
- Draw every object as a hand-authored sprite (pixel maps defined in code), not shapes built from circles, rectangles, or math curves.
- Use a strict limited palette per season and manual pixel techniques: selective anti-aliasing, clean pixel clusters, no stray single pixels, no pillow shading, no smooth gradients. Use dithering only where it adds texture, such as in the sky and water.
- Give careful silhouettes so every shape reads clearly, and use soft rim lighting where warm light hits cool surfaces. Favor restraint and atmosphere over clutter.
- Avoid symmetry and perfection. Trees lean slightly, the roof sags a little, shutters don't match, the dock has a missing plank, rocks have uneven edges.
- Animate with stepped, frame-by-frame timing (3 to 6 frame cycles at about 8 to 12 fps for flames, leaves, and water) instead of smooth interpolation. Motion should feel drawn, not simulated.
- Hand-place particles and vary them: petals, leaves, and snowflakes use several small sprite variants with irregular paths, not uniform random sprays.
- No glow blur, bloom, lens effects, or soft shadows. Express light with color shifts and a few deliberate highlight pixels.
- Add lived-in storytelling details: a worn path to the door, a patched roof tile, firewood stacked by the wall, a laundry line, a cat sleeping on the windowsill, a mug on the porch rail, and small items that change with each season.
- Keep a consistent pixel scale everywhere; nothing drawn at a different resolution.

Scene: A fixed, centered side-on view of one small island with a cozy cottage (chimney, glowing windows, small porch), two or three trees, a little dock with a rowboat, a lantern post, and a garden patch. Gentle waves lap the shore, and the sea reflects the sky and the window light. The island fills roughly the middle 60% of the frame.

Seasons: The scene cycles through spring, summer, fall, and winter, about 90 seconds each, with soft 10-second crossfades in both visuals and music. Winter blends back into spring so the cycle loops seamlessly. All seasons are set at twilight or night so the warm cottage glow always contrasts with a cool sky and sea.

- Spring
  Palette: misty teal, sage green, blossom pink, warm amber windows.
  Elements: soft rain, cherry blossoms, falling petals, a puddle shimmer on the dock, a small kite tied to the porch.
  Music: Fmaj7 / Em7 / Dm7 / Cmaj7, light Rhodes piano, gentle rain ambience, around 72 BPM.

- Summer
  Palette: deep indigo sky, magenta-orange horizon, lush green, golden lantern light.
  Elements: fireflies, full canopy, a hammock between trees, sparkles on the water, a distant lighthouse beam sweeping the sea.
  Music: Dmaj9 / Bm7 / Gmaj7 / A6, warm guitar, soft cicadas and waves, around 78 BPM.

- Fall
  Palette: dusky violet, burnt orange, rust red, honey-yellow windows.
  Elements: drifting red and orange leaves, chimney smoke, low mist on the sea, pumpkins on the porch, a few migrating birds crossing the sky.
  Music: Am9 / Fmaj7 / Dm9 / E7, muted piano, wind and rustling leaves, around 70 BPM.

- Winter
  Palette: cold navy, icy blue, snow white, deep fire orange.
  Elements: falling snow, snow on the roof and trees, icicles on the eaves, frost on the shore, a bright fireplace glow, faint aurora in the sky.
  Music: Cmaj7 / Am7 / Fmaj7 / G6, sparse music box and pad, crackling fire, around 66 BPM.

Music: Generate the lofi soundtrack procedurally with the Web Audio API: soft drums with swing, a warm bass, the seasonal chord progression and instrument, light vinyl crackle, and seasonal ambience. Add small random variations in melody and drum fills so it doesn't feel repetitive over hours. Start audio on a single click (browsers require it) with a clean play button that hides afterward.

Motion: Keep everything slow and calm. Subtle ambient effects throughout: flickering window light, drifting smoke, swaying trees, rippling water, and the seasonal particles. No sudden movement, no text, no people.

Technical: Render at a native 480x270 pixel canvas, scaled 4x with nearest-neighbor to a crisp 1920x1080. Run at a steady frame rate and loop smoothly for hours without drift, audio glitches, or visible seams. Deliver it as a single self-contained HTML page with a canvas.