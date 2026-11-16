"""A Short is shown, never read, and draws no credit labels: this refuses a Short's code that draws a page as a shot's picture (a
browser card of a page, a receipt, a headline, words lit as the act) or a credit, before the gate runs. Viewers of a Short scroll past
cards of text; they stay for pictures.
Text that merely sits inside a frame or a clip is fine (it is not the hero of the image); this reads the code, so it finds the page
components, the page captures used as pictures and the credit props, never a word inside footage.

  PIPE tools/motion/short_visual_check.py src/<short folder>/<Short>.tsx [more.tsx ...]
Exit 0 when clean, 1 with every hit by line."""
import re
import sys
from pathlib import Path

# components that draw a page, a post or a card of words as the picture (the kits' names and the usual names a Short gives its own)
PAGE_COMPONENTS = ("MarkCard", "PageCard", "Receipt9", "Receipt", "Line9", "LockReceipt", "Browser", "Page", "Headlines", "ForumCard",
                   "WebPic", "CodeCard", "UpdateCard", "SpotCard", "Spots")
CHECKS = [
    ("PAGE_CARD", re.compile(r"<(" + "|".join(PAGE_COMPONENTS) + r")\b"), "draws a page or a card of words as the picture (shown, never read)"),
    ("PAGE_IMAGE", re.compile(r"\bpg\(\s*['\"]|['\"/]pages/|\bpages\d*\w*\.json"), "uses a page capture as a picture (shown, never read)"),
    ("CREDIT", re.compile(r"\bcredit\s*=|<Credit\b"), "draws a credit label (a Short draws no credits)"),
]


def check(path):
    hits = []
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("//", 1)[0] if not raw.lstrip().startswith("import") else raw
        if not line.strip():
            continue
        for name, rx, why in CHECKS:
            m = rx.search(line)
            if m:
                hits.append((n, name, why, raw.strip()[:150]))
    return hits


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    bad = 0
    for p in sys.argv[1:]:
        hits = check(p)
        bad += len(hits)
        for n, name, why, src in hits:
            print(f"{p}:{n}: {name}: {why}\n    {src}")
        print(f"{p}: {'clean' if not hits else f'{len(hits)} hit(s)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
