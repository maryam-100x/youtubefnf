"""Download the model files the tools load into MODELS (the setup's step 6), and check each one.

    PIPE tools/setup/models.py            # download what is missing, then check
    PIPE tools/setup/models.py --check    # check only

What lands where (every tool reads these paths through tools/common/paths.py):
  MODELS/yunet/face_detection_yunet_2023mar.onnx   face detection (OpenCV Zoo, MIT): framing checks, face library, footage brain
  MODELS/face_detection_yunet_2023mar.onnx         the same file, where the icon tool looks for it
  MODELS/sface/face_recognition_sface_2021dec.onnx face matching (OpenCV Zoo, Apache 2.0): faces matched by landmarks
  MODELS/yolo/yolov8s.pt                           people and object detection (Ultralytics, AGPL-3.0): framing, footage brain
  MODELS/commonaccent_ecapa/                       the accent classifier (CommonAccent ECAPA, MIT): American-English checks
  MODELS/spkrec_ecapa_voxceleb/                    speaker embeddings (SpeechBrain ECAPA, Apache 2.0): the voice guard
Models the libraries fetch on first use into their own caches (no step needed): faster-whisper (speech to text), the wav2vec2
phoneme aligner, the text and picture embedding models of the footage search, the cut-out model.
"""
import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MODELS  # noqa: E402

UA = {"User-Agent": "studio-setup"}
FILES = {
    "yunet/face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "sface/face_recognition_sface_2021dec.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    "yolo/yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt",
}
HF = {  # SpeechBrain models: the whole repo into its folder, plus the empty custom.py the loader wants
    "commonaccent_ecapa": "Jzuluaga/accent-id-commonaccent_ecapa",
    "spkrec_ecapa_voxceleb": "speechbrain/spkrec-ecapa-voxceleb",
}
MIN_BYTES = {"yunet": 200_000, "sface": 30_000_000, "yolo": 20_000_000}


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(dest)


def download():
    for rel, url in FILES.items():
        dest = MODELS / rel
        if not dest.exists():
            print("downloading", rel)
            fetch(url, dest)
    root_copy = MODELS / "face_detection_yunet_2023mar.onnx"
    if not root_copy.exists():
        shutil.copyfile(MODELS / "yunet" / "face_detection_yunet_2023mar.onnx", root_copy)
    from huggingface_hub import snapshot_download
    for folder, repo in HF.items():
        dest = MODELS / folder
        if not (dest / "hyperparams.yaml").exists():
            print("downloading", repo)
            snapshot_download(repo_id=repo, local_dir=str(dest))
        (dest / "custom.py").touch(exist_ok=True)


def check():
    bad = 0
    for rel in list(FILES) + ["face_detection_yunet_2023mar.onnx"]:
        p = MODELS / rel
        need = MIN_BYTES.get(rel.split("/")[0], 200_000)
        ok = p.exists() and p.stat().st_size >= need
        print(f"{'ok ' if ok else 'BAD'} {rel}  {p.stat().st_size if p.exists() else 0:,} bytes")
        bad += not ok
    for folder in HF:
        p = MODELS / folder
        ok = (p / "hyperparams.yaml").exists() and (p / "embedding_model.ckpt").exists()
        print(f"{'ok ' if ok else 'BAD'} {folder}/")
        bad += not ok
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not a.check:
        download()
    sys.exit(1 if check() else 0)
