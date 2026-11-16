"""Hushed/whisper screen for voice takes. It only SCREENS; the creator's ear judges.

Per sentence of each TTS section (the .align.json next to each .wav gives the sentence times): voiced share, HNR, CPPS (Praat), the
4-8 kHz / 0.1-1 kHz energy ratio, F0 median and 5-95% range, and the median frame level. A sentence is flagged when, against the
median of all sentences given, its level is >= 3 dB lower AND (its F0 median >= 1.5 semitones lower OR its CPPS >= 1.0 lower).
Calibration: a hook heard as whispered against the same hook re-voiced read -4.0 dB, -1.7 st, CPPS -0.85, HF/LF +2.6 dB; a long
narration's sentences (293) spread with a level sd of 1.6 dB, a CPPS sd of 0.88 and F0 p5-p95 of 111-141 Hz.

  PIPE -I tools/qa/breathy.py <section.wav> [...]        (e.g. build/voice/cache/sec_*.wav)
"""
import json
import re
import sys

import numpy as np
import parselmouth
from parselmouth.praat import call


def feats(path, t0=None, t1=None):
    s = parselmouth.Sound(path)
    if t0 is not None:
        s = s.extract_part(from_time=t0, to_time=t1)
    x = s.values[0]
    sr = s.sampling_frequency
    hop, n = int(0.01 * sr), int(0.03 * sr)
    db = 20 * np.log10(np.array([np.sqrt(np.mean(x[i:i + n] ** 2) + 1e-12) for i in range(0, len(x) - n, hop)]))
    act = db > (np.max(db) - 35)
    f0 = s.to_pitch_ac(time_step=0.01, pitch_floor=70, pitch_ceiling=400).selected_array["frequency"]
    m = min(len(f0), len(act))
    voiced = (f0[:m] > 0) & act[:m]
    f0v = f0[:m][voiced]
    st = 12 * np.log2(f0v / np.median(f0v)) if len(f0v) else np.array([0.0])
    hv = s.to_harmonicity_cc(time_step=0.01, minimum_pitch=70).values[0]
    pc = call(s, "To PowerCepstrogram", 60, 0.002, 5000, 50)
    cpps = call(pc, "Get CPPS", "yes", 0.02, 0.0005, 60, 330, 0.05, "Parabolic", 0.001, 0, "Straight", "Robust")
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    fq = np.fft.rfftfreq(len(x), 1 / sr)
    hf, lf = spec[(fq >= 4000) & (fq < 8000)].sum(), spec[(fq >= 100) & (fq < 1000)].sum()
    return dict(voiced=float(voiced.sum() / max(act[:m].sum(), 1)),
                hnr=float(np.median(hv[hv > -100])) if np.any(hv > -100) else float("nan"),
                cpps=float(cpps), hf_lf_db=float(10 * np.log10(hf / lf)),
                f0_med=float(np.median(f0v)) if len(f0v) else 0.0,
                f0_range_st=float(np.percentile(st, 95) - np.percentile(st, 5)),
                level_db=float(np.median(db[act])) if act.any() else -99.0)


def sentences(wav, min_s=1.0):
    d = json.load(open(wav[:-4] + ".align.json", encoding="utf-8"))
    al = d.get("alignment", d)   # the TTS cache wraps it; a patched take keeps it bare
    ch = "".join(al["characters"])
    st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    for mt in re.finditer(r"[^.?!]+[.?!]", ch):
        a, b = mt.start(), mt.end() - 1
        while a < b and ch[a] == " ":
            a += 1
        if en[b] - st[a] >= min_s:
            yield st[a], en[b], ch[a:b + 1]


def main(wavs):
    rows = []
    for w in wavs:
        for t0, t1, text in sentences(w):
            f = feats(w, t0, t1)
            f.update(file=w, t0=t0, t1=t1, text=text)
            rows.append(f)
    if not rows:
        return
    lv = np.median([r["level_db"] for r in rows])
    f0 = np.median([r["f0_med"] for r in rows if r["f0_med"] > 0])
    cp = np.median([r["cpps"] for r in rows])
    print(f"{len(rows)} sentences; medians: level {lv:.1f} dB, F0 {f0:.1f} Hz, CPPS {cp:.2f}")
    for r in rows:
        dl, dc = r["level_db"] - lv, r["cpps"] - cp
        dst = 12 * np.log2(r["f0_med"] / f0) if r["f0_med"] > 0 else 0.0
        if dl <= -3 and (dst <= -1.5 or dc <= -1.0):
            print(f"FLAG {r['file'][-28:]} {r['t0']:6.2f}-{r['t1']:6.2f}  level {dl:+.1f} dB  F0 {dst:+.1f} st  CPPS {dc:+.2f}  | {r['text'][:70]}")


if __name__ == "__main__":
    main(sys.argv[1:])
