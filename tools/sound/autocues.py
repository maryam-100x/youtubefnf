"""autocues.py: a video's sound-effect list written from what its picture actually does, so nobody places ~100-300 effects by hand per
video. It only reads (the gate's probe, the video's words, a cue sheet to compare with) and writes one new file: a snippet in the cue
sheet's own format, each effect citing the probe frame that proves it.

What the picture does is known exactly: the gate's probe (tools/pipeline/gate.py runs gate_probe.mjs on the composition in the gate
mode, tools/motion/src/gate.tsx) holds every text, picture, clip pane and drawn shape of every frame with its box, opacity, colour (a
djb2 hash of the computed colour) and the data-gate name its component gives it. From it:

  EVENTS (each with its film time and the probe frame that proves it)
    mark   a highlight lights: a piece that names itself data-gate="mark" (kit3's MarkBox in a Page, a Still or a Foot frame, a house
           mark) appears where no mark stood in the 3 frames before (one-to-one tracking, so a second box beside a lit one counts); a
           hollow outline drawn on a picture after its cut (the gate's own mark_items: it counts without the name); or a drawing laid
           over a picture as its own layer (an svg exactly the size of an image on the frame: a map's outline or ring) fading in
    lit    a phrase lights: words inside a line (a span whose parent is itself a text: kit3 Lit) turn from their colour to the brand
    label  a label lit whole (a list's or a scale's newest item, a title): the named thing's own light, not a mark: no effect
    stamp  a stamp lands: data-gate="stamp" text appearing whole (kit3 Stamp). A line typing itself (TypedLine, also data-gate="stamp")
           is listed as `typed` and gets no effect here
    roll   a number rolls: an Odometer's digit columns (data-gate="roll") turn in their slots, or a number's own text counts ($3,146 ...
           $0, one way, 5+ values); `land` is the frame the turning stops. A count that appears already whole (NumberBeside fixed) is a
           `land` alone
    cut    a hard cut between two different pictures: the composition's own shot starts (pipeline/shots_<comp>.json, when its length is
           this probe's), else the frames where the big lit pictures share nothing with the frame before

  EFFECTS (the house rules: standard/SOUND_AND_VOICE.md)
    mark, lit  the house marker pal("mark") from the light's first frame, sync 0. Highlights lighting within --group s (0.6) of each
               other are one group: several (3+) share one marker, as do two lighting together (within 0.2 s); two further apart keep
               a marker each (two lights 0.29 s apart get two), the second the first to yield to the cap
    stamp      the house stamp pal("stamp"), once, on its landing frame
    roll       count_up from the roll's first frame, cut to its length (-18, the standard's level); number_land where it lands (-12)
    cut        nothing: plain cuts carry no effect (a whoosh only on a real flight)
  then the density rules: effects are admitted by priority (a stamp or a landing, then a marker, then a count-up), earlier first; one
  sound a beat (an effect within --group s of a stronger kind is carried by it: a map's outline lighting with its stamp); never 4
  effects inside any 5 s (so the effects never turn into a constant patter). What is left out is listed with its reason.

  Left to a person (no rule here can see them): the one statement drop (pal("bass_drop")), whooshes on real flights, a pop on a row or a
  thing landing, impacts, fails, clicks, the register, the shutter, typing; "one for the list" where a list lights item by item more
  than 0.6 s apart; and a highlight a component draws without data-gate="mark" (a ring's border turning brand, a bar or an icon's
  halo): such a component should mark itself data-gate="mark" (the gate's B12 convention), and then it is found here too.

  Against a hand-made sheet (--compare, matched within 0.15 s), 93% of the effects it wrote sat on a hand-placed effect with the same
  sound, and it found 88% of the hand sheet's markers, stamps, count-ups and number landings; most of the markers it missed were lights
  drawn without data-gate="mark".

The output is a Python module in the cue sheet's format: a preamble naming the sounds and levels (from palette.json, as the sheets do) and
one `Sfx(...)` line per effect, anchored on the voice's own words (`w(beat, phrase) + offset`, so a new voice moves every sound with its
picture) when the video's words fit the probe, else at absolute film seconds. Paste the lines between the markers into the sheet's SFX
list (videos/<video>/score/cues.py). Every event (with its frames) goes to <out>.events.json beside it.

  EDIT tools/sound/autocues.py <video> [--probe <dir|probe.jsonl>] [--out <file.py>]
      [--compare <cue sheet.py>] [--words <words.json>] [--group 0.6] [--absolute] [--events]
  <video>      the folder name under videos/ (or its number): its video.toml gives the media folder (MEDIA/videos/<video>) and the
               composition
  --probe      default: the full gate's probe, <media folder>/pipeline/gate/probe.jsonl (else the newest one under gate/)
  --out        default: <media folder>/pipeline/autocues/autocues_<comp>.py
  --compare    a hand-made cue sheet: prints matched (within 0.15 s), only in the hand sheet, only in the generated one, and the rates
  --words      the words the anchors use; default: the --compare sheet's FILM, else the video's [score] cues sheet's FILM
"""
import argparse
import bisect
import json
import re
import runpy
import sys
import time
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MOTION, TOOLS, VIDEOS as MEDIA_VIDEOS, VIDEOS_REPO  # noqa: E402

SOUND = TOOLS / "sound"
VIDEOS = VIDEOS_REPO     # the repo's video folders (video.toml, script, cue sheet)
FPS = 60

MATCH = 0.15            # --compare: a generated effect this close to a hand-placed one is the same effect
WINDOW, CAP = 5.0, 3    # never 4 effects inside any 5 s (so the effects never turn into a constant patter)
GROUP = 0.6             # highlights lighting within this of each other are one group: several (3+) share one marker
TOGETHER = 0.2          # two highlights this close light together: one marker
KEEP = 3                # a tracked shape may miss this many frames and still be the same one (a frame the probe read without it)
MARK_OP = 0.3           # a light counts once it reaches this opacity (the gate's MARK_OP is 0.2; a fade that never gets here is no light)
ROLL_PX = 3.0           # a digit column moving more than this between two frames is turning (a page's push moves it ~0.1 px)
PRIO = {"stamp": 3, "land": 3, "mark": 2, "roll": 1}   # statement/landing > mark > roll
GENERIC = {"Credit", "Stage", "GStage", "Grounds", "Sequence", "AbsoluteFill", "withInteractivitySchema(AbsoluteFillInner)"}


# ======================================================================================================================== small helpers
def sig(s):
    """the probe's colour hash (src/gate.tsx sig: djb2, 32-bit signed)"""
    h = 5381
    for ch in s:
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return h - (1 << 32) if h >= (1 << 31) else h


def brand_rgb():
    """the brand accent (tools/motion/src/brand.ts, set at setup: `BRAND = { accent: '#RRGGBB', ... }`, or a plain
    `BRAND = '#RRGGBB'`) as the browser's computed colour, 'rgb(r, g, b)'; None when brand.ts holds no accent"""
    try:
        text = (MOTION / "src" / "brand.ts").read_text(encoding="utf-8")
    except OSError:
        return None
    m = (re.search(r"\baccent\s*:\s*['\"]#([0-9A-Fa-f]{6})['\"]", text)
         or re.search(r"BRAND\s*=\s*['\"]#([0-9A-Fa-f]{6})['\"]", text))
    if not m:
        return None
    hx = m.group(1)
    return "rgb({}, {}, {})".format(*(int(hx[i:i + 2], 16) for i in (0, 2, 4)))


_BRAND = brand_rgb()
BRAND_TEXT = sig(_BRAND) if _BRAND else None   # no accent found: no phrase can be seen lighting (main warns)


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def stem(path):
    return Path(str(path)).stem if path else ""


# ======================================================================================================================== the video
def video_folder(arg):
    """'12', '012-city-at-night' or a path -> the repo's video folder (as tools/pipeline/common.find_video)"""
    p = Path(arg)
    if p.is_dir() and (p / "video.toml").exists():
        return p.resolve()
    if (VIDEOS / arg).is_dir():
        return VIDEOS / arg
    hits = sorted(VIDEOS.glob(f"{arg}-*")) or sorted(VIDEOS.glob(f"{arg}*"))
    if not hits:
        raise SystemExit(f"autocues: no video folder for {arg!r} in {VIDEOS}")
    return hits[0]


def video_cfg(folder):
    cfg = tomllib.loads((folder / "video.toml").read_text(encoding="utf-8")) if (folder / "video.toml").exists() else {}
    v = cfg.get("video", {})
    return {"slug": folder.name, "comp": v.get("comp", ""),
            "dj": Path(v.get("dj") or cfg.get("dj") or str(MEDIA_VIDEOS / folder.name)).expanduser(),
            "cues": (folder / cfg["score"]["cues"]) if cfg.get("score", {}).get("cues") else None}


def find_probe(arg, dj):
    """--probe (a probe.jsonl or the folder holding one), else the full gate's probe (pipeline/gate/probe.jsonl: a --reprobe splices
    into it), else the newest probe.jsonl under pipeline/gate/ (a scope's or a reprobe's covers part of the film: warned on load)"""
    if arg:
        p = Path(arg)
        p = p / "probe.jsonl" if p.is_dir() else p
        if not p.exists():
            raise SystemExit(f"autocues: no probe at {p}")
        return p
    gate = dj / "pipeline" / "gate"
    if (gate / "probe.jsonl").exists():
        return gate / "probe.jsonl"
    found = sorted(gate.rglob("probe.jsonl"), key=lambda q: q.stat().st_mtime, reverse=True) if gate.exists() else []
    if not found:
        raise SystemExit(f"autocues: no probe under {gate}: run the gate first (PIPE tools/pipeline/pipe.py <video> gate)")
    return found[0]


# ======================================================================================================================== the probe
class It(NamedTuple):
    k: str        # text | img | clip | box | svg
    t: str        # a text's words, a picture's or clip's file
    g: str        # the data-gate name its component gives it (mark, stamp, roll, name, credit, icon, frame ...)
    x: float
    y: float
    w: float
    h: float
    op: float
    br: float
    c: int        # colour hash
    e: int        # 1: a hollow box (an outline)
    cx0: float
    cy0: float
    cx1: float
    cy1: float
    pa: int


def load_probe(path):
    """{frame: [It]} (credits left out), the frame's size, the refused frames"""
    lay, refused, W, H = {}, [], 1920, 1080
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            kind, _, body = line.partition("|")
            if kind == "refusal":
                try:
                    refused.append(json.loads(body)["frame"])
                except (ValueError, KeyError):
                    pass
                continue
            if kind != "layout":
                continue
            try:
                o = json.loads(body)
            except ValueError:
                continue
            W, H = o.get("W", W), o.get("H", H)
            lay[o["frame"]] = [It(i["k"], str(i.get("t", "")), i.get("g") or "", i["x"], i["y"], i["w"], i["h"], i["op"], i.get("br", 1.0),
                                  i.get("c", 0), i.get("e", 0), i.get("cx0", -1e9), i.get("cy0", -1e9), i.get("cx1", 1e9), i.get("cy1", 1e9),
                                  i.get("pa", -1))
                               for i in o["items"] if i.get("g") != "credit"]
    return lay, W, H, sorted(refused)


def area(a):
    return max(0.0, a.w) * max(0.0, a.h)


def iou(a, b):
    iw = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    ih = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    return inter / (area(a) + area(b) - inter)


def seen_area(it, W, H):
    """the part of a picture the viewer sees: inside its overflow parents and the frame"""
    x0, y0 = max(it.x, it.cx0, 0), max(it.y, it.cy0, 0)
    x1, y1 = min(it.x + it.w, it.cx1, W), min(it.y + it.h, it.cy1, H)
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def cost(a, b):
    """how far shape b (this frame) is from shape a (a frame before): None when it can't be the same shape"""
    o = iou(a, b)
    if o >= 0.3:
        return 1.0 - o
    d = abs(a.x + a.w / 2 - b.x - b.w / 2) + abs(a.y + a.h / 2 - b.y - b.h / 2)
    s = max(a.w, a.h, b.w, b.h, 1.0)
    r = (area(b) + 1) / (area(a) + 1)
    if d <= 0.25 * s + 10 and 0.6 <= r <= 1.7:
        return 0.7 + 0.25 * d / s
    return None


def track(frames, shapes_of):
    """one-to-one tracking of shapes over frames: {track id: [(frame, It, tag)]} and the births [(frame, track id)]. A shape matches the
    nearest live shape (seen within KEEP frames) it can be; one that matches none is born on that frame."""
    tracks, live, births = {}, [], []
    nid = 0
    for f in frames:
        cur = shapes_of(f)
        live = [(tid, last_f, last) for tid, last_f, last in live if f - last_f <= KEEP + 1]
        pairs = []
        for i, (_tag, it) in enumerate(cur):
            for j, (_tid, _lf, last) in enumerate(live):
                c = cost(last, it)
                if c is not None:
                    pairs.append((c, i, j))
        pairs.sort()
        took_i, took_j = {}, set()
        for c, i, j in pairs:
            if i in took_i or j in took_j:
                continue
            took_i[i] = live[j][0]
            took_j.add(j)
        nxt = [x for j, x in enumerate(live) if j not in took_j]
        for i, (tag, it) in enumerate(cur):
            tid = took_i.get(i)
            if tid is None:
                nid += 1
                tid = nid
                births.append((f, tid))
            tracks.setdefault(tid, []).append((f, it, tag))
            nxt.append((tid, f, it))
        live = nxt
    return tracks, births


# ======================================================================================================================== events
@dataclass
class Event:
    kind: str                 # mark | lit | stamp | typed | roll | land | cut
    f: int                    # the probe frame that proves it (its first frame)
    what: str                 # what lights, lands or rolls
    on: str = ""              # the picture it sits on (a file's stem) or its text
    f_end: int = None         # a roll's last turning frame
    frames: list = field(default_factory=list)   # every frame of a group's members
    with_cut: bool = False    # it arrives on a cut's frame (the picture's own arrival)
    shot: str = ""

    @property
    def t(self):
        """the action's start in film seconds: it lies between the frame before and this one"""
        return max(0.0, (self.f - 0.5) / FPS)


def pictures(items, W, H):
    """the big lit pictures on a frame (img or clip panes over 15% of it): what a cut changes"""
    return {(i.k, i.t) for i in items if i.k in ("img", "clip") and i.op * i.br >= 0.3 and seen_area(i, W, H) >= 0.15 * W * H}


def swaps(lay, frames, W, H):
    """the frames where the big lit pictures share nothing with the frame before (a cut, or a clip swapped for its held frame)"""
    at, prev = [], None
    for f in frames:
        cur = pictures(lay[f], W, H)
        if prev and cur and not (cur & prev):
            at.append(f)
        prev = cur if cur else prev
    return at


def find_cuts(lay, frames, W, H, shots, swapped):
    """the hard cuts: the composition's own shot starts when its shot list fits this probe (a clip swapped for its held frame under a
    mark is no cut), else the probe's picture swaps; each names the pictures it joins"""
    at = sorted({int(s["at"] * FPS + 0.5) for s in shots if s["at"] > 0}) if shots else swapped
    out = []
    for f in at:
        a = sorted(stem(t) for _k, t in pictures(lay.get(f - 1, []), W, H))
        b = sorted(stem(t) for _k, t in pictures(lay.get(f, []), W, H))
        out.append(Event("cut", f, f"cut {', '.join(a[:2]) or 'graphic'} -> {', '.join(b[:2]) or 'graphic'}", ", ".join(b[:2])))
    return out


def ground(items, it, W, H):
    """the picture a mark points into: the topmost lit img or clip under its centre, bigger than it"""
    cx, cy = it.x + it.w / 2, it.y + it.h / 2
    best = None
    for o in items:
        if o.k in ("img", "clip") and o.op * o.br >= 0.3 and o.x <= cx <= o.x + o.w and o.y <= cy <= o.y + o.h and area(o) > 2.5 * area(it):
            best = o
    return stem(best.t) if best else ""


def outline(items, i, W, H):
    """a hollow outline that marks something (the gate's mark_items): a border with nothing filled in, under a third of the frame,
    no credit, name, stamp or count, and not framing a thing of ours (a box, text or drawing filling half of it or more)"""
    it = items[i]
    if it.k != "box" or it.e != 1 or it.g or it.w < 6 or it.h < 6 or area(it) >= W * H / 3:
        return False
    px, py = 0.15 * it.w, 0.15 * it.h
    x0, y0, x1, y1 = it.x - px, it.y - py, it.x + it.w + px, it.y + it.h + py
    return not any(j != i and o.k in ("box", "text", "svg") and o.op >= 0.2 and x0 <= o.x and o.x + o.w <= x1 and y0 <= o.y
                   and o.y + o.h <= y1 and area(o) >= 0.5 * area(it) for j, o in enumerate(items))


def find_marks(lay, frames, W, H, cutset):
    """data-gate="mark" pieces lighting; a hollow outline drawn on a picture (the gate counts it as a mark without the name); a
    drawing laid over a picture as its own layer (an svg the size of an image on the frame: a map's outline or ring) fading in"""
    def shapes(f):
        items = lay.get(f, [])
        out = []
        boxes = {(round(o.x), round(o.y), round(o.w), round(o.h)) for o in items if o.k == "img"}
        for i, it in enumerate(items):
            if it.g == "mark" and it.k in ("box", "svg", "text"):
                out.append(("mark", it))
            elif outline(items, i, W, H):
                out.append(("outline", it))
            elif it.k == "svg" and not it.g and any(abs(it.x - bx) <= 3 and abs(it.y - by) <= 3 and abs(it.w - bw) <= 4 and abs(it.h - bh) <= 4
                                                   for bx, by, bw, bh in boxes):
                out.append(("drawing", it))
        return out
    tracks, births = track(frames, shapes)
    out = []
    for f, tid in births:
        run = tracks[tid]
        life = [x for x in run if x[0] - f <= 15]
        top = max(x[1].op for x in life)
        _f0, it, tag = run[0]
        if len(run) < 4 and run[-1][0] < frames[-1] - 1:     # a flicker, not a light
            continue
        if top < MARK_OP:
            continue
        at_cut = any(c in cutset for c in range(f - 2, f + 1))
        if tag != "mark" and (at_cut or (tag == "drawing" and it.op >= 0.7)):
            continue                                          # an outline or drawing arriving with its picture is that picture's look
        items = lay[f]
        on = ground(items, it, W, H) if tag != "drawing" else next((stem(o.t) for o in items if o.k == "img" and abs(o.x - it.x) <= 3
                                                                    and abs(o.w - it.w) <= 4), "")
        what = {"mark": "a mark lights", "outline": "an outline is drawn", "drawing": "a drawing fades in"}[tag]
        out.append(Event("mark", f, what, on, with_cut=at_cut))
    return out


def find_lit(lay, frames):
    """plain texts turning to the brand colour: the first frame their colour leaves the one it held. Words inside a line (kit3 Lit: a
    span whose parent is itself a text) are a lit phrase, a highlight; a label lit whole (a list's or a scale's newest item, a title)
    is the named thing's own light, not a mark (it stays silent), and is listed as `label`"""
    if BRAND_TEXT is None:
        return []
    lines = defaultdict(list)    # (text, nth) -> [(frame, colour, opacity, inside a line)]
    for f in frames:
        n = Counter()
        items = lay[f]
        for it in items:
            if it.k != "text" or it.g or not re.search(r"[^\W_]", it.t):     # a comma or a dash lit with its number is no phrase
                continue
            inline = 0 <= it.pa < len(items) and items[it.pa].k == "text"
            lines[(it.t, n[it.t])].append((f, it.c, it.op, inline))
            n[it.t] += 1
    out = []
    for (text, _), seq in lines.items():
        last = -99
        for i in range(2, len(seq)):
            f, c, op, inline = seq[i]
            pf, pc, pop, _ = seq[i - 1]
            if c == pc or pc == BRAND_TEXT or f - pf > 2 or pop < 0.3 or seq[i - 2][1] != pc or f - last < 30:
                continue
            # the colour starts moving here: a light when it settles on the brand within 0.4 s and holds it 3 frames
            end = [x for x in seq[i:i + 26] if x[0] - f <= 24]
            k = next((j for j, x in enumerate(end) if x[1] == BRAND_TEXT), None)
            if k is not None and len(end) >= k + 3 and all(x[1] == BRAND_TEXT for x in end[k:k + 3]):
                out.append(Event("lit" if inline else "label", f, f"'{text[:40]}' lit" + ("" if inline else " (a label: no effect)"), text[:40]))
                last = f
    return out


def find_stamps(lay, frames):
    """data-gate="stamp" texts appearing (a stamp's lines land together); a text that grows letter by letter is a typed line"""
    last, out, cur_group = {}, [], None
    for f in frames:
        texts = sorted((it for it in lay[f] if it.k == "text" and it.g == "stamp" and it.op >= 0.05), key=lambda it: (round(it.y), it.x))
        for it in texts:
            seen = last.get(it.t)
            if seen is not None and f - seen <= 6:
                continue
            grows = any(it.t != t0 and it.t.startswith(t0) and f - f0 <= 6 for t0, f0 in last.items())
            if cur_group and f - cur_group.f <= 3:
                cur_group.frames.append(f)
                cur_group.on = f"{cur_group.on} / {it.t}" if it.t not in cur_group.on else cur_group.on
                if grows:
                    cur_group.kind = "typed"
                continue
            if grows:
                if out and out[-1].kind in ("stamp", "typed") and f - out[-1].frames[-1] <= 30:
                    out[-1].kind, out[-1].what = "typed", "a line types itself"
                    out[-1].frames.append(f)
                continue
            cur_group = Event("stamp", f, "a stamp lands", it.t, frames=[f])
            out.append(cur_group)
        for it in texts:
            last[it.t] = f
    for e in out:
        if e.kind == "stamp":
            e.what = f"stamp '{e.on}' lands"
    return out


def columns(items):
    """an Odometer's digit columns on a frame (data-gate="roll"): [(cx0, cy0, width, the column's offset in its slot, the digit shown)]"""
    cols = defaultdict(list)
    for it in items:
        if it.g == "roll":
            cols[(it.cx0, it.cy0)].append(it)
    out = []
    for (cx, cy), its in cols.items():
        vis = [i for i in its if i.cy0 <= i.y + i.h / 2 <= i.cy1]
        out.append((cx, cy, max(1.0, its[0].cx1 - cx), min(i.y for i in its) - cy, vis[0].t if vis else "?"))
    return sorted(out, key=lambda c: (round(c[1] / 10), c[0]))


def digits_value(items):
    """the numbers the Odometers show, '1,534,000 / 3,150,000': columns on one line next to each other are one number"""
    nums, prev = [], None
    for cx, cy, w, _off, d in columns(items):
        if prev is None or abs(cy - prev[1]) > 10 or cx - (prev[0] + prev[2]) > 1.5 * w:
            nums.append("")
        nums[-1] += d
        prev = (cx, cy, w)
    fmt = lambda s: f"{int(s):,}" if s.isdigit() else s
    return " / ".join(fmt(n) for n in nums)


def find_rolls(lay, frames):
    """an Odometer's columns turning (data-gate="roll"): the roll from its first turning frame to its last, then its landing; a count
    that shows and never turns lands whole on its first frame"""
    shown = [f for f in frames if any(it.g == "roll" for it in lay[f])]
    out = []
    runs, cur = [], []
    for f in shown:
        if cur and f - cur[-1] > 2:
            runs.append(cur)
            cur = []
        cur.append(f)
    if cur:
        runs.append(cur)
    for run in runs:
        moving, prev = [], None
        for f in run:
            cols = columns(lay[f])
            if prev is not None:
                # a column turning in its slot (the same column on the frame before: its slot within 6 px); a page's push moves the
                # slot with the digits, so only the offset inside the slot counts
                for cx, cy, _w, off, _d in cols:
                    p = next((q for q in prev if abs(q[0] - cx) <= 6 and abs(q[1] - cy) <= 6), None)
                    if p is not None and abs(off - p[3]) > ROLL_PX:
                        moving.append(f)
                        break
            prev = cols
        segs, cur = [], []
        for f in moving:
            if cur and f - cur[-1] > 6:
                segs.append(cur)
                cur = []
            cur.append(f)
        if cur:
            segs.append(cur)
        segs = [s for s in segs if len(s) >= 3]         # a roll turns for a few frames; one jolt is no count
        if not segs:
            val = digits_value(lay[run[0]])
            out.append(Event("land", run[0], f"{val} lands whole", val))
            continue
        for seg in segs:
            end = next((f for f in run if f > seg[-1]), seg[-1])
            val = digits_value(lay[end])
            out.append(Event("roll", seg[0], f"the number rolls to {val}", val, f_end=seg[-1]))
            out.append(Event("land", end, f"{val} lands", val))
    return out


NUMBER = re.compile(r"^(\D{0,4}?)([\d][\d,.]*)(\D{0,8})$")


def number_of(text):
    m = NUMBER.match(text.strip())
    try:
        return float(m.group(2).replace(",", "")) if m else 0.0
    except ValueError:
        return 0.0


def find_counts(lay, frames):
    """a number's own text counting ($ 3,146 ... $ 0): on most frames a number on a line is replaced by another of its kind (same
    prefix and unit) on that line; a number still standing where it stood is no step (a row of years doesn't count)"""
    out, prev, run = [], [], None
    same = lambda a, b, dx: a[4] == b[4] and abs(a[2] - b[2]) <= 6 and abs(a[3] - b[3]) <= dx
    for f in frames:
        cur = []
        for it in lay[f]:
            if it.k != "text" or it.g in ("roll", "stamp", "credit"):
                continue
            m = NUMBER.match(it.t.strip())
            if m:
                cur.append((m.group(1).strip(), m.group(3).strip(), it.y, it.x + it.w / 2, it.t))
        new = [a for a in cur if not any(same(a, b, 20) for b in prev)]
        gone = [b for b in prev if not any(same(b, a, 20) for a in cur)]
        stepped = None
        for a in new:
            for b in gone:
                if a[4] != b[4] and a[0] == b[0] and a[1] == b[1] and abs(a[2] - b[2]) <= 6 and abs(a[3] - b[3]) <= 90:
                    stepped = (a, b)
        if stepped:
            if run and f - run["last"] <= 2 and abs(run["y"] - stepped[0][2]) <= 6:
                run["last"], run["n"], run["to"] = f, run["n"] + 1, stepped[0][4]
                run["values"].append(number_of(stepped[0][4]))
            else:
                out.append(run)
                run = {"first": f, "last": f, "n": 1, "y": stepped[0][2], "from": stepped[1][4], "to": stepped[0][4],
                       "values": [number_of(stepped[1][4]), number_of(stepped[0][4])]}
        prev = cur
    out.append(run)
    ev = []
    for r in out:
        # a count: at least 4 steps through 5 different values, all one way (a label flipping between two values is no count)
        if not r or r["n"] < 4 or len(set(r["values"])) < 5:
            continue
        d = [b - a for a, b in zip(r["values"], r["values"][1:]) if b != a]
        if not (all(x > 0 for x in d) or all(x < 0 for x in d)):
            continue
        ev.append(Event("roll", r["first"], f"{r['from']} counts to {r['to']}", r["to"], f_end=r["last"]))
        ev.append(Event("land", r["last"] + 1, f"{r['to']} lands", r["to"]))
    return ev


def name_shots(events, shots, cuts):
    """each event's shot: the composition's own shot list when it fits this probe (pipeline/shots_<comp>.json), else the probe's cuts"""
    if shots:
        starts = [int(s["at"] * FPS + 0.5) for s in shots]     # in frames, as the render places a cut (gate.py fr())
        for e in events:
            i = max(0, bisect.bisect_right(starts, e.f) - 1)
            s = shots[i]
            names = [n for n in s.get("names", []) if n not in GENERIC] or s.get("names", [])[:1]
            e.shot = f"{'/'.join(names[:2]) or 'shot'} shot {s.get('i', i)} at {mmss(s['at'])}"
    else:
        for e in events:
            i = bisect.bisect_right(cuts, e.f)
            e.shot = f"shot {i} at {mmss((cuts[i - 1] if i else 0) / FPS)}"


def load_shots(pipe_dir, comp, seconds):
    """the shot list whose length is this probe's (a probe of the prototype sits beside the film's)"""
    cands = ([pipe_dir / f"shots_{comp}.json"] if comp else []) + sorted(pipe_dir.glob("shots_*.json"))
    for p in cands:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if abs(float(d.get("seconds", -99)) - seconds) <= 0.1 and d.get("shots"):
            return d["shots"], p
    return None, None


# ======================================================================================================================== effects
@dataclass
class Fx:
    kind: str                 # mark | stamp | roll | land
    sound: str                # the preamble's name: MARK, STAMP, CNT, NUM
    t: float
    db: str                   # the preamble's level name or a number
    note: str
    sync: float = None
    dur: float = None
    expr: str = ""            # the time as the sheet writes it (an anchor on the words, or seconds)
    events: list = field(default_factory=list)
    p: float = None           # its own priority (a pair's second light: under a lone marker)
    count: int = None         # a count-up and its own landing share the roll's first frame (the landing never carries its count)
    why: str = ""             # why the cap left it out

    @property
    def prio(self):
        return PRIO[self.kind] if self.p is None else self.p


def frames_txt(e):
    fs = sorted(set([e.f] + e.frames))
    return f"f{fs[0]}" if len(fs) == 1 else f"f{fs[0]}-f{fs[-1]}"


def groups(lights, group):
    """highlights lighting within `group` s of the one before light as one group, and several (3 or more) share one marker; two share
    one only when they light together (TOGETHER), else each keeps its own (two lights 0.29 s apart: two markers; a row of six lighting
    in turn: one). The 5-s cap then thins what is left"""
    runs = []
    for e in lights:
        if runs and e.f - runs[-1][-1].f <= group * FPS:
            runs[-1].append(e)
        else:
            runs.append([e])
    out = []
    for r in runs:
        if len(r) >= 3 or (len(r) == 2 and r[1].f - r[0].f <= TOGETHER * FPS):
            out.append((r, False))
        else:
            out += [([e], k > 0) for k, e in enumerate(r)]    # a pair's second light: the first the cap lets go
    return out


def to_effects(events, group):
    """the house rules: the house marker on a highlight (one per group lit together), the stamp on a stamp, the count-up on a roll and
    number_land on its landing; nothing on a cut, a label's light or a typed line"""
    fx = []
    lights = sorted([e for e in events if e.kind in ("mark", "lit")], key=lambda e: e.f)
    for g, second in groups(lights, group):
        first = g[0]
        if len({(x.f, x.what, x.on) for x in g}) == 1:          # one light drawn in layers (an outline and its glow)
            what = f"{first.what}{' on ' + first.on if first.on and first.kind == 'mark' else ''}" + (f" ({len(g)} layers)" if len(g) > 1 else "")
        else:
            what = f"{len(g)} highlights light {'together' if len(g) == 2 else 'one after another'} " \
                   f"({', '.join(sorted(set((x.on or x.what)[:28] for x in g))[:3])})"
        fs = sorted({x.f for x in g})
        proof = "probe " + ", ".join(f"f{f}" for f in fs[:4]) + (" ..." if len(fs) > 4 else "")
        fx.append(Fx("mark", "MARK", first.t, "MK", f"{first.shot}: {what} ({proof}; the house marker)", sync=0.0, events=g,
                     p=PRIO["mark"] - 0.5 if second else None))
    last_roll = None
    for e in sorted(events, key=lambda e: e.f):
        if e.kind == "stamp":
            fx.append(Fx("stamp", "STAMP", e.t + 0.02, "SD", f"{e.shot}: {e.what} (probe {frames_txt(e)})", events=[e]))
        elif e.kind == "roll":
            dur = round(max(0.3, (e.f_end - e.f + 1) / FPS), 2)
            last_roll = e.f
            fx.append(Fx("roll", "CNT", e.t, "-18", f"{e.shot}: {e.what} (probe f{e.f}-f{e.f_end}; cut to the count)", sync=0.0, dur=dur,
                         events=[e], count=e.f))
        elif e.kind == "land":
            own = last_roll if last_roll is not None and e.f - last_roll <= 600 and not e.what.endswith("whole") else None
            fx.append(Fx("land", "NUM", e.t, "-12", f"{e.shot}: {e.what} (probe f{e.f})", events=[e], count=own))
    return sorted(fx, key=lambda x: x.t)


def crowded(times, t):
    """how many effects a 5-s window holding t would hold with t added (the sheets' own count: u in [s, s + 5))"""
    near = sorted([u for u in times if t - WINDOW < u < t + WINDOW] + [t])
    best = 0
    for k, s in enumerate(near):
        if s > t:
            break
        best = max(best, sum(1 for u in near[k:] if u < s + WINDOW))
    return best


def cap(fx, group):
    """admit by priority (a stamp or a landing, a marker, a count-up), earlier first: one sound per beat (an effect within `group` s of
    a higher one is carried by it: a map's outline lighting with its stamp), and never 4 inside any 5 s"""
    kept, dropped = [], []
    for x in sorted(fx, key=lambda x: (-x.prio, x.t)):
        # carried: by a stronger kind on its beat (a pair's second light only ever yields to the cap, never to its first)
        carrier = next((k for k in kept if PRIO[k.kind] > PRIO[x.kind] and abs(k.t - x.t) <= group
                        and not (x.count is not None and k.count == x.count)), None)
        if carrier is not None:
            x.why = f"carried by the {SOUND_OF[carrier.sound]} at {carrier.t:.2f}"
            dropped.append(x)
        elif crowded([k.t for k in kept], x.t) <= CAP:
            kept.append(x)
        else:
            x.why = "the 5-s cap"
            dropped.append(x)
    return sorted(kept, key=lambda x: x.t), sorted(dropped, key=lambda x: x.t)


# ======================================================================================================================== anchors
def words_from(args, vc, probe_seconds):
    """the words the anchors use and how the written module gets them: (words, ('file', path) | ('sheet', path)) or (None, reason)"""
    if args.words:
        p = Path(args.words).resolve()
        return json.loads(p.read_text(encoding="utf-8")), ("file", p)
    sheet = Path(args.compare).resolve() if args.compare else vc["cues"]
    if not sheet or not Path(sheet).exists():
        return None, "no cue sheet to take the words from"
    try:
        m = run_sheet(sheet)
    except (Exception, SystemExit) as ex:   # noqa: BLE001  a sheet that doesn't load leaves the times absolute
        return None, f"{Path(sheet).name} didn't load ({str(ex)[:120]})"
    film = m.get("FILM")
    if film is None or not getattr(film, "W", None):
        return None, f"{Path(sheet).name} has no FILM"
    return film.W, ("sheet", Path(sheet))


def fits(words, probe_seconds):
    end = max(x["end"] for x in words)
    return probe_seconds * 0.5 <= end <= probe_seconds + 1.0, end


_CLEAN = re.compile(r"^[\"'“”‘’(\[]+|[\"'“”‘’)\].,!?;:…]+$")
STOPWORDS = {"a", "an", "the", "of", "to", "in", "on", "at", "and", "or", "it", "its", "is", "you", "your", "for", "with", "that", "this",
             "so", "but", "as", "by", "be", "are", "was", "he", "she", "they", "we", "i", "if", "up", "out", "just", "then"}


class Anchors:
    """w(beat, phrase) + offset for a time, verified with score.Film's own lookup (the sheets' w)"""

    def __init__(self, words):
        sys.path.insert(0, str(SOUND))
        from score import Film
        self.F = Film.__new__(Film)
        self.F.W, self.F.B, self.F.duration = words, {}, None
        self.W = words
        self.starts = [x["start"] for x in words]

    def __call__(self, t, reach=0.6):
        i = bisect.bisect_left(self.starts, t)
        cands = [j for j in (i - 1, i) if 0 <= j < len(self.W)]
        if not cands:
            return None
        i = min(cands, key=lambda j: abs(self.starts[j] - t))
        if abs(self.starts[i] - t) > reach or not self.F._n(self.W[i]["w"]):
            return None
        beat, start = self.W[i]["beat"], self.starts[i]
        word = self.F._n(self.W[i]["w"])
        for n in range(2 if word in STOPWORDS or len(word) <= 2 else 1, 5):   # "a couple", never a bare "a"
            idx = list(range(i, i + n))
            if idx[-1] >= len(self.W) or any(self.W[j]["beat"] != beat or not self.F._n(self.W[j]["w"]) for j in idx):
                break
            phrase = " ".join(_CLEAN.sub("", self.W[j]["w"]) for j in idx)
            try:
                if abs(self.F.w(beat, phrase) - start) < 1e-9:
                    return self._expr(beat, phrase, None, t - start)
            except KeyError:
                continue
        phrase = _CLEAN.sub("", self.W[i]["w"])
        nth = sum(1 for j in range(i) if self.W[j]["beat"] == beat and self.F._n(self.W[j]["w"]) == self.F._n(self.W[i]["w"]))
        try:
            if abs(self.F.w(beat, phrase, nth) - start) < 1e-9:
                return self._expr(beat, phrase, nth, t - start)
        except KeyError:
            pass
        return None

    def _expr(self, beat, phrase, nth, off):
        off = round(off, 2)
        call = f"w({json.dumps(beat)}, {json.dumps(phrase, ensure_ascii=False)}{'' if nth is None else f', {nth}'})"
        start = self.F.w(beat, phrase, nth or 0)
        return (call if off == 0 else f"{call} {'+' if off > 0 else '-'} {abs(off):.2f}"), start + off


# ======================================================================================================================== the sheets
_SHEETS = {}


def run_sheet(path):
    """a cue sheet's globals (it is run as score.py and gate.py run it), once per path"""
    key = str(Path(path).resolve())
    if key in _SHEETS:
        return _SHEETS[key]
    if str(SOUND) not in sys.path:
        sys.path.insert(0, str(SOUND))
    out = sys.stdout
    try:
        import io
        sys.stdout = io.StringIO()      # a sheet's own prints (a range waiting for its voice) stay out of the report
        _SHEETS[key] = runpy.run_path(str(path), run_name="cues_sheet")
    finally:
        sys.stdout = out
    return _SHEETS[key]


def sheet_effects(path):
    """[(t, sound file's stem, note)] of a sheet's SFX"""
    m = run_sheet(path)
    return sorted((float(s.t), stem(s.path), s.note) for s in m.get("SFX", []))


def palette():
    """the house effects palette (tools/sound/palette.json, as score.py reads it); {} before the setup has laid it in"""
    p = SOUND / "palette.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


SOUND_OF = {"MARK": "mark", "STAMP": "stamp", "CNT": "count_up", "NUM": "number_land"}


def compare(fx, hand_path, seconds):
    """matched (one to one, nearest first, within MATCH s), only in the hand sheet, only in the generated one"""
    pal = palette()
    stem_of = {k: stem(v["file"]) for k, v in pal.items() if isinstance(v, dict) and v.get("file")}
    name_of = {v: k for k, v in stem_of.items()}
    try:
        hand = sheet_effects(hand_path)
    except (Exception, SystemExit) as ex:   # noqa: BLE001  a sheet's own guard (a stale words file, a missing voice) stops it
        print(f"\n=== compare: {hand_path} didn't load, nothing to compare: {str(ex)[:300]}")
        return None
    outside = [h for h in hand if h[0] > seconds + 0.5]
    hand = [h for h in hand if h[0] <= seconds + 0.5]
    pairs = sorted((abs(h[0] - g.t), i, j) for i, h in enumerate(hand) for j, g in enumerate(fx) if abs(h[0] - g.t) <= MATCH)
    hi, gj, matched = set(), set(), []
    for d, i, j in pairs:
        if i in hi or j in gj:
            continue
        hi.add(i)
        gj.add(j)
        matched.append((hand[i], fx[j]))
    matched.sort(key=lambda m: m[0][0])
    only_h = [h for i, h in enumerate(hand) if i not in hi]
    only_g = [g for j, g in enumerate(fx) if j not in gj]
    hname = lambda h: name_of.get(h[1], h[1][:14])
    print(f"\n=== compare with {hand_path} ({len(hand)} hand-placed effects in the probe's {mmss(seconds)}"
          f"{f'; {len(outside)} after it left out' if outside else ''})")
    print(f"\nmatched within {MATCH:.2f} s: {len(matched)}")
    same = 0
    for h, g in matched:
        ok = hname(h) == SOUND_OF[g.sound]
        same += ok
        print(f"  {h[0]:8.2f} {g.t:8.2f} {g.t - h[0]:+.2f}  {hname(h):12s} {'=' if ok else '~'} {SOUND_OF[g.sound]:11s}  {h[2][:70]}")
    print(f"\nonly in the hand sheet: {len(only_h)}")
    for h in only_h:
        print(f"  {h[0]:8.2f}  {hname(h):12s}  {h[2][:100]}")
    print(f"\nonly in the generated one: {len(only_g)}")
    for g in only_g:
        print(f"  {g.t:8.2f}  {SOUND_OF[g.sound]:12s}  {g.note[:100]}")
    kinds = Counter(hname(h) for h in hand)
    got = Counter(hname(h) for h, _g in matched)
    ours = {"mark", "stamp", "count_up", "number_land"}
    n_ours = sum(v for k, v in kinds.items() if k in ours)
    m_ours = sum(v for k, v in got.items() if k in ours)
    print("\nby the hand sheet's sound (matched / placed): " + ", ".join(f"{k} {got[k]}/{v}" for k, v in kinds.most_common()))
    print(f"recall {len(matched)}/{len(hand)} = {len(matched) / max(1, len(hand)):.0%} of every hand-placed effect; "
          f"{m_ours}/{n_ours} = {m_ours / max(1, n_ours):.0%} of the kinds these rules make (marker, stamp, count-up, number landing)")
    print(f"precision {len(matched)}/{len(fx)} = {len(matched) / max(1, len(fx)):.0%} of the generated effects sit on a hand-placed one "
          f"({same} with the same sound)")
    return {"hand": len(hand), "generated": len(fx), "matched": len(matched), "same_sound": same, "hand_ours": n_ours,
            "matched_ours": m_ours, "only_hand": len(only_h), "only_generated": len(only_g)}


# ======================================================================================================================== the output
def write_module(out, fx, dropped, events, info, words_src, anchored):
    pal = palette()
    px = lambda q: Path(q).as_posix() if q else q     # forward slashes: a backslash path in a docstring reads as an escape
    lines = [f'"""{info["video"]}: the effects its picture asks for, written by tools/sound/autocues.py on {time.strftime("%Y-%m-%d %H:%M")}.',
             f"probe: {px(info['probe'])} ({info['frames']} frames, {mmss(info['seconds'])}, made {info['probe_time']})",
             f"shots: {px(info['shots']) or 'the probe cuts'}; words: {info['words'].replace(chr(92), '/')}",
             f"{len(fx)} effects ({info['counts']}); {len(dropped)} left out by the cap or carried by a stronger sound on their beat "
             "(listed at the end).",
             "Each effect cites the probe frames that prove it. Paste the lines between the markers into the cue sheet's SFX list (they use",
             "w and the names below); a person still adds what no rule can see: the statement drop, whooshes on real flights, pops, impacts.",
             '"""',
             "import json",
             "import sys",
             "from pathlib import Path",
             "",
             "# tools/sound: from the repo when this file sits in videos/<video>/score/, else where it was written from",
             "_SOUND = Path(__file__).resolve().parents[3] / \"tools\" / \"sound\"",
             f"sys.path.insert(0, str(_SOUND if (_SOUND / \"score.py\").exists() else Path(\"{px(SOUND)}\")))",
             "from score import PALETTE, Film, Sfx, pal  # noqa: E402,F401",
             "",
             "PALETTE_DB = {k: v.get('db') for k, v in PALETTE.items() if isinstance(v, dict)}"]
    if anchored:
        kind, p = words_src
        if kind == "file":
            beats = next((q for q in (p.with_name(p.name.replace("words", "beats")), p.with_name("beats.json")) if q.exists() and q != p), None)
            if beats:
                lines.append(f"w = Film(\"{px(p)}\", \"{px(beats)}\").w")
            else:
                lines += ["_F = Film.__new__(Film)", f"_F.W, _F.B, _F.duration = json.loads(Path(\"{px(p)}\").read_text(encoding='utf-8')), {{}}, None",
                          "w = _F.w"]
        else:
            lines += ["import runpy  # noqa: E402", f"w = runpy.run_path(\"{px(p)}\")[\"FILM\"].w   # the words the sheet itself anchors on"]
    lines += ["MARK, STAMP, CNT, NUM = pal(\"mark\"), pal(\"stamp\"), pal(\"count_up\"), pal(\"number_land\")",
              f"MK, SD = PALETTE_DB.get(\"mark\") or {pal.get('mark', {}).get('db', -14)}, PALETTE_DB.get(\"stamp\") or {pal.get('stamp', {}).get('db', -2)}",
              "",
              "SFX = [",
              f"    # ---- autocues: paste from here ({len(fx)} effects) ----"]
    for x in fx:
        args = [x.sound, x.expr, x.db]
        if x.sync is not None:
            args.append(f"sync={x.sync}")
        if x.dur is not None:
            args.append(f"dur={x.dur}")
        lines.append(f"    Sfx({', '.join(args)}, note={json.dumps(x.note, ensure_ascii=False)}),   # {mmss(x.t)}")
    lines += ["    # ---- autocues: to here ----", "]", ""]
    if dropped:
        lines.append(f"# left out (admitted by priority stamp/landing > marker > count-up, earlier first; one sound a beat; never 4 inside "
                     f"5 s): {len(dropped)}")
        for x in dropped:
            lines.append(f"#   {x.t:8.2f} {SOUND_OF[x.sound]:11s} [{x.why}] {x.note[:150]}")
    left = [e for e in events if e.kind in ("typed", "label")]
    if left:
        lines.append(f"# events no rule here sounds (a person's call): {len(left)}")
        for e in left:
            lines.append(f"#   {e.t:8.2f} {e.kind:6s} {e.what} '{e.on[:60]}' ({e.shot}; probe {frames_txt(e)})")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ======================================================================================================================== main
def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--probe")
    ap.add_argument("--out")
    ap.add_argument("--compare")
    ap.add_argument("--words")
    ap.add_argument("--group", type=float, default=GROUP)
    ap.add_argument("--absolute", action="store_true", help="absolute film seconds, no word anchors")
    ap.add_argument("--events", action="store_true", help="print every event")
    a = ap.parse_args()

    folder = video_folder(a.video)
    vc = video_cfg(folder)
    probe = find_probe(a.probe, vc["dj"])
    t0 = time.time()
    lay, W, H, refused = load_probe(probe)
    if not lay:
        raise SystemExit(f"autocues: {probe} holds no layout lines")
    frames = sorted(lay)
    seconds = (frames[-1] + 1) / FPS
    gaps = (frames[-1] + 1) - len(frames)
    print(f"probe {probe}: {len(frames)} frames ({mmss(seconds)}), read in {time.time() - t0:.1f} s"
          + (f"; WARNING {gaps} frames missing (a partial probe: events there are not seen)" if gaps > 2 else "")
          + (f"; {len(refused)} refused frames (a kit3 piece drew nothing there: f{refused[0]}...)" if refused else ""))

    if BRAND_TEXT is None:
        print(f"WARNING: no accent colour in {MOTION / 'src' / 'brand.ts'}: lit phrases can't be seen (run the setup's look step)")
    shots, shots_path = load_shots(vc["dj"] / "pipeline", vc["comp"], seconds)
    swapped = swaps(lay, frames, W, H)
    cut_events = find_cuts(lay, frames, W, H, shots, swapped)
    cuts = [e.f for e in cut_events]
    events = (cut_events + find_marks(lay, frames, W, H, set(cuts) | set(swapped)) + find_lit(lay, frames) + find_stamps(lay, frames)
              + find_rolls(lay, frames) + find_counts(lay, frames))
    events.sort(key=lambda e: e.f)
    name_shots(events, shots, cuts)
    kinds = Counter(e.kind for e in events)
    print(f"events ({'cuts from ' + shots_path.name if shots_path else 'cuts from the probe'}): "
          + ", ".join(f"{kinds[k]} {k}" for k in ("cut", "mark", "lit", "label", "stamp", "typed", "roll", "land") if kinds[k]))
    if a.events:
        for e in events:
            print(f"  {e.t:9.3f} {mmss(e.t):>9s} {e.kind:6s} {frames_txt(e):>15s}  {e.what[:64]}{' (with the cut)' if e.with_cut and e.kind != 'cut' else ''}"
                  f"  | {e.shot}")

    fx = to_effects(events, a.group)
    fx, dropped = cap(fx, a.group)

    words, src = (None, "absolute seconds (--absolute)") if a.absolute else words_from(a, vc, seconds)
    anchored = False
    if words is not None:
        ok, end = fits(words, seconds)
        ok = ok or src[0] == "file"     # --words: the person names the voice this picture was made on
        if not ok:
            print(f"words: {src[1]} ends at {mmss(end)}, the probe at {mmss(seconds)}: they are not this probe's (absolute seconds written; "
                  "give --words for the voice this picture was made on)")
            src = (f"absolute seconds ({src[1].name}'s words end at {mmss(end)}, the probe at {mmss(seconds)})", "said")
        else:
            anc = Anchors(words)
            n_abs = 0
            for x in fx:
                got = anc(x.t)
                if got:
                    x.expr, x.t = got
                else:
                    x.expr, n_abs = f"{x.t:.3f}", n_abs + 1
            anchored = True
            print(f"words: {src[0]} {src[1]}: {len(fx) - n_abs} effects anchored on the voice's words, {n_abs} at absolute seconds")
    if not anchored:
        for x in fx:
            x.expr = f"{x.t:.3f}"
        if isinstance(src, str):
            print(f"words: {src}")
        else:
            src = src[0]                # already said above
    counts = Counter(x.kind for x in fx)
    count_txt = ", ".join(f"{counts[k]} {n}" for k, n in (("mark", "markers"), ("stamp", "stamps"), ("roll", "count-ups"), ("land", "number landings")))
    worst = max((crowded([y.t for y in fx if y is not x], x.t) for x in fx), default=0)
    why = Counter(x.why.split(" at ")[0] for x in dropped)
    print(f"effects: {len(fx)} ({count_txt}); left out: {len(dropped)} ({', '.join(f'{v} {k}' for k, v in why.items()) or 'none'}); "
          f"the densest 5 s holds {worst}" + (f"  WARNING: over the cap of {CAP} (the anchors' rounding moved a time: check it)"
                                              if worst > CAP else ""))

    comp = shots_path.stem.removeprefix("shots_") if shots_path else (vc["comp"] or vc["slug"])   # the probe's own composition
    out = Path(a.out) if a.out else vc["dj"] / "pipeline" / "autocues" / f"autocues_{comp}.py"
    info = {"video": vc["slug"], "probe": probe, "frames": len(frames), "seconds": seconds, "counts": count_txt,
            "probe_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(probe.stat().st_mtime)), "shots": shots_path,
            "words": (f"{src[0]} {src[1]}" if anchored else src)}
    write_module(out, fx, dropped, events, info, src if anchored else None, anchored)
    ev_path = out.with_suffix(".events.json")
    ev_path.write_text(json.dumps({"probe": str(probe), "frames": len(frames), "seconds": seconds,
                                   "cuts_from": str(shots_path) if shots_path else "the probe", "events": [{"kind": e.kind, "t": round(e.t, 3), "frame": e.f, "frames": sorted(set([e.f] + e.frames)),
                                               "f_end": e.f_end, "what": e.what, "on": e.on, "shot": e.shot, "with_cut": e.with_cut}
                                              for e in events],
                                   "effects": [{"t": round(x.t, 3), "sound": SOUND_OF[x.sound], "expr": x.expr, "note": x.note} for x in fx],
                                   "dropped": [{"t": round(x.t, 3), "sound": SOUND_OF[x.sound], "note": x.note} for x in dropped]},
                                  indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} and {ev_path.name}")
    if a.compare:
        compare(fx, Path(a.compare), seconds)


if __name__ == "__main__":
    main()
