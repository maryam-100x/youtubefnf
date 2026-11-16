"""PreToolUse hook (Bash, PowerShell): refuses a command that kills processes by NAME. Several chats and their agents share this
computer; a kill by image name hits every chat's jobs (a `taskkill /IM ffmpeg.exe` stops another chat's render mid-stitch along with
any cut). Kill only the PIDs your own command started.

Blocked: taskkill /IM, Stop-Process -Name/-ProcessName, Get-Process <name> | Stop-Process, pkill, killall, wmic ... where name=... delete.
Exit 2 (the tool call is refused and the reason goes back to the model); anything else passes."""
import json
import re
import sys

PATTERNS = [
    (r"\btaskkill\b[^\n]*\s/im\b", "taskkill /IM kills every process of that name"),
    (r"\bstop-process\b[^\n|;]*\s-(process)?name\b", "Stop-Process -Name kills every process of that name"),
    (r"\bget-process\s+(-name\s+|-processname\s+)?['\"]?[a-z*][\w.*-]*['\"]?[^|\n]*\|\s*stop-process\b", "Get-Process <name> | Stop-Process kills every process of that name"),
    (r"(^|[\s;&|(])pkill\s", "pkill kills by name"),
    (r"(^|[\s;&|(])killall\s", "killall kills by name"),
    (r"\bwmic\b[^\n]*\bwhere\b[^\n]*\bname\s*=[^\n]*\b(delete|terminate)\b", "wmic ... where name= ... delete kills by name"),
]


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = str((d.get("tool_input") or {}).get("command", ""))
    low = cmd.lower()
    for rx, why in PATTERNS:
        if re.search(rx, low):
            print(f"Refused by no_kill_by_name.py: {why}. Several chats and their agents share this computer, and a kill by name stops "
                  "other chats' renders, cuts and voice jobs. Kill only the PIDs your own command started: Stop-Process -Id <pid>, "
                  "taskkill /PID <pid> /T, or kill <pid>.", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
