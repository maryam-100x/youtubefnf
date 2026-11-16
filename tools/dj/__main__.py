"""CLI: run from tools/ with the pipeline python (PIPE: `python tools/common/paths.py` prints it):

  cd tools && PIPE -m dj parse ../videos/<video>       check script.md (beats, VIS lines, the opener/sign-off) -> build/script.json
  cd tools && PIPE -m dj tts ../videos/<video>         the narration (config/tts.toml [tts]) -> build/voice/, build/beats.json
  cd tools && PIPE -m dj captions ../videos/<video>    word times from the audio -> build/captions/ (words.json, captions.srt, chunks.srt)
  cd tools && PIPE -m dj all ../videos/<video>         parse, tts, captions in order
  cd tools && PIPE -m dj log ../videos/<video> "<manual step>" <minutes>    a manual step's time into the metrics file
  cd tools && PIPE -m dj clean ../videos/<video>       after the upload: build/ and old review files deleted for good (the final MP4 stays)

The config is config/tts.toml (the example config/tts.example.toml when it is missing; see dj/core.py). Any key can be overridden
with --set section.key=value, and a script can pin its own with `CONFIG: section.key=value` lines."""
import argparse
import csv
import datetime
import sys
import time
from pathlib import Path

from . import captions, clean, script, tts
from .core import Ctx, expand, ffmpeg_bin, load_config

STEPS = {"parse": script.run, "tts": tts.run, "captions": captions.run}


def log_metric(cfg, video, step, seconds):
    p = expand(cfg["paths"]["metrics"])
    new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "video", "command", "seconds"])
        w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), video, step, round(seconds, 1)])


def video_config(video):
    """Per-video settings: `CONFIG: section.key=value` lines in script.md (e.g. `CONFIG: video.short_loop=false`, a Short that ends
    on a spoken pointer to the long video instead of looping)."""
    sp = Path(video) / "script.md"
    if not sp.exists():
        return []
    return [ln.strip()[7:].strip() for ln in sp.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("CONFIG:")]


def main(argv=None):
    for s in (sys.stdout, sys.stderr):  # the Windows terminal is cp1252: a "→" or "ñ" in a script must not crash a print
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="python -m dj", description="the dj pipeline: script -> narration -> captions")
    ap.add_argument("command", choices=[*STEPS, "all", "log", "clean"], help="clean = after the upload: build/ + old review files deleted for good")
    ap.add_argument("video", help="video folder containing script.md")
    ap.add_argument("extra", nargs="*", help='for `log`: "<manual step>" <minutes>')
    ap.add_argument("--config", help="config file (default: config/tts.toml, else config/tts.example.toml)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override config, e.g. tts.engine=dummy")
    ap.add_argument("--format", choices=["short", "long"], help="default: 'short' if the folder name contains 'short'")
    ap.add_argument("--captions", choices=["align", "whisper", "even"], help="caption timing mode")
    a = ap.parse_args(argv)
    cfg = load_config(a.config, [*video_config(a.video), *a.set])  # the script's CONFIG: lines, then --set (which wins)
    ctx = Ctx(a.video, cfg, a.format)
    if a.command == "log":
        if len(a.extra) != 2:
            ap.error('usage: python -m dj log <video_dir> "<manual step>" <minutes>')
        log_metric(cfg, ctx.slug, f"manual: {a.extra[0]}", float(a.extra[1]) * 60)
        print(f"logged {a.extra[0]}: {a.extra[1]} min")
        return
    if a.command == "clean":
        print(f"[clean] {ctx.slug}")
        clean.run(ctx)
        return
    ffmpeg_bin(cfg)
    (ctx.build / "warnings.txt").unlink(missing_ok=True)  # fresh warning list for every run
    kw = {"captions": {"mode": a.captions}}
    steps = list(STEPS) if a.command == "all" else [a.command]
    t_all = time.time()
    for s in steps:
        print(f"[{s}] {ctx.slug}")
        t0 = time.time()
        STEPS[s](ctx, **kw.get(s, {}))
        log_metric(cfg, ctx.slug, s, time.time() - t0)
    if a.command == "all":
        log_metric(cfg, ctx.slug, "all", time.time() - t_all)
        print(f"done in {time.time() - t_all:.0f} s. Output: {ctx.build}")


if __name__ == "__main__":
    main()
