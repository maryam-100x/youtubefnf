"""spotmask.py: a picture thing's own silhouette, for kit3's spot mark.

Why: a box drawn round a thing reads as clutter; the spot mark draws no shape round it: the rest of the picture dims and greys, and
the thing's OWN outline is lit in the brand colour. That outline is measured from the picture's pixels, never drawn by hand:
automark.py's refine (the same separation from the local background its boxes come from) run on the mark's box, so every part of the
thing inside it (a flock of four gulls) is in the silhouette.

  EDIT tools/motion/spotmask.py <image> <x,y,w,h> [<x,y,w,h> ...] [--what gull --count 4] [--method refine|dark [--thr 10]] [--proof out.jpg]
      writes <image dir>/sil/<stem>__<x>_<y>_<w>_<h>.png: the box padded by p = ceil(max(w, h) / 2) on every side (transparent past
      the picture's edge), white, the thing's pixels as alpha. kit3 (marks.SpotRim) places it at [x - p, y - p] in image px and draws
      the rim and the glow from its alpha in screen px, so one mask serves every scale the picture is shown at.
      Exit 1 when nothing in a box stands out from its background (no silhouette: the mark can't be drawn this way)."""
import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from automark import load_image, refine  # noqa: E402
from brand import BRAND_BGR  # noqa: E402


def pad_of(w, h):
    return int(math.ceil(max(w, h) / 2))


def _sel(img, xyxy, rivals=()):
    """refine's own pixels for one find, as a full-size bool mask (or None)"""
    dbg = {}
    r = refine(img, xyxy, rivals, debug=dbg)
    if r is None or "maps" not in dbg:
        return None
    C, _d, _lab, sel, _inD, _inE = dbg["maps"]
    full = np.zeros(img.shape[:2], bool)
    full[C[1]:C[3], C[0]:C[2]] = sel
    return full


def _dark(img, xyxy, thr):
    """a dark thing on a smooth sky: darker than its blurred surroundings by `thr` grey levels, parts of 6 px or more. A small,
    compressed picture (a 1080-px still) keeps its thin wings this way, where refine's growth follows the JPEG's halo"""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in xyxy]
    s = max(x1 - x0, y1 - y0)
    pad = int(max(8, 0.5 * s))
    a0, b0, a1, b1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    g = cv2.cvtColor(np.ascontiguousarray(img[b0:b1, a0:a1]), cv2.COLOR_RGB2GRAY).astype(np.float32)
    bg = cv2.GaussianBlur(g, (0, 0), max(6.0, s / 6))
    m = ((bg - g) > thr).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m, bool)
    for i in range(1, n):
        if st[i, 4] >= 6:
            keep |= lab == i
    full = np.zeros(img.shape[:2], bool)
    full[b0:b1, a0:a1] = keep
    return full


def silhouette(img, box, image=None, what=None, count=None, method="refine", thr=10.0):
    """the thing's pixels inside `box` [x, y, w, h] as a full-size bool mask, or None.
    With `what` (and `count`): each of automark's finds inside the box measured on its own (its detector box, the other finds as
    rivals) and joined: four 5-px gulls beside a tree branch are four gulls, not the branch (refine on the whole box takes the
    biggest part in it as the thing). Without: the box itself (one thing, or things alike and alone in it).
    `method` 'refine' (automark.py's separation) or 'dark' (darker than the blurred sky by `thr`: _dark)"""
    x, y, w, h = box
    measure = (lambda d, rivals: _sel(img, d, rivals)) if method == "refine" else (lambda d, rivals: _dark(img, d, thr))
    if what:
        from automark import find
        p = pad_of(w, h)
        region = f"{max(0, x - p)},{max(0, y - p)},{w + 2 * p},{h + 2 * p}"
        picks, _union, _info = find(image, what, count=count, region=region, log=lambda s: None)
        inside = [q for q in picks if q["px"][0] >= x - 4 and q["px"][1] >= y - 4 and q["px"][2] <= x + w + 4 and q["px"][3] <= y + h + 4]
        if not inside:
            return None
        full = np.zeros(img.shape[:2], bool)
        dets = [[d[0], d[1], d[0] + d[2], d[1] + d[3]] for d in (q["detector"] for q in inside)]
        for i, d in enumerate(dets):
            m = measure(d, [o for j, o in enumerate(dets) if j != i])
            if m is not None:
                full |= m
        # each find's pixels kept inside its own refined box (+2 px): a neighbour's reach never joins it
        keep = np.zeros_like(full)
        for q in inside:
            a0, b0, a1, b1 = q["px"]
            keep[max(0, b0 - 2):b1 + 2, max(0, a0 - 2):a1 + 2] = True
        return full & keep
    m = measure([x, y, x + w, y + h], [])
    if m is not None and method == "dark":
        m &= _boxmask(img.shape, [x - 2, y - 2, w + 4, h + 4])     # the sky's other dark things stay out (a branch past the box)
    return m


def _boxmask(shape, b):
    k = np.zeros(shape[:2], bool)
    k[max(0, b[1]):max(0, b[1] + b[3]), max(0, b[0]):max(0, b[0] + b[2])] = True
    return k


def write_mask(img, box, full, out):
    x, y, w, h = box
    p = pad_of(w, h)
    H, W = img.shape[:2]
    a = np.zeros((h + 2 * p, w + 2 * p), np.uint8)
    sx0, sy0, sx1, sy1 = max(0, x - p), max(0, y - p), min(W, x + w + p), min(H, y + h + p)
    a[sy0 - (y - p):sy1 - (y - p), sx0 - (x - p):sx1 - (x - p)] = full[sy0:sy1, sx0:sx1].astype(np.uint8) * 255
    a = cv2.GaussianBlur(a, (0, 0), 0.5)          # a smooth edge (the measured pixels are whole pixels)
    rgba = np.dstack([np.full_like(a, 255)] * 3 + [a])
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), rgba)
    return p


def proof(img, box, full, path):
    """the box's crop at 100% (magnified when small) beside the silhouette lit on it"""
    x, y, w, h = box
    p = pad_of(w, h)
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(0, x - p), max(0, y - p), min(W, x + w + p), min(H, y + h + p)
    crop = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_RGB2BGR)
    lit = crop.copy()
    m = full[y0:y1, x0:x1]
    lit[m] = BRAND_BGR
    k = max(1, int(round(360 / max(1, crop.shape[0]))))
    both = np.hstack([crop, np.full((crop.shape[0], 6, 3), 255, np.uint8), lit])
    both = cv2.resize(both, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(path), both, [cv2.IMWRITE_JPEG_QUALITY, 92])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("image")
    ap.add_argument("boxes", nargs="+", help="x,y,w,h (image px): the mark's box")
    ap.add_argument("--what", help='the thing, as automark.py names it ("gull"): each find in the box refined on its own')
    ap.add_argument("--count", type=int, help="how many of the thing (with --what)")
    ap.add_argument("--method", choices=["refine", "dark"], default="refine", help="refine: automark.py's separation; dark: darker than the blurred sky (small, compressed pictures)")
    ap.add_argument("--thr", type=float, default=10.0, help="--method dark: grey levels darker than the sky")
    ap.add_argument("--proof", help="a proof sheet per box: <proof stem>_<n>.jpg")
    a = ap.parse_args()
    img = load_image(a.image)
    src = Path(a.image)
    bad = 0
    for i, b in enumerate(a.boxes):
        box = [int(round(float(v))) for v in b.split(",")]
        full = silhouette(img, box, a.image, a.what, a.count, a.method, a.thr)
        if full is None or not full.any():
            print(f"NO SILHOUETTE {src.name} {box}: nothing in the box stands out from its background", file=sys.stderr)
            bad += 1
            continue
        out = src.parent / "sil" / f"{src.stem}__{box[0]}_{box[1]}_{box[2]}_{box[3]}.png"
        p = write_mask(img, box, full, out)
        ys, xs = np.nonzero(full)
        print(f"{out}  pad {p}  pixels {int(full.sum())}  extent [{xs.min()}, {ys.min()}, {xs.max() - xs.min() + 1}, {ys.max() - ys.min() + 1}]")
        if a.proof:
            proof(img, box, full, Path(f"{a.proof}_{i}.jpg"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
