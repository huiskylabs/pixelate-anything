"""The 5 s sound sample: sunset into night. A thunder roll of my own (low-passed noise rumble, a
short crack, a sine sub that swells with it) mixed over the engine's ambient render (pad, music
box, sub drone, wind and fire), cut so the thunder owns the first second and the music box
answers after it.

    python3 sound/make_sample.py      (after: pixelate audio music sound/full.wav)
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, lfilter
import subprocess, pathlib

HERE = pathlib.Path(__file__).resolve().parent
SR = 48000
N = 5 * SR                                       # exactly 5.0 s


def load(path):
    sr, x = wavfile.read(path)
    assert sr == SR
    x = x.astype(np.float64)
    if x.dtype.kind == 'i' or np.abs(x).max() > 2:
        x /= 32768.0
    return x if x.ndim == 2 else np.stack([x, x], 1)


def envelope(x, lo, hi, hop=480):
    sos = butter(4, [lo, hi], 'bandpass', fs=SR, output='sos')
    y = sosfilt(sos, x.mean(1))
    n = len(y) // hop
    return np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12), hop


def pick_window(x):
    """a start where the music box is quiet for the first ~1.1 s, then enters at 1.2-2.2 s and
    keeps answering (at least two more onsets inside the clip)"""
    env, hop = envelope(x, 1100, 6000)
    db = 20 * np.log10(env)
    rise = np.diff(db, prepend=db[0])
    on = np.nonzero((rise > 2.5) & (db > db.max() - 30))[0] * hop / SR
    on = on[np.insert(np.diff(on) > 0.15, 0, True)]
    best = None
    for t0 in np.arange(0.0, len(x) / SR - 5.0, 0.05):
        inside = on[(on >= t0) & (on < t0 + 4.4)] - t0
        if len(inside) < 3 or inside[0] < 1.2 or inside[0] > 2.2:
            continue
        score = len(inside) - abs(inside[0] - 1.5)
        if best is None or score > best[0]:
            best = (score, t0, inside)
    return best


def thunder(seed=7):
    """crack at 0.10 s, rumble swelling to ~0.6 s and rolling off over 4 s, sub sine swell"""
    rng = np.random.default_rng(seed)
    t = np.arange(N) / SR
    out = np.zeros((N, 2))
    # the crack: a few sharp sub-cracks of bright noise, 10-40 ms apart, fast decay
    crack = np.zeros(N)
    t_c = 0.10
    for k, dt in enumerate([0.0, 0.018, 0.041, 0.07, 0.112]):
        i0 = int((t_c + dt) * SR)
        n = int(0.09 * SR)
        e = np.exp(-np.arange(n) / (0.012 * SR)) * (1.0 if k == 0 else 0.55 ** k)
        crack[i0:i0 + n] += rng.standard_normal(n) * e
    crack = sosfilt(butter(2, 600, 'highpass', fs=SR, output='sos'), crack)
    crack = sosfilt(butter(2, 10000, 'lowpass', fs=SR, output='sos'), crack)
    # the rumble: low-passed noise per channel (decorrelated), a cutoff that sinks as it rolls
    env = np.clip((t - 0.12) / 0.35, 0, 1) ** 1.5 * np.exp(-np.clip(t - 0.55, 0, None) / 1.25)
    roll = 1 + 0.35 * np.sin(2 * np.pi * 3.1 * t + 0.6) * np.sin(2 * np.pi * 0.7 * t)
    for ch in range(2):
        nz = rng.standard_normal(N)
        lo1 = sosfilt(butter(4, 260, 'lowpass', fs=SR, output='sos'), nz)
        lo2 = sosfilt(butter(4, 90, 'lowpass', fs=SR, output='sos'), nz)
        mix = np.where(t < 1.2, lo1 * (1 - t / 1.2) + lo2 * (t / 1.2), lo2)
        mix /= np.abs(mix).max() + 1e-9
        out[:, ch] = mix * env * roll
    # the sub: a sine gliding 46 -> 34 Hz that swells with the rumble
    f = 34 + 12 * np.exp(-t / 1.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub_env = np.clip((t - 0.15) / 0.5, 0, 1) ** 2 * np.exp(-np.clip(t - 0.7, 0, None) / 1.4)
    sub = np.sin(ph) * sub_env
    crack /= np.abs(crack).max() + 1e-9
    out[:, 0] += 0.55 * crack * 1.0 + 0.45 * sub
    out[:, 1] += 0.55 * crack * 0.8 + 0.45 * sub
    return out


def k_weight(x):
    """ITU-R BS.1770 K-weighting at 48 kHz"""
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    return lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x):
    y = k_weight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([(y[i:i + blk] ** 2).mean(0).sum() for i in range(0, len(y) - blk + 1, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[lk > -70]
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = ms[(lk > -70) & (lk > rel)]
    return -0.691 + 10 * np.log10(g.mean())


def limit(x, ceil=10 ** (-1.2 / 20)):
    """a soft knee: transparent below 0.7 of the ceiling, tanh above it (no hard clipping)"""
    k = 0.7 * ceil
    a = np.abs(x)
    over = a > k
    y = x.copy()
    y[over] = np.sign(x[over]) * (k + (ceil - k) * np.tanh((a[over] - k) / (ceil - k)))
    return y


def main():
    full = load(HERE / 'full.wav')
    score, t0, inside = pick_window(full)
    i0 = int(round(t0 * SR))
    music = full[i0:i0 + N].copy()
    print('window starts at %.2f s; music box onsets in the clip at %s s' % (t0, np.round(inside, 2)))
    th = thunder()
    # tuck the music a little under the thunder's first second, then let it answer
    t = np.arange(N) / SR
    duck = 1 - 0.35 * np.clip(1 - np.abs(t - 0.6) / 0.6, 0, 1)
    # lift the music box's register (2-6 kHz) so the top is not thin under the rumble
    bright = sosfilt(butter(2, [2200, 7000], 'bandpass', fs=SR, output='sos'), music, axis=0)
    music = music + 1.6 * bright
    mix = music * duck[:, None] * 0.9 + th * 0.34
    gain = 10 ** ((-14.0 - lufs(mix)) / 20)
    mix = limit(mix * gain)
    fade_in = np.clip(t / 0.020, 0, 1)
    fade_out = np.clip((5.0 - t) / 0.400, 0, 1) ** 1.5
    mix *= (fade_in * fade_out)[:, None]
    print('loudness %.1f LUFS, peak %.2f dBFS, %d samples' % (lufs(mix), 20 * np.log10(np.abs(mix).max()), len(mix)))
    pcm = np.round(np.clip(mix, -1, 1) * 32767).astype(np.int16)
    wavfile.write(HERE / '03-sample.wav', SR, pcm)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(HERE / '03-sample.wav'), '-codec:a', 'libmp3lame',
                    '-q:a', '2', str(HERE / '03-sample.mp3')], check=True)


if __name__ == '__main__':
    main()
