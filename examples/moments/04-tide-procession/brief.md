# Tide Procession (scene brief)

Request: a tidal island monastery as a flat black silhouette against a low moon (the peak value); one
shaft from a cloud gap above the moon breathing across the water; a stone causeway to the near
shore; the tide is the clock of a 96 s loop; nine lantern pilgrims cross; the door opens and spills
light down the steps; the tide floods back. Two stills of the best moments and a 5 s sound sample.

## 0. Choices to confirm

- **intent**: a quiet, devotional night pilgrimage that reads in one glance as a thumbnail: a black
  stepped monastery cut out of a low moon, a thread of nine warm lanterns crossing a wet road, the
  only warmth in a cold frame. It must feel hand-pixelled (Sword & Sworcery's grammar, none of its
  content) and calm, never busy.
- **style**: `contre-jour`, gated with `--scene beam` (one big shaft). Projection: side.
- **moments**: A "The crossing" (low tide, t = 34 s of the loop) and B "The door opens" (t = 58 s).
- **figures**: nine hooded pilgrims, 29-34 px (8-9.4% of 360 rows), 1 px legs, no outline.
- **deviation**: the door spill uses Post.lightmap (asked for by the request: multiplicative, so dark
  stone warms and black stays black, with the door leaf as a moving occluder); contre-jour's allowed
  list lacks it, so the gate's `post op lightmap` line is expected to flag it (see section 11).

## 1. Purpose and delivery

- A showcase pair for the pixelate-anything gallery, seen full screen and as 480 px thumbnails.
- Outputs: out/04-a.png and out/04-b.png at 1920x1080 (native 640x360, 3x, prescaled screen
  light), their pre-light pixel layers out/04-a-pre.png and out/04-b-pre.png, out/palette.json,
  and sound/04-sample.wav + .mp3 (5.0 s).
- Loop (the full piece, not delivered here): 96 s = 1152 frames at 12 fps. Beats: 0-20 s high tide,
  bearers gather on the near shore in three uneven groups; 20-30 s the ebb uncovers the road; 30-56 s
  the crossing (one walk lap = 26 s); 56-62 s the door opens (4 held drawings) as the first pilgrim
  arrives; 62-84 s the flood swallows the road behind the last pilgrim; 84-96 s high tide again.

## 2. Style and light regime

- Style `contre-jour`: flat silhouettes; all softness in a screen light layer (Post(res="screen")
  through post.Stack), blend screen, plus one multiplicative Post.lightmap for the door.
- Ramps: `ramp_between('#0d151a', '#a07167')` navy-to-rose bridge for the sky and cloud rims, hazed
  per plane; warm emitter ramps for lanterns and the door; one cold moon ramp. Outline none, dither none.
- Learn the grammar only: nothing from Sword & Sworcery's characters, places or UI; the monastery is
  invented (no real tidal abbey: a square bell tower with a low pyramidal cap, a long nave, a round
  apse, a lean-to dormitory, a stair flight cut into the west face; no spire, no ramparts).

## 3. Art direction rules

- Every object is a slot map or a kit-primitive mask drawn in this scene's code; nothing pasted.
- Near plane (bank, beached boat, mooring posts, bent pine) is flat `sil0` (L .12) and never takes
  light; it sits at least .06 L under the sky or water behind it.
- The monastery is flat `mon0` (L .13) with a 1 px cold rim only on edges facing the moon; the stair
  treads are one step lighter so the flight reads; no windows lit in A.
- Repeated units are mismatched: pilgrims in four kinds and four walk drawings with gaps 23 41 19 54
  31 27 46 38 px; causeway stones 3-8 px wide, two missing stones (puddles); four posts of different
  height, width and lean; roofs of five different pitches and heights.
- Built imperfections: the causeway dips at x 165-245 (its lowest stones, first to flood); one post
  leans 1:6 and has lost its top; the boat lists 3 px with a broken thwart; one stair tread is 4 px
  high; the pine has a dead stub branch.
- Light lives only in the light layer: the moon halo, the shaft, nine lantern pools, the door spill.
  The pixel layer holds the emitters' own slots (moon disc, lantern dots with a one-slot ring, the
  lit doorway) and the reflection dashes.
- Silhouette keys: monastery: a stepped mass of five mismatched roofs climbing the rock, a square
  bell tower with two arched belfry openings and a pyramidal cap, a long pitched nave roof ending in a
  round apse (not a castle: no crenels, no round towers). Pilgrim: a pointed hood, a robe tapering
  wider to the hem, a staff taller than the head, a lantern held out on the island side (not a
  monk-shaped post: the hem flares and the legs show 1 px). Pine: a leaning trunk and three flat swept
  pads of very different size with sky holes (not a mast, not a ball). Boat: a curved sheer line and a
  pointed stem, listing on the sand. Posts: crooked, uneven, one rope sagging.
- Light direction: the low moon behind the island at x 468; every rim and lit column faces right
  toward it; lantern-side rims are warm on the right as well.
- Wind: light, from the left (west); the pine leans right, cloud wisps trail right, hems and the
  lantern flames lean 1 px right.

## 4. The scene

- Projection: side, horizon at y 206; the causeway rises gently from the near shore (left, y 271)
  to the island landing (x 418, y 238), so the road is the leading line ending at the island.
- Hero: 116,204,418,268 (native px); peak value: the moon disc and its halo ring (444,84,492,132); peak chroma: the lead pilgrim's lantern
- Hero B: see brief-b.md (the open portal and its spill, 440,158,536,244).
- Planes: near plane 14% (band 1), island and monastery 8% (band 1), causeway and pilgrims 2% (band 1), night sky and clouds 30% (band 2), far sea 5% (band 2), wet sand flats 16% (band 2), moonlit sky round the moon 18% (band 3), pools 6% (band 3), moon and the shaft's footprint 1% (band 4: brightest)
- Layout: sky 0-205 (calm: clouds, stars, the moon, the shaft only); island x 408-634, y 58-239;
  causeway x 22-418; flats and pools y 240-340; near bank y 296-360 with the pine at x 0-200 rising
  to y 30; boat x 168-252, y 312-334; posts x 497-592, y 280-340.
- Masses: clouds: one dominant bank x 96-418 (50% of the width), a second x 506-640 (21%), a sliver
  x 10-70 (9%); pools: a long road-front lagoon (40%), an outer pool (33%), three small ones; pine
  pads 140, 112, 60 px wide.
- Value plan: near plane, monastery and pilgrims L .10-.14 (darkest); night sky, clouds, far sea and wet sand L .18-.26 (dark); moonlit sky dome, pools, shaft body and wet stone rims L .30-.42 (mid); brightest only at the moon (peak L .95) and its one repeat, the shaft's footprint on the water behind the lead pilgrims (L .5-.6); lantern cores L .86 are 1-2 px dots
- Objects (maximums): 1 island with 1 church, 1 bell tower, 1 apse, 1 dormitory, 1 house,
  1 boathouse, 1 stair flight of 13 treads, 1 bent tree; 1 causeway; 9 pilgrims; 1 moon; 3 cloud
  masses; about 70 stars; 1 far headland; 1 boat, 4 posts, 1 pine.
- Depth planes: far (sky, stars, moon, headland: hazed), middle (sea, island, causeway, flats,
  pilgrims: lit by the shaft, lanterns and the door), near (bank, boat, posts, pine: flat).

## 5. Lived-in details

- A coil of rope on the second post (5x3, sil0 against the pool, one step off).
- The boat's oar leaning on its hull (14x2) and a bailer by the stem (4x3).
- A belfry bell visible in the left opening against the moon (3x4, mon0 on moon2).
- A small iron cross on the tower cap (3x5).
- Weed tufts on the causeway's seaward face (3x2, darker than the stone).
- A lantern hook on the portal jamb (B: 2x3, lit).

## 6. Phases

- One night, two moments. Palette by roles: navy-teal night sky, rose-grey cloud rims, cold
  silver moon, deep teal sea, wet slate causeway, sand-grey flats, near-black silhouettes, amber
  lanterns, gold door light.
- Signature elements: A (low tide): the exposed road with rimmed wet stones, nine lanterns in single
  file, stepped reflection dashes in the road-front pools, the shaft lying on the water behind the
  leaders; B (the door opens): the open portal and its warm wedge down the steps, the leaf's cut edge
  in the wedge, the flood sheet with ripple lines over the lowest stones behind the last pilgrim.
- Accent ration: amber/gold only on the nine lanterns, their reflections and pools (A, under 0.4%
  of the frame) and on the doorway and its spill (B, about 1.5%); cold silver only on the moon,
  the shaft and wet rims; rose only on cloud rims, at chroma .03 or less.
- Music: ambient at 60 bpm in D Dorian: sub drone, a slow Dm9 - Em9/D pad, a wave bed, sparse
  music-box notes, no drums; sync point: one struck bronze bell when the door opens (1.0 s into
  the sample).

## 7. Light list

- Moon: cold silver #e9eef1 disc at (468, 108), radius 22 px, hidden by the bell tower (opaque); halo Post.light radius 44 px, #c8d6e0, strength .30, at the sky depth, so the island in front stays flat.
- Shaft: cold #b9c9d6 Post.shaft, width 13 to 46 px, length 178 px, from the cloud gap (446, 50), angle 106 (A) / 110 (B), strength .30, blocked by the island and moon masks (behind=); it lands on the far sea behind the lead pilgrims; crests inside its ray mask step up a slot.
- Nine lanterns: warm amber #ffb860 pools, radius 9 px, squash .55, strength .30, at the middle depth, hidden by the near plane (never lit); each is a 1-2 px lamp3 core with a one-slot lamp1 ring, flicker held 4 frames in the loop.
- Door (B): gold #ffc070 Post.lightmap, sigma (30, 24), gain 2.4, one light low inside the portal at (509, 192), blocked by the facade wall round the portal (opaque) and by the door leaf (opaque, a moving occluder in 4 held drawings; B uses the open one), so the spill is a wedge through the threshold down the steps; a small Post.light glow, radius 8 px, in the opening, hidden by nothing.
- Ambient: none (not a light); the near plane takes no light. Ops used: light, shaft, glow, plus lightmap (the deviation in section 0).

## 8. Motion table (loop 1152 frames at 12 fps; stills here)

- Pilgrims: walk cycle of 4 drawings held 3 frames (period 12), 0.5 px/frame along the road.
- Lanterns: flicker held 4 frames (period 48 on an 12-entry table).
- Door: 4 held drawings (shut, ajar, half, open) over 6 s, the wedge widening with the leaf.
- Shaft: angle stepped 106 -> 110 -> 106 once per loop on a hold table.
- Clouds: one 640 px trip per loop (about 6.7 px/s); swell streaks one 128 px tile per loop.
- Tide: the waterline steps 1 px every 2 s on the flats, a hand table of 48 entries.

## 9. Particles

- None in the stills but stars (about 70, hand-placed in clusters, 3 tones, 4 bright).

## 10. Never

- Outlines, dither, filters, vignette, grain, scanlines.
- Light on the near plane, or a moon halo wider than one moon diameter.
- Even rows of pilgrims, stones, posts or roofs; symmetric clouds or waves.
- Text, logos, a real abbey's silhouette, a castle read (crenels, round towers).
- Warm colour anywhere but the lanterns, their pools and reflections, and the door.

## 11. Technical

- Native 640x360, 3x to 1920x1080, prescaled screen light; about 60 slots in the pixel layer.
- Figures: 29-34 px, 1 px legs, no outline, slot maps drawn here (study of figures.py slim only).
- Gate A: `pixelate check out/04-a.png --style contre-jour --scene beam --scale 3 --brief brief.md --pal out/palette.json --pre out/04-a-pre.png --actor out/04-a-actor.png --used light,shaft,glow --intent out/04-a-intent.png`.
- Gate B: the same with brief-b.md, out/04-b-*.png and --used light,shaft,glow,lightmap.
- Budget (scene beam): L<0.25 >= 0.45; L>0.6 <= 0.06; L>0.75 <= 0.02; C>0.08 <= 0.02; median_C <= 0.035.
- Gate override: allow Post.lightmap (the request asks for the door spill as a lightmap with the door leaf as a moving occluder)
