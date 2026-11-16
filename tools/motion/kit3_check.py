"""kit3's proof, measured on the demo's rendered stills (kit3_proof.mjs), from the pixels alone:

  EDIT tools/motion/kit3_check.py <proof_dir> [--sheet <out.png>]

1. MARKS ON THEIR INK (pages): each brand mark found in the still by its colour (the wash: the brand multiplied over the page; the box:
   the brand ring); the ink inside it found by the page's own contrast; the four gaps from the ink to the mark's outer edge must each be
   the kit's pad (8 px x the stage's push at the hold) within 2 px. A mark short of its words, loose round blank space, leaning to one
   side or with its border on the letters fails (the four ways a mark goes wrong). And the right words: the ink inside has the shape of
   the target words' ink in the capture (width and height scale alike, within 3%).
2. MARKS ON THEIR TARGET (pictures): a still's or a clip's mark is the room's light on its target with its name tag: the tag (a
   brand chip) centred on where the target box lands on screen (the region's scale, the push at the hold) within 3 px, 0-60 px above or
   below it, and the target lit 1.2x or more over the dimmed room round it.
3. ROWS (plain stage): the visible figures' gaps equal within 2 px; the whole visible content (figures and names) centred on x 960 within
   4 px.
The demo's media are drawn by kit3_demo_assets.py (its pages hold their words inside the boxes below). The brand colour comes from
src/brand.ts (brand.py). Writes <proof_dir>/check.json and prints one line per check; exit 1 when any fails. --sheet: every mark's tile
at 3x, for the eye."""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import TMP  # noqa: E402
from brand import BRAND_RGB  # noqa: E402

PUB = TMP / "pub_kit3"
PAD = 8
WASH = 0.85                                                       # kit3 DS.MARK.WASH: the brand multiplied over the page at 85%
WASH_RGB = tuple(0.15 * 255 + WASH * c for c in BRAND_RGB)        # the wash on white paper

# ------------------------------------------------------------------------------------------------------------------- the demo's facts
# pages: frame -> (capture, the stage push at the hold, look, [original word boxes in reading order])
PAGES = {
    60: ("kit3/demo/pages/page_light.png", (0.44, 3.0), "wash", [[0, 418, 683, 65]]),
    174: ("kit3/demo/pages/page_light.png", (0.44, 3.0), "wash", [[729, 331, 263, 55], [0, 418, 683, 65]]),
    354: ("kit3/demo/pages/page_dark.png", (0.54, 3.0), "box", [[806, 152, 153, 70], [72, 229, 856, 70], [72, 305, 156, 70]]),
    564: ("kit3/demo/pages/page_headline.png", (0.54, 3.5), "wash", [[73, 200, 796, 124]]),
    744: ("kit3/demo/pages/page_number.png", (0.44, 3.0), "wash", [[57, 253, 133, 39]]),
}
# pictures: frame -> (the newest lit target box in picture px, region or None, picture size, push range, hold, shot length)
PICS = {
    792: ([1005, 80, 190, 140], [331, 20, 1538, 865], (1920, 885), (1.0, 1.04), 0.34, 3.5),
    954: ([1264, 657, 117, 109], [331, 20, 1538, 865], (1920, 885), (1.0, 1.04), 0.34, 3.5),
    1086: ([410, 330, 380, 100], None, (1920, 1080), (1.0, 1.02), 0.84, 2.2),
}
# the picture under a mark stands still: (frame a, frame b, region x0 y0 x1 y1, still?) both after the hold must match;
# the pair before the hold must differ (the clip plays until the mark)
FROZEN = [(120, 174, (203, 350, 1717, 780), True, "page A: the card after its first light (0.9 s apart, both marks lit)"),
          (1040, 1086, (0, 0, 1920, 940), True, "clip F: the frame from the mark's light on (0.77 s apart)"),
          (980, 1000, (0, 0, 1920, 940), False, "clip F before the hold: still playing (0.33 s apart)")]
ROWS = {1266: ("devices, names wider than their figures", True), 1446: ("covers with 0-420 px transparent margins", True),
        1806: ("logos", False)}


def dominant(px):
    q = (px.reshape(-1, 3) // 16).astype(np.int32)
    k = Counter(map(tuple, q)).most_common(1)[0][0]
    return np.array(k) * 16 + 8


def ink_mask(px, paper):
    return np.abs(px.astype(np.int32) - paper).max(axis=2) > 60


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def components(mask, min_area):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a >= min_area:
            out.append((int(x), int(y), int(x + w), int(y + h), int(a)))
    return out


def find_marks(img, look):
    r, g, b = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    if look == "wash":
        # the paper under the wash: near the wash's colour on white (a light paper's tint and the edges' blending allowed), and as
        # coloured as it (black ink stays black under a multiply; white paper stays out)
        wr, wg, wb = WASH_RGB
        chroma = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
        m = (np.abs(r - wr) < 60) & (np.abs(g - wg) < 60) & (np.abs(b - wb) < 60) & (chroma > 0.5 * (max(WASH_RGB) - min(WASH_RGB)))
        cs = [c for c in components(m, 300) if (c[2] - c[0]) > 20 and (c[3] - c[1]) > 16]
        # the wash showing through a letter's counter (the bowl of an "a", an "o") is inside a bigger wash: not a mark of its own
        cs = [c for c in cs if not any(o is not c and o[0] <= c[0] and o[1] <= c[1] and o[2] >= c[2] and o[3] >= c[3] for o in cs)]
    else:
        br, bg, bb = BRAND_RGB
        m = (np.abs(r - br) < 45) & (np.abs(g - bg) < 40) & (np.abs(b - bb) < 73)
        cs = [c for c in components(m, 200) if (c[2] - c[0]) > 24 and (c[3] - c[1]) > 18
              and c[4] / ((c[2] - c[0]) * (c[3] - c[1])) < 0.55     # a ring, not a filled chip (the name tags)
              and 0.6 <= c[4] / (4 * 2 * ((c[2] - c[0]) + (c[3] - c[1]))) <= 1.3]   # 4 px thick (not brand-coloured art in the picture)
    return sorted(cs, key=lambda c: (round(c[1] / 20), c[0]))


def snap_capture(cap, box):
    """the target words' ink in the capture: the kit's layout.inkSnap ported (glyphs crossing the line's core band, centred in the box;
    touching glyphs within 12% of the line box; dots and accents over the run)"""
    x, y, w, h = box
    ext, vext = round(0.6 * h), round(0.3 * h)
    rx, ry = max(0, x - ext), max(0, y - vext)
    reg = cap[ry:min(cap.shape[0], y + h + vext), rx:min(cap.shape[1], x + w + ext)]
    paper = dominant(reg)
    ink = ink_mask(reg, paper).astype(np.uint8)
    c0, c1, r0, r1 = max(0, x - rx), min(ink.shape[1], x + w - rx), max(0, y - ry), min(ink.shape[0], y + h - ry)
    count = ink[r0:r1, c0:c1].sum(axis=1)
    if count.max() == 0:
        return None
    peak = int(count.argmax())
    thr = 0.25 * count.max()
    cT = cB = peak
    low, yy = 0, peak - 1
    while yy >= 0 and low <= 2:
        if count[yy] >= thr:
            cT, low = yy, 0
        else:
            low += 1
        yy -= 1
    low, yy = 0, peak + 1
    while yy < len(count) and low <= 2:
        if count[yy] >= thr:
            cB, low = yy, 0
        else:
            low += 1
        yy += 1
    cT, cB = cT + r0, cB + r0
    coreH = cB - cT + 1
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
    comps = [(int(st[i][0]), int(st[i][1]), int(st[i][0] + st[i][2] - 1), int(st[i][1] + st[i][3] - 1)) for i in range(1, n)]
    crosses = [max(0, min(c[3], cB) - max(c[1], cT) + 1) >= 0.4 * (c[3] - c[1] + 1) for c in comps]
    take = [cr and c0 <= (c[0] + c[2]) / 2 < c1 for c, cr in zip(comps, crosses)]
    if not any(take):
        return None
    L = min(c[0] for c, t in zip(comps, take) if t)
    R = max(c[2] for c, t in zip(comps, take) if t)
    gx = max(3, round(0.12 * h))
    grew = True
    while grew:
        grew = False
        for i, c in enumerate(comps):
            if not take[i] and crosses[i] and c[0] <= R + gx and c[2] >= L - gx:
                take[i], grew = True, True
                L, R = min(L, c[0]), max(R, c[2])
    for i, c in enumerate(comps):
        clear = c[3] < cT or c[1] > cB
        whole = c[1] > 0 and c[3] < ink.shape[0] - 1
        if (not take[i] and clear and whole and c[3] - c[1] + 1 <= 0.6 * coreH and c[1] >= cT - 0.8 * coreH and c[3] <= cB + 0.8 * coreH
                and c[0] >= L - gx and c[2] <= R + gx):
            take[i] = True
    sel = [c for c, t in zip(comps, take) if t]
    L, T, R, B = min(c[0] for c in sel), min(c[1] for c in sel), max(c[2] for c in sel), max(c[3] for c in sel)
    return rx + L, ry + T, R - L + 1, B - T + 1


def run_ink(reg):
    """the marked run's ink inside a mark, by glyphs (the kit's own definition): the core band (rows with 25% of the busiest row's
    ink), the glyphs on it (40% of their height in it), small glyphs over or under them; a glyph on the band touching the mark's edge
    is one of its own letters CUT by the mark (a fault); a glyph off the band touching the edge comes from outside (a neighbouring
    line's descender, the paper in a rounded corner) and is left out. Returns (ink box, cut letters, foreign glyphs)."""
    ink = ink_mask(reg, dominant(reg)).astype(np.uint8)
    h, w = ink.shape
    count = ink.sum(axis=1)
    if count.max() == 0:
        return None, 0, 0
    peak, thr = int(count.argmax()), 0.25 * count.max()
    cT = cB = peak
    low, y = 0, peak - 1
    while y >= 0 and low <= 2:
        if count[y] >= thr:
            cT, low = y, 0
        else:
            low += 1
        y -= 1
    low, y = 0, peak + 1
    while y < h and low <= 2:
        if count[y] >= thr:
            cB, low = y, 0
        else:
            low += 1
        y += 1
    coreH = cB - cT + 1
    n, _lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
    keep, cut, foreign = [], 0, 0
    for i in range(1, n):
        x, yy, cw, ch = int(st[i][0]), int(st[i][1]), int(st[i][2]), int(st[i][3])
        x1, y1 = x + cw - 1, yy + ch - 1
        on = max(0, min(y1, cB) - max(yy, cT) + 1) >= 0.4 * ch
        edge = x == 0 or yy == 0 or x1 == w - 1 or y1 == h - 1
        if on and edge:
            cut += 1
            keep.append((x, yy, x1, y1))
        elif edge:
            foreign += 1
        elif on or (ch <= 0.6 * coreH and yy >= cT - 0.8 * coreH and y1 <= cB + 0.8 * coreH):
            keep.append((x, yy, x1, y1))
    if not keep:
        return None, cut, foreign
    return (min(k[0] for k in keep), min(k[1] for k in keep), max(k[2] for k in keep) + 1, max(k[3] for k in keep) + 1), cut, foreign


def check_pages(d, tiles):
    res = []
    for fr, (cap_rel, (hold, dur), look, boxes) in PAGES.items():
        img = cv2.cvtColor(cv2.imread(str(d / f"f_{fr}.png")), cv2.COLOR_BGR2RGB)
        cap = cv2.cvtColor(cv2.imread(str(PUB / cap_rel)), cv2.COLOR_BGR2RGB)
        s = 1 + 0.03 * hold / dur
        want = PAD * s
        found = find_marks(img, look)
        if len(found) != len(boxes):
            res.append({"check": "MARK", "frame": fr, "ok": False, "what": f"{len(found)} {look} marks found, {len(boxes)} expected"})
            continue
        ratios = []
        for (x0, y0, x1, y1, _a), box in zip(found, boxes):
            sh = 5 if look == "box" else 0
            reg = img[y0 + sh:y1 - sh, x0 + sh:x1 - sh]
            bb, cut, foreign = run_ink(reg)
            if bb is None:
                res.append({"check": "MARK", "frame": fr, "ok": False, "what": f"no ink inside the mark at {x0},{y0}"})
                continue
            gaps = [bb[0] + sh, bb[1] + sh, (x1 - x0) - (bb[2] + sh), (y1 - y0) - (bb[3] + sh)]
            ok = all(abs(g - want) <= 2 for g in gaps) and not cut
            src = snap_capture(cap, box)
            rw, rh = (bb[2] - bb[0]) / src[2], (bb[3] - bb[1]) / src[3]
            ratios.append((rw, rh))
            same = abs(rw - rh) / max(rw, rh) <= 0.03 or abs((bb[3] - bb[1]) - src[3] * rw) <= 2
            res.append({"check": "MARK", "frame": fr, "ok": bool(ok and same), "mark": [x0, y0, x1 - x0, y1 - y0], "look": look,
                        "gaps_ltrb": gaps, "want": round(want, 2), "target_box": box, "target_ink": list(map(int, src)),
                        "scale_w_h": [round(rw, 4), round(rh, 4)],
                        "cut_letters": cut, "foreign_edge_glyphs": foreign,
                        "what": f"gaps L{gaps[0]} T{gaps[1]} R{gaps[2]} B{gaps[3]} (want {want:.1f} +-2); the words' shape x{rw:.3f}/x{rh:.3f}"
                                + (f"; {cut} of its own letters cut by the mark" if cut else "")
                                + (f"; {foreign} edge fragment(s) from outside the run left out (the wash's rounded corners, a neighbouring line's descender)" if foreign else "")})
            tiles.append((f"f{fr} {look}", img[max(0, y0 - 14):y1 + 14, max(0, x0 - 14):x1 + 14]))
    return res


def check_pics(d, tiles):
    res = []
    for fr, (box, region, (iw, ih), push, hold, dur) in PICS.items():
        img = cv2.cvtColor(cv2.imread(str(d / f"f_{fr}.png")), cv2.COLOR_BGR2RGB)
        if region:
            sc = max(1920 / region[2], 1080 / region[3])
            ox, oy = region[0] - (1920 / sc - region[2]) / 2, region[1] - (1080 / sc - region[3]) / 2
        else:
            sc, ox, oy = 1.0, 0.0, 0.0
        L, T = math.floor((box[0] - ox) * sc) - PAD, math.floor((box[1] - oy) * sc) - PAD
        R, B = math.ceil((box[0] + box[2] - ox) * sc) + PAD, math.ceil((box[1] + box[3] - oy) * sc) + PAD
        k = push[0] + (push[1] - push[0]) * hold / dur
        want = [960 + (L - 960) * k, 540 + (T - 540) * k, 960 + (R - 960) * k, 540 + (B - 540) * k]
        # a picture's mark is the room's light on its target with the name tag beside it (one dim per picture, a hole round each
        # target): the tag (a filled brand chip) is centred on the target's x and sits just above or below it, and the target is lit
        tags = find_tags(img)
        if not tags:
            res.append({"check": "TARGET", "frame": fr, "ok": False, "what": "no name tag found"})
            continue
        cx = (want[0] + want[2]) / 2
        best = min(tags, key=lambda c: abs((c[0] + c[2]) / 2 - cx) + min(abs(c[1] - want[3]), abs(want[1] - c[3])))
        dx = round((best[0] + best[2]) / 2 - cx, 1)
        gap = best[1] - want[3] if best[1] >= (want[1] + want[3]) / 2 else want[1] - best[3]
        lit = lit_ratio(img, want, best)
        ok = abs(dx) <= 3 and -2 <= gap <= 60 and lit >= 1.2
        res.append({"check": "TARGET", "frame": fr, "ok": ok, "tag": list(best[:4]), "want": [round(v, 1) for v in want], "dx": dx,
                    "gap": round(gap, 1), "lit": round(lit, 2),
                    "what": f"tag {best[:4]} on its target {[round(v) for v in want]}: centre off {dx} px (want 3 or less), {round(gap)} px "
                            f"from it (want 0-60), the target lit {lit:.2f}x the room round it (want 1.2x+)"})
        y0, y1 = int(min(best[1], want[1])) - 14, int(max(best[3], want[3])) + 14
        x0, x1 = int(min(best[0], want[0])) - 14, int(max(best[2], want[2])) + 14
        tiles.append((f"f{fr} target", img[max(0, y0):y1, max(0, x0):x1]))
    return res


def find_tags(img):
    """the name tags: filled chips of the brand colour (the words on them are ink, so the chip fills most of its box)"""
    r, g, b = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    br, bg, bb = BRAND_RGB
    m = (np.abs(r - br) < 45) & (np.abs(g - bg) < 40) & (np.abs(b - bb) < 73)
    return [c for c in components(m, 400) if (c[2] - c[0]) > 40 and (c[3] - c[1]) > 24
            and c[4] / ((c[2] - c[0]) * (c[3] - c[1])) >= 0.55]


def lit_ratio(img, rect, tag):
    """the mean brightness on the target (its rect, the tag left out) over the room's: a band 40-120 px outside the rect"""
    y = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    H, W = y.shape
    inner = np.zeros((H, W), bool)
    L, T, R, B = (int(round(v)) for v in rect)
    inner[max(0, T):B, max(0, L):R] = True
    near = np.zeros((H, W), bool)
    near[max(0, T - 40):B + 40, max(0, L - 40):R + 40] = True
    band = np.zeros((H, W), bool)
    band[max(0, T - 120):B + 120, max(0, L - 120):R + 120] = True
    band &= ~near
    for m in (inner, band):
        m[max(0, tag[1] - 4):tag[3] + 4, max(0, tag[0] - 4):tag[2] + 4] = False
    return float(y[inner].mean() / max(1.0, y[band].mean())) if inner.any() and band.any() else 0.0


def check_frozen(d):
    res = []
    for a, b, (x0, y0, x1, y1), still, what in FROZEN:
        A = cv2.imread(str(d / f"f_{a}.png")).astype(int)[y0:y1, x0:x1]
        B = cv2.imread(str(d / f"f_{b}.png")).astype(int)[y0:y1, x0:x1]
        diff = np.abs(A - B).max(axis=2)
        # page A's second mark lights between the two frames: its own rect (and the veil's hole) are the only change allowed there
        moved = float((diff > 6).mean())
        ok = (moved < 0.06) if still else (moved > 0.2)
        res.append({"check": "FROZEN", "frame": b, "ok": bool(ok), "changed": round(moved, 4),
                    "what": f"{what}: {100 * moved:.2f}% of the pixels changed ({'want under 6%' if still else 'want over 20%'})"})
    return res


def segments(profile, merge):
    idx = np.nonzero(profile)[0]
    if not len(idx):
        return []
    segs, a, b = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - b > merge:
            segs.append((a, b + 1))
            a = i
        b = i
    segs.append((a, b + 1))
    return segs


def check_rows(d):
    res = []
    for fr, (what, named) in ROWS.items():
        img = cv2.cvtColor(cv2.imread(str(d / f"f_{fr}.png")), cv2.COLOR_BGR2RGB)
        m = img.max(axis=2) > 14
        m[950:, :] = False                                  # the credit's band
        bands = sorted(segments(m.any(axis=1), 12), key=lambda s: s[0])
        bands = [b for b in bands if b[1] - b[0] > 20]
        if not bands:
            res.append({"check": "ROW", "frame": fr, "ok": False, "what": f"{what}: nothing found"})
            continue
        fig = max(bands, key=lambda s: s[1] - s[0])
        figs = segments(m[fig[0]:fig[1]].any(axis=0), 40)
        names = []
        if named:
            below = [b for b in bands if b[0] >= fig[1]]
            if below:
                nb = below[0]
                names = segments(m[nb[0]:nb[1]].any(axis=0), 24)
        gaps = [int(figs[i + 1][0] - figs[i][1]) for i in range(len(figs) - 1)]
        xs = [s[0] for s in figs + names] + [s[1] for s in figs + names]
        centre = (min(xs) + max(xs)) / 2
        ok = len(figs) == 3 and (max(gaps) - min(gaps) <= 2) and abs(centre - 960) <= 4 and (not named or len(names) == 3)
        res.append({"check": "ROW", "frame": fr, "ok": bool(ok), "figures": [list(map(int, s)) for s in figs],
                    "names": [list(map(int, s)) for s in names], "gaps": gaps, "centre": centre,
                    "what": f"{what}: {len(figs)} figures, gaps {gaps} px, visible content centred at {centre:.1f} (names {len(names)})"})
    return res


def sheet(tiles, out):
    if not tiles:
        return
    big = [cv2.resize(t, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST) for _, t in tiles]
    W = min(2400, max(b.shape[1] for b in big))
    rows = []
    for (name, _), b in zip(tiles, big):
        b = b[:, :W]
        pad = np.zeros((b.shape[0] + 40, W, 3), np.uint8)
        pad[40:, :b.shape[1]] = b
        cv2.putText(pad, name, (6, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        rows.append(pad)
    cv2.imwrite(str(out), cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("proof_dir")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    d = Path(a.proof_dir)
    tiles = []
    res = check_pages(d, tiles) + check_pics(d, tiles) + check_rows(d) + check_frozen(d)
    proof = d / "proof.json"
    if proof.exists():
        for r in json.loads(proof.read_text(encoding="utf-8")).get("refusals", []):
            res.append({"check": "REFUSE", "ok": r["ok"], "case": r["which"], "what": f"{r['which']}: {r['error'][:140] or 'RENDERED (guard broken)'}"})
    for r in res:
        print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['check']:7} {('f' + str(r['frame'])) if 'frame' in r else '':6} {r['what']}")
    n_bad = sum(not r["ok"] for r in res)
    print(f"kit3 check: {len(res) - n_bad} ok, {n_bad} failed")
    (d / "check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if a.sheet:
        sheet(tiles, a.sheet)
    sys.exit(1 if n_bad else 0)


if __name__ == "__main__":
    main()
