/* ==========================================================================
   Lantern Isle: scene configuration (loaded first, before the engine).
   ========================================================================== */
const SCENE = {
  name: 'Lantern Isle',
  width: 480, height: 270,               // native canvas; exported at 4x (1080p) and 8x (4K)
  // one phase per season; bpm is each phase's tempo (scaled a hair to fit the cycle)
  phases: [
    { name: 'spring', bpm: 72 },
    { name: 'summer', bpm: 78 },
    { name: 'fall', bpm: 70 },
    { name: 'winter', bpm: 66 }
  ],
  bars: 8,                               // each phase plays its 4-chord loop twice
  cycle: 120,                            // seconds for all four phases
  grand: 3,                              // slow drifts loop over 3 cycles: the picture repeats every 360 s
  paletteFallback: 'summer',
  // every palette slot name, in any order. S sky, E sea, K darks, C cool light, Y warm light,
  // G ground, R rock, B wood, H walls, F roof, L foliage, P pine, N pale/snow, A accents,
  // M moon, U aurora, RF reflections; WL/LN are window and lantern light, set per frame.
  slots: ('S0 S1 S2 S3 S4 S5 S6 E0 E1 E2 E3 E4 K0 K1 K2 C0 C1 C2 Y0 Y1 Y2 Y3 ' +
    'G0 G1 G2 G3 R0 R1 R2 R3 B0 B1 B2 B3 H0 H1 H2 H3 F0 F1 F2 F3 L0 L1 L2 L3 L4 P0 P1 P2 P3 ' +
    'N0 N1 N2 N3 A0 A1 A2 A3 A4 A5 M0 M1 M2 M3 U0 U1 U2 RF0 RF1 RF2 ' +
    'WL0 WL1 WL2 WL3 LN0 LN1 LN2 LN3').split(' '),
  dynamicSlots: 'WL0 WL1 WL2 WL3 LN0 LN1 LN2 LN3'.split(' ')
};
