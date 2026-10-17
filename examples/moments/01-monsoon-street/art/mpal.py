"""Monsoon Street palette: one strict albedo palette shared by every phase (the light map changes,
the slots do not). Written in OKLCH so the value and chroma budgets are designed, not hoped for.
Every material's darkest step leans into the shared plum; lights turn warm."""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
import colorlib as cl


def lch(L, C, h):
    C = cl.clamp_chroma(L, C, h)
    return cl.rgb_to_hex(cl.oklab_to_rgb(cl.oklch(L, C, h)))


SPEC = {
    # shared darks
    'void': (0.075, 0.016, 290), 'plum': (0.17, 0.035, 330),
    # night sky (only in the strip over the far roofline)
    'sky0': (0.21, 0.045, 268), 'sky1': (0.26, 0.045, 262), 'sky2': (0.31, 0.040, 255),
    # cool slate: far building, metal, poles, mullions
    'cool0': (0.20, 0.025, 278), 'cool1': (0.27, 0.025, 266), 'cool2': (0.35, 0.024, 255),
    'cool3': (0.45, 0.020, 245), 'cool4': (0.58, 0.016, 230),
    # warm-grey concrete: walls, pavement, curbs
    'con0': (0.24, 0.022, 325), 'con1': (0.32, 0.020, 305), 'con2': (0.41, 0.018, 285),
    'con3': (0.51, 0.016, 70), 'con4': (0.62, 0.018, 78),
    # brick brown: the hero building's upper floors and plinth
    'brk0': (0.25, 0.030, 15), 'brk1': (0.33, 0.035, 25), 'brk2': (0.41, 0.038, 35), 'brk3': (0.50, 0.035, 48),
    # wet asphalt
    'rd0': (0.17, 0.020, 262), 'rd1': (0.22, 0.022, 258), 'rd2': (0.28, 0.022, 252), 'rd3': (0.36, 0.020, 245),
    # teal glass (the near glass building)
    'gls0': (0.24, 0.030, 215), 'gls1': (0.33, 0.035, 208),
    # awnings: muted teal, faded maroon, the hero's indigo
    'awa0': (0.27, 0.035, 185), 'awa1': (0.37, 0.040, 180),
    'awb0': (0.26, 0.045, 12), 'awb1': (0.36, 0.050, 18),
    'awh0': (0.22, 0.045, 282), 'awh1': (0.30, 0.055, 280), 'awh2': (0.39, 0.055, 276),
    # warm light: lit windows, the tram strip, the lamp, their reflections (emissive)
    'win0': (0.44, 0.070, 52), 'win1': (0.56, 0.085, 60), 'win2': (0.67, 0.090, 68),
    'win3': (0.77, 0.080, 78), 'win4': (0.87, 0.060, 86),
    # the hero sign: warm white face, red-brown glyph ink (emissive)
    'hs0': (0.92, 0.035, 92), 'hs1': (0.975, 0.018, 95), 'gl0': (0.36, 0.120, 27),
    # the red paper lantern: the frame's top chroma (emissive)
    'lan0': (0.37, 0.130, 24), 'lan1': (0.50, 0.180, 27), 'lan2': (0.62, 0.200, 33),
    # cool teal neon: one box sign, the green signal (emissive)
    'neo0': (0.47, 0.070, 198), 'neo1': (0.66, 0.090, 192),
    # weather
    'rn0': (0.42, 0.020, 240), 'rn1': (0.58, 0.018, 230),
    'stm0': (0.40, 0.012, 250), 'stm1': (0.50, 0.010, 240),
    # props
    'clw': (0.72, 0.015, 95), 'wd0': (0.32, 0.040, 48), 'wd1': (0.44, 0.050, 60),
    'ps0': (0.48, 0.045, 320), 'pl0': (0.25, 0.040, 150), 'pl1': (0.34, 0.050, 145),
}
PAL = {k: lch(*v) for k, v in SPEC.items()}

# slots that emit: kept at albedo under the lamp map (they are the light, not lit by it)
EMISSIVE = ('win0', 'win1', 'win2', 'win3', 'win4', 'hs0', 'hs1', 'gl0', 'lan0', 'lan1', 'lan2', 'neo0', 'neo1')

LAB = {k: cl.rgb_to_oklab(np.array(cl.hex_to_rgb(v), float)) for k, v in PAL.items()}


def darker(slot, dL=0.08, keep_chroma=0.75, pool=None):
    """the palette slot nearest to `slot` dimmed by dL with its chroma scaled (reflections)"""
    L, a, b = LAB[slot]
    tgt = np.array([max(0.1, L - dL), a * keep_chroma, b * keep_chroma])
    best, bd = slot, 9.0
    for k in (pool or PAL):
        if k in ('hs0', 'hs1', 'clw') or k.startswith(('sky', 'rn', 'stm')):
            continue
        d = float(np.linalg.norm(LAB[k] - tgt))
        if d < bd:
            best, bd = k, d
    return best


if __name__ == '__main__':
    print(len(PAL), 'slots')
    for k, v in PAL.items():
        L, a, b = LAB[k]
        print('%-6s %s  L %.2f C %.3f' % (k, v, L, np.hypot(a, b)))
