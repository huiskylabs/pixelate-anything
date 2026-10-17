/* Monsoon Street, the downpour: felt piano lead and comp in B minor at 66 bpm, brushes, sparse
   hats, a heavy rain bed. Close rootless voicings (3-5-7-9) between 47 and 69:
   Bm9 (D F# A C#) - Gmaj9 (B D F# A) - Em9 (D F# G B) - F#7b9 (E G A# C#). */
const PHASES = [
  { name: 'downpour', swing: 0.2,
    lead: 'piano', comp: 'piano', bass: 'bass', drums: true, snd: 'brush',
    amb: [['rain', 0.5]],
    chords: [[35, [50, 54, 57, 61]], [31, [47, 50, 54, 57]], [40, [50, 54, 55, 59]], [42, [52, 55, 58, 61]]],
    scale: [66, 69, 71, 73, 74, 76, 78, 81],
    alter: { 3: { 69: 70, 81: 82 } },                // A -> A# over F#7b9
    mel: 0.7,
    kick: [[0, 0.75], [7, 0.35], [10, 0.5]],
    snare: [[4, 0.5], [12, 0.55]],
    hats: 8, shaker: 0, ohat: 0 }
];
const TURNS = [
  { pre: [37, [52, 55, 59, 62]], dom: [42, [52, 55, 58, 61]], approach: 34 }   // -> Bm: C#m7b5, F#7b9, A#
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS, texture: { vinyl: 0.25, tape: true } };
