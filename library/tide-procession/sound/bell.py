"""A struck bronze bell, synthesised in numpy (the engine has no bell voice).

Inharmonic partials at 1, 2.0, 2.4, 3.0 and 4.2 times the fundamental (prime, nominal, the tierce an
octave up, the quint an octave up, an upper partial), plus a faint hum at 0.5; each partial is a
slightly detuned pair so it beats slowly the way a cast bell warbles, with its own long, unequal decay.
The strike is soft (a padded clapper): a 6 ms rise on the partials and a short, darkened noise tick.

    from bell import bell
    y = bell(48000, 146.83, 5.0)      # (n, 2) float, peak about 0.5
"""
import numpy as np
from scipy import signal

# (ratio, level, T60 seconds, beat Hz, pan -1..1)
PARTIALS = [(0.5, 0.18, 11.0, 0.21, -0.1), (1.0, 0.60, 8.5, 0.37, 0.05), (2.0, 0.42, 6.0, 0.62, -0.15),
            (2.4, 0.30, 4.6, 0.83, 0.2), (3.0, 0.22, 3.1, 1.10, -0.25), (4.2, 0.15, 1.7, 1.55, 0.3),
            (5.4, 0.07, 0.9, 2.0, -0.3), (6.8, 0.04, 0.6, 2.6, 0.25)]


def bell(sr=48000, f0=146.83, dur=5.0, seed=7):
    n = int(sr * dur)
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)
    out = np.zeros((n, 2))
    rise = np.clip(t / 0.006, 0, 1) ** 2                       # soft strike: 6 ms rise
    for ratio, lev, t60, beat, pan in PARTIALS:
        f = f0 * ratio
        if f > sr / 2.2:
            continue
        env = lev * rise * np.exp(-6.91 * t / t60)
        ph = rng.uniform(0, 2 * np.pi, 2)
        tone = 0.5 * (np.sin(2 * np.pi * (f - beat / 2) * t + ph[0]) +
                      np.sin(2 * np.pi * (f + beat / 2) * t + ph[1]))
        g = env * tone
        out[:, 0] += g * np.sqrt(0.5 * (1 - pan))
        out[:, 1] += g * np.sqrt(0.5 * (1 + pan))
    # the strike tick: 14 ms of noise, low-passed so the clapper sounds padded, not metallic
    k = int(0.014 * sr)
    tick = rng.standard_normal(k) * np.exp(-np.arange(k) / (0.004 * sr))
    b, a = signal.butter(2, 4000 / (sr / 2))
    tick = signal.lfilter(b, a, tick) * 0.25
    out[:k, 0] += tick
    out[:k, 1] += tick * 0.9
    # a small stone room: a decaying noise tail, mixed low, so the bell sits with the pad
    ir_n = int(1.6 * sr)
    ir = rng.standard_normal((ir_n, 2)) * np.exp(-6.91 * np.arange(ir_n) / (1.6 * sr))[:, None]
    b, a = signal.butter(2, 3200 / (sr / 2))
    ir = signal.lfilter(b, a, ir, axis=0)
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([signal.fftconvolve(out[:, c], ir[:, c])[:n] for c in range(2)], 1)
    out = out + 0.22 * wet
    return out / np.abs(out).max() * 0.5
