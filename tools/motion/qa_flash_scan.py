"""Whole-film flash scan on a finished render (the delivered file itself; qa_flash.py works from the clip audit and finds a source
clip's own cut at a shot's edge, this one finds anything that flashes on screen, whatever made it): a flash frame, a one-frame black,
a sliver of another shot inside a clip, a clip fading up from black, a graphic whose first frame is the empty background.
Per-frame mean luma (GPU decode where there is one, 320x180); a frame is flagged when it jumps from the frame before and sits far
above or below BOTH the three frames before it and the three it settles into: the signature of a bright first frame (55 -> 123 -> 75),
a one-frame black (85 -> 0 -> 85), a dip before a graphic appears (50 -> 30 -> 41 -> 51).
Flags are candidates, not verdicts: a camera flash in the footage, a designed wipe or cars passing the lens also flag. With --sheets,
each flag gets a row of frames k-2 .. k+4 on contact sheets (8 rows each) to look at before deciding.

  EDIT tools/motion/qa_flash_scan.py <render.mp4|mkv> [--sheets <dir>] [--jump 8] [--excursion 12]
Needs numpy and PIL (the editing venv has both); about 9 minutes for a 25-minute 4K60 file with an NVIDIA GPU (CUDA decode on
Windows; on macOS, or with QA_NO_CUDA=1, it decodes on the CPU, slower)."""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, MAC  # noqa: E402

W, H = 320, 180


def lumas(src):
    if MAC or os.environ.get("QA_NO_CUDA") == "1":
        cmd = [FFMPEG, "-v", "error", "-i", src, "-vf", f"scale={W}:{H},format=nv12", "-f", "rawvideo", "-"]
    else:
        cmd = [FFMPEG, "-v", "error", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda", "-i", src, "-vf",
               f"scale_cuda={W}:{H},hwdownload,format=nv12", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    fs = W * H * 3 // 2
    out = []
    while True:
        b = p.stdout.read(fs)
        if len(b) < fs:
            break
        out.append(float(np.frombuffer(b[:W * H], dtype=np.uint8).mean()))
    return np.array(out)


def flags(m, jump, exc):
    hits = []
    for k in range(3, len(m) - 6):
        before, after = m[k - 3:k].mean(), m[k + 3:k + 6].mean()
        up, down = m[k] - max(before, after), min(before, after) - m[k]
        if abs(m[k] - m[k - 1]) > jump and (up > exc or down > exc):
            hits.append((k, up if up > exc else -down))
    return hits


def _font(size):
    from PIL import ImageFont
    for p in ("C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheets(src, ks, fps, out_dir):
    from PIL import Image, ImageDraw
    out_dir.mkdir(parents=True, exist_ok=True)
    w, h, n = 256, 144, 7
    font = _font(18)
    rows = []
    for k in ks:
        raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{(k - 2) / fps:.4f}", "-i", src, "-frames:v", str(n), "-vf", f"scale={w}:{h}",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        row = Image.new("RGB", (w * n + 120, h), "black")
        for i in range(min(n, len(raw) // (w * h * 3))):
            row.paste(Image.frombytes("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]), (120 + i * w, 0))
        t = k / fps
        ImageDraw.Draw(row).text((6, 56), f"{int(t // 60)}:{t % 60:05.2f}", font=font, fill="white")
        rows.append(row)
    for s in range(0, len(rows), 8):
        part = rows[s:s + 8]
        sheet = Image.new("RGB", (part[0].width, (h + 4) * len(part)), (40, 40, 40))
        for i, r in enumerate(part):
            sheet.paste(r, (0, i * (h + 4)))
        sheet.save(out_dir / f"flash_{s // 8}.jpg", quality=85)
    print(f"sheets -> {out_dir}")


def main():
    a = sys.argv[1:]
    src = a[0]
    opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    fps_s = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", src],
                           capture_output=True, text=True, check=True).stdout.strip()
    num, den = fps_s.split("/")
    fps = float(num) / float(den)
    m = lumas(src)
    hits = flags(m, opt("--jump", 8.0), opt("--excursion", 12.0))
    print(f"{len(m)} frames, {len(hits)} flagged")
    for k, s in hits:
        t = k / fps
        print(f"  {int(t // 60)}:{t % 60:06.3f}  frame {k}: {m[k - 1]:5.1f} -> {m[k]:5.1f} {m[k + 1]:5.1f} {m[k + 2]:5.1f}  "
              f"({'bright' if s > 0 else 'dark'} {abs(s):.0f})")
    if "--sheets" in a and hits:
        sheets(src, [k for k, _ in hits], fps, Path(a[a.index("--sheets") + 1]))


if __name__ == "__main__":
    main()
