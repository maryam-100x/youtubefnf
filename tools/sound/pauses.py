"""A3 of the sound gate: pauses, measured on the audio, not on Whisper's word times (an over-long pause or an inhale left in it is
heard at once, and Whisper's word edges are off by tens of ms). Two flags:
  LONG    the pause (from the end of the word's last sound, frames over -38 dB, to where speech is back: 3 20-ms frames over -30 dB
          near the next word's start) over 0.20 s between two words of one sentence, commas included (inside a sentence the chain
          makes 0.12 s, so anything over 0.20 s is a pause the chain missed); after a sentence's end inside a beat over 0.30 s;
          between beats over 0.30 s too (holds and bites, over 3 s, are skipped);
  BREATH  a breath left inside a pause: 50 ms or more over -45 dB (one-frame dips joined, 10-ms frames), centred 1.5-3.5 kHz and
          under -25 dB (higher is a fricative, louder is speech), inside the pause = after the word's own sound (its decay until it
          falls under -45 dB, and at least its spelling's guard: an s/f/sh/th/x/z ending 0.24 s, a stop 0.20 s, a voiced end 0.12 s
          after its end) and before the next word's onset ramp. Inhales between words typically hold -32..-45 dB for 70-380 ms,
          centred 2.0-3.0 kHz. Shorter blips (a scrap after a mute, a glottal onset: 30-40 ms) are A2's or the next word's;
          low-centred (under 1.5 kHz) voiced sound is speech, Whisper's words' business (A5).
Pauses under 0.10 s are a word's closure, not a pause, and aren't read. Every flag carries the words either side and the time.

  EDIT tools/sound/pauses.py <video> [--final F --words W] [--json out]
      [--after "the city" "at night" ...]   (just the pauses after these words, with their breaths)"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

HOP = 0.02         # the onset measure's frame length
TAIL = -38.0
ONSET = -30.0
FINE = 0.01        # the inside of a pause, in 10-ms frames
BREATH = -45.0
BREATH_MIN = 0.05  # s over -45 dB
BREATH_HZ = 1500.0
LONG_IN = 0.20     # the chain makes pauses inside a sentence 0.12 s; a release or a short sound left in the pause measures up to
                   # 0.19 s after it, so 0.20 s is the bar
LONG_END = 0.30
MIN_PAUSE = 0.10


def guard(word):
    """how long after its end a word's own sound may run (breath_cut.py's tail guards)"""
    w = word.lower().strip('.,!?;:"\'”“)(')
    if not w:
        return 0.12
    if w[-1].isdigit() or w.endswith(("s", "sh", "ch", "f", "th", "x", "z", "ce", "se", "ve", "v", "fe")):
        return 0.24
    if w.endswith("ng"):
        return 0.12
    if w.endswith(("t", "k", "p", "d", "g", "b", "ct", "ght")):
        return 0.20
    return 0.12


class Voice:
    def __init__(self, wav=None, x=None, sr=None):
        """a wav path, or mono samples and their rate (close_gaps.py measures the audio it is cutting)"""
        self.x, self.sr = G.load_mono(wav) if wav is not None else (x, sr)
        self.lv = G.frame_db(self.x, self.sr, HOP)
        self.lf = G.frame_db(self.x, self.sr, FINE)
        q = int(FINE * self.sr)
        n = len(self.x) // q
        fr = self.x[:n * q].reshape(n, q) * np.hanning(q)
        S = np.abs(np.fft.rfft(fr, axis=1)) + 1e-12
        f = np.fft.rfftfreq(q, 1 / self.sr)
        self.cen = (S * f).sum(1) / S.sum(1)

    def breathlike(self, i, e, apart=False):
        """a stretch of 10-ms frames that sounds like a breath, not a word: centred 1.5-3.5 kHz (inhales sit at 2.0-3.0 kHz) and never
        louder than -28 dB (an s or a vowel is louder, or centred higher or lower). apart: the stretch stands off the word by 40 ms of quiet
        (under -50 dB), so no word's own sound runs into it; then up to -22 dB (a louder inhale that sits in quiet after the word would
        otherwise count as the word's tail and hide the pause it sits in)"""
        c = float(np.median(self.cen[i:e]))
        return BREATH_HZ <= c <= 3500 and float(self.lf[i:e].max()) < (-22 if apart else -28)

    def measure(self, a, b):
        """the pause between words a and b: dict(length, j (s), i0, i1 (the inside, 10-ms frames), breaths) or None if they run together.
        Onset: where speech is back near b's start (3 20-ms frames over -30 dB; a louder breath earlier doesn't end the pause). a's end:
        the end of its last sound, 10-ms frames over -38 dB in a run of 50 ms or more (or touching the word), not breath-like, not b's
        onset (Whisper can end a word before its last syllable; a closure dip inside a word is not a pause; a 30-ms scrap after a mute
        is no word's end). The pause = onset - a's end (the 20-ms onset measure, made word-aware)."""
        lv, lf = self.lv, self.lf
        n = len(lv)
        k = int((b["start"] - 0.12) / HOP)
        kmax = min(n - 3, int((b["start"] + 0.25) / HOP))
        while k < kmax and not (lv[k:k + 3] > ONSET).all():
            k += 1
        r = int(round(HOP / FINE))
        kf = k * r if k < kmax else int(b["start"] / FINE)      # no clear onset: Whisper's start
        kf = min(kf, len(lf) - 1)   # a word timed at or past the narration's end (run() flags it): never read past the audio
        # an inhale louder than the onset bar is not the word (an inhale at -28 dB, 2-3 kHz, before the word can read as its onset, so
        # the pause measures short with no breath in it): when a quiet frame (under -45 dB) lies between that "onset" and the word's first
        # speech frame (over -25 dB), the onset is the start of the speech's own run
        f1 = next((f for f in range(kf, min(len(lf), kf + int(0.40 / FINE))) if lf[f] > -25), None)
        if f1 is not None and (lf[kf:f1] < BREATH).any():
            while f1 > kf and lf[f1 - 1] >= BREATH:
                f1 -= 1
            kf = f1
        # a stop's release is the word's own sound (A1's STOP_END): a stop can release 30-80 ms after the word, a 30-40-ms burst over
        # -32 dB, which must not be measured as pause
        ws = a["w"].lower().strip('.,!?;:"\'”“)(')
        stop = ws.endswith(("t", "d", "k", "p", "g", "b", "c", "que", "ed", "pe", "ke", "te", "de", "be", "ge"))   # silent e: "tape"
        i, last_end = int(a["start"] / FINE), None
        while i < kf:
            if lf[i] > TAIL:
                e = i
                while e < kf and lf[e] > TAIL:
                    e += 1
                if e >= kf - 1:
                    if i * FINE <= a["end"] + 0.03:      # a's sound runs straight into b: no pause
                        return None
                    # b's onset: when it is speech (a vowel louder than a breath, not breath-like) the pause ends where it starts, not at
                    # the 3-frame onset found from Whisper's start (Whisper can time a word late, so its first syllable sits before the
                    # search began and a short gap would measure long)
                    if float(lf[i:e].max()) > -25 and not self.breathlike(i, e):
                        kf = i
                    break
                # a stop's release right after its closure (100 ms of quiet or less after the word's sound, 100 ms long at most, over -36
                # dB) is the word's own, wherever Whisper ends the word: releases 50-70 ms after the vowel, 60-80-ms bursts at
                # 1.5-3.5 kHz, read as breaths once the guard ended at the closure; an inhale runs 150 ms or more
                release = stop and last_end is not None and (i - last_end) * FINE <= 0.10 and (e - i) * FINE <= 0.10 \
                    and float(lf[i:e].max()) > -36
                own = release or (e - i) * FINE >= 0.05 or i * FINE <= a["end"] + 0.02 or (
                    stop and i * FINE <= a["end"] + 0.12 and float(lf[i:e].max()) > -32)
                apart = i >= 4 and float(lf[i - 4:i].max()) < -50 and i * FINE > a["end"] + 0.03
                if own and (release or not ((e - i) >= 3 and self.breathlike(i, e, apart) and i * FINE > a["end"])):
                    last_end = e
                i = e
            else:
                i += 1
        if last_end is None:
            last_end = int(a["end"] / FINE)
        length = (kf - last_end) * FINE
        if length <= 0:
            return None
        i1 = kf
        while i1 - 1 > last_end and lf[i1 - 1] > -55 and lf[i1 - 1] < lf[i1:i1 + 3].max() - 1:   # back over b's rising onset
            i1 -= 1
        i0 = last_end
        # a's own decay, to its first frame under the breath bar (an inhale right after the word never falls to -50 dB, so a walk to
        # -50 dB would run over it as the word's fade and start the breath search at the next word)
        while i0 < i1 - 1 and not lf[i0] < BREATH:
            i0 += 1
        # the spelling guard (an s may hiss 0.24 s) ends at the first 20 ms of quiet after the word's last sound: a hiss can't run on past
        # a real gap, so an inhale right after the word is never hidden inside the guard
        g = int((a["end"] + guard(a["w"])) / FINE)
        q = next((k for k in range(last_end, min(g, i1) - 1) if lf[k] < -45 and lf[k + 1] < -45), g)
        i0 = min(max(i0, min(g, q)), i1)
        runs, i = [], i0
        while i < i1:
            if lf[i] > BREATH:
                e = i
                while e < i1 and (lf[e] > BREATH or (e + 1 < i1 and lf[e + 1] > BREATH)):
                    e += 1
                if (e - i) * FINE >= BREATH_MIN:
                    cen = float(np.median(self.cen[i:e]))
                    # a breath: centred 1.5-3.5 kHz and under -25 dB (higher is a fricative, the word's or the next one's: an F sits
                    # near 5.6 kHz; louder is speech: a vowel near -7 dB)
                    if BREATH_HZ <= cen <= 3500 and float(lf[i:e].max()) < -25:
                        runs.append({"t": i * FINE, "ms": int(round((e - i) * FINE * 1000)), "loud": round(float(lf[i:e].max()), 1),
                                     "hz": int(cen)})
                i = e
            else:
                i += 1
        return {"length": length, "j": last_end * FINE, "i0": i0, "i1": i1, "breaths": runs}


def run(P, after=None, quiet=False):
    V = Voice(P["final"])
    W = G.load_words(P["words"])
    norm = G.key
    if after:
        rows = []
        for name in after:
            toks = name.split()
            for i in range(len(W) - len(toks)):
                if all(norm(W[i + k]["w"]) == norm(t) for k, t in enumerate(toks)):
                    a, b = W[i + len(toks) - 1], W[i + len(toks)]
                    m = V.measure(a, b)
                    L = m["length"] if m else 0.0
                    br = m["breaths"] if m else []
                    rows.append({"after": name, "next": b["w"], "t": a["end"], "pause": round(L, 2), "breaths": br, "beat": a["beat"]})
                    if not quiet:
                        bt = "; ".join(f"BREATH {x['ms']} ms at {x['loud']} dB, {x['hz']} Hz" for x in br) or "clean"
                        print(f"  {name!r:22} -> {b['w']!r:12} pause {L:.2f} s{' LONG' if L > LONG_IN else '     '}  {bt}  "
                              f"({a['beat']}, {G.fmt_t(a['end'])}, {a['end']:.2f} s)")
        return {"check": "A3", "after": rows}
    flags = []
    dur = len(V.x) / V.sr
    for w in W:   # a word timed at or past the narration's end has no sound of its own there (cut, or the clock slipped)
        if w["start"] >= dur - 0.02:
            flags.append(G.flag("A3", G.wkey(w["w"], w["start"]), w["start"], w["w"],
                                f"timed at {w['start']:.2f} s, past the narration's end ({dur:.2f} s): the word has no sound there"))
    for a, b in zip(W, W[1:]):
        if b["start"] - a["end"] > 3.0:          # a hold or an insert gap, not a pause between words
            continue
        m = V.measure(a, b)
        if m is None or m["length"] < MIN_PAUSE:
            continue
        L = m["length"]
        ends = G.sentence_end(a["w"])
        what = f"{a['w']!r} -> {b['w']!r}"
        # between two lines too (a re-voiced line spliced in with its old gap plus its own lead-in makes a long pause between lines);
        # holds and bites (over 3 s) are skipped above
        if L > ((LONG_END if ends else LONG_IN) if a["beat"] == b["beat"] else LONG_END):
            flags.append(G.flag("A3", f"long:{G.wkey(a['w'], a['end'])}", a["end"], a["w"],
                                f"pause {L:.2f} s {'after a sentence end' if ends else 'inside a sentence'} ({what}; bar "
                                f"{LONG_END if ends else LONG_IN} s)", pause=round(L, 2)))
        for br in m["breaths"]:
            flags.append(G.flag("A3", f"breath:{G.wkey(a['w'], a['end'])}", br["t"], a["w"],
                                f"breath in the pause after it: {br['ms']} ms over -45 dB, loudest {br['loud']} dB, centred {br['hz']} Hz "
                                f"({what}; pause {L:.2f} s)", pause=round(L, 2), loudest=br["loud"]))
    flags.sort(key=lambda f: f["t"])
    res = {"check": "A3", "final": str(P["final"]), "flags": flags}
    if not quiet:
        nl = sum(1 for f in flags if f["key"].startswith("long:"))
        print(f"A3 pauses: {len(W)} words; {nl} pauses too long, {len(flags) - nl} breaths left in a pause")
        G.print_flags(res)
    return res


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--after", nargs="+", help="only the pauses after these words")
    a = ap.parse_args()
    res = run(G.paths_from(a), after=a.after)
    G.write_json(a.json, res)
    if not a.after:
        sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
