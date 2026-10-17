"""Monsoon Street: cut the 5.0 s downpour sample from the engine render and mix the tram bell.

    python3 sound/make_sample.py      (from examples/moments/01-monsoon-street)

The bell is my own synth: a struck two-tone "ding-ding" (C#6 then F#5, both in B minor) with
inharmonic partials that decay faster the higher they sit, a soft strike click, a slight detuned
twin for shimmer and a short synthetic room so it sits in the engine's reverb. The clip starts on
a downbeat (a bar start snapped to the kick onset), fades in over 20 ms and out over 400 ms."""
import pathlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, butter, sosfilt

HERE = pathlib.Path(__file__).resolve().parent
SR = 48000
BPM = 66 / 1.001                        # the engine scaled the tempo by 1.001 to fit the cycle
BAR = 4 * 60.0 / BPM
CLIP = 5.0


def load():
    sr, a = wavfile.read(HERE / 'full.wav')
    assert sr == SR
    a = a.astype(np.float64)
    if a.dtype.kind == 'i':
        a /= 32768.0
    return a


def band(x, lo, hi):
    sos = butter(4, [lo, hi], btype='band', fs=SR, output='sos')
    return sosfilt(sos, x)


def pick_start(a):
    """the bar start (2nd..6th bar) whose 5 s holds the most piano (300-2500 Hz) without the
    turnaround, snapped to the kick onset within 40 ms"""
    mono = a.mean(1)
    mid = band(mono, 300, 2500)
    low = band(mono, 40, 140)
    best, bk = None, -1
    for k in range(1, 6):
        s = int(k * BAR * SR)
        e = s + int(CLIP * SR)
        if e > len(mono) - SR:
            break
        score = np.sqrt(np.mean(mid[s:e] ** 2))
        if best is None or score > best:
            best, bk = score, k
    s = int(bk * BAR * SR)
    w = int(0.04 * SR)
    env = np.abs(low[s - w:s + w])
    on = np.argmax(np.diff(np.convolve(env, np.ones(48) / 48, 'same')))
    return bk, s - w + on


def bell(t0, f0, amp, n):
    """one struck strike of the bell at t0 seconds, fundamental f0"""
    ratios = (1.0, 2.41, 3.93, 5.36, 7.05)
    gains = (1.0, 0.36, 0.15, 0.06, 0.02)
    taus = (0.62, 0.30, 0.17, 0.10, 0.06)
    t = np.arange(n) / SR - t0
    on = t >= 0
    tt = np.where(on, t, 0)
    att = np.clip(tt / 0.002, 0, 1)
    y = np.zeros(n)
    for r, g, tau in zip(ratios, gains, taus):
        y += g * np.sin(2 * np.pi * f0 * r * tt) * np.exp(-tt / tau)
    y += 0.35 * np.sin(2 * np.pi * (f0 + 1.7) * tt) * np.exp(-tt / 0.5)       # detuned twin: shimmer
    rng = np.random.default_rng(int(f0))
    click = band(rng.standard_normal(n), 2000, 5000) * np.exp(-tt / 0.004) * 0.08
    return amp * on * att * (y + click)


def room(x):
    rng = np.random.default_rng(7)
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t / 0.22)
    ir = band(ir, 200, 6000)
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    return fftconvolve(x, ir)[:len(x)]


def main():
    a = load()
    bk, s = pick_start(a)
    n = int(CLIP * SR)
    clip = a[s:s + n].copy()
    # the tram bell: ding (C#6) - ding (F#5), soft, a little right of centre, in a small room
    dry = bell(1.86, 1108.73, 0.20, n) + bell(2.16, 739.99, 0.17, n)
    wet = room(dry)
    b = 0.78 * dry + 0.35 * wet
    pan = 0.15
    clip[:, 0] += b * (1 - pan)
    clip[:, 1] += b * (1 + pan)
    # a gentle high shelf (about -2.5 dB above 5 kHz): the rain hiss and the bell's top stay soft
    sos = butter(1, 5000, btype='high', fs=SR, output='sos')
    for ch in range(2):
        clip[:, ch] -= 0.25 * sosfilt(sos, clip[:, ch])
    # fades: 20 ms in, 400 ms out (raised cosine)
    fi, fo = int(0.02 * SR), int(0.4 * SR)
    env = np.ones(n)
    env[:fi] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fi))
    env[-fo:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fo))
    clip *= env[:, None]
    peak = np.max(np.abs(clip))
    if peak > 0.89:                       # keep 1 dB of headroom, never clip
        clip *= 0.89 / peak
    out = np.clip(np.round(clip * 32767), -32768, 32767).astype(np.int16)
    wavfile.write(HERE / '01-sample.wav', SR, out)
    print('bar %d, start %.3f s, %d samples, peak %.3f' % (bk, s / SR, len(out), np.max(np.abs(clip))))


if __name__ == '__main__':
    main()
