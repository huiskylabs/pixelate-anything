/* Starter: Scene Loop: a neutral looping scene to copy. Copy this folder, then change everything. */
const SCENE = {
  name: 'Starter Scene Loop',
  width: 240, height: 135,               // 16:9; exports at 8x = 1920x1080 or 16x = 3840x2160
  phases: [                              // one entry per mood; each gets a palette and a music entry
    { name: 'day', bpm: 76 },
    { name: 'night', bpm: 68 }
  ],
  bars: 8,                               // bars per phase (the 4-chord loop twice)
  cycle: 60,                             // seconds for one pass through all phases: keep it near the
                                         // natural length (check.py tells you the right number)
  grand: 2,                              // the picture loop = cycle x grand = 120 s = 3600 frames
  // every slot name used by palettes and sprites. Slots keep one meaning across phases.
  slots: 'S0 S1 S2 G0 G1 G2 F0 F1 K0 P0 P1 B0 B1 N0 MK'.split(' '),
  dynamicSlots: ['MK']                   // palette-cycled: set every frame in sceneDynamic
};
