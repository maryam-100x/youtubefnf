"""Numbered samples of a hold's cut point (a line of the source's own speech played inside the film), for the creator's ear: each
sample is a number card, the last seconds of the film before the hold, the hold itself cut from its master at one candidate end (its
own sound, at the bite's level), then the first seconds after the hold, so the cut is heard exactly where it will sit in the film.

  PIPE tools/motion/hold_samples.py --export <film.mp4> --at <hold start in the film> --len <hold now>
      --master <master.mp4> --in <hold's in on the master> --ends 10.15,10.25,984.02+0.35 --out <reel.mp4> [--fill "crop=..."]
      [--lead 3.0] [--tail 1.6]

--fill: the crop the edit puts on that master (the prep's FILL). An end written <t>+<s> cuts the sound at t and holds the picture s more
(a breath after the line before the film goes on, when the next words on the master follow too closely)."""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--export", required=True)
ap.add_argument("--at", type=float, required=True)
ap.add_argument("--len", type=float, required=True)
ap.add_argument("--master", required=True)
ap.add_argument("--in", dest="tin", type=float, required=True)
ap.add_argument("--ends", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--fill", default="")
ap.add_argument("--lead", type=float, default=3.0)
ap.add_argument("--tail", type=float, default=1.6)
a = ap.parse_args()

W, H, FPS = 1920, 1080, 60
V = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS)]
A = ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2"]


def run(cmd):
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *cmd], check=True)


tmp = Path(tempfile.mkdtemp(prefix="holdsamples_"))
parts = []
ends = [(float(x.split('+')[0]), float(x.split('+')[1]) if '+' in x else 0.0) for x in a.ends.split(',')]
# the film around the hold, the same for every sample
run(["-ss", f"{a.at - a.lead:.3f}", "-t", f"{a.lead:.3f}", "-i", a.export, "-vf", f"scale={W}:{H}", *V, *A, str(tmp / "lead.mp4")])
run(["-ss", f"{a.at + a.len:.3f}", "-t", f"{a.tail:.3f}", "-i", a.export, "-vf", f"scale={W}:{H}", *V, *A, str(tmp / "tail.mp4")])
for k, (e, hush) in enumerate(ends, 1):
    n, h = tmp / f"n_{k}.mp4", tmp / f"h_{k}.mp4"
    # a number card: the sample's number and its cut, plain, 0.9 s, silent
    run(["-f", "lavfi", "-i", f"color=c=0x101318:s={W}x{H}:d=0.9:r={FPS}", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.9",
         "-vf", f"drawtext=text='{k}':fontcolor=white:fontsize=260:x=(w-text_w)/2:y=(h-text_h)/2-60,"
                f"drawtext=text='cut {e - a.tin:.2f} s into the line" + (f", then {hush:.2f} s quiet" if hush else '') + "':fontcolor=0xbbbbbb:fontsize=44:x=(w-text_w)/2:y=h/2+130",
         *V, *A, str(n)])
    # the hold from its master, in to this end, its own sound brought to the film's bite level (-16 LUFS), 20 ms fades
    d = e - a.tin + hush
    vf = (a.fill + "," if a.fill else "") + f"scale={W}:{H}"
    run(["-ss", f"{a.tin:.3f}", "-t", f"{d:.3f}", "-i", a.master, "-vf", vf,
         "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.02,afade=t=out:st={max(0, e - a.tin - 0.03):.3f}:d=0.03", *V, *A, str(h)])
    parts += [n, tmp / "lead.mp4", h, tmp / "tail.mp4"]
lst = tmp / "list.txt"
lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
run(["-f", "concat", "-safe", "0", "-i", str(lst), *V, *A, a.out])
print(f"{len(ends)} samples -> {a.out}")
for k, (e, hush) in enumerate(ends, 1):
    print(f"  {k}: the line cut {e - a.tin:.2f} s in (master {e:.3f}; now {a.len:.2f})" + (f", then {hush:.2f} s of picture, quiet" if hush else ''))
