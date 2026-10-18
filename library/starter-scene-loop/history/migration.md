# Starter: Scene Loop: migration notes (phase 1)

Moved with `git mv` from `templates/starter` into `library/starter-scene-loop` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. Template from the first kit commits; no request exists.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`study`, not `starter`. §6.2 starts this template as `starter`, which requires that it renders and passes the gate. It renders and its scene check passes, and the `rain` frame passes the `lofi` gate, but the `dusk` phase, which is the first picture a user sees (t=0), fails the `lofi` budget `L>=0.7` (12.5% of pixels against a 4% limit; measured at t=5, 10, 15 and 20 s, 8x). So it is not honestly a passing starter yet.

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `rain`: `python3 "$PIXELATE_KIT/pixelate" shot . 30 --zoom 8 --out out` writes `out/t0030.00.png` (1920x1080, scale 8); identical across both runs: True; `pixelate check out/t0030.00.png --scale 8 --style lofi`: gate PASS. Golden `out/golden/rain.png` is the NEAREST 1x downsample (240x135).

Also run: `pixelate check .` (ALL OK: sprites, timing, determinism, loop seam).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review. Also not checked: the page build (`pixelate check . --page`) and, unless listed above, the rendered soundtrack.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Make the dusk phase pass the `lofi` gate (lower the light sky bands or add a reasoned `- Gate override` in a brief), keep `pixelate check .` green, then set `starter`.
- The 120 s soundtrack was not rendered or committed.
