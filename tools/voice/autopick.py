"""Stage 1 of the voice lock: the machine picks the take (standard/VOICE_LOCK.md). Accent checks run per section, so a British stretch in
a kept section or a name said with a foreign accent is never kept "by measures". Every section is voiced K times the lines-before way
(span_takes.py: the two script lines before the span voiced inside the same request, then cut away; the names table's respellings in
it) and each take is judged by these ears:

  accent   the voice guard on the whole take (accent_take.py): a hard ACCENT or a maybe ACCENT? rejects the take;
  names    every name with an "ipa" pair in names.json said in it (saycheck.py): anything but AMERICAN rejects it;
  words    two recognisers against the script: the CTC letters (ctcalign.py) and Whisper (asr_words.py): a script word neither hears,
           or speech the script doesn't have (3+ letters), rejects it;
  opening  opening.py: a take whose first 4-6 s of speech never reach its own pitch peaks opened cold (cold takes measure -0.49 to
           -0.91 st, warm takes +0.06 to +2.9): rejected, voiced again. The video's first section gets the house warm-up spoken
           before it (span_takes.py, [tts.elevenlabs] warmup), as every other section gets its two lines before.
The pick is the clean take with the lowest accent score; a section with no clean take is never kept: the run stops (exit 2) and names
what to change (the British-pull phrases in the span and the two lines before, the names that failed), and the section is voiced again
with the cue reworded (standard/SOUND_AND_VOICE.md, the method step 4). Takes on disk can be judged without voicing (--score).

  EDIT tools/voice/autopick.py <video> <first beat> <last beat> [--k 3] [--k0 500]
      [--say WORD=SAYING ...]          voices k takes (span_takes.py, ~0.46 credits a character with the prefix), judges, picks
  EDIT tools/voice/autopick.py <video> --score <stem> <k> [<k> ...] [--first B --last B]
                                       judges takes already on disk: build/voice/patch/span_raw/<stem>_<k>_span.wav (+ .align.json)
Writes build/voice/autopick/<first>-<last>.json (every take's verdicts, the pick, script.md's hash); the pick is recorded only if
script.md is the same at the end as at the start (takes judged against old words never land). Splicing the pick in stays the chain's
step: `cd tools && PIPE voice/voice_patch.py ../videos/<video> <beats> --keep-old --use <beat>=<k> ...` (refused while the voice is
locked: use voice_layin.py)."""
import argparse
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np  # noqa: F401
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import PY_PIPE, REPO, TOOLS  # noqa: E402,F401
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sound"))
import ctcalign as C  # noqa: E402
import gatelib as G  # noqa: E402
import opening as O  # noqa: E402
import voice_layin as L  # noqa: E402
import voice_lock as VL  # noqa: E402
import voice_ready as R  # noqa: E402

GT = str(PY_PIPE)
BRITISH_PULL = ["straight away", "whilst", "rubbish", "brilliant", "proper", "reckon", "mate", "cheers", "fancy", "queue", "styoodio",
                "studio", "pound", "autumn", "the UK", "Britain", "British", "Scotland", "Scottish", "England", "London", "Edinburgh",
                "Glasgow", "Australia", "Australian"]


def span_sha(P, first, last):
    """the hash of the span's own lines as script.md has them now (a record stays valid for its span while those lines are unchanged:
    an edit elsewhere in the script re-voices only the sections it touches)"""
    import hashlib
    beats = G.script_beats(P["script"])
    ids = [b for b, _ in beats]
    if first not in ids or last not in ids:
        return None
    return hashlib.sha256("\n".join(v for _, v in beats[ids.index(first):ids.index(last) + 1]).encode("utf-8")).hexdigest()


def span_text(P, first, last):
    beats = G.script_beats(P["script"])
    ids = [b for b, _ in beats]
    i0, i1 = ids.index(first), ids.index(last)
    return beats, i0, i1, " ".join(v for _, v in beats[i0:i1 + 1])


def judge(P, wav, said, text, work, tag):
    """one take of the span: its words forced on, then voice_layin's three ears, then the opening (opening.py) -> verdicts"""
    x, sr = sf.read(str(wav), dtype="float64", always_2d=True)
    x = x.mean(1)
    al = C.align(x, sr, said)
    toks = text.split()
    m = L.map_said(toks, said.split())
    words = [{"w": toks[i], "start": al[m[i]]["start"], "end": al[m[i]]["end"]} for i in range(len(toks)) if i in m and m[i] < len(al)]
    take_words = [{"w": w["w"], "start": w["start"], "end": w["end"], "beat": "take"} for w in al]
    v = L.check_take(P, x, sr, words, text, work, tag, take=(wav, take_words))
    # the fourth ear (a take can sound exhausted at its very start): the opening's pitch peaks against the take's own (opening.py);
    # whether it rejects is decided in main() by how the request was voiced (cold or warm by construction)
    v["opening"] = O.judge_wav(wav)[0]
    return v


WARM_CONTEXT_S = 10.0   # s spoken before the span inside the request: past it the request is warm by construction


def opening_rejects(v, context_s, first_section):
    """The opening ear rejects a take when its request had less than WARM_CONTEXT_S spoken before the span (a cold start: the lines
    before missing or too short) or when it is the video's first section (the very start the viewer hears first; voiced after the
    warm-up). A request with its lines before (15-23 s of them) is warm by construction: there the peak gap is the sentence's own
    intonation, not a cold start (a calm aside voiced with 22.7 s before it read -0.58 to -1.42 in 4 of 4 takes, while the same text
    cold and warm split -0.49..-0.91 against +0.57..+0.70), so it is reported, never a reject."""
    op = v.get("opening") or {}
    if op.get("verdict") != "TIRED":
        return False
    if context_s < WARM_CONTEXT_S or first_section:
        v["why"] = v["why"] + [O.msg(op) + f" (spoken before the span: {context_s:.1f} s)"]
        v["clean"] = False
        return True
    v["opening_note"] = f"report only: {O.msg(op)}; {context_s:.1f} s spoken before the span (warm by construction)"
    return False


def in_place_rejects(v, listen):
    """The accent IN PLACE (the gate's A11): span_takes' listening file holds the take at the video's tempo between the narration's own
    3 s before and after it (when a narration exists: a re-take; the full voice has none, and the gate's A11 judges the joins there);
    the guard on all four 0.125-s grid offsets (accent_take.py --in-place): British on any of them, or maybe British on the
    narration's own grid, rejects. Alone, a take's last second is under-covered by the guard's 2-s windows: a take can read 0.35-0.44
    at its end alone and be a 4-s British stretch (0.76) at the join into the next beat in the narration."""
    pj = listen.with_suffix(".place.json")
    if not listen.exists() or not pj.exists():
        return False
    pl = json.loads(pj.read_text(encoding="utf-8"))
    if not pl.get("pre") or pl.get("s0") is None:
        return False
    r = subprocess.run([GT, str(HERE / "accent_take.py"), str(listen), "--in-place", f"{pl['pre']:.3f}",
                        f"{pl['pre'] + pl['take']:.3f}", "--grid-t0", f"{pl['s0']:.3f}"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        ip = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        v["why"] = v["why"] + ["the in-place accent could not run: " + (r.stderr or r.stdout)[-300:]]
        v["clean"] = False
        return True
    v["in_place"] = {"hard": ip["hard"], "soft": ip["soft"], "gate": ip["gate"], "max": [o["max"] for o in ip["offsets"]]}
    why = [h["msg"] for h in ip["hard"]] + [s["msg"] for s in ip["soft"] if ip.get("gate") is None or s["offset"] == ip["gate"]]
    if why:
        v["why"] = v["why"] + ["accent in place: " + "; ".join(why)]
        v["clean"] = False
        return True
    return False


def unsay(said):
    """the names table's respellings back to the names ('Sersha Nwin' -> 'Saoirse Nguyen'): a take judged against its own words"""
    for name, e in L.names_table().items():
        if isinstance(e, dict) and e.get("say") and e["say"] != "as is" and e["say"] in said:
            said = said.replace(e["say"], name)
    return said


def pulls(beats, i0, i1, say=()):
    ctx = " ".join(v for _, v in beats[max(0, i0 - 2):i1 + 1])
    return [p for p in BRITISH_PULL if re.search(r"(?<![A-Za-z])" + re.escape(p) + r"(?![A-Za-z])", ctx, re.I)]


def main():
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("first", nargs="?")
    ap.add_argument("last", nargs="?")
    ap.add_argument("--first", dest="first_o")
    ap.add_argument("--last", dest="last_o")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--k0", type=int, default=500)
    ap.add_argument("--say", nargs="*", default=[])
    ap.add_argument("--score", nargs="+", metavar=("STEM", "K"), help="judge takes on disk: <stem> <k> [<k> ...]")
    a = ap.parse_args()
    a.first, a.last = a.first_o or a.first, a.last_o or a.last
    P = G.paths(a.video)
    h0 = VL.sha(P["script"])
    pdir = P["dj"] / "build" / "voice" / "patch"
    raw = pdir / "span_raw"
    if a.score:
        stem, ks = a.score[0], [int(k) for k in a.score[1:]]
        if not (a.first and a.last):
            m = re.search(r"(S\d+[a-z]?)(?:-(S\d+[a-z]?))?$", stem)
            if not m:
                raise SystemExit(f"give --first/--last for {stem}")
            a.first, a.last = m[1], m[2] or m[1]
    else:
        R.require(P["video_dir"], "autopick.py")
        if not (a.first and a.last):
            raise SystemExit("give the section's first and last beat")
        # a name that comes out American in only some takes gets enough takes for a clean one (names.json "ipa" "hit_rate": the share
        # of lines-before takes measured American; 1 - (1 - rate)^k >= 90 %, at most 8): a name at 0.3 -> 7 takes
        _, _, _, span_txt = span_text(P, a.first, a.last)
        for name, e in L.names_table().items():
            rate = ((e or {}).get("ipa") or {}).get("hit_rate") if isinstance(e, dict) else None
            if rate and 0 < rate < 1 and re.search(r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])", span_txt):
                need = min(8, math.ceil(math.log(0.1) / math.log(1 - rate)))
                if need > a.k:
                    print(f"{name}: American in {rate:.0%} of takes -> {need} takes instead of {a.k}")
                    a.k = need
        stem, ks = f"autopick_{a.first}-{a.last}", list(range(a.k0, a.k0 + a.k))
        cmd = [GT, str(TOOLS / "voice" / "span_takes.py"), f"../videos/{P['video']}", a.first, a.last, str(ks[0]), str(ks[-1]),
               "--name", stem] + (["--say"] + a.say if a.say else [])
        # a re-take next to a narration: its listening file holds the narration's own seconds around it (the in-place accent ear);
        # span_takes' default context (narration_unlifted.wav) exists only where a lift ran
        vb = P["dj"] / "build" / "voice"
        if not (vb / "narration_unlifted.wav").exists() and (vb / "narration.wav").exists() and (P["dj"] / "build" / "beats.json").exists():
            cmd += ["--context", "narration.wav"]
        print(f"voicing {len(ks)} takes of {a.first}-{a.last} (span_takes.py, the lines-before way)")
        r = subprocess.run(cmd, cwd=str(TOOLS), capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout[-1200:])
        if r.returncode:
            raise SystemExit(f"span_takes failed: {r.stderr[-1500:]}")
    beats, i0, i1, text = span_text(P, a.first, a.last)
    work = P["dj"] / "build" / "voice" / "autopick" / f"{a.first}-{a.last}"
    work.mkdir(parents=True, exist_ok=True)
    rows = []
    for k in ks:
        wav = raw / f"{stem}_{k}_span.wav"
        alj = raw / f"{stem}_{k}.align.json"
        if not wav.exists() or not alj.exists():
            print(f"  take {k}: not on disk ({wav.name})")
            continue
        al = json.loads(alj.read_text(encoding="utf-8"))
        said = "".join(al["characters"]).strip()
        # the head of the next line was voiced after the span and cut away from the audio: cut it from the text too
        nxt = beats[i1 + 1][1] if i1 + 1 < len(beats) else "And that's it."
        h = nxt.split()[0]
        j = said.rfind(" " + h)
        if j > 0 and len(said) - j <= len(" ".join(nxt.split()[:3])) + 12:
            said = said[:j].strip()
        ref = unsay(said) if a.score else text     # takes on disk: judged against the words they were sent (the script may have moved on)
        try:
            v = judge(P, wav, said, ref, work, f"{stem}_{k}")
        except (ValueError, KeyError) as e:
            print(f"  take {k}: can't judge ({e})")
            continue
        opening_rejects(v, float(al.get("before_end") or 0.0), i0 == 0)
        in_place_rejects(v, pdir / f"samples_{stem}" / f"{stem}_{k}.wav")
        acc = (v.get("accent") or {}).get("score")
        rows.append({"k": k, "clean": v["clean"], "why": v["why"], "accent_score": acc,
                     "names": [{kk: n_[kk] for kk in ("name", "verdict", "margin", "heard")} for n_ in v["names"]],
                     "ctc_heard": v.get("ctc_heard"), "whisper_heard": v.get("whisper_heard"), "missing": v.get("missing"),
                     "opening": v.get("opening"), "opening_note": v.get("opening_note"),
                     "context_s": float(al.get("before_end") or 0.0), "in_place": v.get("in_place")})
        op = v.get("opening") or {}
        print(f"  take {k}: {'CLEAN' if v['clean'] else 'REJECT: ' + '; '.join(v['why'])}" + (f"  (accent {acc:.2f})" if acc is not None else "")
              + (f"  (opening {op['gap']:+.2f} st" + (", report only: warm by construction" if v.get("opening_note") else "") + ")"
                 if op.get("gap") is not None else ""))
        for n_ in v["names"]:
            print(f"      {n_['name']}: {n_['verdict']} {n_['margin']:+.3f} (heard {n_['heard']!r})")
    clean = [r for r in rows if r["clean"]]
    pick = min(clean, key=lambda r: (r["accent_score"] if r["accent_score"] is not None else 1.0,
                                     -min([n_["margin"] for n_ in r["names"]] or [0]))) if clean else None
    same = VL.sha(P["script"]) == h0
    out = {"video": P["video"], "span": [a.first, a.last], "stem": stem, "script_sha256": h0, "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "span_sha256": span_sha(P, a.first, a.last), "takes": rows, "pick": pick["k"] if pick and same else None}
    if not same:
        out["refused"] = "script.md changed during the run"
    (work / f"{stem}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    if not same:
        print("STOP: script.md changed during the run: no pick recorded (the takes were judged against the old words)")
        sys.exit(5)
    if not pick:
        bad_names = sorted({n_["name"] for r in rows for n_ in r["names"] if n_["verdict"] != "AMERICAN"})
        p = pulls(beats, i0, i1)
        if rows and all(any(str(w).startswith("opening tired") for w in r["why"]) for r in rows):
            print("  every take opened tired: the request needs spoken context before it (the two lines before; the first "
                  "section [tts.elevenlabs] warmup), never a rewording or a gain")
        print(f"NO CLEAN TAKE in {len(rows)}: never kept. Reword the cue and voice it again" +
              (f"; British pull in the span or the 2 lines before: {', '.join(p)}" if p else "") +
              (f"; names that failed: {', '.join(bad_names)} (another respelling in names.json, measured)" if bad_names else ""))
        sys.exit(2)
    print(f"PICK: take {pick['k']} of {stem} ({len(clean)} clean of {len(rows)}); splice: cd tools && PIPE voice/voice_patch.py "
          f"../videos/{P['video']} {' '.join(b for b, _ in beats[i0:i1 + 1])} --keep-old --use "
          + " ".join(f"{b}={pick['k']}" for b, _ in beats[i0:i1 + 1]))


if __name__ == "__main__":
    main()
