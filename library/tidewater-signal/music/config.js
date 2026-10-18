/* Tidewater overworld cue: one chiptune phase at 132 bpm in A major (I-V-vi-IV).
   10 bars + 1 turnaround bar = 11 bars x 1.818 s = 20 s exactly, so the tempo is not scaled.
   The leitmotif lead is rendered separately (numpy 25% pulse) and mixed over this render. */
const SCENE = {
  name: 'Signal from Tidewater - Overworld',
  width: 160, height: 90,
  phases: [
    { name: 'overworld', bpm: 132 }      // chiptune
  ],
  bars: 10,
  cycle: 20,                             // check.py prints the right value if the tempo changes
  grand: 1,
  slots: ['BG0', 'BG1', 'B0', 'B1', 'B2', 'B3']
};
