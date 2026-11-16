"""Does the footage in a render move as smoothly as it should? A render made beside other heavy jobs (or on a nearly full disk) can
hold footage frames: the clip's picture stands still for ~10 frames, then jumps, and the footage looks laggy. The same edit rendered
alone is clean.

Compares a render with a reference render of the same edit (the previous version) frame by frame: a frame where the reference's picture
moved but this render's didn't is a held frame. Prints the share per 150-s part and the worst stretches; exits 1 when any part holds more
than 0.5 % of its moving frames. Stretches whose picture was meant to change between the versions are skipped (--skip a-b,c-d in s).

--start / --ref-start (s) line up two edits whose timelines are offset (e.g. a part render starting at 100 s against a reference where
the same shots sit 2.65 s earlier: --ref-start 97.35); --until is then a duration from those starts.

  PIPE tools/motion/qa_cadence.py <render.mp4> <reference.mp4> [--until s] [--skip a-b,...] [--part s] [--start s] [--ref-start s]
  PIPE tools/motion/qa_cadence.py --stutter <render> [<render> ...]   (no reference: holds inside moving footage)"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

W, H, FPS = 160, 90, 60


def framediffs(video, until, start=0.0):
    """Mean absolute change between consecutive frames (grey, 160x90), frame by frame."""
    p = subprocess.Popen([FFMPEG, "-v", "error", "-ss", f"{start}", "-t", f"{until}", "-i", video, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)
    prev, out, n = None, [], W * H
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        f = np.frombuffer(b, np.uint8).astype(np.int16)
        if prev is not None:
            out.append(np.abs(f - prev).mean())
        prev = f
    p.wait()
    return np.array(out)


def stutters(x, low=0.2, moving=0.5):
    """The held-frames fault in one render, with no reference: footage that stands still for 3+ frames inside moving footage, then
    jumps. 30-fps footage in a 60-fps render alternates move/still, single frames only; a static card is a long run with no motion
    around it. The frame after a real hold carries the held frames' motion, so it must jump past twice the motion before it (a card
    that eases to a stop and starts again does not)."""
    out, i, n = [], 0, len(x)
    while i < n:
        if x[i] >= low:
            i += 1
            continue
        j = i
        while j < n and x[j] < low:
            j += 1
        run = j - i
        before, after = x[max(0, i - 12):i], x[j:j + 12]
        if 3 <= run <= 20 and len(before) and len(after) and before.mean() > moving and after.mean() > moving and x[j] > 2 * before.mean():
            out.append((i, run, float(x[j])))
        i = j
    return out


def main():
    if "--stutter" in sys.argv:
        # no reference: a reference whose cues sit a few frames off would count the 30-fps cadence's phase as holds
        bad = False
        for v in [a for a in sys.argv[1:] if a != "--stutter"]:
            x = framediffs(v, 1e9)
            st = stutters(x)
            bad |= bool(st)
            print(f"{v}: {len(x)} frames, {len(st)} stutter(s)")
            for i, r, j in st[:12]:
                print(f"  frame {i} ({i / FPS:.2f} s): still {r} frames, then a jump of {j:.1f}")
        sys.exit(1 if bad else 0)
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("reference")
    ap.add_argument("--until", type=float, default=1e9)
    ap.add_argument("--skip", default="")
    ap.add_argument("--part", type=float, default=150.0)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--ref-start", type=float, default=0.0)
    a = ap.parse_args()
    skip = [tuple(float(v) for v in r.split("-")) for r in a.skip.split(",") if r]
    x, ref = framediffs(a.render, a.until, a.start), framediffs(a.reference, a.until, a.ref_start)
    n = min(len(x), len(ref))
    x, ref = x[:n], ref[:n]
    ok = np.ones(n, bool)
    for s0, s1 in skip:
        ok[int(s0 * FPS):int(s1 * FPS)] = False
    held = (ref >= 0.5) & (x < 0.2) & ok
    moved = (ref >= 0.5) & ok
    bad = False
    for p0 in np.arange(0, n / FPS, a.part):
        i0, i1 = int(p0 * FPS), min(int((p0 + a.part) * FPS), n)
        m, h = int(moved[i0:i1].sum()), int(held[i0:i1].sum())
        share = 100 * h / max(m, 1)
        bad |= share > 0.5
        print(f"{int(p0 // 60)}:{int(p0 % 60):02d}-{int(min(p0 + a.part, n / FPS) // 60)}:{int(min(p0 + a.part, n / FPS) % 60):02d}  "
              f"held {h:5d} of {m:5d} moving frames ({share:.1f}%)")
    per_s = np.bincount(np.nonzero(held)[0] // FPS, minlength=int(n / FPS) + 1)
    worst = np.argsort(per_s)[::-1][:8]
    print("worst seconds:", ", ".join(f"{s // 60}:{s % 60:02d} ({per_s[s]})" for s in sorted(worst) if per_s[s] > 0) or "none")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
