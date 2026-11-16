"""Shorts have no pauses between speech: every gap between words in a Short's narration, sentence ends and commas included, cut to
about 0.07 s, breaths with it, before the render.

A gap is a run of 10-ms frames under QUIET (-35 dB: no speech) between two spoken stretches; runs split by a faint blip (a breath, under
BREATH -25 dB, at most 0.25 s; a dip under 0.06 s with a blip under 0.10 s is a word's own release and stays) are one gap. Each gap
keeps KEEP_A s after the word before (its fade stays) and KEEP_B s before the next word; the middle goes, a whole number of 60-fps
frames long. Every cut is proved on the audio before it: both edges under EDGE (-38 dB), the loudest thing removed under BREATH, so no
word is touched. A cut across a beat boundary is split at the boundary so each beat loses whole frames; beats.json moves with it
(voice_edit.py's shift_beats/retime). A HOLD beat (silence on purpose: a clip plays there with its own sound) is never cut. The
narration is rewritten in place: keep a backup.
Then: `cd tools && PIPE -m dj captions ../videos/<video>` and `PIPE tools/motion/sync_words.py` for the words.

  EDIT tools/sound/shorts_tighten.py <video> [--dry] [--cap 0.25]
  (the video's build: MEDIA/videos/<video>/build; --cap is the long form's pause cap)"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import TOOLS, VIDEOS  # noqa: E402

sys.path.insert(0, str(TOOLS / "voice"))
from voice_edit import FPS, retime, shift_beats  # noqa: E402

QUIET, BREATH, EDGE = -35.0, -25.0, -38.0
KEEP_A, KEEP_B = 0.04, 0.03
MIN_CUT_FRAMES = 2
HOP = 0.01


def levels(x, sr):
    h = int(HOP * sr)
    n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)


def gaps(r):
    """Runs under QUIET between speech, merged across faint blips (breaths); the first and last run (lead-in, tail) are left out."""
    runs, i, n = [], 0, len(r)
    while i < n:
        if r[i] < QUIET:
            j = i
            while j < n and r[j] < QUIET:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for a, b in runs:
        if merged:
            pa, pb = merged[-1]
            blip = r[pb:a]
            # a blip is a breath unless both it and the dip before it are short: then it is a word's own release ("it" -> the t burst after its
            # closure), which stays, so no word end sounds cut off
            release = (pb - pa) * HOP < 0.06 and (a - pb) * HOP < 0.10   # a short dip and a short blip: the word's own release
            if len(blip) and (a - pb) * HOP <= 0.25 and blip.max() < BREATH and not release:
                merged[-1][1] = b
                continue
        merged.append([a, b])
    return [g for g in merged if g[0] > 0 and g[1] < n]


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--cap", type=float, help="long form: leave each pause at CAP s instead of the Shorts' 0.07 (55%% after the word, "
                                              "45%% before the next: the long form's pace)")
    a = ap.parse_args()
    global KEEP_A, KEEP_B
    if a.cap:
        KEEP_A = max(KEEP_A, a.cap * 0.55)
        KEEP_B = max(KEEP_B, a.cap - KEEP_A)
    build = VIDEOS / a.slug / "build"
    nar = build / "voice" / "narration.wav"
    x, sr = sf.read(nar, dtype="float64")
    B = json.loads((build / "beats.json").read_text(encoding="utf-8"))
    cuts = plan_cuts(x, sr, B)
    fpf = sr // FPS
    total = 0
    for p1, p2, ok, e1, e2, pk, gl in cuts:
        n = (p2 - p1) // fpf
        print(f"{'OK  ' if ok else 'SKIP'} {p1 / sr:6.2f}-{p2 / sr:6.2f} s: gap {gl:.2f} s, {n} frames out; edges {e1:.0f}/{e2:.0f} dB, removed peak {pk:.0f} dB")
        total += n if ok else 0
    print(f"{sum(1 for c in cuts if c[2])} cuts, {total} frames ({total / FPS:.2f} s) out")
    if a.dry:
        return
    f = int(0.005 * sr)
    for p1, p2, ok, *_ in sorted(cuts, key=lambda c: -c[0]):
        if not ok:
            continue
        n = (p2 - p1) // fpf
        head, tail = x[:p1].copy(), x[p2:].copy()
        ramp = np.linspace(1, 0, f)
        if x.ndim > 1:
            head[-f:] *= ramp[:, None]
            tail[:f] *= ramp[::-1][:, None]
        else:
            head[-f:] *= ramp
            tail[:f] *= ramp[::-1]
        x = np.concatenate([head, tail])
        i = max(k for k, b in enumerate(B["beats"]) if b["start_f"] * fpf <= p1)
        B["beats"][i]["frames"] -= n
        shift_beats(B, i + 1, -n)
    retime(B)
    if "duration" in B:
        B["duration"] = round(B["total_frames"] / FPS, 4)
    sf.write(nar, x, sr, subtype="PCM_16")
    (build / "beats.json").write_text(json.dumps(B, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"narration {len(x) / sr:.3f} s, {B['total_frames']} frames -> {nar}")


def plan_cuts(x, sr, B):
    """The cuts (p1, p2 in samples, ok, edge dBs, removed peak, gap length) for a narration and its beats.json; ok ones are applied.
    Deterministic: run on the narration before a tighten, it gives the same cuts, so word times can be shifted by them exactly (a
    Whisper re-sync can move anchors ~0.3 s; shifting the checked words by the cuts keeps the picture on its words)."""
    mono = x.mean(1) if x.ndim > 1 else x
    fpf = sr // FPS
    r = levels(mono, sr)
    bounds = [b["start_f"] * fpf for b in B["beats"][1:]]
    # a HOLD beat (`[S02h] HOLD: 6.0`) is silence on purpose: a clip plays there with its own sound, so no cut touches it
    bb = B["beats"]
    holds = [(b["start_f"] * fpf, (bb[i + 1]["start_f"] * fpf) if i + 1 < len(bb) else len(mono)) for i, b in enumerate(bb) if not (b.get("voice") or "").strip()]
    cuts = []
    for g0, g1 in gaps(r):
        t0, t1 = g0 * HOP, g1 * HOP
        c1, c2 = int((t0 + KEEP_A) * sr), int((t1 - KEEP_B) * sr)
        if c2 - c1 < MIN_CUT_FRAMES * fpf:
            continue
        if any(c1 < h1 and c2 > h0 for h0, h1 in holds):
            continue
        pieces = []
        inside = [bd for bd in bounds if c1 < bd < c2]
        if inside:
            bd = inside[0]
            k1, k2 = (bd - c1) // fpf, (c2 - bd) // fpf
            if k1:
                pieces.append((bd - k1 * fpf, bd))
            if k2:
                pieces.append((bd, bd + k2 * fpf))
        else:
            k = (c2 - c1) // fpf
            pieces.append((c1, c1 + k * fpf))
        def edge(i0, i1):
            return 20 * np.log10(np.sqrt((mono[max(0, i0):i1] ** 2).mean()) + 1e-12)
        for p1, p2 in pieces:
            e1, e2 = edge(p1 - int(0.01 * sr), p1), edge(p2, p2 + int(0.01 * sr))
            for _ in range(int(0.06 * FPS)):   # a soft next word: step the end back, a frame at a time, up to 0.06 s, to a quiet edge
                if e2 <= EDGE or p2 - fpf - p1 < MIN_CUT_FRAMES * fpf:
                    break
                p2 -= fpf
                e2 = edge(p2, p2 + int(0.01 * sr))
            pk = r[int(p1 / sr / HOP):int(p2 / sr / HOP)].max()
            ok = e1 <= EDGE and e2 <= EDGE and pk < BREATH
            cuts.append((p1, p2, ok, e1, e2, pk, t1 - t0))
    return cuts


if __name__ == "__main__":
    main()
