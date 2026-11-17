"""automark.py: the box of a named thing in a picture, measured by a machine, never by hand.

Why: hand-measured mark boxes drift (a wing tip outside the box, a box past an image's edge). A mark points at a thing, so its box is
measured from the thing's own pixels.

  EDIT tools/motion/automark.py <image> "<what>" [--count N] [--region x,y,w,h] [--pad 8] [--proof out.jpg] [--json] [--threads 2] [--fresh]
      "four gulls" is "gull" --count 4 (a number word in front sets the count; --count wins)

1. DETECT: an open-vocabulary detector (OWLv2 base ensemble, google/owlv2-base-patch16-ensemble) on the CPU, over a pyramid of square
   tiles: the whole region (big things), squares the size of its short side, and tiles at 100% (2x zoom on small pictures) with 25%
   overlap, so a 20-px bird in a 3840x2160 painting is seen at full size. A box cut by a tile's inner edge is dropped (the overlap
   shows the thing whole in a neighbour), duplicates across tiles and levels are merged, and a box holding two or more finds that score
   about as high is their group (the flock round four gulls), not one of them. The model's load and run hold the PC's turn-taking
   ticket (tools/pipeline/heavy.py, kind score: it may wait an hour behind a render); the raw finds are cached in TMP/automark/, so a
   re-run (another --count, --pad, proof) needs no model and no ticket; a --region search uses the whole picture's cached finds inside
   it when there are some. --fresh detects again (on the region's own, finer tiles).
2. REFINE: inside each find's box + half its size, the thing is separated from its local background: a median background finds the
   rough parts, then a narrow blur that skips them (normalized convolution, two passes) follows the clouds and brush strokes round the
   thing; the thing is every pixel that differs from it (brightness first: a JPEG smears colour) by a hysteresis threshold seeded at
   ~half the thing's own contrast, grown down to a fifth of it, never into the background's noise. The connected part with the most
   pixels in the find is the thing, so a thin wing tip the detector cut is inside the box; other parts join when they end in the
   window, sit mostly in the find, change the background the way the thing does, and no other find holds more of them (a neighbour's
   wing). A part that runs out of the window (a power line, a tree branch) counts only inside the find, without its thin runs; past a
   big find's box only thin reaches count (a rotor's arc, not a smoke trail). Clamped to the image.
3. PRINT [x, y, w, h] in image px: kit3's mark format (the thing's own edges; the kit pads it by DS.MARK.PAD itself). With --count N:
   each box, then their union; the last line is the mark to use. Exit 2 (CHECK lines on stderr) when fewer than N are found, a find
   is weak or unrefined, or the picture holds more finds as strong as the marked ones (a sky with two flocks of four gulls: the
   strongest four are marked, the others named: --region picks the one the line means).
4. PROOF: where the marks sit in the whole picture (other strong finds in red), then each box on a crop at 100% (magnified when
   small): a 1-px line just outside the measured pixels and the kit's ring (--pad, 4-px border inside) as the video will draw it,
   so a person checks it in one look."""
import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import TMP, TOOLS  # noqa: E402
from brand import BRAND_RGB  # noqa: E402

PIPELINE = str(TOOLS / "pipeline")   # heavy.py: the PC's turn-taking tickets
CACHE = TMP / "automark"
VERSION = 1                       # of the tile plan and the raw finds' format: a change detects again
BRAND = BRAND_RGB                 # the creator's accent (src/brand.ts, kit3 DS.BRAND), RGB like the picture
LINE = (0, 255, 255)              # the measured box's 1-px line in the proof
MARK_BORDER = 4                   # kit3 DS.MARK.BORDER (the ring's width, inside the padded box)
NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
           "eleven": 11, "twelve": 12, "both": 2, "a": 1, "an": 1, "the": 1}


# ------------------------------------------------------------------------------------------------------------------------- the detectors
def _pretrained(cls, repo):
    """from the local Hugging Face cache when it is there (no network), else downloaded once"""
    try:
        return cls.from_pretrained(repo, local_files_only=True)
    except OSError:
        return cls.from_pretrained(repo)


class Owl:
    """OWLv2 base (patch 16, ensemble): one box per 16-px patch of a 960x960 input, each scored against the text prompts."""
    name, repo, side = "owlv2", "google/owlv2-base-patch16-ensemble", 960
    floor, strong = 0.02, 0.10    # finds kept below `floor` are noise; a pick under `strong` is flagged weak

    @staticmethod
    def prompts(what):
        art = "an" if what[:1].lower() in "aeiou" else "a"
        return [what, f"a photo of {art} {what}"]

    def __init__(self):
        from transformers import Owlv2ForObjectDetection, Owlv2Processor
        self.proc = _pretrained(Owlv2Processor, self.repo)
        self.model = _pretrained(Owlv2ForObjectDetection, self.repo).eval()
        self.side = int(self.model.config.vision_config.image_size)
        ip = self.proc.image_processor
        self.mean = np.array(ip.image_mean, np.float32) * 255
        self.std = np.array(ip.image_std, np.float32) * 255
        self._text = None

    def run(self, tile, prompts):
        """tile: side x side RGB uint8 -> boxes (n, 4) x0 y0 x1 y1 in tile px, scores (n, prompts)"""
        import torch
        if self._text is None or self._text[0] != prompts:
            t = self.proc(text=list(prompts), return_tensors="pt")
            self._text = (list(prompts), t["input_ids"], t["attention_mask"])
        x = (tile.astype(np.float32) - self.mean) / self.std
        pv = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1)))[None]
        with torch.inference_mode():
            out = self.model(input_ids=self._text[1], attention_mask=self._text[2], pixel_values=pv)
        sc = torch.sigmoid(out.logits[0]).float().numpy()                  # (patches, prompts)
        b = out.pred_boxes[0].float().numpy()                              # cx cy w h, 0..1 of the input
        boxes = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1)
        return boxes * self.side, sc


BACKENDS = {"owlv2": Owl}


# ------------------------------------------------------------------------------------------------------------------------------ geometry
def area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def inter(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def iou(a, b):
    i = inter(a, b)
    return i / max(1e-9, area(a) + area(b) - i)


def same(a, b):
    """two finds of one thing: they overlap well, or one sits in the other at a similar size (a body vs the body and its wings)"""
    i = inter(a, b)
    if i <= 0:
        return False
    sa, sb = area(a), area(b)
    return iou(a, b) >= 0.45 or (i >= 0.75 * min(sa, sb) and max(sa, sb) <= 2.5 * min(sa, sb))


def nms(boxes, scores, thr):
    order, keep = np.argsort(-scores), []
    while order.size:
        i = order[0]
        keep.append(int(i))
        r = boxes[order[1:]]
        w = np.clip(np.minimum(r[:, 2], boxes[i, 2]) - np.maximum(r[:, 0], boxes[i, 0]), 0, None)
        h = np.clip(np.minimum(r[:, 3], boxes[i, 3]) - np.maximum(r[:, 1], boxes[i, 1]), 0, None)
        a = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        ar = (r[:, 2] - r[:, 0]) * (r[:, 3] - r[:, 1])
        order = order[1:][w * h / np.maximum(1e-9, a + ar - w * h) < thr]
    return keep


def xywh(b):
    return [int(b[0]), int(b[1]), int(b[2] - b[0]), int(b[3] - b[1])]


# ---------------------------------------------------------------------------------------------------------------------------- the tiles
def spread(length, S, overlap=0.25):
    """window starts along `length` for windows of S, evenly spread, at least `overlap` x S apart from the next window's start"""
    if length <= S:
        return [0]
    n = math.ceil((length - S) / (S * (1 - overlap))) + 1
    return [round(i * (length - S) / (n - 1)) for i in range(n)]


def plan(region, side):
    """the tiles (level, x, y, S): squares in image px that the detector sees at side x side. Level 0 is the whole region (padded to a
    square: big things), 1 squares the size of its short side, 2 tiles at 100% on big pictures (up to 2x zoom on small ones)"""
    rx, ry, rw, rh = region
    L, s = max(rw, rh), min(rw, rh)
    tiles, prev = [(0, rx, ry, L)], L
    if s < 0.75 * L:
        tiles += [(1, rx + x, ry + y, s) for y in spread(rh, s) for x in spread(rw, s)]
        prev = s
    f = int(round(side if s >= 1.5 * side else max(s / 2, side / 2)))
    if f < 0.75 * prev:
        tiles += [(2, rx + x, ry + y, f) for y in spread(rh, f) for x in spread(rw, f)]
    return tiles


def square(img, region, x, y, S, side):
    """the tile's pixels at side x side: the part of the square inside the region, the rest grey (OWLv2's own padding)"""
    rx, ry, rw, rh = region
    sq = np.full((S, S, 3), 128, np.uint8)
    x0, y0, x1, y1 = max(x, rx), max(y, ry), min(x + S, rx + rw), min(y + S, ry + rh)
    sq[y0 - y:y1 - y, x0 - x:x1 - x] = img[y0:y1, x0:x1]
    if S == side:
        return sq
    return cv2.resize(sq, (side, side), interpolation=cv2.INTER_AREA if S > side else cv2.INTER_CUBIC)


def tile_finds(boxes, scores, tile, index, region, side, floor, keep=60):
    """one tile's finds in image px: [x0, y0, x1, y1, score, level, tile, edge, per-prompt scores]; edge = cut by an inner edge"""
    lv, x, y, S = tile
    rx, ry, rw, rh = region
    best = scores.max(axis=1)
    ok = np.nonzero(best >= floor)[0]
    ok = ok[np.argsort(-best[ok])][:300]
    if not ok.size:
        return []
    b, sc, per = boxes[ok], best[ok], scores[ok]
    eps = max(3.0, 0.006 * side)
    inner = (lv > 0 and x > rx, lv > 0 and y > ry, lv > 0 and x + S < rx + rw, lv > 0 and y + S < ry + rh)
    u, out = S / side, []
    for j in nms(b, sc, 0.6)[:keep]:
        bx0, by0, bx1, by1 = b[j]
        edge = ((inner[0] and bx0 <= eps) or (inner[1] and by0 <= eps)
                or (inner[2] and bx1 >= side - eps) or (inner[3] and by1 >= side - eps))
        X0, Y0 = min(max(x + bx0 * u, rx), rx + rw), min(max(y + by0 * u, ry), ry + rh)
        X1, Y1 = min(max(x + bx1 * u, rx), rx + rw), min(max(y + by1 * u, ry), ry + rh)
        if X1 - X0 < 2 or Y1 - Y0 < 2:
            continue
        out.append([round(float(X0), 1), round(float(Y0), 1), round(float(X1), 1), round(float(Y1), 1), round(float(sc[j]), 4), lv, index,
                    int(edge), [round(float(v), 4) for v in per[j]]])
    return out


def detect(img, region, det, prompts, log=None):
    """every tile through the detector: (raw finds, tiles, seconds per tile)"""
    tiles, raw, secs = plan(region, det.side), [], []
    for i, t in enumerate(tiles):
        t0 = time.time()
        boxes, scores = det.run(square(img, region, *t[1:], det.side), prompts)
        raw += tile_finds(boxes, scores, t, i, region, det.side, det.floor)
        secs.append(round(time.time() - t0, 2))
        if log:
            log(f"tile {i + 1}/{len(tiles)} level {t[0]} at {t[1]},{t[2]} side {t[3]}: {secs[-1]} s")
    return raw, tiles, secs


# ------------------------------------------------------------------------------------------------------------------------------ the cache
def cache_file(sha, model, region, prompts):
    key = json.dumps([VERSION, model, list(region), list(prompts)])
    return CACHE / f"{sha}_{model}_{hashlib.sha1(key.encode()).hexdigest()[:12]}.json"


def file_sha(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:16]


# ---------------------------------------------------------------------------------------------------------------------- picking the finds
def candidates(raw, floor):
    """the finds merged across tiles and levels, best first, without group boxes"""
    rows = sorted((r for r in raw if not r[7] and r[4] >= floor), key=lambda r: -r[4])
    kept = []
    for r in rows:
        box = r[:4]
        for k in kept:
            if same(box, k["box"]):
                k["seen"].add(r[5])
                break
        else:
            kept.append({"box": box, "score": r[4], "level": r[5], "seen": {r[5]}})
    for k in kept:   # a box holding two or more finds that score about as high is their group (the flock round four gulls)
        inside = [o for o in kept if o is not k and inter(k["box"], o["box"]) >= 0.8 * area(o["box"])
                  and area(o["box"]) <= 0.5 * area(k["box"]) and o["score"] >= 0.5 * k["score"]]
        k["group"] = len(inside) >= 2
    return [k for k in kept if not k["group"]]


def pick(img, cands, count, strong):
    """the `count` best finds, each refined to its pixels; a find that refines onto a thing already picked is the same thing"""
    out = []
    for c in cands[:60]:                        # (a bounded time: a thing past the 60th find is no pick anyway)
        if len(out) >= count:
            break
        rivals = [o["box"] for o in cands if o is not c and o["score"] >= 0.3 * c["score"]]
        r = refine(img, c["box"], rivals)
        box = r if r is not None else clamp(c["box"], img.shape)
        if any(iou(box, o["px"]) >= 0.5 or inter(box, o["px"]) >= 0.85 * min(area(box), area(o["px"])) for o in out):
            continue
        out.append({"px": box, "box": xywh(box), "score": round(c["score"], 3), "detector": xywh(clamp(c["box"], img.shape)),
                    "level": c["level"], "refined": r is not None, "weak": c["score"] < strong})
    return out


def extras(cands, picks, strong):
    """finds as strong as the picks (>= 0.8 x the weakest pick) that are none of them: the picture holds more of the thing than asked
    (a second flock of gulls in the same sky), so the marked ones may not be the ones the line means"""
    if not picks:
        return []
    bar = max(strong, 0.8 * min(p["score"] for p in picks))
    out = []
    for c in cands:
        b = clamp(c["box"], (1 << 30, 1 << 30))
        if c["score"] >= bar and not any(iou(b, p["px"]) >= 0.3 or inter(b, p["px"]) >= 0.5 * min(area(b), area(p["px"])) for p in picks):
            out.append({"px": b, "box": xywh(b), "score": round(c["score"], 3)})
    return out


def clamp(b, shape):
    H, W = shape[:2]
    x0, y0 = min(max(int(math.floor(b[0])), 0), W - 1), min(max(int(math.floor(b[1])), 0), H - 1)
    return [x0, y0, max(x0 + 1, min(int(math.ceil(b[2])), W)), max(y0 + 1, min(int(math.ceil(b[3])), H))]


# ------------------------------------------------------------------------------------------------------------------------------- refining
def masked_blur(P, wt, sig):
    """the background under a mask: a Gaussian blur of the pixels with weight, divided by the blurred weight (normalized convolution);
    big blurs run on a smaller copy"""
    f = min(1.0, 8.0 / sig)
    if f < 1:
        sw, sh = max(1, round(P.shape[1] * f)), max(1, round(P.shape[0] * f))
        Ps, ws = cv2.resize(P, (sw, sh), interpolation=cv2.INTER_AREA), cv2.resize(wt, (sw, sh), interpolation=cv2.INTER_AREA)
    else:
        Ps, ws = P, wt
    num = cv2.GaussianBlur(Ps * ws[..., None], (0, 0), sig * f)
    den = cv2.GaussianBlur(ws, (0, 0), sig * f)
    bg = num / np.maximum(den, 1e-6)[..., None]
    return cv2.resize(bg, (P.shape[1], P.shape[0]), interpolation=cv2.INTER_LINEAR) if f < 1 else bg


def _parts(d, inE, lo, hi):
    """hysteresis: the connected parts (8-way, 1-px gaps closed) of d >= lo inside the window that hold a pixel of d >= hi"""
    low = cv2.morphologyEx(((d >= lo) & inE).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    n, lab = cv2.connectedComponents(low.astype(np.uint8), connectivity=8)
    seeds = np.unique(lab[(d >= hi) & low])
    return n, lab, seeds[seeds > 0]


YCC = np.array([[0.299, 0.587, 0.114], [-0.1687, -0.3313, 0.5], [0.5, -0.4187, -0.0813]], np.float32).T


def _dist(diff):
    """how far a pixel is from its background: brightness counts fully, colour at 35% (a JPEG's halved colour resolution smears a
    thing's colour a few px round it); x1.7 keeps a grey step's size as in RGB"""
    y = diff @ YCC
    return 1.7 * np.sqrt(y[..., 0] ** 2 + 0.35 * (y[..., 1] ** 2 + y[..., 2] ** 2))


def _median_bg(P8, s):
    """an edge-keeping background for the rough pass: a median over twice the find's size (up to 121 px), where a small thing fills at
    most a quarter of the window (a perched bird's solid body too, not only its outline) and a big one's thin parts vanish; it keeps
    soft glows and gradients. Windows over 61 px run on a half-size copy (OpenCV's big medians)"""
    kf = min(2.0 * s, 121.0)
    f = min(1.0, 61.0 / kf)
    small = cv2.resize(P8, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else P8
    k = int(max(7, round(kf * f))) | 1
    bg = cv2.medianBlur(small, k)
    return cv2.resize(bg, (P8.shape[1], P8.shape[0]), interpolation=cv2.INTER_LINEAR) if f < 1 else bg


def refine(img, box, others=(), debug=None):
    """the thing's own pixels around a find: [x0, y0, x1, y1) in image px, or None when nothing stands out from the background.
    `others`: the other finds' boxes; a part one of them holds more of is that find's (a neighbour bird's wing in this box)"""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = box
    s = max(x1 - x0, y1 - y0, 4.0)
    m = max(12.0, 0.5 * s)                      # how far past the find a part the detector cut may reach
    E = [max(0, int(x0 - m)), max(0, int(y0 - m)), min(W, int(math.ceil(x1 + m))), min(H, int(math.ceil(y1 + m)))]
    c = int(math.ceil(0.3 * s)) + 8             # context for the backgrounds
    C = [max(0, E[0] - c), max(0, E[1] - c), min(W, E[2] + c), min(H, E[3] + c)]
    P8 = np.ascontiguousarray(img[C[1]:C[3], C[0]:C[2]])
    P = P8.astype(np.float32)
    h, w = P.shape[:2]
    inD = np.zeros((h, w), bool)
    inD[max(0, int(y0) - C[1]):int(math.ceil(y1)) - C[1], max(0, int(x0) - C[0]):int(math.ceil(x1)) - C[0]] = True
    inE = np.zeros((h, w), bool)
    inE[E[1] - C[1]:E[3] - C[1], E[0] - C[0]:E[2] - C[0]] = True
    if not inD.any():
        return None
    k3 = np.ones((3, 3), np.uint8)
    # pass 1 (rough): a median background; the clear cores of what stands out in the window
    d = _dist(P - _median_bg(P8, s).astype(np.float32))
    peak = float(np.percentile(cv2.blur(d, (3, 3))[inD], 99.5))
    hi = max(6.0, 0.6 * peak)
    n, lab, seeds = _parts(d, inE, max(4.0, 0.35 * peak), hi)
    if not seeds.size:
        return None
    # passes 2-3 (fine): a blur that skips those parts (normalized convolution), narrow enough (a few times the thing's thickness: the
    # part with the most strong pixels in the find, not a cloud band beside it) to follow the clouds and brush strokes round the thing;
    # the background's noise is measured on the rest of the window
    for _ in range(2):
        obj = np.isin(lab, seeds)
        strong = np.bincount(lab[(d >= hi) & inD], minlength=n)
        strong[0] = 0
        core = lab == int(np.argmax(strong))
        hole = cv2.dilate(obj.astype(np.uint8), k3, iterations=2) > 0
        T = float(cv2.distanceTransform(core.astype(np.uint8), cv2.DIST_L2, 3).max()) if strong.max() > 0 else 2.0
        sig = max(2.5, 0.8 * (T + 2))
        diff = P - masked_blur(P, (~hole).astype(np.float32), sig)
        d = _dist(diff)
        ring = inE & ~hole
        dr = d[ring] if ring.sum() >= 50 else d[inE]
        noise = max(3.0 * float(np.median(dr)), float(np.percentile(dr, 98))) + 1.0
        peak = float(np.percentile(cv2.blur(d, (3, 3))[inD], 99.5))
        if peak < 1.25 * noise:
            return None
        lo, hi = max(noise, min(0.2 * peak, 12.0)), max(1.5 * noise, 0.45 * peak)
        n, lab, seeds = _parts(d, inE, lo, hi)
        if not seeds.size:
            return None
    n_all = np.bincount(lab.ravel(), minlength=n)
    n_in = np.bincount(lab[inD], minlength=n)
    edge = np.zeros((h, w), bool)               # the window's sides that are not the picture's
    ex0, ey0, ex1, ey1 = E[0] - C[0], E[1] - C[1], E[2] - C[0], E[3] - C[1]
    if E[0] > 0:
        edge[ey0:ey1, ex0] = True
    if E[1] > 0:
        edge[ey0, ex0:ex1] = True
    if E[2] < W:
        edge[ey0:ey1, ex1 - 1] = True
    if E[3] < H:
        edge[ey1 - 1, ex0:ex1] = True
    runs = np.zeros(n, bool)
    runs[np.unique(lab[edge])] = True
    top = float(n_in[seeds].max())
    if top == 0:
        return None
    # the thing: the part with the most pixels in the find, preferring one that ends inside the window over one that runs out of it
    whole = [L for L in seeds if not runs[L] and n_in[L] >= 0.25 * top]
    main = int(max(whole or list(seeds), key=lambda L: n_in[L]))
    # other parts join when they end inside the window, sit mostly in the find and differ from the background the way the thing does
    # (a lighter cloud streak under a dark bird does not)
    core = (lab == main) & (d >= hi)
    u = diff[core].mean(axis=0) if core.any() else diff[lab == main].mean(axis=0)
    v = np.stack([np.bincount(lab.ravel(), weights=diff[..., i].ravel(), minlength=n) for i in range(3)], 1) / np.maximum(n_all, 1)[:, None]
    alike = v @ u >= 0.5 * np.linalg.norm(v, axis=1) * np.linalg.norm(u)
    held = np.zeros(n)                          # the largest share of each part another find's box holds
    for o in others:                            # (not a box round this find: that one holds everything)
        if inter(o, E) <= 0 or inter(o, box) >= 0.5 * area(box):
            continue
        ob = np.zeros((h, w), bool)
        oy0, oy1 = max(0, int(o[1]) - C[1]), max(0, int(math.ceil(o[3])) - C[1])
        ob[oy0:oy1, max(0, int(o[0]) - C[0]):max(0, int(math.ceil(o[2])) - C[0])] = True
        if ob.any():
            held = np.maximum(held, np.bincount(lab[ob], minlength=n) / np.maximum(n_all, 1))
    keep = [main] + [int(L) for L in seeds if L != main and not runs[L] and n_in[L] >= 0.4 * n_all[L] and alike[L]
                     and held[L] <= n_in[L] / n_all[L]]
    # a part that runs out of the window counts only inside the find (+ t), without its thin runs (the power line under a perched bird)
    t = max(2, min(round(0.06 * s), 12))
    Dt = np.zeros((h, w), bool)
    ys, xs = np.nonzero(inD)
    Dt[max(0, ys.min() - t):ys.max() + 1 + t, max(0, xs.min() - t):xs.max() + 1 + t] = True
    el = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    sel = np.zeros((h, w), bool)
    for L in keep:
        comp = lab == L
        if runs[L]:
            body = cv2.morphologyEx((comp & Dt).astype(np.uint8), cv2.MORPH_OPEN, el)
            comp = (cv2.dilate(body, k3, iterations=3) > 0) & comp & Dt if body.any() else comp & Dt
        sel |= comp
    # past a big find's box (its box is good to a few %), only thin reaches count (a rotor's arc); a thick one (a smoke trail)
    # stops at the box. A small find keeps every reach: its detector box is coarse, and a cut wing tip is the error this tool fixes
    out = (sel & ~Dt).astype(np.uint8)
    if out.any() and s >= 150:
        thin = max(6.0, 0.04 * s)
        no, olab = cv2.connectedComponents(out, connectivity=8)
        half = cv2.distanceTransform(out, cv2.DIST_L2, 3)
        fat = np.zeros(no, np.float32)
        np.maximum.at(fat, olab.ravel(), half.ravel())
        fat[0] = 0
        sel &= ~np.isin(olab, np.nonzero(2 * fat > thin)[0])
    if not sel.any():
        return None
    ys, xs = np.nonzero(sel)
    if debug is not None:
        debug.update({"noise": round(noise, 1), "peak": round(peak, 1), "lo": round(lo, 1), "hi": round(hi, 1), "sig": round(sig, 1),
                      "parts": len(keep), "runs_out": bool(runs[main]), "maps": (C, d, lab, sel, inD, inE)})
    return [int(xs.min()) + C[0], int(ys.min()) + C[1], int(xs.max()) + 1 + C[0], int(ys.max()) + 1 + C[1]]


# ------------------------------------------------------------------------------------------------------------------------------ the proof
def _font(size):
    for f in ("arial.ttf", "Arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):   # macOS names its Arial file "Arial.ttf"
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _line(a, b, color):
    """a 1-px rectangle just outside the box [x0, y0, x1, y1) (the box's own pixels stay visible)"""
    cv2.rectangle(a, (b[0] - 1, b[1] - 1), (b[2], b[3]), color, 1)


def _ring(a, b, pad, color):
    """the kit's mark: the box padded by `pad`, a MARK_BORDER-px border inside that outer edge"""
    for i in range(MARK_BORDER):
        cv2.rectangle(a, (b[0] - pad + i, b[1] - pad + i), (b[2] + pad - 1 - i, b[3] + pad - 1 - i), color, 1)


def proof(img, picks, union, pad, path, title, others=()):
    """the sheet: where the marks are in the whole picture (and any other finds as strong, in red), then the union (with every box),
    then each box, on 100% crops; small ones magnified beside it"""
    H, W = img.shape[:2]
    font, small = _font(20), _font(16)
    k = min(1.0, 900 / W)                      # the overview
    ov = cv2.resize(img, (round(W * k), round(H * k)), interpolation=cv2.INTER_AREA)
    for q, col in [(p["px"], BRAND) for p in picks] + [(e["px"], (255, 60, 60)) for e in others]:
        x0, y0 = int(q[0] * k) - 3, int(q[1] * k) - 3
        cv2.rectangle(ov, (x0, y0), (int(math.ceil(q[2] * k)) + 2, int(math.ceil(q[3] * k)) + 2), col, 2)
    tag0 = "where: the marks" + (f" (brand) and {len(others)} other finds as strong (red: pass --region if the line means them)"
                                 if others else "") + f"   whole picture at {k:.0%}"
    items = ([("union", union, [p["px"] for p in picks])] if union else []) + [
        (f"{i + 1}: [{', '.join(map(str, p['box']))}] score {p['score']}" + ("" if p["refined"] else " (not refined: detector box)")
         + (" WEAK" if p["weak"] else ""), p["px"], [p["px"]]) for i, p in enumerate(picks)]
    panels = [(tag0, ov)]
    for label, b, lines in items:
        mg = int(max(24, 0.35 * max(b[2] - b[0], b[3] - b[1]))) + pad + MARK_BORDER
        cx0, cy0, cx1, cy1 = max(0, b[0] - mg), max(0, b[1] - mg), min(W, b[2] + mg), min(H, b[3] + mg)
        crop = np.ascontiguousarray(img[cy0:cy1, cx0:cx1])
        rel = [[q[0] - cx0, q[1] - cy0, q[2] - cx0, q[3] - cy0] for q in lines]
        view = crop.copy()
        _ring(view, [b[0] - cx0, b[1] - cy0, b[2] - cx0, b[3] - cy0], pad, BRAND)
        for r in rel:
            _line(view, r, LINE)
        views = [view]
        z = min(8, 420 // max(crop.shape[:2]))
        if z >= 2:                                 # magnified: the line only, so every pixel of the thing shows
            big = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
            for r in rel:
                cv2.rectangle(big, (r[0] * z - 1, r[1] * z - 1), (r[2] * z, r[3] * z), LINE, 1)
            views.append(big)
        vh = max(v.shape[0] for v in views)
        body = np.full((vh, sum(v.shape[1] for v in views) + 12 * (len(views) - 1), 3), 32, np.uint8)
        x = 0
        for v in views:
            body[:v.shape[0], x:x + v.shape[1]] = v
            x += v.shape[1] + 12
        tag = label if label != "union" else f"union [{', '.join(map(str, xywh(b)))}]"
        tag += f"   100% crop at {cx0},{cy0}" + (f", then x{z}" if z >= 2 else "")
        panels.append((tag, body))
    sw = max(max(p[1].shape[1] for p in panels), 900)
    sh = 44 + sum(30 + p[1].shape[0] + 16 for p in panels)
    sheet = Image.new("RGB", (sw + 24, sh), (32, 32, 32))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 10), title, fill=(240, 240, 240), font=font)
    y = 44
    for tag, body in panels:
        dr.text((12, y + 4), tag, fill=(220, 220, 220), font=small)
        sheet.paste(Image.fromarray(body), (12, y + 30))
        y += 30 + body.shape[0] + 16
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=92)


# ---------------------------------------------------------------------------------------------------------------------------------- input
def load_image(path):
    im = ImageOps.exif_transpose(Image.open(path))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        im = Image.alpha_composite(Image.new("RGBA", im.size, (0, 0, 0, 255)), im)
    return np.asarray(im.convert("RGB")).copy()


def parse_what(what, count):
    """'four gulls' -> ('gull', 4); 'the tattoo' -> ('tattoo', 1); --count wins over the words"""
    words = what.strip().split()
    n = None
    if words and (words[0].lower() in NUMBERS or words[0].isdigit()):
        n = int(words[0]) if words[0].isdigit() else NUMBERS[words[0].lower()]
        words = words[1:] or words
    if n and n > 1 and words:
        last = words[-1]
        if re.search(r"[^aeiou]ies$", last):
            last = last[:-3] + "y"
        elif re.search(r"(ches|shes|sses|xes)$", last):
            last = last[:-2]
        elif last.endswith("s") and not last.endswith("ss"):
            last = last[:-1]
        words[-1] = last
    return " ".join(words), count or n or 1


def parse_region(text, shape):
    H, W = shape[:2]
    if not text:
        return (0, 0, W, H)
    x, y, w, h = (int(round(float(v))) for v in text.split(","))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 - x0 < 8 or y1 - y0 < 8:
        raise SystemExit(f"--region {text} is off the picture ({W} x {H})")
    return (x0, y0, x1 - x0, y1 - y0)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "thing"


# ---------------------------------------------------------------------------------------------------------------------------------- main
def find(image, what, count=None, region=None, model="owlv2", threads=2, fresh=False, log=None):
    """the whole job: (picks, union, info). The detector runs only when its finds are not cached, inside a heavy.py ticket."""
    log = log or (lambda s: print(s, file=sys.stderr, flush=True))
    t0 = time.time()
    query, n = parse_what(what, count)
    img = load_image(image)
    reg = parse_region(region, img.shape)
    Det = BACKENDS[model]
    prompts = Det.prompts(query)
    cf = cache_file(file_sha(image), Det.name, reg, prompts)
    info = {"query": query, "count": n, "model": Det.name, "prompts": prompts, "region": list(reg), "cache": str(cf)}
    data = None
    whole = (0, 0, img.shape[1], img.shape[0])
    for f, inside in ((cf, None), (cache_file(file_sha(image), Det.name, whole, prompts), reg)):
        if data is not None or fresh or not f.exists() or (inside is not None and reg == whole):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            info["cached"] = True
        except (OSError, ValueError):
            continue
        if inside:   # the whole picture's finds whose centre is inside the region (--fresh detects on the region's own tiles)
            rx, ry, rw, rh = inside
            data["raw"] = [r for r in data["raw"] if rx <= (r[0] + r[2]) / 2 <= rx + rw and ry <= (r[1] + r[3]) / 2 <= ry + rh]
            info["cache"] = f"{f} (the whole picture's finds inside the region)"
    waited = 0.0
    if data is None:
        sys.path.insert(0, PIPELINE)
        from heavy import HeavyJob
        tw = time.time()
        with contextlib.redirect_stdout(sys.stderr), HeavyJob(f"automark {Path(image).name} {query}", "score"):
            t1 = time.time()
            waited = t1 - tw                    # the PC's turn: not the tool's own time
            import torch
            torch.set_num_threads(threads)
            cv2.setNumThreads(2)
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            from transformers.utils import logging as hf_logging
            hf_logging.set_verbosity_error()
            det = Det()
            t2 = time.time()
            raw, tiles, secs = detect(img, reg, det, prompts, log)
            t3 = time.time()
        data = {"version": VERSION, "image": str(image), "size": [img.shape[1], img.shape[0]], "model": Det.name, "region": list(reg),
                "prompts": prompts, "tiles": tiles, "tile_seconds": secs, "load_seconds": round(t2 - t1, 1),
                "detect_seconds": round(t3 - t2, 1), "raw": raw}
        CACHE.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps(data), encoding="utf-8")
        info["cached"] = False
        info["seconds_model"] = {"load": round(t2 - t1, 1), "detect": round(t3 - t2, 1), "tiles": len(tiles)}
    t4 = time.time()
    cands = candidates(data["raw"], Det.floor)
    picks = pick(img, cands, n, Det.strong)
    info["extras"] = extras(cands, picks, Det.strong)
    union = None
    if len(picks) > 1:
        px = [p["px"] for p in picks]
        union = [min(b[0] for b in px), min(b[1] for b in px), max(b[2] for b in px), max(b[3] for b in px)]
    info["seconds_refine"] = round(time.time() - t4, 2)
    info["seconds"] = round(time.time() - t0 - waited, 1)
    info["waited_for_turn"] = round(waited, 1)
    info["img"] = img
    return picks, union, info


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("image")
    ap.add_argument("what", help='the thing: "helicopter", "the tattoo", "four gulls"')
    ap.add_argument("--count", type=int, help="how many (default: the number word in <what>, else 1)")
    ap.add_argument("--region", help="x,y,w,h: search only there (image px)")
    ap.add_argument("--pad", type=int, default=8, help="the kit's pad round a mark (kit3 DS.MARK.PAD): the proof's ring")
    ap.add_argument("--proof", help="the proof sheet (default TMP/automark/<image>__<what>.jpg)")
    ap.add_argument("--json", action="store_true", help="print JSON")
    ap.add_argument("--threads", type=int, default=2, help="torch threads (2 leaves the PC free for the other jobs)")
    ap.add_argument("--fresh", action="store_true", help="detect again, ignoring the cached finds")
    a = ap.parse_args()
    picks, union, info = find(a.image, a.what, a.count, a.region, "owlv2", a.threads, a.fresh)
    img = info.pop("img")
    H, W = img.shape[:2]
    out = a.proof or str(CACHE / f"{Path(a.image).stem}__{slug(info['query'])}.jpg")
    warn = []
    if len(picks) < info["count"]:
        reused = "inside the region" in info["cache"]
        warn.append(f"only {len(picks)} of {info['count']} found"
                    + (" in the whole picture's cached finds: --fresh detects on the region's own tiles" if reused else ""))
    warn += [f"{info['query']} {i + 1} is weak (score {p['score']})" for i, p in enumerate(picks) if p["weak"]]
    warn += [f"{info['query']} {i + 1} was not refined (nothing stands out from its background): the detector's box"
             for i, p in enumerate(picks) if not p["refined"]]
    if info["extras"]:
        warn.append(f"{len(info['extras'])} more {info['query']} finds as strong as the marked ones (" + "; ".join(
            f"[{', '.join(map(str, e['box']))}] {e['score']}" for e in info["extras"][:5]) + "): pass --region if the mark means them")
    mark = union or (picks[0]["px"] if picks else None)
    if mark and (mark[0] - a.pad < 0 or mark[1] - a.pad < 0 or mark[2] + a.pad > W or mark[3] + a.pad > H):
        warn.append(f"the mark's ring (pad {a.pad}) runs past the picture's edge")
    secs = f"{info['seconds']} s" + ("" if info["cached"] else f" (model load {info['seconds_model']['load']} s, "
                                     f"{info['seconds_model']['tiles']} tiles {info['seconds_model']['detect']} s)")
    if info["waited_for_turn"] >= 1:
        secs += f", after {info['waited_for_turn']:.0f} s waiting for the PC's turn"
    title = (f"{Path(a.image).name}  \"{info['query']}\" x{info['count']}  {info['model']}  {secs}"
             + ("  cached finds" if info["cached"] else ""))
    if picks:
        proof(img, picks, union, a.pad, out, title, info["extras"])
    if a.json:
        print(json.dumps({"image": a.image, **{k: v for k, v in info.items()}, "boxes": [{k: v for k, v in p.items() if k != "px"}
              for p in picks], "union": xywh(union) if union else None, "mark": xywh(mark) if mark else None,
              "proof": out if picks else None, "warnings": warn}))
    else:
        for i, p in enumerate(picks):
            print(f"{info['query']} {i + 1}  [{', '.join(map(str, p['box']))}]  score {p['score']}"
                  + ("" if p["refined"] else "  (detector box)") + ("  WEAK" if p["weak"] else ""))
        if union:
            print(f"union  [{', '.join(map(str, xywh(union)))}]")
        print(f"proof  {out if picks else '(none: nothing found)'}")
        print(f"mark   [{', '.join(map(str, xywh(mark)))}]" if mark else "mark   (none)")
        print(f"time   {secs}", file=sys.stderr)
        for x in warn:
            print(f"CHECK  {x}", file=sys.stderr)
    return 2 if warn and (len(picks) < info["count"] or info["extras"] or any(p["weak"] or not p["refined"] for p in picks)) else 0


if __name__ == "__main__":
    sys.exit(main())
