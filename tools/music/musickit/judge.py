"""The stand-in ear: Meta's Audiobox Aesthetics.

Model: Audiobox Aesthetics by Meta (facebook/audiobox-aesthetics on Hugging Face; pip package audiobox_aesthetics 0.0.4, CC-BY 4.0;
the checkpoint, 415 MB, downloads on the first call into MEDIA/models/hf; tested with snapshot
9b1dd8e5df9af7216e836a98974fe3b82c56ded6). Trained on human ratings, it gives four 1-10 scores per clip: PQ production quality, PC
production complexity, CE content enjoyment, CU content usefulness. A bed is scored in 10-s windows, then the median of each score
(and the worst PQ window). It is a filter against a cheap or harsh render, never the verdict: the creator's ears are.

Calibration (standard/MUSIC.md, the bar): five licensed library beds that passed a listening test scored PQ 7.6-8.0, CE 6.9-7.5,
CU 7.6-8.0.

    SYNTH tools/music/music.py judge <wav> [<wav> ...] [--from S --to S] [--win 10]
    SYNTH tools/music/music.py judge --warm          downloads the model and scores four seconds of quiet noise (the setup's check)

The audio goes to the model as tensors (torchaudio 2.9+ loads files through torchcodec, which this setup doesn't need).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np

from .settings import MODELS

os.environ.setdefault("HF_HOME", str(MODELS / "hf"))   # the model lives with the other models under MEDIA, not in the user folder
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")   # Windows without developer mode: the cache copies instead (harmless)
os.environ.setdefault("HF_HUB_VERBOSITY", "error")              # no "unauthenticated requests" notice: the model is public
_PRED = None


def predictor():
    global _PRED
    if _PRED is None:
        import warnings
        with warnings.catch_warnings():   # the model's own library warns about deprecated torch calls it makes: nothing to act on
            warnings.simplefilter("ignore", FutureWarning)
            warnings.simplefilter("ignore", UserWarning)
            from audiobox_aesthetics.infer import initialize_predictor
            _PRED = initialize_predictor()
    return _PRED


def score(path: str, t0: float = 0.0, t1: float | None = None, win: float = 10.0) -> dict:
    import soundfile as sf
    y, sr = sf.read(path, always_2d=True, dtype="float32")
    a, b = int(t0 * sr), int((t1 if t1 else len(y) / sr) * sr)
    return score_array(y[a:b], sr, win)


def score_array(y: np.ndarray, sr: int, win: float = 10.0) -> dict:
    """y: (samples, channels) float32. Windows shorter than 3 s are not scored."""
    import torch
    rows = []
    items = []
    n = int(win * sr)
    for i in range(0, max(1, len(y) - n // 2), n):
        seg = y[i:i + n]
        if len(seg) < sr * 3:
            break
        items.append({"path": torch.from_numpy(np.ascontiguousarray(seg.T)), "sample_rate": sr})
    import warnings
    pred = predictor()
    with warnings.catch_warnings():   # a deprecation notice from inside the model's attention layers, on every call
        warnings.simplefilter("ignore", UserWarning)
        for k in range(0, len(items), 8):
            for o in pred.forward(items[k:k + 8]):
                rows.append([o["PQ"], o["PC"], o["CE"], o["CU"]])
    if not rows:
        raise ValueError("nothing to score: the audio is shorter than 3 s")
    r = np.array(rows)
    med = np.median(r, axis=0)
    return {"PQ": round(float(med[0]), 2), "PC": round(float(med[1]), 2), "CE": round(float(med[2]), 2),
            "CU": round(float(med[3]), 2), "windows": len(rows), "PQ_min": round(float(r[:, 0].min()), 2)}


def main():
    ap = argparse.ArgumentParser(prog="music.py judge")
    ap.add_argument("wavs", nargs="*")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--win", type=float, default=10.0)
    ap.add_argument("--warm", action="store_true", help="download the model and check it runs")
    a = ap.parse_args()
    if a.warm:
        rng = np.random.default_rng(0)
        y = (0.01 * rng.standard_normal((4 * 48000, 2))).astype(np.float32)
        print("model ok:", score_array(y, 48000, win=4.0), "| HF_HOME", os.environ["HF_HOME"])
        return
    for w in a.wavs:
        s = score(w, a.t0, a.t1, a.win)
        print(f"{Path(w).name:45s} PQ {s['PQ']:5.2f} (min {s['PQ_min']:5.2f})  PC {s['PC']:5.2f}  CE {s['CE']:5.2f}  CU {s['CU']:5.2f}"
              f"  [{s['windows']} windows]", flush=True)


if __name__ == "__main__":
    main()
