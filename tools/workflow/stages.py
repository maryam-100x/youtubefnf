"""The stages of a long video, stamped in order, so the expensive steps can't run before what shapes them is settled (a full cut made
before the prototype passed is thrown away; voice changes after the voice "passed" and fact fixes after the voice each cost a patch
round). A stamp records when, the note (the creator's words for the creator's stamps), and the hash of script.md it was made on: when
the script changes after a stamp that depends on it, the stamp goes stale and the stages after it refuse.

  PIPE tools/workflow/stages.py <video> status
  PIPE tools/workflow/stages.py <video> stamp <stage> --note "the creator's words / the proof"
  PIPE tools/workflow/stages.py <video> require <stage>     (exit 2 with what's missing)
  from stages import require; require(video_dir, "render")   (raises SystemExit with what's missing)

The stages (each needs every stage before it, except where "needs" says otherwise):
  idea          the creator's pick, the "already on YouTube?" check done
  research      the research pack (research_pack.py), depth marks, CRITIC.md
  script        script.md final: lint clean, the blind gate run, coherency read of the script
  facts         every claim fact-checked against its source (script-hashed)
  coldread      a first-time listener's pass (script-hashed)
  bites         the bites table final: TEASE / PARAPHRASE lines are in the script (script-hashed)
  names         every name in names.json and every respelled name measured (script-hashed)
  prototype     the first 60 s at the finished look, the creator's pass (their words in the note)  [needs script]; "skip" when
                creator/choices.toml says prototype_first = false (the whole video in one go): nothing waits for it
  voice         the voice locked: voice_lock.json AND `voice_lock.py <video> verify` passes  [needs facts, coldread, bites, names]
  picture       every section built at the prototype's level, the gate passed on its code stamp
  render        the full render (pipe.py render)  [needs prototype, voice, picture]
  review        the review copy to the creator, their notes in REVIEW_vN.md, every fix a sample or a reel they rated
  final         the 4K and the upload pack (post.md)
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import PY_EDIT, REPO, TOOLS, VIDEOS_REPO  # noqa: E402

STAGES = ["idea", "research", "script", "facts", "coldread", "bites", "names", "prototype", "voice", "picture", "render", "review", "final"]
NEEDS = {
    "prototype": ["script"],
    "voice": ["facts", "coldread", "bites", "names"],
    "render": ["prototype", "voice", "picture"],
}
SCRIPT_HASHED = {"script", "facts", "coldread", "bites", "names"}
CREATOR = {"idea", "prototype"}   # the creator's calls: their note must quote the creator
CHOICES = REPO / "creator" / "choices.toml"


def prototype_first():
    """the creator's choice (creator/choices.toml, asked at setup): True = a prototype first; a missing file or key = True"""
    if not CHOICES.exists():
        return True
    import tomllib
    return bool(tomllib.loads(CHOICES.read_text(encoding="utf-8")).get("prototype_first", True))


def video_dir(v):
    p = Path(v)
    if p.is_dir():
        return p
    hits = sorted(VIDEOS_REPO.glob(f"{v}*"))
    if not hits:
        raise SystemExit(f"no video folder for {v!r}")
    return hits[0]


def script_hash(d):
    s = d / "script.md"
    return hashlib.sha256(s.read_bytes()).hexdigest()[:16] if s.exists() else None


def load(d):
    f = d / "stages.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def needs(stage):
    if stage in NEEDS:
        out = []
        for n in NEEDS[stage]:
            out += needs(n) + [n]
        return list(dict.fromkeys(out))
    i = STAGES.index(stage)
    return STAGES[:i]


def state(d, st, stage, h):
    """'ok', 'stale' (script changed since), 'missing', 'skip' (a prototype the creator chose not to have)"""
    if stage == "prototype" and not st.get(stage) and not prototype_first():
        return "skip"
    if stage == "voice":   # the voice is its lock (standard/VOICE_LOCK.md): it counts only while the locked files still hash as locked
        if not (d / "voice_lock.json").exists():
            return "missing"
        import subprocess
        r = subprocess.run([str(PY_EDIT), str(TOOLS / "voice" / "voice_lock.py"), d.name, "verify"], capture_output=True, text=True)
        return "ok" if r.returncode == 0 else "broken"
    s = st.get(stage)
    if not s:
        return "missing"
    if stage in SCRIPT_HASHED and s.get("script") and h and s["script"] != h:
        return "stale"
    return "ok"


def missing_for(d, stage):
    st, h = load(d), script_hash(d)
    return [(n, k) for n in needs(stage) if (k := state(d, st, n, h)) not in ("ok", "skip")]


def require(v, stage):
    d = video_dir(v)
    miss = missing_for(d, stage)
    if miss:
        raise SystemExit(f"{d.name}: '{stage}' needs " + ", ".join(f"{n} ({s})" for n, s in miss)
                         + f"  [stages.py {d.name} status; a stage is stamped with: stages.py {d.name} stamp <stage> --note ...]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("cmd", choices=["status", "stamp", "require", "unstamp"])
    ap.add_argument("stage", nargs="?")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    d = video_dir(a.video)
    st, h = load(d), script_hash(d)
    if a.cmd == "status":
        for s in STAGES:
            k = state(d, st, s, h)
            mark = {"ok": "done ", "stale": "STALE", "missing": "  -  ", "broken": "BROKE", "skip": "skip "}[k]
            e = st.get(s, {})
            print(f"{mark} {s:10} {e.get('at', '')[:16]:16} {e.get('note', '')[:100]}")
        nxt = next((s for s in STAGES if state(d, st, s, h) not in ("ok", "skip")), None)
        print(f"next: {nxt or 'done'}")
        return
    if a.stage not in STAGES:
        raise SystemExit(f"stage must be one of {STAGES}")
    if a.cmd == "require":
        miss = missing_for(d, a.stage)
        if miss:
            print(f"'{a.stage}' needs: " + ", ".join(f"{n} ({s})" for n, s in miss))
            sys.exit(2)
        print("ok")
        return
    if a.cmd == "unstamp":
        st.pop(a.stage, None)
    else:
        if a.stage in CREATOR and not a.note.strip():
            raise SystemExit(f"'{a.stage}' is the creator's call: --note with their words")
        miss = missing_for(d, a.stage)
        if miss:
            raise SystemExit(f"can't stamp '{a.stage}' yet: needs " + ", ".join(f"{n} ({s})" for n, s in miss))
        st[a.stage] = {"at": time.strftime("%Y-%m-%d %H:%M"), "note": a.note, **({"script": h} if a.stage in SCRIPT_HASHED else {})}
    (d / "stages.json").write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{a.cmd} {a.stage}: ok")


if __name__ == "__main__":
    main()
