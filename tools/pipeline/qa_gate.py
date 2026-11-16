"""The QA gate: `pipe.py <video> qa` runs every check we have on a finished video and writes one report, videos/<video>/QA_v<N>.md
(pass/fail per check, the numbers, and the delivery checklist with the eye checks that no tool can do), plus the same as JSON in the
video's media folder (VIDEOS/<video>/pipeline/). Exit 1 when any check FAILs. Each check names the rule it stands for; a WARN is a
filter's flag to look at (a sheet is written), never a verdict.

Long form (standard/LONG_FORM.md, its delivery checks): the file's shape (4K60, the composition's length), loudness (-14 +/- 0.5 LUFS,
true peak at most -1 dBTP), tools/qa/qa_render.py (flash shots, freezes, holds, repeats, bars, loudness), the static clip audit
(overruns, shots under 0.5 s, clips under 1.0x, files missing from clipdurs.json), both edges of every clip against its source's cuts,
`rate={0.` in the code, broken characters in the code, the card cameras (qa_camera.mjs: 0 two-move cards), the stutter check on the
picture (qa_cadence.py --stutter), short black frames, the subtitles (present, inside the length), the reuse check against the last
videos (reuse_check.py, when the tool is there), the score's report (voice over music 20.5-24 dB, no silence outside the designed ones,
effects' level and mood), and, with --deep, the whole-film flash scan (qa_flash_scan.py). Shorts (standard/SHORTS.md): the shape
(1080x1920, 60 fps, the timeline's length, the end 0.15-0.8 s after the last word), loudness, qa_render --format short with the voice,
qa_holds (nothing over 2.6 s without a change), the word sheet and a 2-fps sheet for the eye, the reuse check, the score's report
(voice over music 16-19.5 dB). Both: no headless browser left behind."""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FFMPEG, HEADLESS, MOTION, NODE, PY_EDIT, PY_PIPE, QA_TOOLS, REPO, ffprobe, loudness, processes, run, say  # noqa: E402

sys.path.append(str(MOTION))
from codefiles import code_files  # noqa: E402   a video's code with the subfolder files it imports

PASS, FAIL, WARN, SKIP, INFO = "PASS", "FAIL", "WARN", "SKIP", "INFO"


class Gate:
    def __init__(self, v, version):
        self.v, self.version, self.checks = v, version, []

    def add(self, name, status, detail, source=""):
        self.checks.append({"check": name, "status": status, "detail": detail, "source": source})
        say(f"  [{status:4s}] {name}: {detail}")

    def fails(self):
        return [c for c in self.checks if c["status"] == FAIL]


def tail(text, n=1):
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return " | ".join(lines[-n:]) if lines else "(no output)"


# -------------------------------------------------------------------------------------------------------------------------- shared checks
def check_shape(g, export, want_w, want_h, want_dur, tol=1.0):
    kv = ffprobe(export)
    w, h, fr = kv.get("width"), kv.get("height"), kv.get("r_frame_rate", "")
    dur = float(kv.get("duration", 0) or 0)
    ok = (w, h) == (str(want_w), str(want_h)) and fr.startswith("60") and abs(dur - want_dur) <= tol
    g.add("file shape", PASS if ok else FAIL, f"{w}x{h} {fr} fps, {dur:.2f} s (the composition: {want_dur:.2f} s)",
          "finish_long.py 4K60 / Root.tsx 1080x1920; the length is the timeline's")
    return dur


def check_loudness(g, export, target=-14.0, tol=0.5):
    lu, tp = loudness(export)
    if lu is None:
        g.add("loudness", FAIL, "ffmpeg could not measure the sound", "")
        return
    ok = abs(lu - target) <= tol and tp is not None and tp <= -1.0
    g.add("loudness", PASS if ok else FAIL, f"{lu:.1f} LUFS (target {target:g} +/- {tol}), true peak {tp} dBTP (max -1.0)", "standard/SOUND_AND_VOICE.md")


def check_qa_render(g, v, export, fmt, voice=None):
    out = v.pipe_dir / f"qa_render_v{g.version}"
    cmd = [PY_EDIT, QA_TOOLS / "qa_render.py", export, "--format", fmt, "--words", v.words(), "--out", out]
    if voice and Path(voice).exists():
        cmd += ["--voice", voice]
    allow = v.section("qa").get("allow")
    if allow:
        cmd += ["--allow", allow]
    r = run(cmd, cwd=REPO, check=False, log=v.pipe_dir / f"qa_render_v{g.version}.log")
    text = (out / "qa.md").read_text(encoding="utf-8") if (out / "qa.md").exists() else r.stdout
    fails = [ln for ln in text.splitlines() if "FAIL" in ln]
    warns = [ln for ln in text.splitlines() if "WARN" in ln]
    status = FAIL if fails else (WARN if warns else PASS)
    g.add("qa_render", status, f"{len(fails)} FAIL, {len(warns)} WARN -> {out / 'qa.md'}" + (f"; first: {fails[0].strip()[:120]}" if fails else ""),
          "tools/qa/qa_render.py (the recurring review notes, measured)")
    return text


def check_black_frames(g, picture, dur):
    """ffmpeg's blackdetect over the whole picture: a black stretch under 0.2 s inside the film is a flash. A section's last frame can
    render black (one frame at a time, at several places in a film), and the edge scan, the stutter check and the 2-fps sheets can't see
    one frame. A designed black (a wipe passing through black, the fade at the end) shows here too: each one is looked at."""
    import subprocess
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(picture), "-vf", "scale=320:-2,blackdetect=d=0.01:pix_th=0.06:pic_th=0.97",
                        "-an", "-f", "null", "-"], capture_output=True, text=True, errors="replace")
    spans = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]
    short = [(a, b) for a, b in spans if b - a < 0.2 and a < dur - 1.0]
    g.add("black frames", PASS if not short else WARN,
          (f"{len(short)} short black(s) inside the film, look at each: " + ", ".join(f"{a:.2f}-{b:.2f}" for a, b in short[:10])) if short
          else f"{len(spans)} black stretch(es), none short inside the film", "LONG_FORM: no flash frame (a section's last frame rendered black)")


def check_after_remotion(g):
    left = processes(HEADLESS)
    g.add("the computer after the job", PASS if not left else WARN, f"{left} {HEADLESS} left", "one Remotion job at a time; none left behind")


def check_reuse(g, v):
    tool = MOTION / "reuse_check.py"
    if not tool.exists():
        g.add("reuse check", SKIP, "tools/motion/reuse_check.py is not there yet", "no line or graph 1:1 from another video")
        return
    out, js = v.pipe_dir / f"reuse_v{g.version}.md", v.pipe_dir / f"reuse_v{g.version}.json"
    r = run([PY_PIPE, tool, v.comp, "--last", "3", "--out", out, "--json", js], cwd=REPO, check=False, log=v.pipe_dir / f"reuse_v{g.version}.log")
    m = re.search(r"wrote .*?: (\d+) findings", r.stdout)
    if r.returncode or not m:
        g.add("reuse check", WARN, f"reuse_check.py did not finish cleanly: {tail(r.stdout)}", "no line or graph 1:1 from another video")
        return
    n = int(m.group(1))
    # strict on graphs 1:1 from another video (and lines: script_lint), relaxed on footage across videos
    md = out.read_text(encoding="utf-8") if out.exists() else ""
    head = "## Graphics taken from a past video's code"
    sec = md.split(head, 1)[1].split("\n## ", 1)[0] if head in md else ""
    graphs = [f"{name} (from {vid})" for name, vid in re.findall(r"- \*\*(\w+)\*\* \(`[^`]+`, from (\d+)\)", sec) if vid != v.id]
    g.add("reuse check", PASS if not graphs else WARN,
          (f"graphs taken 1:1 from another video's code: {', '.join(graphs[:6])}; " if graphs else "no graph taken from another video's code; ")
          + f"{n} finding(s) in all, footage and stills as information -> {out}",
          "never a line or a graph 1:1; footage and music never twice inside a video, preferably not the last video's")


def check_score_log(g, v):
    # not a detached run's own stdout (score_v6_run.log): that log has no report and the effect check would read SKIP
    logs = sorted((p for p in v.pipe_dir.glob(f"score_v{g.version}*.log") if not p.stem.endswith("_run")), key=lambda p: p.stat().st_mtime)
    if not logs:
        g.add("score report", SKIP, f"no score_v{g.version}.log in {v.pipe_dir} (run `pipe score` / `pipe finish` through the line)", "")
        return
    text = logs[-1].read_text(encoding="utf-8", errors="replace")
    sil = re.search(r"outside the designed ones: (\[.*?\])", text)
    vm = [float(x) for x in re.findall(r"voice[^\n]*?music[^\n]*?(-?\d+\.\d) ?dB", text, re.I)]
    # long form ~22 dB voice over music (UNDER 13, GAP_MIN 22; at 17-18 the music swallows the voice); Shorts sit lower, ~17-18
    lo, hi = (20.5, 24.0) if g.v.kind == "long" else (16.0, 19.5)
    problems = []
    if sil and sil.group(1) != "[]":
        problems.append(f"silences outside the designed ones: {sil.group(1)[:80]}")
    off = [x for x in vm if not lo <= x <= hi]
    if vm and off:
        problems.append(f"voice over music {min(vm):.1f}-{max(vm):.1f} dB (the band: {lo:g}-{hi:g})")
    g.add("score report", WARN if problems else PASS, "; ".join(problems) if problems else f"silences outside the designed ones: []; voice over music {min(vm):.1f}-{max(vm):.1f} dB" if vm else "read: " + tail(text, 2),
          "standard/SOUND_AND_VOICE.md (long form ~22 dB, Shorts ~17-18; never digital silence)")
    # no effect louder than the voice (score.py's 1.5-s check), no memey sound under a serious line
    fx = re.search(r"effects louder than [-+]?\d+ LU against the voice: (\[.*?\]|none); memey effects outside a joke: (\[.*?\]|none)", text)
    if fx:
        loud, meme = fx.group(1), fx.group(2)
        st = FAIL if loud != "none" else WARN if meme != "none" else PASS
        g.add("effects: level and mood", st, f"too loud at {loud}; memey outside a joke at {meme}" if st != PASS else
              "every effect -7 LU or quieter against the voice over 1.5 s; no memey sound outside a joke", "effects at -7 LU or under, on the mood")
    else:
        g.add("effects: level and mood", SKIP, "the score log predates score.py's effect check: run `pipe score` again", "effects at -7 LU or under, on the mood")


# ------------------------------------------------------------------------------------------------------------------------------ long form
def gate_long(g, v, a):
    import pipe
    export = Path(a.export) if a.export else v.export_dir / f"{v.export_name(g.version)}.mp4"
    picture = v.render_dir / f"v{g.version}_picture.mkv"
    dur_comp = v.duration()
    if export.exists():
        check_shape(g, export, 3840, 2160, dur_comp)
        check_loudness(g, export)
        check_qa_render(g, v, export, "long")
    else:
        g.add("export", FAIL, f"{export} is missing (finish first)", "")
    # the composition itself
    try:
        report = pipe.audit_report(v, tag="qa_audit")
        n_bad = len(report["over"]) + len(report["short"]) + len(report["shortPlays"]) + len(report["slow"]) + len(report["unknown"])
        g.add("static clip audit", PASS if n_bad == 0 else FAIL,
              f"{len(report['plays'])} plays in {len(report['shots'])} shots; {len(report['over'])} overrun, {len(report['short']) + len(report['shortPlays'])} under {report['minShot']} s, "
              f"{len(report['slow'])} under 1.0x, {len(report['unknown'])} not in clipdurs.json", "LONG_FORM.md: no freeze, no flash, no slowed clip")
        A = v.section("audit")
        if not a.no_edges:
            edges, n = pipe.edges_check(v, report, float(A.get("edge", 0.5)), float(A.get("scene", 0.3)))
            # every hit listed, each one looked at on its frames (a list cut to the first few hides the rest)
            g.add("clip edges", PASS if not edges else WARN, f"{len(edges)} of {n} video plays open or end within {A.get('edge', 0.5)} s of a source cut, fade or flicker"
                  + "".join(f"; {pipe.mmss(e['at'])} {e['src']}: {e['what']}" for e in edges), "LONG_FORM.md: no sliver of the next shot")
        notes = [c for c in report.get("caps", []) if pipe.INTERNAL.search(c["text"])]
        g.add("captions", PASS if not notes else FAIL, f"{len(notes)} of {len(report.get('caps', []))} on-screen strings read like working notes"
              + "".join(f"; {pipe.mmss(c['at'])} {c['prop']}='{c['text'][:40]}'" for c in notes), "no working note, label or placeholder on screen")
        big = [m for m in report.get("marks", []) if m["share"] > 0.5]
        g.add("marks", PASS if not big else FAIL, f"{len(big)} of {len(report.get('marks', []))} card marks cover over half their text"
              + "".join(f"; {pipe.mmss(m['at'])} '{m['hl'][:40]}' {m['share']:.0%}" for m in big), "a mark on most of the text is no mark")
    except SystemExit as e:
        g.add("static clip audit", FAIL, str(e)[:200], "")
    code = code_files(v.src_dir)   # with the subfolder files the film imports
    rates = [f"{f.relative_to(v.src_dir.resolve()).as_posix()}:{i}" for f in code for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
             if re.search(r"rate=\{0\.", ln)]
    g.add("no clip under 1.0x in the code", PASS if not rates else FAIL, f"{len(rates)} `rate={{0.` " + (", ".join(rates[:6]) if rates else ""),
          "a cut, never a slowed clip, outside a deliberate replay")
    # a file re-saved in the wrong encoding shows UTF-8 read as cp1252 on screen (a credit reading "Source Â· ...") and a \uXXXX escape
    # inside a JSX attribute's quotes is printed as typed, never turned into its character
    moji = [f"{f.relative_to(v.src_dir.resolve()).as_posix()}:{i}" for f in code for i, ln in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1)
            if re.search(r"Â|Ã|â€", ln) or re.search(r"""\w=(['"])[^'"]*\\(u[0-9a-fA-F]{4}|[^\x00-\x7f])[^'"]*\1""", ln)]
    g.add("broken characters in the code", PASS if not moji else FAIL, f"{len(moji)} line(s) with Â, Ã, â€ or a \\u escape in a JSX attribute "
          + (", ".join(moji[:6]) if moji else ""), "a credit reading 'Source Â·'; an escape printed as typed ('\\u00b7')")
    cam = MOTION / "qa_camera.mjs"
    if cam.exists():
        js = v.pipe_dir / f"cards_v{g.version}.json"
        r = run([NODE, cam, (v.src_dir / v.module).relative_to(MOTION).as_posix(), "--json", js], cwd=MOTION, check=False, log=v.pipe_dir / f"camera_v{g.version}.log")
        m = re.search(r"(\d+) cards .*?: (\d+) one move, (\d+) two moves", r.stdout)
        if m:
            g.add("card cameras", PASS if m.group(3) == "0" else FAIL, f"{m.group(1)} cards: {m.group(2)} one move, {m.group(3)} two moves", "a card's camera makes one move, from the first frame")
        else:
            g.add("card cameras", WARN, f"qa_camera.mjs: {tail(r.stdout)}", "a card's camera makes one move, from the first frame")
    else:
        g.add("card cameras", SKIP, "qa_camera.mjs is not there", "a card's camera makes one move, from the first frame")
    if picture.exists():
        r = run([PY_PIPE, MOTION / "qa_cadence.py", "--stutter", picture], cwd=MOTION, check=False, log=v.pipe_dir / f"stutter_v{g.version}.log")
        m = re.search(r"(\d+) stutter", r.stdout)
        summary = next((ln.strip() for ln in r.stdout.splitlines() if "stutter" in ln), tail(r.stdout))
        where = [ln.strip() for ln in r.stdout.splitlines() if re.match(r"\s+frame \d+", ln)]
        g.add("stutter check", PASS if m and m.group(1) == "0" else (WARN if m else SKIP), summary.split(": ", 1)[-1] + (f"; {where[0]}" if where else ""),
              "laggy footage shows as a stutter")
    else:
        g.add("stutter check", SKIP, f"{picture.name} is not there", "")
    if export.exists() or picture.exists():   # the export: patches (`finish --patches`) are laid in there, not into the picture file
        check_black_frames(g, export if export.exists() else picture, dur_comp)
    srt = export.with_suffix(".srt")
    if srt.exists():
        text = srt.read_text(encoding="utf-8", errors="replace")
        ends = [int(h) * 3600 + int(m_) * 60 + float(s.replace(",", ".")) for h, m_, s in re.findall(r"--> (\d+):(\d+):(\d+,\d+)", text)]
        n = text.count("-->")
        inside = bool(ends) and max(ends) <= dur_comp + 1
        g.add("subtitles", PASS if n and inside else FAIL, f"{n} cues, last ends at {max(ends) if ends else 0:.1f} s of {dur_comp:.1f}", "SCRIPTS_AND_PACKAGING.md: upload with our own .srt")
    else:
        g.add("subtitles", FAIL if export.exists() else SKIP, f"{srt.name} is missing", "")
    check_reuse(g, v)
    check_score_log(g, v)
    if a.deep and export.exists():
        sheets = v.pipe_dir / f"flash_v{g.version}"
        r = run([PY_EDIT, MOTION / "qa_flash_scan.py", export, "--sheets", sheets], cwd=REPO, check=False, log=v.pipe_dir / f"flash_v{g.version}.log")
        m = re.search(r"(\d+) frames, (\d+) flagged", r.stdout)
        g.add("flash scan (whole film)", (WARN if m.group(2) != "0" else PASS) if m else WARN, (f"{m.group(2)} flagged frames of {m.group(1)} -> {sheets}" if m else tail(r.stdout)),
              "no flash, no black frame, no jump cut")
    check_after_remotion(g)


# --------------------------------------------------------------------------------------------------------------------------------- Shorts
def gate_short(g, v, a):
    export = Path(a.export) if a.export else v.export_dir / f"{v.export_name(g.version)}.mp4"
    dur_comp = v.duration()
    if not export.exists():
        g.add("export", FAIL, f"{export} is missing (finish first)", "")
    else:
        dur = check_shape(g, export, 1080, 1920, dur_comp, tol=0.6)
        check_loudness(g, export)
        words = json.loads(v.words().read_text(encoding="utf-8"))
        last = max(w["end"] for w in words) if words else 0
        gap = dur - last
        g.add("the end after the last word", PASS if 0.15 <= gap <= 0.8 else WARN, f"{gap:.2f} s after the last word (the bar: ~0.4 s, no end card)", "SHORTS.md: stops ~0.4 s after the last word")
        check_qa_render(g, v, export, "short", v.dj / "build" / "voice" / "narration.wav")
        r = run([PY_PIPE, MOTION / "qa_holds.py", export], cwd=REPO, check=False, log=v.pipe_dir / f"holds_v{g.version}.log")
        g.add("holds (a change every 2-3 s)", PASS if r.returncode == 0 else FAIL, tail(r.stdout), "qa_holds.py (nothing over 2.6 s without a change)")
        ws = v.pipe_dir / f"wordsheet_v{g.version}" / "sheet"
        ws.parent.mkdir(parents=True, exist_ok=True)
        r = run([PY_EDIT, QA_TOOLS / "word_sheet.py", export, v.words(), ws], cwd=REPO, check=False)
        g.add("word sheet for the eye", INFO if r.returncode == 0 else WARN, f"every 0.5 s with the word being said -> {ws.parent}", "SHORTS.md check 3: frame 0, every cut a new matching picture, no flash")
        sheet = v.pipe_dir / f"sheet_{v.export_name(g.version)}.jpg"
        run([FFMPEG, "-v", "error", "-y", "-i", export, "-vf", "fps=2,scale=180:320,tile=13x4", "-frames:v", "1", sheet], check=False, quiet=True)
        g.add("2-fps sheet for the eye", INFO, f"every subject centred, vertically too -> {sheet}", "SHORTS.md check 4")
    check_reuse(g, v)
    check_score_log(g, v)
    check_after_remotion(g)


# --------------------------------------------------------------------------------------------------------------------------------- report
CHECKLIST_LONG = """- [ ] A 2-fps sheet of the whole render read against the words: each shot shows what its words say; every name, place, thing and number has its picture; every shot of 4 s or more is live
- [ ] Every flagged clip edge and every qa_render WARN looked at on its sheet, fixed or allowed with the reason written here
- [ ] Pages (articles, posts, documents on screen) near ~16% of the time, each kept only where its words are the point
- [ ] Every clip's span chosen on its whole sheet: the thing named whole and clear in the frame; real objects as real cut-outs, graphics against a pro reference
- [ ] Real people's clips: start matched by audio, at 1.0, the mouth moving, the right name, subtitles clear of the banners
- [ ] Every arrow, cross and stamp checked at 100% on its frame; no circles; no mark where the frame shows the thing
- [ ] Every effect nameable in three words, on its frame; every highlight has a marker drawn from its light; a removed visual took its sound
- [ ] voice_check.py, rhotic.py --sections and accent_id.py clean on every section; no tired opening
- [ ] No asset from the last three videos one to one (the reuse report read); the palette is this video's
- [ ] The end: the subscribe ask at a real break, the like/comment ask, the creator's sign-off line, then a fade to black and silence
- [ ] The chat's own full audit beside the reference video first; after the creator's notes, every fix as a before/after sample before a full render"""
CHECKLIST_SHORT = """- [ ] Frame 0 is the package with the flash alone; every cut a new matching picture; no flash frame; no clip into its source's next shot (word sheet)
- [ ] Every subject centred, vertically too; logos on their weight; nothing above y 260; nothing to read under the captions (2-fps sheet, phone_view.py)
- [ ] Receipts (pages, posts) above the captions, their lines readable at phone size
- [ ] Captions against the voice word by word; no card or label repeating the line
- [ ] The narration passes rhotic.py, accent_id.py, voice_check.py; no silence over 0.18 s
- [ ] Every effect chosen for its moment, nameable, on its frame; no sound outlives its picture; voice over music ~17-18 dB
- [ ] True and safe: every number matches the voice; no leaked footage, no sexual shot, no word a filter could misread
- [ ] Delivery in the final message: the MP4, one title and the tags as copy blocks; no description, no thumbnail, no phone copy"""


def write_report(g, v, a):
    export = Path(a.export) if a.export else v.export_dir / f"{v.export_name(g.version)}.mp4"
    fails = g.fails()
    warns = [c for c in g.checks if c["status"] == WARN]
    lines = [f"# {v.id} v{g.version} · QA gate ({time.strftime('%Y-%m-%d %H:%M')})", "",
             f"`{export}` · {'**FAIL**: ' + str(len(fails)) + ' check(s) failed' if fails else '**PASS**'}; {len(warns)} to look at. "
             f"Run: `PIPE tools/pipeline/pipe.py {v.id} qa --version {g.version}`.", "",
             "| Check | Result | Detail | Stands for |", "|---|---|---|---|"]
    for c in g.checks:
        lines.append(f"| {c['check']} | {c['status']} | {c['detail'].replace('|', '/')} | {c['source'].replace('|', '/')} |")
    lines += ["", "## Delivery checklist (the eye's part; tick each before it goes to the creator)", "",
              CHECKLIST_SHORT if v.kind == "short" else CHECKLIST_LONG, "",
              "## Kept flags (write the reason for every WARN or allowed flag kept)", "", "- (none yet)", ""]
    out = v.folder / f"QA_v{g.version}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    (v.pipe_dir / f"qa_v{g.version}.json").write_text(json.dumps({"video": v.id, "version": g.version, "export": str(export), "checks": g.checks}, indent=1, ensure_ascii=False),
                                                       encoding="utf-8")
    say(f"QA report -> {out} ({'FAIL ' + str(len(fails)) if fails else 'PASS'}, {len(warns)} to look at)")
    return out


def run_gate(v, a):
    g = Gate(v, a.version)
    say(f"QA gate {v.id} v{a.version} ({v.kind})")
    if v.kind == "short":
        gate_short(g, v, a)
    else:
        gate_long(g, v, a)
    write_report(g, v, a)
    if g.fails():
        raise SystemExit(1)
    return g
