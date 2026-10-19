# 05 Four Machines: brief

## 0. Choices to confirm

- Intent: a showcase still people stop on. One original moment drawn four times, each time designed for its machine, so the comparison itself is the delight. What would disappoint: one picture palette-snapped four times, a glider that reads as a bird or a plane, mush at 3x.
- Mode: era (guides/eras.md), four presets: gameboy, nes, snes, gba. Craft limits from `lofi`; each era replaces the value budget.
- The moment: a young postmaster launches a canvas mail-glider off the rail of a cliff-top post office at sunrise. The glider has just left the end of the rail, nose lifting; below, a fishing town in a cove is waking (a few lit windows, one boat leaving the harbour); three gulls cross. The same instant in every panel.
- Sound: an original 8-bar lift-off theme, 116 bpm, D major, 16-bit arrangement; a 5.0 s excerpt of its rising phrase.

## 1. Purpose and delivery

- Image A `out/05-a.png`: a 2x2 poster, every panel at 3x (480x432, 768x672, 768x672, 720x480) on a dark mat, captions in pixfont: 4-SHADE HANDHELD, 8-BIT CONSOLE, 16-BIT CONSOLE, 32-BIT HANDHELD; title ONE MORNING, FOUR MACHINES.
- Image B `out/05-b.png`: the 16-bit panel alone at 4x (1024x896).
- 1x panels `out/panel-{gb,nes,snes,gba}.png`, background-only layers `out/panel-*-bg.png`, gate copies `out/panel-*@4x.png`.
- Seen as a README/gallery image: it must read at thumbnail size (glider, post office, sun, town).

## 2. Style and light regime

- Era mode, light regime none: light is palette steps per machine; no light layer, no blending, no blur.
- Learns from library/retro-screens (Rooftop Run, Island Village, Pixel Harbor): read, never imported. Copies no game, character, logo or UI layout; captions name no console.

## 3. Art direction rules

- Every object is drawn in code per panel at that panel's size: the glider, pilot, post office and houses are separate slot maps per machine (never one drawing scaled).
- The glider is the light shape on the darkest ground: the cove's back wall (the crag) sits directly behind it in every panel.
- Houses are mismatched: 7 houses (a tall narrow townhouse, a squat cottage, a flat roof with a parapet, a steep gable, a net shed with a sagging ridge, a two-storey with a lean-to, the harbour inn), chimneys on two, window rhythm differs per house.
- Waves are short leaning dashes, 3-6 per row, steep face toward the sun, never a stamped row; the sun's glitter path narrows toward the horizon.
- Clouds: one long flat bank with a lit underside and two lobes of very different size, plus one small wisp. No bubble rows.
- Cliff rock: irregular angular facets, each with a lit sun-side edge; dark fractures run up and down, lit lips run across; a few ledges carry grass tufts.
- Named imperfections: a missing tie on the rail, a patched pane on the post office, the sagging ridge on the fisherman's shed, one dark window in a lit row, a chipped corner on the harbour mole.
- Silhouette keys: GLIDER = a shallow delta canvas wing seen slightly from below: a dark leading-edge spar running to two clean points, 3-4 battens a side showing through the cloth, a darker underside panel (not a bird's bent wing), an A-frame control bar under its centre with the pilot hanging, legs dangling (no fuselage, so not a plane); MAIL SATCHEL = a square bag with a flap hanging below the pilot. POST OFFICE = a small gabled house with a chimney, a mail flag on a tall pole and a sloping launching rail on trestles running off the cliff edge (not a barn: the rail and flag make it). BOAT = a small hull with a mast and a wake line (not a log). GULLS = a shallow M of two bent wings, 3 sizes.
- Light direction: the low sun on the horizon at the right (screen angle 180, from the right): every lit edge is on the right, shadows fall left; the glider canvas glows (sun through the cloth).
- Wind: from the right off the sea, moderate: the flag, the pilot's scarf and the chimney smoke all stream left.
- Outlines: GB darkest shade; NES black (the backdrop); 16-bit and GBA own-ramp darks, warm rim on the sun side.

## 4. The scene

- Camera: side view, eye level about half way up the cliff; horizon at 53% of the height (open sea only right of 80%).
- Shared composition (fractions of width u and height v; 16-bit px in brackets):
  - sun: centre u .86 on the horizon, half risen, radius .055 W [220,119, r 14].
  - crag (back wall of the cove, contre-jour): from u .30 v .38 up to its summit u .52 v .26, shoulder u .63 v .31, down to u .80 v .49 and the sea at u .83 [x 77-212, y 58-161].
  - near cliff: plateau v .34 from u 0 to .33, sunlit right face stepping out to u .40 at the bottom [x 0-102, y 76-224].
  - post office on the plateau: u .05-.26, v .14-.34 [x 13-67, y 31-76]; flag pole at u .275 up to v .08.
  - rail: porch u .26 v .31 to the end u .42 v .36, over the cliff edge at u .33, 1 trestle and 1 strut.
  - glider: delta wing u .41-.71, nose at v .32, tips at v .37-.41; A-frame and bar below the keel; pilot at u .53-.57 down to v .54, satchel at the hip.
  - town: u .40-.80, v .64-.86, 7 houses up the cove slope; harbour water v .86-1; mole u .62-.88; boat at u .84-.92, v .89, heading right.
  - gulls: 3: large u .35 v .20, medium u .76 v .29, small u .91 v .41.
- Hero: 102,79,182,122 (native px); peak value: the glider's sunlit canvas; peak chroma: the postmaster's red scarf
- Planes: sky 34% (light), crag and town 21% (darkest), near cliff and post office 18% (mid), sea and harbour 25% (mid), glider 2% (brightest)
- Layout: sky owns the top half (calm: only the cloud bank, the sun and 3 gulls); the left third is the near cliff and post office; the centre is the crag with the glider over it; the bottom band is the town and harbour; the right fifth is open sea and the sun's path.
- Masses: cliff masses 45% (crag), 30% (near cliff), 15% (town), 10% (mole); the cloud bank is one mass with lobes about 50%, 25%, 15% of its width.
- Value plan: darkest = the crag and the shadowed town (L .15-.25); mid = near cliff rock, roofs, sea (L .35-.55); light = sky, sunlit cliff face, cloud underside (L .6-.8); brightest = only the glider's canvas (L .9+), the sun disc held just under it.
- Per panel, designed inside its hardware:
  - 4-shade handheld (gameboy, 160x144): shades 0-3 only. Sky shade 2 with a 2-row checker into shade 1 at the top and into shade 3 around the sun; crag shade 0-1, near cliff shade 1-2 with shade 3 lit ledges; glider canvas shade 3 with shade 0 outline over the shade 0-1 crag. Sprites: wing on palette (0,2,3), pilot on (0,1,3). Tile budget 256 of 360 cells: flat sky rows and the 8 px-periodic sea repeat.
  - 8-bit console (nes, 256x224): 2C02 colours only, black backdrop shared by all; 4 BG sub-palettes of 3 colours chosen per 16x16 block: sky-high (blue, periwinkle, lavender), sky-low and sea (pink, orange, pale yellow), rock (indigo, violet, salmon lit face), town (cream walls, red roofs, lamp yellow). Sky in flat bands with 2-row checker dithers on 8 px rows. Sprites 3 colours each: wing (black, white, orange) 64 px = 8 sprites per line, pilot (black, blue, skin), a second overlapping sprite (dark brown, red, white) for the scarf, satchel and flag, sun and lit window (orange, pale yellow, white); at most 8 sprites per scanline, under 64 in all. Tile budget: under 256 unique 8x8 tiles for the whole frame.
  - 16-bit console (snes, 256x224): 15-bit colours, at most 16 per 8x8 tile; three parallax BG layers: far (sky gradient, sun, cloud bank), mid (crag, town, sea, harbour, boat), near (near cliff, post office, rail); sprites for the glider, pilot, scarf, satchel and gulls. Richer sunrise: 7 sky steps from deep violet to gold with 2-row checker seams, a warm rim along the crag's crest.
  - 32-bit handheld (gba, 240x160): 15-bit colours, at most 16 per 8x8 tile; wider view: the extra width goes to open sea and the boat; brighter, higher-key palette made for an unlit screen; finer sprite detail (rib shading, satchel buckle).

## 5. Lived-in details

- A mail sack slumped by the post office door (16-bit 7x6 px; GB 4x3), a value step lighter than the wall.
- A bicycle leaning on the post office wall (16-bit 10x6 px).
- Chimney smoke from the post office streaming left (16-bit 3 puffs, 4-9 px).
- Washing line between two town houses with 3 hung shirts (16-bit 14x4 px).
- Lit windows: 5 in the town, 1 in the post office, a value step above the walls; one window dark in a lit row.
- The boat's wake: a broken pale line behind the hull (16-bit 12x2 px).
- Lobster pots stacked on the mole (16-bit 6x4 px).

## 6. Phase: sunrise (the only phase)

- Palette by roles: deep violet high sky, rose and peach low sky, gold horizon; crag in plum shadow; near cliff warm ochre rock lit salmon; town cream walls with terracotta roofs in blue shadow; sea teal-violet with gold glitter; canvas cream; scarf red.
- Signature elements: the half-risen sun on the horizon, the gold glitter path, lit windows in a still-shadowed town, the glider catching the first light.
- Accent ration: red only on the scarf and the mail flag (and NES roof tiles, darker); gold only on the sun, its glitter, the crag's rim and lamp windows.
- Music: original 8-bar theme, D major, 116 bpm, 4/4; strings (detuned saws), 2-operator FM bass, FM bell-pluck lead, light kit (kick, snare, closed hat), stereo echo; sync point: the bell lead lands on the downbeat as the glider lifts.

## 7. Light list

- The sun: half disc on the horizon at u .86, pale gold, radius .055 W; lights every right-facing edge; hidden below the horizon line.
- Window lamps: 6 small warm rectangles (2x2 to 3x3 px at 16-bit), no glow, palette steps only.
- The glider canvas: no emitter, the sun through cloth drawn as the brightest slot with darker rib lines.

## 8. Motion table

- Delivered as still frames (1 frame each panel); the implied motion, for a later loop of 96 frames at 12 fps:
- flag: 2 frames at 4 fps.
- scarf: a 4-node chain, 3 drawings held 4 ticks; smoke 3 frames at 4 fps.
- boat 1 px every 8 frames; waves drift 1 px every 6 frames.
- gulls: 2 wing frames at 6 fps; the glider rises 1 px every 4 frames.

## 9. Particles

- Chimney smoke only: 3 hand-shaped puffs per panel, streaming left; no rain, snow or sparkle noise.

## 10. Never

- No palette-snapping one panel from another; no scaled copies.
- No console names, logos, real characters or known game UI in any caption.
- No blur, bloom, alpha blending, gradients outside each machine's colour rules, no pure black outside the NES backdrop.
- No symmetric stamped rows of houses, waves, clouds or gulls.

## 11. Technical

- Native canvases: 160x144, 256x224, 256x224, 240x160; exports nearest-neighbour only, 3x in the poster, 4x for B and the gates.
- Era checks: `pixelate era out/panel-gb.png --era gameboy` (and nes, snes, gba), background layers with `--layer bg`.
- Frame gate: `pixelate check out/panel-X@4x.png --style lofi --era X --scale 4` for each panel.
- Block-in: `pixelate check out/blockin-a.png --blockin --brief brief.md` at 256x224.
- Sprites: era.check_sprites on each panel's sprite boxes (NES 8 per line and 64 in all; GB 10 and 40).
- Sound: 48 kHz 16-bit stereo, exactly 5.0 s, 20 ms fade-in, 400 ms fade-out, about -14 LUFS; `pixelate check sound/05-sample.wav --style any --use song --bpm 116 --key D`.
