"""One QA pass over any finished render, long form or Short, from the MP4 alone. Every check is a fault that keeps coming back in
reviews, turned into a measurement, so it is caught before the creator watches:

  picture  flash shots (a shot of a few frames between two others: no flash frames), freezes (the picture standing still), holds
           (one picture on screen past its point; Shorts: a change every 2-3 s), repeats (the same picture twice: never repeat a clip),
           black bars and black frames (no letterbox), soft shots (low-res or upscaled sources: the sharpest source wins), Shorts'
           frame 0 (the flash open)
  sound    integrated loudness and true peak (-14 LUFS, -1 dBTP), the loudest 3 s (a jump that hurts the ears), absolute silence
           (a stretch of dead air always reads as a fault)
  voice    (with --words, the narration's word times) gaps in the talking (Shorts talk constantly), the first word (Shorts: frame 0),
           the tail after the last word (the video ends right after it)

It flags; every flag gets a look on the sheet it writes (frames around each flagged moment), and a deliberate hold can be allowed with
--allow a-b,c-d (seconds).

  EDIT tools/qa/qa_render.py <video.mp4> [--format long|short] [--words w.json] [--voice narration.wav]
      [--out DIR] [--allow 12.0-15.5,...] [--from S --to S]
--format defaults from the frame shape (vertical = short). --words: [{"w"|"word", "start", "end"}] in video seconds.
Writes <out>/qa.md, <out>/flags_NN.jpg; exits 1 when any FAIL."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE  # noqa: E402

LIMITS = {
    # seconds unless noted
    "long": dict(flash=0.10, flash_warn=0.25, burst=0.5, freeze=2.0, hold=6.0, gap=1.6, first_word=None, tail=3.0,
                 lufs=(-15.0, -13.0), cuts=(18, 32)),
    "short": dict(flash=0.10, flash_warn=0.20, burst=0.5, freeze=0.8, hold=2.6, gap=0.25, first_word=0.15, tail=0.6,
                  lufs=(-16.0, -12.0), cuts=(28, 60)),
}


def probe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return int(v["width"]), int(v["height"]), float(num) / float(den), float(d["format"]["duration"]), \
        any(s["codec_type"] == "audio" for s in d["streams"])


def frames(path, w, h, fps, a=None, b=None):
    """Yield small RGB frames (uint8 h x w x 3) at `fps`."""
    cmd = [FFMPEG, "-v", "error"]
    if a is not None:
        cmd += ["-ss", str(a)]
    cmd += ["-i", str(path)]
    if b is not None:
        cmd += ["-t", str(b - (a or 0))]
    cmd += ["-vf", f"fps={fps},scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


def frame_at(path, tt, w, h):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, tt):.4f}", "-i", str(path), "-frames:v", "1", "-vf",
                          f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) if len(raw) == w * h * 3 else None


def runs(mask, min_len):
    """[start, end) index runs where mask is True, at least min_len long."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def dhash(img):
    """64-bit difference hash of a grey frame."""
    from PIL import Image
    small = np.asarray(Image.fromarray(img).resize((9, 8), Image.BILINEAR), dtype=np.int16)
    return np.packbits((small[:, 1:] > small[:, :-1]).flatten())


def sharpness(img):
    lap = img[1:-1, 1:-1].astype(np.float32) * 4 - img[:-2, 1:-1] - img[2:, 1:-1] - img[1:-1, :-2] - img[1:-1, 2:]
    return float(lap.var())


def loudness(path):
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true:framelog=verbose",
                        "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr
    integ = re.findall(r"I:\s+(-?[\d.]+) LUFS", txt)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", txt)
    st = [float(x) for x in re.findall(r"\bS:\s*(-?[\d.]+)", txt)]
    return (float(integ[-1]) if integ else None, float(peak[-1]) if peak else None, max(st) if st else None)


def silences(path, dur):
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "silencedetect=n=-50dB:d=0.05",
                        "-f", "null", "-"], capture_output=True, text=True)
    s = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    e = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]
    out = []
    for i, a in enumerate(s):
        b = e[i] if i < len(e) else dur
        if a > 0.5 and b < dur - 0.5:
            out.append((a, b))
    return out


def sheet(path, times, out, vertical):
    """Frames around each flagged time (t-0.25, t, t+0.25, t+0.5), one row per flag, labelled."""
    from PIL import Image, ImageDraw, ImageFont
    tw, th = (180, 320) if vertical else (320, 180)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    rows = []
    for t, label in times:
        row = Image.new("RGB", (4 * tw + 260, th), (0, 0, 0))
        d = ImageDraw.Draw(row)
        d.text((6, 6), label[:34], fill=(255, 220, 0), font=font)
        d.text((6, 26), label[34:68], fill=(255, 220, 0), font=font)
        for k, dt in enumerate((-0.25, 0.0, 0.25, 0.5)):
            tt = max(0.0, t + dt)
            raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{tt:.3f}", "-i", str(path), "-frames:v", "1", "-vf",
                                  f"scale={tw}:{th}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            if len(raw) == tw * th * 3:
                im = Image.frombytes("RGB", (tw, th), raw)
                ImageDraw.Draw(im).text((4, 4), f"{tt:.2f}s", fill=(255, 255, 255), font=font)
                row.paste(im, (260 + k * tw, 0))
        rows.append(row)
    files = []
    for k in range(0, len(rows), 12):
        part = rows[k:k + 12]
        img = Image.new("RGB", (part[0].width, sum(r.height for r in part) + 2 * len(part)), (40, 40, 40))
        y = 0
        for r in part:
            img.paste(r, (0, y))
            y += r.height + 2
        f = out / f"flags_{k // 12 + 1:02d}.jpg"
        img.save(f, quality=85)
        files.append(f)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--format", choices=["long", "short"])
    ap.add_argument("--words")
    ap.add_argument("--voice")   # the narration wav: a word gap counts only where the voice itself is silent (speech-to-text word ends leave false gaps)
    ap.add_argument("--out")
    ap.add_argument("--allow", default="")
    ap.add_argument("--from", dest="a", type=float)
    ap.add_argument("--to", dest="b", type=float)
    args = ap.parse_args()
    path = Path(args.video)
    W, H, src_fps, dur, has_audio = probe(path)
    vertical = H > W
    fmt = args.format or ("short" if vertical else "long")
    L = LIMITS[fmt]
    out = Path(args.out) if args.out else path.parent / f"qa_{path.stem}"
    out.mkdir(parents=True, exist_ok=True)
    allow = [tuple(float(x) for x in s.split("-")) for s in args.allow.split(",") if s]
    allowed = lambda a, b: any(a >= x - 0.05 and b <= y + 0.05 for x, y in allow)
    a0 = args.a or 0.0

    # 1. the picture, at 30 fps (60 for Shorts), small and grey
    fps = 60.0 if fmt == "short" and src_fps >= 50 else min(30.0, src_fps)
    sw, sh = (90, 160) if vertical else (160, 90)
    import cv2
    diffs, content, lum, top, bot, hashes = [], [], [], [], [], []
    prev = prev_hsv = None
    for i, fr in enumerate(frames(path, sw, sh, fps, args.a, args.b)):
        grey = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(fr, cv2.COLOR_RGB2HSV).astype(np.int16)
        g16 = grey.astype(np.int16)
        diffs.append(0.0 if prev is None else float(np.abs(g16 - prev).mean()))
        # ContentDetector's score: mean |dH|, |dS|, |dV| (hue doubled to 0-360 like OpenCV's 0-180 scale x2), averaged
        if prev_hsv is None:
            content.append(0.0)
        else:
            dh = np.abs(hsv[..., 0] - prev_hsv[..., 0])
            dh = np.minimum(dh, 180 - dh) * 2
            content.append(float((dh.mean() + np.abs(hsv[..., 1] - prev_hsv[..., 1]).mean() + np.abs(hsv[..., 2] - prev_hsv[..., 2]).mean()) / 3))
        lum.append(float(grey.mean()))
        band = max(2, sh // 12) if not vertical else max(2, sh // 14)
        top.append(float(grey[:band].mean()))
        bot.append(float(grey[-band:].mean()))
        prev, prev_hsv = g16, hsv
        hashes.append(dhash(grey))
    n = len(diffs)
    t = lambda i: a0 + i / fps
    diffs = np.array(diffs)
    content = np.array(content)
    lum = np.array(lum)
    flags = []          # (level, t, text)

    # cuts: the HSV content score jumps over 27 (PySceneDetect's default) and well over the local motion around it
    med = np.array([np.median(content[max(0, i - 15):i + 15]) for i in range(n)])
    cut = (content > np.maximum(27.0, 3.0 * med + 8.0))
    cut[0] = False
    cut_idx = list(np.nonzero(cut)[0])
    bounds = [0] + cut_idx + [n]
    shots = [(bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1) if bounds[k + 1] > bounds[k]]
    durs = np.array([(b - a) / fps for a, b in shots])
    minutes = (n / fps) / 60
    cpm = len(cut_idx) / minutes if minutes else 0
    lo, hi = L["cuts"]
    flags.append(("INFO" if lo <= cpm <= hi else "WARN", a0, f"{len(cut_idx)} cuts = {cpm:.1f} a minute (references {lo}-{hi}); "
                  f"median shot {np.median(durs):.2f} s"))

    # flash shots: a few frames between two cuts, not inside a deliberate burst of short shots, not a dissolve (a blend of its two
    # neighbours: a crossfade reads as two cuts 33 ms apart), not a white flash (a designed transition)
    def blended(a, b):
        tm = t((a + b) / 2)
        x, p0, p1 = frame_at(path, tm, sw, sh), frame_at(path, t(a) - 1.5 / fps, sw, sh), frame_at(path, t(b) + 0.5 / fps, sw, sh)
        if x is None or p0 is None or p1 is None:
            return False
        d = (p1 - p0).reshape(-1)
        if np.abs(d).mean() < 1:
            return True
        al = float(np.clip(np.dot((x - p0).reshape(-1), d) / np.dot(d, d), 0, 1))
        err = np.abs(x - (p0 + al * (p1 - p0))).mean()
        return err < 0.35 * np.abs(d).mean()
    for k, (a, b) in enumerate(shots):
        d = (b - a) / fps
        if k == 0 or k == len(shots) - 1 or d >= L["flash_warn"]:
            continue
        near = [shots[j] for j in (k - 1, k + 1)]
        if all((y - x) / fps < L["burst"] for x, y in near):
            continue
        if float(np.mean(lum[a:b])) > 200:
            flags.append(("INFO", t(a), f"white flash {d * 1000:.0f} ms (a transition)"))
            continue
        if blended(a, b):
            continue
        # a true flash shows a DIFFERENT picture from both neighbours; fast motion or an animated graphic stays close to one of them
        ham = lambda x, y: int(np.unpackbits(np.bitwise_xor(hashes[x], hashes[y])).sum())
        mid = (a + b) // 2
        if a > 0 and b < n and min(ham(mid, a - 1), ham(mid, b)) < 14:
            continue
        if d < L["flash"]:
            flags.append(("FAIL", t(a), f"flash shot: {d * 1000:.0f} ms between two longer shots"))
        else:
            flags.append(("WARN", t(a), f"very short shot: {d * 1000:.0f} ms (meant?)"))

    # freezes: the picture identical frame to frame (a frozen clip or a held still with no drift)
    still = diffs < 0.35
    for a, b in runs(still, int(L["freeze"] * fps)):
        if not allowed(t(a), t(b)):
            flags.append(("FAIL" if fmt == "short" or (b - a) / fps > 2 * L["freeze"] else "WARN", t(a),
                          f"frozen picture {(b - a) / fps:.1f} s"))
    # holds: no cut or big change for longer than the format allows (moving footage counts as alive in long form)
    for k, (a, b) in enumerate(shots):
        d = (b - a) / fps
        if d <= L["hold"] or allowed(t(a), t(b)):
            continue
        motion = float(np.median(diffs[a + 1:b])) if b - a > 2 else 0.0
        if fmt == "short":
            continue                      # Shorts: judged below on changes (cuts, pop-ins, punch-ins), not on cuts alone
        elif motion < 1.2:
            flags.append(("WARN", t(a), f"near-static shot held {d:.1f} s (motion {motion:.2f})"))

    # Shorts: a change at least every ~2.6 s (a cut, a picture popping in, a punch-in)
    if fmt == "short":
        medd = np.array([np.median(diffs[max(0, i - 15):i + 15]) for i in range(n)])
        change = (content > np.maximum(14.0, 2.5 * med + 5.0)) | (diffs > np.maximum(10.0, 3.0 * medd + 5.0))
        ch = [0] + list(np.nonzero(change)[0]) + [n]
        for x, y in zip(ch, ch[1:]):
            if (y - x) / fps > L["hold"] and not allowed(t(x), t(y)) and t(y) < a0 + n / fps - 0.5:
                flags.append(("FAIL", t(x), f"no change of picture for {(y - x) / fps:.1f} s (Shorts: a new picture every 2-3 s)"))

    # repeats: two shots far apart that show the same picture
    hs = []
    for a, b in shots:
        if (b - a) / fps >= 0.4:
            hs.append((a, hashes[(a + b) // 2]))
    for x in range(len(hs)):
        for y in range(x + 1, len(hs)):
            if (hs[y][0] - hs[x][0]) / fps < 8:
                continue
            ham = int(np.unpackbits(np.bitwise_xor(hs[x][1], hs[y][1])).sum())
            if ham <= 5:
                flags.append(("WARN", t(hs[y][0]), f"repeat? looks like the shot at {t(hs[x][0]):.1f}s (hash {ham}/64)"))

    # black bars (letterbox / pillarbox are checked on the top and bottom bands) and black frames
    top, bot = np.array(top), np.array(bot)
    bars = (top < 10) & (bot < 10) & (lum > 35)
    for a, b in runs(bars, int(0.5 * fps)):
        flags.append(("WARN", t(a), f"black bars top and bottom for {(b - a) / fps:.1f} s (a letterboxed source between full frames?)"))
    black = lum < 6
    for a, b in runs(black, 2):
        if t(a) > a0 + 0.6 and t(b) < a0 + n / fps - 1.5:
            flags.append(("WARN", t(a), f"black frames {(b - a) / fps:.2f} s mid-video (meant?)"))

    # soft shots: sharpness far under the video's median, read on a 640-px frame of each longer shot
    sharp = []
    for a, b in shots:
        if (b - a) / fps < 0.8:
            continue
        mid = t((a + b) // 2)
        raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{mid:.3f}", "-i", str(path), "-frames:v", "1", "-vf",
                              f"scale={640 if not vertical else 360}:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        ww, hh = (640, int(640 * H / W) // 2 * 2) if not vertical else (360, int(360 * H / W) // 2 * 2)
        if len(raw) >= ww * hh:
            sharp.append((mid, sharpness(np.frombuffer(raw[:ww * hh], np.uint8).reshape(hh, ww))))
    if sharp:
        medv = float(np.median([s for _, s in sharp]))
        for mid, s in sharp:
            if s < 0.25 * medv:
                flags.append(("WARN", mid, f"soft shot: sharpness {s:.0f} vs median {medv:.0f} (low-res source, blur or a fade?)"))

    # Shorts: frame 0 opens on the flash
    if fmt == "short" and a0 == 0:
        first = lum[:max(2, int(0.2 * fps))]
        if first.max() < 170:
            flags.append(("FAIL", 0.0, f"no flash open: brightest of the first 0.2 s is {first.max():.0f}/255"))

    # 2. the sound
    if has_audio and args.a is None and args.b is None:
        integ, tp, st_max = loudness(path)
        lo_l, hi_l = L["lufs"]
        if integ is not None:
            flags.append(("INFO" if lo_l <= integ <= hi_l else "FAIL", 0.0, f"integrated {integ:.1f} LUFS (target {lo_l} to {hi_l})"))
        if tp is not None:
            flags.append(("INFO" if tp <= -0.9 else "FAIL", 0.0, f"true peak {tp:.1f} dBTP (max -1.0)"))
        if st_max is not None and integ is not None and st_max > integ + 6:
            flags.append(("WARN", 0.0, f"loudest 3 s {st_max:.1f} LUFS, {st_max - integ:.1f} LU over the average (ears)"))
        for a, b in silences(path, dur):
            flags.append(("FAIL", a, f"absolute silence {b - a:.2f} s (under -50 dBFS)"))

    # 3. the voice
    if args.words:
        ws = json.loads(Path(args.words).read_text(encoding="utf-8"))
        ws = [w for w in ws if "start" in w]
        if ws:
            if L["first_word"] is not None and ws[0]["start"] > L["first_word"]:
                flags.append(("FAIL", 0.0, f"first word at {ws[0]['start']:.2f} s (Shorts: on frame 0)"))
            quiet_run = None
            if args.voice:  # the longest stretch inside a gap where the voice is 35 dB under its own loud level (10-ms frames)
                import soundfile as sf
                vx, vsr = sf.read(args.voice)
                vx = vx.mean(axis=1) if vx.ndim > 1 else vx
                hop = int(0.01 * vsr)
                vdb = 20 * np.log10(np.sqrt(np.mean(vx[:len(vx) // hop * hop].reshape(-1, hop) ** 2, axis=1)) + 1e-9)
                vq = vdb < np.percentile(vdb, 95) - 35

                def quiet_run(a, b):
                    best = run = 0
                    for v in vq[int(a * 100):int(b * 100) + 1]:
                        run = run + 1 if v else 0
                        best = max(best, run)
                    return best / 100
            for p, q in zip(ws, ws[1:]):
                gap = q["start"] - p["end"]
                silent = quiet_run(p["end"], q["start"]) if quiet_run else gap
                if gap > L["gap"] and silent > L["gap"] and not allowed(p["end"], q["start"]):
                    flags.append(("WARN" if fmt == "long" else "FAIL", p["end"], f"no talking for {silent:.2f} s"))
            tail = dur - ws[-1]["end"]
            if tail > L["tail"]:
                flags.append(("FAIL", ws[-1]["end"], f"{tail:.1f} s after the last word (end right after it)"))

    # report
    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    flags.sort(key=lambda x: (order[x[0]], x[1]))
    lines = [f"# QA: {path.name} ({fmt}, {W}x{H}, {src_fps:.2f} fps, {dur:.1f} s)", ""]
    for lvl, tt, txt in flags:
        lines.append(f"- **{lvl}** {int(tt // 60)}:{tt % 60:05.2f} {txt}")
    look = [(tt, f"{lvl} {txt}") for lvl, tt, txt in flags if lvl != "INFO"][:96]
    files = sheet(path, look, out, vertical) if look else []
    lines += ["", "Sheets: " + ", ".join(str(f) for f in files)]
    (out / "qa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if any(l == "FAIL" for l, _, _ in flags) else 0


if __name__ == "__main__":
    sys.exit(main())
