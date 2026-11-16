"""Finish a long video for upload: the Remotion render (any size, PCM sound) -> 3840x2160 60 fps H.264 (upscaled once with lanczos:
YouTube gives 4K uploads its higher bitrate) + AAC 320k, +faststart.
--gpu encodes on an NVIDIA GPU (h264_nvenc, cq 22) instead of x264 slow CRF 16: measured frame by frame against a lossless upscale it
beats x264 on every count (PSNR p5 47.9 vs 46.5 dB, SSIM min 0.9918 vs 0.9881) at 53 vs 31 Mbps, and runs about 6x faster (x264 slow
at 4K60 on a 6-core CPU: ~5.6 fps). On macOS there is no NVENC: --gpu falls back to x264 with a note.

Sound:
- Narrated videos (default): -14 LUFS integrated, true peak under -1 dBTP (two-pass loudnorm).
- **--source-sound** (the recording's own sound only, no voice): one linear gain to --lufs (default -25) and the house limiter on the
  transients (bangs, hits), so the recording keeps its own dynamics. Why: loudnorm would raise a quiet recording (e.g. -31 LUFS) 17 dB
  to -14, and its loudest stretches would then sit near -9 LUFS, louder than a narrated video and hard on the ears. Popular uploads with
  no voice-over measure -17.4 to -31.0 LUFS (median ~-23.5); -25 sits in that range.
--video-from <mp4> copies the video stream of an existing upload file and redoes only the sound (a minute instead of a re-encode).
--gain-only: one gain to --lufs and nothing else (for a mix whose peaks are already limited, e.g. a voice chain that delivers at
-1.5 dBTP: loudnorm's TP=-2 would limit it again, dynamically). The output's true peak is checked after the encode as always.
--patch <segment.mkv>@<second> (repeatable) lays a re-rendered stretch over the picture from that second, frame for frame (the second a
multiple of 1/60): a version's few fixed shots go into the one 4K encode instead of a full re-render (a long render can take hours, the
fixes are seconds long). The segments must match the picture's size (the render's own size, e.g. 1440p). The overlay matches frame
numbers, not times: the picture's own timestamps drift up to 8 ms early by the end of a film (e.g. frame 33584 at 559.726 s), and a
time match lays a patch one frame late (its first frame shown twice), so picture and patches are put on the frame grid first.

  PIPE tools/motion/finish_long.py <render.mkv> <out.mp4> [--height 2160] [--gpu]
      [--source-sound] [--lufs -25] [--gain-only] [--video-from <existing.mp4>] [--patch <segment.mkv>@<second> ...]"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, MAC  # noqa: E402

args = sys.argv
src, out = args[1], args[2]
height = int(args[args.index("--height") + 1]) if "--height" in args else 2160
SOURCE_SOUND = "--source-sound" in args
LUFS = float(args[args.index("--lufs") + 1]) if "--lufs" in args else (-25.0 if SOURCE_SOUND else -14.0)
VIDEO_FROM = args[args.index("--video-from") + 1] if "--video-from" in args else None
PATCHES = [args[i + 1] for i, v in enumerate(args) if v == "--patch"]
SR = 48000
# the peak target sits 1 dB under the -1 dBTP limit: the AAC encode adds overshoot (a quiet recording raised to -14 LUFS came out at
# -0.64 dBTP with TP=-1; with TP=-2, -1.53)
TARGET = f"I={LUFS:g}:TP=-2:LRA=11"
GPU = "--gpu" in args
if GPU and MAC:
    print("--gpu: NVENC is not available on macOS; encoding with x264 slow CRF 16")
    GPU = False
VIDEO = (["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "22", "-b:v", "0", "-maxrate", "200M",
          "-bufsize", "400M", "-spatial-aq", "1", "-temporal-aq", "1", "-rc-lookahead", "32", "-bf", "3", "-b_ref_mode", "middle",
          "-profile:v", "high"] if GPU else ["-c:v", "libx264", "-preset", "slow", "-crf", "16"])


def loudness(path):
    res = subprocess.run([FFMPEG, "-hide_banner", "-i", path, "-vn", "-af", f"loudnorm={TARGET}:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, check=True).stderr
    return json.loads(re.findall(r"\{[^{}]*\}", res)[-1])


m = loudness(src)
print(f"measured: {m['input_i']} LUFS, true peak {m['input_tp']} dBTP, LRA {m['input_lra']} LU")
if "--gain-only" in args:
    gain = LUFS - float(m["input_i"])
    af = f"volume={gain:.2f}dB"
    print(f"one gain: {gain:+.2f} dB to {LUFS:g} LUFS, nothing limited")
elif SOURCE_SOUND:  # one gain, then the house limiter (as finish_short.py): 4x oversampled, -2.5 dBFS, lookahead compensated
    gain = LUFS - float(m["input_i"])
    af = (f"volume={gain:.2f}dB,aresample={SR * 4},alimiter=limit={10 ** (-2.5 / 20):.4f}:attack=0.5:release=60:level=disabled:"
          f"latency=1,aresample={SR}")
    print(f"source sound: +{gain:.2f} dB to {LUFS:g} LUFS, peaks limited")
else:
    af = (f"loudnorm={TARGET}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=summary")
if VIDEO_FROM:  # the picture as it is, only the sound redone
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-stats", "-y", "-i", VIDEO_FROM, "-i", src, "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-af", af, "-ar", str(SR), "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", out]
elif PATCHES:  # the picture with the re-rendered stretches laid over it, then the same scale and encode
    rate = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", src],
                          capture_output=True, text=True, check=True).stdout.strip()
    num, den = (int(x) for x in rate.split("/"))
    if den != 1:
        raise SystemExit(f"--patch needs a whole frame rate, the picture has {rate}")
    ins, fc, last = [], [f"[0:v]settb=1/{num},setpts=N[m]"], "m"   # every frame's time = its number: the overlay matches frames, not drifted times
    for k, ps in enumerate(PATCHES, 1):
        f, at = ps.rsplit("@", 1)
        a = round(float(at) * num)
        if abs(a - float(at) * num) > 0.01:
            raise SystemExit(f"--patch {ps}: {at} s is not on a frame")
        ins += ["-i", f]
        fc.append(f"[{k}:v]settb=1/{num},setpts=N+{a}[p{k}]")
        fc.append(f"[{last}][p{k}]overlay=eof_action=pass:repeatlast=0[b{k}]")
        last = f"b{k}"
        print(f"patch {k}: {f} from frame {a} ({float(at):.3f} s)")
    fc.append(f"[{last}]scale=-2:{height}:flags=lanczos,format=yuv420p[vout]")
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-stats", "-y", "-i", src, *ins, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "0:a:0", *VIDEO,
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-af", af, "-ar", str(SR), "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", out]
else:
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-stats", "-y", "-i", src,
           "-vf", f"scale=-2:{height}:flags=lanczos,format=yuv420p", *VIDEO,
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-af", af, "-ar", str(SR), "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True)
c = loudness(out)
print(f"out: {c['input_i']} LUFS, true peak {c['input_tp']} dBTP -> {out}")
if float(c["input_tp"]) > -1 or abs(float(c["input_i"]) - LUFS) > 0.5:
    print(f"WARNING: outside {LUFS:g} +/- 0.5 LUFS or over -1 dBTP: not ready for upload")
