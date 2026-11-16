"""Screen every take in a section_takes.py folder with the voice guard's measures (an accent slip gets several seed takes; the
creator's ear picks among the ones the guard passes). For each take: the guard's flags (ACCENT, CLOSE/DEEP, WHISPER, TONE JUMP,
SWALLOWED WORD), its mean accent score (lower = less British), rhotic.py's dip and the words Whisper missed (section_takes'
sections.json), ranked best first per section, with the current render (take 0) for comparison. Needs the guard's model
(voice_guard.py's docstring: built from the creator's own takes).

  PIPE tools/voice/screen_takes.py <takes dir> [--voice short|long] [--out <report.md>]"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE))
import voice_guard as G  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--voice", choices=["short", "long"], default="short")
    ap.add_argument("--out")
    a = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    d = Path(a.dir)
    M = G.load_model()
    rep = json.loads((d / "sections.json").read_text(encoding="utf-8"))
    lines = [f"# Takes screened: {d}", ""]
    for sec, info in rep.items():
        rows = []
        for t in info["takes"]:
            k = t["take"]
            raw = d / "raw" / f"{sec}_{k}.wav"
            alp = raw.with_suffix(".align.json")
            if not raw.exists() or not alp.exists():
                continue
            al = json.loads(alp.read_text(encoding="utf-8"))
            tw = G.words_from_align(al)
            tb = [{"id": f"{sec}#{k}", "start": 0.0, "end": tw[-1]["end"] if tw else 0.0, "text": info.get("text", "")}]
            res = G.screen(raw, tw, tb, M, sections=[{"beats": [tb[0]["id"]], "name": f"take {k}", "text": info.get("text", "")}], voice=a.voice,
                           align=al, label=f"{sec} take {k}")
            flags = "; ".join(m for r in res["beats"] for _, _, m in r["flags"]) or "clean"
            acc = float(np.nanmean([r["accent"] for r in res["beats"]])) if res["beats"] else float("nan")
            missing = G.real_missing(t.get("missing", []))
            rows.append((G.take_score(res), k, acc, flags, t.get("rhotic_dip"), missing))
        rows.sort(key=lambda r: (bool(r[5]), r[0]))
        lines.append(f"## {sec}")
        for sc, k, acc, flags, dip, missing in rows:
            lines.append(f"- take {k}: accent {acc:.2f}, rhotic dip {dip if dip is not None else '?'}; {flags}"
                         + (f"; MISSING {' '.join(missing)}" if missing else ""))
        lines.append("")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
