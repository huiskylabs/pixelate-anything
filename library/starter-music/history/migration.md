# Starter: Music: migration notes (phase 1)

Moved with `git mv` from `templates/music` into `library/starter-music` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. Template from the initial kit commit; no request exists.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`starter`: the picture (a 160x90 equaliser) passes the `lofi` frame gate, `pixelate check .` passes, and the rendered 48 s loop passes the music gate (`pixelate check out/loop.ogg --use loop`). It is a template, not a recommended finished base.

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `equaliser`: `python3 "$PIXELATE_KIT/pixelate" shot . 0 --zoom 8 --out out` writes `out/t0000.00.png` (1280x720, scale 8); identical across both runs: True; `pixelate check out/t0000.00.png --scale 8 --style lofi`: gate PASS (warnings: 1). Golden `out/golden/equaliser.png` is the NEAREST 1x downsample (160x90).
- `soundtrack` (audio): `mkdir -p out && python3 "$PIXELATE_KIT/pixelate" audio . out/loop.ogg` writes `out/loop.ogg` (1173189 bytes); byte-identical across both runs: False. Audio is not byte-reproducible (the offline render differs by about -70 dB between runs): compare duration and the music gate, not bytes.

Also run: `pixelate check .` (ALL OK), and `pixelate check out/loop.ogg --use loop` (no FAIL or WARN lines).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review. Also not checked: the page build (`pixelate check . --page`) and, unless listed above, the rendered soundtrack.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Nothing needed for `starter`.
