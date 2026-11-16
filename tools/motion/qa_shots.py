"""qa_shots.py: which picture a shot uses and how it is framed: the thing the words name is found at a glance, the people are shown in
the source's own pictures rather than its artwork, and nothing stands too dark to read.

  SUBJECT_MISSING  a still (a screenshot, an artwork, a map: any picture file filling the frame) or a cropped or zoomed clip (drawn 1.15x+
                   the frame, or a window of its source: its first frame is not its master's frame there) with no subject box in its code:
                   a line `// subject: [label] <x> <y> <w> <h> [-> <x> <y> <w> <h>]` in the comment above the shot, in the picture file's
                   own pixels (a clip: the clip file's 1920x1080), `->` the box at the shot's end (a glide, a moving subject). A label that
                   is one of the shot's picture names applies the box to that picture only (a split screen, a burst).
  SUBJECT_LOST     the subject as it lands on screen (its box mapped through the picture's rect the probe records) is not found at a
                   glance, at 2 of the shot's 3 sample frames (10%, 50%, 90%; a moving box at its first and last): its centre more than
                   OFF_CENTRE of the frame's width or height off the middle (a subject at 70% across, 76% down reads as "in the bottom
                   right"), under CUT_MIN of it on screen, small (under SMALL_AREA of the frame and under SMALL_H of its height), or
                   dim (its own mean light under DIM_SUBJECT of 255)
  ART_OVER_REAL    the source's key art (any variant, matched by picture: dhash within ART_BITS of a file in the artwork folders; a kit3d
                   piece made from one) of people the source's own pictures show (the people folders' names), with no
                   `// art: <why no real picture shows it>` above the shot: viewers want the real people
  ART_CLOSE        a third artwork shot inside ART_RUN_S: artwork is a rare variety shot, never a run
  ART_SHARE        artwork on more than ART_SHARE_MAX of the film's screen time
  DARK             a picture too dark to read, on the frames it stands alone (no text or graphic of ours on it, not a card or a dimmed
                   ground): on screen (the source's pixels through the probe's brightness, the kit3 `lift` modelled) the median of its 3
                   samples has mean luma under DARK_MEAN, its 95th percentile under DARK_P95 and no lit block (12 x 8 blocks, the
                   brightest under DARK_BMAX); a black card (black over BLACK_CARD with crisp white: a list, a title, credits) and a night
                   shot by the footage brain pass (this never means no night shots). It asks for a brighter pick; allowed in
                   gate_allow.json with the reason when the line is about the dark.

How it sees: the gate's probe (gate.load_probe's layout {frame: items} and clips {frame: [clip lines]}), the composition's code (the
comment lines above each shot, as qa_cards reads `// card:`), the clips manifest ([gate] clips_json) for each clip's master and second,
the footage brain (kb/footage/brain/<master>.json: a span's time of day), the pictures' own pixels (cached under MEDIA/cache/qa_shots/
by file size and time), and the artwork index (the dhash of every file in the artwork folders, cached the same way).
The source's masters and its artwork and people folders are the creator's data: data/masters.json and data/artwork.json.

  PIPE tools/motion/qa_shots.py <video> [--probe <probe.jsonl>] [--src <code dir>] [--only dark,art,subject] [--dump] [--json <out>]
  exit 1 on a flag not allowed (gate_allow.json {"check", "key", "reason"}: the key is the picture's name, or "film" for ART_SHARE)
  In the gate: `import qa_shots; cd += qa_shots.gate_flags(v, lay, _cl)` beside B19/B20.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, FOOTAGE, KB, MEDIA, PUBLIC, TOOLS  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "pipeline"))
sys.path.insert(0, str(HERE))
from codefiles import code_files  # noqa: E402   with the subfolder files the film imports

FPS = 60
CACHE = Path(os.environ.get("QA_SHOTS_CACHE", str(MEDIA / "cache" / "qa_shots")))
BRAIN = KB / "footage" / "brain"
PROXIES = FOOTAGE / "index" / "proxies"


def _data(name, default):
    try:
        return json.loads((HERE / "data" / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# the source's masters (data/masters.json): {code: {"file": the master's file name as the clips manifest names it, "proxy": its 480p
# proxy in FOOTAGE/index/proxies, "picture": [x0, y0, x1, y1] the picture inside its bars, as fractions (a letterboxed master)}}
MASTER_DATA = _data("masters.json", {})
MASTERS = set(MASTER_DATA)
PROXY = {c: m["proxy"] for c, m in MASTER_DATA.items() if m.get("proxy")}
PIC = {c: tuple(m["picture"]) for c, m in MASTER_DATA.items() if m.get("picture")}
FILE_CODE = {m["file"]: c for c, m in MASTER_DATA.items() if m.get("file")}

# the artwork and people folders (data/artwork.json; relative paths are under FOOTAGE)
ART_DATA = _data("artwork.json", {})


def _dirs(key):
    return [Path(p) if Path(p).is_absolute() else FOOTAGE / p for p in ART_DATA.get(key, [])]


PEOPLE = _dirs("people")                 # the source's own pictures, one subfolder per person ("Anna Lee")
PEOPLE_ART = _dirs("people_art")         # key-art folders whose subfolders are named by the people they show ("Anna_and_Ben_Kitchen")
ART_ROOTS = _dirs("art") + [d for d in PEOPLE_ART if d not in _dirs("art")]
ART_GLOBS = [PUBLIC, "*/art"]            # a video's own downloaded key art
# the source's own screenshots (by their own file names) are never key art, whatever folder a video keeps them in: a video's art folder
# that holds screenshots beside the artwork would otherwise match each one against its own copy
SHOT_ROOTS = _dirs("screenshots")

# ---------------------------------------------------------------------------------------------------- the numbers
OFF_CENTRE = 0.22      # the subject's centre within the middle 44% of the width and height (the thirds' crossings, 0.167, pass)
CUT_MIN = 0.75         # at least this much of the subject's box on screen
SMALL_AREA = 0.015     # small = under 1.5% of the frame and ...
SMALL_H = 0.15         # ... under 15% of its height
DIM_SUBJECT = 30.0     # the subject's own mean luma on screen (0-255)
ZOOM_SCALE = 1.15      # a clip drawn this much bigger than the frame is zoomed (the house push ends at 1.02-1.05)
WINDOW_R = 0.60        # a clip whose first frame correlates under this with its master's frame there is a window of it
ART_BITS = 8           # dhash distance to an artwork file (copies and resizes measure 0-7; other pictures 14+)
ART_RUN_S = 20.0       # three artwork shots inside this many seconds is a run
ART_SHARE_MAX = 0.08   # artwork's share of the film's screen time
DARK_MEAN = 14.0       # murky shots measure 10-11; the darkest readable shots that aren't night or a black card ~17
DARK_P95 = 64.0
DARK_BMAX = 90.0
BLACK_CARD = (0.85, 120.0)   # black share over 0.85 and the 99th percentile over 120: white text or a logo on black
MIN_RUN = 30           # frames: a picture on screen for less than 0.5 s is not judged for DARK


def stem(p):
    return Path(str(p).replace("\\", "/")).stem


# ======================================================================================================================== caches
def _cache(name):
    p = CACHE / name
    try:
        return p, json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return p, {}


def _save(p, d):
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(d), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass


def file_id(p):
    try:
        st = Path(p).stat()
        return f"{st.st_size}:{st.st_mtime_ns}"
    except OSError:
        return "missing"


# ============================================================================================================== pixels on screen
LIFT = None


def lift_model():
    """(brightness, contrast) of kit3 Foot's `lift`, read from its own code (the probe records the brightness product only, `br`; a clip
    drawn at the lift's brightness gets its contrast too: with both, the model lands within 1 level of the render; the brightness alone
    reads 4-6 levels too bright)"""
    global LIFT
    if LIFT is None:
        LIFT = (None, 1.0)
        try:
            t = (HERE / "src/kit3/footage.tsx").read_text(encoding="utf-8")
            m = re.search(r"lift \? `brightness\(([\d.]+)\) contrast\(([\d.]+)\)", t)
            if m:
                LIFT = (float(m.group(1)), float(m.group(2)))
        except OSError:
            pass
    return LIFT


def grab_clip(path, sec, w=480):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, sec):.3f}", "-i", str(path), "-frames:v", "1", "-an", "-vf", f"scale={w}:-2",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    n = len(raw) // (w * 3)
    return np.frombuffer(raw[:n * w * 3], np.uint8).reshape(n, w, 3) if n >= 8 else None


IMGS = {}


def grab_img(path):
    k = str(path)
    if k not in IMGS:
        try:
            im = Image.open(path)
            im.draft("RGB", (1600, 1600))
            im = im.convert("RGB")
            w = min(1600, im.width)
            IMGS[k] = np.asarray(im.resize((w, max(1, round(w * im.height / im.width)))))
        except Exception:  # noqa: BLE001
            IMGS[k] = None
    return IMGS[k]


DIMS = {}


def dims(path, kind):
    """the picture file's own pixel size (an image's, a clip's frame)"""
    k = str(path)
    if k not in DIMS:
        DIMS[k] = None
        try:
            if kind == "img":
                with Image.open(path) as im:
                    DIMS[k] = im.size
            else:
                r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                    str(path)], capture_output=True, text=True).stdout.strip().split(",")
                DIMS[k] = (int(r[0]), int(r[1])) if len(r) == 2 and r[0].isdigit() else None
        except Exception:  # noqa: BLE001
            pass
    return DIMS[k]


def vis_rect(it, W, H):
    return (max(0.0, it["x"], it.get("cx0", 0)), max(0.0, it["y"], it.get("cy0", 0)),
            min(W, it["x"] + it["w"], it.get("cx1", W)), min(H, it["y"] + it["h"], it.get("cy1", H)))


def on_screen(arr, it, rect, br, out=(192, 108)):
    """the source pixels behind a screen rect (x0, y0, x1, y1) of picture item `it`, as the screen shows them (brightness, the lift)"""
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = rect
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None
    u0, u1 = (x0 - it["x"]) / it["w"], (x1 - it["x"]) / it["w"]
    v0, v1 = (y0 - it["y"]) / it["h"], (y1 - it["y"]) / it["h"]
    a = arr[int(max(0, v0) * h):max(int(max(0, v0) * h) + 1, int(min(1, v1) * h)), int(max(0, u0) * w):max(int(max(0, u0) * w) + 1, int(min(1, u1) * w))]
    if a.size == 0:
        return None
    rgb = np.asarray(Image.fromarray(a).resize(out), np.float32) * br
    lb, lc = lift_model()
    if lb and abs(br - lb) < 0.006:
        rgb = (np.clip(rgb, 0, 255) - 127.5) * lc + 127.5
    return np.clip(rgb, 0, 255)


def luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def light_stats(rgb):
    y = luma(rgb)
    p = np.percentile(y, [50, 95, 99])
    bh, bw = y.shape[0] // 8, y.shape[1] // 12
    blocks = y[:bh * 8, :bw * 12].reshape(8, bh, 12, bw).mean(axis=(1, 3))
    return {"mean": round(float(y.mean()), 2), "p50": round(float(p[0]), 1), "p95": round(float(p[1]), 1), "p99": round(float(p[2]), 1),
            "black": round(float((y < 8).mean()), 3), "bmax": round(float(blocks.max()), 1)}


class Pixels:
    """a picture's pixels at a probe frame, cached by file and second"""

    def __init__(self, pub, clips):
        self.pub, self.clips = Path(pub), clips
        self.path, self.data = _cache("pixels.json")
        self.dirty = 0

    def source(self, it, f):
        p = self.pub / str(it["t"])
        if it["k"] == "clip":
            s = next((c["s"] for c in self.clips.get(f, []) if str(c["src"]) == str(it["t"])), None)
            return p, s, (grab_clip(p, s) if s is not None and p.exists() else None)
        return p, None, (grab_img(p) if p.exists() else None)

    def stats(self, it, f, rect, W, H, tag="pic"):
        """light_stats of the picture under screen rect at frame f (None when its source can't be read)"""
        br = round((it.get("br") or 1.0) * it.get("op", 1.0), 3)
        p = self.pub / str(it["t"])
        s = None
        if it["k"] == "clip":
            s = next((c["s"] for c in self.clips.get(f, []) if str(c["src"]) == str(it["t"])), None)
            if s is None:
                return None
        rel = [round((rect[0] - it["x"]) / it["w"], 3), round((rect[1] - it["y"]) / it["h"], 3), round((rect[2] - it["x"]) / it["w"], 3),
               round((rect[3] - it["y"]) / it["h"], 3)]
        key = f"{tag}|{p.name}|{file_id(p)}|{'' if s is None else round(s, 2)}|{rel}|{br}"
        if key in self.data:
            return self.data[key]
        _, _, arr = self.source(it, f)
        if arr is None:
            return None
        rgb = on_screen(arr, it, rect, br)
        st = light_stats(rgb) if rgb is not None else None
        self.data[key] = st
        self.dirty += 1
        if self.dirty >= 100:
            self.save()
        return st

    def save(self):
        if self.dirty:
            _save(self.path, self.data)
            self.dirty = 0


# =============================================================================================================== frames and runs
def varea(it, W, H):
    x0, y0, x1, y1 = vis_rect(it, W, H)
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def frame_info(items, W, H):
    """(the frame's picture: the biggest lit sharp picture file or clip on 40%+ of the frame, not a dimmed ground; a page or card on
    screen; our own text or graphic on the picture)"""
    A = W * H
    lit = [it for it in items if it["op"] >= 0.5 and it.get("g") != "credit"]
    pics = [it for it in lit if it["k"] in ("img", "clip") and (it.get("bl") or 0) < 2 and (it.get("br") or 1.0) * it["op"] >= 0.7
            and varea(it, W, H) >= 0.4 * A]
    pic = max(pics, key=lambda it: varea(it, W, H)) if pics else None
    page = any(it["k"] == "img" and "/pages/" in str(it["t"]).replace("\\", "/") and varea(it, W, H) >= 0.08 * A for it in lit)
    over = False
    for it in lit:
        if it is pic or it.get("g") in ("name", "mark", "roll"):
            continue
        if it["k"] == "text" and (it.get("fs") or 0) >= 26:
            over = True
        elif it["k"] in ("box", "svg", "img", "clip") and 0.015 * A <= varea(it, W, H) and (pic is None or varea(it, W, H) < 0.9 * varea(pic, W, H)):
            over = True
    return pic, page, over


def picture_runs(layout, W, H):
    """[{k, t, f0, f1, frames: [f], plain: [f]}]: consecutive frames showing one picture as the frame's picture; `plain` = its frames with
    nothing of ours on it and no card"""
    runs, cur = [], None
    for f in sorted(layout):
        pic, page, over = frame_info(layout[f], W, H)
        key = (pic["k"], str(pic["t"])) if pic is not None and not page else None
        if cur and key == cur["key"] and f <= cur["f1"] + 2:
            cur["f1"] = f
        else:
            cur = {"key": key, "k": key[0] if key else None, "t": key[1] if key else None, "f0": f, "f1": f, "frames": [], "plain": []}
            runs.append(cur)
        cur["frames"].append(f)
        if key and not over:
            cur["plain"].append(f)
    return [r for r in runs if r["key"]]


def samples(fs, qs=(0.1, 0.5, 0.9)):
    """the frames at these fractions of fs, in the order given, each once"""
    out = []
    for q in qs:
        f = fs[min(len(fs) - 1, int(len(fs) * q))] if fs else None
        if f is not None and f not in out:
            out.append(f)
    return out


def item_at(layout, f, k, t):
    """the picture's item on frame f: the sharp one when the file is drawn twice (a Stage's blurred ground of the same picture under its
    card: the ground, at 1.07x the frame, would read a zoomed card's centred subject as small and off centre), the biggest of those, as
    frame_info picks the frame's picture"""
    its = [it for it in layout.get(f, []) if it["k"] == k and str(it["t"]) == t and it["op"] >= 0.5]
    if not its:
        return None
    sharp = [it for it in its if (it.get("bl") or 0) < 2]
    return max(sharp or its, key=lambda it: it["w"] * it["h"])


# ============================================================================================================== the code's lines
ENTRY = re.compile(r"^\s*(?:shot|ft2?|page|parts)\(|\{at:\s*.+?,\s*el:")
NUM = r"(-?\d+(?:\.\d+)?)"
SUBJ = re.compile(rf"^subject:\s*(.*?)\s*{NUM}\s+{NUM}\s+{NUM}\s+{NUM}(?:\s*->\s*{NUM}\s+{NUM}\s+{NUM}\s+{NUM})?\s*$")


QUOTED = re.compile(r"\"([^\"\n]{2,160})\"|'([^'\n]{2,160})'|`([^`\n]{2,160})`")
PIC_FILE = re.compile(r"""['"`][^'"`\s]+?\.(?:jpe?g|png|webp)['"`]""", re.I)


def _comment_above(lines, i):
    k, com = i - 1, []
    while k >= 0 and lines[k].strip().startswith("//"):
        com.insert(0, lines[k].strip().lstrip("/ ").strip())
        k -= 1
    return com


def _subjects(com):
    subs, art = [], ""
    for c in com:
        m = SUBJ.match(c)
        if m:
            g = m.groups()
            box = tuple(float(x) for x in g[1:5])
            end = tuple(float(x) for x in g[5:9]) if g[5] is not None else None
            subs.append((g[0].strip(), box, end))
        elif c.lower().startswith("art:"):
            art = c.split(":", 1)[1].strip()
    return subs, art


def code_entries(src_dir):
    """[{file, line, names: {picture stems}, subjects: [(label, box, box_end)], art: reason, comment}] for every shot entry of the
    composition's code (the comment lines right above it, as qa_cards reads them), in its folder and the subfolder files it imports
    (codefiles.py); then a PIECE entry for every other line that names a picture file and has its own `// subject:` or `// art:` above
    it (rebuilt shots' pieces in a subfolder name their pictures inside the piece, `{at: x, src: I('a.jpg'), ...}`, where no shot
    entry's lines reach). Shot entries come first, so a shot's own subject line wins over a piece's."""
    out, pieces = [], []
    for f in code_files(src_dir):
        name = f.relative_to(Path(src_dir).resolve()).as_posix()
        lines = f.read_text(encoding="utf-8").splitlines()
        idx = [i for i, ln in enumerate(lines) if ENTRY.search(ln) and not ln.lstrip().startswith(("const ", "export const ", "function ", "//"))]
        for n, i in enumerate(idx):
            j = idx[n + 1] if n + 1 < len(idx) else min(len(lines), i + 40)
            body = "\n".join(ln for ln in lines[i:j] if not ln.lstrip().startswith("//"))
            names = {stem(next(x for x in m if x)) for m in QUOTED.findall(body)}
            com = _comment_above(lines, i)
            subs, art = _subjects(com)
            out.append({"file": name, "line": i + 1, "names": names, "subjects": subs, "art": art, "anchor": lines[i].strip()[:80], "comment": com,
                        "kit3d": re.findall(r"<(Parallax25D)\b[^>]*?src=\{?['\"`]([^'\"`]+)['\"`]", body)})
        heads = set(idx)
        for i, ln in enumerate(lines):
            if i == 0 or i in heads or ln.lstrip().startswith("//") or not lines[i - 1].strip().startswith("//"):
                continue
            subs, art = _subjects(_comment_above(lines, i))
            if not subs and not art:
                continue
            # the picture on this line or on the lines of the same statement after it (`<Still` with its src one line down, a list of
            # pieces over several lines): up to a blank line, a comment, the next shot or a statement's end
            part = []
            for ln2 in lines[i:i + 12]:
                if part and (not ln2.strip() or ln2.lstrip().startswith("//") or ENTRY.search(ln2)):
                    break
                part.append(ln2.split("//", 1)[0])
                if part[-1].rstrip().endswith(";"):
                    break
            code = "\n".join(part)
            if not PIC_FILE.search(code):
                continue
            pieces.append({"file": name, "line": i + 1, "names": {stem(next(x for x in m if x)) for m in QUOTED.findall(code)},
                           "subjects": subs, "art": art, "anchor": ln.strip()[:80], "kit3d": [], "piece": True})
    return out + pieces


def entry_for(entries, t):
    """the code entries that name picture t (by its file stem)"""
    s = stem(t)
    return [e for e in entries if s in e["names"]]


def per_shot(runs, shots, entries):
    """a picture's run split at the shot cuts, each part tied to ITS shot's code entry (two shots in a row can show the same picture file,
    a wide still then a zoom onto one part of it: one run over both would take the first shot's subject line whole and read the zoom as
    the subject cut by the frame). The shot list and the code's shot entries pair by order only when they count the same; otherwise the
    runs stay whole and subject_for picks by the file."""
    se = [e for e in entries if not e.get("piece")]
    if not shots or len(se) != len(shots):
        if shots:   # said, never silent: a count off by one sends every subject back to the file's comments
            by = {}
            for e in se:
                by[e["file"]] = by.get(e["file"], 0) + 1
            print(f"  ! per-shot subjects OFF: {len(se)} shot entries in the code ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))}) "
                  f"vs {len(shots)} shots in the film: each run falls back to its picture's comments in any file; make a shot that "
                  f"isn't a `shot(` line one (or give it its own line)", file=sys.stderr)
        return runs
    # in film order, not file order (a composition that sorts a prototype's file and its sections' files by time would otherwise pair
    # every shot with the comment of one many places off): each entry's beat from its anchor (an anchor with none, `shot(S52_AT(), ...)`,
    # keeps the beat before it in its file), then its line
    key, last = {}, {}
    for n, e in enumerate(se):
        m = re.search(r"['\"]S(\d+)", e["anchor"])
        b = int(m.group(1)) if m else last.get(e["file"], -1)
        last[e["file"]] = b
        key[n] = (b, e["file"], e["line"])
    se = [se[n] for n in sorted(range(len(se)), key=lambda n: key[n])]
    starts = [s["at"] for s in shots]
    out = []
    for r in runs:
        parts = {}
        for f in r["frames"]:
            i = max(0, sum(1 for a in starts if a <= (f + 0.5) / FPS) - 1)
            parts.setdefault(i, []).append(f)
        for i, fs in sorted(parts.items()):
            q = dict(r, frames=fs, f0=fs[0], f1=fs[-1], plain=[f for f in r["plain"] if f in set(fs)])
            if stem(r["t"]) in se[i]["names"]:
                q["entry"] = se[i]
            out.append(q)
    return out


def subject_for(entries, t, entry=None):
    s = stem(t)
    if entry is not None:   # the run's own shot (per_shot): its subject line, or none (SUBJECT_MISSING names that shot)
        own = [x for x in entry["subjects"] if x[0] == s]
        anyl = [x for x in entry["subjects"] if x[0] not in entry["names"]]
        return ((own or anyl)[0] if (own or anyl) else None), entry
    for e in entry_for(entries, t):
        own = [x for x in e["subjects"] if x[0] == s]
        anyl = [x for x in e["subjects"] if x[0] not in e["names"]]
        if own or anyl:
            return (own or anyl)[0], e
    return None, (entry_for(entries, t) or [None])[0]


# ============================================================================================================= masters and brain
RECS = {}


def brain_records(code):
    if code not in RECS:
        try:
            RECS[code] = json.loads((BRAIN / f"{code}.json").read_text(encoding="utf-8"))["shots"]
        except (OSError, ValueError):
            RECS[code] = []
    return RECS[code]


def brain_at(code, t):
    return next((r for r in brain_records(code) if r.get("in", 0) <= t < r.get("out", 0)), None)


def master_of(name, manifest):
    """(master code, its second at the clip's start) for a clip cut from one of the source's masters, else (None, None)"""
    e = manifest.get(name)
    if not e or len(e) < 2:
        return None, None
    code = str(e[0])
    code = FILE_CODE.get(code, code)
    if code not in MASTERS or not isinstance(e[1], (int, float)):
        return None, None
    return code, float(e[1])


def gray(path, sec, w=64, h=36, vf=""):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, sec):.3f}", "-i", str(path), "-frames:v", "1", "-an", "-vf",
                          f"{vf}scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w).astype(np.float32) if len(raw) >= w * h else None


def is_window(clip_path, code, t_in, cache):
    """True when the clip's first frame is a crop window of its master's frame at t_in (a detail zoomed to 2x), False when it is the
    master's whole picture, filled to 16:9 or whole with its bars (the prep may keep a master's letterbox, so both are compared), None
    when unread. Read on the 480p proxy (the brain's), cached by the clip file."""
    key = f"{Path(clip_path).name}|{file_id(clip_path)}|{code}|{t_in:.3f}|bars"
    if key in cache:
        return cache[key]
    if code not in PROXY:
        return None
    proxy = PROXIES / PROXY[code]
    if not proxy.exists():
        return None
    x0, y0, x1, y1 = PIC.get(code, (0.0, 0.0, 1.0, 1.0))
    # the master's picture inside its bars, filled to 16:9 round its centre (prep's scale=increase + crop); the masters are 16:9 frames,
    # so the picture's shape against 16:9 is pw / ph
    pw, ph = x1 - x0, y1 - y0
    ar = pw / ph
    if ar > 1:
        cw, chh = pw / ar, ph
    else:
        cw, chh = pw, ph * ar
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    vf = f"crop=iw*{cw:.5f}:ih*{chh:.5f}:iw*{cx - cw / 2:.5f}:ih*{cy - chh / 2:.5f},"
    rs = []
    for dt in (0.0, 0.1):   # two moments, the better one counts: a seek a frame off or a flash doesn't make a window
        a = gray(clip_path, dt)
        for f in (vf, ""):   # the filled crop, or the whole frame with its bars
            b = gray(proxy, t_in + dt + 0.017, vf=f)
            if a is not None and b is not None and a.std() >= 2 and b.std() >= 2:
                rs.append(float(np.corrcoef(a.ravel(), b.ravel())[0, 1]))
    if not rs:
        cache[key] = None
        return None
    cache[key] = bool(max(rs) < WINDOW_R)
    return cache[key]


# ================================================================================================================== the artwork
def art_index():
    """[(path, dhash, people)] of every key-art file (cached by file size and time)"""
    p, cache = _cache("art_index.json")
    files = []
    for root in ART_ROOTS:
        if root.exists():
            files += [x for x in root.rglob("*") if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and not x.name.startswith("_")]
    base, pat = ART_GLOBS
    shots = {x.stem.lower() for r in SHOT_ROOTS if r.exists() for x in r.rglob("*") if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")}
    for d in sorted(Path(base).glob(pat)) if Path(base).exists() else []:
        files += [x for x in d.iterdir() if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and not x.name.startswith("_")
                  and x.stem.lower() not in shots]
    out, dirty = [], False
    for f in files:
        k = f"{f}|{file_id(f)}"
        if k not in cache:
            try:
                cache[k] = dhash(f)
            except Exception:  # noqa: BLE001
                cache[k] = None
            dirty = True
        if cache[k] is not None:
            out.append((str(f), cache[k], characters(f)))
    if dirty:
        _save(p, cache)
    return out


def dhash(path):
    im = Image.open(path)
    try:
        im.draft("L", (64, 36))
    except Exception:  # noqa: BLE001
        pass
    g = np.asarray(im.convert("L").resize((9, 8), Image.LANCZOS), np.int16)
    bits = (g[:, :8] > g[:, 1:]).ravel()
    return int("".join("1" if b else "0" for b in bits), 2)


PEOPLE_NAMES = None


def people():
    """first names of the people the source's own pictures show (the people folders: 'Anna Lee' -> 'anna')"""
    global PEOPLE_NAMES
    if PEOPLE_NAMES is None:
        PEOPLE_NAMES = set()
        for d in PEOPLE:
            if d.exists():
                for x in d.iterdir():
                    if x.is_dir() and " and " not in x.name:
                        PEOPLE_NAMES.add(x.name.split()[0].lower())
    return PEOPLE_NAMES


def characters(path):
    """the people a key art shows, by its folder's name (Anna_and_Ben_Kitchen -> anna, ben), for the people-art folders; other art: none"""
    p = Path(path)
    if not any(root in p.parents for root in PEOPLE_ART):
        return []
    toks = {t.lower() for t in re.split(r"[_\s]+", p.parent.name)}
    return sorted(toks & people())


ARTS = None
ART_HIT = {}


def art_match(path):
    """the key-art file a picture is (dhash within ART_BITS), with its people, or None"""
    global ARTS
    k = str(path)
    if k in ART_HIT:
        return ART_HIT[k]
    if ARTS is None:
        ARTS = art_index()
    ART_HIT[k] = None
    try:
        h = dhash(path)
    except Exception:  # noqa: BLE001
        return None
    best = min(ARTS, key=lambda a: bin(a[1] ^ h).count("1"), default=None)
    if best and bin(best[1] ^ h).count("1") <= ART_BITS:
        ART_HIT[k] = (best[0], best[2])
    return ART_HIT[k]


# ====================================================================================================================== the checks
def mmss(f):
    t = f / FPS
    return f"{int(t // 60)}:{t % 60:05.2f}"


def check_dark(runs, layout, px, manifest, W, H, rows=None):
    flags = []
    for r in runs:
        fs = r["plain"]
        if len(fs) < MIN_RUN:
            continue
        st = []
        for i, f in enumerate(samples(fs, (0.5, 0.2, 0.8))):
            it = item_at(layout, f, r["k"], r["t"])
            if it is None:
                continue
            s = px.stats(it, f, vis_rect(it, W, H), W, H)
            if s:
                st.append(s)
            if i == 0 and s and s["mean"] >= 2 * DARK_MEAN and s["bmax"] >= DARK_BMAX:   # plainly lit: no need for the other samples
                break
        if not st:
            continue
        m = {k: float(np.median([s[k] for s in st])) for k in st[0]}
        name = stem(r["t"])
        night = None
        if r["k"] == "clip":
            code, t_in = master_of(name, manifest)
            if code:
                s0 = next((c["s"] for c in px.clips.get(fs[len(fs) // 2], []) if str(c["src"]) == r["t"]), 0.0)
                rec = brain_at(code, t_in + (s0 or 0.0))
                night = rec.get("time") if rec else None
        black_card = m["black"] >= BLACK_CARD[0] and m["p99"] >= BLACK_CARD[1]
        dark = m["mean"] < DARK_MEAN and m["p95"] < DARK_P95 and m["bmax"] < DARK_BMAX
        why = ("black card" if black_card else "night (footage brain)" if night == "night" else "")
        if rows is not None:
            rows.append((r["f0"], r["f1"], name, m, night, "DARK" if dark and not why else (why if dark else "")))
        if dark and not why:
            flags.append({"check": "DARK", "key": name, "at": fs[0], "to": fs[-1],
                          "what": f"{name} reads murky on screen: mean light {m['mean']:.0f} of 255, 95% of it under {m['p95']:.0f}, its brightest "
                                  f"block {m['bmax']:.0f} (murky = under {DARK_MEAN:.0f} / {DARK_P95:.0f} / {DARK_BMAX:.0f}; the brain's time: "
                                  f"{night or 'not in the brain'}): pick a brighter span or picture that shows the words; a lift won't "
                                  f"do it (kit3's lift darkens every pixel under 26), or allow it with the reason when the line is about the dark"})
    return flags


def check_subject(runs, layout, px, entries, manifest, W, H, rows=None):
    flags = []
    wpath, wcache = _cache("windows.json")
    seen_missing = set()
    for r in runs:
        name = stem(r["t"])
        fs = r["frames"]
        if len(fs) < 12:
            continue
        mid = item_at(layout, fs[len(fs) // 2], r["k"], r["t"])
        if mid is None:
            continue
        size = dims(px.pub / r["t"], r["k"])
        if not size or mid["h"] < 2 or abs((mid["w"] / mid["h"]) / (size[0] / size[1]) - 1) > 0.02:
            continue   # unreadable, or drawn at another shape than its file (a split screen's half, object-fit cover): no linear mapping
        if r["k"] == "img" and varea(mid, W, H) < 0.9 * W * H:
            continue   # a picture placed on a stage (a cut-out, a logo, a row), not a still filling the frame
        import gate
        if gate.built_still(layout.get(fs[len(fs) // 2], [])):
            continue   # a built graphic's own picture: its dimmed or blurred ground, or under its panels; the graphic is what's framed
        zoom = None
        if r["k"] == "clip":
            scale = max(it["w"] for it in (item_at(layout, f, r["k"], r["t"]) for f in samples(fs)) if it) / W
            if scale >= ZOOM_SCALE:
                zoom = f"drawn at {scale:.2f}x the frame"
            else:
                code, t_in = master_of(name, manifest)
                if code and is_window(px.pub / r["t"], code, t_in, wcache):
                    zoom = f"a window of {code} {t_in:.2f}"
            if not zoom:
                continue
        sub, e = subject_for(entries, r["t"], r.get("entry"))
        if sub is None:
            if name not in seen_missing:
                seen_missing.add(name)
                where = f"{e['file']}:{e['line']}" if e else "its shot"
                flags.append({"check": "SUBJECT_MISSING", "key": name, "at": fs[0], "to": fs[-1],
                              "what": f"{name} ({'a still' if r['k'] == 'img' else 'a clip, ' + zoom}) has no subject box: write "
                                      f"'// subject: <label> x y w h' (the named thing in the picture file's pixels) above {where}"})
            continue
        label, box, end = sub
        nw, nh = size
        bad, notes = [], []
        # a fixed box at 10%, 50% and 90% of the shot; a moving one (`->`, a glide) at the shot's first frame and its last
        sm = samples(fs) if end is None else samples(fs, (0.0, 0.999))
        # a showing zoom (it opens on the whole picture and moves onto its subject) is judged where it lands, not at 10% of the shot,
        # before the zoom
        ws = [(f, it["w"]) for f in fs for it in [item_at(layout, f, r["k"], r["t"])] if it]
        if end is None and ws and max(w for _, w in ws) >= 1.3 * max(1.0, min(w for _, w in ws)):
            top = max(w for _, w in ws)
            land = next(f for f, w in ws if w >= 0.97 * top)
            rest = [f for f in fs if f >= land]
            sm = samples(rest, (0.0, 0.5, 0.999)) if len(rest) >= 3 else [rest[-1]]
        for i, f in enumerate(sm):
            it = item_at(layout, f, r["k"], r["t"])
            if it is None:
                continue
            b = end if (end is not None and i == len(sm) - 1) else box
            sx0, sy0 = it["x"] + b[0] * it["w"] / nw, it["y"] + b[1] * it["h"] / nh
            sx1, sy1 = sx0 + b[2] * it["w"] / nw, sy0 + b[3] * it["h"] / nh
            fx0, fy0, fx1, fy1 = vis_rect(it, W, H)
            vx0, vy0, vx1, vy1 = max(sx0, fx0), max(sy0, fy0), min(sx1, fx1), min(sy1, fy1)
            full = max(1e-6, (sx1 - sx0) * (sy1 - sy0))
            va = max(0.0, vx1 - vx0) * max(0.0, vy1 - vy0)
            if va <= 0:
                bad.append(f)
                notes.append((f, "off the frame", None))
                continue
            cx, cy = (vx0 + vx1) / 2 / W, (vy0 + vy1) / 2 / H
            frac, area, hh = va / full, va / (W * H), (vy1 - vy0) / H
            st = px.stats(it, f, (vx0, vy0, vx1, vy1), W, H, tag="subj")
            fr = px.stats(it, f, (fx0, fy0, fx1, fy1), W, H)
            why = []
            # a readout zoomed into in its own corner is as central as the picture's edges allow: qa_still_words.edge_bound, the same
            # exemption as MARK_CORNER's
            from qa_still_words import edge_bound
            if (abs(cx - 0.5) > OFF_CENTRE or abs(cy - 0.5) > OFF_CENTRE) and not edge_bound(layout, f, cx, cy, W, H, tol=OFF_CENTRE):
                why.append(f"off centre ({cx:.0%} across, {cy:.0%} down)")
            if frac < CUT_MIN:
                why.append(f"cut by the frame ({frac:.0%} on screen)")
            # a small thing under the spot look's light (the rest of the picture darkened round it) is the one lit thing on screen,
            # found at a glance
            spot = any(m.get("sp") and m.get("g") == "mark" and m["x"] < vx1 and vx0 < m["x"] + m["w"] and m["y"] < vy1 and vy0 < m["y"] + m["h"]
                       for m in layout.get(f, []))
            if area < SMALL_AREA and hh < SMALL_H and not spot:
                why.append(f"small ({area:.1%} of the frame, {hh:.0%} of its height)")
            if st and st["mean"] < DIM_SUBJECT:
                why.append(f"dim (its light {st['mean']:.0f})")
            info = (f"at {cx:.0%} across, {cy:.0%} down, {frac:.0%} on screen, {area:.0%} of the frame"
                    + (f", its light {st['mean']:.0f} (the frame {fr['mean']:.0f})" if st and fr else ""))
            notes.append((f, ", ".join(why), info))
            if why:
                bad.append(f)
        if rows is not None:
            rows.append((r["f0"], r["f1"], name, label, [n[2] or n[1] for n in notes], len(bad)))
        need = 2 if end is None and len(sm) >= 3 else 1
        if len(bad) >= need:
            f0 = bad[0]
            why = next(n[1] for n in notes if n[0] == f0)
            info = next((n[2] for n in notes if n[0] == f0 and n[2]), "")
            flags.append({"check": "SUBJECT_LOST", "key": name, "at": fs[0], "to": fs[-1],
                          "what": f"{name}: the subject{(' (' + label + ')') if label else ''} is not found at a glance: {why}; {info}. Frame the "
                                  f"picture on it (its region or push), or pick a picture where it is big, central and lit"})
    _save(wpath, wcache)
    return flags


def check_art(runs, layout, entries, v_pub, shots, total_s, W, H, rows=None):
    """artwork shots on the film: pictures matching the key-art index, plus kit3d pieces (invisible to the probe) made from key art"""
    arts = []
    for r in runs:
        if r["k"] != "img" or r["f1"] - r["f0"] + 1 < 12:
            continue
        m = art_match(Path(v_pub) / r["t"])
        if m:
            arts.append({"at": r["f0"], "to": r["f1"], "name": stem(r["t"]), "art": m[0], "who": m[1], "t": r["t"]})
    # kit3d pieces: the probe draws no picture for them; their shots come from the probe's shot list and their sources from the code,
    # in order (the n-th Parallax25D shot of the film is the n-th Parallax25D of the code)
    k3 = [s for s in shots if "Parallax25D" in (s.get("names") or [])]
    srcs = [(e, src) for e in entries for kind, src in e["kit3d"]]
    for s, (e, src) in zip(k3, srcs if len(srcs) == len(k3) else []):
        f = next((x for x in sorted(Path(v_pub).joinpath(src).parent.glob(Path(src).name + ".*"))
                  if x.suffix.lower() in (".jpg", ".png") and x.stem == Path(src).name), None)
        m = art_match(f) if f else None
        if m:
            arts.append({"at": round(s["at"] * FPS), "to": round(s["end"] * FPS) - 1, "name": Path(src).name, "art": m[0], "who": m[1],
                         "t": src})
    arts.sort(key=lambda a: a["at"])
    if rows is not None:
        rows.extend(arts)
    flags = []
    for a in arts:
        e = entry_for(entries, a["t"])
        reason = next((x["art"] for x in e if x["art"]), "")
        if a["who"] and not reason:
            flags.append({"check": "ART_OVER_REAL", "key": a["name"], "at": a["at"], "to": a["to"],
                          "what": f"{a['name']} is the source's key art ({Path(a['art']).parent.name}) of {', '.join(w.title() for w in a['who'])}, "
                                  f"whom the source's own pictures show: use the real picture, or write '// art: <why>' above the shot"})
    for i in range(2, len(arts)):
        if (arts[i]["at"] - arts[i - 2]["at"]) / FPS < ART_RUN_S:
            a = arts[i]
            flags.append({"check": "ART_CLOSE", "key": a["name"], "at": a["at"], "to": a["to"],
                          "what": f"a third artwork shot inside {ART_RUN_S:.0f} s ({', '.join(x['name'] + ' at ' + mmss(x['at']) for x in arts[i - 2:i + 1])}): "
                                  f"artwork is a rare variety shot, never a run"})
    dur = sum(a["to"] - a["at"] + 1 for a in arts) / FPS
    if total_s and dur / total_s > ART_SHARE_MAX:
        flags.append({"check": "ART_SHARE", "key": "film", "at": arts[0]["at"], "to": arts[-1]["to"],
                      "what": f"artwork holds {dur:.1f} s of {total_s:.1f} s ({dur / total_s:.0%}, over {ART_SHARE_MAX:.0%}): {len(arts)} artwork shots"})
    return flags


# ======================================================================================================================== the gate
def run(v, layout, clips, only=("dark", "art", "subject"), src_dir=None, shots=None, dump=None):
    W, H = 1920, 1080
    try:
        import gate
        W, H = gate.FRAME
    except Exception:  # noqa: BLE001
        pass
    manifest = {}
    try:
        import gate
        manifest = gate.load_manifest((v.section("gate") or {}).get("clips_json"))
    except Exception:  # noqa: BLE001
        pass
    entries = code_entries(src_dir or (HERE / "src" / v.src))
    if shots is None:
        sj = v.pipe_dir / f"shots_{v.comp}.json"
        try:
            d = json.loads(sj.read_text(encoding="utf-8"))
            shots, total = d["shots"], float(d.get("seconds") or 0)
        except (OSError, ValueError, KeyError):
            shots, total = [], 0.0
    else:
        shots, total = shots
    if not total and layout:
        total = (max(layout) + 1) / FPS
    runs = picture_runs(layout, W, H)
    px = Pixels(v.pub, clips)
    flags = []
    if "dark" in only:
        flags += check_dark(runs, layout, px, manifest, W, H, None if dump is None else dump.setdefault("dark", []))
    if "subject" in only:
        flags += check_subject(per_shot(runs, shots, entries), layout, px, entries, manifest, W, H,
                               None if dump is None else dump.setdefault("subject", []))
    if "art" in only:
        flags += check_art(runs, layout, entries, v.pub, shots, total, W, H, None if dump is None else dump.setdefault("art", []))
    px.save()
    return sorted(flags, key=lambda x: x["at"])


def gate_flags(v, layout=None, clips=None):
    """the checks for gate.py, on the probe the gate already loaded: layout {frame: items}, clips {frame: [clip lines]} (gate.load_probe's
    shapes). The gate's own allows (gate_allow.json) and sign-offs apply to these flags like to its own."""
    if layout is None:
        import gate
        clips, layout = gate.load_probe(v.pipe_dir / "gate" / "probe.jsonl")
    return run(v, layout, clips or {})


# ============================================================================================================================ main
def allowed(folder, flags):
    p = folder / "gate_allow.json" if folder else None
    allow = json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else []
    keep, ok = [], []
    for fl in flags:
        a = next((x for x in allow if x["check"] == fl["check"] and (x["key"] in fl["key"] or x["key"] in fl["what"]) and x.get("reason")
                  and (not x.get("frames") or not isinstance(fl.get("at"), (int, float)) or x["frames"][0] <= fl["at"] <= x["frames"][1])), None)
        (ok if a else keep).append((fl, a))
    return [k for k, _ in keep], ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--probe", help="a probe.jsonl (default: the video's gate probe)")
    ap.add_argument("--src", help="the composition's code folder (default: video.toml's)")
    ap.add_argument("--shots", help="the probe's shots json (default: <video media folder>/pipeline/shots_<comp>.json)")
    ap.add_argument("--pub", help="the public dir the pictures are read from (default: video.toml's)")
    ap.add_argument("--only", default="dark,art,subject")
    ap.add_argument("--dump", action="store_true", help="print every judged picture's numbers (the thresholds' calibration)")
    ap.add_argument("--json", help="write the flags and the dump here")
    a = ap.parse_args()
    from common import Video, find_video
    import gate
    folder = find_video(a.video)
    v = Video(folder)
    if a.pub:
        v.pub = Path(a.pub)
    probe = Path(a.probe) if a.probe else v.pipe_dir / "gate" / "probe.jsonl"
    clips, layout = gate.load_probe(probe)
    print(f"probe: {len(layout)} frames ({probe})")
    shots = None
    if a.shots:
        d = json.loads(Path(a.shots).read_text(encoding="utf-8"))
        shots = (d["shots"], float(d.get("seconds") or 0))
    dump = {} if (a.dump or a.json) else None
    flags = run(v, layout, clips, tuple(a.only.split(",")), Path(a.src) if a.src else None, shots, dump)
    if a.dump:
        for f0, f1, name, m, night, verdict in sorted(dump.get("dark", []), key=lambda x: x[3]["mean"])[:40]:
            print(f"  dark? {mmss(f0)}-{mmss(f1 + 1)} {name[:34]:34s} mean {m['mean']:5.1f} p95 {m['p95']:5.1f} p99 {m['p99']:5.1f} black {m['black']:.2f} "
                  f"bmax {m['bmax']:5.1f}  time {night or '-':7s} {verdict}")
        for f0, f1, name, label, notes, nbad in dump.get("subject", []):
            print(f"  subject {mmss(f0)} {name[:30]:30s} {label[:20]:20s} {nbad} bad | " + " | ".join(str(n) for n in notes))
        for x in dump.get("art", []):
            print(f"  art {mmss(x['at'])}-{mmss(x['to'] + 1)} {x['name'][:30]:30s} <- {Path(x['art']).parent.name}/{Path(x['art']).name}  {x['who']}")
    keep, ok = allowed(folder, flags)
    for fl, al in ok:
        print(f"allowed {fl['check']} {mmss(fl['at'])}: {fl['what'][:140]}\n        ({al['reason'][:160]})")
    for fl in keep:
        print(f"{fl['check']:16s} {mmss(fl['at'])}-{mmss(fl['to'] + 1)}  {fl['what']}")
    print(f"{len(keep)} flag(s) ({len(ok)} allowed)")
    if a.json:
        Path(a.json).write_text(json.dumps({"flags": keep, "allowed": [f for f, _ in ok],
                                            "dump": {k: [list(x) if isinstance(x, tuple) else x for x in vv] for k, vv in (dump or {}).items()}},
                                           indent=1, default=str), encoding="utf-8")
    return 1 if keep else 0


if __name__ == "__main__":
    sys.exit(main())
