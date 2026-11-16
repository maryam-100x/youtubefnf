"""review_reels.py: the review reel of what changed between two versions of a video, for any video: the changed shots cut from the new
render with the current mix, so a review watches every changed shot and none of the rest, never against an old mix.

  PIPE tools/pipeline/review_reels.py <video> --version 3 --since-version 2
        the shots whose code changed between the code v2's render was made on and v3's (each render's parts_v<N>/state.json: the shot
        signatures reprobe.py compares, matched by their shape alone, so a shot that only moved or changed length with the voice is
        not reeled), cut from v3's parts and the current mix
  ... --version 3 --since-rev <git rev>     against the code at a git revision (its src/ checked out under tools/motion/out/rev_<sha>/)
  ... --version 3 --ranges 1000-1240,...    any frame ranges (a patch list, a gate round's fixed ranges)
  options: --mix <wav> (default build/score/mix_v<N>.wav), --pad 0.4 (s around each changed shot), --max-min 8 (a reel's length; longer
           lists make reel_1, reel_2 ...), --out <dir> (default review/v<N>_reels/)

Each stretch is cut from the render's own parts at exact frames (parts_v<N>/parts.json; an older render's part_NN.mkv chunks by their
edges; or the joined v<N>_picture.mkv) and the mix at the same film seconds: a raw H.264 stream and exact PCM per stretch, joined and muxed
once (no container stamps, no drift), checked for sync at the last stretch (picture best offset 0, sound lag under one frame). Writes the
reel at 720p, a phone copy under 30 MB (small enough to send to a phone), and the list of film times with the words said there."""
import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FFMPEG, REPO, Video, find_video, frame_count, say  # noqa: E402,F401

FPS, SR = 60, 48000
WIDE = 5      # a changed component under more than this many shots is shown by one example (used by several: listed)
FF = [FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
PHONE_MB = 28


def pieces_of(v, ver):
    """[(file, first film frame, frames)] of the render's picture"""
    pdir = v.render_dir / f"parts_v{ver}"
    mf = pdir / "parts.json"
    if mf.exists():
        return [(Path(p["file"]), p["f0"], p["f1"] - p["f0"] + 1) for p in json.loads(mf.read_text(encoding="utf-8"))["parts"]]
    olds = sorted(pdir.glob("part_[0-9][0-9].mkv"))
    if olds:   # an older render's chunks: edges = round(total * i / chunks)
        total = v.frames()
        n = len(olds)
        e = [round(total * i / n) for i in range(n + 1)]
        return [(f, e[i], e[i + 1] - e[i]) for i, f in enumerate(olds)]
    pic = v.render_dir / f"v{ver}_picture.mkv"
    if pic.exists():
        return [(pic, 0, frame_count(pic))]
    raise SystemExit(f"no render of v{ver}: {pdir} or {pic}")


def plist(pieces, f0, f1):
    """(file, local a, local b) covering film frames [f0, f1)"""
    out = []
    for path, a, n in pieces:
        lo, hi = max(f0, a), min(f1, a + n)
        if lo < hi:
            out.append((path, lo - a, hi - a))
    return out


def seg_cmd(pl, f0, n, mix, out):
    cmd, fl, labs = list(FF), [], []
    for k, (path, a, b) in enumerate(pl):
        # half a frame early: an mkv's ms timestamps would lose a frame to an exact -ss
        cmd += ["-ss", f"{max(0.0, (a - 0.5) / FPS):.6f}", "-i", str(path)]
        fl.append(f"[{k}:v]trim=end_frame={b - a},setpts=PTS-STARTPTS[v{k}]")
        labs.append(f"[v{k}]")
    k = len(labs)
    cmd += ["-ss", f"{f0 / FPS:.6f}", "-i", str(mix)]
    vin = "".join(labs) + (f"concat=n={k}:v=1:a=0," if k > 1 else "")
    fl.append(f"{vin}setpts=N/{FPS}/TB,scale=1280:-2,format=yuv420p[v]")
    fl.append(f"[{k}:a]aformat=sample_rates={SR}:channel_layouts=stereo,apad,atrim=end_sample={n * SR // FPS},asetpts=N/SR/TB[a]")
    cmd += ["-filter_complex", ";".join(fl), "-map", "[v]", "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-bf", "0",
            "-f", "h264", str(out.with_suffix(".h264")), "-map", "[a]", "-c:a", "pcm_s16le", str(out.with_suffix(".wav"))]
    return cmd


def gray(src, ss, n, w=320, h=180):
    # passthrough: a seek that lands a fraction of a frame early must not make ffmpeg duplicate the first frame to keep a constant rate
    # (it did: every check after the first stretch read one frame off)
    r = subprocess.run(FF + ["-ss", f"{max(0.0, ss):.6f}", "-i", str(src), "-frames:v", str(n), "-fps_mode", "passthrough", "-vf", f"scale={w}:{h},format=gray",
                             "-f", "rawvideo", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)


def pcm(src, ss, dur):
    r = subprocess.run(FF + ["-ss", f"{max(0.0, ss):.6f}", "-i", str(src), "-t", f"{dur:.6f}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32)


def sync_check(reel, spans, pieces, mix):
    """at the last stretch's sharpest change: the reel's frames are the film's (best offset 0 of -4..+4) and its sound is the mix's
    (lag under a frame)"""
    j = sum(b - a for a, b, _ in spans[:-1])
    f0, f1, _ = spans[-1]
    n = min(180, f1 - f0)
    path, a, _ = plist(pieces, f0, f0 + n)[0]
    film = gray(path, (a - 0.5) / FPS, n)
    if len(film) < 12:
        return True, "sync: stretch too short to check"
    d = np.array([np.abs(film[i] - film[i - 1]).mean() for i in range(1, len(film))])
    m = 6 + int(np.argmax(d[5:len(d) - 5]))
    rf = gray(reel, (j + m - 2 - 0.5) / FPS, 4)
    errs = [float(np.mean([np.abs(rf[q] - film[m - 2 + o + q]).mean() for q in range(min(4, len(rf)))])) if 0 <= m - 2 + o and m + 2 + o <= len(film) else 1e9
            for o in range(-4, 5)]
    off = int(np.argmin(errs)) - 4
    R = pcm(reel, j / FPS + max(m / FPS, 0.1), 1.0)
    M = pcm(mix, f0 / FPS + max(m / FPS, 0.1) - 0.25, 1.5)
    L = len(R)
    if L < 1000 or len(M) < L or float(np.abs(R).max()) < 1e-4:
        return off == 0, f"sync: picture offset {off} frames (sound too quiet there to check)"
    sc = [float(np.dot(R, M[q:q + L]) / (np.linalg.norm(R) * np.linalg.norm(M[q:q + L]) + 1e-9)) for q in range(0, len(M) - L, 8)]
    lag = (int(np.argmax(sc)) * 8 - 0.25 * SR) / SR * 1000
    ok = off == 0 and abs(lag) < 1000 / FPS and max(sc) > 0.9
    return ok, f"sync at reel {(j + m) / FPS:.2f} s = film {(f0 + m) / FPS:.2f} s: picture offset {off} frames, sound lag {lag:+.1f} ms (corr {max(sc):.3f})"


def mm(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def film_words(v):
    for p in (v.dj / "build" / "insert" / "words_ins.json", v.src_dir / "words.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return []


def said(W, t0, t1, n=7):
    ws = [x["w"] for x in W if t0 - 0.05 <= x["start"] < t1]
    return " ".join(ws[:n]) + (" ..." if len(ws) > n else "")


def changed_spans(v, a):
    import reprobe
    total = v.frames()
    if a.ranges:
        return [tuple(int(x) for x in r.split("-")) for r in a.ranges.split(",")]
    new_state = v.render_dir / f"parts_v{a.version}" / "state.json"
    if a.rev:   # the code the version was rendered from, when its render kept no state.json (an older render)
        new = reprobe.snapshot_at(v, a.rev, total)
    else:
        new = json.loads(new_state.read_text(encoding="utf-8")) if new_state.exists() else reprobe.snapshot(v, total)
    if a.since_version:
        old = json.loads((v.render_dir / f"parts_v{a.since_version}" / "state.json").read_text(encoding="utf-8"))
    else:
        old = reprobe.snapshot_at(v, a.since_rev, total)
    p = reprobe.plan(v, old, new, review=True)
    if "shots" not in p:   # no snapshot to compare: everything
        return [(0, total - 1)]
    # what a reviewer needs: every shot whose own code changed, and the shots a changed component reaches when it reaches few of them;
    # a component that most shots use (the design system, the clip player) changed under all of them: listed once, not reeled whole
    n = len(new["shots"])
    count = {}
    for j, f0, f1, why in p["shots"]:
        if isinstance(why, list):
            for x in why:
                count[x] = count.get(x, 0) + 1
    wide = {x for x, c in count.items() if c > WIDE}
    keep = [(f0, f1) for j, f0, f1, why in p["shots"] if not isinstance(why, list) or set(why) - wide]
    # one example of each wide change: its first shot
    for x in sorted(wide):
        ex = next(((f0, f1) for j, f0, f1, why in p["shots"] if isinstance(why, list) and x in why), None)
        if ex:
            keep.append(ex)
    own = sum(1 for _j, _a, _b, why in p["shots"] if not isinstance(why, list))
    say(f"changed: {own} shots in their own code, {len(keep) - own} reached by a changed component used by few shots; "
        f"{len(p['why'].get('changed_files', []))} changed files")
    if wide:
        say(f"changed under more than {WIDE} shots each, one example of each in the reel: "
            + ", ".join(f"{x} ({count[x]})" for x in sorted(wide, key=lambda x: -count[x])))
    return keep


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--version", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since-version")
    g.add_argument("--since-rev")
    g.add_argument("--ranges")
    ap.add_argument("--rev", help="the git revision version N was rendered from (a render from before parts_v<N>/state.json)")
    ap.add_argument("--plan-only", action="store_true", help="print the changed stretches, cut nothing")
    ap.add_argument("--mix")
    ap.add_argument("--pad", type=float, default=0.4)
    ap.add_argument("--max-min", type=float, default=8.0)
    ap.add_argument("--out")
    a = ap.parse_args()
    v = Video(find_video(a.video))
    pieces = pieces_of(v, a.version)
    total = sum(n for _, _, n in pieces) if pieces[-1][1] + pieces[-1][2] == sum(n for _, _, n in pieces) else pieces[-1][1] + pieces[-1][2]
    mix = Path(a.mix) if a.mix else v.dj / "build" / "score" / f"mix_v{a.version}.wav"
    if not mix.exists():
        raise SystemExit(f"{mix} is missing (--mix)")
    pad = round(a.pad * FPS)
    rs = sorted((max(0, x - pad), min(total, y + 1 + pad)) for x, y in changed_spans(v, a))
    spans = []
    for x, y in rs:
        if spans and x <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], y)
        else:
            spans.append([x, y])
    W = film_words(v)
    spans = [(x, y, said(W, x / FPS, y / FPS)) for x, y in spans]
    if a.plan_only:
        for x, y, words in spans:
            say(f"  film {mm(x / FPS)}-{mm(y / FPS)}  \"{words}\"")
        say(f"{len(spans)} stretches, {sum(y - x for x, y, _ in spans) / FPS / 60:.1f} min")
        return
    # reels of at most --max-min minutes, in film order
    reels, cur, dur = [], [], 0
    for s in spans:
        if cur and dur + (s[1] - s[0]) > a.max_min * 60 * FPS:
            reels.append(cur)
            cur, dur = [], 0
        cur.append(s)
        dur += s[1] - s[0]
    if cur:
        reels.append(cur)
    out = Path(a.out) if a.out else v.dj / "review" / f"v{a.version}_reels"
    out.mkdir(parents=True, exist_ok=True)
    say(f"{len(spans)} stretches, {sum(y - x for x, y, _ in spans) / FPS / 60:.1f} min, in {len(reels)} reel(s)")
    for k, rl in enumerate(reels, 1):
        tmp = out / f"tmp_{k}"
        tmp.mkdir(exist_ok=True)
        vid, aud = tmp / "all.h264", tmp / "all.wav"
        with open(vid, "wb") as vo, wave.open(str(aud), "wb") as ao:
            for i, (x, y, _) in enumerate(rl):
                f = tmp / f"{i:03d}"
                subprocess.run(seg_cmd(plist(pieces, x, y), x, y - x, mix, f), check=True)
                vo.write(f.with_suffix(".h264").read_bytes())
                with wave.open(str(f.with_suffix(".wav")), "rb") as w:
                    if i == 0:
                        ao.setparams(w.getparams())
                    if w.getnframes() != (y - x) * SR // FPS:
                        raise SystemExit(f"stretch {i}: {w.getnframes()} samples, want {(y - x) * SR // FPS}")
                    ao.writeframes(w.readframes(w.getnframes()))
        name = f"reel_v{a.version}" + (f"_{k}" if len(reels) > 1 else "")
        reel = out / f"{name}.mp4"
        subprocess.run(FF + ["-framerate", str(FPS), "-i", str(vid), "-i", str(aud), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-bsf:v",
                             f"setts=ts=N/({FPS}*TB)", "-c:a", "aac", "-b:a", "160k", "-video_track_timescale", "15360", "-movflags", "+faststart",
                             str(reel)], check=True)
        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()
        secs = sum(y - x for x, y, _ in rl) / FPS
        kbps = min(4000, max(400, int(PHONE_MB * 8e6 / max(secs, 1) / 1000) - 140))   # under 30 MB, and no more than a 720p copy needs
        phone = out / f"{name}_phone.mp4"
        subprocess.run(FF + ["-i", str(reel), "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{kbps}k", "-maxrate",
                             f"{int(kbps * 1.2)}k", "-bufsize", f"{kbps * 2}k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags",
                             "+faststart", str(phone)], check=True)
        ok, msg = sync_check(reel, rl, pieces, mix)
        say(f"REEL {reel} ({mm(secs)}; phone copy {phone.stat().st_size / 1e6:.1f} MB) {msg} -> {'OK' if ok else 'OFF'}")
        r0 = 0
        for x, y, words in rl:
            say(f"  film {mm(x / FPS)}-{mm(y / FPS)}  (reel {mm(r0 / FPS)})  \"{words}\"")
            r0 += y - x
        if not ok:
            raise SystemExit(f"{name}: sync check failed")


if __name__ == "__main__":
    main()
