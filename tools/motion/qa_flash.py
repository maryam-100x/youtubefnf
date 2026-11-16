"""Find "flashes": a shot whose source clip cuts to another camera angle within its first or last few frames, so a sliver of a
different shot shows for a frame or two (it reads as an ugly jump to the viewer). Reads the per-frame clip audit that qa_clips.py
writes (out/clip_audit_<comp>.log: which source second every output frame shows), splits it into shots (runs of consecutive frames
from one file), finds the cuts inside each source file with ffmpeg's scene score, and lists every shot that shows less than --edge
seconds of a source shot at its start or its end. Look at each hit: fast motion can score like a cut.

  PIPE tools/motion/qa_flash.py <Composition> [--edge 0.15] [--scene 0.3]
(QA_PUBLIC=<the render's public dir>, as qa_clips.py; the default is the main public dir)"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, PUBLIC  # noqa: E402

HERE = Path(__file__).resolve().parent
FPS = 60


def cuts(path, thr, cache):
    key = f"{path}|{thr}"
    if key not in cache:
        o = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path), "-vf", f"scale=320:-2,select='gt(scene,{thr})',showinfo", "-an",
                            "-f", "null", "-"], capture_output=True, text=True, errors="replace").stderr
        cache[key] = [float(t) for t in re.findall(r"pts_time:([\d.]+)", o)]
    return cache[key]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comp")
    ap.add_argument("--edge", type=float, default=0.15)
    ap.add_argument("--scene", type=float, default=0.3)
    a = ap.parse_args()
    pub = Path(os.environ.get("QA_PUBLIC", str(PUBLIC)))
    rows = defaultdict(list)
    for ln in open(HERE / "out" / f"clip_audit_{a.comp}.log", encoding="utf-8", errors="replace"):
        m = re.search(r"CLIPAUDIT\|(\d+)\|([^|]+)\|([\d.]+)", ln)
        if m:
            rows[m.group(2)].append((int(m.group(1)), float(m.group(3))))
    cache_f = HERE / "out" / "scene_cuts.json"
    cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
    hits = 0
    for src, rs in sorted(rows.items()):
        rs = sorted(set(rs))
        shots, cur = [], [rs[0]]
        for r in rs[1:]:
            if r[0] == cur[-1][0] + 1 and r[1] >= cur[-1][1] - 1e-3:
                cur.append(r)
            else:
                shots.append(cur)
                cur = [r]
        shots.append(cur)
        cs = cuts(pub / src, a.scene, cache)
        for sh in shots:
            s0, s1 = sh[0][1], sh[-1][1]
            for c in cs:
                if s0 < c <= s0 + a.edge and c < s1:
                    hits += 1
                    print(f"  {src}: shot at {sh[0][0] / FPS:.2f}-{sh[-1][0] / FPS:.2f} s opens with {c - s0:.2f} s of a source shot (cut at {c:.2f} s)")
                if s1 - a.edge <= c <= s1 and c > s0:
                    hits += 1
                    print(f"  {src}: shot at {sh[0][0] / FPS:.2f}-{sh[-1][0] / FPS:.2f} s ends with {s1 - c + 1 / 30:.2f} s of the next source shot (cut at {c:.2f} s)")
    cache_f.write_text(json.dumps(cache), encoding="utf-8")
    print(f"{hits} possible flash(es) in {len(rows)} files (edge {a.edge} s, scene {a.scene})")


if __name__ == "__main__":
    main()
