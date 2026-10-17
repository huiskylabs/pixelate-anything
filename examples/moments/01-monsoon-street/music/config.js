/* Monsoon Street: the downpour phase alone, so the render stays short (one lofi phase). */
const SCENE = {
  name: 'Monsoon Street',
  width: 160, height: 90,
  phases: [
    { name: 'downpour', bpm: 66 }        // lofi, B minor
  ],
  bars: 8,
  cycle: 32.7,                           // check.py prints the right value
  grand: 1,
  slots: ['BG0', 'BG1', 'B0', 'B1', 'B2', 'B3']
};
