"""relight(): shift a {slot: hex} palette toward a new light in OKLab (lightness scale and offset, hue pulled
toward `hue`, chroma scale), for the sunset and blue-hour phases of santorini.py.

Copied unchanged from library/san-francisco/art/palettes.py (first-party, MIT) so this piece renders without
that sibling piece; see history/migration.md."""
import numpy as np
import colorlib as cl

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
