"""The layout both stills share: the gondola's screen box, the cable, the cleft, the clock, the cloud sea."""
import numpy as np
from common import W, H, hsh, noise1

CABLE_X = 134                       # the cable's 2 px column at the gondola (x 134-135)
GONDOLA_BLOCK = (116, 200, 162, 266)  # gondola + passenger + lantern, inclusive
HERO = (114, 200, 164, 268)
CLOCK = (58, 238, 28)               # centre and rosette radius; the dial is radius 22


def cleft_edges():
    """x of the left wall's edge and the right wall's edge per row: wider at the top, jogged runs"""
    xl = np.zeros(H, int); xr = np.zeros(H, int)
    y, k = 0, 0
    jl = jr = 0
    while y < H:
        run = 10 + int(hsh(k, 11) * 22)
        jl = int(round((hsh(k, 12) - 0.5) * 7))
        jr = int(round((hsh(k, 13) - 0.5) * 8))
        for yy in range(y, min(H, y + run)):
            u = yy / H
            base_l = 86 + 14 * u + 16 * max(0, u - 0.8) / 0.2 * max(0, u - 0.8) / 0.2 + 2.5 * noise1(yy / 37, 5)
            base_r = 192 - 22 * u - 14 * max(0, u - 0.8) / 0.2 * max(0, u - 0.8) / 0.2 + 2.5 * noise1(yy / 41, 6)
            xl[yy] = int(round(base_l + jl))
            xr[yy] = int(round(base_r + jr))
        y += run; k += 1
    return xl, xr


# carved house fronts cut into the bark (x0, y0, x1, y1): big, medium and small, never equal
FRONTS_A = [
    (20, 34, 74, 80),      # L1 medium: two windows and a door, balcony with the laundry line
    (36, 116, 72, 162),    # L2 small: the arched door with its balcony
    (6, 360, 82, 430),     # L3 big: the lower left house, round window with a flower box
    (198, 58, 254, 104),   # R1 medium
    (214, 124, 248, 154),  # R2 small
    (200, 272, 248, 300),  # R3 small: the watcher's window
    (190, 346, 264, 410),  # R4 big: uneven windows, laundry between balconies
    (196, 438, 240, 476),  # R5 small landing front, the sweeper
]

# aurora curtains in B: rows (y, x0, x1, thickness) of the block-in
AURORA_BLOCK = [(40 + i * 3, 20 + i * 2, 250 - i, 3) for i in range(0)]


def aurora_block_rows():
    rows = []
    for x in range(14, 252):
        u = (x - 14) / 238
        y = int(58 + 60 * u - 38 * u * u + 6 * np.sin(x / 19))
        rows.append((y, x, x + 1, 26 + int(10 * np.sin(x / 31) + 8)))
    for x in range(150, 262):
        u = (x - 150) / 112
        y = int(150 + 30 * u + 5 * np.sin(x / 13))
        rows.append((y, x, x + 1, 18 + int(6 * np.sin(x / 23))))
    return rows


AURORA_BLOCK = aurora_block_rows()


def cloud_top_line():
    """the block-in's cloud-sea top per column: three masses, the near huge one lowest"""
    top = np.full(W, H, int)
    for x in range(W):
        a = 318 + 3 * noise1(x / 23, 3) if x < 168 else H     # near huge mass, x 0-168
        b = 300 + 3 * noise1(x / 17, 4) if 150 <= x < 262 else H   # mid mass, x 150-262
        c = 286 + 2 * noise1(x / 11, 5) if 230 <= x < 268 else H   # far small mass
        top[x] = int(min(a, b, c, H))
    return top
