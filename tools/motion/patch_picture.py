"""Lay `pipe.py patch` segments into a parts render's 1440p picture, for the review copy (findings after a render go in as patches,
never a full re-render). `finish --patches` lays them into the 4K, but the 1440p review copy is the render's own stream copied, and
`splice_patch.py` rebuilds 4K stretches only. This rebuilds just the parts a patch touches: the part's
frames before the patch, the segment, the part's frames after, encoded with the parts' own x264 settings (Remotion's: veryfast, CRF 14,
High 5.1, yuv420p, bt709), so the parts still join by stream copy like `pipe.py render` joins them; every other part is copied as it is.

  PIPE tools/motion/patch_picture.py <parts_dir> <patches.json> <out.mkv> [--fps 60]

<parts_dir> holds parts.json (each part's f0, f1, file); <patches.json> is `pipe.py patch`'s list ({"file", "at"}: a segment of frames
starting at film frame round(at * fps)). A patch must sit inside one part. The checks after: each rebuilt part has the part's own frame
count; the joined file has every part's frames; each rebuilt stretch decodes from the joined file to the same frames (framemd5) as the
rebuilt part alone (a join whose stream headers didn't match would decode differently there)."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE  # noqa: E402

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-profile:v", "high", "-level", "5.1", "-pix_fmt", "yuv420p",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]


def frames(f: Path) -> int:
    r = subprocess.run([FFPROBE, "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets",
                        "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def md5s(f: Path, start: int, n: int, fps: int) -> list[str]:
    r = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{start / fps:.6f}", "-i", str(f), "-frames:v", str(n), "-f", "framemd5", "-"],
                       capture_output=True, text=True)
    return [ln.split(",")[-1].strip() for ln in r.stdout.splitlines() if ln and not ln.startswith("#")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts_dir")
    ap.add_argument("patches")
    ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=60)
    a = ap.parse_args()
    pd, out, fps = Path(a.parts_dir), Path(a.out), a.fps
    parts = sorted(json.loads((pd / "parts.json").read_text(encoding="utf-8"))["parts"], key=lambda p: p["i"])
    work = out.parent / (out.stem + "_parts")
    work.mkdir(parents=True, exist_ok=True)
    by_part: dict[int, list[tuple[int, int, Path]]] = {}
    for p in json.loads(Path(a.patches).read_text(encoding="utf-8")):
        seg = Path(p["file"])
        fa = round(p["at"] * fps)
        fb = fa + frames(seg) - 1
        hit = [q for q in parts if q["f0"] <= fa and fb <= q["f1"]]
        if not hit:
            sys.exit(f"{seg.name} (frames {fa}-{fb}) crosses a part's edge: split the patch")
        by_part.setdefault(hit[0]["i"], []).append((fa, fb, seg))
    files = []
    for q in parts:
        src = Path(q["file"])
        if q["i"] not in by_part:
            files.append(src)
            continue
        n = q["f1"] - q["f0"] + 1
        segs = sorted(by_part[q["i"]])
        ins, chain, last = [str(src)], [], 0
        filt = [f"[0:v]split={len(segs) + 1}" + "".join(f"[m{k}]" for k in range(len(segs) + 1))]
        for k, (fa, fb, seg) in enumerate(segs):
            A, B = fa - q["f0"], fb - q["f0"]
            ins.append(str(seg))
            filt.append(f"[m{k}]select='between(n\\,{last}\\,{A - 1})',setpts=N/{fps}/TB[o{k}]")
            filt.append(f"[{k + 1}:v]setpts=N/{fps}/TB[s{k}]")
            chain += [f"[o{k}]", f"[s{k}]"]
            last = B + 1
        filt.append(f"[m{len(segs)}]select='gte(n\\,{last})',setpts=N/{fps}/TB[tail]")
        chain.append("[tail]")
        filt.append("".join(chain) + f"concat=n={len(chain)}:v=1:a=0[v]")
        dst = work / src.name
        cmd = [FFMPEG, "-v", "error", "-y"]
        for x in ins:
            cmd += ["-i", x]
        cmd += ["-filter_complex", ";".join(filt), "-map", "[v]", "-r", str(fps), *ENC, str(dst)]
        print(f"part {q['i']}: {len(segs)} patch(es) {[(fa, fb) for fa, fb, _ in segs]} -> {dst.name}", flush=True)
        subprocess.run(cmd, check=True)
        got = frames(dst)
        if got != n:
            sys.exit(f"{dst.name}: {got} frames, the part has {n}")
        files.append(dst)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{f.as_posix()}'\n" for f in files), encoding="utf-8")
    tmp = out.with_suffix(".tmp.mkv")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(tmp)], check=True)
    total, want = frames(tmp), parts[-1]["f1"] + 1
    if total != want:
        sys.exit(f"joined: {total} frames, the parts hold {want}")
    for i, segs in sorted(by_part.items()):
        q = parts[i]
        for fa, fb, _ in segs:
            # the stretch decoded from the rebuilt part alone must sit, frame for frame, inside the same place decoded from the joined
            # file (a seek lands within a frame of its target: the window is wider and the match is searched)
            a0, n = max(q["f0"], fa - 3), min(q["f1"], fb + 3) - max(q["f0"], fa - 3) + 1
            alone = md5s(work / Path(q["file"]).name, a0 - q["f0"], n, fps)
            joined = md5s(tmp, max(0, a0 - 15), n + 30, fps)
            if len(alone) < n - 2 or not any(joined[k:k + len(alone)] == alone for k in range(len(joined) - len(alone) + 1)):
                sys.exit(f"frames {a0}-{a0 + n - 1}: the joined file decodes differently from the rebuilt part")
            print(f"frames {a0}-{a0 + n - 1}: the joined file matches the rebuilt part ({len(alone)} frames)", flush=True)
    tmp.replace(out)
    print(f"PATCHED PICTURE {out} ({total} frames, {len(by_part)} part(s) rebuilt)")


if __name__ == "__main__":
    main()
