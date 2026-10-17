/* A 12-band equaliser drawn in pixels. Heights come from a hash of (band, step), so the
   picture is a pure function of the tick and loops with the music. Not audio-reactive:
   the page cannot analyse audio while exporting video, and this keeps both identical. */
function sceneBack(si, k) {
  bands(BG, [[0, 'BG0'], [60, 'BG1', 14]], H);
  const step = (k / 5) | 0;                              // 6 steps per second
  const fast = si === 0;
  for (let b = 0; b < 12; b++) {
    const x0 = 26 + b * 9;
    const r = hash2(b, fast ? step : (step >> 1));
    const base = fast ? 0.35 + 0.65 * r : 0.25 + 0.4 * r;
    const n = Math.max(1, Math.round(base * 12));
    for (let i = 0; i < n; i++) {
      const y = 70 - i * 4;
      const slot = i >= 10 ? 'B3' : i >= 7 ? 'B2' : i >= 3 ? 'B1' : 'B0';
      for (let dy = 0; dy < 3; dy++) hline(BG, x0, x0 + 6, y + dy, SL[slot]);
    }
  }
}
