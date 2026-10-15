/* ==========================================================================
   Hilltop Cabin: composition and the engine hooks.
   Rules that keep it looping and hand-made (see references/craft.md):
   - everything is a function of the tick k (30 Hz); no Math.random, no state
   - every animation period divides the picture loop (TICKS = 3600 here):
     k-periods like 30, 45, 60, 90, 120...; particle periods (15 Hz) divide 1800
   - motion is stepped: compute a slower clock (k / 3 = 10 fps, k / 15 = 2 fps)
   - only palette slots, never raw colours
   ========================================================================== */
const DUSK = 0, RAIN = 1;
const HORIZON = 84;                          // where the far hills begin

// sky gradients: [yStart, slot, dithered transition rows above this stop]
const SKY = [
  [[0, 'S0'], [20, 'S1', 14], [40, 'S2', 14], [58, 'S3', 14], [74, 'S4', 12]],
  [[0, 'S0'], [24, 'S1', 16], [46, 'S2', 16], [64, 'S3', 14], [78, 'S4', 10]]
];

// the hill: a hand-shaped crest; height in rows above the canvas bottom
function hillY(x) {
  const crest = 104 - 17 * Math.exp(-Math.pow((x - 140) / 58, 2));
  return Math.round(crest + 2 * Math.sin(x / 19) + (hash2(x >> 2, 5) < 0.2 ? 1 : 0));
}
function nearY(x) { return Math.round(118 + 9 * Math.exp(-Math.pow((x - 20) / 50, 2)) * -1 + 3 * Math.sin(x / 27 + 2)); }
function farY(x) { return Math.round(HORIZON + 4 * Math.sin(x / 31 + 1) + 2 * Math.sin(x / 13)); }
let HILL = null, NEAR = null;                // computed once: the shapes never move
function sceneInit() {
  HILL = new Int16Array(W); NEAR = new Int16Array(W);
  for (let x = 0; x < W; x++) { HILL[x] = hillY(x); NEAR[x] = nearY(x); }
}

/* ---------------- background ---------------- */
const STARS = [[14, 7], [31, 18], [47, 5], [66, 23], [84, 10], [104, 20], [121, 6], [141, 15], [160, 25],
  [177, 8], [194, 19], [211, 5], [227, 14], [54, 33], [97, 35], [185, 37], [222, 31], [22, 39]];
const CLOUDS = [                             // [y, start x, whole trips across per picture loop, span]
  [[16, 30, 2, 280], [36, 160, 3, 280]],
  [[6, 0, 2, 280], [17, 110, 3, 280], [29, 45, 4, 280], [44, 190, 3, 280], [56, 90, 4, 280]]
];
function cloudX(c, k) {
  const [, x0, trips, span] = c, w = SPR.cloud.w, total = span + w;
  const k2 = k >> 1;                         // 15 Hz steps
  const p = Math.floor(k2 * total * trips / (TICKS / 2));   // whole trips per loop: repeats exactly
  return (x0 + p) % total - w;
}
function sceneBack(si, k) {
  bands(BG, SKY[si], HORIZON + 8);
  if (si === DUSK) {
    const f10 = (k / 3) | 0;
    STARS.forEach(([x, y], i) => {
      const ph = (f10 + i * 13) % 50;        // 50 steps at 10 fps; 150 ticks divides 3600
      if (ph < 4) blit(BG, SPR.twinkle, x - 1, y - 1, ph < 2 ? 0 : 1);
      else if (y < 30) px(BG, x, y, SL.N1);
    });
    blit(BG, SPR.moon, 40, 20);
  }
  for (const c of CLOUDS[si]) blit(BG, SPR.cloud, cloudX(c, k), c[0]);
  // far hills, then the main hill with a lit rim and dithered depth
  for (let x = 0; x < W; x++) for (let y = farY(x); y < H; y++) BG[y * W + x] = SL.F0;
  for (let x = 0; x < W; x++) {
    const top = HILL[x];
    for (let y = top; y < H; y++) {
      const d = y - top;
      let s = d === 0 ? 'H3' : d < 4 ? 'H2' : d < 14 ? 'H1' : 'H0';
      if (d === 4 || d === 14) s = BAYER4[((y & 3) << 2) | (x & 3)] < 8 ? (d === 4 ? 'H2' : 'H1') : s;
      BG[y * W + x] = SL[s];
    }
    if (hash2(x, 9) < 0.18) px(BG, x, top - 1, SL.H2);     // grass tufts
  }
}

/* ---------------- objects ---------------- */
function sceneObjects(si, k) {
  blit(OB, SPR.pine, 118, HILL[118] + 1);
  blit(OB, SPR.cabin, 146, HILL[146] + 1);
  // a nearer, darker hill in front gives depth (drawn as objects so it covers the main hill)
  for (let x = 0; x < W; x++) for (let y = NEAR[x]; y < H; y++)
    OB[y * W + x] = SL[y === NEAR[x] ? 'H2' : (y - NEAR[x] < 5 && BAYER4[((y & 3) << 2) | (x & 3)] < 6 ? 'H1' : 'H0')];
}

/* ---------------- palette cycling: the window flickers like a fire inside ---------------- */
function sceneDynamic(si, k, D, P) {
  const f10 = (k / 3) | 0;
  const w = flick(f10, 3 + si, 4, si === RAIN ? 0.3 : 0.18, 0.06);
  D[SL.WL2] = P[w === 0 ? SL.Y3 : SL.Y2];
  D[SL.WL1] = P[w === 2 ? SL.Y1 : SL.Y2];
  D[SL.WL0] = P[SL.Y0];
}

/* ---------------- particles (after the phase dissolve; dens fades across transitions) ---------------- */
function sceneParticles(si, k, dens, out, D) {
  const k2 = k >> 1;                         // 15 Hz particle clock
  if (si === RAIN) {
    for (let j = 0; j < 140; j++) {
      if (hash2(j, 11) > dens) continue;
      const per = [20, 24, 30][j % 3];       // each divides TICKS / 2 = 1800
      const [age, gen] = pclock(k2, j, per, 13);
      const x0 = Math.floor(hash3(j, gen, 15) * (W + 40)) - 30;
      const yEnd = j % 4 ? HORIZON + Math.floor(hash3(j, gen, 17) * (H - HORIZON)) : H + 4;
      const y = -6 + Math.floor((yEnd + 6) * age / per);
      const x = x0 + Math.floor((y + 6) * 0.25);
      for (let i = 0; i < 3; i++) put(out, D, x + (i >> 1), y + i, j % 4 ? SL.N1 : SL.N0);
    }
  } else {
    // fireflies drift around hand-placed homes and blink slowly
    // the wander path has 12 steps at 2.5 fps: 72 ticks, which divides 3600
    const PATH = [[0, 0], [1, 0], [2, -1], [2, -2], [1, -3], [0, -3], [-1, -2], [-2, -2], [-2, -1], [-1, 0], [0, 1], [0, 0]];
    const HOMES = [[104, 92], [128, 86], [170, 84], [190, 92], [86, 100], [150, 96]];
    HOMES.forEach(([hx, hy], j) => {
      if (hash2(j, 21) > dens) return;
      const p = PATH[(((k2 / 6) | 0) + j * 5) % PATH.length];
      const x = hx + p[0] * (j % 2 ? 1 : -1), y = hy + p[1];
      const b = (((k2 / 3) | 0) + j * 7) % 20; // blink: 20 steps of 5 Hz = 120 ticks
      if (b < 4) put(out, D, x, y, b === 1 || b === 2 ? SL.Y3 : SL.Y2);
    });
  }
}
