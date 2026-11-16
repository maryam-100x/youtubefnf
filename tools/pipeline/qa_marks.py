"""qa_marks: every mark measured on its target: a mark only where there is a choice, tight on its words, clear of the letters.

A mark is a box, outline or highlight laid over a page capture or a held picture (data-gate="mark", or a hollow outline: gate.mark_items).
This check reads the gate probe (gate.load_probe), finds each mark's picture (the page in its own card through the probe's parent chain,
else gate.mark_ground's picture under it; a held clip's frame is grabbed with ffmpeg at the source second its clip line gives), maps the
mark's box from film px into the picture's own pixels (the picture's drawn box and its file's size; a box of another shape than the file
is a tilt or a crop and is not judged, a clip pane is object-fit: cover), resamples the region to 1:1 film px and measures the ink there:
ink = pixels unlike the region's commonest colour, split into parts (8-connected). Each mark is judged once per stretch it shows, on the
middle frame of its full light. It does what a careful hand check of every mark does, in about a minute.

  MARK_OFF        a fault: an outline's border on letters, on the punctuation after its words or on a rule (its band 5 px in, 2 px out),
                  a wash's edge through letters (3 px or more of a glyph each side) or halving a big punctuation mark, the box half on one
                  line and half on the next, an outline sitting on or past its card's edge, nothing inside it, or 60 px or more of blank
                  beside its words (it frames more than them; a box on a panel of its own colour is exempt)
  MARK_REDUNDANT  a fault: the visible crop holds little ink besides what the mark covers, or the marked thing is the one big thing in it
                  (its glyphs 1.2x the other things' height): nothing to pick it out from
  MARK_LOOSE      info: on its words with blank round them (22 px a side, or 20 between opposite sides, by the line's own glyph band),
                  or touching the next line's glyph tips or a small full stop (left as they are: not worth a re-box)
  MARK_UNSAID     info, with --unsaid: OCR of the marked words (the editing venv's rapidocr) against the narration 1.5 s round the
                  light's arrival (first 4 letters, numbers as numbers)

  PIPE tools/pipeline/qa_marks.py <video> [--probe <probe.jsonl>] [--range a-b[,c-d]] [--out <dir>]
        [--loose-crops] [--unsaid [--words <words.json>]]
        writes <out>/marks.md, marks.json and crops/ (each flagged mark drawn on its capture as its component draws it, at 1:1 film
        px, 60 px round it; magenta = the words' ink it found); exit 1 on a MARK_OFF or MARK_REDUNDANT

PROOF (a long video's probe, 305 marks; about a minute with the probe's load, --unsaid ~10 min more): 131 OK, 103 LOOSE, 67 OFF,
8 REDUNDANT (75 fault flags on 74 marks), 4 not judged (a tilted page's 3 marks; a pop-up that is no page). Each fault crop and a sample
of LOOSE ones looked at; the thresholds above were tuned on them.
  Recall against a hand-fixed set: 19 of its 20 fixed ranges get a fault flag; by shot 21 of 24. Missed: a box loose round digits on
  nothing, and two washes flush with their glyphs, cutting none (the hand check called them "on the letters" from the data box).
  Precision: of 49 comparable flags, 27 are in the hand-fixed set (55%) and 47 are real (96%): the others are measured defects of the
  fixed classes the hand check called OK or loose (borders on the full stop or comma after the words, on or past their card's edge, on
  letters, a big number alone in its crop); 2 are false (a mural's drawn frame, a blurred 4x still).
  MARK_UNSAID flagged 101 of ~250 marks: paraphrases (an alert "Payment declined" marked on a line saying "didn't go through") and OCR misreads,
  so info only.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate  # noqa: E402
sys.path.append(str(HERE.parent / "common"))
from paths import FFMPEG, MOTION, PY_EDIT  # noqa: E402
sys.path.append(str(MOTION))
from brand import BRAND_RGB  # noqa: E402   the creator's accent (tools/motion/src/brand.ts)

# ------------------------------------------------------------------------------------------------------------------------------ thresholds
INK_DIFF = 48       # a pixel is ink when one colour channel differs this much from the page's own background colour (0-255)
PAGE_BG = 0.45      # the region round a mark is a page (text on a plain ground) when its background colour fills this share of it
MIN_PART = 6        # px: smaller specks of ink are noise
EDGE = 4            # px: a border's width (the brand outline); its band for "on the letters" is EDGE + 1 (a border touching a glyph)
EDGE_INK = 6        # ink px under one side of an outline's border (from parts with 3 px or more there) that put it on the letters
OUT_TOUCH = 2       # px outside an outline's edge that still count as under it (a glyph glued to the border, like a clock's "1")
CROSS = 3           # px of a glyph on each side of a wash's edge for the edge to cut it ...
PUNCT_H = 0.8       # a part under an edge shorter than this x the marked glyphs' median height and ...
PUNCT_A = 0.6       # ... smaller than this x their median area is punctuation (a full stop, a comma): named apart, still a fault
WASH_PUNCT = 250    # film px of a punctuation mark a wash's edge may halve before it shows (a bold 70-px headline's comma is ~346);
#                     an outline on any punctuation is a fault (its border covers it), a wash edge on a small full stop only a note
NEXT_LINE = 0.35    # a top or bottom edge on the next line's glyphs covering less of them than this is a touch (loose, info only)
CARD_GAP = 1.0      # px an outline must keep inside its card: closer, its border sits on the card's edge or is cut off
BLANK_OFF = 60      # px of blank between the box's inner edge and what it marks past which it frames the wrong thing (a box round a whole alert: ~100)
PANEL_DIFF = 8      # a colour channel step between just inside and just outside two of a box's edges: it frames a panel (a tile, a card)
LOOSE_PX = 22       # px of blank inside a box's edge on one side (the 8-px design pad + 14 of a hand check's tolerance) that make it loose: info only
LOOSE_SKEW = 20     # px between opposite sides' blank (12 of a hand check's tolerance + the 8 a content-box border adds right and under)
RED_RATIO = 0.35    # ink in the visible crop outside the mark / ink under it, under which there is nothing else to pick from
RED_BIG = 1.2       # what it marks this many times taller than the other things in the crop: it stands out on its own
SAY_WIN = 1.5       # s round the mark's arrival in which a marked word must be said (MARK_UNSAID)
REST_OP = 0.97      # a mark is at rest from this share of its highest opacity

FAULTS = ("MARK_OFF", "MARK_REDUNDANT")   # MARK_UNSAID is info (its OCR and paraphrases are noisy, see PROOF)
BRAND = BRAND_RGB


def _sig(s):
    """gate.tsx's colour hash (djb2), to tell a border mark from a wash by its colours"""
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return h - (1 << 32) if h >= 1 << 31 else h


# a brand outline: a translucent brand fill with a brand border (the accent, tools/motion/src/brand.ts); a wash: the solid brand fill
BORDER_SIGS = {_sig(f"rgba({BRAND[0]}, {BRAND[1]}, {BRAND[2]}, {a / 100:g})rgb({BRAND[0]}, {BRAND[1]}, {BRAND[2]})none") for a in range(0, 31)}


def mmss(f, fps=60):
    t = f / fps
    return f"{int(t // 60)}:{t % 60:05.2f}"


# ================================================================================================================ the marks and their grounds
def _chains(items):
    """each item's ancestors (its probe parents, nearest first)"""
    out = []
    for it in items:
        ch, q, seen = [], it.get("pa", -1), set()
        while q is not None and 0 <= q < len(items) and q not in seen:
            seen.add(q)
            ch.append(q)
            q = items[q].get("pa", -1)
        out.append(ch)
    return out


def _clip_area(it):
    x0, y0 = max(it["cx0"], it["x"]), max(it["cy0"], it["y"])
    x1, y1 = min(it["cx1"], it["x"] + it["w"]), min(it["cy1"], it["y"] + it["h"])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def ground_of(items, mi, W, H, chains=None):
    """the picture a mark points into: the page in the mark's own card (a picture sharing its nearest probe ancestor, under its centre;
    of a Receipt's copies of one page the biggest visible one), else gate.mark_ground's picture under it; None when there is none"""
    chains = chains or _chains(items)
    m = items[mi]
    cx, cy = m["x"] + m["w"] / 2, m["y"] + m["h"] / 2
    for a in chains[mi]:
        c = [j for j, it in enumerate(items) if j != mi and it["k"] in ("img", "clip") and it.get("g") != "credit" and a in chains[j]
             and it["x"] <= cx <= it["x"] + it["w"] and it["y"] <= cy <= it["y"] + it["h"] and it["op"] * it.get("br", 1) >= 0.5]
        if c:
            return max(c, key=lambda j: _clip_area(items[j]))
    g, _ = gate.mark_ground(items, mi, W, H)
    if g is None:
        return None
    return next(j for j, it in enumerate(items) if it is g)


def mark_stretches(layout, W, H):
    """each mark followed through the frames it shows (same picture, its box within 15 px of where it was on the frame before, by its
    top-left corner or its centre: marks pop in round their centre or wipe in from their left edge), with the frame it is judged on: the
    middle of the frames it shows at full light"""
    tracks, open_ = [], defaultdict(list)
    for f in sorted(layout):
        items = layout[f]
        # a spot-look mark (kit3 SpotGate, the probe's sp=1) draws no box: there is no border to sit on the ink (judged as a box, every
        # spot light would read as MARK_OFF about a border that isn't drawn)
        marks = [i for i in gate.mark_items(items, W, H) if items[i]["k"] == "box" and not items[i].get("sp")]
        if not marks:
            continue
        chains = _chains(items)
        used = set()
        for mi in marks:
            gi = ground_of(items, mi, W, H, chains)
            if gi is None:
                continue
            m, g = items[mi], items[gi]
            key = (g["k"], g["t"])
            pos = (m["x"], m["y"], m["x"] + m["w"] / 2, m["y"] + m["h"] / 2)
            best = None
            for tr in open_[key]:
                if id(tr) in used or f - tr["last"] > 2:
                    continue
                p = tr["pos"]
                dd = min(abs(pos[0] - p[0]) + abs(pos[1] - p[1]), abs(pos[2] - p[2]) + abs(pos[3] - p[3]))
                if dd <= 15 and (best is None or dd < best[0]):
                    best = (dd, tr)
            if best is None:
                tr = {"key": key, "rows": [], "last": f, "pos": pos}
                tracks.append(tr)
                open_[key].append(tr)
            else:
                tr = best[1]
            used.add(id(tr))
            tr["rows"].append((f, mi, gi, m["op"]))
            tr["last"], tr["pos"] = f, pos
    out = []
    for tr in tracks:
        rows = tr["rows"]
        top = max(r[3] for r in rows)
        rest = [r for r in rows if r[3] >= REST_OP * top]
        f, mi, gi, _ = rest[len(rest) // 2]
        out.append({"f0": rows[0][0], "f1": rows[-1][0], "rest": f, "arrive": rest[0][0], "mi": mi, "gi": gi, "key": tr["key"],
                    "n": len(rows)})
    return sorted(out, key=lambda s: (s["f0"], layout[s["rest"]][s["mi"]]["y"], layout[s["rest"]][s["mi"]]["x"]))


def is_outline(m):
    """a mark drawn as a border (an outline: the gate's hollow box, or the brand box round words on a dark page) rather than a wash"""
    if m.get("e") == 1 or m.get("c") in BORDER_SIGS:
        return True
    return False


# ================================================================================================================ the picture in film px
_PICS = {}


def _load_pic(pub, t, sec=None):
    """a ground's picture as RGB: an image file, or a clip's frame at the source second it shows (one light ffmpeg grab, cached)"""
    key = (t, None if sec is None else round(sec, 3))
    if key in _PICS:
        return _PICS[key]
    p = Path(pub) / t
    if sec is None:
        im = Image.open(p).convert("RGB") if p.exists() else None
    else:
        im = None
        if p.exists():
            r = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{sec:.3f}", "-i", str(p), "-frames:v", "1", "-f", "image2pipe", "-vcodec",
                                "png", "-"], capture_output=True)
            if r.returncode == 0 and r.stdout:
                im = Image.open(io.BytesIO(r.stdout)).convert("RGB")
    if len(_PICS) > 24:
        _PICS.pop(next(iter(_PICS)))
    _PICS[key] = im
    return im


def picture_map(g, nat, cover=None):
    """film px -> picture px for a ground drawn in the box g (x, y, w, h) from a picture of natural size nat: a picture stretched to its
    box (an <Img> at its own shape, a page scaled by its transform) maps straight; one whose box has another shape is drawn object-fit:
    cover, centred (lib.tsx's Clip and Still). Returns (scale film px per picture px, the picture's top-left in film px, how it fits)."""
    nw, nh = nat
    if cover is None:
        cover = abs((g["w"] / max(g["h"], 1e-6)) / (nw / nh) - 1) > 0.01
    if not cover:
        return g["w"] / nw, (g["x"], g["y"]), "fill"
    s = max(g["w"] / nw, g["h"] / nh)
    return s, (g["x"] + (g["w"] - nw * s) / 2, g["y"] + (g["h"] - nh * s) / 2), "cover"


def film_view(pic, s, org, roi):
    """the picture's region under the film-px rectangle roi (x0, y0, x1, y1), resampled to 1:1 film px: (an RGB uint8 array, a mask of
    the film px the picture covers)"""
    x0, y0, x1, y1 = roi
    w, h = int(round(x1 - x0)), int(round(y1 - y0))
    nw, nh = pic.size
    # the picture's own px for the roi, kept inside the picture (the rest is filled from the nearest edge and masked out)
    px0, py0 = (x0 - org[0]) / s, (y0 - org[1]) / s
    px1, py1 = (x1 - org[0]) / s, (y1 - org[1]) / s
    cx0, cy0, cx1, cy1 = max(px0, 0), max(py0, 0), min(px1, nw), min(py1, nh)
    arr = np.zeros((max(h, 1), max(w, 1), 3), np.uint8)
    valid = np.zeros((max(h, 1), max(w, 1)), bool)
    if cx1 <= cx0 or cy1 <= cy0 or w < 1 or h < 1:
        return arr, valid
    fx0, fy0 = int(round((cx0 - px0) * s)), int(round((cy0 - py0) * s))
    fx1, fy1 = int(round((cx1 - px0) * s)), int(round((cy1 - py0) * s))
    fx1, fy1 = min(fx1, w), min(fy1, h)
    if fx1 <= fx0 or fy1 <= fy0:
        return arr, valid
    part = pic.resize((fx1 - fx0, fy1 - fy0), Image.LANCZOS, box=(cx0, cy0, cx1, cy1))
    arr[fy0:fy1, fx0:fx1] = np.asarray(part)
    valid[fy0:fy1, fx0:fx1] = True
    return arr, valid


def ink_mask(arr, valid):
    """ink = pixels unlike the page's own background colour (its commonest colour in the region); returns (mask, background share)"""
    px = arr[valid]
    if len(px) < 50:
        return np.zeros(valid.shape, bool), 0.0
    q = (px >> 4).astype(np.int32)
    code = (q[:, 0] << 8) | (q[:, 1] << 4) | q[:, 2]
    mode = np.bincount(code).argmax()
    bg = px[code == mode].mean(0)
    d = np.abs(arr.astype(np.int16) - bg[None, None, :].astype(np.int16)).max(2)
    m = (d > INK_DIFF) & valid
    return m, float((d[valid] <= INK_DIFF).mean())


def components(mask):
    """8-connected parts of a bool mask, found by row runs (no scipy in the pipeline venv). Returns (label image, 1-based; an array of
    [x0, y0, x1, y1 (inclusive), area] per part, row k-1 for label k)"""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    pad = np.zeros((h, w + 2), np.int8)
    pad[:, 1:-1] = mask
    d = np.diff(pad, axis=1)
    st, en = np.argwhere(d == 1), np.argwhere(d == -1)
    n = len(st)
    if not n:
        return lab, np.zeros((0, 5), np.int64)
    rows, s, e = st[:, 0], st[:, 1], en[:, 1] - 1
    parent = list(range(n))

    def find(a):
        r = a
        while parent[r] != r:
            r = parent[r]
        while parent[a] != r:
            parent[a], a = r, parent[a]
        return r

    rs = np.searchsorted(rows, np.arange(h + 1)).tolist()
    sl, el = s.tolist(), e.tolist()
    for r in range(1, h):
        i, a1, j, b1 = rs[r - 1], rs[r], rs[r], rs[r + 1]
        while i < a1 and j < b1:
            if sl[j] <= el[i] + 1 and sl[i] <= el[j] + 1:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)
            if el[i] < el[j]:
                i += 1
            else:
                j += 1
    roots = np.array([find(i) for i in range(n)])
    _, lid = np.unique(roots, return_inverse=True)
    k = int(lid.max()) + 1
    x0, y0 = np.full(k, 1 << 30), np.full(k, 1 << 30)
    x1, y1, ar = np.full(k, -1), np.full(k, -1), np.zeros(k, np.int64)
    np.minimum.at(x0, lid, s)
    np.maximum.at(x1, lid, e)
    np.minimum.at(y0, lid, rows)
    np.maximum.at(y1, lid, rows)
    np.add.at(ar, lid, e - s + 1)
    for q, (r, a, b) in enumerate(zip(rows.tolist(), sl, el)):
        lab[r, a:b + 1] = lid[q] + 1
    return lab, np.stack([x0, y0, x1, y1, ar], 1)


def _count(lab, n, box):
    """pixels of each part (index = label) inside box (x0, y0, x1, y1), clipped to the image"""
    h, w = lab.shape
    a, b, c, d = max(box[0], 0), max(box[1], 0), min(box[2], w), min(box[3], h)
    if c <= a or d <= b:
        return np.zeros(n + 1, np.int64)
    return np.bincount(lab[b:d, a:c].ravel(), minlength=n + 1)


def _wmedian(vals, weights):
    """the median of vals weighted by weights"""
    o = np.argsort(vals)
    v, w = np.asarray(vals, float)[o], np.asarray(weights, float)[o]
    c = np.cumsum(w)
    return float(v[np.searchsorted(c, c[-1] / 2)])


def _wquant(vals, weights, q):
    """the q-quantile of vals weighted by weights"""
    o = np.argsort(vals)
    v, w = np.asarray(vals, float)[o], np.asarray(weights, float)[o]
    c = np.cumsum(w)
    return float(v[min(len(v) - 1, np.searchsorted(c, q * c[-1]))])


def _thin(c):
    """a rule (a line across the page) or an outline (a frame, a panel's edge): long and thin, or sparse in its own box"""
    w, h, area = c[2] - c[0] + 1, c[3] - c[1] + 1, c[4]
    return (h <= 12 and w >= 8 * h and w >= 30) or (w <= 12 and h >= 8 * w and h >= 30) or (max(w, h) > 60 and area < 0.12 * w * h)


# ================================================================================================================ one mark measured
def measure_mark(m, g, pic, W, H, outline=None, fit=None):
    """measure one mark (probe item m) on its ground g (probe item) whose picture is `pic`. Returns a dict: verdict ('OFF', 'LOOSE', 'OK',
    'UNJUDGED'), the reasons, the blank px per side round the words, what lies under its edges, the redundancy numbers (film px)."""
    outline = is_outline(m) if outline is None else outline
    s, org, how = picture_map(g, pic.size, fit)
    rx0, ry0, rx1, ry1 = m["x"], m["y"], m["x"] + m["w"], m["y"] + m["h"]
    res = {"rect": [round(rx0, 1), round(ry0, 1), round(m["w"], 1), round(m["h"], 1)], "outline": outline, "fit": how,
           "scale": round(s, 3), "reasons": [], "verdict": "OK"}
    if how == "cover" and fit is None:
        # an <Img> drawn at another shape than its file: a tilted page (PageStage) or a fill we can't place; not measured
        res["verdict"] = "UNJUDGED"
        res["reasons"] = [f"its picture is drawn {g['w']:.0f}x{g['h']:.0f} from a {pic.size[0]}x{pic.size[1]} file (a tilt or a crop): not mapped"]
        return res
    # what the viewer sees of the picture: its drawn box inside its card's clip and the frame
    vx0, vy0 = max(g["x"], g["cx0"], 0, org[0]), max(g["y"], g["cy0"], 0, org[1])
    vx1 = min(g["x"] + g["w"], g["cx1"], W, org[0] + pic.size[0] * s)
    vy1 = min(g["y"] + g["h"], g["cy1"], H, org[1] + pic.size[1] * s)
    reasons = []
    # an outline's border against its own card (its clip box): touching or past the card's edge, the border is cut or merges with it
    gap = {"left": rx0 - m["cx0"], "top": ry0 - m["cy0"], "right": m["cx1"] - rx1, "bottom": m["cy1"] - ry1}
    res["card_gap"] = {k: round(v, 1) for k, v in gap.items() if v < 20}
    if outline:
        cut = [k for k, v in gap.items() if v < CARD_GAP]
        if cut:
            reasons.append(f"its border {'runs off' if min(gap[k] for k in cut) < -1 else 'sits on'} its card's edge on the "
                           f"{' and '.join(cut)} ({', '.join(f'{gap[k]:.1f}' for k in cut)} px inside)")
    mx = max(40.0, 0.8 * m["h"])
    roi = (int(np.floor(max(rx0 - mx, vx0))), int(np.floor(max(ry0 - mx, vy0))), int(np.ceil(min(rx1 + mx, vx1))), int(np.ceil(min(ry1 + mx, vy1))))
    res["roi"] = roi
    if roi[2] - roi[0] < 8 or roi[3] - roi[1] < 8:
        res["verdict"] = "OFF" if reasons else "UNJUDGED"
        res["reasons"] = reasons or ["the mark is outside its picture"]
        return res
    arr, valid = film_view(pic, s, org, roi)
    ink, bgshare = ink_mask(arr, valid)
    res["bg_share"] = round(bgshare, 2)
    page = bgshare >= PAGE_BG
    res["page"] = page
    lab, cc = components(ink)
    n = len(cc)
    X0, Y0 = int(round(rx0 - roi[0])), int(round(ry0 - roi[1]))
    X1, Y1 = int(round(rx1 - roi[0])), int(round(ry1 - roi[1]))
    E = EDGE
    inside = _count(lab, n, (X0, Y0, X1, Y1))
    big = cc[:, 4] >= MIN_PART if n else np.zeros(0, bool)
    thin = np.array([_thin(c) for c in cc], bool) if n else np.zeros(0, bool)
    # the marked words: parts mostly inside the box (not rules or frames)
    words = [i for i in range(n) if big[i] and not thin[i] and inside[i + 1] >= 0.5 * cc[i, 4]]
    res["parts_in"] = len(words)
    ref = words or [i for i in range(n) if big[i] and not thin[i]]
    # the glyphs' height: the median by ink (a clock's colon dots and a decimal point don't outvote its digits); their area: the median
    # of the parts at least half that tall (letters, not dots)
    xh = _wmedian([cc[i, 3] - cc[i, 1] + 1 for i in ref], [cc[i, 4] for i in ref]) if ref else 0.0
    let = [cc[i, 4] for i in ref if cc[i, 3] - cc[i, 1] + 1 >= 0.5 * xh]
    xa = float(np.median(let)) if let else 0.0
    res["glyph_h"] = round(xh, 1)

    # text: three or more glyphs of a like height (a line of words); a drawn thing (a painted frame, a stat tile, a card) is judged on
    # its card and its blank only: a non-text mark's own edges are a call for the eye
    hs = np.array([cc[i, 3] - cc[i, 1] + 1 for i in words], float)
    feet = np.array([cc[i, 3] for i in words], float)
    wa = np.array([cc[i, 4] for i in words], float)
    text = False
    if len(words) >= 3 and xh >= 6:
        like = ((hs >= 0.5 * xh) & (hs <= 2.2 * xh)) * wa
        foot = _wmedian(list(feet), list(wa))
        stand = (np.abs(feet - foot) <= max(3.0, 0.2 * xh)) * wa       # glyphs standing on one line
        text = bool(like.sum() >= 0.6 * wa.sum() and stand.sum() >= 0.6 * wa.sum())
    res["text"] = text

    def kind(i, side):
        """what a part under an edge is: a rule, punctuation (short and small: a full stop, a comma, a colon's dot), the tip of the next
        line's glyphs (a top or bottom edge covering under NEXT_LINE of a glyph that lies mostly outside), or letters"""
        if thin[i]:
            return "rule"
        h_ = cc[i, 3] - cc[i, 1] + 1
        if side in ("top", "bottom") and inside[i + 1] < 0.5 * cc[i, 4]:
            cov = (min(cc[i, 3], Y1 - 1) - max(cc[i, 1], Y0) + 1) / h_
            if cov < NEXT_LINE:
                return "the next line's tips"
        if h_ < PUNCT_H * xh and cc[i, 4] < PUNCT_A * xa:
            return "punctuation"
        return "letters"

    if page and text:
        # ---- the edges: which parts each side runs through
        hits = defaultdict(list)    # side -> [(part, px)]
        if outline:
            # the border's band (its width + 1 px inside, OUT_TOUCH px outside: a border touching a glyph reads as on it), each side over
            # the box's span
            B, O = E + 1, OUT_TOUCH
            # (the corners belong to the top and bottom: a glyph of the line over or under at a corner is that line's tip)
            strips = {"top": (X0 - O, Y0 - O, X1 + O, Y0 + B), "bottom": (X0 - O, Y1 - B, X1 + O, Y1 + O),
                      "left": (X0 - O, Y0 + B, X0 + B, Y1 - B), "right": (X1 - B, Y0 + B, X1 + O, Y1 - B)}
            for side, box in strips.items():
                cnt = _count(lab, n, box)
                parts = [(i, int(cnt[i + 1])) for i in range(n) if big[i] and cnt[i + 1] >= 3]
                if sum(px for _, px in parts) >= EDGE_INK:
                    hits[side] = parts
        else:
            # a wash's edge through a glyph: CROSS px or more of it on each side of the edge, the glyph on the box's rows (or columns)
            for i in range(n):
                if not big[i]:
                    continue
                cx0, cy0, cx1, cy1 = cc[i, :4]
                w_, h_ = cx1 - cx0 + 1, cy1 - cy0 + 1
                vy = min(cy1, Y1 - 1) - max(cy0, Y0) + 1     # rows it shares with the box
                vx = min(cx1, X1 - 1) - max(cx0, X0) + 1
                for side, out_, in_, share in (("left", X0 - cx0, cx1 - X0 + 1, vy / h_), ("right", cx1 - X1 + 1, X1 - cx0, vy / h_),
                                               ("top", Y0 - cy0, cy1 - Y0 + 1, vx / w_), ("bottom", cy1 - Y1 + 1, Y1 - cy0, vx / w_)):
                    if out_ >= CROSS and in_ >= CROSS and share >= 0.5:
                        hits[side].append((i, int(cc[i, 4])))
        on, touch = {}, {}
        for side, parts in hits.items():
            kinds = {kind(i, side) for i, _ in parts}
            px = sum(q for _, q in parts)
            big_p = outline or any(kind(i, side) == "punctuation" and cc[i, 4] >= WASH_PUNCT for i, _ in parts)
            if "letters" in kinds:
                on[side] = (px, "the letters")
            elif "punctuation" in kinds and big_p:
                on[side] = (px, "the punctuation")   # a wash halving a bold comma, a border on a full stop or a comma
            elif "rule" in kinds:
                on[side] = (px, "a rule")
            else:
                touch[side] = " and ".join(sorted(kinds))
        res["edge"] = {k: v[0] for k, v in on.items()}
        res["edge_touch"] = touch
        if on:
            reasons.append(f"its {'border' if outline else 'edge'} runs through " + "; ".join(
                f"{what} on the {side}" for side, (px, what) in on.items()) + f" ({', '.join(str(v[0]) for v in on.values())} px of them)")
    if page:
        # ---- the words (or the thing) against the box's inner edges
        inn = E if outline else 0
        if words:
            wx0, wy0 = min(cc[i, 0] for i in words), min(cc[i, 1] for i in words)
            wx1, wy1 = max(cc[i, 2] for i in words), max(cc[i, 3] for i in words)
            if text:
                # up and down, the line's own glyph band: caps to descenders of every glyph on that line, in the box or beside it
                # (marked words without a descender don't make the box loose underneath)
                same = [i for i in range(n) if big[i] and not thin[i]
                        and min(cc[i, 3], wy1) - max(cc[i, 1], wy0) + 1 >= 0.5 * (cc[i, 3] - cc[i, 1] + 1)]
                wy0, wy1 = min([wy0] + [cc[i, 1] for i in same]), max([wy1] + [cc[i, 3] for i in same])
            blank = {"top": int(wy0 - (Y0 + inn)), "bottom": int((Y1 - 1 - inn) - wy1), "left": int(wx0 - (X0 + inn)),
                     "right": int((X1 - 1 - inn) - wx1)}
            blank = {k: max(0, v) for k, v in blank.items()}
            res["blank"] = blank
            res["words_box"] = [int(wx0 + roi[0]), int(wy0 + roi[1]), int(wx1 - wx0 + 1), int(wy1 - wy0 + 1)]
            res["panel"] = panel = _frames_panel(arr, ink, valid, X0, Y0, X1, Y1, E)
            wide = [k for k, v in blank.items() if v > BLANK_OFF]
            if wide and not panel:
                reasons.append(f"{' and '.join(f'{blank[k]} px' for k in wide)} blank {'/'.join(wide)} of what it marks: it frames more "
                               f"than its words")
        else:
            res["blank"] = None
            reasons.append("nothing inside it: it marks blank page")
    res["reasons"] = reasons
    if reasons:
        res["verdict"] = "OFF"
    elif not page:
        res["verdict"] = "UNJUDGED"
        res["reasons"] = [f"not a page round it (its commonest colour fills {bgshare:.0%}): judged only against its card"]
    else:
        bl, notes = res["blank"], []
        if max(bl.values()) >= LOOSE_PX or abs(bl["top"] - bl["bottom"]) >= LOOSE_SKEW or abs(bl["left"] - bl["right"]) >= LOOSE_SKEW:
            notes.append(f"on its words with blank round them (top {bl['top']}, bottom {bl['bottom']}, left {bl['left']}, right "
                         f"{bl['right']} px)")
        for side, what in (res.get("edge_touch") or {}).items():
            notes.append(f"its {'border' if outline else 'edge'} touches {what} on the {side}")
        if notes:
            res["verdict"] = "LOOSE"
            res["reasons"] = notes
    res.update(redundancy(m, pic, s, org, (vx0, vy0, vx1, vy1), W, H))
    return res


def _frames_panel(arr, ink, valid, X0, Y0, X1, Y1, E):
    """the box frames a panel (a stat tile, a card) when the page just inside its edges is another colour than just outside them,
    on two sides or more (a box on words has the same page colour on both sides of its edges)"""
    h, w = ink.shape
    differs = 0
    for a_in, a_out in (((X0 + E + 2, Y0 + E + 2, X1 - E - 2, Y0 + E + 8), (X0, Y0 - 8, X1, Y0 - 2)),
                        ((X0 + E + 2, Y1 - E - 8, X1 - E - 2, Y1 - E - 2), (X0, Y1 + 2, X1, Y1 + 8)),
                        ((X0 + E + 2, Y0 + E + 2, X0 + E + 8, Y1 - E - 2), (X0 - 8, Y0, X0 - 2, Y1)),
                        ((X1 - E - 8, Y0 + E + 2, X1 - E - 2, Y1 - E - 2), (X1 + 2, Y0, X1 + 8, Y1))):
        cols = []
        for x0, y0, x1, y1 in (a_in, a_out):
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
            if x1 <= x0 or y1 <= y0:
                break
            sel = valid[y0:y1, x0:x1] & ~ink[y0:y1, x0:x1]
            if sel.sum() < 10:
                break
            cols.append(np.median(arr[y0:y1, x0:x1][sel], 0))
        if len(cols) == 2 and np.abs(cols[0] - cols[1]).max() > PANEL_DIFF:
            differs += 1
    return differs >= 2


def redundancy(m, pic, s, org, vis, W, H):
    """MARK_REDUNDANT: the things in the visible crop (half film resolution) besides what the mark covers. Redundant when the rest holds
    little ink (RED_RATIO of the marked ink) or the marked thing is the one big thing in it (its glyphs RED_BIG x the other things,
    each measured by ink: the marked parts' median height, the others' 90th percentile)."""
    vx0, vy0, vx1, vy1 = vis
    cx0, cy0, cx1, cy1 = int(np.floor(vx0)), int(np.floor(vy0)), int(np.ceil(vx1)), int(np.ceil(vy1))
    if cx1 - cx0 < 16 or cy1 - cy0 < 16 or ((cx1 - cx0) >= 0.97 * W and (cy1 - cy0) >= 0.97 * H):
        return {}   # a full-frame picture: the whole scene to pick from
    carr, cval = film_view(pic, s, org, (cx0, cy0, cx1, cy1))
    h2, w2 = carr.shape[0] // 2 * 2, carr.shape[1] // 2 * 2
    small = carr[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2, 3).mean((1, 3)).astype(np.uint8)
    sval = cval[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2).all((1, 3))
    ink, _ = ink_mask(small, sval)
    lab, cc = components(ink)
    n = len(cc)
    if not n:
        return {}
    a, b = int(round((m["x"] - cx0) / 2)), int(round((m["y"] - cy0) / 2))
    c, d = int(round((m["x"] + m["w"] - cx0) / 2)), int(round((m["y"] + m["h"] - cy0) / 2))
    inside = _count(lab, n, (a, b, c, d))
    hh, ww = ink.shape
    keep = [i for i in range(n) if cc[i, 4] >= 4 and not _thin(cc[i])
            and not (cc[i, 0] == 0 and cc[i, 2] == ww - 1) and not (cc[i, 1] == 0 and cc[i, 3] == hh - 1)]
    mk = [i for i in keep if inside[i + 1] >= 0.5 * cc[i, 4]]
    ot = [i for i in keep if i not in set(mk)]
    under = int(sum(cc[i, 4] for i in mk)) * 4
    other = int(sum(cc[i, 4] for i in ot)) * 4
    # sizes by ink: the marked glyphs' median height against the other things' 90th percentile (one tall "$" or bracket in a line of
    # the same type is no "big thing": a "$5.99 a Month" or "$150,000" headline)
    mh = int(round(_wmedian([cc[i, 3] - cc[i, 1] + 1 for i in mk], [cc[i, 4] for i in mk]) * 2)) if mk else 0
    oh = int(round(_wquant([cc[i, 3] - cc[i, 1] + 1 for i in ot], [cc[i, 4] for i in ot], 0.9) * 2)) if ot else 0
    out = {"red": {"under": under, "other": other, "ratio": round(other / max(under, 1), 3), "marked_h": mh, "other_h": oh,
                   "crop": [cx0, cy0, cx1 - cx0, cy1 - cy0]}}
    if under > 0 and other < RED_RATIO * under:
        out["redundant"] = (f"the visible crop ({cx1 - cx0}x{cy1 - cy0}) holds {other} ink px besides the {under} under the mark "
                            f"({other / under:.0%}): nothing else to pick it out from")
    elif under > 0 and oh and mh >= RED_BIG * oh:
        out["redundant"] = (f"what it marks is the one big thing in the visible crop ({cx1 - cx0}x{cy1 - cy0}): its glyphs {mh} px "
                            f"tall, the other things {oh} px: it stands out without a mark")
    return out


# ================================================================================================================ the crop PNG
def draw_crop(pic, g, m, res, path, label, fit=None, margin=60):
    """the mark drawn on its capture as its component draws it (a 4-px brand border, or a brand wash multiplied in), at 1:1 film px with
    `margin` px round it; a thin magenta line where the measure found the words' ink; the verdict written under it"""
    s, org, _ = picture_map(g, pic.size, fit)
    W, H = gate.FRAME
    x0, y0 = m["x"] - margin, m["y"] - margin
    x1, y1 = m["x"] + m["w"] + margin, m["y"] + m["h"] + margin
    roi = (int(np.floor(x0)), int(np.floor(y0)), int(np.ceil(x1)), int(np.ceil(y1)))
    arr, valid = film_view(pic, s, org, roi)
    arr = arr.copy()
    arr[~valid] = (40, 40, 40)
    # the card's edge: outside its clip box the viewer sees the stage, shown grey
    gx0, gy0, gx1, gy1 = m["cx0"] - roi[0], m["cy0"] - roi[1], m["cx1"] - roi[0], m["cy1"] - roi[1]
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    outside = (xx < gx0) | (xx >= gx1) | (yy < gy0) | (yy >= gy1)
    arr[outside] = (arr[outside] * 0.35 + 60).astype(np.uint8)
    X0, Y0 = m["x"] - roi[0], m["y"] - roi[1]
    X1, Y1 = X0 + m["w"], Y0 + m["h"]
    a, b, c, d = int(round(X0)), int(round(Y0)), int(round(X1)), int(round(Y1))
    if not res.get("outline"):
        sl = (slice(max(b, 0), max(d, 0)), slice(max(a, 0), max(c, 0)))
        part = arr[sl].astype(np.float32)
        mult = part * (np.array(BRAND, np.float32) / 255.0)
        arr[sl] = (part * 0.15 + mult * 0.85).astype(np.uint8)
    im = Image.fromarray(arr)
    dr = ImageDraw.Draw(im)
    if res.get("outline"):
        for i in range(EDGE):
            dr.rectangle([a + i, b + i, c - 1 - i, d - 1 - i], outline=BRAND)
    # the words' ink found inside it
    wb = res.get("words_box")
    if wb:
        dr.rectangle([wb[0] - roi[0], wb[1] - roi[1], wb[0] + wb[2] - 1 - roi[0], wb[1] + wb[3] - 1 - roi[1]], outline=(255, 0, 255))
    pad = 34
    out = Image.new("RGB", (im.width, im.height + pad), (20, 20, 20))
    out.paste(im, (0, 0))
    ImageDraw.Draw(out).text((6, im.height + 8), label[:180], fill=(255, 255, 255), font=_font())
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)


_FONT = []


def _font():
    if not _FONT:
        for name in ("arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"):   # Windows, macOS, Linux
            try:
                _FONT.append(ImageFont.truetype(name, 15))
                break
            except OSError:
                continue
        if not _FONT:
            _FONT.append(ImageFont.load_default())
    return _FONT[0]


# ================================================================================================================ MARK_UNSAID (OCR)
OCR_CODE = r"""
import json, sys
from rapidocr_onnxruntime import RapidOCR
eng = RapidOCR()
out = {}
for p in json.load(open(sys.argv[1], encoding='utf-8')):
    r, _ = eng(p)
    out[p] = ' '.join(x[1] for x in (r or []))
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'))
"""


def ocr_texts(paths, work):
    """the words in each image, read by rapidocr in the editing venv (one subprocess for all); {} when that venv isn't there"""
    if not paths or not PY_EDIT.exists():
        return {}
    work.mkdir(parents=True, exist_ok=True)
    src, lst, res = work / "ocr_run.py", work / "ocr_in.json", work / "ocr_out.json"
    src.write_text(OCR_CODE, encoding="utf-8")
    lst.write_text(json.dumps([str(p) for p in paths]), encoding="utf-8")
    # two threads: the computer is shared with renders and other jobs; ~2 s a crop
    env = {**os.environ, "OMP_NUM_THREADS": "2", "ORT_NUM_THREADS": "2"}
    r = subprocess.run([str(PY_EDIT), str(src), str(lst), str(res)], capture_output=True, text=True, env=env)
    if r.returncode != 0 or not res.exists():
        return {}
    return json.loads(res.read_text(encoding="utf-8"))


NUMW = set(gate.NUM) | set(gate.SCALE)


def _stems(text):
    """content words, first 4 letters; digits read as themselves"""
    out = set()
    for t in re.findall(r"[A-Za-z0-9]+", text.lower().replace("'", "")):
        if t in gate.STOP or len(t) < 3 and not t.isdigit():
            continue
        out.add(t[:4])
    return out


def _spoken(words, t0, t1):
    toks = set()
    for w in words:
        if w["end"] >= t0 and w["start"] <= t1:
            toks |= _stems(w["w"])
            if w["w"].lower().strip(".,!?;:'\"") in NUMW:
                toks.add("#num")
    return toks


# ================================================================================================================ the check
def check_marks_target(pub_dir, layout, clips=None, words=None, fps=60, out=None, report=None, loose_crops=False):
    """MARK_OFF and MARK_REDUNDANT (and the info MARK_UNSAID with `words` + `out`: OCR in the editing venv) over a probe's layout
    ({frame: [items]}) and clip lines ({frame: [clip lines]}) as gate.load_probe returns them; pub_dir holds the pictures the probe names.
    Returns flags in the gate's format ({check, key, at, to, what}, plus the crop's path); with `out` a crop PNG per flag (and per loose
    mark with loose_crops) goes to <out>/crops. `report`, when a list, receives one row per judged mark (every verdict, its numbers)."""
    W, H = gate.FRAME
    clips = clips or {}
    flags, rows, unsaid_jobs = [], [], []
    for st in mark_stretches(layout, W, H):
        f = st["rest"]
        items = layout[f]
        m, g = items[st["mi"]], items[st["gi"]]
        sec = None
        if g["k"] == "clip":
            cs = [c for c in clips.get(f, []) if c["src"] == g["t"]]
            if not cs:
                continue
            sec = cs[0]["s"]
        pic = _load_pic(pub_dir, g["t"], sec)
        name = Path(str(g["t"])).name
        row = {"f0": st["f0"], "f1": st["f1"], "rest": f, "arrive": st["arrive"], "ground": str(g["t"]), "n": st["n"]}
        if pic is None:
            row.update(verdict="UNJUDGED", reasons=[f"{g['t']} not found in {pub_dir}"])
            rows.append(row)
            continue
        res = measure_mark(m, g, pic, W, H, fit=True if g["k"] == "clip" else None)
        row.update(res)
        rows.append(row)
        where = f"a mark at {m['x']:.0f},{m['y']:.0f} ({m['w']:.0f}x{m['h']:.0f}) on {name} from {mmss(st['f0'], fps)} to {mmss(st['f1'], fps)}"
        key = f"{name}@{int(round(m['x']))},{int(round(m['y']))}"
        crop = None
        if out is not None and (res["verdict"] == "OFF" or res.get("redundant") or (loose_crops and res["verdict"] == "LOOSE")):
            tag = "OFF" if res["verdict"] == "OFF" else ("RED" if res.get("redundant") else "LOOSE")
            crop = Path(out) / "crops" / f"{tag}_{st['f0']:06d}_{Path(name).stem[:40]}_{int(m['x'])}_{int(m['y'])}.png"
            draw_crop(pic, g, m, res, crop, f"{tag} {mmss(st['f0'], fps)} f{f}: " + "; ".join(res["reasons"] + ([res["redundant"]] if res.get("redundant") else [])),
                      fit=True if g["k"] == "clip" else None)
            row["crop"] = str(crop)
        if res["verdict"] == "OFF":
            flags.append({"check": "MARK_OFF", "key": key, "at": st["f0"], "to": st["f1"],
                          "what": f"{where}: " + "; ".join(res["reasons"]) + " (a mark sits tight on its words' own ink, its edge clear of letters)",
                          **({"crop": str(crop)} if crop else {})})
        if res.get("redundant"):
            flags.append({"check": "MARK_REDUNDANT", "key": key, "at": st["f0"], "to": st["f1"],
                          "what": f"{where}: {res['redundant']} (a mark only where there is a choice: drop it)",
                          **({"crop": str(crop)} if crop else {})})
        if words is not None and res.get("page") and res["verdict"] != "UNJUDGED" and out is not None:
            unsaid_jobs.append((st, m, g, pic, row, where, key))
    # MARK_UNSAID: the marked words read off the capture against the narration round the mark's arrival
    if unsaid_jobs:
        work = Path(out) / "ocr"
        paths = []
        for st, m, g, pic, row, where, key in unsaid_jobs:
            s, org, _ = picture_map(g, pic.size, True if g["k"] == "clip" else None)
            arr, valid = film_view(pic, s, org, (int(m["x"]), int(m["y"]), int(m["x"] + m["w"]), int(m["y"] + m["h"])))
            # a plain margin round the marked words: the OCR's detector misses text cut flush at the image's edge
            q = (np.median(arr[valid], 0) if valid.any() else np.array([255, 255, 255])).astype(np.uint8)
            arr = np.pad(arr, ((24, 24), (24, 24), (0, 0)))
            arr[:24], arr[-24:], arr[:, :24], arr[:, -24:] = q, q, q, q
            p = work / f"m_{st['f0']:06d}_{int(m['x'])}_{int(m['y'])}.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(arr).save(p)
            paths.append(p)
        texts = ocr_texts(paths, work)
        for (st, m, g, pic, row, where, key), p in zip(unsaid_jobs, paths):
            text = texts.get(str(p))
            if text is None:
                continue
            row["ocr"] = text
            marked = _stems(text)
            nums = bool(re.search(r"\d", text))
            if not marked and not nums:
                continue
            t = st["arrive"] / fps
            said = _spoken(words, t - SAY_WIN, t + SAY_WIN)
            hit = marked & said or (nums and "#num" in said) or (nums and any(x.isdigit() for x in said))
            row["said"] = bool(hit)
            if not hit:
                flags.append({"check": "MARK_UNSAID", "key": key, "at": st["f0"], "to": st["f1"],
                              "what": f"{where}: it marks \"{text[:60]}\" and none of it is said within {SAY_WIN} s of its arrival at "
                                      f"{mmss(st['arrive'], fps)} (the voice and the light point at different things)"})
    if report is not None:
        report.extend(rows)
    return flags


# ================================================================================================================ the CLI
def _in_ranges(f, spans):
    return any(a <= f <= b for a, b in spans)


def write_reports(out, flags, rows, head, fps=60):
    out.mkdir(parents=True, exist_ok=True)
    (out / "marks.json").write_text(json.dumps({"flags": flags, "marks": rows}, indent=1, default=str), encoding="utf-8")
    cnt = defaultdict(int)
    for r in rows:
        cnt[r.get("verdict", "?")] += 1
    red = sum(1 for r in rows if r.get("redundant"))
    lines = [f"# Marks on their targets (qa_marks.py)", "", head, "",
             f"{len(rows)} marks judged: {cnt['OK']} OK, {cnt['LOOSE']} LOOSE (info), {cnt['OFF']} OFF, {red} REDUNDANT, "
             f"{cnt['UNJUDGED']} not judged.", "",
             f"**Faults: {sum(1 for x in flags if x['check'] in FAULTS)}** (each fixed before the render: the box re-measured on its "
             f"words' own ink, its border clear of letters, punctuation, rules and its card's edge; a mark with nothing to stand out from "
             f"dropped)", ""]
    for x in sorted(flags, key=lambda x: x["at"]):
        if x["check"] in FAULTS:
            lines.append(f"- {x['check']} {mmss(x['at'], fps)}-{mmss(x['to'], fps)} (frames {x['at']}-{x['to']}): {x['what']}"
                         + (f"  \n  crop: `{x['crop']}`" if x.get("crop") else ""))
    info = [x for x in flags if x["check"] not in FAULTS]
    if info:
        lines += ["", "## Info: marked words not said round the light (MARK_UNSAID: OCR, so misreads and paraphrases come up too)", ""]
        lines += [f"- {mmss(x['at'], fps)}: {x['what']}" for x in sorted(info, key=lambda x: x["at"])]
    lines += ["", "## Loose (info only: on their words with blank round them, or touching the next line's glyphs or a small full stop; "
                  "left as they are)", ""]
    for r in rows:
        if r.get("verdict") == "LOOSE":
            lines.append(f"- {mmss(r['f0'], fps)} {Path(r['ground']).name} at {r['rect']}: {'; '.join(r['reasons'])}")
    unj = [r for r in rows if r.get("verdict") == "UNJUDGED"]
    if unj:
        lines += ["", "## Not judged", ""] + [f"- {mmss(r['f0'], fps)} {Path(r['ground']).name}: {'; '.join(r['reasons'])}" for r in unj]
    (out / "marks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    from common import Video, find_video
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--probe", help="the gate probe (default: <dj>/pipeline/gate/probe.jsonl)")
    ap.add_argument("--range", help="frames a-b[,c-d]: judge only marks showing there")
    ap.add_argument("--out", help="the report folder (default: <dj>/pipeline/marks)")
    ap.add_argument("--unsaid", action="store_true", help="also MARK_UNSAID: OCR every judged mark (the editing venv; minutes)")
    ap.add_argument("--loose-crops", action="store_true", help="a crop PNG for every loose mark too")
    ap.add_argument("--words", help="film-time words json for --unsaid (default: <dj>/build/insert/words_ins.json, else build/captions/words.json)")
    a = ap.parse_args(argv)
    v = Video(find_video(a.video))
    probe = Path(a.probe) if a.probe else v.pipe_dir / "gate" / "probe.jsonl"
    out = Path(a.out) if a.out else v.pipe_dir / "marks"
    t0 = time.time()
    clips, layout = gate.load_probe(probe)
    if a.range:
        spans = [tuple(int(x) for x in s.split("-")) for s in a.range.split(",")]
        layout = {f: it for f, it in layout.items() if _in_ranges(f, spans)}
    words = None
    if a.unsaid:
        cands = [Path(a.words)] if a.words else [v.dj / "build" / "insert" / "words_ins.json", v.dj / "build" / "captions" / "words.json"]
        wp = next((c for c in cands if c.exists()), None)
        if wp is None:
            raise SystemExit(f"qa_marks --unsaid: no film-time words ({', '.join(map(str, cands))})")
        words = json.loads(wp.read_text(encoding="utf-8"))
    rows = []
    fps = int(v.cfg.get("video", {}).get("fps", 60))
    flags = check_marks_target(v.pub, layout, clips, words, fps=fps, out=out, report=rows, loose_crops=a.loose_crops)
    head = (f"{v.slug}, probe {probe} ({time.strftime('%Y-%m-%d %H:%M', time.localtime(probe.stat().st_mtime))})"
            + (f", frames {a.range}" if a.range else "") + f"; run {time.time() - t0:.0f} s")
    write_reports(out, flags, rows, head, fps)
    faults = [x for x in flags if x["check"] in FAULTS]
    print(f"qa_marks: {len(rows)} marks, {len(faults)} fault(s) -> {out / 'marks.md'}")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
