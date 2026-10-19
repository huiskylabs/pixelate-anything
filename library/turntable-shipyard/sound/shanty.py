"""07 Turntable shipyard: "Caulkers' Dawn", a shipwrights' work song, 5.0 s sample.

6/8, dotted quarter = 72 bpm (a bar is 1.667 s, so the sample is exactly three bars), D mixolydian
(the C natural in bar 2 is the mode's flat seventh). Our own tune, rendered with a numpy synth:
- concertina lead: two slightly detuned pulse/saw reeds plus a quiet octave reed, through a
  band-pass, a bellows swell over each bar and a push-pull dip at each bellows change;
- left-hand chords: short low reed stabs on each dotted-quarter beat;
- plucked bass on the downbeats (Karplus-Strong);
- caulking-mallet knocks on the beats with a lighter pick-up knock, a hand-saw rasp in bar 2;
- a small room (a synthetic decaying impulse response), 20 ms fade-in, 400 ms fade-out.
Writes sound/07-sample.wav (48 kHz, 16-bit, stereo).
"""
import pathlib
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 48000
DUR = 5.0
N = int(SR * DUR)
BPM = 72.0                       # dotted quarters per minute
E = 60.0 / BPM / 3               # one eighth note: 0.2778 s
HERE = pathlib.Path(__file__).resolve().parent
rng = np.random.default_rng(7)

def hz(n):
    """MIDI note number -> Hz"""
    return 440.0 * 2 ** ((n - 69) / 12.0)

D4, E4, Fs4, G4, A4, B4, C5, D5, E5, Fs5 = 62, 64, 66, 67, 69, 71, 72, 74, 76, 78

# the tune, in eighths: (start, length, note). Bar 1 climbs the D chord with a lilt, bar 2 turns
# down through the flat seventh, bar 3 comes home and holds D under the fade.
TUNE = [(0, 2, A4), (2, 1, D5), (3, 2, Fs5), (5, 1, E5),
        (6, 1, D5), (7, 1, C5), (8, 1, A4), (9, 2, G4), (11, 1, A4),
        (12, 2, B4), (14, 1, A4), (15, 3, D5)]
CHORDS = [(0, [50, 57, 62]), (3, [50, 57, 62]), (6, [48, 55, 60]), (9, [43, 50, 59]),
          (12, [50, 57, 62]), (15, [50, 57, 62])]          # D, D, C, G, D, D (left hand)
BASS = [(0, 38), (3, 45), (6, 36), (9, 43), (12, 38), (15, 33)]   # D2 A2 C2 G2 D2 A1

def env(n, a=0.012, r=0.05, sustain=1.0):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / a) * sustain
    rel = int(r * SR)
    if rel < n:
        e[-rel:] *= np.linspace(1, 0, rel) ** 1.5
    return e

def reed(f, n, detune=0.0045):
    """a concertina reed pair: a narrow pulse and a saw, beating slowly, plus a soft octave"""
    t = np.arange(n) / SR
    ph1 = (f * (1 + detune) * t) % 1.0
    ph2 = (f * (1 - detune) * t) % 1.0
    ph3 = (2 * f * t + 0.3) % 1.0
    pulse = np.where(ph1 < 0.32, 1.0, -0.47)
    saw = 2 * ph2 - 1
    return 0.55 * pulse + 0.45 * saw + 0.18 * (2 * ph3 - 1)

def bandpass(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return sosfilt(sos, x)

def lowpass(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='low', fs=SR, output='sos'), x)

def highpass(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='high', fs=SR, output='sos'), x)

def place(buf, sig, t0):
    i = int(round(t0 * SR))
    if i >= len(buf):
        return
    m = min(len(sig), len(buf) - i)
    buf[i:i + m] += sig[:m]

def lead():
    out = np.zeros(N)
    for st, ln, note in TUNE:
        n = int((ln * E + 0.05) * SR)
        s = reed(hz(note), n) * env(n, a=0.018, r=0.07)
        place(out, s, st * E)
    out = bandpass(out, 420, 3600)
    # bellows: a swell over each bar, a small dip where the bellows turns (push to pull)
    t = np.arange(N) / SR
    bar = (t % (6 * E)) / (6 * E)
    swell = 0.72 + 0.28 * np.sin(np.pi * np.clip(bar * 1.05, 0, 1))
    dip = 1 - 0.12 * np.exp(-((bar - 0.5) / 0.03) ** 2)
    return out * swell * dip

def chords():
    out = np.zeros(N)
    for st, notes in CHORDS:
        n = int(1.4 * E * SR)
        s = sum(reed(hz(m), n, 0.003) for m in notes) / len(notes)
        place(out, s * env(n, a=0.01, r=0.12), st * E + 0.004)
    return lowpass(bandpass(out, 220, 1300), 1100) * 0.40

def pluck(f, dur=1.4, damp=0.996):
    """Karplus-Strong string: a noise burst in a delay line, softened each pass"""
    p = int(SR / f)
    n = int(dur * SR)
    buf = rng.uniform(-1, 1, p)
    buf = np.convolve(buf, np.ones(3) / 3, 'same')
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        j = (i + 1) % p
        buf[i % p] = damp * 0.5 * (buf[i % p] + buf[j])
    return out * env(n, a=0.002, r=0.25)

def bass():
    out = np.zeros(N)
    for st, note in BASS:
        n = int((3 * E + 0.25) * SR)
        t = np.arange(n) / SR
        sub = np.sin(2 * np.pi * hz(note) * t) * np.exp(-t / 0.45) * env(n, a=0.004, r=0.2)
        place(out, pluck(hz(note), dur=3 * E + 0.25) + 0.9 * sub, st * E)
    return lowpass(out, 700) * 1.0

def knock(tone=820, dec=0.045, gain=1.0):
    """a caulking mallet on oak: a short resonant noise tap plus a dull pitched click"""
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    burst = rng.uniform(-1, 1, n) * np.exp(-t / 0.006)
    body = bandpass(burst, tone * 0.7, tone * 1.5) * 3.0
    click = np.sin(2 * np.pi * tone * 1.9 * t) * np.exp(-t / 0.012) * 0.5
    thud = np.sin(2 * np.pi * 170 * t) * np.exp(-t / dec) * 0.7
    s = (body + click + thud) * np.exp(-t / dec)
    s[:48] *= np.linspace(0, 1, 48)
    return s * gain

def mallets():
    out = np.zeros(N)
    for b in range(6):                          # every dotted-quarter beat, the downbeats heavier
        place(out, knock(820 + 30 * (b % 2), 0.05, 1.0 if b % 2 == 0 else 0.8), b * 3 * E)
        if b in (1, 3, 4):                      # the second caulker's pick-up on the last eighth
            place(out, knock(980, 0.03, 0.42), b * 3 * E + 2 * E)
    return out

def rasp(t0, strokes=2):
    """a hand saw: band-limited noise, each push louder than its pull, teeth as a fast buzz"""
    n = int(strokes * 2 * E * SR)
    t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n)
    teeth = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 95 * t))
    cyc = (t % (2 * E)) / (2 * E)
    stroke = np.where(cyc < 0.55, np.sin(np.pi * cyc / 0.55), 0.5 * np.sin(np.pi * (cyc - 0.55) / 0.45))
    s = bandpass(noise * teeth, 2200, 6200) * stroke ** 1.5
    out = np.zeros(N)
    place(out, s * 0.22, t0)
    return out

def room(x, rt=0.32, seed=0):
    r = np.random.default_rng(seed)
    n = int(rt * 1.5 * SR)
    t = np.arange(n) / SR
    ir = r.normal(0, 1, n) * np.exp(-6.9 * t / rt)
    ir = lowpass(ir, 4200)
    ir[:int(0.012 * SR)] = 0                   # a short pre-delay
    ir /= np.sqrt((ir ** 2).sum())
    return fftconvolve(x, ir)[:len(x)]

def mix():
    ld, ch, bs, ml, rs = lead(), chords(), bass(), mallets(), rasp(7 * E, 2)
    L = 0.60 * ld + 0.26 * ch + 1.05 * bs + 0.42 * ml + 0.34 * rs
    R = 0.46 * ld + 0.30 * ch + 1.05 * bs + 0.55 * ml + 0.18 * rs
    L = L + 0.16 * room(L, seed=1); R = R + 0.16 * room(R, seed=2)
    x = np.stack([L, R], 1)
    x = highpass(x.T, 30).T
    x -= x.mean(0)
    # fades: 20 ms in (the sample starts on the downbeat), 400 ms out
    fi, fo = int(0.020 * SR), int(0.400 * SR)
    x[:fi] *= np.linspace(0, 1, fi)[:, None]
    x[-fo:] *= (np.linspace(1, 0, fo) ** 2)[:, None]
    return x

def master(x, target_rms=0.155, ceil=0.84):
    rms = np.sqrt((x ** 2).mean())
    x = x * (target_rms / max(rms, 1e-9))
    x = np.tanh(x / ceil) * ceil                # a gentle limiter
    return x

if __name__ == '__main__':
    import sys
    g = float(sys.argv[1]) if len(sys.argv) > 1 else 0.155
    x = master(mix(), g)
    assert len(x) == N
    wavfile.write(HERE / '07-sample.wav', SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    print('wrote', HERE / '07-sample.wav', '%.3f s' % (len(x) / SR), 'peak %.3f' % np.abs(x).max())
