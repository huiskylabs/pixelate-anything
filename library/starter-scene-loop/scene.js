/* ==========================================================================
   Starter Scene Loop: a neutral sky-and-ground scaffold and the engine hooks.
   Rules that keep it looping and hand-made (see references/drawing.md):
   - everything is a function of the tick k (30 Hz); no Math.random, no state
   - every animation period divides the picture loop (TICKS = 3600 here):
     k-periods like 30, 45, 60, 90, 120...; particle periods (15 Hz) divide 1800
   - motion is stepped: compute a slower clock (k / 3 = 10 fps, k / 15 = 2 fps)
   - only palette slots, never raw colours
   Everything below is a placeholder: a sky, a flat ground, one marker box,
   a foreground strip, one drifting block, a cycled colour and a few motes. Draw your own subject over it.
   ========================================================================== */
const DAY = 0, NIGHT = 1;
// where the ground begins: the `horizon` knob (piece.json), 80, 84 or 88; the build puts it in
// PIXELATE_KNOBS (`pixelate render . --set horizon=88`)
const HORIZON = PIXELATE_KNOBS.horizon;

// sky gradients: [first row, slot, dithered transition rows above this stop]
const SKY = [
  [[0, 'S0'], [30, 'S1', 14], [58, 'S2', 14]],
  [[0, 'S0'], [30, 'S1', 14], [58, 'S2', 14]]
];

/* ---------------- background ---------------- */
// [y, first x, whole trips across per picture loop, span]
const DRIFT = [[24, 40, 2, 280], [46, 170, 3, 280]];
function driftX(c, k) {
  const [, x0, trips, span] = c, w = SPR.block.w, total = span + w;
  const k2 = k >> 1;                         // 15 Hz steps
  const p = Math.floor(k2 * total * trips / (TICKS / 2));   // whole trips per loop: repeats exactly
  return (x0 + p) % total - w;
}
function sceneBack(si, k) {
  bands(BG, SKY[si], HORIZON + 8);
  for (const c of DRIFT) blit(BG, SPR.block, driftX(c, k), c[0]);
  // flat ground: an edge line, a mid tone and a deep tone with a dithered step between them
  for (let x = 0; x < W; x++) {
    for (let y = HORIZON; y < H; y++) {
      const d = y - HORIZON;
      let s = d === 0 ? 'G0' : d < 10 ? 'G1' : 'G2';
      if (d === 10) s = BAYER4[((y & 3) << 2) | (x & 3)] < 8 ? 'G1' : 'G2';
      BG[y * W + x] = SL[s];
    }
  }
}

/* ---------------- objects ---------------- */
const FOREGROUND = 117;                      // top row of the flat foreground strip
function sceneObjects(si, k) {
  blit(OB, SPR.marker, 120, HORIZON + 24);
  // a flat foreground strip with a lit edge keeps the bottom of the frame in use
  for (let x = 0; x < W; x++) for (let y = FOREGROUND; y < H; y++) OB[y * W + x] = SL[y === FOREGROUND ? 'F1' : 'F0'];
}

/* ---------------- palette cycling: the marker's centre pulses ---------------- */
function sceneDynamic(si, k, D, P) {
  const f10 = (k / 3) | 0;
  D[SL.MK] = P[(f10 % 20) < 10 ? SL.P1 : SL.B1];
}

/* ---------------- particles (after the phase dissolve; dens fades across transitions) ---------------- */
function sceneParticles(si, k, dens, out, D) {
  if (si !== NIGHT) return;
  const k2 = k >> 1;                         // 15 Hz particle clock
  for (let j = 0; j < 24; j++) {
    if (hash2(j, 11) > dens) continue;
    const per = [30, 36, 45][j % 3];         // each divides TICKS / 2 = 1800
    const [age] = pclock(k2, j, per, 13);
    const x = Math.floor(hash2(j, 15) * W);
    const y = HORIZON - Math.floor(HORIZON * age / per);
    put(out, D, x, y, SL.N0);
  }
}
