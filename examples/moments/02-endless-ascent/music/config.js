/* Endless Ascent, the trunk town: one short lofi phase for the 5 s sample (76 bpm, D major). */
const SCENE = {
  name: 'Endless Ascent - trunk town',
  width: 160, height: 90,
  phases: [
    { name: 'town', bpm: 76 }
  ],
  bars: 8,
  cycle: 28,                             // check.py prints the right value
  grand: 1,
  slots: ['BG0', 'BG1', 'B0', 'B1', 'B2', 'B3']
};
