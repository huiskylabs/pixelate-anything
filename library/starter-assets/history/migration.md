# Starter: Assets: migration notes (phase 1)

Moved with `git mv` from `templates/assets` into `library/starter-assets` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description ("My Pack") instead of inventing a request. Template from the initial kit commit; no request exists.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`starter`. docs/PLAN-library.md section 2.1 defines a starter as "an empty piece for one mode". The inherited template shipped a finished animated coin and a heart, so a follow-up replaced that subject with neutral placeholders instead of only relabelling it.

What the piece holds now, and what it does not:

- It holds: a palette of outline, white and two four-step ramps (`base0-3` grey, `mark0-3` blue), and two named 8 px placeholder slots in `sprites/slots.px`: `slot_a` (4 frames at 4 fps, tag `cycle`, a single marker pixel moving round the centre of a grey box) and `slot_b` (one frame, the same box in blue).
- It does not hold any finished subject: no coin, heart, gold, red or leaf colour, spin animation, or named item. `tests/test_library_migration.py` (`StarterAssetsTest`) fails if such words come back in the pack files, if the sprite file or slot names change, if the palette slots change or if `out/atlas.json` stops matching the two slots.
- It is not literally empty: an exported pack with no sprites has nothing to show or to check, and the exports would be empty files. Read "empty" as "no authored subject, placeholders only".

## What was kept and what changed

Kept: the `.px` format and every header the guide documents (`anchor`, `fps`, `tags`, `key`, frames), `pack.json` keys (`palette`, `scale`, `preview_bg`, `maps`), the `pixelate assets` command and the same three declared exports (`out/atlas.png`, `out/atlas.json`, `out/contact.png`). More sprite files, `art/*.py` generators and maps can be added as before.

Changed: `sprites/items.px` is now `sprites/slots.px`; `palette.json` has neutral slots (the gold, red and leaf ramps are gone); the pack name in `pack.json` is "Placeholder Pack"; `piece.json` summary, subject tags and anatomy; the three exports and `media/` are regenerated from the new sprites. `guides/assets.md` pointed at the coin in `sprites/items.px`; that sentence was updated.

## Checked (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

- Deterministic pack generation: `python3 "$PIXELATE_KIT/pixelate" assets .` exits 0 and reports `slot_a` (8x8, 4 frames, 6 colours) and `slot_b` (8x8, 1 frame, 5 colours) with no unknown keys or ragged rows (the report also lists 16 and 3 "lone" pixels per slot, which it calls informational). `CleanCopyRenderTest` and `IsolatedCopyTest` run it from clean copies (one inside a kit copy with `library/`, one in a folder with no `library/` next to it) with `out/` files removed first and require `out/atlas.png`, `out/atlas.json` and `out/contact.png` to be byte-identical to the committed files.
- Declaration: the manifest validates through `tools/library.py` (`library.validate`); `out/` files exist and are tracked.
- Mode-appropriate validation: the `pixelate assets` report above. `pixelate check .` needs a `scene.json` and does not apply to a pack.
- The frame gate does not apply: `pixelate check FRAME --style lofi` is built for composed pictures with scene colour budgets. It was tried on the atlas strip (`--scale 1 --style lofi`) and fails three budgets (`L<0.1`, `black`, `median_C`) because transparent pixels read as black; on the contact sheet it fails `L>=0.7`, `stripes` and `small_clusters`. A sprite sheet is not a delivered frame, so no gate pass is claimed and none is declared in `outputs`.

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review. No claim about art quality is made.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Decide whether an asset starter needs a gate of its own (for example a silhouette or palette check on the atlas); the stock frame gate cannot judge a sprite sheet.
