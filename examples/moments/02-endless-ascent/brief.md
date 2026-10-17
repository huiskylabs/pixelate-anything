# Endless Ascent: two moments (short scene brief)

Request: a vertical 270x480 lofi loop (delivered 4x, 1080x1920): a small gondola with one lantern-holding
passenger stays fixed at the screen centre while a 1200 px world strip (root caverns, trunk town, cloud sea,
thin air) scrolls down past it forever. This brief covers the two showcase stills and a 5 s sound sample.

## 0. Choices to confirm

- **intent**: a calm, wondrous phone wallpaper / lofi cover a stranger stops on: one small warm light climbing
  through an enormous cool world; it must never read as procedural filler or as a crop of somebody else's game.
- **style**: `lofi` (palette-step light, Bayer bands 10-16 rows, own-material outlines); runner-up `pastel-cell`
  rejected (it lifts the darks; the lantern needs a dusk-to-night key to be the only warm peak).
- **projection**: side, flat on; the cleft walls are seen face-on, depth by haze planes only.
- **moments**: A "The trunk town" (dusk-blue) and B "Above the cloud sea" (night). Same gondola, same screen spot.
- **figures**: the passenger (own design: a round-hooded coat, a muffler, a lantern on a short crook pole),
  three tiny townsfolk in A (3 poses), one cat in A. Nobody else.

## 1. Purpose and delivery
- Two stills for the showcase: out/02-a.png and out/02-b.png at 1080x1920 (270x480 native, 4x nearest),
  1x copies out/02-a@1x.png, out/02-b@1x.png, palettes out/02-a-palette.json, out/02-b-palette.json.
- Sound: sound/02-sample.wav (48 kHz, 16-bit, stereo, 5.0 s) and sound/02-sample.mp3.
- Seen full screen on a phone and as a thumbnail in a grid: the gondola and its lantern must read at 270 px wide.

## 2. Style and light regime
- Style `lofi`: no light layer; light is palette steps only (warm slots, rims, a few highlight pixels). No post ops.
- Ramps: hand-set OKLCh ramps, 4-6 steps per material, shadows cooler and more saturated, lights warmer and paler.
- Outline: own (each form lined in its own darkest step; the gondola and passenger in their wood0 / coat0).
- Dither: Bayer 4x4 only in sky and haze bands, transitions 10-16 rows; nowhere else.
- Learn the grammar of Lantern Isle only; copy no character, place, logo or UI. No text anywhere.

## 3. Art direction rules
- Everything is code: bark plates, cleft edges, cloud masses and the aurora are seeded masks; the gondola,
  passenger, lantern, cat, townsfolk, skiffs, kites, clock and crate are hand-typed slot maps.
- The cable is a sprite.chain-style rope: nodes 3 px apart on a long slack S-curve, 2 px wide, lay twists every
  3 px (lit pixel left, shade right), outlined in its own dark.
- Imperfections, named: the clock face sits 1 px off level in its rosette and has one chipped hour tick (the 4);
  one balcony rail is missing a baluster; the left laundry line sags lower on its left end; one window
  is boarded with two crossed planks; the gondola roof has one patched (lighter) shingle; one skiff kite in B has a
  torn corner; the cleft is wider at the top than the bottom and jogs, never a ruler line.
- Repeats are mismatched: windows come in 4 shapes (arched, round, square, slit) and 3 sizes with uneven spacing,
  garments differ in width (3-9 px) and spacing; cloud masses 55% / 30% / 12% of the width; stars in 3 kinds.
- Silhouette keys:
  - gondola: a peaked roof with eaves, a grip box with a pulley wheel on the cable above the roof, an open
    upper half showing the passenger, a planked lower half; not a lantern box or a birdhouse (the cable runs through it).
  - passenger: a round hood, a muffler tail trailing right, one arm out holding a crook pole with the lantern
    hanging free of the cabin; not a second lantern.
  - clock: a big round dial with 12 tick marks, two hands of different length, a carved rosette rim; not a
    porthole (the ticks and hands do that).
  - cat: two ear points, a sitting bean body, a tail curled down the crate side; not a jug.
  - pulley crate: a crate hanging on two ropes from a hoist arm with a wheel; not a window box.
  - kite sail (B): a tall diamond with a cross spar, a tether to the skiff bow, a tail of 3 bows; not an envelope.
  - skiff (B): a long low hull with an up-curved prow and a stub mast; not a leaf.
- Light direction: cool skylight from the upper left (rims on top-left edges, shadow on lower-right);
  the lantern is a local warm key at the gondola's right that lights only the gondola, the passenger's face and
  hand and nothing farther than 14 px.
- Wind: a light breeze from the left (west to east): laundry bellies right, the muffler and lantern flame lean
  right, kites fly right-up of their skiffs, cloud wisps tear off to the right.

## 4. The scene
- Projection: side. Canvas 270x480 for both stills.
- Hero: 114,200,164,268 (native px); peak value: the passenger's lantern; peak chroma: the passenger's lantern
- Planes: trunk walls 51% (dark), far haze in the cleft 28% (light), clock and carved fronts 19% (mid), gondola and lantern light 1.1% (brightest)
- Layout: A owns the frame with the trunk (two cleft walls, x 0-95 and 182-270 at mid height) and the cleft haze (x 95-182) with the gondola at x 116-162, y 200-266; B owns it with sky y 0-300, cloud sea y 300-480 and the same gondola box. Calm areas: A's haze strip above and below the gondola (only the cable, a far trunk and the crate in it) and the clock dial; B's sky band y 190-290 (only stars and the kite tethers in it).
- Layout A (moment "The trunk town"):
  - The colossal trunk fills the frame edge to edge, split by a natural vertical cleft: left wall x 0-~95,
    right wall x ~182-270 at the gondola's height; the cleft is 100 px wide at the top, 64 px at the bottom, with jogs.
  - Through the cleft, the far haze: a dusk-blue band sky, two far trunks (one wide, one thin), far branches with
    hazed leaf clumps, and three dim far windows of another tree town (1-2 px each).
  - The gondola at the screen centre x 116-162, y 200-266, the cable from y 0 to y 480 through it.
  - The clock: centre (58,238), dial radius 22 inside a carved rosette radius 28, on the left wall beside the gondola;
    hands at 8:10, the minute hand pointing up-right toward the gondola's grip.
  - Left wall: an arched door with a balcony (y ~150), a ladder from that balcony down to the clock ledge, a balcony
    with a hoist arm at y ~300 whose pulley crate hangs in the cleft at y ~318-334 with the cat on top, carved
    fronts with windows at y 20-120 and 360-470.
  - Right wall: two carved house fronts (y 60-170), a stair cut diagonally into the bark from y 170 to y 230, a
    balcony with a townsperson leaning on the rail watching the gondola (y ~262), a big carved front with uneven
    windows and a laundry line between two balconies (y 360-420), a landing with a sweeping townsperson at y ~455.
  - One laundry line crosses the cleft at y ~40 from a left balcony to a right balcony (behind the cable), 5 garments.
  - Calm areas: the haze strip in the cleft above and below the gondola (only the cable, one far trunk and the
    crate may sit in it); the clock's dial.
- Layout B (moment "Above the cloud sea"):
  - Night sky y 0-300 in Bayer bands (deep indigo top to blue-violet low), aurora curtains: one long curtain arcing
    over y 40-150 (x 20-250) and a shorter fold at y 120-190 on the right (x 150-262).
  - Stars in three kinds, hand-placed in clusters: dust (1 px dim, thickening toward the top edge), points
    (1 px bright, 2 px for a few), sparkles (5x5 four-point crosses, 5 only).
  - Cloud sea y ~300-480: masses of 55%, 30% and 12% of the width, overlapping in three depths (far small, mid,
    near huge); long flat tops, a lit top tier, a body, a deeper belly; the cable sinks into the huge mass.
  - Two kite-sailed skiffs: one at left (hull x 26-48, y ~322, kite at x 54-66, y 268-288) and a smaller far one
    at right (hull x 198-210, y ~350, kite x 216-224, y 322-334).
  - The gondola exactly where it is in A; a torn wisp curls off the cloud top under its floor.
- Masses A: the trunk walls (left 27%, right 24% of the area), the cleft haze (28%), the clock (2%); carved fronts
  differ in size (big 70x60, medium 50x40, small 30x26). B: cloud masses 55% / 30% / 12% of the width.
- Value plan: A: bark furrows and gondola wood L .14-.30; bark plates and carved fronts .32-.48; cleft haze, dial and laundry .40-.58; brightest only at the lantern (.70-.97). B: night sky .12-.26; aurora body and cloud bellies .30-.50; cloud lit tiers .52-.64; brightest only at the lantern.
- Value plan A (detail): dark group (L .14-.30): bark furrows, wall shadow sides, balcony undersides, doors, the gondola's
  wood; mid group (L .32-.48): bark plates, carved heartwood fronts, balconies, the clock rosette; light group
  (L .40-.58): the cleft haze, far trunks, the clock dial, laundry, lit bark rims; windows amber at L .50-.64;
  brightest (L .70-.97): only the lantern and what it lights on the gondola and passenger.
- Value plan B (detail): dark group (L .12-.26): night sky, the gondola wood; mid group (L .30-.50): aurora body, cloud
  bellies and far mass; light group (L .52-.64): cloud lit tiers, the aurora's lower hem, star points;
  brightest (L .70-.97): only the lantern and its pool on the gondola.

## 5. Lived-in details
- A: the cat on the pulley crate: cat 9x9 on a 12x9 crate, a dark cat against the light haze, 2 steps darker.
- A: a laundry line of 5 garments across the cleft, 3-9 px wide and 4-8 px tall, rose / teal / cream, 1-2 steps off the haze.
- A: a flower box under the round window, 8x3, a step lighter than the bark, three 1 px blooms.
- A: a boarded window, 6x8, two crossed planks a step lighter than the dark glass.
- A: a townsperson sweeping the bottom landing, 11 px, broom 6 px; a watcher leaning on the right rail, 10 px,
  rimmed by the window behind him; a third climbing the ladder, 11 px.
- A: a pail on the clock ledge, 4x4, a step lighter than the ledge.
- B: the near skiff's torn kite corner (a 3 px notch); a tiny pilot (6 px) at the tiller; a coil of rope on the
  deck, 4x3, a step lighter than the hull.

## 6. Phases (two moments of one loop)
- A, dusk-blue: haze blues (deep dusk blue to lilac), bark in indigo-violet-brown, heartwood rose-tan, built timber
  brown, windows amber (lower than the lantern), laundry rose / teal / cream, clock dial cool grey-blue.
  Signature: the clock face, laundry across the cleft, uneven lit windows, the cat on the pulley crate.
- B, night: sky deep indigo to blue-violet, aurora teal-green with a violet upper fringe, clouds blue-lilac
  (lit tier pale lilac, belly deep slate), skiff hulls dark teal-brown, kite sails muted rose and sand.
  Signature: the aurora curtains, three kinds of stars, the cloud masses, the kite-sailed skiffs.
- Accent ration: warm yellow-orange (C over .12) only on the lantern and its pool on the gondola (under 1.5% of
  the frame); amber windows in A at C .08-.12 (about 1.5%); aurora teal only in B's sky (under 8%).
- Music: lofi, 76 bpm, D major: plucked guitar lead, Rhodes comp on Dmaj9 - Bm9 - Gmaj9 - A13, swung drums with a
  light snare, a leaves-and-wind bed, vinyl crackle low. Sync point: one low warm clock-bell strike (own synth,
  3 inharmonic partials, long decay) about 1 s into the sample as the gondola passes the clock.

## 7. Light list
- The lantern: a 6x9 slot map (cap, glass, flame, base) on a crook pole at the gondola's right; flame core lamp3
  (2 px), glass lamp2, halo ring lamp1/lamp0 one pixel wide; it lights the passenger's face and hand, the cabin's
  right post and roof underside in the gwarm steps; no pool on the trunk (it is too far).
- A windows: 11 windows, 6 lit (amber win1-win3 inside a win0 frame), 5 dark, the lit ones never brighter than
  L .64; the watcher on the right balcony gets a 1 px win1 rim from the window behind him.
- A far town: 3 dim far windows (win0, 1-2 px) on the far trunk.
- B: the aurora is not a light source on anything; cloud tops take a cool top tier from the sky.

## 8. Motion table (for the loop; the stills are frame 0)
- World scroll: 1200 px per loop, whole pixels, 1 px every 2 ticks (a 40 s loop = 1200 ticks).
- Lantern flame: 4 drawings at 10 fps on a hold table [0,0,1,2,2,1,3,1] (8 steps x 3 ticks = 24 ticks, divides 1200).
- Muffler and laundry: 2 drawings at 2 fps (2 x 15 ticks = 30 ticks).
- Cat tail flick: 3 drawings, once per 240 ticks (8 s).
- Star twinkle: 2 tones on 200-tick holds (6.7 s, divides 1200).
- Kite sails: 2 drawings at 2 fps; skiffs drift one whole trip per loop.

## 9. Particles
- A: none in the still. B: star dust is static flecks (no particles); a few cloud wisp shreds as shapes.

## 10. Never
- glow blur, bloom, lens effects, soft shadows; any light op (light, glow, shaft, fog, motes...).
- narrow gradient bands that read as stripes; noise textures on bark; rows of equal cloud lobes; stamped windows.
- any warm value brighter than the lantern; text, logos, borrowed characters.

## 11. Technical
- Native 270x480, 4x nearest to 1080x1920; one strict palette per still (about 60-80 slots), every pixel a slot.
- Gate: `pixelate check out/02-a.png --style lofi --scale 4 --brief brief.md --pal out/02-a-palette.json`
  (and the same for 02-b), plus `--intent` for the deliberate star flecks in B.
- Block-in: `pixelate check out/blockin-a.png --blockin --brief brief.md` before drawing; B: `--brief brief-b.md` (same Hero line, B's Planes line).
- Value budget (lofi): at most 1% of the frame below L .1, no exact black, at most 4% at L .7 or above and 2%
  above L .8 (only the lantern and its pool), median chroma .02-.1.
- Gate overrides: none.
