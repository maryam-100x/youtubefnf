"""Word endings cut into digital silence (a word that sounds weird or cut off at its end, its last consonant gone). A spoken ending
decays over 40 ms or more; a mute
or a pause cut that took the word's own tail drops from audible sound straight to digital silence. For every word: in a window from
0.05 s after its start to 0.25 s after its end (Whisper's word ends run long), a 5-ms frame at -30 dB or louder followed within 10 ms by a frame under -75 dB (digital
silence, what the chain's cuts and mutes leave) is a cut ending. Prints beat, word, time, the levels; exit 1 if any.

  EDIT tools/sound/cut_ends.py <narration.wav> <words.json> [--loud -30] [--sil -75] [--within 2]"""
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
    ap.add_argument("--loud", type=float, default=-30.0)
    ap.add_argument("--sil", type=float, default=-75.0)
    ap.add_argument("--within", type=int, default=2, help="5-ms frames from the loud frame to silence")
    a = ap.parse_args()
    x, sr = sf.read(a.wav, always_2d=True)
    x = x.mean(axis=1)
    hop = int(sr * 0.005)
    n = len(x) // hop
    fr = x[:n * hop].reshape(n, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-12)
    words = json.load(open(a.words, encoding="utf-8"))
    if isinstance(words, dict):   # build/captions/words.json is {"mode": ..., "words": [...]}
        words = words["words"]
    hits = []
    for i, w in enumerate(words):
        f0, f1 = int((w["start"] + 0.05) / 0.005), int((w["end"] + 0.25) / 0.005)
        nxt = words[i + 1]["start"] if i + 1 < len(words) else 1e9
        f1 = min(f1, int(nxt / 0.005), n - 4)
        for f in range(max(0, f0), f1):
            if db[f] >= a.loud and min(db[f + 1:f + 1 + a.within]) < a.sil:
                hits.append((w["beat"], w["w"], round(f * 0.005, 3), round(float(db[f]), 1), [round(float(v), 1) for v in db[f + 1:f + 4]]))
                break
    for h in hits:
        print(f"{h[0]:6} {h[1]!r:22} {h[2]:9.3f} s  {h[3]} dB -> {h[4]}")
    print(f"{len(hits)} cut ending(s) in {len(words)} words")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
