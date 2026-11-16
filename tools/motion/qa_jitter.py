"""The twitch check for a built Short: every footage shot's frame-to-frame shift measured on the render (phase correlation, grey,
270x480), so a picture that vibrates on screen is caught before anyone watches. A 30-fps clip in a 60-fps Short shows each
frame twice; a window that moves every frame over a picture that itself moves every second frame makes the shift go back and forth
(-3, +5, -3, +5 ...): the twitch. A clip's own 30-fps motion (6, 0, 6, 0) is not one. Flagged: a shot whose shift changes sign on 25%+
of its frames with a zig-zag of 0.5 px or more (x or y, at 270 px wide: x4 at full size). The fix: the Pic component's `lock`.

  EDIT tools/motion/qa_jitter.py <render.mp4> <auditat_<Comp>.json>
  (the json: tools/motion/out/auditat_<Comp>.json, written by frame_review_at.py or audit_short.py)   exit 1 when a shot is flagged"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

W, H = 270, 480
WIN = np.hanning(W)[None, :] * np.hanning(H)[:, None]


def frames(video, a, b):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{a}", "-t", f"{b - a}", "-i", video, "-vf", f"scale={W}:{H},format=gray",
                          "-fps_mode", "passthrough", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def shift(p, q):
    F = np.fft.fft2(p * WIN) * np.conj(np.fft.fft2(q * WIN))
    r = np.fft.ifft2(F / (np.abs(F) + 1e-6)).real
    y, x = np.unravel_index(np.argmax(r), r.shape)
    return (x if x < W // 2 else x - W), (y if y < H // 2 else y - H)


def zig(v):
    """half the gap between the even and the odd frames' mean shift, and the share of frames whose shift changes sign"""
    if len(v) < 4:
        return 0.0, 0.0
    flips = sum(1 for i in range(1, len(v)) if v[i] * v[i - 1] < 0) / (len(v) - 1)
    return abs(v[0::2].mean() - v[1::2].mean()) / 2, flips


def main():
    video, plays = sys.argv[1], sys.argv[2]
    d = json.load(open(plays, encoding="utf-8"))
    seen, bad = set(), 0
    print(f"{'at':>6}  {'clip':26s} {'move':5s} {'zig x':>6} {'flips':>6} {'zig y':>6} {'flips':>6}   (px at 270 wide; x4 at full size)")
    for f in sorted(d["frames"], key=lambda f: f["at"]):
        if not f["video"] or "blur" in (f.get("filter") or ""):
            continue
        k = (round(f["at"], 3), f["src"])
        if k in seen or f["len"] < 0.3:
            continue
        seen.add(k)
        fr = frames(video, f["at"] + 0.05, f["at"] + f["len"] - 0.05)
        s = [shift(fr[i], fr[i - 1]) for i in range(1, len(fr))]
        (zx, fx), (zy, fy) = zig(np.array([v[0] for v in s], float)), zig(np.array([v[1] for v in s], float))
        move = "path" if f.get("path") else ("pan" if f.get("fx1") is not None else "push")
        flag = (fx >= 0.25 and zx >= 0.5) or (fy >= 0.25 and zy >= 0.5)
        bad += flag
        print(f"{f['at']:6.2f}  {f['src'].split('/')[-1]:26s} {move:5s} {zx:6.2f} {fx:6.0%} {zy:6.2f} {fy:6.0%}{'  <-- TWITCH' if flag else ''}")
    print(f"{len(seen)} footage shots, {bad} twitching")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
