# Quarry Wakes (scene brief)

Request: arcade style at 304x224, delivered 4x, checked one layer at a time against the neogeo era. A 6-second boss reveal for an invented game: a colossal rusted dredging machine claws up out of a flooded quarry at dusk (bucket-chain jaw, piston legs, a cabin with one cracked lit window, moss in its seams); a soldier in a mustard coat crouches behind a toppled crane on the right. Two stills of its best moments and a 5 s FM sting.

## 0. Choices to confirm

- **intent**: the "WARNING" beat of an invented arcade run-and-gun: a stage boss heaving out of black water, huge, rusted and alive, and one small warm soldier who is clearly in trouble. Disappointing would be a generic robot, a dinosaur, a soft glow filter or a busy frame where the boss does not read at thumbnail size.
- **style**: `arcade` (warm hand-modelled actors on a cold dark world, opaque FX cells, no light layer), era `neogeo` checked per layer. Runners-up lofi and pastel-cell do not fit loud machine action.
- **projection**: side, camera at the soldier's ledge height, horizon (far waterline) at y 140.
- **time and weather**: dusk after rain, still air with a light wind from the left; a low ember band behind the boss is the last light.
- **phases**: one; two moments of one 6 s reveal (A "It rises" at about 2.4 s, B "The slam" at about 4.4 s).
- **figures**: one soldier, crouched 30 px tall (36 px standing, 3.6 heads); one boss about 190 px wide and 150 px tall, cut by the waterline.
- **purpose and outputs**: a showcase pair: out/06-a.png and out/06-b.png at 1216x896 (4x), 1x copies, the four era layers per image, a boss part sheet, and sound/06-sample.wav/.mp3.
- **music**: an FM boss sting in E minor at 168 bpm ending on the slam (section 6).

## 1. Purpose and delivery
- A key-art pair for the toolkit showcase, seen in a README grid at about 600 px wide and full screen; it must stop a scroll at thumbnail size.
- Delivered at 1216x896: native 304x224, 4x nearest. Stills only (the 6 s beat sheet below poses them).
- Beat sheet at 30 fps (180 frames): water erupts 0-24, jaw lifts 24-60, buckets cascade 48-84, three exhaust coughs at 60, 84, 108, leg rises 108-126, the slam at 132 (4.4 s), dust 132-162, hold to 180. Image A is frame 72, image B frame 136.

## 2. Style and light regime
- Style `arcade`: no light layer; light is palette steps (warm slots, rims, a few highlight pixels); blend palette-step; no post ops.
- Ramps: `arcade` (7 steps, l_max .82) for the boss rust, the coat and the window; flat cold `lofi` steps for the world.
- Outline: own (each material's darkest step), lit arc on the up-left side. Dither: none (checker is only for HUD gauges, and there is no HUD).
- Era `neogeo`: every colour on the 15-bit grid (5 bits per channel); each layer (bg, boss, soldier, fx) rendered alone on transparent and checked with `--layer sprite`: at most 15 colours plus transparent in every 16x16 tile.
- Learn the grammar only: no character, boss, logo, UI or stage from any shipped arcade game; the dredger, the soldier and the quarry are invented here.

## 3. Art direction rules
- Actors carry the chroma and the detail (at least 1.8x the world); the world stays cold and dark (median chroma at most .03).
- Effects are opaque palette cells that shrink with age (fx.burst, fx.debris, own cell sprites for spray); no light layer, no alpha.
- The boss is built from part sprites with pivots, posed per moment: body (hull and gantry), cabin, exhaust stack, jaw (bucket ladder), three bucket links, two piston legs.
- Plates, rivets, buckets and rocks are hand-placed and mismatched: plates 9-23 px wide, rivet spacing 3-6 px with one rivet row missing, buckets of three different sizes.
- Silhouette keys: dredger = a long inclined bucket ladder with open scoop buckets underneath, a boxy wheelhouse with a row of square windows, a tall banded exhaust funnel, a gantry A-frame with a tumbler wheel, telescoping piston legs with clamp feet; not a robot (no head, no face; the cabin sits on a hull with four windows, only one lit) and not a dinosaur (no neck, the jaw is a straight girder with buckets, not teeth in a skull). Soldier = a crouched figure with a round helmet, a mustard greatcoat flaring at the hem, a rifle along the thigh, behind a lattice crane boom lying on its side with its cab tipped over. Terraces = flat benches with vertical faces stepping down, not hills.
- Light direction: one key from the upper left (the ember band behind-left of the boss); lit edges up-left, shadow sides down-right; the cabin window is a second, local warm source on its own frame.
- Wind: light, from the left; smoke and spray lean right by 1-3 px.
- Every object is drawn in this scene's code; references/assets is read only.

## 4. The scene
- Projection: side. Canvas 304x224, far waterline y 140, near rim top y 188-196 at the right.
- Hero: 40,4,262,200 (native px; the boss across both moments, claws on the rim included); peak value: the cracked cabin window and the white spray cells at the boss; peak chroma: the soldier's mustard coat (263,156,296,204).
- Planes: sky and quarry walls 49% (2), flooded quarry water 21% (2), near rim and toppled crane 8% (1), boss 19% (3), soldier 1% (3), window and spray 2% (4).
- Layout: sky y 0-92 with the ember band y 77-92 between x 30 and 250; far terraced wall x 80-230, y 92-140; left side wall x 0-83, y 36-150; right side wall x 224-304, y 52-186; water y 140-200; the near rim across the full width, y 199-224 at the left rising to y 185 at the right, with the crane and the soldier on its right end; boss x 40-262, y 4-200 with both clamp feet on the rim.
- Masses: terraces in four benches of very different height (14, 6, 11, 17 rows at the far wall); side walls 70 and 74 px wide, the left one 1.4x taller; water in three bands (far 30%, middle 25%, near 45% of its depth); spray in one big crown at the waterline (about 90 px wide), one medium sheet off the jaw buckets (about 26 px) and small loose cells.
- Value plan: darkest (L .06-.14) near rim, crane, near water; dark (L .14-.30) sky, walls, far water; mid (L .32-.70) boss plates, soldier, ember band; brightest (L .85-.95) only the cracked window and the spray cells at the boss's waterline and jaw.
- Objects: 1 boss (body, cabin, stack, jaw with 9 scoop buckets on its chain, 3 hanging bucket links, 2 legs); 1 soldier; 1 toppled lattice crane (boom about 86 px, cab 18x14 tipped on its side); 1 haul road zig-zag on the far terraces; 2 broken fence posts on the near rim; no other figures.

## 5. Lived-in details
- A dented second bucket (12x9) with a bent lip, one empty socket on the chain where a bucket is missing (4x3 gap).
- Moss in the hull seams and green weed hanging from the buckets and the hull bottom (strands 1x3 to 2x7), olive two steps below the rust.
- A hanging snapped cable from the gantry top (catenary, 1 px, 18 px long).
- The cracked window: 9x7, a dark 1 px crack from corner to corner across the lit glass, the three other windows dark, one with a shard missing.
- A missing rivet row on the third hull plate, a riveted patch plate (10x7) one step lighter.
- On the near rim: the crane's tipped cab (18x14) with a broken window, two leaning fence posts (2x9, 2x7), a drum barrel (7x9) by the soldier.
- On the far terraces: the haul road zig-zag (1-2 px lighter line) and a tiny dead floodlight mast (1x12).

## 6. Phases
- Accent ration: mustard (h 80-95, C .12-.17) only on the soldier's coat; rust orange (h 35-60) only on the boss; window gold (h 70-85, L over .85) only in the cracked window and its 3 reflection dashes on the water; ember rose-amber only in the sky band (about 3% of the frame); teal-white only in the spray cells.
- One phase, palette by named roles: deep indigo sky stepping to dusky mauve, a dim ember rose-amber band, cold slate-violet terraces, near-black blue rock, black-teal water; rust red-orange hull, warm brown iron gantry, pale brass-steel pistons, olive moss, gold-cream window; mustard coat, olive trousers and helmet, warm skin; teal-white spray, sooty grey-brown smoke, grey-tan dust.
- Signature elements: the bucket-ladder jaw dripping weed, the cracked lit window, the white-teal water crown, the three-puff exhaust cough, the full-width dust wall of the slam.
- Music: an FM boss sting, E minor, 168 bpm, 4/4: an 8th-note FM bass on E with a b2 (F) and b6 (C) push, brassy 3-operator stabs on the off-beats, a short menacing 7-note riff of my own (E G F# E B, Bb A), a rising tom fill from 3.6 s and a noise riser, then the slam at 4.4 s: a pitched-down FM body hit, a noise burst and a sub drop from 70 to 30 Hz, decaying into the fade. Sync point: the slam lands with image B.

## 7. Light list
- The ember band: palette steps in the sky only (glow0 rose, glow1 amber), no light cast into the world.
- The cracked cabin window: glow0-glow3 slots (deep amber edge, orange, gold, cream core) inside the 9x7 glass; it lights the sill below it with one warm rust step and puts 3 gold dashes on the water below the boss; B adds one more ring (the glare) and a 1 px lit frame.
- Rims: rust4-rust5 on the up-left edges of the boss; coat4 on the soldier's left (the boss side); no rims on the world.

## 8. Motion table (180 frames at 30 fps)
- Stills are poses of this table; everything holds on whole frames at 30 fps (anim.Timeline keys), periods divide 180.
- Water crown: 3 drawings held 4, 6 and 8 frames from frame 0, then 6 frames of falling cells.
- Jaw: 4 angle keys (-34, -27, -20, -14 degrees) held 9 frames each over frames 24-60.
- Bucket links: a 3-link chain that lags the jaw by 2 keys (anim.lag), swinging 3 keys of 6 frames in B.
- Smoke: 3 puffs spawned at frames 60, 84 and 108, each 36 frames of fx.smoke_puff age.
- Leg: 3 rise keys held 6 frames (108-126), the slam key at 132 with a 6-frame anim.shake (2 px, 1 px, 0).
- Dust: fx.burst life 30 frames from 132; debris 24 frames; the soldier: brace pose to 128, flinch pose from 132, held 2 keys of 12 frames.

## 9. Particles
- Spray: about 160 opaque cells in A in three sizes (4 px, 2-3 px, 1 px) in two layers, the large ones near the hull and young, the small ones high and old; teal at the base, white at the tips.
- Bucket cascade: 3 falling sheets of 1-2 px wide water streaks with breaking cells.
- Dust (B): fx.burst crowns at 7 hashed points along the rim plus a band of own cells 6-1 px that shrink with distance from the impact, reaching both frame edges; fx.debris chunks (16) arcing from the impact, rock slots.
- Smoke: one hand-shaped cauliflower puff in A (fx.smoke_puff, 6 tones), three in B (oldest highest, thinnest).

## 10. Never
- any soft light layer.
- filters.
- Banned light ops: light, lightmap, glow, shaft, flare, streak, band, tint_field, fade, fog, motes, over, ambient, darkness.
- No dither gradients in the sky (hard bands of uneven height), no alpha, no blur, no pure black or white, no text or HUD, no stamped rows of rivets or rocks, no symmetric boss, no face on the cabin, no second warm figure.

## 11. Technical
- Native 304x224, 4x nearest to 1216x896; every cell flat at delivery size; about 100 colours, every one on the 15-bit grid.
- Figures: soldier 30 px crouched (36 px standing at 3.6 heads), boss about 150 px tall cut by the waterline, both as slot maps drawn here.
- Budget (`styles.check`): L<0.25 >= 0.45; L>0.75 <= 0.07; actor:median_C >= 0.06; world:median_C <= 0.03; actor/world:detail >= 1.8.
- Gate: `pixelate check out/06-a.png --style arcade --scale 4 --brief brief.md --pal out/palette.json --actor out/06-a-actor.png` passes every line, same for 06-b; each layer passes `pixelate era out/06-a-LAYER.png --era neogeo --layer sprite`; reads at 480 px wide.
- Gate overrides: none.
- Sound: sound/06-sample.wav (48 kHz, 16-bit, stereo, exactly 5.0 s, 20 ms fade-in, 400 ms fade-out) and .mp3; `pixelate check sound/06-sample.wav --style any --use song --bpm 168 --key Em`.
