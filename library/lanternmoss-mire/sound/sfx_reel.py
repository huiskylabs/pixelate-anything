#!/usr/bin/env python3
"""Lanternmoss Mire SFX reel: 5.0 s of handheld-style chip sound effects, own numpy synth.

Channels, emulated the way a handheld sound chip works (all at 192 kHz, then low-passed and
decimated to 48 kHz so the square edges stay crisp without aliasing grit):
  pulse 1, pulse 2   square waves with 12.5 / 25 / 50 % duty, frequencies quantised to the
                     chip's 11-bit period (131072 / (2048 - x)), stepped pitch sweeps, 4-bit
                     volume envelopes that step every n/64 s
  wave               a 32-step, 4-bit wave table played at 65536 / (2048 - x) Hz, output level
                     100 / 50 / 25 %
  noise              an LFSR (15-bit, or 7-bit for the metallic tone) clocked at the chip's
                     524288 / r / 2^(s+1) Hz, with its own 4-bit envelope
Events: coin pickup, pole-vault whoosh and landing thud, peat toad inflating and croaking, a
lantern-moth flutter, a splash into bog water, and a 4-note item-get jingle (original).
Writes sound/09-sample.wav (48 kHz, 16-bit, stereo, exactly 5.0 s; 20 ms fade-in, 200 ms
fade-out, peak about -1 dBFS). Make the mp3 with ffmpeg (see the brief).
"""
import pathlib, wave
import numpy as np

SR = 48000
OS = 4
FS = SR * OS
DUR = 5.0
N = int(DUR * FS)
HERE = pathlib.Path(__file__).resolve().parent


def note(name):
    """'E5' -> Hz (A4 = 440)"""
    names = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4, 'F#': -3, 'G': -2, 'G#': -1,
             'A': 0, 'A#': 1, 'B': 2}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o - 4)) / 12)


def pulse_hz(f):
    """quantise to the chip's 11-bit pulse period"""
    x = int(round(2048 - 131072 / f))
    return 131072 / (2048 - max(0, min(2047, x)))


def wave_hz(f):
    x = int(round(2048 - 65536 / f))
    return 65536 / (2048 - max(0, min(2047, x)))


def noise_hz(r, s):
    return 524288 / (0.5 if r == 0 else r) / 2 ** (s + 1)


def env(n, v0, direction, period):
    """4-bit volume envelope: starts at v0, steps by 1 every period/64 s (period 0 = hold)"""
    t = np.arange(n) / FS
    if period == 0:
        v = np.full(n, float(v0))
    else:
        v = v0 + direction * np.floor(t / (period / 64.0))
    return np.clip(v, 0, 15) / 15.0


def stepped(values, step_s, n):
    """a parameter that changes in steps (pitch sweeps, gates): values[k] held for step_s"""
    idx = np.minimum((np.arange(n) / FS / step_s).astype(int), len(values) - 1)
    return np.asarray(values, float)[idx]


def pulse(freq, duty, vol):
    """freq: Hz per sample (array); duty 0.125 / 0.25 / 0.5; vol: 0..1 per sample"""
    ph = np.cumsum(freq / FS) % 1.0
    return np.where(ph < duty, 1.0, -1.0) * vol


TABLES = {
    # 32 steps of 4 bits each
    'round': [8, 10, 12, 13, 14, 15, 15, 15, 15, 14, 13, 12, 10, 8, 6, 4,
              3, 2, 1, 0, 0, 0, 0, 0, 1, 2, 3, 4, 6, 7, 7, 8],
    'bubble': [7, 9, 11, 13, 15, 15, 14, 12, 10, 9, 8, 8, 9, 10, 11, 11,
               10, 8, 6, 4, 2, 1, 0, 0, 1, 2, 3, 4, 4, 5, 6, 7],
    'bass': [15, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
             0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
}


def wavech(freq, table, level):
    """freq: Hz of the whole 32-step table; level: 1, 0.5 or 0.25 (or an array)"""
    tab = (np.array(TABLES[table], float) - 7.5) / 7.5
    ph = np.cumsum(freq / FS) % 1.0
    return tab[(ph * 32).astype(int) % 32] * level


def noise(clock, width7, vol, seed=0x7fff):
    """LFSR noise; clock: Hz per sample (array). The register shifts once per clock tick."""
    n = len(clock)
    ticks = np.floor(np.cumsum(clock / FS)).astype(np.int64)
    total = int(ticks[-1]) + 2
    lfsr = seed & 0x7fff
    bits = np.empty(total, np.int8)
    for i in range(total):
        x = (lfsr ^ (lfsr >> 1)) & 1
        lfsr = (lfsr >> 1) | (x << 14)
        if width7:
            lfsr = (lfsr & ~(1 << 6)) | (x << 6)
        bits[i] = 1 if (lfsr & 1) == 0 else -1
    return bits[ticks].astype(float) * vol


class Mix:
    def __init__(self):
        self.L = np.zeros(N)
        self.R = np.zeros(N)

    def add(self, t0, sig, pan=0.0, gain=1.0):
        """pan -1 (left) .. 1 (right): the far side keeps 60 %, so mono stays whole"""
        i = int(t0 * FS)
        sig = sig[:max(0, N - i)] * gain
        self.L[i:i + len(sig)] += sig * (1.0 if pan <= 0 else 1.0 - 0.4 * pan)
        self.R[i:i + len(sig)] += sig * (1.0 if pan >= 0 else 1.0 + 0.4 * pan)


def samples(sec):
    return int(sec * FS)


def build():
    m = Mix()

    # 1. coin pickup: a quick rising pair, then a ringing top note (pulse 1, 25 % duty)
    n = samples(0.42)
    f = stepped([pulse_hz(note('D6')), pulse_hz(note('G6')), pulse_hz(note('D7'))], 0.04, n)
    m.add(0.06, pulse(f, 0.25, env(n, 12, -1, 2)), pan=-0.2, gain=0.55)
    m.add(0.10, pulse(f * 0.5, 0.125, env(n, 5, -1, 2)), pan=0.3, gain=0.35)     # pulse 2 echo

    # 2. pole-vault: a whoosh (15-bit noise, clock rising then falling, swelling envelope)
    #    with a rising sweep on pulse 2, then the landing thud (7-bit noise + falling wave)
    n = samples(0.40)
    clock = stepped([noise_hz(r, s) for r, s in ((4, 6), (4, 5), (2, 5), (2, 4), (1, 4), (1, 3), (1, 3),
                                                   (2, 4), (2, 5), (4, 5), (4, 6), (4, 7), (4, 7))], 0.031, n)
    swell = np.minimum(env(n, 2, 1, 1), env(n, 15, -1, 2) * 1.0 + 0.0)
    m.add(0.62, noise(clock, False, swell, 0x5a5a), pan=-0.5, gain=0.42)
    n = samples(0.26)
    sweep = [pulse_hz(220 * 2 ** (k / 6)) for k in range(13)]                     # stepped like the chip's sweep unit
    m.add(0.66, pulse(stepped(sweep, 0.02, n), 0.125, env(n, 9, -1, 2)), pan=0.4, gain=0.3)
    n = samples(0.16)
    m.add(1.08, noise(np.full(n, noise_hz(7, 6)), True, env(n, 15, -1, 1), 0x1234), gain=0.5)
    n = samples(0.22)
    fall = stepped([wave_hz(f) for f in (130, 110, 92, 78, 66, 58, 52, 48)], 0.026, n)
    m.add(1.08, wavech(fall, 'round', 1.0) * env(n, 15, -1, 1), gain=0.75)

    # 3. peat toad: inflating (wave channel, rising pitch with a stepped wobble, level 25-50-100 %)
    n = samples(0.52)
    t = np.arange(n) / FS
    rise = stepped([wave_hz(85 * 2 ** (k / 10)) for k in range(14)], 0.037, n)
    wob = 1 + 0.035 * np.sign(np.sin(2 * np.pi * 7 * t))
    lvl = stepped([0.25, 0.25, 0.5, 0.5, 1.0, 1.0, 1.0], 0.075, n)
    m.add(1.42, wavech(rise * wob, 'bubble', lvl), pan=0.15, gain=0.7)
    #    and croaking twice: a 12.5 % pulse chopped at 30 Hz with a dipping pitch, plus rasp
    for c, t0 in enumerate((2.0, 2.24)):
        n = samples(0.15)
        t = np.arange(n) / FS
        f = stepped([pulse_hz(f) for f in (104, 98, 92, 87, 82)], 0.03, n)
        gate = (np.floor(t * 30) % 2 == 0) * 1.0 * 0.85 + 0.15
        m.add(t0, pulse(f, 0.125, env(n, 14 - 2 * c, -1, 1) * gate), pan=0.15, gain=0.62)
        m.add(t0, noise(np.full(n, noise_hz(5, 5)), True, env(n, 6, -1, 1) * gate, 0x2d2d), pan=0.15, gain=0.18)

    # 4. lantern moth: a flutter of soft 7-bit noise gated at 24 Hz, drifting right to left
    n = samples(0.46)
    t = np.arange(n) / FS
    beat = stepped([1.0, 0.25] * 40, 1 / 48, n)
    shape = np.clip(np.minimum(t / 0.08, (0.46 - t) / 0.15), 0, 1)
    fl = noise(np.full(n, noise_hz(1, 2)), True, beat * shape * (9 / 15.0), 0x4e4e)
    half = n // 2
    m.add(2.62, fl[:half], pan=0.5, gain=0.34)
    m.add(2.62 + half / FS, fl[half:], pan=-0.4, gain=0.34)
    n2 = samples(0.07)
    for t0 in (2.70, 2.86):
        m.add(t0, pulse(np.full(n2, pulse_hz(note('E7'))), 0.125, env(n2, 5, -1, 1)), pan=0.2, gain=0.16)

    # 5. splash into bog water: 15-bit noise, bright to dull, then three bubbles on the wave channel
    n = samples(0.34)
    clock = stepped([noise_hz(r, s) for r, s in ((1, 1), (1, 2), (2, 2), (2, 3), (4, 3), (4, 4), (5, 4),
                                                   (5, 5), (6, 5), (7, 5), (7, 6))], 0.031, n)
    m.add(3.24, noise(clock, False, env(n, 15, -1, 2), 0x6b6b), pan=-0.15, gain=0.5)
    for k, t0 in enumerate((3.50, 3.60, 3.67)):
        n = samples(0.05)
        up = stepped([wave_hz(f * (1 + 0.15 * k)) for f in (280, 340, 410, 500, 600)], 0.01, n)
        m.add(t0, wavech(up, 'round', 0.5) * env(n, 12, -1, 1), pan=0.3 - 0.3 * k, gain=0.6)

    # 6. item get: four notes, original; pulse 1 lead, pulse 2 harmony, wave bass
    lead = ['B4', 'E5', 'G#5', 'E6']
    harm = ['G#4', 'B4', 'E5', 'B5']
    t0 = 3.92
    for i, (a, b) in enumerate(zip(lead, harm)):
        d = 0.105 if i < 3 else 0.62
        n = samples(d)
        t = np.arange(n) / FS
        vib = 1 + (0.012 * np.sign(np.sin(2 * np.pi * 6 * t)) * (t > 0.18)) if i == 3 else 1.0
        m.add(t0, pulse(np.full(n, pulse_hz(note(a))) * vib, 0.25, env(n, 12, -1, 4 if i == 3 else 0)), pan=-0.25, gain=0.42)
        m.add(t0, pulse(np.full(n, pulse_hz(note(b))), 0.5, env(n, 7, -1, 4 if i == 3 else 0)), pan=0.25, gain=0.3)
        t0 += d
    n = samples(0.95)
    bass = stepped([wave_hz(note('E3')), wave_hz(note('B2')), wave_hz(note('E3'))], [0.21, 0.105][0], n)
    m.add(3.92, wavech(bass, 'bass', 1.0) * env(n, 15, -1, 7), gain=0.5)
    return m


def finish(m):
    def decimate(x):
        # windowed-sinc low-pass at 18 kHz, then keep every OS-th sample
        taps = 255
        k = np.arange(taps) - (taps - 1) / 2
        fc = 14000 / FS
        h = 2 * fc * np.sinc(2 * fc * k) * np.blackman(taps)
        h /= h.sum()
        return np.convolve(x, h, mode='same')[::OS]

    def highpass(x, fc=18.0):
        a = np.exp(-2 * np.pi * fc / SR)
        y = np.zeros_like(x)
        prev_x = prev_y = 0.0
        for i, v in enumerate(x):
            prev_y = a * (prev_y + v - prev_x)
            prev_x = v
            y[i] = prev_y
        return y

    def lowpass(x, fc=5200.0):
        # one-pole low-pass: the handheld's output stage, takes the fizz off the square edges
        a = np.exp(-2 * np.pi * fc / SR)
        y = np.zeros_like(x)
        prev = 0.0
        for i, v in enumerate(x):
            prev = (1 - a) * v + a * prev
            y[i] = prev
        return y

    st = np.stack([highpass(lowpass(decimate(m.L))), highpass(lowpass(decimate(m.R)))], axis=1)
    n = int(DUR * SR)
    st = st[:n]
    fade_in = int(0.020 * SR)
    fade_out = int(0.200 * SR)
    st[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    st[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    # peak about -1 dBFS, measured on a 4x oversampled copy (true peak)
    spec = np.fft.rfft(st, axis=0)
    up = np.fft.irfft(spec, n=n * 4, axis=0) * 4
    tp = max(np.abs(up).max(), np.abs(st).max())
    st *= 10 ** (-1.0 / 20) / tp
    return st


def main():
    st = finish(build())
    pcm = (np.clip(st, -1, 1) * 32767).round().astype('<i2')
    out = HERE / '09-sample.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('wrote', out, '%.3f s' % (len(pcm) / SR), 'peak %.2f dBFS' % (20 * np.log10(np.abs(st).max())))


if __name__ == '__main__':
    main()
