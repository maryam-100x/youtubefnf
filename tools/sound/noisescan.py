"""A4 of the sound gate: hiss and static in the voice (a near-empty piece of a take that a level step lifts can play as loud static).
Speech, breath and a word's own s are shaped (voiced: energy in the low harmonics; a fricative or a breath: one band); static is flat
across the band. So every 40-ms window (20-ms hop) gets its level and its spectral flatness over 300-8000 Hz (geometric over
arithmetic mean of the power spectrum: 1.0 = white noise, a vowel ~0.00-0.05, a breath or an s 0.05-0.30), and:
  NOISE   inside a pause (A3's measure: after a word's own sound and its spelling's guard, before the next word's onset ramp; before
          the first word; after the last word's guard) a run of 80 ms or more over -55 dB with flatness 0.35 or more (single 40-ms
          windows of the take's own floor reach 0.35-0.55 in clean pauses, a 99th percentile of 0.44-0.53; none hold 80 ms). Not just
          "outside Whisper's words": Whisper ends a word early and its own f, s or v (flatness 0.4-0.57) sits there;
  STATIC  anywhere, words included (Whisper can take the noise for a word and write one onto it), a run of 200 ms or more over
          -25 dB with flatness 0.45 or more (a word's f or v is as flat but 10-20 dB under its vowels: -29..-35 dB; and 120 ms at
          most, -19..-23 dB; an s is louder but narrow, flatness 0.08-0.31). Static measures -11..-19 dB at flatness 0.46-0.64, the
          real word before it 0.00-0.31.
Buzz (hum) isn't covered: no check is proved on it yet.

  EDIT tools/sound/noisescan.py <video> [--final F --words W] [--json out]"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

WIN, HOP = 0.04, 0.02
LO, HI = 300.0, 8000.0
NOISE_DB, NOISE_FLAT, NOISE_MIN = -55.0, 0.35, 0.08
STATIC_DB, STATIC_FLAT, STATIC_MIN = -25.0, 0.45, 0.20
MARGIN = 0.03


def frames(x, sr):
    """(times, level dB, flatness) per 40-ms window, 20-ms hop"""
    q, h = int(WIN * sr), int(HOP * sr)
    n = max(0, (len(x) - q) // h + 1)
    idx = np.arange(q)[None, :] + h * np.arange(n)[:, None]
    fr = x[idx] * np.hanning(q)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2 + 1e-20
    f = np.fft.rfftfreq(q, 1 / sr)
    band = (f >= LO) & (f <= HI)
    Pb = P[:, band]
    flat = np.exp(np.mean(np.log(Pb), axis=1)) / np.mean(Pb, axis=1)
    lv = 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-24)
    return np.arange(n) * HOP, lv, flat


def runs(mask, min_frames):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= min_frames:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def run(P, quiet=False):
    import pauses as PZ
    V = PZ.Voice(P["final"])
    x, sr = V.x, V.sr
    W = G.load_words(P["words"])
    t, lv, fl = frames(x, sr)
    # the pauses' insides (A3's measure: after a word's own sound and its spelling's guard, before the next word's onset ramp), the
    # stretch before the first word and the one after the last word's guard: no word's sound is in them
    outside = np.zeros(len(t), bool)

    def mark(t0, t1):
        a_ = int(max(0, t0) / HOP)
        b_ = int(max(0, t1 - WIN) / HOP) + 1
        if b_ > a_:
            outside[a_:b_] = True
    if W:
        mark(0.0, W[0]["start"] - 0.05)
        mark(W[-1]["end"] + PZ.guard(W[-1]["w"]), len(x) / sr)
    for w0, w1 in zip(W, W[1:]):
        if w1["start"] - w0["end"] > 3.0:
            mark(w0["end"] + PZ.guard(w0["w"]), w1["start"] - 0.05)
            continue
        m = V.measure(w0, w1)
        if m and m["i1"] > m["i0"]:
            mark(m["i0"] * PZ.FINE, m["i1"] * PZ.FINE)
    flags = []
    for i, j in runs((lv > STATIC_DB) & (fl >= STATIC_FLAT), max(1, int(round(STATIC_MIN / HOP)) - 1)):
        t0, t1 = t[i], t[j - 1] + WIN
        inside = [w["w"] for w in W if w["start"] < t1 and w["end"] > t0]
        flags.append(G.flag("A4", f"static@{t0:.2f}", t0, inside[0] if inside else "",
                            f"static {t0:.2f}-{t1:.2f} s ({(t1 - t0) * 1000:.0f} ms), up to {lv[i:j].max():.1f} dB, flatness "
                            f"{fl[i:j].min():.2f}-{fl[i:j].max():.2f}" + (f", where Whisper wrote {inside}" if inside else ""),
                            ms=round((t1 - t0) * 1000), loud=round(float(lv[i:j].max()), 1)))
    # windows overlap by half: a run of k windows covers (k + 1) * 20 ms
    for i, j in runs(outside & (lv > NOISE_DB) & (fl >= NOISE_FLAT), max(1, int(round(NOISE_MIN / HOP)) - 1)):
        t0, t1 = t[i], t[j - 1] + WIN
        if any(f["t"] <= t1 and t0 <= f["t"] + f["ms"] / 1000 for f in flags):
            continue                                   # inside a stretch already flagged as static
        prev = [w for w in W if w["end"] <= t0 + MARGIN]
        word = prev[-1]["w"] if prev else ""
        flags.append(G.flag("A4", f"noise@{t0:.2f}", t0, word,
                            f"noise in a pause {t0:.2f}-{t1:.2f} s ({(t1 - t0) * 1000:.0f} ms), up to {lv[i:j].max():.1f} dB, "
                            f"flatness {fl[i:j].max():.2f}" + (f", after {word!r}" if word else ""),
                            ms=round((t1 - t0) * 1000), loud=round(float(lv[i:j].max()), 1)))
    flags.sort(key=lambda f: f["t"])
    out = outside & (lv > NOISE_DB)
    longest = max((j - i for i, j in runs((lv > STATIC_DB) & (fl >= STATIC_FLAT), 1)), default=0)
    nl = max((j - i for i, j in runs(outside & (lv > NOISE_DB) & (fl >= NOISE_FLAT), 1)), default=0)
    res = {"check": "A4", "final": str(P["final"]), "flags": flags,
           "pause_windows_over_-55dB": int(out.sum()),
           "pause_flatness_p99": round(float(np.percentile(fl[out], 99)), 3) if out.any() else None,
           "pause_flatness_max": round(float(fl[out].max()), 3) if out.any() else None,
           "longest_flat_loud_ms": int((longest + 1) * HOP * 1000) if longest else 0,
           "longest_noise_in_pause_ms": int((nl + 1) * HOP * 1000) if nl else 0}
    if not quiet:
        print(f"A4 noise: {len(t)} windows; in pauses {res['pause_windows_over_-55dB']} over -55 dB, flatness 99th pct "
              f"{res['pause_flatness_p99']}, max {res['pause_flatness_max']}; longest flat run in a pause {res['longest_noise_in_pause_ms']} ms "
              f"(bar {int(NOISE_MIN * 1000)}); longest flat run over {STATIC_DB:.0f} dB anywhere {res['longest_flat_loud_ms']} ms "
              f"(bar {int(STATIC_MIN * 1000)}); {len(flags)} flags")
        G.print_flags(res)
    return res


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    a = ap.parse_args()
    res = run(G.paths_from(a))
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
