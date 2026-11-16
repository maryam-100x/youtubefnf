"""The reviewer's eye: every frame of a short window, tiled, to check a flash or a cut frame by frame (no model).

  EDIT tools/eye/eye_strip.py <video.mp4> <t0> <t1> [--out strip.jpg] [--step 1] [--cols 10] [--w 320]
t0/t1 in seconds or m:ss.ss; --step 2 takes every second frame. Each tile carries its frame number and time. Writes <out> (default
strip_<t0>_<t1>.jpg in the current folder) and prints it."""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "footage"))
from paths import FFMPEG, FFPROBE  # noqa: E402
from sheetfont import font  # noqa: E402


def secs(t):
    p = [float(x) for x in str(t).split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("t0")
    ap.add_argument("t1")
    ap.add_argument("--out")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--w", type=int, default=320)
    a = ap.parse_args()
    t0, t1 = secs(a.t0), secs(a.t1)
    pr = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,width,height", "-of",
                         "csv=p=0", a.video], capture_output=True, text=True).stdout.strip().split(",")
    W0, H0 = int(pr[0]), int(pr[1])
    num, den = pr[2].split("/")
    fps = float(num) / float(den)
    w = a.w
    h = int(round(w * H0 / W0))
    n0 = int(round(t0 * fps))
    n1 = int(round(t1 * fps))
    tail = ["-ss", f"{n0 / fps:.4f}", "-i", a.video, "-frames:v", str(n1 - n0 + 1), "-vf", f"scale={w}:{h}:flags=area,format=rgb24",
            "-f", "rawvideo", "-"]
    # the GPU decodes when there is a CUDA one; anywhere else (a Mac) the CPU does
    raw = subprocess.run([FFMPEG, "-v", "error", "-hwaccel", "cuda"] + tail, capture_output=True).stdout
    if len(raw) < w * h * 3:
        raw = subprocess.run([FFMPEG, "-v", "error"] + tail, capture_output=True).stdout
    frames = np.frombuffer(raw, np.uint8)
    count = len(frames) // (w * h * 3)
    frames = frames[:count * w * h * 3].reshape(count, h, w, 3)[::a.step]
    cols = a.cols
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 2), rows * (h + 16)), (20, 20, 20))
    dr = ImageDraw.Draw(sheet)
    f = font(12)
    for k, fr in enumerate(frames):
        n = n0 + k * a.step
        x, y = (k % cols) * (w + 2), (k // cols) * (h + 16)
        sheet.paste(Image.fromarray(fr), (x, y + 14))
        dr.text((x + 2, y), f"f{n}  {n / fps:7.3f}s", fill=(255, 230, 90), font=f)
    out = Path(a.out) if a.out else Path(f"strip_{t0:.2f}_{t1:.2f}.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85)
    print(out, f"{len(frames)} frames")


if __name__ == "__main__":
    main()
