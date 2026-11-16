"""Every pause inside a sentence (commas and lists included) cut to 0.12 s, the pacing that sounds natural for a narration: a pause
inside a sentence (the next word in the same beat, the word before not ending a sentence), measured as the gate's A3 measures it,
over 0.15 s is shortened by cutting the middle of its longest run of DIGITAL SILENCE (10-ms frames under -60 dB) between the two words,
leaving 10 ms of that run on each side. Only digital silence is ever cut, so no sound of a word can go (a cut that chooses quiet or
breath frames by level takes word ends with it). Overlapping cuts are dropped. Moves dj's beat slots with the cuts (--beats); then
dj captions and sync_words.

--breaths: an inhale left inside such a pause (typically -33..-38 dB, 2-3 kHz, ~160 ms, right after an s or t ending) is no silence,
so nothing here could cut it, and breath_cut.py leaves it alone because it starts inside the word's spelling guard (an s may hiss
0.24 s). It is muted first, by the gate's own measure (pauses.Voice): a run of 10-ms frames over -48 dB that starts 20 ms or more after
the word's last sound, lasts 60 ms or more, is centred 1.5-3.5 kHz with no frame centred over 4 kHz (an s or sh hisses at 4-8 kHz: the
word's own sound) and never louder than -25 dB (the gate's A3 BREATH), ending before the next word's onset ramp; muted frame-exact
with 5-ms fades, then the pause is cut like any other. Every mute is printed; check the words by Whisper after (swallow).

--ends: the same method for the pauses BETWEEN sentences: the word before ends with . ? ! and the next word is in the same beat or
the next beat (beats.json's order, else the words' own), the two under 3 s apart (a hold or an insert gap is no pause, as the gate's A3
skips it). Measured the gate's way (pauses.Voice.measure); a pause over --over (default 0.30 in this mode) is cut to --target (default
0.22), only digital silence, 10 ms of each run left each side, beats moved. Every cut is printed (time in the input and the output, the
pause before -> after, after re-measured on the output). --dry prints the cuts and writes nothing.

  EDIT tools/sound/inner_gaps.py <in.wav> <out.wav> --words <words.json>
      [--beats <build>/beats.json] [--target 0.12] [--over 0.15] [--quiet -60] [--breaths] [--ends [--dry]]"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402
import pauses  # noqa: E402

BREATH_LO, BREATH_HI = 1500.0, 3500.0    # the gate's breath band (pauses.py: inhales centre at 2.0-3.0 kHz)


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--words", required=True)
    ap.add_argument("--beats")
    ap.add_argument("--target", type=float, help="default 0.12 (0.22 with --ends)")
    ap.add_argument("--over", type=float, help="default 0.15 (0.30 with --ends)")
    ap.add_argument("--quiet", type=float, default=-60.0, help="frames under this count as cuttable (default digital silence; -50 also takes room tone, never a word: mutes stay under -45)")
    ap.add_argument("--breaths", action="store_true", help="first mute an inhale left inside the pause (see above)")
    ap.add_argument("--ends", action="store_true", help="the pauses between sentences instead (see above)")
    ap.add_argument("--dry", action="store_true", help="with --ends: print the cuts, write nothing")
    a = ap.parse_args()
    if a.target is None:
        a.target = 0.22 if a.ends else 0.12
    if a.over is None:
        a.over = 0.30 if a.ends else 0.15
    x, sr = sf.read(a.src, always_2d=True)
    W = G.load_words(a.words)
    h = int(sr * 0.01)
    if a.ends:
        order = {}
        if a.beats:
            for i, b in enumerate(json.load(open(a.beats, encoding="utf-8"))["beats"]):
                order[b.get("id", b.get("beat"))] = i
        for w in W:                     # beats.json's order; a beat it doesn't hold, the words' own order after it
            order.setdefault(w.get("beat"), len(order))
        inside = [(p, q) for p, q in zip(W, W[1:]) if q["start"] - p["end"] <= 3.0 and G.sentence_end(p["w"])
                  and order[q.get("beat")] - order[p.get("beat")] in (0, 1)]
    else:
        inside = [(p, q) for p, q in zip(W, W[1:]) if not (q["start"] - p["end"] > 3.0 or p.get("beat") != q.get("beat")
                                                              or re.search(r"[.!?][\"”')]*$", p["w"].strip()))]
    if a.breaths:
        V = pauses.Voice(x=x.mean(1), sr=sr)
        g = np.ones(len(x))
        fade = int(0.005 * sr)
        muted = 0
        for p, q in inside:
            m = V.measure(p, q)
            if not m:      # any pause inside a sentence, short ones too: the gate's A3 BREATH flags an inhale in a 0.14-s pause
                continue
            j = int(round(m["j"] / 0.01))
            k = j + 2
            while k < m["i1"]:
                if V.lf[k] <= -48:
                    k += 1
                    continue
                e = k
                while e < m["i1"] and V.lf[e] > -48:
                    e += 1
                # a breath ends in quiet before the next word; a run that reaches the onset (e == i1) can be the word's own start (the h
                # of a word like "has" is a 3-kHz noise like an inhale), and it starts in quiet too: a run straight out of the word's
                # sound is its stop's release (a -39 dB, 2.2-2.4 kHz, 70-ms k or t release), muting it leaves the word 15 dB under
                if (e - k >= 6 and e < m["i1"] and V.lf[k - 1] <= -45 and BREATH_LO <= float(np.median(V.cen[k:e])) <= BREATH_HI
                        and float(V.cen[k:e].max()) < 4000 and float(V.lf[k:e].max()) < -25):
                    s0, s1 = k * h, e * h
                    g[s0:s1] = 0
                    g[max(0, s0 - fade):s0] = np.minimum(g[max(0, s0 - fade):s0], np.linspace(1, 0, s0 - max(0, s0 - fade)))
                    g[s1:s1 + fade] = np.minimum(g[s1:s1 + fade], np.linspace(0, 1, len(g[s1:s1 + fade])))
                    muted += 1
                    print(f"  breath muted {k * 0.01:.2f}-{e * 0.01:.2f} s after {p['w']!r} (before {q['w']!r}): {(e - k) * 10} ms, "
                          f"loudest {V.lf[k:e].max():.0f} dB, centred {np.median(V.cen[k:e]):.0f} Hz, edges {V.lf[k - 1]:.0f} / "
                          f"{V.lf[min(e, len(V.lf) - 1)]:.0f} dB")
                k = e
        x = x * g[:, None]
        print(f"{muted} breath(s) inside a sentence muted")
    mono = x.mean(1)
    V = pauses.Voice(x=mono, sr=sr)
    n = len(mono) // h
    db = 20 * np.log10(np.sqrt((mono[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)
    cuts, meas = [], {}
    for pi, (p, q) in enumerate(inside):
        m = V.measure(p, q)
        if a.ends and m:
            m = dict(m, length=round(m["length"], 2))    # 10-ms frames: 0.24 is 0.24, not 0.24000000000000002 over the bar
            # the gate's onset is 3 20-ms frames over -30 dB, so a short next word with a dip after it can be passed over and the pause
            # read 0.06-0.08 s long, by where the 20-ms grid falls. The cut takes the shorter of the two (the gate's and the first 10-ms
            # frame over -30 dB), so it never cuts below the target (it can only cut less)
            jf = int(round(m["j"] / 0.01))
            kf = next((k for k in range(jf, min(len(V.lf), m["i1"] + 8)) if V.lf[k] > pauses.ONSET), None)
            if kf is not None and (kf - jf) * 0.01 < m["length"]:
                m = dict(m, length=round((kf - jf) * 0.01, 2), gate=m["length"])
        if not m or m["length"] <= a.over:
            continue
        meas[pi] = m
        # the window from the measured end of the word's last sound (the gate's j), not Whisper's end: Whisper can end a word well after
        # its sound, and the window would start after the pause it should cut
        i0, i1 = int(round(m["j"] / 0.01)) + 1, m["i1"]
        if a.quiet > -60:   # room tone too: only from 40 ms after the word's last sound to 30 ms before the next onset
            i0, i1 = i0 + 3, i1 - 3
        runs, s0 = [], None
        for k in range(max(0, i0), min(n, i1) + 1):
            if k < min(n, i1) and db[k] < a.quiet:
                s0 = k if s0 is None else s0
            elif s0 is not None:
                runs.append((s0, k))
                s0 = None
        # the longest quiet run first, then the next ones (a pause can hold its silence in two or three runs around a faint blip, and
        # the longest alone can't bring it to the target), 10 ms of each run kept on each side
        need = m["length"] - a.target
        # --ends: in whole ms, so an exact 0.03 counts (float arithmetic would leave 0.0299... and skip the second run; the default
        # pass keeps its own arithmetic, unchanged)
        r3 = (lambda v: round(v, 3)) if a.ends else (lambda v: v)
        for r0, r1 in sorted(runs, key=lambda r: r[0] - r[1]):
            drop = r3(min(need, (r1 - r0) * 0.01 - 0.02))
            if drop < 0.03:
                break
            mid = (r0 + r1) * h // 2
            cuts.append((mid - int(drop * sr / 2), mid + int(drop * sr / 2), p["w"], q["w"], m["length"], pi))
            need = r3(need - drop)
            if need < 0.03:
                break
    kept, end = [], -1
    for c in sorted(cuts):
        if c[0] > end:
            kept.append(c)
            end = c[1]
    cuts = kept
    cf = int(0.005 * sr)
    y = x
    for c0, c1, *_ in sorted(cuts, reverse=True):
        ramp = np.linspace(0, 1, cf)[:, None]
        y = np.concatenate([y[:c0 - cf], y[c0 - cf:c0] * (1 - ramp) + y[c1:c1 + cf] * ramp, y[c1 + cf:]])
    spans = sorted((c0 - cf, c1 + cf) for c0, c1, *_ in cuts)

    def moved(t):
        pnt, out = int(round(t * sr)), 0
        for s0_, s1_ in spans:
            if pnt >= s1_:
                out += (s1_ - s0_) - cf
            elif pnt > s0_:
                out += pnt - s0_
        return round((pnt - out) / sr, 4)
    if a.ends:      # every cut, the pause re-measured the gate's way on the cut audio, its words at their moved times
        V2 = pauses.Voice(x=y.mean(1), sr=sr)
        for pi in sorted({c[5] for c in cuts}):
            p, q = inside[pi]
            m1 = meas[pi]
            out_ = sum((c[1] - c[0] + cf) / sr for c in cuts if c[5] == pi)
            p2 = dict(p, start=moved(p["start"]), end=moved(p["end"]))
            q2 = dict(q, start=moved(q["start"]), end=moved(q["end"]))
            m2 = V2.measure(p2, q2)
            # and by the frames: the word's end (the gate's j, moved) to the first 10-ms frame over -30 dB. The gate's onset search starts
            # 0.12 s before Whisper's start of the next word, so where that start runs early (a muted head, Whisper 0.15 s before the
            # sound) a cut can bring the search back into the word before and the gate reads no pause (None)
            j2 = int(round(moved(m1["j"]) / 0.01))
            k2 = next((k for k in range(j2, min(len(V2.lf), j2 + 300)) if V2.lf[k] > pauses.ONSET), j2)
            g1 = f", the gate's {m1['gate']:.2f}" if "gate" in m1 else ""
            g2 = f"{m2['length']:.2f}" if m2 else "none (it reads the words as one)"
            print(f"  {G.fmt_t(p['end'])} ({p['end']:.2f} s -> {p2['end']:.2f} s) {p['beat']}/{q['beat']} {p['w']!r} -> {q['w']!r}: "
                  f"{m1['length']:.2f}{g1} -> {(k2 - j2) * 0.01:.2f} s by the frames, {g2} by the gate ({out_:.3f} s out)")
        if a.dry:
            print(f"DRY: {len(cuts)} cut(s) in {len({c[5] for c in cuts})} pause(s) between sentences over {a.over} s, "
                  f"{(len(x) - len(y)) / sr:.2f} s would go; {len(x) / sr:.2f} -> {len(y) / sr:.2f} s; nothing written")
            return
    sf.write(a.out, y, sr, subtype=sf.info(a.src).subtype)
    if a.beats:
        B = json.load(open(a.beats, encoding="utf-8"))
        fps_s = str(B.get("fps", "60/1"))
        num, den = (int(v) for v in fps_s.split("/")) if "/" in fps_s else (int(fps_s), 1)
        fps = num / den
        for b in B["beats"]:
            for k in ("start", "voice_end", "end"):
                if k in b:
                    b[k] = moved(b[k])
        for i, b in enumerate(B["beats"]):
            b["start_f"] = round(b["start"] * fps)
            nxt = B["beats"][i + 1]["start"] if i + 1 < len(B["beats"]) else len(y) / sr
            b["frames"] = round(nxt * fps) - b["start_f"]
        B["duration"] = round(len(y) / sr, 4)
        B["total_frames"] = round(len(y) / sr * fps)
        json.dump(B, open(a.beats, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{len({c[5] for c in cuts}) if a.ends else len(cuts)} pause(s) {'between sentences' if a.ends else 'inside a sentence'} cut to {a.target} s"
          f"{f' ({len(cuts)} cuts)' if a.ends else ''}, {(len(x) - len(y)) / sr:.2f} s out; "
          f"{len(x) / sr:.2f} -> {len(y) / sr:.2f} s -> {a.out}")


if __name__ == "__main__":
    main()
