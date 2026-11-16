"""A spot fix in minutes: lay patch segments (`pipe.py patch`) into a DELIVERED upload file by re-encoding only the stretch around each
patch, from one keyframe to the next, and copying everything else as it is (the picture stream copied, the sound copied whole).
`finish_long.py --patch` encodes the whole 4K file again: a 2.7-s patch renders in ~20 s and then the full encode takes ~15 min.

  PIPE tools/motion/splice_patch.py <delivered.mp4> <picture.mkv> <patches.json> <out.mp4>

<picture.mkv> is the render the delivered file was finished from (pipe's render/v<N>_picture.mkv, 1440p): the stretch is rebuilt from it
exactly as finish_long builds it (patch laid over, lanczos to 2160, the same encoder settings: h264_nvenc, or on macOS finish_long's
x264 fallback), so the new frames are first-generation, not a re-encode of the delivered 4K. How it joins: the delivered picture is cut
at its own keyframes with the segment muxer (no re-encode), the pieces a patch touches are replaced by the rebuilt stretch, the concat
demuxer joins them, and the delivered sound is mapped in unchanged. The check after: the same frame count as the delivered file; every
frame of a stretch that no new patch covers still the delivered picture (a patch an earlier version laid in must be passed again, or it
fails here); the frames around each seam. Measured: about 1 min against the full finish's ~15 min, the patch on its exact frame,
everything outside the stretch bit-identical to the delivered file, the joins decode clean."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, MAC  # noqa: E402

FPS = 60
# finish_long.py's encoder, word for word (a stretch must decode like the stream around it): --gpu's NVENC, or on macOS (no NVENC)
# the x264 that finish_long falls back to there
VIDEO = (["-c:v", "libx264", "-preset", "slow", "-crf", "16"] if MAC else
         ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "22", "-b:v", "0", "-maxrate", "200M",
          "-bufsize", "400M", "-spatial-aq", "1", "-temporal-aq", "1", "-rc-lookahead", "32", "-bf", "3", "-b_ref_mode", "middle",
          "-profile:v", "high"])
COLOR = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def probe(path, entries, extra=()):
    r = run([FFPROBE, "-v", "error", "-select_streams", "v:0", *extra, "-show_entries", entries, "-of", "json", path],
            capture_output=True, text=True)
    return json.loads(r.stdout)


def keyframes(path):
    """Every keyframe's frame number (the picture's timestamps are multiples of 1/60 from 0)."""
    fr = probe(path, "frame=pts_time", ("-skip_frame", "nokey"))["frames"]
    return sorted({round(float(f["pts_time"]) * FPS) for f in fr})


def frame_count(path):
    r = run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of",
             "csv=p=0", path], capture_output=True, text=True)
    return int(r.stdout.strip())


def frame_times(path):
    """Every frame's own time (s), in display order: a render's picture drifts up to 8 ms early by a film's end, so a frame is
    found by its own timestamp, never by number / fps."""
    r = run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", path],
            capture_output=True, text=True)
    return sorted(float(x) for x in r.stdout.split() if x.strip() and x.strip() != "N/A")


def grab(path, f0, n, w=960, h=540):
    t0 = max(0.0, f0 / FPS - 1.0)
    skip = round(f0 - t0 * FPS)
    raw = run([FFMPEG, "-v", "error", "-ss", f"{t0:.6f}", "-i", path, "-vf", f"select='gte(n\\,{skip})',scale={w}:{h}", "-vsync", "0",
               "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.int16)


def main():
    delivered, picture, patches_json, out = (Path(a) for a in sys.argv[1:5])
    patches = json.loads(patches_json.read_text(encoding="utf-8"))
    total = frame_count(delivered)
    keys = keyframes(delivered)
    if keys[0] != 0:
        raise SystemExit(f"{delivered}: the first keyframe is at frame {keys[0]}, not 0")
    # each patch's frames, then the stretch from the keyframe at or before its first frame to the first keyframe after its last
    spans = []
    for p in patches:
        a = round(float(p["at"]) * FPS)
        n = frame_count(p["file"])
        b = a + n   # one past the patch's last frame
        k0 = max(k for k in keys if k <= a)
        k1 = min([k for k in keys if k >= b] or [total])
        spans.append([k0, k1, [(p["file"], a)]])
    spans.sort()
    merged = []
    for s in spans:   # stretches that touch or overlap become one
        if merged and s[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], s[1])
            merged[-1][2] += s[2]
        else:
            merged.append(s)
    for k0, k1, ps in merged:
        print(f"stretch {k0}-{k1} ({(k1 - k0) / FPS:.2f} s from {k0 / FPS:.3f} s) for patch(es) at {', '.join(str(a) for _, a in ps)}")

    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        tmp = Path(tmp)
        # the delivered picture cut at every stretch's keyframes, stream copied (each piece starts on its keyframe)
        cuts = sorted({k for k0, k1, _ in merged for k in (k0, k1) if 0 < k < total})
        seg = tmp / "piece_%03d.mp4"
        # (a delivered file's frames sit exactly on the grid; each cut time a quarter frame early, so it falls on keyframe k itself)
        run([FFMPEG, "-v", "error", "-y", "-i", delivered, "-map", "0:v:0", "-c", "copy", "-f", "segment", "-segment_times",
             ",".join(f"{(k - 0.25) / FPS:.6f}" for k in cuts), "-reset_timestamps", "1", seg])
        pieces = sorted(tmp.glob("piece_*.mp4"))
        bounds = [0, *cuts, total]
        if len(pieces) != len(bounds) - 1:
            raise SystemExit(f"segment muxer made {len(pieces)} pieces for {len(bounds) - 1} spans")
        for p, a, b in zip(pieces, bounds, bounds[1:]):
            n = frame_count(p)
            if n != b - a:
                raise SystemExit(f"{p.name}: {n} frames, {b - a} expected (a cut off its keyframe?)")
        # rebuild each stretch from the render picture, as finish_long does: the picture entered at frame k0's own timestamp, then picture
        # and patches on the frame grid (setpts=N), so the overlay matches frame numbers
        ptimes = frame_times(picture)
        if len(ptimes) != total:
            raise SystemExit(f"{picture}: {len(ptimes)} frames, the delivered file {total}: not the picture it was finished from")
        new = {}
        for i, (k0, k1, ps) in enumerate(merged):
            ins, fc, last = [], [f"[0:v]settb=1/{FPS},setpts=N[m]"], "m"
            for j, (f, a) in enumerate(ps, 1):
                ins += ["-i", f]
                fc.append(f"[{j}:v]settb=1/{FPS},setpts=N+{a - k0}[p{j}]")
                fc.append(f"[{last}][p{j}]overlay=eof_action=pass:repeatlast=0[b{j}]")
                last = f"b{j}"
            fc.append(f"[{last}]scale=-2:2160:flags=lanczos,format=yuv420p[vout]")
            dst = tmp / f"stretch_{i}.mp4"
            run([FFMPEG, "-v", "error", "-y", "-ss", f"{ptimes[k0] - 0.0005:.6f}", "-i", picture, *ins, "-filter_complex", ";".join(fc),
                 "-map", "[vout]", "-frames:v", str(k1 - k0), *VIDEO, *COLOR, "-an", dst])
            n = frame_count(dst)
            if n != k1 - k0:
                raise SystemExit(f"{dst.name}: {n} frames, {k1 - k0} expected")
            new[k0] = dst
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{(new.get(a) or p).as_posix()}'\n" for p, a in zip(pieces, bounds)), encoding="utf-8")
        run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", delivered, "-map", "0:v:0", "-map", "1:a:0",
             "-c", "copy", "-movflags", "+faststart", out])

    # the check: the frame count, the seams, and every frame outside the stretches unchanged
    n = frame_count(out)
    bad = 0 if n == total else 1
    print(f"frames: {n} (delivered {total})")
    for k0, k1, ps in merged:
        # every frame of the stretch that no new patch covers must still be the delivered picture: the stretch is rebuilt from the
        # render, so a patch already in the delivered file (an earlier version's) and not passed again would be lost here
        mine = set()
        for f, a in ps:
            mine.update(range(a, a + frame_count(f)))
        # (calibrated: a clean splice leaves 0 pixels off by over 40 levels in any unpatched frame at 320x180; a lost patch showed
        # 72-224 in 122 frames, while its mean difference stayed under 1.1: a mean misses a small local change)
        a_, b_ = grab(delivered, k0, k1 - k0, 320, 180), grab(out, k0, k1 - k0, 320, 180)
        lost = [k0 + i for i in range(min(len(a_), len(b_))) if k0 + i not in mine and int((np.abs(a_[i] - b_[i]).max(axis=2) > 40).sum()) > 8]
        if len(a_) != k1 - k0 or len(b_) != k1 - k0:
            print(f"  stretch {k0}-{k1}: read {len(a_)} / {len(b_)} frames of {k1 - k0}")
            bad += 1
        if lost:
            print(f"  stretch {k0}-{k1}: {len(lost)} unpatched frame(s) differ from the delivered file ({lost[0]}-{lost[-1]}): an earlier "
                  f"patch inside the stretch? pass it again")
            bad += 1
        else:
            print(f"  stretch {k0}-{k1}: every unpatched frame matches the delivered file")
        for name, f0, cnt, inside in (("before", k0 - 3, 3, False), ("start", k0, 3, True), ("end", k1 - 3, 3, True), ("after", k1, 3, False)):
            if f0 < 0 or f0 + cnt > total:
                continue
            a, b = grab(delivered, f0, cnt), grab(out, f0, cnt)
            for i in range(min(len(a), len(b))):
                d = float(np.abs(a[i] - b[i]).mean())
                flag = "" if inside or d < 1.0 else "  <-- outside the stretch, not the delivered frame"
                bad += bool(flag)
                print(f"  {name:6s} frame {f0 + i}: mean diff {d:.2f}{flag}")
    if bad:   # never leave a failed splice under a deliverable's name
        failed = out.with_name(out.stem + "_FAILED" + out.suffix)
        out.replace(failed)
        out = failed
    print("SPLICE", "OK" if not bad else f"{bad} problem(s)", "->", out)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
