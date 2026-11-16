"""PreToolUse hook (Bash, PowerShell): while a render, a probe, a gate or a 4K finish holds a heavy.py ticket, refuse a recursive scan
of a whole drive or of a huge tree: a drive root (/, C:\\, /Volumes/<disk>), the users folder, the home folder, or the media root
(tools/common/paths.py MEDIA). Recursive disk scans beside a render have ended in a crash of the whole computer; a line in the
rules did not hold it, this does. A scan of a named sub-folder passes; so does anything while no heavy ticket is live.

  PIPE tools/hooks/no_disk_scan.py --test     the patterns against sample commands (built from this computer's own paths)
Exit 2 refuses the call (the reason goes back to the model); anything else passes."""
import json
import platform
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:
    sys.path.insert(0, str(HERE.parent / "common"))
    from paths import MEDIA  # noqa: E402
except Exception:  # noqa: BLE001  (a hook never fails on its own set-up: the drive roots and the home folder are still guarded)
    MEDIA = None

WINDOWS = platform.system() == "Windows"
SEP = r"[\\/]"


def forms(p):
    """A folder as a command may write it, lower case: C:/x, C:\\x, /c/x (Git Bash), and ~/x, $HOME/x when under the home folder."""
    s = str(p).replace("\\", "/").rstrip("/")
    out = {s}
    if len(s) > 1 and s[1] == ":":
        out.add("/" + s[0] + s[2:])
    home = str(Path.home()).replace("\\", "/").rstrip("/")
    if home and s.lower().startswith(home.lower()):
        rest = s[len(home):]
        out |= {"~" + rest, "$home" + rest, "${home}" + rest}
    return sorted({x.lower() for x in out if x}, key=len, reverse=True)


def folder_rx(p):
    return [re.escape(f).replace("/", SEP) + SEP + "?" for f in forms(p)]


ALTS = folder_rx(Path.home()) + [r"~" + SEP + "?", r"\$home" + SEP + "?", r"\$\{home\}" + SEP + "?"]
if MEDIA is not None:
    ALTS = folder_rx(MEDIA) + ALTS
if WINDOWS:   # the drives and the users folder, as Windows and Git Bash write them
    ALTS += [r"[a-z]:" + SEP + "users" + SEP + "?", r"/[a-z]/users/?", r"[a-z]:" + SEP + "?", r"/[a-z]/?"]
else:         # the disks and the users folders of macOS and Linux
    ALTS += [r"/volumes/[^/\s\"';|&]+/?", r"/volumes/?", r"/users/?", r"/home/?", r"/system/volumes/data/?"]
ALTS += [r"/"]
ROOT = "(?:" + "|".join(ALTS) + ")"
END = r"""(?=["']?(?:\s|$|;|\||&|\)))"""
PATTERNS = [
    (rf"""(^|[\s;&|(])find\s+["']?{ROOT}{END}""", "find over a drive or a huge tree"),
    (rf"""(^|[\s;&|(])du\s+(-\w+\s+)*["']?{ROOT}{END}""", "du over a drive or a huge tree"),
    (rf"""(^|[\s;&|(])(ls|tree)\s+(-\w*r\w*\s+|/f\s+)+["']?{ROOT}{END}""", "a recursive listing of a drive or a huge tree"),
    (rf"""(^|[\s;&|(])(grep|rg)\s+[^|;\n]*-\w*r\w*\b[^|;\n]*\s["']?{ROOT}{END}""", "a recursive grep over a drive or a huge tree"),
    (rf"""(get-childitem|gci|dir|ls)\b[^|;\n]*-recurse[^|;\n]*["']?{ROOT}{END}""", "Get-ChildItem -Recurse over a drive or a huge tree"),
    (rf"""(get-childitem|gci|dir|ls)\s+(-path\s+)?["']?{ROOT}["']?\s[^|;\n]*-recurse""", "Get-ChildItem -Recurse over a drive or a huge tree"),
    (rf"""(^|[\s;&|(])dir\s+["']?{ROOT}["']?\s*/s\b""", "dir /s over a drive or a huge tree"),
    (rf"""(^|[\s;&|(])dir\s+/s\s+["']?{ROOT}{END}""", "dir /s over a drive or a huge tree"),
]


def heavy_running():
    """the live render/finish/probe/gate tickets (heavy.py prunes stale ones)"""
    try:
        sys.path.insert(0, str(HERE.parent / "pipeline"))
        import heavy  # noqa: E402
        return [t for t in heavy.tickets() if t.get("kind") in ("render", "finish", "probe", "gate")]
    except Exception:
        return []


def offending(cmd):
    low = cmd.lower()
    for rx, why in PATTERNS:
        if re.search(rx, low):
            return why
    return None


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = str((d.get("tool_input") or {}).get("command", ""))
    why = offending(cmd)
    if not why:
        return 0
    live = heavy_running()
    if not live:
        return 0
    what = ", ".join(t.get("what", "?") for t in live)
    print(f"Refused by no_disk_scan.py: {why} while a heavy job runs ({what}). Recursive disk scans beside a render have crashed the whole "
          f"computer. Scan a named sub-folder instead, or wait until the job is done.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        home = str(Path.home()).replace("\\", "/")
        media = str(MEDIA).replace("\\", "/") if MEDIA is not None else home + "/Studio"
        bad = ["find / -name '*.mp4'", f"du -sh {media}", "ls -R /", f"grep -r foo {home}", "rg -r foo ~/",
               f"Get-ChildItem {media} -Recurse -Filter *.mkv", f"gci -Recurse {media}", f"find {home} -name x"]
        if WINDOWS:
            bad += ["find /c -name x", "Get-ChildItem C:\\ -Recurse -Filter *.mkv", "dir C:\\ /s", "Get-ChildItem -Path C:\\Users -Recurse"]
        else:
            bad += ["find /Users -name x", "du -sh /Volumes/Backup"]
        good = [f"find {media}/videos/demo -name '*.mkv'", f"du -sh {media}/videos", f"ls -la {media}", f"Get-ChildItem {media}/videos -Recurse",
                "grep -rn foo tools", "find . -name x", "ls /"]
        ok = all(offending(c) for c in bad) and not any(offending(c) for c in good)
        for c in bad:
            print("BLOCK" if offending(c) else "MISS ", c)
        for c in good:
            print("PASS " if not offending(c) else "FALSE", c)
        sys.exit(0 if ok else 1)
    sys.exit(main())
