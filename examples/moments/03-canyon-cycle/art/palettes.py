"""Canyon Cycle: the slot map and the mood palettes.

One index map, many palettes. A slot is either STATIC (one colour per mood), SWITCHED (rain and the
bolt: equal to the colour under it when off), FLICKER (forge, spill, lantern: remapped per frame by
flick()), or belongs to exactly one cycling RANGE (falls, river reaches, stars). Ranges never share
a slot. A moment = a mood + the phase of every range + the flash/rain switches + the flick state.
"""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import palette as P

RANGES = {          # name: (slots, fps, direction in the picture)
    'WA': (['WA%d' % i for i in range(6)], 10.0, 'left fall, streaks move down'),
    'WB': (['WB%d' % i for i in range(6)], 10.0, 'right fall, streaks move down'),
    'RA': (['RA%d' % i for i in range(5)], 5.0, 'far river reach, glints travel left'),
    'RB': (['RB%d' % i for i in range(5)], 7.5, 'near river reach, glints travel right'),
    'T': (['T%d' % i for i in range(3)], 2.0, 'stars, twinkle on a hold table'),
}
FLICKER = {'F': ['F0', 'F1', 'F2', 'F3'], 'FR': ['FR0', 'FR1'], 'L': ['L0', 'L1', 'L2']}
FLASH = ['C0', 'C1', 'C2', 'C3', 'M0', 'M1', 'M2', 'M3']
RAIN = {'RS3': 'S3', 'RC0': 'C0', 'RM0': 'M0', 'RM1': 'M1'}     # rain slot: the slot it lies on
STATIC = (['S%d' % i for i in range(6)] + FLASH + ['K0'] + ['R%d' % i for i in range(5)] +
          ['H0', 'H1', 'H2', 'G0', 'G1', 'G2', 'B0', 'B1', 'B2', 'B3', 'I0', 'I1', 'N0', 'N1',
           'V0', 'V1', 'V2', 'Q0'])

SLOTS = (['S%d' % i for i in range(6)] + RANGES['T'][0] + ['C0', 'C1', 'C2', 'C3', 'BL'] +
         ['M0', 'M1', 'M2', 'M3'] + list(RAIN) + ['K0'] + ['R%d' % i for i in range(5)] +
         ['H0', 'H1', 'H2', 'G0', 'G1', 'G2', 'B0', 'B1', 'B2', 'B3', 'I0', 'I1'] +
         FLICKER['F'] + FLICKER['FR'] + FLICKER['L'] + RANGES['WA'][0] + RANGES['WB'][0] +
         ['N0', 'N1', 'V0', 'V1', 'V2', 'Q0'] + RANGES['RA'][0] + RANGES['RB'][0])
INDEX = {s: i for i, s in enumerate(SLOTS)}
assert len(SLOTS) == len(set(SLOTS))

# ---------------------------------------------------------------- moods, by role (OKLCh: L, C, hue)
SUNSET = dict(
    # sky: violet zenith to peach horizon
    S0=(.29, .065, 298), S1=(.34, .075, 312), S2=(.39, .085, 328), S3=(.44, .095, 346),
    S4=(.49, .100, 8), S5=(.55, .100, 32),
    # storm bank: dark belly, rose-lit crown
    C0=(.27, .045, 300), C1=(.33, .055, 310), C2=(.42, .075, 340), C3=(.51, .090, 15),
    # far mesa, hazed
    M0=(.34, .050, 318), M1=(.39, .060, 335), M2=(.45, .075, 355), M3=(.51, .085, 18),
    # near rock: outline, shadow, half-lit, rose face, sun lip
    K0=(.14, .035, 288), R0=(.17, .045, 285), R1=(.22, .050, 295), R2=(.29, .060, 318),
    R3=(.38, .085, 350), R4=(.48, .100, 20),
    H0=(.31, .050, 315), H1=(.36, .060, 330), H2=(.42, .070, 350),
    G0=(.24, .035, 150), G1=(.31, .045, 135), G2=(.39, .055, 115),
    B0=(.19, .035, 330), B1=(.26, .045, 15), B2=(.34, .055, 40), B3=(.43, .065, 55),
    I0=(.17, .020, 280), I1=(.30, .025, 260),
    N0=(.50, .040, 320), N1=(.62, .040, 340),
    V0=(.21, .050, 300), V1=(.28, .060, 315), V2=(.37, .080, 340), Q0=(.17, .040, 295),
)
SUNSET_RAMPS = dict(
    WA=[(.32, .050, 292), (.38, .055, 300), (.45, .060, 308), (.54, .060, 316), (.66, .050, 322), (.41, .055, 304)],
    WB=[(.40, .060, 330), (.47, .070, 342), (.54, .080, 355), (.61, .080, 12), (.68, .070, 30), (.50, .070, 348)],
    RA=[(.28, .060, 315), (.33, .070, 328), (.41, .085, 345), (.52, .095, 12), (.33, .070, 328)],
    RB=[(.21, .050, 300), (.25, .055, 310), (.32, .065, 328), (.42, .080, 348), (.25, .055, 310)],
    T=None,                                   # stars off: they take the sky under them (S0)
    F=[(.44, .150, 33), (.62, .170, 52), (.78, .140, 72), (.91, .080, 95)],
    FR=[(.40, .110, 42), (.54, .140, 55)],
    L=[(.48, .120, 48), (.73, .140, 72), (.90, .070, 95)],
    BL=(.86, .040, 295),
)
NIGHT = dict(
    S0=(.17, .060, 278), S1=(.20, .065, 276), S2=(.23, .070, 274), S3=(.26, .075, 272),
    S4=(.30, .078, 268), S5=(.34, .078, 262),
    C0=(.16, .045, 282), C1=(.19, .050, 280), C2=(.22, .055, 278), C3=(.26, .055, 272),
    M0=(.18, .045, 285), M1=(.21, .050, 283), M2=(.24, .055, 280), M3=(.27, .055, 276),
    K0=(.13, .035, 285), R0=(.155, .040, 285), R1=(.18, .045, 283), R2=(.21, .050, 280),
    R3=(.245, .055, 278), R4=(.28, .055, 276),
    H0=(.19, .045, 280), H1=(.22, .050, 278), H2=(.25, .055, 276),
    G0=(.17, .035, 228), G1=(.21, .040, 224), G2=(.25, .045, 220),
    B0=(.14, .035, 300), B1=(.18, .040, 318), B2=(.22, .045, 335), B3=(.27, .050, 345),
    I0=(.13, .025, 280), I1=(.24, .030, 270),
    N0=(.40, .045, 228), N1=(.49, .050, 218),
    V0=(.16, .045, 275), V1=(.19, .050, 272), V2=(.22, .055, 268), Q0=(.135, .035, 280),
)
NIGHT_RAMPS = dict(
    WA=[(.30, .055, 238), (.34, .060, 233), (.38, .065, 226), (.43, .070, 218), (.51, .068, 208), (.36, .060, 230)],
    WB=[(.33, .055, 236), (.37, .060, 230), (.42, .065, 222), (.48, .070, 214), (.57, .065, 204), (.39, .060, 228)],
    RA=[(.19, .050, 272), (.23, .055, 260), (.29, .060, 242), (.38, .065, 222), (.23, .055, 260)],
    RB=[(.16, .045, 275), (.19, .050, 265), (.245, .055, 246), (.33, .060, 226), (.19, .050, 265)],
    T=[(.55, .030, 265), (.72, .030, 255), (.88, .035, 95)],
    F=[(.44, .150, 33), (.62, .170, 52), (.78, .140, 72), (.91, .080, 95)],
    FR=[(.40, .110, 42), (.56, .140, 55)],
    L=[(.48, .120, 48), (.73, .140, 72), (.90, .070, 95)],
    BL=None,                                  # bolt off: the sky under it (S3)
)
MOODS = {'sunset': (SUNSET, SUNSET_RAMPS), 'night': (NIGHT, NIGHT_RAMPS)}


def hx(lch):
    return P.from_lch(*lch)


def moment(mood, t=None, flash=None, rain=False, flick=0):
    """{slot: '#hex'} for one instant. t: {range: step} (default 0); flash: None or dict(colour,
    amount, lift) for palette.flash on the storm and mesa slots (and the bolt on); rain: rain slots
    on; flick: 0 full, 1 dim, 2 deep (the flick() states, applied to F, FR and L)."""
    base, ramps = MOODS[mood]
    t = t or {}
    pal = {s: hx(v) for s, v in base.items()}
    for name, (slots, fps, _) in RANGES.items():
        ramp = ramps.get(name)
        n = len(slots)
        for i, s in enumerate(slots):
            pal[s] = hx(ramp[(i - t.get(name, 0)) % n]) if ramp else pal['S0']
    for name, slots in FLICKER.items():
        ramp = [hx(v) for v in ramps[name]]
        for i, s in enumerate(slots):
            pal[s] = ramp[max(0, i - flick)] if flick else ramp[i]
    if flash:
        lifted = P.flash({s: pal[s] for s in FLASH}, **flash)
        pal.update(lifted)
    pal['BL'] = hx(ramps['BL']) if (flash and ramps.get('BL')) else pal['S3']
    for r, under in RAIN.items():
        pal[r] = pal[under]                   # off: invisible on the slot it lies on
        if rain:
            L, C, h = P.lch(pal[under])
            pal[r] = P.from_lch(min(.95, L + .07), C * .6, h)
    missing = [s for s in SLOTS if s not in pal]
    assert not missing, missing
    return {s: pal[s] for s in SLOTS}


SUNSET_FLASH = dict(colour='#e0d8ff', amount=0.5, lift=0.2)
A_MOMENT = dict(mood='sunset', t={'WA': 3, 'WB': 3, 'RA': 2, 'RB': 1}, flash=SUNSET_FLASH, rain=False, flick=0)
B_MOMENT = dict(mood='night', t={'WA': 1, 'WB': 4, 'RA': 0, 'RB': 3, 'T': 1}, flash=None, rain=False, flick=0)
