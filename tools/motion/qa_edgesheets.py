"""Every EDGE flag of `pipe.py <video> audit` shown on the render: one row of frames per flag, around the flagged cut.

The static audit lists each play whose span comes within 0.5 s of a cut in its source ("opens on 0.27 s of the shot before", "ends on
0.23 s of the next shot", "opens in a fade"). Many are not faults (a source with choppy scrolling scores a cut on every frame, a
deliberate switch effect, a quick cut between two shots of the same action), so each one is looked at, never fixed blind. Real ones
(a 0.1-0.3 s sliver of another shot, a clip opening on a fade from black) are typically a small share of the flags, and the plays
sheets' first, middle and last frames miss them.

  EDIT tools/motion/qa_edgesheets.py <audit output .txt> <render.mkv|mp4> <out dir> [--per 8]

<audit output .txt> is the text `pipe.py <video> audit` printed (redirect it to a file). Rows: the shot, its time, the clip, the flag;
then up to 14 frames at 30 fps from 0.1 s before the cut to the edge (an "opens" row starts 0.1 s before the shot). Read each row: a
frame of a different picture inside the shot is a sliver; fix the span (prep's MANUAL), re-audit, patch the range.
Runs with the editing venv (numpy, Pillow).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

W, H, N = 192, 108, 14
FLAG = re.compile(r"EDGE (\d+):([\d.]+) shot (\d+): (\S+) ([\d.]+)-([\d.]+): (.*)")


def rows_of(audit_txt):
    rows = []
    for ln in Path(audit_txt).read_text(encoding="utf-8", errors="replace").splitlines():
        m = FLAG.match(ln)
        if not m:
            continue
        at = int(m.group(1)) * 60 + float(m.group(2))
        shot, clip, dur, rest = int(m.group(3)), Path(m.group(4)).stem, float(m.group(6)), m.group(7)
        for c in re.findall(r"opens on [\d.]+ s of the shot before \(cut at ([\d.]+)\)", rest):
            rows.append((shot, clip, "opens", at, at - 0.1, at + float(c) + 0.1))
        for c in re.findall(r"ends on [\d.]+ s of the next shot \(cut at ([\d.]+)\)", rest):
            rows.append((shot, clip, "ends", at, at + float(c) - 0.1, at + dur + 0.1))
        for kind, a, b in re.findall(r"(opens|ends) in a fade or flicker \([^,]*, ([\d.]+)-([\d.]+)\)", rest):
            rows.append((shot, clip, kind + " in a fade", at, at + float(a) - 0.05, at + float(b) + 0.1))
    return rows


def frames(render, a, b):
    step = max(1.0 / 30, (b - a) / N)
    out, t = [], a
    while t < b and len(out) < N:
        r = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i", render, "-frames:v", "1", "-vf", f"scale={W}:{H}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        if len(r.stdout) == W * H * 3:
            out.append((t, Image.fromarray(np.frombuffer(r.stdout, np.uint8).reshape(H, W, 3))))
        t += step
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audit")
    ap.add_argument("render")
    ap.add_argument("out")
    ap.add_argument("--per", type=int, default=8, help="rows per sheet")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = rows_of(a.audit)
    for k in range(0, len(rows), a.per):
        chunk = rows[k:k + a.per]
        sheet = Image.new("RGB", (W * N + 230, (H + 4) * len(chunk)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, (shot, clip, kind, at, t0, t1) in enumerate(chunk):
            y = i * (H + 4)
            d.text((4, y + 4), f"shot {shot}\n{int(at // 60)}:{at % 60:05.2f}\n{clip}\n{kind}\n{t0:.2f}-{t1:.2f}", fill=(255, 220, 0))
            for j, (t, im) in enumerate(frames(a.render, t0, t1)):
                sheet.paste(im, (230 + j * W, y))
                d.text((232 + j * W, y + 2), f"{t:.2f}", fill=(255, 255, 0))
        p = out / f"edges_{k // a.per:02d}.jpg"
        sheet.save(p, quality=85)
        print(p, len(chunk))
    print(f"{len(rows)} edge(s) in {(len(rows) + a.per - 1) // a.per} sheet(s): read every row")


if __name__ == "__main__":
    main()
