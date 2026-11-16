"""Does a narration open tired or whispered, or swallow a word? A cloned voice can start a request with a tired, half-whispered
sentence, or drop a single word far under the rest. A screen, like rhotic.py and accent_id.py: the creator's ear is the judge, this
catches the faults before they are heard, and --fix lifts the quiet words (a vocal rider: gain only, no change to the voice itself).

Per word (the take's own word times), against the narration's medians over its content words:
  level           the word's body (80th percentile of 20-ms frames), dB
  voiced energy   the share of the word's energy in frames with a pitch: a whispered word has almost none
  CPPS            cepstral peak prominence, the standard measure of breathiness (lower = breathier)
Calibrated on a hand-marked narration: a word heard as swallowed sat 4.4 dB under the median; a whispered word read 0.00 voiced
energy; a tired opening sentence averaged CPPS 1.5 under the median, its pitch sinking to 87 Hz. The unmarked words stayed clear of all
three.

Flags (content words only; function words like "to", "it" are naturally reduced):
  LOUD       5+ dB over the median level (one word far over the rest peaks in the ear); --fix pulls it down to 1.5 dB over
  QUIET      4+ dB under the median level (7+ for a sentence's last word: a sentence falls at its end, and that is natural), on words of
             0.25 s or more (speech-to-text word times are too coarse for a shorter one)
  WHISPERED  under 0.25 voiced energy, 0.1 s or longer
  OPENING    the narration's first sentence, and the first sentence of each beat named in --starts (where a voice request starts cold),
             1.0+ under the median CPPS on average or 2+ dB under the median level (the tired, breathy start)

  EDIT tools/voice/voice_check.py <narration.wav> <words.json> [--starts S06 S14] [--all] [--fix out.wav]
      [--soften S18:spread S19:offices ...]
--fix never clips: the lifted words' peaks go under -1 dBFS by a look-ahead gain (a hard clip at full scale flat-tops a lifted word,
and it sounds bass-boosted and too loud on the mic). --soften: the named words' "s" sounds 6 dB softer (a high shelf from 4.5 kHz on
those words only, 20-ms ramps), for an "s" that peaks and hurts the ear; a de-esser on the whole narration costs too much quality.
words.json: [{"w", "start", "end", "beat"}]. Exits 1 when anything is flagged (after --fix, QUIET words count as fixed)."""
import argparse
import json
import re
import sys

import numpy as np
import parselmouth
import soundfile as sf
from parselmouth.praat import call

FUNCTION = {"a", "an", "the", "to", "of", "in", "on", "at", "it", "its", "it's", "is", "was", "and", "but", "or", "so", "he", "she", "they",
            "we", "you", "i", "him", "her", "his", "for", "with", "as", "by", "be", "been", "that", "this", "than", "then", "from", "up",
            "out", "me", "my", "our", "your", "their", "them", "are", "were", "has", "had", "have", "do", "did", "not", "no", "just",
            "he's", "you're", "we're", "i'm", "it's", "that's", "there", "what", "when", "how", "why", "who"}


def features(snd, pitch, w):
    a, b = w["start"], w["end"]
    x, sr = snd.values[0], snd.sampling_frequency
    seg = x[int(a * sr):int(b * sr)]
    n, hop = int(0.02 * sr), int(0.005 * sr)
    if len(seg) < n + hop:
        return None
    en, vo = [], []
    for k in range(0, len(seg) - n, hop):
        en.append(float(np.mean(seg[k:k + n] ** 2)))
        f0 = pitch.get_value_at_time(a + (k + n / 2) / sr)
        vo.append(f0 == f0 and f0 > 0)
    en, vo = np.array(en), np.array(vo)
    level = float(20 * np.log10(np.sqrt(np.percentile(en, 80)) + 1e-9))
    ves = float(en[vo].sum() / (en.sum() + 1e-12))
    try:
        pc = call(snd.extract_part(from_time=a, to_time=b), "To PowerCepstrogram", 60, 0.002, 5000, 50)
        cpps = float(call(pc, "Get CPPS", "yes", 0.02, 0.0005, 60, 330, 0.05, "Parabolic", 0.001, 0, "Straight", "Robust"))
    except Exception:
        cpps = float("nan")
    f0s = [pitch.get_value_at_time(t) for t in np.arange(a, b, 0.01)]
    f0s = [f for f in f0s if f == f and f > 0]
    return dict(level=level, ves=ves, cpps=cpps, f0=float(np.median(f0s)) if f0s else 0.0, dur=b - a)


def lookahead_limit(y, sr, ceil=0.891):
    """Peaks over -1 dBFS brought under it by a look-ahead gain (the lowest gain needed in a 9-ms window, smoothed): nothing flattened
    (the same method as the voice pipeline's own limiter in tools/dj)."""
    a = np.abs(y).max(axis=1)
    g = np.minimum(1.0, ceil / np.maximum(a, 1e-9))
    w = 2 * int(0.004 * sr) + 1
    p = w // 2
    g = np.lib.stride_tricks.sliding_window_view(np.pad(g, p, mode="edge"), w).min(axis=-1)
    c = np.cumsum(np.insert(np.pad(g, p, mode="edge"), 0, 0.0))
    return y * ((c[w:] - c[:-w]) / w)[:, None]


def high_shelf(y, sr, f0=4500.0, db=-6.0):
    """RBJ high shelf (S = 1), zero phase (filtfilt at half the gain each way), so it can be crossfaded with the original."""
    from scipy.signal import filtfilt
    A = 10 ** (db / 2 / 40)
    w0 = 2 * np.pi * f0 / sr
    al = np.sin(w0) / 2 * np.sqrt(2)
    cw, sa = np.cos(w0), 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa)]
    a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa]
    return filtfilt(np.array(b) / a[0], np.array(a) / a[0], y, axis=0)


def rider(path, out, lifts, soften=()):
    """Gain on each lifted (or pulled-down) word's span, 15-ms ramps in and out; the softened words crossfaded with a high-shelved copy;
    then the look-ahead limit, never a clip."""
    y, sr = sf.read(path, dtype="float64", always_2d=True)
    g = np.ones(len(y))
    r = int(0.015 * sr)
    for a, b, db in lifts:
        i0, i1 = max(0, int(a * sr) - r), min(len(y), int(b * sr) + r)
        env = np.full(i1 - i0, 10 ** (db / 20))
        ramp = np.linspace(1, 10 ** (db / 20), r)
        env[:r] = ramp[:len(env[:r])]
        env[-r:] = ramp[::-1][:len(env[-r:])]
        g[i0:i1] = np.maximum(g[i0:i1], env) if db > 0 else np.minimum(g[i0:i1], env)
    if soften:
        dark = high_shelf(y, sr)
        m = np.zeros(len(y))
        r2 = int(0.02 * sr)
        for a, b in soften:
            i0, i1 = max(0, int(a * sr) - r2), min(len(y), int(b * sr) + r2)
            env = np.ones(i1 - i0)
            env[:r2] = np.linspace(0, 1, r2)[:len(env[:r2])]
            env[-r2:] = np.linspace(1, 0, r2)[:len(env[-r2:])]
            m[i0:i1] = np.maximum(m[i0:i1], env)
        y = y * (1 - m[:, None]) + dark * m[:, None]
    y = y * g[:, None]
    if np.abs(y).max() > 0.891:
        y = lookahead_limit(y, sr)
    sf.write(out, y, sr, subtype="PCM_16")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("words")
    ap.add_argument("--all", action="store_true", help="print every word")
    ap.add_argument("--starts", nargs="*", default=[], help="beats where a voice request starts (the first beat always counts)")
    ap.add_argument("--fix", help="write the narration with each QUIET word lifted toward 1.5 dB under the median (at most +3 dB; a sentence's last word never), each LOUD one "
                    "pulled down to 1.5 dB over it (at most -6 dB)")
    ap.add_argument("--soften", nargs="*", default=[], help="BEAT:word ... the words whose 's' sounds hurt (with --fix)")
    a = ap.parse_args()
    snd = parselmouth.Sound(a.wav)
    pitch = snd.to_pitch_ac(time_step=0.005, pitch_floor=70, pitch_ceiling=400)
    rows = []
    for w in json.loads(open(a.words, encoding="utf-8").read()):
        f = features(snd, pitch, w)
        if f:
            key = re.sub(r"[^a-z0-9']", "", w["w"].lower())
            rows.append(dict(f, beat=w.get("beat", ""), w=w["w"], t=w["start"], end=w["end"], content=key not in FUNCTION))
    content = [r for r in rows if r["content"]]
    ml = float(np.median([r["level"] for r in content]))
    mc = float(np.nanmedian([r["cpps"] for r in content]))
    flags, lifts = [], []
    for r in rows:
        r["dl"], r["dc"] = r["level"] - ml, r["cpps"] - mc
        r["tags"] = []
        final = bool(re.search(r"[.!?]$", r["w"]))
        # under 0.25 s the word times are too coarse for a level: a short word can read -12 dB on the breath before the next word
        if r["content"] and r["dur"] >= 0.25 and r["dl"] <= (-7 if final else -4):
            r["tags"].append("QUIET")
            # at most +3 dB, and never a sentence's last word: a final word falls by nature, and a big lift sounds like the gain was
            # turned up and raises its breath and rumble with it
            if not final:
                lifts.append((r["t"], r["end"], min(3.0, -1.5 - r["dl"])))
        if r["content"] and r["dl"] >= 5.0:
            r["tags"].append("LOUD")
            lifts.append((r["t"], r["end"], max(-6.0, 1.5 - r["dl"])))
        if r["content"] and r["ves"] < 0.25 and r["dur"] >= 0.1:
            r["tags"].append("WHISPERED")
        if r["tags"]:
            flags.append(r)
    openings = []
    beats = {}
    for r in rows:
        beats.setdefault(r["beat"], []).append(r)
    order = list(beats)
    check = {order[0]} | set(a.starts) if order else set()
    for bt, rs in beats.items():
        if bt not in check:
            continue
        first = []
        for r in rs:
            first.append(r)
            if re.search(r"[.!?]$", r["w"]):
                break
        cs = [r["dc"] for r in first if r["content"] and r["dc"] == r["dc"]]
        ls = [r["dl"] for r in first if r["content"]]
        if len(cs) >= 2 and (np.mean(cs) <= -1.0 or np.mean(ls) <= -2.0):
            openings.append((bt, " ".join(r["w"] for r in first), float(np.mean(cs)), min((r["f0"] for r in first if r["f0"]), default=0)))
    print(f"{a.wav}: {len(rows)} words; content words: median level {ml:.1f} dB, median CPPS {mc:.2f}")
    for r in (rows if a.all else flags):
        print(f"  {r['beat']:<5} {r['t']:7.2f}  {r['w']:<18} level {r['dl']:+5.1f}  voiced {r['ves']:.2f}  CPPS {r['dc']:+5.2f}  F0 {r['f0']:4.0f}  "
              f"{' '.join(r['tags'])}")
    for bt, txt, dc, f0 in openings:
        print(f"  OPENING {bt}: \"{txt}\" CPPS {dc:+.2f} under the median on average, lowest pitch {f0:.0f} Hz (a tired, breathy start)")
    if a.fix:
        soft = []
        for sw in a.soften:
            bt, word = sw.split(":", 1)
            hits = [r for r in rows if r["beat"] == bt and word.lower() in r["w"].lower()]
            if not hits:
                raise SystemExit(f"--soften {sw}: no such word in {bt}")
            soft += [(r["t"], r["end"]) for r in hits]
        rider(a.wav, a.fix, lifts, soft)
        print(f"  --fix: {len(lifts)} word(s) lifted or pulled down, {len(soft)} softened -> {a.fix}")
    n = len([r for r in flags if not (a.fix and r["tags"] in (["QUIET"], ["LOUD"]))]) + len(openings)
    print(f"  {n} flag(s) left" if n else "  clean")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
