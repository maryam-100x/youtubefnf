"""Provisional word times from a script, so a composition can be built and type-checked before the voice exists (when the edit has
to start before the interview answers and the voice are in). Every beat's words get times at the house narration's measured pace
(3.24 words a second over a whole film, beat gaps ~0.58 s), each word's length by its letters. A ((Qn)) placeholder beat (an interview
answer still to come) gets a fixed length. The files carry "estimate": true; sync_words.py overwrites both from the real narration,
and every check after it runs again (standard/LONG_FORM.md).

  PIPE tools/motion/est_words.py <script.md> <out dir: src/<folder>> [--q 14]"""
import argparse
import json
import re
from pathlib import Path

GAP = 0.58          # between beats (a narrated film's median)
RATE = 3.55         # words a second inside a beat (3.24 overall, with the gaps taken out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--q", type=float, default=14.0, help="seconds for a ((Qn)) placeholder beat")
    a = ap.parse_args()
    text = Path(a.script).read_text(encoding="utf-8")
    beats = re.findall(r"^\[(S\d+[a-z]?)\] VOICE: (.+)$", text, flags=re.M)
    words, out_beats, t = [], [], 0.0
    for bid, line in beats:
        start = t
        toks = line.split()
        if line.strip().startswith("(("):
            dur = a.q
            per = [dur / max(1, len(toks))] * len(toks)
        else:
            weights = [0.35 + len(re.sub(r"[^A-Za-z0-9]", "", w)) for w in toks]
            dur = len(toks) / RATE
            per = [dur * x / sum(weights) for x in weights]
        for w, d in zip(toks, per):
            clean = re.sub(r"^[^\w']+|[^\w']+$", "", w)
            if clean:
                words.append({"w": clean, "start": round(t, 3), "end": round(t + d * 0.92, 3), "beat": bid})
            t += d
        out_beats.append({"id": bid, "start": round(start, 4), "voice_end": round(t, 4), "end": round(t + GAP, 4)})
        t += GAP
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "words.json").write_text(json.dumps(words, indent=1) + "\n", encoding="utf-8")
    (o / "beats.json").write_text(json.dumps({"duration": round(t, 3), "estimate": True, "beats": out_beats}, indent=1) + "\n", encoding="utf-8")
    print(f"{len(beats)} beats, {len(words)} words, {t / 60:.1f} min (estimate) -> {o}")


if __name__ == "__main__":
    main()
