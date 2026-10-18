# Market Day: Noon from the bell tower (scene brief)

Request: rebuild Pexels photo 14037897 (Nick Verlice, "Aerial View of Medieval Buildings on an Old Town": Strasbourg's Rue Merciere seen from the cathedral tower) as sticker-iso at 600x600, delivered 4x at 2400x2400; a market day with a wedding on the hall steps as the hero; a 5 s brass-band sound sample.

## 0. Choices to confirm

- **intent**: a showcase still a stranger stops on: the real old-town footprint (the long street, the arcaded hall, the two squares, the huge dormered roofs) read instantly, then a dozen tiny stories found one by one; it must feel hand-placed, sunny and festive, never a stamped city.
- **style**: `sticker-iso` (full-bleed noon, gamut-edge flat paint, full #000 silhouettes, no light, no shadow, density is the subject); runners-up `hd-overworld`, `lofi` (rejected: they light the scene).
- **projection**: 2:1 iso, scale 1 (+1 x = 2 px right 1 down, +1 y = 2 px left 1 down, +1 z = 1 px up).
- **time and weather**: noon, clear, no cast shadows.
- **phases**: one still moment (no loop); the sound sample is 5.0 s.
- **figures**: the request's actors only, in vignettes: the wedding party, the band, the juggler and ring, kids and pigeons, the melon argument, the dog and the fish, the cyclist, cafe sitters, shoppers in small groups.
- **purpose and outputs**: image A (full frame) out/08-a.png 2400x2400, @2x 1200, @1x 600; image B out/08-b.png, a 150x150 native crop of the wedding at 8x (1200x1200); sound/08-sample.wav + .mp3.
- **music**: a festive oom-pah march, Bb major, 112 bpm (the request overrides the style's accordion default): tuba on 1 and 3, horn after-beats, trumpet lead, snare, bass drum, a cymbal on bar starts, a crowd-murmur bed.

## 1. Purpose and delivery
- A gallery showcase still for the pixelate-anything toolkit, seen full screen and as a thumbnail; plus a crop that holds up at 8x.
- Native 600x600, 4x nearest to 2400x2400 (A); B is a native crop around the wedding at 8x.
- Loop: none (a still); the sound sample is 5.0 s at 112 bpm (9 1/3 beats: starts on a downbeat, fades out over 400 ms).

## 2. Style and light regime
- Style `sticker-iso`; light: none (res none, blend none); ramps `flat` (faces at L -.12 -.05 0 +.04 +.07) plus a neutral grey ladder; outline black (`Iso.render(silhouette=True)` plus a 1 px #000 ring on every sprite); dither none.
- Learn the grammar of the measured reference only: no characters, logos, readable shop names or brand marks; the place itself is the subject and is depicted.

## 3. Art direction rules
- Every roof is a true steep plane (hr = 1.5 x depth: clean 1:1 and 1:2 rakes), its tiles laid as offset courses with a few slipped and patched tiles, never one value.
- Houses differ in width (9-19 units), wall height (18-46 px), roof (eave or gable to the street, about one in three hipped), paint and window rhythm; no two neighbours share a height, paint or roof.
- Dormers come in stacked rows that shrink toward the ridge (3-4 rows on the big roofs, 1-2 on small ones), spaced unevenly, two or three dormer shapes per roof; never a grid.
- People are 3.3-head slot maps 13-15 px tall in at least 5 poses (stand, walk, throw/wave arm up, sit, play, juggle) plus kids at 10 px, gathered in vignettes; open paving stays calm between them.
- Silhouette keys: the hall = a long low arcaded block (round black arches in a cream stone base) under a roof taller than its walls, three dormer rows, hipped ends (not a church: no tower, no spire); old houses = tall steep roofs with stacked dormers and dark half-timber grids on pale plaster (not modern blocks: no flat roofs); a stall = a counter under a striped awning with produce on top (not a tent: square, open front); the kite = a tall diamond with spars and a bowed tail, snagged on a dormer (not an envelope); a tuba = a big gold bell above the player's head.
- Light direction: none (noon, no light layer); faces keep the fixed order top step 3, left (+y) step 2, right (+x) step 1.
- Wind: a light breeze toward screen right: the kite tail and the petals drift right, awning valances hang straight.
- Every object is drawn in this scene's code from the primitives (iso boxes, planar roof faces, hand-typed slot maps); nothing pasted, traced or generated.

## 4. The scene
- Projection: 2:1 iso, canvas 600x600, origin (284, 291) for world (0, 0, 0). The photo's steep oblique (camera on the cathedral tower looking down the street, street vertical in the frame, cathedral square at the bottom edge, the hall square at the top) maps to iso with the street along world x: it runs from the cathedral square at the lower right up-left into Place Gutenberg; the far (photo-right) side shows its facades, the near (photo-left) side its roof backs. The near row is lowered and the street widened (48 units) so the iso camera can see into it, as the photo's steep camera does. Edges: the left edge cuts the old houses west of the hall, the top cuts the roofs north of the squares, the right edge cuts the far-side blocks and the cathedral square, the bottom cuts the near-side roof rows and the cafe terraces; the city continues past every edge.
- Hero: 150,170,252,250 (native px); peak value: the wedding on the white hall steps (bride, steps, white petals); peak chroma: the wedding's rose runner, bouquet, bridesmaids and petals.
- Planes: roofs 56% (dark), facades, stalls and crowd 18% (mid), street and square paving 25% (light), the wedding on the steps 1% (brightest).
- Layout: the hall x 80-320, y 60-260 (its roof and arcade front); Place Gutenberg x 50-430, y 150-350, calm open paving with the fountain (x 300-330, y 220-245) and the kids and pigeons (x 330-380, y 200-235); the street x 230-560, y 290-470 with the stalls on its far side and the band among them; the cathedral square x 330-600, y 430-600 with cafe terraces and the cyclist; roofs own the rest: upper left (west of the hall), top and upper right (far-side blocks), lower left (near-side rows).
- Masses: the roof field is four masses of very different size: the near-side rows (lower left, about 45% of the width), the far-side blocks (upper right, 35%), the hall roof (25%), the old houses west of the hall (15%); the crowd is 8 vignettes of 2-9 people, never an even scatter.
- Value plan: as masses at thumbnail size: roofs L .45 (dark: paint .33-.64 laced with #000 silhouettes, dark tile courses and dormer windows); facades, stalls and crowd .55 (plaster .78-.80 broken by dark windows, timbers and awnings); paving .62-.66 (mid grey granite, as in the photo); brightest only at the wedding (.95-1: the white steps, the bride, the white petals), set against the black arcade openings and a darker granite apron. Per pixel the frame keeps the style budget (#000 lines 8-30%, 30% at L <= .30, 15% over .70).
- Objects (counts are maximums): the hall 1 (13 arcade bays, 3 dormer rows, a kite on its roof); about 75 houses; 11 stalls (3 fruit, 3 flowers, 2 fish, 3 bread); 1 flower cart; 1 fountain; 4 cafe terraces of 2-4 tables and parasols; 3 trees; 1 bicycle; about 120 people; 1 dog; 14 pigeons (8 flying).

## 5. Lived-in details
- the kite snagged on a hall dormer, its tail fluttering right (9x12 px, gold and blue on the grey-brown roof, two value steps off it).
- a melon held up between a vendor and a customer, a split melon on the crate (5x4 px, green over the orange-awning stall).
- the dog running off with a silver fish, the fishmonger's arm up (dog 9x6 px, fish 5x2 px).
- the cyclist's crate of baguettes on the rear rack (6x4 px, ochre on #000).
- the flower cart heaped with violet and yellow blooms on the cathedral square (13x8 px, brown cart on grey granite).
- a pigeon burst over the kids: 8 birds in 3 sizes rising (3x2 to 5x3 px, grey on paving or roof).
- open umbrellas over two cafe tables, a waiter with a tray (5x5 px).
- a fruit barrow of stacked crates at the cathedral square's north end, a vendor holding up a melon (crates 4x3 px, orange, green and yellow on brown).

## 6. Phases
- One phase: noon. Palette by roles: terracotta and brown roof paints, weathered grey-brown tile (the hall), dark slate; cream, off-white plaster, pink, ochre, mint and sky facades; sandstone (the hall); neutral paving ladder; dark timber; awnings orange (fruit), violet (flowers), blue (fish), yellow (bread); leaf green; brass gold; the hero rose; #000 and #fff.
- Accent ration: rose (OKLCh .62/.255/358) only on the wedding (runner, bouquet, bridesmaids, petals), about 0.3% of the frame; #fff only on the wedding (steps, dress, petals); orange only on fruit awnings and fruit; violet only on flower awnings, the cart and buckets; blue only on fish awnings and the fish crates; yellow only on bread awnings, bread and the kite.
- Music: a festive march (oom-pah) in Bb major at 112 bpm, the band in the stalls: tuba on 1 and 3, horn after-beats on 2 and 4, a trumpet-ish lead of my own, snare and bass drum with a cymbal on bar starts, a soft crowd murmur; written in code (sound/march.py) and judged with `pixelate check sound/08-sample.wav --style any --use song --bpm 112 --key Bb`.

## 7. Light list
- The sun: noon, overhead, drawn as nothing: no cast shadows, no rims, no light layer.
- Windows, dormers and the arcade: dark glass (glass, g0) and dark openings by day, never lit.
- The fountain jet: two water steps and a 1 px pale crest, no glow.

## 8. Motion table (a still; the plan if it is ever animated: 96 frames at 12 fps)
- The band steps along its path 1 unit per 6 frames, a 2-drawing march cycle held 6 frames each (period 12).
- Petals fall 1 px per 4 frames on hashed paths, 3 generations (period 32).
- Pigeons in the burst flap 2 drawings held 3 frames (period 8: held 4 each).
- The kite tail flutters 2 drawings held 12 frames (period 24); the juggler's balls cycle 4 drawings held 3 frames (period 12).
- Loop check: periods 12, 32, 8, 24 and 12 frames all divide the 96-frame loop (anim.check_periods).

## 9. Particles
- Petals: about 40 flecks in 2 sizes (1x1 and 2x1 px) in rose and white, in a fan above the wedding drifting right; marked in the intent mask.
- Pigeons: 14 hand-placed (6 on the paving, 8 in the burst).

## 10. Never
- light of any kind, cast shadows, glow, dither gradients.
- empty areas; an even scatter of people; the same house stamped along a row.
- readable shop names, logos, flags of real organisations.
- rose or #fff outside the wedding.
- Banned light ops: light, lightmap, glow, shaft, flare, streak, band, tint_field, fade, fog, motes, over, ambient, darkness, cast_shadows.

## 11. Technical
- Native 600x600, 4x nearest to 2400x2400; every cell flat at delivery size; about 75 colours in the pixel layer.
- Figures: 13-15 px iso people, 3.3 heads, as my own slot maps (the style's 33-37 px is for a street-corner close-up; this frame holds a whole street, two squares and the hall, so the people are scaled to the footprint).
- Budget (`styles.check`): black 0.08..0.3; L<=0.3 >= 0.3; L>0.7 >= 0.15; C>0.04 0.2..0.55.
- Gate: `pixelate check out/08-a.png --style sticker-iso --scale 4 --brief brief.md --pal art/palette.json --actor out/08-a-actor.png --intent out/08-a-intent.png` passes every line.
- compose.check_density on the placed objects passes (every edge cuts 2+ objects; no 120 px window over 85% bare paving).
- Gate override: focus_contrast >= 0.2 (sticker-iso density: every roof, stall and figure carries #000 silhouettes and dark tile courses, so the strongest local contrast is spread over the full-bleed town by design; the hero holds the top values, the only rose and the only #fff instead)
- Gate override: focus_rival <= 3.2 (full-bleed town: the near-side roof field is one connected busy mass at thumbnail size; it stays mid-value and hue-varied while the white steps and rose runner are the frame's only peak)

## Image B (the wedding crop, gate lines)

B is a straight 8x nearest crop of A's 1x frame, written by `art/scene.py final out 142 162` (the last two arguments are the crop's top-left in native px). As built it is 140x140 native, 1120x1120 delivered; section 0 and 1 say 150x150 and 1200x1200, which the code never produced.

- Hero: 8,8,110,88 (native px, in the crop); peak value: the wedding on the white hall steps (bride, steps, white petals); peak chroma: the wedding's rose runner, bouquet, bridesmaids and petals
- Known gate failures, not excused by this brief: budget L<=0.3 (20.45% against the sticker-iso floor of 30%) and composition empty (57.55% against 30%). The crop holds the hall's calm roof and facade, the white steps and open granite, and no crop of A that keeps the wedding passes (searched 80-150 px squares). Section 11's overrides cover only focus lines of A and none of these.
