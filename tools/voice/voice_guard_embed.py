"""The voice guard's ears, part 1: what a window of a narration sounds like, as numbers (runs in the accent venv, which holds
speechbrain). For every window of each wav (2.0 s, hop 0.5 s) three things, all from local models:
  spk    a 192-d speaker embedding (SpeechBrain ECAPA-TDNN trained on VoxCeleb, MODELS/spkrec_ecapa_voxceleb, Apache 2.0):
         how the voice sounds as a voice (timbre, closeness, delivery); a British stretch or a close-to-the-mic stretch moves away from
         the creator's approved voice in this space
  acc    the CommonAccent classifier's own 192-d embedding (MODELS/commonaccent_ecapa) and its 16 accent probabilities (the same model
         and scaling as accent_id.py)
Written next to the wav as <wav>.guard_embed.json (the cache the guard reads); unchanged wavs are skipped. torch runs on 2 threads
(more is 20-30x slower while other jobs share the CPU).

  ACCENT tools/voice/voice_guard_embed.py <wav or folder> [...] [--win 2.0] [--hop 0.5] [--force]
      (ACCENT = the accent venv's python, `python tools/common/paths.py` prints it; a folder = every .wav under it, e.g.
      <MEDIA>/voice/guard when building the guard's reference: voice_guard_calib.py)"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
import torchaudio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from paths import FFMPEG, MODELS  # noqa: E402

torch.set_num_threads(int(__import__("os").environ.get("VOICE_TORCH_THREADS", "2")))   # 2: more threads beside other CPU jobs oversubscribe the CPU
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]
from speechbrain.inference.classifiers import EncoderClassifier  # noqa: E402
from speechbrain.inference.speaker import EncoderClassifier as SpeakerEncoder  # noqa: E402
from speechbrain.utils.fetching import LocalStrategy  # noqa: E402

SPK_MODEL = (MODELS / "spkrec_ecapa_voxceleb").as_posix()
ACC_MODEL = (MODELS / "commonaccent_ecapa").as_posix()
SR = 16000
VERSION = 1


def load(path):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def stamp(path):
    st = os.stat(path)
    return f"{st.st_size}-{int(st.st_mtime)}-v{VERSION}"


def models():
    spk = SpeakerEncoder.from_hparams(source=SPK_MODEL, savedir=SPK_MODEL + "/_sb", run_opts={"device": "cpu"},
                                      overrides={"pretrained_path": SPK_MODEL}, local_strategy=LocalStrategy.COPY)
    acc = EncoderClassifier.from_hparams(source=ACC_MODEL, savedir=ACC_MODEL + "/_sb", run_opts={"device": "cpu"},
                                         overrides={"pretrained_path": ACC_MODEL}, local_strategy=LocalStrategy.COPY)
    labels = [acc.hparams.label_encoder.decode_ndim(i) for i in range(16)]
    return spk, acc, labels


def embed(path, spk, acc, labels, win=2.0, hop=0.5, old=None):
    """old: the wav's previous cache; a window whose samples hash the same as one in it keeps its numbers (the voice lock: a lay-in
    changes a few seconds of a long narration, and a full pass of a 52-min one takes ~40 min; this way only the changed windows run)"""
    x = load(path)
    reuse = {}
    if old and old.get("win") == win and old.get("hop") == hop and old.get("h"):
        reuse = {h: (sp, ac, pp) for h, sp, ac, pp in zip(old["h"], old["spk"], old["acc"], old["p"])}
    W, H = int(win * SR), int(hop * SR)
    n = len(x)
    starts = list(range(0, max(1, n - W + 1), H)) or [0]
    if starts[-1] + W < n - H:  # the tail
        starts.append(max(0, n - W))
    rows_t, rows_spk, rows_acc, rows_p, rows_h = [], [], [], [], []
    with torch.no_grad():
        for s in starts:
            seg = x[s:s + W]
            if len(seg) < int(0.6 * SR) or np.sqrt(np.mean(seg ** 2)) < 0.003:  # silence or a stub: no numbers
                continue
            hsh = hashlib.sha1(seg.tobytes()).hexdigest()[:20]
            if hsh in reuse:
                sp, ac, pp = reuse[hsh]
                rows_t.append(round(s / SR, 3))
                rows_spk.append(sp)
                rows_acc.append(ac)
                rows_p.append(pp)
                rows_h.append(hsh)
                continue
            t = torch.from_numpy(seg).unsqueeze(0)
            e = spk.encode_batch(t).reshape(-1).numpy()
            a = acc.encode_batch(t).reshape(-1).numpy()
            out = acc.mods.classifier(torch.from_numpy(a).reshape(1, 1, -1)) if hasattr(acc.mods, "classifier") else None
            if out is None:
                out = acc.classify_batch(t)[0]
            p = torch.softmax(30 * out.reshape(-1), dim=-1).numpy()  # cosine scores x the training scale = probabilities
            rows_t.append(round(s / SR, 3))
            rows_spk.append(np.round(e / (np.linalg.norm(e) + 1e-9), 5).tolist())
            rows_acc.append(np.round(a / (np.linalg.norm(a) + 1e-9), 5).tolist())
            rows_p.append(np.round(p, 4).tolist())
            rows_h.append(hsh)
    return {"wav": str(path), "stamp": stamp(path), "win": win, "hop": hop, "seconds": round(n / SR, 3), "labels": labels,
            "t": rows_t, "spk": rows_spk, "acc": rows_acc, "p": rows_p, "h": rows_h}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wavs", nargs="+", help="wav files or folders (a folder = every .wav under it)")
    ap.add_argument("--win", type=float, default=2.0)
    ap.add_argument("--hop", type=float, default=0.5)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    todo = []
    wavs = []
    for w in map(Path, a.wavs):
        wavs += sorted(w.rglob("*.wav")) if w.is_dir() else [w]
    for w in wavs:
        out = w.with_name(w.name + ".guard_embed.json")
        if out.exists() and not a.force:
            try:
                d = json.loads(out.read_text(encoding="utf-8"))
                if d.get("stamp") == stamp(w) and d.get("win") == a.win and d.get("hop") == a.hop:
                    continue
            except Exception:
                pass
        todo.append((w, out))   # (an old cache of the same wav name is passed on: its unchanged windows are reused by hash)
    if not todo:
        print("all cached")
        return
    spk, acc, labels = models()
    for w, out in todo:
        old = None
        if out.exists() and not a.force:
            try:
                old = json.loads(out.read_text(encoding="utf-8"))
            except Exception:
                old = None
        d = embed(w, spk, acc, labels, a.win, a.hop, old)
        out.write_text(json.dumps(d), encoding="utf-8")
        uk = [sum(p[labels.index(k)] for k in ("england", "scotland", "wales", "ireland", "australia", "newzealand")) for p in d["p"]]
        print(f"{w.name}: {len(d['t'])} windows, {d['seconds']:.1f} s, British-leaning {np.mean([u > 0.5 for u in uk]) if uk else 0:.0%}")


if __name__ == "__main__":
    sys.exit(main())
