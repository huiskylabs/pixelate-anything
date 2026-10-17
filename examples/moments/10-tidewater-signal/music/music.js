/* Tidewater overworld: chiptune, A major, I-V-vi-IV (A - E - F#m - D), one chord per bar.
   style 'chiptune' gives the 16th-note pulse2 arpeggio comp, the triangle bass in octaves and
   the noise kit (ckick, csnare, chat). mel: 0 turns the engine's random melody off: the
   5-note leitmotif lead is written note by note in ../art/sound.py (25% pulse, 4-bit volume)
   and mixed over this render, so the motif is fixed and identical in every cue.
   Voicings stay at or under E4 so the arpeggio (+12) sits below the lead's F#5-E6 register. */
const PHASES = [
  { name: 'overworld', style: 'chiptune',
    chords: [[45, [57, 61, 64]],     // A    A3 C#4 E4
             [40, [56, 59, 64]],     // E    G#3 B3 E4
             [42, [54, 57, 61]],     // F#m  F#3 A3 C#4
             [38, [54, 57, 62]]],    // D    F#3 A3 D4
    scale: [76, 78, 80, 81, 83, 85, 86, 88], mel: 0 }
];
const TURNS = [
  { pre: [47, [50, 54, 57, 61]], dom: [40, [50, 54, 56, 61]], approach: 44 }   // -> A: Bm9, E13, G# approach
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS };
