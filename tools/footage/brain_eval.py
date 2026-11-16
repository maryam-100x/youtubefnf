"""The brain's test: for every line in kb/footage/brain/EVAL_LINES.txt, find_shot's top 3 and one sheet per line (each hit's start,
middle and end frame with its 9:16 window in red) to be read by eye; the verdicts (hit / near / miss per line) go into
kb/footage/brain/EVAL.md by hand after the reading.

EVAL_LINES.txt is the creator's: real script lines, one a line, optionally a tab and a note on the shot it should find ("# " lines are
comments). Twenty lines from finished scripts are enough to see whether the search finds the right moments.

  EDIT tools/footage/brain_eval.py [--out FOOTAGE/index/brain/eval] [--no-embed]
Writes <out>/eval_NN.jpg and <out>/eval_hits.json (the hits per line, for the write-up)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402
import find_shot as F  # noqa: E402

LINES = B.BRAIN / "EVAL_LINES.txt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(B.WORK / "eval"))
    ap.add_argument("--no-embed", action="store_true")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    if not LINES.exists():
        raise SystemExit(f"no test lines yet: write {LINES} (one script line a line, a tab, a note on the shot it should find)")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    for ln in LINES.read_text(encoding="utf-8").splitlines():
        if ln.strip() and not ln.startswith("#"):
            q, _, src = ln.partition("\t")
            lines.append((q.strip(), src.strip()))
    recs = F.load_records()
    print(f"{len(recs)} records, {len(lines)} lines")
    result = []
    for i, (q, src) in enumerate(lines):
        hits = F.search(q, recs, use_embed=not a.no_embed, n=a.n)
        sheet = out / f"eval_{i + 1:02d}.jpg"
        F.sheet(hits, str(sheet), vertical=False)
        print(f"\n[{i + 1}] {q}  {src}")
        for k, h in enumerate(hits):
            print(f"   #{k} " + F.fmt(h).split("\n")[0])
            print("      " + h["rec"].get("desc", "")[:150])
        result.append(dict(line=q, src=src, sheet=str(sheet),
                           hits=[dict(score=h["score"], id=h["rec"]["id"], desc=h["rec"].get("desc", ""), flags=h["rec"].get("flags", []),
                                      v=h["rec"].get("v"), used_in=h["rec"].get("used_in", [])) for h in hits]))
    (out / "eval_hits.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(result)} lines -> {out}")


if __name__ == "__main__":
    main()
