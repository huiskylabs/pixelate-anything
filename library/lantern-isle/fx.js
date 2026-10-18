/* ==========================================================================
   Reflections, light on the water, low mist, and weather particles.
   ========================================================================== */
const WOB = [0, 0, 1, 1, 1, 0, 0, -1, -1, -1, 0, 0, 1, 0, 0, -1, -1, 0, 1, 1, 0, -1, 0, 0];   // length divides the cycle
const BRIGHT = new Uint8Array(NSLOT);
'WL0 WL1 WL2 WL3 LN0 LN1 LN2 LN3 Y0 Y1 Y2 Y3 N0 N1 N2 N3 M1 M2 M3'.split(' ').forEach(n => { BRIGHT[SL[n]] = 1; });

function drawReflections(si, k) {
  const R = SEASONS[si].refl;
  const f6 = (k / 5) | 0;
  const fr = f6 >> 1;
  for (let yd = AXIS; yd < H; yd++) {
    const r = yd - AXIS;
    const ys = AXIS - 1 - r;
    if (ys < 0) break;
    if (r > 2 && (yd + fr) % 6 === 0) continue;          // moving ripple gaps
    const amp = r < 3 ? 0 : (r < 16 ? 1 : (r < 60 ? 2 : 3));
    const off = amp ? WOB[(yd * 5 + fr) % WOB.length] * amp : 0;
    const srow = ys * W, drow = yd * W;
    const fade = r > 26 ? Math.min(16, (r - 26) >> 2) : 0;
    for (let x = 0; x < W; x++) {
      const sx = x - off;
      if (sx < 0 || sx >= W) continue;
      const v = OB[srow + sx];
      if (!v) continue;
      const m = R[v];
      if (!m) continue;
      if (fade && !BRIGHT[m] && BAYER4[((yd & 3) << 2) | (x & 3)] < fade) continue;
      if (r > 110 && !BRIGHT[m]) continue;
      BG[drow + x] = m;
    }
  }
  drawLightPaths(si, k);
}

// warm light laid on the water under windows and the lantern
const LIGHT_PATHS = [
  // x, half width, strength, slot family ('WL' windows, 'LN' lantern)
  [226, 3, 0.8, 'WL'], [269, 3, 0.8, 'WL'], [248, 2, 0.55, 'WL'], [354, 2, 0.9, 'LN']
];
function drawLightPaths(si, k) {
  const f6 = (k / 5) | 0;
  const fr = f6 % 4;
  const strong = si === WINTER ? 1.15 : 1;
  for (let p = 0; p < LIGHT_PATHS.length; p++) {
    const [cx, hw, st, fam] = LIGHT_PATHS[p];
    const s2 = SL[fam + '2'], s1 = SL[fam + '1'], s0 = SL[fam + '0'];
    for (let y = AXIS + 1; y < H; y++) {
      const d = (y - AXIS) / (H - AXIS);
      const h = hash3(y, fr * 7 + p, 1201);
      if (h > (0.7 - d * 0.32) * st * strong) continue;
      const w = Math.max(1, Math.round(hw * (0.6 + d * 1.6) * (0.5 + hash3(y, fr, 1203))));
      const off = Math.round((hash3(y, fr + p, 1205) - 0.5) * (2 + d * 6));
      const lev = hash3(y, fr, 1207) + d * 0.5;
      const slot = lev < 0.45 ? s2 : (lev < 1.0 ? s1 : s0);
      hline(BG, cx + TX + off - (w >> 1), cx + TX + off + ((w - 1) >> 1), y, slot);
    }
  }
}

/* ---------------- front layer: low mist ---------------- */
// low mist drifting over the near water, in front of the island's foot
const MISTS = {
  fall: [['mist_a', 203 + TY, 0, 2, 520], ['mist_c', 214 + TY, 300, 3, 520]],
  spring: [['haze_wide', 209 + TY, 120, 1, 540]]
};
function drawFront(si, k) {
  const list = MISTS[SEASONS[si].key];
  if (!list) return;
  for (const m of list) {
    const sp = SPR[m[0]];
    if (!sp) continue;
    blit(IX, sp, cloudX(m, k), m[1]);
  }
}

/* ---------------- particles (drawn after the season dissolve) ---------------- */
const SWAY = [0, 0, 1, 1, 2, 2, 2, 1, 1, 0, 0, -1, -1, -2, -2, -2, -1, -1];

function drawParticles(si, k, dens, out, D) {
  if (dens <= 0.001) return;
  const k2 = k >> 1;
  frameSpace();
  if (si === SPRING) rain(k2, dens, out, D);
  if (si === WINTER) snow(k2, dens, out, D);
  sceneSpace();
  if (si === SPRING) { splashes(k2, dens, out, D); petals(k2, dens, out, D); }
  if (si === SUMMER) fireflies(k2, dens, out, D);
  if (si === FALL) leaves(k2, dens, out, D);
  if (si === WINTER) embers(k2, dens, out, D);
  frameSpace();
}

/* rain: two depths of slanted streaks, plus splashes on hard surfaces */
const SPLASH_SPOTS = [[244, 169], [252, 169], [262, 177], [300, 182], [352, 194], [374, 194], [392, 194], [364, 194], [190, 178], [150, 175], [214, 181], [330, 187]];
function rain(k2, dens, out, D) {
  const far = SL.C0, near = SL.C1, hi = SL.C2;
  const N1 = 160, N2 = 60;
  for (let j = 0; j < N1 + N2; j++) {
    if (hash2(j, 1301) > dens) continue;
    const isNear = j >= N1;
    const per = isNear ? 20 : [24, 27, 30][j % 3];
    const [age, gen] = pclock(k2, j, per, 1303);
    const x0 = Math.floor(hash3(j, gen, 1305) * (W + 60)) - 40;
    const yEnd = isNear ? H + 4 : HORIZON + 10 + Math.floor(hash3(j, gen, 1307) * (H - HORIZON - 10));
    const y0 = -8;
    const y = y0 + Math.floor((yEnd - y0) * age / per);
    const x = x0 + Math.floor((y - y0) * 0.22);
    const len = isNear ? 5 : 3;
    for (let i = 0; i < len; i++) put(out, D, x + Math.floor(i * 0.22), y + i, isNear ? (i === len - 1 ? hi : near) : far);
  }
}
// splashes cycle at fixed hard spots on the island and dock
function splashes(k2, dens, out, D) {
  for (let j = 0; j < SPLASH_SPOTS.length; j++) {
    if (hash2(j, 1311) > dens) continue;
    const [age, gen] = pclock(k2, j, [18, 20, 24][j % 3], 1313);
    if (age > 3) continue;
    const [sx, sy] = SPLASH_SPOTS[j];
    putSpr(out, D, SPR.splash, sx + Math.floor((hash3(j, gen, 1315) - 0.5) * 8), sy, age >> 1);
  }
}

/* petals drift from the cherry canopy downwind */
function petals(k2, dens, out, D) {
  const N = 22;
  for (let j = 0; j < N; j++) {
    if (hash2(j, 1401) > dens) continue;
    const per = [120, 135, 150, 180][j % 4];
    const [age, gen] = pclock(k2, j, per, 1403);
    const u = age / per;
    const sx = 130 + hash3(j, gen, 1405) * 80, sy = 92 + hash3(j, gen, 1407) * 46;
    const dist = 60 + hash3(j, gen, 1409) * 150;
    const drop = 40 + hash3(j, gen, 1411) * 70;
    const sw = SWAY[((age >> 1) + j * 5) % SWAY.length];
    const x = sx + dist * u + sw;
    const y = sy + drop * u + Math.abs(sw) * 0.5;
    if (y > 232) continue;
    const v = j % 3;
    putSpr(out, D, SPR['petal' + v], x, y, ((age >> 2) + j) % 4);
  }
}

/* fireflies: hand-placed homes, slow wandering loops, soft blink */
const FIREFLY_HOMES = [[114, 168], [136, 152], [150, 170], [178, 162], [194, 146], [196, 172], [214, 136], [234, 174],
  [284, 164], [298, 146], [312, 160], [340, 174], [362, 158], [376, 186], [126, 138], [262, 140], [168, 128], [306, 128]];
const FF_PATH = [[0, 0], [1, 0], [1, -1], [2, -1], [2, -2], [3, -2], [3, -3], [2, -3], [2, -4], [1, -4], [0, -4], [0, -3],
  [-1, -3], [-1, -2], [-2, -2], [-2, -1], [-1, -1], [-1, 0]];
const FF_BLINK = [0, 1, 2, 3, 3, 3, 3, 2, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
function fireflies(k2, dens, out, D) {
  for (let j = 0; j < FIREFLY_HOMES.length; j++) {
    if (hash2(j, 1501) > dens) continue;
    const [hx, hy] = FIREFLY_HOMES[j];
    const step = ((k2 / (5 + (j % 3))) | 0) + j * 4;
    const p = FF_PATH[step % FF_PATH.length];
    const big = (j % 2) ? 1 : -1;
    const x = hx + p[0] * big * 2, y = hy + p[1] * 2;
    const b = FF_BLINK[(((k2 / 3) | 0) + j * 7) % FF_BLINK.length];
    if (!b) continue;
    if (b === 3) {
      put(out, D, x, y, SL.A5);
      put(out, D, x - 1, y, SL.L4); put(out, D, x + 1, y, SL.L4);
      put(out, D, x, y - 1, SL.L4); put(out, D, x, y + 1, SL.L4);
    } else put(out, D, x, y, b === 2 ? SL.A5 : SL.L4);
  }
}

/* fall leaves tumble off the trees and ride the wind */
function leaves(k2, dens, out, D) {
  const N = 20;
  for (let j = 0; j < N; j++) {
    if (hash2(j, 1601) > dens) continue;
    const per = [120, 135, 150, 180, 200][j % 5];
    const [age, gen] = pclock(k2, j, per, 1603);
    const u = age / per;
    const fromSmall = hash3(j, gen, 1604) < 0.25;
    const sx = fromSmall ? 108 + hash3(j, gen, 1605) * 26 : 130 + hash3(j, gen, 1605) * 80;
    const sy = fromSmall ? 140 + hash3(j, gen, 1607) * 20 : 92 + hash3(j, gen, 1607) * 46;
    const dist = 80 + hash3(j, gen, 1609) * 260;
    const drop = 30 + hash3(j, gen, 1611) * 90;
    const sw = SWAY[((age >> 1) + j * 3) % SWAY.length] * 2;
    const x = sx + dist * u + sw;
    const y = sy + drop * (u * u * 0.6 + u * 0.4) + Math.abs(sw) * 0.4;
    if (y > 236) continue;
    putSpr(out, D, SPR['leaf' + (j % 3)], x, y, ((age >> 1) + j) % 4);
  }
}

/* snow in three depths with sideways sway */
function snow(k2, dens, out, D) {
  // count, colour, size, fall periods (15 Hz ticks, each divides the loop), sway
  const layers = [[180, 'N0', 1, [300, 270, 360], 1], [104, 'N1', 2, [225, 216, 200], 2], [46, 'N3', 3, [120, 108, 135], 3]];
  let base = 0;
  for (let L = 0; L < 3; L++) {
    const [n, slot, size, pers, amp] = layers[L];
    for (let j = 0; j < n; j++) {
      const id = base + j;
      if (hash2(id, 1701) > dens) continue;
      const P = pers[j % 3];
      const [age, gen] = pclock(k2, id, P, 1703);
      const u = age / P;
      const x0 = hash3(id, gen, 1705) * (W + 40) - 20;
      const yEnd = size === 3 ? H + 4 : HORIZON + 4 + hash3(id, gen, 1707) * (H - HORIZON);
      const y = -6 + (yEnd + 6) * u;
      const sw = SWAY[((age >> 2) + j) % SWAY.length] * amp * 0.5;
      const x = x0 + sw + u * 18 * size;
      if (size === 1) put(out, D, x, y, SL[slot]);
      else if (size === 2) putSpr(out, D, SPR.flake_m, x, y, (j + (age >> 3)) % 2);
      else putSpr(out, D, SPR.flake_l, x, y, (j + (age >> 3)) % 3);
    }
    base += n;
  }
}

/* winter: a few embers escape the chimney */
const CHIMNEY_TOP = [221, 110];
function embers(k2, dens, out, D) {
  for (let j = 0; j < 5; j++) {
    if (hash2(j, 1801) > dens) continue;
    const per = [45, 54, 60, 72, 90][j];
    const [age, gen] = pclock(k2, j, per, 1803);
    const life = 26 + Math.floor(hash3(j, gen, 1805) * 14);
    if (age > life) continue;
    const x = CHIMNEY_TOP[0] + Math.floor(age * 0.45) + SWAY[(age + j * 3) % SWAY.length] * 0.5 + (hash3(j, gen, 1807) - 0.5) * 4;
    const y = CHIMNEY_TOP[1] - Math.floor(age * 0.9);
    const c = age > life - 6 ? SL.Y1 : (((age >> 1) + j) % 3 === 0 ? SL.Y3 : SL.Y2);
    put(out, D, x, y, c);
  }
}
