# Lantern Isle: migration notes (phase 1)

Moved with `git mv` from `examples/lantern-isle` into `library/lantern-isle` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original prompt is kept word for word in `brief.md` and in `piece.json` `request`.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`study`, not `accepted`. docs/PLAN-library.md §6.2 proposes `accepted` because it is "the bar", and references/art-director.md and guides/scenes.md call it the quality bar, but the repository holds no recorded approval by a named user or art director, no review notes, and no knobs. A piece is `accepted` only on evidence, so this one starts as `study` and is promoted once the work below is done.

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `spring`: `python3 "$PIXELATE_KIT/pixelate" shot . 15 --zoom 4 --out out` writes `out/t0015.00.png` (1920x1080, scale 4); identical across both runs: True; `pixelate check out/t0015.00.png --scale 4 --style lofi`: gate PASS. Golden `out/golden/spring.png` is the NEAREST 1x downsample (480x270).
- `summer`: `python3 "$PIXELATE_KIT/pixelate" shot . 45 --zoom 4 --out out` writes `out/t0045.00.png` (1920x1080, scale 4); identical across both runs: True; `pixelate check out/t0045.00.png --scale 4 --style lofi`: gate PASS. Golden `out/golden/summer.png` is the NEAREST 1x downsample (480x270).
- `fall`: `python3 "$PIXELATE_KIT/pixelate" shot . 75 --zoom 4 --out out` writes `out/t0075.00.png` (1920x1080, scale 4); identical across both runs: True; `pixelate check out/t0075.00.png --scale 4 --style lofi`: gate PASS. Golden `out/golden/fall.png` is the NEAREST 1x downsample (480x270).
- `winter`: `python3 "$PIXELATE_KIT/pixelate" shot . 105 --zoom 4 --out out` writes `out/t0105.00.png` (1920x1080, scale 4); identical across both runs: True; `pixelate check out/t0105.00.png --scale 4 --style lofi`: gate PASS (warnings: 1). Golden `out/golden/winter.png` is the NEAREST 1x downsample (480x270).

Also run: `pixelate check .` (ALL OK: sprites, timing, determinism, loop seam).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review. Also not checked: the page build (`pixelate check . --page`) and, unless listed above, the rendered soundtrack.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Record who approved it (the user or the art director) and write review notes, then set `review`.
- Add at least two working knobs. The engine knob surface is `scene.json`/`config.js` (phases, order, palette slot meaning); decide which two (for example season and mood) and implement them for `--set`.
- The 360 s soundtrack loop was not rendered or committed (`pixelate audio . out/loop.ogg`; Playwright Chromium needed). Render it once, or commit a short preview clip with sound under `media/`.
- For `reviewed`: add `brief` (with a `## Image NAME` section per frame), an A-grade critique saved inside the piece, and `pixelate review record`.
