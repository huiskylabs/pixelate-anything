"""The 5 s "door opens" sample: cut from the engine render, the bronze bell mixed on top.

    python3 sound/make_sample.py [gain_db]

The clip starts 15.0 s into sound/full.wav, so the bell at 1.0 s lands on the pad's return from G13 to
Dm11: the door opens on the tonic, and the bell is a D. The bed is trimmed below 180 Hz and given some
2-5 kHz presence so the excerpt is not muddy. Exactly 5.0 s, 20 ms fade-in, 400 ms fade-out,
48 kHz 16-bit stereo -> sound/04-sample.wav (encode the mp3 with ffmpeg afterwards).
"""
import sys
import pathlib
import numpy as np
from scipy.io import wavfile
from scipy import signal

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bell import bell

SR = 48000
START, DUR, BELL_AT = 15.0, 5.0, 1.0
D3 = 146.83


def main(gain_db=0.0):
    sr, full = wavfile.read(HERE / 'full.wav')
    assert sr == SR, sr
    full = full.astype(np.float64)
    n = int(DUR * SR)
    pad = int(0.5 * SR)                              # filter with context, then cut (no edge ringing)
    seg = full[int(START * SR) - pad:int(START * SR) + n + pad].copy()
    b_, a_ = signal.butter(2, 40 / (SR / 2), 'highpass')
    seg = signal.filtfilt(b_, a_, seg, axis=0)
    b_, a_ = signal.butter(2, 180 / (SR / 2))
    seg = seg - 0.50 * signal.filtfilt(b_, a_, seg, axis=0)          # low shelf, about -6 dB
    b_, a_ = signal.butter(2, [2000 / (SR / 2), 5000 / (SR / 2)], 'bandpass')
    seg = seg + 2.2 * signal.filtfilt(b_, a_, seg, axis=0)           # presence, about +10 dB
    clip = seg[pad:pad + n]
    b = bell(SR, D3, DUR - BELL_AT)
    k = int(BELL_AT * SR)
    clip[k:k + len(b)] += 0.62 * b
    env = np.ones(n)
    fi, fo = int(0.020 * SR), int(0.400 * SR)
    env[:fi] = np.linspace(0, 1, fi) ** 2
    env[-fo:] = np.cos(np.linspace(0, np.pi / 2, fo)) ** 2
    clip *= env[:, None]
    clip *= 10 ** (gain_db / 20.0)
    peak = np.abs(clip).max()
    if peak > 0.89:                                  # keep about 1 dB of headroom, never clip
        clip *= 0.89 / peak
    wavfile.write(HERE / '04-sample.wav', SR, np.round(clip * 32767).astype(np.int16))
    print('wrote', HERE / '04-sample.wav', '%.3f s' % (n / SR), 'peak %.3f' % np.abs(clip).max())


if __name__ == '__main__':
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.0)
