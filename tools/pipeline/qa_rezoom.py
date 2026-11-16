"""Re-zoom cuts: a picture pushes in, then a cut that changes nothing jumps back to the same picture at its start size and the push
begins again, which looks like a mistake. On the gate's probe (pipeline/gate/probe.jsonl): for every frame, every picture of 3%+ of the
frame (a clip or
image item); a cut where one of them is the SAME source as the frame before (a still: the same file; a clip: the same file
with its source second carrying on, within 0.2 s) but its box drops by more than 4% (the push restarting) is a re-zoom. Prints each
(time, the picture, the box before -> after); exit 1 if any.

  PIPE tools/pipeline/qa_rezoom.py <probe.jsonl> [--drop 0.04]"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("probe")
    ap.add_argument("--drop", type=float, default=0.04)
    a = ap.parse_args()
    lay, secs = {}, {}
    for line in open(a.probe, encoding="utf-8"):
        if line.startswith("layout|"):
            d = json.loads(line[7:])
            pics = {}
            for it in d["items"]:   # every picture item of 3%+ of the frame, its largest box per source
                if it.get("k") != "text" and it.get("op", 1) >= 0.5 and it["w"] * it["h"] >= 0.03 * 1920 * 1080:
                    pics[str(it["t"])] = max(pics.get(str(it["t"]), 0), it["w"] * it["h"])
            lay[d["frame"]] = pics
        elif line.startswith("clip|"):
            d = json.loads(line[5:])
            secs[(d["abs"], d["src"])] = d["s"]
    hits = []
    for f in sorted(lay):
        if f - 1 not in lay:
            continue
        for t1, a1 in lay[f].items():
            a0 = lay[f - 1].get(t1)
            if not t1 or a0 is None or a1 >= a0 * (1 - a.drop):
                continue
            s0, s1 = secs.get((f - 1, t1)), secs.get((f, t1))
            if s0 is not None and s1 is not None and abs(s1 - s0) > 0.2:
                continue        # a clip jumping to another moment of its file is a real cut
            hits.append((f, t1.split("/")[-1], round(a0 ** 0.5), round(a1 ** 0.5)))
    for f, t, b0, b1 in hits:
        s = f / 60
        print(f"{int(s // 60)}:{s % 60:05.2f} (frame {f}): {t} restarts its push (box ~{b0} -> ~{b1} px)")
    print(f"{len(hits)} re-zoom cut(s)")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
