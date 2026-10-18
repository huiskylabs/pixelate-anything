/* Canyon Cycle sound sample: one short ambient phase (sunset into night) at 64 bpm. */
const SCENE = {
  name: 'Canyon Cycle sample',
  width: 160, height: 90,
  phases: [{ name: 'dusk', bpm: 64, palette: 'drift' }],
  bars: 4,
  cycle: 19,                             // 4 bars at 64 bpm plus the turnaround bar (check.py confirms)
  grand: 1,
  slots: ['BG0', 'BG1', 'B0', 'B1', 'B2', 'B3']
};
