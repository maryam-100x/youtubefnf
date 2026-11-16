"""A hand-picked Short (one at a time, every cut a new picture that matches its words, picked from all the footage):
src/shorts_cur/pN.json (the shots per beat, the phrase each starts on, the 9:16 framing) on the Short's own voice (src/sNNN/words.json
and beats.json, NNN = N in three digits; N is the Short's number, video.toml `curated = N`). Each shot names a master by its key
(data/curate_masters.json) and an in-point, or a still (img, a path under the media root).

  sheet: every shot's 9:16 window at the start, middle and end of its slot, a row per beat with its words: the check by eye BEFORE a
         render (the subject in the middle, the action inside the slot, nothing repeated).
  cut:   the vertical clips and stills (1080x1920) cut from the masters into PUBLIC/curated/pN/, src/shorts_cur/rN.json (the resolved
         timeline ShortCurated.tsx plays) and the clips' last frames into src/clipdurs.json.

  PIPE tools/motion/curate.py sheet N <out.jpg>
  PIPE tools/motion/curate.py cut N [--redo key ...]
The masters are cut in a 3840x2160 frame (VW x VH): every window is computed in it."""
import json
import re
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, FOOTAGE, MEDIA, PUBLIC  # noqa: E402

HERE = Path(__file__).resolve().parent
MOTION = PUBLIC
# the masters a shot names by key: data/curate_masters.json {"<key>": "<path under FOOTAGE, or absolute>"}
_MASTERS = HERE / "data" / "curate_masters.json"
SRC = {k: (Path(v) if Path(v).is_absolute() else FOOTAGE / v)
       for k, v in (json.loads(_MASTERS.read_text(encoding="utf-8")) if _MASTERS.exists() else {}).items()}
VW, VH = 3840, 2160
LIFT = "eq=brightness=0.05:contrast=1.06:gamma=1.35,"   # a dark shot lifted: a near-black window shows nothing to see
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "").replace("'", ""))


def voice_dir(n):
    """The Short's own folder in src/ (its words.json and beats.json from the voice step)."""
    return HERE / "src" / f"s{n:03d}"


def out_dir(n):
    """Where the Short's cut clips and stills go in the public dir (and their published paths' prefix)."""
    return f"curated/p{n}"


def resolve(n):
    """The Short's shots with their slots: [(beat, shot, a, b, words)]."""
    d = voice_dir(n)
    words = json.loads((d / "words.json").read_text(encoding="utf-8"))
    beats = json.loads((d / "beats.json").read_text(encoding="utf-8"))
    spec = json.loads((HERE / f"src/shorts_cur/p{n}.json").read_text(encoding="utf-8"))
    out = []
    for bt in beats["beats"]:
        ws = [w for w in words if w["beat"] == bt["id"]]
        shots = spec.get(bt["id"], [])
        times = []
        for s in shots:
            at, off = s.get("at", 0), 0.0
            if isinstance(at, list):   # [phrase, seconds]: the cut a little before or after the phrase (a source cut, a clip's end)
                at, off = at
            if not at:
                times.append(bt["start"])
                continue
            toks = [norm(x) for x in at.split()]
            hit = [ws[i]["start"] for i in range(len(ws) - len(toks) + 1) if all(norm(ws[i + k]["w"]) == toks[k] for k in range(len(toks)))]
            if not hit:
                raise SystemExit(f"{bt['id']} {s['key']}: '{at}' is not in the words")
            times.append(hit[0] + off)
        for i, s in enumerate(shots):
            a, b = times[i], times[i + 1] if i + 1 < len(shots) else bt["end"]
            if b - a < 0.25:
                raise SystemExit(f"{bt['id']} {s['key']}: a {b - a:.2f} s slot")
            out.append((bt["id"], s, a, b, " ".join(w["w"] for w in ws if a - 0.01 <= w["start"] < b - 0.01)))
    return out, beats


def source_cuts(shots):
    """Video shots whose slot runs over a camera cut inside the source: a flash of another picture unless it's meant (xcut: true, a
    source's own cut the shot is about). The cuts come from the footage index's shot edges (FOOTAGE/index/labels_restored.jsonl,
    video_shot entries) and, for a master the index lacks, FOOTAGE/index/<key>_cuts.txt (cut times in seconds, e.g. ffmpeg's scene
    cuts)."""
    by_name = {p.name: k for k, p in SRC.items()}
    edges = {}
    idx = FOOTAGE / "index/labels_restored.jsonl"
    if idx.exists():
        for line in idx.open(encoding="utf-8"):
            x = json.loads(line)
            if x["type"] == "video_shot" and Path(x["path"]).name in by_name:
                edges.setdefault(by_name[Path(x["path"]).name], set()).add(round(x["start_s"], 2))
    for k in SRC:
        extra = FOOTAGE / f"index/{k}_cuts.txt"
        if extra.exists():
            edges.setdefault(k, set()).update(round(float(v), 2) for v in extra.read_text().split())
    bad = []
    for bt, s0, a, b, ws in shots:
        for s in (s0, s0.get("bg") or {}):
            if "src" not in s or s.get("xcut"):
                continue
            t0, t1 = s["t"], s["t"] + (b - a)
            for e in sorted(edges.get(s["src"], ())):
                if t0 + 0.04 < e < t1 - 0.04:
                    bad.append(f"{bt} {s0['key']}{' bg' if s is not s0 else ''}: {s['src']} cuts at {e:.2f} ({e - t0:.2f} s into a {t1 - t0:.2f} s slot)")
    return bad


def at_f(s, f):
    """The shot's framing at fraction f of its slot. A window can pan to follow a subject that moves across the frame: cx1/cy1 are its
    centre at the slot's end (cx/cy at its start), eased in and out (smoothstep); h stays."""
    if "cx1" not in s and "cy1" not in s:
        return s
    e = f * f * (3 - 2 * f)
    s2 = dict(s)
    for k in ("cx", "cy"):
        v0 = s.get(k, 0.5)
        s2[k] = v0 + (s.get(k + "1", v0) - v0) * e
    return s2


def box(W, H, s, aspect=9 / 16):
    ch = s.get("h", 1.0) * H
    cw = ch * aspect
    if cw > W:
        cw, ch = W, W / aspect
    x0 = min(max(s.get("cx", 0.5) * W - cw / 2, 0), W - cw)
    y0 = min(max(s.get("cy", 0.5) * H - ch / 2, 0), H - ch)
    return int(x0) // 2 * 2, int(y0) // 2 * 2, int(cw) // 2 * 2, int(ch) // 2 * 2


def grab(s, t, w=180, h=320):
    """The shot's 9:16 window at second t of the source (stills: the picture)."""
    if s.get("gfx"):   # our own graphic: its background, or a plain plate with its name
        if "bg" in s:
            return grab(s["bg"], s["bg"].get("t", 0) + (t - s.get("t", 0)), w, h)
        im = Image.new("RGB", (w, h), (24, 30, 44))
        ImageDraw.Draw(im).text((8, h // 2), s["gfx"], fill="white")
        return im
    if s.get("end") and "img" not in s:   # the end card without a picture named: a plain plate
        im = Image.new("RGB", (w, h), (20, 20, 24))
        ImageDraw.Draw(im).text((8, h // 2), "end", fill="white")
        return im
    if s.get("card") or s.get("vertical") or s.get("end"):
        im = Image.open(MEDIA / s["img"]).convert("RGB")
        im.thumbnail((w, h))
        bg = Image.new("RGB", (w, h), (20, 20, 24))
        bg.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
        return bg
    if "img" in s:
        im = Image.open(MEDIA / s["img"]).convert("RGB")
        x0, y0, cw, ch = box(im.width, im.height, s)
        return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h))
    x0, y0, cw, ch = box(VW, VH, s)
    vf = f"crop={cw}:{ch}:{x0}:{y0},{LIFT if s.get('lift') else ''}scale={w}:{h}"
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", str(SRC[s["src"]]), "-frames:v", "1", "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (w, h), raw) if len(raw) == w * h * 3 else Image.new("RGB", (w, h), "red")


def sheet(n, out):
    shots, _ = resolve(n)
    for line in source_cuts(shots):
        print("SOURCE CUT", line)
    TW, TH, TXT = 120, 213, 70
    rows = {}
    for bt, s, a, b, ws in shots:
        rows.setdefault(bt, []).append((s, a, b, ws))
    jobs = []
    for bt, lst in rows.items():
        for s, a, b, ws in lst:
            d = b - a
            for f in (0.08, 0.5, 0.92):
                jobs.append((at_f(s, f), s.get("t", 0) + f * d))
    with ThreadPoolExecutor(6) as ex:
        ims = list(ex.map(lambda j: grab(j[0], j[1], TW, TH), jobs))
    cols = max(len(lst) for lst in rows.values()) * 3
    W = cols * TW + (cols // 3) * 8 + 50
    sheet = Image.new("RGB", (W, len(rows) * (TH + TXT)), "white")
    d = ImageDraw.Draw(sheet)
    k = 0
    for r, (bt, lst) in enumerate(rows.items()):
        y = r * (TH + TXT)
        d.text((4, y + 4), bt, fill="black")
        x = 50
        for s, a, b, ws in lst:
            for _ in range(3):
                sheet.paste(ims[k], (x, y))
                x += TW
                k += 1
            lab = f"{s['key']} {a:.2f}+{b - a:.2f}s"
            d.text((x - 3 * TW + 2, y + TH + 2), lab, fill="black")
            for i, line in enumerate(textwrap.wrap(ws, 58)[:3]):
                d.text((x - 3 * TW + 2, y + TH + 15 + i * 13), line, fill="#333")
            x += 8
    sheet.save(out, quality=86)
    print(len(shots), "shots ->", out)


def probe(p):
    o = subprocess.run([FFPROBE, "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets,r_frame_rate",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip().split(",")
    a, b = o[0].split("/")
    return int(o[1]), float(a) / float(b)


def cut(n, redo):
    shots, beats = resolve(n)
    rel = out_dir(n)
    vd = MOTION / rel
    vd.mkdir(parents=True, exist_ok=True)
    durs = json.loads((HERE / "src/clipdurs.json").read_text(encoding="utf-8"))
    sigf = vd / "sigs.json"   # what each file was cut from: a changed in-point, framing or length re-cuts it
    sigs = json.loads(sigf.read_text(encoding="utf-8")) if sigf.exists() else {}
    tl = []

    def make(s, name, dur):
        """A 9:16 video or still of `s` (src+t or img, framing) for `dur` s: (kind, published path)."""
        ext = "jpg" if "img" in s else "mp4"
        out = vd / f"{name}.{ext}"
        sig = json.dumps([s.get("img"), s.get("src"), s.get("t"), s.get("cx"), s.get("cy"), s.get("h"), s.get("lift"), None if "img" in s else round(dur, 3)]
                         + ([s.get("cx1"), s.get("cy1")] if ("cx1" in s or "cy1" in s) else []))
        if not out.exists() or name in redo or sigs.get(name) != sig:
            if "img" in s:
                im = Image.open(MEDIA / s["img"]).convert("RGB")
                x0, y0, cw, ch = box(im.width, im.height, s)
                im.crop((x0, y0, x0 + cw, y0 + ch)).resize((1080, 1920), Image.LANCZOS).save(out, quality=93)
            else:
                x0, y0, cw, ch = box(VW, VH, s)
                if "cx1" in s or "cy1" in s:   # the window pans over the slot, eased (at_f): ffmpeg evaluates the crop's x/y per frame
                    x1, y1, _, _ = box(VW, VH, at_f(s, 1.0))
                    p = f"st(0,min(t/{dur:.3f},1));st(1,ld(0)*ld(0)*(3-2*ld(0)))"
                    cropf = f"crop=w={cw}:h={ch}:x='{p};{x0}+({x1 - x0})*ld(1)':y='{p};{y0}+({y1 - y0})*ld(1)'"
                else:
                    cropf = f"crop={cw}:{ch}:{x0}:{y0}"
                vf = f"{cropf},{LIFT if s.get('lift') else ''}scale=1080:1920:flags=lanczos,setsar=1"
                subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s['t']:.3f}", "-t", f"{dur + 0.2:.3f}", "-i", str(SRC[s["src"]]),
                                "-an", "-vf", vf, "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", "-bf", "0", str(out)],
                               check=True)
            sigs[name] = sig
            print("cut", name)
        return ("img" if ext == "jpg" else "video"), f"{rel}/{name}.{ext}"

    def make_inset(s, name, dur):
        """A detail of the source frame (inset: [x0, y0, x1, y1], fractions of it) at its own shape, 960 px wide: shown big over the shot
        (a small on-screen detail, an icon or a counter, too small to read in a 9:16 crop of the whole frame)."""
        x0, y0, x1, y1 = s["inset"]
        cw, ch = int((x1 - x0) * VW) // 2 * 2, int((y1 - y0) * VH) // 2 * 2
        ow, oh = 960, int(960 * ch / cw) // 2 * 2
        out = vd / f"{name}.mp4"
        sig = json.dumps([s.get("src"), s.get("t"), s["inset"], round(dur, 3)])
        if not out.exists() or name in redo or sigs.get(name) != sig:
            vf = f"crop={cw}:{ch}:{int(x0 * VW) // 2 * 2}:{int(y0 * VH) // 2 * 2},scale={ow}:{oh}:flags=lanczos,setsar=1"
            subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s['t']:.3f}", "-t", f"{dur + 0.2:.3f}", "-i", str(SRC[s["src"]]),
                            "-an", "-vf", vf, "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", "-bf", "0", str(out)],
                           check=True)
            sigs[name] = sig
            print("cut", name)
        return {"kind": "video", "src": f"{rel}/{name}.mp4", "iw": ow, "ih": oh}

    def one(item):
        bt, s, a, b, ws = item
        e = {"beat": bt, "key": s["key"], "a": round(a, 4), "b": round(b, 4)}
        for f in ("label", "rc", "rc_c", "rc_marks", "credit", "push"):   # push: a still's end scale (ShortCurated.tsx's default 1.06)
            if f in s:
                e[f] = s[f]
        if s.get("end"):
            e["kind"] = "end"
            return e
        if s.get("gfx"):   # our own graphic (src/shorts_cur/gfx.tsx), over the beat's footage when it has a bg
            e.update(kind="gfx", gfx=s["gfx"])
            if "bg" in s:
                k, p = make(s["bg"], f"{s['key']}_bg", b - a)
                e["bg"] = {"kind": k, "src": p}
            return e
        if s.get("card") or s.get("vertical"):
            e.update(kind="card" if s.get("card") else "vimg", src=s["img"].removeprefix("motion/"))
            if "bg" in s:   # the beat's own footage behind the picture: nothing empty to look at
                k, p = make(s["bg"], f"{s['key']}_bg", b - a)
                e["bg"] = {"kind": k, "src": p}
            return e
        k, p = make(s, s["key"], b - a)
        e.update(kind=k, src=p)
        if "inset" in s:
            e["inset"] = make_inset(s, f"{s['key']}_inset", b - a)
        return e

    for line in source_cuts(shots):
        print("SOURCE CUT", line)
    with ThreadPoolExecutor(4) as ex:
        tl = list(ex.map(one, shots))
    sigf.write_text(json.dumps(sigs, indent=1), encoding="utf-8")
    for e in tl:
        for m in (e, e.get("bg") or {}, e.get("inset") or {}):
            if m.get("kind") == "video":
                cnt, fps = probe(MOTION / m["src"])
                durs[m["src"]] = [round((cnt - 1) / fps, 4), fps]
    (HERE / "src/clipdurs.json").write_text(json.dumps(durs, indent=1), encoding="utf-8")
    # the Short stops ~0.4 s after the last word (standard/SHORTS.md "The end"): a longer tail reads as dead air
    words = json.loads((voice_dir(n) / "words.json").read_text(encoding="utf-8"))
    dur = min(beats["duration"], round(max(w["end"] for w in words) + 0.4, 3))
    r = {"n": n, "duration": dur, "beats": beats["beats"], "shots": tl}
    (HERE / f"src/shorts_cur/r{n}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(tl), "shots ->", HERE / f"src/shorts_cur/r{n}.json")


if __name__ == "__main__":
    mode, n = sys.argv[1], int(sys.argv[2])
    if mode == "sheet":
        sheet(n, sys.argv[3])
    else:
        cut(n, set(sys.argv[sys.argv.index("--redo") + 1:]) if "--redo" in sys.argv else set())
