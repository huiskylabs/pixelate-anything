# Starter: Scene Still: notes (phase 2)

New on 2026-10-18 as one of the three starters planned in docs/PLAN-library.md section 6.2. These are build facts, not a review: nobody has reviewed or approved this piece, and a passing check is not approval.

## What it draws

A three-band sky with 14-row Bayer transitions, two flat blocks in it, flat ground with an edge line and a dithered step, a dark foreground strip with a lit edge, and one grey placeholder box with a marker centre. No authored subject. `tests/test_library_starters.py` fails if subject words come back or another slot map is added.

It is not a literally blank frame. The stock composition check `empty_low` allows at most 88% of the bottom third's cells to be empty; the foreground strip and the box bring it to 81%. See `library/starter-scene-loop/history/migration.md` for the same constraint on the loop starter.

No Hero line: a placeholder would fail the focus checks (it is not meant to hold the frame), so the brief says to add one with the subject.

## Checked (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, SciPy 1.17.1, Linux x86_64)

- `python3 art/scene.py` in a lone clean copy writes `out/still.png` (1280x720, scale 4) and `out/palette.json`; two runs give identical bytes. The golden `out/golden/still.png` is its NEAREST 1x downsample (320x180), and every 4x4 cell is flat, so the golden reproduces the frame exactly.
- `pixelate check out/still.png --style lofi --scale 4 --pal out/palette.json --brief brief.md`: ALL PASS (L>=0.7 0.00%, median C 0.050, palette 0 px off, bottom third 81% empty, no repeat warning; focus skipped, no hero).
- `pixelate library test starter-scene-still --quick`: ok, gate_ok, golden 0 px different.

Not checked: `pixelate judge`, `pixelate critique`, any human or art-director review.

## Licensing and provenance

No references or borrowed assets. First-party code under the repository MIT license. Media (`media/thumb.png`, `media/contact.png`) are made from the golden.
