/* Starter Scene Loop: music. One entry per phase (same order as config.js), plus the
   turnaround from each phase into the next. MIDI notes. See references/music.md. */
const PHASES = [
  // day: warm and open, guitar, D major 9 colours
  { name: 'day', swing: 0.18, lead: 'guitar', comp: 'guitar', amb: [['cicadas', 0.12], ['wind', 0.06]],
    chords: [[38, [50, 57, 61, 64, 66]], [47, [47, 54, 57, 62, 66]], [43, [43, 50, 54, 59, 62]], [45, [45, 52, 54, 61, 64]]],
    scale: [66, 69, 71, 73, 74, 76, 78, 81, 83], mel: 0.7,
    kick: [[0, 0.9], [3, 0.45], [8, 0.7], [10, 0.6]], snare: [[4, 0.55], [12, 0.6]], hats: 8, shaker: 0.5, snd: 'snare', ohat: 0.15 },
  // night: slower, felt piano and brushes, A minor 9
  { name: 'night', swing: 0.25, lead: 'piano', comp: 'piano', amb: [['wind', 0.12]],
    chords: [[45, [55, 59, 60, 64]], [41, [52, 57, 60, 65]], [38, [53, 57, 60, 64]], [40, [56, 59, 62, 64]]],
    scale: [64, 67, 69, 71, 72, 74, 76, 79, 81], mel: 0.65, alter: { 3: { 67: 68, 79: 80, 72: 71 } },
    kick: [[0, 0.85], [6, 0.45], [9, 0.7]], snare: [[4, 0.6], [12, 0.6]], hats: 8, shaker: 0, snd: 'brush' }
];
// turnaround into the NEXT phase's first chord: ii (pre), V (dom), chromatic bass approach
const TURNS = [
  { pre: [47, [53, 57, 59, 62]], dom: [40, [56, 59, 62, 65]], approach: 44 },  // day -> night: Bm7b5, E7b9 -> Am9
  { pre: [40, [55, 59, 62, 66]], dom: [45, [55, 59, 61, 66]], approach: 37 }   // night -> day: Em9, A13 -> Dmaj9
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS };
