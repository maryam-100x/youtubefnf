"""The coherency gate: the script, its real voices and its pictures must make sense together for a viewer (a quote the narration says
right before the person says it on screen, a person's voice over an unrelated graph, an interview answer with no question before it).
As hard as the flash-frame and sound gates: nothing renders with an open coherency flag.

  packet <video>   writes <dj>/pipeline/coherency/packet.md: the script line by line, the creator's interview (question -> where the
                   answers went), the real voices (each lead-in, the clip's words, its picture), and the shot table in film order (beat,
                   the words a shot starts on, the picture from its code comment, the clip and its credit), with a stamp of the inputs
  check  <video>   the gate's half: videos/<video>/COHERENCY.md must carry the current stamp (a read of this exact script and code)
                   and every flag must be closed ("fixed: ..." or "allowed: <proof>"); exit 1 otherwise

The read itself is a fresh reader (an agent never told what the chat thinks) given the packet and RUBRIC below; it writes COHERENCY.md:
  stamp: <stamp>
  - [ ] C1 S12 (9:48) SCRIPT: <the words> | <why it breaks> | <the fix>
  closed by the chat as "- [x] C1 ... fixed: <what changed>" or "allowed: <why it is coherent>"; after the fixes the packet's stamp
  changes, so the read runs again on the fixed video until it comes back clean.

Data files beside this one (empty until the creator fills them): banned_sources.json (a list of regexes; a credit or source path in the
code that matches one fails the gate; case-sensitive, wrap a part in (?i:...) for any case), banned_pictures.json (a list of
{"dhash": "<16 hex>", "what": "...", "rule": "..."}), gloss_owners.json (a list of owner names, e.g. ["Acme"]: "Acme's Y" and "is
Acme's version of Y" count as glosses in the S8 list).

  EDIT tools/pipeline/coherency.py packet|check <video>"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import MOTION, PUBLIC, REPO, Video, find_video  # noqa: E402
sys.path.append(str(MOTION))
import codefiles  # noqa: E402   a video's code with the subfolder files it imports

RUBRIC = """Read the whole video the way a viewer meets it, line by line and shot by shot, and flag every place where it stops making sense.

SCRIPT (the words alone, before any picture):
 S1 every line follows from the line before; a new topic gets a turn that says where we are going;
 S2 every quote, opinion or interview answer carries its own setup: the question it answers or the thing it reacts to is in the line
    itself or just before it (an answer "It's all of it" to "which moment of the final got you most?" can't stand after a line about
    a coach saying "We're ready": the viewer never heard the question);
 S3 nothing refers to a person, thing or claim that was never introduced or not named in the last lines ("he", "that", "the same
    thing", "it"); the title is no antecedent (a viewer immersed in the video doesn't hold it: a sign-off "if you still don't get it"
    that means the hype, last named minutes before, needs "or if you still don't get the hype");
 S4 a line that introduces a real person's clip leads straight into it and never says the clip's words first (the narration quoting
    "because it only flowers every few years" and then the person saying it is redundant);
 S5 the line into a clip and the clip match: the clip says what that line promises ("they said the same thing" before a clip about
    something else is broken).
 S6 the creator's interview answers (the interview section below) keep every point they named when they go into the script: a reason,
    a product, a rumour they saw, a feeling; a point dropped or softened out of caution is a flag (a leak they name is said, never shown
    or described).
 S7 an opinion's stance is clear from its first words and the line never sounds like the opposite of what is meant until its last
    clause: a hypothetical is framed as one ("If anything let me down, it would be ..."), never as an expectation ("The only thing I can
    see letting me down is the battery ... I really doubt it" sounds like the speaker expects it to happen).
 S8 a term is explained once per video: "X, which is Y" / "X is its (the maker's) version of Y" / "the maker's Y" the first time X comes
    up, never again; later lines just name it (a nickname glossed as its real name three times is a flag). The packet's gloss list
    below shows every one.
AUDIO AND PICTURE (every shot against the words it sits on):
 A1 the picture is about its words: a named person shows that person (in a compilation, that person's own view), a named product that
    product, a number its source;
 A2 a real person's clip shows that person speaking; their voice over a card, graph or unrelated footage is broken (an interviewee's
    voice over a sales chart);
 A3 nobody talks on screen under narration that isn't theirs, above all while the narration quotes or paraphrases that person;
 A4 no card, chart or graphic that has nothing to do with the words under it;
 A5 the same words aren't shown lit on a page and then said again by a clip a second later;
 A6 an on-screen credit names the source channel, never a person guessed from the picture.
 A7 a lit mark only where the eye needs help: a phrase in an article or a small band on a label; a number, logo or word that already
    fills the middle of the frame gets none (a big year in the centre of the frame: no reason to mark it).
 A8 every picture is the best version of the thing that exists: the packet's still list flags images shown bigger than their pixels
    (over 1.3x); a news bug's grey frame where a lit clean shot exists, a video frame of a product where its press photo exists, an unknown face
    where the group's best-known one exists are flags.
For each flag write one line:
 - [ ] C<n> <beat> SCRIPT|PICTURE|CLIP <rubric id>: "<the words, quoted>" | <what breaks, in one plain sentence> | <the smallest fix>
Flag only real breaks a viewer would feel; no style notes, no taste. A clean video gets no flags."""


def code_files(v):
    """the video's code files: its src folder and the subfolder files the film imports (the stamp, the shot table and the banned-source
    scans read them all; a builder's preview root there, imported by nothing, stays out of the stamp: editing it never voids a read)"""
    return codefiles.code_files(MOTION / "src" / v.src)


def stamp(v):
    h = hashlib.sha1()
    for p in [v.folder / "script.md", v.folder / "OPINIONS.md", *code_files(v),
              *sorted((MOTION / "src" / v.src).glob("inserts*.json"))]:
        if p.exists():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


HELPER = re.compile(r"^\s*(ft2?|page|parts|shot)\(")   # shot helpers (`ft(at, 'clip', credit)`, `ft2(...)`, `page(at, ...)`, `shot(at, el)`):
# the shots written through them are read too, or the packet would miss them


def first_arg(s):
    """the call's first argument, brackets balanced (`w('S12', 'and more than')` holds commas)"""
    depth, q = 0, None
    for i, c in enumerate(s):
        if q:
            q = None if c == q else q
        elif c in "'\"`":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return s[:i]
            depth -= 1
        elif c == "," and depth == 0:
            return s[:i]
    return s


def shots(v):
    """[(file, anchor, comment, clip names, credits)] in the code's order, from each `{at: ...}` entry (or a shot helper's call) and the
    comment above it"""
    out = []
    src = MOTION / "src" / v.src
    for f in code_files(v):
        name = f.relative_to(src).with_suffix("").as_posix()      # a subfolder's file by its path (fix1/street), the top level's by its stem
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith(("const ", "export const ", "function ")):
                continue          # a helper's own definition (`const ft = (at, ...) => ({at, el: ...})`) is no shot
            m = re.search(r"\{at:\s*(.+?),\s*el:", ln)
            hm = None if m else HELPER.match(ln)
            if hm:
                arg = first_arg(ln[hm.end():]).strip()
                m = re.match(r"(.*)", arg)
            if not m:
                continue
            k, com = i - 1, []
            while k >= 0 and lines[k].strip().startswith("//"):
                com.insert(0, lines[k].strip().lstrip("/ ").strip())
                k -= 1
            j = next((k2 for k2 in range(i + 1, min(len(lines), i + 40)) if re.search(r"\{at:", lines[k2]) or HELPER.match(lines[k2])),
                     min(len(lines), i + 12))
            body = " ".join(lines[i:j])
            clips = re.findall(r"(?:Ft|Foot|clip=|a=|b=)\(?\s*['\"]([a-z0-9_]+)['\"]", body)
            if hm and hm.group(1) in ("ft", "ft2", "parts", "shot"):     # the helper's clip names and its credit string
                clips += [c for c in re.findall(r"['\"]([a-z0-9]+_[a-z0-9_]+)['\"]", body) if c not in clips]
            imgs = re.findall(r"['\"]([\w/.-]+\.(?:jpg|png|webp))['\"]", body)
            pages = re.findall(r"name=['\"]([\w-]+_m)['\"]", body)
            cred = re.findall(r"credit[=:]\s*['\"]([^'\"]+)['\"]", body) + re.findall(r"source=['\"]([^'\"]+)['\"]", body)
            el = re.search(r"el:\s*\([^)]*\)\s*=>\s*(?:\{[^<]*?return\s*)?<?\s*(\w+)", body)
            out.append((name, m.group(1).strip(), " ".join(com), clips + imgs + pages, cred, el.group(1) if el else ""))
    return out


def _json_list(name):
    p = HERE / name
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    except ValueError:
        d = []
    return d if isinstance(d, list) else []


def gloss_pattern():
    """S8's gloss phrases: "which is", "is its (their) own version of", "as the <maker> calls it", plus every owner in gloss_owners.json
    ("Acme's Y", "is Acme's version of Y")"""
    own = "|".join(re.escape(o) + "'s" for o in _json_list("gloss_owners.json") if isinstance(o, str) and o)
    alts = [r"which is", r"is (?:%sits|their) (?:own )?version of" % (own + "|" if own else ""),
            r"(?:its%s) own version of" % ("|" + own if own else "")]
    if own:
        alts += [r"(?:%s) (?=[A-Z])" % own, r"(?:%s) version of" % own]
    alts.append(r"as the \w+ calls it")
    return re.compile(r"(?:" + "|".join(alts) + r")\s*([A-Z][\w']*(?: [A-Z][\w']*)*)")


def packet(v):
    d = v.dj / "pipeline" / "coherency"
    d.mkdir(parents=True, exist_ok=True)
    st = stamp(v)
    script = [ln for ln in (v.folder / "script.md").read_text(encoding="utf-8").splitlines() if re.match(r"\[S\w+\]", ln)]
    # a prototype's narration (tools/voice/proto_narration.py: build/beats.json says "prototype") holds only its own beats: the
    # read covers those lines, not the whole script
    try:
        bj = json.loads((v.dj / "build" / "beats.json").read_text(encoding="utf-8"))
        if bj.get("prototype"):
            keep = {b["id"] for b in bj["beats"]}
            script = [ln for ln in script if re.match(r"\[(S\w+)\]", ln).group(1) in keep]
    except (OSError, ValueError, KeyError):
        pass
    ins = []
    for p in sorted((MOTION / "src" / v.src).glob("inserts*.json")):
        for x in json.loads(p.read_text(encoding="utf-8")):
            # an insert says `before` (the bite plays inside its beat, right before that phrase) or `after` (it plays after the beat's
            # last shot); each is printed the way it plays, or a reader flags a bite that is placed right
            where = (f"in {x.get('beat')}, right before \"{x.get('before')}...\"" if x.get("before")
                     else f"after {x.get('beat')} \"...{x.get('after')}\"")
            ins.append(f"- {where}: {x.get('who')} says: "
                       f"{' '.join(l[2] for l in x.get('lines', []))} (clip {Path(x.get('src', '')).name} {x.get('a')}-{x.get('b')} s; credit {x.get('credit')})")
    # a HOLD beat's own voice: a <SaidHold ... lines={[[t0, t1, 'Who', 'words'], ...]} /> in the code (without it the readers meet the
    # hold as "[S12h] HOLD: 6.05" with no words)
    for f in code_files(v):
        if f.suffix not in (".ts", ".tsx"):
            continue
        src = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"shot\(\s*([^,]+?),[^\n]*?<SaidHold\b(.*?)/>\)", src, re.S):
            bm = re.search(r"['\"](S\w+)['\"]", m.group(1))
            said = re.findall(r"""['"]([^'"\]]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\]""", m.group(2))
            if said:
                ins.append(f"- in {bm.group(1) if bm else '?'} (a HOLD: the narration stops, the clip plays): "
                           + " / ".join(f"{who}: \"{txt}\"" for who, txt in said) + f" (code {f.name})")
    sh = shots(v)
    order = {}
    for i, ln in enumerate(script):
        order[re.match(r"\[(S\w+)\]", ln).group(1)] = i
    bite_beat, bite_before = {}, {}
    for p in sorted((MOTION / "src" / v.src).glob("inserts*.json")):
        for x in json.loads(p.read_text(encoding="utf-8")):
            bite_beat[x["name"]] = x.get("beat")
            if x.get("before"):
                bite_before[x["name"]] = re.sub(r"[^a-z0-9]", "", x["before"].lower())
    # a `before` bite sits right before the first shot of its beat whose anchor starts on that phrase (or a later one in the beat)
    first_at, idx = {}, {id(row): i for i, row in enumerate(sh)}
    for i, row in enumerate(sh):
        mm = re.search(r"\bw\(\s*['\"](S\w+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", row[1])
        if mm:
            for nm, ph in bite_before.items():
                if bite_beat.get(nm) == mm.group(1) and re.sub(r"[^a-z0-9]", "", mm.group(2).lower()).startswith(ph[:12]):
                    first_at.setdefault(nm, i)
    # a shot whose start names no beat (`shot(S12_AT(), ...)`: a computed time) takes the beat of the shot before it in its file (else it
    # would sort as beat 0, to the film's top, and a reader would judge it among the wrong lines)
    beat_of, last = {}, {}
    for row in sh:
        m = re.search(r"['\"](S\w+)['\"]", row[1])
        beat_of[id(row)] = m.group(1) if m else last.get(row[0])
        last[row[0]] = beat_of[id(row)]

    def key(s):
        i = idx[id(s)]
        m = re.search(r"insAt\(['\"](\w+)['\"]\)", s[1])
        if m and m.group(1) in first_at:   # inside its beat, right before its phrase's shot
            return (order.get(bite_beat.get(m.group(1)), -1), first_at[m.group(1)] - 0.5)
        if m:   # a bite plays after its beat's last shot
            return (order.get(bite_beat.get(m.group(1)), -1) + 0.5, i)
        b = beat_of.get(id(s))
        return (order.get(b, 0) if b else 0, i)
    rows = []
    for f, at, com, media, cred, _el in sorted(sh, key=key):
        rows.append(f"| {f} | `{at[:60]}` | {com[:300]} | {', '.join(media[:3])} | {'; '.join(dict.fromkeys(cred))[:120]} |")
    # S8: every gloss in the script, in order (a term explained twice is a flag)
    gl, seen = [], {}
    pat = gloss_pattern()
    for ln in script:
        beat = re.match(r"\[(S\w+)\]", ln).group(1)
        for m in pat.finditer(ln):
            y = m.group(1)
            gl.append(f"- {beat}: \"...{ln[max(0, m.start() - 40):m.end()].strip()}\"" + (f"  **REPEAT of {seen[y]}**" if y in seen else ""))
            seen.setdefault(y, beat)
    # A8: every still against its size on screen (a full-frame still 1920x1080; a panel at the frame's height)
    from PIL import Image
    pub = PUBLIC
    up = []
    for f, at, com, media, cred, el in sh:
        if el not in ("St", "Pic", "PhotoPanel", "Still"):
            continue      # a still inside a graphic (a card, a cut-out) has its own size there
        for m in media:
            if not re.search(r"\.(jpg|png|webp)$", m) or "/pages/" in m:
                continue
            cands = [pub / m, pub / v.src / "img" / m, pub / v.src / m]
            src = next((c for c in cands if c.exists()), None)
            if not src:
                continue
            w, h = Image.open(src).size
            panel = el == "PhotoPanel"
            k = 1080 / h if panel else max(1920 / w, 1080 / h)
            if k > 1.3:
                up.append(f"- {f} `{at[:50]}` {m}: {w}x{h} shown at {k:.1f}x its pixels")
    op = v.folder / "OPINIONS.md"
    # the creator's verdicts on coherence, both sides (cases/COHERENCE.md: what they called coherent and what not): every reader
    # calibrates on them before it flags anything
    cb = REPO / "cases" / "COHERENCE.md"
    cases = cb.read_text(encoding="utf-8") if cb.exists() else "(none yet)"
    text = [f"# Coherency packet: {v.id} (stamp {st})", "", "## The rubric", "", RUBRIC, "",
            "## The creator's verdicts so far: the line they draw (read these first; flag what they would flag, pass what they passed)", "",
            cases, "", "## The script, in order", ""] + script + [
        "", "## The creator's interview (the questions their opinions answer)", "", op.read_text(encoding="utf-8") if op.exists() else "(none)", "",
        "## Real voices in the film (each plays right after its lead-in)", ""] + (ins or ["(none)"]) + [
        "", "## Every gloss (S8: one per term in the whole video)", ""] + (gl or ["(none)"]) + [
        "", "## Stills shown bigger than their pixels (A8, over 1.3x)", ""] + (up or ["(none)"]) + [
        "", "## The shot table (code order within each beat: file | the anchor the shot starts on | what it shows | media | credit)", "",
        "| file | starts on | picture | media | credit |", "|---|---|---|---|---|"] + rows
    (d / "packet.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print(f"packet -> {d / 'packet.md'} ({len(script)} lines, {len(rows)} shots, {len(ins)} real voices); stamp {st}")
    return st


# sources the creator banned from every video (banned_sources.json, a list of regexes): any credit or source path in the video's code or
# prep files that matches one fails the gate, whatever the read says. Case-sensitive by default (a short token in capitals would
# otherwise match variable names): wrap a part in (?i:...) to match any case
BANNED_SOURCES = HERE / "banned_sources.json"


def banned_rx():
    pats = [p for p in _json_list("banned_sources.json") if isinstance(p, str) and p]
    return re.compile("|".join(f"(?:{p})" for p in pats)) if pats else None


def banned(v):
    rx = banned_rx()
    if rx is None:
        return []
    hits = []
    files = code_files(v) + sorted(MOTION.glob(f"prep{v.src.lstrip('v')}*.py"))
    for f in files:
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            c = re.split(r"\s#\s|\s//\s", ln, maxsplit=1)[0]     # a comment may say what a shot replaced; the code and credits may not
            if rx.search(c) and not ln.lstrip().startswith(("//", "#")):
                hits.append(f"{f.name}:{i}: {ln.strip()[:140]}")
    return hits


BANNED_PICS = Path(__file__).resolve().parent / "banned_pictures.json"


def dhash(path):
    """a 64-bit difference hash of a picture (9x8 grey): the same picture at another size, crop margin or file name hashes within a few bits"""
    from PIL import Image
    g = np.asarray(Image.open(path).convert("L").resize((9, 8), Image.LANCZOS), dtype=np.int16)
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def banned_pictures(v):
    """pictures the creator banned from every video (banned_pictures.json holds each one's hash): every image file the video's code
    names (its img/ and pages/, by file name or page name) is hashed and held against the list, so a copy under a new name or size is
    caught too"""
    ban = json.loads(BANNED_PICS.read_text(encoding="utf-8")) if BANNED_PICS.exists() else []
    if not ban:
        return []
    text = "\n".join(f.read_text(encoding="utf-8") for f in code_files(v))
    hits = []
    for sub in ("img", "pages"):
        for f in sorted((PUBLIC / v.src / sub).glob("*")):
            if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp") or (f.name not in text and f"\"{f.stem}\"" not in text
                                                                              and f"'{f.stem}'" not in text):
                continue
            h = dhash(f)
            for b in ban:
                d = bin(h ^ int(b["dhash"], 16)).count("1")
                if d <= 8:
                    hits.append(f"{v.src}/{sub}/{f.name}: {b['what']} ({d} bits from it; {b['rule']})")
    return hits


def pending(v):
    """clips the code plays that were never cut (a builder stopped mid-task leaves a clip uncut, and the shot renders as the grey
    "pending" card; the static audit doesn't count it)"""
    durs = json.loads((MOTION / "src" / "clipdurs.json").read_text(encoding="utf-8"))
    names = set()
    cl = f"{v.src}/clips/"
    for f in code_files(v):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"export const CL\s*=\s*['\"]([^'\"]+)['\"]", t)
        if m:
            cl = m.group(1)      # a composition sharing another's media (a second part playing v12/clips/)
        names |= set(re.findall(r"Ft\(\s*'([a-z0-9_]+)'", t)) | set(re.findall(r"\b[ab]=\"([a-z0-9]+_[a-z0-9_]+)\"", t))
        for hm in re.finditer(r"^\s*(?:ft2?)\(", t, re.M):     # ft(at, 'clip', ...) / ft2(at, 'a', 'b', ...)
            rest = t[hm.end():hm.end() + 400]
            rest = rest[len(first_arg(rest)):]
            names |= set(re.findall(r"^,\s*'([a-z0-9]+_[a-z0-9_]+)'(?:,\s*'([a-z0-9]+_[a-z0-9_]+)')?", rest)[0]) - {""} \
                if re.match(r",\s*'[a-z0-9]+_", rest) else set()
    pages = set()      # TwoPages' a=/b= are captured pages, not clips
    for p in (MOTION / "src").glob("*/pages*.json"):
        try:
            pages |= set(json.loads(p.read_text(encoding="utf-8")))
        except (ValueError, TypeError):
            pass
    return sorted(n for n in names if f"{cl}{n}.mp4" not in durs and n not in pages)


def check(v):
    rep = v.folder / "COHERENCY.md"
    st = stamp(v)
    miss = pending(v)
    if miss:
        print(f"COHERENCY FAIL: {len(miss)} clip(s) the code plays were never cut (they render as 'pending'): {', '.join(miss)}")
        return 1
    bad = banned(v)
    for h in bad:
        print("  banned source:", h)
    if bad:
        print(f"COHERENCY FAIL: {len(bad)} use(s) of a banned source (banned_sources.json)")
        return 1
    pics = banned_pictures(v)
    for h in pics:
        print("  banned picture:", h)
    if pics:
        print(f"COHERENCY FAIL: {len(pics)} banned picture(s) in the video (banned_pictures.json)")
        return 1
    if not rep.exists():
        print(f"COHERENCY: no read yet ({rep}): run `coherency.py packet {v.id}` and a fresh read")
        return 1
    t = rep.read_text(encoding="utf-8")
    m = re.search(r"stamp:\s*([0-9a-f]{16})", t)
    if not m or m.group(1) != st:
        print(f"COHERENCY: the read is of another version (its stamp {m.group(1) if m else 'none'}, now {st}): read it again")
        return 1
    open_ = [ln for ln in t.splitlines() if ln.strip().startswith("- [ ]")]
    for ln in open_:
        print("  open:", ln.strip()[:200])
    print(f"COHERENCY {'PASS' if not open_ else 'FAIL'}: {len(open_)} open flag(s) (stamp {st})")
    return 1 if open_ else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["packet", "check", "stamp"])
    ap.add_argument("video")
    a = ap.parse_args()
    v = Video(find_video(a.video))
    if a.step == "packet":
        packet(v)
    elif a.step == "stamp":
        print(stamp(v))
    else:
        sys.exit(check(v))


if __name__ == "__main__":
    main()
