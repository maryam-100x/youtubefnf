"""Sound-effect demos for the creator's pick: when an effect needs replacing, quick few-second snippets of the real cut, one per
candidate, so the creator picks by ear and the pick then applies everywhere that action recurs (rough quality is fine). One short
video per job: the same few seconds of the real cut played once per candidate (rated sounds only: palette.json), each labelled big,
A, B, C ..., with the real narration and music.

The mix is score.py's own: the cue sheet built once with the job's old effects taken out (score.build), each candidate placed exactly as
build() places an effect (peak against the voice's peak, its impact on the frame, sub-heavy files harmonised, cut at dur with a fade),
then the full mix's own gain to -14 LUFS and the house limiter. The picture is the current render (or a fresh render of a changed shot).

  EDIT tools/sound/sfx_demo.py <cue module> <jobs.json> <out dir>
jobs.json: [{"name", "t" (the effect's time), "t0", "t1" (the window), "drop": [note substrings], "picture": mkv/mp4, "pic_t0": the
picture file's start time (0 for the full render), "cands": [{"label", "path" (or null: no sound), "db", "sync", "dur",
"also": [{"path", "t", "db", "sync", "dur"}]}]}]"""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score as S  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

SR = S.SR
# a bold font for the labels (Windows, then macOS); none found: ffmpeg's default font
FONTS = ["C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
         "/System/Library/Fonts/Helvetica.ttc"]


def label_font():
    """the drawtext fontfile option (its colon escaped for the filter), or "" for the default font"""
    f = next((f for f in FONTS if Path(f).exists()), None)
    return f"fontfile='{f.replace(':', chr(92) + ':')}':" if f else ""


def place(sfx, path, t, db, sync, dur, vpk, harm_db=-8.0):
    a = S.load(path)
    ls = S.low_share(a)
    if harm_db is not None and ls > 0.8:
        a = S.harmonize(a, harm_db)
    sy = S.effect_sync(a) if sync is None else sync
    a = a / (np.abs(a).max() + 1e-9) * vpk * 10 ** (db / 20)
    if dur is not None:
        k = int((sy + dur) * SR)
        a = a[:k].copy()
        f = min(len(a), int(0.15 * SR))
        a[len(a) - f:] *= np.linspace(1, 0, f)[:, None]
    i0 = int(round((t - sy) * SR))
    lo, hi = max(0, i0), min(len(sfx), i0 + len(a))
    if hi > lo:
        sfx[lo:hi] += a[lo - i0:hi - i0]


def main():
    spec = importlib.util.spec_from_file_location("cues", sys.argv[1])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    jobs = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    drops = [d for j in jobs for d in j.get("drop", [])]
    before = len(mod.SFX)
    mod.SFX = [s for s in mod.SFX if not any(d in (s.note or "") for d in drops)]
    print(f"effects: {before} -> {len(mod.SFX)} (the jobs' old ones taken out)")
    mix, voice, music, sfx, act, report, v_l, handoffs, fxrep = S.build(mod)
    gdb = -14.0 - S.lufs(mix)
    vpk = np.percentile(np.abs(voice).max(axis=1), 99.9)
    chain = (f"volume={gdb:.2f}dB,aresample={SR * 4},alimiter=limit={10 ** (-2.0 / 20):.4f}:attack=0.5:release=60:level=disabled:latency=1,"
             f"aresample={SR}")
    font = label_font()
    for j in jobs:
        i0, i1 = int(j["t0"] * SR), int(j["t1"] * SR)
        base = (voice + music + sfx)[i0:i1]
        parts = []
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for n, c in enumerate(j["cands"]):
                fx = np.zeros_like(base)
                if c.get("path"):
                    place(fx, c["path"], j["t"] - j["t0"], c.get("db", -10), c.get("sync"), c.get("dur"), vpk)
                for e in c.get("also", []):
                    place(fx, e["path"], e["t"] - j["t0"], e.get("db", -10), e.get("sync"), e.get("dur"), vpk)
                wav = td / f"a{n}.wav"
                subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", "-af", chain, str(wav)],
                               input=(base + fx).astype(np.float32).tobytes(), check=True)
                lab = c["label"].replace(":", "\\:").replace("'", "")
                seg = td / f"v{n}.mp4"
                ss = j["t0"] - j.get("pic_t0", 0.0)
                vf = (f"scale=1280:720,drawbox=x=0:y=0:w=1280:h=86:color=black@0.62:t=fill,"
                      f"drawtext={font}text='{lab}':x=28:y=20:fontsize=46:fontcolor=white")
                subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{ss:.3f}", "-t", f"{j['t1'] - j['t0']:.3f}", "-i", j["picture"], "-i", str(wav),
                                "-map", "0:v:0", "-map", "1:a:0", "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(seg)], check=True)
                parts.append(seg)
                # a short black gap between candidates, so each one starts clean
                gap = td / f"g{n}.mp4"
                subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=30:d=0.7", "-f", "lavfi", "-i",
                                f"anullsrc=r={SR}:cl=stereo", "-t", "0.7", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                                "-c:a", "aac", "-b:a", "192k", str(gap)], check=True)
                parts.append(gap)
            lst = td / "list.txt"
            lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts[:-1]), encoding="utf-8")
            dst = out / f"{j['name']}.mp4"
            subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dst)], check=True)
        print(f"-> {dst} ({len(j['cands'])} candidates)")


if __name__ == "__main__":
    main()
