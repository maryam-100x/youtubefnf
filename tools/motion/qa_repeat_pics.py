"""qa_repeat_pics.py: the same picture twice in one film (the gate's B7 TWICE sees clips only; a still, a cut-out or a ground reused
across several shot lines slips past it). Every picture file (.jpg/.png/.webp) the composition's code names is counted across all its
shot lines, by name and by content (the same bytes under two names); a picture in more than one place is listed unless the extra
place's comment says why (`named-moment:` with its words, or `repeat: <why>` for a deliberate callback). A ground or texture used under
several built shots counts too (a run of the same blurred ground reads as one picture on a loop).

  PIPE tools/motion/qa_repeat_pics.py --src tools/motion/src/<video src> [--img <public dir>/<video src>/img]
  exit 1 when a picture repeats without a reason"""
import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from codefiles import code_files  # noqa: E402
from paths import PUBLIC  # noqa: E402

PIC = re.compile(r"""['"`]([^'"`\s]+?\.(?:jpe?g|png|webp))['"`]""", re.I)


def uses(src):
    """[(file name, tsx, line no, has_reason)] for every picture named on a code line (comments above it read for the reason)"""
    out = []
    for f in code_files(src):   # with the subfolder files the film imports
        name = f.relative_to(Path(src).resolve()).as_posix()
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            code = ln.split("//", 1)[0]
            names = [Path(m).name for m in PIC.findall(code)]
            if not names:
                continue
            block = [ln.split("//", 1)[1]] if "//" in ln else []
            k = i - 1
            while k >= 0 and lines[k].strip().startswith("//"):
                block.insert(0, lines[k].strip()[2:])
                k -= 1
            why = " ".join(block)
            reason = ("named-moment:" in why) or bool(re.search(r"\brepeat:", why))
            for n in names:
                out.append((n, name, i + 1, reason))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="the composition's src folder: tools/motion/src/<folder>")
    ap.add_argument("--img", help="where its pictures are (default: <public dir>/<src folder name>/img)")
    a = ap.parse_args()
    us = uses(a.src)
    by = defaultdict(list)
    for n, f, ln, r in us:
        by[n].append((f, ln, r))
    # the same bytes under two names
    md = {}
    img = Path(a.img) if a.img else PUBLIC / Path(a.src).resolve().name / "img"
    for n in by:
        hits = list(img.rglob(n))
        if hits:
            try:
                md[n] = hashlib.md5(hits[0].read_bytes()).hexdigest()
            except OSError:
                pass
    same = defaultdict(list)
    for n, h in md.items():
        same[h].append(n)
    groups = [sorted(v) for v in same.values() if len(v) > 1]
    bad = 0
    # one place may go without a reason: the picture's own place, the earliest in the film. Which line that is can't be read from file
    # names (a later section's reasoned uses of an earlier section's cut-outs can sort before that section's own files and leave its own
    # lines "without a reason"), so a picture passes when at most one of its places lacks a reason, wherever that place sorts
    for n, places in sorted(by.items()):
        if len(places) < 2:
            continue
        unexplained = [p for p in places if not p[2]]
        if len(unexplained) > 1:
            bad += 1
            print(f"REPEAT {n}: {len(places)} places: " + ", ".join(f"{f}:{ln}{'' if r else ' (no reason)'}" for f, ln, r in places))
    for g in groups:
        places = [p for n in g for p in by[n]]
        if len(places) > 1 and sum(not p[2] for p in places) > 1:
            bad += 1
            print(f"SAME PICTURE under {len(g)} names {', '.join(g)}: " + ", ".join(f"{f}:{ln}" for f, ln, _ in places))
    print(f"{len(by)} pictures named in {a.src}; {bad} repeated without a reason")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
