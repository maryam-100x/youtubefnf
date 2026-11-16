"""Shorts captions: ASS subtitles burned in by libass (tools/motion/finish_short.py calls plan() and write()). 1-2 words per chunk at ONE fixed size, mid-screen, each chunk pops in; *key* words in the accent colour; **hero** phrases
fill the screen (big, bouncing in) exactly when spoken, with a hit SFX cue. Text = what the audio says (captions.words_verified)."""
import re

from .core import font, rgb

SENT_END = ".?!…"
WEAK = set("a an the to of at for and but or in on with from by is are was it's that this his her its their my your".split())


def shown(word):
    """What a caption shows for a word: no sentence punctuation in on-screen captions, question marks
    stay. Apostrophes and hyphens inside a word are part of it ("THAT'S", "FOURTEEN-FORTY")."""
    w = re.sub(r"[;:!…\"“”]", "", word)
    w = re.sub(r"(?<!\d)[.,]|[.,](?!\d)", "", w).strip("-")  # a comma or point between digits stays ("53,000", "1.5")
    return w or word


def ass_colour(hexstr):
    r, g, b = rgb(hexstr)[:3]
    return f"&H00{b:02X}{g:02X}{r:02X}"


def em_scale(ttf):
    """libass sizes a font by its full line height (OS/2 winAscent + winDescent), PIL by the em, so the same number draws
    Anton at 58% of the size in the ASS. ASS Fontsize = PIL size * this (Anton: 1.733, measured 1.735 on a render)."""
    import struct
    data = open(ttf, "rb").read()
    tabs = {data[12 + 16 * i:16 + 16 * i]: struct.unpack(">I", data[20 + 16 * i:24 + 16 * i])[0]
            for i in range(struct.unpack(">H", data[4:6])[0])}
    upm = struct.unpack(">H", data[tabs[b"head"] + 18:tabs[b"head"] + 20])[0]
    win_ascent, win_descent = struct.unpack(">HH", data[tabs[b"OS/2"] + 74:tabs[b"OS/2"] + 78])
    return (win_ascent + win_descent) / upm


def ass_time(t):
    cs = max(0, int(round(t * 100)))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def esc(s):
    return s.replace("\\", "/").replace("{", "(").replace("}", ")")


def plan(ctx, words, quiet=()):
    """-> (chunks, heroes). chunk = {start, end, words:[(text, emph)]}; hero = {start, end, text}."""
    c, v, b = ctx.cfg["captions"], ctx.cfg["visuals"], ctx.cfg["brand"]
    size = int(ctx.H * v["caption_size"])
    f = font(ctx.cfg, "heavy", size)
    max_w = ctx.W * v.get("caption_w", 0.62)
    up = (lambda s: s.upper()) if b.get("caption_upper", True) else (lambda s: s)
    n, brk = len(words), SENT_END + ",;:"
    fits = lambda ws: f.getlength(up(" ".join(x["w"] for x in ws))) <= max_w
    # b continues a's phrase, never across a gap: a word a stamp or captions_hide took out leaves one, and a chunk joined over it would
    # run under the stamp (speech gaps are ~0.07 s in a Short, 0.25 s at most in long form)
    joined = lambda a, b: b["beat"] == a["beat"] and a["w"][-1] not in brk and b["start"] - a["end"] <= 0.3

    pair = {str(x).upper() for x in c.get("pair_with_number", [])}

    def name_pair(k):
        """A name followed by its number ('iPhone 17', 'Model 3', 'Rocky IV'): one caption, never 'IPHONE | 17'. The names are
        [captions] pair_with_number (a name read apart from its number reads as two things)."""
        if not pair or k + 1 >= n or words[k]["w"].strip(".,;:?!\"'").upper() not in pair or not joined(words[k], words[k + 1]):
            return False
        num = words[k + 1]["w"].strip(".,;:?!\"'…").upper()
        return num.isdigit() or num in {"I", "II", "III", "IV", "V", "VI", "VII"}

    def options(i):
        """Where a chunk starting at word i may end (exclusive)."""
        opts = raw_options(i)
        keep = [j for j in opts if not name_pair(j - 1)]  # never end a chunk on a paired name when its number follows
        return keep or [j + 1 if name_pair(j - 1) else j for j in opts]

    def raw_options(i):
        w = words[i]
        if name_pair(i):
            return [i + 2]
        if w.get("emph") == "key":  # a key phrase ("iPhone 17", "Model 3 Pro?") stays whole as long as it fits
            j = i + 1
            while j < n and words[j].get("emph") == "key" and joined(words[j - 1], words[j]) and fits(words[i:j + 1]):
                j += 1
            return [j]
        nxt, after = (words[i + 1] if i + 1 < n else None), (words[i + 2] if i + 2 < n else None)
        lone_key = (nxt and nxt.get("emph") == "key"  # "at *Paris*" pairs; "is *iPhone 17*" doesn't
                    and not (after and after.get("emph") == "key" and joined(nxt, after)))
        if (nxt and c.get("chunk_words", 2) >= 2 and (nxt.get("emph") is None or lone_key) and joined(w, nxt)
                and nxt["end"] - w["start"] <= 1.2 and fits([w, nxt])):
            return [i + 1, i + 2]
        return [i + 1]

    def cost(i, j):
        """1 per chunk (fewer = calmer), +0.8 if it breaks a phrase after 'the/at/…' or a bare number ('AT 350 | DEGREES')."""
        last = words[j - 1]
        k = last["w"].lower().strip(".,;:?!…\"'")
        open_end = j < n and joined(last, words[j]) and words[j].get("emph") != "hero"
        return 1 + 0.8 * (open_end and (k in WEAK or k.isdigit()))

    best, choice = [0.0] * (n + 1), [0] * n
    for i in range(n - 1, -1, -1):
        if words[i].get("emph") in ("hero", "pop"):  # a hero pop, or words a picture pop-in stands for (no caption)
            j = i + 1
            while j < n and words[j].get("emph") == words[i]["emph"]:
                j += 1
            best[i], choice[i] = best[j], j
        else:
            best[i], choice[i] = min((cost(i, j) + best[j], j) for j in options(i))
    chunks, heroes, gaps, i = [], [], [], 0
    while i < n:
        cur, i = words[i:choice[i]], choice[i]
        if cur[0].get("emph") == "hero":
            heroes.append({"start": cur[0]["start"], "end": cur[-1]["end"] + c.get("hero_hold", 0.3),
                           "text": up(" ".join(shown(x["w"]) for x in cur))})
        elif cur[0].get("emph") == "pop":
            gaps.append({"start": cur[0]["start"], "end": cur[-1]["end"]})
        else:
            chunks.append({"start": cur[0]["start"], "end": cur[-1]["end"], "words": [(up(shown(x["w"])), x.get("emph")) for x in cur]})
    events = sorted([dict(e, kind="chunk") for e in chunks] + [dict(e, kind="hero") for e in heroes] +
                    [dict(e, kind="pop") for e in gaps], key=lambda e: e["start"])
    for a, bb in zip(events, events[1:]):  # hold each caption until the next one (no flicker); never two texts at once
        if a["kind"] == "chunk" and bb["start"] - a["end"] < 0.5:
            a["end"] = bb["start"]
        a["end"] = min(a["end"], bb["start"])
    chunks = [e for e in events if e["kind"] == "chunk"]
    heroes = [e for e in events if e["kind"] == "hero"]
    return hush(chunks, heroes, quiet)


def hush(chunks, heroes, quiet):
    """No captions while a graphic says it (the same words twice at once): quiet = [(a, b)] seconds. A chunk mostly inside a quiet
    stretch goes, one partly inside is trimmed to its edge; a hero pop starting inside goes (its hit SFX with it)."""
    if not quiet:
        return chunks, heroes
    inside = lambda a, b: sum(max(0.0, min(b, qb) - max(a, qa)) for qa, qb in quiet)
    kept = []
    for c in chunks:
        if inside(c["start"], c["end"]) > 0.5 * (c["end"] - c["start"]):
            continue
        for qa, qb in quiet:
            if c["start"] < qa < c["end"]:
                c["end"] = qa
            if c["start"] < qb < c["end"] and qa <= c["start"]:
                c["start"] = qb
        if c["end"] - c["start"] > 0.05:
            kept.append(c)
    return kept, [h for h in heroes if not any(qa <= h["start"] < qb for qa, qb in quiet)]


def write(ctx, chunks, heroes, path):
    v, b = ctx.cfg["visuals"], ctx.cfg["brand"]
    size = int(ctx.H * v["caption_size"])
    hero_size = int(size * v.get("hero_scale", 2.3))
    ol = max(4, int(size * 0.09))
    white, key, outline = ass_colour(b["caption_color"]), ass_colour(b.get("caption_key", b["yellow"])), ass_colour(b["outline"])
    fam = b["fonts"]["heavy"].split(":")[0]
    x, y, hy = ctx.W // 2, int(ctx.H * v["caption_y"]), int(ctx.H * v.get("hero_y", 0.42))
    hf = font(ctx.cfg, "heavy", hero_size)
    k = em_scale(hf.path)  # sizes below are PIL sizes (what plan() measured); the ASS needs them in its own unit
    # YCbCr Matrix: None = colours are plain RGB. Without it libass assumes TV-range subtitles and dims them on the transparent
    # Resolve layer (the caption yellow 255,210,31 came out 235,196,43); the burned-in MP4 is the same either way.
    lines = ["[Script Info]", "ScriptType: v4.00+", "YCbCr Matrix: None", f"PlayResX: {ctx.W}", f"PlayResY: {ctx.H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
             "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: Cap,{fam},{round(size * k)},{white},{white},{outline},&H80000000,0,0,0,0,100,100,1,0,1,{ol},0,5,0,0,0,1",
             f"Style: Hero,{fam},{round(hero_size * k)},{key},{key},{outline},&H80000000,0,0,0,0,100,100,2,0,1,{int(ol * 1.8)},0,5,0,0,0,1",
             "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    pop = r"\fscx70\fscy70\t(0,70,\fscx108\fscy108)\t(70,140,\fscx100\fscy100)"
    for c in chunks:
        txt = " ".join(f"{{\\c{key}}}{esc(t)}{{\\c{white}}}" if e == "key" else esc(t) for t, e in c["words"])
        lines.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Cap,,0,0,0,,{{\\an5\\pos({x},{y}){pop}}}{txt}")
    for h in heroes:
        room = min(ctx.W * 0.9, 2 * (v.get("safe_right", ctx.W) - ctx.W / 2) / 1.07)  # clear of the like/comment column, even at the 107% bounce
        fit = min(100, int(100 * room / max(hf.getlength(h["text"]), 1)))  # a long hero phrase shrinks to fit
        # the pop-in measured on strong reference Shorts: 83% -> 107% in 4 frames with motion blur on the first 2, settled at 100% by 200 ms
        pop, settle = v.get("hero_pop_ms", 67), v.get("hero_settle_ms", 200)
        a, o = int(fit * v.get("hero_pop_from", 0.83)), int(fit * v.get("hero_pop_over", 1.07))
        bounce = (rf"\blur6\fscx{a}\fscy{a}\t(0,{pop},\fscx{o}\fscy{o})\t(0,{pop // 2},\blur0)"
                  rf"\t({pop},{settle},\fscx{fit}\fscy{fit})")
        lines.append(f"Dialogue: 1,{ass_time(h['start'])},{ass_time(h['end'])},Hero,,0,0,0,,{{\\an5\\pos({x},{hy}){bounce}}}{esc(h['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(ctx, words, quiet=(), pops=()):
    """pops = [(w0, w1)]: words spoken there are shown by a picture pop-in instead of a caption."""
    inside = lambda w: any(a - 0.01 <= (w["start"] + w["end"]) / 2 <= b + 0.01 for a, b in pops)
    words = [dict(w, emph="pop") if inside(w) else w for w in words]
    chunks, heroes = plan(ctx, words, quiet)
    p = write(ctx, chunks, heroes, ctx.path("captions", "captions_v2.ass"))
    ctx.save_json("captions/events_v2.json", {"chunks": chunks, "heroes": heroes})
    return p, chunks, heroes
