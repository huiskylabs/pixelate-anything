"""Market Day layout: Strasbourg's Rue Merciere from the cathedral tower, laid out in 2:1 iso
world units. x runs along the street toward the cathedral square (screen down-right), y across
it toward the viewer (screen down-left), z up (1 px per unit).

  the street        x 0..140, y 0..42 (paving, stalls on the far side, the crowd)
  Place Gutenberg   x -62..0, y -86..42 (the square; the hall closes its west side)
  the hall          x -94..-62, y -76..28: the long arcaded block, huge hipped roof, 3 dormer rows
  cathedral square  x > 140 (lower-right corner: cafe terraces on the end houses' +x fronts)
  far-side row      y -22..0 (facades face the street: half-timbered, pastel plaster)
  near-side rows    y 42..62, 66..90, 94..118, 122..146 (their +y roof slopes face the viewer)

Buildings are specs (dicts) so the block-in and the final render share one layout."""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
from iso import hash2

W = H = 600
ORIGIN = (284, 291)

STREET = (0, 0, 124, 48)            # x0, y0, x1, y1
SQUARE = (-60, -86, 0, 48)
CATH = (124, -120, 260, 260)
HALL = dict(X=-92, Y=-76, w=32, d=104, h=42, roof=48, hip=18, plinth=6)
STEPS = dict(x0=-60, y0=-37, y1=5, landing=5, n=2, tread=3, rise=2)   # in front of the hall
ALLEY_N = (52, 59)                  # a mouth off the far side (x range), runs north
ALLEY_S = (84, 91)                  # a mouth off the near side, runs south
LANE_SW = (18, 24)                  # a lane through the near-side roof carpet (lower left)

WALLS = ['cream', 'plaster', 'pink', 'ochre', 'plaster', 'mint', 'cream', 'sky', 'plaster', 'pink']
ROOFS = ['slate', 'brown', 'terra', 'slate', 'tile', 'brown', 'slate', 'terra', 'tile']

def _r(k, a, b, s=0):
    return a + (b - a) * hash2(k, 17, s)

def row(x0, x1, y0, d, side, seed, kinds=None, hmin=22, hmax=38, skip=()):
    """a row of houses along x from x0 to x1, lots y0..y0+d. side 'far': its +y facade fronts
    the street; 'near': its +y face is the back. Widths, heights, roofs and walls vary by hash,
    never two neighbours alike."""
    out = []
    x = x0
    k = seed * 101
    prev = (None, None, None)
    while x < x1 - 4:
        w = int(_r(k, 9, 19, 1))
        if x + w > x1 - 5:
            w = x1 - x
        if any(a <= x + w / 2 <= b for a, b in skip):
            x += w; k += 1
            continue
        h = int(_r(k, hmin, hmax, 2)) // 2 * 2
        if prev[0] is not None and abs(h - prev[0]) < 4:
            h = h + 6 if h + 6 <= hmax + 4 else h - 6
        wall = WALLS[int(hash2(k, 5, seed) * len(WALLS))]
        if wall == prev[1]:
            wall = WALLS[(WALLS.index(wall) + 3) % len(WALLS)]
        roof = ROOFS[int(hash2(k, 7, seed) * len(ROOFS))]
        if roof == prev[2]:
            roof = ROOFS[(ROOFS.index(roof) + 2) % len(ROOFS)]
        gable = side == 'far' and w <= 14 and hash2(k, 9, seed) < 0.45
        hip = 0 if gable else (int(_r(k, 3, 7, 4)) if hash2(k, 11, seed) < 0.35 else 0)
        timber = hash2(k, 13, seed) < 0.55
        dd = d - (int(hash2(k, 15, seed) * 3) if side == 'near' else 0)
        out.append(dict(X=x, Y=y0 + (d - dd if side == 'far' else 0), w=w - 0.5, d=dd, h=h, wall=wall, roof=roof,
                        gable=gable, hip=hip, timber=timber, side=side, seed=k))
        prev = (h, wall, roof)
        x += w; k += 1
    return out

def buildings():
    B = []
    # the street's two sides
    B += row(0, ALLEY_N[0], -22, 22, 'far', 1, hmin=26, hmax=40)
    B += row(ALLEY_N[1], 124, -22, 22, 'far', 2, hmin=26, hmax=40)
    B += row(0, ALLEY_S[0], 48, 18, 'near', 3, hmin=18, hmax=26)
    B += row(ALLEY_S[1], 124, 48, 18, 'near', 4, hmin=18, hmax=26)
    # rows behind the near side (lower left), their ends fronting the cathedral square raggedly
    for i, y0 in enumerate((70, 94, 118, 142, 166, 190, 214)):
        xe = 124 - (0, 3, 1, 5, 2, 6, 3)[i]
        lanes = ([ALLEY_S] if i < 2 else []) + ([LANE_SW] if i >= 1 else [])
        B += row(-150, xe, y0, 20, 'near', 10 + i, hmin=20, hmax=32, skip=lanes)
    B += row(-150, -4, 50, 18, 'near', 20, hmin=20, hmax=30)          # the square's south side
    # behind the far side and east and north of the square, to the top-right corner
    for i, y0 in enumerate((-50, -78, -106, -134, -162, -190, -218, -246)):
        B += row(2 if i < 3 else -94, 170, y0, 24, 'far', 30 + i, hmin=26, hmax=42, skip=[ALLEY_N] if i == 0 else ())
    B += row(-94, -2, -110, 24, 'far', 40, hmin=34, hmax=46)           # the square's north side
    # west of the hall, to the left and top edges
    for i, x0 in enumerate((-130, -168, -206, -244)):
        for j, y0 in enumerate((-192, -164, -136, -108, -80, -50, -20, 10)):
            B += row(x0, x0 + 34, y0, 26, 'near', 50 + 9 * i + j, hmin=24, hmax=38)
    return B
