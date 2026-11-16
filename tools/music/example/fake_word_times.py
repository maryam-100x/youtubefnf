"""Make fake word times for example/script.txt (a made-up film), in the format a forced aligner or speech-to-text with word times
gives: [{"w", "start", "end", "beat"}], where "beat" is the section id.

    EDIT tools/music/example/fake_word_times.py tools/music/example/script.txt tools/music/example/words.json --pace 1.0 --seed 1
    EDIT tools/music/example/fake_word_times.py tools/music/example/script.txt tools/music/example/words_voice2.json --pace 1.12 --seed 2
                                                                                                   (a slower "second voice")

In a video the word times come from the narration itself: the voice step writes them (tools/motion/src/<src>/words.json).
"""
from __future__ import annotations

import argparse
import json
import random
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--pace", type=float, default=1.0, help="1.0 = about 2.6 words a second; 1.12 = 12% slower")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--lead-in", type=float, default=0.4)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    t = a.lead_in
    words = []
    for line in open(a.script, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        sec, text = line.split(" ", 1)
        if words:
            t += rnd.uniform(0.75, 1.05) * a.pace          # the breath between sections
        for tok in text.split():
            core = re.sub(r"[^\w']", "", tok)
            dur = (0.10 + 0.052 * len(core)) * a.pace * rnd.uniform(0.9, 1.1)
            words.append({"w": tok, "start": round(t, 3), "end": round(t + dur, 3), "beat": sec})
            t += dur + 0.035 * a.pace
            if tok.endswith((",", ":", ";")):
                t += rnd.uniform(0.18, 0.28) * a.pace
            elif tok.endswith((".", "?", "!")):
                t += rnd.uniform(0.38, 0.55) * a.pace
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=0)
    print(f"{len(words)} words, {words[-1]['end']:.2f} s -> {a.out}")


if __name__ == "__main__":
    main()
