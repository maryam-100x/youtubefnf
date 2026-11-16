"""Beat joins with no breath between them (a sentence's last word running straight into the next beat's first at a splice, so the
end of the sentence sounds cut off).
For every boundary between two beats (words.json's `beat` changes): the longest run of 10-ms frames under -45 dB between the last
word's start + 0.10 s and the next beat's first word + 0.15 s. A sentence end needs a pause (the voice's median 0.18 s); a join with
no run of 0.08 s or more is flagged, with the levels around it. Exit 1 if any.

  EDIT tools/sound/beat_joins.py <narration.wav> <words.json> [--min 0.08] [--quiet -45]"""
import argparse
import json
import sys

import numpy as np
import soundfile as sf


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("words")
    ap.add_argument("--min", type=float, default=0.08)
    ap.add_argument("--quiet", type=float, default=-45.0)
    a = ap.parse_args()
    x, sr = sf.read(a.wav, always_2d=True)
    x = x.mean(axis=1)
    hop = int(sr * 0.01)
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-12)
    w = json.load(open(a.words, encoding="utf-8"))
    w = w["words"] if isinstance(w, dict) else w
    hits = []
    for i in range(len(w) - 1):
        if w[i + 1]["beat"] == w[i]["beat"]:
            continue
        f0, f1 = int((w[i]["start"] + 0.10) / 0.01), min(n, int((w[i + 1]["start"] + 0.15) / 0.01))
        run = best = 0
        for f in range(f0, f1):
            run = run + 1 if db[f] < a.quiet else 0
            best = max(best, run)
        if best * 0.01 < a.min:
            hits.append((w[i]["beat"], w[i]["w"], w[i + 1]["beat"], w[i + 1]["w"], round(w[i]["end"], 2), best * 0.01))
    for h in hits:
        print(f"{h[0]:6} {h[1]!r:16} -> {h[2]:6} {h[3]!r:14} at {h[4]:8.2f} s: longest pause {h[5]:.2f} s")
    print(f"{len(hits)} join(s) without a pause")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
