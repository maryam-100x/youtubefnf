"""Shared bits of the sound gate (every kind of sound fault caught by a machine before anyone listens): a video's files from its
video.toml, mono audio, level frames, words, the script's beats, flags and the allow list.

A video is its folder name under videos/ (e.g. 012-city-at-night); its media files come from video.toml's `dj` path, else
MEDIA/videos/<video>:
  final  <dj>/build/voice/narration.wav            the voice after the clean-up chain
  raw    <dj>/build/voice/narration_prechain.wav   the takes before the clean-up (the chain copies it there)
  words  <dj>/build/captions/words.json            Whisper's words (beat, w, start, end)
  beats  <dj>/build/beats.json
  script videos/<video>/script.md                  beats as `[S01] VOICE: ...`
  out    <dj>/pipeline/gate_sound/                 reports
Every tool takes --final/--raw/--words/--script to run the same code on an old state (a proof on a past version of the voice).

Run in the editing venv (numpy, soundfile, scipy, pyloudnorm): EDIT tools/sound/<tool>.py"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import KB, MEDIA, PY_EDIT, PY_PIPE, REPO, TOOLS, VIDEOS as MEDIA_VIDEOS, VIDEOS_REPO  # noqa: E402,F401

VIDEOS = VIDEOS_REPO            # the repo's video folders (script, video.toml, notes)
SOUND = Path(__file__).resolve().parent
VOICE_TOOLS = TOOLS / "voice"
MOTION = TOOLS / "motion"


def video_dir(video):
    p = Path(video)
    if p.is_dir() and (p / "video.toml").exists():
        return p.resolve()
    p = VIDEOS / video
    if not (p / "video.toml").exists():
        hits = sorted(VIDEOS.glob(f"{video}*/video.toml")) if VIDEOS.exists() else []
        if hits:
            return hits[0].parent
        raise SystemExit(f"no video.toml for {video!r} (looked in {p})")
    return p


def read_toml(path):
    text = Path(path).read_text(encoding="utf-8")
    if tomllib:
        return tomllib.loads(text)
    m = re.search(r'^dj\s*=\s*"([^"]+)"', text, re.M)  # fallback: only what the gate needs
    return {"dj": m[1] if m else None, "video": {}}


def paths(video, final=None, raw=None, words=None, beats=None, script=None, out=None):
    """The files of a video; any given path wins (old states for the proofs)."""
    vd = video_dir(video)
    cfg = read_toml(vd / "video.toml")
    dj = cfg.get("dj") or cfg.get("video", {}).get("dj")
    dj = Path(dj).expanduser() if dj else MEDIA_VIDEOS / vd.name
    b = dj / "build"
    P = {
        "video": vd.name, "video_dir": vd, "dj": dj, "cfg": cfg,
        "final": Path(final) if final else b / "voice" / "narration.wav",
        # the takes before the chain: the layout's own output when there is one, so a second chain run (or a hand cut before it)
        # never becomes the reference the final is compared with
        "raw": Path(raw) if raw else (b / "voice" / "narration_laid.wav" if (b / "voice" / "narration_laid.wav").exists()
                                      else b / "voice" / "narration_prechain.wav"),
        "words": Path(words) if words else b / "captions" / "words.json",
        "beats": Path(beats) if beats else b / "beats.json",
        "script": Path(script) if script else vd / "script.md",
        "out": Path(out) if out else dj / "pipeline" / "gate_sound",
    }
    return P


def add_path_args(ap):
    ap.add_argument("video", help="folder name under videos/ (e.g. 012-city-at-night)")
    ap.add_argument("--final", help="the voice to check (default <dj>/build/voice/narration.wav)")
    ap.add_argument("--raw", help="the takes before the chain (default narration_prechain.wav)")
    ap.add_argument("--words", help="words.json (default <dj>/build/captions/words.json)")
    ap.add_argument("--beats", help="beats.json (default <dj>/build/beats.json)")
    ap.add_argument("--script", help="script.md (default videos/<video>/script.md)")
    ap.add_argument("--json", help="write the result here")
    return ap


def paths_from(a):
    return paths(a.video, final=a.final, raw=getattr(a, "raw", None), words=a.words, beats=getattr(a, "beats", None),
                 script=getattr(a, "script", None))


# ---------------------------------------------------------------- audio

def load_mono(path):
    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    return x.mean(1), sr


def frame_db(x, sr, hop=0.005):
    """RMS level of consecutive frames of `hop` seconds, dBFS"""
    h = max(1, int(round(hop * sr)))
    n = len(x) // h
    if n < 1:
        return np.zeros(0)
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)


def db(a):
    return float(20 * np.log10(np.sqrt(np.mean(np.asarray(a, dtype=np.float64) ** 2)) + 1e-12)) if len(a) else -120.0


# ---------------------------------------------------------------- words and script

def load_words(path):
    W = json.loads(Path(path).read_text(encoding="utf-8"))
    W = W["words"] if isinstance(W, dict) else W
    out = []
    for w in W:
        out.append({"w": w.get("w", w.get("word", "")), "start": float(w["start"]), "end": float(w["end"]), "beat": w.get("beat", "")})
    return sorted(out, key=lambda w: (w["start"], w["end"]))


BEAT_RE = re.compile(r"^\[(S[0-9]+[a-z]?)\]\s*VOICE:\s*(.*\S)\s*$", re.M)


def script_beats(path):
    """[(beat id, voice text)] from script.md's `[S01] VOICE: ...` lines (comments and hold beats without VOICE skipped)"""
    text = Path(path).read_text(encoding="utf-8")
    return [(m[1], m[2]) for m in BEAT_RE.finditer(text)]


def key(t):
    return re.sub(r"[^a-z0-9]", "", t.lower().replace("’", "'"))


def sentence_end(w):
    return bool(re.search(r"[.!?][\"”')]*$", w.strip()))


def fmt_t(t):
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{t % 60:05.2f}"


# ---------------------------------------------------------------- flags

def flag(check, key_, t, word, msg, **extra):
    """one finding: `key` is what gate_allow.json names to allow it (stable across runs of the same audio)"""
    return {"check": check, "key": key_, "t": round(float(t), 3), "word": word, "msg": msg, **extra}


def wkey(word, t):
    return f"{key(word) or '_'}@{t:.2f}"


def write_json(path, obj):
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=float), encoding="utf-8")


def print_flags(res, limit=40):
    fl = res["flags"]
    for f in fl[:limit]:
        print(f"  {f['check']} {fmt_t(f['t'])} ({f['t']:.2f} s) {f['word']!r}: {f['msg']}   [key {f['key']}]")
    if len(fl) > limit:
        print(f"  ... {len(fl) - limit} more")


def utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
