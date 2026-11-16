"""PreToolUse hook (Write, Edit): refuses an edit to a shell script while bash is running it. Bash reads a script as it runs, a few lines
at a time, so an edit mid-run shifts what it reads next and the run breaks or runs the wrong lines (a long voice or render chain lost
halfway). A lesson that is only written down still needs a machine, so this hook holds it (as no_kill_by_name.py holds the kills).

Only .sh targets are looked at. The running scripts come from:
  Windows  the MSYS bash processes' /proc/<pid>/cmdline (Git Bash), read through one bash call (~0.3 s)
  Linux    /proc/<pid>/cmdline, read by the same bash call
  macOS    `ps -axww -o pid=,command=` (no /proc); a script named by a relative path is resolved against its process's working folder
           (`lsof -a -d cwd -p <pid> -Fn`, asked only for those)
Exit 2 (refused, the reason goes back to the model); anything else, or any failure to look, passes."""
import json
import os
import platform
import shutil
import subprocess
import sys

# one line per process: its arguments split by \037 (a command line can hold newlines: the Bash tool's own commands do)
LIST = r'''for p in /proc/[0-9]*; do c=$(tr '\0\n' '\037 ' < "$p/cmdline" 2>/dev/null) || continue; case "$c" in *.sh*) printf '%s\036%s\036%s\n' "${p#/proc/}" "$(readlink "$p/cwd" 2>/dev/null)" "$c";; esac; done'''
MAC = platform.system() == "Darwin"


def norm(p):
    """C:\\Users\\x -> /c/users/x on Windows; lower case (Windows paths and macOS's default disks ignore case)."""
    p = p.replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = "/" + p[0].lower() + p[2:]
    return os.path.normpath(p).replace("\\", "/").lower()


def _proc_rows():
    """(pid, cwd, [args]) of processes whose command line names a .sh, from /proc (Git Bash on Windows, Linux)."""
    bash = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.exe"
    out = subprocess.run([bash, "-c", LIST], capture_output=True, text=True, timeout=8).stdout
    for line in out.split("\n"):   # never splitlines(): it also breaks at \x1e, the field separator
        try:
            pid, cwd, cmd = line.split("\x1e", 2)
        except ValueError:
            continue
        yield pid, cwd, [a for a in cmd.split("\x1f") if a]


def _mac_cwd(pid):
    try:
        out = subprocess.run(["lsof", "-a", "-d", "cwd", "-p", str(pid), "-Fn"], capture_output=True, text=True, timeout=4).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return next((ln[1:] for ln in out.splitlines() if ln.startswith("n")), "")


def _mac_rows():
    """(pid, cwd, [args]) from ps; ps joins the arguments with spaces, so a path with a space in it is not told apart."""
    out = subprocess.run(["ps", "-axww", "-o", "pid=,command="], capture_output=True, text=True, timeout=8).stdout
    for line in out.splitlines():
        pid, _, cmd = line.strip().partition(" ")
        if not pid.isdigit() or ".sh" not in cmd:
            continue
        args = cmd.split()
        cwd = _mac_cwd(pid) if any(a.endswith(".sh") and not a.startswith("/") for a in args[1:]) else ""
        yield pid, cwd, args


def running(target):
    me = os.getpid()
    for pid, cwd, args in (_mac_rows() if MAC else _proc_rows()):
        for a in args[1:]:
            if not a.lower().endswith(".sh"):
                continue
            full = a if a.startswith("/") or (len(a) > 1 and a[1] == ":") else f"{cwd}/{a}"
            if norm(full) == target and int(pid) != me:
                return pid, " ".join(args)[:160]
    return None


def main():
    try:
        d = json.load(sys.stdin)
        path = str((d.get("tool_input") or {}).get("file_path", ""))
        if not path.lower().endswith(".sh"):
            return 0
        hit = running(norm(path))
    except Exception:  # noqa: BLE001
        return 0   # a hook that can't look never blocks the work
    if hit:
        pid, cmd = hit
        print(f"Refused by no_edit_running_script.py: {path} is running now (bash PID {pid}: {cmd}). Bash reads a script as it runs, so "
              "an edit now breaks the run. Wait for it to finish, or write the change into a copy under a new name.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
