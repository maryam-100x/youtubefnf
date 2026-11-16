"""The look board: a look shown on the studio's real pieces (src/_look/LookBoard.tsx: a turn card, a number, a stamp, the sign-off,
the subscribe ask, a Short's caption, a dated card, a kit3 card), one picture per look, for the creator to pick from and to see a
tweak before it is theirs (SETUP.md, step 11). The starting looks are tools/motion/looks/*.json, each shown in its own accent (its
key colour); the creator's own look is src/look.json in brand.ts's accent.

    PIPE tools/motion/look_board.py                   every starting look
    PIPE tools/motion/look_board.py bold clean        those starting looks
    PIPE tools/motion/look_board.py --file x.json     a look in a file (a tweak, before it goes into src/look.json)
    PIPE tools/motion/look_board.py --current         the creator's own look (src/look.json, brand.ts's accent)
    PIPE tools/motion/look_board.py --check x.json    only check a look file (every key a starting look has, the fonts on the shelf)

One bundle and one Chrome for all of them (stills.mjs). Writes MEDIA/looks/<name>.jpg and prints `LOOK <name> <path>` per picture.
The fonts come from Google Fonts while it renders, so it needs the internet.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, MEDIA, MOTION, NODE, TMP, apply_env  # noqa: E402

LOOKS = MOTION / "looks"
CURRENT = MOTION / "src" / "look.json"
OUT = MEDIA / "looks"
FPS = 60
FRAME = round(2.5 * FPS)   # LookBoard's LOOK_BOARD_FRAME (src/_look/LookBoard.tsx)
FONTS_TS = MOTION / "src" / "fonts.ts"
CHOICES = {"shape.shadow": {"soft", "hard", "none"}, "stamp.style": {"fill", "underline", "box"}, "signoff.design": {"corner", "bar"},
           "subscribe.design": {"corner", "bar"}}


def shelf():
    """the font families on the shelf: the names in fonts.ts's SHELF (quoted, or a bare name that is its own import)"""
    block = re.search(r"const SHELF[^{]*\{(.*?)\};", FONTS_TS.read_text(encoding="utf-8"), re.S)[1]
    return {m[0] or m[1] for m in re.findall(r"'([^']+)'\s*:|(?:^|,)\s*([A-Z][A-Za-z]+)\s*(?=,|$)", block, re.M)}


def problems(look, ref=None, path=""):
    """what is wrong with a look: a key the starting looks have that it lacks, a value of the wrong kind, a font not on the shelf"""
    ref = ref if ref is not None else json.loads((LOOKS / "clean.json").read_text(encoding="utf-8"))
    out = []
    for k, v in ref.items():
        at = f"{path}{k}"
        if k not in look:
            out.append(f"{at} is missing")
        elif isinstance(v, dict):
            out += problems(look[k], v, at + ".") if isinstance(look[k], dict) else [f"{at} should be a group of keys"]
        elif isinstance(v, str) and v.startswith("#") and not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(look[k])):
            out.append(f"{at} should be a colour like #1A2B3C, not {look[k]!r}")
        elif isinstance(v, (int, float)) and not isinstance(look[k], (int, float)):
            out.append(f"{at} should be a number, not {look[k]!r}")
        elif isinstance(v, list) and not (isinstance(look[k], list) and all(isinstance(w, int) for w in look[k])):
            out.append(f"{at} should be a list of weights like [400, 700]")
        elif at in CHOICES and look[k] not in CHOICES[at]:
            out.append(f"{at} is one of {', '.join(sorted(CHOICES[at]))}, not {look[k]!r}")
    if not path:
        have = shelf()
        for role in ("display", "text", "caption"):
            fam = look.get("fonts", {}).get(role, {}).get("family")
            if fam and fam not in have:
                out.append(f"fonts.{role} {fam!r} is not on the shelf (src/fonts.ts): add its @remotion/google-fonts import and its SHELF "
                           f"line first")
        if look.get("colors", {}).get("key") != look.get("captions", {}).get("key"):
            out.append("colors.key and captions.key are the look's one accent: the same colour")
    return out


def load(f):
    look = json.loads(Path(f).read_text(encoding="utf-8"))
    bad = problems(look)
    if bad:
        raise SystemExit(f"look_board: {f}:\n  " + "\n  ".join(bad))
    return look


def variants(args):
    if "--current" in args:
        load(CURRENT)
        return [{"tag": "current", "props": {}}]
    if "--file" in args:
        f = Path(args[args.index("--file") + 1])
        look = load(f)
        return [{"tag": f.stem, "props": {"look": look, "accent": look["colors"]["key"]}}]
    names = [a for a in args if not a.startswith("-")] or sorted(p.stem for p in LOOKS.glob("*.json"))
    out = []
    for n in names:
        f = LOOKS / f"{n}.json"
        if not f.exists():
            raise SystemExit(f"no look {n!r}: the starting looks are {', '.join(sorted(p.stem for p in LOOKS.glob('*.json')))}")
        look = load(f)
        out.append({"tag": n, "props": {"look": look, "accent": look["colors"]["key"]}})
    return out


def main(args):
    if "--check" in args:
        f = args[args.index("--check") + 1]
        load(f)
        print(f"{f}: a whole look")
        return 0
    apply_env()
    vs = variants(args)
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="look_board_", dir=TMP))
    try:
        pub = work / "public"   # the board needs no media: an empty public dir keeps the bundle small
        pub.mkdir()
        env = {**os.environ, "QA_COMP": "LookBoard", "QA_PUBLIC": str(pub), "QA_VARIANTS": json.dumps(vs), "REMOTION_FPS": str(FPS)}
        r = subprocess.run([NODE, "stills.mjs", str(work / "stills"), "1", str(FRAME)], cwd=MOTION, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise SystemExit("look_board: the render failed:\n" + (r.stderr or r.stdout)[-3000:])
        for v in vs:
            png = work / "stills" / f"f_{FRAME}_{v['tag']}.png"
            jpg = OUT / f"{v['tag']}.jpg"
            subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(png), "-q:v", "2", str(jpg)], check=True)
            print(f"LOOK {v['tag']} {jpg}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
