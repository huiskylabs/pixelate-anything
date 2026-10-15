/* ==========================================================================
   pixelate-anything engine: generative soundtrack (Web Audio API): lofi, chiptune, ambient.
   The music spec (chords, scales, tempo, instruments, ambience per phase, and
   the ii-V turnaround between phases) comes from the scene's music.js
   (global SCENE_MUSIC).
   Every instrument and ambience is synthesised once into buffers. A lookahead
   scheduler plays bars that are locked to the visual season cycle, so music
   and picture cross over together. Phrases, fills and voicings vary at random.
   ========================================================================== */
const LOFI = (() => {
  let ctx = null, SR = 48000;
  let off = 0;                       // visual time V = ctx time + off
  let master = null, musicSum = null, ambSum = null, verb = null;
  let muted = false, timer = 0, schedEnd = 0, started = false, vinylGain = null;
  const BUS = [];
  let BUF = {};
  let planCache = new Map();
  const state = SCENE.phases.map(() => ({}));

  /* ------------------------------------------------------------ dsp helpers */
  const mtof = m => 440 * Math.pow(2, (m - 69) / 12);
  // every random choice goes through urand(). A loop render swaps in a seeded stream,
  // re-keyed per segment by (cycle mod GRAND, segment), so the music repeats exactly
  // in step with the picture.
  let urand = () => Math.random();
  let LOOPED = false;
  function seedStream(x) {
    let a = Math.imul((x | 0) + 1, 0x9e3779b1) | 0;
    urand = () => {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const rnd = (a, b) => a + urand() * (b - a);
  const pick = a => a[Math.floor(urand() * a.length)];
  function onepoleLP(fc) { const a = 1 - Math.exp(-2 * Math.PI * fc / SR); let y = 0; return x => (y += a * (x - y)); }
  function biquad(type, f, Q) {
    const w0 = 2 * Math.PI * Math.min(f, SR * 0.45) / SR, cw = Math.cos(w0), sw = Math.sin(w0), al = sw / (2 * Q);
    let b0, b1, b2;
    if (type === 'lp') { b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = b0; }
    else if (type === 'hp') { b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = b0; }
    else { b0 = al; b1 = 0; b2 = -al; }
    const a0 = 1 + al, a1 = -2 * cw / a0, a2 = (1 - al) / a0;
    b0 /= a0; b1 /= a0; b2 /= a0;
    let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    return x => { const y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; };
  }
  function buf(chans) {
    const b = ctx.createBuffer(chans.length, chans[0].length, SR);
    chans.forEach((d, i) => b.copyToChannel(d, i));
    return b;
  }
  function norm(d, peak) {
    let m = 1e-9;
    for (let i = 0; i < d.length; i++) { const v = Math.abs(d[i]); if (v > m) m = v; }
    const g = peak / m;
    for (let i = 0; i < d.length; i++) d[i] *= g;
    return d;
  }
  function normPair(L, R, peak) {
    let m = 1e-9;
    for (let i = 0; i < L.length; i++) m = Math.max(m, Math.abs(L[i]), Math.abs(R[i]));
    const g = peak / m;
    for (let i = 0; i < L.length; i++) { L[i] *= g; R[i] *= g; }
  }
  function fadeOut(d, sec) {
    const n = Math.min(d.length, Math.floor(sec * SR));
    for (let i = 0; i < n; i++) d[d.length - 1 - i] *= i / n;
  }
  // loop without a seam: crossfade the extra tail into the head
  function seamless(d, fade) {
    const L = d.length - fade;
    const out = new Float32Array(L);
    out.set(d.subarray(0, L));
    for (let i = 0; i < fade; i++) {
      const t = i / fade;
      out[i] = d[i] * Math.sqrt(t) + d[L + i] * Math.sqrt(1 - t);
    }
    return out;
  }
  // lazily smoothed random walk in [0,1]
  function walk(rate, seedLo, seedHi) {
    let v = rnd(seedLo, seedHi), target = rnd(0, 1), cnt = 0;
    const a = 1 - Math.exp(-1 / (rate * SR));
    return () => {
      if (--cnt <= 0) { target = urand(); cnt = Math.floor(rate * SR * rnd(0.6, 1.4)); }
      return (v += a * (target - v));
    };
  }

  /* ------------------------------------------------------------ instruments */
  function rhodes(m) {
    const f = mtof(m), n = Math.floor(3.4 * SR);
    const L = new Float32Array(n), R = new Float32Array(n);
    const pk = Math.max(0.5, 1 - (m - 60) * 0.02);
    const w = 2 * Math.PI * f / SR, wR = w * 1.0012, wt = w * 7.02;
    let e1 = 1, e2 = 1, ie = 1, te = 1, ph = 0, phR = 0, pt = 0;
    const k1 = Math.exp(-1 / (0.55 * pk * SR)), k2 = Math.exp(-1 / (2.5 * pk * SR));
    const ki = Math.exp(-1 / (0.3 * SR)), kt = Math.exp(-1 / (0.03 * SR)), att = 0.003 * SR;
    const lpL = onepoleLP(4800), lpR = onepoleLP(4800);
    for (let i = 0; i < n; i++) {
      const a = i < att ? i / att : 1;
      const env = (0.55 * e1 + 0.45 * e2) * a;
      const idx = 0.16 + 1.5 * ie;
      const tine = 0.09 * te * Math.sin(pt);
      L[i] = lpL((Math.sin(ph + idx * Math.sin(ph)) + tine) * env);
      R[i] = lpR((Math.sin(phR + idx * Math.sin(phR)) + tine) * env);
      ph += w; phR += wR; pt += wt; e1 *= k1; e2 *= k2; ie *= ki; te *= kt;
    }
    fadeOut(L, 0.2); fadeOut(R, 0.2);
    normPair(L, R, 0.8);
    return buf([L, R]);
  }
  function guitar(m) {
    const f = mtof(m), n = Math.floor(3.2 * SR), out = new Float32Array(n);
    const N = SR / f, Ld = Math.floor(N - 0.5), frac = N - 0.5 - Ld, C = (1 - frac) / (1 + frac);
    const line = new Float32Array(Ld);
    const lp = onepoleLP(1800 + (m - 45) * 45);
    let mean = 0;
    for (let i = 0; i < Ld; i++) { line[i] = lp(urand() * 2 - 1); mean += line[i]; }
    mean /= Ld;
    const tmp = new Float32Array(Ld);
    for (let i = 0; i < Ld; i++) tmp[i] = line[i] - mean;
    const pp = Math.max(1, Math.floor(Ld * 0.17));
    for (let i = 0; i < Ld; i++) line[i] = tmp[i] - 0.55 * tmp[(i + pp) % Ld];
    const T60 = 2.4 * Math.max(0.45, 1 - (m - 48) * 0.014);
    const g = Math.pow(10, -3 / (T60 * f));
    let p = 0, prev = 0, ax = 0, ay = 0;
    for (let i = 0; i < n; i++) {
      const cur = line[p];
      const avg = 0.5 * (cur + prev);
      const ap = C * avg + ax - C * ay; ax = avg; ay = ap;
      line[p] = ap * g; prev = cur; out[i] = cur;
      if (++p >= Ld) p = 0;
    }
    const lp2 = onepoleLP(3000), body = biquad('bp', 190, 1.1);
    for (let i = 0; i < n; i++) { const x = out[i]; out[i] = lp2(x) + 0.3 * body(x); }
    fadeOut(out, 0.15);
    return buf([norm(out, 0.85)]);
  }
  function piano(m) {
    const f = mtof(m), n = Math.floor(3.0 * SR), out = new Float32Array(n);
    const parts = [];
    for (let k = 1; k <= 8; k++) {
      const fk = k * f * Math.sqrt(1 + 0.00025 * k * k);
      if (fk > SR * 0.4) break;
      const amp = Math.pow(k, -1.25) * Math.exp(-(k - 1) * 0.45);
      const tau = 2.6 * Math.max(0.35, 1 - (m - 48) * 0.012) / (1 + 0.6 * (k - 1));
      for (const det of [-0.00035, 0.00035]) {
        const w = 2 * Math.PI * fk * (1 + det) / SR;
        parts.push([Math.cos(w), Math.sin(w), 1, 0, amp * 0.5, Math.exp(-1 / (tau * SR))]);
      }
    }
    for (let i = 0; i < n; i++) {
      let s = 0;
      for (let j = 0; j < parts.length; j++) {
        const p = parts[j];
        const nx = p[2] * p[0] - p[3] * p[1];
        p[3] = p[3] * p[0] + p[2] * p[1]; p[2] = nx;
        s += p[3] * p[4]; p[4] *= p[5];
      }
      out[i] = s;
    }
    const att = Math.floor(0.005 * SR);
    for (let i = 0; i < att; i++) out[i] *= i / att;
    const lh = onepoleLP(1100);
    let he = 0.06;
    const hk = Math.exp(-1 / (0.01 * SR));
    for (let i = 0; i < 0.06 * SR; i++) { out[i] += lh(urand() * 2 - 1) * he; he *= hk; }
    const felt = onepoleLP(1700), felt2 = onepoleLP(2600);
    for (let i = 0; i < n; i++) out[i] = felt(felt2(out[i]));
    fadeOut(out, 0.25);
    return buf([norm(out, 0.85)]);
  }
  function musicbox(m) {
    const f = mtof(m), n = Math.floor(3.2 * SR), out = new Float32Array(n);
    const modes = [[1, 1, 1.7], [2.0, 0.035, 0.7], [3.01, 0.05, 0.45], [6.27, 0.2, 0.11], [8.9, 0.05, 0.05]];
    const ps = modes.filter(md => md[0] * f < SR * 0.42).map(([r, a, t]) => {
      const w = 2 * Math.PI * f * r * (1 + rnd(-0.0006, 0.0006)) / SR;
      return [Math.cos(w), Math.sin(w), 1, 0, a, Math.exp(-1 / (t * SR))];
    });
    for (let i = 0; i < n; i++) {
      let s = 0;
      for (const p of ps) {
        const nx = p[2] * p[0] - p[3] * p[1];
        p[3] = p[3] * p[0] + p[2] * p[1]; p[2] = nx;
        s += p[3] * p[4]; p[4] *= p[5];
      }
      out[i] = s;
    }
    const hp = biquad('hp', 2500, 0.7);
    let ce = 0.12;
    for (let i = 0; i < 0.004 * SR; i++) { out[i] += hp(urand() * 2 - 1) * ce; ce *= 0.995; }
    const lp = onepoleLP(7000);
    for (let i = 0; i < n; i++) out[i] = lp(out[i]);
    fadeOut(out, 0.3);
    return buf([norm(out, 0.8)]);
  }
  function bass(m) {
    const f = mtof(m), n = Math.floor(2.4 * SR), out = new Float32Array(n);
    const w = 2 * Math.PI * f / SR;
    let e = 1, ph = 0;
    const k = Math.exp(-1 / (1.2 * SR)), att = 0.01 * SR;
    const lp = onepoleLP(520);
    for (let i = 0; i < n; i++) {
      const a = i < att ? i / att : 1;
      const x = Math.sin(ph) + 0.34 * Math.sin(2 * ph) + 0.11 * Math.sin(3 * ph);
      out[i] = lp(Math.tanh(x * 1.1) * e * a);
      ph += w; e *= k;
    }
    fadeOut(out, 0.2);
    return buf([norm(out, 0.9)]);
  }

  /* ------------------------------------------------------------ chiptune voices */
  // NES-style: pulse waves with a stepped 4-bit volume, a 32-step triangle, LFSR noise drums
  function pulseWave(m, duty, dur) {
    const f = mtof(m), n = Math.floor(dur * SR), out = new Float32Array(n);
    const lp = onepoleLP(11000);
    let ph = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const vib = t > 0.22 ? 1 + 0.004 * Math.sin(2 * Math.PI * 5.5 * (t - 0.22)) : 1;
      ph += f * vib / SR; if (ph >= 1) ph -= 1;
      const env = (t < 0.004 ? t / 0.004 : Math.max(0.35, 1 - (t - 0.004) * 1.8)) * Math.max(0, Math.min(1, (dur - t) / 0.12));
      out[i] = lp((ph < duty ? 1 : -1) * Math.round(env * 15) / 15);
    }
    return buf([norm(out, 0.7)]);
  }
  const pulse = m => pulseWave(m, 0.25, 1.6);
  const pulse2 = m => pulseWave(m, 0.125, 0.9);
  function tri(m) {
    const f = mtof(m), n = Math.floor(2.4 * SR), out = new Float32Array(n);
    let ph = 0;
    for (let i = 0; i < n; i++) {
      ph += f / SR; if (ph >= 1) ph -= 1;
      const step = Math.floor(ph * 32), v = step < 16 ? step : 31 - step;   // 32-step triangle
      out[i] = (v / 7.5 - 1) * Math.min(1, i / (0.002 * SR));
    }
    fadeOut(out, 0.05);
    return buf([norm(out, 0.9)]);
  }
  function lfsrNoise(n, hold, short) {          // a 15-bit LFSR, each value held `hold` samples
    const out = new Float32Array(n);
    let reg = 1, v = 1, c = 0;
    for (let i = 0; i < n; i++) {
      if (c-- <= 0) { const b = (reg ^ (reg >> (short ? 6 : 1))) & 1; reg = (reg >> 1) | (b << 14); v = (reg & 1) ? 1 : -1; c = hold; }
      out[i] = v;
    }
    return out;
  }
  function ckick(v) {
    const n = Math.floor(0.22 * SR), out = new Float32Array(n);
    let ph = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR, f = 45 + 140 * Math.exp(-t / (0.025 + v * 0.004));
      ph += f / SR; if (ph >= 1) ph -= 1;
      const step = Math.floor(ph * 32), tv = (step < 16 ? step : 31 - step) / 7.5 - 1;
      out[i] = tv * Math.round(Math.exp(-t / 0.09) * 15) / 15;
    }
    return buf([norm(out, 0.95)]);
  }
  function csnare(v) {
    const n = Math.floor(0.2 * SR), nz = lfsrNoise(n, Math.round(SR / (9000 + v * 800)), false), out = new Float32Array(n);
    for (let i = 0; i < n; i++) out[i] = nz[i] * Math.round(Math.exp(-i / SR / (0.06 + v * 0.01)) * 15) / 15;
    return buf([norm(out, 0.8)]);
  }
  function chat(v) {
    const n = Math.floor(0.06 * SR), nz = lfsrNoise(n, Math.max(1, Math.round(SR / (22000 + v * 3000))), v === 2), out = new Float32Array(n);
    for (let i = 0; i < n; i++) out[i] = nz[i] * Math.round(Math.exp(-i / SR / 0.018) * 15) / 15;
    return buf([norm(out, 0.6)]);
  }

  /* ------------------------------------------------------------ drums */
  function kick(v) {
    const n = Math.floor(0.55 * SR), out = new Float32Array(n);
    let ph = 0;
    const lp = onepoleLP(900 + v * 150);
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const f = 46 + 72 * Math.exp(-t / (0.032 + v * 0.004));
      ph += 2 * Math.PI * f / SR;
      const env = Math.exp(-t / (0.2 + v * 0.03)) * Math.min(1, t / 0.0015);
      const click = (urand() * 2 - 1) * Math.exp(-t / 0.0025) * 0.18;
      out[i] = Math.tanh(1.6 * (Math.sin(ph) * env + lp(click))) / Math.tanh(1.6);
    }
    return buf([norm(out, 0.95)]);
  }
  function snare(v) {
    const n = Math.floor(0.4 * SR), out = new Float32Array(n);
    const bp = biquad('bp', 1700 + v * 200, 0.75), lp = onepoleLP(5200);
    let ph = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      ph += 2 * Math.PI * (178 + 30 * Math.exp(-t / 0.02)) / SR;
      const body = Math.sin(ph) * Math.exp(-t / 0.055) * 0.55;
      const nz = bp(urand() * 2 - 1) * Math.exp(-t / (0.12 + v * 0.02)) * 1.6;
      out[i] = lp(body + nz) * Math.min(1, t / 0.001);
    }
    norm(out, 1);
    for (let i = 0; i < n; i++) out[i] = Math.tanh(2.6 * out[i]) / Math.tanh(2.6);
    return buf([norm(out, 0.9)]);
  }
  function rim(v) {
    const n = Math.floor(0.12 * SR), out = new Float32Array(n);
    const bp = biquad('bp', 2400 + v * 300, 2.5);
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      out[i] = bp(urand() * 2 - 1) * Math.exp(-t / 0.012) * 2 + Math.sin(2 * Math.PI * 1650 * t) * Math.exp(-t / 0.018) * 0.4;
    }
    return buf([norm(out, 0.8)]);
  }
  function hat(v, open) {
    const n = Math.floor((open ? 0.45 : 0.12) * SR), out = new Float32Array(n);
    const hp = biquad('hp', 7200 + v * 400, 0.8), lp = onepoleLP(10500);
    const tau = open ? 0.17 : 0.025 + v * 0.006;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      out[i] = lp(hp(urand() * 2 - 1)) * Math.exp(-t / tau) * Math.min(1, t / 0.0008);
    }
    norm(out, 1);
    for (let i = 0; i < n; i++) out[i] = Math.tanh(2.2 * out[i]) / Math.tanh(2.2);
    return buf([norm(out, 0.7)]);
  }
  function shaker(v) {
    const n = Math.floor(0.14 * SR), out = new Float32Array(n);
    const bp = biquad('bp', 6200 + v * 500, 1.4);
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      out[i] = bp(urand() * 2 - 1) * Math.min(1, t / 0.012) * Math.exp(-t / 0.045);
    }
    return buf([norm(out, 0.6)]);
  }
  function brush(v) {
    const n = Math.floor(0.3 * SR), out = new Float32Array(n);
    const bp = biquad('bp', 2800 + v * 300, 0.9), lp = onepoleLP(6000);
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      out[i] = lp(bp(urand() * 2 - 1)) * Math.min(1, t / 0.014) * Math.exp(-t / 0.09);
    }
    return buf([norm(out, 0.75)]);
  }

  /* ------------------------------------------------------------ ambience loops */
  // every continuous loop must fit a whole number of times into the picture loop
  // (CYCLE * GRAND seconds, in samples), so a loop render lands back in phase
  const LOOPSEC = CYCLE * GRAND;
  function loopSamples(sec) {
    const total = LOOPSEC * SR, n0 = Math.max(1, Math.round(LOOPSEC / sec));
    for (let d = 0; d < n0; d++) for (const n of [n0 + d, n0 - d]) if (n >= 1 && total % n === 0) return total / n;
    return Math.floor(sec * SR);
  }
  function loopHz(f) { return Math.max(1, Math.round(f * LOOPSEC)) / LOOPSEC; }
  function stereoLoop(sec, gen, fadeSec) {
    const fade = Math.floor((fadeSec || 1.2) * SR), n = loopSamples(sec) + fade;
    const L = new Float32Array(n), R = new Float32Array(n);
    gen(L, 0); gen(R, 1);
    const a = seamless(L, fade), b = seamless(R, fade);
    normPair(a, b, 0.8);
    return buf([a, b]);
  }
  function sprinkle(d, rate, fn) {
    let t = 0;
    for (;;) {
      t += -Math.log(1 - urand()) / rate;
      const i = Math.floor(t * SR);
      if (i >= d.length) break;
      fn(d, i);
    }
  }
  function drop(d, i, f, amp, dec) {
    const n = Math.floor(dec * 6 * SR), w = 2 * Math.PI * f / SR;
    for (let j = 0; j < n && i + j < d.length; j++) d[i + j] += Math.sin(w * j * (1 - j / (n * 3))) * amp * Math.exp(-j / (dec * SR));
  }
  function burst(d, i, f, q, amp, dec) {
    const bp = biquad('bp', f, q), n = Math.floor(dec * 6 * SR);
    for (let j = 0; j < n && i + j < d.length; j++) d[i + j] += bp(urand() * 2 - 1) * amp * Math.exp(-j / (dec * SR));
  }
  const AMB = {
    rain: () => stereoLoop(18, (d) => {
      const hp = biquad('hp', 450, 0.7), lp = biquad('lp', 5200, 0.6), lo = onepoleLP(700), gust = walk(2.5, 0.4, 0.7);
      for (let i = 0; i < d.length; i++) {
        const x = urand() * 2 - 1;
        d[i] = lp(hp(x)) * 0.22 * (0.7 + 0.5 * gust()) + lo(x) * 0.05;
      }
      sprinkle(d, 70, (a, i) => drop(a, i, rnd(2600, 6200), rnd(0.02, 0.09), 0.0012));
      sprinkle(d, 4, (a, i) => drop(a, i, rnd(1100, 2400), rnd(0.12, 0.28), 0.003));
    }),
    waves: () => stereoLoop(24, (d, ch) => {
      const lp = biquad('lp', 620, 0.6), hp = biquad('hp', 1500, 0.7), lp2 = onepoleLP(4200);
      const env = new Float32Array(d.length);
      let t = rnd(0, 2) + ch * 0.4;
      while (t * SR < d.length) {
        const a = rnd(0.5, 1), up = rnd(1.4, 2.2), down = rnd(2.8, 4.2);
        const i0 = Math.floor(t * SR);
        for (let j = 0; j < (up + down) * SR && i0 + j < env.length; j++) {
          const s = j / SR;
          const e = s < up ? Math.pow(Math.sin(s / up * Math.PI / 2), 2) : Math.exp(-(s - up) / (down * 0.45));
          env[i0 + j] += a * e;
        }
        t += rnd(4.5, 7.5);
      }
      let br = 0;
      for (let i = 0; i < d.length; i++) {
        const x = urand() * 2 - 1;
        br = br * 0.985 + x * 0.06;
        const e = Math.min(1.3, env[i]);
        d[i] = lp(br) * (0.35 + 0.65 * e) + lp2(hp(x)) * e * e * 0.07;
      }
    }),
    cicadas: () => stereoLoop(15, (d, ch) => {
      const bp = biquad('bp', 4900 + ch * 220, 5);
      const f1 = 4550 + ch * 90, f2 = 5300 - ch * 70, am1 = 41 + ch * 3, am2 = 47 - ch * 2;
      const per1 = 6.5 + ch, per2 = 9.2 - ch * 0.7;
      for (let i = 0; i < d.length; i++) {
        const t = i / SR;
        const s1 = 0.5 - 0.5 * Math.cos(2 * Math.PI * t / per1), s2 = 0.5 - 0.5 * Math.cos(2 * Math.PI * t / per2 + 1.3);
        const a1 = Math.pow(0.5 + 0.5 * Math.sin(2 * Math.PI * am1 * t), 3), a2 = Math.pow(0.5 + 0.5 * Math.sin(2 * Math.PI * am2 * t), 3);
        const nz = bp(urand() * 2 - 1) * 0.5;
        d[i] = (Math.sin(2 * Math.PI * f1 * t) * 0.35 + nz) * a1 * (0.15 + 0.85 * s1) * 0.5
             + Math.sin(2 * Math.PI * f2 * t) * a2 * (0.1 + 0.9 * s2) * 0.22;
      }
      // a cricket keeps time underneath
      let t = rnd(0, 1);
      while (t * SR < d.length) {
        for (let p = 0; p < 3; p++) {
          const i0 = Math.floor((t + p * 0.038) * SR);
          for (let j = 0; j < 0.014 * SR && i0 + j < d.length; j++)
            d[i0 + j] += Math.sin(2 * Math.PI * 4150 * j / SR) * Math.sin(Math.PI * j / (0.014 * SR)) * 0.22;
        }
        t += rnd(0.9, 1.3);
      }
    }),
    wind: () => stereoLoop(20, (d, ch) => {
      const gust = walk(1.8, 0.2, 0.6), lp = onepoleLP(1400), bp = varBP(0.8);
      let g = 0.4;
      for (let i = 0; i < d.length; i++) {
        g = gust();
        if ((i & 63) === 0) bp.set(260 + g * 520);
        d[i] = lp(bp.run(urand() * 2 - 1)) * (0.25 + 0.9 * g * g);
      }
    }, 1.6),
    leaves: () => stereoLoop(15, (d) => {
      const gust = walk(1.4, 0.2, 0.6), env = new Float32Array(d.length);
      for (let i = 0; i < d.length; i++) env[i] = gust();
      let t = 0;
      for (;;) {
        const i = Math.floor(t * SR);
        if (i >= d.length) break;
        const e = env[i];
        burst(d, i, rnd(2500, 6500), 1.2, rnd(0.03, 0.16) * (0.2 + e), rnd(0.003, 0.012));
        t += -Math.log(1 - urand()) / (12 + 70 * e * e);
      }
    }),
    fire: () => stereoLoop(18, (d) => {
      const lo = onepoleLP(140), hp = biquad('hp', 3800, 0.7), fl = walk(0.4, 0.4, 0.8);
      for (let i = 0; i < d.length; i++) {
        const x = urand() * 2 - 1;
        d[i] = lo(x) * 0.9 * (0.6 + 0.6 * fl()) + hp(x) * 0.012;
      }
      sprinkle(d, 4.5, (a, i) => burst(a, i, rnd(700, 3200), 1.5, Math.pow(urand(), 2.2) * 0.9 + 0.05, rnd(0.003, 0.014)));
      sprinkle(d, 26, (a, i) => burst(a, i, rnd(1800, 5000), 2, rnd(0.01, 0.06), 0.0015));
    }),
    vinyl: () => stereoLoop(12, (d) => {
      const hp = biquad('hp', 2600, 0.7), lp = onepoleLP(8500);
      for (let i = 0; i < d.length; i++) d[i] = lp(hp(urand() * 2 - 1)) * 0.02;
      sprinkle(d, 9, (a, i) => burst(a, i, rnd(1500, 5000), 0.9, Math.pow(urand(), 3) * 0.35 + 0.02, 0.0007));
      sprinkle(d, 0.3, (a, i) => burst(a, i, rnd(500, 1500), 0.8, 0.35, 0.002));
    })
  };
  // band-pass whose centre can move without resetting its state
  function varBP(Q) {
    let b0 = 0, b2 = 0, a1 = 0, a2 = 0, x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    return {
      set(f) {
        const w0 = 2 * Math.PI * f / SR, cw = Math.cos(w0), al = Math.sin(w0) / (2 * Q), a0 = 1 + al;
        b0 = al / a0; b2 = -al / a0; a1 = -2 * cw / a0; a2 = (1 - al) / a0;
      },
      run(x) { const y = b0 * x + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; }
    };
  }

  /* ------------------------------------------------------------ the scene's music */
  // styles fill in defaults; anything the phase sets itself wins
  const STYLE = {
    chiptune: { swing: 0, lead: 'pulse', comp: 'arp', arpInst: 'pulse2', bass: 'tri', bassMode: 'octaves', kit: 'chip',
      snd: 'csnare', hats: 8, shaker: 0, amb: [], kick: [[0, 0.9], [8, 0.8]], snare: [[4, 0.7], [12, 0.7]] },
    ambient: { drums: false, bassMode: 'drone', comp: 'pad', hats: 0, shaker: 0, kick: [], snare: [], mel: 0.5 }
  };
  const MUSIC = SCENE_MUSIC.phases.map(M => (M.style && STYLE[M.style] ? Object.assign({}, STYLE[M.style], M) : M));
  const TRANS = SCENE_MUSIC.trans;
  if (MUSIC.length !== NPH || TRANS.length !== NPH) throw new Error('pixelate-anything: SCENE_MUSIC needs one phase and one trans entry per phase');
  MUSIC.forEach((M, s) => { M.bpm = TIMELINE.bpm[s]; M.spb = 60 / M.bpm; });

  const CORE = NPH;                    // drums, bass and the riser: never crossfaded
  const LEVEL = { kick: 0.7, snare: 1.0, brush: 1.6, rim: 1.4, hat: 0.75, ohat: 0.4, shaker: 0.7, bass: 0.48,
    rhodes: 0.34, guitar: 0.75, piano: 0.4, musicbox: 0.3, pad: 0.075, riser: 0.14,
    pulse: 0.16, pulse2: 0.09, tri: 0.5, ckick: 0.75, csnare: 0.42, chat: 0.26 };
  const LEAD_BOOST = 1.7;
  const MASTER = 0.72;
  const SEND = { rhodes: 0.28, guitar: 0.22, piano: 0.32, musicbox: 0.55, pad: 0.45, snare: 0.08, brush: 0.12, rim: 0.12, riser: 0.3,
    pulse: 0.1, pulse2: 0.08 };
  // texture: vinyl crackle level and tape wobble; chiptune-only scores default to neither
  const ALLCHIP = MUSIC.every(M => M.kit === 'chip');
  const TEX = Object.assign({ vinyl: ALLCHIP ? 0 : 0.4, tape: !ALLCHIP }, SCENE_MUSIC.texture || {});
  const dn = (M, name) => (M.kit === 'chip' ? ({ kick: 'ckick', hat: 'chat', ohat: 'chat', shaker: 'chat' }[name] || name) : name);

  /* ------------------------------------------------------------ asset generation */
  function notesFor(s) {
    const M = MUSIC[s], set = new Set();
    const voicings = M.chords.map(c => c[1]).concat([TRANS[s].pre[1], TRANS[s].dom[1],
      TRANS[(s + NPH - 1) % NPH].pre[1], TRANS[(s + NPH - 1) % NPH].dom[1]]);
    const mb = M.lead === 'musicbox' || (M.comp === 'pad' && (M.padVoice || 'musicbox') === 'musicbox');
    for (const v of voicings) v.forEach(n => { set.add(n); set.add(n + 12); if (mb) set.add(n + 24); });
    M.scale.forEach(n => set.add(n));
    return [...set];
  }
  const INST = { rhodes, guitar, piano, musicbox, pulse, pulse2 };
  function jobsFor(si) {
    const M = MUSIC[si], jobs = [];
    const insts = [M.lead, M.comp, M.comp === 'pad' ? (M.padVoice || 'musicbox') : null, M.comp === 'arp' ? (M.arpInst || 'pulse2') : null];
    [...new Set(insts)].forEach(inst => { if (INST[inst]) notesFor(si).forEach(m => jobs.push([inst + m, () => INST[inst](m)])); });
    const bs = new Set();
    M.chords.forEach(([b]) => { [b, b + 7, b + 12, b - 1, b + 1, b - 2, b + 2].forEach(x => bs.add(x)); });
    for (const T of [TRANS[si], TRANS[(si + NPH - 1) % NPH]]) [T.pre[0], T.dom[0], T.approach].forEach(x => bs.add(x));
    const bI = M.bass || 'bass';
    bs.forEach(m => { jobs.push([bI + m, () => (bI === 'tri' ? tri(m) : bass(m))]); if (M.bassMode === 'octaves') jobs.push([bI + (m + 12), () => (bI === 'tri' ? tri(m + 12) : bass(m + 12))]); });
    M.amb.forEach(([a]) => jobs.push(['amb_' + a, AMB[a]]));
    return jobs;
  }
  // a soft filtered-noise swell that peaks on the next season's downbeat
  function riser() {
    const n = Math.floor(3.0 * SR), L = new Float32Array(n), R = new Float32Array(n);
    for (const [d, seed] of [[L, 0], [R, 1]]) {
      const bp = varBP(1.4);
      for (let i = 0; i < n; i++) {
        const u = i / n;
        if ((i & 31) === 0) bp.set(380 * Math.pow(14, u) + seed * 40);
        const env = Math.pow(u, 2.2) * (u > 0.94 ? (1 - u) / 0.06 : 1);
        d[i] = bp.run(urand() * 2 - 1) * env;
      }
    }
    normPair(L, R, 0.7);
    return buf([L, R]);
  }
  function commonJobs() {
    const jobs = [];
    for (let v = 0; v < 3; v++) {
      jobs.push(['kick' + v, () => kick(v)], ['snare' + v, () => snare(v)], ['rim' + v, () => rim(v)],
        ['hat' + v, () => hat(v, false)], ['shaker' + v, () => shaker(v)], ['brush' + v, () => brush(v)]);
    }
    jobs.push(['ohat', () => hat(1, true)], ['amb_vinyl', AMB.vinyl], ['riser', riser]);
    if (MUSIC.some(M => M.kit === 'chip'))
      for (let v = 0; v < 3; v++) jobs.push(['ckick' + v, () => ckick(v)], ['csnare' + v, () => csnare(v)], ['chat' + v, () => chat(v)]);
    return jobs;
  }
  async function runJobs(jobs, yieldEvery) {
    let t0 = performance.now();
    for (const [name, fn] of jobs) {
      if (BUF[name]) continue;
      BUF[name] = fn();
      if (yieldEvery && performance.now() - t0 > yieldEvery) {
        await new Promise(r => setTimeout(r, 0));
        t0 = performance.now();
      }
    }
  }

  /* ------------------------------------------------------------ graph */
  function impulse(sec) {
    const n = Math.floor(sec * SR), L = new Float32Array(n), R = new Float32Array(n);
    for (const d of [L, R]) {
      const lp = onepoleLP(5200);
      for (let i = 0; i < n; i++) {
        const t = i / SR;
        d[i] = lp(urand() * 2 - 1) * Math.exp(-t / 0.55) * Math.min(1, t / 0.012);
      }
      for (let e = 0; e < 7; e++) { const i = Math.floor(rnd(0.008, 0.07) * SR); d[i] += rnd(-0.6, 0.6); }
    }
    normPair(L, R, 0.5);
    return buf([L, R]);
  }
  function makeBus(gain) {
    const dry = ctx.createGain();
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 30; hp.Q.value = 0.6;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 16000; lp.Q.value = 0.6;
    const out = ctx.createGain(); out.gain.value = gain;
    dry.connect(hp).connect(lp).connect(out).connect(musicSum);
    const vin = ctx.createGain(), vout = ctx.createGain(); vout.gain.value = gain;
    vin.connect(vout).connect(verb);
    const amb = ctx.createGain(); amb.gain.value = 0;
    amb.connect(ambSum);
    const pans = [-0.45, -0.2, 0, 0.2, 0.45].map(p => {
      const n = ctx.createStereoPanner(); n.pan.value = p; n.connect(dry); return n;
    });
    const sends = {};
    for (const k in SEND) { const g = ctx.createGain(); g.gain.value = SEND[k]; g.connect(vin); sends[k] = g; }
    return { dry, hp, lp, out, vin, vout, amb, pans, sends, ambSrc: [] };
  }
  function buildGraph(dest) {
    master = ctx.createGain(); master.gain.value = 0;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -16; comp.knee.value = 10; comp.ratio.value = 2.5;
    comp.attack.value = 0.012; comp.release.value = 0.3;
    musicSum = ctx.createGain(); musicSum.gain.value = 0.9;
    // tape: slow wow and a little flutter on the music only
    const tape = ctx.createDelay(0.05); tape.delayTime.value = 0.012;
    const wow = ctx.createOscillator(); wow.frequency.value = loopHz(0.425);  // whole turns per picture loop
    const wowG = ctx.createGain(); wowG.gain.value = TEX.tape ? 0.0016 : 0;
    const flu = ctx.createOscillator(); flu.frequency.value = loopHz(5.3);
    const fluG = ctx.createGain(); fluG.gain.value = TEX.tape ? 0.00009 : 0;
    wow.connect(wowG).connect(tape.delayTime); flu.connect(fluG).connect(tape.delayTime);
    wow.start(); flu.start();
    const tone = ctx.createBiquadFilter(); tone.type = 'lowpass'; tone.frequency.value = 9000; tone.Q.value = 0.5;
    const lowcut = ctx.createBiquadFilter(); lowcut.type = 'highpass'; lowcut.frequency.value = 32;
    musicSum.connect(tape).connect(tone).connect(lowcut).connect(comp).connect(master);
    verb = ctx.createConvolver(); verb.buffer = impulse(2.6);
    const verbG = ctx.createGain(); verbG.gain.value = 0.8;
    verb.connect(verbG).connect(musicSum);
    ambSum = ctx.createGain(); ambSum.gain.value = 0.8;
    const ambLP = ctx.createBiquadFilter(); ambLP.type = 'lowpass'; ambLP.frequency.value = 11000;
    ambSum.connect(ambLP).connect(master);
    const lim = ctx.createDynamicsCompressor();
    lim.threshold.value = -2.5; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = 0.002; lim.release.value = 0.12;
    master.connect(lim).connect(dest);
    BUS.length = 0;
    for (let s = 0; s < NPH; s++) BUS.push(makeBus(0));
    BUS.push(makeBus(1));               // CORE: the groove that carries through every season
    // vinyl bed under everything
    const vs = ctx.createBufferSource(); vs.buffer = BUF.amb_vinyl; vs.loop = true;
    const vg = ctx.createGain(); vg.gain.value = TEX.vinyl;
    vs.connect(vg).connect(master); vs.start();
    vinylGain = vg;
  }
  function startAmbience(s, when) {
    const B = BUS[s];
    if (B.ambSrc.length) return;
    for (const [name, lev] of MUSIC[s].amb) {
      const b = BUF['amb_' + name];
      if (!b) continue;
      const src = ctx.createBufferSource(); src.buffer = b; src.loop = true;
      const g = ctx.createGain(); g.gain.value = lev;
      src.connect(g).connect(B.amb);
      src.start(when, urand() * b.duration);
      B.ambSrc.push(src);
    }
  }

  /* ------------------------------------------------------------ crossfade envelopes */
  // per season bus: segments [t0, t1, v0, v1, exponential?] in cycle time (may start < 0)
  const SEG = TIMELINE.seg;
  const ENVS = MUSIC.map((_, s) => {
    if (NPH === 1) return {           // one phase: no crossfade, the bus stays open
      gain: [[0, CYCLE, 1, 1]], lp: [[0, CYCLE, 16000, 16000, 1]], hp: [[0, CYCLE, 30, 30, 1]] };
    const tin = SEG[(2 * s + 2 * NPH - 1) % (2 * NPH)], tout = SEG[2 * s + 1];
    const inStart = s === 0 ? tin.start - CYCLE : tin.start, inEnd = SEG[2 * s].start;
    const outStart = tout.start, outEnd = tout.start + tout.dur;
    const next = inStart + CYCLE;
    return {
      gain: [[inStart, inEnd, 0, 1], [inEnd, outStart, 1, 1], [outStart, outEnd, 1, 0], [outEnd, next, 0, 0]],
      lp: [[inStart, outStart, 16000, 16000, 1], [outStart, outEnd, 16000, 1300, 1], [outEnd, next, 1300, 1300, 1]],
      hp: [[inStart, inEnd, 650, 30, 1], [inEnd, next, 30, 30, 1]]
    };
  });
  function envParams(s) {
    const B = BUS[s];
    return [[ENVS[s].gain, [B.out.gain, B.vout.gain, B.amb.gain]], [ENVS[s].lp, [B.lp.frequency]], [ENVS[s].hp, [B.hp.frequency]]];
  }
  function segValue(sg, T) {
    const u = Math.min(1, Math.max(0, (T - sg[0]) / (sg[1] - sg[0])));
    return sg[4] ? sg[2] * Math.pow(sg[3] / sg[2], u) : sg[2] + (sg[3] - sg[2]) * u;
  }
  function scheduleEnvs(V0, V1) {
    const n0 = Math.floor(V0 / CYCLE) - 1, n1 = Math.floor(V1 / CYCLE) + 1;
    for (let s = 0; s < NPH; s++) {
      for (const [segs, params] of envParams(s)) {
        for (let n = n0; n <= n1; n++) {
          for (const sg of segs) {
            const T0 = n * CYCLE + sg[0];
            if (T0 < V0 || T0 >= V1) continue;
            const T1 = n * CYCLE + sg[1];
            for (const p of params) {
              p.setValueAtTime(sg[2], T0 - off);
              if (sg[4]) p.exponentialRampToValueAtTime(sg[3], T1 - off);
              else p.linearRampToValueAtTime(sg[3], T1 - off);
            }
          }
        }
      }
    }
  }
  // at start: put every envelope where it should be now, and finish its current ramp
  function primeEnvs(V, t) {
    const n = Math.floor(V / CYCLE);
    for (let s = 0; s < NPH; s++) {
      for (const [segs, params] of envParams(s)) {
        for (const m of [n - 1, n, n + 1]) {
          for (const sg of segs) {
            const T0 = m * CYCLE + sg[0], T1 = m * CYCLE + sg[1];
            if (V < T0 || V >= T1) continue;
            const v = segValue(sg, V - m * CYCLE);
            for (const p of params) {
              p.cancelScheduledValues(t);
              p.setValueAtTime(v, t);
              if (sg[4]) p.exponentialRampToValueAtTime(sg[3], T1 - off);
              else p.linearRampToValueAtTime(sg[3], T1 - off);
            }
          }
        }
      }
    }
  }

  /* ------------------------------------------------------------ plans */
  // events carry a beat position inside their segment; the segment's tempo map
  // (steady, or ramping across a transition) turns beats into seconds.
  function nearestTone(m, tones, lo, hi) {
    let best = m, bd = 99;
    for (const t of tones) for (let o = -24; o <= 36; o += 12) {
      const c = t + o, d = Math.abs(c - m);
      if (c < lo || c > hi) continue;
      if (d < bd) { bd = d; best = c; }
    }
    return best;
  }
  const RHYTHMS = [
    [2, 6, 8, 14, 18, 22], [0, 3, 6, 10, 12, 20, 24], [4, 7, 10, 18, 20, 26], [8, 10, 11, 14, 22, 24, 27],
    [1, 4, 6, 12, 17, 20, 28], [6, 8, 12, 14, 24], [0, 2, 4, 10, 16, 18, 22, 26], [3, 10, 14, 19, 26]
  ];
  const MB_ARP = [[0, 3, 6, 10], [0, 4, 8, 11, 14], [2, 6, 9, 12], [0, 6, 10, 13]];
  function stepBeat(M, st) { return st * 0.25 + ((st % 2) ? M.swing * 0.25 : 0); }
  function hum() { return rnd(-0.006, 0.006); }

  function seasonPlan(s) {
    const M = MUSIC[s], ev = [], st = state[s], spb = M.spb, NC = M.chords.length;
    const E = (o, st16, human) => Object.assign(o, { beat: stepBeat(M, st16), hum: human ? hum() : 0 });
    for (let bar = 0; bar < SEASON_BARS; bar++) {
      const o = bar * 16;
      const ci = bar % NC;                         // the chord loop, repeated through the phase
      const [root, voic] = M.chords[ci];
      const last = bar === SEASON_BARS - 1;
      const nextRoot = last ? TRANS[s].pre[0] : M.chords[(ci + 1) % NC][0];
      const nextVoic = last ? TRANS[s].pre[1] : M.chords[(ci + 1) % NC][1];
      // ---- harmony on the season's own bus ----
      if (M.comp === 'rhodes') {
        ev.push(E({ k: 'chord', bus: s, inst: 'rhodes', notes: voic, vel: 0.85, dur: spb * 2.5, strum: 0.012 }, o, true));
        if (urand() < 0.6) ev.push(E({ k: 'chord', bus: s, inst: 'rhodes', notes: voic.slice(1), vel: 0.45, dur: spb * 1.25, strum: 0.008 }, o + 10, true));
        if (ci === NC - 1 && urand() < 0.4)
          ev.push(E({ k: 'chord', bus: s, inst: 'rhodes', notes: nextVoic, vel: 0.5, dur: spb * 0.6, strum: 0.01 }, o + 14, true));
      } else if (M.comp === 'guitar') {
        if (bar === 0 || urand() < 0.3) {
          ev.push(E({ k: 'chord', bus: s, inst: 'guitar', notes: voic, vel: 0.75, dur: spb * 3.6, strum: 0.028 }, o, true));
          [6, 10, 14].forEach((stp, i) => ev.push(E({ k: 'note', bus: s, inst: 'guitar', m: voic[(i + 2) % voic.length], vel: 0.45, dur: spb * 0.75 }, o + stp, true)));
        } else {
          const pat = pick([[0, 3, 6, 8, 11, 14], [0, 4, 6, 10, 12, 14], [0, 3, 7, 10, 13]]);
          const order = pick([[0, 2, 3, 4, 3, 2], [0, 3, 2, 4, 1, 3], [0, 1, 2, 3, 4, 2]]);
          pat.forEach((stp, i) => ev.push(E({ k: 'note', bus: s, inst: 'guitar', m: voic[order[i % order.length] % voic.length],
            vel: i === 0 ? 0.7 : rnd(0.42, 0.58), dur: spb * 1.5 }, o + stp, true)));
        }
      } else if (M.comp === 'piano') {
        ev.push(E({ k: 'chord', bus: s, inst: 'piano', notes: voic, vel: 0.7, dur: spb * 3, strum: 0.014 }, o, true));
        if (urand() < 0.5) ev.push(E({ k: 'chord', bus: s, inst: 'piano', notes: voic.slice(0, 3), vel: 0.38, dur: spb * 1.5, strum: 0.01 }, o + 8, true));
        if (urand() < 0.3) [12, 13, 14].forEach((stp, i) => ev.push(E({ k: 'note', bus: s, inst: 'piano', m: voic[(i + 1) % 4] + 12, vel: 0.3, dur: spb * 0.75 }, o + stp, true)));
      } else if (M.comp === 'pad') {
        ev.push(E({ k: 'pad', bus: s, notes: voic, dur: spb * 4 + 0.4, vel: 1 }, o, false));
        const arp = pick(MB_ARP), pv = M.padVoice || 'musicbox';
        const tones = voic.map(x => x + (pv === 'musicbox' ? 24 : 12)).concat([voic[0] + (pv === 'musicbox' ? 36 : 24)]);
        arp.forEach((stp, i) => { if (urand() < 0.85) ev.push(E({ k: 'note', bus: s, inst: pv, m: tones[(i + (bar & 1)) % tones.length], vel: rnd(0.35, 0.5), dur: 2.5 }, o + stp, true)); });
      } else if (M.comp === 'arp') {
        // chiptune: the chord as a fast 16th-note arpeggio, accents on the beat
        const ai = M.arpInst || 'pulse2', tones = voic.map(x => x + 12);
        for (let stp = 0; stp < 16; stp++) ev.push(E({ k: 'note', bus: s, inst: ai, m: tones[stp % tones.length], vel: stp % 4 ? 0.55 : 0.8, dur: spb * 0.22 }, o + stp, false));
      }
      // ---- bass on the core bus ----
      const bI = M.bass || 'bass';
      if (M.bassMode === 'drone') {
        ev.push(E({ k: 'pad', bus: CORE, notes: [root, root + 12], dur: spb * 4 + 0.6, vel: 2.4 }, o, false));   // overlapping sub pad
      } else if (M.bassMode === 'octaves') {
        [0, 3, 6, 8, 10, 14].forEach((stp, i) => ev.push(E({ k: 'note', bus: CORE, inst: bI, m: root + (i % 2 ? 12 : 0), vel: i ? 0.7 : 0.9, dur: spb * 0.4 }, o + stp, false)));
      } else {
        ev.push(E({ k: 'note', bus: CORE, inst: bI, m: root, vel: 0.9, dur: spb * 1.75 }, o, false));
        if (urand() < 0.6) ev.push(E({ k: 'note', bus: CORE, inst: bI, m: urand() < 0.5 ? root : root + 7, vel: 0.6, dur: spb }, o + 10, true));
        if (urand() < 0.35) ev.push(E({ k: 'note', bus: CORE, inst: bI, m: nextRoot + pick([-1, 1, -2, 2]), vel: 0.5, dur: spb * 0.5 }, o + 14, true));
      }
      if (M.drums === false) continue;
      // ---- drums on the core bus ----
      for (const [stp, v] of M.kick) ev.push(E({ k: 'drum', bus: CORE, name: dn(M, 'kick'), vel: v * rnd(0.9, 1.05) }, o + stp, stp !== 0));
      if (urand() < 0.22) ev.push(E({ k: 'drum', bus: CORE, name: dn(M, 'kick'), vel: 0.42 }, o + pick([3, 14]), true));
      for (const [stp, v] of M.snare) ev.push(E({ k: 'drum', bus: CORE, name: M.snd, vel: v * rnd(0.9, 1.05) }, o + stp, true));
      if (urand() < 0.2) ev.push(E({ k: 'drum', bus: CORE, name: M.snd, vel: 0.18 }, o + pick([7, 15]), true));
      // fills mark the turnaround of the loop; the last bar leaves room for the transition
      const fill = (bar === 3 && urand() < 0.75) || ((bar === 1 || bar === 5) && urand() < 0.3);
      if (fill) [13, 14, 15].forEach((stp, i) => ev.push(E({ k: 'drum', bus: CORE, name: M.snd, vel: 0.2 + i * 0.08 }, o + stp, true)));
      if (M.hats) {
        const thin = urand() < 0.1;
        for (let stp = 0; stp < 16; stp += (M.hats === 16 && !thin ? 1 : 2)) {
          const v = stp % 4 === 0 ? 0.55 : (stp % 2 === 0 ? 0.4 : 0.2);
          ev.push(E({ k: 'drum', bus: CORE, name: dn(M, 'hat'), vel: v * rnd(0.8, 1.1) }, o + stp, true));
        }
        if (M.ohat && urand() < M.ohat) ev.push(E({ k: 'drum', bus: CORE, name: dn(M, 'ohat'), vel: 0.4 }, o + 14, true));
      }
      if (M.shaker) for (let stp = 0; stp < 16; stp += (M.shakerStep || 1))
        ev.push(E({ k: 'drum', bus: CORE, name: dn(M, 'shaker'), vel: M.shaker * (stp % 2 ? 0.55 : 0.9) * rnd(0.85, 1.1) }, o + stp, true));
    }
    // ---- melody: two-bar phrases, sometimes echoing the last rhythm ----
    for (let startBar = 0; startBar < SEASON_BARS; startBar += 2) {
      if (urand() > M.mel * (startBar === 0 ? 1 : 0.75)) continue;
      const rh = (st.rh && urand() < 0.45) ? st.rh : pick(RHYTHMS);
      st.rh = rh;
      let deg = st.deg === undefined ? Math.floor(M.scale.length / 2) : st.deg;
      const lo = M.scale[0] - 3, hi = M.scale[M.scale.length - 1] + 3;
      rh.forEach((stp, i) => {
        deg = Math.max(0, Math.min(M.scale.length - 1, deg + pick([-2, -1, -1, 0, 1, 1, 2])));
        let m = M.scale[deg];
        const bi = (startBar + (stp >> 4)) % NC;
        const chord = M.chords[bi];
        if (stp % 4 === 0) m = nearestTone(m, chord[1].concat([chord[0]]), lo, hi);
        const alt = M.alter && M.alter[bi];
        if (alt && alt[m]) m = alt[m];
        const nxt = rh[i + 1] !== undefined ? rh[i + 1] - stp : 4;
        ev.push(Object.assign({ k: 'note', lead: true, bus: s, inst: M.lead, m, vel: rnd(0.7, 1) * LEAD_BOOST,
          dur: Math.min(6, nxt) * spb * 0.25 + 0.08, pan: pick([1, 3]) }, { beat: stepBeat(M, startBar * 16 + stp), hum: hum() }));
      });
      st.deg = deg;
    }
    return ev;
  }

  function transPlan(s) {
    const A = MUSIC[s], to = (s + 1) % NPH, Bm = MUSIC[to], T = TRANS[s];
    const ev = [], spb = 120 / (A.bpm + Bm.bpm);          // seconds per beat at the mean tempo
    const E = (o, beat, human) => Object.assign(o, { beat, hum: human ? hum() : 0 });
    // harmony on both buses: the bus envelopes do the DJ blend between them
    for (const [bus, M, vIn] of [[s, A, 0.8], [to, Bm, 0.8]]) {
      if (M.comp === 'pad') {
        ev.push(E({ k: 'pad', bus, notes: T.pre[1], dur: spb * 2 + 0.3, vel: 0.9 }, 0, false));
        ev.push(E({ k: 'pad', bus, notes: T.dom[1], dur: spb * 2 + 0.7, vel: 0.9 }, 2, false));
        [0.5, 1.5, 2.5, 3.25].forEach((b, i) => ev.push(E({ k: 'note', bus, inst: M.padVoice || 'musicbox',
          m: (i < 2 ? T.pre[1] : T.dom[1])[(i * 2 + 1) % 4] + 24, vel: 0.38, dur: 2 }, b, true)));
      } else {
        const strum = M.comp === 'guitar' ? 0.028 : (M.comp === 'arp' ? 0.03 : 0.012);
        const ci = M.comp === 'arp' ? (M.arpInst || 'pulse2') : M.comp;
        ev.push(E({ k: 'chord', bus, inst: ci, notes: T.pre[1], vel: vIn, dur: spb * 1.9, strum }, 0, true));
        ev.push(E({ k: 'chord', bus, inst: ci, notes: T.dom[1], vel: vIn, dur: spb * 2.3, strum }, 2, true));
      }
    }
    // the incoming voice often hums a short pickup over the dominant
    if (urand() < 0.65) {
      const up = Bm.lead === 'musicbox' ? 24 : 12;
      const tones = T.dom[1].map(x => x + up).sort((a, b) => a - b);
      const pat = pick([[2.5, 3, 3.5], [3, 3.5], [2, 2.75, 3.5], [2.5, 3.25, 3.75]]);
      const dirUp = urand() < 0.5;
      pat.forEach((b, i) => ev.push(E({ k: 'note', lead: true, bus: to, inst: Bm.lead,
        m: tones[dirUp ? i % tones.length : (tones.length - 1 - i % tones.length)], vel: 0.8 * LEAD_BOOST, dur: spb * 0.6, pan: 3 }, b, true)));
    }
    // bass walks the ii-V and steps chromatically onto the new root
    const bA = A.bass || 'bass', bB = Bm.bass || 'bass';
    ev.push(E({ k: 'note', bus: CORE, inst: bA, m: T.pre[0], vel: 0.85, dur: spb * 1.8 }, 0, false));
    ev.push(E({ k: 'note', bus: CORE, inst: bA, m: T.dom[0], vel: 0.8, dur: spb * 1.4 }, 2, false));
    ev.push(E({ k: 'note', bus: CORE, inst: bB, m: T.approach, vel: 0.55, dur: spb * 0.45 }, 3.5, true));
    // the groove keeps time through the tempo ramp: outgoing snare, then incoming snare and a fill
    if (A.drums !== false || Bm.drums !== false) {
      const G = A.drums !== false ? A : Bm, sA = A.snd || Bm.snd, sB = Bm.snd || A.snd;
      ev.push(E({ k: 'drum', bus: CORE, name: dn(G, 'kick'), vel: 0.85 }, 0, false));
      ev.push(E({ k: 'drum', bus: CORE, name: dn(G, 'kick'), vel: 0.7 }, 2, true));
      if (urand() < 0.5) ev.push(E({ k: 'drum', bus: CORE, name: dn(G, 'kick'), vel: 0.4 }, 2.75, true));
      ev.push(E({ k: 'drum', bus: CORE, name: sA, vel: 0.55 }, 1, true));
      ev.push(E({ k: 'drum', bus: CORE, name: sB, vel: 0.6 }, 3, true));
      [3.25, 3.5, 3.75].forEach((b, i) => ev.push(E({ k: 'drum', bus: CORE, name: sB, vel: 0.2 + i * 0.09 }, b, true)));
      if (A.hats || Bm.hats) for (let b = 0; b < 3; b += 0.5) ev.push(E({ k: 'drum', bus: CORE, name: dn(G, 'hat'), vel: (b % 1 ? 0.25 : 0.45) }, b, true));
      if (A.shaker || Bm.shaker) for (let b = 0; b < 4; b += 0.5) ev.push(E({ k: 'drum', bus: CORE, name: dn(G, 'shaker'), vel: 0.3 }, b, true));
    }
    ev.push(E({ k: 'riser', bus: CORE, vel: 1 }, 0, false));
    return ev;
  }

  const PSTRIDE = Math.max(16, 2 * NPH);
  function plan(n, gi) {
    const key = n * PSTRIDE + gi;
    let p = planCache.get(key);
    if (p) return p;
    const g = SEG[gi];
    if (LOOPED) {
      seedStream(1000 + mod(n, GRAND) * PSTRIDE + gi);
      if (g.kind === 'season') state[g.s] = {};     // no memory across cycles, so cycle n == n + GRAND
    }
    p = g.kind === 'season' ? seasonPlan(g.s) : transPlan(g.s);
    // drum sample and pitch are chosen with the plan, so playback draws nothing at random
    for (const e of p) if (e.k === 'drum') { e.v3 = Math.floor(urand() * 3); e.rate = rnd(0.985, 1.015); }
    planCache.set(key, p);
    if (planCache.size > 300) {
      const it = planCache.keys();
      for (let i = 0; i < 100; i++) planCache.delete(it.next().value);
    }
    return p;
  }

  /* ------------------------------------------------------------ playback */
  function bufFor(inst, m) {
    let b = BUF[inst + m];
    if (b) return [b, 1];
    for (let d = 1; d <= 3; d++) {
      for (const sgn of [1, -1]) {
        b = BUF[inst + (m + sgn * d)];
        if (b) return [b, Math.pow(2, -sgn * d / 12)];
      }
    }
    return [null, 1];
  }
  function voice(bus, inst, m, t, vel, dur, pan) {
    const [b, rate] = bufFor(inst, m);
    if (!b) return;
    const B = BUS[bus];
    const src = ctx.createBufferSource(); src.buffer = b; src.playbackRate.value = rate;
    const g = ctx.createGain();
    const lv = (LEVEL[inst] || 0.3) * vel;
    g.gain.value = lv;
    src.connect(g);
    g.connect(B.pans[pan === undefined ? 2 : pan]);
    if (SEND[inst]) g.connect(B.sends[inst]);
    src.start(t);
    const rel = inst === 'bass' || inst === 'tri' ? 0.12 : (inst === 'pulse' || inst === 'pulse2' ? 0.05 : 0.35);
    const end = Math.min(t + dur, t + b.duration / rate - rel);
    g.gain.setValueAtTime(lv, end);
    g.gain.setTargetAtTime(0, end, rel / 3);
    src.stop(Math.min(t + b.duration / rate, end + rel * 2));
    src.onended = () => { src.disconnect(); g.disconnect(); };
  }
  function drum(bus, name, t, vel, v3, rate) {
    const b = BUF[name === 'ohat' ? 'ohat' : name + (v3 || 0)];
    if (!b) return;
    const B = BUS[bus];
    const src = ctx.createBufferSource(); src.buffer = b;
    src.playbackRate.value = rate || 1;
    const g = ctx.createGain(); g.gain.value = (LEVEL[name] || 0.3) * vel;
    src.connect(g);
    g.connect(name === 'hat' || name === 'shaker' ? B.pans[3] : B.pans[2]);
    if (SEND[name]) g.connect(B.sends[name]);
    src.start(t);
    src.onended = () => { src.disconnect(); g.disconnect(); };
  }
  function pad(bus, notes, t, dur, vel) {
    const B = BUS[bus];
    for (const m of notes) {
      const f = mtof(m);
      const o1 = ctx.createOscillator(); o1.type = 'triangle'; o1.frequency.value = f;
      const o2 = ctx.createOscillator(); o2.type = 'sawtooth'; o2.frequency.value = f * 1.0035;
      const g2 = ctx.createGain(); g2.gain.value = 0.16;
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1000; lp.Q.value = 0.4;
      const g = ctx.createGain(); g.gain.value = 0;
      o1.connect(lp); o2.connect(g2).connect(lp); lp.connect(g);
      g.connect(B.pans[m % 2 ? 1 : 3]); g.connect(B.sends.pad);
      const lv = LEVEL.pad * vel;
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(lv, t + Math.min(1.3, dur * 0.4));
      g.gain.setValueAtTime(lv, t + dur);
      g.gain.linearRampToValueAtTime(0, t + dur + 1.8);
      o1.start(t); o2.start(t); o1.stop(t + dur + 2); o2.stop(t + dur + 2);
      o1.onended = () => { o1.disconnect(); o2.disconnect(); g2.disconnect(); lp.disconnect(); g.disconnect(); };
    }
  }
  function riserAt(t, dur, vel) {
    const b = BUF.riser;
    if (!b) return;
    const B = BUS[CORE];
    const src = ctx.createBufferSource(); src.buffer = b;
    src.playbackRate.value = b.duration / dur;          // peaks exactly on the next downbeat
    const g = ctx.createGain(); g.gain.value = LEVEL.riser * vel;
    // the riser is stereo: it goes straight into the bus, not through a panner. A stereo
    // input flips a StereoPanner into its stereo law, which would lift every mono drum and
    // bass note through that panner by 3 dB for as long as the riser stays connected.
    src.connect(g); g.connect(B.dry); g.connect(B.sends.riser);
    src.start(t);
    src.onended = () => { src.disconnect(); g.disconnect(); };
  }

  let SOLO = null;
  function cat(e) {
    if (e.k === 'drum') return (e.name === 'kick' || e.name === 'ckick') ? 'kick' : (e.name === 'hat' || e.name === 'ohat' || e.name === 'shaker' || e.name === 'chat') ? 'hat' : 'snare';
    if (e.k === 'pad') return 'pad';
    if (e.k === 'riser') return 'fx';
    if (e.inst === 'bass' || e.inst === 'tri') return 'bass';
    return e.lead ? 'lead' : 'keys';
  }
  function fire(e, t, g) {
    if (t < ctx.currentTime) return;
    if (SOLO && !SOLO.includes(cat(e))) return;
    if (e.k === 'drum') drum(e.bus, e.name, t, e.vel, e.v3, e.rate);
    else if (e.k === 'note') voice(e.bus, e.inst, e.m, t, e.vel, e.dur, e.pan);
    else if (e.k === 'chord') e.notes.forEach((m, i) => voice(e.bus, e.inst, m, t + i * e.strum, e.vel * (i === 0 ? 1 : 0.85), e.dur, i % 2 ? 1 : 3));
    else if (e.k === 'pad') pad(e.bus, e.notes, t, e.dur, e.vel);
    else if (e.k === 'riser') riserAt(t, g.dur, e.vel);
  }

  /* ------------------------------------------------------------ scheduler */
  function scheduleRange(t0, t1) {
    const V0 = t0 + off, V1 = t1 + off;
    scheduleEnvs(V0, V1);
    const n0 = Math.floor(V0 / CYCLE) - 1, n1 = Math.floor(V1 / CYCLE) + 1;
    for (let n = n0; n <= n1; n++) {
      for (let gi = 0; gi < SEG.length; gi++) {
        const g = SEG[gi];
        const gs = n * CYCLE + g.start;
        if (gs > V1 || gs + g.dur + 0.5 < V0) continue;
        for (const e of plan(n, gi)) {
          const tv = gs + segBeatTime(g, e.beat) + e.hum;
          if (tv >= V0 && tv < V1) fire(e, tv - off, g);
        }
      }
    }
  }
  const LOOK = 1.8;
  function tick() {
    const now = ctx.currentTime;
    if (schedEnd < now) schedEnd = now;
    const end = now + LOOK;
    if (end > schedEnd) { scheduleRange(schedEnd, end); schedEnd = end; }
  }

  /* ------------------------------------------------------------ public api */
  function clock() {
    if (ctx.getOutputTimestamp) {
      const ts = ctx.getOutputTimestamp();
      if (ts && ts.contextTime > 0 && ts.performanceTime > 0) {
        return ts.contextTime + (performance.now() - ts.performanceTime) / 1000 + off;
      }
    }
    return ctx.currentTime + off;
  }
  function seasonOf(V) {
    const tc = mod(V, CYCLE);
    for (const g of SEG) if (tc < g.start + g.dur) return g.kind === 'season' ? g.s : g.to;
    return 0;
  }
  async function start(getV) {
    if (started) return clock;
    started = true;
    const AC = window.AudioContext || window.webkitAudioContext;
    ctx = new AC({ latencyHint: 'playback' });
    SR = ctx.sampleRate;
    try { await ctx.resume(); } catch (e) { /* resumes on gesture */ }
    const si = seasonOf(getV());
    // what is needed right now first; the rest while the music plays
    await runJobs(commonJobs(), 40);
    await runJobs(jobsFor(si), 40);
    buildGraph(ctx.destination);
    off = getV() - ctx.currentTime;
    primeEnvs(ctx.currentTime + off, ctx.currentTime);
    startAmbience(si, ctx.currentTime);
    master.gain.setValueAtTime(0, ctx.currentTime);
    master.gain.linearRampToValueAtTime(muted ? 0 : MASTER, ctx.currentTime + 2.5);
    schedEnd = ctx.currentTime + 0.05;
    tick();
    timer = setInterval(tick, 200);
    (async () => {
      for (let d = 1; d < NPH; d++) { const s = (si + d) % NPH;
        await runJobs(jobsFor(s), 25);
        startAmbience(s, ctx.currentTime);
      }
    })();
    return clock;
  }
  function toggleMute() {
    if (!ctx || !master) return;
    muted = !muted;
    const t = ctx.currentTime;
    master.gain.cancelScheduledValues(t);
    master.gain.setValueAtTime(master.gain.value, t);
    master.gain.linearRampToValueAtTime(muted ? 0 : MASTER, t + 0.4);
  }
  document.addEventListener('visibilitychange', () => {
    if (ctx && document.visibilityState === 'visible' && ctx.state === 'suspended') ctx.resume();
  });

  /* ------------------------------------------------------------ offline render and checks (debug) */
  // loop = true: seeded so the result repeats exactly every GRAND cycles (one picture loop)
  async function renderOffline(V0, seconds, sr, solo, loop) {
    SOLO = solo || null;
    const save = { ctx, SR, BUF, off, planCache, urand };
    const oc = new OfflineAudioContext(2, Math.floor(seconds * (sr || 48000)), sr || 48000);
    ctx = oc; SR = oc.sampleRate; BUF = {}; planCache = new Map();
    for (let s = 0; s < NPH; s++) state[s] = {};
    let out;
    try {
      if (loop) { LOOPED = true; seedStream(7); }
      await runJobs(commonJobs(), 0);
      for (let s = 0; s < NPH; s++) await runJobs(jobsFor(s), 0);
      buildGraph(oc.destination);
      off = V0;
      primeEnvs(V0, 0);
      for (let s = 0; s < NPH; s++) if (!SOLO || SOLO.includes('amb')) startAmbience(s, 0);
      if (SOLO && !SOLO.includes('vinyl')) vinylGain.gain.value = 0;
      master.gain.setValueAtTime(MASTER, 0);
      scheduleRange(0, seconds);
    } finally {
      LOOPED = false; urand = save.urand;
    }
    out = await oc.startRendering();
    ctx = save.ctx; SR = save.SR; BUF = save.BUF; off = save.off; planCache = save.planCache;
    SOLO = null;
    return out;
  }
  async function selfTest(cycles) {
    const save = { ctx, SR, BUF };
    ctx = new OfflineAudioContext(2, 48000, 48000); SR = 48000; BUF = {};
    await runJobs(commonJobs(), 0);
    for (let s = 0; s < NPH; s++) await runJobs(jobsFor(s), 0);
    let events = 0, missing = 0, retuned = 0, outside = 0;
    const miss = {};
    for (let n = 0; n < cycles; n++) for (let gi = 0; gi < SEG.length; gi++) {
      const g = SEG[gi];
      const beats = g.kind === 'season' ? SEASON_BARS * 4 : 4;
      for (const e of (g.kind === 'season' ? seasonPlan(g.s) : transPlan(g.s))) {
        events++;
        if (e.beat < 0 || e.beat >= beats) outside++;
        const notes = e.k === 'chord' ? e.notes : (e.k === 'note' ? [e.m] : []);
        for (const m of notes) {
          const [b, rate] = bufFor(e.inst, m);
          if (!b) { missing++; miss[e.inst + m] = 1; } else if (rate !== 1) retuned++;
        }
      }
    }
    ctx = save.ctx; SR = save.SR; BUF = save.BUF;
    return { events, missing, retuned, outside, miss: Object.keys(miss).slice(0, 20), bpm: TIMELINE.bpm.map(b => +b.toFixed(2)),
      seg: SEG.map(g => g.kind[0] + g.s + ':' + g.start.toFixed(2) + '+' + g.dur.toFixed(2)) };
  }

  return { start, toggleMute, renderOffline, selfTest, MUSIC };
})();
window.LOFI = LOFI;
