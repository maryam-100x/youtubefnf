"""A7 of the sound gate: scraps of a word's head left before the word (a stutter like "wor-word"). They sit at a join of two takes: a
take that carried the head of the next line, spliced, leaves it in the pause before the same word of the narration. A1 to A6 pass them
(A2 reads only what follows a mute; A3 reads breaths, which are quiet and centred 1.5-3.5 kHz; a scrap is speech).

What a scrap measures like (10-ms frames, against every other short sound in a voice):
  - a short island of sound, 50-140 ms, bounded by quiet (under -50 dB) for 40 ms or more on both sides;
  - loud: its peak -9 to -18 dB (speech; a breath or a stop's release sits at -25 dB and under);
  - no word of Whisper's covers it (Whisper hears the word once, after it);
  - the next sound starts 50-100 ms after it (the word it is the head of); a natural release or exhale after a word sits 170 ms or more
    before the next word, or right on the word before;
  - it sounds like the start of that next sound: the log spectrum of its first 50 ms against the next sound's first 50 ms, cosine
    0.97-1.00 (a different sound, e.g. a word's release before an unrelated word, scores lower).
The rule flags such scraps and nothing in a clean voice. It also catches a word stalled by a gap (its start split from its end, heard
as a stall instead of a fluent run). The fix is the same: re-voice the line.

  EDIT tools/sound/scraps.py <video> [--final F --words W] [--json out] [-v]
      (-v: every short island with its numbers, flagged or not)"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

HOP = 0.01
QUIET = -50.0      # under it is quiet
JOIN = 3           # quiet gaps shorter than 30 ms are inside one sound
MIN_DUR, MAX_DUR = 0.03, 0.20
LOUD = -20.0       # the island's peak at least this (speech)
QUIET_BEFORE = 0.04
QUIET_AFTER = (0.04, 0.12)   # the next sound starts this soon after it
NEXT_MIN = 0.15    # and is a word, not another blip
AFTER_WORD = 0.08  # an island this close after the word before is that word's own end
SIMILAR = 0.90


def frames(x, sr):
    h = int(sr * HOP)
    n = len(x) // h
    fr = x[:n * h].reshape(n, h)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-12)
    sp = np.abs(np.fft.rfft(fr * np.hanning(h), axis=1))
    return db, sp


def sounds(db):
    """runs [i, j) of frames over QUIET, quiet gaps under JOIN frames joined"""
    snd = db >= QUIET
    runs, i, n = [], 0, len(db)
    while i < n:
        if not snd[i]:
            i += 1
            continue
        j = i
        while True:
            while j < n and snd[j]:
                j += 1
            k = j
            while k < n and not snd[k]:
                k += 1
            if k < n and k - j < JOIN:
                j = k
                continue
            break
        runs.append((i, j))
        i = j
    return runs


def shape(sp, a, b):
    s = sp[a:b].mean(0)
    bands = np.array_split(s[1:], 24)
    v = np.log(np.array([bb.mean() for bb in bands]) + 1e-9)
    return v - v.mean()


def cosine(u, v):
    return float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9))


def run(P, quiet=False, verbose=False):
    x, sr = G.load_mono(P["final"])
    W = G.load_words(P["words"])
    db, sp = frames(x, sr)
    R = sounds(db)
    flags = []
    for r in range(1, len(R) - 1):
        a, b = R[r]
        dur = (b - a) * HOP
        pk = float(db[a:b].max())
        qb = (a - R[r - 1][1]) * HOP
        qa = (R[r + 1][0] - b) * HOP
        na, nb = R[r + 1]
        if not (MIN_DUR <= dur <= MAX_DUR and qb >= QUIET_BEFORE and (nb - na) * HOP >= NEXT_MIN):
            continue
        t0, t1 = a * HOP, b * HOP
        cover = [w for w in W if w["start"] < t1 - 0.01 and w["end"] > t0 + 0.01]
        before = [w for w in W if w["end"] <= t0 + 0.05]
        nxt = [w for w in W if w["start"] >= t0 - 0.06]
        k = min(5, b - a)
        sim = cosine(shape(sp, a, a + k), shape(sp, na, na + k))
        gap_word = t0 - before[-1]["end"] if before else 9.0
        hit = (not cover and pk >= LOUD and QUIET_AFTER[0] <= qa <= QUIET_AFTER[1] and gap_word >= AFTER_WORD and sim >= SIMILAR)
        word = nxt[0]["w"] if nxt else "?"
        if verbose:
            print(f"  {t0:8.2f}-{t1:7.2f} {dur * 1000:4.0f} ms peak {pk:6.1f} quiet {qb:.2f}/{qa:.2f} after-word {gap_word:5.2f} "
                  f"like-next {sim:+.2f} cover={','.join(w['w'] for w in cover) or '-'} next {word!r}{'   <- SCRAP' if hit else ''}")
        if hit:
            flags.append(G.flag("A7", f"scrap:{G.wkey(word, t0)}", t0, word,
                                f"a scrap before {word!r}: {dur * 1000:.0f} ms at {pk:.0f} dB, quiet both sides, {qa * 1000:.0f} ms before "
                                f"the word and shaped like its start (similarity {sim:.2f}): a head left at a join (a 'wor-word' stutter) or a word stalled by a gap; "
                                f"re-voice the line (or mute a pure scrap and close the gap)", ms=round(dur * 1000), loud=round(pk, 1),
                                similar=round(sim, 2)))
    res = {"check": "A7", "final": str(P["final"]), "flags": flags}
    if not quiet:
        print(f"A7 scraps: {len(R)} sounds; {len(flags)} scraps")
        G.print_flags(res)
    return res


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    res = run(G.paths_from(a), verbose=a.v)
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
