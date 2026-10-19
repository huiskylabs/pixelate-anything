/* ==========================================================================
   Lantern Isle: music. One entry per phase, plus the turnaround into the next.
   MIDI note numbers. chords: [bass, [voicing]] x 4 (looped through the phase).
   lead/comp: rhodes | guitar | piano | musicbox ; comp may also be pad.
   amb: [[rain|waves|cicadas|wind|leaves|fire, level], ...]
   kick/snare: [[16th step, velocity], ...]; snd: snare | brush | rim
   hats: 0 | 8 | 16 ; shaker: level (0 off); ohat: chance of an open hat; shakerStep: 1 | 2
   mel: chance of a melody phrase; scale: notes the melody may use;
   alter: { chordIndex: { from: to } } bends melody notes over one chord.
   ========================================================================== */
const PHASES = [
  { name: 'spring', swing: 0.22, lead: 'rhodes', comp: 'rhodes', amb: [['rain', 0.55], ['waves', 0.16]],
    chords: [[41, [57, 60, 64, 67]], [40, [55, 59, 62, 64]], [38, [53, 57, 60, 64]], [36, [52, 55, 59, 62]]],
    scale: [64, 67, 69, 72, 74, 76, 79, 81, 84], mel: 0.7,
    kick: [[0, 0.9], [7, 0.5], [10, 0.75]], snare: [[4, 0.55], [12, 0.6]], hats: 16, shaker: 0, snd: 'snare' },
  { name: 'summer', swing: 0.18, lead: 'guitar', comp: 'guitar', amb: [['cicadas', 0.16], ['waves', 0.42]],
    chords: [[38, [50, 57, 61, 64, 66]], [47, [47, 54, 57, 62, 66]], [43, [43, 50, 54, 59, 62]], [45, [45, 52, 54, 61, 64]]],
    scale: [66, 69, 71, 73, 74, 76, 78, 81, 83], mel: 0.7,
    kick: [[0, 0.9], [3, 0.45], [8, 0.7], [10, 0.6]], snare: [[4, 0.55], [12, 0.6]], hats: 8, shaker: 0.55, snd: 'snare', ohat: 0.18 },
  { name: 'fall', swing: 0.25, lead: 'piano', comp: 'piano', amb: [['wind', 0.3], ['leaves', 0.22], ['waves', 0.14]],
    chords: [[45, [55, 59, 60, 64]], [41, [52, 57, 60, 65]], [38, [53, 57, 60, 64]], [40, [56, 59, 62, 64]]],
    scale: [64, 67, 69, 71, 72, 74, 76, 79, 81], mel: 0.65, alter: { 3: { 67: 68, 79: 80, 72: 71 } },
    kick: [[0, 0.85], [6, 0.45], [9, 0.7]], snare: [[4, 0.6], [12, 0.6]], hats: 8, shaker: 0, snd: 'brush' },
  { name: 'winter', swing: 0.2, lead: 'musicbox', comp: 'pad', amb: [['fire', 0.55], ['wind', 0.1], ['waves', 0.08]],
    chords: [[36, [55, 59, 60, 64]], [45, [55, 57, 60, 64]], [41, [53, 57, 60, 64]], [43, [55, 59, 62, 64]]],
    scale: [72, 74, 76, 79, 81, 84, 86, 88], mel: 0.75,
    kick: [[0, 0.6], [10, 0.4]], snare: [[12, 0.45]], hats: 0, shaker: 0.35, shakerStep: 2, snd: 'rim' }
];

// DJ-style hand-off: while the tempo ramps into the next phase, a ii-V of the next
// phase's first chord carries the harmony, and a chromatic bass step lands on it.
const TURNS = [
  { pre: [40, [55, 59, 62, 66]], dom: [45, [55, 59, 61, 66]], approach: 37 },  // Em9  -> A13    -> Dmaj9
  { pre: [47, [53, 57, 59, 62]], dom: [40, [56, 59, 62, 65]], approach: 44 },  // Bm7b5 -> E7b9  -> Am9
  { pre: [38, [53, 57, 60, 64]], dom: [43, [53, 57, 59, 64]], approach: 35 },  // Dm9  -> G13    -> Cmaj7
  { pre: [43, [53, 57, 58, 62]], dom: [36, [52, 57, 58, 62]], approach: 40 }   // Gm9  -> C13    -> Fmaj7
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS };
