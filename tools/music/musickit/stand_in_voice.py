"""A stand-in for a narration, made from the word times alone, so the whole chain can be tested with no voice recording.

Each word becomes a burst of speech-shaped sound for exactly its start-end: a buzz (a pulse train at 110-140 Hz, moving a little like
intonation) plus breath noise, band-limited to 100-5000 Hz, shaped into ~4 syllables a second with 15-ms edges. It has a voice's
band and rhythm, so the ducking, the carve and the loudness checks behave as they would under a real voice. It is not speech and
not anyone's voice. A real video uses its real narration.

    SYNTH tools/music/music.py stand-in <words.json> <out.wav> [--seed 1]
"""
from __future__ import annotations

import argparse

import numpy as np

from .settings import SR, ensure_parent
from .writing import Words


def make(words: Words, seed: int = 1, tail: float = 3.0) -> np.ndarray:
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(seed)
    total = int((words.end() + tail) * SR)
    y = np.zeros(total, np.float32)
    bp = butter(4, [100, 5000], btype="bandpass", fs=SR, output="sos")
    for x in words.W:
        a, b = int(x["start"] * SR), int(x["end"] * SR)
        n = b - a
        if n <= 0:
            continue
        t = np.arange(n) / SR
        f0 = rng.uniform(110, 140) * (1 + 0.06 * np.sin(2 * np.pi * rng.uniform(0.5, 1.5) * t))
        ph = np.cumsum(2 * np.pi * f0 / SR)
        buzz = sum(np.sin(k * ph) / k for k in range(1, 30))
        noise = rng.standard_normal(n)
        s = 0.8 * buzz / 3 + 0.25 * noise
        syl = 0.55 + 0.45 * np.abs(np.sin(np.pi * rng.uniform(3.5, 4.5) * t + rng.uniform(0, np.pi)))
        e = np.minimum(1, np.minimum(t / 0.015, (n / SR - t) / 0.015))
        y[a:b] += (s * syl * e * rng.uniform(0.7, 1.0)).astype(np.float32)
    y = sosfilt(bp, y).astype(np.float32)
    speech = np.abs(y) > 1e-6
    rms = np.sqrt((y[speech] ** 2).mean()) if speech.any() else 1.0
    return (y * (10 ** (-20 / 20) / rms)).astype(np.float32)


def main():
    ap = argparse.ArgumentParser(prog="music.py stand-in")
    ap.add_argument("words")
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    import soundfile as sf
    y = make(Words(a.words), a.seed)
    sf.write(ensure_parent(a.out), y, SR, subtype="PCM_24")
    print(f"stand-in voice: {len(y) / SR:.1f} s -> {a.out}")


if __name__ == "__main__":
    main()
