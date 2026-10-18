# Starter: Scene Still

A neutral scaffold for one still image. It draws no subject of its own: replace every placeholder
with the scene the request asks for, then rewrite this brief for it.

## Intent

- What it is now: a level side view of a plain sky over flat ground, with one grey placeholder box
  standing on the ground, two flat blocks in the sky and a dark foreground strip.
- What to make of it: any still scene with no photo to rebuild. Keep the camera or change it in
  `art/scene.py`.

## Composition

- Horizon at row 112 of 180; the ground runs to the foreground strip at row 153.
- The placeholder box stands centred on the ground; put the subject where the box is, or move
  `MARKER_AT`.
- No hero is declared: a neutral placeholder is not meant to hold the frame's focus. Once a
  subject exists, add its Hero line (box, peak value, peak chroma) so the gate's focus checks run.

## Palette

- One strict palette in `art/pal.py`: sky, ground, foreground, outline, placeholder box, flat
  blocks and the marker. The sky stays under L 0.7 for the lofi budget.

## Technical

- 320x180 at 1x, delivered at 4x (1280x720) as `out/still.png`; style `lofi`.
- Gate: `pixelate check out/still.png --style lofi --scale 4 --pal out/palette.json --brief brief.md`.
- Gate override: none
