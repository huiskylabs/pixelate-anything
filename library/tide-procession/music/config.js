/* Pixel Radio: a music-first template. Edit music.js; the picture is a simple equaliser.
   For standalone music (game loops, a soundtrack file) render with tools/render_audio.py. */
const SCENE = {
  name: 'Tide Procession',
  width: 160, height: 90,
  phases: [
    { name: 'tide', bpm: 60 }            // ambient, D Dorian
  ],
  bars: 8,
  cycle: 36,                             // 8 bars at 60 bpm plus the turnaround bar
  grand: 1,                              // the music repeats exactly every 36 s
  slots: ['BG0', 'BG1', 'B0', 'B1', 'B2', 'B3']
};
