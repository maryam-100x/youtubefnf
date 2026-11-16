"""The production line in one command: pipe.py <video> <step>. Every video reads its own videos/<video>/video.toml (the template:
tools/pipeline/video.example.toml); no video gets its own copies of render/link/audit/finish/srt scripts. No model is needed to run
any step.

  PIPE tools/pipeline/pipe.py <012 | 012-city-at-night | path> <step> [options]

Steps for a long video (kind = "long"):
  script   the script gate: tools/script/script_lint.py --strict (fix-level flags stop the line; --force goes on)
  voice    the voice: voice_ready.py require, the voice chain (voice_chain.sh: takes, the chain, the sound gate), the lock
           (voice_lock.py lock); render, patch, score and finish refuse while the lock doesn't verify (standard/VOICE_LOCK.md)
  link     the lean public dir of hard links (Remotion copies the public dir into the temp on every render, and the full one runs to
           tens of GB)
  gate     the pre-render gate (gate.py): every frame probed for freezes, held frames, flashes, empty frames, text cut off or
           on text, objects off the frame, motion at the cut, effects with nothing shown, overused clips, cut-out edges; `render`
           refuses code the gate hasn't passed. `--scope a-b,c-d`: the scoped gate, every picture check on those shots
           only, in minutes, for a builder's or fixer's own loop; never a pass (gate.step_scope)
  audit    the static clip audit without a render (every play against its file's length, shots and plays under 0.5 s, plays under 1.0x),
           then both edges of every play against its source's own cuts (a sliver of the next shot), has_b_frames on every clip
  plays    every clip play's first, middle and last frame on sheets for the eye (plays_sheet.py: a play that opens on a rating card
           shows there)
  stills   proof stills with one bundle (stills.mjs): --frames 120,600 or --shots 3,4 or --every (one still 0.5 s into each shot)
  render   the picture in parts at 1440p (--chunks, --concurrency, --only 3,4 redoes parts, --frames a-b renders one test range),
           resumable: a part whose file holds every frame is kept; the join goes to a temp name and is moved into place safely
  patch    re-rendered frame ranges as segments (segs.mjs, one bundle): --ranges 1000-1240,...; `finish --patches` lays them in
  score    the mix from the cue sheet (tools/sound/score.py) -> build/score/mix_v<N>.wav, with its report
  finish   the upload file: the mix muxed onto the picture, finish_long.py (4K60 on the GPU, the sound settings from video.toml),
           the subtitles, the stutter check, the file's numbers; --test 0-10 proves the chain on a few seconds first
  srt      the upload subtitles from the captions' srt (`python -m dj captions`) with the fixes table and the real voices' lines in
           the holds
  qa       the QA gate: every check we have, one report (videos/<video>/QA_v<N>.md) with pass/fail and the delivery checklist
  all      link, audit, render, finish, qa
Steps for a Short (kind = "short"): link, gate, render, finish (the captions burned in, the score, qa_render, qa_holds, a 2-fps
sheet), qa, all.

One Remotion job at a time (two side by side kill each other's renders): render, stills and patch wait until no headless browser
runs and no other heavy job holds a ticket (heavy.py; --wait <minutes> to give up instead).
Every step prints what it did and writes its logs to the video's media folder (VIDEOS/<video>/pipeline/). Exit 1 when a gate fails."""
import argparse
import fnmatch
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (FFMPEG, FFPROBE, HERE, MOTION, NODE, NPX, PUBLIC, PY_EDIT, PY_PIPE, PY_VISION, QA_TOOLS, REPO, SCRIPT_TOOLS,  # noqa: E402,F401
                    SOUND, VOICE, WINDOWS, WORKFLOW, RemotionJob, Video, after_remotion, disk_free_gb, ffprobe, find_video, frame_count,
                    hhmm, human_size, loudness, run, safe_replace, say, temp_env)
from heavy import HeavyJob  # noqa: E402
sys.path.append(str(MOTION))
from codefiles import code_files  # noqa: E402   a video's code with the subfolder files it imports

MEDIA_EXT = r"mp4|jpg|jpeg|png|svg|webp|mov|mkv|wav|mp3|json|gif"


# ============================================================================================================================ script gate
def step_script(v, a):
    out = v.pipe_dir / "lint.json"
    v.pipe_dir.mkdir(parents=True, exist_ok=True)
    cmd = [PY_PIPE, SCRIPT_TOOLS / "script_lint.py", v.folder / "script.md", "--json", out, "--strict"] + (["--ignore", a.ignore] if a.ignore else [])
    r = run(cmd, check=False)
    print(r.stdout)
    if r.returncode and not a.force:
        raise SystemExit("the script gate is closed: fix the 'to fix' flags or read them and run with --force (each kept flag written down)")
    say(f"script gate {'passed' if not r.returncode else 'passed with --force'} -> {out}")


# ================================================================================================================================= link
def link_set(v):
    """Every file under PUBLIC the composition names: whole folders, the `const C = 'dir/'` + `C + 'file'`
    pairs and quoted media paths in the scanned sources, the receipt lists' srcs, extra files."""
    L = v.section("link")
    need = set(L.get("folders", [])) | set(L.get("files", []))
    own = f"src/{v.src}/"
    for pattern in L.get("scan", []):
        # a pattern for the video's own code folder reads the subfolder files the film imports too (motion/codefiles.py)
        tail = pattern[len(own):]
        sub = [f for f in code_files(v.src_dir, (".ts", ".tsx")) if f.parent != v.src_dir.resolve() and fnmatch.fnmatch(f.name, tail)] \
            if pattern.startswith(own) and "/" not in tail else []
        for f in sorted(set(MOTION.glob(pattern)) | set(sub)):
            s = f.read_text(encoding="utf-8")
            # also `const A = 'x/', B = 'y/';` declared on one line, and double-quoted paths (a file named only these ways would be
            # missed by the link step, and the render would fail on it)
            consts = dict(re.findall(r"\b([A-Za-z_]\w*) = '([^']+/)'", s))
            need |= {consts[c] + b for c, b in re.findall(r"\b(\w+) \+ '([^']+)'", s) if c in consts and "/" in consts[c] + b}
            for rel in re.findall(r"['\"]([A-Za-z0-9_]+(?:/[A-Za-z0-9_.\-]+)+\.(?:%s))['\"]" % MEDIA_EXT, s):
                if (PUBLIC / rel.split("/")[0]).is_dir():
                    need.add(rel)
    for pj in L.get("pages", []):
        d = json.loads((MOTION / pj).read_text(encoding="utf-8"))
        items = d.values() if isinstance(d, dict) else d
        need |= {m["src"] for m in items if isinstance(m, dict) and m.get("src")}
    return need


def step_link(v, a):
    need = link_set(v)
    linked = kept = 0
    missing = []
    for rel in sorted(need):
        src = PUBLIC / rel
        if not src.exists():
            missing.append(rel)
            continue
        files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
        for p in files:
            dst = v.pub / p.relative_to(PUBLIC)
            if dst.exists():
                if os.path.samefile(dst, p):
                    kept += 1
                    continue
                dst.unlink()
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.link(p, dst)
            linked += 1
    extra = sorted(str(p.relative_to(v.pub)).replace("\\", "/") for p in v.pub.rglob("*") if p.is_file()) if a.list_extra and v.pub.exists() else []
    say(f"{v.pub}: {len(need)} entries, {linked} linked, {kept} already there; missing {missing}")
    if extra:
        wanted = set()
        for rel in need:
            p = PUBLIC / rel
            wanted |= {str(q.relative_to(PUBLIC)).replace("\\", "/") for q in ([p] if p.is_file() else p.rglob("*")) if q.is_file()} if p.exists() else set()
        unneeded = [e for e in extra if e not in wanted]
        say(f"in the public dir but not named by the sources: {len(unneeded)}" + (f" (e.g. {unneeded[:5]})" if unneeded else ""))
    (v.pipe_dir / "link.json").parent.mkdir(parents=True, exist_ok=True)
    (v.pipe_dir / "link.json").write_text(json.dumps({"need": sorted(need), "missing": missing, "linked": linked, "kept": kept}, indent=1), encoding="utf-8")
    if missing:
        raise SystemExit(f"{len(missing)} file(s) the composition names are not under {PUBLIC}: the render would fail on them")


# ================================================================================================================================ audit
def audit_report(v, tag="audit", build=None):
    """Build and run the static audit (audit.tsx filled from video.toml) and return its report dict. `build`: a name of its own for the
    bundle in tools/motion/out (the scoped gate's runs go side by side with each other and with a full gate: never one file)."""
    A = v.section("audit")
    module = (v.src_dir / v.module)
    if not module.exists():
        raise SystemExit(f"{module} is missing (video.toml [video] module)")
    tsx = (HERE / "audit.tsx").read_text(encoding="utf-8")
    rel = "../" + module.relative_to(MOTION).with_suffix("").as_posix()
    tsx = tsx.replace("__MODULE__", rel).replace("__PLAYS__", json.dumps(A.get("plays", ["Foot", "VClip", "VideoCard", "Clip"])))
    tsx = tsx.replace("__BG__", json.dumps(A.get("bg", []))).replace("__MIN_SHOT__", str(A.get("min_shot", 0.5)))
    out = MOTION / "out"
    out.mkdir(exist_ok=True)
    stem = f"audit_{v.comp}" + (f"_{build}" if build else "")
    src = out / f"{stem}.tsx"
    src.write_text(tsx, encoding="utf-8")
    cjs = out / f"{stem}.cjs"
    esbuild = MOTION / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    run([esbuild, src.relative_to(MOTION).as_posix(), "--bundle", "--platform=node", f"--outfile={cjs.relative_to(MOTION).as_posix()}", "--loader:.json=json",
         "--log-level=warning"], cwd=MOTION, quiet=True)
    v.pipe_dir.mkdir(parents=True, exist_ok=True)
    report = v.pipe_dir / f"{tag}_{v.comp}.json"
    r = run([NODE, cjs], cwd=MOTION, env={"PLAYS_JSON": str(report)}, quiet=True)
    say(r.stdout.strip().splitlines()[-1])
    return json.loads(report.read_text(encoding="utf-8"))


def source_cuts(src, t_in, t_out, scene, pad=0.6):
    """ffmpeg's scene-change times inside [t_in - pad, t_out + pad] of a source file."""
    w0 = max(0.0, t_in - pad)
    o = subprocess.run([FFMPEG, "-hide_banner", "-ss", f"{w0:.3f}", "-t", f"{t_out - w0 + pad:.3f}", "-i", str(src), "-an", "-vf",
                        f"scale=320:-2,select='gt(scene,{scene})',showinfo", "-f", "null", "-"], capture_output=True, text=True, errors="replace").stderr
    return [w0 + float(t) for t in re.findall(r"pts_time:([\d.]+)", o)]


def frame_events(src, w0, w1):
    """Cuts and fades in [w0, w1] of a source, measured frame by frame (160x90 grey): a cut is a frame change far above the window's own
    motion (3x its median and 12+ levels) or a jump in the frame's brightness (6+ levels in one frame, 1.8x the motion); a fade is the
    brightness climbing out of black or falling into it (under 12 at one end, 8+ levels of range). ffmpeg's scene score (0.3) misses
    a cut between two dark shots (score 0.15), an end card's lights flickering on, a montage cut 0.05 s into a play.
    -> ([cut times], [(fade start, fade end, lum from, lum to)])"""
    w0 = max(0.0, w0)
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(src)],
                       capture_output=True, text=True)
    num, _, den = (r.stdout.strip().strip(",") or "30/1").partition("/")
    fps = float(num) / float(den or 1)
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{w0:.3f}", "-t", f"{w1 - w0:.3f}", "-i", str(src), "-an", "-vf",
                          "scale=160:90,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    import numpy as np
    if len(raw) < 2 * 160 * 90:
        return [], []
    f = np.frombuffer(raw[: len(raw) // (160 * 90) * 160 * 90], dtype=np.uint8).reshape(-1, 90, 160).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    lum = f.mean(axis=(1, 2))
    med = float(np.median(d[d > 0.05])) if (d > 0.05).any() else 0.0
    t = w0 + np.arange(1, len(f)) / fps  # the time of the frame each change lands on
    cuts = []
    for i, di in enumerate(d):
        jump = abs(float(lum[i + 1] - lum[i]))
        if (di >= max(12.0, 3.0 * med)) or (jump >= 6.0 and di >= max(10.0, 1.8 * med)):
            cuts.append(round(float(t[i]), 3))
    # a dissolve: 3+ frames in a row, each changing far above the window's own motion, none reaching a cut's size (an interview clip
    # dissolving into the next shot: 4.8 a frame against a median of 0.19, and a play that ends 5 frames into it shows the next shot)
    hot = d >= max(2.5, 8.0 * med)
    k = 0
    while k < len(d):
        if hot[k]:
            j = k
            while j < len(d) and hot[j]:
                j += 1
            if j - k >= 3:
                cuts.append(round(float(t[k]), 3))
            k = j
        else:
            k += 1
    cuts = sorted(set(cuts))
    fades = []
    lo, hi = float(lum.min()), float(lum.max())
    if hi - lo >= 8.0 and lo < 12.0:
        k0, k1 = int(lum.argmin()), int(lum.argmax())
        a, b = sorted((k0, k1))
        fades.append((round(w0 + a / fps, 3), round(w0 + b / fps, 3), round(float(lum[k0]), 1), round(float(lum[k1]), 1)))
    return cuts, fades


def edges_check(v, report, edge, scene):
    """The edge check for every play: a source cut within `edge` seconds of a play's in or out point is a sliver of the shot before
    or after; a fade or flicker there counts too, measured frame by frame (frame_events) as well as by ffmpeg's scene score. Fast motion
    can score like a cut: each hit is looked at on its frames."""
    hits = []
    plays = [p for p in report["plays"] if p["src"].rsplit(".", 1)[-1].lower() in ("mp4", "mkv", "mov", "webm")]
    for p in plays:
        src = v.pub / p["src"] if (v.pub / p["src"]).exists() else PUBLIC / p["src"]
        if not src.exists():
            continue
        t_in, t_out = p["from"], p["from"] + p["len"] * p["rate"]
        cuts = source_cuts(src, t_in, t_out, scene)
        hc, hf = frame_events(src, t_in - 0.3, min(t_out, t_in + edge + 0.5))
        tc, tf = frame_events(src, max(t_in, t_out - edge - 0.5), t_out + 0.3)
        cuts = sorted({round(c, 2) for c in cuts + hc + tc})
        inside = [c for c in cuts if t_in + 0.02 < c < t_out - 0.02]
        head = [c for c in inside if c - t_in < edge]
        tail = [c for c in inside if t_out - c < edge]
        head_fade = [f for f in hf if f[0] < t_in + edge and f[1] > t_in + 0.02]
        tail_fade = [f for f in tf if f[1] > t_out - edge and f[0] < t_out - 0.02]
        if head or tail or head_fade or tail_fade:
            what = []
            if head:
                what.append(f"opens on {max(head) - t_in:.2f} s of the shot before (cut at {max(head):.2f})")
            if head_fade:
                what.append(f"opens in a fade or flicker ({head_fade[0][2]:.0f} -> {head_fade[0][3]:.0f} grey, {head_fade[0][0]:.2f}-{head_fade[0][1]:.2f})")
            if tail:
                what.append(f"ends on {t_out - min(tail):.2f} s of the next shot (cut at {min(tail):.2f})")
            if tail_fade:
                what.append(f"ends in a fade or flicker ({tail_fade[0][2]:.0f} -> {tail_fade[0][3]:.0f} grey, {tail_fade[0][0]:.2f}-{tail_fade[0][1]:.2f})")
            hits.append({"at": p["at"], "shot": p["shot"], "src": p["src"], "in": t_in, "out": t_out, "what": "; ".join(what), "cuts": inside})
    return hits, len(plays)


# working words that must never reach the screen (a source line that reads "his take"): labels for the creator's opinions, fact ids,
# review numbers, rule numbers, beat ids, placeholders
INTERNAL = re.compile(r"\bhis (take|opinion|words|note)\b|\bour (gloss|take|note)\b|\bF\d+-\d+\b|#\d+|\brule \d+|\bS\d{2}[a-z]?\b|\bTODO\b|\bTBD\b|\bplaceholder\b|\bXXX\b", re.I)


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def step_audit(v, a):
    report = audit_report(v)
    A = v.section("audit")
    bad = 0
    for o in report["over"]:
        p = o["play"]
        say(f"OVER {mmss(p['at'])} shot {p['shot']}: {p['src']} from {p['from']:.2f} for {p['len']:.2f} s x{p['rate']} asks {o['asks']:.2f} of {o['len']:.2f} s ({o['frozen']:.2f} s frozen)")
        bad += 1
    for c in report.get("caps", []):
        if INTERNAL.search(c["text"]):
            say(f"CAPTION {mmss(c['at'])} shot {c['shot']}: {c['comp']} {c['prop']}=\"{c['text']}\" reads like a working note, not a caption")
            bad += 1
    for m in report.get("marks", []):
        if m["share"] > 0.5:
            say(f"MARK {mmss(m['at'])} shot {m['shot']}: '{m['hl']}' is {m['share']:.0%} of '{m['text']}' (a mark on most of the text is no mark: show it plain)")
            bad += 1
    for s in report["short"]:
        say(f"SHORT {mmss(s['at'])} shot {s['i']}: {s['end'] - s['at']:.2f} s (under {report['minShot']} s reads as a flash)")
        bad += 1
    for p in report["shortPlays"]:
        say(f"SHORT PLAY {mmss(p['at'])} shot {p['shot']}: {p['src']} for {p['len']:.2f} s")
        bad += 1
    for p in report["slow"]:
        say(f"SLOW {mmss(p['at'])} shot {p['shot']}: {p['src']} at {p['rate']}x (a cut, never a slowed clip, outside a deliberate replay)")
        bad += 1
    if report["unknown"]:
        say(f"not in clipdurs.json ({len(report['unknown'])}): {', '.join(report['unknown'][:12])}{' ...' if len(report['unknown']) > 12 else ''}")
        bad += len(report["unknown"])
    # a spoken beat of 2 s or more with no shot starting inside it rides on the shot before (a 20-s opinion with no shots of its own plays
    # under whatever the shot before showed, and only the sheet after the render shows it)
    starts = sorted(s["at"] for s in report["shots"])
    for bt in v.beats()["beats"]:
        b0, b1 = float(bt["start"]), float(bt.get("voice_end", bt["end"]))
        if b1 - b0 >= 2.0 and not any(b0 - 0.35 <= s < b1 for s in starts):
            say(f"BEAT {mmss(b0)} {bt['id']} ({b1 - b0:.1f} s) has no shot of its own: it plays under the shot before")
            bad += 1
    # the slowed-clip rule in the code itself: a `rate={0.` on any clip component
    rates = []
    for f in code_files(v.src_dir):   # with the subfolder files the film imports
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"rate=\{0\.", ln):
                rates.append(f"{f.relative_to(v.src_dir.resolve()).as_posix()}:{i}: {ln.strip()[:100]}")
    if rates:
        say(f"rate under 1.0 in the code ({len(rates)}):\n  " + "\n  ".join(rates))
    # B-frames: Remotion grabs wrong frames from clips with them
    bframes = []
    for src in sorted({p["src"] for p in report["plays"] if p["src"].rsplit(".", 1)[-1].lower() in ("mp4", "mkv", "mov", "webm")}):
        f = v.pub / src if (v.pub / src).exists() else PUBLIC / src
        if f.exists():
            kv = ffprobe(f, entries="stream=has_b_frames", count=False)
            if kv.get("has_b_frames", "0") not in ("0", ""):
                bframes.append(src)
    if bframes:
        say(f"clips with B-frames ({len(bframes)}): {', '.join(bframes[:10])}{' ...' if len(bframes) > 10 else ''} (cut them with -bf 0)")
        bad += len(bframes)
    edges = []
    if not a.no_edges:
        say(f"{hhmm()} edges: every play against its source's own cuts (edge {A.get('edge', 0.5)} s, scene {A.get('scene', 0.3)}) ...")
        edges, n = edges_check(v, report, float(A.get("edge", 0.5)), float(A.get("scene", 0.3)))
        for h in edges:
            say(f"EDGE {mmss(h['at'])} shot {h['shot']}: {h['src']} {h['in']:.2f}-{h['out']:.2f}: {h['what']}  [cuts inside: {', '.join(f'{c:.2f}' for c in h['cuts'])}]")
        say(f"{len(edges)} play(s) with a source cut within {A.get('edge', 0.5)} s of an edge (of {n} video plays)")
        bad += len(edges)
    summary = {"plays": len(report["plays"]), "shots": len(report["shots"]), "over": len(report["over"]), "short": len(report["short"]) + len(report["shortPlays"]),
               "slow": len(report["slow"]), "unknown": len(report["unknown"]), "rate_in_code": rates, "bframes": bframes, "edges": edges, "bad": bad}
    (v.pipe_dir / f"audit_{v.comp}_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    say(f"audit: {len(report['plays'])} plays in {len(report['shots'])} shots; {bad} thing(s) to look at -> {v.pipe_dir / f'audit_{v.comp}_summary.json'}")
    if bad and not a.soft:
        raise SystemExit(1)
    return summary


# =============================================================================================================================== stills
def step_stills(v, a):
    step_link(v, a)   # every file the code names linked first (a render dies on a file added after the last link)
    frames = []
    if a.frames:
        frames = [int(x) for x in a.frames.split(",") if x.strip()]
    if a.shots or a.every:
        report = audit_report(v, tag="shots")
        shots = report["shots"]
        picks = [shots[int(i)] for i in a.shots.split(",")] if a.shots else shots
        for s in picks:
            frames.append(round((s["at"] + min(a.offset, max(0.0, s["end"] - s["at"] - 1 / v.fps))) * v.fps))
            if a.ends:
                frames.append(max(0, round(s["end"] * v.fps) - 1))
    if not frames:
        raise SystemExit("stills: give --frames 120,600, --shots 3,4 or --every")
    out = Path(a.out) if a.out else v.pipe_dir / f"stills_{time.strftime('%m%d_%H%M')}"
    out.mkdir(parents=True, exist_ok=True)
    with RemotionJob(f"stills {v.id} ({len(frames)} frames)", a.wait):
        r = run([NODE, "stills.mjs", out, str(a.scale or 0.5), *[str(f) for f in sorted(set(frames))]], cwd=MOTION,
                env={"QA_COMP": v.comp, "QA_PUBLIC": v.pub.as_posix(), **temp_env()}, log=v.pipe_dir / "stills.log")
    say(f"{len(set(frames))} stills -> {out}")
    if a.sheet:
        sheet = out / "sheet.jpg"
        files = sorted(out.glob("f_*.png"), key=lambda p: int(p.stem[2:]))
        if files:
            lst = out / "list.txt"
            lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files), encoding="utf-8")
            cols = min(6, len(files))
            rows = -(-len(files) // cols)
            run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"scale=320:-1,tile={cols}x{rows}", "-frames:v", "1", sheet], quiet=True)
            say(f"sheet -> {sheet}")


# =============================================================================================================================== render
def chunk_edges(total, chunks):
    return [round(total * i / chunks) for i in range(chunks + 1)]


def lean_bundle(v):
    """One bundle for a whole render, its public dir a junction to the lean dir (tools/motion/lean_bundle.mjs): the CLI renders every
    chunk from it, so no chunk bundles again or copies the public dir (several GB and ~2 min per chunk otherwise), and every chunk draws
    the same code. None with QA_COPY=1 (each chunk bundles and copies).
    QA_ENTRY=<entry> (a film registered only on its own root, e.g. src/v12_index.ts): the bundle is made from that entry, as the gate's
    probe already is (gate.py, reprobe.py), so the film renders from the same code the gate passed."""
    if os.environ.get("QA_COPY") == "1":
        return None
    entry = os.environ.get("QA_ENTRY")
    r = run([NODE, "lean_bundle.mjs", "make", v.pub.as_posix(), *([entry] if entry else [])], cwd=MOTION, env=temp_env(), quiet=True)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith('{"serveUrl"')]
    if not lines:
        raise SystemExit(f"lean bundle: no serveUrl printed\n{r.stdout[-1500:]}")
    url = json.loads(lines[-1])["serveUrl"]
    say(f"{hhmm()} one bundle for the render, no public-dir copy: {url}")
    return url


def lean_clean(url):
    if url:
        run([NODE, "lean_bundle.mjs", "clean", url], cwd=MOTION, quiet=True)


def render_cmd(v, comp, out, frames, concurrency, port=None, scale=None, mkv=True, gl=None, bundle=None):
    # bundle: a ready bundle folder (lean_bundle) as the entry point: the CLI renders from it without bundling or copying
    src = [bundle] if bundle else [os.environ.get("QA_ENTRY") or "src/index.ts"]
    pub = [] if bundle else [f"--public-dir={v.pub.as_posix()}"]
    cmd = [NPX, "remotion", "render", *src, comp, str(out), *pub, "--muted", "--timeout=120000", f"--concurrency={concurrency}"]
    if frames:
        cmd.append(f"--frames={frames[0]}-{frames[1]}")
    if mkv:   # a long video's chunk: lossless-joinable, the finish encodes once
        cmd += ["--codec=h264-mkv", "--crf=16", "--x264-preset=slow", "--color-space=bt709", f"--gl={gl or v.gl}", f"--scale={scale}"]
    if port:
        cmd.append(f"--port={port}")
    return cmd


def run_watched(cmd, cwd, env, log, stall=300):
    """run() for a render, with a stall guard: a render can hang with the browser and ffmpeg idle, no error and no driver reset, and a
    background job only reports when it ends, so a hang would sit unseen.
    Remotion prints a line per frame (and per step of bundling and copying), so its output goes to the log as it comes; when the log
    hasn't grown for `stall` seconds the whole process tree (npx, node, the browser, the compositor, ffmpeg) is killed. r.stalled says so.
    Windows: taskkill /T; macOS and Linux: the job runs in its own session and its process group is killed."""
    e = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    e.update(env or {})
    shown = " ".join(str(c) for c in cmd)
    say(f"$ {shown[:300]}{' ...' if len(shown) > 300 else ''}")
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    stalled = False
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        fh.write(f"$ {shown}\n\n")
        fh.flush()
        p = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=e, stdout=fh, stderr=subprocess.STDOUT, start_new_session=not WINDOWS)
        size, since = -1, time.time()
        while p.poll() is None:
            time.sleep(15)
            n = log.stat().st_size
            if n != size:
                size, since = n, time.time()
            elif time.time() - since > stall:
                stalled = True
                if WINDOWS:
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
                else:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except OSError:
                        p.kill()
                p.wait()
    r = subprocess.CompletedProcess(cmd, p.returncode, log.read_text(encoding="utf-8", errors="replace"), "")
    r.stalled = stalled
    return r


def render_with_retry(cmd, out, log, tries=2, pause=45):
    """Run a Remotion render; when the browser fails to come up ("Timed out ... while trying to connect to the browser", on a loaded
    computer right after another render), wait and try once more. Returns the CompletedProcess of the last try."""
    for k in range(tries):
        r = run_watched(cmd, MOTION, temp_env(), log)
        text = r.stdout
        # "Compositor error: No frame found" can kill a chunk while a memory-heavy job runs beside the render; the frames are in the
        # files, so the chunk gets one more try; so does a chunk that dies on the GPU with no message (exit 0xC0000005, an access
        # violation) and a chunk that stalls (run_watched killed it); a second stall stops the line with that message
        transient = (r.stalled or "connect to the browser" in text or "No frame found" in text
                     or r.returncode in (3221225477, -1073741819))
        if r.stalled:
            say(f"{hhmm()} STALLED: no output for 5 minutes, the render's processes were killed")
        if r.returncode == 0 or not transient or k == tries - 1:
            return r
        why = ("it stalled" if r.stalled else "Chrome did not come up" if "connect to the browser" in text
               else "the compositor lost a frame")
        say(f"{hhmm()} {why} ({tries - k - 1} more try after {pause} s)")
        time.sleep(pause)
    return r


def rescue_in_progress(out, log):
    """Remotion writes <out>.<id>.remotion-in-progress and renames it at the end; when the rename fails (the target open: EPERM), the finished
    file is left behind. If the log says the encode completed, move it into place."""
    out = Path(out)
    if out.exists() and out.stat().st_size > 0:
        return True
    tmp = sorted(out.parent.glob(out.name + ".*.remotion-in-progress"))
    if tmp and log.exists() and re.search(r"Encoded|Rendered|100%", log.read_text(encoding="utf-8", errors="replace")):
        safe_replace(tmp[0], out)
        say(f"{out.name}: moved the finished temp file into place")
        return out.exists()
    return False


def gpu_guard(gl, since):
    """The frames are drawn on the GPU; once the GPU driver resets during a render it is not tried again. After each GPU chunk: any
    NVIDIA driver reset (nvlddmkm in the system log) since the render began stops the line with that message (then: [render] gl =
    "swangle" for good). Windows only: skipped on macOS and Linux."""
    if gl == "swangle" or not WINDOWS:
        return
    mins = max(1, int((time.time() - since) / 60) + 1)
    ps = (f"$e = Get-WinEvent -FilterHashtable @{{LogName='System'; StartTime=(Get-Date).AddMinutes(-{mins})}} -ErrorAction SilentlyContinue | "
          "Where-Object { $_.ProviderName -match 'nvlddmkm' }; \"$(@($e).Count)\"")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.split()
    resets = int(out[0]) if out and out[0].isdigit() else 0
    if resets:
        raise SystemExit(f"GPU guard: {resets} NVIDIA driver reset(s) during this render. The GPU is not tried again: set [render] gl = "
                         "\"swangle\" in every video.toml and the default in common.py.")
    say(f"{hhmm()} GPU guard: no driver reset")


def render_settings(v, a):
    """the render's settings: video.toml [render] over the line's defaults (measured with render_bench.py; standard/PIPELINE.md)"""
    R = v.section("render")
    return {"crf": int(R.get("crf", RENDER_DEFAULTS["crf"])), "preset": R.get("preset", RENDER_DEFAULTS["preset"]),
            "imageFormat": R.get("image_format", RENDER_DEFAULTS["imageFormat"]), "jpegQuality": int(R.get("jpeg_quality", RENDER_DEFAULTS["jpegQuality"])),
            "parallel": R.get("parallel", RENDER_DEFAULTS["parallel"]), "gl": a.gl or v.gl, "scale": a.scale or v.scale,
            "timeoutMs": int(R.get("timeout_ms", 120000))}


# measured with render_bench.py on 600 frames of a long film at 1440p: x264 slow CRF 16 at concurrency 6 ran 7.08-7.96 fps (6.87 when
# Remotion turned parallel encoding off for memory, 5.54 cold), veryfast CRF 14 at 8 with parallel encoding 9.16-9.23 fps (1.22x; 1.34x
# against encoding after), SSIM to a lossless PNG reference 0.99382 against 0.99372 (the same quality)
RENDER_DEFAULTS = {"crf": 14, "preset": "veryfast", "imageFormat": "jpeg", "jpegQuality": 92, "parallel": "force", "part_frames": 3000}
STEP_DOWN = [None, 4, 2]   # a part that failed renders again at the video's concurrency, then 4, then 2 (rule: a failed part never restarts the run)


def comp_info(v, bundle, settings):
    """the composition's own length, fps and size, read from the bundle (render_parts.mjs info): the frame count comes from here"""
    jf = v.pipe_dir / "comp_info.job.json"
    jf.write_text(json.dumps({"serveUrl": bundle, "comp": v.comp, "gl": settings["gl"], "info": True, "parts": []}), encoding="utf-8")
    r = run([NODE, "render_parts.mjs", jf], cwd=MOTION, env=temp_env(), quiet=True)
    m = re.search(r"^COMP (.*)$", r.stdout, re.M)
    if not m:
        raise SystemExit(f"render: the composition {v.comp} didn't load:\n{r.stdout[-1500:]}")
    return json.loads(m.group(1))


def plan_parts(total, part_frames, chunks=None):
    n = chunks or max(1, round(total / part_frames))
    edges = chunk_edges(total, n)
    return [(i, edges[i], edges[i + 1] - 1) for i in range(n)]


def reencode_clip(v, rel, log):
    """a clip the compositor lost a frame of ("No frame found at position N for source <url>", the same part failing again on a clip
    whose frames are regular): re-encoded with a keyframe every second and no B-frames (Remotion's issues #7153 and #8732:
    the failures sit on long forward decodes from sparse keyframes), the same frame count and rate, then put in place of the original
    and relinked into the public dir. The original is kept in render/reencoded/ until the video is done."""
    src = PUBLIC / rel
    pub = v.pub / rel
    if not src.exists():
        say(f"re-encode: {rel} is not under {PUBLIC}")
        return False
    kv = ffprobe(src, entries="stream=nb_read_packets,r_frame_rate:format=duration")
    num, _, den = (kv.get("r_frame_rate") or "30/1").partition("/")
    fps = round(float(num) / float(den or 1))
    tmp = src.with_name(src.stem + ".reenc.mp4")
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "slow",
         "-crf", "12", "-g", str(fps), "-keyint_min", str(fps), "-bf", "0", "-pix_fmt", "yuv420p", "-fps_mode", "passthrough", "-c:a", "copy",
         "-movflags", "+faststart", tmp], quiet=True)
    a_, b_ = frame_count(src), frame_count(tmp)
    if a_ != b_:
        tmp.unlink()
        say(f"re-encode: {rel} came out {b_} frames against {a_}: not used")
        return False
    keep = v.render_dir / "reencoded" / src.name
    keep.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, keep)
    os.replace(tmp, src)
    if pub.exists():
        pub.unlink()
    pub.parent.mkdir(parents=True, exist_ok=True)
    os.link(src, pub)
    done = v.pipe_dir / "render_reencoded.json"
    lst = json.loads(done.read_text(encoding="utf-8")) if done.exists() else []
    lst.append({"clip": rel, "frames": a_, "at": time.strftime("%Y-%m-%d %H:%M"), "original": str(keep)})
    done.write_text(json.dumps(lst, indent=1), encoding="utf-8")
    say(f"{hhmm()} re-encoded {rel} ({a_} frames, keyframe every {fps}, no B-frames); original kept in {keep}")
    return True


def unrecorded_whole(mf, man0, f, i, f0, f1, code, settings, total):
    """a part the last run finished but never wrote into parts.json. render_parts records a batch's parts when the batch ends, so a run
    that stops mid-batch (a crash, a kill) leaves its finished parts out (after a crash at 8 of 12 parts the re-run would take the 8
    whole parts for stale, delete them and render all 12 again). Such a part is kept when
    its file holds every frame and was written after that run's manifest, by the same code, settings, length and plan."""
    if not (man0 and mf.exists() and f.exists()):
        return False
    if man0.get("code") != code or man0.get("settings") != settings or man0.get("total") != total:
        return False
    if "plan" in man0 and [i, f0, f1] not in man0["plan"]:
        return False
    if f.stat().st_mtime < mf.stat().st_mtime:
        return False
    return frame_count(f) == f1 - f0 + 1


def render_parts(v, a, bundle, settings, parts, conc, pdir, t_start, status):
    """render the parts [(i, f0, f1)] into pdir/part_NNN.mkv: each part whole or not at all; a failed part tries again at a lower
    concurrency, a lost-frame clip is re-encoded and the part tried again, a kit3 refusal stops the line with its reason; the parts already
    done stay done (a part that fails twice never sends the whole render back to the start)."""
    pending = list(parts)
    tries = defaultdict(int)
    reenc = set()
    n_run = 0
    while pending:
        i0 = pending[0][0]
        c = STEP_DOWN[min(tries[i0], len(STEP_DOWN) - 1)] or conc
        batch = pending if c == conc else pending[:1]   # a part retried at a lower concurrency goes alone, the rest at the video's
        job = {"serveUrl": bundle, "comp": v.comp, "concurrency": c, **settings,
               "parts": [{"i": i, "f0": f0, "f1": f1, "file": str(pdir / f"part_{i:03d}.mkv")} for i, f0, f1 in batch]}
        n_run += 1
        jf = pdir / f"run_{n_run:02d}.job.json"
        jf.write_text(json.dumps(job, indent=1), encoding="utf-8")
        say(f"{hhmm()} parts {batch[0][0]}-{batch[-1][0]} ({sum(f1 - f0 + 1 for _, f0, f1 in batch)} frames) at concurrency {c} ...")
        r = run_watched([NODE, "render_parts.mjs", jf], MOTION, temp_env(), pdir / f"run_{n_run:02d}.log", stall=300)
        enc = re.search(r"^ENC (.*)$", r.stdout, re.M)
        if enc and n_run == 1:
            say(f"encoding: {enc.group(1)}")
        done = {int(m.group(1)): float(m.group(3)) for m in re.finditer(r"^DONE (\d+) (\d+) ([\d.]+)$", r.stdout, re.M)}
        for i, f0, f1 in batch:
            if i in done:
                n = frame_count(pdir / f"part_{i:03d}.mkv")
                if n != f1 - f0 + 1:
                    raise SystemExit(f"part {i}: {n} frames, expected {f1 - f0 + 1}")
                status(i, f0, f1, done[i], c)
        gpu_guard(settings["gl"], t_start)
        pending = [p for p in pending if p[0] not in done]
        if not pending:
            break
        left = [p for p in batch if p[0] not in done]
        if not left:
            continue   # the batch (a part retried alone) is done: the rest go on at the video's concurrency
        if r.returncode == 0 and not getattr(r, "stalled", False):
            raise SystemExit(f"render_parts.mjs ended without finishing parts {[p[0] for p in left]}: {pdir / f'run_{n_run:02d}.log'}")
        i, f0, f1 = left[0]
        fail = re.search(rf"^FAIL {i} (.*)$", r.stdout, re.M)
        msg = fail.group(1) if fail else ("stalled: no output for 5 minutes" if getattr(r, "stalled", False) else r.stdout.strip()[-600:])
        if "kit3 " in msg:
            raise SystemExit(f"part {i} ({f0}-{f1}): a kit3 piece refused its input (fix the input, never the kit): {msg[:600]}")
        # the message names Remotion's temp copy first ("for source <TMP>\remotion-v4.0.532-assets...\0774...mp4") and the
        # real clip in "(original source = http://localhost:3000/public/v12/clips/c24_street.mp4)": the original is the one to
        # re-encode (os.link on the temp path fails); a path that isn't a public-dir clip is skipped
        lost = (re.search(r"original source\s*=\s*(\S+?)\)", msg) or re.search(r"No frame found at position \d+ for source (\S+)", msg))
        if lost:
            rel = re.sub(r"^.*?/public/", "", lost.group(1)).split("?")[0]
            from urllib.parse import unquote
            rel = unquote(rel)
            if re.match(r"^[A-Za-z]:[\\/]|^/", rel) or "remotion-v" in rel:
                say(f"{hhmm()} part {i}: the lost frame names no public-dir clip ({rel[:120]}): not re-encoded, the part again")
                rel = None
            if rel and rel not in reenc:
                reenc.add(rel)
                say(f"{hhmm()} part {i}: the compositor lost a frame of {rel}: re-encoding it, then the part again")
                if reencode_clip(v, rel, pdir):
                    continue
        tries[i] += 1
        if tries[i] >= len(STEP_DOWN) + 1:
            raise SystemExit(f"part {i} ({f0}-{f1}) failed {tries[i]} times (concurrency {conc}, then {STEP_DOWN[1:]}): {msg[:800]}")
        say(f"{hhmm()} part {i} failed ({msg[:200]}); again at concurrency {STEP_DOWN[min(tries[i], len(STEP_DOWN) - 1)] or conc} after 30 s")
        time.sleep(30)


def render_long(v, a):
    step_link(v, a)   # every file the code names linked first (a render dies on a file added after the last link)
    ver = a.version
    conc = a.concurrency or v.concurrency
    settings = render_settings(v, a)
    part_frames = int(v.section("render").get("part_frames", RENDER_DEFAULTS["part_frames"]))
    t_start = time.time()
    with RemotionJob(f"render {v.id} v{ver}" + (f" test {a.frames}" if a.frames else ""), a.wait):
        bundle = lean_bundle(v)   # one bundle for every part: no per-chunk bundling or public-dir copy
        try:
            comp = comp_info(v, bundle, settings)
            total = comp["durationInFrames"]
            if total != v.frames():
                say(f"NOTE: the composition {v.comp} is {total} frames, video.toml/beats say {v.frames()}: the composition's count is used "
                    f"(video.toml [video] frames is out of date)")
            if a.frames:   # one test range: proof of the line on a few seconds, into render/test_v<N>/
                f0, f1 = (int(x) for x in a.frames.split("-"))
                f1 = min(f1, total - 1)
                tdir = v.render_dir / f"test_v{ver}"
                tdir.mkdir(parents=True, exist_ok=True)
                render_parts(v, a, bundle, settings, [(0, f0, f1)], conc, tdir, t_start, lambda *x: None)
                out = tdir / f"frames_{f0}-{f1}.mkv"
                os.replace(tdir / "part_000.mkv", out)
                say(f"test render -> {out}: {frame_count(out)} frames (expected {f1 - f0 + 1})")
                return out
            pdir = v.render_dir / f"parts_v{ver}"
            pdir.mkdir(parents=True, exist_ok=True)
            plan = plan_parts(total, part_frames, a.chunks)
            mf = pdir / "parts.json"
            man0 = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
            old = {p["i"]: p for p in man0.get("parts", [])}
            code = __import__("gate").code_stamp(v, probe=True)
            only = {int(x) for x in a.only.split(",") if x.strip()} if a.only else set()
            redo_frames = changed_frames(v, a, plan, old)
            todo, kept = [], []
            for i, f0, f1 in plan:
                f = pdir / f"part_{i:03d}.mkv"
                o = old.get(i)
                same = o and o["f0"] == f0 and o["f1"] == f1 and o.get("settings") == settings and f.exists() and frame_count(f) == f1 - f0 + 1
                if not o and unrecorded_whole(mf, man0, f, i, f0, f1, code, settings, total):
                    old[i] = {"i": i, "f0": f0, "f1": f1, "file": str(f), "frames": f1 - f0 + 1, "settings": settings, "recovered": True,
                              "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))}
                    same = True
                    say(f"part {i}: whole on disk from the last run but never recorded (it stopped mid-batch): kept")
                hit = any(f0 <= x1 and x0 <= f1 for x0, x1 in redo_frames)
                if same and not (only and i in only) and not hit:
                    kept.append(i)
                else:
                    if f.exists():
                        f.unlink()
                    todo.append((i, f0, f1))
            say(f"{hhmm()} render {v.comp} v{ver}: {total} frames in {len(plan)} parts of ~{part_frames} (x{settings['scale']}, {settings['preset']} "
                f"crf {settings['crf']}, concurrency {conc}, {settings['imageFormat']}, parallel {settings['parallel']}); {len(kept)} kept, "
                f"{len(todo)} to render; {disk_free_gb():.0f} GB free")
            man = {"comp": v.comp, "total": total, "fps": comp["fps"], "settings": settings, "code": code,
                   "plan": [[i, f0, f1] for i, f0, f1 in plan], "parts": [old[i] for i in kept]}
            # what this render is made of (reprobe.py's snapshot: every shot's signature, every code file's hash): `render --changed`
            # and review_reels.py compare against it; a part kept from an older render keeps the older snapshot's shots it showed
            import reprobe
            (pdir / "state.json").write_text(json.dumps(reprobe.snapshot(v, total)), encoding="utf-8")
            st = v.pipe_dir / f"render_v{ver}.status.json"
            t0 = time.time()
            left = sum(f1 - f0 + 1 for _, f0, f1 in todo)
            got = [0]

            def status(i, f0, f1, secs, c):
                man["parts"] = sorted([p for p in man["parts"] if p["i"] != i] + [{"i": i, "f0": f0, "f1": f1, "file": str(pdir / f"part_{i:03d}.mkv"),
                                       "frames": f1 - f0 + 1, "secs": secs, "concurrency": c, "settings": settings,
                                       "at": time.strftime("%Y-%m-%d %H:%M:%S")}], key=lambda p: p["i"])
                mf.write_text(json.dumps(man, indent=1), encoding="utf-8")
                got[0] += f1 - f0 + 1
                rate = got[0] / max(1.0, time.time() - t0)
                st.write_text(json.dumps({"version": ver, "parts_done": len(man["parts"]), "parts": len(plan), "frames_done": got[0],
                                          "frames_todo": left, "fps": round(rate, 2), "eta_min": round((left - got[0]) / max(rate, 0.01) / 60, 1),
                                          "last": i, "at": time.strftime("%H:%M:%S")}), encoding="utf-8")
                say(f"{hhmm()} part {i} done ({f1 - f0 + 1} frames in {secs:.0f} s, {(f1 - f0 + 1) / max(secs, 0.1):.1f} fps); "
                    f"{got[0]}/{left} frames, ~{(left - got[0]) / max(rate, 0.01) / 60:.0f} min left")
            mf.write_text(json.dumps(man, indent=1), encoding="utf-8")
            if todo:
                render_parts(v, a, bundle, settings, todo, conc, pdir, t_start, status)
        finally:
            lean_clean(bundle)
        lst = pdir / "parts.txt"
        lst.write_text("".join(f"file '{(pdir / f'part_{i:03d}.mkv').as_posix()}'\n" for i, _, _ in plan), encoding="utf-8")
        tmp = v.render_dir / f"v{ver}_picture.tmp.mkv"
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", tmp], quiet=True)
        n = frame_count(tmp)
        if n != total:
            raise SystemExit(f"joined picture has {n} frames, the composition {total}: left as {tmp}")
        final = safe_replace(tmp, v.render_dir / f"v{ver}_picture.mkv")
        kv = ffprobe(final)
        mins = (time.time() - t_start) / 60
        (v.render_dir / f"v{ver}_picture.done.json").write_text(json.dumps(
            {"picture": str(final), "frames": n, "width": kv.get("width"), "height": kv.get("height"), "parts": len(plan), "rendered": len(todo),
             "kept": len(kept), "minutes": round(mins, 1), "settings": settings, "code": man["code"], "at": time.strftime("%Y-%m-%d %H:%M")}, indent=1),
            encoding="utf-8")
        say(f"RENDER DONE -> {final} ({n} frames, {kv.get('width')}x{kv.get('height')}; {len(todo)} parts rendered, {len(kept)} kept, {mins:.0f} min)")
    # the render scan runs on every full render: some faults exist only in the real picture (a delayRender black frame, a black frame
    # in the finished 4K, a render-time freeze); --no-scan or [render] scan = false skips it
    if not getattr(a, "no_scan", False) and v.section("render").get("scan", True):
        scan_render(v, ver, man, total)
    return final


def scan_render(v, ver, man, total):
    """the render scan on the real picture (qa_render_scan.py): black dips, stray frames and render-time freezes the probe can't see,
    read against the gate's probe; ~11-16 min for 52 min of film (its frame measures are read back while the parts are unchanged). Flags
    stop the line (exit 1) before anything goes to the creator; the picture stays."""
    import qa_render_scan
    out = v.pipe_dir / f"render_scan_v{ver}"
    parts = sorted(man["parts"], key=lambda p: p["f0"])
    pieces = [(p["file"], p["f0"]) for p in parts]
    probe = v.pipe_dir / "gate" / "probe.jsonl"
    say(f"{hhmm()} render scan ({len(pieces)} parts) ...")
    flags = qa_render_scan.scan(pieces, probe if probe.exists() else None, out, v.fps, v.pub, expected=[p["frames"] for p in parts])
    qa_render_scan.write_report(flags, out, [f"{v.id} v{ver}: {total} frames in {len(parts)} parts, probe {probe if probe.exists() else 'none'}"])
    if flags:
        for f in flags[:20]:
            say(f"  {f['check']} {mmss(f['at'] / v.fps)} (frame {f['at']}): {f['what'][:160]}")
        raise SystemExit(f"RENDER SCAN: {len(flags)} flag(s) on the real picture -> {out / 'render_scan.md'} (strips beside it): fix and patch "
                         f"before it goes to the creator")
    say(f"{hhmm()} render scan: clean")


def changed_frames(v, a, plan, old):
    """--changed: the frame ranges whose shots changed since the parts were rendered (reprobe.py's change map from the code stamp the
    parts were made on): only those parts render again. [] without --changed."""
    if not getattr(a, "changed", False) or not old:
        return []
    import reprobe
    rng = reprobe.changed_ranges(v, since="render", version=a.version)
    say(f"--changed: {len(rng)} changed frame ranges since the parts were rendered")
    return rng


def render_short(v, a):
    ver = a.version
    v.render_dir.mkdir(parents=True, exist_ok=True)
    out = v.render_dir / f"p{v.id}_v{ver}_render.mp4"
    log = v.pipe_dir / f"render_v{ver}.log"
    frames = tuple(int(x) for x in a.frames.split("-")) if a.frames else None
    if frames:
        out = v.render_dir / f"test_v{ver}" / f"frames_{frames[0]}-{frames[1]}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
    conc = a.concurrency or v.section("render").get("concurrency")   # unset: remotion.config's default (6)
    cmd = [NPX, "remotion", "render", os.environ.get("QA_ENTRY") or "src/index.ts", v.comp, str(out), f"--public-dir={v.pub.as_posix()}", "--muted"]
    if frames:
        cmd.append(f"--frames={frames[0]}-{frames[1]}")
    if conc:
        cmd.append(f"--concurrency={conc}")
    cmd.append(f"--gl={a.gl or v.gl}")
    with RemotionJob(f"render {v.id} v{ver}", a.wait):
        say(f"{hhmm()} render {v.comp} -> {out.name} ...")
        r = render_with_retry(cmd, out, log)
    if not rescue_in_progress(out, log) or (r.returncode and not out.exists()):
        raise SystemExit(f"render failed (exit {r.returncode}): {log}")
    n = frame_count(out)
    expect = (frames[1] - frames[0] + 1) if frames else v.frames()
    say(f"{hhmm()} render -> {out}: {n} frames (expected {expect})")
    if n != expect:
        raise SystemExit("the render's frame count is off")
    return out


def step_gate(v, a):
    if v.kind == "long":
        need_stage(v, a, "voice", inclusive=True)
    step_link(v, a)   # every file the code names linked first (a render dies on a file added after the last link)
    import gate
    if getattr(a, "scope", None):   # the scoped gate: a builder's or fixer's own shots, never a pass (gate.step_scope)
        return gate.step_scope(v, a)
    return gate.step_gate(v, a)


def gate_passed(v, a):
    """A full render starts only on code the gate passed (gate.py writes the code's stamp to pipeline/gate/passed.txt);
    --frames test renders are exempt. --skip-gate exists for the creator's explicit word only."""
    if a.frames or getattr(a, "skip_gate", False):   # a Short is gated too (shots from the probe)
        return
    import gate
    p = v.pipe_dir / "gate" / "passed.txt"
    stamp = gate.code_stamp(v)
    if not p.exists() or p.read_text(encoding="utf-8").strip() != stamp:
        raise SystemExit(f"render refused: the gate hasn't passed on this code (stamp {stamp}). Run `pipe.py {v.slug} gate` first.")


def step_render(v, a):
    if not a.frames:   # a full render (a --frames test is exempt)
        need_stage(v, a, "render")
    voice_verify(v, "render")
    gate_passed(v, a)
    return render_short(v, a) if v.kind == "short" else render_long(v, a)


# ================================================================================================================================ patch
def step_patch(v, a):
    """Re-render frame ranges as segments with one bundle (segs.mjs); `finish --patches <json>` lays them over the picture."""
    if not a.ranges:
        raise SystemExit("patch: --ranges 1000-1240,5000-5400 (frames)")
    voice_verify(v, "patch")
    step_link(v, a)   # every file the code names linked first (a render dies on a file added after the last link)
    ver = a.version
    out = v.render_dir / f"patches_v{ver}"
    out.mkdir(parents=True, exist_ok=True)
    ranges = [r.strip() for r in a.ranges.split(",") if r.strip()]
    scale = a.scale or v.scale
    with RemotionJob(f"patch {v.id} v{ver} ({len(ranges)} segments)", a.wait):
        r = run([NODE, "segs.mjs", out, str(scale), *ranges], cwd=MOTION, env={"QA_COMP": v.comp, "QA_PUBLIC": v.pub.as_posix(), **temp_env()},
                log=v.pipe_dir / f"patch_v{ver}.log")
    segs = []
    for ln in r.stdout.splitlines():
        m = re.match(r"(.+\.mkv)@([\d.]+)$", ln.strip())
        if m:
            segs.append({"file": m.group(1), "at": float(m.group(2))})
    for s in segs:
        n = frame_count(s["file"])
        say(f"segment {Path(s['file']).name}: {n} frames at {s['at']:.3f} s")
    pj = out / "patches.json"
    old = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else []
    byfile = {p["file"]: p for p in old}
    for s in segs:
        byfile[s["file"]] = s
    pj.write_text(json.dumps(sorted(byfile.values(), key=lambda p: p["at"]), indent=1), encoding="utf-8")
    say(f"{len(segs)} segment(s) -> {pj} ({len(byfile)} in all); apply with: pipe.py {v.id} finish --version {ver} --patches {pj}")


# ================================================================================================================================ score
def step_score(v, a):
    voice_verify(v, "score")
    S = v.section("score")
    cues = v.folder / S["cues"]
    if not cues.exists():
        raise SystemExit(f"{cues} is missing (video.toml [score] cues)")
    out = Path(a.out) if a.out else (v.dj / "build" / "score" / f"mix_v{a.version}.wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [PY_EDIT, SOUND / "score.py", cues, out] + (["--picture", a.picture] if a.picture else [])
    say(f"{hhmm()} score: {cues.name} -> {out.name} ...")
    with HeavyJob(f"score {v.id} v{a.version}", "score", a.wait):
        r = run(cmd, log=v.pipe_dir / f"score_v{a.version}.log")
    keep = [ln for ln in r.stdout.splitlines() if re.search(r"LUFS|voice.music|silence|WARN|dBTP|400Hz|overlap|handoff", ln, re.I)]
    print("\n".join(keep[-25:]))
    say(f"score -> {out} (full report: {v.pipe_dir / f'score_v{a.version}.log'})")
    score_checks(v, out, r.stdout)
    return out


VOICE_OVER_MUSIC_MIN = 20.5   # dB; ~22 dB voice over music in speech for long form (Shorts ~17-18)


def score_checks(v, out, report):
    """Two faults the gate's sound half can let through, refused here so a mix can't reach a review copy with them: (1) a cue sheet
    without the prototype's mix block (GAP_MIN 22, carve, tame) leaves every bed 16.5-19 dB under the voice; a long video's beds must
    read >= VOICE_OVER_MUSIC_MIN in score.py's own "voice-music" column; (2) a mix that runs past the picture (the cue sheet's DURATION
    counting the voice file's silence after the last word, which the composition doesn't): the mix must be as long as the composition
    (video.toml frames, which the render's frame count must match) within 0.1 s."""
    errs = []
    if v.kind == "long":
        low = [(m.group(1), float(m.group(2))) for m in re.finditer(r"^\s*(\S+)\s+[\d.]+-\s*[\d.]+\s+.*?voice-music\s+(-?[\d.]+) dB", report, re.M)]
        low = [(cid, vm) for cid, vm in low if vm < VOICE_OVER_MUSIC_MIN]
        if low:
            errs.append(f"voice over music under {VOICE_OVER_MUSIC_MIN} dB (~22 wanted) in {len(low)} bed(s): "
                        + ", ".join(f"{c} {x:.1f}" for c, x in low[:8]) + " (the cue sheet's GAP_MIN 22 / CARVE_DB 8 / UNDER 13 block?)")
    md = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                              capture_output=True, text=True).stdout.strip() or 0)
    pd = v.frames() / v.fps
    if abs(md - pd) > 0.1:
        errs.append(f"the mix runs {md:.2f} s, the composition {pd:.2f} s (video.toml frames {v.frames()}): the cue sheet's DURATION "
                    f"must be the picture's (the last word's end + the tail, as the composition counts it)")
    if errs:
        raise SystemExit("score refused:\n  " + "\n  ".join(errs))


# ================================================================================================================================== srt
def names_as_written(v, cues):
    """Every names.json name in the subtitles as the script writes it (the fix finish_short.py makes in a Short's captions, for the long
    form's .srt, which holds the same heard words: Whisper writes a name as it hears it, "3D" for a brand written ThreeDee, "BLUE WAVE" for
    BlueWave). Whisper's words (build/captions/words.json) against the script's
    (src/<src>/words.json), beat by beat: where they differ and the script's side holds a names.json name, the cue takes the script's
    words. Everything else keeps Whisper's writing; [srt] fixes still apply first."""
    import difflib
    n_ = lambda s: re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "'").replace("'", ""))
    bare = lambda s: re.sub(r"['’]s$", "", s.strip(",.?!:;\"“”()"))
    try:
        heard = json.loads((v.dj / "build" / "captions" / "words.json").read_text(encoding="utf-8"))["words"]
        script = json.loads(v.words().read_text(encoding="utf-8"))
        names = {n_(k) for k in json.loads((SOUND / "names.json").read_text(encoding="utf-8"))["names"]}
    except (OSError, KeyError, ValueError) as e:
        say(f"names as written: skipped ({type(e).__name__}: {e})")
        return cues
    cues, fixed, missed = list(cues), 0, []
    for bt in dict.fromkeys(x["beat"] for x in heard):
        H = [x for x in heard if x["beat"] == bt]
        S = [x["w"] for x in script if x["beat"] == bt]
        sm = difflib.SequenceMatcher(a=[n_(t) for t in S], b=[n_(x["w"]) for x in H], autojunk=False)
        for op, a0, a1, b0, b1 in sm.get_opcodes():
            toks = [bare(t) for t in S[a0:a1]]
            if op != "replace" or not (any(n_(t) in names for t in toks) or n_(" ".join(toks)) in names):
                continue
            seg = H[b0:b1]
            t0, t1 = seg[0]["start"], seg[-1]["end"]
            pat = r"\s+".join(re.escape(bare(x["w"])) for x in seg if bare(x["w"]))
            for k, (a_, b_, t) in enumerate(cues):
                if a_ - 0.02 <= t0 and t1 <= b_ + 0.02 and pat and re.search(pat, t, re.I):
                    cues[k] = (a_, b_, re.sub(pat, " ".join(toks), t, count=1, flags=re.I))
                    fixed += 1
                    say(f"names as written: {' '.join(x['w'] for x in seg)} -> {' '.join(toks)} at {t0:.2f}")
                    break
            else:
                missed.append(f"{' '.join(x['w'] for x in seg)} -> {' '.join(toks)} at {t0:.2f}")
    if missed:
        say(f"names as written: {len(missed)} not placed (across two cues?): add them to [srt] fixes: {missed}")
    return cues


def write_srt(v, out, loose=False, captions=None):
    """The upload subtitles: the captions' srt (`python -m dj captions`: Whisper on the final voice) with the [srt] fixes applied, each
    one checked to still apply (a stale fix means a new voice: look), plus the real voices' lines in the holds as "Name: line" cues at their times in the picture."""
    S = v.section("srt")
    # an empty `captions = ""` (a new video.toml's template) means the default too (read as a path, "" would be the video folder)
    srt = Path(captions) if captions else v.dj / (S.get("captions") or "build/captions/captions.srt")
    if not srt.exists():
        raise SystemExit(f"{srt} is missing: run `python -m dj captions` on the final voice first")
    beats = {b["id"]: b for b in v.beats()["beats"]}
    text = srt.read_text(encoding="utf-8")
    stale = []
    for a_, b_ in S.get("fixes", []):
        if a_ not in text:
            stale.append(a_)
        text = text.replace(a_, b_)
    if stale:
        say(f"{len(stale)} fix(es) no longer apply (a new voice? check the captions): {stale}")
        if not loose:
            raise SystemExit("srt: stale fixes (run with --loose to write the file anyway)")

    def sec(s):
        h, m, r = s.split(":")
        return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))

    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = re.match(r"(\S+) --> (\S+)", lines[1])
        if m:
            cues.append((sec(m.group(1)), sec(m.group(2)), "\n".join(lines[2:])))
    if not captions:
        cues = names_as_written(v, cues)
    holds = S.get("holds", [])
    for beat, a_, b_, line in holds:
        if beat not in beats:
            raise SystemExit(f"srt: hold beat {beat} is not in {v.src_dir / 'beats.json'}")
        cues.append((beats[beat]["start"] + a_, beats[beat]["start"] + b_, line))
    cues.sort(key=lambda c: c[0])
    # a cue lingers into the pause after it (up to 0.6 s, never into the next cue; the last one 0.8 s, inside the film): Whisper ends a
    # sentence's tail on its last word, so a one-word cue would flash for under 0.2 s
    end = v.duration()
    for i, (a_, b_, t) in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else end - 0.3
        cues[i] = (a_, max(b_, min(b_ + (0.6 if i + 1 < len(cues) else 0.8), nxt)), t)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(f"{i}\n{ts(a_)} --> {ts(b_)}\n{t}\n" for i, (a_, b_, t) in enumerate(cues, 1)), encoding="utf-8")
    say(f"{len(cues)} cues ({len(holds)} lines in holds) -> {out}")
    return out


def step_srt(v, a):
    out = Path(a.out) if a.out else v.export_dir / f"{v.export_name(a.version)}.srt"
    return write_srt(v, out, a.loose, a.captions)


# =============================================================================================================================== finish
def finish_long(v, a):
    ver = a.version
    S, F = v.section("score"), v.section("finish")
    picture = Path(a.picture) if a.picture else v.render_dir / f"v{ver}_picture.mkv"
    mix = Path(a.mix) if a.mix else (v.dj / "build" / "score" / f"mix_v{ver}.wav" if (v.dj / "build" / "score" / f"mix_v{ver}.wav").exists()
                                     else v.dj / S.get("mix", f"build/score/mix_v{ver}.wav"))
    if not picture.exists():
        raise SystemExit(f"{picture} is missing: render first")
    if not mix.exists():
        raise SystemExit(f"{mix} is missing: `pipe score` first, or --mix <file>")
    if not a.picture and not a.test:   # a failed render can leave the last version's picture under this name
        n = frame_count(picture)
        if n != v.frames():
            raise SystemExit(f"{picture} has {n} frames, the composition {v.frames()}: an older render's picture; render first")
    if not a.test:   # an older mix left under this name is told apart by its length
        md = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mix)],
                                  capture_output=True, text=True).stdout.strip() or 0)
        pd = v.frames() / v.fps
        if abs(md - pd) > 0.5:
            raise SystemExit(f"{mix} runs {md:.2f} s, the picture {pd:.2f} s: another version's mix; `pipe score` or --mix <file>")
    v.export_dir.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else v.export_dir / f"{v.export_name(ver)}.mp4"   # --out: the 4K beside a 1440p review copy of the same name
    mux = v.render_dir / f"v{ver}_mux.mkv"
    if not a.test:   # the srt needs nothing the encode makes, so it goes first: a stale [srt] path fails in seconds, not after the 25-min encode
        write_srt(v, v.export_dir / f"{v.export_name(ver)}.srt", a.loose)
        import chapters   # the upload pack's chapters from the final timing (chapters.json), never by hand
        if chapters.run(v, write=True, say=say) is None:
            say("chapters: no chapters.json (titles + each chapter's beat): post.md's chapters are not checked")
    if a.test:   # the whole chain on a few seconds: proof before the 25-minute 4K encode
        t0, t1 = (float(x) for x in a.test.split("-"))
        tdir = v.render_dir / f"test_v{ver}"
        tdir.mkdir(parents=True, exist_ok=True)
        pic_cut, mix_cut = tdir / f"pic_{t0:g}-{t1:g}.mkv", tdir / f"mix_{t0:g}-{t1:g}.wav"
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t0}", "-to", f"{t1}", "-i", picture, "-c", "copy", pic_cut], quiet=True)
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t0}", "-to", f"{t1}", "-i", mix, "-c:a", "pcm_s16le", mix_cut], quiet=True)
        picture, mix, mux, out = pic_cut, mix_cut, tdir / f"mux_{t0:g}-{t1:g}.mkv", tdir / f"{v.export_name(ver)}_test_{t0:g}-{t1:g}.mp4"
    say(f"{hhmm()} mux {picture.name} + {mix.name} -> {mux.name}")
    run([FFMPEG, "-v", "error", "-y", "-i", picture, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", mux], quiet=True)
    cmd = [PY_PIPE, MOTION / "finish_long.py", mux, out] + (["--gpu"] if F.get("gpu", True) else []) + list(F.get("args", []))
    if a.video_from:
        cmd += ["--video-from", a.video_from]
    if a.patches:
        t_shift = float(a.test.split("-")[0]) if a.test else 0.0   # in a --test cut the picture starts at t0: a patch at 60.0 s lands at 60.0 - t0
        for p in json.loads(Path(a.patches).read_text(encoding="utf-8")):
            at = p["at"] - t_shift
            if a.test and not (0 <= at < float(a.test.split("-")[1]) - t_shift):
                continue
            cmd += ["--patch", f"{p['file']}@{at:.6f}"]
    say(f"{hhmm()} finish_long -> {out.name} ...")
    with HeavyJob(f"finish {v.id} v{ver}{' test' if a.test else ''}", "finish", a.wait):
        r = run(cmd, cwd=MOTION, log=v.pipe_dir / f"finish_v{ver}{'_test' if a.test else ''}.log")
    print("\n".join(ln for ln in r.stdout.splitlines() if re.search(r"LUFS|patch|WARNING|gain|out:", ln)))
    say(f"{hhmm()} finish done -> {out}")
    if not a.test:
        # the render scan reads the real picture against the gate's probe and already catches a render-time hold; the probe-blind
        # stutter heuristic adds only false flags beside it (stills settling before a cut, a designed freeze before a zoom). It runs only
        # on a picture the scan did not pass.
        rs = v.pipe_dir / f"render_scan_v{ver}" / "render_scan.md"
        scanned = (not a.picture and rs.exists() and rs.stat().st_mtime >= picture.stat().st_mtime
                   and rs.read_text(encoding="utf-8").startswith("# Render scan: PASS"))
        if scanned:
            say("stutter check: skipped, the render scan passed this picture")
        elif not a.no_stutter:
            say(f"{hhmm()} stutter check on the picture ...")
            r = run([PY_PIPE, MOTION / "qa_cadence.py", "--stutter", picture], cwd=MOTION, check=False, log=v.pipe_dir / f"stutter_v{ver}.log")
            print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)")
    kv = ffprobe(out)
    lu, tp = loudness(out)
    say(f"{out.name}: {kv.get('width')}x{kv.get('height')} {kv.get('r_frame_rate')} fps, {float(kv.get('duration', 0)):.2f} s, {lu} LUFS, peak {tp} dBFS")
    return out


def finish_short(v, a):
    """A Short's finish: the captions burned in (finish_short.py), the sound (score.py with the video's cues), the QA (qa_render,
    qa_holds) and a 2-fps contact sheet. ffmpeg and Python only: it can run while the next video renders."""
    ver = a.version
    name = v.export_name(ver)
    render = Path(a.picture) if a.picture else v.render_dir / f"p{v.id}_v{ver}_render.mp4"
    if not render.exists():
        raise SystemExit(f"{render} is missing: render first")
    say(f"{hhmm()} captions in: finish_short.py {v.slug} {render.name} {name} --picture-only")
    r = run([PY_PIPE, MOTION / "finish_short.py", v.slug, render, name, "--picture-only"], cwd=REPO, log=v.pipe_dir / f"finish_short_v{ver}.log")
    print(r.stdout.strip().splitlines()[-1])
    picture = v.dj / "build" / f"{name}_picture.mp4"
    cues = v.folder / v.section("score")["cues"]
    out = v.export_dir / f"{name}.mp4"
    v.export_dir.mkdir(parents=True, exist_ok=True)
    say(f"{hhmm()} score: {cues.name} -> {out.name}")
    r = run([PY_EDIT, SOUND / "score.py", cues, out, "--picture", picture], cwd=REPO, log=v.pipe_dir / f"score_v{ver}.log")
    print("\n".join(ln for ln in r.stdout.splitlines() if re.search(r"LUFS|gap|voice|WARN|rror", ln))[-1500:])
    qa_dir = v.export_dir / f"qa_{name}"
    r = run([PY_EDIT, QA_TOOLS / "qa_render.py", out, "--format", "short", "--words", v.words(), "--voice", v.dj / "build" / "voice" / "narration.wav",
             "--out", qa_dir] + (["--allow", v.section("qa")["allow"]] if v.section("qa").get("allow") else []), cwd=REPO, check=False,
            log=v.pipe_dir / f"qa_render_v{ver}.log")
    print("\n".join(ln for ln in r.stdout.splitlines() if re.search(r"FAIL|WARN|flash|freeze|LUFS|peak|tail|first", ln))[:2000])
    r = run([PY_PIPE, MOTION / "qa_holds.py", out], cwd=REPO, check=False)
    print("\n".join(r.stdout.strip().splitlines()[-2:]))
    sheet = v.pipe_dir / f"sheet_{name}.jpg"
    run([FFMPEG, "-v", "error", "-y", "-i", out, "-vf", "fps=2,scale=135:240,tile=12x10", "-frames:v", "1", sheet], quiet=True)
    lu, tp = loudness(out)
    kv = ffprobe(out)
    say(f"{hhmm()} {name} finished -> {out} ({float(kv.get('duration', 0)):.2f} s, {lu} LUFS, peak {tp} dBFS; sheet {sheet})")
    return out


def step_finish(v, a):
    voice_verify(v, "finish")
    return finish_short(v, a) if v.kind == "short" else finish_long(v, a)


# =================================================================================================================================== qa
def step_qa(v, a):
    from qa_gate import run_gate   # the QA gate lives in its own module
    return run_gate(v, a)


# ================================================================================================================================== all
def step_all(v, a):
    step_link(v, a)
    step_audit(v, a)
    step_render(v, a)
    step_finish(v, a)
    step_qa(v, a)


# ================================================================================================================================ plays
def step_plays(v, a):
    """Every clip play's first, middle and last frame on sheets for the eye (plays_sheet.py): a play can open on a rating card or an
    end card for over a second, and neither the edge scan nor the proof stills look at it. Run after the audit, before the render."""
    from plays_sheet import make_sheets, report
    rep = audit_report(v, tag="plays")
    out = Path(a.out) if a.out else v.pipe_dir / f"plays_v{a.version}"
    flags = make_sheets(rep["plays"], [v.pub, PUBLIC], out)
    print(report(flags, out))
    say(f"read every sheet in {out}: each play shows what its words say, no rating card, black, end card or stray logo")


# ============================================================================================================== stages and the voice lock
def need_stage(v, a, stage, inclusive=False):
    """tools/workflow/stages.py: a step that costs hours runs only after what shapes it is settled. `render` needs the prototype (unless
    creator/choices.toml says prototype_first = false), the locked voice and the picture; `gate` needs the voice (inclusive: the voice stage itself). --no-stages skips the check."""
    if getattr(a, "no_stages", False):
        say(f"stages: skipped for {stage} (--no-stages)")
        return
    sys.path.insert(0, str(WORKFLOW))
    import stages
    d = v.folder
    miss = stages.missing_for(d, stage)
    if inclusive:
        k = stages.state(d, stages.load(d), stage, stages.script_hash(d))
        if k != "ok":
            miss.append((stage, k))
    if miss:
        raise SystemExit(f"{v.slug}: '{stage}' needs " + ", ".join(f"{n} ({k})" for n, k in miss)
                         + f"  [stages.py {v.slug} status; --no-stages skips the check]")


def voice_verify(v, step):
    """the voice lock (standard/VOICE_LOCK.md): when videos/<video>/voice_lock.json exists, its narration and word files must still
    hash as locked before a render, a patch, a mix or a finish (a changed voice under an old picture puts every later fix on the wrong
    words)"""
    if not (v.folder / "voice_lock.json").exists():
        return
    r = run([PY_EDIT, VOICE / "voice_lock.py", v.slug, "verify"], check=False, quiet=True)
    if r.returncode != 0:
        raise SystemExit(f"{step} refused: the voice lock doesn't verify (voice_lock.py {v.slug} verify):\n{r.stdout.strip()[-1200:]}")
    say(f"voice lock: verified ({step})")


def step_voice(v, a):
    """the voice in one step (standard/VOICE_LOCK.md): voice_ready.py require (every stage the voice needs, names measured), then the
    voice chain (tools/sound/voice_chain.sh: takes, the chain, the sound gate), then the lock with the gate's PASS as its note"""
    r = run([PY_EDIT, VOICE / "voice_ready.py", v.slug, "require"], check=False, log=v.pipe_dir / "voice_ready.log")
    print(r.stdout.strip()[-1500:])
    if r.returncode != 0:
        raise SystemExit("voice: not ready (voice_ready.py require)")
    say(f"{hhmm()} voice chain ...")
    r = run(["bash", SOUND / "voice_chain.sh", v.slug], check=False, log=v.pipe_dir / "voice_chain.log")
    print("\n".join(r.stdout.strip().splitlines()[-25:]))
    if r.returncode != 0:
        raise SystemExit(f"voice: the chain failed (exit {r.returncode}): {v.pipe_dir / 'voice_chain.log'}")
    passed = re.findall(r"SOUND GATE PASS[^\n]*", r.stdout)
    if not passed:
        raise SystemExit("voice: the chain ended without the sound gate's PASS: no lock")
    r = run([PY_EDIT, VOICE / "voice_lock.py", v.slug, "lock", "--note", passed[-1][:300]], check=False)
    print(r.stdout.strip()[-800:])
    if r.returncode != 0:
        raise SystemExit("voice: the lock failed")
    say(f"{hhmm()} voice locked: {passed[-1][:120]}")


STEPS = {"script": step_script, "voice": step_voice, "link": step_link, "audit": step_audit, "gate": step_gate, "stills": step_stills,
         "render": step_render, "patch": step_patch, "score": step_score, "finish": step_finish, "srt": step_srt, "qa": step_qa,
         "plays": step_plays, "all": step_all}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("step", choices=sorted(STEPS))
    ap.add_argument("--version", "-v", default=None, help="the version number in file names (parts_v<N>, <name>_v<N>.mp4) "
                    "[render: 1; the other steps: the newest render/v<N>_picture.mkv, else 1]")
    ap.add_argument("--wait", type=float, default=None, help="minutes to wait for a free Remotion before giving up [wait as long as it takes]")
    ap.add_argument("--frames", help="render/stills: a frame range a-b (render) or a list 1,2,3 (stills)")
    ap.add_argument("--only", help="render: redo these parts, 3,4 (the others are kept when whole)")
    ap.add_argument("--no-scan", action="store_true", help="render: skip the render scan on the real picture (qa_render_scan.py; on by default)")
    ap.add_argument("--changed", action="store_true", help="render: redo only the parts whose shots changed since they were rendered (reprobe.py's change map)")
    ap.add_argument("--chunks", type=int)
    ap.add_argument("--concurrency", type=int)
    ap.add_argument("--scale", type=float)
    ap.add_argument("--gl", help="render: angle (the GPU, the default) or swangle (software)")
    ap.add_argument("--shots", help="stills: shot indexes 3,4 (one still each)")
    ap.add_argument("--every", action="store_true", help="stills: one still per shot")
    ap.add_argument("--ends", action="store_true", help="stills: also each shot's last frame (a graphic's end state)")
    ap.add_argument("--offset", type=float, default=0.5, help="stills: seconds into each shot [0.5]")
    ap.add_argument("--sheet", action="store_true", help="stills: also tile them into one sheet")
    ap.add_argument("--out", help="stills/score/srt/plays: the output path; gate --scope: the report [pipeline/gate_scope.md]")
    ap.add_argument("--ranges", help="patch: frame ranges a-b,c-d")
    ap.add_argument("--patches", help="finish: a patches.json from `pipe patch` to lay over the picture")
    ap.add_argument("--picture", help="finish/score: the picture file (default render/v<N>_picture.mkv or render/p<id>_v<N>_render.mp4)")
    ap.add_argument("--mix", help="finish: the mix wav (default build/score/mix_v<N>.wav, else video.toml [score] mix)")
    ap.add_argument("--video-from", help="finish: redo only the sound onto this delivered mp4's picture")
    ap.add_argument("--test", help="finish: run the chain on seconds a-b of the picture and mix only, into render/test_v<N>/")
    ap.add_argument("--no-stutter", action="store_true", help="finish: skip qa_cadence --stutter")
    ap.add_argument("--no-edges", action="store_true", help="audit: skip the source-cut edge scan")
    ap.add_argument("--reuse", action="store_true", help="gate: reuse the last probe when the code is unchanged")
    ap.add_argument("--full", action="store_true", help="gate: a full probe (default: incremental and shift-aware when a snapshot exists, reprobe.py)")
    ap.add_argument("--reprobe", help="gate: probe only these frame ranges (a-b,c-d) and splice them into the last full probe (fixes inside section shots only; see gate.reprobe)")
    ap.add_argument("--scope", help="gate: the scoped gate, a builder's or fixer's own loop: probe and check only these frame ranges "
                    "(a-b,c-d, each widened to the whole shots it touches) against the last full probe, and report the flags inside them "
                    "(pipeline/gate_scope.md, or --out); never stamps the gate, no sound or coherency half (see gate.step_scope)")
    ap.add_argument("--skip-gate", action="store_true", help="render: start without a passed gate (the creator's explicit word only)")
    ap.add_argument("--no-stages", action="store_true", help="render/gate: skip the stages check (tools/workflow/stages.py)")
    ap.add_argument("--soft", action="store_true", help="audit: report, don't fail")
    ap.add_argument("--force", action="store_true", help="script: go on past fix-level flags")
    ap.add_argument("--ignore", help="script: lint --ignore ids")
    ap.add_argument("--loose", action="store_true", help="srt/finish: write the srt even when a fix no longer applies")
    ap.add_argument("--captions", help="srt: another captions.srt")
    ap.add_argument("--list-extra", action="store_true", help="link: list files in the public dir the sources don't name")
    ap.add_argument("--deep", action="store_true", help="qa: also the whole-film flash scan (minutes per 10 minutes of 4K)")
    ap.add_argument("--export", help="qa: the finished file to check (default export/<name>_v<N>.mp4)")
    a = ap.parse_args()
    if getattr(a, "scale", None):
        h = round(1080 * a.scale / 2) * 2
        if abs(1080 * a.scale - h) > 1e-9:
            say(f"--scale {a.scale}: 1080 x scale = {1080 * a.scale:.3f} px, snapped to {h} px ({h / 1080!r})")
            a.scale = h / 1080
    v = Video(find_video(a.video))
    v.pipe_dir.mkdir(parents=True, exist_ok=True)
    if a.version is None:
        # a step that reads a render takes the newest picture's version (by its date, not its number: prototype pictures can carry
        # higher numbers than the real render), so `score` and `srt` never write one version's work under another's name; `render`
        # alone starts at 1
        vs = sorted((p.stat().st_mtime, m.group(1)) for p in v.render_dir.glob("v*_picture.mkv")
                    if (m := re.match(r"v(\d+)_picture\.mkv$", p.name)))
        a.version = vs[-1][1] if vs and a.step != "render" else "1"
    say(f"{v} step {a.step} v{a.version}")
    STEPS[a.step](v, a)


if __name__ == "__main__":
    main()
