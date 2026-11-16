"""The band checks: where a bed's energy sits, against the bar (TESTING.md).

A bed has to leave the voice its room (standard/MUSIC.md, the bar). Measured on the whole file (power spectrum of the mono sum, Hann window):
    lt1k        % of the energy under 1 kHz                  bar: >= 98.8
    voice_band  % of the energy in 1-4 kHz (speech clarity)  bar: <= 1.2
    sub         % of the energy under 80 Hz                  reference beds: 5-76 (reported, not a gate)
    centroid    power-weighted spectral centroid, Hz         reported (pick.py penalises past 760)
And the reference-style measures (librosa at 22.05 kHz mono, how the reference beds were profiled):
    centroid_med   median frame spectral centroid, Hz        reference beds: 417-764
    onsets_s       onsets a second                           reference beds: 4.1-6.5
    range_8s_db    loudest minus quietest 8-s block, dB      reference beds: 4-12 (blocks quieter than 30 dB under the
                                                             loudest are left out: the tail)

    SYNTH tools/music/music.py bands <wav> [<wav> ...] [--judge]      the numbers and, with --judge, the quality model and the verdict
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import soundfile as sf

from .settings import SR

BAR = {"PQ": 7.6, "CE": 6.9, "CU": 7.6, "lt1k": 98.8, "voice_band": 1.2}


def measure(mix: np.ndarray, sr: int = SR) -> dict:
    """mix: (2, n) or (n,) float. The gate's band numbers."""
    m = mix.mean(0) if mix.ndim == 2 else mix
    S = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / sr)
    tot = S.sum() + 1e-12
    return {"centroid": round(float((f * S).sum() / tot)), "lt1k": round(float(S[f < 1000].sum() / tot * 100), 2),
            "voice_band": round(float(S[(f >= 1000) & (f < 4000)].sum() / tot * 100), 2),
            "sub": round(float(S[f < 80].sum() / tot * 100), 1)}


def profile(path: str) -> dict:
    """The reference-style measures (librosa, 22.05 kHz mono)."""
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    step = int(8 * sr / 512)
    blocks = np.array([float(np.sqrt(np.mean(rms[i:i + step] ** 2))) for i in range(0, len(rms), step)]) + 1e-12
    db = 20 * np.log10(blocks)
    live = db[db > db.max() - 30]
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=1024)) ** 2
    cen = float(np.median(librosa.feature.spectral_centroid(S=np.sqrt(S), sr=sr)[0]))
    on = librosa.onset.onset_detect(y=y, sr=sr)
    return {"dur": round(dur, 2), "centroid_med": round(cen), "onsets_s": round(len(on) / dur, 2),
            "range_8s_db": round(float(live.max() - live.min()), 1)}


def verdict(m: dict, j: dict | None = None) -> tuple[bool, list[str]]:
    """At the bar? Returns (ok, the reasons it is not)."""
    why = []
    if m["lt1k"] < BAR["lt1k"]:
        why.append(f"only {m['lt1k']}% under 1 kHz (bar >= {BAR['lt1k']})")
    if m["voice_band"] > BAR["voice_band"]:
        why.append(f"{m['voice_band']}% in 1-4 kHz (bar <= {BAR['voice_band']})")
    if j is not None:
        for k in ("PQ", "CE", "CU"):
            if j.get(k, 0) < BAR[k]:
                why.append(f"{k} {j.get(k)} (bar >= {BAR[k]})")
    return not why, why


def main():
    ap = argparse.ArgumentParser(prog="music.py bands")
    ap.add_argument("wavs", nargs="+")
    ap.add_argument("--judge", action="store_true")
    a = ap.parse_args()
    for w in a.wavs:
        x, sr = sf.read(w, dtype="float32", always_2d=True)
        m = measure(x.T, sr)
        p = profile(w)
        j = None
        if a.judge:
            from . import judge
            j = judge.score_array(x, sr)
        ok, why = verdict(m, j)
        tag = ("AT THE BAR" if ok else "UNDER THE BAR: " + "; ".join(why)) if a.judge else ("bands ok" if ok else "; ".join(why))
        print(f"{w}\n  bands {json.dumps(m)}\n  profile {json.dumps(p)}" + (f"\n  judge {json.dumps(j)}" if j else "")
              + f"\n  -> {tag}", flush=True)


if __name__ == "__main__":
    main()
