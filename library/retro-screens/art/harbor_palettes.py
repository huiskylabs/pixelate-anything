"""Pixel Harbor palettes (copy of library/san-francisco/art/palettes.py, first-party MIT, unchanged apart from
this header, so title_screen.py renders without that sibling piece; see history/migration.md).
Iso City palettes. Every material is a 5-step hue-shifted ramp (NAME0 darkest .. NAME4
lightest); dusk and night are derived from day by relighting in OKLab, then the light sources
(windows, lamps, headlights, the beacon) are set by hand. One render, three palettes."""
import sys, pathlib
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / 'tools'))
import colorlib as cl
from palette import ramp

MATERIALS = {
    'earth': '#8a5a3c', 'grass': '#5aa04a', 'tree': '#3f8f4a', 'road': '#4d5263', 'walk': '#bcb3a4',
    'cream': '#e6d9bd', 'white': '#eeeae2', 'pink': '#e3aa9c', 'mint': '#a9d3b8', 'blue': '#a3bdd8',
    'brick': '#b05a48', 'glassy': '#4e5a75', 'granite': '#6a4a48', 'quartz': '#e4ded2', 'roof': '#8d8a93',
    'carR': '#d2443f', 'carY': '#f0bf3a', 'carB': '#4677d0', 'carW': '#e7e7e2', 'water': '#3d8fc6',
    'metal': '#7b8291',
}

def day():
    p = {'ol': '#1d1726'}
    for name, base in MATERIALS.items():
        for i, h in enumerate(ramp(base, 5, 24)):
            p['%s%d' % (name, i)] = h
    p.update({
        'sky0': '#7fc3ec', 'sky1': '#a6d8f2', 'sky2': '#d3eef8', 'star': '#a6d8f2', 'cloud': '#ffffff', 'cloudB': '#dcecf6',
        'glass': '#5d7393', 'paneHi': '#7e97b5', 'litA': '#5d7393', 'litB': '#5d7393', 'litC': '#5d7393', 'litD': '#5d7393',
        'lamp': '#d8d6c8', 'head': '#e8e6da', 'tail': '#a8403c', 'beacon': '#c9c4b8', 'lane': '#efd977',
        'zebra': '#e9e6dc', 'sun': '#fffbe6', 'sunB': '#ffe9a6', 'gull': '#ffffff',
    })
    for k in ('road', 'walk', 'grass'):                     # light-pool variants: same as unlit by day
        for i in range(5):
            p['%s%dL' % (k, i)] = p['%s%d' % (k, i)]
    return p

def relight(p, L_mul, L_add, hue, pull, c_mul, keep=()):
    out = {}
    for k, h in p.items():
        if k in keep:
            out[k] = h; continue
        lab = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(h), float))
        L, C, H = (float(v) for v in cl.lch_of(lab))
        d = ((hue - H + 180) % 360) - 180
        H2 = H + d * pull
        L2 = min(0.98, max(0.04, L * L_mul + L_add))
        C2 = cl.clamp_chroma(L2, C * c_mul + 0.02 * pull, H2)
        out[k] = cl.rgb_to_hex(cl.oklab_to_rgb(cl.oklch(L2, C2, H2)))
    return out

def dusk():
    p = relight(day(), 0.82, 0.02, 40, 0.28, 1.05)
    p.update({'sky0': '#5b4a8c', 'sky1': '#c0628a', 'sky2': '#f3a36b', 'star': '#c0628a', 'cloud': '#ffd0a6', 'cloudB': '#e98f86',
              'litA': '#ffcf6a', 'litB': '#5a5f80', 'litC': '#5a5f80', 'litD': '#ffcf6a', 'lamp': '#ffe9a0', 'beacon': '#ff5a4a',
              'sun': '#ffd27a', 'sunB': '#ff9a5c', 'gull': '#3a2c4a'})
    return p

def night():
    p = relight(day(), 0.48, 0.02, 265, 0.45, 0.7)
    p.update({'sky0': '#0c1030', 'sky1': '#17204a', 'sky2': '#2a3466', 'star': '#f4f0d0', 'cloud': '#2e3868', 'cloudB': '#222a58',
              'litA': '#ffd166', 'litB': '#ffb85a', 'litC': '#28304a', 'litD': '#fff0b0', 'lamp': '#fff4b8',
              'head': '#fff8d0', 'tail': '#ff4a3c', 'beacon': '#ff3a2e', 'ol': '#0b0814',
              'sun': '#f4eed2', 'sunB': '#bdb8a4', 'gull': '#17204a'})
    lit = {'road': ['#3a3448', '#5a4a52', '#7a6252', '#9a7c5c', '#b89868'],
           'walk': ['#4a4050', '#6e5c5a', '#957a64', '#b99a72', '#d8b880'],
           'grass': ['#24402e', '#36583a', '#4f7442', '#6e9048', '#93ac58']}
    for k, ramp_ in lit.items():
        for i, h in enumerate(ramp_):
            p['%s%dL' % (k, i)] = h
    return p

PHASES = {'day': day, 'dusk': dusk, 'night': night}
