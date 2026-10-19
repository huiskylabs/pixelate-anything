"""'Lift-off', an original 8-bar theme for 05 Four Machines, in a 16-bit arrangement, synthesised
with numpy (no samples). D major, 116 bpm, 4/4.

  theme   bars 1-4 state it (D | A/C# | Bm | G A), bars 5-8 lift it: a rising sequence over G | A that
          lands on a held high F# over D at the bar 7 downbeat (the glider leaving the rail), then G A.
  voices  string ensemble (5 detuned saws per note, slow attack, gentle low-pass, spread wide),
          2-operator FM bass (index falls after each attack), FM bell-pluck lead (ratio 3.5) with a
          quiet square an octave down for body, light kit (sine-drop kick, noise+tone snare, closed hat),
          stereo ping-pong echo (dotted eighth) on the lead and a small feedback-delay reverb.
  sample  5.0 s from the bar 5 downbeat (bars 5-7: the best rising phrase), 20 ms fade-in, 400 ms fade-out.

Run: python3 sound/theme.py -> sound/05-sample.wav (48 kHz, 16-bit, stereo); then ffmpeg for the mp3.
"""
import pathlib
import numpy as np
from scipy.signal import lfilter, butter

SR = 48000
BPM = 116
BEAT = 60.0 / BPM
BAR = 4 * BEAT
HERE = pathlib.Path(__file__).resolve().parent

def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)

# ---------------------------------------------------------------- the score (beats from bar 1)
CHORDS = [  # (start beat, length, bass midi, voicing midis)
    (0, 4, 38, [62, 66, 69, 74]),       # D
    (4, 4, 37, [61, 64, 69, 73]),       # A/C#
    (8, 4, 35, [62, 66, 71, 74]),       # Bm
    (12, 2, 31, [62, 67, 71, 74]),      # G
    (14, 2, 33, [61, 64, 69, 73]),      # A
    (16, 4, 31, [59, 62, 67, 74]),      # G      (bar 5: the lift begins)
    (20, 4, 33, [61, 64, 69, 76]),      # A
    (24, 4, 38, [62, 66, 69, 78]),      # D      (bar 7: the arrival)
    (28, 2, 31, [62, 67, 71, 74]),      # G
    (30, 2, 33, [61, 64, 69, 76]),      # A
]
LEAD = [  # (beat, length, midi)
    # bars 1-4: the statement
    (0, 1, 78), (1, .5, 81), (1.5, .5, 78), (2, 1, 76), (3, 1, 74),
    (4, 1.5, 76), (5.5, .5, 73), (6, 2, 69),
    (8, .5, 71), (8.5, .5, 73), (9, .5, 74), (9.5, .5, 78), (10, 1, 76), (11, .5, 74), (11.5, .5, 71),
    (12, 1, 74), (13, 1, 73), (14, .5, 71), (14.5, .5, 73), (15, 1, 76),
    # bars 5-7: the rising sequence and the held peak
    (16, .5, 74), (16.5, .5, 76), (17, 1, 79), (18, 1, 83), (19, .5, 81), (19.5, .5, 79),
    (20, .5, 81), (20.5, .5, 83), (21, 1, 85), (22, 1, 88), (23, .5, 86), (23.5, .5, 88),
    (24, 3.5, 90),
    # bar 8: the answer
    (28, 1, 86), (29, .5, 83), (29.5, .5, 81), (30, 2, 88),
]

def bass_line():
    notes = []
    for start, length, root, _ in CHORDS:
        for k in range(int(length * 2)):                       # eighths: root root octave root ...
            pat = [0, 0, 12, 0, 7, 0, 12, 7][k % 8]
            notes.append((start + k * 0.5, 0.45, root + pat))
    return notes

def drums():
    hits = []
    for bar in range(8):
        b = bar * 4
        hits += [('kick', b), ('kick', b + 2), ('kick', b + 2.5) if bar % 2 else ('kick', b + 2), ('snare', b + 1), ('snare', b + 3)]
        sub = 0.25 if bar == 5 else 0.5                         # bar 6 builds with sixteenth hats
        hits += [('hat', b + k * sub) for k in range(int(4 / sub))]
    hits += [('snare', 23.5), ('snare', 23.75), ('splash', 24)]
    return hits

# ---------------------------------------------------------------- voices
def env_adsr(n, a, d, s, r, rel_start):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = t >= rel_start
    e[rel] = e[rel] * np.exp(-(t[rel] - rel_start) / max(r, 1e-4))
    return e

def saw(f, t, phase=0.0):
    x = (f * t + phase) % 1.0
    return 2 * x - 1

def strings(total):
    out = np.zeros((total, 2))
    detunes = [-11, -5, 0, 6, 12]
    pans = [-0.7, -0.35, 0, 0.35, 0.7]
    rng = np.random.default_rng(4)
    b, a = butter(2, 2600 / (SR / 2))
    for start, length, _, voicing in CHORDS:
        i0 = int(start * BEAT * SR)
        dur = length * BEAT
        n = int((dur + 0.9) * SR)
        t = np.arange(n) / SR
        e = env_adsr(n, 0.28, 0.6, 0.85, 0.45, dur)
        for m in voicing:
            for dc, pn in zip(detunes, pans):
                f = midi(m) * 2 ** (dc / 1200.0)
                v = saw(f, t, rng.random()) * e * 0.018
                v = lfilter(b, a, v)
                seg = out[i0:i0 + n]
                L = len(seg)
                seg[:, 0] += v[:L] * (0.5 - pn / 2) ** 0.5
                seg[:, 1] += v[:L] * (0.5 + pn / 2) ** 0.5
    return out

def fm_bass(total):
    out = np.zeros(total)
    for beat, length, m in bass_line():
        i0 = int(beat * BEAT * SR)
        n = int((length * BEAT + 0.12) * SR)
        t = np.arange(n) / SR
        f = midi(m)
        index = 2.6 * np.exp(-t / 0.07) + 0.5                  # bright attack, rounder body
        mod = np.sin(2 * np.pi * f * t)
        car = np.sin(2 * np.pi * f * t + index * mod)
        sub = np.sin(2 * np.pi * f * t) * 0.5
        e = env_adsr(n, 0.004, 0.18, 0.55, 0.05, length * BEAT)
        v = (car * 0.6 + sub) * e * 0.20
        seg = out[i0:i0 + n]
        seg += v[:len(seg)]
    return out

def lead(total):
    out = np.zeros(total)
    for beat, length, m in LEAD:
        i0 = int(beat * BEAT * SR)
        dur = length * BEAT
        n = int((dur + 1.2) * SR)
        t = np.arange(n) / SR
        f = midi(m)
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.35) / 0.4, 0, 1)
        index = 3.2 * np.exp(-t / 0.09) + 0.35                 # the bell's bright strike, then a pure tone
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        car = np.sin(ph + index * np.sin(3.5 * ph))
        hold = 0.75 if length < 2 else 0.9
        e = np.exp(-t / (0.35 if length < 2 else 1.6)) * (1 - hold) + hold * env_adsr(n, 0.003, 0.25, 0.55, 0.18, dur)
        e *= np.clip(t / 0.003, 0, 1)
        sq = np.sign(np.sin(ph / 2)) * 0.06 * env_adsr(n, 0.01, 0.2, 0.6, 0.12, dur)
        v = (car * 0.17 * e + sq) * (1.0 if m < 88 else 0.9)
        seg = out[i0:i0 + n]
        seg += v[:len(seg)]
    b, a = butter(2, 7000 / (SR / 2))
    return lfilter(b, a, out)

def kit(total):
    out = np.zeros(total)
    rng = np.random.default_rng(7)
    for kind, beat in drums():
        i0 = int(beat * BEAT * SR)
        if kind == 'kick':
            n = int(0.35 * SR); t = np.arange(n) / SR
            f = 48 + 90 * np.exp(-t / 0.03)
            v = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.14) * 0.55
        elif kind == 'snare':
            n = int(0.22 * SR); t = np.arange(n) / SR
            noise = rng.standard_normal(n)
            b, a = butter(2, [1500 / (SR / 2), 8000 / (SR / 2)], 'band')
            v = (lfilter(b, a, noise) * np.exp(-t / 0.06) * 0.30 +
                 np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.16)
        elif kind == 'hat':
            n = int(0.06 * SR); t = np.arange(n) / SR
            b, a = butter(2, 7500 / (SR / 2), 'high')
            v = lfilter(b, a, rng.standard_normal(n)) * np.exp(-t / 0.014) * 0.09
        else:                                                    # a soft splash on the arrival
            n = int(1.4 * SR); t = np.arange(n) / SR
            b, a = butter(2, 5000 / (SR / 2), 'high')
            v = lfilter(b, a, rng.standard_normal(n)) * np.exp(-t / 0.45) * 0.07
        seg = out[i0:i0 + n]
        seg += v[:len(seg)]
    return out

def pingpong(x, delay, fb, mix):
    d = int(delay * SR)
    L = np.zeros(len(x)); R = np.zeros(len(x))
    for k in range(1, 6):                                       # taps alternate sides, each fb quieter
        g = mix * fb ** (k - 1)
        if k * d >= len(x):
            break
        (L if k % 2 else R)[k * d:] += x[:-k * d] * g
    return L, R

def reverb(stereo, mix=0.16):
    out = np.zeros_like(stereo)
    for ch, delays in enumerate(([1557, 1617, 1491, 1422], [1277, 1356, 1188, 1116])):
        y = np.zeros(len(stereo))
        for dl in delays:
            a = np.zeros(dl + 1); a[0] = 1; a[dl] = -0.78
            y += lfilter([1.0], a, stereo[:, ch])
        for dl in (225, 556):
            y = lfilter(np.r_[-0.5, np.zeros(dl - 1), 1.0], np.r_[1.0, np.zeros(dl - 1), -0.5], y)
        b, a2 = butter(1, 5000 / (SR / 2))
        out[:, ch] = lfilter(b, a2, y) * 0.12
    return stereo * (1 - mix) + out * mix * 4

def render():
    total = int((8 * BAR + 2.0) * SR)
    mix = strings(total)
    bass = fm_bass(total)
    ld = lead(total)
    drm = kit(total)
    eL, eR = pingpong(ld, 0.75 * BEAT, 0.42, 0.30)
    mix[:, 0] += bass + ld * 0.95 + eL + drm
    mix[:, 1] += bass + ld * 0.95 + eR + drm
    mix = reverb(mix)
    return mix

def excerpt(mix, start_bar=4, seconds=5.0, fade_in=0.02, fade_out=0.4, gain=1.0):
    i0 = int(start_bar * BAR * SR)
    n = int(seconds * SR)
    b, a = butter(2, 25 / (SR / 2), 'high')                      # block DC and sub-rumble first
    hp = lfilter(b, a, mix, axis=0)
    x = hp[i0:i0 + n].copy() * gain
    x -= x.mean(axis=0)
    t = np.arange(n) / SR
    x *= np.clip(t / fade_in, 0, 1)[:, None]
    x *= np.clip((seconds - t) / fade_out, 0, 1)[:, None] ** 1.5
    lim = 10 ** (-1.0 / 20)                                      # a soft limiter: tanh knee under -1 dBFS
    x = lim * np.tanh(x / lim)
    return x

def save_wav(x, path):
    import wave
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    import sys
    gain = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    m = render()
    x = excerpt(m, gain=gain)
    save_wav(x, HERE / '05-sample.wav')
    rms = np.sqrt((x ** 2).mean())
    print('wrote 05-sample.wav: %.3f s, peak %.2f dBFS, rms %.1f dBFS' % (len(x) / SR, 20 * np.log10(np.abs(x).max()), 20 * np.log10(rms)))
