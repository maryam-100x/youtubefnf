"""Shared pieces of the production line (tools/pipeline/pipe.py): where things are, the video's video.toml, running commands with a log,
and the one-render-at-a-time rule: heavy-job tickets (heavy.py) plus a check for Remotion's headless browsers, because two Remotion jobs
side by side kill each other's renders and a headless browser left behind keeps holding memory.

Nothing here needs a model to run. Pythons (tools/common/paths.py): PY_PIPE = the pipeline venv (this file runs in it), PY_EDIT = the
editing venv (OpenCV, numpy, the QA and sound tools), PY_VISION = the framing check's venv. Paths that are not here are read from the
video's video.toml."""
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent                     # tools/pipeline
sys.path.insert(0, str(HERE.parent / "common"))
from paths import NPX as paths_NPX  # noqa: E402
from paths import (FFMPEG, FFPROBE, MAC, MEDIA, MOTION, NODE, PUBLIC, PY_EDIT, PY_PIPE, PY_VISION, REPO, TMP, TOOLS,  # noqa: E402,F401
                   VIDEOS, VIDEOS_REPO, WINDOWS)
sys.path.insert(0, str(HERE))
import heavy  # noqa: E402   heavy jobs take turns across every chat on the computer

SCRIPT_TOOLS = TOOLS / "script"                            # the script craft's tools (script_lint.py)
QA_TOOLS = TOOLS / "qa"                                    # render and edit measures (qa_render.py, word_sheet.py)
SOUND = TOOLS / "sound"
VOICE = TOOLS / "voice"
WORKFLOW = TOOLS / "workflow"
# PUBLIC: the media every composition reads (the full public dir); each video's pub dir is a lean set of hard links into it
# TMP: Remotion's temp (kept off the system drive's temp so a cleaner never deletes a running render's files); the lock lives here too
NPX = paths_NPX                            # the studio's own npx (MEDIA/apps/node), tools/common/paths.py
LOCK = TMP / "remotion.lock"
HEADLESS = heavy.HEADLESS                                  # Remotion's browser process
FPS = 60


def say(msg):
    print(msg, flush=True)


def hhmm():
    return time.strftime("%H:%M:%S")


# ----------------------------------------------------------------------------------------------------------------------------- the video
def find_video(arg):
    """'012', '012-city-at-night', a path to the repo folder or to its video.toml -> the repo video folder."""
    p = Path(arg)
    if p.suffix == ".toml" and p.exists():
        return p.parent
    if p.is_dir() and (p / "video.toml").exists():
        return p.resolve()
    if (VIDEOS_REPO / arg).is_dir():
        return VIDEOS_REPO / arg
    hits = sorted(VIDEOS_REPO.glob(f"{arg}-*")) or sorted(VIDEOS_REPO.glob(f"{arg}*"))
    if not hits:
        raise SystemExit(f"no video folder for {arg!r} in {VIDEOS_REPO}")
    return hits[0]


class Video:
    """A video's settings: video.toml with defaults derived from the folder (kind from 'short' in the name, dj = VIDEOS/<slug> under the
    media root, pub = MEDIA/pub<id>, name = the folder's slug). Every path a step needs comes from here, never from a copy of a script."""

    def __init__(self, folder):
        self.folder = Path(folder)
        toml_path = self.folder / "video.toml"
        if not toml_path.exists():
            raise SystemExit(f"{toml_path} is missing: copy tools/pipeline/video.example.toml next to the script and fill it in")
        self.cfg = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        v = self.cfg.get("video", {})
        self.slug = self.folder.name
        self.id = v.get("id", self.slug[:3])
        self.kind = v.get("kind", "short" if "short" in self.slug.lower() else "long")
        self.name = v.get("name", self.slug)
        self.comp = v.get("comp")
        self.src = v.get("src")                           # tools/motion/src/<src>
        self.module = v.get("module", f"{self.comp}.tsx")
        self.fps = v.get("fps", FPS)
        self.dj = Path(v.get("dj", str(VIDEOS / self.slug)))   # the video's media folder: build, renders, exports, pipeline logs
        r = self.cfg.get("render", {})
        self.pub = Path(r.get("pub", str(MEDIA / f"pub{self.id}")))
        self.chunks = int(r.get("chunks", 10))
        self.concurrency = int(r.get("concurrency", 3))
        self.scale = r.get("scale", 1.3333333333333333)
        # the frames are drawn on the GPU ("angle"); "swangle" (software) for good once the GPU driver resets during a render
        # (pipe.py's GPU guard stops the line then)
        self.gl = r.get("gl", "angle")
        self.render_dir = self.dj / "render"
        self.export_dir = self.dj / "export"
        self.pipe_dir = self.dj / "pipeline"              # machine outputs of the line (logs, json), outside the repo

    def section(self, name):
        return self.cfg.get(name, {})

    @property
    def src_dir(self):
        return MOTION / "src" / self.src

    def words(self):
        return self.src_dir / "words.json"

    def beats(self):
        return json.loads((self.src_dir / "beats.json").read_text(encoding="utf-8"))

    def duration(self):
        """The composition's length in seconds: the beats' duration (Root.tsx builds the composition from it). A composition that ends
        before the voice file's tail (a Short that ends 0.4 s after its last word) gives its frames in video.toml ([video] frames)."""
        if self.section("video").get("frames"):
            return self.section("video")["frames"] / self.fps
        return float(self.beats()["duration"])

    def frames(self):
        return round(self.duration() * self.fps)

    def export_name(self, version):
        return f"{self.name}_v{version}"

    def __repr__(self):
        return f"Video({self.id} {self.kind} comp={self.comp} src={self.src} pub={self.pub})"


# -------------------------------------------------------------------------------------------------------------------------- running things
def run(cmd, cwd=None, log=None, env=None, check=True, quiet=False):
    """Run a command, print it, tee its output to a log when given. Returns the CompletedProcess (stdout holds the text)."""
    e = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if env:
        e.update(env)
    shown = " ".join(str(c) for c in cmd)
    if not quiet:
        say(f"$ {shown[:300]}{' ...' if len(shown) > 300 else ''}")
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None, env=e, capture_output=True, text=True, errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        Path(log).write_text(f"$ {shown}\n\n{out}", encoding="utf-8")
    if check and r.returncode != 0:
        tail = out[-2500:]
        raise SystemExit(f"FAILED (exit {r.returncode}): {shown[:200]}\n{tail}")
    r.stdout = out
    return r


def ffprobe(path, entries="stream=nb_read_packets,width,height,r_frame_rate:format=duration", count=True):
    cmd = [FFPROBE, "-v", "error", "-select_streams", "v:0"] + (["-count_packets"] if count else []) + ["-show_entries", entries, "-of", "default=nw=1", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return dict(ln.split("=", 1) for ln in out.splitlines() if "=" in ln)


def frame_count(path):
    """Decoded video frames of a file (packets; the renders are all-I or B-frame-free, so packets = frames)."""
    kv = ffprobe(path)
    n = kv.get("nb_read_packets", "")
    return int(n) if n.isdigit() else None


def loudness(path):
    """Integrated LUFS and true peak of a file's sound (ffmpeg's ebur128), for the summaries."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace").stderr
    import re
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return (float(i[-1]) if i else None, float(tp[-1]) if tp else None)


# ------------------------------------------------------------------------------------------------------------------- one Remotion job at a time
def processes(name):
    """How many processes of this image name run (Windows: tasklist; macOS and Linux: ps, matched on the program's file name)."""
    if WINDOWS:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"], capture_output=True, text=True, errors="replace").stdout
        return sum(1 for ln in out.splitlines() if ln.lower().startswith(name.lower()))
    out = subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True, errors="replace").stdout
    return sum(1 for ln in out.splitlines() if Path(ln.strip()).name.lower() == name.lower())


def pid_alive(pid):
    if WINDOWS:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, errors="replace").stdout
        return str(pid) in out
    try:
        os.kill(int(pid), 0)
    except PermissionError:
        return True
    except (OSError, ValueError, OverflowError):
        return False
    return int(pid) > 0


def read_lock():
    """The older lock file (TMP/remotion.lock), if a job of a tool that still writes one holds it (a lock whose job died is stale and goes)."""
    try:
        d = json.loads(LOCK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not pid_alive(d.get("pid", -1)):
        try:
            LOCK.unlink()
        except OSError:
            pass
        return None
    return d


def remotion_busy():
    """A reason a render can't start now, or None: heavy.py's tickets (every chat's heavy jobs), the old lock, or any headless browser
    (any Remotion render or stills run on this computer, ours or another chat's)."""
    d = read_lock()
    if d:
        return f"lock: {d.get('what')} since {d.get('started')} (pid {d.get('pid')})"
    return heavy.blocker("render", heavy.NEED_GB["render"])


class RemotionJob(heavy.HeavyJob):
    """`with RemotionJob('render 012 v2'):` waits until no other heavy job runs on the computer (heavy.py: renders run alone), then
    holds the ticket for this one. --wait 0 fails instead of waiting; the default waits as long as it takes, saying so every 5 minutes."""

    def __init__(self, what, wait_minutes=None):
        super().__init__(what, "render", wait_minutes)

    def __exit__(self, *exc):
        sweep_remotion()   # the job's leftovers go while it still holds its ticket (Remotion's temp grows by gigabytes a run otherwise)
        super().__exit__(*exc)
        after_remotion()


def sweep_remotion():
    """Remotion's leftovers (an assets folder and a browser profile per run, a bundle a killed job left) deleted for good: rtmp_sweep.py
    (it does nothing while a headless browser or compositor still runs). Never stops the line: a failure is said and passed."""
    try:
        r = subprocess.run([str(PY_PIPE), str(HERE / "rtmp_sweep.py"), "--min-age", "0", "--quiet"], capture_output=True,
                           text=True, timeout=900)
        out = (r.stdout or "").strip()
        if out:
            say(out.splitlines()[-1])
    except Exception as e:   # noqa: BLE001
        say(f"rtmp_sweep failed ({e}); the leftovers stay for the next job's sweep")


def after_remotion():
    """After any heavy job: no headless browser left behind, and the bundle copies in the temp."""
    left = processes(HEADLESS)
    bundles = sorted(TMP.glob("remotion-webpack-bundle-*")) if TMP.exists() else []
    size = sum(f.stat().st_size for b in bundles for f in b.rglob("*") if f.is_file()) / 1e9 if bundles else 0
    say(f"after: {left} {HEADLESS} left"
        f"{'; ' + str(len(bundles)) + ' bundle copies in ' + str(TMP) + f' ({size:.1f} GB): delete them, sized, when no render runs' if bundles else ''}")
    return left == 0


def temp_env():
    """Remotion's temp in TMP (Windows: TEMP and TMP; macOS and Linux: TMPDIR)."""
    TMP.mkdir(parents=True, exist_ok=True)
    if WINDOWS:
        return {"TEMP": str(TMP).replace("/", "\\"), "TMP": str(TMP).replace("/", "\\")}
    return {"TMPDIR": str(TMP)}


def safe_replace(src, dst, tries=6, pause=10):
    """Move a finished file into place. Windows refuses while the target is open (a player, Explorer's preview): retry, then leave the file
    beside the target and say where it is (a finished render must never be lost to an EPERM)."""
    src, dst = Path(src), Path(dst)
    for k in range(tries):
        try:
            os.replace(src, dst)
            return dst
        except PermissionError:
            if k == tries - 1:
                say(f"could not replace {dst.name} (it is open somewhere): the finished file is {src}")
                return src
            time.sleep(pause)
    return src


def disk_free_gb(path=None):
    """Free space on the drive that holds the media root (or `path`)."""
    p = Path(path) if path else MEDIA
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(str(p)).free / 1e9


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


if __name__ == "__main__":
    print(remotion_busy() or "Remotion free")
    print(heavy.status())
    print("python", sys.version.split()[0], "repo", REPO)
