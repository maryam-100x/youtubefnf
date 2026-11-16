"""Finish a Remotion Short: the house captions burned in (dj/ass.py, the same planner as every Short, at the house line), the voice, the
Remotion sound effects (the render's PCM track), a music bed ~17 dB under the voice, levelled to MIX_LUFS and limited. Writes
export/<name>.mp4 (one export, no copy without music).

A looping Short (the last line runs into the first): the bed is a whole number of bars from a downbeat, gently re-timed to the Short's
exact length (librosa beat track), and nothing fades at either end, so the music runs on through the loop.

  PIPE tools/motion/finish_short.py <video folder name> <render.mkv> <name> [music_start_s music_span_s] [--music <file>] [--picture-only]
--picture-only: the captions burned in, nothing else (build/<name>_picture.mp4); the sound comes from tools/sound/score.py --picture
(the usual way). --music: the bed for the full mix, a file in MUSIC (or a full path): the creator's own track or one made with
tools/music; with no --music the mix has no bed.

Caption data (each optional, missing = nothing to do):
  videos/<video>/captions_fix.json      measured onsets ({beat, w, start}: onsets.py) and misheard words split ({beat, w, nth?, into})
  videos/<video>/captions_bites.json    a real clip's own words in a hold, captioned like the narration
  videos/<video>/captions_hide.json     phrases a stamp, count or label already shows on screen
  tools/sound/names.json                every name of the scripts, so a name is captioned as the script writes it
  tools/motion/data/caption_phrases.json  [["<word>", "<word>", ...], ...]: multi-word names that are always one caption
  tools/motion/data/numbered_titles.json  ["<title word>", ...]: a title followed by its number ("<title> 2", "<title> II"): the
                                        number always as a digit, and title and number one caption"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, MUSIC as MUSIC_DIR, TOOLS, VIDEOS, VIDEOS_REPO  # noqa: E402

sys.path.insert(0, str(TOOLS))
from dj import ass as house_ass  # noqa: E402
from dj.core import Ctx, font, load_config  # noqa: E402
from onsets import apply_onsets  # noqa: E402

HERE = Path(__file__).resolve().parent
SR = 48000
MUSIC = None      # --music: the bed (None: no bed)
MIX_LUFS = -15.0  # the Short's level
PICTURE_ONLY = False  # --picture-only: captions burned in, the sound mixed by score.py


def _data(name, default):
    f = HERE / "data" / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


def load(path, ss=None, t=None, af=None):
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error"] + (["-ss", f"{ss:.3f}"] if ss is not None else []) + (["-t", f"{t:.3f}"] if t else []) + ["-i", str(path)]
    cmd += (["-af", af] if af else []) + ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).copy()


def lufs(x, tmp):
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", str(tmp)],
                   input=x.astype(np.float32).tobytes(), check=True)
    err = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(tmp), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float([ln for ln in err.splitlines() if ln.strip().startswith("I:")][-1].split()[1])


def main(slug, render, name, m_start=None, m_span=None):
    video = VIDEOS_REPO / slug
    ctx = Ctx(video, load_config())
    render = Path(render).resolve()
    B = ctx.build
    total = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(render)], capture_output=True, text=True).stdout)
    n = int(round(total * SR))
    # captions: the heard words (they keep "$45", "Model 3"), cut at the Short's end
    words = [x for x in json.loads((B / "captions/words.json").read_text(encoding="utf-8"))["words"] if x["start"] < total]
    # what Whisper misheard (e.g. "eighty too" -> "$82"): [{beat, w, nth?, into: [words]}]: the nth (from 0) heard `w` in that beat is
    # split into `into` by length; into [] drops a word heard twice. By position, not time: a re-timed voice keeps its fixes
    fix_file = video / "captions_fix.json"
    words = apply_onsets(words, fix_file)  # measured onsets first ({beat, w, start}: onsets.py)
    for fx in (json.loads(fix_file.read_text(encoding="utf-8")) if fix_file.exists() else []):
        if "into" not in fx:
            continue
        hits = [i for i, x in enumerate(words) if x["beat"] == fx["beat"] and x["w"] == fx["w"]]
        nth = fx.get("nth", 0)
        if nth >= len(hits):
            print(f"  ! caption fix not applied (no {fx['w']!r} #{nth} in {fx['beat']}): check {fix_file.name}")
            continue
        i = hits[nth]
        x = words[i]
        L = [len(t) + 1 for t in fx["into"]]
        t0, d, parts = x["start"], x["end"] - x["start"], []
        for tok, l in zip(fx["into"], L):
            parts.append(dict(x, w=tok, start=round(t0, 3), end=round(t0 + d * l / sum(L), 3)))
            t0 += d * l / sum(L)
        words[i:i + 1] = parts
        print(f"  caption fix: {fx['w']} at {x['start']} -> {' '.join(fx['into']) or '(dropped)'}")
    # a name as the script writes it: Whisper spells names its own way (a brand written as digits, a surname spelled by ear) and every
    # name of a script is in names.json (A6, before any voice), so where the heard words differ from this Short's own script words
    # (src/<src>/words.json, beat by beat) and the script's side holds a names.json name, the script's words take that span. Everything
    # else keeps Whisper's writing ("$45", "Model 3"); captions_fix.json above still wins where it applies
    import difflib
    import re as _re0
    import tomllib as _toml0
    _n = lambda s: _re0.sub(r"[^a-z0-9]", "", s.lower().replace("’", "'").replace("'", ""))  # noqa: E731
    _bare = lambda s: _re0.sub(r"['’]s$", "", s.strip(",.?!:;"))  # noqa: E731
    try:
        _src = _toml0.loads((video / "video.toml").read_text(encoding="utf-8"))["video"]["src"]
        _sw = json.loads((HERE / "src" / _src / "words.json").read_text(encoding="utf-8"))
        names_n = {_n(k) for k in json.loads((TOOLS / "sound" / "names.json").read_text(encoding="utf-8"))["names"]}
    except (OSError, KeyError) as e:
        _sw, names_n = [], set()
        print(f"  ! names as written: skipped ({type(e).__name__}: {e})")
    for bt in dict.fromkeys(x["beat"] for x in words):
        hi = [i for i, x in enumerate(words) if x["beat"] == bt]
        if hi != list(range(hi[0], hi[-1] + 1)):
            print(f"  ! names as written: {bt}'s words aren't together, skipped")
            continue
        S = [x["w"] for x in _sw if x["beat"] == bt]
        sm = difflib.SequenceMatcher(a=[_n(t) for t in S], b=[_n(words[i]["w"]) for i in hi], autojunk=False)
        for op, a0, a1, b0, b1 in reversed(sm.get_opcodes()):
            toks = S[a0:a1]
            if op != "replace" or not (any(_n(_bare(t)) in names_n for t in toks) or _n(" ".join(_bare(t) for t in toks)) in names_n):
                continue
            seg = words[hi[b0]:hi[b1 - 1] + 1]
            t0, t1, L = seg[0]["start"], seg[-1]["end"], [len(t) + 1 for t in toks]
            parts, t = [], t0
            for tok, l in zip(toks, L):
                parts.append(dict(seg[0], w=tok, start=round(t, 3), end=round(t + (t1 - t0) * l / sum(L), 3)))
                t += (t1 - t0) * l / sum(L)
            words[hi[b0]:hi[b1 - 1] + 1] = parts
            print(f"  caption fix: the name as written: {' '.join(x['w'] for x in seg)} -> {' '.join(toks)} at {t0}")
    # a title's number as a digit, always (one caption style: never "II" in one place and "2" in another): Whisper's Roman numeral
    # right after a numbered title (data/numbered_titles.json) becomes its digit, in every Short
    TITLES = {t.upper() for t in _data("numbered_titles.json", [])}
    ROMAN = {"II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7"}
    for i in range(1, len(words)):
        tok = words[i]["w"].rstrip(",.?!'s’")
        if words[i - 1]["w"].rstrip(",.?!").upper() in TITLES and tok in ROMAN:
            print(f"  caption fix: {words[i - 1]['w']} {words[i]['w']} at {words[i]['start']} -> {ROMAN[tok]}")
            words[i] = dict(words[i], w=words[i]["w"].replace(tok, ROMAN[tok], 1))
    # a multi-word name is one caption (a name whole, never split across two caption chunks): its words merge into one, from the
    # first word's start to the last one's end (data/caption_phrases.json, the longer phrases first)
    NAMES = [tuple(w.lower() for w in p) for p in _data("caption_phrases.json", [])]
    bare = lambda s: s.lower().strip(",.?!:;")  # noqa: E731
    import re as _re
    i = 0
    while i < len(words):
        # a numbered title and its number are one caption ("<title> 2's", "<title> 3")
        if words[i]["w"].strip(",.?!:;").upper() in TITLES and i + 1 < len(words) and _re.match(r"^\d+('s|’s)?[,.?!]?$", words[i + 1]["w"]):
            words[i:i + 2] = [dict(words[i], w=f"{words[i]['w'].strip(',.?!:;')} {words[i + 1]['w']}", end=words[i + 1]["end"])]
            i += 1
            continue
        for nm in NAMES:
            if i + len(nm) <= len(words) and all(bare(words[i + k]["w"]) == nm[k] for k in range(len(nm))):
                joined = " ".join(words[i + k]["w"].strip(",.?!:;") for k in range(len(nm))) + words[i + len(nm) - 1]["w"][len(words[i + len(nm) - 1]["w"].rstrip(",.?!:;")):]
                print(f"  caption fix: one caption for {joined!r} at {words[i]['start']}")
                words[i:i + len(nm)] = [dict(words[i], w=joined, end=words[i + len(nm) - 1]["end"])]
                break
        i += 1
    # a real clip's own words in a HOLD (the clip plays, not a quote), captioned like the narration:
    # captions_bites.json = [{beat: "S02h", offset: s (when the bite's sound starts in the hold), words: [[w, t0, t1], ...]}], the times
    # relative to the bite's sound (Whisper on the bite file), so a re-timed narration keeps them in place
    bites_file = video / "captions_bites.json"
    if bites_file.exists():
        starts = {b["id"]: b["start"] for b in json.loads((B / "beats.json").read_text(encoding="utf-8"))["beats"]}
        for bt in json.loads(bites_file.read_text(encoding="utf-8")):
            t0 = starts[bt["beat"]] + bt.get("offset", 0.0)
            words += [{"w": w_, "start": round(t0 + a, 3), "end": round(t0 + b, 3), "beat": bt["beat"]} for w_, a, b in bt["words"]]
            print(f"  bite captions: {len(bt['words'])} words in {bt['beat']} from {t0:.2f} s")
        words.sort(key=lambda x: x["start"])
    # words a stamp, count or label already shows (text shows once, never twice; on-screen text can replace captions):
    # captions_hide.json = [{beat, phrase, nth?}], the phrase in the script's words; its span is read from the composition's own word
    # timing (src/<src>/words.json) and every caption word heard inside it is dropped
    hide_file = video / "captions_hide.json"
    if hide_file.exists():
        import re
        import tomllib
        norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "'").replace("'", ""))  # noqa: E731
        src = tomllib.loads((video / "video.toml").read_text(encoding="utf-8"))["video"]["src"]
        sw = json.loads((HERE / "src" / src / "words.json").read_text(encoding="utf-8"))
        for hd in json.loads(hide_file.read_text(encoding="utf-8")):
            toks = [norm(t) for t in hd["phrase"].split() if norm(t)]
            hits = [i for i in range(len(sw)) if all(i + k < len(sw) and sw[i + k]["beat"] == hd["beat"] and norm(sw[i + k]["w"]) == toks[k]
                                                     for k in range(len(toks)))]
            if len(hits) <= hd.get("nth", 0):
                raise SystemExit(f"captions_hide: {hd['phrase']!r} is not in {hd['beat']} ({hide_file})")
            i = hits[hd.get("nth", 0)]
            a, b = sw[i]["start"] - 0.03, sw[i + len(toks) - 1]["end"] + 0.03
            gone = [x["w"] for x in words if a <= (x["start"] + x["end"]) / 2 <= b]
            words = [x for x in words if not a <= (x["start"] + x["end"]) / 2 <= b]
            print(f"  caption hidden (the screen shows it): {hd['beat']} {hd['phrase']!r} {a:.2f}-{b:.2f} s: {' '.join(gone)}")
    # and while a stamp, count or label sits on the caption line, that line is its alone (two texts stacked on one line read as one,
    # e.g. "NOW" over "5,000"): every caption word heard in those frames is dropped, the small ones too. The frames come from the
    # gate's probe of this very code (render refuses an ungated stamp): text marked data-gate="stamp" whose centre is within 200 px of
    # the caption line (y 960)
    probe = B.parent / "pipeline" / "gate" / "probe.jsonl"
    if probe.exists():
        on = set()
        for line in probe.open(encoding="utf-8"):
            kind, _, body = line.partition("|")
            if kind != "layout":
                continue
            try:
                o = json.loads(body)
            except ValueError:
                continue
            # a stamp's words or a lone logo (an <img> inside a data-gate="stamp" logo) on the caption line
            if any(it.get("k") in ("text", "img", "clip") and it.get("g") == "stamp" and it.get("op", 0) >= 0.5 and abs(it["y"] + it["h"] / 2 - 960) <= 200 for it in o["items"]):
                on.add(o["frame"])
            # a receipt's window across the caption line (the Shorts kit's receipt, centred on it): its lit words carry the line, the
            # words said around them go uncaptioned
            elif any(it.get("g") == "frame" and it.get("k") == "box" and it.get("op", 0) >= 0.5 and max(it["y"], it.get("cy0", -1e9)) < 930
                     and min(it["y"] + it["h"], it.get("cy1", 1e9)) > 990 for it in o["items"]):
                on.add(o["frame"])
        spans, run = [], None
        for fr in sorted(on):
            if run and fr - run[1] <= 2:
                run[1] = fr
            else:
                if run:
                    spans.append(run)
                run = [fr, fr]
        if run:
            spans.append(run)
        spans = [(a / 60 - 0.02, (b + 1) / 60 + 0.02) for a, b in spans]
        # a word goes when 40%+ of it is under the stamp (a word said 0.02 s into a stamp's end keeps its caption, so the line never
        # stands bare; a word under the stamp for most of its length goes)
        under = lambda x: any(min(x["end"], b) - max(x["start"], a) >= 0.4 * max(0.01, x["end"] - x["start"]) for a, b in spans)  # noqa: E731
        gone = [x["w"] for x in words if under(x)]
        words = [x for x in words if not under(x)]
        print(f"  captions under the stamps' line ({len(spans)} stretches): {' '.join(gone) or 'none'}")
    else:
        print("  ! no gate probe: the stamps' stretches can't be cleared from the captions (run pipe.py gate first)")
    chunks, heroes = house_ass.plan(ctx, words)
    ass = B / "captions" / f"{name}.ass"
    house_ass.write(ctx, chunks, heroes, ass)
    fonts = B / "captions/fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    # the look's caption font (look.json fonts.caption), the file dj fetched into the studio's fonts folder when it measured the captions
    cap_font = Path(font(ctx.cfg, "heavy", 10).path)
    (fonts / cap_font.name).write_bytes(cap_font.read_bytes())
    pic = B / f"{name}_picture.mp4"
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(render), "-an", "-vf", f"ass=captions/{name}.ass:fontsdir=captions/fonts",
                    "-c:v", "libx264", "-crf", "15", "-preset", "slow", "-pix_fmt", "yuv420p", str(pic)], cwd=str(B), check=True)
    if PICTURE_ONLY:  # the sound is mixed elsewhere (score.py --picture): the captioned picture is the product here
        print(pic)
        return
    # sound
    voice = load(B / "voice/narration.wav")[:n]
    v = np.zeros((n, 2), np.float32)
    v[:len(voice)] = voice
    fx = load(render)[:n]
    fxp = np.zeros((n, 2), np.float32)
    fxp[:len(fx)] = fx
    tmp = B / "qa" / "_lufs.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    v_l = lufs(v, tmp)
    out_dir = VIDEOS / slug / "export"
    out_dir.mkdir(parents=True, exist_ok=True)
    lim = f"aresample={SR * 4},alimiter=limit={10 ** (-2.5 / 20):.4f}:attack=0.5:release=60:level=disabled:latency=1,aresample={SR}"
    if MUSIC is None:
        print("  no --music: the mix has no bed")
    for with_music, suffix in ((MUSIC is not None, ""),):  # one export, no copy without music
        mix = v + fxp
        if with_music:
            if m_start is not None:  # a whole number of bars, re-timed to the exact length: the bed loops with the Short
                # read 0.2 s past the span: atempo holds back its last ~10 ms, which would leave the bed's final 10 ms silent at the
                # loop's join; the first n samples are still exactly the span, so the bars stay aligned
                m = load(MUSIC, ss=m_start, t=m_span + 0.2, af=f"atempo={m_span / total:.5f}")
            else:
                m = load(MUSIC, ss=30.0, t=total)
            m = np.pad(m[:n], ((0, max(0, n - len(m))), (0, 0)))
            k = int(0.004 * SR)  # 4 ms: no click at the loop point, no audible fade
            m[:k] *= np.linspace(0, 1, k)[:, None]
            m[-k:] *= np.linspace(1, 0, k)[:, None]
            mix = mix + m * 10 ** ((v_l - 17.0 - lufs(m, tmp)) / 20)
        k = int(0.004 * SR)  # the whole mix, too: the opening flash starts mid-sound, a step at the loop's join without this
        mix[:k] *= np.linspace(0, 1, k)[:, None]
        mix[-k:] *= np.linspace(1, 0, k)[:, None]
        wav = B / f"{name}_mix{suffix}.wav"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                        "-af", f"volume={MIX_LUFS - lufs(mix, tmp):.2f}dB,{lim}", str(wav)], input=mix.astype(np.float32).tobytes(), check=True)
        dst = out_dir / f"{name}{suffix}.mp4"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(pic), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "384k", "-t", f"{total:.3f}", "-movflags", "+faststart", str(dst)], check=True)
        print(dst)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--music" in argv:
        k = argv.index("--music")
        mf = Path(argv[k + 1])
        MUSIC = mf if mf.is_absolute() else MUSIC_DIR / mf
        del argv[k:k + 2]
    PICTURE_ONLY = "--picture-only" in argv
    a = [x for x in argv if x != "--picture-only"]
    main(a[0], a[1], a[2], *(float(x) for x in a[3:5]))
