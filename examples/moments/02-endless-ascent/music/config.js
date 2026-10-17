/* Endless Ascent, the trunk town: one short lofi phase for the 5 s sample (76 bpm, D major). */
const SCENE = {
  name: 'Endless Ascent - trunk town',
  width: 160, height: 90,
  phases: [
    { name: 'town', bpm: 76 }
  ],
  bars: 18,
  cycle: 60,                             // 19 bars at 76 bpm (18 + the turnaround) = 60 s exactly
  grand: 1,
  slots: ['BG0', 'BG1', 'B0', 'B1', 'B2', 'B3']
};
