/* ==========================================================================
   Sky features: stars, moons, clouds, aurora, lighthouse, migrating birds.
   ========================================================================== */
// hand-placed stars: x, y, kind (0 dim, 1 bright, 2 twinkler)
const STARS = [
  [12, 8, 0], [27, 21, 1], [41, 5, 0], [58, 33, 0], [66, 14, 2], [83, 27, 0], [97, 9, 1], [109, 41, 0],
  [121, 18, 0], [134, 6, 0], [146, 29, 1], [152, 52, 0], [163, 13, 0], [177, 37, 2], [189, 22, 0], [198, 7, 1],
  [211, 45, 0], [219, 16, 0], [232, 30, 0], [241, 9, 2], [253, 52, 0], [262, 24, 1], [274, 11, 0], [283, 39, 0],
  [296, 19, 0], [305, 6, 1], [314, 48, 0], [322, 28, 2], [337, 15, 0], [349, 35, 0], [356, 8, 0], [368, 57, 1],
  [377, 22, 0], [389, 42, 0], [398, 12, 2], [409, 31, 0], [417, 4, 0], [428, 47, 1], [436, 19, 0], [447, 36, 0],
  [455, 9, 1], [466, 27, 0], [473, 51, 0], [8, 64, 0], [33, 72, 1], [52, 61, 0], [74, 86, 0], [91, 70, 0],
  [118, 79, 0], [139, 66, 1], [171, 74, 0], [203, 84, 0], [226, 68, 0], [248, 90, 1], [271, 72, 0], [290, 83, 0],
  [318, 70, 0], [343, 88, 0], [361, 76, 1], [384, 66, 0], [402, 82, 0], [421, 73, 0], [444, 91, 1], [462, 68, 0],
  [19, 102, 0], [61, 110, 0], [103, 98, 0], [187, 108, 0], [233, 104, 0], [279, 112, 0], [333, 100, 0],
  [391, 106, 0], [452, 114, 0], [5, 30, 0], [88, 48, 0], [128, 54, 2], [196, 58, 0], [283, 58, 1], [341, 61, 0],
  [470, 80, 0], [16, 126, 0], [123, 122, 0], [404, 128, 0], [258, 128, 0], [163, 136, 0], [31, 140, 0]
];


const LIGHTHOUSE = { x: 446, y: HORIZON, dir: -1 };   // far islet on the right; its beam sweeps left
const MOON_POS = { fall: [352, 26], summer: [58, 20], spring: [330, 18] };

function drawStars(si, k) {
  const lim = SEASONS[si].starsBelow;
  if (!lim) return;
  const f10 = (k / 3) | 0;
  const dim = SL.C0, mid = SL.C1, hi = SL.C2;
  for (let i = 0; i < STARS.length; i++) {
    const [x, y, kind] = STARS[i];
    if (y >= lim) continue;
    // stars near the band where the sky brightens fade to their dim tone
    const nearEdge = y > lim - 18;
    const tw = hash2(((f10 + i * 7) / 5) | 0, i);
    if (kind === 0) { px(BG, x, y, nearEdge ? dim : (tw < 0.08 ? dim : mid)); continue; }
    if (kind === 1) { px(BG, x, y, nearEdge ? mid : (tw < 0.12 ? mid : hi)); continue; }
    // twinkler: 3x3 cross at its brightest, single pixel otherwise
    const ph = ((f10 + i * 13) % 40);
    if (!nearEdge && ph < 6) blit(BG, SPR.twinkle, x - 1, y - 1, ph < 2 || ph >= 4 ? 1 : 0);
    else px(BG, x, y, tw < 0.2 ? mid : hi);
  }
}

function drawMoon(si, k) {
  if (si === FALL) blit(BG, SPR.moon_fall, MOON_POS.fall[0], MOON_POS.fall[1]);
  else if (si === SUMMER) blit(BG, SPR.moon_crescent, MOON_POS.summer[0], MOON_POS.summer[1]);
  else if (si === SPRING) blit(BG, SPR.moon_veiled, MOON_POS.spring[0], MOON_POS.spring[1]);
}

/* ---- clouds: drifting sprites, whole traversals per cycle so they loop ---- */
// [sprite, y, startX, traversals per cycle (negative = leftward), span]
// spans are wider than the frame so a cloud is always fully off screen when it wraps
const CLOUDS = {
  spring: [
    ['cloud_bank_a', 8, 0, 3, 500], ['cloud_bank_b', 38, 214, 4, 500], ['cloud_bank_c', 70, 80, 5, 500],
    ['cloud_wisp_a', 108, 52, 6, 540], ['cloud_wisp_b', 128, 268, 6, 540]
  ],
  summer: [
    ['cloud_thin_a', 64, 186, 1, 560], ['cloud_thin_c', 90, 26, 2, 560],
    ['cloud_dusk_a', 116, 80, 2, 540], ['cloud_dusk_b', 131, 440, 3, 540], ['cloud_dusk_c', 144, 254, 2, 540]
  ],
  fall: [
    ['cloud_thin_a', 28, 346, 2, 560], ['cloud_thin_b', 54, 80, 3, 560], ['cloud_thin_c', 118, 560, 2, 560]
  ],
  winter: [
    ['cloud_thin_c', 132, 160, 1, 560]
  ]
};
function cloudX(c, k) {
  const [, , x0, trav, span] = c;
  const sp = SPR[c[0]];
  const w = sp ? sp.w : 64;
  const total = span + w;
  const k2 = k >> 1;                        // 15 Hz stepping
  const per = TICKS / 2 / Math.abs(trav);   // ticks per traversal
  const p = ((k2 % per) / per) * total;
  const x = trav > 0 ? (x0 + p) % total - w : total - ((x0 + p) % total) - w;
  return Math.floor(x);
}
function drawClouds(si, k) {
  const list = CLOUDS[SEASONS[si].key];
  for (const c of list) {
    const sp = SPR[c[0]];
    if (!sp) continue;
    blit(BG, sp, cloudX(c, k), c[1]);
  }
}

/* ---- aurora: two faint curtains, hand-shaped, folds drift slowly ---- */
// each curtain: base line control points and ray heights along x (hand placed)
const AURORA = [
  { base: [[18, 72], [66, 68], [120, 63], [172, 57], [226, 53], [280, 56], [334, 48], [386, 43], [440, 45], [466, 43]],
    hgt: [[18, 8], [66, 18], [120, 24], [172, 30], [226, 34], [280, 27], [334, 31], [386, 28], [440, 19], [466, 9]],
    seed: 3, speed: 1 },
  { base: [[52, 98], [120, 93], [186, 89], [252, 86], [320, 83], [386, 80], [426, 79]],
    hgt: [[52, 5], [120, 11], [186, 16], [252, 19], [320, 16], [386, 9], [426, 5]],
    seed: 9, speed: -1 }
];
function lerpTable(tab, x) {
  if (x <= tab[0][0]) return tab[0][1];
  for (let i = 1; i < tab.length; i++) {
    if (x <= tab[i][0]) {
      const a = tab[i - 1], b = tab[i];
      return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]);
    }
  }
  return tab[tab.length - 1][1];
}
// a fold profile drawn by hand: brightness along the curtain (repeats)
const FOLD = [0.2, 0.35, 0.6, 0.85, 1, 0.9, 0.7, 0.5, 0.4, 0.45, 0.6, 0.75, 0.7, 0.5, 0.3, 0.2, 0.25, 0.4, 0.55, 0.5, 0.35, 0.2, 0.15, 0.15];
function drawAurora(si, k) {
  if (si !== WINTER) return;
  const f3 = (k / 10) | 0;                    // 3 fps
  const U0 = SL.U0, U1 = SL.U1, U2 = SL.U2;
  for (const cu of AURORA) {
    const x0 = cu.base[0][0], x1 = cu.base[cu.base.length - 1][0];
    const shift = ((f3 / 4) | 0) * cu.speed;   // folds slide one step every ~1.3 s
    for (let x = x0; x <= x1; x++) {
      const fi = mod(Math.floor((x + shift + cu.seed * 7) / 6), FOLD.length);
      const fo = FOLD[fi] * Math.min(1, (x - x0) / 30, (x1 - x) / 30);
      if (fo < 0.1) continue;
      const base = Math.round(lerpTable(cu.base, x)) + AURORA_WOB[mod(((x >> 3) + (f3 >> 3)), AURORA_WOB.length)];
      // rays: neighbouring columns differ in reach, which reads as vertical striation
      const ray = hash2(x >> 1, cu.seed + ((f3 >> 5) & 3));
      const reach = ray < 0.35 ? 1.35 : (ray < 0.6 ? 1 : 0.7);
      const hgt = Math.max(3, Math.round(lerpTable(cu.hgt, x) * (0.45 + fo * 0.6) * reach));
      const colBright = fo * (ray < 0.35 ? 1.15 : 0.9);
      for (let r = 0; r < hgt; r++) {
        const y = base - r;
        if (y < 2) break;
        const t = r / hgt;
        let slot = U0;
        if (r === 0) slot = colBright > 0.75 ? U2 : U1;
        else if (r < 3 && colBright > 0.5) slot = U1;
        else if (ray < 0.35 && t < 0.45 && colBright > 0.6) slot = U1;
        const keep = (1 - t) * (0.3 + colBright * 0.7);
        if (BAYER8[((y & 7) << 3) | (x & 7)] >= keep * 64) continue;
        px(BG, x, y, slot);
      }
    }
  }
}
const AURORA_WOB = [0, 0, 1, 1, 0, 0, -1, -1, 0, 1, 0, -1, 0, 0];

/* ---- lighthouse on a far islet, its beam sweeps only in clear summer air ---- */
function drawLighthouse(si, k) {
  const { x, y, dir } = LIGHTHOUSE;
  blit(BG, SPR.lighthouse, x, y);
  const lx = x, ly = y - 14;
  if (si !== SUMMER) {
    // a slow blink in hazy seasons
    const on = ((k / 45) | 0) % 4 === 0;
    px(BG, lx, ly, on ? SL.Y3 : SL.Y1);
    return;
  }
  const per = 270;                       // 9 s per rotation (divides the loop)
  const ph = Math.floor(((k % per) / per) * 12);
  const LEN = [118, 92, 62, 30, 0, 0, 0, 0, 0, 0, 0, 0];
  px(BG, lx, ly, ph === 4 ? SL.Y3 : (ph < 4 ? SL.Y3 : SL.Y2));
  if (ph === 4) { blit(BG, SPR.flare, lx - 2, ly - 2); return; }
  const L = LEN[ph];
  if (!L) return;
  // a tapered wedge of paler air: wider and thinner as it reaches out
  for (let d = 2; d <= L; d++) {
    const xx = lx + d * dir;
    const u = d / L;
    const half = Math.min(3, Math.floor(d / 20));
    for (let o = -half; o <= half; o++) {
      const yy = ly + o + Math.floor(d / 45);
      if (yy >= HORIZON) continue;
      const edge = Math.abs(o) === half && half > 0;
      const th = Math.round((1 - u) * 13 + 2) - (edge ? 5 : 0);
      if (BAYER4[((yy & 3) << 2) | (xx & 3)] >= th) continue;
      px(BG, xx, yy, u < 0.35 && !edge ? SL.N2 : SL.N1);
    }
    // where it grazes the water a few pale dashes appear
    if (d > 24 && (d % 3) && BAYER4[((HORIZON & 3) << 2) | (xx & 3)] < (1 - u) * 10) px(BG, xx, HORIZON + 1 + Math.floor(d / 60), SL.N0);
  }
}

/* ---- migrating birds cross the fall moon ---- */
const FLOCK = [[0, 0], [-6, 3], [-11, 5], [-5, -3], [-12, -5], [-18, 8], [-20, -7]];
const BIRD_PASSES = [
  { t0: 2, t1: 20, y: 40, far: false },
  { t0: 9, t1: 26, y: 80, far: true }
];
function drawBirds(si, k) {
  if (si !== FALL) return;
  const { t } = seasonClock(k, FALL);
  const k2 = k >> 1;
  for (const p of BIRD_PASSES) {
    if (t < p.t0 || t > p.t1) continue;
    const u = (t - p.t0) / (p.t1 - p.t0);
    for (let i = 0; i < FLOCK.length; i++) {
      const [ox, oy] = FLOCK[i];
      const bx = Math.floor(-30 + u * (W + 60)) + ox * (p.far ? 0.7 : 1);
      const bob = BIRD_BOB[((k2 >> 2) + i * 3) % BIRD_BOB.length];
      const by = p.y + Math.round(oy * (p.far ? 0.7 : 1)) + bob;
      const fr = (((k2 >> 1) + i * 2) % 4);
      blit(BG, p.far ? SPR.bird_far : SPR.bird, Math.round(bx), by, fr === 3 ? 1 : fr);
    }
  }
}
const BIRD_BOB = [0, 0, 0, 1, 1, 1, 0, 0, -1, -1, 0, 0];

function drawSkyFeatures(si, k) {
  drawStars(si, k);
  drawAurora(si, k);
  drawMoon(si, k);
  drawLighthouse(si, k);
  drawClouds(si, k);
  drawBirds(si, k);
}
