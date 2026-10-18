# Ten moments

Ten showcase requests for pixelate-anything, ranked by expected impact. Each one is rendered at its two best moments, with a five-second sound sample. Everything is drawn from scratch in code with the kit. They lived in `examples/moments/`; phase 1 of `docs/PLAN-library.md` moved them (with `git mv`, so history follows) to `library/<id>/`, each with a `piece.json` manifest (spec: `references/piece.md`).

Every piece is `study` for now. The migration did not earn `accepted`: see [Status and what promotion needs](#status-and-what-promotion-needs).

| id | former folder | what you see | style, canvas | sound |
|---|---|---|---|---|
| [monsoon-street](../../library/monsoon-street) | 01 | A: the tram crosses the vanishing point in a downpour. B: at 2 a.m. the puddle mirrors the street. | rebuild of a Pexels photo in its own one-point camera; `cosy-lightmap` exterior, 480x270 at 4x | felt piano and brushes in B minor, rain bed, tram bell |
| [endless-ascent](../../library/endless-ascent) | 02 | A: the gondola passes the clock of a town carved into a giant trunk. B: it rises out of a cloud sea under the aurora. | `lofi`, 270x480 at 4x | guitar and Rhodes at 76 bpm, clock bell |
| [canyon-cycle](../../library/canyon-cycle) | 03 | A: a rose sunset with lightning on the mesa. B: indigo night. Both decode from one index array. | `lofi`, 320x180 at 6x, palette cycling | ambient: thunder, wind and fire bed, music box |
| [tide-procession](../../library/tide-procession) | 04 | A: nine lanterns cross the causeway. B: the monastery door opens and spills light down the steps. | `contre-jour` beam, 640x360 at 3x | D Dorian drone, waves, bronze bell |
| [four-machines](../../library/four-machines) | 05 | A: one moment under four console limits (poster). B: the 16-bit panel at 4x. | Game Boy-, NES-, SNES- and GBA-style; each passes `pixelate era` | 16-bit arrangement: strings, FM bass, echo |
| [quarry-wakes](../../library/quarry-wakes) | 06 | A: a dredging machine breaks out of a flooded quarry. B: its leg slams the rim. | `arcade`, 304x224 at 4x, layers checked against `neogeo` | FM boss sting in E minor at 168 bpm |
| [turntable-shipyard](../../library/turntable-shipyard) | 07 | A: dawn, bare ribs on the keel. B: night, the finished ship a quarter-turn later. | `tactics`, one 3D description in `iso`/`sdf`, 640x360 at 3x | 6/8 work song: concertina, mallets, saw |
| [market-day](../../library/market-day) | 08 | A: Strasbourg's street and squares at noon, full of market stories. B: the wedding on the hall steps at 8x. | rebuild of a Pexels aerial; `sticker-iso`, 600x600 at 4x | oom-pah march in B♭ over a crowd murmur |
| [lanternmoss-mire](../../library/lanternmoss-mire) | 09 | A: the asset pack's map by day. B: the same tiles at night, glowing. | asset pack (runtime `pack`): 16x16 tiles, 16x24 hero, map 320x192 at 4x | chip SFX reel and item-get jingle |
| [tidewater-signal](../../library/tidewater-signal) | 10 | A: a keeper's radio on the sill in a storm (cassette cover). B: the lightning frame. | `lofi`, 270x480 at 4x | the overworld cue: pulse leitmotif at 132 bpm |

## Layout of a moved piece

```text
library/<id>/
  piece.json       manifest: request, tags, outputs (with run commands), anatomy, provenance
  brief.md         the original short brief (brief-b.md: gate lines for image B where it existed)
  art/ sound/ music/   the original source, unchanged (09: also pack.json, palette*, sprites/, maps/)
  out/             the delivered frames the programs write, and out/golden/ (below)
  media/           thumb.png (<= 256 px) and contact.png (A and B tiles, each <= 256 px)
  .gitignore       the narrow exception that tracks out/ frames and goldens (the repo ignores out/)
```

The drawing code is as it was made. No file under `art/`, `sound/`, `music/`, `maps/` or `sprites/` was edited; they are 100% renames in git.

## Rebuild

Run commands now live in each `piece.json` `outputs[].run`. They run from the piece folder, and assume the runner supplies the kit:

- `PYTHONPATH=<kit>/tools`, because the drawing code does `from canvas import ...` (it also inserts a hardcoded `/home/user/pixelate-anything/tools`, which does not exist elsewhere).
- `pixelate` resolvable on `PATH` (it is `<kit>/pixelate`), for `pixelate audio` and `pixelate assets`. The old `../../../pixelate` shell paths no longer apply.
- `bash` as the shell, `ffmpeg` with libmp3lame, and, for the five engine-music pieces (01-04, 10), Playwright Chromium.
- `scipy` for 01's art and for most sound scripts (see `requirements.txt`: it lists only `pillow` and `numpy`).

Corrections to the old README table (found by running the commands from a clean copy):

| piece | old README | actual |
|---|---|---|
| 07 | `python3 art/yard.py a` and `b` | those write only `out/draft-*.png`; the delivered stills come from `python3 art/yard.py export` |
| 08 | `python3 art/scene.py final out 130 162` | the committed `08-b.png` is the crop at offset `142 162`; `130 162` gives a different crop |
| 08 | `python3 sound/march.py` | needs the output path: `python3 sound/march.py sound/08-sample.wav` |
| 05 | stills only | `out/05-b.png` is byte-identical to `out/panel-snes@4x.png`; the four `panel-*@4x.png` frames were not tracked and now are |
| all | `ffmpeg` "afterwards" | the mp3 is `ffmpeg -i NN-sample.wav -codec:a libmp3lame -q:a 2 NN-sample.mp3` (03 and 10 do it inside their script) |

01's `pixelate audio` returns exit code 2 (a "loop is not seamless" warning) while still writing the wav; its run command accepts that code.

## Goldens: the convention used here

`outputs[].frame` is the **delivered** render at `scale` (for example the 1920x1080 `out/01-a.png`). It is generated by the run command and tracked as the original deliverable. A separate 1x **golden** sits at `out/golden/<output name>.png`, declared as `golden` on the image output, with `size: {w, h}` where the output differs from `canvas` (05's four panels, in place of a canvas that fits the poster).

A golden is the delivered frame reduced to 1x RGBA with PIL's `Image.resize((w, h), Image.NEAREST)`, so `frame size == size x scale`. It is *not* a copy of any `@1x.png` the programs write: 01 and 04 deliver a screen-resolution light layer over the pixel layer, and their `@1x`/`-pre` files are the pre-light layer.

**The catalog schema at head e9b46c7 does not know `golden` or `size`, and rejects them.** `python3 tools/library.py list` therefore fails on these ten manifests until the runtime schema lands. Until then, validate a copy with those two keys removed from every output. `tests/test_library_moments_migration.py` does exactly that.

Follow-up contract for `library test`:
1. Accept `golden` (image outputs, default `out/golden/<name>.png`) and `size`; reject a golden that is missing, a link, not a PNG, or of the wrong size.
2. Render from a clean copy, downscale the frame with `Image.NEAREST` to `size` (or `canvas`), convert to RGBA, and require exact equality with the golden; report the differing-pixel count and bounding box.
3. Give the renderer the kit environment above; run `run` under `bash`; treat a missing optional dependency (scipy, Chromium, ffmpeg) as skipped, not as a green pass.
4. Do not compare audio bytes (below), and do not run contributed code in CI without the trust policy.

## What was run, and what it showed

Environment: catalog head `e9b46c7` plus this migration; Python 3.12.3, numpy 2.5.4, Pillow 12.3.0, scipy 1.18.1, ffmpeg 6.1.1 (libmp3lame), Playwright 1.63.0 with Chromium 153 (its libnss3 and libnspr4 were missing and came from extracted Ubuntu packages via `LD_LIBRARY_PATH`). Each piece was copied from the tracked files into a clean directory, its tracked frames deleted, and every image and export `run` executed with `PYTHONPATH=<kit>/tools` and a 30 minute timeout. Then each image output was gated with the arguments `tools/render.py` would pass, and compared with its golden.

- **Images.** Every delivered frame, export and palette regenerated **byte-for-byte identical** to the tracked file, and every golden matched with 0 differing pixels. Gate (`pixelate check`) result per image output: monsoon-street a, b 19 PASS 0 FAIL; endless-ascent 20/0; canyon-cycle 20/0; tide-procession 27/0; four-machines gb 12/0, nes 11/0, snes 12/0, gba 12/0; quarry-wakes 19/0; turntable-shipyard 18/0; market-day a 21/0; lanternmoss-mire 15/0; tidewater-signal 20/0. A technical gate pass is not approval.
- **03 and 04 cannot render in place.** `canyon-cycle/art/render.py` and `tide-procession/art/scene.py` (and both `blockin.py`) write to hardcoded `/home/user/pixelate-anything/examples/moments/<folder>/out/`. In a clean copy the declared commands fail (`FileNotFoundError` for 03, `PermissionError` on `/home/user` for 04). They reproduce byte-identically only in a temporary copy whose absolute paths were rewritten by `sed`; the sources here are unchanged. For that reason their manifests carry no `kit.tested`, and a CI render of these two needs the path fix first (a `__file__`-relative `ROOT`).
- **08 image B is an export, not a gated image.** `08-b.png` is an 8x crop of the wedding from image A, and it fails the gate (budget L<=0.3 at 20.45%, composition empty 57.55%). The brief only ever gated A. It is declared as an `export`, with no golden.
- **05's poster is an export.** The poster and `05-b.png` are composites of four separately gated panels; the gated outputs are the four `panel-*@4x.png` frames (style `lofi` with the panel's era).
- **Audio is not reproducible bytewise here.** Re-running the declared sound commands gave identical mp3s for 08 and 09 only. The others differ from the committed mp3 (relative RMS difference: 02 0.3%, 10 0.3%, 01 0.5%, 03 0.7%, 07 12%, 05 17%, 04 17%, 06 30%). The 06 and 07 synths were run twice here and matched themselves, so the committed samples were probably made by an earlier script or library versions. The committed mp3s are kept as the delivered artifacts; the manifests' audio `run` commands are not claimed to regenerate them.

## Reference photos and licensing

The code, characters, titles, glyphs and tunes are original and are covered by the repository's MIT license (plan decision D1). That is a statement about this repository, not an independent license review. 01 and 08 rebuild photos from Pexels (Pexels license). They are rebuilt, not converted, and the photos are not in the repository. Their `provenance.by` credits them.

- monsoon-street: [Night City Street after Rain Illuminated by Colorful Neon Signs Reflecting on a Wet Road](https://www.pexels.com/photo/night-city-street-after-rain-illuminated-by-colorful-neon-signs-reflecting-on-a-wet-road-18867525/) by Johannes Plenio
- market-day: [Aerial View of Medieval Buildings on an Old Town](https://www.pexels.com/photo/aerial-view-of-medieval-buildings-on-an-old-town-14037897/) by Nick Verlice

## Status and what promotion needs

All ten are `study`: they render (see above) and carry tags, anatomy and provenance. None may be called `accepted` yet:

- **No approval evidence exists in the repository.** The showcase run used a coordinating agent as art director, but no critique or approval record was kept with the pieces. `review` is therefore omitted. Approval by `user` or `art-director`, and review notes with real content, are still to be supplied for each piece.
- **No working knobs.** `knobs` is `{}`. `accepted` needs two, and `tools/piece.py`, `PIXELATE_KNOBS` and `render --set` do not exist yet (plan phase 2). The art does not read knobs. Declaring any would be a claim that nothing backs.
- **`reviewed`** additionally needs a `pixelate review record` sidecar and an independent A-grade review bound to the exact bytes. None was produced.
- **Requests.** `request` is the brief's own `Request:` line, joined across line breaks, for 01-04, 06-08 and 10. No literal request is recorded for 05 and 09, so their `request` says so and quotes the brief and README instead.
- **Media.** `media.thumb` and `media.contact` exist for all ten (derived from the delivered frames with PIL `LANCZOS`; contact tiles are A and B side by side, each at most 256 px, so a contact sheet is up to 516 px wide). No GIF or sound preview clip was made.

## Not done here

- `quarry-wakes/render.json` was removed because `piece.json` carries the same two images with the same fields (name, run, frame, style, scale, brief, pal, actor), and a piece with both is ambiguous for `pixelate render`. `references/delivery.md` still names that file (outside this migration's paths).
- `evals/run.py` filters `examples/moments/` out of the skill-arm snapshot. The answers now live in `library/`, so that filter has to cover `library/` too, or the benchmark's held-out answers leak. `references/delivery.md` (which also cites the removed `render.json`) and `evals/README.md` still cite `examples/moments`. Those files are outside this migration's allowed paths.
