# Rose Squall: migration notes (phase 1)

Moved with `git mv` from `examples/indie` into `library/rose-squall` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. The commit message describes it as "a lighthouse on a sea stack in a rose squall (pastel platformer style)"; it studies the modern pastel platformer grammar, never its characters or places.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`study` until audited (§6.2).

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `rose-squall`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/rose_squall@6x.png` (1920x1080, scale 6); identical across both runs: True; `pixelate check out/rose_squall@6x.png --scale 6 --style pastel-cell`: gate FAIL (composition blocky 0.19 [ .. 0.12]). Golden `out/golden/rose-squall.png` is the NEAREST 1x downsample (320x180).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Audit; fix or override with a reason the `composition blocky` gate failure; add knobs; independent critique.
