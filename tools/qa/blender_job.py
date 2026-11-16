"""A Blender render as a heavy job with Blender's own memory need. with_remotion_lock.sh takes a "render" ticket at Remotion's measured
10 GB, so a 4K Cycles still of a small scene would wait behind a commit limit it never reaches. This takes the same kind of ticket
with a need of its own (default 7 GB), runs Blender, and prints the process's measured peak memory, so the number stays a measurement.

  PIPE tools/qa/blender_job.py "<what>" [--need 6] -- <blender args...>

A small 4K Cycles scene at 256 samples peaks near 6 GB of commit (a 4 GB ask is too low): hence the default 7. The peak is Windows'
PeakPagefileUsage (commit) and peak working set; on macOS and Linux, the child's peak resident memory (getrusage).
Blender is found from config/paths.toml's `blender` key, else the STUDIO_BLENDER environment variable, else `blender` on the PATH
(macOS: also /Applications/Blender.app)."""
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / "common"))
sys.path.insert(0, str(TOOLS / "pipeline"))
from paths import CONFIG  # noqa: E402
from heavy import HeavyJob  # noqa: E402

WINDOWS = platform.system() == "Windows"
MAC = platform.system() == "Darwin"


def blender():
    try:
        with open(CONFIG, "rb") as f:
            v = tomllib.load(f).get("blender")
    except (OSError, tomllib.TOMLDecodeError):
        v = None
    v = v or os.environ.get("STUDIO_BLENDER") or shutil.which("blender")
    if not v and MAC and Path("/Applications/Blender.app/Contents/MacOS/Blender").exists():
        v = "/Applications/Blender.app/Contents/MacOS/Blender"
    return v or "blender"


def peak_gb(proc):
    """(peak commit GB, peak working set GB) of the finished process; on macOS/Linux both are the peak resident memory."""
    if WINDOWS:
        import ctypes
        import ctypes.wintypes as wt

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(wt.HANDLE(int(proc._handle)), ctypes.byref(c), c.cb)
        return c.PeakPagefileUsage / 2 ** 30, c.PeakWorkingSetSize / 2 ** 30
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss   # bytes on macOS, kilobytes on Linux
        gb = rss / 2 ** 30 if MAC else rss / 2 ** 20
        return gb, gb
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def main():
    argv = sys.argv[1:]
    if "--" not in argv or not argv or argv[0] == "--":
        sys.exit('usage: blender_job.py "<what>" [--need 6] -- <blender args...>')
    what = argv[0]
    need = 7.0
    if "--need" in argv[:argv.index("--")]:
        need = float(argv[argv.index("--need") + 1])
    rest = argv[argv.index("--") + 1:]
    with HeavyJob(what, "render", need_gb=need):
        p = subprocess.Popen([blender()] + rest)
        rc = p.wait()
        commit, ws = peak_gb(p)
        print(f"{what}: exit {rc}; Blender's peak commit {commit:.2f} GB, peak working set {ws:.2f} GB (asked {need:g})", flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
