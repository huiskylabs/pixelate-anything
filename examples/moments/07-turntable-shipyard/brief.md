# 07 Turntable Shipyard (scene brief)

Request: a tactics-style canal boatyard diorama floating in darkness, built once in tools/iso.py and
tools/sdf.py and turned like a model on a lazy susan: four quarter-turns, each advancing time and
construction (bare ribs at dawn, planked hull at noon, deck and rails at dusk, mast and pennants at
night with lanterns lit). Two stills of the best moments and a 5 s work-song sample.

## 0. Choices to confirm

- **intent**: a showcase still a stranger stops on: a calm, readable board in the dark whose one warm thing is the ship; the turntable must read as the same model turned, not two scenes. A ship that reads as a box, or a busy yard that buries it, would disappoint.
- **style**: `tactics` (2:1 iso slab floating in the dark, five near-neutral greys, colour rationed to warm accents, black outlines with white spec strokes, hard cast shadows, no light layer).
- **projection**: 2:1 iso, native 640x360, 3x nearest to 1920x1080.
- **moments**: A "Dawn, bare ribs" (turn 1, 0 deg, stage 1) and B "Night, she's finished" (turn 4, 270 deg, stage 4).
- **music**: a shipwrights' work song, not the style's synth default (the request asks for it): 6/8 at 72 bpm (dotted quarter), D mixolydian, concertina lead, plucked bass, caulking mallets, a hand-saw rasp.

## 1. Purpose and delivery
- Two stills for the pixelate-anything showcase, seen full screen and as gallery thumbnails: out/07-a.png and out/07-b.png at 1920x1080, out/07-a@1x.png and out/07-b@1x.png at 640x360, palettes as out/07-a-palette.json and out/07-b-palette.json.
- Sound: sound/07-sample.wav (48 kHz, 16-bit, stereo) and sound/07-sample.mp3, exactly 5.0 s.
- No loop is delivered; the four turns are described so the model is complete, two are rendered.

## 2. Style and light regime
- Style `tactics`; light regime none: every face is a palette step chosen from N.L of the key light (lstep: shade 1, glancing 2, lit 3, face-on 4), cast shadows two steps down from iso.cast_shadows, no light layer, no post ops.
- Ramps: five near-neutral stone greys carry the stage; warm ramps only for the ship (oak, trim) and, at night, for lantern-lit wood and ground (oakW, timberW, stoneW).
- Outline: black (`ol`) where shapes meet the void; one step darker between near and far objects; 1 px white spec strokes on the hero's upper edges and its edges toward the light.
- Learn the grammar only: no game's units, boards, UI or palettes are copied. No text and no UI on the frame.

## 3. Art direction rules
- One model, four turns: every object is placed once in model coordinates; a turn rotates those coordinates (Turn.pt) before iso.py sees them, so the camera and the sun stay fixed and the yard spins.
- The ship is the only warm, saturated thing by day; by night the lanterns are, and the ship's lanterns are the hottest.
- Hand-placed and asymmetric: frames at uneven spacing with a doubled pair amidships and heads standing 0 to 2.6 units proud of the sheer; keel blocks of eight different sizes; shores at different angles; plank lengths and sticker positions hashed per board; logs of five diameters.
- Named imperfections: a sprung plank lifting off the top of the stack; the crane's third brace re-pinned crooked; a patched tarp with a darker stitched square; the lock gate weeps into a wet tongue on the dock floor; two pale new shingles on the hut roof; the near ribband not yet fitted.
- Forms are filled planes split along real structure: hull strakes follow the sheer, deck seams follow the keel line, roof shingles run parallel to the ridge, stone courses on the slab's cut faces.
- Silhouette keys: the ship is a wooden hull with a keel, ribs (U-frames), a curving sheer line and a raked curving stem (not a fish skeleton or a fence: the stem and sternpost stand above the frame heads at each end); the crane is a lattice timber mast with a laddered jib and a hanging block (not a tower or a ladder: the jib angles out over the dock and the rope drops straight); the lock gate is a pair of mitred timber leaves meeting in a V upstream with balance beams lying back over the coping (not a fence: the V points into the canal).
- Light direction: A, low dawn sun from screen left (world (-0.45, 0.80, 0.42)), 25 deg up, shadows streaking right; B, moon from screen right (world (0.85, -0.30, 0.55)), 31 deg up, shadows falling left.
- Wind: light, from screen left: the dawn chimney smoke leans right; at night the pennants stream right.

## 4. The scene
- Projection: 2:1 iso, Iso(scale=1): +1 x is 2 px right and 1 down, +1 y 2 px left and 1 down, +1 z 1 px up. Canvas 640x360; the slab is centred and fills about 75% of the width, floating in calm darkness.
- World (model units): slab 136 x 100, top z 0, cut faces to z -18 with two inset underside tiers to z -27. Graving dock x 10-104, y 28-66 with three altar steps (z -1.5, -3, -4.5, each 2 wide) down to a flagged floor at z -6. Entrance x 104-112, y 36-58, gate leaves hinged at x 106 (y 36 and 58) meeting at x 109.2, y 47; balance beams run 8.5 units back over the coping. Canal x 112-122 along the whole slab, water at z -2.6. Far bank x 122-136.
- Ship: hull field from station u (transom 0 .. stem 1): length 80 (x 18-98), beam 20, keel z -4 on keel blocks, depth 17, sheer rising 4 aft and 7 forward (z 13 amidships, 17 at the transom, 20 at the stem head), raked transom, the forefoot curving up into a raked stem; 16 frames moulded 1.5, sided 1.2-1.4.
- Build stage (one parameter, same field): 1 frames, keelson and one ribband; 2 planked shell (strakes on eta, tarred below a waterline at z 2.5, an ochre boot-top, a wale); 3 adds deck, bulwarks, cap rail, deckhouse, hatch and capstan; 4 adds mast (40 + 10 units), yard with a furled sail, bowsprit, rigging, two pennants and lit lanterns.
- Crane: lattice mast 6 x 6 x 46 at x 48-54, y 12-18 on a stone footing, five girts, alternating diagonal braces, a cap; a laddered jib from z 7 out to (53, 31.5, 33) over the far altars; the block hangs on its rope to z 19; winch drum at the foot.
- Sawpit x 20-38, y 76-82, boarded, floor at z -4.5 with a sawdust heap; two trestles; at dawn a 22-unit log (r 1.9) with the pit saw standing in it; at night three sawn boards and the saw leaning on the trestle.
- Plank stack x 47-80, y 78-86 on three bearers: four stickered layers at dawn, two at night; the sprung plank on top; a patched canvas tarp over the far end.
- Chandlery hut on the far bank x 123.6-135, y 57-75, walls 9, shingle roof ridge along y to z 15, a stovepipe; shop window on the canal side, door and small window on the front; a landing stage, two barrels, a crate, a coil of rope; a 14-unit dory moored in the canal.
- Turn: k quarter-turns about (68, 50); A is k 0 (the canal and hut on the right, the dock head upper left), B is k 3 (the stern toward the viewer, the moonlit starboard side facing right, the canal and hut at the back right).
- Hero: 223,119,389,209 (native px); peak value: the ship's sunlit frames and their spec strokes; peak chroma: the ship's sunlit frames
- Planes: void 72% (darkest), dock pit and canal 6% (dark), slab cut faces 4% (dark), yard ground 12% (mid), crane, sawpit, plank stack, hut 4% (mid), ship 2% (brightest)
- Layout: the slab occupies x 85-555, y 75-335; the ship and dock own the centre (x 170-450, y 100-240); the crane rises upper centre-right (x 330-380, y 75-180); the sawpit and plank stack sit lower left (x 150-300, y 150-235); the canal, gate and hut take the right third (x 380-555). The void is the calm area: nothing sits in it but the slab and the chimney smoke.
- Masses: the yard's things are three sizes: the ship and dock (about 45% of the slab's width), the crane and the plank stack (about 15% each), the hut, sawpit and logs (about 8% each); never a row of equal boxes.
- Value plan (A): darkest, the void (L .085) and black outlines; dark, the dock pit, the canal and the cut faces in shadow (L .16-.23); mid, the sunlit yard and its props (L .31-.47); brightest, only the ship's sunlit frames (L .60-.74) with spec strokes (L .93). (B): darkest, the void (L .06); dark, the yard in moonshade (L .10-.18); mid, moonlit tops and faces (L .22-.28) and the moonlit hull (L .31-.52); brightest, the ship's deck lanterns (L .95) and its warm-lit wood.

## 5. Lived-in details
- A: the next frame lies on two blocks waiting to be raised (about 30 x 14 px, one step above the ground); the log on the trestles with the pit saw standing in it (44 x 12 px); an off-cut pile of five different ends (10 x 6 px); the tar pot on its tripod by the coping (6 x 10 px); the hanging block (5 x 11 px, black-outlined against the far altars); smoke from the chandler's stovepipe (15 x 13 px, L .53 against darker ground).
- Both: the moored dory, the coil of rope and the barrels by the hut, the wet tongue under the gate, the worn patches along the front coping, sawdust and chips round the pit.
- B: the sawn boards, a lower plank stack (two layers), the lit stern windows and deckhouse window, a lantern on the crane mast, the leaning saw.

## 6. Phases
- Accent ration: amber oak (C .08-.10) only on the ship's sunlit frames by day; at night lantern amber (lampH, lampA, win, oakW, timberW, stoneW, refl) only at the three lit places and their pools and reflections; the pennant red (C .16) only on the ship's two pennants. Together under 2.5% of the frame above C .08.
- Dawn (A): blue-black void, five cool-to-warm greys, amber oak glowing on the frames, pale warm smoke. Signature: bare frames, long raking shadows streaming right, the next frame waiting on the ground.
- Noon (turn 2, described): neutral greys, short shadows, planked hull in natural oak over black tar.
- Dusk (turn 3, described): low sun from the right, long shadows left, deck and rails on.
- Night (B): violet-black void, cool moonlit greys, warm lanterns: the stern lantern on its post and a lantern at the bow (hottest, L .95), the shop window over the canal and a lantern on the crane (L .74-.84); warm hand-shaped pools on deck and ground; their reflections broken into dashes on the canal. Signature: mast, furled sail, pennants, lit stern windows.
- Music: a shipwrights' work song in 6/8, dotted quarter 72 bpm, D mixolydian: concertina lead (two detuned pulse/saw oscillators through a band-pass with a bellows swell per phrase), plucked bass on the downbeats, caulking-mallet knocks on the beats, a hand-saw rasp twice, a small room reverb. The tune is our own. Sync point: the sample starts on a downbeat.

## 7. Light list
- A: the sun only (palette steps and cast shadows).
- B: moon (palette steps and cast shadows); stern lantern on a post at the taffrail and a bow lantern (cores lampH, L .95; pools on deck in oakW, about 8 x 5 units, irregular); crane lantern on the mast at z 21 (lampA; a ground pool in stoneW about 9 x 6 units, cut by the mast's shadow side); the shop window over the canal (win; a spill on the landing stage and a broken reflection on the water below it). No flicker in a still.

## 8. Motion table
- Stills only: no motion. If animated later: the turntable advances one quarter-turn in 6 held key drawings with a 1 px settle, the block sways 2 frames at 2 fps, smoke 3 drawings at 4 fps.

## 9. Particles
- None. The smoke is one hand-typed plume (15 x 13 px); no rain, dust or stars, so the darkness stays calm.

## 10. Never
- No light layer, glow, bloom, fog, vignette or soft shadows; no dither; no stars or texture in the void; no saturated scenery; no symmetry or stamped rows; no text; no figures.

## 11. Technical
- Native 640x360, 3x nearest to 1920x1080; every cell flat; one palette per image (about 50 slots each), exported as JSON.
- Gate A: `pixelate check out/07-a.png --style tactics --scale 3 --brief brief.md --pal out/07-a-palette.json`.
- Gate B: `pixelate check out/07-b.png --style tactics --scale 3 --brief brief-b.md --pal out/07-b-palette.json` (brief-b.md holds image B's Hero line).
- Block-in: `pixelate check out/blockin-a.png --blockin --brief brief.md`.
- Gate overrides: none.
