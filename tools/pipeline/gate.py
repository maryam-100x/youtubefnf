"""The pre-render gate: the goal is a first version with no real mistakes in it (freezes, flash frames, broken graphs and animations,
sound faults). Every kind of mistake a viewer can catch in a finished video has a machine check here, and `pipe.py <video> render`
refuses to start until the last gate passed on the code as it is (pipe.py checks the gate's stamp). A flag is fixed, or allowed in
videos/<video>/gate_allow.json with a reason and the frames that prove it (never "a false positive" from reasoning alone).

  PIPE tools/pipeline/pipe.py <video> gate [--reuse]
  PIPE tools/pipeline/pipe.py <video> gate --scope a-b,c-d [--out <report>]
        (the scoped gate: the gate confirms, it never discovers. Every builder and fixer runs it on their own shots before handing
        them back, until it is clean: the frame ranges, each widened to the whole shots it touches, probed fresh with 60 frames each
        side and their pictures, under the Remotion ticket; the rest of the film is the last full probe, read while the ticket is held
        and kept in memory. Every picture check B0-B23 runs: the per-frame and per-shot ones on the probed frames, the per-play ones on
        the plays touching the scope, TWICE on the scope's plays against every play of the film, ART_CLOSE on the 20 s round the scope,
        CARD_CLOSE and B23 on the whole film's code. The flags whose frames meet the ranges (a pair flag when one of its shots does),
        with the allows and the creator's sign-offs applied -> pipeline/gate_scope.md; the film's totals (CARD_TIME, DEVICE_SPREAD)
        listed apart, ART_SHARE left to the full gate. Never a pass: passed.txt, the probe, its stamp and snapshot, the still pictures,
        gate.md and the analysis cache stay the full gate's; no sound half, no coherency read. Exit 1 while a flag is left. Its files:
        pipeline/gate/scope/<tag>/. Its timings: standard/PIPELINE.md)
  PIPE tools/pipeline/gate.py <video> --probe-dir <dir> [--shots s.json --durs d.json --clips <dir>]
        (the analysis alone on an existing probe: to prove a check on an older probe)

How it sees: gate_probe.mjs renders every frame of the composition in the gate mode (src/gate.tsx): no video is fetched; every clip
reports the source second it shows, every text, picture, clip pane and drawn mark its real box. ~14 min for 13 minutes of film.

  B0  the composition is gated() in Root.tsx and plays video only through Clip/SpeedRamp (else the probe can't see its clips)
  B1  FREEZE  a clip asked past its file's last frame, in any graphic (a burst of short plays, a flip between two clips, a clip pane)
      STILL   a designed stretch (no clip on screen) standing still: qa_render's frozen test on the probe's pictures (a row of logos)
      HOLD    a held picture on a beat inside a play: 24/25-fps footage stored as 30 (a hitch several times a second)
  B2  FLASH   a cut, dissolve or fade of the source within 0.3 s of a play's exact in or out point, each confirmed on the picture (a cut
              = the next frame unlike this one, far below the clip's own frame-to-frame likeness)
  B3  GAP     a frame inside a shot where a clip pane drops out and comes back (a burst's black last frame)
  B4  TEXT_CUT text cut by the frame or its card; MARK_CUT a lit phrase pushed past the frame; TEXT_ON_TEXT; CREDITS_STACKED;
      TEXT_CUT_BY_PIC a picture's edge through text (a running year under a cover); OFF_FRAME an object half off the frame (a product
      cut-out); BOTTOM a big label under the player's controls (an on-screen counter); EMPTY_SLOT; PIC_ON_PIC two pictures drawn over
      each other (one logo on another)
  B4  LETTERBOX (Shorts only) a letterboxed source's black bars on screen; LETTERBOX_CUT (long form) a clip of a letterboxed source cut
      without its bars, so cropped and blown up; ASPECT a clip drawn at another shape than its file (a 3840x1608 cut declared 16:9)
  B7  TWICE   the same stretch of a source shown twice, under one clip name or two (the same dusk skyline in two cuts)
  B10 CAPTION_TWICE a stamp, count or label showing a word the captions show at the same time
  B9  CREDIT  a clip credited to another source than its own (shots of one official video credited to another)
  B5  MOVING_AT_CUT something still moving in a shot's last 0.25 s (a 2D-3D flip, a calendar); MARK_LATE a highlight drawing in the
      last 0.6 s; SHAKES more shakes than impact sounds; YOYO a change that springs back (a map snap)
  B6  SYNC    an effect with nothing happening on screen; a marker sound with no phrase lighting (a marker a second early)
  B7  REUSE   a clip the creator named as overused (gate_overused.json)
  B8  CUTOUT  chunks missing from a cut-out (half a face); CUTOUT_HALO a cut-out over its own blurred copy (a product box, a speaker);
      CUTOUT_ON_CARD a cut-out on a box
  B12 MARK_MOVES a box, ring, label or highlight that leaves its target: over a playing clip (it must be held while the mark shows), or
              sliding more than 2 px from its place in a still or page that moves under it (a mural's boxes drifting off as the clip
              pushes in); a mark riding with its picture is fine
  B13 TEXT_OVERLAP two visible texts whose letters intersect by more than 2 px each way (one label running 12 px into the next; B4's
              TEXT_ON_TEXT needs 15% of the smaller box and misses an edge sliver), or a text running more than 2 px out of its card
              (B4's TEXT_CUT sees only clipped text)
  B14 ROW_CENTRE a row of pictures (two or more on one floor at one height, CutoutRow's way) whose visible content (the pictures' alpha
              bounds and their name lines) sits more than 8 px off the frame's centre, or whose gaps differ by more than 8 px (a long
              name line running past its narrow picture)
  B3  BLANK   1-6 frames with nothing lit between pictures that fill the frame (a delayRender race)
      BLANK_LONG 0.5 s or more with nothing to see (no lit picture, no text): a critical failure to a viewer
  B15 KIT3_REFUSAL a kit3 piece refused its input on these frames (gate.tsx catches it per frame in the probe; the reason is the flag)
      CHECK_CRASHED one check crashed: a flag with the error, the other checks still read (one check never costs a whole gate run)
  B16 MARK_OFF / MARK_REDUNDANT a mark off its words or with nothing to pick out (qa_marks.py)
  B17 LIT_UNSAID a lit phrase whose words aren't said round it (qa_lit.py): to look at, not blocking
  B23 DEVICE_SPREAD one graphic component the main picture of more than 6 appearances of the film with no `// device: <why>` above them;
      ROUND_CROP a round crop of a screenshot as a shot's picture (Chip, PlacedIcon, kit3 Still's icons, a face circle over a clip), the
      two main people's portraits passing only where the words name both and the shot says `// device: portrait <why>` (circles all
      over a video read as a template; qa_devices.py, from the code, no probe)
  B24 TEXT_SHORT a text of ours at reading size on screen under its reading time (1.2 s, +0.03 s a character past 10), across cuts:
              a text that is gone before it can be read
  B25 MARK_SMALL a mark on a thing under 4% of the frame its picture never zooms into (1.6x within 0.7 s): a small thing is zoomed into
              quickly (kit3 Foot zoom)
  B4  UPSCALE a zoomed clip showing its file's pixels past 1.3x: a 1080p cut zoomed is soft (prep's 4K ZOOMED cuts)
  B25b MARK_BLINK a mark lit under 0.5 s that goes while its picture stays (two marks named together both stay)
  B26 OUTRO   the last line asks for a like and a comment, and the house SignOff never shows
  STILL_SOURCE a full-frame clip standing still in its own source: to look at, not blocking (the eye's call)
A flag means a fault (standard/PIPELINE.md sections 7-8): the by-design cases are told apart inside the checks, a stretch the creator
passed is [[gate.signed]] in video.toml, the eye's calls are listed apart; the probe is incremental and shift-aware after the first
full one (reprobe.py), and the per-play reads are cached by content (analysis_cache.json).
Credits, name lines, stamps and connector labels mark themselves (data-gate="credit" / "name" / "stamp" / "mid") and may sit on pictures;
a count-up's digit slots mark themselves data-gate="roll" (their digits pass the slot's edge by design: no TEXT_CUT); a mark into a picture
marks itself data-gate="mark" (B12; a hollow outline counts without it).
The sound half (A1-A11 + LOCK) is tools/sound/gate_sound.py."""
import argparse
import hashlib
import json
import os
import math
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MOTION, NODE, PY_EDIT, REPO, TOOLS, RemotionJob, Video, after_remotion, find_video, say, temp_env  # noqa: E402
sys.path.append(str(MOTION))
from codefiles import code_files  # noqa: E402   a video's code with the subfolder files it imports

FPS = 60


def fr(t):
    """A time in seconds -> its frame, the way the render places it (lib.tsx f(): JS Math.round, x.5 up). Python's round() is
    banker's (x.5 to even), so a cut on a half frame (a word at 97078.5) would sit a frame early in the gate: false REVERSE flags."""
    return int(np.floor(t * FPS + 0.5))
OVERUSED = Path(__file__).resolve().parent / "gate_overused.json"
FRAME = [1920, 1080]   # the composition's width and height, read from the probe (a Short is 1080x1920)


# ============================================================================================================================ the probe
def preflight(v):
    """B0: the probe sees only what goes through Clip/SpeedRamp and only in a gated() composition."""
    bad = []
    # Root.tsx, or a video's own root beside its code (src/v12/root12.tsx, bundled by its own entry src/v12_index.ts: run the gate
    # with QA_ENTRY=<that entry>; a film registered on its own root is still a gated film)
    roots = [MOTION / "src/Root.tsx"] + sorted((MOTION / "src").glob("*/root*.tsx"))
    if not any(re.search(rf'id="{re.escape(v.comp)}"\s+component={{gated\(', r.read_text(encoding="utf-8")) for r in roots):
        bad.append(f"B0 {v.comp} is not registered as gated({v.comp}) in src/Root.tsx or a src/*/root*.tsx: the layout probe can't run")
    for f in code_files(v.src_dir):   # its subfolders' files the film imports too (motion/codefiles.py)
        s = f.read_text(encoding="utf-8")
        if re.search(r"OffthreadVideo|Html5Video|<Video[\s>]|@remotion/media", s):
            bad.append(f"B0 {f.relative_to(v.src_dir.resolve()).as_posix()} plays video itself: only lib.tsx's Clip and kit2's SpeedRamp report what they show")
    return bad


def code_stamp(v, probe=False):
    """what the gate checked: the composition's code, the shared kit, the clips' lengths, the video's settings. `probe=True`: what the
    probe's pictures depend on, i.e. without gate_allow.json (an allow changes no frame, so an allow-only round never re-probes a whole
    film for hours; `--reuse` compares this one, the render's pass still the full stamp)"""
    h = hashlib.sha1()
    files = sorted(v.src_dir.glob("*.ts*")) + sorted(v.src_dir.glob("*.json")) + sorted(v.src_dir.glob("data/*.json"))
    # the subfolder files the film imports (rebuilt shots in a subfolder; placeholder words in a JSON import the import walk below never
    # follows): after the top level, so a video without subfolders keeps its stamp; a builder's preview root in a subfolder, imported by
    # nothing, stays out (editing it never voids a passed gate)
    top = {f.resolve() for f in files}
    files += [f for f in code_files(v.src_dir, (".ts", ".tsx", ".json")) if f.parent != v.src_dir.resolve() and f not in top]
    files += [MOTION / "src/lib.tsx", MOTION / "src/kit2/edit.tsx", MOTION / "src/gate.tsx", MOTION / "src/clipdurs.json", v.folder / "video.toml",
              v.folder / "script.md"] + ([] if probe else [v.folder / "gate_allow.json"])
    # every local module the composition imports, all the way down (a shared kit changed after the gate must void the stamp)
    seen, todo = set(), [f for f in files if f.suffix in (".ts", ".tsx")]
    while todo:
        f = todo.pop()
        if f in seen or not f.exists():
            continue
        seen.add(f)
        for m in re.finditer(r"from\s+'(\.{1,2}/[^']+)'", f.read_text(encoding="utf-8", errors="ignore")):
            base = (f.parent / m.group(1)).resolve()
            for c in (base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.tsx", base / "index.ts"):
                if c.exists():
                    todo.append(c)
                    break
    files += sorted(x for x in seen if x not in files)
    # the shared clip lengths: only the entries this video names (a clip cut for another video rewrites clipdurs.json, and that must
    # never void this video's passed gate)
    durs_p = MOTION / "src/clipdurs.json"
    if durs_p in files:
        files.remove(durs_p)
        text = "".join(f.read_text(encoding="utf-8", errors="ignore") for f in files if f.suffix in (".ts", ".tsx") and f.exists())
        durs = json.loads(durs_p.read_text(encoding="utf-8"))
        used = {k: durs[k] for k in sorted(durs) if Path(k).stem in text}
        h.update(json.dumps(used, sort_keys=True).encode())
    # the voice the sound gate heard: a re-voiced narration needs the gate again
    for f in (v.dj / "build/voice/narration.wav", v.dj / "build/captions/words.json"):
        if f.exists():
            h.update(f"{f.name}{f.stat().st_size}{int(f.stat().st_mtime)}".encode())
    for f in files:
        if f.exists():
            h.update(f.name.encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:16]


def run_probe(v, d, every=1, pics=False):
    import pipe  # the stall guard (pipe.run_watched)
    d.mkdir(parents=True, exist_ok=True)
    with RemotionJob(f"gate probe {v.id}", None):
        # to the composition's own last frame (gate_probe.mjs clamps the range to durationInFrames): never video.toml's guess (a toml
        # missing a few seconds would leave the tail out of the probe)
        r = pipe.run_watched([NODE, "gate_probe.mjs", d, "0.25", f"0-{max(v.frames(), 10 ** 8) - 1}", str(every)] + (["--png"] if pics else []), MOTION,
                             {"QA_COMP": v.comp, "QA_PUBLIC": v.pub.as_posix(), **temp_env()}, d / "probe.log", stall=300)
    after_remotion()
    if r.returncode != 0 or getattr(r, "stalled", False):
        raise SystemExit(f"gate: the probe failed{' (stalled)' if getattr(r, 'stalled', False) else ''}: {d / 'probe.log'}")
    return d / "probe.jsonl"


def _probe_frame(line):
    """the film frame a probe line is about: a layout line's "frame", a clip line's "abs"; None for anything else"""
    kind, _, body = line.partition("|")
    if kind not in ("layout", "clip"):
        return None
    try:
        o = json.loads(body)
    except ValueError:
        return None
    return o.get("frame") if kind == "layout" else o.get("abs")


def reprobe(v, d, ranges):
    """`--reprobe a-b,c-d` (a full probe of 188,000 frames takes ~75 min): probe only the frame ranges a fix touched and splice them
    into the last full probe.jsonl, every other frame's lines kept. Use it only when the fixes since that probe change nothing outside
    the given ranges (shots in section files, ranges = each changed shot's whole span plus a margin); a change to shared code (the
    video's design file, its pieces, its main composition, lib) or to timing needs the full probe. The log names the ranges, so a pass
    on a spliced probe can be told apart from a full one."""
    import pipe
    rd = d / "reprobe"
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    with RemotionJob(f"gate reprobe {v.id} ({ranges})", None):
        r = pipe.run_watched([NODE, "gate_probe.mjs", rd, "0.25", ranges, "1"], MOTION,
                             {"QA_COMP": v.comp, "QA_PUBLIC": v.pub.as_posix(), **temp_env()}, rd / "probe.log", stall=300)
    after_remotion()
    if r.returncode != 0 or getattr(r, "stalled", False):
        raise SystemExit(f"gate: the reprobe failed{' (stalled)' if getattr(r, 'stalled', False) else ''}: {rd / 'probe.log'}")
    spans = [tuple(int(x) for x in s.split("-")) for s in ranges.split(",")]
    inside = lambda f: f is not None and any(a <= f <= b for a, b in spans)
    old, new = d / "probe.jsonl", rd / "probe.jsonl"
    with open(old, encoding="utf-8") as fh:
        keep = [ln for ln in fh if not inside(_probe_frame(ln))]
    with open(new, encoding="utf-8") as fh:
        add = [ln for ln in fh if _probe_frame(ln) is not None]
    got = {_probe_frame(ln) for ln in add}
    lost = [f"{a}-{b}" for a, b in spans if not any(a <= f <= b for f in got)]
    if lost:
        raise SystemExit(f"gate: the reprobe wrote nothing for {', '.join(lost)}: {rd / 'probe.log'}")
    merged = sorted(keep + add, key=lambda ln: (_probe_frame(ln) if _probe_frame(ln) is not None else -1))
    for p_ in (d / "still").glob("element-*.jp*g") if (d / "still").exists() else []:   # their pictures show the old code
        m_ = re.search(r"(\d+)\.jpe?g$", p_.name)
        if m_ and inside(int(m_.group(1))):
            p_.unlink()
    tmp = d / "probe.jsonl.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(ln if ln.endswith("\n") else ln + "\n" for ln in merged)
    os.replace(tmp, old)
    say(f"  probe: {len(add)} lines re-probed in {ranges}, spliced into the last full probe ({len(keep)} kept)")
    return old


REFUSALS = {}   # frame -> the reason a piece refused to draw (gate.tsx's GateBoundary: kit3's own guards), read by check_refusals


def one_copy(items):
    """a picture stacked on an exact copy of itself is one picture on screen: kit3 SpotDim's `src=` draws the dim as the picture's own
    copy, filtered and masked, on the same box (marks.tsx: a backdrop filter goes soft under a camera's scale). Every check that counts
    pictures (B14's rows, the cards, the hero) would count it twice (a ROW_CENTRE "cover_a + cover_a"), so the later copy (same file,
    box within 1.5 px) is dropped here, where the probe is read, and the parent links (`pa`) are renumbered"""
    keep, seen, new = [], [], {}
    for i, it in enumerate(items):
        if it.get("k") == "img" and any(o["t"] == it["t"] and abs(o["x"] - it["x"]) <= 1.5 and abs(o["y"] - it["y"]) <= 1.5
                                        and abs(o["w"] - it["w"]) <= 1.5 and abs(o["h"] - it["h"]) <= 1.5 for o in seen):
            continue
        if it.get("k") == "img":
            seen.append(it)
        new[i] = len(keep)
        keep.append(it)
    if len(keep) == len(items):
        return items
    for it in keep:
        if it.get("pa", -1) >= 0:
            it["pa"] = new.get(it["pa"], -1)
    return keep


def load_probe(path):
    clips, layout = defaultdict(list), {}
    REFUSALS.clear()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            kind, _, body = line.partition("|")
            try:
                o = json.loads(body)
            except ValueError:
                continue
            if kind == "clip":
                clips[o["abs"]].append(o)
            elif kind == "layout":
                layout[o["frame"]] = one_copy(o["items"])
                AT_STARTS.update(o.get("ats", []))
                FRAME[0], FRAME[1] = o.get("W", FRAME[0]), o.get("H", FRAME[1])
            elif kind == "refusal":
                REFUSALS[o["frame"]] = o.get("msg", "")
    return clips, layout


def check_refusals():
    """KIT3_REFUSAL: a piece that refused its input on these frames (kit3 throws with the reason: a redundant mark, text out
    of its card, a mark lighting in the shot's last 0.6 s, a number card over blur). The probe logged it and drew nothing there; the
    reason is the flag. Fixed in the input, never allowed."""
    runs = defaultdict(list)
    for f, msg in REFUSALS.items():
        runs[msg].append(f)
    return [{"check": "KIT3_REFUSAL", "key": msg[:80], "at": f0, "to": f1, "what": f"{msg} ({(f1 - f0 + 1) / FPS:.2f} s refused)"}
            for msg, f0, f1 in runs_of(runs, 1)]


def crashed_flag(name, e):
    """CHECK_CRASHED: one check's crash never takes the gate run down (a crash in one check, e.g. qa_fades on a play a few frames
    long, would otherwise lose every other check's results with it). The crash is a flag that blocks the pass, with the error and
    where it was raised; every other check still reads. Fixed in the check (or its input), never allowed."""
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    at = f" ({Path(tb[-1].filename).name}:{tb[-1].lineno})" if tb else ""
    return {"check": "CHECK_CRASHED", "key": name, "at": 0, "to": 0,
            "what": f"{name} crashed: {type(e).__name__}: {str(e)[:200]}{at}; its flags are unknown until the check is fixed"}


def group_plays(clips):
    """one play = one clip shown on consecutive frames from one origin (the same file can show twice at once: a blurred backdrop + the
    picture); a SpeedRamp's origin moves, so its frames group by file alone"""
    runs = defaultdict(list)
    for f in sorted(clips):
        for c in clips[f]:
            key = (c["src"], "ramp") if c.get("ramp") else (c["src"], round(c["s"] - f / FPS * (c.get("rate") or 1), 2))
            runs[key].append((f, c))
    plays = []
    for (src, _), fr in runs.items():
        cur = [fr[0]]
        for a, b in zip(fr, fr[1:]):
            if b[0] - a[0] > 2:
                plays.append((src, cur))
                cur = []
            cur.append(b)
        plays.append((src, cur))
    out = []
    for src, fr in plays:
        out.append({"src": src, "f0": fr[0][0], "f1": fr[-1][0], "s0": fr[0][1]["s"], "s1": fr[-1][1]["s"], "rate": fr[-1][1].get("rate") or 1,
                    "fits": fr[-1][1].get("fits"), "n": len(fr)})
    return sorted(out, key=lambda p: p["f0"])


AT_STARTS = set()   # every <At> range's first frame the probe saw (lib.tsx data-gateat): a built Short's cuts


def shots_from_probe(layout, clips, fps=FPS):
    """A built Short has no SHOTS list (its pictures are <At> ranges): its cuts are where most of what's on screen changes at once
    (under 30% of the visible pictures, clip panes and texts carry over from the frame before) or a new clip pane mounts full-frame."""
    def keys(f):
        return {(i["k"], str(i["t"])) for i in layout.get(f, []) if i["op"] >= 0.3 and i["k"] in ("img", "clip") and i["w"] * i["h"] > 0.2 * 1080 * 1920}
    frames = sorted(layout)
    if AT_STARTS and frames:
        # the composition's own ranges (the guess below can merge a bar with the page after it or split a page in two, so MARK_LATE
        # and MOVING_AT_CUT would measure against cuts that aren't there)
        cuts = sorted({frames[0]} | {a for a in AT_STARTS if frames[0] < a <= frames[-1]})
        end = frames[-1] + 1
        return [{"at": a / fps, "end": b / fps} for a, b in zip(cuts, cuts[1:] + [end]) if b > a]
    cuts, prev = [frames[0]] if frames else [], None
    for f in frames:
        k = keys(f)
        if prev is not None and (k or prev) and len(k & prev) / max(1, len(k | prev)) < 0.3:
            cuts.append(f)
        prev = k
    end = frames[-1] + 1 if frames else 0
    return [{"at": a / fps, "end": b / fps} for a, b in zip(cuts, cuts[1:] + [end]) if b > a]


def mmss(f):
    t = f / FPS
    return f"{int(t // 60)}:{t % 60:05.2f}"


# ===================================================================================================================== the analysis cache
# Without it, every gate run re-reads every clip for B1 holds (~10 min on a long film), B2 flashes (~11 min) and fades (~6 min) and the
# still pass's source motion, though most plays haven't changed. Each of those is a function of the clip file and the stretch of it played,
# never of where the play sits in the film, so its answer is kept under a key of what it reads: the check and its version, the file's size
# and modification time, the source seconds (Bazel's action cache, by content; a re-cut clip has a new size or time, so a new key). A
# check whose code changes bumps its version in CHECK_VER and its old answers are never read again.
CHECK_VER = {"holds": 1, "flash": 1, "fades": 2, "srcmove": 1, "texture": 1, "music": 1, "footev": 1}
CACHE = {"path": None, "data": {}, "dirty": 0, "hits": 0, "miss": 0}


def cache_open(path):
    CACHE.update(path=Path(path), data={}, dirty=0, hits=0, miss=0)
    try:
        CACHE["data"] = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass


def cache_save():
    if CACHE["path"] and CACHE["dirty"]:
        tmp = CACHE["path"].with_suffix(".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(CACHE["data"]), encoding="utf-8")
        os.replace(tmp, CACHE["path"])
        CACHE["dirty"] = 0


def file_id(p):
    try:
        st = Path(p).stat()
        return f"{st.st_size}:{st.st_mtime_ns}"
    except OSError:
        return "missing"


def cached(kind, path, args, fn):
    """fn()'s answer for (kind, the file at path, args), from the cache when the same file and args were answered before"""
    k = f"{kind}{CHECK_VER[kind]}|{Path(path).name}|{file_id(path)}|{args}"
    if k in CACHE["data"]:
        CACHE["hits"] += 1
        return CACHE["data"][k]
    v = fn()
    CACHE["miss"] += 1
    CACHE["data"][k] = v
    CACHE["dirty"] += 1
    if CACHE["dirty"] >= 200:
        cache_save()
    return v


# ============================================================================================================================== B1-B3
def check_freezes(plays, durs):
    flags = []
    for p in plays:
        m = durs.get(p["src"])
        if not m:
            flags.append({"check": "FREEZE", "key": p["src"], "at": p["f0"], "what": f"{p['src']}: its length isn't in clipdurs.json"})
            continue
        last, fps = m
        over = p["s1"] - (last + 1 / fps)
        if over > 1e-3:
            frozen = over / max(p["rate"], 1e-6)
            flags.append({"check": "FREEZE", "key": Path(p["src"]).stem, "at": p["f1"] - round(frozen * FPS),
                          "what": f"{Path(p['src']).stem} frozen for its last {frozen:.2f} s (asked {p['s1']:.2f} s of a {last + 1 / fps:.2f}-s file)"})
    return flags


def gray_frames(path, w0, w1):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, w0):.3f}", "-t", f"{w1 - max(0.0, w0):.3f}", "-i", str(path), "-an",
                          "-vf", "scale=160:90,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (160 * 90)
    return np.frombuffer(raw[: n * 160 * 90], dtype=np.uint8).reshape(n, 90, 160).astype(np.float32) if n else None


GROUND_BLUR = 6.0   # px: a clip blurred this much (a Stage's ground is 8) shows neither its cadence nor a dissolve's double picture
GROUND_LIT = 0.35   # a clip dimmed under this (opacity x brightness; a Stage's ground is 0.42 behind its card) hides them as well


def hidden_ground(layout, p):
    """the play is a blurred or dimmed ground for most of its frames (lib.tsx's gate pane carries the video's filter, gate.tsx reads
    its blur): its holds and dissolves are not seen (grounds under a page would otherwise flag HOLD and DISSOLVE that no viewer sees)"""
    fs = [p["f0"], (p["f0"] + p["f1"]) // 2, p["f1"]]
    hid = 0
    for f in fs:
        its = [it for it in layout.get(f, []) if it["k"] == "clip" and str(it["t"]) == str(p["src"])]
        if its and all((it.get("bl") or 0) >= GROUND_BLUR or it["op"] * it.get("br", 1.0) < GROUND_LIT for it in its):
            hid += 1
    return hid >= 2


def check_holds(plays, pub, durs, layout=None):
    """uneven holds inside a play: how long each picture of the source stays on screen in our 60-fps film. 30-fps content stored at 60
    (every frame twice) or a 30-fps clip shows each picture 2 frames, evenly: smooth. 24-fps footage in a 30-fps file shows every 5th
    picture 4 frames instead of 2: a hitch five times a second. A hold = a picture on screen 4+ frames and
    at least 1.9x the play's usual; two or more inside a play (not its first or last pictures) flag."""
    flags = []
    for p in plays:
        if p.get("ramp"):
            continue
        f = pub / p["src"]
        if not f.exists():
            continue
        fps = (durs.get(p["src"]) or [0, 30])[1] or 30
        if layout is not None and hidden_ground(layout, p):
            continue
        h = cached("holds", f, f"{p['s0']:.4f}|{p['s1']:.4f}|{fps}|{p['rate']}", lambda: holds_of(f, p["s0"], p["s1"], fps, p["rate"]))
        if h:
            t, gap, hmax, usual = h
            f_at = p["f0"] + round((t[0] - p["s0"]) / max(p["rate"], 1e-6) * FPS)
            flags.append({"check": "HOLD", "key": Path(p["src"]).stem, "at": f_at,
                          "what": f"{Path(p['src']).stem}: a held picture every {gap:.2f} s ({len(t)} holds of {hmax:.0f} frames against the usual {usual:.0f}: 24/25-fps footage stored as {fps:.0f}) at "
                                  f"{', '.join(map(str, t[:6]))}{' ...' if len(t) > 6 else ''} s of the clip: a hitch on screen"})
    return flags


def holds_of(f, s0, s1, fps, rate):
    """the hold beat inside one play of a file: ([hold times in the source], gap s, longest hold, usual) or None (cached by file+span)"""
    fr = gray_frames(f, s0, s1 + 1 / fps)
    if fr is None or len(fr) < 8:
        return None
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    med = float(np.median(d))
    if med < 1.0:   # still footage: a hold isn't seen
        return None
    same = (d < 0.25 * med) & (d < 0.8)
    runs, start_i = [], 0
    for i, sm in enumerate(same):
        if not sm:
            runs.append((start_i, i - start_i + 1))
            start_i = i + 1
    runs.append((start_i, len(fr) - start_i))
    per = FPS / fps * max(rate, 1e-6) ** -1
    durs_r = [n * per for _, n in runs]
    if len(durs_r) < 6:
        return None
    usual = float(np.median(durs_r))
    holds = [(i0, n * per) for (i0, n) in runs[2:-2] if n * per >= max(4.0, 1.9 * usual) - 1e-6]
    # the hitch you see is a beat: a held picture every few frames (24 or 25 fps stored as 30). One long hold is the footage resting
    # (a logo settling, 28 frames): the picture's own content, not a cadence fault
    gaps = np.diff([i0 for i0, _ in holds]) if len(holds) >= 3 else np.array([])
    if len(holds) >= 3 and gaps.mean() > 0 and gaps.std() <= 0.35 * gaps.mean():
        return [round(s0 + i0 / fps, 2) for i0, _ in holds], float(gaps.mean() / fps), float(max(h for _, h in holds)), usual
    return None


def corr(a, b):
    """how alike two frames are (0 = unrelated, 1 = the same picture), on 40x22 grey: motion keeps it high, a cut drops it"""
    def small(x):
        h, w = x.shape
        return x[: h // 4 * 4, : w // 4 * 4].reshape(h // 4, 4, w // 4, 4).mean(axis=(1, 3)).ravel()
    u, v = small(a), small(b)
    u, v = u - u.mean(), v - v.mean()
    den = float(np.sqrt((u * u).sum() * (v * v).sum()))
    return float((u * v).sum() / den) if den > 1e-6 else 1.0


def edge_events(path, w0, w1, fps):
    """cuts, dissolves and fades in [w0, w1] of a clip, each confirmed on the picture: pipe.frame_events' candidates (a change far above
    the window's motion, a brightness jump, 3+ hot frames in a row) count as a cut only when the frames on either side are different
    pictures (corr < 0.6: a drive under a bridge, 0.25 s "of the next shot" by a plain change test, is one continuous take); a fade
    only when the brightness climbs out of black (or falls into it) steadily over 6+ frames, not a dark stage's lights flickering"""
    fr = gray_frames(path, w0, w1)
    if fr is None or len(fr) < 3:
        return [], []
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    lum = fr.mean(axis=(1, 2))
    med = float(np.median(d[d > 0.05])) if (d > 0.05).any() else 0.0
    t = w0 + np.arange(1, len(fr)) / fps
    # a cut: one step where the picture is suddenly unlike the one before, an isolated dip below the steps around it (fast motion, a
    # flash going off, a camera whip lower several steps in a row). Repeated frames are dropped first, so every step is one real picture
    # (24-fps footage stored as 30 makes every 5th step a double step). Measured: real cuts 0.63 (a drive cut to 3 frames of another
    # drive: same street, same dashcam stamp; its neighbours 0.99/0.92), 0.08, -0.37, 0.39, -0.12; nine continuous clips that plainer
    # tests called cuts (a cyclist leaving the frame, a fireworks burst, a crowd pan, a concert camera) all stay above it
    dup = max(0.5, 0.3 * float(np.median(d)))   # a repeat, or a near-repeat a re-encode left slightly different
    keep = [0] + [k + 1 for k in range(len(d)) if d[k] > dup]
    cc = np.array([corr(fr[keep[j]], fr[keep[j + 1]]) for j in range(len(keep) - 1)])
    cuts = []
    for j, c in enumerate(cc):
        if c >= 0.8:
            continue
        nb = cc[max(0, j - 1): j].tolist() + cc[j + 1: j + 2].tolist()
        # 3.5x as unlike as its least alike neighbour: a cut stands out of its own footage (0.37 against 0.08); a fast crowd pan whose
        # steps wander between 0.44 and 0.86 (3x at most) doesn't
        if (1 - c) >= 3.5 * max(0.03, 1 - (min(nb) if nb else 1.0)):
            cuts.append(round(float(w0 + keep[j + 1] / fps), 3))
    hot = d >= max(2.5, 8.0 * med)
    k = 0
    while k < len(d):
        if hot[k]:
            j = k
            while j < len(d) and hot[j]:
                j += 1
            if j - k >= 3 and corr(fr[k], fr[min(j, len(fr) - 1)]) < 0.6:
                cuts.append(round(float(t[k]), 3))
            k = j
        else:
            k += 1
    fades = []
    for a in range(0, max(1, len(lum) - 6)):
        seg = lum[a: a + 8]
        if len(seg) < 6:
            break
        steps = np.diff(seg)
        rising = (steps >= -0.3).mean() >= 0.85 and seg[-1] - seg[0] >= 8 and seg[0] < 12
        falling = (steps <= 0.3).mean() >= 0.85 and seg[0] - seg[-1] >= 8 and seg[-1] < 12
        if rising or falling:
            fades.append((round(w0 + a / fps, 3), round(w0 + (a + len(seg) - 1) / fps, 3), round(float(seg[0]), 1), round(float(seg[-1]), 1)))
            break
    return sorted(set(cuts)), fades


def check_flashes(plays, pub, durs, edge=0.3):
    flags = []
    for p in plays:
        f = pub / p["src"]
        if not f.exists() or p["f1"] - p["f0"] < 2:
            continue
        fps = (durs.get(p["src"]) or [0, 30])[1] or 30
        short = FRAME[1] > FRAME[0]
        r = cached("flash", f, f"{p['s0']:.4f}|{p['s1']:.4f}|{fps}|{edge}|{int(short)}", lambda: flash_of(f, p["s0"], p["s1"], fps, edge, short))
        if r:
            what, at_head = r
            flags.append({"check": "FLASH", "key": Path(p["src"]).stem, "at": p["f0"] if at_head else p["f1"],
                          "what": f"{Path(p['src']).stem} [{p['s0']:.2f}-{p['s1'] + 1 / fps:.2f}]: " + "; ".join(what)})
    return flags


def flash_of(f, s0, s1, fps, edge, short):
    """one play's edge events: ([what], at its head?) or None (cached by file+span)"""
    t_in, t_out = s0, s1 + 1 / fps
    hc, hf = edge_events(f, max(0.0, t_in - 0.3), min(t_out, t_in + edge + 0.5), fps)
    tc, tf = edge_events(f, max(t_in, t_out - edge - 0.5), t_out + 0.3, fps)
    cuts = sorted({round(c, 3) for c in hc + tc})
    head = [c for c in cuts if t_in + 0.5 / fps < c < t_in + edge]
    tail = [c for c in cuts if t_out - edge < c < t_out - 0.5 / fps]
    hfade = [x for x in hf if x[0] < t_in + edge and x[1] > t_in + 0.02]
    tfade = [x for x in tf if x[1] > t_out - edge and x[0] < t_out - 0.02]
    what = []
    if head:
        what.append(f"opens on {max(head) - t_in:.2f} s of the shot before (its cut at {max(head):.2f})")
    if tail:
        what.append(f"ends on {t_out - min(tail):.2f} s of the next shot (its cut at {min(tail):.2f})")
    if hfade:
        what.append(f"opens in a fade ({hfade[0][2]:.0f} -> {hfade[0][3]:.0f} grey)")
    if tfade:
        what.append(f"ends in a fade ({tfade[0][2]:.0f} -> {tfade[0][3]:.0f} grey)")
    # a Short shows one shot of its source per play (standard/SHORTS.md): a cut anywhere inside it is a second picture the edit didn't
    # choose (a source cutting to its next shot 0.43 s before the play's end)
    if short and t_out - t_in > 2 * edge:
        mc, _ = edge_events(f, t_in, t_out, fps)
        mid = sorted({round(c, 3) for c in mc if t_in + edge <= c <= t_out - edge})
        if mid:
            what.append(f"cuts to another shot of its source inside the play (at {', '.join(f'{c:.2f}' for c in mid)})")
    return (what, bool(head or hfade)) if what else None


def check_gaps(clips, shots):
    """a clip pane that drops out for 1-3 frames inside a shot and comes back: a black or empty frame in the render"""
    flags = []
    for s in shots:
        a, b = fr(s["at"]), fr(s["end"])
        n = [len(clips.get(f, [])) for f in range(a, b)]
        i = 1
        while i < len(n) - 1:
            if n[i] < n[i - 1]:
                j = i
                while j < len(n) and j - i < 4 and n[j] < n[i - 1]:
                    j += 1
                if j < len(n) and j - i < 4 and n[j] >= n[i - 1]:
                    flags.append({"check": "GAP", "key": f"{a + i}", "at": a + i,
                                  "what": f"{j - i} frame(s) with {n[i]} clip(s) where the frames around show {n[i - 1]}: an empty or black frame"})
                i = j
            i += 1
    return flags


def lit_area(items, W, H):
    """the share of the frame lit pictures (img and clip panes at opacity x brightness 0.3+) cover, by their visible boxes"""
    a = 0.0
    for it in items:
        if it["k"] in ("img", "clip") and it["op"] * it.get("br", 1.0) >= 0.3:
            r = vis(it, W, H)
            a = max(a, area(r) / (W * H)) if r else a
    return a


def check_blank(layout, most=6, near=8):
    """B3 BLANK: 1-6 frames on which nothing lit is drawn, between frames where a picture fills most of the frame within 8 frames on
    both sides. It reads like a flash frame: typically a delayRender released before a Receipt's ground video mounted, so each render
    tab's first frame of it draws no ground; the probe renders with tabs too and loses the same frames the render does"""
    W, H = FRAME
    fs = sorted(layout)
    lit = {f: lit_area(layout[f], W, H) for f in fs}
    flags, i = [], 0
    while i < len(fs):
        f = fs[i]
        if lit[f] >= 0.02:
            i += 1
            continue
        j = i
        while j < len(fs) and lit[fs[j]] < 0.02 and fs[j] - f < most + 1:
            j += 1
        n = fs[j - 1] - f + 1
        if n <= most and j < len(fs) and lit[fs[j]] >= 0.5:
            before = [lit.get(g, 0) for g in range(f - near, f)]
            if before and max(before) >= 0.5 and lit.get(f - 1, 0) >= 0.5:
                flags.append({"check": "BLANK", "key": f"{f}", "at": f, "to": fs[j - 1],
                              "what": f"{n} frame(s) with nothing lit between pictures that fill the frame: a lost picture (a delayRender released "
                                      f"before what it waited for mounted, or a clip pane missing)"})
        i = max(j, i + 1)
    return flags


def check_blank_long(layout, need=0.5):
    """B3 BLANK_LONG: `need` seconds or more on which nothing is there to see: no lit picture (lit_area under 2% of the frame) and no
    text at half opacity (a board standing on its dark ground before its first tile). A frame never opens on blank: what it shows pops
    up within the first 0.5 s, since even a second of plain blank costs viewers. A run touching the measured frames' edge isn't judged."""
    W, H = FRAME
    fs = sorted(layout)
    if not fs:
        return []

    def empty(f):
        items = layout[f] or []
        if lit_area(items, W, H) >= 0.02:
            return False
        return not any(it["k"] == "text" and it["op"] >= 0.5 and vis(it, W, H) for it in items)

    flags, run = [], []
    for f in fs + [None]:
        if f is not None and empty(f) and (not run or f - run[-1] <= 2):
            run.append(f)
            continue
        if run and run[0] > fs[0] and run[-1] < fs[-1] and (run[-1] - run[0] + 1) / FPS >= need:
            flags.append({"check": "BLANK_LONG", "key": f"{run[0]}", "at": run[0], "to": run[-1],
                          "what": f"{(run[-1] - run[0] + 1) / FPS:.2f} s with nothing to see (no lit picture, no text): a frame never opens "
                                  f"on blank; the graphic's pieces are on screen from its first frame"})
        run = [f] if (f is not None and empty(f)) else []
    return flags


# ================================================================================================================================ B4
def ink(it):
    """a text's letters, not its line box: one line's box is ~1.2x the font size, the letters ~0.75x of it in the middle (a "16x" over
    an "8 GB" touches by line boxes only, 30 px apart by their letters)"""
    if it["k"] == "text" and it["fs"] and it["h"] < 1.8 * it["fs"]:
        pad = max(0.0, (it["h"] - 0.75 * it["fs"]) / 2)
        return it["x"], it["y"] + pad, it["w"], it["h"] - 2 * pad
    return it["x"], it["y"], it["w"], it["h"]


def vis(it, W, H):
    """the part of an item the viewer sees: its box (a text's letters) inside its overflow parents and the frame"""
    x, y, w, h = ink(it)
    x0, y0 = max(x, it["cx0"], 0), max(y, it["cy0"], 0)
    x1, y1 = min(x + w, it["cx1"], W), min(y + h, it["cy1"], H)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1]) if r else 0.0


def on_picture(items, i, lit=0.3, grow=2.0):
    """the lit picture (img or clip pane) under item i's centre, drawn before it and over `grow` times its area: an outline there is a
    mark pointing into the picture, not an empty slot"""
    it = items[i]
    cx, cy = it["x"] + it["w"] / 2, it["y"] + it["h"] / 2
    for o in items[:i]:
        if o["k"] in ("img", "clip") and o["op"] * o.get("br", 1.0) >= lit and o["x"] <= cx <= o["x"] + o["w"] and o["y"] <= cy <= o["y"] + o["h"] \
                and o["w"] * o["h"] > grow * it["w"] * it["h"]:
            return o
    return None


def runs_of(frames_flags, min_len):
    """{key: [frames]} -> [(key, first, last)] for runs of at least min_len consecutive frames"""
    out = []
    for key, fs in frames_flags.items():
        fs = sorted(set(fs))
        start = prev = fs[0]
        for f in fs[1:] + [None]:
            if f is not None and f - prev <= 2:
                prev = f
                continue
            if prev - start + 1 >= min_len:
                out.append((key, start, prev))
            if f is not None:
                start = prev = f
    return out


FLY_PX = 3.0   # px a frame at 1080 lines (180 px/s at 60 fps): words moving faster are in flight, not being read


def text_speeds(items, prev, H):
    """{item index: px moved since the frame before, scaled to 1080 lines} for each text, matched to the nearest same words one frame
    earlier; a word that wasn't there gets 0 (a card's shards flying apart move 5-18 px a frame at their median: words crossing or
    leaving the frame in flight are an exit by design, words at rest are what a viewer reads)"""
    was = defaultdict(list)
    for it in prev or []:
        if it["k"] == "text" and it["op"] >= 0.3:
            was[it["t"]].append((it["x"] + it["w"] / 2, it["y"] + it["h"] / 2))
    out = {}
    for i, it in enumerate(items):
        if it["k"] == "text" and was.get(it["t"]):
            c = (it["x"] + it["w"] / 2, it["y"] + it["h"] / 2)
            out[i] = min(math.dist(c, p) for p in was[it["t"]]) * 1080 / max(H, 1)
    return out


def check_layout(layout):
    hits = defaultdict(list)
    info = {}
    for f in sorted(layout):
        items = layout[f]
        if not items:
            continue
        W, H = FRAME
        sp = text_speeds(items, layout.get(f - 1), H)
        fly = {i for i, s in sp.items() if s >= FLY_PX}
        texts = []
        anc = {}
        for i, it in enumerate(items):
            chain, q = set(), it.get("pa", -1)
            while q is not None and 0 <= q < len(items) and q not in chain:
                chain.add(q)
                q = items[q].get("pa", -1)
            anc[i] = chain
        for i, it in enumerate(items):
            if it["op"] < 0.3:
                continue
            v = vis(it, W, H)
            if not v:
                continue
            ix, iy, iw, ih = ink(it)
            full = area((ix, iy, ix + iw, iy + ih))
            seen = area(v) / full if full else 1.0
            if it["k"] == "text":
                texts.append((i, it, v))
                # a count-up's digits roll through their slots by design (SceneNumber marks its slots data-gate="roll"; a count would
                # otherwise give one TEXT_CUT flag per digit passing its slot's edge)
                if seen < 0.93 and it["w"] * it["h"] > 400 and it["g"] != "roll" and i not in fly:
                    edge = "the frame" if (it["x"] < -2 or it["y"] < -2 or it["x"] + it["w"] > W + 2 or it["y"] + it["h"] > H + 2) else "its card"
                    k = ("TEXT_CUT", it["t"])
                    hits[k].append(f)
                    info[k] = f"\"{it['t']}\" cut by {edge} ({seen:.0%} of it shows)"
                if it["fs"] >= 40 and it["y"] + it["h"] > 0.9 * H and it["g"] != "credit":
                    k = ("BOTTOM", it["t"])
                    hits[k].append(f)
                    info[k] = f"\"{it['t']}\" ({it['fs']:.0f} px) in the bottom strip, under the player's controls and captions"
            elif it["k"] in ("img", "clip") and it["w"] < 0.9 * W and it["h"] < 0.9 * H:
                inside_card = it["cx0"] > -1e8 and (it["cx1"] - it["cx0"]) < 0.98 * W and it["cx0"] >= -2 and it["cx1"] <= W + 2 \
                    and it["cy0"] >= -2 and it["cy1"] <= H + 2
                on_frame = area((max(it["x"], 0), max(it["y"], 0), min(it["x"] + it["w"], W), min(it["y"] + it["h"], H))) / full if full else 1
                if not inside_card and 0.12 < on_frame < 0.88:
                    k = ("OFF_FRAME", it["t"])
                    hits[k].append(f)
                    info[k] = f"{Path(str(it['t'])).name} only {on_frame:.0%} inside the frame"
        # a lit phrase pushed past the frame's edge: a highlight (a short, wide box over a page) partly outside the frame (a phrase past
        # the right edge after a mark-centred push; the lit phrase shows whole)
        for it in items:
            if it["k"] == "box" and it["h"] < 140 and it["w"] > 40 and it["op"] >= 0.5:
                on = area((max(it["x"], 0), max(it["y"], 0), min(it["x"] + it["w"], W), min(it["y"] + it["h"], H))) / max(it["w"] * it["h"], 1)
                if 0.05 < on < 0.95:
                    k = ("MARK_CUT", f"{round(it['y'] / 30)}")
                    hits[k].append(f)
                    info[k] = f"a lit phrase only {on:.0%} inside the frame (its box at {it['x']:.0f},{it['y']:.0f}, {it['w']:.0f} wide)"
        # two credits at once, one on the other (a map's source credit stacked on its outlines' credit)
        # a credit: marked data-gate="credit", or (code without the marks) a 26-28-px line at the frame's foot; a map's 30-px place name with
        # its small "1890 survey" caption is a label, not two credits
        small = [it for it in items if it["k"] == "text" and it["op"] >= 0.5 and it["y"] > 0.85 * H
                 and (it["g"] == "credit" or (not it["g"] and it["fs"] and 25 <= it["fs"] <= 28.5))]
        for x in range(len(small)):
            for y in range(x + 1, len(small)):
                a_, b_ = small[x], small[y]
                if a_["t"] != b_["t"] and a_["x"] < b_["x"] + b_["w"] and b_["x"] < a_["x"] + a_["w"] and                         abs((a_["y"] + a_["h"] / 2) - (b_["y"] + b_["h"] / 2)) < 1.6 * max(a_["h"], b_["h"]):
                    k = ("CREDITS_STACKED", f"{a_['t']} | {b_['t']}")
                    hits[k].append(f)
                    info[k] = f"two credits at once, one on the other: \"{a_['t']}\" and \"{b_['t']}\""
        # an empty slot: a hollow box (an outline, nothing filled) with no picture, text or clip in it (empty bars get filled).
        # A mark is not a slot (marks round words inside a page capture are outlines too): an outline named a mark (data-gate="mark"),
        # or lying on a lit picture bigger than itself, points into that picture
        for bi, it in enumerate(items):
            if it["k"] != "box" or not it.get("e") or it["op"] < 0.4 or it["w"] * it["h"] < 0.01 * W * H or it["w"] > 0.9 * W:
                continue
            if it.get("g") == "mark" or on_picture(items, bi):
                continue
            inside = any(o is not it and o["k"] in ("img", "text", "clip") and o["op"] >= 0.3 and it["x"] <= o["x"] + o["w"] / 2 <= it["x"] + it["w"]
                         and it["y"] <= o["y"] + o["h"] / 2 <= it["y"] + it["h"] for o in items)
            if not inside:
                k = ("EMPTY_SLOT", f"{round(it['x'] / 20)},{round(it['y'] / 20)}")
                hits[k].append(f)
                info[k] = f"an empty outlined slot at {it['x']:.0f},{it['y']:.0f} ({it['w']:.0f}x{it['h']:.0f})"
        # a picture's edge cutting through text: its letters partly on a cover or cut-out it doesn't belong to (a running year coming to
        # rest with a fifth of it under a cover). A label wholly on its picture (a name on a photo, a credit on a page, a duration on a
        # thumbnail) or wholly off it is the design
        pics = [(j, o) for j, o in enumerate(items) if o["k"] == "img" and o["op"] >= 0.5 and o["w"] < 0.9 * W and o["h"] < 0.9 * H]
        for i, it, va in texts:
            if it["g"] in ("credit", "name", "mid", "stamp"):   # placed over pictures by design (the components mark themselves: data-gate)
                continue
            for j, o in pics:
                if j in anc.get(i, set()) or i in anc.get(j, set()):
                    continue
                vb = vis(o, W, H)
                if not vb:
                    continue
                ov = area((max(va[0], vb[0]), max(va[1], vb[1]), min(va[2], vb[2]), min(va[3], vb[3]))) if va[0] < vb[2] and vb[0] < va[2] and va[1] < vb[3] and vb[1] < va[3] else 0
                share = ov / max(area(va), 1)
                if 0.08 < share < 0.85:
                    k = ("TEXT_CUT_BY_PIC", f"{it['fs']:.0f}|{Path(str(o['t'])).name}")
                    hits[k].append(f)
                    info[k] = f"\"{it['t']}\" half on {Path(str(o['t'])).name}: the picture's edge runs through its letters ({share:.0%} on it)"
        # text on text: two words' boxes overlapping, neither inside the other's element; a count's rolling digit slots pass each other
        # by design (data-gate="roll": a counter's comma meeting a passing 9 mid-roll)
        for x in range(len(texts)):
            for y in range(x + 1, len(texts)):
                (i, a, va), (j, b, vb) = texts[x], texts[y]
                if i in anc[j] or j in anc[i] or a["t"] == b["t"] or "roll" in (a.get("g"), b.get("g")) or i in fly or j in fly:
                    continue
                ov = area((max(va[0], vb[0]), max(va[1], vb[1]), min(va[2], vb[2]), min(va[3], vb[3]))) if va[0] < vb[2] and vb[0] < va[2] and va[1] < vb[3] and vb[1] < va[3] else 0
                if ov > 0.15 * min(area(va), area(vb)):
                    k = ("TEXT_ON_TEXT", f"{a['t']} | {b['t']}")
                    hits[k].append(f)
                    info[k] = f"\"{a['t']}\" over \"{b['t']}\""
    flags = []
    need = {"TEXT_CUT": 10, "BOTTOM": 20, "OFF_FRAME": 30, "TEXT_ON_TEXT": 10, "EMPTY_SLOT": 30, "TEXT_CUT_BY_PIC": 10, "MARK_CUT": 10, "CREDITS_STACKED": 10}
    for (check, key), f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= need[check]:
            flags.append({"check": check, "key": str(key)[:80], "at": f0, "to": f1, "what": info[(check, key)] + f" for {(f1 - f0 + 1) / FPS:.2f} s"})
    return flags


# ================================================================================================================================ B5
def track(layout, f0, f1):
    """{item key: {frame: (cx, cy, w, h, op)}} for f0..f1; an item's key is its kind and text/file, numbered when it shows twice"""
    tr = defaultdict(dict)
    last = {"box": [], "svg": []}   # the unnamed shapes on the frame before: [(track id, cx, cy, w, h)]
    nid = [0]
    for f in range(f0, f1 + 1):
        seen = defaultdict(int)
        shapes = {"box": [], "svg": []}
        for it in layout.get(f, []):
            if it["k"] not in ("text", "img", "clip", "svg", "box") or it["op"] < 0.05:
                continue
            # a receipt's browser window (data-gate="frame": its bar, dots and address field) only pushes with the page: an address field
            # growing wider would read as a highlight drawing (MARK_LATE) and its unnamed boxes as swapping places (MOVING_AT_CUT)
            if it.get("g") == "frame" and it["k"] in ("box", "svg"):
                continue
            if it["k"] in ("box", "svg"):
                shapes[it["k"]].append(it)
                continue
            base = (it["k"], it["t"])
            n = seen[base]
            seen[base] += 1
            tr[base + (n,)][f] = (it["x"] + it["w"] / 2, it["y"] + it["h"] / 2, it["w"], it["h"], it["op"], it.get("c", 0))
        # shapes have no name: each is followed to the nearest shape of the frame before (place and size), never by its order or a size
        # bucket (a chart's bars growing staggered change size buckets and swap keys, which would read as "49 px a frame" at the cut and
        # as shakes while the bars stand still)
        for k, its in shapes.items():
            cands = sorted(((abs(it["x"] + it["w"] / 2 - p[1]) + abs(it["y"] + it["h"] / 2 - p[2]) + abs(it["w"] - p[3]) + abs(it["h"] - p[4]), j, q)
                            for j, it in enumerate(its) for q, p in enumerate(last[k])), key=lambda c: c[0])
            took, used, now = {}, set(), []
            for cost, j, q in cands:
                if cost > 150 or j in took or q in used:
                    continue
                took[j] = last[k][q][0]
                used.add(q)
            for j, it in enumerate(its):
                if j not in took:
                    nid[0] += 1
                    took[j] = nid[0]
                cx, cy = it["x"] + it["w"] / 2, it["y"] + it["h"] / 2
                tr[(k, it["t"], "#", took[j])][f] = (cx, cy, it["w"], it["h"], it["op"], it.get("c", 0))
                now.append((took[j], cx, cy, it["w"], it["h"]))
            last[k] = now
    return tr


def check_motion(layout, shots, effects=()):
    hits = [round(t * FPS) for t, _, _ in effects]
    flags = []
    for s in shots:
        a, b = fr(s["at"]), fr(s["end"]) - 1
        if b - a < 30:
            continue
        tr = track(layout, a, b)
        moving = []
        events = []
        for key, pts in tr.items():
            fs = sorted(pts)
            if len(fs) < 10 or key[0] in ("box", "svg") and pts[fs[-1]][2] * pts[fs[-1]][3] < 400:
                continue
            sp = []
            for f, g in zip(fs, fs[1:]):
                if g - f != 1:
                    continue
                p, q = pts[f], pts[g]
                sp.append((g, abs(q[0] - p[0]) + abs(q[1] - p[1]), abs(q[2] - p[2]) / max(p[2], 1), q[4] - p[4], q[0] - p[0], q[1] - p[1]))
            if not sp:
                continue
            # still moving at the cut: in the last 0.25 s it moves fast, faster than its own steady drift, and it's not leaving.
            # Speeds over two frames: a pan with `lock` steps on its clip's 30-fps frames (0, 2v, 0, 2v ... in the 60-fps Short), and
            # one-frame speeds make its steady drift read as ~0 and every step at the cut as a jump (a steady pan's probe dx: -31.4, 0,
            # -31.5, 0 ... -33.1, 0)
            spd = {x[0]: x[1] for x in sp}
            sm = {g: (v_ + spd[g - 1]) / 2 if g - 1 in spd else v_ for g, v_ in spd.items()}
            tail = [x for x in sp if x[0] > b - 15]
            body = [x for x in sp if x[0] <= b - 15]
            drift = float(np.median([sm[x[0]] for x in body])) if body else 0.0
            # (a typing caret still running at the cut counts: the typing is unfinished at the cut; end it 0.35 s before the cut)
            if tail and fs[-1] == b and pts[b][4] >= 0.3:
                fast = max(sm[x[0]] for x in tail)
                grow = max(x[2] for x in tail)
                if (fast > 6 and fast > 2.5 * drift + 2) or grow > 0.02:
                    moving.append((key, fast, grow))
            # shakes and pulses: direction flips of 3 px or more, grouped into events 0.25 s apart
            flips = []
            for u, w in zip(sp, sp[1:]):
                if (u[4] * w[4] + u[5] * w[5]) < 0 and min(abs(u[4]) + abs(u[5]), abs(w[4]) + abs(w[5])) >= 3:
                    flips.append(w[0])
            ev, last = 0, -999
            for f in flips:
                if f - last > 15 and not any(abs(f - h) <= 18 for h in hits):
                    ev += 1
                last = f
            if ev >= 2:
                events.append((key, ev))
        # a yo-yo: something at rest shrinks (or grows) by 15%+ and springs back within a second (a map to 72% and back to full on
        # "smaller": a change shrinks and stays)
        yoyo = []
        for key, pts in tr.items():
            if key[0] not in ("img", "clip", "box", "svg") or len(pts) < 30:
                continue
            fs = sorted(pts)
            ws = [pts[f][2] for f in fs]
            for i in range(10, len(fs) - 5):
                base = ws[i - 1]
                if base < 80 or max(ws[i - 10:i]) - min(ws[i - 10:i]) > 0.02 * base:   # not at rest before
                    continue
                low = min(range(i, min(i + 30, len(ws))), key=lambda j: ws[j])
                if ws[low] > 0.85 * base:
                    continue
                back = [j for j in range(low, min(low + 40, len(ws))) if ws[j] >= 0.95 * base]
                if back:
                    yoyo.append((key, fs[i], ws[low] / base))
                    break
        if yoyo:
            k = yoyo[0]
            flags.append({"check": "YOYO", "key": f"{a}", "at": k[1], "to": k[1] + 60,
                          "what": f"{k[0][0]} '{str(k[0][1])[:40]}' shrinks to {k[2]:.0%} and springs back: a change on screen stays"})
        # a move that goes back: a picture's centre travels 30 px or more one way inside the shot and then 8 px or more back (a page's
        # zoom-out that pans up and then down: its centre y 0 -> 581 -> 562 as its top edge is clamped mid-move). One way only.
        for key, pts in tr.items():
            if key[0] not in ("img", "clip") or len(pts) < 20:
                continue
            fs = sorted(pts)
            if pts[fs[-1]][2] < 600:
                continue
            for ax, name in ((0, "x"), (1, "y")):
                v = [pts[f][ax] for f in fs]
                for ext in (max(range(len(v)), key=lambda i: v[i]), min(range(len(v)), key=lambda i: v[i])):
                    if 0 < ext < len(v) - 1 and abs(v[ext] - v[0]) >= 30 and abs(v[ext] - v[-1]) >= 8:
                        flags.append({"check": "REVERSE", "key": f"{key[1]}", "at": fs[ext], "to": fs[-1],
                                      "what": f"{key[0]} '{str(key[1])[:40]}' moves {name} {v[0]:.0f} -> {v[ext]:.0f} -> {v[-1]:.0f}: it goes one way and "
                                              f"then {abs(v[ext] - v[-1]):.0f} px back (one move, one way)"})
                        break
                else:
                    continue
                break
        # a highlight still drawing within 0.6 s of its page's cut (every mark ends at least 0.6 s before the cut; a lit phrase still
        # growing as the shot cuts is never read)
        late = []
        for key, pts in tr.items():
            if key[0] != "box":
                continue
            fs = [f for f in sorted(pts) if f >= b - 36]
            # drawing = wider but not taller (a page's push makes it both)
            if len(fs) >= 2 and fs[-1] == b and pts[b][3] < 140 and pts[b][2] > 40 and \
                    pts[fs[-1]][2] / max(pts[fs[0]][2], 1) - pts[fs[-1]][3] / max(pts[fs[0]][3], 1) > 0.03:
                late.append(key)
        if late:
            flags.append({"check": "MARK_LATE", "key": f"{a}", "at": b - 36, "to": b,
                          "what": f"{len(late)} highlight(s) still drawing in the last 0.6 s before the cut"})
        if moving:
            k = max(moving, key=lambda m: m[1])
            flags.append({"check": "MOVING_AT_CUT", "key": f"{a}", "at": b - 15, "to": b,
                          "what": f"{len(moving)} thing(s) still moving in the shot's last 0.25 s, e.g. {k[0][0]} '{str(k[0][1])[:40]}' {k[1]:.0f} px a frame"})
        if events:
            k = max(events, key=lambda e: e[1])
            flags.append({"check": "SHAKES", "key": f"{a}", "at": a, "to": b,
                          "what": f"{k[0][0]} '{str(k[0][1])[:40]}' shakes or pulses {k[1]} times in one shot with no impact sound on them (one impact, one shake)"})
    return flags


# ================================================================================================================================ B6
def effects_from_cues(v):
    """the effects the video's cue sheet places: (impact second, name, note), read from the sheet itself before any mix exists (an old
    score report would leave a first gate with no effects to check, and a later one with an out-of-date list)"""
    S = v.section("score") if hasattr(v, "section") else {}
    cues = v.folder / S["cues"] if S.get("cues") else None
    if not cues or not cues.exists():
        return None
    code = ("import json, runpy, sys; m = runpy.run_path(sys.argv[1]); "
            "print('EFFECTS' + json.dumps([[s.t, __import__('pathlib').Path(str(s.path)).stem, s.note] for s in m.get('SFX', [])])); "
            "print('BEDS' + json.dumps([[str(c.path), c.t0, c.t1, c.src, list(c.align) if c.align else None, [list(x) for x in (c.auto or [])]] "
            "for c in m.get('CUES', [])]))")
    r = subprocess.run([str(PY_EDIT), "-c", code, str(cues)], capture_output=True, text=True, cwd=str(REPO), env={**__import__('os').environ, "PYTHONUTF8": "1"})
    m = re.search(r"^EFFECTS(.*)$", r.stdout, re.M)
    if not m:
        say(f"gate: the cue sheet {cues.name} didn't load ({(r.stderr or '').strip().splitlines()[-1:]}), the sync checks use the newest score report")
        return None
    b = re.search(r"^BEDS(.*)$", r.stdout, re.M)
    BEDS[:] = json.loads(b.group(1)) if b else []
    return sorted((float(t), n, note) for t, n, note in json.loads(m.group(1)))


BEDS = []   # the cue sheet's beds: [path, t0, t1, src, align, auto], for check_sync's music events


def music_event(t, db=4.0):
    """an effect on the music's own turn (a drums-out gets a hit, a return gets a hit): the bed playing at t changes level by `db` or
    more across t (its song's own arrangement, read from the song file at the bed's time, or the bed's own level move there). Such an
    effect is synced to the music, not to the picture, so it is never SOUND_NOTHING_SHOWN"""
    for path, t0, t1, src, align, auto in BEDS:
        if not (t0 <= t <= t1):
            continue
        for (ta, ua), (tb, ub) in zip(auto, auto[1:]):
            if ta - 0.3 <= t <= tb + 0.3 and abs(ub - ua) >= db and tb - ta <= 1.0:
                return True
        st = (align[0] + (t - align[1])) if align else (src + (t - t0))
        def level():
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, st - 0.6):.3f}", "-t", "1.2", "-i", str(path), "-ac", "1", "-ar", "8000",
                                  "-f", "f32le", "-"], capture_output=True).stdout
            x = np.frombuffer(raw[: len(raw) // 4 * 4], np.float32)
            if len(x) < 8000:
                return None
            h = len(x) // 2
            rms = lambda y: 20 * np.log10(max(float(np.sqrt(np.mean(y * y))), 1e-6))
            return rms(x[h:]) - rms(x[:h])
        d = cached("music", Path(path), f"{st:.2f}", level)
        if d is not None and abs(d) >= db:
            return True
    return False


def footage_event(clips, pub, F):
    """something happens inside the footage on screen at F (a whoosh on the camera climbing away, a logo forming inside its clip, bags
    landing on a table): the clip's own picture changes 2.5x its usual within -0.1/+0.2 s of the effect"""
    for c in clips.get(F, []):
        src, sec = pub / c["src"], c["s"]
        def spike():
            fr_ = gray_frames(src, max(0.0, sec - 1.0), sec + 1.0)
            if fr_ is None or len(fr_) < 10:
                return None
            d = np.abs(np.diff(fr_, axis=0)).mean(axis=(1, 2))
            fps_ = len(fr_) / 2.0
            i0 = int(round((min(sec, 1.0) - 0.1) * fps_))
            i1 = int(round((min(sec, 1.0) + 0.2) * fps_)) + 1
            win = d[max(0, i0):i1]
            med = float(np.median(d)) if len(d) else 0.0
            return bool(len(win) and float(win.max()) >= max(2.5 * med, 2.0))
        if cached("footev", src, f"{sec:.3f}", spike):
            return True
    return False


def effects_from_log(log):
    """the effects score.py placed: (second, name, note) from its report (or the cue sheet's list itself)"""
    if isinstance(log, list):
        return log
    out = {}
    if not log or not Path(log).exists():
        return []
    for line in Path(log).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s+(\d+\.\d+)\s+(\S+)\s+(impact ([\d.]+) s in the file.*?dB\s+(.*)|.*)$", line)
        if not m:
            continue
        t, name = float(m.group(1)), m.group(2)
        if name in ("A", "B", "C", "D", "E", "F", "G", "H") or not re.search(r"[a-zA-Z]", name):
            continue
        key = round(t, 2)
        off = float(m.group(4)) if m.group(4) else 0.0
        note = m.group(5) or out.get(key, (0, "", ""))[2]
        out[key] = (t + off, name, note)
    return sorted(out.values())


def landed(layout, F):
    """an impact on a landing: a stamp that slams in over 8 frames and lands on the hit ('40 YEARS'), an odometer that eases to rest on
    'the count lands': the thing moved, scaled or faded in over the 0.5 s before and comes to rest within -0.1/+0.2 s of the sound"""
    tr = track(layout, F - 30, F + 12)
    for key, pts in tr.items():
        fs = sorted(pts)
        moves = [f for i, f in enumerate(fs[1:], 1)
                 if abs(pts[f][0] - pts[fs[i - 1]][0]) + abs(pts[f][1] - pts[fs[i - 1]][1]) > 0.5
                 or abs(pts[f][2] - pts[fs[i - 1]][2]) / max(pts[fs[i - 1]][2], 1) > 0.002 or abs(pts[f][4] - pts[fs[i - 1]][4]) > 0.02]
        if not moves or not (F - 6 <= moves[-1] <= F + 12):
            continue
        a, b = pts[fs[0]], pts[moves[-1]]
        if abs(b[0] - a[0]) + abs(b[1] - a[1]) > 15 or abs(b[2] - a[2]) / max(a[2], 1) > 0.05 or b[4] - a[4] > 0.3:
            return True
    return False


def mark_lights(layout, f0, f1):
    """the frames in f0..f1 where a mark lights: one more data-gate="mark" item at full light (op >= 0.3) than on the frame before"""
    n = lambda f: sum(1 for it in layout.get(f, []) if it.get("g") == "mark" and it.get("op", 0) >= 0.3)
    return [f for f in range(max(1, f0), f1 + 1) if f in layout and n(f) > n(f - 1)]


def check_sync(layout, clips, shots, effects, pub=None):
    cuts = {fr(s["at"]) for s in shots}
    starts = set()
    prev = set()
    for f in sorted(clips):
        cur = {c["src"] for c in clips[f]}
        if cur - prev:
            starts.add(f)
        prev = cur
    flags = []
    end = max(layout) if layout else 0
    for t, name, note in effects:
        F = round(t * FPS)
        w0, w1 = F - 6, F + 12
        if w1 > end:
            continue
        # a marker sound belongs to a phrase lighting up (a highlight appearing or drawing), not to the card's own arrival (a card cut
        # in with the marker sound while its phrase lights a second later: the marker sounds too early)
        marker = "marker" in name.lower() or "mark" in (note or "").lower()
        if not marker and any(w0 <= c <= w1 for c in cuts | starts):
            continue
        tr = track(layout, w0 - 6, w1)
        happened = False
        for key, pts in tr.items():
            # a phrase lit by its colour (a design's Lit: the words turn from ink to the accent colour, no box drawn; without this every
            # such marker would read as "nothing shown"): the lit text's colour changes inside the window
            # (a bar of a chart lit the same way: its box's colour changes)
            if marker and key[0] in ("text", "box", "svg"):
                fs = sorted(pts)
                before = [pts[f] for f in fs if f <= w0]
                during = [pts[f] for f in fs if w0 <= f <= w1]
                base = before[-1] if before else (during[0] if during else None)   # a page cut in with its phrase lighting from the cut
                if base and during and max(d[4] for d in during) >= 0.3 and any(d[5] != base[5] for d in during):
                    happened = True
                    break
                # a mark box laid over a page already on screen (it shows up inside the window), or a thing dimmed on its word
                if during and ((key[0] == "box" and not before and fs[0] > w0) or (before and max(abs(d[4] - before[-1][4]) for d in during) > 0.3)):
                    happened = True
                    break
                if key[0] == "text":
                    continue
            if marker and not (key[0] == "box" and max(v[3] for v in pts.values()) < 140):
                continue
            fs = sorted(pts)
            before = [pts[f] for f in fs if f <= w0]
            during = [pts[f] for f in fs if w0 <= f <= w1]
            if not during:
                continue
            if not before or before[-1][4] < 0.3 <= max(d[4] for d in during):
                happened = True   # it appears
                break
            p0 = before[-1]
            if marker:   # drawing: wider, not taller (a page's push grows it both ways)
                if max(d[2] / max(p0[2], 1) - d[3] / max(p0[3], 1) for d in during) > 0.05:
                    happened = True
                    break
                continue
            if max(abs(d[0] - p0[0]) + abs(d[1] - p0[1]) for d in during) > 15 or max(abs(d[2] - p0[2]) / max(p0[2], 1) for d in during) > 0.05 \
                    or max(abs(d[4] - p0[4]) for d in during) > 0.3 or any(d[5] != p0[5] for d in during):
                happened = True
                break
        if not happened and not marker:
            happened = landed(layout, F) or music_event(t) or (pub is not None and footage_event(clips, pub, F))
        if not happened and marker:
            # a mark DOES light near the marker, just not on it: the sound is off its light (the cue on one phrase, the light on the next
            # phrase 0.9 s later: a mark sound that is plainly out of sync). Named with the light's own time, and never allowed: the cue
            # moves. A light another marker cue sounds on is that cue's (three marks lit 1.6 s before the next cue), not this one's
            mine = [f for f in mark_lights(layout, F - 72, F + 72) if not (w0 <= f <= w1)
                    and not any(round(t2 * FPS) - 6 <= f <= round(t2 * FPS) + 12 for t2, n2, o2 in effects
                                if ("marker" in n2.lower() or "mark" in (o2 or "").lower()) and abs(t2 - t) > 1e-6)]
            near = min(mine, key=lambda f: abs(f - F), default=None)
            if near is not None:
                flags.append({"check": "MARK_SOUND_OFF", "key": f"{name}@{t:.2f} {note[:40]}".strip(), "at": F, "no_allow": True,
                              "what": f"the {name} effect at {t:.2f} s ({note or 'no note'}): its mark lights at {near / FPS:.2f} s "
                                      f"({(near - F) / FPS:+.2f} s): move the cue onto the light's first frame; not allowable"})
                continue
        if not happened:
            # the key carries the cue's own note after its time: an allow keyed by the note survives a re-timing (an allow keyed by the
            # time alone goes stale on every voice fix); an old name@time allow still matches
            flags.append({"check": "SOUND_NOTHING_SHOWN", "key": f"{name}@{t:.2f} {note[:40]}".strip() if note else f"{name}@{t:.2f}", "at": F,
                          "what": f"the {name} effect at {t:.2f} s ({note or 'no note'}): nothing appears, moves or cuts within -0.1/+0.2 s"
                                  " (an allow needs \"measured\": the second its change shows, read off frames, within -0.1/+0.25 s)"})
    return flags


# =========================================================================================================================== B7, B8
def check_fades(plays, pub, layout=None):
    """B2 FADE/DISSOLVE: a play that opens or closes inside a fade or a dissolve (to a viewer it counts as a flash frame: an end card
    opening in a logo's dissolve, a shot running into its fade to black; check_flashes' 0.3-s edges and hard-cut scan miss both).
    tools/motion/qa_fades.py on each play's own span."""
    sys.path.insert(0, str(MOTION))
    import qa_fades
    flags, seen = [], {}
    for p in plays:
        f = pub / p["src"]
        if not f.exists() or p["s1"] - p["s0"] < 0.3:
            continue
        key = (p["src"], round(p["s0"], 2), round(p["s1"], 2))
        if key not in seen:
            seen[key] = cached("fades", f, f"{p['s0']:.4f}|{p['s1']:.4f}", lambda: [list(x) for x in qa_fades.scan(f, p["s0"], p["s1"])])
        hid = layout is not None and hidden_ground(layout, p)
        for edge, kind, msg in seen[key]:
            if hid and kind == "DISSOLVE":
                continue
            flags.append({"check": kind, "key": f"{Path(p['src']).stem}:{edge}", "at": p["f0"] if edge == "head" else p["f1"],
                          "what": f"{Path(p['src']).stem} {edge}: {msg}"})
    return flags


def load_manifest(spec):
    """the clips manifest ([gate] clips_json, name -> [master, file] or [master, a, b]) merged from a file, a glob or a list of them, relative
    to tools/motion: a video built by several builders has one prep file each, and each writes its own manifest"""
    if not spec:
        return {}
    out = {}
    for one in ([spec] if isinstance(spec, (str, Path)) else spec):
        one = Path(one) if Path(one).is_absolute() else MOTION / one
        for f in (sorted(one.parent.glob(one.name)) if any(c in one.name for c in "*?[") else [one]):
            if f.exists():
                out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


def check_reuse(plays, clips_json):
    if not OVERUSED.exists():
        return []
    bad = json.loads(OVERUSED.read_text(encoding="utf-8"))
    sources = {}
    for n, e in load_manifest(clips_json).items():
        sources[n] = str(e[0])
    flags = []
    for p in plays:
        name = Path(p["src"]).stem
        where = f"{p['src']} {sources.get(name, '')}".lower()
        for b in bad:
            if b["match"].lower() in where:
                flags.append({"check": "OVERUSED", "key": name, "at": p["f0"], "what": f"{name} is {b['what']} ({b['why']})"})
    return flags


def mask_parts(m):
    """the sizes of a small boolean mask's 4-connected parts"""
    from collections import deque
    h, w = m.shape
    seen = np.zeros_like(m)
    out = []
    for y in range(h):
        for x in range(w):
            if m[y, x] and not seen[y, x]:
                q, n = deque([(y, x)]), 0
                seen[y, x] = True
                while q:
                    cy, cx = q.popleft()
                    n += 1
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                out.append(n)
    return out


def cutout_bite(path):
    """None for a picture that isn't a cut-out; else how much of the subject's outline is bitten away: the mask closed with a 21-px
    brush (at 400 px) against the mask itself. A person with half the face cut away: 0.105; good cut-outs (people, devices, product
    boxes): 0.006-0.056. Logos and maps' land are shapes, not subjects: not measured."""
    from PIL import Image, ImageFilter
    name = Path(path).name.lower()
    if any(k in name for k in ("logo", "land_", "map", "wordmark")):
        return None
    im = Image.open(path)
    if im.mode not in ("RGBA", "LA", "PA") and "transparency" not in im.info:
        return None
    im = im.convert("RGBA")
    s = 400 / max(im.size)
    im = im.resize((max(1, round(im.size[0] * s)), max(1, round(im.size[1] * s))))
    a = np.asarray(im)[..., 3] > 127
    if (~a).mean() < 0.05 or a.mean() < 0.02:
        return None
    M = Image.fromarray((a * 255).astype(np.uint8))
    small = np.asarray(M.resize((max(1, M.size[0] // 4), max(1, M.size[1] // 4)))) > 127
    if sum(1 for z in mask_parts(small) if z > 0.01 * small.sum()) > 2:   # many separate parts: a group shot or a shape, not one subject
        return None
    closed = np.asarray(M.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.MinFilter(21))) > 127
    return float((closed & ~a).sum() / max(a.sum(), 1))


def check_cutouts(layout, pub):
    """B8: a cut-out with chunks missing (half a face), and a cut-out shown on a card or box (a product box on a glowing card, a person
    boxed small; a cut-out stands on the picture itself)"""
    flags, seen, cut = [], {}, {}
    for f in sorted(layout):
        for it in layout[f]:
            t = str(it["t"])
            if it["k"] == "img" and t.lower().endswith(".png") and t not in seen:
                seen[t] = f
    for t, f in seen.items():
        p = pub / t
        if not p.exists():
            continue
        b = cutout_bite(p)
        if b is None:
            continue
        cut[t] = b
        if b > 0.08:
            flags.append({"check": "CUTOUT", "key": Path(t).name, "at": f,
                          "what": f"{Path(t).name}: chunks missing from the subject (bite {b:.3f}; good cut-outs are under 0.06)"})
    boxed = defaultdict(list)
    halo = defaultdict(list)
    for f, items in layout.items():
        # a cut-out over its own blown-up blurred copy (Stage's backdrop): the blur of a transparent picture glows round the subject
        # like a halo; a cut-out goes on a clean backdrop: CutOut
        names = defaultdict(list)
        for it in items:
            if it["k"] == "img" and str(it["t"]) in cut and it["op"] >= 0.3:
                names[str(it["t"])].append(it)
        for t, its in names.items():
            if len(its) >= 2 and any(o["w"] >= 0.9 * FRAME[0] for o in its) and any(o["w"] < 0.9 * FRAME[0] for o in its):
                halo[t].append(f)
        for it in items:
            if it["k"] != "img" or str(it["t"]) not in cut or it["op"] < 0.3:
                continue
            p = it.get("pa", -1)
            while p is not None and 0 <= p < len(items):
                q = items[p]
                if q["k"] == "box" and q["w"] * q["h"] < 2.5 * it["w"] * it["h"] and q["w"] < 1700:
                    boxed[str(it["t"])].append(f)
                    break
                p = q.get("pa", -1)
    for t, f0, f1 in runs_of(halo, 1):
        if f1 - f0 >= 20:
            flags.append({"check": "CUTOUT_HALO", "key": Path(t).name, "at": f0, "to": f1,
                          "what": f"{Path(t).name} shown over its own blurred copy: the blur glows round the cut-out like a halo (use CutOut)"})
    for t, f0, f1 in runs_of(boxed, 1):
        if f1 - f0 >= 20:
            flags.append({"check": "CUTOUT_ON_CARD", "key": Path(t).name, "at": f0, "to": f1,
                          "what": f"{Path(t).name} shown on a card or box behind it: a cut-out stands on the picture itself"})
    return flags


INK = {}


def ink_frac(pub, t):
    """the part of a picture's box its opaque pixels fill, as fractions (x0, y0, x1, y1): a logo's PNG is often padded"""
    if t not in INK:
        INK[t] = (0.0, 0.0, 1.0, 1.0)
        p = pub / t
        if t.lower().endswith(".png") and p.exists():
            from PIL import Image
            im = Image.open(p)
            if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
                im = im.convert("RGBA")
                s = 300 / max(im.size)
                a = np.asarray(im.resize((max(1, round(im.size[0] * s)), max(1, round(im.size[1] * s)))))[..., 3] > 40
                ys, xs = np.nonzero(a)
                if len(xs):
                    h, w = a.shape
                    INK[t] = (xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h)
    return INK[t]


def check_overlap(layout, pub):
    """B4 PIC_ON_PIC: two pictures (logos, cut-outs, covers) drawn over each other, neither inside the other's element nor laid wholly on
    it (one logo stacked over another: a row's fixed 230-px step against a 414-px tall logo). A picture
    wholly on another (a logo on its card, a cover replacing a cover) is the design; a crossfade is too short to count"""
    W, H = FRAME
    hits, info = defaultdict(list), {}
    for f in sorted(layout):
        items = layout[f]
        anc = {}
        for i, it in enumerate(items):
            chain, q = set(), it.get("pa", -1)
            while q is not None and 0 <= q < len(items) and q not in chain:
                chain.add(q)
                q = items[q].get("pa", -1)
            anc[i] = chain
        pics = []
        for i, it in enumerate(items):
            if it["k"] != "img" or it["op"] < 0.5 or it["w"] >= 0.9 * W or it["h"] >= 0.9 * H:
                continue
            fx0, fy0, fx1, fy1 = ink_frac(pub, str(it["t"]))
            box = (it["x"] + fx0 * it["w"], it["y"] + fy0 * it["h"], it["x"] + fx1 * it["w"], it["y"] + fy1 * it["h"])
            v = (max(box[0], it["cx0"], 0), max(box[1], it["cy0"], 0), min(box[2], it["cx1"], W), min(box[3], it["cy1"], H))
            if v[2] > v[0] and v[3] > v[1] and area(v) > 0.002 * W * H:
                pics.append((i, it, v))
        for x in range(len(pics)):
            for y in range(x + 1, len(pics)):
                (i, a, va), (j, b, vb) = pics[x], pics[y]
                if i in anc[j] or j in anc[i] or a["t"] == b["t"]:
                    continue
                if not (va[0] < vb[2] and vb[0] < va[2] and va[1] < vb[3] and vb[1] < va[3]):
                    continue
                ov = area((max(va[0], vb[0]), max(va[1], vb[1]), min(va[2], vb[2]), min(va[3], vb[3])))
                small = min(area(va), area(vb))
                if 0.10 * small < ov < 0.90 * small:
                    na, nb = sorted((Path(str(a["t"])).name, Path(str(b["t"])).name))
                    k = f"{na} | {nb}"
                    hits[k].append(f)
                    info[k] = f"{na} and {nb} drawn over each other ({ov / small:.0%} of the smaller one covered)"
    flags = []
    for k, f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= 10:
            flags.append({"check": "PIC_ON_PIC", "key": k[:80], "at": f0, "to": f1, "what": info[k] + f" for {(f1 - f0 + 1) / FPS:.2f} s"})
    return flags


# the source masters the clips are cut from (gate_masters.json beside this file, empty until the creator's setup fills it):
#   "masters": {code: the words a credit under its footage must hold}, e.g. {"OV": "Official Video", "PK": "Press Kit"}; the prep
#              scripts' tables name a clip's master by its code ("harbour_aerial": ("OV", 12.0, 14.5))
#   "letterboxed": {code: how the flag names it}, the masters whose picture carries its own black bars, e.g. {"OV": "the Official Video (2.22:1)"}
#   "subject_credit", "subject_file": the credit words of the main subject's own footage, and the words its source files' names carry
#              (a clip cut from another file must not be credited as the subject's)
MASTERS_FILE = Path(__file__).resolve().parent / "gate_masters.json"
_MASTERS = json.loads(MASTERS_FILE.read_text(encoding="utf-8")) if MASTERS_FILE.exists() else {}
MASTER_WORDS = _MASTERS.get("masters", {})
SUBJECT_CREDIT, SUBJECT_FILE = _MASTERS.get("subject_credit", ""), _MASTERS.get("subject_file", "")
MASTER_RX = "|".join(map(re.escape, MASTER_WORDS)) or r"(?!x)x"   # the codes as a regex group (never matches while none is set)


def clip_sources(v):
    """{clip name: its master (a code of MASTER_WORDS) or the file it was cut from}: the clips manifest ([gate] clips_json) and the prep
    scripts' tables ([gate] sources: e.g. a prep script's `"harbour_aerial": ("OV", ...)`)"""
    G = v.section("gate") if hasattr(v, "section") else {}
    out = {}
    for name in G.get("sources", []):
        p = MOTION / name
        if p.exists():
            for m in re.finditer(r'"([\w.-]+)":\s*\(\s*"(' + MASTER_RX + ')"', p.read_text(encoding="utf-8")):
                out[m.group(1)] = m.group(2)
    for k, x in load_manifest(G.get("clips_json")).items():
        out[k] = x[0] if isinstance(x, list) and x else out.get(k)
    return out


def check_credits(layout, srcs):
    """B9 CREDIT: the credit on screen names another source than the clip shown (shots of one official video credited to another, a
    clip from another source credited as the subject's own). The clip shown = an opaque clip pane over a third of the frame; its
    master's name must be in a credit on screen; a clip cut from another file must not carry the subject's credit (SUBJECT_CREDIT)"""
    W, H = FRAME
    hits, info = defaultdict(list), {}
    for f in sorted(layout):
        items = layout[f]
        credits = " | ".join(str(it["t"]) for it in items if it["k"] == "text" and it["g"] == "credit" and it["op"] >= 0.5)
        for it in items:
            if it["k"] != "clip" or it["op"] < 0.5:
                continue
            v_ = vis(it, W, H)
            if not v_ or area(v_) < W * H / 3:
                continue
            name = Path(str(it["t"])).stem
            src = srcs.get(name)
            if not src:
                continue
            if src in MASTER_WORDS:
                # a credit names the footage's real source: the master's own name, never only its maker's
                if MASTER_WORDS[src] not in credits:
                    k = (name, credits)
                    hits[k].append(f)
                    info[k] = f"{name} is from the {MASTER_WORDS[src]}, the credit says \"{credits or 'nothing'}\""
            elif SUBJECT_CREDIT and SUBJECT_CREDIT in credits and SUBJECT_FILE not in str(src):
                k = (name, credits)
                hits[k].append(f)
                info[k] = f"{name} is cut from {Path(str(src)).name}, the credit says \"{credits}\""
    flags = []
    for k, f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= 10:
            flags.append({"check": "CREDIT", "key": k[0], "at": f0, "to": f1, "what": info[k]})
    return flags


def clip_spans(v):
    """{clip name: (its master or source file, in, out)} from the clips manifest and the prep scripts' tables (see clip_sources)"""
    G = v.section("gate") if hasattr(v, "section") else {}
    out = {}
    for name in G.get("sources", []):
        p = MOTION / name
        if p.exists():
            for m in re.finditer(r'"([\w.-]+)":\s*\(\s*"(' + MASTER_RX + r')",\s*([\d.]+),\s*([\d.]+)', p.read_text(encoding="utf-8")):
                out[m.group(1)] = (m.group(2), float(m.group(3)), float(m.group(4)))
    for k, x in load_manifest(G.get("clips_json")).items():
        if isinstance(x, list) and len(x) >= 3:
            out[k] = (str(x[0]), float(x[1]), float(x[2]))
    return out


def check_twice(plays, layout, spans, scope=None):
    """B7 TWICE: the same stretch of a source shown twice in one video, under one clip name or two (one aerial shown under two lines,
    0.16 s of it in both; two cuts of one dusk skyline, 1.3 s of the same frames). A blurred ground (the clip at under half opacity)
    isn't a showing. `scope` [(a, b)] (the scoped gate):
    only the pairs with a play on those frames, wherever the other one is (the flag sits on the later play, as in the full gate)"""
    shown = []
    for p in plays:
        mid = (p["f0"] + p["f1"]) // 2
        op = max([it["op"] for it in layout.get(mid, []) if it["k"] == "clip" and str(it["t"]) == str(p["src"])] or [1.0])
        if op < 0.5 or p["n"] < 6:
            continue
        name = Path(str(p["src"])).stem
        lo, hi = sorted((p["s0"], p["s1"]))
        if name in spans:
            m, a, _ = spans[name]
            shown.append((m, a + lo, a + hi, name, p["f0"]))
        else:
            shown.append((str(p["src"]), lo, hi, name, p["f0"]))
        if scope is not None:
            shown[-1] += (any(x <= p["f1"] and p["f0"] <= y for x, y in scope),)
    flags = []
    ends = defaultdict(set)
    for p in plays:
        ends[Path(str(p["src"])).stem].update(range(p["f1"] - 3, p["f1"] + 4))
    for i in range(len(shown)):
        for j in range(i + 1, len(shown)):
            if scope is not None and not (shown[i][5] or shown[j][5]):
                continue
            (m1, a1, b1, n1, f1), (m2, a2, b2, n2, f2) = shown[i][:5], shown[j][:5]
            ov = min(b1, b2) - max(a1, a2)
            # one clip restarted back to back is a Loop (the same scene over and over on the bed's beat, by design): the same name, the
            # next play starting within 3 frames of one's end
            if n1 == n2 and max(f1, f2) in ends[n1]:
                continue
            if m1 == m2 and ov > 0.1:
                flags.append({"check": "TWICE", "key": f"{n1}|{n2}", "at": max(f1, f2),
                              "what": f"{n2} shows {ov:.2f} s of the same {Path(m1).name} frames as {n1} at {mmss(min(f1, f2))}"})
    return flags


BARS = {}


def bars_of(path):
    """a clip's letterbox bars as fractions of its height (top, bottom): ffmpeg's cropdetect, the crop most frames agree on, kept only when
    it is the same above and below (a night shot's dark sky isn't a bar)"""
    k = str(path)
    if k not in BARS:
        BARS[k] = (0.0, 0.0)
        r = subprocess.run(["ffmpeg", "-v", "info", "-t", "3", "-i", k, "-vf", "cropdetect=24:2:0", "-an", "-f", "null", "-"],
                           capture_output=True, text=True)
        crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
        hh = re.search(r"Stream.*Video.*?(\d{3,5})x(\d{3,5})", r.stderr)
        if crops and hh:
            H = int(hh.group(2))
            from collections import Counter
            (cw, ch, cx, cy), n = Counter(crops).most_common(1)[0]
            top, bot = int(cy) / H, (H - int(cy) - int(ch)) / H
            if n >= 0.6 * len(crops) and top > 0.02 and abs(top - bot) < 0.012:
                BARS[k] = (top, bot)
    return BARS[k]


def check_letterbox(layout, pub):
    """B4 LETTERBOX: a letterboxed source's black bars inside the picture (standard/SHORTS.md: a source of 1920x864 inside 1080 needs a
    1.26+ push in a 9:16 window; at 1.0 it shows 108-px bars above and below)"""
    W, H = FRAME
    hits, info = defaultdict(list), {}
    for f in sorted(layout):
        for it in layout[f]:
            if it["k"] != "clip" or it["op"] < 0.3:
                continue
            top, bot = bars_of(pub / str(it["t"]))
            if not top:
                continue
            y0, y1 = max(it["y"], it["cy0"], 0), min(it["y"] + it["h"], it["cy1"], H)
            show = max(0.0, min(y1, it["y"] + it["h"] * top) - y0) + max(0.0, y1 - max(y0, it["y"] + it["h"] * (1 - bot)))
            if show > 4:
                k = Path(str(it["t"])).stem
                hits[k].append(f)
                info[k] = f"{k} is letterboxed ({top:.0%} bars above and below): {show:.0f} px of black bars on screen (push it 1.26+)"
    flags = []
    for k, f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= 6:
            flags.append({"check": "LETTERBOX", "key": k, "at": f0, "to": f1, "what": info[k]})
    return flags


LETTERBOXED_MASTERS = _MASTERS.get("letterboxed", {})   # gate_masters.json: {code: how the flag names it}


def check_letterbox_cut(layout, pub, srcs):
    """B4 LETTERBOX_CUT, long form: a letterboxed source plays whole, its own black bars kept (we show them whole). A clip cut from one
    whose file has no bars was cropped to fill the screen and lost its sides (a 2.22:1 master's clips at 1.25x, a 2:1 master's at
    1.125x: a prep script's fill). Allowed only in gate_allow.json with the reason the words point at a detail the whole frame can't
    show."""
    W, H = FRAME
    hits, info = defaultdict(list), {}
    for f in sorted(layout):
        for it in layout[f]:
            if it["k"] != "clip" or it["op"] < 0.3 or (it.get("bl") or 0) >= GROUND_BLUR or it["w"] * it["h"] < 0.33 * W * H:
                continue
            k = Path(str(it["t"])).stem
            m = srcs.get(k)
            if m not in LETTERBOXED_MASTERS or bars_of(pub / str(it["t"]))[0]:
                continue
            hits[k].append(f)
            info[k] = (f"{k} is cut from {LETTERBOXED_MASTERS[m]} without its bars: cropped and blown up to fill "
                       f"(show it whole with its bars)")
    flags = []
    for k, f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= 6:
            flags.append({"check": "LETTERBOX_CUT", "key": k, "at": f0, "to": f1, "what": info[k]})
    return flags


DIMS = {}


def dims_of(path):
    k = str(path)
    if k not in DIMS:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", k],
                           capture_output=True, text=True).stdout.strip().split(",")
        DIMS[k] = (int(r[0]), int(r[1])) if len(r) == 2 and r[0].isdigit() else None
    return DIMS[k]


def check_aspect(layout, pub):
    """B4 ASPECT: a clip drawn at another shape than its file (cuts of 3840x1608 declared 1920x1080: the browser
    letterboxes the video inside its 16:9 box, black bars the file itself doesn't have, so LETTERBOX's look at the file can't see them)"""
    hits, info = defaultdict(list), {}
    for f in sorted(layout):
        for it in layout[f]:
            if it["k"] != "clip" or it["op"] < 0.3 or it["h"] < 2 or (it.get("bl") or 0) >= GROUND_BLUR:   # a blurred fill ground
                continue
            d = dims_of(pub / str(it["t"]))
            if not d:
                continue
            drawn, real = it["w"] / it["h"], d[0] / d[1]
            if abs(drawn / real - 1) > 0.02:
                k = Path(str(it["t"])).stem
                hits[k].append(f)
                info[k] = f"{k} is {d[0]}x{d[1]} ({real:.2f}:1) but drawn at {drawn:.2f}:1: its picture is letterboxed inside its box (declare its real size)"
    flags = []
    for k, f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= 3:
            flags.append({"check": "ASPECT", "key": k, "at": f0, "to": f1, "what": info[k]})
    return flags


UPSCALE_MAX = 1.3    # frame px per pixel of a clip's own file a zoom may show (every picture in its best quality; kit3 Still's maxScale)
UPSCALE_ZOOM = 1.15  # a clip pane this much bigger than the frame is a zoom (a cover fit inside a frame-sized pane is not this check's)


def check_upscale(layout, pub):
    """B4 UPSCALE (every picture in its best quality; kit3 Foot's zoom into a small thing): a clip zoomed (its pane over UPSCALE_ZOOM x
    the frame) so that one pixel of its file covers more than UPSCALE_MAX frame px, for 3+ frames: a 1080p cut zoomed past 1.3x goes
    soft. Cut it from the 4K master (a prep script's ZOOMED cuts) or zoom less; a blurred ground is exempt"""
    W, H = FRAME
    hits, info = defaultdict(list), {}
    for f in sorted(layout):
        for it in layout[f]:
            if it["k"] != "clip" or it["op"] < 0.3 or it["h"] < 2 or (it.get("bl") or 0) >= GROUND_BLUR:
                continue
            if it["w"] < UPSCALE_ZOOM * W and it["h"] < UPSCALE_ZOOM * H:
                continue
            d = dims_of(pub / str(it["t"]))
            if not d:
                continue
            sc = max(it["w"] / d[0], it["h"] / d[1])
            if sc > UPSCALE_MAX:
                k = Path(str(it["t"])).stem
                hits[k].append(f)
                if sc > info.get(k, (0, None))[0]:
                    info[k] = (sc, d)
    flags = []
    for k, f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= 3:
            sc, d = info[k]
            flags.append({"check": "UPSCALE", "key": k, "at": f0, "to": f1,
                          "what": f"{k} ({d[0]}x{d[1]}) is zoomed to {sc:.2f} frame px per pixel of its file (over {UPSCALE_MAX}): soft. Cut "
                                  f"it from the 4K master (prep's ZOOMED) or zoom less"})
    return flags


MARK_SMALL = 0.02    # a mark (its padded box) under this share of the frame is on a thing too small to read whole-frame on a phone
MARK_ZOOMED = 1.6    # ... so its picture grows at least this much on screen ...
MARK_ZOOM_S = 0.7    # ... within this long of the mark's first frame
MARK_FULL = 0.9      # B25 reads marks on a full-frame picture only (a graphic's own icon is sized by its design)
MARK_MIN_S = 0.5     # B25b: a mark shows at least this long unless its shot cuts


def mark_tracks(layout):
    """every mark (data-gate="mark") on a lit picture followed from frame to frame by its place in the picture's own coordinates (a mark
    riding a zoom keeps it): [picture name, first frame, last frame, the mark's area share then, the picture's box then, its widest
    within MARK_ZOOM_S, the mark, whether the picture is still on screen right after the mark's last frame]"""
    W, H = FRAME
    tracks = defaultdict(list)
    for f in sorted(layout):
        items = layout[f]
        for mi in mark_items(items, W, H):
            m = items[mi]
            if m.get("g") != "mark":
                continue
            ground, _r = mark_ground(items, mi, W, H)
            if ground is None:
                continue
            gw, gh = max(ground["w"], 1.0), max(ground["h"], 1.0)
            place = ((m["x"] + m["w"] / 2 - ground["x"]) / gw, (m["y"] + m["h"] / 2 - ground["y"]) / gh)
            name = str(ground["t"]).split("/")[-1]
            dist = lambda tr: abs(tr["place"][0] - place[0]) + abs(tr["place"][1] - place[1])  # noqa: E731
            near = min((tr for tr in tracks[name] if f - tr["f1"] <= 3), key=dist, default=None)
            if near is None or dist(near) > 0.05:
                tracks[name].append({"name": name, "t": ground["t"], "place": place, "f0": f, "f1": f, "share": m["w"] * m["h"] / (W * H),
                                     "g0": (ground["w"], ground["h"]), "w1": ground["w"], "m": m})
                continue
            near["f1"] = f
            if f - near["f0"] <= MARK_ZOOM_S * FPS:
                near["w1"] = max(near["w1"], ground["w"])
    out = []
    for trs in tracks.values():
        for tr in trs:
            nxt = layout.get(tr["f1"] + 1)
            tr["cut"] = nxt is None or not any(it["k"] in ("clip", "img") and it["t"] == tr["t"] and it["op"] >= 0.5 for it in nxt)
            out.append(tr)
    return sorted(out, key=lambda tr: tr["f0"])


def check_mark_zoom(layout):
    """B25 MARK_SMALL: a mark on a thing under MARK_SMALL of the frame, on a full-frame picture, whose picture doesn't grow MARK_ZOOMED x
    on screen within MARK_ZOOM_S of the mark's first frame (kit3 Foot `zoom`): darkening round a small icon is fine, but the picture
    also zooms into it quickly, or it is a speck on a phone.
    B25b MARK_BLINK: a mark that shows under MARK_MIN_S and goes while its picture stays on screen (two things named together, the
    second mark's light switching the first off as both light: both stay lit)"""
    W, H = FRAME
    flags = []
    for tr in mark_tracks(layout):
        m, name, f0 = tr["m"], tr["name"], tr["f0"]
        full = tr["g0"][0] >= MARK_FULL * W and tr["g0"][1] >= MARK_FULL * H
        # a picture already drawn MARK_ZOOMED x the frame or more is the zoom (a shot drawn at 7680 px with 124-px icons is already a 4x
        # crop: no zoom is asked of it)
        if full and tr["share"] < MARK_SMALL and tr["g0"][0] < MARK_ZOOMED * W and tr["w1"] < MARK_ZOOMED * tr["g0"][0]:
            flags.append({"check": "MARK_SMALL", "key": name, "at": f0, "to": f0 + int(MARK_ZOOM_S * FPS),
                          "what": f"a mark at {m['x']:.0f},{m['y']:.0f} ({m['w']:.0f}x{m['h']:.0f}, {tr['share']:.1%} of the frame) on {name} "
                                  f"is never zoomed into ({tr['w1'] / max(tr['g0'][0], 1):.2f}x in {MARK_ZOOM_S} s): a speck on a phone. "
                                  f"Zoom into it quickly (kit3 Foot zoom)"})
        dur = (tr["f1"] - f0 + 1) / FPS
        if dur < MARK_MIN_S and not tr["cut"]:
            flags.append({"check": "MARK_BLINK", "key": name, "at": f0, "to": tr["f1"],
                          "what": f"a mark at {m['x']:.0f},{m['y']:.0f} ({m['w']:.0f}x{m['h']:.0f}) on {name} shows {dur:.2f} s and goes while "
                                  f"its picture stays: lit and switched off at once; marks named "
                                  f"together light together (kit3 SAME_AT)"})
    return flags


def check_outro(v, layout):
    """B26 OUTRO: a long video whose narration's last 25 s ask for a like and a comment shows the house SignOff (the outro elements) on
    them: a LIKE (or LIKED) and a COMMENTS
    text on screen in the film's last 25 s. A Short, or a film whose last words don't ask (a prototype), is not read"""
    if v.kind != "long" or not layout:
        return []
    try:
        W = json.loads(v.words().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    end = max(x["end"] for x in W) if W else 0
    said = " ".join(re.sub(r"[^a-z]", "", x["w"].lower()) for x in W if x["end"] >= end - 25)
    if not ("like" in said.split() and any(w.startswith("comment") for w in said.split())):
        return []
    last = max(layout)
    win = [f for f in layout if f >= last - 25 * FPS]
    texts = {str(it.get("t") or "").strip().upper() for f in win for it in layout[f] if it["k"] == "text" and it["op"] >= 0.3}
    if texts & {"LIKE", "LIKED"} and "COMMENTS" in texts:
        return []
    return [{"check": "OUTRO", "key": "signoff", "at": win[0] if win else last, "to": last,
             "what": "the last line asks for a like and a comment, but the house SignOff (its LIKE and COMMENTS) never shows "
                     "in the film's last 25 s (the outro elements are missing)"}]


EMPTY_COVER = 0.6    # the share of a Short's frame that pictures must fill
EMPTY_LIT = 0.28     # a picture counts once its opacity x its filters' brightness reaches this (an art ground at 0.55 x 0.55 = 0.30)
EMPTY_SECS = 0.4


def check_empty(layout):
    """B4 EMPTY (Shorts): a small picture on a plain ground, most of the screen nothing (SHORTS.md "never a small picture on a plain
    ground"). The frame's share covered by pictures (images and clips, credits aside) on a 40-px grid; a picture dimmed below EMPTY_LIT
    doesn't fill it (a card over a blurred skyline at 0.4 x 0.5 reads as "black above and below"). Proven against a reviewer's notes on
    three Shorts: it flags every stretch they called a small card, receipt, logo, cover or map on an empty ground, and none of the
    full-frame footage"""
    if FRAME[1] <= FRAME[0]:
        return []
    W, H, C = FRAME[0], FRAME[1], 40
    low = []
    for f in sorted(layout):
        g = np.zeros((H // C, W // C), bool)
        for it in layout[f]:
            if it["k"] not in ("img", "clip") or it.get("g") == "credit" or it["op"] * it.get("br", 1.0) < EMPTY_LIT:
                continue
            r = vis(it, W, H)
            if r:
                g[int(round(r[1] / C)):int(round(r[3] / C)), int(round(r[0] / C)):int(round(r[2] / C))] = True
        if g.mean() < EMPTY_COVER:
            low.append((f, float(g.mean())))
    flags, run = [], []
    for f, c in low + [(None, 1.0)]:
        if run and (f is None or f - run[-1][0] > 2):
            if run[-1][0] - run[0][0] + 1 >= EMPTY_SECS * FPS:
                m = min(x[1] for x in run)
                flags.append({"check": "EMPTY", "key": f"{run[0][0]}", "at": run[0][0], "to": run[-1][0],
                              "what": f"pictures fill only {m:.0%} of the frame for {(run[-1][0] - run[0][0] + 1) / FPS:.2f} s: a small thing on a "
                                      f"plain ground (make it big, or put it over full-bleed footage or art of the subject)"})
            run = []
        if f is not None:
            run.append((f, c))
    return flags


PAN_MIN = 0.2       # how far the 9:16 window must travel across a wide picture, in window widths
PAN_WIDE = 1.3      # a picture at least this many windows wide has more to show than the window holds
PAN_SECS = 0.6
PAN_LIT = 0.6       # a dimmed ground behind a card or a receipt isn't the hero


def check_pan(layout):
    """B11 PAN (Shorts): a wide picture shown full frame without a pan (in a vertical frame, panning is how a wide picture is centred on
    what matters: two people at the frame's edges with a product between them leave nothing to see in the middle, so the window pans
    from one to the other). Every lit picture that fills the frame and is PAN_WIDE windows wide or more (a 16:9 shot in
    9:16 is ~3) must move its window sideways by PAN_MIN window widths over its slot (a Short kit's place() fx -> fx1 or a `path`): from the
    one the words are on to the other, along the one who moves, across what the line names. A push alone flags. A shot that has to
    hold (one subject, nothing beside it) goes in gate_allow.json by its file name with the reason"""
    if FRAME[1] <= FRAME[0]:
        return []
    W, H = FRAME[0], FRAME[1]
    seen = defaultdict(list)
    for f in sorted(layout):
        for it in layout[f]:
            if it["k"] not in ("img", "clip") or it.get("g") == "credit" or it["op"] * it.get("br", 1.0) < PAN_LIT:
                continue
            r = vis(it, W, H)
            if not r or area(r) < 0.9 * W * H or it["w"] < 1:
                continue
            seen[(it["k"], it["t"])].append((f, ((r[0] + r[2]) / 2 - it["x"]) / it["w"], it["w"] / (r[2] - r[0])))
    flags = []
    for (k, t), xs in seen.items():
        run = []
        for x in xs + [None]:
            if run and (x is None or x[0] - run[-1][0] > 2):
                wide = float(np.median([q[2] for q in run]))
                if run[-1][0] - run[0][0] + 1 >= PAN_SECS * FPS and wide >= PAN_WIDE:
                    cx = [q[1] for q in run]
                    travel = (max(cx) - min(cx)) * wide
                    if travel < PAN_MIN:
                        name = t.split("/")[-1]
                        flags.append({"check": "PAN", "key": name, "at": run[0][0], "to": run[-1][0],
                                      "what": f"{name} is {wide:.1f} windows wide and its window moves {travel:.2f} of a width over "
                                              f"{(run[-1][0] - run[0][0] + 1) / FPS:.2f} s: pan it (fx -> fx1 or a path) from one subject "
                                              f"to the next, or allow it with the reason it holds"})
                run = []
            if x is not None:
                run.append(x)
    return flags


MARK_LIT = 0.5      # a ground counts as the picture a mark points into once its opacity x brightness reaches this (a dimmed ground isn't)
MARK_OP = 0.2       # a mark shows from this opacity
MARK_RIDE = 2.0     # px a mark may drift from its place in its picture's own coordinates while it shows (B12)
#                     moves a 1920-wide frame's edge ~19 px, so a slow push is caught over the mark's life, not frame by frame (eased
#                     pushes move < 0.25 px a frame at their ends: measured on a page push)


def mark_items(items, W, H):
    """the marks on a frame: anything a component names data-gate="mark" (a box, a ring, a label on a person, a highlight on a page), and
    every hollow outline (a border with nothing filled in) smaller than a third of the frame that isn't a credit, a name line, a stamp or a
    count's slot"""
    out = []
    for i, it in enumerate(items):
        if it["op"] < MARK_OP:
            continue
        g = it.get("g") or ""
        if g == "mark" and it["k"] in ("box", "svg", "text"):
            out.append(i)
        elif it["k"] == "box" and it.get("e") == 1 and not g and it["w"] * it["h"] < W * H / 3 \
                and not (it.get("rr", 0) >= 0.45 or abs(it["w"] - it["h"]) <= 0.06 * max(it["w"], it["h"])):
            # (an untagged ring is a graphic's own ping, focus ring or ripple, round, so square in its box: a tracker's pings on a moving parcel
            # and a call ripple would read as MARK_OFF "marks blank page"; a mark round words is wide, and kit marks name themselves
            # data-gate="mark" whatever their shape. rr: the probe's corner radius share)
            # an outline round one of our own things (a button's press ripple round its chip: the sign-off's LIKE) frames that thing,
            # it points at nothing in the picture: a box, text or drawing of ours filling half of it or more
            px, py = 0.15 * it["w"], 0.15 * it["h"]
            x0, y0, x1, y1 = it["x"] - px, it["y"] - py, it["x"] + it["w"] + px, it["y"] + it["h"] + py
            ours = any(j != i and o["k"] in ("box", "text", "svg") and o["op"] >= MARK_OP
                       and x0 <= o["x"] and o["x"] + o["w"] <= x1 and y0 <= o["y"] and o["y"] + o["h"] <= y1
                       and o["w"] * o["h"] >= 0.5 * it["w"] * it["h"] for j, o in enumerate(items))
            if not ours:
                out.append(i)
    return out


def mark_ground(items, mi, W, H):
    """the picture a mark points into: the topmost lit clip pane or picture under the mark's centre, bigger than the mark; None when a
    card (a filled box) lies between them (the mark is on the card) or nothing lit is under it"""
    m = items[mi]
    r = vis(m, W, H)
    if not r:
        return None, None
    # a mark drawn inside a filled card or page panel (its probe parent: PageShot's page card, a Receipt) points into that card, whatever
    # its size against the mark: the blurred ground behind the card is not what it marks (a page's marks would read as marks on its
    # ground when the page is under 2.5x the mark's area)
    q, seen = m.get("pa", -1), set()
    while q is not None and 0 <= q < len(items) and q not in seen:
        seen.add(q)
        it = items[q]
        if it["k"] == "box" and not it.get("e") and it.get("g") != "mark" and it["op"] >= 0.5:
            return None, r
        q = it.get("pa", -1)
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    for gi in range(mi - 1, -1, -1):
        it = items[gi]
        gr = vis(it, W, H)
        if not gr or not (gr[0] <= cx <= gr[2] and gr[1] <= cy <= gr[3]):
            continue
        # a picture that holds the whole mark is its target even when it is under 2.5x the mark's area (a page capture under a 1058x147
        # mark would be skipped for its size, and the blurred ground clip behind it taken as the target)
        holds = it["k"] == "img" and gr[0] - 2 <= r[0] and r[2] <= gr[2] + 2 and gr[1] - 2 <= r[1] and r[3] <= gr[3] + 2
        if area(gr) <= 2.5 * area(r) and not holds:
            continue
        if it["k"] == "box" and not it.get("e") and it.get("g") != "mark" and it["op"] >= 0.5:
            return None, r   # a card under the mark
        if it["k"] in ("clip", "img") and it.get("g") != "credit" and it["op"] * it.get("br", 1.0) >= MARK_LIT:
            return it, r
    return None, r


def check_marks(layout, clips):
    """B12 MARK_MOVES: a mural's boxes drifting off their targets while the footage pushes in. The fault is one part moving while the
    other stays in its place; boxes fixed on the clip, moving together with it, are fine. The invariant: a mark (a box, ring, arrow,
    label or highlight that points INTO a picture) stays on its target.
      1. A mark over a playing video clip fails (the motion inside a video can't be read from the boxes): the clip is held (the design's
         Hold/heldT) while the mark shows; it may play before the marks arrive and after they leave.
      2. A mark over a still, a page or a held clip whose layer moves (a push, zoom or pan) passes when it rides with it: its place in the
         layer's own coordinates (its offset from the layer's box, scaled with the layer) stays within MARK_RIDE px while it shows. It
         fails when the layer moves and the mark doesn't, or the mark moves and the layer doesn't.
    (A stricter rule, the ground's box never travelling more than 1 px under a mark, would fail a highlight riding its page.)"""
    W, H = FRAME
    secs = defaultdict(dict)      # frame -> src -> the source seconds its panes show
    for f, cs in clips.items():
        for c in cs:
            secs[f].setdefault(c["src"], set()).add(round(c["s"], 4))
    seen = defaultdict(list)      # ground name -> [(frame, its box, playing into the next frame, [the marks' boxes])]
    for f in sorted(layout):
        items = layout[f]
        marks = mark_items(items, W, H)
        if not marks:
            continue
        nxt = layout.get(f + 1)
        per = {}
        for mi in marks:
            ground, _r = mark_ground(items, mi, W, H)
            if ground is None:
                continue
            name = str(ground["t"]).split("/")[-1]
            if name not in per:
                plays = False
                if ground["k"] == "clip" and nxt is not None and any((i["k"], i["t"]) == (ground["k"], ground["t"]) for i in nxt):
                    a, b = secs.get(f, {}).get(ground["t"]), secs.get(f + 1, {}).get(ground["t"])
                    plays = bool(a and b and not (a & b))
                per[name] = (f, (ground["x"], ground["y"], ground["w"], ground["h"]), plays, [])
            per[name][3].append(items[mi])
        for name, row in per.items():
            seen[name].append(row)
    flags = []

    def norm(m, g):
        """the mark's top-left corner and its centre in the layer's own coordinates (a mark that pops in scales round its centre, a light
        that wipes in grows from its left edge: either one held still counts as staying on its target)"""
        gw, gh = max(g[2], 1.0), max(g[3], 1.0)
        return ((m["x"] - g[0]) / gw, (m["y"] - g[1]) / gh, (m["x"] + m["w"] / 2 - g[0]) / gw, (m["y"] + m["h"] / 2 - g[1]) / gh)

    def judge(name, run):
        played = [q[0] for q in run if q[2]]
        # each mark followed from frame to frame by its place in the layer's coordinates (nearest track), its drift in px measured at
        # the layer's size on that frame
        tracks = []   # [first place, last place, worst drift px, the frames it drifted, the mark]
        for f, g, _p, ms in run:
            used = set()
            for m in ms:
                u = norm(m, g)
                best = min(((abs(u[0] - tr[1][0]) + abs(u[1] - tr[1][1]), i) for i, tr in enumerate(tracks) if i not in used), default=None)
                if best is None or best[0] > 0.05:
                    tracks.append([u, u, 0.0, [], m])
                    used.add(len(tracks) - 1)
                    continue
                tr = tracks[best[1]]
                used.add(best[1])
                tr[1] = u
                drift = min(max(abs(u[0] - tr[0][0]) * g[2], abs(u[1] - tr[0][1]) * g[3]),
                            max(abs(u[2] - tr[0][2]) * g[2], abs(u[3] - tr[0][3]) * g[3]))
                if drift > MARK_RIDE:
                    tr[3].append(f)
                tr[2] = max(tr[2], drift)
        drifted = [tr for tr in tracks if len(tr[3]) >= 2]
        if len(played) < 2 and not drifted:
            return
        m = (drifted[0][4] if drifted else run[0][3][0])
        bad = sorted(set(played) | {f for tr in drifted for f in tr[3]})
        label = f" '{m['t']}'" if m.get("t") else ""
        why = (f"the clip plays under it for {len(played) / FPS:.2f} s" if len(played) >= 2 else "") +               (" and " if len(played) >= 2 and drifted else "") +               (f"it slides {max(tr[2] for tr in drifted):.1f} px off its target (the picture and the mark move apart)" if drifted else "")
        flags.append({"check": "MARK_MOVES", "key": name, "at": bad[0], "to": bad[-1],
                      "what": f"a mark{label} at {m['x']:.0f},{m['y']:.0f} ({m['w']:.0f}x{m['h']:.0f}) on {name} from {mmss(run[0][0])} to "
                              f"{mmss(run[-1][0])}: {why}: hold the clip on the mark's frame (the design's Hold/heldT), or "
                              f"move the mark with its picture"})

    for name, rows in seen.items():
        run = []
        for row in rows + [None]:
            if run and (row is None or row[0] - run[-1][0] > 2):
                judge(name, run)
                run = []
            if row is not None:
                run.append(row)
    return flags

NUM = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
       "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
       "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
SCALE = {"hundred": 100, "thousand": 1000, "million": 10 ** 6, "billion": 10 ** 9}
STOP = {"the", "a", "an", "of", "to", "in", "is", "it", "its", "and", "that", "you", "for", "on", "at", "i", "s", "x", "this", "just", "so", "be",
        "are", "was", "with", "they", "he", "we", "or", "by", "as", "up", "every", "per"}


def ancestry(items):
    """{item index: the indexes of the items it sits inside} (the probe's pa chain)"""
    anc = {}
    for i, it in enumerate(items):
        chain, q = set(), it.get("pa", -1)
        while q is not None and 0 <= q < len(items) and q not in chain:
            chain.add(q)
            q = items[q].get("pa", -1)
        anc[i] = chain
    return anc


def check_text_overlap(layout, px=2.0, need=6):
    """B13 TEXT_OVERLAP: two name lines under two covers, one running 12 px into the other so they read as one run-on line. Two visible
    texts (opacity
    0.3+, not a count's rolling digits, not one inside the other, not the same words) whose letters (ink(): a line's letter band, a block's
    box) intersect by more than `px` both ways, for `need` frames or more. B4's TEXT_ON_TEXT asks for 15% of the smaller box and so misses
    two lines that only touch along an edge. Also a text whose letters run more than `px` out of the card, panel or chip it sits in (a
    post title past its card's right edge)."""
    hits, info = defaultdict(list), {}
    W, H = FRAME
    pos = {}   # text -> its place on the frame before: two texts that only pass each other mid-move don't count (a ranked list's rows
    #            gliding over each other for 0.17 s); an overlap a viewer reads is two texts at rest
    for f in sorted(layout):
        items = layout[f]
        texts = []
        before, pos = pos, {}
        for i, it in enumerate(items or []):
            if it["k"] == "text":
                pos.setdefault(str(it["t"]), (it["x"], it["y"]))
            if it["k"] != "text" or it["op"] < 0.3 or it.get("g") == "roll":
                continue
            v = vis(it, W, H)
            if v:
                texts.append((i, it, v))
        if not texts:
            continue
        rest = lambda t_: str(t_["t"]) in before and abs(before[str(t_["t"])][0] - t_["x"]) + abs(before[str(t_["t"])][1] - t_["y"]) <= 1.0
        anc = ancestry(items)
        # a text running out of its card (a long post title past the card's right edge: the text extends over the card): its letters
        # past the nearest filled box (a card, a panel, a chip) it sits inside by more than `px`; a card that clips its text is B4's
        # TEXT_CUT
        for i, it, va in texts:
            card = next((items[q] for q in sorted(anc[i], reverse=True) if items[q]["k"] == "box" and not items[q].get("e")
                         and items[q]["op"] >= 0.3 and items[q].get("g") not in ("mark", "roll")), None)
            if card is None:
                continue
            cx0, cy0, cx1, cy1 = card["x"], card["y"], card["x"] + card["w"], card["y"] + card["h"]
            past = max(cx0 - va[0], va[2] - cx1, cy0 - va[1], va[3] - cy1)
            if past > px:
                k = ("past", str(it["t"]))
                hits[k].append(f)
                info[k] = f"\"{it['t']}\" runs {past:.0f} px out of its card ({cx0:.0f},{cy0:.0f} {card['w']:.0f}x{card['h']:.0f})"
        for x in range(len(texts)):
            for y in range(x + 1, len(texts)):
                (i, a, va), (j, b, vb) = texts[x], texts[y]
                if a["t"] == b["t"] or i in anc[j] or j in anc[i]:
                    continue
                ox = min(va[2], vb[2]) - max(va[0], vb[0])
                oy = min(va[3], vb[3]) - max(va[1], vb[1])
                if ox > px and oy > px and rest(a) and rest(b):
                    k = tuple(sorted((str(a["t"]), str(b["t"]))))
                    hits[k].append(f)
                    info[k] = f"\"{k[0]}\" and \"{k[1]}\" overlap by {ox:.0f} x {oy:.0f} px"
    return [{"check": "TEXT_OVERLAP", "key": (f"out of its card: {k[1]}" if k[0] == "past" else f"{k[0]} | {k[1]}")[:80], "at": f0, "to": f1,
             "what": info[k] + f" for {(f1 - f0 + 1) / FPS:.2f} s"} for k, f0, f1 in runs_of(hits, need)]


def hold_need(text, floor=1.2, per_char=0.03, free=10):
    """a text's reading time: 1.2 s, plus 0.03 s a character past 10 (SOLD OUT TWICE 1.32 s, NOT BEFORE THE FINALE 1.53 s)"""
    return floor + per_char * max(0, len(text) - free)


def check_text_hold(layout, fs_min=30, gap=2):
    """B24 TEXT_SHORT: a stamped text gone before it can be read (the cut comes 0.5 s after the stamp or sooner). A text of ours at
    reading size (30 px+, opacity 0.5+; credits and rolling digits aside) on screen for less than its reading time (hold_need: 1.2 s
    plus 0.03 s a character past 10; a stamp held 1.61 s reads, stamps held 0.29 s and ~0.5 s don't). Measured from the first frame its
    letters stand at half opacity to the last, across cuts (the same words carried on by the next shot are one run, as a checklist over
    three clips); a text that grows into a longer one
    (a typed line) or that the next frames show again within `gap` frames is one run; a run touching the edge of the measured frames
    (a scoped gate's window) isn't measured whole and isn't judged."""
    W, H = FRAME
    frames = sorted(layout)
    if not frames:
        return []
    first, last = frames[0], frames[-1]
    on, read = defaultdict(list), set()
    for f in frames:
        for it in layout[f] or []:
            # on screen from half opacity; a text dimmed after it was read (a row's labels at 45% while another is named) stays on screen
            # down to 0.3
            if it["k"] != "text" or it["op"] < 0.3 or it.get("g") in ("credit", "roll"):
                continue
            if (it.get("fs") or it.get("h") or 0) < fs_min or not vis(it, W, H):
                continue
            k = " ".join(str(it["t"]).split()).upper()
            if sum(ch.isalnum() for ch in k) >= 2:   # a lone sign ("~", "+") is part of a label, not words to read
                on[k].append(f)
                if it["op"] >= 0.5:
                    read.add(k)
    keys = [k for k in on if k in read]
    out = []
    for k in keys:
        fs_ = sorted(set(on[k]))
        runs, a, b = [], fs_[0], fs_[0]
        for f in fs_[1:]:
            if f - b <= gap + 1:
                b = f
            else:
                runs.append((a, b))
                a = b = f
        runs.append((a, b))
        for a, b in runs:
            if a <= first or b >= last:
                continue
            # a typed line: this text grows into a longer one (or is the end of one shrinking) right after its run
            if any(k2 != k and (k2.startswith(k) or k.startswith(k2)) and any(b < f2 <= b + gap + 1 for f2 in on[k2]) for k2 in keys):
                continue
            dur = (b - a + 1) / FPS
            need = hold_need(k)
            if dur < need:
                out.append({"check": "TEXT_SHORT", "key": k[:80], "at": a, "to": b,
                            "what": f"\"{k}\" on screen {dur:.2f} s, under its reading time {need:.2f} s: the next picture starts later, "
                                    f"or the words land sooner"})
    return out


ALPHA = {}


def alpha_box(pub, t):
    """the visible part of a picture file as fractions of its width and height (alpha above 16 of 255, as a design's measureImg); the whole
    file when it has no alpha or can't be read"""
    if t in ALPHA:
        return ALPHA[t]
    box = (0.0, 0.0, 1.0, 1.0)
    try:
        from PIL import Image
        im = Image.open(Path(pub) / t)
        if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
            im = im.convert("RGBA")
            im.thumbnail((640, 640))
            a = np.asarray(im)[:, :, 3] > 16
            ys, xs = np.nonzero(a)
            if len(xs):
                h, w = a.shape
                box = (xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h)
    except (OSError, ValueError):
        pass
    ALPHA[t] = box
    return box


def row_groups(items, pub, W, H):
    """the rows on a frame: two or more pictures (opacity 0.5+, smaller than the frame) on one floor (bottoms within 3 px) at one height
    (within 3 px), spanning the frame's centre; each with its visible boxes (alpha bounds) and the name lines centred under or on them"""
    pics = [it for it in items if it["k"] == "img" and it["op"] >= 0.5 and it.get("g") != "credit" and it["w"] < 0.9 * W and it["h"] < 0.9 * H]
    groups = []
    # kit3's rows name themselves (data-kit3="row": gate.tsx's `rw`): their cut-outs keep transparent margins, so their
    # boxes need not share a floor or a height; a kit3 row is read as the kit built it
    kit = defaultdict(list)
    for it in pics:
        if (it.get("rw") if it.get("rw") is not None else -1) >= 0:
            kit[it["rw"]].append(it)
    groups += [g for g in kit.values()]
    for it in sorted([o for o in pics if (o.get("rw") if o.get("rw") is not None else -1) < 0], key=lambda o: (o["y"] + o["h"], o["h"])):
        g = next((g for g in groups if (g[0].get("rw") if g[0].get("rw") is not None else -1) < 0
                  and abs(g[0]["y"] + g[0]["h"] - it["y"] - it["h"]) <= 3 and abs(g[0]["h"] - it["h"]) <= 3), None)
        (g.append(it) if g is not None else groups.append([it]))
    out = []
    for g in groups:
        if len(g) < 2:
            continue
        boxes = []
        for it in g:
            fx0, fy0, fx1, fy1 = alpha_box(pub, it["t"])
            boxes.append((it["x"] + fx0 * it["w"], it["y"] + fy0 * it["h"], it["x"] + fx1 * it["w"], it["y"] + fy1 * it["h"]))
        boxes.sort()
        if not (boxes[0][0] < W / 2 < max(b[2] for b in boxes)):
            continue
        bottom = max(b[3] for b in boxes)
        names = []
        for t in items:
            if t["k"] != "text" or t.get("g") != "name" or t["op"] < 0.5:
                continue
            cx = t["x"] + t["w"] / 2
            if any(b[0] <= cx <= b[2] for b in boxes) and t["y"] <= bottom + 220 and t["y"] + t["h"] >= min(b[1] for b in boxes):
                names.append((t["x"], t["y"], t["x"] + t["w"], t["y"] + t["h"]))
        allx = [b[0] for b in boxes + names] + [b[2] for b in boxes + names]
        # a row that shares the frame with something beside it (a split: a book cover and its caption left of a grid, a slot still to fill on
        # its right) is one column of a layout, not the frame's centred group: not judged here
        lo, hi = min(b[1] for b in boxes), max(b[3] for b in boxes + names)
        side = [t for t in items if t["op"] >= 0.5 and t.get("g") not in ("name", "credit") and t not in g
                and ((t["k"] == "text" and t["fs"] >= 40) or (t["k"] == "img" and t["w"] < 0.9 * W and t["h"] < 0.9 * H))
                and t["y"] < hi and t["y"] + t["h"] > lo and (t["x"] + t["w"] <= min(allx) + 2 or t["x"] >= max(allx) - 2)]
        off = (min(allx) + max(allx)) / 2 - W / 2
        gaps = [boxes[k + 1][0] - boxes[k][2] for k in range(len(boxes) - 1)]
        out.append({"names": {str(it["t"]) for it in g}, "n": len(g), "off": off, "split": bool(side), "span": max(allx) - min(allx),
                    "gapdiff": max(gaps) - min(gaps) if len(gaps) > 1 else 0.0, "gaps": gaps,
                    "what": " + ".join(Path(str(it["t"])).stem for it in sorted(g, key=lambda o: o["x"]))})
    return out


def check_row_centre(layout, pub, tol=8.0, settle=20):
    """B14 ROW_CENTRE: a row that doesn't look centred left to right (three devices centred by their pictures, but one name line running
    64 px past its narrow device, so the row's visible content sits 32 px right of centre, and the name lines' gaps read 311 against
    105 px). A row (row_groups) whose visible content, its pictures' alpha bounds and their name lines,
    sits more than `tol` px off the frame's centre, or whose gaps between pictures differ by more than `tol` px. Read on the row at rest:
    the last `settle` frames on which the row holds its most pictures (a row whose items land one by one stands at its final places from
    the first frame, so a part-filled row is not judged)."""
    W, H = FRAME
    # one track per row on screen: a frame's row joins the track that showed one of its pictures up to 2 frames before (its pictures grow
    # with a push and arrive one by one, so neither their sizes nor their count names the row)
    tracks = []   # [names, last frame, [(frame, row)]]
    for f in sorted(layout):
        for r in row_groups(layout[f] or [], pub, W, H):
            tr = next((t for t in tracks if f - t[1] <= 2 and t[1] < f and t[0] & r["names"]), None)
            if tr is None:
                tracks.append([set(r["names"]), f, [(f, r)]])
            else:
                tr[0] |= r["names"]
                tr[1] = f
                tr[2].append((f, r))
    flags = []
    for _names, _last, run in tracks:
        nmax = max(r["n"] for _f, r in run)
        # at rest = the row's width steady (within 1%) over +-10 frames: a camera zooming onto one of the row's pictures carries the row
        # off the centre on purpose ("-842 px off" read mid-move, the row centred at rest before it); a slow keep-alive push (2% over
        # seconds) stays at rest
        spans = {f: r["span"] for f, r in run}
        def at_rest(f):
            near = [spans[g] for g in range(f - 10, f + 11) if g in spans]
            return len(near) >= 3 and max(near) <= 1.01 * max(1.0, min(near))
        full = [(f, r) for f, r in run if r["n"] == nmax and at_rest(f)][-settle:]
        if len(full) < settle or any(r["split"] for _f, r in full):
            continue
        f0, r = full[0][0], full[-1][1]
        if all(abs(x["off"]) > tol for _f, x in full):
            flags.append({"check": "ROW_CENTRE", "key": r["what"][:80], "at": f0, "to": full[-1][0],
                          "what": f"the row {r['what']} sits {r['off']:+.0f} px off the centre (its pictures' visible bounds and name lines)"})
        elif all(x["gapdiff"] > tol for _f, x in full):
            flags.append({"check": "ROW_CENTRE", "key": r["what"][:80], "at": f0, "to": full[-1][0],
                          "what": f"the row {r['what']} has unequal gaps " + ", ".join(f"{g:.0f}" for g in r["gaps"]) + " px"})
    return flags


def spoken_tokens(words):
    """each script word's tokens as a caption would show it: the word, and for a run of number words the number in digits too
    ("five thousand" -> 5000 on both words, "eleven" -> 11)"""
    import re as _re
    norm = lambda w_: _re.sub(r"[^a-z0-9]", "", w_.lower().replace("'", ""))
    toks = [{norm(x["w"])} for x in words]
    i = 0
    while i < len(words):
        j, total, cur = i, 0, 0
        while j < len(words) and words[j]["beat"] == words[i]["beat"] and (norm(words[j]["w"]) in NUM or norm(words[j]["w"]) in SCALE
                                                                            or (j > i and norm(words[j]["w"]) == "and")):
            t = norm(words[j]["w"])
            if t in NUM:
                cur += NUM[t]
            elif t in SCALE:
                if SCALE[t] == 100:
                    cur = (cur or 1) * 100
                else:
                    total += (cur or 1) * SCALE[t]
                    cur = 0
            j += 1
        if j > i and any(norm(words[k]["w"]) in NUM for k in range(i, j)):
            val = str(total + cur)
            for k in range(i, j):
                toks[k].add(val)
            i = j
        else:
            i += 1
    return toks


def screen_tokens(text):
    import re as _re
    t = text.lower().replace(",", "")
    out = set(_re.findall(r"\d+|[a-z]+", t))
    for a, b in (("m", "million"), ("b", "billion"), ("k", "thousand")):
        if a in out:
            out.add(b)
    return out - STOP


def check_caption_twice(v, layout):
    """B10 CAPTION_TWICE: a stamp, count or label on screen shows a word the captions show at the same time (text is shown once, never
    redundantly twice; on-screen text may replace the captions outright): the word belongs in captions_hide.json"""
    wp = v.src_dir / "words.json"
    if not wp.exists():
        return []
    words = json.loads(wp.read_text(encoding="utf-8"))
    toks = spoken_tokens(words)
    hidden = []
    hp = v.folder / "captions_hide.json"
    if hp.exists():
        import re as _re
        norm = lambda w_: _re.sub(r"[^a-z0-9]", "", w_.lower().replace("'", ""))
        for hd in json.loads(hp.read_text(encoding="utf-8")):
            ph = [norm(t) for t in hd["phrase"].split() if norm(t)]
            hits = [i for i in range(len(words)) if all(i + k < len(words) and words[i + k]["beat"] == hd["beat"] and norm(words[i + k]["w"]) == ph[k]
                                                      for k in range(len(ph)))]
            if len(hits) > hd.get("nth", 0):
                i = hits[hd.get("nth", 0)]
                hidden.append((words[i]["start"] - 0.03, words[i + len(ph) - 1]["end"] + 0.03, set().union(*toks[i:i + len(ph)]) - STOP))
    on_line = sorted(f for f in layout if any(it["k"] in ("text", "img", "clip") and it["g"] == "stamp" and it["op"] >= 0.5
                                               and abs(it["y"] + it["h"] / 2 - 960) <= 200 for it in layout[f]))
    run = None
    for f in on_line + [None]:
        if f is not None and run and f - run[1] <= 2:
            run[1] = f
            continue
        if run:
            hidden.append((run[0] / FPS - 0.02, (run[1] + 1) / FPS + 0.02, set()))
        run = [f, f] if f is not None else None
    hits, info = defaultdict(list), {}
    for f in sorted(layout):
        texts = [it for it in layout[f] if it["k"] == "text" and it["g"] == "stamp" and it["op"] >= 0.5]
        if not texts:
            continue
        sc = set().union(*(screen_tokens(str(it["t"])) for it in texts))
        t = f / FPS
        for i, x in enumerate(words):
            if not (x["start"] - 0.05 <= t <= x["end"] + 0.35):
                continue
            mid = (x["start"] + x["end"]) / 2
            # hidden exactly as finish_short hides it: a captions_hide phrase by the word's middle, a stamp's stretch when 40%+ of the
            # word is under it (a long word partly under a stamp)
            if any((a <= mid <= b) if ht else (min(x["end"], b) - max(x["start"], a) >= 0.4 * max(0.01, x["end"] - x["start"])) for a, b, ht in hidden):
                continue
            same = (toks[i] - STOP) & sc
            if same:
                k = f"{x['beat']}:{x['w']}"
                hits[k].append(f)
                info[k] = f"the caption \"{x['w']}\" ({x['beat']}, {x['start']:.2f} s) while the screen shows \"{' / '.join(str(it['t']) for it in texts)}\": put the phrase in captions_hide.json"
        # the text that replaces hidden captions sits where the captions are (replacing the captions means taking their place): its words'
        # centre within 130 px of the caption line (y 960 in a Short)
        for a, b, ht in hidden:
            if a <= t <= b:
                for it in texts:
                    if screen_tokens(str(it["t"])) & ht:
                        cy = it["y"] + it["h"] / 2
                        if abs(cy - 960) > 130:
                            k = f"off:{it['t']}"
                            hits[k].append(f)
                            info[k] = f"\"{it['t']}\" replaces the captions but sits at y {cy:.0f}, not on the caption line (~960)"
    flags = []
    for k, f0, f1 in runs_of(hits, 1):
        if f1 - f0 + 1 >= 4:
            flags.append({"check": "CAPTION_OFF_LINE" if k.startswith("off:") else "CAPTION_TWICE", "key": k, "at": f0, "to": f1, "what": info[k]})
    return flags


STILL_BAR = 0.45


SRC_MOTION = {}


def source_moves(pub, src, sec, bar=0.5):
    """does the clip's own picture move around this second of it? (mean grey change between frames 0.1 s apart at 90x160 over 0.6 s;
    a title card or a held frame is under 0.5, so a still card never counts as motion and its still stretch is checked).
    `bar`: SPEAKING_BAR for an interview bite (see there)"""
    k = str(src)
    if k not in SRC_MOTION:
        def measure():
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pub / src), "-vf", "fps=10,scale=90:160:flags=area,format=gray", "-f", "rawvideo",
                                  "-"], capture_output=True).stdout
            n = len(raw) // (90 * 160)
            a_ = np.frombuffer(raw[: n * 90 * 160], np.uint8).reshape(n, 160, 90).astype(np.int16) if n else None
            return [round(float(np.abs(a_[i] - a_[i - 1]).mean()), 3) for i in range(1, n)] if n > 1 else []
        SRC_MOTION[k] = cached("srcmove", pub / src, "", measure)
    m = SRC_MOTION[k]
    if not m:
        return True
    i = int(sec * 10)
    seg = m[max(0, i - 3): i + 3] or m[-3:]
    return float(np.median(seg)) >= bar


# an interview bite (a clip named bite_*, playing with its own voice) is a face talking, and a face talking moves less than footage:
# speaking bites measure 0.30-0.31 (heads turning, mouths moving, by their frames) where a held logo measures 0.01 and footage 7-22, so
# at 0.5 a speaker would read as a frozen picture. A held frame or a slide inside a bite (0.01-0.05) stays under this bar
SPEAKING_BAR = 0.15


TEXTURE = {}


def source_texture(pub, src):
    """how much detail a clip's middle frame has (mean grey step between neighbours at 90x160): a dark title card is ~1, footage 5+"""
    k = str(src)
    if k not in TEXTURE:
        def measure():
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(pub / src)], capture_output=True,
                               text=True)
            try:
                mid = float(r.stdout.strip()) / 2
            except ValueError:
                return 10.0
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{mid:.2f}", "-i", str(pub / src), "-frames:v", "1", "-vf",
                                  "scale=90:160:flags=area,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
            if len(raw) != 90 * 160:
                return 10.0
            a_ = np.frombuffer(raw, np.uint8).reshape(160, 90).astype(np.int16)
            return float(np.abs(np.diff(a_, axis=1)).mean() + np.abs(np.diff(a_, axis=0)).mean()) / 2
        TEXTURE[k] = cached("texture", pub / src, "", measure)
    return TEXTURE[k]


REUSE = [False]   # set by step_gate from --reuse

PUSH_RATE = 0.005   # a big picture growing 0.5% a second or more is under a push (a still's 1.00-1.04 over 2.5 s is 1.6%; a menu's 1.00-1.02 0.8%)
PAN_RATE = 0.3      # px a frame its centre travels: a pan


def pushed(layout, f, span=15):
    """a big still picture (img, 40% of the frame or more, opacity 0.5+) on frame f that grows or travels over the frames around it.
    Pictures only: a clip whose footage stands still under a slow push reads frozen (a static clip under a push, a frozen countdown
    grid: real STILL faults; check_still's clip test keeps judging those)"""
    W, H = FRAME
    a = f - span if (f - span) in layout else f
    b = f + span if (f + span) in layout else f
    if b - a < 10:
        return False
    def big(fr):
        return {(it["k"], str(it["t"])): it for it in layout.get(fr, []) if it["k"] == "img" and it["op"] >= 0.5
                and it["w"] * it["h"] >= 0.4 * W * H}
    A, B = big(a), big(b)
    for k, p in A.items():
        q = B.get(k)
        if not q:
            continue
        rate = abs(q["w"] / max(p["w"], 1) - 1) / ((b - a) / FPS)
        move = (abs(q["x"] + q["w"] / 2 - p["x"] - p["w"] / 2) + abs(q["y"] + q["h"] / 2 - p["y"] - p["h"] / 2)) / (b - a)
        if rate >= PUSH_RATE or move >= PAN_RATE:
            return True
    return False


def reading(items, words=8):
    """a card being read: `words` or more of our own text at reading size (26 px+, opacity 0.5+; credits, names and rolling digits aside)
    over a still or a ground, never over an interview bite, which must be seen talking (a quote over a frozen bite is a real STILL)"""
    W, H = FRAME
    if any(it["k"] == "clip" and it["op"] >= 0.5 and Path(str(it["t"])).stem.startswith("bite_") and it["w"] * it["h"] >= 0.4 * W * H for it in items):
        return False
    n = sum(len(str(it["t"]).split()) for it in items if it["k"] == "text" and it["op"] >= 0.5 and (it.get("fs") or 0) >= 26
            and it.get("g") not in ("credit", "name", "roll"))
    return n >= words


STILL_RENDER = [True]   # False: the analysis alone (gate.py --probe-dir), no Remotion


def merge_frames(frames, gap=1):
    """sorted frames -> [(a, b)] runs (frames within `gap` of each other join)"""
    out = []
    for f in sorted(frames):
        if out and f - out[-1][1] <= gap:
            out[-1][1] = f
        else:
            out.append([f, f])
    return [(a, b) for a, b in out]


def draw_stills(v, out, spans):
    """the probe's pictures (graphics only, clips hidden) of these frame spans into out/element-<frame>.jpeg"""
    import pipe
    tmp = out.parent / "still_new"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with RemotionJob(f"gate stills {v.id}", None):
        r = pipe.run_watched([NODE, "gate_probe.mjs", tmp, "0.25", ",".join(f"{a}-{b}" for a, b in spans), "1", "--png"], MOTION,
                             {"QA_COMP": v.comp, "QA_PUBLIC": v.pub.as_posix(), **temp_env()}, tmp / "probe.log", stall=300)
    after_remotion()
    if r.returncode != 0 or getattr(r, "stalled", False):
        raise SystemExit(f"gate: the still probe failed: {tmp / 'probe.log'}")
    for p_ in tmp.glob("element-*.jp*g"):
        os.replace(p_, out / p_.name)
    shutil.rmtree(tmp, ignore_errors=True)


def static_footage(v, layout, clips, f):
    """the name of a full-frame clip of footage (40% of the frame or more, opacity 0.5+, detail like footage: source_texture 3+) on frame
    f, not an interview bite (a bite must be seen talking: its stillness stays a STILL); None when there is none"""
    W, H = FRAME
    for it in layout.get(f, []):
        if it["k"] == "clip" and it["op"] >= 0.5 and it["w"] * it["h"] >= 0.4 * W * H:
            name = Path(str(it["t"])).stem
            if not name.startswith("bite_") and source_texture(v.pub, str(it["t"])) >= 3.0:
                return name
    return None


BUILT_STILL_CAP = 6.0   # s: a built graphic standing longer than this with nothing changing flags (a long one by design stands ~3.9 s)


def built_still(items):
    """a built graphic is the picture: no sharp, undimmed picture fills half the frame (a blurred or dimmed ground is the graphic's own,
    as a card over its blurred hallway, a profile card over a person at 62%), or the graphic's panels sit on top (opaque boxes or
    shapes of 5-90% of the frame: phone cards, price panels). A screenshot alone with its credit is no graphic, and neither is one
    under a full-frame vignette. Nor is a picture card with none of our words on screen: a sharp page or screenshot of 20-90% of the
    frame standing still is a fault (a news page on its card for 3.9 s). Measured on a labelled set of STILL flags: all 6 real ones
    still raised, 33 of 90 by design dropped"""
    W, H = FRAME
    A = W * H
    pics = [it for it in items if it["k"] in ("img", "clip") and it["op"] >= 0.5 and it["w"] * it["h"] >= 0.5 * A]
    sharp = lambda it: not it.get("bl") and it.get("br", 1) >= 0.9
    ours = any(it["k"] == "text" and it["op"] >= 0.5 and it.get("g") != "credit" and str(it["t"]).strip() for it in items)
    cards = [it for it in items if it["k"] in ("img", "clip") and it["op"] >= 0.5 and sharp(it) and 0.2 * A <= it["w"] * it["h"] <= 0.9 * A]
    if not ours and len({str(it["t"]) for it in cards}) == 1:   # one card alone (a row of picture cards is a graphic: price panels)
        return False
    if not any(sharp(it) for it in pics):
        return True
    return any(it["k"] in ("box", "svg") and it["op"] >= 0.5 and 0.05 * A <= it["w"] * it["h"] <= 0.9 * A for it in items)


def still_key(items, f):
    """a STILL flag's allow key that survives a re-timing (a frame-number key goes stale whenever a re-probe moves a stretch by one
    frame): the biggest picture's name, else the biggest words on screen, else the frame"""
    pics = sorted((it for it in items if it["k"] in ("img", "clip") and it["op"] >= 0.3), key=lambda it: -it["w"] * it["h"])
    if pics:
        return f"pic:{Path(str(pics[0]['t'])).stem}"
    words = sorted((it for it in items if it["k"] == "text" and it.get("g") != "credit" and str(it["t"]).strip()),
                   key=lambda it: -it.get("fs", 0) * len(str(it["t"])))
    return f"text:{str(words[0]['t']).strip()[:40]}" if words else f"{f}"


def check_still(v, layout, d, clips=None):
    """B1 STILL: a designed stretch (no clip on screen) whose picture stands still: qa_render's frozen test (the frame's mean grey change
    under 0.35 at 90x160 for 0.8 s in a Short, 2 s in long form) run before the render, on the probe's own pictures of those stretches
    (three logos drifting 10% a second on a dark ground read as a frozen picture; a slow drift of a small thing doesn't move the
    frame). The probe's 0.25-scale JPEGs change more frame to frame than the h264 file does (a row of logos: median 0.35 against the
    export's 0.27), so the probe's bar is 0.45: on six designed stretches it flagged frames 1529-1588 and nothing else, where qa_render
    on the export flagged 1535-1588 and nothing else"""
    short = FRAME[1] > FRAME[0]
    need = round((0.8 if short else 2.0) * FPS)
    free = []
    W, H = FRAME
    for f in sorted(layout):
        # the by-design stills (most STILL flags on a long film are one of these three kinds):
        #  - a mark on screen: B12 wants the picture frozen under its marks (a receipt standing from its first mark to the cut)
        #  - a big picture under the house camera's one slow push or a pan (a still's 1.00-1.04 over 2.5 s, a menu's 1.00-1.02): the
        #    frame changes too little for the frozen test, the eye sees the push
        #  - a card being read: 8 words or more of our own text at reading size (a quote or headline the voice reads on its card)
        if mark_items(layout[f], W, H) or pushed(layout, f) or reading(layout[f]):
            free.append((f, False))
            continue
        big = [it for it in layout[f] if it["k"] == "clip" and it["op"] >= 0.3 and it["w"] * it["h"] > 0.02 * FRAME[0] * FRAME[1]]
        secs = {str(c["src"]): c["s"] for c in (clips or {}).get(f, [])}
        # a still clip pushed or panned moves the frame too (the probe draws it as a blank pane, so its own push can't be seen there):
        # its box growing 6%+ a second or sliding 1+ px a frame
        prev = {str(it["t"]): it for it in layout.get(f - 1, []) if it["k"] == "clip"}
        def boxed(it):
            q = prev.get(str(it["t"]))
            return bool(q) and (abs(it["w"] / max(q["w"], 1) - 1) > 0.001 or abs(it["x"] - q["x"]) + abs(it["y"] - q["y"]) > 1.0)
        # a blurred ground under half opacity barely moves the frame however its footage moves (a card over a blurred skyline reads as a
        # frozen picture on the export, though the skyline itself moves)
        clip = any((it["op"] >= 0.5 and source_moves(v.pub, str(it["t"]), secs.get(str(it["t"]), 0.0),
                                                      SPEAKING_BAR if Path(str(it["t"])).stem.startswith("bite_") else 0.5))
                   or (boxed(it) and source_texture(v.pub, str(it["t"])) >= 3.0) for it in big)
        free.append((f, not clip))
    runs, start = [], None
    for f, ok in free + [(None, False)]:
        if ok and start is None:
            start = f
        if not ok and start is not None:
            if prev - start + 1 >= need:
                runs.append((start, prev))
            start = None
        prev = f
    if not runs:
        return []
    out = d / "still"
    out.mkdir(parents=True, exist_ok=True)
    # incremental (drawing every still stretch again takes 25-44 min a run on a long film): the pictures are kept per frame. A full
    # probe empties this folder (they show the old code), a --reprobe deletes the frames it re-probes and
    # moves the rest with a timing change (reprobe.py); only frames of the runs without a picture are drawn
    have = {int(m.group(1)) for p_ in out.glob("element-*.jp*g") if (m := re.search(r"(\d+)\.jpe?g$", p_.name))}
    missing = sorted(f for a, b in runs for f in range(a, b + 1) if f not in have)
    if missing and STILL_RENDER[0]:
        spans = merge_frames(missing)
        say(f"  B1 stills: drawing {len(missing)} frames in {len(spans)} stretches ({len(have)} kept from before)")
        draw_stills(v, out, spans)
    elif missing:
        say(f"  B1 stills: {len(missing)} frames have no picture and are not drawn (analysis only): read as moving")
    else:
        say(f"  B1 stills: every frame of the {len(runs)} runs already has its picture")
    from PIL import Image
    files = {int(re.search(r"(\d+)\.jpe?g$", p.name).group(1)): p for p in out.glob("element-*.jp*g")}
    flags = []
    for a, b in runs:
        prev_g, still = None, []
        for f in range(a, b + 1):
            if f not in files:
                prev_g = None
                still.append((f, False))
                continue
            g = np.asarray(Image.open(files[f]).convert("L").resize((90, 160) if short else (160, 90), Image.BOX)).astype(np.int16)
            still.append((f, float(np.abs(g - prev_g).mean()) if prev_g is not None else 99.0))
            prev_g = g
        dv = [x[1] if isinstance(x[1], float) else 99.0 for x in still]
        sm = [float(np.median(dv[max(0, i - 1): i + 2])) for i in range(len(dv))]
        still = [(f, sm[i] < STILL_BAR) for i, (f, _) in enumerate(still)]
        s0 = None
        for f, s in still + [(None, False)]:
            if s and s0 is None:
                s0 = f
            if not s and s0 is not None:
                if pf - s0 + 1 >= need:
                    src = static_footage(v, layout, clips, (s0 + pf) // 2)
                    if src:
                        # a full-frame clip of footage or a screen that stands still in its own source (a menu, a checklist, a
                        # store page, a progress bar, a figure standing): the eye's call, not a fault the machine can name (most
                        # such stretches are still by nature, the thing the words name): listed to look at, never blocking
                        flags.append({"check": "STILL_SOURCE", "key": f"{s0}", "at": s0, "to": pf, "look": True,
                                      "what": f"{src} stands still in its own source for {(pf - s0 + 1) / FPS:.2f} s (a still screen or "
                                              f"frozen-looking footage: look whether it is the thing the words name)"})
                    elif not short and built_still(layout.get((s0 + pf) // 2, [])) and (pf - s0 + 1) < BUILT_STILL_CAP * FPS:
                        # a built graphic standing for its words to be read (no sharp full-frame picture under it): by design in long
                        # form (such graphics hold 2.0-3.9 s; a render-time freeze is the render scan's). One standing
                        # BUILT_STILL_CAP s+ with nothing changing still flags. Shorts keep the 0.8-s test
                        pass
                    else:
                        mid = layout.get((s0 + pf) // 2, [])
                        flags.append({"check": "STILL", "key": still_key(mid, s0), "at": s0, "to": pf,
                                      "what": f"the picture stands still for {(pf - s0 + 1) / FPS:.2f} s (no clip on screen; qa_render's frozen test)"})
                s0 = None
            pf = f
    return flags


# ============================================================================================================================ report
def files_sha(files):
    """the hash of a signed-off stretch's code (repo-relative paths)"""
    h = hashlib.sha1()
    for f in sorted(files):
        p = REPO / f
        h.update(f.encode())
        h.update(p.read_bytes() if p.exists() else b"(missing)")
    return h.hexdigest()[:16]


def signed_off(v, flags):
    """[[gate.signed]] in video.toml: a stretch the creator passed as it is, e.g. a prototype's first shots S01-S04: {frames = "0-3345",
    files = [the code it is drawn from], sha = files_sha(files), note = the creator's verdict}. Its flags are what the creator already
    saw and passed, so they are listed apart and don't stop the line, while the code is the code they passed: a change to any of its
    files changes the sha and its flags count again.
    Frames are on the current timing. -> (flags left, [(flag, note)] signed off, [stale notes])"""
    keep, signed, stale = [], [], []
    spans = []
    for s in (v.section("gate").get("signed") or []) if hasattr(v, "section") else []:
        f0, f1 = (int(x) for x in str(s["frames"]).split("-"))
        sha = files_sha(s.get("files", []))
        if sha == s.get("sha"):
            spans.append((f0, f1, s.get("note", "")))
        else:
            stale.append(f"{s['frames']}: its code changed since the creator passed it (sha {sha}, signed {s.get('sha')}): its flags count again")
    for fl in flags:
        sp = next((x for x in spans if x[0] <= fl["at"] <= x[1]), None)
        (signed.append((fl, sp[2])) if sp else keep.append(fl))
    return keep, signed, stale


def in_frames(x, fl):
    """an allow from a range's file (merge_allows.py with rebuild/ranges.json) holds only inside its range's frames"""
    fr_ = x.get("frames")
    at = fl.get("at")
    return not fr_ or not isinstance(at, (int, float)) or fr_[0] <= at <= fr_[1]


def measured_ok(x, fl):
    """a sound on nothing the probe sees is allowed only with the change's measured second (disproved by frames, never by reasoning:
    "a custom piece the probe doesn't report" can hide a marker 0.9 s off its light)"""
    if fl["check"] != "SOUND_NOTHING_SHOWN":
        return True
    m = x.get("measured")
    return isinstance(m, (int, float)) and -0.1 <= m - fl["at"] / FPS <= 0.25


def allowed(v, flags):
    p = v.folder / "gate_allow.json"
    allow = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    keep, ok = [], []
    for fl in flags:
        # a flag that measures its own fix (the light's time for a marker off its light) is never allowed: it is fixed
        a = None if fl.get("no_allow") else next((x for x in allow if x["check"] == fl["check"] and (x["key"] in fl["key"] or x["key"] in fl["what"]) and x.get("reason")
                  and in_frames(x, fl) and measured_ok(x, fl)), None)
        (ok if a else keep).append((fl, a))
    return [k for k, _ in keep], ok


LOADED = []   # the last probe analyse() loaded: (clips, layout), so step_gate doesn't parse 240 MB three times


def analyse(v, probe, shots, durs, pub, effects_log, clips_json):
    clips, layout = load_probe(probe)
    LOADED[:] = [clips, layout]
    plays = group_plays(clips)
    say(f"probe: {len(layout)} frames measured, {len(plays)} clip plays")
    flags = []
    for name, fn in (("B1 freezes", lambda: check_freezes(plays, durs)), ("B1 holds", lambda: check_holds(plays, pub, durs, layout)),
                     ("B2 flashes", lambda: check_flashes(plays, pub, durs)), ("B2 fades", lambda: check_fades(plays, pub, layout)), ("B3 gaps", lambda: check_gaps(clips, shots)), ("B3 blank", lambda: check_blank(layout)), ("B3 blank long", lambda: check_blank_long(layout)),
                     ("B4 layout", lambda: check_layout(layout)), ("B4 overlap", lambda: check_overlap(layout, pub)), ("B5 motion", lambda: check_motion(layout, shots, effects_from_log(effects_log))),
                     ("B6 sync", lambda: check_sync(layout, clips, shots, effects_from_log(effects_log), pub)),
                     ("B7 reuse", lambda: check_reuse(plays, clips_json)), ("B8 cut-outs", lambda: check_cutouts(layout, pub)),
                     ("B12 marks", lambda: check_marks(layout, clips)), ("B13 text overlap", lambda: check_text_overlap(layout)),
                     ("B14 row centre", lambda: check_row_centre(layout, pub)), ("B15 kit3 refusals", check_refusals),
                     ("B24 text hold", lambda: check_text_hold(layout)), ("B25 mark zoom", lambda: check_mark_zoom(layout))):
        t0 = time.time()
        h0, m0 = CACHE["hits"], CACHE["miss"]
        try:
            got = fn()
        except Exception as e:  # noqa: BLE001
            got = [crashed_flag(name, e)]
        hm = f"; {CACHE['hits'] - h0} from the cache, {CACHE['miss'] - m0} measured" if CACHE["hits"] + CACHE["miss"] > h0 + m0 else ""
        say(f"  {name}: {len(got)} flag(s) ({time.time() - t0:.0f} s{hm})")
        flags += got
    cache_save()
    return sorted(flags, key=lambda x: x["at"]), plays


def write_report(v, flags, ok, out, stamp, signed=(), stale=(), note="", look=()):
    lines = [f"# Gate {v.id} ({time.strftime('%Y-%m-%d %H:%M')}): {'PASS' if not flags else f'{len(flags)} flag(s)'}", "",
             f"code stamp {stamp}; allowed in gate_allow.json: {len(ok)}; signed off by the creator: {len(signed)}" + (f"; {note}" if note else ""), ""]
    lines += [f"- STALE SIGN-OFF {s}" for s in stale]
    for fl in flags:
        to = f"-{mmss(fl['to'])}" if fl.get("to") else ""
        lines.append(f"- **{fl['check']}** {mmss(fl['at'])}{to} (frame {fl['at']}): {fl['what']}")
    if look:
        lines += ["", "## To look at (not blocking: the eye's call, the machine can't name a fault here)"]
        for fl in look:
            to = f"-{mmss(fl['to'])}" if fl.get("to") else ""
            lines.append(f"- {fl['check']} {mmss(fl['at'])}{to} (frame {fl['at']}): {fl['what']}")
    if signed:
        lines += ["", "## Signed off by the creator ([[gate.signed]] in video.toml, its code unchanged)"]
        for fl, n in signed:
            lines.append(f"- {fl['check']} {mmss(fl['at'])}: {fl['what']} — {n}")
    if ok:
        lines += ["", "## Allowed (gate_allow.json)"]
        for fl, a in ok:
            lines.append(f"- {fl['check']} {mmss(fl['at'])}: {fl['what']} — {a['reason']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sound_gate(v, d):
    """A1-A11 + LOCK (tools/sound/gate_sound.py, the editing venv; A10 word fragments, A11 accent and the voice lock's check,
    standard/VOICE_LOCK.md): its lines, and whether it passed"""
    r = subprocess.run([str(PY_EDIT), str(TOOLS / "sound" / "gate_sound.py"), v.slug, "--json", str(d / "sound.json")],
                       capture_output=True, text=True, errors="replace", env={**__import__("os").environ, "PYTHONUTF8": "1"})
    for line in (r.stdout or "").strip().splitlines()[-12:]:
        say(f"  {line}")
    if r.returncode not in (0, 1):
        say((r.stderr or "")[-600:])
    return r.returncode == 0


def clear_stills(d):
    """a full probe: the still pictures showed the old code, so they go (the still pass draws the frames it needs again)"""
    sd = d / "still"
    if sd.exists():
        for p_ in sd.glob("element-*.jp*g"):
            p_.unlink()


def step_gate(v, a):
    import pipe
    bad = preflight(v)
    for b in bad:
        say(b)
    if bad:
        raise SystemExit("gate: B0 failed")
    REUSE[0] = bool(getattr(a, "reuse", False))
    t_gate = time.time()
    d = v.pipe_dir / "gate"
    d.mkdir(parents=True, exist_ok=True)
    say("sound (A1-A11 + LOCK):")
    sound_ok = sound_gate(v, d)
    probe = d / "probe.jsonl"
    stamp = code_stamp(v)
    pstamp = code_stamp(v, probe=True)      # the probe's own stamp: allows change no frame
    cache_open(d / "analysis_cache.json")
    import reprobe as rp
    shots = None
    if v.kind != "short":
        rep = pipe.audit_report(v, tag="shots")
        shots = rep["shots"]
        total = fr(rep["seconds"]) if rep.get("seconds") else v.frames()
    if getattr(a, "reprobe", None) and probe.exists():
        probe = reprobe(v, d, a.reprobe)
        (d / "stamp.txt").write_text(pstamp, encoding="utf-8")
    elif a.reuse and probe.exists() and (d / "stamp.txt").exists() and (d / "stamp.txt").read_text().strip() in (pstamp, stamp):
        say("probe: the last probe reused (--reuse: the same probe stamp)")
    elif v.kind != "short" and probe.exists() and not getattr(a, "full", False):
        # the incremental, shift-aware probe (reprobe.py): the changed shots, the seams of a timing change and every 12th frame as
        # sentinels; the rest of the old probe moved with the timing. A full probe when the plan can't (no snapshot, the probe changed)
        snap = rp.snapshot(v, total, shots)
        p = rp.plan(v, rp.load_state(d), snap)
        (d / "reprobe_plan.json").write_text(json.dumps(p, indent=1), encoding="utf-8")
        if p["full"]:
            say(f"probe: a full probe ({p['full']})")
            probe = run_probe(v, d)
            clear_stills(d)
        else:
            say(f"probe: incremental: {p['why'].get('probe_frames')} of {total} frames to probe ({len(p['why'].get('changed_files', []))} files "
                f"changed, {p['why'].get('unmatched_shots')} shots new or moved in length, {p['why'].get('reached_by_files')} reached by changed files)")
            rp.incremental(v, d, p)
        (d / "stamp.txt").write_text(pstamp, encoding="utf-8")
    else:
        probe = run_probe(v, d)
        clear_stills(d)
        (d / "stamp.txt").write_text(pstamp, encoding="utf-8")
    if v.kind == "short":
        c, lay = load_probe(probe)
        shots = shots_from_probe(lay, c)
        say(f"shots from the probe (a built Short): {len(shots)}")
    else:
        rp.save_state(d, rp.snapshot(v, total, shots))   # what this probe was made on: the next run's plan starts here
    durs = json.loads((MOTION / "src/clipdurs.json").read_text(encoding="utf-8"))
    logs = sorted(v.pipe_dir.glob("score_v*.log"), key=lambda p: p.stat().st_mtime)
    G = v.section("gate") if hasattr(v, "section") else {}
    clips_json = G.get("clips_json")
    fx = effects_from_cues(v)
    say(f"effects: {len(fx)} from the cue sheet" if fx is not None else "effects: from the newest score report")
    flags, plays = analyse(v, probe, shots, durs, v.pub, fx if fx is not None else (logs[-1] if logs else None), clips_json)
    t0 = time.time()
    _cl, _lay = LOADED
    got = check_still(v, _lay, d, _cl)
    say(f"  B1 stills: {len(got)} flag(s) ({time.time() - t0:.0f} s)")
    lay = _lay
    # B16 marks on their targets (qa_marks.py, the hand method of checking marks as a tool): a border on the letters, a box on the
    # wrong line or past its card, a mark with nothing to pick out (MARK_LOOSE and MARK_UNSAID are information, in pipeline/gate/marks/)
    t0 = time.time()
    import qa_marks
    mk = [f for f in qa_marks.check_marks_target(v.pub, lay, _cl, out=d / "marks") if f["check"] in ("MARK_OFF", "MARK_REDUNDANT")]
    say(f"  B16 marks on target: {len(mk)} flag(s) ({time.time() - t0:.0f} s; crops in {d / 'marks'})")
    got += mk
    # B17 a lit phrase against the words said round it (qa_lit.py: the voice says one thing while the mark lights another): a
    # heuristic by word stems (a synonym or a number said in words flags too), so it is listed to look at, never blocking
    try:
        sys.path.insert(0, str(MOTION))
        import qa_lit
        n_lit, lit = qa_lit.check(v.src_dir)
        got += [{"check": "LIT_UNSAID", "key": x[:80], "at": 0, "look": True, "what": x} for x in lit]
        say(f"  B17 lights against their words: {len(lit)} of {n_lit} to look at")
    except (OSError, ValueError) as e:
        say(f"  B17 lights: not read ({e})")
    cr = check_credits(lay, clip_sources(v))
    say(f"  B9 credits: {len(cr)} flag(s)")
    tw = check_twice(plays, lay, clip_spans(v))
    say(f"  B7 twice: {len(tw)} flag(s)")
    lb = (check_letterbox(lay, v.pub) if v.kind == "short" else check_letterbox_cut(lay, v.pub, clip_sources(v))) \
        + check_aspect(lay, v.pub) + check_upscale(lay, v.pub)
    say(f"  B4 letterbox/aspect/upscale: {len(lb)} flag(s)")
    em = check_empty(lay)
    say(f"  B4 empty: {len(em)} flag(s)")
    lb += em
    ou = check_outro(v, lay)
    say(f"  B26 outro: {len(ou)} flag(s)")
    lb += ou
    # B11 PAN is off (a pan is used only when it has a job, never for its own sake): it made every wide picture travel, and no check can
    # know a pan's reason; GATE_B11=1 runs it as information
    import os
    pn = check_pan(lay) if v.kind == "short" and os.environ.get("GATE_B11") == "1" else []
    say(f"  B11 pan: {len(pn)} flag(s)")
    lb += pn
    ct = check_caption_twice(v, lay) if v.kind == "short" else []
    say(f"  B10 caption twice: {len(ct)} flag(s)")
    # B19 CARDS (text cards are rare: people watch videos, they don't come to read): every page / headline / quote / number card in the
    # code needs its written reason ("// card: ..."), cards stay under 8% of the film and never two within 20 s (tools/motion/qa_cards.py;
    # the film's shots from the probe's shots_<comp>.json)
    cd = []
    if v.kind == "long":
        try:
            sys.path.insert(0, str(MOTION))
            import qa_cards
            cd = qa_cards.gate_flags(v)
            say(f"  B19 cards: {len(cd)} flag(s)")
        except Exception as e:   # the check must never take the gate down; it says why it couldn't read
            say(f"  B19 cards: not read ({e})")
        # B20 picture vs words (a held picture that looks like a frozen frame, a mark so small in a corner most viewers miss it, a thing
        # the words name shown as text): STILL_UNDER_ACTION (a held picture under words of motion), CARD_FOR_MOMENT (a card under "we can
        # see" / "in the video"), MARK_SMALL (< 48 px), MARK_CORNER
        try:
            import qa_still_words
            sw = qa_still_words.gate_flags(v, lay, _cl)
            say(f"  B20 still/marks vs words: {len(sw)} flag(s)")
            cd += sw
        except Exception as e:
            say(f"  B20 still/marks vs words: not read ({e})")
        # B21 centred (a logo not centred left to right; a face placed badly within its circle): LOGO_OFF_CENTRE (a logo's visual centre
        # over 12 px off, 3D from kit3d's own probe lines), ICON_FACE_OFF and the icon-source check (face icons cut from the source
        # footage, the face centred: make_icon.py)
        try:
            import qa_centred
            ce = qa_centred.gate_flags(v, lay, _cl)
            say(f"  B21 centred logos and icons: {len(ce)} flag(s)")
            cd += ce
        except Exception as e:
            say(f"  B21 centred logos and icons: not read ({e})")
        # B22 shots (a subject the viewer has to look for; artwork too often in a short stretch; pictures that just look low in
        # brightness): SUBJECT (every still and cropped/zoomed clip names its subject, `// subject: <label> x y w h`, and it lands
        # central, whole, big, lit), ART (source footage first, `// art: <why>`, no third artwork inside 20 s, under 8% of the film),
        # DARK (murky, not night)
        try:
            import qa_shots
            sh = qa_shots.gate_flags(v, lay, _cl)
            say(f"  B22 subject, artwork, dark: {len(sh)} flag(s)")
            cd += sh
        except Exception as e:
            say(f"  B22 subject, artwork, dark: not read ({e})")
        # B23 devices (circles all over a video read as a template; one map of face icons copied into dozens of graphics): from the
        # code, each shot's main picture (clip, still or the graphic component it is); DEVICE_SPREAD (one graphic component the main
        # picture of more than 6 appearances without `// device: <why>` above a shot), ROUND_CROP (a round crop of a screenshot as a
        # shot's picture, outright: the two main people's portraits only where the words name both and the shot says
        # `// device: portrait <why>`) (tools/motion/qa_devices.py)
        try:
            import qa_devices
            dv = qa_devices.gate_flags(v)
            say(f"  B23 devices and round crops: {len(dv)} flag(s)")
            cd += dv
        except Exception as e:
            say(f"  B23 devices and round crops: not read ({e})")
    flags = sorted(flags + got + cr + tw + lb + ct + cd, key=lambda x: x["at"])
    look = [f for f in flags if f.get("look")]
    flags = [f for f in flags if not f.get("look")]
    flags, signed, stale = signed_off(v, flags)
    flags, ok = allowed(v, flags)
    rep = v.pipe_dir / "gate.md"
    rpj = d / "reprobe_report.json"
    note = ""
    if rpj.exists() and rpj.stat().st_mtime > t_gate:
        r_ = json.loads(rpj.read_text(encoding="utf-8"))
        note = f"probe spliced: {r_['probed_frames']} frames probed, {r_['reused_frames']} reused, sentinels every {r_['sentinel_every']} ({r_['sentinel_differ']} differed)"
    write_report(v, flags, ok, rep, stamp, signed, stale, note, look)
    (d / "flags.json").write_text(json.dumps(flags, indent=1), encoding="utf-8")
    # the coherency half: a current fresh read of this script and code with every flag closed (coherency.py check);
    # a long video only (a Short's script is read by the Shorts chat's own checks)
    coh_ok = True
    if v.kind == "long":
        import coherency
        say("coherency:")
        coh_ok = coherency.check(v) == 0
    say(f"gate: picture {'PASS' if not flags else f'{len(flags)} flag(s)'} ({len(ok)} allowed, {len(signed)} signed off) -> {rep}; sound {'PASS' if sound_ok else 'FAIL'} -> {d / 'sound.json'}"
        + ("" if v.kind != "long" else f"; coherency {'PASS' if coh_ok else 'FAIL'} -> {v.folder / 'COHERENCY.md'}"))
    if not flags and sound_ok and coh_ok:
        (d / "passed.txt").write_text(stamp, encoding="utf-8")
    elif (d / "passed.txt").exists():
        (d / "passed.txt").unlink()
    if flags or not sound_ok or not coh_ok:
        raise SystemExit(1)


# ======================================================================================================================= the scoped gate
# The aim is check - all flags - fixes - done, never check - flags - fixes - check - many flags again: checks run only at the end, on
# the whole film, leave builders and fixers blind to them, and every round's fixes are new, unchecked pictures the next run flags.
# `pipe.py <video> gate --scope a-b,c-d` runs the gate's own picture checks on a builder's or fixer's own shots, in minutes, inside their
# loop; the full gate before the render only confirms. It replaces the full gate runs inside a fix round (a full run on a long film:
# ~14 min for the picture half, ~18.5 with the sound half).
SCOPE_MARGIN = 60          # frames probed fresh on each side of the scope (1 s): what the checks look at round a frame (B3 BLANK 8 frames
#                            back, the push test 15, a landing 30, a run of 30 for OFF_FRAME) is the new code at the scope's edges too
SCOPE_CLOSE = 20 * FPS     # the last full probe's frames on each side of the scope for the one rule counted across 20 s in the picture
#                            (ART_CLOSE, a third artwork shot inside 20 s); CARD_CLOSE reads the audit's shots of the whole film
SCOPE_JOIN = 150           # probed stretches closer than this are probed as one (each renderFrames call costs ~4 s: reprobe.JOIN)
FILM_WIDE = ("CARD_TIME", "ART_SHARE", "DEVICE_SPREAD")   # the whole film's totals: listed apart when the scope adds to them, never
#                                                           blocking here (the full gate's call: a part can't settle a share)


def merge_spans(spans, gap=0):
    """[(a, b)] sorted, with overlapping, touching or (within `gap` frames) close ones joined"""
    out = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1] + 1 + gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def parse_scope(spec):
    out = []
    for r in str(spec).replace(" ", "").split(","):
        if not r:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", r)
        if not m or int(m.group(1)) > int(m.group(2)):
            raise SystemExit(f"gate --scope: {r!r} is not a frame range a-b (frames, as the gate's report gives them: 'frame 51234')")
        out.append((int(m.group(1)), int(m.group(2))))
    if not out:
        raise SystemExit("gate --scope: give the frame ranges of your shots, a-b,c-d")
    return merge_spans(out)


def widen_to_shots(ranges, shots, total):
    """each range -> the whole shots it touches: a shot is checked whole, its cut and its last 0.25 s too (MOVING_AT_CUT, MARK_LATE)"""
    out = []
    for a, b in ranges:
        if a > total - 1:
            raise SystemExit(f"gate --scope: {a}-{b} starts past the film's last frame ({total - 1})")
        a, b = max(0, a), min(total - 1, b)
        hit = [s for s in shots if fr(s["at"]) <= b and fr(s["end"]) - 1 >= a]
        if hit:
            a, b = min(a, min(fr(s["at"]) for s in hit)), min(total - 1, max(b, max(fr(s["end"]) - 1 for s in hit)))
        out.append((a, b))
    return merge_spans(out)


def overlaps(f0, f1, spans):
    return any(a <= f1 and f0 <= b for a, b in spans)


def read_at_once(path):
    """a file's bytes in one read, open for a moment only: on Windows another process's os.replace of a file fails while it is open
    (measured: PermissionError, and FILE_SHARE_DELETE on the reader doesn't change it), and the full gate replaces probe.jsonl
    and analysis_cache.json that way"""
    with open(path, "rb") as fh:
        return fh.read()


class LastProbe:
    """the last full probe (pipeline/gate/probe.jsonl) as the scoped gate reads it: its clip lines parsed (every play of the film, for
    TWICE), its layout lines indexed by frame and parsed only where asked (a 139-MB probe: ~1 s, where load_probe takes 3 s and ~10x the
    memory). Read in one go while the scope holds the Remotion ticket (no full probe writes it then) and kept in memory until load() is
    done with it (drop())."""
    LINE = re.compile(rb'layout\|\{"frame":(\d+)')

    def __init__(self, path):
        self.path = Path(path)
        self.clips, self.idx, self.layout, self.ats = defaultdict(list), {}, {}, {}
        self.data = read_at_once(self.path) if self.path.exists() else b""
        data, pos, n = self.data, 0, len(self.data)
        while pos < n:
            end = data.find(b"\n", pos)
            end = n if end < 0 else end + 1
            if data.startswith(b"clip|", pos):
                try:
                    o = json.loads(data[pos + 5:end])
                    self.clips[o["abs"]].append(o)
                except (ValueError, KeyError):
                    pass
            elif data.startswith(b"layout|", pos):
                m = self.LINE.match(data, pos)
                if m and int(m.group(1)) not in self.idx:
                    self.idx[int(m.group(1))] = (pos, end)
            pos = end

    @property
    def frames(self):
        return max(self.idx) + 1 if self.idx else 0

    def load(self, frames):
        """these frames' layout lines parsed into self.layout (their <At> starts into self.ats)"""
        for f in sorted(f for f in set(frames) if f in self.idx and f not in self.layout):
            a, b = self.idx[f]
            try:
                o = json.loads(self.data[a + len(b"layout|"):b])
            except ValueError:
                continue
            self.layout[f] = one_copy(o["items"])
            self.ats[f] = o.get("ats", [])

    def drop(self):
        self.data = b""


def read_scope_probe(path):
    """the scope's own probe: ({frame: clip lines}, {frame: items}, {frame: refusal}, {frame: <At> starts}, (W, H))"""
    clips, layout, ref, ats, wh = defaultdict(list), {}, {}, {}, None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            kind, _, body = line.partition("|")
            if kind not in ("clip", "layout", "refusal"):
                continue
            try:
                o = json.loads(body)
            except ValueError:
                continue
            if kind == "clip":
                clips[o["abs"]].append(o)
            elif kind == "layout" and o["frame"] not in layout:
                layout[o["frame"]] = one_copy(o["items"])
                ats[o["frame"]] = o.get("ats", [])
                wh = wh or (o.get("W", FRAME[0]), o.get("H", FRAME[1]))
            elif kind == "refusal":
                ref[o["frame"]] = o.get("msg", "")
    return clips, layout, ref, ats, wh


def code_times(v):
    """{code file: [(line, seconds)]} of the film's shot entries, as qa_devices reads each entry's anchor word: a code flag that names a
    place (CARD_REASON's file:line) is put on its shot's frames with them. {} when the code can't be read."""
    try:
        sys.path.insert(0, str(MOTION))
        import qa_devices
        code = qa_devices.Code(MOTION / "src" / v.src)
        shs = qa_devices.shots(code, qa_devices.video_words(v, code), getattr(v, "module", None))
    except Exception as e:  # noqa: BLE001   a reader that fails leaves the flag unplaced (listed apart), never the gate down
        say(f"  (the code's shot times not read: {e})")
        return {}
    by = defaultdict(list)
    for s in shs:
        if s.get("t") is not None:
            by[s["file"]].append((s["line"], s["t"]))
    return {f: sorted(x) for f, x in by.items()}


def place_code_flag(fl, times):
    """(at, to) for a flag the gate puts at frame 0 because it comes from the code or the words: CARD_REASON by its file:line (the shot
    entry at or above it), LIT_UNSAID by the second qa_lit names ("(12.3 s), heard:"); None when it has no place"""
    if fl["check"] == "CARD_REASON":
        m = re.match(r"(.+):(\d+)$", str(fl["key"]))
        rows = times.get(m.group(1), []) if m else []
        t = [s for ln, s in rows if ln <= int(m.group(2))] if m else []
        return (fr(t[-1]), fr(t[-1]) + 2 * FPS) if t else None
    if fl["check"] == "LIT_UNSAID":
        m = re.search(r"\((\d+(?:\.\d+)?) s\), heard:", fl["what"])
        return (fr(float(m.group(1))), fr(float(m.group(1))) + FPS) if m else None
    return None


def write_scope_report(v, out, scope, flags, ok, signed, stale, look, wide, frameless, notes):
    def line(fl, bold=True):
        to = f"-{mmss(fl['to'])}" if fl.get("to") else ""
        name = f"**{fl['check']}**" if bold else fl["check"]
        return f"- {name} {mmss(fl['at'])}{to} (frame {fl['at']}): {fl['what']}"
    lines = [f"# Gate scope {v.id} ({time.strftime('%Y-%m-%d %H:%M')}): {'clean' if not flags else f'{len(flags)} flag(s)'} in frames "
             + ", ".join(f"{a}-{b}" for a, b in scope), "",
             "The scoped gate: the gate's picture checks on these shots only. **Not a pass**: only the full gate (`pipe.py "
             f"{v.slug} gate`) stamps `passed.txt`, and it confirms before the render; no sound half, no coherency read here.", ""]
    lines += [f"- {n}" for n in notes] + [""]
    lines += [f"- STALE SIGN-OFF {s}" for s in stale]
    lines += [line(fl) for fl in flags]
    if look:
        lines += ["", "## To look at (not blocking: the eye's call)"] + [line(fl, False) for fl in look]
    if wide:
        lines += ["", "## The whole film's totals your shots add to (the full gate's call, not blocking here)"] + [line(fl, False) for fl in wide]
    if frameless:
        lines += ["", "## From the code with no place on the film (the whole film's: see whether one is yours)"] + [line(fl, False) for fl in frameless]
    if signed:
        lines += ["", "## Signed off by the creator ([[gate.signed]] in video.toml, its code unchanged)"]
        lines += [f"- {fl['check']} {mmss(fl['at'])}: {fl['what']} — {n}" for fl, n in signed]
    if ok:
        lines += ["", "## Allowed (gate_allow.json)"] + [f"- {fl['check']} {mmss(fl['at'])}: {fl['what']} — {al['reason']}" for fl, al in ok]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")


def step_scope(v, a):
    """`pipe.py <video> gate --scope a-b,c-d`: every picture check of the gate (B0-B23, the qa_* modules it calls) on the
    given frame ranges only, in minutes, for a builder's or fixer's own loop: run it on your own shots until it is clean, then hand back.

      1. The shots: the audit of the code as it is now; each range is widened to the whole shots it touches.
      2. The probe: those shots plus SCOPE_MARGIN frames each side, with their pictures (--png, for B1 STILL), under the Remotion ticket
         (heavy.py: one Remotion job at a time on this computer; it waits, never kills another job). Still holding the ticket, the last full
         probe (pipeline/gate/probe.jsonl) is read: the film's state is that probe with the probed frames replaced, in memory only.
      3. The checks: the per-frame and per-shot checks on the probed frames, the per-play checks on the plays that touch the scope, TWICE
         on the scope's plays against every play of the film, ART_CLOSE on the 20 s round the scope, CARD_CLOSE and B23 on the whole
         film's current code. A flag is the scope's when its frames meet a range (a pair flag, TWICE, CARD_CLOSE, ART_CLOSE: when one of
         its shots is in a range, wherever the flag sits); the gate's allows (gate_allow.json) and the creator's sign-offs apply as in the full gate.
         The whole film's totals (CARD_TIME, DEVICE_SPREAD; ART_SHARE needs the whole film's pictures and isn't read) are listed apart;
         CARD_REASON and LIT_UNSAID are placed on their shot by the code and the words.
      4. The report: <pipe dir>/gate_scope.md (or --out), a copy and flags.json in pipeline/gate/scope/<tag>/; exit 1 while a flag is left.
    It never writes the full gate's files (probe.jsonl, stamp.txt, probe_state.json, still/, gate.md, flags.json, analysis_cache.json,
    shots_<comp>.json) and never stamps passed.txt: the full gate before the render confirms, and a flag it finds is a miss of the loop."""
    import copy
    import pipe
    t_all = time.time()
    tm = {}
    bad = preflight(v)
    for b in bad:
        say(b)
    if bad:
        raise SystemExit("gate --scope: B0 failed")
    for opt in ("reprobe", "full", "reuse"):
        if getattr(a, opt, None):
            say(f"gate --scope: --{opt} is the full gate's and is not used here")
    d = v.pipe_dir / "gate"
    base_path = d / "probe.jsonl"
    ranges = parse_scope(a.scope)
    tag = "s" + hashlib.sha1(",".join(f"{x}-{y}" for x, y in ranges).encode()).hexdigest()[:8]
    sd = d / "scope" / tag
    gd = sd / "gate"
    # a fresh folder for this run; the scope's own analysis cache stays (the per-play reads of its new clips)
    keep = None
    if (gd / "analysis_cache.json").exists():
        keep = (gd / "analysis_cache.json").read_bytes()
    if sd.exists():
        shutil.rmtree(sd)
    gd.mkdir(parents=True)
    if keep is not None:
        (gd / "analysis_cache.json").write_bytes(keep)
    vs = copy.copy(v)
    vs.pipe_dir = sd   # every file a check reads from "the video's pipeline" is the scope's own (shots_<comp>.json, gate/probe.jsonl)
    say(f"gate scope {v.id}: {', '.join(f'{x}-{y}' for x, y in ranges)} -> {sd}")

    # 1. the shots, and the ranges widened to them
    t0 = time.time()
    if v.kind != "short":
        build = f"scope_{tag}"
        try:
            rep = pipe.audit_report(vs, tag="shots", build=build)
        finally:
            for ext in ("tsx", "cjs"):
                (MOTION / "out" / f"audit_{v.comp}_{build}.{ext}").unlink(missing_ok=True)
        shots = rep["shots"]
        total = fr(rep["seconds"]) if rep.get("seconds") else v.frames()
    else:
        # a built Short's shots are its <At> ranges, from the probe: the last full probe's for the widening (a Short's is small)
        total = v.frames()
        pre = LastProbe(base_path)
        pre.load(pre.idx)
        pre.drop()
        AT_STARTS.clear()
        for x in pre.ats.values():
            AT_STARTS.update(x)
        shots = shots_from_probe(pre.layout, pre.clips) if pre.layout else []
    scope = widen_to_shots(ranges, shots, total)
    in_scope = [s for s in shots if overlaps(fr(s["at"]), fr(s["end"]) - 1, scope)]
    spans = merge_spans([(max(0, x - SCOPE_MARGIN), min(total - 1, y + SCOPE_MARGIN)) for x, y in scope], SCOPE_JOIN)
    n_probe = sum(y - x + 1 for x, y in spans)
    say(f"scope: {', '.join(f'{x}-{y}' for x, y in scope)} ({len(in_scope)} shots, {sum(y - x + 1 for x, y in scope) / FPS:.1f} s); "
        f"probed with the margins: {', '.join(f'{x}-{y}' for x, y in spans)} ({n_probe} frames)")
    fx = effects_from_cues(v)
    logs = sorted(v.pipe_dir.glob("score_v*.log"), key=lambda p: p.stat().st_mtime)
    effects = effects_from_log(fx if fx is not None else (logs[-1] if logs else None))
    tm["setup"] = time.time() - t0

    # 2. the probe, then (still holding the ticket) the last full probe
    lst = gd / "ranges.txt"
    lst.write_text(",".join(f"{x}-{y}" for x, y in spans), encoding="utf-8")
    t0 = time.time()
    inside = lambda f: any(x <= f <= y for x, y in spans)  # noqa: E731
    with RemotionJob(f"gate scope {v.id} ({n_probe} frames)", getattr(a, "wait", None)):
        tm["wait"] = time.time() - t0
        t1 = time.time()
        r = pipe.run_watched([NODE, "gate_probe.mjs", gd, "0.25", f"@{lst}", "1", "--png"], MOTION,
                             {"QA_COMP": v.comp, "QA_PUBLIC": v.pub.as_posix(), **temp_env()}, gd / "probe.log", stall=300)
        tm["probe"] = time.time() - t1
        ok_probe = r.returncode == 0 and not getattr(r, "stalled", False)
        if ok_probe:
            t1 = time.time()
            f_clips, f_lay, f_ref, f_ats, wh = read_scope_probe(gd / "probe.jsonl")
            last = LastProbe(base_path)
            clips = defaultdict(list)
            for f, cs in last.clips.items():
                if not inside(f):
                    clips[f] = cs
            for f, cs in f_clips.items():
                clips[f] = cs
            plays = group_plays(clips)
            scope_plays = [p for p in plays if overlaps(p["f0"], p["f1"], scope)]
            # the last probe's pictures the checks look at outside the probed frames: each play's middle (TWICE: a blurred ground isn't a
            # showing), the scope's plays' ends (HOLD, DISSOLVE: a hidden ground), the 20 s round the scope (ART_CLOSE); a Short's all
            need = {(p["f0"] + p["f1"]) // 2 for p in plays} | {p[k] for p in scope_plays for k in ("f0", "f1")}
            for x, y in scope:
                need |= set(range(max(0, x - SCOPE_CLOSE), min(total, y + SCOPE_CLOSE + 1)))
            if v.kind == "short":
                need |= set(last.idx)
            last.load(f for f in need if not inside(f))
            last.drop()
            tm["read"] = time.time() - t1
    if not ok_probe:
        raise SystemExit(f"gate --scope: the probe failed{' (stalled)' if getattr(r, 'stalled', False) else ''}: {gd / 'probe.log'}")
    lost = [f"{x}-{y}" for x, y in spans if not any(x <= f <= y for f in f_lay)]
    if lost:
        raise SystemExit(f"gate --scope: the probe wrote nothing for {', '.join(lost)}: {gd / 'probe.log'}")
    short_of = sum(1 for x, y in spans for f in range(x, y + 1) if f not in f_lay)
    still_dir = gd / "still"
    still_dir.mkdir(exist_ok=True)
    for p_ in gd.glob("element-*.jp*g"):   # the probe's own pictures of every frame (graphics only): B1 STILL draws nothing more
        os.replace(p_, still_dir / p_.name)
    if wh:
        FRAME[0], FRAME[1] = wh
    REFUSALS.clear()
    REFUSALS.update(f_ref)
    AT_STARTS.clear()
    for f, x in list(f_ats.items()) + [(f, x) for f, x in last.ats.items() if not inside(f)]:
        AT_STARTS.update(x)
    lay = {f: f_lay[f] for f in sorted(f_lay)}                       # the probed frames: every per-frame and per-shot check runs here
    lay_key = {**last.layout, **lay}                                  # .get() only: hidden grounds, TWICE's showings
    if v.kind == "short":
        lay_all = {f: (lay.get(f) if inside(f) else last.layout.get(f)) for f in sorted(set(lay) | set(last.layout))}
        shots = shots_from_probe({f: x for f, x in lay_all.items() if x is not None}, clips)
        in_scope = [s for s in shots if overlaps(fr(s["at"]), fr(s["end"]) - 1, scope)]
    win_shots = [s for s in shots if any(x <= fr(s["at"]) and fr(s["end"]) - 1 <= y for x, y in spans)]
    near_shots = [s for s in shots if overlaps(fr(s["at"]), fr(s["end"]) - 1, spans)]
    clips_win = {f: clips[f] for f in lay if f in clips}
    notes = [f"scope {', '.join(f'{x}-{y}' for x, y in scope)} ({len(in_scope)} shots; your ranges {', '.join(f'{x}-{y}' for x, y in ranges)} "
             f"widened to their whole shots), probed fresh with {SCOPE_MARGIN} frames each side: {n_probe} frames"
             + (f" ({short_of} without a layout line)" if short_of else ""),
             f"the rest of the film: the last full probe ({base_path}, {time.strftime('%Y-%m-%d %H:%M', time.localtime(base_path.stat().st_mtime))}, "
             f"{last.frames} frames)" if last.idx else "no full probe yet: TWICE and the 20-s rule see the scope alone"]
    if last.idx and last.frames != total:
        notes.append(f"the last full probe has {last.frames} frames, the composition {total}: the timing moved since, so outside the probed "
                     f"frames the film's state is the old timing (TWICE's other showing may sit a little off; the scope itself is new)")
    say(f"probe: {n_probe} frames in {tm['probe']:.0f} s; {len(plays)} plays in the film, {len(scope_plays)} touch the scope; "
        f"{len(effects)} effects")

    # 3. the checks
    t0 = time.time()
    full_cache = {}   # the full gate's answers, read only and in one go (read_at_once); the scope saves its own beside them
    try:
        full_cache = json.loads(read_at_once(d / "analysis_cache.json").decode("utf-8"))
    except (OSError, ValueError):
        pass
    cache_open(gd / "analysis_cache.json")
    CACHE["data"] = {**full_cache, **CACHE["data"]}
    durs = json.loads((MOTION / "src/clipdurs.json").read_text(encoding="utf-8"))
    G = v.section("gate") if hasattr(v, "section") else {}
    clips_json = G.get("clips_json")
    pub = v.pub
    scope_fx = [e for e in effects if overlaps(round(e[0] * FPS), round(e[0] * FPS), scope)]
    found, play_flags, pair_flags, code_flags, wide = [], [], [], [], []
    say("checks (each line counts what it found on the probed frames, margins included; the scope's own are picked after):")

    def step(name, fn, into, soft=False):
        t_ = time.time()
        h0, m0 = CACHE["hits"], CACHE["miss"]
        try:
            got = fn()
        except Exception as e:  # noqa: BLE001
            if not soft:
                say(f"  {name}: CRASHED ({type(e).__name__}: {e})")
                into.append(crashed_flag(name, e))
                return []
            # as in the full gate (B17, B19-B23): a check that can't read says why and never takes the run down; the report says it too
            say(f"  {name}: not read ({type(e).__name__}: {e})")
            notes.append(f"{name}: NOT READ ({type(e).__name__}: {e}): its flags are unknown here")
            return []
        hm = f"; {CACHE['hits'] - h0} from the cache, {CACHE['miss'] - m0} measured" if CACHE["hits"] + CACHE["miss"] > h0 + m0 else ""
        say(f"  {name}: {len(got)} ({time.time() - t_:.0f} s{hm})")
        into += got
        return got

    def stills():
        out = []
        for x, y in spans:   # one stretch at a time: check_still reads its frames as one run
            out += check_still(vs, {f: lay[f] for f in range(x, y + 1) if f in lay}, gd, clips_win)
        return out

    sys.path.insert(0, str(MOTION))
    step("B1 freezes", lambda: check_freezes(scope_plays, durs), play_flags)
    step("B1 holds", lambda: check_holds(scope_plays, pub, durs, lay_key), play_flags)
    step("B2 flashes", lambda: check_flashes(scope_plays, pub, durs), play_flags)
    step("B2 fades", lambda: check_fades(scope_plays, pub, lay_key), play_flags)
    step("B3 gaps", lambda: check_gaps(clips, win_shots), found)
    step("B3 blank", lambda: check_blank(lay), found)
    step("B3 blank long", lambda: check_blank_long(lay), found)
    step("B4 layout", lambda: check_layout(lay), found)
    step("B4 overlap", lambda: check_overlap(lay, pub), found)
    step("B5 motion", lambda: check_motion(lay, win_shots, effects), found)
    step("B6 sync", lambda: check_sync(lay, clips, near_shots, scope_fx, pub), found)
    step("B7 reuse", lambda: check_reuse(scope_plays, clips_json), play_flags)
    step("B8 cut-outs", lambda: check_cutouts(lay, pub), found)
    step("B12 marks", lambda: check_marks(lay, clips_win), found)
    step("B13 text overlap", lambda: check_text_overlap(lay), found)
    step("B14 row centre", lambda: check_row_centre(lay, pub), found)
    step("B15 kit3 refusals", check_refusals, found)
    step("B24 text hold", lambda: check_text_hold(lay), found)
    step("B25 mark zoom", lambda: check_mark_zoom(lay), found)
    cache_save()
    step("B1 stills", stills, found)

    def marks_target():
        import qa_marks
        return [f for f in qa_marks.check_marks_target(v.pub, lay, clips_win, out=gd / "marks") if f["check"] in ("MARK_OFF", "MARK_REDUNDANT")]
    step("B16 marks on target", marks_target, found)

    def lit():
        import qa_lit
        _, xs = qa_lit.check(v.src_dir)
        return [{"check": "LIT_UNSAID", "key": x[:80], "at": 0, "look": True, "what": x} for x in xs]
    step("B17 lights against their words", lit, code_flags, soft=True)
    step("B9 credits", lambda: check_credits(lay, clip_sources(v)), found)
    step("B7 twice (the scope's plays against the film's)", lambda: check_twice(plays, lay_key, clip_spans(v), scope=scope), pair_flags)
    step("B4 letterbox/aspect", lambda: (check_letterbox(lay, pub) if v.kind == "short"
                                         else check_letterbox_cut(lay, pub, clip_sources(v))) + check_aspect(lay, pub) + check_upscale(lay, pub), found)
    step("B4 empty", lambda: check_empty(lay), found)
    if v.kind == "short" and os.environ.get("GATE_B11") == "1":
        step("B11 pan", lambda: check_pan(lay), found)
    if v.kind == "short":
        step("B10 caption twice", lambda: check_caption_twice(v, lay), found)
    if v.kind == "long":
        mine_shot = lambda a_, e_: overlaps(fr(a_), fr(e_) - 1, scope)  # noqa: E731   a shot (seconds) in the scope

        def cards():
            import qa_cards
            got = qa_cards.gate_flags(vs)   # the whole film's shots in the code as it is now (the scope's own shots_<comp>.json)
            cs, _ = qa_cards.film_cards(sd / f"shots_{v.comp}.json")
            pairs = {f"{c1[0]:.2f}": (c0, c1) for c0, c1 in zip(cs, cs[1:])}   # CARD_CLOSE's key: the second card's start
            for fl in got:
                if fl["check"] == "CARD_CLOSE":
                    pr = pairs.get(fl["key"])
                    if pr and (mine_shot(*pr[0][:2]) or mine_shot(*pr[1][:2])):
                        pair_flags.append(fl)
                elif fl["check"] == "CARD_TIME":
                    if any(mine_shot(*c[:2]) for c in cs):
                        wide.append(fl)
                else:
                    code_flags.append(fl)   # CARD_REASON: a code place, put on its shot below
            return got
        step("B19 cards", cards, [], soft=True)
        step("B20 still/marks vs words", lambda: __import__("qa_still_words").gate_flags(vs, lay, clips_win), found, soft=True)
        step("B21 centred logos and icons", lambda: __import__("qa_centred").gate_flags(vs, lay, clips_win), found, soft=True)
        import inspect
        import qa_shots
        kinds = tuple(k for k in inspect.signature(qa_shots.run).parameters["only"].default if k != "art")
        step(f"B22 {', '.join(kinds)}", lambda: qa_shots.run(vs, lay, clips_win, only=kinds), found, soft=True)

        def art():
            # artwork on the 20 s round the scope: the per-picture artwork checks on their own frames, ART_CLOSE when one of its three
            # shots is in the scope
            out, dump = [], {}
            for x, y in merge_spans([(max(0, x - SCOPE_CLOSE), min(total - 1, y + SCOPE_CLOSE)) for x, y in scope]):
                la = {f: lay_key[f] for f in range(x, y + 1) if f in lay_key}
                dump.clear()
                got = qa_shots.run(vs, la, {f: clips[f] for f in la if f in clips}, only=("art",), dump=dump)
                arts = dump.get("art", [])
                for fl in got:
                    if fl["check"] == "ART_CLOSE":
                        i = next((k for k, x_ in enumerate(arts) if x_["at"] == fl["at"] and x_["name"] == fl["key"]), None)
                        if i is not None and any(overlaps(x_["at"], x_["to"], scope) for x_ in arts[max(0, i - 2):i + 1]):
                            pair_flags.append(fl)
                    elif fl["check"] != "ART_SHARE":   # a share of the whole film: not measurable on a part (the note below)
                        out.append(fl)
            return out
        step("B22 artwork", art, found, soft=True)
        notes.append("ART_SHARE (artwork's share of the whole film) is not read here: a part can't measure it, the full gate does")
        def devices():
            import qa_devices
            got = qa_devices.gate_flags(v)   # from the whole film's code
            for fl in got:
                if fl["check"] in FILM_WIDE:
                    if overlaps(fl["at"], fl.get("to") or fl["at"], scope):
                        wide.append(fl)
                elif not fl["at"]:
                    code_flags.append(fl)   # a stamp in no shot: no place on the film
                else:
                    found.append(fl)
            return got
        step("B23 devices and round crops", devices, [], soft=True)
    cache_save()
    tm["checks"] = time.time() - t0

    # the scope's flags: found on its frames, a play or a pair of it, the code's placed on their shot
    t0 = time.time()
    times = code_times(v) if any(fl["check"] == "CARD_REASON" for fl in code_flags) else {}
    frameless = []
    for fl in code_flags:
        pl = place_code_flag(fl, times)
        if pl:
            fl["at"], fl["to"] = pl
            found.append(fl)
        else:
            frameless.append(fl)
    mine = [fl for fl in found + play_flags if overlaps(fl["at"], fl.get("to") or fl["at"], scope)
            or (not fl["at"] and fl.get("look"))]   # a window check's by-file note with no frame (a picture file not found)
    once = {}   # one flag once (a kit3d artwork is read in each 20-s window round the scope)
    for fl in sorted(mine + pair_flags, key=lambda x: x["at"]):
        once.setdefault((fl["check"], str(fl["key"]), fl["at"]), fl)
    mine = list(once.values())
    look = [fl for fl in mine if fl.get("look")]
    flags = [fl for fl in mine if not fl.get("look")]
    flags, signed, stale = signed_off(v, flags)
    flags, ok = allowed(v, flags)
    wide, _ = allowed(v, wide)
    frameless_block = [fl for fl in frameless if not fl.get("look")]
    frameless_block, _ = allowed(v, frameless_block)
    frameless = frameless_block + [fl for fl in frameless if fl.get("look")]
    out = Path(a.out) if getattr(a, "out", None) else v.pipe_dir / "gate_scope.md"
    # (no code stamp: nothing is stamped here, and hashing the code costs 5-12 s on a long film)
    notes.insert(0, f"allowed in gate_allow.json: {len(ok)}; signed off by the creator: {len(signed)}")
    tm["report"] = time.time() - t0
    tm["all"] = time.time() - t_all
    notes.append("time: " + ", ".join(f"{k} {tm[k]:.0f} s" for k in ("setup", "wait", "probe", "read", "checks", "report") if k in tm)
                 + f"; {tm['all'] / 60:.1f} min in all")
    write_scope_report(v, out, scope, flags, ok, signed, stale, look, wide, frameless, notes)
    if out != sd / "gate_scope.md":
        shutil.copyfile(out, sd / "gate_scope.md")
    (sd / "flags.json").write_text(json.dumps({"scope": scope, "ranges": ranges, "flags": flags, "look": look, "wide": wide,
                                               "frameless": frameless, "allowed": [f for f, _ in ok], "time": tm}, indent=1), encoding="utf-8")
    # the probe's pictures matter only to look at a STILL: those frames' are kept, the rest go (3812 frames hold ~74 MB)
    held = [(fl["at"], fl.get("to") or fl["at"]) for fl in flags + look if fl["check"] in ("STILL", "STILL_SOURCE")]
    for p_ in still_dir.glob("element-*.jp*g"):
        m_ = re.search(r"(\d+)\.jpe?g$", p_.name)
        if not (m_ and overlaps(int(m_.group(1)), int(m_.group(1)), held)):
            p_.unlink()
    for fl in flags:
        to = f"-{mmss(fl['to'])}" if fl.get("to") else ""
        say(f"  {fl['check']} {mmss(fl['at'])}{to} (frame {fl['at']}): {fl['what'][:220]}")
    say(f"gate scope: {'CLEAN' if not flags else f'{len(flags)} flag(s)'} in {', '.join(f'{x}-{y}' for x, y in scope)} ({len(ok)} allowed, "
        f"{len(look)} to look at, {len(wide)} film-wide, {len(frameless)} with no place) -> {out}; {tm['all'] / 60:.1f} min "
        f"(probe {tm['probe']:.0f} s, checks {tm['checks']:.0f} s). Not a pass: the full gate confirms before the render")
    if flags:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--probe-dir", required=True)
    ap.add_argument("--shots", help="a shots json (the audit's report) [the video's own]")
    ap.add_argument("--durs", help="a clipdurs.json [src/clipdurs.json]")
    ap.add_argument("--clips", help="the public dir the clips are read from [the video's]")
    ap.add_argument("--score-log", help="score.py's report for the effects [the newest score_v*.log]")
    ap.add_argument("--clips-json", help="the clips manifest (name -> source) for B7")
    ap.add_argument("--out", help="the report [<probe-dir>/gate.md]")
    a = ap.parse_args()
    v = Video(find_video(a.video))
    import pipe
    shots = json.loads(Path(a.shots).read_text(encoding="utf-8"))["shots"] if a.shots else pipe.audit_report(v, tag="shots")["shots"]
    durs = json.loads(Path(a.durs or MOTION / "src/clipdurs.json").read_text(encoding="utf-8"))
    logs = sorted(v.pipe_dir.glob("score_v*.log"), key=lambda p: p.stat().st_mtime)
    cache_open(Path(a.probe_dir) / "analysis_cache.json")
    flags, _ = analyse(v, Path(a.probe_dir) / "probe.jsonl", shots, durs, Path(a.clips) if a.clips else v.pub,
                       a.score_log or (logs[-1] if logs else None), a.clips_json)
    look = [f for f in flags if f.get("look")]
    flags = [f for f in flags if not f.get("look")]
    flags, signed, stale = signed_off(v, flags)
    flags, ok = allowed(v, flags)
    out = Path(a.out) if a.out else Path(a.probe_dir) / "gate.md"
    write_report(v, flags, ok, out, "analysis only", signed, stale, "", look)
    (Path(a.probe_dir) / "flags.json").write_text(json.dumps(flags, indent=1), encoding="utf-8")
    say(f"{len(flags)} flag(s) -> {out}")


if __name__ == "__main__":
    main()
