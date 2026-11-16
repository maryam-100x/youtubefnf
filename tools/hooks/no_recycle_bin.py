"""PreToolUse hook (Bash, PowerShell, Write, Edit): refuses sending anything to the Recycle Bin (Windows) or the Trash (macOS).
Deletes in this work are permanent, so nobody has to empty a bin by hand; a tool that "safely" bins its clean-up fills the disk
behind everyone's back. Written as a rule it gets forgotten, so a hook holds it.

Blocked in a command, or in code being written:
  Windows  the VisualBasic FileIO bin option, the send-to-trash library, SHFileOperation's undo flag, the FileIO recycle-option enum,
           Shell.Application's delete verb, the Recycle module's safe remove, nircmd's bin move, a move into the bin's own folder
  macOS    Finder's delete or "move ... to trash" through osascript / AppleScript, the `trash` command, NSFileManager's trashItem, a
           move (mv, shutil.move, os.rename, Move-Item) into ~/.Trash
Exit 2 (the tool call is refused and the reason goes back to the model); anything else passes. Delete for good instead:
Remove-Item -Recurse -Force, rm -rf, shutil.rmtree, Path.unlink.
The patterns below are written in pieces (adjacent string literals) so this file never matches itself."""
import json
import re
import sys

PATTERNS = [
    (r"sendto" r"recyclebin", "the VisualBasic FileIO bin option"),
    (r"send2" r"trash", "the send-to-trash library"),
    (r"fof_allow" r"undo", "SHFileOperation with the undo flag (the bin)"),
    (r"recycle" r"option", "the FileIO recycle-option enum"),
    (r"invokeverb" r"\(\s*['\"]delete", "Shell.Application's delete verb (the bin)"),
    (r"remove-item" r"safely", "the Recycle module's safe remove"),
    (r"move" r"recyclebin", "nircmd's bin move"),
    (r"(move-item|\bmv\b|\bmove\b)[^\n]*\$" r"recycle\.bin", "a move into the Recycle Bin's own folder"),
    # macOS: the Trash
    (r"application\s+\\?[\"']finder\\?[\"'][\s\S]{0,300}?\bdelete\b", "Finder's delete (the Trash)"),
    (r"application\s+\\?[\"']finder\\?[\"'][\s\S]{0,300}?\bto\s+(the\s+)?trash\b", "Finder's move to the Trash"),
    (r"trashitem(aturl)?\b", "NSFileManager's trashItem (the Trash)"),
    (r"(\bmv\b|move-item|shutil\.move|os\.rename|os\.replace|\.rename\()[^\n]*[/\\]\.trash\b", "a move into ~/.Trash"),
]
COMMAND_ONLY = [   # looked for in a command only: as a word in prose being written it means nothing
    (r"(^|[\s;&|(])trash\s+[^\s|;&]", "the trash command (the Trash)"),
]
SELF = "tools/hooks/no_recycle_bin.py"   # this file names the patterns it blocks


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    ti = d.get("tool_input") or {}
    if str(ti.get("file_path", "")).replace("\\", "/").lower().endswith(SELF):
        return 0
    text = "\n".join(str(ti.get(k, "")) for k in ("command", "content", "new_string")).lower()
    command = str(ti.get("command", "")).lower()
    hits = [why for rx, why in PATTERNS if re.search(rx, text)] + [why for rx, why in COMMAND_ONLY if re.search(rx, command)]
    if hits:
        print(f"Refused by no_recycle_bin.py: {hits[0]}. Deletes here are permanent, never the Recycle Bin or the Trash (nobody empties "
              "it by hand). Look at the target first, then delete for good: Remove-Item -Recurse -Force, rm -rf, shutil.rmtree, "
              "Path.unlink.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
