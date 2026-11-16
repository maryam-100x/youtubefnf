"""A blind A/B pair for the creator's ears: the same window of the film, two full mixes (e.g. a licensed track vs. the written bed, or
two beds), brought to the same loudness (gain only, so the voice sits at the same level), the same 0.3-s fades, in random order.
The key goes to <outdir>/KEY.json, kept back until the listener has answered. With --video, each clip gets the film's picture
(ffmpeg needed); without it the clips are WAVs.

    SYNTH tools/music/music.py ab <mixA.wav> <mixB.wav> <t0> <t1> <outdir> [--video film.mp4] [--seed N]
      mixA: the reference (its loudness is kept), mixB: the new one
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from .settings import _paths

FFMPEG = _paths.FFMPEG

from .loudness import lufs


def main():
    ap = argparse.ArgumentParser(prog="music.py ab")
    ap.add_argument("mix_a")
    ap.add_argument("mix_b")
    ap.add_argument("t0", type=float)
    ap.add_argument("t1", type=float)
    ap.add_argument("outdir")
    ap.add_argument("--video", default="")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    A, sr = sf.read(a.mix_a, dtype="float32", always_2d=True)
    B, srb = sf.read(a.mix_b, dtype="float32", always_2d=True)
    if not sr == srb == 48000:
        raise SystemExit("both mixes must be 48 kHz")
    la, lb = lufs(A), lufs(B)
    gb = 10 ** ((la - lb) / 20)
    print(f"integrated: A {la:.2f} LUFS, B {lb:.2f} LUFS -> B gain {la - lb:+.3f} dB")
    i0, i1 = int(a.t0 * sr), int(a.t1 * sr)
    fade = int(0.3 * sr)
    env = np.ones(i1 - i0, np.float32)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    clips = {"A": A[i0:i1] * env[:, None], "B": B[i0:i1] * gb * env[:, None]}
    rnd = random.Random(a.seed)
    order = ["A", "B"]
    rnd.shuffle(order)
    key = {}
    ff = FFMPEG if shutil.which(FFMPEG) else None
    if a.video and not ff:
        raise SystemExit("--video needs ffmpeg on PATH")
    pic = out / "_picture.mp4"
    if a.video:
        subprocess.run([ff, "-v", "error", "-y", "-ss", f"{a.t0:.3f}", "-t", f"{a.t1 - a.t0:.3f}", "-i", a.video, "-an", "-c:v",
                        "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(pic)], check=True)
    for i, k in enumerate(order, 1):
        wav = out / f"clip_{i}.wav"
        sf.write(wav, clips[k], sr, subtype="PCM_24")
        if a.video:
            subprocess.run([ff, "-v", "error", "-y", "-i", str(pic), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "256k", "-shortest", str(out / f"clip_{i}.mp4")], check=True)
        key[f"clip_{i}"] = k
    (out / "KEY.json").write_text(json.dumps({"key": key, "A": a.mix_a, "B": a.mix_b, "window": [a.t0, a.t1],
                                              "B_gain_db": round(la - lb, 3)}, indent=1), encoding="utf-8")
    print("clips: clip_1, clip_2 | the key in KEY.json (don't open it before the listener answers)")


if __name__ == "__main__":
    main()
