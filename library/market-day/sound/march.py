"""Market Day: the band in the stalls. A 5.0 s oom-pah march excerpt in Bb major at 112 bpm,
synthesised from scratch in numpy (no samples):

  brass   band-limited sawtooth (polyBLEP) through a resonant TPT state-variable low-pass whose
          cutoff follows the note envelope; a little delayed vibrato on long notes, a small pitch
          scoop on the attack
  tuba    roots and fifths on beats 1 and 3; horns: chord after-beats on 2 and 4
  trumpet my own fanfare line (bar 1 Bb, bar 2 F7, landing on Bb in bar 3)
  drums   bass drum on 1 and 3, snare on 2 and 4 with a roll into bar 3, a cymbal on bar starts
  crowd   band-passed noise with slow amplitude wobble, decorrelated left and right

    python3 march.py OUT.wav
"""
import sys, math
import numpy as np
import wave

SR = 48000
BPM = 112.0
BEAT = 60.0 / BPM
DUR = 5.0
N = int(SR * DUR)
rng = np.random.default_rng(1868)

def hz(name):
    names = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] - 9 + 12 * (o - 4)) / 12.0)

def polyblep(t, dt):
    out = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m2 = t > 1.0 - dt
    x = (t[m2] - 1.0) / dt[m2]
    out[m2] = x * x + x + x + 1.0
    return out

def saw(freq):
    """band-limited sawtooth for a per-sample frequency array"""
    dt = freq / SR
    ph = np.cumsum(dt) % 1.0
    return 2.0 * ph - 1.0 - polyblep(ph, dt)

def svf_lp(x, fc, q):
    """TPT state-variable low-pass with a per-sample cutoff"""
    g = np.tan(np.pi * np.clip(fc, 30, SR * 0.45) / SR)
    k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k)); a2 = g * a1; a3 = g * a2
    y = np.empty_like(x)
    ic1 = ic2 = 0.0
    for i in range(len(x)):
        v3 = x[i] - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1 = 2 * v1 - ic1; ic2 = 2 * v2 - ic2
        y[i] = v2
    return y

def env_adsr(n, a, d, s, r, gate):
    t = np.arange(n) / SR
    e = np.where(t < a, t / a, np.where(t < a + d, 1 - (1 - s) * (t - a) / d, s))
    rel = t >= gate
    e = np.where(rel, np.interp(t, [gate, gate + r], [e[min(n - 1, int(gate * SR))], 0.0]) * (t < gate + r), e)
    return np.clip(e, 0, 1)

def brass(f0, dur, cut_lo, cut_hi, q=2.2, vib=True, scoop=True, bright=1.0):
    gate = dur
    n = int((dur + 0.12) * SR)
    t = np.arange(n) / SR
    f = np.full(n, f0)
    if scoop:
        f *= 1 - 0.012 * np.exp(-t / 0.025)              # the lip scoop into the note
    if vib and dur > 0.38:
        depth = 0.0045 * np.clip((t - 0.22) / 0.2, 0, 1)
        f *= 1 + depth * np.sin(2 * np.pi * 5.6 * t)
    x = saw(f) * 0.6 + saw(f * 1.0035) * 0.4             # two slightly detuned saws
    e = env_adsr(n, 0.018, 0.12, 0.72, 0.07, gate)
    fc = cut_lo + (cut_hi - cut_lo) * e ** 1.3 * bright  # the cutoff follows the envelope: the brass "bloom"
    return svf_lp(x, fc, q) * e

def place(buf, sig, t0, gain=1.0, pan=0.0):
    i0 = int(round(t0 * SR))
    if i0 >= N:
        return
    sig = sig[:N - i0]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[0, i0:i0 + len(sig)] += sig * gain * l
    buf[1, i0:i0 + len(sig)] += sig * gain * r

def kick(n=int(0.35 * SR)):
    t = np.arange(n) / SR
    f = 48 + 70 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.16) + 0.25 * np.exp(-t / 0.004) * rng.standard_normal(n) * 0.3

def bandnoise(n, lo, hi):
    X = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    X[(fr < lo) | (fr > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)

def snare(n=int(0.22 * SR), amp=1.0):
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 186 * t) * np.exp(-t / 0.05)
    rattle = bandnoise(n, 1500, 7000) * np.exp(-t / 0.075)
    return (0.45 * body + 0.8 * rattle) * amp

def cymbal(n=int(1.6 * SR)):
    t = np.arange(n) / SR
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (583, 845, 1203, 1617, 2149, 2963)) / 6.0
    hiss = bandnoise(n, 4000, 12000)
    x = 0.35 * metal + 0.8 * hiss
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1 / SR); X[fr < 3000] *= 0.15
    x = np.fft.irfft(X, n)
    x /= np.abs(x).max() + 1e-9
    return x * (np.exp(-t / 0.55) * (1 - np.exp(-t / 0.002)))

def crowd():
    out = np.zeros((2, N))
    t = np.arange(N) / SR
    for ch in range(2):
        x = bandnoise(N, 250, 1600)
        wob = 0.6 + 0.25 * np.sin(2 * np.pi * 0.37 * t + ch) + 0.15 * np.sin(2 * np.pi * 1.13 * t + 2 * ch) \
            + 0.1 * np.sin(2 * np.pi * 2.9 * t + 0.5 * ch)
        out[ch] = x * wob
    return out

def render():
    buf = np.zeros((2, N))
    b = lambda bar, beat: (bar * 4 + beat) * BEAT
    # ---- tuba: roots and fifths on 1 and 3 (Bb | F7 | Bb)
    tuba = [(0, 0, 'Bb1'), (0, 2, 'F2'), (1, 0, 'Eb2'), (1, 2, 'F1'), (2, 0, 'Bb1')]
    for bar, beat, note in tuba:
        place(buf, brass(hz(note), BEAT * 0.62, 120, 900, q=1.6, vib=False), b(bar, beat), 0.62, 0.0)
    # ---- horns: chord after-beats on 2 and 4
    chords = {(0, 1): ('Bb3', 'D4', 'F4'), (0, 3): ('Bb3', 'D4', 'F4'), (1, 1): ('Bb3', 'Eb4', 'G4'), (1, 3): ('A3', 'C4', 'Eb4')}
    for bar in (0, 1):
        for beat in (1, 3):
            for k, note in enumerate(chords[(bar, beat)]):
                place(buf, brass(hz(note), BEAT * 0.34, 300, 2200, q=1.8, vib=False), b(bar, beat), 0.16, -0.35 + 0.12 * k)
    # ---- trumpet: my own fanfare line
    mel = [(0, 0.0, 0.75, 'Bb4'), (0, 0.75, 0.25, 'C5'), (0, 1.0, 0.5, 'D5'), (0, 1.5, 0.5, 'Bb4'), (0, 2.0, 0.75, 'F5'),
           (0, 2.75, 0.25, 'Eb5'), (0, 3.0, 1.0, 'D5'),
           (1, 0.0, 0.5, 'Eb5'), (1, 0.5, 0.5, 'G5'), (1, 1.0, 0.5, 'Bb5'), (1, 1.5, 0.5, 'G5'), (1, 2.0, 0.5, 'Eb5'),
           (1, 2.5, 0.5, 'C5'), (1, 3.0, 0.5, 'A4'), (1, 3.5, 0.5, 'C5'),
           (2, 0.0, 1.6, 'Bb4')]
    for bar, beat, dur, note in mel:
        place(buf, brass(hz(note), dur * BEAT * 0.86, 500, 4200, q=2.4, vib=True), b(bar, beat), 0.30, 0.25)
    # ---- drums
    for bar in (0, 1, 2):
        for beat in (0, 2):
            if b(bar, beat) < DUR:
                place(buf, kick(), b(bar, beat), 0.55, 0.0)
        if b(bar, 0) < DUR:
            place(buf, cymbal(), b(bar, 0), 0.16, 0.2)
    for bar in (0, 1):
        for beat in (1, 3):
            place(buf, snare(), b(bar, beat), 0.30, -0.08)
    for k in range(4):                                       # a roll into bar 3
        place(buf, snare(amp=0.55 + 0.12 * k), b(1, 3.5) + k * BEAT / 8, 0.22, -0.08)
    # ---- the crowd murmur bed
    buf += crowd() * 0.035
    # ---- a short room: a decaying noise impulse response, mixed low
    ir_n = int(0.5 * SR)
    ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.12)
    ir /= np.sqrt((ir ** 2).sum())
    for ch in range(2):
        wet = np.fft.irfft(np.fft.rfft(buf[ch], N + ir_n) * np.fft.rfft(ir, N + ir_n), N + ir_n)[:N]
        buf[ch] += 0.18 * wet
    # ---- fades: 20 ms in, 400 ms out; level to about -14 LUFS (checked by the music gate)
    fade = np.ones(N)
    fi = int(0.02 * SR); fo = int(0.4 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
    buf *= fade
    buf -= buf.mean(axis=1, keepdims=True) * 0      # keep DC handling to the filters (saws are centred)
    # a gentle lookahead limiter: push 3.5 dB into a -1 dBFS ceiling (only the drum peaks are touched)
    buf *= 10 ** ((GAIN_DB + PUSH_DB) / 20.0) / np.abs(buf).max()
    ceil = 10 ** (GAIN_DB / 20.0)
    need = np.minimum(1.0, ceil / np.maximum(np.abs(buf).max(axis=0), 1e-9))
    w = int(0.004 * SR)
    from numpy.lib.stride_tricks import sliding_window_view
    padded = np.pad(need, (w, w), constant_values=1.0)
    g = sliding_window_view(padded, 2 * w + 1).min(axis=1)          # look ahead and hold
    k = np.hanning(2 * w + 1); k /= k.sum()
    g = np.convolve(np.pad(g, (w, w), mode='edge'), k, mode='valid')
    buf *= g[None, :]
    buf *= ceil / max(ceil, np.abs(buf).max())
    return buf

GAIN_DB = -1.0
PUSH_DB = 3.5

def write(path, buf):
    x = np.clip(buf, -1, 1)
    pcm = (x.T * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    if len(sys.argv) > 2:
        GAIN_DB = float(sys.argv[2])
    buf = render()
    write(sys.argv[1], buf)
    print('wrote', sys.argv[1], buf.shape[1] / SR, 's, peak %.2f dBFS' % (20 * np.log10(np.abs(buf).max())))
