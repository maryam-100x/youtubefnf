"""Shared pieces of the footage brain (kb/footage/brain/): the sources, where their frames come from, ids, and frame grabs.

The brain is a one-time, vision-built index of every shot the creator owns (their source videos, their clip libraries, their stills),
searched afterwards with no model at all: find_shot.py searches it (keywords + local embeddings on the CPU), brain_to_shot.py turns a
hit into a curate.py shot or a long-form Foot line. kb/footage/README.md is the method.

Sources: kb/footage/sources.json, filled by the creator (the README shows an entry). Each has a short code (its `key`) and a kind:
  video    one full-quality source video (a "master"): `file`, optional `proxy`, `title`, `pic` (the picture inside the frame as
           fractions x0, y0, x1, y1 when it is letterboxed; a 9:16 window must stay inside it)
  library  a folder of clips; each file is its own source, a shot id is "<code>/<stem>@<in s>"
  stills   a folder of pictures; `variants` groups one artwork's sizes (_landscape, _portrait ...), `art` marks illustrated art (it
           ranks lower unless the line asks for art), `skip_copies_of` names stills keys whose files (same name and size) it leaves out
A relative path is under FOOTAGE; an absolute one is used as written. Any source may carry `art: true`.
Times are seconds of the file; frames are the file's own frame numbers (0-based) at its own frame rate; a master's 480p proxy
(FOOTAGE/index/proxies/<stem>_480p.mp4, made by `brain_cuts.py proxy <key>`) shares its timeline frame for frame (same frame count, both
start at pts 0).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, FOOTAGE, KB, MEDIA, MODELS, PUBLIC, REPO  # noqa: E402,F401

BRAIN = KB / "footage" / "brain"                 # the index (git)
SOURCES = KB / "footage" / "sources.json"        # the creator's sources
CATALOGUE = KB / "footage" / "catalogue.json"    # the footage catalogue (tools/footage/catalogue.py)
NAMES = KB / "footage" / "names.json"            # {"alias as written, lower case": "the name records use"}
SYNONYMS = KB / "footage" / "synonyms.json"      # {"a word of the creator's niche": "the word records use"} (find_shot.py)
LEDGER = KB / "ASSET_LEDGER.json"                # what each delivered edit played ("used in")
WORK = FOOTAGE / "index" / "brain"               # frames, strips, sheets, scratch (not git)
PROXY_DIR = FOOTAGE / "index" / "proxies"
PEOPLE = FOOTAGE / "people"                      # one folder of face pictures per named person (face labels)
FULL = (0.0, 0.0, 1.0, 1.0)


def _path(p):
    p = Path(p).expanduser()
    return p if p.is_absolute() else FOOTAGE / p


def _load():
    try:
        raw = json.loads(SOURCES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = []
    masters, libs, stills, opts, art = {}, {}, {}, {}, set()
    for e in raw if isinstance(raw, list) else []:
        key, kind = e["key"], e.get("kind", "video")
        if e.get("art"):
            art.add(key)
        opts[key] = e
        if kind == "video":
            f = _path(e["file"])
            masters[key] = dict(file=f, proxy=_path(e["proxy"]) if e.get("proxy") else PROXY_DIR / f"{f.stem}_480p.mp4",
                                title=e.get("title", key), pic=tuple(e.get("pic", FULL)))
        elif kind == "library":
            libs[key] = _path(e["folder"])
        elif kind == "stills":
            stills[key] = _path(e["folder"])
    return masters, libs, stills, opts, art


MASTERS, LIBS, STILLS, OPTS, ART = _load()
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm")


def probe(path):
    """(width, height, fps, frames, duration) of a video file."""
    o = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_packets,duration", "-of", "json", str(path)], capture_output=True, text=True).stdout
    s = json.loads(o)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    fps = float(a) / float(b)
    n = int(s["nb_read_packets"])
    return int(s["width"]), int(s["height"]), fps, n, float(s.get("duration") or n / fps)


def size(path):
    """(width, height) of a video file, without counting its packets."""
    o = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(path)],
                       capture_output=True, text=True).stdout
    s = json.loads(o)["streams"][0]
    return int(s["width"]), int(s["height"])


def lib_files(code):
    d = LIBS[code]
    return sorted(p for p in d.iterdir() if p.suffix.lower() in VIDEO_EXT) if d.exists() else []


def sources():
    """Every video source as (key, path, proxy-or-None): the masters by code, the library clips by code/stem."""
    out = []
    for k, m in MASTERS.items():
        out.append((k, m["file"], m["proxy"]))
    for code in LIBS:
        for p in lib_files(code):
            out.append((f"{code}/{p.stem}", p, None))
    return out


def source_path(key):
    if key in MASTERS:
        return MASTERS[key]["file"]
    code, stem = key.split("/", 1)
    for p in LIBS[code].iterdir():
        if p.stem == stem:
            return p
    raise FileNotFoundError(key)


def proxy_or_file(key):
    """A master's 480p proxy when it has been made, else the file itself (a library clip is always its own file)."""
    if key in MASTERS and Path(MASTERS[key]["proxy"]).exists():
        return MASTERS[key]["proxy"]
    return source_path(key)


def pic_of(key):
    return MASTERS[key]["pic"] if key in MASTERS else FULL


def grab(path, t, w, h, vf=""):
    """One RGB frame of `path` at second t, scaled to w x h (PIL Image); red when the grab fails."""
    from PIL import Image
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, t):.4f}", "-i", str(path), "-frames:v", "1", "-vf", f"{vf}scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (w, h), raw) if len(raw) == w * h * 3 else Image.new("RGB", (w, h), (200, 30, 30))


def grab_run(path, t, n, w, h):
    """n consecutive frames from second t (a strip around a cut), as PIL Images."""
    from PIL import Image
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, t):.4f}", "-i", str(path), "-frames:v", str(n), "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    sz = w * h * 3
    return [Image.frombytes("RGB", (w, h), raw[i:i + sz]) for i in range(0, len(raw) - sz + 1, sz)]


def seek_time(f, fps):
    """The seek that lands on frame f: ffmpeg's -ss drops every frame whose own time is before the seek, so a seek to the middle of
    frame f lands on f+1. A third of a frame early is safe on both sides."""
    return max(0.0, round((f - 0.3) / fps, 4))


def t_for_frame(f, fps=30.0):
    """The `t` to write into a curate.py shot or a Foot start for frame f (3 decimals, lands on f)."""
    return max(0.0, round(f / fps - 0.3 / fps, 3))


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def key_file(key):
    """The work-file stem for a source key ("A1", "LIB1/street_a" -> "LIB1__street_a")."""
    return key.replace("/", "__")


def catalogue():
    """The footage catalogue ({} until the creator's chat fills it)."""
    try:
        cat = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cat = {}
    return cat if isinstance(cat, dict) else {}


def ledger():
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def rel_footage(p):
    """A path relative to FOOTAGE (posix), or the absolute posix path when it lies elsewhere."""
    p = Path(p)
    try:
        return p.relative_to(FOOTAGE).as_posix()
    except ValueError:
        return p.as_posix()
