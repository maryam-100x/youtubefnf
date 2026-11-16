"""The asset ledger: what every past edit put on screen, read from its own composition, into kb/ASSET_LEDGER.json. reuse_check.py
compares an edit against it, so no asset comes back one-to-one from the last videos (the style stays; the assets change).

How it reads an edit: ledger/walk.tsx steps the composition through react-dom/server at every 6th frame (0.1 s at 60 fps) and at the first
frame of every sequence, with Remotion stubbed (ledger/remotion_stub.tsx: the same timeline rules, nothing rendered or decoded). Each
<OffthreadVideo> reports its file and source second, each <Img>, <img> and CSS url() its file, each of our components its name, its file and
its props. Here the samples become uses: a clip with its source span (exact where it plays to its sequence's edges, else to the sample,
0.1 s), a still with its time on screen, a receipt page with its URL and quote, a graphic component with its props. Nothing is guessed: a
span the samples can't pin down says so (`edges`), and a composition that fails to walk is listed under `failed`.

Provenance where it is written down: curated vertical cuts (a sigs.json next to them in the public dir, <folder>/<part>/sigs.json: the
master and second each file was cut from, as curate.py writes it); credits from the SOURCES files; receipts' URLs and quotes from
captures*.json and pages*.json. Footage cut into different files from one source is matched by reuse_check.py's picture fingerprints
(fp_* below).

The delivered videos are listed in data/delivered_videos.json (one entry per video: its composition as src/Root.tsx registers it, its
kind, date and delivered file); the master sources in data/curate_masters.json. Run from the repo root with the pipeline python (Node
and ffmpeg on PATH or in config/paths.toml):
  PIPE tools/motion/asset_ledger.py                  # every video in data/delivered_videos.json, written to the ledger
  PIPE tools/motion/asset_ledger.py --only 012,013   # some (the others stay as they are)
  ... --rev <commit>    the compositions as committed at <commit> (a delivered version), not the working tree
A new video goes into data/delivered_videos.json when it is delivered, then this runs for it."""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FOOTAGE, KB, MEDIA, NODE, PUBLIC, REPO, VIDEOS_REPO  # noqa: E402

HERE = Path(__file__).resolve().parent            # tools/motion
SRC = HERE / "src"
SRC_REL = "tools/motion/src"                      # the same, as git names it
OUT = HERE / "out/ledger"                         # walker bundles, walks, the fingerprint cache (gitignored)
LEDGER = KB / "ASSET_LEDGER.json"
PUB = PUBLIC                                      # the public dir every composition reads from
STEP = 6                                          # frames between samples (0.1 s at 60 fps)
FPS = 60
DATA = HERE / "data"


def _load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# The master sources (the long official films a video's footage is cut from) by the keys curate.py's cuts name: data/curate_masters.json
# {"<key>": "<path under FOOTAGE, or absolute>"} (shared with curate.py); data/master_crops.json {"<key>": "<ffmpeg crop>"} gives the 16:9
# picture inside a letterboxed master, so a master's fingerprints compare like the cuts made from it.
MASTERS = {k: (Path(v) if Path(v).is_absolute() else FOOTAGE / v) for k, v in _load("curate_masters.json", {}).items() if v}
MASTER_CROP = {k: _load("master_crops.json", {}).get(k, "") for k in MASTERS}

# One entry per delivered video: its composition as Root.tsx registers it. `folders`: the src folders that are this video's own code (a
# component from another video's folder is that video's graphic). `date`: the delivered file's time.
VIDEOS = _load("delivered_videos.json", [])

# The house kits: used by many videos on purpose (the house style). A component from them is reported as the house's, never as a video's.
KITS = {"house": "the house kit", "lib.tsx": "lib.tsx", "kit3": "kit3", "kit3d": "kit3d"}
# Components that only play a file or frame the screen: their media is in clips/stills, they are not a graphic of their own
WRAPPERS = {"Clip", "LClip", "Foot", "Chain", "Still", "Full", "At", "Play", "Layer", "Sfx", "Grain", "Vignette", "Dust", "Marker", "Media",
            "Cover", "Blurred", "Backdrop", "Pic", "Stage", "Shot", "Scene", "Overlay", "Over", "Seq", "Subs", "Credit", "FlashIn", "Flash"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
STOCK_RE = re.compile(r"pexels|pixabay|mixkit|coverr|videvo|storyblocks|unsplash|/stock/|(^|/)fx_", re.I)


def log(*a):
    print(*a, flush=True)


def node(*args, env=None, timeout=3600):
    e = dict(os.environ, **(env or {}))
    return subprocess.run([NODE, *args], cwd=HERE, env=e, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


# ------------------------------------------------------------------------------------------------------------------------------ walking

def src_tree(rev):
    """The src/ to walk: the working tree, or `rev`'s committed src/ exported under out/ledger/rev_<sha>/ (node_modules resolve from there)."""
    if not rev:
        return SRC, None
    sha = subprocess.run(["git", "rev-parse", "--short=10", rev], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    root = OUT / f"rev_{sha}"
    tree = root / SRC_REL
    if not tree.exists():
        tar = subprocess.run(["git", "archive", "--format=tar", sha, SRC_REL], cwd=REPO, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(root, filter="data")
    return tree, sha


def entry_source(v, tree):
    rel = lambda p: Path(p).as_posix()
    mod = rel(tree / v["module"])
    lines = ["import {walk} from '" + rel(HERE / "ledger/walk") + "';"]
    if v.get("props_json"):
        lines += [f"import {{{v['export']}}} from '{mod}';", f"import cur from '{rel(tree / v['props_json'])}';",
                  f"walk({{id: '{v['comp']}', comp: {v['export']} as never, props: {{cur}}, seconds: (cur as {{duration: number}}).duration, "
                  f"width: {v['size'][0]}, height: {v['size'][1]}}});"]
    else:
        names = [v["export"], v["seconds"]] + ([v["shots"]] if v.get("shots") else [])
        lines += [f"import {{{', '.join(names)}}} from '{mod}';",
                  f"walk({{id: '{v['comp']}', comp: {v['export']} as never, seconds: {v['seconds']}, width: {v['size'][0]}, height: {v['size'][1]}"
                  + (f", shots: {v['shots']}" if v.get("shots") else "") + "});"]
    return "\n".join(lines) + "\n"


def walk(v, rev=None, step=STEP):
    """Walks one composition; returns the walker's JSON (media, comps, errors) plus where it ran."""
    OUT.mkdir(parents=True, exist_ok=True)
    tree, sha = src_tree(rev)
    tag = f"{v['comp']}{'_' + sha if sha else ''}"
    ent, cjs, js = OUT / f"e_{tag}.tsx", OUT / f"e_{tag}.cjs", OUT / f"{tag}.json"
    ent.write_text(entry_source(v, tree), encoding="utf-8")
    b = node(str(HERE / "ledger/build.mjs"), str(ent), str(cjs), env={"LEDGER_SRC": str(tree)})
    if b.returncode:
        raise RuntimeError(f"{v['comp']}: the walker did not bundle: {(b.stderr or b.stdout)[-1500:]}")
    t0 = time.time()
    r = node(str(cjs), env={"LEDGER_OUT": str(js), "LEDGER_STEP": str(step)})
    if r.returncode or not js.exists():
        raise RuntimeError(f"{v['comp']}: the walk failed: {(r.stderr or r.stdout)[-1500:]}")
    w = json.loads(js.read_text(encoding="utf-8"))
    w["src"] = f"{SRC_REL}{' @ ' + sha if sha else ''}"
    w["wall"] = round(time.time() - t0, 1)
    return w


# -------------------------------------------------------------------------------------------------------------------- what we know of files

def _tsv_rows(p):
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for ln in lines[1:]:
        cols = [c.strip() for c in ln.split("\t")]
        if len(cols) >= 2 and cols[0]:
            yield cols


def credits_index():
    """basename -> a credit line, from every SOURCES file in the public dir (their formats differ: tsv, txt, md, json)."""
    idx = {}
    for p in list(PUB.glob("*/SOURCES*")) + list(PUB.glob("*/*/SOURCES*")) + list(PUB.glob("*/*/*/SOURCES*")):
        try:
            if p.suffix in (".tsv", ".txt"):
                for cols in _tsv_rows(p):
                    key = Path(cols[0].replace("\\", "/")).name
                    if "." in key:
                        idx.setdefault(key.lower(), " | ".join(c for c in cols[1:] if c)[:300])
            elif p.suffix == ".md":
                for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = re.match(r"\s*-\s*([^:]+):\s*(.+)", ln)
                    if m:
                        for name in re.findall(r"[\w.\-]+\.(?:jpg|jpeg|png|webp|mp4|svg)", m.group(1)):
                            idx.setdefault(name.lower(), m.group(2)[:300])
            elif p.suffix == ".json":
                for k, e in json.loads(p.read_text(encoding="utf-8")).items():
                    if isinstance(e, dict):
                        idx.setdefault(f"{k}.jpg".lower(), f"{e.get('title', '')} | {e.get('src', '')}"[:300])
        except (OSError, ValueError):
            continue
    return idx


def pages_index():
    """A receipt's published file -> its url, quotes, outlet, date (captures*.json for the urls, src/*/pages*.json and receipts.json for the files)."""
    caps = {}
    for p in VIDEOS_REPO.glob("*/captures*.json"):
        try:
            for k, e in json.loads(p.read_text(encoding="utf-8")).items():
                if isinstance(e, dict) and e.get("url"):
                    caps.setdefault(k, e)
        except ValueError:
            continue
    idx = {}
    for p in list(SRC.glob("*/pages*.json")) + list(SRC.glob("*/receipts*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for k, e in data.items():
            if not isinstance(e, dict) or not e.get("src"):
                continue
            c = caps.get(k, {})
            marks = e.get("marks")
            quotes = list(marks.keys()) if isinstance(marks, dict) else (c.get("marks") if isinstance(c.get("marks"), list) else [])
            idx[e["src"]] = {"url": e.get("url") or c.get("url"), "quotes": quotes, "outlet": e.get("outlet") or c.get("outlet"),
                             "date": e.get("date") or c.get("date"), "key": k}
    return idx


def masters_index():
    """A cut file -> the master and seconds it was cut from, where a cutting tool wrote it down (curate.py's sigs.json next to the
    vertical cuts it makes: <folder>/<part>/sigs.json in the public dir)."""
    idx = {}
    for sigf in PUB.glob("*/*/sigs.json"):
        part = sigf.parent.relative_to(PUB).as_posix()
        try:
            sigs = json.loads(sigf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for name, sig in sigs.items():
            try:
                s = json.loads(sig) if isinstance(sig, str) else sig
            except ValueError:
                continue
            if not isinstance(s, list):
                continue
            if len(s) >= 8 and s[1] in MASTERS and s[2] is not None:      # [img, src, t, cx, cy, h, lift, dur, ...]
                idx[f"{part}/{name}.mp4"] = {"master": s[1], "t": float(s[2]), "cut": True}
                idx[f"{part}/{name}.jpg"] = {"master": s[1], "t": float(s[2]), "still": True}
            elif len(s) >= 4 and s[0] in MASTERS and isinstance(s[2], list):  # an inset: [src, t, inset, dur]
                idx[f"{part}/{name}.mp4"] = {"master": s[0], "t": float(s[1]), "inset": s[2], "cut": True}
            elif s and isinstance(s[0], str):
                idx[f"{part}/{name}.jpg"] = {"image": s[0]}
    return idx


def clip_lengths():
    try:
        return {k: v[0] for k, v in json.loads((SRC / "clipdurs.json").read_text(encoding="utf-8")).items()}
    except (OSError, ValueError):
        return {}


def norm_src(s):
    s = s.replace("\\", "/")
    s = re.sub(r"^https?://localhost[^/]*/", "", s)
    return s.lstrip("/").removeprefix("public/")


def is_video(path):
    return Path(path.split("?")[0]).suffix.lower() in VIDEO_EXT


def still_family(path, via):
    low, name = path.lower(), Path(path).name.lower()
    if "/pages/" in low or (via and via[-1] in ("PageStage", "Page")):
        return "page"
    if "logo" in name:
        return "logo"
    if "/covers/" in low:
        return "cover"
    if low.startswith("official/") or "/official/" in low or name.startswith(("art_", "key_art", "keyart")):
        return "official art"
    if "thumb" in name:
        return "thumbnail"
    if "/pics/" in low or "commons" in name or "/img/" in low or "/photos/" in low:
        return "photo"
    return "still"


def file_md5(path):
    p = PUB / path
    try:
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


# ------------------------------------------------------------------------------------------------------------------ the walk -> uses

def _window(m, step, frames):
    """The frames an element was on screen: its samples, snapped to its sequence's edges when they lie within a sample of them."""
    ws = m.get("winStart") or 0
    we = m.get("winEnd")
    we = frames if we is None else min(we, frames)
    lo_exact = m["first"] - ws <= step
    hi_exact = we - (m["last"] + 1) <= step
    lo = ws if lo_exact else m["first"] - step // 2
    hi = we if hi_exact else m["last"] + 1 + step // 2
    return max(lo, ws), min(hi, we), lo_exact and hi_exact


def _master_re():
    keys = [re.escape(k.lower()) for k in MASTERS]
    return re.compile(r"/(" + "|".join(keys) + r")_") if keys else None


def uses_from_walk(v, w, credits, pages, masters, lengths):
    fps, step, frames = w["fps"], w["step"], w["frames"]
    r3 = lambda x: round(x, 3)
    mre = _master_re()
    clips, stills, comps, md5s = {}, {}, {}, {}
    for m in w["media"]:
        src = norm_src(m["src"])
        via = [p[0] for p in m["path"]]
        lo, hi, exact = _window(m, step, frames)
        use = {"at": r3(lo / fps), "dur": r3((hi - lo) / fps), "shot": r3(m["root"]["from"] / fps), "via": ">".join(via) or "-",
               "edges": "exact" if exact else f"+-{step / fps:.1f} s"}
        if m["kind"] == "video":
            sf, rate, s0 = m["startFrom"], m["rate"], m["seqStart"]
            if m.get("frozen"):
                use.update({"from": r3(m["t0"]), "to": r3(m["t0"]), "rate": 0, "frozen": True})
            else:
                use.update({"from": r3((sf + (lo - s0) * rate) / fps), "to": r3((sf + (hi - s0) * rate) / fps), "rate": rate})
            e = clips.setdefault(src, {"file": src, "uses": []})
            e["uses"].append(use)
        else:
            e = stills.setdefault(src, {"file": src, "uses": []})
            e["uses"].append(use)
            e.setdefault("_vias", []).append(via)
    for src, e in clips.items():
        name = Path(src).name.lower()
        e["length"] = lengths.get(src)
        cr = credits.get(name)
        if cr:
            e["credit"] = cr
        mm = masters.get(src)
        if mm:
            e["master"] = mm
        e["family"] = ("official" if mm or (mre and mre.search("/" + src.lower())) else
                       "stock" if STOCK_RE.search(src) or (cr and STOCK_RE.search(cr)) else "outside")
        if e["family"] == "official" and mm:
            for u in e["uses"]:
                u["master_span"] = [r3(mm["t"] + u["from"]), r3(mm["t"] + u["to"])]
        e["uses"] = _merge(e["uses"])
    out_stills, out_pages = [], []
    for src, e in stills.items():
        vias = e.pop("_vias")
        mm = masters.get(src)
        if mm:
            e["source"] = mm
        fam = still_family(src, max(vias, key=len))
        if mm and (mm.get("master") or "official/" in str(mm.get("image", ""))):
            fam = "official art"                            # a still cut from the source's own frame, artwork or screenshot
        e["family"] = fam
        cr = credits.get(Path(src).name.lower())
        if cr:
            e["credit"] = cr
        if src not in md5s:
            md5s[src] = file_md5(src)
        if md5s[src]:
            e["md5"] = md5s[src]
        e["uses"] = _merge(e["uses"])
        if fam == "page":
            pi = pages.get(src)
            if pi:
                e.update({k: x for k, x in pi.items() if x})
            out_pages.append(e)
        else:
            out_stills.append(e)
    own = tuple(v.get("folders", []))
    for c in w["comps"]:
        if c["name"] in WRAPPERS or c["name"].startswith("ledger:"):
            continue
        mod = c["mod"] or "?"
        key = (c["name"], mod)
        e = comps.setdefault(key, {"name": c["name"], "module": mod, "origin": origin_of(mod, own), "uses": []})
        try:
            props = json.loads(c["props"]) if not c["props"].endswith("…") else {"_props": c["props"]}
        except ValueError:
            props = {"_props": c["props"]}
        lo, hi = c["first"], c["last"] + step
        e["uses"].append({"at": r3(lo / fps), "dur": r3(min(hi - lo, c["root"]["from"] + c["root"]["dur"] - lo) / fps), "shot": r3(c["root"]["from"] / fps),
                          "via": ">".join(p[0] for p in c["path"]) or "-", "props": props})
    for e in comps.values():
        e["uses"] = _merge_comp(e["uses"])
    return (sorted(clips.values(), key=lambda e: e["uses"][0]["at"]), sorted(out_stills, key=lambda e: e["uses"][0]["at"]),
            sorted(out_pages, key=lambda e: e["uses"][0]["at"]), sorted(comps.values(), key=lambda e: e["uses"][0]["at"]))


def origin_of(mod, own):
    top = mod.split("/")[0]
    if top in own:
        return "own"
    if top in KITS or mod in KITS:
        return "kit: " + KITS.get(top, KITS.get(mod, top))
    for v in VIDEOS:
        if top in v.get("folders", []):
            return "from " + v["video"]
    return "other: " + top


def _merge(uses):
    """One use per (time, span): the same file drawn twice in one shot (a photo over its own blurred copy) is one use."""
    out = {}
    for u in sorted(uses, key=lambda u: (u["at"], -u["dur"])):
        k = (u["at"], u["dur"], u.get("from"), u.get("to"))
        if k in out:
            if u["via"] not in out[k]["via"].split(" + "):
                out[k]["via"] += " + " + u["via"]
            continue
        out[k] = u
    return list(out.values())


def _merge_comp(uses):
    out = {}
    for u in sorted(uses, key=lambda u: u["at"]):
        k = u["shot"]
        if k in out:
            o = out[k]
            end = max(o["at"] + o["dur"], u["at"] + u["dur"])
            o["at"] = min(o["at"], u["at"])
            o["dur"] = round(end - o["at"], 3)
            continue
        out[k] = u
    return list(out.values())


def ledger_entry(v, w, idx):
    clips, stills, pages, comps = uses_from_walk(v, w, *idx)
    e = {k: v[k] for k in ("video", "title", "kind", "comp", "date", "delivered")}
    e["code"] = f"{w['src']}/{v['module']}.tsx" + (f" with {v['props_json']}" if v.get("props_json") else "")
    e["walk"] = {"fps": w["fps"], "frames": w["frames"], "seconds": round(w["frames"] / w["fps"], 2), "step": w["step"], "samples": w["samples"],
                 "errors": w.get("errorCount", 0), "walked": time.strftime("%Y-%m-%dT%H:%M"), "wall_s": w.get("wall")}
    if w.get("errors"):
        e["walk"]["first_errors"] = w["errors"][:5]
    e["clips"], e["stills"], e["pages"], e["components"] = clips, stills, pages, comps
    unresolved = [f"{c['file']} at {u['at']:.2f} s: edges {u['edges']}" for c in clips for u in c["uses"] if u["edges"] != "exact"]
    unresolved += [f"{c['file']}: not in src/clipdurs.json (file length unknown)" for c in clips if c.get("length") is None]
    e["unresolved"] = unresolved
    e["counts"] = {"clips": len(clips), "clip_uses": sum(len(c["uses"]) for c in clips), "stills": len(stills), "pages": len(pages),
                   "components": len(comps)}
    return e


def indexes():
    return credits_index(), pages_index(), masters_index(), clip_lengths()


# --------------------------------------------------------------------------------------------------------- picture fingerprints (reuse_check)

FP_CACHE = OUT / "fp_cache.json"
_fp = None


def _fp_cache():
    global _fp
    if _fp is None:
        try:
            _fp = json.loads(FP_CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _fp = {}
    return _fp


def fp_save():
    if _fp is not None:
        OUT.mkdir(parents=True, exist_ok=True)
        FP_CACHE.write_text(json.dumps(_fp), encoding="utf-8")


def _dhash_frames(raw, n):
    """dHash (64 bits) of each 9x8 grey frame in `raw`: a bit per neighbouring pixel pair, set where the left one is brighter."""
    out = []
    for i in range(n):
        f = raw[i * 72:(i + 1) * 72]
        if len(f) < 72:
            break
        h, spread = 0, max(f) - min(f)
        for y in range(8):
            row = f[y * 9:(y + 1) * 9]
            for x in range(8):
                h = (h << 1) | (1 if row[x] > row[x + 1] else 0)
        out.append(h if spread >= 24 else None)          # a flat frame (black, a fade, a plain card) matches everything: left out
    return out


def fingerprints(path, t0, t1, rate_hz=2.0, crop=""):
    """Fingerprints of a file's frames from t0 to t1 s, `rate_hz` a second (a still: one). The centre 60% of the picture, so a crop made
    for one video and a full frame of the same moment still compare. Cached by file, size, time and span."""
    p = Path(path) if Path(path).is_absolute() else PUB / path
    try:
        st = p.stat()
    except OSError:
        return None
    key = f"{p.as_posix()}|{st.st_size}|{int(st.st_mtime)}|{t0:.2f}|{t1:.2f}|{rate_hz}|{crop}"
    c = _fp_cache()
    if key in c:
        return c[key]
    vf = ",".join(x for x in (crop, "crop=iw*0.6:ih*0.6", f"fps={rate_hz}" if is_video(str(p)) else "", "scale=9:8:flags=area", "format=gray") if x)
    if is_video(str(p)):
        span = max(0.05, t1 - t0)
        cmd = [FFMPEG, "-v", "error", "-ss", f"{max(0.0, t0):.3f}", "-t", f"{span:.3f}", "-i", str(p), "-an", "-vf", vf, "-f", "rawvideo", "-"]
    else:
        cmd = [FFMPEG, "-v", "error", "-i", str(p), "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=600)
    raw = r.stdout
    hashes = _dhash_frames(raw, len(raw) // 72)
    if not hashes and is_video(str(p)):                   # a span shorter than one sample: its first frame
        r = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, t0):.3f}", "-i", str(p), "-frames:v", "1", "-an", "-vf",
                            ",".join(x for x in (crop, "crop=iw*0.6:ih*0.6", "scale=9:8:flags=area", "format=gray") if x), "-f", "rawvideo", "-"],
                           capture_output=True, timeout=600)
        hashes = _dhash_frames(r.stdout, len(r.stdout) // 72)
    c[key] = [None if h is None else f"{h:016x}" for h in hashes]
    return c[key]


def fp_args(entry, use, kind):
    """What to fingerprint for one use: a clip's span (a vertical cut: its master at the same seconds, the full frame), a still."""
    if kind == "clip":
        mm = entry.get("master")
        if mm and mm.get("master") in MASTERS and mm.get("cut"):
            return (str(MASTERS[mm["master"]]), round(mm["t"] + use["from"], 2), round(mm["t"] + max(use["to"], use["from"] + 0.1), 2),
                    MASTER_CROP.get(mm["master"], ""))
        return (entry["file"], round(use["from"], 2), round(max(use["to"], use["from"] + 0.1), 2), "")
    src = entry.get("source") or {}
    if src.get("master") in MASTERS:                       # a still cut from a master frame
        return (str(MASTERS[src["master"]]), round(src["t"], 2), round(src["t"] + 0.1, 2), MASTER_CROP.get(src["master"], ""))
    if src.get("image"):
        return (str(MEDIA / src["image"]), 0.0, 0.0, "")
    return (entry["file"], 0.0, 0.0, "")


def use_fingerprints(entry, use, kind):
    p, t0, t1, crop = fp_args(entry, use, kind)
    return fingerprints(p, t0, t1, crop=crop)


def fingerprint_all(jobs, workers=6):
    """Runs (entry, use, kind) fingerprint jobs in parallel, each distinct file and span once; the results land in the cache."""
    todo = sorted({fp_args(*j) for j in jobs})
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda a: fingerprints(a[0], a[1], a[2], crop=a[3]), todo))
    fp_save()


# ------------------------------------------------------------------------------------------------------------------------------- main

def load_ledger():
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"videos": {}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated video numbers (e.g. 012,013); the others stay as they are in the ledger")
    ap.add_argument("--rev", help="walk the compositions as committed at this git revision")
    ap.add_argument("--step", type=int, default=STEP, help=f"frames between samples (default {STEP})")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    if not VIDEOS:
        log(f"no delivered videos listed in {DATA / 'delivered_videos.json'} yet: nothing to walk")
    led = load_ledger()
    led.setdefault("videos", {})
    idx = indexes()
    failed = {}
    for v in VIDEOS:
        if only and v["video"] not in only:
            continue
        log(f"{v['video']} {v['comp']}: walking ...")
        try:
            w = walk(v, a.rev, a.step)
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            failed[v["video"]] = str(e)[:600]
            log(f"  FAILED: {str(e)[:300]}")
            continue
        e = ledger_entry(v, w, idx)
        led["videos"][v["video"]] = e
        c = e["counts"]
        log(f"  {w['samples']} samples in {w.get('wall')} s, {e['walk']['errors']} errors: {c['clips']} clips ({c['clip_uses']} uses), "
            f"{c['stills']} stills, {c['pages']} pages, {c['components']} components; {len(e['unresolved'])} unresolved")
    led["_doc"] = ("What every delivered edit put on screen, read from its composition by tools/motion/asset_ledger.py (its docstring says "
                   "how); tools/motion/reuse_check.py compares an edit against it. Times in seconds of the video; a clip's "
                   "from/to are seconds of its file (master_span: of the master source it was cut from); edges 'exact' = the span is the "
                   "sequence's own, else known to the sample.")
    led["updated"] = time.strftime("%Y-%m-%dT%H:%M")
    if failed:
        led["failed"] = {**led.get("failed", {}), **failed}
    for k in list(led.get("failed", {})):
        if k in led["videos"] and k not in failed:
            led["failed"].pop(k)
    led["videos"] = dict(sorted(led["videos"].items(), key=lambda kv: kv[1]["date"]))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"wrote {LEDGER} ({LEDGER.stat().st_size // 1024} KB, {len(led['videos'])} videos)" + (f"; FAILED: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
