"""A library of close-up faces from source footage (the official videos and stills of the video's subject), for cut-outs, face
picks in the edit and thumbnails: the biggest, sharpest face of every shot, found once and named, so a picture of one person's face
is a lookup instead of a scrub through hours of footage. Faces are real frames of the source, never generated.

  EDIT tools/qa/face_library.py scan <video> [--every 10] [--min-h 0.14]
      decodes the whole video (ffmpeg, scaled to 1280x720), runs YuNet on every --every-th frame, keeps the frames whose biggest face is
      at least --min-h of the frame's height, splits them into shots (a jump in the picture) and keeps each shot's best frame (face
      height x sharpness), then grabs those frames at full resolution: <LIB>/<video>/<video>_<seconds>.jpg, rows in <LIB>/faces.csv.
  EDIT tools/qa/face_library.py stills <dir> [--min-h 0.10]
      the same for still images (official photos, a press set); the images stay where they are.
  EDIT tools/qa/face_library.py label [--people DIR] [--min-sim 0.363]
      names each face with SFace (OpenCV Zoo) against references: every face in the people folder's images, one sub-folder per
      person (FOOTAGE/people/<name>/*.jpg; pair folders like "Ana and Ben" are skipped); a face closer to no one than --min-sim
      (0.363, OpenCV Zoo's threshold) stays "?" (its sheet: unknown_<n>.jpg).
  EDIT tools/qa/face_library.py sheets
      contact sheets, one per name, biggest faces first: <LIB>/sheets/<name>_<n>.jpg (the file name under each cell).

Run with the editing venv (OpenCV, numpy, Pillow). <LIB> = MEDIA/faces; the YuNet and SFace models in MODELS/yunet and MODELS/sface
(fetched at setup)."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, FOOTAGE, MEDIA, MODELS  # noqa: E402

LIB = MEDIA / "faces"
CSV = LIB / "faces.csv"
YUNET = str(MODELS / "yunet" / "face_detection_yunet_2023mar.onnx")
SFACE = str(MODELS / "sface" / "face_recognition_sface_2021dec.onnx")
PEOPLE = FOOTAGE / "people"
FIELDS = ["file", "source", "t", "w", "h", "fx", "fy", "fw", "fh", "face_h", "sharp", "score", "name", "sim"]
SW, SH = 1280, 720


def probe(video):
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip().split(",")
    num, den = out[2].split("/")
    return int(out[0]), int(out[1]), float(num) / float(den)


def biggest_face(det, img):
    det.setInputSize((img.shape[1], img.shape[0]))
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        return None
    return max(faces, key=lambda f: f[3])


def sharpness(img, f):
    x, y, w, h = (int(round(v)) for v in f[:4])
    x0, y0 = max(0, x), max(0, y)
    crop = img[y0:y + h, x0:x + w]
    if crop.size == 0:
        return 0.0
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, (128, int(128 * g.shape[0] / max(1, g.shape[1]))))
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def read_rows():
    if not CSV.exists():
        return []
    with CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_rows(rows):
    LIB.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def cmd_scan(a):
    video = Path(a.video)
    W, H, fps = probe(video)
    det = cv2.FaceDetectorYN.create(YUNET, "", (SW, SH), 0.75)
    cmd = [FFMPEG, "-v", "error", "-i", str(video), "-vf", f"select='not(mod(n\\,{a.every}))',scale={SW}:{SH}", "-fps_mode", "passthrough",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=SW * SH * 3 * 4)
    n_bytes = SW * SH * 3
    k, shot, prev, cands = 0, 0, None, []
    while True:
        buf = proc.stdout.read(n_bytes)
        if len(buf) < n_bytes:
            break
        img = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
        small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (64, 36)).astype(np.float32)
        if prev is not None and np.abs(small - prev).mean() > 18:
            shot += 1
        prev = small
        t = k * a.every / fps
        f = biggest_face(det, img)
        if f is not None and f[3] / SH >= a.min_h:
            cands.append({"t": t, "shot": shot, "f": f, "sharp": sharpness(img, f)})
        k += 1
        if k % 500 == 0:
            print(f"  {video.stem}: {t:7.1f} s, {len(cands)} close frames", flush=True)
    proc.wait()
    if not cands:
        print("no close-ups")
        return
    med = float(np.median([c["sharp"] for c in cands])) or 1.0
    best = {}
    for c in cands:
        c["score"] = c["f"][3] / SH * min(c["sharp"] / med, 2.0)
        if c["shot"] not in best or c["score"] > best[c["shot"]]["score"]:
            best[c["shot"]] = c
    out_dir = LIB / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [r for r in read_rows() if r["source"] != str(video)]
    sx, sy = W / SW, H / SH
    for c in sorted(best.values(), key=lambda c: c["t"]):
        name = out_dir / f"{video.stem}_{c['t']:07.2f}.jpg"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{c['t']:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(name)], check=True)
        x, y, w, h = c["f"][:4]
        rows.append({"file": str(name), "source": str(video), "t": f"{c['t']:.2f}", "w": W, "h": H, "fx": round(x * sx), "fy": round(y * sy),
                     "fw": round(w * sx), "fh": round(h * sy), "face_h": f"{h / SH:.3f}", "sharp": f"{c['sharp']:.0f}",
                     "score": f"{c['score']:.3f}", "name": "", "sim": ""})
    write_rows(rows)
    print(f"{video.stem}: {k} frames looked at, {len(cands)} close, {len(best)} shots kept -> {out_dir}")


def cmd_stills(a):
    det = cv2.FaceDetectorYN.create(YUNET, "", (SW, SH), 0.75)
    files = sorted(p for p in Path(a.dir).rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    done = {r["file"] for r in read_rows()}
    rows = read_rows()
    for p in files:
        if str(p) in done:
            continue
        im = np.asarray(Image.open(p).convert("RGB"))[..., ::-1]
        H, W = im.shape[:2]
        k = SW / W
        img = cv2.resize(im, (SW, round(H * k)))
        f = biggest_face(det, img)
        if f is None or f[3] / img.shape[0] < a.min_h:
            continue
        x, y, w, h = (v / k for v in f[:4])
        rows.append({"file": str(p), "source": "still", "t": "", "w": W, "h": H, "fx": round(x), "fy": round(y), "fw": round(w), "fh": round(h),
                     "face_h": f"{f[3] / img.shape[0]:.3f}", "sharp": f"{sharpness(img, f):.0f}", "score": "", "name": "", "sim": ""})
    write_rows(rows)
    print(f"{len(rows)} rows in {CSV}")


def embed(rec, det, path, box=None):
    im = np.asarray(Image.open(path).convert("RGB"))[..., ::-1].copy()
    H, W = im.shape[:2]
    k = min(1.0, 1600 / W)
    img = cv2.resize(im, (round(W * k), round(H * k))) if k < 1 else im
    det.setInputSize((img.shape[1], img.shape[0]))
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        return None
    if box is not None:  # the face this row is about: the detection nearest its box
        cx, cy = (box[0] + box[2] / 2) * k, (box[1] + box[3] / 2) * k
        f = min(faces, key=lambda f: (f[0] + f[2] / 2 - cx) ** 2 + (f[1] + f[3] / 2 - cy) ** 2)
    else:
        f = max(faces, key=lambda f: f[3])
    return rec.feature(rec.alignCrop(img, f)).flatten()


def cmd_label(a):
    det = cv2.FaceDetectorYN.create(YUNET, "", (SW, SH), 0.75)
    rec = cv2.FaceRecognizerSF.create(SFACE, "")
    refs = {}
    people = Path(a.people)
    if not people.is_dir():
        sys.exit(f"no people folder at {people}: one sub-folder per person, holding pictures of that person's face")
    # one folder per person; a pair folder ("Ana and Ben") is no identity: its faces are named like any other face
    for d in sorted(p for p in people.iterdir() if p.is_dir() and " and " not in p.name):
        feats = [e for e in (embed(rec, det, p) for p in sorted(d.glob("*.jpg"))) if e is not None]
        if feats:
            refs[d.name] = feats
            print(f"  {d.name}: {len(feats)} reference faces")
    if not refs:
        sys.exit(f"no reference faces found in {people}")
    rows = read_rows()
    for r in rows:
        e = embed(rec, det, r["file"], (float(r["fx"]), float(r["fy"]), float(r["fw"]), float(r["fh"])))
        if e is None:
            r["name"], r["sim"] = "?", ""
            continue
        sims = {n: max(rec.match(e.reshape(1, -1), f.reshape(1, -1), cv2.FaceRecognizerSF_FR_COSINE) for f in fs) for n, fs in refs.items()}
        n, s = max(sims.items(), key=lambda kv: kv[1])
        r["name"], r["sim"] = (n if s >= a.min_sim else "?"), f"{s:.3f}"
    write_rows(rows)
    names = {}
    for r in rows:
        names[r["name"]] = names.get(r["name"], 0) + 1
    print(", ".join(f"{n}: {c}" for n, c in sorted(names.items(), key=lambda kv: -kv[1])))


def cmd_sheets(a):
    rows = read_rows()
    out = LIB / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    by = {}
    for r in rows:
        by.setdefault(r["name"] or "?", []).append(r)
    cw, ch, cols, per = 480, 270, 5, 30
    for name, rs in by.items():
        rs.sort(key=lambda r: -float(r["face_h"]))
        for n in range(0, len(rs), per):
            part = rs[n:n + per]
            rows_n = (len(part) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * (cw + 6), rows_n * (ch + 22)), (15, 15, 15))
            d = ImageDraw.Draw(sheet)
            for i, r in enumerate(part):
                im = Image.open(r["file"]).convert("RGB")
                im.thumbnail((cw, ch))
                x, y = (i % cols) * (cw + 6), (i // cols) * (ch + 22)
                sheet.paste(im, (x, y))
                label = Path(r["file"]).stem + (f"  {r['sim']}" if r["sim"] else "")
                d.text((x + 4, y + ch + 4), label, fill=(230, 230, 230))
            safe = "unknown" if name in ("?", "") else name.replace(" ", "_")
            sheet.save(out / f"{safe}_{n // per + 1}.jpg", quality=88)
    print(f"sheets in {out}: " + ", ".join(f"{k} {len(v)}" for k, v in by.items()))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("video"); p.add_argument("--every", type=int, default=10); p.add_argument("--min-h", dest="min_h", type=float, default=0.14)
    p = sub.add_parser("stills")
    p.add_argument("dir"); p.add_argument("--min-h", dest="min_h", type=float, default=0.10)
    p = sub.add_parser("label")
    p.add_argument("--min-sim", dest="min_sim", type=float, default=0.363)  # OpenCV Zoo's cosine threshold for SFace
    p.add_argument("--people", default=str(PEOPLE), help="one sub-folder per person with pictures of their face")
    sub.add_parser("sheets")
    a = ap.parse_args()
    {"scan": cmd_scan, "stills": cmd_stills, "label": cmd_label, "sheets": cmd_sheets}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
