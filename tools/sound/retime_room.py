"""Room for a word end the chain cut with no room to lay it back (the sound gate's A1 "NO ROOM ... re-time or re-take": a word lost
its final t-burst where the next word follows at once). Inserts a short silence right after each
named word's end in the final narration and shifts every later word time in captions/words.json by the same amount, so tails.py --fix
can lay the lost sound back from the take; then the chain's sync re-times the picture. A re-time of 0.03 s per word, never a re-take.

  EDIT tools/sound/retime_room.py <video> <word>@<time> [<word>@<time> ...]
      [--gap 0.03]   (the word and time as the gate's A1 key prints them: quiet@126.08 but@187.32)"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("keys", nargs="+")
    ap.add_argument("--gap", type=float, default=0.03)
    a = ap.parse_args()
    P = G.paths(a.video)
    B = Path(P["dj"]) / "build"
    nar, cap = B / "voice" / "narration.wav", B / "captions" / "words.json"
    x, sr = sf.read(nar, always_2d=True)
    H = json.loads(cap.read_text(encoding="utf-8"))
    W = H["words"]
    cuts = []
    for k in a.keys:
        word, t = k.rsplit("@", 1)
        t = float(t)
        i = min((j for j in range(len(W)) if W[j]["w"].lower().strip(".,!?\"'") == word.lower()),
                key=lambda j: abs(W[j]["end"] - t), default=None)
        if i is None or abs(W[i]["end"] - t) > 0.2:
            raise SystemExit(f"no word {word!r} ending near {t}")
        cuts.append((W[i]["end"] + 0.005, W[i]["w"]))
    shutil.copy2(nar, nar.with_name("narration_preroom.wav"))
    shutil.copy2(cap, cap.with_name("words_preroom.json"))
    out, last, shift = [], 0, 0.0
    for at, w in sorted(cuts):
        s = int(round(at * sr))
        out += [x[last:s], np.zeros((int(round(a.gap * sr)), x.shape[1]))]
        last = s
        print(f"  {a.gap * 1000:.0f} ms of room after {w!r} at {at:.3f} s")
    out.append(x[last:])
    y = np.concatenate(out)
    sf.write(nar, y, sr, subtype=sf.info(str(nar.with_name("narration_preroom.wav"))).subtype)
    for wd in W:
        n = sum(1 for at, _ in cuts if wd["start"] >= at)
        if n:
            wd["start"] = round(wd["start"] + n * a.gap, 3)
            wd["end"] = round(wd["end"] + n * a.gap, 3)
    cap.write_text(json.dumps(H, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"-> {nar} (+{len(cuts) * a.gap:.2f} s; backups narration_preroom.wav, words_preroom.json)")


if __name__ == "__main__":
    main()
