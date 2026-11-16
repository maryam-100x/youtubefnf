"""Local embeddings for the brain (CPU, no API): a sentence embedding of every record's words (all-MiniLM-L6-v2) and a CLIP picture
embedding of its frames (clip-vit-base-patch32), so find_shot.py can match a script line by meaning and by what the picture shows, not
only by shared words. The models come from the Hugging Face cache (downloaded once on the first run); nothing leaves the machine.
-> kb/footage/brain/embeddings.npz: ids, text (N x 384), clip (N x 512), float16, unit length.

  EDIT tools/footage/brain_embed.py [--only A1,A2]   (others are kept from the file)"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402

EMB = B.BRAIN / "embeddings.npz"
TEXT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CLIP_MODEL = "openai/clip-vit-base-patch32"


def record_text(r):
    """The words a record is embedded and keyword-searched by."""
    parts = [r.get("desc", ""), " ".join(r.get("who", [])), " ".join(r.get("what", [])), r.get("action", ""), r.get("setting", ""),
             r.get("time", ""), r.get("mood", "")]
    parts += [c[2] for c in r.get("cat", [])][:4]
    parts += [m.get("note", "") for m in r.get("moments", [])]
    parts += [f.get("fact") or f.get("note", "") for f in r.get("facts", [])]   # the research facts it shows
    parts += [(r.get("ui") or {}).get("read", "")]                               # an on-screen interface read exactly
    return ". ".join(p for p in parts if p)


class TextEmbedder:
    def __init__(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        torch.set_num_threads(2)          # light CPU: torch on 2 threads
        self.tok = AutoTokenizer.from_pretrained(TEXT_MODEL)
        self.model = AutoModel.from_pretrained(TEXT_MODEL).eval()

    def __call__(self, texts, bs=64):
        out = []
        with self.torch.no_grad():
            for i in range(0, len(texts), bs):
                enc = self.tok(texts[i:i + bs], padding=True, truncation=True, max_length=256, return_tensors="pt")
                h = self.model(**enc).last_hidden_state
                m = enc["attention_mask"].unsqueeze(-1).float()
                e = (h * m).sum(1) / m.sum(1).clamp(min=1e-6)
                e = self.torch.nn.functional.normalize(e, dim=-1)
                out.append(e.cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 384), np.float32)


class ClipEmbedder:
    def __init__(self):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self.torch = torch
        torch.set_num_threads(2)
        self.proc = CLIPProcessor.from_pretrained(CLIP_MODEL)
        self.model = CLIPModel.from_pretrained(CLIP_MODEL).eval()

    def images(self, ims, bs=16):
        out = []
        with self.torch.no_grad():
            for i in range(0, len(ims), bs):
                inp = self.proc(images=ims[i:i + bs], return_tensors="pt")
                # transformers 5 returns an output object from get_image_features: go through the towers and projections
                pooled = self.model.vision_model(pixel_values=inp["pixel_values"]).pooler_output
                e = self.model.visual_projection(pooled)
                out.append(self.torch.nn.functional.normalize(e, dim=-1).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 512), np.float32)

    def texts(self, texts):
        with self.torch.no_grad():
            inp = self.proc(text=texts, return_tensors="pt", padding=True, truncation=True, max_length=77)
            pooled = self.model.text_model(input_ids=inp["input_ids"], attention_mask=inp["attention_mask"]).pooler_output
            e = self.model.text_projection(pooled)
            return self.torch.nn.functional.normalize(e, dim=-1).cpu().numpy()


def frame_paths(r):
    """The frames a record was described from (WORK/frames/<key>/NNNNNNN.jpg), or the still itself."""
    if r.get("kind") == "image":
        return [Path(r["file"])]
    kf = B.key_file(r["src"] if r["src"] in B.MASTERS else r["id"].split("@")[0])
    d = B.WORK / "frames" / kf
    fl = r.get("frames", [])
    if len(fl) > 3:
        fl = [fl[0], fl[len(fl) // 2], fl[-1]]
    return [d / f"{f:07d}.jpg" for f in fl]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    from PIL import Image
    recs = []
    for p in sorted(B.BRAIN.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        recs += d.get("shots", [])
    only = set(a.only.split(",")) if a.only else None
    old = {}
    if EMB.exists() and only:
        E = np.load(EMB, allow_pickle=False)
        for i, sid in enumerate(E["ids"]):
            old[str(sid)] = (E["text"][i], E["clip"][i])
    todo = [r for r in recs if not only or r["src"] in only or r["id"].split("/")[0] in only]
    print(f"{len(recs)} records, {len(todo)} to embed")
    te, ce = TextEmbedder(), ClipEmbedder()
    texts = [record_text(r) or r["id"] for r in todo]
    T = te(texts)
    C = np.zeros((len(todo), 512), np.float32)
    for i, r in enumerate(todo):
        ims = []
        for fp in frame_paths(r):
            if fp.exists():
                try:
                    ims.append(Image.open(fp).convert("RGB"))
                except OSError:
                    pass
        if ims:
            e = ce.images(ims).mean(axis=0)
            C[i] = e / (np.linalg.norm(e) + 1e-9)
        if i % 100 == 0:
            print(f"  clip {i}/{len(todo)}", flush=True)
    ids, text, clip = [], [], []
    done = {r["id"] for r in todo}
    for r in recs:
        if r["id"] in done:
            j = [k for k, x in enumerate(todo) if x["id"] == r["id"]][0]
            ids.append(r["id"]); text.append(T[j]); clip.append(C[j])
        elif r["id"] in old:
            ids.append(r["id"]); text.append(old[r["id"]][0]); clip.append(old[r["id"]][1])
    np.savez_compressed(EMB, ids=np.array(ids), text=np.array(text, np.float16), clip=np.array(clip, np.float16))
    print(f"{len(ids)} embeddings -> {EMB}")


if __name__ == "__main__":
    main()
