/* ==========================================================================
   pixelate-anything engine: bootstrap. Clock, integer-scaled display, play button,
   keyboard helpers (F fullscreen, M mute).
   ========================================================================== */
const DEBUG_BUILD = true;
(function () {
  const cv = document.getElementById('c');
  const stage = document.getElementById('stage');
  const btn = document.getElementById('play');
  cv.width = W; cv.height = H;
  const g = cv.getContext('2d', { alpha: false });
  const img = g.createImageData(W, H);
  const out32 = new Uint32Array(img.data.buffer);
  initPalettes();

  // ---- clock: performance clock until audio starts, then the audio clock ----
  let q = {};
  try {
    if (DEBUG_BUILD) location.search.slice(1).split('&').forEach(p => {
      const [a, b] = p.split('='); if (a) q[a] = decodeURIComponent(b || '1');
    });
  } catch (e) { q = {}; }
  const perf0 = performance.now();
  let base = q.t ? parseFloat(q.t) : 0;
  let frozen = q.freeze ? true : false;
  let audioClock = null;
  function vtime() {
    if (frozen) return base;
    if (audioClock) return audioClock();
    return base + (performance.now() - perf0) / 1000;
  }

  // ---- display scaling: whole device pixels when possible ----
  let scale = 1;
  function fit() {
    const dpr = window.devicePixelRatio || 1;
    const vw = stage.clientWidth * dpr, vh = stage.clientHeight * dpr;
    // whole device pixels when the screen allows 2x or more; otherwise fit exactly
    const fitS = Math.min(vw / W, vh / H);
    let s = Math.floor(fitS);
    if (s < 2) s = fitS;
    scale = s;
    cv.style.width = (W * s / dpr) + 'px';
    cv.style.height = (H * s / dpr) + 'px';
    // the play button keeps a comfortable tap size whatever the pixel scale
    const cssPx = (W * s / dpr) / W;
    const b = Math.max(88, Math.min(160, Math.round(17 * cssPx * 2.3)));
    btn.style.width = btn.style.height = b + 'px';
  }
  window.addEventListener('resize', fit);
  fit();

  // ---- render loop: content changes only on 30 Hz ticks ----
  let lastK = -1, lastEdge = '';
  const css = c => 'rgb(' + (c & 255) + ',' + ((c >> 8) & 255) + ',' + ((c >> 16) & 255) + ')';
  // the most common colour among the first pixels of a row (ignores rain, snow, dither)
  function rowColor(y) {
    const b = y * W;
    let best = out32[b], cnt = 0;
    for (let i = 0; i < 8; i++) {
      let n = 0;
      for (let j = 0; j < 8; j++) if (out32[b + j] === out32[b + i]) n++;
      if (n > cnt) { cnt = n; best = out32[b + i]; }
    }
    return best;
  }
  // margins around the frame (phones taller or wider than 9:16) continue its rows
  function edgeColours() {
    const r = cv.getBoundingClientRect(), sh = stage.clientHeight || 1;
    const parts = [css(rowColor(0)) + ' 0%'];
    for (let y = 0; y < H; y += 8) {
      const pos = (r.top + (y + 4) / H * r.height) / sh * 100;
      parts.push(css(rowColor(y)) + ' ' + pos.toFixed(2) + '%');
    }
    parts.push(css(rowColor(H - 1)) + ' 100%');
    const bg = 'linear-gradient(to bottom, ' + parts.join(', ') + ')';
    if (bg !== lastEdge) { lastEdge = bg; stage.style.background = bg; }
  }
  function drawTick(k) {
    renderFrame(k, out32);
    g.putImageData(img, 0, 0);
    if (k % 15 === 0 || !lastEdge) edgeColours();
  }
  const LOOP = CYCLE * GRAND;
  function loop() {
    const v = vtime();
    const k = Math.floor(mod(v, LOOP) * HZ) % TICKS;
    if (k !== lastK) { lastK = k; drawTick(k); }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  // ---- idle cursor ----
  let idleTimer = 0;
  function wake() {
    stage.classList.remove('idle');
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => stage.classList.add('idle'), 2500);
  }
  window.addEventListener('mousemove', wake, { passive: true });
  wake();

  // ---- fullscreen & mute helpers ----
  function toggleFull() {
    try {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (stage.requestFullscreen) stage.requestFullscreen().catch(() => {});
    } catch (e) { /* optional */ }
  }
  stage.addEventListener('dblclick', toggleFull);
  window.addEventListener('keydown', e => {
    if (e.key === 'f' || e.key === 'F') toggleFull();
    if ((e.key === 'm' || e.key === 'M') && window.LOFI) window.LOFI.toggleMute();
  });

  // ---- wake lock so a long recording never dims the screen ----
  let lock = null;
  async function holdWake() {
    try { if ('wakeLock' in navigator) lock = await navigator.wakeLock.request('screen'); } catch (e) { lock = null; }
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && btn.hidden) holdWake();
  });

  // ---- play button ----
  btn.addEventListener('click', async () => {
    if (btn.classList.contains('busy')) return;
    btn.classList.add('busy');
    holdWake();
    try {
      if (window.LOFI) {
        const clock = await window.LOFI.start(vtime);
        if (clock && !frozen) { audioClock = clock; }
      }
    } catch (e) {
      if (DEBUG_BUILD) console.error(e);
    }
    btn.classList.remove('busy');
    btn.classList.add('gone');
    setTimeout(() => { btn.hidden = true; }, 950);
  });

  // ---- debug hooks used by the preview harness ----
  if (DEBUG_BUILD) {
    window.__dbg = {
      set(t) { base = t; frozen = true; lastK = -1; const k = Math.floor(mod(t, CYCLE * GRAND) * HZ) % TICKS; drawTick(k); return k; },
      grab() { return cv.toDataURL('image/png'); },
      warn: SPRITE_WARN.concat(PALETTE_WARN),
    };
    if (SPRITE_WARN.length || PALETTE_WARN.length) console.warn(SPRITE_WARN.concat(PALETTE_WARN).join('\n'));
  }
})();
