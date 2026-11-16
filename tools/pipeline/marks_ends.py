"""Every lit mark box ends where its word ends (a headline "Setting a New Industry Record" lit only to "Recor" reads as a mistake).
For each mark box of a pages json (x, y, w, h on the page image), the
page's own ink in the box's line band is read past each edge: ink that goes on within a word gap of the box's right edge (or left edge),
for more than a punctuation mark's width, means the box stops (or starts) inside a word.

  PIPE tools/pipeline/marks_ends.py <pages.json> <page image dir> [--used <code glob>]

--used: only the pages a Rec/Pic in that code names. --sheet out.png: every flagged box drawn on its page, for the eye (punctuation
right after a word, an icon's frame and an apostrophe-s also trip it: judge each on the sheet; a typical run: 17 flags, 2 real, a
short duplicate box under one word and a 16-px stub at a line wrap). Exit 1 with any box cut inside a word."""
import argparse
import fnmatch
import glob
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def ink_cols(a, y0, y1, x0, x1, bg):
    band = a[y0:y1, max(0, x0):min(a.shape[1], x1)]
    if band.size == 0:
        return np.zeros(0, bool)
    return (np.abs(band - bg) > 60).any(axis=0)


def word_gap(a, b, bg, y0, y1):
    """the narrowest gap that is a word gap on this line, from the box's own text: its gaps sorted, split at the biggest jump (letter
    spacing below, word spaces above); a box with one word or no clear jump: 0.2 x its height. None when the box holds no text-like ink
    (one solid run as wide as the box)"""
    x, w, h = b["x"], b["w"], b["h"]
    cols = ink_cols(a, y0, y1, int(x), int(x + w), bg)
    if not cols.any():
        return None
    idx = np.flatnonzero(cols)
    cols = cols[idx[0]:idx[-1] + 1]
    gaps, k = [], 0
    while k < len(cols):
        if cols[k]:
            k += 1
            continue
        g = 0
        while k + g < len(cols) and not cols[k + g]:
            g += 1
        gaps.append(g)
        k += g
    if len(gaps) < 2:
        return None if not gaps and len(cols) > 3 * h else max(3, int(0.2 * h))
    gs = sorted(gaps)
    jumps = [(gs[i + 1] / max(1, gs[i]), i) for i in range(len(gs) - 1)]
    r, i = max(jumps)
    if r < 1.8:
        return max(3, int(0.2 * h))
    return max(3, (gs[i] + gs[i + 1]) // 2 + 1)


def side(a, b, bg, right):
    """(px of ink that carries on past the edge within a word gap, px of empty columns first) or None"""
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    y0, y1 = int(y + 0.15 * h), int(y + 0.85 * h)       # the letters' body, not the line above or below
    gap = word_gap(a, b, bg, y0, y1)
    if gap is None:
        return None                                       # no text in the box (an icon, a logo): nothing to cut
    reach = int(1.6 * h)
    if right:
        c0 = int(round(x + w))
        cols = ink_cols(a, y0, y1, c0, c0 + reach, bg)
    else:
        c0 = int(round(x))
        cols = ink_cols(a, y0, y1, c0 - reach, c0, bg)[::-1]
    if len(cols) == 0:
        return None
    empty = 0
    while empty < len(cols) and not cols[empty]:
        empty += 1
    if empty >= gap or empty == len(cols):
        return None                                       # the box ends in a word gap: fine
    run = 0
    k = empty
    while k < len(cols):
        if cols[k]:
            run = k - empty + 1
            k += 1
            continue
        g = 0
        while k + g < len(cols) and not cols[k + g]:
            g += 1
        if g >= gap:
            break
        k += g
    if run <= 0.25 * h:                                   # a comma, a full stop, a closing quote
        return None
    return run, empty


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages")
    ap.add_argument("imgdir")
    ap.add_argument("--used", help="a glob of the code that names the pages (Rec name=, Pic path)")
    ap.add_argument("--sheet", help="draw every flagged box on its page into this png")
    a = ap.parse_args()
    d = json.loads(Path(a.pages).read_text(encoding="utf-8"))
    keys = list(d)
    if a.used:
        # 'src/<folder>/*.tsx' reads the subfolder files the film imports too (rebuilt shots in a subfolder, src/v12/fix1/)
        head, _, tail = a.used.replace("\\", "/").rpartition("/")
        files = {Path(x).resolve() for x in glob.glob(a.used)}
        if head and "*" not in head and Path(head).is_dir():
            sys.path.append(str(Path(__file__).resolve().parents[1] / "motion"))
            from codefiles import code_files
            files |= {f for f in code_files(head, (".ts", ".tsx")) if f.parent != Path(head).resolve() and fnmatch.fnmatch(f.name, tail)}
        code = "".join(p.read_text(encoding="utf-8") for p in sorted(files))
        keys = [k for k in keys if re.search(rf"['\"/]{re.escape(k)}(?:\.png)?['\"]", code)]
    bad = n = 0
    tiles = []
    for k in keys:
        e = d[k]
        src = Path(a.imgdir) / e["src"]
        if not src.exists() or not e.get("marks"):
            continue
        img = np.asarray(Image.open(src).convert("L")).astype(float)
        bg = float(np.median(img))
        marks = e["marks"]
        boxes = marks if isinstance(marks, list) else [dict(b, phrase=ph) for ph, bs in marks.items() for b in bs]
        for b in boxes:
            n += 1
            for right in (True, False):
                r = side(img, b, bg, right)
                if r:
                    bad += 1
                    run, empty = r
                    print(f"CUT  {k}: \"{b.get('phrase', '?')}\" box {'ends' if right else 'starts'} inside a word: ink goes on {run} px "
                          f"{'past' if right else 'before'} its {'right' if right else 'left'} edge after a {empty}-px gap (box x {b['x']:.0f} "
                          f"w {b['w']:.0f} h {b['h']:.0f})")
                    if a.sheet:
                        from PIL import ImageDraw
                        im = Image.open(src).convert("RGB")
                        ImageDraw.Draw(im).rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]], outline=(255, 0, 0), width=3)
                        ex, h = (b["x"] + b["w"]) if right else b["x"], b["h"]
                        c = im.crop((int(ex - 3 * h), int(b["y"] - 0.4 * h), int(ex + 3 * h), int(b["y"] + 1.4 * h)))
                        c.thumbnail((600, 200))
                        t = Image.new("RGB", (600, 230), "white")
                        t.paste(c, (0, 30))
                        ImageDraw.Draw(t).text((4, 4), f"{k[:44]} {'end' if right else 'start'}: {b.get('phrase', '?')[:40]}", fill=(0, 0, 0))
                        tiles.append(t)
    if a.sheet and tiles:
        W = Image.new("RGB", (1200, 230 * ((len(tiles) + 1) // 2)), "white")
        for i, t in enumerate(tiles):
            W.paste(t, ((i % 2) * 600, (i // 2) * 230))
        W.save(a.sheet)
        print(f"sheet -> {a.sheet}")
    print(f"{n} boxes on {len(keys)} pages read; {bad} cut inside a word")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
