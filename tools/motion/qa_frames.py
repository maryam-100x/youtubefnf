"""QA stills at words of the voice: each spec is BEAT:phrase[:offset_s] (or a plain number of seconds); renders them with stills.mjs
(one bundle) and tiles them into one labelled sheet.

  QA_SRC=<src folder with words.json and beats.json> QA_COMP=<Composition> PIPE tools/motion/qa_frames.py <name> "S10:the launch:0.4" "S08:a city skyline:0.5" 120.5 ...
The sheet goes to PUBLIC/review/qa_<name>.jpg, its stills to PUBLIC/review/frames."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import NODE, PUBLIC, WINDOWS  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = os.environ.get("QA_SRC")
if not SRC:
    raise SystemExit("set QA_SRC to the src folder that holds the video's words.json and beats.json (and QA_COMP to its composition)")
W = json.loads((HERE / "src" / SRC / "words.json").read_text(encoding="utf-8"))
B = {b["id"]: b for b in json.loads((HERE / "src" / SRC / "beats.json").read_text(encoding="utf-8"))["beats"]}
OUT = PUBLIC / "review" / "frames"
LABEL = (255, 214, 64)   # the sheet's caption colour (a review sheet, never on screen in a video)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("'", "").replace("\u2019", ""))


def w(beat, phrase, nth=0):
    toks = [norm(t) for t in phrase.split() if norm(t)]
    seen = 0
    for i in range(len(W)):
        if W[i]["beat"] == beat and all(i + k < len(W) and W[i + k]["beat"] == beat and norm(W[i + k]["w"]) == t for k, t in enumerate(toks)):
            if seen == nth:
                return W[i]["start"]
            seen += 1
    raise SystemExit(f'"{phrase}" is not in {beat}')


def when(spec):
    try:
        return float(spec)
    except ValueError:
        parts = spec.split(":")
        beat, phrase = parts[0], parts[1]
        off = float(parts[2]) if len(parts) > 2 else 0.0
        t = B[beat]["start"] if phrase == "" else w(beat, phrase)
        return t + off


def _font(size):
    for p in ("C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main(name, specs, scale=0.5):
    frames = [round(when(s) * 60) for s in specs]
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([NODE, "stills.mjs", str(OUT), str(scale)] + [str(f) for f in frames], cwd=HERE, check=True, shell=WINDOWS)
    ims = [Image.open(OUT / f"f_{f}.png") for f in frames]
    w0, h0 = ims[0].size
    cols = (4 if w0 < h0 else 2) if len(ims) > 1 else 1
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w0, rows * (h0 + 30)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    font = _font(20)
    for i, (im, spec, f) in enumerate(zip(ims, specs, frames)):
        x, y = (i % cols) * w0, (i // cols) * (h0 + 30)
        d.text((x + 6, y + 4), f"{spec}  ({f / 60:.2f} s)", fill=LABEL, font=font)
        sheet.paste(im, (x, y + 30))
    dst = OUT.parent / f"qa_{name}.jpg"
    sheet.save(dst, quality=88)
    print(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
