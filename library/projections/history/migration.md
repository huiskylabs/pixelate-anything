# Projections: migration notes (phase 1)

Moved with `git mv` from `examples/projections` into `library/projections` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. Guides/rebuild.md and guides/styles.md use it as the worked example of the five projections.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`study` until audited (§6.2).

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `projections`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/projections@2x.png` (1776x700, scale 2); identical across both runs: True; `pixelate check out/projections@2x.png --scale 2 --style tactics`: gate FAIL (budget C>0.08 10.41% [ .. 2.50%]; budget median_C 0.026 [ .. 0.020]). Golden `out/golden/projections.png` is the NEAREST 1x downsample (888x350).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review.

## Independence from other pieces

`art/projections.py` used to import `palettes.py` from `library/san-francisco/art` and used only `day()`. `art/cottage_palette.py` now holds `MATERIALS` and `day()` copied unchanged from that file (first-party, MIT) with an attribution header; the unused dusk, night and relight code was not copied. No other drawing code changed. The copy was checked by rendering this piece alone: the kit copy had no `library/` folder, the piece sat in a folder of its own, and the output matched the committed 1x golden pixel for pixel; the pack is fast, so the test always runs (`tests/test_library_migration.py`, `IsolatedCopyTest`). A remix copied out of library/ therefore needs only this folder and the installed kit.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Audit; the `tactics` gate budgets do not fit this colourful reference sheet (see above): decide the right style or a reasoned gate override; add knobs.
