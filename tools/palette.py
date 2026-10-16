#!/usr/bin/env python3
"""Palettes: extract from an image, build hue-shifted ramps in one of ten styles, grade, haze, export.

usage:
  palette.py extract IMAGE [-n 16] [-o OUT]       k-means in OKLab, sorted into hue families
  palette.py ramps NAME=#hex [NAME=#hex ...] [--steps 5] [--shift 22] [--style S] [-o OUT]
                                                  one ramp per material, named NAME0..NAME{steps-1}
  palette.py ramp #hex [--steps 5] [--shift 22] [--style S]   print one ramp
  palette.py styles [#hex ...] [-o OUT]           every ramp style on a few bases, as a swatch sheet
  palette.py between #dark #light [--steps 7]     a ramp that crosses temperature through grey (01)
  palette.py show PALETTE [-o OUT]                swatch sheet of any palette
  palette.py js PALETTE --name KEY                print a palettes.js entry ({slot: hex}) for a scene
  palette.py grade PALETTE --map #a,#b,#c [--amount 0.8] [--mode lch|lab] [--keep a,b]
                   [--window 245,350] [--floor 0.37] [-o OUT]
                                                  recolour a whole palette into one mood (below)
  palette.py haze PALETTE --fog #hex [--amount 0.8] [--contrast 0.4] [--prefix far_] [-o OUT]
                                                  a depth layer's copy of a palette (below)
  palette.py list                                 bundled presets

PALETTE is a preset name (palettes/*.hex), a .hex/.gpl/.json/.png file, or "#a,#b,...".
-o OUT writes OUT.hex, OUT.gpl (GIMP/Aseprite/Krita), OUT.json, OUT.png (1 px per colour,
loadable as a palette in Aseprite) and OUT-swatch.png (labelled, for looking at).

Ramps. ramp(base, steps, shift) with no style is the lofi ramp the older examples use: darks
drift toward blue-violet and get a touch more saturated, lights drift toward warm yellow and lose
saturation (shift degrees at the ends), about 0.125 L per step, the base colour stays exact.
The ten reference studies showed that is one style among many, so ramp() takes style=:

    ramp('#553d30', style='rise')     # 04 Sea of Stars: 8 steps of 0.054 L, chroma x1.6 toward the light
    ramp('#486a9e', style='arch')     # 06 Into the Breach: chroma peaks mid-ramp, lights go cool and white
    ramp('#ff0b68', style='flat')     # 07 Freitas: paint faces -0.12 -0.05 0 +0.04 +0.07 L, fixed hue
    ramp('#999996', style='living')   # 08 Owlboy: a grey with mauve darks and cream lights
    ramp('#654643', style='lit')      # 09 Katana ZERO: 9 steps of 0.055, red-brown darks, gold lights, hot top
    ramp('#73493b', style='plum')     # 10 Stardew: step 0 is the shared plum anchor dark
    ramp('#8f5f96', style='window')   # 02 Celeste: every hue held inside 245-350, floor L 0.37
    ramp('#2a8e11', style='toy')      # 10 creatures: constant hue, top step is a near-white glint
    ramp('#b95b16', style='arcade')   # 05 Metal Slug: lofi turn (+40 deg), body keeps C and caps at L .82, top = specular

and the knobs dL, L_range, dark_hue, light_hue, chroma_ends, l_max, anchor_dark, base_index and
window work with any style. ramp_path() splines a ramp through (L, C, h) stops, ramp_between()
crosses from one colour to another (navy to rose through grey, 01), neutral_ramp() places
near-greys at given L (06). ramps() is canvas.ramps with styles.

Grade: the Celeste move. One scene, one mood colour: every colour takes its hue and chroma from a
gradient map (first stop for the darks, last for the lights) by `amount`, and keeps its own
lightness, so every ramp keeps its order and every slot keeps its role. mode='lch' (default)
turns hue along the shortest arc and mixes chroma on its own, so complements never pass through
grey; keep= leaves slots alone (the cool wall behind the actor), hue_window= pulls stray hues
into the scene's window, floor_L= lifts the darks. flash() is the 2-frame lightning palette.

Haze: depth in the palette, never blur (08 Owlboy, 01). haze(pal, fog, amount, contrast) pulls
each colour's a/b toward the fog and squeezes its L toward the fog's L, and returns new slots
under a prefix (far_rock3 ...), so each depth layer stays indexed. haze_levels() makes the 01
k = 0.12 / 0.25 / 0.40 planes in one call.

Era ramps: era_ramp('#00a800', 3, anchor_dark='#000000', base_index=2) -> 000000 006800 00a800: an ordered ramp out of a
fixed console palette (NES, Game Boy, PICO-8) instead of computing tones that fall off it;
era_ramps() is its slot-dict form.

Families: families() writes a whole 03-style palette as role families (frame, heart, warm, hot,
spark, void) whose frame hue drifts across x; drift() makes the in-between ramps of two
families and drift_index() says which one each pixel uses.
"""
import json, math, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorlib as cl

# ---------------------------------------------------------------- OKLCh helpers
def lch(h):
    """'#hex' -> (L, C, h) in OKLCh"""
    L, C, H = cl.lch_of(cl.rgb_to_oklab(np.array(cl.hex_to_rgb(h), float)))
    return float(L), float(C), float(H)

def from_lch(L, C, h):
    """(L, C, h) -> '#hex', chroma clamped into the sRGB gamut at that L and hue"""
    L, h = min(1.0, max(0.0, float(L))), float(h) % 360
    return cl.rgb_to_hex(cl.oklab_to_rgb(cl.oklch(L, cl.clamp_chroma(L, max(0.0, float(C)), h), h)))

def arc(h0, h1):
    """signed shortest turn from hue h0 to hue h1, degrees in [-180, 180)"""
    return ((h1 - h0 + 180) % 360) - 180

def _toward(h0, target, deg):
    """turn h0 toward target by at most deg degrees along the shortest arc"""
    if target is None or not deg:
        return h0
    d = arc(h0, target)
    return h0 + math.copysign(min(abs(d), abs(deg)), d)

def _turn(h0, h1, w):
    """hue w of the way from h0 to h1 on the shorter side, as a mix of unit hue vectors: past
    w = 0.5 a near-complement lands near h1 from either side, so the colours of one ramp, whose
    hues sit either side of the antipode, all turn the same way (a linear angle would split them)"""
    a0, a1 = math.radians(h0), math.radians(h1)
    x, y = (1 - w) * math.cos(a0) + w * math.cos(a1), (1 - w) * math.sin(a0) + w * math.sin(a1)
    if math.hypot(x, y) < 1e-3:                        # an exact complement at w = 0.5
        return h0 + arc(h0, h1) * w
    return math.degrees(math.atan2(y, x)) % 360

def _pair(v, default):
    v = default if v is None else v
    return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))

# ---------------------------------------------------------------- ramps
def _lofi(base, steps, shift, dL=None, L_range=None, dark_hue=None, light_hue=None, bi=None):
    """the original ramp -> (hexes, [(L, C, h)], base index); with no knobs it is byte-identical.
    shift may be (dark, light)."""
    L0, C0, h0 = cl.lch_of(cl.rgb_to_oklab(np.array(cl.hex_to_rgb(base))))
    L0, C0, h0 = float(L0), float(C0), float(h0)
    if bi is None:
        bi = min(steps - 1, max(0, round((steps - 1) * 0.55)))
    lo, hi = (0.2, 0.95) if L_range is None else L_range
    dd, dl = (0.125, 0.13) if dL is None else (dL, dL)
    Lmin, Lmax = max(lo, L0 - dd * bi), min(hi, L0 + dl * (steps - 1 - bi))   # ~0.125 L per step
    tdark, tlight = 275.0 if dark_hue is None else dark_hue, 85.0 if light_hue is None else light_hue
    out, lch3 = [], []
    for i in range(steps):
        if i == bi:
            out.append(base.lower()); lch3.append((L0, C0, h0)); continue
        t = (i - bi) / max(1, bi) if i < bi else (i - bi) / max(1, steps - 1 - bi)   # -1 .. 1
        L = L0 + (L0 - Lmin) * t if t < 0 else L0 + (Lmax - L0) * t
        target = tdark if t < 0 else tlight          # shadows cool, lights warm
        d = ((target - h0 + 180) % 360) - 180
        sh = shift if not isinstance(shift, tuple) else shift[0] if t < 0 else shift[1]
        h = h0 + np.sign(d) * min(abs(d), sh * abs(t))
        C = C0 * ((L / L0) if L0 > 0 else 1.0) ** 0.8 * (1 + 0.15 * abs(t)) if t < 0 else C0 * (1 - 0.28 * t)
        C = cl.clamp_chroma(L, max(C, 0.0), h)
        out.append(cl.rgb_to_hex(cl.oklab_to_rgb(cl.oklch(L, C, h))))
        lch3.append((float(L), float(C), float(h)))
    return out, lch3, bi

# per style: default steps, L per step, (dark, light) hue targets, (dark, light) shift in degrees
RAMP_STYLES = {
    'lofi':   dict(steps=5, dL=None,  hues=(275, 85),   shift=(22, 22), ref='lantern-isle',
                   note='the original: cool darks, warm desaturating lights, ~0.125 L per step'),
    'rise':   dict(steps=8, dL=0.054, hues=None,        shift=(40, 25), ref='04 Sea of Stars',
                   note='long low-key ramp, chroma rises x1.6 toward the light, plum or teal darks'),
    'arch':   dict(steps=7, dL=0.069, hues=(None, 265), shift=(0, 14),  ref='06 Into the Breach',
                   note='chroma peaks mid-ramp, the lights go cooler and white, never warm'),
    'flat':   dict(steps=5, dL=0.05,  hues=(None, None), shift=(0, 0),  ref='07 Freitas',
                   note='gamut-edge paint: faces -0.12 -0.05 0 +0.04 +0.07 L at a fixed hue'),
    'living': dict(steps=6, dL=0.10,  hues=(0, 88),     shift=(22, 22), ref='08 Owlboy',
                   note='chroma added at both ends: mauve darks, neutral middle, cream lights'),
    'lit':    dict(steps=9, dL=0.055, hues=(12, 68),    shift=(16, 40), ref='09 Katana ZERO',
                   note='9 close steps, red-brown darks, gold lights gaining chroma, a hot top'),
    'plum':   dict(steps=5, dL=0.12,  hues=(None, 70),  shift=(0, 24),  ref='10 Stardew Valley',
                   note='step 0 is a shared plum anchor dark (#22101a), the lights go gold'),
    'window': dict(steps=5, dL=0.06,  hues=(295, 338),  shift=(30, 20), ref='02 Celeste',
                   note='hues held inside 245-350, lights to pink not yellow, floor L 0.37'),
    'toy':    dict(steps=5, dL=(0.16, 0.08), hues=(None, None), shift=(0, 0), ref='10 Stardew creatures',
                   note='constant hue, chroma follows L, the top step is a near-white glint'),
    'arcade': dict(steps=7, dL=None,  hues=(275, 85),   shift=(16, 26), ref='05 Metal Slug 3',
                   note='warm actor ramp (+40 deg dark to light), chroma held to L .8, body capped at L 0.82, top = specular'),
}

def _rise_hues(h0):
    """04: earth and reds sink to plum and rise to yellow; greens sink to teal; water and sky to navy"""
    if h0 < 100 or h0 >= 300:
        return 330.0, 95.0
    if h0 < 170:
        return 200.0, 105.0
    return 250.0, 185.0

def ramp(base, steps=None, shift=None, style=None, dL=None, L_range=None, dark_hue=None, light_hue=None,
         chroma_ends=None, l_max=None, anchor_dark=None, base_index=None, window=None, hot_jump=None):
    """'#hex' -> [hex] darkest first. The base colour sits exactly at base_index.

    style      None or 'lofi' (the original), 'rise', 'arch', 'flat', 'living', 'lit', 'plum',
               'window', 'toy', 'arcade' (see RAMP_STYLES; `palette.py styles` draws them)
    steps      default 5 (lofi) or the style's own (rise 8, arch 7, living 6, lit 9)
    shift      degrees of hue turn at the ends, one number or (dark, light)
    dL         L per step, or (dark, light) (lofi: 0.125 / 0.13; toy: 0.16 / 0.08)
    L_range    (lo, hi): the ramp spans exactly lo..hi with the base at its own L (lofi: a clamp)
    dark_hue, light_hue   hue targets the ends turn toward along the shortest arc
    chroma_ends (Cd, Cl): chroma ADDED at the dark and light end, toward dark_hue / light_hue,
               so even a neutral grey gets hued ends (living defaults to (0.03, 0.04))
    l_max      cap for the body tones; the top step stays as the specular (05: 0.82)
    anchor_dark  step 0 becomes this hex, steps 1..base-1 cross from it to the base (plum's default)
    window     (lo, hi) hue window: every chromatic step is turned inside it (window: (245, 350))
    hot_jump   extra L on the top step (lit: 0.12)
    """
    if style is None and dL is None and L_range is None and dark_hue is None and light_hue is None and \
            chroma_ends is None and l_max is None and anchor_dark is None and base_index is None and window is None:
        return _lofi(base, 5 if steps is None else steps, 22.0 if shift is None else shift)[0]
    style = style or 'lofi'
    if style not in RAMP_STYLES:
        raise ValueError('ramp style %r: one of %s' % (style, ', '.join(RAMP_STYLES)))
    S = RAMP_STYLES[style]
    n = int(S['steps'] if steps is None else steps)
    if n < 1:
        raise ValueError('a ramp needs at least one step')
    if n == 1:
        return [base.lower()]
    L0, C0, h0 = lch(base)
    hues = S['hues'] if S['hues'] is not None else _rise_hues(h0)
    hd = hues[0] if dark_hue is None else dark_hue
    hl = hues[1] if light_hue is None else light_hue
    sd, sl = _pair(shift, S['shift'])
    if style == 'arcade' and l_max is None:
        l_max = 0.82
    if style in ('lofi', 'arcade'):
        if style == 'arcade' and L_range is None and L0 < 0.3:   # lofi's 0.2 floor would lift a dark base's darks
            L_range = (L0 * 0.5, 0.95)
        _, pts, bi = _lofi(base, n, (sd, sl), dL, L_range, hd, hl, base_index)
        if style == 'arcade':                          # 05 chitin: chroma peaks at L .6-.7, the body lights keep it
            pts = [list(p) for p in pts]
            for i in range(bi + 1, n - 1):
                pts[i][1] = C0 * (1.05 - 0.2 * (i - bi) / max(1, n - 1 - bi))
        return _finish(base, pts, bi, n, style, hd, hl, chroma_ends, l_max, anchor_dark, window)
    body = n - 1 if style == 'toy' else n              # toy: the last step is the glint
    step = S['dL'] if dL is None else dL
    # where the base sits
    if base_index is not None:
        bi = int(base_index)
    elif L_range is not None:
        lo, hi = L_range
        bi = int(round((body - 1) * (min(hi, max(lo, L0)) - lo) / max(1e-6, hi - lo)))
    elif style == 'rise':
        bi = int(round(0.43 * (body - 1)))
    elif style == 'arch':                              # the lights climb to white at dL; a dark base
        bi = body - 1 - int(math.floor((0.95 - L0) / _pair(step, 0)[1]))   # still keeps ~30% darks
        lo_bi = int(round(0.3 * (body - 1)))
        if bi < lo_bi and L0 < 0.95:
            bi = lo_bi
            step = (_pair(step, 0)[0], (0.95 - L0) / max(1, body - 1 - bi))
    elif style == 'lit':
        bi = (body - 1) // 2
    elif style == 'flat':
        bi = body - 1 - min(2, (body - 1) // 2)
    elif style == 'plum':                              # anchor, crossing steps, base, then the gold lights
        bi = int(round(0.7 * (body - 1)))
    else:
        bi = int(round(0.55 * (body - 1)))
    bi = min(body - 1, max(0, bi))
    # lightness
    st_d, st_l = _pair(step, 0)
    if style == 'flat':
        k = st_d / 0.05
        dark_off = [-0.05, -0.12] + [-0.12 - 0.08 * j for j in range(1, body)]
        light_off = [0.04, 0.07] + [0.07 + 0.03 * j for j in range(1, body)]
        Ls = [L0 + k * (dark_off[bi - 1 - i] if i < bi else light_off[i - bi - 1] if i > bi else 0)
              for i in range(body)]
    else:
        Ls = [L0 + (st_d if i < bi else st_l) * (i - bi) for i in range(body)]
    if L_range is not None:
        lo, hi = L_range
        Lb = min(hi, max(lo, L0))
        Ls = [lo + (Lb - lo) * (i / bi) if i < bi else Lb if i == bi else
              Lb + (hi - Lb) * ((i - bi) / max(1, body - 1 - bi)) for i in range(body)]
    if style == 'lit' and body > bi + 1:
        Ls[-1] += 0.12 if hot_jump is None else hot_jump
    elif hot_jump:
        Ls[-1] += hot_jump
    if style == 'window' and min(Ls) < 0.37 and L0 > 0.37:   # lifted floor: squeeze the darks, keep order
        lo_ = min(Ls)
        Ls = [0.37 + (L - lo_) * (L0 - 0.37) / (L0 - lo_) if i < bi else L for i, L in enumerate(Ls)]
    Ls = _fit(Ls, bi, L0)
    pts = []
    for i in range(body):
        if i == bi:
            pts.append((L0, C0, h0)); continue
        t = (i - bi) / max(1, bi) if i < bi else (i - bi) / max(1, body - 1 - bi)
        u, L = abs(t), Ls[i]
        h = _toward(h0, hd, sd * u) if t < 0 else _toward(h0, hl, sl * t)
        if style == 'rise':
            C = C0 + (0.018 - C0) * u ** 0.9 if t < 0 else min(C0 * (1 + 0.8 * t ** 0.9), max(C0, 0.14))
        elif style == 'arch':
            C = C0 * (1 - 0.35 * u ** 1.2) if t < 0 else C0 * (1 - 0.93 * t ** 1.6)
        elif style == 'flat':
            C = C0 * (0.8 if (i == body - 1 and body - 1 - bi >= 2) else 1.0)
        elif style == 'living':                       # the base's own chroma follows L; the ends are added below
            C = C0 * (L / L0 if L0 > 0 else 1) if t < 0 else C0 * (1 - 0.3 * t)
        elif style == 'lit':
            C = C0 * ((L / L0) if L0 > 0 else 1) ** 1.2 if t < 0 else C0 * (1 + 0.2 * min(i - bi, 2))
        elif style == 'plum':
            C = C0 * (L / L0 if L0 > 0 else 1) if t < 0 else C0 * (1 + 0.3 * t)   # 10: the gold top gains C
        elif style == 'window':
            C = C0 * (1 + 0.15 * u) if t < 0 else C0 * (1 + 0.3 * t)     # measured: the rock lights gain chroma
        else:                                          # toy: chroma follows L, so the creature pops
            C = C0 * (L / L0 if L0 > 0 else 1)
        pts.append((L, C, h))
    if style == 'toy':                                 # the glint: near white, a breath of the hue
        pts.append((max(0.95, pts[-1][0] + 0.05), min(0.03, C0 * 0.3), h0))
    if style == 'plum' and anchor_dark is None:
        anchor_dark = '#22101a'
    if style == 'living' and chroma_ends is None:
        chroma_ends = (0.03, 0.04)
    if style == 'window' and window is None:
        window = (245, 350)
    return _finish(base, pts, bi, n, style, hd, hl, chroma_ends, l_max, anchor_dark, window)

def _fit(Ls, bi, L0, lo=0.03, hi=0.985):
    """keep the steps inside lo..hi by squeezing that side's spacing, not by clipping (clipping
    stacks the end steps onto one colour); the base keeps its own L"""
    Ls = list(Ls)
    top, bot = max(Ls[bi + 1:], default=L0), min(Ls[:bi], default=L0)
    if top > hi and L0 < hi:
        Ls[bi + 1:] = [L0 + (L - L0) * (hi - L0) / (top - L0) for L in Ls[bi + 1:]]
    if bot < lo and L0 > lo:
        Ls[:bi] = [L0 - (L0 - L) * (L0 - lo) / (L0 - bot) for L in Ls[:bi]]
    return [min(max(hi, L0), max(min(lo, L0), L)) if i != bi else L for i, L in enumerate(Ls)]

def _finish(base, pts, bi, n, style, hd, hl, chroma_ends, l_max, anchor_dark, window):
    """the knobs every style shares, then hexes (the base stays exact unless a knob moved it)"""
    pts = [list(p) for p in pts]
    orig = tuple(pts[bi])
    if anchor_dark is not None and bi > 0 and lch(anchor_dark)[0] < pts[bi][0] - 0.02:   # step 0 = the anchor
        La, Ca, ha = lch(anchor_dark)
        L0, C0, h0 = pts[bi]
        d = arc(ha, h0) if Ca > 0.01 and C0 > 0.01 else 0.0
        if Ca <= 0.01: ha = h0
        far = abs(d) > 90                              # plum to green: cross through grey, not orange
        for i in range(bi):
            s = i / bi
            if far:
                a_ = Ca * math.cos(math.radians(ha)) * (1 - s) + C0 * math.cos(math.radians(h0)) * s
                b_ = Ca * math.sin(math.radians(ha)) * (1 - s) + C0 * math.sin(math.radians(h0)) * s
                pts[i] = [La + (L0 - La) * s, math.hypot(a_, b_), math.degrees(math.atan2(b_, a_)) % 360]
            else:
                pts[i] = [La + (L0 - La) * s, Ca + (C0 - Ca) * s, ha + d * s]
    if chroma_ends is not None and any(chroma_ends):   # additive chroma toward the end hues
        cd, cl_ = chroma_ends
        for i, (L, C, h) in enumerate(pts):
            if i == bi: continue
            t = (i - bi) / max(1, bi) if i < bi else (i - bi) / max(1, n - 1 - bi)
            add, th = (cd * (-t) ** 1.2, hd) if t < 0 else (cl_ * t ** 1.5, hl)
            th = h if th is None else th
            a = C * math.cos(math.radians(h)) + add * math.cos(math.radians(th))
            b = C * math.sin(math.radians(h)) + add * math.sin(math.radians(th))
            pts[i] = [L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360]
    if l_max is not None and n - 2 > bi and l_max > pts[bi][0]:   # squeeze the body lights under l_max
        L0 = pts[bi][0]
        top = pts[n - 2][0]
        if top > l_max:
            for i in range(bi + 1, n - 1):
                pts[i][0] = L0 + (pts[i][0] - L0) * (l_max - L0) / (top - L0)
    if window is not None:                             # hold every chromatic hue inside the window
        lo, hi = window
        for p in pts:
            if p[1] > 0.02 and (p[2] - lo) % 360 > (hi - lo) % 360:
                p[2] = lo if abs(arc(p[2], lo)) < abs(arc(p[2], hi)) else hi
    out = []
    for i, p in enumerate(pts):
        out.append(base.lower() if i == bi and tuple(p) == orig else from_lch(*p))
    return out

def ramps(bases, steps=None, shift=None, extra=None, **kw):
    """{'rock': '#hex'} -> {'rock0': .., 'rockN': ..}: canvas.ramps with ramp styles and knobs.
    A list of hexes is taken as the ramp itself; a dict value is per-material ramp() kwargs
    ({'rock': dict(base='#553d30', style='rise')})."""
    pal = {}
    for name, base in bases.items():
        if isinstance(base, (list, tuple)):
            hexes = list(base)
        elif isinstance(base, dict):
            k = dict(kw); k.update(base); b = k.pop('base')
            hexes = ramp(b, k.pop('steps', steps), k.pop('shift', shift), **k)
        else:
            hexes = ramp(base, steps, shift, **kw)
        for i, h in enumerate(hexes):
            pal['%s%d' % (name, i)] = h
    pal.update(extra or {})
    return pal

# ---------------------------------------------------------------- ramps held to a fixed console palette
ERA_PALETTES = {'nes': 'nes', 'famicom': 'nes', 'gameboy': 'gameboy', 'gb': 'gameboy', 'pico-8': 'pico-8', 'pico8': 'pico-8'}

def _era_colours(era, exclude=()):
    """(hexes, OKLab) of an era's fixed palette, a palette preset/file, or a hex list; duplicates dropped"""
    if isinstance(era, (list, tuple, dict)):
        hexes = cl.palette_list(era)
    elif era in ERA_PALETTES:
        hexes = cl.palette_list(cl.load_palette(ERA_PALETTES[era]))
    elif era in ('snes', 'genesis', 'gba', 'neogeo'):
        raise ValueError('era %r has no fixed palette (a bit depth): use ramp() and era.enforce' % era)
    else:
        hexes = cl.palette_list(cl.load_palette(era))
    drop = {('#' + h.lstrip('#')).lower() for h in exclude}
    out = []
    for h in hexes:
        h = ('#' + h.lstrip('#')).lower()
        if h not in out and h not in drop:
            out.append(h)
    return out, cl.rgb_to_oklab(np.array([cl.hex_to_rgb(h) for h in out], float))

def era_ramp(base, steps=3, era='nes', dL=0.2, min_dL=None, base_index=None, anchor_dark=None,
             chroma_fall=0.2, exclude=(), centre=0.03):
    """'#hex' -> [hex] darkest first, every step a colour of the era's fixed palette, learnt from NES
    and Game Boy art, where a material ramp is 3 or 4 hand-picked master-palette entries (black,
    005800, 00a800) rather than computed tones. The palette colour nearest the base is always in the
    ramp; the other steps are the ordered choice (L strictly rising by at least min_dL) that stays
    closest to the base's hue and chroma (falling by chroma_fall per step away from it) near
    evenly spaced L targets dL apart. Deterministic: a dynamic programme, no randomness.
    min_dL None is 0.06, relaxed to any rise when the palette is too small for it (Game Boy).

    era          'nes', 'gameboy', 'pico-8' (aliases famicom, gb, pico8), any palette preset or file,
                 or a list of hexes
    base_index   where the base sits; None tries every position and keeps the best, a position
                 costing `centre` per step away from the lofi ramp's (55% up the ramp)
    anchor_dark  step 0 is fixed to the palette colour nearest this (the NES backdrop '#000000')
    exclude      palette hexes never used (a colour reserved for the HUD)
    """
    hexes, lab = _era_colours(era, exclude)
    n = int(steps)
    if n < 1:
        raise ValueError('a ramp needs at least one step')
    P = len(hexes)
    L, ab = lab[:, 0], lab[:, 1:]
    b = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(base), float)).reshape(3)
    a_idx = int(cl.nearest(b[None], lab)[0])
    d_idx = None if anchor_dark is None else int(cl.nearest(
        cl.rgb_to_oklab(np.array(cl.hex_to_rgb(anchor_dark), float)).reshape(1, 3), lab)[0])
    if n == 1:
        return [hexes[a_idx]]
    lo, hi = float(L.min()), float(L.max())
    mid = min(n - 1, max(0, round((n - 1) * 0.55)))
    for gap in ((0.06, 1e-6) if min_dL is None else (min_dL,)):
        best = _era_dp(L, ab, n, a_idx, d_idx, lo, hi, dL, gap, chroma_fall,
                       [base_index] if base_index is not None else range(n), mid, centre)
        if best[1] is not None:
            break
    if best[1] is None:
        raise ValueError('no %d-step ordered ramp through %s in the %s palette (%d colours)' % (
            n, hexes[a_idx], era if isinstance(era, str) else 'given', P))
    return [hexes[j] for j in best[1]]

def _era_dp(L, ab, n, a_idx, d_idx, lo, hi, dL, min_dL, chroma_fall, positions, mid, centre):
    """the cheapest ordered path of n palette indices through a_idx -> (cost, path or None)"""
    P = len(L)
    best = (np.inf, None)
    for bi in positions:
        if d_idx is not None and (bi == 0) != (d_idx == a_idx):
            continue
        cost = np.empty((n, P))
        for k in range(n):
            Lt = min(hi, max(lo, L[a_idx] + (k - bi) * dL))
            s = max(0.0, 1.0 - chroma_fall * abs(k - bi))
            cost[k] = np.linalg.norm(ab - s * ab[a_idx], axis=1) + 0.5 * np.abs(L - Lt)
        cost[bi] = np.inf; cost[bi, a_idx] = 0.0
        if d_idx is not None:
            cost[0] = np.inf; cost[0, d_idx] = 0.0
        ok = (L[None, :] - L[:, None]) >= min_dL                  # ok[i, j]: j may follow i
        acc, back = cost[0].copy(), np.zeros((n, P), int)
        for k in range(1, n):
            t = np.where(ok, acc[:, None], np.inf)                # (from, to)
            back[k] = t.argmin(0)
            acc = t.min(0) + cost[k]
        j = int(acc.argmin())
        if np.isfinite(acc[j]) and acc[j] + centre * abs(bi - mid) < best[0]:
            path = [j]
            for k in range(n - 1, 0, -1):
                path.append(int(back[k][path[-1]]))
            best = (float(acc[j]) + centre * abs(bi - mid), path[::-1])
    return best

def era_ramps(bases, steps=3, era='nes', extra=None, **kw):
    """{'leaf': '#00a800'} -> {'leaf0': .., 'leaf2': ..}: era_ramp per material, slot names as ramps();
    a list of hexes is taken as the ramp itself, a dict value is per-material era_ramp kwargs"""
    pal = {}
    for name, base in bases.items():
        if isinstance(base, (list, tuple)):
            hexes = list(base)
        elif isinstance(base, dict):
            k = dict(kw); k.update(base); b = k.pop('base')
            hexes = era_ramp(b, k.pop('steps', steps), k.pop('era', era), **k)
        else:
            hexes = era_ramp(base, steps, era, **kw)
        for i, h in enumerate(hexes):
            pal['%s%d' % (name, i)] = h
    pal.update(extra or {})
    return pal

def _pchip(x, y, xq):
    """monotone cubic (Fritsch-Carlson): smooth through the stops, no overshoot"""
    x, y, xq = np.asarray(x, float), np.asarray(y, float), np.asarray(xq, float)
    if len(x) == 1:
        return np.full_like(xq, y[0])
    h = np.diff(x); dl = np.diff(y) / h
    m = np.zeros_like(y)
    m[0], m[-1] = dl[0], dl[-1]
    for k in range(1, len(x) - 1):
        if dl[k - 1] * dl[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / dl[k - 1] + w2 / dl[k])
    k = np.clip(np.searchsorted(x, xq, side='right') - 1, 0, len(x) - 2)
    s = (xq - x[k]) / h[k]
    h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
    return h00 * y[k] + h10 * h[k] * m[k] + h01 * y[k + 1] + h11 * h[k] * m[k + 1]

def _stop(s):
    return lch(s) if isinstance(s, str) else tuple(float(v) for v in s)

def ramp_path(stops, steps=None, by='L'):
    """[(L, C, h) or '#hex', ...] darkest first -> [hex]: a ramp splined through the stops.
    Hue runs along the shortest arc between neighbouring stops; a near-grey stop takes its
    neighbour's hue. by='L' spaces the steps evenly in lightness (the stops' L must rise),
    by='index' evenly along the stop list. steps=None returns just the stops.

        stone = ramp_path([(0.39, 0.03, 0), (0.57, 0.006, 40), (0.76, 0.02, 92), (0.90, 0.045, 85)], 6)
    """
    P = [list(_stop(s)) for s in stops]
    if steps is None:
        steps = len(P)
    for i, p in enumerate(P):                          # greys borrow a hue so they do not swing it
        if p[1] < 0.01:
            nb = [q for q in P[i + 1:] + P[:i][::-1] if q[1] >= 0.01]
            if nb: p[2] = nb[0][2]
    hs = [P[0][2]]
    for p in P[1:]:
        hs.append(hs[-1] + arc(hs[-1], p[2]))
    if by == 'L':
        x = np.array([p[0] for p in P])
        if np.any(np.diff(x) <= 0):
            raise ValueError('ramp_path by=L needs stops with rising L')
        xq = np.linspace(x[0], x[-1], steps)
    else:
        x = np.linspace(0, 1, len(P)); xq = np.linspace(0, 1, steps)
    L = _pchip(x, [p[0] for p in P], xq)
    C = np.maximum(0, _pchip(x, [p[1] for p in P], xq))
    H = _pchip(x, hs, xq)
    return [from_lch(*v) for v in zip(L, C, H)]

def ramp_between(dark, light, steps=7, chroma=None, power=1.4, hue_path='short', through_grey=None, cross=None):
    """a ramp from one colour to another with its own chroma curve: L linear, hue linear along
    the shortest (or 'long') arc, C = c0 + (c1 - c0) * s**power. 01 Sword & Sworcery: the cool
    navy darks cross into the warm rose lights through near-zero chroma, so the switch never
    shows green or violet. through_grey (default: when the hues are over 90 degrees apart and both
    ends have colour): the dark's chroma fades to 0 at `cross` (default where the two chromas
    balance) and the light's hue rises from there; the hue never sweeps the arc in between.

        ramp_between('#262523', '#a07167', 9, chroma=(0.004, 0.065))    # the 01 bridge ramp
    """
    L0, C0, h0 = lch(dark); L1, C1, h1 = lch(light)
    c0, c1 = (C0, C1) if chroma is None else chroma
    if C0 < 0.01: h0 = h1
    if C1 < 0.01: h1 = h0
    d = arc(h0, h1)
    if hue_path == 'long' and d:
        d -= math.copysign(360, d)
    if through_grey is None:
        through_grey = abs(d) > 90 and c0 > 0.01 and c1 > 0.01
    s0 = c0 / max(1e-6, c0 + c1) if cross is None else float(cross)
    out = []
    for i in range(steps):
        s = i / max(1, steps - 1)
        if chroma is None and i in (0, steps - 1):
            out.append((dark if i == 0 else light).lower()); continue
        L = L0 + (L1 - L0) * s
        if not through_grey:
            out.append(from_lch(L, c0 + (c1 - c0) * s ** power, h0 + d * s))
        elif s < s0:
            out.append(from_lch(L, c0 * ((s0 - s) / s0) ** power, h0))
        else:
            out.append(from_lch(L, c1 * ((s - s0) / max(1e-6, 1 - s0)) ** power, h1))
    return out

def neutral_ramp(Ls, hue=300, chroma=0.006):
    """near-greys at the given L values (06: five greys carry the whole stage). hue and chroma
    may be single values or one per step.  neutral_ramp([.13, .18, .24, .28, .34], [20, 0, 315, 0, 270],
    [.006, 0, .008, 0, .006])"""
    n = len(Ls)
    hs = list(hue) if isinstance(hue, (list, tuple)) else [hue] * n
    cs = list(chroma) if isinstance(chroma, (list, tuple)) else [chroma] * n
    return [from_lch(L, c, h) for L, c, h in zip(Ls, cs, hs)]

# ---------------------------------------------------------------- whole-palette moves
def _items(pal):
    return list(pal.items()) if isinstance(pal, dict) else list(enumerate(pal))

def _kept(key, keep):
    if not keep and keep != 0:
        return False
    if isinstance(keep, (str, int)):
        keep = (keep,)
    s = str(key)
    base = s.rstrip('0123456789')
    for k in keep:
        if not isinstance(k, str):
            if key == k: return True
        elif s == k or base == k or (k.endswith('*') and s.startswith(k[:-1])):
            return True
    return False

def grade(pal, stops, amount=0.8, chroma=1.0, mode='lch', keep=(), hue_window=None, floor_L=None,
          span='palette', window_pull=0.6):
    """{slot: hex} or [hex] -> the same, recoloured toward a gradient map of `stops` (hexes, darks
    first) by `amount` 0..1, keeping each colour's lightness. chroma scales the result's chroma.

    mode       'lch': hue turns toward the map's hue on the shorter side (a mix of unit hue
               vectors, so one ramp never splits either side of the antipode) and chroma mixes on
               its own, so complements never go grey; 'lab': the plain a/b mix
    keep       slots left exactly as they are: names, ramp bases ('wall' keeps wall0..wall6),
               'prefix*' patterns, or list indices
    hue_window (lo, hi): hues that end up outside are turned window_pull of the way to the
               nearest edge (02: (245, 350))
    floor_L    the darks are lifted so nothing sits below it; order is kept (02: 0.37)
    span       which L range indexes the map: 'palette' (its own darkest..lightest, the default),
               'stops' (the stops' own L) or (lo, hi). With 'stops' or a fixed span, adding black
               or white to the palette does not move every other colour along the map.
    """
    items = _items(pal)
    if not items or not stops:
        return dict(pal) if isinstance(pal, dict) else list(pal)
    lab = cl.rgb_to_oklab(np.array([cl.hex_to_rgb(h) for _, h in items], float))
    stop_lab = cl.rgb_to_oklab(np.array([cl.hex_to_rgb(h) for h in stops], float))
    L = lab[:, 0]
    if span == 'palette':
        lo, hi = float(L.min()), float(L.max())
    elif span == 'stops':
        lo, hi = float(stop_lab[:, 0].min()), float(stop_lab[:, 0].max())
    else:
        lo, hi = span
    k = np.clip((L - lo) / max(1e-6, hi - lo), 0, 1) * (len(stops) - 1)
    i0 = np.minimum(k.astype(int), len(stops) - 2) if len(stops) > 1 else np.zeros(len(k), int)
    f = (k - i0)[:, None] if len(stops) > 1 else np.zeros((len(k), 1))
    i1 = np.minimum(i0 + 1, len(stops) - 1)
    if mode == 'lab':
        g = stop_lab[i0] * (1 - f) + stop_lab[i1] * f
        ab = lab[:, 1:] * (1 - amount) + g[:, 1:] * amount
        out_lab = np.column_stack([L, ab * chroma])
        res = []
        for c in out_lab:
            Lc, Cc, Hc = cl.lch_of(c)
            res.append(cl.rgb_to_hex(cl.oklab_to_rgb(cl.oklch(float(Lc), float(cl.clamp_chroma(float(Lc), float(Cc), float(Hc))), float(Hc)))))
    else:
        _, SC, SH = cl.lch_of(stop_lab)
        _, PC, PH = cl.lch_of(lab)
        res = []
        for j in range(len(items)):
            a, b, s = int(i0[j]), int(i1[j]), float(f[j, 0])
            ha, hb = float(SH[a]), float(SH[b])
            if SC[a] < 0.01: ha = hb
            if SC[b] < 0.01: hb = ha
            gh = ha + arc(ha, hb) * s                  # the map itself in LCh: no grey midpoints
            gc = float(SC[a]) * (1 - s) + float(SC[b]) * s
            c0, h0 = float(PC[j]), float(PH[j])
            w = amount + (1 - amount) * min(1.0, max(0.0, 1 - c0 / 0.03))   # a grey takes the map's hue
            h = _turn(h0, gh, w) if gc > 0.005 else h0
            C = (c0 * (1 - amount) + gc * amount) * chroma
            Lj = float(L[j])
            res.append((Lj, C, h % 360))
        if hue_window is not None:
            wl, wh = hue_window
            res2 = []
            for Lj, C, h in res:
                if C > 0.02 and (h - wl) % 360 > (wh - wl) % 360:
                    e = wl if abs(arc(h, wl)) < abs(arc(h, wh)) else wh
                    h = h + arc(h, e) * window_pull
                res2.append((Lj, C, h))
            res = res2
        if floor_L is not None:
            Ls = np.array([r[0] for r in res])
            lo_ = float(Ls.min())
            if lo_ < floor_L:                          # squeeze [lo, floor + 0.15] into [floor, floor + 0.15]
                top = floor_L + 0.15
                res = [((floor_L + (Lj - lo_) * (top - floor_L) / (top - lo_)) if Lj < top else Lj, C, h)
                       for Lj, C, h in res]
        res = [from_lch(*r) for r in res]
    out = [(key, (h0 if _kept(key, keep) else h1)) for (key, h0), h1 in zip(items, res)]
    return dict(out) if isinstance(pal, dict) else [h for _, h in out]

def flash(pal, colour='#ffffff', amount=0.5, lift=0.35, keep=()):
    """the 1-2 frame lightning or hit palette: L' = L + (1 - L) * lift, a/b pulled toward the
    flash colour by amount. Swap the scene palette for this one for exactly those frames (05, 02)."""
    fl = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(colour), float))
    out = []
    for key, h in _items(pal):
        if _kept(key, keep):
            out.append((key, h)); continue
        c = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(h), float))
        L = c[0] + (1 - c[0]) * lift
        a, b = c[1:] * (1 - amount) + fl[1:] * amount
        Lc, Cc, Hc = cl.lch_of(np.array([L, a, b]))
        out.append((key, from_lch(float(Lc), float(Cc), float(Hc))))
    return dict(out) if isinstance(pal, dict) else [h for _, h in out]

def haze(pal, fog, amount=0.8, contrast=0.4, lift=0.0, prefix='far_'):
    """a depth layer's palette: in OKLab L' = Lf + (L - Lf) * contrast + lift, ab' = ab moved toward
    the fog's ab by amount. A dict comes back as new slots {prefix + slot: hex} so the far layer
    is drawn with its own indexed slots (far_rock3 ...); a list comes back as a list.
    08 Owlboy: far = haze(pal, '#4e3c52', 0.8, 0.4), mid = haze(pal, '#565470', 0.4, 0.8, prefix='mid_')."""
    f = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(fog), float))
    out = []
    for key, h in _items(pal):
        c = cl.rgb_to_oklab(np.array(cl.hex_to_rgb(h), float))
        L = f[0] + (c[0] - f[0]) * contrast + lift
        a, b = c[1:] * (1 - amount) + f[1:] * amount
        Lc, Cc, Hc = cl.lch_of(np.array([L, a, b]))
        out.append(('%s%s' % (prefix, key), from_lch(float(Lc), float(Cc), float(Hc))))
    return dict(out) if isinstance(pal, dict) else [h for _, h in out]

def haze_levels(pal, fog, ks=(0.12, 0.25, 0.40), prefix='f%d_'):
    """01 Sword & Sworcery planes: level k mixes every colour k of the way to the fog (L too).
    -> {'f1_rock3': .., 'f2_rock3': .., ...}; level 0 is the palette itself."""
    out = {}
    for n, k in enumerate(ks, 1):
        out.update(haze(pal, fog, amount=k, contrast=1 - k, prefix=prefix % n))
    return out

def drift(ramp_a, ramp_b, n=4):
    """n ramps from family a to family b (both included), step by step in LCh along the
    shortest hue arc with chroma mixed on its own, so the middle ramps never go grey.
    03: drift(teal_frame, indigo_frame, 4) drawn per x band."""
    if len(ramp_a) != len(ramp_b):
        raise ValueError('drift needs ramps of the same length')
    A, B = [lch(h) for h in ramp_a], [lch(h) for h in ramp_b]
    out = []
    for k in range(n):
        s = k / max(1, n - 1)
        if k == 0: out.append([h.lower() for h in ramp_a]); continue
        if k == n - 1: out.append([h.lower() for h in ramp_b]); continue
        r = []
        for (La, Ca, ha), (Lb, Cb, hb) in zip(A, B):
            if Ca < 0.01: ha = hb
            if Cb < 0.01: hb = ha
            r.append(from_lch(La + (Lb - La) * s, Ca + (Cb - Ca) * s, ha + arc(ha, hb) * s))
        out.append(r)
    return out

def drift_slots(name, ramp_a, ramp_b, n=4):
    """drift() as slots: {name + 'a' + step, name + 'b' + step, ...}, band a on the left"""
    return {'%s%s%d' % (name, chr(97 + k), i): h for k, r in enumerate(drift(ramp_a, ramp_b, n))
            for i, h in enumerate(r)}

def _hash2(x, y, seed):
    h = (np.asarray(x, np.int64) * 374761393 + np.asarray(y, np.int64) * 668265263 + seed * 2654435761) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0

def drift_index(W, H, n=4, jitter=6, run=4, seed=0, axis='x'):
    """(H, W) int band of drift() to use per pixel: bands across x (or y), with boundaries that
    step by up to `jitter` px every `run` rows so no straight seam shows. Band letter = chr(97 + i)."""
    yy, xx = np.mgrid[0:H, 0:W]
    pos, other, size = (xx, yy, W) if axis == 'x' else (yy, xx, H)
    off = (_hash2(other // max(1, run), 7, seed) - 0.5) * 2 * jitter
    return np.clip(((pos + off) * n / size).astype(int), 0, n - 1)

def families(frame=('#0c3140', '#193356'), frame_hue=(228, 285), heart='#2aad62', warm='#81574e',
             accents=('#fb565e', '#ff6544'), sparks=('#1afc88', '#87fcdd'), plum='#331d39', void='#000000',
             bands=4, frame_steps=6, frame_L=(0.20, 0.40)):
    """03 Hyper Light Drifter: a low-key palette written as role families before any drawing.
    -> {slot: hex} with
      frame{a..}{0..}  the frame ramps (L 0.20-0.40, C ~0.05), one per x band, hue drifting
                       frame_hue[0] -> frame_hue[1] from left to right (use drift_index)
      plum0..3         the right flank's sub-family (L 0.25-0.35)
      heart0..4        the lit heart (emerald, L 0.45-0.85)
      warm0..3         khaki surfaces near emitters (L 0.30-0.50)
      hot0..           the emitters, darkest first (C >= 0.20); spark0.. the motes; void
    Budget (stats.budget): hot under 1.5% of pixels, heart about 20%, frame about 70%."""
    fr = [frame] if isinstance(frame, str) else list(frame)
    Cf = float(np.mean([lch(h)[1] for h in fr]))
    pal = {}
    for k in range(bands):
        s = (k + 0.5) / bands
        h = frame_hue[0] + arc(frame_hue[0], frame_hue[1]) * s
        stops = [(frame_L[0], Cf * 0.75, h - 6), ((frame_L[0] + frame_L[1]) / 2, Cf, h), (frame_L[1], Cf * 0.85, h + 6)]
        for i, v in enumerate(ramp_path(stops, frame_steps)):
            pal['frame%s%d' % (chr(97 + k), i)] = v
    if plum:
        Lp, Cp, hp = lch(plum)
        for i, v in enumerate(ramp_path([(0.25, max(Cp, 0.04), hp), (0.35, max(Cp, 0.04) * 0.9, hp + 8)], 4)):
            pal['plum%d' % i] = v
    if heart:
        Lh, Ch, hh = lch(heart)                        # emerald body, sage-mint lights (03)
        Lh = min(0.78, max(0.52, Lh))
        for i, v in enumerate(ramp_path([(0.45, Ch * 0.6, hh + 6), (Lh, Ch, hh), (0.85, Ch * 0.55, hh + 4)], 5)):
            pal['heart%d' % i] = v
    if warm:
        Lw, Cw, hw = lch(warm)
        for i, v in enumerate(ramp_path([(0.30, Cw * 0.8, hw - 6), (0.50, Cw, hw + 6)], 4)):
            pal['warm%d' % i] = v
    for name, cols in (('hot', accents), ('spark', sparks)):
        cols = sorted(cols or (), key=lambda c: lch(c)[0])
        for i, v in enumerate(cols):
            pal['%s%d' % (name, i)] = v.lower()
    if void:
        pal['void'] = void.lower()
    return pal

def extract(image, n=16):
    im = np.array(Image.open(image).convert('RGBA')).reshape(-1, 4)
    px = im[im[:, 3] > 127][:, :3]
    lab = cl.rgb_to_oklab(px)
    # weight saturated colours up a little so small accents survive
    L, C, H = cl.lch_of(lab)
    # over-cluster, then keep n colours that are both common and distinct from each other,
    # so a dark sky cannot spend half the palette on near-identical blacks
    cand = cl.kmeans(lab, min(len(lab), n * 3), weights=1 + 3 * np.clip(C / 0.2, 0, 1))
    share = np.bincount(cl.nearest(lab[::7], cand), minlength=len(cand)).astype(float) + 1
    pick = [int(np.argmax(share))]
    while len(pick) < min(n, len(cand)):
        d = np.min(((cand[:, None, :] - cand[pick][None]) ** 2).sum(-1), 1) ** 0.5
        score = d * share ** 0.35
        score[pick] = -1
        pick.append(int(np.argmax(score)))
    return cl.sort_palette([cl.rgb_to_hex(c) for c in cl.oklab_to_rgb(cand[pick])])

def swatch(pal, path, cols=None):
    items = list(pal.items()) if isinstance(pal, dict) else [(None, h) for h in pal]
    n = len(items)
    cols = cols or min(n, 8)
    rows = (n + cols - 1) // cols
    cw, ch = 72, 56
    im = Image.new('RGB', (cols * cw, rows * ch), (24, 24, 28))
    d = ImageDraw.Draw(im)
    for i, (name, h) in enumerate(items):
        x, y = (i % cols) * cw, (i // cols) * ch
        d.rectangle([x + 2, y + 2, x + cw - 3, y + ch - 18], fill=cl.hex_to_rgb(h))
        d.text((x + 4, y + ch - 16), (name + ' ' if name else '') + h, fill=(220, 220, 220))
    im.save(path)

def write_all(pal, out, title='palette'):
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    hexes = cl.palette_list(pal)
    out.with_suffix('.hex').write_text('\n'.join(h.lstrip('#') for h in hexes) + '\n')
    gpl = ['GIMP Palette', 'Name: ' + title, 'Columns: 8', '#']
    names = list(pal.keys()) if isinstance(pal, dict) else [h for h in hexes]
    for name, h in zip(names, hexes):
        r, g, b = cl.hex_to_rgb(h)
        gpl.append('%3d %3d %3d\t%s' % (r, g, b, name))
    out.with_suffix('.gpl').write_text('\n'.join(gpl) + '\n')
    out.with_suffix('.json').write_text(json.dumps(pal if isinstance(pal, dict) else {'colors': hexes}, indent=1))
    strip = Image.new('RGB', (len(hexes), 1))
    strip.putdata([cl.hex_to_rgb(h) for h in hexes])
    strip.save(out.with_suffix('.png'))
    swatch(pal, out.parent / (out.name + '-swatch.png'))
    print('wrote %s.{hex,gpl,json,png} and %s-swatch.png (%d colours)' % (out, out.name, len(hexes)))

def style_sheet(path, bases=None, cell=36):
    """every ramp style on a few bases: one row per (style, base), labelled with its reference"""
    bases = bases or ['#553d30', '#486a9e', '#999996', '#654643', '#2a8e11', '#8f5f96']
    rows = [(st, b, ramp(b, style=st)) for st in RAMP_STYLES for b in bases]
    W = 150 + cell * max(len(r) for _, _, r in rows)
    im = Image.new('RGB', (W, len(rows) * (cell + 4) + 4), (24, 24, 28))
    d = ImageDraw.Draw(im)
    for j, (st, b, r) in enumerate(rows):
        y = 4 + j * (cell + 4)
        d.text((4, y + 4), st, fill=(230, 230, 230))
        d.text((4, y + 18), '%s  %s' % (b, RAMP_STYLES[st]['ref'][:14]), fill=(150, 150, 150))
        for i, h in enumerate(r):
            d.rectangle([150 + i * cell, y, 150 + (i + 1) * cell - 1, y + cell - 1], fill=cl.hex_to_rgb(h))
    im.save(path)

def main(a):
    def opt(name, default=None):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return v
        return default
    if not a:
        print(__doc__); return
    cmd = a.pop(0)
    out = opt('-o')
    if cmd == 'list':
        for p in sorted((cl.KIT / 'palettes').glob('*.hex')):
            print('%-24s %d colours' % (p.stem, len(cl.load_palette(str(p)))))
    elif cmd == 'extract':
        n = int(opt('-n', '16'))
        pal = extract(a[0], n)
        print(' '.join(pal))
        if out: write_all(pal, out, pathlib.Path(a[0]).stem)
    elif cmd in ('ramp', 'ramps'):
        st, sh = opt('--steps'), opt('--shift')
        steps, shift, style = (int(st) if st else None), (float(sh) if sh else None), opt('--style')
        if cmd == 'ramp':
            print(' '.join(ramp(a[0], steps, shift, style=style))); return
        pal = ramps(dict(spec.split('=') for spec in a), steps, shift, style=style)
        for k, v in pal.items():
            print(k, v)
        if out: write_all(pal, out, pathlib.Path(out).stem)
    elif cmd == 'styles':
        path = (out or 'ramp-styles') + '.png'
        style_sheet(path, a or None); print('wrote', path)
    elif cmd == 'between':
        print(' '.join(ramp_between(a[0], a[1], int(opt('--steps', '7')))))
    elif cmd == 'show':
        pal = cl.load_palette(a[0])
        path = (out or pathlib.Path(a[0]).stem) + '-swatch.png'
        swatch(pal, path); print('wrote', path)
    elif cmd == 'js':
        pal = cl.load_palette(a[0])
        key = opt('--name', 'phase')
        if not isinstance(pal, dict):
            pal = {'C%d' % i: h for i, h in enumerate(pal)}
        body = ', '.join("%s: '%s'" % (k, v) for k, v in pal.items())
        print('  %s: { %s },' % (key, body))
    elif cmd in ('grade', 'haze'):
        pal = cl.load_palette(a[0])
        if cmd == 'grade':
            stops = [h if h.startswith('#') else '#' + h for h in opt('--map').split(',')]
            keep, win, floor = opt('--keep'), opt('--window'), opt('--floor')
            res = grade(pal, stops, float(opt('--amount', '0.8')), mode=opt('--mode', 'lch'),
                        keep=tuple(keep.split(',')) if keep else (),
                        hue_window=tuple(float(v) for v in win.split(',')) if win else None,
                        floor_L=float(floor) if floor else None)
        else:
            res = haze(pal, opt('--fog'), float(opt('--amount', '0.8')), float(opt('--contrast', '0.4')),
                       float(opt('--lift', '0')), opt('--prefix', 'far_'))
        for k, v in (res.items() if isinstance(res, dict) else enumerate(res)):
            print(k, v)
        if out: write_all(res, out, pathlib.Path(out).stem)
    else:
        print(__doc__)

if __name__ == '__main__':
    main(sys.argv[1:])
