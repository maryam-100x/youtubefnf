"""A stretch of a video as a dense contact sheet (frames every --step s, the time under each), to find a short moment by eye (a
hand reaching, a lid coming off, a turn of the head) out of all the frames around it, not the first that roughly fits.

  PIPE tools/footage/scan.py <video> <from s> <to s> <out.jpg> [--step 0.25] [--cols 8]     (--step 0.033 at 30 fps: frame by frame)"""
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("a", type=float)
    ap.add_argument("b", type=float)
    ap.add_argument("out")
    ap.add_argument("--step", type=float, default=0.25)
    ap.add_argument("--cols", type=int, default=8)
    o = ap.parse_args()
    TW, TH = (240, 135) if o.step < 0.5 else (176, 99)
    n = int((o.b - o.a) / o.step) + 1
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{o.a:.3f}", "-t", f"{o.b - o.a:.3f}", "-i", o.video, "-vf",
                          f"fps={1 / o.step},scale={TW}:{TH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    frames = [raw[i:i + TW * TH * 3] for i in range(0, len(raw), TW * TH * 3)][:n]
    rows = (len(frames) + o.cols - 1) // o.cols
    sheet = Image.new("RGB", (o.cols * TW, rows * (TH + 14)), "white")
    d = ImageDraw.Draw(sheet)
    for i, fr in enumerate(frames):
        if len(fr) < TW * TH * 3:
            continue
        x, y = (i % o.cols) * TW, (i // o.cols) * (TH + 14)
        sheet.paste(Image.frombytes("RGB", (TW, TH), fr), (x, y))
        t = o.a + i * o.step
        d.text((x + 3, y + TH + 1), f"{int(t // 60)}:{t % 60:05.2f}", fill="black")
    sheet.save(o.out, quality=85)
    print(len(frames), "frames ->", o.out)


if __name__ == "__main__":
    main()
