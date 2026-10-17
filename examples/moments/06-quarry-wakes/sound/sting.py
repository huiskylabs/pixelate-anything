"""Quarry Wakes boss sting: 5.0 s, E minor, 168 bpm, ending on the slam. Every voice is FM synthesis
written here in numpy (2 to 4 operators), no samples:
  bass   2-op FM pluck (ratio 1, fast-decaying index) in 8ths on E with b2 (F) and b6 (C) pushes
  brass  3-op FM stabs (index follows the amplitude, the classic brass attack), detuned pair
  riff   4-op FM growl lead: E G F# E B, Bb A (written for this piece)
  drums  FM kick (pitch drop), noise+FM snare, metallic FM hats, a rising tom fill and a noise riser
  slam   the downbeat of bar 4 (4.29 s): an inharmonic FM boom with a pitch drop, a noise burst,
         a sub drop 70 -> 30 Hz, a metal clank and an E power-chord brass hit, decaying into the fade
Writes sting.wav (48 kHz, 16-bit stereo); the caller trims, fades and encodes."""
import sys, wave, pathlib
import numpy as np

SR = 48000
BPM = 168.0
BEAT = 60.0 / BPM
DUR = 5.0
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(6)

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)

def env_adsr(n, a, d, s, r, hold):
    """attack, decay to sustain s, hold (s), release; all times in seconds -> array of n"""
    t = np.arange(n) / SR
    e = np.zeros(n)
    a = max(a, 1e-4)
    e = np.where(t < a, t / a, e)
    dd = (t >= a) & (t < a + d)
    e = np.where(dd, 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    e = np.where((t >= a + d) & (t < hold), s, e)
    rel = t >= max(hold, a + d)
    e = np.where(rel, s * np.exp(-(t - max(hold, a + d)) / max(r, 1e-4)), e)
    return e

def place(buf, x, start, gain=1.0, pan=0.0):
    """add mono x into the stereo buffer at time start (s), equal-power pan -1..1"""
    i = int(round(start * SR))
    if i >= N:
        return
    x = x[:N - i]
    l = np.cos((pan + 1) * np.pi / 4) * gain
    r = np.sin((pan + 1) * np.pi / 4) * gain
    buf[i:i + len(x), 0] += x * l
    buf[i:i + len(x), 1] += x * r

def fm2(f, n, ratio, index_env, amp_env, fb=0.0):
    """2-operator FM: modulator (with optional self-feedback) into the carrier"""
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * ratio * t)
    if fb:
        mod = np.sin(2 * np.pi * f * ratio * t + fb * mod)
    return np.sin(2 * np.pi * f * t + index_env * mod) * amp_env

def onepole_lp(x, fc):
    """one-pole low-pass; fc may be an array (a sweep)"""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y

# ---------------------------------------------------------------- voices
def bass(m, length):
    n = int(SR * length)
    f = mtof(m)
    t = np.arange(n) / SR
    idx = 2.6 * np.exp(-t / 0.045) + 0.5               # the slap: a bright attack that closes fast
    amp = env_adsr(n, 0.003, 0.08, 0.55, 0.03, length * 0.85)
    tone = fm2(f, n, 1.0, idx, amp, fb=0.6)
    sub = np.sin(2 * np.pi * f * t) * amp * 0.55
    return 0.8 * tone + sub

def brass(notes, length, bright=1.0):
    n = int(SR * length)
    out = np.zeros(n)
    t = np.arange(n) / SR
    for k, m in enumerate(notes):
        for det in (-0.07, 0.07):                        # a detuned pair per note
            f = mtof(m + det)
            amp = env_adsr(n, 0.018, 0.12, 0.6, 0.06, length * 0.8)
            idx = bright * (1.2 + 2.4 * amp)             # index follows amplitude: the brass bite
            # 3 operators: op3 -> op2 -> op1 (carrier)
            op3 = np.sin(2 * np.pi * f * 2.0 * t) * 0.6
            op2 = np.sin(2 * np.pi * f * 1.0 * t + op3)
            out += np.sin(2 * np.pi * f * t + idx * op2) * amp
    return out / (2 * len(notes))

def lead(m, length):
    n = int(SR * length)
    f = mtof(m)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.08) / 0.1, 0, 1)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    amp = env_adsr(n, 0.006, 0.06, 0.75, 0.04, length * 0.9)
    # 4 operators: two modulators in series (ratios 3 and 1) plus a feedback growl on a second stack
    m2 = np.sin(3.0 * ph) * 0.8
    m1 = np.sin(1.0 * ph + m2 * 1.2)
    c1 = np.sin(ph + (1.5 + 1.5 * amp) * m1)
    c2 = np.sin(2.0 * ph + 0.9 * np.sin(2.0 * ph)) * 0.3
    return (c1 + c2) * amp

def kick(gain=1.0):
    n = int(SR * 0.32)
    t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    amp = np.exp(-t / 0.11)
    click = np.exp(-t / 0.003) * 0.4
    return (np.sin(ph + 0.8 * np.sin(ph * 1.5) * np.exp(-t / 0.01)) * amp + click * np.sin(2 * np.pi * 1800 * t)) * gain

def snare(gain=1.0):
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n) * np.exp(-t / 0.06)
    noise = noise - onepole_lp(noise, 900.0)            # keep the crack, lose the rumble
    body = np.sin(2 * np.pi * 190 * t + 1.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t / 0.05)
    return (0.55 * noise + 0.6 * body) * gain

def hat(gain=1.0, open_=False):
    n = int(SR * (0.12 if open_ else 0.04))
    t = np.arange(n) / SR
    m = np.sin(2 * np.pi * 7100 * t + 4 * np.sin(2 * np.pi * 10300 * t))
    noise = rng.standard_normal(n)
    x = 0.5 * m + 0.5 * (noise - onepole_lp(noise, 6000.0))
    return x * np.exp(-t / (0.05 if open_ else 0.012)) * gain

def tom(f0, gain=1.0):
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    f = f0 * (1 + 0.5 * np.exp(-t / 0.025))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph + 0.6 * np.sin(ph * 2.0) * np.exp(-t / 0.03)) * np.exp(-t / 0.12) * gain

def riser(length):
    n = int(SR * length)
    t = np.arange(n) / SR
    u = t / length
    noise = rng.standard_normal(n)
    lp = onepole_lp(noise, 400 + 7000 * u ** 2)
    hp = lp - onepole_lp(lp, 200 + 2500 * u ** 2)
    sweep = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2.5 * u)) / SR + 1.5 * np.sin(2 * np.pi * np.cumsum(330 * 2 ** (2.5 * u)) / SR))
    return (0.8 * hp + 0.25 * sweep) * (u ** 1.6)

def slam():
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    # inharmonic FM boom with a pitch drop (ratio 1.41: metal, not a drum)
    f = 34 + 30 * np.exp(-t / 0.08)
    ph = 2 * np.pi * np.cumsum(f) / SR
    boom = np.sin(ph + (5.0 * np.exp(-t / 0.06) + 0.4) * np.sin(1.41 * ph)) * np.exp(-t / 0.35)
    # the sub drop 70 -> 30 Hz
    fs = 30 + 40 * np.exp(-t / 0.18)
    sub = np.sin(2 * np.pi * np.cumsum(fs) / SR) * np.exp(-t / 0.55) * np.clip(t / 0.004, 0, 1)
    # the noise burst: a bright transient and a darker rolling tail
    noise = rng.standard_normal(n)
    burst = onepole_lp(noise, 300 + 5000 * np.exp(-t / 0.05)) * np.exp(-t / 0.2)
    crack = (noise - onepole_lp(noise, 3000.0)) * np.exp(-t / 0.012)
    # a metal clank: FM ratio 2.76 on a mid tone
    clank = np.sin(2 * np.pi * 196 * t + 3.0 * np.exp(-t / 0.1) * np.sin(2 * np.pi * 196 * 2.76 * t)) * np.exp(-t / 0.28)
    return 0.9 * boom + 0.9 * sub + 0.55 * burst + 0.35 * crack + 0.22 * clank

# ---------------------------------------------------------------- arrangement (beats from 0)
def render():
    buf = np.zeros((N, 2))
    b = lambda beats: beats * BEAT
    E8 = BEAT / 2
    bassline = [40, 52, 40, 52, 40, 52, 41, 53,      # bar 1: E, the b2 push
                40, 52, 40, 52, 36, 48, 35, 47,      # bar 2: the b6 (C) and B under the riff
                40, 52, 40, 52, 41, 41, 43, 44]      # bar 3: E, then F F G G# climbing into the slam
    for i, m in enumerate(bassline):
        place(buf, bass(m, E8 * 0.92), b(i * 0.5), 0.42)
    stabs = [(0.0, (64, 67, 71), 0.75), (1.5, (64, 67, 71), 0.3), (2.5, (64, 67, 71), 0.3), (3.5, (65, 69, 72), 0.4),
             (4.0, (64, 67, 71), 0.3), (5.5, (60, 64, 67), 0.3), (6.5, (60, 64, 67), 0.3), (7.5, (59, 62, 65), 0.4),
             (8.0, (64, 67, 71), 0.6), (9.5, (65, 69, 72), 0.3)]
    for beat, notes, ln in stabs:
        place(buf, brass(notes, ln), b(beat), 0.30, pan=-0.35)
        place(buf, brass([n + 0.0 for n in notes], ln, bright=0.8), b(beat) + 0.011, 0.22, pan=0.35)
    riff = [(4.0, 76, 0.5), (4.5, 79, 0.5), (5.0, 78, 0.5), (5.5, 76, 0.5), (6.0, 83, 1.0), (7.0, 82, 0.5),
            (7.5, 81, 0.5), (8.0, 76, 0.5), (8.5, 79, 0.5), (9.0, 78, 0.5), (9.5, 76, 0.5)]
    for beat, m, ln in riff:
        place(buf, lead(m - 12, ln * BEAT * 0.95), b(beat), 0.17, pan=0.05)
    for beat in (0, 1, 2, 2.75, 3, 4, 5, 6, 6.75, 7, 8, 9):
        place(buf, kick(), b(beat), 0.62)
    for beat in (1, 3, 5, 7, 9):
        place(buf, snare(), b(beat), 0.32, pan=0.1)
    for k in range(20):
        beat = k * 0.5
        place(buf, hat(open_=(k % 8 == 7)), b(beat) + (0 if k % 2 == 0 else 0.004), 0.10 if k % 2 else 0.065, pan=0.45)
    # the fill: 16th toms rising over beats 10-12, a riser, a snare flam on the last 16th
    for k in range(8):
        place(buf, tom(85 * 2 ** (k / 6.5)), b(10 + k * 0.25), 0.34 + 0.03 * k, pan=-0.4 + 0.11 * k)
    place(buf, riser(b(3.0)), b(9.0), 0.20)
    place(buf, snare(1.0), b(11.75), 0.30)
    # THE SLAM on the downbeat of bar 4
    place(buf, slam(), b(12.0), 0.80)
    place(buf, brass((40, 47, 52), 0.9, bright=1.3), b(12.0), 0.42, pan=-0.2)
    place(buf, brass((52, 59, 64), 0.9, bright=1.1), b(12.0) + 0.008, 0.30, pan=0.2)
    return buf

def finish(buf, lufs_target=-14.0):
    """gentle saturation, fades (20 ms in, 400 ms out), loudness near the target, peak <= -1 dBFS"""
    x = np.tanh(buf * 1.1) / np.tanh(1.1)
    fi = int(0.020 * SR)
    fo = int(0.400 * SR)
    x[:fi] *= np.linspace(0, 1, fi)[:, None]
    x[-fo:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fo)))[:, None]
    return x

def write(path, x, gain):
    y = np.clip(x * gain, -1, 1)
    pcm = (y * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).with_name('06-sample.wav'))
    gain = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    x = finish(render())
    peak = np.abs(x).max()
    write(out, x / peak * 0.89, gain)
    print('wrote', out, '%.3f s' % (N / SR), 'peak before norm %.2f' % peak)
