"""An upright pinhole camera for two-point perspective, set from the guides a photo gives you.

A rebuild records the photo's horizon row and its two vanishing points (`pixelate reference
PHOTO --marks` keeps them as camera.horizon_y and camera.vanishing_points). For an upright camera
(level eye, image plane vertical) looking across a corner of two perpendicular world axes, those
three numbers and the principal point fix the camera:

    focal f    = sqrt((vp_right - cx) * (cx - vp_left))     (cx must lie between the points)
    yaw        = atan((cx - vp_left) / f)                   (between the view and the +Y axis)

World axes: +X recedes to the right vanishing point, +Y to the left one, +Z is up. Verticals stay
vertical and every horizontal line along X or Y meets its own finite point on the horizon. This
is a projection of world points, not a renderer: callers project corners and fill the polygons.
"""
import math


class TwoPointCamera:
    def __init__(self, horizon, vp_left, vp_right, cx, eye):
        if not vp_left < cx < vp_right:
            raise ValueError('the principal point x must lie between the two vanishing points')
        self.horizon, self.cx = float(horizon), float(cx)
        self.f = math.sqrt((vp_right - cx) * (cx - vp_left))
        self.yaw = math.atan2(cx - vp_left, self.f)
        s, c = math.sin(self.yaw), math.cos(self.yaw)
        self.right = (c, -s)              # the image's x axis on the ground plane
        self.forward = (s, c)             # the view direction on the ground plane
        self.eye = tuple(float(v) for v in eye)

    def depth(self, p):
        return (p[0] - self.eye[0]) * self.forward[0] + (p[1] - self.eye[1]) * self.forward[1]

    def project(self, p):
        """world point (x, y, z) -> screen point (sx, sy) in native pixels, unrounded"""
        dx, dy, dz = p[0] - self.eye[0], p[1] - self.eye[1], p[2] - self.eye[2]
        zc = dx * self.forward[0] + dy * self.forward[1]
        if zc <= 1e-6:
            raise ValueError(f'point {p!r} is behind the camera')
        xc = dx * self.right[0] + dy * self.right[1]
        return self.cx + self.f * xc / zc, self.horizon - self.f * dz / zc

    def vanishing_point(self, direction):
        """the screen point where world lines along a horizontal direction (dx, dy) meet"""
        zc = direction[0] * self.forward[0] + direction[1] * self.forward[1]
        if abs(zc) < 1e-9:
            raise ValueError('a direction parallel to the image plane has no finite vanishing point')
        xc = direction[0] * self.right[0] + direction[1] * self.right[1]
        return self.cx + self.f * xc / zc, self.horizon

    def guides(self):
        """the camera as reference-style guides: horizon row, the two vanishing points, focal, yaw"""
        return {'horizon_y': self.horizon, 'vanishing_points': [list(self.vanishing_point((0, 1))),
                                                               list(self.vanishing_point((1, 0)))],
                'principal_x': self.cx, 'focal_px': self.f, 'yaw_deg': math.degrees(self.yaw),
                'eye': list(self.eye)}
