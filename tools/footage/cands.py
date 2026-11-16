"""Every candidate picture for one line, out of the creator's whole library, so all the options are weighed instead of the first one
that roughly fits: the footage brain's records (kb/footage/brain/*.json: every shot of every source and every still, with what is in
it) searched for the line's words, ranked by how many of them each record matches, and laid out as a contact sheet of the records'
middle frames with id, time and description, to be looked at and picked by eye. No model loads (find_shot.py is the ranked search with
embeddings and the 9:16 windows).

  PIPE tools/footage/cands.py <out.jpg> <word> [<word> ...] [--max 40] [--src A1,IMG]"""
import argparse
import re
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402
import find_shot as FS  # noqa: E402
from sheetfont import font  # noqa: E402


def text(r):
    s = r.get("subject") or {}
    parts = [r.get("desc", ""), r.get("action", ""), r.get("setting", ""), " ".join(r.get("who", [])), " ".join(r.get("what", [])),
             s.get("label", "") if isinstance(s, dict) else str(s), " ".join(r.get("text", [])), " ".join(c[2] for c in r.get("cat", [])),
             " ".join(m.get("note", "") for m in r.get("moments", []))]
    return " ".join(p if isinstance(p, str) else " ".join(map(str, p)) for p in parts).lower()


def thumb(r):
    """The record's middle frame (the brain's frames), or the still itself."""
    if r.get("kind") == "image":
        return Path(r["file"])
    fl = r.get("frames", [])
    if not fl:
        return None
    kf = B.key_file(r["src"] if r["src"] in B.MASTERS else r["id"].split("@")[0])
    return B.WORK / "frames" / kf / f"{fl[len(fl) // 2]:07d}.jpg"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("words", nargs="+")
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--src", default="", help="only these sources (keys of kb/footage/sources.json)")
    a = ap.parse_args()
    recs = FS.load_records(set(a.src.split(",")) if a.src else None)
    if not recs:
        raise SystemExit("no records in " + str(B.BRAIN))
    scored = []
    for r in recs:
        t = text(r)
        hits = [w for w in a.words if re.search(r"\b" + re.escape(w.lower()), t)]
        if hits:
            scored.append((len(hits), r, hits))
    scored.sort(key=lambda s: (-s[0], s[1].get("id", ""), s[1].get("in", 0)))
    scored = scored[:a.max]
    TW, TH, TXT = 320, 180, 92
    cols = 5
    rows = (len(scored) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * TW, max(1, rows) * (TH + TXT)), "white")
    d = ImageDraw.Draw(sheet)
    f = font(11, bold=False)
    for i, (n, r, hits) in enumerate(scored):
        p = thumb(r)
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((TW, TH))
        except Exception:  # noqa: BLE001
            im = Image.new("RGB", (TW, TH), "grey")
        cx, cy = (i % cols) * TW, (i // cols) * (TH + TXT)
        sheet.paste(im, (cx + (TW - im.width) // 2, cy))
        when = "" if r.get("kind") == "image" else f" {B.mmss(r['in'])}-{B.mmss(r['out'])}"
        d.text((cx + 3, cy + TH + 2), f"#{i} {r['id'][:34]}{when}", fill="black", font=f)
        for k, line in enumerate(textwrap.wrap(r.get("desc", ""), 52)[:5]):
            d.text((cx + 3, cy + TH + 15 + k * 13), line, fill="#222", font=f)
        print(f"#{i:2d} [{n}] {r['id']}{when}  {r.get('desc', '')[:150]}")
    sheet.save(a.out, quality=85)
    print(len(scored), "candidates ->", a.out)


if __name__ == "__main__":
    main()
