# Starter: Rebuild Perspective: notes (phase 2)

New on 2026-10-18 as one of the three starters planned in docs/PLAN-library.md section 6.2. These are build facts, not a review: nobody has reviewed or approved this piece, and a passing check is not approval.

## What it draws

Two plain grey blocks with placeholder panel grids, seen across their corners; a ground plane with paving joints; a plain sky. No authored subject and no reference photo.

## The camera

`art/camera.py` is an upright pinhole camera. It is set from the horizon row (104), two finite vanishing points on it (x -70 and x 470) and the principal point (the frame centre, x 160): focal length sqrt((470 - 160) * (160 + 70)) = 267.0 px and yaw 40.7 degrees follow. Every drawn edge is a projected world line, so faces along world X meet the right point, faces along world Y the left one, verticals stay vertical, and equal world steps shrink with depth. It does not use `tools/iso.py`, whose presets are orthographic. `out/camera.json` records the guides in the same terms as `pixelate reference` (`horizon_y`, `vanishing_points`).

Joints are drawn only between depths 3 and 24 units, so the ground does not turn to noise near the horizon.

## Checked (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, SciPy 1.17.1, Linux x86_64)

- `python3 art/scene.py` in a lone clean copy writes `out/corner.png` (1280x720, scale 4), `out/palette.json` and `out/camera.json`; two runs give identical bytes. The golden `out/golden/corner.png` is the NEAREST 1x downsample (320x180) and reproduces the frame exactly.
- `pixelate check out/corner.png --style lofi --scale 4 --pal out/palette.json --brief brief.md`: ALL PASS (L>=0.7 0.00%, median C 0.041, jaggies 5%, bottom third 46% empty, no repeat warning; focus skipped, no hero).
- `tests/test_library_starters.py` (`TwoPointCameraTest`): both points finite, distinct and on the horizon; the top and bottom edges of every face and panel pass through their own axis's point; verticals vertical; foreshortening along each face; the rendered corner sits where the projection puts it.
- `pixelate library test starter-rebuild-perspective --quick`: ok, gate_ok, golden 0 px different.

Not checked: `pixelate judge`, `pixelate critique`, any human or art-director review, and a rebuild from a real photo.

## Licensing and provenance

No references or borrowed assets. First-party code under the repository MIT license. Media (`media/thumb.png`, `media/contact.png`) are made from the golden.
