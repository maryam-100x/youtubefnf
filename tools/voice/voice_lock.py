"""The voice lock (standard/VOICE_LOCK.md stage 3). A voice that keeps changing after it "passed" costs hours: each change moves the
timing, so the gate re-probes, the mix re-runs and the picture re-anchors. Once the voice is final it is locked: voice_lock.json (in
videos/<video>/) holds the hashes of the narration and the word files the picture anchors on, and

  - every tool that writes the narration or its word times refuses while the lock exists (guard_argv / guard_video, one line at the
    top of each writer: dj tts, dj captions, the voice chain, voice_patch, section_takes --use, fixmutes, tails --fix, relay, cutspan,
    close_gaps, inner_gaps, ...); the one way to change a locked voice is voice_layin.py, which lays a fix into the old slot without
    moving time and records it here;
  - `verify` (run by the sound gate before its checks, and by pipe.py before a render or a mix) fails when a locked file changed any
    other way (a `cp` in a shell script, a tool that has no guard yet): a lock is a hash, not a promise.
  - `unlock --why "<reason>"` is the explicit way out (a new script line, a re-voice of a whole section): the lock moves to
    voice_lock.unlocked.json with the reason and the time, the writers run again, and the voice is locked anew when it is final.

  EDIT tools/voice/voice_lock.py <video> lock [--note "..."]
  EDIT tools/voice/voice_lock.py <video> verify          (exit 1 when a locked file changed; prints which)
  EDIT tools/voice/voice_lock.py <video> status
  EDIT tools/voice/voice_lock.py <video> unlock --why "<reason>"
  EDIT tools/voice/voice_lock.py <video> refuse <tool>   (exit 4 while locked: for shell scripts, e.g. voice_chain.sh's first line)

Any python of the repo: only the standard library and tools/common/paths.py (the writers import it from the pipeline venv and the
editing venv alike)."""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import REPO, TOOLS, VIDEOS as MEDIA_VIDEOS, VIDEOS_REPO  # noqa: E402,F401

VIDEOS = VIDEOS_REPO          # the videos' repo folders (script.md, video.toml, the lock)
LOCK = "voice_lock.json"


def _toml(vd):
    try:
        import tomllib
        return tomllib.loads((vd / "video.toml").read_text(encoding="utf-8"))
    except Exception:
        text = (vd / "video.toml").read_text(encoding="utf-8")
        m = re.search(r'^dj\s*=\s*"([^"]+)"', text, re.M)
        s = re.search(r'^src\s*=\s*"([^"]+)"', text, re.M)
        return {"dj": m[1] if m else None, "video": {"src": s[1] if s else None}}


def video_dir(video):
    p = Path(str(video))
    if p.is_dir() and (p / "video.toml").exists():
        return p.resolve()
    if (VIDEOS / p.name / "video.toml").exists():
        return VIDEOS / p.name
    return None


def files(video):
    """the locked files: {name: path}"""
    vd = video_dir(video)
    cfg = _toml(vd)
    dj = Path(cfg.get("dj") or cfg.get("video", {}).get("dj") or MEDIA_VIDEOS / vd.name)   # the build's root (media root by default)
    b = dj / "build"
    out = {"narration": b / "voice" / "narration.wav", "words": b / "captions" / "words.json", "beats": b / "beats.json"}
    src = (cfg.get("video") or {}).get("src")
    if src:
        sd = TOOLS / "motion" / "src" / src
        out["edit_words"] = sd / "words.json"
        out["edit_beats"] = sd / "beats.json"
    return out


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def lock_file(video):
    vd = video_dir(video)
    return vd / LOCK if vd else None


def locked(video):
    lf = lock_file(video)
    if lf and lf.exists():
        return json.loads(lf.read_text(encoding="utf-8"))
    return None


def snapshot(video):
    return {k: {"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size} for k, p in files(video).items() if p.exists()}


def write_lock(video, d):
    lock_file(video).write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def lock(video, note=""):
    vd = video_dir(video)
    d = {"video": vd.name, "locked": time.strftime("%Y-%m-%dT%H:%M:%S"), "note": note, "files": snapshot(video), "layins": [],
         "script_sha256": sha(vd / "script.md") if (vd / "script.md").exists() else None}
    old = locked(video)
    if old:
        d["layins"] = old.get("layins", [])
    write_lock(video, d)
    return d


def verify(video):
    """-> [problems] (empty: every locked file is as locked)"""
    d = locked(video)
    if not d:
        return []
    bad = []
    for k, f in d["files"].items():
        p = Path(f["path"])
        if not p.exists():
            bad.append(f"{k}: {p} is gone")
        elif p.stat().st_size != f["bytes"] or sha(p) != f["sha256"]:
            bad.append(f"{k}: {p} changed since the lock ({time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))})")
    return bad


def record_layin(video, entry):
    """the lay-in's write: the new hashes, and the entry in the log (A10 listens at its edges)"""
    d = locked(video)
    if not d:
        return None
    d["files"] = snapshot(video)
    d.setdefault("layins", []).append({**entry, "when": time.strftime("%Y-%m-%dT%H:%M:%S")})
    write_lock(video, d)
    return d


def unlock(video, why):
    if not why or not why.strip():
        raise SystemExit("unlock needs --why: the reason goes on record")
    lf = lock_file(video)
    d = locked(video)
    if not d:
        raise SystemExit(f"{video}: not locked")
    hist = lf.with_name("voice_lock.unlocked.json")
    log = json.loads(hist.read_text(encoding="utf-8")) if hist.exists() else []
    log.append({**d, "unlocked": time.strftime("%Y-%m-%dT%H:%M:%S"), "why": why})
    hist.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    lf.unlink()
    return d


# ---------------------------------------------------------------- the writers' refusal

def refuse_msg(video, tool):
    return (f"\nVOICE LOCKED: {video} has videos/{video}/{LOCK}; {Path(str(tool)).name} would change the locked narration or its word "
            f"times.\n  A fix to a locked voice is laid into its old slot: tools/voice/voice_layin.py {video} <beat> <takes...>\n"
            f"  A real re-voice (new script lines, a whole section): tools/voice/voice_lock.py {video} unlock --why \"<reason>\", "
            f"then lock it again when it is final.\n")


def guard_video(video, tool):
    """refuse (exit 4) while `video` is locked"""
    vd = video_dir(video)
    if vd and (vd / LOCK).exists() and os.environ.get("VOICE_LOCK_LAYIN") != sha(vd / LOCK):
        sys.stderr.write(refuse_msg(vd.name, tool))
        raise SystemExit(4)


def _video_of(tok):
    if not tok or tok.startswith("-"):
        return None
    vd = video_dir(tok)
    if vd:
        return vd
    m = re.search(r"[\\/]videos[\\/]([^\\/]+)", tok)
    if m and video_dir(m[1]):
        return video_dir(m[1])
    if re.search(r"[\\/]", tok):        # a path under a locked video's build folder (its dj root from video.toml)
        try:
            p = str(Path(tok).resolve()).lower()
        except OSError:
            return None
        for lf in VIDEOS.glob(f"*/{LOCK}"):
            try:
                root = str(files(lf.parent)["narration"].parents[2].resolve()).lower()
            except Exception:
                continue
            if p.startswith(root):
                return lf.parent
    return None


def guard_argv(tool, when=None, unless=None):
    """the writers' first line: refuse when the command line names a locked video (its folder name, videos/<video>, or a file
    under the media root's videos/<video>/). when="--fix": only when that flag is given; unless="--dry": not when that flag is given
    (a read-only mode stays free)."""
    if (when and when not in sys.argv) or (unless and unless in sys.argv):
        return
    for tok in sys.argv[1:]:
        for part in str(tok).split("="):
            vd = _video_of(part)
            if vd:
                guard_video(vd, tool)


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("action", choices=["lock", "verify", "status", "unlock", "refuse"])
    ap.add_argument("tool", nargs="?", default="a shell script")
    ap.add_argument("--note", default="")
    ap.add_argument("--why", default="")
    a = ap.parse_args()
    vd = video_dir(a.video)
    if not vd:
        raise SystemExit(f"no video {a.video!r}")
    if a.action == "lock":
        d = lock(vd, a.note)
        print(f"LOCKED {vd.name}: " + ", ".join(f"{k} {v['sha256'][:12]}" for k, v in d["files"].items()))
    elif a.action == "verify":
        if not locked(vd):
            print(f"{vd.name}: not locked")
            return
        bad = verify(vd)
        print(f"VOICE LOCK {vd.name}: " + ("OK, every locked file as locked" if not bad else "BROKEN\n  " + "\n  ".join(bad) +
              "\n  only voice_layin.py may change a locked voice; restore the file or unlock with --why and lock again"))
        sys.exit(1 if bad else 0)
    elif a.action == "status":
        d = locked(vd)
        print(json.dumps(d, indent=1, ensure_ascii=False) if d else f"{vd.name}: not locked")
    elif a.action == "unlock":
        unlock(vd, a.why)
        print(f"UNLOCKED {vd.name}: {a.why}")
    elif a.action == "refuse":
        guard_video(vd, a.tool)


if __name__ == "__main__":
    main()
