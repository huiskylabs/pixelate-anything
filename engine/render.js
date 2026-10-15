/* ==========================================================================
   pixel-loop engine: frame rendering
   Each phase renders into palette-index buffers with its own palette. Phase
   changes dissolve two finished frames through an ordered dither, so every
   on-screen pixel is always a colour from one of the hand-picked palettes.

   Scene hooks (global functions the scene defines; only sceneBack is required):
     sceneBack(si, k)              background into BG (sky, sea, far things)
     sceneObjects(si, k)           objects into OB (drawn over BG)
     sceneAfterObjects(si, k)      reads OB, writes BG (reflections, light on water)
     sceneFront(si, k)             into IX after compositing (mist, foreground)
     sceneDynamic(si, k, D, P)     palette cycling: D = live palette, P = base
     sceneParticles(si, k, dens, out, D)  weather into the final RGBA frame;
                                   dens fades 1 -> 0 across a transition
   ========================================================================== */
const BG = new Uint8Array(NPX);     // background indices
const OB = new Uint8Array(NPX);     // object indices (0 = empty)
const IX = new Uint8Array(NPX);     // composited indices
const RGB = [new Uint32Array(NPX), new Uint32Array(NPX)];
const DYN = [new Uint32Array(NSLOT), new Uint32Array(NSLOT)];
const PHASE_PAL = [];

function initPalettes() {
  // slots a palette leaves out fall back to SCENE.paletteFallback (default: the first phase)
  const first = PALETTES[SCENE.paletteFallback || SCENE.phases[0].palette || SCENE.phases[0].name];
  SCENE.phases.forEach((ph, i) => {
    const key = ph.palette || ph.name;
    if (!PALETTES[key]) throw new Error('pixel-loop: no palette "' + key + '"');
    PHASE_PAL[i] = buildPalette(PALETTES[key], first, key);
  });
  if (typeof sceneInit === 'function') sceneInit();
}

/* ---------------- banded gradients ---------------- */
// stops: [yStart, slot, transitionRows]; the dithered transition sits just above each stop
function bands(buf, stops, yEnd) {
  for (let b = 0; b < stops.length; b++) {
    const y0 = stops[b][0];
    const a = SL[stops[b][1]];
    const nxt = stops[b + 1];
    const y1 = nxt ? nxt[0] : yEnd;
    const tw = nxt ? (nxt[2] || 4) : 0;
    const nb = nxt ? SL[nxt[1]] : 0;
    for (let y = y0; y < y1; y++) {
      const row = y * W;
      const r = y - (y1 - tw);
      if (!nxt || r < 0) { buf.fill(a, row, row + W); continue; }
      const L = Math.round((r + 1) / (tw + 1) * 64);
      const by = (y & 7) << 3;
      for (let x = 0; x < W; x++) buf[row + x] = BAYER8[by | (x & 7)] < L ? nb : a;
    }
  }
}

/* ---------------- stepped flicker for palette cycling ---------------- */
// returns 0 (full), 1 (dim) or 2 (deep), held for `hold` steps of f10 (10 fps)
function flick(f10, seed, hold, pDim, pDeep) {
  const h = hash2(Math.floor(f10 / hold), seed);
  return h < pDeep ? 2 : (h < pDeep + pDim ? 1 : 0);
}

/* ---------------- one phase ---------------- */
function renderSeason(si, k, outIdx) {
  BG.fill(0); OB.fill(0);
  setOrigin(0, 0);
  sceneBack(si, k);
  if (typeof sceneObjects === 'function') sceneObjects(si, k);
  setOrigin(0, 0);
  if (typeof sceneAfterObjects === 'function') sceneAfterObjects(si, k);
  for (let i = 0; i < NPX; i++) IX[i] = OB[i] || BG[i];
  setOrigin(0, 0);
  if (typeof sceneFront === 'function') sceneFront(si, k);
  const D = DYN[outIdx], P = PHASE_PAL[si];
  D.set(P);
  if (typeof sceneDynamic === 'function') sceneDynamic(si, k, D, P);
  const out = RGB[outIdx];
  for (let i = 0; i < NPX; i++) out[i] = D[IX[i]];
}

/* ---------------- frame compositing ---------------- */
let FADE_T = null;
function fadeThreshold() {
  // ordered dither with a gentle diagonal lean so the next phase drifts in like weather
  const t = new Float32Array(NPX);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const b = (BAYER8[((y & 7) << 3) | (x & 7)] + 0.5) / 64;
    const lean = (x / W) * 0.6 + (y / H) * 0.4;
    t[y * W + x] = b * 0.82 + lean * 0.18;
  }
  return t;
}
// where are we in the cycle? (phase, blend toward the next, next phase)
function seasonAt(k) {
  const tc = (k % CYCLE_TICKS) / HZ;
  const seg = TIMELINE.seg;
  for (let i = 0; i < seg.length; i++) {
    const g = seg[i];
    if (tc < g.start + g.dur || i === seg.length - 1) {
      if (g.kind === 'season') return { si: g.s, f: 0, nx: (g.s + 1) % NPH };
      let f = Math.min(1, Math.max(0, (tc - g.start) / g.dur));
      f = f * f * (3 - 2 * f);
      return { si: g.s, f, nx: g.to };
    }
  }
  return { si: 0, f: 0, nx: 1 % NPH };
}
// phase-relative clock for timed events: seconds since that phase began
function seasonClock(k, s) {
  const tc = (k % CYCLE_TICKS) / HZ;
  const g = TIMELINE.seg[s * 2];
  return { t: tc - g.start, dur: g.dur };
}
function particles(si, k, dens, out, D) {
  if (typeof sceneParticles !== 'function' || dens <= 0.001) return;
  setOrigin(0, 0);
  sceneParticles(si, k, dens, out, D);
  setOrigin(0, 0);
}
function renderFrame(k, out32) {
  if (!FADE_T) FADE_T = fadeThreshold();
  const { si, f, nx } = seasonAt(k);
  renderSeason(si, k, 0);
  if (f <= 0) {
    out32.set(RGB[0]);
    particles(si, k, 1, out32, DYN[0]);
    return;
  }
  renderSeason(nx, k, 1);
  const A = RGB[0], B = RGB[1], T = FADE_T;
  const ff = f * 1.02;
  for (let i = 0; i < NPX; i++) out32[i] = T[i] < ff ? B[i] : A[i];
  particles(si, k, 1 - f, out32, DYN[0]);
  particles(nx, k, f, out32, DYN[1]);
}

/* particle helpers: write palette colours straight into the RGBA frame */
function put(out, D, x, y, slot) {
  x = Math.floor(x) + OX; y = Math.floor(y) + OY;
  if (x < 0 || y < 0 || x >= W || y >= H) return;
  out[y * W + x] = D[slot];
}
function putSpr(out, D, s, x, y, fi, flip) {
  if (!s) return;
  const d = s.f[(fi || 0) % s.f.length];
  x = Math.round(x + OX - (flip ? s.w - 1 - s.ax : s.ax)); y = Math.round(y + OY - s.ay);
  for (let j = 0; j < s.h; j++) {
    const Y = y + j; if (Y < 0 || Y >= H) continue;
    for (let i = 0; i < s.w; i++) {
      const v = d[j * s.w + (flip ? s.w - 1 - i : i)];
      if (!v) continue;
      const X = x + i; if (X < 0 || X >= W) continue;
      out[Y * W + X] = D[v];
    }
  }
}
// periodic particle clock: period in 15 Hz ticks (k >> 1); must divide TICKS / 2.
// returns [age within the period, generation index] (generation picks new random positions)
function pclock(k2, j, per, seed) {
  const off = Math.floor(hash2(j, seed) * per);
  const t = k2 + off;
  return [t % per, Math.floor(t / per) % (TICKS / 2 / per)];
}
