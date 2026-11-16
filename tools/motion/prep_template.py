"""prep_template.py: how a video's clips are cut. Copy it to tools/motion/prep<id>.py (e.g. prep12.py for video 012), fill CLIPS with the
shots the shot plan picked, and run it; nothing else in the pipeline cuts footage.

What it does, in order:
  1. every CLIPS entry is cut from its source into PUBLIC/v<id>/clips/<name>.mp4: 1920x1080 (cover-scaled with lanczos, or the
     source's own picture with KEEP), the source's own frame rate, x264 CRF 15 medium, a keyframe every 15 frames and no B-frames (so
     Remotion seeks fast and every frame decodes the same), no audio, no data streams. A clip on disk whose entry is unchanged is kept.
  2. each clip's last frame and rate go into src/clipdurs.json (shared by every prep: read fresh and written under a lock), so the
     gate and the static audit know where each file ends;
  3. the gate's manifest prep<id>_clips.json (name -> [source, in, out]), which video.toml's [gate] clips_json names.
  --check, after the cut (each flag a real fault; a clip that holds a cut by design is named in CUTS_OK with its count):
     CUT    a camera cut inside the cut clip (ffmpeg's scene score > 0.25 at 480 px): a sliver of the source's next shot;
     EDGE   a cut in the SOURCE within EDGE seconds inside the span's in or out point (scene > SCENE at 320 px): the clip opens on the
            shot before or ends on the shot after, so every span sits inside one shot of its source;
     FADE   a fade or dissolve at either edge (qa_fades.py: reads as a flash frame);
     FREEZE a held stretch inside a clip (qa_midfreeze.py).
Every span is picked on a frame sheet of its source (the shot's own frames, not a guess from its time): read the source's cuts first
and keep each span inside one shot, with a few frames to spare on each side.

  PIPE tools/motion/prep_template.py [--only name ...] [--check]
  EDIT tools/motion/prep_template.py --proof [<dir>]     every BOXES entry drawn on a crop of its file (default PUBLIC/v<id>/proof)

The heavy-job ticket (tools/pipeline/heavy.py) wraps the cuts: decoding 4K sources waits its turn beside renders. Keep this file's top
level free of side effects (everything runs under main()): qa_fades.py and the gate import a prep file to read its CLIPS and DL."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, FOOTAGE, PUBLIC, TOOLS  # noqa: E402

HERE = Path(__file__).resolve().parent
ID = "12"                                   # the video's short id: its public folder v12/, src/v12/, prep12_clips.json (as video.toml)
V = PUBLIC / f"v{ID}"                       # the video's own media folder under the public dir (public paths "v12/clips/<name>.mp4")
OUT = V / "clips"
DL = FOOTAGE / "sources"                    # where the sources sit; a CLIPS source is relative to it (or a full path)
DURS = HERE / "src" / "clipdurs.json"
MANIFEST = HERE / f"prep{ID}_clips.json"
ENC = ["-threads", "2", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", "-bf", "0",
       "-movflags", "+faststart"]
COVER = "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,setsar=1,setpts=PTS-STARTPTS"
KEEP = "KEEP"                               # the source's own picture as it is (e.g. a 4K source the edit zooms into)
EDGE, SCENE = 0.5, 0.3                      # the source-edge check: as video.toml [audit] edge and scene

# a few sources, named once (the source's own file name under DL; where it came from, in a comment)
LAUNCH = "launch_video_2160p.mp4"           # the product's official launch video, 4K 30
CITY = "city_broll_1080p.mp4"               # a stock clip of the city at night, 1080p 30
INTERVIEW = "interview_2023_1080p.mp4"      # an interview the video quotes, 1080p 25
# name: (source, in s, out s, filter): one shot per entry, named s<beat>_<what> (the beat it plays on, what it shows); the comment says which words it is on, and the
# source shot it sits inside (from the frame sheet), so a later edit can check the span without opening the source again.
# filter: "" = cover-scale to 1920x1080; KEEP = as it is; any other string = an ffmpeg filter that runs before the cover scale
# (e.g. "crop=iw:ih*0.8:0:ih*0.1" for a picture inside bars, when the edit really wants it filled)
CLIPS = {
    "s03_launch_stage": (LAUNCH, 12.40, 15.10, ""),        # S03 "on stage": the presenter walks on (shot 12.30-15.40)
    "s05_launch_detail": (LAUNCH, 48.20, 49.90, KEEP),     # S05 "the small print": the product's label, kept 4K for the zoom (shot 47.95-50.10)
    "s07_city_traffic": (CITY, 3.10, 6.00, ""),            # S07 ground: traffic over the bridge at night (shot 2.90-6.40)
    "s09_interview_quote": (INTERVIEW, 301.20, 304.80, ""),  # S09 the quote itself, the speaker in close-up (shot 298.70-305.10)
}
CUTS_OK = {}                                # {"<name>": <n>}: a clip that holds n of its source's own cuts by design
# the boxes the shots light (a mark, a zoom's subject, a highlight), [x, y, w, h] in each file's own pixels, file relative to V; each
# is drawn by --proof and looked at before a shot uses it (the marks' boxes come from the pixels: tools/motion/automark.py)
BOXES = {
    # "img/launch_label.png": {"price": [812, 404, 220, 64]},
}


def src(name):
    """a clip's source as a full path"""
    s = CLIPS[name][0]
    return Path(s) if Path(s).is_absolute() else DL / s


def src_fps(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True).stdout.strip()
    num, _, den = r.partition("/")
    return max(1, round(float(num) / float(den or 1)))


def cut(name, done):
    s, a, b, flt = CLIPS[name]
    out = OUT / f"{name}.mp4"
    key = [s, a, b, flt]
    if out.exists() and done.get(name) == key:
        return name, "kept"
    vf = "setsar=1,setpts=PTS-STARTPTS" if flt == KEEP else (flt + "," if flt else "") + COVER
    tmp = out.with_suffix(".part.mp4")
    subprocess.run([FFMPEG, "-nostdin", "-threads", "2", "-v", "error", "-ss", f"{a:.3f}", "-i", str(src(name)), "-t", f"{b - a:.3f}",
                    "-map", "0:v:0", "-dn", "-an", "-vf", vf, *ENC, "-y", str(tmp)], check=True)
    tmp.replace(out)
    done[name] = key
    return name, "cut"


def last_frame(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames,r_frame_rate",
                        "-of", "json", str(p)], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)["streams"][0]
    num, den = (int(x) for x in st["r_frame_rate"].split("/"))
    return [round((int(st["nb_read_frames"]) - 1) * den / num, 4), round(num / den, 3)]


def write_durs(new):
    """src/clipdurs.json is shared by every prep: read fresh and written under a lock file (O_EXCL), a stale lock taken over after 2 min"""
    lock = DURS.with_suffix(".lock")
    for _ in range(600):
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 120:
                    lock.unlink(missing_ok=True)
            except FileNotFoundError:
                pass
            time.sleep(0.2)
    else:
        raise SystemExit("clipdurs.json stays locked")
    try:
        durs = json.loads(DURS.read_text(encoding="utf-8")) if DURS.exists() else {}
        durs.update(new)
        DURS.write_text(json.dumps(durs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


def scene_cuts(path, thr, width, ss=None, t=None):
    """the times (s, from ss) where ffmpeg's scene score passes thr"""
    r = subprocess.run([FFMPEG, "-nostdin", "-threads", "2", "-hide_banner", *(["-ss", f"{ss:.3f}"] if ss is not None else []),
                        *(["-t", f"{t:.3f}"] if t is not None else []), "-i", str(path), "-an", "-vf",
                        f"scale={width}:-2,select='gt(scene,{thr})',showinfo", "-f", "null", "-"], capture_output=True, text=True)
    return [float(x) + (ss or 0.0) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def check(names):
    """CUT, EDGE, FADE and FREEZE (the module docstring); returns the number of flags"""
    sys.path.insert(0, str(HERE))
    import qa_fades
    bad = 0
    for n in names:
        _, a, b, _ = CLIPS[n]
        inside = scene_cuts(OUT / f"{n}.mp4", 0.25, 480)
        ok = len(inside) <= CUTS_OK.get(n, 0)
        bad += not ok
        print(f"{'ok  ' if ok else 'CUT '} {n}: {', '.join(f'{x:.2f}' for x in inside) or 'no cut inside'}")
        w0 = max(0.0, a - 0.1)
        edge = [c for c in scene_cuts(src(n), SCENE, 320, w0, b - w0 + 0.1) if a < c <= a + EDGE or b - EDGE <= c < b]
        bad += bool(edge)
        print(f"{'EDGE' if edge else 'ok  '} {n}: " + (", ".join(f"the source cuts at {c:.2f} s, {min(c - a, b - c):.2f} s inside the span"
                                                                for c in edge) or "inside one shot of its source"))
        hits = qa_fades.scan(src(n), a, b)
        bad += bool(hits)
        print(f"{'FADE' if hits else 'ok  '} {n}: " + ("; ".join(f"{e} {k}: {m}" for e, k, m in hits) or "no fade or dissolve at its edges"))
    r = subprocess.run([sys.executable, str(HERE / "qa_midfreeze.py"), str(OUT), str(MANIFEST), "--only", ",".join(names)],
                       capture_output=True, text=True)
    print(r.stdout.strip()[-4000:])
    bad += r.returncode != 0
    print(f"{bad} flag(s)")
    return bad


def proof(dst):
    """every box in BOXES drawn on a crop of its file (EDIT: OpenCV), to be looked at before a shot uses it"""
    import cv2
    dst = Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for f, boxes in BOXES.items():
        im = cv2.imread(str(V / f))
        if im is None:
            print(f"cannot read {V / f}")
            continue
        for k, (x, y, w, h) in boxes.items():
            cv2.rectangle(im, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(im, k, (x, max(14, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        xs = [b[0] for b in boxes.values()] + [b[0] + b[2] for b in boxes.values()]
        ys = [b[1] for b in boxes.values()] + [b[1] + b[3] for b in boxes.values()]
        pad = 120
        crop = im[max(0, min(ys) - pad):max(ys) + pad, max(0, min(xs) - pad):max(xs) + pad]
        cv2.imwrite(str(dst / (Path(f).stem + "_boxes.jpg")), crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print("proofs in", dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--proof", nargs="?", const=str(V / "proof"), help="draw every BOXES entry on its file into this folder, then stop")
    a = ap.parse_args()
    if a.proof:
        proof(a.proof)
        return 0
    names = [n for n in CLIPS if not a.only or n in a.only]
    missing = sorted({str(src(n)) for n in names if not src(n).exists()})
    if missing:
        raise SystemExit("sources missing:\n  " + "\n  ".join(missing))
    OUT.mkdir(parents=True, exist_ok=True)
    rec = OUT / f"clips_{ID}.json"
    done = json.loads(rec.read_text(encoding="utf-8")) if rec.exists() else {}
    sys.path.insert(0, str(TOOLS / "pipeline"))
    from heavy import HeavyJob   # the sources' decodes wait their turn beside renders
    with HeavyJob(f"prep{ID}: clip cuts", "finish", need_gb=1):
        res = []
        for n in names:
            res.append(cut(n, done))
            print(f"{res[-1][1]:5} {n}", flush=True)
            rec.write_text(json.dumps(done, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({n: [Path(s).name, x, y] for n, (s, x, y, _) in CLIPS.items()}, indent=1) + "\n", encoding="utf-8")
    write_durs({f"v{ID}/clips/{n}.mp4": last_frame(OUT / f"{n}.mp4") for n, _ in res})
    print(f"{len(res)} clips; {DURS.name} and {MANIFEST.name} written")
    if a.check:
        return 1 if check(names) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
