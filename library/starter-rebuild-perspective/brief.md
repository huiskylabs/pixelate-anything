# Starter: Rebuild Perspective

A neutral scaffold for rebuilding a photo or a place seen in two-point perspective, such as a
street corner. It draws no subject of its own: set the camera from the reference, replace the
placeholder blocks with its forms, then rewrite this brief for it (guides/rebuild.md).

## Intent

- What it is now: a level view across the corners of two plain grey blocks with placeholder panel
  grids, standing on a ground plane with paving joints, under a plain sky.
- What to make of it: a rebuild whose reference has two vanishing points. Keep the reference's
  camera instead of substituting an isometric view.

## Camera

- Upright pinhole camera (`art/camera.py`): horizon at row 104 of 180, vanishing points at
  x -70 and x 470 on the horizon (both outside the frame), principal point at the frame centre,
  eye 1.6 units above the ground. Focal length and yaw follow from those numbers.
- Faces along world X recede to the right point, faces along world Y to the left one, verticals
  stay vertical; panels and joints are laid out in world units, so they shrink with depth.
- From a photo: mark its horizon and vanishing points (`pixelate reference PHOTO --marks`), copy
  them into `art/scene.py`, and keep the principal point between the two points.

## Composition

- The near block's corner stands left of centre; a taller block sits behind it on the right.
- No hero is declared: a neutral placeholder is not meant to hold the frame's focus. Once a
  subject exists, add its Hero line (box, peak value, peak chroma) so the gate's focus checks run.

## Technical

- 320x180 at 1x, delivered at 4x (1280x720) as `out/corner.png`; style `lofi`.
- `out/camera.json` records the horizon, both vanishing points, focal length, yaw and eye.
- Gate: `pixelate check out/corner.png --style lofi --scale 4 --pal out/palette.json --brief brief.md`.
- Gate override: none
