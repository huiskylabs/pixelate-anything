"""Fallen petals (spring) and fallen leaves (fall) scattered by hand on the grass."""
from artlib import Grid

# (x, y, slot) in canvas coordinates; placed under and downwind of the cherry
PETALS = [(132, 176, 'L3'), (137, 175, 'L4'), (141, 177, 'L3'), (146, 174, 'L3'), (150, 176, 'L4'),
          (155, 173, 'L3'), (158, 175, 'L3'), (163, 177, 'L4'), (168, 174, 'L3'), (172, 176, 'L3'),
          (176, 173, 'L4'), (181, 175, 'L3'), (185, 178, 'L3'), (190, 176, 'L4'), (196, 179, 'L3'),
          (203, 177, 'L3'), (210, 179, 'L4'), (218, 180, 'L3'), (226, 181, 'L3'), (235, 179, 'L4'),
          (144, 179, 'L2'), (160, 179, 'L2'), (178, 179, 'L2'), (139, 173, 'L4'), (152, 172, 'L3')]
LEAVES = [(130, 177, 'L2'), (131, 177, 'L3'), (138, 175, 'L1'), (143, 176, 'L2'), (144, 176, 'L2'),
          (149, 174, 'L3'), (154, 176, 'L2'), (157, 173, 'L1'), (158, 173, 'L2'), (163, 176, 'L3'),
          (167, 174, 'L2'), (171, 177, 'L1'), (172, 177, 'L2'), (177, 175, 'L3'), (183, 177, 'L2'),
          (188, 179, 'L2'), (189, 179, 'L3'), (195, 177, 'L1'), (204, 180, 'L2'), (214, 181, 'L3'),
          (215, 181, 'L2'), (232, 180, 'L2'), (246, 182, 'L1'), (262, 181, 'L2'), (263, 181, 'L3'),
          (280, 180, 'L2'), (300, 182, 'L1'), (318, 184, 'L2'), (319, 184, 'L3'), (338, 190, 'L2'),
          (117, 186, 'L3'), (122, 184, 'L2'), (126, 182, 'L2')]

def overlay(points):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    x0, y0 = min(xs), min(ys)
    g = Grid(max(xs) - x0 + 1, max(ys) - y0 + 1)
    for (x, y, v) in points:
        g.set(x - x0, y - y0, v)
    return g, x0, y0

def export():
    pg, px0, py0 = overlay(PETALS)
    lg, lx0, ly0 = overlay(LEAVES)
    return [('sprite', 'petals_ground', [pg], 0, 0), ('const', 'PETALS_GROUND_POS', '[%d, %d]' % (px0, py0)),
            ('sprite', 'leaves_ground', [lg], 0, 0), ('const', 'LEAVES_GROUND_POS', '[%d, %d]' % (lx0, ly0))]
