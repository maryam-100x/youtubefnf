"""A8 of the sound gate: every stretch of the voice went through chain D (a re-take spliced in raw, only gained up to the section's
level, sounds like a different mic; dj tts sends the whole narration through tools/sound/voice_level.py --chain mb, a hand splice has
to do it itself).

The chain holds the vowel band back on its loud moments and limits at -1.5 dB, so a chained take's peaks sit closer to its loudness
(10-ms frames, the frames within 25 dB of the stretch's loudest; crest = the 99.9th percentile of the samples over their RMS): a
chained narration's beats sit at about 11.0 dB median (MAD 0.3; the highest 12.1), chained re-takes 11.1-11.7, the same takes raw
13.7-15.3. Gaining a raw take to the right level leaves its crest where it was, so the crest finds it at any level. Flags:
  RAW    a beat whose crest is 2 dB or more over the narration's median, or a 4-s window inside one 3 dB or more over it (a take
         that skipped chain D; a window reads fewer peaks, so its bar is higher: a clean chained beat can hold a 4-s window 2.7 dB over);
  LEVEL  a beat whose loudness is 4 dB or more off the median (a take spliced at another level);
  CLIP   samples at full scale: a raw take gained up to the narration's level runs over 0 dBFS and is clipped when written, which also
         lowers its crest, so clipping is its own flag.
A clean chained voice gives 0 flags; raw takes spliced in at the narration's level flag RAW (crest 14.8-15.3), and the same written
clipped as 24-bit flag RAW or CLIP.

  EDIT tools/sound/chainmatch.py <video> [--final F --beats B] [--json out] [-v]"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

HOP = 0.01
SPAN = 25.0        # frames within this of the loudest count as voice
CREST_OVER = 2.0   # dB over the median crest: raw
LEVEL_OFF = 4.0    # dB off the median loudness
WIN, STEP = 4.0, 1.0
WIN_OVER = 3.0     # dB over the median crest for a 4-s window
FULL = 0.999       # a sample at or over this is clipped


def measure(x, sr):
    h = int(sr * HOP)
    n = len(x) // h
    if n < 20:
        return None
    fr = x[:n * h].reshape(n, h)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-12)
    v = db > db.max() - SPAN
    vs = fr[v]
    rms = np.sqrt((vs ** 2).mean())
    return {"crest": float(20 * np.log10(np.percentile(np.abs(vs), 99.9) / rms)), "level": float(20 * np.log10(rms))}


def load_beats(path):
    B = json.loads(Path(path).read_text(encoding="utf-8"))
    B = B.get("beats", B) if isinstance(B, dict) else B
    out = []
    for b in B:
        s, e = b.get("start", b.get("t0")), b.get("end", b.get("t1"))
        if s is None or e is None:
            continue
        if b.get("hold") or ("voice" in b and not (b.get("voice") or "").strip()):
            continue   # a HOLD (a clip's own sound plays there; the narration is silent): no take to level (it would read -inf)
        out.append((b.get("id", b.get("beat", "?")), float(s), float(e)))
    return out


def run(P, quiet=False, verbose=False):
    x, sr = G.load_mono(P["final"])
    beats = load_beats(P["beats"])
    rows = []
    for bid, s, e in beats:
        if e - s < 2.0:
            continue
        m = measure(x[int(s * sr):int(e * sr)], sr)
        if m:
            rows.append((bid, s, e, m))
    if len(rows) < 5:
        raise ValueError(f"only {len(rows)} beats of 2 s or more in {P['beats']}: no median to compare with")
    med_c = float(np.median([r[3]["crest"] for r in rows]))
    med_l = float(np.median([r[3]["level"] for r in rows]))
    flags = []
    for bid, s, e, m in rows:
        dc, dl = m["crest"] - med_c, m["level"] - med_l
        if verbose:
            print(f"  {bid:6s} {G.fmt_t(s)}  crest {m['crest']:5.2f} ({dc:+.2f})  level {m['level']:6.2f} ({dl:+.2f})")
        if dc >= CREST_OVER:
            flags.append(G.flag("A8", f"raw:{bid}", s, bid, f"{bid}: crest {m['crest']:.1f} dB, {dc:.1f} dB over the narration's "
                                f"{med_c:.1f}: peaks a raw take has (chained 11-12, raw 13.7-15.3): run the take through chain D "
                                f"(voice_level.py --chain mb --lufs -14 --ceil -1.5) before the splice", crest=round(m["crest"], 2)))
            continue
        if abs(dl) >= LEVEL_OFF:
            flags.append(G.flag("A8", f"level:{bid}", s, bid, f"{bid}: {dl:+.1f} dB against the narration's loudness: a take at "
                                f"another level", level=round(m["level"], 2)))
            continue
        t = s
        while t + WIN <= e:
            w = measure(x[int(t * sr):int((t + WIN) * sr)], sr)
            if w and w["crest"] - med_c >= WIN_OVER:
                flags.append(G.flag("A8", f"raw:{bid}@{t:.0f}", t, bid, f"{bid} from {G.fmt_t(t)}: crest {w['crest']:.1f} dB over 4 s, "
                                    f"{w['crest'] - med_c:.1f} dB over the narration's {med_c:.1f}: a piece spliced in raw?",
                                    crest=round(w["crest"], 2)))
                break
            t += STEP
    clip = np.flatnonzero(np.abs(x) >= FULL)
    if len(clip) >= 3:
        runs = np.split(clip, np.flatnonzero(np.diff(clip) > int(0.05 * sr)) + 1)
        for r in runs[:10]:
            t0 = r[0] / sr
            bid = next((b for b, s, e in beats if s <= t0 < e), "?")
            flags.append(G.flag("A8", f"clip:{t0:.2f}", t0, bid, f"{len(r)} samples at full scale ({bid}): clipped, a take gained "
                                f"past 0 dBFS; re-splice it through chain D", samples=int(len(r))))
    res = {"check": "A8", "final": str(P["final"]), "median_crest": round(med_c, 2), "median_level": round(med_l, 2), "flags": flags}
    if not quiet:
        print(f"A8 chain: {len(rows)} beats, crest median {med_c:.2f} dB, level median {med_l:.2f} dB; {len(flags)} flags")
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
