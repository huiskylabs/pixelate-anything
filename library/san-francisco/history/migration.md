# San Francisco: migration notes (phase 1)

Moved with `git mv` from `examples/san-francisco` into `library/san-francisco` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. The aerial photo of the Financial District and the Transamerica Pyramid was supplied by the user; it is not in the repository.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`study` until audited (§6.2).

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `sf-rebuild`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/sf_rebuild@3x.png` (720x1080, scale 3); identical across both runs: True; `pixelate check out/sf_rebuild@3x.png --scale 3 --style sticker-iso`: gate FAIL (budget black 0.00% [8.00% .. 30.00%]; budget L<=0.3 2.05% [30.00% .. ]). Golden `out/golden/sf-rebuild.png` is the NEAREST 1x downsample (240x360).
- `iso-city`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/iso_city@3x.png` (864x864, scale 3); identical across both runs: True; `pixelate check out/iso_city@3x.png --scale 3 --style sticker-iso`: gate FAIL (budget black 0.00% [8.00% .. 30.00%]; budget L<=0.3 1.40% [30.00% .. ]) (warnings: 1). Golden `out/golden/iso-city.png` is the NEAREST 1x downsample (288x288).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review.

## Licensing and provenance

The reference photo of the Financial District and the Transamerica Pyramid was "supplied by the user" (docs/gallery/SOURCES.md) and is not in the repository. No license for it is recorded, so its terms are unknown; this note does not assert any, and nobody has recorded consent from the photo's author or the user's right to redistribute art rebuilt from it.

**Human gate before MIT publication:** this piece is kept in the library because the plan counts 17 pieces, but the rights to publish a rebuild of that photo under MIT are unestablished. A person must either document the photo's license or the user's permission, or decide to replace, re-derive or withdraw the piece (and the Pixel Harbor city in `retro-screens`, which is a copy of this piece's city) before the library is published. Migration did not resolve this.

## To promote

- Resolve the rights gate above; audit: confirm the supplied reference photo may be used for rebuilt art; add real knobs (time of day) once `--set` exists; run `pixelate judge` and an independent critique; approve or demote.
