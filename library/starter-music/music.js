/* Music Starter: two plain phases to replace, with a generic hand-off each way. No tune is written out:
   the engine builds melody phrases from `scale`, `mel` and the chords.
   style: 'chiptune' -> pulse lead, 16th-note pulse arpeggio, triangle octave bass, noise drums.
   style: 'ambient'  -> pad with sparse voices on top, a drone bass, no drums.
   Anything a phase sets itself overrides the style's defaults (see guides/music.md). */
const PHASES = [
  { name: 'part_a', style: 'chiptune',
    chords: [[36, [55, 60, 64]], [43, [55, 59, 62]], [45, [57, 60, 64]], [41, [57, 60, 65]]],
    scale: [72, 74, 76, 79, 81], mel: 0.5 },
  { name: 'part_b', style: 'ambient', amb: [['wind', 0.12]],
    chords: [[33, [52, 55, 59, 62]], [29, [53, 57, 60, 64]], [36, [52, 55, 59, 64]], [31, [50, 55, 59, 62]]],
    scale: [64, 67, 69, 71, 72], mel: 0.2 }
];
const TURNS = [
  { pre: [47, [53, 57, 59, 62]], dom: [40, [56, 59, 62, 65]], approach: 44 },   // part_a -> part_b
  { pre: [38, [53, 57, 60, 64]], dom: [43, [53, 57, 59, 64]], approach: 35 }    // part_b -> part_a
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS };
