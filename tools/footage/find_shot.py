"""Find the shot for a line, out of everything the brain knows (kb/footage/brain/*.json): ranked spans with frame-accurate in/out,
their flags and the 9:16 window, by the line's words plus local embeddings (the record's words by meaning, the picture by CLIP; CPU,
no API). Every option looked at, and the window placed on the subject, made into a tool.

  EDIT tools/footage/find_shot.py "the moment the lid comes off" [options]
    --vertical            rank for a Short: shots whose subject a 9:16 window holds (fit ok/tight), wide shots down
    --min-dur 1.5         clean span at least this long (seconds)
    --exclude-used v11,v12   leave out spans a delivered edit already played (ASSET_LEDGER.json via the records' used_in)
    --src A1,LIB1         only these sources (the keys of kb/footage/sources.json)
    --n 12                how many hits
    --sheet out.jpg       a contact sheet of the hits: each shot's start, middle and end frame with its window drawn in red, and
                          (--vertical) the window itself
    --no-embed            keywords only (no model loads; instant)
    --json                print the hits as JSON (for scripts)
Output: one line per hit: rank, score, id, in-out, clean span, dur, flags, who, the description, the window (cx cy h [-> cx1 cy1] fit),
used in.

The creator's own words map onto the words records use through kb/footage/synonyms.json ({"their word": "the record's word"}), on top
of the common synonyms below.

The picture counts too:
  - the real footage first: a source marked `art` in sources.json (illustrated key art, posters) ranks ART_DEMOTE lower unless the
    line asks for art (art, artwork, poster, wallpaper);
  - no murky pick: each record's light is measured on its own frames inside the clean span (mean, 95th percentile, the brightest of
    12 x 8 blocks: the render gate's dark-shot measure), a murky record that is not a night shot ranks MURKY_DEMOTE lower; inside a
    record the murky stretch is found frame by frame (the brain's per-frame light), and the hit prints its lit span and its murky one
    (a record's only usable window can be its lit part); the brain's "dark" flag no longer costs a night shot;
  - the named thing big and central: when the line names the record's subject (its label or who), a subject box that fills
    SUBJECT_BIG of the frame with its centre inside the middle 44% ranks SUBJECT_BONUS higher, a small or off-centre one SUBJECT_MALUS
    lower."""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402

EMB = B.BRAIN / "embeddings.npz"
STOP = set("a an the of in on at to for and or with his her their its it this that these those is are was were be been being as by from into onto over "
           "under up down out off you your yours we our they them he she him i me my if when while then than so too very just can could will would "
           "should may might do does did done has have had having not no nor s t re ve ll d get got gets getting go goes went going one some any all "
           "there here where who whom which what how why also like about around through during before after above below between again further once "
           "only own same such but because until both each few more most other each every".split())
SYN = {"kid": "child", "kids": "child", "children": "child", "toddler": "child", "lady": "woman", "women": "woman", "men": "man",
       "doctor": "doctor", "doc": "doctor", "physician": "doctor", "automobile": "car", "cars": "car", "bike": "bicycle", "bikes": "bicycle",
       "cycling": "bicycle", "cyclist": "bicycle", "cash": "money", "dollars": "money", "bucks": "money",
       "cooking": "cook", "cooks": "cook", "chef": "cook", "baking": "bake", "bakes": "bake", "baked": "bake", "stove": "oven",
       "skillet": "pan", "veggies": "vegetable", "vegetables": "vegetable", "espresso": "coffee", "latte": "coffee",
       "woods": "forest", "trees": "tree", "mountains": "mountain", "hill": "mountain", "creek": "river", "pond": "lake", "ocean": "sea",
       "waves": "wave", "snowy": "snow", "sunrise": "dawn",
       "evening": "sunset", "dusk": "sunset", "golden": "sunset", "laptop": "computer", "desktop": "computer", "monitor": "screen",
       "display": "screen", "cam": "camera", "lens": "camera", "quadcopter": "drone",
       "soccer": "football", "goals": "goal", "scored": "goal", "jogging": "running", "runner": "running", "sprint": "running",
       "plane": "airplane", "planes": "airplane", "jet": "airplane", "flight": "airplane", "trains": "train", "railway": "train",
       "luggage": "suitcase", "lab": "laboratory", "experiment": "laboratory", "fortress": "castle", "ruins": "ruin",
       "dog": "dog", "dogs": "dog", "puppy": "dog", "kitten": "cat", "bird": "bird", "birds": "bird", "horses": "horse",
       "store": "store", "shop": "store", "market": "store",
       "money": "money", "phone": "phone", "cellphone": "phone", "smartphone": "phone", "guitars": "guitar", "singer": "singing",
       "sings": "singing", "sang": "singing", "gig": "concert", "concerts": "concert", "garden": "garden", "yard": "garden",
       "house": "house", "home": "house", "apartment": "house", "rain": "rain", "raining": "rain", "night": "night", "books": "book"}


def _own_synonyms():
    try:
        d = json.loads(B.SYNONYMS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {str(k).lower(): str(v).lower() for k, v in d.items()} if isinstance(d, dict) else {}


SYN.update(_own_synonyms())


def stem(w):
    w = w.lower()
    w = SYN.get(w, w)
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            w = w[: -len(suf)]
            break
    return w


def tokens(text):
    return [stem(w) for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and len(w) > 1]


def load_records(srcs=None):
    recs = []
    for p in sorted(B.BRAIN.glob("*.json")):
        if p.name in ("embeddings.npz",):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for r in d.get("shots", []):
            code = r["src"] if r["src"] in B.MASTERS or r["src"] in B.STILLS else r["id"].split("/")[0]
            if srcs and code not in srcs:
                continue
            r["_code"] = code
            recs.append(r)
    return recs


def rec_words(r):
    """Weighted bag of the record's words: who and what count double, the description and the catalogue's notes once."""
    bag = {}
    for field, wgt in (("desc", 1.0), ("action", 1.0), ("setting", 0.8), ("time", 0.6), ("mood", 0.6), ("subject", 1.2)):
        v = r.get(field, "")
        if isinstance(v, dict):
            v = v.get("label", "")
        for t in tokens(str(v)):
            bag[t] = max(bag.get(t, 0), wgt)
    for field in ("who", "what"):
        for t in tokens(" ".join(r.get(field, []))):
            bag[t] = max(bag.get(t, 0), 1.5)
    for c in r.get("cat", []):
        for t in tokens(f"{c[1]} {c[2]}"):
            bag[t] = max(bag.get(t, 0), 0.9)
    for t in tokens(" ".join(r.get("text", []))):
        bag[t] = max(bag.get(t, 0), 0.7)
    for m in r.get("moments", []):
        for t in tokens(m.get("note", "")):
            bag[t] = max(bag.get(t, 0), 1.0)
    for f in r.get("facts", []):   # the research facts the shot shows
        for t in tokens(f"{f.get('fact', '')} {f.get('note', '')}"):
            bag[t] = max(bag.get(t, 0), 0.8)
    for t in tokens((r.get("ui") or {}).get("read", "")):   # an on-screen interface read off a full-resolution zoom
        bag[t] = max(bag.get(t, 0), 1.0)
    return bag


# ------------------------------------------------------------------------------------------------- the picture: art, light, subject
ART_WORDS = {"art", "artwork", "keyart", "poster", "wallpaper", "illustration", "painting", "painted", "drawing"}
ART_DEMOTE = 0.6
MURKY = (14.0, 64.0, 90.0)     # mean, 95th percentile, brightest block: the render gate's dark-shot thresholds
MURKY_DEMOTE = 0.5
MURKY_FRAME = 14.0             # the brain's per-frame light (RGB mean at 128x72) under this is a murky frame
SUBJECT_BIG = 0.06             # a subject box on 6%+ of the frame ...
SUBJECT_CENTRE = 0.22          # ... its centre within 22% of the middle
SUBJECT_BONUS, SUBJECT_MALUS = 0.15, 0.2   # the brain's boxes are coarse (whole people, a whole seat): the malus is the sharper signal
LIGHT = B.WORK / "work" / "light.json"
_LIGHT = {"data": None, "dirty": 0}
_FEAT = {}


def is_art(r):
    return r.get("_code") in B.ART


def frame_light(key, f):
    """The light (mean, 95th percentile, brightest block) of one brain frame (WORK/frames/<key>/NNNNNNN.jpg, 1280 wide), cached in
    WORK/work/light.json"""
    if _LIGHT["data"] is None:
        try:
            _LIGHT["data"] = json.loads(LIGHT.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _LIGHT["data"] = {}
    k = f"{key}/{f}"
    if k not in _LIGHT["data"]:
        p = B.WORK / "frames" / B.key_file(key) / f"{f:07d}.jpg"
        if not p.exists():
            return None
        from PIL import Image
        im = Image.open(p)
        im.draft("RGB", (384, 216))
        a = np.asarray(im.convert("RGB").resize((192, 108)), np.float32)
        y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        blocks = y[:104, :192].reshape(8, 13, 12, 16).mean(axis=(1, 3))
        _LIGHT["data"][k] = [round(float(y.mean()), 1), round(float(np.percentile(y, 95)), 1), round(float(blocks.max()), 1)]
        _LIGHT["dirty"] += 1
    return _LIGHT["data"][k]


def save_light():
    if _LIGHT["dirty"]:
        LIGHT.parent.mkdir(parents=True, exist_ok=True)
        tmp = LIGHT.with_suffix(".tmp")
        tmp.write_text(json.dumps(_LIGHT["data"]), encoding="utf-8")
        tmp.replace(LIGHT)
        _LIGHT["dirty"] = 0


def record_light(r):
    """(median mean, p95, bright block) of the record's own frames inside its clean span, and whether that reads murky (not a night shot)"""
    key = r["src"] if r["src"] in B.MASTERS or r["src"] in B.STILLS else r["id"].split("@")[0]
    if r.get("kind") == "image":
        fl = r.get("frames", [])
    else:
        fps = r.get("fps", 30)
        fl = [f for f in r.get("frames", []) if r.get("clean_in", r["in"]) * fps - 1 <= f <= r.get("clean_out", r["out"]) * fps + 1] or r.get("frames", [])
    st = [s for s in (frame_light(key, f) for f in fl) if s]
    if not st:
        return None, False
    m = [float(np.median([s[i] for s in st])) for i in range(3)]
    murky = m[0] < MURKY[0] and m[1] < MURKY[1] and m[2] < MURKY[2] and r.get("time") != "night"
    return m, murky


def runs_of(mask, value):
    """[(start, end)] index runs where mask == value"""
    out, cur = [], None
    for i, d in enumerate(np.append(mask, not value)):
        if d == value and cur is None:
            cur = i
        elif d != value and cur is not None:
            out.append((cur, i))
            cur = None
    return out


def lit_span(r):
    """for a video record: (lit_in, lit_out, [(murky_in, murky_out), ...]) when part of its clean span is murky for 0.5 s or more (the
    brain's per-frame light, smoothed over 0.5 s): the longest lit stretch to cut from and the murky ones; else None"""
    if r.get("kind") == "image" or r["src"] not in B.MASTERS:
        return None
    if r["src"] not in _FEAT:
        p = B.WORK / "work" / f"{B.key_file(r['src'])}_feat.npz"
        _FEAT[r["src"]] = np.load(p)["luma"] if p.exists() else None
    L = _FEAT[r["src"]]
    if L is None:
        return None
    fps = r.get("fps", 30)
    a, b = int(round(r.get("clean_in", r["in"]) * fps)), int(round(r.get("clean_out", r["out"]) * fps))
    seg = L[a:b]
    if len(seg) < fps:
        return None
    k = max(1, int(fps / 2))
    sm = np.convolve(seg, np.ones(k) / k, mode="same")
    dark = sm < MURKY_FRAME
    murk = [(x, y) for x, y in runs_of(dark, True) if y - x >= fps / 2]
    lit = runs_of(dark, False)
    if not murk or not lit:
        return None
    best = max(lit, key=lambda xy: xy[1] - xy[0])
    return (round((a + best[0]) / fps, 2), round((a + best[1]) / fps, 2), [(round((a + x) / fps, 2), round((a + y) / fps, 2)) for x, y in murk])


def subject_fit(r, q):
    """(area, centre offset) of the record's subject box when the line names it (its label or who), else None"""
    s = r.get("subject") or {}
    names = set(tokens(f"{s.get('label', '')} {' '.join(r.get('who', []))}"))
    if not names & set(q):
        return None
    boxes = [b for b in (s.get("start"), s.get("mid"), s.get("end")) if b]
    if not boxes:
        return None
    area = float(np.mean([(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]))
    off = float(np.mean([max(abs((b[0] + b[2]) / 2 - 0.5), abs((b[1] + b[3]) / 2 - 0.5)) for b in boxes]))
    return area, off


def keyword_score(q_tokens, bag):
    if not q_tokens:
        return 0.0
    hit = sum(bag.get(t, 0.0) for t in set(q_tokens))
    return hit / len(set(q_tokens))


def zscore(x):
    x = np.asarray(x, np.float32)
    s = x.std()
    return (x - x.mean()) / (s if s > 1e-6 else 1.0)


_LOADED = {}   # the embeddings file and the two models, loaded once per process (pick_boards.py searches every line of a script in one run)


def _embedded():
    if "E" not in _LOADED:
        from brain_embed import ClipEmbedder, TextEmbedder
        E = np.load(EMB, allow_pickle=False)
        _LOADED.update(E=E, idx={str(s): i for i, s in enumerate(E["ids"])}, T=E["text"].astype(np.float32),
                       C=E["clip"].astype(np.float32), te=TextEmbedder(), ce=ClipEmbedder())
    return _LOADED


def search(query, recs, use_embed=True, vertical=False, min_dur=0.0, exclude_used=(), n=12):
    q = tokens(query)
    kw = np.array([keyword_score(q, rec_words(r)) for r in recs], np.float32)
    score = kw.copy()
    parts = {"kw": kw}
    if use_embed and EMB.exists() and recs:
        L = _embedded()
        idx = L["idx"]
        rows = [idx.get(r["id"], -1) for r in recs]
        have = np.array([i >= 0 for i in rows])
        T, C = L["T"], L["C"]
        qt = L["te"]([query])[0]
        qc = L["ce"].texts([f"a video frame of {query}"])[0]
        ts = np.array([float(T[i] @ qt) if i >= 0 else 0.0 for i in rows], np.float32)
        cs = np.array([float(C[i] @ qc) if i >= 0 else 0.0 for i in rows], np.float32)
        if have.any():
            zt, zc = zscore(ts[have]), zscore(cs[have])
            tsz, csz = np.zeros_like(ts), np.zeros_like(cs)
            tsz[have], csz[have] = zt, zc
            # the embeddings pull a shot up when they agree with it, scaled so a good keyword hit still leads
            score = kw + 0.45 * np.clip(tsz, -1, 4) + 0.35 * np.clip(csz, -1, 4)
            parts.update(text=ts, clip=cs)
    hits = []
    wants_art = bool(set(re.findall(r"[a-z]+", query.lower())) & ART_WORDS)
    for i, r in enumerate(recs):
        s = float(score[i])
        cdur = r.get("clean_out", r["out"]) - r.get("clean_in", r["in"]) if r.get("kind") != "image" else 99.0
        if cdur < min_dur:
            continue
        if exclude_used and set(r.get("used_in", [])) & set(exclude_used):
            continue
        fit = r.get("v", {}).get("fit", "no")
        if vertical:
            s += {"ok": 0.35, "tight": 0.1}.get(fit, -0.6)
            if "wide" in r.get("flags", []):
                s -= 0.3
        for f in ("dark", "lowres", "blur", "blocked"):   # "dark" doesn't cost a night shot (night stays); murky is measured below
            if f in r.get("flags", []) and not (f == "dark" and r.get("time") == "night"):
                s -= 0.12
        if "short" in r.get("flags", []) and r.get("kind") != "image":
            s -= 0.15
        hits.append([s, i])
    # the picture: ranked first by the words, then the top of the list measured (art, light, the named thing's box), then ranked again
    hits.sort(key=lambda h: -h[0])
    pool = hits[:max(60, n * 5)]
    for h in pool:
        r = recs[h[1]]
        notes = []
        if is_art(r) and not wants_art:
            h[0] -= ART_DEMOTE
            notes.append("artwork")
        light, murky = record_light(r)
        if murky:
            h[0] -= MURKY_DEMOTE
            notes.append("murky")
        sf = subject_fit(r, q)
        if sf:
            area, off = sf
            if area >= SUBJECT_BIG and off <= SUBJECT_CENTRE:
                h[0] += SUBJECT_BONUS
                notes.append("subject big+central")
            elif area < 0.015 or off > 0.3:
                h[0] -= SUBJECT_MALUS
                notes.append("subject small/off-centre")
        h += [notes, light, lit_span(r), sf]
    save_light()
    pool.sort(key=lambda h: -h[0])
    out = []
    for s, i, notes, light, lit, sf in pool[:n]:
        r = recs[i]
        out.append(dict(score=round(s, 3), kw=round(float(kw[i]), 2), text=round(float(parts["text"][i]), 2) if "text" in parts else None,
                        clip=round(float(parts["clip"][i]), 2) if "clip" in parts else None, rec=r, notes=notes, light=light, lit=lit,
                        subject=sf))
    return out


FILE_LINE = re.compile(r".+:\d+$")


def fmt(h):
    r = h["rec"]
    v = r.get("v", {})
    win = f"cx {v.get('cx', 0.5)} cy {v.get('cy', 0.5)} h {v.get('h', 1.0)}" + (f" -> {v['cx1']},{v['cy1']}" if "cx1" in v else "") + f" fit {v.get('fit', '?')}"
    if r.get("kind") == "image":
        span = "still"
    else:
        span = f"{B.mmss(r['in'])}-{B.mmss(r['out'])} ({r['dur']:.2f} s), clean {r['clean_in']:.3f}-{r['clean_out']:.3f}"
    who = ",".join(r.get("who", [])) or "-"
    used = ",".join(r.get("used_in", [])) or "-"
    emb = f" text {h['text']:.2f} clip {h['clip']:.2f}" if h.get("text") is not None else ""
    fx = r.get("facts", [])
    facts = sorted({m for f in fx for m in f.get("ids", [])} | {f["via"] for f in fx if FILE_LINE.match(str(f.get("via", "")))})
    ui = (r.get("ui") or {}).get("read", "")
    pic = []
    if h.get("light"):
        pic.append(f"light {h['light'][0]:.0f}/{h['light'][1]:.0f}/{h['light'][2]:.0f}")
    if h.get("lit"):
        pic.append(f"lit {h['lit'][0]:.2f}-{h['lit'][1]:.2f}, murky {', '.join(f'{x:.2f}-{y:.2f}' for x, y in h['lit'][2])}: cut from the lit span")
    if h.get("subject"):
        pic.append(f"subject {h['subject'][0]:.0%} of the frame, {h['subject'][1]:.2f} off centre")
    if h.get("notes"):
        pic.append("ranked: " + ", ".join(h["notes"]))
    return (f"{h['score']:5.2f} (kw {h['kw']:.2f}{emb})  {r['id']}  {span}  [{' '.join(r.get('flags', []))}]  who: {who}\n"
            f"        {r.get('desc', '')[:170]}\n        window: {win}   used in: {used}" + (f"   facts: {', '.join(facts)}" if facts else "")
            + (f"\n        on screen (f{r['ui'].get('frame')}): {ui[:170]}" if ui else "")
            + (f"\n        picture: {'; '.join(pic)}" if pic else ""))


def sheet(hits, out, vertical):
    from PIL import Image, ImageDraw
    from sheetfont import font as sheet_font
    TW, TH = 320, 180
    VW, VH = 101, 180
    font = sheet_font(12)
    rows = []
    for h in hits:
        r = h["rec"]
        ims = []
        if r.get("kind") == "image":
            im = Image.open(r["file"]).convert("RGB")
            W, H = im.size
            frames = [(im, (W, H))]
        else:
            fl = r.get("frames", [])
            fl = [fl[0], fl[len(fl) // 2], fl[-1]] if len(fl) >= 3 else fl
            kf = B.key_file(r["src"] if r["src"] in B.MASTERS else r["id"].split("@")[0])
            frames = []
            for f in fl:
                p = B.WORK / "frames" / kf / f"{f:07d}.jpg"
                if p.exists():
                    im = Image.open(p).convert("RGB")
                else:
                    im = B.grab(Path(r["file"]), B.seek_time(f, r.get("fps", 30)), 1280, 720)
                frames.append((im, im.size))
        v = r.get("v", {})
        for k, (im, (W, H)) in enumerate(frames):
            sm = im.resize((TW, TH))
            d = ImageDraw.Draw(sm)
            fr = k / max(1, len(frames) - 1)
            e = fr * fr * (3 - 2 * fr)
            cx = v.get("cx", 0.5) + (v.get("cx1", v.get("cx", 0.5)) - v.get("cx", 0.5)) * e
            cy = v.get("cy", 0.5) + (v.get("cy1", v.get("cy", 0.5)) - v.get("cy", 0.5)) * e
            hh = v.get("h", 1.0) * TH
            ww = hh * 9 / 16 * (H / W) * (TW / TH) if W else hh * 9 / 16
            x0 = min(max(cx * TW - ww / 2, 0), TW - ww)
            y0 = min(max(cy * TH - hh / 2, 0), TH - hh)
            d.rectangle([x0, y0, x0 + ww, y0 + hh], outline=(255, 40, 40), width=2)
            ims.append(sm)
            if vertical and k == len(frames) // 2:
                big = im
                bw, bh = big.size
                hh2 = v.get("h", 1.0) * bh
                ww2 = hh2 * 9 / 16
                xx = min(max(cx * bw - ww2 / 2, 0), bw - ww2)
                yy = min(max(cy * bh - hh2 / 2, 0), bh - hh2)
                ims.append(big.crop((int(xx), int(yy), int(xx + ww2), int(yy + hh2))).resize((VW, VH)))
        rows.append((h, ims))
    cols = max(len(ims) for _, ims in rows)
    LH = 44
    W = cols * (TW + 4) + 4
    sh = Image.new("RGB", (W, len(rows) * (TH + LH)), (16, 16, 20))
    d = ImageDraw.Draw(sh)
    for i, (h, ims) in enumerate(rows):
        y = i * (TH + LH)
        r = h["rec"]
        x = 2
        for im in ims:
            sh.paste(im, (x, y + LH))
            x += im.width + 4
        v = r.get("v", {})
        d.text((4, y + 2), f"#{i} {h['score']:.2f}  {r['id']}  {B.mmss(r['in']) if r.get('kind') != 'image' else 'still'}  "
                           f"{r.get('dur', 0):.2f}s  [{' '.join(r.get('flags', []))}]  cx {v.get('cx')} cy {v.get('cy')} h {v.get('h')} {v.get('fit')}",
               fill=(255, 230, 0), font=font)
        d.text((4, y + 18), r.get("desc", "")[:150], fill=(220, 220, 220), font=font)
        d.text((4, y + 31), f"who: {','.join(r.get('who', [])) or '-'}   used in: {','.join(r.get('used_in', [])) or '-'}", fill=(160, 200, 255), font=font)
    sh.save(out, quality=86)
    print(len(rows), "hits ->", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--min-dur", type=float, default=0.0)
    ap.add_argument("--exclude-used", default="")
    ap.add_argument("--src", default="")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--sheet")
    ap.add_argument("--no-embed", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    srcs = set(a.src.split(",")) if a.src else None
    recs = load_records(srcs)
    if not recs:
        raise SystemExit("no records in " + str(B.BRAIN))
    hits = search(a.query, recs, use_embed=not a.no_embed, vertical=a.vertical, min_dur=a.min_dur,
                  exclude_used=[x for x in a.exclude_used.split(",") if x], n=a.n)
    if a.json:
        print(json.dumps([dict(score=h["score"], id=h["rec"]["id"], notes=h.get("notes"), light=h.get("light"), lit=h.get("lit"), subject=h.get("subject"),
                               **{k: h["rec"].get(k) for k in ("in", "out", "clean_in", "clean_out", "dur", "desc", "who", "flags", "v", "used_in", "facts")})
                          for h in hits], indent=1))
    else:
        print(f"{len(recs)} shots searched for: {a.query}")
        for i, h in enumerate(hits):
            print(f"#{i:2d} " + fmt(h))
    if a.sheet:
        sheet(hits, a.sheet, a.vertical)


if __name__ == "__main__":
    main()
