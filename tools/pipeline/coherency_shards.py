"""The coherency read in parallel (speed every step, keep every check).

coherency.py writes ONE packet and one fresh reader reads it all: ~20 min for a 25-shot prototype, and a long film's packet can run to
1,500 lines with ~1,050 shots, read the same way. This splits the packet's shot table into N slices, each a packet of its own with
everything a reader needs to judge it (the rubric, the creator's verdicts, the WHOLE script so every line keeps its context, the
interview, the real voices, the glosses, the oversized stills, and only that slice of the shot table plus the 3 rows before it), so N
fresh readers read at once; then merges their flags into the one COHERENCY.md that `coherency.py check` reads (the stamp line, flags
renumbered C1..Cn in film order). Script-only flags that several readers raise alike are kept once. coherency.py itself is unchanged.

  EDIT tools/pipeline/coherency_shards.py split <video> [--n 4]
        -> <dj>/pipeline/coherency/shards/packet_<k>.md (run `coherency.py packet <video>` first); prints each reader's brief
  EDIT tools/pipeline/coherency_shards.py merge <video>
        -> videos/<video>/COHERENCY.md from shards/flags_<k>.md (each reader writes its own: the stamp line, then "- [ ] C1 ..." lines)
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import Video, find_video  # noqa: E402

TABLE = "## The shot table"
CONTEXT_ROWS = 3


def parts(packet):
    """(head before the shot table, the table's header lines, its rows, the stamp)"""
    t = packet.read_text(encoding="utf-8")
    m = re.search(r"stamp ([0-9a-f]{16})", t)
    if not m or TABLE not in t:
        raise SystemExit(f"{packet}: not a coherency packet (no stamp or no shot table): run coherency.py packet first")
    head, table = t.split(TABLE, 1)
    lines = table.splitlines()
    hdr = [TABLE + lines[0]] + [ln for ln in lines[1:4] if ln.startswith("|") and ("---" in ln or "file" in ln)]
    rows = [ln for ln in lines[1:] if ln.startswith("| ") and ln not in hdr]
    tail = [ln for ln in lines[1:] if not ln.startswith("|")]
    return head, hdr, rows, m.group(1), "\n".join(tail).strip()


def split(v, n):
    d = v.pipe_dir / "coherency"
    head, hdr, rows, stamp, tail = parts(d / "packet.md")
    sd = d / "shards"
    sd.mkdir(exist_ok=True)
    for f in sd.glob("*.md"):
        f.unlink()
    n = max(1, min(n, len(rows)))
    size = -(-len(rows) // n)
    for k in range(n):
        a, b = k * size, min(len(rows), (k + 1) * size)
        if a >= b:
            break
        ctx = rows[max(0, a - CONTEXT_ROWS):a]
        body = [head.rstrip(), "", *hdr]
        if ctx:
            body += [r.replace("| ", "| (context, judged by the slice before) ", 1) for r in ctx]
        body += rows[a:b]
        if tail:
            body += ["", tail]
        note = (f"\n\n**Your slice: shots {a + 1}-{b} of {len(rows)}.** Judge every SCRIPT line (the whole script is here for context) "
                f"only where it meets your slice's shots, and every PICTURE in your slice. Rows marked (context) belong to the slice "
                f"before: read them, never flag them.\n")
        (sd / f"packet_{k + 1}.md").write_text("\n".join(body).replace(TABLE, note + TABLE, 1) + "\n", encoding="utf-8")
        print(f"shard {k + 1}: shots {a + 1}-{b} -> {sd / f'packet_{k + 1}.md'}")
        print(f"  brief: a fresh reader reads {sd / f'packet_{k + 1}.md'} (the rubric inside it) and writes {sd / f'flags_{k + 1}.md'}: "
              f"'stamp: {stamp}' then '- [ ] C1 S.. SCRIPT|PICTURE|AUDIO: <words> | <why> | <fix>' lines, or 'No flags.'")


def merge(v):
    sd = v.pipe_dir / "coherency" / "shards"
    stamp = parts(v.pipe_dir / "coherency" / "packet.md")[3]
    flags, seen = [], set()
    files = sorted(sd.glob("flags_*.md"), key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))
    if not files:
        raise SystemExit(f"no flags_<k>.md in {sd}")
    for f in files:
        t = f.read_text(encoding="utf-8")
        m = re.search(r"stamp:\s*([0-9a-f]{16})", t)
        if not m or m.group(1) != stamp:
            raise SystemExit(f"{f.name}: read of another version (stamp {m.group(1) if m else 'none'}, now {stamp}): read it again")
        for ln in t.splitlines():
            mm = re.match(r"- \[[ x]\] C\d+ (.*)$", ln.strip())
            if not mm:
                continue
            body = mm.group(1)
            key = re.sub(r"\W+", " ", body.split("|")[0].lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            flags.append(body)
    def beat(b):
        m = re.match(r"S(\d+)", b)
        return int(m.group(1)) if m else 9999
    flags.sort(key=beat)
    out = [f"stamp: {stamp}"] + [f"- [ ] C{i} {b}" for i, b in enumerate(flags, 1)] or ["No flags."]
    if not flags:
        out.append("No flags.")
    (v.folder / "COHERENCY.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(flags)} flag(s) from {len(files)} reader(s) -> {v.folder / 'COHERENCY.md'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["split", "merge"])
    ap.add_argument("video")
    ap.add_argument("--n", type=int, default=4)
    a = ap.parse_args()
    v = Video(find_video(a.video))
    split(v, a.n) if a.step == "split" else merge(v)


if __name__ == "__main__":
    main()
