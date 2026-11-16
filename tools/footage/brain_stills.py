"""The stills for the brain: every stills key of kb/footage/sources.json (screenshots, photos, artwork). A key with `variants` keeps one
record per artwork, its portrait/phone/square/tablet/ultrawide variants listed beside the landscape file; a key with `skip_copies_of`
leaves out the files another stills key already holds (same name and size), so a picture is never indexed twice. Each still gets a
1280-wide working copy in WORK/frames/<KEY>/NNNNNNN.jpg so brain_detect.py and brain_sheets.py treat it like a shot's frame, and a
shots file (WORK/work/<KEY>_shots.json) with one "shot" per still (f_in = f_out = its index) so the rest of the chain runs unchanged;
brain_build.py --stills <KEY> writes brain/<KEY>.json with kind "image".

  EDIT tools/footage/brain_stills.py prep [KEY ...]   (default: every stills key; a key's shots file is rewritten, so prep only the
  key being added: the indices are the sorted file order of the folder at that moment)"""
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402

EXT = (".jpg", ".jpeg", ".png", ".webp")
VARIANTS = ("_landscape", "_portrait", "_phone", "_square", "_tablet", "_ultrawide")


def list_stills(key):
    """[(index, path, variants)]: every image file of the key's folder, or (a key with `variants`) one per artwork: the landscape
    file, its variants listed. Files another key named in `skip_copies_of` holds (same name and size) are left out."""
    root = B.STILLS[key]
    opts = B.OPTS.get(key, {})
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in EXT)
    for other in opts.get("skip_copies_of", []) or []:
        if other in B.STILLS and B.STILLS[other].exists():
            held = {(p.name, p.stat().st_size) for p in B.STILLS[other].rglob("*") if p.suffix.lower() in EXT}
            files = [p for p in files if (p.name, p.stat().st_size) not in held]
    out = []
    if not opts.get("variants"):
        for i, p in enumerate(files):
            out.append((i, p, []))
        return out
    groups = {}
    for p in files:
        stem = p.stem
        base = stem
        for v in VARIANTS:
            if stem.endswith(v):
                base = stem[: -len(v)]
                break
        groups.setdefault((p.parent, base), []).append(p)
    i = 0
    for (parent, base), ps in sorted(groups.items()):
        main = next((p for p in ps if p.stem.endswith("_landscape")), None) or sorted(ps, key=lambda p: -Image.open(p).size[0])[0]
        out.append((i, main, [str(p).replace("\\", "/") for p in ps if p != main]))
        i += 1
    return out


def prep(keys):
    for key in keys:
        fd = B.WORK / "frames" / key
        fd.mkdir(parents=True, exist_ok=True)
        shots, meta = [], []
        for i, p, variants in list_stills(key):
            out = fd / f"{i:07d}.jpg"
            im = Image.open(p).convert("RGB")
            W, H = im.size
            if not out.exists():
                k = 1280 / W
                im.resize((1280, max(1, round(H * k))), Image.LANCZOS).save(out, quality=90)
            shots.append(dict(f_in=i, f_out=i, c_in=i, c_out=i, edge_flags=[], frames=[i]))
            meta.append(dict(index=i, path=str(p).replace("\\", "/"), rel=B.rel_footage(p), size=[W, H], variants=variants))
        (B.WORK / "work").mkdir(parents=True, exist_ok=True)
        (B.WORK / "work" / f"{key}_shots.json").write_text(json.dumps(dict(key=key, fps=1.0, frames=len(shots), shots=shots, stills=meta), indent=1),
                                                             encoding="utf-8")
        print(f"{key}: {len(shots)} stills -> {fd}")


if __name__ == "__main__":
    prep(tuple(sys.argv[2:]) or tuple(B.STILLS))
