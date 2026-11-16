"""Where does a render hold one picture too long? A good Short cuts or changes in some significant way every 2-3 seconds; a picture
that sits for 6 seconds loses the viewer.

Reads the render small (grey, 90x160 for a Short, its caption band masked) and marks a change wherever the picture jumps: a hard cut, or a pop-in (a picture, a window, a
card) that changes a big part of the frame within 0.2 s. Moving footage and slow zooms are not changes. Prints every stretch between
changes that is longer than --max (default 2.6 s) and exits 1 if there is any.

  PIPE tools/motion/qa_holds.py <render.mp4> [...] [--max 2.6] [--skip-end 1.0]"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE  # noqa: E402

FPS = 60
MASK = (0.44, 0.56)   # the Shorts' caption band (y ~880-1040 of 1920): words changing there are not a change of picture


def frames(video):
    wh = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", video],
                        capture_output=True, text=True).stdout.strip().split(",")
    vertical = int(wh[1]) > int(wh[0])
    W, H = (90, 160) if vertical else (160, 90)
    keep = np.ones(H, bool)
    if vertical:
        keep[int(MASK[0] * H):int(MASK[1] * H)] = False
    p = subprocess.Popen([FFMPEG, "-v", "error", "-i", video, "-vf", f"fps={FPS},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)
    n = W * H
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).astype(np.int16).reshape(H, W)[keep]


def changes(video, cut=14.0, pop=0.18):
    """times (s) of the changes: a frame-to-frame mean change above `cut`, or a share above `pop` of the pixels changing by more than 40
    levels against the picture 0.2 s earlier (a pop-in)"""
    hist, out, last = [], [], -1.0
    for i, f in enumerate(frames(video)):
        t = i / FPS
        hit = False
        if hist:
            if np.abs(f - hist[-1]).mean() > cut:
                hit = True
            elif len(hist) >= 12 and (np.abs(f - hist[-12]) > 40).mean() > pop:
                hit = True
        if hit and t - last > 0.15:
            out.append(t)
            last = t
        hist.append(f)
        if len(hist) > 12:
            hist.pop(0)
    return out, i / FPS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--max", type=float, default=2.6)
    ap.add_argument("--skip-end", type=float, default=0.0, help="ignore a hold that ends within this many seconds of the end")
    a = ap.parse_args()
    bad = 0
    for v in a.videos:
        ch, dur = changes(v)
        edges = [0.0] + ch + [dur]
        holds = [(x, y) for x, y in zip(edges, edges[1:]) if y - x > a.max and not (dur - y < a.skip_end and y == dur)]
        gaps = np.diff(edges)
        print(f"{v}: {len(ch)} changes in {dur:.1f} s, median gap {np.median(gaps):.2f} s, longest {gaps.max():.2f} s; over {a.max} s: "
              + (", ".join(f"{x:.2f}-{y:.2f} ({y - x:.1f})" for x, y in holds) or "none"))
        bad += len(holds)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
