"""Measure Surge XT patches for a role, in bulk, before anything is heard.

Each patch plays a short test phrase for its role; the render is measured: level, spectral centroid, energy under 1 kHz and in the
voice band (1-4 kHz), the sub's share (under 80 Hz), attack (time to 90% of the peak level), sustain (level at the end against the
start), noisiness (spectral flatness), stereo width (side RMS over mid RMS), and pitch clarity (the chroma share on the notes played:
low = detuned, noisy or an effect). Use it to cut a library of ~3,000 patches down to a candidate list for pick.py.

    SYNTH tools/music/music.py audition <role> <out.json> [--only <substring>] [--limit N] [--part i/N]
    roles: pad (Dm chord, 6 s), bass (D1/D2 eighths), pulse (eighths on D3/A3 at 100 bpm), keys (Dm arpeggio), drone (D2 held 8 s),
           fx (C3 held 3 s: risers, impacts, ticks)
    --part i/N: this process takes every N-th patch from the i-th (run N processes side by side: Surge renders on one core each)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from .settings import SR, ensure_parent
from .surge import Surge, list_patches

CATS = {
    "pad": ("Pads", "Polysynths", "Chords", "Winds"),
    "bass": ("Basses",),
    "pulse": ("Plucks", "Sequences"),
    "keys": ("Keys", "Plucks"),
    "drone": ("Pads", "FX", "Winds"),
    "fx": ("FX", "Percussion"),
}


def phrase(role: str):
    """(notes, seconds, the MIDI notes whose pitch classes count as 'in tune')."""
    if role == "pad":
        return [(0.0, 6.0, n, 80) for n in (50, 53, 57)], 8.0, [50, 53, 57]
    if role == "bass":
        return [(i * 0.3, 0.25, 26 if i % 4 else 38, 100) for i in range(16)], 5.5, [26, 38]
    if role == "pulse":
        return [(i * 0.3, 0.2, (50, 57)[i % 2], 90) for i in range(16)], 5.5, [50, 57]
    if role == "keys":
        return [(i * 0.6, 1.2, (50, 53, 57, 62)[i % 4], 75) for i in range(8)], 6.5, [50, 53, 57, 62]
    if role == "drone":
        return [(0.0, 8.0, 38, 90)], 9.0, [38]
    if role == "fx":
        return [(0.0, 3.0, 48, 100)], 6.0, [48]
    raise ValueError(role)


def measure(a: np.ndarray, notes: list[int]) -> dict:
    import librosa
    m = a.mean(0)
    peak = float(np.abs(a).max())
    if peak < 1e-4:
        return {"peak": peak, "silent": True}
    rms = float(np.sqrt((m ** 2).mean()))
    S = np.abs(librosa.stft(m, n_fft=4096, hop_length=1024)) ** 2
    fr = librosa.fft_frequencies(sr=SR, n_fft=4096)
    e = S.sum(1)
    tot = e.sum() + 1e-12
    env = librosa.feature.rms(y=m, frame_length=2048, hop_length=480)[0]
    i90 = int(np.argmax(env >= 0.9 * env.max()))
    sec = SR // 480
    first, last = env[:sec].mean() + 1e-9, env[-2 * sec:-sec].mean() + 1e-9
    side = (a[0] - a[1]) / 2
    chroma = librosa.feature.chroma_stft(S=S, sr=SR).mean(1)
    pcs = {n % 12 for n in notes}
    clar = float(sum(chroma[p] for p in pcs) / (chroma.sum() + 1e-9))
    return {
        "peak": round(peak, 4), "rms_db": round(20 * np.log10(rms + 1e-12), 1),
        "centroid": round(float((fr * e).sum() / tot)), "lt1k": round(float(e[fr < 1000].sum() / tot) * 100, 1),
        "voice_band": round(float(e[(fr >= 1000) & (fr < 4000)].sum() / tot) * 100, 2),
        "sub": round(float(e[fr < 80].sum() / tot) * 100, 1), "attack": round(i90 * 480 / SR, 3),
        "sustain_db": round(float(20 * np.log10(last / first)), 1),
        "flatness": round(float(librosa.feature.spectral_flatness(S=S).mean()), 4),
        "width": round(float(np.sqrt((side ** 2).mean()) / (rms + 1e-12)), 3), "pitch_clarity": round(clar, 3),
    }


def main():
    ap = argparse.ArgumentParser(prog="music.py audition")
    ap.add_argument("role")
    ap.add_argument("out")
    ap.add_argument("--only", default="", help="keep patches whose library path contains this")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--part", default="", help="i/N: this process takes every N-th patch from the i-th")
    a = ap.parse_args()
    cats = CATS[a.role]
    names = [p for p in list_patches(a.only) if any(f"/{c}/" in f"/{p}" for c in cats)]
    if a.part:
        i, n = (int(x) for x in a.part.split("/"))
        names = names[i::n]
    if a.limit:
        names = names[: a.limit]
    notes, secs, pcs = phrase(a.role)
    s = Surge()
    out = {}
    t0 = time.time()
    for i, n in enumerate(names):
        try:
            s.load(n)
            audio = s.render(notes, secs)
            out[n] = measure(audio, pcs)
        except Exception as e:  # a patch that fails to load is skipped, named in the report
            out[n] = {"error": str(e)[:200]}
        if i % 25 == 0:
            print(f"{i}/{len(names)} {time.time() - t0:.0f}s", flush=True)
    ensure_parent(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"done: {len(out)} patches in {time.time() - t0:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
