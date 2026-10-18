"""The 5 s overworld sample: the engine's chiptune comp, bass and drums (music/, mel: 0) with the
leitmotif lead written note by note here, then cut from bar 1 with a 20 ms fade-in and a 400 ms
fade-out.

Leitmotif (A major): E5 F#5 C#6 B5 E6, sol la mi re sol: a step up, a fifth up, a step down, a fourth
up, ending open on the fifth like a beacon turning. Rhythm in 16ths: 2 2 4 2 6 ("da-da DAA da DAAAA").
Over E it is answered by a closing phrase (E5 F#5 B5 G#5 E5); over F#m it states itself again.
Lead: a 25% pulse (polyBLEP edges), volume on a 4-bit (16-level) envelope stepped at 60 Hz, a
delayed 60 Hz-stepped vibrato, and a dotted-eighth echo on the other side.
"""
import sys, pathlib, subprocess
sys.path.insert(0, '/home/user/pixelate-anything/tools')
import numpy as np
import musiccheck as mc

HERE = pathlib.Path(__file__).resolve().parent
SND = HERE.parent / 'sound'
SR, BPM = 48000, 132
S16 = 60.0 / BPM / 4

def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)

MOTIF = [(76, 0, 2), (78, 2, 2), (85, 4, 4), (83, 8, 2), (88, 10, 6)]          # E5 F#5 C#6 B5 E6
ANSWER = [(76, 0, 2), (78, 2, 2), (83, 4, 4), (80, 8, 2), (76, 10, 6)]         # E5 F#5 B5 G#5 E5
LEAD = [(m, 0 + s, d) for m, s, d in MOTIF] + [(m, 16 + s, d) for m, s, d in ANSWER] + \
       [(m, 32 + s, d) for m, s, d in MOTIF] + [(m, 48 + s, d) for m, s, d in ANSWER]

def pulse(f, n, duty=0.25, phase0=0.0):
    """band-limited pulse: naive pulse with polyBLEP at both edges, f may vary per sample"""
    inc = f / SR
    ph = (phase0 + np.cumsum(inc)) % 1.0
    def blep(t, dt):
        out = np.zeros_like(t)
        a = t < dt
        x = t[a] / dt[a]; out[a] = x + x - x * x - 1
        b = t > 1 - dt
        x = (t[b] - 1) / dt[b]; out[b] = x * x + x + x + 1
        return out
    y = np.where(ph < duty, 1.0, -1.0)
    y += blep(ph, inc)
    y -= blep((ph - duty) % 1.0, inc)
    return y - (2 * duty - 1)              # remove the DC of an asymmetric pulse

def env4(n, dur_s):
    """the 4-bit volume envelope, one level per 60 Hz frame: 12 at the attack, down to 8, release"""
    frames = int(np.ceil(n / (SR / 60)))
    lv = []
    for k in range(frames):
        t = k / 60.0
        if t < dur_s - 0.03:
            v = 12 if k == 0 else max(8, 12 - k // 2)
        else:
            v = max(0, 8 - 3 * int((t - (dur_s - 0.03)) * 60 + 1))
        lv.append(v)
    e = np.repeat(np.array(lv, float) / 15.0, int(SR / 60) + 1)[:n]
    return e

def lead(total_s):
    n_tot = int(total_s * SR)
    out = np.zeros(n_tot)
    for m, st, d in LEAD:
        t0 = st * S16
        dur = d * S16 - 0.012                      # a short gap between notes
        n = int((dur + 0.06) * SR)
        i0 = int(t0 * SR)
        if i0 >= n_tot:
            continue
        n = min(n, n_tot - i0)
        t = np.arange(n) / SR
        # vibrato after 180 ms, +-14 cents at 5.6 Hz, held per 60 Hz frame
        tf = np.floor(t * 60) / 60
        vib = np.where(tf > 0.18, 14 * np.sin(2 * np.pi * 5.6 * (tf - 0.18)), 0.0)
        f = midi_hz(m) * 2 ** (vib / 1200)
        y = pulse(f, n) * env4(n, dur)
        out[i0:i0 + n] += y
    return out

def load_engine():
    d = open(SND / 'full.wav', 'rb').read()
    return np.frombuffer(d[44:], dtype='<f4').reshape(-1, 2).astype(np.float64)

def limiter(x, thr):
    """look-ahead peak limiter: gain from the 4 ms windowed peak, fast attack, 80 ms release"""
    a = np.abs(x).max(1)
    w = int(0.004 * SR)
    pk = np.array([a[max(0, i - w):i + w].max() for i in range(0, len(a), w)])
    g = np.minimum(1.0, thr / np.maximum(pk, 1e-9))
    rel = np.exp(-w / (0.08 * SR))
    for i in range(1, len(g)):
        g[i] = min(g[i], g[i - 1] * rel + (1 - rel))
    for i in range(len(g) - 2, -1, -1):
        g[i] = min(g[i], g[i + 1] * rel + (1 - rel))
    gs = np.interp(np.arange(len(a)), np.arange(len(g)) * w + w / 2, g)
    return x * gs[:, None]

def main():
    eng = load_engine()
    L = 5.0
    n = int(L * SR)
    ld = lead(L + 0.5)[:n]
    # echo: a dotted eighth later, on the right, 30% and duller (a one-pole low-pass)
    dl = int(3 * S16 * SR)
    echo = np.zeros(n); echo[dl:] = ld[:n - dl] * 0.30
    for i in range(1, n):
        echo[i] = echo[i - 1] + 0.35 * (echo[i] - echo[i - 1])
    mix = eng[:n] * 0.82
    # a gentle low shelf on the engine stem (triangle bass and kick ran 1 dB too heavy): -4 dB under ~190 Hz
    a = np.exp(-2 * np.pi * 190 / SR)
    low = np.zeros_like(mix)
    for i in range(1, n):
        low[i] = a * low[i - 1] + (1 - a) * mix[i]
    mix = mix - (1 - 10 ** (-4 / 20)) * low
    lead_amp = 0.14
    mix[:, 0] += lead_amp * (ld * 0.92 + echo * 0.35)
    mix[:, 1] += lead_amp * (ld * 0.80 + echo * 1.0)
    # loudness to about -14 LUFS, true peak under -1 dBFS
    for _ in range(3):
        lufs = mc.integrated(mc.block_loudness(mix.astype(np.float32), SR))
        mix *= 10 ** ((-14.0 - lufs) / 20)
        mix = limiter(mix, 10 ** (-1.3 / 20))
    # fades: 20 ms in, 400 ms out (raised cosine)
    fi = int(0.020 * SR); fo = int(0.400 * SR)
    mix[:fi] *= (0.5 - 0.5 * np.cos(np.pi * np.arange(fi) / fi))[:, None]
    mix[-fo:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(fo) / fo))[:, None]
    mix -= mix.mean(0)
    # 16-bit with TPDF dither
    rng = np.random.default_rng(10)
    q = np.clip(np.round(mix * 32767 + rng.random(mix.shape) - rng.random(mix.shape)), -32768, 32767).astype('<i2')
    import wave
    with wave.open(str(SND / '10-sample.wav'), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(q.tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(SND / '10-sample.wav'), '-codec:a', 'libmp3lame',
                    '-q:a', '2', str(SND / '10-sample.mp3')], check=True)
    lufs = mc.integrated(mc.block_loudness(mix.astype(np.float32), SR))
    print('wrote', SND / '10-sample.wav', '%.3f s' % (len(q) / SR), 'LUFS %.1f' % lufs,
          'peak %.2f dBFS' % (20 * np.log10(np.abs(mix).max())))

if __name__ == '__main__':
    main()
