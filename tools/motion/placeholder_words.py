"""A placeholder words.json + beats.json for a prototype whose voice doesn't exist yet.

The composition anchors every shot with w(beat, phrase) on src/<folder>/words.json (sync_words.py writes the real one from the voice).
Before the voice exists, this writes the same two files from the script's beats at the house voice's measured pace, so the composition
renders now and every anchor is checked against the script's words; the real files replace these unchanged in format.

The pace model is fitted on a real narration of the house voice (2,108 words, 589.6 s):
  a word lasts 0.0274 s x its spoken letters + 0.124 s; the gap after a word ending "." "?" "!" is 0.245 s, after "," ";" ":" 0.22 s,
  inside a sentence 0.015 s, between beats 0.28 s (medians). Overall 3.58 words a second, as the real voice.
  (A different voice: refit these five numbers on one of its narrations.)
Digits count as their spoken letters ("6" = "six"). The words are the script's own tokens, punctuation kept (as the aligner writes them).

  EDIT tools/motion/placeholder_words.py <script.md> <first beat> <last beat> <out dir>
  e.g. ... videos/012-my-first-video/script.md S001 S013 tools/motion/src/v012
The beats.json it writes says "placeholder": true, so nothing mistakes it for the voice's timing."""
import json
import re
import sys
from pathlib import Path

PER_LETTER, BASE = 0.0274, 0.124
GAP = {"period": 0.245, "comma": 0.22, "none": 0.015, "beat": 0.28}
SPOKEN = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}


def letters(tok):
    s = "".join(SPOKEN.get(ch, ch) for ch in tok)
    return len(re.sub(r"[^A-Za-z]", "", s)) or 1


def beats_of(script, first, last):
    rows = re.findall(r"^\[(S\d+[a-z]?)\] VOICE: (.+)$", script, re.M)
    ids = [b for b, _ in rows]
    if first not in ids or last not in ids:
        raise SystemExit(f"beats {first}..{last} not both in the script")
    i, j = ids.index(first), ids.index(last)
    return rows[i:j + 1]


def build(rows):
    words, beats, t = [], [], 0.005
    for k, (beat, text) in enumerate(rows):
        b0 = t if k else 0.0
        toks = text.split()
        for n, tok in enumerate(toks):
            d = PER_LETTER * letters(tok) + BASE
            words.append({"w": tok, "start": round(t, 3), "end": round(t + d, 3), "beat": beat})
            t += d
            if n + 1 < len(toks):
                t += GAP["period"] if tok[-1] in ".?!" else GAP["comma"] if tok[-1] in ",;:" else GAP["none"]
        voice_end = t
        t += GAP["beat"]
        beats.append({"id": beat, "start": round(b0, 4), "voice_end": round(voice_end, 4), "end": round(t if k + 1 < len(rows) else voice_end + 0.4, 4)})
    return words, beats


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    script, first, last, out = sys.argv[1:]
    rows = beats_of(Path(script).read_text(encoding="utf-8"), first, last)
    words, beats = build(rows)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "words.json").write_text(json.dumps(words, indent=1) + "\n", encoding="utf-8")
    meta = {"duration": beats[-1]["end"], "narration": None, "placeholder": True,
            "note": f"placeholder_words.py from {Path(script).name} {first}-{last} at the house voice's measured pace; the voice's own words.json replaces it",
            "beats": beats}
    (out / "beats.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"{len(words)} words, {len(beats)} beats, {beats[-1]['end']:.2f} s -> {out}")
    for b in beats:
        print(f"  {b['id']}  {b['start']:7.2f} - {b['voice_end']:7.2f}")


if __name__ == "__main__":
    main()
