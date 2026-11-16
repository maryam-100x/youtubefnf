"""Do the sounds still belong to their pictures? Every effect must still apply to what is on screen, be in sync and not be a
leftover from a visual that was removed.

`qa_clips.py` (its audio-only audit render) logs every sound cue's anchor time to out/sfx_cues_<comp>.csv (the cue's name is its
effect's file name in SFX, without the extension). This renders one still just after each cue of a sound that MEANS something on
screen (a marker = a stroke being drawn, a shutter = a photo or a flash, correct = a tick, scan = a scan, paper = a card or page
arriving ...) and tiles them into labelled contact sheets: look at every tile; a cue whose tile shows nothing of its kind is a
leftover from a removed visual or needs its picture (a shutter with no flash gets one). The other half of the check is
`npx tsc --noEmit -p . --noUnusedParameters`: a component prop that is never read is a removed visual, and a cue on that prop's time
plays over nothing.

  PIPE tools/motion/qa_sfx.py <Composition> [--names marker,shutter,...] [--out DIR]"""
import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import NODE, WINDOWS  # noqa: E402

HERE = Path(__file__).resolve().parent
FPS = 60
# how long after the cue its picture is clearest (s), by effect name: a stroke half drawn, a card landed, a flash at its peak
AFTER = {"marker": 0.3, "shutter": 0.06, "correct": 0.3, "scan": 0.35, "granted": 0.3, "register": 0.15, "typing": 0.1, "glitch": 0.05,
         "glitch_long": 0.1, "slam": 0.1, "sub": 0.1, "flash": 0.05, "message": 0.25, "paper": 0.25}


def _font(size):
    for p in ("C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comp")
    ap.add_argument("--names", default=",".join(AFTER), help="effect names to check (default: every specific one)")
    ap.add_argument("--out", default=str(HERE / "out" / "qa_sfx"))
    a = ap.parse_args()
    names = [n for n in a.names.split(",") if n]
    rows = list(csv.DictReader(open(HERE / "out" / f"sfx_cues_{a.comp}.csv", encoding="utf-8")))
    cues = [(int(r["frame"]) + round(AFTER.get(r["name"], 0.2) * FPS), r["name"], float(r["seconds"])) for r in rows if r["name"] in names]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"{len(cues)} cues of {', '.join(names)}")
    env = dict(os.environ, QA_COMP=a.comp)
    subprocess.run([NODE, "stills.mjs", str(out), "0.3333333", *[str(f) for f, _, _ in cues]], cwd=HERE, env=env, check=True, shell=WINDOWS)
    font = _font(18)
    cols, tw, th = 5, 640, 360
    for s in range(0, len(cues), 20):
        part = cues[s:s + 20]
        rows_n = (len(part) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + 4), rows_n * (th + 28)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, (f, n, sec) in enumerate(part):
            x, y = (i % cols) * (tw + 4), (i // cols) * (th + 28)
            d.text((x + 4, y + 2), f"#{s + i} {n} @ {int(sec // 60)}:{sec % 60:05.2f}", fill=(255, 225, 70), font=font)
            sheet.paste(Image.open(out / f"f_{f}.png").convert("RGB").resize((tw, th)), (x, y + 28))
        p = out / f"sfx_sheet_{s // 20 + 1}.jpg"
        sheet.save(p, quality=85)
        print(p)


if __name__ == "__main__":
    main()
