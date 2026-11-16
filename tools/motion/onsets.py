"""Measured word onsets from a video's captions_fix.json, applied to the heard words (build/captions/words.json) before they are used.
Whisper's word starts can be 150 ms off on a stop consonant ("dropped", "banks") or a beat's first word; an entry
{"beat": "S02", "w": "banks,", "start": 8.335, "why": "..."} (the heard spelling, `nth` from 0 when it repeats) moves that word's start
to the onset measured on narration.wav (20-ms RMS), and the previous word's end with it. Used by finish_short.py (the captions) and
sync_words.py (the picture's cues), so both follow the same sound."""
import json
from pathlib import Path


def apply_onsets(words, fix_file):
    fix_file = Path(fix_file)
    if not fix_file.exists():
        return words
    for fx in json.loads(fix_file.read_text(encoding="utf-8")):
        if "start" not in fx:
            continue
        hits = [i for i, x in enumerate(words) if x["beat"] == fx["beat"] and x["w"] == fx["w"]]
        nth = fx.get("nth", 0)
        if nth >= len(hits):
            print(f"  ! onset fix not applied (no {fx['w']!r} #{nth} in {fx['beat']}): check {fix_file.name}")
            continue
        i = hits[nth]
        old = words[i]["start"]
        words[i] = dict(words[i], start=fx["start"])
        # the previous word ends where this one now starts (earlier: cut short; later: it held the gap Whisper gave this word)
        if i and words[i - 1]["beat"] == fx["beat"] and (words[i - 1]["end"] > fx["start"] or words[i - 1]["end"] >= old - 0.01):
            words[i - 1] = dict(words[i - 1], end=fx["start"])
        print(f"  onset fix: {fx['w']} {old} -> {fx['start']}")
    return words
