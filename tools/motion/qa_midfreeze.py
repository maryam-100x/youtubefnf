"""Freezes INSIDE a clip: a clip that plays a little, holds still, then plays on looks broken; there is usually a fluent part of the
source to show instead. The gate's B1 checks a clip's end (FREEZE) and a regular hitch (HOLD), not one held stretch in the middle
(e.g. a clip holding 0.42 s at 0.62 s). For every clip of the composition's prep manifests: ffmpeg mpdecimate drops repeated frames;
a gap of more than --max seconds between two kept frames is a freeze on screen. Exit 1 if any.

  PIPE tools/motion/qa_midfreeze.py <clips dir> <prep manifest json> [...] [--max 0.15] [--only name,...]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402


def gaps(path, mx):
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path), "-vf", "mpdecimate=hi=64*4:lo=64*2:frac=0.33,showinfo", "-f", "null", "-"],
                       capture_output=True, text=True, errors="ignore")
    ts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    return [(round(a, 3), round(b - a, 3)) for a, b in zip(ts, ts[1:]) if b - a > mx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips")
    ap.add_argument("manifests", nargs="+")
    ap.add_argument("--max", type=float, default=0.15)
    ap.add_argument("--only")
    a = ap.parse_args()
    names = set()
    for m in a.manifests:
        names |= set(json.load(open(m, encoding="utf-8")))
    if a.only:
        names &= set(a.only.split(","))
    bad = 0
    for n in sorted(names):
        p = Path(a.clips) / f"{n}.mp4"
        if not p.exists():
            continue
        g = gaps(p, a.max)
        if g:
            bad += 1
            print(f"{n}: " + ", ".join(f"held {d:.2f} s at {t:.2f} s" for t, d in g))
    print(f"{bad} clip(s) with a freeze inside (> {a.max} s) of {len(names)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
