"""Contact sheets of a render for review: frames every 1/fps s between start and end, labelled with their video time, 6 per row,
48 per sheet. Writes <out_dir>/<name>_<n>.jpg (out_dir: PUBLIC/review) and prints the paths.

  PIPE tools/motion/qa_sheet.py <video> <start_s> <end_s> [fps=2] [offset_s=0] [name]
offset_s = the video time of the file's first frame (a part render that starts later in the video). The frames are read by the
editing python (OpenCV)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import PUBLIC, PY_EDIT  # noqa: E402

CODE = r"""
import cv2, sys, numpy as np
video, t0, t1, fps, off, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
cap = cv2.VideoCapture(video)
vfps = cap.get(cv2.CAP_PROP_FPS)
times, t = [], t0
while t < t1 - 1e-6:
    times.append(t); t += 1 / fps
W, H, COLS, PER = 320, 180, 6, 48
paths = []
for s in range(0, len(times), PER):
    tiles = []
    for tt in times[s:s + PER]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((tt - off) * vfps)))
        ok, fr = cap.read()
        fr = cv2.resize(fr, (W, H)) if ok else np.zeros((H, W, 3), np.uint8)
        cv2.rectangle(fr, (0, 0), (92, 22), (0, 0, 0), -1)
        cv2.putText(fr, f"{int(tt // 60)}:{tt % 60:05.2f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 255, 80), 1)
        tiles.append(fr)
    while len(tiles) % COLS:
        tiles.append(np.zeros((H, W, 3), np.uint8))
    rows = [np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)]
    p = f"{out}_{s // PER + 1}.jpg"
    cv2.imwrite(p, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
    paths.append(p)
print("\n".join(paths))
"""


def main():
    a = sys.argv[1:]
    video, t0, t1 = a[0], a[1], a[2]
    fps = a[3] if len(a) > 3 else "2"
    off = a[4] if len(a) > 4 else "0"
    name = a[5] if len(a) > 5 else Path(video).stem
    out = PUBLIC / "review" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(PY_EDIT), "-c", CODE, video, t0, t1, fps, off, str(out)], check=True)


if __name__ == "__main__":
    main()
