"""A contact sheet of chosen frames and pictures, to compare options by eye: each item is `label=A1@711.2` (a frame of a source video of
kb/footage/sources.json at that second) or `label=<picture path>` (absolute, or relative to FOOTAGE or to the media root).

  PIPE tools/footage/peek.py <out.jpg> item [item ...] [--cols 4] [--w 480]"""
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402


def load(spec, w):
    if "@" in spec and spec.split("@")[0] in B.MASTERS:
        s, t = spec.split("@")
        h = w * 9 // 16
        raw = subprocess.run([B.FFMPEG, "-v", "error", "-ss", t, "-i", str(B.MASTERS[s]["file"]), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        return Image.frombytes("RGB", (w, h), raw)
    p = Path(spec)
    for base in (Path(""), B.FOOTAGE, B.MEDIA):
        if (base / p).exists():
            im = Image.open(base / p).convert("RGB")
            im.thumbnail((w, w))
            return im
    raise FileNotFoundError(spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("items", nargs="+")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--w", type=int, default=480)
    a = ap.parse_args()
    ims = [(it.split("=", 1)[0], load(it.split("=", 1)[1], a.w)) for it in a.items]
    ch = max(im.height for _, im in ims) + 16
    rows = (len(ims) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * a.w, rows * ch), "white")
    d = ImageDraw.Draw(sheet)
    for i, (lab, im) in enumerate(ims):
        x, y = (i % a.cols) * a.w, (i // a.cols) * ch
        sheet.paste(im, (x + (a.w - im.width) // 2, y))
        d.text((x + 3, y + ch - 14), lab, fill="black")
    sheet.save(a.out, quality=85)
    print(len(ims), "->", a.out)


if __name__ == "__main__":
    main()
