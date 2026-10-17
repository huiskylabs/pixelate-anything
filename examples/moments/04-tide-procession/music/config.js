/* Pixel Radio: a music-first template. Edit music.js; the picture is a simple equaliser.
   For standalone music (game loops, a soundtrack file) render with tools/render_audio.py. */
const SCENE = {
  name: 'Tide Procession',
  width: 160, height: 90,
  phases: [
    { name: 'tide', bpm: 60 }            // ambient, D Dorian
  ],
  bars: 8,
  cycle: 48,                             // check.py prints the right value if the tempos change
  grand: 1,                              // the music repeats exactly every 48 s
  slots: ['BG0', 'BG1', 'B0', 'B1', 'B2', 'B3']
};
