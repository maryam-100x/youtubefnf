"""qa_still_words.py: the picture against the words it sits under. A viewer watches to SEE what is being told, not to read it: a held
picture under words of action, or a text card where the words point at a moment you can see, loses them.

  STILL_UNDER_ACTION  a held picture (a still image under at most a slow push, a frozen clip frame, a mark hold, a page, a text or number
                      card, a built graphic standing still) for most of a phrase that describes action or change: a verb of motion
                      ("drive off", "blinking", "switch"), a change ("works differently"), one by one or every ("one part at a time",
                      "year by year", "every single"), or a list of three or more said over one held picture. A held frame under "one
                      part at a time" reads as a frozen frame; a headline card under "every single detail" asks the viewer to read.
  CARD_FOR_MOMENT     a text or page card under words that name a moment you can see ("we can see", "you can see", "in the trailer",
                      "shows"): the moment itself goes on screen, never an article's line about it. A moment a past video used is not a
                      reason for the card: qa_reused.py accepts it when the shot's comment says `named-moment:`. The names of the
                      source's own videos ("in the launch video") go in data/moment_words.json as extra patterns.
  MARK_SMALL          a lit mark (data-gate="mark" or a hollow outline: gate.mark_items) whose box is under MARK_MIN_H px tall on the
                      1080 frame at its full light: most viewers miss a small box in a corner. Measured on screen, so a picture zoomed
                      or framed onto its target first passes.
  MARK_CORNER         a lit mark whose centre sits in an outer corner of the frame (the outer CORNER of the width and of the height).

How it sees: the gate's probe (gate_probe.mjs: every frame's texts, pictures, clip panes and marks with their real boxes, and the source
second every clip shows), so it runs on the code before any render. Each frame's picture is one of
  play (a sharp clip, 40%+ of the frame, its source second moving), frozen (the same, its second standing still), still (a sharp picture,
  40%+, under at most a slow push), glide (a still under a real camera move: GLIDE_SCALE a second or GLIDE_PX), card (a page capture, a
  blurred ground with our own text or picture on it, or 8+ words of text at reading size with no sharp clip), graphic / held_graphic
  (built pieces moving / standing), or not judged (nothing lit: a 3D canvas reads empty in the probe).
Held = frozen, still, card, held_graphic. The words come from the narration's word times (the inserted copy when bites are laid in).
A flag is fixed, or allowed in videos/<video>/gate_allow.json ({"check", "key", "reason"}: the key is the phrase, or the mark's
box as the flag's text gives it, "box 233,464 23x40" (an allow key matches the flag's key or its text), never its "MARK@<frame>": a
frame goes stale at every re-timing), with the reason that proves it.

  PIPE tools/motion/qa_still_words.py <video> [--probe <probe.jsonl>] [--words <words.json>]
        [--range a-b (frames)] [--out <dir>] [--marks-only | --words-only] [--dump-marks]
  exit 1 on a flag not allowed
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import TOOLS  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "pipeline"))

FPS = 60
HELD = {"frozen", "still", "card", "held_graphic"}
GLIDE_SCALE = 0.10      # a still whose scale changes 10%+ a second is under a real camera move (the house push: 1.6-4%/s)
GLIDE_PX = 120.0        # ... or whose centre travels 120+ px a second (a map's fly-over: hundreds)
HELD_SHARE = 0.6        # a phrase is under a held picture when 60%+ of its judged frames are held
MIN_RUN = 0.5           # ... and that held picture stays 0.5 s or more
MARK_MIN_H = 48.0       # px on the 1080 frame (64 px at 1440p): a 37-px box is missed; marks that read measure 50+
CORNER = 0.15           # the outer 15% of the width AND of the height

# the words (the figurative uses that fire on a long film and are not action are left out: a date's "fall", a name like Dodge,
# "switched it off", "showed up", "every single week", "had turned into")
MOTION = ("drive drives driving drove driven chase chases chasing chased crash crashes crashing crashed race races racing raced ride rides "
          "riding rode steal steals stealing stole stolen shoot shoots shooting firing fight fights fighting fought hop hops hopping hopped "
          "switch switches switching switched swap swaps swapping swapped jump jumps jumping jumped falling fell climb climbs "
          "climbing climbed swim swims swimming swam explode explodes exploding exploded punch punches punching punched kick kicks kicking "
          "kicked throw throws throwing threw rob robs robbing robbed escape escapes escaping escaped dance dances dancing danced walk walks "
          "walking walked spin spins spinning spun flip flips flipping flipped dodge dodges dodging dodged smash smashes smashing smashed "
          "grab grabs grabbing grabbed blink blinks blinking blinked attack attacks attacking attacked sneak sneaks sneaking flies flying "
          "flew fly").split()
CHANGE = ["different", "differently", "change", "changes", "changed", "changing", "transform", "transforms", "transformed",
          "turn into", "turns into"]
SEQUENCE = [r"one \w+ at a time", r"one at a time", r"one by one", r"one after (?:another|the other)", r"\b(\w+) by \1\b",
            r"every single (?!time|week|day|month|year|night|hour|minute|second)", r"every one of", r"each one", r"step by step"]
MOMENT = [r"we can see", r"you can see", r"we see", r"you see", r"can be seen", r"in (?:the )?(?:\w+ ){0,2}trailer",
          r"\bshows\b(?! up)", r"\bshowed\b(?! up)", r"\bshown\b", r"on screen", r"you can spot", r"we can spot"]
OFF_ON = {"switch", "switches", "switching", "switched"}   # "switched that on", "switched the whole thing off": a setting, not the action


def _moment_extra():
    """the creator's own moment patterns (data/moment_words.json: a list of regexes on the lower-case words, punctuation dropped,
    e.g. "in (?:the )?launch video"): the names of the source's own videos"""
    try:
        return [str(p) for p in json.loads((HERE / "data" / "moment_words.json").read_text(encoding="utf-8"))]
    except (OSError, ValueError):
        return []


MOMENT += _moment_extra()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "").replace("'", ""))


# ===================================================================================================================== the probe, per frame
def load(path, rng=None):
    layout, clips = {}, defaultdict(dict)
    W, H = 1920, 1080
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            kind, _, body = line.partition("|")
            if kind not in ("layout", "clip"):
                continue
            try:
                o = json.loads(body)
            except ValueError:
                continue
            f = o.get("frame") if kind == "layout" else o.get("abs")
            if f is None or (rng and not rng[0] <= f <= rng[1]):
                continue
            if kind == "layout":
                layout[f] = o["items"]
                W, H = o.get("W", W), o.get("H", H)
            else:
                clips[f][str(o["src"])] = o["s"]
    return layout, clips, W, H


def varea(it, W, H):
    x0, y0 = max(0.0, it["x"]), max(0.0, it["y"])
    x1, y1 = min(W, it["x"] + it["w"]), min(H, it["y"] + it["h"])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def frame_kind(f, layout, clips, W, H):
    """(kind, the picture's name) of frame f"""
    A = W * H
    items = layout.get(f, [])
    lit = [it for it in items if it["op"] >= 0.5 and it.get("g") != "credit"]
    bl = lambda it: it.get("bl") or 0  # noqa: E731
    sharp_clips = sorted((it for it in lit if it["k"] == "clip" and bl(it) < 2 and varea(it, W, H) >= 0.4 * A),
                         key=lambda it: -varea(it, W, H))
    page = [it for it in lit if it["k"] == "img" and "/pages/" in str(it["t"]).replace("\\", "/") and varea(it, W, H) >= 0.08 * A]
    ground = any(it["k"] in ("clip", "img") and bl(it) >= 4 and varea(it, W, H) >= 0.5 * A for it in lit)
    on_ground = [it for it in lit if bl(it) < 2 and it.get("g") not in ("name", "mark")
                 and ((it["k"] in ("img", "box", "svg") and 0.05 * A <= varea(it, W, H) < 0.9 * A)
                      or (it["k"] == "text" and (it.get("fs") or 0) >= 40))]
    words = sum(len(str(it["t"]).split()) for it in lit if it["k"] == "text" and (it.get("fs") or 0) >= 26
                and it.get("g") not in ("name", "roll"))
    if page:
        return "card", Path(str(page[0]["t"])).stem
    if not sharp_clips and ((ground and on_ground) or words >= 8):
        top = max(on_ground, key=lambda it: varea(it, W, H)) if on_ground else None
        # pictures travelling across the ground (a strip of years gliding past) are a camera move, not a card; digits rolling on a
        # number card leave it a card
        prev = {(it["k"], str(it["t"])): it for it in layout.get(f - 6, [])}
        for it in on_ground:
            q = prev.get((it["k"], str(it["t"])))
            if it["k"] != "text" and q is not None:
                move = (abs(it["x"] + it["w"] / 2 - q["x"] - q["w"] / 2) + abs(it["y"] + it["h"] / 2 - q["y"] - q["h"] / 2)) / (6 / FPS)
                if move >= GLIDE_PX:
                    return "graphic", Path(str(it["t"])).stem or it["k"]
        name = (Path(str(top["t"])).stem or top["k"]) if top else "text"
        texts = [it for it in lit if it["k"] == "text" and it.get("g") not in ("name", "roll") and (it.get("fs") or 0) >= 40]
        if name in ("box", "svg") and texts:   # a number or text card: named by its biggest line
            name = str(max(texts, key=lambda it: it.get("fs") or 0)["t"])[:40]
        return "card", name
    if sharp_clips:
        c = sharp_clips[0]
        src = str(c["t"])
        s, sp = clips.get(f, {}).get(src), clips.get(f - 1, {}).get(src)
        name = Path(src).stem
        if s is not None and sp is not None and abs(s - sp) < 0.25 / FPS:
            return "frozen", name
        return "play", name
    stills = sorted((it for it in lit if it["k"] == "img" and bl(it) < 2 and varea(it, W, H) >= 0.4 * A), key=lambda it: -varea(it, W, H))
    if stills:
        p = stills[0]
        q = next((it for it in layout.get(f - 6, []) if it["k"] == "img" and it["t"] == p["t"]), None)
        if q:
            dt = 6 / FPS
            scale = abs(p["w"] / max(q["w"], 1.0) - 1) / dt
            move = (abs(p["x"] + p["w"] / 2 - q["x"] - q["w"] / 2) + abs(p["y"] + p["h"] / 2 - q["y"] - q["h"] / 2)) / dt
            if scale >= GLIDE_SCALE or move >= GLIDE_PX:
                return "glide", Path(str(p["t"])).stem
        return "still", Path(str(p["t"])).stem
    content = [it for it in lit if varea(it, W, H) >= 0.01 * A]
    if not content:
        return None, ""
    prev = {(it["k"], str(it["t"])): it for it in layout.get(f - 1, [])}
    moved = False
    for it in content:
        q = prev.get((it["k"], str(it["t"])))
        if q is None or abs(it["x"] - q["x"]) + abs(it["y"] - q["y"]) > 0.5 or abs(it["w"] / max(q["w"], 1.0) - 1) > 0.002:
            moved = True
            break
    big = max(content, key=lambda it: varea(it, W, H))
    return ("graphic" if moved else "held_graphic"), (Path(str(big["t"])).stem or big["k"])


# ============================================================================================================================= the words
def phrases(words):
    """[(check, label, i0, i1)]: the action, change, sequence and moment phrases in the narration, by word index"""
    toks = [norm(x["w"]) for x in words]
    text, offs = "", []
    for i, t in enumerate(toks):
        offs.append(len(text))
        text += t + " "
    def span(m):
        a, b = m.start(), m.end() - 1
        i0 = max(i for i, o in enumerate(offs) if o <= a)
        i1 = max(i for i, o in enumerate(offs) if o <= b)
        return i0, i1
    out = []
    for pat, check, label in ([(rf"\b{w}\b", "STILL_UNDER_ACTION", "motion") for w in MOTION]
                              + [(rf"\b{w}\b", "STILL_UNDER_ACTION", "change") for w in CHANGE]
                              + [(p, "STILL_UNDER_ACTION", "one by one / every") for p in SEQUENCE]
                              + [(p, "CARD_FOR_MOMENT", "a moment you can see") for p in MOMENT]):
        for m in re.finditer(pat, text):
            i0, i1 = span(m)
            if label == "motion":
                w0 = words[i0]["w"].strip("\"“”'‘ ")
                if w0[:1].isupper() and i0 > 0 and not words[i0 - 1]["w"].rstrip().endswith((".", "?", "!", ":")):
                    continue   # a name mid-sentence (Dodge, the car maker)
                if toks[i0] in OFF_ON and any(t in ("on", "off") for t in toks[i0 + 1:i0 + 6]):
                    continue
            out.append((check, label, i0, i1))
    # a list: three or more short items (1-4 words each), each ending in a comma, parallel (they start with the same word, or each is one
    # or two words): "your keys, your phone, your wallet,"; a date's commas ("On March 4th, 2030,") or an apposition
    # ("the company, the one that makes it,") are not a list
    i = 0
    while i < len(words):
        items, j = [], i
        while j < len(words):
            k = j
            while k < len(words) and k - j < 3 and not words[k]["w"].rstrip().endswith((",", ".", "?", "!")):
                k += 1
            if k >= len(words) or not words[k]["w"].rstrip().endswith(","):
                break
            items.append((j, k))
            j = k + 1
        firsts = [norm(words[p]["w"]) for p, _ in items]
        if len(items) >= 3 and not (max(firsts.count(x) for x in firsts) >= 2 or all(q - p <= 1 for p, q in items)):
            items = []
        if len(items) >= 3:
            out.append(("STILL_UNDER_ACTION", "a list", items[0][0], items[-1][1]))
            out[-1] = out[-1] + (items,)
            i = j
        else:
            i += 1
    return out


def held_runs(kinds):
    """{frame: (run start, run end, kind, name)} for every frame of a run of one held picture"""
    by, cur = {}, None
    for f in sorted(kinds):
        k, n = kinds[f]
        if k in HELD:
            if cur and cur[1] == f - 1 and cur[3] == n:
                cur[1] = f
            else:
                cur = [f, f, k, n]
                by.setdefault("runs", []).append(cur)
        else:
            cur = None
    out = {}
    for r in by.get("runs", []):
        for f in range(r[0], r[1] + 1):
            out[f] = tuple(r)
    return out


def acted_out(layout, f0, f1, W, H, need=2):
    """our own pieces act the words out: at least `need` separate moments inside the phrase (+0.1 s) where a piece of ours (a shape, an
    icon, a mark, a picture under 40% of the frame; never text, never the held picture itself, never a credit) appears, goes, lights or
    changes colour, or moves 15 px+ in 3 frames (icons clearing one by one, each readout lit on its word, a bar filling red and a dot
    sliding along it). A single mark landing on a held frame, or a card's rolling digits, stay held"""
    if not layout:
        return False
    A = W * H

    def pieces(f):
        out = defaultdict(list)
        for it in layout.get(f, []):
            if it["op"] < 0.3 or it["k"] == "text" or it.get("g") == "credit":
                continue
            if varea(it, W, H) >= 0.4 * A:   # the held picture itself, a full-frame vignette or dim
                continue
            out[(it["k"], str(it["t"]))].append((it["x"] + it["w"] / 2, it["y"] + it["h"] / 2, it["op"], it.get("c")))
        return out

    moments, prev = 0, pieces(f0 - 3)
    for f in range(f0, f1 + 1, 3):   # inside the held picture's own frames: the next shot's arrival is no act
        cur = pieces(f)
        ev = False
        for key in set(cur) | set(prev):
            a, b = cur.get(key, []), prev.get(key, [])
            if len(a) != len(b):
                ev = True   # one appeared or went
                break
            for p in a:
                q = min(b, key=lambda q: abs(q[0] - p[0]) + abs(q[1] - p[1]))
                if abs(q[0] - p[0]) + abs(q[1] - p[1]) >= 15 or abs(q[2] - p[2]) >= 0.3 or q[3] != p[3]:
                    ev = True
                    break
            if ev:
                break
        moments += ev
        prev = cur
    return moments >= need


def no_footage(v):
    """{picture stem: the search} for shots whose code comment says `// no-footage: <the action>, searched: <3+ wordings>`: the only real
    example of a thing stays, and "it doesn't exist" needs 3+ search wordings first. Written where the pick is made, so the gate asks
    nothing. A comment without "searched" passes nothing"""
    if v is None:
        return {}
    try:
        import qa_shots
        ents = qa_shots.code_entries(Path(__file__).resolve().parent / "src" / v.src)
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for e in ents:
        for c in e.get("comment", []):
            m = re.match(r"no-footage:\s*(.+)", c)
            if m and "searched" in m.group(1):
                for n in e["names"]:
                    out[n] = m.group(1)
    return out


def check_words(words, kinds, rng, layout=None, W=1920, H=1080, nofoot=None):
    runs = held_runs(kinds)
    flags, seen = [], set()
    for ph in phrases(words):
        check, label, i0, i1 = ph[:4]
        a, b = words[i0]["start"], words[i1]["end"]
        f0, f1 = round(a * FPS), max(round(a * FPS), round(b * FPS) - 1)
        if rng and not (rng[0] <= f0 <= rng[1]):
            continue
        judged = [f for f in range(f0, f1 + 1) if kinds.get(f, (None,))[0] is not None]
        if not judged:
            continue
        said = " ".join(w["w"] for w in words[i0:i1 + 1])
        ctx = " ".join(w["w"] for w in words[max(0, i0 - 6):min(len(words), i1 + 7)])
        if label == "a list":
            items = ph[4]
            for (p0, _), (q0, _) in zip(items, items[1:]):
                r = runs.get(round(words[p0]["start"] * FPS))
                if r and r == runs.get(round(words[q0]["start"] * FPS)) and (r[1] - r[0] + 1) / FPS >= MIN_RUN \
                        and not acted_out(layout, max(f0, r[0]), min(f1, r[1]), W, H):
                    key = (check, r[0])
                    if key not in seen:
                        seen.add(key)
                        flags.append({"check": check, "key": said, "at": r[0], "to": r[1], "what":
                                      f"{label} said over one held picture ({r[2]} '{r[3]}', {(r[1] - r[0] + 1) / FPS:.2f} s): \"{ctx}\""})
            continue
        if check == "CARD_FOR_MOMENT":
            cards = [f for f in judged if kinds[f][0] == "card"]
            if len(cards) / len(judged) < HELD_SHARE:
                continue
            r = runs.get(cards[0])
        else:
            held = [f for f in judged if kinds[f][0] in HELD]
            if len(held) / len(judged) < HELD_SHARE:
                continue
            r = runs.get(held[0])
            if r and (acted_out(layout, max(f0, r[0]), min(f1, r[1]), W, H) or (nofoot and r[3] in nofoot)):
                continue
        if not r or (r[1] - r[0] + 1) / FPS < MIN_RUN:
            continue
        old = next((x for x in flags if x["check"] == check and x["at"] == r[0]), None)
        if old is not None:   # one flag per held picture and check: its phrases listed together
            if said not in old["key"]:
                old["key"] += f" / {said}"
                old["what"] = old["what"].replace("' over ", f"' / '{said}' over ", 1)
            continue
        what = ("a card stands in for the moment the words point at" if check == "CARD_FOR_MOMENT"
                else f"a held picture under {label} words")
        flags.append({"check": check, "key": said, "at": r[0], "to": r[1],
                      "what": f"{what}: '{said}' over {r[2]} '{r[3]}' ({(r[1] - r[0] + 1) / FPS:.2f} s held): \"{ctx}\""})
    return flags


# ============================================================================================================================= the marks
def mark_groups(layout, W, H, rng):
    """one entry per mark stretch: its box at full light (the frame it is biggest and lit), its frames"""
    from gate import mark_items  # the gate's own definition of a mark (data-gate="mark", or a hollow outline)
    groups = {}
    for f in sorted(layout):
        if rng and not rng[0] <= f <= rng[1]:
            continue
        items = layout[f]
        for i in mark_items(items, W, H):
            it = items[i]
            if it["op"] < 0.5:
                continue
            k = (round(it["x"] / 6), round(it["y"] / 6), round(it["w"] / 6), round(it["h"] / 6))
            g = next((v for kk, v in groups.items() if v["last"] >= f - 2 and abs(kk[0] - k[0]) <= 2 and abs(kk[1] - k[1]) <= 2
                      and abs(kk[2] - k[2]) <= 3 and abs(kk[3] - k[3]) <= 2), None)
            if g is None:
                g = groups.setdefault(k, {"first": f, "last": f, "box": it, "n": 0})
            g["last"] = f
            g["n"] += 1
            if it["w"] * it["h"] >= g["box"]["w"] * g["box"]["h"]:
                g["box"] = it
                g["bf"] = f   # the frame of that box (edge_bound reads the picture under it there)
    return sorted(groups.values(), key=lambda g: g["first"])


ZOOMED_IN = 1.6         # a picture drawn this much bigger than the frame has been zoomed into (kit3 Foot `zoom`)


def edge_bound(layout, f, cx, cy, W, H, tol=0.5 - CORNER):
    """True when a corner mark sits in its corner only because its picture is zoomed into it as far as the picture's own edges allow: the
    biggest lit picture under the mark at frame f is >= ZOOMED_IN x the frame and its edge lies on the frame's edge on each side the mark
    is near. A readout that lives in its corner of the source picture (a status icon, a small clock) zoomed into as far as it goes is the
    framing the corner rule asks for"""
    px, py = cx * W, cy * H
    pics = [it for it in layout.get(f, []) if it["k"] in ("clip", "img") and it["op"] >= 0.5
            and it["x"] <= px <= it["x"] + it["w"] and it["y"] <= py <= it["y"] + it["h"]]
    if not pics:
        return False
    p = max(pics, key=lambda it: it["w"] * it["h"])
    if p["w"] < ZOOMED_IN * W:
        return False
    # an axis the mark is off centre on (beyond `tol`) needs the picture's edge on the frame's edge on that side (within 1% of the
    # picture: the keep-alive drift after the zoom grows it round the mark, so its edge creeps a few px past the frame's)
    e = max(2.0, 0.01 * max(p["w"], p["h"]))
    okx = abs(cx - 0.5) <= tol or (p["x"] >= -e if cx < 0.5 else p["x"] + p["w"] <= W + e)
    oky = abs(cy - 0.5) <= tol or (p["y"] >= -e if cy < 0.5 else p["y"] + p["h"] <= H + e)
    return okx and oky


def check_marks(layout, W, H, rng):
    flags, rows = [], []
    s = 1080.0 / H
    for g in mark_groups(layout, W, H, rng):
        b = g["box"]
        if g["n"] < 6:   # under 0.1 s lit: a mark drawing in or out, not a mark the eye reads
            continue
        x0, y0 = max(0.0, b["x"]), max(0.0, b["y"])
        x1, y1 = min(W, b["x"] + b["w"]), min(H, b["y"] + b["h"])
        h = (y1 - y0) * s
        cx, cy = (x0 + x1) / 2 / W, (y0 + y1) / 2 / H
        corner = (cx < CORNER or cx > 1 - CORNER) and (cy < CORNER or cy > 1 - CORNER)
        if corner and edge_bound(layout, g.get("bf", g["last"]), cx, cy, W, H):
            corner = False
        rows.append((g["first"], g["last"], round(x0), round(y0), round(x1 - x0), round(y1 - y0), round(h, 1), round(cx, 3), round(cy, 3), corner))
        key = f"MARK@{g['first']}"
        where = f"box {round(x0)},{round(y0)} {round(x1 - x0)}x{round(y1 - y0)} px, lit {(g['last'] - g['first'] + 1) / FPS:.2f} s"
        if h < MARK_MIN_H:
            flags.append({"check": "MARK_SMALL", "key": key, "at": g["first"], "to": g["last"],
                          "what": f"a mark {h:.0f} px tall on the 1080 frame (under {MARK_MIN_H:.0f}; {h * 4 / 3:.0f} px at 1440p): {where}; "
                                  "frame the picture onto it first, or mark something bigger"})
        if corner:
            flags.append({"check": "MARK_CORNER", "key": key, "at": g["first"], "to": g["last"],
                          "what": f"a mark in the frame's outer corner (centre at {cx:.0%} across, {cy:.0%} down): {where}; "
                                  "frame the picture onto it first"})
    return flags, rows


# ================================================================================================================================ the gate
def words_of(v):
    """the narration's word times on the film: the inserted copy when bites are laid in, else the src's words.json"""
    ins = v.dj / "build" / "insert" / "words_ins.json"
    return json.loads((ins if ins.exists() else v.words()).read_text(encoding="utf-8"))


def gate_flags(v, layout=None, clips=None):
    """the four checks for gate.py (B20), on the probe the gate already loaded: layout {frame: items}, clips {frame: [clip lines]}
    (gate.load_probe's shapes). The gate's own allows (gate_allow.json) and sign-offs apply to these flags like to its own."""
    if layout is None:
        layout, cl, W, H = load(str(v.pipe_dir / "gate" / "probe.jsonl"))
    else:
        cl = defaultdict(dict)
        for f, lst in (clips or {}).items():
            for c in lst:
                cl[f][str(c["src"])] = c["s"]
        W, H = (1920, 1080)
        try:
            import gate
            W, H = gate.FRAME
        except Exception:  # noqa: BLE001
            pass
    kinds = {f: frame_kind(f, layout, cl, W, H) for f in sorted(layout)}
    flags = check_words(words_of(v), kinds, None, layout, W, H, no_footage(v)) + check_marks(layout, W, H, None)[0]
    return sorted(flags, key=lambda x: x["at"])


# ================================================================================================================================ main
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
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?")
    ap.add_argument("--probe")
    ap.add_argument("--words")
    ap.add_argument("--range", help="frames a-b")
    ap.add_argument("--out")
    ap.add_argument("--marks-only", action="store_true")
    ap.add_argument("--words-only", action="store_true")
    ap.add_argument("--dump-marks", action="store_true", help="print every mark's size and place (the thresholds' calibration)")
    ap.add_argument("--kinds", action="store_true", help="print each run of one picture kind (to read what the check saw)")
    a = ap.parse_args()
    folder, probe, words_p, v = None, a.probe, a.words, None
    if a.video:
        from common import Video, find_video
        folder = find_video(a.video)
        v = Video(folder)
        probe = probe or str(v.pipe_dir / "gate" / "probe.jsonl")
        if not words_p:
            ins = v.dj / "build" / "insert" / "words_ins.json"
            words_p = str(ins if ins.exists() else v.words())   # (words_of(v), as the gate reads them)
    if not probe:
        raise SystemExit("give a video or --probe")
    rng = tuple(int(x) for x in a.range.split("-")) if a.range else None
    layout, clips, W, H = load(probe, (rng[0] - 8, rng[1] + 8) if rng else None)
    print(f"probe: {len(layout)} frames ({probe})")
    flags = []
    if not a.marks_only:
        if not words_p:
            raise SystemExit("give --words (the narration's word times on the film)")
        words = json.loads(Path(words_p).read_text(encoding="utf-8"))
        kinds = {f: frame_kind(f, layout, clips, W, H) for f in sorted(layout)}
        if a.kinds:
            cur = None
            for f in sorted(kinds):
                if cur and kinds[f] == cur[2] and f == cur[1] + 1:
                    cur[1] = f
                    continue
                if cur:
                    print(f"  {mmss(cur[0])}-{mmss(cur[1] + 1)}  {cur[2][0] or '-':12s} {cur[2][1]}")
                cur = [f, f, kinds[f]]
            if cur:
                print(f"  {mmss(cur[0])}-{mmss(cur[1] + 1)}  {cur[2][0] or '-':12s} {cur[2][1]}")
        flags += check_words(words, kinds, rng, layout, W, H, no_footage(v))
    if not a.words_only:
        mf, rows = check_marks(layout, W, H, rng)
        flags += mf
        if a.dump_marks:
            print("marks (first-last frame, box x y w h on the film, height on the 1080 frame, centre, corner):")
            for r in rows:
                print(f"  {mmss(r[0])}-{mmss(r[1] + 1)}  {r[2:6]}  h {r[6]:5.1f}  centre {r[7]:.2f},{r[8]:.2f}{'  CORNER' if r[9] else ''}")
    flags.sort(key=lambda x: x["at"])
    keep, ok = allowed(folder, flags)
    for fl, al in ok:
        print(f"allowed {fl['check']} {mmss(fl['at'])}: {fl['what'][:140]}\n        ({al['reason'][:160]})")
    for fl in keep:
        print(f"{fl['check']:18s} {mmss(fl['at'])}-{mmss(fl['to'] + 1)}  {fl['what']}")
    print(f"{len(keep)} flags ({len(ok)} allowed)")
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "still_words.json").write_text(json.dumps({"flags": keep, "allowed": [f for f, _ in ok]}, indent=1), encoding="utf-8")
    return 1 if keep else 0


if __name__ == "__main__":
    sys.exit(main())
