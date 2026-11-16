"""Build kb/footage/brain/<key>.json from a source's verified shots (WORK/work/<key>_shots.json), the machine detections
(<key>_det.json), the vision pass's descriptions (WORK/desc/<key>_desc.json: one record per shot id, written by the description pass
from the sheets), the footage catalogue's notes and the asset ledger's "used in".

A record (every coordinate a fraction of the full frame, x0,y0,x1,y1):
  id          "<key>@<start s>" (A1@712.93); for a library clip "LIB1/<stem>@<start s>"
  src, file   the source code and the file's path
  in, out     seconds: the shot's first frame and the first frame of the next shot (exclusive), frame-accurate (f_in, f_out = frame numbers,
              f_out inclusive); dur
  clean_in, clean_out   the span to cut from: after a fade-in, a flash or a dark head, before a fade-out or the next shot
  desc, who, what, action, setting, time, mood   from the vision pass; the catalogue's notes for the same span in `cat`
  flags       dark, lowres, upscaled, letterbox, ui, text, blocked, blur, wide, quiet, action, short, social, tv, fade_in, fade_out, flash_in
  subject     {"label", "start": box, "mid": box, "end": box}: the main subject's box at the clean span's start, middle and end
  v           the 9:16 window for a Short (curate.py's fields): cx, cy, h, and cx1/cy1 when the subject moves; fit = ok | tight | no
  faces       [[name, sim, box]] per frame (SFace against the people folders; "?" = a face no one matched)
  cat         [[star, theme/group, note]] the catalogue's entries inside the shot
  used_in     the videos whose delivered edit played this span (ASSET_LEDGER.json, master_span)
  pic         the picture inside the frame (letterboxed masters)

  EDIT tools/footage/brain_build.py <key> [<key> ...]
  EDIT tools/footage/brain_build.py --lib LIB1      every clip of a library into brain/LIB1.json (each clip's shots from its own work files)
  EDIT tools/footage/brain_build.py --stills [KEY ...]   every stills key of sources.json, or the keys named; kind "image", ids
                                         <KEY>:<path under FOOTAGE>; a description record's "facts" (the research facts the still
                                         shows) is carried into the record
Names in `who` go through kb/footage/names.json ({"alias as written, lower case": "the name records use"}), so every pass writes one
name per person."""
import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402

DESC = B.WORK / "desc"


def _names():
    try:
        d = json.loads(B.NAMES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {str(k).strip().lower(): str(v) for k, v in d.items()} if isinstance(d, dict) else {}


NAMES = _names()


def names(lst):
    out = []
    for n in lst or []:
        n2 = NAMES.get(str(n).strip().lower(), str(n).strip())
        if n2 and n2 not in out:
            out.append(n2)
    return out


def window(boxes, pic, hmin=0.45, margin=0.85, fit_hint=None, wh=(3840, 2160)):
    """A 9:16 window (cx, cy, h, cx1, cy1, fit) that holds the subject's box at the start, middle and end of the shot, whole and centred,
    inside the picture area `pic`. One static window when the subject stays; a pan (cx1/cy1) when it moves more than 6% of the frame.
    h is the window's height as a fraction of the frame height (curate.py), at least hmin (no zoom past ~2.2x), at most the picture's.
    fit: ok = the box fits with room inside a window no taller than the picture; tight = it fits only at the picture's full height
    with no room; no = the box is wider than the tallest window (the vision pass's fit916 wins when given)."""
    x0p, y0p, x1p, y1p = pic
    ph = y1p - y0p
    bs = [b for b in boxes if b]
    if not bs:
        return dict(cx=0.5, cy=round((y0p + y1p) / 2, 3), h=round(ph, 3), fit=fit_hint or "no")
    asp = 9 / 16 * wh[1] / wh[0]          # a window's width as a fraction of the frame width = h * asp (16:9 frames: 0.316)

    def need_h(b, m):
        bw, bh = b[2] - b[0], b[3] - b[1]
        return max(bh / m, (bw / m) / asp)

    hs = [need_h(b, margin) for b in bs]
    h = min(max(max(hs), hmin), ph)
    if max(hs) <= ph:
        fit = "ok"
    elif max(need_h(b, 0.98) for b in bs) <= ph:
        fit = "tight"
    else:
        fit = "no"
    if fit_hint:
        fit = fit_hint
    w = h * asp

    def centre(b):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        # a person taller than the window: keep the head in (the window's top at the box's top): centred is about the subject in the
        # window, and a cut-off head is the mistake
        bh = b[3] - b[1]
        if bh > h * 0.95:
            cy = b[1] + h / 2 - 0.02
        cx = min(max(cx, w / 2), 1 - w / 2)
        cy = min(max(cy, y0p + h / 2), y1p - h / 2)
        return round(cx, 3), round(cy, 3)

    cs = [centre(b) for b in bs]
    c0, c1 = cs[0], cs[-1]
    out = dict(cx=c0[0], cy=c0[1], h=round(h, 3), fit=fit)
    if abs(c1[0] - c0[0]) > 0.06 or abs(c1[1] - c0[1]) > 0.06:
        out["cx1"], out["cy1"] = c1
    else:  # a still window: the mean centre
        out["cx"] = round(sum(c[0] for c in cs) / len(cs), 3)
        out["cy"] = round(sum(c[1] for c in cs) / len(cs), 3)
    return out


def resolve_box(ref, det):
    """A subject reference from the vision pass: "b2" (YOLO box 2 of that frame), "f0" (face 0), or [x0, y0, x1, y1]."""
    if ref is None:
        return None
    if isinstance(ref, list) and len(ref) == 4:
        return [round(float(v), 4) for v in ref]
    if isinstance(ref, str):
        if ref.startswith("b") and ref[1:].isdigit():
            bx = det.get("boxes", [])
            i = int(ref[1:])
            return bx[i][2:6] if i < len(bx) else None
        if ref.startswith("f") and ref[1:].isdigit():
            fs = det.get("faces", [])
            i = int(ref[1:])
            if i < len(fs):
                x0, y0, x1, y1 = fs[i][2:6]
                # a face box stands for the person: widen it to head and shoulders
                fh = y1 - y0
                return [max(0, x0 - fh * 0.8), max(0, y0 - fh * 0.4), min(1, x1 + fh * 0.8), min(1, y1 + fh * 2.0)]
    return None


def cat_entries(key, fps):
    if key not in B.MASTERS:
        return []
    out, seen = [], set()
    for tid, T in B.catalogue().get("themes", {}).items():
        for e in T.get("entries", []):
            if e.get("src") == key and "start_s" in e and (e["start_s"], e["end_s"], e["note"]) not in seen:
                seen.add((e["start_s"], e["end_s"], e["note"]))
                out.append((e["start_s"], e["end_s"], bool(e.get("star")), f"{tid}/{e.get('group', '')}", e["note"], e.get("crop")))
    return out


def _lib_rel(code):
    """A library folder relative to the motion public dir (how the ledger names clip files), or None when it lies elsewhere."""
    try:
        return B.LIBS[code].relative_to(B.PUBLIC).as_posix()
    except ValueError:
        return None


def ledger_uses(key):
    """[(a, b, video)] master spans the delivered edits played, for a master; by file name for a library clip."""
    led = B.ledger()
    out = []
    for vid, v in led.get("videos", {}).items():
        for c in v.get("clips", []):
            m = c.get("master") or {}
            for u in c.get("uses", []):
                if key in B.MASTERS and m.get("master") == key and u.get("master_span"):
                    out.append((u["master_span"][0], u["master_span"][1], vid))
                elif key not in B.MASTERS:
                    code, stem = key.split("/", 1)
                    folder = _lib_rel(code)
                    if folder and c.get("file", "").startswith(f"{folder}/{stem}."):
                        out.append((u.get("from", 0.0), u.get("to", 1e9), vid))
    return out


def clip_master(key):
    """Where a library clip was cut from, when the ledger knows (a prep script's CLIPS entry): {"src", "t", "end"}."""
    if key in B.MASTERS:
        return None
    code, stem = key.split("/", 1)
    rel = _lib_rel(code)
    if rel is None:
        return None
    for v in B.ledger().get("videos", {}).values():
        for c in v.get("clips", []):
            if c.get("master") and c.get("file", "").startswith(f"{rel}/{stem}."):
                m = c["master"]
                return dict(src=m.get("master"), t=m.get("t"), end=m.get("end"))
    return None


def build(key):
    kf = B.key_file(key)
    shots = json.loads((B.WORK / "work" / f"{kf}_shots.json").read_text(encoding="utf-8"))
    fps = shots["fps"]
    import brain_detect
    det = brain_detect.load_all(key)
    desc = {}
    # the descriptions: a file per source, or one per library (<CODE>_desc.json, written from the library's sheets)
    cands = [DESC / f"{kf}_desc.json"] + ([DESC / f"{key.split('/', 1)[0]}_desc.json"] if "/" in key else [])
    for descp in cands:
        if descp.exists():
            for r in json.loads(descp.read_text(encoding="utf-8")):
                desc.setdefault(r["id"], r)
    path = B.source_path(key)
    pic = B.pic_of(key)
    wh = B.size(path)
    cats = cat_entries(key, fps)
    uses = ledger_uses(key)
    recs = []
    for s in shots["shots"]:
        sid = f"{key}@{s['f_in'] / fps:.2f}"
        d = desc.get(sid, {})
        t_in, t_out = s["f_in"] / fps, (s["f_out"] + 1) / fps
        frames = s.get("frames", [])
        fr_det = {f: det.get(f"{f:07d}", {}) for f in frames}
        # the subject's boxes at the start, middle and end: the vision pass's references, else the biggest box the machine saw
        sb = d.get("subject_boxes") or {}
        pick = []
        for f in (frames[0], frames[len(frames) // 2], frames[-1]) if frames else []:
            ref = sb.get(f"f{f}", sb.get(str(f)))
            b = resolve_box(ref, fr_det[f])
            if b is None and ref is None and not d:   # no vision pass yet: the machine's biggest box
                bx = fr_det[f].get("boxes", [])
                b = bx[0][2:6] if bx else None
            pick.append(b)
        v = window(pick, pic, fit_hint=d.get("fit916"), wh=wh)
        flags = sorted(set(s.get("edge_flags", [])) | set(d.get("flags", [])))
        if tuple(pic) != B.FULL:
            flags = sorted(set(flags) | {"letterbox"})
        faces = {f: [[fc[0], fc[1], fc[2:6]] for fc in fr_det[f].get("faces", [])] for f in frames if fr_det[f].get("faces")}
        # a described record's "who" wins, even when empty (DESCRIBE.md: unknown people stay out); the face labels only fill an
        # undescribed shot (a weak face match must never name a stranger)
        who = names(d["who"] if "who" in d else sorted({fc[0] for fl in faces.values() for fc in fl if fc[0] != "?" and fc[1] >= 0.45}))
        # the catalogue's edges were read off a 480p proxy at 2 decimals: an entry belongs to this shot when they share at least
        # 0.3 s or 40% of the entry, whichever is less
        c_in, c_out = s["c_in"] / fps, (s["c_out"] + 1) / fps
        cat = [[st, grp, note] for (a, b, st, grp, note, crop) in cats
               if min(b, c_out) - max(a, c_in) >= min(0.3, 0.4 * max(0.05, b - a))]
        used = sorted({vid for (a, b, vid) in uses if a < t_out - 0.05 and b > t_in + 0.05})
        rec = dict(id=sid, src=key, file=str(path).replace("\\", "/"), size=list(wh), fps=fps, f_in=s["f_in"], f_out=s["f_out"],
                   **{"in": round(t_in, 3), "out": round(t_out, 3)}, dur=round(t_out - t_in, 3),
                   clean_in=round(s["c_in"] / fps, 3), clean_out=round((s["c_out"] + 1) / fps, 3),
                   desc=d.get("desc", ""), who=who, what=d.get("what", []), action=d.get("action", ""), setting=d.get("setting", ""),
                   time=d.get("time", ""), mood=d.get("mood", ""), flags=flags,
                   subject=dict(label=d.get("subject", ""), start=pick[0] if pick else None, mid=pick[1] if len(pick) > 1 else None,
                                end=pick[-1] if pick else None),
                   v=v, faces=faces, text=sorted({w for f in frames for w, *_ in fr_det[f].get("text", [])}), cat=cat, used_in=used, pic=list(pic),
                   frames=frames)
        if key not in B.MASTERS:
            cm = clip_master(key)
            if cm:
                rec["master"] = cm   # the master span this clip was cut from (the ledger's provenance)
        if d.get("moments"):
            rec["moments"] = d["moments"]
        if d.get("text_from") is not None:
            rec["text_from"] = d["text_from"]
        if d.get("missed_cut"):
            rec["missed_cut"] = d["missed_cut"]
        if d.get("facts"):
            rec["facts"] = d["facts"]   # the research facts this shot shows (DESCRIBE.md)
        if d.get("ui"):
            rec["ui"] = d["ui"]         # an on-screen interface read exactly off a full-resolution zoom: {"frame", "read"}
        recs.append(rec)
    return recs


def build_stills(key):
    """A stills key's records (kind "image"): one per still, the catalogue's notes by path, the 9:16 window from the subject's box, and
    "used in" by the file's md5 against the ledger's stills (a byte-identical copy in a motion dir)."""
    import brain_detect
    from brain_sheets import cat_notes_stills
    kf = B.key_file(key)
    shots = json.loads((B.WORK / "work" / f"{kf}_shots.json").read_text(encoding="utf-8"))
    stills = shots["stills"]
    det = brain_detect.load_all(key)
    descp = DESC / f"{kf}_desc.json"
    desc = {}
    if descp.exists():
        for r in json.loads(descp.read_text(encoding="utf-8")):
            desc[r["id"]] = r
    notes = cat_notes_stills(stills)
    led_md5 = {}
    for vid, v in B.ledger().get("videos", {}).items():
        for st in v.get("stills", []):
            if st.get("md5"):
                led_md5.setdefault(st["md5"], set()).add(vid)
    recs = []
    for m in stills:
        sid = f"{key}:{m['rel']}"
        d = desc.get(sid, {})
        fr = det.get(f"{m['index']:07d}", {})
        sb = d.get("subject_boxes") or {}
        ref = next(iter(sb.values()), None)
        box = resolve_box(ref, fr)
        if box is None and not d:
            bx = fr.get("boxes", [])
            box = bx[0][2:6] if bx else None
        W, H = m["size"]
        pic = B.FULL
        v = window([box] if box else [], pic, fit_hint=d.get("fit916"))
        # window() assumes a 16:9 frame; a still of another shape gets its window width corrected
        if W and H and abs(W / H - 16 / 9) > 0.02:
            asp = (9 / 16) * (H / W)
            if box:
                bw, bh = box[2] - box[0], box[3] - box[1]
                h = min(max(bh / 0.85, (bw / 0.85) / asp, 0.45), 1.0)
                v["h"] = round(h, 3)
                v["fit"] = d.get("fit916") or ("ok" if max(bh / 0.85, (bw / 0.85) / asp) <= 1.0 else ("tight" if max(bh / 0.98, (bw / 0.98) / asp) <= 1.0 else "no"))
                v["cx"] = round(min(max((box[0] + box[2]) / 2, h * asp / 2), 1 - h * asp / 2), 3)
                v["cy"] = round(min(max((box[1] + box[3]) / 2, h / 2), 1 - h / 2), 3)
            if W / H < 9 / 16 + 0.02:   # portrait or phone art: the whole picture is the window
                v = dict(cx=0.5, cy=0.5, h=1.0, fit="ok")
        md5 = hashlib.md5(Path(m["path"]).read_bytes()).hexdigest()
        used = sorted(led_md5.get(md5, set()))
        faces = [[fc[0], fc[1], fc[2:6]] for fc in fr.get("faces", [])]
        who = names(d["who"] if "who" in d else sorted({fc[0] for fc in faces if fc[0] != "?" and fc[1] >= 0.45}))
        flags = sorted(set(d.get("flags", [])))
        rec = dict(id=sid, src=key, kind="image", file=m["path"], size=[W, H], variants=m.get("variants", []),
                   desc=d.get("desc", ""), who=who, what=d.get("what", []), action=d.get("action", ""), setting=d.get("setting", ""),
                   time=d.get("time", ""), mood=d.get("mood", ""), flags=flags,
                   subject=dict(label=d.get("subject", ""), start=box, mid=box, end=box), v=v, faces={str(m["index"]): faces} if faces else {},
                   text=sorted({w for w, *_ in fr.get("text", [])}), cat=[[st, grp, note] for (st, grp, note) in notes.get(m["index"], [])],
                   used_in=used, pic=list(pic), frames=[m["index"]], md5=md5)
        if d.get("facts"):
            rec["facts"] = d["facts"]   # the research facts this still shows
        recs.append(rec)
    out = B.BRAIN / f"{key}.json"
    described = sum(1 for r in recs if r["desc"])
    out.write_text(json.dumps(dict(source=key, folder=str(B.STILLS[key]).replace("\\", "/"), built=dt.date.today().isoformat(), described=described,
                                   shots=recs), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{key}: {len(recs)} stills ({described} described) -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--lib")
    ap.add_argument("--stills", nargs="*", help="build every stills key of sources.json, or the keys named")
    a = ap.parse_args()
    B.BRAIN.mkdir(parents=True, exist_ok=True)
    if a.stills is not None:
        for key in (a.stills or list(B.STILLS)):
            build_stills(key)
        return
    if a.lib:
        code = a.lib
        recs, clips = [], []
        for p in B.lib_files(code):
            key = f"{code}/{p.stem}"
            if (B.WORK / "work" / f"{B.key_file(key)}_shots.json").exists():
                r = build(key)
                recs += r
                clips.append(dict(key=key, file=str(p).replace("\\", "/"), shots=len(r)))
        out = B.BRAIN / f"{code}.json"
        out.write_text(json.dumps(dict(source=code, folder=str(B.LIBS[code]).replace("\\", "/"), built=dt.date.today().isoformat(), clips=clips,
                                       shots=recs), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{code}: {len(clips)} clips, {len(recs)} shots -> {out}")
        return
    for key in a.keys:
        recs = build(key)
        m = B.MASTERS[key]
        out = B.BRAIN / f"{key}.json"
        described = sum(1 for r in recs if r["desc"])
        out.write_text(json.dumps(dict(source=key, title=m["title"], file=str(m["file"]).replace("\\", "/"), pic=list(m["pic"]),
                                       built=dt.date.today().isoformat(), described=described, shots=recs), indent=1, ensure_ascii=False),
                       encoding="utf-8")
        print(f"{key}: {len(recs)} shots ({described} described) -> {out}")


if __name__ == "__main__":
    main()
