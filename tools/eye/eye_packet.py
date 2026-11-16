"""The reviewer's eye, step 1: the review packet (no model). Everything a reviewer needs to watch a finished video the way the creator
does, from the MP4 itself: one decode finds every cut and keeps the first frame, the frame 3 frames in, the middle and the last frame of
each shot; a shot sheet lays those four out per shot next to the words said over it and what is on screen (from the asset ledger when
the delivered file is the ledger's); a contact sheet per 30 s (a Short: per 15 s) shows the flow; the transcript has its times;
loudness is measured per shot; the script's beats and, in production, the QA gate's report go in beside them. packet.md is the index.

  EDIT tools/eye/eye_packet.py <video.mp4> [--out DIR] [--srt FILE | --words FILE]
      [--script FILE | git:REV:PATH] [--beats "## Beats v2"] [--ledger ID] [--qa FILE] [--title TEXT]
  e.g. EDIT tools/eye/eye_packet.py VIDEOS/<video>/export/<file>_v1.mp4 --ledger <video> --script videos/<video>/script.md
           --qa videos/<video>/QA_v1.md
       (a blind test of the reviewer: --script git:<rev>:videos/<video>/script.md reads the script as it was before the creator's review)

--out defaults to VIDEOS/<video folder>/eye/<file stem>/. --srt defaults to the .srt beside the MP4 (phrase times; words are spread
over each phrase by length). --ledger takes the video's entry in kb/ASSET_LEDGER.json only when its delivered file is this MP4
(another version's shot list would mislead). ~100 frames a second with the GPU decoding (a 9-minute 4K film in ~6 min); without a
CUDA GPU (a Mac) the CPU decodes, slower. --reuse rebuilds the sheets and lists from an earlier run's decode.json and frames (seconds).
For a closer look at one moment the reviewer runs eye_frame.py."""
import argparse
import json
import re
import subprocess
import sys
import textwrap
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "footage"))
from paths import FFMPEG, FFPROBE, KB, PY_EDIT, REPO  # noqa: E402
from sheetfont import font as sheet_font  # noqa: E402

LEDGER = KB / "ASSET_LEDGER.json"
INK, DIM, LAYER, BG = (235, 235, 235), (150, 150, 150), (120, 200, 255), (24, 24, 28)


def font(size, bold=False):
    return sheet_font(size, bold)


def mmss(t, dec=1):
    m, s = divmod(max(t, 0.0), 60)
    return f"{int(m)}:{s:0{3 + dec}.{dec}f}" if dec else f"{int(m)}:{int(s):02d}"


def probe(video):
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", str(video)],
                         capture_output=True, text=True).stdout
    j = json.loads(out)
    st = j["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return int(st["width"]), int(st["height"]), float(num) / float(den), float(j["format"]["duration"]), int(st.get("nb_frames", 0) or 0)


# ------------------------------------------------------------------------------------------------------------------------- words
def read_srt(path):
    phrases = []
    for block in re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8-sig").strip()):
        lines = block.strip().splitlines()
        tl = next((ln for ln in lines if "-->" in ln), None)
        if not tl:
            continue
        a, b = [x.strip() for x in tl.split("-->")]
        to_s = lambda x: int(x[:2]) * 3600 + int(x[3:5]) * 60 + float(x[6:].replace(",", "."))
        text = " ".join(ln.strip() for ln in lines[lines.index(tl) + 1:]).strip()
        if text:
            phrases.append((to_s(a), to_s(b), text))
    return phrases


def spread_words(phrases):
    """Word times from phrase times: each word gets a share of its phrase by its length."""
    words = []
    for t0, t1, text in phrases:
        toks = text.split()
        weights = [len(w) + 1 for w in toks]
        tot, acc = sum(weights), 0
        for w, k in zip(toks, weights):
            a = t0 + (t1 - t0) * acc / tot
            acc += k
            words.append({"w": w, "start": round(a, 3), "end": round(t0 + (t1 - t0) * acc / tot, 3)})
    return words


def read_words(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data = data.get("words", data) if isinstance(data, dict) else data
    return [{"w": d.get("w") or d.get("word") or d.get("text", ""), "start": float(d["start"]), "end": float(d["end"])} for d in data]


# ------------------------------------------------------------------------------------------------------------------------- script
def read_script(spec, beats):
    if spec.startswith("git:"):
        _, rev, path = spec.split(":", 2)
        text = subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{path}"], capture_output=True).stdout.decode("utf-8")
    else:
        text = Path(spec).read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if (ln.strip() == beats.strip() if beats else ln.startswith("## Beats"))), None)
    if start is None:
        return text
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


# ------------------------------------------------------------------------------------------------------------------------- ledger
def read_ledger(vid, video):
    led = json.loads(LEDGER.read_text(encoding="utf-8"))["videos"].get(vid)
    if not led:
        sys.exit(f"no ledger entry {vid}")
    if Path(led["delivered"]).resolve() != Path(video).resolve():
        print(f"  ledger {vid} is for {led['delivered']}, not this file: shot list from the picture only")
        return None
    uses = []
    for kind in ("clips", "stills", "pages"):
        for item in led[kind]:
            name = Path(item["file"]).name
            extra = ""
            if kind == "pages":
                q = "; ".join(item.get("quotes", [])[:2])
                extra = (item.get("outlet") or "") + (f' "{q}"' if q else "")
            for u in item["uses"]:
                span = f" src {u['from']:.1f}-{u['to']:.1f}s" if "from" in u else ""
                rate = f" x{u['rate']}" if u.get("rate") not in (None, 1) else ""
                uses.append({"at": u["at"], "dur": u["dur"], "shot": u.get("shot", u["at"]), "kind": kind[:-1],
                             "text": f"{kind[:-1]} {name}{span}{rate} [{u.get('via', '')}]" + (f" {extra}" if extra else "")})
    for comp in led["components"]:
        for u in comp["uses"]:
            uses.append({"at": u["at"], "dur": u["dur"], "shot": u.get("shot", u["at"]), "kind": "graphic",
                         "text": f"graphic {comp['name']} ({comp.get('module', '')})"})
    return sorted(uses, key=lambda u: (u["at"], u["kind"]))


# ------------------------------------------------------------------------------------------------------------------------- decode
def decode(video, w, h, fps, total, sample_step, known, outdir):
    """One pass: cut detection on a small grey copy, samples every sample_step frames, the exact frames around every cut."""
    (outdir / "frames").mkdir(parents=True, exist_ok=True)
    tiny = (96, 54) if w >= h else (54, 96)
    size = w * h * 3
    # the GPU decodes and scales when there is a CUDA one; anywhere else (a Mac, a codec it can't take) the CPU does
    vf = f"scale_cuda={w}:{h},hwdownload,format=nv12,format=bgr24"
    cmd = [FFMPEG, "-v", "error", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda", "-i", str(video), "-vf", vf,
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w * h * 3 * 8)
    first = p.stdout.read(size)
    if len(first) < size:
        p.kill()
        cmd = [FFMPEG, "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h},format=bgr24", "-f", "rawvideo", "-"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=w * h * 3 * 8)
        first = p.stdout.read(size)
    hist = deque(maxlen=3)          # (n, frame) of the last three frames
    diffs, recent = [], deque(maxlen=10)
    pending, saved, detected = set(), set(), []
    prev_g = None
    known = set(known)

    def save(n, frame, tag="c"):
        if (tag, n) in saved:
            return
        cv2.imwrite(str(outdir / "frames" / f"{tag}_{n:06d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 86])
        saved.add((tag, n))

    n = -1
    while True:
        buf, first = (first, None) if first is not None else (p.stdout.read(size), None)
        if len(buf) < size:
            break
        n += 1
        frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        g = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), tiny, interpolation=cv2.INTER_AREA).astype(np.int16)
        d = float(np.abs(g - prev_g).mean()) if prev_g is not None else 0.0
        prev_g = g
        diffs.append(d)
        hist.append((n, frame))
        # a cut at n-1 is decided now: a jump well over the recent motion and over the next frame's change
        if n >= 2:
            dc = diffs[n - 1]
            base = float(np.median(recent)) if recent else 0.0
            if dc >= 14 and dc >= 3 * base + 4 and dc >= 1.8 * d:
                detected.append(n - 1)
                save(n - 2, hist[0][1])
                save(n - 1, hist[1][1])
                pending.add(n + 2)
            recent.append(dc)
        if n in known:
            if len(hist) >= 2:
                save(n - 1, hist[-2][1])
            save(n, frame)
            pending.add(n + 3)
        if n in pending:
            save(n, frame)
            pending.discard(n)
        if n % sample_step == 0:
            save(n, frame, "s")
        if total and n % 3000 == 0:
            print(f"  frame {n}/{total}", flush=True)
    if hist:
        save(hist[-1][0], hist[-1][1])
    p.wait()
    return n + 1, diffs, detected


# ------------------------------------------------------------------------------------------------------------------------- loudness
def loudness_start(video):
    return subprocess.Popen([FFMPEG, "-nostats", "-hide_banner", "-i", str(video), "-map", "0:a:0", "-af", "ebur128=peak=true",
                             "-f", "null", "-"], stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, errors="replace")


def loudness_read(proc):
    err = proc.communicate()[1]
    pts = [(float(m.group(1)), float(m.group(2)), float(m.group(3))) for m in
           re.finditer(r"t:\s*([\d.]+)\s+TARGET:\S+ LUFS\s+M:\s*(-?[\d.]+|-inf)\s+S:\s*(-?[\d.]+|-inf)", err.replace("-inf", "-120"))]
    i_m = re.findall(r"I:\s*(-?[\d.]+) LUFS", err)
    pk = re.findall(r"Peak:\s*(-?[\d.]+) dBFS", err)
    return pts, (float(i_m[-1]) if i_m else None), (float(pk[-1]) if pk else None)


# ------------------------------------------------------------------------------------------------------------------------- sheets
def fit(img, box):
    im = Image.open(img).convert("RGB") if isinstance(img, (str, Path)) else img
    im.thumbnail(box)
    return im


def shot_sheets(shots, outdir, vertical, fmt_title):
    tw, th = (144, 256) if vertical else (288, 162)
    per = 6 if vertical else 9
    text_w = 560 if vertical else 470
    row_h = th + 10
    W = 4 * (tw + 4) + 8 + text_w
    f_head, f_txt, f_small = font(17, True), font(15), font(13)
    sheets = []
    for k in range(0, len(shots), per):
        group = shots[k:k + per]
        H = 34 + len(group) * row_h
        sheet = Image.new("RGB", (W, H), BG)
        dr = ImageDraw.Draw(sheet)
        dr.text((8, 8), f"{fmt_title}  shots #{group[0]['i']}-#{group[-1]['i']}  "
                        f"{mmss(group[0]['t0'])}-{mmss(group[-1]['t1'])}   (each row: first | +3 frames | middle | last)",
                fill=INK, font=f_head)
        for r, s in enumerate(group):
            y = 34 + r * row_h
            for c, key in enumerate(("first", "plus3", "mid", "last")):
                im = fit(outdir / s["frames"][key], (tw, th))
                sheet.paste(im, (4 + c * (tw + 4), y))
            x = 4 * (tw + 4) + 8
            burst = f"  ({s['cuts_inside']} quick cuts inside)" if s["cuts_inside"] else ""
            dr.text((x, y), f"#{s['i']}  {mmss(s['t0'], 2)}-{mmss(s['t1'], 2)}  {s['dur']:.2f} s{burst}", fill=INK, font=f_head)
            yy = y + 22
            words = f'"{s["words"]}"' if s["words"] else "(no narration)"
            for ln in textwrap.wrap(words, 62 if vertical else 52)[:6 if vertical else 4]:
                dr.text((x, yy), ln, fill=INK, font=f_txt)
                yy += 18
            for ln in [ln for lay in s["layers"][:4] for ln in textwrap.wrap(lay, 70 if vertical else 60)[:1]]:
                if yy > y + th - 14:
                    break
                dr.text((x, yy), ln, fill=LAYER, font=f_small)
                yy += 15
        name = f"shots_{len(sheets) + 1:02d}.jpg"
        sheet.save(outdir / "sheets" / name, quality=88)
        sheets.append((name, group[0]["i"], group[-1]["i"], group[0]["t0"], group[-1]["t1"]))
    return sheets


def contact_sheets(samples, fps, duration, outdir, vertical, step_s, span_s, cols):
    tw, th = (144, 256) if vertical else (256, 144)
    f_lab = font(14, True)
    out = []
    t = 0.0
    while t < duration - 0.05:
        times = [x for x in np.arange(t, min(t + span_s, duration), step_s)]
        rows = (len(times) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + 4) + 4, 30 + rows * (th + 4)), BG)
        dr = ImageDraw.Draw(sheet)
        dr.text((6, 6), f"contact sheet {mmss(t, 0)}-{mmss(min(t + span_s, duration), 0)} (one frame every {step_s:g} s)", fill=INK,
                font=f_lab)
        for k, tt in enumerate(times):
            n = int(round(tt * fps))
            near = min(samples, key=lambda s: abs(s - n))
            im = fit(outdir / "frames" / f"s_{near:06d}.jpg", (tw, th))
            x, y = 4 + (k % cols) * (tw + 4), 30 + (k // cols) * (th + 4)
            sheet.paste(im, (x, y))
            dr.rectangle((x, y, x + 52, y + 18), fill=(0, 0, 0))
            dr.text((x + 3, y + 1), mmss(tt, 0), fill=(255, 230, 90), font=f_lab)
        name = f"contact_{len(out) + 1:02d}.jpg"
        sheet.save(outdir / "sheets" / name, quality=86)
        out.append((name, t, min(t + span_s, duration)))
        t += span_s
    return out


# ------------------------------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out")
    ap.add_argument("--srt")
    ap.add_argument("--words")
    ap.add_argument("--script")
    ap.add_argument("--beats", default="")
    ap.add_argument("--ledger")
    ap.add_argument("--qa")
    ap.add_argument("--title", default="")
    ap.add_argument("--reuse", action="store_true", help="reuse decode.json and the frames of an earlier run (no decode)")
    a = ap.parse_args()

    video = Path(a.video)
    out = Path(a.out) if a.out else video.parent.parent / "eye" / video.stem
    (out / "sheets").mkdir(parents=True, exist_ok=True)
    W0, H0, fps, duration, nb = probe(video)
    vertical = H0 > W0
    w, h = (540, 960) if vertical else (960, 540)
    sample_step = int(round(fps / (10 if vertical else 5)))
    print(f"{video.name}: {W0}x{H0} {fps:g} fps {duration:.2f} s -> packet {out}")

    uses = read_ledger(a.ledger, video) if a.ledger else None
    known = sorted({int(round(u["shot"] * fps)) for u in uses} | {int(round(u["at"] * fps)) for u in uses
                                                                   if u["kind"] != "graphic"}) if uses else []
    cache = out / "decode.json"
    if a.reuse and cache.exists():
        dc = json.loads(cache.read_text(encoding="utf-8"))
        n_frames, detected, pts, integ, peak = dc["n_frames"], dc["detected"], dc["loud"], dc["integrated"], dc["peak"]
        print(f"  decode reused from {cache}")
    else:
        lp = loudness_start(video)
        n_frames, diffs, detected = decode(video, w, h, fps, nb, sample_step, known, out)
        pts, integ, peak = loudness_read(lp)
        cache.write_text(json.dumps({"n_frames": n_frames, "detected": detected, "known": known, "integrated": integ, "peak": peak,
                                     "loud": pts}), encoding="utf-8")

    # shots: the composition's starts, plus every hard cut the picture shows away from them; a stretch shorter than 0.25 s joins the
    # next shot (a flicker, a flash or a burst of quick cuts shows as one row that says how many cuts it holds)
    bounds = set(known)
    for c in detected:
        if not any(abs(c - k) <= 6 for k in known):
            bounds.add(c)
    bounds = sorted(b for b in bounds | {0} if 0 <= b < n_frames)
    least = int(round(0.25 * fps))
    spans, start, inside = [], bounds[0], 0
    for b in bounds[1:]:
        if b - start < least:
            inside += 1
            continue
        spans.append((start, b, inside))
        start, inside = b, 0
    if spans and n_frames - start < least:
        s0, _, k = spans.pop()
        spans.append((s0, n_frames, k + inside + 1))
    else:
        spans.append((start, n_frames, inside))
    samples = sorted(int(p.stem[2:]) for p in (out / "frames").glob("s_*.jpg"))
    have = {int(p.stem[2:]) for p in (out / "frames").glob("c_*.jpg")}

    def cframe(n):
        if n in have:
            return f"frames/c_{n:06d}.jpg"
        near = min(samples, key=lambda s: abs(s - n))
        return f"frames/s_{near:06d}.jpg"

    if a.words:
        words = read_words(a.words)
    else:
        srt = Path(a.srt) if a.srt else video.with_suffix(".srt")
        words = spread_words(read_srt(srt)) if srt.exists() else []
    phrases = read_srt(Path(a.srt) if a.srt else video.with_suffix(".srt")) if (a.srt or video.with_suffix(".srt").exists()) else []

    shots = []
    for i, (b, e, inside) in enumerate(spans):
        t0, t1 = b / fps, e / fps
        mid_n = (b + e) // 2
        mid = min(samples, key=lambda s: abs(s - mid_n)) if e - b > sample_step else b
        said = " ".join(wd["w"] for wd in words if t0 <= (wd["start"] + wd["end"]) / 2 < t1)
        lays = []
        if uses:
            for u in uses:
                if u["at"] < t1 - 0.02 and u["at"] + u["dur"] > t0 + 0.02 and u["text"] not in lays:
                    lays.append(u["text"])
        lp_pts = [p for p in pts if t0 <= p[0] < t1]
        m_max = max((p[1] for p in lp_pts), default=None)
        s_mean = float(np.mean([p[2] for p in lp_pts])) if lp_pts else None
        shots.append({"i": i + 1, "f0": b, "f1": e, "t0": round(t0, 3), "t1": round(t1, 3), "dur": round(t1 - t0, 3),
                      "frames": {"first": cframe(b), "plus3": cframe(b + 3) if b + 3 < e else cframe(e - 1),
                                 "mid": f"frames/s_{mid:06d}.jpg" if e - b > sample_step else cframe(b), "last": cframe(e - 1)},
                      "cuts_inside": inside, "words": said, "layers": lays, "loud_max_M": m_max, "loud_mean_S": None if s_mean is None else round(s_mean, 1)})

    title = a.title or video.stem
    sheets = shot_sheets(shots, out, vertical, title)
    contacts = contact_sheets(samples, fps, duration, out, vertical, 0.5 if vertical else 1.0, 15.0 if vertical else 30.0,
                              10 if vertical else 6)

    (out / "shots.json").write_text(json.dumps(shots, indent=1), encoding="utf-8")
    with (out / "shots.md").open("w", encoding="utf-8") as f:
        f.write(f"# Shots of {title} ({len(shots)} shots; time, length, the words said over it, what is on screen, loudness)\n\n")
        for s in shots:
            loud = f"  [loudness: max momentary {s['loud_max_M']:.1f}, mean short-term {s['loud_mean_S']}]" if s["loud_max_M"] is not None else ""
            burst = f", {s['cuts_inside']} quick cuts inside" if s["cuts_inside"] else ""
            f.write(f"#{s['i']} {mmss(s['t0'], 2)}-{mmss(s['t1'], 2)} ({s['dur']:.2f} s{burst}){loud}\n")
            f.write(f"  said: {s['words'] or '(nothing)'}\n")
            for lay in s["layers"]:
                f.write(f"  on screen: {lay}\n")
    with (out / "transcript.md").open("w", encoding="utf-8") as f:
        f.write(f"# Transcript of {title} (phrase times from the subtitles)\n\n")
        for t0, t1, text in phrases:
            f.write(f"[{mmss(t0)}-{mmss(t1)}] {text}\n")
    if a.script:
        (out / "script.md").write_text(read_script(a.script, a.beats), encoding="utf-8")
    if a.qa:
        (out / "qa.md").write_text(Path(a.qa).read_text(encoding="utf-8"), encoding="utf-8")

    # what stands out in the numbers (for the reviewer to look at, not verdicts)
    hold = 2.6 if vertical else 8.0
    long_shots = [s for s in shots if s["dur"] > hold]
    loud = [s for s in shots if integ is not None and s["loud_max_M"] is not None and s["loud_max_M"] > integ + 7]
    with (out / "packet.md").open("w", encoding="utf-8") as f:
        f.write(f"# Review packet: {title}\n\n")
        f.write(f"- file: {video} ({W0}x{H0}, {fps:g} fps, {mmss(duration)}; {'Short (9:16)' if vertical else 'long form (16:9)'})\n")
        f.write(f"- loudness: {integ} LUFS integrated, true peak {peak} dBFS\n")
        bursts = [x for x in shots if x["cuts_inside"]]
        f.write(f"- {len(shots)} shots ({len(shots) / duration * 60:.1f} a minute, counting a burst as one); stretches under 0.25 s joined "
                f"the next shot: " + (", ".join(f"#{x['i']} {mmss(x['t0'], 2)} ({x['cuts_inside']} cuts)" for x in bursts[:40]) or "none") + "\n")
        f.write(f"- shot list from: {'the composition (asset ledger ' + a.ledger + ') plus the cuts the picture shows' if uses else 'the cuts the picture shows'}\n\n")
        f.write("## Files\n\n- `shots.md`: every shot with its time, the words over it, what is on screen and its loudness\n"
                "- `sheets/shots_NN.jpg`: per shot its first frame, the frame 3 frames in, the middle and the last, beside its words\n"
                f"- `sheets/contact_NN.jpg`: one frame every {0.5 if vertical else 1.0:g} s, {15 if vertical else 30} s a sheet: the flow\n"
                "- `transcript.md`: the narration with times\n" + ("- `script.md`: the script's beats\n" if a.script else "") +
                ("- `qa.md`: the deterministic checks' report (what the tools already caught)\n" if a.qa else "") +
                f"- `frames/`: every frame on the sheets at {w}x{h} (c_<frame>.jpg exact cut frames, s_<frame>.jpg samples; frame = "
                f"seconds x {fps:g}); a full-size frame at any time: `{Path(PY_EDIT).as_posix()} "
                f"{(Path(__file__).resolve().parent / 'eye_frame.py').as_posix()} \"{video}\" <seconds> --out <dir>`\n\n")
        f.write("## Shot sheets\n\n| sheet | shots | time |\n|---|---|---|\n")
        for name, i0, i1, t0, t1 in sheets:
            f.write(f"| sheets/{name} | #{i0}-#{i1} | {mmss(t0)}-{mmss(t1)} |\n")
        f.write("\n## Contact sheets\n\n" + "".join(f"- sheets/{n}: {mmss(t0, 0)}-{mmss(t1, 0)}\n" for n, t0, t1 in contacts))
        f.write(f"\n## Numbers to look at (measurements, not verdicts)\n\n- shots longer than {hold:g} s: " +
                (", ".join(f"#{s['i']} {mmss(s['t0'])} ({s['dur']:.1f} s)" for s in long_shots) or "none") + "\n")
        f.write("- shots with a moment 7+ LU over the film's loudness: " +
                (", ".join(f"#{s['i']} {mmss(s['t0'])} ({s['loud_max_M']:.1f})" for s in loud) or "none") + "\n")
    print(f"done: {len(shots)} shots, {len(sheets)} shot sheets, {len(contacts)} contact sheets, "
          f"loudness {integ} LUFS / {peak} dBFS -> {out / 'packet.md'}")


if __name__ == "__main__":
    main()
