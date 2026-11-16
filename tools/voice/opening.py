"""The opening screen: does a voice request open tired? A request with nothing spoken before it starts cold (low, flat, breathy, it
sounds exhausted at the very start), and the accent, name and word checks (autopick, the gate's A1-A11) don't hear it, so this does.

What it measures (standard/VOICE_LOCK.md "The opening"): a cold start keeps the voice's pitch peaks down for its first sentences
(the same text voiced cold and warm, 3 takes each: the first word 160 Hz cold against 193 Hz warm, "Pretty much" 172-183 against
200-221; the take caught up by its fifth sentence). So the opening's peaks are held against the request's own:

  peak_gap = mean of three, in semitones: F0 p95 over the opening's first 6 s of speech against the request's p95, and F0 p98 over
             its first 4 s and first 6 s against the request's p98 (Praat pitch, voiced speech frames; voice_guard_tone's frames)

A tired opening sits under its own request's peaks; a warm one reaches them. It is a verdict only where a cold start can be:
the video's first request (voiced after the warm-up) and any request voiced with under 10 s spoken before its span; a request with
its lines before (the two script lines before the span voiced inside the same request, then cut away) is warm by construction, and a
low reading there is the sentence's own intonation (a calm aside: 4 of 4 lines-before takes -0.58 to -1.42), so it is reported, never a
reject (autopick.opening_rejects, the gate's A12). Calibrated on takes with a verdict or a known way of voicing: cold (nothing spoken
before) -0.49 to -1.10; warm (the lines before, voiced in the same request, or the house warm-up) +0.21 to +2.9. TIRED below MIN_GAP (0.0): the midpoint.
Needs 6 s of speech in the opening and 12 s in the request, else it says UNKNOWN (never a pass by default: a short request is judged
on the narration around it in the gate).

  EDIT tools/voice/opening.py <wav> [--span T0 T1 ...] [--json]
      (no span: the whole wav is one request, as a take from span_takes.py)"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import voice_guard_tone as tone  # noqa: E402

MIN_GAP = 0.0          # st: under it, the opening never reaches its request's peaks (tired)
OPEN_S = (4.0, 6.0)    # s of speech the opening is read over
MIN_REQ_S = 12.0       # s of speech a request needs for its own reference


def st(a, b):
    return float(12 * np.log2(max(a, 1e-6) / max(b, 1e-6)))


def frames(wav):
    return tone.frames(tone.load(str(wav)))


OCTAVE = 1.5           # x: a voiced frame this far over or under the median of its 31 voiced neighbours is a tracker octave jump


def clean_f0(f0):
    """the F0 track with the pitch tracker's octave jumps out (7 frames at 275-283 Hz and one at 350 Hz inside one phrase, over a
    contour at ~140 Hz, can put a take's first 4 s at +4.5 st at p98 and pass a tired opening as +2.20 while its sister takes read
    -3.0 and -3.2): each voiced frame against the median of its 15 voiced neighbours either side (~300 ms of voicing); over x1.5
    (+7 st) or under /1.5 it is dropped."""
    f0 = np.asarray(f0, float).copy()
    vi = np.flatnonzero(f0 > 0)
    if len(vi) < 5:
        return f0
    vals = f0[vi]
    med = np.array([np.median(vals[max(0, i - 15):i + 16]) for i in range(len(vals))])
    bad = (vals > med * OCTAVE) | (vals < med / OCTAVE)
    f0[vi[bad]] = 0.0
    return f0


def _parts(fr, f0, sp, idx):
    """-> (parts, opening p95, request p95) or None: the three peak ratios over the given F0 track"""
    v = f0 > 0
    ref = f0[sp & v]

    def first(secs):
        m = np.zeros(len(v), bool)
        m[idx[:int(secs * 100)]] = True
        return f0[m & v]
    f4, f6 = first(OPEN_S[0]), first(OPEN_S[1])
    if len(f4) < 60 or len(f6) < 100 or len(ref) < 100:
        return None
    parts = {"p95_6s": st(np.percentile(f6, 95), np.percentile(ref, 95)), "p98_4s": st(np.percentile(f4, 98), np.percentile(ref, 98)),
             "p98_6s": st(np.percentile(f6, 98), np.percentile(ref, 98))}
    return parts, float(np.percentile(f6, 95)), float(np.percentile(ref, 95))


def peak_gap(fr, t0=0.0, t1=None):
    """the opening of the request that runs t0..t1 (s) -> {"gap", "gap_clean", "parts", "verdict", "speech_s"}. Two readings: the
    pitch track as Praat gives it (the calibration's: "gap") and with its octave jumps out (clean_f0: "gap_clean"); TIRED when either is
    under MIN_GAP. A few jumped frames lift the high percentiles the measure reads (one take: +2.20 as tracked, -1.89 clean), and the
    clean reading alone shifts the calibration (the cold takes' gaps rise toward 0), so the jumps can only make a take TIRED, never
    pass one: the calibration takes keep their verdicts, and every warm take's clean reading is +0.07 or more."""
    t1 = fr["seconds"] if t1 is None else t1
    sp = fr["speech"] & (fr["t"] >= t0) & (fr["t"] < t1)
    idx = np.flatnonzero(sp)
    out = {"t0": round(t0, 3), "t1": round(t1, 3), "speech_s": round(len(idx) / 100, 2)}
    if len(idx) < MIN_REQ_S * 100:
        return {**out, "gap": None, "verdict": "UNKNOWN", "why": f"only {len(idx) / 100:.1f} s of speech in the request"}
    raw = _parts(fr, np.asarray(fr["f0"], float), sp, idx)
    if raw is None:
        return {**out, "gap": None, "verdict": "UNKNOWN", "why": "too little voiced speech in the opening"}
    parts, o95, r95 = raw
    gap = float(np.mean(list(parts.values())))
    cl = _parts(fr, clean_f0(fr["f0"]), sp, idx)
    gap_clean = float(np.mean(list(cl[0].values()))) if cl else gap
    return {**out, "gap": round(gap, 3), "gap_clean": round(gap_clean, 3), "parts": {k: round(x, 3) for k, x in parts.items()},
            "opening_hz": round(o95, 1), "request_hz": round(r95, 1),
            "verdict": "TIRED" if min(gap, gap_clean) < MIN_GAP else "OK"}


def judge_wav(wav, spans=None):
    fr = frames(wav)
    return [peak_gap(fr, a, b) for a, b in (spans or [(0.0, None)])]


REF_MIN_S = 45.0       # s: the gate's reference for a short request reaches this far into the narration


def window(wav, t0, t1):
    """voice_guard_tone's frames for the narration between t0 and t1 only (a 48-min narration whole would take minutes and GBs)"""
    import soundfile as sf
    info = sf.info(str(wav))
    x, sr = sf.read(str(wav), dtype="float64", always_2d=True, start=int(t0 * info.samplerate), stop=int(t1 * info.samplerate))
    x = x.mean(1)
    if sr != tone.SR:
        raise SystemExit(f"{wav}: {sr} Hz, the tone frames need {tone.SR}")
    return tone.frames(x)


WARM_CONTEXT_S = 10.0  # s spoken before the span inside the request: warm by construction past it (autopick.py's own rule)


def openings(P):
    """the request openings in the final narration: the narration's first beat and the first beat of every section autopick picked
    (build/voice/autopick/*/autopick_*.json), each with the beat slots it spans and how many seconds the picked take had spoken before
    its span (the take's align.json "before_end"; None when unknown) -> [(beat, t0, t1, context_s)] in the narration's seconds"""
    bj = json.loads(Path(P["beats"]).read_text(encoding="utf-8"))
    beats = [b for b in bj["beats"] if b.get("voice_end") is not None]
    ids = [b["id"] for b in beats]
    spans, ctx = {}, {}
    raw = Path(P["dj"]) / "build" / "voice" / "patch" / "span_raw"
    for rec in sorted((Path(P["dj"]) / "build" / "voice" / "autopick").glob("*/autopick_*.json")):
        try:
            d = json.loads(rec.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        a, b = d.get("span", [None, None])
        if d.get("pick") is not None and a in ids and b in ids:
            spans[a] = b
            try:
                al = json.loads((raw / f"{d['stem']}_{d['pick']}.align.json").read_text(encoding="utf-8"))
                ctx[a] = float(al.get("before_end") or 0.0)
            except (OSError, ValueError, KeyError):
                ctx[a] = None
    out, firsts = [], ([ids[0]] if ids else []) + [a for a in spans if a != (ids[0] if ids else None)]
    for a in sorted(set(firsts), key=ids.index):
        b = spans.get(a, a)
        i0, i1 = ids.index(a), ids.index(b)
        out.append((a, float(beats[i0]["start"]), float(beats[i1]["voice_end"]), ctx.get(a)))
    return out


def gate(P, span=None):
    """A12 of the sound gate, per request opening in the final narration: the opening's pitch peaks against the request's own (its
    own span, as autopick judged the take; a request too short for that reads on to REF_MIN_S). TIRED is a flag on the video's first
    request and on any request whose picked take had under WARM_CONTEXT_S spoken before its span (a cold start: the lines before or
    the warm-up missing; the take's align.json "before_end"); on a request warm by construction it is reported (there the gap is the
    sentence's own intonation, as in a calm aside). A flag can't be allowed: the section is voiced again."""
    sys.path.insert(0, str(HERE.parent / "sound"))
    import gatelib as G
    import soundfile as sf
    dur = sf.info(str(P["final"])).duration
    flags, rows, first = [], [], True
    for beat, t0, t1, context_s in openings(P):
        is_first, first = first, False
        if span and not (span[0] - 1.0 <= t0 <= span[1] + 1.0):
            continue
        t1 = min(dur, t1 if t1 - t0 >= MIN_REQ_S + 3 else max(t1, t0 + REF_MIN_S))
        fr = window(P["final"], t0, t1)
        r = peak_gap(fr, 0.0, t1 - t0)
        if r["verdict"] == "UNKNOWN" and t1 < min(dur, t0 + REF_MIN_S):
            t1 = min(dur, t0 + REF_MIN_S)
            fr = window(P["final"], t0, t1)
            r = peak_gap(fr, 0.0, t1 - t0)
        r.update({"beat": beat, "t0": round(t0, 3), "t1": round(t1, 3), "context_s": context_s, "first": is_first})
        rows.append(r)
        if r["verdict"] == "TIRED" and (is_first or context_s is None or context_s < WARM_CONTEXT_S):
            how = "unknown" if context_s is None else f"{context_s:.1f} s"
            flags.append(G.flag("A12", f"opening:{beat}@{t0:.2f}", t0, beat, f"{beat} {msg(r)}; spoken before its span: {how} - voice "
                                "the section again the lines-before way (the first section after the warm-up); this flag can't be allowed",
                                hard=True))
    unknown = [r for r in rows if r["verdict"] == "UNKNOWN"]
    if unknown:
        print("     A12 openings too short to judge (report): " + ", ".join(f"{r['beat']} {G.fmt_t(r['t0'])}" for r in unknown))
    low = [r for r in rows if r["verdict"] == "TIRED" and not r["first"] and (r["context_s"] or 0) >= WARM_CONTEXT_S]
    if low:
        print("     A12 low openings on warm requests (report, the sentence's own intonation): " +
              ", ".join(f"{r['beat']} {min(r['gap'], r.get('gap_clean', r['gap'])):+.2f}" for r in low))
    return {"check": "A12", "final": str(P["final"]), "flags": flags, "openings": rows}


def msg(r):
    if r["verdict"] == "UNKNOWN":
        return f"opening unknown ({r['why']})"
    clean = r.get("gap_clean")
    return (f"opening {r['verdict'].lower()}: its pitch peaks {r['gap']:+.2f} st against the request's own"
            + (f" ({clean:+.2f} with the tracker's octave jumps out)" if clean is not None and abs(clean - r["gap"]) >= 0.005 else "")
            + f" (p95 {r['opening_hz']:.0f} Hz in its first 6 s, the request's {r['request_hz']:.0f} Hz; tired under {MIN_GAP:+.2f})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav")
    ap.add_argument("--span", nargs=2, type=float, action="append", metavar=("T0", "T1"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = judge_wav(a.wav, [tuple(s) for s in a.span] if a.span else None)
    if a.json:
        print(json.dumps(res))
    else:
        for r in res:
            print(f"{r['t0']:8.2f}-{r['t1']:8.2f}  {msg(r)}")
    sys.exit(1 if any(r["verdict"] == "TIRED" for r in res) else 0)


if __name__ == "__main__":
    main()
