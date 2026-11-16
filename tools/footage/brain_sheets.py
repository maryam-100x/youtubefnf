"""The description sheets: what the vision pass reads to write each shot's record. One row per shot: its frames (start, middle, end of
the clean span, more for a long shot) at 480x270 with a 10% grid (numbers along the top and left edges: a box is read in 0-1 frame
coordinates), the machine's boxes drawn and numbered (YOLO: yellow; faces: green with the name SFace gives), and a header line with
the shot id, its times, length, measured flags, the OCR'd words and the footage catalogue's notes for any span inside it. Six rows a
sheet -> WORK/sheets/<key>/<key>_desc_NNN.jpg, and the list of what each sheet holds -> WORK/sheets/<key>/index.json.

  EDIT tools/footage/brain_sheets.py <key> [--rows 6] [--tile 480]     (stills read better with --tile 960 --rows 4)
  EDIT tools/footage/brain_sheets.py <CODE> --lib                      one sheet set for all the clips of a library"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402
from sheetfont import font as sheet_font  # noqa: E402

TW, TH = 480, 270


def cat_notes_stills(stills):
    """The catalogue's notes on stills, by path: {index: [(star, theme/group, note)]}; an artwork's variants share its note."""
    by_rel = {}
    for tid, T in B.catalogue().get("themes", {}).items():
        for e in T.get("entries", []):
            if e.get("src") in B.STILLS and "path" in e:
                by_rel.setdefault(e["path"], []).append((bool(e.get("star")), f"{tid}/{e.get('group', '')}", e["note"]))
    out = {}
    for m in stills:
        notes = by_rel.get(m["rel"], [])
        if not notes:
            for v in m.get("variants", []):
                notes = by_rel.get(B.rel_footage(v), [])
                if notes:
                    break
        seen, uniq = set(), []
        for n in notes:
            if n[2] not in seen:
                seen.add(n[2])
                uniq.append(n)
        out[m["index"]] = uniq
    return out


def cat_notes(key, fps):
    """The catalogue's entries on this source: [(start_f, end_f, star, theme/group, note)]."""
    if key not in B.MASTERS:
        return []
    out, seen = [], set()
    for tid, T in B.catalogue().get("themes", {}).items():
        for e in T.get("entries", []):
            if e.get("src") == key and "start_s" in e:
                k = (e["start_s"], e["end_s"], e["note"])
                if k in seen:
                    continue
                seen.add(k)
                out.append((int(round(e["start_s"] * fps)), int(round(e["end_s"] * fps)), e.get("star", False), f"{tid}/{e.get('group', '')}", e["note"]))
    return out


def shot_id(key, f, fps):
    return f"{key}@{f / fps:.2f}"


def draw_frame(p, det, label, font):
    """One tile: the picture (a still of another shape is fitted on the tile), the 10% grid and the machine's boxes in the picture's
    own 0-1 coordinates."""
    src = Image.open(p).convert("RGB")
    if abs(src.width / src.height - 16 / 9) < 0.02:
        im, ox, oy, pw, ph = src.resize((TW, TH), Image.BILINEAR), 0, 0, TW, TH
    else:
        k = min(TW / src.width, TH / src.height)
        pw, ph = max(1, int(src.width * k)), max(1, int(src.height * k))
        ox, oy = (TW - pw) // 2, (TH - ph) // 2
        im = Image.new("RGB", (TW, TH), (40, 40, 46))
        im.paste(src.resize((pw, ph), Image.BILINEAR), (ox, oy))
    d = ImageDraw.Draw(im)
    P = lambda x, y: (ox + x * pw, oy + y * ph)   # picture 0-1 -> tile pixels  # noqa: E731
    for g in range(1, 10):
        x, y = P(g / 10, g / 10)
        d.line([x, oy, x, oy + ph], fill=(255, 255, 255), width=1)
        d.line([ox, y, ox + pw, y], fill=(255, 255, 255), width=1)
        d.text((x + 1, oy + 1), str(g), fill=(255, 255, 0), font=font)
        d.text((ox + 1, y + 1), str(g), fill=(0, 255, 255), font=font)
    for i, b in enumerate(det.get("boxes", [])[:8]):
        cls, cf, x0, y0, x1, y1 = b
        d.rectangle([*P(x0, y0), *P(x1, y1)], outline=(255, 210, 0), width=2)
        d.text((P(x0, y0)[0] + 2, P(x0, y0)[1] + 1), f"{i}:{cls}", fill=(255, 210, 0), font=font)
    for fc in det.get("faces", []):
        name, sim, x0, y0, x1, y1 = fc
        d.rectangle([*P(x0, y0), *P(x1, y1)], outline=(0, 255, 80), width=2)
        d.text((P(x0, y0)[0] + 2, max(0, P(x0, y0)[1] - 12)), f"{name} {sim:.2f}", fill=(0, 255, 80), font=font)
    d.text((2, TH - 13), label, fill=(255, 255, 255), font=font)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key", help="a source key, or a library code with --lib (one sheet set for all its clips)")
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--tile", type=int, default=480, help="tile width (stills read better at 960)")
    ap.add_argument("--lib", action="store_true")
    a = ap.parse_args()
    global TW, TH
    TW, TH = a.tile, a.tile * 9 // 16
    import brain_detect
    key = a.key
    if a.lib:
        # every clip's shots in one list; each row keeps its clip key (the id is "<code>/<stem>@<s>")
        rows_all, det, fps_of, fdir_of = [], {}, {}, {}
        for p in B.lib_files(key):
            k = f"{key}/{p.stem}"
            sp = B.WORK / "work" / f"{B.key_file(k)}_shots.json"
            if not sp.exists():
                continue
            sh = json.loads(sp.read_text(encoding="utf-8"))
            for s in sh["shots"]:
                s["_key"] = k
                rows_all.append(s)
            for f, x in brain_detect.load_all(k).items():
                det[f"{k}|{f}"] = x
            fps_of[k], fdir_of[k] = sh["fps"], B.WORK / "frames" / B.key_file(k)
        shots = dict(shots=rows_all, fps=None)
        kf = key
        stills, notes, snotes = {}, [], {}
        fps = None
        fdir = None
    else:
        kf = B.key_file(key)
        shots = json.loads((B.WORK / "work" / f"{kf}_shots.json").read_text(encoding="utf-8"))
        fps = shots["fps"]
        det = brain_detect.load_all(key)
        stills = {m["index"]: m for m in shots.get("stills", [])}
        notes = cat_notes(key, fps) if not stills else []
        snotes = cat_notes_stills(list(stills.values())) if stills else {}
        fdir = B.WORK / "frames" / kf
        fps_of = fdir_of = None
    out = B.WORK / "sheets" / kf
    out.mkdir(parents=True, exist_ok=True)
    font, hfont = sheet_font(11), sheet_font(14)
    LH = 40
    index = []
    maxcols = max(len(s["frames"]) for s in shots["shots"])
    cols = min(maxcols, 6)
    for p0 in range(0, len(shots["shots"]), a.rows):
        chunk = shots["shots"][p0:p0 + a.rows]
        sheet = Image.new("RGB", (cols * (TW + 4), len(chunk) * (TH + LH + 6)), (16, 16, 20))
        dr = ImageDraw.Draw(sheet)
        rows = []
        for r, s in enumerate(chunk):
            y = r * (TH + LH + 6)
            if a.lib:   # per-clip detections, frame rate and frames folder
                k = s["_key"]
                fps, fdir = fps_of[k], fdir_of[k]
                getdet = lambda f, k=k: det.get(f"{k}|{f:07d}", {})  # noqa: E731
            else:
                getdet = lambda f: det.get(f"{f:07d}", {})  # noqa: E731
            ocr = sorted({w for f in s["frames"] for w, *_ in getdet(f).get("text", [])})
            if a.lib:
                sid = f"{s['_key']}@{s['f_in'] / fps:.2f}"
                dur = (s["f_out"] - s["f_in"] + 1) / fps
                cn = []
                head = (f"{sid}  frames {s['f_in']}-{s['f_out']} ({B.mmss(s['f_in'] / fps)}-{B.mmss((s['f_out'] + 1) / fps)}, {dur:.2f} s, {fps:.3g} fps)  "
                        f"clean {s['c_in']}-{s['c_out']}  {' '.join(s['edge_flags'])}")
            elif stills:
                m = stills[s["f_in"]]
                sid = f"{key}:{m['rel']}"
                cn = [f"{'★ ' if st else ''}{grp}: {note}" for (st, grp, note) in snotes.get(s["f_in"], [])]
                head = f"{sid}  {m['size'][0]}x{m['size'][1]}" + (f"  +{len(m['variants'])} variants" if m.get("variants") else "")
            else:
                sid = shot_id(key, s["f_in"], fps)
                dur = (s["f_out"] - s["f_in"] + 1) / fps
                cn = [f"{'★ ' if st else ''}{grp}: {note}" for (a0, b0, st, grp, note) in notes if a0 < s["f_out"] - 2 and b0 > s["f_in"] + 2]
                head = (f"{sid}  frames {s['f_in']}-{s['f_out']} ({B.mmss(s['f_in'] / fps)}-{B.mmss((s['f_out'] + 1) / fps)}, {dur:.2f} s)  "
                        f"clean {s['c_in']}-{s['c_out']}  {' '.join(s['edge_flags'])}")
            dr.text((4, y + 2), head, fill=(255, 230, 0), font=hfont)
            line2 = (("OCR: " + " | ".join(ocr)[:150] + "   ") if ocr else "") + ("CAT: " + " || ".join(cn)[:400] if cn else "")
            dr.text((4, y + 20), line2[:260], fill=(200, 200, 200), font=font)
            fl = s["frames"]
            # at most `cols` frames: start, end and evenly spaced ones between
            if len(fl) > cols:
                idx = [round(i * (len(fl) - 1) / (cols - 1)) for i in range(cols)]
                fl = [fl[i] for i in idx]
            for c, f in enumerate(fl):
                p = fdir / f"{f:07d}.jpg"
                if not p.exists():
                    continue
                lab = f"f{f} {B.mmss(f / fps)}" if not stills else Path(stills[s["f_in"]]["rel"]).name[:40]
                im = draw_frame(p, getdet(f), lab, font)
                sheet.paste(im, (c * (TW + 4), y + LH))
            rows.append(dict(id=sid, key=s.get("_key", key), f_in=s["f_in"], f_out=s["f_out"], c_in=s["c_in"], c_out=s["c_out"], frames=fl, ocr=ocr, cat=cn,
                             edge_flags=s["edge_flags"]))
        name = out / f"{kf}_desc_{p0 // a.rows + 1:03d}.jpg"
        sheet.save(name, quality=85)
        index.append(dict(sheet=str(name), shots=rows))
    (out / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{key}: {len(shots['shots'])} shots on {len(index)} sheets -> {out}")


if __name__ == "__main__":
    main()
