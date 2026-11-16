"""A Short's pause the tighten can't take (a Short keeps ~0.07 s between words): shorts_tighten skips a gap whose first edge is the
word's own hiss (a word ending on "s" before the next word: edges at -32 dB, the s still sounding). This finds the quiet stretch inside
the gap after <t> (10-ms frames under -45 dB), removes its middle in whole 60-fps frames so 0.07 s of quiet is left (the hiss and the
next word's onset untouched: a cut starts and ends in quiet), and moves every later beat in build/beats.json back by the cut. Then:
`dj captions`, sync_words.py, gate_sound.py. The narration is rewritten in place; the old one is kept as narration_precut.wav. Works on a
long video's narration the same way (--keep 0.12 for a pause inside a sentence).

  EDIT tools/sound/cut_pause.py <video> <t seconds> [--keep 0.07] [--dry] [--words]
      [--give-back T]   time kept (for a pause cut after the picture was fitted to the timing):
                        the cut's length goes back as digital silence into the middle of the quiet stretch after T (the sentence's
                        end pause); only the words between the cut and T move back, everything from T on keeps its time
      --words           build/captions/words.json's words, cues and chunks moved with the sound (no new Whisper pass)"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import TOOLS, VIDEOS  # noqa: E402

FPS = 60


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("t", type=float)
    ap.add_argument("--keep", type=float, default=0.07)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--give-back", type=float)
    ap.add_argument("--words", action="store_true", help="move build/captions/words.json's words, cues and chunks with the sound and sign "
                    "the narration again (instead of a new Whisper pass)")
    a = ap.parse_args()
    build = VIDEOS / a.slug / "build"
    wav = build / "voice" / "narration.wav"
    x, sr = sf.read(wav, always_2d=True)
    mono = x.mean(1)
    hop = int(0.01 * sr)
    i0, i1 = int(a.t * sr), int((a.t + 0.8) * sr)
    seg = mono[i0:i1]
    n = len(seg) // hop
    db = 20 * np.log10(np.sqrt((seg[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-12)
    quiet = db < -45
    best, cur, start = (0, 0), 0, 0
    for k, q in enumerate(quiet):
        if q:
            if cur == 0:
                start = k
            cur += 1
            if cur > best[1]:
                best = (start, cur)
        else:
            cur = 0
    qs, ql = best
    run = ql * 0.01
    cut = run - a.keep
    fpf = sr // FPS
    frames = int(cut * FPS)
    if frames < 1:
        raise SystemExit(f"the quiet stretch after {a.t:.2f} s is {run:.2f} s: nothing to cut")
    c1 = i0 + qs * hop + int(a.keep / 2 * sr)
    c2 = c1 + frames * fpf
    edge = lambda p: 20 * np.log10(np.sqrt((mono[max(0, p - hop // 2): p + hop // 2] ** 2).mean()) + 1e-12)
    print(f"quiet {run:.2f} s from {a.t + qs * 0.01:.2f} s; cut {frames} frames ({frames / FPS:.3f} s) at {c1 / sr:.3f}-{c2 / sr:.3f} s; "
          f"edges {edge(c1):.0f}/{edge(c2):.0f} dB")
    if edge(c1) > -45 or edge(c2) > -45:
        raise SystemExit("an edge isn't quiet: nothing cut")
    g = None
    if a.give_back is not None:
        # the longest quiet run in the 1.2 s after T (the sentence's end pause): the cut's length goes back into its middle
        j0, j1 = int(a.give_back * sr), int((a.give_back + 1.2) * sr)
        sg = mono[j0:j1]
        ng = len(sg) // hop
        dbg = 20 * np.log10(np.sqrt((sg[: ng * hop].reshape(ng, hop) ** 2).mean(1)) + 1e-12)
        bestg, curg, stg = (0, 0), 0, 0
        for k, q in enumerate(dbg < -45):
            if q:
                if curg == 0:
                    stg = k
                curg += 1
                if curg > bestg[1]:
                    bestg = (stg, curg)
            else:
                curg = 0
        if bestg[1] < 5:
            raise SystemExit(f"no quiet stretch of 50 ms after {a.give_back:.2f} s to give the time back into: nothing cut")
        g = j0 + (bestg[0] + bestg[1] // 2) * hop
        if c1 <= g <= c2:
            raise SystemExit("the give-back point is inside the cut: nothing cut")
        if g > c2:
            print(f"give back {frames / FPS:.3f} s at {g / sr:.3f} s (quiet {bestg[1] * 0.01:.2f} s from {a.give_back + bestg[0] * 0.01:.2f} s, "
                  f"edge {edge(g):.0f} dB): the words {c2 / sr:.2f}-{g / sr:.2f} s move back, nothing after {g / sr:.2f} s moves")
        else:   # an earlier pause takes the time (a sentence end grown too long by an earlier give-back goes back into its own sentence)
            print(f"give back {frames / FPS:.3f} s at {g / sr:.3f} s, before the cut (quiet {bestg[1] * 0.01:.2f} s from "
                  f"{a.give_back + bestg[0] * 0.01:.2f} s, edge {edge(g):.0f} dB): the words {g / sr:.2f}-{c1 / sr:.2f} s move on, nothing "
                  f"before {g / sr:.2f} s or after {c2 / sr:.2f} s moves")
        if edge(g) > -45:
            raise SystemExit("the give-back point isn't quiet: nothing cut")
    if a.dry:
        return
    shutil.copy2(wav, wav.with_name("narration_precut.wav"))
    sub = "PCM_24" if sf.info(wav.with_name("narration_precut.wav")).subtype == "PCM_24" else "PCM_16"
    z = np.zeros((c2 - c1, x.shape[1]))
    if g is None:
        sf.write(wav, np.concatenate([x[:c1], x[c2:]]), sr, subtype=sub)
    elif g > c2:
        sf.write(wav, np.concatenate([x[:c1], x[c2:g], z, x[g:]]), sr, subtype=sub)
    else:
        sf.write(wav, np.concatenate([x[:g], z, x[g:c1], x[c2:]]), sr, subtype=sub)
    sec = frames / FPS
    # what moves, on the old clock: (lo, hi, shift)
    if g is None:
        lo, hi, d = c1 / sr, float("inf"), -sec
    elif g > c2:
        lo, hi, d = c1 / sr, g / sr, -sec
    else:
        lo, hi, d = g / sr, c1 / sr, sec
    bp = build / "beats.json"
    B = json.loads(bp.read_text(encoding="utf-8"))
    for b in B["beats"]:
        for k in ("start_f", "end_f"):
            if isinstance(b.get(k), int) and lo * FPS < b[k] < hi * FPS:
                b[k] += int(round(d * FPS))
        for k in ("start", "end", "voice_end"):
            if isinstance(b.get(k), (int, float)) and lo < b[k] < hi:
                b[k] = round(b[k] + d, 4)
    if g is None and isinstance(B.get("duration"), (int, float)):
        B["duration"] = round(B["duration"] - sec, 4)
    bp.write_text(json.dumps(B, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.words:
        # the captions' words, cues and chunks move with the sound (no new Whisper pass: its word boxes change from pass to pass, and
        # each pass brings new flags), the srt files rewritten and the narration signed again
        import sys as _s
        _s.path.insert(0, str(TOOLS))
        from dj.core import file_sig
        from dj.captions import write_srt
        cp = build / "captions" / "words.json"
        D = json.loads(cp.read_text(encoding="utf-8"))
        moved = 0
        for key in ("words", "cues", "chunks"):
            for w in D.get(key, []):
                if key != "words":
                    # a cue or chunk holds several words: its end goes where its last word went. Clipping it at the cut (a word box's
                    # overhang into the pause) takes a cue spanning an inner cut off the screen while its words are still said
                    # (0.5-1.8 s with no subtitle)
                    s_, e_ = w["start"], w["end"]
                    ns = s_ + d if lo <= s_ < hi else s_
                    ne = e_ + d if lo <= e_ < hi else e_
                    if d < 0 and lo <= e_ < lo - d:      # it ended inside the stretch cut out (silence): it ends where the cut is
                        ne = lo
                    w["start"], w["end"] = round(ns, 4), round(max(ne, ns), 4)
                    continue
                if lo <= w["start"] < hi:
                    w["start"], w["end"] = round(w["start"] + d, 4), round(min(w["end"], hi) + d, 4)
                    moved += 1
                elif w["start"] < lo < w["end"] and d < 0:
                    w["end"] = round(lo, 4)
        D["narration_sig"] = file_sig(wav)
        cp.write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
        write_srt(build / "captions" / "captions.srt", D["cues"])
        write_srt(build / "captions" / "chunks.srt", D["chunks"])
        print(f"  captions: {moved} words moved {d:+.3f} s ({lo:.2f}-{hi:.2f} s), the narration signed again; next: sync_words.py")
    if g is None:
        print(f"narration {len(x) / sr - sec:.3f} s; beats after {c1 / sr:.2f} s moved back {sec:.3f} s")
    else:
        print(f"narration {len(x) / sr:.3f} s (unchanged); {lo:.2f}-{hi:.2f} s moved {d:+.3f} s, the rest kept its time")


if __name__ == "__main__":
    main()
