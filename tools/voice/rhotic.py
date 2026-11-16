"""How American a voice take sounds, measured: rhoticity (a voice can come out British in some sections and in every re-take of one;
the creator's ear stays the judge, this only screens takes before they reach it).

American English says the r after a vowel ("four", "later", "internet"); a British (RP) voice drops it. The r colours the vowel by pulling
its third formant (F3) far down, so the measure is, at every written post-vocalic r of the take (located by the ElevenLabs character
timestamps), how far F3 dips below the take's own median F3 (Praat's Burg tracker, via parselmouth). Score = the median dip in Hz over all
such r's; American takes dip several hundred Hz, non-rhotic ones barely.

  cd tools && PIPE voice/rhotic.py <take.wav> ...                     (each take's .align.json next to it)
  cd tools && PIPE voice/rhotic.py --sections ../videos/<video>       (every cached voice section of the current narration)"""
import json
import re
import sys
from pathlib import Path

import numpy as np

VOWELS = set("aeiouy")


def r_spots(chars, st, en):
    """The written post-vocalic r's: [(word, t0, t1)], t0 = the vowel before the r, t1 = the r (or a silent final e after it)."""
    out, i, n = [], 0, len(chars)
    while i < n:
        if not chars[i].isalpha():
            i += 1
            continue
        j = i
        while j < n and (chars[j].isalpha() or chars[j] in "'’"):
            j += 1
        word = "".join(chars[i:j]).lower()
        for k, c in enumerate(word):
            if c != "r" or k == 0 or word[k - 1] not in VOWELS or (k + 1 < len(word) and word[k + 1] == "r") or (k and word[k - 1] == "r"):
                continue
            rest = word[k + 1:].replace("'", "").replace("’", "")
            # the r closes the syllable: the word ends, a consonant follows, or a final silent e ("were", "more", "fire", "are")
            if rest and rest[0] in VOWELS and not (rest == "e" or rest in ("es", "ed")):
                continue
            a = i + k - 1
            while a > i and word[a - i - 1] in VOWELS:  # the whole vowel spelling before the r ("four", "hear")
                a -= 1
            b = i + k + (1 if rest[:1] == "e" else 0)
            out.append((word, st[a], en[b]))
        i = j
    return out


def score(wav, align):
    import parselmouth
    snd = parselmouth.Sound(str(wav))
    fm = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=5000, window_length=0.025)
    pitch = snd.to_pitch(time_step=0.005)
    ts = np.arange(fm.xmin + 0.0125, fm.xmax - 0.0125, 0.005)
    f3 = np.array([fm.get_value_at_time(3, t) for t in ts])
    f0 = np.array([pitch.get_value_at_time(t) for t in ts])
    voiced = np.isfinite(f3) & np.isfinite(f0) & (f0 > 0)
    base = float(np.median(f3[voiced]))
    al = align.get("alignment", align)
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    dips = []
    for word, t0, t1 in r_spots(chars, st, en):
        m = voiced & (ts >= t0 - 0.03) & (ts <= t1 + 0.08)  # the character times run a little behind the sound
        if m.sum() < 3:
            continue
        dips.append((word, base - float(np.percentile(f3[m], 10))))
    d = np.array([x for _, x in dips]) if dips else np.zeros(1)
    return {"base_f3": round(base), "n": len(dips), "median_dip": round(float(np.median(d))), "share_over_400": round(float((d > 400).mean()), 2),
            "dips": [(w, round(x)) for w, x in dips]}


def main():
    a = sys.argv[1:]
    if a and a[0] == "--sections":
        here = Path(__file__).resolve().parent
        sys.path.insert(0, str(here.parent / "common"))
        sys.path.insert(0, str(here))
        sys.path.insert(0, str(here.parent))   # tools/: the dj package
        from section_takes import sections
        from dj.__main__ import video_config
        from dj.core import Ctx, load_config
        cfg = load_config(None, video_config(a[1]))
        ctx = Ctx(a[1], cfg)
        for k, (ids, _, w) in enumerate(sections(ctx, ctx.cfg["tts"]), 1):
            if not w.with_suffix(".align.json").exists():  # a line edited after the build (voice_patch): this section's take has the old
                # text's key; screen the patched line's own take instead (rhotic.py build/voice/patch/<beat>_1.wav)
                print(f"{k:2d} {ids[0]:>6}-{ids[-1]:<6} not screened: its text changed after the build (a voice_patch line)")
                continue
            r = score(w, json.loads(w.with_suffix(".align.json").read_text(encoding="utf-8")))
            print(f"{k:2d} {ids[0]:>6}-{ids[-1]:<6} n {r['n']:3d}  median dip {r['median_dip']:5d} Hz  over 400 Hz {r['share_over_400']:4.0%}  (F3 {r['base_f3']})")
        return
    for w in a:
        p = Path(w)
        aj = p.with_suffix(".align.json")
        r = score(p, json.loads(aj.read_text(encoding="utf-8")))
        print(f"{p.name:34s} n {r['n']:3d}  median dip {r['median_dip']:5d} Hz  over 400 Hz {r['share_over_400']:4.0%}  (F3 {r['base_f3']})")


if __name__ == "__main__":
    main()
