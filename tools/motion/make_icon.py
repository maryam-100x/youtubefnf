"""A profile icon (a round face picture: a person on a map, a chart, a lineup) cut from a REAL frame of the subject (footage, a
screenshot, a photo), its face measured, never guessed. Artwork reads as cheap next to the real thing, and a crop placed by hand puts the
face off the circle's centre (chin on the edge, or the face filling the whole circle); measured, it sits where an avatar's face sits.

  EDIT tools/motion/make_icon.py make <out.png> --src <image | video> [--t <seconds>] [--pick biggest|<n>|x,y] [--size 512] [--share 0.56]
      the frame (a video at --t, decoded at its full resolution; a still as it is), its faces found with YuNet, one picked (the biggest,
      the n-th by size, or the one nearest x,y in source px), and a square cropped so the face box's centre is the square's centre and
      its height `share` of the side; written as <out.png> (square RGB: the component draws the circle) beside <out>.icon.json, the
      sidecar kit3's `icons` require: the source and its kind, the crop, the face box MEASURED AGAIN ON THE WRITTEN ICON, its score.
      Refused: an artwork source (any folder named *artwork*, cover art, postcards, wallpapers), a frame without a face, a crop that
      would leave the source, a face that lands off the icon's centre by more than OFF_TOL of the side or outside SHARE_RANGE.
  EDIT tools/motion/make_icon.py check <icon.png> [...] [--json]
      the gate's reading of an icon (icon_verdict; qa_centred.py runs it): its sidecar, the face found on the icon itself, off-centre
      and size. Exit 1 on a fault (--json: one list on stdout instead).
  EDIT tools/motion/make_icon.py sheet <out.jpg> --src <file>[@t] [...] [--names a,b,...]
      candidates side by side as they would show (in their circle, at 264 px), each with its face offset and size, to pick from.

The face's centre is YuNet's box centre (brows to chin, ear to ear): centred on it, the eyes sit a little above the circle's middle and
the hair fills the top, as an avatar is framed. Editing venv (OpenCV 5 with YuNet, numpy, Pillow); the model file is
MODELS/face_detection_yunet_2023mar.onnx (the setup downloads it)."""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import FFMPEG, MODELS  # noqa: E402
from brand import BRAND_RGB  # noqa: E402

YUNET = str(MODELS / "face_detection_yunet_2023mar.onnx")
VERSION = 1
SIZE = 512            # the icon's side in px (kit3 draws it 132 px across on the 1920 frame: 176 px at 1440p, so 512 is ~3x)
SHARE = 0.56          # the face box's height as a share of the side: the face big enough to know at 132 px, the hair inside
SHARE_RANGE = (0.42, 0.72)
OFF_TOL = 0.04        # the face's centre may sit this share of the side off the circle's centre (20 px of 512; 5 px of 132 on screen)
ARTWORK = re.compile(r"(artwork|cover[_ ]?art|postcard|wallpaper)", re.I)


def is_artwork(path):
    return bool(ARTWORK.search(str(Path(path)).replace("\\", "/")))


def source_kind(path):
    p = str(path).replace("\\", "/").lower()
    if is_artwork(p):
        return "artwork"
    if p.endswith((".mp4", ".mkv", ".mov", ".webm")):
        return "clip" if "/clips/" in p else "footage" if "/videos/" in p else "video"
    return "screenshot" if "screenshot" in p else "still"


def read_frame(src, t=None):
    """BGR frame of a still, or of a video at t seconds (full resolution, one frame)"""
    src = str(src)
    if t is None and not src.lower().endswith((".mp4", ".mkv", ".mov", ".webm")):
        im = np.array(Image.open(src).convert("RGB"))[:, :, ::-1]
        return np.ascontiguousarray(im)
    r = subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-ss", f"{t or 0:.3f}", "-i", src, "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True, check=True)
    im = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
    if im is None:
        raise SystemExit(f"make_icon: no frame from {src} at {t}")
    return im


def faces(img, min_frac=0.03):
    """YuNet's faces, biggest first: [x, y, w, h, 10 landmark values, score], on the whole picture (detected at <= 1280 px wide, mapped back)"""
    h, w = img.shape[:2]
    k = min(1.0, 1280 / w)
    small = cv2.resize(img, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA) if k < 1 else img
    sh, sw = small.shape[:2]
    out = None
    for thr in (0.7, 0.5, 0.35):
        det = cv2.FaceDetectorYN.create(YUNET, "", (sw, sh), thr, 0.3, 50)
        _, f = det.detect(small)
        if f is not None and len(f):
            out = f
            break
    if out is None:
        return []
    out = [np.concatenate([f[:14] / k, f[14:]]) for f in out]
    out = [f for f in out if f[3] >= min_frac * h]
    return sorted(out, key=lambda f: -f[3])


def pick_face(fs, pick):
    if not fs:
        return None
    if pick in (None, "biggest"):
        return fs[0]
    if re.fullmatch(r"\d+", str(pick)):
        return fs[int(pick)] if int(pick) < len(fs) else None
    x, y = (float(v) for v in str(pick).split(","))
    return min(fs, key=lambda f: (f[0] + f[2] / 2 - x) ** 2 + (f[1] + f[3] / 2 - y) ** 2)


def crop_square(img, f, share=SHARE):
    """the square around the face box's centre, the box's height `share` of its side: (x0, y0, side) in source px, or None past the edge"""
    h, w = img.shape[:2]
    cx, cy = f[0] + f[2] / 2, f[1] + f[3] / 2
    side = f[3] / share
    x0, y0 = cx - side / 2, cy - side / 2
    if x0 < 0 or y0 < 0 or x0 + side > w or y0 + side > h:
        return None
    return x0, y0, side


def cut(img, sq, size=SIZE):
    x0, y0, side = sq
    k = size / side
    M = np.float32([[k, 0, -x0 * k], [0, k, -y0 * k]])
    return cv2.warpAffine(img, M, (size, size), flags=cv2.INTER_LANCZOS4 if k > 1 else cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)


def measure_icon(icon_bgr):
    """the face on the icon itself: (dx, dy) of its box centre from the icon's centre and its height, as shares of the side; None: no face"""
    s = icon_bgr.shape[0]
    fs = faces(icon_bgr, min_frac=0.2)
    if not fs:
        return None
    f = fs[0]
    return {"box": [round(float(v), 1) for v in f[:4]], "score": round(float(f[-1]), 3),
            "dx": round(float((f[0] + f[2] / 2 - s / 2) / s), 4), "dy": round(float((f[1] + f[3] / 2 - s / 2) / s), 4),
            "share": round(float(f[3] / s), 4)}


def faults(m, side_note=""):
    if m is None:
        return ["no face found on the icon (YuNet)"]
    out = []
    if abs(m["dx"]) > OFF_TOL or abs(m["dy"]) > OFF_TOL:
        out.append(f"its face sits {m['dx'] * 100:+.1f}% / {m['dy'] * 100:+.1f}% of the circle off its centre (over {OFF_TOL * 100:.0f}%){side_note}")
    if not SHARE_RANGE[0] <= m["share"] <= SHARE_RANGE[1]:
        out.append(f"its face is {m['share'] * 100:.0f}% of the circle's height (outside {SHARE_RANGE[0] * 100:.0f}-{SHARE_RANGE[1] * 100:.0f}%)")
    return out


def cmd_make(a):
    if is_artwork(a.src):
        raise SystemExit(f"make_icon: {a.src} is artwork: a profile icon is cut from a real frame of the subject (the source's "
                         "footage, a clip, a screenshot, a photo)")
    img = read_frame(a.src, a.t)
    fs = faces(img)
    f = pick_face(fs, a.pick)
    if f is None:
        raise SystemExit(f"make_icon: no face in {a.src}{f' at {a.t} s' if a.t is not None else ''} (pick {a.pick})")
    sq = crop_square(img, f, a.share)
    if sq is None:
        raise SystemExit(f"make_icon: the face at {f[:4].round().tolist()} is too near the frame's edge for a square of "
                         f"{f[3] / a.share:.0f} px (share {a.share}): another frame, or a larger --share")
    icon = cut(img, sq, a.size)
    m = measure_icon(icon)
    # one refining pass: the detector's box on the icon (what the gate reads) differs from its box on the whole frame by a few %; the
    # crop moves by that difference when the source has room, and the closer of the two is kept
    if m is not None:
        x0, y0, side = sq
        sq2 = (x0 + m["dx"] * side, y0 + m["dy"] * side, side)
        h, w = img.shape[:2]
        if sq2[0] >= 0 and sq2[1] >= 0 and sq2[0] + side <= w and sq2[1] + side <= h:
            icon2 = cut(img, sq2, a.size)
            m2 = measure_icon(icon2)
            if m2 is not None and abs(m2["dx"]) + abs(m2["dy"]) < abs(m["dx"]) + abs(m["dy"]):
                sq, icon, m = sq2, icon2, m2
    bad = faults(m)
    if bad:
        raise SystemExit(f"make_icon: {a.out}: " + "; ".join(bad))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(icon[:, :, ::-1]).save(out, optimize=True)
    side = {"tool": "tools/motion/make_icon.py", "version": VERSION, "made": time.strftime("%Y-%m-%d %H:%M"),
            "source": {"file": str(a.src).replace("\\", "/"), "t": a.t, "kind": source_kind(a.src)}, "artwork": False,
            "face_in_source": [round(float(v), 1) for v in f[:4]], "score_in_source": round(float(f[-1]), 3),
            "crop": [round(float(v), 1) for v in sq], "size": a.size, "share": a.share, "face": m}
    Path(str(out)[:-4] + ".icon.json").write_text(json.dumps(side, indent=1) + "\n", encoding="utf-8")
    print(f"{out}: {source_kind(a.src)} {Path(a.src).name}{f' @ {a.t} s' if a.t is not None else ''}; face {m['share'] * 100:.0f}% of the "
          f"circle, {m['dx'] * 100:+.1f}% / {m['dy'] * 100:+.1f}% off its centre (score {m['score']})")


def icon_verdict(path):
    """(faults, the icon's measured face, its sidecar or None): what the gate (qa_centred.py) and kit3's icons hold an icon to"""
    p = Path(path)
    side_p = Path(str(p)[:-4] + ".icon.json")
    side = json.loads(side_p.read_text(encoding="utf-8")) if side_p.exists() else None
    img = np.array(Image.open(p).convert("RGB"))[:, :, ::-1]
    img = np.ascontiguousarray(img)
    if img.shape[0] != img.shape[1]:
        s = min(img.shape[:2])
        img = img[(img.shape[0] - s) // 2:(img.shape[0] - s) // 2 + s, (img.shape[1] - s) // 2:(img.shape[1] - s) // 2 + s]
    m = measure_icon(img)
    bad = faults(m)
    if side is None:
        bad.append("no sidecar (<name>.icon.json): not made by make_icon.py from a real frame of the subject")
    elif side.get("artwork") or is_artwork(side.get("source", {}).get("file", "")):
        bad.append(f"cut from artwork ({side.get('source', {}).get('file')}): an icon is cut from a real frame of the subject")
    return bad, m, side


def cmd_check(a):
    if a.json:
        out = []
        for p in a.icons:
            bad, m, side = icon_verdict(p)
            out.append({"path": p, "bad": bad, "face": m, "source": (side or {}).get("source")})
        print(json.dumps(out))
        return
    n_bad = 0
    for p in a.icons:
        bad, m, side = icon_verdict(p)
        src = side["source"]["file"] if side else "-"
        mm = f"face {m['share'] * 100:.0f}%, {m['dx'] * 100:+.1f}% / {m['dy'] * 100:+.1f}%" if m else "no face"
        print(f"{'BAD ' if bad else 'ok  '} {p}: {mm}; source {src}" + (f"\n      " + "\n      ".join(bad) if bad else ""))
        n_bad += bool(bad)
    sys.exit(1 if n_bad else 0)


def cmd_sheet(a):
    names = a.names.split(",") if a.names else []
    cells = []
    for i, s in enumerate(a.src):
        f_, _, t = s.partition("@")
        t = float(t) if t else None
        lab = names[i] if i < len(names) else Path(f_).stem + (f"@{t}" if t is not None else "")
        img = read_frame(f_, t)
        fs = faces(img)
        for j, f in enumerate(fs[:a.per]):
            sq = crop_square(img, f, a.share)
            if sq is None:
                continue
            icon = cut(img, sq, 264)
            m = measure_icon(icon)
            cells.append((icon, f"{lab}#{j}", m, is_artwork(f_)))
    if not cells:
        raise SystemExit("make_icon sheet: no faces")
    cols = min(6, len(cells))
    rows = (len(cells) + cols - 1) // cols
    W, H = 300, 330
    sheet = Image.new("RGB", (cols * W, rows * H), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    mask = Image.new("L", (264, 264), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 263, 263), fill=255)
    for k, (icon, lab, m, art) in enumerate(cells):
        x, y = (k % cols) * W + 18, (k // cols) * H + 10
        sheet.paste(Image.fromarray(icon[:, :, ::-1]), (x, y), mask)
        d.ellipse((x, y, x + 263, y + 263), outline=(244, 239, 230), width=3)
        d.line((x + 132 - 6, y + 132, x + 132 + 6, y + 132), fill=BRAND_RGB)
        d.line((x + 132, y + 132 - 6, x + 132, y + 132 + 6), fill=BRAND_RGB)
        mm = f"{m['share'] * 100:.0f}% {m['dx'] * 100:+.1f}/{m['dy'] * 100:+.1f}" if m else "no face on icon"
        d.text((x, y + 270), lab[:40], fill=(255, 120, 120) if art else (230, 230, 230), font=font)
        d.text((x, y + 288), mm, fill=(200, 200, 200), font=font)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out, quality=90)
    print(f"{a.out}: {len(cells)} candidates")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("out")
    m.add_argument("--src", required=True)
    m.add_argument("--t", type=float)
    m.add_argument("--pick", default="biggest")
    m.add_argument("--size", type=int, default=SIZE)
    m.add_argument("--share", type=float, default=SHARE)
    c = sub.add_parser("check")
    c.add_argument("icons", nargs="+")
    c.add_argument("--json", action="store_true", help="one JSON list on stdout (qa_centred.py reads it)")
    s = sub.add_parser("sheet")
    s.add_argument("out")
    s.add_argument("--src", nargs="+", required=True)
    s.add_argument("--names")
    s.add_argument("--per", type=int, default=2)
    s.add_argument("--share", type=float, default=SHARE)
    a = ap.parse_args()
    {"make": cmd_make, "check": cmd_check, "sheet": cmd_sheet}[a.cmd](a)


if __name__ == "__main__":
    main()
