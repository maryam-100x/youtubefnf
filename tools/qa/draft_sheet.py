"""Contact sheets of a draft render, one frame a second (or --step), each stamped with its time in the full video, for reading a chapter
against its words before the final render (a 2-fps sheet read against the words catches a picture that misses its line).

  EDIT tools/qa/draft_sheet.py <draft.mp4> <out prefix> [--t0 <seconds the draft starts at>] [--step 1.0]"""
import argparse

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("out")
ap.add_argument("--t0", type=float, default=0.0)
ap.add_argument("--step", type=float, default=1.0)
a = ap.parse_args()
cap = cv2.VideoCapture(a.video)
fps = cap.get(cv2.CAP_PROP_FPS)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
W, H, C, R = 384, 216, 8, 7
frames, t = [], 0.5 * a.step
while t < n / fps:
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
    ok, f = cap.read()
    if not ok:
        break
    f = cv2.resize(f, (W, H))
    cv2.rectangle(f, (0, 0), (84, 20), (0, 0, 0), -1)
    cv2.putText(f, f"{a.t0 + t:6.1f}", (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    frames.append(f)
    t += a.step
for k in range(0, len(frames), C * R):
    g = np.zeros((H * R, W * C, 3), np.uint8)
    for i, f in enumerate(frames[k:k + C * R]):
        g[(i // C) * H:(i // C + 1) * H, (i % C) * W:(i % C + 1) * W] = f
    cv2.imwrite(f"{a.out}{k // (C * R) + 1}.jpg", g, [cv2.IMWRITE_JPEG_QUALITY, 82])
print(len(frames), "frames ->", a.out + "*.jpg")
