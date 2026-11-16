"""The camera on a card, measured on the render: a smooth zoom and pan reads as one move; a zoom in, a pause and a second zoom in
(or a quick little zoom before the main one) reads as a stutter. Judged by numbers, never by eye on stills: a still can't show a pause.

Every frame of a window (a card's first frame to its last) is matched to the window's first frame (SIFT + a RANSAC similarity on a
1280-px grey copy), which gives per frame:
  zoom    the camera's scale against the first frame
  speed   how fast the picture moves on screen: the mean travel of a grid over the frame's middle 80% from one frame to the next, in
          1080p pixels a second (zoom and pan together: what the eye sees)
A card's camera is ONE MOVE when its speed, smoothed over 5 frames, has one hump. A second hump of at least a quarter of the top speed,
with the speed between them under 40% of the smaller one, is TWO MOVES: the stutter (e.g. a quick 0.2-0.5-s drift to a fifth of the
push, a stop, then the push; or a 0.3-s entry settle against the push). A pan at a steady speed after the push is no hump.

  EDIT tools/motion/qa_zoom.py <video> <windows.json> <out_dir> [--offset <s>] [--tag <name>]
windows.json: [{"name": "2:30 card_launch_day", "t0": 149.9417, "t1": 154.4}, ...]: seconds on the video's timeline; a window starts
on a card's first frame (a shot's `at` from the composition) and should end before the next cut. --offset <s>: the timeline second of
the video's first frame (a patch segment rendered from frame a: a/60). Writes <out_dir>/zoom_<tag>.json (the curves and the verdicts)
and <out_dir>/zoom_<tag>.png (one panel per window), and prints one line per window.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE  # noqa: E402

W, H = 1280, 720
K = 1080 / H                 # speeds in 1080p pixels
SM = 5                       # smoothing (frames)
HUMP, DIP = 0.25, 0.40


def frames(video, t0, n, fps):
    # the frame at t0 first: seek half a frame early (ffmpeg keeps frames at or after the seek point); passthrough, or the raw pipe
    # repeats that first frame to fill the half frame before it (every curve one frame late, with a false stop at its start)
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{max(0.0, t0 - 0.5 / fps):.6f}", "-i", str(video), "-frames:v", str(n),
           "-vf", f"scale={W}:{H}:flags=area,format=gray", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W)


def fps_of(video):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True).stdout.strip()
    a, b = r.split("/")
    return float(a) / float(b)


def detect(sift, img):
    # OpenCV can throw "Unknown C++ exception" on a frame it reads fine a minute later: one retry on a fresh copy
    for _ in range(2):
        try:
            return sift.detectAndCompute(np.ascontiguousarray(img).copy(), None)
        except cv2.error:
            pass
    return [], None


def snap(video, t0, fps, k=3):
    # the window starts on the card's real first frame: the biggest picture change within k frames of t0, when it is a clear cut (a render
    # can cut into a card one frame later than the composition says: a window opening on the clip before it matches nothing)
    if t0 < k / fps:
        return t0, 0
    f = frames(video, t0 - k / fps, 2 * k + 1, fps).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    i = int(np.argmax(d))
    if d[i] >= 8.0 and d[i] >= 3.0 * float(np.median(d)):
        return t0 + (i + 1 - k) / fps, i + 1 - k
    return t0, 0


def measure(video, t0, t1, fps):
    n = max(2, round(t1 * fps) - round(t0 * fps))
    fr = frames(video, t0, n, fps)
    sift = cv2.SIFT_create(nfeatures=4000)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    k0, d0 = detect(sift, fr[0])
    hs = []
    for img in fr:
        k1, d1 = detect(sift, img)
        h = None
        if d0 is not None and d1 is not None and len(k1) >= 8:
            good = [m for m, s in (p for p in bf.knnMatch(d0, d1, k=2) if len(p) == 2) if m.distance < 0.75 * s.distance]
            if len(good) >= 12:
                a = np.float32([k0[m.queryIdx].pt for m in good])
                b = np.float32([k1[m.trainIdx].pt for m in good])
                # a similarity (scale, turn, shift): a camera push and pan on a flat card, steadier than a full homography on a small
                # photo (with 8 free parameters a small photo card reads 100-px/s humps of noise)
                m2, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=4000, confidence=0.999)
                # a fit from too few points, or a scale no camera move makes in one card (a singular fit), is dropped
                sc = float(np.hypot(m2[0, 0], m2[1, 0])) if m2 is not None else 0.0
                if m2 is not None and inl is not None and int(inl.sum()) >= 12 and 0.5 < sc < 2.5:
                    h = np.vstack([m2, [0.0, 0.0, 1.0]])
        hs.append(h if h is not None else (hs[-1] if hs else np.eye(3)))
    # zoom: a 200-px square at the frame's centre mapped back to the first frame, area ratio
    c = np.float32([[W / 2 - 100, H / 2 - 100], [W / 2 + 100, H / 2 - 100], [W / 2 + 100, H / 2 + 100], [W / 2 - 100, H / 2 + 100]]).reshape(-1, 1, 2)
    zoom = []
    for h in hs:
        q = cv2.perspectiveTransform(c, np.linalg.inv(h)).reshape(-1, 2)
        area = 0.5 * abs(np.dot(q[:, 0], np.roll(q[:, 1], 1)) - np.dot(q[:, 1], np.roll(q[:, 0], 1)))
        zoom.append(float(np.sqrt(200 * 200 / max(area, 1e-6))))
    # speed: a grid over the middle 80%, carried from frame i to frame i+1 through the first frame
    gx, gy = np.meshgrid(np.linspace(0.1 * W, 0.9 * W, 9), np.linspace(0.1 * H, 0.9 * H, 7))
    g = np.float32(np.stack([gx.ravel(), gy.ravel()], 1)).reshape(-1, 1, 2)
    speed = [0.0]
    for i in range(1, len(hs)):
        p = cv2.perspectiveTransform(g, np.linalg.inv(hs[i - 1]))
        q = cv2.perspectiveTransform(p, hs[i])
        speed.append(float(np.mean(np.linalg.norm((q - g).reshape(-1, 2), axis=1)) * K * fps))
    speed[0] = speed[1] if len(speed) > 1 else 0.0
    return zoom, speed


def humps(s):
    # a hump is a peak of at least HUMP of the top speed; two humps are two such peaks with a trough between them under DIP of each
    # (a speed that only falls after its peak is one hump). qa_camera.mjs applies the same rule to the code's own camera.
    top = float(s.max()) if len(s) else 0.0
    if top < 1.0:
        return []
    hs, up, pk, pi, low, lows = [], False, 0.0, 0, 0.0, []
    for k, v in enumerate(s):
        if up:
            if v > pk:
                pk, pi = v, k
            if v < DIP * pk:
                hs.append((pi, float(pk)))
                up, low = False, v
        else:
            low = min(low, v)
            if v >= HUMP * top and low <= DIP * v:
                if hs:
                    lows.append(float(low))
                up, pk, pi = True, v, k
    if up:
        hs.append((pi, float(pk)))
    return [(a, p, lows[i - 1] if i else None) for i, (a, p) in enumerate(hs)]


def verdict(speed):
    s = np.convolve(np.pad(np.asarray(speed, float), SM // 2, mode="edge"), np.ones(SM) / SM, mode="valid")
    h = humps(s)
    if not h:
        return "still", [], s
    if len(h) == 1:
        return "one move", [], s
    return "TWO MOVES", [(h[i][0], h[i + 1][0], h[i + 1][2]) for i in range(len(h) - 1)], s


def main():
    args = sys.argv[1:]
    video, wins_p, out = Path(args[0]), Path(args[1]), Path(args[2])
    off = float(args[args.index("--offset") + 1]) if "--offset" in args else 0.0
    tag = args[args.index("--tag") + 1] if "--tag" in args else video.stem
    out.mkdir(parents=True, exist_ok=True)
    fps = fps_of(video)
    wins = json.loads(wins_p.read_text(encoding="utf-8"))
    res = []
    for w in wins:
        t0, moved = snap(video, float(w["t0"]) - off, fps)
        if moved:
            print(f"{w['name']}: the cut is {moved:+d} frame(s) from the window's start; measured from the cut", flush=True)
        zoom, speed = measure(video, t0, float(w["t1"]) - off, fps)
        v, info, sm = verdict(speed)
        if v == "TWO MOVES":
            det = "; ".join(f"humps at {a / fps:.2f} s ({sm[a]:.0f} px/s) and {b / fps:.2f} s ({sm[b]:.0f} px/s), down to {m:.0f} px/s between"
                            for a, b, m in info)
        elif v == "one move":
            det = f"peak {sm.max():.0f} px/s at {int(np.argmax(sm)) / fps:.2f} s"
        else:
            det = "no motion"
        print(f"{w['name']}: {v}  zoom {zoom[0]:.3f} -> {max(zoom):.3f}; {det}", flush=True)
        res.append({"name": w["name"], "t0": w["t0"], "t1": w["t1"], "fps": fps, "verdict": v, "detail": det, "zoom": zoom, "speed": speed,
                    "speed_smooth": [float(x) for x in sm]})
    (out / f"zoom_{tag}.json").write_text(json.dumps(res), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(res), 2, figsize=(13, 2.3 * len(res)), squeeze=False)
    for r, (az, av) in zip(res, axs):
        t = np.arange(len(r["zoom"])) / r["fps"]
        az.plot(t, r["zoom"], color="#1f6feb", lw=1.6)
        az.set_ylabel("zoom")
        az.set_title(f"{r['name']}: zoom", fontsize=9, loc="left")
        av.plot(t, r["speed"], color="#bbbbbb", lw=0.8)
        av.plot(t, r["speed_smooth"], color="#d6336c" if r["verdict"] == "TWO MOVES" else "#2f9e44", lw=1.8)
        av.set_ylabel("px/s (1080p)")
        av.set_title(f"screen speed: {r['verdict']}", fontsize=9, loc="left")
        for a in (az, av):
            a.grid(alpha=0.3)
            a.set_xlim(0, t[-1])
    axs[-1][0].set_xlabel("seconds into the card")
    axs[-1][1].set_xlabel("seconds into the card")
    fig.tight_layout()
    fig.savefig(out / f"zoom_{tag}.png", dpi=110)
    print(f"-> {out / f'zoom_{tag}.png'}")


if __name__ == "__main__":
    main()
