"""qa_centred.py: what is meant to sit on a point, measured where the viewer sees it.

  LOGO_OFF_CENTRE  a lone logo or hero object meant to be centred whose VISUAL centre sits more than LOGO_TOL px (on the 1920 frame) off
                   its point, left to right. The visual centre is halfway between the box of its visible pixels and their centre of mass
                   (a logo centred by its box alone reads as leaning to its heavy side):
                   - 2D: a cut-out picture (a logo, an object: its file has transparency) alone at its height (no other picture or text
                     beside it; full-frame grounds don't count), placed to be centred (its box's centre within NEAR of the frame's), at
                     least MIN_W wide; its file read for its alpha (alpha > 16, the kit's rule) and mapped onto its box on screen. Judged
                     on the run's settled frames (opacity 0.9+), the median. Photos, pages and covers (no transparency) are what their box
                     shows, and a page panned to its quote sits off centre by design: not this check's.
                   - 3D: kit3d's own measure. A 3D canvas is an empty box to the probe, so Emblem3D, Phone3D and CaseNumber3D log
                     `kit3d|{frame, kind, mode, box, centroid, visual, target}` on every frame in the gate mode (src/kit3d/centre.ts;
                     `visual` is the piece's point: the eye's for one object, the content box's for CaseNumber3D's group); a piece it
                     can't centre refuses itself (the gate's B15 KIT3_REFUSAL).
  ICON_FACE_OFF    a round profile icon (kit3 Still's `icons`, data-gate="icon"; or a small square picture named *pfp*, *icon* or *avatar*)
                   whose face, found with YuNet ON THE ICON'S OWN FILE (make_icon.py check), sits more than 4% of the circle off its
                   centre, fills outside 42-72% of its height, or isn't found.
  ICON_NOT_REAL    an icon with no sidecar (make_icon.py's <name>.icon.json: cut from a frame of the source's own footage, its face
                   measured) or cut from artwork: an icon shows the real person, as the footage does.

How it sees: the gate's probe (gate_probe.mjs: every frame's pictures with their real boxes after every zoom) and the files themselves,
so it runs on the code before any render. A flag is fixed, or allowed in videos/<video>/gate_allow.json ({"check", "key", "reason"};
the key is the picture's file name) with the reason that proves it.
The creator's own avatar files (a logo on the subscribe ask, no face to centre) are listed in data/house_avatars.json.

  gate.py (B21) calls:  cd += qa_centred.gate_flags(v, lay, _cl)
  PIPE tools/motion/qa_centred.py <video> [--probe <probe.jsonl>] [--kit3d <lines.jsonl>] [--range a-b] [--pub <dir> ...] [--json <out>]
        exit 1 on a flag not allowed
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import PUBLIC, PY_EDIT, TOOLS  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "pipeline"))

FPS = 60
PY_ED = str(PY_EDIT)
MOTION_PUB = PUBLIC
LOGO_TOL = 12.0         # px on the 1920 frame: a hero 25 px off reads as off centre to the eye; 12 and under reads centred
NEAR = 0.12             # a picture whose box's centre sits within 12% of the width of the frame's centre was placed to be centred
MIN_W = 60.0            # px: smaller pictures (bullets, chips) aren't heroes
SETTLED = 0.9           # opacity from which a frame of a picture counts (its entrance is over)
LOCKUP_ASPECT = 2.5     # a wider cut-out is a lockup (an icon beside a wordmark, 4:1 and wider): flagged to LOOK at, not blocking, since
#                         whether a wordmark's weight reads off centre is not measured
FULL = 0.9              # a picture covering 90%+ of the width or the height is a ground, not a thing on it
ICON_RE = re.compile(r"(^|[_/.-])(pfp|icon|avatar)([_.-]|$)", re.I)
SKIP_G = {"credit", "name", "mark", "roll"}


def _house_avatars():
    """the creator's own avatar files (data/house_avatars.json, a list of file names): a logo, no face to centre"""
    try:
        return set(json.loads((HERE / "data" / "house_avatars.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


HOUSE_AVATARS = _house_avatars()


# ============================================================================================================================ pictures
def public_file(t, pubs):
    for p in pubs:
        f = Path(p) / t
        if f.exists():
            return f
    return None


@lru_cache(maxsize=512)
def alpha_stats(path):
    """(iw, ih, x0, x1, wx, cutout) of a picture file in its own px: the visible pixels' box left to right (alpha > 16), their centre of
    mass (alpha-weighted), and whether it is a cut-out (a logo, an object: 2%+ of it transparent). A picture without alpha is all visible
    and no cut-out: a photo, a page, a cover, whose box is what you see (a page panned to its quote sits off centre by design)"""
    im = Image.open(path)
    iw, ih = im.size
    k = min(1.0, 1024 / max(iw, ih))
    if k < 1:
        im = im.resize((max(1, round(iw * k)), max(1, round(ih * k))), Image.BILINEAR)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        a = np.asarray(im.convert("RGBA").getchannel("A"), dtype=np.float64)
    else:
        a = np.full((im.size[1], im.size[0]), 255.0)
    cutout = bool((a < 250).mean() > 0.02)
    m = a > 16
    if not m.any():
        return iw, ih, 0.0, float(iw), iw / 2, cutout, 0.0, float(ih)
    cols = np.nonzero(m.any(axis=0))[0]
    rws = np.nonzero(m.any(axis=1))[0]
    wa = np.where(m, a, 0.0).sum(axis=0)
    wx = float((wa * (np.arange(len(wa)) + 0.5)).sum() / wa.sum())
    return iw, ih, cols[0] / k, (cols[-1] + 1) / k, wx / k, cutout, rws[0] / k, (rws[-1] + 1) / k


def visual_x(it, st):
    """the picture's visual centre left to right on screen, its box's centre, and its weight's: film px"""
    iw, ih, x0, x1, wx = st[:5]
    s = it["w"] / iw
    box = it["x"] + (x0 + x1) / 2 * s
    weight = it["x"] + wx * s
    return (box + weight) / 2, box, weight


def overlap_y(a, b):
    lo, hi = max(a["y"], b["y"]), min(a["y"] + a["h"], b["y"] + b["h"])
    return max(0.0, hi - lo) / max(1.0, min(a["h"], b["h"]))


def near_centre(items, W, H):
    """the pictures placed near the frame's centre on this frame, each with whether it stands alone at its height: [(item, lone)]"""
    pics = [(i, it) for i, it in enumerate(items) if it["k"] in ("img", "clip") and it["op"] >= 0.3 and it.get("g") not in SKIP_G
            and it["w"] < FULL * W and it["h"] < FULL * H]
    texts = [it for it in items if it["k"] == "text" and it["op"] >= 0.3 and it.get("g") not in ("credit",) and it.get("fs", 0) >= 24]
    out = []
    for i, it in pics:
        if it["k"] != "img" or it.get("g") == "icon" or ICON_RE.search(Path(str(it["t"])).name) or it["w"] < MIN_W:
            continue
        if abs(it["x"] + it["w"] / 2 - W / 2) > NEAR * W:
            continue
        side = [o for j, o in pics if j != i and o["w"] >= MIN_W and overlap_y(it, o) > 0.3 and not (o["x"] <= it["x"] and o["x"] + o["w"] >= it["x"] + it["w"])
                and not (it["x"] <= o["x"] and it["x"] + it["w"] >= o["x"] + o["w"])]
        side += [o for o in texts if overlap_y(it, o) > 0.3 and (o["x"] + o["w"] <= it["x"] + 4 or o["x"] >= it["x"] + it["w"] - 4)]
        # beside something at its height: a row or a group (B14, the group's own centring), not a lone thing
        out.append((it, not side))
    return out


def runs_of(frames):
    """consecutive frames (gaps up to 2) as (first, last)"""
    out = []
    for f in sorted(frames):
        if out and f - out[-1][1] <= 2:
            out[-1][1] = f
        else:
            out.append([f, f])
    return [(a, b) for a, b in out]


def logos_on_frame(f, items, W, H, pubs, seen, missing):
    """one frame's centred cut-outs into `seen` {name: {frame: (visual, box, weight, width, lone, x, aspect)}} (offsets from the centre in
    1920-frame px); a picture alone now that is joined at the same place later in its run is a row being built, not a lone thing"""
    for it, lone in near_centre(items, W, H):
        if it["op"] < SETTLED:
            continue
        t = str(it["t"])
        p = public_file(t, pubs)
        if p is None:
            if lone:
                missing.add(t)
            continue
        st = alpha_stats(str(p))
        if not st[5]:
            continue   # no transparency: a photo, a page or a cover (its box is what you see)
        vx, bx, wx = visual_x(it, st)
        k = 1920 / W   # the tolerance is in px of a 1920-wide frame (a Short's 1080: scaled)
        aspect = (st[3] - st[2]) / max(1.0, st[7] - st[6])   # the visible content's width : height
        seen[t][f] = ((vx - W / 2) * k, (bx - W / 2) * k, (wx - W / 2) * k, it["w"] * k, lone, it["x"], aspect)


def check_logos(layout, W, H, pubs, seen=None, missing=None):
    if seen is None:
        seen, missing = defaultdict(dict), set()
        for f in sorted(layout):
            logos_on_frame(f, layout[f], W, H, pubs, seen, missing)
    flags, rows = [], []
    for t, fr in seen.items():
        for a, b in runs_of(fr):
            vals = [fr[f] for f in range(a, b + 1) if f in fr]
            lone = [v for v in vals if v[4]]
            if not lone:
                continue
            # alone now, joined at the same place later in its run (or before): a row being built (one logo, then the next beside it)
            xs = [v[5] for v in lone]
            if any(not v[4] and min(abs(v[5] - x) for x in xs) <= 3 for v in vals):
                continue
            mid = len(lone) // 2
            med = sorted(v[0] for v in lone)[mid]
            box = sorted(v[1] for v in lone)[mid]
            wgt = sorted(v[2] for v in lone)[mid]
            w = sorted(v[3] for v in lone)[mid]
            aspect = sorted(v[6] for v in lone)[mid]
            row = {"name": t, "at": a, "to": b, "visual": round(med, 1), "box": round(box, 1), "weight": round(wgt, 1), "w": round(w),
                   "aspect": round(aspect, 2)}
            rows.append(row)
            if abs(med) > LOGO_TOL:
                wide = aspect > LOCKUP_ASPECT
                flags.append({"check": "LOGO_OFF_CENTRE", "key": Path(t).name, "at": a, "to": b, **({"look": True} if wide else {}),
                              "what": f"{Path(t).name} ({w:.0f} px wide) sits {med:+.1f} px off the centre to the eye (its box {box:+.1f}, "
                                      f"its weight {wgt:+.1f}; over {LOGO_TOL:.0f}); centre it on its visual centre "
                                      "(kit3 Row/LogosLand do for a lone figure; or move it by the difference)"
                                      + (f". A wide lockup ({aspect:.1f}:1, icon + wordmark): to look at, whether its weight reads off "
                                         "centre is not measured" if wide else "")})
    for t in sorted(missing):
        flags.append({"check": "LOGO_OFF_CENTRE", "key": Path(t).name, "at": 0, "look": True,
                      "what": f"{t}: a lone centred picture whose file isn't in the public dirs ({', '.join(map(str, pubs))}): not measured"})
    return flags, rows


# ================================================================================================================================ 3D
def kit3d_lines(path, rng=None):
    out = []
    if not path or not Path(path).exists():
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("kit3d|"):
                continue
            try:
                o = json.loads(line.partition("|")[2])
            except ValueError:
                continue
            if not isinstance(o.get("frame"), int) or "visual" not in o:
                continue
            if rng and not rng[0] <= o["frame"] <= rng[1]:
                continue
            out.append(o)
    return out


def check_kit3d(lines):
    by = defaultdict(dict)
    for o in lines:
        by[(o.get("kind"), o.get("what"))][o["frame"]] = o
    flags, rows = [], []
    for (kind, what), fr in by.items():
        for a, b in runs_of(fr):
            off = [(fr[f]["visual"][0] - fr[f]["target"][0], fr[f]) for f in range(a, b + 1) if f in fr]
            worst = max(off, key=lambda x: abs(x[0]))
            # the move's end on: the frames from the run's last third (a 3D logo at rest), and the worst frame of the whole run
            rest = sorted(o for o, _ in off[len(off) * 2 // 3:])
            med = rest[len(rest) // 2] if rest else worst[0]
            o = worst[1]
            box = (o["box"][0] + o["box"][2]) / 2 - o["target"][0]
            wgt = o["centroid"][0] - o["target"][0]
            row = {"name": f"{kind} {what}", "at": a, "to": b, "visual_rest": round(med, 1), "worst": round(worst[0], 1), "box": round(box, 1),
                   "weight": round(wgt, 1)}
            rows.append(row)
            bad = [f for f in range(a, b + 1) if f in fr and abs(fr[f]["visual"][0] - fr[f]["target"][0]) > LOGO_TOL]
            if bad:
                flags.append({"check": "LOGO_OFF_CENTRE", "key": Path(str(what)).name, "at": bad[0], "to": bad[-1],
                              "what": f"{kind} {Path(str(what)).name}: its visual centre {med:+.1f} px off its point at rest (worst {worst[0]:+.1f}; "
                                      f"its box {box:+.1f}, its weight {wgt:+.1f}) on {len(bad)} frames (over {LOGO_TOL:.0f})"})
    return flags, rows


# =============================================================================================================================== icons
def icon_items(items, W, H):
    out = []
    for it in items:
        if it["k"] != "img" or it["op"] < 0.3:
            continue
        name = Path(str(it["t"])).name
        square = abs(it["w"] - it["h"]) <= 0.04 * max(it["w"], it["h"]) and it["w"] <= 0.3 * H
        if it.get("g") == "icon" or (square and ICON_RE.search(name) and name not in HOUSE_AVATARS):
            out.append(it)
    return out


def check_icons(layout, W, H, pubs, shows=None):
    if shows is None:
        shows = defaultdict(list)
        for f in sorted(layout):
            for it in icon_items(layout[f], W, H):
                shows[str(it["t"])].append(f)
    if not shows:
        return [], []
    files = {t: public_file(t, pubs) for t in shows}
    have = [str(p) for p in files.values() if p is not None]
    verdicts = {}
    if have:
        r = subprocess.run([PY_ED, str(HERE / "make_icon.py"), "check", "--json", *have], capture_output=True, text=True, errors="replace")
        try:
            for v in json.loads(r.stdout.strip().splitlines()[-1]):
                verdicts[str(Path(v["path"]))] = v
        except (ValueError, IndexError):
            raise RuntimeError(f"make_icon.py check: {r.stderr[-400:]}")
    flags, rows = [], []
    for t, frs in shows.items():
        p = files[t]
        a, b = min(frs), max(frs)
        if p is None:
            flags.append({"check": "ICON_NOT_REAL", "key": Path(t).name, "at": a, "to": b, "what": f"{t}: the icon's file isn't in the public dirs"})
            continue
        v = verdicts.get(str(Path(p)), {"bad": ["not read"], "face": None})
        m = v.get("face")
        rows.append({"name": t, "at": a, "to": b, "face": m, "source": v.get("source"), "bad": v["bad"]})
        face_bad = [x for x in v["bad"] if "face" in x]
        src_bad = [x for x in v["bad"] if "face" not in x]
        if face_bad:
            flags.append({"check": "ICON_FACE_OFF", "key": Path(t).name, "at": a, "to": b,
                          "what": f"{Path(t).name}: " + "; ".join(face_bad) + " (the face measured and centred: make_icon.py make)"})
        if src_bad:
            flags.append({"check": "ICON_NOT_REAL", "key": Path(t).name, "at": a, "to": b, "what": f"{Path(t).name}: " + "; ".join(src_bad)})
    return flags, rows


# ================================================================================================================================ the gate
def frame_size(layout):
    try:
        import gate
        return gate.FRAME[0], gate.FRAME[1]
    except Exception:  # noqa: BLE001
        return 1920, 1080


def pubs_of(v):
    out = []
    for p in (getattr(v, "pub", None), MOTION_PUB):
        if p and Path(p).exists() and Path(p) not in out:
            out.append(Path(p))
    return out


def gate_flags(v, layout=None, clips=None):
    """LOGO_OFF_CENTRE, ICON_FACE_OFF, ICON_NOT_REAL for gate.py, on the probe the gate already loaded (gate.load_probe's layout
    {frame: items}; `clips` unused) plus the probe file's kit3d lines. The gate's allows and sign-offs apply to these flags like to its own."""
    probe = v.pipe_dir / "gate" / "probe.jsonl"
    if layout is None:
        layout, W, H = load(str(probe))
    else:
        W, H = frame_size(layout)
    pubs = pubs_of(v)
    lf, _ = check_logos(layout, W, H, pubs)
    kf, _ = check_kit3d(kit3d_lines(probe))
    icf, _ = check_icons(layout, W, H, pubs)
    return sorted(lf + kf + icf, key=lambda x: x["at"])


# ================================================================================================================================ main
def stream(path, rng=None):
    """(frame, its pictures and texts, W, H) for every layout line of a probe, one at a time"""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("layout|"):
                continue
            try:
                o = json.loads(line.partition("|")[2])
            except ValueError:
                continue
            f = o.get("frame")
            if f is None or (rng and not rng[0] <= f <= rng[1]):
                continue
            yield f, [it for it in o["items"] if it["k"] in ("img", "clip", "text")], o.get("W", 1920), o.get("H", 1080)


def load(path, rng=None):
    layout, W, H = {}, 1920, 1080
    for f, items, W, H in stream(path, rng):
        layout[f] = items
    return layout, W, H


def allowed(folder, flags):
    p = folder / "gate_allow.json" if folder else None
    allow = json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else []
    keep, ok = [], []
    for fl in flags:
        a = next((x for x in allow if x["check"] == fl["check"] and (x["key"] in fl["key"] or x["key"] in fl["what"]) and x.get("reason")
                  and (not x.get("frames") or not isinstance(fl.get("at"), (int, float)) or x["frames"][0] <= fl["at"] <= x["frames"][1])), None)
        (ok if a else keep).append((fl, a))
    return [k for k, _ in keep], ok


def mmss(f):
    t = f / FPS
    return f"{int(t // 60)}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video", nargs="?")
    ap.add_argument("--probe", help="a gate probe (probe.jsonl) [the video's own]")
    ap.add_argument("--kit3d", help="kit3d lines to read instead of the probe's (src/kit3d/test/centre.test.mjs --json writes them)")
    ap.add_argument("--range", help="frames a-b")
    ap.add_argument("--pub", nargs="*", help="public dirs to read pictures from [the video's pub, the main public dir]")
    ap.add_argument("--json", help="write the measurements and flags here")
    a = ap.parse_args()
    v = folder = None
    if a.video:
        from common import Video, find_video
        folder = find_video(a.video)
        v = Video(folder)
    probe = Path(a.probe) if a.probe else (v.pipe_dir / "gate" / "probe.jsonl" if v else None)
    rng = tuple(int(x) for x in a.range.split("-")) if a.range else None
    pubs = [Path(p) for p in a.pub] if a.pub else (pubs_of(v) if v else [MOTION_PUB])
    # the probe streamed frame by frame (a long film's probe runs to hundreds of MB: its layout whole would take GBs)
    seen, missing, shows = defaultdict(dict), set(), defaultdict(list)
    n, W, H = 0, 1920, 1080
    if probe and probe.exists():
        for f, items, W, H in stream(str(probe), rng):
            n += 1
            logos_on_frame(f, items, W, H, pubs, seen, missing)
            for it in icon_items(items, W, H):
                shows[str(it["t"])].append(f)
    lf, lrows = check_logos(None, W, H, pubs, seen, missing)
    kf, krows = check_kit3d(kit3d_lines(a.kit3d or probe, rng))
    icf, irows = check_icons(None, W, H, pubs, shows)
    flags = sorted(lf + kf + icf, key=lambda x: x["at"])
    print(f"{n} frames read ({W}x{H}); lone centred pictures {len(lrows)} runs, 3D {len(krows)} runs, icons {len(irows)}")
    for r in lrows:
        print(f"  2D {mmss(r['at'])}-{mmss(r['to'])} {Path(r['name']).name} ({r['w']} px): visual {r['visual']:+.1f}, box {r['box']:+.1f}, weight {r['weight']:+.1f}")
    for r in krows:
        print(f"  3D {mmss(r['at'])}-{mmss(r['to'])} {r['name']}: visual at rest {r['visual_rest']:+.1f} (worst {r['worst']:+.1f}), box {r['box']:+.1f}, weight {r['weight']:+.1f}")
    for r in irows:
        m = r["face"]
        print(f"  icon {mmss(r['at'])} {Path(r['name']).name}: " + (f"face {m['share'] * 100:.0f}%, {m['dx'] * 100:+.1f}% / {m['dy'] * 100:+.1f}%" if m else "no face")
              + f"; source {(r['source'] or {}).get('file', '-')}")
    keep, ok = allowed(folder, flags)
    for fl in keep:
        print(f"{'LOOK' if fl.get('look') else 'FLAG'} {fl['check']} {mmss(fl['at'])}: {fl['what']}")
    for fl, al in ok:
        print(f"allowed {fl['check']} {mmss(fl['at'])}: {fl['what']} ({al['reason']})")
    if a.json:
        Path(a.json).write_text(json.dumps({"logos": lrows, "kit3d": krows, "icons": irows, "flags": flags}, indent=1), encoding="utf-8")
    sys.exit(1 if [f for f in keep if not f.get("look")] else 0)


if __name__ == "__main__":
    main()
