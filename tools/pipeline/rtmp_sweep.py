"""Deletes what finished Remotion jobs leave behind in the render temp (TMP, tools/common/paths.py) and the user's temp folder.

Every render or stills run leaves a `remotion-v4.*-assets*` folder (the media it pulled in) and a `puppeteer_dev_chrome_profile-*` folder
(its browser profile) in its temp folder, and a stills run makes one of each per still: Windows file locks stop Remotion's own
clean-up, and left alone they reach ~100 GB and fill the disk. Also swept: react-motion-render*, remotion-webpack-bundle-* (a bundle a
killed job left), lean-pub-* (lean_bundle.mjs's empty dirs); the same names in the user's temp folder. Never touched: heavy/ (the
tickets), pub_* lean dirs, anything else.

Safe by construction: it sweeps only when no headless browser or Remotion compositor runs (else it says so and stops; when the
processes cannot be listed it sweeps nothing either), and it skips anything modified in the last --min-age minutes. Runs at the end of
every with_remotion_lock.sh job and after every pipe.py Remotion job (common.after_remotion), and by hand:
  PIPE tools/pipeline/rtmp_sweep.py [--dry] [--min-age 2] [--wait 15]
Deletes for good, never to a bin."""
import argparse
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import TMP  # noqa: E402


def user_temps():
    """The user's own temp folder(s), where a Remotion job run without TMP as its temp leaves its leftovers."""
    if platform.system() == "Windows":
        return [Path(os.path.expanduser("~")) / "AppData/Local/Temp"]
    out = [Path(tempfile.gettempdir())]
    try:   # macOS: the per-user temp folder even when TMPDIR points elsewhere for this run
        d = os.confstr("CS_DARWIN_USER_TEMP_DIR")
        if d:
            out.append(Path(d))
    except (ValueError, OSError, AttributeError):
        pass
    return out


DIRS = [Path(TMP)] + [d for d in user_temps() if d.resolve() != Path(TMP).resolve()]
PATTERNS = ["remotion-v4*", "puppeteer_dev_chrome_profile-*", "react-motion-render*", "remotion-webpack-bundle-*", "lean-pub-*"]
BUSY = ("chrome-headless-shell", "remotion")   # process names, without Windows' .exe


def running():
    """{pid: name} of headless browsers and Remotion compositors (heavy.py's process list: a Toolhelp snapshot on Windows, ps
    elsewhere); None when the processes cannot be listed."""
    try:
        sys.path.insert(0, str(HERE))
        import heavy
        procs = heavy.processes()
    except Exception:  # noqa: BLE001
        return None
    if not procs:
        return None
    strip = lambda n: n[:-4] if n.lower().endswith(".exe") else n
    return {pid: name for pid, name in procs.items() if strip(name).lower() in BUSY}


def size_of(p):
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="list, delete nothing")
    ap.add_argument("--min-age", type=float, default=2.0, help="minutes since the last change before an entry may go [2]")
    ap.add_argument("--wait", type=float, default=15.0, help="seconds to wait for a finished job's browser to exit [15]")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    t_end = time.time() + a.wait
    busy = running()
    while busy and time.time() < t_end:
        time.sleep(1)
        busy = running()
    if busy is None:
        print("rtmp_sweep: the running processes could not be listed: nothing swept")
        return 0
    if busy:
        print(f"rtmp_sweep: Remotion is running ({', '.join(f'{n} {p}' for p, n in list(busy.items())[:4])}): nothing swept")
        return 0
    cutoff = time.time() - a.min_age * 60
    n = freed = failed = 0
    for d in DIRS:
        if not d.exists():
            continue
        for pat in PATTERNS:
            for p in d.glob(pat):
                try:
                    if p.lstat().st_mtime > cutoff:
                        continue
                except OSError:
                    continue
                if a.dry:
                    freed += size_of(p) if p.is_dir() else p.lstat().st_size
                    n += 1
                    continue
                try:
                    s = size_of(p) if p.is_dir() else p.lstat().st_size
                    if p.is_dir() and not p.is_symlink():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    n += 1
                    freed += s
                except OSError:
                    failed += 1
    if not a.quiet or n:
        verb = "would free" if a.dry else "freed"
        print(f"rtmp_sweep: {n} leftovers {verb} {freed / 1e9:.2f} GB" + (f"; {failed} still locked, left" if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
