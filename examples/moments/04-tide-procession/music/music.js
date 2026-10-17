/* Tide Procession: one slow ambient phase in D Dorian at 60 bpm.
   A sub drone, a slow pad (Dm9 - G13 - Dm11 - Em7/D: the B natural is the Dorian colour), a wave
   bed, sparse music-box notes on top, no drums. The struck bronze bell is not an engine voice: it
   is synthesised in sound/bell.py and mixed over the render (sound/make_sample.py). */
const PHASES = [
  { name: 'tide', style: 'ambient', lead: 'musicbox', comp: 'pad', padVoice: 'musicbox',
    bassMode: 'drone', drums: false, amb: [['waves', 0.4]],
    chords: [[38, [53, 57, 60, 64]],      // Dm9   (D) F A C E
             [43, [53, 57, 59, 64]],      // G13   (G) F A B E
             [38, [53, 55, 60, 64]],      // Dm11  (D) F G C E
             [38, [55, 59, 62, 64]]],     // Em7/D (D) G B D E
    scale: [62, 64, 65, 67, 69, 71, 72, 74, 76], mel: 0.35 }
];
const TURNS = [
  { pre: [43, [53, 57, 59, 64]], dom: [45, [55, 60, 64, 67]], approach: 40 }    // -> Dm: G13, Am7, E
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS };
