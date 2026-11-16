"""The look board: a look shown on the studio's real pieces (src/_look/LookBoard.tsx: a turn card, a number, a stamp, the sign-off,
the subscribe ask, a Short's caption, a dated card, a kit3 card), one picture per look, for the creator to pick from and to see a
tweak before it is theirs (SETUP.md, step 11). The starting looks are tools/motion/looks/*.json, each shown in its own accent (its
key colour); the creator's own look is src/look.json in brand.ts's accent.

    PIPE tools/motion/look_board.py                   every starting look
    PIPE tools/motion/look_board.py bold clean        those starting looks
    PIPE tools/motion/look_board.py --file x.json     a look in a file (a tweak, before it goes into src/look.json)
    PIPE tools/motion/look_board.py --current         the creator's own look (src/look.json, brand.ts's accent)
    PIPE tools/motion/look_board.py --check x.json    only check a look file (every key a starting look has, the fonts on the shelf)
    --scale 2                                         any of them at twice the size (every tile a full 1920 x 1080 frame), to check

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
    named = [a for i, a in enumerate(args) if not a.startswith("-") and (i == 0 or args[i - 1] != "--scale")]
    names = named or sorted(p.stem for p in LOOKS.glob("*.json"))
    out = []
    for n in names:
        f = LOOKS / f"{n}.json"
        if not f.exists():
            raise SystemExit(f"no look {n!r}: the starting looks are {', '.join(sorted(p.stem for p in LOOKS.glob('*.json')))}")
        look = load(f)
        out.append({"tag": n, "props": {"look": look, "accent": look["colors"]["key"]}})
    return out


def _hex(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _sky(w, h, stops):
    """a vertical gradient through (position 0-1, '#RRGGBB') stops, the last colour held to the bottom"""
    from PIL import Image, ImageDraw
    stops = [(p, _hex(c)) for p, c in stops] + [(1.0, _hex(stops[-1][1]))]
    img = Image.new("RGB", (w, h))
    dr = ImageDraw.Draw(img)
    for y in range(h):
        p = y / (h - 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= p <= p1:
                k = (p - p0) / max(p1 - p0, 1e-6)
                dr.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * k) for a, b in zip(c0, c1)))
                break
    return img


def _glow(img, cx, cy, r, colour, core):
    """a sun: a soft glow of radius r and a disc of radius core"""
    from PIL import Image, ImageDraw, ImageFilter
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55], fill=_hex(colour) + (150,))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.35))
    ImageDraw.Draw(layer).ellipse([cx - core, cy - core, cx + core, cy + core], fill=_hex(colour) + (255,))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def _ridge(img, seed, base, amp, rough, colour):
    import math
    import random
    from PIL import ImageDraw
    w, h = img.size
    k = w / 1920
    rnd = random.Random(seed)
    p1, p2, p3 = (rnd.random() * 6.28 for _ in range(3))
    pts = [(x, base * k - amp * k * (0.55 + 0.25 * math.sin(x / (260 * k) + p1) + 0.14 * math.sin(x / (97 * k) + p2)
                                      + rough * math.sin(x / (31 * k) + p3))) for x in range(0, w + 24, 24)]
    ImageDraw.Draw(img).polygon([(0, h)] + pts + [(w, h)], fill=_hex(colour))


def _city(img, seed, colour, lit, max_h):
    import random
    from PIL import ImageDraw
    w, h = img.size
    rnd = random.Random(seed)
    dr = ImageDraw.Draw(img)
    x = -20
    while x < w + 20:
        bw, bh = 70 + rnd.random() * 120, 120 + rnd.random() * max_h
        top = h - bh
        dr.rectangle([x, top, x + bw, h], fill=_hex(colour))
        for wy in range(int(top + 22), h - 20, 34):
            for wx in range(int(x + 14), int(x + bw - 18), 26):
                if rnd.random() < lit:
                    a = 0.55 + rnd.random() * 0.4
                    dr.rectangle([wx, wy, wx + 11, wy + 15], fill=tuple(round(c * a + b * (1 - a)) for c, b in zip(_hex("#FFD27F"), _hex(colour))))
        x += bw + 4 + rnd.random() * 10


def board_pictures(pub):
    """The two pictures kit3's number needs as files (src/_look/LookBoard.tsx): board/ground.jpg, a city at dusk behind it, and
    board/cover.jpg, the thing it counts (a cover: a sunset over the sea). Drawn here, nobody's photo."""
    from PIL import ImageDraw
    d = pub / "board"
    d.mkdir(parents=True, exist_ok=True)
    g = _sky(1920, 1080, [(0, "#1D2240"), (0.55, "#6E4664"), (0.8, "#E9966B")])
    g = _glow(g, 1390, 610, 260, "#FFD9A6", 74).convert("RGB")
    _ridge(g, 7, 760, 260, 0.06, "#4A3A5C")
    _city(g, 11, "#181626", 0.28, 420)
    g.save(d / "ground.jpg", quality=92)
    c = _sky(1000, 1000, [(0, "#24476F"), (0.45, "#6F98C0"), (0.6, "#F0C595")])
    c = _glow(c, 500, 600, 300, "#FFE0B0", 86).convert("RGB")
    dr = ImageDraw.Draw(c)
    sea = _sky(1000, 400, [(0, "#3D6E9E"), (1, "#0C223D")])
    c.paste(sea, (0, 600))
    for k in range(7):
        half = 110 - k * 12
        a = 0.6 - k * 0.07
        dr.rectangle([500 - half, 622 + k * 26, 500 + half, 627 + k * 26],
                     fill=tuple(round(x * a + y * (1 - a)) for x, y in zip(_hex("#FFE0B0"), _hex("#2D5A86"))))
    c.save(d / "cover.jpg", quality=92)


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
        pub = work / "public"   # the board's own two pictures, nothing else: a small bundle
        pub.mkdir()
        board_pictures(pub)
        scale = args[args.index("--scale") + 1] if "--scale" in args else "1"
        env = {**os.environ, "QA_COMP": "LookBoard", "QA_PUBLIC": str(pub), "QA_VARIANTS": json.dumps(vs), "REMOTION_FPS": str(FPS)}
        r = subprocess.run([NODE, "stills.mjs", str(work / "stills"), scale, str(FRAME)], cwd=MOTION, env=env, capture_output=True,
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
