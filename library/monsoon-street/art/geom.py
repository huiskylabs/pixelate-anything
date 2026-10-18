"""Monsoon Street: the photo's camera on the native 480x270 grid (one-point perspective).

Recorded from the reference (Pexels 18867525) at native size: horizon row 168, vanishing point
(276, 168), camera 1.5 m up, focal 400 px. Everything is placed in metres and projected here, then
snapped to whole pixels: X is across the street (negative left), Z is depth from the camera, Y is
height above the road.
"""
import math

W, H = 480, 270
HZ, VPX = 168, 276          # horizon row, vanishing point column
F, CAM_H = 400.0, 1.5       # focal length in px, camera height in m


def row(Z):
    """screen row of the ground at depth Z"""
    return HZ + F * CAM_H / Z


def col(X, Z):
    return VPX + F * X / Z


def yh(Yw, Z):
    """screen row of a point Yw metres up at depth Z"""
    return HZ + F * (CAM_H - Yw) / Z


def depth_of_row(y):
    return F * CAM_H / max(1e-6, (y - HZ))


def depth_on_wall(x, X):
    """depth of the column x on a receding wall at X"""
    return F * X / (x - VPX)


def P(X, Yw, Z):
    return (col(X, Z), yh(Yw, Z))


# ---------------------------------------------------------------- the street plan (metres)
X_L = -4.2          # left street wall (far part)
X_R = 3.3           # right street wall (far part and the hero's side face)
X_CURB_L = -3.0     # left curb (far part)
X_CURB_R = 2.1      # right curb
Z_FAR = 33.0        # near curb of the far cross street
Z_TRAM = 35.5       # tram centre line
Z_FARWALL = 41.0    # the far building across the cross street
Z_LC = 15.4         # face of the left corner block (faces the camera)
X_LC0 = -8.5        # left end of the corner block face
Z_LCURB = 11.1      # curb of the side street in front of the corner block
Z_HERO = 13.6       # hero shop front face (faces the camera)
Z_HERO_BACK = 17.6  # back end of the hero's side face
X_HERO1 = 6.3       # right end of the hero front face (the glass building starts here)

# screen anchors derived from the plan (for the block-in and the brief)
HERO_BASE = row(Z_HERO)                    # 212
LC_BASE = row(Z_LC)                        # 207
FAR_ROW = row(Z_FAR)                       # 186
FARWALL_ROW = row(Z_FARWALL)               # 182.6
X_OPEN0 = col(X_L, Z_FAR)                  # 225
X_OPEN1 = col(X_R, Z_FAR)                  # 316
X_HERO_SIDE0 = col(X_R, Z_HERO_BACK)       # 351
X_HERO_C = col(X_R, Z_HERO)                # 373
X_HERO_R = col(X_HERO1, Z_HERO)            # 461
X_LC0_S = col(X_LC0, Z_LC)                 # 55
X_LC1_S = col(X_L, Z_LC)                   # 167

HERO_BOX = (344, 120, 462, 210)
PUDDLE = (246, 234, 392, 262)

if __name__ == '__main__':
    for k in ('HERO_BASE', 'LC_BASE', 'FAR_ROW', 'FARWALL_ROW', 'X_OPEN0', 'X_OPEN1', 'X_HERO_SIDE0',
              'X_HERO_C', 'X_HERO_R', 'X_LC0_S', 'X_LC1_S'):
        print(k, round(globals()[k], 1))
