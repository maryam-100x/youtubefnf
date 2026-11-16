"""The render scan: the REAL rendered picture, every frame, checked for the faults that only happen at render time, before anyone watches it.

The gate (gate.py) probes the composition with no video pixels drawn, so a fault born in the render itself is invisible to it. One such
fault: a component that releases its delayRender before a card's blurred video ground has mounted, so every render tab's first frame of
that card loses its ground (a few dark frames, one per render tab: up to the render's concurrency). This scan decodes the render's own
frames (small and grey, streamed, two ffmpeg at a time) and reads them against the gate's probe (what should be on screen at each frame):

  BLACK_DIP    1-6 frames much darker than the stretches on both sides that come back: a lost or blank frame. Designed darkness is
               told apart by the probe: the design fades there (its lit weight falls gradually), or shows nothing for longer than a dip.
               A probe that is ALSO empty for those 1-6 frames, with lit shots on both sides, is no alibi: the probe renders the same
               composition and loses the same frames (a long video's probe can hold a couple of hundred such 1-6 frame drop-outs).
  FLASH_FRAME  1-8 frames of one picture with a jump in and a jump out (corr or grey, 3x the sides' own motion): a stray picture in a
               shot, or a short picture squeezed into a cut (A | X | B: a "flash frame"). Each jump is traced: the design's (the probe
               changes there), the source's (the clip's own file jumps there) or nothing's (render time). Designed + designed and source +
               source pass (the composition's or the footage's own); a designed cut beside a source jump is the source's own cut at the
               play's edge (a few frames of the source's previous shot at a clip's head); an unexplained jump is a render fault.
  FROZEN       the probe says a clip plays (its source second moves on to new source frames) while its part of the rendered frame stands
               still, and the source itself changes there (laid where the probe puts the clip, scaled by how the render follows the
               source around it): a freeze born in the render.
  FRAMES       a piece (chunk) holding more or fewer frames than its share of the film, or decoding to another count than its packets.

  PIPE tools/pipeline/qa_render_scan.py <video> --version 3 [--parts render/parts_v3]
        [--probe pipeline/gate/probe.jsonl] [--range a-b] [--out DIR] [--file x.mkv[:first_frame] ...] [--no-probe] [--total N]
  scan(pieces, probe_path=None, out_dir=..., fps=60, pub=None, frange=None, expected=None, strips=True) -> list of flags
        pieces = [(path, first_film_frame), ...]; flags in the gate's format {"check", "key", "at", "to", "what", "strip"}

Writes <out>/render_scan.md and render_scan.json and one strip PNG per flag (<CHECK>_<frame>.png: frames f-3..f+3 side by side at
320x180, the flagged frames outlined red), exits 1 on any flag. A run keeps the frame measures in <out>/render_scan_features.npz and the
probe's summary in <out>/probe_summary.npz, so a second run on the same files reads them back instead of decoding again.

How it measures (Y plane, 16 = black, 235 = white; the frames scaled to 160x90 by area, so H.264 noise averages out):
  lum = mean Y; corr = how alike two frames are (zero-mean correlation of 40x22 thumbs: 1 the same picture, ~0 unrelated; motion keeps it
  high, a cut drops it; a flat frame against anything not flat counts 0); d (grey) = mean |Y difference| at 160x90; an 8x6 grid of the
  same per cell for the frozen test. The checks only decode short windows again (strips, frozen and flash confirmations).

PROOF (a long render: 16 pieces of 2560x1440 60-fps H.264, ~188,000 frames, with its probe):
  run time: decoding 11-16 min (two ffmpeg at -threads 4: ~290 frames/s for the pair on a quiet computer, slower beside other jobs), the
  probe's summary 35-80 s, the checks 1.5-2 min (the frozen confirmations), the strips seconds. 4 flags, all real: two clips ending on 2
  frames after their source's own jump (minor), a ground opening on 3 frames of its source's previous shot, and one black frame where the
  probe is empty too (an empty frame in the composition, in the final export as well).
  false flags found and fixed while tuning (each measured on its strip): 4 FLASH on 24-fps footage (3-2-3 holds: its real changes are
  the motion, not the repeats), 8 FROZEN on blurred grounds behind cards and a blurred backdrop beside a 4:3 picture (now: the top-most
  clip, and the source laid where the clip sits, calibrated by the render around it), 2 FROZEN on whole-pixel placement of a slow push
  (now sub-pixel), 1 FROZEN on calibration by noise (now 1.0+ of source change), 3 FLASH on a menu animating in, the source's own
  dissolve, and a stamp landing with a full-frame overlay the probe does not list (now: source + source passes; item changes count as
  design).
  recall: the delayRender race's dark frames (3 at concurrency 3: Y 26 against 115 and 43; 1 at concurrency 1) flagged with and without
  the probe, the fixed renders clean; 7 frames of a clip's previous take at its head flagged without a probe; a sun's glare for 3 frames
  at the head of a whip-pan not caught (its jump is only 1.8x the whip's own motion). 17 review samples (12,381 frames) scanned without a
  probe: no flag.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "common"))
from paths import FFMPEG, FFPROBE  # noqa: E402

FPS = 60
GW, GH = 160, 90            # the scan's picture size
TW, TH = 40, 22             # the correlation thumbs (160x88 pooled 4x4)
CGX, CGY = 8, 6             # the frozen test's cells (20x15 px of the 160x90 frame each)
LAGS = 4                    # frame distances measured: 1..4 (a 1-3 frame run: the frame before it against the frame after)
BLOCK = 600                 # frames read from ffmpeg at a time
THREADS = 4                 # ffmpeg threads per process (a shared computer)
WORKERS = 2                 # ffmpeg processes at a time
FLAT_SD = 1.5               # a thumb with less spread than this (Y levels) is flat: one colour, its corr defined by its mean alone
STRIP_W, STRIP_H = 320, 180


def say(msg):
    print(msg, flush=True)


def mmss(f, fps=FPS):
    t = f / fps
    return f"{int(t // 60)}:{t % 60:05.2f}"


# ================================================================================================================== decoding (ffmpeg)
def _ffmpeg(path, vf, pix, start=None, count=None, fps=FPS, threads=THREADS):
    """ffmpeg reading `path` from frame `start` (local to the file) for `count` frames, through `vf`, raw `pix` frames on stdout.
    The seek lands half a frame early: an MKV's millisecond timestamps put frame n anywhere in n/60 +- 0.5 ms, and ffmpeg's accurate
    seek then starts at the first frame at or after that time, which is frame n."""
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-threads", str(threads)]
    if start:
        cmd += ["-ss", f"{(start - 0.5) / fps:.6f}"]
    cmd += ["-i", str(path), "-an", "-sn", "-dn"]
    if count:
        cmd += ["-frames:v", str(count)]
    cmd += ["-vf", vf, "-pix_fmt", pix, "-f", "rawvideo", "-"]
    err = tempfile.TemporaryFile()
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, bufsize=1 << 20), err


def gray_frames(path, start=None, count=None, w=GW, h=GH, fps=FPS):
    """frames of a file as (n, h, w) uint8 luma, read whole (a short window)"""
    p, err = _ffmpeg(path, f"extractplanes=y,scale={w}:{h}:flags=area", "gray", start, count, fps)
    raw = p.stdout.read()
    p.wait()
    n = len(raw) // (w * h)
    return np.frombuffer(raw[: n * w * h], np.uint8).reshape(n, h, w)


def rgb_frames(path, start=None, count=None, w=STRIP_W, h=STRIP_H, fps=FPS):
    p, err = _ffmpeg(path, f"scale={w}:{h}:flags=area", "rgb24", start, count, fps)
    raw = p.stdout.read()
    p.wait()
    n = len(raw) // (w * h * 3)
    return np.frombuffer(raw[: n * w * h * 3], np.uint8).reshape(n, h, w, 3)


def packets(path):
    """the video packets of a file (ffprobe -count_packets: a demux, no decode; the renders hold one packet per frame)"""
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True).stdout.strip()
    return int(out) if out.isdigit() else None


SRC_INFO = {}


def src_fps(path):
    k = str(path)
    if k not in SRC_INFO:
        out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate,r_frame_rate",
                              "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True).stdout.split()
        fps = 30.0
        for x in out:
            a, _, b = x.partition("/")
            try:
                v = float(a) / float(b or 1)
            except (ValueError, ZeroDivisionError):
                continue
            if 1 <= v <= 240:
                fps = v
                break
        SRC_INFO[k] = fps
    return SRC_INFO[k]


def src_gray(path, t0, t1):
    """a source file's frames between t0 and t1 seconds at 160x90 luma, and the source frame index of each"""
    fps = src_fps(path)
    i0 = max(0, math.ceil(t0 * fps - 1e-6))
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-threads", str(THREADS), "-ss", f"{max(0.0, (i0 - 0.5) / fps):.6f}", "-i", str(path), "-an",
           "-frames:v", str(max(1, math.ceil((t1 - t0) * fps) + 1)), "-vf", f"extractplanes=y,scale={GW}:{GH}:flags=area", "-pix_fmt", "gray",
           "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (GW * GH)
    return np.frombuffer(raw[: n * GW * GH], np.uint8).reshape(n, GH, GW), np.arange(i0, i0 + n)


# ============================================================================================================ the frame measures
def thumbs(fr):
    """(n, 90, 160) -> (n, 880) 40x22 thumbs (4x4 means of the top 88 rows)"""
    n = len(fr)
    return fr[:, : TH * 4, :].reshape(n, TH, 4, TW, 4).mean(axis=(2, 4)).reshape(n, TH * TW)


def corr_pairs(ta, tb):
    """corr of thumbs row by row (see the module docstring for flat thumbs)"""
    ua, ub = ta - ta.mean(1, keepdims=True), tb - tb.mean(1, keepdims=True)
    na, nb = np.sqrt((ua * ua).sum(1)), np.sqrt((ub * ub).sum(1))
    c = (ua * ub).sum(1) / np.maximum(na * nb, 1e-6)
    fa, fb = na / math.sqrt(TW * TH) < FLAT_SD, nb / math.sqrt(TW * TH) < FLAT_SD
    both = fa & fb
    c = np.where(fa ^ fb, 0.0, c)
    c = np.where(both, (np.abs(ta.mean(1) - tb.mean(1)) < 6).astype(np.float64), c)
    return c


FEATS = ("lum", "hi", "sd", "c1", "c2", "c3", "c4", "d1", "d2", "d3", "d4")


def measure(prev, block):
    """the measures of `block` (n frames), `prev` the up to LAGS frames before it (for the distances); returns a dict of (n,) arrays and
    the (n, 48) cell differences"""
    n = len(block)
    allf = np.concatenate([prev, block]).astype(np.float32) if len(prev) else block.astype(np.float32)
    m = len(prev)
    out = {k: np.full(n, np.nan, np.float32) for k in FEATS}
    flat = block.reshape(n, -1)
    out["lum"] = flat.mean(1).astype(np.float32)
    out["hi"] = np.partition(flat, int(0.98 * flat.shape[1]), axis=1)[:, int(0.98 * flat.shape[1])].astype(np.float32)
    th = thumbs(allf).astype(np.float64)
    u = th - th.mean(1, keepdims=True)
    out["sd"] = (np.sqrt((u * u).sum(1)) / math.sqrt(TW * TH))[m:].astype(np.float32)
    cells = np.full((n, CGX * CGY), np.nan, np.float16)
    for k in range(1, LAGS + 1):
        idx = np.arange(m, m + n)
        ok = idx - k >= 0
        if not ok.any():
            continue
        i1, i0 = idx[ok], idx[ok] - k
        out[f"c{k}"][ok] = corr_pairs(th[i1], th[i0]).astype(np.float32)
        dif = np.abs(allf[i1] - allf[i0])
        out[f"d{k}"][ok] = dif.mean(axis=(1, 2))
        if k == 1:
            cells[ok] = dif.reshape(-1, CGY, GH // CGY, CGX, GW // CGX).mean(axis=(2, 4)).reshape(-1, CGX * CGY).astype(np.float16)
    return out, cells


def scan_piece(path, f0, start=None, count=None, label=""):
    """stream one piece through ffmpeg and measure every frame. Returns (first film frame measured, measures, cells, head frames, tail
    frames, decoded count): the head and tail (LAGS frames each) let the frames at a join be measured against the piece before."""
    t0 = time.time()
    p, err = _ffmpeg(path, f"extractplanes=y,scale={GW}:{GH}:flags=area", "gray", start, count)
    size = GW * GH
    parts, cparts, prev, head, n_all = [], [], np.zeros((0, GH, GW), np.uint8), None, 0
    try:
        while True:
            raw = p.stdout.read(size * BLOCK)
            if not raw:
                break
            n = len(raw) // size
            block = np.frombuffer(raw[: n * size], np.uint8).reshape(n, GH, GW)
            if head is None:
                head = block[:LAGS].copy()
            m, c = measure(prev, block)
            parts.append(m)
            cparts.append(c)
            prev = np.concatenate([prev, block])[-LAGS:].copy()
            n_all += n
    finally:
        if p.poll() is None:
            p.kill()
        p.wait()
    err.seek(0)
    msg = err.read().decode("utf-8", "replace").strip()
    feats = {k: np.concatenate([x[k] for x in parts]) if parts else np.zeros(0, np.float32) for k in FEATS}
    cells = np.concatenate(cparts) if cparts else np.zeros((0, CGX * CGY), np.float16)
    say(f"  {label or Path(path).name}: {n_all} frames in {time.time() - t0:.0f} s{' (ffmpeg: ' + msg[:200] + ')' if msg else ''}")
    return (f0 + (start or 0), feats, cells, head if head is not None else np.zeros((0, GH, GW), np.uint8), prev, n_all)


def measure_pieces(pieces, frange=None, workers=WORKERS):
    """every piece measured (two ffmpeg at a time), laid on film frames. Returns (F0, F1, feats over F0..F1-1, cells, decoded counts)"""
    jobs = []
    for i, (path, f0, n) in enumerate(pieces):
        if frange:
            a, b = max(frange[0] - 12, f0), min(frange[1] + 12, f0 + n - 1)
            if a > b:
                continue
            jobs.append((i, path, f0, a - f0, b - a + 1))
        else:
            jobs.append((i, path, f0, None, None))
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda j: (j[0], scan_piece(j[1], j[2], j[3], j[4], f"{Path(j[1]).name}")), jobs))
    F0 = min(r[1][0] for r in res)
    F1 = max(r[1][0] + r[1][5] for r in res)
    feats = {k: np.full(F1 - F0, np.nan, np.float32) for k in FEATS}
    cells = np.full((F1 - F0, CGX * CGY), np.nan, np.float16)
    counts = {}
    for i, (a, fe, ce, head, tail, n) in res:
        for k in FEATS:
            feats[k][a - F0: a - F0 + n] = fe[k]
        cells[a - F0: a - F0 + n] = ce
        counts[i] = n
    # the joins: a piece's first frames against the piece before it (when it ends right there)
    for i, (a, fe, ce, head, tail, n) in res:
        before = next((r for r in res if r[1][0] + r[1][5] == a), None)
        if before is None or len(head) == 0:
            continue
        m, c = measure(before[1][4], head)
        for k in FEATS:
            feats[k][a - F0: a - F0 + len(head)] = m[k]
        cells[a - F0: a - F0 + len(head)] = c
    return F0, F1, feats, cells, counts


# ===================================================================================================================== the probe
GRID_X, GRID_Y = 32, 18     # the probe's coverage grid (60 px cells of 1920x1080)
LIT = 0.3                   # a picture counts as lit from opacity x brightness 0.3 (gate.py EMPTY_LIT 0.28: a dimmed art ground sits at 0.30)


def _vis(it, W, H):
    x, y, w, h = it["x"], it["y"], it["w"], it["h"]
    x0, y0 = max(x, it.get("cx0", 0), 0), max(y, it.get("cy0", 0), 0)
    x1, y1 = min(x + w, it.get("cx1", W), W), min(y + h, it.get("cy1", H), H)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def probe_summary(path, cache=None):
    """One pass over the probe (a layout line per frame, sorted; clip lines anywhere), kept per frame:
      lit   the share of the frame a picture (img or clip, credits aside) covers at opacity x brightness >= LIT
      wl    the frame's mean lit weight: each 60-px cell takes the opacity x brightness of the picture on top there (0 = nothing lit)
      dz    the share of cells whose picture on top (or its weight, by > 0.2) changed since the frame before: 1 at a hard cut, 0 in a shot
      dd    the share of the frame covered by items (any kind, credits aside, 0.5%+ of the frame) that appear, go or fade by more than 0.1
            since the frame before: a stamp slamming on, a card arriving (a stamp can land with a dark full-frame overlay the probe
            doesn't list; its texts are the design's trace)
      clip  the main clip (the clip pane at opacity >= 0.5 with the most cells showing it, nothing on top): its file's id, cover share,
            opacity x brightness, the source second shown, its picture's box, and `free`: the 8x6 cells fully inside its pane with
            nothing drawn over them (bit i = cell i, row by row)
    The file runs to hundreds of MB on a long video; the summary is a few MB, kept in `cache` keyed by the probe's size and time."""
    path = Path(path)
    st = path.stat()
    key = f"{path.resolve()}|{st.st_size}|{int(st.st_mtime)}|v4"
    if cache and Path(cache).exists():
        with np.load(cache, allow_pickle=False) as z:
            if str(z["key"]) == key:
                d = {k: z[k] for k in z.files if k not in ("key", "names")}
                d["names"] = [str(x) for x in z["names"]]
                return d
    t0 = time.time()
    names, ids = [], {}

    def nid(s):
        if s not in ids:
            ids[s] = len(names)
            names.append(s)
        return ids[s]

    clip_abs, clip_src, clip_s = [], [], []
    rows = []
    prev_id = prev_w = None
    prev_items = {}
    W, H = 1920, 1080
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            kind, _, body = line.partition("|")
            if kind == "clip":
                try:
                    o = json.loads(body)
                except ValueError:
                    continue
                clip_abs.append(o["abs"])
                clip_src.append(nid(o["src"]))
                clip_s.append(o.get("s", 0.0))
                continue
            if kind != "layout":
                continue
            try:
                o = json.loads(body)
            except ValueError:
                continue
            W, H = o.get("W", W), o.get("H", H)
            cw, ch = W / GRID_X, H / GRID_Y
            gid = np.full((GRID_Y, GRID_X), -1, np.int32)
            gw = np.zeros((GRID_Y, GRID_X), np.float32)
            items = o["items"]
            for i, it in enumerate(items):
                k = it["k"]
                r = _vis(it, W, H)
                if not r:
                    continue
                a = (r[2] - r[0]) * (r[3] - r[1]) / (W * H)
                ob = it["op"] * it.get("br", 1.0)
                if k in ("img", "clip") and it.get("g") != "credit" and ob >= 0.05:
                    gx0, gy0 = int(round(r[0] / cw)), int(round(r[1] / ch))
                    gx1, gy1 = int(round(r[2] / cw)), int(round(r[3] / ch))
                    if gx1 > gx0 and gy1 > gy0:
                        gid[gy0:gy1, gx0:gx1] = nid(f"{k}:{it['t']}")
                        gw[gy0:gy1, gx0:gx1] = ob
                elif k == "box" and not it.get("e") and it["op"] >= 0.5 and a >= 0.02:
                    # a filled card over the pictures: it hides them where it sits (its own look is unknown: not lit, not dark)
                    gx0, gy0 = int(round(r[0] / cw)), int(round(r[1] / ch))
                    gx1, gy1 = int(round(r[2] / cw)), int(round(r[3] / ch))
                    if gx1 > gx0 and gy1 > gy0:
                        gid[gy0:gy1, gx0:gx1] = nid(f"box:{it.get('c')}")
                        gw[gy0:gy1, gx0:gx1] = np.maximum(gw[gy0:gy1, gx0:gx1], 0.5)
            lit = float((gw >= LIT).mean())
            wl = float(gw.mean())
            if prev_id is None:
                dz = 0.0
            else:
                dz = float(((gid != prev_id) | (np.abs(gw - prev_w) > 0.2)).mean())
            prev_id, prev_w = gid, gw
            cur, seen = {}, {}
            for it in items:
                if it.get("g") == "credit":
                    continue
                r = _vis(it, W, H)
                if not r:
                    continue
                a = (r[2] - r[0]) * (r[3] - r[1]) / (W * H)
                if a < 0.005:
                    continue
                k0 = (it["k"], str(it["t"]) if it["k"] in ("img", "clip", "text") else str(it.get("c")))
                seen[k0] = seen.get(k0, 0) + 1
                cur[k0 + (seen[k0],)] = (a, it["op"] * it.get("br", 1.0))
            dd = 0.0
            for ik in set(cur) | set(prev_items):
                if ik in cur and ik in prev_items:
                    dd += max(cur[ik][0], prev_items[ik][0]) * max(0.0, abs(cur[ik][1] - prev_items[ik][1]) - 0.1)
                else:
                    dd += (cur.get(ik) or prev_items.get(ik))[0]
            dd = min(1.0, dd) if prev_id is not None else 0.0
            prev_items = cur
            # the main clip: the clip pane (opacity >= 0.5) with the most of the frame's cells showing it with nothing on top; a
            # sharp 4:3 picture over its own blurred, enlarged copy is the picture, not the copy behind it
            best = None
            ex, ey = W / CGX, H / CGY
            for i, it in enumerate(items):
                if it["k"] != "clip" or it["op"] < 0.5:
                    continue
                r = _vis(it, W, H)
                if not r:
                    continue
                over = [_vis(q, W, H) for q in items[i + 1:] if q["op"] >= 0.3 and q.get("pa", -1) != i]
                over = [q for q in over if q]
                free = 0
                for cy in range(CGY):
                    for cx in range(CGX):
                        x0, y0, x1, y1 = cx * ex, cy * ey, (cx + 1) * ex, (cy + 1) * ey
                        if not (r[0] <= x0 + 1 and r[1] <= y0 + 1 and r[2] >= x1 - 1 and r[3] >= y1 - 1):
                            continue
                        hit = sum(max(0, min(x1, q[2]) - max(x0, q[0])) * max(0, min(y1, q[3]) - max(y0, q[1])) for q in over)
                        if hit <= 0.05 * ex * ey:
                            free |= 1 << (cy * CGX + cx)
                a = (r[2] - r[0]) * (r[3] - r[1]) / (W * H)
                rank = (bin(free).count("1"), a)
                if best is None or rank > best[0]:
                    best = (rank, it, a, free)
            m_id, m_cov, m_ob, free, box = -1, 0.0, 0.0, 0, (0.0, 0.0, 0.0, 0.0)
            if best is not None:
                _, it, m_cov, free = best
                m_id, m_ob = nid(it["t"]), it["op"] * it.get("br", 1.0)
                box = (it["x"], it["y"], it["w"], it["h"])
            rows.append((o["frame"], lit, wl, dz, dd, m_id, m_cov, m_ob, free, box))
    n = max(r[0] for r in rows) + 1 if rows else 0
    d = {"lit": np.full(n, np.nan, np.float32), "wl": np.full(n, np.nan, np.float32), "dz": np.full(n, np.nan, np.float32),
         "dd": np.zeros(n, np.float32),
         "clip": np.full(n, -1, np.int32), "cover": np.zeros(n, np.float32), "cob": np.zeros(n, np.float32), "free": np.zeros(n, np.int64),
         "s": np.full(n, np.nan, np.float32), "box": np.zeros((n, 4), np.float32)}
    for f, lit, wl, dz, dd, m_id, m_cov, m_ob, free, box in rows:
        d["lit"][f], d["wl"][f], d["dz"][f], d["dd"][f] = lit, wl, dz, dd
        d["clip"][f], d["cover"][f], d["cob"][f], d["free"][f], d["box"][f] = m_id, m_cov, m_ob, free, box
    sec = {}
    for f, s_id, s in zip(clip_abs, clip_src, clip_s):
        sec.setdefault((f, s_id), s)
    for f in np.nonzero(d["clip"] >= 0)[0]:
        s = sec.get((int(f), int(d["clip"][f])))
        if s is not None:
            d["s"][f] = s
    d["names"] = names
    say(f"  probe: {n} frames, {len(clip_abs)} clip lines, {len(names)} names in {time.time() - t0:.0f} s")
    if cache:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, key=np.array(key), names=np.array(names), **{k: v for k, v in d.items() if k != "names"})
    return d


# ====================================================================================================================== the checks
def _med(a):
    a = a[~np.isnan(a)]
    return float(np.median(a)) if len(a) else float("nan")


def _play_edges(pr, f):
    """the first and last frame of the main clip's play around frame f (same file on consecutive frames)"""
    c = pr["clip"]
    i = c[f]
    a = f
    while a - 1 >= 0 and c[a - 1] == i:
        a -= 1
    b = f
    while b + 1 < len(c) and c[b + 1] == i:
        b += 1
    return a, b


def _src_path(pub, pr, f):
    if pr is None or f >= len(pr["clip"]) or pr["clip"][f] < 0 or pub is None:
        return None
    p = Path(pub) / pr["names"][pr["clip"][f]]
    return p if p.exists() else None


# ---- BLACK_DIP
DIP_RATIO = 0.7      # the run's brightest frame at most 0.7x the darker side's stretch ...
DIP_LEVELS = 10      # ... and at least 10 Y levels under it (16 = black)
DIP_MAX = 6          # 1-6 frames (a render tab's first frame lost: one per tab, concurrency up to 6)
SIDE = 6             # the stretches either side: medians of 6 frames
DESIGN_DIM = 0.8     # the probe's lit weight over the run under 0.8x the sides': the design dims there ...
FADE_STEP = 0.35     # ... and does it gradually (no frame-to-frame step of the lit weight over 0.35): a fade, a dip to black
NOTHING_LIT = 0.15   # under 15% of the frame lit in the probe: nothing should show there, when it lasts longer than a dip (7+ frames).
                     # A probe that shows nothing for only 1-6 frames between two lit shots, with hard edges, is no proof of design: the
                     # probe renders the same composition and loses the same frames to a mount race (a long video's probe can hold a
                     # couple of hundred such drop-outs)


def check_black(F0, fe, pr=None, pub=None, fps=FPS):
    """BLACK_DIP: a run of 1-6 frames whose brightest frame is at most DIP_RATIO of the darker of the 6-frame stretches on either side and
    DIP_LEVELS under it, the picture coming back after. A delayRender race at concurrency 3: a shot at Y 114, three frames at 26
    (a card with no blurred ground), then 43 (with the ground): 26 <= 0.7 x 43 and 17 levels under it.
    With a probe a dip is the design's when the probe shows nothing lit for longer than a dip (7+ frames) or its lit weight over the run
    falls under DESIGN_DIM x the sides' gradually (no step over FADE_STEP: a fade). A probe empty for just those 1-6 frames between lit
    shots is flagged as the composition's own empty frame. A dip on a clip whose source frames are themselves dark there is the
    footage's (the footage's own cut to black); kept only within 0.3 s of the play's edge, where it is the source's edge showing (gate
    B2's class). On a long render (~188,000 frames) the step-down-and-back test found 1 run; the probe's short drop-outs are bright in
    the render once the race is fixed, so they never reach this test."""
    lum = fe["lum"]
    n = len(lum)
    flags = []
    f = 1
    while f < n - 1:
        if np.isnan(lum[f]) or np.isnan(lum[f - 1]):
            f += 1
            continue
        # a step down into the run
        if not (lum[f] <= DIP_RATIO * lum[f - 1] and lum[f - 1] - lum[f] >= DIP_LEVELS):
            f += 1
            continue
        found = None
        for b in range(f, min(f + DIP_MAX, n - 1)):
            top = float(np.nanmax(lum[f: b + 1]))
            if lum[b + 1] >= top / DIP_RATIO and lum[b + 1] - top >= DIP_LEVELS:
                before = _med(lum[max(0, f - SIDE): f])
                after = _med(lum[b + 1: b + 1 + SIDE])
                side = min(before, after)
                if not np.isnan(side) and top <= DIP_RATIO * side and side - top >= DIP_LEVELS:
                    found = (b, top, before, after)
                break_ok = lum[b + 1] >= top / DIP_RATIO
                if break_ok:
                    break
        if not found:
            f += 1
            continue
        b, top, before, after = found
        a_film, b_film = F0 + f, F0 + b
        why, kind = None, "render"
        if pr is not None and b_film < len(pr["lit"]):
            run = slice(a_film, b_film + 1)
            lit = float(np.nanmax(pr["lit"][run]))
            wl = float(np.nanmin(pr["wl"][run]))
            wside = min(_med(pr["wl"][max(0, a_film - SIDE): a_film]), _med(pr["wl"][b_film + 1: b_film + 1 + SIDE]))
            ws = pr["wl"][max(0, a_film - SIDE): b_film + 1 + SIDE]
            gradual = len(ws) > 1 and float(np.nanmax(np.abs(np.diff(ws)))) <= FADE_STEP
            dark = pr["lit"] < NOTHING_LIT
            da, db = a_film, b_film
            while da - 1 >= 0 and dark[da - 1]:
                da -= 1
            while db + 1 < len(dark) and dark[db + 1]:
                db += 1
            if lit < NOTHING_LIT and db - da + 1 > DIP_MAX:
                why = f"designed: nothing lit in the probe for {db - da + 1} frames"
            elif not np.isnan(wside) and wl < DESIGN_DIM * wside and gradual:
                why = f"designed: the probe fades there (lit weight {wl:.2f} against {wside:.2f})"
            elif lit < NOTHING_LIT:
                kind = "probe"
            else:
                src = _src_path(pub, pr, a_film)
                if src is not None and pr["cover"][a_film] >= 0.5 and not np.isnan(pr["s"][a_film]):
                    s0 = float(pr["s"][a_film])
                    s_after = float(pr["s"][min(b_film + 3, len(pr["s"]) - 1)]) if pr["clip"][min(b_film + 3, len(pr["s"]) - 1)] == pr["clip"][a_film] else s0
                    s_before = float(pr["s"][max(0, a_film - 3)]) if pr["clip"][max(0, a_film - 3)] == pr["clip"][a_film] else s0
                    sf, si = src_gray(src, max(0.0, min(s_before, s0) - 0.05), max(s_after, s0) + 0.1)
                    if len(sf):
                        sl = sf.reshape(len(sf), -1).mean(1)
                        sfps = src_fps(src)
                        j = int(np.clip(math.floor(s0 * sfps + 1e-6) - si[0], 0, len(sl) - 1))
                        if sl[j] <= DIP_RATIO * max(sl.max(), 1) and sl.max() - sl[j] >= DIP_LEVELS:
                            pa, pb = _play_edges(pr, a_film)
                            edge = min(a_film - pa, pb - b_film) <= 0.3 * fps
                            if not edge:
                                why = f"the footage's own: {src.name} is dark at {s0:.2f} s itself"
                            else:
                                kind = "source"
        if why:
            f = b + 1
            continue
        k = b - f + 1
        where = ""
        if pr is not None and a_film < len(pr["lit"]):
            where = f"; the probe shows {pr['lit'][a_film]:.0%} of the frame lit" + (f", {pr['names'][pr['clip'][a_film]].split('/')[-1]} at {pr['s'][a_film]:.2f} s" if pr["clip"][a_film] >= 0 else "")
        cause = ("the source's own dark frame(s) at the play's edge" if kind == "source"
                 else "the probe shows nothing there either, with lit shots on both sides: an empty frame in the composition (a gap "
                      "between two shots, or a mount race), not a designed cut" if kind == "probe"
                 else "a lost or blank frame at render time" if pr is not None else "a lost or blank frame (no probe: designed or not unknown)")
        flags.append({"check": "BLACK_DIP", "key": str(a_film), "at": a_film, "to": b_film,
                      "what": f"{mmss(a_film, fps)}: {k} dark frame(s) (Y {top:.0f} against {before:.0f} before and {after:.0f} after){where}: {cause}"})
        f = b + 1
    return flags


# ---- FLASH_FRAME
FLASH_MAX = 8        # a stray of 1-8 frames (0.13 s): no shot is that short by design (~25 cuts a minute); a stray take of 7 frames is seen
J_U = 0.25           # a jump: the picture unlike the one before (1 - corr >= 0.25) ...
J_D = 8.0            # ... or its grey jumping (mean |Y change| >= 8 at 160x90: the same view re-framed can keep corr 0.96 at a grey jump of 14) ...
CONTRAST = 3.0       # ... and at least 3x the sides' own motion (their real changes, repeats skipped) by the same measure
INNER = 0.75         # a stray's own frames are one picture (alike, corr >= 0.75, no jump among them)
ALIKE = 0.75         # the frames around a stray alike (corr >= 0.75): a stray inside a shot; else a short shot inside a cut (A | X | B)
BLEND_R2 = 0.9       # a 1-frame stray that is a mix of both sides (a dissolve's or a wipe's frame) is a transition, not a stray
DZ_CUT = 0.3         # the probe changes 30%+ of the frame's pictures there: a designed cut ...
DD_CUT = 0.1         # ... or items covering 10%+ of the frame appear, go or fade there (a stamp, a card)
REPEAT_D = 0.3       # a step under 0.3 mean |Y change| at 160x90 is a repeated picture (30-fps footage shows each picture twice)
SIDE_LOOK = 8        # the sides' motion: the 2 nearest real changes within 8 frames


def _blend_r2(x, a, b):
    """how much of thumb x a mix of thumbs a and b explains (least squares with an offset): 1 = a dissolve frame between them"""
    A = np.stack([a, b, np.ones_like(a)], 1)
    coef, *_ = np.linalg.lstsq(A, x, rcond=None)
    res = x - A @ coef
    tot = ((x - x.mean()) ** 2).sum()
    return 1.0 - float((res ** 2).sum() / tot) if tot > 1e-6 else 1.0


def _side_motion(fe, i, step):
    """a side's own motion: the larger (1 - corr, mean |Y change|) of its 2 nearest real changes (repeats skipped), looking from step i
    (c1[i] = frame i against i-1) away from the run. 24-fps footage shows its pictures 3, 2, 3 frames (60/24), each new picture at corr
    0.4-0.6 to the one before (fast motion), so a 2-frame picture would read as a stray against sides measured inside their own repeats
    (corr 1.0); its real changes are the sides' motion"""
    c1, d1 = fe["c1"], fe["d1"]
    us, ds, j = [], [], i
    for _ in range(SIDE_LOOK):
        if j < 1 or j >= len(c1):
            break
        if not np.isnan(c1[j]) and not np.isnan(d1[j]) and d1[j] > REPEAT_D:
            us.append(1 - float(c1[j]))
            ds.append(float(d1[j]))
            if len(us) == 2:
                break
        j += step
    return (max(us), max(ds)) if us else (0.0, 0.0)


def _jump(fe, f, mu, md):
    """step f (frame f against f-1) a jump against motion (mu, md)?"""
    u, d = 1 - float(fe["c1"][f]), float(fe["d1"][f])
    if np.isnan(u) or np.isnan(d):
        return False
    return (u >= max(J_U, CONTRAST * mu)) or (d >= max(J_D, CONTRAST * md))


def flash_candidates(F0, fe):
    """runs [a, b] (indices into the measures) of 1-FLASH_MAX frames, one picture, with a jump into them and a jump out (see check_flash)"""
    c1, n = fe["c1"], len(fe["c1"])
    cands = []
    for a in range(3, n - 4):
        if np.isnan(c1[a]):
            continue
        u0, d0 = 1 - float(c1[a]), float(fe["d1"][a])
        if u0 < J_U and d0 < J_D:
            continue
        mb = _side_motion(fe, a - 1, -1)
        for k in range(1, FLASH_MAX + 1):
            b = a + k - 1
            if b + 3 >= n:
                break
            if k > 1 and (np.isnan(c1[b]) or c1[b] < INNER or (1 - c1[b] >= J_U) or fe["d1"][b] >= J_D):
                break   # the run is no longer one picture
            ma = _side_motion(fe, b + 2, +1)
            m = (max(mb[0], ma[0], 0.03), max(mb[1], ma[1], 0.3))
            if _jump(fe, a, *m) and _jump(fe, b + 1, *m):
                # a dark run is BLACK_DIP's to judge (designed or not); this check is for pictures
                top, side = float(np.nanmax(fe["lum"][a: b + 1])), float(min(fe["lum"][a - 1], fe["lum"][b + 1]))
                if top <= DIP_RATIO * side and side - top >= DIP_LEVELS:
                    break
                cands.append((a, b, float(c1[a]), float(c1[b + 1]), float(fe[f"c{k + 1}"][b + 1]) if k + 1 <= LAGS else float("nan")))
                break
    return cands


def _jump_cause(pr, pub, f, u, d):
    """what a rendered jump at step f is: 'design' (the probe's pictures change there, +-1 frame), 'source' (the main clip's own file
    changes as much there, +-1 source frame) or 'render' (nothing explains it); and the clip's name and second"""
    if f >= len(pr["dz"]):
        return "render", None, None
    if float(np.nanmax(pr["dz"][max(0, f - 1): f + 2])) >= DZ_CUT or float(np.nanmax(pr["dd"][max(0, f - 1): f + 2])) >= DD_CUT:
        return "design", None, None
    c = pr["clip"]
    if c[f] < 0 or c[f] != c[f - 1] or pr["cover"][f] < 0.5 or np.isnan(pr["s"][f]) or np.isnan(pr["s"][f - 1]):
        return "render", None, None
    src = _src_path(pub, pr, f)
    if src is None:
        return "render", None, None
    sfps = src_fps(src)
    i0, i1 = math.floor(float(pr["s"][f - 1]) * sfps + 1e-6), math.floor(float(pr["s"][f]) * sfps + 1e-6)
    sf, si = src_gray(src, max(0, i0 - 1) / sfps, (i1 + 1.5) / sfps)
    if len(sf) < 2:
        return "render", src.name, float(pr["s"][f])
    st = thumbs(sf.astype(np.float32)).astype(np.float64)
    su = 1 - corr_pairs(st[1:], st[:-1])
    sd = np.abs(np.diff(sf.astype(np.float32), axis=0)).mean(axis=(1, 2))
    if (len(su) and float(su.max()) >= 0.5 * u) or (len(sd) and float(sd.max()) >= 0.5 * d):
        return "source", src.name, float(pr["s"][f])
    return "render", src.name, float(pr["s"][f])


def check_flash(F0, fe, pieces, pr=None, pub=None, fps=FPS):
    """FLASH_FRAME: 1-8 frames of one picture with a jump into them and a jump out of them, each jump (1 - corr >= J_U or a grey jump
    >= J_D) at least CONTRAST x the sides' own motion. The frames around alike (corr >= ALIKE): a stray inside a shot; else a short shot
    squeezed into a cut (A | X | B): a "flash frame" at a cut. A 1-frame X that is a mix of A and B (R2 >= BLEND_R2) is a dissolve's or
    wipe's frame and passes.
    With a probe each jump gets a cause: 'design' (the probe's pictures change there), 'source' (the clip's own file jumps as much there)
    or 'render' (nothing explains it). Both designed: the composition's own short shot (the gate's to judge) and passes. Both in the
    source: the footage's own (a camera flash, a promo's quick cuts, a menu animating in) and passes. A 'render' jump is a fault at render
    time; a designed cut beside a source jump is the source's own cut at the play's edge (a few frames of another shot of the source at a
    clip's head) and is flagged for a trim."""
    flags = []
    for a, b, ca, cb, cab in flash_candidates(F0, fe):
        a_film, b_film = F0 + a, F0 + b
        k = b - a + 1
        in_cut = np.isnan(cab) or cab < ALIKE
        if in_cut and k == 1:
            win = rgb_or_gray(pieces, a_film - 1, b_film + 1)
            if win is not None and len(win) == 3:
                th = thumbs(win.astype(np.float32)).astype(np.float64)
                if _blend_r2(th[1], th[0], th[2]) >= BLEND_R2:
                    continue
        kind, where = "render", ""
        if pr is not None and b_film + 1 < len(pr["dz"]):
            if float(np.nanmax(pr["lit"][max(0, a_film - SIDE): b_film + 1 + SIDE])) < NOTHING_LIT:
                continue   # a stray on a ground the probe shows dark for longer than a dip (a text animating on black): the design's
            j1 = _jump_cause(pr, pub, a_film, 1 - ca, float(fe["d1"][a]))
            j2 = _jump_cause(pr, pub, b_film + 1, 1 - cb, float(fe["d1"][b + 1]))
            causes = (j1[0], j2[0])
            if causes == ("design", "design"):
                continue
            if "render" in causes:
                kind = "render"
            elif causes == ("source", "source"):
                # both jumps inside the clip's own file: its footage (a camera flash, a dissolve and a cut in a promo, a menu header
                # animating in, the source's own dissolve), wherever it sits in the play
                continue
            else:
                kind = "source"
            named = j1 if j1[1] else j2
            if named[1]:
                where = f"; {named[1]} at {named[2]:.2f} s"
            where += f" (jump in: {causes[0]}, jump out: {causes[1]})"
        side = ("inside a shot (the frames around alike)" if not in_cut else "between two other pictures" if np.isnan(cab)
                else "in a cut (a short picture between two shots)")
        cause = {"render": "a stray picture at render time" if pr is not None else "a stray picture (no probe: designed or not unknown)",
                 "source": "the source's own cut at the play's edge: trim the clip"}[kind]
        flags.append({"check": "FLASH_FRAME", "key": str(a_film), "at": a_film, "to": b_film,
                      "what": f"{mmss(a_film, fps)}: {k} frame(s) of one picture with a jump in (corr {ca:.2f}, grey {fe['d1'][a]:.1f}) and out "
                              f"(corr {cb:.2f}, grey {fe['d1'][b + 1]:.1f}) {side}{where}: {cause}"})
    return flags


# ---- FROZEN
STILL_D = 0.25       # a candidate: every free cell's mean |Y change| at 160x90 under 0.25 from frame to frame ...
FROZEN_MIN = 8       # ... for 8+ frames (0.13 s) ...
SRC_NEW = 3          # ... while the probe moves on through 3+ source frames
FREE_MIN = 6         # cells of the clip with nothing over them, at least
SRC_RUN = 1.5        # the source must change over the run: its picture laid where the clip sits, mean |Y change| first to last >= 1.5
TRACK = 0.25         # frozen: the render changes under 0.25x what the source changes over the run, scaled by how the render tracks
                     # the source just before or after it in the same play (its blur and dimming: a blurred ground behind a card follows
                     # its footage at a fraction of the source's change)
CAL_MIN = 1.0        # a calibration window counts when the source changes by 1.0+ over it (under it the render's own noise sets the
                     # ratio: a clip under a dark overlay the probe does not see can read 4x)


def _expected_frame(src_frame, box, W=1920, H=1080):
    """a source frame (160x90 luma) laid where the probe puts the clip's picture (its box in composition pixels), on a 160x90 frame"""
    # sub-pixel exact (an affine map), as the render pushes in smoothly: whole-pixel placement at 160x90 reads a slow push as a change
    # of 3 grey levels
    from PIL import Image
    x, y, w, h = (float(v) for v in box)
    if w < 1 or h < 1:
        return np.zeros((GH, GW), np.float32)
    sh, sw = src_frame.shape
    # Pillow maps an output pixel's centre (u + 0.5) to the input coordinate a(u + 0.5) + c (pixel centres at i + 0.5 there too)
    a, e = (W / GW) / w * sw, (H / GH) / h * sh
    c, f = -x / w * sw, -y / h * sh
    img = Image.fromarray(src_frame.astype(np.float32), mode="F")
    out = np.asarray(img.transform((GW, GH), Image.AFFINE, (a, 0, c, 0, e, f), resample=Image.BILINEAR, fillcolor=0.0), np.float32)
    return out


def _free_pixels(mask):
    m = np.zeros((GH, GW), bool)
    cw, ch = GW // CGX, GH // CGY
    for j in range(CGX * CGY):
        if mask >> j & 1:
            cy, cx = divmod(j, CGX)
            m[cy * ch:(cy + 1) * ch, cx * cw:(cx + 1) * cw] = True
    return m


def check_frozen(F0, fe, cells, pr, pub, pieces, fps=FPS):
    """FROZEN: the probe's main clip (the pane with the most of the frame showing it, half the frame or more) moving on through SRC_NEW+
    source frames while every one of its free cells (nothing drawn over them) changes under STILL_D a frame for FROZEN_MIN+ frames,
    confirmed against the source: the source's own frames, laid where the probe puts the clip, change by SRC_RUN+ from the run's first
    frame to its last, and the render changes under TRACK x that, scaled by how much the render follows the source over a window of the
    same length just before or after (same play: same blur, same dimming). Still footage, a held frame or a slow-motion hold in the source
    is the source's own and passes; a blurred, dimmed ground moving slowly behind a card passes by its calibration."""
    if pr is None:
        return []
    n = len(fe["lum"])
    flags = []
    still = np.zeros(n, bool)
    clip_at = np.full(n, -1, np.int64)
    for i in range(n):
        f = F0 + i
        if f >= len(pr["clip"]) or pr["clip"][f] < 0 or pr["cover"][f] < 0.5:
            continue
        free = int(pr["free"][f])
        idx = [j for j in range(CGX * CGY) if free >> j & 1]
        if len(idx) < FREE_MIN:
            continue
        cv = cells[i, idx].astype(np.float32)
        if np.isnan(cv).any():
            continue
        clip_at[i] = pr["clip"][f]
        still[i] = float(cv.max()) < STILL_D
    i = 0
    while i < n:
        if not still[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and still[j + 1] and clip_at[j + 1] == clip_at[i]:
            j += 1
        if j - i + 2 >= FROZEN_MIN:
            fl = _confirm_frozen(F0 + i - 1, F0 + j, pr, pub, pieces, fps)
            if fl:
                flags.append(fl)
        i = j + 1
    return flags


def _confirm_frozen(A, B, pr, pub, pieces, fps):
    """the still run A..B (one picture on screen) against its source (see check_frozen): a flag, or None"""
    src = _src_path(pub, pr, A)
    s = pr["s"]
    if src is None or np.isnan(s[A: B + 1]).all():
        return None
    sfps = src_fps(src)

    def sidx(f):
        return None if np.isnan(s[f]) else int(math.floor(float(s[f]) * sfps + 1e-6))

    if len({sidx(f) for f in range(A, B + 1)} - {None}) < SRC_NEW:
        return None
    pa, pb = _play_edges(pr, A)
    L = B - A
    w0, w1 = max(pa, A - L), min(pb, B + L)
    full = (1 << (CGX * CGY)) - 1
    mask = full
    for f in range(w0, w1 + 1):
        mask &= int(pr["free"][f])
    if bin(mask).count("1") < FREE_MIN:
        mask = int(pr["free"][A])
    px = _free_pixels(mask)
    ids = [sidx(f) for f in range(w0, w1 + 1)]
    known = [x for x in ids if x is not None]
    sf, si = src_gray(src, min(known) / sfps, (max(known) + 0.5) / sfps)
    if len(sf) == 0:
        return None
    # first the source alone (cheap): its whole frame must change inside the run, or the run is the footage holding still
    ia, ib = A + 2, B - 2
    if ib - ia < 4 or ids[ia - w0] is None or ids[ib - w0] is None:
        return None
    ka, kb = (int(np.clip(ids[f - w0] - si[0], 0, len(sf) - 1)) for f in (ia, ib))
    if float(np.abs(sf[kb].astype(np.float32) - sf[ka]).mean()) < 0.5 * SRC_RUN:
        return None
    rend = rgb_or_gray(pieces, w0, w1)
    if rend is None or len(rend) < w1 - w0 + 1:
        return None
    rend = rend.astype(np.float32)
    exp = {}

    def E(f):
        k = ids[f - w0]
        if k is None:
            return None
        k = int(np.clip(k - si[0], 0, len(sf) - 1))
        key = (k, tuple(np.round(pr["box"][f], 0)))
        if key not in exp:
            exp[key] = _expected_frame(sf[k], pr["box"][f])
        return exp[key]

    def disp(f1, f2):
        e1, e2 = E(f1), E(f2)
        if e1 is None or e2 is None:
            return None, None
        return float(np.abs(rend[f2 - w0] - rend[f1 - w0])[px].mean()), float(np.abs(e2 - e1)[px].mean())

    # the run's inside: 2 frames off each end, so a source change that lands on the run's last frame by one frame's rounding (Remotion's
    # pick of the source frame against the probe's floor) isn't read as a change the render missed (a menu that jumps from one slot to
    # the next, the render one frame later)
    r_run, e_run = disp(ia, ib)
    if r_run is None or e_run < SRC_RUN:
        return None
    A0, B0, L = A, B, ib - ia
    A, B = ia, ib
    ks = []
    for f1, f2 in ((A - L, A), (B, B + L)):
        if f1 >= w0 and f2 <= w1:
            r, e = disp(f1, f2)
            if r is not None and e >= CAL_MIN:
                ks.append(r / e)
    k = max(ks) if ks else 1.0
    if r_run >= TRACK * k * e_run:
        return None
    return {"check": "FROZEN", "key": str(A0), "at": A0, "to": B0,
            "what": f"{mmss(A0, fps)}-{mmss(B0, fps)}: {src.name} stands still for {B0 - A0 + 1} frames while the probe plays it on through "
                    f"{float(np.nanmin(s[A0:B0 + 1])):.2f}-{float(np.nanmax(s[A0:B0 + 1])):.2f} s of the file, where its picture changes by "
                    f"{e_run:.1f} (the render {r_run:.2f}; around it the render follows the file at {k:.2f}x"
                    f"{'' if ks else ', no window to tell'}): a freeze at render time"}


# ---- FRAMES
def check_frames(pieces, counts, expected, scanned_whole):
    """FRAMES: a piece's packets (ffprobe -count_packets) against its share of the film, and the frames decoded against the packets"""
    flags = []
    for i, (path, f0, n_pk) in enumerate(pieces):
        exp = expected[i] if expected else None
        if exp is not None and n_pk != exp:
            flags.append({"check": "FRAMES", "key": Path(path).name, "at": f0, "to": f0 + max(n_pk or 0, exp) - 1,
                          "what": f"{Path(path).name} holds {n_pk} frames where its share of the film is {exp} (frames {f0}-{f0 + exp - 1})"})
        if scanned_whole and i in counts and n_pk is not None and counts[i] != n_pk:
            flags.append({"check": "FRAMES", "key": Path(path).name + ":decoded", "at": f0, "to": f0 + n_pk - 1,
                          "what": f"{Path(path).name}: {counts[i]} frames decoded of its {n_pk} packets"})
    return flags


# ===================================================================================================================== the strips
def piece_of(pieces, f):
    for path, f0, n in pieces:
        if f0 <= f < f0 + n:
            return path, f - f0
    return None, None


def rgb_or_gray(pieces, fa, fb, rgb=False, w=GW, h=GH):
    """film frames fa..fb (clamped to the pieces) as luma (or RGB) arrays, decoded around them only"""
    out = []
    f = fa
    while f <= fb:
        path, loc = piece_of(pieces, f)
        if path is None:
            f += 1
            continue
        n_here = next(n for p, f0, n in pieces if p == path) - loc
        cnt = min(fb - f + 1, n_here)
        fr = rgb_frames(path, loc, cnt, w, h) if rgb else gray_frames(path, loc, cnt, w, h)
        out.append(fr)
        f += cnt
    return np.concatenate(out) if out else None


def write_strip(pieces, fl, out_dir, fps=FPS):
    """frames at-3..to+3 (at most 7 + the run) side by side at 320x180, the flagged ones outlined red, frame numbers under them"""
    from PIL import Image, ImageDraw
    a, b = fl["at"], fl.get("to", fl["at"])
    if fl["check"] == "FROZEN":
        b = min(b, a + 3)   # a long freeze: its first frames and the frames before
    if fl["check"] == "FRAMES":
        return None
    fa, fb = max(0, a - 3), b + 3
    fr = rgb_or_gray(pieces, fa, fb, rgb=True, w=STRIP_W, h=STRIP_H)
    if fr is None:
        return None
    pad = 4
    im = Image.new("RGB", (len(fr) * (STRIP_W + pad) + pad, STRIP_H + 2 * pad + 18), (24, 24, 24))
    dr = ImageDraw.Draw(im)
    for i, x in enumerate(fr):
        f = fa + i
        px = pad + i * (STRIP_W + pad)
        im.paste(Image.fromarray(x), (px, pad))
        if a <= f <= fl.get("to", a):
            dr.rectangle([px - 2, pad - 2, px + STRIP_W + 1, pad + STRIP_H + 1], outline=(255, 40, 40), width=3)
        dr.text((px + 2, pad + STRIP_H + 4), f"{f}  {mmss(f, fps)}", fill=(230, 230, 230))
    out = Path(out_dir) / f"{fl['check']}_{a}.png"
    im.save(out)
    return out


# ======================================================================================================================= the scan
def scan(pieces, probe_path=None, out_dir=None, fps=60, pub=None, frange=None, expected=None, strips=True, workers=WORKERS):
    """Scan a render's pieces [(path, first_film_frame), ...] (its chunk files in order, or one joined file with first frame 0).
    probe_path: the gate's probe.jsonl for this cut (None: no designed/footage exemptions, every dip and stray is flagged);
    out_dir: where the strips, the caches and the report go; pub: the public dir the probe's clip names are relative to (the FROZEN and
    footage checks read the sources there); frange: (a, b) film frames to scan (with a 12-frame margin) instead of everything;
    expected: each piece's frame count by the film's split (FRAMES). Returns the flags, sorted by frame."""
    global FPS
    FPS = fps
    out_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="render_scan_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    missing = [str(p) for p, _ in pieces if not Path(p).exists()]
    if missing:
        raise SystemExit(f"render scan: no such piece: {', '.join(missing)}")
    with ThreadPoolExecutor(workers) as ex:
        counted = list(ex.map(lambda p: packets(p[0]), pieces))
    full = [(str(path), int(f0), n) for (path, f0), n in zip(pieces, counted)]
    say(f"render scan: {len(full)} piece(s), {sum(n or 0 for _, _, n in full)} frames by their packets")
    cache = out_dir / "render_scan_features.npz"
    key = json.dumps([[p, f0, n, os.path.getsize(p), int(os.path.getmtime(p))] for p, f0, n in full] + [list(frange) if frange else None])
    got = None
    if cache.exists():
        with np.load(cache, allow_pickle=False) as z:
            if str(z["key"]) == key:
                got = (int(z["F0"]), int(z["F1"]), {k: z[k] for k in FEATS}, z["cells"],
                       {int(k): int(v) for k, v in json.loads(str(z["counts"])).items()})
                say(f"  frame measures read back from {cache.name}")
    if got is None:
        got = measure_pieces(full, frange, workers)
        F0, F1, fe, cells, counts = got
        np.savez(cache, key=np.array(key), F0=F0, F1=F1, cells=cells, counts=np.array(json.dumps({str(k): v for k, v in counts.items()})), **fe)
    F0, F1, fe, cells, counts = got
    t_dec = time.time() - t0
    pr = None
    if probe_path:
        pr = probe_summary(probe_path, out_dir / "probe_summary.npz")
    flags = []
    for name, fn in (("BLACK_DIP", lambda: check_black(F0, fe, pr, pub, fps)), ("FLASH_FRAME", lambda: check_flash(F0, fe, full, pr, pub, fps)),
                     ("FROZEN", lambda: check_frozen(F0, fe, cells, pr, pub, full, fps)),
                     ("FRAMES", lambda: check_frames(full, counts, expected, frange is None))):
        t1 = time.time()
        got = fn()
        say(f"  {name}: {len(got)} flag(s) ({time.time() - t1:.0f} s)")
        flags += got
    if frange:
        flags = [x for x in flags if x["check"] == "FRAMES" or frange[0] <= x["at"] <= frange[1]]
    # a stray that is a dark dip is reported once, as the dip
    dips = [(x["at"], x["to"]) for x in flags if x["check"] == "BLACK_DIP"]
    flags = [x for x in flags if not (x["check"] == "FLASH_FRAME" and any(a - 1 <= x["at"] <= b + 1 for a, b in dips))]
    flags.sort(key=lambda x: (x["at"], x["check"]))
    if strips:
        # the last run's strips go (only the files its report lists), so the folder holds this run's alone
        last = out_dir / "render_scan.json"
        if last.exists():
            try:
                for old in json.loads(last.read_text(encoding="utf-8")):
                    sp = Path(old.get("strip", ""))
                    if sp.name and sp.parent == out_dir and sp.suffix == ".png" and sp.exists():
                        sp.unlink()
            except (ValueError, OSError):
                pass
        for fl in flags:
            p = write_strip(full, fl, out_dir, fps)
            if p:
                fl["strip"] = str(p)
    say(f"render scan: {len(flags)} flag(s); decoding {t_dec / 60:.1f} min, all {(time.time() - t0) / 60:.1f} min")
    return flags


# ========================================================================================================================= the CLI
def find_pieces(folder, total, chunks):
    """a folder's pieces: parts.json [{"file", "f0", "f1"}] when there is one, else part_NN.mkv with first frames round(total*i/chunks)"""
    folder = Path(folder)
    man = folder / "parts.json"
    if man.exists():
        d = json.loads(man.read_text(encoding="utf-8"))
        pieces = [((folder / x["file"]) if not Path(x["file"]).is_absolute() else Path(x["file"]), int(x["f0"])) for x in d]
        expected = [int(x["f1"]) - int(x["f0"]) + 1 if "f1" in x else None for x in d]
        return pieces, expected
    files = sorted(folder.glob("part_*.mkv"))
    if not files:
        raise SystemExit(f"no part_*.mkv or parts.json in {folder}")
    if chunks and len(files) != chunks:
        say(f"note: {len(files)} part files where video.toml says {chunks} chunks; the split uses {len(files)}")
    k = len(files)
    starts = [round(total * i / k) for i in range(k + 1)]
    return [(f, starts[i]) for i, f in enumerate(files)], [starts[i + 1] - starts[i] for i in range(k)]


def write_report(flags, out_dir, head):
    lines = [f"# Render scan: {'PASS' if not flags else f'{len(flags)} flag(s)'}", "", *head, ""]
    for fl in flags:
        to = f"-{mmss(fl['to'])}" if fl.get("to") not in (None, fl["at"]) else ""
        strip = f" ([strip]({Path(fl['strip']).name}))" if fl.get("strip") else ""
        lines.append(f"- **{fl['check']}** {mmss(fl['at'])}{to} (frame {fl['at']}{'-' + str(fl['to']) if fl.get('to') not in (None, fl['at']) else ''}): {fl['what']}{strip}")
    (Path(out_dir) / "render_scan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (Path(out_dir) / "render_scan.json").write_text(json.dumps(flags, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video", help="the video's id or slug (videos/<slug>)")
    ap.add_argument("--version", type=int, required=True, help="the render's version: render/parts_v<N>")
    ap.add_argument("--parts", help="the pieces' folder (relative to the video's media folder); default render/parts_v<N>")
    ap.add_argument("--file", action="append", help="scan these files instead: path[:first_frame] (repeatable; a joined file is path:0)")
    ap.add_argument("--probe", help="the probe (relative to the media folder); default pipeline/gate/probe.jsonl when it exists")
    ap.add_argument("--no-probe", action="store_true", help="scan without a probe (every dip and stray flagged)")
    ap.add_argument("--range", help="film frames a-b only")
    ap.add_argument("--out", help="the output folder; default pipeline/render_scan_v<N>")
    ap.add_argument("--total", type=int, help="the film's frames (default video.toml's)")
    ap.add_argument("--no-strips", action="store_true")
    a = ap.parse_args()
    from common import Video, find_video
    v = Video(find_video(a.video))
    total = a.total or v.frames()
    if a.file:
        pieces = []
        for x in a.file:
            p, _, f0 = x.rpartition(":") if x.rpartition(":")[2].isdigit() and len(x.rpartition(":")[0]) > 2 else (x, "", "0")
            pieces.append((Path(p), int(f0 or 0)))
        expected = None
    else:
        folder = (v.dj / a.parts) if a.parts else v.render_dir / f"parts_v{a.version}"
        pieces, expected = find_pieces(folder, total, v.chunks)
    probe = None
    if not a.no_probe:
        probe = (v.dj / a.probe) if a.probe else v.pipe_dir / "gate" / "probe.jsonl"
        if not probe.exists():
            if a.probe:
                raise SystemExit(f"no probe at {probe}")
            say(f"no probe at {probe}: scanning without one")
            probe = None
    out = Path(a.out) if a.out else v.pipe_dir / f"render_scan_v{a.version}"
    if a.out and not Path(a.out).is_absolute():
        out = v.dj / a.out
    frange = tuple(int(x) for x in a.range.split("-")) if a.range else None
    flags = scan(pieces, probe, out, v.fps, v.pub, frange, expected, not a.no_strips)
    head = [f"video {v.id}, version {a.version}, {time.strftime('%Y-%m-%d %H:%M')}; pieces: {', '.join(Path(p).name for p, _ in pieces)}",
            f"probe: {probe or 'none (no designed or footage exemptions)'}; range: {a.range or 'the whole film'}"]
    write_report(flags, out, head)
    say(f"report: {out / 'render_scan.md'}")
    sys.exit(1 if flags else 0)


if __name__ == "__main__":
    main()
