"""Machine eyes for the brain's frames (WORK/frames/<key>/*.jpg): where the people, vehicles and animals are (YOLOv8), whose faces
they are (YuNet + SFace against the people folders, below), where the picture is dark or has text (RapidOCR). The
description pass then picks the main subject among the numbered boxes, so its 9:16 window is placed on a measured box, not a guess.
-> WORK/work/<key>_det.json  {frame: {"boxes": [[cls, conf, x0, y0, x1, y1], ...], "faces": [[name, sim, x0, y0, x1, y1]],
"text": [[words, x0, y0, x1, y1]], "luma": mean}}  (coordinates are fractions of the frame)

  yolo  <key>   VISION tools/footage/brain_detect.py yolo <key>      (the vision python: ultralytics)
  faces <key>   EDIT tools/footage/brain_detect.py faces <key>
  text  <key>   EDIT tools/footage/brain_detect.py text <key>        RapidOCR on each frame: text boxes with their words
Each mode writes its own file (<key>_det_<mode>.json) so the three can run side by side; load_all(key) merges them (and a single
<key>_det.json when there is one).
Model files come from MODELS: yolo/yolov8s.pt, yunet/face_detection_yunet_2023mar.onnx, sface/face_recognition_sface_2021dec.onnx.
The people folders: FOOTAGE/people/<Name>/*.jpg, one folder per person the creator wants named (clear, front-facing pictures; a folder
whose name holds " and " is a pair picture and is skipped)."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402

YUNET = str(B.MODELS / "yunet" / "face_detection_yunet_2023mar.onnx")
SFACE = str(B.MODELS / "sface" / "face_recognition_sface_2021dec.onnx")
PEOPLE = B.PEOPLE
YOLO_W = str(B.MODELS / "yolo" / "yolov8s.pt")
# COCO classes kept (the rest is noise for most footage): people, vehicles, animals, a few objects
KEEP = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane", 5: "bus", 6: "train", 7: "truck", 8: "boat", 14: "bird", 15: "cat",
        16: "dog", 17: "horse", 18: "sheep", 19: "cow", 20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack", 26: "handbag",
        28: "suitcase", 32: "sports ball", 34: "baseball bat", 36: "skateboard", 37: "surfboard", 38: "tennis racket", 62: "tv", 63: "laptop",
        67: "cell phone", 73: "book", 77: "teddy bear"}


def det_path(key, mode=""):
    """Each mode writes its own file (yolo, faces and text run side by side without clobbering each other); load_all merges them."""
    return B.WORK / "work" / f"{B.key_file(key)}_det{('_' + mode) if mode else ''}.json"


def load(key, mode=""):
    p = det_path(key, mode)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save(key, d, mode=""):
    det_path(key, mode).write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")


def load_all(key):
    """Every detection of a source merged per frame: the single file, then the per-mode files."""
    out = load(key)
    for mode in ("yolo", "faces", "text"):
        for f, x in load(key, mode).items():
            out.setdefault(f, {}).update(x)
    return out


def frames(key):
    return sorted((B.WORK / "frames" / B.key_file(key)).glob("*.jpg"))


def yolo(key):
    from ultralytics import YOLO
    from PIL import Image
    import torch
    torch.set_num_threads(2)      # light CPU: other jobs share the machine
    model = YOLO(YOLO_W)
    d = load(key, "yolo")
    done = load_all(key)
    fl = frames(key)
    todo = [p for p in fl if "boxes" not in done.get(p.stem, {})]
    for i in range(0, len(todo), 8):
        batch = todo[i:i + 8]
        ims = [Image.open(p).convert("RGB") for p in batch]
        res = model.predict(ims, imgsz=640, conf=0.3, verbose=False)
        for p, im, r in zip(batch, ims, res):
            W, H = im.size
            bx = []
            for c, cf, xy in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist()):
                c = int(c)
                if c in KEEP:
                    bx.append([KEEP[c], round(cf, 2), round(xy[0] / W, 4), round(xy[1] / H, 4), round(xy[2] / W, 4), round(xy[3] / H, 4)])
            bx.sort(key=lambda b: -(b[4] - b[2]) * (b[5] - b[3]))
            g = np.asarray(im.convert("L"), dtype=np.float32)
            d.setdefault(p.stem, {})["boxes"] = bx[:12]
            d[p.stem]["luma"] = round(float(g.mean()), 1)
        if (i // 8) % 20 == 0:
            save(key, d, "yolo")
            print(f"  {key}: {min(i + 8, len(todo))}/{len(todo)} frames", flush=True)
    save(key, d, "yolo")
    print(f"{key}: yolo on {len(todo)} frames -> {det_path(key, 'yolo')}")


def _refs(det, rec):
    """SFace features of every reference face: one folder per person in the people folders (pair folders skipped)."""
    import cv2
    refs = {}
    if not PEOPLE.exists():
        return refs
    for folder in sorted(p for p in PEOPLE.iterdir() if p.is_dir() and " and " not in p.name):
        feats = []
        for img in sorted(folder.glob("*.jpg")):
            a = cv2.imread(str(img))
            if a is None:
                continue
            h, w = a.shape[:2]
            k = 1280 / w
            a = cv2.resize(a, (1280, int(h * k)))
            det.setInputSize((a.shape[1], a.shape[0]))
            _, fs = det.detect(a)
            if fs is None or len(fs) == 0:
                continue
            f = max(fs, key=lambda r: r[3])
            feats.append(rec.feature(rec.alignCrop(a, f)))
        if feats:
            refs[folder.name] = feats
    return refs


def faces(key, min_sim=0.363):
    import cv2
    cv2.setNumThreads(2)          # light CPU
    det = cv2.FaceDetectorYN.create(YUNET, "", (1280, 720), 0.7)
    rec = cv2.FaceRecognizerSF.create(SFACE, "")
    refs = _refs(det, rec)
    print("  references:", {k: len(v) for k, v in refs.items()})
    d = load(key, "faces")
    done = load_all(key)
    fl = frames(key)
    todo = [p for p in fl if "faces" not in done.get(p.stem, {})]
    for i, p in enumerate(todo):
        a = cv2.imread(str(p))
        if a is None:
            continue
        H, W = a.shape[:2]
        det.setInputSize((W, H))
        _, fs = det.detect(a)
        out = []
        for f in ([] if fs is None else fs):
            x, y, w, h = (float(v) for v in f[:4])
            if h < 0.045 * H:
                continue   # too small to tell anyone apart
            e = rec.feature(rec.alignCrop(a, f))
            best, bs = "?", 0.0
            for name, feats in refs.items():
                s = max(float(rec.match(e, r, cv2.FaceRecognizerSF_FR_COSINE)) for r in feats)
                if s > bs:
                    best, bs = name, s
            out.append([best if bs >= min_sim else "?", round(bs, 3), round(x / W, 4), round(y / H, 4), round((x + w) / W, 4), round((y + h) / H, 4)])
        d.setdefault(p.stem, {})["faces"] = out
        if i % 200 == 0:
            save(key, d, "faces")
            print(f"  {key}: {i}/{len(todo)} frames", flush=True)
    save(key, d, "faces")
    print(f"{key}: faces on {len(todo)} frames -> {det_path(key, 'faces')}")


def text(key):
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image
    try:                          # light CPU
        ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
    except TypeError:
        ocr = RapidOCR()
    d = load(key, "text")
    done = load_all(key)
    fl = frames(key)
    todo = [p for p in fl if "text" not in done.get(p.stem, {})]
    for i, p in enumerate(todo):
        im = Image.open(p).convert("RGB")
        W, H = im.size
        res, _ = ocr(np.asarray(im))
        out = []
        for box, words, conf in (res or []):
            if float(conf) < 0.6 or len(words.strip()) < 2:
                continue
            xs, ys = [q[0] for q in box], [q[1] for q in box]
            out.append([words.strip(), round(min(xs) / W, 4), round(min(ys) / H, 4), round(max(xs) / W, 4), round(max(ys) / H, 4)])
        d.setdefault(p.stem, {})["text"] = out[:12]
        if i % 200 == 0:
            save(key, d, "text")
            print(f"  {key}: {i}/{len(todo)} frames", flush=True)
    save(key, d, "text")
    print(f"{key}: text on {len(todo)} frames -> {det_path(key, 'text')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["yolo", "faces", "text"])
    ap.add_argument("key", help="a source key, or a library code with --lib")
    ap.add_argument("--lib", action="store_true", help="every clip of the library <key> that has frames")
    a = ap.parse_args()
    fn = {"yolo": yolo, "faces": faces, "text": text}[a.mode]
    if a.lib:
        for p in B.lib_files(a.key):
            k = f"{a.key}/{p.stem}"
            if (B.WORK / "frames" / B.key_file(k)).exists():
                fn(k)
    else:
        fn(a.key)
