"""Clips already played: inside this composition (a fault) and in the creator's past videos (information).

Every clip the composition plays (the names in its prep manifests that its code names; files in <clips dir>) gets 3 fingerprints: a
64-bit difference hash (9x8 grey, as pipeline/coherency.py's dhash) of its frames at 25, 50 and 75% of its length. Every clip file of every
OTHER video (PUBLIC/*/clips/*.mp4 except the composition's own folder and --skip's) gets the same hash at 4 frames a second, so a span
of the same moment cut with other in/out points still lines up (a new frame meets an old frame at most 0.125 s off). A match = 2 of the
3 frames within --bits (6) of a frame of the same old clip, confirmed on the pictures (48x27 grey correlation: 2 frames >= --ncc 0.8 or
one >= 0.9; two different logos on black hash alike and correlate low). Near-flat frames (black, a white flash) don't count.
INSIDE the composition: each clip against every other clip it plays (same match), a clip name in more than one shot (a later use with a
start/gstart plays on: not counted), and two clips cutting overlapping spans of the same source file (from the manifests' spans, or the
preps' CLIPS; the same span under two crops hashes apart). The same footage twice in one video bores the viewer at once.
The hashes are cached (PUBLIC/reused_cache.json, by path, size and mtime; merged and swapped in whole, since several runs may use it at
once), so a re-run hashes only what changed. Prints each finding with the clip's shot words (its prep comment).
A NAMED MOMENT is allowed: when the words name one exact moment and a past video holds its only picture, the shot's comment (the // block
above the line naming the clip in src/*.tsx, or the # comment on or above its prep entry) says `named-moment: "<the words, as said>" <why
it is the only source>`; the quoted words must be in src/words.json. The reuse prints as ALLOWED REUSE, never as a reason to fall back to
a text card.
Footage may repeat across videos (whatever fits best wins; sentences and graphics never repeat): a match in another video prints as ACROSS
VIDEOS, as information, and the exit code counts only the repeats INSIDE the composition (TWICE, NAME TWICE, SPAN TWICE). Exit 1 if any.

  PIPE tools/motion/qa_reused.py --clips PUBLIC/<video>/clips --src tools/motion/src/<video folder>
      --manifests tools/motion/prep_<video>_*_clips.json ... [--bits 6] [--only name,...] [--skip <folder>] [--no-inside | --inside-only]
      [--show-rejected] [--jobs 6]
  ... qa_reused.py --clips ... --src ... --images [--skip <folder>]   the pictures: every img/ file the code names that another video's
                                            img/ holds (same bytes or dhash within 3 bits): logos and covers may repeat, photos and
                                            footage frames are worth a look
  ... qa_reused.py --clips ... --fresh <source> [in out [filter]]   a source's span every 0.25 s against the cache: which runs no past
      video played (give the prep's whole filter chain, e.g. "<letterbox crop>,scale=1920:1080:force_original_aspect_ratio=increase,
      crop=1920:1080", or a letterboxed source reads fresh where it isn't)
A manifest is a prep's <name>_clips.json: {clip name: [source, in, out]} (or a list of names, then the prep's CLIPS gives the spans).
"""
import argparse
import glob
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, FOOTAGE, PUBLIC  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codefiles import code_files  # noqa: E402   with the subfolder files the film imports

HERE = Path(__file__).resolve().parent
MEDIA = PUBLIC                 # the public dir every video's clips/ and img/ sit in (Q.MEDIA for the tools that import this one)
CACHE = MEDIA / "reused_cache.json"
W, H = 160, 90                 # frames come out of ffmpeg at this size, grey; PIL's LANCZOS takes them to 9x8 (coherency's dhash)
FLAT = 2.5                     # a 9x8 grey frame with less spread than this is flat: its hash is noise


def save(cache):
    """the cache written whole and then swapped in (several runs may use it at the same time: a reader never meets half a file)"""
    import os
    try:                                            # merged over what's there now: another run's new entries are kept
        cur = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    except (ValueError, OSError):
        cur = {}
    cur.update(cache)
    cache.update(cur)
    tmp = CACHE.with_name(f"{CACHE.stem}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(cur), encoding="utf-8")
    for _ in range(20):
        try:
            os.replace(tmp, CACHE)
            return
        except PermissionError:                     # Windows: another process is reading it this instant
            import time
            time.sleep(0.2)


def dhash_arr(g):
    """(hash, flat) of one W x H grey frame"""
    s = np.asarray(Image.fromarray(g).resize((9, 8), Image.LANCZOS), dtype=np.int16)
    return int("".join("1" if b else "0" for b in (s[:, 1:] > s[:, :-1]).flatten()), 2), bool(s.std() < FLAT)


def frames(path, vf_pre="", ss=None):
    """grey W x H frames of a file: all of them through vf_pre (fps=4), or one at ss"""
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-threads", "2"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.3f}"]
    cmd += ["-i", str(path), "-an"]
    if ss is not None:
        cmd += ["-frames:v", "1"]
    cmd += ["-vf", (vf_pre + "," if vf_pre else "") + f"scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"]
    r = subprocess.run(cmd, capture_output=True)
    buf = np.frombuffer(r.stdout, dtype=np.uint8)
    n = buf.size // (W * H)
    return [buf[i * W * H:(i + 1) * W * H].reshape(H, W) for i in range(n)]


def duration(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True,
                       text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def key(p):
    st = p.stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def old_hashes(p):
    return [[f"{h:016x}", fl] for h, fl in (dhash_arr(g) for g in frames(p, "fps=4"))]


def new_hashes(p):
    d = duration(p)
    out = []
    for f in (0.25, 0.5, 0.75):
        g = frames(p, ss=d * f)
        out.append(list(dhash_arr(g[0])) if g else [0, True])
    return out


def words_of(prep_files):
    """clip name -> its shot's words: the beat (the last 'Sxx' named in a comment above it) and the comment on the clip's own line, else
    the last comment line above it"""
    out = {}
    for f in prep_files:
        beat, last = "", ""
        for ln in Path(f).read_text(encoding="utf-8").splitlines():
            s = ln.strip()
            if s.startswith("#"):
                last = s.lstrip("# ").strip()
                m = re.search(r"\b(S\d+[a-z]?)\b", s)
                if m:
                    beat = m.group(1)
                continue
            m = re.match(r'\s*"([A-Za-z0-9_\-]+)":\s*\(', ln)
            if m:
                tail = ln.split("#", 1)[1].strip() if "#" in ln.split(")", 1)[-1] else ""
                text = tail or last
                out.setdefault(m.group(1), (text if text.startswith(beat) else f"{beat} {text}")[:150])
    return out


SMALL = (48, 27)               # the confirmation's picture: grey, zero-mean, unit-norm, so brightness and contrast don't count


def small(path, t):
    g = frames(path, ss=max(0.0, t))
    if not g:
        return None
    s = np.asarray(Image.fromarray(g[0]).resize(SMALL, Image.BOX), dtype=np.float64).flatten()
    s -= s.mean()
    n = np.linalg.norm(s)
    return s / n if n > 1e-6 else None


def confirm(newp, fr_times, oldp, old_times, ncc):
    """the new clip's frames and the old clip's nearest-hash frames compared at 48x27 (normalised correlation): a pair whose dhash only agrees
    by chance (two dark title cards, a logo on black over another) correlates low; the same picture correlates near 1"""
    out = []
    for tn, to in zip(fr_times, old_times):
        a = small(newp, tn)
        best = 0.0
        for dt in (-0.12, 0.0, 0.12):                  # the old clip's frame a step either side: its hash came at 4 fps
            b = small(oldp, to + dt)
            if a is not None and b is not None:
                best = max(best, float(a @ b))
        out.append(best)
    # the same picture: 2 of the frames alike, or one frame nearly identical (the old clip covered part of this span)
    return sum(c >= ncc for c in out) >= 2 or max(out, default=0) >= 0.9, out


def images(img, src, bits=3, skip=()):
    """every picture of <img> (and its subfolders) that the composition's code names (file name or stem in quotes), held against every
    other video's img/ pictures: the same bytes (md5) or a dhash within <bits>. Listed; which are footage frames or photos (to replace)
    and which are logos or official cover art (may repeat) is read by eye"""
    import hashlib
    code = "\n".join(f.read_text(encoding="utf-8") for f in code_files(src))
    ext = (".png", ".jpg", ".jpeg", ".webp")

    def used(f):
        return f.name in code or f'"{f.stem}"' in code or f"'{f.stem}'" in code

    def sig(f):
        try:
            md = hashlib.md5(f.read_bytes()).hexdigest()
        except OSError:                             # gone since the listing (another run's clean-up)
            return None, None
        try:
            g = Image.open(f).convert("L").resize((9, 8), Image.LANCZOS)
        except Exception:
            return md, None
        s = np.asarray(g, dtype=np.int16)
        return md, int("".join("1" if b else "0" for b in (s[:, 1:] > s[:, :-1]).flatten()), 2)

    mine = [f for f in sorted(img.rglob("*")) if f.suffix.lower() in ext and used(f)]
    others = [f for f in sorted(MEDIA.glob("*/img/**/*")) if f.suffix.lower() in ext and f.parent.resolve() != img.resolve()
              and img.resolve() not in f.resolve().parents and f.parents[1].name not in skip and f.parents[2].name not in skip]
    # a picture shown only as one tile of a picture wall (an img/wall/ folder: dozens of thumbnails at once) was never shown as itself
    others = [f for f in others if "wall" not in {p.name for p in f.relative_to(MEDIA).parents}]
    osig = [(f, *s) for f in others for s in [sig(f)] if s[0] is not None]
    named = named_pictures(src, [f.name for f in mine])
    n = 0
    for f in mine:
        md, h = sig(f)
        hits = [(o, "same bytes" if om == md else f"dhash {bin(h ^ oh).count('1')} bits") for o, om, oh in osig
                if om == md or (h is not None and oh is not None and bin(h ^ oh).count("1") <= bits)]
        if hits and named.get(f.name, (False,))[0]:
            print(f"ALLOWED REUSE {f.relative_to(img)}: {named[f.name][1][:120]}")
            continue
        if hits and f.name in named:
            print(f"NAMED-MOMENT REFUSED {f.relative_to(img)}: {named[f.name][1]}")
        if hits:
            n += 1
            print(f"PICTURE {f.relative_to(img)}")
            for o, why in hits[:6]:
                print(f"        = {o.relative_to(MEDIA)}  ({why})")
    print(f"{len(mine)} pictures the code names; {n} also in another video's img/ (across videos is fine: information only)")
    return 0


def said_words(src):
    """the narration's words as one normalised string: the voice's words.json, and while the voice covers only part of the script (a
    build on the placeholder voice) the whole script's placeholder in ph/words.json too, so a named moment beyond the voiced beats is judged"""
    out = []
    for wp in (Path(src) / "words.json", Path(src) / "ph" / "words.json"):
        if wp.exists():
            out.append(" ".join(w for w in (re.sub(r"[^a-z0-9]", "", x["w"].lower().replace("’", "").replace("'", ""))
                                            for x in json.loads(wp.read_text(encoding="utf-8"))) if w))
    return " | ".join(out)


def named_pictures(src, names):
    """picture file name -> (ok, reason) for every picture whose shot says `named-moment: "<the words>" <why>` (the clips' rule for stills:
    an official picture a past video showed comes back only where the line names exactly what it shows): the comment block above the code
    line that names the file, or on it"""
    said = said_words(src)
    out = {}
    for f in code_files(src):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            hit = [n for n in names if n in ln.split("//", 1)[0]]
            if not hit:
                continue
            block = [ln.split("//", 1)[1]] if "//" in ln else []
            k = i - 1
            while k >= 0 and lines[k].strip().startswith("//"):
                block.insert(0, lines[k].strip()[2:])
                k -= 1
            text = " ".join(block)
            if NAMED not in text:
                continue
            reason = text.split(NAMED, 1)[1].strip()
            q = re.search(r"[\"“]([^\"”]{3,})[\"”]", reason)
            if not q:
                ok = (False, f"no quoted words in '{reason[:80]}'")
            else:
                toks = " ".join(x for x in (re.sub(r"[^a-z0-9]", "", y.lower().replace("’", "").replace("'", "")) for y in q.group(1).split()) if x)
                ok = (True, reason[:200]) if toks and f" {toks} " in f" {said} " else (False, f"'{q.group(1)}' is not said in the narration")
            for n in hit:
                out.setdefault(n, ok)
    return out


POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def dist(old_bytes, h):
    """bits apart: one hash against every old frame's (their 8 bytes each)"""
    q = np.array([h], dtype=np.uint64).view(np.uint8)
    return POP[old_bytes ^ q].sum(axis=1, dtype=np.int32)


def old_array(cache, others):
    """every old frame in one array: (the old clips, their frames' hashes as bytes [n x 8], each frame's clip index, its time in its clip)"""
    olds = [p for p in others if str(p) in cache]
    hs, idx, ts = [], [], []
    for i, p in enumerate(olds):
        for k, (h, fl) in enumerate(cache[str(p)]["h"]):
            if not fl:
                hs.append(int(h, 16))
                idx.append(i)
                ts.append(k * 0.25)
    if not hs:
        return [], None, None, None
    return olds, np.array(hs, dtype=np.uint64).view(np.uint8).reshape(-1, 8), np.array(idx), np.array(ts)


def fresh(src, t0, t1, vf, bits, clips):
    """a span of a source, every 0.25 s, held against the old clips (the cache): the runs that no past video played (to pick a
    replacement span from) and the runs that one did, with its clip"""
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    others = sorted(p for p in MEDIA.glob("*/clips/*.mp4") if p.parent.parent.resolve() != clips.parent.resolve())
    olds, bits_old, idx, _ = old_array(cache, others)
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(src)] + (["-t", f"{t1 - t0:.3f}"] if t1 else []) + \
          ["-an", "-vf", (vf + "," if vf else "") + f"fps=4,scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"]
    buf = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.uint8)
    rows = []
    for i in range(buf.size // (W * H)):
        h, fl = dhash_arr(buf[i * W * H:(i + 1) * W * H].reshape(H, W))
        d = dist(bits_old, h)
        j = int(d.argmin())
        used = (not fl) and d[j] <= bits
        rows.append((t0 + i * 0.25, "flat" if fl else (f"{olds[idx[j]].parent.parent.name}/{olds[idx[j]].stem}" if used else "fresh"),
                     int(d[j])))
    run = None
    for t, what, d in rows + [(None, None, 0)]:
        if run and (what != run[1] or t is None):
            print(f"{run[0]:8.2f}-{run[2] + 0.25:8.2f}  {run[1]}")
            run = None
        if t is not None and run is None:
            run = [t, what, t]
        elif run:
            run[2] = t
    print("(a used run is still the line's picture when the words name that exact moment and this is its only source: the shot's comment "
          "carries `named-moment: \"<the words>\" <why it is the only source>` and qa_reused allows it. Never a reason for a text card "
          "in place of the moment the words name)")
    return 0


NAMED = "named-moment:"


def named_moments(src, prep_files):
    """clip name -> (ok, reason) for every clip whose shot says `named-moment: "<the words>" <why>` (a line naming one exact moment shows
    that moment, even if a past video played it; a text card in its place is the fault). Read from the composition's code (the // comment
    block right above the line that names the clip, or on that line) and from the preps (the # comment on or above the clip's entry). The
    quoted words must be in the narration (the src's words.json), so the reason is tied to what is said; else (False, why)."""
    said = said_words(src)
    wp = Path(src) / "words.json"

    def judge(text):
        reason = text.split(NAMED, 1)[1].strip()
        q = re.search(r"[\"“]([^\"”]{3,})[\"”]", reason)
        if not q:
            return False, f"no quoted words in '{reason[:80]}'"
        toks = " ".join(t for t in (re.sub(r"[^a-z0-9]", "", x.lower().replace("’", "").replace("'", "")) for x in q.group(1).split()) if t)
        if not toks or f" {toks} " not in f" {said} ":
            return False, f"'{q.group(1)}' is not said in {wp.parent.name}'s narration"
        return True, reason[:200]

    out = {}
    for f in code_files(src):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            names = re.findall(r"""['"]([A-Za-z0-9_\-]+)['"]""", ln.split("//", 1)[0])
            if not names:
                continue
            block = [ln.split("//", 1)[1]] if "//" in ln else []
            k = i - 1
            while k >= 0 and lines[k].strip().startswith("//"):
                block.insert(0, lines[k].strip()[2:])
                k -= 1
            text = " ".join(block)
            if NAMED in text:
                for n in names:
                    out.setdefault(n, judge(text))
    for pf in prep_files:
        last = ""
        for ln in Path(pf).read_text(encoding="utf-8").splitlines():
            s = ln.strip()
            if s.startswith("#"):
                last = (last + " " + s.lstrip("# ")) if last else s.lstrip("# ")
                continue
            m = re.match(r'\s*"([A-Za-z0-9_\-]+)":\s*\(', ln)
            if m:
                tail = ln.split("#", 1)[1] if "#" in ln else ""
                text = f"{last} {tail}"
                if NAMED in text:
                    out.setdefault(m.group(1), judge(text))
            if not s.startswith("#"):
                last = ""
    return out


def inside(mine, clips, words, cache, a, src, sel=None, manifests=()):
    """the same footage twice INSIDE the composition (one clip five times in a video's last minutes is the fault this catches): every
    clip's 3 frames against every OTHER clip's frames at 4 fps (same match and confirmation as against the past videos), and a clip name
    the code plays in more than one shot. Returns the number of findings."""
    sel = set(sel or mine)                         # the clips to check (--only), each against every clip of the composition
    todo = [n for n in mine if cache.get(f"dense:{clips / (n + '.mp4')}", {}).get("k") != key(clips / f"{n}.mp4")]
    if todo:
        print(f"hashing {len(todo)} of the composition's clips at 4 fps ...", flush=True)
        with ThreadPoolExecutor(a.jobs) as ex:
            for n, hs in zip(todo, ex.map(lambda n: old_hashes(clips / f"{n}.mp4"), todo)):
                cache[f"dense:{clips / (n + '.mp4')}"] = {"k": key(clips / f"{n}.mp4"), "h": hs}
        save(cache)
    hs, idx, ts = [], [], []
    for i, n in enumerate(mine):
        for k, (h, fl) in enumerate(cache[f"dense:{clips / (n + '.mp4')}"]["h"]):
            if not fl:
                hs.append(int(h, 16))
                idx.append(i)
                ts.append(k * 0.25)
    arr, idx, ts = np.array(hs, dtype=np.uint64).view(np.uint8).reshape(-1, 8), np.array(idx), np.array(ts)
    cand, seen = [], set()
    for i, n in enumerate(mine):
        if n not in sel:
            continue
        per = {}
        for k, (h, fl) in enumerate(cache[f"new:{clips / (n + '.mp4')}"]["h"]):
            if fl:
                continue
            d = dist(arr, int(h, 16))
            for r in np.nonzero((d <= a.bits) & (idx != i))[0]:
                j = int(idx[r])
                prev = per.setdefault(j, {}).get(k)
                if prev is None or d[r] < prev[2]:
                    per[j][k] = (k, float(ts[r]), int(d[r]))
        for j, v in per.items():
            pair = frozenset((n, mine[j]))
            if len(v) >= 2 and pair not in seen:
                seen.add(pair)
                cand.append((n, mine[j], list(v.values())))
    durs = {}

    def check(c):
        n, m, ks = c
        f = clips / f"{n}.mp4"
        if n not in durs:
            durs[n] = duration(f)
        ok, cs = confirm(f, [durs[n] * (0.25, 0.5, 0.75)[k] for k, _, _ in ks], clips / f"{m}.mp4", [t for _, t, _ in ks], a.ncc)
        return n, m, [b for _, _, b in ks], ok, cs

    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(check, cand))
    found = sorted([r for r in res if r[3]], key=lambda x: (x[0], x[1]))
    for n, m, ds, _, cs in found:
        print(f"TWICE {n}  [{words.get(n, '')}]\n      = {m}  [{words.get(m, '')}]  (bits {', '.join(map(str, ds))}; "
              f"r {', '.join(f'{c:.2f}' for c in cs)})")
    # one clip name played in more than one shot (code lines, not comments)
    # (the composition's own files: DesignRef* is another composition; a use within 3 lines of the one before is the same shot, e.g.
    # a TV wall's tile and its ground; a later use with a start offset plays on from where the first stopped: other frames)
    code = []
    for f in code_files(src):
        if f.name.startswith("DesignRef"):
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            c = re.split(r"(?<!:)//", ln, maxsplit=1)[0]
            if c.strip():
                code.append((f.relative_to(Path(src).resolve()).as_posix(), i, c))
    names = set(mine) & sel
    uses = {}
    for fn, i, c in code:
        for m in re.finditer(r"""['"]([A-Za-z0-9_\-]+)['"]""", c):
            if m.group(1) in names:
                nxt = " ".join(cc for ff, ii, cc in code if ff == fn and i < ii <= i + 2)   # the element's props may run on
                cont = bool(re.search(r"\b(g?start)\s*[:=]", c + " " + nxt))
                lst = uses.setdefault(m.group(1), [])
                if lst and lst[-1][0] == fn and i - lst[-1][1] <= 3 and not cont:
                    continue
                if not lst or (lst[-1][0], lst[-1][1]) != (fn, i):
                    lst.append((fn, i, cont))
    multi = {n: w for n, w in uses.items() if len([u for u in w if not u[2]]) > 1}
    for n, w in sorted(multi.items()):
        print(f"NAME TWICE {n}  [{words.get(n, '')}]: " + ", ".join(f"{fn}:{i}{' (plays on)' if c else ''}" for fn, i, c in w))
    # the same source file's spans overlapping between two clips (a span cut twice with two different crops hashes apart, e.g. a
    # letterboxed source in one prep and its cover-cropped copy in another)
    ov = span_overlaps(manifests, sel, among=set(mine))
    for n, m, src_name, o in ov:
        print(f"SPAN TWICE {n} and {m}: {src_name} overlap {o:.2f} s")
    print(f"inside: {len(found)} clip pairs show the same footage; {len(multi)} clip names in more than one shot; "
          f"{len(ov)} overlapping spans of one file")
    return len(found) + len(multi) + len(ov)


def manifest_spans(manifests):
    """[(clip, source path lowercased, in, out)] of every clip the manifests cut: the manifest's own spans ({name: [source, in, out]}),
    else its prep's CLIPS (the <name>.py next to <name>_clips.json; a source path relative to the prep's DL, or FOOTAGE)"""
    import importlib.util
    spans = []
    for m in manifests:
        mp = Path(m)
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entries, dl = {}, FOOTAGE
        if isinstance(data, dict) and any(isinstance(v, list) and len(v) >= 3 for v in data.values()):
            entries = data
        else:
            f = mp.with_name(mp.name.replace("_clips.json", ".py"))
            if not f.exists():
                continue
            spec = importlib.util.spec_from_file_location(f"_prep_{f.stem}", f)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except Exception as e:  # noqa: BLE001
                print(f"(span check: {f.name} not readable: {type(e).__name__} {e})")
                continue
            entries, dl = getattr(mod, "CLIPS", {}), getattr(mod, "DL", FOOTAGE)
        for n, e in entries.items():
            if len(e) < 3 or not isinstance(e[1], (int, float)) or not isinstance(e[2], (int, float)):
                continue
            p = Path(e[0]) if Path(e[0]).is_absolute() else Path(dl) / e[0]
            spans.append((n, str(p.resolve()).lower(), float(e[1]), float(e[2])))
    return spans


def span_overlaps(manifests, sel, min_s=0.5, among=None):
    """every pair of the composition's clips whose spans of the SAME source file overlap by min_s or more (read from the manifests or the
    preps' CLIPS, no decoding). Only pairs with at least one clip in sel."""
    spans = manifest_spans(manifests)
    out = []
    by = {}
    for s in spans:
        by.setdefault(s[1], []).append(s)
    for src_name, ss in by.items():
        ss.sort(key=lambda x: x[2])
        for i, (n, _, a, b) in enumerate(ss):
            for m, _, c, d in ss[i + 1:]:
                if c >= b:
                    break
                o = min(b, d) - max(a, c)
                if o >= min_s and n != m and (n in sel or m in sel) and (among is None or (n in among and m in among)):
                    out.append((n, m, Path(src_name).name, o))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True, help="the composition's own clips folder (PUBLIC/<video>/clips)")
    ap.add_argument("--manifests", nargs="*", help="the composition's prep manifests (<prep>_clips.json)")
    ap.add_argument("--bits", type=int, default=6)
    ap.add_argument("--only")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--images", action="store_true", help="the pictures instead: img/ files the code names, byte- or dhash-identical")
    ap.add_argument("--src", help="the composition's src folder (its .tsx files and words.json)")
    ap.add_argument("--ncc", type=float, default=0.8, help="the confirmation's correlation a frame pair needs (2 of the 3)")
    ap.add_argument("--show-rejected", action="store_true")
    ap.add_argument("--skip", nargs="*", help="other videos' folders not to count as past videos (e.g. one built at the same time)")
    ap.add_argument("--no-inside", action="store_true", help="skip the repeats inside the composition")
    ap.add_argument("--inside-only", action="store_true", help="only the repeats inside the composition")
    ap.add_argument("--fresh", nargs="+", metavar="SRC [IN OUT [FILTER]]", help="probe a source span against the old clips")
    a = ap.parse_args()
    if a.fresh:
        f = a.fresh
        return fresh(Path(f[0]), float(f[1]) if len(f) > 1 else 0.0, float(f[2]) if len(f) > 2 else 0.0, f[3] if len(f) > 3 else "",
                     a.bits, Path(a.clips))
    if not a.src:
        ap.error("--src: the composition's src folder")
    if a.images:
        return images(Path(a.clips).parent / "img", Path(a.src), skip=tuple(a.skip or ()))
    clips = Path(a.clips)
    if not a.manifests:
        ap.error("--manifests: the composition's prep manifests (<prep>_clips.json)")
    mans = sorted({f for m in a.manifests for f in (glob.glob(m) or [m])})
    names = []
    for m in mans:
        names += [n for n in json.loads(Path(m).read_text(encoding="utf-8")) if n not in names]
    # only the clips the composition's code plays (a manifest keeps every CLIPS entry, also ones no shot uses any more)
    code = "\n".join(f.read_text(encoding="utf-8") for f in code_files(a.src) if not f.name.startswith("DesignRef"))
    played = set(re.findall(r"""['"]([A-Za-z0-9_\-]+)['"]""", code))
    unplayed = [n for n in names if n not in played]
    names = [n for n in names if n in played]
    if unplayed:
        print(f"({len(unplayed)} manifest clips no shot plays, not checked: {', '.join(unplayed[:12])}{' ...' if len(unplayed) > 12 else ''})")
    if a.only:
        keep = set(a.only.split(","))
        allnames, names = names, [n for n in names if n in keep]
    else:
        allnames = names
    preps = [m.replace("_clips.json", ".py") for m in mans]
    words = words_of([p for p in preps if Path(p).exists()])

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    others = sorted(p for p in MEDIA.glob("*/clips/*.mp4") if p.parent.parent.resolve() != clips.parent.resolve()
                    and p.parent.parent.name not in (a.skip or []))
    todo = [p for p in others if cache.get(str(p), {}).get("k") != key(p)]
    if todo:
        print(f"hashing {len(todo)} other videos' clips (of {len(others)}) ...", flush=True)
        with ThreadPoolExecutor(a.jobs) as ex:
            for i, (p, hs) in enumerate(zip(todo, ex.map(old_hashes, todo)), 1):
                cache[str(p)] = {"k": key(p), "h": hs}
                if i % 200 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
                    save(cache)
    for p in list(cache):
        if p.startswith("new:"):
            continue
        if not Path(p).exists():
            del cache[p]

    mine = [n for n in names if (clips / f"{n}.mp4").exists()]
    missing = [n for n in names if n not in mine]
    todo = [n for n in mine if cache.get(f"new:{clips / (n + '.mp4')}", {}).get("k") != key(clips / f"{n}.mp4")]
    if todo:
        with ThreadPoolExecutor(a.jobs) as ex:
            for n, hs in zip(todo, ex.map(lambda n: new_hashes(clips / f"{n}.mp4"), todo)):
                cache[f"new:{clips / (n + '.mp4')}"] = {"k": key(clips / f"{n}.mp4"), "h": [[f"{h:016x}" if isinstance(h, int) else h, fl]
                                                                                               for h, fl in hs]}
    save(cache)
    twice = 0
    if not a.no_inside:
        every = [n for n in allnames if (clips / f"{n}.mp4").exists()]
        for n in every:                             # the composition's other clips' new 3-frame hashes, for --only runs
            if cache.get(f"new:{clips / (n + '.mp4')}", {}).get("k") != key(clips / f"{n}.mp4"):
                hs = new_hashes(clips / f"{n}.mp4")
                cache[f"new:{clips / (n + '.mp4')}"] = {"k": key(clips / f"{n}.mp4"), "h": [[f"{h:016x}" if isinstance(h, int) else h, fl]
                                                                                               for h, fl in hs]}
        twice = inside(every, clips, words, cache, a, Path(a.src), sel=mine, manifests=mans)
        if a.inside_only:
            return 1 if twice else 0

    olds, bits_old, idx, ts = old_array(cache, others)
    if not olds:
        print("no other clips hashed")
        return 1
    cand = []
    for n in mine:
        fr = cache[f"new:{clips / (n + '.mp4')}"]["h"]
        per = {}
        for k, (h, fl) in enumerate(fr):
            if fl:
                continue
            d = dist(bits_old, int(h, 16))
            for r in np.nonzero(d <= a.bits)[0]:                 # every close old frame; per old clip its closest one
                j = int(idx[r])
                prev = per.setdefault(j, {}).get(k)
                if prev is None or d[r] < prev[2]:
                    per[j][k] = (k, float(ts[r]), int(d[r]))
        per = {j: list(v.values()) for j, v in per.items()}
        for j, ks in per.items():
            if len(ks) >= 2:
                cand.append((n, olds[j], ks))

    # the hash's candidates confirmed on the pictures themselves (48x27 correlation of the same frames)
    durs = {}

    def check(c):
        n, p, ks = c
        f = clips / f"{n}.mp4"
        if n not in durs:
            durs[n] = duration(f)
        ok, cs = confirm(f, [durs[n] * (0.25, 0.5, 0.75)[k] for k, _, _ in ks], p, [t for _, t, _ in ks], a.ncc)
        return n, p, [b for _, _, b in ks], ok, cs

    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(check, cand))
    hits = sorted([r for r in res if r[3]], key=lambda x: (x[0], sum(x[2])))
    # a line that names one exact moment shows that moment, even when a past video played it: the shot's comment says
    # `named-moment: "<the words>" <why it is the only source>`, and the reuse is allowed, never "fixed" by a card
    named = named_moments(Path(a.src), [p for p in preps if Path(p).exists()])
    allowed_hits = [h for h in hits if named.get(h[0], (False,))[0]]
    hits = [h for h in hits if not named.get(h[0], (False,))[0]]
    for n, p, ds, ok, cs in allowed_hits:
        print(f"ALLOWED REUSE (named moment) {n}  = {p.parent.parent.name}/clips/{p.name}: {named[n][1]}")
    for n, (ok, why) in named.items():
        if not ok and n in mine:
            print(f"NAMED-MOMENT REFUSED {n}: {why} (quote the words that name the moment, as the narration says them)")
    for n, p, ds, ok, cs in hits:
        print(f"ACROSS VIDEOS (fine) {n}  [{words.get(n, '')}]\n       ={p.parent.parent.name}/clips/{p.name}  (bits {', '.join(map(str, ds))}; "
              f"r {', '.join(f'{c:.2f}' for c in cs)})")
    if a.show_rejected:
        for n, p, ds, ok, cs in sorted([r for r in res if not r[3]], key=lambda x: x[0]):
            print(f"rejected {n} = {p.parent.parent.name}/clips/{p.name}  (bits {', '.join(map(str, ds))}; r {', '.join(f'{c:.2f}' for c in cs)})")
    if missing:
        print(f"{len(missing)} manifest clips not cut: {', '.join(missing[:20])}")
    print(f"{len(mine)} clips checked against {len(olds)} clips of other videos: {len(set(h[0] for h in hits))} reused "
          f"({len(set(r[0] for r in res)) - len(set(h[0] for h in hits)) - len(set(h[0] for h in allowed_hits))} more by the hash alone, "
          f"not the same picture; {len(set(h[0] for h in allowed_hits))} allowed as named moments)")
    return 1 if twice else 0            # across videos is information; only a repeat inside the film fails


if __name__ == "__main__":
    sys.exit(main())
