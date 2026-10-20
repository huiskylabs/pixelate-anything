"""Placeholder massing: axis-aligned blocks drawn through the two-point camera.

A block is (x0, y0, x1, y1, height) in world units. Each face the eye can see is projected corner
by corner, so its top and bottom edges run to the vanishing point of its own axis; a grid of
placeholder panels is laid out on the face in world units, so the panels shrink with depth.
Replace the blocks and panels with the reference's own forms; keep drawing through the camera.
"""


def faces(cam, block):
    """[(axis, world quad)] of the vertical faces turned toward the eye; axis 'x' recedes to the
    right vanishing point, 'y' to the left one. Quads run bottom-near, bottom-far, top-far, top-near."""
    x0, y0, x1, y1, h = block
    ex, ey = cam.eye[0], cam.eye[1]
    out = []
    for y in ((y0,) if ey < y0 else (y1,) if ey > y1 else ()):
        out.append(('x', [(x0, y, 0), (x1, y, 0), (x1, y, h), (x0, y, h)]))
    for x in ((x0,) if ex < x0 else (x1,) if ex > x1 else ()):
        out.append(('y', [(x, y0, 0), (x, y1, 0), (x, y1, h), (x, y0, h)]))
    return out


def panels(quad, pitch=2.5, width=1.2, first=2.0, row=3.0, tall=1.4, margin=1.0):
    """world quads of a panel grid on a face quad: columns every `pitch` units along the face, rows
    every `row` units up from `first`, each `width` by `tall`, kept `margin` from the face's ends"""
    (ax, ay, _), (bx, by, _), h = quad[0], quad[1], quad[3][2]
    length = abs(bx - ax) + abs(by - ay)          # faces run along one axis

    def at(u, z):
        return ax + (bx - ax) * u / length, ay + (by - ay) * u / length, z

    out = []
    z = first
    while z + tall <= h - margin:
        u = margin
        while u + width <= length - margin:
            out.append([at(u, z), at(u + width, z), at(u + width, z + tall), at(u, z + tall)])
            u += pitch
        z += row
    return out


def draw(c, cam, block, ramp):
    """draw one block: lit 'y' faces in ramp0, shaded 'x' faces in ramp1, their panels in ramp2 and
    ramp3, and a contact line where the faces meet the ground. Returns the screen quads drawn."""
    drawn = []
    for axis, quad in faces(cam, block):
        lit = axis == 'y'
        screen = [cam.project(p) for p in quad]
        c.poly(screen, ramp + ('0' if lit else '1'))
        for panel in panels(quad):
            c.poly([cam.project(p) for p in panel], ramp + ('2' if lit else '3'))
        (ax, ay), (bx, by) = screen[0], screen[1]
        c.line(round(ax), round(ay) - 1, round(bx), round(by) - 1, 'K0')
        drawn.append((axis, screen))
    return drawn
