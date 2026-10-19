/* ==========================================================================
   Objects on the island, back to front. Positions are hand-set in LAYOUT.
   ========================================================================== */
const LAYOUT = {
  cottage: [207, 113],
  cherry: [166, 172],
  birch: [121, 188],
  pine: [322, 185],
  dock: [338, 194],
  bollard: [398, 189],
  boat: [358, 200],
  lantern: [347, 196],
  cat: [265, 156],
  mug: [233, 158],
  kite: [257, 155],
  hammock: [123, 158],
  laundry: [168, 148],
  garden: [172, 168],
  barrel: [202, 166],
  wboxL: [219, 161],
  wboxR: [262, 161],
  firewood: [284, 166],
  stump: [299, 172],
  wreath: [245, 158],
  sled: [277, 158],
  rake: [214, 153],
  boots: [225, 173],
  hat: [231, 157],
  rod: [386, 180],
  jack: [225, 170]
};
const CHIMNEY = [221, 111];

// stepped sway: the upper crown leans a pixel downwind and settles (2 fps steps)
const SWAY_CYCLE = {   // 24 steps: divides the loop at 2 fps
  spring: [0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
  summer: [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  fall: [0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0],
  winter: [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
};
function swayAt(si, k, phase) {
  const c = SWAY_CYCLE[SEASONS[si].key];
  return c[(((k / 15) | 0) + phase) % c.length];
}
// blit with the top `frac` of the sprite shifted by `dx`
function blitSway(buf, s, x, y, dx, frac, fi) {
  if (!s) return;
  if (!dx) { blit(buf, s, x, y, fi); return; }
  const d = s.f[fi || 0], w = s.w, h = s.h;
  const ox = Math.round(x + OX - s.ax), oy = Math.round(y + OY - s.ay);
  const cut = Math.floor(h * frac), mid = Math.floor(h * frac * 1.35);
  for (let j = 0; j < h; j++) {
    const Y = oy + j;
    if (Y < 0 || Y >= H) continue;
    const sh = j < cut ? dx : (j < mid && (j & 1) ? dx : 0);
    for (let i = 0; i < w; i++) {
      const v = d[j * w + i];
      if (!v) continue;
      const X = ox + i + sh;
      if (X < 0 || X >= W) continue;
      buf[Y * W + X] = v;
    }
  }
}
const at = (name, si) => LAYOUT[name];
function put2(name, sprite, fi, alpha) {
  const p = LAYOUT[name];
  blit(OB, SPR[sprite || name], p[0], p[1], fi, false, alpha);
}

/* ---- warm light pools laid on the ground: hand-shaped masks, palette remap ---- */
// '2' core, '1' dim, ':' dim on a checker. Only ground pixels take the colour.
const POOL_MASKS = [
  [217, 177, 'WL', [
    '..:1111111111:..',
    '.:111122221111:.',
    ':11112222221111:',
    '.:111122221111:.',
    '..::11111111::..']],
  [260, 177, 'WL', [
    '..:1111111111:..',
    '.:111122221111:.',
    ':11112222221111:',
    '.:111122221111:.',
    '..::11111111::..']],
  [237, 175, 'WL', [
    '....:::1111:::.....',
    '..:11112222111:....',
    '.:1111222222111:...',
    ':11111222222111:...',
    '.:11111122111111:..',
    '..::1111111111::...']],
  [341, 194, 'LN', [
    '...:11111111:...',
    '.:111122221111:.',
    ':11112222221111:',
    '.::1111111111::.']]
];
const GROUND = new Uint8Array(NSLOT);
'G0 G1 G2 G3 B0 B1 B2 B3 R0 R1 R2 R3 N0 N1 N2 N3'.split(' ').forEach(n => { GROUND[SL[n]] = 1; });
function applyPools(si) {
  for (const [x0, y0, fam, rows] of POOL_MASKS) {
    const hi = SL[fam + '1'], lo = SL[fam + '0'];
    for (let j = 0; j < rows.length; j++) {
      const r = rows[j], y = y0 + j + TY;
      for (let i = 0; i < r.length; i++) {
        const c = r[i];
        if (c === '.') continue;
        const x = x0 + i + TX, idx = y * W + x;
        if (!GROUND[OB[idx]]) continue;
        if (c === ':' && ((x + y) & 1)) continue;
        OB[idx] = c === '2' ? (si === WINTER || fam === 'LN' ? hi : lo) : lo;
      }
    }
  }
}

/* ---- rim light: edges that face a warm source pick up a pixel of its colour ---- */
const RIM_LIGHTS = [
  // x, y, radius, family
  [226, 157, 48, 'WL'], [269, 157, 48, 'WL'], [248, 162, 30, 'WL'], [354, 176, 34, 'LN']
];
const RIM_OK = new Uint8Array(NSLOT);
'L0 L1 L2 L3 L4 P0 P1 P2 P3 B0 B1 B2 B3 R1 R2 R3 G1 G2 G3 N1 N2 N3 A0 A1 A2 A3 A4 A5 H2 H3'.split(' ').forEach(n => { RIM_OK[SL[n]] = 1; });
const COT_BOX = [207 + TX, 113 + TY, 289 + TX, 177 + TY];
function drawRimLight(si) {
  for (const [sx0, sy0, R, fam] of RIM_LIGHTS) {
    const lx = sx0 + TX, ly = sy0 + TY;
    const hi = SL[fam + '1'], lo = SL[fam + '0'];
    const x0 = Math.max(0, lx - R), x1 = Math.min(W - 1, lx + R);
    const y0 = Math.max(0, ly - R), y1 = Math.min(AXIS - 1, ly + R);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      if (x >= COT_BOX[0] && x <= COT_BOX[2] && y >= COT_BOX[1] && y <= COT_BOX[3]) continue;
      const i = y * W + x, v = OB[i];
      if (!v || !RIM_OK[v]) continue;
      const dx = lx - x, dy = ly - y;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d > R || d < 2) continue;
      // the neighbour toward the light must be open air
      const sx = Math.abs(dx) >= Math.abs(dy) ? Math.sign(dx) : 0, sy = sx ? 0 : Math.sign(dy);
      if (OB[i + sy * W + sx]) continue;
      const u = d / R;
      if (BAYER4[((y & 3) << 2) | (x & 3)] >= Math.round((1 - u) * 18)) continue;
      OB[i] = u < 0.45 ? hi : lo;
    }
  }
}

/* ---- shore foam: found from the island's lowest pixels, laps in stepped waves ---- */
let FOAM = null;
function foamInit() {
  FOAM = [];
  const s = SPR.island, d = s.f[0];
  for (let x = 0; x < s.w; x++) {
    let bot = -1;
    for (let y = s.h - 1; y >= 0; y--) if (d[y * s.w + x]) { bot = y; break; }
    if (bot < 0) continue;
    const Y = ISLAND_POS[1] + bot;
    if (Y >= AXIS - TY - 1) FOAM.push(ISLAND_POS[0] + x, Y + 1);   // scene space
  }
}
const FOAM_SEQ = [2, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1];   // 2 bright, 1 soft, 0 none (12 steps)
function drawFoam(si, k) {
  if (!FOAM) foamInit();
  const f3 = (k / 10) | 0;
  const c2 = si === WINTER ? SL.N1 : SL.C1, c1 = SL.C0;
  for (let i = 0; i < FOAM.length; i += 2) {
    const x = FOAM[i], y = FOAM[i + 1];
    const ph = FOAM_SEQ[mod(f3 - Math.floor(x / 9), FOAM_SEQ.length)];
    if (!ph) continue;
    if (ph === 2 && (x & 1)) { px(OB, x, y, c2); if (x % 3 === 0) px(OB, x, y + 1, c1); }
    else if ((x % 3) === 0) px(OB, x, y, c1);
  }
}

/* ---- chimney smoke: a hand-shaped looping plume, thicker as the nights get colder ---- */
const SMOKE_SPR = ['smoke_thin', null, 'smoke_mid', 'smoke_thick'];
function drawSmoke(si, k) {
  const sp = SMOKE_SPR[si];
  if (!sp) return;
  blit(OB, SPR[sp], CHIMNEY[0], CHIMNEY[1], ((k / 3) | 0) % 8);
}

function drawObjects(si, k) {
  const k15 = (k / 15) | 0;           // 2 fps
  const f10 = (k / 3) | 0;            // 10 fps
  sceneSpace();
  blit(OB, SPR.island, ISLAND_POS[0], ISLAND_POS[1]);
  if (si === WINTER) blit(OB, SPR.island_snow, ISLAND_POS[0], ISLAND_POS[1]);
  if (si === SPRING) blit(OB, SPR.petals_ground, PETALS_GROUND_POS[0], PETALS_GROUND_POS[1]);
  if (si === FALL) blit(OB, SPR.leaves_ground, LEAVES_GROUND_POS[0], LEAVES_GROUND_POS[1]);

  // far left: the birch, then the cherry on its knoll
  const [cx, cy] = LAYOUT.cherry, [bx, by] = LAYOUT.birch, [pnx, pny] = LAYOUT.pine;
  const sw = swayAt(si, k, 0), sw2 = swayAt(si, k, 7), sw3 = swayAt(si, k, 3);
  const yt = ['young_full', 'young_full', 'young_fall', 'young_bare'][si];
  blitSway(OB, SPR[yt], bx, by, sw2, 0.4);
  if (si === WINTER) blitSway(OB, SPR.young_snow, bx, by, sw2, 0.4);
  const cher = ['cherry_bloom', 'cherry_full', 'cherry_fall', 'cherry_bare'][si];
  blitSway(OB, SPR[cher], cx, cy, sw, si === WINTER ? 0.25 : 0.42);
  if (si === WINTER) blitSway(OB, SPR.cherry_snow, cx, cy, sw, 0.25);
  if (si === SUMMER) put2('hammock');

  // laundry line between the cherry and the cottage corner
  put2('laundry', 'laundry_' + SEASONS[si].key, (k15 + (si === FALL ? 0 : 1)) % (si === FALL ? 2 : 4) === 0 ? 1 : 0);
  put2('garden', 'garden_' + SEASONS[si].key);
  put2('barrel');
  if (si === SPRING) blit(OB, SPR.barrel_ripple, LAYOUT.barrel[0], LAYOUT.barrel[1] + 2, (f10 >> 1) % 4);
  if (si === WINTER) put2('barrel', 'barrel_snow');

  // the cottage and its winter coat
  blit(OB, SPR.cottage, LAYOUT.cottage[0], LAYOUT.cottage[1]);
  if (si === WINTER) {
    blit(OB, SPR.roof_snow, LAYOUT.cottage[0], LAYOUT.cottage[1]);
    blit(OB, SPR.icicles, LAYOUT.cottage[0], LAYOUT.cottage[1]);
    put2('wreath');
    put2('sled');
  }
  drawSmoke(si, k);
  put2('wboxL', 'wbox_' + SEASONS[si].key);
  put2('wboxR', 'wbox_' + SEASONS[si].key);
  // the cat dozes on the sill: slow breathing, a rare tail flick
  const cb = (k15 % 6) < 3 ? 0 : 1;
  const flick = mod(k15, 48) === 17 ? 2 : cb;
  put2('cat', 'cat', flick);
  put2('mug');
  if (si !== SUMMER) put2('mug', 'steam', (k / 6 | 0) % 4, 0.75);
  if (si === SPRING) { put2('kite', 'kite', (f10 >> 2) % 3); put2('boots'); }
  if (si === SUMMER) put2('hat');
  if (si === FALL) {
    put2('rake');
    put2('jack');
    blit(OB, SPR.pumpkin_med, 259, 163);
    blit(OB, SPR.pumpkin_small, 253, 169);
    blit(OB, SPR.pumpkin_big, 262, 170);
  }
  put2('firewood');
  if (si === WINTER) blit(OB, SPR.firewood_snow, LAYOUT.firewood[0], LAYOUT.firewood[1] - 2);
  put2('stump');

  // pine in front
  blitSway(OB, SPR.pine, pnx, pny, sw3, 0.22);
  if (si === WINTER) blitSway(OB, SPR.pine_snow, pnx, pny, sw3, 0.22);

  // dock, lantern, boat
  put2('dock', 'dock_short');
  if (si === WINTER) put2('dock', 'dock_short_snow');
  if (si === SPRING) drawPuddle(k);
  const bob = BOAT_BOB[k15 % BOAT_BOB.length];
  const [bx2, by2] = LAYOUT.boat;
  blit(OB, SPR.boat, bx2, by2 + bob);
  if (si === WINTER) blit(OB, SPR.boat_snow, bx2, by2 + bob);
  // mooring rope from the bollard to the stern ring
  const [rx, ry] = LAYOUT.bollard;
  for (let y = ry + 4; y < by2 + bob + 3; y++) px(OB, rx + 2 - ((y - ry) >> 3), y, SL.B2);
  put2('bollard');
  if (si === SUMMER) {
    put2('rod');
    for (let y = 182; y < AXIS - TY; y += 1) if ((y + (f10 >> 2)) % 5) px(OB, 403, y, SL.N0);
  }
  drawBuoy(si, k);
  put2('lantern', 'lantern', (f10 >> 1) % 4);
  if (si === WINTER) put2('lantern', 'lantern_snow');

  drawFoam(si, k);
  frameSpace();
  drawRimLight(si);
  applyPools(si);
}
const BOAT_BOB = [0, 0, 0, 1, 1, 1, 1, 0, 0, 0, -1, -1];

// spring: a rain puddle on the dock planks catches the lantern light
function drawPuddle(k) {
  const f = ((k / 5) | 0) % 6;
  const y = LAYOUT.dock[1];
  for (let x = 361; x < 372; x++) px(OB, x, y, x === 361 || x === 371 ? SL.C0 : SL.C1);
  for (let x = 363; x < 370; x++) px(OB, x, y + 1, SL.C0);
  const shine = [364, 366, 368, 367, 365, 369][f];
  px(OB, shine, y, SL.C2);
  px(OB, shine + 1, y, SL.LN2);
  if (f === 2 || f === 5) px(OB, shine - 2, y + 1, SL.C1);
}

// a channel buoy rides the swell beside the boat; its lamp blinks slowly
function drawBuoy(si, k) {
  const k15 = (k / 15) | 0;
  const bob = BUOY_BOB[(k15 + 3) % BUOY_BOB.length];
  const x = 414, y = 203 + bob;
  blit(OB, SPR.buoy, x, y);
  if (si === WINTER) { px(OB, x + 1, y, SL.N2); px(OB, x + 2, y, SL.N3); px(OB, x + 3, y, SL.N2); }
  const on = ((k / 30) | 0) % 4 === 0;
  px(OB, x + 2, y - 1, on ? SL.Y3 : SL.A0);
  if (on) { px(OB, x + 1, y - 1, SL.Y1); px(OB, x + 3, y - 1, SL.Y1); }
}
const BUOY_BOB = [0, 1, 1, 1, 0, 0, -1, 0];
