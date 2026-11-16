"""PreToolUse hook (Bash, PowerShell): refuse to START a memory-heavy job while the computer's memory is at or over 85% of its limit.
Several model-loading jobs side by side (speech recognition at ~3 GB each, picture embeddings at 2-3 GB each, other chats' jobs) can
run the memory out, and then the computer dies and every chat with it. A limit written as a sentence gets broken; this is the
mechanism.

A heavy job = a model load or a render: autopick, ASR/alignment/accent checks, find_shot with embeddings (--no-embed passes), Whisper,
the gate/render/stills/finish/score steps of pipe.py, Remotion renders and stills, eye packets, cut-outs and depth passes. Everything
else passes, and so does any job while memory is under the line. What is read:
  Windows  the commit (GlobalMemoryStatusEx: the page file total and what's left of it = Task Manager's "Committed" against its limit)
  macOS    the OS's own memory-pressure level (sysctl kern.memorystatus_vm_pressure_level): a heavy job waits at warning or critical
  Linux    MemTotal - MemAvailable against MemTotal (/proc/meminfo)
Anything that cannot be read passes: the hook never blocks work it cannot judge.

Exit 2 refuses the call (the reason goes back to the model); anything else passes."""
import json
import platform
import re
import subprocess
import sys

LINE = 0.85
HEAVY = [
    (r"autopick\.py", "autopick (ASR models, ~2.9 GB)"),
    (r"(asr_words|ctcalign|accent_take|saycheck|accent_id|rhotic|voice_check)\.py", "a voice check (model load)"),
    (r"voice_lock\.py\b(?![^\n]*\b(verify|status)\b)", "the voice lock"),
    (r"\bwhisper\b|faster_whisper|whisperx", "Whisper"),
    (r"find_shot\.py(?![^\n]*--no-embed)", "find_shot with embeddings (add --no-embed for keywords only)"),
    (r"pipe\.py\s+\S+\s+(render|gate|stills|finish|score|probe|voice)\b", "a pipe.py heavy step"),
    (r"remotion\s+(render|still)|render_parts\.mjs|stills\.mjs|render_lean\.sh|centre_proof\.mjs", "a Remotion render or stills run"),
    (r"eye_packet\.py", "an eye packet (GPU decode)"),
    (r"rembg|kit3d_assets\.py|make_icon\.py|--cutouts?\b|birefnet|cutout\w*\.py", "cut-outs, depth or face models", 0.70),
    (r"finish_long\.py|splice_patch\.py|score\.py\s", "a finish, splice or mix"),
    # the biggest measured: a job that can grow by its own size needs that much headroom (the line is lower): a whole-narration
    # voice_level.py run peaked at ~18 GB, a range of cut-outs at ~19 GB. The windowed voice jobs (tails.py --span/--show read ~3 s of
    # two files, voice_layin.py a +/-15-s window) only load a model (accent_take's size): the model-load line. The first matching
    # pattern wins, so the windowed one sits above the whole-file one.
    (r"tails\.py[^\n]*--(span|show)\b|voice_layin\.py", "a windowed voice job (a model load, ~3 GB)"),
    (r"voice_level\.py|voice_chain\.sh|breath\.py|tails\.py|hiss\w*\.py",
     "a whole-narration voice job (voice_level.py on a whole narration can peak at ~18 GB, tails.py --fix at ~10 GB)", 0.60),
]
# a pattern's own line where it has one (third item), else LINE


def _windows():
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        return None
    total, avail = m.ullTotalPageFile, m.ullAvailPageFile
    return (total - avail) / total, (total - avail) / 2**30, total / 2**30


def _mac():
    out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
    page = 4096
    pages = {}
    for ln in out.splitlines():
        if "page size of" in ln:
            digits = "".join(ch for ch in ln.split("page size of", 1)[1] if ch.isdigit())
            page = int(digits) if digits else page
        elif ":" in ln:
            k, _, v = ln.partition(":")
            v = v.strip().rstrip(".")
            if v.isdigit():
                pages[k.strip()] = int(v)
    total = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5).stdout.strip() or 0)
    if not total or not pages:
        return None
    if "Anonymous pages" in pages:   # app memory = anonymous pages that are not purgeable
        app = pages["Anonymous pages"] - pages.get("Pages purgeable", 0)
    else:
        app = pages.get("Pages active", 0)
    used = (app + pages.get("Pages wired down", 0) + pages.get("Pages occupied by compressor", 0)) * page
    return used / total, used / 2**30, total / 2**30


def _linux():
    info = {}
    with open("/proc/meminfo", encoding="utf-8") as fh:
        for ln in fh:
            k, _, v = ln.partition(":")
            if v.strip().split():
                info[k] = int(v.strip().split()[0]) * 1024
    total, avail = info.get("MemTotal"), info.get("MemAvailable")
    if not total or avail is None:
        return None
    return (total - avail) / total, (total - avail) / 2**30, total / 2**30


def commit_used():
    """(share used, GB used, GB limit) or None when it can't be read."""
    system = platform.system()
    if system == "Windows":
        return _windows()
    if system == "Darwin":
        return _mac()
    if system == "Linux":
        return _linux()
    return None


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = str((d.get("tool_input") or {}).get("command", ""))
    low = cmd.lower()
    if re.search(r"(^|\s)(-h|--help)\b", low):
        return 0
    # only what the command RUNS counts, never words in its text: heredoc bodies and quoted strings go first (a note written with
    # echo "... Whisper stays on the GPU ..." is no Whisper launch)
    low = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1\b", " ", low, flags=re.S)
    low = re.sub(r"'[^']*'|\"[^\"]*\"", " ", low)
    hit = next(((h[1], h[2] if len(h) > 2 else LINE) for h in HEAVY if re.search(h[0], low)), None)
    if not hit:
        return 0
    why, line = hit
    if platform.system() == "Darwin":
        # macOS compresses and swaps on its own: "used" sits high on a 16 GB Mac at rest, so the OS's own pressure level decides
        # (1 normal, 2 warning, 4 critical); a heavy job starts only at normal
        try:
            lvl = subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], capture_output=True, text=True,
                                 timeout=5).stdout.strip()
        except Exception:
            return 0
        if lvl in ("2", "4"):
            print(f"Refused by commit_guard.py: {why} would start while macOS reports "
                  f"{'warning' if lvl == '2' else 'critical'} memory pressure. Wait for a running heavy job to finish and try again "
                  f"(re-check in a minute or two); run one model-loading job at a time.", file=sys.stderr)
            return 2
        return 0
    try:
        c = commit_used()
    except Exception:
        return 0
    if not c or c[0] < line:
        return 0
    print(f"Refused by commit_guard.py: {why} would start while memory is at {c[0]:.0%} ({c[1]:.1f} of {c[2]:.1f} GB; the line is "
          f"{line:.0%}). When the memory runs out the computer dies and takes every chat with it. Wait for a running heavy job to "
          f"finish and try again (re-check in a minute or two); run one model-loading job at a time; for footage searches use "
          f"find_shot --no-embed. The voice has priority on memory.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
