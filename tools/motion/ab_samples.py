"""Before/after samples of fixed spots in a long video, for the creator's review before any full render: quick samples of the fixed
sections to check; the ones that pass go into the video. Each spot plays twice on the delivered file's picture: A with the delivered
sound, then B with the new mix (or B's own picture when given), labelled with its number, time and words. 1280x720, quick to make;
one file per list.

  PIPE tools/motion/ab_samples.py <delivered.mp4> <new_mix.wav> <items.json> <out.mp4> [--b-video <new_picture.mp4>]
items.json: [{"t0": 813.4, "t1": 817.0, "label": "13:33 'the fifth of May'"}, ...] (seconds on the delivered file's timeline); an item's
"b_video" (+ "b_video_t0", the timeline second of its first frame) gives B a picture of its own, e.g. a quick render of a fixed shot;
"variants": [{"video", "video_t0", "tag"}, ...] plays several new versions after A (B, C, ...), for a choice between them.
Encodes with NVENC; on macOS (no NVENC) with x264 veryfast."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, MAC  # noqa: E402

# drawtext's font (the colon after a Windows drive letter escaped for the filter)
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if MAC else "C\\:/Windows/Fonts/arialbd.ttf"
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"] if MAC else ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "23"]


def esc(s):
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def main():
    src, mix, items_p, out = sys.argv[1:5]
    bvid = sys.argv[sys.argv.index("--b-video") + 1] if "--b-video" in sys.argv else src
    items = json.load(open(items_p, encoding="utf-8"))
    n = len(items)
    with tempfile.TemporaryDirectory() as d:
        parts = []
        for i, it in enumerate(items, 1):
            t0, t1 = float(it["t0"]), float(it["t1"])
            dur = t1 - t0
            sides = [("A", src, src, "white", "A  delivered", t0)]
            if "variants" in it:
                sides += [(chr(66 + j), v["video"], mix, "0x6cff6c", f"{chr(66 + j)}  {v['tag']}", t0 - float(v.get("video_t0", 0.0)))
                          for j, v in enumerate(it["variants"])]
            else:
                sides.append(("B", it.get("b_video", bvid), mix, "0x6cff6c", "B  NEW",
                              t0 - float(it.get("b_video_t0", 0.0)) if "b_video" in it else t0))
            for side, vin, ain, color, tag, vss in sides:
                p = Path(d) / f"{i:02d}{side}.mkv"
                head = f"{i}/{n}   {it['label']}" if n > 1 else it["label"]
                vf = (f"scale=1280:720:flags=bicubic,format=yuv420p,"
                      f"drawbox=x=0:y=0:w=iw:h=64:color=black@0.62:t=fill,"
                      f"drawtext=fontfile='{FONT}':text='{esc(head)}':x=22:y=17:fontsize=30:fontcolor=white,"
                      f"drawtext=fontfile='{FONT}':text='{esc(tag)}':x=w-tw-22:y=14:fontsize=36:fontcolor={color}")
                af = f"afade=t=in:d=0.02,afade=t=out:st={dur - 0.12:.3f}:d=0.12,aresample=48000"
                cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{vss:.3f}", "-t", f"{dur:.3f}", "-i", vin,
                       "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", ain, "-map", "0:v:0", "-map", "1:a:0", "-vf", vf, "-af", af,
                       "-r", "60", *ENC, "-c:a", "pcm_s16le", "-ac", "2", str(p)]
                subprocess.run(cmd, check=True)
                parts.append(p)
        lst = Path(d) / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)
    print(f"{n} spot(s), A then B -> {out}")


if __name__ == "__main__":
    main()
