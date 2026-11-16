"""qa_anchors.py <src folder>: every w(beat, phrase) anchor whose phrase occurs more than once in its beat.

w() (the timing helper the compositions import) returns the start of the FIRST match of the phrase in the beat, so a phrase that
occurs twice or more anchors to the first one whether the shot meant it or not (w('S12', 'million') can hit "eighty million" when
the shot meant "over a million people", and a count rolls 10 s early). This lists each literal w('Sxx', 'phrase') call in the
folder's .ts/.tsx files whose phrase matches more than once (tokens lowercased, every non [a-z0-9$%] stripped, a contiguous match
inside the beat, in the folder's words.json). A call that passes an nth (the 4th argument) picks its match itself and is skipped.

Exit 1 if any ambiguous phrase is not marked: a trailing /*first*/ comment on the same line says the first match is the one meant.
Calls whose phrase is not in its beat at all are listed too (w() would throw there).

  PIPE tools/motion/qa_anchors.py tools/motion/src/<video src>
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codefiles import code_files  # noqa: E402   with the subfolder files the film imports

CALL = re.compile(r"""(?<![\w.$])w\(\s*(['"])(S\d+[A-Za-z]?)\1\s*,\s*(['"])((?:(?!\3).)*)\3\s*([,)])""")
MARK = re.compile(r"/\*\s*first\s*\*/\s*$")


def norm(s):
    return re.sub(r"[^a-z0-9$%]", "", s.lower())


def rest_args(line, pos):
    """The text of the call's remaining arguments after the phrase (up to its closing paren)."""
    depth, i = 1, pos
    while i < len(line) and depth:
        if line[i] == "(":
            depth += 1
        elif line[i] == ")":
            depth -= 1
        i += 1
    return line[pos:i - 1] if depth == 0 else line[pos:]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    words = json.loads((src / "words.json").read_text(encoding="utf-8"))
    beats = {}
    for x in words:
        beats.setdefault(x["beat"], []).append(norm(x["w"]))

    def count(beat, phrase):
        toks = [t for t in (norm(p) for p in phrase.split()) if t]
        bw = beats.get(beat, [])
        if not toks:
            return 0
        return sum(1 for i in range(len(bw) - len(toks) + 1) if bw[i:i + len(toks)] == toks)

    bad, marked, missing = [], [], []
    for f in sorted(code_files(src, (".ts", ".tsx"))):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in CALL.finditer(line):
                beat, phrase = m.group(2), m.group(4)
                if m.group(5) == ",":
                    args = [a.strip() for a in rest_args(line, m.end()).split(",")]
                    if len(args) >= 2 and args[1] not in ("0", ""):
                        continue   # an explicit nth
                c = count(beat, phrase)
                row = f"{f.relative_to(src.resolve()).as_posix()}:{n}  {beat}  '{phrase}'  x{c}"
                if c == 0:
                    missing.append(row)
                elif c > 1:
                    (marked if MARK.search(line) else bad).append(row)
    for title, rows in (("AMBIGUOUS (not marked /*first*/)", bad), ("marked /*first*/", marked), ("NOT IN ITS BEAT", missing)):
        if rows:
            print(f"{title}: {len(rows)}")
            for r in rows:
                print("  " + r)
    if not bad:
        print(f"ok: no unmarked ambiguous anchor ({len(marked)} marked first)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
