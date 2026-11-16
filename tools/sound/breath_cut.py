"""Only the words stay: every breath, inhale, exhale and dead air between words is taken out of a narration, so a listener hears
speech and nothing else (inhales between words are what viewers notice first).

What is a word: each word of words.json (the script's words with the times Whisper heard) is found in the audio by its voiced frames
(10 ms frames whose autocorrelation pitch strength at 70-400 Hz is over VOICED and whose level is within 35 dB of the narration's peak),
searched from 0.15 s before Whisper's start to 0.15 s after its end. A word keeps everything from a guard before its first voiced frame
to a guard after its last: its unvoiced consonants live there (an s, f, sh, th, h or a t/k/p release), so the guard follows its spelling:
  start: s/sh/f/th/h/ch/x/z/c(e,i) 0.16 s, p/t/k/c/q 0.12 s, anything voiced 0.035 s
  end:   s/sh/ch/f/th/x/z/ce/se 0.24 s, t/k/p/ct/ght 0.2 s, anything voiced 0.12 s, and on through the word's own decay to
         its valley (so no word end sounds cut off)
Everything between one word's kept end and the next word's kept start is not a word. A stretch there that has voiced frames as loud as
speech (within 15 dB of the peak) is left alone and reported: a word the list doesn't have, never cut by guess.

  --mode mute   the stretch is silenced in place (25 ms fades): the timing never moves (a finished long video, its picture locked)
  --mode cut    the stretch is cut down to a pause: 0.10 s after a sentence's end (. ? !), 0.07 s after a comma, 0.04 s between other
                words (config.toml's gaps; Shorts: no silence over 0.18 s); with --beats the cuts stay inside each beat's frame-aligned
                slot and every later beat moves up (beats.json's start_f/frames), and every words file given with --remap is re-timed
                with the same map

  EDIT tools/sound/breath_cut.py <narration.wav> <words.json> <out.wav> --mode mute|cut
      [--beats <beats.json> --beats-out <beats.json>] [--remap <in.json>=<out.json> ...] [--report <report.json>] [--fps 60]"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf

VOICED = 0.45
PAUSE = {"sentence": 0.10, "comma": 0.07, "word": 0.04}


def frames_features(x, sr):
    """Per 10 ms frame: level (dB) and pitch strength (normalised autocorrelation peak, 70-400 Hz, 30 ms window), on a 16 kHz copy."""
    k = max(1, sr // 16000)
    y = x[::k].astype(np.float64)
    fs = sr / k
    hop, win = int(fs * 0.01), int(fs * 0.03)
    n = max(0, (len(y) - win) // hop + 1)
    lo, hi = int(fs / 400), int(fs / 70)
    lv, ps = np.empty(n), np.empty(n)
    for b0 in range(0, n, 20000):                 # in blocks: a 20-minute narration in one go needs ~2 GB
        b1 = min(n, b0 + 20000)
        idx = np.arange(win)[None, :] + hop * np.arange(b0, b1)[:, None]
        F = y[idx]
        F = F - F.mean(1, keepdims=True)
        lv[b0:b1] = 10 * np.log10((F ** 2).mean(1) + 1e-14)
        spec = np.fft.rfft(F * np.hanning(win), 2 * win)
        ac = np.fft.irfft(np.abs(spec) ** 2)[:, :win]
        ps[b0:b1] = ac[:, lo:hi].max(1) / (ac[:, 0] + 1e-20)
    return lv, ps


def head_guard(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0.035
    if w[:2] in ("sh", "th", "ch", "ph") or w[0] in "sfhxz" or (w[0] == "c" and w[1:2] in ("e", "i", "y")):
        return 0.16
    if w[0] in "ptkcq":
        return 0.12
    return 0.035


def tail_guard(word):
    w = re.sub(r"[^a-z0-9]", "", word.lower())
    if not w:
        return 0.12
    if w.isdigit():                                   # "6", "17": said as words; "six", "seventeen" end voiced or in s/x
        return 0.24
    if w.endswith(("ght", "ct", "pt")) or w[-1] in "tkpdbg":   # a -d/-b/-g releases late too
        return 0.2
    # a voiced fricative end is a fricative too: a -ve buzzes at -25..-33 dB past the 0.12-s voiced guard, and a later pass would mute
    # it as breath
    if w.endswith(("sh", "ch", "th", "ce", "se", "fe", "ve")) or w[-1] in "sfxzv":
        return 0.24
    if w.endswith("ed") and len(w) > 3:
        return 0.2
    return 0.12


def find_regions(x, sr, words):
    lv, ps = frames_features(x, sr)
    n = len(lv)
    pk = float(np.percentile(lv, 99))
    voiced = (ps > VOICED) & (lv > pk - 35)
    loud = voiced & (lv > pk - 15)
    sm = np.convolve(lv, np.ones(3) / 3, mode="same")
    keep = []
    for w in words:
        a, b = int((w["start"] - 0.15) * 100), int((w["end"] + 0.15) * 100)
        a, b = max(0, a), min(n, b)
        v = np.where(voiced[a:b])[0]
        if len(v):
            s, e = (a + v[0]) / 100, (a + v[-1] + 3) / 100       # +3: the 30 ms window's span
        else:                                                    # no voiced frame (a whispered or unvoiced word): Whisper's times
            s, e = w["start"], w["end"]
        # so no word end sounds cut off, the tail runs on while the level keeps falling (the word's own decay, smoothed over 30 ms)
        # to its valley or to 50 dB under the peak, at most 0.4 s; a rise means the next sound (an inhale) has started, and the cut
        # goes there, never earlier than the spelling's guard
        j, lim = int(e * 100), min(n - 1, int((e + 0.4) * 100))
        while j < lim and sm[j + 1] <= sm[j] + 0.5 and sm[j] > pk - 50:
            j += 1
        keep.append([max(0.0, s - head_guard(w["w"])), max(e + tail_guard(w["w"]), j / 100 + 0.02)])
    regions, skipped = [], []
    dur = len(x) / sr
    bounds = [(0.0, None)] + [(k[1], i) for i, k in enumerate(keep)]
    for j in range(len(bounds)):
        g0, i = bounds[j]
        g1 = keep[j][0] if j < len(keep) else dur
        if g1 - g0 < 0.03:
            continue
        f0, f1 = int(g0 * 100), int(g1 * 100)
        if loud[f0:f1].sum() >= 5:                                # 50 ms of loud voice: speech the list lacks
            skipped.append({"start": round(g0, 3), "end": round(g1, 3), "after": words[i]["w"] if i is not None else None})
            continue
        prev = words[i]["w"] if i is not None else ""
        kind = "sentence" if re.search(r"[.?!]['\"”]?$", prev) else "comma" if re.search(r"[,;:—-]$", prev) else "word"
        if i is None:
            kind = "lead"
        noise = float(lv[f0:f1].max() - pk) if f1 > f0 else -99.0
        regions.append({"start": round(g0, 3), "end": round(g1, 3), "after": prev, "kind": kind, "loudest_db": round(noise, 1)})
    return regions, skipped


def mute(x, sr, regions):
    g = np.ones(len(x))
    f = int(0.025 * sr)                               # 25 ms fades (10 ms read as a chop)
    for r in regions:
        s0, s1 = int(r["start"] * sr), min(len(x), int(r["end"] * sr))
        if s1 - s0 <= 2 * f:
            continue
        g[s0:s0 + f] = np.minimum(g[s0:s0 + f], np.linspace(1, 0, f))
        g[s0 + f:s1 - f] = 0
        g[s1 - f:s1] = np.minimum(g[s1 - f:s1], np.linspace(0, 1, f))
    return x * (g[:, None] if x.ndim == 2 else g)


DROPS_ON_SOUND = []    # the last declick's drops into silence that came on sound (s): cuts through a word, left for the gate


def declick(y, sr, fade=0.04, floor_db=-70.0):
    """Every drop into digital silence fades out over the 40 ms before it (a splice piece that ends in a 3 ms fade while still
    audible, -30 to -45 dB, clicks). Returns (y, count)."""
    mono = y.mean(1) if y.ndim == 2 else y
    z = np.abs(mono) < 1e-7
    h = int(0.002 * sr)
    n = len(mono) // h
    zz = z[:n * h].reshape(n, h).all(1)                          # 2 ms blocks of exact silence
    f, thr, count = int(fade * sr), 10 ** (floor_db / 20), 0
    g = np.ones(len(mono))
    DROPS_ON_SOUND.clear()
    for i in range(1, n):
        if zz[i] and not zz[i - 1]:
            e = i * h
            while e > 0 and z[e - 1]:
                e -= 1
            last = mono[max(0, e - int(0.005 * sr)):e]
            # a drop that comes ON sound (the last 5 ms over -40 dB) is a cut through a word, never a click to smooth: the 40-ms fade
            # would take even more of the word's end. Left as it is and listed; the gate's A13/A1 flag the lost end and the fix goes
            # to the step that cut
            if len(last) and 20 * np.log10(np.sqrt(np.mean(last ** 2)) + 1e-12) > -40:
                DROPS_ON_SOUND.append(round(e / sr, 3))
                continue
            if np.abs(last).max() > thr:
                s0 = max(0, e - f)
                ramp = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, e - s0))
                g[s0:e] = np.minimum(g[s0:e], ramp)
                count += 1
    return (y * (g[:, None] if y.ndim == 2 else g)), count


def cut_plan(regions, dur):
    """[(t0, t1, keep_s)]: the stretch t0-t1 becomes keep_s of silence (the rest is removed)."""
    plan = []
    for r in regions:
        if r["kind"] == "lead":
            p = 0.0 if r["start"] == 0.0 else PAUSE["word"]
        elif r["end"] >= dur - 1e-3:
            p = 0.0
        else:
            p = PAUSE.get(r["kind"], PAUSE["word"])
        plan.append((r["start"], r["end"], min(p, r["end"] - r["start"])))
    return plan


def apply_cut(x, sr, plan):
    out, t_prev, f = [], 0, int(0.02 * sr)
    for t0, t1, keep in plan:
        s0, s1 = int(t0 * sr), int(t1 * sr)
        seg = x[t_prev:s0].copy()
        if len(seg) > f:
            seg[-f:] *= np.linspace(1, 0, f)[:, None] if seg.ndim == 2 else np.linspace(1, 0, f)
        out.append(seg)
        out.append(np.zeros((int(keep * sr),) + x.shape[1:]))
        t_prev = s1
    out.append(x[t_prev:].copy())
    return np.concatenate(out)


def fade_in_after_cuts(y, sr, starts):
    f = int(0.02 * sr)
    for s in starts:
        s = int(s * sr)
        if s + f <= len(y):
            y[s:s + f] *= np.linspace(0, 1, f)[:, None] if y.ndim == 2 else np.linspace(0, 1, f)
    return y


def time_map(plan):
    """old time -> new time for a cut plan."""
    def m(t):
        shift = 0.0
        for t0, t1, keep in plan:
            if t >= t1:
                shift += (t1 - t0) - keep
            elif t > t0:
                return t0 - shift + min(t - t0, keep)
        return t - shift
    return m


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("words")
    ap.add_argument("out")
    ap.add_argument("--mode", choices=["mute", "cut"], required=True)
    ap.add_argument("--beats")
    ap.add_argument("--beats-out")
    ap.add_argument("--remap", action="append", default=[])
    ap.add_argument("--report")
    ap.add_argument("--fps", type=int, default=60)
    a = ap.parse_args()

    x, sr = sf.read(a.wav, dtype="float64", always_2d=False)
    W = json.loads(Path(a.words).read_text(encoding="utf-8"))
    W = W["words"] if isinstance(W, dict) else W
    words = sorted(W, key=lambda w: w["start"])
    mono = x.mean(1) if x.ndim == 2 else x
    regions, skipped = find_regions(mono, sr, words)
    dur = len(x) / sr
    removed = sum(r["end"] - r["start"] for r in regions)
    if a.mode == "mute":
        y = mute(x, sr, regions)
        y, nclick = declick(y, sr)
        sf.write(a.out, y, sr, subtype="PCM_16")
        print(f"{nclick} drops into silence faded over 40 ms (de-click)")
        print(f"{len(regions)} stretches between words silenced in place ({removed:.2f} s of {dur:.2f} s); "
              f"{len(skipped)} left alone (loud voice the words list lacks) -> {a.out}")
    else:
        fpf = sr // a.fps
        if a.beats:
            B = json.loads(Path(a.beats).read_text(encoding="utf-8"))
            pieces, new_start_f, plan_all = [], 0, []
            for b in B["beats"]:
                s0, s1 = b["start_f"] * fpf, (b["start_f"] + b["frames"]) * fpf
                bt0, bt1 = s0 / sr, s1 / sr
                plan = [(max(t0, bt0), min(t1, bt1), keep) for t0, t1, keep in cut_plan(regions, dur) if t1 > bt0 and t0 < bt1]
                plan = [(t0, t1, min(keep, t1 - t0)) for t0, t1, keep in plan if t1 - t0 > 0.02]
                # the beat's last stretch (into the next beat) is the sentence pause; a beat's first stretch keeps the pause before it
                local = [(t0 - bt0, t1 - bt0, k) for t0, t1, k in plan]
                seg = apply_cut(x[s0:s1], sr, local)
                seg = fade_in_after_cuts(seg, sr, [time_map(local)(t1) for _, t1, _ in local])
                frames = int(np.ceil(len(seg) / fpf))
                seg = np.concatenate([seg, np.zeros((frames * fpf - len(seg),) + seg.shape[1:])])
                shift = new_start_f * fpf / sr - bt0
                plan_all.append((bt0, bt1, local, shift))
                pieces.append(seg)
                b["start_f"], b["frames"] = new_start_f, frames
                new_start_f += frames
            y = np.concatenate(pieces)

            def m(t):
                for k, (bt0, bt1, local, shift) in enumerate(plan_all):
                    if bt0 <= t < bt1 or k == len(plan_all) - 1:
                        return time_map(local)(t - bt0) + bt0 + shift
                return t
            for b in B["beats"]:
                st = b["start_f"] / a.fps
                dv = m(b["voice_end"]) - m(b["start"]) if "voice_end" in b else None
                b["start"] = round(st, 4)
                b["end"] = round(st + b["frames"] / a.fps, 4)
                if dv is not None:
                    b["voice_end"] = round(min(st + dv, b["end"]), 4)
            B["total_frames"] = new_start_f
            B["duration"] = round(len(y) / sr, 3)
            Path(a.beats_out or a.beats).write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            plan = cut_plan(regions, dur)
            y = apply_cut(x, sr, plan)
            y = fade_in_after_cuts(y, sr, [time_map(plan)(t1) for _, t1, _ in plan])
            m = time_map(plan)
        y, nclick = declick(y, sr)
        print(f"{nclick} drops into silence faded over 40 ms (de-click)")
        sf.write(a.out, y, sr, subtype="PCM_16")
        for spec in a.remap:
            src, dst = spec.split("=", 1)
            D = json.loads(Path(src).read_text(encoding="utf-8"))
            L = D["words"] if isinstance(D, dict) else D
            for w in L:
                for k in ("start", "end"):
                    if k in w:
                        w[k] = round(m(w[k]), 3)
            Path(dst).write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(regions)} stretches between words cut ({removed:.2f} s of not-words; {dur:.2f} -> {len(y) / sr:.2f} s); "
              f"{len(skipped)} left alone -> {a.out}")
    for s in skipped:
        print(f"  left alone {s['start']:.2f}-{s['end']:.2f} after {s['after']!r}: voice as loud as speech, not in the words list")
    if a.report:
        Path(a.report).write_text(json.dumps({"mode": a.mode, "regions": regions, "skipped": skipped}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
