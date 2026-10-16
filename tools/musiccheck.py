#!/usr/bin/env python3
"""The music gate: listen to a rendered track and say PASS or FAIL, the way `check FRAME` judges a picture.

The agent writes the music itself, in any code (the engine's phases, its own Web Audio or Python
synth, anything that renders a file). This tool does not make sound; it measures what came out and
holds it to limits, so the agent can rewrite until it passes. It also draws an ear sheet: a picture
of the track to LOOK at, as with frame previews.

usage: musiccheck.py TRACK.{wav,ogg,flac,mp3,mp4} [--style S] [--use U] [--bpm N] [--key Am]
                     [--sheet sheet.png] [--json]

  --style   the sound being made, sets the mix limits: lofi | chiptune | ambient | orchestral |
            synthwave | eastern | any (default any: only the limits every style shares)
  --use     what it is for, sets the form limits:
              loop      background or game loop: seamless wrap, no dead air, variety over time
              showcase  a short piece people watch (a trailer, a demo reel): a hook that returns,
                        an arc (it builds and releases), no flat stretches
              song      a piece with an ending: no wrap check, an arc
            (default loop)
  --bpm     the tempo the code asked for: the measured beat must match it
  --key     the key the code asked for (C, F#m, Bbm ...): the measured key must match it

Checks (each prints PASS, FAIL or SKIP with the measured value and the limit; exit 1 on a FAIL):
  technical   peak       true peak (4x oversampled) under -0.5 dBFS: no clipping
              loudness   integrated loudness (BS.1770, gated) inside the style's LUFS range
              dc         no DC offset
              clicks     isolated sample jumps (pops from a note starting or stopping off zero)
              stereo     L/R correlation: positive, so it survives mono speakers
              silence    no dead air at the start or end, no dropouts inside
              seam       --use loop: the wrap from the end back to the start is as smooth as any
                         other step (sample jump, loudness and spectrum on both sides)
  mix         balance    energy in sub, bass, low-mid, high-mid and air bands inside the style's ranges
                         (muddy = too much low-mid, harsh = too much 2-6 kHz, thin = too little bass)
              tilt       spectral slope in dB per octave (dull or bright overall)
              dynamics   peak-to-loudness ratio: not squashed flat, not spiky
  music       tempo      a steady beat found (and it matches --bpm); free-time styles skip it
              key        a clear key centre (and it matches --key); notes outside it kept low
              variety    bars that are not copies of an earlier bar, so it does not loop too soon
              hook       --use showcase: a melodic phrase that comes back at least 3 times
              arc        --use showcase or song: loudness and density change across the piece
                         (a build and a release), not one flat level start to end

Not measured, so judge by ear (guides/music.md "Self-critique"): is the melody your own, does it
fit the picture, does each section feel different. A PASS means nothing is wrong that numbers see.

    import musiccheck as mc
    x, sr = mc.load('theme.wav')
    rows = mc.report(x, sr, style='chiptune', use='showcase', bpm=140)
    # [(group, check, 'PASS'|'FAIL'|'SKIP', 'measured, limit'), ...]
Deterministic, numpy and pillow only (ffmpeg decodes anything that is not WAV).
"""
import json, pathlib, subprocess, sys, wave
import numpy as np

SR = 48000
AUDIO_EXT = ('.wav', '.ogg', '.flac', '.mp3', '.m4a', '.aac', '.opus', '.mp4', '.webm', '.mkv')

# Mix limits per style: LUFS range, band shares (dB of total energy), slope (dB/oct),
# PLR (true peak minus loudness, dB), clicks per minute. Measured on the kit's own tracks
# (Lantern Isle, pixel-radio) and on mixes typical of each genre, with a margin.
BANDS = (('sub', 20, 60), ('bass', 60, 250), ('lowmid', 250, 2000), ('highmid', 2000, 6000), ('air', 6000, 20000))
ANY = dict(lufs=(-20, -9), sub=(-30, -4), bass=(-14, -1), lowmid=(-12, -0.5), highmid=(-24, -5),
           air=(-40, -9), tilt=(-9, -1.5), plr=(6, 20), clicks=4, key_min=0.45, out_key=0.35,
           tempo=True, variety=0.30)
STYLES = {
    'any': {},
    'lofi': dict(lufs=(-17, -11), highmid=(-26, -8), air=(-44, -13), tilt=(-9, -3), plr=(8, 18)),
    'chiptune': dict(lufs=(-16, -9), bass=(-16, -2), highmid=(-24, -4), air=(-34, -7), tilt=(-8, -1.5),
                     plr=(5, 16), clicks=None),   # square edges and hard note starts are the sound
    'ambient': dict(lufs=(-22, -13), plr=(9, 22), tempo=False, variety=0.2, key_min=0.35),
    'orchestral': dict(lufs=(-23, -12), plr=(10, 24), key_min=0.4),
    'synthwave': dict(lufs=(-15, -9), sub=(-24, -3), highmid=(-22, -5), plr=(6, 15)),
    'eastern': dict(lufs=(-20, -11), plr=(8, 20), out_key=0.25),   # pentatonic: few notes outside
}
USES = ('loop', 'showcase', 'song')
HOOK_MIN = 3        # a phrase of HOOK_LEN notes heard this many times (showcase)
HOOK_LEN = 5
ARC_MIN = 4.0       # dB between the quietest and loudest sections (showcase, song)

def limits(style):
    if style not in STYLES:
        sys.exit('styles: ' + ', '.join(STYLES))
    d = dict(ANY); d.update(STYLES[style]); return d

# ------------------------------------------------------------------ input
def load(path):
    """Any audio (or a video's soundtrack) as float32 stereo at 48 kHz."""
    p = str(path)
    if p.lower().endswith('.wav'):
        try:
            with wave.open(p) as w:
                if w.getsampwidth() == 2 and w.getframerate() == SR:
                    x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
                    x = x.reshape(-1, w.getnchannels())
                    return (np.repeat(x, 2, 1) if x.shape[1] == 1 else x[:, :2]), SR
        except wave.Error:
            pass            # float WAV: ffmpeg reads it
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vn', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                       capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit('cannot decode %s: %s' % (p, r.stderr.decode()[-300:]))
    return np.frombuffer(r.stdout, '<f4').reshape(-1, 2).copy(), SR

db = lambda p: 10 * np.log10(np.maximum(p, 1e-12))

# ------------------------------------------------------------------ loudness (BS.1770-4)
def _kweight(n, sr):
    """|H(f)|^2 of the K-weighting pre-filter and RLB high-pass, for an rfft of length n."""
    w = 2 * np.pi * np.fft.rfftfreq(n, 1 / sr) / sr
    z = np.exp(-1j * w)
    def h(b, a):
        return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    H = h((1.53512485958697, -2.69169618940638, 1.19839281085285), (1, -1.69065929318241, 0.73248077421585))
    H = H * h((1.0, -2.0, 1.0), (1, -1.99004745483398, 0.99007225036621))
    return np.abs(H) ** 2

def block_loudness(x, sr, win=0.4, hop=0.1):
    """Loudness (LUFS) of each window, K-weighted in the frequency domain."""
    n = int(win * sr); s = int(hop * sr)
    k = _kweight(n, sr)
    wt = np.full(n // 2 + 1, 2.0); wt[0] = 1; wt[-1] = 1 if n % 2 == 0 else 2
    k = k * wt / (n * n)                  # Parseval: mean square straight from the rfft
    out = []
    for i in range(0, max(1, len(x) - n + 1), s):
        seg = x[i:i + n]
        if len(seg) < n:
            break
        ms = (np.abs(np.fft.rfft(seg, axis=0)) ** 2 * k[:, None]).sum()   # both channels summed (G = 1)
        out.append(-0.691 + db(ms))
    return np.array(out)

def integrated(blocks):
    b = blocks[blocks > -70]
    if not len(b):
        return -70.0
    rel = -0.691 + db(np.mean(10 ** ((b + 0.691) / 10))) - 10
    b = b[b > rel]
    return float(-0.691 + db(np.mean(10 ** ((b + 0.691) / 10))))

def true_peak(x):
    m = float(np.abs(x).max())
    n = 1 << 15
    for i in range(0, len(x), n):
        seg = x[max(0, i - 64):i + n + 64]
        F = np.fft.rfft(seg, axis=0)
        up = np.fft.irfft(F, 4 * len(seg), axis=0) * 4
        m = max(m, float(np.abs(up).max()))
    return 20 * np.log10(max(m, 1e-9))

# ------------------------------------------------------------------ spectrum
def stft_mag(mono, sr, n=4096, hop=1024):
    win = np.hanning(n).astype(np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(mono, n)[::hop]
    return np.abs(np.fft.rfft(frames * win, axis=1)).astype(np.float32), np.fft.rfftfreq(n, 1 / sr)

def band_shares(S, f, active):
    P = (S[active] ** 2).mean(0)
    tot = P[(f >= 20) & (f < 20000)].sum()
    return {name: float(db(P[(f >= lo) & (f < hi)].sum() / tot)) for name, lo, hi in BANDS}

def tilt(S, f, active):
    P = (S[active] ** 2).mean(0)
    cs = [63 * 2 ** k for k in range(9)]          # 63 Hz .. 16 kHz octave bands
    e = [db(P[(f >= c / 2 ** .5) & (f < c * 2 ** .5)].sum()) for c in cs]
    return float(np.polyfit(np.log2(cs), e, 1)[0])

# ------------------------------------------------------------------ pitch content
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

def chroma(S, f):
    """Pitch-class energy per frame, from spectral peaks only (refined between bins), so the
    leakage around a loud bass note does not count as its neighbour semitones."""
    sel = np.where((f >= 65) & (f <= 2100))[0]
    a, b, c = (np.log(S[:, sel + d] + 1e-9) for d in (-1, 0, 1))
    peak = (b > a) & (b >= c)
    off = np.where(peak, 0.5 * (a - c) / np.minimum(a - 2 * b + c, -1e-9), 0)
    fr = (sel + off) * (f[1] - f[0])
    pc = np.round(69 + 12 * np.log2(np.maximum(fr, 1) / 440)).astype(int) % 12
    w = np.where(peak, S[:, sel] ** 2, 0)
    C = np.stack([(w * (pc == k)).sum(1) for k in range(12)], 1)
    return C / np.maximum(C.sum(1, keepdims=True), 1e-12)

def key_of(C):
    prof = C.sum(0)
    best = (-2, 0, 'maj')
    for r in range(12):
        for mode, ks in (('maj', KS_MAJ), ('min', KS_MIN)):
            c = np.corrcoef(prof, np.roll(ks, r))[0, 1]
            if c > best[0]:
                best = (c, r, mode)
    c, r, mode = best
    scale = np.array([0, 2, 4, 5, 7, 9, 11] if mode == 'maj' else [0, 2, 3, 5, 7, 8, 10])
    inside = prof[(scale + r) % 12].sum() / prof.sum()
    return NAMES[r] + ('m' if mode == 'min' else ''), float(c), float(1 - inside)

def parse_key(k):
    k = k.strip()
    minor = k.endswith('m') and not k.endswith('maj')
    root = k[:-1] if minor else k.replace('maj', '')
    alias = {'Db': 'C#', 'D#': 'Eb', 'Gb': 'F#', 'G#': 'Ab', 'A#': 'Bb', 'Cb': 'B', 'Fb': 'E'}
    root = alias.get(root, root)
    return NAMES.index(root), minor

def same_key(a, b):
    """Equal, or the relative major/minor (the same notes)."""
    ra, ma = parse_key(a); rb, mb = parse_key(b)
    if ma == mb:
        return ra == rb
    return (ra + (3 if ma else -3)) % 12 == rb if ma else (ra - 3) % 12 == rb

def onset_env(S):
    L = np.log1p(S[:, :600] * 10)
    return np.maximum(np.diff(L, axis=0), 0).sum(1)

def tempo(S, sr, hop):
    o = onset_env(S); o = o - o.mean()
    ac = np.correlate(o, o, 'full')[len(o) - 1:]
    fps = sr / hop
    lags = np.arange(len(ac)) / fps
    ok = (lags >= 60 / 200) & (lags <= 60 / 55)
    i = np.argmax(np.where(ok, ac, -np.inf))
    # parabolic refinement
    if 0 < i < len(ac) - 1:
        a, b, c = ac[i - 1], ac[i], ac[i + 1]
        i = i + 0.5 * (a - c) / (a - 2 * b + c)
    bpm = 60 * fps / i
    strength = float(ac[int(round(i))] / ac[0])
    return bpm, strength

def melody(S, f, sr, hop):
    """The top line as notes: per frame the strongest pitch in 330-2100 Hz if it stands out,
    joined into notes. Returns MIDI numbers (one per note)."""
    sel = np.where((f >= 330) & (f <= 2100))[0]
    sub = S[:, sel]
    pk = sub.argmax(1)
    sal = sub.max(1) / (np.median(sub, 1) + 1e-9)
    midi = np.round(69 + 12 * np.log2(f[sel][pk] / 440)).astype(int)
    midi[sal < 25] = -1
    notes, cur, run = [], -1, 0
    for m in midi:
        if m == cur:
            run += 1
            continue
        if cur >= 0 and run >= 2:
            notes.append(cur)
        cur, run = m, 1
    if cur >= 0 and run >= 2:
        notes.append(cur)
    return notes

def hook(notes):
    """Most-heard phrase of HOOK_LEN notes, as intervals (so a transposed return counts),
    counting non-overlapping occurrences."""
    iv = np.diff(notes) if len(notes) > 1 else np.array([])
    iv = [int(v) for v in iv if abs(v) <= 12]
    best = (0, ())
    seen = {}
    k = HOOK_LEN - 1
    for i in range(len(iv) - k + 1):
        g = tuple(iv[i:i + k])
        if all(v == 0 for v in g) or len(set(g)) < 2:
            continue      # a repeated note or a plain trill is not a phrase
        last, n = seen.get(g, (-k, 0))
        if i - last >= k:
            seen[g] = (i, n + 1)
            if n + 1 > best[0]:
                best = (n + 1, g)
    return best

def bar_features(S, f, C, sr, hop, bpm):
    """One vector per bar (4 beats): pitch classes and band energies over its 16 steps."""
    fpb = 4 * 60 / bpm * sr / hop
    nb = int(len(S) / fpb)
    edges = [0] + [b for _, b, _ in [(0, 250, 0), (0, 2000, 0), (0, 6000, 0)]] + [20000]
    feats = []
    for b in range(nb):
        i0, i1 = int(b * fpb), int((b + 1) * fpb)
        steps = np.array_split(np.arange(i0, i1), 8)
        v = []
        for st in steps:
            v.extend(C[st].mean(0))
            P = (S[st] ** 2).mean(0)
            v.extend(db([P[(f >= lo) & (f < hi)].sum() for lo, hi in zip(edges[:-1], edges[1:])]) / 60)
        feats.append(np.array(v))
    return np.array(feats)

def variety(F):
    """Share of bars that are not a near copy of an earlier bar."""
    if len(F) < 4:
        return 1.0, len(F)
    Z = F - F.mean(0)
    Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
    sim = Z @ Z.T
    new = sum(1 for i in range(len(F)) if i == 0 or sim[i, :i].max() < 0.92)
    return new / len(F), len(F)

# ------------------------------------------------------------------ the gate
def report(x, sr=SR, style='any', use='loop', bpm=None, key=None, data=None):
    L = limits(style)
    rows = []
    def row(g, name, ok, msg):
        rows.append((g, name, 'SKIP' if ok is None else ('PASS' if ok else 'FAIL'), msg))
    dur = len(x) / sr
    mono = x.mean(1)
    blocks = block_loudness(x, sr)
    lufs = integrated(blocks)
    tp = true_peak(x)
    # technical
    row('technical', 'peak', tp <= -0.5, 'true peak %.2f dBFS, limit -0.5' % tp)
    lo, hi = L['lufs']
    row('technical', 'loudness', lo <= lufs <= hi, '%.1f LUFS, range %g..%g' % (lufs, lo, hi))
    dc = float(np.abs(x.mean(0)).max())
    row('technical', 'dc', dc < 0.002, 'offset %.4f, limit 0.002' % dc)
    if L['clicks'] is None:
        row('technical', 'clicks', None, 'hard edges are part of %s' % style)
    else:
        d2 = np.abs(np.diff(mono, 2))
        # a lone jump stands ~30x above the RMS of the jumps around it (20 ms); the edges of a
        # square wave come every few ms, so they stand only ~15x above theirs
        n = int(0.020 * sr)
        loc = np.sqrt(np.convolve(d2 ** 2, np.ones(n) / n, 'same')) + 1e-6
        spikes = np.where((d2 > 20 * loc) & (d2 > 0.02))[0]
        if len(spikes):
            spikes = spikes[np.insert(np.diff(spikes) > int(0.05 * sr), 0, True)]
        cpm = len(spikes) / (dur / 60)
        where = ', '.join('%.2fs' % (s / sr) for s in spikes[:5])
        row('technical', 'clicks', cpm <= L['clicks'],
            '%.1f per minute, limit %g%s' % (cpm, L['clicks'], (' (at ' + where + ')') if len(spikes) else ''))
    l, r = x[:, 0], x[:, 1]
    corr = float((l * r).sum() / np.sqrt((l * l).sum() * (r * r).sum() + 1e-12))
    row('technical', 'stereo', corr > 0.2, 'L/R correlation %.2f, limit > 0.2' % corr)
    mom = blocks
    t = np.arange(len(mom)) * 0.1
    quiet = mom < lufs - 25
    head = float(t[np.argmax(~quiet)]) if (~quiet).any() else dur
    tail = float(dur - 0.4 - t[len(quiet) - 1 - np.argmax(~quiet[::-1])]) if (~quiet).any() else dur
    longest, run = 0.0, 0
    for qv in quiet[int(head * 10):len(quiet) - int(tail * 10)]:
        run = run + 1 if qv else 0
        longest = max(longest, run * 0.1)
    gap_lim = 4.0 if style in ('ambient', 'orchestral') else 1.5
    edge_lim = 0.3 if use == 'loop' else 1.5
    row('technical', 'silence', head <= edge_lim and tail <= (edge_lim if use == 'loop' else 4) and longest <= gap_lim,
        'lead-in %.1fs, tail %.1fs (limit %.1fs), longest dropout %.1fs (limit %.1fs)' % (head, tail, edge_lim, longest, gap_lim))
    if use == 'loop':
        step = float(np.abs(x[0] - x[-1]).max())
        typical = float(np.percentile(np.abs(np.diff(x, axis=0)), 99.9))
        n = int(0.5 * sr)
        lend = integrated(block_loudness(x[-n:], sr, 0.4, 0.05))
        lsta = integrated(block_loudness(x[:n], sr, 0.4, 0.05))
        Se, fe = stft_mag(x[-n:].mean(1), sr, 2048, 512)
        Ss, _ = stft_mag(x[:n].mean(1), sr, 2048, 512)
        ce = float((Se.mean(0) * fe).sum() / (Se.mean(0).sum() + 1e-9))
        cs = float((Ss.mean(0) * fe).sum() / (Ss.mean(0).sum() + 1e-9))
        cr = abs(np.log2(max(ce, 1) / max(cs, 1)))
        ok = step <= max(typical * 1.5, 0.01) and abs(lend - lsta) <= 3 and cr <= 0.5
        row('technical', 'seam', ok, 'wrap jump %.3f (typical %.3f), loudness end %.1f vs start %.1f LUFS, '
            'brightness %.0f vs %.0f Hz' % (step, typical, lend, lsta, ce, cs))
    # mix
    hop = 1024
    S, f = stft_mag(mono, sr, 4096, hop)
    fl = block_loudness(x, sr, 4096 / sr, hop / sr)[:len(S)]
    active = np.zeros(len(S), bool); active[:len(fl)] = fl > lufs - 20
    if active.sum() < 4:
        active[:] = True
    sh = band_shares(S, f, active)
    bad = ['%s %.1f (%g..%g)' % (b, sh[b], *L[b]) for b, _, _ in BANDS if not L[b][0] <= sh[b] <= L[b][1]]
    hint = {'lowmid': 'muddy: thin the chords or pads around 250-2000 Hz', 'highmid': 'harsh or thin top: 2-6 kHz',
            'bass': 'bass level', 'sub': 'sub level', 'air': 'air: hats, noise, brightness above 6 kHz'}
    msg = ', '.join('%s %.1f' % (b, sh[b]) for b, _, _ in BANDS) + ' dB'
    if bad:
        msg += '; outside: ' + '; '.join(bad) + ' (' + '; '.join(hint[b.split()[0]] for b in bad) + ')'
    row('mix', 'balance', not bad, msg)
    tl = tilt(S, f, active)
    row('mix', 'tilt', L['tilt'][0] <= tl <= L['tilt'][1], '%.1f dB/oct, range %g..%g (lower = duller)' % (tl, *L['tilt']))
    plr = tp - lufs
    row('mix', 'dynamics', L['plr'][0] <= plr <= L['plr'][1],
        'peak to loudness %.1f dB, range %g..%g (low = squashed, high = spiky or too quiet)' % (plr, *L['plr']))
    # music
    found_bpm, strength = tempo(S, sr, hop)
    if not L['tempo'] and bpm is None:
        row('music', 'tempo', None, 'free time in %s (beat %.0f bpm, strength %.2f)' % (style, found_bpm, strength))
    else:
        ok = strength >= 0.2
        msg = 'beat %.1f bpm (or a multiple), strength %.2f (limit 0.2)' % (found_bpm, strength)
        if bpm:
            ratios = [found_bpm / bpm * m for m in (1, 2, 0.5, 1.5, 2 / 3)]
            ok = ok and any(abs(r_ - 1) < 0.02 for r_ in ratios)
            msg += ', asked %g' % bpm
        row('music', 'tempo', ok, msg)
    C = chroma(S, f)
    kname, kc, outk = key_of(C[active])
    ok = kc >= L['key_min'] and outk <= L['out_key']
    msg = '%s, clarity %.2f (limit %.2f), outside the key %.0f%% (limit %.0f%%)' % (kname, kc, L['key_min'], outk * 100, L['out_key'] * 100)
    if key:
        ok = ok and same_key(key, kname)
        msg += ', asked %s' % key
    row('music', 'key', ok, msg)
    use_bpm = bpm or found_bpm
    F = bar_features(S, f, C, sr, hop, use_bpm)
    v, nbars = variety(F)
    vlim = L['variety'] if use != 'showcase' else max(L['variety'], 0.45)
    row('music', 'variety', v >= vlim if nbars >= 4 else None,
        '%.0f%% of %d bars are new (limit %.0f%%); a lower share means it repeats itself' % (v * 100, nbars, vlim * 100))
    notes = melody(S, f, sr, hop)
    n_hook, phrase = hook(notes)
    if use == 'showcase':
        row('music', 'hook', n_hook >= HOOK_MIN, 'best %d-note phrase heard %d times (limit %d), intervals %s, %d melody notes'
            % (HOOK_LEN, n_hook, HOOK_MIN, list(phrase), len(notes)))
    else:
        row('music', 'hook', None, 'best %d-note phrase heard %d times (checked for --use showcase)' % (HOOK_LEN, n_hook))
    sec = max(4.0, dur / 8)
    ns = int(dur // sec)
    lev = [integrated(blocks[int(i * sec * 10):int((i + 1) * sec * 10)]) for i in range(ns)]
    dens = [float(onset_env(S[int(i * sec * sr / hop):int((i + 1) * sec * sr / hop)]).mean()) for i in range(ns)]
    spread = (max(lev) - min(lev)) if ns >= 3 else 0.0
    dspread = (max(dens) / max(min(dens), 1e-6)) if ns >= 3 else 1.0
    if use in ('showcase', 'song') and ns >= 3:
        row('music', 'arc', spread >= ARC_MIN or dspread >= 2.0,
            'sections of %.0fs: loudness spread %.1f dB (limit %.1f) or density x%.1f (limit x2)' % (sec, spread, ARC_MIN, dspread))
    else:
        row('music', 'arc', None, 'loudness spread %.1f dB over %d sections (checked for showcase and song)' % (spread, ns))
    if data is not None:
        data.update(S=S, f=f, C=C, F=F, blocks=blocks, lufs=lufs, hop=hop, notes=notes, bpm=use_bpm, dur=dur, sr=sr)
    return rows

# ------------------------------------------------------------------ the ear sheet
def sheet(d, out, title=''):
    """Spectrogram (log frequency), loudness, pitch classes and bar similarity in one picture."""
    from PIL import Image, ImageDraw
    S, f, C, F = d['S'], d['f'], d['C'], d['F']
    W, H = 1200, 260
    fr = np.geomspace(40, 16000, H)
    idx = np.searchsorted(f, fr).clip(0, len(f) - 1)
    cols = np.linspace(0, len(S) - 1, W).astype(int)
    spec = db(S[cols][:, idx] ** 2)
    spec = ((spec - (spec.max() - 80)) / 80).clip(0, 1).T[::-1]
    ramp = np.array([[8, 10, 24], [40, 30, 90], [140, 40, 110], [230, 110, 60], [250, 230, 150]], float)
    def colour(v):
        p = v * (len(ramp) - 1); i = np.minimum(p.astype(int), len(ramp) - 2); t = (p - i)[..., None]
        return (ramp[i] * (1 - t) + ramp[i + 1] * t).astype(np.uint8)
    loud = np.zeros((90, W, 3), np.uint8) + 16
    b = d['blocks']; bi = np.linspace(0, len(b) - 1, W).astype(int)
    y = ((b[bi] + 40) / 40).clip(0, 1)
    for xx in range(W):
        loud[90 - int(y[xx] * 88):, xx] = (120, 200, 160)
    ch = colour(C[cols].T[::-1] / max(C.max(), 1e-9) * 1.4 % 1.0001)
    ch = np.repeat(ch, 8, 0)
    top = np.concatenate([colour(spec), loud, ch], 0)
    n = len(F)
    side = 240
    if n >= 2:
        Z = F - F.mean(0); Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
        sim = ((Z @ Z.T + 1) / 2) ** 3
        sm = colour(sim)
        sm = np.array(Image.fromarray(sm).resize((side, side), Image.NEAREST))
    else:
        sm = np.zeros((side, side, 3), np.uint8)
    canvas = Image.new('RGB', (W + side + 30, top.shape[0] + 40), (16, 16, 20))
    canvas.paste(Image.fromarray(top), (10, 30))
    canvas.paste(Image.fromarray(sm), (W + 20, 30))
    g = ImageDraw.Draw(canvas)
    g.text((10, 8), '%s  %.1fs  %.1f LUFS  %.0f bpm   spectrogram 40 Hz-16 kHz | loudness | pitch classes C..B' %
           (title, d['dur'], d['lufs'], d['bpm']), fill=(220, 220, 220))
    g.text((W + 20, 8), 'bar vs bar (bright = same)', fill=(220, 220, 220))
    for sec in range(0, int(d['dur']) + 1, 10):
        xx = 10 + int(sec / d['dur'] * W)
        g.line([(xx, 30 + H), (xx, 34 + H)], fill=(200, 200, 200))
    canvas.save(out)
    return out

def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__); return 2
    path = argv[0]
    opt = {'--style': 'any', '--use': 'loop', '--bpm': None, '--key': None, '--sheet': None}
    js = '--json' in argv
    a = [v for v in argv[1:] if v != '--json']
    for i in range(0, len(a) - 1, 2):
        if a[i] not in opt:
            sys.exit('unknown option ' + a[i])
        opt[a[i]] = a[i + 1]
    if opt['--use'] not in USES:
        sys.exit('uses: ' + ', '.join(USES))
    x, sr = load(path)
    data = {}
    rows = report(x, sr, opt['--style'], opt['--use'], float(opt['--bpm']) if opt['--bpm'] else None, opt['--key'], data)
    if opt['--sheet']:
        sheet(data, opt['--sheet'], pathlib.Path(path).name)
    if js:
        print(json.dumps([dict(group=g, check=c, result=s, detail=m) for g, c, s, m in rows], indent=1))
    else:
        print('%s: %.1f s, style %s, use %s' % (path, len(x) / sr, opt['--style'], opt['--use']))
        for g, c, s, m in rows:
            print('%-4s %-9s %-9s %s' % (s, g, c, m))
        if opt['--sheet']:
            print('ear sheet: %s (look at it)' % opt['--sheet'])
    return 1 if any(s == 'FAIL' for _, _, s, _ in rows) else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
