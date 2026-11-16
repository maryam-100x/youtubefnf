"""The reviewer's eye: one frame of a video at full size, for a closer look at a moment the sheets show small (no model).

  EDIT tools/eye/eye_frame.py <video.mp4> <seconds> [<seconds> ...] [--out DIR] [--w 1920]
Writes <out>/zoom_<seconds>.jpg (default out: the current folder) and prints each path."""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("times", nargs="+", type=float)
    ap.add_argument("--out", default=".")
    ap.add_argument("--w", type=int, default=1920)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for t in a.times:
        dst = out / f"zoom_{t:08.2f}.jpg"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1",
                        "-vf", f"scale={a.w}:-2:flags=lanczos", "-q:v", "3", str(dst)], check=True)
        print(dst)


if __name__ == "__main__":
    main()
