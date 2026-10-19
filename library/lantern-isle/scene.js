/* ==========================================================================
   Lantern Isle: composition and the engine hooks.
   The island art is authored in its own "scene space" and offset onto the
   480 x 270 frame by (TX, TY). Every phase (season) shares the same slot
   meanings, so one sprite reads correctly in all four palettes.
   ========================================================================== */
const TX = -12, TY = 0;                  // scene space -> frame
const HORIZON = 158 + TY;                // first sea row
const AXIS = 207 + TY;                   // water surface used for reflections
function sceneSpace() { setOrigin(TX, TY); }
function frameSpace() { setOrigin(0, 0); }

/* sky and sea gradients per season: [yStart, slot, dithered transition rows] */
const SEASONS = [
  { name: 'spring', key: 'spring',
    sky: [[0, 'S0'], [34, 'S1', 12], [64, 'S2', 12], [92, 'S3', 12], [116, 'S4', 10], [136, 'S5', 10], [150, 'S6', 8]],
    sea: [[158, 'E0'], [164, 'E1', 4], [178, 'E2', 8], [204, 'E3', 10], [236, 'E4', 12]],
    starsBelow: 0, winHold: 4, lanHold: 3 },
  { name: 'summer', key: 'summer',
    sky: [[0, 'S0'], [32, 'S1', 14], [62, 'S2', 14], [88, 'S3', 12], [110, 'S4', 12], [130, 'S5', 10], [146, 'S6', 8]],
    sea: [[158, 'E0'], [162, 'E1', 4], [174, 'E2', 8], [200, 'E3', 10], [234, 'E4', 12]],
    starsBelow: 66, winHold: 5, lanHold: 3 },
  { name: 'fall', key: 'fall',
    sky: [[0, 'S0'], [36, 'S1', 14], [66, 'S2', 14], [94, 'S3', 12], [116, 'S4', 12], [136, 'S5', 10], [150, 'S6', 8]],
    sea: [[158, 'E0'], [163, 'E1', 4], [176, 'E2', 8], [202, 'E3', 10], [234, 'E4', 12]],
    starsBelow: 104, winHold: 4, lanHold: 3 },
  { name: 'winter', key: 'winter',
    sky: [[0, 'S0'], [40, 'S1', 16], [76, 'S2', 16], [104, 'S3', 12], [126, 'S4', 12], [143, 'S5', 10], [152, 'S6', 6]],
    sea: [[158, 'E0'], [162, 'E1', 4], [174, 'E2', 8], [200, 'E3', 10], [232, 'E4', 12]],
    starsBelow: 150, winHold: 2, lanHold: 3 }
];
const SPRING = 0, SUMMER = 1, FALL = 2, WINTER = 3;
// the gradient transitions were drawn a touch wide; tighten them (sky 90%, sea 80%)
for (const s of SEASONS) {
  s.sky = s.sky.map(([y, slot, tw]) => [y, slot, tw ? Math.min(26, Math.round(tw * 0.9)) : 0]);
  s.sea = s.sea.map(([y, slot, tw]) => [y, slot, tw ? Math.min(26, Math.round(tw * 0.8)) : 0]);
}

/* what each colour becomes when mirrored in the water */
function buildReflectMap() {
  const m = new Uint8Array(NSLOT);
  const set = (names, to) => names.split(' ').forEach(n => { m[SL[n]] = SL[to]; });
  set('K0 K1 K2 R0 B0 P0 P1 G0 F0 L0 C0', 'RF0');
  set('R1 R2 B1 B2 G1 G2 H0 H1 F1 F2 L1 L2 P2 P3 A2 A3', 'RF1');
  set('H2 H3 G3 R3 B3 F3 L3 L4 N0 N1 A0 A1 A4 A5 C1', 'RF2');
  set('N2 N3 C2 M2 M3', 'N0');
  set('M0 M1', 'RF2');
  set('WL3', 'WL2'); set('WL2', 'WL1'); set('WL1', 'WL1'); set('WL0', 'WL0');
  set('LN3', 'LN2'); set('LN2', 'LN1'); set('LN1', 'LN0'); set('LN0', 'Y0');
  set('Y3', 'Y2'); set('Y2', 'Y1'); set('Y1', 'Y0'); set('Y0', 'RF1');
  return m;
}

/* warm windows and the lantern flicker by swapping palette entries (WL*, LN*) */
function sceneDynamic(si, k, D, P) {
  const s = SEASONS[si];
  const f10 = (k / 3) | 0;
  const deep = si === WINTER ? 0.08 : 0.04, dim = si === WINTER ? 0.30 : 0.18;
  const w = flick(f10, 17 + si, s.winHold, dim, deep);
  D[SL.WL3] = P[w === 0 ? SL.Y3 : SL.Y2];
  D[SL.WL2] = P[w === 2 ? SL.Y1 : SL.Y2];
  D[SL.WL1] = P[w === 2 ? SL.Y0 : SL.Y1];
  D[SL.WL0] = P[w === 0 ? SL.Y0 : SL.RF1];
  const l = flick(f10, 41 + si, s.lanHold, 0.22, 0.06);
  D[SL.LN3] = P[l === 0 ? SL.Y3 : SL.Y2];
  D[SL.LN2] = P[l === 2 ? SL.Y1 : SL.Y2];
  D[SL.LN1] = P[l === 2 ? SL.Y0 : SL.Y1];
  D[SL.LN0] = P[l === 0 ? SL.Y0 : SL.RF1];
  return { w, l };
}

/* ---------------- engine hooks ---------------- */
function sceneInit() {
  for (const s of SEASONS) s.refl = buildReflectMap();
}
function sceneBack(si, k) {
  const s = SEASONS[si];
  bands(BG, s.sky, HORIZON);
  bands(BG, s.sea, H);
  drawSkyFeatures(si, k);
  drawSeaFeatures(si, k);
}
function sceneObjects(si, k) { drawObjects(si, k); }
function sceneAfterObjects(si, k) { drawReflections(si, k); }
function sceneFront(si, k) { drawFront(si, k); }
function sceneParticles(si, k, dens, out, D) { drawParticles(si, k, dens, out, D); }
