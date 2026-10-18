# Starter: Scene Loop: migration notes (phase 1)

Moved with `git mv` from `templates/starter` into `library/starter-scene-loop` on 2026-10-18. These are migration facts, not a review: nobody has approved this piece in this migration, and a passing check is not approval.

## Request and authorship

The original request is not recorded anywhere in the repository, so `request` says so and quotes the source description instead of inventing a request. Template from the first kit commits; no request exists.
Authorship is taken from git history only (the `by` field); it does not attest review.

## Status

`starter`. §6.2 starts this template as `starter`, which requires that it renders and passes the gate. The first version of this migration kept it at `study` because the `dusk` phase, the first picture a user sees (t=0), failed the `lofi` budget `L>=0.7` (12.5% of pixels against a 4% limit, measured at t=0, 5, 10, 15 and 20 s, 8x), caused by the horizon band `S4`. The fix is one palette value, not a gate override: `S4` in the dusk palette went from `#ec8a5c` (OKLab L 0.729) to `#e0794f` (L 0.684), a slightly deeper orange. Nothing else in the drawing code changed. `dusk` is now a declared output with its own golden, and `media/` shows it.

What that means: the default image passes the *technical* `lofi` frame gate and `pixelate check .` passes. It is still a populated sample (a cabin, a pine, rain), not a blank scene, and it has had no art review; passing says nothing about quality. The shared `palettes/hilltop-dusk.hex` still lists the old `ec8a5c`; it is outside this piece and was not edited.

## Checked at migration (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, Node v22.23.2, ffmpeg 6.1.1, Linux x86_64)

The `rain` golden is byte-identical to the one before the change. Each output command was run from clean copies of the tree (no `.git`; generated `out/` files removed, goldens kept), with `PIXELATE_KIT` set to the copy:

- `dusk`: `python3 "$PIXELATE_KIT/pixelate" shot . 0 --zoom 8 --out out` writes `out/t0000.00.png` (1920x1080, scale 8); the golden `out/golden/dusk.png` is its NEAREST 1x downsample (240x135); `pixelate check out/t0000.00.png --scale 8 --style lofi`: gate PASS (0.19% of pixels at L>=0.7). Re-measured after the change (kit 1.0.0, same toolchain): frames at t = 0, 4, 8 .. 116 s all pass the `lofi` gate, 5 of those 30 with one heuristic WARN (`repeat`, 1 row of near-identical units).
- `rain`: `python3 "$PIXELATE_KIT/pixelate" shot . 30 --zoom 8 --out out` writes `out/t0030.00.png` (1920x1080, scale 8); identical across both runs: True; `pixelate check out/t0030.00.png --scale 8 --style lofi`: gate PASS. Golden `out/golden/rain.png` is the NEAREST 1x downsample (240x135).

Also run: `pixelate check .` (ALL OK: sprites, timing, determinism, loop seam).

Not checked: `pixelate judge`, `pixelate critique`, and any human or art-director review. Also not checked: the page build (`pixelate check . --page`) and, unless listed above, the rendered soundtrack.

## Licensing and provenance

No reference photos or borrowed assets are used. The code is first-party and falls under the repository MIT license (docs/PLAN-library.md D1).

## To promote

- Decide whether a starter should be an empty scene (sky and hill) rather than this populated cabin; the plan says "an empty piece for one mode" and the existing scene still draws a cabin, a pine and a rain.
- The 120 s soundtrack was not rendered or committed.
