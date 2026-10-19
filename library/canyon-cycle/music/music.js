/* Canyon Cycle: a dusky ambient phase in B-flat minor. A pad with music-box voices on top, a sub
   drone, no drums, a wind and fire bed. The thunder roll is mixed on top in Python (sound/). */
const PHASES = [
  { name: 'dusk', style: 'ambient', lead: 'musicbox', comp: 'pad', padVoice: 'musicbox',
    bass: 'bass', bassMode: 'drone', drums: false,
    amb: [['wind', 0.3], ['fire', 0.2]],
    chords: [[34, [53, 56, 60, 61]],     // Bbm9   (F Ab C Db over Bb)
             [30, [53, 58, 61, 66]],     // Gbmaj7 (F Bb Db Gb over Gb)
             [37, [53, 56, 60, 63]],     // Dbmaj9 (F Ab C Eb over Db)
             [41, [51, 56, 58, 60]]],    // Fm11   (Eb Ab Bb C over F)
    scale: [65, 68, 70, 72, 73, 75, 77, 80], mel: 0.75 }
];
const TURNS = [
  { pre: [36, [51, 54, 58, 60]], dom: [41, [51, 54, 57, 60]], approach: 33 }   // Cm7b5, F7b9 -> Bbm
];
const SCENE_MUSIC = { phases: PHASES, trans: TURNS };
