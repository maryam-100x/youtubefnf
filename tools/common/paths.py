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
APPS = MEDIA / "apps"                  # the studio's own programs (tools/setup/apps.py): uv, Python, Node, ffmpeg, Surge XT
CACHE = MEDIA / "cache"                # the package managers' and libraries' caches, kept inside MEDIA too


def _app(key, win, mac, bare):
    """A program: the config key if set, else the studio's own copy in APPS, else the bare name (only before the setup put it there).
    The studio never runs the computer's own uv, Python, Node or ffmpeg: it has its own (SETUP.md, step 2)."""
    if _cfg.get(key):
        return str(_cfg[key])
    p = APPS / (win if WINDOWS else mac)
    return str(p) if p.exists() else bare


UV = _app("uv", "uv/uv.exe", "uv/uv", "uv")
NODE = _app("node", "node/node.exe", "node/bin/node", "node")
NPM = _app("npm", "node/npm.cmd", "node/bin/npm", "npm.cmd" if WINDOWS else "npm")
NPX = _app("npx", "node/npx.cmd", "node/bin/npx", "npx.cmd" if WINDOWS else "npx")
FFMPEG = _app("ffmpeg", "ffmpeg/bin/ffmpeg.exe", "ffmpeg/bin/ffmpeg", "ffmpeg")
FFPROBE = _app("ffprobe", "ffmpeg/bin/ffprobe.exe", "ffmpeg/bin/ffprobe", "ffprobe")
PYTHONS = APPS / "python"              # the Pythons uv installed for the environments (never the computer's own)
# the studio's program folders, first on PATH for every command the studio runs
BIN_DIRS = [APPS / "uv", APPS / "node" if WINDOWS else APPS / "node" / "bin", APPS / "ffmpeg" / "bin"]


def studio_env():
    """The variables every process of the studio runs with: its own programs first on PATH, and every package manager's and
    library's cache and settings inside MEDIA, so nothing of the computer's own (another uv, Python, Node or ffmpeg, their caches,
    a user config) is used or changed. Returns {"path": [folders to put first], "set": {name: value}, "dirs": [folders that must
    exist before a library looks (Ultralytics writes to C:/tmp when its folder is missing)], "media": MEDIA}."""
    p = Path.as_posix
    dirs = [CACHE / "uv", CACHE / "npm", CACHE / "ultralytics", CACHE / "matplotlib", MODELS / "hf", MODELS / "torch",
            MODELS / "u2net"]
    return {
        "media": p(MEDIA),
        "dirs": [p(d) for d in dirs],
        "path": [str(d) for d in BIN_DIRS],
        "set": {
            "UV_CACHE_DIR": p(CACHE / "uv"),
            "UV_PYTHON_INSTALL_DIR": p(PYTHONS),
            "UV_MANAGED_PYTHON": "1",                      # only the Pythons in PYTHONS, never one the computer has
            "UV_NO_CONFIG": "1",                           # no uv.toml of the computer's
            "UV_PYTHON_INSTALL_BIN": "0",                  # a Python uv installs puts nothing on the computer's PATH
            "UV_PYTHON_INSTALL_REGISTRY": "0",             # nor into Windows' registry
            "UV_CREDENTIALS_DIR": p(SECRETS / "uv"),       # an index install would open uv's store in the user's AppData
            "npm_config_cache": p(CACHE / "npm"),
            "npm_config_userconfig": p(APPS / "node" / "studio.npmrc"),   # never the user's own .npmrc
            "npm_config_update_notifier": "false",
            "npm_config_fund": "false",
            "HF_HOME": p(MODELS / "hf"),                   # speech to text, aligners, embeddings, the music judge
            "TORCH_HOME": p(MODELS / "torch"),
            "U2NET_HOME": p(MODELS / "u2net"),             # the cut-out model
            "YOLO_CONFIG_DIR": p(CACHE / "ultralytics"),
            "MPLCONFIGDIR": p(CACHE / "matplotlib"),
            "XDG_CACHE_HOME": p(CACHE),                    # yt-dlp and any other library that keeps a cache
        },
    }


def apply_env(env=None):
    """Put studio_env() into env (default: this process, so every program a tool starts gets it too). Safe to call twice."""
    env = os.environ if env is None else env
    s = studio_env()
    if MEDIA.is_dir():   # only once the setup made MEDIA (step 2): never a folder before the creator's media root exists
        for d in s["dirs"]:
            os.makedirs(d, exist_ok=True)
    for k, v in s["set"].items():
        env[k] = v
    key = next((k for k in env if k.upper() == "PATH"), "PATH")
    rest = [p for p in env.get(key, "").split(os.pathsep) if p and p not in s["path"]]
    env[key] = os.pathsep.join(s["path"] + rest)
    return env


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


def video_dirs(video):
    """(repo folder, media folder) of a video given its folder name, its number, or a path"""
    p = Path(video)
    if p.is_absolute() and p.exists():
        name = p.name
    else:
        hits = sorted(VIDEOS_REPO.glob(f"{video}*")) if VIDEOS_REPO.exists() else []
        name = hits[0].name if hits else str(video)
    return VIDEOS_REPO / name, VIDEOS / name


def _posix(p):
    """A folder as bash writes it: C:/Studio/apps -> /c/Studio/apps on Windows (Git Bash), unchanged elsewhere."""
    p = Path(p).as_posix()
    return "/" + p[0].lower() + p[2:] if WINDOWS and len(p) > 1 and p[1] == ":" else p


def shell_lines():
    """studio_env() as lines for bash or zsh to source: the variables, then the program folders put first on PATH (once)."""
    s = studio_env()
    out = [f"export {k}='{v}'" for k, v in s["set"].items()]
    first = ":".join(_posix(d) for d in s["path"])
    out.append(f'case ":$PATH:" in *":{first}:"*) ;; *) export PATH="{first}:$PATH" ;; esac')
    return out


apply_env()   # every tool imports this file: the programs it starts run with the studio's own programs and caches


def _run(argv):
    """paths.py --run [--in DIR] <command> [args]: one command with the studio's programs and caches (studio_env), in DIR (default:
    here). For the chat's own commands in a shell that hasn't got them (PowerShell, the first chat of the setup)."""
    import shutil
    import subprocess
    cwd = None
    if argv[:1] == ["--in"]:
        cwd, argv = argv[1], argv[2:]
    if not argv:
        raise SystemExit("usage: paths.py --run [--in DIR] <command> [args]")
    exe = shutil.which(argv[0], path=os.environ.get("PATH")) or argv[0]
    return subprocess.run([exe, *argv[1:]], cwd=cwd).returncode


if __name__ == "__main__":
    if sys.argv[1:2] == ["--run"]:
        raise SystemExit(_run(sys.argv[2:]))
    if sys.argv[1:2] == ["--env"]:  # the studio's variables as shell lines (sh: bash and zsh) or JSON
        if sys.argv[2:3] == ["json"]:
            import json
            print(json.dumps(studio_env(), indent=1))
        else:
            print("\n".join(shell_lines()))
        raise SystemExit(0)
    if "--init" in sys.argv:  # the setup: create the media root's folders (never touches anything that exists)
        for d in (VIDEOS, PUBLIC, FOOTAGE, SFX, MUSIC, MODELS, SECRETS, TMP, HEAVY, MEDIA / "voice" / "guard" / "approved",
                  MEDIA / "voice" / "guard" / "flagged", MEDIA / "envs", APPS, CACHE):
            Path(d).mkdir(parents=True, exist_ok=True)
    print("config", CONFIG, "(found)" if CONFIG.exists() else "(missing: defaults)")
    for k in ("REPO", "MEDIA", "PY_PIPE", "PY_EDIT", "PY_VISION", "PY_ACCENT", "PY_SYNTH", "MOTION", "VIDEOS", "PUBLIC", "FOOTAGE", "SFX", "MUSIC",
              "MODELS", "SECRETS", "TMP", "APPS", "CACHE"):
        v = globals()[k]
        print(f"{k:10s} {v}  {'ok' if Path(v).exists() else '-'}")
    for k in ("UV", "NODE", "NPM", "NPX", "FFMPEG", "FFPROBE"):
        v = globals()[k]
        own = Path(v).is_absolute() and Path(v).exists()
        note = "ok (the studio's own)" if own else "- (not installed yet: SETUP.md steps 2-3)"
        print(f"{k:10s} {v}  {note}")
    print("python", sys.version.split()[0], "os", platform.system())
