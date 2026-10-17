"""The 5 s trunk-town sample: the best 5 s of the engine render (sound/full.wav, 76 bpm, D major),
cut on a downbeat, with one clock-bell strike of our own synthesis mixed on top about 1 s in, as the
gondola passes the clock.

The bell: a low warm struck bell on D3 (146.83 Hz, the root of the Dmaj9 under it): a hum an octave
below, the prime with a slow 0.7 Hz beat (two detuned copies), a slightly stretched octave and two
inharmonic partials (2.76 and 4.07) that die away fast, each its own exponential decay (T60 7 s down
to 1.1 s), a 2 ms attack and a short lowpassed strike thump; panned a little left, where the clock
hangs on screen. Writes sound/02-sample.wav (48 kHz, 16-bit, stereo, exactly 5.0 s); the mp3 is made
with ffmpeg from it.
"""
import sys, pathlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, '/home/user/pixelate-anything/tools')
import musiccheck as MC

HERE = pathlib.Path(__file__).resolve().parent
SR = 48000
BAR = 4 * 60 / 76                 # one bar at 76 bpm
GRID = 0.065                      # the render's first downbeat (kick onset), measured
START_BAR = 16                    # a bar on Dmaj9 where the guitar phrase starts on the downbeat
LEN = 5.0
BELL_AT = 1.0


def bell(sr=SR, dur=4.2, f0=146.83):
    t = np.arange(int(dur * sr)) / sr
    def partial(ratio, amp, t60, detune=0.0):
        k = np.log(1000.0) / t60                       # -60 dB at t60
        return amp * np.exp(-k * t) * np.sin(2 * np.pi * (f0 * ratio + detune) * t)
    x = (partial(0.5, 0.30, 7.0)                       # hum
         + partial(1.0, 0.55, 5.5, -0.35) + partial(1.0, 0.45, 5.5, +0.35)   # prime, beating slowly
         + partial(2.006, 0.36, 3.4)                   # a slightly stretched octave
         + partial(2.76, 0.16, 1.9)                    # inharmonic
         + partial(4.07, 0.07, 1.1))                   # inharmonic, bright, short
    att = np.minimum(1.0, t / 0.002)
    x *= att
    # the strike: a 10 ms lowpassed noise thump
    rng = np.random.default_rng(7)
    n = int(0.010 * sr)
    thump = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.0025 * sr))
    thump = sosfilt(butter(2, 1800, 'lowpass', fs=sr, output='sos'), thump) * 0.35
    x[:n] += thump
    # gentle warmth: roll the top off a little
    x = sosfilt(butter(1, 3500, 'lowpass', fs=sr, output='sos'), x)
    return x / np.abs(x).max()


def main():
    sr, full = wavfile.read(HERE / 'full.wav')
    assert sr == SR, sr
    full = full.astype(np.float64)
    a = int(round((GRID + START_BAR * BAR) * SR))
    n = int(round(LEN * SR))
    clip = full[a:a + n].copy()
    assert len(clip) == n
    # the bell, panned a little left (the clock is left of the gondola), about -9 dB under full scale
    b = bell() * 0.36
    i0 = int(BELL_AT * SR)
    m = min(len(b), n - i0)
    pan = -0.3
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    clip[i0:i0 + m, 0] += b[:m] * gl * 1.41
    clip[i0:i0 + m, 1] += b[:m] * gr * 1.41
    # a gentle high shelf (about -3 dB above 5 kHz): the hats and crackle sat a touch bright for a lofi tilt
    hp = sosfilt(butter(1, 5000, 'highpass', fs=SR, output='sos'), clip, axis=0)
    clip = clip - 0.3 * hp
    # level: about -14 LUFS integrated, true peak kept under -1 dBFS
    lufs = MC.integrated(MC.block_loudness(clip, SR))
    clip *= 10 ** ((-14.0 - lufs) / 20)
    tp = MC.true_peak(clip)
    if tp > -1.2:
        clip *= 10 ** ((-1.2 - tp) / 20)
    # fades: 20 ms in (from the downbeat), about 400 ms out
    fi = int(0.020 * SR); fo = int(0.400 * SR)
    clip[:fi] *= np.linspace(0, 1, fi)[:, None]
    clip[-fo:] *= (np.cos(np.linspace(0, np.pi, fo)) * 0.5 + 0.5)[:, None]
    out = np.clip(np.round(clip * 32767), -32768, 32767).astype(np.int16)
    wavfile.write(HERE / '02-sample.wav', SR, out)
    print('start %.3f s (bar %d), %d samples, %.3f s, LUFS %.1f, true peak %.1f dBFS' % (
        a / SR, START_BAR, len(out), len(out) / SR, MC.integrated(MC.block_loudness(out / 32768.0, SR)),
        MC.true_peak(out / 32768.0)))


if __name__ == '__main__':
    main()
