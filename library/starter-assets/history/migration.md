# Starter: Assets: migration notes (phase 1)

Moved with `git mv` from `templates/assets` into `library/starter-assets` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. Template from the initial kit commit; no request exists.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`starter`: `pixelate assets .` exits 0 with no warnings, and every export is byte-identical across two independent clean renders. It is a template, not a recommended finished base.

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `atlas-image` (export): `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/atlas.png` (394 bytes); byte-identical across both runs: True.
- `atlas-data` (export): `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/atlas.json` (625 bytes); byte-identical across both runs: True.
- `contact-sheet` (export): `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/contact.png` (2651 bytes); byte-identical across both runs: True.

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Nothing needed for `starter`.
