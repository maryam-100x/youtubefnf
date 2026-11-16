"""Measure the edit of any video (the creator's or a reference): every shot, the cut rate over time, a contact sheet of every shot, and
the sound's loudness over time. The numbers a study needs, so craft rules come from measurements, not memory.

  EDIT tools/qa/measure_edit.py <video> <out dir> [--from S] [--to S] [--threshold 27] [--no-audio]

Writes to <out dir>:
  proxy.mp4         a 640-px 30-fps copy (fast to scan; kept for later looks)
  shots.json        [{i, start, end, dur}] from PySceneDetect's ContentDetector (hard cuts)
  stats.md          cuts a minute (whole and per minute), shot lengths (median, quartiles, longest), holds over 4 s
  sheet_NN.jpg      the middle frame of every shot, numbered with its start time, 6 x 5 per sheet
  loudness.json     momentary loudness (LUFS, 400-ms windows every 100 ms) and onset strength per second (busy vs calm sound)
Detection misses dissolves and counts flashes as cuts; the sheets show which is which."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE  # noqa: E402


def run(cmd):
    subprocess.run(cmd, check=True)


def proxy(src, out, a, b):
    if out.exists():
        return
    cmd = [FFMPEG, "-v", "error", "-y"]
    if a:
        cmd += ["-ss", str(a)]
    cmd += ["-i", str(src)]
    if b:
        cmd += ["-t", str(b - (a or 0))]
    cmd += ["-vf", "fps=30,scale='if(gte(iw,ih),640,360)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", str(out)]
    run(cmd)


def shots(path, threshold):
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector
    v = open_video(str(path))
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold, min_scene_len=4))
    sm.detect_scenes(v, show_progress=False)
    sc = sm.get_scene_list()
    out = [{"i": i, "start": round(s.get_seconds(), 3), "end": round(e.get_seconds(), 3), "dur": round(e.get_seconds() - s.get_seconds(), 3)}
           for i, (s, e) in enumerate(sc)]
    if not out:
        dur = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                   capture_output=True, text=True).stdout)
        out = [{"i": 0, "start": 0.0, "end": dur, "dur": dur}]
    return out


def stats(sh, total):
    d = np.array([s["dur"] for s in sh])
    lines = [f"- duration {total:.1f} s, {len(sh)} shots, {max(0, len(sh) - 1) / (total / 60):.1f} cuts a minute",
             f"- shot length: median {np.median(d):.2f} s, quartiles {np.percentile(d, 25):.2f}-{np.percentile(d, 75):.2f} s, "
             f"mean {d.mean():.2f} s, longest {d.max():.2f} s",
             f"- shots under 1 s: {int((d < 1).sum())} ({100 * (d < 1).mean():.0f}%), 1-2 s: {int(((d >= 1) & (d < 2)).sum())}, "
             f"2-4 s: {int(((d >= 2) & (d < 4)).sum())}, 4 s and over: {int((d >= 4).sum())} ({100 * (d >= 4).mean():.0f}%)"]
    per = []
    for m in range(int(np.ceil(total / 60))):
        n = sum(1 for s in sh[1:] if m * 60 <= s["start"] < (m + 1) * 60)
        per.append(n)
    lines.append("- cuts per minute, minute by minute: " + " ".join(str(x) for x in per))
    long_ = [s for s in sh if s["dur"] >= 4]
    if long_:
        lines.append("- holds of 4 s or more: " + ", ".join(f"{s['start']:.1f}s ({s['dur']:.1f})" for s in long_[:40]))
    return "\n".join(lines)


def sheets(path, sh, out):
    from PIL import Image, ImageDraw, ImageFont
    import cv2
    cap = cv2.VideoCapture(str(path))
    try:
        f = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        f = ImageFont.load_default()
    tiles = []
    vw, vh = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    tw, th = (320, 180) if vw >= vh else (180, 320)   # vertical video (Shorts) gets tall tiles
    cols, rows = (6, 5) if vw >= vh else (10, 3)
    for s in sh:
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000 * (s["start"] + s["dur"] / 2))
        ok, fr = cap.read()
        if not ok:
            continue
        im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)).resize((tw, th))
        d = ImageDraw.Draw(im)
        t = s["start"]
        lab = f"#{s['i']} {int(t // 60)}:{t % 60:04.1f} ({s['dur']:.1f}s)"
        d.rectangle([0, 0, min(tw, 8 + 9 * len(lab)), 22], fill=(0, 0, 0))
        d.text((4, 2), lab, fill=(255, 230, 0), font=f)
        tiles.append(im)
    per = cols * rows
    for k in range(0, len(tiles), per):
        page = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
        for j, im in enumerate(tiles[k:k + per]):
            page.paste(im, ((j % cols) * tw, (j // cols) * th))
        page.save(out / f"sheet_{k // per + 1:02d}.jpg", quality=85)


def loudness(path, out):
    import librosa
    import pyloudnorm as pyln
    y = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-ac", "1", "-ar", "22050", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(y, np.float32)
    if not len(x):
        return {}
    sr = 22050
    meter = pyln.Meter(sr, block_size=0.4)
    hop = int(0.1 * sr)
    w = int(0.4 * sr)
    mom = []
    for i in range(0, len(x) - w, hop):
        seg = x[i:i + w]
        try:
            mom.append(round(float(meter.integrated_loudness(seg)), 1))
        except Exception:
            mom.append(-70.0)
    on = librosa.onset.onset_strength(y=x, sr=sr)
    fps = sr / 512
    per_s = [round(float(on[int(s * fps):int((s + 1) * fps)].mean()), 3) for s in range(int(len(on) / fps))]
    res = {"momentary_lufs_100ms": mom, "onset_strength_per_s": per_s}
    (out / "loudness.json").write_text(json.dumps(res), encoding="utf-8")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--from", dest="a", type=float, default=None)
    ap.add_argument("--to", dest="b", type=float, default=None)
    ap.add_argument("--threshold", type=float, default=27.0)
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    px = out / "proxy.mp4"
    proxy(Path(a.video), px, a.a, a.b)
    total = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(px)],
                                 capture_output=True, text=True).stdout)
    sh = shots(px, a.threshold)
    (out / "shots.json").write_text(json.dumps(sh, indent=0), encoding="utf-8")
    st = stats(sh, total)
    sheets(px, sh, out)
    extra = ""
    if not a.no_audio:
        lo = loudness(px, out)
        if lo:
            m = np.array([v for v in lo["momentary_lufs_100ms"] if v > -60])
            extra = (f"\n- loudness (momentary, 400 ms): median {np.median(m):.1f} LUFS, 10th-90th {np.percentile(m, 10):.1f} to "
                     f"{np.percentile(m, 90):.1f}; onset strength per second median {np.median(lo['onset_strength_per_s']):.2f}")
    (out / "stats.md").write_text(f"# {Path(a.video).name}\n{st}{extra}\n", encoding="utf-8")
    print((out / "stats.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
