"""Every cue of an export's .srt against the caption words it was made from, so subtitles never drift behind the voice after cuts that
moved the words but not the cues. A cue counts as on time when its start is within 50 ms of the start of a word that matches its first
word (within 3 s). Run it on every .srt before it goes out.

  EDIT tools/voice/srt_check.py <export .srt> <build>/captions/words.json"""
import json
import re
import sys

srt, words = sys.argv[1], sys.argv[2]
W = json.load(open(words, encoding="utf-8"))["words"]
t = open(srt, encoding="utf-8").read()


def sec(s):
    h, m, r = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))


n = bad = 0
for b in re.split(r"\n\s*\n", t.strip()):
    L = b.splitlines()
    if len(L) < 3:
        continue
    m = re.match(r"(\S+) --> (\S+)", L[1])
    s = sec(m.group(1))
    first = L[2].split()[0]
    cand = [w for w in W if abs(w["start"] - s) < 3 and w["w"] == first]
    if not cand:
        continue
    n += 1
    off = min((s - w["start"] for w in cand), key=abs)
    if abs(off) > 0.05:
        bad += 1
        if bad <= 10:
            print(f"  {m.group(1)}  {off:+.3f} s  {L[2][:50]}")
print(f"{n} cues checked, {bad} off by more than 50 ms")
sys.exit(1 if bad else 0)
