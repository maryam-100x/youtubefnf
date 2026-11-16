"""QA of a finished long render (the Remotion pipeline), from the MP4 itself:
- format: size, fps, frame count, colour tags, the audio's length against the picture's;
- sync: the narration against the mix's audio, per 20-s window (cross-correlation, +-100 ms): every window must be 0 ms;
- the audio decodes whole and ffmpeg reports no decode errors;
- never absolute silence: no 50 ms of the mix under -50 dBFS (the last half-second's fade aside);
- black frames (blackdetect) and frozen picture (freezedetect, >= 1 s) listed with their video times, for a look at each;
- loudness: integrated LUFS and true peak.

  PIPE tools/motion/qa_full.py <video.mp4> <narration.wav> [--t 60]"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFPROBE, TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
from dj.core import ffmpeg_bin, loudness  # noqa: E402

SR = 48000


def pcm(path, t=None):
    cmd = [ffmpeg_bin(), "-v", "error", "-i", str(path)] + (["-t", str(t)] if t else []) + ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).astype(np.float64)


def probe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-count_packets", "-show_entries",
                          "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_packets,pix_fmt,color_space,color_primaries,"
                          "color_transfer,sample_rate,channels:format=duration", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("narration")
    ap.add_argument("--t", type=float, default=None, help="check only the first T seconds")
    a = ap.parse_args()
    p = probe(a.video)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    au = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    num, den = map(int, v["r_frame_rate"].split("/"))
    fps = num / den
    print(f"video {v['codec_name']} {v['width']}x{v['height']} {fps:g} fps, {v.get('nb_read_packets')} frames, {v.get('pix_fmt')} "
          f"{v.get('color_space')}/{v.get('color_primaries')}/{v.get('color_transfer')} | audio {au and au['codec_name']} {au and au['sample_rate']} Hz "
          f"x{au and au['channels']} | duration {float(p['format']['duration']):.3f} s")

    mix = pcm(a.video, a.t)
    nar = pcm(a.narration, a.t)
    print(f"audio {len(mix) / SR:.3f} s, narration {len(nar) / SR:.3f} s, picture {int(v.get('nb_read_packets') or 0) / fps:.3f} s")
    # sync per 20-s window
    lags, W, M = [], 20 * SR, int(0.1 * SR)
    for s0 in range(0, min(len(mix), len(nar)) - W, W):
        x, y = mix[s0:s0 + W], nar[s0:s0 + W]
        if np.abs(y).mean() < 1e-3:
            continue
        n = 1 << (2 * W - 1).bit_length()
        c = np.fft.irfft(np.fft.rfft(x, n) * np.conj(np.fft.rfft(y, n)), n)
        lags.append(float(round((np.argmax(np.concatenate([c[-M:], c[:M + 1]])) - M) / SR * 1000, 1)))
    print(f"sync (ms, per 20 s): {sorted(set(lags))} over {len(lags)} windows")
    err = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(a.video)] + (["-t", str(a.t)] if a.t else []) + ["-f", "null", "-"],
                         capture_output=True, text=True).stderr.strip()
    print(f"decode errors: {err[:300] or 'none'}")
    # absolute silence: 50-ms windows under -50 dBFS (stereo mix folded to mono; the last 0.5 s is the fade)
    hop = int(0.05 * SR)
    k = len(mix) // hop
    lv = 20 * np.log10(np.sqrt((mix[:k * hop].reshape(k, hop) ** 2).mean(1)) + 1e-12)
    end = len(mix) / SR - 0.5
    quiet = [round(i * hop / SR, 2) for i in np.where(lv < -50)[0] if i * hop / SR < end]
    print(f"silence (50 ms under -50 dBFS): {len(quiet)} windows {quiet[:20]}")
    # black and frozen picture
    vf = "blackdetect=d=0.08:pix_th=0.06,freezedetect=n=-55dB:d=1"
    log = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(a.video)] + (["-t", str(a.t)] if a.t else []) +
                         ["-vf", vf, "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", log)
    print(f"black stretches: {len(blacks)}")
    for b0, b1, d in blacks:
        print(f"   black {float(b0):8.3f} -> {float(b1):8.3f} ({float(d):.3f} s)")
    fs = re.findall(r"freeze_start: ([\d.]+)", log)
    fe = re.findall(r"freeze_end: ([\d.]+)", log)
    print(f"frozen stretches (>= 1 s): {len(fs)}")
    for i, s in enumerate(fs):
        e = fe[i] if i < len(fe) else "end"
        print(f"   frozen {float(s):8.3f} -> {e}")
    if not a.t:
        m = loudness(a.video)
        print(f"loudness {float(m['input_i']):.1f} LUFS, true peak {float(m['input_tp']):.1f} dBTP, LRA {float(m['input_lra']):.1f} LU")


if __name__ == "__main__":
    main()
