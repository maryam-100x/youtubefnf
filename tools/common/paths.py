"""paths.py: where everything lives, for every tool in this repo. No tool writes a path of its own; each one imports these.

Two roots:
  REPO   this repository (the office: rules, standards, scripts, code). Found from this file's own place.
  MEDIA  the media root outside the repo (footage, renders, voice takes, music, effects, models, keys). Big files never go in git.
Both, and the programs the tools call, come from config/paths.toml, which the setup writes on the first run
(config/paths.example.toml shows every key). A key that is missing falls back to the default below.

  import sys; sys.path.insert(0, str(<repo>/"tools"/"common")); from paths import REPO, MEDIA, PY_PIPE, PY_EDIT, video_dirs
  python tools/common/paths.py            prints every path and whether it exists
"""
import os
import platform
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WINDOWS = platform.system() == "Windows"
MAC = platform.system() == "Darwin"
CONFIG = REPO / "config" / "paths.toml"

_cfg = {}
if CONFIG.exists():
    with open(CONFIG, "rb") as f:
        _cfg = tomllib.load(f)


def _get(key, default):
    v = _cfg.get(key) or os.environ.get("STUDIO_" + key.upper())
    return Path(v).expanduser() if v else Path(default).expanduser()


def _venv_python(venv):
    return venv / ("Scripts/python.exe" if WINDOWS else "bin/python")


# the media root: a short path with no spaces (Remotion, ffmpeg filters and bash all read it)
MEDIA = _get("media", "C:/Studio" if WINDOWS else "~/Studio")
# the Python environments the setup builds (their packages clash, so they are kept apart)
VENV_PIPE = _get("venv_pipeline", REPO / "tools" / ".venv")              # the pipeline: dj, voice, sound gate, pipe.py
VENV_EDIT = _get("venv_edit", MEDIA / "envs" / "edit")                   # picture and audio analysis: OpenCV, torch (CPU), QA tools
VENV_VISION = _get("venv_vision", MEDIA / "envs" / "vision")             # people and object detection for framing checks (YOLO)
VENV_ACCENT = _get("venv_accent", MEDIA / "envs" / "accent")             # the accent classifier
VENV_SYNTH = _get("venv_synth", MEDIA / "envs" / "synth")                # music made in code: Surge XT through pedalboard, the judge
PY_PIPE = _venv_python(VENV_PIPE)
PY_EDIT = _venv_python(VENV_EDIT)
PY_VISION = _venv_python(VENV_VISION)
PY_ACCENT = _venv_python(VENV_ACCENT)
PY_SYNTH = _venv_python(VENV_SYNTH)
FFMPEG = str(_cfg.get("ffmpeg") or "ffmpeg")
FFPROBE = str(_cfg.get("ffprobe") or "ffprobe")
NODE = str(_cfg.get("node") or "node")

# the repo's own places
TOOLS = REPO / "tools"
MOTION = TOOLS / "motion"              # the Remotion project
VIDEOS_REPO = REPO / "videos"          # each video's script, cue sheet, notes, settings (video.toml)
KB = REPO / "kb"                       # the knowledge base of the creator's niche

# the media root's places
VIDEOS = MEDIA / "videos"              # each video's build, renders and exports
PUBLIC = MEDIA / "motion"              # Remotion public dirs (the edits' pictures, clips, sounds)
FOOTAGE = MEDIA / "footage"            # source footage and stills, and their index
SFX = MEDIA / "sfx"                    # effects (the house set unzipped here, plus any the creator adds)
MUSIC = MEDIA / "music"                # music beds (licensed, generated or the creator's own)
MODELS = MEDIA / "models"              # model files the tools load (face detection and the like)
SECRETS = MEDIA / "secrets"            # API keys, one file each; never printed, never committed, never opened by an agent
TMP = MEDIA / "tmp"                    # lock files, heavy-job tickets, scratch
HEAVY = TMP / "heavy"                  # the heavy-job tickets (tools/pipeline/heavy.py)
APPS = MEDIA / "apps"                  # programs the setup unpacks (Surge XT for music made in code: apps/surge-xt)


def video_dirs(video):
    """(repo folder, media folder) of a video given its folder name, its number, or a path"""
    p = Path(video)
    if p.is_absolute() and p.exists():
        name = p.name
    else:
        hits = sorted(VIDEOS_REPO.glob(f"{video}*")) if VIDEOS_REPO.exists() else []
        name = hits[0].name if hits else str(video)
    return VIDEOS_REPO / name, VIDEOS / name


if __name__ == "__main__":
    if "--init" in sys.argv:  # the setup: create the media root's folders (never touches anything that exists)
        for d in (VIDEOS, PUBLIC, FOOTAGE, SFX, MUSIC, MODELS, SECRETS, TMP, HEAVY, MEDIA / "voice" / "guard" / "approved", MEDIA / "voice" / "guard" / "flagged", MEDIA / "envs"):
            Path(d).mkdir(parents=True, exist_ok=True)
    print("config", CONFIG, "(found)" if CONFIG.exists() else "(missing: defaults)")
    for k in ("REPO", "MEDIA", "PY_PIPE", "PY_EDIT", "PY_VISION", "PY_ACCENT", "PY_SYNTH", "MOTION", "VIDEOS", "PUBLIC", "FOOTAGE", "SFX", "MUSIC",
              "MODELS", "SECRETS", "TMP"):
        v = globals()[k]
        print(f"{k:10s} {v}  {'ok' if Path(v).exists() else '-'}")
    print("python", sys.version.split()[0], "os", platform.system())
