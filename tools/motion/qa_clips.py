"""Clips that run past their end. Remotion then holds the file's last frame: a freeze the viewer sees, which blur or a slow push can hide
from freezedetect (e.g. a 4.93-s shot from 3.0 s under a 5.76-s scene: frozen ~4 s).
An audio-only render with REMOTION_CLIP_AUDIT=1 makes every mounted Clip log the source second it shows on each frame (lib.tsx `Clip`);
this reads those lines, measures each file, and lists every stretch where a clip asks for time past its last frame. A hidden layer
(opacity 0) logs too: look at each hit before fixing it.
A clip with a sliver end (src/clipedges.json: the source's next shot in its last frames) is measured to its last GOOD frame, and any
frame past it counts (a 1-frame sliver shows). The render also logs every sound cue (Sfx.tsx): their anchor times go to
out/sfx_cues_<comp>.csv (qa_sfx.py reads it).
It also lists every shot whose clip plays slower than 1.0x: a clip slowed down to stay on screen looks forced, so it gets a cut instead
(a second clip); only a stylized replay keeps its slow motion.

  bash tools/motion/with_remotion_lock.sh "clip audit" PIPE tools/motion/qa_clips.py <Composition> [--frames a-b]
(a Remotion render: it runs as the one Remotion job. QA_PUBLIC=<a lean public dir> renders from that dir; the default is the main
public dir.)"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFPROBE, PUBLIC, WINDOWS  # noqa: E402

HERE = Path(__file__).resolve().parent
PUB = Path(os.environ.get("QA_PUBLIC", str(PUBLIC)))  # QA_PUBLIC: a lean public dir (the CLI copies the whole dir into its bundle)
FPS = 60


def duration(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames,r_frame_rate:format=duration",
                          "-of", "default=nw=1", str(path)], capture_output=True, text=True).stdout
    kv = dict(ln.split("=", 1) for ln in out.splitlines() if "=" in ln)
    num, den = map(int, kv.get("r_frame_rate", "30/1").split("/"))
    fps = num / den
    n = int(kv["nb_frames"]) if kv.get("nb_frames", "N/A").isdigit() else round(float(kv["duration"]) * fps)
    return n / fps, fps  # the last frame starts at n/fps - 1/fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comp")
    ap.add_argument("--frames", default=None)
    a = ap.parse_args()
    (HERE / "out").mkdir(exist_ok=True)
    log = HERE / "out" / f"clip_audit_{a.comp}.log"
    env = dict(os.environ, REMOTION_CLIP_AUDIT="1")
    cmd = ["npx", "remotion", "render", "src/index.ts", a.comp, str(HERE / "out" / "clip_audit.wav"), "--codec=wav", "--log=verbose",
           f"--public-dir={PUB.as_posix()}"] + ([f"--frames={a.frames}"] if a.frames else [])
    with open(log, "w", encoding="utf-8") as fh:
        subprocess.run(cmd, cwd=HERE, env=env, stdout=fh, stderr=subprocess.STDOUT, shell=WINDOWS)
    hits = defaultdict(list)  # src -> [(abs frame, source s)]
    cues = set()  # (abs anchor frame, name)
    for ln in open(log, encoding="utf-8", errors="replace"):
        m = re.search(r"CLIPAUDIT\|(\d+)\|([^|]+)\|([\d.]+)", ln)
        if m:
            hits[m.group(2)].append((int(m.group(1)), float(m.group(3))))
        m = re.search(r"SFXAUDIT\|(-?\d+)\|([a-z_0-9]+)\|(-?[\d.]+)", ln)
        if m:
            cues.add((int(m.group(1)) + round(float(m.group(3)) * FPS), m.group(2)))
    if cues:
        out = HERE / "out" / f"sfx_cues_{a.comp}.csv"
        out.write_text("frame,seconds,name\n" + "".join(f"{fr},{fr / FPS:.3f},{n}\n" for fr, n in sorted(cues)), encoding="utf-8")
        print(f"{len(cues)} sound cues -> {out.name}")
    edges = json.loads((HERE / "src" / "clipedges.json").read_text(encoding="utf-8"))
    print(f"{sum(len(v) for v in hits.values())} clip-frames from {len(hits)} files ({log.name})")
    bad = 0
    for src, rows in sorted(hits.items()):
        d, fps = duration(PUB / src)
        last = d - 1 / fps
        sliver = (edges.get(src) or [0, None])[1]
        if sliver is not None and sliver < last:
            over = sorted({f for f, s in rows if s > sliver + 0.25 / fps})
            if over:
                bad += 1
                print(f"  {src}: {len(over)} frame(s) from {over[0] / FPS:.2f} s show the sliver past its last good frame {sliver:.3f} s"
                      f" (asks up to {max(s for f, s in rows if f in set(over)):.3f} s)")
            continue
        over = sorted({f for f, s in rows if s > last + 0.5 / fps})
        if not over:
            continue
        # contiguous stretches of absolute frames
        runs, r0, prev = [], over[0], over[0]
        for f in over[1:]:
            if f != prev + 1:
                runs.append((r0, prev))
                r0 = f
            prev = f
        runs.append((r0, prev))
        for f0, f1 in runs:
            if f1 - f0 + 1 <= 2:
                continue
            worst = max(s for f, s in rows if f0 <= f <= f1)
            bad += 1
            print(f"  {src}: frames {f0}-{f1} ({f0 / FPS:.2f}-{(f1 + 1) / FPS:.2f} s, {(f1 - f0 + 1) / FPS:.2f} s) ask up to {worst:.2f} s"
                  f" of a {d:.2f}-s file")
    print(f"{bad} overrun stretch(es)")
    # every shot whose clip plays slower than 1.0x is listed; one that was slowed to fill its shot gets a cut instead (a second clip),
    # only a stylized replay keeps its slow motion
    slow = 0
    for src, rows in sorted(hits.items()):
        rows = sorted(set(rows))
        runs, cur = [], [rows[0]]
        for f, s in rows[1:]:
            pf, ps = cur[-1]
            if f == pf + 1 and 0 <= s - ps < 0.2:
                cur.append((f, s))
            else:
                runs.append(cur)
                cur = [(f, s)]
        runs.append(cur)
        for r in runs:
            (f0, s0), (f1, s1) = r[0], r[-1]
            if f1 - f0 < 0.3 * FPS:
                continue
            rate = (s1 - s0) / ((f1 - f0) / FPS)
            if rate < 0.98:
                slow += 1
                print(f"  SLOW {src}: {f0 / FPS:.2f}-{(f1 + 1) / FPS:.2f} s plays at {rate:.2f}x")
    print(f"{slow} slowed shot(s) (cut instead, unless it's a stylized replay)")


if __name__ == "__main__":
    main()
