/* Pixel Radio: one chiptune phase and one ambient phase, with a ii-V hand-off each way.
   style: 'chiptune' -> pulse lead, 16th-note pulse arpeggio, triangle octave bass, noise drums.
   style: 'ambient'  -> pad with sparse voices on top, a drone bass, no drums.
   Anything a phase sets itself overrides the style's defaults (see guides/music.md). */
const PHASES = [
  { name: 'overworld', style: 'chiptune',
    chords: [[36, [55, 60, 64]], [43, [55, 59, 62]], [45, [57, 60, 64]], [41, [57, 60, 65]]],   // C G Am F
    scale: [72, 74, 76, 79, 81, 84, 86, 88], mel: 0.9 },
  { name: 'drift', style: 'ambient', lead: 'piano', padVoice: 'musicbox', amb: [['wind', 0.12]],
    chords: [[33, [52, 55, 59, 62]], [29, [53, 57, 60, 64]], [36, [52, 55, 59, 64]], [31, [50, 55, 59, 62]]],  // Am9 Fmaj7 Cmaj7 G6
    scale: [64, 67, 69, 71, 72, 74, 76, 79], mel: 0.45 }
];
const TURNS = [
  { pre: [47, [53, 57, 59, 62]], dom: [40, [56, 59, 62, 65]], approach: 44 },   // -> Am: Bm7b5, E7b9
  { pre: [38, [53, 57, 60, 64]], dom: [43, [53, 57, 59, 64]], approach: 35 }    // -> C: Dm9, G13
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS };
