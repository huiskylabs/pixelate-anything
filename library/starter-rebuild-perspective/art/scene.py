#!/usr/bin/env python3
"""Starter Rebuild Perspective: a neutral two-point perspective scaffold rendered as one still.

    python3 art/scene.py      writes out/corner.png (4x), out/palette.json and out/camera.json
                              (the horizon, both vanishing points, focal length, yaw and eye)

The camera is set from a horizon row and two finite vanishing points, as a photo gives them
(camera.py), and every edge is a projected world line: the faces along world X run to the right
point, the faces along world Y to the left one, and verticals stay vertical. Everything drawn is a
placeholder: a sky, a ground plane with paving joints, and two grey blocks with panel grids seen
across their corners. To rebuild a reference, copy its horizon and vanishing points into the
constants below, then replace BLOCKS and the joints with its own forms.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# canvas is a kit module: piece commands run with the kit's tools/ first on PYTHONPATH
import canvas  # noqa: E402  # pyright: ignore[reportMissingImports]
import massing  # noqa: E402  # pyright: ignore[reportMissingImports]
from camera import TwoPointCamera  # noqa: E402  # pyright: ignore[reportMissingImports]
from pal import PALETTE  # noqa: E402  # pyright: ignore[reportMissingImports]

W, H, SCALE = 320, 180, 4
HORIZON = 104                                 # eye-level row
VP_LEFT, VP_RIGHT = -70, 470                  # vanishing points on the horizon (x), outside the frame
CX = W / 2                                    # principal point: the frame centre
EYE = (-20.0, -27.0, 1.6)                     # world position of the eye (x, y, height), units
BLOCKS = [(0, 0, 14, 10, 12),                 # placeholder massing: x0, y0, x1, y1, height
          (17, 3, 27, 13, 18)]
JOINTS = (4, 4)                               # paving joint spacing along x and y, units
JOINT_RANGE = (-24, 30)                       # paving runs over this world x and y span
NEAR, FAR = 3.0, 24.0                         # joints are drawn between these depths
OUT = HERE.parent / 'out'


def camera():
    return TwoPointCamera(HORIZON, VP_LEFT, VP_RIGHT, CX, EYE)


def segment(cam, a, b):
    """the part of the ground line a-b between depths NEAR and FAR, projected, or None"""
    da, db = cam.depth(a), cam.depth(b)
    lo, hi = sorted(((NEAR - da) / (db - da), (FAR - da) / (db - da))) if db != da else (0.0, 1.0)
    lo, hi = max(0.0, lo), min(1.0, hi)
    if lo >= hi:
        return None
    at = [tuple(a[i] + (b[i] - a[i]) * t for i in range(3)) for t in (lo, hi)]
    return [cam.project(p) for p in at]


def compose():
    cam = camera()
    c = canvas.Canvas(W, H)
    c.bands(0, HORIZON, [('S0', 0), ('S1', 44, 14), ('S2', 84, 14)])
    c.bands(HORIZON, H, [('G0', HORIZON), ('G1', 126, 12), ('G2', 156, 12)])
    lo, hi = JOINT_RANGE
    lines = [((lo, y, 0), (hi, y, 0)) for y in range(lo, hi + 1, JOINTS[1])]
    lines += [((x, lo, 0), (x, hi, 0)) for x in range(lo, hi + 1, JOINTS[0])]
    for a, b in lines:
        seg = segment(cam, a, b)
        if seg:
            (ax, ay), (bx, by) = seg
            c.line(round(ax), round(ay), round(bx), round(by), 'J0')
    far_first = sorted(BLOCKS, key=lambda b: -cam.depth(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, 0)))
    for block, ramp in zip(far_first, ('B', 'A'), strict=True):
        massing.draw(c, cam, block, ramp)
    return c, cam


def main():
    c, cam = compose()
    OUT.mkdir(exist_ok=True)
    c.image(PALETTE).resize((W * SCALE, H * SCALE), 0).save(OUT / 'corner.png')
    (OUT / 'palette.json').write_text(json.dumps(PALETTE, indent=1, sort_keys=True) + '\n')
    (OUT / 'camera.json').write_text(json.dumps(cam.guides(), indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
