"""Highlight boxes that sit exactly on the letters, so a highlighter or a mark never looks misplaced on a page capture.

For a capture from capture_page.mjs (<name>.png + <name>.json): each mark box is
  1. moved back by the clip's negative origin (a capture whose clip started left of or above the page: the screenshot starts at 0,
     the boxes were measured from the negative x, so they sat that far right of the text), then
  2. snapped to the ink: inside the mark's row band the ink columns are grouped into words (gaps over 0.2 x the line height), the words
     the box covers by more than half are kept, and the box becomes their exact extent, rows and columns.
It also says whether the page is light or dark (the median colour of the block), so the card draws ONE highlighter style: a box in the
brand's highlight colour behind dark letters (on a light page: multiplied under the print; on a dark page: the glyphs drawn dark on it).

  PIPE tools/footage/snap_marks.py <capture.png> [--marks x,y,w,h ...]   (prints JSON: light, marks)
  As a module: snap(png_path, marks, clip_x=0, clip_y=0, scale=2) -> (light, marks)"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def snap(png, marks, clip_x=0.0, clip_y=0.0, scale=2.0, crop=None):
    a = np.asarray(Image.open(png).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    c = crop or [0, 0, W, H]
    region = a[c[1]:c[1] + c[3], c[0]:c[0] + c[2]].reshape(-1, 3)
    bg = np.median(region, axis=0)
    light = bool(bg.mean() > 128)
    ink = np.abs(a - bg).sum(axis=2) > 120
    dx, dy = min(0.0, clip_x) * scale, min(0.0, clip_y) * scale
    out = []
    for m in marks:
        x, y, w, h = m[0] + dx, m[1] + dy, m[2], m[3]
        y0, y1 = max(0, int(y)), min(H, int(y + h + 0.5))
        pad = int(0.35 * h)
        x0, x1 = max(0, int(x) - pad), min(W, int(x + w) + pad)
        if y1 <= y0 or x1 <= x0:
            out.append([round(x), round(y), round(w), round(h)])
            continue
        cols = ink[y0:y1, x0:x1].any(axis=0)
        gap = max(4, int(0.2 * h))
        words, start, run = [], None, 0
        for i, v in enumerate(cols):
            if v:
                if start is None:
                    start = i
                run = 0
                end = i
            elif start is not None:
                run += 1
                if run > gap:
                    words.append((start + x0, end + x0 + 1))
                    start, run = None, 0
        if start is not None:
            words.append((start + x0, end + x0 + 1))
        keep = [(a0, a1) for a0, a1 in words if min(a1, x + w) - max(a0, x) > 0.5 * (a1 - a0)]
        if not keep:
            out.append([round(x), round(y), round(w), round(h)])
            continue
        nx0, nx1 = min(k[0] for k in keep), max(k[1] for k in keep)
        rows = np.where(ink[y0:y1, nx0:nx1].any(axis=1))[0]
        ny0, ny1 = (y0 + rows[0], y0 + rows[-1] + 1) if len(rows) else (y0, y1)
        out.append([int(nx0), int(ny0), int(nx1 - nx0), int(ny1 - ny0)])
    return light, out


if __name__ == "__main__":
    png = Path(sys.argv[1])
    meta = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
    raw = [[m["x"], m["y"], m["w"], m["h"]] for m in meta.get("marks", [])]
    if "--marks" in sys.argv:
        raw = [[float(v) for v in s.split(",")] for s in sys.argv[sys.argv.index("--marks") + 1:]]
    light, marks = snap(png, raw, meta["clip"]["x"], meta["clip"]["y"], meta.get("scale", 2))
    print(json.dumps({"light": light, "marks": marks}))
