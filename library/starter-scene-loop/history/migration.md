# Starter: Scene Loop: migration notes (phase 1)

Moved with `git mv` from `templates/starter` into `library/starter-scene-loop` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description ("Hilltop Cabin: a starter scene for pixelate-anything") instead of inventing a request. Template from the first kit commits; no request exists.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`starter`. docs/PLAN-library.md section 2.1 defines a starter as "an empty piece for one mode" that "renders, passes the gate empty". The inherited template drew a recognisable cabin, pine, moon and rain, so a follow-up replaced that subject with a neutral scaffold instead of only relabelling it.

What the piece draws now, and what it does not:

- It draws: a three-band sky, flat ground with an edge line, a flat foreground strip, one grey box (`marker`) with a pulsing centre, two flat drifting blocks (`block`) and, in the `night` phase only, 24 single-pixel motes. Phases are `day` and `night` (were `dusk` and `rain`); outputs, palettes and music entries are named the same way.
- It does not draw any authored subject: no building, tree, hill, weather, moon, cloud or creature. `tests/test_library_migration.py` (`StarterSceneLoopTest`) fails if such words come back in the piece's files, if a sprite other than `marker` and `block` is defined, or if phase names drift apart.
- It is not a literally blank frame, and cannot be under the stock gate (see below). Read "empty" as "no authored subject, placeholders only".

## What was kept and what changed

Kept: the engine hooks `sceneBack`, `sceneObjects`, `sceneDynamic` and `sceneParticles` (`sceneInit` is gone because nothing needs precomputing; `sceneFront` was never used), the 240x135 canvas at 8x (1920x1080 frames), the 60 s cycle with `grand: 2` (120 s picture loop), the `lofi` style, the soundtrack's chords, scales, drums and tempos, and the editable `config.js` and `scene.json`. Every animation period still divides the loop (drift trips, motes, marker pulse); `pixelate check .` confirms determinism and the loop seam.

Changed: `scene.js`, `sprites.js`, `palettes.js` and `config.js` slots rewritten around placeholders; `music.js` only renames its phases and swaps the night phase's rain ambience for a quiet wind bed (rain no longer matches the picture); `piece.json` summary, subject and setting tags and anatomy; the two goldens are renamed `out/golden/day.png` and `out/golden/night.png` (and are new images); `media/` shows them. The cabin palette's `S4` fix from the first migration is gone with the palette. `palettes/hilltop-dusk.hex` and `hilltop-rain.hex` are standalone presets of the old cabin colours; nothing references them, they are outside this piece and were left unchanged.

## Why the bottom third is not empty

The stock frame gate has a composition check, `empty_low`: at most 88% of the bottom third's cells may be empty (a cell is busy when 3% of its pixels differ from its own median colour by 0.12 OkLab). A bare sky over flat ground fails it at 97%. The scaffold clears it with a flat foreground strip with a lit edge (cell-straddling at row 117) and the grey box; the frame measures 77% empty. This is a real property of the gate, not something this piece overrides. If a literally blank starter is wanted, a starter-specific rule is needed rather than a global recalibration, for example a declared per-piece budget on `empty_low` (`pixelate check ... --budget 'empty_low 1.0 (starter: blank by design)'`) limited to `status: starter` pieces. That is a decision for the plan's owner and is not implemented.

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `day`: `python3 "$PIXELATE_KIT/pixelate" shot . 0 --zoom 8 --out out` writes `out/t0000.00.png` (1920x1080, scale 8); the golden `out/golden/day.png` is its NEAREST 1x downsample (240x135); `pixelate check out/t0000.00.png --scale 8 --style lofi`: gate PASS, no warnings (L>=0.7: 0.00%, median C 0.050, bottom-third empty 77%).
- `night`: `shot . 30 --zoom 8 --out out` writes `out/t0030.00.png`; golden `out/golden/night.png`; gate PASS, no warnings (L>=0.7: 0.07%, median C 0.041, bottom-third empty 77%).
- Representative frames over the loop: frames at t = 0, 2, 4 .. 118 s (60 frames) through the `lofi` gate: 56 pass with no warning; the four at t = 26, 58, 86 and 118 s fail (`cluster_px` or `small_clusters`). Those are the middle of the engine's ordered-dither phase change (about 26 to 28 s and 57 to 59 s, repeating each 60 s), where every colour shatters into 1 px clusters. The cabin scene this replaced fails the same way at the same moments (checked at 26.5, 27, 27.5, 57.5, 58 and 58.5 s on the previous commit), so this is the engine's dissolve against the stock gate, not a regression, and it is not a delivered still (the declared images are t=0 and t=30). Not overridden or hidden; the test gates the steady frames and says so.
- `pixelate check .`: ALL OK (sprites, timing, determinism, loop seam).
- The clean-copy tests also run the piece alone, in a folder with no `library/` next to it, and pass.

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review. Also not checked: the page build (`pixelate check . --page`) and the rendered soundtrack (the 120 s file was not rendered or committed; the music changed only in phase names and one ambience bed).

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Decide whether a literally blank frame is wanted; if so it needs the starter-specific `empty_low` rule above.
- Decide how the engine's phase dissolve should be treated by the gate (exempt mid-dissolve frames, or shorten or reshape the dissolve); this affects every engine scene, not this piece alone.
- Render the soundtrack and run the music gate.
