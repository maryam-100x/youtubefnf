"""A mute inside a word: a chain step silenced frames that belong to a word (e.g. the t of "eigh-teen" taken for a hiss between two
words), so the listener hears the word cut off in the middle; A1 (tails) reads word ENDS only, A2 the mutes' edges, so neither sees it.

Every word of the final voice (captions/words.json) is lined up with the raw take by tails.py's Align (the word's own match); inside the
word's span (from 30 ms before its start to 20 ms after its end) any run of 15 ms or more where the take sounds (over -38 dB) and the final
is digital silence (under -70 dB) is a mute inside the word. Printed with the word, its time and the run; --json for the gate.

  EDIT tools/sound/inword.py <video> [--json out.json]"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402
from tails import Align  # noqa: E402

H = 0.005


def scan(al):
    sr, h = al.sr, int(H * al.sr)
    out = []
    for w in al.W:
        L = al.locate(w, record=False)
        if not L:
            continue
        A, pa, g, sc = L
        if sc < 0.8:
            continue
        a0 = int((w["start"] - 0.03) * sr)
        a1 = int((w["end"] + 0.02) * sr)
        if a0 < 0 or a1 <= a0:
            continue
        off = pa - A
        lf = al.lv(al.fm[a0:a1])
        lp = al.lv(al.pm[a0 + off:a1 + off]) + g
        n = min(len(lf), len(lp))
        bad = (lp[:n] > -38) & (lf[:n] < -70)
        run = best = 0
        k_best = 0
        for k, b in enumerate(bad):
            run = run + 1 if b else 0
            if run > best:
                best, k_best = run, k
        # a cut INSIDE the word has the take's voice on both sides of it within 40 ms ("eigh|t|een"); a run with quiet before it is a
        # breath muted in the pause that the captions counted into the next word's start (every such hit read by frames was one)
        k0 = k_best - best + 1
        if best * H >= 0.015 and np.max(lp[max(0, k0 - 8):k0], initial=-99) > -30 and np.max(lp[k_best + 1:k_best + 9], initial=-99) > -30:
            t1 = (a0 + (k_best + 1) * h) / sr
            out.append({"t": round(t1 - best * H, 3), "ms": int(best * H * 1000), "word": w["w"], "start": w["start"], "end": w["end"],
                        "take_db": round(float(np.max(lp[k_best - best + 1:k_best + 1])), 1)})
    return out


def main():
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--json")
    a = ap.parse_args()
    P = G.paths(a.video)
    al = Align(P["final"], P["raw"], P["words"])
    hits = scan(al)
    for x in hits:
        print(f"MUTED INSIDE '{x['word']}' {G.fmt_t(x['start'])} ({x['start']:.2f}-{x['end']:.2f} s): {x['ms']} ms of digital silence from "
              f"{x['t']:.3f} s where the take sounds at up to {x['take_db']} dB")
    print(f"{len(hits)} word(s) with a mute inside ({len(al.W)} words read)")
    if a.json:
        Path(a.json).write_text(json.dumps(hits, indent=1), encoding="utf-8")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
