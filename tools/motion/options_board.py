"""The options boards: a premium edit collects every possible option before it picks. One contact sheet per line of a section, every
candidate on it side by side (a clip as three frames: just after its in-point, its middle, just before its out-point; a still, page or
built picture as itself), the pick framed in the brand colour (src/brand.ts), each labelled with its source, its time and what it shows.

The spec is a JSON file (videos/<video>/options/<section>.json): {"prefix": {"E": "<folder>", ...}, "slots": [{"id": "S01a", "words": "...",
"cands": [{"src": "@E/file.mp4", "t": [in, out], "vf": "crop=...", "what": "...", "why": "..."} | {"img": "@IMG/file.jpg", ...} |
{"built": "what it is", "img": "...optional preview..."}, ...], "pick": 0, "pick_why": "...", "media": ["clip or img names the shot uses"]}]}.
Paths "@KEY/rest" take the spec's prefix[KEY]. Sheets go next to the spec as <slot>_<n>.jpg (n = 1, 2 ... when a slot has more than 6
candidates).

  PIPE tools/motion/options_board.py <spec.json> [--only S01a,S02c]
  PIPE tools/motion/options_board.py <spec.json> --md      the boards as text (<spec>.md), no sheets"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand import BRAND_RGB  # noqa: E402

TW, TH = 400, 225
BRAND = BRAND_RGB
PER = 6


def path(p, prefix):
    """"@KEY/rest" -> prefix[KEY] + rest; anything else as it is"""
    if p.startswith("@"):
        k, _, rest = p[1:].partition("/")
        return Path(prefix[k]) / rest
    return Path(p)


def frame(src, t, vf):
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-threads", "2", "-ss", f"{max(0.0, t):.3f}", "-i", str(src), "-frames:v", "1", "-an", "-vf",
           (vf + "," if vf else "") + f"scale={TW}:{TH}:force_original_aspect_ratio=increase,crop={TW}:{TH}", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    if len(raw) < TW * TH * 3:
        return Image.new("RGB", (TW, TH), (60, 0, 0))
    return Image.frombytes("RGB", (TW, TH), raw[:TW * TH * 3])


def still(p):
    try:
        im = Image.open(p).convert("RGB")
    except Exception:
        return Image.new("RGB", (TW, TH), (60, 0, 0))
    im.thumbnail((TW * 3, TH))
    can = Image.new("RGB", (TW * 3, TH), (24, 24, 24))
    can.paste(im, ((TW * 3 - im.width) // 2, (TH - im.height) // 2))
    return can


def wrap(d, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def board(slot, prefix, outdir):
    try:
        f1, f2 = ImageFont.truetype("arialbd.ttf", 22), ImageFont.truetype("arial.ttf", 17)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    cands = slot["cands"]
    out = []
    for page in range((len(cands) + PER - 1) // PER):
        part = cands[page * PER:(page + 1) * PER]
        rowh = TH + 70
        W = TW * 3 + 640
        sh = Image.new("RGB", (W, 60 + rowh * len(part)), (250, 250, 250))
        d = ImageDraw.Draw(sh)
        d.text((10, 8), f'{slot["id"]}  "{slot["words"]}"', fill="black", font=f1)
        d.text((10, 34), f'pick: #{slot["pick"] + 1}  {slot.get("pick_why", "")[:170]}', fill=(40, 90, 0), font=f2)
        for i, c in enumerate(part):
            k = page * PER + i
            y = 60 + i * rowh
            if "src" in c:
                src = path(c["src"], prefix)
                a, b = c["t"]
                pad = min(0.2, (b - a) / 4)
                for j, t in enumerate((a + pad, (a + b) / 2, b - pad)):
                    sh.paste(frame(src, t, c.get("vf", "")), (j * TW, y))
                label = f'#{k + 1} {src.name}  {a:.2f}-{b:.2f} s ({b - a:.2f} s)'
            elif "img" in c:
                sh.paste(still(path(c["img"], prefix)), (0, y))
                label = f'#{k + 1} {path(c["img"], prefix).name}' + (f'  (built: {c["built"]})' if "built" in c else "")
            else:
                d.rectangle([0, y, TW * 3 - 1, y + TH - 1], fill=(30, 30, 30))
                for n, ln in enumerate(wrap(d, "BUILT: " + c.get("built", ""), f1, TW * 3 - 40)[:6]):
                    d.text((20, y + 20 + n * 30), ln, fill="white", font=f1)
                label = f"#{k + 1} built"
            if k == slot["pick"]:
                d.rectangle([0, y, TW * 3 - 1, y + TH - 1], outline=BRAND, width=8)
            d.text((6, y + TH + 4), label[:120], fill="black", font=f2)
            tx = TW * 3 + 14
            lines = wrap(d, c.get("what", ""), f2, 610) + [""] + wrap(d, c.get("why", ""), f2, 610)
            for n, ln in enumerate(lines[:12]):
                d.text((tx, y + 4 + n * 21), ln, fill="black", font=f2)
        p = outdir / f'{slot["id"]}_{page + 1}.jpg'
        sh.save(p, quality=84)
        out.append(p)
    return out


def markdown(spec, outdir, md):
    """the boards as text (OPTIONS_<section>.md): per line every candidate (source, time, what it shows, its case), the pick and why"""
    out = [f"# Options boards: {spec.get('section', '')}", "",
           "5+ candidates per line from different sources, every source scanned whole first (its 1-fps sheets in `options/sources/`, by "
           "source_sheet.py; the scanners' catalogues `options/sources/CATALOG_*.md`), the pick and why it beats the rest. Written from "
           f"`{Path(md).with_suffix('.json').name}` by `tools/motion/options_board.py --md` (edit the JSON, not this file); the sheets are "
           "`options/<line>_<n>.jpg` (the pick framed in the brand colour). `qa_options.py` fails a shot whose media no board names.", ""]
    for s in spec["slots"]:
        n = (len(s["cands"]) + PER - 1) // PER
        out += [f"## {s['id']} \"{s['words']}\"", "", f"Sheets: " + ", ".join(f"`{s['id']}_{k + 1}.jpg`" for k in range(n)), ""]
        for i, c in enumerate(s["cands"]):
            if "src" in c:
                src = f"`{path(c['src'], spec['prefix']).name}` {c['t'][0]:.2f}-{c['t'][1]:.2f} s" + (f" ({c['vf']})" if c.get("vf") else "")
            elif "img" in c:
                src = f"`{path(c['img'], spec['prefix']).name}`" + (" (built)" if "built" in c else "")
            else:
                src = "built"
            what = c.get("what", "") if "built" not in c or "img" in c else c["built"]
            if "built" in c and "img" in c:
                what = f"{c['built']} ({c.get('what', '')})"
            mark = "**PICK** " if i == s["pick"] else ""
            out.append(f"{i + 1}. {mark}{src}: {what}; {c.get('why', '')}")
        out += ["", f"**Pick: #{s['pick'] + 1}.** {s.get('pick_why', '')}", f"Media: {', '.join('`' + m + '`' for m in s.get('media', []))}", ""]
    Path(md).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--only")
    ap.add_argument("--md", action="store_true", help="only write OPTIONS_<section>.md next to the spec (no sheets)")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    outdir = Path(a.spec).parent
    if a.md:
        return markdown(spec, outdir, Path(a.spec).with_suffix(".md"))
    only = set(a.only.split(",")) if a.only else None
    for slot in spec["slots"]:
        if only and slot["id"] not in only:
            continue
        for p in board(slot, spec["prefix"], outdir):
            print(p)


if __name__ == "__main__":
    main()
