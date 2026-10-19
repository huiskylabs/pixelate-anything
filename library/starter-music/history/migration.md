# Starter: Music: migration notes (phase 1)

Moved with `git mv` from `templates/music` into `library/starter-music` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description ("Pixel Radio: a music-first template") instead of inventing a request. Template from the initial kit commit; no request exists.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`starter`. docs/PLAN-library.md section 2.1 defines a starter as "an empty piece for one mode" that "renders, passes the gate empty". The inherited template was an authored chiptune overworld phase handing off to an ambient drift phase under a "Pixel Radio" title, so a follow-up replaced that with a generic scaffold instead of only relabelling it.

What the piece holds now, and what it does not:

- It holds: two plain phases, `part_a` (`style: 'chiptune'`, 120 bpm) and `part_b` (`style: 'ambient'`, 70 bpm), a four-chord loop each, a hand-off each way, melody scales of five notes with a modest chance of a phrase (`mel` 0.5 and 0.2), and a twelve-band equaliser in slate blues, titled "Music Starter".
- It does not hold: a written-out tune, a motif or hook, a scene story, or the names overworld, drift or radio. The melody is the engine's own phrase generator running over `scale`; nothing in `music.js` spells out a melody. `tests/test_library_migration.py` (`StarterMusicTest`) fails if those words or tags return, if a scale grows past five notes or `mel` past 0.5, if the phase names drift apart across `config.js`, `palettes.js` and `music.js`, and it runs the music loop gate on the committed `out/loop.ogg`.
- It is not silent or blank, and cannot usefully be: a silent track has no tempo or key and fails the music gate, and a blank frame fails the stock `empty_low` check. Read "empty" as "no authored theme or subject".
- It is generic, not novel: the chord loops are the kit's own stock progressions (C G Am F; Am9 Fmaj7 Cmaj7 G6) and the hand-off chords were not changed. They are the kit's defaults, not an authored theme of this piece.

## What was kept and what changed

Kept: every kit API the guide documents (`SCENE`, `PALETTES`, `SCENE_MUSIC` with `phases` and `trans`, styles, `grand`, `cycle`, `bars`, slot names), the 160x90 canvas at 8x, the 48 s loop, the two declared outputs (`equaliser`, `soundtrack`), the equaliser drawing code in `scene.js` (it was already subject-free: bars from a hash of band and step), and the page `files` list.

Changed: phases renamed `overworld` to `part_a` and `drift` to `part_b` in `config.js`, `palettes.js` and `music.js`; the palettes from a green and gold game-like set to slate blues; the lead instrument override (`piano`) and `padVoice` (`musicbox`) on the second phase removed, so the ambient style's defaults apply; both melody scales cut from 8 notes to 5; `mel` from 0.9 and 0.45 to 0.5 and 0.2; the scene title and description; `piece.json` summary, tags and anatomy; the golden, `media/` and `out/loop.ogg` regenerated.

## Checked (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Run from an independent clean copy: a kit copy with no `library/`, `.git`, `docs`, `examples` or `tests`, and the piece alone in a folder of its own (no sibling library piece), with `PIXELATE_KIT` set to the kit copy and generated files removed first.

- `equaliser`: `python3 "$PIXELATE_KIT/pixelate" shot . 0 --zoom 8 --out out` writes `out/t0000.00.png` (1280x720); its NEAREST 1x downsample (160x90) is byte-identical to the committed `out/golden/equaliser.png`; `pixelate check out/t0000.00.png --scale 8 --style lofi`: ALL PASS with 1 heuristic warning (`repeat`: 1 row of near-identical units, four 9 px lobes at y 72; the equaliser's equal-width bars trip this heuristic; the notes for the previous version also record one warning). The test suite also checks this golden in both copies.
- `pixelate check .`: ALL OK (sprites and palettes, timing, determinism, loop seam).
- `soundtrack` (audio): `mkdir -p out && python3 "$PIXELATE_KIT/pixelate" audio . out/loop.ogg` writes `out/loop.ogg` (48 s, 1171233 bytes, loop seam -78.4 dB; below -60 dB is seamless). `pixelate check out/loop.ogg --use loop`: 13 PASS, 2 SKIP (hook and arc, checked only for showcase and song), no FAIL or WARN lines (-14.0 LUFS, tempo 121.5 bpm for 120 asked, key C, 79% of 24 bars new). The clean-copy render passes the same gate.
- Audio nondeterminism, reported and not treated as a golden failure: three renders of the same tree (two in the working tree, one in the clean copy) differ byte for byte; decoded to PCM, the second differs from the first by -51.1 dB and the clean-copy one by -50.3 dB relative RMS (the previous version's notes recorded about -70 dB). The committed `out/loop.ogg` is one of those renders. Tests check the file's gate result and the duration, not its bytes.
- Environment for the audio render: the sandbox's default python has no Playwright and the cached Chromium is build 1243 (Chrome for Testing 153.0.8010.12) while the Playwright 1.64.0 in `/tmp/pwlib` asks for build 1248, so the render ran with `PLAYWRIGHT_BROWSERS_PATH` pointing at a temporary folder that links `chromium_headless_shell-1248` to the 1243 build, and with `LD_LIBRARY_PATH` set to a user-space copy of the NSS and NSPR libraries the browser needs. Nothing of this is in the repository. A reviewer with `playwright install chromium` will not need it.

Not checked: `pixelate judge`, `pixelate critique`, `pixelate critique-music` and any human or art-director listening or review; the page build (`pixelate check . --page`). No claim about musical or visual quality is made.

## Licensing and provenance

No reference photos, samples or borrowed assets are used; every sound is synthesised. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1). No tune is quoted from any game, song or film.

## To promote

- Decide whether a starter should carry the kit's stock chord loops or something more neutral still; they are generic, not authored.
