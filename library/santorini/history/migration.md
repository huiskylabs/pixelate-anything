# Santorini: migration notes (phase 1)

Moved with `git mv` from `examples/santorini` into `library/santorini` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. The reference is "Houses on Hill" by Vasilis Karkalas, https://www.pexels.com/photo/houses-on-hill-11222833/ (Pexels license); it is not in the repository.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`study` until audited (§6.2).

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `santorini`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/santorini@3x.png` (864x864, scale 3); identical across both runs: True; `pixelate check out/santorini@3x.png --scale 3 --style sticker-iso`: gate FAIL (budget black 0.00% [8.00% .. 30.00%]; budget L<=0.3 1.25% [30.00% .. ]) (warnings: 1). Golden `out/golden/santorini.png` is the NEAREST 1x downsample (288x288).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review.

## Dependency

`art/santorini.py` imports palettes.py from ../san-francisco/art (library/san-francisco), so this piece is not self-contained. The import path was changed from `examples/san-francisco/art` to `library/san-francisco/art`; no other drawing code changed. A copy of this folder outside the kit tree (a remix) breaks until the shared helper moves into `tools/`.

## Licensing and provenance

The reference is "Houses on Hill" by Vasilis Karkalas, https://www.pexels.com/photo/houses-on-hill-11222833/, under the Pexels license (docs/gallery/SOURCES.md). The photo is not in the repository. Whether art rebuilt from it is licensed as MIT was not assessed here.

## To promote

- Audit the Pexels reference use; add real knobs; run `pixelate judge` and an independent critique; approve or demote.
