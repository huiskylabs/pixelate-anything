/* Hilltop Cabin: a starter scene for pixel-loop. Copy this folder, then change everything. */
const SCENE = {
  name: 'Hilltop Cabin',
  width: 240, height: 135,               // 16:9; exports at 8x = 1920x1080 or 16x = 3840x2160
  phases: [                              // one entry per mood; each gets a palette and a music entry
    { name: 'dusk', bpm: 76 },
    { name: 'rain', bpm: 68 }
  ],
  bars: 8,                               // bars per phase (the 4-chord loop twice)
  cycle: 60,                             // seconds for one pass through all phases: keep it near the
                                         // natural length (check.py tells you the right number)
  grand: 2,                              // the picture loop = cycle x grand = 120 s = 3600 frames
  // every slot name used by palettes and sprites. Slots keep one meaning across phases.
  slots: ('S0 S1 S2 S3 S4 F0 H0 H1 H2 H3 K0 R1 R2 W0 W1 W2 Y0 Y1 Y2 Y3 T0 T1 T2 M0 M1 C0 C1 N0 N1 ' +
    'WL0 WL1 WL2').split(' '),
  dynamicSlots: ['WL0', 'WL1', 'WL2']    // window light: set every frame in sceneDynamic
};
