"""Shot boundaries for the footage brain, frame-accurate and verified by eye: the source's own cuts are found frame by frame before any
in-point is set, so a clip never opens or ends on frames of the neighbouring shot.

  proxy      <key>            a master's 480p proxy (FOOTAGE/index/proxies/<stem>_480p.mp4: the same timeline frame for frame), which
                              features, strips and the sheets read; without one they read the full file (slower)
  features   <key>            per-frame measures of the whole file (its 480p proxy for a master): colour-histogram distance and pixel
                              difference to the frame before, mean luma, white and black fractions -> WORK/work/<key>_feat.npz
  candidates <key>            cut candidates from the features (hard cuts, fades through black, flashes, dissolves), merged with the
                              footage catalogue's edges -> WORK/work/<key>_cands.json
  strips     <key> <out dir>  one strip per candidate (the 3 frames before the cut | the 3 from it, frame numbers under them),
                              12 strips a sheet, to be read by eye (VERIFY_CUTS.md); the verdicts go into WORK/work/<key>_verdicts.json
  apply      <key>            verdicts + features -> WORK/work/<key>_shots.json: every shot's first and last frame, and its clean span
                              (after a fade-in or a flash, before a fade-out or the next shot)
  longscan   <key> [out dir]  cuts the candidates missed inside long takes (pixel-difference spikes): strips to read by eye
  beats      <key>            split long continuous takes (> 12 s) into beats at the catalogue's moment edges (no cut: cont_in /
                              cont_out) -> WORK/work/<key>_beats.json, then apply
  strips_lib <CODE> <out dir> one set of sheets for a whole clip library (rows headed "<clip stem>#<frame>"); the verdicts go into
                              WORK/work/<CODE>_verdicts.json keyed the same way, and apply_lib <CODE> applies them clip by clip

Verdict file: {"<candidate frame>": "ok" | "+1" | "-1" | "+2" | "-2" | "no" | "dissolve <first frame> <last frame>"} (missing = "ok");
a frame that was no candidate with the value "cut" adds a cut the strips did not propose.
A frame with the value "beat" is no cut: a beat edge `beats` must use inside a long take (a screen in the picture changing in one shot).

Run with the editing python (numpy, Pillow): EDIT tools/footage/brain_cuts.py ..."""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402
from sheetfont import font  # noqa: E402

WORKD = B.WORK / "work"
FW, FH = 128, 72          # the analysis frame
# strips grab their frames with this many ffmpeg processes at once (BRAIN_FF_WORKERS=1: one ffmpeg at a time on a busy machine)
FF_WORKERS = int(os.environ.get("BRAIN_FF_WORKERS", "6"))


def feat_path(key):
    return WORKD / f"{B.key_file(key)}_feat.npz"


def proxy(key):
    """The 480p proxy of a master: every frame kept, scaled to 480 px high (libx264 veryfast crf 23, no audio)."""
    m = B.MASTERS[key]
    out = Path(m["proxy"])
    if out.exists():
        print(f"{key}: proxy already there -> {out}")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([B.FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(m["file"]), "-vf", "scale=-2:480", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "23", "-an", str(out)], check=True)
    a, b = B.probe(m["file"])[3], B.probe(out)[3]
    print(f"{key}: proxy -> {out} ({b} frames; the file has {a}{'' if a == b else ': NOT the same count, check before using it'})")


def features(key):
    """Decode the whole file once (ffmpeg -> 128x72 RGB) and measure every frame against the one before."""
    path = B.source_path(key)
    src = B.proxy_or_file(key)
    w, h, fps, n, dur = B.probe(path)
    # the GPU decodes (NVDEC) when it can: the CPU is busy with the detections; a machine or codec it can't take falls back to software
    cmd = [B.FFMPEG, "-v", "error", "-hwaccel", "cuda", "-i", str(src), "-vf", f"scale={FW}:{FH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=FW * FH * 3 * 64)
    first = proc.stdout.read(FW * FH * 3)
    if len(first) < FW * FH * 3:
        proc.kill()
        cmd = [B.FFMPEG, "-v", "error", "-i", str(src), "-vf", f"scale={FW}:{FH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=FW * FH * 3 * 64)
        first = proc.stdout.read(FW * FH * 3)
    hd, d1, luma, white, black, d12 = [], [], [], [], [], []
    prev_hist, prev_gray, grays = None, None, []
    sz = FW * FH * 3
    pending = first
    while True:
        buf = pending if pending is not None else proc.stdout.read(sz)
        pending = None
        if len(buf) < sz:
            break
        im = np.frombuffer(buf, np.uint8).reshape(FH, FW, 3)
        g = im.astype(np.float32).mean(axis=2)
        hist = np.concatenate([np.bincount((im[..., c] >> 3).ravel(), minlength=32) for c in range(3)]).astype(np.float32)
        hist /= hist.sum()
        hd.append(0.0 if prev_hist is None else 0.5 * float(np.abs(hist - prev_hist).sum()) / 3)
        d1.append(0.0 if prev_gray is None else float(np.abs(g - prev_gray).mean()))
        grays.append(g)
        d12.append(0.0 if len(grays) < 13 else float(np.abs(g - grays[-13]).mean()))
        if len(grays) > 13:
            grays.pop(0)
        luma.append(float(g.mean()))
        white.append(float((g > 235).mean()))
        black.append(float((g < 16).mean()))
        prev_hist, prev_gray = hist, g
    proc.wait()
    WORKD.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(feat_path(key), hd=np.array(hd, np.float32), d1=np.array(d1, np.float32), d12=np.array(d12, np.float32),
                        luma=np.array(luma, np.float32), white=np.array(white, np.float32), black=np.array(black, np.float32),
                        fps=fps, frames=len(hd), width=w, height=h)
    print(f"{key}: {len(hd)} frames measured ({n} in the file, {fps:.3f} fps) -> {feat_path(key)}")


def external_edges(key, fps):
    """Shot edges another pass found: the catalogue's spans on this master (set by eye on a 480p proxy, 2 decimals)."""
    if key not in B.MASTERS:
        return set()
    return external_edges_catalogue(key, fps)


def candidates(key, thr_hd=0.16, thr_d1=22.0):
    F = np.load(feat_path(key))
    hd, d1, d12, luma, white, black = (F[k] for k in ("hd", "d1", "d12", "luma", "white", "black"))
    fps, n = float(F["fps"]), int(F["frames"])
    cands = {}

    def add(f, kind, score, note=""):
        if 0 < f < n and (f not in cands or score > cands[f]["score"]):
            cands[f] = dict(f=int(f), kind=kind, score=round(float(score), 3), hd=round(float(hd[f]), 3), d1=round(float(d1[f]), 1), note=note)

    # hard cuts: a spike in the histogram distance or the pixel difference, a local maximum, well above its neighbourhood
    for f in range(1, n):
        if hd[f] >= thr_hd or d1[f] >= thr_d1:
            lo, hi = max(1, f - 15), min(n, f + 16)
            if d1[f] < d1[lo:hi].max() or hd[f] < hd[lo:hi].max() * 0.999 and d1[f] < d1[lo:hi].max() * 0.999:
                # not the local peak of either measure: a neighbour wins
                if not (d1[f] == d1[lo:hi].max() or hd[f] == hd[lo:hi].max()):
                    continue
            med = float(np.median(d1[lo:hi]))
            if d1[f] < 2.2 * max(med, 3.0) and hd[f] < 0.3:
                continue  # steady motion (a pan, a tracking shot), not a cut
            add(f, "cut", hd[f] + d1[f] / 100)
    # flashes: one or two near-white frames
    f = 1
    while f < n:
        if white[f] > 0.6 and white[f - 1] <= 0.6:
            g = f
            while g < n and white[g] > 0.6:
                g += 1
            add(f, "flash", 1.0 + (g - f) / 100, f"white {f}-{g - 1}")
            if g < n:
                add(g, "cut", 0.9, f"after the flash {f}-{g - 1}")
            f = g
        f += 1
    # fades through black: a run of near-black frames; the shot before fades out into it, the shot after fades in from it
    f = 0
    while f < n:
        if black[f] > 0.97:
            g = f
            while g < n and black[g] > 0.97:
                g += 1
            # the fade-in's first lit frame is the new shot's first frame; the fade-out's first black frame ends the old one
            if f > 0:
                add(f, "black", 0.8, f"black {f}-{g - 1}")
            if g < n:
                add(g, "cut", 0.8, f"first lit frame after black {f}-{g - 1}")
            f = g
        f += 1
    # dissolves: the picture 12 frames back is very different but no single frame jumped
    for f in range(13, n - 1):
        if d12[f] > 42 and d1[f - 12:f + 1].max() < thr_d1 * 0.8 and hd[f - 12:f + 1].max() < thr_hd:
            # one candidate per dissolve: its end
            if d12[f] >= d12[max(0, f - 12):f + 13].max():
                add(f, "dissolve?", 0.5 + d12[f] / 200, f"gradual change ending ~{f}")
    # edges another pass found, when nothing of ours sits within 3 frames
    ours = sorted(cands)
    for e in sorted(external_edges(key, fps)):
        if 0 < e < n and not any(abs(e - o) <= 3 for o in ours):
            add(e, "ext", 0.3, "catalogue edge, nothing measured here")
    out = sorted(cands.values(), key=lambda c: c["f"])
    (WORKD / f"{B.key_file(key)}_cands.json").write_text(json.dumps(dict(key=key, fps=fps, frames=n, cands=out), indent=1), encoding="utf-8")
    kinds = {}
    for c in out:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print(f"{key}: {len(out)} candidates {kinds} -> {WORKD / (B.key_file(key) + '_cands.json')}")


def strips(key, out_dir, per_sheet=12, tw=240, th=135):
    """Sheets of 6-frame strips (f-3..f+2) around every candidate, read by eye: is the cut exactly between f-1 and f?"""
    d = json.loads((WORKD / f"{B.key_file(key)}_cands.json").read_text(encoding="utf-8"))
    fps, cands = d["fps"], d["cands"]
    path = B.proxy_or_file(key)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fnt = font(14)

    def strip(c):
        f0 = max(0, c["f"] - 3)
        ims = B.grab_run(path, B.seek_time(f0, fps), 6, tw, th)
        return c, f0, ims

    with ThreadPoolExecutor(FF_WORKERS) as ex:
        rows = list(ex.map(strip, cands))
    LH = 18
    sheets = []
    for p in range(0, len(rows), per_sheet):
        chunk = rows[p:p + per_sheet]
        sheet = Image.new("RGB", (6 * tw + 5 * 2 + 10, len(chunk) * (th + LH + 4)), (20, 20, 24))
        dr = ImageDraw.Draw(sheet)
        for r, (c, f0, ims) in enumerate(chunk):
            y = r * (th + LH + 4)
            for i, im in enumerate(ims[:6]):
                x = i * (tw + 2) + (10 if i >= 3 else 0)
                sheet.paste(im, (x, y + LH))
                fnum = f0 + i
                dr.text((x + 3, y + 2), f"{fnum}", fill=(255, 255, 0) if fnum == c["f"] else (200, 200, 200), font=fnt)
            dr.rectangle([3 * (tw + 2) + 1, y + LH, 3 * (tw + 2) + 8, y + LH + th], fill=(255, 40, 40))
            dr.text((3 * (tw + 2) + 14, y + 2), f"#{c['f']}  {c['kind']}  t={B.mmss(c['f'] / fps)}  hd={c['hd']} d1={c['d1']}  {c['note']}",
                    fill=(255, 230, 0), font=fnt)
        name = out_dir / f"{B.key_file(key)}_cuts_{p // per_sheet + 1:03d}.jpg"
        sheet.save(name, quality=84)
        sheets.append(name)
    print(f"{key}: {len(rows)} strips on {len(sheets)} sheets -> {out_dir}")


def lib_keys(code):
    return [f"{code}/{p.stem}" for p in B.lib_files(code)]


def strips_lib(code, out_dir, per_sheet=12, tw=240, th=135):
    """One set of sheets for a whole clip library: every clip's candidates in order, each row headed by the clip's name and the frame
    (`<stem>#<frame>`), so a verifier reads one folder and writes one verdict file (apply_lib splits it per clip)."""
    rows = []
    for key in lib_keys(code):
        cp = WORKD / f"{B.key_file(key)}_cands.json"
        if not cp.exists():
            continue
        d = json.loads(cp.read_text(encoding="utf-8"))
        path = B.source_path(key)
        for c in d["cands"]:
            rows.append((key, d["fps"], path, c))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fnt = font(14)

    def strip(row):
        key, fps, path, c = row
        f0 = max(0, c["f"] - 3)
        return row, f0, B.grab_run(path, B.seek_time(f0, fps), 6, tw, th)

    with ThreadPoolExecutor(FF_WORKERS) as ex:
        done = list(ex.map(strip, rows))
    LH = 18
    sheets = []
    for p in range(0, len(done), per_sheet):
        chunk = done[p:p + per_sheet]
        sheet = Image.new("RGB", (6 * tw + 5 * 2 + 10, len(chunk) * (th + LH + 4)), (20, 20, 24))
        dr = ImageDraw.Draw(sheet)
        for r, ((key, fps, path, c), f0, ims) in enumerate(chunk):
            y = r * (th + LH + 4)
            for i, im in enumerate(ims[:6]):
                x = i * (tw + 2) + (10 if i >= 3 else 0)
                sheet.paste(im, (x, y + LH))
                fnum = f0 + i
                dr.text((x + 3, y + 2), f"{fnum}", fill=(255, 255, 0) if fnum == c["f"] else (200, 200, 200), font=fnt)
            dr.rectangle([3 * (tw + 2) + 1, y + LH, 3 * (tw + 2) + 8, y + LH + th], fill=(255, 40, 40))
            stem = key.split("/", 1)[1]
            dr.text((3 * (tw + 2) + 14, y + 2), f"{stem}#{c['f']}  {c['kind']}  t={B.mmss(c['f'] / fps)}  hd={c['hd']} d1={c['d1']}  {c['note']}"[:150],
                    fill=(255, 230, 0), font=fnt)
        name = out_dir / f"{code}_cuts_{p // per_sheet + 1:03d}.jpg"
        sheet.save(name, quality=84)
        sheets.append(name)
    print(f"{code}: {len(done)} strips of {len(set(r[0] for r in rows))} clips on {len(sheets)} sheets -> {out_dir}")


def apply_lib(code):
    """Split WORKD/<code>_verdicts.json ({"<stem>#<frame>": verdict}) into per-clip verdict files and apply every clip."""
    vp = WORKD / f"{code}_verdicts.json"
    ver = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}
    per = {}
    for k, v in ver.items():
        if "#" in k:
            stem, f = k.rsplit("#", 1)
            per.setdefault(stem, {})[f] = v
    n = 0
    for key in lib_keys(code):
        if not (WORKD / f"{B.key_file(key)}_cands.json").exists():
            continue
        stem = key.split("/", 1)[1]
        (WORKD / f"{B.key_file(key)}_verdicts.json").write_text(json.dumps(per.get(stem, {}), indent=1), encoding="utf-8")
        apply(key)
        n += 1
    print(f"{code}: {n} clips applied")


def longscan(key, out_dir, min_len=5.0, ratio=3.5):
    """Cuts the candidates may have missed inside long shots (two dark shots barely move the histogram): every frame whose
    pixel difference is the peak of its +-15 frames and `ratio` times their median (or a histogram jump > 0.07 that is its window's
    peak), not within 2 frames of a candidate -> strips (<key>_longscan.jpg) read like the cut strips; a real cut gets the verdict
    "cut", then apply / beats again."""
    F = np.load(feat_path(key))
    hd, d1 = F["hd"], F["d1"]
    fps = float(F["fps"])
    cands = {c["f"] for c in json.loads((WORKD / f"{B.key_file(key)}_cands.json").read_text(encoding="utf-8"))["cands"]}
    shots = json.loads((WORKD / f"{B.key_file(key)}_shots.json").read_text(encoding="utf-8"))["shots"]
    # whole takes: beat edges are no cuts
    takes, cur = [], None
    for s in shots:
        if cur and "cont_in" in s["edge_flags"]:
            cur[1] = s["f_out"]
        else:
            cur = [s["f_in"], s["f_out"]]
            takes.append(cur)
    hits = []
    for a, b in takes:
        if (b - a) / fps < min_len:
            continue
        for f in range(a + 3, b - 2):
            lo, hi = max(a, f - 15), min(b, f + 16)
            med = float(np.median(d1[lo:hi]))
            if d1[f] >= d1[lo:hi].max() and (d1[f] / max(med, 0.7) > ratio or (hd[f] > 0.07 and hd[f] >= hd[lo:hi].max())) \
                    and not any(abs(f - c) <= 2 for c in cands):
                hits.append(f)
    path = B.proxy_or_file(key)
    tw, th, LH = 240, 135, 18
    fnt = font(14)
    sheet = Image.new("RGB", (6 * tw + 20, max(1, len(hits)) * (th + LH + 4)), (20, 20, 24))
    dr = ImageDraw.Draw(sheet)
    for r, f in enumerate(hits):
        ims = B.grab_run(path, B.seek_time(f - 3, fps), 6, tw, th)
        y = r * (th + LH + 4)
        for i, im in enumerate(ims[:6]):
            x = i * (tw + 2) + (10 if i >= 3 else 0)
            sheet.paste(im, (x, y + LH))
            dr.text((x + 3, y + 2), str(f - 3 + i), fill=(255, 255, 0) if i == 3 else (200, 200, 200), font=fnt)
        dr.rectangle([3 * (tw + 2) + 1, y + LH, 3 * (tw + 2) + 8, y + LH + th], fill=(255, 40, 40))
    out = Path(out_dir) / f"{B.key_file(key)}_longscan.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=84)
    print(f"{key}: {len(hits)} spikes inside long takes -> {out}")


def beats_path(key):
    return WORKD / f"{B.key_file(key)}_beats.json"


def beats(key, min_len=12.0, target=8.0, max_piece=14.0, gap=2.5):
    """Split every long continuous take (a walk-through that runs minutes as one take) into beats, so each record covers one moment:
    its own frames, picture embedding, description and 9:16 window. A beat edge is no cut (the camera keeps rolling): the beat after it
    carries `cont_in`, the one before `cont_out`. Edges come from the catalogue's moment spans inside the take (set by eye), at least
    `gap` s from each other and from the take's cuts; a piece still longer than `max_piece` s is cut into ~`target`-s parts at the
    biggest change in the picture (12-frame difference) within 1.5 s of each even split. -> WORK/work/<key>_beats.json, then apply."""
    F = np.load(feat_path(key))
    d12 = F["d12"]
    fps = float(F["fps"])
    bp = beats_path(key)
    if bp.exists():
        bp.unlink()            # the cut-only shots first
    apply(key)
    shots = json.loads((WORKD / f"{B.key_file(key)}_shots.json").read_text(encoding="utf-8"))["shots"]
    cat_edges = sorted(external_edges_catalogue(key, fps))
    # beat edges set by eye win over the catalogue's: a verdict "beat" on a frame (a screen in the picture changing inside one take)
    vp = WORKD / f"{B.key_file(key)}_verdicts.json"
    marks = sorted(int(k) for k, v in (json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}).items()
                   if k.isdigit() and str(v).strip() == "beat")
    out = []
    g = int(round(gap * fps))
    for s in shots:
        a, e = s["f_in"], s["f_out"]
        if (e - a + 1) / fps <= min_len:
            continue
        mine = [m for m in marks if a < m <= e]
        kept = [a] + mine + [e + 1]
        for c in cat_edges:
            if a + g <= c <= e - g and all(abs(c - k) >= g for k in kept):
                kept.append(c)
        edges = sorted(kept)
        fill = []
        for p, q in zip(edges[:-1], edges[1:]):
            if (q - p) / fps > max_piece:
                k = max(2, round((q - p) / fps / target))
                for i in range(1, k):
                    m = p + round((q - p) * i / k)
                    lo, hi = max(p + g, m - int(1.5 * fps)), min(q - g, m + int(1.5 * fps))
                    if hi > lo:
                        m = lo + int(np.argmax(d12[lo:hi + 1]))
                    fill.append(m)
        out += edges[1:-1] + fill
    out = sorted(set(out))
    bp.write_text(json.dumps(dict(key=key, note="beat edges inside long continuous takes (no cut): brain_cuts.py beats", frames=out),
                             indent=1), encoding="utf-8")
    print(f"{key}: {len(out)} beat edges -> {bp}")
    apply(key)


def external_edges_catalogue(key, fps):
    """The catalogue's moment edges on a master (frames)."""
    edges = set()
    for T in B.catalogue().get("themes", {}).values():
        for e in T.get("entries", []):
            if e.get("src") == key and "start_s" in e:
                edges.add(int(round(e["start_s"] * fps)))
                edges.add(int(round(e["end_s"] * fps)))
    return edges


def apply(key):
    """Verdicts -> shots. A shot runs from its first frame to the frame before the next shot's first; its clean span skips a fade-in
    (frames until the luma reaches 80% of the shot's median), a flash at the start, and a fade-out at the end. Beat edges
    (<key>_beats.json, `beats`) split a long take with no cut: those edges are not trimmed and carry cont_in / cont_out."""
    d = json.loads((WORKD / f"{B.key_file(key)}_cands.json").read_text(encoding="utf-8"))
    fps, n = d["fps"], d["frames"]
    vp = WORKD / f"{B.key_file(key)}_verdicts.json"
    ver = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}
    F = np.load(feat_path(key))
    luma, white, black = F["luma"], F["white"], F["black"]
    bp = beats_path(key)
    beat_edges = set(json.loads(bp.read_text(encoding="utf-8"))["frames"]) if bp.exists() else set()
    starts, dissolves = {0}, []
    for c in d["cands"]:
        v = str(ver.get(str(c["f"]), "ok")).strip()
        if c["kind"] == "flash":
            if v != "no":
                dissolves.append((c["f"], c["f"]))   # a flash frame belongs to nobody: both neighbours' clean spans stop at it
            continue
        if c["kind"] == "black":
            continue  # the fade's first black frame: handled by the clean span of the shot before it
        if v == "no":
            continue
        if v.startswith("dissolve"):
            _, a, b = v.split()
            dissolves.append((int(a), int(b)))
            starts.add(int(b) + 1)
            continue
        if v == "ok":
            starts.add(c["f"])
        elif v in ("+1", "+2", "-1", "-2", "+3", "-3"):
            starts.add(c["f"] + int(v))
        elif v.isdigit():
            starts.add(int(v))
    # a cut the strips did not propose (the verifier saw it in a row): a verdict "cut" on a frame that is no candidate
    cand_frames = {c["f"] for c in d["cands"]}
    for k, v in ver.items():
        if k.isdigit() and int(k) not in cand_frames and str(v).strip() in ("cut", "ok"):
            starts.add(int(k))
    beat_edges -= starts                     # a beat edge that is a cut anyway stays a cut
    starts |= beat_edges
    starts = sorted(s for s in starts if 0 <= s < n)
    shots = []
    for i, s in enumerate(starts):
        e = (starts[i + 1] - 1) if i + 1 < len(starts) else n - 1
        if e < s:
            continue
        ci, co = s, e
        cont_in, cont_out = s in beat_edges, (e + 1) in beat_edges
        # a fade-in: the first frames are dark and much darker than the picture half a second later (a shot that is simply dark, or
        # one whose content brightens, keeps its first frame); a flash or black frame at the edge is skipped too; a beat edge is
        # the same take rolling on, never trimmed
        def dim(f, ref):
            return luma[f] < 60 and luma[f] < 0.75 * luma[ref]
        while not cont_in and ci < e and (dim(ci, min(e, ci + 15)) or white[ci] > 0.6 or black[ci] > 0.97):
            ci += 1
        while not cont_out and co > ci and (dim(co, max(ci, co - 15)) or white[co] > 0.6 or black[co] > 0.97):
            co -= 1
        med = float(np.median(luma[s:e + 1])) if e >= s else 0.0
        for a, b in dissolves:
            if s <= a <= e:   # the dissolve or flash lies inside this shot's frames
                if a - s < e - b:
                    ci = max(ci, b + 1)
                else:
                    co = min(co, a - 1)
        flags = []
        if ci > s:
            flags.append("flash_in" if white[s] > 0.6 else "fade_in")
        if co < e:
            flags.append("fade_out")
        if cont_in:
            flags.append("cont_in")
        if cont_out:
            flags.append("cont_out")
        if (e - s + 1) / fps < 1.0:
            flags.append("short")
        if med < 40:
            flags.append("dark")
        shots.append(dict(f_in=int(s), f_out=int(e), c_in=int(ci), c_out=int(max(ci, co)), edge_flags=flags))
    outp = WORKD / f"{B.key_file(key)}_shots.json"
    outp.write_text(json.dumps(dict(key=key, fps=fps, frames=n, shots=shots), indent=1), encoding="utf-8")
    print(f"{key}: {len(shots)} shots -> {outp}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["proxy", "features", "candidates", "strips", "apply", "beats", "longscan", "strips_lib", "apply_lib"])
    ap.add_argument("key")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--thr-hd", type=float, default=0.16)
    ap.add_argument("--thr-d1", type=float, default=22.0)
    a = ap.parse_args()
    if a.mode == "proxy":
        proxy(a.key)
    elif a.mode == "features":
        features(a.key)
    elif a.mode == "candidates":
        candidates(a.key, a.thr_hd, a.thr_d1)
    elif a.mode == "strips":
        strips(a.key, a.out or (B.WORK / "strips"))
    elif a.mode == "strips_lib":
        strips_lib(a.key, a.out or (B.WORK / "strips"))
    elif a.mode == "apply_lib":
        apply_lib(a.key)
    elif a.mode == "beats":
        beats(a.key)
    elif a.mode == "longscan":
        longscan(a.key, a.out or (B.WORK / "strips"))
    else:
        apply(a.key)
