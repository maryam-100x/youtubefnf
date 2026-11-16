"""Parse script.md: title options, fact IDs, the machine-readable `## Beats` block, and sanity checks.

  cd tools && PIPE -m dj parse ../videos/<video>      prints the beats and their shots, warns about faults -> build/script.json

The Beats block (a fenced block under `## Beats`): `[S01] VOICE: <the words>` per beat (a long line may continue on the next line),
`[S02] HOLD: 1.5` a pause without voice whose shots and sound play on, and under a beat optional VIS: / POP: / HUSH: / MUSIC: lines
(below). VOICE markup: *word* = a key word (accent colour in the captions), **words** = a hero pop."""
import difflib
import re

BEAT_RE = re.compile(r"^\[(S\d+[a-z]?)\]\s*VOICE:\s*(.*)$")
HOLD_RE = re.compile(r"^\[(S\d+\w*)\]\s*HOLD:\s*([\d.]+)\s*(join)?\s*$")  # a pause without voice: its shots + sound play on
KEYS = {"zoom", "text", "todo", "chapter", "fit", "crop", "on", "trans", "punch", "focus", "sfx", "label", "sub", "style", "dur", "bg", "captions", "mark", "marked", "pan", "ring", "sound", "arrow", "from", "to", "hold", "y", "sfx_at", "alen", "cuts"}
STYLES = {"badge", "sticker"}  # POP lines: a round photo badge, or a picture (logo, cut-out) as it is
SFX = {"whoosh", "pop", "hit", "shutter", "ping", "drop", "rewind", "boom", "riser", "tick", "typing", "glitch", "none"}  # sfx= on a VIS: that sound on the cut into the shot ("none": no sound there)
ZOOMS = {"in", "out", "none", "auto"}
FITS = {"fill", "blur"}
CROPS = {"left": 0.0, "center": 0.5, "centre": 0.5, "right": 1.0}
TRANS = {"whip", "cut"}
ARROW_FROM = {"n", "ne", "e", "se", "s", "sw", "w", "nw"}


def split_fields(s):
    """Split on | outside double quotes."""
    fields, buf, quoted = [], "", False
    for ch in s:
        if ch == '"' and not buf.endswith("\\"):
            quoted = not quoted
        if ch == "|" and not quoted:
            fields.append(buf)
            buf = ""
        else:
            buf += ch
    return fields + [buf]


def tc(s):
    """'04:12' / '1:02:03.5' / '12.5' -> seconds."""
    sec = 0.0
    for part in s.strip().split(":"):
        sec = sec * 60 + float(part)
    return sec


def parse_range(s, vis):
    """'@ 00:30-00:35' = play from 0:30 to 0:35; '@ -00:30' = end at 0:30, starting as early as the shot needs (a looping
    Short's last shot ends on the opening shot's first frame, so the replay continues the same take)."""
    a, _, b = s.strip().lstrip("@").strip().partition("-")
    if not a.strip() and b.strip():
        vis["in"], vis["out"], vis["end_at"] = None, tc(b), True
        return
    vis["in"] = tc(a)
    vis["out"] = tc(b) if b.strip() else None
    if vis["out"] is not None and vis["out"] <= vis["in"]:
        raise ValueError(f"bad in/out range: {s}")


def parse_vis(s):
    vis = {"asset": None, "todo": None, "zoom": "auto", "text": None, "chapter": None, "in": None, "out": None,
           "fit": None, "crop": 0.5,  # fit None = [visuals] short_fit; crop = horizontal position of a fill crop (0 left .. 1 right)
           "on": None, "trans": None, "punch": 1.0, "focus": (0.5, 0.5), "end_at": False, "sfx": None, "pan": None, "ring": None, "sound": None, "arrow": None, "from": None, "to": None,
           "hold": None, "punch_to": None}
    # several VIS lines per beat = several shots: on="phrase" starts a shot on that spoken phrase (else the beat is shared
    # evenly); trans = whip|cut into this shot; punch = zoom factor (1-3) centred on focus="x,y" (0-1, 0,0 = top left)
    for i, f in enumerate(split_fields(s)):
        f = f.strip()
        if not f:
            continue
        if f.startswith("@"):
            parse_range(f, vis)
            continue
        k, eq, v = f.partition("=")
        k = k.strip()
        if eq and re.fullmatch(r"[a-z_]+", k):
            if k not in KEYS:
                raise ValueError(f"unknown VIS key '{k}' in: {s}")
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] == '"':
                v = v[1:-1].replace('\\"', '"')
            if k == "zoom" and v not in ZOOMS:
                raise ValueError(f"zoom must be one of {sorted(ZOOMS)}: {s}")
            if k == "cuts" and v != "keep":
                raise ValueError(f"cuts must be 'keep' (a clip we animated ourselves: no hard-cut guard): {s}")
            if k == "fit" and v not in FITS:
                raise ValueError(f"fit must be one of {sorted(FITS)}: {s}")
            if k == "crop":
                try:
                    v = CROPS[v] if v in CROPS else float(v)
                except ValueError:
                    v = -1.0
                if not 0.0 <= v <= 1.0:
                    raise ValueError(f"crop must be left, center, right or a number 0-1: {s}")
            if k == "text":
                v = None if v.lower() in ("", "none") else v.replace("\\n", "\n")
            if k == "style" and v not in STYLES:
                raise ValueError(f"style must be one of {sorted(STYLES)}: {s}")
            if k == "dur":
                try:
                    v = float(v)
                except ValueError:
                    v = 0.0
                if not 0.3 <= v <= 6:
                    raise ValueError(f"dur must be 0.3-6 seconds: {s}")
            if k == "sfx" and v not in SFX:
                raise ValueError(f"sfx must be one of {sorted(SFX)}: {s}")
            if k == "pan":  # pan=a-b: a 16:9 still in a 9:16 Short, the window slides from crop position a to b (0 left .. 1 right)
                try:
                    v = tuple(float(x) for x in v.split("-"))
                except ValueError:
                    v = ()
                if len(v) != 2 or not all(0.0 <= x <= 1.0 for x in v):
                    raise ValueError(f"pan must be a-b with both 0-1 (e.g. pan=0.1-0.8): {s}")
            if k == "ring":  # ring=r: a red callout ring around the focus point (x,y), radius r of the frame height (long videos)
                try:
                    v = float(v)
                except ValueError:
                    v = 0.0
                if not 0.02 <= v <= 0.5:
                    raise ValueError(f"ring must be a radius 0.02-0.5 (of the frame height): {s}")
            if k == "trans" and v not in TRANS:
                raise ValueError(f"trans must be one of {sorted(TRANS)}: {s}")
            if k == "punch":  # punch=2 or punch=1.8-2.6 (a progressive zoom over the shot, long videos)
                try:
                    a, _, b = v.partition("-")
                    v, vis["punch_to"] = float(a), (float(b) if b else None)
                except ValueError:
                    v = 0.0
                if not 1.0 <= v <= 3.0 or not (vis["punch_to"] is None or 1.0 <= vis["punch_to"] <= 3.0):
                    raise ValueError(f"punch must be a number from 1 to 3 (or a-b): {s}")
            if k == "arrow":  # arrow=gap: a red arrow whose tip stops `gap` (of the frame height) from the focus point (long videos)
                try:
                    v = float(v)
                except ValueError:
                    v = -1.0
                if not 0.0 <= v <= 0.3:
                    raise ValueError(f"arrow must be a gap 0-0.3 (of the frame height): {s}")
            if k == "from" and v not in ARROW_FROM:
                raise ValueError(f"from must be one of {sorted(ARROW_FROM)}: {s}")
            if k == "hold":  # seconds a punch-in holds before easing back to the full frame (0 = stays punched)
                try:
                    v = float(v)
                except ValueError:
                    v = -1.0
                if not 0.0 <= v <= 10:
                    raise ValueError(f"hold must be 0-10 seconds: {s}")
            if k == "sfx_at":  # sfx_at="pop@0.05,0.17": that sound at those seconds into the shot (events inside an animated clip);
                # several kinds with ";": "tick@0.2,0.42;boom@1.3" (a tick per item counted in, a boom on the last)
                groups = []
                for g in v.split(";"):
                    kind, _, ts = g.strip().partition("@")
                    try:
                        ts = tuple(float(x) for x in ts.split(","))
                    except ValueError:
                        ts = ()
                    if kind not in SFX - {"none"} or not ts or not all(0.0 <= t <= 10 for t in ts):
                        raise ValueError(f"sfx_at must be kind@t,t,...[;kind@t,...] (kind one of {sorted(SFX - {'none'})}, 0-10 s): {s}")
                    groups.append((kind, ts))
                v = tuple(groups)
            if k == "alen":  # alen=0.05-0.4: the arrow's length (of the frame height; default 0.11 in Shorts), e.g. an end card pointing at a link
                try:
                    v = float(v)
                except ValueError:
                    v = -1.0
                if not 0.05 <= v <= 0.4:
                    raise ValueError(f"alen must be 0.05-0.4 (of the frame height): {s}")
            if k == "y":  # y=0-1: a POP's vertical centre (Shorts)
                try:
                    v = float(v)
                except ValueError:
                    v = -1.0
                if not 0.1 <= v <= 0.9:
                    raise ValueError(f"y must be 0.1-0.9: {s}")
            if k == "to":  # to=x,y: the camera pans from focus to here over the shot (long videos)
                try:
                    v = tuple(float(x) for x in v.split(","))
                except ValueError:
                    v = ()
                if len(v) != 2 or not all(0.0 <= x <= 1.0 for x in v):
                    raise ValueError(f"to must be x,y with both 0-1: {s}")
            if k == "focus":
                try:
                    v = tuple(float(x) for x in v.split(","))
                except ValueError:
                    v = ()
                if len(v) != 2 or not all(0.0 <= x <= 1.0 for x in v):
                    raise ValueError(f"focus must be x,y with both 0-1: {s}")
            vis[k] = v
        elif i == 0:
            asset, at, rng = f.partition("@")
            vis["asset"] = asset.strip()
            if at:
                parse_range(rng, vis)
        else:
            raise ValueError(f"VIS field not understood: '{f}' in: {s}")
    if not vis["asset"] and not vis["todo"]:
        vis["todo"] = "no visual given"
    return vis


def norm_words(s):
    s = re.sub(r"[’']", "", s.lower())
    return re.sub(r"[^a-z0-9]+", " ", s).split()


def table_voice(text):
    """Voice column of the human `| Time | Voice | On screen |` table, joined."""
    m = re.search(r"^\|\s*Time\s*\|\s*Voice\s*\|.*\n((?:\|.*\n?)*)", text, re.M)
    if not m:
        return None
    cells = [ln.split("|")[2] for ln in m[1].splitlines() if ln.count("|") >= 3 and not re.match(r"^\|\s*-", ln)]
    return " ".join(cells)


def parse_emphasis(voice):
    """VOICE markup: *word* = key word (accent colour in captions), **words** = hero pop (full-screen, with a hit SFX).
    Returns (clean text for TTS/captions, [None|"key"|"hero"] per word of the clean text)."""
    words, marks, state = [], [], None
    for tok in voice.split():
        if tok.startswith("**"):
            state = "hero"
        elif tok.startswith("*") and state is None:
            state = "key"
        clean = tok.replace("*", "")
        if clean:
            words.append(clean)
            marks.append(state)
        if tok.rstrip(".,!?…;:\"')").endswith("*"):
            state = None
    return " ".join(words), marks


def parse_text(text):
    meta = {"titles": [], "facts": [], "thumb": None, "beats": [], "warnings": []}
    m = re.search(r"^## Title options.*?\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if m:
        meta["titles"] = [t.strip() for t in re.findall(r"^\d+\.\s+(.+)$", m[1], re.M)]
    m = re.search(r"Facts:(.*)", text)
    if m:
        meta["facts"] = list(dict.fromkeys(re.findall(r"\b[A-Z]{2,5}-\d{2,3}\b", m[1])))
    m = re.search(r"^## Beats.*?^```[^\n]*\n(.*?)^```", text, re.M | re.S)
    if not m:
        raise ValueError("script.md has no '## Beats' section with a fenced block")
    cur = None
    for raw in m[1].splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        mb = BEAT_RE.match(line)
        mh = HOLD_RE.match(line)
        if mb:
            cur = {"id": mb[1], "voice": mb[2].strip(), "vis": None}
            meta["beats"].append(cur)
        elif mh:
            hold = float(mh[2])
            if not 0.3 <= hold <= 10:
                raise ValueError(f"HOLD must be 0.3-10 seconds: {raw}")
            cur = {"id": mh[1], "voice": "", "hold": hold, "vis": None, "join": bool(mh[3])}
            meta["beats"].append(cur)
        elif line.startswith("VIS:"):
            if not cur:
                raise ValueError(f"VIS without its own [Sxx] VOICE line: {raw}")
            vis = parse_vis(line[4:])
            if cur["vis"] is None:
                cur["vis"], cur["shots"] = vis, [vis]
            else:
                cur["shots"].append(vis)  # another shot in the same beat
        elif line.startswith("THUMB:"):
            meta["thumb"] = parse_vis(line[6:])
        elif line.startswith("POP:"):  # a picture popping in over the shot on a word (POP: <asset> | on="<phrase>")
            if not cur:
                raise ValueError(f"POP without its own [Sxx] VOICE line: {raw}")
            cur.setdefault("pops", []).append(parse_vis(line[4:]))
        elif line.startswith("HUSH:"):  # the music stops while this phrase is spoken (a stylized pause to land a point)
            if not cur:
                raise ValueError(f"HUSH without its own [Sxx] VOICE line: {raw}")
            mo = re.fullmatch(r'on="([^"]+)"', line[5:].strip())
            if not mo:
                raise ValueError(f'HUSH needs on="<phrase as spoken>": {raw}')
            cur.setdefault("hush", []).append(mo[1])
        elif line.startswith("MUSIC:") and (cur is None or not re.search(r"\|\s*under=|^\s*same\b", line[6:])):
            meta["music"] = line[6:].strip()  # this video's music bed (path under assets, e.g. music/<track>.mp3; "none" = no music)
        elif line.startswith("MUSIC:"):  # long videos, per part (a new bed per chapter, its level per section):
            # MUSIC: music/x.mp3 | under=14  starts that track at this beat, ~14 LU under the voice; "same" keeps the running track
            # and only changes the level from here on
            parts = [x.strip() for x in line[6:].split("|")]
            mm = {"file": parts[0], "under": None}
            for q in parts[1:]:
                k, _, v = q.partition("=")
                if k.strip() != "under":
                    raise ValueError(f"MUSIC in a beat takes only under=<LU under the voice>: {raw}")
                mm["under"] = float(v)
            cur["music"] = mm
        elif cur and cur["vis"] is None and not cur.get("hold"):
            cur["voice"] += " " + line  # voice continues on the next line
        else:
            raise ValueError(f"line not understood in Beats block: {raw}")
    ids = [b["id"] for b in meta["beats"]]
    if not ids:
        raise ValueError("Beats block is empty")
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate beat ids: {ids}")
    for b in meta["beats"]:
        b["vis"] = b["vis"] or parse_vis("")
        b["shots"] = b.get("shots") or [b["vis"]]
        b["voice"], b["emph"] = parse_emphasis(b["voice"])
        if not b["voice"] and not b.get("hold"):
            raise ValueError(f"{b['id']} has no VOICE text")
        check_shots(b)
        if re.search(r"\[[^\]]*\]", b["voice"]):
            meta["warnings"].append(f"{b['id']} voice has a placeholder to fill in: {b['voice']}")
    tv = table_voice(text)
    if tv is not None:
        a, bw = norm_words(tv), norm_words(" ".join(b["voice"] for b in meta["beats"]))
        if a != bw:
            sm = difflib.SequenceMatcher(a=a, b=bw, autojunk=False)
            diffs = [f"table '{' '.join(a[i1:i2])}' vs beats '{' '.join(bw[j1:j2])}'"
                     for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
            meta["warnings"].append("Beats voice differs from the table: " + "; ".join(diffs[:5]))
    return meta


def phrase_at(words, phrase, start=0):
    """Index of the first word of `phrase` in `words` (compared as norm_words, so "iPhone 17 Pro?" = "iphone 17 pro"), from `start`, or None."""
    keys, want = [norm_words(w) for w in words], norm_words(phrase)
    for i in range(start, len(words)):
        j, k = i, 0
        while j < len(words) and k < len(want) and keys[j] and keys[j] == want[k:k + len(keys[j])]:
            k, j = k + len(keys[j]), j + 1
        if want and k == len(want):
            return i
    return None


def check_shots(b):
    """on= phrases must be in this beat's voice, in order; the first shot starts with the beat."""
    if b["shots"][0]["on"]:
        raise ValueError(f"{b['id']}: the first VIS starts with the beat; on= is for the later ones")
    words, pos = b["voice"].split(), 0
    for v in b["shots"]:
        if v["on"]:
            i = phrase_at(words, v["on"], pos)
            if i is None:
                raise ValueError(f"{b['id']}: on=\"{v['on']}\" is not in the voice (after the previous shot's phrase)")
            pos = i + 1
    pos = 0
    for p in b.get("pops", []):  # a POP needs its word, in order
        i = phrase_at(words, p["on"], pos) if p["on"] else None
        if i is None:
            raise ValueError(f"{b['id']}: POP {p['asset']} needs on=\"...\" with a phrase from the voice (in order)")
        pos = i + 1


def load(ctx):
    return parse_text((ctx.video / "script.md").read_text(encoding="utf-8"))


def run(ctx):
    meta = load(ctx)
    for w in meta["warnings"]:
        ctx.warn(w)
    s, voice = ctx.cfg["script"], " ".join(b["voice"] for b in meta["beats"])
    lines = [x for x in (s.get("opener", ""), s.get("signoff", "")) if norm_words(x)]  # [script] in config/tts.toml; "" = no check
    has = [" ".join(norm_words(x)) in " ".join(norm_words(voice)) for x in lines]
    if ctx.fmt == "long" and not all(has):
        ctx.warn(f"long-form script lacks the opener '{s.get('opener', '')}' or the sign-off '{s.get('signoff', '')}'")
    if ctx.fmt == "short" and any(has):
        ctx.warn("Shorts get no opener or sign-off (they end on the loop line)")
    ctx.save_json("script.json", meta)
    words = sum(len(b["voice"].split()) for b in meta["beats"])
    wpm = ctx.cfg["tts"]["wpm"]
    print(f"  {len(meta['beats'])} beats, {words} words (~{words / wpm * 60:.0f} s at {wpm} wpm), format {ctx.fmt} {ctx.W}x{ctx.H}")
    for b in meta["beats"]:
        for k, v in enumerate(b["shots"]):
            src = f"TODO: {v['todo']}" if v["todo"] else (v["asset"] + ("" if ctx.resolve_asset(v["asset"]) else "  (MISSING)"))
            print(f"  {b['id'] if k == 0 else '   '}  {src}" + (f'  on="{v["on"]}"' if v["on"] else "")
                  + (f"  text={v['text']!r}" if v["text"] else ""))
    return meta


def load_beats(ctx):
    """Fresh VIS info from script.md merged with the timing from `tts` (beats.json)."""
    meta = load(ctx)
    timing = ctx.load_json("beats.json", "tts")
    by_id = {b["id"]: b for b in timing["beats"]}
    beats = []
    for b in meta["beats"]:
        t = by_id.get(b["id"])
        # a prototype's narration (tools/voice/proto_narration.py, before the full voice exists) holds only its own beats: the script's
        # other beats aren't voiced yet and are left out of the captions, the sync and the gate (beats.json says "prototype")
        if not t and timing.get("prototype"):
            continue
        if not t or t["voice"] != b["voice"]:
            raise SystemExit(f"{b['id']}: voice changed since the last `tts` run; run `cd tools && PIPE -m dj tts ../videos/{ctx.slug}` again")
        beats.append({**t, "vis": b["vis"], "shots": b["shots"], "pops": b.get("pops", []), "emph": b["emph"],
                      "hush": b.get("hush", []), "music": b.get("music")})
    return meta, timing, beats
