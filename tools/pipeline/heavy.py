"""Heavy jobs on this computer take turns, across every chat. Two memory-hungry jobs side by side (a background-removal cut-out takes
~20 GB of committed memory, a 4K finish ~3 GB) can run the computer out of memory and take every chat down with it. No chat sees another
chat's jobs, so each heavy job holds a ticket in HEAVY (tools/common/paths.py: MEDIA/tmp/heavy) while it runs, and waits for its turn
before it starts:

  render   a Remotion render, stills or patch: alone (no other ticket, no headless browser of another tool)
  cutout   a background-removal cut-out (matting models): never beside a render, never two at once (20 GB each)
  finish   the 4K encode (finish_long.py); score  score.py: never beside a render, beside one cut-out at most

On top of the kinds, a job starts only when the tickets' memory plus its own stays inside BUDGET_GB and the system has its memory free
(Windows: the commit headroom, RAM + pagefile, since running out of commit is what crashes it, not the RAM alone; macOS: free RAM plus free
swap). A ticket whose process died is stale and goes. Stdlib only (plus tools/common/paths.py), so every venv can use it:

  sys.path.insert(0, str(<repo>/"tools"/"pipeline")); from heavy import HeavyJob
  with HeavyJob("clean product_shot.png", "cutout"):
      ...
  PIPE tools/pipeline/heavy.py      what holds the computer now, and the memory
  PIPE tools/pipeline/heavy.py take <kind> "<what>" <pid>   waits for the turn, then leaves the ticket to process <pid> (a bash
      script's own: tools/motion/with_remotion_lock.sh), which deletes HEAVY/<pid>.json when its command ends"""
import ctypes
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import HEAVY  # noqa: E402

WINDOWS = platform.system() == "Windows"
if WINDOWS:
    from ctypes import wintypes as wt

DIR = HEAVY
GATE = DIR / ".gate"                       # held for the moment of checking and writing a ticket, so two jobs never both start
HEADLESS = "chrome-headless-shell.exe" if WINDOWS else "chrome-headless-shell"
NEED_GB = {"render": 10, "cutout": 20, "finish": 4, "score": 4}   # committed memory each kind takes at its peak (measured)
BUDGET_GB = 26                             # all tickets together, set for a computer with ~50 GB of commit whose own load (the apps, the
                                           # chats) takes ~12: lower it on a smaller machine
MARGIN_GB = 4                              # commit left free beyond a job's own need


# ------------------------------------------------------------------------------------------------------------- Windows, without subprocesses
if WINDOWS:
    class _MemStatus(ctypes.Structure):
        _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    class _ProcEntry(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wt.DWORD), ("szExeFile", ctypes.c_wchar * 260)]


def _sysctl(name):
    try:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _mac_memory():
    """macOS: (free RAM GB, free RAM + free swap GB, RAM + swap GB) from vm_stat and sysctl (free = free + inactive + purgeable pages)."""
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    page = 4096
    pages = {}
    for ln in out.splitlines():
        if "page size of" in ln:
            digits = "".join(ch for ch in ln.split("page size of", 1)[1] if ch.isdigit())
            page = int(digits) if digits else page
        elif ":" in ln:
            k, _, val = ln.partition(":")
            val = val.strip().rstrip(".")
            if val.isdigit():
                pages[k.strip()] = int(val)
    free = sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages purgeable", "Pages speculative")) * page / 2**30
    total = int(_sysctl("hw.memsize") or 0) / 2**30
    swap_total = swap_free = 0.0
    sw = _sysctl("vm.swapusage")   # "total = 2048.00M  used = 1024.00M  free = 1024.00M  (encrypted)"
    for key in ("total", "free"):
        if f"{key} =" in sw:
            num = sw.split(f"{key} =", 1)[1].split()[0]
            unit = num[-1:].upper()
            try:
                val = float(num[:-1]) / (1024 if unit == "M" else 1 if unit == "G" else 2**20 if unit == "K" else 1)
            except ValueError:
                val = 0.0
            if key == "total":
                swap_total = val
            else:
                swap_free = val
    return free, free + swap_free, total + swap_total


def memory():
    """(free RAM GB, free commit GB, commit limit GB). macOS has no commit limit: free RAM + free swap stands for it."""
    if not WINDOWS:
        return _mac_memory()
    m = _MemStatus()
    m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2**30, m.ullAvailPageFile / 2**30, m.ullTotalPageFile / 2**30


def processes():
    """{pid: image name} of every process (Windows: a Toolhelp snapshot, since tasklist hangs under load; macOS and Linux: ps)."""
    if not WINDOWS:
        try:
            out = subprocess.run(["ps", "-axo", "pid=,comm="], capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.TimeoutExpired):
            return {}
        procs = {}
        for ln in out.splitlines():
            pid, _, comm = ln.strip().partition(" ")
            if pid.isdigit():
                procs[int(pid)] = Path(comm.strip()).name
        return procs
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snap = k32.CreateToolhelp32Snapshot(2, 0)   # TH32CS_SNAPPROCESS
    if snap in (None, ctypes.c_void_p(-1).value):
        return {}
    out, e = {}, _ProcEntry()
    e.dwSize = ctypes.sizeof(e)
    try:
        ok = k32.Process32FirstW(ctypes.c_void_p(snap), ctypes.byref(e))
        while ok:
            out[e.th32ProcessID] = e.szExeFile
            ok = k32.Process32NextW(ctypes.c_void_p(snap), ctypes.byref(e))
    finally:
        k32.CloseHandle(ctypes.c_void_p(snap))
    return out


def msys_winpid(pid):
    """Windows only: the Windows pid behind an MSYS (Git Bash) pid, read from Git's /proc by its own cat.exe; None when there is no such
    MSYS pid (and always None on macOS and Linux, where a shell's pid is the real one)."""
    if not WINDOWS:
        return None
    cat = Path("C:/Program Files/Git/usr/bin/cat.exe")
    if not cat.exists():
        return None
    try:
        r = subprocess.run([str(cat), f"/proc/{int(pid)}/winpid"], capture_output=True, text=True, timeout=10)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    out = (r.stdout or "").strip()
    return int(out) if r.returncode == 0 and out.isdigit() else None


def windows_pid(pid):
    """The pid a `take` ticket belongs to. Windows: Git Bash's $$ and $BASHPID are MSYS pids, not Windows ones, and the same number may
    belong to a Windows service that never exits (its ticket would never go stale and would block every Remotion job). A pid that isn't
    a shell's is replaced by this process's nearest bash.exe/sh.exe ancestor: the subshell that runs the job and exits with it.
    macOS and Linux: the pid as given."""
    if not WINDOWS:
        return pid
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    tree, e = {}, _ProcEntry()
    e.dwSize = ctypes.sizeof(e)
    try:
        ok = k32.Process32FirstW(ctypes.c_void_p(snap), ctypes.byref(e))
        while ok:
            tree[e.th32ProcessID] = (e.szExeFile.lower(), e.th32ParentProcessID)
            ok = k32.Process32NextW(ctypes.c_void_p(snap), ctypes.byref(e))
    finally:
        k32.CloseHandle(ctypes.c_void_p(snap))
    shells = ("bash.exe", "sh.exe")
    if tree.get(pid, ("", 0))[0] in shells:
        return pid
    # an MSYS pid (a bash subshell's $BASHPID) is turned into its Windows pid by Git's own cat.exe first: the walk below would find the
    # stub bash.exe MSYS forks for the `take` command itself, which exits the moment take returns, so the ticket would go stale at once
    w = msys_winpid(pid)
    if w and tree.get(w, ("", 0))[0] in shells:
        return w
    p, seen = os.getpid(), set()
    while p in tree and p not in seen:
        seen.add(p)
        if tree[p][0] in shells:
            return p
        p = tree[p][1]
    return pid


# ------------------------------------------------------------------------------------------------------------------------------ tickets
def tickets(procs=None):
    """The live tickets; a ticket whose process is gone (or whose pid now belongs to another program) is stale and deleted."""
    procs = processes() if procs is None else procs
    live = []
    for f in sorted(DIR.glob("*.json")) if DIR.exists() else []:
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if procs.get(t.get("pid"), "").lower() != t.get("exe", "").lower():
            try:
                f.unlink()
            except OSError:
                pass
            continue
        live.append(t)
    return live


def waiters(procs=None):
    """The jobs waiting for their turn (<pid>.wait files beside the tickets); a dead one's file is stale and deleted."""
    procs = processes() if procs is None else procs
    live = []
    for f in sorted(DIR.glob("*.wait")) if DIR.exists() else []:
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if procs.get(t.get("pid"), "").lower() != t.get("exe", "").lower():
            try:
                f.unlink()
            except OSError:
                pass
            continue
        live.append(t)
    return live


def blocker(kind, need, procs=None, me=None):
    """Why a job of this kind can't start now, or None."""
    procs = processes() if procs is None else procs
    me = os.getpid() if me is None else me
    live = [t for t in tickets(procs) if t["pid"] != me]
    if kind == "render" and live:
        return "; ".join(f"{t['what']} ({t['kind']}, since {t['started']})" for t in live)
    if kind == "render":
        # a waiting score job (the voice chain's captions and mixes: short, and the critical path) goes before a waiting render or
        # stills run, so the voice chain never waits behind a queue of stills
        first = [w for w in waiters(procs) if w["kind"] == "score" and w["pid"] != me]
        if first:
            return f"{first[0]['what']} waits first (score before render, since {first[0]['since']})"
    for t in live:
        if t["kind"] == "render":
            return f"{t['what']} (render, since {t['started']})"
        if kind == "cutout" and t["kind"] == "cutout":
            return f"{t['what']} (another cut-out, since {t['started']})"
    if any(n.lower() == HEADLESS for n in procs.values()):   # no render ticket holds it: another tool's Remotion job
        return f"{HEADLESS} runs (a Remotion job of another tool)"
    held = sum(t["need_gb"] for t in live)
    if held + need > BUDGET_GB:
        return f"{held:g} GB of jobs run ({', '.join(t['what'] for t in live)}); this one needs {need:g} of the {BUDGET_GB} GB budget"
    if not WINDOWS:
        # macOS compresses and swaps on its own, so Windows' commit numbers don't fit it (a 16 GB Mac would never reach a render's
        # 10 GB + 4 free): the OS's own memory-pressure level decides (1 normal, 2 warning, 4 critical)
        lvl = _sysctl("kern.memorystatus_vm_pressure_level")
        if lvl and lvl != "1":
            return f"macOS reports {({'2': 'warning', '4': 'critical'}).get(lvl, lvl)} memory pressure: waiting until it is normal"
        return None
    ram, commit, limit = memory()
    if commit < need + MARGIN_GB:
        return f"the system has {commit:.1f} GB of commit free of {limit:.0f} (this job needs {need:g} + {MARGIN_GB} spare)"
    return None


class HeavyJob:
    """`with HeavyJob('finish 012 v3', 'finish'):` waits for its turn (saying why every 5 minutes), holds a ticket while the block runs.
    wait_minutes=None waits as long as it takes; a number fails with the reason once it runs out."""

    def __init__(self, what, kind, wait_minutes=None, need_gb=None, pid=None):
        if kind not in NEED_GB:
            raise ValueError(f"kind {kind!r}: one of {sorted(NEED_GB)}")
        self.what, self.kind, self.wait_minutes = what, kind, wait_minutes
        self.need = NEED_GB[kind] if need_gb is None else need_gb
        self.pid = os.getpid() if pid is None else pid   # another process may hold the ticket (`take`: a bash script's own pid)
        self.ticket = DIR / f"{self.pid}.json"

    def _take_gate(self):
        while True:
            try:
                os.close(os.open(GATE, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return
            except FileExistsError:
                try:
                    if time.time() - GATE.stat().st_mtime > 30:   # a job died between the check and its ticket
                        GATE.unlink()
                except OSError:
                    pass
                time.sleep(0.2)

    def __enter__(self):
        DIR.mkdir(parents=True, exist_ok=True)
        t0, last = time.time(), 0
        exe = processes().get(self.pid, Path(sys.executable).name)
        wait = DIR / f"{self.pid}.wait"
        wait.write_text(json.dumps({"pid": self.pid, "exe": exe, "what": self.what, "kind": self.kind,
                                    "since": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
        try:
            while True:
                self._take_gate()
                try:
                    why = blocker(self.kind, self.need, me=self.pid)
                    if not why:
                        self.ticket.write_text(json.dumps({"pid": self.pid, "exe": exe, "what": self.what, "kind": self.kind,
                                                           "need_gb": self.need, "started": time.strftime("%Y-%m-%d %H:%M:%S")}),
                                               encoding="utf-8")
                        break
                finally:
                    GATE.unlink(missing_ok=True)
                if self.wait_minutes is not None and time.time() - t0 > self.wait_minutes * 60:
                    raise SystemExit(f"{self.what}: still waiting after {self.wait_minutes} min for {why} (heavy jobs take turns)")
                if time.time() - last > 300:
                    print(f"{time.strftime('%H:%M:%S')} {self.what} waits its turn: {why}", flush=True)
                    last = time.time()
                time.sleep(15)
        finally:
            wait.unlink(missing_ok=True)
        print(f"{time.strftime('%H:%M:%S')} {self.what} starts ({self.kind}, ticket {self.ticket})", flush=True)
        return self

    def __exit__(self, *exc):
        self.ticket.unlink(missing_ok=True)


def status():
    procs = processes()
    ram, commit, limit = memory()
    lines = [f"RAM free {ram:.1f} GB; commit free {commit:.1f} of {limit:.0f} GB"]
    live = tickets(procs)
    lines += [f"  {t['kind']:<7}{t['need_gb']:>3g} GB  {t['what']} (pid {t['pid']}, since {t['started']})" for t in live] or ["  no heavy job holds a ticket"]
    n = sum(1 for p in procs.values() if p.lower() == HEADLESS)
    if n:
        lines.append(f"  {n} {HEADLESS} running")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "take":   # heavy.py take <kind> "<what>" <pid>: wait for the turn, leave the ticket to <pid>
        HeavyJob(sys.argv[3], sys.argv[2], pid=windows_pid(int(sys.argv[4]))).__enter__()
    else:
        print(status())
