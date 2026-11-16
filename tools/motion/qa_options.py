"""Every picture a section's code shows has its options board (options_board.py): the pick is made from all the options, never the
first that fits. A note in words does not stop the first-fitting pick; this check does.

A section's options live in videos/<video>/options/OPTIONS_<section>.json (options_board.py draws its sheets from the same file): per
line a slot with a few easy candidates (about 3, good resolution), the pick, why it wins, and `media`, the clip / image / page names the shot uses.
This check reads the section's code (the .tsx files given), finds every media name it uses (quoted names that are a clip in
<media>/clips, an image in <media>/img or a page in <media>/pages), and fails when one is in no slot's `media`, when a slot has fewer
than 3 candidates (--min), or when a slot has no pick or no reason.

  PIPE tools/motion/qa_options.py --tsx src/<video folder>/<section>.tsx
      --options videos/<video>/options/OPTIONS_S01-S04.json --media PUBLIC/<video> [--min 3]
Exit 1 on any failure."""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsx", nargs="+", required=True)
    ap.add_argument("--options", nargs="+", required=True)
    ap.add_argument("--media", required=True, help="the video's folder in the public dir (its clips/, img/ and pages/)")
    ap.add_argument("--min", type=int, default=3)
    a = ap.parse_args()
    media = Path(a.media)
    clips = {p.stem for p in (media / "clips").glob("*.mp4")}
    imgs = {p.name for p in (media / "img").glob("*") if p.is_file()}
    pages = {p.stem for p in (media / "pages").glob("*.png")}
    bad = 0
    covered = set()
    for pat in a.options:
        for f in glob.glob(pat):
            spec = json.loads(Path(f).read_text(encoding="utf-8"))
            for s in spec["slots"]:
                covered.update(s.get("media", []))
                n = len(s.get("cands", []))
                if n < a.min:
                    print(f"FEW   {s['id']}: {n} candidates (the bar: {a.min}+)")
                    bad += 1
                if "pick" not in s or not str(s.get("pick_why", "")).strip():
                    print(f"NOPICK {s['id']}: no pick or no reason")
                    bad += 1
    used = []
    for pat in a.tsx:
        for f in glob.glob(str(pat)) or glob.glob(str(HERE / pat)):
            code = Path(f).read_text(encoding="utf-8")
            for m in re.finditer(r"""['"`]([A-Za-z0-9_\-\.]+)['"`]""", code):
                name = m.group(1)
                if name in clips or name in imgs or name in pages:
                    used.append((Path(f).name, name))
    seen = set()
    for f, name in used:
        if name in seen:
            continue
        seen.add(name)
        if name not in covered:
            print(f"NOBOARD {f}: '{name}' is shown but no options board names it")
            bad += 1
    print(f"{len(seen)} media names in the code, {len(covered)} named by the boards; {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
