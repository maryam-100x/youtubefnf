"""pick_boards.py: every line of a script with its picture options on a board, and the picks as exact spans an agent cuts.

Why: picking a picture per line is the slowest step of a footage video, and every picture is picked by the chat from the whole
catalogue, frames looked at, while agents get only exact instructions. One run searches the footage brain (find_shot.py: keywords + text
and CLIP embeddings, each hit's light and subject measured, art and murky shots ranked down) for EVERY line of the script at once, the
models loaded once, and draws one board per line:
  - the line's top candidates: a clip as the first, middle and last frame of its record, a still as itself, each with what it shows,
    its span, its lit and murky stretches, its flags and the videos that already played it;
  - the top candidate's scene: its source at one frame a second around the span, the span outlined in green, every second a past
    video already played outlined in red with that video's name (qa_reused's fingerprints: no clip from a past video);
  - each candidate's "USED by frames" from the same fingerprints over its whole span (four checks a second, frames decoded at the
    source's own rate and timed by their index, the strip's too), so it agrees with the strip at a glance, and the brain's ledger beside it.
The chat looks, writes each pick into PICKS.json, and `cut` turns the picks into the house's clip manifest (and cuts them, --run).

  EDIT tools/footage/pick_boards.py boards <script.md> <out dir> [--beats S001-S020,S031] [--n 5] [--scene 8]
        [--src A1,A2,LIB1,IMG] [--min-dur 1.0] [--exclude-used v11,v12] [--own PUBLIC/v12/clips]
        [--split sentence|clause|beat] [--no-embed]
      -> <out>/<NN>_<section>/<beat>_<k>.jpg   one board per line (1920 px wide)
         <out>/PICKS.json   every line: its section, beat, words, board and candidates (n, key, id, file, in, out, clean span, lit
                            span, murky stretches, flags, desc, used_in, score); "pick": null, "in": null, "out": null for the chat
         <out>/PICKS.md     the same as text, each line with its board, so the boards are read beside their words
  EDIT tools/footage/pick_boards.py cut <out>/PICKS.json --prefix v12 --manifest <video>_clips.json [--run <clips dir>]
      -> {name: [source key, in, out]}, the format the prep scripts read: only the lines with a pick; a still pick goes under
         "stills" with its file. --run also cuts each clip (1920x1080, libx264 crf 15 medium, -g 15 -bf 0, no audio; a letterboxed
         source whole with its own bars). A pick's span is its candidate's clean span unless "in"/"out" are set.

Script format: the house's `## Beats` block, `[S005] VOICE: <words>` lines under `# ===== <SECTION> =====` headers (script.md). A line
is a sentence (--split clause cuts long sentences at their commas; --split beat keeps a beat whole)."""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "motion"))
import brain_lib as B  # noqa: E402
import find_shot as FS  # noqa: E402
from sheetfont import font as sheet_font  # noqa: E402

W = 1920
TW, TH = 352, 198                     # a candidate's frame (three = 1056 px)
SW, SH = 188, 106                     # a scene frame (ten a row)
GREEN, RED, HEAD = (60, 220, 90), (235, 45, 45), (255, 230, 0)
SEC = re.compile(r"^#\s*=+\s*(.+?)\s*=+\s*$")
BEAT = re.compile(r"^\[(S\d+[a-z]?)\]\s*VOICE:\s*(.+)$")
ENC = ["-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", "-bf", "0"]


def font(size, bold=False):
    return sheet_font(size, bold)


# ------------------------------------------------------------------------------------------------------------------------------- the script
def parse(script):
    """[(section name, [(beat, words), ...]), ...] from the `## Beats` block"""
    secs, cur = [], None
    for raw in Path(script).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        m = SEC.match(s)
        if m:
            cur = (m.group(1).strip(), [])
            secs.append(cur)
            continue
        m = BEAT.match(s)
        if m:
            if cur is None:
                cur = ("SCRIPT", [])
                secs.append(cur)
            cur[1].append((m.group(1), m.group(2).strip()))
    return secs


def split_lines(words, how):
    if how == "beat":
        return [words]
    out = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[\"“'A-Z0-9])", words) if p.strip()]
    if how == "clause":
        fine = []
        for p in out:
            parts = [x.strip() for x in re.split(r"(?<=[,;])\s+", p)]
            buf = ""
            for x in parts:
                buf = f"{buf} {x}".strip()
                if len(buf.split()) >= 5:
                    fine.append(buf)
                    buf = ""
            if buf:
                if fine and len(buf.split()) < 5:
                    fine[-1] = f"{fine[-1]} {buf}"
                else:
                    fine.append(buf)
        out = fine
    return out


def beat_filter(spec):
    """'S001-S020,S031' -> a test on beat ids"""
    if not spec:
        return lambda b: True
    num = lambda b: int(re.sub(r"\D", "", b))  # noqa: E731
    parts = []
    for p in spec.split(","):
        a, _, b = p.partition("-")
        parts.append((num(a), num(b or a)))
    return lambda beat: any(x <= num(beat) <= y for x, y in parts)


# ------------------------------------------------------------------------------------------------------------------------------ the pictures
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "section"


def src_code(r):
    return r.get("_code") or (r["src"] if r["src"] in B.MASTERS or r["src"] in B.STILLS else r["id"].split("/")[0])


def video_file(r, proxy=False):
    """the record's video file (a master's 480p proxy when `proxy`: the same timeline frame for frame)"""
    if r["src"] in B.MASTERS:
        m = B.MASTERS[r["src"]]
        return Path(m["proxy"]) if proxy and Path(m["proxy"]).exists() else Path(m["file"])
    return Path(r["file"])


def cand_frames(r):
    """a clip's first, middle and last record frames (the brain's frames when it has them, else grabbed); a still as itself"""
    if r.get("kind") == "image":
        try:
            return [Image.open(r["file"]).convert("RGB")]
        except OSError:
            return [Image.new("RGB", (TW, TH), (90, 0, 0))]
    fl = r.get("frames", [])
    fl = [fl[0], fl[len(fl) // 2], fl[-1]] if len(fl) >= 3 else fl
    if not fl:
        fps = r.get("fps", 30)
        fl = [int(round(t * fps)) for t in (r["in"], (r["in"] + r["out"]) / 2, r["out"] - 0.1)]
    kf = B.key_file(r["src"] if r["src"] in B.MASTERS else r["id"].split("@")[0])
    out = []
    for f in fl:
        p = B.WORK / "frames" / kf / f"{f:07d}.jpg"
        if p.exists():
            out.append(Image.open(p).convert("RGB"))
        else:
            out.append(B.grab(video_file(r, proxy=True), B.seek_time(f, r.get("fps", 30)), 854, 480))
    return out


def vid_label(folder):
    """a past clip's folder as the video it belongs to: v103 -> 103, s055 -> 055 (the motion public dirs' names), else the folder"""
    m = re.match(r"^[vs](\d{3})", folder)
    return m.group(1) if m else folder


class Used:
    """qa_reused's fingerprints of every past video's clips (tools/motion/qa_reused.py); `own` = this video's own clips folder, never
    counted"""

    def __init__(self, own=None, bits=6):
        import qa_reused as Q
        self.Q, self.bits = Q, bits
        cache = json.loads(Q.CACHE.read_text(encoding="utf-8")) if Q.CACHE.exists() else {}
        own_p = Path(own).resolve().parent if own else None
        others = sorted(p for p in B.PUBLIC.glob("*/clips/*.mp4") if own_p is None or p.parent.parent.resolve() != own_p)
        self.olds, self.old_bits, self.idx, _ = Q.old_array(cache, others)

    def of(self, rgb_small, pic):
        """'fresh' or 'used:<video>' for one frame (the picture inside a letterboxed source's bars hashed, as the old clips were cut)"""
        if self.old_bits is None:
            return "fresh"
        im = Image.fromarray(rgb_small)
        x0, y0, x1, y1 = pic
        if (x0, y0, x1, y1) != (0.0, 0.0, 1.0, 1.0):
            w, h = im.size
            im = im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
        g = np.asarray(im.convert("L").resize((self.Q.W, self.Q.H), Image.BOX), np.uint8)
        hsh, flat = self.Q.dhash_arr(g)
        if flat:
            return "flat"
        d = self.Q.dist(self.old_bits, hsh)
        j = int(d.argmin())
        return f"used:{vid_label(self.olds[self.idx[j]].parent.parent.name)}" if d[j] <= self.bits else "fresh"


def span_used(r, used):
    """the past videos whose clips hold a frame of this record's whole span, by the same frames and fingerprints as the scene strip
    (four checks a second): {video: [times]}"""
    if used is None or r.get("kind") == "image":
        return {}
    out = {}
    for tt, st in checks(r, decode(r, r["in"], r["out"]), used):
        if st.startswith("used:") and r["in"] - 1e-6 <= tt <= r["out"] + 1e-6:
            out.setdefault(st[5:], []).append(round(tt, 2))
    return out


def decode(r, t0, t1):
    """every frame of the record's source from t0 to t1 (a master's 480p proxy), SW x SH: [(true time, array)]. Decoded at the source's
    own rate and timed by frame index: ffmpeg's fps=1 hands over the LAST frame of each second (~0.47 s after its label), which put a
    strip's second past the record's cut and made it disagree with the candidate's own check"""
    f = video_file(r, proxy=True)
    fps = float(r.get("fps") or 30.0)
    raw = subprocess.run([B.FFMPEG, "-nostdin", "-v", "error", "-threads", "2", "-ss", f"{max(0.0, t0):.3f}", "-i", str(f), "-t",
                          f"{t1 - t0:.3f}", "-an", "-vf", f"scale={SW}:{SH}:flags=area", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    first = math.ceil(max(0.0, t0) * fps - 1e-6) / fps          # the first frame at or after t0
    sz = SW * SH * 3
    return [(first + i / fps, np.frombuffer(raw[i * sz:(i + 1) * sz], np.uint8).reshape(SH, SW, 3)) for i in range(len(raw) // sz)]


def checks(r, frames, used, per_s=4):
    """the frames' fingerprints, `per_s` a second (qa_reused hashed the old clips every 0.25 s): [(time, status)]"""
    if used is None or not frames:
        return [(tt, "fresh") for tt, _ in frames[::8]]
    pic = B.pic_of(r["src"])
    step = max(1, round(float(r.get("fps") or 30.0) / per_s))
    return [(tt, used.of(a, pic)) for tt, a in frames[::step]]


def scene(r, pad, used):
    """the source at one frame a second from `pad` s before the record to `pad` s after: [(time, image, status)]; a second is red when
    any of its four checks (0.25 s apart, the same as the candidate's own) is a past video's frame"""
    if r.get("kind") == "image":
        return []
    t0, t1 = max(0.0, r["in"] - pad), r["out"] + pad
    frames = decode(r, t0, t1)
    if not frames:
        return []
    ck = checks(r, frames, used)
    out = []
    k = 0
    while t0 + k <= frames[-1][0] + 1e-6:
        tt = t0 + k
        img = min(frames, key=lambda x: abs(x[0] - tt))[1]
        # a second inside the span counts only the span's own checks (and one outside only checks outside it): near a cut its half-second
        # window would reach the neighbouring shot, and the strip would disagree with the candidate's own verdict
        inside = r["in"] - 1e-6 <= tt <= r["out"] + 1e-6
        hit = [s for ts, s in ck if tt - 0.5 <= ts < tt + 0.5 and s.startswith("used") and (r["in"] - 1e-6 <= ts <= r["out"] + 1e-6) == inside]
        out.append((tt, Image.fromarray(img), hit[0] if hit else "fresh"))
        k += 1
    return out


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def cand_dict(k, h, uf=None):
    """a candidate as PICKS.json keeps it; `uf` its span's frame fingerprints {video: [times]} (used_frames); used_in = the ledger"""
    r = h["rec"]
    lit = h.get("lit")
    d = dict(n=k + 1, key=src_code(r) if r["src"] not in B.MASTERS else r["src"], id=r["id"], kind=r.get("kind", "video"),
             file=str(r.get("file", "")), fps=r.get("fps"), score=h["score"], flags=r.get("flags", []), desc=r.get("desc", ""),
             who=r.get("who", []), used_frames=uf or {}, used_in=r.get("used_in", []), notes=h.get("notes", []))
    if r.get("kind") != "image":
        d.update({"in": round(r["in"], 3), "out": round(r["out"], 3),
                  "clean": [round(r.get("clean_in", r["in"]), 3), round(r.get("clean_out", r["out"]), 3)],
                  "lit": [round(lit[0], 3), round(lit[1], 3)] if lit else None, "murky": [list(m) for m in lit[2]] if lit else []})
        if r["src"] not in B.MASTERS:
            d["key"] = Path(d["file"]).name
    return d


def used_text(c):
    """what the board says: the frames' verdict first (the same fingerprints as the scene strip), the ledger after"""
    fr = "; ".join(f'{v} @{", ".join(f"{x:.1f}" for x in ts[:4])}{"..." if len(ts) > 4 else ""}' for v, ts in c["used_frames"].items())
    return (f"USED by frames: {fr}" if fr else "fresh by frames"), "ledger: " + (",".join(c["used_in"]) or "-")


def draw(slot, hits, cands, scn, out):
    f1, f2, f3 = font(24, True), font(17), font(14)
    rowh = TH + 14
    sc_rows = (len(scn) + 9) // 10
    H = 96 + rowh * len(hits) + (40 + sc_rows * (SH + 20) if scn else 0)
    sh = Image.new("RGB", (W, H), (18, 18, 22))
    d = ImageDraw.Draw(sh)
    head = wrap(d, f'{slot["id"]}  "{slot["words"]}"', f1, W - 30)
    for i, ln in enumerate(head[:2]):
        d.text((12, 8 + i * 30), ln, fill=HEAD, font=f1)
    d.text((12, 70), f'{slot["section"]}  ·  pick: write its number into PICKS.json ("pick"), and "in"/"out" to trim inside its span',
           fill=(170, 170, 170), font=f3)
    for k, h in enumerate(hits):
        r = h["rec"]
        y = 96 + k * rowh
        ims = cand_frames(r)
        if r.get("kind") == "image":
            im = ims[0].copy()
            im.thumbnail((TW * 3, TH))
            sh.paste(im, ((TW * 3 - im.width) // 2, y + (TH - im.height) // 2))
        else:
            for j, im in enumerate(ims[:3]):
                sh.paste(im.resize((TW, TH)), (j * TW, y))
        c = cands[k]
        span = "still" if c["kind"] == "image" else (f'{B.mmss(c["in"])}-{B.mmss(c["out"])} ({c["out"] - c["in"]:.2f} s), clean '
                                                     f'{c["clean"][0]:.2f}-{c["clean"][1]:.2f}')
        tx = TW * 3 + 16
        lines = [(f'#{k + 1}  {c["id"]}   {span}', HEAD, f2)]
        info = [f'score {c["score"]:.2f}', "flags: " + (" ".join(c["flags"]) or "-"), *used_text(c)]
        if c.get("lit"):
            info.append(f'lit {c["lit"][0]:.2f}-{c["lit"][1]:.2f}' + (f', murky {", ".join(f"{a:.2f}-{b:.2f}" for a, b in c["murky"])}'
                                                                     if c["murky"] else ""))
        if c["notes"]:
            info.append("ranked: " + ", ".join(c["notes"]))
        lines.append(("   ".join(info), (255, 120, 110) if c["used_frames"] else (200, 200, 210), f3))
        lines += [(ln, (235, 235, 235), f3) for ln in wrap(d, c["desc"], f3, W - tx - 14)[:7]]
        yy = y + 2
        for text, col, ff in lines:
            for ln in wrap(d, text, ff, W - tx - 14)[:3]:
                d.text((tx, yy), ln, fill=col, font=ff)
                yy += 22 if ff is f2 else 18
    if scn:
        y0 = 96 + rowh * len(hits) + 8
        r = hits[0]["rec"]
        d.text((12, y0), f'the scene of #1: {r["id"].split("@")[0]} {B.mmss(scn[0][0])}-{B.mmss(scn[-1][0])}, one frame a second; green = '
                         f'its span, red = a past video played it (its name)', fill=(200, 200, 210), font=f2)
        for i, (t, im, st) in enumerate(scn):
            x, y = (i % 10) * (SW + 4) + 4, y0 + 30 + (i // 10) * (SH + 20)
            sh.paste(im, (x, y))
            inside = r["in"] - 1e-6 <= t <= r["out"] + 1e-6
            if inside:        # the span inside, a past video's use outside: a used second of the span shows both
                d.rectangle([x + 5, y + 5, x + SW - 6, y + SH - 6], outline=GREEN, width=3)
            if st.startswith("used"):
                d.rectangle([x, y, x + SW - 1, y + SH - 1], outline=RED, width=4)
            lab = B.mmss(t) + ("  " + st.split(":")[1] if st.startswith("used") else "")
            d.text((x + 2, y + SH + 2), lab, fill=RED if st.startswith("used") else (230, 230, 230), font=f3)
    out.parent.mkdir(parents=True, exist_ok=True)
    sh.save(out, quality=86)


# --------------------------------------------------------------------------------------------------------------------------------- the runs
def boards(a):
    secs = parse(a.script)
    if not secs:
        raise SystemExit(f"no [Sxx] VOICE: lines in {a.script}")
    keep = beat_filter(a.beats)
    srcs = set(a.src.split(",")) if a.src else None
    recs = FS.load_records(srcs)
    if not recs:
        raise SystemExit("the footage brain has no records for " + (a.src or "any source"))
    used = Used(a.own) if not a.no_used else None
    out = Path(a.out)
    picks, md = [], [f"# Picking boards: {Path(a.script).name}", "",
                     "One board per line (`pick_boards.py`): its top candidates from the footage brain and the scene of the first. Write the "
                     "pick's number into PICKS.json (`\"pick\"`), `\"in\"`/`\"out\"` to trim inside its span, then `pick_boards.py cut`.", ""]
    n_lines = 0
    for si, (name, beats) in enumerate(secs, 1):
        folder = f"{si:02d}_{slug(name)}"
        sec_md = []
        for beat, words in beats:
            if not keep(beat):
                continue
            for k, line in enumerate(split_lines(words, a.split), 1):
                sid = f"{beat}_{k}"
                hits = FS.search(line, recs, use_embed=not a.no_embed, min_dur=a.min_dur,
                                 exclude_used=[x for x in a.exclude_used.split(",") if x], n=a.n)
                if not hits:
                    continue
                scn = scene(hits[0]["rec"], a.scene, used) if a.scene > 0 else []
                cands = [cand_dict(i, h, span_used(h["rec"], used)) for i, h in enumerate(hits)]
                slot = {"section": f"{si:02d} {name}", "beat": beat, "k": k, "id": sid, "words": line,
                        "board": f"{folder}/{sid}.jpg", "cands": cands, "pick": None, "in": None, "out": None, "note": ""}
                draw(slot, hits, cands, scn, out / slot["board"])
                picks.append(slot)
                n_lines += 1
                fresh = sum(1 for _, _, st in scn if st == "fresh")
                sec_md += [f"### {sid} \"{line}\"", f"Board: `{slot['board']}`" + (f" (scene: {fresh} of {len(scn)} s fresh)" if scn else ""), ""]
                for c in slot["cands"]:
                    span = "still" if c["kind"] == "image" else f'{c["clean"][0]:.2f}-{c["clean"][1]:.2f} s clean'
                    sec_md.append(f'{c["n"]}. `{c["id"]}` {span} [{" ".join(c["flags"])}] {" / ".join(used_text(c))}: {c["desc"][:160]}')
                sec_md.append("")
                print(f"{sid}: {len(hits)} candidates -> {slot['board']}", flush=True)
        if sec_md:
            md += [f"## {si:02d} {name}", ""] + sec_md
    out.mkdir(parents=True, exist_ok=True)
    (out / "PICKS.json").write_text(json.dumps({"script": str(Path(a.script).resolve()), "lines": picks}, indent=1), encoding="utf-8")
    (out / "PICKS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{n_lines} lines, boards in {out}; PICKS.json and PICKS.md written")


def cut(a):
    data = json.loads(Path(a.picks).read_text(encoding="utf-8"))
    man, stills, missing = {}, {}, []
    for s in data["lines"]:
        if not s.get("pick"):
            missing.append(s["id"])
            continue
        c = s["cands"][int(s["pick"]) - 1]
        name = f'{a.prefix}_{s["id"].lower()}'
        if c["kind"] == "image":
            stills[name] = c["file"]
            continue
        lo, hi = s.get("in") if s.get("in") is not None else c["clean"][0], s.get("out") if s.get("out") is not None else c["clean"][1]
        if not (c["in"] - 0.01 <= lo < hi <= c["out"] + 0.01):
            raise SystemExit(f'{s["id"]}: in/out {lo}-{hi} lie outside its candidate\'s span {c["in"]}-{c["out"]}')
        man[name] = [c["key"], round(lo, 3), round(hi, 3)]
        if a.run:
            dst = Path(a.run) / f"{name}.mp4"
            dst.parent.mkdir(parents=True, exist_ok=True)
            src = c["file"] if c["key"] not in B.MASTERS else str(B.MASTERS[c["key"]]["file"])
            vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
            subprocess.run([B.FFMPEG, "-nostdin", "-y", "-v", "error", "-threads", "2", "-ss", f"{lo:.3f}", "-i", src, "-t", f"{hi - lo:.3f}",
                            "-an", "-vf", vf] + ENC + [str(dst)], check=True)
            print("cut", dst, flush=True)
    res = dict(man)
    if stills:
        res["stills"] = stills
    Path(a.manifest).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"{len(man)} clips, {len(stills)} stills -> {a.manifest}" + (f"; no pick yet: {', '.join(missing)}" if missing else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("boards")
    b.add_argument("script")
    b.add_argument("out")
    b.add_argument("--beats", default="", help="S001-S020,S031: only these beats")
    b.add_argument("--n", type=int, default=5, help="candidates a line")
    b.add_argument("--scene", type=float, default=8.0, help="seconds of the first candidate's source on each side (0 = none)")
    b.add_argument("--src", default="", help="only these sources (the keys of kb/footage/sources.json, library codes)")
    b.add_argument("--min-dur", type=float, default=0.0)
    b.add_argument("--exclude-used", default="", help="videos whose spans are left out (ASSET_LEDGER)")
    b.add_argument("--own", help="this video's own clips folder: its clips are not past videos")
    b.add_argument("--split", choices=["sentence", "clause", "beat"], default="sentence")
    b.add_argument("--no-embed", action="store_true", help="keywords only (no model loads)")
    b.add_argument("--no-used", action="store_true", help="skip the past-video fingerprints on the scene")
    c = sub.add_parser("cut")
    c.add_argument("picks")
    c.add_argument("--prefix", required=True)
    c.add_argument("--manifest", required=True)
    c.add_argument("--run", help="cut the clips into this folder too")
    a = ap.parse_args()
    boards(a) if a.cmd == "boards" else cut(a)


if __name__ == "__main__":
    main()
