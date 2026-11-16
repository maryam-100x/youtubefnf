"""The studio is its own environment: every command a chat runs uses the studio's own programs (uv, Node, npm, ffmpeg in MEDIA/apps)
and keeps every cache inside MEDIA, never the computer's own installs (tools/common/paths.py: studio_env).

Run by the SessionStart hook (.claude/settings.json): it writes the studio's variables into the file Claude Code names in
CLAUDE_ENV_FILE, which the app runs before each Bash command of the chat, so `node`, `npm`, `npx`, `uv`, `ffmpeg` and `ffprobe` in Bash
are the studio's. PowerShell doesn't read these lines (they aren't plain assignments): there, run those programs through
`PIPE tools/common/paths.py --run <command>` (CLAUDE.md). The cache variables also sit in .claude/settings.json's "env"
(install_hooks.py), which every tool of the chat gets.

  PIPE tools/hooks/studio_env.py           print the lines
  PIPE tools/hooks/studio_env.py --hook    the hook: add the lines to $CLAUDE_ENV_FILE (once; nothing when it isn't set)"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import shell_lines  # noqa: E402


def main():
    lines = shell_lines()
    if "--hook" not in sys.argv:
        print("\n".join(lines))
        return 0
    try:
        sys.stdin.read()          # the hook's JSON: nothing in it is needed
    except Exception:  # noqa: BLE001
        pass
    target = os.environ.get("CLAUDE_ENV_FILE")
    if not target:
        return 0
    f = Path(target)
    have = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
    new = [ln for ln in lines if ln not in have]
    if new:
        with open(f, "a", encoding="utf-8", newline="\n") as o:
            o.write("".join(ln + "\n" for ln in new))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001   a hook never blocks the chat
        print(f"studio_env hook: {e}", file=sys.stderr)
        sys.exit(0)
