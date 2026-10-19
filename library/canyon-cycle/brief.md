# Canyon Cycle (scene brief)

Request: one 320x180 still of a gorge at the meeting of two waterfalls: a rope bridge, a forge cut into the cliff with its door open, a river curling into the foreground, a hanging lantern, storm clouds over a far mesa. No pixel is ever redrawn: all motion is palette rotation over dedicated slot ranges. The palette moves through four moods: cold dawn, hard white noon, rose sunset, indigo night. Deliver two moments from one index array: A rose sunset at the lightning instant, B indigo night.

## 0. Choices to confirm

- **intent**: a Mark-Ferrari-style colour-cycling showpiece: one hand-drawn index map that stays alive through palette motion alone, where the warm forge at the bridge end is the place the eye rests in every mood; it must stop a stranger scrolling past
- **style**: `lofi` (palette-step light, Bayer gradients, own-material outlines)
- **projection**: side, a slot-canyon view framed by two near walls
- **moods**: cold dawn, hard white noon, rose sunset, indigo night (same slots, four palettes); delivered: sunset at the flash instant (A), night (B)
- **figures**: none (the open door and the lantern say someone works here)
- **purpose and outputs**: a showcase still pair at 1920x1080 plus the index map, palettes, a range diagram and a 5 s sound sample
- **music**: ambient pad and music box over a sub drone, 64 bpm, wind and fire bed, a thunder roll mixed on top

## 1. Purpose and delivery
- Two stills for the pixelate-anything showcase: out/03-a.png (sunset, lightning) and out/03-b.png (night), 1920x1080 = native 320x180 at 6x nearest.
- Both decode from out/03-index.png (P-mode, 1x); palettes out/03-sunset.* and out/03-night.* (json, gpl, hex); out/03-ranges.png labels the cycling ranges.
- Loop (for the engine version): 120 s = 3600 frames at 30 ticks/s, four moods of 30 s; every range period divides 3600.

## 2. Style and light regime
- Style `lofi`: light regime none (no light layer): light is palette steps only; sun rims, the forge spill and the lantern are warm slots drawn into the index map.
- Ramps `lofi` shape, written per mood in OKLCh (`palette.from_lch`); flash frames via `palette.flash` on the storm and mesa slots only.
- Outline own (darkest step of each material); dither bayer4 in the sky only, transitions 10-16 rows.
- Budget (lofi): L<0.1 <= 1%, L>=0.7 <= 4%, L>0.8 <= 2%, median C 0.02-0.1; the forge interior and lantern core are the only L>0.8 masses.
- Original work: no characters, logos or places from any game; studied library/lantern-isle and references/assets/props.py (lantern) only as examples to read.

## 3. Art direction rules
- Every object is a hand-placed slot map in art/*.py on the kit's canvas; no stamped units.
- The walls are layered canyon sandstone: strata 8-22 px tall, each with a lit lip and a shadowed underside, vertical cracks splitting blocks, ledged and frayed inner edges (`shapes.ledges`, `shapes.fray`, `texture.flakes`).
- Waterfalls are streaked columns, never horizontal stripes: each column has its own phase and streak length (3-6 px per slot).
- Named imperfections: one missing deck plank and one broken plank hanging, the handrail rope sagging lower on the left, one snapped suspender cord, a cracked forge chimney with embers in the crack, the door leaf hanging a pixel off square.
- Repeated units are mismatched: strata heights, cloud lobes, foam dashes, river glints, stars and planks never in even rows.
- Calm areas stay calm: the sky gap is three long bands plus one cloud bank; the near river is one dark body with sparse glints.
- Silhouette keys: forge = dark arched cut in the wall, a bright interior with an anvil silhouette, a door leaf swung out and a stone chimney (not a window); rope bridge = two sagging catenaries with vertical cords and a planked deck (not a pipe or a branch); lantern = cap, bail and a glowing glass box hanging from an arm (not a star); mesa = flat caprock over talus skirts (not a hill); falls = tall vertical streaked ribbons with foam at the foot (not a road).
- Light direction: the sunset sun is low on the left (west), so left-facing faces and ledge tops on the right wall, the mesa's left face and the cloud bank's left crown take the rose light; at night only the forge (right, x 220-238) and the lantern light anything.
- Wind: light, from the right; rain streaks lean 1 px left per 3 rows.

## 4. The scene
- Projection: side. Canvas 320x180.
- Hero: 194,74,252,112 (native px); peak value: the forge interior and the lantern core; peak chroma: the forge fire (orange F1)
- Planes: near walls 43% (dark), foreground banks 17% (dark), bridge 1% (dark), upper sky and storm 9% (mid), mesa 3% (mid), rock step 5% (mid), left fall 2% (mid), pool and river 13% (mid), forge frame and landing 1% (mid), low sky glow 6% (light), right fall 1% (light), forge light 1% (brightest)
- Value plan: dark group L .14-.30, mean .25 (near walls, foreground banks, bridge silhouette); mid group L .31-.46, mean .38 (upper sky and storm, rose-lit wall faces, rock step, left fall, river body, mesa); light group L .47-.62, mean .52 (low sky glow, right fall, cloud crown; flashed storm rims up to .72); brightest (L .78-.92) only at the focal forge interior and the lantern core. At night: everything L .10-.27 except the water ranges (to .52), the spill (to .58) and the forge and lantern (to .92).
- Layout: left wall x 0-100 (full height to the pool at y 124), right wall x 204-320; sky gap x 96-214, y 0-96 with the storm bank x 108-210, y 6-52 and the mesa x 116-204, y 64-96 (a small butte x 102-122); hazed rock step x 96-212, y 88-124.
- Left fall (in the wall's shadow): pours over a lip at y 30, x 92-101, breaks on a ledge at y 70, lower tier x 88-104 widening to 22 px at the pool (y 124); right fall (sunlit): pours over the rock pinnacle's lip at y 76, x 126-134, breaks at y 98, lower tier x 122-137 widening to 19 px; their spray crowns merge into one foam pool at the river's head (x 80-150), behind the bridge (art director note 2).
- Bridge: posts at x 74 (left ledge, y 86) and x 205 (forge landing, y 104); deck sags 9 px; 2 handrail ropes, cords every 5-9 px.
- Forge: door opening x 220-237, y 84-106 in a stone frame x 215-241, landing planks x 196-252 at y 106-110, chimney x 242-249 from y 46.
- River: leaves the pool at x 110-200, curls left to x 70-160 at y 146, then right, leaving the bottom edge at x 120-262; foreground rocks x 0-125 and x 240-320, a gravel bar on the inner bend.
- Masses: the walls are 3 strata groups per side of very different height (about 50%, 30%, 20% of the wall); the cloud bank one dominant head (60% of its width), one anvil shelf (30%), two scuds.

## 5. Lived-in details
- A quench barrel by the door on the landing, 5x6 px, one step lighter than the planks (B2 on B1) with an iron hoop.
- Stacked charcoal sacks left of the door, 7x4 px, B1 and I1 against the lit rock.
- Tongs and a horseshoe hung on the door frame, 4x5 px, I0 on the FR1 spill.
- The anvil silhouette inside the door against the fire, 7x5 px, I0 on F2/F3.
- The cracked chimney: a 1 px crack 6 px long with 3 ember pixels (F1) in it, chimney 7x36 px.
- The missing plank (a 4 px gap) and the broken plank hanging below the deck, 3x5 px, B2 on the fall behind.
- Fern tufts in the falls' spray on the pool bank, 6x4 px, G1-G2 on R0.

## 6. Phases
- Accent ration: orange and amber (F, FR, L) only on the forge, its spill, its reflection glints and the lantern; rose is the sunset light on rims, sky and falls; teal is the night water only.
- Cold dawn: sky slate-blue to pale lemon, walls blue-grey with a cold rim on the left wall, falls pale cyan; signature: mist-pale falls, the forge banked low (deep flick table).
- Hard white noon: sky washed near-white cyan at the horizon, walls ochre-sand with short shadows, river turquoise; signature: the lantern unlit (L slots = iron), rain on (a passing shower).
- Rose sunset (A): violet zenith to peach horizon, right-wall faces rose, falls rose-violet, mesa lilac; signature: the storm over the mesa and the lightning flash (`palette.flash` on C, M, BL for 2 frames).
- Indigo night (B): everything indigo L .10-.27; forge, spill and lantern warm; falls and river glints teal; signature: stars twinkling on T0-T2.
- Music: ambient at 64 bpm in B-flat minor (Bbm9, Gbmaj7, Dbmaj7, Fm7): a slow pad with music-box voices, a sub drone (bassMode drone), no drums, wind 0.3 and fire 0.2 beds; the 5 s sample opens on a thunder roll (own synth: low-passed noise rumble, a short crack and a swelling sine sub) and the music box answers after it.

## 7. Light list
- Forge fire: slots F0-F3 (ember red to pale-yellow core) fill the door opening; the spill FR0-FR1 (warm orange) is a hand-shaped wedge on the landing planks reaching 14 px out from the door and a 1-2 px warm rim on the door frame stones; hidden by the door leaf on its left side and by the wall everywhere else.
- Lantern: L0-L2 (amber glass, pale core 2x2 px) in a 5x7 px box, a warm rim on the nearest 3 cords and the bridge post; blocked by nothing; no glow ring wider than 1 px.
- Sunset sun: not drawn; the rose rim slots R3-R4 on left-facing faces and ledge tops of the right wall, M2-M3 on the mesa, C2-C3 on the cloud crown.
- Lightning: bolt slot BL (pale lilac) from the flat cloud base (y 41) to the mesa caprock (y 61), a jagged channel 1-2 px wide with three short branches, on only during the 2 flash frames; the flash lifts C0-C3 and M0-M3 by `palette.flash`.

## 8. Motion table
- Left fall WA0-WA5: 6-slot range rotating one step every 3 ticks (10 fps), streaks move down; period 18 ticks.
- Right fall WB0-WB5: 6-slot range, 10 fps, period 18 ticks.
- River far reach RA0-RA4: 5-slot range one step every 6 ticks (5 fps), glints travel left; period 30 ticks.
- River near reach RB0-RB4: 5-slot range one step every 4 ticks (7.5 fps) in the opposite screen direction (right); period 20 ticks.
- Forge F0-F3 and FR0-FR1: flick() held 3-5 steps at 10 fps; lantern L0-L2 flick() held 3 steps.
- Stars T0-T2: 3-slot range stepped on a hold table at 2 fps; period 45 ticks.
- Lightning: one strike per loop at sunset, 1 pre-flash frame then 2 flash frames (BL on, `palette.flash` on C and M), decay over 3 frames.
- Rain RS3, RC0, RM0, RM1: the storm's rain curtain under the right of the cloud base, switched on for the 8 s sunset storm (on in A, per art director note 4) and off otherwise (off = its base colour, as in B).
- Mood change: palette dissolve over 2 s between moods, all slots keep their role.

## 9. Particles
- None as sprites: rain is drawn once into the index map as faint 2-4 px streaks under the storm bank (about 60 streaks, hashed positions, leaning left), visible only when the rain slots are on.
- Stars: 22 hand-placed 1 px stars in the clear sky (y 0-30) on S0 only, in two clusters and a loose arc, 3 at T2.

## 10. Never
- glow blur, bloom, lens effects, soft shadows, alpha.
- narrow gradient bands that read as stripes.
- Banned light ops: light, lightmap, glow, shaft, flare, streak, band, tint_field, fade, fog, motes, over, ambient, darkness.
- No pixel redrawn between moments: A and B differ only in palette.
- Two ranges never share a slot; no range slot is used by any static object.

## 11. Technical
- Native 320x180, 6x nearest to 1920x1080; 80 slots (lofi allows 40-80), about 60 distinct colours per frame.
- Slot map: static S0-S5, K0, R0-R4, H0-H2, G0-G2, B0-B3, I0-I1, N0-N1, V0-V2, Q0; flash group C0-C3, M0-M3 and switched BL; switched rain RS3, RC0, RM0, RM1; flicker F0-F3, FR0-FR1, L0-L2; ranges WA0-WA5, WB0-WB5, RA0-RA4, RB0-RB4, T0-T2.
- Index map built once (art/canyon.py); palettes per mood with ranges rotated to the moment (art/palettes.py); render and verify in art/render.py.
- Gate: `pixelate check out/03-a.png --style lofi --scale 6 --brief brief.md --pal out/03-sunset.json` and the same for 03-b with out/03-night.json; block-in `pixelate check out/blockin-a.png --blockin --brief brief.md`.
- Sound: sound/03-sample.wav, 5.0 s, 48 kHz 16-bit stereo, 20 ms fade-in, 400 ms fade-out, near -14 LUFS; `pixelate check sound/03-sample.wav --style ambient --use song --bpm 64`.
- Gate overrides: none (A and B pass every line without one).
