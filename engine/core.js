'use strict';
/* ==========================================================================
   pixel-loop engine: core
   Canvas constants, the shared phase timeline (picture and music), palette
   slots, sprite parsing and blitting. Everything on screen is a pure function
   of the tick k (30 Hz), so the loop repeats exactly and never drifts.

   Needs a global SCENE (the scene's config.js), loaded before this file.
   ========================================================================== */
const W = SCENE.width, H = SCENE.height, NPX = W * H;
const HZ = 30;                                  // content tick rate

/* ---- the phase timeline, shared by picture and music ----
   Each phase plays its chord loop for SCENE.bars bars at its own tempo, then one
   transition bar ramps the tempo into the next phase like a DJ blend. Tempos are
   scaled by a hair so the whole cycle lasts exactly SCENE.cycle seconds. */
const NPH = SCENE.phases.length;
const BASE_BPM = SCENE.phases.map(p => p.bpm);
const SEASON_BARS = SCENE.bars || 8;
const CYCLE = SCENE.cycle || 120;               // seconds for one pass through every phase
const CYCLE_TICKS = CYCLE * HZ;
const GRAND = SCENE.grand || 3;                 // slow drifts loop over GRAND cycles
const TICKS = CYCLE_TICKS * GRAND;              // the picture repeats every CYCLE * GRAND seconds
const TIMELINE = (() => {
  const total = b => {
    let t = 0;
    for (let s = 0; s < NPH; s++) t += SEASON_BARS * 240 / b[s] + 480 / (b[s] + b[(s + 1) % NPH]);
    return t;
  };
  const k = total(BASE_BPM) / CYCLE;
  const bpm = BASE_BPM.map(b => b * k);
  const seg = [];
  let t = 0;
  for (let s = 0; s < NPH; s++) {
    const L = SEASON_BARS * 240 / bpm[s];
    seg.push({ kind: 'season', s, start: t, dur: L, bpm: bpm[s] });
    t += L;
    const b0 = bpm[s], b1 = bpm[(s + 1) % NPH];
    seg.push({ kind: 'trans', s, to: (s + 1) % NPH, start: t, dur: 480 / (b0 + b1), b0, b1 });
    t += 480 / (b0 + b1);
  }
  seg[seg.length - 1].dur += CYCLE - t;         // absorb float rounding
  return { bpm, seg };
})();
// beat position -> seconds inside a segment (tempo ramps linearly across a transition)
function segBeatTime(g, beat) {
  if (g.kind === 'season') return beat * 60 / g.bpm;
  const a = (g.b1 - g.b0) / (120 * g.dur), b = g.b0 / 60;
  if (Math.abs(a) < 1e-9) return beat / b;
  return (-b + Math.sqrt(b * b + 4 * a * beat)) / (2 * a);
}

/* ---- drawing origin: art can be authored in its own space and offset ---- */
let OX = 0, OY = 0;
function setOrigin(x, y) { OX = x; OY = y; }

/* ---- palette slots: '_' (0) is transparent; the rest come from the scene ---- */
const SLOT_LIST = ['_'].concat(SCENE.slots);
const SL = {};
SLOT_LIST.forEach((n, i) => { SL[n] = i; });
const NSLOT = SLOT_LIST.length;
if (NSLOT > 255) throw new Error('pixel-loop: at most 255 palette slots');

// ordered dither matrices
const BAYER4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
const BAYER8 = new Uint8Array([
  0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26,
  12, 44, 4, 36, 14, 46, 6, 38, 60, 28, 52, 20, 62, 30, 54, 22,
  3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25,
  15, 47, 7, 39, 13, 45, 5, 37, 63, 31, 55, 23, 61, 29, 53, 21]);

// deterministic integer hash -> [0,1). Never use Math.random in drawing code.
function hash(n) {
  n = (n | 0) ^ 0x9e3779b9;
  n = Math.imul(n ^ (n >>> 16), 0x85ebca6b);
  n = Math.imul(n ^ (n >>> 13), 0xc2b2ae35);
  n ^= n >>> 16;
  return (n >>> 0) / 4294967296;
}
function hash2(a, b) { return hash(Math.imul(a | 0, 73856093) ^ Math.imul(b | 0, 19349663)); }
function hash3(a, b, c) { return hash(Math.imul(a | 0, 73856093) ^ Math.imul(b | 0, 19349663) ^ Math.imul(c | 0, 83492791)); }
const mod = (a, n) => ((a % n) + n) % n;

/* ---------------- palettes ---------------- */
function hexTo32(hex) {
  const v = parseInt(hex.slice(1), 16);
  const r = (v >> 16) & 255, g = (v >> 8) & 255, b = v & 255;
  return (0xff000000 | (b << 16) | (g << 8) | r) >>> 0;
}
const PALETTE_WARN = [];
function buildPalette(def, fallback, name) {
  const p = new Uint32Array(NSLOT);
  for (let i = 1; i < NSLOT; i++) {
    const n = SLOT_LIST[i];
    const hex = def[n] || (fallback && fallback[n]);
    if (!hex && !(SCENE.dynamicSlots || []).includes(n) && PALETTE_WARN.length < 50) PALETTE_WARN.push((name || '?') + ': no colour for slot ' + n);
    p[i] = hex ? hexTo32(hex) : 0xffff00ff;     // loud magenta marks a missing colour
  }
  return p;
}

/* ---------------- sprites ---------------- */
// def(name, key, src): ASCII rows; '.' or ' ' transparent; frames separated by '---'.
// key maps characters to slot names. opt.ax/ay set the anchor.
const SPR = {};
const SPRITE_WARN = [];
function def(name, key, src, opt) {
  opt = opt || {};
  const lines = src.split('\n');
  while (lines.length && !lines[0].trim()) lines.shift();
  while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
  const frames = [];
  let cur = [];
  for (const ln of lines) {
    if (/^\s*-{3,}\s*$/.test(ln)) { frames.push(cur); cur = []; }
    else cur.push(ln.replace(/\s+$/, ''));
  }
  frames.push(cur);
  let w = 0, h = 0;
  for (const f of frames) { h = Math.max(h, f.length); for (const r of f) w = Math.max(w, r.length); }
  const data = frames.map(f => {
    const a = new Uint8Array(w * h);
    for (let y = 0; y < f.length; y++) {
      const row = f[y];
      for (let x = 0; x < row.length; x++) {
        const c = row[x];
        if (c === '.' || c === ' ') continue;
        const sn = key[c];
        if (sn === undefined || SL[sn] === undefined) {
          SPRITE_WARN.push(name + ': unknown key ' + JSON.stringify(c) + ' at ' + x + ',' + y);
          continue;
        }
        a[y * w + x] = SL[sn];
      }
    }
    return a;
  });
  SPR[name] = { name, w, h, f: data, ax: opt.ax || 0, ay: opt.ay || 0 };
  return SPR[name];
}

// draw sprite into an index buffer. alpha < 1 dissolves through an 8x8 ordered dither.
function blit(buf, s, x, y, fi, flip, alpha, remap) {
  if (!s) return;
  const d = s.f[(fi || 0) % s.f.length];
  const w = s.w, h = s.h;
  x = Math.round(x + OX - (flip ? (w - 1 - s.ax) : s.ax));
  y = Math.round(y + OY - s.ay);
  const th = (alpha === undefined || alpha >= 1) ? 64 : Math.floor(Math.max(0, alpha) * 64);
  if (th <= 0) return;
  for (let j = 0; j < h; j++) {
    const Y = y + j;
    if (Y < 0 || Y >= H) continue;
    const row = Y * W, srow = j * w;
    for (let i = 0; i < w; i++) {
      const v = d[srow + (flip ? w - 1 - i : i)];
      if (!v) continue;
      const X = x + i;
      if (X < 0 || X >= W) continue;
      if (th < 64 && BAYER8[((Y & 7) << 3) | (X & 7)] >= th) continue;
      buf[row + X] = remap ? remap[v] : v;
    }
  }
}

function px(buf, x, y, slot) {
  x = Math.floor(x) + OX; y = Math.floor(y) + OY;
  if (x < 0 || y < 0 || x >= W || y >= H) return;
  buf[y * W + x] = slot;
}
function hline(buf, x0, x1, y, slot) {
  y = Math.floor(y) + OY;
  if (y < 0 || y >= H) return;
  x0 = Math.max(0, Math.floor(x0) + OX); x1 = Math.min(W - 1, Math.floor(x1) + OX);
  for (let x = x0; x <= x1; x++) buf[y * W + x] = slot;
}
