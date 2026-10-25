"""Synthesise the background music for the UNWRAP video -> music.js (MP3, base64) + audio/music.mp3

A calm, warm explainer-style bed (think Kurzgesagt): soft detuned pad, round sub-bass, glassy plucked
arpeggio with a ping-pong echo, a tiny shaker in the middle section, and a light room reverb.
D major, 76 bpm, chords D - Bm - G - A.  The page ducks it under the voice and swells it for the title and ending.

Usage: python make_music.py [length_seconds]     (default 330)
Needs: numpy, scipy, lameenc
"""
import base64, pathlib, sys
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt
import lameenc

HERE = pathlib.Path(__file__).parent
SR = 44100
LENGTH = float(sys.argv[1]) if len(sys.argv) > 1 else 330.0
BPM = 76
BEAT = 60 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(7)
N = int(SR * LENGTH)
L = np.zeros(N); R = np.zeros(N)           # dry mix
PL = np.zeros(N); PR = np.zeros(N)          # pluck bus (goes through the echo)

mtof = lambda n: 440.0 * 2 ** ((n - 69) / 12)
PROG = [[50, 57, 61, 64], [47, 54, 57, 61], [43, 50, 54, 59], [45, 52, 55, 59]]

def lowpass(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), btype="low", output="sos"), x)

def add(buf, w, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(w))
    buf[i:j] += w[: j - i] * gain

def pad_wave(chord, det, dur):
    t = np.arange(int(SR * dur)) / SR
    w = np.zeros_like(t)
    for n in chord:
        f = mtof(n) * 2 ** (det / 1200)
        for h in range(1, 14):                      # band-limited saw
            if f * h > 2400: break
            w += np.sin(2 * np.pi * f * h * t + h) / h
    env = np.minimum(1, t / 1.25) * np.minimum(1, np.maximum(0, (dur - t)) / 1.1)
    return lowpass(w * env, 950)

def bass_wave(n):
    t = np.arange(int(SR * BAR)) / SR
    f = mtof(n)
    w = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(1, t / 0.05) * np.exp(-t * 0.9) * np.minimum(1, (BAR - t) / 0.3)
    return w * env

def pluck_wave(n):
    t = np.arange(int(SR * 1.7)) / SR
    f = mtof(n)
    w = np.zeros_like(t)
    for m, a, d in [(1, 1.0, 2.6), (2, 0.30, 4.0), (3, 0.10, 6.0), (4.01, 0.05, 8.0)]:
        w += a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d)
    w *= np.minimum(1, t / 0.006)
    return w * np.minimum(1, (1.7 - t) / 0.1)

def shaker_wave():
    t = np.arange(int(SR * 0.09)) / SR
    n = rng.standard_normal(len(t))
    sos = butter(2, 6500 / (SR / 2), btype="high", output="sos")
    return sosfilt(sos, n) * np.exp(-t * 55)

pads = {(ci, d): pad_wave(PROG[ci], d, BAR + 1.2) for ci in range(4) for d in (-9, 0, 9)}
basses = [bass_wave(PROG[ci][0] - 12) for ci in range(4)]
plucks = {}
shk = shaker_wave()
PAT = [0, 2, 1, 3, 2, 1, 3, 2]
PANS = [-.35, .1, -.1, .4, -.25, .2, -.4, .3]

nbars = int(LENGTH / BAR) + 1
for b in range(nbars):
    t0 = b * BAR
    ci = b % 4
    for d, pan in ((-9, -0.55), (0, 0.0), (9, 0.55)):
        w = pads[(ci, d)]
        gl, gr = 0.0125 * np.sqrt((1 - pan) / 2) * 1.4, 0.0125 * np.sqrt((1 + pan) / 2) * 1.4
        add(L, w, t0, gl * 1.0); add(R, w, t0, gr * 1.0)
    add(L, basses[ci], t0, 0.19); add(R, basses[ci], t0, 0.19)
    for i in range(8):
        tt = t0 + i * BEAT / 2
        n = PROG[ci][PAT[i]] + 12 + (12 if i % 4 == 3 else 0)
        if n not in plucks: plucks[n] = pluck_wave(n)
        vel = (0.10 if i % 2 == 0 else 0.055) * (0.9 + 0.2 * rng.random())
        pan = PANS[i]
        add(PL, plucks[n], tt, vel * np.sqrt((1 - pan) / 2)); add(PR, plucks[n], tt, vel * np.sqrt((1 + pan) / 2))
        if i % 2 == 1 and 90 < tt < LENGTH - 20:
            add(L, shk, tt, 0.020); add(R, shk, tt, 0.020)

# ping-pong echo on the plucks
echo_l, echo_r = PL.copy(), PR.copy()
d = int(0.38 * SR)
for k in range(1, 6):
    g = 0.42 ** k
    sl, sr_ = (PR, PL) if k % 2 else (PL, PR)
    echo_l[d * k:] += lowpass(sl, 3000)[: N - d * k] * g
    echo_r[d * k:] += lowpass(sr_, 3000)[: N - d * k] * g
L += echo_l; R += echo_r

# room reverb (synthetic impulse response)
ir_len = int(1.9 * SR)
ti = np.arange(ir_len) / SR
ir = rng.standard_normal(ir_len) * np.exp(-ti * 2.6)
ir = lowpass(ir, 4200)
ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
ir /= np.sqrt(np.sum(ir ** 2))
wet_l = fftconvolve(L, ir)[:N]
ir2 = np.roll(ir, 37) * -1
wet_r = fftconvolve(R, ir2)[:N]
L = L * 0.82 + wet_l * 0.22
R = R * 0.82 + wet_r * 0.22

mix = np.stack([L, R], axis=1)
mix *= 0.88 / np.max(np.abs(mix))
fade = int(SR * 0.05)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
print("peak", float(np.max(np.abs(mix))), "rms", float(np.sqrt(np.mean(mix ** 2))))

pcm = (mix * 32767).astype("<i2")
enc = lameenc.Encoder()
enc.set_bit_rate(128); enc.set_in_sample_rate(SR); enc.set_channels(2); enc.set_quality(2)
mp3 = bytes(enc.encode(pcm.tobytes())) + bytes(enc.flush())
(HERE / "audio").mkdir(exist_ok=True)
(HERE / "audio" / "music.mp3").write_bytes(mp3)
(HERE / "music.js").write_text("/* generated by make_music.py */\nwindow.MUSIC_DATA='%s';\n" % base64.b64encode(mp3).decode(), encoding="ascii")
print("music.mp3", len(mp3) // 1024, "KB,", LENGTH, "s")
