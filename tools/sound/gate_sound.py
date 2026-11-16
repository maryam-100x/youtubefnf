"""The sound gate: every kind of sound fault a listener would catch, caught by a machine before anyone hears the voice.
One command after every voice chain, before any render or sample; one line per check, exit 1 while anything is flagged:

  A1 tails      final voice vs the raw takes, word by word: chopped word ends            tails.py
  A2 clicks     scraps after a mute (bar -55 dB): clicks                                  mutescan.py
  A3 pauses     pauses over 0.20 s inside a sentence, breaths left in a pause             pauses.py
  A4 noise      hiss and static in pauses, after the last word, anywhere loud             noisescan.py
  A5 takes      Whisper's words vs the script, v/f phrase ends, sentence loudness         takecheck.py
  A6 names      every proper noun has a voice spelling or "as is" in names.json           names.py
  A7 scraps     a word's head left before the word at a join (a "wor-word" stutter)      scraps.py
  A8 chain      a take spliced without chain D (crest), at another level, or clipped     chainmatch.py
  A9 inserts    an interview bite's split on sound, or the word's end left after it      insertcut.py
  A10 fragments voiced sound of 60 ms+ that no word of the script covers                  fragments.py
  A11 accent    the voice guard on the final narration: a hard ACCENT fails, never allowed   tools/voice/accent_take.py
  A12 opening   every request's opening reaches its own pitch peaks: a tired one, never allowed tools/voice/opening.py
  A13 hiss      no word's end lost at a cut: the final against the narration as laid out      hisstails.py
  LOCK          with videos/<video>/voice_lock.json: the narration and word files as locked (tools/voice/voice_lock.py)

A12 judges openings (the first request of a section has nothing spoken before it, so nothing in A1-A11 hears a tired start); A13 holds
every word end against the layout's own output, so a hand cut or a second chain run can never become its own reference.
A12 can't be allowed (the section is voiced again); A13's reference is <dj>/build/voice/narration_laid.wav (the layout's own output,
written by the voice layout, tools/voice/proto_narration.py) when it exists, else narration_prechain.wav.

A10 catches a stray piece of a word left at a splice that A1-A9 read past; A11's hard flags and a broken LOCK can't be allowed: a hard
accent is re-voiced, a lock is restored or unlocked with a reason. --span T0 T1 judges only flags inside those seconds (the lay-in's
changed span; A10 and A11 then listen only there).

A flag is fixed (fixmutes.py, tails.py --fix, a re-take, the chain) or proven wrong by its frames; only then may it be allowed, in
videos/<video>/gate_allow.json: {"allow": [{"check": "A1", "key": "<the flag's key>", "reason": "<the proof, in words>"}]}. An
entry without a reason, or with a key no flag has, is reported; an entry without a reason fails the gate. A check that can't run (a
missing file) fails it too. What each check catches and its numbers: tools/sound/SOUND_GATE.md.
A comma inside a spoken question is the script check's, not the gate's.

  EDIT tools/sound/gate_sound.py <video> [--final F --raw R --words W --script S]
      [--json out.json] [--allow gate_allow.json] [--only A1,A3] [--span T0 T1] [-v]   (-v: every flag; else the first 6 of each check)"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

CHECKS = [("A1", "tails"), ("A2", "clicks"), ("A3", "pauses"), ("A4", "noise"), ("A5", "takes"), ("A6", "names"), ("A7", "scraps"),
          ("A8", "chain"), ("A9", "inserts"), ("A10", "fragments"), ("A11", "accent"), ("A12", "opening"), ("A13", "hiss")]
NEVER_ALLOWED = {"A11": "hard ACCENT", "A12": "tired opening"}     # re-voiced, never allowed (VOICE_LOCK.md)


KEY_T = re.compile(r"^(.*)@(\d+(?:\.\d+)?)$")
SAME_T = 0.15


def same_key(allowed, flagged):
    """An allow matches its flag; a key that ends in a time (word:back@615.00, noise@170.90, long:possible@977.04) matches the same kind
    and word within SAME_T seconds: every dj captions pass moves Whisper's word times by a few hundredths (an allow proven on one pass
    would go stale on the next, word:back@615.00 -> @614.96), while the sound the proof is about stays where it is."""
    if allowed == flagged:
        return True
    a, f = KEY_T.match(allowed), KEY_T.match(flagged)
    return bool(a and f and a.group(1) == f.group(1) and abs(float(a.group(2)) - float(f.group(2))) <= SAME_T)


def lock_check(P):
    """[problems] when videos/<video>/voice_lock.json exists and a locked file changed (tools/voice/voice_lock.py verify)"""
    sys.path.insert(0, str(G.VOICE_TOOLS))
    try:
        import voice_lock
    except ImportError:
        return []
    if not voice_lock.locked(P["video_dir"]):
        return []
    return voice_lock.verify(P["video_dir"])


def load_allow(path):
    """-> (entries, errors)"""
    if not path or not Path(path).exists():
        return [], []
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [], [f"{path}: not JSON ({e})"]
    items = d.get("allow", []) if isinstance(d, dict) else d
    good, errors = [], []
    for i, e in enumerate(items):
        if not isinstance(e, dict) or not e.get("check") or not e.get("key"):
            errors.append(f"{Path(path).name} entry {i}: needs check and key")
        elif not str(e.get("reason", "")).strip():
            errors.append(f"{Path(path).name} entry {i} ({e['check']} {e['key']}): no reason: an allow needs its proof in words")
        else:
            good.append(e)
    return good, errors


def run_check(cid, P, shared):
    if cid == "A1":
        import tails
        if not Path(P["raw"]).exists():
            raise FileNotFoundError(f"no raw takes to compare with: {P['raw']}")
        shared["align"] = tails.Align(P["final"], P["raw"], P["words"])
        shared["align"]._ref = str(P["raw"])      # A13 reuses it when its reference is the same file (one copy of a long pair in memory)
        return tails.run(P, quiet=True, al=shared["align"])
    if cid == "A2":
        import mutescan
        return mutescan.run(P, al=shared.get("align"), quiet=True)
    if cid == "A3":
        import pauses
        return pauses.run(P, quiet=True)
    if cid == "A4":
        import noisescan
        return noisescan.run(P, quiet=True)
    if cid == "A5":
        import takecheck
        # a prototype's narration (tools/voice/proto_narration.py: beats.json says "prototype") holds only its own beats: the
        # script's other lines aren't voiced yet, so only the narration's beats are held against the script
        try:
            bj = json.loads(Path(P["beats"]).read_text(encoding="utf-8"))
            only = {b["id"] for b in bj["beats"]} if bj.get("prototype") else None
        except (OSError, ValueError, KeyError):
            only = None
        return takecheck.run(P, quiet=True, beats_only=only)
    if cid == "A6":
        import names
        return names.run(P, quiet=True)
    if cid == "A7":
        import scraps
        return scraps.run(P, quiet=True)
    if cid == "A8":
        import chainmatch
        return chainmatch.run(P, quiet=True)
    if cid == "A9":
        import insertcut
        return insertcut.run(P, quiet=True)
    if cid == "A10":
        import fragments
        return fragments.run(P, quiet=True, span=P.get("span"))
    if cid == "A11":
        return accent_check(P)
    if cid == "A12":
        sys.path.insert(0, str(G.VOICE_TOOLS))
        import opening
        return opening.gate(P, span=P.get("span"))
    if cid == "A13":
        import hisstails
        al = shared.get("align")       # A1's alignment, when it was made against the same reference
        same = al is not None and Path(getattr(al, "_ref", "")).resolve() == Path(hisstails.reference(P)).resolve()
        return hisstails.run(P, quiet=True, al=al if same else None)
    raise ValueError(cid)


def accent_check(P):
    """A11: the voice guard's accent on the final narration (tools/voice/accent_take.py in the pipeline venv): a hard ACCENT is a flag
    that can't be allowed. An ACCENT? (maybe) is reported, not failed: on an approved final voice it marks about a fifth of the sections
    that passed by ear, so as a gate it would be a false alarm a fifth of the time; the per-take pick (autopick.py) is where it rejects.
    With a span, only that stretch (+-1 s) is screened."""
    import subprocess
    import tempfile
    gt = str(G.PY_PIPE)
    tool = str(G.VOICE_TOOLS / "accent_take.py")
    if P.get("span"):
        import soundfile as sf
        a, b = max(0.0, P["span"][0] - 1.0), P["span"][1] + 1.0
        sr0 = sf.info(str(P["final"])).samplerate
        x, sr = sf.read(str(P["final"]), dtype="int16", always_2d=True, start=int(a * sr0), stop=int(b * sr0))
        W = [w for w in G.load_words(P["words"]) if w["start"] >= a and w["end"] <= b]
        tmp = Path(tempfile.mkdtemp(prefix="a11_"))
        sf.write(tmp / "span.wav", x, sr, subtype="PCM_16")
        (tmp / "words.json").write_text(json.dumps([{**w, "start": w["start"] - a, "end": w["end"] - a} for w in W]), encoding="utf-8")
        cmd, off = [gt, tool, str(tmp / "span.wav"), "--words", str(tmp / "words.json")], a
    else:
        cmd, off = [gt, tool, str(P["final"]), "--video", str(P["video_dir"]), "--words", str(P["words"])], 0.0
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or "{" not in r.stdout:
        raise RuntimeError(f"accent_take.py failed: {(r.stderr or r.stdout)[-400:]}")
    d = json.loads(r.stdout[r.stdout.index("{"):])
    flags = []
    for f in d["hard"]:
        t = f["start"] + off
        flags.append(G.flag("A11", f"accent:hard:{f['beat']}@{t:.2f}", t, f["beat"], "BRITISH (hard): " + f["msg"] +
                            " - re-voice the section whole (autopick.py / span_takes.py); this flag can't be allowed", hard=True))
    maybe = [{"beat": f["beat"], "t": round(f["start"] + off, 2), "msg": f["msg"]} for f in d["soft"]]
    if maybe:   # report only: about a fifth of an approved voice's sections carry one (VOICE_LOCK.md); autopick rejects them per take
        print(f"     A11 maybe-British (report, not a fail): " + ", ".join(f"{m['beat']} {G.fmt_t(m['t'])}" for m in maybe))
    return {"check": "A11", "final": str(P["final"]), "flags": flags, "maybe": maybe}


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--allow", help="the allow list (default videos/<video>/gate_allow.json)")
    ap.add_argument("--only", help="comma list of checks (A1..A13)")
    ap.add_argument("--span", nargs=2, type=float, help="judge only flags inside these narration seconds (a lay-in's changed span)")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    P = G.paths_from(a)
    P["span"] = a.span
    allow_path = Path(a.allow) if a.allow else P["video_dir"] / "gate_allow.json"
    allow, allow_errors = load_allow(allow_path)
    only = set(a.only.split(",")) if a.only else None
    for k in ("final", "words"):
        if not Path(P[k]).exists():
            print(f"SOUND GATE {P['video']}: FAIL, {k} missing: {P[k]}")
            sys.exit(1)
    print(f"SOUND GATE {P['video']}  ({time.strftime('%Y-%m-%d %H:%M')})\n  final  {P['final']}\n  raw    {P['raw']}\n  words  {P['words']}\n"
          f"  script {P['script']}\n  allow  {allow_path if allow_path.exists() else '(none)'}")
    shared, results, failed, used = {}, {}, False, set()
    lock_bad = lock_check(P)
    if lock_bad:
        print("LOCK    FAIL: the narration or its word files changed under the voice lock (can't be allowed):\n     " +
              "\n     ".join(lock_bad))
        failed = True
    for cid, name in CHECKS:
        if only and cid not in only:
            continue
        t0 = time.time()
        try:
            res = run_check(cid, P, shared)
        except Exception as e:              # a check that can't run is not a pass
            results[cid] = {"check": cid, "error": f"{type(e).__name__}: {e}", "flags": []}
            print(f"{cid} {name:7} FAIL: can't run ({type(e).__name__}: {e})")
            failed = True
            continue
        if a.span:
            res["flags"] = [f for f in res["flags"] if a.span[0] - 0.3 <= f["t"] <= a.span[1] + 0.3]
        open_, allowed = [], []
        for f in res["flags"]:
            never = cid in NEVER_ALLOWED and f.get("hard")
            hit = None if never else next((e for e in allow if e["check"] == cid and same_key(e["key"], f["key"])), None)
            if hit:
                used.add((cid, hit["key"]))
                allowed.append(dict(f, allowed=hit["reason"]))
            else:
                open_.append(f)
        res["open"], res["allowed"] = open_, allowed
        results[cid] = res
        dt = time.time() - t0
        if not open_:
            print(f"{cid} {name:7} PASS" + (f" ({len(allowed)} allowed)" if allowed else "") + f"  [{dt:.0f} s]")
            continue
        failed = True
        shown = open_ if a.v else open_[:6]
        items = "; ".join(f"{G.fmt_t(f['t'])} {f['word']!r}" if f["t"] or cid != "A6" else f"{f['word']!r}" for f in shown)
        more = f"; ... {len(open_) - len(shown)} more" if len(open_) > len(shown) else ""
        print(f"{cid} {name:7} {len(open_)} flag{'s' if len(open_) != 1 else ''}: {items}{more}" +
              (f" ({len(allowed)} allowed)" if allowed else "") + f"  [{dt:.0f} s]")
        if a.v:
            for f in open_:
                print(f"     {f['msg']}   [key {f['key']}]")
    ids = {c for c, _ in CHECKS} & (only or {c for c, _ in CHECKS})    # the file is shared with the picture gate (gate.py): its own checks are its
    stale = [] if a.span else [e for e in allow if e["check"] in ids and (e["check"], e["key"]) not in used]   # a span sees only its own flags
    for e in stale:
        print(f"  allow entry with no flag (stale, remove it): {e['check']} {e['key']}")
    for err in allow_errors:
        print(f"  ALLOW LIST ERROR: {err}")
        failed = True
    total = sum(len(r.get("open", [])) for r in results.values()) + sum(1 for r in results.values() if r.get("error"))
    print(f"SOUND GATE {'FAIL' if failed else 'PASS'}: {total} open flag{'s' if total != 1 else ''}"
          + ("" if not failed else " - fix each or prove it wrong by its frames; gate_allow.json only with that proof"))
    out = a.json or str(P["out"] / "gate_sound.json")
    try:
        G.write_json(out, {"video": P["video"], "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "pass": not failed,
                           "files": {k: str(P[k]) for k in ("final", "raw", "words", "script")},
                           "allow_errors": allow_errors, "stale_allows": stale,
                           "checks": {k: {kk: vv for kk, vv in v.items() if kk != "flags"} | {"flags": v.get("flags", [])}
                                      for k, v in results.items()}})
        print(f"  report -> {out}")
    except OSError as e:
        print(f"  (report not written: {e})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
