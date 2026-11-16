"""The framing review for built Shorts (<At> ranges; standard/SHORTS.md asks it of every Short, built or hand-picked): a subject cut at
the frame's edge, a title cut by the crop, letterbox bars all come from framing by guess.
For every picture the Short places with the Shorts kit's Cover (Pic and the Short's own covers; blurred backgrounds left out): the whole
source picture at the start, middle and end of its slot, the 9:16 window it shows there drawn in red (the Cover's place(): the push
s0 -> s1 and the pan fx/fy -> fx1/fy1 over `dur`, never past the picture's edges), the faces YuNet finds in green, a 10% grid, the
window itself as the viewer sees it, and the words said in the slot. Read it row by row: does the window hold what the words name,
whole, in the middle, for the whole slot? Then set fx/fy (fx1/fy1 for a subject that moves, s0/s1 to zoom) in the Short's .tsx and run
this again.

  EDIT tools/motion/frame_review_at.py <id> [--out <dir>] [--rows 7] [--all]
  (--all: also the blurred backgrounds)  -> <out>/frames_<id>_<k>.jpg (default VIDEOS/<id>-*/review/framing/)"""
import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, MODELS, NODE, PUBLIC, VIDEOS, VIDEOS_REPO  # noqa: E402

HERE = Path(__file__).resolve().parent
MOTION_PUB = PUBLIC
YUNET = str(MODELS / "yunet/face_detection_yunet_2023mar.onnx")
FW, FH = 480, 270           # one source frame on the sheet (a 16:9 tile; other shapes fitted inside it)
CW, CH = 152, 270           # the 9:16 window as the viewer sees it


def _font(size, bold):
    names = (("C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf") if bold
             else ("C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"))
    for p in names:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT = _font(15, False)
FONT_B = _font(16, True)


def plays(vid):
    """The Short's pictures and their framing, from audit_at.tsx (the same walker as audit_short.py)."""
    folder = next(VIDEOS_REPO.glob(f"{vid}-*"))
    cfg = tomllib.loads((folder / "video.toml").read_text(encoding="utf-8"))
    comp, src = cfg["video"]["comp"], cfg["video"]["src"]
    pub = Path(cfg.get("render", {}).get("pub", MOTION_PUB))
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    tsx = (HERE / "audit_at.tsx").read_text(encoding="utf-8").replace("__COMP__", comp).replace("__MODULE__", f"../src/{src}/{comp}")
    (out / f"auditat_{comp}.tsx").write_text(tsx, encoding="utf-8")
    esb = HERE / "node_modules/.bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    subprocess.run([str(esb), f"out/auditat_{comp}.tsx", "--bundle", "--platform=node", f"--outfile=out/auditat_{comp}.cjs", "--loader:.json=json",
                    "--log-level=warning"], cwd=HERE, check=True, shell=os.name == "nt")
    rep = out / f"auditat_{comp}.json"
    r = subprocess.run([NODE, f"out/auditat_{comp}.cjs"], cwd=HERE, env={**os.environ, "PLAYS_JSON": str(rep)}, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    data = json.loads(rep.read_text(encoding="utf-8"))
    words = json.loads((HERE / "src" / src / "words.json").read_text(encoding="utf-8"))
    return folder, pub, data["frames"], words


def ease_in_out(x):
    return 0.5 - 0.5 * np.cos(np.pi * x)   # lib's easeInOut is a sine curve: close enough to draw the window


def mono(ts, vs, t):
    """The Cover's mono(): a value through keys, smooth through every key (monotone cubic, Fritsch-Carlson), held outside them."""
    n = len(ts)
    if n == 1 or t <= ts[0]:
        return vs[0]
    if t >= ts[-1]:
        return vs[-1]
    d = [(vs[i + 1] - vs[i]) / (ts[i + 1] - ts[i]) for i in range(n - 1)]
    m = [d[0] if i == 0 else d[n - 2] if i == n - 1 else (0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2) for i in range(n)]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        q = a * a + b * b
        if q > 9:
            m[i], m[i + 1] = 3 / q ** 0.5 * a * d[i], 3 / q ** 0.5 * b * d[i]
    i = 0
    while t > ts[i + 1]:
        i += 1
    h = ts[i + 1] - ts[i]
    u = (t - ts[i]) / h
    return (2 * u**3 - 3 * u**2 + 1) * vs[i] + (u**3 - 2 * u**2 + u) * h * m[i] + (-2 * u**3 + 3 * u**2) * vs[i + 1] + (u**3 - u**2) * h * m[i + 1]


def place(f, t, bw=1080, bh=1920):
    """The Cover's place() in source fractions: the window (x0, y0, x1, y1) of the source the box shows at local time t."""
    t0, dur = f.get("t0") or 0.0, f.get("dur") or 3.0
    p = ease_in_out(min(1.0, max(0.0, (t - t0) / dur)))
    s0 = f.get("s0") if f.get("s0") is not None else 1.0
    s1 = f.get("s1") if f.get("s1") is not None else s0
    s = s0 + (s1 - s0) * p
    fx0 = f.get("fx") if f.get("fx") is not None else 0.5
    fy0 = f.get("fy") if f.get("fy") is not None else 0.5
    fx = fx0 + ((f.get("fx1") if f.get("fx1") is not None else fx0) - fx0) * p
    fy = fy0 + ((f.get("fy1") if f.get("fy1") is not None else fy0) - fy0) * p
    pk = f.get("path")
    if pk:
        ts = [k[0] for k in pk]
        fx, fy = mono(ts, [k[1] for k in pk], t), mono(ts, [k[2] for k in pk], t)
        if all(len(k) > 3 for k in pk):
            s = mono(ts, [k[3] for k in pk], t)
    box = f.get("box") or {"w": bw, "h": bh}
    W, H = box["w"], box["h"]
    k = max(W / f["iw"], H / f["ih"]) * s
    dw, dh = f["iw"] * k, f["ih"] * k
    left = min(0.0, max(W - dw, W / 2 - fx * dw))
    top = min(0.0, max(H - dh, H / 2 - fy * dh))
    return (-left / dw, -top / dh, (-left + W) / dw, (-top + H) / dh), s


def source(pub, f, t):
    """The source picture at local time t, RGB at up to 1280 px wide."""
    p = pub / f["src"]
    if not p.exists():
        p = MOTION_PUB / f["src"]
    if f["video"]:
        at = f["from"] + t * (f.get("rate") or 1)
        raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, at):.3f}", "-i", str(p), "-frames:v", "1", "-vf", "scale=1280:-2",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if not raw:
            return Image.new("RGB", (1280, 720), (160, 0, 0))
        return Image.open(__import__("io").BytesIO(raw)).convert("RGB")
    im = Image.open(p).convert("RGB")
    if im.width > 1280:
        im = im.resize((1280, round(im.height * 1280 / im.width)))
    return im


_det = {}


def faces(im):
    w, h = im.size
    if (w, h) not in _det:
        _det[(w, h)] = cv2.FaceDetectorYN.create(YUNET, "", (w, h), 0.6, 0.3, 5000)
    arr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    _, found = _det[(w, h)].detect(arr)
    return [] if found is None else [(x / w, y / h, (x + fw) / w, (y + fh) / h) for x, y, fw, fh in found[:, :4]]


def tile(im, win, fc):
    """The whole source fitted into FW x FH, the window in red, faces in green, a 10% grid."""
    k = min(FW / im.width, FH / im.height)
    tw, th = int(im.width * k), int(im.height * k)
    ox, oy = (FW - tw) // 2, (FH - th) // 2
    out = Image.new("RGB", (FW, FH), (40, 40, 46))
    out.paste(im.resize((tw, th)), (ox, oy))
    d = ImageDraw.Draw(out)
    for i in range(1, 10):
        d.line([(ox + tw * i / 10, oy), (ox + tw * i / 10, oy + th)], fill=(255, 255, 255, 60), width=1)
        d.line([(ox, oy + th * i / 10), (ox + tw, oy + th * i / 10)], fill=(255, 255, 255, 60), width=1)
    for x0, y0, x1, y1 in fc:
        d.rectangle([ox + x0 * tw, oy + y0 * th, ox + x1 * tw, oy + y1 * th], outline=(40, 255, 90), width=2)
    x0, y0, x1, y1 = win
    d.rectangle([ox + x0 * tw, oy + y0 * th, ox + x1 * tw, oy + y1 * th], outline=(255, 40, 40), width=3)
    return out


def crop(im, win):
    x0, y0, x1, y1 = win
    c = im.crop((round(x0 * im.width), round(y0 * im.height), round(x1 * im.width), round(y1 * im.height)))
    return c.resize((CW, CH))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--out")
    ap.add_argument("--rows", type=int, default=7)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--cols", type=int, default=3, help="source frames per shot across its slot (more to place a path key by key)")
    ap.add_argument("--only", help="shot numbers as the default sheet numbers them, e.g. 12,25")
    ap.add_argument("--tag", default="", help="added to the sheet names")
    a = ap.parse_args()
    folder, pub, frames, words = plays(a.id)
    out = Path(a.out) if a.out else VIDEOS / folder.name / "review" / "framing"
    out.mkdir(parents=True, exist_ok=True)
    seen, rows = set(), []
    for f in sorted(frames, key=lambda f: f["at"]):
        if "blur" in (f.get("filter") or "") and not a.all:
            continue
        key = (round(f["at"], 3), f["src"], round(f["from"], 3))
        if key in seen or f["len"] <= 0:
            continue
        seen.add(key)
        f["n"] = len(rows) + 1
        rows.append(f)
    if a.only:
        keep = {int(x) for x in a.only.split(",")}
        rows = [f for f in rows if f["n"] in keep]
    C = max(1, a.cols)
    RW, RH = C * FW + (C - 1) * 10 + CW + 40, FH + 52
    sheets = []
    for k0 in range(0, len(rows), a.rows):
        part = rows[k0:k0 + a.rows]
        sheet = Image.new("RGB", (RW, RH * len(part)), (18, 18, 22))
        d = ImageDraw.Draw(sheet)
        for r, f in enumerate(part):
            n = f["n"]
            y = r * RH
            said = " ".join(wd["w"] for wd in words if wd["start"] < f["at"] + f["len"] and wd["end"] > f["at"])
            name = Path(f["src"]).name
            mv = f"fx {f.get('fx', 0.5)}" + (f"->{f['fx1']}" if f.get("fx1") is not None else "") + f"  fy {f.get('fy', 0.5)}" + \
                 (f"->{f['fy1']}" if f.get("fy1") is not None else "") + f"  s {f.get('s0', 1)}->{f.get('s1', f.get('s0', 1))}" + \
                 (f"  from {f['from']:.2f}" if f["video"] else "  still") + \
                 (("  path " + " ".join("[" + ",".join(f"{v:g}" for v in k) + "]" for k in f["path"])) if f.get("path") else "")
            d.text((8, y + 6), f"{n}.  {f['at']:.2f}-{f['at'] + f['len']:.2f} s  {name}  ({f['iw']}x{f['ih']})   {mv}", font=FONT_B, fill=(255, 220, 90))
            d.text((8, y + 27), f"\u201c{said}\u201d"[:230], font=FONT, fill=(225, 225, 225))
            mid = None
            end = max(0.0, f["len"] - 1 / 60)
            for c in range(C):
                t = end * c / (C - 1) if C > 1 else 0.0
                im = source(pub, f, t)
                win, _ = place(f, t)
                sheet.paste(tile(im, win, faces(im)), (c * FW + c * 10, y + 50))
                d.text((c * FW + c * 10 + 4, y + 52), f"+{t:.2f}", font=FONT_B, fill=(255, 255, 120))
                if c == C // 2:
                    mid = (im, win)
            sheet.paste(crop(*mid), (C * FW + (C - 1) * 10 + 20, y + 50))
        p = out / f"frames_{a.id}{a.tag}_{k0 // a.rows + 1}.jpg"
        sheet.save(p, quality=88)
        sheets.append(p)
    print(f"{len(rows)} framed pictures -> " + ", ".join(str(s) for s in sheets))


if __name__ == "__main__":
    main()
