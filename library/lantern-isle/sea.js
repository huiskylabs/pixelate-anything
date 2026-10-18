/* ==========================================================================
   Sea: swell glints, moon / sunset / aurora reflections, rain rings.
   ========================================================================== */
let GLINTS = null;
function glintInit() {
  GLINTS = [];
  let y = HORIZON + 1, row = 0;
  while (y < H - 1) {
    const d = (y - HORIZON) / (H - HORIZON);          // 0 far .. 1 near
    const gx = Math.round(14 + d * 46);
    let x = Math.floor(hash2(row, 3) * gx);
    while (x < W) {
      const j = GLINTS.length;
      const L = Math.max(1, Math.round(1 + d * 6 * (0.4 + hash2(j, 5) * 0.6)));
      GLINTS.push({ x, y, L, per: [24, 30, 36, 40, 45, 48][Math.floor(hash2(j, 7) * 6)],
        ph: Math.floor(hash2(j, 9) * 48), r: hash2(j, 11), d });
      x += Math.round(gx * (0.55 + hash2(j, 13) * 0.9));
    }
    y += Math.max(2, Math.round(2 + d * 5 + hash2(row, 17) * 2));
    row++;
  }
}
// visible life of a glint in 6 fps frames: length factor per frame
const GLINT_LIFE = [0.25, 0.6, 1, 1, 0.6, 0.25];
const SEA_GLINT = {
  spring: { dens: 0.32, far: 'C0', near: 'C0', hot: 'C1' },
  summer: { dens: 1.0, far: 'S6', near: 'C1', hot: 'Y2' },
  fall: { dens: 0.55, far: 'C0', near: 'C0', hot: 'M2' },
  winter: { dens: 0.45, far: 'C0', near: 'C0', hot: 'C1' }
};
// reflection columns under bright sky sources: [x center, half-width at horizon, half-width at bottom, slots]
const SKY_REFLECT = {
  fall: [[365, 6, 22, ['M1', 'M2', 'M3']]],
  summer: [[64, 2, 7, ['C0', 'C0', 'C1']]],
  spring: [[341, 4, 14, ['C0', 'C1', 'C1']]],
  winter: []
};

// long slow swell streaks, one tone lighter than the water around them
let SWELLS = null;
function swellInit() {
  SWELLS = [];
  let y = HORIZON + 3;
  while (y < H - 2) {
    const d = (y - HORIZON) / (H - HORIZON);
    const n = Math.round(3 + (1 - d) * 5);
    for (let j = 0; j < n; j++) {
      const len = Math.round(5 + d * 34 * (0.4 + hash3(y, j, 33)));
      SWELLS.push({ y, x: Math.floor(hash3(y, j, 31) * (W + len)), len, sp: hash3(y, j, 35) < 0.5 ? 1 : -1 });
    }
    y += Math.round(3 + d * 8 + hash2(y, 39) * 3);
  }
}
function seaSlotAt(stops, y) {
  let a = stops[0][1], prev = stops[0][1];
  for (const st of stops) { if (st[0] <= y) { prev = a; a = st[1]; } }
  return [SL[a], SL[prev]];
}
function drawSwells(si, k) {
  if (!SWELLS) swellInit();
  const stops = SEASONS[si].sea, k2 = k >> 1;
  for (const s of SWELLS) {
    const span = W + s.len;
    const shift = Math.floor(k2 * span / (TICKS / 2));      // one full pass per loop: repeats exactly
    const x = mod(s.x + s.sp * shift, span) - s.len;
    const [, lighter] = seaSlotAt(stops, s.y);
    hline(BG, x, x + s.len - 1, s.y, lighter);
  }
}
// far mist banks lie on the water behind the island (fall), drawn before objects
const FAR_MIST = { fall: [['mist_b', 164 + TY, 60, 1, 540]], spring: [['haze_wide', 160 + TY, 200, 1, 540]] };

function drawSeaFeatures(si, k) {
  if (!GLINTS) glintInit();
  drawSwells(si, k);
  const fm = FAR_MIST[SEASONS[si].key];
  if (fm) for (const m of fm) { const sp = SPR[m[0]]; if (sp) blit(BG, sp, cloudX(m, k), m[1]); }
  const S = SEASONS[si];
  const cfg = SEA_GLINT[S.key];
  const f6 = (k / 5) | 0;
  const far = SL[cfg.far], near = SL[cfg.near], hot = SL[cfg.hot];
  const cols = SKY_REFLECT[S.key];

  // swell glints
  for (let i = 0; i < GLINTS.length; i++) {
    const g = GLINTS[i];
    if (g.r > cfg.dens) continue;
    const t = (f6 + g.ph) % g.per;
    if (t >= GLINT_LIFE.length) continue;
    const len = Math.max(1, Math.round(g.L * GLINT_LIFE[t]));
    const drift = t >> 1;
    let slot = g.d < 0.18 ? far : near;
    for (const c of cols) {
      const hw = c[1] + (c[2] - c[1]) * g.d;
      if (Math.abs(g.x - c[0]) < hw * 1.6) slot = SL[c[3][1]];
    }
    if (si === SUMMER && g.d < 0.22 && g.r < 0.55) slot = g.r < 0.2 ? hot : SL.S6;
    const x0 = g.x + drift - (len >> 1);
    hline(BG, x0, x0 + len - 1, g.y, slot);
  }

  // shimmering columns under the moon / bright sky
  for (const c of cols) {
    const [cx, hw0, hw1, sl] = c;
    const fr = (f6 >> 1) % 4;
    for (let y = HORIZON + 1; y < H; y += 1) {
      const d = (y - HORIZON) / (H - HORIZON);
      if (hash3(y, fr, 501) > (si === SUMMER ? 0.3 : 0.62) - d * 0.25) continue;
      const hw = hw0 + (hw1 - hw0) * d;
      const off = Math.round((hash3(y, fr, 503) - 0.5) * hw * 1.6);
      const len = Math.max(1, Math.round(hw * (0.3 + hash3(y, fr, 507) * 0.7)));
      const lev = hash3(y, fr, 509);
      const slot = SL[sl[lev < 0.55 ? 0 : (lev < 0.88 ? 1 : 2)]];
      hline(BG, cx + off - (len >> 1), cx + off + (len >> 1), y, slot);
    }
  }

  // summer: the last light of the day sparkles in single bright pixels
  if (si === SUMMER) {
    for (let j = 0; j < 26; j++) {
      const per = [18, 24, 30, 36][j % 4];
      const t = (f6 + Math.floor(hash2(j, 701) * per)) % per;
      if (t > 1) continue;
      const gen = Math.floor((f6 + Math.floor(hash2(j, 701) * per)) / per);
      const x = Math.floor(hash3(j, gen % 97, 703) * W);
      const y = HORIZON + 1 + Math.floor(Math.pow(hash3(j, gen % 97, 705), 1.6) * 33);
      px(BG, x, y, t === 0 ? SL.Y3 : SL.Y2);
    }
  }
  // winter: the aurora lays a few faint green dashes on the water beneath it
  if (si === WINTER) {
    const fr = (f6 >> 2) % 4;
    for (let y = HORIZON + 2; y < HORIZON + 30; y += 2) {
      for (let x = 20; x < W - 20; x += 17) {
        const h = hash3(x + fr * 5, y, 611);
        if (h > 0.11) continue;
        const len = 2 + Math.floor(hash3(x, y, 613) * 4);
        hline(BG, x, x + len, y, h < 0.025 ? SL.U1 : SL.U0);
      }
    }
  }

  // spring rain rings on the open sea
  if (si === SPRING) drawRainRings(k);
}

function drawRainRings(k) {
  const N = 48;
  const k2 = k >> 1;
  for (let j = 0; j < N; j++) {
    const per = [18, 20, 24, 27, 30][j % 5];   // 15 Hz ticks, divides the loop
    const off = Math.floor(hash2(j, 801) * per);
    const t = k2 + off;
    const age = t % per;
    if (age > 5) continue;
    const gen = Math.floor(t / per) % (TICKS / 2 / per);
    const x = Math.floor(hash3(j, gen, 803) * W);
    const y = HORIZON + 6 + Math.floor(Math.pow(hash3(j, gen, 805), 0.8) * (H - HORIZON - 8));
    const near = y > HORIZON + 33;
    blit(BG, near ? SPR.ring_near : SPR.ring_far, x, y, age >> 1);
  }
}
