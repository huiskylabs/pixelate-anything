"""The day palette of projections.py: every material is a 5-step hue-shifted ramp (NAME0 darkest .. NAME4
lightest) plus sky, glass and light slots.

Copied from library/san-francisco/art/palettes.py (first-party, MIT; MATERIALS and day() unchanged, the dusk,
night and relight parts dropped as unused here) so this piece renders without that sibling piece; see
history/migration.md."""
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
