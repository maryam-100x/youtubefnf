"""Stage 0 of the voice lock: ready to voice (standard/VOICE_LOCK.md). A voice made before what shapes its words is settled gets
changed again and again after it "passed" (fact fixes, the cold read's lines, the bites' TEASE lines, a coherency line after the
picture), and every change costs a patch round. So the first take refuses until these are stamped on the CURRENT script:

  script     script.md final (lint, blind gate, coherency read of the script)
  facts      every claim fact-checked against its source
  coldread   a first-time listener's pass
  bites      the bites table final (its TEASE / PARAPHRASE lines are script lines)
  names      every proper noun in names.json (A6) and every respelled name MEASURED said the American way on a test take

The stamps live in ONE place, videos/<video>/stages.json, written by tools/workflow/stages.py (each script-hashed: an edit to
script.md after a stamp makes it stale). This tool reads them through stages.py's own functions (load, state, script_hash) and adds the
one stamp a machine can earn by itself: `names`, by measuring.

  EDIT tools/voice/voice_ready.py <video> status
  EDIT tools/voice/voice_ready.py <video> require [tool]     (exit 5 with what's missing; the voicing tools call require() at their start)
  EDIT tools/voice/voice_ready.py <video> names [--measure] [--k 2] [--stamp]
       A6 (names.py) + for every respelled name the script says (names.json "say" not "as is"): its "ipa" pair and a measured take.
       --measure voices the first beat that says it the lines-before way (span_takes.py: the two script lines before the beat voiced inside the
       same request, then cut away; k takes, ~300 credits a take) and judges the name on each take (saycheck.py); a name passes when a
       take is AMERICAN. --stamp writes the names stage through stages.py when all pass.

Shorts (video.toml kind = "short") are not held by it: the stages are the long form's.

The voicing tools call it first: dj tts (tools/dj/tts.py run), span_takes.py, section_takes.py, voice_patch.py, voice_versions.py,
autopick.py."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import PY_EDIT, PY_PIPE, TOOLS, VIDEOS  # noqa: E402
sys.path.insert(0, str(TOOLS / "workflow"))
import stages as ST  # noqa: E402

READY = ["script", "facts", "coldread", "bites", "names"]
GT = str(PY_PIPE)
ED = str(PY_EDIT)
NAMES = TOOLS / "sound" / "names.json"


def video_dir(video):
    p = Path(str(video))
    if p.is_dir() and (p / "script.md").exists():
        return p.resolve()
    return ST.video_dir(p.name)


def status(video):
    d = video_dir(video)
    st, h = ST.load(d), ST.script_hash(d)
    return d, {s: ST.state(d, st, s, h) for s in READY}, st


def is_short(d):
    try:
        import tomllib
        kind = (tomllib.loads((d / "video.toml").read_text(encoding="utf-8")).get("video") or {}).get("kind")
    except Exception:
        kind = None
    return kind == "short" or (kind is None and "short" in d.name)


def require(video, tool="voicing"):
    """the voicing tools' first line: refuse (exit 5) unless every ready stamp matches the current script.md (long videos: the stages
    are the long form's; a Short follows the Shorts process)"""
    d = video_dir(video)
    if d is None or is_short(d):
        return
    d, s, _ = status(d)
    # the names stage's own test takes (measure_name -> span_takes) run before the names stamp exists: that stamp is what they earn
    # (every other stamp is still required)
    skip = {"names"} if os.environ.get("VOICE_READY_NAMES_MEASURE") == "1" else set()
    miss = [f"{k} ({v})" for k, v in s.items() if v != "ok" and k not in skip]
    if not miss:
        return
    msg = (f"NOT READY TO VOICE: {d.name} needs " + ", ".join(miss) + f" on the current script.md before {Path(str(tool)).name}.\n"
           f"  stamps: tools/workflow/stages.py {d.name} stamp <stage> --note \"<the proof>\"; names by measure: "
           f"tools/voice/voice_ready.py {d.name} names --measure --stamp\n")
    sys.stderr.write(msg)
    raise SystemExit(5)


def _names():
    try:
        return json.loads(NAMES.read_text(encoding="utf-8")).get("names", {})
    except (OSError, ValueError):
        return {}


def respelled(d):
    """[(name, entry, first beat)] for every name the script says whose respelling is phonetic (a sound the voice may read its own way:
    'Sersha', 'Tee-bo'); a respelling into plain words the voice already says ('Night Owl', 'Ever Green') needs no measure, nor a name
    with an "ipa" pair it must still pass"""
    T = _names()
    sys.path.insert(0, str(TOOLS / "sound"))
    import names as N
    plain, _caps = N.plain_corpus()
    text = (d / "script.md").read_text(encoding="utf-8")
    beats = [(m[1], m[2]) for m in re.finditer(r"^\[(S[0-9]+[a-z]?)\]\s*VOICE:\s*(.*\S)\s*$", text, re.M)]
    out = []
    for name, e in T.items():
        if not isinstance(e, dict) or not e.get("say") or e["say"] == "as is":
            continue
        parts = [w.lower() for w in re.split(r"[\s-]+", e["say"]) if w]
        if e.get("measure") is False or ("ipa" not in e and all(w in plain or w in name.lower() or len(w) == 1 or w.isdigit() for w in parts)):
            continue
        pat = re.compile(r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])")
        first = next((b for b, v in beats if pat.search(v)), None)
        if first:
            out.append((name, e, first))
    return out


def names(video, measure=False, k=2, stamp=False):
    d = video_dir(video)
    sys.path.insert(0, str(TOOLS / "sound"))
    r = subprocess.run([ED, str(TOOLS / "sound" / "names.py"), d.name], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    a6 = r.returncode == 0
    print(("A6 PASS: every proper noun has an entry" if a6 else "A6 FAIL:\n" + r.stdout[-1500:]).rstrip())
    rows, ok = [], a6
    for name, e, beat in respelled(d):
        row = {"name": name, "say": e["say"], "beat": beat, "ipa": "ipa" in e, "takes": []}
        if "ipa" not in e:
            print(f"  {name}: respelled {e['say']!r} but no 'ipa' pair in names.json: it can't be measured (add the American and "
                  f"the native pronunciation, VOICE_LOCK.md)")
            ok = False
            rows.append(row)
            continue
        if measure:
            row["takes"] = measure_name(d, name, beat, k)
        good = [t for t in row["takes"] if t["verdict"] == "AMERICAN"]
        print(f"  {name} ({e['say']!r}, first in {beat}): " + (", ".join(f"take {t['k']} {t['verdict']} {t['margin']:+.3f}"
                                                                         for t in row["takes"]) or "not measured"))
        ok = ok and bool(good)
        rows.append(row)
    vb = _dj(d) / "build" / "voice"
    vb.mkdir(parents=True, exist_ok=True)
    (vb / "names_measured.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"NAMES {'READY' if ok else 'NOT READY'} ({len(rows)} respelled name(s); evidence {vb / 'names_measured.json'})")
    if ok and stamp:
        note = "A6 clean; measured American: " + "; ".join(
            f"{r['name']} take {max(r['takes'], key=lambda t: t['margin'])['k']} {max(t['margin'] for t in r['takes']):+.3f}"
            for r in rows if r["takes"]) if rows else "A6 clean; no respelled names"
        subprocess.run([GT, str(TOOLS / "workflow" / "stages.py"), d.name, "stamp", "names", "--note", note], check=True)
    return ok


def _dj(d):
    """the video's build root (video.toml dj =, else the media root's videos/<video>)"""
    import tomllib
    cfg = tomllib.loads((d / "video.toml").read_text(encoding="utf-8"))
    return Path(cfg.get("dj") or cfg.get("video", {}).get("dj") or VIDEOS / d.name)


def measure_name(d, name, beat, k):
    """k lines-before takes of the beat that first says the name (span_takes.py, the names table's respellings in the request), each judged"""
    sys.path.insert(0, str(HERE))
    import soundfile as sf
    import saycheck
    k0 = 900
    r = subprocess.run([GT, str(TOOLS / "voice" / "span_takes.py"), f"../videos/{d.name}", beat, beat, str(k0), str(k0 + k - 1),
                        "--name", f"names_{beat}"], cwd=str(TOOLS), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, "VOICE_READY_NAMES_MEASURE": "1"})
    if r.returncode:
        raise SystemExit(f"span_takes failed:\n{(r.stdout + r.stderr)[-1500:]}")
    pdir = _dj(d) / "build" / "voice" / "patch"
    out = []
    say = _names()[name]["say"]
    for kk in range(k0, k0 + k):
        w = pdir / f"{beat}_{kk}.wav"
        al = json.loads(w.with_suffix(".align.json").read_text(encoding="utf-8"))
        said = "".join(al["characters"]).strip()
        x, sr = sf.read(str(w), dtype="float32", always_2d=True)
        x = x.mean(1)
        form = say if say in said else name
        spans = saycheck.span_in(x, sr, said, form)
        for t0, t1 in spans[:1]:
            v = saycheck.judge(x, sr, t0, t1, saycheck.entry(name))
            out.append({"k": kk, **v})
    return out


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("cmd", choices=["status", "require", "names"])
    ap.add_argument("tool", nargs="?", default="voicing")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--stamp", action="store_true")
    a = ap.parse_args()
    if a.cmd == "status":
        d, s, st = status(a.video)
        for k, v in s.items():
            e = st.get(k, {})
            print(f"{'ok   ' if v == 'ok' else v.upper():7} {k:9} {e.get('at', ''):16} {e.get('note', '')[:110]}")
        print(f"READY TO VOICE: {'yes' if all(v == 'ok' for v in s.values()) else 'no'}")
    elif a.cmd == "require":
        require(a.video, a.tool)
        print("ready")
    else:
        sys.exit(0 if names(a.video, a.measure, a.k, a.stamp) else 1)


if __name__ == "__main__":
    main()
