"""Reuse check: everything an edit shares with the last N long videos (and the 60-s prototypes among them) and with the Shorts in
kb/ASSET_LEDGER.json (asset_ledger.py), as a readable report. The style stays from video to video; no asset comes back one-to-one.

  PIPE tools/motion/reuse_check.py <video | composition | src folder> [--last 3] [--rev <commit>]
                                   [--no-fp] [--out <report.md>] [--json <file>] [--sheet <dir>]
  e.g.  reuse_check.py 012 --rev 1a2b3c4 --out videos/012-example/REUSE_v1.md --sheet <dir>
        reuse_check.py src/v013            (a new edit: its composition is found in src/Root.tsx and walked as it is now)
The first run fingerprints every past use (~20 min with the CPU shared; cached in out/ledger/fp_cache.json, then ~4 min). --sheet draws
each picture match side by side (fingerprint_matches.jpg): look at it before trusting a match.

What counts as shared (each with its time in this edit and where it was used before):
- the same clip file over the same span, or within 2 s of it; the same short clip (60 s or less) at another span: a different timestamp
  of one short clip is the same picture to a viewer; a long source (a 27-minute official film, a full recording) only where the spans
  meet;
- another cut of a source used before, by its file name's series (fx_city_skyline_dusk_pexels_1234567 and fx_city_skyline_night_pexels_
  1234580: two takes of one stock shoot; an official film's _open and _end halves);
- the same moment of a master source cut into another file (curated cuts know their master and seconds);
- the same picture from another file: picture fingerprints of what each use showed (2 a second, the centre 60% of the frame, a 64-bit
  difference hash; 2+ samples within 10 bits; a flat frame never counts), each match confirmed on its closest pair of frames
  (their colour thumbnails correlate 0.7 or more), so the same source cut differently still shows up and a logo on black never
  matches another;
- the same still or photo (the same file, the same bytes, the same source frame, or a fingerprint within 6 bits);
- the same receipt (the same capture, the same URL, or the same quoted words);
- the same graphic: one of our components used again (from a past video's own code, or the house kit with its props side by side),
  a component whose code is mostly a past video's (a copied look under a new name), and a component of the same kind by its name (a
  new two-bar comparison that is 49% like a past video's bars in code and the same idea: found only that way).
What it can't see: words on screen inside a clip, colours and backgrounds (the palette), the script's lines, sound and music."""
import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_ledger as AL  # noqa: E402

GAP = 2.0          # spans this close count as the same span (seconds)
SHORT_FILE = 60.0  # a file this long or shorter: any span of it is the same clip
FP_BITS = 10       # fingerprint distance for footage
FP_STILL_BITS = 6  # ... for stills
SIMILAR = 0.6      # code similarity that makes a component a copy of another's look (measured: copies 0.76-1.0, unrelated graphics
                   # 0.3 median and up to 0.5, so a look rebuilt in new code, a two-bar comparison at 0.49 to a past one, is found by
                   # its kind below, not by its code)
# The kind of graphic a component's name says it is: two different components of one kind are the same idea shown again (numbers shown
# the same way again; two bar comparisons). By name only, so a match is a prompt to look, not a verdict.
KINDS = [("bar comparison", r"Bars?\b|Bar[A-Z]|Bars$"), ("big number", r"Number|Count(er|Up)|Stat\b|Figure"),
         ("globe or map", r"Globe|Map\b|Map[A-Z]|Earth"), ("timeline", r"Release|Timeline|YearRoll|Years?\b"), ("logo card", r"Logo"),
         ("people card", r"Bosses|Silhouette|People|Faces|Portrait|Crew"), ("quote card", r"Quote"), ("typed date", r"Date"),
         ("stamp", r"^Stamp"), ("chapter card", r"Chapter"), ("name tag", r"NameTag|Lower(Third)?"), ("clip in a card", r"VClip|VideoCard|ClipCard"),
         ("photo card", r"PhotoCard|TwoPhotos"), ("subscribe ask", r"Subscribe"), ("sign-off", r"SignOff"), ("cross or strike", r"Cross|Strike"),
         ("cover row", r"CoverRow|Covers\b")]
KIND_SKIP = {"Page", "PageStage", "Browser", "Receipt"}   # the receipt is the house's one way to show a page
# the creator's own brand (the avatar in the subscribe ask and the sign-off: files under a brand/ folder or named brand_*): the same in
# every video on purpose
BRAND = re.compile(r"(^|/)brand[_-]|(^|/)brand/", re.I)
MASTER_OVERLAP = 0.25  # seconds two cuts of one master must share: a master is many shots, so a neighbouring shot is not the same picture


def series(path):
    """A clip's source series from its name: the descriptive words before the take, the stock id or the date (fx_city_skyline_dusk_pexels_
    1234567 -> city skyline dusk). Two files of one series are cuts of one source: another take of the same shoot (a different timestamp
    of one shoot is the same picture to a viewer), the other half of an official film, the same broadcast."""
    w = Path(path).stem.lower().split("_")
    if w and re.fullmatch(r"c\d+|fx|pp|pl", w[0]):
        w = w[1:]
    out = []
    for t in w:
        if t in ("pexels", "pixabay", "mixkit", "coverr", "videvo") or re.fullmatch(r"\d{4,}|\d{4}-\d{2}(-\d{2})?|[a-d]|open|end|v\d+", t):
            break
        out.append(t)
    return out


def kind_of(name):
    if name in KIND_SKIP:
        return None
    for k, rx in KINDS:
        if re.search(rx, name):
            return k
    return None


# ------------------------------------------------------------------------------------------------------------------- the target edit

def root_compositions():
    """Root.tsx's compositions: id -> {module, export, seconds, size, props_json, shots}."""
    root = (AL.SRC / "Root.tsx").read_text(encoding="utf-8")
    imports = {}
    for names, mod in re.findall(r"import\s*\{([^}]*)\}\s*from\s*'\./([^']+)'", root):
        for n in names.split(","):
            n = n.strip()
            if not n or n.startswith("type "):
                continue
            src, _, alias = n.partition(" as ")
            imports[(alias or src).strip()] = (mod, src.strip())
    json_imports = dict((k, m) for k, m in re.findall(r"import\s+(\w+)\s+from\s*'\./([^']+\.json)'", root))
    comps = {}
    for m in re.finditer(r"<Composition\s+([^>]*?)/>", root, re.S):
        a = m.group(1)
        cid = re.search(r'id="([^"]+)"', a)
        comp = re.search(r"component=\{(\w+)\}", a)
        if not cid or not comp or comp.group(1) not in imports:
            continue
        mod, export = imports[comp.group(1)]
        w = re.search(r"width=\{(\d+)\}", a)
        h = re.search(r"height=\{(\d+)\}", a)
        sec = re.search(r"durationInFrames=\{Math\.round\((\w+)\s*\*\s*FPS\)\}", a)
        cur = re.search(r"defaultProps=\{\{cur:\s*(\w+)", a)
        e = {"comp": cid.group(1), "module": mod, "export": export, "size": [int(w.group(1)) if w else 1920, int(h.group(1)) if h else 1080]}
        if cur and cur.group(1) in json_imports:
            e["props_json"] = json_imports[cur.group(1)]
        elif sec and sec.group(1) in imports:
            e["seconds"] = sec.group(1)
        else:
            continue
        code = (AL.SRC / (mod + ".tsx")).read_text(encoding="utf-8") if (AL.SRC / (mod + ".tsx")).exists() else ""
        if re.search(r"export const SHOTS\b", code):
            e["shots"] = "SHOTS"
        comps[cid.group(1)] = e
    return comps


def resolve_target(arg):
    """A video number, a composition id or a src folder -> a VIDEOS-like entry."""
    for v in AL.VIDEOS:
        if arg in (v["video"], v["comp"]):
            return dict(v)
    comps = root_compositions()
    if arg in comps:
        e = comps[arg]
    else:
        folder = Path(arg.replace("\\", "/")).name if ("/" in arg or "\\" in arg) else arg
        hits = [c for c in comps.values() if c["module"].split("/")[0] == folder]
        if not hits:
            sys.exit(f"reuse_check: no composition for {arg!r} in VIDEOS or src/Root.tsx")
        if len(hits) > 1:
            sys.exit(f"reuse_check: {arg!r} has several compositions ({', '.join(c['comp'] for c in hits)}): name one")
        e = hits[0]
    num = re.search(r"(\d{3})", e["module"].split("/")[0])
    e.update({"video": num.group(1) if num else e["comp"], "title": e["comp"], "kind": "short" if e["size"][1] > e["size"][0] else "long",
              "date": time.strftime("%Y-%m-%dT%H:%M"), "delivered": None, "folders": [e["module"].split("/")[0]]})
    return e


# ------------------------------------------------------------------------------------------------------------------------ helpers

def mmss(t, short=False):
    if short or t < 60:
        return f"{t:.1f} s" if short else f"0:{t:04.1f}"
    return f"{int(t // 60)}:{t % 60:04.1f}"


def gap(a0, a1, b0, b1):
    return max(0.0, max(a0, b0) - min(a1, b1))


def ints(fp):
    """Fingerprints (hex strings, None for a flat frame) as ints, flat frames dropped."""
    return [int(h, 16) for h in (fp or []) if h]


def fp_match(A, B, bits):
    """How many of A's samples have a sample of B within `bits`."""
    return sum(1 for a in A if any((a ^ b).bit_count() <= bits for b in B))


def code_of(mod, name, cache={}):
    """A component's source (from its declaration to the next top-level one), comments and spaces normalised."""
    if mod not in cache:
        p = AL.SRC / mod
        cache[mod] = p.read_text(encoding="utf-8") if p.exists() else ""
    src = cache[mod]
    m = re.search(rf"^(?:export\s+)?(?:const|function)\s+{re.escape(name)}\b", src, re.M)
    if not m:
        return ""
    nxt = re.search(r"^(?:export\s+)?(?:const|function|let|type|interface|class)\s+\w+", src[m.end():], re.M)
    body = src[m.start(): m.end() + (nxt.start() if nxt else len(src))]
    body = re.sub(r"//[^\n]*|/\*.*?\*/", "", body, flags=re.S)
    return " ".join(re.findall(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|\S", body))


def similarity(a, b):
    if not a or not b:
        return 0.0
    sm = difflib.SequenceMatcher(None, a.split(), b.split(), autojunk=False)
    if sm.real_quick_ratio() < SIMILAR or sm.quick_ratio() < SIMILAR:
        return 0.0
    return sm.ratio()


def where(v, u, kind):
    s = f"{v['video']} at {mmss(u['at'])}"
    if kind == "clip" and "from" in u:
        s += f" ({u['from']:.1f}-{u['to']:.1f} s of the file)"
    return s


# ------------------------------------------------------------------------------------------------------------------------- the check

def check(tgt, past, use_fp=True):
    """Every shared asset: a list of findings {type, at, what, before[], note}."""
    found = []
    by_file, by_master, by_md5, by_url, by_quote, by_src_img = {}, {}, {}, {}, {}, {}
    for pv in past:
        for c in pv["clips"]:
            for u in c["uses"]:
                by_file.setdefault(c["file"], []).append((pv, c, u))
                if u.get("master_span"):
                    by_master.setdefault(c["master"]["master"], []).append((pv, c, u))
        for s in pv["stills"] + pv["pages"]:
            for u in s["uses"]:
                by_file.setdefault(s["file"], []).append((pv, s, u))
                if s.get("md5"):
                    by_md5.setdefault(s["md5"], []).append((pv, s, u))
                src = s.get("source") or {}
                if src.get("image"):
                    by_src_img.setdefault(src["image"], []).append((pv, s, u))
                if s.get("url"):
                    by_url.setdefault(norm_url(s["url"]), []).append((pv, s, u))
                for q in s.get("quotes") or []:
                    by_quote.setdefault(norm_q(q), []).append((pv, s, u))

    by_series = {}
    for pv in past:
        for pc in pv["clips"]:
            if pc.get("family") != "official" and series(pc["file"]):
                by_series.setdefault(tuple(series(pc["file"])), []).append((pv, pc))
    # footage
    for c in tgt["clips"]:
        ln = c.get("length")
        for u in c["uses"]:
            same, other = [], []
            for pv, pc, pu in by_file.get(c["file"], []):
                if "from" not in pu:
                    continue
                g = gap(u["from"], u["to"], pu["from"], pu["to"])
                if g <= GAP:
                    same.append(where(pv, pu, "clip"))
                elif ln is None or ln <= SHORT_FILE or c.get("family") in ("stock", "outside") and ln <= 180:
                    other.append(where(pv, pu, "clip"))
            if same:
                found.append(dict(type="clip-span", at=u["at"], dur=u["dur"], file=c["file"], span=(u["from"], u["to"]), family=c.get("family"),
                                  before=same, also=other))
            elif other:
                found.append(dict(type="clip-other", at=u["at"], dur=u["dur"], file=c["file"], span=(u["from"], u["to"]), family=c.get("family"),
                                  before=other))
            ms = u.get("master_span")
            if ms:
                hits = [f"{pv['video']} at {mmss(pu['at'])} ({pc['file']}, {pc['master']['master']} {pu['master_span'][0]:.1f}-{pu['master_span'][1]:.1f} s)"
                        for pv, pc, pu in by_master.get(c["master"]["master"], [])
                        if pc["file"] != c["file"] and min(ms[1], pu["master_span"][1]) - max(ms[0], pu["master_span"][0]) >= MASTER_OVERLAP]
                if hits:
                    found.append(dict(type="clip-master", at=u["at"], dur=u["dur"], file=c["file"], span=(u["from"], u["to"]),
                                      master=f"{c['master']['master']} {ms[0]:.1f}-{ms[1]:.1f} s", before=hits))
            sr = series(c["file"])
            if c.get("family") != "official" and sr and not same and not other:
                hits = []
                for key, lst in by_series.items():
                    k = list(key)
                    common = next((i for i, (x, y) in enumerate(zip(sr, k)) if x != y), min(len(sr), len(k)))
                    for pv, pc in lst:
                        if pc["file"] != c["file"] and (sr == k or common >= 2):
                            hits += [f"{pv['video']} at {mmss(pu['at'])} ({pc['file']}, {pu['from']:.1f}-{pu['to']:.1f} s)" for pu in pc["uses"] if "from" in pu]
                if hits:
                    found.append(dict(type="clip-source", at=u["at"], dur=u["dur"], file=c["file"], span=(u["from"], u["to"]), family=c.get("family"),
                                      series=" ".join(sr), before=dedupe(hits)))
    # stills and pages
    for kind, items in (("still", tgt["stills"]), ("page", tgt["pages"])):
        for s in items:
            if BRAND.search(s["file"]):
                continue
            for u in s["uses"]:
                hits, how = [], []
                for pv, ps, pu in by_file.get(s["file"], []):
                    hits.append(where(pv, pu, kind))
                    how.append("the same file")
                if s.get("md5"):
                    for pv, ps, pu in by_md5.get(s["md5"], []):
                        if ps["file"] != s["file"]:
                            hits.append(f"{where(pv, pu, kind)} as {ps['file']}")
                            how.append("the same bytes")
                src = s.get("source") or {}
                if src.get("image"):
                    for pv, ps, pu in by_src_img.get(src["image"], []):
                        if ps["file"] != s["file"]:
                            hits.append(f"{where(pv, pu, kind)} as {ps['file']}")
                            how.append("the same source picture")
                if kind == "page":
                    if s.get("url"):
                        for pv, ps, pu in by_url.get(norm_url(s["url"]), []):
                            if ps["file"] != s["file"]:
                                hits.append(f"{where(pv, pu, kind)} as {ps['file']}")
                                how.append("the same article (URL)")
                    for q in s.get("quotes") or []:
                        for pv, ps, pu in by_quote.get(norm_q(q), []):
                            if ps["file"] != s["file"]:
                                hits.append(f"{where(pv, pu, kind)} as {ps['file']}")
                                how.append(f"the same quote (\"{q[:60]}\")")
                if hits:
                    found.append(dict(type=kind, at=u["at"], dur=u["dur"], file=s["file"], family=s.get("family"), url=s.get("url"),
                                      before=dedupe(hits), how=sorted(set(how))))
    if use_fp:
        found += fp_findings(tgt, past, found)
    found += graphic_findings(tgt, past)
    return found


def dedupe(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def norm_url(u):
    return re.sub(r"^https?://(www\.)?|[?#].*$|/$", "", u.strip().lower())


def norm_q(q):
    return re.sub(r"[^a-z0-9]+", " ", q.lower()).strip()


NCC_MIN = 0.7      # the colour correlation of the matched frames that confirms a fingerprint match. Measured on real candidates: the
                   # same footage 0.84-1.00, the false ones (logos on black, dark frames from old footage, a blue sky against a person at
                   # a red window, 0.74 alike in grey) -0.41 to 0.48


_THUMB = {}


def _thumb(path, t, crop):
    """A 32x18 colour thumbnail of the centre 60% of one frame (or a still), as floats; None if it can't be read. Memoised: one frame of
    this edit is compared with many candidates."""
    key = (str(path), round(t, 2), crop)
    if key not in _THUMB:
        _THUMB[key] = _thumb_read(path, t, crop)
    return _THUMB[key]


def _thumb_read(path, t, crop):
    import subprocess
    import numpy as np
    p = Path(path) if Path(path).is_absolute() else AL.PUB / path
    vf = ",".join(x for x in (crop, "crop=iw*0.6:ih*0.6", "scale=32:18:flags=area", "format=rgb24") if x)
    cmd = [AL.FFMPEG, "-v", "error"] + (["-ss", f"{max(0.0, t):.3f}"] if AL.is_video(str(p)) else []) + \
          ["-i", str(p), "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, timeout=300).stdout
    return np.frombuffer(raw, np.uint8).astype(float) if len(raw) == 32 * 18 * 3 else None


def confirm(a_args, b_args, A, B):
    """The colour correlation of the best-matching pair of samples' frames (fingerprints at 2 a second: sample k is k/2 s into the span)."""
    import numpy as np
    key = f"ncc_rgb|{a_args}|{b_args}"
    c = AL._fp_cache()
    if key in c:
        return c[key]
    pairs = [((int(a, 16) ^ int(b, 16)).bit_count(), i, j) for i, a in enumerate(A or []) if a for j, b in enumerate(B or []) if b]
    if not pairs:
        return 0.0
    _, i, j = min(pairs)
    fa, fb = _thumb(a_args[0], a_args[1] + i * 0.5, a_args[3]), _thumb(b_args[0], b_args[1] + j * 0.5, b_args[3])
    if fa is None or fb is None:
        return 0.0
    fa, fb = fa - fa.mean(), fb - fb.mean()
    r = float((fa * fb).sum() / (np.sqrt((fa * fa).sum() * (fb * fb).sum()) + 1e-9))
    c[key] = round(r, 3)
    return c[key]


def fp_findings(tgt, past, found):
    """The same picture from another file: fingerprints of every clip and still use, compared across files; each match confirmed on
    its best pair of frames (NCC_MIN)."""
    jobs = [(c, u, "clip") for c in tgt["clips"] for u in c["uses"]] + \
           [(s, u, "still") for s in tgt["stills"] if not BRAND.search(s["file"]) for u in s["uses"]]
    pjobs = [(c, u, "clip") for pv in past for c in pv["clips"] for u in c["uses"]] + \
            [(s, u, "still") for pv in past for s in pv["stills"] if not BRAND.search(s["file"]) for u in s["uses"]]
    t0 = time.time()
    AL.fingerprint_all(jobs + pjobs)
    print(f"fingerprints: {len(jobs)} uses here, {len(pjobs)} before ({time.time() - t0:.0f} s)", flush=True)
    owner = {}
    for pv in past:
        for c in pv["clips"]:
            for u in c["uses"]:
                owner[id(u)] = pv
        for s in pv["stills"]:
            for u in s["uses"]:
                owner[id(u)] = pv
    known = {(f["file"], f["at"]) for f in found}
    out = []
    pfp = [(e, u, k, AL.use_fingerprints(e, u, k)) for e, u, k in pjobs]
    pfp = [(e, u, k, raw, ints(raw)) for e, u, k, raw in pfp]
    rejected = 0
    for e, u, k in jobs:
        if (e["file"], u["at"]) in known:
            continue
        rawA = AL.use_fingerprints(e, u, k)
        A = ints(rawA)
        if not A:
            continue
        hits = []
        for pe, pu, pk, rawB, B in pfp:
            if pe["file"] == e["file"] or not B:
                continue
            need = 2 if len(A) >= 2 and len(B) >= 2 else 1
            bits = FP_BITS if k == pk == "clip" and need == 2 else FP_STILL_BITS   # one sample against one: the stricter bar
            n = fp_match(A, B, bits)
            if n >= need:
                r = confirm(AL.fp_args(e, u, k), AL.fp_args(pe, pu, pk), rawA, rawB)
                if r < NCC_MIN:
                    rejected += 1
                    continue
                pv = owner[id(pu)]
                hits.append((n, f"{where(pv, pu, pk)}: {pe['file']} ({n} of {len(A)} samples, frames {r:.2f} alike)", AL.fp_args(pe, pu, pk)))
        if hits:
            hits.sort(key=lambda h: -h[0])
            out.append(dict(type="fp-" + k, at=u["at"], dur=u["dur"], file=e["file"], span=(u.get("from"), u.get("to")), before=[h[1] for h in hits],
                            pair=(AL.fp_args(e, u, k), hits[0][2], hits[0][1])))
    AL.fp_save()
    print(f"fingerprint matches: {len(out)} kept, {rejected} candidate pairs rejected on their frames (correlation under {NCC_MIN})", flush=True)
    return out


def frame_at(path, t, crop=""):
    """One frame of a file (or a still) as a 320-px PIL image."""
    from io import BytesIO
    from PIL import Image
    import subprocess
    p = Path(path) if Path(path).is_absolute() else AL.PUB / path
    if not AL.is_video(str(p)):
        im = Image.open(p).convert("RGB")
        im.thumbnail((320, 180))
        return im
    vf = ",".join(x for x in (crop, "scale=320:180:force_original_aspect_ratio=decrease") if x)
    r = subprocess.run([AL.FFMPEG, "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(p), "-frames:v", "1", "-vf", vf, "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True, timeout=300)
    return Image.open(BytesIO(r.stdout)).convert("RGB") if r.stdout else Image.new("RGB", (320, 180), (60, 0, 0))


def sheet(found, out_dir):
    """The fingerprint matches side by side (this edit's frame | the frame it matched | what), to check them by eye before trusting them."""
    from PIL import Image, ImageDraw
    rows = [f for f in found if f["type"].startswith("fp-") and f.get("pair")]
    if not rows:
        return None
    W, H, T = 320, 180, 560
    img = Image.new("RGB", (W * 2 + T, H * len(rows)), (16, 16, 16))
    d = ImageDraw.Draw(img)
    for i, f in enumerate(rows):
        (p0, a0, b0, c0), (p1, a1, b1, c1), what = f["pair"]
        for j, (p, a, b, c) in enumerate(((p0, a0, b0, c0), (p1, a1, b1, c1))):
            fr = frame_at(p, (a + b) / 2 if b > a else a, c)
            img.paste(fr, (j * W + (W - fr.width) // 2, i * H + (H - fr.height) // 2))
        d.text((2 * W + 10, i * H + 10), f"here {mmss(f['at'])}: {Path(f['file']).name}", fill=(255, 255, 255))
        d.text((2 * W + 10, i * H + 34), what[:90], fill=(200, 200, 200))
        d.text((2 * W + 10, i * H + 52), what[90:180], fill=(200, 200, 200))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out = Path(out_dir) / "fingerprint_matches.jpg"
    img.save(out, quality=88)
    return out


def graphic_findings(tgt, past):
    """Our components used again: from a past video's code, from the house kit (props side by side), or a past component's code copied."""
    out = []
    pcomp = {}
    for pv in past:
        for c in pv["components"]:
            pcomp.setdefault((c["name"], c["module"]), []).append((pv, c))
    for c in tgt["components"]:
        key = (c["name"], c["module"])
        before = pcomp.get(key, [])
        first = c["uses"][0]
        if c["origin"].startswith("from "):
            out.append(dict(type="graphic-import", at=first["at"], name=c["name"], module=c["module"], origin=c["origin"],
                            uses=[(u["at"], u["props"]) for u in c["uses"]],
                            before=[(pv["video"], u["at"], u["props"]) for pv, pc in before for u in pc["uses"]]))
        elif before and c["origin"].startswith("kit"):
            out.append(dict(type="graphic-kit", at=first["at"], name=c["name"], module=c["module"], origin=c["origin"],
                            uses=[(u["at"], u["props"]) for u in c["uses"]],
                            before=[(pv["video"], u["at"], u["props"]) for pv, pc in before for u in pc["uses"]]))
    # a copied look: our own component whose code is mostly a past video's component
    own = [c for c in tgt["components"] if c["origin"] == "own"]
    pown = {(pc["name"], pc["module"]): (pv, pc) for pv in past for pc in pv["components"] if pc["origin"] == "own"}
    pcode = {k: code_of(k[1], k[0]) for k in pown}
    for c in own:
        mine = code_of(c["module"], c["name"])
        if len(mine.split()) < 40:
            continue
        best = []
        for k, (pv, pc) in pown.items():
            if k[1] == c["module"]:          # the same file: a series' own template (the parts of one Shorts series), not a copy
                continue
            r = similarity(mine, pcode[k])
            if r >= SIMILAR:
                best.append((r, pv, pc))
        if best:
            best.sort(key=lambda b: -b[0])
            out.append(dict(type="graphic-copy", at=c["uses"][0]["at"], name=c["name"], module=c["module"],
                            uses=[(u["at"], u["props"]) for u in c["uses"]],
                            before=[(pv["video"], pc["name"], pc["module"], round(r, 2), [u["at"] for u in pc["uses"]][:6]) for r, pv, pc in best[:3]]))
    # the same kind of graphic under another name (by name: a prompt to look)
    copied = {(f["name"], f["module"], b[1], b[2]) for f in out if f["type"] == "graphic-copy" for b in f["before"]}
    reported = {(f["name"], f["module"]) for f in out if f["type"] in ("graphic-import", "graphic-kit")}
    for c in tgt["components"]:
        k = kind_of(c["name"])
        if not k or (c["name"], c["module"]) in reported:
            continue
        others = [(pv, pc) for (n, m), lst in pcomp.items() for pv, pc in lst
                  if (n, m) != (c["name"], c["module"]) and kind_of(n) == k and (c["name"], c["module"], n, m) not in copied]
        if others:
            out.append(dict(type="graphic-kind", at=c["uses"][0]["at"], name=c["name"], module=c["module"], origin=c["origin"], kind=k,
                            uses=[(u["at"], u["props"]) for u in c["uses"]],
                            before=[(pv["video"], u["at"], {"_component": f"{pc['name']} ({pc['module']})", **u["props"]}) for pv, pc in others
                                    for u in pc["uses"]]))
    return out


# --------------------------------------------------------------------------------------------------------------------------- report

LABEL = {
    "clip-span": "Same clip, same span (or within 2 s)",
    "clip-other": "Same clip, another span (a short clip or a stock/outside clip: the same picture to a viewer)",
    "clip-source": "Another cut of a source used before (the same shoot, broadcast or trailer, by file name)",
    "clip-master": "The same moment of a master source, cut into another file",
    "fp-clip": "The same picture from another file (fingerprints)",
    "still": "Same still or photo (a logo: the same mark is fine, show it a new way)",
    "fp-still": "A still that is a picture used before (fingerprints)",
    "page": "Same receipt",
    "graphic-import": "Graphics taken from a past video's code",
    "graphic-copy": "Graphics whose code is mostly a past video's (a copied look under a new name)",
    "graphic-kit": "House-kit graphics used again (the style stays; vary the look: layout, palette, how the number lands)",
    "graphic-kind": "The same kind of graphic as a past one, by its name (look at both: a new idea or the old one again?)",
}
ORDER = list(LABEL)


def props_short(p, n=150):
    p = {k: v for k, v in (p or {}).items() if k not in ("dur", "children")}
    s = json.dumps(p, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def report(tgt, tv, past, found, args):
    vids = ", ".join(f"{p['video']} ({p['kind']})" for p in past)
    L = [f"# Reuse check: {tv['video']} ({tgt['comp']})", "",
         f"*`tools/motion/reuse_check.py {' '.join(args)}`, {time.strftime('%Y-%m-%d %H:%M')}. The edit walked from "
         f"{tgt['code']}; compared with the ledger (`kb/ASSET_LEDGER.json`, {LED.get('updated', '?')}): {vids}. Times are this edit's "
         f"(m:ss.s); a clip's span is seconds of its file. The style stays, no asset as it was in the last videos.*", ""]
    counts = {k: sum(1 for f in found if f["type"] == k) for k in ORDER}
    L += ["| What | Found |", "|---|---|"] + [f"| {LABEL[k]} | {counts[k]} |" for k in ORDER] + [""]
    for k in ORDER:
        items = sorted((f for f in found if f["type"] == k), key=lambda f: f["at"])
        if not items:
            continue
        L += [f"## {LABEL[k]}", ""]
        if k.startswith("graphic"):
            for f in items:
                ats = ", ".join(mmss(a) for a, _ in f["uses"][:12]) + (f" (+{len(f['uses']) - 12})" if len(f["uses"]) > 12 else "")
                L.append(f"- **{f['name']}** (`{f['module']}`{', ' + f['origin'] if f.get('origin') else ''}), here at {ats}")
                L.append(f"  - here: {props_short(f['uses'][0][1])}")
                if k == "graphic-copy":
                    for vid, nm, mod, r, ats0 in f["before"]:
                        L.append(f"  - {vid}'s **{nm}** (`{mod}`), {int(r * 100)}% the same code; used there at {', '.join(mmss(a) for a in ats0)}")
                elif k == "graphic-kind":
                    by = {}
                    for vid, a, p in f["before"]:
                        by.setdefault((vid, p.get("_component")), []).append((a, p))
                    L[-2] = L[-2] + f" · kind: {f['kind']}"
                    for (vid, comp), xs in by.items():
                        p0 = {k2: v2 for k2, v2 in xs[0][1].items() if k2 != "_component"}
                        L.append(f"  - {vid}'s {comp}: {len(xs)}x, at {', '.join(mmss(a) for a, _ in xs[:8])}{' ...' if len(xs) > 8 else ''}; e.g. {props_short(p0)}")
                else:
                    by = {}
                    for vid, a, p in f["before"]:
                        by.setdefault(vid, []).append((a, p))
                    for vid, xs in by.items():
                        L.append(f"  - {vid}: {len(xs)}x, at {', '.join(mmss(a) for a, _ in xs[:8])}{' ...' if len(xs) > 8 else ''}; e.g. {props_short(xs[0][1])}")
            L.append("")
            continue
        if k in ("still", "page", "fp-still"):          # one row per file, all its times here
            byf = {}
            for f in items:
                g = byf.setdefault(f["file"], dict(f, ats=[]))
                g["ats"].append((f["at"], f["dur"]))
                g["before"] = dedupe(g["before"] + f["before"])
            items = list(byf.values())
        L += ["| Here | File | Before |", "|---|---|---|"]
        for f in items:
            span = f" ({f['span'][0]:.1f}-{f['span'][1]:.1f} s)" if f.get("span") and f["span"][0] is not None else ""
            extra = f" · {f['master']}" if f.get("master") else ""
            fam = f" · {f['family']}" if f.get("family") else ""
            how = f" · by {', '.join(f['how'])}" if f.get("how") and f["how"] != ["the same file"] else ""
            url = f" · {f['url']}" if f.get("url") else ""
            ser = f" · series \"{f['series']}\"" if f.get("series") else ""
            fam = fam + ser
            before = "; ".join(f["before"][:5]) + (f"; +{len(f['before']) - 5} more" if len(f["before"]) > 5 else "")
            if f.get("also"):
                before += "; also " + "; ".join(f["also"][:3]) + (f"; +{len(f['also']) - 3} more" if len(f["also"]) > 3 else "")
            here = ", ".join(mmss(a) for a, _ in f["ats"]) if f.get("ats") else f"{mmss(f['at'])} ({f['dur']:.1f} s)"
            L.append(f"| {here} | `{f['file']}`{span}{fam}{extra}{url}{how} | {before} |")
        L.append("")
    un = tgt.get("unresolved") or []
    L += ["## What this check can't see", "",
          "Words on screen inside a clip, colours and backgrounds (the palette: one per video), the script's own lines "
          "(a line said again word for word from a past video), sound and music. "
          + (f"Spans known only to the sample (0.1 s): {len(un)}." if un else "Every span was pinned to its sequence's edges."), ""]
    return "\n".join(L)


LED = {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a video number (012), a composition id (V012) or a src folder (src/v013)")
    ap.add_argument("--last", type=int, default=3, help="how many long videos before it to compare with (default 3)")
    ap.add_argument("--rev", help="walk the edit as committed at this git revision")
    ap.add_argument("--no-fp", action="store_true", help="skip the picture fingerprints (faster; misses the same picture in another file)")
    ap.add_argument("--out", help="write the report here (markdown); else it prints")
    ap.add_argument("--json", help="also write the findings as JSON")
    ap.add_argument("--sheet", help="a folder for fingerprint_matches.jpg: each picture match side by side, to check by eye")
    a = ap.parse_args()
    global LED
    LED = AL.load_ledger()
    tv = resolve_target(a.target)
    print(f"walking {tv['comp']} ...", flush=True)
    w = AL.walk(tv, a.rev)
    tgt = AL.ledger_entry(tv, w, AL.indexes())
    vids = [v for k, v in LED.get("videos", {}).items() if k != tv["video"]]
    longs = sorted((v for v in vids if v["kind"] == "long" and v["date"] < tv["date"]), key=lambda v: v["date"], reverse=True)[:a.last]
    oldest = min((v["date"] for v in longs), default="")
    protos = [v for v in vids if v["kind"] == "proto" and oldest <= v["date"] < tv["date"]]
    shorts = [v for v in vids if v["kind"] == "short"]
    past = longs + sorted(protos, key=lambda v: v["date"], reverse=True) + sorted(shorts, key=lambda v: v["video"])
    print(f"against {', '.join(p['video'] for p in past)}", flush=True)
    found = check(tgt, past, use_fp=not a.no_fp)
    args = [a.target] + (["--last", str(a.last)] if a.last != 3 else []) + (["--rev", a.rev] if a.rev else []) + (["--no-fp"] if a.no_fp else [])
    md = report(tgt, tv, past, found, args)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
        print(f"wrote {a.out}: {len(found)} findings")
    else:
        print(md)
    if a.json:
        Path(a.json).write_text(json.dumps(found, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if a.sheet:
        s = sheet(found, a.sheet)
        print(f"wrote {s}" if s else "no picture matches to draw")
    return 0


if __name__ == "__main__":
    sys.exit(main())
