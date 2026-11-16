"""Frames of every shot for the brain's detection and description passes: the clean span's start, middle and end (2 frames in from
each edge), plus one frame every ~2 s inside a long shot, grabbed from the full-quality file at 1280 wide (faces and small objects need
more than the 480p proxy) into WORK/frames/<key>/<frame>.jpg. Reads WORK/work/<key>_shots.json (brain_cuts.py apply).

  EDIT tools/footage/brain_frames.py <key> [--threads 6]
  EDIT tools/footage/brain_frames.py <CODE> --lib       every clip of a library that has a shots file"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402

GW, GH = 1280, 720


def frames_of(shot, fps):
    """The frame numbers to look at for one shot."""
    a, b = shot["c_in"], shot["c_out"]
    n = b - a + 1
    if n <= 5:
        return sorted({a, (a + b) // 2, b})
    s, e = a + 2, b - 2
    picks = [s, (s + e) // 2, e]
    dur = n / fps
    if dur > 4.0:
        k = int(dur // 2.0)                       # one more frame every ~2 s
        picks += [s + round((e - s) * (i / (k + 1))) for i in range(1, k + 1)]
    return sorted(set(picks))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key", help="a source key, or a library code with --lib")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--lib", action="store_true", help="every clip of the library <key> that has a shots file")
    a = ap.parse_args()
    if a.lib:
        for p in B.lib_files(a.key):
            k = f"{a.key}/{p.stem}"
            if (B.WORK / "work" / f"{B.key_file(k)}_shots.json").exists():
                run(k, a.threads)
        return
    run(a.key, a.threads)


def run(key, threads):
    d = json.loads((B.WORK / "work" / f"{B.key_file(key)}_shots.json").read_text(encoding="utf-8"))
    fps = d["fps"]
    path = B.source_path(key)
    out = B.WORK / "frames" / B.key_file(key)
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for s in d["shots"]:
        fl = frames_of(s, fps)
        s["frames"] = fl
        for f in fl:
            p = out / f"{f:07d}.jpg"
            if not p.exists():
                jobs.append((f, p))

    def grab(job):
        f, p = job
        base = [B.FFMPEG, "-v", "error", "-y", "-ss", f"{B.seek_time(f, fps):.4f}"]
        tail = ["-i", str(path), "-frames:v", "1", "-vf", f"scale={GW}:-2:flags=bicubic", "-q:v", "3", str(p)]   # the picture keeps its shape
        subprocess.run(base + ["-hwaccel", "cuda"] + tail, check=False)   # the GPU decodes when it can
        if not p.exists():
            subprocess.run(base + tail, check=False)
        return p.exists()

    # frames close together (a long take's frame every ~2 s) come out of one decode of their span: a seek per frame decodes from the
    # keyframe each time (seconds a frame on a long 4K file), a run decodes the span once
    jobs.sort()
    runs, cur = [], []
    for j in jobs:
        if cur and j[0] - cur[-1][0] <= 3 * fps:
            cur.append(j)
        else:
            cur = [j]
            runs.append(cur)
    singles = [r[0] for r in runs if len(r) < 3]
    runs = [r for r in runs if len(r) >= 3]

    def grab_span(run):
        f0, f1 = run[0][0], run[-1][0]
        want = {f - f0: p for f, p in run}
        sel = "+".join(f"eq(n\\,{k})" for k in sorted(want))
        tmp = out / f"_run_{f0}_%04d.jpg"
        base = [B.FFMPEG, "-v", "error", "-y", "-ss", f"{B.seek_time(f0, fps):.4f}", "-t", f"{(f1 - f0 + 1.5) / fps:.4f}"]
        tail = ["-i", str(path), "-frames:v", str(len(want)), "-vf", f"select='{sel}',scale={GW}:-2:flags=bicubic", "-fps_mode", "passthrough",
                "-q:v", "3", str(tmp)]
        subprocess.run(base + ["-hwaccel", "cuda"] + tail, check=False)
        made = sorted(out.glob(f"_run_{f0}_*.jpg"))
        if len(made) != len(want):   # the GPU path failed or the count is off: the software path
            for m in made:
                m.unlink()
            subprocess.run(base + tail, check=False)
            made = sorted(out.glob(f"_run_{f0}_*.jpg"))
        n = 0
        for m, k in zip(made, sorted(want)):
            m.replace(want[k])
            n += 1
        for m in out.glob(f"_run_{f0}_*.jpg"):
            m.unlink()
        return n

    ok = sum(grab_span(r) for r in runs)
    with ThreadPoolExecutor(threads) as ex:
        ok += sum(ex.map(grab, singles))
    (B.WORK / "work" / f"{B.key_file(key)}_shots.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
    print(f"{key}: {len(d['shots'])} shots, {sum(len(s['frames']) for s in d['shots'])} frames ({ok} new) -> {out}")


if __name__ == "__main__":
    main()
