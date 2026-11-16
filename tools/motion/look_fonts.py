"""The look's font files that a picture needs on disk (a browser loads the rest from Google Fonts itself): the display family at its
display weight as PUBLIC/kit3d/fonts/display.ttf, the 3D number's font (kit3d's Number3D cuts its digits from a font file). Run it
after the look changes (the setup's look step does). The Shorts captions fetch their own font (dj, by family name).

    PIPE tools/motion/look_fonts.py            fetch it for src/look.json (again only when the family or weight changed)
    PIPE tools/motion/look_fonts.py --check    say whether the file on disk is the look's
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MOTION, PUBLIC  # noqa: E402

LOOK = MOTION / "src" / "look.json"
OUT = PUBLIC / "kit3d" / "fonts" / "display.ttf"
STAMP = OUT.with_suffix(".json")   # which family and weight the file is


def want():
    look = json.loads(LOOK.read_text(encoding="utf-8"))
    return {"family": look["fonts"]["display"]["family"], "weight": int(look["type"]["display_weight"])}


def fetch(family, weight):
    """the family's TTF at `weight` through Google Fonts' CSS API (a plain client gets TTF links, a browser would get woff2)"""
    q = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}"
    css = urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": "curl/8"}), timeout=30).read().decode()
    m = re.search(r"url\((https://[^)]+\.ttf)\)", css)
    if not m:
        raise SystemExit(f"Google Fonts gave no TTF for {family} {weight} (is the family spelled as on fonts.google.com?)")
    return urllib.request.urlopen(urllib.request.Request(m[1], headers={"User-Agent": "curl/8"}), timeout=60).read()


def main():
    w = want()
    have = json.loads(STAMP.read_text(encoding="utf-8")) if STAMP.exists() and OUT.exists() else None
    if "--check" in sys.argv:
        print(f"{OUT}: " + ("the look's" if have == w else f"not the look's (have {have}, the look wants {w})"))
        return 0 if have == w else 1
    if have == w:
        print(f"{OUT} is already {w['family']} {w['weight']}")
        return 0
    data = fetch(w["family"], w["weight"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    STAMP.write_text(json.dumps(w), encoding="utf-8")
    print(f"{OUT}: {w['family']} {w['weight']} ({len(data) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
