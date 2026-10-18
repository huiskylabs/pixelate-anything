# Retro Screens: migration notes (phase 1)

Moved with `git mv` from `examples/retro` into `library/retro-screens` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. SOURCES notes describe the characters, places, titles and text as original; console names describe hardware limits only. The Pixel Harbor city is the san-francisco rebuild.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`study` until audited (§6.2).

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

Each output command was run from two independent clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `rooftop-run`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/rooftop_run@3x.png` (768x672, scale 3); identical across both runs: True; `pixelate check out/rooftop_run@3x.png --scale 3 --era nes`: gate FAIL (era tiles (whole frame) 351 tiles limit 256). Golden `out/golden/rooftop-run.png` is the NEAREST 1x downsample (256x224).
- `island-village`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/island_village@3x.png` (480x432, scale 3); identical across both runs: True; `pixelate check out/island_village@3x.png --scale 3 --era gameboy`: gate PASS. Golden `out/golden/island-village.png` is the NEAREST 1x downsample (160x144).
- `title-screen`: `python3 "$PIXELATE_KIT/pixelate" assets .` writes `out/title_screen@3x.png` (768x672, scale 3); identical across both runs: True; `pixelate check out/title_screen@3x.png --scale 3 --era nes`: gate FAIL (era tiles (whole frame) 791 tiles limit 256) (warnings: 1). Golden `out/golden/title-screen.png` is the NEAREST 1x downsample (256x224).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review.

## Independence from other pieces

`art/title_screen.py` used to import `city.py` (and through it `palettes.py`) from `library/san-francisco/art`. `art/harbor_city.py` and `art/harbor_palettes.py` are now copies of those two files (first-party, MIT, attribution headers). Changes against the originals: `city.py` imports `harbor_palettes`, and its `export()` and `__main__` probe were removed, because the pack loads every `art/*.py` and would otherwise add a second `iso_city` output to this piece. `title_screen.py` imports `harbor_city`. No other drawing code changed. The copy is about 400 lines of the san-francisco city, kept because Pixel Harbor is that city retargeted to the NES preset. The copy was checked by rendering this piece alone: the kit copy had no `library/` folder, the piece sat in a folder of its own, and the output matched the committed 1x golden pixel for pixel (`tests/test_library_migration.py`, `IsolatedCopyTest`; `PIXELATE_SLOW_LIBRARY=1` for this slow pack). A remix copied out of library/ therefore needs only this folder and the installed kit.

## Licensing and provenance

The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1). Rooftop Run and Island Village use no reference photo. Pixel Harbor (`title-screen`) is the san-francisco city, which was rebuilt from an aerial photo supplied by the user; no license for that photo is recorded, so this piece shares the unresolved rights question of `san-francisco` (see its migration notes). This note asserts no redistribution right for the photo.

## To promote

- Audit; add real knobs; check the NES background tiles on the background alone (`pixelate era BG.png --era nes --tiles`) so the whole-frame tile failure is resolved or explained.
