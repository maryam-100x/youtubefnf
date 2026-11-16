"""Close the pauses a breath pass left long: a breath cut out must take its gap with it. The 0.25-s pause cap (shorts_tighten.py)
measures gaps by Whisper's word edges, which take in parts of breaths; the breath passes after it (the safe breath mutes,
hiccup_breaths.py) silence those breaths and keep the timing, so a pause can end up 0.3-0.5 s. This pass reads the audio itself:
every stretch with no speech (10-ms RMS under --thr) longer than --gap is cut down to --gap, the cut in the middle of the stretch (its
quietest part), so each side keeps half the gap next to its word; 10-ms crossfade. The silence before the first word and the tail stay.
Then: `cd tools && PIPE -m dj captions ../videos/<video>` and `PIPE tools/motion/sync_words.py` for the new word times (every later
word moves).

--beats <build>/beats.json moves dj's beat slots with the cuts (as shorts_tighten.py does), so `dj captions` files each word under its
beat. A HOLD beat (silence on purpose: a clip plays there with its own sound) is never closed.
--words <build>/captions/words.json --words-out w2.json writes the words moved with the cuts.
--inside (pauses inside a sentence) is withdrawn: it lost words in its cuts; tools/sound/inner_gaps.py does that job before close_gaps.

  EDIT tools/sound/close_gaps.py <in.wav> <out.wav> [--gap 0.25] [--thr -42] [--beats b.json] [--shoulders]
      [--words w.json [--words-out w2.json]] [--report r.json]"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

HOP = 0.01


def word_slope(side, tol=2.0):
    """side: 10-ms levels running from a word toward the silence. True when they only fall (no rise over tol dB on the way): the
    word's own fade (or, read backwards, the next word's onset), not half of a breath, which rises again after the word's dip."""
    lo = side[0]
    for v in side[1:]:
        if v > lo + tol:
            return False
        lo = min(lo, v)
    return True


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--gap", type=float, default=0.25, help="the set pause in seconds (long form 0.25)")
    ap.add_argument("--thr", type=float, default=-42.0, help="no speech under this 10-ms RMS, dBFS")
    ap.add_argument("--report")
    ap.add_argument("--beats", help="dj's build/beats.json, shifted in place with the cuts")
    ap.add_argument("--words", help="words.json of this audio (dj captions): finds the pauses inside a sentence")
    ap.add_argument("--inside", type=float, help="withdrawn: inner_gaps.py sets the pause inside a sentence")
    ap.add_argument("--words-out", help="write the words moved with the cuts here")
    ap.add_argument("--shoulders", action="store_true", help="first mute a breath the cap split in two: both quiet sides of a cut "
                    "(digital silence) when each stays at -26 dB or under for 60-350 ms")
    a = ap.parse_args()
    if a.inside is not None:   # withdrawn: it lost words in its cuts (cause not found); the pause inside a sentence is inner_gaps.py's
        raise SystemExit("--inside is withdrawn (it lost words): use tools/sound/inner_gaps.py before close_gaps")
    x, sr = sf.read(a.src, dtype="float64", always_2d=True)
    mono = x.mean(1)
    h = int(HOP * sr)
    n = len(mono) // h
    lv = 20 * np.log10(np.sqrt((mono[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)
    if a.shoulders:   # a breath the pause cap cut through leaves its two halves around the cut ("hiccupped breaths")
        dead, muted, kept, i = lv < -70, 0, 0, 0
        g = np.ones(len(mono))
        while i < n:
            if dead[i]:
                j = i
                while j < n and dead[j]:
                    j += 1
                if j - i >= 3:
                    L = i - 1
                    while L >= 0 and -60 < lv[L] <= -26 and i - L <= 35:
                        L -= 1
                    R = j
                    while R < n and -60 < lv[R] <= -26 and R - j <= 35:
                        R += 1
                    # a split breath has a dip on each side (the word's fade, then the breath's own rise); a side whose level only
                    # falls from the word into the silence (or only rises from the silence into the next word) is the word's own
                    # fade or onset, never muted (a word's -26..-47 dB fade taken for a breath half cuts the word off)
                    if (i - 1 - L >= 6 and R - j >= 6 and not word_slope(lv[L + 1:i]) and not word_slope(lv[j:R][::-1])):
                        g[(L + 1) * h:R * h] = 0
                        muted += 1
                    elif i - 1 - L >= 6 and R - j >= 6:
                        kept += 1
                i = j
            else:
                i += 1
        f = int(0.008 * sr)
        k = np.ones(f) / f
        g = np.convolve(g, k, mode="same")   # 8-ms ramps at each edge
        x = x * g[:, None]
        mono = x.mean(1)
        lv = 20 * np.log10(np.sqrt((mono[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)
        print(f"{muted} split breath(s) muted on both sides of their cut; {kept} kept (a side was a word's own fade or onset)")
    quiet = lv < a.thr
    runs, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    W = []
    if a.words:
        W = json.load(open(a.words, encoding="utf-8"))
        W = sorted(W["words"] if isinstance(W, dict) else W, key=lambda w: w["start"])
    f = int(0.01 * sr)
    cuts, inner = [], []
    if a.inside is not None and W:   # pauses inside a sentence, measured as the gate's A3 does (withdrawn: refused above)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import pauses
        V = pauses.Voice(x=mono, sr=sr)
        for p, q in zip(W, W[1:]):
            if q["start"] - p["end"] > 3.0 or p.get("beat") != q.get("beat") or re.search(r"[.!?][\"”')]*$", p["w"].strip()):
                continue
            m = V.measure(p, q)
            if not m:
                continue
            inner.append((p["end"] - 0.05, q["start"] + 0.05))
            if m["length"] <= a.inside + 0.03:
                continue
            # the cut: the middle of the longest run of quiet frames (under -45 dB, or a breath: 50 ms+ under -28 dB centred 1.5-3.5 kHz)
            # from 30 ms after the word's last sound to 20 ms before the next word's onset ramp; the word's own fade stays
            lo, hi = int(round(m["j"] / pauses.FINE)) + 3, m["i1"] - 2
            bre = [V.lf[k] < -28 and V.lf[k] >= -45 and pauses.BREATH_HZ <= V.cen[k] <= 3500 for k in range(lo, hi)]
            breath = set()
            k = 0
            while k < len(bre):           # a breath lasts 50 ms or more: a stop's 20-ms release at 2.3 kHz is no breath ("it,")
                if bre[k]:
                    e = k
                    while e < len(bre) and bre[e]:
                        e += 1
                    if e - k >= 5:
                        breath.update(range(lo + k, lo + e))
                    k = e
                else:
                    k += 1
            cut_ok = lambda k: V.lf[k] < -45 or k in breath   # quiet, or a breath
            jf = int(round(m["j"] / pauses.FINE))
            last = max((k for k in range(lo, min(hi, jf + 15)) if not cut_ok(k)), default=None)   # a stop's release after its hold
            if last is not None:
                lo = last + 2              # never cut between a word and its own release (a t can come 110 ms after its hold)
            best, k = (0, 0), lo
            while k < hi:
                if cut_ok(k):
                    e = k
                    while e < hi and cut_ok(e):
                        e += 1
                    if e - k > best[1] - best[0]:
                        best = (k, e)
                    k = e
                else:
                    k += 1
            d = min(m["length"] - a.inside, (best[1] - best[0]) * pauses.FINE - 0.02)
            if d < 0.03:
                continue
            mid = (best[0] + best[1]) / 2 * pauses.FINE
            c0, c1 = int((mid - d / 2) * sr) + f // 2, int((mid + d / 2) * sr) - f // 2   # the crossfade takes f more
            cuts.append((c0, c1, round(m["j"], 3), round(m["length"], 3), a.inside))
    n_in = len(cuts)

    # a HOLD beat (`[S12h] HOLD: 9.0`: silence on purpose, a clip plays there with its own sound) is never closed, as shorts_tighten.py
    # spares it: closing it would run the next line over the clip's own sound
    holds = []
    if a.beats:
        bb = json.load(open(a.beats, encoding="utf-8"))["beats"]
        holds = [(b["start"], bb[i + 1]["start"] if i + 1 < len(bb) else len(mono) / sr) for i, b in enumerate(bb)
                 if b.get("hold") or not (b.get("voice") or "").strip()]
    edge = int(0.3 / HOP)
    for i, j in runs:
        if i < edge or j > n - edge:
            continue   # the silence before the first word, and the tail
        if any(i * HOP < h1 and j * HOP > h0 for h0, h1 in holds):
            continue   # a HOLD's silence, and the pauses joined to it
        dur = (j - i) * HOP
        tgt = a.gap
        if any(s0 <= (i + j) / 2 * HOP <= s1 for s0, s1 in inner):
            continue   # inside a sentence: the pass above
        if dur <= tgt + 0.02:
            continue
        keep = tgt / 2
        c0, c1 = int((i * HOP + keep) * sr), int((j * HOP - keep) * sr)
        if c1 - c0 > int(0.02 * sr):
            cuts.append((c0, c1, round(i * HOP, 3), round(dur, 3), tgt))
    # never two cuts over one stretch: cuts are applied from the end, so an earlier cut reaching into a later one would remove the
    # speech after it
    kept, end = [], -1
    for c in sorted(cuts):
        if c[0] - f > end:
            kept.append(c)
            end = c[1] + f
    if len(kept) < len(cuts):
        print(f"{len(cuts) - len(kept)} overlapping cut(s) dropped")
    cuts = kept
    fade = np.linspace(1, 0, f)[:, None]
    y = x
    for c0, c1, *_ in sorted(cuts, reverse=True):   # from the end, so earlier indices hold
        joined = y[c0 - f:c0] * fade + y[c1:c1 + f] * (1 - fade)
        y = np.vstack([y[:c0 - f], joined, y[c1 + f:]])
    sf.write(a.out, y, sr, subtype="PCM_16")
    spans = sorted((c0 - f, c1 + f) for c0, c1, *_ in cuts)

    def moved(t):   # each join replaces [c0 - f, c1 + f) with f samples: a time inside lands on the join, a later one moves back
        p, out = int(round(t * sr)), 0
        for s0, s1 in spans:
            if p >= s1:
                out += (s1 - s0) - f
            elif p > s0:
                out += p - s0
        return round((p - out) / sr, 4)
    if a.words_out and W:
        W2 = [dict(w, start=moved(w["start"]), end=moved(w["end"])) for w in W]
        json.dump({"mode": "whisper", "words": W2}, open(a.words_out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if a.beats:
        B = json.load(open(a.beats, encoding="utf-8"))
        num, den = (int(v) for v in str(B.get("fps", "60/1")).split("/")) if "/" in str(B.get("fps", "60")) else (int(B.get("fps", 60)), 1)
        fps = num / den
        for b in B["beats"]:
            for k in ("start", "voice_end", "end"):
                b[k] = moved(b[k])
        for i, b in enumerate(B["beats"]):
            b["start_f"] = round(b["start"] * fps)
            nxt = B["beats"][i + 1]["start"] if i + 1 < len(B["beats"]) else len(y) / sr
            b["frames"] = round(nxt * fps) - b["start_f"]
        B["duration"] = round(len(y) / sr, 4)
        B["total_frames"] = round(len(y) / sr * fps)
        json.dump(B, open(a.beats, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    removed = (len(x) - len(y)) / sr
    rows = [{"at": t, "was": d, "now": g} for _, _, t, d, g in cuts]
    if a.report:
        json.dump(rows, open(a.report, "w", encoding="utf-8"), indent=0)
    print(f"{len(cuts)} pause(s) closed ({n_in} inside a sentence to {a.inside} s, the rest to {a.gap} s), {removed:.2f} s out; "
          f"{len(x) / sr:.2f} -> {len(y) / sr:.2f} s -> {a.out}")
    for r in sorted(rows, key=lambda r: -r["was"])[:8]:
        print(f"   {int(r['at'] // 60)}:{r['at'] % 60:05.2f}  {r['was']:.2f} s")


if __name__ == "__main__":
    main()
