# 09 Lanternmoss Mire: short brief

## 0. Choices

- **Mode / style:** assets (guides/assets.md), lofi-family sprite craft: palette-step light only,
  own outlines in `ol`, light from the upper left, 3 tones per material at 16 px.
- **Grid:** 16x16 tiles; hero 16x24 (pivot 8,23 at the feet); creatures 12-20 px; items 7-12 px.
- **Camera:** 3/4 top-down game screen; islands show a dark south bank face, the boardwalk a
  front edge and piles.
- **Delivery:** `out/09-a.png` day and `out/09-b.png` glowing night, 1280x768 (the 320x192 map at
  4x, nearest), 1x copies `out/09-a@1x.png`, `out/09-b@1x.png`; the export's `contact.png`,
  `silhouettes.png`, strips, JSON and GIFs; `sound/09-sample.wav` + `.mp3` (5.0 s SFX reel).
- **Palette:** 38 slots + `ol` + `wh`, day (`palette.json`) and glowing night
  (`palette-night.json`), identical slot names. Both ship as .json/.gpl/.hex/.png. Seven slots were
  added after the art director's notes: `glow`, `lap`, `shallow` and four `lamp_*` slots. The lamp
  slots equal the plank and water colours by day, so the lantern pool only shows at night.

## Palette by role (day -> glowing night)

| slots | role | day | night |
|---|---|---|---|
| ol, wh | outline, glint | violet near-black, cream | blue-black, pale cyan sparkle |
| water0-2 | bog water: deep, body, ripple | tea-teal | indigo; **water2 glows cyan-green** |
| peat0-2 | peat banks: face, top, lit rim | chocolate | sinks to violet |
| moss0-3 | moss: shadow, body, mid, lit fringe | green, yellow-green tips | deep teal; **moss3 fringe glows** |
| wood0-2 | planks, cart, shrine, stump, pole | weathered tan | blue-violet |
| reed0-2 | straw hat, cattail stalks, toad belly | ochre straw | blue-grey |
| coat0-2 | hero coat (top chroma) | rust red / orange | wine, lit side warmed by the lantern |
| skin0-1 | face, hands | warm | lantern-lit face |
| gold0-2, flame | brass, coin, key, bell; lantern core | gold | **flame + gold2 = the one warm peak** |
| lum0-2 | glow caps, moth lantern, tonic | pale sage | **bioluminescent cyan-green** |
| mist0-2 | heron, iron, glass, beard | blue-grey | deep blue-violet |
| glow | moth bodies and wing edges | dull dusty beige | **brightest cool point** |
| lap, shallow | shore laps, shallows band | light teal | **laps glow**, shallows sink |
| lamp_w1-2, lamp_q1-2 | lantern pool on planks and water (map mask) | = wood1-2, water1-2 | **warm** |

## Sprites and parts

- **Hero, bog-ferrier 16x24:** wide straw rain-hat (brim 12 px, the silhouette key), shadowed face
  with two eye pixels, grey scarf, long rust coat with belt and brass buckle, brown waders, a 2 px
  punting pole, a 4x6 brass lantern. Front is the base drawing; back = the base with the face and
  front details overwritten and pole/lantern on swapped hands; side drawn on the same row plan.
  Idle 3 frames (breath: head and coat sink 1 px, lantern sways), walk 4 (contact, passing,
  contact, passing), all by moving parts in code (`art/mire_hero.py`).
- **Creatures (idle 2-4 frames):** reed heron (tall legs, S-neck, dagger bill, crest; 3 frames neck),
  peat toad (squat, throat sac; 4 frames inflate), lantern moth (two wing pairs, glowing abdomen;
  4 frames flap), mud-crab (wide shell, raised claw; 3 frames), drowned-bell snail (a verdigris
  bronze bell as its shell; 3 frames eye stalks), eye stump (roots, moss cap, a knot that opens one
  eye; 4 frames).
- **Items (12):** coin (spin: face, 3/4, edge, mirrored 3/4), key (same spin), glow tonic potion
  (full / half / low), glow cap, peat brick, marsh berries, brass bell, bog eel, reed bundle, moth
  scale, rope coil, map scroll.
- **Tiles:** moss-on-peat corner autotiles (16 x 3 variants); peat bank over water (16 x 3
  variants, with a shallows band and laps; the water stays transparent so the animated water shows
  through); deep-water corner set (16); bog water (4 variants x 4 frames, ripples move 4 px per frame,
  an exact wrap); boardwalk (H straight x2, broken plank, ends, V straight x2, V ends, landing).
- **Props:** cattails (2-frame sway), sunken cart, shrine post, glow mushrooms (two clumps), lily
  pads and a 4-pad lily cluster.

## Map plan (20x12 tiles, 320x192)

Water 55%, three islands of clearly different size (west big, north-east shrine island medium,
south-east bank small), a boardwalk that enters left, crosses the west island, bridges the open
water (one broken plank, a coin beyond it) and turns north to the shrine. Vignettes: hero on the
boardwalk with two moths at the lantern (focal, left of centre); heron wading in cattails (north-
west); eye stump watching with glow caps and the toad inflating (west island); shrine post with
caps, a moth and the key (north-east); sunken cart with the bell snail and a potion on the bank
(south); mud-crab on the south-east bank. Two deep channels, two lily clusters, and a hand-drawn
lantern-pool mask around the hero (its core swaps every plank and water slot to a lamp slot, its
rim only the light ones). Day and night use the same tile indices and frames.

Rebuild: `./pixelate assets examples/moments/09-lanternmoss-mire`, then
`python3 examples/moments/09-lanternmoss-mire/maps/render_map.py --gif`.

## Sound plan (sound/09-sample.wav, 5.0 s)

Own numpy chip synth (`sound/sfx_reel.py`): pulse 1+2 (12.5/25/50% duty, 4-bit stepped volume
envelopes, pitch sweep), 4-bit 32-step wave channel, LFSR noise (15-bit and 7-bit). Events:
coin (0.10 s), pole-vault whoosh + landing thud (0.55 s), toad inflate + croak (1.25 s), moth
flutter (2.05 s), bog splash (2.70 s), 4-note item-get jingle (3.55 s). 20 ms fade-in, 200 ms
fade-out, peak about -1 dBFS.

## Checks

`./pixelate assets` report: no unknown keys, no ragged frames, lone pixels only eyes/sparkles.
`./pixelate check out/09-a.png --scale 4 --style lofi` craft lines; the music gate with
`--style chiptune --use song`.
