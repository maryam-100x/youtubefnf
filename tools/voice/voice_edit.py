"""Edits to a finished narration that keep a take whole.

Why: patching one piece per line, each laid into its old slot, puts the old silence back around every line and cuts each piece at its
30-dB span with a 3 ms fade: a long pause appears where the picked take has under 0.12 s, and a click where a piece ends on a lip
smack. Here a take goes in as ONE piece across its lines, so it sounds exactly as it was picked; the lines' boundaries are set at the
take's own pauses, on whole video frames.

  span   lay one continuous take over beats FIRST..LAST: the first beat keeps its old lead silence (narration before its first word),
         the take follows from 30 ms before its first voiced sound, the last beat keeps its old tail (after its last word, to the next
         beat). --pieces a.wav b.wav ...: the take as consecutive files (span_takes.py's line pieces, cut at the quietest 10 ms
         between lines; the joins are the beat boundaries), raw: 1.04x and the voice chain (tools/sound/voice_level.py --chain mb) are
         applied as for every line. --piece x.wav --splits t1,t2,..: one processed file (already 1.04x + the chain) and the seconds in
         it where each next beat starts. The take is level-matched to the span it replaces (integrated loudness of the voiced parts).
  cut    remove a stretch of one beat (a sentence that goes): from the quietest 10 ms in --a (a window "t0,t1" in narration seconds),
         a whole number of frames long, so that the pause left equals --pause s; 20 ms crossfade.
Every later beat moves by the frames gained or lost (beats.json start_f, frames, start, voice_end, end, total_frames, duration);
the narration is rewritten in place (keep a backup). Then: `cd tools && PIPE -m dj captions ../videos/<video>` and
tools/motion/sync_words.py for the words.

  EDIT tools/voice/voice_edit.py span <build dir> S12 S13 --pieces p/S12_1.wav p/S13_1.wav
  EDIT tools/voice/voice_edit.py span <build dir> S40 S43 --piece outro.wav --splits 1.4,4.9,8.1
  EDIT tools/voice/voice_edit.py cut <build dir> S09 --a 50.95,51.20 --b 54.40,54.95 --pause 0.68"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import FFMPEG, PY_EDIT, TOOLS  # noqa: E402

sys.path.insert(0, str(HERE))
ED = str(PY_EDIT)
FPS = 60


def env(x, sr, hop=0.01):
    h = int(hop * sr)
    n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)


def voiced_span(x, sr, rel=30):
    e = env(x, sr)
    on = np.where(e > e.max() - rel)[0]
    return on[0] * 0.01, (on[-1] + 1) * 0.01


def process(raw, tmpdir, tempo=1.04):
    fast, d = tmpdir / (raw.stem + "_tempo.wav"), tmpdir / (raw.stem + "_chain.wav")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(raw), "-af", f"atempo={tempo}", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
                    str(fast)], check=True)
    subprocess.run([ED, str(TOOLS / "sound" / "voice_level.py"), str(fast), str(d), "--chain", "mb", "--lufs", "-14", "--ceil", "-1.5"],
                   check=True, capture_output=True)
    x, _ = sf.read(d, dtype="float64")
    return x


def loud(x, sr):
    s0, s1 = voiced_span(x, sr)
    v = x[int(s0 * sr):int(s1 * sr)]
    if len(v) > 0.5 * sr:
        return pyln.Meter(sr).integrated_loudness(v)
    return 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-12)


def shift_beats(B, i_from, d_frames):
    for b in B["beats"][i_from:]:
        b["start_f"] += d_frames


def retime(B):
    for b in B["beats"]:
        st = b["start_f"] / FPS
        dv = b.get("voice_end", b["end"]) - b["start"]
        de = b["end"] - b["start"]
        b["start"] = round(st, 4)
        b["end"] = round(st + b["frames"] / FPS, 4)
        b["voice_end"] = round(min(st + dv, b["end"]), 4) if de else b["end"]
    B["total_frames"] = sum(b["frames"] for b in B["beats"])


def main():
    __import__("voice_lock").guard_argv(__file__)  # the voice lock (standard/VOICE_LOCK.md): a locked narration is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["span", "cut"])
    ap.add_argument("build")
    ap.add_argument("first")
    ap.add_argument("last", nargs="?")
    ap.add_argument("--pieces", nargs="*")
    ap.add_argument("--piece")
    ap.add_argument("--splits")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--pause", type=float)
    ap.add_argument("--tempo", type=float, default=1.04, help="span --pieces: the speed-up (1.04 long form; a Short's hook ~1.1: 5.65 syllables a second)")
    ap.add_argument("--c2", type=float, help="cut: end the cut exactly here and put back silence for --pause")
    a = ap.parse_args()
    build = Path(a.build)
    nar = build / "voice" / "narration.wav"
    x, sr = sf.read(nar, dtype="float64")
    fpf = sr // FPS
    B = json.loads((build / "beats.json").read_text(encoding="utf-8"))
    ids = [b["id"] for b in B["beats"]]
    i0 = ids.index(a.first)

    if a.mode == "cut":
        b = B["beats"][i0]
        s_beat, e_beat = b["start_f"] * fpf, (b["start_f"] + b["frames"]) * fpf
        t0a, t1a = map(float, a.a.split(","))
        t0b, t1b = map(float, a.b.split(","))
        e = env(x[int(t0a * sr):int(t1a * sr)], sr)
        c1 = int((t0a + (int(np.argmin(e)) + 0.5) * 0.01) * sr)
        # the pause left = (c1 - the voice's end before it) + (the beat's end - c2): choose c2 in window b, c2 - c1 a whole number of frames
        e_before = env(x[int((t0a - 1.0) * sr):c1], sr)
        last_on = np.where(e_before > e_before.max() - 30)[0][-1]
        voice_end = int((t0a - 1.0) * sr) + (last_on + 1) * int(0.01 * sr)
        if a.c2 is None:
            want = int(e_beat - (a.pause * sr - (c1 - voice_end)))
            n = int(round((want - c1) / fpf))
            c2 = c1 + n * fpf
            pad = 0
            if not (t0b * sr <= c2 <= t1b * sr):
                raise SystemExit(f"cut: c2 {c2 / sr:.3f} outside {a.b}")
        else:
            # --c2: the cut ends exactly here (after a breath that runs up to the next word, which is never touched); silence is put
            # back so the pause left is --pause, the whole change a whole number of frames
            c2 = int(a.c2 * sr)
            left = (c1 - voice_end) + (e_beat - c2)
            n = int(round((c2 - c1 - max(0, a.pause * sr - left)) / fpf))
            pad = (c2 - c1) - n * fpf
            if pad < 0:
                raise SystemExit("cut: --c2 leaves no room")
        f = int(0.02 * sr)
        w = np.linspace(0, 1, f)
        join = x[c1 - f:c1] * (1 - w)                          # the voice's end fades into the cut (it is already near silence)
        head = x[c2:c2 + f] * w                                 # and what follows the cut fades in
        y = np.concatenate([x[:c1 - f], join, np.zeros(pad), head, x[c2 + f:]])
        b["frames"] -= n
        shift_beats(B, i0 + 1, -n)
        print(f"cut {a.first}: {c1 / sr:.3f}-{c2 / sr:.3f} out, {pad / sr:.3f} s of silence back ({n} frames, {n / FPS:.3f} s); pause left "
              f"{(c1 - voice_end + e_beat - c2 + pad) / sr:.2f} s")
    else:
        i1 = ids.index(a.last)
        span = B["beats"][i0:i1 + 1]
        s0 = span[0]["start_f"] * fpf
        s1 = (span[-1]["start_f"] + span[-1]["frames"]) * fpf
        old = x[s0:s1]
        v0, v1 = voiced_span(old, sr)
        lead, tail = int(v0 * sr), len(old) - int(v1 * sr)
        tmp = build / "voice" / "patch" / "voice_edit_tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        if a.pieces:
            parts = [process(Path(p), tmp, a.tempo) for p in a.pieces]
            joins = list(np.cumsum([len(p) for p in parts])[:-1])
            take = np.concatenate(parts)
        else:
            take, tsr = sf.read(a.piece, dtype="float64")
            if take.ndim == 2:
                take = take.mean(1)
            assert tsr == sr, "the piece's rate differs from the narration's"
            joins = [int(float(t) * sr) for t in a.splits.split(",")]
        if len(joins) != len(span) - 1:
            raise SystemExit(f"span {a.first}-{a.last}: {len(span)} beats need {len(span) - 1} splits, got {len(joins)}")
        g = 10 ** ((loud(old, sr) - loud(take, sr)) / 20)
        t0, t1 = voiced_span(take, sr)
        k0 = max(0, int((t0 - 0.03) * sr))
        take = take[k0:] * g
        joins = [j - k0 for j in joins]
        f = int(0.005 * sr)
        take[:f] *= np.linspace(0, 1, f)
        new = np.concatenate([np.zeros(lead), take, np.zeros(tail)])
        bounds = [0] + [int(round((lead + j) / fpf)) for j in joins] + [int(np.ceil(len(new) / fpf))]
        new = np.concatenate([new, np.zeros(bounds[-1] * fpf - len(new))])
        y = np.concatenate([x[:s0], new, x[s1:]])
        d = bounds[-1] - sum(b["frames"] for b in span)
        for k, b in enumerate(span):
            b["start_f"] = span[0]["start_f"] + bounds[k]
            b["frames"] = bounds[k + 1] - bounds[k]
        shift_beats(B, i1 + 1, d)
        print(f"span {a.first}-{a.last}: one take ({len(take) / sr:.2f} s, gain {20 * np.log10(g):+.2f} dB), lead {lead / sr:.2f} s, "
              f"tail {tail / sr:.2f} s; {d:+d} frames; beats " + ", ".join(f"{b['id']} {b['frames']}" for b in span))
    retime(B)
    B["duration"] = round(len(y) / sr, 3)
    sf.write(nar, y, sr, subtype="PCM_16")
    (build / "beats.json").write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"narration {B['duration']} s, {B['total_frames']} frames")


if __name__ == "__main__":
    main()
