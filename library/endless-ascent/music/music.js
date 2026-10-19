/* Endless Ascent, the trunk town at dusk: plucked guitar lead over a Rhodes comp, swung drums with a
   light snare, a leaves-and-wind bed. Dmaj9 - Bm9 - Gmaj9 - A13, close voiced between 47 and 69,
   never doubling the bass. The turnaround walks Em9 - A13 back into Dmaj9. */
const PHASES = [
  { name: 'town', style: '', swing: 0.22,
    lead: 'guitar', comp: 'rhodes', bass: 'bass', bassMode: '',
    drums: true,
    amb: [['leaves', 0.22], ['wind', 0.10]],
    chords: [[38, [54, 57, 61, 64]],      // Dmaj9: F# A C# E over D
             [35, [50, 54, 57, 61]],      // Bm9:   D F# A C# over B
             [31, [54, 57, 59, 62]],      // Gmaj9: F# A B D over G
             [33, [55, 59, 61, 66]]],     // A13:   G B C# F# over A
    scale: [66, 69, 71, 73, 74, 76, 78, 81],
    mel: 0.8,
    kick: [[0, 0.8], [7, 0.4], [10, 0.6]],
    snare: [[4, 0.42], [12, 0.45]],
    snd: 'snare',
    hats: 8, shaker: 0.08, shakerStep: 2, ohat: 0.15 }
];
const TURNS = [
  { pre: [40, [50, 54, 55, 59]], dom: [45, [55, 59, 61, 66]], approach: 37 }   // -> Dmaj9: Em9, A13, C# approach
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS, texture: { vinyl: 0.3, tape: true } };
