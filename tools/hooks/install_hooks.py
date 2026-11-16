"""Writes the repo's Claude Code hooks: <repo>/.claude/settings.json gets the "hooks" block of tools/hooks/settings.template.json,
every command pointing at this repo's pipeline python (PY_PIPE, tools/common/paths.py) and its hook scripts in tools/hooks/, as
absolute paths with forward slashes (they work the same on Windows, from Git Bash or cmd, and on macOS). The setup runs it once, after
the pipeline venv is built; run it again whenever the repo or the venv moves.

  PIPE tools/hooks/install_hooks.py            write .claude/settings.json (other keys in it are kept; "hooks" is replaced)
  PIPE tools/hooks/install_hooks.py --print    show what would be written, write nothing
  PIPE tools/hooks/install_hooks.py --force    write even when the pipeline python is not there yet (the hooks fail until it is)

The hooks: chat_health.py (UserPromptSubmit, and SessionStart after a compaction), keep_working.py (Stop), no_kill_by_name.py,
no_disk_scan.py and commit_guard.py (before Bash/PowerShell), no_recycle_bin.py (before Bash/PowerShell/Write/Edit),
no_edit_running_script.py (before Write/Edit). Every one of them only reads, refuses with exit 2, or passes; none needs more than the
standard library and tools/common/paths.py."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import PY_PIPE, REPO  # noqa: E402

TEMPLATE = HERE / "settings.template.json"
TARGET = REPO / ".claude" / "settings.json"


def posix(p):
    return str(Path(p)).replace("\\", "/")


def build():
    hooks = json.loads(TEMPLATE.read_text(encoding="utf-8"))["hooks"]
    py, folder = posix(PY_PIPE), posix(HERE)
    missing = []
    for event in hooks.values():
        for group in event:
            for h in group.get("hooks", []):
                cmd = h["command"].replace("{PY}", py).replace("{HOOKS}", folder)
                h["command"] = cmd
                for script in re.findall(r'"([^"]+\.py)"', cmd):
                    if not Path(script).exists():
                        missing.append(script)
    return hooks, sorted(set(missing))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--print", dest="show", action="store_true", help="show the settings, write nothing")
    ap.add_argument("--force", action="store_true", help="write even when the pipeline python does not exist yet")
    a = ap.parse_args()
    hooks, missing = build()
    if missing:
        sys.exit("hook scripts missing (a partial checkout?): " + ", ".join(missing))
    settings = {}
    if TARGET.exists():
        try:
            settings = json.loads(TARGET.read_text(encoding="utf-8"))
        except ValueError as e:
            sys.exit(f"{TARGET} is not valid JSON ({e}): fix or remove it, then run this again")
    settings["hooks"] = hooks
    text = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    if a.show:
        print(text)
        return 0
    if not Path(PY_PIPE).exists() and not a.force:
        sys.exit(f"the pipeline python is not there yet ({posix(PY_PIPE)}): build the pipeline venv first (SETUP.md), or pass --force")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8")
    n = sum(len(g.get("hooks", [])) for ev in hooks.values() for g in ev)
    print(f"{n} hooks written to {posix(TARGET)} (python {posix(PY_PIPE)}); a chat started in this folder from now on runs them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
