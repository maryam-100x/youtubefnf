"""A2 of the sound gate: clicks the clean-up's mutes leave (a mute that starts on a word's sound, or a lone burst left between a mute and
the next word, is heard as a click):

  1. CHOP: a mute (digital silence over 40 ms) that starts within 0.22 s after a word's end while the sound is still above -42 dB
     (the last 10 ms): the word steps into silence (its release still open, the mute took the rest);
  2. SCRAP: a lone burst right after 30 ms or more of digital silence, over -55 dB for 1-12 frames of 5 ms (60 ms at most), its
     loudest frame over -32 dB, then quiet (under -45 dB for 25 ms): a breath or word fragment left between a mute and the next word.
     The bar is -55: at -45, a 30-ms click whose first 5-ms frame ends at -48 dB is missed.
With the raw takes (narration_prechain.wav, lined up as in tails.py) each finding is checked against the take, so a word's own sound
is never called a click (a stop's release that tails --fix laid back after a mute would otherwise read as a scrap):
  - a CHOP counts only where the take still sounds when the mute starts (3 or more 5-ms frames over -45 dB in the next 25 ms): the
    mute cut something; where the take dies too, the mute only follows the word's own end;
  - a SCRAP is the word's own release (not counted) when it is the take's own sound (correlation 0.8 or more) and a lone burst in the
    take too (the take under -45 dB for 10 ms before it and 20 ms after it); a scrap cut from a longer sound (the start of a word, the
    rest muted) still counts.
Without the raw file every finding counts. 0 scraps is the bar. CHOPs are listed, not counted here: whether a mute cut a word's sound
is A1's call (tails.py holds every word end against the take, release against breath), and a laid-back release ending in its fade
into a mute reads as a CHOP by level alone.

  EDIT tools/sound/mutescan.py <video> [--final F --raw R --words W] [--json out]"""
import argparse
import bisect
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

SCRAP_BAR = -55.0     # a scrap runs while over this (5-ms frames)
SCRAP_MAX = 12        # frames: 60 ms at most
SCRAP_PEAK = -32.0
CHOP_BAR = -42.0      # the last 10 ms before a mute


def mute_starts(x, sr, min_s=0.04):
    """first sample of every run of digital silence longer than min_s (checked every 1 ms)"""
    z = np.abs(x) < 1e-6
    step = max(1, sr // 1000)
    zs = z[::step]
    out, s = [], None
    for i, v in enumerate(zs):
        if v and s is None:
            s = i
        if not v and s is not None:
            if (i - s) * step > sr * min_s:
                k = s * step
                while k > 0 and z[k - 1]:       # back to the exact first silent sample
                    k -= 1
                out.append(k)
            s = None
    return out


def find(x, sr, W, al=None, chop_bar=CHOP_BAR):
    """-> (chops, scraps, exempt): dicts with sample positions; `exempt` = findings the take shows are the word's own sound"""
    ends = sorted((w["end"], w["w"]) for w in W)
    E = [e for e, _ in ends]
    chops, scraps, exempt = [], [], []
    for r0 in mute_starts(x, sr):
        t0 = r0 / sr
        k = bisect.bisect_right(E, t0) - 1
        if k < 0 or t0 - E[k] >= 0.22:
            continue
        lv = G.db(x[max(0, r0 - int(0.01 * sr)):r0])
        if lv <= chop_bar:
            continue
        item = {"s": r0, "t": t0, "word": ends[k][1], "word_end": E[k], "loud": lv}
        if al is not None:
            m = al.raw_at(r0, near=r0 - int(0.02 * sr))
            if m is not None:
                pr, g = m
                nxt = G.frame_db(al.pm[pr:pr + int(0.025 * sr)], sr, 0.005) + g
                item["take_after"] = float(nxt.max()) if len(nxt) else -120.0
                if (nxt > -45).sum() < 3:
                    item["why"] = f"the take dies there too (next 25 ms: {item['take_after']:.1f} dB at most)"
                    exempt.append(dict(item, kind="chop"))
                    continue
        chops.append(item)
    h = int(0.005 * sr)
    lv5 = G.frame_db(x, sr, 0.005)
    n = len(lv5)
    i = 0
    while i < n - 20:
        if lv5[i] < -80:
            j = i
            while j < n and lv5[j] < -80:
                j += 1
            if j - i >= 6:
                k = j
                while k < n and k < j + SCRAP_MAX + 2 and lv5[k] > SCRAP_BAR:
                    k += 1
                if 1 <= k - j <= SCRAP_MAX and lv5[j:k].max() > SCRAP_PEAK and (lv5[k:k + 5] < -45).all():
                    a, b = j * h, k * h
                    kk = bisect.bisect_right(E, a / sr + 0.3) - 1
                    item = {"s": a, "e": b, "t": a / sr, "ms": (k - j) * 5, "loud": float(lv5[j:k].max()),
                            "word": ends[kk][1] if kk >= 0 else "", "word_end": E[kk] if kk >= 0 else 0.0}
                    own = False
                    if al is not None:
                        m = al.raw_at(a, near=a - int(0.15 * sr))
                        if m is not None:
                            pr, g = m
                            c = float(np.dot(x[a:b], al.pm[pr:pr + (b - a)]) /
                                      (np.linalg.norm(x[a:b]) * np.linalg.norm(al.pm[pr:pr + (b - a)]) + 1e-12))
                            before = G.db(al.pm[max(0, pr - int(0.01 * sr)):pr]) + g
                            after = G.frame_db(al.pm[pr + (b - a):pr + (b - a) + int(0.02 * sr)], sr, 0.005) + g
                            item.update(take_corr=round(c, 2), take_before=round(before, 1),
                                        take_after=round(float(after.max()) if len(after) else -120.0, 1))
                            # the take's own lone burst: the same sound, quiet before it, and after it only its own decay (10 dB
                            # or more under its peak) dying under -45 dB within 20 ms
                            own = (c >= 0.8 and before < -45 and len(after) > 0 and float(after.max()) <= item["loud"] - 10
                                   and float(after[-1]) < -45)
                    if own:
                        item["why"] = (f"the take's own lone burst (corr {item['take_corr']}, take {item['take_before']} dB before, "
                                       f"{item['take_after']} dB at most after, dying): the word's own release, laid back")
                        exempt.append(dict(item, kind="scrap"))
                    else:
                        scraps.append(item)
            i = j
        else:
            i += 1
    return chops, scraps, exempt


def run(P, al=None, quiet=False, use_raw=True):
    if al is None and use_raw and Path(P["raw"]).exists():
        from tails import Align
        al = Align(P["final"], P["raw"], P["words"])
    if al is not None:
        x, sr, W = al.fm, al.sr, al.W
    else:
        x, sr = G.load_mono(P["final"])
        W = G.load_words(P["words"])
    chops, scraps, exempt = find(x, sr, W, al)
    flags = []
    for s in scraps:
        flags.append(G.flag("A2", f"scrap@{s['t']:.3f}", s["t"], s["word"],
                            f"scrap after a mute: {s['ms']} ms, loudest {s['loud']:.1f} dB"
                            + (f" (take corr {s['take_corr']}, take after {s['take_after']} dB: a fragment of a longer sound)"
                               if "take_corr" in s else "")))
    flags.sort(key=lambda f: f["t"])
    chop_rows = [{k: v for k, v in c.items() if k != "s"} for c in chops]
    res = {"check": "A2", "final": str(P["final"]), "raw": str(P["raw"]) if al is not None else None,
           "mutes": len(mute_starts(x, sr)), "flags": flags, "chops": chop_rows,
           "exempt": [{k: v for k, v in e.items() if k not in ("s", "e")} for e in exempt]}
    if not quiet:
        print(f"A2 clicks: {res['mutes']} mutes; {len(scraps)} scraps after a mute ({sum(1 for e in exempt if e['kind'] == 'scrap')} "
              f"left as the word's own release); {len(chops)} mutes start on a word's sound (reported here, counted by A1)")
        G.print_flags(res)
        for c in chop_rows:
            print(f"  chop (A1 decides): {G.fmt_t(c['t'])} ({c['t']:.3f} s) {c['word']!r}: mute {c['t'] - c['word_end']:.2f} s after the word, "
                  f"{c['loud']:.1f} dB in its last 10 ms" + (f", the take at {c['take_after']:.1f} dB" if "take_after" in c else ""))
        for e in res["exempt"]:
            print(f"  left: {e['kind']} {G.fmt_t(e['t'])} ({e['t']:.3f} s) {e['word']!r}: {e['why']}")
    return res


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--no-raw", action="store_true", help="don't check findings against the take (every finding counts)")
    a = ap.parse_args()
    res = run(G.paths_from(a), use_raw=not a.no_raw)
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
