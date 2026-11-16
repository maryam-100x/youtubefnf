"""A narration for a PROTOTYPE's beats before the full voice exists (voice_full.py also lays the whole film out with it).

The voice lock's stage 1 (autopick.py) voices each section of the prototype the lines-before way (the two script lines before the span voiced
inside the same request, then cut away) and records the machine's pick in
<build>/voice/autopick/<first>-<last>/autopick_<first>-<last>.json; the picked take's beats are in <build>/voice/patch/<beat>_<k>.wav
(span_takes.py's pieces: 1.0x, each with its .align.json). `dj tts` would voice the WHOLE script; this lays only the prototype's
picked beats out the way `dj tts` lays a narration out (dj/tts.py run(): each beat's pauses capped at [tts] max_pause, the house tempo
[tts] tempo (1.04x), clean_ends, level_beats, the first beat trimmed to its first sound, the edge check, frame-aligned slots of the
beat + [tts] gap (the tail after the last), normalize), and writes <build>/voice/narration.wav, the per-beat wavs and
<build>/beats.json in dj tts's format, so voice_chain.sh, dj captions and sync_words.py run on it unchanged. It refuses a section
with no recorded pick or a pick made on another script.md, and never runs on a locked voice.

  PIPE tools/voice/proto_narration.py <video> <first beat> <last beat>"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import TOOLS, VIDEOS_REPO  # noqa: E402
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE))
from dj import script as dj_script  # noqa: E402
from dj.__main__ import video_config  # noqa: E402
from dj.core import SR, Ctx, load_config, read_wav, write_wav  # noqa: E402
from dj.tts import all_tempo, clean_ends, edge_faults, level_beats, normalize, tighten_pauses, trim_lead  # noqa: E402
import numpy as np  # noqa: E402


def end_on_sound(clip):
    """'<levels>' when the 20 ms before a beat clip's last 10 ms still sound (broadband over -45 dB or 4-12 kHz over -50 dB), else None"""
    x = clip.astype(np.float64) / 32768
    a, b = len(x) - int(0.030 * SR), len(x) - int(0.010 * SR)
    if a <= int(0.02 * SR):
        return None
    seg = x[a:b]
    w = np.hanning(len(seg))     # the band by FFT (numpy only: the pipeline venv has no scipy)
    X = np.abs(np.fft.rfft(seg * w)) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    hf_db = float(10 * np.log10(2 * X[(f >= 4000) & (f <= 12000)].sum() / (len(seg) * (w ** 2).sum()) + 1e-12))
    bb_db = float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12))
    # a word's sound, not a breath: a hiss (the band within 5 dB of the whole: -32 / -31) or a voiced sound with no air in it (the
    # band 20+ dB under: a take that ended inside the next beat's first word, -36 / -87); a breath sits between (an inhale -28 / -34)
    # and is the chain's to mute
    hiss = hf_db > -50 and hf_db >= bb_db - 5
    voiced = bb_db > -45 and hf_db < bb_db - 20
    return f"{bb_db:.0f} dB, 4-12 kHz {hf_db:.0f} dB ({'a hiss' if hiss else 'voiced'})" if hiss or voiced else None


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    video, first, last = sys.argv[1:]
    video = Path(video).name            # a folder name, or a path to the video folder
    vdir = str(VIDEOS_REPO / video)
    __import__("voice_lock").guard_video(vdir, "proto_narration.py")
    cfg = load_config(None, video_config(vdir))
    ctx = Ctx(vdir, cfg)
    tcfg = cfg["tts"]
    every = dj_script.load(ctx)["beats"]
    beats_all = [b for b in every if b.get("voice") and not b.get("hold")]
    ids = [b["id"] for b in beats_all]
    i0, i1 = ids.index(first), ids.index(last)
    beats = beats_all[i0:i1 + 1]
    script_hash = __import__("hashlib").sha256((VIDEOS_REPO / video / "script.md").read_bytes()).hexdigest()
    script_md = (VIDEOS_REPO / video / "script.md").read_text(encoding="utf-8")
    # the picks: every autopick record whose span lies inside first..last, made on this script.md; a beat takes the newest record
    # that picked a take for it (a section that found no clean take may be voiced again in smaller spans: those records cover it)
    picks, when, bad = {}, {}, {}
    for rec in sorted((ctx.build / "voice" / "autopick").glob("*/autopick_*.json")):
        d = json.loads(rec.read_text(encoding="utf-8"))
        pick = d.get("pick")
        a, b = d["span"]
        if a not in ids or b not in ids or ids.index(a) < i0 or ids.index(b) > i1:
            continue
        span_ids = ids[ids.index(a):ids.index(b) + 1]
        sh = d.get("script_sha256") or d.get("script") or d.get("script_hash")
        if pick is None:
            for bid in span_ids:
                bad.setdefault(bid, f"{rec.name}: no clean take was picked (autopick exit 2): voice that section again")
            continue
        # a record holds while its span's own lines are unchanged (span_sha256, autopick.span_sha: script.md's VOICE lines as gatelib
        # reads them); older records: this very script.md
        span_now = None
        if d.get("span_sha256"):
            import re as _re
            lines = _re.findall(r"^\[(S[0-9]+[a-z]?)\]\s*VOICE:\s*(.*\S)\s*$", script_md, _re.M)
            lid = [x for x, _ in lines]
            if a in lid and b in lid:
                span_now = __import__("hashlib").sha256("\n".join(v for _, v in lines[lid.index(a):lid.index(b) + 1])
                                                        .encode("utf-8")).hexdigest()
        if d.get("span_sha256") and d["span_sha256"] != span_now:
            for bid in span_ids:
                bad.setdefault(bid, f"{rec.name}: its lines changed since it was voiced: voice that section again")
            continue
        if not d.get("span_sha256") and sh and not script_hash.startswith(str(sh)[:12]) and not str(sh).startswith(script_hash[:12]):
            for bid in span_ids:
                bad.setdefault(bid, f"{rec.name}: picked on another script.md ({str(sh)[:12]} vs {script_hash[:12]}): voice it again")
            continue
        for bid in span_ids:
            if bid not in picks or d.get("when", "") >= when[bid]:
                picks[bid], when[bid] = int(pick), d.get("when", "")
    unresolved = sorted({bad[b["id"]] for b in beats if b["id"] not in picks and b["id"] in bad})
    if unresolved:
        raise SystemExit("; ".join(unresolved))
    miss = [b["id"] for b in beats if b["id"] not in picks]
    if miss:
        raise SystemExit(f"no picked take for {', '.join(miss)} (run autopick.py on their sections)")
    pdir = ctx.build / "voice" / "patch"
    clips = []
    for b in beats:
        x = read_wav(pdir / f"{b['id']}_{picks[b['id']]}.wav")
        clips.append(tighten_pauses(x, tcfg.get("max_pause", 0)) if tcfg.get("max_pause") else x)
    clips = all_tempo(tcfg, beats, clips)
    if tcfg.get("clean_ends", True):
        clips = [clean_ends(c) for c in clips]
    if tcfg.get("level_beats", True):
        clips = [lv if lv is not None else c for lv, c in zip(level_beats(clips), clips)]
    clips[0] = trim_lead(clips[0])
    bad = [f"{b['id']} {', '.join(fl)}" for b, c in zip(beats, clips) for fl in [edge_faults(c)] if fl]
    # a beat's end must lie after its last word's sound, its hiss included (a cut-off last sound is heard): the 20 ms before the
    # piece's 10-ms fade under -45 dB broadband and -50 dB in 4-12 kHz (an /s/ ends in the band a loudness check misses)
    bad += [f"{b['id']} ends on sound ({e})" for b, c in zip(beats, clips) for e in [end_on_sound(c)] if e]
    if bad:
        raise SystemExit("beats cut mid-sound: " + "; ".join(bad))
    # the HOLD beats inside the span (a pause without voice: its shots and sound play on, e.g. a real person's own clip) laid the way
    # dj tts lays them (dj/tts.py "put the holds back"): silence for their length, no gap after them. Without them the line after a
    # hold would run straight on from the one before, and the hold's clip would play over the narration
    by_id = {b["id"]: c for b, c in zip(beats, clips)}
    eid = [b["id"] for b in every]
    span = [b for b in every[eid.index(first):eid.index(last) + 1] if (b.get("voice") and not b.get("hold")) or b.get("hold")]
    beats = span
    clips = [np.zeros(int(round(b["hold"] * SR)), np.int16) if b.get("hold") else by_id[b["id"]] for b in span]
    spf = SR * ctx.fd[0] / ctx.fd[1]
    out, start_f = [], 0
    for i, (b, clip) in enumerate(zip(beats, clips)):
        dur = len(clip) / SR
        hold = b.get("hold")
        pad = 0.0 if hold else (tcfg["tail"] if i == len(beats) - 1 else tcfg["gap"])
        n = ctx.frames(dur + pad)
        o = {"id": b["id"], "voice": b["voice"], "start_f": start_f, "frames": n, "start": round(ctx.sec(start_f), 4),
             "voice_end": round(ctx.sec(start_f) + dur, 4), "end": round(ctx.sec(start_f + n), 4),
             "align": None if hold else str(pdir / f"{b['id']}_{picks[b['id']]}.align.json"), "take": None if hold else picks[b["id"]]}
        if hold:
            o["hold"] = hold
        out.append(o)
        start_f += n
    total = round(start_f * spf)
    nar = np.zeros(total, np.int16)
    for o, clip in zip(out, clips):
        s = round(o["start_f"] * spf)
        nar[s:s + len(clip)] = clip[:max(0, total - s)]
    raw, norm = ctx.path("voice", "narration_raw.wav"), ctx.path("voice", "narration.wav")
    write_wav(raw, nar)
    normalize(ctx, raw, norm)
    nar = read_wav(norm)
    nar = np.pad(nar, (0, max(0, total - len(nar))))[:total]
    write_wav(norm, nar)
    for o in out:
        a, b = round(o["start_f"] * spf), round((o["start_f"] + o["frames"]) * spf)
        o["wav"] = str(ctx.path("voice", f"{o['id']}.wav"))
        write_wav(o["wav"], nar[a:b])
    meta = {"engine": "elevenlabs", "format": ctx.fmt, "fps": ctx.rate, "total_frames": start_f, "duration": round(ctx.sec(start_f), 3),
            "narration": str(norm), "beats": out, "layout": f"{first}-{last} from autopick's picks (proto_narration.py)"}
    if i0 > 0 or i1 < len(beats_all) - 1:      # a part of the script (a prototype): dj and the gate hold only these beats
        meta["prototype"] = f"{first}-{last} from autopick's picks (proto_narration.py)"
    ctx.save_json("beats.json", meta)
    # the layout as laid: voice_chain.sh starts every run from these, and the gate's A1/A13 hold the final against them
    import shutil
    shutil.copy2(norm, ctx.path("voice", "narration_laid.wav"))
    shutil.copy2(ctx.build / "beats.json", ctx.build / "beats_laid.json")
    print(f"narration {first}-{last}: {ctx.sec(start_f):.2f} s, takes {sorted(set(picks.values()))} -> {norm} (+ narration_laid.wav)")


if __name__ == "__main__":
    main()
